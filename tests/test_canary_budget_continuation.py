"""A new instrument condition must retain every earlier sequence charge."""
import hashlib
import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import pytest
from filelock import Timeout

_path=Path(__file__).resolve().parents[1]/'notes/matched_cborg_2026-09-13/budgeted_cborg.py'
_spec=importlib.util.spec_from_file_location('continued_cborg_budget',_path)
budget=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(budget)


def checkpoint(tmp_path, *, cost='3.29146500', status='settled'):
    old=budget.Ledger(tmp_path/'old.json',manifest_sha256='old-condition',total_cap=6)
    ticket=old.reserve('CHORUS_api_rep1',cost,'original-request')
    if status=='settled':old.settle(ticket,cost,response_sha256='original-response',usage={})
    raw=old.path.read_bytes()
    manifest={'budget':{'additional_usd':6,'per_attempt_usd':5,
        'ledger_path':str((tmp_path/'new/billing.json').resolve()),
        'continuation':{'checkpoint':str(old.path),'sha256':hashlib.sha256(raw).hexdigest(),'cost_usd':cost}},
        'pinned_files':{str(old.path):hashlib.sha256(raw).hexdigest()}}
    return old,manifest


def test_api_and_native_share_carried_total_with_distinct_attempts(tmp_path):
    old,manifest=checkpoint(tmp_path)
    prior_bytes=old.path.read_bytes()
    ledger=budget.open_ledger(manifest,'new-condition')
    api=budget.attempt_identity('new-condition','CHORUS_api_rep1')
    native=budget.attempt_identity('new-condition','CHORUS_agentic_rep1')
    # A fresh attempt has its own allowance, but cannot reset the sequence.
    ticket=ledger.reserve(api,'2','api');ledger.settle(ticket,'2',response_sha256='api-response',usage={})
    reopened=budget.open_ledger(manifest,'new-condition')
    with pytest.raises(budget.BudgetStop,match='remaining budget'):
        reopened.reserve(native,'0.71','native')
    state=json.loads(reopened.path.read_bytes())
    assert len(state['requests'])==2
    assert state['requests'][0]==json.loads(prior_bytes)['requests'][0]
    assert sum(Decimal(row['cost_usd']) for row in state['requests'])==Decimal('5.29146500')
    assert old.path.read_bytes()==prior_bytes


def test_continuation_does_not_share_old_attempt_allowance(tmp_path):
    old,manifest=checkpoint(tmp_path)
    # A larger sequence cap makes the separate $5 attempt allowance observable.
    value=json.loads(old.path.read_bytes());value['additional_cap_usd']='200'
    old.path.write_text(json.dumps(value))
    h=budget.digest(old.path.read_bytes())
    manifest['budget']['additional_usd']=200
    manifest['budget']['continuation']['sha256']=h;manifest['pinned_files'][str(old.path)]=h
    ledger=budget.open_ledger(manifest,'new-condition')
    attempt=budget.attempt_identity('new-condition','CHORUS_api_rep1')
    ticket=ledger.reserve(attempt,5,'new-request')
    ledger.settle(ticket,5,response_sha256='new-response',usage={})
    with pytest.raises(budget.BudgetStop,match='remaining budget'):
        ledger.reserve(attempt,'0.001','too-much')


@pytest.mark.parametrize('defect',['changed','unresolved','wrong_total','unbound','different_cap','duplicate','invalid_cost'])
def test_bad_checkpoint_cannot_seed_a_fresh_budget(tmp_path,defect):
    old,manifest=checkpoint(tmp_path,status='pending' if defect=='unresolved' else 'settled')
    prior=manifest['budget']['continuation']
    if defect=='changed':old.path.write_bytes(old.path.read_bytes()+b' ')
    if defect=='wrong_total':prior['cost_usd']='0'
    if defect=='unbound':manifest['pinned_files']={}
    if defect=='different_cap':manifest['budget']['additional_usd']=200
    if defect in ['duplicate','invalid_cost']:
        value=json.loads(old.path.read_bytes())
        if defect=='duplicate':value['requests']*=2
        else:value['requests'][0]['cost_usd']='NaN'
        old.path.write_text(json.dumps(value))
        prior['sha256']=budget.digest(old.path.read_bytes());manifest['pinned_files'][str(old.path)]=prior['sha256']
    with pytest.raises(budget.BudgetStop):budget.open_ledger(manifest,'new-condition')
    assert not (tmp_path/'new/billing.json').exists()


def test_reopening_cannot_erase_changed_or_existing_charges(tmp_path):
    old,manifest=checkpoint(tmp_path)
    ledger=budget.open_ledger(manifest,'new-condition')
    state=json.loads(ledger.path.read_bytes());state['requests'][0]['cost_usd']='0'
    ledger.path.write_text(json.dumps(state));before=ledger.path.read_bytes()
    with pytest.raises(budget.BudgetStop,match='history changed'):
        budget.open_ledger(manifest,'new-condition')
    assert ledger.path.read_bytes()==before
    other=budget.Ledger(tmp_path/'other/billing.json',manifest_sha256='new-condition',total_cap=6)
    other.reserve('existing',1,'already-running')
    before=other.path.read_bytes()
    with pytest.raises(budget.BudgetStop,match='cannot replace existing'):
        budget.open_ledger({**manifest,'budget':{**manifest['budget'],'ledger_path':str(other.path.resolve())}},'new-condition')
    assert other.path.read_bytes()==before


@pytest.mark.parametrize('condition',['settled','pending','locked'])
def test_relocated_registration_shares_all_subsequent_accounting(tmp_path,condition):
    _,manifest=checkpoint(tmp_path)
    first=tmp_path/'first/registration.json';second=tmp_path/'relocated/registration.json'
    first.parent.mkdir();second.parent.mkdir()
    first.write_text(json.dumps(manifest));second.write_bytes(first.read_bytes())
    registration_sha=budget.digest(first.read_bytes())
    api=budget.open_ledger(json.loads(first.read_bytes()),registration_sha)
    ticket=api.reserve(budget.attempt_identity(registration_sha,'CHORUS_api_rep1'),'2','api-request')
    if condition!='pending':api.settle(ticket,'2',response_sha256='api-response',usage={})
    if condition=='locked':
        with api.lock:
            with pytest.raises(Timeout):
                budget.open_ledger(json.loads(second.read_bytes()),registration_sha)
    else:
        native=budget.open_ledger(json.loads(second.read_bytes()),registration_sha)
        assert native.path==api.path
        with pytest.raises(budget.BudgetStop,match='pending or unknown' if condition=='pending' else 'remaining budget'):
            native.reserve(budget.attempt_identity(registration_sha,'CHORUS_agentic_rep1'),'0.71','native-request')
    state=json.loads(api.path.read_bytes())
    assert len(state['requests'])==2
    assert state['requests'][-1]['id']==ticket
    assert not first.with_name('billing.json').exists()
    assert not second.with_name('billing.json').exists()


@pytest.mark.parametrize('location',[None,'','billing.json'])
def test_unbound_ledger_location_is_refused(tmp_path,location):
    _,manifest=checkpoint(tmp_path)
    if location is None:del manifest['budget']['ledger_path']
    else:manifest['budget']['ledger_path']=location
    with pytest.raises(budget.BudgetStop,match='ledger path'):
        budget.open_ledger(manifest,'new-condition')
    assert not (tmp_path/'new/billing.json').exists()
