"""U3-A r2 bridge checks with real local committed-source proof, 2026-11-07.

Tiny consumers below are explicit software fixtures, never U3-C/D admission.
No helper, runtime, native executable or provider is launched. Guard-removal
tests must reach their named refusal rather than fail at an unrelated join.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_execution_registration_v2 as registration
from data_sheets_schema import native_shared_contract as c
from tests.test_native_execution_registration_v2 import (
    _execution_prefix, prepared, inputs, isolated_modules, native_spec, declaration,
)


CONSUMER_PATH = 'src/data_sheets_schema/native_shared_registration.py'
CONSUMER_SOURCE = b'''"""Synthetic source-binding fixture, not an execution implementation."""
AUTHORITY_VERSION = 2

def rebuild_v2_body(*, preparation_raw, composition_path, system_path,
                   permission_probe_path, attempt_id, attempt_directory,
                   evidence_directory, max_draft_checks, receipt_origin_version,
                   classifier_projection):
    return {'fixture': 'not an admitted execution'}

def execution_paths_v2(body, *, fresh, extra_protected):
    return []
'''


def _git(root, *args):
    # No inherited Git config, hooks, credentials, alternates or replacement refs.
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'GIT_NO_LAZY_FETCH': '1',
           'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_SYSTEM': os.devnull}
    return subprocess.run(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Software fixture',
        '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false',
        *args], cwd=root, env=env, capture_output=True, check=True, timeout=30).stdout


@pytest.fixture
def consumer_source(tmp_path):
    """Create each exact consumer in its own local object store; never a worktree edit."""
    def create(source=CONSUMER_SOURCE, extras=None):
        root = tmp_path / ('consumer-' + str(len(list(tmp_path.glob('consumer-*')))))
        root.mkdir()
        files = {CONSUMER_PATH: source, **(extras or {})}
        for relative, raw in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        _git(root, 'init', '-q')
        _git(root, 'add', '--', '.')
        _git(root, 'commit', '-qm', 'Synthetic consumer source proof')
        identity = {'version': 2, 'base': {'authority_version': 2,
            'source_commit': _git(root, 'rev-parse', 'HEAD').decode().strip(),
            'package_sources': {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
            'modules': {}}, 'additional_modules': {}}
        return root, identity
    return create


@contextmanager
def source_context(monkeypatch, root, identity):
    """Only source location/identity is fixture supplied; Git proof is unmodified."""
    with monkeypatch.context() as patch:
        patch.setattr(registration.authority, 'ROOT', root)
        patch.setattr(registration.authority, 'dependency_identity', lambda: deepcopy(identity))
        yield


@pytest.mark.parametrize('field', ['attempt_id', 'permission_probe_sha256',
                                  'system_path', 'attempt_directory', 'scope', 'extra'])
def test_execution_key_set_refuses_before_preparation_or_consumer(prepared, monkeypatch, field):
    data, preparation = prepared
    envelope = _execution_prefix(data, preparation)
    if field == 'extra': envelope['registration']['skip_gates'] = True
    else: envelope['registration'].pop(field)
    monkeypatch.setattr(registration, 'verify_preparer',
                        lambda *a, **k: pytest.fail('bad execution shape reached preparation'))
    monkeypatch.setattr(registration, '_consumer',
                        lambda *a, **k: pytest.fail('bad execution shape reached consumer'))
    with pytest.raises(ValueError, match='v2 execution body keys mismatch'):
        registration.verified(c.canonical(envelope), classifier_projection=object())


def test_verified_routes_dirty_closure_through_actual_committed_proof(prepared, consumer_source, monkeypatch):
    data, preparation = prepared
    envelope = _execution_prefix(data, preparation)
    root, identity = consumer_source()
    source = root / CONSUMER_PATH
    source.write_bytes(source.read_bytes() + b'\n# uncommitted source change\n')
    identity['base']['package_sources'][CONSUMER_PATH] = c.sha(source.read_bytes())
    real_proof = registration.authority.require_committed
    visits = []

    def prove(dependencies):
        visits.append(deepcopy(dependencies))
        assert dependencies == preparation['registration']['dependencies']
        with source_context(monkeypatch, root, identity):
            real_proof(identity)

    monkeypatch.setattr(registration.authority, 'require_committed', prove)
    monkeypatch.setattr(registration, '_consumer',
                        lambda *a, **k: pytest.fail('dirty closure reached consumer'))
    with pytest.raises(ValueError, match='consumed source differs from the reviewed commit'):
        registration.verified(c.canonical(envelope), classifier_projection=object())
    assert visits == [preparation['registration']['dependencies']]
    assert source.read_bytes().endswith(b'# uncommitted source change\n')


def test_verified_rechecks_committed_sources_after_preparation(prepared, consumer_source, monkeypatch):
    """ME guard test: the first proof passes; the real second proof must refuse.

    The tiny committed closure is a software fixture, not a C execution consumer.
    Preparation still takes its ordinary path. Only the proof's local source
    location and identity are substituted, as in the earlier first-proof test.
    """
    data, preparation = prepared
    envelope = _execution_prefix(data, preparation)
    root, identity = consumer_source()
    source = root / CONSUMER_PATH
    real_proof = registration.authority.require_committed
    real_verify_preparer = registration.verify_preparer
    proofs, preparations = [], []

    def prove(dependencies):
        assert dependencies == preparation['registration']['dependencies']
        proofs.append('after preparation' if preparations else 'before preparation')
        with source_context(monkeypatch, root, identity):
            real_proof(identity)

    def prepare_then_dirty(raw, *, job_id):
        result = real_verify_preparer(raw, job_id=job_id)
        preparations.append(job_id)
        source.write_bytes(source.read_bytes() + b'\n# changed after preparation proof\n')
        identity['base']['package_sources'][CONSUMER_PATH] = c.sha(source.read_bytes())
        return result

    monkeypatch.setattr(registration.authority, 'require_committed', prove)
    monkeypatch.setattr(registration, 'verify_preparer', prepare_then_dirty)
    monkeypatch.setattr(registration, '_consumer',
                        lambda *a, **k: pytest.fail('post-preparation dirty closure reached consumer'))
    with pytest.raises(ValueError, match='consumed source differs from the reviewed commit'):
        registration.verified(c.canonical(envelope), classifier_projection=object())
    assert preparations == [preparation['registration']['job_id']]
    assert proofs[0] == 'before preparation'
    assert proofs.count('before preparation') >= 2
    assert proofs.count('after preparation') == 1
    assert proofs[-1] == 'after preparation'
    assert source.read_bytes().endswith(b'# changed after preparation proof\n')


@pytest.mark.parametrize('entry', ['verified', 'admit'])
@pytest.mark.parametrize('projection', ['omitted', 'none'])
def test_projection_is_required_before_any_authority_effect(tmp_path, monkeypatch, entry, projection):
    """Missing input cannot reach wire decoding, source loads, or authority reads."""
    def forbidden(*args, **kwargs):
        pytest.fail('missing projection reached an authority operation')

    for name in ('_wire', '_consumer', '_authorizations', '_read', 'validate_runtime'):
        monkeypatch.setattr(registration, name, forbidden)
    for name in ('dependency_identity', 'require_committed', 'loaded_dependencies'):
        monkeypatch.setattr(registration.authority, name, forbidden)
    kwargs = {} if entry == 'verified' else {
        'review_path': tmp_path / 'review', 'ci_path': tmp_path / 'ci',
        'launch_word_path': tmp_path / 'owner'}
    if projection == 'none':
        kwargs['classifier_projection'] = None
    expected = TypeError if projection == 'omitted' else ValueError
    diagnostic = 'classifier_projection' if projection == 'omitted' else 'explicit classifier projection'
    with pytest.raises(expected, match=diagnostic):
        getattr(registration, entry)(b'not decoded or opened', **kwargs)
    assert list(tmp_path.iterdir()) == []


class _OpaqueProjectionLookalike:
    """A forwarding sentinel; it is deliberately not a valid C projection."""
    def __bool__(self):
        raise AssertionError('A must not test projection truthiness')

    def __iter__(self):
        raise AssertionError('A must not enumerate a projection')

    def __deepcopy__(self, memo):
        raise AssertionError('A must not copy a projection')

    def __getattr__(self, name):
        raise AssertionError('A must not inspect projection attributes: ' + name)


def _projection(kind):
    return {'opaque': object, 'mapping': dict, 'lookalike': _OpaqueProjectionLookalike}[kind]()


@pytest.mark.parametrize('kind', ['opaque', 'mapping', 'lookalike'])
def test_verified_forwards_exact_projection_to_source_compiled_consumer(
        prepared, consumer_source, monkeypatch, kind):
    """Only A's forwarding is accepted here, using an explicit software consumer.

    This tiny source-compiled consumer records the supplied object and returns a
    declared body. It does not validate C authority, and no execution is admitted.
    """
    data, preparation = prepared
    envelope = _execution_prefix(data, preparation)
    expected = envelope['registration']
    source = CONSUMER_SOURCE.replace(b'AUTHORITY_VERSION = 2',
                                    b'AUTHORITY_VERSION = 2\nRECEIVED = []')
    source = source.replace(b"return {'fixture': 'not an admitted execution'}",
        ('RECEIVED.append(classifier_projection)\n    return ' + repr(expected)).encode())
    root, identity = consumer_source(source)
    real_consumer = registration._consumer
    received = []
    projection = _projection(kind)

    @contextmanager
    def fixture_consumer(dependencies):
        assert dependencies == preparation['registration']['dependencies']
        with source_context(monkeypatch, root, identity):
            registration.authority.require_committed(identity)
            with real_consumer(identity) as module:
                yield module
                received.extend(module.RECEIVED)

    monkeypatch.setattr(registration, '_consumer', fixture_consumer)
    result = registration.verified(c.canonical(envelope), classifier_projection=projection)
    assert result == expected
    assert len(received) == 1 and received[0] is projection
    assert 'classifier_projection' not in result
    assert 'classifier_projection' not in registration._rebuild_inputs(
        expected, expected['preparation_raw_json'].encode('utf-8'))


@pytest.mark.parametrize('kind', ['opaque', 'mapping', 'lookalike'])
def test_admit_forwards_same_projection_to_both_verifications(monkeypatch, kind):
    """Isolated A orchestration unit; fabricated gate outputs are not C admission."""
    projection = _projection(kind)
    raw = b'isolated admission forwarding fixture'
    value = {'runtime': {'fixture': 'not a real runtime'}, 'dependencies': {'fixture': True}}
    evidence = {role: SimpleNamespace(pin=SimpleNamespace(path='fixture-' + role))
                for role in ('review', 'ci', 'launch_word')}
    verified_calls, path_calls, rereads = [], [], []

    def verified(given_raw, *, classifier_projection):
        assert given_raw is raw
        verified_calls.append(classifier_projection)
        return deepcopy(value)

    def execution_paths(body, *, fresh, extra_protected):
        path_calls.append((body, fresh, extra_protected))
        return []

    @contextmanager
    def consumer(dependencies):
        assert dependencies == value['dependencies']
        yield SimpleNamespace(execution_paths_v2=execution_paths)

    def read(path, label):
        rereads.append((path, label))
        return next(item for item in evidence.values() if item.pin.path == path)

    monkeypatch.setattr(registration, 'verified', verified)
    monkeypatch.setattr(registration, '_authorizations', lambda *a, **k: evidence)
    monkeypatch.setattr(registration, 'validate_runtime',
                        lambda runtime: {'keep_awake': {'host_platform': sys.platform}})
    monkeypatch.setattr(registration, '_consumer', consumer)
    monkeypatch.setattr(registration, '_checked_reservations', lambda *a, **k: ())
    monkeypatch.setattr(registration, '_read', read)
    result = registration.admit(raw, review_path='unused-review', ci_path='unused-ci',
        launch_word_path='unused-owner', classifier_projection=projection)
    assert len(verified_calls) == 2 and all(item is projection for item in verified_calls)
    assert path_calls == [(value, True, tuple(item.pin.path for item in evidence.values()))]
    assert len(rereads) == 3
    assert result == registration.Admission(raw, tuple(evidence.values()), ())
    assert 'classifier_projection' not in vars(result)


def test_consumer_loads_real_committed_bytes_without_ambient_module(consumer_source, monkeypatch):
    root, identity = consumer_source()
    name = 'data_sheets_schema.native_shared_registration'
    previous = sys.modules.get(name)
    with source_context(monkeypatch, root, identity):
        registration.authority.require_committed(identity)
        with registration._consumer(identity) as module:
            assert module.AUTHORITY_VERSION == 2
            assert Path(module.__file__).resolve() == root / CONSUMER_PATH
            assert callable(module.rebuild_v2_body)
            assert callable(module.execution_paths_v2)
    assert sys.modules.get(name) is previous


@pytest.mark.parametrize('change', ['version', 'bool_version', 'varargs', 'positional',
                                  'default', 'projection_default', 'projection_missing',
                                  'path_default', 'missing_rebuilder', 'missing_paths'])
def test_committed_consumer_rejects_wrong_version_or_interface(consumer_source, monkeypatch, change):
    source = CONSUMER_SOURCE
    if change == 'version': source = source.replace(b'AUTHORITY_VERSION = 2', b'AUTHORITY_VERSION = 1')
    elif change == 'bool_version': source = source.replace(b'AUTHORITY_VERSION = 2', b'AUTHORITY_VERSION = True')
    elif change == 'varargs':
        source = source[:source.index(b'def rebuild_v2_body')] + b'''def rebuild_v2_body(*args, **kwargs):
    return {}
def execution_paths_v2(body, *, fresh, extra_protected):
    return []
'''
    elif change == 'positional': source = source.replace(b'def rebuild_v2_body(*, preparation_raw,', b'def rebuild_v2_body(preparation_raw, *,')
    elif change == 'default': source = source.replace(b'receipt_origin_version,', b'receipt_origin_version=0,')
    elif change == 'projection_default': source = source.replace(b'classifier_projection):', b'classifier_projection=None):')
    elif change == 'projection_missing': source = source.replace(b'receipt_origin_version,\n                   classifier_projection):', b'receipt_origin_version):')
    elif change == 'path_default': source = source.replace(b'fresh, extra_protected):', b'fresh, extra_protected=()):')
    elif change == 'missing_rebuilder': source = source.replace(b'def rebuild_v2_body(', b'def verified_v2_body(')
    else: source = source.replace(b'def execution_paths_v2(', b'def arbitrary_paths(')
    assert source != CONSUMER_SOURCE, 'the named interface mutation must change the source'
    root, identity = consumer_source(source)
    with source_context(monkeypatch, root, identity):
        diagnostic = ('v2 execution consumer authority version mismatch'
            if change in ('version', 'bool_version') else 'v2 execution consumer interface mismatch')
        with pytest.raises(ValueError, match=diagnostic):
            with registration._consumer(identity):
                pytest.fail('unsupported committed consumer admitted')


def test_consumer_refuses_changed_source_despite_valid_committed_name(consumer_source, monkeypatch):
    root, identity = consumer_source()
    (root / CONSUMER_PATH).write_bytes(CONSUMER_SOURCE + b'\nUNREVIEWED = True\n')
    with source_context(monkeypatch, root, identity):
        with pytest.raises(ValueError, match='consumer source differs from the committed package closure'):
            with registration._consumer(identity):
                pytest.fail('changed source executed')


@pytest.mark.parametrize('change', ['echo_preparation', 'different_closed_body'])
def test_verified_refuses_echo_or_different_reconstruction(prepared, consumer_source, monkeypatch, change):
    data, preparation = prepared
    envelope = _execution_prefix(data, preparation)
    if change == 'echo_preparation':
        source = b'import json\n' + CONSUMER_SOURCE.replace(
            b"return {'fixture': 'not an admitted execution'}",
            b"return json.loads(preparation_raw)['registration']")
        diagnostic = 'v2 execution body keys mismatch'
    else:
        rebuilt = deepcopy(envelope['registration'])
        rebuilt['effective_system'] = 'A different reconstructed declaration.'
        source = CONSUMER_SOURCE.replace(
            b"return {'fixture': 'not an admitted execution'}", ('return ' + repr(rebuilt)).encode())
        diagnostic = 'v2 execution consumer did not reconstruct the complete registration'
    root, identity = consumer_source(source)
    real_consumer = registration._consumer
    received = []

    @contextmanager
    def fixture_consumer(dependencies):
        received.append(deepcopy(dependencies))
        with source_context(monkeypatch, root, identity):
            registration.authority.require_committed(identity)
            with real_consumer(identity) as module:
                yield module

    monkeypatch.setattr(registration, '_consumer', fixture_consumer)
    with pytest.raises(ValueError, match=diagnostic):
        registration.verified(c.canonical(envelope), classifier_projection=object())
    assert received == [preparation['registration']['dependencies']]


def _reservation_paths(data, preparation):
    value = _execution_prefix(data, preparation)['registration']
    selected = c.strict_json(data['selection'].read_bytes())
    expected = {Path(value['attempt_directory']), Path(value['evidence_directory']),
                Path(selected['stage_root'])}
    expected.update(Path(path).parent for path in preparation['registration']['outputs'].values())
    return value, sorted(expected)


@pytest.mark.parametrize('change', ['none', 'tuple', 'strings', 'omitted', 'duplicate', 'extra'])
def test_reservation_consumer_result_is_typed_complete_and_unique(prepared, change):
    data, preparation = prepared
    value, paths = _reservation_paths(data, preparation)
    if change == 'none': paths = None
    elif change == 'tuple': paths = tuple(paths)
    elif change == 'strings': paths = list(map(str, paths))
    elif change == 'omitted': paths.pop()
    elif change == 'duplicate': paths.append(paths[0])
    else: paths.append(data['root'] / 'not-a-declared-reservation')
    with pytest.raises(ValueError, match='v2 execution reservation result mismatch'):
        registration._checked_reservations(paths, value, {})


def test_reservations_refuse_protected_input_overlap_without_creating_directories(prepared):
    data, preparation = prepared
    value, paths = _reservation_paths(data, preparation)
    attempt = Path(value['attempt_directory'])
    assert not attempt.exists()
    # Direct path-consumer unit: the submitted input lives inside the proposed
    # reservation. Full verified() independently checks that input's bytes.
    value['composition'] = str(attempt / 'composition.json')
    with pytest.raises(ValueError, match='v2 execution reservations overlap protected paths'):
        registration._checked_reservations(paths, value, {})
    assert not attempt.exists()


def test_reservations_refuse_selection_changed_after_preparation(prepared, monkeypatch):
    data, preparation = prepared
    value, paths = _reservation_paths(data, preparation)
    real_verify = registration.verify_preparer
    visits = []

    def verify_then_change(raw, *, job_id):
        result = real_verify(raw, job_id=job_id)
        visits.append(result['selection'])
        changed = c.strict_json(data['selection'].read_bytes())
        changed['stage_root'] = str(data['root'] / 'late-foreign-stages')
        data['selection'].write_bytes(c.canonical(changed))
        return result

    monkeypatch.setattr(registration, 'verify_preparer', verify_then_change)
    with pytest.raises(ValueError, match='v2 selected path authority changed after preparation'):
        registration._checked_reservations(paths, value, {})
    assert visits == [preparation['registration']['selection']]
    assert not (data['root'] / 'late-foreign-stages').exists()


def test_worker_thread_admission_refuses_before_verification_or_evidence(monkeypatch):
    monkeypatch.setattr(registration, 'verified',
                        lambda *a, **k: pytest.fail('worker thread reached verification'))
    monkeypatch.setattr(registration, '_authorizations',
                        lambda *a, **k: pytest.fail('worker thread reached evidence reads'))
    observed = []

    def attempt():
        try:
            registration.admit(b'not an envelope', review_path='not-read-review',
                ci_path='not-read-ci', launch_word_path='not-read-owner',
                classifier_projection=object())
        except BaseException as exc:
            observed.append(exc)

    thread = threading.Thread(target=attempt)
    thread.start(); thread.join(timeout=5)
    assert not thread.is_alive()
    assert len(observed) == 1 and type(observed[0]) is ValueError
    assert str(observed[0]) == 'v2 execution admission requires the main thread'


def test_wire_still_invokes_pinned_envelope_check_after_structural_precheck(prepared, monkeypatch):
    _, preparation = prepared
    loader = registration.authority.loaded_dependencies
    observed = []

    @contextmanager
    def observe(identity):
        with loader(identity) as controls:
            original = controls['prepare_registration_v2'].require_envelope
            def check(value):
                observed.append(deepcopy(value))
                return original(value)
            # Spy on the yielded lookup only; never mutate the source-verified
            # module or its callables. The real pinned check still runs.
            yield {**controls, 'prepare_registration_v2': SimpleNamespace(require_envelope=check)}

    monkeypatch.setattr(registration.authority, 'loaded_dependencies', observe)
    body, identity = registration._wire(c.canonical(preparation))
    assert body == preparation['registration']
    assert identity == preparation['registration']['dependencies']
    assert observed == [preparation]
