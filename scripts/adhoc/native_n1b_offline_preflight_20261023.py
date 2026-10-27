#!/usr/bin/env python3
# Purpose: N1b steps3/4 offline CHORUS render and proxy sizing, 2026-10-23.
# Inputs: explicit retained API registration/ledger/intermediates and aligned tree.
# Outputs: evidence-only text/JSON; no registration, execution or scientific approval.
# Coordination: notes/coordination/2026-10-23-codex-n1b-prompt.md.
"""Render a hypothetical native26 instruction or size complete proxy requests.

Run only after the helper is committed and native scientific pins are aligned.
Invoke with the existing venv Python -S -P -B and an explicit trial/src
PYTHONPATH (optionally also trial/scripts and trial). Installed dependencies
are added explicitly without executing site or .pth files. The separate
``import-check --tree ABS [--dependency-path-out ABS]`` action proves this
environment for the real offline CLI without rendering or loading run inputs.
The native runtime identity is explicitly hypothetical; auth is not observed.
All stage history/binding carriers are invented in memory solely to exercise
the released serializer. They are never written or accepted as live evidence.
The retained API answers are transformed proxy content, never native answers.
Exact historical instruction replay is the default. The explicit current-target
mode renders integrated trial API25 code on the same fixed historical inputs;
it records historical differences without claiming historical replay acceptance.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from dataclasses import replace
from decimal import Decimal
import difflib
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

SCOPE = "hypothetical_offline_not_registered"
MODEL = "HYPOTHETICAL_MODEL_NOT_SELECTED"
PROVIDER = "HYPOTHETICAL_PROVIDER_NOT_AUTHENTICATED"
MAX_READ = 128_000_000
RULE_START = "UNIFORM DECISION RULES — these apply identically to every project and every arm:"
RULE_END = "## Shared generation rules v1"
API_INSTRUCTION_MODES = ("exact-historical", "current-target")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                      allow_nan=False).encode("utf-8") + b"\n"


def _object_pairs(rows):
    value = {}
    for key, item in rows:
        if key in value:
            raise ValueError("duplicate JSON key: " + key)
        value[key] = item
    return value


def parsed(raw):
    def invalid(value):
        raise ValueError("nonfinite JSON value: " + value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_object_pairs,
                      parse_constant=invalid)


class Reader:
    """Bounded regular-file reads, retained identities, and final fresh reread."""
    def __init__(self):
        self.files = {}

    def read(self, path, limit=MAX_READ):
        path = Path(path).absolute()
        if path.resolve(strict=True) != path:
            raise ValueError("input must use its physical absolute path: " + str(path))
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("input is not a bounded regular file: " + str(path))
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        def identity(info):
            return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns
        if (len(raw) > limit or len(raw) != before.st_size or identity(before) != identity(opened)
                or identity(before) != identity(after)
                or identity(before) != identity(path.stat(follow_symlinks=False))):
            raise ValueError("input changed during read: " + str(path))
        old = self.files.get(str(path))
        if old is not None and old != raw:
            raise ValueError("input changed between reads: " + str(path))
        self.files[str(path)] = raw
        return raw

    def pin(self, declared):
        raw = self.read(declared["path"])
        if len(raw) != declared["bytes"] or digest(raw) != declared["sha256"]:
            raise ValueError("retained input differs from pin: " + declared["path"])
        return raw

    def stable(self):
        for path, expected in tuple(self.files.items()):
            if self.read(path) != expected:
                raise ValueError("input changed: " + path)

    def manifest(self):
        return [{"path": path, "bytes": len(raw), "sha256": digest(raw)}
                for path, raw in sorted(self.files.items())]


def evidence_destination(evidence, name, tree):
    evidence = Path(evidence).absolute()
    if (evidence.resolve(strict=True) != evidence or not evidence.is_dir()
            or evidence.name != "evidence" or evidence == tree or tree in evidence.parents
            or "data" in evidence.parts):
        raise ValueError("use an existing physical evidence directory outside the source/data tree")
    if not name or Path(name).name != name or name in (".", ".."):
        raise ValueError("output name must be one new directory component")
    target = evidence / name
    if os.path.lexists(target):
        raise ValueError("evidence output already exists")
    return target


def publish(target, files):
    # Exclusive directory creation preserves every prior output. All filenames
    # are fixed by this program, not chosen from an input document.
    target.mkdir(mode=0o700)
    for name, raw in files.items():
        if Path(name).name != name:
            raise ValueError("output filename is not flat")
        fd = os.open(target / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())


def git_read(tree, *arguments):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0")
    return subprocess.run(["git", "--no-replace-objects", "-C", str(tree), *arguments], env=environment,
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30).stdout


def frozen_head(tree):
    head = git_read(tree, "rev-parse", "HEAD").decode().strip()
    dirty = git_read(tree, "diff", "--name-only", "HEAD")
    if dirty:
        raise ValueError("tracked source must be committed before offline evidence is produced")
    return head


def source_roster(tree):
    return tuple(sorted((tree / "src").rglob("*.py")))


def require_source_roster(tree, expected):
    if source_roster(tree) != expected:
        raise ValueError("source Python roster changed; evidence was not published")


def record_sources(tree, reader):
    # Git ignores do not hide imported Python from the evidence manifest.
    # Do not follow symlinks: Reader refuses aliases before capturing bytes.
    roster = source_roster(tree)
    for path in roster:
        reader.read(path)
    relative = "scripts/adhoc/native_n1b_offline_preflight_20261023.py"
    committed = git_read(tree, "show", "HEAD:" + relative)
    if reader.read(tree / relative) != committed:
        raise ValueError("helper bytes must match its committed source")
    return roster


def source_tools(tree, reader, head):
    """Load the already-reviewed origin proof from its exact committed helper."""
    relative = "scripts/adhoc/native_n1b_receipt_policy_probe_20261023.py"
    path = tree / relative
    raw = reader.read(path)
    if raw != git_read(tree, "show", head + ":" + relative):
        raise ValueError("import-origin helper differs from its committed blob")
    spec = importlib.util.spec_from_file_location("n1b_committed_source_proof", path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module, {"path": str(path), "sha256": digest(raw), "head": head,
                    "git_blob": git_read(tree, "rev-parse", head + ":" + relative).decode().strip()}


def require_isolated_start(tree):
    allowed = (str(tree / "src"), os.pathsep.join(map(str, (tree / "src", tree / "scripts", tree))))
    if os.environ.get("PYTHONPATH") not in allowed:
        raise ValueError("use only the declared trial/src PYTHONPATH, optionally followed by trial/scripts:trial")
    if not sys.flags.no_site or not sys.flags.safe_path or not sys.dont_write_bytecode:
        raise ValueError("preflight requires -S -P -B before any project import")
    if any(name == "data_sheets_schema" or name.startswith("data_sheets_schema.") for name in sys.modules):
        raise ValueError("project code was already imported before source isolation")


def isolated_imports(tree, reader, head, *, cli=False):
    """Fresh-process isolation; never repair/prune a contaminated namespace."""
    require_isolated_start(tree)
    tools, proof = source_tools(tree, reader, head)
    dependencies = tools.dependency_environment(Path(sys.executable))
    config_raw = reader.read(dependencies["config_path"])
    if (digest(config_raw) != dependencies["config_sha256"]
            or dependencies["python_version"] != f"{sys.version_info.major}.{sys.version_info.minor}"):
        raise ValueError("dependency config differs from the actual interpreter")
    site = dependencies["site_packages"]
    if site in sys.path:
        raise ValueError("dependency site was active before explicit isolation")
    # Plain append does not execute .pth hooks. The proof refuses a regular
    # foreign package or an additional installed namespace leg; no pruning.
    sys.path.append(site)
    importlib.import_module("data_sheets_schema")
    initial = tools.loaded_source_proof(tree, head)
    if cli:
        importlib.import_module("data_sheets_schema.cli")  # never execute __main__
        initial = tools.loaded_source_proof(tree, head)
    return tools, {"python": sys.executable, "python_version": sys.version,
        "pythonpath": os.environ["PYTHONPATH"], "dependency_environment": dependencies,
        "origin_proof_helper": proof, "loaded_project_sources": initial,
        "flags": {"no_site": sys.flags.no_site, "safe_path": sys.flags.safe_path,
                  "dont_write_bytecode": sys.dont_write_bytecode}}


def import_check_main(argv):
    check = argparse.ArgumentParser(description="Prove isolated offline CLI imports; no registration or render action.")
    check.add_argument("--tree", required=True)
    check.add_argument("--dependency-path-out", help="new dependency-site.txt inside a sibling evidence package")
    args = check.parse_args(argv)
    tree = Path(args.tree).resolve(strict=True)
    if Path(__file__).resolve() != tree / "scripts/adhoc/native_n1b_offline_preflight_20261023.py":
        raise ValueError("execute the committed helper from the declared trial tree")
    output = None
    if args.dependency_path_out:
        output = Path(args.dependency_path_out).absolute()
        if (output.name != "dependency-site.txt" or output.parent.resolve(strict=True) != output.parent
                or output.parent.parent != tree.parent / "evidence" or os.path.lexists(output)):
            raise ValueError("dependency path output must be new inside a physical sibling evidence package")
    head, reader = frozen_head(tree), Reader()
    roster = record_sources(tree, reader)
    tools, report = isolated_imports(tree, reader, head, cli=True)
    report.update(scope="offline_import_origin_check_only", head=head,
                  native_launch_authorized=False, scientific_approval="not assessed")
    require_source_roster(tree, roster)
    reader.stable()
    if frozen_head(tree) != head:
        raise ValueError("source HEAD changed during import check")
    report["inputs"] = reader.manifest()
    if output:
        raw = (report["dependency_environment"]["site_packages"] + "\n").encode()
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
    print(encoded(report).decode(), end="")
    return 0


def candidate_bounds(scenario):
    """Explicit non-approved comparison assumptions, not registration defaults."""
    return {"max_authority_bytes": 64_000_000, "max_evidence_bytes": 512_000_000,
        "max_history_bytes": 64_000_000, "max_history_records": 16384,
        "max_input_bytes": 8_000_000, "max_inventory_bytes": 12288 if scenario == "api-partition" else 65536,
        "max_paths_per_worker": 80 if scenario == "api-partition" else 384,
        "max_populated_paths": 100000, "max_request_bytes": 32_000_000,
        "max_response_bytes": 8_000_000, "max_submissions": 7, "max_workers": 4}


def scientific_slice(text):
    if text.count(RULE_START) != 1 or text.count(RULE_END) != 1:
        raise ValueError("scientific block markers are missing or ambiguous")
    start, end = text.index(RULE_START), text.index(RULE_END)
    if end <= start:
        raise ValueError("scientific block markers are out of order")
    return text[start:end].strip()


def verify_r9(source, native_text, api_text):
    start_marker = "- A slot whose declared range is an enumeration is populated only from a\n"
    end_marker = "\n- `raw_data_format`"
    if source.count(start_marker) != 1 or source.count(end_marker) != 1:
        raise ValueError("target R9 paragraph markers are missing or ambiguous")
    start, end = source.index(start_marker), source.index(end_marker)
    if start >= end:
        raise ValueError("target R9 markers are out of order")
    excerpt = source[start:end]
    occurrences = {"native26": native_text.count(excerpt), "api25": api_text.count(excerpt)}
    if occurrences != {"native26": 1, "api25": 1}:
        raise ValueError("complete target #5048 R9 paragraph is not present verbatim once in each instruction")
    return excerpt, {"source": "src/download/prompts/d4d_generic_arm_prompt_v10.md",
        "source_sha256": digest(source.encode()), "start_marker": start_marker, "end_marker": end_marker,
        "excerpt_sha256": digest(excerpt.encode()), "excerpt_bytes": len(excerpt.encode()),
        "verbatim_occurrences": occurrences, "verified_scope": "entire target R9 bullet including #5048 qualifications"}


def joined_render_spec(reg, identity):
    recorded = copy.deepcopy(identity["instruction"]["spec"])
    if recorded.get("shared_generation_registration") != identity["shared_generation"]["registration"]:
        raise ValueError("recorded API instruction names a different captured registration")
    receipt = recorded.get("receipt_completion_registration")
    if type(receipt) is not dict or set(receipt) != {"sha256", "raw_json"} or type(receipt["raw_json"]) is not str:
        raise ValueError("recorded API lacks its exact receipt registration capture")
    receipt_raw = receipt["raw_json"].encode()
    if digest(receipt_raw) != receipt["sha256"] or parsed(receipt_raw) != reg["receipt"]:
        raise ValueError("recorded API receipt registration differs from shared registration")
    expected = {"condition": reg["selection"]["condition"], "render_version": reg["selection"]["renderer"],
        "shared_generation_version": reg["selection"]["version"],
        "api_playbook_version": reg["selection"]["api_playbook_version"],
        "receipt_completion_version": reg["selection"]["receipt_completion_version"],
        "runtime": reg["selection"]["runtime"], "provider": reg["runtime"]["provider"],
        "arm": reg["run"]["arm"], "profile": reg["inputs"]["profile"]["name"],
        "shared_generation_assets": reg["selection"]["assets"]}
    for field, value in expected.items():
        if recorded.get(field) != value:
            raise ValueError("recorded API axis differs from registration: " + field)
    for field, role in (("bundle", "bundle"), ("chunk_manifest", "chunk_manifest"), ("manifest", "source_manifest")):
        pin = reg["inputs"][role]
        if recorded.get(field) != (None if pin is None else pin["path"]):
            raise ValueError("recorded API input differs from registration: " + field)
    for field in ("native_shared_generation_version", "native_source_attribution_version", "removal_repair_version"):
        if type(recorded.get(field, 0)) is not int or recorded.get(field, 0) != 0:
            raise ValueError("recorded API has an incompatible axis: " + field)
    # input_identity deliberately omits profile_basis (api_runner.py:947).
    # Restore it only from that identity's exact captured registration.
    if "profile_basis" in recorded and recorded["profile_basis"] != reg["inputs"]["profile"]["basis"]:
        raise ValueError("recorded API profile basis conflicts with its registration")
    recorded["profile_basis"] = reg["inputs"]["profile"]["basis"]
    return recorded


def settled_usage(ledger):
    """Summarize recorded rows; absent counters stay unknown, not zero."""
    rows = ledger["rows"]
    if type(rows) is not list:
        raise ValueError("ledger rows must be a list")
    identities = []
    for row in rows:
        if (type(row) is not dict or type(row.get("usage_id")) is not str or not row["usage_id"]
                or type(row.get("phase")) is not str or not row["phase"]):
            raise ValueError("settled usage row has no explicit identity/phase")
        identities.append(row["usage_id"])
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate settled usage identity")
    counters = {}
    for field in ("input_tokens", "output_tokens", "cache_read", "cache_write"):
        known, missing = [], []
        for index, row in enumerate(rows):
            value = row.get(field)
            if value is None:
                missing.append(index)
            elif type(value) is not int or value < 0:
                raise ValueError("invalid settled token counter: " + field)
            else:
                known.append(value)
        counters[field] = {"source_field": field, "known_subtotal": sum(known),
            "total": None if missing else sum(known), "missing_row_indexes": missing,
            "complete": not missing}
    durations, missing = [], []
    for index, row in enumerate(rows):
        value = row.get("seconds")
        if value is None:
            missing.append(index)
            durations.append({"usage_id": row["usage_id"], "phase": row["phase"], "seconds": None})
        else:
            if type(value) not in (int, float) or not Decimal(str(value)).is_finite() or value < 0:
                raise ValueError("invalid settled row seconds")
            durations.append({"usage_id": row["usage_id"], "phase": row["phase"], "seconds": str(value)})
    subtotal = sum((Decimal(row["seconds"]) for row in durations if row["seconds"] is not None), Decimal(0))
    return {"scope": "retained API settled rows only; not provider invoice authentication",
        "row_count": len(rows), "usage_ids": identities, "counters": counters,
        "cache_field_mapping": {"cache_read_input_tokens": "cache_read", "cache_creation_input_tokens": "cache_write"},
        "row_durations": durations, "duration_source_field": "seconds",
        "known_duration_seconds_sum": str(subtotal), "duration_seconds_sum": None if missing else str(subtotal),
        "missing_duration_row_indexes": missing,
        "duration_scope": "sum of recorded row durations; excludes gaps and is not native elapsed time",
        "abandoned_calls": "not supplied, not included; absence is not a zero-count assertion",
        "cost_and_subscription_share": "not converted"}


def same_resource(tree, historical, relative, reader, expected=None):
    """Pin the exact active resource at both roots before changing CWD."""
    relative = Path(relative)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError("resource comparison requires an exact repository-relative path")
    current, retained = reader.read(tree / relative), reader.read(historical / relative)
    if current != retained or (expected is not None and digest(retained) != expected):
        raise ValueError("historical renderer resource differs from trial/pin: " + str(relative))
    return {"relative_path": relative.as_posix(), "trial_path": str(tree / relative),
        "historical_path": str(historical / relative), "bytes": len(retained), "sha256": digest(retained)}


@contextmanager
def historical_resource_cwd(directory):
    """Only a read-only renderer runs inside this scope; imports stay isolated."""
    previous = Path.cwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(previous)


def historical_resources(tree, reg, reader):
    from data_sheets_schema import api_runner as api, shared_generation as sg, audit_omissions
    from data_sheets_schema.evidence_assertions import protocol_for_renderer
    from data_sheets_schema.profiles import profile_named
    from data_sheets_schema.resources import checkout_at
    # Derive the original physical checkout from the registered standard full
    # schema. No new registration, alternate caller path, alias or guard is used.
    relative = Path(api.FULL_SCHEMA_PATH)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("API full schema no longer has its standard relative resource spelling")
    original = Path(reg["inputs"]["full_schema"]["root"])
    root = original
    for _part in relative.parts:
        root = root.parent
    if (root / relative != original or root.resolve(strict=True) != root
            or checkout_at(root) != root or Path.cwd() != tree):
        raise ValueError("API replay requires its registration-derived physical checkout and trial start CWD")
    reader.read(root / "pyproject.toml")
    rows = {}
    def pair(relative, expected=None):
        row = same_resource(tree, root, relative, reader, expected)
        rows[row["relative_path"]] = row
    if reg["selection"]["assets"] != sg.ASSET_HASHES:
        raise ValueError("historical API asset roster differs from the selected trial protocol")
    for name, expected in reg["selection"]["assets"].items():
        pair(name, expected)
    # resolve_prompt also reads the selected evidence protocol directly. Its
    # shared/phase contracts are current imported Python, covered by source proof.
    pair(f"src/download/prompts/evidence_protocol_v{protocol_for_renderer(25)}.md")
    for kind, selected in (("full_schema", api.FULL_SCHEMA_PATH), ("core_schema", api.CORE_SCHEMA_PATH)):
        if reg["inputs"][kind]["root"] != str(root / selected):
            raise ValueError("historical schema roots do not share the registered resource checkout")
        for pin in reg["inputs"][kind]["sources"]:
            reader.pin(pin)
            pair(Path(pin["path"]).relative_to(root), pin["sha256"])
    vocabulary = reg["inputs"]["profile"]["vocabulary"]
    actual = profile_named(reg["inputs"]["profile"]["name"]).pin_path
    if (actual is None) != (vocabulary is None):
        raise ValueError("historical/trial profile vocabulary declarations differ")
    if vocabulary is not None:
        relative = Path(actual).absolute().relative_to(tree)
        if vocabulary["path"] != str(root / relative):
            raise ValueError("historical profile vocabulary is outside its resource checkout")
        reader.pin(vocabulary)
        pair(relative, vocabulary["sha256"])
    config = reg["runtime"]["config"]
    if config is not None:
        reader.pin(config)
        pair(Path(config["path"]).relative_to(root), config["sha256"])
    # These validation assets follow imported trial code, not resource CWD.
    adjacent = []
    for name, expected in sorted(audit_omissions.ASSET_SHA256.items()):
        path = (audit_omissions.ASSETS / name).absolute()
        path.relative_to(tree / "src")
        raw = reader.read(path)
        if digest(raw) != expected:
            raise ValueError("trial omission validation asset differs from its pin: " + name)
        adjacent.append({"path": str(path), "bytes": len(raw), "sha256": digest(raw)})
    return root, {"scope": "historical API25 resource replay under current trial imports; not relocated live admission",
        "trial_code_root": str(tree), "historical_resource_root": str(root),
        "historical_resource_head": git_read(root, "rev-parse", "HEAD").decode().strip(),
        "matched_resources": [rows[key] for key in sorted(rows)],
        "trial_module_adjacent_validation_assets": adjacent,
        "registered_input_paths": "unchanged; original bundle/chunks/manifest/context and all ledger pins verified separately",
        "live_cli_refusal": "retained separately; this replay does not overturn its physical-root refusal"}


def capture_protection_paths(tree, root, paths, reader, installed_types=None):
    # Explicit independent discovery bounds, not native execution capacity.
    if installed_types is not None:
        installed_types = Path(installed_types)
        if (not installed_types.is_absolute()
                or installed_types.parts[-5:] != ("linkml_runtime", "linkml_model", "model", "schema", "types.yaml")
                or installed_types.resolve(strict=True) != installed_types):
            raise ValueError("installed protection types must use its exact physical absolute path")
    paths = tuple(sorted(set(Path(path).absolute() for path in paths)))
    if len(paths) > 512:
        raise ValueError("API protection resource roster exceeds 512 files")
    rows, total = {}, 0
    for path in paths:
        if installed_types is not None and path == installed_types:
            relative = "@dependency/linkml_runtime/linkml_model/model/schema/types.yaml"
            origin = "verified_environment_linkml_types"
        elif path.is_relative_to(root):
            relative, origin = path.relative_to(root).as_posix(), "selected_resource_cwd"
        elif path.is_relative_to(tree / "src"):
            relative, origin = path.relative_to(tree).as_posix(), "trial_module_adjacent"
        else:
            raise ValueError("API protection resource is outside selected/trial roots: " + str(path))
        raw = reader.read(path, 64_000_000 - total)
        total += len(raw)
        if relative in rows:
            raise ValueError("ambiguous relative API protection resource: " + relative)
        rows[relative] = {"path": str(path), "bytes": len(raw), "sha256": digest(raw), "origin": origin}
    return {"roster": [str(path) for path in paths], "files": rows, "bytes": total,
            "max_files": 512, "max_bytes": 64_000_000}


def protection_resources(tree, original, spec, reader, installed_types=None):
    from data_sheets_schema.shared_generation_resources import resource_paths
    captured = {}
    for label, root in (("historical", original), ("trial", tree)):
        with historical_resource_cwd(root):
            captured[label] = capture_protection_paths(tree, root, resource_paths((spec,)), reader, installed_types)
    historical, trial = captured["historical"]["files"], captured["trial"]["files"]
    comparisons = []
    for relative in sorted(set(historical) | set(trial)):
        left, right = historical.get(relative), trial.get(relative)
        comparisons.append({"relative_path": relative, "historical": left, "trial": right,
            "same_bytes": left is not None and right is not None and (left["bytes"], left["sha256"]) == (right["bytes"], right["sha256"])})
    return {"scope": "write-footprint protection/discovery reads; differences are retained, not scientific equivalence",
        "discovery": "shared_generation_resources.resource_paths; no changed guard or registration",
        "installed_dependency_scope": "only the exact LinkML types file from the verified environment; captured current bytes, not a historical dependency pin",
        "roots": captured, "comparisons": comparisons}


def render_api_instruction(tree, root, recorded, reg, reader, installed_types=None):
    """Run the actual isolated trial renderer on pinned historical resources."""
    from data_sheets_schema import api_runner as api
    # from_render_spec itself verifies active playbook/receipt/shared assets;
    # therefore both construction and rendering use the original resource CWD.
    with historical_resource_cwd(root):
        spec = api.RunSpec.from_render_spec(recorded, **{k: reg["run"][k] for k in ("project", "method", "label")})
        protection = protection_resources(tree, root, spec, reader, installed_types)
        text = api.resolve_prompt(spec)
        if protection_resources(tree, root, spec, reader, installed_types) != protection:
            raise ValueError("API protection resource roster changed during historical replay")
        return text, protection


def replay_historical_instruction(tree, root, recorded, reg, expected_sha, reader, installed_types=None, diagnostics=None):
    text, protection = render_api_instruction(tree, root, recorded, reg, reader, installed_types)
    observed_sha = digest(text.encode())
    if observed_sha != expected_sha:
        if diagnostics is not None:
            diagnostics.update(candidate_text=text, expected_sha256=expected_sha,
                observed_sha256=observed_sha, protection_resource_observations=protection)
        raise ValueError("API25 replay is not byte-identical to its recorded instruction")
    return text, protection


def load_api(args, reader, report, files=None):
    mode = getattr(args, "api_instruction_mode", "exact-historical")
    if mode not in API_INSTRUCTION_MODES:
        raise ValueError("unknown API instruction comparison mode")
    report["api_instruction_mode"] = mode
    from data_sheets_schema import api_runner as api, shared_generation as sg
    raw = reader.read(args.api_registration, 8_000_000)
    reg = sg.parse_registration(raw)
    if (reg["format"] != "shared_generation_registration_v1" or reg["run"]["project"] != "CHORUS"
            or reg["selection"]["condition"] != "generic_v10" or reg["selection"]["renderer"] != 25):
        raise ValueError("comparison requires an explicitly selected CHORUS generic_v10 API25 registration")
    if reg["registration_path"] != str(Path(args.api_registration).absolute()):
        raise ValueError("existing API registration was read from another path")
    ledger = parsed(reader.read(args.api_ledger))
    identity = ledger["input_identity"]
    expected_sha = identity["instruction"]["sha256"]
    if (type(expected_sha) is not str or len(expected_sha) != 64
            or set(expected_sha) - set("0123456789abcdef")):
        raise ValueError("recorded API instruction requires an exact SHA256")
    captured = identity["shared_generation"]["registration"]
    if captured != {"sha256": digest(raw), "raw_json": raw.decode("utf-8")}:
        raise ValueError("API ledger does not capture this exact registration")
    if ledger["identity"] != {k: reg["run"][k] for k in ("project", "method", "label")} | {"condition": "generic_v10"}:
        raise ValueError("API ledger belongs to another run")
    for pin in identity["shared_generation"]["files"]:
        reader.pin(pin)
    recorded = joined_render_spec(reg, identity)
    # These validated settled rows remain useful evidence even if the strict
    # historical resource/SHA replay below refuses. No native success implied.
    report["settled_api_usage"] = settled_usage(ledger)
    root, replay = historical_resources(Path(args.tree).resolve(strict=True), reg, reader)
    # This exact dependency is imported by the record/source schemas. The
    # environment was verified before imports; no directory-wide exemption,
    # alternate caller root, or production discovery change is introduced.
    dependency_site = Path(report["import_environment"]["dependency_environment"]["site_packages"])
    installed_types = dependency_site / "linkml_runtime/linkml_model/model/schema/types.yaml"
    diagnostics = {}
    try:
        if mode == "exact-historical":
            text, protection = replay_historical_instruction(
                Path(args.tree).resolve(strict=True), root, recorded, reg, expected_sha,
                reader, installed_types, diagnostics)
        else:
            text, protection = render_api_instruction(
                Path(args.tree).resolve(strict=True), root, recorded, reg, reader, installed_types)
        replay["protection_resource_observations"] = protection
    except ValueError:
        if diagnostics:
            candidate = diagnostics.pop("candidate_text").encode()
            filename = "unverified-api-replay-candidate.txt"
            if files is not None:
                files[filename] = candidate
            report["api_replay_candidate"] = {**diagnostics,
                "scope": "unverified diagnostic candidate; historical instruction identity failed",
                "file": filename if files is not None else None, "bytes": len(candidate),
                "exact_historical_instruction_verified": False}
            context = {**replay, "exact_historical_instruction_verified": False}
            observations = (
                ("historical_resource_head_observed_after", lambda: git_read(root, "rev-parse", "HEAD").decode().strip()),
                ("trial_cwd_restored", lambda: Path.cwd() == Path(args.tree).resolve(strict=True)),
            )
            for field, observe in observations:
                try:
                    context[field] = observe()
                except Exception as secondary:
                    # Secondary diagnostics cannot replace the original
                    # instruction-identity refusal. Final source/input
                    # checks below main's handler remain mandatory.
                    context[field] = None
                    context.setdefault("diagnostic_observation_errors", []).append({
                        "field": field, "type": type(secondary).__name__, "message": str(secondary)[:2000]})
            report["historical_api_resource_replay"] = context
        # A diagnostic candidate never permits native rendering or sizing.
        # Main still proves all source origins and rereads every input before
        # publishing any retained bytes, including this failed candidate.
        raise
    if git_read(root, "rev-parse", "HEAD").decode().strip() != replay["historical_resource_head"]:
        raise ValueError("historical resource checkout HEAD changed during replay")
    observed_sha = digest(text.encode())
    replay.update(api_instruction_mode=mode, instruction_sha256=observed_sha,
                  historical_instruction_sha256=expected_sha,
                  matches_historical_instruction=observed_sha == expected_sha,
                  exact_historical_instruction_verified=mode == "exact-historical",
                  trial_cwd_restored=Path.cwd() == Path(args.tree).resolve(strict=True))
    if mode == "current-target":
        replay["scope"] = ("current integrated trial API25 rendering on fixed historical inputs; "
            "not historical instruction replay acceptance or byte-identical target-commit source")
    if not replay["trial_cwd_restored"]:
        raise ValueError("historical replay did not restore the trial resource CWD")
    return reg, ledger, text, replay


def native_case(args, reader, reg, destination):
    from data_sheets_schema import api_runner as api, native_shared_contract as c
    from data_sheets_schema import native_shared_selection as selected, native_shared_render as render
    from data_sheets_schema import agentic_runtime
    from data_sheets_schema.native_execution_registration import ROUTE
    from data_sheets_schema.schema_snapshot import capture_schema
    from data_sheets_schema.resources import resource_path

    def artifact(role, path, raw):
        return c.CapturedArtifact(c.ArtifactPin(role, str(path), len(raw), c.sha(raw)), raw)
    def pin(item):
        return {k: getattr(item.pin, k) for k in ("path", "bytes", "sha256")}
    root = destination / "hypothetical-unwritten"
    bounds = c.parse_bounds(candidate_bounds(args.scenario))
    assets = selected.capture_assets()
    for item in assets:
        if reader.read(item.pin.path) != item.raw:
            raise ValueError("native asset changed during capture")
    authority = list(assets)
    inputs = {"project": "CHORUS", "profile": copy.deepcopy(reg["inputs"]["profile"])}
    for role in ("bundle", "chunk_manifest", "context", "source_manifest"):
        declared = reg["inputs"][role]
        if declared is None:
            raise ValueError("CHORUS comparison requires explicit " + role)
        raw = reader.pin(declared)
        item = artifact(role, declared["path"], raw)
        authority.append(item)
        inputs[role] = pin(item)
    vocab = inputs["profile"]["vocabulary"]
    if vocab is not None:
        authority.append(artifact("vocabulary", vocab["path"], reader.pin(vocab)))
    schema_items = {}
    for kind, cls, source in (("full", "Dataset", api.FULL_SCHEMA_PATH), ("core", "CoreDataset", api.CORE_SCHEMA_PATH)):
        path = resource_path(source).absolute()
        snapshot = capture_schema(path, strict=True, read_bytes=reader.read)
        old = reg["inputs"][kind + "_schema"]["sources"]
        if [digest(raw) for _, _, raw in snapshot.sources] != [row["sha256"] for row in old]:
            raise ValueError("trial schema bytes differ from the retained API proxy: " + kind)
        rows = []
        for index, (name, path, raw) in enumerate(snapshot.sources):
            item = artifact(f"{kind}_schema:{index}", path, raw)
            schema_items[item.pin.role] = item
            rows.append({"name": str(name), **pin(item)})
        inputs[kind + "_schema"] = {"root": str(snapshot.sources[0][1]), "root_class": cls, "sources": rows}
    policy = artifact("receipt_policy", root / "receipt-policy.json", c.canonical({
        "kind": c.KINDS["receipt_policy"], "version": 1, "registration_id": "hypothetical-pending-floor",
        "condition": c.CONDITION, "runtime_policy_sha256": selected.RECEIPT_POLICY_SHA256,
        "receipt_instrument_version": 4, "coverage_floor": {"state": "pending", "mode": "diagnostic_pilot"}}))
    axes = {k: v for k, v in selected.descriptor().items()
            if k not in {"typed_protocol", "projection", "receipt_policy", "assets"}}
    run = {"project": "CHORUS", "arm": reg["run"]["arm"], "method": "claudecode_direct", "label": args.label}
    doc = {"kind": c.KINDS["selection"], "version": 1, "registration_id": "hypothetical-not-registered",
        "registration_path": str(root / "selection.json"), "stage_root": str(root / "stages"), "run": run,
        "selection": {**axes, "descriptor_sha256": selected.descriptor_capture().sha256,
            "assets": {a.pin.role[len("asset:"):]: pin(a) for a in assets}},
        "inputs": inputs, "receipt_policy": pin(policy), "bounds": bounds}
    selection = selected.rebuild(artifact("selection", doc["registration_path"], c.canonical(doc)),
        tuple(authority), selected._declared_schemas(doc, schema_items), policy)
    runtime_doc = {"route": ROUTE, "executable": {"status": "not_selected_or_executed"},
        "model": MODEL, "auxiliary_models": [], "effort": args.hypothetical_effort,
        "limits": {"contextWindow": args.hypothetical_context, "maxOutputTokens": args.hypothetical_output},
        "limits_basis": "hypothetical sizing assumption only; native capacity not observed",
        "provider": PROVIDER, "auth": {"status": "not_observed"}, "environment": {},
        "deadline_seconds": None, "budget_guard_usd": None, "keep_awake": {"status": "not_observed"}}
    runtime = artifact("runtime_declaration", root / "runtime.json", c.canonical(runtime_doc))
    tools = agentic_runtime.toolchain()
    paths = {"full": str(root / "outputs" / "CHORUS_d4d.yaml"),
        "core": str(root / "outputs" / "CHORUS_d4d_core.yaml"),
        "receipt": str(root / "outputs" / "CHORUS_coverage_receipt.yaml"),
        "report": str(root / "outputs" / "CHORUS_reconciliation.md")}
    metadata = {"native_shared_generation_version": 1,
        "native_shared_generation_descriptor": selected.descriptor(),
        "native_shared_generation_registration": {"sha256": selection.registration.pin.sha256,
            "raw_json": selection.registration.raw.decode()},
        "native_shared_generation_context": selection.generation_context(),
        "native_shared_receipt_policy": render._raw_identity(policy),
        "native_shared_runtime_declaration": render._raw_identity(runtime),
        "native_shared_max_draft_checks": args.hypothetical_drafts}
    recorded = {**metadata, "condition": c.CONDITION, "render_version": 26,
        "arm": run["arm"], "bundle": inputs["bundle"]["path"], "manifest": inputs["source_manifest"]["path"],
        "chunk_manifest": inputs["chunk_manifest"]["path"], "manifest_line": "# Source manifest: " + inputs["source_manifest"]["path"],
        "profile": inputs["profile"]["name"], "profile_basis": inputs["profile"]["basis"],
        "runtime": c.RUNTIME, "provider": PROVIDER, "reasoning_effort": args.hypothetical_effort,
        "run_date": args.date, "prompt_text_env": True, "chunk_check_uses_manifest": True,
        "agentic_artifact_paths": paths, "agentic_toolchain": tools}
    spec = api.RunSpec.from_render_spec(recorded, project="CHORUS", method=run["method"], label=run["label"])
    text = render.instruction(spec)
    return selection, runtime, spec, text


def stage_case(selection, runtime, spec, instruction, full, core, receipt):
    """Construct honest invented in-memory bindings, not observed authority."""
    from data_sheets_schema import native_shared_contract as c, native_shared_stage as stage
    def at(role, raw):
        return c.CapturedArtifact(c.ArtifactPin(role, selection.role(role), len(raw), c.sha(raw)), raw)
    def invented(role):
        return at(role, c.canonical({"scope": SCOPE, "not_observed": role}))
    def observation(number):
        raw = c.canonical({"scope": SCOPE, "not_observed": number})
        return c.CapturedArtifact(c.ArtifactPin("observation", selection.role("observations_root") + f"/{number:06d}.json", len(raw), c.sha(raw)), raw)
    exe = c.ExecutionBinding(attempt_id="hypothetical-attempt", session_id="hypothetical-session-not-observed",
        selection_sha256=selection.registration.pin.sha256, execution=invented("execution_capture"),
        started=invented("started_capture"), binding_artifact=invented("session_binding"), init_observation=observation(0),
        instruction_sha256=digest(instruction.encode()), permission_sha256=digest(b"not-observed"),
        runtime_declaration=runtime, runtime_declaration_sha256=runtime.pin.sha256,
        registered_python=spec._agentic_toolchain["python"], working_directory=str(Path.cwd()))
    phase = c.Phase1Capture(full=at("phase1_full", full), original_receipt=at("phase1_receipt", receipt),
        seal=invented("phase1_seal"), full_seal_observation=observation(1), core=at("phase1_core", core),
        core_seal=invented("core_seal"), core_seal_observation=observation(2))
    journal = at("journal", stage.journal_bytes(selection_sha256=selection.registration.pin.sha256,
        execution_sha256=exe.execution.pin.sha256, attempt_id=exe.attempt_id, records=()))
    history = c.RawHistory(journal=journal, records=(), artifacts=(), observations=())
    entries = (("genesis", {"execution": c.pin_dict(exe.execution.pin), "started": c.pin_dict(exe.started.pin)}),
        ("session_bound", {"binding": c.pin_dict(exe.binding_artifact.pin), "init_observation": c.pin_dict(exe.init_observation.pin)}),
        ("phase1_sealed", {"seal": c.pin_dict(phase.seal.pin), "full": c.pin_dict(phase.full.pin),
            "original_receipt": c.pin_dict(phase.original_receipt.pin), "observation": c.pin_dict(phase.full_seal_observation.pin)}))
    rows, journal = stage.append_records(selection, exe, history, tuple((key, c.canonical(value)) for key, value in entries))
    captured = lambda value: c.CapturedArtifact(value.pin, value.raw)
    history = replace(history, records=tuple(captured(row) for row in rows), journal=captured(journal))
    # The constructor's original history checks run. No __new__, method
    # replacement, patched guard or suppression is used to enter _request.
    return stage._Replay(selection, exe, phase, history)


def sizing_bound_coverage(selection, instruction):
    """Describe measured static carriers, without certifying a future run."""
    from data_sheets_schema import native_shared_contract as c
    bounds, doc = selection.bounds(), selection.document()
    artifacts = (selection.receipt_policy, *selection.authority,
        *(source for schema in selection.schemas for source in schema.sources))
    by_path = {}
    for item in artifacts:
        if item.pin.path in by_path and by_path[item.pin.path] != item.raw:
            raise ValueError("hypothetical authority path has inconsistent bytes")
        by_path[item.pin.path] = item.raw
    inputs = []
    for role in ("bundle", "chunk_manifest", "context", "source_manifest", "vocabulary"):
        declared = (doc["inputs"]["profile"]["vocabulary"] if role == "vocabulary"
                    else doc["inputs"][role])
        if declared is not None:
            inputs.append({"role": role, "bytes": len(selection.raw(declared["path"])),
                "max_input_bytes": bounds["max_input_bytes"]})
    return {"scope": "exact named hypothetical carriers and per-request serialization only",
        "static_checks_completed": {
            "authority": {"unique_files_including_selection": len(by_path) + 1,
                "max_files": c.HARD_LIMITS["authority_files"],
                "bytes_including_selection": len(selection.registration.raw) + sum(map(len, by_path.values())),
                "max_authority_bytes": bounds["max_authority_bytes"],
                "guard": "native_shared_contract.parse_selection; native_shared_selection.rebuild"},
            "inputs": inputs,
            "instruction": {"bytes": len(instruction.encode("utf-8")),
                "max_request_bytes": bounds["max_request_bytes"],
                "guard": "native_shared_render.instruction"}},
        "request_guards": "native_shared_stage._Replay._request including complete outer request; no truncation",
        "inventory_guards": "native_shared_stage._Replay._packet and typed_audit planner; no truncation",
        "history_scope": "only invented genesis/session_bound/phase1_sealed records; no response transitions",
        "execution_capacity_verified": False,
        "not_measured": [
            "complete evolving journal, record count, observations and failure-finalization reserves",
            "complete cumulative evidence pool, transcript/control stream and final saved wire",
            "future native responses, integration assembly and final reconciliation/report artifacts",
            "future request changes from native outputs, real identity strings and selected output paths",
            "model context/token capacity, subscription share and elapsed time"],
        "execution_or_launch_authority": "none; invented carriers are not observed native evidence"}


def ledger_proxy_file(reader, path, pin, historical_root, label, limit=MAX_READ):
    """Bind a proxy container to the already joined run ledger, without accepting its contents."""
    if (type(pin) is not dict or type(pin.get("path")) is not str
            or ".." in Path(pin["path"]).parts or Path(historical_root) / pin["path"] != path):
        raise ValueError(label + " path differs from validated API ledger")
    raw = reader.read(path, limit)
    if pin.get("sha256") != digest(raw):
        raise ValueError(label + " bytes differ from validated API ledger")
    return raw


def current_proxy_containers(args, reader, ledger, api_render):
    from data_sheets_schema import typed_audit as typed
    root = Path(args.proxy_intermediate).absolute()
    historical = api_render["historical_resource_root"]
    packet_raw = ledger_proxy_file(reader, root / "CHORUS_typed_audit_packet.json",
        ledger["typed_audit"]["packet"], historical, "proxy packet", typed.MAX_PACKET_BYTES)
    assembly_raw = ledger_proxy_file(reader, root / "CHORUS_typed_audit_assembly.json",
        ledger["typed_audit"]["assembly"], historical, "proxy assembly", typed.MAX_ASSEMBLY_BYTES)
    packet, saved = parsed(packet_raw), parsed(assembly_raw)
    if (packet.get("kind") != typed.PACKET or packet.get("project") != "CHORUS" or saved.get("kind") != typed.ASSEMBLY
            or encoded(saved["packet"]) != encoded(packet)):
        raise ValueError("proxy assembly does not contain the exact ledger-pinned packet")
    report = {"scope": "ledger-pinned historical API containers only; not accepted historical packets or answers",
        "packet_file_sha256": digest(packet_raw), "assembly_file_sha256": digest(assembly_raw),
        "historical_packet_acceptance_claimed": False, "historical_request_identities_validated": False,
        "historical_source": "later API producer; current native contracts may differ",
        "current_source": "integrated trial native26; every consumed proxy answer must pass current guards"}
    try:
        typed._open(packet)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        report["current_source_open_observation"] = {"accepted": False,
            "type": type(exc).__name__, "message": str(exc)[:2000]}
    else:
        report["current_source_open_observation"] = {"accepted": True}
    expected = {"original_full", "original_core", "bundle", "manifest", "receipt", "context", "source_manifest"}
    if type(packet.get("inputs")) is not dict or set(packet["inputs"]) != expected:
        raise ValueError("CHORUS proxy requires exact phase1/source input blob roster")
    raw = {name: typed._unblob(value) for name, value in packet["inputs"].items()}
    report["raw_inputs"] = {name: {"sha256": digest(value), "bytes": len(value)} for name, value in raw.items()}
    return packet, raw, saved, report


def opaque_worker_answer(saved, packet, worker_id):
    """Extract checksummed bytes, deliberately making no old request/coverage acceptance claim."""
    from data_sheets_schema import typed_audit as typed, audit_grammar
    raw = typed._unblob(saved["workers"][worker_id], typed.MAX_SAVED_RESPONSE_BYTES)
    value = typed._bounded_json(raw, "historical worker proxy envelope", typed.MAX_SAVED_RESPONSE_BYTES)
    if (set(value) != {"kind", "packet_sha256", "request_sha256", "worker_id", "response"}
            or value["kind"] != "typed_audit_worker_response_v1" or value["worker_id"] != worker_id
            or value["packet_sha256"] != packet["sha256"]):
        raise ValueError("historical proxy worker envelope identity differs from its container")
    return typed._unblob(value["response"], audit_grammar.MAX_BYTES)


def receipt_proxy_transport(raw):
    """Remove only the released API decoder's enclosing fence, preserving its exact inner bytes."""
    from data_sheets_schema import rereceipt
    import yaml
    grammar = r"\A\s*```(?:ya?ml)?[ \t]*\r?\n(.*?)\r?\n[ \t]*```\s*\Z"
    text = raw.decode("utf-8")
    match = re.match(grammar, text, re.S | re.I)
    inner = match.group(1).encode("utf-8") if match else raw
    prefix, suffix = (text[:match.start(1)].encode(), text[match.end(1):].encode()) if match else (b"", b"")
    if prefix + inner + suffix != raw:
        raise ValueError("receipt fence transformation changed inner bytes")
    try:
        old_answers, new_answers = rereceipt.parse_answers(raw), rereceipt.parse_answers(inner)
    except yaml.YAMLError as exc:
        raise ValueError("released API receipt decoder refused proxy text: " + type(exc).__name__) from exc
    if encoded(old_answers) != encoded(new_answers):
        raise ValueError("receipt transport transformation changed released API answers")
    return inner, {"transformation": "remove_exact_enclosing_yaml_fence" if match else "unchanged_unfenced",
        "scope": "historical API transport adapter only; current native validator still required",
        "released_api_decoder": "data_sheets_schema.rereceipt.parse_answers", "anchored_grammar": grammar,
        "raw_sha256": digest(raw), "raw_bytes": len(raw), "inner_sha256": digest(inner), "inner_bytes": len(inner),
        "removed_prefix_bytes": len(prefix), "removed_suffix_bytes": len(suffix),
        "removed_prefix_sha256": digest(prefix), "removed_suffix_sha256": digest(suffix),
        "exact_inner_bytes_preserved": True, "released_api_answers_equal": True,
        "parsed_answer_count": len(new_answers), "parsed_answers_sha256": digest(encoded(new_answers))}


