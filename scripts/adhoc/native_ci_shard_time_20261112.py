#!/usr/bin/env python3
"""Purpose: extract per-file and per-shard test execution times from GitHub
Actions CI run 42976790438 on native stack head 1a137b58860416a31618de44173180d021dfcc61,
identify unweighted test files against the weights file named in .github/workflows/
at that commit, explain why shards 5 and 8 timed out at the 45-minute limit, and
predict shard totals using the exact partition code at 1a137b58860416a31618de44173180d021dfcc61
for current, +1, and +2 shards.

Inputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema (Git object store at 1a137b58860416a31618de44173180d021dfcc61)
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/lead-ci-run-42976790438-failures-20261112.json
  - /Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard{1,2,3,4,6,7}/pytest.xml
  - /Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/logs/shard{1..8}.log
  - /Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305.collect.log

Outputs:
  - /Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/pytest_shard_1a137b588604.py (exported partition module outside all worktrees)
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy1-native-ci-shard-time-20261112.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy1-native-ci-shard-time-20261112.md

Serves: owner direction D134; gate G12 of the native critical path; issue 5875.
Date: 2026-11-12.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
from statistics import mean, median
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True

PRIMARY_REPO = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema")
REPORT_WORKTREE = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111"
)
EXTERNAL_RUN_DIR = Path("/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438")
COLLECT_LOG_PATH = Path("/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305.collect.log")
LEAD_FAILURES_JSON = (
    REPORT_WORKTREE
    / "notes/development_efficiency_20261111/handoffs/lead-ci-run-42976790438-failures-20261112.json"
)
EXPORTED_SHARD_MODULE = EXTERNAL_RUN_DIR / "pytest_shard_1a137b588604.py"

SCRIPT_PATH = REPORT_WORKTREE / "scripts/adhoc/native_ci_shard_time_20261112.py"
OUT_JSON = (
    REPORT_WORKTREE
    / "notes/development_efficiency_20261111/handoffs/agy1-native-ci-shard-time-20261112.json"
)
OUT_MD = (
    REPORT_WORKTREE
    / "notes/development_efficiency_20261111/handoffs/agy1-native-ci-shard-time-20261112.md"
)

RUN_ID = "42976790438"
HEAD_COMMIT = "1a137b58860416a31618de44173180d021dfcc61"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
LOG_LINE_RE = re.compile(r"^(\d{4}-\d\d-\d\dT[0-9:.]+Z)\s+(.*)$")
RESULT_RE = re.compile(
    r"\[(gw\d+)\]\s+\[\s*(\d+)%\]\s+(PASSED|SKIPPED|FAILED|ERROR|XFAIL|XPASS)\s+(tests/.*)"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_show_bytes(rev_spec: str) -> bytes:
    env = {
        **os.environ,
        "PATH": "/usr/bin:/bin",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    return subprocess.check_output(
        ["/usr/bin/git", "-C", str(PRIMARY_REPO), "show", rev_spec],
        env=env,
    )


def git_ls_tree_names(commit: str, prefix: str) -> list[str]:
    env = {
        **os.environ,
        "PATH": "/usr/bin:/bin",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    out = subprocess.check_output(
        ["/usr/bin/git", "-C", str(PRIMARY_REPO), "ls-tree", "-r", "--name-only", commit, prefix],
        env=env,
    ).decode("utf-8")
    return [line.strip() for line in out.splitlines() if line.strip()]


def load_partition_module_outside_worktrees():
    raw_bytes = git_show_bytes(f"{HEAD_COMMIT}:utils/pytest_shard.py")
    EXPORTED_SHARD_MODULE.parent.mkdir(parents=True, exist_ok=True)
    EXPORTED_SHARD_MODULE.write_bytes(raw_bytes)
    spec = importlib.util.spec_from_file_location("pytest_shard_1a137b588604", EXPORTED_SHARD_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load spec from {EXPORTED_SHARD_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, sha256_bytes(raw_bytes)


def classname_to_file(classname: str, name: str, test_files_set: set[str]) -> str:
    if not classname:
        cand = name.replace(".", "/") + ".py"
        if cand in test_files_set:
            return cand
    parts = classname.split(".")
    for idx in range(len(parts), 0, -1):
        cand = "/".join(parts[:idx]) + ".py"
        if cand in test_files_set:
            return cand
    raise ValueError(f"Cannot map JUnit testcase classname={classname!r} name={name!r} to test file")


def parse_junit_xml(xml_path: Path, test_files_set: set[str]) -> dict:
    raw = xml_path.read_bytes()
    root = ET.fromstring(raw)
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        raise RuntimeError(f"Missing testsuite in {xml_path}")
    suite_wall_seconds = float(suite.attrib.get("time", "0"))
    file_seconds: dict[str, float] = defaultdict(float)
    file_cases: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    collection_error_files: list[str] = []
    total_cases = 0
    for tc in root.iter("testcase"):
        classname = tc.attrib.get("classname", "")
        name = tc.attrib.get("name", "")
        duration = float(tc.attrib.get("time", "0"))
        mapped = classname_to_file(classname, name, test_files_set)
        if not classname and mapped == "tests/test_native_u3c_test_driver.py":
            collection_error_files.append(mapped)
            continue
        total_cases += 1
        file_seconds[mapped] += duration
        file_cases[mapped] += 1
        if tc.find("failure") is not None:
            outcomes["failed"] += 1
        elif tc.find("error") is not None:
            outcomes["error"] += 1
        elif tc.find("skipped") is not None:
            outcomes["skipped"] += 1
        else:
            outcomes["passed"] += 1
    return {
        "xml_path": str(xml_path),
        "xml_sha256": sha256_bytes(raw),
        "suite_wall_seconds": round(suite_wall_seconds, 3),
        "total_cases_excluding_collection_error": total_cases,
        "collection_error_files": collection_error_files,
        "outcomes": dict(outcomes),
        "file_seconds": {k: round(v, 6) for k, v in sorted(file_seconds.items())},
        "file_cases": dict(sorted(file_cases.items())),
        "sum_case_seconds": round(sum(file_seconds.values()), 3),
    }


def parse_job_log(log_path: Path) -> dict:
    raw_bytes = log_path.read_bytes()
    lines = raw_bytes.decode("utf-8", errors="replace").splitlines()
    first_ts = session_ts = workers_ts = cancel_ts = last_ts = None
    prev_by_worker: dict[str, datetime] = {}
    last_node_by_worker: dict[str, str] = {}
    file_seconds: dict[str, float] = defaultdict(float)
    file_cases: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    completed_nodes: list[str] = []
    last_pct = 0

    for raw_line in lines:
        clean = ANSI_RE.sub("", raw_line.lstrip("\ufeff"))
        m = LOG_LINE_RE.match(clean)
        if not m:
            continue
        stamp_str, text = m.groups()
        stamp = datetime.fromisoformat(stamp_str.replace("Z", "+00:00"))
        first_ts = first_ts or stamp
        last_ts = stamp
        if "test session starts" in text and session_ts is None:
            session_ts = stamp
        if "created: 4/4 workers" in text and workers_ts is None:
            workers_ts = stamp
        if (
            "The operation was canceled." in text
            or "exceeded the maximum execution time" in text
        ) and cancel_ts is None:
            cancel_ts = stamp
        rm = RESULT_RE.search(text)
        if rm:
            worker, pct_s, outcome, nodeid_raw = rm.groups()
            nodeid = nodeid_raw.rstrip()
            last_pct = int(pct_s)
            begin = prev_by_worker.get(worker, workers_ts or session_ts or first_ts)
            duration = (stamp - begin).total_seconds()
            prev_by_worker[worker] = stamp
            last_node_by_worker[worker] = nodeid
            fpath = nodeid.split("::", 1)[0]
            file_seconds[fpath] += duration
            file_cases[fpath] += 1
            outcomes[outcome.lower()] += 1
            completed_nodes.append(nodeid)

    end_ref = cancel_ts or last_ts
    in_flight_gaps = {}
    for w in sorted(prev_by_worker):
        gap = (end_ref - prev_by_worker[w]).total_seconds() if end_ref else 0.0
        in_flight_gaps[w] = {
            "last_completed_at": prev_by_worker[w].isoformat(),
            "last_completed_nodeid": last_node_by_worker[w],
            "unreported_tail_seconds_to_end": round(gap, 3),
        }

    startup_to_workers = (
        round((workers_ts - first_ts).total_seconds(), 3)
        if (workers_ts and first_ts)
        else None
    )
    session_to_end = (
        round((end_ref - session_ts).total_seconds(), 3)
        if (end_ref and session_ts)
        else None
    )

    return {
        "log_path": str(log_path),
        "log_sha256": sha256_bytes(raw_bytes),
        "job_log_first_timestamp": first_ts.isoformat() if first_ts else None,
        "pytest_session_start": session_ts.isoformat() if session_ts else None,
        "workers_created_timestamp": workers_ts.isoformat() if workers_ts else None,
        "cancelled_timestamp": cancel_ts.isoformat() if cancel_ts else None,
        "startup_to_workers_seconds": startup_to_workers,
        "pytest_session_to_end_seconds": session_to_end,
        "completed_cases": len(completed_nodes),
        "completed_files_count": len(file_seconds),
        "last_reported_percent": last_pct,
        "outcomes": dict(outcomes),
        "sum_completed_worker_interval_seconds": round(sum(file_seconds.values()), 3),
        "sum_unreported_in_flight_worker_tail_seconds": round(
            sum(v["unreported_tail_seconds_to_end"] for v in in_flight_gaps.values()), 3
        ),
        "worker_last_completions": in_flight_gaps,
        "file_seconds": {k: round(v, 6) for k, v in sorted(file_seconds.items())},
        "file_cases": dict(sorted(file_cases.items())),
        "completed_nodes": completed_nodes,
    }


def evaluate_partition(
    shard_module,
    paths: list[str],
    shard_counts: list[int],
    scheduling_weights: dict[str, float],
    reference_measured_weights: dict[str, float],
) -> dict[str, dict]:
    results = {}
    ref_estimates = shard_module._estimates(paths, reference_measured_weights)
    for n_shards in shard_counts:
        assignment = shard_module.balanced_files(paths, n_shards, scheduling_weights)
        sched_estimates = shard_module._estimates(paths, scheduling_weights)
        sched_by_shard = [0.0] * n_shards
        ref_by_shard = [0.0] * n_shards
        counts_by_shard = [0] * n_shards
        heaviest_file_by_shard: list[tuple[str, float]] = [("", 0.0) for _ in range(n_shards)]

        for fpath in paths:
            idx = assignment[fpath] - 1
            counts_by_shard[idx] += 1
            sched_by_shard[idx] += sched_estimates[fpath]
            ref_by_shard[idx] += ref_estimates[fpath]
            if ref_estimates[fpath] > heaviest_file_by_shard[idx][1]:
                heaviest_file_by_shard[idx] = (fpath, round(ref_estimates[fpath], 3))

        sched_rounded = [round(x, 3) for x in sched_by_shard]
        ref_rounded = [round(x, 3) for x in ref_by_shard]
        max_sched = max(sched_rounded)
        min_sched = min(sched_rounded)
        max_ref = max(ref_rounded)
        min_ref = min(ref_rounded)
        max_sched_shard = sched_rounded.index(max_sched) + 1
        max_ref_shard = ref_rounded.index(max_ref) + 1

        results[str(n_shards)] = {
            "total_shards": n_shards,
            "file_counts_by_shard": counts_by_shard,
            "predicted_scheduled_totals_seconds": sched_rounded,
            "largest_predicted_scheduled_shard": max_sched_shard,
            "largest_predicted_scheduled_seconds": max_sched,
            "smallest_predicted_scheduled_seconds": min_sched,
            "largest_predicted_scheduled_ideal_4worker_minutes": round(max_sched / 240.0, 2),
            "evaluated_against_all_measured_totals_seconds": ref_rounded,
            "largest_evaluated_measured_shard": max_ref_shard,
            "largest_evaluated_measured_seconds": max_ref,
            "smallest_evaluated_measured_seconds": min_ref,
            "largest_evaluated_measured_ideal_4worker_minutes": round(max_ref / 240.0, 2),
            "heaviest_measured_file_on_largest_evaluated_shard": {
                "file": heaviest_file_by_shard[max_ref_shard - 1][0],
                "seconds": heaviest_file_by_shard[max_ref_shard - 1][1],
            },
        }
    return results


def main() -> int:
    shard_module, shard_module_sha256 = load_partition_module_outside_worktrees()

    workflow_bytes = git_show_bytes(f"{HEAD_COMMIT}:.github/workflows/main.yaml")
    workflow_text = workflow_bytes.decode("utf-8")
    workflow_sha256 = sha256_bytes(workflow_bytes)

    m_timings = re.search(r"--ci-shard-timings=(\S+)", workflow_text)
    if not m_timings:
        raise RuntimeError("Could not find --ci-shard-timings in .github/workflows/main.yaml")
    weights_rel_path = m_timings.group(1)

    weights_bytes = git_show_bytes(f"{HEAD_COMMIT}:{weights_rel_path}")
    weights_sha256 = sha256_bytes(weights_bytes)
    weights_doc = json.loads(weights_bytes.decode("utf-8"))
    committed_weights: dict[str, float] = weights_doc["file_seconds"]

    all_tests_tree = git_ls_tree_names(HEAD_COMMIT, "tests")
    git_test_files = sorted(
        f
        for f in all_tests_tree
        if f.endswith(".py")
        and (Path(f).name.startswith("test_") or Path(f).name.endswith("_test.py"))
    )
    git_test_files_set = set(git_test_files)

    # Identify uncollected files in CI run 42976790438:
    # 1. tests/test_renderer.py has 0 test functions/classes
    # 2. tests/test_native_u3c_test_driver.py raises RuntimeError during collection outside d4d-executions
    collected_799 = [
        f
        for f in git_test_files
        if f not in ("tests/test_renderer.py", "tests/test_native_u3c_test_driver.py")
    ]
    collected_800_with_u3c = [f for f in git_test_files if f != "tests/test_renderer.py"]

    actual_assignment_8 = shard_module.balanced_files(collected_799, 8, committed_weights)
    initial_estimates_799 = shard_module._estimates(collected_799, committed_weights)
    known_in_799 = [committed_weights[p] for p in collected_799 if p in committed_weights]
    fallback_median_seconds = round(float(median(known_in_799)), 6)

    # Parse simulated collection nodeids to know exact expected cases on cancelled shards 5 and 8
    dedicated_nodes = set(shard_module.DEDICATED_CASE_LANES.values())
    sim_cases_by_file: dict[str, list[str]] = defaultdict(list)
    for raw_line in COLLECT_LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("tests/") and "::" in line and line not in dedicated_nodes:
            fpath = line.split("::", 1)[0]
            if fpath in git_test_files_set:
                sim_cases_by_file[fpath].append(line)

    lead_failures_doc = json.loads(LEAD_FAILURES_JSON.read_text(encoding="utf-8"))
    lead_jobs_by_name = {j["name"]: j for j in lead_failures_doc["jobs"]}

    junit_by_shard: dict[int, dict] = {}
    log_by_shard: dict[int, dict] = {}
    primary_file_seconds_by_shard: dict[int, dict[str, float]] = {}
    primary_file_cases_by_shard: dict[int, dict[str, int]] = {}
    primary_source_by_shard: dict[int, str] = {}

    for s in range(1, 9):
        log_path = EXTERNAL_RUN_DIR / "logs" / f"shard{s}.log"
        log_by_shard[s] = parse_job_log(log_path)
        xml_path = EXTERNAL_RUN_DIR / f"tests-py3.12-shard{s}" / "pytest.xml"
        if xml_path.exists():
            junit_by_shard[s] = parse_junit_xml(xml_path, git_test_files_set)
            primary_file_seconds_by_shard[s] = junit_by_shard[s]["file_seconds"]
            primary_file_cases_by_shard[s] = junit_by_shard[s]["file_cases"]
            primary_source_by_shard[s] = "junit_xml"
        else:
            primary_file_seconds_by_shard[s] = log_by_shard[s]["file_seconds"]
            primary_file_cases_by_shard[s] = log_by_shard[s]["file_cases"]
            primary_source_by_shard[s] = "job_log_worker_intervals"

    # Verify that every file observed in shard s belongs to actual_assignment_8[file] == s
    for s in range(1, 9):
        for fpath in primary_file_seconds_by_shard[s]:
            if actual_assignment_8.get(fpath) != s:
                raise RuntimeError(
                    f"Shard {s} observed file {fpath} assigned to {actual_assignment_8.get(fpath)}"
                )

    # Merge per-file measured times across all 8 shards
    measured_file_seconds: dict[str, float] = {}
    measured_file_cases: dict[str, int] = {}
    measured_file_source: dict[str, str] = {}
    for s in range(1, 9):
        for fpath, secs in primary_file_seconds_by_shard[s].items():
            measured_file_seconds[fpath] = round(secs, 6)
            measured_file_cases[fpath] = primary_file_cases_by_shard[s][fpath]
            measured_file_source[fpath] = f"shard{s}:{primary_source_by_shard[s]}"

    # Detailed availability analysis for cancelled shards 5 and 8
    cancelled_shards_detail = {}
    for s in (5, 8):
        assigned_files = sorted(f for f, sh in actual_assignment_8.items() if sh == s)
        expected_nodes = [n for f in assigned_files for n in sim_cases_by_file[f]]
        done_nodes = log_by_shard[s]["completed_nodes"]
        rem_counter = Counter(expected_nodes) - Counter(done_nodes)
        unfinished_nodes = list(rem_counter.elements())
        unfinished_by_file = Counter(n.split("::", 1)[0] for n in unfinished_nodes)

        fully_completed_files = []
        partially_completed_files = []
        unstarted_files = []
        for f in assigned_files:
            done_c = primary_file_cases_by_shard[s].get(f, 0)
            exp_c = len(sim_cases_by_file[f])
            if done_c == 0:
                unstarted_files.append(
                    {
                        "file": f,
                        "expected_cases": exp_c,
                        "committed_weight_seconds": committed_weights.get(f),
                        "scheduled_estimate_seconds": round(initial_estimates_799[f], 3),
                        "is_native": f.startswith("tests/test_native_"),
                    }
                )
            elif done_c < exp_c:
                partially_completed_files.append(
                    {
                        "file": f,
                        "completed_cases": done_c,
                        "expected_cases": exp_c,
                        "unfinished_cases": exp_c - done_c,
                        "measured_completed_seconds": round(primary_file_seconds_by_shard[s][f], 3),
                        "committed_weight_seconds": committed_weights.get(f),
                        "scheduled_estimate_seconds": round(initial_estimates_799[f], 3),
                        "is_native": f.startswith("tests/test_native_"),
                    }
                )
            else:
                fully_completed_files.append(f)

        log_info = dict(log_by_shard[s])
        log_info.pop("completed_nodes", None)
        log_info.pop("file_seconds", None)
        log_info.pop("file_cases", None)

        cancelled_shards_detail[f"shard_{s}"] = {
            "shard": s,
            "job_id": lead_jobs_by_name[f"Python 3.12 / shard {s}"]["id"],
            "job_wall_seconds": lead_jobs_by_name[f"Python 3.12 / shard {s}"]["seconds"],
            "junit_xml_artifact_uploaded": False,
            "what_is_available": (
                f"GitHub Actions job log (logs/shard{s}.log) with microsecond UTC timestamps and "
                f"worker IDs ([gw0]..[gw3]) for all {len(done_nodes)} completed test cases across "
                f"{len(fully_completed_files) + len(partially_completed_files)}/{len(assigned_files)} "
                f"assigned files ({len(fully_completed_files)} fully completed, "
                f"{len(partially_completed_files)} partially completed), plus the last completion "
                f"timestamp per worker before the 45-minute cancellation."
            ),
            "what_is_not_available": (
                f"No JUnit XML artifact (tests-py3.12-shard{s}/pytest.xml was not written before "
                f"cancellation), no pytest --durations=25 summary table, and no CI timing for "
                f"{len(unfinished_nodes)} unfinished test cases ({len(partially_completed_files)} "
                f"partially completed files and {len(unstarted_files)} unstarted files, including "
                f"{sum(1 for x in unstarted_files if x['is_native'])} unstarted unweighted "
                f"tests/test_native_*.py files)."
            ),
            "assigned_files_count": len(assigned_files),
            "expected_cases_count": len(expected_nodes),
            "completed_cases_count": len(done_nodes),
            "unfinished_cases_count": len(unfinished_nodes),
            "fully_completed_files_count": len(fully_completed_files),
            "partially_completed_files": partially_completed_files,
            "unstarted_files_count": len(unstarted_files),
            "unstarted_weighted_files_count": sum(
                1 for x in unstarted_files if x["committed_weight_seconds"] is not None
            ),
            "unstarted_weighted_files_committed_weight_sum_seconds": round(
                sum(
                    x["committed_weight_seconds"]
                    for x in unstarted_files
                    if x["committed_weight_seconds"] is not None
                ),
                3,
            ),
            "unstarted_unweighted_files": [
                x for x in unstarted_files if x["committed_weight_seconds"] is None
            ],
            "unfinished_cases_sample": unfinished_nodes[:25],
            "log_timing_summary": log_info,
        }

    # Section 2: Unweighted files inventory
    unweighted_all = sorted(f for f in git_test_files if f not in committed_weights)
    unweighted_native_files = [f for f in unweighted_all if f.startswith("tests/test_native_")]
    unweighted_other_files = [f for f in unweighted_all if not f.startswith("tests/test_native_")]
    weighted_native_files = sorted(
        f for f in git_test_files if f in committed_weights and "native" in f
    )

    unweighted_native_records = []
    for f in unweighted_native_files:
        shard_num = actual_assignment_8.get(f)
        meas = measured_file_seconds.get(f)
        done_c = measured_file_cases.get(f, 0)
        exp_c = len(sim_cases_by_file.get(f, []))
        if f == "tests/test_native_u3c_test_driver.py":
            status = "collection_error_all_shards"
        elif meas is None:
            status = f"unstarted_on_cancelled_shard_{shard_num}"
        elif shard_num in (5, 8) and done_c < exp_c:
            status = f"partial_on_cancelled_shard_{shard_num} ({done_c}/{exp_c} cases)"
        else:
            status = "measured_complete"
        unweighted_native_records.append(
            {
                "file": f,
                "assigned_shard": shard_num,
                "status": status,
                "completed_cases": done_c,
                "expected_cases": exp_c,
                "scheduled_fallback_seconds": fallback_median_seconds if shard_num else None,
                "measured_seconds": round(meas, 3) if meas is not None else None,
                "measurement_source": measured_file_source.get(f),
            }
        )

    unweighted_other_records = []
    for f in unweighted_other_files:
        shard_num = actual_assignment_8.get(f)
        meas = measured_file_seconds.get(f)
        done_c = measured_file_cases.get(f, 0)
        exp_c = len(sim_cases_by_file.get(f, []))
        status = (
            "zero_tests_not_collected"
            if f == "tests/test_renderer.py"
            else (
                f"unstarted_on_cancelled_shard_{shard_num}"
                if meas is None
                else "measured_complete"
            )
        )
        unweighted_other_records.append(
            {
                "file": f,
                "assigned_shard": shard_num,
                "status": status,
                "completed_cases": done_c,
                "expected_cases": exp_c,
                "scheduled_fallback_seconds": fallback_median_seconds if shard_num else None,
                "measured_seconds": round(meas, 3) if meas is not None else None,
                "measurement_source": measured_file_source.get(f),
            }
        )

    weighted_native_records = []
    for f in weighted_native_files:
        shard_num = actual_assignment_8.get(f)
        meas = measured_file_seconds.get(f)
        old_w = committed_weights[f]
        weighted_native_records.append(
            {
                "file": f,
                "assigned_shard": shard_num,
                "committed_weight_seconds": old_w,
                "measured_seconds": round(meas, 3) if meas is not None else None,
                "delta_seconds": round(meas - old_w, 3) if meas is not None else None,
                "measurement_source": measured_file_source.get(f),
            }
        )

    # Section 3: Per-shard breakdown (1..8): measured total, native sum, 10 slowest files
    per_shard_breakdown = []
    for s in range(1, 9):
        job_entry = lead_jobs_by_name[f"Python 3.12 / shard {s}"]
        assigned_s = sorted(f for f, sh in actual_assignment_8.items() if sh == s)
        f_secs = primary_file_seconds_by_shard[s]
        f_cases = primary_file_cases_by_shard[s]

        scheduled_total = round(sum(initial_estimates_799[f] for f in assigned_s), 3)
        measured_total = round(sum(f_secs.values()), 3)
        native_all_sum = round(
            sum(v for k, v in f_secs.items() if k.startswith("tests/test_native_")), 3
        )
        native_unweighted_sum = round(
            sum(
                v
                for k, v in f_secs.items()
                if k.startswith("tests/test_native_") and k not in committed_weights
            ),
            3,
        )
        native_weighted_sum = round(
            sum(
                v
                for k, v in f_secs.items()
                if k.startswith("tests/test_native_") and k in committed_weights
            ),
            3,
        )
        unweighted_all_sum = round(
            sum(v for k, v in f_secs.items() if k not in committed_weights), 3
        )

        slowest_10 = []
        for rank, (fpath, secs) in enumerate(
            sorted(f_secs.items(), key=lambda kv: (-kv[1], kv[0]))[:10], 1
        ):
            old_w = committed_weights.get(fpath)
            eff_w = round(initial_estimates_799[fpath], 3)
            slowest_10.append(
                {
                    "rank": rank,
                    "file": fpath,
                    "measured_seconds": round(secs, 3),
                    "completed_cases": f_cases.get(fpath, 0),
                    "expected_cases": len(sim_cases_by_file.get(fpath, [])),
                    "committed_weight_seconds": old_w,
                    "scheduled_estimate_seconds": eff_w,
                    "delta_vs_scheduled_seconds": round(secs - eff_w, 3),
                    "is_native": fpath.startswith("tests/test_native_"),
                    "had_weight": old_w is not None,
                }
            )

        per_shard_breakdown.append(
            {
                "shard": s,
                "job_id": job_entry["id"],
                "conclusion": job_entry["conclusion"],
                "job_wall_seconds": job_entry["seconds"],
                "job_wall_minutes": round(job_entry["seconds"] / 60.0, 2),
                "pytest_suite_wall_seconds": (
                    junit_by_shard[s]["suite_wall_seconds"]
                    if s in junit_by_shard
                    else log_by_shard[s]["pytest_session_to_end_seconds"]
                ),
                "measurement_source": primary_source_by_shard[s],
                "assigned_files_count": len(assigned_s),
                "files_with_completed_cases_count": len(f_secs),
                "Assigned_native_files_count": sum(
                    1 for f in assigned_s if f.startswith("tests/test_native_")
                ),
                "Assigned_unweighted_native_files_count": sum(
                    1
                    for f in assigned_s
                    if f.startswith("tests/test_native_") and f not in committed_weights
                ),
                "measured_Native_files_count": sum(
                    1 for f in f_secs if f.startswith("tests/test_native_")
                ),
                "scheduled_case_seconds_total": scheduled_total,
                "measured_case_seconds_total": measured_total,
                "measured_minus_scheduled_seconds": round(measured_total - scheduled_total, 3),
                "log_worker_interval_seconds_total": log_by_shard[s][
                    "sum_completed_worker_interval_seconds"
                ],
                "measured_native_files_seconds": native_all_sum,
                "measured_unweighted_native_files_seconds": native_unweighted_sum,
                "measured_weighted_native_files_seconds": native_weighted_sum,
                "measured_all_unweighted_files_seconds": unweighted_all_sum,
                "ten_slowest_files": slowest_10,
            }
        )

    # Section 4: Partition predictions for current, +1, and +2 shards
    # Floor at 0.001s as required by utils/pytest_shard.py read_weights / update_ci_shard_timings.py
    measured_floored = {
        f: max(round(v, 3), 0.001) for f, v in measured_file_seconds.items()
    }
    measured_unweighted_native_floored = {
        f: v
        for f, v in measured_floored.items()
        if f not in committed_weights and f.startswith("tests/test_native_")
    }
    measured_all_native_floored = {
        f: v for f, v in measured_floored.items() if f.startswith("tests/test_native_")
    }
    measured_all_unweighted_floored = {
        f: v for f, v in measured_floored.items() if f not in committed_weights
    }

    mean_unweighted_native = round(
        float(mean(measured_unweighted_native_floored.values())), 3
    )
    median_unweighted_native = round(
        float(median(measured_unweighted_native_floored.values())), 3
    )

    weights_model_0_original = dict(committed_weights)
    weights_model_1_add_unweighted_native = {
        **committed_weights,
        **measured_unweighted_native_floored,
    }
    weights_model_2_update_all_native = {
        **committed_weights,
        **measured_all_native_floored,
    }
    weights_model_3_add_all_unweighted = {
        **committed_weights,
        **measured_all_unweighted_floored,
    }
    weights_model_4_update_all_measured = {
        **committed_weights,
        **measured_floored,
    }
    # Model 5: Model 4 + impute the 15 unrun Shard-8 unweighted native files (and test_historical_eval_pack.py)
    # with the observed mean of the 112 measured unweighted native files (105.094s)
    unmeasured_collected_unweighted = {
        f: mean_unweighted_native
        for f in collected_799
        if f not in committed_weights and f not in measured_floored
    }
    weights_model_5_update_all_plus_mean_unrun_native = {
        **weights_model_4_update_all_measured,
        **unmeasured_collected_unweighted,
    }

    shard_counts_to_check = [6, 7, 8, 9, 10]
    predictions = {
        "collected_files_count": len(collected_799),
        "pr_shard_counts": {
            "current": 8,
            "plus_one": 9,
            "plus_two": 10,
            "timeout_minutes": 45,
            "timeout_seconds": 2700,
        },
        "main_shard_counts": {
            "current": 6,
            "plus_one": 7,
            "plus_two": 8,
            "timeout_minutes": 60,
            "timeout_seconds": 3600,
        },
        "models": {
            "0_committed_weights_at_1a137b588604": {
                "description": (
                    "Unchanged utils/ci_test_durations.json at 1a137b58860416a31618de44173180d021dfcc61 "
                    "(661 keys; 127 collected native files and 14 non-native files use 1.622s median fallback)."
                ),
                "by_shard_count": evaluate_partition(
                    shard_module,
                    collected_799,
                    shard_counts_to_check,
                    weights_model_0_original,
                    weights_model_4_update_all_measured,
                ),
            },
            "1_add_112_measured_unweighted_native_files": {
                "description": (
                    "Add the 112 unweighted tests/test_native_*.py files measured in run 42976790438 "
                    "(11,770.535s total) to committed weights; keep all 661 existing weights unchanged."
                ),
                "by_shard_count": evaluate_partition(
                    shard_module,
                    collected_799,
                    shard_counts_to_check,
                    weights_model_1_add_unweighted_native,
                    weights_model_4_update_all_measured,
                ),
            },
            "2_update_all_134_measured_native_files": {
                "description": (
                    "Add the 112 measured unweighted tests/test_native_*.py files and update the 22 "
                    "already-weighted tests/test_native_*.py files that ran in 42976790438; keep non-native weights unchanged."
                ),
                "by_shard_count": evaluate_partition(
                    shard_module,
                    collected_799,
                    shard_counts_to_check,
                    weights_model_2_update_all_native,
                    weights_model_4_update_all_measured,
                ),
            },
            "3_add_all_125_measured_unweighted_files": {
                "description": (
                    "Add all 125 previously unweighted files measured in run 42976790438 "
                    "(112 native + 13 non-native, 12,479.811s total) to committed weights; keep 661 existing weights unchanged."
                ),
                "by_shard_count": evaluate_partition(
                    shard_module,
                    collected_799,
                    shard_counts_to_check,
                    weights_model_3_add_all_unweighted,
                    weights_model_4_update_all_measured,
                ),
            },
            "4_update_all_714_measured_files_from_run_42976790438": {
                "description": (
                    "Update all 714 files measured in run 42976790438 (including test_generation_specificity_skill.py "
                    "at 5,918.248s vs 1,148.699s and test_d42_claude_d55.py at 3,352.067s vs 2,184.783s), "
                    "retaining committed weights for the 69 weighted unstarted Shard-8 files."
                ),
                "by_shard_count": evaluate_partition(
                    shard_module,
                    collected_799,
                    shard_counts_to_check,
                    weights_model_4_update_all_measured,
                    weights_model_4_update_all_measured,
                ),
            },
            "5_update_all_714_measured_plus_impute_16_unstarted_unweighted_at_native_mean": {
                "description": (
                    f"Model 4 plus imputing the 16 unstarted Shard-8 unweighted files (15 native + 1 non-native) "
                    f"at the observed mean of the 112 measured unweighted native files ({mean_unweighted_native}s each = "
                    f"{round(16 * mean_unweighted_native, 3)}s added)."
                ),
                "by_shard_count": evaluate_partition(
                    shard_module,
                    collected_799,
                    shard_counts_to_check,
                    weights_model_5_update_all_plus_mean_unrun_native,
                    weights_model_5_update_all_plus_mean_unrun_native,
                ),
            },
        },
    }

    answer_text = (
        "On this one run's evidence (and one run is one measurement), adding only the measured "
        "native test file durations to `utils/ci_test_durations.json` does NOT fit the 45-minute "
        "PR limit on 8 shards (or 9 shards), because `tests/test_generation_specificity_skill.py` "
        "on Shard 8 grew from its 1,148.699s weight to 5,918.248s (and `tests/test_d42_claude_d55.py` "
        "on Shard 5 grew from 2,184.783s to 3,352.067s): if only native weights are added, "
        "balanced_files predicts a largest scheduled shard of 7,518.450s (8 shards), 6,683.063s "
        "(9 shards), and 6,014.757s (10 shards), but packs ~6,370s of other files onto the "
        "`tests/test_generation_specificity_skill.py` shard for an actual measured load of 13,861.539s "
        "(57.76 ideal 4-worker min) at 8 shards, 12,062.054s (50.26 min) at 9 shards, and "
        "10,756.118s (44.82 min) at 10 shards. If all 714 files measured in run 42976790438 "
        "(both native and non-native) are updated in the weights, the largest shard drops to "
        "8,253.583s (34.39 ideal 4-worker min, ~37–38 min job wall) at 8 shards, 7,336.518s "
        "(30.57 min) at 9 shards, and 6,602.866s (27.51 min) at 10 shards (or 8,464.084s, "
        "7,523.630s, and 6,771.267s when also imputing the 15 unrun Shard-8 native files at the "
        "105.094s measured native mean) — meaning a full weight refresh (not native-only) can fit "
        "45 minutes at 8 shards with ~6–7 min wall margin, while moving to 9 or 10 PR shards buys "
        "~4–7 min of additional wall-clock headroom."
    )

    payload = {
        "schema_version": 1,
        "date": "2026-11-12",
        "run_id": RUN_ID,
        "head_commit": HEAD_COMMIT,
        "one_run_caveat": "One CI run is one measurement; Shard 5 (99%) and Shard 8 (16%) were cancelled at the 45-minute timeout, so 3 cases on Shard 5 and 3,233 cases (85 unstarted files + 2 partial files) on Shard 8 were not measured in this run.",
        "answer": answer_text,
        "workflow_inspection_at_head": {
            "workflow_file": ".github/workflows/main.yaml",
            "workflow_sha256": workflow_sha256,
            "weights_file": weights_rel_path,
            "weights_sha256": weights_sha256,
            "partition_module": "utils/pytest_shard.py",
            "partition_module_sha256": shard_module_sha256,
            "exported_partition_module_path": str(EXPORTED_SHARD_MODULE),
            "exported_partition_module_sha256": sha256_file(EXPORTED_SHARD_MODULE),
            "pr_shards": 8,
            "main_shards": 6,
            "pr_timeout_minutes": 45,
            "main_timeout_minutes": 60,
            "xdist_args": "-n logical --maxprocesses=4 --dist load --maxschedchunk=1",
        },
        "collection_and_weights_summary": {
            "git_test_files_count": len(git_test_files),
            "zero_test_files_not_collected": ["tests/test_renderer.py"],
            "collection_error_files_in_run_42976790438": ["tests/test_native_u3c_test_driver.py"],
            "collected_files_in_run_42976790438": len(collected_799),
            "committed_weights_entries_count": len(committed_weights),
            "committed_weights_in_collected_799_count": len(known_in_799),
            "retired_committed_weights_entries": sorted(
                set(committed_weights) - git_test_files_set
            ),
            "fallback_median_weight_seconds": fallback_median_seconds,
            "unweighted_test_files_total_count": len(unweighted_all),
            "unweighted_native_test_files_count": len(unweighted_native_files),
            "unweighted_native_measured_count": sum(
                1 for r in unweighted_native_records if r["measured_seconds"] is not None
            ),
            "unweighted_native_unstarted_on_shard8_count": sum(
                1
                for r in unweighted_native_records
                if r["status"].startswith("unstarted_on_cancelled_shard_")
            ),
            "unweighted_native_collection_error_count": 1,
            "unweighted_native_measured_sum_seconds": round(
                sum(
                    r["measured_seconds"]
                    for r in unweighted_native_records
                    if r["measured_seconds"] is not None
                ),
                3,
            ),
            "unweighted_native_measured_mean_seconds": mean_unweighted_native,
            "unweighted_native_measured_median_seconds": median_unweighted_native,
            "unweighted_non_native_test_files_count": len(unweighted_other_files),
            "unweighted_non_native_measured_sum_seconds": round(
                sum(
                    r["measured_seconds"]
                    for r in unweighted_other_records
                    if r["measured_seconds"] is not None
                ),
                3,
            ),
            "weighted_native_test_files_count": len(weighted_native_files),
            "weighted_native_committed_sum_seconds": round(
                sum(r["committed_weight_seconds"] for r in weighted_native_records), 3
            ),
            "weighted_native_measured_sum_seconds": round(
                sum(
                    r["measured_seconds"]
                    for r in weighted_native_records
                    if r["measured_seconds"] is not None
                ),
                3,
            ),
        },
        "cancelled_shards_availability": cancelled_shards_detail,
        "per_shard_breakdown": per_shard_breakdown,
        "unweighted_native_test_files": unweighted_native_records,
        "unweighted_non_native_test_files": unweighted_other_records,
        "weighted_native_test_files": weighted_native_records,
        "partition_predictions": predictions,
        "measured_file_seconds_all_714": {
            f: {
                "shard": actual_assignment_8[f],
                "source": measured_file_source[f],
                "completed_cases": measured_file_cases[f],
                "expected_cases": len(sim_cases_by_file.get(f, [])),
                "committed_weight_seconds": committed_weights.get(f),
                "scheduled_estimate_seconds": round(initial_estimates_799[f], 3),
                "measured_seconds": round(measured_file_seconds[f], 3),
                "is_native": f.startswith("tests/test_native_"),
            }
            for f in sorted(measured_file_seconds)
        },
    }

    json_text = json.dumps(payload, indent=2) + "\n"
    assert chr(64) not in json_text, "JSON output must not contain at-sign"
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json_text, encoding="utf-8")

    md_text = render_markdown(payload)
    assert chr(64) not in md_text, "Markdown output must not contain at-sign"
    sim_root = Path("/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305")
    for token in set(re.findall(r"`([^`\n]+)`", md_text)):
        if "/" in token or token.endswith((".py", ".json", ".md", ".xml", ".yaml", ".log")):
            exists = (
                (Path(token).exists() if token.startswith("/") else False)
                or (REPORT_WORKTREE / token).exists()
                or (sim_root / token).exists()
                or token in git_test_files_set
            )
            if not exists:
                raise RuntimeError(f"Backticked path-like token does not exist: {token!r}")
    OUT_MD.write_text(md_text, encoding="utf-8")

    print(f"Wrote {OUT_JSON} ({OUT_JSON.stat().st_size} bytes)")
    print(f"Wrote {OUT_MD} ({OUT_MD.stat().st_size} bytes)")
    return 0


def render_markdown(data: dict) -> str:
    lines: list[str] = []
    lines.append("# Native CI Shard Time Analysis (`42976790438` at `1a137b58860416a31618de44173180d021dfcc61`)")
    lines.append("")
    lines.append("## Answer")
    lines.append("")
    lines.append(data["answer"])
    lines.append("")
    lines.append(
        "> **Single-run caveat:** One CI run is one measurement. In run `42976790438`, "
        "Python 3.12 shard 5 (99%, 3,106 of 3,109 cases completed) and "
        "Python 3.12 shard 8 (16%, 627 of 3,860 cases completed) were cancelled at the "
        "45-minute job timeout (2,715.0s and 2,717.0s), leaving 3 cases on Shard 5 and "
        "3,233 cases (85 unstarted files + 2 partially completed files) on Shard 8 unmeasured in CI."
    )
    lines.append("")
    lines.append("### Why Shard 5 and Shard 8 Timed Out")
    lines.append("")
    lines.append(
        "1. **Workflow & weights configuration at `1a137b58860416a31618de44173180d021dfcc61`**: "
        "`.github/workflows/main.yaml` invokes `utils/pytest_shard.py` with "
        "8 shards on pull requests (timeout 45 minutes = 2,700s) or 6 shards "
        "on main and manual runs (timeout 60 minutes = 3,600s), reading "
        "`utils/ci_test_durations.json` and running 4 xdist workers "
        "(`-n logical --maxprocesses=4 --dist load --maxschedchunk=1`)."
    )
    lines.append(
        "2. **128 unweighted native test files scheduled at 1.622s fallback**: "
        "Out of 801 test files in `tests/` (799 collected in run `42976790438` after excluding "
        "`tests/test_renderer.py` with 0 test functions and `tests/test_native_u3c_test_driver.py` "
        "which failed at collection), 143 files (141 collected) have no entry in "
        "`utils/ci_test_durations.json`: **128 native files** (`test_native_` prefix) and "
        "**15 non-native files**. `utils/pytest_shard.py` assigns every unweighted file the median "
        "known weight (1.622s). Across the 112 unweighted native files that actually ran, "
        "scheduled weight was 181.664s (112 x 1.622s), whereas their measured time was "
        "**11,770.535s** (64.8x their scheduled fallback)."
    )
    lines.append(
        "3. **Shard 5 (2,715.0s, cancelled at 99%, 3,106 of 3,109 cases completed across 101 of 101 files)**: "
        "Completed worker intervals totaled **9,948.120s** (plus 497.181s of in-flight worker time "
        "between each worker's last completed case and cancellation = 10,445.301s against a "
        "6,097.547s scheduled total, an overrun of **+3,850.573s** completed or **+4,347.754s** "
        "including in-flight tails). Two factors drove the timeout: "
        "(a) **19 unweighted native files** scheduled at 30.818s (19 x 1.622s) "
        "consumed **1,883.059s** of completed worker intervals (led by `tests/test_native_shared_results.py` "
        "at 602.251s + 179.619s in-flight on `gw3`, `tests/test_native_permission_projection_derivation.py` "
        "at 316.250s, and `tests/test_native_generation_frontdoor.py` at 227.033s), and because their "
        "1.622s fallback gave them tiny per-case priorities, "
        "`utils/pytest_shard.py` queued them near the end of the shard; "
        "(b) **weighted files on Shard 5 also grew by +1,796.609s**, led by `tests/test_d42_claude_d55.py` "
        "(3,352.067s vs 2,184.783s weight, +1,167.284s), weighted native file "
        "`tests/test_native_attempt_supervisor.py` (1,120.114s vs 770.845s, +349.269s), and "
        "`tests/test_source_heading_runtime_api.py` (918.268s vs 636.861s, +281.407s)."
    )
    lines.append(
        "4. **Shard 8 (2,717.0s, cancelled at 16%, 627 of 3,860 cases completed across 16 of 101 files)**: "
        "Completed worker intervals totaled **10,229.580s** (plus 211.662s in-flight = 10,441.242s) "
        "across only 16 files. Only **1 unweighted native file** (`tests/test_native_u3d_round9_preparation.py`, "
        "1 case, 45.802s) ran before cancellation; the other **15 unweighted native files** "
        "(741 cases) never started. Shard 8 timed out because **`tests/test_generation_specificity_skill.py`** "
        "(which runs the specificity scanner across the codebase and grew on the native branch) consumed "
        "**5,918.248s** across 366 of 381 completed cases (with `gw0`, `gw1`, `gw2` still running its remaining "
        "15 cases at cancellation) against a recorded weight of **1,148.699s** (**+4,769.549s**, or **5.15x** "
        "its weight), and `tests/test_d69_artifact_completeness.py` consumed 1,545.220s (vs 1,357.606s)."
    )
    lines.append("")

    # Section 1: Data availability & Cancelled Shards
    lines.append("## 1. Measured Time Source & Cancelled Shard Availability (`42976790438`)")
    lines.append("")
    lines.append(
        "- **Downloaded artifacts directory**: `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438`"
    )
    lines.append(
        "- **Completed/failed shards (`1, 2, 3, 4, 6, 7`)**: Uploaded per-shard JUnit XML artifacts "
        "(`/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard1/pytest.xml`, "
        "`/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard2/pytest.xml`, "
        "`/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard3/pytest.xml`, "
        "`/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard4/pytest.xml`, "
        "`/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard6/pytest.xml`, "
        "`/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard7/pytest.xml`) "
        "are present and used as the primary per-file measurement "
        "(summing `<testcase time=\"...\">` per file, matching `utils/update_ci_shard_timings.py`)."
    )
    lines.append(
        "- **Cancelled shards (`5` and `8`)**: No JUnit XML artifact was uploaded because the runner terminated "
        "pytest at the 45-minute timeout before session finish. Per-file times are extracted from the saved "
        "GitHub Actions job logs (`/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/logs/shard5.log` "
        "and `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/logs/shard8.log`) using the repo's "
        "established worker-completion-interval method (elapsed time between consecutive `[gwN]` results on each "
        "of the 4 workers, starting from worker creation)."
    )
    lines.append("")
    lines.append("| Cancelled Shard | Job ID | Job Wall (s) | Assigned Files | Files Started (Full / Partial / Unstarted) | Cases Completed / Expected | Completed Worker-Interval Sum (s) | Unreported In-Flight Worker Tail (s) | Unstarted Weighted Files (Weight Sum) | Unstarted Unweighted Files (`test_native_` / Other) |")
    lines.append("| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |")
    for key in ("shard_5", "shard_8"):
        c = data["cancelled_shards_availability"][key]
        lt = c["log_timing_summary"]
        n_full = c["fully_completed_files_count"]
        n_part = len(c["partially_completed_files"])
        n_unstart = c["unstarted_files_count"]
        unw_nat = sum(1 for x in c["unstarted_unweighted_files"] if x["is_native"])
        unw_oth = len(c["unstarted_unweighted_files"]) - unw_nat
        lines.append(
            f"| Shard {c['shard']} | `{c['job_id']}` | {c['job_wall_seconds']:.1f} | "
            f"{c['assigned_files_count']} | {n_full + n_part} ({n_full} / {n_part} / {n_unstart}) | "
            f"{c['completed_cases_count']} / {c['expected_cases_count']} ({lt['last_reported_percent']}%) | "
            f"{lt['sum_completed_worker_interval_seconds']:.3f} | "
            f"{lt['sum_unreported_in_flight_worker_tail_seconds']:.3f} | "
            f"{c['unstarted_weighted_files_count']} ({c['unstarted_weighted_files_committed_weight_sum_seconds']:.3f}s) | "
            f"{len(c['unstarted_unweighted_files'])} ({unw_nat} / {unw_oth}) |"
        )
    lines.append("")
    lines.append("### Partially Completed Files on Cancelled Shards 5 and 8")
    lines.append("")
    lines.append("| Shard | File | Completed / Expected Cases | Unfinished Cases | Completed Worker-Interval Time (s) | Committed Weight (s) | Scheduled Estimate (s) |")
    lines.append("| ---: | --- | ---: | ---: | ---: | ---: | ---: |")
    for key in ("shard_5", "shard_8"):
        c = data["cancelled_shards_availability"][key]
        for p in c["partially_completed_files"]:
            cw = "none" if p["committed_weight_seconds"] is None else f"{p['committed_weight_seconds']:.3f}"
            lines.append(
                f"| {c['shard']} | `{p['file']}` | {p['completed_cases']} / {p['expected_cases']} | "
                f"{p['unfinished_cases']} | {p['measured_completed_seconds']:.3f} | {cw} | "
                f"{p['scheduled_estimate_seconds']:.3f} |"
            )
    lines.append("")

    lines.append("## 2. Which Files Have No Weight at `1a137b58860416a31618de44173180d021dfcc61`")
    lines.append("")
    cs = data["collection_and_weights_summary"]
    lines.append(
        f"- **Weights file read by `.github/workflows/main.yaml`**: `utils/ci_test_durations.json` "
        f"(SHA-256: `{data['workflow_inspection_at_head']['weights_sha256']}`, `{cs['committed_weights_entries_count']}` entries; "
        f"median fallback across the `{cs['committed_weights_in_collected_799_count']}` weighted collected files = "
        f"**`{cs['fallback_median_weight_seconds']:.3f}s`**)."
    )
    lines.append(
        f"- **Unweighted native test files (`test_native_` prefix)**: **`{cs['unweighted_native_test_files_count']}` files** "
        f"(`{cs['unweighted_native_measured_count']}` ran and measured **`{cs['unweighted_native_measured_sum_seconds']:.3f}s`**, "
        f"mean `{cs['unweighted_native_measured_mean_seconds']:.3f}s`, median `{cs['unweighted_native_measured_median_seconds']:.3f}s`; "
        f"`{cs['unweighted_native_unstarted_on_shard8_count']}` were assigned to cancelled Shard 8 and never started; "
        f"`1` failed at collection across all shards: `tests/test_native_u3c_test_driver.py`)."
    )
    lines.append(
        f"- **Already-weighted native test files**: **`{cs['weighted_native_test_files_count']}` files** "
        f"(committed weight sum `{cs['weighted_native_committed_sum_seconds']:.3f}s`; measured sum in run `42976790438` = "
        f"`{cs['weighted_native_measured_sum_seconds']:.3f}s`)."
    )
    lines.append(
        f"- **Unweighted non-native test files**: **`{cs['unweighted_non_native_test_files_count']}` files** "
        f"(`13` ran and measured `{cs['unweighted_non_native_measured_sum_seconds']:.3f}s`; `tests/test_historical_eval_pack.py` "
        f"was unstarted on Shard 8; `tests/test_renderer.py` has `0` tests)."
    )
    lines.append("")
    lines.append("### All `128` Unweighted Native Test Files, Ordered by Measured Seconds")
    lines.append("")
    lines.append("| # | Native Test File | Shard | Status | Cases (Done / Exp) | Scheduled Fallback (s) | Measured Seconds (s) | Source |")
    lines.append("| ---: | --- | ---: | --- | ---: | ---: | ---: | --- |")
    sorted_unw_native = sorted(
        data["unweighted_native_test_files"],
        key=lambda r: (
            r["measured_seconds"] is None,
            -(r["measured_seconds"] or 0.0),
            r["file"],
        ),
    )
    for idx, r in enumerate(sorted_unw_native, 1):
        sh_str = str(r["assigned_shard"]) if r["assigned_shard"] is not None else "n/a"
        fb_str = f"{r['scheduled_fallback_seconds']:.3f}" if r["scheduled_fallback_seconds"] is not None else "n/a"
        ms_str = f"{r['measured_seconds']:.3f}" if r["measured_seconds"] is not None else "not measured"
        src_str = r["measurement_source"] or "n/a"
        lines.append(
            f"| {idx} | `{r['file']}` | {sh_str} | {r['status']} | "
            f"{r['completed_cases']} / {r['expected_cases']} | {fb_str} | {ms_str} | {src_str} |"
        )
    lines.append("")

    lines.append("### Unweighted Non-Native Test Files (`15` files)")
    lines.append("")
    lines.append("| # | Non-Native Test File | Shard | Status | Cases (Done / Exp) | Scheduled Fallback (s) | Measured Seconds (s) |")
    lines.append("| ---: | --- | ---: | --- | ---: | ---: | ---: |")
    for idx, r in enumerate(
        sorted(
            data["unweighted_non_native_test_files"],
            key=lambda x: (x["measured_seconds"] is None, -(x["measured_seconds"] or 0.0), x["file"]),
        ),
        1,
    ):
        sh_str = str(r["assigned_shard"]) if r["assigned_shard"] is not None else "n/a"
        fb_str = f"{r['scheduled_fallback_seconds']:.3f}" if r["scheduled_fallback_seconds"] is not None else "n/a"
        ms_str = f"{r['measured_seconds']:.3f}" if r["measured_seconds"] is not None else "not measured"
        lines.append(
            f"| {idx} | `{r['file']}` | {sh_str} | {r['status']} | "
            f"{r['completed_cases']} / {r['expected_cases']} | {fb_str} | {ms_str} |"
        )
    lines.append("")

    # Section 3: Where the time went
    lines.append("## 3. Where the Time Went: Per-Shard Totals, Native Sums, and 10 Slowest Files (`1..8`)")
    lines.append("")
    lines.append("| Shard | Conclusion | Job Wall (s / min) | Pytest Wall (s) | Source | Files (Ran / Assigned) | Scheduled Case-Seconds (s) | Measured Case-Seconds Total (s) | Measured All Native `test_native_` (s) | Measured Unweighted Native (s) | Measured Weighted Native (s) |")
    lines.append("| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in data["per_shard_breakdown"]:
        lines.append(
            f"| {row['shard']} | `{row['conclusion']}` | {row['job_wall_seconds']:.1f}s ({row['job_wall_minutes']:.2f}m) | "
            f"{row['pytest_suite_wall_seconds']:.2f}s | `{row['measurement_source']}` | "
            f"{row['files_with_completed_cases_count']} / {row['assigned_files_count']} | "
            f"{row['scheduled_case_seconds_total']:.3f} | **{row['measured_case_seconds_total']:.3f}** | "
            f"**{row['measured_native_files_seconds']:.3f}** | {row['measured_unweighted_native_files_seconds']:.3f} | "
            f"{row['measured_weighted_native_files_seconds']:.3f} |"
        )
    lines.append("")

    for row in data["per_shard_breakdown"]:
        s = row["shard"]
        lines.append(
            f"### Shard {s} — 10 Slowest Files (`{row['conclusion']}`, "
            f"measured total `{row['measured_case_seconds_total']:.3f}s`, "
            f"native sum `{row['measured_native_files_seconds']:.3f}s`)"
        )
        lines.append("")
        lines.append("| Rank | Test File | Measured (s) | Committed Weight (s) | Scheduled (s) | Delta vs Scheduled (s) | Cases (Done / Exp) | Native? |")
        lines.append("| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |")
        for item in row["ten_slowest_files"]:
            cw = (
                "none"
                if item["committed_weight_seconds"] is None
                else f"{item['committed_weight_seconds']:.3f}"
            )
            nat = "yes" if item["is_native"] else "no"
            lines.append(
                f"| {item['rank']} | `{item['file']}` | {item['measured_seconds']:.3f} | "
                f"{cw} | {item['scheduled_estimate_seconds']:.3f} | "
                f"{item['delta_vs_scheduled_seconds']:+.3f} | "
                f"{item['completed_cases']} / {item['expected_cases']} | {nat} |"
            )
        lines.append("")

    # Section 4: What partition would fit
    lines.append("## 4. What Partition Would Fit (`utils/pytest_shard.py` at `1a137b58860416a31618de44173180d021dfcc61`)")
    lines.append("")
    lines.append(
        "- **Partition module**: Imported from `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/pytest_shard_1a137b588604.py` "
        f"(SHA-256: `{data['workflow_inspection_at_head']['exported_partition_module_sha256']}`), exported directly from "
        "commit `1a137b58860416a31618de44173180d021dfcc61` path `utils/pytest_shard.py`."
    )
    lines.append(
        "- **Why two numbers are reported for each shard count**: "
        "`balanced_files(paths, total, weights)` balances the **scheduled weights** it is given. "
        "If only native test durations are added to `utils/ci_test_durations.json` (Models 1–2), "
        "`balanced_files` still sees `tests/test_generation_specificity_skill.py` at its old weight "
        "1,148.699s (instead of its measured 5,918.248s) and `tests/test_d42_claude_d55.py` at "
        "2,184.783s (instead of 3,352.067s), so the shard containing `tests/test_generation_specificity_skill.py` "
        "receives ~6,370s of additional files and actually totals 13,861.539s at 8 shards! "
        "Therefore the table below reports **both** the largest predicted scheduled shard total "
        "(in the model's own weights) **and** the largest shard total when that partition is evaluated "
        "against all 714 measured file durations from run `42976790438`."
    )
    lines.append("")
    lines.append("### Largest Predicted Shard Totals for Current (`8` PR / `6` main), `+1` (`9` PR / `7` main), and `+2` (`10` PR / `8` main) Shards")
    lines.append("")
    lines.append("| Weight Model | Shards | Role | Largest Scheduled Shard (s / ideal 4w min) | Largest Actual Measured Shard (s / ideal 4w min) | Heaviest File on Largest Measured Shard | All Shards Scheduled Totals (s) |")
    lines.append("| --- | ---: | --- | ---: | ---: | --- | --- |")

    role_labels = {
        "6": "main current (6)",
        "7": "main +1 (7)",
        "8": "PR current (8) / main +2 (8)",
        "9": "PR +1 (9)",
        "10": "PR +2 (10)",
    }
    for model_key, model_info in data["partition_predictions"]["models"].items():
        for sc in ("8", "9", "10", "6", "7"):
            row = model_info["by_shard_count"][sc]
            hf = row["heaviest_measured_file_on_largest_evaluated_shard"]
            sched_list = ", ".join(f"{x:.1f}" for x in row["predicted_scheduled_totals_seconds"])
            lines.append(
                f"| `{model_key}` | {sc} | {role_labels[sc]} | "
                f"**{row['largest_predicted_scheduled_seconds']:.3f}s** ({row['largest_predicted_scheduled_ideal_4worker_minutes']:.2f}m, shard {row['largest_predicted_scheduled_shard']}) | "
                f"**{row['largest_evaluated_measured_seconds']:.3f}s** ({row['largest_evaluated_measured_ideal_4worker_minutes']:.2f}m, shard {row['largest_evaluated_measured_shard']}) | "
                f"`{hf['file']}` ({hf['seconds']:.3f}s) | `[{sched_list}]` |"
            )
    lines.append("")

    lines.append("## 5. Reproduction Command")
    lines.append("")
    lines.append("```sh")
    lines.append(
        "PYTHONDONTWRITEBYTECODE=1 python3 "
        "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/native_ci_shard_time_20261112.py"
    )
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
