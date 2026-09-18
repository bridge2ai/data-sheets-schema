"""Offline controller ownership and exclusive lifecycle with genuine Ledger rows.

The ancestry fixture is synthetic; scientific/prompt validation is covered by
contract tests. No fixture constitutes acceptance of a real generated dataset.
"""
from decimal import Decimal
from pathlib import Path
import json
import sys

import pytest

BASE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE))
from test_continuation_sequence import fixture,finish_registration,save
from continuation_sequence import read,sha
from . import native,registration
from budgeted_cborg import BudgetStop


@pytest.fixture
def registered(tmp_path,monkeypatch):
    m,path,state=fixture(tmp_path)
    attempt=path.parent/'attempts'/'finish';output=attempt/'output'
    m['kind']=registration.KIND;m['repository_commit']='synthetic-reviewed-code'
    m['inputs']={'audit':m['budget_sequence']['audit_origin']['result']['path']}
    m['job'].update(attempt_dir=str(attempt),output_dir=str(output),full_path=str(output/'full.yaml'),
        core_path=str(output/'core.yaml'),report_path=str(output/'report.md'))
    identity=finish_registration(m,path)
    review=path.parent/'launch-review.json'
    save(review,{'verdict':'approve','registration_sha256':identity,'repository_commit':m['repository_commit'],
        'ci_conclusion':'success','allowed_jobs':['finish']})
    monkeypatch.setattr(registration,'validate_registration',lambda p:read(p))
    def verify(manifest,p,digest):
        if sha(p)!=digest:raise BudgetStop('changed fixture registration')
        for name,expected in manifest['pinned_files'].items():
            if sha(name)!=expected:raise BudgetStop('changed fixture input')
    monkeypatch.setattr(registration,'verify',verify)
    monkeypatch.setattr(native,'build_policy',lambda *a:{})
    monkeypatch.setattr(native.runtime,'verify_runtime',lambda *a:Path(sys.executable))
    return m,path,state,review


def successful_adapter(context):
    context.verify()
    ticket=context.ledger.reserve(context.manifest_sha256+':'+context.job['id'],'.02','offline-request')
    context.ledger.settle(ticket,'.01',response_sha256='offline-response',usage={'output_tokens':1})
    artifacts={}
    for key in ('full_path','core_path','report_path'):
        p=Path(context.job[key]);p.write_text('Synthetic '+key+'\n');artifacts[str(p)]=sha(p)
    return {'validation':{'passed':True,'checked':True},'artifacts':artifacts,
        'runtime':{'proxy_shutdown_complete':True,'unfinished_handlers':0},
        'evidence':{'phase4':{'closing_repairs':0,'scope':'synthetic adapter lifecycle only'}}}


def test_run_holds_actual_owner_carries_once_and_preserves_originals(registered):
    m,path,state,review=registered
    before={name:Path(name).read_bytes() for name in m['pinned_files']}
    receipt=native.run_job(path,review,adapter=successful_adapter)
    assert receipt['status']=='completed_pending_independent_review'
    assert receipt['settled_cost_usd']=='0.01' and receipt['requests_admitted']==1
    assert receipt['phase1_phase2_performed_here'] is False and receipt['phase3_performed_here'] is False
    assert read(state)['active_tip']['registration_sha256']==sha(path)
    ledger=read(m['budget']['ledger_path']);old=read(m['budget']['continuation']['checkpoint'])
    assert ledger['requests'][:-1]==old['requests']
    assert sum(Decimal(r['cost_usd']) for r in ledger['requests'])==Decimal('2.11')
    assert before=={name:Path(name).read_bytes() for name in before}
    lineage=read(Path(m['job']['attempt_dir'])/'lineage.json')
    assert lineage['scientific_acceptance'] is False
    assert lineage['accepted_audit']==m['budget_sequence']['audit_origin']
    assert lineage['final_artifacts']=={name:digest for name,digest in receipt['artifacts'].items() if not name.endswith('/lineage.json')}


def test_consumed_attempt_cannot_reopen_or_reserve_again(registered):
    m,path,state,review=registered;native.run_job(path,review,adapter=successful_adapter)
    before=Path(m['budget']['ledger_path']).read_bytes();state_before=state.read_bytes()
    with pytest.raises(BudgetStop,match='consumed'):native.run_job(path,review,adapter=successful_adapter)
    assert Path(m['budget']['ledger_path']).read_bytes()==before and state.read_bytes()==state_before