def size_proxy(args, reader, selection, runtime, spec, instruction, files, *, ledger=None, api_render=None):
    from data_sheets_schema import native_shared_contract as c, native_shared_receipts as nr
    from data_sheets_schema import typed_audit as typed, audit_omissions as omissions, audit_batches as batches
    root = Path(args.proxy_intermediate).absolute()
    current_proxy = args.action == "size-current-proxy"
    container_report, saved = None, None
    if current_proxy:
        packet, raw_inputs, saved, container_report = current_proxy_containers(args, reader, ledger, api_render)
        files["proxy-historical-containers.json"] = encoded(container_report)
        receipt_inputs = parsed(ledger_proxy_file(reader, root / "CHORUS_receipt_completion_inputs.json",
            ledger["receipt_completion"]["inputs"], api_render["historical_resource_root"], "receipt proxy inputs"))
    else:
        packet = parsed(reader.read(root / "CHORUS_typed_audit_packet.json"))
        raw_inputs, _ = typed._open(packet)
        receipt_inputs = parsed(reader.read(root / "CHORUS_receipt_completion_inputs.json"))
    if receipt_inputs["record"].encode() != raw_inputs["original_full"]:
        raise ValueError("receipt and typed originals differ")
    for old, role in (("bundle", "bundle"), ("manifest", "chunk_manifest"), ("context", "context"), ("source_manifest", "source_manifest")):
        if raw_inputs[old] != selection.raw(role):
            raise ValueError("proxy source differs from hypothetical selection: " + role)
    if (reader.read(root / "CHORUS_full.yaml") != raw_inputs["original_full"]
            or reader.read(root / "CHORUS_core.yaml") != raw_inputs["original_core"]):
        raise ValueError("proxy must use the retained phase1 full/core snapshots")
    replay = stage_case(selection, runtime, spec, instruction, raw_inputs["original_full"],
        raw_inputs["original_core"], receipt_inputs["receipt"].encode())
    rows, problems, transformations = [], [], []
    progress = {"scope": SCOPE, "requests": rows, "transformations": transformations,
        "future_native_requests_measured": False, "request_roster_complete_for_named_proxy": False,
        "bound_coverage": sizing_bound_coverage(selection, instruction)}
    if current_proxy:
        progress["historical_containers"] = container_report
        progress["proxy_mode"] = "current native requests with historical opaque answer bytes; no original packet acceptance"
    # Retain already measured complete wires if a later bound/answer fails.
    # Caller writes this payload before reporting the specific refusal.
    files["proxy-sizing-progress.json"] = encoded(progress)
    ordinal = 1
    def measure(kind, target):
        nonlocal ordinal
        cursor = c.StageCursor(ordinal=ordinal, kind=kind, target_id=target)
        artifact, response, inner, _, _ = replay._request(cursor, replay.h.journal.pin.sha256)
        inner_bytes = len(c.canonical(inner))
        payload_bytes = len(c.canonical(c.strict_json(artifact.raw,
            max_bytes=selection.bounds()["max_request_bytes"])["payload"]))
        name = f"proxy-{ordinal:03d}-{kind}.json"
        # The file is an evidence wrapper, intentionally not an executable
        # native request artifact. The nested string preserves exact bytes.
        files[name] = encoded({"scope": SCOPE, "outer_sha256": digest(artifact.raw),
            "request_bytes": len(artifact.raw), "hypothetical_request_json": artifact.raw.decode()})
        rows.append({"kind": kind, "target": target, "outer_bytes": len(artifact.raw),
            "inner_bytes": inner_bytes, "payload_bytes": payload_bytes,
            "outer_minus_inner_bytes": len(artifact.raw) - inner_bytes,
            "outer_wrapper_bytes": len(artifact.raw) - payload_bytes,
            "byte_difference_scope": "arithmetic differences of complete canonical serializations, not token estimates",
            "response_destination_max_bytes": response.max_bytes,
            "max_request_bytes": selection.bounds()["max_request_bytes"],
            "sha256": digest(artifact.raw), "evidence_file": name})
        files["proxy-sizing-progress.json"] = encoded(progress)
        ordinal += 1
        return inner
    request = nr.prepare(selection, replay.e, replay.p)
    if request["requested_paths"]:
        measure("receipt", "receipt")
        response_raw = (ledger_proxy_file(reader, root / "CHORUS_receipt_completion_response.json",
            ledger["receipt_completion"]["response"], api_render["historical_resource_root"], "receipt proxy response")
            if current_proxy else reader.read(root / "CHORUS_receipt_completion_response.json"))
        response = parsed(response_raw)
        if response.get("stop_reason") != "end_turn" or type(response.get("text")) is not str:
            raise ValueError("retained receipt answer is not a complete textual answer")
        receipt_answer = response["text"].encode()
        if current_proxy:
            files["proxy-receipt-original-answer.txt"] = receipt_answer
            receipt_answer, transport = receipt_proxy_transport(receipt_answer)
            files["proxy-receipt-native-answer.yaml"] = receipt_answer
            files["proxy-receipt-transport.json"] = encoded(transport)
            progress["receipt_transport"] = transport
            transformations.append("Receipt proxy transport: " + transport["transformation"]
                + "; exact inner bytes and released API answers preserved; native validation pending.")
            files["proxy-sizing-progress.json"] = encoded(progress)
    else:
        receipt_answer = None
        progress["receipt_state"] = "verified_zero_work_no_answer_consumed"
    replay.receipt = nr.complete(selection, replay.e, replay.p, receipt_answer)
    receipt_result = c.strict_json(replay.receipt.result_json)
    files["proxy-native-receipt-result.json"] = encoded({"scope": SCOPE, "result": receipt_result})
    if receipt_result["state"] != "answers_complete":
        raise ValueError("historical receipt answer does not complete the native proxy request")
    if replay.receipt.effective_receipt != raw_inputs["receipt"]:
        raise ValueError("native reconstruction differs from the historical effective receipt bytes")
    transformations.append("Native receipt1 replay (or verified zero work) produces the exact historical effective receipt bytes.")
    replay.packet = replay._packet()
    plan = replay.packet["plan"]
    files["proxy-inventory.json"] = encoded({"scope": SCOPE, "plan": plan})
    inventory_rows = {row["path"]: row for row in plan["inventory"]["values"]}
    allocations = []
    for worker in plan["workers"]:
        allocated = [inventory_rows[path] for path in worker["paths"]]
        allocated_bytes = len(batches.canonical_bytes(allocated))
        if allocated_bytes != worker["inventory_bytes"]:
            raise ValueError("worker inventory byte count differs from complete assigned rows")
        allocations.append({"worker": worker["id"], "paths": len(allocated), "inventory_bytes": allocated_bytes,
            "max_paths": selection.bounds()["max_paths_per_worker"],
            "max_inventory_bytes": selection.bounds()["max_inventory_bytes"]})
    inventory_sizes = {"paths": len(inventory_rows), "max_populated_paths": selection.bounds()["max_populated_paths"],
        "all_values_bytes": len(batches.canonical_bytes(plan["inventory"]["values"])),
        "full_inventory_object_bytes": len(batches.canonical_bytes(plan["inventory"])),
        "worker_count": len(allocations), "max_workers": selection.bounds()["max_workers"],
        "allocations": allocations, "inventory_byte_bound_scope": "per worker assigned rows, not global inventory"}
    progress["inventory"] = inventory_sizes
    files["proxy-sizing-progress.json"] = encoded(progress)
    if len(plan["workers"]) + 2 + bool(request["requested_paths"]) > selection.bounds()["max_submissions"]:
        raise ValueError("complete native roster exceeds hypothetical max_submissions")
    same_partition = c.canonical(plan) == c.canonical(packet["plan"])
    if saved is None:
        saved = parsed(reader.read(root / "CHORUS_typed_audit_assembly.json"))
    if saved["packet"] != packet:
        raise ValueError("retained assembly belongs to another typed packet")
    old_workers = saved["workers"]
    for worker in plan["workers"]:
        key = worker["id"]
        inner = measure("worker", key)
        if same_partition:
            if current_proxy:
                answer = opaque_worker_answer(saved, packet, key)
            else:
                original_saved = typed._unblob(old_workers[key], typed.MAX_SAVED_RESPONSE_BYTES)
                original_request = typed.worker_request(packet, key)
                answer = typed._unwrap(original_saved, original_request)
                if not typed.check_worker(packet, key, original_saved)["passed"]:
                    raise ValueError("historical worker fails original structural coverage: " + key)
            transformed = typed.capture_response(inner, answer)
            if not typed.check_worker(replay.packet, key, transformed, **replay.options)["passed"]:
                raise ValueError("historical worker is incompatible with native proxy: " + key)
            replay.workers[key] = transformed
            transformations.append(f"{key}: checksummed historical inner answer {digest(answer)} re-enveloped for current hypothetical packet; "
                + ("old request not accepted; " if current_proxy else "") + "current worker guard passed; not native delivery.")
    measure("omission", "omission")
    if same_partition:
        omission = typed._unblob(saved["omission_response"], omissions.MAX_RESPONSE_BYTES)
        if not current_proxy:
            # Strict legacy mode still requires original packet/request joins.
            typed.index(packet, {key: typed._unblob(value, typed.MAX_SAVED_RESPONSE_BYTES)
                for key, value in old_workers.items()}, omission)
        replay.omission = omission
        # _request invokes the actual current typed.index/omission check.
        # Any identity or coverage refusal retains prior measured wires.
        measure("integration", "integration")
        transformations.append("Exact historical omission answer " + digest(omission) + " reused after "
            + ("current proxy index validation; original packet not accepted." if current_proxy
               else "original and proxy index validation."))
    else:
        problems.append("changed_partition: historical worker answers cannot be transferred; integration remains unmeasured")
    progress.update(request_roster_complete_for_named_proxy=same_partition, unmeasured=problems)
    files["proxy-sizing-progress.json"] = encoded(progress)
    return {"requests": rows, "request_roster_complete_for_named_proxy": same_partition,
        "historical_containers": container_report,
        "future_native_requests_measured": False, "same_historical_partition": same_partition,
        "inventory": inventory_sizes,
        "bound_coverage": progress["bound_coverage"],
        "execution_capacity_verified": False,
        "transformations": transformations, "unmeasured": problems,
        "token_context_weekly_share_wall_clock": "not established by offline serialized byte sizes"}


