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


@pytest.mark.parametrize('value', [None, True, False, 0, -1, 1.5, '3600000', float('inf'), 10800001])
def test_native_timeout_rejects_invalid_or_unbounded_values(value):
    manifest = {'native_runtime': {'api_timeout_ms': value}, 'job': {'deadline_seconds': 10800}}
    with pytest.raises(r.BudgetStop, match='native API timeout'):
        r.native_api_timeout(manifest)


def test_native_timeout_preserves_omission_and_accepts_a_bounded_integer():
    manifest = {'native_runtime': {}, 'job': {'deadline_seconds': 10800}}
    assert r.native_api_timeout(manifest) is None
    manifest['native_runtime']['api_timeout_ms'] = 3600000
    assert r.native_api_timeout(manifest) == 3600000


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


@pytest.fixture
def stopped_audit(accounting):
    """A generation checkpoint followed by one stopped, separately billed audit."""
    m, _, _, baseline, reg = accounting
    first = copy.deepcopy(m)
    first.update(kind='d4d_native_audit_continuation')
    first['job']['attempt_dir'] = str(reg.parent / 'attempts' / first['job']['id'])
    save(reg, first)
    source_sha = r.sha(reg)
    with r.sequence_guard(first, source_sha):
        ledger = r.open_audit_ledger(first, reg, source_sha)
        request_id = ledger.reserve(r.attempt_identity(source_sha, first['job']['id']), Decimal('2.7'), 'audit')
        ledger.stop_attempt(r.attempt_identity(source_sha, first['job']['id']), 'synthetic interrupted audit')
    source = Path(first['budget']['ledger_path'])
    old = r.read_json(source)
    row = old['requests'][-1]
    assert row['id'] == request_id
    result = Path(first['job']['attempt_dir']) / 'result.json'
    result.parent.mkdir(parents=True)
    save(result, {'registration_sha256': source_sha, 'job_id': first['job']['id'],
        'scope': 'phase3_audit_only', 'status': 'stopped', 'unresolved_requests': [row['id']]})
    receipt = reg.parent / 'confirmed.json'
    confirmation = {'kind': 'user_confirmed_provider_charge_reconciliation',
        'source_attempt_kind': 'phase3_audit_only', 'source_registration_sha256': source_sha,
        'source_ledger_sha256': r.sha(source), 'stopped_result_sha256': r.sha(result),
        'user_confirmation': {'exact_response': 'approved', 'quoted_request': 'Confirm match and complete charge'},
        'request_id': row['id'], 'attempt': row['attempt'], 'previous_reservation_usd': row['reserved_usd'],
        'confirmed_complete_charge_usd': '0.08', 'recorded_at': '2026-09-18T01:00:00Z',
        'provider_observation_sha256': 'observation'}
    save(receipt, confirmation)
    reconciled = copy.deepcopy(old)
    reconciled['requests'][-1].update(status='settled', cost_usd='0.08',
        settled_at=confirmation['recorded_at'], settlement_basis='user_confirmed_provider_accounting',
        reconciliation_receipt_sha256=r.sha(receipt), provider_observation_sha256='observation',
        provider_usage_is_final=False, source_attempt_kind='phase3_audit_only', source_attempt_outcome='stopped')
    reconciled['reconciled_from'] = {'checkpoint_sha256': r.sha(source), 'receipt_sha256': r.sha(receipt),
        'request_id': row['id'], 'previous_status': 'pending', 'confirmed_charge_usd': '0.08',
        'source_attempt_completed': False}
    checkpoint = reg.parent / 'reconciled.json'
    save(checkpoint, reconciled)
    next_m = copy.deepcopy(m)
    next_dir = reg.parent / 'next'; next_dir.mkdir()
    next_m['budget']['ledger_path'] = str(next_dir / 'billing.json')
    next_m['budget']['continuation'] = {'checkpoint': str(checkpoint), 'sha256': r.sha(checkpoint),
        'cost_usd': '2.26768875', 'reconciliation': {'source_registration': str(reg),
        'source_ledger': str(source), 'receipt': str(receipt), 'result': str(result)}}
    for path in (reg, source, receipt, result, checkpoint):
        next_m['pinned_files'][str(path)] = r.sha(path)
    return next_m, source, receipt, checkpoint, next_dir / 'registration.json'


def repin(m, path):
    m['pinned_files'][str(path)] = r.sha(path)
    if str(path) == m['budget']['continuation']['checkpoint']:
        m['budget']['continuation']['sha256'] = r.sha(path)


def test_confirmed_audit_copy_advances_once_without_rewriting_history(stopped_audit):
    m, source, receipt, checkpoint, reg = stopped_audit
    preserved = {p: p.read_bytes() for p in (source, receipt, checkpoint)}
    original_rows = r.read_json(source)['requests'][:-1]
    assert r.validate_audit_reconciliation(m) == r.read_json(checkpoint)
    with r.sequence_guard(m, 'second'):
        ledger = r.open_audit_ledger(m, reg, 'second')
    state = r.read_json(ledger.path)
    assert state['requests'][:-1] == original_rows
    assert all(row['status'] == 'settled' for row in state['requests'])
    assert sum(Decimal(row['cost_usd']) for row in state['requests']) == Decimal('2.26768875')
    assert r.read_json(source)['requests'][-1]['status'] == 'pending'
    assert all(p.read_bytes() == value for p, value in preserved.items())
    with pytest.raises(r.BudgetStop, match='already consumed'):
        with r.sequence_guard(m, 'second'): pass
    with pytest.raises(r.BudgetStop, match='current sequence tip'):
        with r.sequence_guard(m, 'third'): pass


