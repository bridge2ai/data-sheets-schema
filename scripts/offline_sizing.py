#!/usr/bin/env python3
"""Step A1 model-free sizing sweep for generic_v10 API requests (#5072, #4829, #4830).

Builds every request the runtime constructs for a run, with the production
builders, from historical phase-1 originals staged into a scratch run
(plan step A1, `notes/d4d_generation_plan_2026-10-09.md`). Measures each
request's canonical payload bytes, estimates its tokens with ratios
calibrated from the 2026-10-12 A1b `messages.count_tokens` results, and
applies the launch rule:

- every typed-audit worker fits in 1,000,000 tokens in flight (input plus
  the request's own `max_tokens`);
- every report, report regate and after-repair report fits in 850,000 (a 15%
  margin under the 1,000,000-token window);
- every other request fits in the window.

A token figure here is an ESTIMATE from bytes, never a count. Its verdict is
recorded as `estimate_fits` / `estimate_exceeds`; it can never be PASS, and it
is no substitute for the A1b count that the unbilled endpoint gives. The
evidence reader in `data_sheets_schema.offline_sizing` stays the only place a
saved count can clear a request.

No provider call: sockets are blocked before anything is imported. Writes
only under `--workdir` and `--out`.

The sweep needs the A3 draft registration builder and the A5d omission
contexts (`scripts/build_api_registrations.py`, `data/omission_contexts/`,
PR #5095), so `--root` names a checkout that has them. Example::

    PYTHONPATH=<root>/src:<root> python scripts/offline_sizing.py sweep \\
        --root <root> --workdir <new dir> --out <new file>.json
    python scripts/offline_sizing.py table <file>.json      # per-project tables
    python scripts/offline_sizing.py summary <file>.json    # the note's cross-project tables

Placeholders for content that does not exist before a run (the report as
written, the responses integration carries) are sized at their output caps in
TOKENS, added after the byte estimate. A1b sized them as runs of 'x' at 4
bytes per token, and the endpoint counted about one token per 'x' (see A1B
below). So each A1b placeholder counted about four times its intended size,
and those rows overstate the report family by about three times each
placeholder's intended size.

Each typed worker's answer is floored (`response_floor`). The floor has one
row per assigned path; each claim quotes and covers its value, as the
terminal source review requires; every other string is one character.
- **The worker-stage check** (`audit_batches.check_worker`) accepts the
  floor. It also accepts a smaller answer with one-character claims, which is
  recorded too.
- **The terminal check** (`evidence_assertions.check_audit`, run at assembly)
  is run on the assembled floor audit, to confirm that it has no quoting or
  coverage finding.

Two carries are sized at the larger of the registered output caps' bound and
the floor, since a completed audit carries at least every row whatever the
caps:
- the audit that `reconcile_full` and the report family carry;
- the worker answers integration carries, as saved envelopes with the
  proposal index.

When the floor wins, the figure is a lower bound for that carry.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import math
import re
import socket
import sys
from pathlib import Path
from types import SimpleNamespace

ROUTE_WINDOW_TOKENS = 1_000_000
WORKER_CEILING_TOKENS = 1_000_000
REPORT_CEILING_TOKENS = 850_000
REPORT_PHASES = ("report", "report_regate", "report_after_repair")
WORKER_PHASE = "typed_audit_worker"

#: A1b, 2026-10-12, `messages.count_tokens` on api.cborg.lbl.gov, claude-opus-5,
#: thinking {adaptive, summarized}: (payload bytes, counted input tokens,
#: placeholder 'x' bytes in that payload). Source: the A1b report
#: `notes/.local_drafts/a1b_calibrated_tokens.json` at commit 10dee83fe, a
#: local commit on no remote branch, so the figures are copied here
#: (sha256 3146ef36c265d4d06058da242c49ccd3804d24b771cc4fe43a1d7496c5924186),
#: payloads built by the A1 harness then (max_paths 192, inventory 32768,
#: 16 workers, every audit output cap 4000). The findings placeholder was
#: 'x' * 16,000 in reconcile_full, report and report_regate; the regate also
#: carried 'x' * 384,000 for the report as written. regate minus report is
#: +382,173 bytes and +383,458 tokens in both projects, about one token per
#: 'x'; with that, report and regate give the same clean ratio
#: (CHORUS 0.3685/0.3686, AI_READI 0.3545/0.3545).
A1B = {
    "CHORUS": {
        "full": (268_470, 97_019, 0), "full_readdress": (293_478, 105_707, 0),
        "full_receipt_completion": (1_883_013, 697_241, 0),
        "typed_audit_omission": (2_108_184, 801_995, 0),
        "typed_audit_worker": (2_460_146, 1_009_249, 0),
        "reconcile_full": (950_762, 362_779, 16_000), "report": (1_058_438, 400_139, 16_000),
        "report_regate": (1_440_611, 783_597, 400_000), "repair_full": (86_828, 35_148, 0),
    },
    "AI_READI": {
        "full": (791_609, 269_756, 0), "full_readdress": (888_821, 302_729, 0),
        "full_receipt_completion": (2_588_964, 933_950, 0),
        "typed_audit_omission": (3_395_253, 1_257_986, 0),
        "typed_audit_worker": (3_983_212, 1_557_087, 0),
        "reconcile_full": (2_181_513, 789_709, 16_000), "report": (2_598_001, 931_279, 16_000),
        "report_regate": (2_980_174, 1_314_737, 400_000), "repair_full": (159_075, 59_459, 0),
    },
}
#: Tokens counted per placeholder 'x' (derivation above).
TOKENS_PER_X = 1.0

#: Calibration family of each sized phase.
FAMILY = {
    "full": "full", "full_readdress": "full_readdress",
    "full_receipt_completion": "full_receipt_completion",
    "full_receipt_completion_after_readdress": "full_receipt_completion",
    WORKER_PHASE: WORKER_PHASE, "typed_audit_omission": "typed_audit_omission",
    # Integration carries the shared context the workers carry.
    "typed_audit_integration": WORKER_PHASE,
    "reconcile_full": "reconcile_full", "report": "report", "report_regate": "report_regate",
    "report_after_repair": "report", "repair_full": "repair_full",
}


def clean_ratio(project, family):
    """Tokens per payload byte with the placeholder bytes and tokens removed."""
    payload_bytes, tokens, x_bytes = A1B[project][family]
    return (tokens - x_bytes * TOKENS_PER_X) / (payload_bytes - x_bytes)


def ratios(project, phase):
    """(ratio used, low, high, basis): the project's own calibration where A1b
    counted it, otherwise the higher of the two calibrated projects."""
    family = FAMILY[phase]
    known = {p: clean_ratio(p, family) for p in A1B}
    low, high = min(known.values()), max(known.values())
    if project in known:
        return known[project], low, high, f"A1b {project} {family}"
    return high, low, high, f"no A1b count for {project}: higher of CHORUS/AI_READI {family}"


def ceiling(phase):
    if phase == WORKER_PHASE:
        return WORKER_CEILING_TOKENS
    if phase in REPORT_PHASES:
        return REPORT_CEILING_TOKENS
    return ROUTE_WINDOW_TOKENS


def estimate(project, phase, payload_bytes, max_output_tokens, placeholder_tokens=0):
    """Byte-based estimate against the phase's ceiling; never a PASS."""
    ratio, low, high, basis = ratios(project, phase)
    inputs = round(payload_bytes * ratio) + placeholder_tokens
    in_flight = inputs + max_output_tokens
    limit = ceiling(phase)
    return {"payload_bytes": payload_bytes, "ratio": round(ratio, 4), "ratio_basis": basis,
            "ratio_range": [round(low, 4), round(high, 4)],
            "placeholder_tokens": placeholder_tokens, "estimated_input_tokens": inputs,
            "max_output_tokens": max_output_tokens, "estimated_in_flight_tokens": in_flight,
            "estimated_in_flight_range": [round(payload_bytes * low) + placeholder_tokens + max_output_tokens,
                                          round(payload_bytes * high) + placeholder_tokens + max_output_tokens],
            "ceiling_tokens": limit, "estimated_clearance_tokens": limit - in_flight,
            "verdict": "estimate_fits" if in_flight <= limit else "estimate_exceeds"}


#: Phase-1 originals used as stand-ins: generic_v10 has no records yet. The
#: plan names the first CHORUS and AI_READI entries (step A1, Inputs); the
#: other replicates measure record-size sensitivity. VOICE_PEDIATRIC has no
#: record, so VOICE's records stand in with VOICE_PEDIATRIC's own bundle,
#: manifest and context (a proxy, labelled as one). AI_READI's 2026-09-04f
#: rep1 record is left out: it carries three top-level `source_caveats` and
#: is declared invalid by its own validation block (#1029).
RUNS = {
    "CHORUS": ["2026-09-12_claude-opus-5-api-generic-v9_rep1", "2026-09-04f_claude-opus-5-api-generic-v8_rep1",
               "2026-09-04f_claude-opus-5-api-generic-v8_rep2", "2026-09-04f_claude-opus-5-api-generic-v8_rep3"],
    "AI_READI": ["2026-09-04g_claude-opus-5-api-generic-v8_rep2", "2026-09-04g_claude-opus-5-api-generic-v8_rep1",
                 "2026-09-04g_claude-opus-5-api-generic-v8_rep3"],
    "CM4AI": ["2026-09-04g_claude-opus-5-api-generic-v8_rep1", "2026-09-04g_claude-opus-5-api-generic-v8_rep2",
              "2026-09-04g_claude-opus-5-api-generic-v8_rep3"],
    "VOICE": ["2026-09-04f_claude-opus-5-api-generic-v8_rep1", "2026-09-04f_claude-opus-5-api-generic-v8_rep2",
              "2026-09-04f_claude-opus-5-api-generic-v8_rep3"],
}
PROXY = {"VOICE_PEDIATRIC": "VOICE", "KIDS_FIRST": "AI_READI"}
#: Projects whose inputs live outside `data/preprocessed/`. Kids First's
#: bundle, chunk manifest and source manifest are in its canary directory.
#: It has no A5d omission context, so a root-only draft is synthesized with
#: the A3 builder's `build_draft_context` (a few KB next to MB-sized
#: requests), and it uses the neutral profile (A19-reg). It has no record,
#: so AI_READI's, the largest, stand in.
EXTERNAL = {"KIDS_FIRST": {"dir": "notes/matched_cborg_2026-09-13/kids_first",
                           "bundle": "KIDS_FIRST_preprocessed.txt", "manifest": "chunks.yaml",
                           "source_manifest": "manifest.yaml", "profile": "neutral"}}
PROJECTS = ("CHORUS", "AI_READI", "CM4AI", "VOICE", "VOICE_PEDIATRIC", "KIDS_FIRST")

#: (max_paths, max_inventory_bytes, max_workers). G2 is the A3 draft default
#: and the A1b setting; G1 is typed.prepare's default.
GRID = {
    "G1": (96, 16_384, 16), "G2": (192, 32_768, 16), "G3": (384, 65_536, 16),
    "G4": (192, 32_768, 8), "G5": (384, 65_536, 4), "G6": (768, 131_072, 2),
}


