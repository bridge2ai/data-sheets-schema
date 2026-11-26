#!/usr/bin/env python3
"""Compare three immutable scanner archives for issue 6384, 2026-11-26.

Inputs: the named source commit, PR 6366 base and confirmed remote-main commit.
Outputs: fresh Git archives, complete scanner outputs and ordered-array receipt.
No measured run, response, candidate, evaluation or credential is read. Scanner,
tokens and exceptions must be byte-identical across all three source archives.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

sys.dont_write_bytecode = True

from replay_scorer_session_identity_6384_20261126 import require_output_outside

BASE = "047137b9ea30603abbe3ede25a15c4a753f71978"
REMOTE_MAIN = "483bed03b14a4c70d6e68dad6679631350a12b72"
SKILL = ".claude/skills/d4d-generation-specificity-audit"
ASSETS = ("scan.py", "tokens.yaml", "exceptions.yaml")
ARRAYS = ("hits", "violations", "test_dependencies")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def physical(path):
    value = Path(os.path.abspath(path))
    require(not any(item.is_symlink() for item in (value, *value.parents)), "symlink in source or output path")
    return value


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, timeout=120).stdout


def write_json(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
    require(path.read_bytes() == raw, "saved evidence bytes differ")
    return sha(raw)


def compare(before, after):
    left = Counter(json.dumps(item, sort_keys=True) for item in before)
    right = Counter(json.dumps(item, sort_keys=True) for item in after)
    return {"before_count": len(before), "after_count": len(after), "ordered_equal": before == after,
            "added": [json.loads(item) for item in (right - left).elements()],
            "removed": [json.loads(item) for item in (left - right).elements()]}


def verify(args):
    root, out = physical(args.repo_root), physical(args.evidence_directory)
    require(not out.exists() and root != out and root not in out.parents, "output must be fresh and outside checkout")
    require_output_outside(out, (root,))
    candidate = git(root, "rev-parse", args.candidate_ref).decode().strip()
    require(git(root, "rev-parse", "HEAD").decode().strip() == candidate, "candidate is not current HEAD")
    require(not git(root, "diff", "HEAD", "--"), "tracked source has uncommitted changes")
    out.mkdir(parents=False, exist_ok=False)
    results, documents, reference_assets = {}, {}, None
    try:
        for name, commit in (("base", BASE), ("remote-main", REMOTE_MAIN), ("candidate", candidate)):
            source = out / (name + "-" + commit[:12])
            archive = out / (name + ".tar")
            source.mkdir()
            with archive.open("xb") as stream:
                subprocess.run(["git", "-C", str(root), "archive", "--format=tar", commit],
                               stdout=stream, check=True, timeout=120)
            with tarfile.open(archive) as stream:
                stream.extractall(source, filter="data")
            assets = {item: sha((source / SKILL / item).read_bytes()) for item in ASSETS}
            if reference_assets is None:
                reference_assets = assets
            require(assets == reference_assets, "scanner/token/exception bytes differ across source refs")
            tool = source / SKILL / "scan.py"
            output = out / (name + ".json")
            command = [sys.executable, "-P", "-B", str(tool), "--root", str(source),
                       "--report", str(out / (name + ".md")), "--json", str(output),
                       "--tokens", str(tool.with_name("tokens.yaml")),
                       "--exceptions", str(tool.with_name("exceptions.yaml")), "--full-json"]
            env = {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR", "VIRTUAL_ENV") if key in os.environ}
            env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PIP_NO_INDEX="1", UV_OFFLINE="1")
            print(json.dumps({"phase": "scanner", "source": name, "commit": commit}), flush=True)
            started = time.monotonic()
            with (out / (name + ".stdout.txt")).open("xb") as stdout, (out / (name + ".stderr.txt")).open("xb") as stderr:
                completed = subprocess.run(command, cwd=source, env=env, stdout=stdout,
                                           stderr=stderr, timeout=600)
            require(completed.returncode in (0, 1), "scanner did not complete for " + name)
            raw = output.read_bytes()
            document = json.loads(raw)
            require(document.get("self_test", {}).get("passed") is True, "scanner self-test failed for " + name)
            require(all(isinstance(document.get(key), list) and all(isinstance(item, dict) for item in document[key])
                        for key in ARRAYS), "scanner lacks complete arrays for " + name)
            results[name] = {"commit": commit, "archive_sha256": sha(archive.read_bytes()),
                             "scan_sha256": sha(raw), "command": command,
                             "returncode": completed.returncode, "elapsed_seconds": time.monotonic() - started,
                             "scanner_assets": assets, "self_test": document["self_test"]}
            documents[name] = document
        comparisons = {name: {key: compare(documents[name][key], documents["candidate"][key]) for key in ARRAYS}
                       for name in ("base", "remote-main")}
        same = all(row["ordered_equal"] for baseline in comparisons.values() for row in baseline.values())
        require(git(root, "rev-parse", "HEAD").decode().strip() == candidate
                and not git(root, "diff", "HEAD", "--"), "source changed during scanner comparisons")
        receipt = {"status": "PASSED" if same else "BLOCKED", "candidate": candidate,
                   "runs": results, "comparisons": comparisons, "full_ordered_objects_compared": True,
                   "scanner_assets_unchanged": True, "scoring_calls": 0, "evaluation_writes": 0}
        digest = write_json(out / "comparison.json", receipt)
        print(json.dumps({"status": receipt["status"], "receipt_sha256": digest,
                          "comparisons": {name: {key: {field: value[field] for field in
                           ("before_count", "after_count", "ordered_equal")} for key, value in rows.items()}
                           for name, rows in comparisons.items()}}, sort_keys=True), flush=True)
        return 0 if same else 2
    except Exception as error:
        write_json(out / "failure.json", {"status": "REFUSED", "reason": str(error),
                                          "candidate": candidate, "completed_runs": results})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--candidate-ref", required=True)
    parser.add_argument("--evidence-directory", type=Path, required=True)
    return verify(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
