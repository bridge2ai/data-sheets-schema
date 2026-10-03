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
