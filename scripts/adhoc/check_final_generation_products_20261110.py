#!/usr/bin/env python3
"""
Purpose:
    Compare base 7233f193ad102a8488b31ec7333662c8fefaa996 Git blobs against G2
    generated products for the large generated-diff/reordering artifacts:
      1. project/owl/data_sheets_schema.owl.ttl:
         Verify RDF graph isomorphism (rdflib.compare.isomorphic called once,
         with rdflib.NORMALIZE_LITERALS=False) after ONLY the expected schema
         version ("3.2.0" -> "3.2.1") and collection_type description literal
         substitutions, capturing the exact allowed changes.
      2. src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv
         and src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_uri_comprehensive.tsv:
         Compare all rows ignoring mapping_date, requiring every row except
         collection_type to be unchanged and recording the observed
         free_text -> unmapped keyword-heuristic shift on collection_type
         (same sssom:NoTermFound non-mapping, not a new curated mapping).

Inputs:
    - Base Git revision blobs read via git show (default:
      7233f193ad102a8488b31ec7333662c8fefaa996).
    - Integrated worktree files via --g2-root (default:
      /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-generation-readiness-20261110).

Outputs:
    - Fresh JSON report written to caller-specified scratch path (--output or
      --scratch-dir). Refuses to overwrite an existing file.

Related issue:
    - bridge2ai/data-sheets-schema#2975

Date:
    2026-11-10
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from typing import Any

import rdflib
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import isomorphic


DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_BASE_REV = "7233f193ad102a8488b31ec7333662c8fefaa996"
DEFAULT_LEAD_ROOT = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/"
    "codex-final-generation-readiness-20261110"
)
DEFAULT_G2_ROOT = DEFAULT_LEAD_ROOT
DEFAULT_SCRATCH_DIR = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/"
    "scratch-final-readiness-lead-20261110"
)

OWL_RELPATH = "project/owl/data_sheets_schema.owl.ttl"
SSSOM_COMPREHENSIVE_RELPATH = (
    "src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv"
)
SSSOM_URI_COMPREHENSIVE_RELPATH = (
    "src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_uri_comprehensive.tsv"
)

ONTOLOGY_URI = URIRef("https://w3id.org/bridge2ai/data-sheets-schema")
PAV_VERSION_URI = URIRef("http://purl.org/pav/version")
COLLECTION_TYPE_URI = URIRef(
    "https://w3id.org/bridge2ai/data-sheets-schema/collection_type"
)
SKOS_DEFINITION_URI = URIRef("http://www.w3.org/2004/02/skos/core#definition")

EXPECTED_OLD_VERSION = "3.2.0"
EXPECTED_NEW_VERSION = "3.2.1"

EXPECTED_OLD_COLLECTION_TYPE_DESC = (
    "Type(s) of content in this file collection. A collection may have "
    "multiple types, for example a collection containing both raw_data and "
    "documentation files would have both types listed."
)
EXPECTED_NEW_COLLECTION_TYPE_DESC = (
    "Primary content classification for this file collection from "
    "FileCollectionTypeEnum. Each FileCollection has one collection_type "
    "value; represent differently classified file groups as separate "
    "FileCollection entries in the dataset\x27s file_collections."
)


def git_env() -> dict[str, str]:
    env = dict(os.environ)
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def resolve_commit_sha(git_repo: Path, rev: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(git_repo), "rev-parse", f"{rev}^{{commit}}"],
        env=git_env(),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def read_git_blob_text(git_repo: Path, rev: str, relpath: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(git_repo), "show", f"{rev}:{relpath}"],
        env=git_env(),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def triple_to_dict(triple: tuple[Any, Any, Any]) -> dict[str, str]:
    s, p, o = triple
    return {
        "subject": str(s),
        "predicate": str(p),
        "object": str(o),
        "object_type": "bnode"
        if isinstance(o, BNode)
        else ("literal" if isinstance(o, Literal) else "uri"),
    }


def ground_triples(graph: Graph) -> set[tuple[Any, Any, Any]]:
    return {
        t
        for t in graph
        if not isinstance(t[0], BNode)
        and not isinstance(t[1], BNode)
        and not isinstance(t[2], BNode)
    }


def check_owl_isomorphism(git_repo: Path, base_rev: str, g2_root: Path) -> dict[str, Any]:
    base_ttl = read_git_blob_text(git_repo, base_rev, OWL_RELPATH)
    g2_path = g2_root / OWL_RELPATH
    g2_ttl = g2_path.read_text(encoding="utf-8")

    prev_normalize = rdflib.NORMALIZE_LITERALS
    rdflib.NORMALIZE_LITERALS = False
    try:
        base_graph = Graph()
        base_graph.parse(data=base_ttl, format="turtle")

        g2_graph = Graph()
        g2_graph.parse(data=g2_ttl, format="turtle")

        expected_old_triples = {
            (ONTOLOGY_URI, PAV_VERSION_URI, Literal(EXPECTED_OLD_VERSION)),
            (
                COLLECTION_TYPE_URI,
                SKOS_DEFINITION_URI,
                Literal(EXPECTED_OLD_COLLECTION_TYPE_DESC),
            ),
        }
        expected_new_triples = {
            (ONTOLOGY_URI, PAV_VERSION_URI, Literal(EXPECTED_NEW_VERSION)),
            (
                COLLECTION_TYPE_URI,
                SKOS_DEFINITION_URI,
                Literal(EXPECTED_NEW_COLLECTION_TYPE_DESC),
            ),
        }
    finally:
        rdflib.NORMALIZE_LITERALS = prev_normalize

    base_ground = ground_triples(base_graph)
    g2_ground = ground_triples(g2_graph)

    ground_only_in_base = base_ground - g2_ground
    ground_only_in_g2 = g2_ground - base_ground

    unexpected_ground_in_base = ground_only_in_base - expected_old_triples
    unexpected_ground_in_g2 = ground_only_in_g2 - expected_new_triples
    missing_expected_old = expected_old_triples - ground_only_in_base
    missing_expected_new = expected_new_triples - ground_only_in_g2

    substituted_base = Graph()
    for triple in base_graph:
        substituted_base.add(triple)

    for old_triple in expected_old_triples:
        substituted_base.remove(old_triple)
    for new_triple in expected_new_triples:
        substituted_base.add(new_triple)

    iso_after_sub = isomorphic(substituted_base, g2_graph)

    passed = (
        len(base_graph) == len(g2_graph)
        and not unexpected_ground_in_base
        and not unexpected_ground_in_g2
        and not missing_expected_old
        and not missing_expected_new
        and iso_after_sub
    )

    return {
        "relpath": OWL_RELPATH,
        "g2_path": str(g2_path),
        "passed": passed,
        "normalize_literals": False,
        "base_triple_count": len(base_graph),
        "g2_triple_count": len(g2_graph),
        "expected_substitutions": [
            {
                "subject": str(ONTOLOGY_URI),
                "predicate": str(PAV_VERSION_URI),
                "old_literal": EXPECTED_OLD_VERSION,
                "new_literal": EXPECTED_NEW_VERSION,
            },
            {
                "subject": str(COLLECTION_TYPE_URI),
                "predicate": str(SKOS_DEFINITION_URI),
                "old_literal": EXPECTED_OLD_COLLECTION_TYPE_DESC,
                "new_literal": EXPECTED_NEW_COLLECTION_TYPE_DESC,
            },
        ],
        "ground_triples_only_in_base": [
            triple_to_dict(t) for t in sorted(ground_only_in_base, key=str)
        ],
        "ground_triples_only_in_g2": [
            triple_to_dict(t) for t in sorted(ground_only_in_g2, key=str)
        ],
        "unexpected_ground_triples_in_base": [
            triple_to_dict(t) for t in sorted(unexpected_ground_in_base, key=str)
        ],
        "unexpected_ground_triples_in_g2": [
            triple_to_dict(t) for t in sorted(unexpected_ground_in_g2, key=str)
        ],
        "isomorphic_after_expected_substitutions": iso_after_sub,
    }


def parse_sssom_tsv(text: str) -> tuple[dict[str, Any], list[str], list[dict[str, str]]]:
    comments: list[str] = []
    data_lines: list[str] = []
    status_breakdown: dict[str, int] = {}
    header_date: str | None = None
    in_status_block = False

    for line in text.splitlines():
        if line.startswith("#"):
            comments.append(line)
            stripped = line[1:].strip()
            if stripped.startswith("Date:"):
                header_date = stripped.split("Date:", 1)[1].strip()
                in_status_block = False
            elif stripped == "Status breakdown:":
                in_status_block = True
            elif in_status_block and ":" in stripped:
                k, v = stripped.split(":", 1)
                k = k.strip()
                v = v.strip()
                if v.isdigit():
                    status_breakdown[k] = int(v)
                else:
                    in_status_block = False
            elif stripped == "":
                in_status_block = False
        else:
            data_lines.append(line)

    reader = csv.DictReader(io.StringIO("\n".join(data_lines)), delimiter="\t")
    fieldnames = list(reader.fieldnames or [])
    rows = [dict(row) for row in reader]
    meta = {
        "comments": comments,
        "comment_line_count": len(comments),
        "header_date": header_date,
        "status_breakdown": status_breakdown,
    }
    return meta, fieldnames, rows


def compare_comment_headers(
    base_comments: list[str], g2_comments: list[str]
) -> dict[str, Any]:
    allowed_diffs: list[dict[str, Any]] = []
    unexpected_diffs: list[dict[str, Any]] = []
    saw_free_text_shift = False
    saw_unmapped_shift = False

    if len(base_comments) != len(g2_comments):
        unexpected_diffs.append(
            {
                "reason": "comment_line_count_mismatch",
                "base_count": len(base_comments),
                "g2_count": len(g2_comments),
            }
        )
    else:
        for idx, (b_line, g_line) in enumerate(
            zip(base_comments, g2_comments), start=1
        ):
            if b_line == g_line:
                continue
            if b_line.startswith("# Date: ") and g_line.startswith("# Date: "):
                allowed_diffs.append(
                    {"line": idx, "kind": "date", "base": b_line, "g2": g_line}
                )
            elif (b_line, g_line) == ("#   free_text: 13", "#   free_text: 12"):
                saw_free_text_shift = True
                allowed_diffs.append(
                    {
                        "line": idx,
                        "kind": "status_free_text",
                        "base": b_line,
                        "g2": g_line,
                    }
                )
            elif (b_line, g_line) == ("#   unmapped: 84", "#   unmapped: 85"):
                saw_unmapped_shift = True
                allowed_diffs.append(
                    {
                        "line": idx,
                        "kind": "status_unmapped",
                        "base": b_line,
                        "g2": g_line,
                    }
                )
            else:
                unexpected_diffs.append(
                    {"line": idx, "base": b_line, "g2": g_line}
                )

    passed = (
        len(base_comments) == len(g2_comments)
        and not unexpected_diffs
        and saw_free_text_shift
        and saw_unmapped_shift
    )
    return {
        "passed": passed,
        "base_comment_lines": base_comments,
        "g2_comment_lines": g2_comments,
        "allowed_comment_diffs": allowed_diffs,
        "unexpected_comment_diffs": unexpected_diffs,
        "saw_exact_free_text_13_to_12": saw_free_text_shift,
        "saw_exact_unmapped_84_to_85": saw_unmapped_shift,
    }


def compare_sssom_table(
    git_repo: Path,
    base_rev: str,
    g2_root: Path,
    relpath: str,
    key_column: str,
    collection_type_key: str,
    expected_changes: dict[str, dict[str, str]],
) -> dict[str, Any]:
    base_text = read_git_blob_text(git_repo, base_rev, relpath)
    g2_path = g2_root / relpath
    g2_text = g2_path.read_text(encoding="utf-8")

    base_meta, base_fields, base_rows = parse_sssom_tsv(base_text)
    g2_meta, g2_fields, g2_rows = parse_sssom_tsv(g2_text)
    comment_header_comparison = compare_comment_headers(
        base_meta["comments"], g2_meta["comments"]
    )

    base_keys = [r[key_column] for r in base_rows]
    g2_keys = [r[key_column] for r in g2_rows]

    base_by_key = {r[key_column]: r for r in base_rows}
    g2_by_key = {r[key_column]: r for r in g2_rows}

    non_collection_type_diffs: list[dict[str, Any]] = []
    collection_type_diffs: dict[str, dict[str, str]] = {}

    if base_fields == g2_fields and base_keys == g2_keys:
        for row_key in base_keys:
            b_row = base_by_key[row_key]
            g_row = g2_by_key[row_key]
            row_diff: dict[str, dict[str, str]] = {}
            for col in base_fields:
                if col == "mapping_date":
                    continue
                if b_row.get(col, "") != g_row.get(col, ""):
                    row_diff[col] = {
                        "base": b_row.get(col, ""),
                        "g2": g_row.get(col, ""),
                    }
            if row_key == collection_type_key:
                collection_type_diffs = row_diff
            elif row_diff:
                non_collection_type_diffs.append(
                    {"row_key": row_key, "changed_columns": row_diff}
                )

    unexpected_collection_type_changes = {
        col: vals
        for col, vals in collection_type_diffs.items()
        if expected_changes.get(col) != vals
    }
    missing_expected_collection_type_changes = {
        col: vals
        for col, vals in expected_changes.items()
        if collection_type_diffs.get(col) != vals
    }

    base_ct = base_by_key.get(collection_type_key, {})
    g2_ct = g2_by_key.get(collection_type_key, {})

    same_no_term_found = (
        base_ct.get("predicate_id") == "skos:exactMatch"
        and g2_ct.get("predicate_id") == "skos:exactMatch"
        and base_ct.get("object_id") == "sssom:NoTermFound"
        and g2_ct.get("object_id") == "sssom:NoTermFound"
        and base_ct.get("mapping_justification") == "semapv:UnspecifiedMatching"
        and g2_ct.get("mapping_justification") == "semapv:UnspecifiedMatching"
        and base_ct.get("confidence") == "0.0"
        and g2_ct.get("confidence") == "0.0"
        and base_ct.get("other_curated_mappings")
        == "skos:exactMatch d4d:collectionType (ttl d4d:FileCollection_collection_type)"
        and g2_ct.get("other_curated_mappings")
        == "skos:exactMatch d4d:collectionType (ttl d4d:FileCollection_collection_type)"
    )

    expected_status_shift_ok = (
        base_meta["status_breakdown"].get("free_text") == 13
        and g2_meta["status_breakdown"].get("free_text") == 12
        and base_meta["status_breakdown"].get("unmapped") == 84
        and g2_meta["status_breakdown"].get("unmapped") == 85
        and base_meta["status_breakdown"].get("mapped")
        == g2_meta["status_breakdown"].get("mapped")
        and base_meta["status_breakdown"].get("novel_d4d")
        == g2_meta["status_breakdown"].get("novel_d4d")
        and base_meta["status_breakdown"].get("recommended")
        == g2_meta["status_breakdown"].get("recommended")
    )

    passed = (
        comment_header_comparison["passed"]
        and base_fields == g2_fields
        and len(base_rows) == len(g2_rows)
        and base_keys == g2_keys
        and len(non_collection_type_diffs) == 0
        and not unexpected_collection_type_changes
        and not missing_expected_collection_type_changes
        and same_no_term_found
        and expected_status_shift_ok
    )

    return {
        "relpath": relpath,
        "g2_path": str(g2_path),
        "passed": passed,
        "row_count_base": len(base_rows),
        "row_count_g2": len(g2_rows),
        "fieldnames_identical": base_fields == g2_fields,
        "row_key_order_identical": base_keys == g2_keys,
        "ignored_columns": ["mapping_date"],
        "comment_header_comparison": comment_header_comparison,
        "header_date": {
            "base": base_meta["header_date"],
            "g2": g2_meta["header_date"],
        },
        "status_breakdown": {
            "base": base_meta["status_breakdown"],
            "g2": g2_meta["status_breakdown"],
            "expected_free_text_to_unmapped_shift_verified": expected_status_shift_ok,
        },
        "non_collection_type_changed_row_count": len(non_collection_type_diffs),
        "non_collection_type_changed_rows": non_collection_type_diffs,
        "collection_type_row_key": collection_type_key,
        "collection_type_observed_changes_ignoring_mapping_date": collection_type_diffs,
        "unexpected_collection_type_changes": unexpected_collection_type_changes,
        "missing_expected_collection_type_changes": missing_expected_collection_type_changes,
        "collection_type_heuristic_transition": {
            "mapping_status": {
                "base": base_ct.get("mapping_status"),
                "g2": g2_ct.get("mapping_status"),
            },
            "mapping_source": {
                "base": base_ct.get("mapping_source"),
                "g2": g2_ct.get("mapping_source"),
            },
            "heuristic_hint": {
                "base": base_ct.get("heuristic_hint"),
                "g2": g2_ct.get("heuristic_hint"),
            },
            "same_no_term_found": same_no_term_found,
            "new_curated_mapping_introduced": False if same_no_term_found else True,
            "invariant_alignment_fields": {
                "predicate_id": g2_ct.get("predicate_id"),
                "object_id": g2_ct.get("object_id"),
                "mapping_justification": g2_ct.get("mapping_justification"),
                "confidence": g2_ct.get("confidence"),
                "other_curated_mappings": g2_ct.get("other_curated_mappings"),
            },
            "cause": (
                "Old collection_type description contained the substring "
                "\"documentation\" (matched by FREE_TEXT_KEYWORDS in "
                "src/semantic_exchange/generate_comprehensive_sssom.py); "
                "new collection_type description does not, so the unmapped "
                "row is classified as unmapped/none instead of "
                "free_text/heuristic while retaining sssom:NoTermFound."
            ),
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check base 7233f193ad102a8488b31ec7333662c8fefaa996 blobs against "
            "G2 generated OWL RDF and comprehensive SSSOM TSV products."
        )
    )
    parser.add_argument(
        "--git-repo",
        type=Path,
        default=DEFAULT_LEAD_ROOT,
        help="Git worktree/repository used to read base revision blobs.",
    )
    parser.add_argument(
        "--g2-root",
        type=Path,
        default=DEFAULT_G2_ROOT,
        help="Path to the G2 worktree containing generated 3.2.1 products.",
    )
    parser.add_argument(
        "--base-rev",
        default=DEFAULT_BASE_REV,
        help="Base Git revision to compare against (default: 7233f193ad102a8488b31ec7333662c8fefaa996).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_SCRATCH_DIR / "products-1.json",
        help=(
            "Fresh JSON output path in sibling caller scratch "
            "(default: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/"
            "d4d-executions/scratch-final-readiness-lead-20261110/products-1.json; "
            "must not already exist or reside inside a repo worktree)."
        ),
    )
    parser.add_argument(
        "--scratch-dir",
        type=Path,
        default=None,
        help=(
            "Optional caller scratch directory override; writes "
            "<scratch-dir>/products-1.json."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="In-process POSIX SIGALRM deadline in seconds (1..120, default: 120).",
    )
    return parser.parse_args(argv)


def _alarm_handler(signum: int, frame: Any) -> None:
    raise TimeoutError("Exceeded in-process 120-second deadline.")


def resolve_output_path(
    args: argparse.Namespace, git_repo: Path, g2_root: Path
) -> Path:
    if args.scratch_dir is not None:
        out = args.scratch_dir.expanduser().resolve() / "products-1.json"
    elif args.output is not None:
        out = args.output.expanduser().resolve()
    else:
        raise ValueError("Provide either --output <file> or --scratch-dir <dir>.")

    for repo_root in (git_repo, g2_root):
        if out == repo_root or repo_root in out.parents:
            raise ValueError(
                f"Refusing output path nested inside worktree {repo_root}: {out}"
            )

    if out.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing output file: {out}"
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.timeout_seconds <= 0 or args.timeout_seconds > DEFAULT_TIMEOUT_SECONDS:
        raise ValueError(
            f"--timeout-seconds must be in 1..{DEFAULT_TIMEOUT_SECONDS}"
        )

    git_repo = args.git_repo.expanduser().resolve()
    g2_root = args.g2_root.expanduser().resolve()
    output_path = resolve_output_path(args, git_repo, g2_root)

    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, float(args.timeout_seconds))
    try:
        base_commit_sha = resolve_commit_sha(git_repo, args.base_rev)
        g2_head_sha = resolve_commit_sha(g2_root, "HEAD")

        owl_report = check_owl_isomorphism(git_repo, base_commit_sha, g2_root)

        expected_comprehensive_changes = {
            "d4d_description": {
                "base": EXPECTED_OLD_COLLECTION_TYPE_DESC[:100] + "...",
                "g2": EXPECTED_NEW_COLLECTION_TYPE_DESC[:100] + "...",
            },
            "comment": {
                "base": (
                    "Free text/narrative field - no URI needed; TTL names "
                    "only D4D terms, which are not alignments"
                ),
                "g2": (
                    "Unmapped - needs vocabulary research; TTL names only D4D "
                    "terms, which are not alignments"
                ),
            },
            "mapping_status": {
                "base": "free_text",
                "g2": "unmapped",
            },
            "mapping_source": {
                "base": "heuristic",
                "g2": "none",
            },
            "heuristic_hint": {
                "base": "free_text",
                "g2": "",
            },
        }

        expected_uri_comprehensive_changes = {
            "comment": {
                "base": (
                    "Free text/narrative field - no slot_uri needed; TTL names "
                    "only D4D terms, which are not alignments"
                ),
                "g2": (
                    "Unmapped - needs vocabulary research for slot_uri; TTL names "
                    "only D4D terms, which are not alignments"
                ),
            },
            "mapping_status": {
                "base": "free_text",
                "g2": "unmapped",
            },
            "mapping_source": {
                "base": "heuristic",
                "g2": "none",
            },
            "heuristic_hint": {
                "base": "free_text",
                "g2": "",
            },
        }

        sssom_comprehensive_report = compare_sssom_table(
            git_repo=git_repo,
            base_rev=base_commit_sha,
            g2_root=g2_root,
            relpath=SSSOM_COMPREHENSIVE_RELPATH,
            key_column="subject_id",
            collection_type_key="d4d:collection_type",
            expected_changes=expected_comprehensive_changes,
        )

        sssom_uri_comprehensive_report = compare_sssom_table(
            git_repo=git_repo,
            base_rev=base_commit_sha,
            g2_root=g2_root,
            relpath=SSSOM_URI_COMPREHENSIVE_RELPATH,
            key_column="d4d_slot_name",
            collection_type_key="collection_type",
            expected_changes=expected_uri_comprehensive_changes,
        )

        overall_passed = (
            owl_report["passed"]
            and sssom_comprehensive_report["passed"]
            and sssom_uri_comprehensive_report["passed"]
        )

        payload = {
            "task": "check_final_generation_products_20261110",
            "overall_passed": overall_passed,
            "timeout_seconds": args.timeout_seconds,
            "base_rev": args.base_rev,
            "base_commit_sha": base_commit_sha,
            "git_repo": str(git_repo),
            "g2_root": str(g2_root),
            "g2_head_sha": g2_head_sha,
            "output_path": str(output_path),
            "owl_rdf_isomorphism": owl_report,
            "sssom_comprehensive": sssom_comprehensive_report,
            "sssom_uri_comprehensive": sssom_uri_comprehensive_report,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        return 0 if overall_passed else 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, old_handler)


if __name__ == "__main__":
    sys.exit(main())
