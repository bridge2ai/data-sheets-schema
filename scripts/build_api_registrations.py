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

    # Any other project names bounds sized for it (see PARTITION_PROFILES) and an
    # aggregate input allowance, checked against an earlier run's record (#5155):
    python scripts/build_api_registrations.py -p AI_READI --max-paths N --max-inventory-bytes B --max-workers W --aggregate-input-tokens T --sizing-record AI_READI=<intermediate directory of an earlier AI_READI API run> -l 2026-10-DDa_claude-opus-5-api-generic-v10_rep1 -o data/registrations/generic_v10

    # Several projects in one roster, each with its own limits:
    python scripts/build_api_registrations.py -p CHORUS,AI_READI --project-limits CHORUS:partition=chorus --project-limits AI_READI:max_paths=N,max_inventory_bytes=B,max_workers=W,aggregate_input_tokens=T --sizing-record AI_READI=<directory> -l 2026-10-DDa_claude-opus-5-api-generic-v10_rep1 -o data/registrations/generic_v10

    # Dry-run validation without writing to disk:
    python scripts/build_api_registrations.py -p CHORUS --partition chorus -l 2026-10-DDa_claude-opus-5-api-generic-v10_rep1 --dry-run
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
import functools
import hashlib
import inspect
import json
import math
import os
import sys
import threading
import types
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _bootstrap_worktree(argv: list[str]) -> Path | None:
    """Select copied-script imports before any project package is imported."""
    selected = None
    # All non-flag CLI options take one value. Skip those values so a literal
    # label/path spelled '--worktree' can never change the import authority.
    flags = {"--all", "--synthesize-draft-context", "--dry-run", "--check", "--replace", "--help"}
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--":
            break
        if arg in ("--worktree", "-w") and index + 1 < len(argv):
            selected = argv[index + 1]
            index += 2
            continue
        elif arg.startswith("--worktree="):
            selected = arg.split("=", 1)[1]
        elif arg.startswith("-w") and len(arg) > 2:
            selected = arg[2:]
        elif arg not in flags and ((arg.startswith("--") and "=" not in arg) or (arg.startswith("-") and len(arg) == 2)):
            index += 2
            continue
        index += 1
    return Path(selected).resolve() if selected else None


_selected_bootstrap_root = _bootstrap_worktree(sys.argv[1:]) if __name__ == "__main__" else None
candidate_src = (_selected_bootstrap_root or ROOT) / "src"
if _selected_bootstrap_root is not None and not (candidate_src / "data_sheets_schema" / "api_runner.py").is_file():
    raise SystemExit("--worktree must contain the data_sheets_schema source package")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if candidate_src.is_dir() and str(candidate_src) not in sys.path:
    sys.path.insert(0, str(candidate_src))

if _selected_bootstrap_root is not None:
    import data_sheets_schema as _selected_package
    _expected_package = candidate_src / "data_sheets_schema"
    if any(Path(path).resolve() != _expected_package for path in _selected_package.__path__):
        raise SystemExit(
            "--worktree package imports are mixed with another checkout; use the selected checkout's own venv, "
            "or python -S with site-packages on PYTHONPATH"
        )

import click
import yaml

from data_sheets_schema import api_runner as api
from data_sheets_schema import receipt_completion as rc
from data_sheets_schema import shared_generation as sg
from data_sheets_schema.chunking import CONCAT_DIR as BUNDLE_DIR, manifest_for
from data_sheets_schema.cli.api import ARMS
from data_sheets_schema.profiles import profile_named, select_profile
from data_sheets_schema.registry import load_registry
from data_sheets_schema.resources import checkout_at, resource_path
from data_sheets_schema.schema_snapshot import capture_schema

DEFAULT_PROJECTS = ("CHORUS", "AI_READI", "CM4AI", "VOICE")
DEFAULT_CONDITION = "generic_v10"
DEFAULT_ID_PREFIX = "generic-v10"
DEFAULT_RECEIPT_ID = "generic-v10-receipt"
DEFAULT_PROVIDER = "LBL CBORG (proxy to Anthropic)"
DEFAULT_BASE_URL = "https://api.cborg.lbl.gov"
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_VOCABULARIES_PATH = Path("src/data_sheets_schema/b2ai_registry_vocabularies.yaml")


def _worktree_resources(function):
    """Scope explicit worktree resources in this single-threaded preparation CLI.

    Relative input/output arguments are relative to the selected worktree. The
    implicit calling convention is unchanged. A library caller selecting another
    tree must run without other threads because cwd is process-global; all exits
    restore the caller's cwd. Project resource readers then honor missing files
    in the selected checkout instead of falling back to another checkout.
    """
    signature = inspect.signature(function)
    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        worktree = bound.arguments.get("worktree")
        if worktree is None:
            return function(*args, **kwargs)
        selected = Path(worktree).resolve()
        if checkout_at(selected) != selected:
            raise ValueError("--worktree must be the root of a data-sheets-schema checkout")
        previous = Path.cwd()
        if previous != selected and threading.active_count() != 1:
            raise ValueError("--worktree resource selection requires a single-threaded process")
        bound.arguments["worktree"] = selected
        try:
            os.chdir(selected)
            return function(*bound.args, **bound.kwargs)
        finally:
            os.chdir(previous)
    return wrapped

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
    "context_limit_tokens": 1000000,
    "context_limit_basis": "Route context window 1,000,000 tokens; sized for largest bundle",
}

# The aggregate input allowance has no default either (#5155). The typed
# runtime admits each audit call only while the input already settled plus
# that call's count fits it, so too small an allowance refuses the plan
# midway, after the earlier calls are billed. Unlike the output allowance it
# cannot be derived from the caps: every call carries the complete record,
# core, receipt, inventory and bundle, and no record exists when the
# registration is built. A partition profile names the allowance validated
# for its bounds. Any other registration names it and is sized on a sizing
# record (`size_typed_audit_input`); a value below the sizing is refused
# before anything is written.

# Partition bounds have no default (D-C, owner decision 2026-10-23): no one
# setting plans every project. A top-level list too large for one worker is
# split between whole entries (A17, #5112), so at 80 paths / 12,288 bytes
# what refuses a record is the worker count: the v8 API full records need
# 5-6 workers (CHORUS), 8-9 (CM4AI), 9-11 (VOICE) and 12-15 (AI_READI). Four
# refuses every one of them, and the refusal comes after `full` and receipt
# completion are billed. 384 / 65,536 / 4 plans them but hands one worker
# about five times the inventory a CHORUS worker filled 64k of output with.
# `resolve_audit_limits` derives the aggregate output and call allowances
# from `max_workers`. A registration names its bounds, or a profile
# validated for its project; a multi-project build can give each project its
# own (`--project-limits`).
PARTITION_KEYS = ("max_paths", "max_inventory_bytes", "max_workers")
PARTITION_PROFILES: dict[str, dict[str, Any]] = {
    # What 2026-10-22a ran: 98 paths in three workers (35/54/9), the fullest
    # 39 bytes under the inventory bound, each using 14k-50k of its 64k.
    # Baseline arm only: 15 of the 18 CHORUS crate-arm records fail planning
    # under these bounds, all on the worker count (16 before A17), and the de
    # novo arm has no v10 evidence. Billed typed-audit input was 1,002,650
    # (10-20a, with a worker that hit the then 25k cap) and 1,148,972 (10-22a,
    # with an integration attempt that timed out) of the 4,000,000 allowance.
    # Sized on 10-22a's own record, the largest plan these bounds admit needs
    # about 1.92M at worst. Its expected integration call fits the window;
    # the worst case, every response at its cap, does not and is warned.
    "chorus": {"projects": ("CHORUS",), "arms": ("baseline",),
               "limits": {"max_paths": 80, "max_inventory_bytes": 12288, "max_workers": 4,
                          "aggregate_input_tokens": 4000000}},
}

