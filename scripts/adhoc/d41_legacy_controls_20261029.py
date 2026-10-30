#!/usr/bin/env python3
"""#5212 evidence only, 2026-10-29: capture pre-D41 tests and replay exact bytes.

Inputs: local f8c5ac73c checkout, #5212 checkout, existing Python dependencies.
Outputs: immutable before/after directories, SHA-256 manifests, traces and pytest
reports under an explicit scratch root. No production edits or provider calls.
Run with the dependency environment's python -S -P -B. No site/.pth execution.
Use --mode plan first; generate/replay one case before a serial batch. Recovery
faults are those in the ORIGINAL pre-D41 tests, not deleted current journals.
The adjacent _v1.py retains the exact initially executed driver. This revision
preopens its report stream so filesystem-prohibition tests cannot break it.
"""
from __future__ import annotations

import argparse
from collections import Counter
import dataclasses
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import traceback

PRE = "f8c5ac73caba610d40c49aaceddb31ead3590a72"
BASE = "d9b69d84d9a6936809681ae240bb8e767649ca11"
CASES = {
    "c1": ("tests/test_fresh_orphan_partial_generation.py::test_fresh_restart_does_not_accept_unrelated_archived_attempts", [2]),
    "c2": ("tests/test_fresh_orphan_partial_generation.py::test_fresh_restart_records_an_orphaned_partial_predecessor[malformed]", [2]),
    "c3": ("tests/test_fresh_orphan_partial_generation.py::test_fresh_restart_records_an_orphaned_partial_predecessor[missing]", [2]),
    "c4": ("tests/test_fresh_orphan_partial_generation.py::test_predecessor_binding_survives_interrupted_index_activation", [2, 3]),
    "c5": ("tests/test_generation_manifest_identity.py::test_legacy_progress_without_input_evidence_requires_explicit_restart", [1]),
    "c6": ("tests/test_generation_recovery_review.py::test_explicit_restart_preserves_an_unreadable_snapshot_index", [1, 2]),
    "c7": ("tests/test_midnight_resume.py::test_automatic_date_is_restored_before_cached_instruction_or_portable_checks[True-False]", [2]),
    "c8": ("tests/test_reasoning_generation_restart.py::test_fresh_generation_archives_malformed_predecessor_reasoning[True]", [2]),
}
SUITES = ["tests/test_latch_journal.py", "tests/test_api_latch_guard.py",
          "tests/test_pr5212_d55_fixes.py", "tests/test_d42_claude_d55.py",
          "tests/test_pr5212_r3_fixes.py", "tests/test_pr5212_r4_fixes.py",
          "tests/test_d41_request_parity.py"]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, default=str)
        stream.write("\n")


def inventory(root):
    """Direct walk includes ignored/hidden bytes; forbid symlinks in fixtures."""
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"fixture symlink: {path}")
        if path.is_file():
            raw = path.read_bytes()
            result[str(path.relative_to(root))] = {"bytes": len(raw), "sha256": sha(raw)}
    return result


def capture(source, dest):
    before = inventory(source)
    shutil.copytree(source, dest)
    assert inventory(source) == inventory(dest) == before
    return before


def git(tree, *args):
    return subprocess.check_output(["git", "--no-replace-objects", "-C", str(tree), *args], text=True).strip()


