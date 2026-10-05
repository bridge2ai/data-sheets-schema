"""Explicit shared-generation API protocol and immutable caller registration.

Selection is preparation, not campaign, comparator or scientific approval.
No client, native process or network access occurs in this module.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

NAME = "shared_generation_v1"
FORMAT = "shared_generation_registration_v1"
PROMPT = "src/download/prompts/d4d_generic_arm_prompt_v10.md"
POLICY = "src/download/prompts/shared_generation_v1.md"
API_POLICY = "src/download/prompts/api_playbook_v2.md"
RECEIPT_POLICY = "src/download/prompts/receipt_completion_runtime_v2.md"
SELECTED_PLAYBOOKS = (
    ".claude/agents/d4d-provenance-guard-v2.md",
    ".claude/commands/d4d-agent-v2.md",
    ".claude/commands/d4d-full-core-v2.md",
    ".claude/commands/d4d-uniform-rules-v2.md",
)
# Versioned content identities. This is separate from the history-backed prompt
# registry; both must agree. No asset is trusted merely because it names itself.
ASSET_HASHES = {'.claude/agents/d4d-provenance-guard-v2.md': '10dc4689e1855096ef3507de01b129abfd5795690fbcfbd3458407741fe30085',
 '.claude/commands/d4d-agent-v2.md': 'dcb33659014a68596a248ed768c196dd0b1e396a0fe41579918dff95ac559299',
 '.claude/commands/d4d-full-core-v2.md': '2f52d3e70d7a6f3098b7acfcc80b9e9d0f318c9ca1517f711eae9fb789410124',
 '.claude/commands/d4d-uniform-rules-v2.md': '7b511b1ef15d6fb56d47dc58b367196ed9c7269a61406ed19127481f719c885a',
 'src/download/prompts/api_playbook_v2.md': '5fa3385ae994231cf68f8432d0dba35a86d8c4e37120e80d0aecda199f5ad719',
 'src/download/prompts/d4d_generic_arm_prompt_v10.md': 'a3a2004cef2147b3351613cb38a67abde1d58c91c19ee0c72c66ff476d0722ec',
 'src/download/prompts/receipt_completion_runtime_v2.md': 'c5f6b3818fabb9256bdb6d035eb1760b92cfe03ad0d8a60ab80becb51bf30d5c',
 'src/download/prompts/shared_generation_v1.md': '34608f26b4a0407da036486a6e8ec6692df6b54594335140bdc3df4229d78450'}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def captured_assets() -> dict[str, bytes]:
    """Verify installed bytes, then resolve references from those same bytes.

    The released provenance walker is deliberately tolerant for historical
    reports. A new selected execution instead refuses missing/changed inputs.
    """
    from .resources import resource_path
    from .provenance import _PLAYBOOK_REF
    captured = {name: resource_path(name).read_bytes() for name in ASSET_HASHES}
    for name, raw in captured.items():
        if sha(raw) != ASSET_HASHES[name]:
            raise ValueError(f"shared-generation selected asset changed: {name}")
    pending, reached = [PROMPT], set()
    while pending:
        name = pending.pop()
        for ref in _PLAYBOOK_REF.findall(captured[name].decode("utf-8")):
            if ref not in reached:
                if ref not in captured:
                    raise ValueError(f"unbound selected playbook reference: {ref}")
                reached.add(ref)
                pending.append(ref)
    expected = {name for name in ASSET_HASHES if name.startswith(".claude/")}
    if reached != expected:
        raise ValueError("selected playbook closure differs from the frozen protocol")
    return captured


def descriptor() -> dict:
    captured_assets()
    return {"protocol": NAME, "version": 1, "condition": "generic_v10",
            "renderer": 25, "runtime": "Claude API (direct)",
            "typed_protocol": "typed_audit_protocol_v1", "api_playbook_version": 2,
            "receipt_completion_version": 2, "assets": dict(ASSET_HASHES)}


def policy_text() -> str:
    return captured_assets()[POLICY].decode("utf-8").split("## Prompt body", 1)[1].strip()


def role_instruction() -> str:
    return "## Role relationship review v1" + policy_text().split("## Role relationship review v1", 1)[1]


def select(spec) -> dict | None:
    version = getattr(spec, "shared_generation_version", 0)
    if type(version) is not int or version not in (0, 1):
        raise ValueError("shared_generation_version must be the integer 0 or 1")
    registration = getattr(spec, "shared_generation_registration", None)
    if not version:
        if getattr(spec, 'native_shared_generation_version', 0):
            from .native_shared_render import validate_spec
            validate_spec(spec)
            return None
        if (registration is not None or spec.condition == "generic_v10"
                or spec.render_version == 25 or spec.api_playbook_version == 2
                or spec.receipt_completion_version == 2):
            raise ValueError("shared-generation selections require explicit version 1 and registration")
        return None
    if (spec.condition != "generic_v10" or spec.render_version != 25
            or spec.runtime != "Claude API (direct)" or spec.api_playbook_version != 2
            or spec.receipt_completion_version != 2 or spec.removal_repair_version
            or spec.native_source_attribution_version):
        raise ValueError("shared generation v1 requires generic_v10/API25/playbook2/receipt2; native and removal repair are not supported")
    if type(registration) is not str or not registration:
        raise ValueError("shared generation requires captured immutable registration JSON")
    return descriptor()

MAX_REGISTRATION_BYTES = 2_000_000
MAX_AUTHORITY_BYTES = 64_000_000
_AUDIT_LIMITS = {"max_paths", "max_inventory_bytes", "max_workers", "max_request_bytes",
    "max_input_tokens_per_call", "worker_output_tokens", "omission_output_tokens",
    "integration_output_tokens", "aggregate_input_tokens", "aggregate_output_tokens",
    "max_calls", "context_limit_tokens", "context_limit_basis"}


def _exact(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"{label} fields differ from the registered contract")


def _integer(value, label, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} requires an integer >= {minimum}")
    return value


def _text(value, label):
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} requires nonempty text")
    return value


def _path(value, label):
    value = _text(value, label)
    selected = Path(value)
    if not selected.is_absolute() or ".." in selected.parts or str(selected) != value:
        raise ValueError(f"{label} requires an explicit absolute normalized path")
    return selected


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate registration key: {key}")
        value[key] = item
    return value


def _invalid_constant(value):
    raise ValueError(f"nonfinite registration value: {value}")


def parse_registration(raw: bytes) -> dict:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_REGISTRATION_BYTES:
        raise ValueError("shared registration requires bounded nonempty UTF-8 bytes")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=_invalid_constant)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError("shared registration requires strict UTF-8 JSON") from exc
    _exact(value, {"format", "registration_id", "registration_path", "selection", "inputs",
                   "runtime", "audit_limits", "audit_transport", "receipt", "run"}, "shared registration")
    if value["format"] != FORMAT or canonical(value["selection"]) != canonical(descriptor()):
        raise ValueError("shared registration names a different protocol or selected assets")
    _text(value["registration_id"], "registration_id")
    _path(value["registration_path"], "registration_path")
    _exact(value["run"], {"project", "arm", "method", "label"}, "registered run")
    for key, item in value["run"].items():
        _text(item, "run " + key)
    inputs = value["inputs"]
    _exact(inputs, {"project", "bundle", "chunk_manifest", "source_manifest", "context",
                    "profile", "full_schema", "core_schema"}, "registered inputs")
    _text(inputs["project"], "project")
    _exact(inputs["profile"], {"name", "basis", "vocabulary"}, "registered profile")
    if inputs["profile"]["vocabulary"] is not None:
        _validate_pin(inputs["profile"]["vocabulary"], "profile vocabulary")
    for key in ("name", "basis"):
        _text(inputs["profile"][key], f"profile {key}")
    for key in ("bundle", "chunk_manifest", "context", "source_manifest"):
        if key == "source_manifest" and inputs[key] is None:
            continue
        _validate_pin(inputs[key], key)
    for key in ("full_schema", "core_schema"):
        selected = inputs[key]
        _exact(selected, {"root", "sources"}, key)
        _path(selected["root"], key + " root")
        if type(selected["sources"]) is not list or not 0 < len(selected["sources"]) <= 256:
            raise ValueError("registered schema requires its complete bounded import closure")
        names = []
        for pin in selected["sources"]:
            _validate_pin(pin, key)
            names.append(pin["path"])
        if len(set(names)) != len(names) or names[0] != selected["root"]:
            raise ValueError("schema closure root/order/identity is ambiguous")
    runtime = value["runtime"]
    _exact(runtime, {"provider", "base_url", "model", "temperature", "thinking", "effort", "config"}, "runtime")
    for key in ("provider", "base_url", "model"):
        _text(runtime[key], f"runtime {key}")
    if runtime["temperature"] is not None and type(runtime["temperature"]) not in (int, float):
        raise ValueError("temperature must be an explicit finite number or null")
    if runtime["thinking"] is not None and type(runtime["thinking"]) is not dict:
        raise ValueError("thinking must be an explicit mapping or null")
    if runtime["effort"] is not None:
        _text(runtime["effort"], "effort")
    if runtime["config"] is not None:
        _validate_pin(runtime["config"], "runtime config")
    limits = value["audit_limits"]
    _exact(limits, _AUDIT_LIMITS, "audit limits")
    for key in _AUDIT_LIMITS - {"context_limit_basis"}:
        _integer(limits[key], key)
    _text(limits["context_limit_basis"], "context limit basis")
    # Even an empty record has one explicit worker, plus omission/integration.
    # Refuse internally impossible supplied allowances before generation.
    if limits['max_calls'] < 3 or limits['aggregate_input_tokens'] < 3:
        raise ValueError('audit allowances cannot cover the three mandatory stages')
    if limits['aggregate_output_tokens'] < max(limits[f'{stage}_output_tokens']
            for stage in ('worker', 'omission', 'integration')):
        raise ValueError('aggregate audit output allowance cannot admit a declared stage cap')
    for stage in ("worker", "omission", "integration"):
        if limits[f"{stage}_output_tokens"] >= limits["context_limit_tokens"]:
            raise ValueError("audit output allowance leaves no input context")
    if canonical(value["audit_transport"]) != canonical({"transport_attempts": 1, "sdk_max_retries": 0,
                                                           "malformed_response_retries": 0}):
        raise ValueError("shared audit v1 admits exactly one delivery and no automatic answer retries")
    from .receipt_completion_policy import parse_registration as parse_receipt
    receipt = parse_receipt(canonical(value["receipt"]), version=2)
    if receipt["condition"] != "generic_v10":
        raise ValueError("shared receipt registration requires generic_v10")
    return value


def _validate_pin(value, label):
    _exact(value, {"path", "sha256", "bytes"}, label)
    _path(value["path"], label + " path")
    _integer(value["bytes"], label + " bytes")
    if value["bytes"] > MAX_AUTHORITY_BYTES or type(value["sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"]):
        raise ValueError(f"{label} has an invalid hash/byte identity")


def file_pin(path: Path, raw: bytes | None = None) -> dict:
    """Public preparation helper; a pin is not scientific or launch approval."""
    path = Path(path).absolute()
    raw = path.read_bytes() if raw is None else raw
    return {"path": str(path), "sha256": sha(raw), "bytes": len(raw)}


def schema_pin(snapshot) -> dict:
    return {"root": str(snapshot.sources[0][1]),
            "sources": [file_pin(path, raw) for _name, path, raw in snapshot.sources]}


@dataclass(frozen=True)
class Capture:
    registration: bytes
    # Exact authority bytes, with logical paths. No mutable parsed dictionary.
    files: tuple[tuple[str, bytes], ...]
    full_schema: object
    core_schema: object

    def document(self) -> dict:
        return parse_registration(self.registration)

    def raw(self, path: str) -> bytes:
        for selected, raw in self.files:
            if selected == path:
                return raw
        raise ValueError("requested file is outside captured shared-generation authority")

    def identity(self) -> dict:
        return {"registration": {"sha256": sha(self.registration), "raw_json": self.registration.decode("utf-8")},
                "files": [file_pin(Path(path), raw) for path, raw in self.files]}


def _separate_authorities(specs, paths, *, extra_outputs=()):
    """Protect the captured closure and actual immutable assets from all writers."""
    from .shared_generation_resources import resource_paths
    from .shared_write_footprint import for_run, require_separate
    specs = tuple(specs)
    authorities = (*paths, *resource_paths(specs))
    try:
        require_separate(authorities, (for_run(spec) for spec in specs),
                         extra_points=extra_outputs)
    except RuntimeError as exc:
        raise ValueError('shared write footprint cannot resolve a filesystem alias') from exc


def _separate_inputs(spec, paths):
    """Caller authority may not alias any run-owned write destination."""
    _separate_authorities((spec,), paths)


def capture(spec) -> Capture:
    select(spec)
    raw = spec.shared_generation_registration.encode("utf-8")
    reg = parse_registration(raw)
    if reg["run"] != {key: getattr(spec, key) for key in ("project", "arm", "method", "label")}:
        raise ValueError("shared registration belongs to another explicit run")
    selected = reg["inputs"]
    vocabulary_path = spec.profile_obj.pin_path
    vocabulary = selected["profile"]["vocabulary"]
    if spec.chunk_manifest is None:
        raise ValueError("shared generation requires an explicit captured chunk manifest")
    if ((None if vocabulary_path is None else str(vocabulary_path.absolute())) !=
            (None if vocabulary is None else vocabulary["path"])):
        raise ValueError("registered profile vocabulary differs from selected profile")
    if (selected["project"] != spec.project or {k: selected["profile"][k] for k in ("name", "basis")} != {"name": spec.profile, "basis": spec.profile_basis}
            or selected["bundle"]["path"] != str(Path(spec.bundle).absolute())
            or selected["chunk_manifest"]["path"] != str(Path(spec.chunk_manifest).absolute())
            or (None if spec.manifest is None else str(Path(spec.manifest).absolute())) !=
               (None if selected["source_manifest"] is None else selected["source_manifest"]["path"])):
        raise ValueError("registered project/profile/source selection differs from RunSpec")
    if spec.manifest is not None and not spec.manifest_used:
        raise ValueError("shared generation cannot declare a selected source manifest unused")
    if canonical(reg["receipt"]) != canonical(json.loads(spec.receipt_completion_registration)):
        raise ValueError("shared and receipt-completion registrations disagree")
    saved = getattr(spec, "_shared_generation_capture", None)
    if saved is not None:
        if type(saved) is not Capture or saved.registration != raw:
            raise ValueError("shared registration differs from captured authority")
        _separate_inputs(spec, (path for path, _ in saved.files))
        return saved
    files = {reg["registration_path"]: raw}
    pins = [selected[k] for k in ("bundle", "chunk_manifest", "source_manifest", "context") if selected[k] is not None]
    if reg["runtime"]["config"] is not None:
        pins.append(reg["runtime"]["config"])
    if vocabulary is not None:
        pins.append(vocabulary)
    for key in ("full_schema", "core_schema"):
        pins.extend(selected[key]["sources"])
    _separate_inputs(spec, [reg["registration_path"], *(pin["path"] for pin in pins)])
    if Path(reg["registration_path"]).read_bytes() != raw:
        raise ValueError("caller-owned registration bytes differ from the supplied capture")
    for pin in pins:
        path = Path(pin["path"])
        data = files.get(pin["path"])
        if data is None:
            if path.stat().st_size > MAX_AUTHORITY_BYTES:
                raise ValueError("selected authority exceeds byte bound")
            data = files[pin["path"]] = path.read_bytes()
        if file_pin(path, data) != pin:
            raise ValueError(f"registered authority hash/size differs: {path}")
    from . import api_runner as api
    from .resources import resource_path, physical
    from .schema_snapshot import capture_schema
    from .schema_view import captured_view
    snapshots = []
    for key, installed, cls in (("full_schema", api.FULL_SCHEMA_PATH, "Dataset"),
                                ("core_schema", api.CORE_SCHEMA_PATH, "CoreDataset")):
        root = Path(selected[key]["root"])
        if root != physical(resource_path(installed)):
            raise ValueError("registered schema differs from the actual API validation/digest schema")
        def read(path):
            if str(path) not in files:
                raise ValueError("schema import is outside registered captured authority")
            return files[str(path)]
        snapshot = capture_schema(root, read_bytes=read, strict=True)
        if schema_pin(snapshot) != selected[key]:
            raise ValueError("registered schema closure/order differs from its actual imports")
        with captured_view(snapshot) as view:
            if view.get_class(cls) is None:
                raise ValueError(f"captured schema has no {cls}")
        snapshots.append(snapshot)
    from .audit_omissions import _mapping
    from . import audit_omissions as omissions
    context = _mapping(files[selected["context"]["path"]], "generation scope context", json_only=True)
    if omissions._shape(context, json.loads(omissions._asset('context.schema.json'))):
        raise ValueError('generation scope context does not satisfy omission_context_v1')
    owners = [scope['owner'] for scope in context['scopes']]
    if owners.count('') != 1 or len(owners) != len(set(owners)):
        raise ValueError('generation scopes must include root once and name distinct owners')
    # Whether a non-root owner exists requires the generated record and stays
    # in the typed omission check. Impossible inventories need no paid output.
    for key in ('bundle', 'chunk_manifest', 'source_manifest', 'context'):
        pin = selected[key]
        if pin is not None and len(files[pin['path']]) > omissions.MAX_INPUT_BYTES:
            raise ValueError('selected input exceeds typed audit input bound')
    if any(sum(len(raw) for _name, _path, raw in snapshot.sources) > omissions.MAX_SCHEMA_BYTES for snapshot in snapshots):
        raise ValueError('selected schema exceeds typed audit schema bound')
    result = Capture(raw, tuple(sorted(files.items())), *snapshots)
    spec._shared_generation_capture = result
    return result


def identity(spec) -> dict:
    return capture(spec).identity()


def assert_current(spec) -> Capture:
    """Refuse drift before admission; requests still use the original capture."""
    captured = capture(spec)
    captured_assets()
    for path, expected in captured.files:
        if Path(path).read_bytes() != expected:
            raise ValueError(f"shared-generation authority changed: {path}")
    return captured


def preflight(spec, settings) -> Capture:
    captured = assert_current(spec)
    reg = captured.document()
    expected = reg["runtime"]
    from . import api_runner as api
    endpoint = api.provider_identity()
    actual = {"model": settings["name"], "temperature": settings["temperature"] if api.accepts_temperature(settings["name"]) else None,
              "thinking": settings.get("thinking"), "effort": settings.get("effort")}
    for key, value in actual.items():
        if canonical(value) != canonical(expected[key]):
            raise ValueError(f"registered {key} differs from resolved request settings")
    if spec.provider is not None and spec.provider != expected["provider"]:
        raise ValueError("registered provider differs from RunSpec")
    # An offline plan has no credentials/route observation. Actual execution
    # checks this again with the selected client endpoint before any admission.
    for key in ("provider", "base_url"):
        if endpoint[key] is not None and endpoint[key] != expected[key]:
            raise ValueError("registered endpoint differs from actual selected route")
    config = expected["config"]
    if settings.get("config_path"):
        from .resources import resource_path
        if config is None or Path(config["path"]).resolve() != resource_path(settings["config_path"]).resolve():
            raise ValueError("resolved configuration lacks its matching immutable registration pin")
    elif config is not None:
        raise ValueError("registration claims a config not used by resolved settings")
    limits = reg["audit_limits"]
    for stage in ("worker", "omission", "integration"):
        if limits[stage + "_output_tokens"] > api.output_limit(settings["name"]):
            raise ValueError("registered audit output cap exceeds the selected route; no clamping")
    known_window = api.context_facts(settings["name"], [])["limit_tokens"]
    if known_window is not None and limits["context_limit_tokens"] > known_window:
        raise ValueError("registered audit context exceeds the named route window")
    return captured

GENERATION_CONTEXT_HEADER = '# Shared generation: captured generation scope and vocabulary\n\n'
SCHEMA_CONTEXT_HEADER = '# Shared generation: captured schema owners and complete containing values\n\n'


def generation_context(spec) -> str:
    """Complete caller scope authority, distinct from schema-owner context.

    Keep exact input text and its verified identity, including when there is
    no source manifest. This is omission_context_v1, not scientific approval
    or the separately reviewed applicability packet.
    """
    captured = assert_current(spec)
    inputs = captured.document()['inputs']
    context = inputs['context']
    profile = copy.deepcopy(inputs['profile'])
    vocabulary = profile['vocabulary']
    if vocabulary is not None:
        profile['vocabulary'] = {'identity': vocabulary,
            'raw_text': captured.raw(vocabulary['path']).decode('utf-8')}
    return GENERATION_CONTEXT_HEADER + canonical({
        'context': {'identity': context, 'raw_json': captured.raw(context['path']).decode('utf-8')},
        'profile': profile, 'source_manifest': inputs['source_manifest'],
        'scope': 'Caller-declared generation scope, source policy and vocabulary; '
                 'not a scientific applicability or support verdict.'}).decode('utf-8')


def require_generation_context(spec, messages) -> None:
    """Verify the complete selected block before any request is admitted."""
    from .usage_ledger import UsageLedgerError
    expected = generation_context(spec)
    blocks = [part for message in messages
              if message.get('role') == 'user' and isinstance(message.get('content'), list)
              for part in message['content'] if isinstance(part, dict)]
    selected = [block for block in blocks
                if isinstance(block.get('text'), str) and block['text'].startswith(GENERATION_CONTEXT_HEADER)]
    if selected != [{'type': 'text', 'text': expected}]:
        raise UsageLedgerError('actual shared request omits, changes or duplicates captured generation scope')


def schema_context(spec, record: str | None = None) -> str:
    """Actual induced keys plus complete occupied owners; no role inference.

    All mapping-valued schema owners are supplied, not a hand-maintained list
    of role names. The instruction asks for scientific relationship review.
    Software's induced keys are included for generation before values exist.
    """
    captured = assert_current(spec)
    return memo(spec, 'schema_context', [canonical(schema_pin(captured.full_schema)),
        *[raw for _name, _path, raw in captured.full_schema.sources],
        canonical(record)], lambda: _schema_context(captured, record))


def _schema_context(captured, record):
    from .schema_view import captured_view
    from .audit_omissions import _mapping
    from linkml_runtime.dumpers import json_dumper
    from .support_targets import _typed
    import yaml
    owners, classes = [], {}
    value = _mapping(record.encode("utf-8"), "whole record for role review") if record is not None else None
    with captured_view(captured.full_schema) as view:
        def describe(cls):
            if cls not in classes:
                if view.get_class(cls) is None:
                    raise ValueError(f"occupied schema owner has no class: {cls}")
                classes[cls] = {str(slot.name): json.loads(json_dumper.dumps(slot))
                                for slot in view.class_induced_slots(cls)}
            return classes[cls]
        describe('Dataset')
        if view.get_class('Software') is not None:
            describe('Software')
        pending = [(value, 'Dataset', '')] if value is not None else []
        while pending:
            item, cls, pointer = pending.pop()
            if not isinstance(item, dict):
                continue
            slots = describe(cls)
            owners.append({'path': pointer, 'class': cls,
                'whole_value_yaml': yaml.safe_dump(item, sort_keys=False, allow_unicode=True),
                'whole_value_identity': _typed(item)})
            for name, child in item.items():
                slot = slots.get(name)
                if slot is None or view.get_class(slot.get('range')) is None:
                    continue
                target = slot['range']
                child_pointer = pointer + '/' + name.replace('~', '~0').replace('/', '~1')
                if isinstance(child, list):
                    pending.extend((v, target, child_pointer + '/' + str(i)) for i, v in enumerate(child))
                elif isinstance(child, dict):
                    if slot.get('multivalued') and not slot.get('inlined_as_list'):
                        pending.extend((v, target, child_pointer + '/' + str(k).replace('~', '~0').replace('/', '~1'))
                                       for k, v in child.items())
                    else:
                        pending.append((child, target, child_pointer))
    return SCHEMA_CONTEXT_HEADER + canonical({'schema': schema_pin(captured.full_schema),
        'classes': classes, 'owners': owners,
        'scope': 'Actual schema structure and complete values; relationship support is an evaluator declaration.'}).decode('utf-8')


def require_client(spec, client):
    """Bind the actual adapter's declared endpoint, without reading a secret."""
    reg = capture(spec).document()
    endpoint = getattr(client, 'base_url', None)
    if endpoint is None or str(endpoint).rstrip('/') != reg['runtime']['base_url'].rstrip('/'):
        raise ValueError('actual client endpoint differs from registered route')


