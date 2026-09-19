"""Explicit full-reservation budget debits never invent provider accounting."""
from copy import deepcopy
from decimal import Decimal
import hashlib
from pathlib import Path

import pytest

from . import registration as r
from .test_registration import accounting, stopped_audit, save, repin


def checkpoint_for(source, receipt_path, receipt):
    checkpoint = r.read_json(source)
    row = next(row for row in checkpoint['requests'] if row['status'] == 'pending')
    row.update(status='settled', cost_usd=receipt['budget_debit_usd'], settled_at=receipt['recorded_at'],
        settlement_basis='user_authorized_full_reservation_debit', reconciliation_receipt_sha256=r.sha(receipt_path),
        accounting_observation_sha256=receipt['accounting_observation_sha256'],
        provider_charge_confirmed=False, provider_charge_usd=None, provider_usage_is_final=False,
        released_excess_reservation_usd='0', source_attempt_kind='phase3_audit_only', source_attempt_outcome='stopped')
    checkpoint['reconciled_from'] = {'checkpoint_sha256': r.sha(source), 'receipt_sha256': r.sha(receipt_path),
        'request_id': row['id'], 'previous_status': 'pending', 'budget_debit_usd': receipt['budget_debit_usd'],
        'settlement_basis': 'user_authorized_full_reservation_debit', 'provider_charge_confirmed': False,
        'source_attempt_completed': False}
    return checkpoint


@pytest.fixture
def exception_case(stopped_audit):
    m, source, receipt_path, checkpoint, registration = stopped_audit
    old = r.read_json(source);row = old['requests'][-1]
    row['request_sha256'] = hashlib.sha256(b'synthetic interrupted audit request').hexdigest()
    # Original partial observations survive; they are never relabelled final.
    row['partial_usage'] = {'input_tokens': 17, 'output_tokens': 1}
    save(source, old);repin(m, source)
    result_path = Path(m['budget']['continuation']['reconciliation']['result'])
    result = r.read_json(result_path)
    result['runtime'] = {'proxy_shutdown_complete': True, 'unfinished_handlers': 0}
    save(result_path, result);repin(m, result_path)
    previous = r.read_json(receipt_path)
    receipt = {key: previous[key] for key in ('source_attempt_kind','source_registration_sha256',
        'request_id','attempt','previous_reservation_usd','recorded_at')}
    receipt.update(kind='user_authorized_full_reservation_debit', source_ledger_sha256=r.sha(source),
        stopped_result_sha256=r.sha(result_path), request_sha256=row['request_sha256'],
        user_authorization={'exact_response':'Book the full reservation for this request.',
                            'quoted_request':'The exact synthetic request retains its stated reservation.'},
        budget_debit_usd=row['reserved_usd'], provider_charge_confirmed=False, provider_charge_usd=None,
        provider_usage_is_final=False, released_excess_reservation_usd='0',
        accounting_observation_sha256=hashlib.sha256(b'synthetic unresolved accounting observation').hexdigest(),
        source_attempt_completed=False, scientific_acceptance=False)
    save(receipt_path, receipt);repin(m, receipt_path)
    save(checkpoint, checkpoint_for(source, receipt_path, receipt));repin(m, checkpoint)
    m['budget']['continuation']['cost_usd'] = str(sum(
        (Decimal(row['cost_usd']) for row in r.read_json(checkpoint)['requests']), Decimal(0)))
    return m, source, receipt_path, checkpoint, registration


