#!/usr/bin/env python3
# Purpose: N2d/#4354 full API25/native26 instruction parity, 2026-10-25.
# Inputs: frozen unit4 tree, pinned N1b report/CHORUS inputs and old instructions.
# Outputs: new exclusive evidence directory; hypothetical fixtures, raw renders,
# diffs, source/import/input identities and exact R9/uniform checks. No launch.
"""Render current packages offline, without changing historical registrations.

Commit this helper before running. Use an existing venv Python with -S -P -B,
PYTHONPATH=<tree>/src and PYTHONPYCACHEPREFIX=<output>/unused-import-cache.
The API renderer requires a readable registration-shaped fixture; it is written
only inside the new evidence directory, never registered through a CLI. Native
selection/runtime carriers remain in memory. No client, probe or generation is
called. Neither instruction is an observed model input or accepted campaign.

Reader, isolation and native reconstruction adapt reviewed helpers at db0573d96:
native_n1b_offline_preflight_20261023.py (sha256 1565fd34f1f62084982708e394659d99d16a692ebda622676d12fa3ff93ae6e8)
native_n1b_receipt_policy_probe_20261023.py (sha256 80a7fe9a3ef8abfe19faf656c586d162fbbe9934c540a46cbfbe6ea702823a85).
The historical replay route is intentionally not reused: current R9 assets no
longer equal the old registration. That old physical-root refusal is not waived.
"""
from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import importlib
from importlib.machinery import ModuleSpec, NamespaceLoader
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from types import ModuleType

SELF = "scripts/adhoc/native_n2_render_parity_20261025.py"
SCOPE = "hypothetical_current_package_render_not_registered"
GENERIC = "src/download/prompts/d4d_generic_arm_prompt_v10.md"
UNIFORM = ".claude/commands/d4d-uniform-rules-v2.md"
ASSET_PINS = {
    GENERIC: "95511eeea60e5112c630c28bcc342f132d14efcf0d5485bbf26f3e81a0f4cc99",
    UNIFORM: "cbf7e9f53e97a1d7dd953507308825e3c835daabcb8f6ee0a6a5dcd8bb9a048f",
}
R9_START = b"- A slot whose declared range is an enumeration is populated only from a\n"
R9_END = b"\n- `raw_data_format`"
R9_BYTES = 4433
R9_SHA = "2ae71e83e11a096764b63bc4037786d756d5e31523e3fe71701505b976eaf765"
RULE_START = b"UNIFORM DECISION RULES \xe2\x80\x94 these apply identically to every project and every arm:"
RULE_END = b"## Shared generation rules v1"
OLD_INSTRUCTIONS = {
    "current-target-api25-instruction.txt": "489a4b59f675990bf2b37921be1a234bdac9dbe05f6ea3c031ed2c5b06dfcc78",
    "hypothetical-native26-instruction.txt": "0b693a535bdccfb6d8f5f49410fc84b82c8af396cb2d82b68a3c84257f344ca4",
}
MAX_READ = 128_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2,
                      allow_nan=False).encode("utf-8") + b"\n"


def strict_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("nonfinite JSON value: " + value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=nonfinite)


class Reader:
    """Bounded physical regular-file reads, retained bytes and fresh rereads."""
    def __init__(self):
        self.files = {}

    def read(self, path, limit=MAX_READ):
        path = Path(path).absolute()
        require(path.resolve(strict=True) == path, "input must be physical: " + str(path))
        before = path.stat(follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= limit,
                "input is not a bounded regular file: " + str(path))
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        def identity(value):
            return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns
        require(len(raw) <= limit and len(raw) == before.st_size
                and identity(before) == identity(opened) == identity(after)
                == identity(path.stat(follow_symlinks=False)), "input changed during read: " + str(path))
        require(str(path) not in self.files or self.files[str(path)] == raw,
                "input changed between reads: " + str(path))
        self.files[str(path)] = raw
        return raw

    def pin(self, pin):
        raw = self.read(pin["path"])
        require(type(pin["bytes"]) is int and len(raw) == pin["bytes"]
                and sha(raw) == pin["sha256"], "input differs from pin: " + pin["path"])
        return raw

    def stable(self):
        for path in tuple(self.files):
            self.read(path)

    def manifest(self):
        return [{"path": path, "bytes": len(raw), "sha256": sha(raw)}
                for path, raw in sorted(self.files.items())]


