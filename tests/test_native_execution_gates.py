"""Focused typed stream-boundary checks, independent of permission evidence.

These are deliberately incomplete gate fixtures, never a complete native run.
The real helper/callback/receipt conjunction is exercised in test_native_execution.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_execution_gates as gates
from data_sheets_schema import native_execution_authority as authority


def selected():
    session='00000000-0000-4000-8000-000000000001'
    runtime={'model':'synthetic-model','auth':{'expected_api_key_source':'none'},
             'executable':{'init_version':'synthetic-v1'}}
    events=[{'type':'system','subtype':'init','cwd':'/synthetic','session_id':session,
             'model':'synthetic-model','apiKeySource':'none','claude_code_version':'synthetic-v1',
             'tools':['Read','Write','Bash']},
            {'type':'assistant','session_id':session,'message':{'role':'assistant','model':'synthetic-model',
             'content':[{'type':'text','text':'Synthetic completion text.'}]}},
            {'type':'result','session_id':session,'is_error':False,'terminal_reason':'completed','stop_reason':'end_turn'}]
    prepared={'snapshot':object(),'state':SimpleNamespace(spec=SimpleNamespace(),reg={'working_directory':'/synthetic'}),
              'events':events,'policy':{}}
    return prepared,runtime


def verdict(prepared,runtime):
    with authority.loaded_dependencies(authority.dependency_identity()) as controls:
        return gates.check(prepared,{},runtime,controls,exit_code=0,shutdown=None,
                           live={},first_stop=None,runtime_authority={'passed':False},keep_awake={'passed':False})


def test_settled_native_parent_narration_is_compatible_but_not_full_acceptance():
    prepared,runtime=selected();out=verdict(prepared,runtime)
    assert out['terminal']['passed'] is True
    assert not all(row['passed'] for row in out.values())


@pytest.mark.parametrize('change',['session_absent','session_other','cwd_other','parent_tool',
    'parent_terminal','wrong_message_role','wrong_message_model','wrong_frame_model','error_subtype',
    'error_payload','bad_permission','version_other','error_bool_alias','duplicate_terminal',
    'tools_missing','tools_duplicate','unknown_subtype'])
def test_contradictory_native_identity_never_becomes_a_success(change):
    prepared,runtime=selected();events=prepared['events']
    if change=='session_absent':del events[-1]['session_id']
    elif change=='session_other':events[1]['session_id']='different'
    elif change=='cwd_other':events[0]['cwd']='/foreign'
    elif change=='parent_tool':events[1]['parent_tool_use_id']='other-parent'
    elif change=='parent_terminal':events[-1]['parent_tool_use_id']='other-parent'
    elif change=='wrong_message_role':events[1]['message']['role']='user'
    elif change=='wrong_message_model':events[1]['message']['model']='foreign'
    elif change=='wrong_frame_model':events[-1]['model']='foreign'
    elif change=='error_subtype':events[-1]['subtype']='error_during_execution'
    elif change=='unknown_subtype':events[-1]['subtype']='unknown_result'
    elif change=='error_payload':events[-1]['error']={'message':'bad'}
    elif change=='bad_permission':events[0]['permissionMode']='bypassPermissions'
    elif change=='version_other':events[0]['claude_code_version']='foreign'
    elif change=='error_bool_alias':events[-1]['is_error']=0
    elif change=='duplicate_terminal':events.append(deepcopy(events[-1]))
    elif change=='tools_missing':events[0]['tools'].remove('Write')
    elif change=='tools_duplicate':events[0]['tools'].append('Read')
    assert verdict(prepared,runtime)['terminal']['passed'] is False


@pytest.mark.parametrize('change',['none','passed_false','auth_changed','whitespace','malformed'])
def test_runtime_gate_binds_exact_captured_observation(change):
    from data_sheets_schema import native_attribution_registration as draft
    admitted={'checked':True,'passed':True,'auth':{'loggedIn':True}}
    captured=deepcopy(admitted)
    if change=='passed_false':captured['passed']=False
    elif change=='auth_changed':captured['auth']['loggedIn']=False
    raw=draft._encoded(captured)
    if change=='whitespace':raw+=b'\n'
    elif change=='malformed':raw=b'not a JSON observation'
    result=gates.runtime_observation_result(raw,admitted)
    assert result['passed'] is (change=='none')
    assert result['matches_admitted'] is (change=='none')
    assert result['admitted_observation']==admitted
    assert result['captured_sha256']==draft._sha(raw)
    assert result['admitted_sha256']==draft._sha(draft._encoded(admitted))


@pytest.mark.parametrize('change',['none','failed','whitespace','wrong_policy','wrong_state',
    'missing_acquisition','missing_release','bool_release','failed_release','not_applicable','na_release'])
def test_cleanup_gate_binds_exact_outcome_and_registered_policy(change):
    from data_sheets_schema import native_attribution_registration as draft
    policy={'policy':'macos_iokit_ims_v1','host_platform':'darwin','basis':'synthetic'}
    assertions=[{'type':kind,'id':index} for index,kind in enumerate(gates.IOKIT_ASSERTIONS,1)]
    observed={'passed':True,'policy':deepcopy(policy),'state':'released',
        'acquisition':{'policy':policy['policy'],'status':'acquired','pid':123,'acquired_at':'synthetic acquisition',
                       'assertions':assertions,'limitations':'Synthetic only','cleanup_receipt':'keep_awake_cleanup.json'},
        'released_at':'synthetic release','releases':[{**row,'return_code':0} for row in reversed(assertions)]}
    if change=='failed':observed['passed']=False
    elif change=='wrong_policy':observed['policy']['basis']='different'
    elif change=='wrong_state':observed['state']='acquired'
    elif change=='missing_acquisition':observed['acquisition']={}
    elif change=='missing_release':observed['releases'].pop()
    elif change=='bool_release':observed['releases'][0]['return_code']=False
    elif change=='failed_release':observed['releases'][0]['return_code']=1
    elif change in ('not_applicable','na_release'):
        policy={**policy,'policy':'not_applicable'}
        observed={'passed':True,'policy':deepcopy(policy),'state':'explicitly_not_applicable'}
        if change=='na_release':observed['releases']=[{'return_code':0}]
    raw=draft._encoded(observed)
    if change=='whitespace':raw+=b'\n'
    result=gates.cleanup_result(raw,observed,policy)
    assert result['passed'] is (change in ('none','not_applicable'))
    assert result['observed_cleanup']==observed
    assert result['registered_policy']==policy
    assert result['captured_sha256']==draft._sha(raw)
    assert result['observed_sha256']==draft._sha(draft._encoded(observed))


@pytest.mark.parametrize('mutation',['none','not_held','wrong_policy','duplicate_release','duplicate_acquisition',
    'wrong_release_id','wrong_release_type','missing_assertion','foreign_assertion','release_error',
    'null_release_error','acquisition_error','bool_id','float_id','zero_id','overflow_id',
    'bool_pid','missing_acquired_at','missing_released_at','na_acquisition','na_empty_acquisition','na_release_time'])
def test_cleanup_requires_real_producer_shape_and_matching_error_free_releases(mutation):
    from data_sheets_schema import native_attribution_registration as draft
    # Invoke the actual pinned guard, supplying only the IOKit boundary; no
    # library, host assertion or native executable is accessed by this test.
    class FakeIOKit:
        count=0
        def create(self,kind):
            self.count+=1
            return self.count
        def release(self,identity):return 0
    with authority.loaded_dependencies(authority.dependency_identity()) as controls:
        producer=controls['run_direct_canary_awake']
        assert producer.ASSERTIONS==gates.IOKIT_ASSERTIONS
        guard=producer.KeepAwake(api=FakeIOKit())
        guard.__enter__();acquisition=guard.snapshot();guard.close()
        policy={'policy':producer.POLICY,'host_platform':'darwin','basis':'Synthetic only'}
    observed={'passed':True,'policy':deepcopy(policy),'state':'released','acquisition':acquisition,
              'releases':guard.releases,'released_at':guard.released_at,'signals_received':[]}
    a=observed['acquisition'];releases=observed['releases']
    if mutation=='not_held':a['status']='not_held'
    elif mutation=='wrong_policy':a['policy']='foreign'
    elif mutation=='duplicate_release':releases[1]=deepcopy(releases[0])
    elif mutation=='duplicate_acquisition':
        a['assertions'][1]['id']=a['assertions'][0]['id']
        releases[1]['id']=a['assertions'][1]['id']
    elif mutation=='wrong_release_id':releases[0]['id']=999
    elif mutation=='wrong_release_type':releases[0]['type']=releases[1]['type']
    elif mutation=='missing_assertion':a['assertions'].pop()
    elif mutation=='foreign_assertion':a['assertions'][0]['type']='UnregisteredAssertion'
    elif mutation=='release_error':releases[0]['error_type']='RuntimeError'
    elif mutation=='null_release_error':releases[0]['error_type']=None
    elif mutation=='acquisition_error':a['error_type']='RuntimeError'
    elif mutation=='bool_id':a['assertions'][0]['id']=True
    elif mutation=='float_id':a['assertions'][0]['id']=1.0
    elif mutation=='zero_id':a['assertions'][0]['id']=0
    elif mutation=='overflow_id':a['assertions'][0]['id']=2**32
    elif mutation=='bool_pid':a['pid']=True
    elif mutation=='missing_acquired_at':del a['acquired_at']
    elif mutation=='missing_released_at':del observed['released_at']
    elif mutation.startswith('na_'):
        policy={**policy,'policy':'not_applicable'}
        observed.update(policy=deepcopy(policy),state='explicitly_not_applicable',releases=[])
        if mutation!='na_release_time':del observed['released_at']
        if mutation=='na_empty_acquisition':observed['acquisition']={}
        elif mutation=='na_release_time':del observed['acquisition']
    result=gates.cleanup_result(draft._encoded(observed),observed,policy)
    assert result['outcome_matches'] is (mutation=='none')
    assert result['passed'] is (mutation=='none')
    # Invalid outcomes remain inspectable failed evidence, including when the
    # producer has already marked the unsuccessful observation as failed.
    observed['passed']=False
    assert gates.cleanup_result(draft._encoded(observed),observed,policy)['passed'] is False
