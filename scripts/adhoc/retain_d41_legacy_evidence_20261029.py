#!/usr/bin/env python3
"""Retain #5212 offline design evidence, 2026-10-29.

Inputs: d41_legacy_controls_20261029.py scratch captures/replays/check reports.
Outputs: verified exact-byte tar.gz, a concise result ledger and archive hash.
No source/run mutation. Invoke only after all serial executions have finished.
"""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET

PRE = "f8c5ac73caba610d40c49aaceddb31ead3590a72"
BASE = "d9b69d84d9a6936809681ae240bb8e767649ca11"
REPOSITORY = Path(__file__).resolve().parents[2]
DRIVER = REPOSITORY / "scripts/adhoc/d41_legacy_controls_20261029.py"
ORIGINAL_DRIVER = DRIVER.with_name("d41_legacy_controls_20261029_v1.py")
ENVIRONMENT_CONTROLS = ("poetry-environment-canary", "poetry-environment-control",
                        "checkout-environment-canary", "checkout-environment-control")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def manifest(root):
    result = {}
    for path in sorted(root.rglob("*")):
        assert not path.is_symlink(), path
        if path.is_file():
            raw = path.read_bytes()
            result[str(path.relative_to(root))] = {"sha256": sha(raw), "bytes": len(raw)}
    return result


def outcome(row):
    return {k: v for k, v in row.items() if k != "traceback"}


@lru_cache(maxsize=None)
def git_blob_sha(head, relative):
    raw = subprocess.check_output(["git", "--no-replace-objects", "-C", str(REPOSITORY),
                                   "show", f"{head}:{relative}"])
    return sha(raw)


def executed_helper(digest):
    for path in (DRIVER, ORIGINAL_DRIVER):
        if digest == sha(path.read_bytes()):
            return str(path.relative_to(REPOSITORY))
    raise AssertionError(f"executed helper bytes not retained: {digest}")


def verify_source(record, expected_head):
    """Recorded imported bytes must match Git blobs, not just a checkout label."""
    assert record["head"] == expected_head
    executed_helper(record["environment"]["helper_sha256"])
    assert "data_sheets_schema.api_runner" in record["origins"]
    for origin in record["origins"].values():
        marker = "/src/data_sheets_schema/" if "/src/data_sheets_schema/" in origin["path"] else "/tests/"
        relative = marker.lstrip("/") + origin["path"].split(marker, 1)[1]
        assert origin["sha256"] == git_blob_sha(expected_head, relative), relative
    return len(record["origins"])


def junit_summary(path):
    root = ET.parse(path).getroot()
    suites = root.iter("testsuite")
    counts = Counter()
    for suite in suites:
        counts.update({key: int(suite.get(key, "0")) for key in ("tests", "failures", "errors", "skipped")})
    skips = Counter(node.get("message", "") for node in root.iter("skipped"))
    return dict(counts), dict(skips)