@pytest.mark.parametrize('change', ['earlier_cost', 'removed_row', 'new_row', 'boolean_usage',
    'confirmed_cost', 'fabricated_usage', 'completed_attempt', 'changed_budget', 'cleared_stops', 'relabelled_lineage'])
def test_audit_reconciliation_checks_content_after_repin(stopped_audit, change):
    m, _, _, checkpoint, _ = stopped_audit
    value = r.read_json(checkpoint)
    if change == 'earlier_cost': value['requests'][0]['cost_usd'] = '0'
    elif change == 'removed_row': value['requests'].pop(0)
    elif change == 'new_row': value['requests'].append(copy.deepcopy(value['requests'][0]))
    elif change == 'boolean_usage': value['requests'][0]['usage']['output_tokens'] = True
    elif change == 'confirmed_cost': value['requests'][-1]['cost_usd'] = '0'
    elif change == 'fabricated_usage': value['requests'][-1]['provider_usage_is_final'] = True
    elif change == 'completed_attempt': value['requests'][-1]['source_attempt_outcome'] = 'completed'
    elif change == 'changed_budget': value['additional_cap_usd'] = '800'
    elif change == 'cleared_stops': value['stopped_attempts'] = []
    elif change == 'relabelled_lineage': value['reconciled_from']['source_attempt_completed'] = True
    save(checkpoint, value); repin(m, checkpoint)
    before = Path(m['sequence_state']).read_bytes()
    with pytest.raises(r.BudgetStop, match='unconfirmed history'):
        with r.sequence_guard(m, 'second'): pass
    assert Path(m['sequence_state']).read_bytes() == before


@pytest.mark.parametrize('field,value', [('request_id','unrelated'), ('attempt','unrelated'),
    ('confirmed_complete_charge_usd','NaN'), ('confirmed_complete_charge_usd','-1'),
    ('confirmed_complete_charge_usd','4'), ('source_registration_sha256','wrong'),
    ('stopped_result_sha256','wrong'), ('source_attempt_kind','generation'),
    ('previous_reservation_usd','4'), ('user_confirmation', {'exact_response': True, 'quoted_request': 'x'})])
def test_audit_receipt_binds_exact_pending_request(stopped_audit, field, value):
    m, _, receipt, _, _ = stopped_audit
    record = r.read_json(receipt); record[field] = value
    save(receipt, record); repin(m, receipt)
    with pytest.raises(r.BudgetStop): r.validate_audit_reconciliation(m)


@pytest.mark.parametrize('mutation', ['registration', 'ledger', 'result', 'foreign_source', 'missing_pin', 'extra_bridge_field'])
def test_audit_bridge_rejects_stale_or_unbound_identity(stopped_audit, mutation):
    m, _, _, _, _ = stopped_audit
    bridge = m['budget']['continuation']['reconciliation']
    state_path = Path(m['sequence_state'])
    state = r.read_json(state_path)
    if mutation == 'registration': state['registration_sha256'] = 'unrelated'; save(state_path, state)
    elif mutation == 'ledger': state['ledger_path'] = str(state_path.parent / 'unrelated.json'); save(state_path, state)
    elif mutation == 'foreign_source': state['source_registration_sha256'] = 'foreign'; save(state_path, state)
    elif mutation == 'result':
        path = Path(bridge['result']); record = r.read_json(path); record['status'] = 'completed'
        save(path, record); repin(m, path)
    elif mutation == 'missing_pin': del m['pinned_files'][bridge['source_ledger']]
    elif mutation == 'extra_bridge_field': bridge['other'] = bridge['source_ledger']
    before = state_path.read_bytes()
    with pytest.raises(r.BudgetStop):
        with r.sequence_guard(m, 'second'): pass
    assert state_path.read_bytes() == before


@pytest.mark.parametrize('kwargs', [
    {'continuation_source_registration': '/source'},
    {'continuation_reconciliation_receipt': '/receipt'},
    {'continuation_source_registration': '/source', 'continuation_reconciliation_receipt': '/receipt'}])
def test_prepare_requires_complete_reconciliation_before_creating_condition(tmp_path, kwargs):
    from audit_controls.prepare import prepare
    destination = tmp_path / 'uncreated'
    with pytest.raises(r.BudgetStop, match='reconciliation requires'):
        prepare(parent_registration='/unused', parent_overlay='/unused', parent_job_id='unused',
            reconciliation_receipt='/unused', reconciled_checkpoint='/unused', destination=destination,
            job_id='new', repository=str(tmp_path), **kwargs)
    assert not destination.exists()
