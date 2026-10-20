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

Placeholders for content that does not exist before a run (the typed audit's
findings, the report as written) are sized at their output caps in TOKENS,
added after the byte estimate. A1b sized them as runs of 'x' at 4 bytes per
token, and the endpoint counted about one token per 'x' (see A1B below), so
those A1b rows overstate the report family by about four times each
placeholder.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import re
import shutil
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
#: `notes/.local_drafts/a1b_calibrated_tokens.json` at commit 10dee83fe
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
PROXY = {"VOICE_PEDIATRIC": "VOICE"}
PROJECTS = ("CHORUS", "AI_READI", "CM4AI", "VOICE", "VOICE_PEDIATRIC", "KIDS_FIRST")

#: (max_paths, max_inventory_bytes, max_workers). G2 is the A3 draft default
#: and the A1b setting; G1 is typed.prepare's default.
GRID = {
    "G1": (96, 16_384, 16), "G2": (192, 32_768, 16), "G3": (384, 65_536, 16),
    "G4": (192, 32_768, 8), "G5": (384, 65_536, 4), "G6": (768, 131_072, 2),
}


def block_network():
    def forbidden(*args, **kwargs):
        raise RuntimeError("offline sizing must not open a network connection")
    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.create_connection = forbidden


def load(root):
    """Import the runtime from `root` only.

    `data_sheets_schema` and `scripts` are namespace packages, and an editable
    install puts another checkout's `src` on the path, so a module missing
    from `root` would silently load from that checkout. Every other location
    is removed first, and every loaded module is checked afterwards.
    """
    root = Path(root).resolve()
    own = {root, root / "src"}

    def foreign(entry):
        try:
            path = Path(entry or ".").resolve()
        except OSError:
            return False
        return path not in own and ((path / "data_sheets_schema").is_dir() or (path / "scripts").is_dir())
    sys.path[:] = [entry for entry in sys.path if not foreign(entry)]
    for entry in (str(root), str(root / "src")):
        if entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)
    from data_sheets_schema import api_runner as api, receipt_completion as rc, shared_generation as sg
    from data_sheets_schema import snapshot_store, typed_audit as typed, typed_audit_runtime as tar
    from data_sheets_schema import usage_ledger as ledger
    from data_sheets_schema.cli.api import ARMS
    try:
        from scripts.build_api_registrations import DEFAULT_AUDIT_LIMITS, build_registration
    except ImportError as exc:
        raise SystemExit(f"{root} has no A3 registration builder (scripts/build_api_registrations.py, #5095): {exc}")
    strays = sorted(name for name, module in list(sys.modules.items())
                    if name.split(".")[0] in ("data_sheets_schema", "scripts") and getattr(module, "__file__", None)
                    and not Path(module.__file__).resolve().is_relative_to(root))
    if strays:
        raise SystemExit(f"modules loaded from outside {root}: {strays}")
    return SimpleNamespace(root=root, api=api, rc=rc, sg=sg, snapshot_store=snapshot_store, typed=typed,
                           tar=tar, ledger=ledger, ARMS=ARMS, DEFAULT_AUDIT_LIMITS=DEFAULT_AUDIT_LIMITS,
                           build_registration=build_registration)


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
    bundle = root / f"data/preprocessed/concatenated/{project}_preprocessed.txt"
    manifest = root / f"data/preprocessed/chunks/{project}_chunks.yaml"
    context = root / f"data/omission_contexts/{project.lower()}_omission_context.json"
    missing = [str(p.relative_to(root)) for p in (bundle, manifest, context) if not p.is_file()]
    return bundle, manifest, context, missing


