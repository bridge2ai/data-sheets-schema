"""Exercise the parent control channel with real local child processes."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shlex
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from budgeted_cborg import BudgetStop
import native_control as control
import run_native_canary as runner


CHILD = r'''
import json, os, subprocess, sys, time
from pathlib import Path
case=json.loads(Path('case.json').read_text())
def send(value):print(json.dumps(value),flush=True)
init=json.loads(sys.stdin.readline())
if case.get('no_init'):
    time.sleep(20);sys.exit(0)
if case.get('early_result'):
    send({'type':'result'})
send({'type':'control_response','response':{'subtype':'success','request_id':init['request_id'],'response':{}}})
prompt=json.loads(sys.stdin.readline())
assert prompt['message']['content']=='synthetic input'
command=case['command'];identity='synthetic_tool'
tool=case.get('tool','Bash');payload=case.get('input',{'command':command})
send({'type':'assistant','message':{'content':[{'type':'tool_use','id':identity,'name':tool,'input':payload}]}})
if not case.get('skip_callback'):
    request={'type':'control_request','request_id':'synthetic_request','request':{
        'subtype':'hook_callback','callback_id':'d4d_tool_policy_v2',
        'input':{'hook_event_name':'PreToolUse','tool_name':tool,'tool_use_id':identity,
                 'cwd':os.getcwd(),'tool_input':payload.copy()}}}
    mutation=case.get('mutation')
    if mutation=='callback':request['request']['callback_id']='unregistered'
    if mutation=='command':request['request']['input']['tool_input']['command']='different command'
    if mutation=='file':request['request']['input']['tool_input']['file_path']='different-path'
    if mutation=='content':request['request']['input']['tool_input']['content']='different-content'
    if mutation=='identity':request['request']['input']['tool_use_id']='unknown_tool'
    if mutation=='event':request['request']['input']['hook_event_name']='PostToolUse'
    if mutation=='cwd':request['request']['input']['cwd']='/another/worktree'
    send(request)
    if mutation=='duplicate':send(request)
    reply=json.loads(sys.stdin.readline())
    denied=reply['response']['response'].get('hookSpecificOutput',{}).get('permissionDecision')=='deny'
else:denied=False
if not denied:
    if tool=='Bash':
        result=subprocess.run(command,shell=True,capture_output=True,text=True)
        error=result.returncode!=0;content=result.stdout+result.stderr
    elif tool=='Read':error=False;content=Path(payload['file_path']).read_text()
    else:
        Path(payload['file_path']).write_text(payload['content'])
        error=False;content='written'
else:error=True;content='Denied by the synthetic control host'
send({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':identity,'is_error':error,'content':content}]}})
send({'type':'result','permission_denials':[{'tool_use_id':identity,'tool_name':tool,'tool_input':payload}] if denied else []})
'''


@pytest.fixture
def run_case(tmp_path):
    source=tmp_path/'registered source.txt';source.write_text('REGISTERED_MARKER\n')
    policy={'python':sys.executable,'programs':[],'manifest_paths':[],
            'readonly_lookups':{'repository':str(tmp_path),'inputs':[str(source)],'output_directories':[]},
            'pretool_control':deepcopy(control.CONTRACT)}
    (tmp_path/'out').mkdir()
    policy['readonly_lookups']['output_directories']=[str(tmp_path/'out')]
    instruction=tmp_path/'instruction';instruction.write_text('synthetic input')
    closed=[];stops=[]
    proxy=SimpleNamespace(failed=threading.Event(),failure=None,close_admission=lambda:closed.append(True))
    def run(case=None, timeout=4):
        value={'command':shlex.join(['cat',str(source)]),**(case or {})}
        (tmp_path/'case.json').write_text(json.dumps(value))
        policy['pretool_control']=deepcopy(control.CONTRACT)
        result=runner.execute_child([sys.executable,'-c',CHILD,'--input-format','stream-json'],
            proxy=proxy,instruction=instruction,attempt=tmp_path,cwd=tmp_path,env={},
            deadline_seconds=timeout,verify_launch=lambda:None,command_policy=policy,
            record_stop=stops.append)
        events=[json.loads(line) for line in (tmp_path/'transcript.jsonl').read_text().splitlines()]
        return result,events,control.check_control_history(events,tmp_path/'control.jsonl',policy,runner._classify_command)
    return run,tmp_path,source,policy,closed,stops


def test_prescribed_read_executes_and_has_complete_parent_evidence(run_case):
    run,path,source,policy,closed,stops=run_case
    code,events,checked=run()
    assert code==0 and closed and not stops
    assert checked=={'checked':True,'bash_calls':1,'file_calls':0,'decisions':1,'persisted_output_paths':[],'problems':[]}
    assert 'REGISTERED_MARKER' in (path/'transcript.jsonl').read_text()
    assert not runner.command_history(events,policy,[])['problems']


def test_compound_command_is_denied_before_its_marker_can_be_written(run_case):
    run,path,source,policy,closed,stops=run_case
    marker=path/'must-not-exist'
    command=shlex.join(['cat',str(source)])+'; '+shlex.join(['touch',str(marker)])
    code,events,checked=run({'command':command})
    assert code==0 and closed and not stops and checked['problems']==[]
    assert not marker.exists()
    terminal=next(e for e in events if e.get('type')=='result')
    assert len(terminal['permission_denials'])==1
    assert not runner.command_history(events,policy,terminal['permission_denials'])['problems']


def test_blank_command_remains_a_nondisqualifying_denial(run_case):
    run,path,source,policy,closed,stops=run_case
    code,events,checked=run({'command':'  '})
    assert code==0 and not stops and checked['problems']==[]
    terminal=next(e for e in events if e.get('type')=='result')
    judgments=runner.classify_denials(terminal['permission_denials'],instruction_text='',
        python=sys.executable,repository=str(path),output_directories=[],readable_inputs=[],command_policy=policy)
    assert len(judgments)==1 and not runner.denial_problems(judgments)


def test_shutdown_preserves_unconsumed_native_pipe_bytes(tmp_path):
    read_fd,write_fd=os.pipe()
    stream=os.fdopen(read_fd,'rb');os.set_blocking(read_fd,False)
    channel=control.NativeControl({'pretool_control':deepcopy(control.CONTRACT)},lambda *args:None)
    channel.process=SimpleNamespace(stdin=None,stdout=stream)
    path=tmp_path/'transcript.jsonl';path.write_bytes(b'earlier event\n')
    try:
        os.write(write_fd,b'last native event\n');os.close(write_fd)
        channel.retain_pipe_tail(path)
        assert path.read_bytes()==b'earlier event\nlast native event\n'
    finally:
        channel.close()


@pytest.mark.parametrize('mutation',['callback','command','identity','event','cwd','duplicate'])
def test_malformed_callback_stops_without_executing_the_command(run_case,mutation):
    run,path,source,policy,closed,stops=run_case
    marker=path/'must-not-exist'
    with pytest.raises(BudgetStop,match='callback'):
        run({'command':shlex.join(['touch',str(marker)]),'mutation':mutation})
    assert closed and stops and not marker.exists()


def test_missing_initialization_times_out_before_sending_a_prompt(run_case,monkeypatch):
    run,path,source,policy,closed,stops=run_case
    monkeypatch.setitem(control.CONTRACT,'initialize_timeout_seconds',.1)
    start=time.monotonic()
    with pytest.raises(BudgetStop,match='initialization timed out'):
        run({'no_init':True})
    assert time.monotonic()-start<2 and closed and stops
    records=[json.loads(line) for line in (path/'control.jsonl').read_text().splitlines()]
    assert [r['kind'] for r in records]==['initialize_sent']


def test_terminal_before_initialization_stops_without_sending_a_prompt(run_case):
    run,path,source,policy,closed,stops=run_case
    with pytest.raises(BudgetStop,match='result arrived'):
        run({'early_result':True})
    assert closed and stops
    records=[json.loads(line) for line in (path/'control.jsonl').read_text().splitlines()]
    assert [r['kind'] for r in records]==['initialize_sent']


@pytest.mark.parametrize('failure',['timeout','exception','malformed'])
def test_classifier_failure_never_sends_a_permissive_response(run_case,monkeypatch,failure):
    run,path,source,policy,closed,stops=run_case
    def broken(*args):
        if failure=='timeout':time.sleep(2);return ('prescribed','late')
        if failure=='exception':raise ValueError('synthetic classifier error')
        return ('prescribed',None)
    monkeypatch.setattr(runner,'_classify_command',broken)
    monkeypatch.setitem(control.CONTRACT,'callback_timeout_seconds',.1)
    start=time.monotonic()
    with pytest.raises(BudgetStop,match='classification'):
        run()
    assert time.monotonic()-start<2 and closed and stops
    records=[json.loads(line) for line in (path/'control.jsonl').read_text().splitlines()]
    assert not any(r['kind']=='decision' for r in records)


def test_a_runtime_that_omits_callbacks_cannot_complete(run_case):
    run,path,source,policy,closed,stops=run_case
    with pytest.raises(BudgetStop,match='without complete evidence'):
        run({'skip_callback':True})
    assert closed and stops


@pytest.mark.parametrize('change',['missing','duplicate','response','command','policy','order','orphan_result'])
def test_terminal_audit_rejects_incomplete_or_contradictory_evidence(run_case,change):
    run,path,source,policy,closed,stops=run_case
    _,events,_=run()
    evidence=path/'control.jsonl'
    rows=[json.loads(line) for line in evidence.read_text().splitlines()]
    decision=next(r for r in rows if r['kind']=='decision')
    if change=='missing':rows.remove(decision)
    elif change=='duplicate':rows.append(decision)
    elif change=='response':decision['response']['response']['response']={'hookSpecificOutput':{'permissionDecision':'allow'}}
    elif change=='command':decision['request']['request']['input']['tool_input']['command']='changed command'
    elif change=='policy':rows[0]['policy_sha256']='changed'
    elif change=='order':
        callback=next(e for e in events if e.get('type')=='control_request')
        events.remove(callback);events.insert(0,callback)
    elif change=='orphan_result':
        events.append({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'no-call','content':'unattested'}]}})
    evidence.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    assert control.check_control_history(events,evidence,policy,runner._classify_command)['problems']


def test_missing_control_evidence_is_a_failed_check(tmp_path):
    checked=control.check_control_history([],tmp_path/'missing.jsonl',{},runner._classify_command)
    assert checked['checked'] is False and checked['problems']


@pytest.mark.parametrize('relative',[False,True])
def test_registered_file_read_reaches_the_tool_and_is_reconciled(run_case,relative):
    run,path,source,policy,closed,stops=run_case
    target=source.name if relative else str(source)
    code,events,checked=run({'tool':'Read','input':{'file_path':target}})
    assert code==0 and not stops and checked['file_calls']==1 and not checked['problems']
    assert 'REGISTERED_MARKER' in (path/'transcript.jsonl').read_text()


@pytest.mark.parametrize('tool',['Read','Write'])
def test_unregistered_file_operation_is_denied_before_access(run_case,tool):
    run,path,source,policy,closed,stops=run_case
    target=path/'unregistered-agent.md';target.write_text('UNREGISTERED_PRIVATE_MARKER')
    payload={'file_path':str(target)}
    if tool=='Write':payload['content']='changed'
    code,events,checked=run({'tool':tool,'input':payload})
    assert code==0 and not stops and checked['problems']==[] and checked['file_calls']==1
    assert target.read_text()=='UNREGISTERED_PRIVATE_MARKER'
    assert 'UNREGISTERED_PRIVATE_MARKER' not in (path/'transcript.jsonl').read_text()
    terminal=next(e for e in events if e.get('type')=='result')
    assert len(terminal['permission_denials'])==1


def test_write_cannot_replace_a_registered_input(run_case):
    run,path,source,policy,closed,stops=run_case
    code,events,checked=run({'tool':'Write','input':{'file_path':str(source),'content':'changed'}})
    assert code==0 and not checked['problems'] and source.read_text()=='REGISTERED_MARKER\n'
    assert next(e for e in events if e.get('type')=='result')['permission_denials']


def test_own_artifact_write_is_allowed_and_observed(run_case):
    run,path,source,policy,closed,stops=run_case
    target=path/'out/receipt.yaml'
    code,events,checked=run({'tool':'Write','input':{'file_path':'out/receipt.yaml','content':'receipt'}})
    assert code==0 and not checked['problems'] and target.read_text()=='receipt'
    assert checked['file_calls']==1 and checked['decisions']==1


@pytest.mark.parametrize('tool',['Read','Write'])
def test_symlink_cannot_escape_the_output_directory(run_case,tool):
    run,path,source,policy,closed,stops=run_case
    outside=path/'unregistered-agent.md';outside.write_text('PRIVATE_LINK_MARKER')
    target=path/'out/linked.md';target.symlink_to(outside)
    payload={'file_path':str(target)}
    if tool=='Write':payload['content']='changed'
    code,events,checked=run({'tool':tool,'input':payload})
    assert code==0 and not checked['problems'] and outside.read_text()=='PRIVATE_LINK_MARKER'
    assert 'PRIVATE_LINK_MARKER' not in (path/'transcript.jsonl').read_text()
    assert next(e for e in events if e.get('type')=='result')['permission_denials']


@pytest.mark.parametrize('mutation',['file','content'])
def test_file_callback_cannot_substitute_path_or_content(run_case,mutation):
    run,path,source,policy,closed,stops=run_case
    target=path/'out/new.txt'
    with pytest.raises(BudgetStop,match='callback'):
        run({'tool':'Write','input':{'file_path':str(target),'content':'original'},'mutation':mutation})
    assert not target.exists() and closed and stops


def test_file_path_matching_cannot_block_the_parent_deadline(run_case,monkeypatch):
    from native_file_policy import FileAccess
    run,path,source,policy,closed,stops=run_case
    original=FileAccess.matches
    def slow_match(*args):
        time.sleep(.5)
        return original(*args)
    monkeypatch.setattr(FileAccess,'matches',slow_match)
    monkeypatch.setitem(control.CONTRACT,'callback_timeout_seconds',.1)
    target=path/'out/must-not-exist'
    started=time.monotonic()
    with pytest.raises(BudgetStop,match='classification timed out'):
        run({'tool':'Write','input':{'file_path':str(target),'content':'must not execute'}})
    assert time.monotonic()-started < .5
    assert closed and stops and not target.exists()


@pytest.mark.parametrize('change,reason', [
    ('size', 'native persisted tool output has invalid provenance'),
    ('hard_link', 'native persisted output is not a single-link regular file'),
])
def test_terminal_audit_preserves_local_file_policy_reason(run_case, change, reason):
    """A valid persisted result becomes invalid, and the audit names why."""
    import hashlib
    import re

    run, path, source, policy, closed, stops = run_case
    _, events, checked = run()
    assert checked['checked'] and not checked['problems']
    session = '12345678-1234-1234-1234-123456789abc'
    config = path / 'config'
    persisted = config / 'projects' / re.sub(r'[^a-zA-Z0-9]', '-', str(path)) / session / 'tool-results/result.txt'
    persisted.parent.mkdir(parents=True)
    persisted.write_text('persisted helper output')
    events.insert(0, {'type': 'system', 'subtype': 'init', 'cwd': str(path), 'session_id': session})
    result = next(e for e in events if e.get('type') == 'user')
    result['session_id'] = session
    result['tool_use_result'] = {'persistedOutputPath': str(persisted), 'persistedOutputSize': persisted.stat().st_size}
    result['message']['content'][0]['content'] = f'<persisted-output>\nFull output saved to: {persisted}\n'
    evidence = {'kind': 'persisted_output', 'tool_use_id': 'synthetic_tool', 'path': str(persisted),
                'file': {'bytes': persisted.stat().st_size, 'sha256': hashlib.sha256(persisted.read_bytes()).hexdigest()}}
    with (path / 'control.jsonl').open('a') as stream:
        stream.write(json.dumps(evidence) + '\n')
    before = control.check_control_history(events, path / 'control.jsonl', policy, runner._classify_command, config)
    assert before['checked'] and not before['problems']
    if change == 'size':
        persisted.write_text('different output with a different size')
    else:
        persisted.unlink()
        os.link(source, persisted)
    after = control.check_control_history(events, path / 'control.jsonl', policy, runner._classify_command, config)
    assert not after['checked']
    assert any(reason in problem for problem in after['problems'])
