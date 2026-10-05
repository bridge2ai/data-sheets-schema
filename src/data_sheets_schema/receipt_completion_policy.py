"""Immutable receipt-completion registration and exact coverage gates (#4266).

No empirical floor is chosen here. Historical callers select no policy.
"""
from __future__ import annotations

import hashlib
import json

FORMAT = "receipt_completion_registration_v1"
SPEC_KEYS = {"receipt_completion_version", "receipt_completion_policy_sha256",
             "receipt_completion_registration"}
BLOCK_KEY = "receipt_completion_policy"


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}, not a boolean")
    return value


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate registration key: {key}")
        value[key] = item
    return value


def _invalid_constant(value):
    raise ValueError(f"nonfinite registration constant: {value}")


def parse_registration(raw: bytes, *, version: int = 1) -> dict:
    from data_sheets_schema.receipt_completion import policy_identity
    selected = policy_identity(version=version)
    POLICY_SHA256 = selected["sha256"]
    # Verify the installed asset  # Verify the installed asset, not only the supplied hash string.
    if type(raw) is not bytes or not raw or len(raw) > 1_000_000:
        raise ValueError("registration must be bounded nonempty UTF-8 JSON bytes")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=_invalid_constant)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError("registration is not strict UTF-8 JSON") from exc
    keys = {"format", "registration_id", "condition", "runtime_policy_sha256",
            "receipt_instrument_version", "max_output_tokens", "max_request_bytes",
            "context_limit_tokens", "context_limit_basis", "coverage_floor"}
    if not isinstance(value, dict) or set(value) != keys or value["format"] != (FORMAT if version == 1 else "receipt_completion_registration_v2"):
        raise ValueError("registration fields do not match receipt_completion_registration_v1")
    for name in ("registration_id", "condition", "context_limit_basis"):
        if not isinstance(value[name], str) or not value[name].strip():
            raise ValueError(f"registration {name} must be a nonempty string")
    conditions = {"generic_v7", "generic_v8", "generic_v9"} if version == 1 else {"generic_v10"}
    if value["condition"] not in conditions:
        raise ValueError("receipt completion requires a receipt-producing condition")
    if value["runtime_policy_sha256"] != POLICY_SHA256:
        raise ValueError("registration names a different runtime policy")
    if _integer(value["receipt_instrument_version"], "receipt instrument") != 4:
        raise ValueError("registration must select receipt instrument 4")
    _integer(value["max_output_tokens"], "max_output_tokens", 1)
    _integer(value["max_request_bytes"], "max_request_bytes", 1)
    _integer(value["context_limit_tokens"], "context_limit_tokens", 1)
    if value["max_output_tokens"] > value["context_limit_tokens"]:
        raise ValueError("output cap alone exceeds the registered context window")
    floor = value["coverage_floor"]
    if not isinstance(floor, dict):
        raise ValueError("coverage_floor must be a mapping")
    if floor.get("state") == "pending":
        if floor != {"state": "pending", "mode": "diagnostic_pilot"}:
            raise ValueError("pending floor requires an explicit diagnostic_pilot")
    elif floor.get("state") == "registered":
        if set(floor) != {"state", "numerator", "denominator"}:
            raise ValueError("registered floor needs only an exact numerator/denominator")
        numerator = _integer(floor["numerator"], "floor numerator")
        denominator = _integer(floor["denominator"], "floor denominator", 1)
        if numerator > denominator:
            raise ValueError("coverage floor must be within [0, 1]")
    else:
        raise ValueError("coverage floor must be pending or registered")
    return value


def registration_identity(raw: bytes, *, version: int = 1) -> dict:
    parse_registration(raw, version=version)
    return {"sha256": hashlib.sha256(raw).hexdigest(), "raw_json": raw.decode("utf-8")}


def _identity(value):
    if not isinstance(value, dict) or set(value) != {"sha256", "raw_json"} or not isinstance(value["raw_json"], str):
        raise ValueError("receipt completion registration identity is missing or malformed")
    raw = value["raw_json"].encode("utf-8")
    try:
        format_name = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_invalid_constant).get("format")
    except (ValueError, AttributeError, RecursionError) as exc:
        raise ValueError("receipt completion registration is unreadable") from exc
    version = 2 if format_name == "receipt_completion_registration_v2" else 1
    if registration_identity(raw, version=version) != value:
        raise ValueError("receipt completion registration bytes differ from their SHA256")
    return parse_registration(raw, version=version)


