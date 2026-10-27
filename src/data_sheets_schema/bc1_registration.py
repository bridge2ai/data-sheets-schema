"""Offline BC1 registration sizing through the production renderers.

BC1 / 2026-10-27. Inputs are an explicit registration and actual earlier full,
core and receipt bytes. Outputs are byte-pinned planning scenarios, never a
token-count, scientific decision, launch authorization or future-size bound.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

from . import bc1_context as context, bc1_selection as selection

FORMAT = "bc1_input_sizing_v1"
PROJECTS = ("CHORUS", "AI_READI", "CM4AI", "VOICE", "VOICE_PEDIATRIC", "KIDS_FIRST")


def _raw(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def _pin(path, raw):
    return {"path": str(Path(path).resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


@dataclass(frozen=True)
class SizingCapture:
    """Offline capture only. Not a live shared-generation Capture/RunSpec."""
    registration: bytes
    files: tuple
    full_schema: object
    core_schema: object

    def document(self):
        return json.loads(self.registration)

    def raw(self, path):
        for name, raw in self.files:
            if name == path:
                return raw
        raise ValueError("BC1 sizing requested bytes outside its captured inputs")


def capture_inputs(registration, *, context_raw, schema_snapshot):
    """Read only pinned input paths; never discover evaluator rationale."""
    from .schema_snapshot import capture_schema
    inputs = registration["inputs"]
    if context._schema_pin(schema_snapshot) != inputs["full_schema"]:
        raise ValueError("BC1 sizing schema differs from its registered closure")
    pins = [inputs[k] for k in ("bundle", "chunk_manifest", "source_manifest", "context") if inputs[k] is not None]
    if inputs["profile"]["vocabulary"] is not None:
        pins.append(inputs["profile"]["vocabulary"])
    files = {}
    for pin in pins:
        path = pin["path"]
        raw = context_raw if path == inputs["context"]["path"] else Path(path).read_bytes()
        if _pin(path, raw) != pin:
            raise ValueError("BC1 sizing input differs from registered byte pin")
        if path in files and files[path] != raw:
            raise ValueError("BC1 sizing has conflicting input aliases")
        files[path] = raw
    core = capture_schema(inputs["core_schema"]["root"], strict=True)
    if context._schema_pin(core) != inputs["core_schema"]:
        raise ValueError("BC1 sizing core schema differs from its registered closure")
    return SizingCapture(_raw(registration), tuple(files.items()), schema_snapshot, core)


def _own_record(project, arm, raw, *, core=False):
    header = []
    for line in raw.decode("utf-8").splitlines():
        if not line.startswith("#"):
            break
        header.append(line.strip())
    titles = {f"# D4D Datasheet for {project} Dataset"}
    if core:
        titles.add(f"# D4D Core Datasheet for {project} Dataset")
    return bool(header) and header[0] in titles and f"# Arm: {arm}" in header


def _placeholder(size, label):
    if type(size) is not int or size < 0:
        raise ValueError("BC1 future visible-byte scenario requires nonnegative integers")
    prefix = ("HYPOTHETICAL BC1 SIZING ONLY: " + label + "; ").encode()
    return (prefix + b"x" * max(0, size - len(prefix)))[:size].decode("ascii")


def size_inputs(registration, *, sizing_record, context_raw, schema_snapshot,
                exploratory_stand_in=False, expected_visible_bytes=None,
                planning_bytes_per_token=2.0, payload_sink=None):
    """Measure actual current request shapes and explicit future-byte scenarios.

    Future codec strings are deliberately NOT accepted model responses. They
    convey byte scenarios through the same pure production formatter without
    manufacturing source-review judgments to reach a later integration stage.
    """
    from . import api_runner as api, bc1_audit as audit, bc1_runtime as runtime
    from . import bc1_codec as codec, shared_generation as shared
    if not isinstance(planning_bytes_per_token, (int, float)) or isinstance(planning_bytes_per_token, bool) or not math.isfinite(planning_bytes_per_token) or planning_bytes_per_token <= 0:
        raise ValueError("BC1 planning bytes/token ratio must be explicit and positive")
    selection.validate_registration(registration)
    project, arm = registration["run"]["project"], registration["run"]["arm"]
    if project not in PROJECTS:
        raise ValueError("BC1 sizing project is not one of the six declared projects")
    paths = {key: Path(getattr(sizing_record, key)) for key in ("full", "core", "receipt")}
    raws = {key: path.read_bytes() for key, path in paths.items()}
    own = _own_record(project, arm, raws["full"]) and _own_record(project, arm, raws["core"], core=True)
    if not own and not exploratory_stand_in:
        raise ValueError("BC1 live sizing requires this project's actual full record and core record of the selected arm")
    captured = capture_inputs(registration, context_raw=context_raw, schema_snapshot=schema_snapshot)
    inputs = registration["inputs"]
    limits = registration["audit_limits"]
    fan = registration["bounded_carry"]["fan_in"]
    packet = runtime.prepare_packet_bytes(SimpleNamespace(project=project), captured,
        {"original_full": raws["full"], "original_core": raws["core"]}, raws["receipt"])
    settings = {"name": registration["runtime"]["model"], "thinking": deepcopy(registration["runtime"]["thinking"]),
                "temperature": registration["runtime"]["temperature"], "effort": registration["runtime"]["effort"]}
    registration_sha = hashlib.sha256(shared.canonical(registration)).hexdigest()
    # Receipt completion is not replayed or invented. Its selected bounded carry
    # is future authority, so this absence is made explicit in every scenario.
    receipt_carry = "BC1 SIZING PLACEHOLDER: future receipt-completion decision carry is not yet available."
    common = {"packet": packet, "settings": settings, "audit_limits": limits,
        "registration_sha256": registration_sha, "generation_id": "0" * 32,
        "policy_text": selection.policy_text(), "evidence_contract": api.shared_evidence_contract(),
        "generation_context": context.generation_context(captured), "receipt_carry": receipt_carry}
    rows = []

    def render(stage, inner, scenario, *, assignment=None, placeholders=None):
        _, payload = runtime.render_request(**common, stage=stage, inner=inner,
            schema_context=context.schema_context(captured, raws["full"].decode(), assigned_paths=assignment))
        wire = shared.canonical(payload)
        output = payload["max_tokens"]
        estimate = math.ceil(len(wire) / planning_bytes_per_token)
        row = {"stage": deepcopy(stage), "scenario": scenario, "wire_bytes": len(wire),
               "wire_sha256": hashlib.sha256(wire).hexdigest(), "output_token_reserve": output,
               "estimated_input_tokens": estimate,
               "estimated_context_tokens": estimate + output,
               "estimated_context_fits": estimate <= min(limits["max_input_tokens_per_call"], limits["context_limit_tokens"] - output),
               "actual_count_tokens": None, "future_placeholders": placeholders or {},
               "wire_basis": "Exact canonical production payload for the stated concrete hypothetical inputs; not SDK HTTP framing."}
        rows.append(row)
        if payload_sink is not None:
            payload_sink(deepcopy(row), wire)
        return row

    for worker in packet["plan"]["workers"]:
        render({"phase": "typed_audit_worker", "worker_id": worker["id"]}, audit.worker_request(packet, worker["id"]),
               "captured_record")
    render({"phase": "typed_audit_omission"}, audit.omission_request(packet), "captured_record")
    scenarios = {"empty_future_floor": {"worker": 0, "concern": 0},
                 "visible_cap_ascii_scenario": {"worker": codec.WORKER_BYTES, "concern": codec.CARRY_BYTES}}
    if expected_visible_bytes is not None:
        if type(expected_visible_bytes) is not dict or set(expected_visible_bytes) != {"worker", "concern", "basis"} or not isinstance(expected_visible_bytes["basis"], str) or not expected_visible_bytes["basis"].strip():
            raise ValueError("BC1 expected-byte scenario needs worker/concern integer bytes and an explicit basis")
        if any(type(expected_visible_bytes[k]) is not int or not 0 <= expected_visible_bytes[k] <= cap
               for k, cap in (("worker", codec.WORKER_BYTES), ("concern", codec.CARRY_BYTES))):
            raise ValueError("BC1 expected-byte scenario exceeds visible contract")
        scenarios["caller_expected_visible_scenario"] = dict(expected_visible_bytes)
    stages = [*packet["groups"], {"id": "final", "workers": []}]
    for scenario, amounts in scenarios.items():
        processed = []
        for group in stages:
            processed.extend(group["workers"])
            selected_paths = {path for worker in packet["plan"]["workers"] if worker["id"] in processed
                              for path in worker["paths"]}
            inner = audit.render_stage_request(packet, stage_id=group["id"],
                new_workers={key: _placeholder(amounts["worker"], "future worker") for key in group["workers"]},
                concern_packet=_placeholder(amounts["concern"], "future complete concern packet").encode(),
                record_digest=audit.render_record_digest(packet, row_count=len(selected_paths),
                    current_row_index_sha256="0" * 64, processed_workers=processed),
                prior_state_sha256="0" * 64, current_row_index_sha256="0" * 64)
            render({"phase": "typed_audit_integration", "stage_id": group["id"], "worker_ids": group["workers"]},
                   inner, scenario, placeholders={**amounts, "valid_model_response": False,
                   "record_digest": "hypothetical future state, not an accepted review"})
    fixed = [row for row in rows if row["scenario"] == "captured_record"]
    totals = {}
    for name in scenarios:
        chosen = fixed + [row for row in rows if row["scenario"] == name]
        totals[name] = {"calls": len(chosen), "wire_bytes": sum(r["wire_bytes"] for r in chosen),
            "estimated_input_tokens": sum(r["estimated_input_tokens"] for r in chosen),
            "output_token_reservations": sum(r["output_token_reserve"] for r in chosen),
            "estimated_all_calls_fit": all(r["estimated_context_fits"] for r in chosen)}
    return {"format": FORMAT, "registration_sha256": registration_sha, "project": project,
        "scope": "Typed-audit roster only; full/receipt/reconcile/report retain separate parent limits and actual admission checks.",
        "own_project_and_arm_record": own, "exploratory_stand_in": not own,
        "sizing_record": {key: _pin(paths[key], raws[key]) for key in paths},
        "captured_inputs": deepcopy(inputs), "plan_sha256": packet["plan"]["sha256"],
        "plan_workers": len(packet["plan"]["workers"]), "groups": deepcopy(packet["groups"]),
        "final_cross_group_calls": 1, "registered_maximum_roster": selection.allowances(limits["max_workers"], fan,
            **{key: limits[key] for key in ("worker_output_tokens", "omission_output_tokens", "integration_output_tokens")}),
        "rows": rows, "own_plan_scenarios": totals, "expected_visible_bytes": expected_visible_bytes,
        "planning_bytes_per_token": planning_bytes_per_token,
        "shared_placeholders": {"generation_id": "32-character hypothetical UUID hex; never a live generation",
                                "receipt_carry": "future checked receipt-completion outcome unavailable"},
        "receipt_completion_carry": {"actual": False, "placeholder_bytes": len(receipt_carry.encode())},
        "downstream_projection": {"actual": False, "bytes": None,
            "representation": "Self-contained BC1 codec with empty external dictionary; runtime visible-byte cap 262144.",
            "reason": "No completed BC1 assembly exists before generation; reconcile/report bodies remain unknown."},
        "actual_provider_token_counts": None, "admission": "UNVERIFIED_UNTIL_ACTUAL_REQUEST_COUNT",
        "warnings": ["Future record, judgment, UTF-8 escaping and receipt carry can change request sizes.",
                     "Visible-byte caps do not bound thinking tokens; 64k output reservations remain.",
                     "The ASCII visible-cap scenario is not an upper bound on escaped JSON wire bytes or token counts.",
                     "Own-plan totals are not maximum-worker or retry-inclusive campaign budgets."],
        "source_identity": selection.contract_identity()}


def draft_candidate(registration, *, sizing_record, context_raw, schema_snapshot, fan_in=2,
                    exploratory_stand_in=False, **sizing_options):
    """Explicitly unlaunchable exploration; never call the production parser."""
    from . import shared_generation as shared
    candidate = deepcopy(registration)
    if "bounded_carry" in candidate:
        raise ValueError("BC1 draft input must be an unmodified parent registration")
    shared.parse_registration(shared.canonical(candidate))
    candidate["bounded_carry"] = selection.registration_block(fan_in=fan_in)
    limits = candidate["audit_limits"]
    limits["worker_output_tokens"] = limits["integration_output_tokens"] = 64_000
    allowance = selection.allowances(limits["max_workers"], fan_in, omission_output_tokens=limits["omission_output_tokens"])
    limits.update({key: allowance[key] for key in ("max_calls", "aggregate_output_tokens")})
    sizing = size_inputs(candidate, sizing_record=sizing_record, context_raw=context_raw,
        schema_snapshot=schema_snapshot, exploratory_stand_in=exploratory_stand_in, **sizing_options)
    return {"format": "bc1_unlaunchable_registration_candidate_v1", "launchable": False,
            "requires_protected_hooks": True, "registration": candidate, "sizing": sizing}


def check_sizing_record(registration, sizing):
    """A sidecar is tied to the actual record and whole registration, never a profile waiver."""
    from . import shared_generation as shared
    selection.validate_registration(registration)
    if (type(sizing) is not dict or sizing.get("format") != FORMAT
            or sizing.get("registration_sha256") != hashlib.sha256(shared.canonical(registration)).hexdigest()
            or sizing.get("project") != registration["run"]["project"]
            or sizing.get("own_project_and_arm_record") is not True
            or sizing.get("exploratory_stand_in") is not False):
        raise ValueError("BC1 registration requires its actual project/arm sizing record")
    if sizing.get("source_identity") != selection.contract_identity():
        raise ValueError("BC1 sizing code/contract identity is stale")
    groups = sizing.get("groups")
    if (not isinstance(groups, list) or not groups or any(type(g) is not dict or set(g) != {"id", "workers"}
            or not isinstance(g["id"], str) or not isinstance(g["workers"], list)
            or not 1 <= len(g["workers"]) <= registration["bounded_carry"]["fan_in"] for g in groups)):
        raise ValueError("BC1 sizing group roster is invalid")
    worker_ids = [worker for group in groups for worker in group["workers"]]
    if (any(not isinstance(w, str) for w in worker_ids) or len(set(worker_ids)) != len(worker_ids)
            or len({g["id"] for g in groups}) != len(groups) or "final" in {g["id"] for g in groups}
            or sizing.get("plan_workers") != len(worker_ids) or sizing.get("final_cross_group_calls") != 1):
        raise ValueError("BC1 sizing worker/final roster is incomplete")
    expected_fixed = [{"phase": "typed_audit_worker", "worker_id": worker} for worker in worker_ids]
    expected_fixed.append({"phase": "typed_audit_omission"})
    expected_stages = [{"phase": "typed_audit_integration", "stage_id": group["id"], "worker_ids": group["workers"]}
                       for group in groups] + [{"phase": "typed_audit_integration", "stage_id": "final", "worker_ids": []}]
    rows, totals = sizing.get("rows"), sizing.get("own_plan_scenarios")
    if (not isinstance(rows, list) or not isinstance(totals, dict)
            or not {"empty_future_floor", "visible_cap_ascii_scenario"} <= set(totals)
            or set(totals) - {"empty_future_floor", "visible_cap_ascii_scenario", "caller_expected_visible_scenario"}):
        raise ValueError("BC1 sizing scenario roster is incomplete")
    if any(type(row) is not dict or row.get("scenario") not in {"captured_record", *totals} for row in rows):
        raise ValueError("BC1 sizing has an undeclared scenario")
    fixed = [row for row in rows if row["scenario"] == "captured_record"]
    if [row.get("stage") for row in fixed] != expected_fixed:
        raise ValueError("BC1 sizing worker/omission requests are incomplete")
    limits = registration["audit_limits"]
    if len(worker_ids) > limits["max_workers"]:
        raise ValueError("BC1 sizing exceeds its registered worker limit")
    for row in rows:
        label = {"typed_audit_worker": "worker", "typed_audit_omission": "omission",
                 "typed_audit_integration": "integration"}.get(row.get("stage", {}).get("phase"))
        if (label is None or type(row.get("wire_bytes")) is not int or not 0 < row["wire_bytes"] <= limits["max_request_bytes"]
                or row.get("output_token_reserve") != limits[label + "_output_tokens"]
                or type(row.get("estimated_input_tokens")) is not int or row["estimated_input_tokens"] < 0):
            raise ValueError("BC1 sizing wire/output envelope is invalid")
    for name, total in totals.items():
        future = [row for row in rows if row["scenario"] == name]
        if [row.get("stage") for row in future] != expected_stages:
            raise ValueError("BC1 sizing group/final requests are incomplete")
        chosen = fixed + future
        expected = {"calls": len(chosen), "wire_bytes": sum(r["wire_bytes"] for r in chosen),
            "estimated_input_tokens": sum(r["estimated_input_tokens"] for r in chosen),
            "output_token_reservations": sum(r["output_token_reserve"] for r in chosen),
            "estimated_all_calls_fit": all(r["estimated_context_fits"] for r in chosen)}
        if total != expected or expected["calls"] > limits["max_calls"] or expected["output_token_reservations"] > limits["aggregate_output_tokens"]:
            raise ValueError("BC1 sizing totals omit or exceed registered audit calls/output reservations")
    for pin in sizing.get("sizing_record", {}).values():
        if _pin(pin["path"], Path(pin["path"]).read_bytes()) != pin:
            raise ValueError("BC1 sizing source bytes changed")
    if set(sizing.get("sizing_record", {})) != {"full", "core", "receipt"}:
        raise ValueError("BC1 sizing source roster is incomplete")


def plan(spec, settings):
    """Registration roster only; no historical record or provider discovery."""
    from . import shared_generation as shared
    selection.validate_spec_mode(spec)
    captured = shared.preflight(spec, settings)
    reg = captured.document()
    limits = reg["audit_limits"]
    roster = selection.allowances(limits["max_workers"], reg["bounded_carry"]["fan_in"],
        **{key: limits[key] for key in ("worker_output_tokens", "omission_output_tokens", "integration_output_tokens")})
    return {"project": spec.project, "arm": spec.arm, "method": spec.method, "label": spec.label,
        "condition": spec.condition, "bounded_carry": deepcopy(reg["bounded_carry"]),
        "registered_maximum_roster": roster, "registered_audit_allowances": deepcopy(limits),
        "actual_plan_workers": None, "actual_request_bytes": None, "actual_provider_token_counts": None,
        "estimate_basis": "A future full record determines the fixed worker/group plan. Registered allowances do not predict actual spend.",
        "readiness": {"scientific_approval": "unverified", "campaign_launch": "not authorized by a plan",
                      "native_direct": "unsupported", "actual_request_count": "required before every dispatch"}}
