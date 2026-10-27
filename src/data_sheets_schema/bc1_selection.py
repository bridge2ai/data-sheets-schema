"""Explicit BC1 selection and closed local contract identity.

BC1 is a new model-access condition, not an equivalent spelling of the old
single-integrator audit. Its protected shared-generation parser hook is supplied
as a proposal. Merely installing this module cannot enable generation.
"""
from __future__ import annotations

import hashlib
from importlib.metadata import version as package_version
import json
import math
import sys

VERSION = 1
FIELD = "bounded_carry"
PROCEDURE = """## BC1 bounded audit procedure v1

This explicitly selected procedure changes later model access. Each worker
reviews every assigned populated value and every clause against the complete
source bundle. Integration uses a fixed sequence of groups of one or two new
workers, followed by one separate cross-group consistency check. Every stage
has its own exact request and one response allowance; no refusal permits a
larger cap, changed grouping, truncated evidence or another answer.

The controller retains the complete worker reviews and machine audit. Later
calls receive all concerns, changed rows, predecessors, omission candidates and
decisions in a bounded ConcernPacketV1. Untouched supporting-only and metadata
review text can be omitted from that model view. Counts and hashes identify the
omitted material; they do not establish support or claim that you reread it.
Use the full original records, full schema semantics and complete sources to
check cross-field and cross-group conflicts. Follow the exact selected stage
contract for explicit retention, changes and every omission disposition.

The final RecordDigestV1 is bookkeeping, not scientific evidence. Reconciliation
still inspects every affected occurrence. Report writing reviews every populated
final-full value anew, including unchanged entries, and preserves all existing
source-review and evidence-assertion duties. Retirement, representation changes
and fewer repeated rows do not increase source coverage. Literal copying alone
does not justify exactMatch or a none disposition. Never manufacture a support
judgment, discard a qualification or summarize away a concern to fit a bound.
"""
EXTRA_CODE = (
    "src/data_sheets_schema/bc1_selection.py",
    "src/data_sheets_schema/bc1_codec.py",
    "src/data_sheets_schema/bc1_audit.py",
    "src/data_sheets_schema/bc1_runtime.py",
    "src/data_sheets_schema/bc1_context.py",
    "src/data_sheets_schema/bc1_registration.py",
    "src/data_sheets_schema/output_ownership.py",
    "src/data_sheets_schema/schema_sync.py",
)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def enabled(spec) -> bool:
    value = getattr(spec, "bounded_carry_version", 0)
    if type(value) is not int or value not in (0, VERSION):
        raise ValueError("bounded_carry_version must be the integer 0 or 1")
    return value == VERSION


def require_hooks() -> None:
    from . import shared_generation as shared
    if getattr(shared, "BC1_HOOK_VERSION", None) != VERSION:
        raise ValueError("BC1 shared-generation hook is not installed; review and apply "
                         "the protected patch proposal before preparing a live registration")


def contract_identity() -> dict:
    """Bind contracts, project source and reader versions; not binary attestation."""
    from . import bc1_audit, bc1_context, shared_generation as shared
    from .resources import resource_path
    code = sorted(set(shared.ROUTING_CODE) | set(EXTRA_CODE))
    return {
        "protocol": "bc1_typed_audit_v1",
        "version": VERSION,
        "parent": {"shared_generation_version": 1, "renderer": 25,
                   "api_playbook_version": 2, "receipt_completion_version": 2},
        "audit": bc1_audit.contract_identity(),
        "context": bc1_context.contract_identity(),
        "procedure_sha256": hashlib.sha256(PROCEDURE.encode("utf-8")).hexdigest(),
        "code": {name: hashlib.sha256(resource_path(name).read_bytes()).hexdigest()
                 for name in code},
        "reader_runtime": {"python": list(sys.version_info[:2]),
                           "packages": {name: package_version(name) for name in
                                        ("linkml", "linkml-runtime", "PyYAML", "jsonschema", "referencing")}},
        "scientific_readiness": "new condition; independent review and canary pending",
    }


def policy_text() -> str:
    from .shared_generation import policy_text as parent_policy
    return parent_policy(version=1) + "\n\n" + PROCEDURE


def registration_block(*, fan_in=2) -> dict:
    if type(fan_in) is not int or fan_in not in (1, 2):
        raise ValueError("BC1 fan_in is one or two workers per planned integration call")
    return {"version": VERSION, "fan_in": fan_in, "contract": contract_identity()}


