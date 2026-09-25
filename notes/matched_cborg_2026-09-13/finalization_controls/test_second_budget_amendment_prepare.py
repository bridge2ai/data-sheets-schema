"""Synthetic accepted audit -> real Phase4 preparation and shared accounting.

Historical scientific acceptance is invented, as in the existing foundation
fixtures. Current financial proof, complete ledger, ownership, registration,
rendering and budget inheritance are real; no provider is constructed.
"""
from copy import deepcopy
from pathlib import Path

import pytest

import budget_amendment as amendment
import continuation_sequence as sequence
from budgeted_cborg import BudgetStop, attempt_identity
from audit_controls import registration as audit_registration
from audit_controls.test_second_budget_amendment_registration import (
    ancestry, second_approved, prepare_second, save, reference, unchanged)
from . import prepare, registration

REAL_SEQUENCE_VALIDATE = sequence._validate
REAL_SEAL = sequence.seal_document


@pytest.fixture
def second_phase4(second_approved, tmp_path, monkeypatch):
    c = second_approved
    increased_path, increased = prepare_second(c, tmp_path/'first-second-increase')
    increased_sha = audit_registration.sha(increased_path)
    with audit_registration.sequence_guard(increased, increased_sha):
        increased_ledger = audit_registration.open_audit_ledger(increased, increased_path, increased_sha)
        ticket = increased_ledger.reserve(attempt_identity(increased_sha, increased['job']['id']),
                                         '.02', 'synthetic-before-same-cap-successor')
        increased_ledger.settle(ticket, '.01', response_sha256='synthetic-response', usage={})
    audit_path, audit = prepare_second(c, tmp_path/'accepted-same-cap-audit',
                                      continuation_checkpoint=increased_ledger.path)
    identity = audit_registration.sha(audit_path)
    with audit_registration.sequence_guard(audit, identity):
        ledger = audit_registration.open_audit_ledger(audit, audit_path, identity)
        ticket = ledger.reserve(attempt_identity(identity, audit['job']['id']), '.02', 'synthetic-audit')
        ledger.settle(ticket, '.01', response_sha256='synthetic-audit-response', usage={})
    output = Path(audit['job']['audit_path']); output.parent.mkdir(parents=True)
    output.write_bytes(Path(c['example']['job']['audit_path']).read_bytes())
    artifacts = {str(output): audit_registration.sha(output)}
    result = save(Path(audit['job']['attempt_dir'])/'result.json', {
        'scope': 'phase3_audit_only', 'job_id': audit['job']['id'], 'registration_sha256': identity,
        'status': 'completed_pending_independent_review', 'unresolved_requests': [],
        'audit_path': str(output), 'audit_sha256': artifacts[str(output)],
        'validation': {'checked': True, 'passed': True, 'job_id': audit['job']['id'],
                       'audit_sha256': artifacts[str(output)], 'findings': [], 'errors': []},
        'runtime': {'exit_code': 0, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0}})
    acceptance = save(tmp_path/'synthetic-audit-acceptance.json', {'verdict': 'accept',
        'registration_sha256': identity, 'result_sha256': audit_registration.sha(result),
        'ledger_sha256': audit_registration.sha(ledger.path), 'artifacts': artifacts})
    # Undo only the old fixture's foundation stubs; current shared accounting
    # and closure validation must run, without executing a scientific checker.
    monkeypatch.setattr(sequence, '_validate', REAL_SEQUENCE_VALIDATE)
    monkeypatch.setattr(prepare, 'seal_document', REAL_SEAL)
    path = prepare.prepare(accepted_audit_registration=audit_path, acceptance=acceptance,
        destination=tmp_path/'phase4', job_id='synthetic_final', repository=c['args']['repository'])
    manifest = registration.validate_registration(path)
    return {'case': c, 'path': path, 'manifest': manifest, 'audit': audit,
            'audit_path': audit_path, 'audit_ledger': Path(ledger.path),
            'acceptance': acceptance, 'state': c['state']}


def test_second_amendment_real_phase4_preparation_preserves_authority(second_phase4):
    f = second_phase4; m = f['manifest']; c = f['case']
    assert m['budget_amendment'] == c['proof']
    assert m['budget']['additional_usd'] == '600' and m['budget']['per_attempt_usd'] == '5'
    assert m['budget']['per_job_attempt_usd'] == {'synthetic_final': '20'}
    assert amendment.paths(m) <= registration.required_paths(m)
    assert not Path(m['budget']['ledger_path']).exists()
    assert not Path(m['job']['attempt_dir']).exists()
    assert not (f['path'].parent/'sequence_claim').exists()
    assert 'native_history_control' not in m and 'audit_batches' not in m
    assert audit_registration.read_json(f['path'].parent/'preparation.json')['provider_calls'] == 0
    unchanged(c, state=False)


def test_real_phase4_handoff_imports_the_complete600_history_without_credit(second_phase4):
    f = second_phase4; m = f['manifest']; path = f['path']
    previous = f['audit_ledger'].read_bytes()
    with sequence.owned_sequence(m, path, sequence.sha(path)) as owner:
        state = sequence.read(owner.ledger.path)
        assert state['additional_cap_usd'] == '600'
        assert state['requests'] == sequence.read(f['audit_ledger'])['requests']
        assert len(state['requests']) == 259 and 'budget_amendment_sha256' not in state['continued_from']
        ticket = owner.reserve(sequence.sha(path)+':synthetic_final', '.02', 'synthetic-phase4')
        owner.ledger.settle(ticket, '.01', response_sha256='synthetic-phase4-response', usage={})
    with sequence.owned_sequence(m, path, sequence.sha(path)) as reopened:
        assert len(sequence.read(reopened.ledger.path)['requests']) == 260
    assert f['audit_ledger'].read_bytes() == previous
    unchanged(f['case'], state=False)


@pytest.mark.parametrize('damage', ['drop_second', 'replace_with_first', 'unpin_prior_authority', 'stale_owner'])
def test_real_phase4_handoff_refuses_lost_proof_or_stale_owner_before_spend(second_phase4, damage):
    f = second_phase4; m = deepcopy(f['manifest']); path = f['path']
    if damage == 'drop_second': m.pop('budget_amendment')
    elif damage == 'replace_with_first': m['budget_amendment'] = deepcopy(f['case']['first'])
    elif damage == 'unpin_prior_authority': m['pinned_files'].pop(f['case']['first']['authorization']['path'])
    else: save(f['state'], {'synthetic': 'another current owner'})
    save(path, m); before = f['state'].read_bytes()
    with pytest.raises(BudgetStop):
        with sequence.owned_sequence(m, path, sequence.sha(path)):
            pytest.fail('invalid handoff reached accounting')
    assert f['state'].read_bytes() == before
    assert not Path(m['budget']['ledger_path']).exists()
