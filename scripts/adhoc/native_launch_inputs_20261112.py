#!/usr/bin/env python3
"""
Purpose:
  Extract the production native launch CLI inputs and candidate builder
  functions at commit 1a137b58860416a31618de44173180d021dfcc61 as structured
  data without importing or executing repository code, without modifying any
  worktree, and without writing to GitHub.

Inputs:
  - Repository object store:
    /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema
  - Commit:
    1a137b58860416a31618de44173180d021dfcc61
  - Source file parsed via Python ast (from git show):
    src/data_sheets_schema/native_generation.py
  - Builder search words (via git grep -n -E '^\\s*def [A-Za-z0-9_]*<word>'):
    registration, review, bundle, launch_word, word, account_choice,
    statement, runtime, capture, guard, ci_evidence, probe

Outputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy2-native-launch-inputs-20261112.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy2-native-launch-inputs-20261112.md

Assignment:
  claude-lead-agy2-native-launch-inputs-20261112 (D134)

Date:
  2026-11-12
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List


REPO_PATH = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema")
WORKTREE_ROOT = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111"
)
TARGET_COMMIT = "1a137b58860416a31618de44173180d021dfcc61"
TARGET_FILE = "src/data_sheets_schema/native_generation.py"

BUILDER_WORDS: List[str] = [
    "registration",
    "review",
    "bundle",
    "launch_word",
    "word",
    "account_choice",
    "statement",
    "runtime",
    "capture",
    "guard",
    "ci_evidence",
    "probe",
]

SCRIPT_PATH = WORKTREE_ROOT / "scripts/adhoc/native_launch_inputs_20261112.py"
ASSIGNMENT_PATH = (
    WORKTREE_ROOT
    / "notes/development_efficiency_20261111/assignments/claude-lead-agy2-native-launch-inputs-20261112.md"
)
DEFAULT_JSON_OUT = (
    WORKTREE_ROOT
    / "notes/development_efficiency_20261111/handoffs/agy2-native-launch-inputs-20261112.json"
)
DEFAULT_MD_OUT = (
    WORKTREE_ROOT
    / "notes/development_efficiency_20261111/handoffs/agy2-native-launch-inputs-20261112.md"
)


def git_env() -> Dict[str, str]:
    env = dict(os.environ)
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def verify_commit_present(repo: Path, commit: str) -> None:
    res = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"],
        env=git_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Commit {commit} is not present in {repo}")


def git_show_file(repo: Path, commit: str, rel_path: str) -> str:
    res = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{rel_path}"],
        env=git_env(),
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout


def eval_ast_expr(node: ast.AST, local_vars: Dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return local_vars.get(node.id, node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return str(eval_ast_expr(node.left, local_vars)) + str(
            eval_ast_expr(node.right, local_vars)
        )
    if isinstance(node, (ast.Tuple, ast.List)):
        return [eval_ast_expr(elt, local_vars) for elt in node.elts]
    return ast.unparse(node)


def parse_commands_and_arguments(source_text: str) -> Dict[str, Any]:
    tree = ast.parse(source_text)
    subparsers_info: Dict[str, Any] = {}
    subcommands: List[Dict[str, Any]] = []
    subcmd_by_var: Dict[str, Dict[str, Any]] = {}

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "parser":
            def walk_stmts(stmts: List[ast.stmt], local_vars: Dict[str, Any]) -> None:
                for stmt in stmts:
                    if (
                        isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                    ):
                        var_name = stmt.targets[0].id
                        call = stmt.value
                        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
                            if call.func.attr == "add_subparsers":
                                kw = {
                                    k.arg: eval_ast_expr(k.value, local_vars)
                                    for k in call.keywords
                                    if k.arg
                                }
                                subparsers_info["variable"] = var_name
                                subparsers_info["dest"] = kw.get("dest", "command")
                                subparsers_info["required"] = bool(kw.get("required", False))
                                subparsers_info["line"] = stmt.lineno
                            elif call.func.attr == "add_parser":
                                sub_name = str(eval_ast_expr(call.args[0], local_vars))
                                kw = {
                                    k.arg: eval_ast_expr(k.value, local_vars)
                                    for k in call.keywords
                                    if k.arg
                                }
                                rec: Dict[str, Any] = {
                                    "subcommand": sub_name,
                                    "parser_variable": var_name,
                                    "defined_at_line": stmt.lineno,
                                    "allow_abbrev": kw.get("allow_abbrev"),
                                    "help": kw.get("help") if kw.get("help") is not None else "none",
                                    "arguments": [],
                                }
                                subcommands.append(rec)
                                subcmd_by_var[var_name] = rec
                    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        call = stmt.value
                        if isinstance(call.func, ast.Attribute) and call.func.attr == "add_argument":
                            target_ref = eval_ast_expr(call.func.value, local_vars)
                            if isinstance(target_ref, str) and target_ref in subcmd_by_var:
                                rec = subcmd_by_var[target_ref]
                            elif isinstance(target_ref, dict):
                                rec = target_ref
                            else:
                                continue
                            flags = [str(eval_ast_expr(a, local_vars)) for a in call.args]
                            kw = {
                                k.arg: eval_ast_expr(k.value, local_vars)
                                for k in call.keywords
                                if k.arg
                            }
                            dest = kw.get("dest")
                            if not dest:
                                long_flags = [f for f in flags if f.startswith("--")]
                                chosen = long_flags[0] if long_flags else flags[0]
                                dest = chosen.lstrip("-").replace("-", "_")
                            rec["arguments"].append(
                                {
                                    "flags": flags,
                                    "dest": str(dest),
                                    "required": bool(kw.get("required", False)),
                                    "type": str(kw["type"]) if "type" in kw else "str",
                                    "help": str(kw["help"]) if kw.get("help") is not None else "none",
                                    "defined_at_line": stmt.lineno,
                                }
                            )
                    elif isinstance(stmt, ast.For) and isinstance(stmt.target, ast.Name):
                        loop_var = stmt.target.id
                        iter_items = eval_ast_expr(stmt.iter, local_vars)
                        for item in iter_items:
                            next_vars = dict(local_vars)
                            if (
                                isinstance(item, str)
                                and item in subcmd_by_var
                                and loop_var == "command"
                            ):
                                next_vars[loop_var] = subcmd_by_var[item]
                            else:
                                next_vars[loop_var] = item
                            walk_stmts(stmt.body, next_vars)

            walk_stmts(node.body, {})

    unique_destinations: List[str] = []
    for sub in subcommands:
        for arg in sub["arguments"]:
            if arg["dest"] not in unique_destinations:
                unique_destinations.append(arg["dest"])

    lines = source_text.splitlines()
    destination_usages: List[Dict[str, Any]] = []
    subparser_dest = str(subparsers_info.get("dest", "command"))
    all_destinations = [subparser_dest] + unique_destinations

    for dest in all_destinations:
        pattern = re.compile(rf"\bargs\.{re.escape(dest)}\b")
        occurrences: List[Dict[str, Any]] = []
        for line_no, raw_line in enumerate(lines, 1):
            if pattern.search(raw_line):
                occurrences.append(
                    {
                        "line": line_no,
                        "stripped_line": raw_line.strip(),
                    }
                )
        subcommands_with_dest = [
            s["subcommand"]
            for s in subcommands
            if any(a["dest"] == dest for a in s["arguments"])
        ]
        destination_usages.append(
            {
                "destination": dest,
                "is_subparser_selector": dest == subparser_dest,
                "subcommands_declaring_destination": (
                    [s["subcommand"] for s in subcommands]
                    if dest == subparser_dest
                    else subcommands_with_dest
                ),
                "occurrence_count": len(occurrences),
                "occurrences": occurrences,
            }
        )

    return {
        "subparsers": subparsers_info,
        "subcommands": subcommands,
        "unique_argument_destinations": unique_destinations,
        "destination_usages": destination_usages,
    }


def parse_grep_line(raw_line: str, commit: str, word: str) -> Dict[str, Any]:
    prefix = f"{commit}:"
    if not raw_line.startswith(prefix):
        raise ValueError(f"Unexpected git grep line prefix: {raw_line}")
    rest = raw_line[len(prefix) :]
    file_path, line_str, def_line = rest.split(":", 2)
    stripped = def_line.strip()
    m = re.match(r"^def\s+([A-Za-z0-9_]+)", stripped)
    func_name = m.group(1) if m else ""
    return {
        "word": word,
        "file": file_path,
        "line": int(line_str),
        "function_name": func_name,
        "stripped_line": stripped,
    }


def git_grep_word(repo: Path, commit: str, word: str, pathspecs: List[str]) -> List[Dict[str, Any]]:
    pattern = rf"^\s*def [A-Za-z0-9_]*{word}"
    res = subprocess.run(
        ["git", "-C", str(repo), "grep", "-n", "-E", pattern, commit, "--"] + pathspecs,
        env=git_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode not in (0, 1):
        raise RuntimeError(f"git grep failed for word={word}, pathspecs={pathspecs}: {res.stderr}")
    rows: List[Dict[str, Any]] = []
    for raw_line in res.stdout.splitlines():
        if raw_line.strip():
            rows.append(parse_grep_line(raw_line, commit, word))
    return rows


def collect_builders(repo: Path, commit: str) -> Dict[str, Any]:
    by_word: List[Dict[str, Any]] = []
    non_test_src_scripts_all: List[Dict[str, Any]] = []
    embedded_test_in_scripts_all: List[Dict[str, Any]] = []
    top_level_tests_all: List[Dict[str, Any]] = []
    fixture_builders_tests_utils_all: List[Dict[str, Any]] = []

    for word in BUILDER_WORDS:
        src_scripts_hits = git_grep_word(repo, commit, word, ["src/", "scripts/"])
        non_test_hits = [
            h for h in src_scripts_hits if not h["file"].startswith("tests/") and "/tests/" not in h["file"]
        ]
        embedded_test_hits = [
            h for h in src_scripts_hits if h["file"].startswith("tests/") or "/tests/" in h["file"]
        ]
        top_tests_hits = git_grep_word(repo, commit, word, ["tests/"])
        fixture_utils_hits = git_grep_word(repo, commit, word, ["tests/utils/"])

        non_test_src_scripts_all.extend(non_test_hits)
        embedded_test_in_scripts_all.extend(embedded_test_hits)
        top_level_tests_all.extend(top_tests_hits)
        fixture_builders_tests_utils_all.extend(fixture_utils_hits)

        by_word.append(
            {
                "word": word,
                "pattern": rf"^\s*def [A-Za-z0-9_]*{word}",
                "src_and_scripts_total_count": len(src_scripts_hits),
                "non_test_paths_count": len(non_test_hits),
                "embedded_test_paths_in_scripts_count": len(embedded_test_hits),
                "top_level_tests_paths_count": len(top_tests_hits),
                "combined_test_paths_count": len(embedded_test_hits) + len(top_tests_hits),
                "fixture_builders_tests_utils_count": len(fixture_utils_hits),
                "non_test_paths": non_test_hits,
                "embedded_test_paths_in_scripts": embedded_test_hits,
                "top_level_tests_paths": top_tests_hits,
                "fixture_builders_tests_utils": fixture_utils_hits,
            }
        )

    unique_non_test_defs = sorted(
        {(h["file"], h["line"], h["function_name"]) for h in non_test_src_scripts_all}
    )
    unique_src_scripts_all_defs = sorted(
        {
            (h["file"], h["line"], h["function_name"])
            for h in (non_test_src_scripts_all + embedded_test_in_scripts_all)
        }
    )
    unique_embedded_test_defs = sorted(
        {(h["file"], h["line"], h["function_name"]) for h in embedded_test_in_scripts_all}
    )
    unique_top_tests_defs = sorted(
        {(h["file"], h["line"], h["function_name"]) for h in top_level_tests_all}
    )
    unique_fixture_utils_defs = sorted(
        {(h["file"], h["line"], h["function_name"]) for h in fixture_builders_tests_utils_all}
    )

    return {
        "words": BUILDER_WORDS,
        "by_word": by_word,
        "totals": {
            "non_test_word_matches_count": len(non_test_src_scripts_all),
            "non_test_unique_functions_count": len(unique_non_test_defs),
            "src_and_scripts_all_word_matches_count": len(non_test_src_scripts_all)
            + len(embedded_test_in_scripts_all),
            "src_and_scripts_all_unique_functions_count": len(unique_src_scripts_all_defs),
            "embedded_test_in_scripts_word_matches_count": len(embedded_test_in_scripts_all),
            "embedded_test_in_scripts_unique_functions_count": len(unique_embedded_test_defs),
            "top_level_tests_word_matches_count": len(top_level_tests_all),
            "top_level_tests_unique_functions_count": len(unique_top_tests_defs),
            "all_test_paths_word_matches_count": len(embedded_test_in_scripts_all)
            + len(top_level_tests_all),
            "all_test_paths_unique_functions_count": len(unique_embedded_test_defs)
            + len(unique_top_tests_defs),
            "fixture_builders_tests_utils_word_matches_count": len(
                fixture_builders_tests_utils_all
            ),
            "fixture_builders_tests_utils_unique_functions_count": len(
                unique_fixture_utils_defs
            ),
        },
    }


def esc(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("`", "'")


def render_markdown(payload: Dict[str, Any]) -> str:
    counts = payload["counts"]
    cli = payload["cli"]
    builders = payload["builders"]

    lines: List[str] = []
    lines.append("# Production Native Launch Inputs and Builder Inventory (2026-11-12)")
    lines.append("")
    lines.append("## Command and Provenance")
    lines.append("")
    lines.append("- Assignment file: `" + str(ASSIGNMENT_PATH) + "`")
    lines.append("- Extraction script: `" + str(SCRIPT_PATH) + "`")
    lines.append("- Structured JSON output: `" + str(DEFAULT_JSON_OUT) + "`")
    lines.append("- Markdown handoff output: `" + str(DEFAULT_MD_OUT) + "`")
    lines.append("- Repository git object store: `" + str(REPO_PATH) + "`")
    lines.append("- Commit read via git show and git grep: " + payload["commit"])
    lines.append("- CLI module parsed with Python ast: " + payload["target_file"])
    lines.append("")
    lines.append("```bash")
    lines.append(f"python3 {SCRIPT_PATH}")
    lines.append("```")
    lines.append("")
    lines.append("## Summary Counts")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---:|")
    lines.append(f"| Subcommands in native_generation.py | {counts['subcommands_count']} |")
    lines.append(
        f"| Total subcommand argument registrations across subcommands | {counts['subcommand_argument_registrations_count']} |"
    )
    lines.append(
        f"| Unique subcommand argument destinations (excluding subparser selector command) | {counts['unique_argument_destinations_count']} |"
    )
    lines.append(
        f"| Unique argument destinations including subparser selector command | {counts['unique_destinations_including_command_count']} |"
    )
    lines.append(
        f"| Total args.<destination> line occurrences (19 argument destinations) | {counts['argument_destination_line_occurrences_count']} |"
    )
    lines.append(
        f"| Total args.<destination> line occurrences (including args.command) | {counts['all_destination_line_occurrences_including_command_count']} |"
    )
    lines.append(
        f"| Builder search words | {counts['builder_words_count']} |"
    )
    lines.append(
        f"| Builder function word-matches outside tests (src/ and scripts/ excluding */tests/*) | {counts['builder_functions_outside_tests_word_matches_count']} |"
    )
    lines.append(
        f"| Unique builder functions outside tests (src/ and scripts/ excluding */tests/*) | {counts['builder_functions_outside_tests_unique_count']} |"
    )
    lines.append(
        f"| Builder function word-matches in all of src/ and scripts/ (including scripts/.../tests/*) | {counts['builder_functions_src_and_scripts_all_word_matches_count']} |"
    )
    lines.append(
        f"| Unique builder functions in all of src/ and scripts/ (including scripts/.../tests/*) | {counts['builder_functions_src_and_scripts_all_unique_count']} |"
    )
    lines.append(
        f"| Builder function word-matches in scripts/.../tests/* | {counts['builder_functions_embedded_tests_in_scripts_word_matches_count']} |"
    )
    lines.append(
        f"| Builder function word-matches in top-level tests/ | {counts['builder_functions_top_level_tests_word_matches_count']} |"
    )
    lines.append(
        f"| Unique builder functions in top-level tests/ | {counts['builder_functions_top_level_tests_unique_count']} |"
    )
    lines.append(
        f"| Fixture builder word-matches in tests/utils/ | {counts['fixture_builders_tests_utils_word_matches_count']} |"
    )
    lines.append(
        f"| Unique fixture builder functions in tests/utils/ | {counts['fixture_builders_tests_utils_unique_count']} |"
    )
    lines.append("")
    lines.append("## 1. Subcommands and Arguments in src/data_sheets_schema/native_generation.py")
    lines.append("")
    lines.append("### 1A. Subcommands")
    lines.append("")
    lines.append("| # | Subcommand | Parser Variable | Defined Line | Argument Count | Subcommand Help Text |")
    lines.append("|---:|---|---|---:|---:|---|")
    for idx, sub in enumerate(cli["subcommands"], 1):
        lines.append(
            f"| {idx} | {esc(sub['subcommand'])} | {esc(sub['parser_variable'])} | {sub['defined_at_line']} | {len(sub['arguments'])} | {esc(sub['help'])} |"
        )
    lines.append("")
    lines.append("### 1B. Arguments per Subcommand")
    lines.append("")
    lines.append("| Subcommand | Flags | Destination | Required | Type | Defined Line | Help Text |")
    lines.append("|---|---|---|---|---|---:|---|")
    for sub in cli["subcommands"]:
        for arg in sub["arguments"]:
            flags_str = ", ".join(arg["flags"])
            req_str = "yes" if arg["required"] else "no"
            lines.append(
                f"| {esc(sub['subcommand'])} | {esc(flags_str)} | {esc(arg['dest'])} | {req_str} | {esc(arg['type'])} | {arg['defined_at_line']} | {esc(arg['help'])} |"
            )

    lines.append("")
    lines.append("## 2. Where Each Argument Destination Is Used (args.<destination>)")
    lines.append("")
    lines.append("| Destination | Declared On Subcommands | Line | Stripped Line |")
    lines.append("|---|---|---:|---|")
    for usage in cli["destination_usages"]:
        dest = usage["destination"]
        subs_str = ", ".join(usage["subcommands_declaring_destination"])
        if not usage["occurrences"]:
            lines.append(f"| {esc(dest)} | {esc(subs_str)} | none | none |")
        else:
            for occ in usage["occurrences"]:
                lines.append(
                    f"| {esc(dest)} | {esc(subs_str)} | {occ['line']} | {esc(occ['stripped_line'])} |"
                )

    lines.append("")
    lines.append("## 3. Builder Function Definitions by Word")
    lines.append("")
    lines.append("### 3A. Counts per Word Across Path Categories")
    lines.append("")
    lines.append(
        "| Word | Regex Pattern | Non-Test Paths (src/ and scripts/ excluding */tests/*) | Test Paths Inside scripts/ (scripts/.../tests/*) | All src/ and scripts/ | Top-Level tests/ | All Test Paths Combined | Fixture Builders (tests/utils/) |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for wrec in builders["by_word"]:
        lines.append(
            f"| {esc(wrec['word'])} | {esc(wrec['pattern'])} | {wrec['non_test_paths_count']} | {wrec['embedded_test_paths_in_scripts_count']} | {wrec['src_and_scripts_total_count']} | {wrec['top_level_tests_paths_count']} | {wrec['combined_test_paths_count']} | {wrec['fixture_builders_tests_utils_count']} |"
        )

    lines.append("")
    lines.append("### 3B. Non-Test Paths in src/ and scripts/ (Excluding */tests/*)")
    lines.append("")
    lines.append("| Word | File | Line | Function Name | Stripped Definition Line |")
    lines.append("|---|---|---:|---|---|")
    for wrec in builders["by_word"]:
        word = wrec["word"]
        if not wrec["non_test_paths"]:
            lines.append(f"| {esc(word)} | none | none | none | none |")
        else:
            for h in wrec["non_test_paths"]:
                lines.append(
                    f"| {esc(word)} | {esc(h['file'])} | {h['line']} | {esc(h['function_name'])} | {esc(h['stripped_line'])} |"
                )

    lines.append("")
    lines.append("### 3C. Test Paths Inside scripts/ (scripts/.../tests/*)")
    lines.append("")
    lines.append("| Word | File | Line | Function Name | Stripped Definition Line |")
    lines.append("|---|---|---:|---|---|")
    for wrec in builders["by_word"]:
        word = wrec["word"]
        if not wrec["embedded_test_paths_in_scripts"]:
            lines.append(f"| {esc(word)} | none | none | none | none |")
        else:
            for h in wrec["embedded_test_paths_in_scripts"]:
                lines.append(
                    f"| {esc(word)} | {esc(h['file'])} | {h['line']} | {esc(h['function_name'])} | {esc(h['stripped_line'])} |"
                )

    lines.append("")
    lines.append("### 3D. Test Paths in Top-Level tests/")
    lines.append("")
    lines.append("| Word | File | Line | Function Name | Stripped Definition Line |")
    lines.append("|---|---|---:|---|---|")
    for wrec in builders["by_word"]:
        word = wrec["word"]
        if not wrec["top_level_tests_paths"]:
            lines.append(f"| {esc(word)} | none | none | none | none |")
        else:
            for h in wrec["top_level_tests_paths"]:
                lines.append(
                    f"| {esc(word)} | {esc(h['file'])} | {h['line']} | {esc(h['function_name'])} | {esc(h['stripped_line'])} |"
                )

    lines.append("")
    lines.append("## 4. Fixture Builders in tests/utils/")
    lines.append("")
    lines.append("| Word | File | Line | Function Name | Stripped Definition Line |")
    lines.append("|---|---|---:|---|---|")
    for wrec in builders["by_word"]:
        word = wrec["word"]
        if not wrec["fixture_builders_tests_utils"]:
            lines.append(f"| {esc(word)} | none | none | none | none |")
        else:
            for h in wrec["fixture_builders_tests_utils"]:
                lines.append(
                    f"| {esc(word)} | {esc(h['file'])} | {h['line']} | {esc(h['function_name'])} | {esc(h['stripped_line'])} |"
                )

    lines.append("")
    content = "\n".join(lines)
    if "\x40" in content:
        raise RuntimeError("Generated Markdown contains a forbidden at-sign character")
    return content


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract native launch CLI inputs and candidate builder functions at 1a137b58."
    )
    parser.add_argument("--repo", type=Path, default=REPO_PATH)
    parser.add_argument("--commit", type=str, default=TARGET_COMMIT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument(
        "--skip-target-backtick-check",
        action="store_true",
        help="Skip checking DEFAULT_JSON_OUT/DEFAULT_MD_OUT existence when writing to /tmp first.",
    )
    args = parser.parse_args()

    verify_commit_present(args.repo, args.commit)
    source_text = git_show_file(args.repo, args.commit, TARGET_FILE)
    cli_data = parse_commands_and_arguments(source_text)
    builder_data = collect_builders(args.repo, args.commit)

    arg_dest_occ_count = sum(
        u["occurrence_count"]
        for u in cli_data["destination_usages"]
        if not u["is_subparser_selector"]
    )
    all_dest_occ_count = sum(
        u["occurrence_count"] for u in cli_data["destination_usages"]
    )

    counts = {
        "subcommands_count": len(cli_data["subcommands"]),
        "subcommand_argument_registrations_count": sum(
            len(s["arguments"]) for s in cli_data["subcommands"]
        ),
        "unique_argument_destinations_count": len(cli_data["unique_argument_destinations"]),
        "unique_destinations_including_command_count": len(cli_data["destination_usages"]),
        "argument_destination_line_occurrences_count": arg_dest_occ_count,
        "all_destination_line_occurrences_including_command_count": all_dest_occ_count,
        "builder_words_count": len(BUILDER_WORDS),
        "builder_functions_outside_tests_word_matches_count": builder_data["totals"][
            "non_test_word_matches_count"
        ],
        "builder_functions_outside_tests_unique_count": builder_data["totals"][
            "non_test_unique_functions_count"
        ],
        "builder_functions_src_and_scripts_all_word_matches_count": builder_data["totals"][
            "src_and_scripts_all_word_matches_count"
        ],
        "builder_functions_src_and_scripts_all_unique_count": builder_data["totals"][
            "src_and_scripts_all_unique_functions_count"
        ],
        "builder_functions_embedded_tests_in_scripts_word_matches_count": builder_data[
            "totals"
        ]["embedded_test_in_scripts_word_matches_count"],
        "builder_functions_embedded_tests_in_scripts_unique_count": builder_data["totals"][
            "embedded_test_in_scripts_unique_functions_count"
        ],
        "builder_functions_top_level_tests_word_matches_count": builder_data["totals"][
            "top_level_tests_word_matches_count"
        ],
        "builder_functions_top_level_tests_unique_count": builder_data["totals"][
            "top_level_tests_unique_functions_count"
        ],
        "builder_functions_all_test_paths_word_matches_count": builder_data["totals"][
            "all_test_paths_word_matches_count"
        ],
        "builder_functions_all_test_paths_unique_count": builder_data["totals"][
            "all_test_paths_unique_functions_count"
        ],
        "fixture_builders_tests_utils_word_matches_count": builder_data["totals"][
            "fixture_builders_tests_utils_word_matches_count"
        ],
        "fixture_builders_tests_utils_unique_count": builder_data["totals"][
            "fixture_builders_tests_utils_unique_functions_count"
        ],
    }

    payload: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "task_id": "claude-lead-agy2-native-launch-inputs-20261112",
        "date": "2026-11-12",
        "repository_path": str(args.repo),
        "report_worktree_path": str(WORKTREE_ROOT),
        "commit": args.commit,
        "target_file": TARGET_FILE,
        "counts": counts,
        "cli": cli_data,
        "builders": builder_data,
    }

    json_text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    if "\x40" in json_text:
        raise RuntimeError("Generated JSON contains a forbidden at-sign character")

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json_text, encoding="utf-8")

    reloaded = json.loads(args.json_out.read_text(encoding="utf-8"))
    md_text = render_markdown(reloaded)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.write_text(md_text, encoding="utf-8")

    if not args.skip_target_backtick_check:
        for m in re.finditer(r"`([^`\n]+)`", md_text):
            token = m.group(1)
            if not Path(token).exists():
                raise RuntimeError(f"Backticked path does not exist: {token}")

    print(f"SCRIPT_PATH={SCRIPT_PATH} SHA256={sha256_file(SCRIPT_PATH)}")
    print(f"JSON_OUT={args.json_out} SHA256={sha256_file(args.json_out)}")
    print(f"MD_OUT={args.md_out} SHA256={sha256_file(args.md_out)}")


if __name__ == "__main__":
    main()
