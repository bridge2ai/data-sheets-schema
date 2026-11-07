"""U3-A preparation/admission boundaries; offline synthetic inputs, 2026-11-07.

Positive preparation uses the real U1 selection/render path and pinned loader.
The fingerprint-only executable is never run. Fabricated E/C prefixes and
approval evidence below are rejection/unit fixtures, not execution acceptance.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest

from data_sheets_schema import native_attribution_controller_v2 as controller
from data_sheets_schema import native_execution_registration as legacy
from data_sheets_schema import native_execution_registration_v2 as registration
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_selection as selection
from tests.test_native_shared_selection import declaration
from tests.test_native_shared_render import native_spec


@pytest.fixture
def isolated_modules():
    """Explicit test isolation; production must refuse existing foreign aliases."""
    authority = registration.authority
    manifest = json.loads((authority.ROOT / controller.SOURCES_PATH).read_bytes())
    names = set(manifest['modules']) | set(authority.neutral.ADDITIONAL) | set(authority.ADDITIONAL)
    absent = object()
    previous = {name: sys.modules.pop(name, absent) for name in names}
    old_path = list(sys.path)
    try:
        yield names
    finally:
        sys.path[:] = old_path
        for name, module in previous.items():
            sys.modules.pop(name, None)
            if module is not absent:
                sys.modules[name] = module


@pytest.fixture
def inputs(native_spec, isolated_modules, tmp_path, monkeypatch):
    """A real captured S plus an R accepted by unpatched runtime validation."""
    monkeypatch.chdir(registration.authority.ROOT)
    executable = tmp_path.resolve() / 'fingerprint-only-not-a-native-program'
    executable.write_bytes(b'Fingerprint-only test fixture. Not an executable program.\n')
    executable.chmod(0o700)
    runtime = c.strict_json(native_spec._native_shared_runtime_capture.raw)
    runtime['executable'].update(path=str(executable), sha256=c.sha(executable.read_bytes()))
    runtime['auth'] = {'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
        'subscriptionType': 'synthetic-software-test', 'expected_api_key_source': 'none'}
    runtime['environment'] = {'PATH': '/usr/bin:/bin', 'HOME': str(tmp_path.resolve()),
        'CLAUDE_SECURESTORAGE_CONFIG_DIR': '', 'CLAUDE_CODE_DISABLE_1M_CONTEXT': '1'}
    runtime['keep_awake']['host_platform'] = sys.platform
    runtime_path = Path(native_spec._native_shared_runtime_capture.pin.path)
    runtime_path.write_bytes(c.canonical(runtime))
    source = native_spec._native_shared_generation_capture
    if source is None:
        source = selection.capture(c.strict_json(
            native_spec.native_shared_generation_registration.encode())['registration_path'])
    selection_path = Path(source.registration.pin.path)
    calls = []
    original = subprocess.Popen

    def local_git_only(argv, *args, **kwargs):
        assert not kwargs.get('shell'), 'preparation must not launch a shell'
        assert isinstance(argv, (list, tuple)) and Path(argv[0]).name == 'git', (
            'preparation must not execute a native, auth, provider or other child')
        calls.append(tuple(argv))
        return original(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, 'Popen', local_git_only)
    return {'spec': native_spec, 'selection': selection_path, 'runtime_path': runtime_path,
        'runtime': runtime, 'executable': executable, 'root': tmp_path.resolve(), 'calls': calls,
        'kwargs': {'job_id': 'synthetic_native_rep1', 'run_date': '2026-11-07', 'max_draft_checks': 2}}


def _files(root):
    return {str(path.relative_to(root)): c.sha(path.read_bytes())
            for path in root.rglob('*') if path.is_file()}


def _entries(root):
    """Retain empty directories and links as well as regular-file names."""
    return {(str(path.relative_to(root)),
             'symlink' if path.is_symlink() else 'directory' if path.is_dir()
             else 'file' if path.is_file() else 'other')
            for path in root.rglob('*')}


def _prepare(inputs):
    return registration.prepare(inputs['selection'], inputs['runtime_path'], **inputs['kwargs'])


@pytest.fixture
def prepared(inputs):
    return inputs, _prepare(inputs)


def test_prepare_rederives_real_native26_and_all_pins_without_effects(inputs, isolated_modules):
    before = _files(inputs['root'])
    old_path = list(sys.path)
    envelope = _prepare(inputs)
    body = envelope['registration']
    assert envelope['authority_version'] == 2
    assert envelope['controller_sources_sha256'] == controller.SOURCES_SHA256
    assert body['kind'] == 'd4d_native_shared_preparation_v2'
    assert body['execution'] == 'offline_inputs_only_not_permission_or_launch_authority'
    assert body['render_spec']['render_version'] == 26
    assert body['render_spec']['native_shared_generation_version'] == 1
    assert body['instruction_sha256'] == c.sha(body['instruction'].encode())
    assert '# Model: synthetic-native-model' in body['instruction']
    assert 'Registered maximum draft checks: 2.' in body['instruction']
    assert 'native_shared_stage advance --registration' in body['instruction']
    assert body['selection']['path'] == str(inputs['selection'])
    assert body['runtime']['path'] == str(inputs['runtime_path'])
    assert body['runtime']['sha256'] == c.sha(inputs['runtime_path'].read_bytes())
    assert body['input_identity']
    assert set(body['outputs']) == {'full', 'core', 'report', 'provenance'}
    assert all(Path(path).is_absolute() for path in body['outputs'].values())
    captured = selection.capture(inputs['selection'])
    required = {a.pin.path for a in (captured.registration, captured.receipt_policy,
        *captured.authority, *(a for s in captured.schemas for a in s.sources))}
    required.update({str(inputs['runtime_path']), str(inputs['executable'])})
    required.update(str(registration.authority.ROOT / path)
                    for path in body['dependencies']['base']['package_sources'])
    assert required <= set(body['pinned_files'])
    for path, digest in body['pinned_files'].items():
        assert c.sha(Path(path).read_bytes()) == digest
    raw = c.canonical(envelope)
    assert registration.verify_preparer(raw, job_id=body['job_id']) == body
    assert _files(inputs['root']) == before
    assert not Path(captured.document()['stage_root']).exists()
    assert sys.path == old_path
    assert not isolated_modules.intersection(sys.modules)
    assert all(Path(call[0]).name == 'git' for call in inputs['calls'])


@pytest.mark.parametrize('mutation', ['v1', 'bool', 'text', 'digest', 'extra', 'missing',
                                     'inner_v1', 'inner_bool', 'nonobject'])
def test_bad_authority_envelope_refuses_before_input_capture(isolated_modules, monkeypatch, mutation):
    value = {'authority_version': 2, 'controller_sources_sha256': controller.SOURCES_SHA256,
             'registration': {'schema_version': 2}}
    if mutation == 'v1': value['authority_version'] = 1
    elif mutation == 'bool': value['authority_version'] = True
    elif mutation == 'text': value['authority_version'] = '2'
    elif mutation == 'digest': value['controller_sources_sha256'] = '0' * 64
    elif mutation == 'extra': value['unexpected'] = True
    elif mutation == 'missing': del value['authority_version']
    elif mutation == 'inner_v1': value['registration']['schema_version'] = 1
    elif mutation == 'inner_bool': value['registration']['schema_version'] = True
    else: value = []
    monkeypatch.setattr(selection, 'capture', lambda *a, **k: pytest.fail('invalid envelope reached S'))
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('invalid envelope spawned a process'))
    monkeypatch.setattr(registration.authority, 'loaded_dependencies',
                        lambda *a, **k: pytest.fail('invalid envelope compiled or loaded helpers'))
    with pytest.raises(ValueError, match='v2 authority envelope'):
        registration.verify_preparer(c.canonical(value), job_id='synthetic')


def test_duplicate_json_refuses_before_dependency_loading(monkeypatch):
    monkeypatch.setattr(registration.authority, 'dependency_identity',
                        lambda: pytest.fail('duplicate wire reached authority loading'))
    with pytest.raises(ValueError, match='duplicate'):
        registration.verify_preparer(b'{"authority_version":2,"authority_version":2}', job_id='synthetic')


@pytest.mark.parametrize('mutation', ['extra', 'kind', 'job', 'selection_pin', 'runtime_pin',
    'code_pin', 'missing_pin', 'render', 'instruction', 'input_identity', 'outputs', 'draft_bool'])
def test_current_preparation_rejects_tampered_contract(prepared, mutation):
    inputs, value = prepared
    value = deepcopy(value)
    body = value['registration']
    if mutation == 'extra': body['acceptance'] = True
    elif mutation == 'kind': body['kind'] = 'd4d_direct_arm_registration_v2'
    elif mutation == 'job': body['job_id'] = 'foreign'
    elif mutation == 'selection_pin': body['selection']['sha256'] = '0' * 64
    elif mutation == 'runtime_pin': body['runtime']['sha256'] = '0' * 64
    elif mutation == 'code_pin':
        path = str(registration.authority.ROOT / 'src/data_sheets_schema/api_runner.py')
        body['pinned_files'][path] = '0' * 64
    elif mutation == 'missing_pin': del body['pinned_files'][str(inputs['selection'])]
    elif mutation == 'render': body['render_spec']['reasoning_effort'] = 'low'
    elif mutation == 'instruction':
        body['instruction'] += '\nForeign directive.\n'
        body['instruction_sha256'] = c.sha(body['instruction'].encode())
    elif mutation == 'input_identity': body['input_identity'] = {'substituted': True}
    elif mutation == 'outputs': body['outputs']['full'] = str(inputs['root'] / 'foreign.yaml')
    else: body['max_draft_checks'] = True
    before = _files(inputs['root'])
    with pytest.raises(ValueError):
        registration.verify_preparer(c.canonical(value), job_id=inputs['kwargs']['job_id'])
    assert _files(inputs['root']) == before


@pytest.mark.parametrize('changed', ['source', 'selection', 'runtime', 'executable'])
def test_preparation_does_not_cache_admission_after_live_drift(prepared, changed):
    inputs, envelope = prepared
    raw = c.canonical(envelope)
    body = registration.verify_preparer(raw, job_id=inputs['kwargs']['job_id'])
    if changed == 'source':
        document = c.strict_json(inputs['selection'].read_bytes())
        path = Path(document['inputs']['bundle']['path'])
        path.write_bytes(path.read_bytes() + b'Changed source.\n')
    elif changed == 'selection':
        document = c.strict_json(inputs['selection'].read_bytes())
        document['run']['label'] = 'different-registered-label'
        inputs['selection'].write_bytes(c.canonical(document))
    elif changed == 'runtime':
        runtime = deepcopy(inputs['runtime'])
        runtime['model'] = 'different-explicit-model'
        inputs['runtime_path'].write_bytes(c.canonical(runtime))
    else:
        inputs['executable'].write_bytes(b'Changed executable fingerprint.\n')
    before = _files(inputs['root'])
    with pytest.raises(ValueError):
        registration.verify_preparer(raw, job_id=body['job_id'])
    assert _files(inputs['root']) == before


def test_v1_execution_and_v2_envelope_cross_refuse(prepared):
    inputs, envelope = prepared
    before_files, before_entries = _files(inputs['root']), _entries(inputs['root'])
    v1 = {'kind': legacy.KIND, 'version': 1, 'execution': legacy.EXECUTION}
    with pytest.raises(ValueError, match='v2 authority envelope'):
        registration.verified(c.canonical(v1))
    with pytest.raises(ValueError, match='not a supported explicit native execution registration'):
        legacy.verified(c.canonical(envelope))
    # A genuine preparation is still not a complete execution registration.
    with pytest.raises(ValueError, match='v2 execution body keys mismatch'):
        registration.admit(c.canonical(envelope), review_path=inputs['root'] / 'absent-review',
            ci_path=inputs['root'] / 'absent-ci', launch_word_path=inputs['root'] / 'absent-owner')
    assert _files(inputs['root']) == before_files
    assert _entries(inputs['root']) == before_entries
    assert all(not Path(path).exists() for path in envelope['registration']['outputs'].values())


def test_complete_valid_v1_execution_refused_by_v2_without_reservation(
        isolated_modules, tmp_path, monkeypatch):
    """Actual v1 registration verification first; no native/runtime invocation."""
    from tests.test_native_execution import make_native_case

    monkeypatch.chdir(registration.authority.ROOT)
    v1_manifest = json.loads((legacy.authority.ROOT / legacy.composition.SOURCES_PATH).read_bytes())
    names = (set(isolated_modules) | set(v1_manifest['modules'])
             | set(legacy.authority.neutral.ADDITIONAL) | set(legacy.authority.ADDITIONAL))
    absent = object()
    previous = {name: sys.modules.pop(name, absent) for name in names}
    old_path = list(sys.path)
    original = subprocess.Popen
    calls = []

    def local_git_only(argv, *args, **kwargs):
        assert not kwargs.get('shell'), 'cross-version verification must not launch a shell'
        assert isinstance(argv, (list, tuple)) and Path(argv[0]).name == 'git', (
            'cross-version verification must not invoke the synthetic CLI, native, auth or provider')
        calls.append(tuple(argv))
        return original(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, 'Popen', local_git_only)
    try:
        case = make_native_case(tmp_path.resolve() / 'complete-v1')
        assert legacy.verified(case['raw']) == case['value']
        reservations = [Path(case['value'][name])
                        for name in ('attempt_directory', 'evidence_directory')]
        assert all(not path.exists() and not path.is_symlink() for path in reservations)
        before_files, before_entries = _files(tmp_path), _entries(tmp_path)
        assert sys.path == old_path

        # The successful v1 constructor loads its frozen bare aliases. This is
        # test-owned isolation, not a production fallback that hides origins.
        # The following refusal must be the actual wire/version boundary.
        for name in names:
            sys.modules.pop(name, None)
        with pytest.raises(ValueError, match='v2 launch requires an exact v2 authority envelope'):
            registration.verified(case['raw'])
        assert _files(tmp_path) == before_files
        assert _entries(tmp_path) == before_entries
        with pytest.raises(ValueError, match='v2 launch requires an exact v2 authority envelope'):
            registration.admit(case['raw'], **case['kwargs'])
        assert _files(tmp_path) == before_files
        assert _entries(tmp_path) == before_entries
        assert all(not path.exists() and not path.is_symlink() for path in reservations)
        assert sys.path == old_path
        assert not names.intersection(sys.modules)
        assert calls and all(Path(call[0]).name == 'git' for call in calls)
    finally:
        sys.path[:] = old_path
        for name, module in previous.items():
            sys.modules.pop(name, None)
            if module is not absent:
                sys.modules[name] = module


def _execution_prefix(inputs, preparation):
    """Closed-shape synthetic joins, deliberately no real C/permission proof."""
    prepared_raw = c.canonical(preparation)
    body = preparation['registration']
    composition = {'render_spec': body['render_spec'],
        'instruction_sha256': body['instruction_sha256'],
        'selection_sha256': body['selection']['sha256'], 'runtime_sha256': body['runtime']['sha256']}
    composition_raw = c.canonical(composition)
    return {'authority_version': 2, 'controller_sources_sha256': controller.SOURCES_SHA256,
        'registration': {'kind': registration.EXECUTION_KIND, 'schema_version': 2,
            'execution': registration.EXECUTION_SCOPE, 'execution_gates': list(registration.EXECUTION_GATES),
            'preparation_raw_json': prepared_raw.decode(), 'preparation_sha256': c.sha(prepared_raw),
            'job_id': body['job_id'], 'dependencies': body['dependencies'],
            'runtime': inputs['runtime'], 'runtime_declaration_sha256': body['runtime']['sha256'],
            'selection_sha256': body['selection']['sha256'], 'max_draft_checks': body['max_draft_checks'],
            'instruction_sha256': body['instruction_sha256'], 'working_directory': body['working_directory'],
            'composition_raw_json': composition_raw.decode(), 'composition_sha256': c.sha(composition_raw),
            'attempt_id': 'synthetic-attempt',
            'composition': str(inputs['root'] / 'synthetic-composition.json'),
            'system_path': str(inputs['root'] / 'synthetic-system.md'),
            'permission_probe': str(inputs['root'] / 'synthetic-permission.json'),
            'attempt_directory': str(inputs['root'] / 'synthetic-attempt'),
            'evidence_directory': str(inputs['root'] / 'synthetic-evidence'),
            'system_sha256': 'a' * 64, 'effective_system': 'Synthetic test only.',
            'effective_system_sha256': c.sha(b'Synthetic test only.'),
            'permission_probe_sha256': 'b' * 64, 'permission_expected_sha256': 'c' * 64,
            'permission_observations': {'synthetic': True}, 'argv': ['not-executed'],
            'environment': {}, 'selection': {'synthetic': True},
            'scope': 'Fabricated bridge test, never a C/D or admission verdict.'}}


def test_v1_refuses_v2_execution_envelope_and_inner_join_prefix(prepared):
    """Wire rejection only: this prefix lacks the real U3-C/D C/permission proof."""
    inputs, preparation = prepared
    envelope = _execution_prefix(inputs, preparation)
    assert envelope['registration']['kind'] == registration.EXECUTION_KIND
    assert envelope['registration']['schema_version'] == 2
    before_files, before_entries = _files(inputs['root']), _entries(inputs['root'])
    for value in (envelope, envelope['registration']):
        with pytest.raises(ValueError, match='not a supported explicit native execution registration'):
            legacy.verified(c.canonical(value))
        assert _files(inputs['root']) == before_files
        assert _entries(inputs['root']) == before_entries
    assert not Path(selection.capture(inputs['selection']).document()['stage_root']).exists()


def test_execution_prefix_refuses_until_fixed_shared_consumer_exists(prepared, monkeypatch):
    inputs, preparation = prepared
    envelope = _execution_prefix(inputs, preparation)
    before = _files(inputs['root'])
    actual_consumer = registration._consumer
    def missing_consumer(dependencies):
        # D now installs the consumer. Inject its absence only at this refusal
        # boundary, after genuine outer/preparation/source validation, rather
        # than assuming the current package must permanently lack the module.
        missing = deepcopy(dependencies)
        missing['base']['package_sources'].pop(
            'src/data_sheets_schema/native_shared_registration.py', None)
        return actual_consumer(missing)
    monkeypatch.setattr(registration, '_consumer', missing_consumer)
    monkeypatch.delitem(sys.modules, 'data_sheets_schema.native_shared_registration', raising=False)
    with pytest.raises(ValueError, match='requires the committed U3-C/D shared composition and permission consumer'):
        registration.verified(c.canonical(envelope))
    assert _files(inputs['root']) == before


def test_runtime_changed_after_preparer_verification_refuses_before_consumer(prepared, monkeypatch):
    """R1: do not bind new R bytes to the previously verified R pin."""
    inputs, preparation = prepared
    envelope = _execution_prefix(inputs, preparation)
    changed_runtime = deepcopy(inputs['runtime'])
    changed_runtime['model'] = 'different-late-runtime'
    envelope['registration']['runtime'] = changed_runtime
    actual_verify = registration.verify_preparer
    visits = []

    def verify_then_change(raw, *, job_id):
        result = actual_verify(raw, job_id=job_id)
        visits.append(job_id)
        inputs['runtime_path'].write_bytes(c.canonical(changed_runtime))
        return result

    monkeypatch.setattr(registration, 'verify_preparer', verify_then_change)
    monkeypatch.setattr(registration, '_consumer',
                        lambda *a: pytest.fail('changed R reached execution consumer'))
    with pytest.raises(ValueError, match='prepared runtime changed before execution binding'):
        registration.verified(c.canonical(envelope))
    assert visits == [inputs['kwargs']['job_id']]


def test_same_origin_module_cannot_substitute_for_absent_committed_consumer(prepared, monkeypatch):
    """R2: a same-origin sys.modules stand-in is not committed source proof."""
    inputs, preparation = prepared
    relative = 'src/data_sheets_schema/native_shared_registration.py'
    dependencies = deepcopy(preparation['registration']['dependencies'])
    dependencies['base']['package_sources'].pop(relative, None)
    assert relative not in dependencies['base']['package_sources']
    module = ModuleType('data_sheets_schema.native_shared_registration')
    module.__file__ = str(registration.authority.ROOT / relative)
    module.AUTHORITY_VERSION = 2
    module.verified_v2_body = lambda *a, **k: pytest.fail('uncommitted consumer called')
    module.execution_paths_v2 = lambda *a, **k: pytest.fail('uncommitted path consumer called')
    monkeypatch.setitem(sys.modules, module.__name__, module)
    before = _files(inputs['root'])
    with pytest.raises(ValueError, match='requires the committed U3-C/D'):
        # Exercise the actual fixed consumer loader with an absent declaration;
        # the preceding test covers the public verifier's same refusal path.
        registration._consumer(dependencies)
    assert sys.modules[module.__name__] is module
    assert _files(inputs['root']) == before


@pytest.mark.parametrize('mutation,diagnostic', [
    ('gates', 'v2 execution gate obligations mismatch'),
    ('preparation_digest', 'v2 preparation digest mismatch'),
    ('dependencies', 'v2 dependency identity mismatch'),
    ('budget', 'v2 execution runtime mismatch'),
    ('runtime_digest', 'v2 execution runtime_declaration_sha256 mismatch'),
    ('draft_bool', 'v2 execution max_draft_checks mismatch'),
    ('draft_count', 'v2 execution max_draft_checks mismatch'),
    ('selection', 'v2 execution selection_sha256 mismatch'),
    ('instruction', 'v2 execution instruction_sha256 mismatch'),
    ('working_directory', 'v2 execution working_directory mismatch'),
    ('composition_digest', 'v2 composition digest mismatch'),
    ('composition', 'v2 composition render_spec mismatch'),
    ('composition_instruction', 'v2 composition instruction_sha256 mismatch'),
    ('composition_selection', 'v2 composition selection_sha256 mismatch'),
    ('composition_runtime', 'v2 composition runtime_sha256 mismatch'),
], ids=['gates', 'preparation_digest', 'dependencies', 'budget', 'runtime_digest',
        'draft_bool', 'draft_count', 'selection', 'instruction', 'working_directory',
        'composition_digest', 'composition', 'composition_instruction',
        'composition_selection', 'composition_runtime'])
def test_execution_prefix_must_match_rederived_preparation_before_consumer(prepared, monkeypatch, mutation, diagnostic):
    inputs, preparation = prepared
    envelope = _execution_prefix(inputs, preparation)
    body = envelope['registration']
    if mutation == 'gates': body['execution_gates'].pop()
    elif mutation == 'preparation_digest': body['preparation_sha256'] = '0' * 64
    elif mutation == 'dependencies':
        body['dependencies'] = deepcopy(body['dependencies'])
        body['dependencies']['base']['source_commit'] = 'f' * 40
    elif mutation == 'budget':
        body['runtime'] = deepcopy(body['runtime'])
        body['runtime']['budget_guard_usd'] = '999'
    elif mutation == 'runtime_digest': body['runtime_declaration_sha256'] = '0' * 64
    elif mutation == 'draft_bool': body['max_draft_checks'] = True
    elif mutation == 'draft_count': body['max_draft_checks'] += 1
    elif mutation == 'selection': body['selection_sha256'] = '0' * 64
    elif mutation == 'instruction': body['instruction_sha256'] = '0' * 64
    elif mutation == 'working_directory': body['working_directory'] = str(inputs['root'])
    elif mutation == 'composition_digest': body['composition_sha256'] = '0' * 64
    else:
        composition = c.strict_json(body['composition_raw_json'].encode())
        if mutation == 'composition': composition['render_spec']['reasoning_effort'] = 'low'
        else:
            field = {'composition_instruction': 'instruction_sha256',
                     'composition_selection': 'selection_sha256',
                     'composition_runtime': 'runtime_sha256'}[mutation]
            composition[field] = '0' * 64
        composition_raw = c.canonical(composition)
        body['composition_raw_json'] = composition_raw.decode()
        body['composition_sha256'] = c.sha(composition_raw)
    monkeypatch.setattr(registration, '_consumer',
                        lambda *a: pytest.fail('mismatched E/C reached consumer'))
    with pytest.raises(ValueError, match=diagnostic):
        registration.verified(c.canonical(envelope))


@pytest.fixture
def fabricated_authorizations(tmp_path, monkeypatch):
    """Isolated approval-parser unit data, never a valid full E or real approval."""
    raw = b'FABRICATED approval parser unit; not an execution registration\n'
    source_commit = registration.authority.neutral.head()
    value = {'attempt_id': 'synthetic-attempt', 'permission_probe_sha256': 'b' * 64,
             'dependencies': {'base': {'source_commit': source_commit}}}
    binding = {'registration_sha256': c.sha(raw), 'attempt_id': value['attempt_id'],
        'source_commit': source_commit, 'dependencies_sha256': c.sha(c.canonical(value['dependencies']))}
    review = {**binding, 'kind': 'd4d_native_execution_review_v2', 'version': 2,
        'reviewer': 'synthetic-reviewer', 'author': 'synthetic-author', 'independent': True,
        'decision': 'approved', 'reviewed_at': 'synthetic-time', 'evidence': 'Fabricated unit test only'}
    repository = 'https://github.com/synthetic/native-u3a-tests'
    monkeypatch.setattr(registration, '_ci_repository_url', lambda: repository)
    ci = {**binding, 'kind': 'd4d_native_execution_ci_v2', 'version': 2,
        'workflow_event': 'workflow_dispatch', 'workflow_ref': 'refs/heads/main',
        'tested_commit': source_commit,
        'workflow_sha256': {'.github/workflows/main.yaml':
            c.sha((registration.authority.ROOT / '.github/workflows/main.yaml').read_bytes())},
        'checks': {name: {'head_sha': source_commit, 'status': 'completed', 'conclusion': 'success',
            'details_url': repository + '/actions/runs/1'}
            for name in registration.required_checks('workflow_dispatch')}}
    word = {**binding, 'kind': 'd4d_native_execution_launch_authorization_v2', 'version': 2,
        'owner': 'synthetic-owner', 'authorized_at': 'synthetic-time', 'word': 'AUTHORIZE_ONE_NATIVE_ATTEMPT',
        'review_sha256': c.sha(c.canonical(review)), 'ci_sha256': c.sha(c.canonical(ci)),
        'permission_probe_sha256': value['permission_probe_sha256']}
    records = {'review': review, 'ci': ci, 'launch_word': word}
    paths = {key: tmp_path.resolve() / (key + '.json') for key in records}
    for key, record in records.items():
        paths[key].write_bytes(c.canonical(record))
    return raw, value, records, paths


def _authorization_kwargs(paths):
    return {key + '_path': path for key, path in paths.items()}


def test_approval_parser_captures_exact_fabricated_bytes_without_writes(fabricated_authorizations):
    raw, value, records, paths = fabricated_authorizations
    before = {key: path.read_bytes() for key, path in paths.items()}
    captured = registration._authorizations(raw, value, **_authorization_kwargs(paths))
    assert set(captured) == set(paths)
    for key, artifact in captured.items():
        assert artifact.raw == before[key]
        assert artifact.pin.sha256 == c.sha(before[key])
        assert paths[key].read_bytes() == before[key]


@pytest.mark.parametrize('mutation,diagnostic', [
    ('self_review', 'v2 review cannot approve its own author'),
    ('not_independent', 'v2 review independence must be explicit'),
    ('review_decision', 'v2 review decision must be approved'),
    ('review_v1', 'review must bind this exact v2 execution'),
    ('review_bool', 'review must bind this exact v2 execution'),
    ('extra_review', 'v2 independent review'),
    ('ci_head', 'v2 CI check source differs from source commit'),
    ('ci_status', 'v2 CI check status must be completed'),
    ('missing_check', 'v2 CI check roster differs from the exact required event roster'),
    ('failed_ci', 'v2 CI check conclusion must be success'),
    ('owner_registration', 'launch_word must bind this exact v2 execution'),
    ('owner_review', 'v2 owner review hash differs'),
    ('owner_ci', 'v2 owner CI hash differs'),
    ('owner_permission', 'v2 owner permission probe hash differs'),
    ('owner_word', 'v2 owner word must authorize exactly one native attempt'),
], ids=['self_review', 'not_independent', 'review_decision', 'review_v1', 'review_bool',
        'extra_review', 'ci_head', 'ci_status', 'missing_check', 'failed_ci',
        'owner_registration', 'owner_review', 'owner_ci', 'owner_permission', 'owner_word'])
def test_approval_parser_refuses_each_fabricated_authority_mismatch(fabricated_authorizations, mutation, diagnostic):
    raw, value, records, paths = fabricated_authorizations
    review, ci, word = records['review'], records['ci'], records['launch_word']
    if mutation == 'self_review': review['reviewer'] = review['author']
    elif mutation == 'not_independent': review['independent'] = False
    elif mutation == 'review_decision': review['decision'] = 'changes_requested'
    elif mutation == 'review_v1': review['version'] = 1
    elif mutation == 'review_bool': review['version'] = True
    elif mutation == 'extra_review': review['override'] = True
    elif mutation == 'ci_head': next(iter(ci['checks'].values()))['head_sha'] = 'c' * 40
    elif mutation == 'ci_status': next(iter(ci['checks'].values()))['status'] = 'in_progress'
    elif mutation == 'missing_check': ci['checks'].pop(next(iter(ci['checks'])))
    elif mutation == 'failed_ci': next(iter(ci['checks'].values()))['conclusion'] = 'failure'
    elif mutation == 'owner_registration': word['registration_sha256'] = '0' * 64
    elif mutation == 'owner_review': word['review_sha256'] = '0' * 64
    elif mutation == 'owner_ci': word['ci_sha256'] = '0' * 64
    elif mutation == 'owner_permission': word['permission_probe_sha256'] = '0' * 64
    else: word['word'] = 'ALLOW_ANY_ATTEMPT'
    if not mutation.startswith('owner_'):
        # Owner evidence must endorse the changed bytes. Otherwise its stale
        # hash masks removal of the review/CI check this case is meant to kill.
        word['review_sha256'] = c.sha(c.canonical(review))
        word['ci_sha256'] = c.sha(c.canonical(ci))
    for key, record in records.items():
        paths[key].write_bytes(c.canonical(record))
    before = {key: path.read_bytes() for key, path in paths.items()}
    with pytest.raises(ValueError, match=diagnostic):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))
    assert {key: path.read_bytes() for key, path in paths.items()} == before