def test_full_debit_advances_once_preserves_originals_and_does_not_claim_provider_fee(exception_case):
    m, source, receipt, checkpoint, registration = exception_case
    preserved = {p: p.read_bytes() for p in (source, receipt, checkpoint)}
    original = r.read_json(source);row = original['requests'][-1]
    assert r.validate_audit_reconciliation(m) == r.read_json(checkpoint)
    with r.sequence_guard(m, 'exception-successor'):
        ledger = r.open_audit_ledger(m, registration, 'exception-successor')
    carried = r.read_json(ledger.path)
    assert carried['requests'][:-1] == original['requests'][:-1]
    debit = carried['requests'][-1]
    assert Decimal(debit['cost_usd']) == Decimal(row['reserved_usd'])
    assert debit['settlement_basis'] == 'user_authorized_full_reservation_debit'
    assert debit['partial_usage'] == row['partial_usage']
    assert debit['provider_charge_confirmed'] is False and debit['provider_charge_usd'] is None
    assert debit['provider_usage_is_final'] is False and debit['source_attempt_outcome'] == 'stopped'
    assert debit['released_excess_reservation_usd'] == '0'
    assert 'confirmed_complete_charge_usd' not in debit and 'confirmed_charge_usd' not in debit
    assert carried['additional_cap_usd'] == original['additional_cap_usd']
    assert carried['attempt_cap_usd'] == original['attempt_cap_usd']
    assert m['budget']['per_job_attempt_usd'] == {'new_audit': 20}
    available_before = Decimal(original['additional_cap_usd']) - sum((
        Decimal(row['cost_usd'] if row['status'] == 'settled' else row['reserved_usd'])
        for row in original['requests']), Decimal(0))
    available_after = Decimal(carried['additional_cap_usd']) - sum((
        Decimal(row['cost_usd']) for row in carried['requests']), Decimal(0))
    assert available_after == available_before  # No previously reserved capacity is released.
    assert all(p.read_bytes() == raw for p, raw in preserved.items())
    assert r.read_json(source)['requests'][-1]['status'] == 'pending'
    with pytest.raises(r.BudgetStop, match='already consumed'):
        with r.sequence_guard(m, 'exception-successor'): pass
    with pytest.raises(r.BudgetStop, match='current sequence tip'):
        with r.sequence_guard(m, 'unregistered-retry'): pass


@pytest.mark.parametrize('field,value', [
    ('budget_debit_usd','0'), ('budget_debit_usd','2.69'), ('budget_debit_usd','2.71'),
    ('budget_debit_usd','NaN'), ('budget_debit_usd','Infinity'), ('budget_debit_usd',True),
    ('released_excess_reservation_usd','0.01'), ('released_excess_reservation_usd','NaN'),
    ('released_excess_reservation_usd',False), ('provider_charge_confirmed',True),
    ('provider_charge_confirmed',0), ('provider_charge_usd','2.7'), ('provider_usage_is_final',True),
    ('provider_usage_is_final',0), ('request_id','other'), ('request_sha256','0'*64),
    ('request_sha256','short'), ('attempt','other'), ('previous_reservation_usd','2.69'),
    ('source_registration_sha256','0'*64), ('source_ledger_sha256','0'*64),
    ('stopped_result_sha256','0'*64), ('source_attempt_kind','generation'),
    ('accounting_observation_sha256','short'), ('recorded_at',' '),
    ('user_authorization',{'exact_response':True,'quoted_request':'x'}),
    ('user_authorization',{'exact_response':'yes','quoted_request':' '}), ('user_authorization',None),
    ('confirmed_complete_charge_usd','2.7'), ('confirmed_charge_usd','2.7'),
    ('user_confirmation',{'exact_response':'yes','quoted_request':'x'}),
    ('provider_observation_sha256','0'*64), ('source_attempt_completed',True), ('scientific_acceptance',True),
])
def test_exception_receipt_rejects_underfunding_false_confirmation_and_wrong_identity(exception_case, field, value):
    m, source, receipt_path, checkpoint, registration = exception_case
    receipt = r.read_json(receipt_path);receipt[field] = value
    save(receipt_path, receipt);repin(m, receipt_path)
    # Coherently rebind receipt references so a stale hash cannot cause the test's rejection.
    changed = r.read_json(checkpoint)
    changed['requests'][-1]['reconciliation_receipt_sha256'] = r.sha(receipt_path)
    changed['reconciled_from']['receipt_sha256'] = r.sha(receipt_path)
    if field == 'budget_debit_usd':
        changed['requests'][-1]['cost_usd'] = value;changed['reconciled_from']['budget_debit_usd'] = value
    save(checkpoint, changed);repin(m, checkpoint)
    before = Path(m['sequence_state']).read_bytes();old = source.read_bytes()
    with pytest.raises(r.BudgetStop):
        with r.sequence_guard(m, 'must-not-advance'):pytest.fail('invalid exception advanced sequence')
    assert Path(m['sequence_state']).read_bytes() == before and source.read_bytes() == old
    assert not Path(m['budget']['ledger_path']).exists()


@pytest.mark.parametrize('field', ['provider_charge_confirmed','provider_charge_usd','provider_usage_is_final',
    'released_excess_reservation_usd','budget_debit_usd','request_sha256','accounting_observation_sha256',
    'user_authorization'])
