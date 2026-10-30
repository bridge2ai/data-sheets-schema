#!/usr/bin/env python3
"""Replay all 96 committed audit/report pairs for PR #5094 F1–F4, 2026-10-28.

Inputs: local git objects at the pinned v2/data trees and v10 canary branch;
candidate report_audit_totals from this checkout (or --candidate-ref).
Outputs: JSON readings, status/changed-pair/regate tables on stdout. Read-only,
offline; no checkout, historical data mutation, provider calls, or tree dumps.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import types

ROOT = Path(__file__).resolve().parents[2]
BASE = "8ff18d2e57ceed1ec4de53169163174f26fecebb"
DATA_REF = "8f181a68699066d5fab847a46d5c2368aedf1e95"
CANARY_REF = "origin/data/chorus-v10-api-canaries-2026-10-22"
CANARY_HEAD = "d184dd4bdb8ac9f02b48d3a323b54a9e278ad905"
MODULE = "src/data_sheets_schema/report_audit_totals.py"
FIELDS = ("checked", "status", "reason", "stated_total", "stated_totals", "stated_by_severity",
          "computed_total", "computed_by_severity", "mismatches", "findings")


def git(*args):
    return subprocess.check_output(
        ["git", "--no-replace-objects", *args], cwd=ROOT,
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_OPTIONAL_LOCKS": "0"},
    ).decode()


def reader(ref):
    module = types.ModuleType("replay_report_audit_totals")
    source = git("show", f"{ref}:{MODULE}")
    exec(compile(source, f"git:{ref}:{MODULE}", "exec"), module.__dict__)
    return module.check_report_audit_totals


def pairs():
    """Enumerate committed files, including gitignored intermediate snapshots."""
    for ref, roots in ((DATA_REF, ("data/d4d_concatenated", "data/ATTIC")),
                       (CANARY_REF, ("data/ATTIC/d4d_concatenated_archived",))):
        files = set(git("ls-tree", "-r", "--name-only", ref, "--", *roots).splitlines())
        for audit in sorted(files):
            path = Path(audit)
            if path.parent.name != "intermediate" or not path.name.endswith("_audit.json"):
                continue
            project = path.name.removesuffix("_audit.json")
            report = str(path.parent.parent / f"{project}_reconciliation.md")
            if report not in files:
                continue
            if ref == CANARY_REF:
                if "-v10_rep1/CHORUS_" not in report:
                    continue
                group = "v10 CHORUS"
            else:
                group = "ATTIC" if report.startswith("data/ATTIC/") else "d4d_concatenated"
            yield ref, group, report, audit


def replay(candidate_ref=None):
    from data_sheets_schema.report_audit_totals import check_report_audit_totals
    old = reader(BASE)
    new = reader(candidate_ref) if candidate_ref else check_report_audit_totals
    rows = []
    assert git("rev-parse", CANARY_REF).strip() == CANARY_HEAD, "canary branch moved; review its new inputs"
    for ref, group, report, audit in pairs():
        report_text, audit_text = git("show", f"{ref}:{report}"), git("show", f"{ref}:{audit}")
        readings = {"v2": old(report_text, audit_text), "new": new(report_text, audit_text)}
        rows.append({"group": group, "pair": report, "audit": audit,
                     "report_sha256": hashlib.sha256(report_text.encode()).hexdigest(),
                     "audit_sha256": hashlib.sha256(audit_text.encode()).hexdigest(),
                     **readings})
    assert Counter(row["group"] for row in rows) == {"d4d_concatenated": 87, "ATTIC": 7, "v10 CHORUS": 2}
    return rows


def comparable(reading):
    return {field: reading[field] for field in FIELDS}


def changes(rows):
    return [row for row in rows if comparable(row["v2"]) != comparable(row["new"])]


def validate(rows):
    """Acceptance against v2, with the four reviewed display-only differences.

    Exact findings equality preserves every v2 mismatch, not just each status.
    Exact totals/status equality prevents dropped or falsely stated totals.
    The two v10 canaries must match all common fields without any exceptions.
    """
    prefix = "data/d4d_concatenated/"
    display_changes = {
        prefix + "claudecode_agent_core/2026-08-22c_claude-opus-5-api-generic-v5_rep3/CHORUS_reconciliation.md": {},
        prefix + "claudecode_api_core/2026-09-04c_claude-opus-5-api-generic-v8_rep1/CM4AI_reconciliation.md": {"medium": 1, "low": 6},
        prefix + "claudecode_api_core/2026-09-04f_claude-opus-5-api-generic-v8_rep1/AI_READI_reconciliation.md": {"medium": 4, "low": 13},
        prefix + "claudecode_api_core/2026-09-04f_claude-opus-5-api-generic-v8_rep1/VOICE_reconciliation.md": {"medium": 4, "low": 11},
    }
    assert {row["pair"] for row in changes(rows)} == set(display_changes)
    for row in rows:
        expected = comparable(row["v2"])
        if row["pair"] in display_changes:
            expected["stated_by_severity"] = display_changes[row["pair"]]
        assert comparable(row["new"]) == expected, row["pair"]
    assert Counter(row["new"]["status"] for row in rows) == {
        "mismatch": 57, "consistent": 31, "no_total_stated": 8,
    }


def markdown(rows):
    lines = ["| Corpus | Reader | mismatch | consistent | no_total_stated | not_checked |",
             "|---|---|---:|---:|---:|---:|"]
    for group in ("d4d_concatenated", "ATTIC", "v10 CHORUS", "ALL"):
        for reader_name in ("v2", "new"):
            counts = Counter(row[reader_name]["status"] for row in rows if group == "ALL" or row["group"] == group)
            lines.append(f"| {group} | {reader_name} | " + " | ".join(str(counts[key]) for key in
                         ("mismatch", "consistent", "no_total_stated", "not_checked")) + " |")
    lines.extend(["", "Changed pairs (common measurement fields; excludes the version stamp/new diagnostic keys):"])
    for row in changes(rows):
        lines.extend(["", f"- `{row['pair']}`"])
        for key in FIELDS:
            if row["v2"][key] != row["new"][key] and key != "findings":
                lines.append(f"  - {key}: `{json.dumps(row['v2'][key], sort_keys=True)}` → `{json.dumps(row['new'][key], sort_keys=True)}`")
    flips = [row for row in rows if bool(row["v2"]["findings"]) != bool(row["new"]["findings"])]
    lines.extend(["", "Totals-only report_regate trigger changes:"])
    lines.extend(f"- `{row['pair']}`: {bool(row['v2']['findings'])} → {bool(row['new']['findings'])}" for row in flips)
    if not flips:
        lines.append("- None.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-ref")
    parser.add_argument("--check", action="store_true", help="Assert the reviewed acceptance contract for all 96 pairs")
    parser.add_argument("--json", action="store_true", help="Emit all per-pair readings and input hashes instead of Markdown")
    args = parser.parse_args()
    rows = replay(args.candidate_ref)
    if args.check:
        validate(rows)
    if args.json:
        print(json.dumps({"v2_ref": git("rev-parse", BASE).strip(), "data_ref": git("rev-parse", DATA_REF).strip(),
                          "canary_ref": git("rev-parse", CANARY_REF).strip(), "rows": rows}, indent=2))
    else:
        print(markdown(rows))


if __name__ == "__main__":
    main()
