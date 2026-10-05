"""Closed data contract for the explicitly selected native shared protocol.

This module uses only the standard library. Captures retain immutable bytes;
constructing a carrier neither reads a file nor establishes tool observation.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
from types import MappingProxyType
from typing import Optional, Union, get_args, get_origin, get_type_hints

NAME = "native_shared_generation_v1"
VERSION = 1
RENDERER = 26
RUNTIME = "Claude Code (direct)"
CONDITION = "generic_v10"

KINDS = MappingProxyType({'advance_result': 'd4d_native_shared_advance_result',
 'attempt': 'd4d_native_shared_attempt',
 'binding': 'd4d_native_shared_session_binding',
 'capture_pool': 'd4d_native_shared_capture_pool',
 'completion': 'd4d_native_shared_stage_completion',
 'execution': 'd4d_native_shared_execution_registration',
 'journal': 'd4d_native_shared_stage_journal',
 'observation': 'd4d_native_shared_stage_observation',
 'permission': 'd4d_native_shared_saved_permission_probe',
 'permission_expected': 'd4d_native_shared_permission_expected',
 'permission_recipe': 'd4d_native_shared_permission_recipe',
 'receipt_policy': 'd4d_native_shared_receipt_policy',
 'record': 'd4d_native_shared_stage_record',
 'selection': 'd4d_native_shared_selection'})

ROLE_RELATIVE_PATHS = MappingProxyType({'audit': 'outputs/audit.json',
 'completion': 'outputs/completion.json',
 'core_seal': 'sealed/core-seal.json',
 'effective_receipt': 'outputs/effective-receipt.yaml',
 'execution_capture': 'binding/execution.json',
 'journal': 'journal.json',
 'journal_records_root': 'records',
 'observations_root': 'observations',
 'packet': 'outputs/packet.json',
 'phase1_core': 'sealed/core.yaml',
 'phase1_full': 'sealed/full.yaml',
 'phase1_receipt': 'sealed/original-receipt.yaml',
 'phase1_seal': 'sealed/phase1.json',
 'receipt_carry': 'outputs/receipt-carry.json',
 'receipt_result': 'outputs/receipt-result.json',
 'requests_root': 'requests',
 'responses_root': 'responses',
 'session_binding': 'binding/session.json',
 'started_capture': 'binding/started.json',
 'typed_assembly': 'outputs/assembly.json',
 'typed_index': 'outputs/typed-index.json'})

HARD_LIMITS = MappingProxyType({'advance_invocations': 8214,
 'assembly_bytes': 160000000,
 'authority_files': 640,
 'authority_raw_total_bytes': 64000000,
 'captured_members': 65536,
 'evidence_metadata_wire_bytes': 16000000,
 'evidence_raw_total_bytes': 512000000,
 'evidence_wire_bytes': 704000000,
 'failure_diagnostics_bytes': 65536,
 'finalization_reserve_history_bytes': 32000000,
 'finalization_reserve_history_records': 1,
 'finalization_reserve_observation_records': 2,
 'finalization_reserve_raw_bytes': 32000000,
 'generic_response_bytes': 8000000,
 'history_metadata_total_bytes': 64000000,
 'history_records': 16384,
 'input_bytes': 8000000,
 'inventory_bytes_per_worker': 4000000,
 'journal_bytes': 16000000,
 'json_yaml_depth': 64,
 'json_yaml_nodes_per_document': 200000,
 'metadata_record_bytes': 4000000,
 'observation_records': 32768,
 'original_full_bytes': 4000000,
 'original_record_nodes': 100000,
 'packet_bytes': 96000000,
 'paths_per_worker': 100000,
 'permission_decoded_total_bytes': 32000000,
 'permission_jsonl_rows_per_member': 256,
 'permission_member_bytes': 8000000,
 'permission_members': 128,
 'permission_metadata_wire_bytes': 4000000,
 'permission_recipe_sources': 32,
 'permission_wire_bytes': 196000000,
 'populated_paths': 100000,
 'request_bytes': 64000000,
 'schema_files_per_closure': 256,
 'schema_member_bytes': 8000000,
 'schema_raw_total_bytes_per_closure': 16000000,
 'selection_metadata_bytes': 2000000,
 'stream_bytes': 384000000,
 'stream_rows': 200000,
 'submissions': 4099,
 'typed_response_bytes': 2097152,
 'typed_saved_envelope_bytes': 3000000,
 'workers': 4096})

BOUND_CEILINGS = MappingProxyType({'max_authority_bytes': 64000000,
 'max_evidence_bytes': 512000000,
 'max_history_bytes': 64000000,
 'max_history_records': 16384,
 'max_input_bytes': 8000000,
 'max_inventory_bytes': 4000000,
 'max_paths_per_worker': 100000,
 'max_populated_paths': 100000,
 'max_request_bytes': 64000000,
 'max_response_bytes': 8000000,
 'max_submissions': 4099,
 'max_workers': 4096})

BOUND_KEYS = frozenset(BOUND_CEILINGS)
OUTER_REQUEST_KEYS = frozenset(('protocol', 'selection', 'execution', 'attempt_id', 'session_id', 'cursor', 'predecessor_history_sha256', 'phase1', 'policies', 'receipt_carry', 'generation_context', 'owner_context', 'inner_request', 'response'))
STATES = frozenset(('assembly_complete', 'await_core', 'awaiting_response', 'failed', 'receipt_zero_work', 'request_ready'))

_TYPE_CACHE = {}


def _matches(value, annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Union:
        return any(_matches(value, item) for item in args)
    if origin is tuple:
        if type(value) is not tuple:
            return False
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_matches(item, args[0]) for item in value)
        return len(value) == len(args) and all(_matches(v, t) for v, t in zip(value, args))
    return type(value) is annotation


class _Carrier:
    def __post_init__(self):
        cls = type(self)
        if cls not in _TYPE_CACHE:
            _TYPE_CACHE[cls] = get_type_hints(cls)
        for field in fields(self):
            if not _matches(getattr(self, field.name), _TYPE_CACHE[cls][field.name]):
                raise ValueError(f"{cls.__name__}.{field.name} has the wrong immutable type")
        _validate_carrier(self)


@dataclass(frozen=True)
class ArtifactPin(_Carrier):
    role: str
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class CapturedArtifact(_Carrier):
    pin: ArtifactPin
    raw: bytes


@dataclass(frozen=True)
class CurrentAdvance(_Carrier):
    admission_observation: CapturedArtifact
    argv: tuple[str, ...]
    call: ObservedCall
    command: str
    control_prefix: EvidencePrefix
    predecessor_history_sha256: str
    transcript_prefix: EvidencePrefix
    working_directory: str


@dataclass(frozen=True)
class DescriptorCapture(_Carrier):
    raw: bytes
    sha256: str


@dataclass(frozen=True)
class EventRef(_Carrier):
    stream: str
    line: int
    block: Optional[int]
    raw_line_sha256: str
    value_sha256: str


@dataclass(frozen=True)
class EvidencePrefix(_Carrier):
    stream: str
    path: str
    raw: bytes
    bytes: int
    sha256: str
    lines: int


@dataclass(frozen=True)
class ExecutionBinding(_Carrier):
    attempt_id: str
    binding_artifact: CapturedArtifact
    execution: CapturedArtifact
    init_observation: CapturedArtifact
    instruction_sha256: str
    permission_sha256: str
    registered_python: str
    runtime_declaration: CapturedArtifact
    runtime_declaration_sha256: str
    selection_sha256: str
    session_id: str
    started: CapturedArtifact
    working_directory: str


@dataclass(frozen=True)
class HelperPublication(_Carrier):
    action: str
    artifact: ProposedArtifact
    predecessor_sha256: Optional[str]


@dataclass(frozen=True)
class NativeEffectView(_Carrier):
    correction_window: bool
    cursor: Optional[StageCursor]
    execution_binding_sha256: str
    history_sha256: str
    pending_advance_tool_use_id: Optional[str]
    protected_roles: tuple[RolePath, ...]
    protocol: str
    request: Optional[ArtifactPin]
    request_read_observation_sha256: Optional[str]
    response: Optional[ResponseDestination]
    response_intent_observation_sha256: Optional[str]
    sealed: tuple[ArtifactPin, ...]
    selection_sha256: str
    stage_command: str
    stage_root: str
    state: str
    static_policy_sha256: str
    working_directory: str


@dataclass(frozen=True)
class NativeSelectionCapture(_Carrier):
    arm: str
    authority: tuple[CapturedArtifact, ...]
    bounds_json: bytes
    condition: str
    descriptor: DescriptorCapture
    project: str
    protocol: str
    receipt_policy: CapturedArtifact
    registration: CapturedArtifact
    roles: tuple[RolePath, ...]
    run_id: str
    schemas: tuple[SchemaClosureCapture, ...]

    def document(self) -> dict:
        return parse_selection(self.registration.raw)

    def raw(self, role_or_path: str) -> bytes:
        candidates = (self.registration, self.receipt_policy, *self.authority,
                      *(source for schema in self.schemas for source in schema.sources))
        found = [a.raw for a in candidates if role_or_path in (a.pin.role, a.pin.path)]
        if not found or any(raw != found[0] for raw in found):
            raise ValueError("authority is absent or ambiguous in the immutable capture")
        return found[0]

    def role(self, name: str) -> str:
        found = [entry.path for entry in self.roles if entry.role == name]
        if len(found) != 1:
            raise ValueError("unknown or ambiguous native shared role")
        return found[0]

    def bounds(self) -> dict:
        return parse_bounds(strict_json(self.bounds_json, "stage bounds"))

    def generation_context(self) -> dict:
        inputs = self.document()["inputs"]
        context, profile = inputs["context"], inputs["profile"]
        vocabulary = profile["vocabulary"]
        if vocabulary is not None:
            profile["vocabulary"] = {
                "identity": vocabulary,
                "raw_text": self.raw(vocabulary["path"]).decode("utf-8")}
        return {"context": {"identity": context,
                            "raw_json": self.raw(context["path"]).decode("utf-8")},
                "profile": profile, "source_manifest": inputs["source_manifest"],
                "scope": "Caller-declared generation scope, source policy and vocabulary; "
                         "not a scientific applicability or support verdict."}


@dataclass(frozen=True)
class ObservedCall(_Carrier):
    admission: EventRef
    call: EventRef
    callback: EventRef
    input_json: bytes
    session_id: str
    tool_name: str
    tool_use_id: str


@dataclass(frozen=True)
class ObservedToolRequest(_Carrier):
    call: EventRef
    callback: EventRef
    input_json: bytes
    session_id: str
    tool_name: str
    tool_use_id: str


@dataclass(frozen=True)
class Phase1Capture(_Carrier):
    core: Optional[CapturedArtifact]
    core_seal: Optional[CapturedArtifact]
    core_seal_observation: Optional[CapturedArtifact]
    full: CapturedArtifact
    full_seal_observation: CapturedArtifact
    original_receipt: CapturedArtifact
    seal: CapturedArtifact


@dataclass(frozen=True)
class ProposedArtifact(_Carrier):
    pin: ArtifactPin
    raw: bytes


@dataclass(frozen=True)
class RawHistory(_Carrier):
    artifacts: tuple[CapturedArtifact, ...]
    journal: CapturedArtifact
    observations: tuple[CapturedArtifact, ...]
    records: tuple[CapturedArtifact, ...]


@dataclass(frozen=True)
class ResponseDestination(_Carrier):
    max_bytes: int
    media_type: str
    path: str
    role: str


@dataclass(frozen=True)
class RolePath(_Carrier):
    role: str
    path: str


@dataclass(frozen=True)
class SchemaClosureCapture(_Carrier):
    closure_sha256: str
    import_roles: tuple[tuple[str, str], ...]
    kind: str
    root_class: str
    root_name: str
    sources: tuple[CapturedArtifact, ...]


@dataclass(frozen=True)
class SettledCall(_Carrier):
    call: ObservedCall
    observation: CapturedArtifact
    result: EventRef


@dataclass(frozen=True)
class StageCompletion(_Carrier):
    assembly: CapturedArtifact
    attempt_id: str
    audit: CapturedArtifact
    core_seal_sha256: str
    counts_json: bytes
    effective_receipt: CapturedArtifact
    execution_sha256: str
    history_sha256: str
    packet: CapturedArtifact
    phase1_seal_sha256: str
    receipt_carry: CapturedArtifact
    receipt_result: CapturedArtifact
    selection_sha256: str
    session_id: str
    stage_origins_json: bytes
    typed_index: CapturedArtifact


@dataclass(frozen=True)
class StageCursor(_Carrier):
    ordinal: int
    kind: str
    target_id: str


@dataclass(frozen=True)
class StageDecision(_Carrier):
    completion: Optional[StageCompletion]
    cursor: Optional[StageCursor]
    failure_json: Optional[bytes]
    history_sha256: str
    publications: tuple[HelperPublication, ...]
    request: Union[CapturedArtifact, ProposedArtifact, None]
    request_predecessor_history_sha256: Optional[str]
    response: Optional[ResponseDestination]
    sealed: tuple[ArtifactPin, ...]
    state: str


@dataclass(frozen=True)
class StageInvocationCapture(_Carrier):
    current_advance: CurrentAdvance
    execution: ExecutionBinding
    history: RawHistory
    phase1: Phase1Capture
    selection: NativeSelectionCapture


@dataclass(frozen=True)
class StageTransition(_Carrier):
    before_history_sha256: str
    consumed_record_sha256: str
    cursor: StageCursor
    disposition: str
    first_response: CapturedArtifact
    predicted_journal: ProposedArtifact
    publications: tuple[HelperPublication, ...]
    records_to_append: tuple[ProposedArtifact, ...]
    request_sha256: str


RECORD_TYPES = frozenset({
    "genesis", "session_bound", "phase1_sealed", "core_sealed", "request_admitted",
    "response_consumed", "stage_checked", "receipt_zero_work", "waiting_for_core",
    "failed", "assembly_checked",
})


def sha(raw: bytes) -> str:
    if type(raw) is not bytes:
        raise ValueError("hash input must be immutable bytes")
    return hashlib.sha256(raw).hexdigest()


def _json_values(value):
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if depth > HARD_LIMITS["json_yaml_depth"] or nodes > HARD_LIMITS["json_yaml_nodes_per_document"]:
            raise ValueError("native shared JSON exceeds its structural bound")
        if type(item) is dict:
            if any(type(k) is not str for k in item):
                raise ValueError("JSON object keys must be strings")
            pending.extend((v, depth + 1) for v in item.values())
        elif type(item) in (list, tuple):
            pending.extend((v, depth + 1) for v in item)
        elif type(item) is float:
            if not math.isfinite(item):
                raise ValueError("nonfinite JSON number")
        elif type(item) not in (str, int, bool, type(None)):
            raise ValueError("unsupported native shared JSON value")


def canonical(value) -> bytes:
    _json_values(value)
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                          separators=(",", ":")).encode("utf-8")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("native shared value is not canonical UTF-8 JSON") from exc


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate native shared JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite native shared JSON constant: " + value)


def _lexical_budget(text):
    """Bound nesting and value starts before json.loads allocates containers."""
    quoted = escaped = scalar = False
    depth = starts = 0
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char.isspace() or char in ",:":
            scalar = False
        elif char in "{[":
            depth += 1
            starts += 1
            scalar = False
        elif char in "}]":
            depth -= 1
            scalar = False
        elif char == '"':
            quoted = True
            starts += 1
            scalar = False
        elif not scalar:
            scalar = True
            starts += 1
        if depth > HARD_LIMITS["json_yaml_depth"] or starts > HARD_LIMITS["json_yaml_nodes_per_document"]:
            raise ValueError("native shared JSON exceeds its structural bound")


def strict_json(raw: bytes, label="native shared JSON", max_bytes=2_000_000):
    positive_int(max_bytes, "JSON byte bound")
    if type(raw) is not bytes or not raw or len(raw) > max_bytes:
        raise ValueError(f"{label} requires bounded nonempty immutable bytes")
    try:
        text = raw.decode("utf-8")
        _lexical_budget(text)
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject_constant)
        _json_values(value)
        # Surrogate escapes can parse, but cannot represent canonical UTF-8.
        canonical(value)
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"{label} is not strict UTF-8 JSON") from exc


def exact(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"{label} fields differ from the closed contract")
    return value


def positive_int(value, label, maximum=None):
    if type(value) is not int or value < 1 or (maximum is not None and value > maximum):
        raise ValueError(f"{label} must be a positive integer within its bound")
    return value


def _nonnegative(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")


def _text(value, label):
    if (type(value) is not str or not value.strip()
            or any(ord(c) < 32 for c in value)):
        raise ValueError(f"{label} requires explicit nonblank single-line text")
    return value


def _hash(value, label):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} requires a lowercase SHA256")
    return value


def canonical_path(value, label="path") -> str:
    _text(value, label)
    path = PurePosixPath(value)
    if (not path.is_absolute() or str(path) != value or ".." in path.parts
            or value.startswith("//")):
        raise ValueError(f"{label} requires an exact canonical absolute path")
    return value


def file_pin(value, label="file pin") -> dict:
    exact(value, {"path", "bytes", "sha256"}, label)
    canonical_path(value["path"], label + " path")
    positive_int(value["bytes"], label + " bytes", HARD_LIMITS["authority_raw_total_bytes"])
    _hash(value["sha256"], label + " hash")
    return dict(value)


def pin_dict(pin: ArtifactPin) -> dict:
    if type(pin) is not ArtifactPin:
        raise ValueError("expected an exact ArtifactPin")
    return {"role": pin.role, "path": pin.path, "bytes": pin.bytes, "sha256": pin.sha256}


def parse_bounds(value) -> dict:
    exact(value, BOUND_KEYS, "native stage bounds")
    for key, maximum in BOUND_CEILINGS.items():
        positive_int(value[key], key, maximum)
    if (value["max_history_bytes"] <= HARD_LIMITS["finalization_reserve_history_bytes"]
            or value["max_evidence_bytes"] <= HARD_LIMITS["finalization_reserve_raw_bytes"]
            or value["max_history_records"] <= HARD_LIMITS["finalization_reserve_history_records"]
            or value["max_submissions"] < 3):
        raise ValueError("stage bounds leave no room for mandatory stages and failure evidence")
    return dict(value)


def role_paths(selection_path: str, stage_root: str) -> tuple[RolePath, ...]:
    canonical_path(selection_path, "selection path")
    canonical_path(stage_root, "stage root")
    root = PurePosixPath(stage_root)
    if root == PurePosixPath("/") or selection_path == stage_root or root in PurePosixPath(selection_path).parents:
        raise ValueError("selection must be outside the separate mutable stage root")
    return (RolePath("selection", selection_path), RolePath("stage_root", stage_root),
            *(RolePath(role, str(root / relative)) for role, relative in ROLE_RELATIVE_PATHS.items()))


def parse_selection(raw: bytes) -> dict:
    value = strict_json(raw, "native selection", HARD_LIMITS["selection_metadata_bytes"])
    exact(value, {"kind", "version", "registration_id", "registration_path", "run",
                  "selection", "inputs", "receipt_policy", "bounds", "stage_root"}, "native selection")
    if value["kind"] != KINDS["selection"] or type(value["version"]) is not int or value["version"] != VERSION:
        raise ValueError("unknown native selection kind/version")
    _text(value["registration_id"], "registration ID")
    role_paths(value["registration_path"], value["stage_root"])
    run = exact(value["run"], {"project", "arm", "method", "label"}, "native run")
    for key, item in run.items():
        _text(item, "run " + key)
    if run["method"] != "claudecode_direct":
        raise ValueError("native shared method must be claudecode_direct")
    selected = value["selection"]
    axes = {"protocol": NAME, "version": VERSION, "condition": CONDITION, "renderer": RENDERER,
            "runtime": RUNTIME, "native_shared_generation_version": 1,
            "native_source_attribution_version": 0, "shared_generation_version": 0,
            "api_playbook_version": 0, "receipt_completion_version": 0, "removal_repair_version": 0}
    exact(selected, set(axes) | {"descriptor_sha256", "assets"}, "native selector")
    if any(type(selected[k]) is not type(expected) or selected[k] != expected for k, expected in axes.items()):
        raise ValueError("native shared selector has mixed or unsupported axes")
    _hash(selected["descriptor_sha256"], "descriptor hash")
    assets = selected["assets"]
    if type(assets) is not dict or not assets or len(assets) > HARD_LIMITS["authority_files"]:
        raise ValueError("native selector requires its bounded complete asset closure")
    for name, pin in assets.items():
        _text(name, "asset name")
        logical = PurePosixPath(name)
        if logical.is_absolute() or str(logical) != name or ".." in logical.parts:
            raise ValueError("asset name must be an exact relative resource name")
        file_pin(pin, "asset pin")
    inputs = exact(value["inputs"], {"project", "bundle", "chunk_manifest", "source_manifest",
        "context", "profile", "full_schema", "core_schema"}, "native inputs")
    if inputs["project"] != run["project"]:
        raise ValueError("native input project differs from the selected run")
    for key in ("bundle", "chunk_manifest", "context", "source_manifest"):
        if key == "source_manifest" and inputs[key] is None:
            continue
        file_pin(inputs[key], key)
        if inputs[key]["bytes"] > HARD_LIMITS["input_bytes"]:
            raise ValueError("native input exceeds the typed input ceiling")
    profile = exact(inputs["profile"], {"name", "basis", "vocabulary"}, "native profile")
    _text(profile["name"], "profile name")
    _text(profile["basis"], "profile basis")
    if profile["vocabulary"] is not None:
        file_pin(profile["vocabulary"], "profile vocabulary")
        if profile["vocabulary"]["bytes"] > HARD_LIMITS["input_bytes"]:
            raise ValueError("native vocabulary exceeds the typed input ceiling")
    for key, cls in (("full_schema", "Dataset"), ("core_schema", "CoreDataset")):
        schema = exact(inputs[key], {"root", "root_class", "sources"}, key)
        canonical_path(schema["root"], "schema root")
        if schema["root_class"] != cls:
            raise ValueError("schema root class differs from its selected role")
        sources = schema["sources"]
        if type(sources) is not list or not 0 < len(sources) <= HARD_LIMITS["schema_files_per_closure"]:
            raise ValueError("schema requires a bounded complete source closure")
        names, paths, total = [], [], 0
        for source in sources:
            exact(source, {"name", "path", "bytes", "sha256"}, "schema source")
            _text(source["name"], "schema import name")
            file_pin({k: source[k] for k in ("path", "bytes", "sha256")}, "schema source")
            if source["bytes"] > HARD_LIMITS["schema_member_bytes"]:
                raise ValueError("schema source exceeds member limit")
            names.append(source["name"])
            paths.append(source["path"])
            total += source["bytes"]
        if (len(set(names)) != len(names) or len(set(paths)) != len(paths)
                or paths[0] != schema["root"] or total > HARD_LIMITS["schema_raw_total_bytes_per_closure"]):
            raise ValueError("schema source closure has inconsistent roots, identities or size")
    file_pin(value["receipt_policy"], "native receipt policy")
    bounds = parse_bounds(value["bounds"])
    declarations = [value["receipt_policy"], *assets.values()]
    declarations.extend(inputs[k] for k in ("bundle", "chunk_manifest", "context", "source_manifest")
                        if inputs[k] is not None)
    if profile["vocabulary"] is not None:
        declarations.append(profile["vocabulary"])
    for key in ("full_schema", "core_schema"):
        declarations.extend({k: source[k] for k in ("path", "bytes", "sha256")}
                            for source in inputs[key]["sources"])
    by_path = {}
    stage_root = PurePosixPath(value["stage_root"])
    for pin in declarations:
        path = PurePosixPath(pin["path"])
        if (path == stage_root or stage_root in path.parents
                or pin["path"] == value["registration_path"]):
            raise ValueError("selection authority overlaps its own declaration or mutable stage root")
        if pin["path"] in by_path and by_path[pin["path"]] != pin:
            raise ValueError("one authority path has conflicting declared identities")
        by_path[pin["path"]] = pin
    if (len(by_path) + 1 > HARD_LIMITS["authority_files"]
            or len(raw) + sum(pin["bytes"] for pin in by_path.values()) > bounds["max_authority_bytes"]):
        raise ValueError("declared complete authority exceeds the supplied bound")
    if any(inputs[k] is not None and inputs[k]["bytes"] > bounds["max_input_bytes"]
           for k in ("bundle", "chunk_manifest", "context", "source_manifest")):
        raise ValueError("declared input exceeds the supplied input bound")
    if profile["vocabulary"] is not None and profile["vocabulary"]["bytes"] > bounds["max_input_bytes"]:
        raise ValueError("declared vocabulary exceeds the supplied input bound")
    return value


def parse_receipt_policy(raw: bytes, policy_sha256: Optional[str] = None) -> dict:
    value = strict_json(raw, "native receipt policy")
    exact(value, {"kind", "version", "registration_id", "condition", "runtime_policy_sha256",
                  "receipt_instrument_version", "coverage_floor"}, "native receipt policy")
    if (value["kind"] != KINDS["receipt_policy"] or type(value["version"]) is not int
            or value["version"] != VERSION or value["condition"] != CONDITION
            or type(value["receipt_instrument_version"]) is not int or value["receipt_instrument_version"] != 4):
        raise ValueError("unknown native receipt policy selection")
    _text(value["registration_id"], "receipt registration ID")
    _hash(value["runtime_policy_sha256"], "native receipt asset hash")
    if policy_sha256 is not None and value["runtime_policy_sha256"] != _hash(policy_sha256, "expected receipt hash"):
        raise ValueError("native receipt asset differs from the selected policy")
    floor = value["coverage_floor"]
    if type(floor) is not dict:
        raise ValueError("coverage floor must be explicit")
    if floor.get("state") == "pending":
        if floor != {"state": "pending", "mode": "diagnostic_pilot"}:
            raise ValueError("pending coverage floor requires diagnostic_pilot")
    elif floor.get("state") == "registered":
        exact(floor, {"state", "numerator", "denominator"}, "coverage floor")
        _nonnegative(floor["numerator"], "floor numerator")
        positive_int(floor["denominator"], "floor denominator")
        if floor["numerator"] > floor["denominator"]:
            raise ValueError("coverage floor exceeds one")
    else:
        raise ValueError("coverage floor must be pending or registered")
    return value


def schema_closure_sha(sources, import_roles) -> str:
    by_role = {source.pin.role: source.pin for source in sources}
    return sha(canonical([{"name": name, **pin_dict(by_role[role])}
                          for name, role in sorted(import_roles)]))


def _validate_carrier(value):
    for field in fields(value):
        item = getattr(value, field.name)
        if item is not None and (field.name == "sha256" or field.name.endswith("_sha256")):
            _hash(item, field.name)
    if type(value) in (ArtifactPin, RolePath, ResponseDestination):
        _text(value.role, "artifact role")
        canonical_path(value.path)
    if type(value) is ArtifactPin:
        _nonnegative(value.bytes, "artifact bytes")
    elif type(value) in (CapturedArtifact, ProposedArtifact):
        if len(value.raw) != value.pin.bytes or sha(value.raw) != value.pin.sha256:
            raise ValueError("artifact raw bytes differ from their pin")
    elif type(value) is DescriptorCapture:
        if sha(value.raw) != value.sha256 or canonical(strict_json(value.raw)) != value.raw:
            raise ValueError("descriptor must retain its exact canonical bytes and hash")
    elif type(value) is ResponseDestination:
        positive_int(value.max_bytes, "response byte bound", HARD_LIMITS["generic_response_bytes"])
        _text(value.media_type, "response media type")
    elif type(value) is StageCursor:
        positive_int(value.ordinal, "stage ordinal", HARD_LIMITS["submissions"])
        if value.kind not in {"receipt", "worker", "omission", "integration"}:
            raise ValueError("unknown native stage kind")
        _text(value.target_id, "stage target")
    elif type(value) is SchemaClosureCapture:
        if value.kind not in {"full", "core"} or value.root_class != {"full": "Dataset", "core": "CoreDataset"}[value.kind]:
            raise ValueError("schema closure role/class differs")
        names = [name for name, _ in value.import_roles]
        roles = [role for _, role in value.import_roles]
        actual = [source.pin.role for source in value.sources]
        if (not actual or len(actual) > HARD_LIMITS["schema_files_per_closure"]
                or len(names) != len(set(names)) or len(roles) != len(set(roles))
                or len(actual) != len(set(actual)) or set(roles) != set(actual)
                or value.root_name not in names or dict(value.import_roles)[value.root_name] != actual[0]):
            raise ValueError("schema closure is incomplete or ambiguous")
        if (any(len(s.raw) > HARD_LIMITS["schema_member_bytes"] for s in value.sources)
                or sum(len(s.raw) for s in value.sources) > HARD_LIMITS["schema_raw_total_bytes_per_closure"]
                or schema_closure_sha(value.sources, value.import_roles) != value.closure_sha256):
            raise ValueError("schema closure bytes differ from their bound identity")
    elif type(value) is NativeSelectionCapture:
        doc = value.document()
        if (value.protocol != NAME or value.condition != CONDITION or value.run_id != doc["registration_id"]
                or value.project != doc["run"]["project"] or value.arm != doc["run"]["arm"]
                or value.registration.pin.role != "selection"
                or value.registration.pin.path != doc["registration_path"]
                or value.roles != role_paths(doc["registration_path"], doc["stage_root"])
                or value.descriptor.sha256 != doc["selection"]["descriptor_sha256"]
                or canonical(value.bounds()) != canonical(doc["bounds"])
                or {s.kind for s in value.schemas} != {"full", "core"} or len(value.schemas) != 2):
            raise ValueError("selection carrier disagrees with its immutable declaration")
        receipt_pin = {k: getattr(value.receipt_policy.pin, k) for k in ("path", "bytes", "sha256")}
        if receipt_pin != doc["receipt_policy"]:
            raise ValueError("captured native receipt policy differs from selection")
        parse_receipt_policy(value.receipt_policy.raw)
        roles = [a.pin.role for a in value.authority]
        if len(set(roles)) != len(roles):
            raise ValueError("duplicate captured authority roles")
    elif type(value) is EvidencePrefix:
        canonical_path(value.path, "stream path")
        if (value.stream not in {"transcript", "control"} or value.bytes != len(value.raw)
                or value.bytes > HARD_LIMITS["stream_bytes"] or sha(value.raw) != value.sha256
                or value.lines != value.raw.count(b"\n") or value.lines > HARD_LIMITS["stream_rows"]
                or (value.raw and not value.raw.endswith(b"\n"))):
            raise ValueError("stream prefix must end at its exact complete line boundary")
    elif type(value) is EventRef:
        if value.stream not in {"transcript", "control"}:
            raise ValueError("unknown event stream")
        positive_int(value.line, "event line", HARD_LIMITS["stream_rows"])
        if value.block is not None:
            _nonnegative(value.block, "event block")
    elif type(value) in (ObservedToolRequest, ObservedCall):
        for item in (value.tool_use_id, value.tool_name, value.session_id):
            _text(item, "observed tool identity")
        if type(strict_json(value.input_json, "tool input", HARD_LIMITS["request_bytes"])) is not dict:
            raise ValueError("tool input must retain a typed JSON object")
    elif type(value) is ExecutionBinding:
        if value.runtime_declaration.pin.sha256 != value.runtime_declaration_sha256:
            raise ValueError("runtime binding differs from sole captured declaration")
        canonical_path(value.registered_python, "registered Python")
        canonical_path(value.working_directory, "registered working directory")
        _text(value.attempt_id, "attempt ID")
        _text(value.session_id, "session ID")
    elif type(value) is Phase1Capture:
        present = [x is not None for x in (value.core, value.core_seal, value.core_seal_observation)]
        if any(present) and not all(present):
            raise ValueError("core, core seal and its observation must appear together")
    elif type(value) is HelperPublication:
        if (value.action not in {"create_once", "replace_journal_from_exact_predecessor"}
                or (value.action == "create_once") != (value.predecessor_sha256 is None)):
            raise ValueError("publication action/predecessor differ")
        if value.action == "replace_journal_from_exact_predecessor" and value.artifact.pin.role != "journal":
            raise ValueError("only the journal admits exact-predecessor replacement")
    elif type(value) is StageDecision:
        if value.state not in STATES:
            raise ValueError("unknown stage decision state")
        if value.state == "awaiting_response":
            if type(value.request) is not CapturedArtifact or value.cursor is None or value.response is None:
                raise ValueError("awaiting response requires an observed current request")
        elif value.response is not None:
            raise ValueError("only awaiting_response exposes model Write authority")
        if value.state in {"receipt_zero_work", "await_core", "assembly_complete", "failed"}:
            if value.cursor is not None or value.request is not None:
                raise ValueError("nonrequest stage must not expose a cursor/request")
        if value.state == "request_ready" and (type(value.request) is not ProposedArtifact or value.cursor is None):
            raise ValueError("request_ready requires a proposed request and cursor")
        if (value.state == "assembly_complete") != (value.completion is not None):
            raise ValueError("completion is confined to assembly_complete")
        if (value.state == "failed") != (value.failure_json is not None):
            raise ValueError("failure detail is confined to failed decisions")
    elif type(value) is NativeEffectView:
        if value.protocol != NAME or value.state not in STATES:
            raise ValueError("unknown native effect protocol/state")
        if value.state != "awaiting_response" and value.response is not None:
            raise ValueError("effect view exposes a response outside its admitted stage")
        canonical_path(value.stage_root, "effect stage root")
        canonical_path(value.working_directory, "effect working directory")
    elif type(value) is StageTransition:
        if value.disposition not in {"checked", "failed"} or value.predicted_journal.pin.role != "journal":
            raise ValueError("invalid stage transition disposition or journal role")