#: Connection attempts the blocked socket refused during this process.
NETWORK_ATTEMPTS = []


def block_network():
    def forbidden(*args, **kwargs):
        NETWORK_ATTEMPTS.append(repr(args[1:2])[:120])
        raise RuntimeError("offline sizing must not open a network connection")
    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.create_connection = forbidden


def foreign_path(entry, root):
    """Whether an import-path entry could supply `data_sheets_schema` or
    `scripts` from somewhere other than `root` or `root/src`."""
    root = Path(root).resolve()
    try:
        path = Path(entry or ".").resolve()
    except OSError:
        return False
    return path not in {root, root / "src"} and (
        (path / "data_sheets_schema").is_dir() or (path / "scripts").is_dir())


def load(root):
    """Import the runtime from `root` only.

    `data_sheets_schema` and `scripts` are namespace packages, and an editable
    install puts another checkout's `src` on the path, so a module missing
    from `root` would silently load from that checkout. Every other location
    is removed first, and every loaded module is checked afterwards.
    """
    root = Path(root).resolve()
    sys.path[:] = [entry for entry in sys.path if not foreign_path(entry, root)]
    for entry in (str(root), str(root / "src")):
        if entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)
    from data_sheets_schema import api_runner as api, receipt_completion as rc, shared_generation as sg
    from data_sheets_schema import audit_batches, evidence_assertions as evidence, snapshot_store
    from data_sheets_schema import typed_audit as typed, typed_audit_runtime as tar
    from data_sheets_schema import usage_ledger as ledger
    from data_sheets_schema.cli.api import ARMS
    try:
        from scripts.build_api_registrations import DEFAULT_AUDIT_LIMITS, build_draft_context, build_registration
    except ImportError as exc:
        raise SystemExit(f"{root} has no A3 registration builder (scripts/build_api_registrations.py, #5095): {exc}")
    strays = sorted(name for name, module in list(sys.modules.items())
                    if name.split(".")[0] in ("data_sheets_schema", "scripts") and getattr(module, "__file__", None)
                    and not Path(module.__file__).resolve().is_relative_to(root))
    if strays:
        raise SystemExit(f"modules loaded from outside {root}: {strays}")
    return SimpleNamespace(root=root, api=api, rc=rc, sg=sg, snapshot_store=snapshot_store, typed=typed,
                           tar=tar, ledger=ledger, audit_batches=audit_batches, evidence=evidence, ARMS=ARMS,
                           DEFAULT_AUDIT_LIMITS=DEFAULT_AUDIT_LIMITS,
                           build_registration=build_registration, build_draft_context=build_draft_context)


def loaded_from(root):
    """Every runtime module the sweep used must still be under `root`."""
    return sorted(name for name, module in list(sys.modules.items())
                  if name.split(".")[0] in ("data_sheets_schema", "scripts") and getattr(module, "__file__", None)
                  and not Path(module.__file__).resolve().is_relative_to(root))


def run_files(root, project, label):
    """The staged run's files, by role; a missing optional file is None."""
    core = root / "data/d4d_concatenated/claudecode_api_core" / label
    full = root / "data/d4d_concatenated/claudecode_api" / label
    pick = lambda *paths: next((p for p in paths if p.is_file()), None)
    return {"original_full": core / "intermediate" / f"{project}_full.yaml",
            "original_core": core / "intermediate" / f"{project}_core.yaml",
            "receipt": core / f"{project}_coverage_receipt.yaml",
            "reconciled_full": pick(core / "intermediate" / f"{project}_reconcile_full.yaml",
                                    full / f"{project}_d4d.yaml"),
            "completed_core": pick(core / "intermediate" / f"{project}_reconcile_core.yaml",
                                   core / f"{project}_d4d_core.yaml"),
            "report": pick(core / "intermediate" / f"{project}_report.md")}


def inputs_for(root, project):
    """(bundle, chunk manifest, context or None to synthesize, missing paths)."""
    if project in EXTERNAL:
        source = EXTERNAL[project]
        base = root / source["dir"]
        paths = [base / source["bundle"], base / source["manifest"], base / source["source_manifest"]]
        return paths[0], paths[1], None, [str(p.relative_to(root)) for p in paths if not p.is_file()]
    bundle = root / f"data/preprocessed/concatenated/{project}_preprocessed.txt"
    manifest = root / f"data/preprocessed/chunks/{project}_chunks.yaml"
    context = root / f"data/omission_contexts/{project.lower()}_omission_context.json"
    missing = [str(p.relative_to(root)) for p in (bundle, manifest, context) if not p.is_file()]
    return bundle, manifest, context, missing


@contextlib.contextmanager
def offline_receipt_and_index(m):
    """Receipt completion's recovery needs a live run's results, so it is an
    inert stand-in, as in the A1 harness. The integration tail is rendered as
    `typed.index` renders it: the workers' saved envelopes (each answer as a
    base64 blob) and the proposal index built from them, which appears twice.
    Only the omission check is inert, since no omission response exists
    offline."""
    saved_recover, saved_index = m.rc.recover, m.typed.index
    m.rc.recover = lambda s, **kw: {"input_identity": s.input_identity(),
        "registration": m.rc.registration_identity(s), "journal": {"result": "scratch_result_artifact.json"},
        "unsupported_audit_candidates": []}

    def index(packet, workers, omission, derivations=None):
        inner = m.typed._workers(packet, workers, derivations=derivations) if workers else {}
        proposals = m.typed._index(packet, inner) if inner else {}
        check = {"protocol_complete": True, "declared_candidates": []}
        payload = {"stage": "integration", "packet_sha256": packet["sha256"],
                   "shared_context": packet["requests"]["shared_context"], "proposal_index": proposals,
                   "workers": {key: raw.decode("utf-8") for key, raw in workers.items()},
                   "omission_response": (omission or b"").decode("utf-8"), "omission_check": check,
                   "output_contract": packet["contracts"]["integration"]}
        return {"kind": "typed_audit_index_v1", "packet_sha256": packet["sha256"], "index": proposals,
                "omission_check": check, "integration_request": {"kind": "typed_audit_integration_request_v1",
                "payload": payload, "request_sha256": "0" * 64}, "sha256": "0" * 64}
    m.typed.index = index
    try:
        yield
    finally:
        m.rc.recover, m.typed.index = saved_recover, saved_index


_VIEWS = {}


def conform_record(text, schema_path):
    """Make a stand-in record's cardinality match the current schema.

    The typed audit's owner traversal (audit_omissions._owners) refuses a
    value whose list-ness differs from its slot's `multivalued`, and receipt
    completion's linkml validation refuses the same records earlier. The
    write-time normaliser lists scalars in multivalued string slots at any
    depth, except on a line that opens a list item (`- slot: value`); it
    skips multivalued slots of other ranges, and nothing unwraps or joins a
    list in a single-valued slot. A scalar in a multivalued slot is wrapped, a one-item
    list in a single-valued slot unwrapped, and a list of several scalars in
    a single-valued slot joined into one string (the same text, for
    sizing); anything else is left and counted as unfixable. Edits go
    through a round-trip YAML load and dump, which keeps the rest of the
    record's bytes: a plain re-dump shrank these records by 7-8%, which
    would understate every request that carries them. Returns
    (text, edits, unfixable).
    """
    import io
    from linkml_runtime.utils.schemaview import SchemaView
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedSeq
    from ruamel.yaml.util import load_yaml_guess_indent
    view = _VIEWS.get(schema_path)
    if view is None:
        view = _VIEWS[schema_path] = SchemaView(str(schema_path))
    slots_of, classes = {}, set(view.all_classes())
    _, indent, sequence_indent = load_yaml_guess_indent(text)
    yaml_rt = YAML(typ="rt")
    yaml_rt.preserve_quotes = True
    yaml_rt.width = 10**9
    # Keep the record's own indentation ('  - item' or '- item').
    yaml_rt.indent(mapping=sequence_indent or 2, sequence=indent or 2, offset=sequence_indent or 0)
    record = yaml_rt.load(text)
    edits, unfixable = [], []

    def walk(value, cls, path):
        if cls not in slots_of:
            slots_of[cls] = {str(s.name): s for s in view.class_induced_slots(cls)}
        for field, item in list(value.items()):
            slot = slots_of[cls].get(field)
            if slot is None:
                # A slot the current class does not declare: the traversal
                # refuses it, and a valid generic_v10 record cannot carry it.
                del value[field]
                edits.append(f"{path}/{field} (undeclared in {cls}, removed)")
                continue
            if item is None:
                continue
            many, here = bool(slot.multivalued), f"{path}/{field}"
            if many and not isinstance(item, list):
                value[field] = item = CommentedSeq([item])
                edits.append(here + " (wrapped)")
            elif not many and isinstance(item, list):
                if len(item) == 1:
                    value[field] = item = item[0]
                    edits.append(here + " (unwrapped)")
                elif all(not isinstance(x, (dict, list)) for x in item):
                    value[field] = item = " ".join(str(x) for x in item)
                    edits.append(here + " (joined)")
                else:
                    unfixable.append(here)
                    continue
            if slot.range in classes:
                members = list(enumerate(item)) if isinstance(item, list) else [(None, item)]
                for index, member in members:
                    if isinstance(member, dict):
                        walk(member, slot.range, here if index is None else f"{here}/{index}")
    if isinstance(record, dict):
        walk(record, "Dataset", "")
    if not edits:
        return text, edits, unfixable
    buffer = io.StringIO()
    yaml_rt.dump(record, buffer)
    return buffer.getvalue(), edits, unfixable


def carry_receipt(root, receipt_text, manifest_path):
    """Carry a receipt written against an earlier bundle onto today's manifest.

    AI_READI's v8 receipts pin bundle d22b61a9; #5042 rebuilt the bundle
    (1a58ad7b) without the RO-Crate chunks, and receipt validation refuses a
    receipt naming another bundle. Each entry moves to the chunk with the
    same sha256 (the preamble to the preamble), entries for chunks that no
    longer exist are dropped, a new chunk with no counterpart is marked
    nothing_relevant, and `redundant_with` lists are remapped. Returns
    (text, info); info is None when the receipt already names this bundle.
    """
    import subprocess
    import yaml
    current = yaml.safe_load(Path(manifest_path).read_text(encoding="utf-8"))
    pinned = yaml.safe_load(receipt_text)["bundle_md5"]
    if pinned == current["bundle_md5"]:
        return receipt_text, None
    relative = str(Path(manifest_path).resolve().relative_to(root))
    for commit in subprocess.run(["git", "-C", str(root), "log", "--format=%H", "--", relative],
                                 capture_output=True, text=True, check=True).stdout.split():
        candidate = yaml.safe_load(subprocess.run(["git", "-C", str(root), "show", f"{commit}:{relative}"],
                                                  capture_output=True, text=True, check=True).stdout)
        if candidate.get("bundle_md5") == pinned:
            text, info = remap_receipt(receipt_text, candidate, current)
            return text, {**info, "manifest_commit": commit}
    raise ValueError(f"no manifest in history for receipt bundle {pinned}")


