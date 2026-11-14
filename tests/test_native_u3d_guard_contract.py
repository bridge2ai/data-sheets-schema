"""U3-D fixed A interface and remaining handoff requirements, 2026-11-07.

Synthetic builder tests check only argument forwarding and preparation binding.
They cannot establish C/D admission. Real consumer execution is independently
required by the registration and permission integration tests. The six earlier
forwarding/binding assertions retain their exact preparation-byte obligations.
"""
from copy import deepcopy
import os
from pathlib import Path
import subprocess

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_execution_registration_v2 as admission
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_registration as registration
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401 (fixture)


REBUILD_INPUTS = (
    'preparation_raw', 'composition_path', 'system_path', 'permission_probe_path',
    'attempt_id', 'attempt_directory', 'evidence_directory', 'max_draft_checks',
    'receipt_origin_version', 'classifier_projection',
)


def test_actual_consumer_signatures_match_a3_input_only_contract():
    admission._signature(registration, 'rebuild_v2_body', (), REBUILD_INPUTS)
    admission._signature(registration, 'execution_paths_v2', ('body',),
                         ('fresh', 'extra_protected'))


def test_actual_consumer_graph_loads_without_reservation_or_effects(tmp_path, monkeypatch, isolated_modules):
    # Capture real local package pins before installing effect traps. No graph,
    # source bytes, refusal verdict or loader result is replaced by a fixture.
    dependencies = authority.dependency_identity()
    touched = []

    def forbidden(*args, **kwargs):
        touched.append('effect')
        pytest.fail('consumer loading must not reserve or publish')

    with monkeypatch.context() as patch:
        for name in ('run', 'Popen', 'check_output', 'check_call', 'call'):
            patch.setattr(subprocess, name, forbidden)
        for name in ('mkdir', 'write_bytes', 'write_text'):
            patch.setattr(Path, name, forbidden)
        for name in ('mkdir', 'makedirs', 'rename', 'replace', 'unlink'):
            patch.setattr(os, name, forbidden)
        with admission._consumer(dependencies) as loaded:
            assert loaded.rebuild_v2_body.__code__.co_filename == str(
                authority.ROOT / 'src/data_sheets_schema/native_shared_registration.py')
            assert loaded.execution_paths_v2.__code__.co_filename == loaded.rebuild_v2_body.__code__.co_filename
    assert touched == []
    assert list(tmp_path.iterdir()) == []


@pytest.fixture
def synthetic_reconstruction(tmp_path, monkeypatch):
    # Deliberately not a real preparation or E. The real-graph test above and
    # existing integration suites separately retain actual admission duties.
    preparation_raw = b'{"synthetic_preparation":true}\n'
    inputs = dict(preparation_raw=preparation_raw,
        composition_path=tmp_path / 'composition.json',
        system_path=tmp_path / 'system.txt',
        permission_probe_path=tmp_path / 'permission.json', attempt_id='one-attempt',
        attempt_directory=tmp_path / 'one-attempt',
        evidence_directory=tmp_path / 'evidence', max_draft_checks=2,
        receipt_origin_version=1, classifier_projection=object())
    events = []
    supplied = []
    result = {'preparation_raw_json': preparation_raw.decode('utf-8'),
              'preparation_sha256': c.sha(preparation_raw)}

    def gates():
        events.append('gates')

    def builder(composition_path, system_path, **kwargs):
        events.append('builder')
        supplied.append({'composition_path': composition_path,
                         'system_path': system_path, **kwargs})
        return {**deepcopy(result), 'synthetic_reconstruction_number': len(supplied)}

    monkeypatch.setattr(registration, '_require_integrated_gate_implementation', gates)
    monkeypatch.setattr(registration, '_registration_body', builder)
    return inputs, events, supplied, result


def test_input_only_rebuild_forwards_inputs_and_reconstructs_each_call(synthetic_reconstruction):
    inputs, events, supplied, expected = synthetic_reconstruction
    first = registration.rebuild_v2_body(**inputs)
    second = registration.rebuild_v2_body(**inputs)
    assert events == ['gates', 'builder', 'gates', 'builder']
    wanted = {key: value for key, value in inputs.items() if key != 'classifier_projection'}
    wanted.update(controls=inputs['classifier_projection'], controller_sources=registration.controller_sources())
    assert supplied == [wanted, wanted]
    assert first == {**expected, 'synthetic_reconstruction_number': 1}
    assert second == {**expected, 'synthetic_reconstruction_number': 2}
    assert not inputs['attempt_directory'].exists()
    assert not inputs['evidence_directory'].exists()


@pytest.mark.parametrize('change', ['supplied_raw', 'rebuilt_raw', 'rebuilt_digest',
                                    'missing_raw', 'missing_digest'])
def test_input_only_rebuild_binds_exact_preparation_bytes(synthetic_reconstruction, change):
    inputs, events, supplied, result = synthetic_reconstruction
    if change == 'supplied_raw':
        # Same JSON value with different bytes must not be normalized away.
        inputs['preparation_raw'] = inputs['preparation_raw'].rstrip(b'\n')
    elif change == 'rebuilt_raw':
        result['preparation_raw_json'] += ' '
    elif change == 'rebuilt_digest':
        result['preparation_sha256'] = '0' * 64
    else:
        del result['preparation_raw_json' if change == 'missing_raw' else 'preparation_sha256']
    with pytest.raises(ValueError, match='preparation binding differs from fresh reconstruction'):
        registration.rebuild_v2_body(**inputs)
    assert events == ['gates', 'builder']
    assert len(supplied) == 1
    assert not inputs['attempt_directory'].exists()


@pytest.mark.parametrize('raw', [None, '', b'', bytearray(b'{}'), b'\xff'])
def test_input_only_rebuild_refuses_invalid_preparation_before_builder(synthetic_reconstruction, raw):
    inputs, events, supplied, _ = synthetic_reconstruction
    inputs['preparation_raw'] = raw
    with pytest.raises(ValueError, match='v2 consumer preparation requires'):
        registration.rebuild_v2_body(**inputs)
    assert events == supplied == []


def test_reservations_require_explicit_extra_protected():
    with pytest.raises(TypeError, match='extra_protected'):
        registration.execution_paths_v2({}, fresh=True)


def test_fixed_a_entry_refuses_missing_projection_before_builder_or_effects(synthetic_reconstruction):
    inputs, events, supplied, _ = synthetic_reconstruction
    inputs['classifier_projection'] = None
    with pytest.raises(ValueError, match='explicit classifier projection'):
        registration.rebuild_v2_body(**inputs)
    assert events == supplied == []
    assert not inputs['attempt_directory'].exists()
    assert not inputs['evidence_directory'].exists()


def test_execution_facade_requires_the_current_explicit_ci_event():
    from data_sheets_schema import native_shared_execution_orchestration as execution
    from data_sheets_schema import native_execution_orchestration as engine

    assert execution.required_checks is admission.required_checks
    assert engine.admission is admission
    pull = execution.required_checks('pull_request')
    push = execution.required_checks('push')
    manual = execution.required_checks('workflow_dispatch')
    assert manual == push
    assert set(pull) - set(push) == {
        'Python 3.12 / shard 9', 'Python 3.12 / shard 10', 'Python 3.12 / shard 11',
        'Python 3.12 / shard 12', 'large-files'}
    assert set(push) - set(pull) == {'schema-examples (3.12)'}
    with pytest.raises(TypeError):
        execution.required_checks()
    for invalid in (None, True, '', 'unknown'):
        with pytest.raises(ValueError, match='CI workflow event'):
            execution.required_checks(invalid)
