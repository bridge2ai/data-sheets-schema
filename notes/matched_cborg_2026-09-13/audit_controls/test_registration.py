"""Accounting ancestry and exclusive continuation admission, without provider calls."""
import copy
from decimal import Decimal
import json
from pathlib import Path
import sys

import pytest
from filelock import FileLock, Timeout

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from audit_controls import registration as r


def save(path, value):
    Path(path).write_text(json.dumps(value))


@pytest.fixture
def accounting(tmp_path):
    root = tmp_path.resolve()
    parent = root / 'parent'; parent.mkdir()
    source = parent / 'billing.json'
    reg = parent / 'registration.json'
    result = parent / 'result.json'; save(result, {'status': 'stopped'})
    generation = {'budget': {'ledger_path': str(source)}, 'generation': {'jobs': [{'id': 'frozen'}]}}
    save(reg, generation)
    attempt = r.attempt_identity(r.sha(reg), 'frozen')
    old = {'manifest_sha256': r.sha(reg), 'additional_cap_usd': '400', 'attempt_cap_usd': '5',
        'requests': [{'id': 'earlier', 'attempt': 'old:run', 'status': 'settled', 'cost_usd': '2.1', 'usage': {'output_tokens': 1}},
                     {'id': 'interrupted', 'attempt': attempt, 'status': 'pending', 'reserved_usd': '3.5'}]}
    save(source, old)
    receiptpath = root / 'confirmed.json'
    receipt = {'kind': 'user_confirmed_provider_charge_reconciliation',
        'source_registration_sha256': r.sha(reg), 'source_ledger_sha256': r.sha(source),
        'stopped_result_sha256': r.sha(result), 'user_confirmation': {'exact_response': 'confirmed', 'quoted_request': 'exact request'},
        'request_id': 'interrupted', 'attempt': attempt, 'previous_reservation_usd': '3.5',
        'confirmed_complete_charge_usd': '0.08768875', 'recorded_at': '2026-09-18T00:00:00Z',
        'provider_observation_sha256': 'observed'}
    save(receiptpath, receipt)
    checkpoint = copy.deepcopy(old)
    checkpoint['requests'][1].update(status='settled', cost_usd='0.08768875', settled_at=receipt['recorded_at'],
        settlement_basis='user_confirmed_provider_accounting', reconciliation_receipt_sha256=r.sha(receiptpath),
        provider_observation_sha256='observed', provider_usage_is_final=False, generation_outcome='stopped')
    checkpoint['reconciled_from'] = {'checkpoint_sha256': r.sha(source), 'receipt_sha256': r.sha(receiptpath),
        'request_id': 'interrupted', 'previous_status': 'pending', 'confirmed_charge_usd': '0.08768875',
        'generation_completed': False}
    ckpt = root / 'reconciled.json'; save(ckpt, checkpoint)
    dest = root / 'audit'; dest.mkdir()
    manifest = {'parent': {'registration': str(reg), 'repository': str(parent), 'job_id': 'frozen',
        'result': str(result), 'reconciliation_receipt': str(receiptpath), 'reconciled_checkpoint': str(ckpt)},
        'job': {'id': 'new_audit'}, 'budget': {'additional_usd': 400, 'per_attempt_usd': 5,
            'per_job_attempt_usd': {'new_audit': 20}, 'ledger_path': str(dest / 'billing.json'),
            'continuation': {'checkpoint': str(ckpt), 'sha256': r.sha(ckpt), 'cost_usd': '2.18768875'}},
        'sequence_state': str(parent / 'audit_sequence.json'), 'pinned_files': {str(ckpt): r.sha(ckpt)}}
    return manifest, source, receiptpath, ckpt, dest / 'registration.json'


def test_reconciliation_preserves_original_and_every_unconfirmed_field(accounting):
    m, source, _, checkpoint, _ = accounting
    before = source.read_bytes()
    assert r.validate_reconciliation(m) == r.read_json(checkpoint)
    assert source.read_bytes() == before


@pytest.mark.parametrize('change', ['earlier_cost', 'removed_earlier', 'new_row', 'changed_attempt',
    'settlement_cost', 'fake_usage', 'generation_accepted', 'changed_top_budget', 'source_field', 'duplicate_row', 'boolean_usage'])
def test_reconciliation_rejects_unconfirmed_changes(accounting, change):
    m, _, _, checkpoint, _ = accounting
    value = r.read_json(checkpoint)
    if change == 'earlier_cost': value['requests'][0]['cost_usd'] = '1.0'
    elif change == 'removed_earlier': value['requests'].pop(0)
    elif change == 'new_row': value['requests'].append({'id': 'new', 'cost_usd': '0', 'status': 'settled'})
    elif change == 'changed_attempt': value['requests'][1]['attempt'] = 'another'
    elif change == 'settlement_cost': value['requests'][1]['cost_usd'] = '0'
    elif change == 'fake_usage': value['requests'][1]['provider_usage_is_final'] = True
    elif change == 'generation_accepted': value['requests'][1]['generation_outcome'] = 'completed'
    elif change == 'changed_top_budget': value['additional_cap_usd'] = '800'
    elif change == 'source_field': value['requests'][1]['reserved_usd'] = '4'
    elif change == 'duplicate_row': value['requests'].append(value['requests'][0])
    elif change == 'boolean_usage': value['requests'][0]['usage']['output_tokens'] = True
    save(checkpoint, value)
    with pytest.raises(r.BudgetStop): r.validate_reconciliation(m)


