"""Explicit v2 preparation and fail-closed execution admission (native U3-A).

The shared preparation producer consumes U1's real S/R captures. It is not the
historical direct preparer, and never wraps an unrelated execution dictionary
to make its schema look compatible. No function here reserves an attempt,
probes a runtime, invokes a launcher or contacts a provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import inspect
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
from .native_execution_registration import validate_runtime

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
EXECUTION_KEYS = frozenset(('kind', 'schema_version', 'execution', 'attempt_id',
    'composition', 'system_path', 'permission_probe', 'attempt_directory',
    'evidence_directory', 'job_id', 'preparation_raw_json', 'preparation_sha256',
    'execution_gates', 'runtime', 'max_draft_checks', 'selection_sha256',
    'runtime_declaration_sha256', 'working_directory', 'dependencies',
    'composition_raw_json', 'composition_sha256', 'system_sha256',
    'effective_system', 'effective_system_sha256', 'instruction_sha256',
    'permission_probe_sha256', 'permission_expected_sha256',
    'permission_observations', 'argv', 'environment', 'selection', 'scope'))
_REBUILD_INPUTS = ('preparation_raw', 'composition_path', 'system_path',
    'permission_probe_path', 'attempt_id', 'attempt_directory',
    'evidence_directory', 'max_draft_checks', 'receipt_origin_version',
    'classifier_projection')


def required_checks(event):
    """Explicit current workflow profiles; a future roster needs review/tests."""
    if type(event) is not str or event not in ('pull_request', 'push', 'workflow_dispatch'):
        raise ValueError('CI workflow event must be pull_request, push or workflow_dispatch')
    pull = event == 'pull_request'
    return (tuple(f'Python 3.12 / shard {n}' for n in range(1, 9 if pull else 7))
            + _COMMON_CHECKS + (('large-files',) if pull else ('schema-examples (3.12)',)))


def _ci_git(*args, absent=False):
    """Read local CI identity without borrowed Git settings, hooks or network."""
    env = {key: value for key, value in git_env().items() if not key.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null',
               GIT_TERMINAL_PROMPT='0', GIT_ALLOW_PROTOCOL='')
    try:
        result = subprocess.run(['git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
            *args], cwd=authority.ROOT, env=env, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('local CI Git identity could not be read') from exc
    if absent and result.returncode == 1:
        return None
    if result.returncode != 0:
        raise ValueError('local CI Git object or configuration is unavailable')
    return result.stdout


def _ci_commit(commit, label):
    if type(commit) is not str or re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', commit) is None:
        raise ValueError(label + ' must be an exact local Git commit identity')
    if _ci_git('rev-parse', '--verify', commit + '^{commit}').decode('ascii').strip() != commit:
        raise ValueError(label + ' must name the exact commit object')


def _ci_tested_commit(source_commit, tested_commit, event, ref):
    """Bind declared CI to a source or a PR merge; no claim of remote authenticity."""
    required_checks(event)
    _ci_commit(source_commit, 'CI source commit')
    _ci_commit(tested_commit, 'CI tested commit')
    if type(ref) is not str or len(ref) > 512:
        raise ValueError('v2 CI workflow ref must be explicit bounded text')
    if event == 'pull_request':
        if re.fullmatch(r'refs/pull/[1-9][0-9]*/merge', ref) is None:
            raise ValueError('v2 PR CI requires the tested pull-request merge ref')
        parents = _ci_git('rev-list', '--parents', '-n', '1', tested_commit).decode('ascii').split()
        if len(parents) != 3 or parents[0] != tested_commit or parents[2] != source_commit:
            raise ValueError('v2 PR CI tested commit must merge the exact source as second parent')
    else:
        if tested_commit != source_commit:
            raise ValueError('v2 non-PR CI tested commit differs from source commit')
        if event == 'push' and ref != 'refs/heads/main':
            raise ValueError('v2 push CI requires refs/heads/main')
        if not ref.startswith('refs/heads/'):
            raise ValueError('v2 manual CI requires an explicit branch ref')
        _ci_git('check-ref-format', ref)


def _workflow_paths(event):
    required_checks(event)
    return ('.github/workflows/main.yaml',) + (
        ('.github/workflows/large-files.yaml',) if event == 'pull_request' else ())


def _workflow_sha(source_commit, tested_commit, event):
    """Pin every active workflow at both reviewed source and tested Git tree.

    A base-side workflow change in a PR merge requires a new reviewed source;
    its old fixed check roster cannot stand in for a different workflow.
    """
    result = {}
    for relative in _workflow_paths(event):
        current = _read(str(authority.ROOT / relative), 'CI workflow', c.HARD_LIMITS['input_bytes'])
        source = _ci_git('show', source_commit + ':' + relative)
        tested = _ci_git('show', tested_commit + ':' + relative)
        if source != current.raw:
            raise ValueError('CI workflow differs from its exact source commit')
        if tested != source:
            raise ValueError('CI tested workflow differs from reviewed source workflow')
        result[relative] = current.pin.sha256
    return result


def _ci_repository_url():
    """Canonical Actions repository from local d4d.ciRepositoryUrl or origin."""
    raw = _ci_git('config', '--local', '--get', 'd4d.ciRepositoryUrl', absent=True)
    if raw is None:
        raw = _ci_git('config', '--local', '--get', 'remote.origin.url', absent=True)
    if raw is None:
        raise ValueError('v2 CI requires local d4d.ciRepositoryUrl or origin')
    try:
        value = raw.decode('utf-8').rstrip('\n')
    except UnicodeDecodeError as exc:
        raise ValueError('v2 CI repository URL is not UTF-8') from exc
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)'
                         r'([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)', value)
    if match is None or match[1] in ('.', '..'):
        raise ValueError('v2 CI repository must be an explicit GitHub HTTPS or SSH origin')
    repository = match[2].removesuffix('.git')
    if repository in ('', '.', '..'):
        raise ValueError('v2 CI repository name is invalid')
    return 'https://github.com/' + match[1] + '/' + repository


def _read(path, label, maximum=MAX_WIRE_BYTES):
    return read_regular(str(path), label, max_bytes=maximum).captured


def _file_pin(artifact):
    return {'path': artifact.pin.path, 'bytes': artifact.pin.bytes, 'sha256': artifact.pin.sha256}


def _job_id(value):
    if type(value) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', value) is None:
        raise ValueError('job_id must be an explicit bounded single path component')


def _wire(raw):
    """Pure structural refusal precedes Git/imports; pinned U2 check follows."""
    value = c.strict_json(raw, 'v2 authority envelope', MAX_WIRE_BYTES)
    if (type(value) is not dict
            or set(value) != {'authority_version', 'controller_sources_sha256', 'registration'}
            or type(value['authority_version']) is not int or value['authority_version'] != VERSION
            or type(value['controller_sources_sha256']) is not str
            or value['controller_sources_sha256'] != authority.neutral.composition.SOURCES_SHA256
            or type(value['registration']) is not dict
            or type(value['registration'].get('schema_version')) is not int
            or value['registration']['schema_version'] != VERSION):
        raise ValueError('v2 launch requires an exact v2 authority envelope')
    identity = authority.dependency_identity()
    authority.require_committed(identity)
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


@contextmanager
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
    authority.refuse_legacy_consumer_imports(source.raw, name=name,
        package_sources=dependencies['base']['package_sources'])
    with authority.verified_source_module(name, path=expected, raw=source.raw, sha256=digest,
            package_sources=dependencies['base']['package_sources']) as module:
        identity = {'name': name, 'path': str(expected), 'sha256': digest}
        if authority.module_source_identity(module) != identity:
            raise ValueError('v2 execution consumer source identity mismatch')
        if (type(getattr(module, 'AUTHORITY_VERSION', None)) is not int
                or module.AUTHORITY_VERSION != VERSION):
            raise ValueError('v2 execution consumer authority version mismatch')
        _signature(module, 'rebuild_v2_body', (), _REBUILD_INPUTS)
        _signature(module, 'execution_paths_v2', ('body',), ('fresh', 'extra_protected'))
        yield module
        if authority.module_source_identity(module) != identity:
            raise ValueError('v2 execution consumer changed during verification')


def _signature(module, name, positional, keywords):
    function = getattr(module, name, None)
    if (not inspect.isfunction(function) or function.__module__ != module.__name__
            or hasattr(function, '__signature__')):
        raise ValueError('v2 execution consumer interface mismatch: ' + name)
    actual = tuple((p.name, p.kind, p.default) for p in
                   inspect.signature(function, follow_wrapped=False).parameters.values())
    expected = tuple((n, inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.empty)
                     for n in positional) + tuple(
        (n, inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.empty) for n in keywords)
    if actual != expected:
        raise ValueError('v2 execution consumer interface mismatch: ' + name)


def _closed_execution(body):
    if type(body) is not dict or set(body) not in (
            EXECUTION_KEYS, EXECUTION_KEYS | {'receipt_origin_reporting'}):
        raise ValueError('v2 execution body keys mismatch')
    if (body['kind'] != EXECUTION_KIND or type(body['schema_version']) is not int
            or body['schema_version'] != VERSION or body['execution'] != EXECUTION_SCOPE):
        raise ValueError('not the closed v2 shared execution route')
    if body['execution_gates'] != list(EXECUTION_GATES):
        raise ValueError('v2 execution gate obligations mismatch')


def _rebuild_inputs(body, preparation_raw):
    origin_version = 0
    if 'receipt_origin_reporting' in body:
        declaration = body['receipt_origin_reporting']
        if type(declaration) is not dict or type(declaration.get('version')) is not int or declaration['version'] != 1:
            raise ValueError('v2 receipt origin declaration version mismatch')
        origin_version = 1
    return dict(preparation_raw=preparation_raw, composition_path=body['composition'],
        system_path=body['system_path'], permission_probe_path=body['permission_probe'],
        attempt_id=body['attempt_id'], attempt_directory=body['attempt_directory'],
        evidence_directory=body['evidence_directory'], max_draft_checks=body['max_draft_checks'],
        receipt_origin_version=origin_version)


def verified(raw, *, classifier_projection):
    """Reconstruct v2 E through its fixed consumer; no reservation or dispatch.

    C/D must check the full closed E, genuine C/policy/saved permission recipe,
    and original/effective receipt authority from inputs only. The submitted
    body's derived fields are never passed to the reconstruction consumer.
    The live classifier projection is forwarded unchanged; C owns its validation.
    """
    if classifier_projection is None:
        raise ValueError('v2 execution requires an explicit classifier projection')
    body, dependencies = _wire(raw)
    _closed_execution(body)
    try:
        preparation_raw = body['preparation_raw_json'].encode('utf-8')
        preparation = verify_preparer(preparation_raw, job_id=body['job_id'])
        if body['preparation_sha256'] != c.sha(preparation_raw):
            raise ValueError('v2 preparation digest mismatch')
        if body['dependencies'] != dependencies or preparation['dependencies'] != dependencies:
            raise ValueError('v2 dependency identity mismatch')
        runtime_capture = _read(preparation['runtime']['path'], 'runtime_declaration',
                                c.HARD_LIMITS['input_bytes'])
        if _file_pin(runtime_capture) != preparation['runtime']:
            raise ValueError('v2 prepared runtime changed before execution binding')
        runtime = c.strict_json(runtime_capture.raw)
        expected = {'runtime': runtime,
            'runtime_declaration_sha256': preparation['runtime']['sha256'],
            'selection_sha256': preparation['selection']['sha256'],
            'max_draft_checks': preparation['max_draft_checks'],
            'instruction_sha256': preparation['instruction_sha256'],
            'working_directory': preparation['working_directory']}
        for key, wanted in expected.items():
            if c.canonical(body[key]) != c.canonical(wanted):
                raise ValueError('v2 execution ' + key + ' mismatch')
        composition_raw = body['composition_raw_json'].encode('utf-8')
        composition = c.strict_json(composition_raw, 'v2 shared composition', MAX_WIRE_BYTES)
        if c.sha(composition_raw) != body['composition_sha256']:
            raise ValueError('v2 composition digest mismatch')
        expected = {'render_spec': preparation['render_spec'],
            'instruction_sha256': preparation['instruction_sha256'],
            'selection_sha256': preparation['selection']['sha256'],
            'runtime_sha256': preparation['runtime']['sha256']}
        for key, wanted in expected.items():
            if c.canonical(composition[key]) != c.canonical(wanted):
                raise ValueError('v2 composition ' + key + ' mismatch')
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('incomplete v2 shared execution binding') from exc
    authority.require_committed(dependencies)
    with _consumer(dependencies) as consumer:
        result = consumer.rebuild_v2_body(**_rebuild_inputs(body, preparation_raw),
                                         classifier_projection=classifier_projection)
    _closed_execution(result)
    if c.canonical(result) != c.canonical(body):
        raise ValueError('v2 execution consumer did not reconstruct the complete registration')
    if authority.dependency_identity() != dependencies:
        raise ValueError('v2 execution authority changed during verification')
    return c.strict_json(c.canonical(result), 'verified v2 execution', MAX_WIRE_BYTES)


def _text(value, label):
    if (type(value) is not str or not value or value != value.strip() or len(value) > 4096
            or any(x in value for x in ('\0', '\r', '\n'))):
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
    if review['kind'] != 'd4d_native_execution_review_v2':
        raise ValueError('v2 review kind is not independent review evidence')
    for key in ('reviewer', 'author', 'reviewed_at', 'evidence'):
        _text(review[key], key)
    pass  # MB: deliberately removed refusal
    if review['decision'] != 'approved':
        raise ValueError('v2 review decision must be approved')
    if review['reviewer'] == review['author']:
        raise ValueError('v2 review cannot approve its own author')
    ci = records['ci']
    c.exact(ci, set(binding) | {'kind', 'version', 'checks', 'workflow_event', 'workflow_ref',
        'workflow_sha256', 'tested_commit'}, 'v2 CI evidence')
    if ci['kind'] != 'd4d_native_execution_ci_v2':
        raise ValueError('v2 CI kind is not CI evidence')
    if type(ci['checks']) is not dict or set(ci['checks']) != set(required_checks(ci['workflow_event'])):
        raise ValueError('v2 CI check roster differs from the exact required event roster')
    _ci_tested_commit(binding['source_commit'], ci['tested_commit'], ci['workflow_event'], ci['workflow_ref'])
    if (type(ci['workflow_sha256']) is not dict
            or ci['workflow_sha256'] != _workflow_sha(
                binding['source_commit'], ci['tested_commit'], ci['workflow_event'])):
        raise ValueError('v2 CI workflow map differs from exact reviewed and tested workflow bytes')
    action_url = re.escape(_ci_repository_url()) + r'/actions/runs/[1-9][0-9]*(?:/job/[1-9][0-9]*)?'
    for row in ci['checks'].values():
        c.exact(row, {'head_sha', 'status', 'conclusion', 'details_url'}, 'v2 CI check')
        if row['head_sha'] != binding['source_commit']:
            raise ValueError('v2 CI check source differs from source commit')
        if row['status'] != 'completed':
            raise ValueError('v2 CI check status must be completed')
        if row['conclusion'] != 'success':
            raise ValueError('v2 CI check conclusion must be success')
        if type(row['details_url']) is not str or re.fullmatch(action_url, row['details_url']) is None:
            raise ValueError('v2 CI check URL differs from the configured repository Actions run')
    word = records['launch_word']
    c.exact(word, set(binding) | {'kind', 'version', 'owner', 'authorized_at', 'word',
        'review_sha256', 'ci_sha256', 'permission_probe_sha256'}, 'v2 owner evidence')
    if word['kind'] != 'd4d_native_execution_launch_authorization_v2':
        raise ValueError('v2 owner kind is not launch authorization evidence')
    if word['word'] != 'AUTHORIZE_ONE_NATIVE_ATTEMPT':
        raise ValueError('v2 owner word must authorize exactly one native attempt')
    if word['review_sha256'] != captured['review'].pin.sha256:
        raise ValueError('v2 owner review hash differs')
    if word['ci_sha256'] != captured['ci'].pin.sha256:
        raise ValueError('v2 owner CI hash differs')
    if word['permission_probe_sha256'] != value['permission_probe_sha256']:
        raise ValueError('v2 owner permission probe hash differs')
    _text(word['owner'], 'owner')
    _text(word['authorized_at'], 'authorized_at')
    return captured


@dataclass(frozen=True)
class Admission:
    """Observation only; never a reusable launch capability or passed cache."""
    registration_raw: bytes
    evidence: tuple[c.CapturedArtifact, ...]
    reservations: tuple[Path, ...]


def _checked_reservations(result, value, evidence):
    """Consume the consumer's typed path result against independently captured S."""
    prep = verify_preparer(value['preparation_raw_json'].encode('utf-8'), job_id=value['job_id'])
    captured_selection = _read(prep['selection']['path'], 'selected path authority')
    if _file_pin(captured_selection) != prep['selection']:
        raise ValueError('v2 selected path authority changed after preparation')
    selected = c.parse_selection(captured_selection.raw)
    expected = {Path(value['attempt_directory']), Path(value['evidence_directory']),
                Path(selected['stage_root'])}
    expected.update(Path(path).parent for path in prep['outputs'].values())
    if (type(result) is not list or not result or any(not isinstance(p, Path) for p in result)
            or len(set(result)) != len(result) or set(result) != expected):
        raise ValueError('v2 execution reservation result mismatch')
    protected = {Path(path) for path in prep['pinned_files']}
    protected.update(Path(value[k]) for k in ('composition', 'system_path', 'permission_probe'))
    protected.update(Path(item.pin.path) for item in evidence.values())
    protected.update(authority.ROOT / p for p in
                     ('src', 'notes', 'scripts', 'tests', 'project', '.git', '.github', '.claude'))
    for path in result:
        if not path.is_absolute() or path != path.resolve() or path.exists() or path.is_symlink():
            raise ValueError('v2 execution reservations must be canonical and unspent')
        for other in protected | (expected - {path}):
            other = other.resolve()
            if path == other or path in other.parents or other in path.parents:
                raise ValueError('v2 execution reservations overlap protected paths')
    for key in ('attempt_directory', 'evidence_directory'):
        if not Path(value[key]).parent.is_dir():
            raise ValueError('v2 execution reservation parents must exist')
    return tuple(sorted(result))