def git(tree, *args):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0")
    return subprocess.run(["git", "--no-replace-objects", "-C", str(tree), *args],
                          env=environment, check=True, capture_output=True, timeout=30).stdout


def frozen_source(tree, head, reader):
    require(git(tree, "rev-parse", "HEAD").decode().strip() == head, "HEAD differs from expected commit")
    require(not git(tree, "diff", "--name-only", "--no-ext-diff", "--no-textconv", "HEAD"),
            "tracked tree must be committed and frozen")
    tracked = git(tree, "ls-tree", "-r", "--name-only", "-z", head, "--", "src").split(b"\0")
    expected = sorted(tree / name.decode() for name in tracked if name.endswith(b".py"))
    # pathlib includes ignored files; untracked/ignored Python cannot hide here.
    actual = sorted((tree / "src").rglob("*.py"))
    require(actual == expected, "Python source roster differs from committed tree, including ignored files")
    for path in actual:
        reader.read(path)
    for relative in (SELF, "pyproject.toml"):
        require(reader.read(tree / relative) == git(tree, "show", head + ":" + relative),
                "helper/marker differs from committed source: " + relative)
    return {"head": head, "src_git_tree": git(tree, "rev-parse", head + ":src").decode().strip(),
            "python_files": len(actual), "helper_sha256": sha(reader.files[str(tree / SELF)])}


def dependency_environment(reader):
    interpreter = Path(sys.executable)
    require(interpreter.is_absolute() and interpreter.parent.name == "bin"
            and interpreter.parent.resolve(strict=True) == interpreter.parent,
            "use an absolute existing venv/bin Python interpreter")
    config = interpreter.parent.parent / "pyvenv.cfg"
    raw = reader.read(config, 64_000)
    versions = re.findall(r"^(?:version_info|version)\s*=\s*(\d+)\.(\d+)(?:\.|\s|$)",
                          raw.decode(), flags=re.MULTILINE)
    require(versions and len(set(versions)) == 1, "venv config lacks one consistent Python version")
    version = ".".join(versions[0])
    require(version == f"{sys.version_info.major}.{sys.version_info.minor}", "venv/interpreter versions differ")
    site = interpreter.parent.parent / "lib" / ("python" + version) / "site-packages"
    require(site.resolve(strict=True) == site and site.is_dir(), "dependency directory must be physical")
    return {"python": str(interpreter), "config": str(config), "config_sha256": sha(raw),
            "site_packages": str(site), "python_version": sys.version,
            "scope": "Existing dependencies; site/.pth execution disabled; dependency package bytes not attested."}


def module_origins(tree, head, reader, *, modules=None):
    result = {}
    for name, module in sorted(tuple((sys.modules if modules is None else modules).items())):
        if name != "data_sheets_schema" and not name.startswith("data_sheets_schema."):
            continue
        spec = getattr(module, "__spec__", None)
        require(type(module) is ModuleType and type(spec) is ModuleSpec and spec.name == name,
                "project module has inconsistent identity: " + name)
        filename = getattr(module, "__file__", None)
        if filename is None:
            expected = tree / "src" / Path(*name.split("."))
            locations = spec.submodule_search_locations
            require(spec.origin is None and not spec.has_location and spec.cached is None
                    and type(spec.loader) is NamespaceLoader and module.__loader__ is spec.loader
                    and locations is not None and getattr(module, "__path__", None) is locations
                    and getattr(spec.loader, "_path", None) is locations
                    and list(locations) == [str(expected)] and expected.resolve(strict=True) == expected,
                    "project namespace has a foreign or inconsistent search root: " + name)
            relative = expected.relative_to(tree).as_posix()
            require(git(tree, "cat-file", "-t", head + ":" + relative) == b"tree\n",
                    "project namespace is not a committed source directory")
            result[name] = {"kind": "namespace", "path": str(expected),
                            "git_tree": git(tree, "rev-parse", head + ":" + relative).decode().strip()}
        else:
            path = Path(filename)
            require(path.is_absolute() and path.resolve(strict=True) == path
                    and path.is_relative_to(tree / "src") and path.suffix == ".py"
                    and spec.origin == str(path), "project module loaded from foreign source: " + name)
            relative = path.relative_to(tree).as_posix()
            raw = reader.read(path)
            require(raw == git(tree, "show", head + ":" + relative),
                    "loaded project source differs from committed blob: " + relative)
            result[name] = {"kind": "source", "path": str(path), "sha256": sha(raw)}
    return result