def remap_receipt(receipt_text, old, current):
    """carry_receipt's mapping from the receipt's manifest `old` to `current`."""
    import io
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap
    rt = YAML(typ="rt")
    rt.preserve_quotes = True
    rt.width = 10**9
    receipt = rt.load(receipt_text)
    if receipt["bundle_md5"] != old["bundle_md5"]:
        raise ValueError("receipt does not name the old manifest's bundle")
    new_by_sha = {c["sha256"]: c["id"] for c in current["chunks"]}
    preamble = {c["id"] for c in current["chunks"] if c.get("source") == "<preamble>"}
    moved = {}
    for chunk in old["chunks"]:
        if chunk.get("source") == "<preamble>" and preamble:
            moved[chunk["id"]] = next(iter(preamble))
        elif chunk["sha256"] in new_by_sha:
            moved[chunk["id"]] = new_by_sha[chunk["sha256"]]
    entries, dropped = {}, []
    for entry in receipt["chunks"]:
        target = moved.get(entry["id"])
        if target is None:
            dropped.append(entry["id"])
            continue
        entry["id"] = target
        if "chunks" in entry:
            kept = [moved[c] for c in entry["chunks"] if c in moved]
            if kept:
                entry["chunks"] = kept
            else:
                for key in [k for k in entry if k not in ("id",)]:
                    del entry[key]
                entry["status"] = "nothing_relevant"
                entry["reason"] = "Redundant with a chunk #5042 removed (sizing stand-in)."
        entries[target] = entry
    added = []
    chunks = []
    for chunk in current["chunks"]:
        if chunk["id"] in entries:
            chunks.append(entries[chunk["id"]])
        else:
            added.append(chunk["id"])
            filler = CommentedMap()
            filler["id"], filler["status"] = chunk["id"], "nothing_relevant"
            filler["reason"] = "No counterpart in the receipt's bundle (sizing stand-in)."
            chunks.append(filler)
    receipt["bundle_md5"] = current["bundle_md5"]
    receipt["chunks"] = chunks
    buffer = io.StringIO()
    rt.dump(receipt, buffer)
    return buffer.getvalue(), {"from_bundle_md5": old["bundle_md5"], "to_bundle_md5": current["bundle_md5"],
                               "dropped": dropped, "added": added, "moved": len(entries)}


def minimal_receipt(manifest_path):
    """A receipt naming every chunk nothing_relevant: for a proxy project whose
    stand-in record's receipt belongs to another bundle. It is smaller than a
    real receipt, so a proxy's estimate understates by that difference."""
    import yaml
    current = yaml.safe_load(Path(manifest_path).read_text(encoding="utf-8"))
    lines = [f"bundle_md5: {current['bundle_md5']}", "chunks:"]
    for chunk in current["chunks"]:
        lines += [f"- id: {chunk['id']}", "  status: nothing_relevant",
                  "  reason: Proxy run with no receipt of its own (sizing stand-in)."]
    return "\n".join(lines) + "\n"


def stage_run(m, project, files, bundle, manifest, context, limits, workdir, label, *, proxy=False):
    """Copy the originals into a scratch run, register it, return (spec, reg, settings, staging)."""
    run_dir = workdir / f"{project.lower()}_run"
    (run_dir / "intermediate").mkdir(parents=True)
    audit_limits = copy.deepcopy(m.DEFAULT_AUDIT_LIMITS)
    audit_limits.update(limits)
    external = {}
    if project in EXTERNAL:
        source = EXTERNAL[project]
        source_manifest = m.root / source["dir"] / source["source_manifest"]
        context = workdir / f"{project.lower()}_draft_omission_context.json"
        m.build_draft_context(project, source_manifest_path=source_manifest, context_path=context,
                              write_to_disk=True)
        external = {"source_manifest_path": source_manifest, "profile_name": source["profile"]}
    reg = m.build_registration(project=project, label=label, arm="baseline",
        registration_path=workdir / f"{project}_registration.json", context_path=context,
        bundle_path=bundle, chunk_manifest_path=manifest, audit_limits=audit_limits, write_to_disk=True,
        **external)
    # Each record passes through the runner's write-time normaliser, as every
    # record the generic_v10 runner writes does, then conform_record.
    staging = {}
    for role, name in (("original_full", f"{project}_full.yaml"), ("original_core", f"{project}_core.yaml")):
        raw = files[role].read_bytes().decode("utf-8")
        text = m.api.normalise_record_text(raw, phase="full")
        if role == "original_full":
            text, edits, unfixable = conform_record(text, reg["inputs"]["full_schema"]["root"])
        else:
            edits, unfixable = [], []
        staging[role] = {"source_bytes": len(raw.encode()), "staged_bytes": len(text.encode()),
                         "conformance_edits": edits, "unfixable": unfixable}
        for target in (run_dir / "intermediate" / name, run_dir / name):
            target.write_bytes(text.encode("utf-8"))
    receipt_raw = files["receipt"].read_bytes().decode("utf-8")
    if proxy:
        receipt_text, carried = minimal_receipt(manifest), "minimal receipt: proxy record, another bundle"
    else:
        receipt_text, carried = carry_receipt(m.root, receipt_raw, manifest)
    staging["receipt"] = {"source_bytes": len(receipt_raw.encode()), "staged_bytes": len(receipt_text.encode()),
                          "carried": carried}
    (run_dir / f"{project}_coverage_receipt.yaml").write_bytes(receipt_text.encode("utf-8"))
    # The run specification as production reads it from a registration
    # (offline_sizing._spec_from_registration), with the scratch run directory.
    selected, source = reg["selection"], reg["inputs"]
    spec = m.api.RunSpec(**reg["run"], condition=selected["condition"], condition_stated=True,
        render_version=selected["renderer"], bundle=Path(source["bundle"]["path"]),
        chunk_manifest=Path(source["chunk_manifest"]["path"]),
        manifest=None if source["source_manifest"] is None else Path(source["source_manifest"]["path"]),
        profile=source["profile"]["name"], profile_basis=source["profile"]["basis"],
        runtime=m.api.RUNTIME, provider=reg["runtime"]["provider"],
        shared_generation_version=selected["version"], shared_generation_registration=m.sg.canonical(reg).decode(),
        api_playbook_version=selected["api_playbook_version"],
        receipt_completion_version=selected["receipt_completion_version"],
        receipt_completion_registration=m.sg.canonical(reg["receipt"]).decode(), out_dir=run_dir)
    m.ledger.prepare_usage(spec, resume=False)
    m.ledger.pin_inputs(spec)
    m.snapshot_store.record(spec, f"{project}_full.yaml", run_dir / "intermediate" / f"{project}_full.yaml")
    m.snapshot_store.record(spec, f"{project}_core.yaml", run_dir / "intermediate" / f"{project}_core.yaml")
    model = m.api._model_settings(spec.condition)
    settings = {"name": reg["runtime"]["model"], "temperature": reg["runtime"]["temperature"],
                "thinking": copy.deepcopy(reg["runtime"].get("thinking")), "effort": reg["runtime"].get("effort"),
                "max_tokens": model["max_tokens"]}
    return spec, reg, settings, staging


def cap(m, spec, settings, phase):
    return m.api.phase_max_tokens(spec, phase, settings["max_tokens"], model=settings["name"])


def nbytes(m, payload):
    return len(m.sg.canonical(payload))


#: Tokens per byte assumed for a response floor: 4 bytes a token, the usual
#: figure for English prose and below every ratio A1b counted (0.34-0.41), so
#: a floor in tokens errs low.
FLOOR_TOKENS_PER_BYTE = 0.25


def _compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def floor_variants(plan, worker, *, quote=None):
    """The smallest candidate worker responses, as compact JSON bytes.

    A worker returns one source-review row per assigned path
    (`audit_batches.check_worker`). Here each row is a declared-metadata row
    where the inventory allows one. Otherwise it is one claim with
    one-character source, chunk, quote and reason. The claim quotes the whole
    value, because the terminal source review (`source_review.check`, run at
    assembly) requires a row's claims to quote and cover its value. With
    `quote`, every claim's text is `quote` instead; the worker-stage check
    alone accepts that. The variants are:
    - `supported`: every claim supported, with one document assertion;
    - `revised`: every claim revised with no evidence, plus one finding
      linking them;
    - `mixed`: each row in whichever of those two forms is smaller."""
    by_path = {row["path"]: row for row in plan["inventory"]["values"]}
    forms = []                                   # (path, supported row, revised row or None)
    for path in worker["paths"]:
        row = by_path[path]
        if row["record_metadata_allowed"]:
            forms.append((path, {"path": path, "metadata_reason": "m"}, None))
            continue
        claim = {"text": row["text"] if quote is None else quote, "attributed_to": [], "claim_status": "fact",
                 "reason": "r"}
        forms.append((path, {"path": path, "claims": [{**claim, "verdict": "supported", "source_status": "fact",
                             "evidence": [{"source": "s", "chunk": "c", "quote": "q"}]}]},
                      {"path": path, "claims": [{**claim, "verdict": "revise", "source_status": "unstated",
                       "evidence": []}]}))

    def body(revise):
        rows, linked = [], []
        for path, supported, revised in forms:
            take = revised is not None and revise(path, supported, revised)
            rows.append(revised if take else supported)
            linked += [path] if take else []
        findings = [{"severity": "low", "record": "full", "slot": "s", "issue": "i", "review_paths": linked,
                     "evidence": [{"artifact": "original_full", "path": "/id", "op": "contains", "quote": "q"}]}]
        return _compact({"findings": findings if linked else [], "summary": "s", "source_review": {
            "artifact": "original_full", "sha256": plan["original_full_sha256"], "values": rows}})
    # A revised row also costs its path in the finding's review_paths.
    smaller = lambda path, supported, revised: len(_compact(revised)) + len(_compact(path)) + 1 < len(
        _compact(supported))
    return {"supported": body(lambda *a: False), "revised": body(lambda *a: True), "mixed": body(smaller)}


def response_floor(plan, worker, check):
    """A floor under any answer the terminal source review accepts, in bytes.

    The smallest of `floor_variants` that `check(raw, plan, worker_id)` (the
    worker-stage check) accepts. Its claims quote and cover every value, as the
    terminal check requires, and every other string is one character, which no
    real answer's sources, quotes and reasons can be. The worker-stage check
    itself does not test quoting: `worker_check_minimum` is the smallest
    answer it accepts, with one-character claims."""
    def smallest(variants):
        best, errors = None, {}
        for name, raw in variants.items():
            report = check(raw, plan, worker["id"])
            if report["passed"]:
                if best is None or len(raw) < best["bytes"]:
                    best = {"bytes": len(raw), "variant": name, "passed": True}
            else:
                errors[name] = [e.get("code") for e in report.get("errors", [])][:3]
        return best or {"bytes": None, "passed": False, "errors": errors}
    return {**smallest(floor_variants(plan, worker)),
            "worker_check_minimum": smallest(floor_variants(plan, worker, quote="t"))}


def floor_tokens(floor_bytes):
    return None if floor_bytes is None else math.ceil(floor_bytes * FLOOR_TOKENS_PER_BYTE)


