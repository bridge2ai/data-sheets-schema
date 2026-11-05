#!/usr/bin/env python3
# Purpose: reproduce BC1+G2 merge resolutions and attribute silent lost lines.
# Inputs: local target/incoming/base commits and current merge tree; outputs:
# conflict snapshots and a per-line non-merge commit ledger in scratch/reviews.
# Serves integration task 3, 2026-11-03. Offline; never authors protected files.
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TARGET = "3f673180d6959f741d51db88f8c1fa6867e4d81d"
INCOMING = "9fca277e851660ae5ccb8455505535bd0eb85925"
BASE = "3c41133fcdcdb6db4d09564dc365b8b42b39c390"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode()


def blob(ref, path):
    result = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True)
    return result.stdout.decode(errors="surrogateescape") if result.returncode == 0 else ""


def resolve(output):
    output.mkdir(parents=True, exist_ok=True)
    for relative in ("scripts/build_api_registrations.py", "tests/test_build_api_registrations.py",
                     "src/data_sheets_schema/typed_audit_runtime.py"):
        path = ROOT / relative
        before = path.read_text()
        (output / (path.name + ".conflicted.txt")).write_text(before)
        matches = list(re.finditer(r"^<<<<<<< HEAD\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*\n", before, re.M | re.S))
        expected = 5 if relative.startswith("scripts/") else 1
        assert len(matches) == expected, (relative, len(matches))
        def choose(match):
            ours, theirs = match.groups()
            if path.name == "typed_audit_runtime.py":
                return ours + theirs  # Main's legacy refusal precedes BC1 dispatch.
            if "target_projects = load_registry" in ours:
                return theirs  # Additional Round 2 guard; never permit empty --all.
            return ours
        after = re.sub(r"^<<<<<<< HEAD\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*\n", choose, before, flags=re.M | re.S)
        if relative.startswith("scripts/"):
            redundant = ('    if bounded_carry_version == 1 and not reg_registry.declares(project):\n'
                         '        raise ValueError(f"BC1 project {project!r} is not declared in source manifest {sm_resolved!s}")\n')
            assert after.count(redundant) == 1
            after = after.replace(redundant, "")
            old = "                                 source_manifest=source_manifest, root_dir=worktree)"
            assert after.count(old) == 1
            after = after.replace(old, "                                 source_manifest=select_manifest(proj, bundle,\n"
                "                                     requested=source_manifest if source_manifest is not None else AUTO),\n"
                "                                 root_dir=worktree)")
        assert not re.search(r"^(<<<<<<<|=======|>>>>>>>)", after, re.M)
        path.write_text(after)
        assert path.read_text() == after
        print(relative, len(matches), hashlib.sha256(after.encode()).hexdigest())


def audit(output, ref):
    paths = git("diff", "--name-only", BASE, INCOMING).splitlines()
    records = []
    for path in paths:
        common = set(blob(BASE, path).splitlines()) & set(blob(TARGET, path).splitlines())
        if not common:
            continue
        current = blob(ref, path) if ref else ((ROOT / path).read_text(errors="surrogateescape") if (ROOT / path).is_file() else "")
        lost = sorted(line for line in common - set(current.splitlines()) if line.strip())
        if not lost:
            continue
        history = git("log", "--no-merges", "--format=COMMIT|%H|%s", "-p", "--no-renames", BASE + ".." + INCOMING, "--", path)
        removed = defaultdict(list)
        commit = None
        for line in history.splitlines():
            if line.startswith("COMMIT|"):
                _, sha, subject = line.split("|", 2)
                commit = {"commit": sha, "subject": subject}
            elif line.startswith("-") and not line.startswith("--- ") and commit:
                removed[line[1:]].append(commit)
        rows = []
        for line in lost:
            row = {"line": line, "non_merge_removals": removed[line]}
            # Main extracted _render_prepared after BC1 added term_policy to
            # prepare. The merge forwards that existing feature through the
            # new formatter. These two line changes are that transposition,
            # not stale main bytes: retain the formatter and both byte checks.
            if path == "src/data_sheets_schema/audit_omissions.py" and line in (
                "                     chunks, prior, max_output_tokens, max_request_bytes):",
                "        max_output_tokens=max_output_tokens, max_request_bytes=max_request_bytes)",
            ):
                row["semantic_origin"] = {
                    "commit": "b2525adb92159776d3fbeb22ecf41f564143462a",
                    "reason": "Forward existing BC1 term_policy through main's extracted _render_prepared; "
                              "retain main's formatter and complete-request byte check.",
                }
            rows.append(row)
        records.append({"path": path, "lost_count": len(rows), "lines": rows})
    result = {"target": TARGET, "incoming": INCOMING, "base": BASE, "result": ref or "working merge",
              "files": records, "unattributed": [{"path": item["path"], "line": row["line"]}
                for item in records for row in item["lines"]
                if not row["non_merge_removals"] and not row.get("semantic_origin")]}
    raw = json.dumps(result, indent=2, sort_keys=True).encode() + b"\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    assert output.read_bytes() == raw
    for item in records:
        print(item["path"], item["lost_count"], "unattributed", sum(not row["non_merge_removals"] for row in item["lines"]))
    print("unattributed:", json.dumps(result["unattributed"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("resolve", "audit"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--ref")
    args = parser.parse_args()
    resolve(args.output) if args.action == "resolve" else audit(args.output, args.ref)