def offline_audit(event, args):
    if event.startswith("socket.") and event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo"}:
        raise RuntimeError("network forbidden in offline render")
    if event == "subprocess.Popen":
        argv = args[1]
        require(isinstance(argv, (list, tuple)) and argv and Path(str(argv[0])).name == "git",
                "only read-only Git subprocesses are permitted")
        words = list(map(str, argv[1:]))
        while words and words[0].startswith("-"):
            option = words.pop(0)
            if option in {"-C", "-c", "--git-dir", "--work-tree"}:
                require(bool(words), "incomplete Git option")
                words.pop(0)
        require(words and words[0] in {"rev-parse", "diff", "show", "cat-file", "ls-tree", "ls-files", "status"},
                "Git mutation/network operation forbidden in offline render")


def isolated_imports(tree, head, target, reader):
    require(os.environ.get("PYTHONPATH") == str(tree / "src"), "PYTHONPATH must name only the selected tree/src")
    require(sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode,
            "run Python with -S -P -B")
    cache = target / "unused-import-cache"
    require(sys.pycache_prefix == str(cache) and not os.path.lexists(cache),
            "set PYTHONPYCACHEPREFIX to the fresh output/unused-import-cache")
    require(not any(name == "data_sheets_schema" or name.startswith("data_sheets_schema.")
                    for name in sys.modules), "project code imported before isolation")
    require(not any(os.environ.get(name) for name in ("ANTHROPIC_API_KEY", "CBORG_API_KEY", "OPENAI_API_KEY")),
            "credential variables must be absent for the offline helper")
    environment = dependency_environment(reader)
    require(environment["site_packages"] not in sys.path, "dependency site was already active")
    sys.path.append(environment["site_packages"])
    sys.addaudithook(offline_audit)
    importlib.import_module("data_sheets_schema")
    from data_sheets_schema.resources import resource_root
    require(resource_root() == (tree, "checkout"), "resources resolved outside the selected checkout")
    return {"environment": environment, "flags": {"no_site": True, "safe_path": True,
            "dont_write_bytecode": True}, "pycache_prefix": str(cache),
            "before": module_origins(tree, head, reader)}


def between(raw, start, end, name, *, strip=False):
    require(raw.count(start) == 1 and raw.count(end) == 1, name + " markers missing or ambiguous")
    first, last = raw.index(start), raw.index(end)
    require(first < last, name + " markers are reversed")
    value = raw[first:last]
    return value.strip() if strip else value


def compare_rules(generic, api, native):
    require(sha(generic) == ASSET_PINS[GENERIC], "generic asset is not the reviewed R9 source")
    r9 = between(generic, R9_START, R9_END, "R9")
    require(len(r9) == R9_BYTES and sha(r9) == R9_SHA, "complete reviewed R9 differs")
    occurrences = {"api25": api.count(r9), "native26": native.count(r9)}
    require(occurrences == {"api25": 1, "native26": 1}, "complete R9 must occur verbatim exactly once in each instruction")
    api_rules = between(api, RULE_START, RULE_END, "API uniform rules", strip=True)
    native_rules = between(native, RULE_START, RULE_END, "native uniform rules", strip=True)
    require(api_rules == native_rules, "complete extracted uniform sections differ")
    return {"r9": {"bytes": len(r9), "sha256": sha(r9), "occurrences": occurrences},
            "uniform": {"bytes": len(api_rules), "sha256": sha(api_rules), "identical": True,
                        "extraction": "Unique start/end markers; trim surrounding whitespace only."}}, r9, api_rules


def unique_pin(rows, path):
    found = [row for row in rows if row.get("path") == str(path)]
    require(len(found) == 1, "historical report lacks one exact input pin: " + str(path))
    return found[0]