def plan(spec, settings):
    """No client or historical-output discovery; dynamic sizes remain unknown."""
    from . import api_runner as api
    captured = preflight(spec, settings)
    reg = captured.document()
    request = api.build_phase(spec, 'full', carry={})
    from .receipt_completion import PHASE as RECEIPT_PHASE
    from .typed_audit_runtime import WORKER_PHASE, OMISSION_PHASE, INTEGRATION_PHASE
    return {'project': spec.project, 'arm': spec.arm, 'method': spec.method, 'label': spec.label,
        'condition': spec.condition, 'runtime': spec.runtime, 'model': copy.deepcopy(settings),
        'bundle': str(spec.bundle), 'bundle_bytes': len(captured.raw(reg['inputs']['bundle']['path'])),
        'profile': spec.profile, 'profile_basis': spec.profile_basis,
        'api_playbook_version': 2, 'receipt_completion_version': 2, 'shared_generation_version': 1,
        'shared_generation_registration': captured.identity()['registration'],
        'prompt_files': [str(path) for path in spec.prompt_files],
        'schema_digest_md5': None,
        'phases': [{'phase': 'full', 'approx_input_tokens': request.approx_tokens(), 'carried': {},
                    'cached_blocks': len(request.cached_blocks)},
                   {'phase': 'typed_audit', 'approx_input_tokens': None, 'carried': 'actual originals and effective receipt',
                    'cached_blocks': 0}],
        'approx_total_input_tokens': None, 'full_request_approx_input_tokens': request.approx_tokens(),
        'registered_audit_allowances': copy.deepcopy(reg['audit_limits']),
        'estimate_basis': 'Only the actual full request has an approximate byte-derived count. Future record-dependent requests/roster are unknown; declared audit allowances are bounds, not measured tokens or prices.',
        'outputs': {'full': str(spec.full_path), 'core': str(spec.core_path), 'report': str(spec.report_path)},
        'conditional_calls': [f'{RECEIPT_PHASE}: receipt completion2 before core; exact explicit receipt cap and coverage floor',
                              f'{WORKER_PHASE}: every partition worker; count depends on the complete captured originals, no answer retries',
                              f'{OMISSION_PHASE}: one complete source-chunk omission pass; no answer retries',
                              f'{INTEGRATION_PHASE}: one integration of every worker and omission candidate; no answer retries',
                              'full_readdress: existing one-time full receipt-path correction',
                              'report_regate: existing one-time report disposition correction'],
        'readiness': {'software_protocol': NAME, 'native_direct': 'unsupported; separate adapter required',
                      'scientific_approval': 'unverified', 'campaign_launch': 'not authorized by a plan',
                      'coverage_floor': copy.deepcopy(reg['receipt']['coverage_floor'])}}


