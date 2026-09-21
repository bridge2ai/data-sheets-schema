"""Persistent protocol delivery without changing the scientific instrument (#2164)."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import contract_context, native, prepare, registration, transport
from audit_controls.test_context_preparation import ancestry, accepted_audit
from budgeted_cborg import BudgetStop
from data_sheets_schema import api_runner
from evaluation_controls import registration as evaluation
from finalization_controls import native as final_native, prepare as final_prepare, registration as final_registration
import run_api_canary

KEY = 'audit_contract_context'
SELECTION = {'kind': 'persistent_protocol_v1'}


def selected(value=SELECTION, **changes):
    return {'kind': 'd4d_native_audit_continuation', 'protocol_version': 3,
            'render_version': 14, KEY: deepcopy(value), **changes}


@pytest.mark.parametrize('value', [None, True, False, [], 'persistent_protocol_v1', {},
                                  {'kind': 'unknown'}, {**SELECTION, 'extra': True}])
def test_bad_selector_stops_before_runtime_and_transport(value, tmp_path, monkeypatch):
    m = selected(value)
    monkeypatch.setattr(native, 'build_policy', lambda *a: pytest.fail('native policy constructed'))
    monkeypatch.setattr(transport, 'Client', lambda **k: pytest.fail('HTTP client constructed'))
    with pytest.raises(BudgetStop):
        contract_context.enabled(m)
    with pytest.raises(BudgetStop):
        native.execute_job(SimpleNamespace(manifest=m, job={}, attempt=tmp_path))
    with pytest.raises(BudgetStop):
        transport.provider_clients(m, 'synthetic-unused-key')
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('changes', [
    {'kind': 'd4d_native_finalization'}, {'kind': 'd4d_evaluation_registration'},
    {'protocol_version': True}, {'protocol_version': 3.0}, {'protocol_version': 2},
    {'render_version': 14.0}, {'render_version': 13},
])
def test_selector_requires_the_exact_native_audit_instrument(changes):
    with pytest.raises(BudgetStop):
        contract_context.enabled(selected(**changes))


@pytest.mark.parametrize('value', [None, True, SELECTION])
def test_other_real_entrypoints_reject_presence_before_other_checks(value, tmp_path, monkeypatch):
    m = {KEY: value}
    path = tmp_path / 'registration.json'
    path.write_text(json.dumps(m))
    with pytest.raises(BudgetStop, match='audit-only'):
        run_api_canary.verify(m, path, 'unused')
    with pytest.raises(BudgetStop, match='audit-only'):
        final_registration.validate_registration(path)
    with pytest.raises(BudgetStop, match='audit-only'):
        evaluation.verify_manifest(m, path, 'unused')
    # Even a forged audit kind cannot route the selector through Phase 4.
    monkeypatch.setattr(final_native, 'build_policy', lambda *a: pytest.fail('Phase 4 policy constructed'))
    with pytest.raises(BudgetStop, match='native audit controller'):
        final_native.execute_job(SimpleNamespace(manifest=selected(value), job={}, attempt=tmp_path))
    assert [p.name for p in tmp_path.iterdir()] == ['registration.json']


@pytest.mark.parametrize('value', [None, 0, 1, 'true', {}])
def test_preparation_flag_is_a_boolean_and_refused_without_side_effects(ancestry, tmp_path, value):
    destination = tmp_path / 'bad'
    with pytest.raises(BudgetStop):
        prepare.prepare(**ancestry[0], destination=destination, persistent_audit_contract=value)
    assert not destination.exists()


@pytest.mark.parametrize('recovery, staged', [(False, False), (True, False), (True, True)])
def test_real_preparation_keeps_exact_protocol_in_system_without_changing_science(
        ancestry, tmp_path, recovery, staged):
    args = dict(ancestry[0], context_recovery=recovery, staged_audit_output=staged)
    old_path = prepare.prepare(**args, destination=tmp_path / 'old')
    new_path = prepare.prepare(**args, destination=tmp_path / 'new', persistent_audit_contract=True)
    old = registration.validate_registration(old_path)
    new = registration.validate_registration(new_path)
    assert KEY not in old and new[KEY] == SELECTION
    old_system = Path(old['job']['system_prompt']).read_bytes()
    new_system = Path(new['job']['system_prompt']).read_bytes()
    protocol = Path(new['inputs']['protocol']).read_bytes()
    shared = api_runner.evidence_phase_contract('audit', 14).encode()
    assert new_system.count(protocol) == 1 and new_system.count(shared) == 1
    assert protocol not in old_system and shared not in old_system
    # The same manifest without selection must replay the historical rendering.
    omitted = deepcopy(new)
    del omitted[KEY]
    expected_old = old_system.replace(str(old_path.parent).encode(), str(new_path.parent).encode())
    if recovery:
        expected_old = expected_old.replace(old['context_recovery']['index']['sha256'].encode(),
                                            new['context_recovery']['index']['sha256'].encode())
    assert prepare.render_system(omitted).encode() == expected_old
    # Delivery changes, but the scientific instruction and carried bytes do not.
    assert Path(new['job']['instruction']).read_bytes() == Path(old['job']['instruction']).read_bytes().replace(
        str(old_path.parent).encode(), str(new_path.parent).encode())
    for role, path in new['inputs'].items():
        assert Path(path).read_bytes() == Path(old['inputs'][role]).read_bytes()
    module = str(BASE / 'audit_controls/contract_context.py')
    assert new['pinned_files'][module] == registration.sha(module)
    assert module not in old['pinned_files']
    assert not Path(new['budget']['ledger_path']).exists()
    assert not Path(new['job']['attempt_dir']).exists()
    assert ancestry[2] == {name: Path(name).read_bytes() for name in ancestry[2]}
    plan = json.loads((new_path.parent / 'offline_plan.json').read_text())
    assert plan[KEY] == SELECTION


def test_system_contract_cannot_be_removed_and_repinned(ancestry, tmp_path):
    path = prepare.prepare(**ancestry[0], destination=tmp_path / 'selected', persistent_audit_contract=True)
    m = registration.read_json(path)
    system = Path(m['job']['system_prompt'])
    protocol = Path(m['inputs']['protocol']).read_bytes()
    system.write_bytes(system.read_bytes().replace(protocol, b''))
    m['pinned_files'][str(system)] = registration.sha(system)
    path.write_text(json.dumps(m))
    with pytest.raises(BudgetStop):
        registration.validate_registration(path)


def test_phase4_preparation_preserves_historical_pin_but_drops_active_selector(ancestry, tmp_path, monkeypatch):
    # Synthetic ancestry deliberately stubs acceptance/ownership in the shared fixture.
    # Check the real Phase 4 preparer's field selection, never create a real acceptance.
    actual_prepare = prepare.prepare
    monkeypatch.setattr(prepare, 'prepare', lambda **kwargs: actual_prepare(
        **kwargs, persistent_audit_contract=True))
    audit_path, acceptance = accepted_audit(ancestry, tmp_path / 'accepted')
    assert registration.read_json(audit_path)[KEY] == SELECTION
    path = final_prepare.prepare(accepted_audit_registration=audit_path, acceptance=acceptance,
        destination=tmp_path / 'final', job_id='synthetic_final', repository=ancestry[0]['repository'])
    final = final_registration.read_json(path)
    assert KEY not in final
    assert final['pinned_files'][str(audit_path)] == registration.sha(audit_path)