# What a sizing depends on: the plan's shape, the stage caps that bound every
# response the integration call carries, and the allowance under test.
SIZING_KEYS = (*PARTITION_KEYS, "worker_output_tokens", "omission_output_tokens",
               "integration_output_tokens", "aggregate_input_tokens")
ADMISSION_CEILING_KEYS = ("context_limit_tokens", "max_input_tokens_per_call", "max_request_bytes")
# The retained sizing instrument counts text components and a carry allowance,
# not the complete canonical provider body. A supplied record can re-estimate
# token admission, but cannot establish a smaller wire-byte ceiling (#5211).
CALIBRATED_REQUEST_BYTE_CEILING = 32000000

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
    if limits.get("aggregate_input_tokens") is None:
        raise ValueError(
            "aggregate_input_tokens has no default without a partition profile (#5155): pass "
            "--aggregate-input-tokens, which is checked against a --sizing-record of the project"
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


def profile_sized(partition: str | None, limits: dict[str, Any]) -> bool:
    """Keep calibrated bounds/caps, with no smaller allowance or admission ceiling."""
    if partition is None:
        return False
    expected = {**DEFAULT_AUDIT_LIMITS, **PARTITION_PROFILES[partition]["limits"]}
    return (all(limits[key] == expected[key] for key in SIZING_KEYS if key != "aggregate_input_tokens")
            and limits["aggregate_input_tokens"] >= expected["aggregate_input_tokens"]
            and all(limits[key] >= expected[key] for key in ADMISSION_CEILING_KEYS))


def profile_covered(project: str, arm: str | None, limits: dict[str, Any]) -> bool:
    """A profile validated for this project and arm covers these limits, named or not.

    A registration does not record how its limits were chosen. Equal partition
    bounds and output caps may inherit calibration only when aggregate input
    and every per-call admission ceiling are at least as permissive.
    """
    return any(project in profile["projects"] and arm in profile["arms"] and profile_sized(name, limits)
               for name, profile in PARTITION_PROFILES.items())


# Typed-audit input sizing (#5155), calibrated on CHORUS 2026-10-22a.
# - The original render matched that run's saved text with receipt-carry and
#   padded-owner allowances, plus the D35 worker sentence change. A14 changes
#   the schema context and omission wire: current omission sizing now uses
#   the sealed runtime formatter, with exact owners when the historical record
#   can be interpreted and a declared padding allowance otherwise. Worker schema context
#   retains a conservative description allowance; integration excludes its
#   responses. Current-runtime parity checks all calls, separately from the
#   historical calibration below.
# - Its worker, omission and integration requests counted 2.25, 2.35 and
#   1.75 bytes per token.
# - Its integration request carried four responses, the workers' as base64
#   envelopes: 131,507 output tokens, thinking included. Over the rendered base
#   (163,447 at 2.0 bytes per token) they cost 153,467 of its 316,914 counted
#   input tokens: 1.167 per output token.
# - The runtime admits a call only if its count plus its output cap fits
#   context_limit_tokens and the count fits max_input_tokens_per_call, and
#   counts each stage only on reaching it: every earlier stage is billed first.
#
# The integration request is sized two ways:
# - Expected, which refuses the registration when it cannot fit: the sizing
#   record's own plan, each response at the mean fraction of its cap that
#   10-22a's usage ledger shows, at 1.2 input tokens per output token.
# - Worst, which is warned and recorded and sizes the aggregate allowance:
#   max_workers responses and the omission's, each at its whole cap, at 3.5
#   input tokens per output token. That is the ~3 per text token 10-22a's
#   envelopes cost, for a response written as text with no thinking.
SIZING_INSTRUMENT = "typed_audit_input_sizing_v3"
SIZING_BYTES_PER_TOKEN = 2.0
SIZING_INPUT_TOKENS_PER_RESPONSE_TOKEN = 3.5
SIZING_EXPECTED_INPUT_TOKENS_PER_RESPONSE_TOKEN = 1.2
# 10-22a's typed workers used 50,130, 43,348 and 14,032 of 64,000 (mean
# 0.55995); its omission call 23,997 of 32,000 (0.7499).
SIZING_WORKER_RESPONSE_CAP_FRACTION = 0.56
SIZING_OMISSION_RESPONSE_CAP_FRACTION = 0.75
SIZING_STAGES = ("worker", "omission", "integration")
# F2 of the A17 review: the cap's only evidence is six CHORUS workers.
SIZING_WORKER_CAP_NOTE = ("worker_output_tokens is calibrated on six CHORUS workers of 3-12 KB inventory, "
                          "the largest using 53,204 of 64,000; a worker that reaches its cap ends the audit "
                          "after the earlier stages are billed")
_STAND_IN_DIGEST = "0" * 64
_SIZING_CATALOGS: dict[bytes, dict[str, Any]] = {}
# Literals of typed_audit_runtime's binding and shared_generation's generation context.
_BINDING_SCOPE = "Declared response association, not provider authentication or scientific approval."
_GENERATION_SCOPE = ("Caller-declared generation scope, source policy and vocabulary; "
                     "not a scientific applicability or support verdict.")


@dataclass(frozen=True)
class SizingRecord:
    """A phase-1 record of the project from an earlier run, with its core and coverage receipt."""

    full: Path
    core: Path
    receipt: Path

    @classmethod
    def in_directory(cls, directory: Path | str, project: str) -> "SizingRecord":
        """An API run's intermediate directory: {P}_full.yaml, {P}_core.yaml, {P}_coverage_receipt.yaml."""
        root = Path(directory)
        return cls(*(root / f"{project}_{name}.yaml" for name in ("full", "core", "coverage_receipt")))


SIZING_RECORD_FORMAT = "typed_audit_input_sizing_record_v1"


def sizing_path(registration_path: Path | str) -> Path:
    """Where a registration's input sizing is written: beside it, as <stem>.sizing.json."""
    path = Path(registration_path)
    return path.with_name(path.stem + ".sizing.json")


def _require_request_byte_calibration(limits: dict[str, Any]) -> None:
    if limits["max_request_bytes"] < CALIBRATED_REQUEST_BYTE_CEILING:
        raise ValueError(
            f"max_request_bytes {limits['max_request_bytes']:,} is below the calibrated byte ceiling "
            f"{CALIBRATED_REQUEST_BYTE_CEILING:,}; a sizing record estimates text/token demand, not "
            "complete canonical request bytes. A lower byte ceiling needs complete wire-byte calibration (#5211)"
        )


def _admissible_input_tokens(limits: dict[str, Any]) -> dict[str, int]:
    return {stage: min(limits["max_input_tokens_per_call"],
                       limits["context_limit_tokens"] - limits[f"{stage}_output_tokens"])
            for stage in SIZING_STAGES}


def check_registration_sizing(registration_path: Path | str, raw: bytes) -> dict[str, Any] | None:
    """The sizing record beside a registration, checked against its bytes.

    Returns None when a partition profile covers the registration's limits.
    Otherwise a sizing record must name these exact registration bytes and
    admit its limits, or ValueError is raised.
    """
    reg = json.loads(raw)
    limits = reg["audit_limits"]
    _require_request_byte_calibration(limits)
    arm = next((key for key, value in ARMS.items() if value[0] == reg["run"]["arm"]), None)
    covered = profile_covered(reg["run"]["project"], arm, limits)
    path = sizing_path(registration_path)
    if not path.is_file():
        if covered:
            return None
        raise ValueError(f"{registration_path}: no partition profile covers its aggregate_input_tokens "
                         f"and no sizing record is beside it ({path.name})")
    record = json.loads(path.read_bytes())
    sizing = record.get("sizing") if isinstance(record, dict) else None
    if (not isinstance(sizing, dict) or record.get("format") != SIZING_RECORD_FORMAT
            or record.get("registration_sha256") != hashlib.sha256(raw).hexdigest()):
        raise ValueError(f"{path}: is not the sizing record of these registration bytes")
    if (sizing["aggregate_input_tokens"] > limits["aggregate_input_tokens"]
            or any(sizing[f"{stage}_input_tokens"] > room
                   for stage, room in _admissible_input_tokens(limits).items())):
        raise ValueError(f"{path}: its sizing does not admit the registered limits")
    return record


def _typed_contracts() -> dict[str, Any]:
    """typed_audit._derive_uncached's output contracts; a test checks they still agree."""
    from data_sheets_schema import audit_batch_format as output_format
    return {stage: {"contract": output_format.contract(stage, version=2),
                    "rendered": output_format.render(stage, version=2),
                    "saved_response": {"kind": f"typed_audit_{stage}_response_v1",
                        "required_fields": ["kind", "packet_sha256", "request_sha256", "response",
                                            "worker_id" if stage == "worker" else "typed_index_sha256"],
                        "response_encoding": "Exact UTF-8 inner JSON bytes as base64, sha256 and bytes.",
                        "authority": "A declared request/response association, not provider authentication."}}
            for stage in ("worker", "integration")}


def render_typed_audit_inputs(
    project: str,
    limits: dict[str, Any],
    registration: dict[str, Any],
    *,
    record: bytes,
    core: bytes | None,
    receipt: bytes,
    context: bytes,
    schema_snapshot,
) -> dict[str, Any]:
    """Text bytes of each typed-audit request for ``record``'s plan, rendered as the runtime renders them.

    The inner requests follow typed_audit, the outer parts typed_audit_runtime.
    Digests and identifiers are stand-ins of the same width; the receipt carry
    is an allowance. The omission request uses the runtime's sealed S7 formatter
    and complete projected schema. Uninterpretable historical owner classes keep
    a declared padding allowance; interpretable records use their actual owners.
    The integration request is rendered without its worker and omission
    responses, at the plan's worker count and at ``max_workers``;
    `size_typed_audit_input` adds the responses. A record that does not plan
    under the bounds raises AuditBatchError. The inner requests are returned
    too, for comparison with the typed packet's.
    """
    from data_sheets_schema import (audit_batches, audit_omissions as omissions, audit_protocol,
                                    evidence_assertions as evidence, typed_audit as typed,
                                    typed_audit_runtime as runtime)
    inputs = registration["inputs"]

    def read(pin):
        return Path(pin["path"]).read_bytes() if pin else None

    bundle, manifest, source_manifest = (read(inputs[key]) for key in ("bundle", "chunk_manifest", "source_manifest"))
    record_text = record.decode("utf-8")
    plan = audit_batches.make_plan(record_text, version=2, **{key: limits[key] for key in PARTITION_KEYS})
    identity = sg.canonical(sg.schema_pin(schema_snapshot))
    if identity not in _SIZING_CATALOGS:
        _SIZING_CATALOGS[identity] = omissions._schema(Path(schema_snapshot.sources[0][1]),
                                                       schema_snapshot=schema_snapshot)
    schema = {key: value for key, value in _SIZING_CATALOGS[identity].items() if key not in ("classes", "slots")}
    context_doc = json.loads(context)
    contracts = _typed_contracts()
    shared = typed._json({"protocol": audit_protocol.select(audit_protocol.TYPED), "original_full": record_text,
        "original_core": core.decode("utf-8") if core else None, "bundle": bundle.decode("utf-8"),
        "manifest": manifest.decode("utf-8"), "receipt": receipt.decode("utf-8"), "context": context_doc,
        "schema": schema, "registered_provenance": (typed._source_authority(source_manifest, project)
                                                    if source_manifest is not None else None)}).decode("utf-8")

    profile = copy.deepcopy(inputs["profile"])
    if profile["vocabulary"] is not None:
        profile["vocabulary"] = {"identity": profile["vocabulary"],
                                 "raw_text": read(inputs["profile"]["vocabulary"]).decode("utf-8")}
    generation = sg.GENERATION_CONTEXT_HEADER + sg.canonical({
        "context": {"identity": inputs["context"], "raw_json": context.decode("utf-8")}, "profile": profile,
        "source_manifest": inputs["source_manifest"], "scope": _GENERATION_SCOPE}).decode("utf-8")
    # The carry restates the registration twice beside about 7 KB of fixed
    # identities, and lists the receipt completion's unsupported paths: at
    # most every inventory path.
    paths = [row["path"] for row in plan["inventory"]["values"]]
    carry = len(rc.AUDIT_HEADER) + 2 * len(sg.canonical(registration)) + 8192 + len(sg.canonical(paths))
    common = sum(len(text.encode("utf-8")) for text in (
        runtime.SYSTEM, sg.policy_text(version=registration["selection"]["version"]), api.shared_evidence_contract(),
        sg._schema_context(types.SimpleNamespace(full_schema=schema_snapshot), record_text), generation)) + carry

    requests: dict[str, Any] = {"workers": []}

    def call(stage, inner):
        binding = {"protocol": registration["selection"]["protocol"], "generation_id": "0" * 32,
                   "registration_sha256": _STAND_IN_DIGEST, "packet_sha256": _STAND_IN_DIGEST, "stage": stage,
                   "inner_request_sha256": _STAND_IN_DIGEST, "scope": _BINDING_SCOPE}
        if stage["phase"] == runtime.OMISSION_PHASE:
            binding["packet_inner_request_sha256"] = _STAND_IN_DIGEST
        return common + len(("# Registered audit request identity\n\n" + sg.canonical(binding).decode("utf-8")
                             + "# Exact typed stage request\n\n" + sg.canonical(inner).decode("utf-8")).encode("utf-8"))

    workers = []
    for worker in plan["workers"]:
        stage = typed._json({"stage": "worker", "shared_context_sha256": _STAND_IN_DIGEST, "plan_sha256": plan["sha256"],
                             "assignment": worker, "inventory": plan["inventory"],
                             "output_contract": contracts["worker"]}).decode("utf-8")
        requests["workers"].append({"kind": "typed_audit_worker_request_v1", "request_sha256": _STAND_IN_DIGEST,
                                    "payload": {"packet_sha256": _STAND_IN_DIGEST, "worker_id": worker["id"],
                                                "shared_context": shared, "stage": stage}})
        workers.append(call({"phase": runtime.WORKER_PHASE, "worker_id": worker["id"]}, requests["workers"][-1]))

    # Share the runtime payload and selected-wire formatters (F1, #5162).
    # A historical sizing receipt may name an older/different bundle: estimate
    # its bytes without granting it execution authority or rewriting its input.
    chunks, _ = evidence.source_chunks_from_bytes(bundle, manifest)
    receipt_doc = yaml.safe_load(receipt)
    prior = {entry["id"]: entry.get("status") for entry in (receipt_doc or {}).get("chunks", [])
             if isinstance(entry, dict) and "id" in entry} if isinstance(receipt_doc, dict) else {}
    catalog = _SIZING_CATALOGS[identity]
    document = yaml.safe_load(record_text)
    owner_note = None
    owner_warning = None
    try:
        owners = omissions._owners(document, catalog, context_doc["vocabulary"])
    except ValueError as exc:
        # Historical sizing already allowed records from earlier schemas and
        # other arms. Preserve that estimate, with a visible allowance, without
        # weakening the runtime's strict owner traversal.
        owners = {}
        width = max([32, *[len(sg.canonical(name)) for name in catalog["classes"]]])

        def mappings(value, pointer):
            if isinstance(value, dict):
                owners[pointer] = "X" * width
                for key, child in value.items():
                    mappings(child, pointer + "/" + str(key).replace("~", "~0").replace("/", "~1"))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    mappings(child, f"{pointer}/{index}")

        mappings(document, "")
        cause = "historical sizing record has no current typed owner traversal"
        if str(exc) == "missing explicitly supplied vocabulary":
            cause = "registered context vocabulary prevents typed owner traversal"
            owner_warning = (
                "registered context is missing explicitly supplied vocabulary required by the sizing record's "
                "schema slots; a live record carrying those slots (including null values) would be refused "
                "during typed owner traversal, after `full` and receipt completion may already be billed")
        owner_note = (f"{cause} ({exc}); "
                      f"omission owner classes use a {width}-byte name allowance for every mapping; "
                      "this is an estimate, not validation of an executable packet")
    prepared = omissions._render_prepared(record=record, bundle=bundle, manifest=manifest, receipt=receipt,
        context=context, context_doc=context_doc, catalog=catalog,
        owners=owners,
        chunks=chunks, prior=prior, max_output_tokens=limits["omission_output_tokens"],
        max_request_bytes=limits["max_request_bytes"])
    requests["omission"] = typed._render_omission_wire_request(prepared, omission_wire=typed.SHARED_OMISSION_WIRE)
    omission = call({"phase": runtime.OMISSION_PHASE}, requests["omission"])

    owner_of = {path: worker["id"] for worker in plan["workers"] for path in worker["paths"]}

    def integration_request(count):
        ids = [f"worker_{i + 1:04d}" for i in range(count)]
        index = {"schema_version": 2, "kind": "audit_batch_index_v2", "plan_sha256": _STAND_IN_DIGEST,
                 "original_full_sha256": _STAND_IN_DIGEST, "sha256": _STAND_IN_DIGEST, "findings": [],
                 "workers": [{"id": key, "sha256": _STAND_IN_DIGEST, "bytes": 0} for key in ids],
                 "rows": [{"path": path, "worker_id": owner_of[path], "sha256": _STAND_IN_DIGEST} for path in paths]}
        return {"kind": "typed_audit_index_v1", "packet_sha256": _STAND_IN_DIGEST, "sha256": _STAND_IN_DIGEST,
                "index": index, "omission_check": {},
                "integration_request": {"kind": "typed_audit_integration_request_v1", "request_sha256": _STAND_IN_DIGEST,
                    "payload": {"stage": "integration", "packet_sha256": _STAND_IN_DIGEST, "shared_context": shared,
                                "proposal_index": index, "workers": {key: "" for key in ids}, "omission_response": "",
                                "omission_check": {}, "output_contract": contracts["integration"]}}}

    requests["integration"] = integration_request(len(plan["workers"]))
    return {"plan_workers": len(plan["workers"]), "worker_bytes": max(workers), "omission_bytes": omission,
            "integration_base_bytes": call({"phase": runtime.INTEGRATION_PHASE}, requests["integration"]),
            "integration_largest_base_bytes": call({"phase": runtime.INTEGRATION_PHASE},
                                                   integration_request(limits["max_workers"])),
            "carry_allowance_bytes": carry, "owner_allowance_note": owner_note,
            "owner_allowance_warning": owner_warning,
            "shared_context": shared, "requests": requests}


def size_typed_audit_input(
    project: str,
    limits: dict[str, Any],
    registration: dict[str, Any],
    *,
    sizing_record: SizingRecord,
    context: bytes,
    schema_snapshot,
    stand_in: bool = False,
) -> dict[str, Any]:
    """Input tokens of the largest typed-audit plan these limits admit, sized on an earlier record.

    Every call carries the complete record, core, receipt, inventory and
    bundle, so each of ``max_workers`` workers is sized at the record plan's
    largest worker. The integration call is sized as expected, for the
    record's own plan with each response at 10-22a's mean use of its cap,
    and at worst, for ``max_workers`` with every response at its cap; the
    aggregate takes the worst. Bytes become tokens at SIZING_BYTES_PER_TOKEN.
    Also returns the input each stage's call may take, by the runtime's
    admission rule, and warns when the worst case would not fit. This is an
    estimate for the record supplied, not a bound on a later record.

    The record must declare the registration's project and arm in its
    generator header (``# D4D Datasheet for PROJECT Dataset`` and ``# Arm:
    ...``); ``stand_in`` sizes on another project's or arm's record anyway,
    and says so in the result.
    """
    from data_sheets_schema.audit_batches import AuditBatchError
    files = {name: Path(getattr(sizing_record, name)) for name in ("full", "core", "receipt")}
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"sizing record for {project} is incomplete: missing {', '.join(missing)}")
    raw = {name: path.read_bytes() for name, path in files.items()}
    header = []
    for line in raw["full"].decode("utf-8", "replace").splitlines():
        if not line.startswith("#"):
            break
        header.append(line.strip())
    expected = [f"# D4D Datasheet for {project} Dataset", f"# Arm: {registration['run']['arm']}"]
    own = header[:1] == expected[:1] and expected[1] in header
    if not own and not stand_in:
        raise ValueError(f"sizing record {files['full']} is not a {project} record of this arm: its header "
                         f"reads {(header[:1] or [''])[0]!r} and {next((h for h in header if h.startswith('# Arm:')), '')!r}, "
                         f"not {expected[0]!r} and {expected[1]!r}; size on the project's own record")
    try:
        rendered = render_typed_audit_inputs(project, limits, registration, record=raw["full"], core=raw["core"],
                                             receipt=raw["receipt"], context=context, schema_snapshot=schema_snapshot)
    except AuditBatchError as exc:
        raise ValueError(f"sizing record {files['full']} does not plan under these bounds ({exc}); a {project} "
                         "record like it would be refused at planning, after `full` and receipt completion "
                         "are billed") from None

    def tokens(size):
        return math.ceil(size / SIZING_BYTES_PER_TOKEN)

    planned, workers = rendered["plan_workers"], limits["max_workers"]
    worker, omission = tokens(rendered["worker_bytes"]), tokens(rendered["omission_bytes"])
    expected_responses = math.ceil(SIZING_EXPECTED_INPUT_TOKENS_PER_RESPONSE_TOKEN * (
        planned * SIZING_WORKER_RESPONSE_CAP_FRACTION * limits["worker_output_tokens"]
        + SIZING_OMISSION_RESPONSE_CAP_FRACTION * limits["omission_output_tokens"]))
    worst_responses = math.ceil(SIZING_INPUT_TOKENS_PER_RESPONSE_TOKEN * (
        workers * limits["worker_output_tokens"] + limits["omission_output_tokens"]))
    expected = tokens(rendered["integration_base_bytes"]) + expected_responses
    worst = tokens(rendered["integration_largest_base_bytes"]) + worst_responses
    admissible = _admissible_input_tokens(limits)
    warnings = []
    if worst > admissible["integration"]:
        warnings.append(f"at worst, {workers} worker responses and the omission's at their caps, the integration "
                        f"call would need {worst:,} input tokens, over the {admissible['integration']:,} it may take")
    if rendered.get("owner_allowance_warning"):
        warnings.append(rendered["owner_allowance_warning"])
    return {"instrument": SIZING_INSTRUMENT, "sizing_record": {name: sg.file_pin(path) for name, path in files.items()},
            "stand_in": not own,
            "bytes_per_token": SIZING_BYTES_PER_TOKEN,
            "expected_responses": {"input_tokens_per_response_token": SIZING_EXPECTED_INPUT_TOKENS_PER_RESPONSE_TOKEN,
                                   "worker_cap_fraction": SIZING_WORKER_RESPONSE_CAP_FRACTION,
                                   "omission_cap_fraction": SIZING_OMISSION_RESPONSE_CAP_FRACTION},
            "worst_responses": {"input_tokens_per_response_token": SIZING_INPUT_TOKENS_PER_RESPONSE_TOKEN,
                                "cap_fraction": 1.0},
            "plan_workers": planned, "max_workers": workers, "worker_input_tokens": worker,
            "omission_input_tokens": omission, "integration_base_input_tokens": tokens(rendered["integration_base_bytes"]),
            "integration_response_input_tokens": expected_responses, "integration_input_tokens": expected,
            "integration_worst_response_input_tokens": worst_responses, "integration_worst_input_tokens": worst,
            "aggregate_input_tokens": workers * worker + omission + worst,
            "admissible_input_tokens": admissible, "warnings": warnings,
            "notes": [SIZING_WORKER_CAP_NOTE, *([rendered["owner_allowance_note"]] if rendered["owner_allowance_note"] else [])]}


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