def historical_inputs(args, reader):
    report_raw = reader.read(args.historical_report)
    require(sha(report_raw) == args.historical_report_sha256, "historical report SHA differs")
    report = strict_json(report_raw)
    require(report.get("scope") == "hypothetical_offline_not_registered"
            and report.get("api_instruction_mode") == "current-target"
            and report.get("status") == "completed_offline_measurement", "wrong historical render report")
    old_raw = reader.pin(unique_pin(report["inputs"], Path(args.historical_registration)))
    ledger_raw = reader.pin(unique_pin(report["inputs"], Path(args.historical_ledger)))
    old, ledger = strict_json(old_raw), strict_json(ledger_raw)
    require(old["registration_path"] == args.historical_registration
            and old["format"] == "shared_generation_registration_v1"
            and old["run"]["project"] == "CHORUS" and old["selection"]["renderer"] == 25
            and old["selection"]["condition"] == "generic_v10", "historical CHORUS selection differs")
    identity = ledger["input_identity"]["shared_generation"]
    require(identity["registration"] == {"raw_json": old_raw.decode(), "sha256": sha(old_raw)},
            "historical ledger/registration join differs")
    require(ledger["identity"] == {key: old["run"][key] for key in ("project", "method", "label")}
            | {"condition": "generic_v10"}, "historical ledger run differs")
    for pin in identity["files"]:
        reader.pin(pin)
    snapshots = {}
    for role in ("bundle", "chunk_manifest", "context", "source_manifest"):
        require(old["inputs"][role] is not None, "historical CHORUS role is absent: " + role)
        snapshots[role] = reader.pin(old["inputs"][role])
    instructions = {}
    for name, expected in OLD_INSTRUCTIONS.items():
        rows = [row for row in report["outputs"] if row["file"] == name]
        require(len(rows) == 1 and rows[0]["sha256"] == expected, "historical instruction report differs: " + name)
        raw = reader.read(Path(args.historical_report).parent / name)
        require(len(raw) == rows[0]["bytes"] and sha(raw) == expected, "historical instruction changed: " + name)
        instructions[name] = raw
    return old, snapshots, instructions, {"report_sha256": sha(report_raw),
        "registration_sha256": sha(old_raw), "ledger_sha256": sha(ledger_raw), "run": old["run"],
        "scope": "Old run/input identity only; not admitted against current scientific assets."}


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def api_fixture(tree, target, old, reader, label, date):
    from data_sheets_schema import api_runner as api, shared_generation as sg
    from data_sheets_schema import receipt_completion as rc
    from data_sheets_schema.profiles import profile_named
    from data_sheets_schema.resources import resource_path
    from data_sheets_schema.schema_snapshot import capture_schema
    reg = copy.deepcopy(old)
    reg.update(registration_id="OFFLINE-NOT-REGISTERED-api25-render",
               registration_path=str(target / "api-registration-fixture.json"), selection=sg.descriptor())
    reg["run"]["label"] = label + "-api"
    reg["run"]["method"] = "claudecode_api"
    for name, expected in sg.ASSET_HASHES.items():
        require(sha(reader.read(tree / name)) == expected, "installed API asset differs: " + name)
    schemas = {}
    for kind, path in (("full", api.FULL_SCHEMA_PATH), ("core", api.CORE_SCHEMA_PATH)):
        snapshot = capture_schema(resource_path(path).absolute(), strict=True, read_bytes=reader.read)
        reg["inputs"][kind + "_schema"] = sg.schema_pin(snapshot)
        schemas[kind] = snapshot
    vocab = profile_named(reg["inputs"]["profile"]["name"]).pin_path
    reg["inputs"]["profile"]["vocabulary"] = (
        sg.file_pin(vocab.absolute(), reader.read(vocab.absolute())) if vocab is not None else None)
    settings = api._model_settings("generic_v10")
    config = settings.get("config_path")
    config_path = resource_path(config).absolute() if config else None
    reg["runtime"] = {"provider": "HYPOTHETICAL_PROVIDER_NOT_AUTHENTICATED",
        "base_url": "https://example.invalid", "model": settings["name"],
        "temperature": settings["temperature"] if api.accepts_temperature(settings["name"]) else None,
        "thinking": settings.get("thinking"), "effort": settings.get("effort"),
        "config": sg.file_pin(config_path, reader.read(config_path)) if config_path else None}
    reg["receipt"].update(registration_id="OFFLINE-NOT-REGISTERED-receipt",
        runtime_policy_sha256=rc.policy_identity(version=2)["sha256"],
        coverage_floor={"state": "pending", "mode": "diagnostic_pilot"})
    raw = sg.canonical(reg)
    sg.parse_registration(raw)
    # Actual API construction/capture validates this isolated synthetic file.
    # Neither a registration command nor runtime admission is invoked.
    write_new(Path(reg["registration_path"]), raw)
    reader.read(reg["registration_path"])
    spec = api.RunSpec(**reg["run"], bundle=Path(reg["inputs"]["bundle"]["path"]),
        manifest=Path(reg["inputs"]["source_manifest"]["path"]),
        chunk_manifest=Path(reg["inputs"]["chunk_manifest"]["path"]),
        out_dir=target / "hypothetical-unwritten" / "api", condition="generic_v10", render_version=25,
        runtime=api.RUNTIME, provider=reg["runtime"]["provider"], run_date=date,
        profile=reg["inputs"]["profile"]["name"], profile_basis=reg["inputs"]["profile"]["basis"],
        shared_generation_version=1, shared_generation_registration=raw.decode(), api_playbook_version=2,
        receipt_completion_version=2, receipt_completion_registration=sg.canonical(reg["receipt"]).decode())
    spec.bind_api_header_values(settings)
    text = api.resolve_prompt(spec).encode()
    require(not (target / "hypothetical-unwritten").exists(), "render unexpectedly created output paths")
    return reg, schemas, text, spec.render_spec()


