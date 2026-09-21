"""Explicit fitness schema authority through real evaluation control paths."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import yaml

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent)]
import api
import prepare_evaluation as prepare
import registration as reg
import source_pair
from evaluation_controls import closure
from data_sheets_schema import fitness_schema
from test_prepare_evaluation import accepted_fixture
from test_source_pair import composite

GUIDANCE='nested_semantics_v1'
SELECTOR='fitness_schema_guidance'


@pytest.fixture
def selected_composite(tmp_path, monkeypatch):
    import test_source_pair
    original = test_source_pair.final_fixture
    # The old minimal accounting fixture omits repository; actual accepted
    # Phase4 manifests carry it as the relative pin/profile authority.
    def complete_fixture(*a, **kw):
        from data_sheets_schema.schema_snapshot import capture_schema
        result = {**original(*a, **kw), 'repository':str(prepare.ROOT)}
        for role in ('full_schema','core_schema'):
            snapshot = capture_schema(result['inputs'][role],strict=True)
            result['pinned_files'].update({str(path):reg.sha(path) for _,path,_ in snapshot.sources})
        return result
    monkeypatch.setattr(test_source_pair, 'final_fixture', complete_fixture)
    return composite.__wrapped__(tmp_path, monkeypatch)


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')
    return path


def schemas(root):
    directory=root/'src/data_sheets_schema/schema';directory.mkdir(parents=True,exist_ok=True)
    child=directory/'children.yaml'
    child.write_text(yaml.safe_dump({'id':'https://example.invalid/children','name':'children',
        'default_prefix':'ex','prefixes':{'ex':'https://example.invalid/'},'default_range':'string',
        'types':{'string':{'base':'str','uri':'http://www.w3.org/2001/XMLSchema#string'}},
        'classes':{'Detail':{'description':'Settings after installation, not installation instructions.',
            'attributes':{'label':{'description':'Required operational label.','required':True},
                          'optional_note':{'description':'Optional maintenance meaning.'}}}}},sort_keys=False))
    paths={}
    for variant,kind in [('full','Dataset'),('core','CoreDataset')]:
        p=directory/('data_sheets_schema_all.yaml' if variant=='full' else 'data_sheets_schema_core_all.yaml')
        p.write_text(yaml.safe_dump({'id':'https://example.invalid/'+variant,'name':variant,'default_prefix':'ex',
            'prefixes':{'ex':'https://example.invalid/'},'default_range':'string','imports':['children'],
            'classes':{kind:{'description':'Synthetic declared record.', 'attributes':{
                'id':{'range':'string'},'name':{'range':'string'},'keywords':{'range':'string','multivalued':True},
                'description':{'range':'Detail','inlined':True,'description':'Declared settings object.'}}}}},sort_keys=False))
        paths[variant]=p
    return paths,child


@pytest.fixture
def selected_case(tmp_path):
    root=tmp_path/'authority';root.mkdir();paths,child=schemas(root)
    source={'repository':str(root),'pinned_files':{str(p):api.sha(p) for p in [*paths.values(),child]}}
    parent=write(root/'registration.json',source)
    record=tmp_path/'record.yaml';record.write_text(yaml.safe_dump({'Dataset':{'description':{'unknown':'UNCHANGED_VALUE'}}}))
    m={SELECTOR:GUIDANCE,'schema_version':1,'repository':str(prepare.ROOT),'profile':'neutral',
       'model':{'model':'synthetic'},'source_generation':{'registration':str(parent),'registration_sha256':api.sha(parent)},
       'pinned_files':dict(source['pinned_files'])}
    job={SELECTOR:GUIDANCE,'id':'fitness','style':'fitness','variant':'full','class_name':'Dataset','profile':'neutral',
        'schema_path':str(paths['full']),'input':str(record),'input_sha256':api.sha(record),
        'unit_path':'#','slot':'description','value_sha256':api.value_digest({'unknown':'UNCHANGED_VALUE'}),
        'project':'SYNTHETIC','max_tokens':8000}
    job['instrument']=api.slot_instrument(job);m['evaluation_jobs']=[job]
    return m,job,paths,child,parent


def test_actual_request_contains_complete_declared_guide_and_unchanged_value(selected_case):
    m,j,_,_,_=selected_case
    request=api.render_request(m,j)
    text=json.dumps(request)
    assert 'Required operational label.' in text and 'Optional maintenance meaning.' in text
    assert 'UNCHANGED_VALUE' in text
    assert 'unknown' in text
    assert j['instrument'][SELECTOR]==GUIDANCE
    assert 'bundle' not in request and 'held-out' not in text
    assert source_pair.fitness_schema_authority(m)[0]['full']==Path(j['schema_path'])


@pytest.mark.parametrize('value',[None,False,0,{},[], 'unknown','Nested_semantics_v1'])
def test_invalid_selectors_fail_before_setup_or_destination(tmp_path,monkeypatch,value):
    monkeypatch.setattr(prepare,'runtime_snapshot',lambda *a:pytest.fail('runtime setup reached'))
    destination=tmp_path/'not-created'
    with pytest.raises(ValueError,match='guidance'):
        prepare.build_registration(destination,generation_registration='missing',generation_acceptance='missing',
            generation_job_id='g',context_path='missing',billing_checkpoint='missing',fitness_schema_guidance=value)
    with pytest.raises(ValueError,match='guidance'):
        prepare.build_composite_registration(destination,finalization_registration='missing',
            finalization_acceptance='missing',context_path='missing',fitness_schema_guidance=value)
    assert not destination.exists()
    with pytest.raises(reg.BudgetStop,match='guidance'):
        reg.verify_manifest({SELECTOR:value,'evaluation_jobs':[]},'missing','missing')


@pytest.mark.parametrize('change',['manifest_absent','job_absent','job_null','wrong_style','instrument_missing','instrument_legacy'])
def test_direct_request_and_aggregate_selection_refuse_downgrades(selected_case,tmp_path,change):
    m,j,*_=deepcopy(selected_case)
    if change=='manifest_absent':m.pop(SELECTOR)
    elif change=='job_absent':j.pop(SELECTOR)
    elif change=='job_null':j[SELECTOR]=None
    elif change=='wrong_style':j['style']='grounding'
    elif change=='instrument_missing':j.pop('instrument')
    else:j['instrument'].pop(SELECTOR)
    with pytest.raises((ValueError,KeyError,reg.BudgetStop)):
        api.render_request(m,j)
    with pytest.raises((ValueError,KeyError,reg.BudgetStop)):
        closure.validate_output(m,j,tmp_path/'missing.json')


@pytest.mark.parametrize('style',['grounding','direct_api_quality','semantic_agent','field_agent'])
def test_unrelated_job_selector_refused_in_both_actual_roster_and_dispatch(style):
    m={SELECTOR:GUIDANCE,'evaluation_jobs':[{SELECTOR:GUIDANCE,'style':style}]}
    with pytest.raises(ValueError,match='only'):
        source_pair.validate_roster(m)
    with pytest.raises(ValueError,match='only'):
        api._schema_selection(m,m['evaluation_jobs'][0])
    with pytest.raises(ValueError,match='only'):
        closure.build_aggregate(m,Path('/unused'))


@pytest.mark.parametrize('mutation',['import_bytes','import_pin','root_path','class','registration_sha'])
def test_import_and_root_authority_are_checked_before_capture_send(selected_case,mutation):
    m,j,paths,child,parent=selected_case
    if mutation=='import_bytes':child.write_text(child.read_text().replace('Optional maintenance meaning.','Changed child role.'))
    elif mutation=='import_pin':m['pinned_files'].pop(str(child))
    elif mutation=='root_path':j['schema_path']=str(paths['core'])
    elif mutation=='class':j['class_name']='CoreDataset'
    else:m['source_generation']['registration_sha256']='0'*64
    with pytest.raises((ValueError,reg.BudgetStop)):
        api.render_request(m,j)


def test_selected_snapshot_is_single_shared_instrument_and_prompt_capture(selected_case,monkeypatch):
    m,j,*_=selected_case
    snapshot=api.fitness_snapshot(j);seen=[]
    original=api.slot_instrument
    def instrument(job,**kw):
        seen.append(kw['schema_snapshot']);return original(job,**kw)
    monkeypatch.setattr(api,'slot_instrument',instrument)
    monkeypatch.setattr(api,'fitness_snapshot',lambda *a:pytest.fail('unexpected second capture'))
    api.render_request(m,j,schema_snapshot=snapshot)
    assert seen==[snapshot]


def selected_parent(case):
    m,j,*_=case
    parent={'version':1,'job_id':j['id'],'style':'fitness',
        **{k:j[k] for k in ('input_sha256','unit_path','slot','value_sha256')},
        'instrument':dict(j['instrument']), 'judgement':{'fitness':.5,'failure':'form','reason':'Exact parent reason.'}}
    p=Path(j['input']).with_name('parent_fitness.json');write(p,parent)
    sub={**j,'id':'subtype','style':'subtype','fitness_job_id':j['id'],'fitness_result':str(p),'fitness_result_sha256':api.sha(p)}
    sub['instrument']=api.slot_instrument(sub)
    m=deepcopy(m);m['evaluation_jobs']=[sub]
    return m,sub,p,parent


def test_selected_subtype_retains_parent_reason_version_and_class(selected_case):
    m,j,p,parent=selected_parent(selected_case)
    request=api.render_request(m,j)
    assert 'Exact parent reason.' in json.dumps(request)
    failure=api._fitness_failure(j,api.selected_value(j),j['instrument'])
    assert failure.schema_guidance==GUIDANCE and failure.class_name=='Dataset'


@pytest.mark.parametrize('key,value',[('fitness_schema_guidance',None),('fitness_schema_guidance','other'),
    ('specification','0'*64),('schema','0'*32)])
def test_subtype_rejects_changed_parent_instrument_before_cache(selected_case,key,value):
    m,j,p,parent=selected_parent(selected_case)
    parent['instrument'][key]=value;write(p,parent);j['fitness_result_sha256']=api.sha(p)
    with pytest.raises(ValueError):api.render_request(m,j)


def bind_source_schemas(args):
    p=args['generation_registration'];m=reg.read_json(p);paths,child=schemas(Path(m['repository']))
    m['pinned_files'].update({str(p):reg.sha(p) for p in [*paths.values(),child]});write(p,m)
    for ledger in (Path(m['budget']['ledger_path']),args['billing_checkpoint']):
        content=reg.read_json(ledger);content['manifest_sha256']=reg.sha(p);write(ledger,content)
    acceptance=reg.read_json(args['generation_acceptance']);acceptance['registration_sha256']=reg.sha(p)
    write(args['generation_acceptance'],acceptance)
    return paths,child


def test_real_ordinary_preparation_selects_only_fitness_and_pins_accepted_imports(accepted_fixture):
    paths,child=bind_source_schemas(accepted_fixture)
    result=prepare.build_registration(**accepted_fixture,fitness_schema_guidance=GUIDANCE)
    m=reg.read_json(result['registration'])
    assert m[SELECTOR]==GUIDANCE
    assert len(m['evaluation_jobs'])==32
    assert m['pinned_files'][str(child)]==reg.sha(child)
    for job in m['evaluation_jobs']:
        assert (SELECTOR in job)==(job['style']=='fitness')
        if job['style']=='fitness':
            assert job['schema_path']==str(paths[job['variant']])
            assert job['instrument'][SELECTOR]==GUIDANCE
            assert reg.read_json(job['expected_request'])==api.render_request(m,job)
    assert not Path(m['budget']['ledger_path']).exists()
    assert not Path(m['source_generation']['evaluation_sequence_state']).exists()


def test_selected_preparation_refuses_unpinned_import_before_creating_condition(accepted_fixture):
    _,child=bind_source_schemas(accepted_fixture)
    p=accepted_fixture['generation_registration'];m=reg.read_json(p);m['pinned_files'].pop(str(child));write(p,m)
    for ledger in (Path(m['budget']['ledger_path']),accepted_fixture['billing_checkpoint']):
        content=reg.read_json(ledger);content['manifest_sha256']=reg.sha(p);write(ledger,content)
    acceptance=reg.read_json(accepted_fixture['generation_acceptance']);acceptance['registration_sha256']=reg.sha(p)
    write(accepted_fixture['generation_acceptance'],acceptance)
    with pytest.raises(reg.BudgetStop,match='import closure'):
        prepare.build_registration(**accepted_fixture,fitness_schema_guidance=GUIDANCE)
    assert not accepted_fixture['destination'].exists()


def test_real_composite_preparation_preserves_accepted_phase4_schema_authority(selected_composite):
    composite=selected_composite
    owner_before=composite['state'].read_bytes()
    args={k:v for k,v in composite.items() if k not in ('state','phase')}
    result=prepare.build_composite_registration(**args,fitness_schema_guidance=GUIDANCE)
    m=reg.read_json(result['registration'])
    for job in m['evaluation_jobs']:
        if job['style']=='fitness':
            assert job['schema_path']==composite['phase']['inputs'][job['variant']+'_schema']
            assert job['instrument'][SELECTOR]==GUIDANCE
    source_pair.validate_roster(m)
    assert composite['state'].read_bytes()==owner_before
    assert reg.read_json(composite['state'])['active_tip']['registration_sha256']==reg.sha(composite['finalization_registration'])


def test_execution_captures_selected_snapshot_before_provider_resolution(selected_case,tmp_path,monkeypatch):
    m,j,*_=selected_case
    path=write(tmp_path/'request.json',api.render_request(m,j));j['expected_request']=str(path)
    context=SimpleNamespace(manifest=m,job=j,attempt=tmp_path/'attempt',verify=lambda:None)
    original=api.fitness_snapshot;captured=[]
    def capture(job):
        snap=original(job);captured.append(snap);return snap
    monkeypatch.setattr(api,'fitness_snapshot',capture)
    class ReachedProvider(Exception):pass
    def provider(*a,**kw):
        assert len(captured)==1
        raise ReachedProvider
    monkeypatch.setattr(api,'provider_clients',provider)
    monkeypatch.setenv('CBORG_API_KEY','synthetic-unused')
    with pytest.raises(ReachedProvider):api._execute_job(context,{})
    assert len(captured)==1
    j['instrument'].pop(SELECTOR)
    with pytest.raises(ValueError,match='instrument'):api._execute_job(context,{})
    assert len(captured)==1


def test_direct_registered_instrument_rejects_unpinned_import_without_provider(selected_case):
    m,j,_,child,_=selected_case
    assert str(child) in {str(p) for p in reg._fitness_resources(m)}
    m['pinned_files'].pop(str(child))
    with pytest.raises(reg.BudgetStop,match='not pinned'):reg._fitness_resources(m)


def test_subtype_dependency_rejects_parent_selector_downgrade_before_receipt(selected_case,monkeypatch):
    m,j,p,parent=selected_parent(selected_case)
    j['canary']=True
    old=deepcopy(m);old.pop(SELECTOR)
    old['evaluation_jobs'][0].pop(SELECTOR)
    old['evaluation_jobs'][0]['style']='fitness'
    m['prior_evaluation']={'registration_sha256':'old'}
    monkeypatch.setattr(reg,'_prior',lambda *a:old)
    monkeypatch.setattr(reg,'receipt_for',lambda *a:pytest.fail('receipt reached before selector mismatch'))
    with pytest.raises(reg.BudgetStop,match='parent fitness schema guidance'):
        reg.verify_dependencies(m,'new',j)


def test_selected_subtype_exact_parent_instrument_checked_before_cache(selected_case,monkeypatch):
    m,j,p,parent=selected_parent(selected_case);j['canary']=True
    old=deepcopy(m);old['evaluation_jobs']=[{**j,'id':j['fitness_job_id'],'style':'fitness','output':str(p)}]
    old['evaluation_jobs'][0]['instrument']=dict(parent['instrument'])
    m['prior_evaluation']={'registration_sha256':'old'}
    receipt={'output_sha256':api.sha(p)}
    m['pinned_files'][str(p)]=api.sha(p)
    monkeypatch.setattr(reg,'_prior',lambda *a:old)
    monkeypatch.setattr(reg,'receipt_for',lambda *a:(p,receipt))
    j['instrument']['specification']='0'*64
    with pytest.raises(reg.BudgetStop,match='parent fitness instrument'):
        reg.verify_dependencies(m,'new',j)


def test_selected_actual_api_aggregate_and_subtype_preparer_keep_exact_instrument(tmp_path,monkeypatch):
    import test_closure
    from evaluation_controls import api as package_api, prepare_subtype
    authority=tmp_path/'accepted-schema';authority.mkdir()
    paths,child=schemas(authority)
    sourcepins={str(p):reg.sha(p) for p in [*paths.values(),child]}
    source=write(authority/'registration.json',{'kind':'d4d_native_finalization',
        'repository':str(authority),'inputs':{v+'_schema':str(p) for v,p in paths.items()},
        'pinned_files':sourcepins})
    original_setup=test_closure.setup_job
    def selected_setup(directory,*args,**kw):
        context=original_setup(directory,*args,**kw)
        job=context.job;variant='core' if job['class_name']=='CoreDataset' else 'full'
        job.update({SELECTOR:GUIDANCE,'variant':variant,'schema_path':str(paths[variant])})
        job['instrument']=package_api.slot_instrument(job)
        return context
    original_finish=test_closure.foundation.finish_registration
    def selected_finish(m,path):
        if m.get('kind')=='d4d_evaluation_registration':
            m.update({SELECTOR:GUIDANCE,'repository':str(prepare.ROOT)})
            m['source_pair']['finalization']={'registration':{'path':str(source),'sha256':reg.sha(source)}}
            m['pinned_files'].update(sourcepins)
            for job in m['evaluation_jobs']:
                # Source/roster identity is covered by the actual composite
                # preparation test; this fixture executes real SDK/ledger
                # cleanup, complete aggregation, and subtype rendering.
                if 'expected_request' in job:
                    write(Path(job['expected_request']),package_api.render_request(m,job))
                    m['pinned_files'][job['expected_request']]=reg.sha(job['expected_request'])
        return original_finish(m,path)
    monkeypatch.setattr(test_closure,'setup_job',selected_setup)
    monkeypatch.setattr(test_closure.foundation,'finish_registration',selected_finish)
    e,er,state=test_closure.completed_evaluation(tmp_path,monkeypatch)
    aggregate=closure.build_aggregate(e,er)
    assert len(aggregate['selected_form_failures'])==2
    assert all(row[SELECTOR]==GUIDANCE and row['instrument'][SELECTOR]==GUIDANCE
               for row in aggregate['selected_form_failures'])
    args=test_closure.prepare_from_fixture(e,er,state,tmp_path,monkeypatch)
    before=state.read_bytes(),Path(e['budget']['ledger_path']).read_bytes()
    result=prepare_subtype.prepare(**args)
    m=reg.read_json(result['registration'])
    assert m[SELECTOR]==GUIDANCE and result['jobs']==2
    for job in m['evaluation_jobs']:
        assert job[SELECTOR]==GUIDANCE
        parent=reg.read_json(job['fitness_result'])
        assert job['instrument']['schema']==parent['instrument']['schema']
        assert job['instrument']['specification']==parent['instrument']['specification']
        assert reg.read_json(job['expected_request'])==package_api.render_request(m,job)
        assert 'Appropriate description.' in json.dumps(reg.read_json(job['expected_request']))
    assert before==(state.read_bytes(),Path(e['budget']['ledger_path']).read_bytes())
    assert result['provider_calls']==result['token_count_calls']==0
    assert not Path(m['budget']['ledger_path']).exists()
