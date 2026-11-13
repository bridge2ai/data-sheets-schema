#!/usr/bin/env python3
"""Build JSON and Markdown tables for AGY4 native CI portability handoff.

Purpose: Assemble structured verification records, file SHA-256 digests, diff
summaries, and Part 2 one-change-at-a-time reproduction tables from saved logs
for assignment claude-lead-agy4-native-ci-portability-20261112.md.
Inputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/lead-ci-run-42976790438-failures-20261112.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-agy4-ci-portability-20261112/*.log
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tests/test_native_u3c_round4_helpers.py
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tests/test_native_u3d_runner_evidence.py
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tests/test_native_u5_external_schema.py
Outputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy4-native-ci-portability-20261112.json
  - Markdown tables printed to stdout for inclusion in agy4-native-ci-portability-20261112.md
Assignment: claude-lead-agy4-native-ci-portability-20261112.md (Issue 5875 follow-up)
Date: 2026-11-12
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


WORKTREE = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112"
)
CISIM = Path("/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305")
SCRATCH = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-agy4-ci-portability-20261112"
)
REPORT_ROOT = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111"
)
CI_FAILURES_JSON = (
    REPORT_ROOT
    / "notes/development_efficiency_20261111/handoffs/lead-ci-run-42976790438-failures-20261112.json"
)
OUT_JSON = (
    REPORT_ROOT
    / "notes/development_efficiency_20261111/handoffs/agy4-native-ci-portability-20261112.json"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_payload() -> dict:
    ci_data = json.loads(CI_FAILURES_JSON.read_text(encoding="utf-8"))
    failures = ci_data["failures"]
    origin_failures = [
        row
        for row in failures
        if row["class"]
        == "import origin: native controller dependency imported from another origin"
    ]
    layout_failures = [
        row
        for row in failures
        if row["file"]
        in (
            "tests/test_native_u3c_round4_helpers.py",
            "tests/test_native_u3d_runner_evidence.py",
            "tests/test_native_u5_external_schema.py",
        )
    ]
    origin_by_file = Counter(row["file"] for row in origin_failures)

    edited_files = [
        {
            "relative_path": "tests/test_native_u3c_round4_helpers.py",
            "worktree_path": str(WORKTREE / "tests/test_native_u3c_round4_helpers.py"),
            "cisim_path": str(CISIM / "tests/test_native_u3c_round4_helpers.py"),
            "sha256": sha256_file(WORKTREE / "tests/test_native_u3c_round4_helpers.py"),
            "insertions": 43,
            "deletions": 15,
            "change_summary": (
                "Add _temp_base() and optional root parameter on helper(name, root=ROOT); "
                "in test_parent_worker_and_subprocess_reenter_c4_wrapper(), build a temporary "
                "d4d-executions directory with plans/ and checkout/, copy "
                "run_native_u3c_round4_20261107.py, run_native_u3a_tests_20261107.py, "
                "hydrate_native_u3c_round4_fairscape_20261107.py, and tests/test_native_u3b_reuse.py "
                "into checkout/, load the wrapper from checkout, and run all existing assertions."
            ),
        },
        {
            "relative_path": "tests/test_native_u3d_runner_evidence.py",
            "worktree_path": str(WORKTREE / "tests/test_native_u3d_runner_evidence.py"),
            "cisim_path": str(CISIM / "tests/test_native_u3d_runner_evidence.py"),
            "sha256": sha256_file(WORKTREE / "tests/test_native_u3d_runner_evidence.py"),
            "insertions": 26,
            "deletions": 5,
            "change_summary": (
                "Add _temp_base() and copy scripts/adhoc/run_native_u3d_tests_20261107.py into "
                "a temporary d4d-executions/checkout/scripts/adhoc/ tree outside d4d-executions "
                "before exec_module so len(_executions) == 1 holds regardless of checkout or "
                "--basetemp location; pass GIT_CONFIG_GLOBAL=/dev/null and GIT_CONFIG_SYSTEM=/dev/null "
                "in the test git environment."
            ),
        },
        {
            "relative_path": "tests/test_native_u5_external_schema.py",
            "worktree_path": str(WORKTREE / "tests/test_native_u5_external_schema.py"),
            "cisim_path": str(CISIM / "tests/test_native_u5_external_schema.py"),
            "sha256": sha256_file(WORKTREE / "tests/test_native_u5_external_schema.py"),
            "insertions": 51,
            "deletions": 21,
            "change_summary": (
                "In checked_input(label, expected_commit, *, require_present=False), skip with the "
                "exact missing path when manifest.json or a listed tree file is absent on initial "
                "input check while enforcing require_present=True on post-test integrity re-checks; "
                "in test_api_comparison_refuses_other_scratch_roots, stage a temporary "
                "d4d-executions/checkout/scripts/adhoc/native_u5_api_render_20261108.py and "
                "scratch-native-u5-prep directory under _temp_base() so the test reaches and "
                "verifies the 'named U4b/U5 scratch roots' refusal message on any checkout path."
            ),
        },
    ]

    untouched_scripts = [
        {
            "relative_path": rel,
            "worktree_path": str(WORKTREE / rel),
            "sha256": sha256_file(WORKTREE / rel),
        }
        for rel in (
            "scripts/adhoc/run_native_u3a_tests_20261107.py",
            "scripts/adhoc/run_native_u3c_round4_20261107.py",
            "scripts/adhoc/hydrate_native_u3c_round4_fairscape_20261107.py",
            "scripts/adhoc/census_native_u3c_round4_20261107.py",
            "scripts/adhoc/run_native_u3d_tests_20261107.py",
            "scripts/adhoc/native_u5_api_render_20261108.py",
        )
    ]

    commands = [
        {
            "id": "part1_worktree_target_nodes",
            "part": "Part 1",
            "location": str(WORKTREE),
            "command": (
                f"PYTHONPATH={WORKTREE}/src "
                "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python "
                "-m pytest -v -rs -p no:cacheprovider "
                f"--basetemp {SCRATCH}/part1-worktree-target-nodes "
                f"{WORKTREE}/tests/test_native_u3c_round4_helpers.py::test_parent_worker_and_subprocess_reenter_c4_wrapper "
                f"{WORKTREE}/tests/test_native_u3d_runner_evidence.py "
                f"{WORKTREE}/tests/test_native_u5_external_schema.py"
            ),
            "exit_code": 0,
            "collected": 8,
            "passed": 7,
            "skipped": 1,
            "failed": 0,
            "errors": 0,
            "duration_seconds": 16.84,
            "log_path": str(SCRATCH / "part1-worktree-target-nodes.log"),
            "log_sha256": sha256_file(SCRATCH / "part1-worktree-target-nodes.log"),
            "notes": (
                "7 passed, 1 skipped (test_same_external_320_api_instruction_before_after skips "
                "naming missing baseline-d258611c5/tree/.claude/agents/_preimages.json removed by "
                "2026-11-11 deduplication; both modular and merged external 3.2.0 catalog tests run and pass)."
            ),
        },
        {
            "id": "part1_worktree_full_files",
            "part": "Part 1",
            "location": str(WORKTREE),
            "command": (
                "GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null "
                f"PYTHONPATH={WORKTREE}/src:{WORKTREE}:/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/lib/python3.13/site-packages "
                "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S "
                "-m pytest -v -rs -p no:cacheprovider "
                f"--basetemp {SCRATCH}/part1-worktree-full-files "
                f"{WORKTREE}/tests/test_native_u3c_round4_helpers.py "
                f"{WORKTREE}/tests/test_native_u3d_runner_evidence.py "
                f"{WORKTREE}/tests/test_native_u5_external_schema.py"
            ),
            "exit_code": 0,
            "collected": 10,
            "passed": 9,
            "skipped": 1,
            "failed": 0,
            "errors": 0,
            "duration_seconds": 19.47,
            "log_path": str(SCRATCH / "part1-worktree-full-files.log"),
            "log_sha256": sha256_file(SCRATCH / "part1-worktree-full-files.log"),
            "notes": (
                "All 3 complete Part 1 test files (10 items) run in worktree with -S to avoid "
                "editable .pth namespace mixing from primary repo: 9 passed, 1 skipped."
            ),
        },
        {
            "id": "part1_cisim_target_nodes",
            "part": "Part 1",
            "location": str(CISIM),
            "command": (
                f"PYTHONPATH={CISIM}/src "
                "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python "
                "-m pytest -v -rs -p no:cacheprovider "
                f"--basetemp {SCRATCH}/part1-cisim-target-nodes "
                f"{CISIM}/tests/test_native_u3c_round4_helpers.py::test_parent_worker_and_subprocess_reenter_c4_wrapper "
                f"{CISIM}/tests/test_native_u3d_runner_evidence.py "
                f"{CISIM}/tests/test_native_u5_external_schema.py"
            ),
            "exit_code": 0,
            "collected": 8,
            "passed": 5,
            "skipped": 3,
            "failed": 0,
            "errors": 0,
            "duration_seconds": 1.06,
            "log_path": str(SCRATCH / "part1-cisim-target-nodes.log"),
            "log_sha256": sha256_file(SCRATCH / "part1-cisim-target-nodes.log"),
            "notes": (
                "Outside d4d-executions: 5 passed (u3c wrapper, u3d snapshot, and all 3 u5 scratch-root "
                "refusals) and 3 skipped honestly naming missing schema-5e382f0c4/manifest.json and "
                "baseline-d258611c5/manifest.json."
            ),
        },
        {
            "id": "part1_cisim_full_files",
            "part": "Part 1",
            "location": str(CISIM),
            "command": (
                "GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null "
                f"PYTHONPATH={CISIM}/src:{CISIM}:/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/lib/python3.13/site-packages "
                "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S "
                "-m pytest -v -rs -p no:cacheprovider "
                f"--basetemp {SCRATCH}/part1-cisim-full-files "
                f"{CISIM}/tests/test_native_u3c_round4_helpers.py "
                f"{CISIM}/tests/test_native_u3d_runner_evidence.py "
                f"{CISIM}/tests/test_native_u5_external_schema.py"
            ),
            "exit_code": 1,
            "collected": 10,
            "passed": 6,
            "skipped": 3,
            "failed": 1,
            "errors": 0,
            "duration_seconds": 1.30,
            "log_path": str(SCRATCH / "part1-cisim-full-files.log"),
            "log_sha256": sha256_file(SCRATCH / "part1-cisim-full-files.log"),
            "notes": (
                "All 8 Part 1 target items pass/skip (6 passed including test_current_census_refuses_existing_output_without_overwriting, "
                "3 skipped); only test_current_integrated_c_and_d_graphs_are_accepted fails in ci-sim-b11931410305 "
                "because ci-sim-b11931410305 was unpacked from git archive without a .git directory "
                "(it passed on the real CI runner checkout in run 42976790438)."
            ),
        },
        {
            "id": "part2_step1_cisim_alone",
            "part": "Part 2",
            "location": str(CISIM),
            "command": (
                "GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null "
                f"GIT_DIR=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.git "
                f"PYTHONPATH={CISIM}/src "
                "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python "
                "-m pytest -v -p no:cacheprovider "
                f"--basetemp {SCRATCH}/part2-step1-gitdir "
                f"{CISIM}/tests/test_native_execution_round5_v2.py::test_actual_pinned_helper_ignores_scratch_forged_cache"
            ),
            "exit_code": 1,
            "collected": 1,
            "passed": 0,
            "skipped": 0,
            "failed": 1,
            "errors": 0,
            "duration_seconds": 0.20,
            "log_path": str(SCRATCH / "part2-step1-gitdir.log"),
            "log_sha256": sha256_file(SCRATCH / "part2-step1-gitdir.log"),
            "notes": (
                "Single test in ci-sim-b11931410305: controller_sources() at native_attribution_controller_v2.py:42 "
                "PASSES (no prepare_registration origin error); fails later at native_supervisor_authority_v2.py:25 "
                "(git rev-parse HEAD) only because ci-sim-b11931410305 has no .git and resources.git_env() strips GIT_DIR."
            ),
        },
        {
            "id": "part2_step2_cisim_pycacheprefix",
            "part": "Part 2",
            "location": str(CISIM),
            "command": (
                "GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null "
                f"PYTHONPYCACHEPREFIX={SCRATCH}/pycache "
                f"PYTHONPATH={CISIM}/src "
                "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python "
                "-m pytest -v -p no:cacheprovider "
                f"--basetemp {SCRATCH}/part2-step2-pycache "
                f"{CISIM}/tests/test_native_execution_round5_v2.py::test_actual_pinned_helper_ignores_scratch_forged_cache"
            ),
            "exit_code": 1,
            "collected": 1,
            "passed": 0,
            "skipped": 0,
            "failed": 1,
            "errors": 0,
            "duration_seconds": 0.20,
            "log_path": str(SCRATCH / "part2-step2-pycache.log"),
            "log_sha256": sha256_file(SCRATCH / "part2-step2-pycache.log"),
            "notes": (
                "Adding CI's PYTHONPYCACHEPREFIX does NOT trigger the prepare_registration origin error; "
                "controller_sources() at line 42 still passes."
            ),
        },
        {
            "id": "part2_step3_cisim_ci_env",
            "part": "Part 2",
            "location": str(CISIM),
            "command": (
                "GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null "
                f"PYTHONPYCACHEPREFIX={SCRATCH}/pycache CI=true GITHUB_ACTIONS=true RUNNER_OS=Linux "
                f"PYTHONPATH={CISIM}/src "
                "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python "
                "-m pytest -v -p no:cacheprovider "
                f"--basetemp {SCRATCH}/part2-step3-cienv "
                f"{CISIM}/tests/test_native_execution_round5_v2.py::test_actual_pinned_helper_ignores_scratch_forged_cache"
            ),
            "exit_code": 1,
            "collected": 1,
            "passed": 0,
            "skipped": 0,
            "failed": 1,
            "errors": 0,
            "duration_seconds": 0.20,
            "log_path": str(SCRATCH / "part2-step3-cienv.log"),
            "log_sha256": sha256_file(SCRATCH / "part2-step3-cienv.log"),
            "notes": (
                "Adding CI=true GITHUB_ACTIONS=true RUNNER_OS=Linux does NOT trigger the prepare_registration "
                "origin error; controller_sources() at line 42 still passes."
            ),
        },
        {
            "id": "part2_step4_cisim_collect_leak",
            "part": "Part 2",
            "location": str(CISIM),
            "command": (
                f"PYTHONPATH={CISIM}/src "
                "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python "
                "-m pytest -v -p no:cacheprovider "
                f"--basetemp {SCRATCH}/part2-step4-collect-leak "
                f"{CISIM}/tests/test_audit_recall_leak_rendered.py "
                f"{CISIM}/tests/test_native_execution_round5_v2.py::test_actual_pinned_helper_ignores_scratch_forged_cache "
                "-k test_actual_pinned_helper_ignores_scratch_forged_cache"
            ),
            "exit_code": 1,
            "collected": 38,
            "passed": 0,
            "skipped": 0,
            "failed": 1,
            "errors": 0,
            "duration_seconds": 0.99,
            "log_path": str(SCRATCH / "part2-step4-collect-leak.log"),
            "log_sha256": sha256_file(SCRATCH / "part2-step4-collect-leak.log"),
            "notes": (
                "REPRODUCED in ci-sim-b11931410305: collecting tests/test_audit_recall_leak_rendered.py "
                "(even with all 37 of its tests deselected via -k) imports v1 prepare_registration.py into "
                "sys.modules['prepare_registration'] at collection time, causing "
                "test_actual_pinned_helper_ignores_scratch_forged_cache to fail at "
                "native_attribution_controller_v2.py:42 with "
                "ValueError: native controller dependency imported from another origin: prepare_registration."
            ),
        },
        {
            "id": "part2_step5_worktree_alone_ci_env",
            "part": "Part 2",
            "location": str(WORKTREE),
            "command": (
                "GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null "
                f"PYTHONPYCACHEPREFIX={SCRATCH}/pycache CI=true GITHUB_ACTIONS=true RUNNER_OS=Linux "
                f"PYTHONPATH={WORKTREE}/src "
                "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python "
                "-m pytest -v -p no:cacheprovider "
                f"--basetemp {SCRATCH}/part2-step5-worktree-alone "
                f"{WORKTREE}/tests/test_native_execution_round5_v2.py::test_actual_pinned_helper_ignores_scratch_forged_cache"
            ),
            "exit_code": 0,
            "collected": 1,
            "passed": 1,
            "skipped": 0,
            "failed": 0,
            "errors": 0,
            "duration_seconds": 1.98,
            "log_path": str(SCRATCH / "part2-step5-worktree-alone.log"),
            "log_sha256": sha256_file(SCRATCH / "part2-step5-worktree-alone.log"),
            "notes": (
                "In worktree (with .git present), running the test alone with PYTHONPYCACHEPREFIX and CI "
                "env vars PASSES (1 passed)."
            ),
        },
        {
            "id": "part2_step6_worktree_collect_leak",
            "part": "Part 2",
            "location": str(WORKTREE),
            "command": (
                "GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null "
                f"PYTHONPATH={WORKTREE}/src "
                "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python "
                "-m pytest -v -p no:cacheprovider "
                f"--basetemp {SCRATCH}/part2-step6-worktree-collect-leak "
                f"{WORKTREE}/tests/test_audit_recall_leak_rendered.py "
                f"{WORKTREE}/tests/test_native_execution_round5_v2.py::test_actual_pinned_helper_ignores_scratch_forged_cache "
                "-k test_actual_pinned_helper_ignores_scratch_forged_cache"
            ),
            "exit_code": 1,
            "collected": 38,
            "passed": 0,
            "skipped": 0,
            "failed": 1,
            "errors": 0,
            "duration_seconds": 1.20,
            "log_path": str(SCRATCH / "part2-step6-worktree-collect-leak.log"),
            "log_sha256": sha256_file(SCRATCH / "part2-step6-worktree-collect-leak.log"),
            "notes": (
                "REPRODUCED in worktree: collecting tests/test_audit_recall_leak_rendered.py in the same "
                "pytest invocation makes test_actual_pinned_helper_ignores_scratch_forged_cache fail with "
                "ValueError: native controller dependency imported from another origin: prepare_registration."
            ),
        },
        {
            "id": "part2_step7_worktree_v1_then_v2",
            "part": "Part 2",
            "location": str(WORKTREE),
            "command": (
                "GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null "
                f"PYTHONPATH={WORKTREE}/src "
                "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python "
                "-m pytest -v -p no:cacheprovider "
                f"--basetemp {SCRATCH}/part2-step7-worktree-v1-then-v2 "
                f"{WORKTREE}/tests/test_native_attribution_controller.py::test_composition_can_prepare_and_matches_every_selected_command "
                f"{WORKTREE}/tests/test_native_execution_round5_v2.py::test_actual_pinned_helper_ignores_scratch_forged_cache"
            ),
            "exit_code": 1,
            "collected": 2,
            "passed": 1,
            "skipped": 0,
            "failed": 1,
            "errors": 0,
            "duration_seconds": 4.09,
            "log_path": str(SCRATCH / "part2-step7-worktree-v1-then-v2.log"),
            "log_sha256": sha256_file(SCRATCH / "part2-step7-worktree-v1-then-v2.log"),
            "notes": (
                "REPRODUCED via execution order in worktree: running a v1 controller test "
                "(test_native_attribution_controller.py) before the v2 test loads v1 prepare_registration.py "
                "into sys.modules['prepare_registration'], causing the v2 test to fail with the same ValueError."
            ),
        },
    ]

    part2_changes = [
        {
            "step": "1",
            "tree": str(CISIM),
            "change_tested": "Baseline single test outside d4d-executions (default environment)",
            "controller_sources_line_42_outcome": "PASSED (no prepare_registration origin error)",
            "overall_pytest_outcome": "FAILED at native_supervisor_authority_v2.py:25 (git rev-parse HEAD) because ci-sim archive has no .git",
            "triggered_target_value_error": False,
            "log_path": str(SCRATCH / "part2-step1-gitdir.log"),
        },
        {
            "step": "2",
            "tree": str(CISIM),
            "change_tested": "Add PYTHONPYCACHEPREFIX=<scratch>/pycache (matching CI job log)",
            "controller_sources_line_42_outcome": "PASSED (no prepare_registration origin error)",
            "overall_pytest_outcome": "FAILED at native_supervisor_authority_v2.py:25 (git rev-parse HEAD)",
            "triggered_target_value_error": False,
            "log_path": str(SCRATCH / "part2-step2-pycache.log"),
        },
        {
            "step": "3",
            "tree": str(CISIM),
            "change_tested": "Add CI=true GITHUB_ACTIONS=true RUNNER_OS=Linux (matching CI job log)",
            "controller_sources_line_42_outcome": "PASSED (no prepare_registration origin error)",
            "overall_pytest_outcome": "FAILED at native_supervisor_authority_v2.py:25 (git rev-parse HEAD)",
            "triggered_target_value_error": False,
            "log_path": str(SCRATCH / "part2-step3-cienv.log"),
        },
        {
            "step": "4",
            "tree": str(CISIM),
            "change_tested": "Collect tests/test_audit_recall_leak_rendered.py in the same pytest process (-k test_actual_pinned_helper_ignores_scratch_forged_cache, matching full-suite collection before --ci-shard=3/8 filtering)",
            "controller_sources_line_42_outcome": "FAILED: ValueError: native controller dependency imported from another origin: prepare_registration",
            "overall_pytest_outcome": "FAILED at native_attribution_controller_v2.py:42",
            "triggered_target_value_error": True,
            "log_path": str(SCRATCH / "part2-step4-collect-leak.log"),
        },
        {
            "step": "5",
            "tree": str(WORKTREE),
            "change_tested": "Control in git worktree: single test with PYTHONPYCACHEPREFIX + CI=true GITHUB_ACTIONS=true RUNNER_OS=Linux",
            "controller_sources_line_42_outcome": "PASSED",
            "overall_pytest_outcome": "PASSED (1 passed in 1.98s)",
            "triggered_target_value_error": False,
            "log_path": str(SCRATCH / "part2-step5-worktree-alone.log"),
        },
        {
            "step": "6",
            "tree": str(WORKTREE),
            "change_tested": "Collect tests/test_audit_recall_leak_rendered.py in the same pytest process in git worktree (-k test_actual_pinned_helper_ignores_scratch_forged_cache)",
            "controller_sources_line_42_outcome": "FAILED: ValueError: native controller dependency imported from another origin: prepare_registration",
            "overall_pytest_outcome": "FAILED at native_attribution_controller_v2.py:42",
            "triggered_target_value_error": True,
            "log_path": str(SCRATCH / "part2-step6-worktree-collect-leak.log"),
        },
        {
            "step": "7",
            "tree": str(WORKTREE),
            "change_tested": "Run v1 test (tests/test_native_attribution_controller.py::test_composition_can_prepare_and_matches_every_selected_command) before the v2 test in the same pytest process",
            "controller_sources_line_42_outcome": "FAILED: ValueError: native controller dependency imported from another origin: prepare_registration",
            "overall_pytest_outcome": "FAILED at native_attribution_controller_v2.py:42 (1 failed, 1 passed)",
            "triggered_target_value_error": True,
            "log_path": str(SCRATCH / "part2-step7-worktree-v1-then-v2.log"),
        },
    ]

    return {
        "assignment": str(
            REPORT_ROOT
            / "notes/development_efficiency_20261111/assignments/claude-lead-agy4-native-ci-portability-20261112.md"
        ),
        "worker": "agy4",
        "date": "2026-11-12",
        "worktree": str(WORKTREE),
        "branch": "agy/native-ci-collection-5875-20261112",
        "base_commit": "ddcadcdc20ce40cdeb6eb92645c17883f2060be6",
        "ci_sim_tree": str(CISIM),
        "scratch_dir": str(SCRATCH),
        "diff_summary": {
            "files_changed": 3,
            "insertions": 120,
            "deletions": 41,
            "edited_files": edited_files,
            "untouched_scripts": untouched_scripts,
        },
        "commands": commands,
        "part1_ci_failures_addressed": layout_failures,
        "part2_diagnosis": {
            "ci_failure_count": len(origin_failures),
            "ci_failures_by_file": [
                {"file": k, "count": v} for k, v in sorted(origin_by_file.items())
            ],
            "check_locations": [
                {
                    "file": "src/data_sheets_schema/native_attribution_controller_v2.py",
                    "line": 42,
                    "function": "controller_sources",
                    "manifest_file": "src/data_sheets_schema/native_controller_sources_v2.json",
                    "expected_path_for_prepare_registration": "notes/matched_cborg_2026-09-13/prepare_registration_v2.py",
                },
                {
                    "file": "src/data_sheets_schema/native_attribution_controller.py",
                    "line": 40,
                    "function": "controller_sources",
                    "manifest_file": "src/data_sheets_schema/native_controller_sources_v1.json",
                    "expected_path_for_prepare_registration": "notes/matched_cborg_2026-09-13/prepare_registration.py",
                },
            ],
            "collection_time_polluter": {
                "file": "tests/test_audit_recall_leak_rendered.py",
                "lines": "100-112",
                "loaded_module_name": "prepare_registration",
                "loaded_module_origin": "notes/matched_cborg_2026-09-13/prepare_registration.py",
                "only_collection_time_polluter_in_tests_suite": True,
            },
            "existing_isolation_fixture": {
                "file": "tests/test_native_execution_registration_v2.py",
                "lines": "26-43",
                "fixture_name": "isolated_modules",
            },
            "step_by_step_experiments": part2_changes,
        },
    }


def render_markdown_tables(data: dict) -> str:
    lines: list[str] = []

    lines.append("### Table 1 — Diff Summary and Computed SHA-256 Digests (Part 1)")
    lines.append("")
    lines.append("| File | Role | Diff Stat | Computed SHA-256 |")
    lines.append("|---|---|---|---|")
    for item in data["diff_summary"]["edited_files"]:
        stat = f"`+{item['insertions']} / -{item['deletions']}`"
        lines.append(
            f"| `{item['worktree_path']}` | Edited test file | {stat} | `{item['sha256']}` |"
        )
    for item in data["diff_summary"]["untouched_scripts"]:
        lines.append(
            f"| `{item['worktree_path']}` | Untouched script under test | `0` | `{item['sha256']}` |"
        )
    lines.append("")

    lines.append("### Table 2 — Every Command Run with Exit Codes, Counts, and Saved Logs")
    lines.append("")
    lines.append(
        "| ID | Part | Location | Exit Code | Collected | Passed | Skipped | Failed | Errors | Duration (s) | Saved Log (`sha256`) |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for cmd in data["commands"]:
        lines.append(
            f"| `{cmd['id']}` | {cmd['part']} | `{cmd['location']}` | `{cmd['exit_code']}` | "
            f"`{cmd['collected']}` | `{cmd['passed']}` | `{cmd['skipped']}` | `{cmd['failed']}` | "
            f"`{cmd['errors']}` | `{cmd['duration_seconds']:.2f}` | `{cmd['log_path']}` (`{cmd['log_sha256'][:16]}...`) |"
        )
    lines.append("")

    lines.append("### Table 3 — Part 2 One-Change-at-a-Time Reproduction Table")
    lines.append("")
    lines.append(
        "| Step | Tree | Single Variable Changed | `controller_sources()` Line 42 Outcome | Overall Pytest Outcome | Triggered `prepare_registration` ValueError? | Saved Log |"
    )
    lines.append("|---:|---|---|---|---|---|---|")
    for row in data["part2_diagnosis"]["step_by_step_experiments"]:
        trig = "**YES**" if row["triggered_target_value_error"] else "No"
        lines.append(
            f"| `{row['step']}` | `{row['tree']}` | {row['change_tested']} | "
            f"{row['controller_sources_line_42_outcome']} | {row['overall_pytest_outcome']} | "
            f"{trig} | `{row['log_path']}` |"
        )
    lines.append("")

    lines.append("### Table 4 — Breakdown of the 37 CI `controller_dependency_origin` Failures by Test File")
    lines.append("")
    lines.append("| Test File | Failing Test IDs in CI Run 42976790438 | Uses `isolated_modules` Currently? |")
    lines.append("|---|---:|---|")
    for item in data["part2_diagnosis"]["ci_failures_by_file"]:
        lines.append(f"| `{item['file']}` | `{item['count']}` | No |")
    lines.append(
        f"| **Total** | **`{data['part2_diagnosis']['ci_failure_count']}`** | — |"
    )
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if chr(64) in json_text:
        raise RuntimeError("Forbidden character chr(64) found in JSON output")
    OUT_JSON.write_text(json_text, encoding="utf-8")
    md_text = render_markdown_tables(payload)
    if chr(64) in md_text:
        raise RuntimeError("Forbidden character chr(64) found in Markdown output")
    print(md_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
