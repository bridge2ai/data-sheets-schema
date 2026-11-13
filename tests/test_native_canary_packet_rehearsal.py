"""G13 explicitly synthetic saved-input rehearsal, never launch authority.

No executable peer runs and no reservation is made. The protected constructor
refusal is observed unchanged. Separate CLI spies prove routing only, with the
unavailable registration/metadata/runtime front-door gates explicitly isolated.
They are not end-to-end admission or a workaround for production validation.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_runtime_profiles as profiles
from data_sheets_schema import native_u4b_runtime as runtime_api
from tests.test_native_synthetic_profiles import runtime as provisional_fixture
from tests.utils.native_synthetic_evidence import runtime_for
from tests.utils.native_u4b_fixtures import bundle_for
from tests.test_native_canary_packet_builder import invoke

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('review_adapter',ROOT/'scripts/native_packet_review_inputs.py')
adapter=importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
LABEL='SYNTHETIC REHEARSAL ONLY; NO HUMAN APPROVAL, CI SUCCESS OR LAUNCH AUTHORITY'


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    provisional=provisional_fixture.__wrapped__(tmp_path)
    seed=tmp_path/'synthetic-runtime-seed.json'; seed.write_bytes(c.canonical(provisional))
    runtime=runtime_for({'runtime_path':seed},tmp_path)
    assert profiles.require_synthetic(runtime)==runtime
    assert runtime_api.validate_prepared_runtime(runtime)==runtime
    raw=c.canonical(runtime)
    path=tmp_path/'SYNTHETIC-final-runtime.json'; path.write_bytes(raw)
    (tmp_path/'REHEARSAL-NOT-AUTHORITY.txt').write_text(LABEL+'\n')
    return runtime,path


def test_synthetic_preparation_stops_at_unchanged_protected_constructor(synthetic,tmp_path):
    from data_sheets_schema import native_execution_registration_v2 as execution
    runtime,path=synthetic
    out=tmp_path/'packet'
    result=invoke(out)
    assert result.returncode==2,result.stdout+result.stderr
    with pytest.raises(TypeError, match="unexpected keyword argument 'native_shared_generation_version'") as refusal:
        execution.prepare_synthetic(out/'selection.json',path,job_id='synthetic-rehearsal',run_date='2026-11-12',max_draft_checks=1)
    (tmp_path/'protected-refusal.json').write_text(json.dumps({'scope':LABEL,'producer':'native_execution_registration_v2.prepare_synthetic','refusal':str(refusal.value),'reservation_performed':False},indent=2)+'\n')
    # The ordinary production entry rejects these bytes before constructing RunSpec.
    with pytest.raises(ValueError,match='production|synthetic'):
        execution.prepare(out/'selection.json',path,job_id='synthetic-rehearsal',run_date='2026-11-12',max_draft_checks=1)
    assert not (tmp_path/'never-reserved-attempt').exists()


@pytest.fixture
def documents(synthetic,tmp_path):
    runtime,path=synthetic
    from data_sheets_schema import native_subscription_guard as wire
    value={'attempt_id':'SYNTHETIC-REHEARSAL-NOT-AUTHORITY','runtime':runtime,
        'dependencies':{'base':{'source_commit':'a'*40}},'permission_probe_sha256':'2'*64,
        'scope':LABEL,'selection':{'render_spec':{'scope':LABEL}}}
    registration=c.canonical({'authority_version':2,'controller_sources_sha256':'f'*64,'registration':value})
    now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    review,word=bundle_for(registration,tmp_path/'synthetic-capture',now=now)
    ci=c.canonical({'scope':LABEL,'kind':'SYNTHETIC-CI-NOT-EVIDENCE','checks':{},'status':'not_run'})
    coded=c.strict_json(word); coded['ci_sha256']=c.sha(ci); word=c.canonical(coded)
    adapter.validate_supplied(registration,review,word)
    choice=c.canonical({'kind':'d4d_native_u4_owner_choice','version':1,'decisions':['D105','D106'],
        'account_label':'LBL work Claude Max','effort':'high','receipt_instrument':4,
        'subject_sha256':wire.sha(registration),'runtime_sha256':wire.sha(wire.canonical(runtime))})
    data={'registration':registration,'review':review,'launch-word':word,'ci':ci,'account-choice':choice,
          'capture':c.canonical({'scope':LABEL,'status':'not_captured'}),
          'subscription-guard':c.canonical({'scope':LABEL,'status':'not_admitted'})}
    paths={name:tmp_path/('SYNTHETIC-'+name+'.json') for name in data}
    for name,raw in data.items(): paths[name].write_bytes(raw)
    assert b'Synthetic' in Path(c.strict_json(review)['reviews'][0]['document']['path']).read_bytes()
    assert b'SYNTHETIC' in ci and b'fixture owner' in word
    return value,data,paths


def test_review_adapter_checks_real_byte_binding(documents):
    value,data,paths=documents
    adapter.validate_supplied(data['registration'],data['review'],data['launch-word'])
    changed=c.strict_json(data['launch-word']); changed['review_sha256']='0'*64
    with pytest.raises(ValueError,match='differs'):
        adapter.validate_supplied(data['registration'],data['review'],c.canonical(changed))
    # Full production reconstruction must refuse the incomplete synthetic envelope.
    from data_sheets_schema import native_shared_registration_orchestration as registration
    with pytest.raises((ValueError,TypeError)):
        registration.verified(data['registration'])


@pytest.mark.parametrize('command', ['capture-subscription-event','prepare-subscription-guard-v2','launch'])
def test_three_cli_routes_stop_before_effect_boundary(documents,tmp_path,monkeypatch,command):
    from data_sheets_schema import native_generation as cli
    from data_sheets_schema import native_shared_registration_orchestration as registration
    from data_sheets_schema import native_shared_render as render
    from data_sheets_schema import native_permission_probe as permission
    from data_sheets_schema import native_subscription_capture as capture
    from data_sheets_schema import native_shared_execution_orchestration as execution
    value,data,paths=documents
    # These isolated gates are declared in saved evidence; never claim admission.
    monkeypatch.setattr(registration,'verified',lambda raw: value if raw==data['registration'] else pytest.fail('substituted registration'))
    monkeypatch.setattr(render,'validate_metadata',lambda x: None if x==value['selection']['render_spec'] else pytest.fail('substituted metadata'))
    monkeypatch.setattr(permission,'require_u4_runtime',lambda x: profiles.require_synthetic(x))
    class StopBeforeEffect(Exception): pass
    seen=[]
    def stop(**kwargs):
        seen.append(kwargs)
        raise StopBeforeEffect('SYNTHETIC routing only; stopped before reservation')
    def launch(raw,**kwargs):
        assert raw==data['registration']; return stop(**kwargs)
    def guard(path,**kwargs):
        assert path==str(paths['capture']); return stop(**kwargs)
    monkeypatch.setattr(capture,'capture_subscription',stop)
    monkeypatch.setattr(capture,'current_guard_preparation',guard)
    monkeypatch.setattr(execution,'launch',launch)
    def forbidden(*a,**kw): pytest.fail('reservation or process execution forbidden')
    monkeypatch.setattr(capture,'_reserve',forbidden)
    monkeypatch.setattr(subprocess,'Popen',forbidden) if command=='launch' else None
    args=[command]
    names=['registration','review','launch-word','account-choice']
    if command=='launch': names+=['ci','subscription-guard']
    if command=='prepare-subscription-guard-v2': names+=['capture']
    for name in names: args+=['--'+name,str(paths[name])]
    if command=='capture-subscription-event': args+=['--output-directory',str(tmp_path/'NEVER-CAPTURE')]
    if command=='prepare-subscription-guard-v2': args+=['--output',str(tmp_path/'NEVER-GUARD.json')]
    if command=='launch': args+=['--subscription-guard-sha256',c.sha(data['subscription-guard'])]
    with pytest.raises(StopBeforeEffect): cli.main(args)
    assert len(seen)==1
    if command=='capture-subscription-event':
        assert seen[0]==dict(registration_raw=data['registration'],review_bundle_raw=data['review'],launch_word_raw=data['launch-word'],directory=str(tmp_path/'NEVER-CAPTURE'))
    elif command=='prepare-subscription-guard-v2':
        assert seen[0]==dict(registration_raw=data['registration'],review_bundle_raw=data['review'],launch_word_raw=data['launch-word'])
    else:
        assert seen[0]==dict(review_path=str(paths['review']),ci_path=str(paths['ci']),launch_word_path=str(paths['launch-word']),subscription_guard_path=str(paths['subscription-guard']),subscription_guard_sha256=c.sha(data['subscription-guard']))
    assert not (tmp_path/'NEVER-CAPTURE').exists()
    assert not (tmp_path/'NEVER-GUARD.json').exists()
    (tmp_path/'routing-evidence.json').write_text(json.dumps({'scope':LABEL,'command':args,'stopped_before':'capture / guard / launch implementation; no reservation','isolated_gates':['registration.verified','render.validate_metadata','permission.require_u4_runtime'],'passed_gates':['account choice binding','runtime saved-evidence validation for capture/guard','review/word byte binding for capture/guard']},indent=2)+'\n')


def test_saved_review_command_keeps_synthetic_scope_and_refuses_overwrite(documents,tmp_path):
    import sys
    value,data,paths=documents
    inputs=tmp_path/'review-inputs.json'
    inputs.write_text(json.dumps({'registration_path':str(paths['registration']),
        'review_path':str(paths['review']),'launch_word_path':str(paths['launch-word'])}))
    out=tmp_path/'review-only-output'
    args=[sys.executable,'-P','-B',str(ROOT/'scripts/native_canary_saved_step.py'),
          '--checkout',str(ROOT),'--step','review','--inputs',str(inputs),'--output',str(out)]
    first=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert first.returncode==0,first.stdout+first.stderr
    before=(out/'review-validation.json').read_bytes()
    assert b'not human authentication' in before
    second=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert second.returncode!=0
    assert (out/'review-validation.json').read_bytes()==before


def test_expectation_wrapper_preserves_system_bytes_and_verified_consumer_scope(tmp_path,monkeypatch):
    """Wrapper regression only; fake consumer cannot establish actual admission."""
    from types import SimpleNamespace
    from data_sheets_schema import native_shared_controller_orchestration as controller
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_shared_permission_orchestration as permission
    from data_sheets_schema import native_permission_probe as probe
    module_spec=importlib.util.spec_from_file_location('saved_step',ROOT/'scripts/native_canary_saved_step.py')
    module=importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(module)
    composition=tmp_path/'composition.json'; composition.write_bytes(b'SYNTHETIC MOCK')
    system=tmp_path/'system.md'; system.write_bytes(b'SYNTHETIC\r\nexact system\r\n')
    dependencies={'base':{'package_sources':{'SYNTHETIC':'NOT-AUTHORITY'}}}
    composed={'runtime_raw_json':'{"scope":"SYNTHETIC"}','dependencies':dependencies,'policy':{}}
    spec=object(); controls=object(); active=[]; calls=[]
    monkeypatch.setattr(controller,'reconstruct_composition',lambda raw:(composed,spec,None))
    @contextmanager
    def inputs(value):
        assert value==dependencies; active.append('controls')
        try: yield controls,{}
        finally: active.pop()
    @contextmanager
    def verified(name,**kw):
        assert active==['controls']
        assert name=='data_sheets_schema.native_shared_registration'
        assert kw=={'package_sources':dependencies['base']['package_sources']}
        active.append('consumer')
        try: yield consumer
        finally: active.pop()
    def guidance(policy,*,classifier_projection):
        assert active==['controls','consumer'] and classifier_projection is controls
        return '\nSYNTHETIC GUIDANCE'
    def expectation(runtime,selected,run,effective,config,deps):
        assert active==['controls','consumer'] and selected is composed and run is spec
        assert effective=='SYNTHETIC\r\nexact system\r\n\nSYNTHETIC GUIDANCE'
        calls.append(effective)
        return {'scope':LABEL}
    consumer=SimpleNamespace(policy=SimpleNamespace(command_guidance=guidance),permission_expectation=expectation)
    monkeypatch.setattr(permission,'loaded_permission_inputs',inputs)
    monkeypatch.setattr(authority,'loaded_verified_package_module',verified)
    monkeypatch.setattr(probe,'require_u4_expectation',lambda value: None)
    result=module.produce('expectation',{'composition_path':str(composition),'system_path':str(system),'config_directory':str(tmp_path/'uncreated-config')})
    assert c.strict_json(result['expectation.json'])=={'scope':LABEL}
    assert len(calls)==1 and active==[]
    assert not (tmp_path/'uncreated-config').exists()