@_worktree_resources
def build_draft_context(
    project: str,
    source_manifest_path: Path | str | None = None,
    context_path: Path | str | None = None,
    write_to_disk: bool = True,
    worktree: Path | str | None = None,
) -> dict[str, Any]:
    """Synthesize a compliant root-only omission_context_v1 draft document.

    Delegates to scripts/build_draft_contexts.py so both synthesizers share one
    implementation, profile/vocabulary policy, and canonical byte serialization (#5120).
    """
    from scripts.build_draft_contexts import (
        build_draft_scope_context,
        load_project_manifest_data,
        serialize_draft_context,
    )

    manifest_data = load_project_manifest_data(project, source_manifest_path)
    doc = build_draft_scope_context(project, manifest_data)

    vocab_path = resource_path(DEFAULT_VOCABULARIES_PATH)
    if vocab_path.is_file():
        declared_prof = str(manifest_data.get("profile") or "").strip().lower()
        if declared_prof != "neutral":
            vocab_data = yaml.safe_load(vocab_path.read_text(encoding="utf-8")) or {}
            doc["vocabulary"] = vocab_data.get("vocabularies", {})
        else:
            doc["vocabulary"] = {}
    elif worktree is not None:
        raise FileNotFoundError(f"selected worktree vocabulary is missing: {vocab_path}")

    if write_to_disk and context_path is not None:
        target = Path(context_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(serialize_draft_context(doc))

    return doc


def _write_outputs(outputs: list[tuple[Path, bytes]], replace: bool) -> None:
    """Write every file only after checking that none would overwrite different bytes."""
    for target, data in outputs:
        if target.exists() and not replace and target.read_bytes() != data:
            raise FileExistsError(f"{target} already exists with different bytes; pass --replace to overwrite")
    for target, data in outputs:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def build_registration(project: str, label: str, *, write_to_disk: bool = True, replace: bool = False,
                       **options: Any) -> dict[str, Any]:
    """Build, check and (unless ``write_to_disk`` is false) write one registration.

    Takes `prepare_registration`'s options. Nothing is written unless every
    check passed, including the input sizing.
    """
    reg, outputs, _ = prepare_registration(project, label, **options)
    if write_to_disk:
        _write_outputs(outputs, replace)
    return reg


@_worktree_resources
def prepare_registration(
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
    sizing_record: SizingRecord | Path | str | None = None,
    sizing_stand_in: bool = False,
    worktree: Path | str | None = None,
) -> tuple[dict[str, Any], list[tuple[Path, bytes]], dict[str, Any] | None]:
    """Build a complete shared_generation_registration_v1 document without writing it.

    Modelled on `tests/test_shared_generation_selection.py:17-52`.
    Validates output via `shared_generation.parse_registration`. Returns the
    registration, the files to write (a synthesized draft context, the
    registration, and its sizing record) and the input sizing, if one ran.

    An aggregate_input_tokens not covered by a partition profile is sized on
    ``sizing_record`` (a `SizingRecord`, or an API run's intermediate
    directory), which must be the project's own, of the same arm, unless
    ``sizing_stand_in``.
    It is refused when a typed-audit call cannot fit its window or the
    allowance is below the sizing (#5155).
    """
    if arm not in ARMS:
        raise ValueError(f"unknown arm '{arm}'; must be one of {sorted(ARMS.keys())}")
    # Library callers need the same refusal-before-write guarantee as the
    # CLI precheck: context synthesis below can create files and directories.
    active_audit_limits = resolve_audit_limits(project, partition, audit_limits, arm=arm)
    arm_display, method, pattern, _ = ARMS[arm]
    root_dir = Path(worktree).resolve() if worktree is not None else ROOT
    kids_first_manifest = (
        root_dir / "notes" / "matched_cborg_2026-09-13" / "kids_first" / "manifest.yaml"
    )

    # Resolve manifest
    default_study_manifest = (root_dir / "data" / "preprocessed" / "source_manifest.yaml").resolve()
    sm_resolved: Path | None = None
    if source_manifest_path is not None:
        raw_sm = Path(source_manifest_path)
        p = raw_sm.resolve()
        if not p.is_file() and not raw_sm.is_absolute():
            alt = (root_dir / raw_sm).resolve()
            if alt.is_file():
                p = alt
        if p.is_file():
            sm_resolved = p
        else:
            raise FileNotFoundError(f"source manifest not found: {source_manifest_path}")
    else:
        if project.upper() == "KIDS_FIRST" and kids_first_manifest.is_file():
            sm_resolved = kids_first_manifest.resolve()
        elif default_study_manifest.is_file():
            sm_resolved = default_study_manifest

    reg_registry = load_registry(sm_resolved)
    if (
        not reg_registry.declares(project)
        and project.upper() == "KIDS_FIRST"
        and sm_resolved == default_study_manifest
        and kids_first_manifest.is_file()
    ):
        sm_resolved = kids_first_manifest.resolve()
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
            root_dir / "data" / "omission_contexts" / f"{project.lower()}_omission_context.json",
            root_dir / "data" / "omission_contexts" / f"{project}_context.json",
            resolved_reg_path.parent / f"{project.lower()}_omission_context.json",
            resolved_reg_path.parent / f"{project}_context.json",
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
            from scripts.build_draft_contexts import serialize_draft_context

            # Written with the registration, once every check has passed.
            draft_doc = build_draft_context(
                project=project,
                source_manifest_path=sm_resolved,
                context_path=target_context,
                write_to_disk=False,
                worktree=worktree,
            )
            resolved_context = target_context.resolve()
            resolved_context_raw = serialize_draft_context(draft_doc)
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
        prof_vocab_pin = sg.file_pin(vocab_path)

    # Capture schema snapshots
    full_schema = capture_schema(api.FULL_SCHEMA_PATH, strict=True)
    full_schema_pin = sg.schema_pin(full_schema)
    core_schema_pin = sg.schema_pin(capture_schema(api.CORE_SCHEMA_PATH, strict=True))

    # Resolve runtime settings
    # An explicitly selected checkout must provide its declared configuration;
    # missing files cannot silently select the API's built-in fallback settings.
    if worktree is not None and not resource_path(api.DETERMINISTIC_CONFIG).is_file():
        raise FileNotFoundError(f"selected worktree runtime config is missing: {api.DETERMINISTIC_CONFIG}")
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
    _require_request_byte_calibration(active_audit_limits)

    sizing = None
    if sizing_record is not None or not profile_covered(project, arm, active_audit_limits):
        if sizing_record is None:
            raise ValueError(
                f"{project}: an audit-limit combination no partition profile covers needs a sizing record (#5155, #5211); "
                f"pass --sizing-record {project}=<intermediate directory of an earlier {project} API run>"
            )
        if not isinstance(sizing_record, SizingRecord):
            sizing_record = SizingRecord.in_directory(sizing_record, project)
        context_raw = resolved_context_raw if resolved_context_raw is not None else resolved_context.read_bytes()
        sizing = size_typed_audit_input(project, active_audit_limits, reg, sizing_record=sizing_record,
                                        context=context_raw, schema_snapshot=full_schema, stand_in=sizing_stand_in)
        # The runtime counts and admits each stage only on reaching it, so a
        # call that cannot fit is refused after every earlier stage is billed.
        # Integration is judged at the record's own plan with responses at
        # 10-22a's mean use of their caps; its worst case is only warned.
        for stage in SIZING_STAGES:
            need, room = sizing[f"{stage}_input_tokens"], sizing["admissible_input_tokens"][stage]
            if need > room:
                detail = (f" for its own plan ({sizing['plan_workers']} worker responses and the omission's at "
                          f"10-22a's mean use of their caps; {sizing['integration_base_input_tokens']:,} without them)"
                          if stage == "integration" else "")
                raise ValueError(
                    f"{project}: the typed-audit {stage} call sized on {sizing_record.full} needs {need:,} input "
                    f"tokens{detail}, over the {room:,} it may take: context_limit_tokens "
                    f"{active_audit_limits['context_limit_tokens']:,} less {stage}_output_tokens "
                    f"{active_audit_limits[stage + '_output_tokens']:,}, and no more than max_input_tokens_per_call "
                    f"{active_audit_limits['max_input_tokens_per_call']:,}. The runtime would refuse it only on "
                    f"reaching it, after billing every earlier stage (#5155)"
                )
        if active_audit_limits["aggregate_input_tokens"] < sizing["aggregate_input_tokens"]:
            raise ValueError(
                f"{project}: aggregate_input_tokens {active_audit_limits['aggregate_input_tokens']:,} is below the "
                f"typed-audit input sized on {sizing_record.full}: {sizing['max_workers']} workers x "
                f"{sizing['worker_input_tokens']:,} + omission {sizing['omission_input_tokens']:,} + integration "
                f"at worst {sizing['integration_worst_input_tokens']:,} = {sizing['aggregate_input_tokens']:,}. A "
                f"plan that size could be refused midway, after its first stages are billed (#5155)"
            )

    outputs = []
    if resolved_context_raw is not None:
        outputs.append((resolved_context, resolved_context_raw))
    outputs.append((resolved_reg_path, canonical_bytes))
    if sizing is not None:
        # The registration format is closed (shared_generation.parse_registration),
        # so the sizing goes beside it, bound to the registration's bytes.
        sidecar = sizing_path(resolved_reg_path)
        sidecar_bytes = sg.canonical({"format": SIZING_RECORD_FORMAT, "registration_path": str(resolved_reg_path),
                                      "registration_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
                                      "sizing": sizing})
        outputs.append((sidecar, sidecar_bytes))
        sizing = {**sizing, "sidecar": {"path": str(sidecar), "sha256": hashlib.sha256(sidecar_bytes).hexdigest()}}
    return reg, outputs, sizing


def build_roster(
    registrations: list[dict[str, Any]],
    roster_path: Path | str | None = None,
    write_to_disk: bool = True,
    replace: bool = False,
    *,
    pending_registration_writes: bool = False,
) -> dict[str, Any]:
    """Build a shared_generation_batch_roster_v2 document from registration dicts.

    Ensures no duplicate (project, label) rows, paths, or registration_ids, and
    pins each row's registration SHA-256 digest. Existing files retain their
    actual serialization unless the caller will write the supplied canonical
    registrations after preparing the entire transaction.
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
        reg_bytes = (reg_file.read_bytes()
                     if reg_file.is_file() and not pending_registration_writes else sg.canonical(reg))
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


@_worktree_resources
def verify_registration_input_pins(
    reg: dict[str, Any],
    *,
    worktree: Path | str | None = None,
) -> None:
    """Verify current file bytes and complete full/core schema import closures."""
    reg = sg.parse_registration(sg.canonical(reg))
    inputs = reg.get("inputs") or {}
    runtime = reg.get("runtime") or {}
    pin_entries: list[tuple[str, Any]] = [
        ("inputs.bundle", inputs.get("bundle")),
        ("inputs.chunk_manifest", inputs.get("chunk_manifest")),
        ("inputs.source_manifest", inputs.get("source_manifest")),
        ("inputs.context", inputs.get("context")),
        ("inputs.profile.vocabulary", (inputs.get("profile") or {}).get("vocabulary")),
        ("runtime.config", runtime.get("config")),
    ]
    if reg["format"] == sg.ROUTING_FORMAT:
        pin_entries.append(("routing.artifact", reg["routing"]["artifact"]))
    for schema in ("full_schema", "core_schema"):
        pin_entries.extend((f"inputs.{schema}.sources[{index}]", pin)
                           for index, pin in enumerate(inputs[schema]["sources"]))
    captured: dict[str, bytes] = {}
    for label, pin in pin_entries:
        if pin is None:
            continue
        raw_path = pin["path"]
        expected_sha = pin["sha256"]
        p = Path(raw_path)
        if not p.is_file():
            raise FileNotFoundError(f"Pinned {label} file not found on disk: {raw_path}")
        if p.stat().st_size > sg.MAX_AUTHORITY_BYTES:
            raise ValueError(f"Pinned {label} file exceeds the authority byte bound: {raw_path}")
        raw_bytes = captured.get(raw_path)
        if raw_bytes is None:
            with p.open("rb") as stream:
                raw_bytes = stream.read(sg.MAX_AUTHORITY_BYTES + 1)
            if len(raw_bytes) > sg.MAX_AUTHORITY_BYTES:
                raise ValueError(f"Pinned {label} file exceeds the authority byte bound: {raw_path}")
            captured[raw_path] = raw_bytes
        actual_sha = hashlib.sha256(raw_bytes).hexdigest()
        if actual_sha.lower() != str(expected_sha).lower():
            raise ValueError(
                f"Pinned {label} SHA-256 mismatch for {p}: expected {expected_sha}, got {actual_sha}"
            )
        expected_bytes = pin["bytes"]
        if len(raw_bytes) != expected_bytes:
            raise ValueError(
                f"Pinned {label} byte-length mismatch for {p}: expected {expected_bytes}, got {len(raw_bytes)}"
            )
    for schema in ("full_schema", "core_schema"):
        selected = inputs[schema]
        allowed = {pin["path"] for pin in selected["sources"]}
        def read_selected(path):
            if str(path) not in allowed:
                raise ValueError(f"Pinned {schema} import is outside the registered closure: {path}")
            return captured[str(path)]
        actual = capture_schema(Path(selected["root"]), strict=True, read_bytes=read_selected)
        if sg.schema_pin(actual) != selected:
            raise ValueError(f"Pinned {schema} closure/order differs from its actual imports")


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


PROJECT_LIMIT_KEYS = ("partition", *PARTITION_KEYS, "max_calls", "max_input_tokens_per_call",
                      "aggregate_input_tokens", "aggregate_output_tokens", "worker_output_tokens",
                      "omission_output_tokens", "integration_output_tokens", "context_limit_tokens")


def parse_project_limits(values: tuple[str, ...] | list[str]) -> dict[str, dict[str, Any]]:
    """``PROJECT:key=value[,key=value...]`` entries as {project: limits}; ``partition=none`` clears a profile."""
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        project, separator, body = value.partition(":")
        project = project.strip()
        if not separator or not project or not body.strip():
            raise ValueError(f"--project-limits {value!r}: expected PROJECT:KEY=VALUE[,KEY=VALUE...]")
        if project in result:
            raise ValueError(f"--project-limits names {project} twice")
        entry: dict[str, Any] = {}
        for item in body.split(","):
            key, equals, text = (part.strip() for part in item.partition("="))
            key = key.replace("-", "_")
            if not equals or key not in PROJECT_LIMIT_KEYS or key in entry:
                raise ValueError(f"--project-limits {value!r}: {item.strip()!r} is not one of "
                                 f"{', '.join(PROJECT_LIMIT_KEYS)} given once as KEY=VALUE")
            if key == "partition":
                entry[key] = None if text.lower() == "none" else text
            else:
                try:
                    entry[key] = int(text)
                except ValueError:
                    raise ValueError(f"--project-limits {value!r}: {key} must be an integer") from None
        result[project] = entry
    return result


def parse_sizing_records(values: tuple[str, ...] | list[str]) -> dict[str, Path]:
    """``PROJECT=DIRECTORY`` entries as {project: directory}."""
    result: dict[str, Path] = {}
    for value in values:
        project, separator, directory = (part.strip() for part in value.partition("="))
        if not separator or not project or not directory:
            raise ValueError(f"--sizing-record {value!r}: expected PROJECT=DIRECTORY")
        if project in result:
            raise ValueError(f"--sizing-record names {project} twice")
        result[project] = Path(directory)
    return result


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
    help="Named audit partition bounds validated for a project, with their input allowance (chorus: "
         "80 paths, 12,288 bytes, 4 workers, 4,000,000 input tokens; CHORUS only). Without it "
         "--max-paths, --max-inventory-bytes, --max-workers and --aggregate-input-tokens are required, "
         "with a --sizing-record: none of them has a default.",
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
    "--project-limits", "project_limits",
    multiple=True,
    metavar="PROJECT:KEY=VALUE[,KEY=VALUE...]",
    help="Audit limits for one project, applied over the options above (repeatable). Keys: partition "
         "(a profile, or none), max_paths, max_inventory_bytes, max_workers, aggregate_input_tokens and the "
         "other integer limits, e.g. AI_READI:max_paths=80,max_inventory_bytes=12288,max_workers=16,"
         "aggregate_input_tokens=15000000.",
)
@click.option(
    "--sizing-record", "sizing_records",
    multiple=True,
    metavar="PROJECT=DIRECTORY",
    help="Intermediate directory of an earlier API run of PROJECT ({P}_full.yaml, {P}_core.yaml, "
         "{P}_coverage_receipt.yaml), whose record must declare PROJECT and the arm. Required for an aggregate_input_tokens "
         "no partition profile covers. The build is refused when a typed-audit call sized on that record cannot "
         "fit its window, or the allowance is below the sizing; otherwise the sizing is written beside the "
         "registration (#5155).",
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
    help="Validate existing registrations and roster on disk without rebuilding; attests pinned bytes, not runtime admission.",
)
@click.option(
    "--replace",
    is_flag=True,
    help="Allow overwriting an existing registration or roster file with different bytes.",
)
@click.option(
    "--worktree", "-w",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help=(
        "Select checkout resources; relative input/output paths resolve under this root (single-threaded preparation). "
        "Use the selected checkout's own venv, or python -S with site-packages on PYTHONPATH."
    ),
)
@_worktree_resources
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
    project_limits: tuple[str, ...],
    sizing_records: tuple[str, ...],
    id_prefix: str,
    synthesize_draft_context: bool,
    dry_run: bool,
    check: bool,
    replace: bool = False,
    worktree: Path | None = None,
) -> None:
    """Build shared generation registrations and batch rosters for D4D Messages-API generic_v10.

    --check attests pinned bytes, not runtime admission.
    """
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
        verified: dict[tuple[str, str], tuple[Path, str]] = {}
        for proj in target_projects:
            for lbl in target_labels:
                reg_file = out_dir / f"registration_{proj.lower()}_{lbl}.json"
                if not reg_file.is_file():
                    raise click.ClickException(f"Missing registration file: {reg_file}")
                raw = reg_file.read_bytes()
                parsed_reg = sg.parse_registration(raw)
                if parsed_reg["registration_path"] != str(reg_file):
                    raise click.ClickException(f"Out-dir registration path differs from its declared authority: {reg_file}")
                try:
                    verify_registration_input_pins(parsed_reg, worktree=worktree)
                except (FileNotFoundError, ValueError) as exc:
                    raise click.ClickException(f"Input pin verification failed for {reg_file.name}: {exc}") from exc
                try:
                    sized = check_registration_sizing(reg_file, raw)
                except ValueError as exc:
                    raise click.ClickException(str(exc)) from exc
                verified[(proj, lbl)] = (reg_file, hashlib.sha256(raw).hexdigest())
                click.echo(f"  ✓ {proj}: {reg_file.name}" + (f" (sized: {sizing_path(reg_file).name})" if sized else ""))
        if not target_roster_path.is_file():
            raise click.ClickException(f"Missing roster file: {target_roster_path}")
        pairs = [(p, lbl) for p in target_projects for lbl in target_labels]
        roster = validate_roster_file(target_roster_path, pairs)
        for pair, captured in roster["registrations"].items():
            try:
                verify_registration_input_pins(captured["document"], worktree=worktree)
            except (FileNotFoundError, ValueError) as exc:
                raise click.ClickException(f"Input pin verification failed for roster registration {captured['path']}: {exc}") from exc
            expected_path, expected_sha = verified[pair]
            if captured["path"] != expected_path:
                raise click.ClickException(f"Roster registration path differs from verified out-dir file: {captured['path']} != {expected_path}")
            if captured["sha256"] != expected_sha:
                raise click.ClickException(f"Roster registration SHA-256 differs from verified out-dir file: {expected_path}")
        click.echo(f"  ✓ Roster valid: {target_roster_path.name}")
        click.echo("All checks passed.")
        return

    try:
        per_project = parse_project_limits(project_limits)
        records = parse_sizing_records(sizing_records)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    for name, given in (("--project-limits", per_project), ("--sizing-record", records)):
        stray = sorted(set(given) - set(target_projects))
        if stray:
            raise click.UsageError(f"{name} names {', '.join(stray)}, which this build does not target")

    def limits_for(proj: str) -> tuple[str | None, dict[str, Any]]:
        entry = dict(per_project.get(proj, {}))
        return entry.pop("partition", partition), {**audit_overrides, **entry}

    # Every target must accept its bounds before any registration is built.
    for proj in target_projects:
        part, overrides = limits_for(proj)
        if part is None and any(overrides.get(key) is None for key in PARTITION_KEYS):
            raise click.UsageError(
                f"{proj}: audit partition bounds have no default (D-C, 2026-10-23): pass --partition chorus "
                "for CHORUS, or --max-paths, --max-inventory-bytes and --max-workers (or --project-limits) "
                "sized for the project"
            )
        try:
            resolve_audit_limits(proj, part, overrides or None, arm=arm)
        except ValueError as exc:
            raise click.UsageError(f"{proj}: {exc}") from exc

    registrations: list[dict[str, Any]] = []
    outputs: list[tuple[Path, bytes]] = []
    click.echo(f"Building registrations for {target_projects} (arm: {arm}, labels: {target_labels})...")

    # Every registration is built, sized and checked before any file is written.
    for proj in target_projects:
        part, overrides = limits_for(proj)
        for lbl in target_labels:
            reg_file = out_dir / f"registration_{proj.lower()}_{lbl}.json"
            try:
                reg, files, sizing = prepare_registration(
                    project=proj,
                    label=lbl,
                    arm=arm,
                    registration_path=reg_file,
                    id_prefix=id_prefix,
                    context_path=context_file,
                    context_dir=context_dir,
                    source_manifest_path=source_manifest,
                    bundle_path=bundle,
                    chunk_manifest_path=chunk_manifest,
                    profile_name=profile_name,
                    coverage_floor=coverage_floor,
                    floor_basis=floor_basis,
                    partition=part,
                    audit_limits=overrides or None,
                    synthesize_draft_context=synthesize_draft_context,
                    sizing_record=records.get(proj),
                    worktree=worktree,
                )
            except (ValueError, FileNotFoundError) as exc:
                raise click.ClickException(f"{proj} ({lbl}): {exc}") from exc
            registrations.append(reg)
            outputs.extend(files)
            reg_sha = hashlib.sha256(sg.canonical(reg)).hexdigest()
            ctx_sha = ((reg.get("inputs") or {}).get("context") or {}).get("sha256", "")
            click.echo(
                f"  ✓ {proj}: registration_id={reg['registration_id']} sha256={reg_sha} context_sha256={ctx_sha}"
            )
            if sizing is not None:
                limits, room = reg["audit_limits"], sizing["admissible_input_tokens"]
                click.echo(
                    f"    input sized on {sizing['sizing_record']['full']['path']}"
                    f"{' (stand-in)' if sizing['stand_in'] else ''}: {sizing['plan_workers']} of "
                    f"{sizing['max_workers']} workers; per call worker {sizing['worker_input_tokens']:,} of "
                    f"{room['worker']:,}, omission {sizing['omission_input_tokens']:,} of {room['omission']:,}, "
                    f"integration {sizing['integration_input_tokens']:,} of {room['integration']:,} expected "
                    f"({sizing['integration_worst_input_tokens']:,} at worst); aggregate "
                    f"{sizing['aggregate_input_tokens']:,} of {limits['aggregate_input_tokens']:,}"
                )
                click.echo(f"    sizing record {Path(sizing['sidecar']['path']).name} "
                           f"sha256={sizing['sidecar']['sha256']}")
                for warning in sizing["warnings"]:
                    click.echo(f"    warning: {warning}")
                for note in sizing["notes"]:
                    click.echo(f"    note: {note}")

    roster = build_roster(registrations=registrations, write_to_disk=False, pending_registration_writes=True)
    roster_sha = hashlib.sha256(sg.canonical(roster)).hexdigest()
    if not dry_run:
        _write_outputs(outputs + [(target_roster_path, sg.canonical(roster))], replace)
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
