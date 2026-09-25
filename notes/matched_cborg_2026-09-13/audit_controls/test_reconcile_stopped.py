"""A stopped audit's one pending charge, settled under the standing authorization (#2467)."""
import copy
from decimal import Decimal
import json
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from budgeted_cborg import BudgetStop
from audit_controls import registration as r
from audit_controls import reconcile_stopped as tool
from audit_controls.test_registration import accounting, save  # noqa: F401  (fixture)


@pytest.fixture
def stopped(accounting):
    """A generation checkpoint followed by one audit stopped on an unconfirmed charge."""
    m, _, _, _, reg = accounting
    first = copy.deepcopy(m)
    first.update(kind='d4d_native_audit_continuation', repository=str(reg.parent), repository_commit='a' * 40)
    first['job']['attempt_dir'] = str(reg.parent / 'attempts' / first['job']['id'])
    save(reg, first)
    source_sha = r.sha(reg)
    with r.sequence_guard(first, source_sha):
        ledger = r.open_audit_ledger(first, reg, source_sha)
        attempt = r.attempt_identity(source_sha, first['job']['id'])
        settled = ledger.reserve(attempt, Decimal('1'), '1' * 64)
        ledger.settle(settled, Decimal('0.25'), response_sha256='synthetic', usage={})
        request_id = ledger.reserve(attempt, Decimal('2.4535'), '2' * 64)
        ledger.stop_attempt(attempt, 'upstream HTTP response did not confirm a completed charge')
    folder = Path(first['job']['attempt_dir']) / 'children' / 'worker_0001' / 'requests' / request_id
    folder.mkdir(parents=True)
    save(folder / 'admission.json', {'reserved_usd': '2.4535'})
    save(folder / 'http_status.json', {'status': 500, 'correlation_headers': {}})
    save(Path(first['job']['attempt_dir']) / 'result.json', {
        'registration_sha256': source_sha, 'job_id': first['job']['id'], 'scope': 'phase3_audit_only',
        'status': 'stopped', 'unresolved_requests': [request_id],
        'runtime': {'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0}})
    authorization = reg.parent.parent / 'standing.json'
    save(authorization, {'kind': tool.AUTHORIZATION_KIND, 'exact_response': '3- approved',
                         'quoted_request': 'Standing authority to debit unconfirmed charges at their full reservation?',
                         'recorded_at': '2026-09-25T18:00:31Z'})
    return m, first, reg, request_id, folder, authorization


def test_the_stopped_charge_is_settled_in_a_checkpoint_the_successor_accepts(stopped):
    m, first, reg, request_id, folder, authorization = stopped
    ledger = Path(first['budget']['ledger_path'])
    result = Path(first['job']['attempt_dir']) / 'result.json'
    before = {p: p.read_bytes() for p in (reg, ledger, result)}
    out = reg.parent.parent / 'reconciliation'
    value = tool.reconcile(reg, authorization, out, recorded_at='2026-09-25T19:00:00+00:00')
    assert before == {p: p.read_bytes() for p in before}
    receipt = json.loads(Path(value['receipt']).read_text())
    assert receipt['accounting_observation_sha256'] == r.sha(folder / 'http_status.json')
    assert receipt['user_authorization']['standing'] is True and receipt['budget_debit_usd'] == '2.4535'
    state = json.loads(Path(value['checkpoint']).read_text())
    row = next(x for x in state['requests'] if x['id'] == request_id)
    assert (row['status'], row['cost_usd'], row['provider_charge_confirmed']) == ('settled', '2.4535', False)
    assert Decimal(value['cost_usd']) == sum(Decimal(x['cost_usd']) for x in state['requests'])
    # The next audit continues from it through the real sequence guard and ledger import.
    successor = copy.deepcopy(m)
    folder_next = reg.parent.parent / 'next'
    folder_next.mkdir()
    successor['budget']['ledger_path'] = str(folder_next / 'billing.json')
    successor['budget']['continuation'] = {'checkpoint': value['checkpoint'], 'sha256': value['checkpoint_sha256'],
        'cost_usd': value['cost_usd'], 'reconciliation': {'source_registration': str(reg),
        'source_ledger': str(ledger), 'receipt': value['receipt'], 'result': str(result)}}
    for path in (reg, ledger, result, value['receipt'], value['checkpoint']):
        successor['pinned_files'][str(path)] = r.sha(path)
    assert r.validate_audit_reconciliation(successor) == state
    next_reg = folder_next / 'registration.json'
    save(next_reg, successor)
    with r.sequence_guard(successor, r.sha(next_reg)):
        imported = r.read_json(r.open_audit_ledger(successor, next_reg, r.sha(next_reg)).path)
    assert imported['requests'] == state['requests']
    with pytest.raises(BudgetStop, match='written once'):
        tool.reconcile(reg, authorization, out)


@pytest.mark.parametrize('damage', ['two_pending', 'no_pending', 'unresolved_mismatch', 'authorization', 'no_evidence'])
def test_nothing_is_published_for_a_stop_the_standing_debit_does_not_cover(stopped, damage):
    m, first, reg, request_id, folder, authorization = stopped
    ledger = Path(first['budget']['ledger_path'])
    state = json.loads(ledger.read_text())
    result = Path(first['job']['attempt_dir']) / 'result.json'
    if damage == 'two_pending':
        state['requests'][-2]['status'] = 'pending'
        ledger.write_text(json.dumps(state))
    elif damage == 'no_pending':
        state['requests'][-1].update(status='settled', cost_usd='2.4535')
        ledger.write_text(json.dumps(state))
    elif damage == 'unresolved_mismatch':
        value = json.loads(result.read_text()); value['unresolved_requests'] = ['another']
        result.write_text(json.dumps(value))
    elif damage == 'authorization':
        value = json.loads(authorization.read_text()); value['exact_response'] = ' '
        authorization.write_text(json.dumps(value))
    else:
        for name in ('admission.json', 'http_status.json'):
            (folder / name).unlink()
    out = reg.parent.parent / 'reconciliation'
    with pytest.raises(BudgetStop):
        tool.reconcile(reg, authorization, out)
    assert not out.exists() and not list(out.parent.glob('.reconciliation-*'))


def test_a_result_the_validator_refuses_publishes_nothing(stopped):
    m, first, reg, request_id, folder, authorization = stopped
    result = Path(first['job']['attempt_dir']) / 'result.json'
    value = json.loads(result.read_text())
    value['runtime']['proxy_shutdown_complete'] = False          # the runtime never closed
    result.write_text(json.dumps(value))
    out = reg.parent.parent / 'reconciliation'
    with pytest.raises(BudgetStop, match='closed runtime'):
        tool.reconcile(reg, authorization, out)
    assert not out.exists() and not list(out.parent.glob('.reconciliation-*'))
