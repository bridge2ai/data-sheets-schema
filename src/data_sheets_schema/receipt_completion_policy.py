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
NATIVE_SPEC_KEYS = {"native_shared_generation_version", "native_shared_generation_descriptor",
                    "native_shared_generation_registration", "native_shared_generation_context",
                    "native_shared_receipt_policy"}


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
    if len(raw) > 2_000_000:
        raise ValueError('receipt registration identity exceeds its byte bound')
    try:
        parsed = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
        format_name = parsed.get("format")
    except (ValueError, AttributeError, RecursionError) as exc:
        raise ValueError("receipt completion registration is unreadable") from exc
    if parsed.get("kind") == "d4d_native_shared_receipt_policy":
        from .native_shared_contract import parse_receipt_policy
        from .native_shared_selection import RECEIPT_POLICY_SHA256
        if hashlib.sha256(raw).hexdigest() != value["sha256"]:
            raise ValueError("native receipt policy bytes differ from their SHA256")
        return parse_receipt_policy(raw, RECEIPT_POLICY_SHA256)
    version = 2 if format_name == "receipt_completion_registration_v2" else 1
    if registration_identity(raw, version=version) != value:
        raise ValueError("receipt completion registration bytes differ from their SHA256")
    return parse_registration(raw, version=version)


def _native_selection(spec):
    """Select recorded native authority without reading current input paths."""
    from . import native_shared_contract as c, native_shared_selection as native
    if (not NATIVE_SPEC_KEYS <= set(spec)
            or type(spec['native_shared_generation_version']) is not int
            or spec['native_shared_generation_version'] != 1):
        raise ValueError('native receipt selection fields are missing or contradictory')
    if (spec.get('runtime') != c.RUNTIME or spec.get('condition') != c.CONDITION
            or type(spec.get('render_version')) is not int or spec['render_version'] != c.RENDERER
            or spec['native_shared_generation_descriptor'] != native.descriptor()):
        raise ValueError('native receipt selection requires its exact descriptor and renderer')
    for axis in ('native_source_attribution_version', 'shared_generation_version', 'api_playbook_version',
                 'receipt_completion_version', 'removal_repair_version'):
        if type(spec.get(axis, 0)) is not int or spec.get(axis, 0) != 0:
            raise ValueError('native receipt selection conflicts with another execution axis')
    if {'receipt_completion_policy_sha256', 'receipt_completion_registration'}.intersection(spec):
        raise ValueError('native receipt selection cannot carry an API receipt registration')
    registered = spec['native_shared_generation_registration']
    c.exact(registered, {'sha256', 'raw_json'}, 'native selection identity')
    if type(registered['raw_json']) is not str:
        raise ValueError('native selection must retain raw UTF-8 JSON')
    raw = registered['raw_json'].encode('utf-8')
    doc = c.parse_selection(raw)
    if c.sha(raw) != registered['sha256'] or doc['selection']['descriptor_sha256'] != native.descriptor_capture().sha256:
        raise ValueError('native receipt selection identity differs from its recorded bytes')
    assets = doc['selection']['assets']
    if set(assets) != set(native.ASSET_HASHES) or any(assets[name]['sha256'] != digest for name, digest in native.ASSET_HASHES.items()):
        raise ValueError('native receipt selection assets differ from the fixed descriptor')
    declared = spec['native_shared_receipt_policy']
    c.exact(declared, {'path', 'sha256', 'raw_json'}, 'native receipt declaration')
    identity = {key: declared[key] for key in ('sha256', 'raw_json')}
    registration = _identity(identity)
    policy_raw = declared['raw_json'].encode('utf-8')
    if ({'path': declared['path'], 'sha256': declared['sha256'], 'bytes': len(policy_raw)} != doc['receipt_policy']
            or registration.get('kind') != c.KINDS['receipt_policy']):
        raise ValueError('native receipt policy does not match its selection file pin')
    context = spec['native_shared_generation_context']
    c.exact(context, {'context', 'profile', 'source_manifest', 'scope'}, 'native generation context')
    expected_scope = ('Caller-declared generation scope, source policy and vocabulary; '
                      'not a scientific applicability or support verdict.')
    if context['scope'] != expected_scope or context['source_manifest'] != doc['inputs']['source_manifest']:
        raise ValueError('native receipt source authority differs from selected scope')
    def captured_text(value, pin, key):
        c.exact(value, {'identity', key}, 'native captured context member')
        if type(value[key]) is not str:
            raise ValueError('native context member must retain text')
        body = value[key].encode('utf-8')
        if value['identity'] != pin or len(body) != pin['bytes'] or c.sha(body) != pin['sha256']:
            raise ValueError('native captured context bytes differ from selection')
    captured_text(context['context'], doc['inputs']['context'], 'raw_json')
    profile = context['profile']
    c.exact(profile, {'name', 'basis', 'vocabulary'}, 'native profile context')
    expected = doc['inputs']['profile']
    if profile['name'] != expected['name'] or profile['basis'] != expected['basis']:
        raise ValueError('native profile differs from selected authority')
    if expected['vocabulary'] is None:
        if profile['vocabulary'] is not None:
            raise ValueError('native profile has an unselected vocabulary')
    else:
        captured_text(profile['vocabulary'], expected['vocabulary'], 'raw_text')
    return {'registration': registration, 'identity': identity,
            'runtime_policy_sha256': native.RECEIPT_POLICY_SHA256}


def native_render_declaration(capture):
    """Receipt CLI's explicit native declaration, using one immutable capture."""
    from . import native_shared_contract as c, native_shared_selection as native
    if type(capture) is not c.NativeSelectionCapture:
        raise ValueError('native receipt declaration requires a selection capture')
    return {'condition': c.CONDITION, 'runtime': c.RUNTIME, 'render_version': c.RENDERER,
        'native_shared_generation_version': 1,
        'native_shared_generation_descriptor': native.descriptor(),
        'native_shared_generation_registration': {'sha256': capture.registration.pin.sha256,
            'raw_json': capture.registration.raw.decode('utf-8')},
        'native_shared_generation_context': capture.generation_context(),
        'native_shared_receipt_policy': {'path': capture.receipt_policy.pin.path,
            'sha256': capture.receipt_policy.pin.sha256,
            'raw_json': capture.receipt_policy.raw.decode('utf-8')}}


def _selection(spec):
    from data_sheets_schema.receipt_completion import policy_identity
    if not isinstance(spec, dict):
        raise ValueError("recorded render spec must be a mapping")
    if 'native_shared_generation_version' in spec and type(spec['native_shared_generation_version']) is not int:
        raise ValueError('native receipt axis must be an integer')
    if (spec.get('native_shared_generation_version', 0) != 0
            or (NATIVE_SPEC_KEYS - {'native_shared_generation_version'}).intersection(spec)):
        return _native_selection(spec)
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
            if render_spec is not None and any(key in recorded_spec or key in render_spec
                    for key in NATIVE_SPEC_KEYS - {'native_shared_generation_version'}):
                if any(render_spec.get(key) != recorded_spec.get(key) for key in NATIVE_SPEC_KEYS):
                    raise ValueError('supplied native receipt selection differs from the record declaration')
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


def coverage_counts(coverage: dict) -> tuple[int, int]:
    """Validate the released integer coverage accounting without selecting a policy."""
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
    return covered, eligible


def evaluate_floor(coverage: dict, policy: dict) -> dict:
    """Compare integer fractions exactly; never certify pending or empty data."""
    covered, eligible = coverage_counts(coverage)
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
