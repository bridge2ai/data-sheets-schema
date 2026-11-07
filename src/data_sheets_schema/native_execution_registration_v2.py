"""Explicit v2 preparation and fail-closed execution admission (native U3-A).

The shared preparation producer consumes U1's real S/R captures. It is not the
historical direct preparer, and never wraps an unrelated execution dictionary
to make its schema look compatible. No function here reserves an attempt,
probes a runtime, invokes a launcher or contacts a provider.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
import re
import subprocess
import sys
import threading

from . import native_execution_authority_v2 as authority
from . import native_shared_contract as c
from . import native_shared_selection as selection
from .native_shared_evidence import read_regular
from .resources import git_env
# Reuse only pure runtime validation/fingerprinting. No legacy registration,
# verification, composition, loader or execution entrypoint is called.
from .native_execution_registration import validate_runtime, executable_identity

VERSION = 2
PREPARATION_KIND = 'd4d_native_shared_preparation_v2'
EXECUTION_KIND = 'd4d_native_shared_execution_registration_v2'
PREPARATION_SCOPE = 'offline_inputs_only_not_permission_or_launch_authority'
EXECUTION_SCOPE = 'requires_exact_independent_review_ci_permission_and_owner_launch_evidence'
MAX_WIRE_BYTES = c.HARD_LIMITS['request_bytes']
_COMMON_CHECKS = tuple('Python 3.12 / API case ' + name for name in (
    'routing-dispatch', 'routing-portable', 'routing-regate', 'routing-default-layout')) + tuple(
    'Python 3.12 / SG2 case ' + name for name in ('sg2-none', 'sg2-conventional', 'sg2-explicit')) + (
    'Python 3.12 / offline canary controls', 'Python 3.12 / offline audit and finalization',
    'Python 3.12 / offline evaluation', 'test')
EXECUTION_GATES = ('terminal', 'shutdown', 'first_stop', 'live_attribution',
    'saved_attribution', 'phase_history', 'tool_history', 'schema', 'pair',
    'receipts', 'evidence', 'observation', 'accounting', 'runtime_authority', 'keep_awake')
_PREPARATION_KEYS = frozenset(('kind', 'schema_version', 'execution', 'job_id',
    'working_directory', 'dependencies', 'selection', 'runtime', 'run_date',
    'max_draft_checks', 'render_spec', 'input_identity', 'instruction',
    'instruction_sha256', 'outputs', 'pinned_files'))


def required_checks(event):
    """Explicit current workflow profiles; a future roster needs review/tests."""
    if type(event) is not str or event not in ('pull_request', 'push', 'workflow_dispatch'):
        raise ValueError('CI workflow event must be pull_request, push or workflow_dispatch')
    pull = event == 'pull_request'
    return (tuple(f'Python 3.12 / shard {n}' for n in range(1, 9 if pull else 7))
            + _COMMON_CHECKS + (('large-files',) if pull else ('schema-examples (3.12)',)))


REQUIRED_CHECKS = required_checks('pull_request')


def _workflow_sha(source_commit):
    if type(source_commit) is not str or re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', source_commit) is None:
        raise ValueError('CI source commit must be an exact local Git object identity')
    relative = '.github/workflows/main.yaml'
    current = _read(str(authority.ROOT / relative), 'CI workflow', c.HARD_LIMITS['input_bytes'])
    try:
        committed = subprocess.run(['git', '--no-replace-objects', 'show', source_commit + ':' + relative],
            cwd=authority.ROOT, env=git_env(), capture_output=True, timeout=30, check=True).stdout
    except subprocess.CalledProcessError as exc:
        raise ValueError('CI workflow is absent from the named local source commit') from exc
    if committed != current.raw:
        raise ValueError('CI workflow differs from its exact source commit')
    return current.pin.sha256


def _read(path, label, maximum=MAX_WIRE_BYTES):
    return read_regular(str(path), label, max_bytes=maximum).captured


def _file_pin(artifact):
    return {'path': artifact.pin.path, 'bytes': artifact.pin.bytes, 'sha256': artifact.pin.sha256}


def _job_id(value):
    if type(value) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', value) is None:
        raise ValueError('job_id must be an explicit bounded single path component')


def _wire(raw):
    """Pinned U2 wire check precedes every inner-record or execution consumer."""
    value = c.strict_json(raw, 'v2 authority envelope', MAX_WIRE_BYTES)
    identity = authority.dependency_identity()
    with authority.loaded_dependencies(identity) as controls:
        inner = controls['prepare_registration_v2'].require_envelope(value)
    return inner, identity


def _envelope(body, dependencies):
    with authority.loaded_dependencies(dependencies) as controls:
        value = controls['prepare_registration_v2'].envelope(body)
        controls['prepare_registration_v2'].require_envelope(value)
    raw = c.canonical(value)
    if len(raw) > MAX_WIRE_BYTES:
        raise ValueError('v2 authority envelope exceeds its byte bound')
    return value


def _pin_map(captured, runtime, dependencies):
    """Complete selected inputs/assets and current package/helper sources."""
    pins = {}
    artifacts = (captured.registration, captured.receipt_policy, runtime,
                 *captured.authority, *(a for s in captured.schemas for a in s.sources))
    for artifact in artifacts:
        previous = pins.setdefault(artifact.pin.path, artifact.pin.sha256)
        if previous != artifact.pin.sha256:
            raise ValueError('one selected path has conflicting input identities')
    base = dependencies['base']
    for relative, digest in base['package_sources'].items():
        pins[str(authority.ROOT / relative)] = digest
    for pin in (*base['modules'].values(), *dependencies['additional_modules'].values()):
        path = str(authority.ROOT / pin['path'])
        if path in pins and pins[path] != pin['sha256']:
            raise ValueError('selected helper conflicts with another source pin')
        pins[path] = pin['sha256']
    return pins


def prepare(selection_path, runtime_path, *, job_id, run_date, max_draft_checks):
    """Prepare the explicit shared-native input contract; perform no writes.

    RunSpec boundary: guarded
    """
    from .api_runner import RunSpec, _require_registered_input_spellings
    _job_id(job_id)
    c.positive_int(max_draft_checks, 'maximum draft checks')
    if type(run_date) is not str or re.fullmatch(r'\d{4}-\d{2}-\d{2}', run_date) is None:
        raise ValueError('run_date must be an explicit ISO date')
    from datetime import date
    date.fromisoformat(run_date)
    if Path.cwd().resolve() != authority.ROOT:
        raise ValueError('v2 preparation requires its exact source checkout root')
    captured = selection.capture(selection_path)
    runtime_capture = _read(runtime_path, 'runtime_declaration', c.HARD_LIMITS['input_bytes'])
    runtime = validate_runtime(c.strict_json(runtime_capture.raw, 'runtime declaration'))
    doc = captured.document()
    inputs = doc['inputs']
    manifest = inputs['source_manifest']
    spec = RunSpec(**doc['run'], condition=c.CONDITION, render_version=c.RENDERER,
        bundle=Path(inputs['bundle']['path']), chunk_manifest=Path(inputs['chunk_manifest']['path']),
        manifest=None if manifest is None else Path(manifest['path']),
        profile=inputs['profile']['name'], profile_basis=inputs['profile']['basis'],
        runtime=c.RUNTIME, provider=runtime['provider'], reasoning_effort=runtime['effort'],
        prompt_text_env=True, run_date=run_date, native_shared_generation_version=1,
        native_shared_generation_registration=captured.registration.raw.decode('utf-8'))
    _require_registered_input_spellings(spec)
    spec._native_shared_runtime_capture = runtime_capture
    spec._native_shared_max_draft_checks = max_draft_checks
    instruction = spec.instruction
    dependencies = authority.dependency_identity()
    pins = _pin_map(captured, runtime_capture, dependencies)
    pins[runtime['executable']['path']] = runtime['executable']['sha256']
    body = {'kind': PREPARATION_KIND, 'schema_version': VERSION, 'execution': PREPARATION_SCOPE,
        'job_id': job_id, 'working_directory': str(authority.ROOT), 'dependencies': dependencies,
        'selection': _file_pin(captured.registration), 'runtime': _file_pin(runtime_capture),
        'run_date': run_date, 'max_draft_checks': max_draft_checks, 'render_spec': spec.render_spec(),
        'input_identity': spec.input_identity(), 'instruction': instruction,
        'instruction_sha256': c.sha(instruction.encode('utf-8')),
        'outputs': {name: str(Path(path).absolute()) for name, path in {
            'full': spec.full_path, 'core': spec.core_path, 'report': spec.report_path,
            'provenance': spec.provenance_path}.items()}, 'pinned_files': pins}
    # Re-read every selected member, not a saved passed flag. Source identity is
    # independently rechecked after rendering; source-commit proof is admission.
    if (selection.capture(selection_path) != captured
            or _read(runtime_path, 'runtime_declaration', c.HARD_LIMITS['input_bytes']) != runtime_capture
            or authority.dependency_identity() != dependencies):
        raise ValueError('v2 preparation authority changed during capture')
    return _envelope(body, dependencies)


def verify_preparer(raw, *, job_id):
    """Return a fresh rederived shared preparation, never a launch capability."""
    _job_id(job_id)
    body, dependencies = _wire(raw)
    c.exact(body, _PREPARATION_KEYS, 'shared-native v2 preparation')
    if (body['kind'] != PREPARATION_KIND or body['execution'] != PREPARATION_SCOPE
            or body['job_id'] != job_id):
        raise ValueError('not the selected shared-native v2 preparation')
    c.file_pin(body['selection'], 'selection pin')
    c.file_pin(body['runtime'], 'runtime pin')
    expected = prepare(body['selection']['path'], body['runtime']['path'], job_id=job_id,
                       run_date=body['run_date'], max_draft_checks=body['max_draft_checks'])
    if c.canonical(body) != c.canonical(expected['registration']):
        raise ValueError('v2 preparation differs from current pins, selection, runtime or rendering')
    if body['dependencies'] != dependencies:
        raise ValueError('v2 preparation source authority changed')
    return expected['registration']


def _consumer(dependencies):
    """Only the fixed U3-D consumer may complete execution-body validation.

    There is no callable/module supplied by an input, and no fallback to v1.
    Until that module implements this exact contract, admission refuses.
    """
    name = 'data_sheets_schema.native_shared_registration'
    relative = 'src/data_sheets_schema/native_shared_registration.py'
    expected = authority.ROOT / relative
    digest = dependencies['base']['package_sources'].get(relative)
    if digest is None:
        raise ValueError('v2 execution requires the committed U3-C/D shared composition and permission consumer')
    source = _read(str(expected), 'v2 execution consumer source', c.HARD_LIMITS['input_bytes'])
    if source.pin.sha256 != digest:
        raise ValueError('v2 execution consumer source differs from the committed package closure')
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name != name:
            raise
        raise ValueError('v2 execution requires the U3-C/D shared composition and permission consumer') from exc
    if (Path(getattr(module, '__file__', '')).resolve() != expected
            or type(getattr(module, 'AUTHORITY_VERSION', None)) is not int
            or module.AUTHORITY_VERSION != VERSION
            or not callable(getattr(module, 'verified_v2_body', None))
            or not callable(getattr(module, 'execution_paths_v2', None))):
        raise ValueError('v2 execution consumer has an unsupported interface or origin')
    return module


def verified(raw):
    """Reconstruct v2 E through its fixed consumer; no reservation or dispatch.

    C/D must check the full closed E, genuine C/policy/saved permission recipe,
    and original/effective receipt authority in verified_v2_body. Its return
    must be the same complete body, not a boolean or projected subset.
    """
    body, dependencies = _wire(raw)
    if (body.get('kind') != EXECUTION_KIND or body.get('execution') != EXECUTION_SCOPE
            or body.get('execution_gates') != list(EXECUTION_GATES)):
        raise ValueError('not the closed v2 shared execution route')
    try:
        preparation_raw = body['preparation_raw_json'].encode('utf-8')
        preparation = verify_preparer(preparation_raw, job_id=body['job_id'])
        if (body['preparation_sha256'] != c.sha(preparation_raw)
                or body['dependencies'] != dependencies
                or preparation['dependencies'] != dependencies):
            raise ValueError('execution differs from its prepared v2 source identity')
        runtime_capture = _read(preparation['runtime']['path'], 'runtime_declaration',
                                c.HARD_LIMITS['input_bytes'])
        if _file_pin(runtime_capture) != preparation['runtime']:
            raise ValueError('v2 prepared runtime changed before execution binding')
        runtime = c.strict_json(runtime_capture.raw)
        if (body['runtime'] != runtime
                or body['runtime_declaration_sha256'] != preparation['runtime']['sha256']
                or body['selection_sha256'] != preparation['selection']['sha256']
                or type(body['max_draft_checks']) is not int
                or body['max_draft_checks'] != preparation['max_draft_checks']
                or body['instruction_sha256'] != preparation['instruction_sha256']
                or body['working_directory'] != preparation['working_directory']):
            raise ValueError('execution runtime, budget or selected inputs differ from v2 preparation')
        composition_raw = body['composition_raw_json'].encode('utf-8')
        composition = c.strict_json(composition_raw, 'v2 shared composition', MAX_WIRE_BYTES)
        if (c.sha(composition_raw) != body['composition_sha256']
                or composition['render_spec'] != preparation['render_spec']
                or composition['instruction_sha256'] != preparation['instruction_sha256']
                or composition['selection_sha256'] != preparation['selection']['sha256']
                or composition['runtime_sha256'] != preparation['runtime']['sha256']):
            raise ValueError('composition differs from the exact v2 prepared rendering')
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('incomplete v2 shared execution binding') from exc
    authority.require_committed(dependencies)
    consumer = _consumer(dependencies)
    result = consumer.verified_v2_body(c.canonical(body), preparation_raw=preparation_raw)
    if c.canonical(result) != c.canonical(body):
        raise ValueError('v2 execution consumer did not reconstruct the complete registration')
    if authority.dependency_identity() != dependencies:
        raise ValueError('v2 execution authority changed during verification')
    return c.strict_json(c.canonical(result), 'verified v2 execution', MAX_WIRE_BYTES)


def _text(value, label):
    if type(value) is not str or not value.strip() or len(value) > 4096 or any(x in value for x in ('\0', '\r', '\n')):
        raise ValueError(label + ' must be explicit bounded single-line text')


def _authorizations(raw, value, *, review_path, ci_path, launch_word_path):
    paths = {'review': str(review_path), 'ci': str(ci_path), 'launch_word': str(launch_word_path)}
    captured = {key: _read(path, key + ' evidence') for key, path in paths.items()}
    records = {key: c.strict_json(item.raw, key + ' evidence') for key, item in captured.items()}
    binding = {'registration_sha256': c.sha(raw), 'attempt_id': value['attempt_id'],
        'source_commit': value['dependencies']['base']['source_commit'],
        'dependencies_sha256': c.sha(c.canonical(value['dependencies']))}
    for name, record in records.items():
        if (type(record) is not dict or type(record.get('version')) is not int
                or record['version'] != VERSION or any(record.get(k) != v for k, v in binding.items())):
            raise ValueError(name + ' must bind this exact v2 execution, attempt and source')
    review = records['review']
    c.exact(review, set(binding) | {'kind', 'version', 'reviewer', 'author', 'independent',
        'decision', 'reviewed_at', 'evidence'}, 'v2 independent review')
    if (review['kind'] != 'd4d_native_execution_review_v2' or review['independent'] is not True
            or review['decision'] != 'approved' or review['reviewer'] == review['author']):
        raise ValueError('explicit independent v2 approval is required')
    for key in ('reviewer', 'author', 'reviewed_at', 'evidence'):
        _text(review[key], key)
    ci = records['ci']
    c.exact(ci, set(binding) | {'kind', 'version', 'checks', 'workflow_event', 'workflow_sha256'}, 'v2 CI evidence')
    if (ci['kind'] != 'd4d_native_execution_ci_v2' or type(ci['checks']) is not dict
            or set(ci['checks']) != set(required_checks(ci['workflow_event']))
            or ci['workflow_sha256'] != _workflow_sha(binding['source_commit'])):
        raise ValueError('exact full v2 required CI evidence is missing')
    for row in ci['checks'].values():
        c.exact(row, {'head_sha', 'status', 'conclusion', 'details_url'}, 'v2 CI check')
        if (row['head_sha'] != binding['source_commit'] or row['status'] != 'completed'
                or row['conclusion'] != 'success' or type(row['details_url']) is not str
                or not row['details_url'].startswith('https://github.com/bridge2ai/data-sheets-schema/actions/')):
            raise ValueError('required CI is not successful at the exact v2 source')
    word = records['launch_word']
    c.exact(word, set(binding) | {'kind', 'version', 'owner', 'authorized_at', 'word',
        'review_sha256', 'ci_sha256', 'permission_probe_sha256'}, 'v2 owner evidence')
    if (word['kind'] != 'd4d_native_execution_launch_authorization_v2'
            or word['word'] != 'AUTHORIZE_ONE_NATIVE_ATTEMPT'
            or word['review_sha256'] != captured['review'].pin.sha256
            or word['ci_sha256'] != captured['ci'].pin.sha256
            or word['permission_probe_sha256'] != value['permission_probe_sha256']):
        raise ValueError('owner evidence does not authorize this exact v2 attempt')
    _text(word['owner'], 'owner')
    _text(word['authorized_at'], 'authorized_at')
    return captured


@dataclass(frozen=True)
class Admission:
    """Observation only; never a reusable launch capability or passed cache."""
    registration_raw: bytes
    evidence: tuple[c.CapturedArtifact, ...]


def admit(raw, *, review_path, ci_path, launch_word_path):
    """Fresh pre-effect checks. U3-D must call again immediately before effects."""
    value = verified(raw)
    evidence = _authorizations(raw, value, review_path=review_path, ci_path=ci_path,
                               launch_word_path=launch_word_path)
    runtime = validate_runtime(value['runtime'])
    if runtime['keep_awake']['host_platform'] != sys.platform:
        raise ValueError('v2 execution host differs from the registered host')
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('v2 execution admission requires the main thread')
    _consumer(value['dependencies']).execution_paths_v2(
        value, fresh=True, extra_protected=[x.pin.path for x in evidence.values()])
    # Admission is fresh on every call, including after a successful earlier
    # check. The future actuator owns durable reservation and one-use semantics.
    if verified(raw) != value:
        raise ValueError('v2 execution changed during admission')
    for role, item in evidence.items():
        if _read(item.pin.path, role + ' evidence') != item:
            raise ValueError('external v2 execution authority changed during admission')
    return Admission(raw, tuple(evidence[name] for name in ('review', 'ci', 'launch_word')))
