#!/usr/bin/env python3
"""Purpose: turn one GitHub Actions run of the test workflow into a failure
inventory: every job with its conclusion and duration, and for each job that
did not succeed, every pytest FAILED/ERROR summary line, grouped by test file
and by a coarse cause class. Written for run 42976790438, the first full CI
run to finish any job on the native stack top (head 1a137b588604), so that the
work of getting the native code green in CI starts from data.

Inputs: argument 1, the run id; argument 2, the output JSON path. Uses `gh`
(read-only API calls) from the primary repository checkout.
Outputs: the JSON, and a summary on stdout (jobs, classes, files).
Serves: owner direction D134; gate G12 of the native critical path; issue
5875. Date: 2026-11-12.

The cause classes are regular expressions on the summary line. They sort the
failures for reading; they are not a diagnosis.
"""
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime

REPO_DIR = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema"
REPO = "bridge2ai/data-sheets-schema"
CLASSES = [
    ("collection: script requires the d4d-executions layout (issue 5875)", r"source must be below the canonical d4d-executions root"),
    ("host layout: needs a d4d-executions directory or scratch roots at run time", r"scratch-native|scratch roots|d4d-executions|StopIteration"),
    ("import origin: native controller dependency imported from another origin", r"imported from another origin"),
    ("scanner: specificity scanner could not derive a meaning", r"delegated_scanner\.ConfigError|api meaning not derived|ConfigError"),
    ("missing file", r"FileNotFoundError|No such file or directory"),
    ("timeout", r"[Tt]imeout|timed out"),
]
ANSI = re.compile(r"\x1b\[[0-9;]*m")
LINE = re.compile(r"^(FAILED|ERROR) (tests/\S+?)(?:::(\S+))?(?: - (.*))?$")


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], cwd=REPO_DIR, capture_output=True, text=True, check=True).stdout


def classify(message: str) -> str:
    for name, pattern in CLASSES:
        if re.search(pattern, message):
            return name
    return "other"


def seconds(job: dict) -> float | None:
    try:
        a = datetime.fromisoformat(job["startedAt"].replace("Z", "+00:00"))
        b = datetime.fromisoformat(job["completedAt"].replace("Z", "+00:00"))
        return (b - a).total_seconds()
    except (KeyError, ValueError, AttributeError):
        return None


def main() -> int:
    run_id, out_path = sys.argv[1], sys.argv[2]
    run = json.loads(gh("run", "view", run_id, "--json", "status,conclusion,headSha,jobs,workflowName,event,createdAt"))
    jobs = []
    rows = []
    for job in run["jobs"]:
        entry = {"id": job["databaseId"], "name": job["name"], "conclusion": job.get("conclusion"),
                 "seconds": seconds(job), "summary_lines": 0, "pytest_tail": None}
        if job.get("conclusion") not in ("success", "skipped"):
            try:
                log = gh("api", "--allow-escape-sequences", f"repos/{REPO}/actions/jobs/{job['databaseId']}/logs")
            except subprocess.CalledProcessError as exc:
                entry["log_error"] = (exc.stderr or "")[:200]
                log = ""
            seen = set()
            for raw in log.splitlines():
                text = ANSI.sub("", raw)
                text = text.split("Z ", 1)[1] if re.match(r"^\S+Z ", text) else text
                match = LINE.match(text.strip())
                if match:
                    kind, path, node, message = match.groups()
                    key = (kind, path, node)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append({"job": job["name"], "kind": kind, "file": path, "node": node or "",
                                 "message": (message or "")[:300], "class": classify(message or "")})
                    entry["summary_lines"] += 1
                elif re.search(r"=+ .*(passed|failed|error|deselected).* in [0-9.]+s", text):
                    entry["pytest_tail"] = text.strip().strip("= ")[:200]
        jobs.append(entry)
    payload = {"run_id": run_id, "head": run["headSha"], "conclusion": run["conclusion"], "jobs": jobs, "failures": rows}
    with open(out_path, "w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    print(f"run {run_id} head {run['headSha'][:12]} conclusion {run['conclusion']}")
    for entry in jobs:
        sec = "" if entry["seconds"] is None else f"{entry['seconds'] / 60:.1f} min"
        print(f"  {entry['conclusion'] or '':10s} {sec:>9s}  {entry['name']}  lines={entry['summary_lines']}  {entry['pytest_tail'] or ''}")
    distinct = {(r["kind"], r["file"], r["node"]): r for r in rows}
    print(f"distinct failing or erroring test ids across jobs: {len(distinct)}")
    by_class = Counter(r["class"] for r in distinct.values())
    for name, count in by_class.most_common():
        print(f"  {count:5d}  {name}")
    by_file = defaultdict(Counter)
    for r in distinct.values():
        by_file[r["file"]][r["class"]] += 1
    print(f"test files with a failure: {len(by_file)}")
    for path, counts in sorted(by_file.items(), key=lambda kv: -sum(kv[1].values())):
        detail = "; ".join(f"{c} {n.split(':')[0]}" for n, c in counts.most_common())
        print(f"  {sum(counts.values()):5d}  {path}  ({detail})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
