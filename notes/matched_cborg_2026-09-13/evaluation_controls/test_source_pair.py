"""Synthetic accepted composite ancestry, actual owner and deterministic renderers."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import json
import sys

import pytest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import registration as reg
import prepare_evaluation as prepare
import source_pair
from budgeted_cborg import Ledger
import continuation_sequence as sequence
from finalization_controls.test_contract import final_fixture


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')
    return {'path':str(path),'sha256':reg.sha(path)}


def reference(path):return {'path':str(path),'sha256':reg.sha(path)}


@pytest.fixture
def composite(tmp_path,monkeypatch):
    # Actual scientific fixture is preserved; no accepted real dataset is used.
    (tmp_path/'science').mkdir()
    science=final_fixture(tmp_path/'science')
    root=tmp_path/'chain';root.mkdir()
    native=root/'version-only';native.write_text('#!/bin/sh\nprintf "%s\\n" "2.1.272 (Claude Code)"\n');native.chmod(0o700)
    inputs=deepcopy(science['inputs']);auditpath=Path(inputs.pop('audit'))
    generation_path=root/'generation/registration.json';original_ledger=generation_path.parent/'billing.json'
    generation={'repository':str(root),'budget':{'ledger_path':str(original_ledger),'additional_usd':'400','per_attempt_usd':'5'},
        'generation':{'jobs':[{'id':'original','project':'Synthetic','method':'author_supplied','profile':'neutral',
            'bundle':inputs['bundle'],'input_identity':{'bundle':reference(inputs['bundle'])}}]}}
    origin=save(generation_path,generation);save(original_ledger,{'historical':'unchanged original ledger'})
    parent={'registration':str(generation_path),'job_id':'original'}
    audit_registration=root/'audit/registration.json';audit_ledger=audit_registration.parent/'billing.json'
    audit={'kind':'d4d_native_audit_continuation','parent':parent,'inputs':inputs,
        'job':{'id':'audit','audit_path':str(auditpath)},'budget':{'ledger_path':str(audit_ledger)}}
    auditref=save(audit_registration,audit)
    ledger=Ledger(audit_ledger,manifest_sha256=auditref['sha256'],total_cap='400',attempt_cap='5')
    ticket=ledger.reserve(auditref['sha256']+':audit','.02','offline');ledger.settle(ticket,'.01',response_sha256='offline',usage={})
    auditresult=save(root/'audit/result.json',{'scope':'phase3_audit_only','job_id':'audit','registration_sha256':auditref['sha256'],
        'status':'completed_pending_independent_review','unresolved_requests':[],
        'validation':{'passed':True,'checked':True,'job_id':'audit','audit_sha256':reg.sha(auditpath),'findings':[],'errors':[]},
        'runtime':{'proxy_shutdown_complete':True,'unfinished_handlers':0},'audit_path':str(auditpath),'audit_sha256':reg.sha(auditpath)})
    auditaccept=save(root/'audit/acceptance.json',{'verdict':'accept','registration_sha256':auditref['sha256'],
        'result_sha256':auditresult['sha256'],'ledger_sha256':reg.sha(audit_ledger),'artifacts':{str(auditpath):reg.sha(auditpath)}})
    state=original_ledger.with_name('audit_sequence.json');legacy={'schema_version':1,'registration_sha256':auditref['sha256'],
        'ledger_path':str(audit_ledger),'source_registration_sha256':origin['sha256']}
    save(state,legacy);snapshot=save(root/'audit_state.json',legacy)
    predecessor={'stage':'audit','registration':auditref,'ledger':reference(audit_ledger),'state':snapshot,'result':auditresult,'acceptance':auditaccept}
    phase_path=root/'phase4/registration.json';attempt=phase_path.parent/'attempts/final';output=attempt/'output';output.mkdir(parents=True)
    phase=deepcopy(science);phase['job'].update(id='final',attempt_dir=str(attempt),output_dir=str(output),deadline_seconds=10800)
    for role,name in [('full','full.yaml'),('core','core.yaml'),('report','report.md')]:
        target=output/name;target.write_bytes(Path(science['job'][role+'_path']).read_bytes());phase['job'][role+'_path']=str(target)
    # core_text binds the full filename in its generated header; recompute at
    # the actual synthetic Phase4 destination rather than copying old headers.
    from data_sheets_schema.derive_core import core_text
    from data_sheets_schema.d4d_pair_consistency import load_pair_schema
    pair_schema=load_pair_schema(Path(phase['inputs']['full_schema']),Path(phase['inputs']['core_schema']))
    Path(phase['job']['core_path']).write_text(core_text(Path(phase['job']['full_path']),pair_schema,phase4_complete=True)[0])
    phase.update(kind='d4d_native_finalization',schema_version=1,parent=parent,accepted_audit={'registration':auditref},
        model={'model':'claude-opus-5','route_model':'vertex_ai/claude-opus-5'},profile='neutral',
        provider_base_url='https://api.cborg.lbl.gov',provider_context_policy='headroom_bypass_v1',
        native_runtime={**prepare.runtime_snapshot(native),'api_timeout_ms':3600000,'api_force_idle_timeout':False},
        budget={'additional_usd':'400','per_attempt_usd':'5','ledger_path':str(phase_path.parent/'billing.json'),
            'per_job_attempt_usd':{'final':'20'},'prices_per_token':{'input':.000005,'output':.000025,'cache_write':.00000625,'cache_read':.0000005},
            'continuation':{'checkpoint':str(audit_ledger),'sha256':reg.sha(audit_ledger),'cost_usd':'.01'}},
        budget_sequence={'protocol':'shared_sequence_v2','stage':'reconciliation','state_path':str(state),
            'origin':{'registration':origin,'ledger_path':str(original_ledger)},'predecessor':predecessor,'audit_origin':deepcopy(predecessor)})
    for ref in [origin,auditref,auditresult,auditaccept,snapshot,reference(audit_ledger),reference(auditpath),reference(sequence.__file__)]:
        phase['pinned_files'][ref['path']]=ref['sha256']
    seal=save(root/'seal.json',sequence.seal_document(phase));phase['budget_sequence']['seal']=seal;phase['pinned_files'][seal['path']]=seal['sha256']
    save(phase_path,phase)
    with sequence.owned_sequence(phase,phase_path,reg.sha(phase_path)) as owner:
        t=owner.reserve(reg.sha(phase_path)+':final','.02','synthetic-finalization');owner.ledger.settle(t,'.01',response_sha256='offline',usage={})
    artifacts={phase['job'][role+'_path']:reg.sha(phase['job'][role+'_path']) for role in ('full','core','report')}
    from finalization_controls.native import lineage
    lin=save(attempt/'lineage.json',lineage(phase,reg.sha(phase_path),artifacts,{'phase4':{'fixture':True}}))
    allartifacts={**artifacts,lin['path']:lin['sha256']}
    result=save(attempt/'result.json',{'scope':'phase4_reconciliation','job_id':'final','registration_sha256':reg.sha(phase_path),
        'status':'completed_pending_independent_review','unresolved_requests':[],
        'validation':{'checked':True,'passed':True,'errors':[],'findings':[],'artifacts':artifacts},
        'runtime':{'exit_code':0,'proxy_shutdown_complete':True,'unfinished_handlers':0},
        'evidence':{'phase4':{'fixture':True}},'artifacts':allartifacts})
    acceptance=save(root/'phase4/acceptance.json',{'verdict':'accept','registration_sha256':reg.sha(phase_path),
        'result_sha256':result['sha256'],'ledger_sha256':reg.sha(phase['budget']['ledger_path']),'artifacts':allartifacts})
    context=root/'context.json';save(context,{})
    import anthropic
    monkeypatch.setattr(anthropic,'Anthropic',lambda *a,**k:pytest.fail('provider constructed offline'))
    # New source is uncommitted while implementation tests run; production must
    # retain this guard. The fixture only stubs code attestation, not ancestry.
    monkeypatch.setattr(prepare,'verify_implementation',lambda m:None)
    monkeypatch.setattr(reg,'verify_implementation',lambda m:None)
    return {'destination':root/'evaluation','finalization_registration':phase_path,
        'finalization_acceptance':Path(acceptance['path']),'context_path':context,'native_executable':native,
        'state':state,'phase':phase}


def build(case):return prepare.build_composite_registration(**{k:v for k,v in case.items() if k not in ('state','phase')})


def test_composite_preparation_preserves_ancestry_roster_and_real_budget(composite):
    before=composite['state'].read_bytes();phase=composite['phase']
    ledger=Path(phase['budget']['ledger_path']);billing=ledger.read_bytes()
    result=build(composite);m=reg.read_json(result['registration'])
    assert m['schema_version']==2 and 'source_generation' not in m
    assert m['source_pair']['kind']=='composite_finalization_v1'
    assert m['source_pair']['original_generation']['job_id']=='original'
    assert composite['state'].read_bytes()==before and ledger.read_bytes()==billing
    assert not Path(m['budget']['ledger_path']).exists() and not Path(m['attempts_dir']).exists()
    assert m['budget']['continuation']['checkpoint']==str(ledger)
    assert m['budget']['additional_usd']=='400' and m['budget']['per_attempt_usd']=='5'
    assert 'per_job_attempt_usd' not in m['budget']
    from collections import Counter
    counts=Counter(j['style'] for j in m['evaluation_jobs'])
    assert counts['semantic_agent']==12 and counts['field_agent']==4 and counts['direct_api_quality']==4
    inventory=reg.read_json(composite['destination']/'slot_inventory.json')
    assert counts['fitness']==counts['grounding']==sum(len(v['included']) for v in inventory.values())
    assert len(m['canary_acceptances'])==16
    for job in m['evaluation_jobs']:
        assert job['input']==phase['job'][job['variant']+'_path']
        if job['style'] in reg.NATIVE_STYLES:
            assert job['native_runtime']['api_timeout_ms']==3600000 and job['native_runtime']['api_force_idle_timeout'] is False
    assert reg.verify_manifest(m,result['registration'],reg.sha(result['registration']))


@pytest.mark.parametrize('damage',['no_acceptance','missing_lineage_acceptance','old_pair','wrong_parent','pending','unchecked','live_handlers','exit_nonzero','exit_missing','exit_boolean','changed_bundle','changed_lineage','contradictory_phase_history','other_owner'])
def test_composite_refuses_invalid_source_before_preparation(composite,damage):
    phase=composite['phase'];acceptance=composite['finalization_acceptance'];review=reg.read_json(acceptance)
    if damage=='no_acceptance':review['verdict']='pending';save(acceptance,review)
    elif damage=='missing_lineage_acceptance':
        review['artifacts'].pop(str(Path(phase['job']['attempt_dir'])/'lineage.json'));save(acceptance,review)
    elif damage=='old_pair':Path(phase['job']['full_path']).write_bytes(Path(phase['inputs']['original_full']).read_bytes())
    elif damage=='wrong_parent':
        value=reg.read_json(composite['finalization_registration']);value['parent']['job_id']='other';save(composite['finalization_registration'],value)
    elif damage=='pending':
        path=Path(phase['budget']['ledger_path']);value=reg.read_json(path);value['requests'][-1]['status']='pending';save(path,value)
    elif damage in ('unchecked','live_handlers','exit_nonzero','exit_missing','exit_boolean'):
        path=Path(phase['job']['attempt_dir'])/'result.json';value=reg.read_json(path)
        if damage=='unchecked':value['validation']['checked']=False
        elif damage=='live_handlers':value['runtime']['unfinished_handlers']=1
        elif damage=='exit_nonzero':value['runtime']['exit_code']=1
        elif damage=='exit_missing':value['runtime'].pop('exit_code')
        else:value['runtime']['exit_code']=False
        save(path,value);review['result_sha256']=reg.sha(path);save(acceptance,review)
    elif damage=='changed_bundle':Path(phase['inputs']['bundle']).write_text('different source\n')
    elif damage=='changed_lineage':
        path=Path(phase['job']['attempt_dir'])/'lineage.json';value=reg.read_json(path);value['phase3_performed_here']=True;save(path,value)
    elif damage=='contradictory_phase_history':
        # Coherently update the accepted file hashes, retaining a contradictory
        # observed history between the actual result and its lineage copy.
        lineage=Path(phase['job']['attempt_dir'])/'lineage.json'
        value=reg.read_json(lineage);value['observed_phase4']={'fixture':False};save(lineage,value)
        result=Path(phase['job']['attempt_dir'])/'result.json';value=reg.read_json(result)
        value['artifacts'][str(lineage)]=reg.sha(lineage);save(result,value)
        review['result_sha256']=reg.sha(result);review['artifacts'][str(lineage)]=reg.sha(lineage);save(acceptance,review)
    else:
        value=reg.read_json(composite['state']);value['active_tip']['registration_sha256']='other';save(composite['state'],value)
    with pytest.raises((reg.BudgetStop,ValueError,KeyError)):
        build(composite)
    assert not composite['destination'].exists()


@pytest.mark.parametrize('damage',['prices','pair','canary_map','source_ancestry','context_class','runtime_idle','omitted_repeat','omitted_slot','other_context','job_profile','job_schema'])
def test_registered_composite_mutants_fail_closed(composite,damage):
    result=build(composite);path=result['registration'];m=reg.read_json(path)
    if damage=='prices':m['budget']['prices_per_token']['input']=0
    elif damage=='pair':m['evaluation_jobs'][0]['input']=composite['phase']['inputs']['original_full']
    elif damage=='canary_map':m['canary_acceptances'].pop(next(iter(m['canary_acceptances'])))
    elif damage=='source_ancestry':m['source_pair']['original_generation']['job_id']='other'
    elif damage=='context_class':m['evaluation_jobs'][0]['class_name']='CoreDataset'
    elif damage=='runtime_idle':m['evaluation_jobs'][0]['native_runtime']['api_force_idle_timeout']=True
    elif damage=='omitted_repeat':m['evaluation_jobs'].remove(next(j for j in m['evaluation_jobs'] if j['style']=='semantic_agent' and j['rating']==3))
    elif damage=='omitted_slot':m['evaluation_jobs'].remove(next(j for j in m['evaluation_jobs'] if j['style']=='fitness'))
    elif damage=='other_context':
        other=path.parent/'other_context.json';save(other,{})
        m['pinned_files'][str(other)]=reg.sha(other);m['evaluation_jobs'][0]['context_path']=str(other)
    elif damage=='job_profile':m['evaluation_jobs'][0]['profile']='bridge2ai'
    else:m['evaluation_jobs'][0]['schema_path']=m['evaluation_jobs'][-1]['schema_path'] if m['evaluation_jobs'][-1]['schema_path']!=m['evaluation_jobs'][0]['schema_path'] else '/wrong/schema.yaml'
    save(path,m)
    with pytest.raises((reg.BudgetStop,ValueError,KeyError)):
        reg.verify_manifest(m,path,reg.sha(path))


def test_duplicate_subtype_parent_refuses_before_spend(subtype_registration):
    m,path,review,save_child,_=subtype_registration
    first=m['evaluation_jobs'][0]
    duplicate={**first,'id':'duplicate_parent_job','canary':False,'rating':2,
        'canary_acceptance':str(path.parent/'reviewed_subtype_canary.json'),
        'candidate':str(Path(m['attempts_dir'])/'duplicate_parent_job/output/candidate.json'),
        'output':str(path.parent/'published/duplicate_parent.json')}
    m['evaluation_jobs'].append(duplicate)
    save_child()
    # Both unique job IDs/paths and group shape are valid. The same exact
    # fitness parent must not become two separately billable subtype ratings.
    with pytest.raises(reg.BudgetStop,match='exactly one job per fitness'):
        reg.verify_manifest(m,path,reg.sha(path))
    assert not Path(m['budget']['ledger_path']).exists()


from test_registration import registered, subtype_registration