def floor_assembly(audit_batches, plan):
    """The assembled audit the runner carries as "Audit findings"
    (`audit_batches.assemble`'s canonical JSON), built from every worker's
    smallest all-supported response and an integration that keeps every row.
    Within about 1% of the smallest variants, which need finding decisions.
    None when assembly refuses. A real audit is larger."""
    proposals = {w["id"]: floor_variants(plan, w)["supported"] for w in plan["workers"]}
    try:
        index = audit_batches.build_index(plan, proposals, version=2)
        integration = {"kind": "audit_integration_v2", "proposal_index_sha256": index["sha256"],
                       "retain_other_rows_from_index_sha256": index["sha256"], "row_replacements": [],
                       "finding_decisions": [], "new_findings": [], "summary": "s", "omission_dispositions": []}
        raw, _ = audit_batches.assemble(plan, proposals, _compact(integration), version=2)
    except (audit_batches.AuditBatchError, ValueError):
        return None
    return raw.decode("utf-8")


#: The terminal source review's findings about a claim's text: its quoting
#: and its coverage of the value (`source_review.check`).
QUOTE_COVERAGE = ("claim text must quote this value, retaining case and punctuation",
                  "a numeric, boolean or date claim must quote its complete scalar value",
                  "source review omits part of the value's text", "populated value was not source reviewed")


def terminal_check(m, spec, packet, audit_text):
    """Run the terminal check `typed.assemble` applies
    (`evidence_assertions.check_audit`) on an assembled floor audit, and sort
    its findings. The floor's claims must quote and cover every value, so it
    should have no quoting or coverage finding. Its one-character evidence
    must fail the evidence assertions."""
    raw, _ = m.typed._open(packet, derivations=m.tar._derivations(spec))
    chunks, _ = m.evidence.source_chunks_from_bytes(raw["bundle"], raw["manifest"])
    artifacts = {key: raw[key].decode("utf-8") for key in ("original_full", "original_core") if key in raw}
    checked = m.evidence.check_audit(json.loads(audit_text), artifacts=artifacts, chunks=chunks,
        protocol_version=7, source_manifest_raw=raw.get("source_manifest"), project=packet["project"])
    return sort_findings(checked["findings"])


def sort_findings(findings):
    quoting = [f for f in findings if f.get("detail") in QUOTE_COVERAGE]
    return {"findings": len(findings), "quote_or_coverage": len(quoting),
            "quote_or_coverage_examples": [f.get("detail") for f in quoting[:3]],
            "other_kinds": sorted({str(f.get("kind")) for f in findings if f not in quoting})}


def integration_alternatives(m, workers, omission, integration):
    """Integration's request as `larger_carry` alternatives (see
    `measure_typed`). One is an empty carry, with every worker answer and the
    omission response at their caps. The other carries the floor answers as
    saved envelopes, with the proposal index built from them (real bytes),
    and only the omission response at its cap."""
    out = [(nbytes(m, integration[0]), integration[0]["max_tokens"],
            sum(w["max_output_tokens"] for w in workers) + omission["max_tokens"], "registered output caps",
            integration[0])]
    if len(integration) > 1:
        out.append((nbytes(m, integration[1]), integration[1]["max_tokens"], omission["max_tokens"],
                    "workers' smallest responses, as saved envelopes", integration[1]))
    return out


def larger_carry(project, phase, alternatives):
    """Of one request built with different carries, as (payload bytes,
    max_tokens, placeholder tokens, basis, ...), the one with the larger
    estimate. When the floor wins, the figure is a lower bound for the
    carry: it can show that a request exceeds, never that it fits."""
    return max(alternatives, key=lambda a: estimate(project, phase, a[0], a[1], placeholder_tokens=a[2])[
        "estimated_in_flight_tokens"])


def measure_typed(m, spec, settings):
    """Workers, omission and integration through prepare_packet/build_request.

    Integration is built twice: with no worker answers (sized later at their
    caps), and, when every worker's floor passes, with each floor answer as
    the envelope the runtime saves (`typed.capture_response`)."""
    check = lambda raw, plan, worker_id: m.audit_batches.check_worker(raw, plan, worker_id, version=2)
    with offline_receipt_and_index(m):
        packet = m.tar.prepare_packet(spec)
        rows, largest, envelopes = [], None, {}
        for worker in packet["plan"]["workers"]:
            stage = {"phase": m.tar.WORKER_PHASE, "worker_id": worker["id"]}
            _, payload, inner = m.tar.build_request(spec, packet, stage, workers={}, omission=None,
                                                    settings=settings)
            floor = response_floor(packet["plan"], worker, check)
            rows.append({"worker_id": worker["id"], "paths": len(worker["paths"]),
                         "inventory_bytes": worker["inventory_bytes"], "payload_bytes": nbytes(m, payload),
                         "max_output_tokens": payload["max_tokens"], "response_floor": floor})
            if floor["passed"]:
                answer = floor_variants(packet["plan"], worker)[floor["variant"]]
                envelopes[worker["id"]] = m.typed.capture_response(inner, answer)
            if largest is None or rows[-1]["payload_bytes"] > nbytes(m, largest):
                largest = payload
        _, omission, _ = m.tar.build_request(spec, packet, {"phase": m.tar.OMISSION_PHASE}, workers={},
                                             omission=None, settings=settings)
        integration = [m.tar.build_request(spec, packet, {"phase": m.tar.INTEGRATION_PHASE}, workers=answers,
                                           omission=b"", settings=settings)[1]
                       for answers in ([{}, envelopes] if len(envelopes) == len(rows) else [{}])]
    return packet, rows, omission, integration, largest


TYPED_HEADER = "# Exact typed stage request\n\n"
#: Induced-slot keys a trimmed schema context (option S5) would drop: the
#: classes using the slot, constants, and duplicates of the name or class.
TRIMMED_SLOT_KEYS = ("domain_of", "from_schema", "alias", "owner", "@type", "slot_uri", "annotations",
                     "exact_mappings")


def components(m, payload):
    """Bytes each part contributes to `payload`, found by emptying that part
    and re-encoding the whole body: exact for bytes. Covers every text part
    of every message (keyed by its first line), the schema context's
    members, and, in a typed stage request, the members of its shared
    context, worker tail or omission payload, each re-encoded through the
    same JSON levels the builder uses."""
    total = nbytes(m, payload)
    result = {"total": total, "parts": {}}

    def emptied(mi, pi, text):
        trimmed = copy.deepcopy(payload)
        trimmed["messages"][mi]["content"][pi]["text"] = text
        return total - nbytes(m, trimmed)
    if isinstance(payload.get("system"), str) and payload["system"]:
        trimmed = copy.deepcopy(payload)
        trimmed["system"] = ""
        result["parts"]["system"] = total - nbytes(m, trimmed)
    for mi, message in enumerate(payload["messages"]):
        if not isinstance(message["content"], list):
            continue
        for pi, part in enumerate(message["content"]):
            text = part.get("text") if isinstance(part, dict) else None
            if not isinstance(text, str) or not text:
                continue
            label = f"m{mi}.{pi}: " + text.split("\n", 1)[0][:70]
            result["parts"][label] = emptied(mi, pi, "")
            if text.startswith(m.sg.SCHEMA_CONTEXT_HEADER):
                head = m.sg.SCHEMA_CONTEXT_HEADER
                context = json.loads(text[len(head):])

                def context_without(change, context=context, mi=mi, pi=pi, head=head):
                    changed = copy.deepcopy(context)
                    change(changed)
                    return emptied(mi, pi, head + m.sg.canonical(changed).decode("utf-8"))
                result["schema_context"] = {
                    "total": result["parts"][label],
                    "classes": context_without(lambda c: c.update(classes={})),
                    "classes_trimmed": context_without(lambda c: c.update(classes={
                        cls: {name: {k: v for k, v in slot.items() if k not in TRIMMED_SLOT_KEYS}
                              for name, slot in slots.items()} for cls, slots in c["classes"].items()})),
                    "class_count": len(context["classes"]),
                    "owners": context_without(lambda c: c.update(owners=[])),
                    "owner_yaml": context_without(lambda c: [o.update(whole_value_yaml="") for o in c["owners"]]),
                    "owner_typed_tree": context_without(
                        lambda c: [o.update(whole_value_identity=None) for o in c["owners"]]),
                    "nested_owners": context_without(lambda c: c.update(owners=c["owners"][:1])),
                    "owner_count": len(context["owners"])}
            if text.startswith("{"):
                # A JSON part (receipt completion's inputs): each large member.
                try:
                    document = json.loads(text)
                except ValueError:
                    document = None
                if isinstance(document, dict):
                    # Both sides re-serialized alike, so formatting cancels.
                    serialized = lambda d: json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    whole = emptied(mi, pi, serialized(document))
                    result["json"] = {
                        "json." + key: emptied(mi, pi, serialized({k: (None if k == key else v)
                                                                    for k, v in document.items()})) - whole
                        for key in [k for k, v in document.items() if len(json.dumps(v, ensure_ascii=False)) > 1024]}
            if text.startswith(TYPED_HEADER):
                inner = json.loads(text[len(TYPED_HEADER):])
                # Integration nests its request one level down.
                route = ("integration_request", "payload") if "integration_request" in inner else ("payload",)
                body = inner
                for key in route:
                    body = body.get(key, {})

                def inner_without(edit, inner=inner, mi=mi, pi=pi, route=route):
                    changed = copy.deepcopy(inner)
                    target = changed
                    for key in route:
                        target = target[key]
                    edit(target)
                    return emptied(mi, pi, TYPED_HEADER + m.sg.canonical(changed).decode())
                typed = {}
                if isinstance(body.get("shared_context"), str):
                    shared = json.loads(body["shared_context"])
                    for key in [k for k, v in shared.items() if v is not None]:
                        def edit(p, key=key):
                            changed = json.loads(p["shared_context"])
                            changed[key] = None
                            p["shared_context"] = m.typed._json(changed).decode("utf-8")
                        typed["shared." + key] = inner_without(edit)
                # A worker's `stage` is embedded JSON; integration's is the plain name "integration".
                if isinstance(body.get("stage"), str) and body["stage"].startswith("{"):
                    tail = json.loads(body["stage"])
                    for key in ("inventory", "assignment"):
                        if key in tail:
                            def edit(p, key=key):
                                changed = json.loads(p["stage"])
                                changed[key] = (None if key != "inventory" else
                                                {**changed[key], "values": []})
                                p["stage"] = m.typed._json(changed).decode("utf-8")
                            typed["stage." + key] = inner_without(edit)
                for key in [k for k, v in body.items() if k not in ("shared_context", "stage") and v]:
                    if isinstance(body[key], (dict, list, str)) and len(json.dumps(body[key])) > 1024:
                        typed["payload." + key] = inner_without(lambda p, key=key: p.update({key: None}))
                result["typed"] = typed
    return result


