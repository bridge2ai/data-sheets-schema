#!/usr/bin/env python3
"""Shared generation API registration builder (Step A3 / #1763, #4345, #2926).

Offline registration builder for the D4D Messages-API generic_v10 condition.
Generates immutable `shared_generation_registration_v1` documents,
`receipt_completion_registration_v2` receipts, and `shared_generation_batch_roster_v1`
rosters conforming strictly to the shared-generation selection and audit protocol.

Modelled on `tests/test_shared_generation_selection.py:17-52`.
Kept outside `src/` so registrations remain project inputs.

Usage examples:
    # Build single-project registration for CHORUS baseline (partition bounds are
    # never defaulted; the chorus profile is validated for CHORUS only):
    python scripts/build_api_registrations.py -p CHORUS --partition chorus -l 2026-10-DDa_claude-opus-5-api-generic-v10_rep1 -o data/registrations/generic_v10

    # Any other project names bounds sized for it (see PARTITION_PROFILES):
    python scripts/build_api_registrations.py -p AI_READI --max-paths N --max-inventory-bytes B --max-workers W -l 2026-10-DDa_claude-opus-5-api-generic-v10_rep1 -o data/registrations/generic_v10

    # Dry-run validation without writing to disk:
    python scripts/build_api_registrations.py -p CHORUS --partition chorus -l 2026-10-DDa_claude-opus-5-api-generic-v10_rep1 --dry-run
"""

from __future__ import annotations

import copy
import hashlib
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
KIDS_FIRST_MANIFEST_PATH = (
    ROOT / "notes" / "matched_cborg_2026-09-13" / "kids_first" / "manifest.yaml"
)
DEFAULT_CONDITION = "generic_v10"
DEFAULT_ID_PREFIX = "generic-v10"
DEFAULT_RECEIPT_ID = "generic-v10-receipt"
DEFAULT_PROVIDER = "LBL CBORG (proxy to Anthropic)"
DEFAULT_BASE_URL = "https://api.cborg.lbl.gov"
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_VOCABULARIES_PATH = (
    ROOT / "src" / "data_sheets_schema" / "b2ai_registry_vocabularies.yaml"
)

# Stage output caps follow the CHORUS canaries (D-C, owner decision
# 2026-10-23): at 25,000 the first 2026-10-20a worker spent its whole budget
# thinking and wrote nothing; under 64,000/32,000/32,000 the most any stage
# used was 53,204 (83%), 23,997 (75%) and 23,347 (73%). The aggregate output
# allowance and the call allowance are derived from these and the partition
# bounds in `resolve_audit_limits`, never stated separately.
DEFAULT_AUDIT_LIMITS: dict[str, Any] = {
    "max_request_bytes": 32000000,
    "max_input_tokens_per_call": 1000000,
    "worker_output_tokens": 64000,
    "omission_output_tokens": 32000,
    "integration_output_tokens": 32000,
    "aggregate_input_tokens": 4000000,
    "context_limit_tokens": 1000000,
    "context_limit_basis": "Route context window 1,000,000 tokens; sized for largest bundle",
}