def packet_differences(recorded, derived):
    """Bounded exact JSON differences; never normalize a saved packet for acceptance."""
    rows, visited, truncated = [], 0, False

    def identity(value):
        raw = encoded(value)
        result = {"type": type(value).__name__, "bytes": len(raw), "sha256": digest(raw)}
        if len(raw) <= 240:
            result["value"] = value
        return result

    def walk(old, new, path=""):
        nonlocal visited, truncated
        visited += 1
        if visited > 200_000 or len(rows) >= 100 or path.count("/") > 64:
            truncated = True
            return
        if encoded(old) == encoded(new):
            return
        if type(old) is dict and type(new) is dict and set(old) == set(new):
            for key in sorted(old):
                walk(old[key], new[key], path + "/" + key.replace("~", "~0").replace("/", "~1"))
        elif type(old) is list and type(new) is list and len(old) == len(new):
            for index, (left, right) in enumerate(zip(old, new)):
                walk(left, right, path + "/" + str(index))
        else:
            row = {"pointer": path or "/", "recorded": identity(old), "derived": identity(new)}
            if type(old) is str and type(new) is str:
                diff = "".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                    fromfile="retained", tofile="current-derived"))
                row.update(text_diff=diff[:8000], text_diff_truncated=len(diff) > 8000)
            rows.append(row)
    walk(recorded, derived)
    return {"exactly_equal": encoded(recorded) == encoded(derived),
        "differences": rows, "visited": visited, "truncated": truncated,
        "limits": {"differences": 100, "visited": 200_000, "pointer_depth": 64, "diff_characters_per_row": 8000}}