def native_fixture(tree, target, reg, schemas, reader, label, date):
    from data_sheets_schema import api_runner as api, agentic_runtime
    from data_sheets_schema import native_shared_contract as c, native_shared_selection as selected
    from data_sheets_schema import native_shared_render as render
    from data_sheets_schema.native_execution_registration import ROUTE
    def artifact(role, path, raw):
        return c.CapturedArtifact(c.ArtifactPin(role, str(path), len(raw), c.sha(raw)), raw)
    def pin(item):
        return {key: getattr(item.pin, key) for key in ("path", "bytes", "sha256")}
    root = target / "hypothetical-unwritten" / "native"
    assets = selected.capture_assets()
    authority = list(assets)
    for item in assets:
        require(reader.read(item.pin.path) == item.raw, "native captured asset changed")
    inputs = {"project": "CHORUS", "profile": copy.deepcopy(reg["inputs"]["profile"])}
    for role in ("bundle", "chunk_manifest", "context", "source_manifest"):
        declared = reg["inputs"][role]
        item = artifact(role, declared["path"], reader.pin(declared))
        authority.append(item)
        inputs[role] = pin(item)
    vocab = inputs["profile"]["vocabulary"]
    if vocab is not None:
        authority.append(artifact("vocabulary", vocab["path"], reader.pin(vocab)))
    schema_items = {}
    for kind, cls in (("full", "Dataset"), ("core", "CoreDataset")):
        rows = []
        for index, (name, path, raw) in enumerate(schemas[kind].sources):
            item = artifact(f"{kind}_schema:{index}", path, raw)
            schema_items[item.pin.role] = item
            rows.append({"name": str(name), **pin(item)})
        inputs[kind + "_schema"] = {"root": str(schemas[kind].sources[0][1]), "root_class": cls, "sources": rows}
    policy = artifact("receipt_policy", root / "receipt-policy.json", c.canonical({
        "kind": c.KINDS["receipt_policy"], "version": 1, "registration_id": "OFFLINE-pending-floor",
        "condition": c.CONDITION, "runtime_policy_sha256": selected.RECEIPT_POLICY_SHA256,
        "receipt_instrument_version": 4, "coverage_floor": {"state": "pending", "mode": "diagnostic_pilot"}}))
    bounds = {"max_authority_bytes": 64_000_000, "max_evidence_bytes": 512_000_000,
        "max_history_bytes": 64_000_000, "max_history_records": 16384, "max_input_bytes": 8_000_000,
        "max_inventory_bytes": 12288, "max_paths_per_worker": 80, "max_populated_paths": 100000,
        "max_request_bytes": 32_000_000, "max_response_bytes": 8_000_000, "max_submissions": 7, "max_workers": 4}
    axes = {key: value for key, value in selected.descriptor().items()
            if key not in {"typed_protocol", "projection", "receipt_policy", "assets"}}
    run = {"project": "CHORUS", "arm": reg["run"]["arm"], "method": "claudecode_direct", "label": label + "-native"}
    doc = {"kind": c.KINDS["selection"], "version": 1, "registration_id": "OFFLINE-NOT-REGISTERED-native26-render",
        "registration_path": str(root / "selection.json"), "stage_root": str(root / "stages"), "run": run,
        "selection": {**axes, "descriptor_sha256": selected.descriptor_capture().sha256,
                      "assets": {a.pin.role[len("asset:"):]: pin(a) for a in assets}},
        "inputs": inputs, "receipt_policy": pin(policy), "bounds": c.parse_bounds(bounds)}
    selection = selected.rebuild(artifact("selection", doc["registration_path"], c.canonical(doc)),
        tuple(authority), selected._declared_schemas(doc, schema_items), policy)
    runtime_doc = {"route": ROUTE, "executable": {"status": "not_selected_or_executed"},
        "model": "HYPOTHETICAL_MODEL_NOT_SELECTED", "auxiliary_models": [], "effort": "high",
        "limits": {"contextWindow": 1_000_000, "maxOutputTokens": 32_000},
        "limits_basis": "Offline render fixture only; not a selected or observed capacity",
        "provider": "HYPOTHETICAL_PROVIDER_NOT_AUTHENTICATED", "auth": {"status": "not_observed"},
        "environment": {}, "deadline_seconds": None, "budget_guard_usd": None,
        "keep_awake": {"status": "not_observed"}}
    runtime = artifact("runtime_declaration", root / "runtime.json", c.canonical(runtime_doc))
    toolchain = agentic_runtime.toolchain()
    for path in toolchain["resources"].values():
        reader.read(path)
    paths = {"full": str(root / "CHORUS_d4d.yaml"), "core": str(root / "CHORUS_d4d_core.yaml"),
        "receipt": str(root / "CHORUS_coverage_receipt.yaml"), "report": str(root / "CHORUS_reconciliation.md")}
    recorded = {"native_shared_generation_version": 1, "native_shared_generation_descriptor": selected.descriptor(),
        "native_shared_generation_registration": {"sha256": selection.registration.pin.sha256,
            "raw_json": selection.registration.raw.decode()},
        "native_shared_generation_context": selection.generation_context(),
        "native_shared_receipt_policy": render._raw_identity(policy),
        "native_shared_runtime_declaration": render._raw_identity(runtime), "native_shared_max_draft_checks": 2,
        "condition": c.CONDITION, "render_version": 26, "arm": run["arm"],
        "bundle": inputs["bundle"]["path"], "manifest": inputs["source_manifest"]["path"],
        "chunk_manifest": inputs["chunk_manifest"]["path"],
        "manifest_line": "# Source manifest: " + inputs["source_manifest"]["path"],
        "profile": inputs["profile"]["name"], "profile_basis": inputs["profile"]["basis"],
        "runtime": c.RUNTIME, "provider": runtime_doc["provider"], "reasoning_effort": "high",
        "run_date": date, "prompt_text_env": True, "chunk_check_uses_manifest": True,
        "agentic_artifact_paths": paths, "agentic_toolchain": toolchain}
    spec = api.RunSpec.from_render_spec(recorded, project="CHORUS", method=run["method"], label=run["label"])
    text = render.instruction(spec).encode()
    require(not (target / "hypothetical-unwritten").exists(), "render unexpectedly created native output paths")
    return text, recorded


