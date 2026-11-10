#!/usr/bin/env python3
"""Analyze cached GitHub Actions run/job timestamps and generate the CI queue checkpoint report.

Purpose: Derive observed workflow-creation-to-job-start delays and whole-job durations
(including setup/post steps) for PRs #5665, #5677, #5678, #5709, #5710, and #5711 from
preserved GitHub Actions JSON snapshots, validate <=350 words and zero at-signs before
writing, and write the CI checkpoint report.
Inputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/ci-queue-checkpoint-20261110/ci_main_runs_20261110.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/ci-queue-checkpoint-20261110/ci_large_files_runs_20261110.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/ci-queue-checkpoint-20261110/ci_jobs_42734850581.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/ci-queue-checkpoint-20261110/ci_jobs_42740507255.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/ci-queue-checkpoint-20261110/ci_jobs_42743340595.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/ci-queue-checkpoint-20261110/ci_jobs_42764693028.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/ci-queue-checkpoint-20261110/ci_jobs_42765972713.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/ci-queue-checkpoint-20261110/ci_jobs_42764805517.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/ci-queue-checkpoint-20261110/ci_jobs_42766780586.json
Outputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/ci_queue_checkpoint_2026-11-10.md
  - JSON provenance and verification summary printed to stdout
PRs: #5665, #5677, #5678, #5709, #5710, #5711
Date: 2026-11-10
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/ci-queue-checkpoint-20261110"
)
MAIN_RUNS_PATH = CACHE_DIR / "ci_main_runs_20261110.json"
LARGE_RUNS_PATH = CACHE_DIR / "ci_large_files_runs_20261110.json"
REPORT_PATH = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/ci_queue_checkpoint_2026-11-10.md"
)

TARGET_RUNS = [
    (5678, "0e28ab54d", "42734850581", "42734850323"),
    (5677, "c135e916b", "42740507255", "42740506996"),
    (5710, "db9295538", "42743340595", "42743339893"),
    (5709, "807417fc2", "42764693028", "42764693016"),
    (5665, "2a5db4ac5", "42765972713", "42765972668"),
    (5711, "c22a08538", "42764805517", "42764805439"),
    (5711, "3ae8bd672", "42766780586", "42766780319"),
]


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_runner_started(job: dict) -> bool:
    """Return True only when a job was assigned a runner and created execution steps."""
    return (
        job.get("status") != "queued"
        and int(job.get("runner_id") or 0) > 0
        and bool(job.get("steps"))
    )


def analyze_run(
    pr_num: int,
    head_short: str,
    main_run_id: str,
    large_run_id: str,
    main_runs: dict[str, dict],
    large_runs: dict[str, dict],
) -> dict[str, object]:
    run_obj = main_runs[main_run_id]
    large_obj = large_runs[large_run_id]
    jobs_payload = json.loads((CACHE_DIR / f"ci_jobs_{main_run_id}.json").read_text())
    jobs = jobs_payload.get("jobs", [])

    run_created = parse_ts(run_obj["created_at"])
    test_jobs = [j for j in jobs if j["name"] not in ("schema-examples", "test")]
    gate_jobs = [j for j in jobs if j["name"] == "test"]

    start_delays: list[int] = []
    whole_job_durations: list[int] = []
    started_timestamps: list[str] = []
    completed_timestamps: list[str] = []
    status_counts: dict[str, int] = {}
    cancelled_started = 0
    cancelled_unstarted = 0

    for job in test_jobs:
        status_key = job["status"] + (
            f"/{job['conclusion']}" if job.get("conclusion") else ""
        )
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
        j_started = parse_ts(job.get("started_at"))
        j_completed = parse_ts(job.get("completed_at"))
        started_on_runner = is_runner_started(job)

        if job.get("conclusion") == "cancelled":
            if started_on_runner:
                cancelled_started += 1
            else:
                cancelled_unstarted += 1

        if j_started and run_created and started_on_runner:
            start_delays.append(int((j_started - run_created).total_seconds()))
            started_timestamps.append(job["started_at"])
        if j_started and j_completed and job.get("conclusion") == "success":
            whole_job_durations.append(int((j_completed - j_started).total_seconds()))
            completed_timestamps.append(job["completed_at"])

    large_created = parse_ts(large_obj["created_at"])
    large_updated = parse_ts(large_obj["updated_at"])
    large_elapsed_s = (
        int((large_updated - large_created).total_seconds())
        if (large_created and large_updated)
        else None
    )

    return {
        "pr": pr_num,
        "head": head_short,
        "main_run_id": main_run_id,
        "main_url": run_obj["html_url"],
        "main_status": run_obj["status"],
        "main_conclusion": run_obj["conclusion"],
        "created_at": run_obj["created_at"],
        "updated_at": run_obj["updated_at"],
        "total_jobs_registered": len(jobs),
        "test_jobs_registered": len(test_jobs),
        "runner_started_jobs": len(start_delays),
        "cancelled_started": cancelled_started,
        "cancelled_unstarted": cancelled_unstarted,
        "status_counts": status_counts,
        "start_delay_min_s": min(start_delays) if start_delays else None,
        "start_delay_max_s": max(start_delays) if start_delays else None,
        "first_started_at": min(started_timestamps) if started_timestamps else None,
        "last_started_at": max(started_timestamps) if started_timestamps else None,
        "whole_job_min_s": min(whole_job_durations) if whole_job_durations else None,
        "whole_job_max_s": max(whole_job_durations) if whole_job_durations else None,
        "last_completed_at": max(completed_timestamps) if completed_timestamps else None,
        "gate_job_status": gate_jobs[0]["status"] if gate_jobs else None,
        "gate_job_created_at": gate_jobs[0]["created_at"] if gate_jobs else None,
        "large_run_id": large_run_id,
        "large_url": large_obj["html_url"],
        "large_conclusion": large_obj["conclusion"],
        "large_elapsed_s": large_elapsed_s,
    }


def render_report(metrics: list[dict[str, object]]) -> str:
    by_key = {(m["pr"], m["head"]): m for m in metrics}
    m5678 = by_key[(5678, "0e28ab54d")]
    m5677 = by_key[(5677, "c135e916b")]
    m5710 = by_key[(5710, "db9295538")]
    m5709 = by_key[(5709, "807417fc2")]
    m5665 = by_key[(5665, "2a5db4ac5")]
    m5711_prev = by_key[(5711, "c22a08538")]
    m5711_curr = by_key[(5711, "3ae8bd672")]

    lines = [
        "# CI Queue vs. Execution Checkpoint (2026-11-10)",
        "",
        "Historical snapshot (`2026-11-10T06:18:34Z`) from `.temp/ci-queue-checkpoint-20261110/` via `scripts/adhoc/analyze_ci_queue_checkpoint_20261110.py`.",
        "",
        "## 1. Trigger & Concurrency",
        "- `main.yaml:1-30,83-381` runs on unfiltered `pull_request` (`#1361`), spawning **18 `ubuntu-latest` test jobs** plus skipped `schema-examples` and final `test` (`if: always()`). `large-files.yaml:1-15` adds `1` job (`20` jobs/push).",
        "- `concurrency` (`main.yaml:16-18`) cancels superseded runs only within the same PR (`Build and test data_sheets_schema-<pr>`). Cross-PR contention (~20 concurrent jobs inferred from active counts, not observed cap) delays starts.",
        "",
        "## 2. Workflow-Creation-to-Job-Start vs. Whole-Job Duration (`main.yaml`)",
        "Start delay is `job.started_at - run.created_at` for runner-assigned jobs (`runner_id > 0`, non-empty `steps`); whole-job duration is `job.completed_at - job.started_at` (including setup/checkout/post steps).",
        "",
        "|PR (`head`)|Run & `06:18Z` State|Created|Start Delay|Whole-Job Duration|",
        "|---|---|---|---|---|",
        f"|`#5678` (`0e28ab54d`)|[{m5678['main_run_id']}]({m5678['main_url']}) `success`|`{m5678['created_at'][11:]}`|`{m5678['start_delay_min_s']}–{m5678['start_delay_max_s']}s` (`{m5678['first_started_at'][11:]}–{m5678['last_started_at'][11:]}`)|`{m5678['whole_job_min_s']}–{m5678['whole_job_max_s']}s` (done `{m5678['updated_at'][11:]}`)|",
        f"|`#5677` (`c135e916b`)|[{m5677['main_run_id']}]({m5677['main_url']}) `success`|`{m5677['created_at'][11:]}`|`{m5677['start_delay_min_s']}–{m5677['start_delay_max_s']}s` (last `{m5677['last_started_at'][11:]}`)|`{m5677['whole_job_min_s']}–{m5677['whole_job_max_s']}s` (done `{m5677['updated_at'][11:]}`)|",
        f"|`#5710` (`db9295538`)|[{m5710['main_run_id']}]({m5710['main_url']}) `success`|`{m5710['created_at'][11:]}`|`{m5710['start_delay_min_s']}–{m5710['start_delay_max_s']}s` (last `{m5710['last_started_at'][11:]}`)|`{m5710['whole_job_min_s']}–{m5710['whole_job_max_s']}s` (done `{m5710['updated_at'][11:]}`)|",
        f"|`#5709` (`807417fc2`)|[{m5709['main_run_id']}]({m5709['main_url']}) `in_progress` (`13/18` done)|`{m5709['created_at'][11:]}`|`{m5709['start_delay_min_s']}–{m5709['start_delay_max_s']}s` (`{m5709['first_started_at'][11:]}–{m5709['last_started_at'][11:]}`)|`{m5709['whole_job_min_s']}–{m5709['whole_job_max_s']}s` (`13` done `{m5709['last_completed_at'][11:]}`; `5` running)|",
        f"|`#5665` (`2a5db4ac5`)|[{m5665['main_run_id']}]({m5665['main_url']}) `queued` (`1` done, `15` running, `2` queued)|`{m5665['created_at'][11:]}`|`{m5665['start_delay_min_s']}–{m5665['start_delay_max_s']}s` (`16` started `{m5665['first_started_at'][11:]}–{m5665['last_started_at'][11:]}`; `2` unstarted `>885s`)|`{m5665['whole_job_min_s']}s` (`1` done `06:14:04Z`; `17` incomplete)|",
        f"|`#5711` (`c22a08538`)|[{m5711_prev['main_run_id']}]({m5711_prev['main_url']}) `queued` (`3` done, `15` cancelled: `11` started + `4` unstarted; `test` queued)|`{m5711_prev['created_at'][11:]}`|`{m5711_prev['start_delay_min_s']}–{m5711_prev['start_delay_max_s']}s` (`14` started `{m5711_prev['first_started_at'][11:]}–{m5711_prev['last_started_at'][11:]}`)|`{m5711_prev['whole_job_min_s']}–{m5711_prev['whole_job_max_s']}s` (`3` done; `15` cancelled `06:10:56–06:11:14Z`)|",
        f"|`#5711` (`3ae8bd672`)|[{m5711_curr['main_run_id']}]({m5711_curr['main_url']}) `pending` (`0` jobs at `06:18Z`; large-files [{m5711_curr['large_run_id']}]({m5711_curr['large_url']}) `{m5711_curr['large_elapsed_s']}s`)|`{m5711_curr['created_at'][11:]}`|Unavailable at `06:18Z` (`>459s`)|Unavailable at `06:18Z` (later root readback: `2` running/`16` queued)|",
        "",
        "## 3. Docs-Only `3ae8bd672`, Uncertainty & Recommendation",
        "- **Full suite triggered**: Yes (`42766780586` at `06:10:55Z`). Inferred mechanism: it cancelled `42764805517` (`11` running, `4` unstarted), freeing runners for `#5665`, while `42764805517`'s `test` job (`06:11:14Z`) held the `#5711` concurrency lock until a runner cleared it.",
        "- **Uncertainty**: Unstarted/queued jobs report placeholder timestamps (`started_at == created_at`, `runner_id == 0`); `#5709`, `#5665`, and `#5711` remain incomplete.",
        "- **Recommendation**: Batch non-urgent checkpoint pushes on docs PR `#5711` while code PRs (`#5665`, `#5709`) run CI.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    main_runs = {
        str(r["id"]): r
        for r in json.loads(MAIN_RUNS_PATH.read_text()).get("workflow_runs", [])
    }
    large_runs = {
        str(r["id"]): r
        for r in json.loads(LARGE_RUNS_PATH.read_text()).get("workflow_runs", [])
    }

    metrics = [
        analyze_run(pr, head, m_id, l_id, main_runs, large_runs)
        for pr, head, m_id, l_id in TARGET_RUNS
    ]
    report_text = render_report(metrics)
    word_count = len(report_text.split())
    report_at_count = report_text.count(chr(64))
    script_bytes = Path(__file__).read_bytes()
    script_at_count = script_bytes.decode("utf-8").count(chr(64))

    assert word_count <= 350, f"Report exceeds 350 words: {word_count}"
    assert report_at_count == 0, "Report contains chr(64)"
    assert script_at_count == 0, "Script contains chr(64)"

    REPORT_PATH.write_text(report_text, encoding="utf-8")
    report_bytes = REPORT_PATH.read_bytes()

    summary = {
        "report_path": str(REPORT_PATH),
        "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "report_word_count": word_count,
        "report_at_count": report_at_count,
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": hashlib.sha256(script_bytes).hexdigest(),
        "script_at_count": script_at_count,
        "runs": metrics,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
