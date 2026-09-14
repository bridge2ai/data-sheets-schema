"""A registered exception changes one attempt's ceiling, never the allocation."""
import copy
import hashlib
import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import pytest

_path = Path(__file__).resolve().parents[1] / 'notes/matched_cborg_2026-09-13/budgeted_cborg.py'
_spec = importlib.util.spec_from_file_location('attempt_cap_budget', _path)
budget = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(budget)


def manifest(tmp_path, *, total=200, caps=None):
    value = {
        'budget': {'additional_usd': total, 'per_attempt_usd': 5,
                   'ledger_path': str((tmp_path / 'billing.json').resolve())},
        'generation': {'jobs': [{'id': 'external_api'}, {'id': 'external_native'},
                                {'id': 'study_api'}]},
        'pinned_files': {},
    }
    if caps is not None:
        value['budget']['per_job_attempt_usd'] = caps
    return value


def settle(ledger, attempt, cost):
    ticket = ledger.reserve(attempt, cost, 'request')
    ledger.settle(ticket, cost, response_sha256='response', usage={})
    return ticket


def test_exception_is_cumulative_and_bound_to_exact_registered_job(tmp_path):
    m = manifest(tmp_path, caps={'external_api': 15, 'external_native': 15})
    ledger = budget.open_ledger(m, 'new')
    api = budget.attempt_identity('new', 'external_api')
    native = budget.attempt_identity('new', 'external_native')
    settle(ledger, api, 6)
    reopened = budget.open_ledger(m, 'new')
    settle(reopened, api, 9)
    with pytest.raises(budget.BudgetStop, match=r'attempt \$0'):
        reopened.reserve(api, '.01', 'over-cap')
    assert reopened.limit_for_attempt(native) == Decimal(15)
    for other in ['external_api', 'old:external_api', 'new:study_api', 'new:external_api_extra']:
        assert reopened.limit_for_attempt(other) == Decimal(5)
        with pytest.raises(budget.BudgetStop, match='remaining budget'):
            reopened.reserve(other, 6, 'not-excepted')
    assert [r['attempt_cap_usd'] for r in json.loads(ledger.path.read_text())['requests']] == ['15', '15']


def test_exception_does_not_reset_sequence_or_prior_attempt_caps(tmp_path):
    old = budget.Ledger(tmp_path / 'prior.json', manifest_sha256='old', total_cap=20)
    settle(old, 'old:external_api', 5)
    prior = old.path.read_bytes()
    h = hashlib.sha256(prior).hexdigest()
    m = manifest(tmp_path, total=20, caps={'external_api': 15, 'external_native': 15})
    m['budget']['continuation'] = {'checkpoint': str(old.path), 'sha256': h, 'cost_usd': '5'}
    m['pinned_files'][str(old.path)] = h
    ledger = budget.open_ledger(m, 'new')
    settle(ledger, 'new:external_api', 15)
    with pytest.raises(budget.BudgetStop, match=r'sequence \$0'):
        budget.open_ledger(m, 'new').reserve('new:external_native', '.01', 'no-allocation')
    state = json.loads(ledger.path.read_text())
    assert state['requests'][0] == json.loads(prior)['requests'][0]
    assert state['requests'][0]['attempt_cap_usd'] == '5'
    assert old.path.read_bytes() == prior
    assert sum(Decimal(r['cost_usd']) for r in state['requests']) == 20


@pytest.mark.parametrize('change', ['increase', 'remove', 'rename'])
def test_reopening_cannot_change_or_remove_registered_exceptions(tmp_path, change):
    m = manifest(tmp_path, caps={'external_api': 15})
    ledger = budget.open_ledger(m, 'new')
    settle(ledger, 'new:external_api', 6)
    altered = copy.deepcopy(m)
    if change == 'increase':
        altered['budget']['per_job_attempt_usd']['external_api'] = 16
    elif change == 'remove':
        del altered['budget']['per_job_attempt_usd']
    else:
        altered['budget']['per_job_attempt_usd'] = {'external_native': 15}
    before = ledger.path.read_bytes()
    with pytest.raises(budget.BudgetStop, match='budget changed'):
        budget.open_ledger(altered, 'new').reserve('new:external_api', 1, 'changed-policy')
    assert ledger.path.read_bytes() == before


@pytest.mark.parametrize('caps', [[], None, {'unknown': 15}, {'external_api': 0},
                                 {'external_api': -1}, {'external_api': 'NaN'},
                                 {'external_api': 'Infinity'}, {'external_api': True},
                                 {'external_api': 'bad'}, {'external_api': 201}])
def test_invalid_exception_fails_before_admission(tmp_path, caps):
    m = manifest(tmp_path)
    m['budget']['per_job_attempt_usd'] = caps
    with pytest.raises(budget.BudgetStop):
        budget.open_ledger(m, 'new')
    assert not Path(m['budget']['ledger_path']).exists()


def test_duplicate_job_identity_cannot_receive_exception(tmp_path):
    m = manifest(tmp_path, caps={'external_api': 15})
    m['generation']['jobs'].append({'id': 'external_api'})
    with pytest.raises(budget.BudgetStop, match='unique'):
        budget.open_ledger(m, 'new')


def test_pending_exception_blocks_other_jobs_and_preserves_reservation(tmp_path):
    m = manifest(tmp_path, caps={'external_api': 15})
    ledger = budget.open_ledger(m, 'new')
    ticket = ledger.reserve('new:external_api', 6, 'pending')
    with pytest.raises(budget.BudgetStop, match='pending or unknown'):
        budget.open_ledger(m, 'new').reserve('new:study_api', 1, 'later')
    assert json.loads(ledger.path.read_text())['requests'][0]['id'] == ticket
    assert json.loads(ledger.path.read_text())['requests'][0]['status'] == 'pending'


def test_legacy_default_registration_remains_five_dollars(tmp_path):
    m = manifest(tmp_path)
    ledger = budget.open_ledger(m, 'new')
    settle(ledger, 'new:external_api', 5)
    with pytest.raises(budget.BudgetStop, match='remaining budget'):
        budget.open_ledger(m, 'new').reserve('new:external_api', '.01', 'default-cap')
    assert 'attempt_caps_usd' not in json.loads(ledger.path.read_text())
