"""Run two unchanged offline public tests serially and retain their fresh evidence.

This runner does not certify native/model/scientific behavior. The actual tests
own their assertions; small runner tests use explicitly fake child outcomes.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET


NODES = (
    ("neutral", "tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion"),
    ("omission", "tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses"),
)
ORIGINS = (
    "data_sheets_schema.native_shared_selection", "data_sheets_schema.native_shared_receipts",
    "data_sheets_schema.native_shared_capture", "data_sheets_schema.native_shared_execution",
)
BOOTSTRAP = """import importlib,json,pathlib,sys
root=pathlib.Path.cwd().resolve()
origins={}
for name in %r:
    path=pathlib.Path(importlib.import_module(name).__file__).resolve()
    assert path.is_relative_to(root/'src'), (name,str(path))
    origins[name]=str(path)
print('IMPORT_ORIGINS_VERIFIED '+json.dumps(origins,sort_keys=True),flush=True)
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
""" % (ORIGINS,)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS="0")).decode()


def source(repo):
    """Compare materialized tracked bytes/modes with Git; gitlinks stay opaque."""
    entries, valid = {}, True
    for row in git(repo, "ls-tree", "-rz", "HEAD").split("\0"):
        if not row:
            continue
        meta, name = row.split("\t", 1)
        mode, kind, oid = meta.split()
        if kind == "commit":
            entries[name] = {"mode": mode, "gitlink": oid}
            continue
        path = repo / name
        if not path.exists() and not path.is_symlink():
            entries[name] = {"missing": True}
            valid = False
            continue
        raw = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
        actual_mode = "120000" if path.is_symlink() else (
            "100755" if path.stat().st_mode & 0o111 else "100644")
        actual_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        valid = valid and actual_blob == oid and actual_mode == mode
        entries[name] = {"mode": actual_mode, "git_blob": actual_blob,
                         "sha256": digest(raw), "bytes": len(raw)}
    return {"head": git(repo, "rev-parse", "HEAD").strip(),
            "tree": git(repo, "rev-parse", "HEAD^{tree}").strip(),
            "tracked_exact": valid, "entries": entries}


def junit_pass(path, node):
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    return (len(cases) == 1 and cases[0].get("name") == node.split("::")[1]
            and not any(list(root.iter(tag)) for tag in ("failure", "error", "skipped"))
            and all(int(element.get(key, "0")) == 0 for element in root.iter()
                    for key in ("failures", "errors", "skipped")))


def pytest_child(repo, output, label, node):
    base = output / "cases" / label
    if base.exists() or base.is_symlink():
        raise ValueError("pytest basetemp must be fresh")
    command = [sys.executable, "-c", BOOTSTRAP, "-q", "-p", "no:cacheprovider",
               "--basetemp", str(base), "--junitxml", str(output / (label + ".xml")), node]
    save(output / (label + "-command.json"), {"argv": command, "cwd": str(repo)})
    with (output / (label + ".log")).open("xb") as log:
        return subprocess.run(command, cwd=repo, stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH="src:scripts:.")).returncode


def run(repo, output, expected):
    output.mkdir(parents=True, exist_ok=False)
    (output / "cases").mkdir()
    outcome = {"status": "failed", "stages": {}, "scientific_acceptance": "not_assessed"}
    try:
        baseline = source(repo)
        save(output / "source-before.json", baseline)
        if baseline["head"] != expected or not baseline["tracked_exact"]:
            raise ValueError("exact selected source head and tracked bytes required")
        if git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
            raise ValueError("clean checkout required")
        save(output / "run.json", {"head": expected, "tree": baseline["tree"],
            "python": {"path": sys.executable, "version": sys.version},
            "packages": sorted((d.metadata.get("Name", ""), d.version)
                               for d in importlib.metadata.distributions()),
            "workflow": {k: os.environ.get(k) for k in
                         ("GITHUB_REPOSITORY", "GITHUB_REF", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")},
            "environment_overrides": {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "src:scripts:."}})
        for label, node in NODES:
            code = pytest_child(repo, output, label, node)
            outcome["stages"][label] = {"returncode": code, "node": node}
            after = source(repo)
            save(output / ("source-after-" + label + ".json"), after)
            if after != baseline:
                raise ValueError("tracked source changed during " + label)
            if code != 0 or not junit_pass(output / (label + ".xml"), node):
                raise ValueError(label + " must pass exactly one unchanged test without skips")
            outcome["stages"][label]["passed"] = True
        outcome["status"] = "passed"
    except Exception as exc:
        outcome["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        if "omission" not in outcome["stages"]:
            outcome["omission_not_run"] = "neutral completion and source/JUnit checks did not pass"
        save(output / "outcome.json", outcome)
    return 0 if outcome["status"] == "passed" else 1


def inventory(root):
    result = {}
    if root.is_symlink():
        raise ValueError("inventory root must not be a symlink")
    if not root.exists():
        return result
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(parent) / name
            info = path.lstat()
            row = {"mode": stat.S_IMODE(info.st_mode)}
            if path.is_symlink():
                row.update(type="symlink", target=os.readlink(path))
            elif path.is_dir():
                row.update(type="directory")
            elif path.is_file():
                raw = path.read_bytes()
                row.update(type="file", bytes=len(raw), sha256=digest(raw))
            else:
                raise ValueError("unexpected nonregular case entry")
            result[str(path.relative_to(root))] = row
    return result


def finalize(repo, output, expected):
    output.mkdir(parents=True, exist_ok=True)
    upload = output / "upload"
    upload.mkdir(exist_ok=True)
    current = source(repo)
    save(output / "source-final.json", current)
    before_path = output / "source-before.json"
    same = before_path.exists() and json.loads(before_path.read_text()) == current
    save(output / "preservation.json", {"source_unchanged": same,
        "expected_head_matches": current["head"] == expected,
        "run_reached": (output / "outcome.json").is_file()})
    cases = output / "cases"
    before = inventory(cases)
    with tarfile.open(upload / "cases.tar.gz", "w:gz", dereference=False) as archive:
        if cases.exists():
            archive.add(cases, arcname="cases", recursive=True)
    after = inventory(cases)
    save(upload / "case-manifest.json", {"entries": before, "unchanged_during_archive": before == after,
                                       "original_root": str(cases)})
    names = ["run.json", "outcome.json", "source-before.json", "source-final.json", "preservation.json"]
    for label, _ in NODES:
        names += [label + ".log", label + ".xml", label + "-command.json", "source-after-" + label + ".json"]
    for name in names:
        path = output / name
        if path.is_file() and not path.is_symlink():
            shutil.copyfile(path, upload / name)
    artifacts = inventory(upload)
    artifacts.pop("artifact-manifest.json", None)
    save(upload / "artifact-manifest.json", artifacts)
    return 0 if same and current["tracked_exact"] and current["head"] == expected and before == after else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("run", "finalize"))
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    repo, output = Path.cwd().resolve(), args.output.resolve()
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_head):
        parser.error("expected-head must be a full commit SHA")
    if output == temp or not output.is_relative_to(temp) or output.is_relative_to(repo) or repo.is_relative_to(output):
        parser.error("output must be a separate fresh runner-temp child")
    return (run if args.operation == "run" else finalize)(repo, output, args.expected_head)


if __name__ == "__main__":
    raise SystemExit(main())