# Partition bounds have no default (D-C, owner decision 2026-10-23): no one
# setting plans every project. 80 paths / 12,288 bytes / 4 workers refuses
# every v8 AI_READI, CM4AI, VOICE and CHORUS full record (a single /creators
# or /file_collections field outgrows a worker, or the plan needs more than
# four), and the refusal comes after `full` and receipt completion are
# billed. 384 / 65,536 / 4 plans them but hands one worker about five times
# the inventory a CHORUS worker filled 64k of output with. A registration
# names its bounds, or a profile validated for its project.
PARTITION_KEYS = ("max_paths", "max_inventory_bytes", "max_workers")
PARTITION_PROFILES: dict[str, dict[str, Any]] = {
    # What 2026-10-22a ran: 98 paths in three workers (35/54/9), the fullest
    # 39 bytes under the inventory bound, each using 14k-50k of its 64k.
    # Baseline arm only: 16 of the 18 CHORUS crate-arm records fail planning
    # under these bounds, and the de novo arm has no v10 evidence.
    "chorus": {"projects": ("CHORUS",), "arms": ("baseline",),
               "limits": {"max_paths": 80, "max_inventory_bytes": 12288, "max_workers": 4}},
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


def resolve_audit_limits(
    project: str,
    partition: str | None = None,
    overrides: dict[str, Any] | None = None,
    *,
    arm: str = "baseline",
) -> dict[str, Any]:
    """Defaults, then a named partition profile, then explicit overrides.

    The aggregate output allowance is the sum of every stage cap for the
    largest plan (``max_workers`` workers, omission, integration): the typed
    runtime admits each call only while settled output plus that call's cap
    fits, so anything less refuses a full plan midway and anything more is
    an allowance no plan can use. A supplied value that disagrees is refused.
    ``max_calls`` defaults to that roster's length and may not be smaller.
    """
    limits = copy.deepcopy(DEFAULT_AUDIT_LIMITS)
    if partition is not None:
        if partition not in PARTITION_PROFILES:
            raise ValueError(f"unknown partition profile {partition!r}; known: {sorted(PARTITION_PROFILES)}")
        profile = PARTITION_PROFILES[partition]
        if project not in profile["projects"] or arm not in profile["arms"]:
            raise ValueError(
                f"partition profile {partition!r} is validated only for {', '.join(profile['projects'])} "
                f"({', '.join(profile['arms'])} arm); pass --max-paths, --max-inventory-bytes and "
                f"--max-workers sized for {project} ({arm})"
            )
        limits.update(profile["limits"])
    limits.update(overrides or {})
    missing = [key for key in PARTITION_KEYS if limits.get(key) is None]
    if missing:
        raise ValueError(
            "audit partition bounds have no default (D-C): pass --partition, or "
            + ", ".join(f"--{key.replace('_', '-')}" for key in missing)
        )
    roster = limits["max_workers"] + 2
    aggregate = (limits["max_workers"] * limits["worker_output_tokens"]
                 + limits["omission_output_tokens"] + limits["integration_output_tokens"])
    if limits.get("aggregate_output_tokens") is not None and limits["aggregate_output_tokens"] != aggregate:
        raise ValueError(
            f"aggregate_output_tokens {limits['aggregate_output_tokens']} disagrees with the stage caps: "
            f"{limits['max_workers']} x {limits['worker_output_tokens']} + {limits['omission_output_tokens']}"
            f" + {limits['integration_output_tokens']} = {aggregate}"
        )
    limits["aggregate_output_tokens"] = aggregate
    if limits.get("max_calls") is None:
        limits["max_calls"] = roster
    if limits["max_calls"] < roster:
        raise ValueError(
            f"max_calls {limits['max_calls']} cannot cover {limits['max_workers']} workers"
            f" plus omission and integration ({roster})"
        )
    return limits


FLOOR_BASIS_CHOICES = ("receipted_part", "all_receiptable")


def parse_coverage_floor(value: str | dict[str, Any] | None, *,
                         basis: str = "receipted_part") -> dict[str, Any]:
    """Parse a coverage floor specification into receipt_completion_registration_v2 format.

    Accepts:
      - None, "pending", or "diagnostic_pilot" -> {"state": "pending", "mode": "diagnostic_pilot"}
      - "NUM/DEN" (e.g. "13/20") -> {"state": "registered", "numerator": NUM, "denominator": DEN, "basis": ...}
      - Decimal multiple of 0.05 in (0, 1] (e.g. "0.65") -> {"state": "registered", "numerator": 13, "denominator": 20, ...}
      - An existing dict, unchanged.

    A registered floor gates the receipted part by default (D-C, 2026-10-23):
    values reconciliation added after the receipt are reported, not gated.
    ``basis="all_receiptable"`` writes the v2 floor with no basis key, the
    form every registration before the decision carries.
    """
    if basis not in FLOOR_BASIS_CHOICES:
        raise ValueError(f"invalid coverage floor basis {basis!r}; expected one of {FLOOR_BASIS_CHOICES}")
    if value is None:
        return {"state": "pending", "mode": "diagnostic_pilot"}
    if isinstance(value, dict):
        return copy.deepcopy(value)
    floor = _parse_floor_fraction(value)
    if floor["state"] == "registered" and basis == "receipted_part":
        floor["basis"] = "receipted_part"
    return floor


def _parse_floor_fraction(value: str) -> dict[str, Any]:
    text = str(value).strip()
    if text.lower() in ("pending", "diagnostic_pilot"):
        return {"state": "pending", "mode": "diagnostic_pilot"}
    if "/" in text:
        parts = text.split("/", 1)
        try:
            num = int(parts[0].strip())
            den = int(parts[1].strip())
        except ValueError as exc:
            raise ValueError(
                f"invalid coverage_floor {value!r}; expected 'pending' or 'NUM/DEN'"
            ) from exc
        if not (0 < num <= den <= 1000):
            raise ValueError(
                f"invalid coverage_floor {value!r}; require 0 < numerator <= denominator <= 1000"
            )
        return {"state": "registered", "numerator": num, "denominator": den}
    try:
        dec = float(text)
    except ValueError as exc:
        raise ValueError(
            f"invalid coverage_floor {value!r}; expected 'pending', 'NUM/DEN', or decimal in (0, 1]"
        ) from exc
    if not (0.0 < dec <= 1.0):
        raise ValueError(f"coverage_floor decimal {value!r} must be in (0, 1]")
    num_20 = round(dec * 20)
    if abs(num_20 / 20.0 - dec) < 1e-9 and 0 < num_20 <= 20:
        return {"state": "registered", "numerator": num_20, "denominator": 20}
    num_1000 = round(dec * 1000)
    if not (0 < num_1000 <= 1000):
        raise ValueError(f"invalid coverage_floor {value!r}")
    return {"state": "registered", "numerator": num_1000, "denominator": 1000}


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
    manifest_profile: str | None = None

    if source_manifest_path:
        sm = Path(source_manifest_path)
        if sm.is_file():
            try:
                data = yaml.safe_load(sm.read_text(encoding="utf-8")) or {}
                if isinstance(data.get("profile"), str):
                    manifest_profile = data["profile"].strip()
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
                elif isinstance(data.get("projects"), dict) and project in data["projects"]:
                    proj_entry = data["projects"][project]
                    sources = proj_entry.get("sources", []) if isinstance(proj_entry, dict) else []
                    seen_types: list[str] = []
                    for src in sources:
                        if isinstance(src, dict):
                            st = str(src.get("source_type") or "").strip()
                            if st and st not in seen_types:
                                seen_types.append(st)
                    if seen_types:
                        source_policy_priority = seen_types
                        source_policy_basis = (
                            "Declared source types from project manifest (no tier hierarchy declared)."
                        )
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
    coverage_floor: str | dict[str, Any] | None = None,
    floor_basis: str = "receipted_part",
    partition: str | None = None,
    audit_limits: dict[str, Any] | None = None,
    receipt_limits: dict[str, Any] | None = None,
    synthesize_draft_context: bool = False,
    write_to_disk: bool = True,
    replace: bool = False,
) -> dict[str, Any]:
    """Build a complete shared_generation_registration_v1 document.

    Modelled on `tests/test_shared_generation_selection.py:17-52`.
    Validates output via `shared_generation.parse_registration`.
    """
    if arm not in ARMS:
        raise ValueError(f"unknown arm '{arm}'; must be one of {sorted(ARMS.keys())}")
    arm_display, method, pattern, _ = ARMS[arm]

    # Resolve manifest
    default_study_manifest = (ROOT / "data" / "preprocessed" / "source_manifest.yaml").resolve()
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
        if project.upper() == "KIDS_FIRST" and KIDS_FIRST_MANIFEST_PATH.is_file():
            sm_resolved = KIDS_FIRST_MANIFEST_PATH.resolve()
        elif default_study_manifest.is_file():
            sm_resolved = default_study_manifest

    reg_registry = load_registry(sm_resolved)
    if (
        not reg_registry.declares(project)
        and project.upper() == "KIDS_FIRST"
        and sm_resolved == default_study_manifest
        and KIDS_FIRST_MANIFEST_PATH.is_file()
    ):
        sm_resolved = KIDS_FIRST_MANIFEST_PATH.resolve()
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
            alt_chunks = (resolved_bundle.parent / "chunks.yaml").resolve()
            if alt_chunks.is_file():
                resolved_chunks = alt_chunks

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
        prof_basis = "stated by the caller"
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
    active_audit_limits = resolve_audit_limits(project, partition, audit_limits, arm=arm)

    active_receipt = copy.deepcopy(DEFAULT_RECEIPT_LIMITS)
    if coverage_floor is not None:
        active_receipt["coverage_floor"] = parse_coverage_floor(coverage_floor, basis=floor_basis)
    if "context_limit_tokens" in (audit_limits or {}) and "context_limit_tokens" not in (receipt_limits or {}):
        active_receipt["context_limit_tokens"] = active_audit_limits["context_limit_tokens"]
    if "context_limit_basis" in (audit_limits or {}) and "context_limit_basis" not in (receipt_limits or {}):
        active_receipt["context_limit_basis"] = active_audit_limits["context_limit_basis"]
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
        if resolved_reg_path.exists() and not replace and resolved_reg_path.read_bytes() != canonical_bytes:
            raise FileExistsError(
                f"{resolved_reg_path} already exists with different bytes; pass --replace to overwrite"
            )
        resolved_reg_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_reg_path.write_bytes(canonical_bytes)

    return reg


