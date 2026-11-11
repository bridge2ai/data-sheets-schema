#!/usr/bin/env python3
"""Refresh utils/ci_test_durations.json from complete ordinary-shard CI run 42916359440.

Purpose:
  Build refreshed per-file CI scheduling weights from all eight ordinary-shard
  JUnit XML artifacts of GitHub Actions run 42916359440 (commit
  6792947ea6558d10c85106065b023cb57838835a, PR #5808) using the existing
  utils.update_ci_shard_timings.build implementation against the actual run
  checkout root so all 663 collected test files (including the two readiness
  test files added on 6792947ea) map cleanly with zero dropped testcases.
  Compare old vs. new predicted shard assignments against the same measured
  run 42916359440 durations while preserving historical provenance in
  utils/ci_test_durations.json.

Inputs:
  - tmp/run-42916359440/run_metadata.json
  - tmp/run-42916359440/artifacts_roster.json
  - tmp/run-42916359440/artifacts/tests-py3.12-shard{1..8}/pytest.xml
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-generation-readiness-20261110
    (checked out at 6792947ea6558d10c85106065b023cb57838835a)
  - utils/ci_test_durations.json (prior snapshot at 7233f193ad102a8488b31ec7333662c8fefaa996)

Outputs:
  - utils/ci_test_durations.json (updated file_seconds and provenance block)
  - tmp/run-42916359440/refresh_evidence.json (verification and shard comparison)

Serves:
  Work unit E2 (CI timing refresh) and review issue #5809, 2026-11-11.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

WORKTREE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

from utils.pytest_shard import DEDICATED_CASE_LANES, balanced_files
from utils.update_ci_shard_timings import build

RUN_ID = 42916359440
RUN_COMMIT = "6792947ea6558d10c85106065b023cb57838835a"
BASE_MAIN_COMMIT = "7233f193ad102a8488b31ec7333662c8fefaa996"
READINESS_ONLY_FILES = [
    "tests/test_final_generation_acceptance.py",
    "tests/test_final_record_component_limits.py",
]
EXPECTED_ORDINARY_ARTIFACT_IDS = {
    "tests-py3.12-shard1": 13811466815,
    "tests-py3.12-shard2": 13811196151,
    "tests-py3.12-shard3": 13811616484,
    "tests-py3.12-shard4": 13811385881,
    "tests-py3.12-shard5": 13812880450,
    "tests-py3.12-shard6": 13810838458,
    "tests-py3.12-shard7": 13810813307,
    "tests-py3.12-shard8": 13811114126,
}
DEFAULT_READINESS_ROOT = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-generation-readiness-20261110"
)
DEFAULT_SCRATCH_DIR = WORKTREE_ROOT / "tmp" / f"run-{RUN_ID}"
DURATIONS_PATH = WORKTREE_ROOT / "utils" / "ci_test_durations.json"
REFRESH_KEY = "ci_refresh_42916359440_20261111"
METHOD_SUFFIX = (
    " Complete 8-shard ordinary CI refresh (2026-11-11): build active file_seconds from "
    "run 42916359440 at commit 6792947ea6558d10c85106065b023cb57838835a via "
    "utils.update_ci_shard_timings.build against the run checkout root, preserving "
    "prior weights and historical provenance under source.ci_refresh_42916359440_20261111."
)


def _git_head(repo: Path) -> str:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()


def _git_test_files(repo: Path) -> list[str]:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "tests"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.splitlines()
    return sorted(
        path
        for path in out
        if path.endswith(".py")
        and (Path(path).name.startswith("test_") or Path(path).name.endswith("_test.py"))
    )


def _evaluate_partition(
    paths: list[str],
    total_shards: int,
    scheduling_weights: dict[str, float],
    measured_weights: dict[str, float],
) -> dict[str, object]:
    assignment = balanced_files(paths, total_shards, scheduling_weights)
    reverse_assignment = balanced_files(list(reversed(paths)), total_shards, scheduling_weights)
    if assignment != reverse_assignment:
        raise ValueError(f"Order-dependent partition for {total_shards} shards")

    shard_measured_seconds = [Decimal("0")] * total_shards
    shard_scheduled_seconds = [Decimal("0")] * total_shards
    shard_file_counts = [0] * total_shards

    known = sorted(Decimal(str(scheduling_weights[p])) for p in paths if p in scheduling_weights)
    if not known:
        fallback = Decimal("1")
    else:
        mid = len(known) // 2
        fallback = (known[mid - 1] + known[mid]) / Decimal("2") if len(known) % 2 == 0 else known[mid]

    for path in paths:
        shard_idx = assignment[path] - 1
        shard_file_counts[shard_idx] += 1
        shard_measured_seconds[shard_idx] += Decimal(str(measured_weights[path]))
        sched_val = Decimal(str(scheduling_weights[path])) if path in scheduling_weights else fallback
        shard_scheduled_seconds[shard_idx] += sched_val

    measured_floats = [float(val.quantize(Decimal("0.001"))) for val in shard_measured_seconds]
    scheduled_floats = [float(val.quantize(Decimal("0.001"))) for val in shard_scheduled_seconds]
    min_measured = min(measured_floats)
    max_measured = max(measured_floats)
    spread_measured = round(max_measured - min_measured, 3)
    ratio_measured = round(max_measured / min_measured, 6) if min_measured > 0 else None

    return {
        "total_shards": total_shards,
        "collected_files": len(paths),
        "shard_file_counts": shard_file_counts,
        "scheduled_case_seconds_by_shard": scheduled_floats,
        "measured_case_seconds_by_shard": measured_floats,
        "measured_min_case_seconds": min_measured,
        "measured_max_case_seconds": max_measured,
        "measured_spread_case_seconds": spread_measured,
        "measured_max_over_min_ratio": ratio_measured,
        "note": (
            "Scheduling estimates computed from summed JUnit case seconds per shard; "
            "not wall-clock predictions."
        ),
    }


def main() -> None:
    os.environ["GIT_CONFIG_GLOBAL"] = "/dev/null"
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"

    readiness_root = DEFAULT_READINESS_ROOT
    scratch_dir = DEFAULT_SCRATCH_DIR
    artifacts_dir = scratch_dir / "artifacts"

    readiness_head = _git_head(readiness_root)
    if readiness_head != RUN_COMMIT:
        raise RuntimeError(
            f"Expected readiness root {readiness_root} at {RUN_COMMIT}, got {readiness_head}"
        )

    run_meta = json.loads((scratch_dir / "run_metadata.json").read_text())
    if (
        run_meta["id"] != RUN_ID
        or run_meta["head_sha"] != RUN_COMMIT
        or run_meta["status"] != "completed"
        or run_meta["conclusion"] != "success"
    ):
        raise RuntimeError(f"Run metadata verification failed: {run_meta}")

    roster_data = json.loads((scratch_dir / "artifacts_roster.json").read_text())
    roster_by_name = {item["name"]: item for item in roster_data["artifacts"]}
    for name, expected_id in EXPECTED_ORDINARY_ARTIFACT_IDS.items():
        if name not in roster_by_name:
            raise RuntimeError(f"Missing ordinary shard artifact {name} in roster")
        item = roster_by_name[name]
        if (
            item["id"] != expected_id
            or item["expired"]
            or item["workflow_run"]["id"] != RUN_ID
            or item["workflow_run"]["head_sha"] != RUN_COMMIT
        ):
            raise RuntimeError(f"Invalid roster metadata for {name}: {item}")

    built = build(artifacts_dir, readiness_root, run_id=RUN_ID, commit=RUN_COMMIT)
    built_artifacts_by_path = {entry["path"]: entry["sha256"] for entry in built["source"]["artifacts"]}
    if len(built_artifacts_by_path) != 8:
        raise RuntimeError(f"Expected 8 built artifacts, got {len(built_artifacts_by_path)}")

    dedicated_nodeids = set(DEDICATED_CASE_LANES.values())
    shard_summaries = []
    collision_records = []
    total_passed = 0
    total_skipped = 0

    for shard_idx in range(1, 9):
        shard_name = f"tests-py3.12-shard{shard_idx}"
        rel_xml = f"{shard_name}/pytest.xml"
        xml_path = artifacts_dir / rel_xml
        xml_bytes = xml_path.read_bytes()
        xml_sha256 = hashlib.sha256(xml_bytes).hexdigest()
        if built_artifacts_by_path.get(rel_xml) != xml_sha256:
            raise RuntimeError(f"Digest mismatch for {rel_xml}")

        root_el = ET.fromstring(xml_bytes)
        suite = root_el if root_el.tag == "testsuite" else root_el.find("testsuite")
        if suite is None:
            raise RuntimeError(f"Missing testsuite element in {rel_xml}")

        seen_in_shard: Counter[tuple[str, str]] = Counter()
        shard_cases = 0
        shard_skipped = 0
        shard_seconds = Decimal("0")
        for case in root_el.iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                raise RuntimeError(f"Unsuccessful testcase in {rel_xml}")
            shard_cases += 1
            if case.find("skipped") is not None:
                shard_skipped += 1
            classname = case.attrib["classname"]
            name = case.attrib["name"]
            seen_in_shard[(classname, name)] += 1
            shard_seconds += Decimal(case.attrib["time"])

            module_rel = classname.replace(".", "/") + ".py"
            nodeid = f"{module_rel}::{name}"
            if nodeid in dedicated_nodeids:
                raise RuntimeError(f"Dedicated lane case {nodeid} found in ordinary {rel_xml}")

        for (classname, name), count in sorted(seen_in_shard.items()):
            if count > 1:
                collision_records.append(
                    {
                        "shard": shard_name,
                        "classname": classname,
                        "name": name,
                        "occurrences": count,
                    }
                )

        total_passed += shard_cases - shard_skipped
        total_skipped += shard_skipped
        roster_item = roster_by_name[shard_name]
        archive_digest = roster_item["digest"]
        if not archive_digest.startswith("sha256:"):
            raise RuntimeError(f"Unexpected digest format for {shard_name}: {archive_digest}")

        shard_summaries.append(
            {
                "id": roster_item["id"],
                "name": shard_name,
                "path": rel_xml,
                "sha256": xml_sha256,
                "locally_computed_xml_sha256": xml_sha256,
                "locally_computed_xml_size_bytes": len(xml_bytes),
                "api_reported_archive_sha256": archive_digest.removeprefix("sha256:"),
                "api_reported_archive_size_bytes": roster_item["size_in_bytes"],
                "digest_provenance": (
                    "sha256/locally_computed_xml_sha256 is computed locally from extracted pytest.xml bytes; "
                    "api_reported_archive_sha256 is the GitHub Actions API-reported ZIP archive digest."
                ),
                "head_sha": roster_item["workflow_run"]["head_sha"],
                "test_cases": shard_cases,
                "passed": shard_cases - shard_skipped,
                "skipped": shard_skipped,
                "failures": 0,
                "errors": 0,
                "suite_wall_seconds": float(suite.attrib["time"]),
                "summed_case_seconds": float(shard_seconds.quantize(Decimal("0.001"))),
            }
        )

    current_data = json.loads(DURATIONS_PATH.read_text())
    if REFRESH_KEY in current_data.get("source", {}):
        prior_file_seconds = dict(current_data["source"][REFRESH_KEY]["previous_file_seconds"])
    else:
        prior_file_seconds = dict(current_data["file_seconds"])

    new_file_seconds = dict(built["file_seconds"])
    main_test_files = [p for p in _git_test_files(WORKTREE_ROOT) if p in new_file_seconds]
    readiness_test_files = sorted(new_file_seconds)
    uncollected_git_test_files = sorted(set(_git_test_files(readiness_root)) - set(new_file_seconds))
    if sorted(set(readiness_test_files) - set(main_test_files)) != READINESS_ONLY_FILES:
        raise RuntimeError("Readiness checkout vs main checkout file delta mismatch")

    added_files = sorted(set(new_file_seconds) - set(prior_file_seconds))
    newly_timed_main_files = sorted(set(added_files) - set(READINESS_ONLY_FILES))
    removed_files = sorted(set(prior_file_seconds) - set(new_file_seconds))
    expected_retired = sorted(current_data["local_overrides"][1]["retired_modules"])
    if removed_files != expected_retired:
        raise RuntimeError(
            f"Removed files {removed_files} do not match expected retired modules {expected_retired}"
        )

    main_measured_weights = {path: new_file_seconds[path] for path in main_test_files}
    comparisons = {
        "readiness_676_files_8_shards_pr": {
            "old_weights": _evaluate_partition(
                readiness_test_files, 8, prior_file_seconds, new_file_seconds
            ),
            "new_weights": _evaluate_partition(
                readiness_test_files, 8, new_file_seconds, new_file_seconds
            ),
        },
        "readiness_676_files_6_shards_main": {
            "old_weights": _evaluate_partition(
                readiness_test_files, 6, prior_file_seconds, new_file_seconds
            ),
            "new_weights": _evaluate_partition(
                readiness_test_files, 6, new_file_seconds, new_file_seconds
            ),
        },
        "main_674_files_8_shards_pr": {
            "old_weights": _evaluate_partition(
                main_test_files, 8, prior_file_seconds, main_measured_weights
            ),
            "new_weights": _evaluate_partition(
                main_test_files, 8, new_file_seconds, main_measured_weights
            ),
        },
        "main_674_files_6_shards_main": {
            "old_weights": _evaluate_partition(
                main_test_files, 6, prior_file_seconds, main_measured_weights
            ),
            "new_weights": _evaluate_partition(
                main_test_files, 6, new_file_seconds, main_measured_weights
            ),
        },
    }

    weight_deltas = []
    for path in sorted(set(prior_file_seconds) & set(new_file_seconds)):
        before_val = prior_file_seconds[path]
        after_val = new_file_seconds[path]
        delta_val = round(after_val - before_val, 3)
        weight_deltas.append(
            {
                "file": path,
                "before_seconds": before_val,
                "after_seconds": after_val,
                "delta_seconds": delta_val,
            }
        )
    largest_reductions = sorted(weight_deltas, key=lambda row: row["delta_seconds"])[:15]
    largest_increases = sorted(weight_deltas, key=lambda row: row["delta_seconds"], reverse=True)[:15]

    refresh_block = {
        "run_id": RUN_ID,
        "commit": RUN_COMMIT,
        "base_main_commit": BASE_MAIN_COMMIT,
        "pull_request": 5808,
        "status": "completed",
        "conclusion": "success",
        "url": built["source"]["url"],
        "kind": "Complete 8-shard ordinary GitHub Actions Python 3.12 JUnit measurement",
        "method": (
            "utils.update_ci_shard_timings.build(results, root, "
            "run_id=42916359440, commit='6792947ea6558d10c85106065b023cb57838835a') "
            "against run checkout root; sum JUnit case seconds by collected file with 0.001s floor"
        ),
        "test_cases": built["source"]["test_cases"],
        "passed_cases": total_passed,
        "skipped_cases": total_skipped,
        "same_shard_label_collisions": collision_records,
        "readiness_only_files": READINESS_ONLY_FILES,
        "newly_timed_main_files": newly_timed_main_files,
        "retired_prior_files": removed_files,
        "artifacts": shard_summaries,
        "previous_file_seconds": prior_file_seconds,
        "file_seconds": new_file_seconds,
    }

    current_data["source"][REFRESH_KEY] = refresh_block
    if METHOD_SUFFIX not in current_data["method"]:
        current_data["method"] = current_data["method"] + METHOD_SUFFIX
    current_data["file_seconds"] = new_file_seconds

    DURATIONS_PATH.write_text(json.dumps(current_data, indent=2) + "\n")

    prior_total_seconds = round(sum(prior_file_seconds.values()), 3)
    new_total_seconds_all = round(sum(new_file_seconds.values()), 3)
    new_total_seconds_main_674 = round(sum(main_measured_weights.values()), 3)

    evidence = {
        "run_id": RUN_ID,
        "run_commit": RUN_COMMIT,
        "base_main_commit": BASE_MAIN_COMMIT,
        "pull_request": 5808,
        "status": run_meta["status"],
        "conclusion": run_meta["conclusion"],
        "total_test_cases": built["source"]["test_cases"],
        "passed_cases": total_passed,
        "skipped_cases": total_skipped,
        "same_shard_label_collisions": collision_records,
        "prior_file_count": len(prior_file_seconds),
        "new_file_count": len(new_file_seconds),
        "main_file_count": len(main_test_files),
        "uncollected_git_test_files": uncollected_git_test_files,
        "readiness_only_files": {
            path: new_file_seconds[path] for path in READINESS_ONLY_FILES
        },
        "newly_timed_main_files": {
            path: new_file_seconds[path] for path in newly_timed_main_files
        },
        "retired_prior_files": {
            path: prior_file_seconds[path] for path in removed_files
        },
        "prior_total_case_seconds": prior_total_seconds,
        "new_total_case_seconds_676_files": new_total_seconds_all,
        "new_total_case_seconds_674_main_files": new_total_seconds_main_674,
        "total_case_seconds_delta_674_main_files": round(
            new_total_seconds_main_674 - prior_total_seconds, 3
        ),
        "ordinary_shard_artifacts": shard_summaries,
        "partition_comparisons": comparisons,
        "largest_weight_reductions": largest_reductions,
        "largest_weight_increases": largest_increases,
        "updated_durations_sha256": hashlib.sha256(DURATIONS_PATH.read_bytes()).hexdigest(),
    }

    evidence_path = scratch_dir / "refresh_evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": "ok",
                "test_cases": built["source"]["test_cases"],
                "prior_file_count": len(prior_file_seconds),
                "new_file_count": len(new_file_seconds),
                "main_file_count": len(main_test_files),
                "prior_total_case_seconds": prior_total_seconds,
                "new_total_case_seconds_676": new_total_seconds_all,
                "new_total_case_seconds_674": new_total_seconds_main_674,
                "readiness_8shard_old_max_s": comparisons["readiness_676_files_8_shards_pr"][
                    "old_weights"
                ]["measured_max_case_seconds"],
                "readiness_8shard_new_max_s": comparisons["readiness_676_files_8_shards_pr"][
                    "new_weights"
                ]["measured_max_case_seconds"],
                "main_8shard_old_max_s": comparisons["main_674_files_8_shards_pr"]["old_weights"][
                    "measured_max_case_seconds"
                ],
                "main_8shard_new_max_s": comparisons["main_674_files_8_shards_pr"]["new_weights"][
                    "measured_max_case_seconds"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