# Per-RunSpec pure derivations only. No admission, terminal or accounting state
# is stored here. Callers revalidate their live authority/pins before reuse.
MAX_MEMO_BYTES = 128_000_000
MAX_MEMO_ENTRIES = 32


def memo(spec, namespace, raw_parts, build):
    if any(type(raw) is not bytes for raw in raw_parts):
        raise TypeError('pure derivation keys require exact bytes')
    key = (namespace, tuple((len(raw), sha(raw)) for raw in raw_parts))
    cache = getattr(spec, '_shared_generation_derivations', None)
    if cache is None:
        cache = spec._shared_generation_derivations = {}
    if key in cache:
        return json.loads(cache[key])
    result = build()
    encoded = canonical(result)
    if len(encoded) <= MAX_MEMO_BYTES:
        while cache and (len(cache) >= MAX_MEMO_ENTRIES or sum(map(len, cache.values())) + len(encoded) > MAX_MEMO_BYTES):
            del cache[next(iter(cache))]
        cache[key] = encoded
    return json.loads(encoded)


def source_raw(spec):
    captured = assert_current(spec)
    pin = captured.document()['inputs']['source_manifest']
    return captured.raw(pin['path']) if pin else None


def source_registry(spec):
    from .registry import Registry
    from .typed_audit import _source_authority
    from .source_metadata import _Loader
    import yaml
    raw = source_raw(spec)
    if raw is None:
        return Registry(None, {})
    _source_authority(raw, spec.project)  # Bound aliases/nodes before construction.
    data = yaml.load(raw.decode('utf-8'), Loader=_Loader)
    if type(data) is not dict:
        raise ValueError('captured source manifest must be a mapping')
    return Registry(Path(spec.manifest), data)