def semantic_checks(case, captured, replayed, report):
    """Check archival/predecessor side effects, beyond the returned call count."""
    before, after = captured / "before", replayed / "after"
    checks = {}
    active = [p for p in after.rglob("*_api_usage_*.json") if ".previous-" not in p.name]
    if case == "c1":
        assert report["outcome"]["fake_dispatches"] == 0
        assert "unaccounted attempt" in report["outcome"]["message"]
        assert len(active) == 1
        assert "unrelated-unaccounted-generation" not in load(active[0])["prior_generation_ids"]
        checks["unrelated_generation_not_admitted"] = True
    if report["outcome"]["status"] == "returned":
        assert report["outcome"]["fake_dispatches"] == report["outcome"]["usage_rows"] == 4
        assert len(active) == 1
        account = load(active[0])
        old_index = next(before.rglob("*_snapshot_index.json"), None)
        current_index = next(after.rglob("*_snapshot_index.json"))
        assert load(current_index)["generation_id"] == account["generation_id"]
        checks["current_index_matches_generation"] = True
        if old_index:
            raw = old_index.read_bytes()
            archives = list(after.rglob("*_snapshot_index.previous-*.json"))
            assert any(p.read_bytes() == raw for p in archives)
            checks["exact_old_index_archived"] = True
            try:
                old = json.loads(raw)
            except ValueError:
                old = None
            if isinstance(old, dict) and old.get("generation_id"):
                assert old["generation_id"] in account["prior_generation_ids"]
                checks["exact_predecessor_id_retained"] = True
        old_reasoning = next(before.rglob("*_reasoning.jsonl"), None)
        if old_reasoning:
            assert any(p.read_bytes() == old_reasoning.read_bytes() for p in after.rglob("*_reasoning.previous-*.jsonl"))
            checks["exact_old_reasoning_archived"] = True
        current_reasoning = next(after.rglob("*_reasoning.jsonl"))
        assert all(json.loads(line)["generation_id"] == account["generation_id"] for line in current_reasoning.read_bytes().splitlines())
        checks["active_reasoning_generation_isolated"] = True
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--runtime-ci-root", type=Path, help="retain the two blocked data-write controller traces from pytest basetemp")
    parser.add_argument("--environment-evidence", type=Path, help="copy completed external control reports, verifying every byte")
    args = parser.parse_args()
    external_copies = []
    if args.environment_evidence:
        assert not args.preview, "preview is read-only; copy only after controls finish"
        for name in ENVIRONMENT_CONTROLS:
            folder = args.environment_evidence / name
            assert (folder / "result.json").stat().st_size
            assert (folder / "pytest.xml").stat().st_size
            for original in [*sorted(folder.iterdir()), args.environment_evidence / (name + ".log")]:
                assert original.is_file() and not original.is_symlink()
                relative = original.relative_to(args.environment_evidence)
                retained = args.scratch / relative
                retained.parent.mkdir(parents=True, exist_ok=True)
                raw = original.read_bytes()
                with retained.open("xb") as stream:
                    stream.write(raw)
                assert retained.read_bytes() == raw
                external_copies.append({"path": str(relative), "bytes": len(raw), "sha256": sha(raw)})
    rows = []
    generations = []
    for path in sorted((args.scratch / "captures").glob("*/generation.json")):
        generation = load(path)
        assert generation["pytest_exit"] == 0
        generations.append({"case": path.parent.name, "head": generation["head"],
                            "nodeid": generation["nodeid"], "derived": generation.get("derived_from_emitted_artifacts", False),
                            "executed_helper": executed_helper(generation["environment"]["helper_sha256"]),
                            "imported_sources_verified_against_git": verify_source(generation, PRE)})
        for call in generation["targets"]:
            captured = path.parent / f"call-{call}"
            replayed = args.scratch / "replays" / path.parent.name / f"call-{call}"
            if not (replayed / "result.json").exists() and args.preview:
                continue
            report = load(replayed / "result.json")
            imported_sources = verify_source(report, BASE)
            before = load(captured / "before-manifest.json")
            assert before == manifest(captured / "before") == report["before"]
            assert report["after"] == manifest(replayed / "after")
            assert report["exact_transplant_verified"]
            assert not any("latch_journal" in name for name in before)
            after_hashes = {item["sha256"] for item in report["after"].values()}
            missing = [name for name, item in before.items() if item["sha256"] not in after_hashes]
            frames = re.findall(r'File "([^"]+/src/data_sheets_schema/[^"\n]+)", line (\d+), in ([^\n]+)', report["outcome"].get("traceback", ""))
            rows.append({"case": path.parent.name, "call": call, "nodeid": generation["nodeid"],
                         "classification": {"c1": "A", "c2": "A", "c3": "B", "c4": "B", "c5": "B", "c6": "A", "c7": "C", "c8": "A"}[path.parent.name.split("-")[0]],
                         "pre_d41": outcome(load(captured / "outcome.json")), "base_5212": outcome(report["outcome"]),
                         "captured_file_count": len(before), "captured_bytes": sum(x["bytes"] for x in before.values()),
                         "capture_manifest_sha256": sha((captured / "before-manifest.json").read_bytes()),
                         "transplant_exact": True, "changed_files": len(report["changes"]),
                         "imported_sources_verified_against_git": imported_sources,
                         "original_bytes_not_in_resulting_run": missing,
                         "all_original_bytes_retained_in_capture": True,
                         "semantic_side_effects": semantic_checks(path.parent.name, captured, replayed, report),
                         "base_trace": [{"file": p.split("/src/data_sheets_schema/")[1], "line": int(n), "function": f} for p, n, f in frames],
                         "raw_result": str((replayed / "result.json").relative_to(args.scratch))})
    checks = {}
    for name in ("collect", "collect-tests", "ci-canary", "ci-observer-canary", "suites", "ci", *ENVIRONMENT_CONTROLS):
        path = args.scratch / name / "result.json"
        if path.exists():
            data = load(path)
            assert data["head"] == BASE
            if "environment_control_sha256" in data["environment"]:
                assert data["environment"]["environment_control_sha256"] == sha(
                    (REPOSITORY / "scripts/adhoc/d41_environment_controls_20261029.py").read_bytes())
            junit, skip_reasons = junit_summary(path.parent / "pytest.xml")
            checks[name] = {"head": data["head"], "exit_code": data["exit_code"], "command": data["command"],
                            "executed_helper": executed_helper(data["environment"]["helper_sha256"]),
                            "collected": len(data["collected"]), "collection_errors": len(data["collection_errors"]),
                            "outcomes": dict(Counter(r["outcome"] for r in data["reports"] if r["when"] == "call")),
                            "junit": junit, "skip_reasons": skip_reasons,
                            "failure_reports": [r for r in data["reports"] if r["outcome"] == "failed"],
                            "all_selected_occurrences_completed": data.get("all_selected_occurrences_completed"),
                            "ci_partition": data.get("ci_partition"),
                            "environment": data["environment"]}
            if name == "ci":
                dedicated = {}
                for lane, nodes in data["ci_partition"]["4"]["dedicated"].items():
                    assert len(nodes) == 1
                    reports = [r for r in data["reports"] if r["nodeid"] == nodes[0]]
                    dedicated[lane] = {"nodeid": nodes[0], "reports": reports,
                        "all_phases_passed_without_xfail":
                            [r["when"] for r in reports] == ["setup", "call", "teardown"]
                            and all(r["outcome"] == "passed" and not r["wasxfail"] for r in reports)}
                checks[name]["dedicated_cases"] = dedicated
    helpers = [Path(__file__).resolve(), DRIVER, ORIGINAL_DRIVER,
               REPOSITORY / "scripts/adhoc/status_d41_validation_20261029.py",
               REPOSITORY / "scripts/adhoc/d41_environment_controls_20261029.py",
               *(REPOSITORY / "scripts/adhoc").glob("*d41*20261029*.sh"),
               *(REPOSITORY / "scripts/adhoc").glob("d41_*20261029.sb")]
    summary = {"generations": generations, "results": rows, "validation": checks,
               "helper_hashes": {str(p.relative_to(REPOSITORY)): sha(p.read_bytes()) for p in sorted(helpers)}}
    if external_copies:
        summary["external_environment_reports_copied_verbatim"] = external_copies
    interrupted = args.scratch / "ci-observer-error"
    if interrupted.is_dir():
        partial = [json.loads(line) for line in (interrupted / "reports.jsonl").read_text().splitlines()]
        summary["superseded_validation"] = {"path": "ci-observer-error", "completed": sum(r["when"] == "teardown" for r in partial),
                                             "reason": "observer Path.open conflicts with test filesystem prohibition",
                                             "counted_as_final_gate": False}
    if (args.scratch / "environment-launcher-v1").is_dir():
        original_canary = load(args.scratch / "environment-launcher-v1/poetry-environment-canary/result.json")
        assert original_canary["exit_code"] == 0 and original_canary["all_selected_occurrences_completed"]
        assert len(original_canary["collected"]) == 1
        summary["superseded_environment_validation"] = {
            "path": "environment-launcher-v1", "canary_passed": True,
            "control_tests_started": False,
            "reason": "Bash empty-array expansion under set -u; corrected launcher re-canaries in fresh directories",
            "executed_launcher": "scripts/adhoc/run_d41_environment_serial_20261029_v1.sh"}
    if args.preview:
        print(json.dumps(summary, indent=2))
        return
    assert len(generations) == 10 and len(rows) == 14
    assert {"collect", "suites", "ci"} <= set(checks)
    for name in ("suites", "ci"):
        assert checks[name]["all_selected_occurrences_completed"], name
        assert checks[name]["collection_errors"] == 0, name
    assert checks["suites"]["exit_code"] == 0
    assert all(checks["ci"]["ci_partition"][total]["exact_union"] for total in ("4", "6"))
    assert len(checks["ci"]["dedicated_cases"]) == 4
    assert all(row["all_phases_passed_without_xfail"] for row in checks["ci"]["dedicated_cases"].values())
    for name in ENVIRONMENT_CONTROLS:
        assert checks[name]["exit_code"] == 0 and checks[name]["all_selected_occurrences_completed"]
        assert checks[name]["collection_errors"] == 0
    if args.runtime_ci_root:
        diagnostics = []
        for case in ("test_real_legacy_launcher_keep0", "test_real_legacy_launcher_keep2"):
            for name in ("controller_traceback.txt", "result.json"):
                original = args.runtime_ci_root / case / "registration/attempts/CHORUS_direct_rep1" / name
                raw = original.read_bytes()
                retained = args.scratch / "validation-diagnostics" / case / name
                retained.parent.mkdir(parents=True, exist_ok=True)
                with retained.open("xb") as stream:
                    stream.write(raw)
                assert retained.read_bytes() == raw
                diagnostics.append({"source": str(original), "retained": str(retained.relative_to(args.scratch)),
                                    "sha256": sha(raw), "bytes": len(raw)})
        summary["runtime_diagnostics"] = diagnostics
    args.output.mkdir(parents=True, exist_ok=True)
    files = []
    for top in ("captures", "canary-setup-error", "ci-observer-error", "environment-launcher-v1", "validation-diagnostics"):
        files.extend(p for p in (args.scratch / top).rglob("*") if p.is_file())
    for top in checks:
        files.extend(p for p in (args.scratch / top).iterdir() if p.is_file())
    for p in (args.scratch / "replays").rglob("*"):
        if p.is_file() and "displaced" not in p.relative_to(args.scratch / "replays").parts:
            files.append(p)
    files.extend(args.scratch.glob("*.log"))
    files.extend(args.scratch.glob("*.json"))
    archive = args.output / "authentic_controls.tar.gz"
    assert not archive.exists()
    with tarfile.open(archive, "w:gz") as bundle:
        for path in sorted(set(files)):
            bundle.add(path, arcname=str(path.relative_to(args.scratch)), recursive=False)
    # Verify decompression against every source byte, not tar's exit status.
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            assert member.isfile()
            assert bundle.extractfile(member).read() == (args.scratch / member.name).read_bytes()
    summary["archive"] = {"path": archive.name, "bytes": archive.stat().st_size,
                          "sha256": sha(archive.read_bytes()), "files": len(set(files)), "decompressed_bytes_verified": True}
    with (args.output / "results.json").open("x") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"results": len(rows), "archive": summary["archive"], "validation": checks}, indent=2))


if __name__ == "__main__":
    main()
