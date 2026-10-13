#!/usr/bin/env python3
"""Preserve the metadata procedure used for the PR #5022 CI-failure review.

Purpose: pin completed GitHub evidence, extract the failure and preceding test,
    and save exact public source bytes for the bounded cache-isolation review.
Inputs: --repo (Git object database), --evidence-dir containing job.json,
    job.log, pr.json and the four saved open-issue query JSON files below.
Outputs: a NEW --output-dir with source preimages, a line-numbered log excerpt,
    diagnosis.json and diagnosis.md. No project imports or test execution.
Issue: #5022 / #5016; the suspected test-isolation defect is not declared proven.
Date: 2026-10-12 (local); GitHub job timestamps are 2026-10-13 UTC.

This saved helper follows the original read-only analysis; it does not replace
or claim to have produced the retained original diagnosis01 artifacts.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


HEAD = "363714122048ef40b567229158d4995afb7735bb"
JOB_URL = (
    "https://github.com/bridge2ai/data-sheets-schema/actions/runs/"
    "38342496007/job/115116774404"
)
TARGET = (
    "tests/test_identifier_form.py::TestOnTheRunner::"
    "test_the_written_full_and_core_carry_the_curie_and_the_grounding_check_sees_none"
)
PREDECESSOR = (
    "tests/test_schema/test_datacite_relationships.py::"
    "TestTheDigestShowsNestedVocabularies::"
    "test_truncation_still_announces_itself_if_it_ever_happens"
)
SOURCES = (
    "tests/test_schema/test_datacite_relationships.py",
    "tests/test_identifier_form.py",
    "src/data_sheets_schema/schema_digest.py",
    "src/data_sheets_schema/schema_sync.py",
    "src/data_sheets_schema/api_runner.py",
)
QUERIES = (
    "open-merged-digest-issues.json",
    "open-identifier-issues.json",
    "open-enum-limit-issues.json",
    "open-digest-cache-issues.json",
)


def pin(path, label):
    data = path.read_bytes()
    return {"path": label, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence_dir
    job = json.loads((evidence / "job.json").read_text())
    if job["id"] != 115116774404 or job["conclusion"] != "failure":
        raise SystemExit("expected the completed failing job, not another receipt")
    if job.get("head_sha") != HEAD:
        raise SystemExit("job head differs from the reviewed PR head")
    # Refuse to overwrite the original retained evidence or a prior successor.
    args.output_dir.mkdir(parents=True, exist_ok=False)
    source_pins = []
    for name in SOURCES:
        data = subprocess.check_output(
            ["git", "-C", str(args.repo), "show", HEAD + ":" + name]
        )
        destination = args.output_dir / "source-at-pr-head" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        source_pins.append(pin(destination, name))

    raw = (evidence / "job.log").read_text()
    lines = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", raw).splitlines()
    selected = []
    predecessor_lines = []
    target_lines = []
    summary = []
    for number, line in enumerate(lines, 1):
        if PREDECESSOR in line:
            predecessor_lines.append({"line": number, "text": line})
        if TARGET in line:
            target_lines.append({"line": number, "text": line})
        if "1 failed, 3768 passed, 3 skipped" in line:
            summary.append({"line": number, "text": line})
        if (7875 <= number <= 7955 or 8000 <= number <= 8003
                or PREDECESSOR in line or ("[gw0]" in line and TARGET in line)):
            selected.append(f"{number}: {line}")
    if len(summary) != 1 or not predecessor_lines or not target_lines:
        raise SystemExit("the saved log does not match the reviewed failure")
    (args.output_dir / "failure-excerpt.txt").write_text("\n".join(selected) + "\n")

    searches = []
    for name in QUERIES:
        rows = json.loads((evidence / name).read_text())
        searches.append({
            "file": name, "count": len(rows),
            "issues": [{key: row[key] for key in ("number", "title", "url")}
                       for row in rows],
        })
    facts = {
        "schema_version": 1,
        "classification": "same-worker test-state pollution candidate; runtime not assessed by this helper",
        "head": HEAD, "job_url": JOB_URL,
        "source_pins": source_pins,
        "evidence_pins": [pin(evidence / name, name)
                          for name in ("job.json", "job.log", "pr.json", *QUERIES)],
        "helper": pin(Path(__file__), Path(__file__).name),
        "target": TARGET, "preceding_candidate": PREDECESSOR,
        "predecessor_log_records": predecessor_lines,
        "target_log_records": target_lines,
        "summary_log_records": summary,
        "issue_searches": searches,
        "limitations": [
            "No project imports, test execution or GitHub mutation.",
            "Same-worker order and source are evidence of a candidate, not causal proof.",
            "Saved issue queries are bounded searches, not an exhaustive historical-comment audit.",
        ],
    }
    (args.output_dir / "diagnosis.json").write_text(json.dumps(facts, indent=2) + "\n")
    report = f"""# PR #5022 CI failure: bounded static diagnosis

The [completed job]({JOB_URL}) at `{HEAD}` reports **1 failed, 3,768 passed,
3 skipped**. The sole target is `{TARGET}`. It raises the real schema-sync
guard: Dataset's merged schema matches, but its digest does not.

The same worker (`gw0`) first passed `{PREDECESSOR}`. That test temporarily
sets `MAX_ENUM_VALUES=5` and clears only `_BUILD_CACHE`, leaving `_TEXT_CACHE`
whose key omits this test-mutated constant. Source anchors at the exact head:
[test](https://github.com/bridge2ai/data-sheets-schema/blob/{HEAD}/tests/test_schema/test_datacite_relationships.py#L220-L232),
[text cache](https://github.com/bridge2ai/data-sheets-schema/blob/{HEAD}/src/data_sheets_schema/schema_digest.py#L799-L816).

This is a source-supported order-dependence candidate. A fresh target-only run
and a fresh serial predecessor→target run are the bounded causal comparison.
This helper does not execute them or ingest later runtime results. A warm
default text cache can also hide the intended truncation assertion; the test
should exercise a specific enum truncation and preserve normal text afterward.
No production cache change, guard weakening, schema regeneration or weight
rollback is justified solely by these static observations.

The issue-query summaries, source hashes and exact log records are in
`diagnosis.json`. Original downloaded logs and the first diagnosis remain
unchanged. Query matches are not a claim of exhaustive closed-issue/comment
coverage. Local source searches during the review included ignored files.
"""
    (args.output_dir / "diagnosis.md").write_text(report)


if __name__ == "__main__":
    main()
