"""Synthetic raw frames exercising exact prefix and native tool-result joins."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_observations as observed

SESSION='00000000-0000-4000-8000-000000000001'
POLICY={'pretool_control':{'event':'PreToolUse','callback_id':'fixed','matcher':'Bash|Read|Write','runtime_callback_timeout_seconds':125},
        'readonly_lookups':{'repository':'/neutral'}}


def prefix(stream,values):
    raw=b''.join(c.canonical(row)+b'\n' for row in values)
    return c.EvidencePrefix(stream,'/neutral/'+stream,raw,len(raw),c.sha(raw),len(values))


def artifact(role,path,raw):
    return c.CapturedArtifact(c.ArtifactPin(role,path,len(raw),c.sha(raw)),raw)


def events(tool='Read',raw=b'{"complete":"outer request"}\n'):
    path='/neutral/current.json' if tool=='Read' else '/neutral/response.bin'
    inputs={'file_path':path} if tool=='Read' else {'file_path':path,'content':raw.decode()}
    call={'type':'assistant','session_id':SESSION,'message':{'role':'assistant','content':[
        {'type':'tool_use','id':'tool-1','name':tool,'input':inputs}]}}
    callback={'type':'control_request','request_id':'callback-1','request':{'subtype':'hook_callback','callback_id':'fixed',
        'input':{'hook_event_name':'PreToolUse','cwd':'/neutral','tool_use_id':'tool-1','tool_name':tool,'tool_input':deepcopy(inputs)}}}
    record={'kind':'decision','request':deepcopy(callback),'classification':'prescribed','basis':'selected current effect',
        'response':{'type':'control_response','response':{'subtype':'success','request_id':'callback-1','response':{}}}}
    if tool=='Read':
        lines=raw.decode().split('\n');text='\n'.join(f'{i}\t{line}' for i,line in enumerate(lines,1))
        metadata={'type':'text','file':{'filePath':path,'content':raw.decode(),'numLines':len(lines),'startLine':1,'totalLines':len(lines)}}
    else:
        text='File created successfully at: '+path
        metadata={'type':'create','filePath':path,'content':raw.decode(),'originalFile':None,'structuredPatch':[],'userModified':False}
    result={'type':'user','session_id':SESSION,'message':{'role':'user','content':[
        {'type':'tool_result','tool_use_id':'tool-1','content':text}]},'tool_use_result':metadata}
    return [call,callback,result],[record],artifact('request' if tool=='Read' else 'response',path,raw)


def trace(native,parent):
    initialized,sent,runtime=initial()
    return observed.Trace(prefix('transcript',initialized+native),prefix('control',sent+parent),
        session_id=SESSION,policy=POLICY,runtime=runtime)


@pytest.mark.parametrize('raw',[b'{}',b'{"long":"'+b'a'*100000+b'"}\n','{"text":"α\u2028β"}\n'.encode()])
def test_complete_read_uses_all_actual_raw_content(raw):
    native,parent,request=events(raw=raw);value=trace(native,parent)
    assert observed.complete_request_read(value,value.settled('tool-1'),request)


@pytest.mark.parametrize('change',['truncated','wrapped','wrong_lines','bool_lines','different_path','offset','bool_error',
    'error','background','foreign_session','child','wrong_role','duplicate_call','duplicate_result','duplicate_callback',
    'foreign_callback','callback_after_result','different_decision','contradictory_admission','pending','exit_bool','exit_conflict'])
def test_partial_or_contradictory_read_cannot_authorize_response(change):
    native,parent,request=events();result=native[-1];metadata=result['tool_use_result'];block=result['message']['content'][0]
    if change=='truncated':metadata['file']['content']='{}'
    elif change=='wrapped':block['content']='<persisted-output>partial</persisted-output>'
    elif change=='wrong_lines':metadata['file']['totalLines']+=1
    elif change=='bool_lines':metadata['file']['startLine']=True
    elif change=='different_path':metadata['file']['filePath']='/neutral/another'
    elif change=='offset':
        native[0]['message']['content'][0]['input']['offset']=1
        native[1]['request']['input']['tool_input']['offset']=1
        parent[0]['request']=deepcopy(native[1])
    elif change=='bool_error':block['is_error']=0
    elif change=='error':metadata['error']={'message':'failed'}
    elif change=='background':metadata['backgroundTaskId']='pending'
    elif change=='foreign_session':result['session_id']='foreign'
    elif change=='child':result['parent_tool_use_id']='parent'
    elif change=='wrong_role':result['message']['role']='assistant'
    elif change=='duplicate_call':native.insert(1,deepcopy(native[0]))
    elif change=='duplicate_result':native.append(deepcopy(result))
    elif change=='duplicate_callback':native.insert(2,deepcopy(native[1]))
    elif change=='foreign_callback':native[1]['request']['input']['tool_input']['file_path']='/foreign'
    elif change=='callback_after_result':native=[native[0],native[2],native[1]]
    elif change=='different_decision':parent[0]['request']['request']['input']['tool_input']['file_path']='/foreign'
    elif change=='contradictory_admission':parent[0]['response']['response']['response']={'permissionDecision':'deny'}
    elif change=='pending':native=native[:2]
    elif change=='exit_bool':metadata['exitCode']=False
    elif change=='exit_conflict':metadata.update(exitCode=0,exit_code=1)
    with pytest.raises(ValueError):
        value=trace(native,parent);observed.complete_request_read(value,value.settled('tool-1'),request)


def test_result_cannot_be_borrowed_from_future_prefetched_frame():
    native,parent,request=events();value=trace(native[:2],parent)
    with pytest.raises(ValueError,match='pending'):value.settled('tool-1')
    all_rows=prefix('transcript',initial()[0]+native)
    with pytest.raises(ValueError,match='beyond its observed prefix'):
        observed.event(value.transcript,observed.reference(all_rows,5,0))


@pytest.mark.parametrize('change',[None,'updated','content','intent','error','patch','modified','success_path'])
def test_response_is_only_exact_first_creation(change):
    native,parent,response=events('Write',b'{"answer":[]}');metadata=native[-1]['tool_use_result']
    intent=c.canonical(native[0]['message']['content'][0]['input'])
    if change=='updated':metadata['type']='update'
    elif change=='content':metadata['content']='another answer'
    elif change=='intent':intent=c.canonical({'file_path':response.pin.path,'content':'changed intent'})
    elif change=='error':native[-1]['message']['content'][0]['is_error']=True
    elif change=='patch':metadata['structuredPatch']=[{'oldLines':[]}]
    elif change=='modified':metadata['userModified']=True
    elif change=='success_path':native[-1]['message']['content'][0]['content']='File created successfully at: /foreign'
    value=trace(native,parent)
    if change is None:assert observed.first_response_write(value,value.settled('tool-1'),response,intent_input_json=intent)
    else:
        with pytest.raises(ValueError):observed.first_response_write(value,value.settled('tool-1'),response,intent_input_json=intent)


def test_current_helper_must_be_only_pending_and_admitted():
    native,parent,_=events();command='/neutral/python -m fixed'
    native[0]['message']['content'][0].update(name='Bash',input={'command':command})
    native[1]['request']['input'].update(tool_name='Bash',tool_input={'command':command})
    parent[0]['request']=deepcopy(native[1])
    value=trace(native[:2],parent)
    assert value.current_advance('tool-1',command).tool_name=='Bash'
    other=deepcopy(native[0]);other['message']['content'][0]['id']='pending-2'
    with pytest.raises(ValueError,match='sole pending'):trace(native[:2]+[other],parent).current_advance('tool-1',command)
    with pytest.raises(ValueError,match='admission'):trace(native[:2],[]).current_advance('tool-1',command)


def initial():
    policy=deepcopy(POLICY);contract=policy['pretool_control'];runtime={'model':'fixture-model',
        'executable':{'init_version':'fixture-version'},'auth':{'expected_api_key_source':'none'}}
    sent={'kind':'initialize_sent','policy_sha256':c.sha(json.dumps(policy,sort_keys=True,separators=(',',':')).encode()),
        'frame':{'type':'control_request','request_id':'d4d_initialize_v1','request':{'subtype':'initialize',
            'hooks':{'PreToolUse':[{'matcher':contract['matcher'],'hookCallbackIds':[contract['callback_id']],'timeout':125}]}}}}
    ack={'type':'control_response','response':{'subtype':'success','request_id':'d4d_initialize_v1'}}
    init={'type':'system','subtype':'init','session_id':SESSION,'cwd':'/neutral','model':'fixture-model',
        'claude_code_version':'fixture-version','apiKeySource':'none','tools':['Read','Write','Bash']}
    return [ack,init],[sent,{'kind':'initialize_ack','frame':deepcopy(ack)}],runtime


@pytest.mark.parametrize('change',[None,'duplicate','policy','late_ack','session','model','version','source','error','tools'])
def test_actual_init_binding_is_not_a_declared_session(change):
    native,parent,runtime=initial()
    if change=='duplicate':native.append(deepcopy(native[0]))
    elif change=='policy':parent[0]['policy_sha256']='f'*64
    elif change=='late_ack':native.reverse()
    elif change=='session':native[1]['session_id']=None
    elif change=='model':native[1]['model']='other'
    elif change=='version':native[1]['claude_code_version']='other'
    elif change=='source':native[1]['apiKeySource']='ANTHROPIC_API_KEY'
    elif change=='error':native[0]['response']['error']='refused';parent[1]['frame']=deepcopy(native[0])
    elif change=='tools':native[1]['tools'].append('Read')
    args=(prefix('transcript',native),prefix('control',parent))
    if change is None:assert observed.initialization(*args,policy=POLICY,runtime=runtime)[0]==SESSION
    else:
        with pytest.raises(ValueError):observed.initialization(*args,policy=POLICY,runtime=runtime)


@pytest.mark.parametrize('change',['missing_init','foreign_declared_session','contradictory_model','child_callback'])
def test_tool_observation_requires_the_real_parent_runtime_before_join(change):
    native,parent,_=events();initialized,sent,runtime=initial();session=SESSION
    if change=='missing_init':initialized=[]
    elif change=='foreign_declared_session':session='foreign'
    elif change=='contradictory_model':native[0]['message']['model']='foreign'
    elif change=='child_callback':native[1]['parent_tool_use_id']='parent'
    with pytest.raises(ValueError):
        observed.Trace(prefix('transcript',initialized+native),prefix('control',sent+parent),
            session_id=session,policy=POLICY,runtime=runtime)
