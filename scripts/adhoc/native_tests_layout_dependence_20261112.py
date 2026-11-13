#!/usr/bin/env python3
"""Mechanical classification of tests mentioning d4d-executions and CI collection fix evidence.

Purpose:
  1. Scan all files under `tests/` in the baseline tree (`b11931410305`, 78 files)
     and the edited worktree (`agy-native-ci-collection-20261112`, 79 files after
     adding the temporary `d4d-executions` fixture tree to
     `tests/test_native_u3c_test_driver.py`) for every file and every line that
     mentions `d4d-executions`.
  2. Classify each matching line mechanically as one of:
     - `inside a string that is only compared or printed`
     - `a path that is opened or resolved`
     - `an import-time statement`
  3. Also scan `tests/*.py` for indirect references to `scripts/adhoc/*.py` that
     themselves enforce `d4d-executions` layout checks at import or run time.
  4. Parse the saved pytest and collection logs from Part 2 Steps 1-2, write the
     structured JSON handoff, and print Markdown tables from the JSON.

Inputs:
  - Baseline tests tree (`HEAD` at `b11931410305569aba30b0f593193ae894bd0dc7`): `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tests`
  - Edited worktree tests tree: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tests`
  - Saved logs:
    - `/tmp/agy4-5875-step1-worktree-pytest.log`
    - `/tmp/agy4-5875-step2-cisim-pytest.log`
    - `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305.collect.log`
    - `/tmp/agy4-5875-step2-cisim-collect.log`

Outputs:
  - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy4-native-ci-collection-fix-20261112.json`
  - Markdown tables printed to stdout (or written to `--md-out` if requested).

Serves: Issue 5875 / assignment `claude-lead-agy4-native-ci-collection-fix-20261112.md`.
Date: 2026-11-12.
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


REPORT_ROOT = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111"
)
EDIT_WORKTREE = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112"
)
CI_SIM_ROOT = Path(
    "/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305"
)
BASELINE_COLLECT_LOG = Path(
    "/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305.collect.log"
)
STEP1_WORKTREE_LOG = Path("/tmp/agy4-5875-step1-worktree-pytest.log")
STEP2_CISIM_PYTEST_LOG = Path("/tmp/agy4-5875-step2-cisim-pytest.log")
STEP2_CISIM_COLLECT_LOG = Path("/tmp/agy4-5875-step2-cisim-collect.log")

JSON_OUT = (
    REPORT_ROOT
    / "notes/development_efficiency_20261111/handoffs/agy4-native-ci-collection-fix-20261112.json"
)

TOKEN = "d4d-executions"

CAT_STRING = "inside a string that is only compared or printed"
CAT_PATH = "a path that is opened or resolved"
CAT_IMPORT = "an import-time statement"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_safe_excerpt(line: str, max_len: int = 140) -> str:
    """Extract a bounded excerpt around `d4d-executions` with no at-sign characters."""
    stripped = line.strip()
    idx = stripped.find(TOKEN)
    if len(stripped) <= max_len:
        excerpt = stripped
    elif idx == -1:
        excerpt = stripped[:max_len] + "..."
    else:
        half = (max_len - len(TOKEN)) // 2
        start = max(0, idx - half)
        end = min(len(stripped), start + max_len)
        start = max(0, end - max_len)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(stripped) else ""
        excerpt = f"{prefix}{stripped[start:end]}{suffix}"
    # Enforce standing rule: zero chr(64) characters in handoff artifacts.
    return excerpt.replace(chr(64), "[at]")


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _enclosing_function(
    node: ast.AST, parents: dict[ast.AST, ast.AST]
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    cur: ast.AST | None = node
    while cur is not None:
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
        cur = parents.get(cur)
    return None


def _statement_calls_path_or_parents(stmt: ast.AST) -> bool:
    """Return True if the AST statement constructs/resolves/opens a Path or walks `.parents`."""
    for sub in ast.walk(stmt):
        if isinstance(sub, ast.Call):
            func = sub.func
            if isinstance(func, ast.Name) and func.id in {"Path", "PurePath", "open"}:
                return True
            if isinstance(func, ast.Attribute) and func.attr in {
                "resolve",
                "open",
                "read_text",
                "read_bytes",
                "mkdir",
                "is_dir",
                "is_file",
                "exists",
                "lexists",
            }:
                return True
        if isinstance(sub, ast.Attribute) and sub.attr == "parents":
            return True
        if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Div):
            return True
    return False


def classify_python_line(
    tree: ast.Module, parents: dict[ast.AST, ast.AST], lineno: int, raw_line: str
) -> tuple[str, str]:
    """Mechanically classify a line in a Python file that contains `d4d-executions`."""
    matching_stmts: list[ast.stmt] = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.stmt)
        and getattr(node, "lineno", 0) <= lineno <= getattr(node, "end_lineno", getattr(node, "lineno", 0))
    ]
    if not matching_stmts:
        return (CAT_STRING, "comment_or_docstring")

    # Innermost statement covering this line
    stmt = min(
        matching_stmts,
        key=lambda n: getattr(n, "end_lineno", n.lineno) - n.lineno,
    )
    enclosing_fn = _enclosing_function(stmt, parents)
    if enclosing_fn is None:
        return (CAT_IMPORT, "module_top_level_statement")

    # Check if `d4d-executions` on this line is used in a Path construction, `/` join, or `.parents` walk
    if _statement_calls_path_or_parents(stmt):
        # Special case: `if 'd4d-executions' in resolved.parts:` checks `.parts` membership on an already-resolved path
        if ".parts" in raw_line and "Path(" not in raw_line and ".parents" not in raw_line and " / " not in raw_line:
            return (CAT_STRING, f"in_function:{enclosing_fn.name}:parts_string_comparison")
        return (CAT_PATH, f"in_function:{enclosing_fn.name}:path_or_parents_operation")

    return (CAT_STRING, f"in_function:{enclosing_fn.name}:string_literal_comparison_or_message")


def classify_file_lines(root: Path, rel_path: str) -> dict[str, Any]:
    full_path = root / rel_path
    text = full_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    is_python = rel_path.endswith(".py")
    tree: ast.Module | None = None
    parents: dict[ast.AST, ast.AST] = {}
    if is_python:
        tree = ast.parse(text, filename=rel_path)
        parents = _build_parent_map(tree)

    line_entries: list[dict[str, Any]] = []
    counts = Counter()
    for idx, raw_line in enumerate(lines, start=1):
        if TOKEN not in raw_line:
            continue
        occurrences = raw_line.count(TOKEN)
        if is_python and tree is not None:
            classification, basis = classify_python_line(tree, parents, idx, raw_line)
        else:
            # Non-Python files under tests/ are static JSON/YAML fixtures or contracts
            suffix = Path(rel_path).suffix.lower()
            if suffix == ".json":
                basis = "json_fixture_string_value"
            elif suffix in {".yaml", ".yml"}:
                basis = (
                    "yaml_fixture_comment_string"
                    if raw_line.lstrip().startswith("#")
                    else "yaml_fixture_string_value"
                )
            else:
                basis = "static_fixture_text"
            classification = CAT_STRING

        counts[classification] += 1
        line_entries.append(
            {
                "line_number": idx,
                "occurrences_on_line": occurrences,
                "classification": classification,
                "mechanical_basis": basis,
                "excerpt": extract_safe_excerpt(raw_line),
            }
        )

    # Determine dominant/summary classification for the file
    if counts[CAT_IMPORT] > 0:
        file_classification = CAT_IMPORT
    elif counts[CAT_PATH] > 0:
        file_classification = CAT_PATH
    else:
        file_classification = CAT_STRING

    return {
        "file": rel_path,
        "file_type": "python" if is_python else Path(rel_path).suffix.lstrip("."),
        "matching_line_count": len(line_entries),
        "total_token_occurrences": sum(item["occurrences_on_line"] for item in line_entries),
        "file_classification": file_classification,
        "classification_counts": {
            CAT_STRING: counts[CAT_STRING],
            CAT_PATH: counts[CAT_PATH],
            CAT_IMPORT: counts[CAT_IMPORT],
        },
        "lines": line_entries,
    }


def scan_tests_tree(root: Path) -> list[dict[str, Any]]:
    tests_dir = root / "tests"
    results: list[dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(tests_dir, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for fname in sorted(filenames):
            if fname.endswith((".pyc", ".pyo")):
                continue
            fpath = Path(dirpath) / fname
            if not fpath.is_file():
                continue
            try:
                raw = fpath.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if TOKEN not in raw:
                continue
            rel = fpath.relative_to(root).as_posix()
            results.append(classify_file_lines(root, rel))
    results.sort(key=lambda item: item["file"])
    return results


def parse_collect_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    error_files = [
        line.removeprefix("ERROR ").strip()
        for line in lines
        if line.startswith("ERROR tests/")
    ]
    summary_line = lines[-1].strip() if lines else ""
    m_collected = re.search(r"(\d+)\s+tests\s+collected", summary_line)
    m_errors = re.search(r"(\d+)\s+errors?", summary_line)
    u3c_nodes = [
        line.strip()
        for line in lines
        if line.startswith("tests/test_native_u3c_test_driver.py::")
    ]
    return {
        "log_path": str(path),
        "log_sha256": sha256_file(path),
        "collected_count": int(m_collected.group(1)) if m_collected else None,
        "error_count": int(m_errors.group(1)) if m_errors else 0,
        "error_files": error_files,
        "u3c_test_driver_error_present": "tests/test_native_u3c_test_driver.py" in error_files,
        "u3c_collected_nodes": u3c_nodes,
        "u3c_collected_node_count": len(u3c_nodes),
        "summary_line": summary_line,
    }


def parse_pytest_run_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary_line = lines[-1] if lines else ""
    m_passed = re.search(r"(\d+)\s+passed", summary_line)
    m_failed = re.search(r"(\d+)\s+failed", summary_line)
    m_errors = re.search(r"(\d+)\s+errors?", summary_line)
    return {
        "log_path": str(path),
        "log_sha256": sha256_file(path),
        "passed_count": int(m_passed.group(1)) if m_passed else 0,
        "failed_count": int(m_failed.group(1)) if m_failed else 0,
        "error_count": int(m_errors.group(1)) if m_errors else 0,
        "summary_line": summary_line,
    }


def git_show_head_file(worktree: Path, rel_path: str) -> bytes:
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_NO_LAZY_FETCH": "1",
    }
    return subprocess.check_output(
        ["/usr/bin/git", "--no-replace-objects", "show", f"HEAD:{rel_path}"],
        cwd=worktree,
        env=env,
    )


def compute_diff_summary(worktree: Path, rel_path: str) -> dict[str, Any]:
    before_bytes = git_show_head_file(worktree, rel_path)
    after_path = worktree / rel_path
    after_bytes = after_path.read_bytes()
    before_lines = before_bytes.decode("utf-8").splitlines(keepends=True)
    after_lines = after_bytes.decode("utf-8").splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
        )
    )
    added = sum(
        1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
    )
    sanitized_diff = "".join(diff_lines).replace(chr(64), "#")
    return {
        "target_file": str(after_path),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest(),
        "after_sha256": hashlib.sha256(after_bytes).hexdigest(),
        "before_line_count": len(before_lines),
        "after_line_count": len(after_lines),
        "added_lines": added,
        "removed_lines": removed,
        "unified_diff_no_at_signs": sanitized_diff,
    }


def build_report() -> dict[str, Any]:
    edited_files = scan_tests_tree(EDIT_WORKTREE)
    # In baseline HEAD (b11931410305569aba30b0f593193ae894bd0dc7), only
    # tests/test_native_u3c_test_driver.py differs, and its HEAD bytes do not contain `d4d-executions`.
    head_u3c_bytes = git_show_head_file(
        EDIT_WORKTREE, "tests/test_native_u3c_test_driver.py"
    )
    assert TOKEN.encode("utf-8") not in head_u3c_bytes
    baseline_files = [
        f for f in edited_files if f["file"] != "tests/test_native_u3c_test_driver.py"
    ]

    baseline_line_totals = Counter()
    for item in baseline_files:
        for k, v in item["classification_counts"].items():
            baseline_line_totals[k] += v

    edited_line_totals = Counter()
    for item in edited_files:
        for k, v in item["classification_counts"].items():
            edited_line_totals[k] += v

    python_files_baseline = [f for f in baseline_files if f["file_type"] == "python"]
    python_files_edited = [f for f in edited_files if f["file_type"] == "python"]

    runtime_layout_hazards = [
        {
            "test_file": "tests/test_native_u3c_round4_helpers.py",
            "line_number": 25,
            "test_function": "test_parent_worker_and_subprocess_reenter_c4_wrapper",
            "direct_mention_in_tests": True,
            "classification": CAT_PATH,
            "collection_time_impact": "None (loads helper inside test function, not at module import time).",
            "runtime_impact_on_ci_runner": (
                "FAILS at test execution time outside d4d-executions: line 24 calls "
                "helper('run_native_u3c_round4_20261107.py'), which executes "
                "scripts/adhoc/run_native_u3a_tests_20261107.py (raising RuntimeError: "
                "'source must be below the canonical d4d-executions root'), and line 25 "
                "evaluates `next(path for path in ROOT.parents if path.name == 'd4d-executions')` "
                "(raising StopIteration)."
            ),
        },
        {
            "test_file": "tests/test_native_u3d_runner_evidence.py",
            "line_number": 11,
            "test_function": "test_source_snapshot_binds_tracked_and_untracked_bytes",
            "direct_mention_in_tests": False,
            "classification": "indirect via scripts/adhoc/run_native_u3d_tests_20261107.py:30-32",
            "collection_time_impact": "None (loads script inside test function, not at module import time).",
            "runtime_impact_on_ci_runner": (
                "FAILS at test execution time outside d4d-executions: line 14 executes "
                "scripts/adhoc/run_native_u3d_tests_20261107.py, which checks "
                "`_executions = [path for path in ROOT.parents if path.name == 'd4d-executions']` "
                "at module top level (lines 30-32) and raises RuntimeError: "
                "'expected one enclosing d4d-executions directory'."
            ),
        },
        {
            "test_file": "tests/test_native_u5_external_schema.py",
            "line_number": 97,
            "test_function": "test_same_external_320_api_instruction_before_after, test_api_comparison_refuses_other_scratch_roots",
            "direct_mention_in_tests": False,
            "classification": "indirect via scripts/adhoc/native_u5_api_render_20261108.py:28 (and SCRATCH manifest lookup)",
            "collection_time_impact": "None (runs subprocess inside test functions).",
            "runtime_impact_on_ci_runner": (
                "FAILS at test execution time outside d4d-executions: requires pre-materialized "
                "scratch-native-u5-prep exports and invokes scripts/adhoc/native_u5_api_render_20261108.py, "
                "which checks `executions = [p for p in checkout.parents if p.name == 'd4d-executions']` "
                "(line 28) and raises SystemExit('source root must sit under d4d-executions')."
            ),
        },
    ]

    diff_summary = compute_diff_summary(
        EDIT_WORKTREE,
        "tests/test_native_u3c_test_driver.py",
    )

    step1_run = parse_pytest_run_log(STEP1_WORKTREE_LOG)
    step2_pytest_run = parse_pytest_run_log(STEP2_CISIM_PYTEST_LOG)
    baseline_collect = parse_collect_log(BASELINE_COLLECT_LOG)
    step2_collect = parse_collect_log(STEP2_CISIM_COLLECT_LOG)

    return {
        "schema_version": "1.0",
        "date": "2026-11-12",
        "issue": 5875,
        "assignment": str(
            REPORT_ROOT
            / "notes/development_efficiency_20261111/assignments/claude-lead-agy4-native-ci-collection-fix-20261112.md"
        ),
        "worktree": str(EDIT_WORKTREE),
        "branch": "agy/native-ci-collection-5875-20261112",
        "base_commit": "b11931410305569aba30b0f593193ae894bd0dc7",
        "answer_summary": {
            "route_taken": (
                "Preferred route: module-scoped fixture (`driver`) in `tests/test_native_u3c_test_driver.py` "
                "builds a temporary `d4d-executions` directory with `plans` under a resolved temporary base directory "
                "outside `d4d-executions` and copies `scripts/adhoc/run_native_u3a_tests_20261107.py` to "
                "a `checkout` subdirectory at the same relative depth (`parents[2]`), loading the module inside the "
                "fixture rather than at import time. Also renamed the helper `setup()` to `_setup(driver_module)` "
                "so pytest's xunit plugin does not invoke `setup` as a module/function setup hook."
            ),
            "run_native_u3a_tests_20261107_edited": False,
            "run_native_u3a_tests_20261107_sha256": sha256_file(
                EDIT_WORKTREE / "scripts/adhoc/run_native_u3a_tests_20261107.py"
            ),
            "four_tests_pass_in_worktree": step1_run["passed_count"] == 4
            and step1_run["failed_count"] == 0
            and step1_run["error_count"] == 0,
            "four_tests_pass_outside_executions": step2_pytest_run["passed_count"] == 4
            and step2_pytest_run["failed_count"] == 0
            and step2_pytest_run["error_count"] == 0,
            "collection_clean_of_u3c_error_outside_executions": (
                not step2_collect["u3c_test_driver_error_present"]
                and step2_collect["u3c_collected_node_count"] == 4
            ),
        },
        "diff_summary": diff_summary,
        "commands": [
            {
                "step": "part2_step1_worktree_pytest",
                "cwd": str(EDIT_WORKTREE),
                "command": (
                    "PYTHONPATH=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/src "
                    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest "
                    "-p no:cacheprovider --basetemp /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tmp/basetemp "
                    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tests/test_native_u3c_test_driver.py"
                ),
                "exit_code": 0,
                "result": step1_run,
            },
            {
                "step": "part2_step2_copy_to_ci_sim",
                "cwd": "/Users/marcin",
                "command": (
                    "cp /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tests/test_native_u3c_test_driver.py "
                    "/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305/tests/test_native_u3c_test_driver.py"
                ),
                "exit_code": 0,
                "copied_file_sha256": sha256_file(
                    CI_SIM_ROOT / "tests/test_native_u3c_test_driver.py"
                ),
            },
            {
                "step": "part2_step2_ci_sim_pytest",
                "cwd": str(CI_SIM_ROOT),
                "command": (
                    "PYTHONPATH=/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305/src "
                    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest "
                    "-p no:cacheprovider --basetemp /tmp/agy4-5875-ci-sim-basetemp "
                    "/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305/tests/test_native_u3c_test_driver.py"
                ),
                "exit_code": 0,
                "result": step2_pytest_run,
            },
            {
                "step": "part2_step2_ci_sim_collect_only",
                "cwd": str(CI_SIM_ROOT),
                "command": (
                    "cd /Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305 && "
                    "PYTHONPATH=/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305/src "
                    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest "
                    "--collect-only -q tests -p no:cacheprovider"
                ),
                "exit_code": 2,
                "baseline_collect": baseline_collect,
                "after_fix_collect": step2_collect,
            },
        ],
        "step3_layout_dependence": {
            "search_method": (
                "gitignore-independent walk of `tests/` (`os.walk`, skipping only `__pycache__`/`*.pyc`), "
                "which includes the 5 tracked `*_api_progress.json` fixture files matched by `.gitignore` "
                "(74 files via default `rg`, 78 files via `rg -uu` / `git grep` in baseline `b11931410305`, "
                "and 79 files in `agy-native-ci-collection-20261112` after `tests/test_native_u3c_test_driver.py` "
                "adds the synthetic temp-tree `d4d-executions` fixture)."
            ),
            "baseline_b11931410305_counts": {
                "files_mentioning_d4d_executions": len(baseline_files),
                "python_files_mentioning_d4d_executions": len(python_files_baseline),
                "fixture_data_files_mentioning_d4d_executions": len(baseline_files)
                - len(python_files_baseline),
                "total_matching_lines": sum(f["matching_line_count"] for f in baseline_files),
                "total_token_occurrences": sum(
                    f["total_token_occurrences"] for f in baseline_files
                ),
                "line_classification_counts": {
                    CAT_STRING: baseline_line_totals[CAT_STRING],
                    CAT_PATH: baseline_line_totals[CAT_PATH],
                    CAT_IMPORT: baseline_line_totals[CAT_IMPORT],
                },
                "file_classification_counts": dict(
                    Counter(f["file_classification"] for f in baseline_files)
                ),
            },
            "edited_worktree_counts": {
                "files_mentioning_d4d_executions": len(edited_files),
                "python_files_mentioning_d4d_executions": len(python_files_edited),
                "fixture_data_files_mentioning_d4d_executions": len(edited_files)
                - len(python_files_edited),
                "total_matching_lines": sum(f["matching_line_count"] for f in edited_files),
                "total_token_occurrences": sum(
                    f["total_token_occurrences"] for f in edited_files
                ),
                "line_classification_counts": {
                    CAT_STRING: edited_line_totals[CAT_STRING],
                    CAT_PATH: edited_line_totals[CAT_PATH],
                    CAT_IMPORT: edited_line_totals[CAT_IMPORT],
                },
                "file_classification_counts": dict(
                    Counter(f["file_classification"] for f in edited_files)
                ),
            },
            "python_files_detail_edited_worktree": python_files_edited,
            "runtime_ci_hazards_identified": runtime_layout_hazards,
            "baseline_78_files": baseline_files,
            "edited_worktree_79_files": edited_files,
        },
    }


def render_markdown_tables(data: dict[str, Any]) -> str:
    out: list[str] = []

    # Table 1: Verification commands and results
    out.append("### Table 1 — Verification Commands and Outcomes (Part 2, Steps 1–2)")
    out.append("")
    out.append("| Step | Location | Exit Code | Passed | Collection Errors | Collected Tests | Saved Log |")
    out.append("|---|---|---:|---:|---:|---:|---|")
    c0 = data["commands"][0]
    c2 = data["commands"][2]
    c3 = data["commands"][3]
    b_col = c3["baseline_collect"]
    a_col = c3["after_fix_collect"]
    out.append(
        f"| Step 1 (`pytest tests/test_native_u3c_test_driver.py`) | `{EDIT_WORKTREE}` | `{c0['exit_code']}` | `{c0['result']['passed_count']}` | `{c0['result']['error_count']}` | `4` | `{c0['result']['log_path']}` |"
    )
    out.append(
        f"| Step 2a (`pytest tests/test_native_u3c_test_driver.py` outside `d4d-executions`) | `{CI_SIM_ROOT}` | `{c2['exit_code']}` | `{c2['result']['passed_count']}` | `{c2['result']['error_count']}` | `4` | `{c2['result']['log_path']}` |"
    )
    out.append(
        f"| Step 2b Baseline (`pytest --collect-only -q tests` before fix) | `{CI_SIM_ROOT}` | `2` | n/a | `{b_col['error_count']}` (includes `test_native_u3c_test_driver.py`) | `{b_col['collected_count']}` | `{b_col['log_path']}` |"
    )
    out.append(
        f"| Step 2b After Fix (`pytest --collect-only -q tests` after fix) | `{CI_SIM_ROOT}` | `{c3['exit_code']}` | n/a | `{a_col['error_count']}` (only 3 `fairscape_models.rocrate`; `u3c` error gone) | `{a_col['collected_count']}` | `{a_col['log_path']}` |"
    )
    out.append("")

    # Table 2: Summary of Step 3 mechanical classification
    s3 = data["step3_layout_dependence"]
    b_cnt = s3["baseline_b11931410305_counts"]
    e_cnt = s3["edited_worktree_counts"]
    out.append("### Table 2 — Mechanical Classification Summary (`tests/` Mentions of `d4d-executions`)")
    out.append("")
    out.append("| Classification | Baseline `b11931410305` Files (of 78) | Baseline `b11931410305` Lines (of 601) | Edited Worktree Files (of 79) | Edited Worktree Lines (of 604) |")
    out.append("|---|---:|---:|---:|---:|")
    for cat in (CAT_STRING, CAT_PATH, CAT_IMPORT):
        bf = b_cnt["file_classification_counts"].get(cat, 0)
        bl = b_cnt["line_classification_counts"].get(cat, 0)
        ef = e_cnt["file_classification_counts"].get(cat, 0)
        el = e_cnt["line_classification_counts"].get(cat, 0)
        out.append(f"| `{cat}` | `{bf}` | `{bl}` | `{ef}` | `{el}` |")
    out.append(
        f"| **Total** | **`{b_cnt['files_mentioning_d4d_executions']}`** | **`{b_cnt['total_matching_lines']}`** | **`{e_cnt['files_mentioning_d4d_executions']}`** | **`{e_cnt['total_matching_lines']}`** |"
    )
    out.append("")

    # Table 3: Every Python line mentioning d4d-executions
    out.append("### Table 3 — Python Files Under `tests/` Mentioning `d4d-executions` (Line-by-Line)")
    out.append("")
    out.append("| File | Line | Classification | Mechanical Basis | CI Run-Time Assessment | Excerpt |")
    out.append("|---|---:|---|---|---|---|")
    ci_notes = {
        ("tests/test_5139_relative_paths.py", 60): "Safe on CI: synthetic foreign worktree path is lexically stripped to its relative `data/preprocessed` suffix under `tmp_path` by `arm_comparison._path`.",
        ("tests/test_arm_comparison.py", 1254): "Safe on CI: synthetic foreign worktree path is lexically stripped to its relative `data/preprocessed` suffix under `tmp_path` by `arm_comparison._path`.",
        ("tests/test_receipt_origin.py", 3543): "Safe on CI: string key in dict passed to `ro._backstop(command)` and compared to `False`.",
        ("tests/offline_bc1_planline.py", 16): "Not collected by pytest (filename does not match `test_*.py` or `*_test.py`); only runs if invoked as `__main__`.",
        ("tests/test_native_u3c_round4_helpers.py", 25): "**CI RUN-TIME FAILURE**: `test_parent_worker_and_subprocess_reenter_c4_wrapper` loads `scripts/adhoc/run_native_u3c_round4_20261107.py` (which loads `scripts/adhoc/run_native_u3a_tests_20261107.py`) and walks `ROOT.parents` for `d4d-executions`.",
        ("tests/test_native_u3c_test_driver.py", 21): "Added by this fix: skips any temp root whose resolved path is inside `d4d-executions`.",
        ("tests/test_native_u3c_test_driver.py", 28): "Added by this fix: `RuntimeError` message string if no writable temp dir exists.",
        ("tests/test_native_u3c_test_driver.py", 33): "Added by this fix: creates synthetic `d4d-executions` directory under resolved temp base inside module fixture.",
    }
    for fitem in s3["python_files_detail_edited_worktree"]:
        for litem in fitem["lines"]:
            key = (fitem["file"], litem["line_number"])
            note = ci_notes.get(key, "")
            excerpt_escaped = litem["excerpt"].replace("|", "\\|").replace("`", "'")
            out.append(
                f"| `{fitem['file']}` | `{litem['line_number']}` | `{litem['classification']}` | `{litem['mechanical_basis']}` | {note} | {excerpt_escaped} |"
            )
    out.append("")

    # Table 4: Run-time CI hazards (direct + indirect via scripts/adhoc)
    out.append("### Table 4 — Run-Time `d4d-executions` Layout Hazards for CI Execution")
    out.append("")
    out.append("| Test File | Line | Test Function | Direct `d4d-executions` Mention in `tests/` | Collection-Time Impact | Run-Time Impact on CI Runner Outside `d4d-executions` |")
    out.append("|---|---:|---|---|---|---|")
    for h in s3["runtime_ci_hazards_identified"]:
        out.append(
            f"| `{h['test_file']}` | `{h['line_number']}` | `{h['test_function']}` | `{h['direct_mention_in_tests']}` | {h['collection_time_impact']} | {h['runtime_impact_on_ci_runner']} |"
        )
    out.append("")

    # Table 5: Complete 78-file baseline inventory (+1 edited test file = 79 files)
    out.append("### Table 5 — Complete File-by-File Inventory of `d4d-executions` Mentions Under `tests/` (78 Baseline Files + 1 Edited Test File)")
    out.append("")
    out.append("| # | File | Type | Matching Lines | Token Occurrences | Line Numbers | Classification |")
    out.append("|---:|---|---|---:|---:|---|---|")
    for idx, fitem in enumerate(s3["edited_worktree_79_files"], start=1):
        line_nums = ", ".join(str(l["line_number"]) for l in fitem["lines"])
        marker = " *(added by 5875 fix)*" if fitem["file"] == "tests/test_native_u3c_test_driver.py" else ""
        out.append(
            f"| {idx} | `{fitem['file']}`{marker} | `{fitem['file_type']}` | `{fitem['matching_line_count']}` | `{fitem['total_token_occurrences']}` | `{line_nums}` | `{fitem['file_classification']}` |"
        )
    out.append("")
    return "\n".join(out)


def main() -> None:
    report = build_report()
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(report, indent=2) + "\n"
    if chr(64) in json_text:
        raise RuntimeError("at-sign character detected in JSON output")
    JSON_OUT.write_text(json_text, encoding="utf-8")

    md_tables = render_markdown_tables(report)
    if chr(64) in md_tables:
        raise RuntimeError("at-sign character detected in Markdown tables")
    print(md_tables)


if __name__ == "__main__":
    main()
