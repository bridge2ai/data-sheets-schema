"""Budget planning limits and real reservation boundaries; no provider calls."""
from decimal import Decimal
import json
from pathlib import Path

import pytest

from budgeted_cborg import BudgetStop, Ledger
from audit_controls.batch_registration import offline_plan_fields
from audit_controls.test_batch_runtime import batch


def test_amended_batch_plan_exposes_headroom_without_claiming_retry_funding(batch):
    m = batch.m
    instruction = batch.reg.parent / 'controller-instruction.txt'
    instruction.write_text('Synthetic controller wrapper.\n')
    m['job']['instruction'] = str(instruction)
    m['budget'].update(additional_usd='500', continuation={'cost_usd': '387.50763200'})
    m['audit_batches']['worker_total_cap_usd'] = '35'
    m['native_stall_policy'] = {'max_stall_debits': 6}
    # The report is a projection after registration validation, not an authority validator.
    m['budget_amendment'] = {'synthetic_report_selector': True}
    plan = offline_plan_fields(m)
    limits = plan['budget_admission_plan']
    assert limits['worker_ceiling_usd'] == '35'
    assert limits['attempt_ceiling_usd'] == '40'
    assert limits['minimum_integration_allowance_usd'] == '5'
    assert limits['shared_allocation_usd'] == '500'
    assert limits['remaining_shared_allocation_usd'] == '112.49236800'
    assert limits['maximum_stall_debits'] == 6
    assert limits['retry_allowance_guarantees_funded_retries'] is False
    assert limits['workload_and_retry_costs_known'] is False
    assert plan['complete_workload_cost_estimate_available'] is False
    assert any(row['dynamic_proposal_inputs_pending'] for row in plan['audit_batch_inputs'])
    m.pop('budget_amendment')
    assert 'budget_admission_plan' not in offline_plan_fields(m)


@pytest.mark.parametrize('worker_cap, admitted', [('30', False), ('35', True)])
def test_retry_reserves_whole_request_after_stall_debit(tmp_path, worker_cap, admitted):
    ledger = Ledger(tmp_path/'billing.json', manifest_sha256='a'*64, total_cap=500,
                    attempt_cap=5, attempt_caps_usd={'fresh': 40})
    first = ledger.reserve('fresh', Decimal('26.62043'), 'b'*64, stage_cap=worker_cap)
    ledger.settle(first, Decimal('26.62043'), response_sha256='c'*64, usage={})
    stalled = ledger.reserve('fresh', Decimal('3.02635'), 'd'*64, stage_cap=worker_cap)
    ledger.debit_unconfirmed(stalled, maximum=6, evidence={'synthetic': True})
    before = json.loads(ledger.path.read_text())
    assert sum(Decimal(row['cost_usd']) for row in before['requests']) == Decimal('29.64678')
    assert before['requests'][-1]['provider_charge_confirmed'] is False
    if not admitted:
        with pytest.raises(BudgetStop):
            ledger.reserve('fresh', Decimal('3.02635'), 'e'*64, stage_cap=worker_cap)
        after = json.loads(ledger.path.read_text())
        assert after['requests'] == before['requests']
        assert 'fresh' in after['stopped_attempts']
        return
    retry = ledger.reserve('fresh', Decimal('3.02635'), 'e'*64, stage_cap=worker_cap)
    ledger.settle(retry, Decimal('3.02635'), response_sha256='f'*64, usage={})
    # Integration uses the actual attempt remainder; no separate budget is created.
    remainder = Decimal('40') - Decimal('32.67313')
    integration = ledger.reserve('fresh', remainder, '1'*64)
    ledger.settle(integration, remainder, response_sha256='2'*64, usage={})
    rows = json.loads(ledger.path.read_text())['requests']
    assert sum(Decimal(row['cost_usd']) for row in rows) == Decimal('40')
    with pytest.raises(BudgetStop):
        ledger.reserve('fresh', Decimal('.01'), '3'*64)
    assert json.loads(ledger.path.read_text())['requests'] == rows
