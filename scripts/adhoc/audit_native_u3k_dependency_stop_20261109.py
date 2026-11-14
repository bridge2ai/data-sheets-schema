#!/usr/bin/env python3
"""Preserve the U3-K dependency-stop diagnosis, 2026-11-09.

Inputs: an existing stopped cohort, its exact dependency manifest/tree/archive.
Output: one new JSON audit; never modifies inputs, repairs witnesses, or runs tests.
Serves the native U3-K lifecycle integrity stop. Standard library only; use -B -S.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def utc(epoch: float | None) -> str | None:
    return None if epoch is None else dt.datetime.fromtimestamp(epoch, dt.timezone.utc).isoformat()


def metadata(path: Path) -> dict:
    entry = path.lstat()
    result = {
        "path": str(path), "bytes": entry.st_size, "mode": stat.filemode(entry.st_mode),
        "nlink": entry.st_nlink, "mtime_epoch": entry.st_mtime,
        "mtime_utc": utc(entry.st_mtime), "ctime_epoch": entry.st_ctime,
        "ctime_utc": utc(entry.st_ctime),
        "birth_epoch": getattr(entry, "st_birthtime", None),
        "birth_utc": utc(getattr(entry, "st_birthtime", None)),
    }
    if stat.S_ISREG(entry.st_mode):
        result["sha256"] = digest(path.read_bytes())
    elif stat.S_ISLNK(entry.st_mode):
        result["symlink_target"] = os.readlink(path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    cohort = args.cohort.resolve(strict=True)
    output = args.out.absolute()
    if output.exists() or output.is_symlink():
        raise SystemExit("Refusing to overwrite audit output")
    if cohort in output.parents:
        raise SystemExit("Audit must be outside the original cohort")
    outcome_raw = (cohort / "outcome.json").read_bytes()
    outcome = json.loads(outcome_raw)
    links = json.loads((cohort / "dependency-links.json").read_bytes())
    before = links["fairscape_dependency"]
    tree = Path(before["package_root"])
    physical_tree = tree.resolve(strict=True)
    if tree != physical_tree:
        raise SystemExit("Dependency root now resolves elsewhere; audit separately")
    manifest_path = tree.parent / "manifest.json"
    archive_path = tree.parent / "source.tar"
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    pinned = manifest["files"]
    actual = {}
    directories = []
    for current, dirs, names in os.walk(tree, followlinks=False):
        for name in sorted(dirs + names):
            path = Path(current) / name
            relative = path.relative_to(tree).as_posix()
            item = metadata(path)
            if stat.S_ISDIR(path.lstat().st_mode):
                directories.append(relative)
            else:
                actual[relative] = item
    comparisons = {}
    for name, expected in sorted(pinned.items()):
        observed = actual.get(name)
        comparisons[name] = {
            "expected": expected, "observed": observed,
            "bytes_match": observed is not None and observed["bytes"] == expected["bytes"],
            "sha256_match": observed is not None and observed.get("sha256") == expected["sha256"],
        }
    extras = {name: actual[name] for name in sorted(actual.keys() - pinned.keys())}
    mismatches = [name for name, item in comparisons.items()
                  if not item["sha256_match"] or not item["bytes_match"]]
    witnesses = {}
    for name in (
        "outcome.json", "dependency-links.json", "plan.json", "origins-before.json",
        "origins-after.json", "worker-outcome.json", "source-stability.json",
        "u3k-harness.json", "pytest.xml", "pytest.log", "early-cutoff.json", "u3g-cutoff.json",
    ):
        path = cohort / name
        witnesses[name] = metadata(path) if path.exists() or path.is_symlink() else {"missing": True}
    xml = ET.fromstring((cohort / "pytest.xml").read_bytes())
    completed = []
    for case in xml.iter("testcase"):
        findings = []
        for child in case:
            if child.tag in {"failure", "error", "skipped"}:
                findings.append({"kind": child.tag, "attributes": dict(child.attrib), "text": child.text or ""})
        completed.append({
            "nodeid": case.get("classname", "").replace(".", "/") + ".py::" + case.get("name", ""),
            "junit_attributes": dict(case.attrib), "diagnostics": findings,
        })
    log_lines = (cohort / "pytest.log").read_text(errors="replace").splitlines()
    selected_diagnostics = [
        {"line": index + 1, "text": line} for index, line in enumerate(log_lines)
        if "unexpected FAIRSCAPE dependency file" in line
        or line.startswith("FAILED ")
        or line.startswith("E ")
        or "= 5 failed" in line
    ]
    pids = sorted({int(item[0]) for item in outcome.get("observed_processes", [])})
    ps = None
    if pids:
        command = ["/bin/ps", "-p", ",".join(map(str, pids)), "-o", "pid=,lstart=,stat=,comm="]
        sample_time = dt.datetime.now(dt.timezone.utc).isoformat()
        sample = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        ps = {
            "sampled_at_utc": sample_time, "command": command,
            "returncode": sample.returncode, "stdout": sample.stdout, "stderr": sample.stderr,
            "none_of_recorded_pids_currently_present": sample.returncode == 1 and not sample.stdout.strip() and not sample.stderr.strip(),
            "limits": "Read-only PID sample; any present PID requires creation-time comparison. Does not establish absence of never-observed orphans or repair cleanup evidence.",
        }
    archive = metadata(archive_path)
    result = {
        "schema": "native-u3k-dependency-stop-audit-v1",
        "audited_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "STOP: incomplete lifecycle integrity and cleanup evidence; no acceptance inferred",
        "script": metadata(Path(__file__).resolve()),
        "interpreter": {"executable": sys.executable, "version": sys.version, "dont_write_bytecode": sys.dont_write_bytecode},
        "cohort": str(cohort), "original_outcome": outcome,
        "original_outcome_sha256": digest(outcome_raw),
        "original_witnesses": witnesses,
        "dependency_before": before,
        "dependency_now": {
            "physical_tree": str(physical_tree), "inventory_method": "os.walk, followlinks=False, lstat; includes hidden and ignored files",
            "manifest": metadata(manifest_path), "archive": archive,
            "manifest_matches_before": digest(manifest_raw) == before["manifest_sha256"],
            "archive_matches_before": archive["sha256"] == before["archive_sha256"],
            "pinned_count": len(pinned), "actual_nondirectory_count": len(actual),
            "missing_pinned": sorted(pinned.keys() - actual.keys()), "pinned_mismatches": mismatches,
            "all_pinned_bytes_match": not mismatches,
            "pinned_comparisons": comparisons, "unexpected_entries": extras,
            "unexpected_bytes": sum(item["bytes"] for item in extras.values()),
            "symlink_entries": {name: item for name, item in actual.items() if "symlink_target" in item},
            "directories": directories,
            "creator_attribution": "Unknown; filesystem timestamps do not identify the creator.",
            "interpretation": "Pinned byte equality does not repair the changed dependency roster or absent final witnesses.",
        },
        "junit": {"suite_attributes": [dict(suite.attrib) for suite in xml.iter("testsuite")],
                  "completed_case_count": len(completed), "completed_cases": completed},
        "log_diagnostics": selected_diagnostics,
        "log_tail": log_lines[-45:],
        "cutoffs": {name: json.loads((cohort / name).read_bytes()) for name in ("early-cutoff.json", "u3g-cutoff.json")},
        "read_only_process_sample": ps,
        "claims_not_made": ["No original witness repaired", "No tests rerun", "No source-origin completion established", "No cleanup verification established", "No creator identified"],
    }
    output.parent.resolve(strict=True)
    encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    with output.open("xb") as stream:
        stream.write(encoded)
    persisted = output.read_bytes()
    if persisted != encoded:
        raise SystemExit("Audit output readback mismatch")
    print(json.dumps({"output": str(output), "bytes": len(persisted), "sha256": digest(persisted),
                      "pinned": len(pinned), "mismatches": len(mismatches), "extras": len(extras),
                      "completed_cases": len(completed), "status": result["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
