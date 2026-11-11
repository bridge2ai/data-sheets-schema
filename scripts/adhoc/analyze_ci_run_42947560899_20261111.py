#!/usr/bin/env python3
"""Read-only post-CI comparison of run 42947560899 against 42916359440 replay weights.

Purpose:
  Summarize ordinary-shard and dedicated-lane step durations, per-shard JUnit XML
  case-seconds, overlapping case-duration / suite-wall ratios, and per-file deltas
  between reference run 42916359440 and observed run 42947560899.
Inputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/ci-observed-42947560899/run.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/ci-observed-42947560899/shard8.log
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-ci-timing-refresh-20261111/tmp/run-42947560899/jobs.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-ci-timing-refresh-20261111/tmp/run-42947560899/artifacts/tests-py3.12-shard{1..8}/pytest.xml
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-ci-timing-refresh-20261111/utils/ci_test_durations.json
Outputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/ci-observed-42947560899/post_ci_analysis_corrected.json
    (preserves prior /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-ci-timing-refresh-20261111/tmp/run-42947560899/post_ci_analysis.json untouched)
Issue / PR:
  - PR #5814 / Review Issues #5824, #5831, #5832 (Work Unit E2 post-CI read-only observation)
Date:
  - 2026-11-11
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import xml.etree.ElementTree as ET

LEAD_WORKTREE = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111"
)
WORKTREE = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-ci-timing-refresh-20261111")
RUN_OLD_DIR = WORKTREE / "tmp" / "run-42916359440"
RUN_NEW_DIR = WORKTREE / "tmp" / "run-42947560899"
CORRECTED_OUT_PATH = (
    LEAD_WORKTREE / "tmp" / "ci-observed-42947560899" / "post_ci_analysis_corrected.json"
)
DURATIONS = json.loads((WORKTREE / "utils" / "ci_test_durations.json").read_text())
WEIGHTS = DURATIONS["file_seconds"]

DEDICATED_EXECUTION_STEP_NAMES = (
    "Run the required offline API case",
    "Run the required offline SG2 case",
    "Exercise registered evaluation controls offline",
    "Exercise native audit continuation controls offline",
    "Exercise native canary transport and shutdown offline",
    "Exercise experimental canary admission offline",
)


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def fmt_mmss(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}m{s:02d}s"


def main() -> None:
    jobs_data = json.loads((RUN_NEW_DIR / "jobs.json").read_text())
    jobs_by_name = {j["name"]: j for j in jobs_data["jobs"]}

    old_case_times: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    for idx in range(1, 9):
        root = ET.parse(RUN_OLD_DIR / "artifacts" / f"tests-py3.12-shard{idx}" / "pytest.xml").getroot()
        for case in root.iter("testcase"):
            cn = case.attrib["classname"]
            nm = case.attrib["name"]
            t = Decimal(case.attrib["time"])
            old_case_times[(cn, nm)].append(t)

    shard_rows = []
    new_shard_files: dict[int, dict[str, Decimal]] = {}
    new_shard_case_counts: dict[int, dict[str, int]] = {}
    new_shard_cases: dict[int, list[tuple[Decimal, str, str]]] = {}

    for idx in range(1, 9):
        job_name = f"Python 3.12 / shard {idx}"
        job = jobs_by_name[job_name]
        job_s = (parse_iso(job["completed_at"]) - parse_iso(job["started_at"])).total_seconds()
        test_step = next(st for st in job["steps"] if st["number"] == 5)
        step_s = (parse_iso(test_step["completed_at"]) - parse_iso(test_step["started_at"])).total_seconds()

        xml_path = RUN_NEW_DIR / "artifacts" / f"tests-py3.12-shard{idx}" / "pytest.xml"
        root = ET.parse(xml_path).getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        assert suite is not None
        suite_wall_s = float(suite.attrib["time"])

        file_times: dict[str, Decimal] = defaultdict(Decimal)
        file_counts: dict[str, int] = defaultdict(int)
        cases_list: list[tuple[Decimal, str, str]] = []
        total_case_s = Decimal("0")
        case_count = 0
        for case in root.iter("testcase"):
            cn = case.attrib["classname"]
            nm = case.attrib["name"]
            t = Decimal(case.attrib["time"])
            parts = cn.split(".")
            mapped = None
            for i in range(len(parts), 0, -1):
                cand = "/".join(parts[:i]) + ".py"
                if cand in WEIGHTS:
                    mapped = cand
                    break
            assert mapped is not None, f"Unmapped {cn}"
            file_times[mapped] += t
            file_counts[mapped] += 1
            cases_list.append((t, mapped, nm))
            total_case_s += t
            case_count += 1

        new_shard_files[idx] = dict(file_times)
        new_shard_case_counts[idx] = dict(file_counts)
        new_shard_cases[idx] = sorted(cases_list, reverse=True)

        assert int(suite.attrib["tests"]) == case_count, (
            f"Shard {idx} header tests={suite.attrib['tests']} != counted {case_count}"
        )
        replayed_s = sum(Decimal(str(WEIGHTS[f])) for f in file_times)
        shard_rows.append(
            {
                "shard": idx,
                "job_id": job["id"],
                "job_seconds": job_s,
                "job_mmss": fmt_mmss(job_s),
                "test_step_number": test_step["number"],
                "test_step_name": test_step["name"],
                "test_step_seconds": step_s,
                "test_step_mmss": fmt_mmss(step_s),
                "suite_wall_seconds": suite_wall_s,
                "suite_wall_mmss": fmt_mmss(suite_wall_s),
                "files": len(file_times),
                "cases": case_count,
                "replayed_case_seconds_42916359440": float(replayed_s.quantize(Decimal("0.001"))),
                "actual_case_seconds_42947560899": float(total_case_s.quantize(Decimal("0.001"))),
                "case_seconds_delta": float((total_case_s - replayed_s).quantize(Decimal("0.001"))),
                "effective_parallelism_actual_case_over_suite_wall": round(
                    float(total_case_s) / suite_wall_s, 3
                ),
                "max_single_case_seconds": float(new_shard_cases[idx][0][0]),
                "max_single_case_id": f"{new_shard_cases[idx][0][1]}::{new_shard_cases[idx][0][2]}",
            }
        )

    dedicated_rows = []
    for j in jobs_data["jobs"]:
        if j["name"].startswith("Python 3.12 / ") and "shard" not in j["name"]:
            job_s = (parse_iso(j["completed_at"]) - parse_iso(j["started_at"])).total_seconds()
            matched_steps = [
                st for st in j["steps"] if st["name"] in DEDICATED_EXECUTION_STEP_NAMES
            ]
            if not matched_steps:
                raise ValueError(
                    f"Dedicated job {j['name']!r} ({j['id']}) has no matching execution step"
                )
            step_records = []
            for st in matched_steps:
                st_s = (parse_iso(st["completed_at"]) - parse_iso(st["started_at"])).total_seconds()
                step_records.append(
                    {
                        "number": st["number"],
                        "name": st["name"],
                        "seconds": st_s,
                        "mmss": fmt_mmss(st_s),
                    }
                )
            step_s = sum(r["seconds"] for r in step_records)
            dedicated_rows.append(
                {
                    "name": j["name"],
                    "job_id": j["id"],
                    "job_seconds": job_s,
                    "job_mmss": fmt_mmss(job_s),
                    "test_step_number": (
                        step_records[0]["number"]
                        if len(step_records) == 1
                        else [r["number"] for r in step_records]
                    ),
                    "test_step_name": (
                        step_records[0]["name"]
                        if len(step_records) == 1
                        else " + ".join(r["name"] for r in step_records)
                    ),
                    "execution_steps": step_records,
                    "test_step_seconds": step_s,
                    "test_step_mmss": fmt_mmss(step_s),
                }
            )

    s8_files = []
    for f, actual_t in new_shard_files[8].items():
        rep_t = Decimal(str(WEIGHTS[f]))
        cnt = new_shard_case_counts[8][f]
        per_item_est = rep_t / Decimal(cnt)
        s8_files.append(
            {
                "file": f,
                "cases": cnt,
                "replayed_file_seconds": float(rep_t),
                "per_item_priority_seconds": round(float(per_item_est), 3),
                "actual_file_seconds_42947560899": float(actual_t.quantize(Decimal("0.001"))),
                "delta_seconds": float((actual_t - rep_t).quantize(Decimal("0.001"))),
            }
        )
    s8_files_by_priority = sorted(
        s8_files, key=lambda r: (-r["per_item_priority_seconds"], r["file"])
    )
    s8_files_by_delta = sorted(s8_files, key=lambda r: r["delta_seconds"], reverse=True)

    s3_files = []
    for f, actual_t in new_shard_files[3].items():
        rep_t = Decimal(str(WEIGHTS[f]))
        cnt = new_shard_case_counts[3][f]
        s3_files.append(
            {
                "file": f,
                "cases": cnt,
                "replayed_file_seconds": float(rep_t),
                "actual_file_seconds_42947560899": float(actual_t.quantize(Decimal("0.001"))),
                "delta_seconds": float((actual_t - rep_t).quantize(Decimal("0.001"))),
            }
        )
    s3_files_by_delta = sorted(s3_files, key=lambda r: r["delta_seconds"])

    before_journal_files = []
    before_journal_actual_s = 0.0
    before_journal_replayed_s = 0.0
    before_journal_cases = 0
    for row in s8_files_by_priority:
        if row["file"] == "tests/test_bc1_g2_journal.py":
            journal_row = row
            break
        before_journal_files.append(row)
        before_journal_actual_s += row["actual_file_seconds_42947560899"]
        before_journal_replayed_s += row["replayed_file_seconds"]
        before_journal_cases += row["cases"]

    out = {
        "shard_rows": shard_rows,
        "dedicated_rows": dedicated_rows,
        "shard8_journal_queue_position": {
            "journal_row": journal_row,
            "files_scheduled_before_journal": len(before_journal_files),
            "cases_scheduled_before_journal": before_journal_cases,
            "replayed_case_seconds_before_journal": round(before_journal_replayed_s, 3),
            "actual_case_seconds_before_journal": round(before_journal_actual_s, 3),
            "files_before_journal": before_journal_files,
        },
        "shard8_top_file_deltas": s8_files_by_delta[:10],
        "shard8_bottom_file_deltas": list(reversed(s8_files_by_delta[-10:])),
        "shard3_bottom_file_deltas": s3_files_by_delta[:10],
        "shard3_top_file_deltas": list(reversed(s3_files_by_delta[-5:])),
    }
    CORRECTED_OUT_PATH.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