def allowances(max_workers: int, fan_in: int, *, worker_output_tokens=64_000,
               omission_output_tokens: int, integration_output_tokens=64_000) -> dict:
    """Worst roster allowance, not an expected run or a permission to spend."""
    if type(max_workers) is not int or not 1 <= max_workers <= 32:
        raise ValueError("BC1 requires a registered maximum of 1..32 workers")
    if type(fan_in) is not int or fan_in not in (1, 2):
        raise ValueError("BC1 fan_in must be 1 or 2")
    for value in (worker_output_tokens, omission_output_tokens, integration_output_tokens):
        if type(value) is not int or value <= 0:
            raise ValueError("BC1 output reservations must be positive integers")
    if worker_output_tokens != 64_000 or integration_output_tokens != 64_000:
        raise ValueError("BC1 keeps uniform 64,000-token worker/integration reservations including thinking")
    integrations = math.ceil(max_workers / fan_in) + 1
    return {"max_workers": max_workers, "integration_calls": integrations,
            "max_calls": max_workers + 1 + integrations,
            "aggregate_output_tokens": max_workers * worker_output_tokens
            + omission_output_tokens + integrations * integration_output_tokens}


def validate_registration(reg: dict, *, shared_version=1) -> None:
    """Called by the proposed protected parser after its existing strict checks."""
    if FIELD not in reg:
        return
    if type(shared_version) is not int or shared_version != 1:
        raise ValueError("BC1 v1 supports shared generation v1; routing/native parity is not installed")
    block = reg[FIELD]
    if type(block) is not dict or set(block) != {"version", "fan_in", "contract"}:
        raise ValueError("BC1 registration requires its exact version, fan_in and contract")
    if type(block["version"]) is not int or block["version"] != VERSION:
        raise ValueError("unsupported BC1 registration version")
    if _canonical(block) != _canonical(registration_block(fan_in=block["fan_in"])):
        raise ValueError("BC1 registration contract/source/runtime identity differs")
    limits = reg["audit_limits"]
    required = allowances(limits["max_workers"], block["fan_in"],
        **{key: limits[key] for key in
           ("worker_output_tokens", "omission_output_tokens", "integration_output_tokens")})
    for key in ("max_calls", "aggregate_output_tokens"):
        if type(limits[key]) is not int or limits[key] < required[key]:
            raise ValueError("BC1 " + key + " cannot cover every registered worker, group and final check")
    if reg["selection"].get("condition") != "generic_v10":
        raise ValueError("BC1 v1 requires the generic_v10 API parent condition")


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate shared registration key")
        result[key] = value
    return result


def validate_spec_mode(spec) -> None:
    """Selection is explicit in BOTH RunSpec and the immutable registration.

    Legacy malformed-registration diagnostics remain the existing parser's
    responsibility. An escaped spelling of the BC1 key cannot evade this check.
    """
    selected = enabled(spec)
    raw = getattr(spec, "shared_generation_registration", None)
    try:
        reg = json.loads(raw, object_pairs_hook=_pairs) if type(raw) is str else None
    except (ValueError, TypeError, RecursionError):
        if selected:
            raise ValueError("BC1 requires a strict shared registration object") from None
        return
    present = type(reg) is dict and FIELD in reg
    if selected != present:
        raise ValueError("explicit bounded_carry_version and registered BC1 selection differ")
    if not selected:
        return
    require_hooks()
    if (getattr(spec, "shared_generation_version", None) != 1
            or getattr(spec, "condition", None) != "generic_v10"
            or getattr(spec, "render_version", None) != 25
            or getattr(spec, "api_playbook_version", None) != 2
            or getattr(spec, "receipt_completion_version", None) != 2
            or getattr(spec, "runtime", None) != "Claude API (direct)"
            or getattr(spec, "native_source_attribution_version", 0)
            or getattr(spec, "removal_repair_version", 0)):
        raise ValueError("BC1 v1 requires the explicit generic_v10/API25/shared1/playbook2/receipt2 tuple")
    # parse_registration performs all parent validation and invokes our closed
    # block validator. It does not call select(spec), so there is no recursion.
    from . import shared_generation as shared
    shared.parse_registration(raw.encode("utf-8"))


def identity(spec) -> dict | None:
    validate_spec_mode(spec)
    if not enabled(spec):
        return None
    return json.loads(spec.shared_generation_registration)[FIELD]