@pytest.mark.parametrize('field,value', [('request_id','unrelated'),('attempt','unrelated'),
    ('confirmed_complete_charge_usd','NaN'),('confirmed_complete_charge_usd','-1'),
    ('confirmed_complete_charge_usd','4'),('source_registration_sha256','unrelated'),
    ('stopped_result_sha256','unrelated'),('previous_reservation_usd','4')])
def test_confirmation_must_match_the_source_reservation(accounting, field, value):
    m, _, receipt, _, _ = accounting
    record = r.read_json(receipt); record[field] = value; save(receipt, record)
    with pytest.raises(r.BudgetStop): r.validate_reconciliation(m)


def test_audit_cap_binds_exact_attempt_and_carries_charges(accounting):
    m, source, _, checkpoint, reg = accounting
    original = checkpoint.read_bytes()
    ledger = r.open_audit_ledger(m, reg, 'new-registration')
    assert ledger.limit_for_attempt('new-registration:new_audit') == Decimal(20)
    assert ledger.limit_for_attempt('other:new_audit') == Decimal(5)
    state = r.read_json(ledger.path)
    assert state['requests'] == r.read_json(checkpoint)['requests']
    assert checkpoint.read_bytes() == original
    with pytest.raises(r.BudgetStop): ledger.reserve('new-registration:new_audit', 21, 'request')
    assert r.read_json(source)['requests'][-1]['status'] == 'pending'


def test_changed_checkpoint_refuses_before_new_ledger(accounting):
    m, _, _, checkpoint, reg = accounting
    checkpoint.write_text(checkpoint.read_text() + '\n')
    with pytest.raises(r.BudgetStop): r.open_audit_ledger(m, reg, 'new')
    assert not Path(m['budget']['ledger_path']).exists()


def test_sequence_consumes_identity_and_holds_lock(accounting):
    m, _, _, _, reg = accounting
    with r.sequence_guard(m, 'new'):
        with pytest.raises(Timeout):
            with FileLock(m['sequence_state'] + '.lock', timeout=0): pass
        r.open_audit_ledger(m, reg, 'new')
    with pytest.raises(r.BudgetStop, match='already consumed'):
        with r.sequence_guard(m, 'new'): pass


def successor(m, reg):
    first = copy.deepcopy(m)
    with r.sequence_guard(first, 'first'):
        r.open_audit_ledger(first, reg, 'first')
    new = copy.deepcopy(first)
    prior = first['budget']['ledger_path']
    new['budget']['continuation'] = {'checkpoint': prior, 'sha256': r.sha(prior), 'cost_usd': '2.18768875'}
    new['budget']['ledger_path'] = str(reg.parent / 'next' / 'billing.json')
    return new, Path(prior)


def test_sequence_accepts_settled_tip_and_rejects_fork(accounting):
    m, _, _, _, reg = accounting
    next_m, _ = successor(m, reg)
    with pytest.raises(r.BudgetStop, match='billing fork'):
        with r.sequence_guard(m, 'fork'): pass
    with r.sequence_guard(next_m, 'second'): pass


@pytest.mark.parametrize('mutation', ['pending', 'wrong_identity', 'wrong_source'])
def test_sequence_rejects_unresolved_or_unrelated_tip(accounting, mutation):
    m, _, _, _, reg = accounting
    next_m, previous = successor(m, reg)
    value = r.read_json(previous)
    if mutation == 'pending': value['requests'][-1]['status'] = 'pending'
    if mutation == 'wrong_identity': value['manifest_sha256'] = 'different'
    if mutation == 'wrong_source':
        state = r.read_json(m['sequence_state']); state['source_registration_sha256'] = 'different'; save(m['sequence_state'], state)
    save(previous, value)
    next_m['budget']['continuation']['sha256'] = r.sha(previous)
    with pytest.raises(r.BudgetStop):
        with r.sequence_guard(next_m, 'second'): pass


def test_path_alias_and_duplicate_json_are_refused(tmp_path):
    target = tmp_path/'target'; target.write_text('x')
    alias = tmp_path/'alias'; alias.symlink_to(target)
    with pytest.raises(r.BudgetStop): r.canonical_path(str(alias))
    with pytest.raises(ValueError): r.strict_json('{"cost":1,"cost":2}')
    with pytest.raises(ValueError): r.strict_json('{"cost":NaN}')


def test_copied_confirmation_cannot_fork_sequence(accounting, tmp_path):
    m, _, receipt, checkpoint, reg = accounting
    with r.sequence_guard(m, 'first'):
        r.open_audit_ledger(m, reg, 'first')
    copied = copy.deepcopy(m)
    elsewhere = tmp_path / 'copied'; elsewhere.mkdir()
    for key, source in [('reconciliation_receipt', receipt), ('reconciled_checkpoint', checkpoint)]:
        destination = elsewhere / source.name; destination.write_bytes(source.read_bytes())
        copied['parent'][key] = str(destination)
    copied['sequence_state'] = str(elsewhere / 'audit_sequence.json')
    with pytest.raises(r.BudgetStop, match='immutable source ledger'):
        with r.sequence_guard(copied, 'copied'): pass


def test_json_overflow_and_invalid_unicode_refused():
    with pytest.raises(ValueError): r.strict_json('{"cost":1e999}')
    with pytest.raises(UnicodeError): r.strict_json('"\\ud800"')
