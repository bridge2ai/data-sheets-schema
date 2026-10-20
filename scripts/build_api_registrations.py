#!/usr/bin/env python3
"""Shared generation API registration builder (Step A3 / #1763, #4345, #2926).

Offline registration builder for the D4D Messages-API generic_v10 condition.
Generates immutable `shared_generation_registration_v1` documents,
`receipt_completion_registration_v2` receipts, and `shared_generation_batch_roster_v1`
rosters conforming strictly to the shared-generation selection and audit protocol.

Modelled on `tests/test_shared_generation_selection.py:17-52`.
Kept outside `src/` so registrations remain project inputs.

Usage examples:
    # Build single-project registration for CHORUS baseline:
    python scripts/build_api_registrations.py -p CHORUS -l 2026-10-DDa_claude-opus-5-api-generic-v10_rep1 -o data/registrations/generic_v10

    # Build batch registrations and roster for all 4 study projects:
    python scripts/build_api_registrations.py --all -l 2026-10-DDa_claude-opus-5-api-generic-v10_rep1 -o data/registrations/generic_v10 -r data/registrations/generic_v10/roster.json

    # Dry-run validation without writing to disk:
    python scripts/build_api_registrations.py --all -l 2026-10-DDa_claude-opus-5-api-generic-v10_rep1 --dry-run
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

# Ensure repository root and src/ are importable
ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "src").is_dir() and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# Support --worktree argument if copied to sibling inputs directory
for idx, arg in enumerate(sys.argv):
    if arg in ("--worktree", "-w") and idx + 1 < len(sys.argv):
        candidate_src = Path(sys.argv[idx + 1]).resolve() / "src"
        if candidate_src.is_dir() and str(candidate_src) not in sys.path:
            sys.path.insert(0, str(candidate_src))

import click
import yaml

from data_sheets_schema import api_runner as api
from data_sheets_schema import receipt_completion as rc
from data_sheets_schema import shared_generation as sg
from data_sheets_schema.chunking import CONCAT_DIR as BUNDLE_DIR, manifest_for
from data_sheets_schema.cli.api import ARMS
from data_sheets_schema.profiles import profile_named, select_profile
from data_sheets_schema.registry import load_registry
from data_sheets_schema.resources import resource_path
from data_sheets_schema.schema_snapshot import capture_schema

DEFAULT_PROJECTS = ("CHORUS", "AI_READI", "CM4AI", "VOICE")
DEFAULT_CONDITION = "generic_v10"
DEFAULT_ID_PREFIX = "generic-v10"
DEFAULT_RECEIPT_ID = "generic-v10-receipt"
DEFAULT_PROVIDER = "LBL CBORG (proxy to Anthropic)"
DEFAULT_BASE_URL = "https://api.cborg.lbl.gov"
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_VOCABULARIES_PATH = (
    ROOT / "src" / "data_sheets_schema" / "b2ai_registry_vocabularies.yaml"
)

DEFAULT_AUDIT_LIMITS: dict[str, Any] = {
    "max_paths": 192,
    "max_inventory_bytes": 32768,
    "max_workers": 16,
    "max_request_bytes": 32000000,
    "max_input_tokens_per_call": 1000000,
    "worker_output_tokens": 4000,
    "omission_output_tokens": 4000,
    "integration_output_tokens": 4000,
    "aggregate_input_tokens": 4000000,
    "aggregate_output_tokens": 100000,
    "max_calls": 18,
    "context_limit_tokens": 1000000,
    "context_limit_basis": "Route context window 1,000,000 tokens; sized for largest bundle",
}

DEFAULT_RECEIPT_LIMITS: dict[str, Any] = {
    "format": "receipt_completion_registration_v2",
    "registration_id": DEFAULT_RECEIPT_ID,
    "condition": DEFAULT_CONDITION,
    "receipt_instrument_version": 4,
    "max_output_tokens": 4000,
    "max_request_bytes": 32000000,
    "context_limit_tokens": 1000000,
    "context_limit_basis": "Route context window 1,000,000 tokens; sized for largest bundle",
    "coverage_floor": {"state": "pending", "mode": "diagnostic_pilot"},
}

DEFAULT_AUDIT_TRANSPORT: dict[str, int] = {
    "transport_attempts": 1,
    "sdk_max_retries": 0,
    "malformed_response_retries": 0,
}


def build_draft_context(
    project: str,
    source_manifest_path: Path | str | None = None,
    context_path: Path | str | None = None,
    write_to_disk: bool = True,
) -> dict[str, Any]:
    """Synthesize a compliant root-only omission_context_v1 draft document.

    Extracts referent and note from source_manifest.yaml scope metadata when available,
    satisfying context.schema.json and shared_generation.py root scope requirements.
    """
    referent = f"{project} dataset"
    referent_id = None
    referent_note = f"Scope authority for {project} dataset."
    source_policy_priority = [
        "RO-Crate, structured metadata, data resource",
        "documentation, license, DUA, IRB",
        "publication, preprint, white paper",
        "NIH project page, tutorial",
        "historical data release, historical documentation",
    ]
    source_policy_basis = "Declared source_manifest.yaml tier hierarchy."

    if source_manifest_path:
        sm = Path(source_manifest_path)
        if sm.is_file():
            try:
                data = yaml.safe_load(sm.read_text(encoding="utf-8")) or {}
                scope_map = data.get("scope", {})
                if isinstance(scope_map, dict) and project in scope_map:
                    entry = scope_map[project]
                    if isinstance(entry, dict):
                        referent = entry.get("referent") or referent
                        referent_id = entry.get("referent_id")
                        # Under D04, CHORUS release is null (not the website URL)
                        if project.upper() == "CHORUS" and referent_id == "https://chorus4ai.org/":
                            referent_id = None
                        referent_note = entry.get("referent_note") or referent_note
                if "source_priority" in data and isinstance(data["source_priority"], dict):
                    sp = data["source_priority"]
                    source_policy_priority = [
                        ", ".join(str(x) for x in sp[k]) if isinstance(sp[k], list) else str(sp[k])
                        for k in sorted(sp.keys())
                    ]
            except Exception:
                pass

    vocabulary: dict[str, Any] = {}
    if DEFAULT_VOCABULARIES_PATH.is_file():
        vocab_data = yaml.safe_load(DEFAULT_VOCABULARIES_PATH.read_text(encoding="utf-8")) or {}
        vocabulary = vocab_data.get("vocabularies", {})

    doc: dict[str, Any] = {
        "format": "omission_context_v1",
        "root_class": "Dataset",
        "scopes": [
            {
                "owner": "",
                "referent": referent,
                "release": referent_id,
                "scope": referent_note,
            }
        ],
        "source_policy": {
            "priority": source_policy_priority,
            "basis": source_policy_basis,
        },
        "vocabulary": vocabulary,
    }

    if write_to_disk and context_path is not None:
        target = Path(context_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(sg.canonical(doc))

    return doc


def build_registration(
    project: str,
    label: str,
    *,
    arm: str = "baseline",
    registration_path: Path | str | None = None,
    registration_id: str | None = None,
    id_prefix: str = DEFAULT_ID_PREFIX,
    context_path: Path | str | None = None,
    context_dir: Path | str | None = None,
    source_manifest_path: Path | str | None = None,
    bundle_path: Path | str | None = None,
    chunk_manifest_path: Path | str | None = None,
    profile_name: str | None = None,
    audit_limits: dict[str, Any] | None = None,
    receipt_limits: dict[str, Any] | None = None,
    synthesize_draft_context: bool = False,
    write_to_disk: bool = True,
) -> dict[str, Any]:
    """Build a complete shared_generation_registration_v1 document.

    Modelled on `tests/test_shared_generation_selection.py:17-52`.
    Validates output via `shared_generation.parse_registration`.
    """
    if arm not in ARMS:
        raise ValueError(f"unknown arm '{arm}'; must be one of {sorted(ARMS.keys())}")
    arm_display, method, pattern, _ = ARMS[arm]

    # Resolve manifest
    sm_resolved: Path | None = None
    if source_manifest_path is not None:
        raw_sm = Path(source_manifest_path)
        p = raw_sm.resolve()
        if not p.is_file() and not raw_sm.is_absolute():
            alt = (ROOT / raw_sm).resolve()
            if alt.is_file():
                p = alt
        if p.is_file():
            sm_resolved = p
        else:
            raise FileNotFoundError(f"source manifest not found: {source_manifest_path}")
    else:
        # Check standard location
        candidate = (ROOT / "data" / "preprocessed" / "source_manifest.yaml").resolve()
        if candidate.is_file():
            sm_resolved = candidate

    reg_registry = load_registry(sm_resolved)

    # Resolve bundle
    if bundle_path is not None:
        resolved_bundle = Path(bundle_path).resolve()
    else:
        if arm == "baseline":
            resolved_bundle = reg_registry.bundle(project).resolve()
        else:
            resolved_bundle = (reg_registry.anchored(BUNDLE_DIR) / pattern.format(p=project)).resolve()

    if not resolved_bundle.is_file():
        raise FileNotFoundError(f"bundle file not found: {resolved_bundle}")

    # Resolve chunk manifest
    if chunk_manifest_path is not None:
        resolved_chunks = Path(chunk_manifest_path).resolve()
    else:
        resolved_chunks = manifest_for(resolved_bundle, source_manifest=sm_resolved).resolve()

    if not resolved_chunks.is_file():
        raise FileNotFoundError(f"chunk manifest not found: {resolved_chunks}")

    # Resolve registration path
    if registration_path is None:
        raise ValueError("registration_path must be specified or resolved before building")
    resolved_reg_path = Path(registration_path).resolve()

    # Resolve registration ID
    if registration_id is None:
        registration_id = f"{id_prefix}-{project.lower()}-{label}"

    # Resolve context
    resolved_context: Path
    resolved_context_raw: bytes | None = None
    if context_path is not None:
        resolved_context = Path(context_path).resolve()
        if not resolved_context.is_file():
            raise FileNotFoundError(f"specified context file not found: {resolved_context}")
    else:
        # Search candidate context locations
        candidates: list[Path] = []
        if context_dir is not None:
            cd = Path(context_dir).resolve()
            candidates.extend([
                cd / f"{project.lower()}_omission_context.json",
                cd / f"{project}_context.json",
                cd / f"{project.lower()}_context.json",
            ])
        candidates.extend([
            resolved_reg_path.parent / f"{project.lower()}_omission_context.json",
            resolved_reg_path.parent / f"{project}_context.json",
            ROOT / "data" / "omission_contexts" / f"{project.lower()}_omission_context.json",
            ROOT / "data" / "omission_contexts" / f"{project}_context.json",
        ])

        found: Path | None = None
        for c in candidates:
            if c.is_file():
                found = c
                break

        if found is not None:
            resolved_context = found
        elif synthesize_draft_context:
            target_context = (
                Path(context_dir).resolve() / f"{project.lower()}_omission_context.json"
                if context_dir is not None
                else resolved_reg_path.parent / f"{project.lower()}_omission_context.json"
            )
            draft_doc = build_draft_context(
                project=project,
                source_manifest_path=sm_resolved,
                context_path=target_context,
                write_to_disk=write_to_disk,
            )
            resolved_context = target_context.resolve()
            resolved_context_raw = sg.canonical(draft_doc)
        else:
            raise FileNotFoundError(
                f"no omission context file found for {project!r} (searched {[str(c) for c in candidates]}); "
                "run scripts/build_draft_contexts.py first or pass --synthesize-draft-context"
            )

    # Resolve profile
    if profile_name is not None:
        prof = profile_named(profile_name)
        prof_name = prof.name
        prof_basis = "stated by caller"
    else:
        sel = select_profile(sm_resolved)
        prof = profile_named(sel.name)
        prof_name = sel.name
        prof_basis = sel.basis

    prof_vocab_pin = None
    if prof.pin_path:
        vocab_path = Path(prof.pin_path).resolve()
        if vocab_path.is_file():
            prof_vocab_pin = sg.file_pin(vocab_path)

    # Capture schema snapshots
    full_schema_pin = sg.schema_pin(capture_schema(api.FULL_SCHEMA_PATH, strict=True))
    core_schema_pin = sg.schema_pin(capture_schema(api.CORE_SCHEMA_PATH, strict=True))

    # Resolve runtime settings
    model_settings = api._model_settings(condition=DEFAULT_CONDITION)
    config_pin = None
    if model_settings.get("config_path"):
        cfg_path = Path(resource_path(model_settings["config_path"])).resolve()
        if cfg_path.is_file():
            config_pin = sg.file_pin(cfg_path)

    runtime_block = {
        "provider": DEFAULT_PROVIDER,
        "base_url": DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL,
        "temperature": None,
        "thinking": model_settings.get("thinking") or {"type": "adaptive", "display": "summarized"},
        "effort": None,
        "config": config_pin,
    }

    # Resolve limits
    active_audit_limits = copy.deepcopy(DEFAULT_AUDIT_LIMITS)
    if audit_limits:
        active_audit_limits.update(audit_limits)

    active_receipt = copy.deepcopy(DEFAULT_RECEIPT_LIMITS)
    if receipt_limits:
        active_receipt.update(receipt_limits)
    active_receipt["runtime_policy_sha256"] = rc.policy_identity(version=2)["sha256"]

    # Construct complete registration structure
    reg: dict[str, Any] = {
        "format": sg.FORMAT,
        "registration_id": registration_id,
        "registration_path": str(resolved_reg_path),
        "run": {
            "project": project,
            "arm": arm_display,
            "method": method,
            "label": label,
        },
        "selection": sg.descriptor(),
        "inputs": {
            "project": project,
            "bundle": sg.file_pin(resolved_bundle),
            "chunk_manifest": sg.file_pin(resolved_chunks),
            "source_manifest": sg.file_pin(sm_resolved) if sm_resolved else None,
            "context": sg.file_pin(resolved_context, raw=resolved_context_raw),
            "profile": {
                "name": prof_name,
                "basis": prof_basis,
                "vocabulary": prof_vocab_pin,
            },
            "full_schema": full_schema_pin,
            "core_schema": core_schema_pin,
        },
        "runtime": runtime_block,
        "audit_limits": active_audit_limits,
        "audit_transport": copy.deepcopy(DEFAULT_AUDIT_TRANSPORT),
        "receipt": active_receipt,
    }

    canonical_bytes = sg.canonical(reg)

    # Validate strictly with shared_generation.parse_registration
    sg.parse_registration(canonical_bytes)

    if write_to_disk:
        resolved_reg_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_reg_path.write_bytes(canonical_bytes)

    return reg


def build_roster(
    registrations: list[dict[str, Any]],
    roster_path: Path | str | None = None,
    write_to_disk: bool = True,
) -> dict[str, Any]:
    """Build a shared_generation_batch_roster_v1 document from registration dicts.

    Ensures no duplicate (project, label) rows, paths, or registration_ids.
    """
    rows: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()
    seen_paths: set[str] = set()
    seen_ids: set[str] = set()

    for reg in registrations:
        run = reg.get("run") or {}
        project = run.get("project")
        label = run.get("label")
        reg_path = reg.get("registration_path")
        reg_id = reg.get("registration_id")

        if not project or not label or not reg_path:
            raise ValueError(f"registration missing required project, label, or path: {reg}")

        key = (project, label)
        if key in seen_keys:
            raise ValueError(f"duplicate (project, label) pair in roster: {key}")
        seen_keys.add(key)

        resolved_path = str(Path(reg_path).resolve())
        if resolved_path in seen_paths:
            raise ValueError(f"duplicate registration path in roster: {resolved_path}")
        seen_paths.add(resolved_path)

        if reg_id:
            if reg_id in seen_ids:
                raise ValueError(f"duplicate registration_id across roster rows: {reg_id}")
            seen_ids.add(reg_id)

        rows.append({
            "project": project,
            "label": label,
            "registration_path": resolved_path,
        })

    roster: dict[str, Any] = {
        "format": "shared_generation_batch_roster_v1",
        "registrations": rows,
    }

    if write_to_disk and roster_path is not None:
        target = Path(roster_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(sg.canonical(roster))

    return roster


def validate_registration_document(reg: dict[str, Any]) -> dict[str, Any]:
    """Validate registration document using shared_generation.parse_registration."""
    raw = sg.canonical(reg)
    return sg.parse_registration(raw)


def validate_roster_file(roster_path: Path | str, pairs: list[tuple[str, str]] | None = None) -> dict[str, Any]:
    """Validate roster file using cli/api._shared_roster."""
    from data_sheets_schema.cli.api import _shared_roster
    p = Path(roster_path).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"roster file does not exist: {p}")

    if pairs is None:
        data = json.loads(p.read_text(encoding="utf-8"))
        pairs = [(r["project"], r["label"]) for r in data.get("registrations", [])]

    return _shared_roster(str(p), pairs)


@click.command(name="build-api-registrations")
@click.option(
    "--project", "-p", "projects",
    multiple=True,
    help="Project name(s) (e.g. CHORUS, AI_READI). Can be passed multiple times or comma-separated.",
)
@click.option(
    "--all", "all_projects",
    is_flag=True,
    help=f"Build registrations for all four study projects ({', '.join(DEFAULT_PROJECTS)}).",
)
@click.option(
    "--label", "-l",
    required=True,
    help="Replicate / run label (e.g. 2026-10-DDa_claude-opus-5-api-generic-v10_rep1).",
)
@click.option(
    "--arm", "-a",
    default="baseline",
    show_default=True,
    type=click.Choice(sorted(ARMS.keys())),
    help="Condition arm.",
)
@click.option(
    "--output-dir", "-o",
    type=click.Path(path_type=Path),
    default=Path("data/registrations/generic_v10"),
    show_default=True,
    help="Directory to write registration JSON files.",
)
@click.option(
    "--roster-path", "-r",
    type=click.Path(path_type=Path),
    help="Path to write batch roster JSON file. Defaults to <output-dir>/roster_<label>.json.",
)
@click.option(
    "--context", "-c", "context_file",
    type=click.Path(path_type=Path),
    help="Explicit path to an omission_context_v1 JSON file (for single project).",
)
@click.option(
    "--context-dir",
    type=click.Path(path_type=Path),
    help="Directory containing or to receive project omission context JSON files.",
)
@click.option(
    "--source-manifest", "-m",
    type=click.Path(path_type=Path),
    default=Path("data/preprocessed/source_manifest.yaml"),
    show_default=True,
    help="Path to source_manifest.yaml.",
)
@click.option(
    "--id-prefix",
    default=DEFAULT_ID_PREFIX,
    show_default=True,
    help="Prefix for registration_id.",
)
@click.option(
    "--synthesize-draft-context",
    is_flag=True,
    help="Synthesize a draft omission_context_v1 file if no pre-built context file is found.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Build and validate registrations in memory without writing to disk.",
)
@click.option(
    "--check",
    is_flag=True,
    help="Validate existing registrations and roster on disk without rebuilding.",
)
def cli(
    projects: tuple[str, ...],
    all_projects: bool,
    label: str,
    arm: str,
    output_dir: Path,
    roster_path: Path | None,
    context_file: Path | None,
    context_dir: Path | None,
    source_manifest: Path,
    id_prefix: str,
    synthesize_draft_context: bool,
    dry_run: bool,
    check: bool,
) -> None:
    """Build shared generation registrations and batch rosters for D4D Messages-API generic_v10."""
    target_projects: list[str] = []
    if all_projects:
        target_projects = list(DEFAULT_PROJECTS)
    elif projects:
        for p in projects:
            for item in p.split(","):
                item = item.strip()
                if item and item not in target_projects:
                    target_projects.append(item)
    else:
        raise click.UsageError("Specify at least one --project or use --all.")

    if context_file and len(target_projects) > 1:
        raise click.UsageError("--context can only be used with a single project. Use --context-dir for multiple projects.")

    out_dir = output_dir.resolve()
    target_roster_path = (roster_path or (out_dir / f"roster_{label}.json")).resolve()

    if check:
        click.echo(f"Checking registrations for {target_projects} under {out_dir}...")
        for proj in target_projects:
            reg_file = out_dir / f"registration_{proj.lower()}_{label}.json"
            if not reg_file.is_file():
                raise click.ClickException(f"Missing registration file: {reg_file}")
            raw = reg_file.read_bytes()
            sg.parse_registration(raw)
            click.echo(f"  ✓ {proj}: {reg_file.name}")
        if not target_roster_path.is_file():
            raise click.ClickException(f"Missing roster file: {target_roster_path}")
        pairs = [(p, label) for p in target_projects]
        validate_roster_file(target_roster_path, pairs)
        click.echo(f"  ✓ Roster valid: {target_roster_path.name}")
        click.echo("All checks passed.")
        return

    registrations: list[dict[str, Any]] = []
    click.echo(f"Building registrations for {target_projects} (arm: {arm}, label: {label})...")

    for proj in target_projects:
        reg_file = out_dir / f"registration_{proj.lower()}_{label}.json"
        reg = build_registration(
            project=proj,
            label=label,
            arm=arm,
            registration_path=reg_file,
            id_prefix=id_prefix,
            context_path=context_file,
            context_dir=context_dir or out_dir,
            source_manifest_path=source_manifest,
            synthesize_draft_context=synthesize_draft_context,
            write_to_disk=not dry_run,
        )
        registrations.append(reg)
        click.echo(f"  ✓ {proj}: registration_id={reg['registration_id']}")

    roster = build_roster(
        registrations=registrations,
        roster_path=target_roster_path,
        write_to_disk=not dry_run,
    )
    click.echo(f"  ✓ Roster with {len(roster['registrations'])} rows: {target_roster_path}")

    if dry_run:
        click.echo("[dry-run] Validated registrations and roster in memory without writing to disk.")
    else:
        click.echo("Done. Registrations and roster written successfully.")


def main() -> int:
    try:
        cli()
        return 0
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    except Exception as exc:
        sys.stderr.write(f"build_api_registrations: error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