def digest_text(spec, cls):
    from . import schema_digest
    captured = assert_current(spec)
    snapshot = captured.core_schema if cls == 'CoreDataset' else captured.full_schema
    pin = captured.document()['inputs']['profile']['vocabulary']
    vocabulary = captured.raw(pin['path']) if pin else b''
    return memo(spec, 'digest:' + cls,
        [canonical(schema_pin(snapshot)), *[raw for _name, _path, raw in snapshot.sources], vocabulary],
        lambda: schema_digest.render(schema_digest._build_cached(cls, snapshot.sources[0][1], snapshot),
            vocabulary=schema_digest.vocabularies(content=vocabulary, profile=spec.profile_obj)))


def marked_bundle(spec):
    from .audit_omissions import _mapping
    from .chunking import canonical_name, validate_manifest_mapping
    captured = assert_current(spec)
    inputs = captured.document()['inputs']
    raw = captured.raw(inputs['bundle']['path'])
    manifest = _mapping(captured.raw(inputs['chunk_manifest']['path']), 'captured chunk manifest')
    validate_manifest_mapping(manifest, raw, canonical_name(spec.bundle, source_manifest=spec.manifest))
    starts = {chunk['lines'][0]: chunk['id'] for chunk in manifest['chunks']}
    out = []
    for number, line in enumerate(raw.decode('utf-8', errors='ignore').split('\n'), 1):
        if number in starts:
            out.append(f'[{starts[number]}]')
        out.append(line)
    return '\n'.join(out), manifest['bundle_md5']