def findings_bound(worker_count, audit_limits):
    """Tokens the carried "Audit findings" can hold: the runner carries the
    assembled audit (`outcome.audit`, from `batches.assemble`), which merges
    every worker's source-review rows and findings with the integration
    output, so its bound is every worker's output cap plus integration's."""
    return worker_count * audit_limits["worker_output_tokens"] + audit_limits["integration_output_tokens"]


def delivered_body(record, receipt, mark):
    """The full phase's entire delivered body, as production keeps it before
    `split_receipt` (`api_runner`, #1048): the record, the receipt mark line,
    then the receipt."""
    return f"{record.rstrip(chr(10))}\n{mark}\n{receipt}"


def measure_ordinary(m, project, spec, settings, reg, files, worker_count, audit_floor=None):
    """Ordinary phases as the runner builds them (A1: build_phase, the
    PHASE_NEEDS carries, _append_regate, build_repair + generation_context).
    `worker_count` sizes the assembled audit the runner carries at the
    registered caps' bound; `audit_floor`, when given, is that audit at its
    smallest. Returns {phase: (payload, placeholder tokens)} and the audit
    carry basis of each phase that carries it."""
    bases = {}
    read = lambda path: path.read_bytes().decode("utf-8") if path is not None else ""
    # The staged originals, as the typed stages saw them.
    run_dir = Path(spec.out_dir)
    full = read(run_dir / "intermediate" / f"{project}_full.yaml")
    core = read(run_dir / "intermediate" / f"{project}_core.yaml")
    receipt = read(run_dir / f"{project}_coverage_receipt.yaml")
    reconciled = read(files["reconciled_full"]) if files["reconciled_full"] else full
    completed = read(files["completed_core"]) if files["completed_core"] else core
    report_text = read(files["report"]) if files["report"] else ""
    findings = findings_bound(worker_count, reg["audit_limits"])
    report_cap = cap(m, spec, settings, "report")
    readdress_cap = min(m.api.READDRESS_MAX_TOKENS, m.api.output_limit(settings["name"]))
    out = {}

    def payload(req, phase, max_tokens=None):
        return m.rc.request_payload(req, settings,
            {"max_output_tokens": max_tokens if max_tokens is not None else cap(m, spec, settings, phase)})

    full_req = m.api.build_phase(spec, "full", carry={})
    out["full"] = (payload(full_req, "full"), 0)
    # The re-address turn and receipt completion both carry the whole
    # delivered body: the record, then the receipt (#1048).
    body = delivered_body(full, receipt, m.api.RECEIPT_MARK)
    unresolved = [{"slot": "placeholder", "detail": "one unresolved receipt entry"}]
    readdress = m.api.build_readdress(full_req, body, unresolved)
    out["full_readdress"] = (payload(readdress, "full_readdress", readdress_cap), 0)

    def completion(transcript):
        inputs = {"record": full, "receipt": receipt,
                  "manifest": Path(spec.chunk_manifest).read_text(encoding="utf-8"),
                  "bundle": Path(spec.bundle).read_text(encoding="utf-8"), "schema": m.rc.schema_capture(spec),
                  "transcript": transcript, "transcript_pin": "scratch_full_transcript.json",
                  "registration": m.rc.registration_identity(spec),
                  "policy": m.rc.policy_identity(version=spec.receipt_completion_version),
                  "input_identity": spec.input_identity(),
                  "max_output_tokens": reg["receipt"]["max_output_tokens"]}
        request, _ = m.rc.build_request(inputs)
        return m.rc.request_payload(request, settings, m.rc.registration(spec))
    # The transcript remember_exchange keeps: the full exchange, or after a
    # re-address the re-address exchange, whose response is at most its cap.
    exchange = lambda req, response: {"phase": req.phase, "system": req.system, "messages": copy.deepcopy(
        req.messages), "cached_blocks": copy.deepcopy(req.cached_blocks), "response": response,
        "usage_id": "scratch"}
    out["full_receipt_completion"] = (completion(exchange(full_req, body)), 0)
    out["full_receipt_completion_after_readdress"] = (completion(exchange(readdress, "")), readdress_cap)
    # The audit exists only after the typed stages. Each request that carries
    # it is built twice: the carry empty and sized at the registered output
    # caps' bound, and the workers' smallest responses assembled (the least a
    # completed audit carries). The larger estimate is kept.
    carries = [("", findings, "registered output caps")]
    if audit_floor is not None:
        carries.append((audit_floor, 0, "workers' smallest responses, assembled"))

    def audited(phase, cap_phase, build, extra=0, max_tokens=None):
        options = []
        for text, placeholder, basis in carries:
            p = payload(build(text), cap_phase, max_tokens)
            options.append((nbytes(m, p), p["max_tokens"], placeholder + extra, basis, p))
        chosen = larger_carry(project, "report_regate" if phase.startswith("report_regate") else phase, options)
        out[phase] = (chosen[4], chosen[2])
        bases[phase] = chosen[3]
    audited("reconcile_full", "reconcile_full", lambda a: m.api.build_phase(spec, "reconcile_full",
            carry={"Completed full record": full, "Audit findings": a}))
    report_carry = lambda a: {"Audit findings": a, "Original full record": full, "Original core record": core,
                              "Reconciled full record": reconciled, "Completed core record": completed}
    audited("report", "report", lambda a: m.api.build_phase(spec, "report", carry=report_carry(a)))

    def regate(audit, report_as_written):
        request = m.api.build_phase(spec, "report", carry=report_carry(audit))
        m.api._append_regate(request, spec, report_as_written, [])
        return request
    # The regate's contradiction listing is not sized: no cap bounds it, and
    # a regate happens only when it is non-empty (`_gate_report`). The report
    # as written is at most the report cap; a v8 report shows a realistic size.
    audited("report_regate", "report", lambda a: regate(a, ""), extra=report_cap, max_tokens=report_cap)
    audited("report_regate_with_v8_report", "report", lambda a: regate(a, report_text), max_tokens=report_cap)
    repair = m.api.build_repair("full", reconciled,
        errors=["Slot 'data_collection' has validation error: missing required source link"],
        profile=spec.profile_obj, _captured_digest=m.sg.digest_text(spec, "Dataset"))
    repair.messages[0]["content"].insert(-1, {"type": "text", "text": m.sg.generation_context(spec)})
    out["repair_full"] = (payload(repair, "repair_full"), 0)
    return out, bases


def size_one(m, project, label, limits, workdir, *, with_components=False):
    # A proxy project's records are the related project's; stage_run copies
    # them into this project's run under this project's names.
    record_project = PROXY.get(project, project)
    files = run_files(m.root, record_project, label)
    bundle, manifest, context, missing = inputs_for(m.root, project)
    if missing or not files["original_full"].is_file():
        return {"status": "UNKNOWN", "reason": "missing inputs: " + ", ".join(missing or [str(files["original_full"])])}
    run_label = "2026-10-20a_claude-opus-5-api-generic-v10_rep1"
    try:
        spec, reg, settings, staging = stage_run(m, project, files, bundle, manifest, context, limits, workdir,
                                                 run_label, proxy=record_project != project)
    except Exception as exc:                      # noqa: BLE001 - recorded, not hidden
        return {"status": "REFUSED", "reason": f"registration/staging: {type(exc).__name__}: {exc}"}
    result = {"status": "MEASURED", "label": label, "record_project": record_project, "staging": staging,
              "inputs": {role: (str(p.relative_to(m.root)) if p else None) for role, p in files.items()},
              "bundle_bytes": bundle.stat().st_size, "original_full_bytes": files["original_full"].stat().st_size,
              "thinking": settings["thinking"], "stages": {}}
    parts = {}
    limits = reg["audit_limits"]
    result["audit_limits"] = {k: limits[k] for k in ("aggregate_input_tokens", "aggregate_output_tokens",
                              "max_calls", "max_input_tokens_per_call", "worker_output_tokens",
                              "omission_output_tokens", "integration_output_tokens", "max_paths",
                              "max_inventory_bytes", "max_workers")}
    worker_count, result["findings_basis"] = limits["max_workers"], "max_workers: the typed stage was refused"
    audit_floor = None
    try:
        packet, workers, omission, integration, largest = measure_typed(m, spec, settings)
    except Exception as exc:                      # noqa: BLE001
        result["typed"] = {"status": "REFUSED", "reason": f"{type(exc).__name__}: {exc}"}
    else:
        worker_count, result["findings_basis"] = len(workers), "this run's worker count"
        result["typed"] = {"status": "MEASURED", "worker_count": len(workers), "workers": [
            {**w, **estimate(project, WORKER_PHASE, w["payload_bytes"], w["max_output_tokens"])} for w in workers]}
        result["stages"]["typed_audit_omission"] = estimate(project, "typed_audit_omission",
            nbytes(m, omission), omission["max_tokens"])
        if len(integration) > 1:
            audit_floor = floor_assembly(m.audit_batches, packet["plan"])
        chosen = larger_carry(project, "typed_audit_integration",
                              integration_alternatives(m, workers, omission, integration))
        result["stages"]["typed_audit_integration"] = {**estimate(project, "typed_audit_integration", chosen[0],
            chosen[1], placeholder_tokens=chosen[2]), "carry_basis": chosen[3]}
        result["audit_floor_bytes"] = len(audit_floor.encode("utf-8")) if audit_floor is not None else None
        if audit_floor is not None:
            result["audit_floor_terminal_check"] = terminal_check(m, spec, packet, audit_floor)
        parts.update({WORKER_PHASE + " (largest)": largest, "typed_audit_omission": omission,
                      "typed_audit_integration": chosen[4]})
    try:
        ordinary, bases = measure_ordinary(m, project, spec, settings, reg, files, worker_count, audit_floor)
    except Exception as exc:                      # noqa: BLE001
        result["ordinary"] = {"status": "REFUSED", "reason": f"{type(exc).__name__}: {exc}"}
    else:
        for phase, (payload, placeholder) in ordinary.items():
            family_phase = "report_regate" if phase == "report_regate_with_v8_report" else phase
            result["stages"][phase] = estimate(project, family_phase, nbytes(m, payload), payload["max_tokens"],
                                               placeholder_tokens=placeholder)
            if family_phase != phase:
                result["stages"][phase]["phase"] = family_phase
            if phase in bases:
                result["stages"][phase]["carry_basis"] = bases[phase]
            parts[phase] = payload
        result["stages"]["report_after_repair"] = {**result["stages"]["report"], "note": "same request as report, "
            "built from the repaired records; sized here from the reconciled records"}
    if with_components:
        result["components"] = {name: components(m, payload) for name, payload in parts.items()}
    return result


