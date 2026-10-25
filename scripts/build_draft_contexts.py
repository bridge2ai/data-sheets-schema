#!/usr/bin/env python3
"""Draft Scope Contexts Builder (Step A5d / #1763, #2914, #422).

Extracts and validates root-only omission_context_v1 draft context documents
from data/preprocessed/source_manifest.yaml scope and priority blocks.

Satisfies:
- omission_inventory_v1/context.schema.json
- shared_generation.py capture assertions (root scope exactly once, distinct owners)
- Decision D04: CHORUS release is null
- Issue #422: No diagnoses, labels, or prior-arm content

Usage:
    # Build default root drafts (CHORUS and AI_READI) into data/omission_contexts/:
    python scripts/build_draft_contexts.py

    # Build all available Grand Challenge draft contexts:
    python scripts/build_draft_contexts.py --all

    # Validate existing context files against source_manifest.yaml:
    python scripts/build_draft_contexts.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "src").is_dir() and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from data_sheets_schema import shared_generation as sg

DEFAULT_MANIFEST_PATH = ROOT / "data" / "preprocessed" / "source_manifest.yaml"
KIDS_FIRST_MANIFEST_PATH = (
    ROOT / "notes" / "matched_cborg_2026-09-13" / "kids_first" / "manifest.yaml"
)
DEFAULT_OUT_DIR = ROOT / "data" / "omission_contexts"
SCHEMA_PATH = (
    ROOT / "src" / "data_sheets_schema" / "omission_inventory_v1" / "context.schema.json"
)
DEFAULT_VOCABULARIES_PATH = (
    ROOT / "src" / "data_sheets_schema" / "b2ai_registry_vocabularies.yaml"
)

# Standard Grand Challenge projects declared in source_manifest.yaml
DEFAULT_PROJECTS = ["CHORUS", "AI_READI"]
ALL_GC_PROJECTS = ["CHORUS", "AI_READI", "CM4AI", "VOICE", "VOICE_PEDIATRIC"]
ALL_CAMPAIGN_PROJECTS = [*ALL_GC_PROJECTS, "KIDS_FIRST"]

FORBIDDEN_SUBSTRINGS = [
    "diagnosis",
    "diagnoses",
    "prior-arm",
    "baseline arm",
    "de novo arm",
]


def load_context_schema() -> dict[str, Any]:
    """Load the frozen context.schema.json."""
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"Context schema not found at {SCHEMA_PATH}")
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def extract_source_policy(
    manifest_data: dict[str, Any],
    project: str | None = None,
) -> dict[str, Any]:
    """Extract tier priority hierarchy from source_manifest.yaml or project manifest."""
    sp = manifest_data.get("source_priority", {})
    if isinstance(sp, dict) and sp:
        priority_list = [
            ", ".join(sp[k]) if isinstance(sp[k], list) else str(sp[k])
            for k in sorted(sp.keys())
        ]
        basis = "Declared source_manifest.yaml tier hierarchy."
    else:
        # Check if project declares source_type entries under projects.<P>.sources
        declared_types: list[str] = []
        projects_block = manifest_data.get("projects", {})
        if project and isinstance(projects_block, dict):
            entry = projects_block.get(project) or projects_block.get(project.upper())
            sources = entry.get("sources", []) if isinstance(entry, dict) else (entry if isinstance(entry, list) else [])
            for src in sources:
                if isinstance(src, dict):
                    st = src.get("source_type")
                    if isinstance(st, str) and st.strip() and st.strip() not in declared_types:
                        declared_types.append(st.strip())
        if declared_types:
            priority_list = declared_types
            basis = "Declared source types from project manifest (no tier hierarchy declared)."
        else:
            priority_list = [
                "RO-Crate, structured metadata, data resource",
                "documentation, license, DUA, IRB",
                "publication, preprint, white paper",
                "NIH project page, tutorial",
                "historical data release, historical documentation",
            ]
            basis = "Declared source_manifest.yaml tier hierarchy."
    return {
        "priority": priority_list,
        "basis": basis,
    }


def _format_related_but_distinct(declared: dict[str, Any] | None) -> str:
    """Render declared related_but_distinct entries into scope text (#5120)."""
    if not isinstance(declared, dict):
        return ""
    from data_sheets_schema.scope import aliases_of, malformed_in

    rows = malformed_in(declared)
    skipped = {r["index"] for r in rows if r["skipped"]}
    related = [
        e
        for i, e in enumerate(declared.get("related_but_distinct") or [])
        if i not in skipped and isinstance(e, dict)
    ]
    if not related:
        return ""
    lines = ["The declared bundle also documents datasets that are NOT this one:"]
    for entry in related:
        name = str(entry.get("name") or entry.get("id") or "").strip()
        ids = aliases_of(entry)
        head = f"- {name}" + (f" — {', '.join(ids)}" if ids else "")
        lines.append(head)
        why = str(entry.get("why") or "").strip()
        if why:
            lines.append(f"  Why distinct: {why}")
        express = str(entry.get("express_as") or "").strip()
        if express:
            lines.append(
                f"  Facts about it belong in `{express}`, never in this dataset's own slots."
            )
        in_bundle = entry.get("in_bundle")
        if in_bundle:
            names = (
                list(in_bundle)
                if isinstance(in_bundle, (list, tuple))
                else [in_bundle]
            )
            lines.append(
                "  Its documentation is legitimately in this bundle, under source "
                + ", ".join(str(n) for n in names)
                + "."
            )
    return "\n".join(lines)


def serialize_draft_context(doc: dict[str, Any]) -> bytes:
    """Serialize an omission_context_v1 document to canonical indented UTF-8 JSON bytes."""
    return json.dumps(doc, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def load_project_manifest_data(
    project: str,
    source_manifest_path: Path | str | None = None,
) -> dict[str, Any]:
    """Load manifest data for a project, resolving KIDS_FIRST neutral manifest when appropriate."""
    norm_project = project.strip()
    manifest_data: dict[str, Any] = {}
    if source_manifest_path is not None:
        sm = Path(source_manifest_path)
        if sm.is_file():
            manifest_data = yaml.safe_load(sm.read_text(encoding="utf-8")) or {}
    elif norm_project.upper() == "KIDS_FIRST" and KIDS_FIRST_MANIFEST_PATH.is_file():
        manifest_data = yaml.safe_load(KIDS_FIRST_MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    elif DEFAULT_MANIFEST_PATH.is_file():
        manifest_data = yaml.safe_load(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8")) or {}

    scope_map = manifest_data.get("scope", {}) if isinstance(manifest_data, dict) else {}
    if (
        norm_project.upper() == "KIDS_FIRST"
        and not any(k.upper() == "KIDS_FIRST" for k in (scope_map or {}))
        and KIDS_FIRST_MANIFEST_PATH.is_file()
    ):
        manifest_data = (
            yaml.safe_load(KIDS_FIRST_MANIFEST_PATH.read_text(encoding="utf-8")) or {}
        )
    return manifest_data if isinstance(manifest_data, dict) else {}


def build_draft_scope_context(
    project: str,
    manifest_data: dict[str, Any],
) -> dict[str, Any]:
    """Build a compliant root-only omission_context_v1 document for a project."""
    norm_project = project.strip()
    scope_block = manifest_data.get("scope", {})
    if not isinstance(scope_block, dict):
        raise ValueError("source_manifest.yaml missing 'scope' dictionary")

    # Match project case-insensitively if needed
    matched_entry: dict[str, Any] | None = None
    for k, v in scope_block.items():
        if k.upper() == norm_project.upper():
            matched_entry = v
            break

    referent = f"{norm_project} dataset"
    referent_id: str | None = None
    referent_note = f"Scope authority for {norm_project} dataset."

    if matched_entry and isinstance(matched_entry, dict):
        referent = matched_entry.get("referent") or referent
        if "release" in matched_entry:
            raw_release = matched_entry.get("release")
            referent_id = str(raw_release).strip() if raw_release is not None else None
        else:
            raw_ref_id = matched_entry.get("referent_id")
            referent_id = str(raw_ref_id).strip() if raw_ref_id is not None else None
        referent_note = matched_entry.get("referent_note") or referent_note

    scope_text = referent_note.strip()
    related_text = _format_related_but_distinct(matched_entry)
    if related_text:
        scope_text = f"{scope_text}\n\n{related_text}"

    source_policy = extract_source_policy(manifest_data, project=norm_project)

    vocabulary: dict[str, Any] = {}
    declared_prof = str(manifest_data.get("profile") or "").strip().lower()
    if declared_prof != "neutral" and DEFAULT_VOCABULARIES_PATH.is_file():
        vocab_data = yaml.safe_load(DEFAULT_VOCABULARIES_PATH.read_text(encoding="utf-8")) or {}
        vocabulary = vocab_data.get("vocabularies", {})

    doc: dict[str, Any] = {
        "format": "omission_context_v1",
        "root_class": "Dataset",
        "scopes": [
            {
                "owner": "",
                "referent": referent.strip(),
                "release": referent_id if referent_id else None,
                "scope": scope_text,
            }
        ],
        "source_policy": source_policy,
        "vocabulary": vocabulary,
    }

    # Validate against schema
    schema = load_context_schema()
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(doc))
    if errors:
        msg = "; ".join(f"{e.json_path}: {e.message}" for e in errors)
        raise ValueError(f"Draft context for {norm_project} failed schema validation: {msg}")

    # Validate shared_generation root scope uniqueness
    owners = [s["owner"] for s in doc["scopes"]]
    if owners.count("") != 1 or len(owners) != len(set(owners)):
        raise ValueError("Draft context scopes must contain root owner '' exactly once")

    # Validate issue #422: no forbidden words in scope text
    serialized_text = json.dumps(doc).lower()
    for forbidden in FORBIDDEN_SUBSTRINGS:
        if forbidden in serialized_text:
            raise ValueError(
                f"Draft context for {norm_project} violates issue #422 constraint: contains '{forbidden}'"
            )

    return doc


def generate_draft_contexts(
    projects: list[str],
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    out_dir: Path = DEFAULT_OUT_DIR,
    check_only: bool = False,
) -> dict[str, Path]:
    """Generate or verify draft contexts for the specified projects.

    Returns a dict mapping project name to the output file Path.
    """
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Source manifest not found at {manifest_path}")

    raw_manifest = manifest_path.read_text(encoding="utf-8")
    manifest_data = yaml.safe_load(raw_manifest) or {}

    out_paths: dict[str, Path] = {}

    if not check_only:
        out_dir.mkdir(parents=True, exist_ok=True)

    for proj in projects:
        proj_manifest_data = load_project_manifest_data(proj, manifest_path)
        doc = build_draft_scope_context(proj, proj_manifest_data)
        out_file = out_dir / f"{proj.lower()}_omission_context.json"
        out_paths[proj] = out_file

        canonical_bytes = serialize_draft_context(doc)

        if check_only:
            if not out_file.is_file():
                raise FileNotFoundError(f"Missing draft context file for {proj}: {out_file}")
            existing_bytes = out_file.read_bytes()
            existing_doc = json.loads(existing_bytes)
            if existing_doc != doc or existing_bytes != canonical_bytes:
                raise ValueError(
                    f"Existing draft context at {out_file} differs from generated context for {proj}"
                )
        else:
            out_file.write_bytes(canonical_bytes)

    return out_paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Draft Scope Contexts Builder (Step A5d / #1763, #2914)"
    )
    parser.add_argument(
        "--projects",
        type=str,
        default="",
        help="Comma-separated project list (default: CHORUS,AI_READI)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate draft contexts for all declared campaign projects (5 GC + KIDS_FIRST)",
    )
    parser.add_argument(
        "--source-manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Path to source_manifest.yaml",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Target output directory for draft contexts",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify existing context files without overwriting",
    )

    args = parser.parse_args(argv)

    if args.all:
        selected_projects = ALL_CAMPAIGN_PROJECTS
    elif args.projects:
        selected_projects = [p.strip() for p in args.projects.split(",") if p.strip()]
    else:
        selected_projects = DEFAULT_PROJECTS

    try:
        paths = generate_draft_contexts(
            projects=selected_projects,
            manifest_path=args.source_manifest,
            out_dir=args.out_dir,
            check_only=args.check,
        )
        action_word = "Verified" if args.check else "Generated"
        for p, path in paths.items():
            print(f"{action_word} draft context for {p}: {path}")
        return 0
    except Exception as exc:
        sys.stderr.write(f"build_draft_contexts: error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
