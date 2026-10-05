"""Pure stage overlay invariants; no files, runtime, or permission claims."""
from dataclasses import replace
import shlex

import pytest

from data_sheets_schema import native_shared_effects as effects
from data_sheets_schema.native_shared_contract import (
    NAME, ArtifactPin, NativeEffectView, ResponseDestination, RolePath,
    StageCursor, role_paths, sha,
)


def view(kind='worker'):
    root='/selected/stages'
    return NativeEffectView(protocol=NAME, selection_sha256='a'*64,
        execution_binding_sha256='b'*64, static_policy_sha256='c'*64,
        stage_root=root,working_directory='/selected/cwd',
        stage_command=shlex.join(['/selected/python','-m',effects.MODULE,'advance',
                                 '--registration','/selected/selection.json']),
        state='awaiting_response',cursor=StageCursor(ordinal=1,kind=kind,target_id='selected-target'),
        request=ArtifactPin(role='request',path=root+'/requests/000001.json',bytes=2,sha256=sha(b'{}')),
        response=ResponseDestination(role='response',path=root+'/responses/000001.bin',
                                     max_bytes=64,media_type='application/json'),
        sealed=(ArtifactPin(role='phase1_full',path=root+'/sealed/full.yaml',bytes=2,sha256=sha(b'{}')),),
        protected_roles=role_paths('/selected/selection.json',root)+(RolePath('source','/selected/source.md'),),
        history_sha256='d'*64,request_read_observation_sha256=None,
        response_intent_observation_sha256=None,pending_advance_tool_use_id=None,
        correction_window=False)


def classified(selected, name, payload):
    return effects.classify_effect(selected, tool_name=name, tool_input=payload)[0]


@pytest.mark.parametrize('kind',['receipt','worker','omission','integration'])
def test_same_current_delivery_rules_for_all_four_stages(kind):
    selected=view(kind)
    assert classified(selected,'Read',{'file_path':selected.request.path})=='prescribed'
    answer={'file_path':selected.response.path,'content':'{}'}
    assert classified(selected,'Write',answer)=='not_prescribed'
    read=replace(selected,request_read_observation_sha256='e'*64)
    assert classified(read,'Write',answer)=='prescribed'
    assert classified(replace(read,response_intent_observation_sha256='f'*64),'Write',answer)=='not_prescribed'
    assert classified(read,'Bash',{'command':selected.stage_command})=='prescribed'


@pytest.mark.parametrize('state',['request_ready','receipt_zero_work','await_core','assembly_complete','failed'])
def test_no_response_states_cannot_write(state):
    selected=replace(view(),state=state,cursor=None,request=None,response=None)
    assert classified(selected,'Write',{'file_path':selected.stage_root+'/responses/000001.bin','content':'{}'})=='not_prescribed'
    result=classified(selected,'Bash',{'command':selected.stage_command})
    assert result==('not_prescribed' if state=='failed' else 'prescribed')


@pytest.mark.parametrize('name,path',[
    ('Read','/selected/stages/requests/000002.json'),
    ('Read','/selected/stages/responses/000001.bin'),
    ('Read','/selected/stages/unknown.json'),
    ('Write','/selected/stages/requests/000001.json'),
    ('Write','/selected/stages/sealed/full.yaml'),
    ('Write','/selected/stages/journal.json'),
    ('Write','/selected/stages/responses/000002.bin'),
    ('Write','/selected/source.md'),
    ('Write','/selected/selection.json'),
])
def test_closed_namespace_and_immutable_authority_denials(name,path):
    selected=replace(view(),request_read_observation_sha256='e'*64)
    payload={'file_path':path,**({'content':'{}'} if name=='Write' else {})}
    assert effects.governs_stage_effect(selected,tool_name=name,tool_input=payload)
    assert classified(selected,name,payload)=='not_prescribed'


@pytest.mark.parametrize('path',[None,True,'relative','/selected//source.md',
    '/selected/./source.md','/selected/../source.md','//selected/source.md','/selected/source.md\n'])
def test_malformed_paths_refuse_before_nonstage_routing(path):
    with pytest.raises(ValueError,match='path'):
        effects.governs_stage_effect(view(),tool_name='Read',tool_input={'file_path':path})


def test_nonstage_does_not_gain_authority_from_stage_approval():
    selected=view()
    for name,payload in [('Read',{'file_path':'/selected/source.md'}),
                         ('Write',{'file_path':'/selected/report.md','content':'report'}),
                         ('Bash',{'command':'/selected/python -m genuine_helper --checked'})]:
        assert effects.governs_stage_effect(selected,tool_name=name,tool_input=payload) is False
        assert classified(selected,name,payload)=='not_prescribed'


def test_sealed_reads_do_not_grant_stale_request_reads():
    selected=view()
    assert classified(selected,'Read',{'file_path':selected.sealed[0].path})=='prescribed'
    with pytest.raises(ValueError,match='sealed-read'):
        effects.governs_stage_effect(replace(selected,sealed=(selected.request,)),
                                    tool_name='Read',tool_input={'file_path':selected.request.path})


@pytest.mark.parametrize('changes',[{'pending_advance_tool_use_id':'active-call'},
                                    {'correction_window':True}])
def test_pending_advance_and_report_only_correction_stop_stage_mutation(changes):
    selected=replace(view(),request_read_observation_sha256='e'*64,**changes)
    assert classified(selected,'Write',{'file_path':selected.response.path,'content':'{}'})=='not_prescribed'
    assert classified(selected,'Bash',{'command':selected.stage_command})=='not_prescribed'


@pytest.mark.parametrize('content',['', 'x'*65, '\ud800'])
def test_complete_response_byte_bound(content):
    selected=replace(view(),request_read_observation_sha256='e'*64)
    assert classified(selected,'Write',{'file_path':selected.response.path,'content':content})=='not_prescribed'


@pytest.mark.parametrize('extra',[{'offset':1},{'limit':12},{'offset':1,'limit':10000}])
def test_fragmented_current_reads_do_not_claim_whole_delivery(extra):
    selected=view()
    assert classified(selected,'Read',{'file_path':selected.request.path,**extra})=='not_prescribed'


@pytest.mark.parametrize('mutate',[lambda v:v.stage_command+' --other',
    lambda v:v.stage_command+' > /selected/report.md',
    lambda v:'cat '+v.request.path])
def test_no_changed_stage_bash_falls_through(mutate):
    selected=view();payload={'command':mutate(selected)}
    assert effects.governs_stage_effect(selected,tool_name='Bash',tool_input=payload)
    assert classified(selected,'Bash',payload)=='not_prescribed'


def test_background_stage_helper_is_never_admitted():
    selected=view()
    assert classified(selected,'Bash',{'command':selected.stage_command,'run_in_background':True})=='not_prescribed'


def test_missing_protected_role_and_forged_current_path_refuse():
    selected=view()
    for altered in (replace(selected,protected_roles=selected.protected_roles[1:]),
        replace(selected,response=replace(selected.response,path='/selected/report.md'))):
        with pytest.raises(ValueError):
            effects.governs_stage_effect(altered,tool_name='Bash',tool_input={'command':selected.stage_command})