def diff(left, right, before, after):
    return "".join(difflib.unified_diff(left.decode().splitlines(keepends=True),
        right.decode().splitlines(keepends=True), fromfile=before, tofile=after)).encode()


def destination(parent, name, tree):
    parent = Path(parent)
    require(parent.is_absolute() and parent.resolve(strict=True) == parent and parent.is_dir(),
            "evidence parent must be an existing physical directory")
    require(parent != tree and not parent.is_relative_to(tree) and "data" not in parent.parts,
            "evidence must be outside the source/data tree")
    require(name and Path(name).name == name and name not in {".", ".."}, "output name must be one component")
    target = parent / name
    require(not os.path.lexists(target), "refuse existing evidence output")
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("tree", "expect-head", "evidence", "name", "historical-report", "historical-report-sha256",
                 "historical-registration", "historical-ledger", "label", "date"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    tree = Path(args.tree)
    require(tree.is_absolute() and tree.resolve(strict=True) == tree and Path(__file__).resolve() == tree / SELF,
            "execute this committed helper from its physical declared worktree")
    require(re.fullmatch("[0-9a-f]{40}", args.expect_head), "expected head must be a full SHA")
    require(re.fullmatch("[0-9a-f]{64}", args.historical_report_sha256), "historical report needs an explicit SHA256")
    require(re.fullmatch(r"[A-Za-z0-9_-]+", args.label), "label must be an explicit safe fixture component")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date), "date must be explicit YYYY-MM-DD")
    target = destination(args.evidence, args.name, tree)
    os.chdir(tree)
    reader = Reader()
    source = frozen_source(tree, args.expect_head, reader)
    report = {"scope": SCOPE, "acceptance_eligible": False, "launch_authorized": False,
        "scientific_acceptance": "not_assessed", "source": source, "argv": vars(args),
        "fixture_declarations_not_selected_caps": True, "status": "started"}
    target.mkdir(mode=0o700)
    files = {}
    exit_code = 2
    try:
        report["isolation"] = isolated_imports(tree, args.expect_head, target, reader)
        old, snapshots, old_instructions, report["historical"] = historical_inputs(args, reader)
        for role, raw in snapshots.items():
            files["historical-input-" + role + ".txt"] = raw
        for name, raw in old_instructions.items():
            files["historical-" + name] = raw
        for name, expected in ASSET_PINS.items():
            require(sha(reader.read(tree / name)) == expected, "current reviewed asset differs: " + name)
        reg, schemas, api, api_spec = api_fixture(tree, target, old, reader, args.label, args.date)
        native, native_spec = native_fixture(tree, target, reg, schemas, reader, args.label, args.date)
        files.update({"current-api25-instruction.txt": api, "current-native26-instruction.txt": native,
            "api-render-spec.json": encoded(api_spec), "native-render-spec.json": encoded(native_spec),
            "instructions.diff": diff(api, native, "current-api25", "hypothetical-current-native26"),
            "historical-to-current-api.diff": diff(old_instructions["current-target-api25-instruction.txt"], api,
                "N1b-api25", "current-api25"),
            "historical-to-current-native.diff": diff(old_instructions["hypothetical-native26-instruction.txt"], native,
                "N1b-native26", "hypothetical-current-native26")})
        report["parity"], r9, rules = compare_rules(reader.read(tree / GENERIC), api, native)
        files.update({"reviewed-r9.txt": r9, "api-uniform-rules.txt": rules, "native-uniform-rules.txt": rules})
        report["fixture"] = {"api_registration": reg, "native_selection_written": False,
            "native_runtime_written": False, "original_registration_changed": False,
            "source_inputs": reg["inputs"], "schema_source": "current unit4 checkout",
            "vocabulary_source": "current selected profile's physical unit4 path",
            "historical_physical_root_refusal": "Retained historical evidence; not retried, changed or waived.",
            "bounds_scope": "Inherited historical API allowances and explicit native render placeholders, not approved future limits."}
        report["new_hunks"] = [line for line in files["instructions.diff"].decode().splitlines() if line.startswith("@@ ")]
        report["classification"] = "Pending independent review of every new hunk and both historical deltas; seven hunks not assumed."
        report["status"] = "completed_offline_render_parity"
        exit_code = 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        report["status"] = "refused"
        report["error"] = {"type": type(error).__name__, "message": str(error)[:3000]}
    try:
        report["loaded_project_sources"] = module_origins(tree, args.expect_head, reader)
        require(frozen_source(tree, args.expect_head, reader) == source, "source identity changed")
        reader.stable()
        require(not os.path.lexists(target / "unused-import-cache"), "unexpected import cache created")
        require(not os.path.lexists(target / "hypothetical-unwritten"), "unexpected output/attempt state created")
        report["source_and_inputs_unchanged"] = True
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        report.update(status="refused", source_and_inputs_unchanged=False,
                      final_verification_error={"type": type(error).__name__, "message": str(error)[:3000]})
        exit_code = 2
    report["inputs"] = reader.manifest()
    for name, raw in files.items():
        write_new(target / name, raw)
    report["outputs"] = [{"file": path.name, "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
                         for path in sorted(target.iterdir()) if path.is_file()]
    write_new(target / "report.json", encoded(report))
    print(target / "report.json")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