def _selection(spec):
    from data_sheets_schema.receipt_completion import policy_identity
    if not isinstance(spec, dict):
        raise ValueError("recorded render spec must be a mapping")
    if not SPEC_KEYS.intersection(spec):
        return None
    if not SPEC_KEYS <= set(spec) or type(spec["receipt_completion_version"]) is not int or spec["receipt_completion_version"] not in (1, 2):
        raise ValueError("new receipt condition has missing or contradictory selection fields")
    version = spec["receipt_completion_version"]
    POLICY_SHA256 = policy_identity(version=version)["sha256"]
    if spec["receipt_completion_policy_sha256"] != POLICY_SHA256:
        raise ValueError("render spec names a different receipt completion policy")
    registration = _identity(spec["receipt_completion_registration"])
    if registration["format"] != (FORMAT if version == 1 else "receipt_completion_registration_v2"):
        raise ValueError("receipt registration and selected version differ")
    if registration["condition"] != spec.get("condition"):
        raise ValueError("registered condition differs from the recorded render spec")
    from data_sheets_schema.api_runner import RUNTIME
    if spec.get("runtime") != RUNTIME or type(spec.get("render_version")) is not int or spec["render_version"] != (8 if version == 1 else 25):
        raise ValueError("receipt completion requires API renderer 8")
    if version == 2:
        from .shared_generation import parse_registration as parse_shared, descriptor
        if (type(spec.get("shared_generation_version")) is not int or spec["shared_generation_version"] != 1
                or type(spec.get("api_playbook_version")) is not int or spec["api_playbook_version"] != 2):
            raise ValueError("receipt v2 requires the explicit shared-generation selection")
        shared = spec.get("shared_generation_registration")
        if type(shared) is not dict or set(shared) != {"sha256", "raw_json"} or type(shared["raw_json"]) is not str:
            raise ValueError("receipt v2 lacks its shared registration identity")
        raw = shared["raw_json"].encode("utf-8")
        if hashlib.sha256(raw).hexdigest() != shared["sha256"] or parse_shared(raw)["receipt"] != registration:
            raise ValueError("receipt v2 registration differs from shared authority")
        if spec.get("shared_generation_assets") != descriptor()["assets"]:
            raise ValueError("receipt v2 selected asset identities differ")
    return {"registration": registration,
            "identity": dict(spec["receipt_completion_registration"]),
            "runtime_policy_sha256": POLICY_SHA256}


def select_policy(render_spec: dict | None = None, record: dict | None = None) -> dict | None:
    """Select only from the supplied spec or provenance prompts.request.spec.

    A receipt marker, diagnostic block or condition label cannot activate it.
    When both authoritative declarations exist they must agree byte for byte.
    """
    selected = _selection(render_spec) if render_spec is not None else None
    recorded_spec = None
    if record is not None:
        if not isinstance(record, dict):
            raise ValueError("provenance record must be a mapping")
        prompts = record.get("prompts")
        if isinstance(prompts, dict) and isinstance(prompts.get("request"), dict):
            recorded_spec = prompts["request"].get("spec")
        if recorded_spec is not None:
            recorded = _selection(recorded_spec)
            if render_spec is not None and selected != recorded:
                raise ValueError("supplied receipt policy differs from the record declaration")
            selected = recorded
        runtime = record.get("receipt_completion")
        if runtime is not None:
            if selected is None or not isinstance(runtime, dict) or runtime.get("registration") != selected["identity"]:
                raise ValueError("receipt completion outcome lacks its matching authoritative registration")
    return selected


def block_identity(policy: dict) -> dict:
    return {"registration": dict(policy["identity"]),
            "runtime_policy_sha256": policy["runtime_policy_sha256"]}


