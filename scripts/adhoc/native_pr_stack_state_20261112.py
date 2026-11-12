#!/usr/bin/env python3
"""
Purpose:
  Collect the exact state of the 13 open native pull requests in
  bridge2ai/data-sheets-schema (5839, 5840, 5841, 5851, 5852, 5853, 5855,
  5857, 5858, 5866, 5871, 5542, 4659) using gh and git without modifying any
  worktree or GitHub state, write the structured JSON report, and render the
  Markdown handoff tables directly from that JSON.

Inputs:
  - GitHub PR metadata and workflow runs for the 13 PRs via gh (or captured
    raw gh JSON streams when running inside a sandbox that blocks ~/.config/gh).
  - Local git object store in:
    /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111
  - Target main commit: 7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1
  - D127 protected files:
    * src/data_sheets_schema/shared_generation.py
    * src/data_sheets_schema/api_runner.py
    * src/download/prompts/canonical_hashes.yaml
    * tests/utils/run_spec_boundary_contracts.json

Outputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy2-native-pr-stack-state-20261112.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy2-native-pr-stack-state-20261112.md

Assignment:
  claude-lead-agy2-native-pr-stack-state-20261112 (D134)

Date:
  2026-11-12
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List


REPO_SLUG = "bridge2ai/data-sheets-schema"
WORKTREE_ROOT = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111"
)
TARGET_MAIN_COMMIT = "7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1"

PR_NUMBERS: List[int] = [
    5839,
    5840,
    5841,
    5851,
    5852,
    5853,
    5855,
    5857,
    5858,
    5866,
    5871,
    5542,
    4659,
]

D127_PROTECTED_FILES: List[str] = [
    "src/data_sheets_schema/shared_generation.py",
    "src/data_sheets_schema/api_runner.py",
    "src/download/prompts/canonical_hashes.yaml",
    "tests/utils/run_spec_boundary_contracts.json",
]

DEFAULT_JSON_OUT = (
    WORKTREE_ROOT
    / "notes/development_efficiency_20261111/handoffs/agy2-native-pr-stack-state-20261112.json"
)
DEFAULT_MD_OUT = (
    WORKTREE_ROOT
    / "notes/development_efficiency_20261111/handoffs/agy2-native-pr-stack-state-20261112.md"
)
ASSIGNMENT_PATH = (
    WORKTREE_ROOT
    / "notes/development_efficiency_20261111/assignments/claude-lead-agy2-native-pr-stack-state-20261112.md"
)
SCRIPT_PATH = WORKTREE_ROOT / "scripts/adhoc/native_pr_stack_state_20261112.py"

DEFAULT_STEP_PR_RAW = Path(
    "/Users/marcin/.gemini/antigravity-cli/brain/5ccc0e74-cf59-4048-ace1-659970340544/.system_generated/steps/2798/output.txt"
)
DEFAULT_STEP_RUNS_RAW = Path(
    "/Users/marcin/.gemini/antigravity-cli/brain/5ccc0e74-cf59-4048-ace1-659970340544/.system_generated/steps/2807/output.txt"
)


def git_env() -> Dict[str, str]:
    env = dict(os.environ)
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def git_is_ancestor(worktree: Path, ancestor_sha: str, descendant_sha: str) -> bool:
    res = subprocess.run(
        ["git", "-C", str(worktree), "merge-base", "--is-ancestor", ancestor_sha, descendant_sha],
        env=git_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if res.returncode not in (0, 1):
        raise RuntimeError(
            f"git merge-base --is-ancestor failed with exit code {res.returncode} "
            f"for {ancestor_sha} -> {descendant_sha}"
        )
    return res.returncode == 0


def git_three_dot_changed_files(worktree: Path, base_sha: str, head_sha: str) -> List[str]:
    res = subprocess.run(
        ["git", "-C", str(worktree), "diff", "--name-only", f"{base_sha}...{head_sha}"],
        env=git_env(),
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def parse_json_stream(raw_text: str) -> List[Any]:
    decoder = json.JSONDecoder()
    items: List[Any] = []
    idx = 0
    length = len(raw_text)
    while idx < length:
        match = re.search(r"[\{\[]", raw_text[idx:])
        if not match:
            break
        start = idx + match.start()
        try:
            obj, end = decoder.raw_decode(raw_text, start)
            items.append(obj)
            idx = end
        except Exception:
            idx = start + 1
    return items


def load_gh_data_live(pr_numbers: List[int]) -> tuple[Dict[int, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    pr_map: Dict[int, Dict[str, Any]] = {}
    runs_map: Dict[str, List[Dict[str, Any]]] = {}
    for pr_num in pr_numbers:
        pr_res = subprocess.run(
            [
                "gh",
                "pr",
                "view",
                str(pr_num),
                "--repo",
                REPO_SLUG,
                "--json",
                "number,title,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,mergeable,mergeStateStatus,changedFiles,files",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        pr_obj = json.loads(pr_res.stdout)
        pr_map[pr_num] = pr_obj
        head_oid = pr_obj["headRefOid"]
        run_res = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "--repo",
                REPO_SLUG,
                "--commit",
                head_oid,
                "--json",
                "databaseId,workflowName,status,conclusion,event,createdAt,headSha",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        runs_map[head_oid] = json.loads(run_res.stdout)
    return pr_map, runs_map


def load_gh_data_from_raw_captures(
    pr_raw_path: Path, runs_raw_path: Path
) -> tuple[Dict[int, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    pr_items = parse_json_stream(pr_raw_path.read_text(encoding="utf-8"))
    pr_map: Dict[int, Dict[str, Any]] = {}
    for item in pr_items:
        if isinstance(item, dict) and "number" in item and "headRefOid" in item:
            pr_map[int(item["number"])] = item

    run_items = parse_json_stream(runs_raw_path.read_text(encoding="utf-8"))
    runs_map: Dict[str, List[Dict[str, Any]]] = {}
    for item in run_items:
        if isinstance(item, list):
            for run in item:
                if isinstance(run, dict) and "headSha" in run and "databaseId" in run:
                    sha = str(run["headSha"])
                    runs_map.setdefault(sha, []).append(run)
    return pr_map, runs_map


def collect_state(
    worktree: Path,
    pr_raw_path: Path,
    runs_raw_path: Path,
    prefer_live_gh: bool = True,
) -> Dict[str, Any]:
    pr_map: Dict[int, Dict[str, Any]] = {}
    runs_map: Dict[str, List[Dict[str, Any]]] = {}
    gh_source = "live_gh_cli"

    if prefer_live_gh:
        try:
            pr_map, runs_map = load_gh_data_live(PR_NUMBERS)
        except Exception:
            pr_map, runs_map = load_gh_data_from_raw_captures(pr_raw_path, runs_raw_path)
            gh_source = "captured_gh_cli_output"
    else:
        pr_map, runs_map = load_gh_data_from_raw_captures(pr_raw_path, runs_raw_path)
        gh_source = "captured_gh_cli_output"

    missing = [num for num in PR_NUMBERS if num not in pr_map]
    if missing:
        raise RuntimeError(f"Missing PR metadata for PR numbers: {missing}")

    # Verify target main commit and all PR head/base commits exist in worktree object store
    for sha in [TARGET_MAIN_COMMIT] + [pr_map[n]["headRefOid"] for n in PR_NUMBERS] + [
        pr_map[n]["baseRefOid"] for n in PR_NUMBERS
    ]:
        rc = subprocess.run(
            ["git", "-C", str(worktree), "cat-file", "-e", f"{sha}^{{commit}}"],
            env=git_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        if rc != 0:
            raise RuntimeError(f"Commit {sha} is missing from git object store in {worktree}")

    head_branch_to_prs: Dict[str, List[int]] = {}
    for num in PR_NUMBERS:
        head_branch = str(pr_map[num]["headRefName"])
        head_branch_to_prs.setdefault(head_branch, []).append(num)

    records: List[Dict[str, Any]] = []
    for num in PR_NUMBERS:
        raw = pr_map[num]
        head_oid = str(raw["headRefOid"])
        base_oid = str(raw["baseRefOid"])
        head_branch = str(raw["headRefName"])
        base_branch = str(raw["baseRefName"])
        is_draft = bool(raw["isDraft"])
        draft_or_ready = "draft" if is_draft else "ready"

        stack_parents = [p for p in head_branch_to_prs.get(base_branch, []) if p != num]
        stack_children = [
            c for c in PR_NUMBERS if c != num and str(pr_map[c]["baseRefName"]) == head_branch
        ]
        if stack_parents:
            parent_head_oids = [str(pr_map[p]["headRefOid"]) for p in stack_parents]
            base_matches_parent_head = base_oid in parent_head_oids
        else:
            base_matches_parent_head = None

        is_ancestor_of: List[int] = []
        has_ancestor: List[int] = []
        for other_num in PR_NUMBERS:
            if other_num == num:
                continue
            other_head_oid = str(pr_map[other_num]["headRefOid"])
            if git_is_ancestor(worktree, head_oid, other_head_oid):
                is_ancestor_of.append(other_num)
            if git_is_ancestor(worktree, other_head_oid, head_oid):
                has_ancestor.append(other_num)

        gh_files = [
            str(f["path"]) for f in raw.get("files", []) if isinstance(f, dict) and "path" in f
        ]
        git_files = git_three_dot_changed_files(worktree, base_oid, head_oid)
        changed_files_count = int(raw["changedFiles"])

        touched_protected = [
            p for p in D127_PROTECTED_FILES if p in set(gh_files) or p in set(git_files)
        ]

        contains_target_main = git_is_ancestor(worktree, TARGET_MAIN_COMMIT, head_oid)

        raw_runs = runs_map.get(head_oid, [])
        seen_run_ids = set()
        workflow_runs: List[Dict[str, Any]] = []
        for r in raw_runs:
            run_id = int(r["databaseId"])
            if run_id in seen_run_ids:
                continue
            seen_run_ids.add(run_id)
            workflow_runs.append(
                {
                    "databaseId": run_id,
                    "workflowName": str(r["workflowName"]),
                    "status": str(r["status"]),
                    "conclusion": str(r.get("conclusion") or "none"),
                    "event": str(r.get("event") or ""),
                    "createdAt": str(r.get("createdAt") or ""),
                    "headSha": str(r.get("headSha") or head_oid),
                }
            )

        stack_edge_str = (
            ", ".join(f"PR {p}" for p in stack_parents) if stack_parents else "none"
        )
        anc_of_str = (
            ", ".join(f"PR {p}" for p in is_ancestor_of) if is_ancestor_of else "none"
        )
        has_anc_str = (
            ", ".join(f"PR {p}" for p in has_ancestor) if has_ancestor else "none"
        )
        runs_summary_str = (
            "; ".join(
                f"{r['workflowName']} ({r['databaseId']}: {r['status']}/{r['conclusion']})"
                for r in workflow_runs
            )
            if workflow_runs
            else "none"
        )
        protected_str = ", ".join(touched_protected) if touched_protected else "none"
        main_str = "yes" if contains_target_main else "no"

        one_line_summary = (
            f"PR {num} is {draft_or_ready} on head {head_branch} ({head_oid[:12]}) targeting "
            f"{base_branch} (stack parent in list: {stack_edge_str}), reports "
            f"{raw['mergeable']}/{raw['mergeStateStatus']} with {changed_files_count} changed "
            f"file(s), is ancestor of {anc_of_str} (has ancestor in list: {has_anc_str}), "
            f"touches {protected_str} of the D127 protected files, contains main "
            f"{TARGET_MAIN_COMMIT[:12]}: {main_str}, and has head workflow runs: {runs_summary_str}."
        )

        records.append(
            {
                "number": num,
                "title": str(raw["title"]),
                "isDraft": is_draft,
                "draft_or_ready": draft_or_ready,
                "headRefName": head_branch,
                "headRefOid": head_oid,
                "baseRefName": base_branch,
                "baseRefOid": base_oid,
                "stack_edge_parent_prs": stack_parents,
                "stack_edge_child_prs": stack_children,
                "base_oid_matches_stack_parent_head_oid": base_matches_parent_head,
                "mergeable": str(raw["mergeable"]),
                "mergeStateStatus": str(raw["mergeStateStatus"]),
                "changedFiles": changed_files_count,
                "gh_files_list_count": len(gh_files),
                "git_three_dot_changed_files_count": len(git_files),
                "is_ancestor_of_prs": is_ancestor_of,
                "has_ancestor_prs": has_ancestor,
                "workflow_runs_on_head": workflow_runs,
                "d127_protected_files_touched": touched_protected,
                "touches_d127_protected_files": bool(touched_protected),
                "contains_main_7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1": contains_target_main,
                "one_line_summary": one_line_summary,
            }
        )

    payload: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "task_id": "claude-lead-agy2-native-pr-stack-state-20261112",
        "date": "2026-11-12",
        "repository": REPO_SLUG,
        "worktree_path": str(worktree),
        "gh_collection_mode": gh_source,
        "target_main_commit": TARGET_MAIN_COMMIT,
        "d127_protected_files": D127_PROTECTED_FILES,
        "pr_numbers": PR_NUMBERS,
        "summary": {
            "total_prs": len(records),
            "draft_count": sum(1 for r in records if r["isDraft"]),
            "ready_count": sum(1 for r in records if not r["isDraft"]),
            "prs_with_stack_parent_in_list_count": sum(
                1 for r in records if r["stack_edge_parent_prs"]
            ),
            "prs_is_ancestor_of_another_in_list_count": sum(
                1 for r in records if r["is_ancestor_of_prs"]
            ),
            "prs_has_ancestor_in_list_count": sum(
                1 for r in records if r["has_ancestor_prs"]
            ),
            "prs_touching_d127_protected_files_count": sum(
                1 for r in records if r["touches_d127_protected_files"]
            ),
            "prs_containing_main_7ad8c9e7_count": sum(
                1
                for r in records
                if r["contains_main_7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1"]
            ),
            "total_workflow_runs_across_heads": sum(
                len(r["workflow_runs_on_head"]) for r in records
            ),
        },
        "pull_requests": records,
    }
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# State of the Open Native Pull Requests (2026-11-12)")
    lines.append("")
    lines.append("## Generation Command and Inputs")
    lines.append("")
    lines.append("- Assignment specification: `" + str(ASSIGNMENT_PATH) + "`")
    lines.append("- Generator script: `" + str(SCRIPT_PATH) + "`")
    lines.append("- Structured JSON output: `" + str(DEFAULT_JSON_OUT) + "`")
    lines.append("- Markdown handoff output: `" + str(DEFAULT_MD_OUT) + "`")
    lines.append("- Target main commit checked for ancestry: " + payload["target_main_commit"])
    lines.append("- D127 protected files checked:")
    for rel_path in payload["d127_protected_files"]:
        lines.append("  - `" + str(WORKTREE_ROOT / rel_path) + "`")
    lines.append("")
    lines.append("```bash")
    lines.append(f"python3 {SCRIPT_PATH}")
    lines.append("```")
    lines.append("")
    lines.append(
        "## Table 1: PR Identity, Stack Edge, Merge State, Changed Files, Ancestry, D127 Protected Files, and Main Containment"
    )
    lines.append("")
    lines.append(
        "| PR | State | Title | Head Branch | Head Commit | Base Branch | Stack Edge (Base=Other Head) | mergeable | mergeStateStatus | Changed Files | Head Is Ancestor Of (Contained In) | Head Has Ancestor In List | D127 Protected Files Changed | Contains main 7ad8c9e7295f |"
    )
    lines.append(
        "|---:|---|---|---|---|---|---|---|---|:---:|---|---|---|---|"
    )

    for pr in payload["pull_requests"]:
        stack_edge = (
            ", ".join(str(p) for p in pr["stack_edge_parent_prs"])
            if pr["stack_edge_parent_prs"]
            else "none"
        )
        anc_of = (
            ", ".join(str(p) for p in pr["is_ancestor_of_prs"])
            if pr["is_ancestor_of_prs"]
            else "none"
        )
        has_anc = (
            ", ".join(str(p) for p in pr["has_ancestor_prs"])
            if pr["has_ancestor_prs"]
            else "none"
        )
        d127 = (
            ", ".join(pr["d127_protected_files_touched"])
            if pr["d127_protected_files_touched"]
            else "none"
        )
        contains_main = (
            "yes"
            if pr["contains_main_7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1"]
            else "no"
        )
        title_clean = pr["title"].replace("|", "\\|")
        lines.append(
            f"| {pr['number']} | {pr['draft_or_ready']} | {title_clean} | {pr['headRefName']} | {pr['headRefOid']} | {pr['baseRefName']} | {stack_edge} | {pr['mergeable']} | {pr['mergeStateStatus']} | {pr['changedFiles']} | {anc_of} | {has_anc} | {d127} | {contains_main} |"
        )

    lines.append("")
    lines.append("## Table 2: Workflow Runs on Each PR Head Commit")
    lines.append("")
    lines.append(
        "| PR | Head Commit | Workflow Name | Run ID | Status | Conclusion | Event | Created At (UTC) |"
    )
    lines.append("|---:|---|---|---:|---|---|---|---|")

    for pr in payload["pull_requests"]:
        runs = pr["workflow_runs_on_head"]
        if not runs:
            lines.append(
                f"| {pr['number']} | {pr['headRefOid']} | none | none | none | none | none | none |"
            )
            continue
        for run in runs:
            wf_name = str(run["workflowName"]).replace("|", "\\|")
            lines.append(
                f"| {pr['number']} | {pr['headRefOid']} | {wf_name} | {run['databaseId']} | {run['status']} | {run['conclusion']} | {run['event']} | {run['createdAt']} |"
            )

    lines.append("")
    lines.append("## One-Line Data Summary per Pull Request")
    lines.append("")
    for pr in payload["pull_requests"]:
        lines.append(f"- {pr['one_line_summary']}")

    lines.append("")
    content = "\n".join(lines)
    if "\x40" in content:
        raise RuntimeError("Generated Markdown contains a forbidden at-sign character")
    return content


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect state of the 13 open native PRs and render JSON + Markdown."
    )
    parser.add_argument("--worktree", type=Path, default=WORKTREE_ROOT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--pr-raw", type=Path, default=DEFAULT_STEP_PR_RAW)
    parser.add_argument("--runs-raw", type=Path, default=DEFAULT_STEP_RUNS_RAW)
    parser.add_argument(
        "--from-captured-gh",
        action="store_true",
        help="Use captured gh CLI output directly without trying live gh first.",
    )
    args = parser.parse_args()

    payload = collect_state(
        worktree=args.worktree,
        pr_raw_path=args.pr_raw,
        runs_raw_path=args.runs_raw,
        prefer_live_gh=not args.from_captured_gh,
    )

    json_text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    if "\x40" in json_text:
        raise RuntimeError("Generated JSON contains a forbidden at-sign character")

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json_text, encoding="utf-8")

    reloaded = json.loads(args.json_out.read_text(encoding="utf-8"))
    md_text = render_markdown(reloaded)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.write_text(md_text, encoding="utf-8")

    # Verify every backticked path in the Markdown file exists on disk
    for m in re.finditer(r"`([^`\n]+)`", md_text):
        token = m.group(1)
        if not Path(token).exists():
            raise RuntimeError(f"Backticked path does not exist: {token}")

    print(f"SCRIPT_PATH={SCRIPT_PATH} SHA256={sha256_file(SCRIPT_PATH)}")
    print(f"JSON_OUT={args.json_out} SHA256={sha256_file(args.json_out)}")
    print(f"MD_OUT={args.md_out} SHA256={sha256_file(args.md_out)}")


if __name__ == "__main__":
    main()