def offline(event, args):
    if event in {"socket.connect", "socket.sendto", "socket.bind"}:
        if getattr(args[0], "family", None) == socket.AF_UNIX:
            return
        address = args[-1]
        if not (isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1", "localhost"}):
            raise RuntimeError(f"offline control refuses {event}")
    if event in {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"}:
        if args[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise RuntimeError(f"offline control refuses {event}")
    if event == "subprocess.Popen":
        name = Path(os.fsdecode(args[0])).name
        if name in {"gh", "curl", "wget", "ssh", "claude", "codex", "gemini"}:
            resolved = Path(shutil.which(os.fsdecode(args[0]), path=(args[3] or os.environ).get("PATH")) or os.fsdecode(args[0])).resolve()
            if not resolved.is_relative_to(_SCRATCH):
                raise RuntimeError(f"offline control refuses executable {name}")


def bootstrap(tree, scratch):
    global _SCRATCH
    _SCRATCH = scratch
    assert sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode
    removed = []
    for key in list(os.environ):
        if (any(part in key.upper() for part in ("API_KEY", "API_TOKEN", "AUTH_TOKEN", "ACCESS_TOKEN"))
                or key.upper().endswith("_PROXY")
                or key.startswith(("ANTHROPIC_", "OPENAI_", "CBORG_", "AZURE_", "AWS_", "GEMINI_", "GOOGLE_API_", "D4D_", "PYTEST_"))):
            removed.append(key)
            del os.environ[key]
    os.environ.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                      PYTHONPYCACHEPREFIX=str(scratch / "pycache"), GIT_NO_LAZY_FETCH="1",
                      GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
                      GIT_OPTIONAL_LOCKS="0", TOKENIZERS_PARALLELISM="false")
    (scratch / "temporary").mkdir(exist_ok=True)
    os.environ.update(TMPDIR=str(scratch / "temporary"), PIP_NO_INDEX="1", UV_OFFLINE="1",
                      PIP_DISABLE_PIP_VERSION_CHECK="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                      MPLCONFIGDIR=str(scratch / "matplotlib"))
    venv = Path(sys.executable).parent.parent
    site = venv / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    assert site.is_dir()
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path.append(str(site))
    sys.path[:0] = [str(tree / "src"), str(tree), str(tree / "scripts")]
    os.environ["PYTHONPATH"] = os.pathsep.join(sys.path[:3])
    os.chdir(tree)
    sys.addaudithook(offline)
    return {"python": sys.version, "executable": sys.executable, "site": str(site),
            "helper_sha256": sha(Path(__file__).read_bytes()),
            "removed_environment_names": sorted(removed), "site_and_pth_execution": False,
            "dependencies": {p: importlib.metadata.version(p) for p in
                             ("pytest", "linkml", "linkml-runtime", "anthropic", "PyYAML")},
            "poetry_lock_sha256": sha((tree / "poetry.lock").read_bytes())}


def origins(tree):
    found = {}
    for name, module in list(sys.modules.items()):
        if name != "data_sheets_schema" and not name.startswith(("data_sheets_schema.", "tests.")):
            continue
        for raw in getattr(module, "__path__", []):
            assert Path(raw).resolve().is_relative_to(tree)
        if getattr(module, "__file__", None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(tree), (name, path)
            found[name] = {"path": str(path), "sha256": sha(path.read_bytes())}
    return found


def encode(value):
    if isinstance(value, Path):
        return {"__path__": str(value)}
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    assert value is None or isinstance(value, (str, int, float, bool)), type(value)
    return value


def decode(value):
    if isinstance(value, dict):
        if set(value) == {"__path__"}:
            return Path(value["__path__"])
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def saved_spec(spec):
    return {"kwargs": {f.name: encode(getattr(spec, f.name)) for f in dataclasses.fields(spec) if f.init},
            "automatic_run_date": spec._automatic_run_date,
            "instruction_cached": "instruction" in spec.__dict__,
            "dict_keys": sorted(spec.__dict__)}


def outcome(call, spec, client):
    start = len(client.messages.calls)
    try:
        result = call()
    except BaseException as exc:
        row = {"status": "raised", "type": type(exc).__name__, "message": str(exc),
               "traceback": traceback.format_exc()}
    else:
        row = {"status": "returned", "already_complete": result.get("already_complete", False),
               "usage_rows": len(result.get("usage", [])), "validation_problems": result.get("validation_problems"),
               "skipped": result.get("skipped")}
    row.update(fake_dispatches=len(client.messages.calls) - start, run_date=spec.run_date)
    return row


def generate(args, env):
    assert git(args.tree, "rev-parse", "HEAD") == PRE
    # Ignore-independent physical search as well as the immutable Git tree.
    assert not list((args.tree / "src").rglob("*latch_journal*"))
    import pytest
    from data_sheets_schema import api_runner as api
    case_name = args.case + ("-derived" if args.derived else "")
    case_dir = args.evidence / "captures" / case_name
    case_dir.mkdir(parents=True)
    (args.scratch / "pytest").mkdir(exist_ok=True)
    rows = []
    original = api.execute

    def observed(spec, **kwargs):
        number = len(rows) + 1
        folder = case_dir / f"call-{number}"
        folder.mkdir()
        root = spec.out_dir.parent.resolve()
        row = {"call": number, "root": str(root), "resume": kwargs.get("resume", True),
               "spec": saved_spec(spec), "before": capture(root, folder / "before")}
        rows.append(row)
        save(folder / "invocation.json", {k: v for k, v in row.items() if k != "before"})
        save(folder / "before-manifest.json", row["before"])
        client = kwargs["client"]
        count = len(client.messages.calls)
        try:
            result = original(spec, **kwargs)
        except BaseException as exc:
            row["outcome"] = {"status": "raised", "type": type(exc).__name__, "message": str(exc),
                              "traceback": traceback.format_exc()}
            raise
        else:
            row["outcome"] = {"status": "returned", "already_complete": result.get("already_complete", False),
                              "usage_rows": len(result.get("usage", [])),
                              "validation_problems": result.get("validation_problems")}
            return result
        finally:
            row["outcome"].update(fake_dispatches=len(client.messages.calls) - count, run_date=spec.run_date)
            row["after"] = capture(root, folder / "after")
            save(folder / "after-manifest.json", row["after"])
            save(folder / "outcome.json", row["outcome"])

    api.execute = observed
    node, targets = CASES[args.case]
    if args.derived:
        assert args.case in {"c5", "c6"}
        from tests.test_generation_manifest_identity import external, offline as fixture_offline
        from tests.test_download.test_api_runner import FakeClient
        from data_sheets_schema import usage_ledger, snapshot_store
        root = args.scratch / "pytest" / case_name / "fixture"
        root.mkdir(parents=True)
        with pytest.MonkeyPatch.context() as patch:
            fixture_offline.__wrapped__(patch)
            spec = external.__wrapped__(root)
            first = FakeClient()
            first.messages.fail_on = "audit"
            with pytest.raises(RuntimeError, match="boom"):
                api.execute(spec, client=first)
            if args.case == "c5":
                progress_path = api._progress_path(spec)
                progress = json.loads(progress_path.read_bytes())
                # Original generated bytes already retained in call-1/after.
                usage_ledger.ledger_path(spec).unlink()
                progress_path.write_text(json.dumps({"label": progress["label"], "completed": progress["completed"]}))
                diagnostic = "no recorded generation input identity"
            else:
                index = snapshot_store.index_path(spec.metadata_dir, spec.project)
                raw = index.read_bytes()
                # Model a transferred, interrupted index: retain the entire
                # emitting run separately and expose only a prefix of its index.
                spec.out_dir.rename(case_dir / "emitting-run")
                index.parent.mkdir(parents=True)
                index.write_bytes(raw[:100])
                diagnostic = "cannot recover generation snapshots"
            refused = FakeClient()
            with pytest.raises(usage_ledger.UsageLedgerError, match=diagnostic):
                api.execute(spec, client=refused)
            assert not refused.messages.calls
            fresh = FakeClient()
            result = api.execute(spec, resume=False, client=fresh)
            assert len(fresh.messages.calls) == len(result["usage"]) == 4
            if args.case == "c6":
                assert any(p.read_bytes() == raw[:100] for p in index.parent.glob(f"{index.stem}.previous-*.json"))
        code, targets = 0, [2, 3]
    else:
        code = pytest.main([node, "-q", "-p", "no:cacheprovider",
                            "--basetemp", str(args.scratch / "pytest" / case_name),
                            "--junitxml", str(case_dir / "pytest.xml")])
    save(case_dir / "generation.json", {"head": PRE, "nodeid": node, "targets": targets,
         "derived_from_emitted_artifacts": args.derived, "pytest_exit": int(code), "calls": len(rows),
         "environment": env, "origins": origins(args.tree)})
    assert code == 0, "pre-D41 original test did not pass"
    assert all((case_dir / f"call-{n}" / "outcome.json").is_file() for n in targets)


def replay(args, env):
    assert git(args.tree, "rev-parse", "HEAD") == BASE
    from data_sheets_schema import api_runner as api, snapshot_store
    from tests.test_download.test_api_runner import FakeClient
    import pytest
    api.MAX_ATTEMPTS = 1
    case_name = args.case + ("-derived" if args.derived else "")
    source = args.evidence / "captures" / case_name / f"call-{args.call}"
    info = json.loads((source / "invocation.json").read_bytes())
    expected = json.loads((source / "before-manifest.json").read_bytes())
    destination = Path(info["root"])
    assert destination.is_relative_to(args.scratch / "pytest")
    suffix = "-fresh" if args.fresh else ""
    report = args.evidence / "replays" / case_name / f"call-{args.call}{suffix}"
    report.mkdir(parents=True)
    # Preserve the preceding execution in full. Restore into a new directory at
    # the SAME pathname: immutable artifacts contain absolute path identities.
    if destination.exists():
        destination.rename(report / "displaced")
    assert capture(source / "before", destination) == expected
    assert not any("latch_journal" in name for name in expected)
    data = info["spec"]
    spec = api.RunSpec(**decode(data["kwargs"]))
    spec._automatic_run_date = data["automatic_run_date"]
    if data["instruction_cached"]:
        spec.instruction
    client = FakeClient()
    with pytest.MonkeyPatch.context() as patch:
        if args.case == "c4" and args.call == 2:
            def interrupted(*a, **kw):
                raise OSError("injected index publication failure")
            patch.setattr(snapshot_store, "_write", interrupted)
        before = inventory(destination)
        assert before == expected
        row = outcome(lambda: api.execute(spec, resume=False if args.fresh else info["resume"], client=client), spec, client)
        after = capture(destination, report / "after")
    changed = {k: {"before": before.get(k), "after": after.get(k)} for k in sorted(set(before) | set(after)) if before.get(k) != after.get(k)}
    save(report / "result.json", {"head": BASE, "source_head": PRE, "nodeid": CASES[args.case][0],
          "call": args.call, "explicit_restart_supplement": args.fresh, "exact_transplant_verified": True,
          "source": str(source), "destination": str(destination), "before": before, "after": after,
          "changes": changed, "outcome": row, "environment": env, "origins": origins(args.tree)})
    print(json.dumps({"case": args.case, "call": args.call, "fresh": args.fresh, "outcome": row,
                      "changed_files": len(changed)}, indent=2))


def checks(args, env):
    # CI uses installed pytest entry points. Keep them for broad checks while
    # retaining no-site/.pth isolation; all top-level execution remains serial.
    os.environ.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
    import pytest
    report = args.evidence / args.mode
    report.mkdir(parents=True)
    temporary = args.scratch / args.mode
    temporary.mkdir()
    selected = ([] if args.mode == "collect" else ["tests"] if args.mode in {"ci", "collect-tests"}
                else ["tests/test_audit_batch_context.py::test_worker_recovery_ranges_do_not_access_filesystem_and_keep_exact_locator"]
                if args.mode == "ci-observer-canary"
                else ["tests/test_ci_sharding.py::test_one_long_case_starts_before_a_file_with_many_short_cases"]
                if args.mode == "ci-canary" else SUITES)
    flags = ["--collect-only"] if args.mode.startswith("collect") else []
    command = [*selected, *flags, "-q", "--tb=short", "-p", "no:cacheprovider", "--basetemp", str(temporary / "tmp"),
               "--junitxml", str(report / "pytest.xml")]
    # Precreate durable outputs so the notes/ path-hygiene hook sees no additions
    # during pytest. Content grows durably; runtime artifacts stay in TMPDIR.
    for name in ("pytest.xml", "collected.json", "reports.jsonl"):
        (report / name).touch(exist_ok=False)
    reports_path = report / "reports.jsonl"
    # Tests may temporarily prohibit Path.open, builtin open, stat, etc. Report
    # via an already-open stream, rather than introducing filesystem lookups
    # between a test's call and the teardown that restores those operations.
    report_stream = reports_path.open("a")
    encode_report = json.JSONEncoder().encode
    ledger = {"reports": [], "collection_errors": []}
    class Observe:
        def pytest_collection_finish(self, session):
            ledger["collected"] = [item.nodeid for item in session.items]
            (report / "collected.json").write_text(json.dumps(ledger["collected"]))
        def pytest_collectreport(self, report):
            if report.failed:
                ledger["collection_errors"].append(str(report.longrepr))
        def pytest_runtest_logreport(self, report):
            row = {"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome,
                   "wasxfail": getattr(report, "wasxfail", None)}
            if report.failed:
                row["message"] = str(report.longrepr)
            ledger["reports"].append(row)
            report_stream.write(encode_report(row) + "\n")
            report_stream.flush()
    try:
        code = pytest.main(command, plugins=[Observe()])
    finally:
        report_stream.close()
    selected_count = Counter(ledger.get("collected", []))
    completed_count = Counter(r["nodeid"] for r in ledger["reports"] if r["when"] == "teardown")
    partition = {}
    if args.mode == "ci" and not ledger["collection_errors"]:
        from utils.pytest_shard import partition_lanes, balanced_files, read_weights
        lanes = partition_lanes(ledger["collected"])
        weights = read_weights(args.tree / "utils/ci_test_durations.json")
        for total in (4, 6):
            owners = balanced_files((node.split("::", 1)[0] for node in lanes["ordinary"]), total, weights)
            counts = Counter(owners[node.split("::", 1)[0]] for node in lanes["ordinary"])
            union = Counter(lanes["ordinary"])
            for lane, nodes in lanes.items():
                if lane != "ordinary":
                    union.update(nodes)
            partition[str(total)] = {"ordinary_counts": dict(counts), "dedicated": {k: v for k, v in lanes.items() if k != "ordinary"},
                                     "exact_union": union == selected_count}
    save(report / "result.json", {"head": git(args.tree, "rev-parse", "HEAD"), "command": command,
         "exit_code": int(code), "environment": env, "ci_partition": partition,
         "all_selected_occurrences_completed": selected_count == completed_count,
         "scope": "serial full tests/ union, not Python 3.12/Linux CI or separate notes/build jobs", **ledger})
    raise SystemExit(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, help="durable evidence root, separate from runtime scratch")
    parser.add_argument("--mode", choices=["plan", "generate", "replay", "collect", "collect-tests", "ci-canary", "ci-observer-canary", "ci", "suites"], required=True)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--call", type=int)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--derived", action="store_true", help="also test faults derived from actual f8 runner output for c5/c6")
    args = parser.parse_args()
    args.tree, args.scratch = args.tree.resolve(), args.scratch.resolve()
    args.evidence = (args.evidence or args.scratch).resolve()
    env = bootstrap(args.tree, args.scratch)
    if args.mode == "plan":
        print(json.dumps({"head": git(args.tree, "rev-parse", "HEAD"), "cases": CASES,
                          "environment": env, "suites": SUITES}, indent=2))
    elif args.mode == "generate":
        generate(args, env)
    elif args.mode == "replay":
        replay(args, env)
    else:
        checks(args, env)


if __name__ == "__main__":
    main()