def sweep(root, workdir, projects=PROJECTS, grid=GRID, components_grid="G2", replicate_grid="G2",
          primary_only=False):
    """Every grid on each project's primary record; `replicate_grid` only on
    the other replicates, which measure record-size sensitivity."""
    import hashlib
    import os
    block_network()
    workdir = Path(workdir).resolve()
    # Prompts, schema and other resources resolve from the working directory
    # first (`resources.resource_path`), so the sweep runs from the measured
    # tree, not from wherever it was started.
    root = Path(root).resolve()
    os.chdir(root)
    # A full-phase cap override would silently change every full request.
    override = os.environ.pop("D4D_RECEIPT_FULL_MAX_TOKENS", None)
    m = load(root)
    from data_sheets_schema import resources
    if Path(resources.resource_root()[0]).resolve() != root:
        raise SystemExit(f"resources resolve from {resources.resource_root()[0]}, not {root}")
    workdir.mkdir(parents=True, exist_ok=False)
    results = {"format": "d4d_a1_offline_sizing_sweep_v1", "root": str(m.root),
               "root_head": _head(m.root), "root_dirty_paths": _dirty(m.root),
               "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "cleared_environment": {"D4D_RECEIPT_FULL_MAX_TOKENS": override},
               "ceilings": {"worker": WORKER_CEILING_TOKENS,
               "report_family": REPORT_CEILING_TOKENS, "window": ROUTE_WINDOW_TOKENS},
               "calibration": {p: {f: {"bytes": v[0], "tokens": v[1], "x_bytes": v[2],
                               "clean_ratio": round(clean_ratio(p, f), 4)} for f, v in A1B[p].items()} for p in A1B},
               "grid": {k: dict(zip(("max_paths", "max_inventory_bytes", "max_workers"), v)) for k, v in grid.items()},
               "projects": {}}
    for project in projects:
        record_project = PROXY.get(project, project)
        labels = RUNS.get(record_project, [])
        if not labels:
            results["projects"][project] = {"status": "UNKNOWN", "reason": "no bundle, context or record to stage"}
            continue
        rows = {}
        for label in (labels[:1] if primary_only else labels):
            selected = grid if label == labels[0] else {k: v for k, v in grid.items() if k == replicate_grid}
            for name, (paths, inventory, workers) in selected.items():
                work = workdir / f"{project}_{label}_{name}"
                work.mkdir(parents=True)
                rows[f"{label}|{name}"] = size_one(m, project, label,
                    {"max_paths": paths, "max_inventory_bytes": inventory, "max_workers": workers}, work,
                    with_components=(name == components_grid and label == labels[0]))
                print(f"{project} {label} {name}: {_summary(rows[f'{label}|{name}'])}", file=sys.stderr, flush=True)
        results["projects"][project] = {"status": "MEASURED", "record_project": record_project,
                                        "proxy": record_project != project, "primary": labels[0], "runs": rows}
    strays = loaded_from(m.root)
    if strays:
        raise SystemExit(f"modules loaded from outside {m.root} during the sweep: {strays}")
    results["modules_outside_root"] = strays
    # Counted, not assumed: every attempt raised, so a non-empty list also
    # shows up as REFUSED rows.
    results["network_attempts"] = list(NETWORK_ATTEMPTS)
    return results


def _head(root):
    import subprocess
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _dirty(root):
    """Tracked paths that differ from HEAD in the measured tree."""
    import subprocess
    try:
        out = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return [line[3:] for line in out.splitlines() if line.strip()]


def _summary(row):
    if row.get("status") != "MEASURED":
        return f"{row.get('status')}: {row.get('reason')}"
    typed = row.get("typed", {})
    if typed.get("status") != "MEASURED":
        return f"typed {typed.get('status')}: {typed.get('reason')}"
    largest = max(typed["workers"], key=lambda w: w["estimated_in_flight_tokens"])
    return (f"{typed['worker_count']} workers, largest {largest['payload_bytes']:,} B ~"
            f"{largest['estimated_in_flight_tokens']:,} tok in flight ({largest['verdict']})")


#: Compaction options, as parts removed from a measured request: a change to
#: the shared-generation or typed-audit protocol that no one has made. Each
#: is a condition-boundary change (model-facing text), for the owner.
OPTIONS = {
    "S1": ("schema carried once: the typed request's own schema copy dropped, the schema context kept",
           ("typed.shared.schema", "typed.payload.schema", "json.schema")),
    "S2": ("schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept",
           ("schema_context.classes",)),
    "S3": ("S1 plus the full-record inventory repeated in every worker dropped",
           ("typed.shared.schema", "typed.payload.schema", "json.schema", "typed.stage.inventory")),
    "S4": ("S1 plus owners without their typed trees",
           ("typed.shared.schema", "typed.payload.schema", "json.schema", "schema_context.owner_typed_tree")),
    "S5": ("induced-slot definitions trimmed to name, description, range, cardinality and inlining",
           ("schema_context.classes_trimmed",)),
    "S6": ("S1 plus S5", ("typed.shared.schema", "typed.payload.schema", "json.schema",
                          "schema_context.classes_trimmed")),
    "S7": ("S6 plus owners without their typed trees", ("typed.shared.schema", "typed.payload.schema",
           "json.schema", "schema_context.classes_trimmed", "schema_context.owner_typed_tree")),
}


def typed_aggregate(project, run, components=None, keys=()):
    """Estimated input tokens across one run's typed calls: every worker, the
    omission stage and integration (with the responses it carries). Before
    each typed stage the runtime refuses it when this total would pass the
    registered `aggregate_input_tokens` (`typed_audit_runtime`, about :506).
    With a primary record's `components` and an option's `keys`, the
    option's removal is applied to each request; the shared content a worker
    carries is the same in every worker of a run. None when the typed stages
    were not measured."""
    typed, stages = run.get("typed", {}), run.get("stages", {})
    if typed.get("status") != "MEASURED" or "typed_audit_omission" not in stages:
        return None

    def after(e, phase, stage_key):
        removed = removed_bytes(components[stage_key], keys) if components and keys else 0
        return estimate(project, phase, max(e["payload_bytes"] - removed, 0), e["max_output_tokens"],
                        placeholder_tokens=e.get("placeholder_tokens", 0))["estimated_input_tokens"]
    total = sum(after(w, WORKER_PHASE, WORKER_PHASE + " (largest)") for w in typed["workers"])
    total += after(stages["typed_audit_omission"], "typed_audit_omission", "typed_audit_omission")
    return total + after(stages["typed_audit_integration"], "typed_audit_integration", "typed_audit_integration")


def removed_bytes(parts, keys):
    """Bytes the parts named by `keys` contribute to one request's components."""
    total = 0
    for key in keys:
        section, _, member = key.partition(".")
        value = parts.get(section, {}) if section != "typed" else parts.get("typed", {})
        if section == "typed":
            total += value.get(member, 0)
        elif section == "json":
            total += parts.get("json", {}).get(key, 0)
        else:
            total += value.get(member, 0) if isinstance(value, dict) else 0
    return total


def _fmt(n):
    return f"{n:,}" if isinstance(n, int) else str(n)