def build_roster(
    registrations: list[dict[str, Any]],
    roster_path: Path | str | None = None,
    write_to_disk: bool = True,
    replace: bool = False,
) -> dict[str, Any]:
    """Build a shared_generation_batch_roster_v2 document from registration dicts.

    Ensures no duplicate (project, label) rows, paths, or registration_ids, and
    pins each row's canonical registration SHA-256 digest.
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

        reg_file = Path(resolved_path)
        reg_bytes = reg_file.read_bytes() if reg_file.is_file() else sg.canonical(reg)
        reg_sha256 = hashlib.sha256(reg_bytes).hexdigest()

        rows.append({
            "project": project,
            "label": label,
            "registration_path": resolved_path,
            "registration_sha256": reg_sha256,
        })

    roster: dict[str, Any] = {
        "format": "shared_generation_batch_roster_v2",
        "registrations": rows,
    }

    if write_to_disk and roster_path is not None:
        target = Path(roster_path).resolve()
        roster_bytes = sg.canonical(roster)
        if target.exists() and not replace and target.read_bytes() != roster_bytes:
            raise FileExistsError(
                f"{target} already exists with different bytes; pass --replace to overwrite"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(roster_bytes)

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
    "--label", "-l", "labels",
    multiple=True,
    help="Replicate / run label(s) (e.g. 2026-10-DDa_claude-opus-5-api-generic-v10_rep1).",
)
@click.option(
    "--label-prefix",
    help="Label prefix for replicate fan-out (e.g. 2026-10-DDa_claude-opus-5-api-generic-v10).",
)
@click.option(
    "--replicates",
    type=int,
    default=1,
    show_default=True,
    help="Number of replicates when --label-prefix is used (generates <label-prefix>_rep1..N).",
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
    help="Path to write batch roster JSON file. Defaults to <output-dir>/roster_<label_or_prefix>.json.",
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
    "--bundle",
    type=click.Path(path_type=Path),
    help="Explicit bundle path override (for single project).",
)
@click.option(
    "--chunk-manifest",
    type=click.Path(path_type=Path),
    help="Explicit chunk manifest path override (for single project).",
)
@click.option(
    "--profile", "profile_name",
    help="Explicit profile name (e.g. bridge2ai or neutral).",
)
@click.option(
    "--coverage-floor",
    default="pending",
    show_default=True,
    help="Receipt coverage floor: 'pending' or 'NUM/DEN' (e.g. '13/20') or decimal in (0, 1] (e.g. '0.65').",
)
@click.option(
    "--floor-basis",
    type=click.Choice(FLOOR_BASIS_CHOICES),
    default="receipted_part",
    show_default=True,
    help="What a registered floor divides by: the receipted part (values added after the receipt are "
         "reported, not gated; D-C 2026-10-23) or all receiptable leaves (the v2 form, no basis key).",
)
@click.option(
    "--partition", "partition",
    type=click.Choice(sorted(PARTITION_PROFILES)),
    help="Named audit partition bounds validated for a project (chorus: 80 paths, 12,288 bytes, "
         "4 workers; CHORUS only). Without it --max-paths, --max-inventory-bytes and --max-workers "
         "are required: partition bounds have no default.",
)
@click.option(
    "--max-paths",
    type=int,
    help="Override audit_limits.max_paths.",
)
@click.option(
    "--max-workers",
    type=int,
    help="Override audit_limits.max_workers.",
)
@click.option(
    "--max-calls",
    type=int,
    help="Override audit_limits.max_calls.",
)
@click.option(
    "--max-inventory-bytes",
    type=int,
    help="Override audit_limits.max_inventory_bytes.",
)
@click.option(
    "--max-input-tokens-per-call",
    type=int,
    help="Override audit_limits.max_input_tokens_per_call.",
)
@click.option(
    "--aggregate-input-tokens",
    type=int,
    help="Override audit_limits.aggregate_input_tokens.",
)
@click.option(
    "--aggregate-output-tokens",
    type=int,
    help=(
        "Explicit aggregate output token cap (must equal "
        "max_workers * worker_output_tokens + omission_output_tokens + integration_output_tokens)."
    ),
)
@click.option(
    "--worker-output-tokens",
    type=int,
    help="Override audit_limits.worker_output_tokens.",
)
@click.option(
    "--omission-output-tokens",
    type=int,
    help="Override audit_limits.omission_output_tokens.",
)
@click.option(
    "--integration-output-tokens",
    type=int,
    help="Override audit_limits.integration_output_tokens.",
)
@click.option(
    "--context-limit-tokens",
    type=int,
    help="Override audit_limits.context_limit_tokens and receipt.context_limit_tokens.",
)
@click.option(
    "--context-limit-basis",
    help="Override audit_limits.context_limit_basis and receipt.context_limit_basis.",
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
@click.option(
    "--replace",
    is_flag=True,
    help="Allow overwriting an existing registration or roster file with different bytes.",
)
def cli(
    projects: tuple[str, ...],
    all_projects: bool,
    labels: tuple[str, ...],
    label_prefix: str | None,
    replicates: int,
    arm: str,
    output_dir: Path,
    roster_path: Path | None,
    context_file: Path | None,
    context_dir: Path | None,
    source_manifest: Path,
    bundle: Path | None,
    chunk_manifest: Path | None,
    profile_name: str | None,
    coverage_floor: str,
    floor_basis: str,
    partition: str | None,
    max_paths: int | None,
    max_workers: int | None,
    max_calls: int | None,
    max_inventory_bytes: int | None,
    max_input_tokens_per_call: int | None,
    aggregate_input_tokens: int | None,
    aggregate_output_tokens: int | None,
    worker_output_tokens: int | None,
    omission_output_tokens: int | None,
    integration_output_tokens: int | None,
    context_limit_tokens: int | None,
    context_limit_basis: str | None,
    id_prefix: str,
    synthesize_draft_context: bool,
    dry_run: bool,
    check: bool,
    replace: bool = False,
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

    target_labels: list[str] = []
    if labels and label_prefix:
        raise click.UsageError("Specify either --label or --label-prefix, not both.")
    if label_prefix:
        if replicates < 1:
            raise click.UsageError("--replicates must be at least 1.")
        target_labels = [f"{label_prefix}_rep{i}" for i in range(1, replicates + 1)]
    elif labels:
        for raw_label in labels:
            for item in raw_label.split(","):
                item = item.strip()
                if item and item not in target_labels:
                    target_labels.append(item)
    else:
        raise click.UsageError("Specify --label (-l) or --label-prefix.")

    if context_file and len(target_projects) > 1:
        raise click.UsageError("--context can only be used with a single project. Use --context-dir for multiple projects.")
    if (bundle or chunk_manifest) and len(target_projects) > 1:
        raise click.UsageError("--bundle and --chunk-manifest can only be used with a single project.")

    audit_overrides: dict[str, Any] = {}
    for key, val in (
        ("max_paths", max_paths),
        ("max_workers", max_workers),
        ("max_calls", max_calls),
        ("max_inventory_bytes", max_inventory_bytes),
        ("max_input_tokens_per_call", max_input_tokens_per_call),
        ("aggregate_input_tokens", aggregate_input_tokens),
        ("aggregate_output_tokens", aggregate_output_tokens),
        ("worker_output_tokens", worker_output_tokens),
        ("omission_output_tokens", omission_output_tokens),
        ("integration_output_tokens", integration_output_tokens),
        ("context_limit_tokens", context_limit_tokens),
        ("context_limit_basis", context_limit_basis),
    ):
        if val is not None:
            audit_overrides[key] = val

    out_dir = output_dir.resolve()
    roster_stem = label_prefix or target_labels[0]
    target_roster_path = (roster_path or (out_dir / f"roster_{roster_stem}.json")).resolve()

    if check:
        click.echo(f"Checking registrations for {target_projects} x {target_labels} under {out_dir}...")
        for proj in target_projects:
            for lbl in target_labels:
                reg_file = out_dir / f"registration_{proj.lower()}_{lbl}.json"
                if not reg_file.is_file():
                    raise click.ClickException(f"Missing registration file: {reg_file}")
                raw = reg_file.read_bytes()
                sg.parse_registration(raw)
                click.echo(f"  ✓ {proj}: {reg_file.name}")
        if not target_roster_path.is_file():
            raise click.ClickException(f"Missing roster file: {target_roster_path}")
        pairs = [(p, lbl) for p in target_projects for lbl in target_labels]
        validate_roster_file(target_roster_path, pairs)
        click.echo(f"  ✓ Roster valid: {target_roster_path.name}")
        click.echo("All checks passed.")
        return

    if partition is None and any(audit_overrides.get(key) is None for key in PARTITION_KEYS):
        raise click.UsageError(
            "audit partition bounds have no default (D-C, 2026-10-23): pass --partition chorus for "
            "CHORUS, or --max-paths, --max-inventory-bytes and --max-workers sized for the project"
        )
    # Every target must accept the bounds before any registration is written.
    for proj in target_projects:
        try:
            resolve_audit_limits(proj, partition, audit_overrides or None, arm=arm)
        except ValueError as exc:
            raise click.UsageError(str(exc)) from exc

    registrations: list[dict[str, Any]] = []
    click.echo(f"Building registrations for {target_projects} (arm: {arm}, labels: {target_labels})...")

    for proj in target_projects:
        for lbl in target_labels:
            reg_file = out_dir / f"registration_{proj.lower()}_{lbl}.json"
            reg = build_registration(
                project=proj,
                label=lbl,
                arm=arm,
                registration_path=reg_file,
                id_prefix=id_prefix,
                context_path=context_file,
                context_dir=context_dir or out_dir,
                source_manifest_path=source_manifest,
                bundle_path=bundle,
                chunk_manifest_path=chunk_manifest,
                profile_name=profile_name,
                coverage_floor=coverage_floor,
                floor_basis=floor_basis,
                partition=partition,
                audit_limits=audit_overrides or None,
                synthesize_draft_context=synthesize_draft_context,
                write_to_disk=not dry_run,
                replace=replace,
            )
            registrations.append(reg)
            reg_sha = hashlib.sha256(sg.canonical(reg)).hexdigest()
            click.echo(f"  ✓ {proj}: registration_id={reg['registration_id']} sha256={reg_sha}")

    roster = build_roster(
        registrations=registrations,
        roster_path=target_roster_path,
        write_to_disk=not dry_run,
        replace=replace,
    )
    roster_sha = hashlib.sha256(sg.canonical(roster)).hexdigest()
    click.echo(f"  ✓ Roster with {len(roster['registrations'])} rows: {target_roster_path} (sha256={roster_sha})")

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