def test_uncertain_charge_stays_reserved_and_no_success_lineage(registered):
    m,path,state,review=registered
    def stopped(context):
        context.ledger.reserve(context.manifest_sha256+':finish','.02','uncertain-request')
        raise BudgetStop('synthetic transport interruption')
    with pytest.raises(BudgetStop):native.run_job(path,review,adapter=stopped)
    result=read(Path(m['job']['attempt_dir'])/'result.json')
    assert result['status']=='stopped' and len(result['unresolved_requests'])==1
    assert result['runtime']['unfinished_handlers'] is None
    assert not (Path(m['job']['attempt_dir'])/'lineage.json').exists()
    assert read(m['budget']['ledger_path'])['requests'][-1]['status']=='pending'


def test_owner_detects_external_tip_change_before_a_reservation(registered):
    m,path,state,review=registered
    def altered(context):
        value=read(state);value['active_tip']['registration_sha256']='other-owner';save(state,value)
        context.ledger.reserve(context.manifest_sha256+':finish','.02','must-not-admit')
    with pytest.raises(BudgetStop,match='owner changed'):native.run_job(path,review,adapter=altered)
    assert read(m['budget']['ledger_path'])['requests']==read(m['budget']['continuation']['checkpoint'])['requests']


@pytest.mark.parametrize('change',['review','pending','unchecked','input'])
def test_admission_failure_does_not_consume_state_or_create_outputs(registered,change):
    m,path,state,review=registered;before=state.read_bytes()
    if change=='review':
        value=read(review);value['allowed_jobs']=['unrelated'];save(review,value)
    elif change=='input':Path(m['inputs']['audit']).write_text('changed')
    elif change=='pending':
        value=read(m['budget']['continuation']['checkpoint']);value['requests'][0]['status']='pending';save(Path(m['budget']['continuation']['checkpoint']),value)
    else:
        value=read(m['budget_sequence']['predecessor']['result']['path']);value['validation']['checked']=False;save(Path(m['budget_sequence']['predecessor']['result']['path']),value)
    with pytest.raises(BudgetStop):native.run_job(path,review,adapter=successful_adapter)
    assert state.read_bytes()==before and not Path(m['job']['attempt_dir']).exists()
    assert not Path(m['budget']['ledger_path']).exists()


def test_owned_ledger_enforces_registered_attempt_roster(registered):
    m,path,state,review=registered
    def wrong_job(context):context.ledger.reserve(context.manifest_sha256+':unregistered','.01','must-not-admit')
    with pytest.raises(BudgetStop,match='unregistered'):native.run_job(path,review,adapter=wrong_job)
    assert len(read(m['budget']['ledger_path'])['requests'])==len(read(m['budget']['continuation']['checkpoint'])['requests'])


@pytest.mark.parametrize('change',['free_input','typed_prices','missing_prices','larger_cap','zero','negative','infinite','nan','extra_job','no_override'])
def test_inherited_prices_and_attempt_approval_are_admission_constraints(change):
    from copy import deepcopy
    accepted={'job':{'id':'accepted_audit'},'budget':{'per_attempt_usd':'5',
        'per_job_attempt_usd':{'accepted_audit':'20'},'prices_per_token':{'input':.000005,'output':.000025}}}
    manifest={'job':{'id':'finalize'},'budget':{'per_job_attempt_usd':{'finalize':'20'},
        'prices_per_token':deepcopy(accepted['budget']['prices_per_token'])}}
    if change=='free_input':manifest['budget']['prices_per_token']['input']=0
    elif change=='typed_prices':manifest['budget']['prices_per_token']['input']='0.000005'
    elif change=='missing_prices':manifest['budget'].pop('prices_per_token')
    elif change=='extra_job':manifest['budget']['per_job_attempt_usd']['unapproved']='20'
    elif change=='no_override':manifest['budget'].pop('per_job_attempt_usd')
    else:manifest['budget']['per_job_attempt_usd']['finalize']={'larger_cap':'20.01','zero':'0','negative':'-1','infinite':'Infinity','nan':'NaN'}[change]
    with pytest.raises(BudgetStop):registration.validate_budget_identity(manifest,accepted)


@pytest.mark.parametrize('cap',['5','20'])
def test_exact_prices_and_approved_positive_cap_pass(cap):
    accepted={'job':{'id':'audit'},'budget':{'per_attempt_usd':'5','per_job_attempt_usd':{'audit':'20'},
        'prices_per_token':{'input':.000005,'output':.000025}}}
    manifest={'job':{'id':'finalize'},'budget':{'per_job_attempt_usd':{'finalize':cap},
        'prices_per_token':{'input':.000005,'output':.000025}}}
    registration.validate_budget_identity(manifest,accepted)