def table(results):
    """Markdown tables from a sweep's results, for the A1 note."""
    out = []
    window = results["ceilings"]
    out.append(f"Ceilings: worker {window['worker']:,}; report family {window['report_family']:,}; "
               f"every other request {window['window']:,} (tokens in flight: input plus `max_tokens`).\n")
    for project, block in results["projects"].items():
        out.append(f"### {project}\n")
        if block.get("status") != "MEASURED":
            out.append(f"UNKNOWN: {block.get('reason')}\n")
            continue
        if block.get("proxy"):
            context = ("a root-only draft context synthesized by the A3 builder" if project in EXTERNAL
                       else "its own context")
            out.append(f"Proxy: {block['record_project']}'s records with {project}'s own bundle and chunk "
                       f"manifest, {context}, and a minimal receipt; an estimate for a run that has no record "
                       "yet.\n")
        runs = block["runs"]
        # The primary record carries every grid (results are stored with sorted keys).
        counts = {}
        for key in runs:
            counts[key.split("|")[0]] = counts.get(key.split("|")[0], 0) + 1
        label = block.get("primary") or max(counts, key=lambda k: (counts[k], k == RUNS.get(
            block.get("record_project", project), [None])[0]))
        out.append(f"Primary record `{label}`.\n")
        components_g2 = runs.get(f"{label}|G2", {}).get("components")
        registered = next((r["audit_limits"] for r in runs.values() if r.get("audit_limits")), {})
        allowance = registered.get("aggregate_input_tokens", 4_000_000)
        worker_cap = registered.get("worker_output_tokens", 4_000)
        out.append("| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | "
                   "Est. in flight | Verdict | Assigned inventory per worker B | Typed input, all calls: "
                   "current / S6 / S7 |")
        out.append("|---|---|---|---|---|---|---|---|")
        for key, row in runs.items():
            if not key.startswith(label + "|"):
                continue
            grid = key.split("|")[1]
            limits = results["grid"][grid]
            limit_text = f"{limits['max_paths']} / {limits['max_inventory_bytes']:,} / {limits['max_workers']}"
            typed = row.get("typed", {})
            if row.get("status") != "MEASURED" or typed.get("status") != "MEASURED":
                reason = row.get("reason") or typed.get("reason")
                out.append(f"| {grid} | {limit_text} | refused | | | {reason} | | |")
                continue
            largest = max(typed["workers"], key=lambda w: w["estimated_in_flight_tokens"])
            inventory = [w["inventory_bytes"] for w in typed["workers"]]

            def mark(total):
                return "—" if total is None else f"{total:,}" + (" over" if total > allowance else "")
            totals = [typed_aggregate(project, row)] + [
                typed_aggregate(project, row, components_g2, OPTIONS[o][1]) if components_g2 else None
                for o in ("S6", "S7")]
            out.append(f"| {grid} | {limit_text} | {typed['worker_count']} | {largest['payload_bytes']:,} | "
                       f"{largest['estimated_in_flight_tokens']:,} | {largest['verdict']} | "
                       f"{min(inventory):,}–{max(inventory):,} | {' / '.join(mark(t) for t in totals)} |")
        out.append(f"\n\"Over\" in the last column passes the registered typed `aggregate_input_tokens` "
                   f"({allowance:,}). The assigned inventory is what a worker must answer for, one row per "
                   f"path with complete claims, inside its output cap of {worker_cap:,} tokens.")
        output_allowance = registered.get("aggregate_output_tokens", 100_000)
        omission_cap = registered.get("omission_output_tokens", 4_000)
        integration_cap = registered.get("integration_output_tokens", 4_000)
        out.append(f"\nWorker output. The floor (`response_floor`) is a floor under any answer the terminal "
                   "source review accepts; the worker-stage check alone accepts the smaller one-character-claim "
                   f"answer. Tokens are at {round(1 / FLOOR_TOKENS_PER_BYTE)} bytes a token, so they err low, "
                   f"and thinking draws on the same `max_tokens`. \"Over\" on the largest worker passes its cap "
                   f"({worker_cap:,}). The peak is the smallest `aggregate_output_tokens` the admission rule "
                   "needs with every worker's cap at the largest floor and outputs at their floors, the omission "
                   f"output taken as 0 (`peak_output_need`); \"over\" passes the registered {output_allowance:,}.\n")
        out.append("| Grid | Workers | Largest assignment (paths) | Largest worker's floor B | Its tokens, at "
                   "least | Worker-check minimum, tokens | All workers' floors, tokens | Peak output need |")
        out.append("|---|---|---|---|---|---|---|---|")
        for key, row in runs.items():
            typed = row.get("typed", {})
            if not key.startswith(label + "|") or typed.get("status") != "MEASURED":
                continue
            floors = [w.get("response_floor", {}) for w in typed["workers"]]
            if not floors or any(not f.get("passed") for f in floors):
                out.append(f"| {key.split('|')[1]} | {typed['worker_count']} | | not measured or refused |||||")
                continue
            tokens = [floor_tokens(f["bytes"]) for f in floors]
            low = max(floor_tokens(f["worker_check_minimum"]["bytes"]) for f in floors)
            need = peak_output_need(tokens, omission_cap, integration_cap)
            out.append(f"| {key.split('|')[1]} | {typed['worker_count']} | "
                       f"{max(w['paths'] for w in typed['workers'])} | {max(f['bytes'] for f in floors):,} | "
                       f"{max(tokens):,}{' over' if max(tokens) > worker_cap else ''} | "
                       f"{low:,}{' over' if low > worker_cap else ''} | {sum(tokens):,} | "
                       f"{need:,}{' over' if need > output_allowance else ''} |")
        g2 = runs.get(f"{label}|G2")
        if g2 and g2.get("stages"):
            out.append("\nEvery request at G2 (largest worker shown for the typed workers):\n")
            out.append("| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | "
                       "Est. in flight (range) | Ceiling | Verdict |")
            out.append("|---|---|---|---|---|---|---|---|")
            rows = []
            typed = g2.get("typed", {})
            if typed.get("status") == "MEASURED":
                w = max(typed["workers"], key=lambda w: w["estimated_in_flight_tokens"])
                rows.append(("typed_audit_worker (largest)", w))
            rows += [(k, v) for k, v in g2["stages"].items() if k != "report_after_repair"]
            for name, e in rows:
                low, high = e["estimated_in_flight_range"]
                if e.get("carry_basis"):
                    name = f"{name} (audit carried at: {e['carry_basis']})"
                out.append(f"| {name} | {e['payload_bytes']:,} | {e['ratio']} ({e['ratio_basis']}) | "
                           f"{e['placeholder_tokens']:,} | {e['max_output_tokens']:,} | "
                           f"{e['estimated_in_flight_tokens']:,} ({low:,}–{high:,}) | {e['ceiling_tokens']:,} | "
                           f"{e['verdict']} |")
        replicates = [(k, v) for k, v in runs.items() if k.endswith("|G2")]
        if len(replicates) > 1:
            out.append("\nRecord sensitivity at G2 (estimated tokens in flight):\n")
            out.append("| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | "
                       "Receipt completion | Report | Regate (cap) |")
            out.append("|---|---|---|---|---|---|---|---|---|---|")
            for key, row in replicates:
                if row.get("status") != "MEASURED":
                    out.append(f"| `{key.split('|')[0]}` | refused: {row.get('reason')} |||||||||")
                    continue
                stg, typed = row.get("stages", {}), row.get("typed", {})
                largest = (max(w["estimated_in_flight_tokens"] for w in typed["workers"])
                           if typed.get("status") == "MEASURED" else "refused")
                cell = lambda s: _fmt(stg[s]["estimated_in_flight_tokens"]) if s in stg else "—"
                staging = row.get("staging", {}).get("original_full", {})
                out.append(f"| `{key.split('|')[0]}` | {staging.get('staged_bytes', ''):,} | "
                           f"{len(staging.get('conformance_edits', []))} | {typed.get('worker_count', '—')} | "
                           f"{_fmt(largest)} | {cell('typed_audit_omission')} | {cell('typed_audit_integration')} | "
                           f"{cell('full_receipt_completion')} | {cell('report')} | {cell('report_regate')} |")
        components_by_stage = (g2 or {}).get("components")
        if components_by_stage:
            out.append("\nWhat the largest requests carry (bytes, by emptying each part):\n")
            for stage in ("typed_audit_worker (largest)", "typed_audit_omission", "full_receipt_completion",
                          "report_regate"):
                parts = components_by_stage.get(stage)
                if not parts:
                    continue
                pieces = dict(parts["parts"])
                pieces.update({f"  inside: {k}": v for k, v in parts.get("typed", {}).items()})
                pieces.update({f"  inside: {k}": v for k, v in parts.get("json", {}).items()})
                if "schema_context" in parts:
                    sc = parts["schema_context"]
                    pieces.update({f"  schema context: {k}": sc[k] for k in
                                   ("classes", "owners", "owner_yaml", "owner_typed_tree", "nested_owners")})
                top = sorted(pieces.items(), key=lambda kv: -kv[1])[:9]
                # A part's first line can name a local path; it says nothing about the size.
                tidy = lambda k: re.sub(r"/\S+", "<path>", k.strip())
                out.append(f"- **{stage}** ({parts['total']:,} B): " + "; ".join(
                    f"{tidy(k)} {v:,} ({100 * v / parts['total']:.0f}%)" for k, v in top))
            out.append("\nCompaction options (protocol changes nobody has made; estimated tokens in flight "
                       "after removing the parts, with the request's own tokens-per-byte ratio):\n")
            stages = [s for s in ("typed_audit_worker (largest)", "typed_audit_omission", "typed_audit_integration",
                                  "full_receipt_completion", "report", "report_regate")
                      if s in components_by_stage]
            out.append("| Option | " + " | ".join(stages) + " |")
            out.append("|---|" + "---|" * len(stages))
            for option, (text, keys) in OPTIONS.items():
                cells = []
                for stage in stages:
                    parts = components_by_stage[stage]
                    if stage.startswith("typed_audit_worker"):
                        e = max(g2["typed"]["workers"], key=lambda w: w["payload_bytes"])
                        phase = WORKER_PHASE
                    else:
                        e = g2["stages"][stage]
                        phase = e.get("phase", stage)
                    after = estimate(project, phase, max(e["payload_bytes"] - removed_bytes(parts, keys), 0),
                                     e["max_output_tokens"], placeholder_tokens=e["placeholder_tokens"])
                    mark = "fits" if after["verdict"] == "estimate_fits" else "exceeds"
                    cells.append(f"{after['estimated_in_flight_tokens']:,} ({mark})")
                out.append(f"| {option}: {text} | " + " | ".join(cells) + " |")
        out.append("")
    return "\n".join(out)


def peak_output_need(floors, omission_cap, integration_cap):
    """The smallest `aggregate_output_tokens` the runtime's admission rule
    needs (`typed_audit_runtime`, about :506). Before each typed stage, the
    output already spent plus that stage's `max_tokens` must fit. Here every
    worker's cap is the largest floor, each worker spends exactly its floor,
    and the omission stage's output is taken as 0, since it is not floored. So
    this is a lower bound."""
    cap, spent, need = max(floors), 0, 0
    for floor in floors:
        need, spent = max(need, spent + cap), spent + floor
    return max(need, spent + omission_cap, spent + integration_cap)


def room_per_row(estimate_row, rows):
    """Bytes of carried content each source-review row could still add before
    the request reaches its ceiling, at the request's own ratio."""
    room = estimate_row["ceiling_tokens"] - estimate_row["estimated_in_flight_tokens"]
    return round(room / estimate_row["ratio"] / rows)


#: The note's cross-project columns: (heading, stage key; None is the largest worker).
SUMMARY_STAGES = (("Largest worker", None), ("Omission", "typed_audit_omission"),
                  ("Integration", "typed_audit_integration"),
                  ("Receipt completion (with a re-address turn)", "full_receipt_completion_after_readdress"),
                  ("Report", "report"), ("Regate (report at its 96k cap)", "report_regate"))


def option_estimate(project, run, stage, keys=()):
    """One request of a measured run, re-estimated after removing the parts
    `keys` names (an option's), using the run's own components."""
    components = run.get("components") or {}
    if stage is None:
        e, phase = max(run["typed"]["workers"], key=lambda w: w["payload_bytes"]), WORKER_PHASE
        parts = components.get(WORKER_PHASE + " (largest)")
    else:
        e = run["stages"][stage]
        phase, parts = e.get("phase", stage), components.get(stage)
    removed = removed_bytes(parts or {}, keys) if keys else 0
    return {**estimate(project, phase, max(e["payload_bytes"] - removed, 0), e["max_output_tokens"],
                       placeholder_tokens=e["placeholder_tokens"]), "carry_basis": e.get("carry_basis")}