def diagnose_packet(args, reader, api_render, ledger):
    """Observe unchanged production refusal and rederivation; no rebuilt packet is consumed."""
    from data_sheets_schema import typed_audit as typed
    root = Path(args.proxy_intermediate).absolute()
    path = root / "CHORUS_typed_audit_packet.json"
    raw = reader.read(path, typed.MAX_PACKET_BYTES)
    packet = parsed(raw)
    historical = Path(api_render["historical_resource_root"])
    pin = ledger["typed_audit"]["packet"]
    if (type(pin.get("path")) is not str or ".." in Path(pin["path"]).parts
            or historical / pin["path"] != path or pin.get("sha256") != digest(raw)):
        raise ValueError("diagnostic packet differs from the validated API ledger pin")
    report = {"scope": "diagnostic only; no packet substitution, response acceptance or sizing",
        "ledger_packet_pin": dict(pin), "file_sha256": digest(raw),
        "saved_packet_sha256": packet.get("sha256"), "observations": []}
    initial_cwd = Path.cwd()
    for label, directory in (("trial", Path(args.tree).resolve(strict=True)), ("historical", historical)):
        row = {"resource_cwd": str(directory), "label": label}
        with historical_resource_cwd(directory):
            try:
                typed._open(packet)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                row["production_open"] = {"accepted": False, "type": type(exc).__name__, "message": str(exc)[:2000]}
                # This is the production _open reconstruction formula, used only
                # for diagnostics after preserving its refusal. Never pass the
                # candidate to any consumer or accept its newly computed hash.
                try:
                    derived, _, _ = typed._derive(packet["inputs"], packet["schema_sources"], packet["project"], packet["limits"])
                    expected = typed._seal({**{key: packet[key] for key in
                        ("kind", "protocol", "inputs", "schema_sources", "project", "limits")},
                        **derived, "limitations": list(typed.LIMITATIONS)})
                    row["derived_packet_sha256"] = expected["sha256"]
                    row["packet_comparison"] = packet_differences(packet, expected)
                    row["shared_context_comparison"] = packet_differences(
                        parsed(packet["requests"]["shared_context"].encode()),
                        parsed(expected["requests"]["shared_context"].encode()))
                except (ValueError, OSError, KeyError, TypeError) as secondary:
                    row["derivation_error"] = {"type": type(secondary).__name__, "message": str(secondary)[:2000]}
            else:
                row["production_open"] = {"accepted": True}
        report["observations"].append(row)
    if Path.cwd() != initial_cwd:
        raise ValueError("packet diagnostic did not restore the trial CWD")
    if git_read(historical, "rev-parse", "HEAD").decode().strip() != api_render["historical_resource_head"]:
        raise ValueError("historical resource checkout HEAD changed during packet diagnostic")
    report["trial_cwd_restored"] = True
    report["acceptance_eligible"] = False
    return report


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("action", choices=("render", "size", "size-current-proxy", "packet-diagnostic"))
    for option in ("tree", "evidence", "name", "api-registration", "api-ledger", "label", "date"):
        result.add_argument("--" + option, required=True)
    result.add_argument("--scenario", choices=("api-partition", "target-proposal"), required=True)
    result.add_argument("--api-instruction-mode", choices=API_INSTRUCTION_MODES, default="exact-historical",
        help="exact-historical requires the recorded instruction SHA; current-target compares integrated trial API25 on fixed historical inputs")
    result.add_argument("--hypothetical-effort", choices=("minimal", "low", "medium", "high", "xhigh", "max"), required=True,
        help="explicit placeholder only; D-D remains pending")
    result.add_argument("--hypothetical-context", type=int, required=True)
    result.add_argument("--hypothetical-output", type=int, required=True)
    result.add_argument("--hypothetical-drafts", type=int, required=True)
    result.add_argument("--proxy-intermediate", help="explicit retained10-22a intermediate directory; required for size")
    result.add_argument("--api-cli-refusal-log", help="optional retained raw CLI refusal; never run a client here")
    return result


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["import-check"]:
        return import_check_main(argv[1:])
    args = parser().parse_args(argv)
    tree = Path(args.tree).resolve(strict=True)
    if Path(__file__).resolve() != tree / "scripts/adhoc/native_n1b_offline_preflight_20261023.py":
        raise ValueError("execute the committed helper from the declared trial tree")
    if args.action in ("size", "size-current-proxy", "packet-diagnostic") and not args.proxy_intermediate:
        raise ValueError("sizing/packet-diagnostic requires an explicit retained proxy intermediate directory")
    if args.action == "size-current-proxy" and args.api_instruction_mode != "current-target":
        raise ValueError("size-current-proxy requires explicit current-target instruction mode")
    destination = evidence_destination(args.evidence, args.name, tree)
    os.chdir(tree)
    before = frozen_head(tree)
    reader, files = Reader(), {}
    initial_source_roster = record_sources(tree, reader)
    report = {"scope": SCOPE, "head": before, "action": args.action, "scenario": args.scenario,
        "api_instruction_mode": args.api_instruction_mode,
        "scientific_approval": "not assessed", "native_launch_authorized": False,
        "hypothetical_model": MODEL, "hypothetical_provider": PROVIDER,
        "hypothetical_effort": args.hypothetical_effort, "D_D": "pending",
        "proposed_bounds_not_approved": candidate_bounds(args.scenario),
        "api_render_route": "selected API instruction comparison; raw CLI acceptance is a separate retained check"}
    exit_code = 0
    tools = None
    try:
        tools, report["import_environment"] = isolated_imports(tree, reader, before)
        reg, ledger, api_text, api_render = load_api(args, reader, report, files)
        current_target = args.api_instruction_mode == "current-target"
        report["current_target_api_render" if current_target else "historical_api_resource_replay"] = api_render
        report["api_render_route"] = ("current integrated trial API25 on fixed historical inputs; historical instruction equality is not required"
            if current_target else "exact historical API25 instruction replay at original resource CWD under isolated trial imports")
        report["live_cli_acceptance"] = "not established; physical-root refusal retained separately"
        selection, runtime, spec, native_text = native_case(args, reader, reg, destination)
        api_prefix = "current-target-api25" if current_target else "api25"
        files[api_prefix + "-instruction.txt"] = api_text.encode()
        files["hypothetical-native26-instruction.txt"] = native_text.encode()
        files["instructions.diff"] = "".join(difflib.unified_diff(api_text.splitlines(keepends=True),
            native_text.splitlines(keepends=True), fromfile="current-target-api25" if current_target else "captured-api25",
            tofile="hypothetical-native26")).encode()
        a, n = scientific_slice(api_text), scientific_slice(native_text)
        source_r9 = selection.raw("asset:src/download/prompts/d4d_generic_arm_prompt_v10.md").decode()
        excerpt, report["target_5048_verbatim"] = verify_r9(source_r9, native_text, api_text)
        files["target-5048-r9-verbatim.txt"] = excerpt.encode()
        files[api_prefix + "-uniform-scientific-rules.txt"], files["native26-uniform-scientific-rules.txt"] = a.encode(), n.encode()
        report["scientific_uniform_rules"] = {"identical": a == n, "api_sha256": digest(a.encode()), "native_sha256": digest(n.encode()),
            "other_diff_sections": "pending scientific/execution-procedure classification; full diff retained"}
        if a != n:
            raise ValueError("uniform scientific rules differ; do not claim aligned scientific content")
        report["instruction_bytes"] = {"api25": len(api_text.encode()), "native26_hypothetical": len(native_text.encode())}
        report["source_proxy"] = {**ledger["identity"],
            "scope": "historical API outputs used only as named proxy content; not generated by this current-target comparison",
            "historical_instruction_sha256": api_render["historical_instruction_sha256"],
            "comparison_api_instruction_sha256": api_render["instruction_sha256"],
            "outputs_generated_by_current_target_comparison": False}
        if args.api_cli_refusal_log:
            files["api-cli-refusal.txt"] = reader.read(args.api_cli_refusal_log)
        if args.action in ("size", "size-current-proxy"):
            report["size"] = size_proxy(args, reader, selection, runtime, spec, native_text, files,
                ledger=ledger, api_render=api_render)
            if report["size"]["unmeasured"]:
                exit_code = 2
        if args.action == "packet-diagnostic":
            report["packet_diagnostic"] = diagnose_packet(args, reader, api_render, ledger)
            files["packet-diagnostic.json"] = encoded(report["packet_diagnostic"])
        report["status"] = "completed_offline_measurement" if not exit_code else "partial_offline_measurement"
        if args.action == "packet-diagnostic":
            report["status"] = "completed_packet_diagnostic"
    except (ValueError, OSError, KeyError, TypeError) as exc:
        report["status"] = "refused"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)[:2000]}
        exit_code = 2
    if tools is not None:
        report["import_environment"]["loaded_project_sources"] = tools.loaded_source_proof(tree, before)
    require_source_roster(tree, initial_source_roster)
    reader.stable()
    if frozen_head(tree) != before:
        raise ValueError("source HEAD changed; evidence was not published")
    report["inputs"] = reader.manifest()
    report["outputs"] = [{"file": name, "bytes": len(raw), "sha256": digest(raw)} for name, raw in sorted(files.items())]
    files["report.json"] = encoded(report)
    publish(destination, files)
    print(destination / "report.json")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
