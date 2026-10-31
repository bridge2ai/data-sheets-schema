#!/usr/bin/env python3
"""#5212/D68-D73, 2026-10-31: publish the requested local implementation report.

Inputs: reviewed repository note, retained validation/census JSON, local Git
history and the pinned main/packet SHAs saved immediately before the merge.
Output: the owner's exact report path, or an explicit scratch preview. No
network, Git mutation, production edit or write to a run-evidence directory.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-5212fix"
REPORT = ROOT.parent / "plans/reviews/d41_legacy_impl_d68_d70_2026-10-30.md"
EVIDENCE = ROOT / "notes/reviews/d73_5212_evidence_20261031"
NOTE = ROOT / "notes/reviews/d73_5212_review_followup_2026-10-31.md"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=REPORT)
args = parser.parse_args()
target = args.output.resolve()
assert target == REPORT.resolve() or target.is_relative_to(SCRATCH.resolve())


def git(*command, optional=False):
    result = subprocess.run(["git", "--no-replace-objects", "-C", str(ROOT), *command],
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_OPTIONAL_LOCKS": "0"},
        capture_output=True, text=True)
    if not optional:
        result.check_returncode()
    return result


head = git("rev-parse", "HEAD").stdout.strip()
branch = git("branch", "--show-current").stdout.strip()
main = (SCRATCH / "d73-main-sha.txt").read_text().strip()
packet = (SCRATCH / "d73-packet-sha.txt").read_text().strip()
assert (SCRATCH / "d73-main-merge.log").stat().st_size
git("merge-base", "--is-ancestor", "20def9d63", head)
protected = git("diff", "--name-only", "20def9d63", packet, "--",
    "src/data_sheets_schema/shared_generation.py", ":(glob)**/canonical_hashes.yaml",
    "data", "notes/coordination/STATUS.md").stdout.strip()
assert not protected, protected
conflicts = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
merged = git("merge-base", "--is-ancestor", main, head, optional=True).returncode == 0
assert conflicts or merged, "retain the merge outcome before publishing"
note = NOTE.read_text()
assert "Work is in progress" not in note, "review the report note before publication"
validation = json.loads((EVIDENCE / "validation.json").read_text())

lines = ["# D41 legacy implementation: D68–D70 and D73 review follow-up", "",
    f"Report generated: {datetime.now(timezone.utc).isoformat()}", "",
    f"Final head: `{head}`. Branch: `{branch}`.", "",
    f"Pre-merge packet: `{packet}`. Local `origin/main` pinned for the merge: `{main}`.", ""]
if conflicts:
    lines += ["The main merge is uncommitted. Work stopped at the production conflict, as instructed;",
              "no production conflict was resolved and no merge commit was made.", "",
              "Unmerged paths:", "", *[f"- `{path}`" for path in conflicts], "",
              "Post-merge focused tests and collection were not run against the conflicted tree.", ""]
else:
    lines += ["The pinned local main commit is an ancestor of the final head.", ""]

lines += ["## Implementation, review findings and #5409 dispositions", "",
          note.partition("\n")[2].strip(), "", "## Retained validation results", "",
          "Counts below come from the saved pytest phase reports. A written report from an",
          "interrupted run is explicitly marked incomplete. Expected failing controls and",
          "superseded attempts are retained separately from the final gates.", "",
          "| Phase | Run head | Selected | Passed calls | Failed nodes | Skipped nodes | Complete |",
          "|---|---|---:|---:|---:|---:|---|"]
for row in validation:
    if "environment" not in row:
        lines.append(f"| {row['phase']} | — | — | — | — | — | no report |")
        continue
    failed = len({item["nodeid"] for item in row["failed_phases"]})
    skipped = len({item["nodeid"] for item in row["skipped_phases"]})
    lines.append(f"| {row['phase']} | `{row['environment']['head'][:9]}` | {row['selected']} | "
        f"{row['call_outcomes'].get('passed', 0)} | {failed} | {skipped} | {row['complete']} |")
lines += ["", f"Full commands, hashes, failure traces and per-file counts: [validation ledger]({EVIDENCE / 'validation.json'}).",
          "", "## Committed-record census", "",
          "This includes generation and derived provenance, including the four historical",
          "derived unions omitted by the earlier generation-only census. Eligibility here",
          "is the integrity/age gate in the two consumers, not a claim that every record",
          "meets their other quality or registration requirements.", "",
          "| Ref/scope | Records | Pre-D41 | Post-D41 | Age unestablished | Canary before → after | Evaluation before → after |",
          "|---|---:|---:|---:|---:|---:|---:|"]
for name in ("base", "packet", "merged"):
    path = EVIDENCE / f"corpus-{name}.json"
    if not path.exists():
        continue
    census = json.loads(path.read_text())
    assert not census["parse_errors"] and census["counts"]["v8_changes"] == 0
    counts = census["counts"]
    assert counts["record_types"].get("d4d_derived_provenance") == 4
    for scope, scoped in [("all", counts), *counts["scopes"].items()]:
        ages = scoped["age"]
        lines.append(f"| {name}/{scope} | {scoped['records']} | {ages.get('pre-D41', 0)} | "
            f"{ages.get('post-D41', 0)} | {ages.get('age unestablished', 0)} | "
            f"{scoped['before']['canary']} → {scoped['after']['canary']} | "
            f"{scoped['before']['evaluation']} → {scoped['after']['evaluation']} |")
    lines += ["", f"{name}: `{census['ref']}`; {counts['v8_records']} v8 records, "
              f"{counts['v8_changes']} eligibility changes. [Every record]({path}).", ""]

lines += ["## Every commit since 4cde66d2d", "",
          "All reachable commits in `4cde66d2d..HEAD`, including incoming main history if merged:", ""]
for sha in git("log", "--reverse", "--format=%H", "4cde66d2d..HEAD").stdout.splitlines():
    lines.append(f"- `{sha}`")
lines += ["", "Packet first-parent subjects:", ""]
for entry in git("log", "--first-parent", "--reverse", "--format=%H %s", "4cde66d2d..HEAD").stdout.splitlines():
    sha, _, subject = entry.partition(" ")
    lines.append(f"- `{sha[:9]}` — {subject.replace('@', '(at)')}")
lines += ["", "The stopped `.d68-validation/` gate remains evidence of its recorded older commits only.",
          "This report does not count it as validation of the follow-up. No push, remote Git",
          "operation, `gh`, network access or provider call was performed for this task.", ""]
rendered = "\n".join(lines)
target.write_text(rendered)
assert target.stat().st_size and target.read_text() == rendered
print(json.dumps({"head": head, "main": main, "report": str(target),
    "bytes": target.stat().st_size, "merge_conflicts": conflicts}, indent=2))