def core_inventory(spec):
    from .schema_view import captured_view
    captured = assert_current(spec)
    def build():
        with captured_view(captured.core_schema) as view:
            return [str(slot.name) for slot in view.class_induced_slots('CoreDataset')]
    return memo(spec, 'core_inventory', [canonical(schema_pin(captured.core_schema)),
        *[raw for _name, _path, raw in captured.core_schema.sources]], build)


def core_text(spec, *, phase4_complete=False):
    from . import derive_core as derive
    from .d4d_pair_consistency import pair_schema_from_views
    from .schema_view import captured_view
    from .audit_omissions import _mapping
    import yaml
    captured = assert_current(spec)
    raw = spec.full_path.read_bytes()
    full = _mapping(raw, 'full record to derive core')
    with captured_view(captured.full_schema) as full_view, captured_view(captured.core_schema) as core_view:
        pair = pair_schema_from_views(full_view, core_view)
        core = derive.derive_core(full, pair)
        facts = {'derived': True, 'rule': derive.RULE,
            'from': {'path': str(spec.full_path), 'md5': hashlib.md5(raw).hexdigest()},
            'identity_slots': len(pair.identity_slots), 'projected_slots': list(pair.projected_slots),
            'distribution_slots': derive._distribution_slots(pair), 'conditional': dict(derive.CONDITIONAL)}
    body = yaml.safe_dump(core, sort_keys=False, allow_unicode=True, width=88)
    header = '\n'.join(derive.core_header(raw.decode('utf-8'), spec.full_path, phase4_complete))
    return (header + '\n\n' if header else '') + body, facts


def source_chunks(spec):
    from .evidence_assertions import source_chunks_from_bytes
    captured = assert_current(spec)
    inputs = captured.document()['inputs']
    return source_chunks_from_bytes(captured.raw(inputs['bundle']['path']),
                                   captured.raw(inputs['chunk_manifest']['path']))