def summary(results):
    """The note's cross-project tables, generated from a sweep's results."""
    out, measured = [], {p: b for p, b in results["projects"].items() if b.get("status") == "MEASURED"}
    floored = lambda e: str(e.get("carry_basis") or "").startswith("workers' smallest")
    tag = lambda e: (f"{e['estimated_in_flight_tokens']:,}" + (" over" if e["verdict"] != "estimate_fits" else "")
                     + (" †" if floored(e) else ""))

    def primary(block, grid="G2"):
        return block["runs"].get(f"{block['primary']}|{grid}", {})

    def name(project, block):
        return f"{project} (proxy)" if block.get("proxy") else project
    heads = [h for h, _ in SUMMARY_STAGES]
    out.append("Current protocol, G2, primary records (estimated tokens in flight; \"over\" passes the "
               "request's ceiling; † carries the audit, or the worker answers, at their floor, which here "
               "exceeds the registered output caps' bound: for that carry a † figure is a lower bound):\n")
    out.append("| Project | " + " | ".join([heads[0], "Largest worker, every record at G2"] + heads[1:]) + " |")
    out.append("|---|" + "---|" * (len(heads) + 1))
    for project, block in measured.items():
        run = primary(block)
        across = [max(w["estimated_in_flight_tokens"] for w in r["typed"]["workers"])
                  for k, r in block["runs"].items() if k.endswith("|G2") and r.get("typed", {}).get("status") == "MEASURED"]
        cells = [tag(option_estimate(project, run, s)) for _, s in SUMMARY_STAGES]
        out.append(f"| {name(project, block)} | {cells[0]} | {min(across):,}–{max(across):,} ({len(across)}) | "
                   + " | ".join(cells[1:]) + " |")
    keys = OPTIONS["S7"][1]
    out.append("\nUnder S7, G2, primary records:\n")
    out.append("| Project | " + " | ".join(heads) + " |")
    out.append("|---|" + "---|" * len(heads))
    for project, block in measured.items():
        run = primary(block)
        out.append(f"| {name(project, block)} | "
                   + " | ".join(tag(option_estimate(project, run, s, keys)) for _, s in SUMMARY_STAGES) + " |")
    out.append("\nUnder S7 plus each project's largest record difference at G2 (another record's current "
               "figure minus the primary's, where positive), the conservative reading:\n")
    out.append("| Project | " + " | ".join(heads) + " |")
    out.append("|---|" + "---|" * len(heads))
    for project, block in measured.items():
        run, cells = primary(block), []
        for _, stage in SUMMARY_STAGES:
            base = option_estimate(project, run, stage)["estimated_in_flight_tokens"]
            others = [option_estimate(project, r, stage)["estimated_in_flight_tokens"]
                      for k, r in block["runs"].items() if k.endswith("|G2") and r is not run
                      and r.get("typed", {}).get("status") == "MEASURED" and (stage is None or stage in r["stages"])]
            extra = max([o - base for o in others] + [0])
            e = option_estimate(project, run, stage, keys)
            total = e["estimated_in_flight_tokens"] + extra
            cells.append(f"{total:,} (+{extra:,})" + (" over" if total > e["ceiling_tokens"] else ""))
        out.append(f"| {name(project, block)} | " + " | ".join(cells) + " |")
    out.append("\nUnder S7, G2, primary records: the report family with the audit at its floor (a lower bound) "
               "and the report as written read two ways, at its 96k cap (an upper bound) or as the v8 report's "
               "text. In brackets, the bytes each source-review row could still add before the request reaches "
               "850,000, at the request's ratio; a real row adds a reason, quotes, a source and a chunk id:\n")
    out.append("| Project | Rows | Report | Regate, report at its cap | Regate, v8 report text |")
    out.append("|---|---|---|---|---|")
    for project, block in measured.items():
        run = primary(block)
        if run.get("typed", {}).get("status") != "MEASURED":
            continue
        rows = sum(w["paths"] for w in run["typed"]["workers"])
        cells = []
        for stage in ("report", "report_regate", "report_regate_with_v8_report"):
            e = option_estimate(project, run, stage, keys)
            cells.append(f"{e['estimated_in_flight_tokens']:,} ({room_per_row(e, rows):,} B)"
                         + (" over" if e["verdict"] != "estimate_fits" else ""))
        out.append(f"| {name(project, block)} | {rows} | " + " | ".join(cells) + " |")
    grids = list(results["grid"])
    allowance = next((r["audit_limits"]["aggregate_input_tokens"] for b in measured.values()
                      for r in b["runs"].values() if r.get("audit_limits")), 4_000_000)
    out.append(f"\nTyped input across every typed call of a run, current / S6 / S7, against "
               f"`aggregate_input_tokens` ({allowance:,}); the options use the G2 components, since a "
               "worker's shared content does not depend on the partition:\n")
    out.append("| Project | " + " | ".join(grids) + " |")
    out.append("|---|" + "---|" * len(grids))
    for project, block in measured.items():
        g2, cells = primary(block), []
        for grid in grids:
            run = primary(block, grid)
            totals = [typed_aggregate(project, run)] + [
                typed_aggregate(project, run, g2.get("components"), OPTIONS[o][1]) for o in ("S6", "S7")]
            cells.append("refused" if totals[0] is None else " / ".join(
                f"{t / 1e6:.2f}M" + ("*" if t > allowance else "") for t in totals))
        out.append(f"| {name(project, block)} | " + " | ".join(cells) + " |")
    out.append("\n\\* passes the allowance.\n")
    caps = next((r["audit_limits"] for b in measured.values() for r in b["runs"].values() if r.get("audit_limits")),
                {})
    unit = round(1 / FLOOR_TOKENS_PER_BYTE)
    out.append(f"The largest worker's answer, in tokens at {unit} bytes a token (at least). The first figure "
               "is the floor under any answer the terminal source review accepts (claims quoting and covering "
               "each value); the second is the smallest answer the worker-stage check accepts (one-character "
               "claims); in brackets, the largest assignment's paths. The registered worker cap is "
               f"{caps.get('worker_output_tokens', 4_000):,}:\n")
    out.append("| Project | " + " | ".join(grids) + " |")
    out.append("|---|" + "---|" * len(grids))
    for project, block in measured.items():
        cells = []
        for grid in grids:
            typed = primary(block, grid).get("typed", {})
            floors = [w.get("response_floor", {}) for w in typed.get("workers", [])]
            if typed.get("status") != "MEASURED" or not floors or not all(f.get("passed") for f in floors):
                cells.append("refused" if typed.get("status") == "REFUSED" else "—")
                continue
            low = [floor_tokens(f["worker_check_minimum"]["bytes"]) for f in floors]
            cells.append(f"{max(floor_tokens(f['bytes']) for f in floors):,} / {max(low):,} "
                         f"({max(w['paths'] for w in typed['workers'])})")
        out.append(f"| {name(project, block)} | " + " | ".join(cells) + " |")
    out.append(f"\nThe smallest `aggregate_output_tokens` the admission rule needs (registered: "
               f"{caps.get('aggregate_output_tokens', 100_000):,}), at {unit} bytes a token: every worker's cap "
               "at the largest floor, each worker spending its floor, the omission output taken as 0 and no "
               "thinking (`peak_output_need`, a lower bound); in brackets, the workers' floors summed:\n")
    out.append("| Project | " + " | ".join(grids) + " |")
    out.append("|---|" + "---|" * len(grids))
    for project, block in measured.items():
        cells = []
        for grid in grids:
            typed = primary(block, grid).get("typed", {})
            floors = [w.get("response_floor", {}) for w in typed.get("workers", [])]
            if typed.get("status") != "MEASURED" or not floors or not all(f.get("passed") for f in floors):
                cells.append("refused" if typed.get("status") == "REFUSED" else "—")
                continue
            tokens = [floor_tokens(f["bytes"]) for f in floors]
            need = peak_output_need(tokens, caps.get("omission_output_tokens", 4_000),
                                    caps.get("integration_output_tokens", 4_000))
            cells.append(f"{need:,} ({sum(tokens):,})")
        out.append(f"| {name(project, block)} | " + " | ".join(cells) + " |")
    out.append("\nStaging of each stand-in record (conformance edits to the current schema's cardinality):\n")
    out.append("| Record | Edits: wrapped / unwrapped / joined / removed | Undeclared slots removed | "
               "Bytes before → after |")
    out.append("|---|---|---|---|")
    seen = set()
    for project, block in measured.items():
        for key, run in block["runs"].items():
            label = key.split("|")[0]
            if not key.endswith("|G2") or (block["record_project"], label) in seen:
                continue
            seen.add((block["record_project"], label))
            staging = run.get("staging", {}).get("original_full", {})
            edits = staging.get("conformance_edits", [])
            removed = [e.split(" (")[0] for e in edits if e.endswith(", removed)")]
            kinds = [sum(e.endswith(f" ({k})") for e in edits) for k in ("wrapped", "unwrapped", "joined")]
            before, after = staging.get("source_bytes"), staging.get("staged_bytes")
            out.append(f"| {block['record_project']} `{label}` | {len(edits)}: "
                       f"{' / '.join(str(k) for k in kinds)} / {len(removed)} | "
                       f"{', '.join(f'`{r}`' for r in removed) or '—'} | {before:,} → {after:,} "
                       f"({after - before:+,}, {100 * (after - before) / before:+.2f}%) |")
    return "\n".join(out) + "\n"


def merge(full, again):
    """Put a primary-only rerun's component breakdown into a full sweep's results.

    The rerun must use the same tree. Its scratch directory differs, and the
    run directory's path reaches typed-stage text (plan risk 7), so every
    ordinary-phase number must match exactly and each project's typed stages
    may differ only by one uniform byte offset of at most 100 bytes. Anything
    else refuses, so the merged results state one measurement.
    """
    if full["root_head"] != again["root_head"]:
        raise ValueError("the two sweeps measured different trees")
    typed_stages = ("typed_audit_omission", "typed_audit_integration")
    merged, problems, offsets, added = copy.deepcopy(full), [], {}, []
    for project, block in again["projects"].items():
        if block.get("status") != "MEASURED":
            continue
        if merged["projects"].get(project, {}).get("status") != "MEASURED":
            # A project the full sweep could not measure: the rerun's block is the measurement.
            merged["projects"][project] = copy.deepcopy(block)
            added.append(project)
            continue
        key = f"{block['primary']}|G2"
        a, b = merged["projects"][project]["runs"][key], block["runs"][key]
        seen = set()
        for stage, e in b.get("stages", {}).items():
            delta = e["payload_bytes"] - a["stages"][stage]["payload_bytes"]
            if stage in typed_stages:
                seen.add(delta)
            elif delta or e["estimated_in_flight_tokens"] != a["stages"][stage]["estimated_in_flight_tokens"]:
                problems.append((project, stage, delta))
        wa = {w["worker_id"]: w["payload_bytes"] for w in a["typed"]["workers"]}
        wb = {w["worker_id"]: w["payload_bytes"] for w in b["typed"]["workers"]}
        if set(wa) != set(wb):
            problems.append((project, "worker roster differs"))
        seen |= {wb[k] - wa[k] for k in wa if k in wb}
        if len(seen) > 1 or any(abs(d) > 100 for d in seen):
            problems.append((project, "typed offsets", sorted(seen)))
        offsets[project] = sorted(seen)
        a["components"] = b["components"]
        merged["projects"][project]["primary"] = block["primary"]
    if problems:
        raise ValueError(f"the rerun differs from the full sweep beyond a scratch-path offset: {problems[:5]}")
    previous = merged.get("components_from", {})
    merged["components_from"] = {
        "typed_byte_offsets": {**previous.get("typed_byte_offsets", {}), **offsets},
        "added_projects": previous.get("added_projects", []) + added,
        "note": "primary records at G2 from a rerun; ordinary phases matched exactly and each typed stage "
                "differed only by the uniform offset shown; added projects were measured only by the rerun"}
    return merged


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("sweep", help="size every request offline over the grid")
    run.add_argument("--root", type=Path, required=True, help="checkout with the A3 builder and A5d contexts")
    run.add_argument("--workdir", type=Path, required=True, help="new directory for scratch runs")
    run.add_argument("--out", type=Path, required=True, help="new JSON results file")
    run.add_argument("--projects", nargs="+", default=list(PROJECTS), choices=PROJECTS)
    run.add_argument("--grid", nargs="+", default=list(GRID), choices=list(GRID))
    run.add_argument("--primary-only", action="store_true", help="each project's primary record only")
    tables = commands.add_parser("table", help="markdown tables from a sweep's results")
    tables.add_argument("results", type=Path)
    pivot = commands.add_parser("summary", help="the note's cross-project tables from a sweep's results")
    pivot.add_argument("results", type=Path)
    combine = commands.add_parser("merge", help="add a primary-only rerun's components to a full sweep")
    combine.add_argument("full", type=Path)
    combine.add_argument("rerun", type=Path)
    combine.add_argument("--out", type=Path, required=True, help="new JSON results file")
    args = parser.parse_args(argv)
    if args.command == "table":
        print(table(json.loads(args.results.read_text(encoding="utf-8"))))
        return 0
    if args.command == "summary":
        print(summary(json.loads(args.results.read_text(encoding="utf-8"))), end="")
        return 0
    if args.command == "merge":
        merged = merge(json.loads(args.full.read_text(encoding="utf-8")),
                       json.loads(args.rerun.read_text(encoding="utf-8")))
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(merged, stream, indent=1, sort_keys=True)
            stream.write("\n")
        print(json.dumps(merged["components_from"]["typed_byte_offsets"]))
        return 0
    out = args.out.resolve()          # the sweep changes into --root
    results = sweep(args.root.resolve(), args.workdir.resolve(), tuple(args.projects),
                    {k: GRID[k] for k in args.grid}, primary_only=args.primary_only)
    with out.open("x", encoding="utf-8") as stream:
        json.dump(results, stream, indent=1, sort_keys=True)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