def admit(raw, *, review_path, ci_path, launch_word_path, classifier_projection):
    """Fresh pre-effect checks. U3-D must call again immediately before effects."""
    if classifier_projection is None:
        raise ValueError('v2 execution requires an explicit classifier projection')
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('v2 execution admission requires the main thread')
    value = verified(raw, classifier_projection=classifier_projection)
    evidence = _authorizations(raw, value, review_path=review_path, ci_path=ci_path,
                               launch_word_path=launch_word_path)
    runtime = validate_runtime(value['runtime'])
    if runtime['keep_awake']['host_platform'] != sys.platform:
        raise ValueError('v2 execution host differs from the registered host')
    with _consumer(value['dependencies']) as consumer:
        result = consumer.execution_paths_v2(
            c.strict_json(c.canonical(value)), fresh=True,
            extra_protected=tuple(x.pin.path for x in evidence.values()))
    reservations = _checked_reservations(result, value, evidence)
    # Admission is fresh on every call, including after a successful earlier
    # check. The future actuator owns durable reservation and one-use semantics.
    if verified(raw, classifier_projection=classifier_projection) != value:
        raise ValueError('v2 execution changed during admission')
    for role, item in evidence.items():
        if _read(item.pin.path, role + ' evidence') != item:
            raise ValueError('external v2 execution authority changed during admission')
    return Admission(raw, tuple(evidence[name] for name in ('review', 'ci', 'launch_word')), reservations)