def policy_from_block(block: dict, *, policy: dict | None = None) -> dict | None:
    """Revalidate a freshly checked block, optionally against its run selection."""
    value = block.get(BLOCK_KEY)
    if value is None:
        if policy is not None:
            raise ValueError("selected receipt condition has no policy in its checked block")
        return None
    if not isinstance(value, dict) or set(value) != {"registration", "runtime_policy_sha256"}:
        raise ValueError("receipt block policy identity is malformed")
    registration = _identity(value["registration"])
    if value["runtime_policy_sha256"] != registration["runtime_policy_sha256"]:
        raise ValueError("receipt block policy hash differs from registration")
    selected = {"identity": value["registration"], "registration": registration,
                "runtime_policy_sha256": value["runtime_policy_sha256"]}
    if policy is not None and selected != policy:
        raise ValueError("receipt block policy differs from the record declaration")
    if block.get("checked"):
        from data_sheets_schema.receipts import RERECEIPTS_INSTRUMENT
        if block.get("instrument") != RERECEIPTS_INSTRUMENT:
            raise ValueError("new receipt policy requires a checked instrument-v4 block")
    return selected


def evaluate_floor(coverage: dict, policy: dict) -> dict:
    """Compare integer fractions exactly; never certify pending or empty data."""
    if not isinstance(coverage, dict):
        raise ValueError("receipt coverage must be a mapping")
    eligible = _integer(coverage.get("receiptable"), "receiptable")
    covered = _integer(coverage.get("with_receipt"), "with_receipt")
    if covered > eligible:
        raise ValueError("with_receipt exceeds receiptable")
    for key, value in coverage.items():
        if not isinstance(key, str):
            raise ValueError("coverage keys must be strings")
        if value is not None and (key.endswith("_count") or key in {"receipt_paths", "exempt_on_carried_identifier"}):
            _integer(value, key)
    if "populated" in coverage or "exempt" in coverage:
        populated = _integer(coverage.get("populated"), "populated")
        exempt = _integer(coverage.get("exempt"), "exempt")
        if populated != eligible + exempt:
            raise ValueError("coverage populated/exempt/receiptable counters disagree")
        if coverage.get("exempt_on_carried_identifier") is not None and coverage["exempt_on_carried_identifier"] > exempt:
            raise ValueError("carried-identifier exemptions exceed all exempt leaves")
    missing = eligible - covered
    truncated = coverage.get("without_receipt_truncated")
    if truncated is not None:
        _integer(truncated, "without_receipt_truncated")
        if truncated > missing or "without_receipt" not in coverage:
            raise ValueError("coverage truncation count lacks consistent missing paths")
    if "without_receipt" in coverage:
        paths = coverage["without_receipt"]
        truncated = 0 if truncated is None else truncated
        if not isinstance(paths, list) or any(not isinstance(p, str) for p in paths) or len(set(paths)) != len(paths) or len(paths) + truncated != missing:
            raise ValueError("coverage missing paths/counters disagree")
    for key in ("never_receipted", "added_after_receipt"):
        if coverage.get(key) is not None:
            _integer(coverage[key], key)
            if coverage[key] > missing:
                raise ValueError(f"coverage {key} exceeds uncovered leaves")
    if all(coverage.get(k) is not None for k in ("never_receipted", "added_after_receipt")):
        if coverage["never_receipted"] + coverage["added_after_receipt"] != missing:
            raise ValueError("coverage phase-1 missing counters disagree")
    registration = _identity(policy["identity"])
    if registration != policy.get("registration") or registration["runtime_policy_sha256"] != policy.get("runtime_policy_sha256"):
        raise ValueError("selected receipt policy differs from its pinned registration")
    floor = registration["coverage_floor"]
    result = {"with_receipt": covered, "receiptable": eligible, "floor": dict(floor),
              "passed": False, "registration_sha256": policy["identity"]["sha256"]}
    if floor["state"] == "pending":
        return {**result, "state": "pending", "reason": "diagnostic pilot; coverage floor not registered"}
    if eligible == 0:
        return {**result, "state": "not_applicable", "reason": "no eligible leaves; coverage unmeasurable"}
    passed = covered * floor["denominator"] >= eligible * floor["numerator"]
    return {**result, "state": "passed" if passed else "failed", "passed": passed}