def test_exception_cannot_omit_its_truthful_basis(exception_case, field):
    m, _, receipt_path, _, _ = exception_case
    receipt = r.read_json(receipt_path);receipt.pop(field);save(receipt_path, receipt);repin(m, receipt_path)
    with pytest.raises(r.BudgetStop):r.validate_audit_reconciliation(m)


@pytest.mark.parametrize('damage', ['no_runtime','shutdown_false','shutdown_integer','unfinished',
    'boolean_handlers','never_initialized','untyped_initialized'])
def test_exception_requires_closed_source_runtime_even_when_rebound(exception_case, damage):
    m, source, receipt_path, checkpoint, _ = exception_case
    result_path = Path(m['budget']['continuation']['reconciliation']['result']);result = r.read_json(result_path)
    if damage == 'no_runtime':result.pop('runtime')
    elif damage == 'shutdown_false':result['runtime']['proxy_shutdown_complete'] = False
    elif damage == 'shutdown_integer':result['runtime']['proxy_shutdown_complete'] = 1
    elif damage == 'unfinished':result['runtime']['unfinished_handlers'] = 1
    elif damage == 'boolean_handlers':result['runtime']['unfinished_handlers'] = False
    elif damage == 'never_initialized':result['runtime']['proxy_initialized'] = False
    else:result['runtime']['proxy_initialized'] = 1
    save(result_path, result);repin(m, result_path)
    receipt = r.read_json(receipt_path);receipt['stopped_result_sha256'] = r.sha(result_path)
    save(receipt_path, receipt);repin(m, receipt_path)
    save(checkpoint, checkpoint_for(source, receipt_path, receipt));repin(m, checkpoint)
    before = Path(m['sequence_state']).read_bytes()
    with pytest.raises(r.BudgetStop, match='closed runtime'):
        with r.sequence_guard(m, 'must-not-advance'):pytest.fail('open handler admitted')
    assert Path(m['sequence_state']).read_bytes() == before


@pytest.mark.parametrize('damage', ['earlier_cost','prior_usage','removed_row','new_row','budget','stops',
    'fee_confirmed','fee_known','partial_usage','confirmed_field','completed','released','provenance'])
def test_exception_checkpoint_cannot_change_history_or_invent_fee_after_repin(exception_case, damage):
    m, source, _, checkpoint, _ = exception_case
    value = r.read_json(checkpoint);row = value['requests'][-1]
    if damage == 'earlier_cost':value['requests'][0]['cost_usd'] = '0'
    elif damage == 'prior_usage':value['requests'][0]['usage']['output_tokens'] = True
    elif damage == 'removed_row':value['requests'].pop(0)
    elif damage == 'new_row':value['requests'].append(deepcopy(row))
    elif damage == 'budget':value['additional_cap_usd'] = '800'
    elif damage == 'stops':value['stopped_attempts'] = []
    elif damage == 'fee_confirmed':row['provider_charge_confirmed'] = True
    elif damage == 'fee_known':row['provider_charge_usd'] = row['cost_usd']
    elif damage == 'partial_usage':row['partial_usage']['output_tokens'] = 2
    elif damage == 'confirmed_field':row['confirmed_complete_charge_usd'] = row['cost_usd']
    elif damage == 'completed':row['source_attempt_outcome'] = 'completed'
    elif damage == 'released':row['released_excess_reservation_usd'] = '0.01'
    else:value['reconciled_from']['confirmed_charge_usd'] = row['cost_usd']
    save(checkpoint, value);repin(m, checkpoint)
    before = Path(m['sequence_state']).read_bytes();source_before = source.read_bytes()
    with pytest.raises(r.BudgetStop, match='unconfirmed history'):
        with r.sequence_guard(m, 'must-not-advance'):pytest.fail('altered history admitted')
    assert Path(m['sequence_state']).read_bytes() == before and source.read_bytes() == source_before


def test_exception_cannot_resolve_multiple_pending_requests_even_when_source_rebound(exception_case):
    m, source, receipt_path, checkpoint, _ = exception_case
    value = r.read_json(source);duplicate = deepcopy(value['requests'][-1]);duplicate['id'] = 'another-pending'
    value['requests'].append(duplicate);save(source, value);repin(m, source)
    receipt = r.read_json(receipt_path);receipt['source_ledger_sha256'] = r.sha(source)
    save(receipt_path, receipt);repin(m, receipt_path)
    with pytest.raises(r.BudgetStop, match='exactly one pending'):r.validate_audit_reconciliation(m)