@contextlib.contextmanager
def offline_receipt_and_index(m):
    """As the A1 harness: receipt completion's recovery and the integration
    index need a live run's results, so both are replaced by inert stand-ins."""
    saved_recover, saved_index = m.rc.recover, m.typed.index
    m.rc.recover = lambda s, **kw: {"input_identity": s.input_identity(),
        "registration": m.rc.registration_identity(s), "journal": {"result": "scratch_result_artifact.json"},
        "unsupported_audit_candidates": []}
    def index(packet, workers, omission, derivations=None):
        return {"kind": "typed_audit_index_v1", "packet_sha256": packet["sha256"], "index": {},
                "omission_check": {"protocol_complete": True, "declared_candidates": []},
                "integration_request": {"kind": "typed_audit_integration_request_v1", "payload": {
                    "stage": "integration", "packet_sha256": packet["sha256"],
                    "shared_context": packet["requests"]["shared_context"], "proposal_index": {},
                    "workers": {}, "omission_response": "",
                    "omission_check": {"protocol_complete": True, "declared_candidates": []},
                    "output_contract": packet["contracts"]["integration"]}, "request_sha256": "0" * 64}}
    m.typed.index = index
    try:
        yield
    finally:
        m.rc.recover, m.typed.index = saved_recover, saved_index


_VIEWS = {}


