"""U4b addendum 1: actual public boundary, isolated upstream reconstruction.

The permitted base cannot construct a genuine current-profile registration.
These tests isolate that prerequisite and CI/source loading, then execute the
real public proposal/readback boundary and pinned runtime observation reader.
They are not full registration acceptance; no process or provider is executed.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import native_shared_registration_orchestration as subject
from data_sheets_schema import native_u4b_runtime as runtime
from tests.test_native_u4b_runtime import runtime_inputs, refresh_fabricated_observation, no_process_launch  # noqa: F401


def registration_body(tmp_path):
    initial, arguments = runtime_inputs(tmp_path)
    prepared = runtime.prepare_runtime(initial, **arguments)
    preparation = b'{"scope":"fabricated upstream prerequisite"}'
    body = {'runtime': prepared, 'kind': subject.KIND, 'schema_version': subject.VERSION,
        'execution': subject.EXECUTION, 'execution_gates': list(subject.consumer.GATES),
        'preparation_raw_json': preparation.decode(), 'preparation_sha256': subject.c.sha(preparation),
        'composition': str(tmp_path / 'composition'), 'system_path': str(tmp_path / 'system'),
        'permission_probe': str(tmp_path / 'permission'), 'attempt_id': 'invented-boundary',
        'attempt_directory': str(tmp_path / 'attempt'), 'evidence_directory': str(tmp_path / 'evidence'),
        'max_draft_checks': 1, 'dependencies': {'scope': 'isolated upstream source prerequisite'}}
    path = Path(body['permission_probe'])
    path.write_bytes(b'{"scope":"invented upstream permission snapshot A"}')
    body['permission_probe_sha256'] = subject.c.sha(path.read_bytes())
    return body, arguments, preparation


def isolated_bound_result(path):
    """A readback-boundary fixture, not an actual permission verdict.

    The genuine saved consumer is independently exercised by the A3 sequence
    tests. Here only its reported pin is varied to test the final body join.
    """
    raw = Path(path).read_bytes()
    return {'checked': True, 'passed': True,
            'permission': {'path': path, 'sha256': subject.c.sha(raw), 'bytes': len(raw)},
            'scope': 'explicitly isolated bound-probe prerequisite; not acceptance'}


def corrupt_thinking(body, arguments, mutation):
    basis = json.loads(body['runtime']['limits_basis'])
    if mutation == 'missing_observation':
        path = Path(arguments['native_request_path'])
        init = json.loads(path.read_bytes())
        del init['thinking']
        line = json.dumps(init).encode()
        raw = line + b'\n'
        path.write_bytes(raw)
        basis['request'].update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        basis['thinking']['observed'] = {'state': 'not_emitted', 'field': None, 'value': None}
    elif mutation == 'missing_registration_field':
        del basis['thinking']['declared']
    elif mutation == 'missing_kind':
        del basis['kind']
    elif mutation == 'changed_kind':
        basis['kind'] = 'invented-historical-discriminator'
    elif mutation == 'legacy_basis':
        body['runtime']['limits_basis'] = 'historical declared basis'
        return
    else:
        basis['thinking']['declared'] = False
    body['runtime']['limits_basis'] = runtime._canonical(basis)


@pytest.mark.parametrize('entry', ['proposal', 'outer_readback', 'body_readback'])
@pytest.mark.parametrize('mutation', ['missing_observation', 'missing_registration_field', 'mismatch',
                                    'missing_kind', 'changed_kind', 'legacy_basis'])
def test_public_registration_refuses_unobserved_or_contradictory_thinking(
        tmp_path, monkeypatch, entry, mutation):
    body, arguments, preparation = registration_body(tmp_path)
    # This cohort isolates complete bound-probe verification, like the other
    # upstream prerequisites. A3 sequence tests exercise its real reader.
    from data_sheets_schema import native_u4b_probe_sequence as sequence
    monkeypatch.setattr(sequence, 'validate_bound_probe', lambda selected, path: isolated_bound_result(path))
    assert subject._require_runtime_observation(body) is body
    corrupt_thinking(body, arguments, mutation)
    monkeypatch.setattr(subject, '_registration_body', lambda *a, **k: deepcopy(body))

    def no_envelope(*args, **kwargs):
        pytest.fail('invalid observation reached envelope publication')
    monkeypatch.setattr(subject.authority, 'loaded_dependencies', no_envelope)
    if entry == 'proposal':
        call = lambda: subject.registration(body['composition'], body['system_path'])
    elif entry == 'body_readback':
        call = lambda: subject.verified_v2_body(subject.c.canonical(body), preparation_raw=preparation)
    else:
        projection = object()
        @contextmanager
        def isolated_controls(dependencies):
            assert dependencies == body['dependencies']
            yield projection
        def isolated_reconstruction(raw, *, classifier_projection):
            assert raw == b'explicit upstream fixture' and classifier_projection is projection
            return deepcopy(body)
        monkeypatch.setattr(subject.authority, 'dependency_identity', lambda: body['dependencies'])
        monkeypatch.setattr(subject.control_loading, 'loaded_controls', isolated_controls)
        monkeypatch.setattr(subject.execution_v2, 'verified', isolated_reconstruction)
        call = lambda: subject.verified(b'explicit upstream fixture')
    diagnostic = ('U4b runtime basis' if mutation in ('missing_kind', 'changed_kind')
                  else 'Expecting value' if mutation == 'legacy_basis' else 'thinking')
    with pytest.raises(ValueError, match=diagnostic):
        call()
    assert not Path(body['attempt_directory']).exists()
    assert not Path(body['evidence_directory']).exists()


@pytest.mark.parametrize('entry', ['proposal', 'outer_readback', 'body_readback'])
def test_public_boundary_rejects_replaced_and_rehashed_bound_permission(tmp_path, monkeypatch, entry):
    body, _, preparation = registration_body(tmp_path)
    from data_sheets_schema import native_u4b_probe_sequence as sequence
    monkeypatch.setattr(sequence, 'validate_bound_probe', lambda selected, path: isolated_bound_result(path))
    assert subject._require_runtime_observation(body) is body
    # Upstream reconstruction captured A. The later reader now reports B's
    # freshly recomputed digest; neither a passing flag nor rehash permits the
    # public boundary to return A's registration with B's permission evidence.
    Path(body['permission_probe']).write_bytes(b'{"scope":"invented replacement permission snapshot B"}')
    assert isolated_bound_result(body['permission_probe'])['permission']['sha256'] != body['permission_probe_sha256']
    monkeypatch.setattr(subject, '_registration_body', lambda *a, **k: deepcopy(body))
    monkeypatch.setattr(subject.authority, 'loaded_dependencies',
                        lambda *a, **k: pytest.fail('replaced permission reached envelope publication'))
    if entry == 'proposal':
        call = lambda: subject.registration(body['composition'], body['system_path'])
    elif entry == 'body_readback':
        call = lambda: subject.verified_v2_body(subject.c.canonical(body), preparation_raw=preparation)
    else:
        projection = object()
        @contextmanager
        def isolated_controls(dependencies):
            assert dependencies == body['dependencies']
            yield projection
        monkeypatch.setattr(subject.authority, 'dependency_identity', lambda: body['dependencies'])
        monkeypatch.setattr(subject.control_loading, 'loaded_controls', isolated_controls)
        def reconstruction(raw, *, classifier_projection):
            assert raw == b'isolated captured registration A' and classifier_projection is projection
            return deepcopy(body)
        monkeypatch.setattr(subject.execution_v2, 'verified', reconstruction)
        call = lambda: subject.verified(b'isolated captured registration A')
    with pytest.raises(ValueError, match='bound permission result differs'):
        call()
    assert not Path(body['attempt_directory']).exists()
    assert not Path(body['evidence_directory']).exists()


def test_matching_bound_pin_passes_isolated_public_body_readback(tmp_path, monkeypatch):
    body, _, preparation = registration_body(tmp_path)
    from data_sheets_schema import native_u4b_probe_sequence as sequence
    calls = []
    def readback(selected, path):
        assert selected == body['runtime'] and path == body['permission_probe']
        calls.append(path)
        return isolated_bound_result(path)
    monkeypatch.setattr(sequence, 'validate_bound_probe', readback)
    monkeypatch.setattr(subject, '_registration_body', lambda *a, **k: deepcopy(body))
    assert subject.verified_v2_body(subject.c.canonical(body), preparation_raw=preparation) == body
    assert calls == [body['permission_probe']]


@pytest.mark.parametrize('mutation', ['unchecked', 'unpassed', 'missing_pin', 'wrong_path',
                                     'bool_bytes', 'zero_bytes', 'missing_registered_hash'])
def test_final_join_requires_explicit_matching_bound_result(tmp_path, monkeypatch, mutation):
    body, _, _ = registration_body(tmp_path)
    from data_sheets_schema import native_u4b_probe_sequence as sequence
    returned = isolated_bound_result(body['permission_probe'])
    if mutation == 'unchecked': returned['checked'] = False
    elif mutation == 'unpassed': returned['passed'] = False
    elif mutation == 'missing_pin': del returned['permission']
    elif mutation == 'wrong_path': returned['permission']['path'] += '-other'
    elif mutation == 'bool_bytes': returned['permission']['bytes'] = True
    elif mutation == 'zero_bytes': returned['permission']['bytes'] = 0
    else: del body['permission_probe_sha256']
    monkeypatch.setattr(sequence, 'validate_bound_probe', lambda *a: deepcopy(returned))
    with pytest.raises(ValueError, match='permission'):
        subject._require_runtime_observation(body)


@pytest.mark.parametrize('context_mode', ['0', '1'])
def test_historical_other_model_profile_keeps_its_validator(tmp_path, context_mode):
    historical, _ = runtime_inputs(tmp_path)
    historical['model'] = 'claude-opus-4-6'
    historical['environment']['CLAUDE_CODE_DISABLE_1M_CONTEXT'] = context_mode
    historical['limits_basis'] = 'historical declared basis'
    body = {'runtime': historical}
    assert subject._require_runtime_observation(body) is body


def test_observed_false_is_retained_by_observation_helper(tmp_path):
    initial, arguments = runtime_inputs(tmp_path)
    path = Path(arguments['native_request_path'])
    init = json.loads(path.read_bytes())
    init['thinking'] = False
    path.write_text(json.dumps(init) + '\n')
    arguments['thinking_setting'] = False
    refresh_fabricated_observation((initial, arguments))
    body = {'runtime': runtime.prepare_runtime(initial, **arguments)}
    assert runtime.validate_prepared_runtime(body['runtime']) == body['runtime']
    assert json.loads(body['runtime']['limits_basis'])['thinking']['observed']['value'] is False