def conform_record(text, schema_path):
    """Make a stand-in record's cardinality match the current schema.

    The typed audit's owner traversal (audit_omissions._owners) refuses a
    value whose list-ness differs from its slot's `multivalued`. v8/v9
    records predate later schema changes, and the write-time normaliser
    lists scalars only where its table names the slot, so nested inlined
    slots stay scalar. A scalar in a multivalued slot is wrapped, a one-item
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
                edits.append(here)
            elif not many and isinstance(item, list):
                if len(item) == 1:
                    value[field] = item = item[0]
                    edits.append(here)
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
    reg = m.build_registration(project=project, label=label, arm="baseline",
        registration_path=workdir / f"{project}_registration.json", context_path=context,
        bundle_path=bundle, chunk_manifest_path=manifest, audit_limits=audit_limits, write_to_disk=True)
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


def measure_typed(m, spec, settings):
    """Workers, omission and integration through prepare_packet/build_request."""
    with offline_receipt_and_index(m):
        packet = m.tar.prepare_packet(spec)
        rows, largest = [], None
        for worker in packet["plan"]["workers"]:
            stage = {"phase": m.tar.WORKER_PHASE, "worker_id": worker["id"]}
            _, payload, _ = m.tar.build_request(spec, packet, stage, workers={}, omission=None, settings=settings)
            rows.append({"worker_id": worker["id"], "paths": len(worker["paths"]),
                         "inventory_bytes": worker["inventory_bytes"], "payload_bytes": nbytes(m, payload),
                         "max_output_tokens": payload["max_tokens"]})
            if largest is None or rows[-1]["payload_bytes"] > nbytes(m, largest):
                largest = payload
        _, omission, _ = m.tar.build_request(spec, packet, {"phase": m.tar.OMISSION_PHASE}, workers={},
                                             omission=None, settings=settings)
        _, integration, _ = m.tar.build_request(spec, packet, {"phase": m.tar.INTEGRATION_PHASE}, workers={},
                                                omission=b"", settings=settings)
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


def measure_ordinary(m, project, spec, settings, reg, files):
    """Ordinary phases as the runner builds them (A1: build_phase, the
    PHASE_NEEDS carries, _append_regate, build_repair + generation_context)."""
    read = lambda path: path.read_bytes().decode("utf-8") if path is not None else ""
    # The staged originals, as the typed stages saw them.
    run_dir = Path(spec.out_dir)
    full = read(run_dir / "intermediate" / f"{project}_full.yaml")
    core = read(run_dir / "intermediate" / f"{project}_core.yaml")
    reconciled = read(files["reconciled_full"]) if files["reconciled_full"] else full
    completed = read(files["completed_core"]) if files["completed_core"] else core
    report_text = read(files["report"]) if files["report"] else ""
    findings_cap = reg["audit_limits"]["integration_output_tokens"]
    report_cap = cap(m, spec, settings, "report")
    out = {}

    def payload(req, phase, max_tokens=None):
        return m.rc.request_payload(req, settings,
            {"max_output_tokens": max_tokens if max_tokens is not None else cap(m, spec, settings, phase)})

    full_req = m.api.build_phase(spec, "full", carry={})
    out["full"] = (payload(full_req, "full"), 0)
    unresolved = [{"slot": "placeholder", "detail": "one unresolved receipt entry"}]
    readdress = m.api.build_readdress(full_req, full, unresolved)
    out["full_readdress"] = (payload(readdress, "full_readdress", min(m.api.READDRESS_MAX_TOKENS,
                             m.api.output_limit(settings["name"]))), 0)
    transcript = {"phase": "full", "system": full_req.system, "cached_blocks": copy.deepcopy(full_req.cached_blocks),
                  "messages": copy.deepcopy(full_req.messages), "response": [{"type": "text", "text": full}]}
    rc_inputs = {"record": full, "receipt": read(run_dir / f"{project}_coverage_receipt.yaml"),
                 "manifest": Path(spec.chunk_manifest).read_text(encoding="utf-8"),
                 "bundle": Path(spec.bundle).read_text(encoding="utf-8"), "schema": m.rc.schema_capture(spec),
                 "transcript": transcript, "transcript_pin": "scratch_full_transcript.json",
                 "registration": m.rc.registration_identity(spec),
                 "policy": m.rc.policy_identity(version=spec.receipt_completion_version),
                 "input_identity": spec.input_identity(), "max_output_tokens": reg["receipt"]["max_output_tokens"]}
    rc_req, _ = m.rc.build_request(rc_inputs)
    out["full_receipt_completion"] = (m.rc.request_payload(rc_req, settings, m.rc.registration(spec)), 0)
    # Findings exist only after the audit: an empty carry, sized at their cap in tokens.
    out["reconcile_full"] = (payload(m.api.build_phase(spec, "reconcile_full",
        carry={"Completed full record": full, "Audit findings": ""}), "reconcile_full"), findings_cap)
    report_carry = {"Audit findings": "", "Original full record": full, "Original core record": core,
                    "Reconciled full record": reconciled, "Completed core record": completed}
    out["report"] = (payload(m.api.build_phase(spec, "report", carry=report_carry), "report"), findings_cap)
    regate = m.api.build_phase(spec, "report", carry=report_carry)
    m.api._append_regate(regate, spec, "", [])
    # The report as written, at most the report cap; a v8 report shows a realistic size.
    out["report_regate"] = (payload(regate, "report", report_cap), findings_cap + report_cap)
    realistic = m.api.build_phase(spec, "report", carry=report_carry)
    m.api._append_regate(realistic, spec, report_text, [])
    out["report_regate_with_v8_report"] = (payload(realistic, "report", report_cap), findings_cap)
    repair = m.api.build_repair("full", reconciled,
        errors=["Slot 'data_collection' has validation error: missing required source link"],
        profile=spec.profile_obj, _captured_digest=m.sg.digest_text(spec, "Dataset"))
    repair.messages[0]["content"].insert(-1, {"type": "text", "text": m.sg.generation_context(spec)})
    out["repair_full"] = (payload(repair, "repair_full"), 0)
    return out


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
    try:
        packet, workers, omission, integration, largest = measure_typed(m, spec, settings)
    except Exception as exc:                      # noqa: BLE001
        result["typed"] = {"status": "REFUSED", "reason": f"{type(exc).__name__}: {exc}"}
    else:
        result["typed"] = {"status": "MEASURED", "worker_count": len(workers), "workers": [
            {**w, **estimate(project, WORKER_PHASE, w["payload_bytes"], w["max_output_tokens"])} for w in workers]}
        result["stages"]["typed_audit_omission"] = estimate(project, "typed_audit_omission",
            nbytes(m, omission), omission["max_tokens"])
        # Integration also carries every worker response and the omission
        # response at their caps: the plan's upper bound from the output caps.
        bound = sum(w["max_output_tokens"] for w in workers) + omission["max_tokens"]
        result["stages"]["typed_audit_integration"] = estimate(project, "typed_audit_integration",
            nbytes(m, integration), integration["max_tokens"], placeholder_tokens=bound)
        parts.update({WORKER_PHASE + " (largest)": largest, "typed_audit_omission": omission,
                      "typed_audit_integration": integration})
    try:
        ordinary = measure_ordinary(m, project, spec, settings, reg, files)
    except Exception as exc:                      # noqa: BLE001
        result["ordinary"] = {"status": "REFUSED", "reason": f"{type(exc).__name__}: {exc}"}
    else:
        for phase, (payload, placeholder) in ordinary.items():
            family_phase = "report_regate" if phase == "report_regate_with_v8_report" else phase
            result["stages"][phase] = estimate(project, family_phase, nbytes(m, payload), payload["max_tokens"],
                                               placeholder_tokens=placeholder)
            if family_phase != phase:
                result["stages"][phase]["phase"] = family_phase
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
    block_network()
    m = load(root)
    workdir = Path(workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=False)
    results = {"format": "d4d_a1_offline_sizing_sweep_v1", "root": str(m.root),
               "root_head": _head(m.root), "ceilings": {"worker": WORKER_CEILING_TOKENS,
               "report_family": REPORT_CEILING_TOKENS, "window": ROUTE_WINDOW_TOKENS},
               "calibration": {p: {f: {"bytes": v[0], "tokens": v[1], "x_bytes": v[2],
                               "clean_ratio": round(clean_ratio(p, f), 4)} for f, v in A1B[p].items()} for p in A1B},
               "grid": {k: dict(zip(("max_paths", "max_inventory_bytes", "max_workers"), v)) for k, v in grid.items()},
               "network_calls": 0, "projects": {}}
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
    return results


def _head(root):
    import subprocess
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


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
}


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
            out.append(f"Proxy: {block['record_project']}'s records with {project}'s own bundle, manifest and "
                       "context, and a minimal receipt; an estimate for a run that has no record yet.\n")
        runs = block["runs"]
        # The primary record carries every grid (results are stored with sorted keys).
        counts = {}
        for key in runs:
            counts[key.split("|")[0]] = counts.get(key.split("|")[0], 0) + 1
        label = block.get("primary") or max(counts, key=lambda k: (counts[k], k == RUNS.get(
            block.get("record_project", project), [None])[0]))
        out.append(f"Primary record `{label}`.\n")
        out.append("| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | "
                   "Est. in flight | Verdict |")
        out.append("|---|---|---|---|---|---|")
        for key, row in runs.items():
            if not key.startswith(label + "|"):
                continue
            grid = key.split("|")[1]
            limits = results["grid"][grid]
            limit_text = f"{limits['max_paths']} / {limits['max_inventory_bytes']:,} / {limits['max_workers']}"
            typed = row.get("typed", {})
            if row.get("status") != "MEASURED" or typed.get("status") != "MEASURED":
                reason = row.get("reason") or typed.get("reason")
                out.append(f"| {grid} | {limit_text} | refused | | | {reason} |")
                continue
            largest = max(typed["workers"], key=lambda w: w["estimated_in_flight_tokens"])
            out.append(f"| {grid} | {limit_text} | {typed['worker_count']} | {largest['payload_bytes']:,} | "
                       f"{largest['estimated_in_flight_tokens']:,} | {largest['verdict']} |")
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
    merged, problems, offsets = copy.deepcopy(full), [], {}
    for project, block in again["projects"].items():
        if block.get("status") != "MEASURED":
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
    merged["components_from"] = {"typed_byte_offsets": offsets, "note": "primary records at G2 from a rerun; "
        "ordinary phases matched exactly and each typed stage differed only by the uniform offset shown"}
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
    combine = commands.add_parser("merge", help="add a primary-only rerun's components to a full sweep")
    combine.add_argument("full", type=Path)
    combine.add_argument("rerun", type=Path)
    combine.add_argument("--out", type=Path, required=True, help="new JSON results file")
    args = parser.parse_args(argv)
    if args.command == "table":
        print(table(json.loads(args.results.read_text(encoding="utf-8"))))
        return 0
    if args.command == "merge":
        merged = merge(json.loads(args.full.read_text(encoding="utf-8")),
                       json.loads(args.rerun.read_text(encoding="utf-8")))
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(merged, stream, indent=1, sort_keys=True)
            stream.write("\n")
        print(json.dumps(merged["components_from"]["typed_byte_offsets"]))
        return 0
    results = sweep(args.root, args.workdir, tuple(args.projects), {k: GRID[k] for k in args.grid},
                    primary_only=args.primary_only)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(results, stream, indent=1, sort_keys=True)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
