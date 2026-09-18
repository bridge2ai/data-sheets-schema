"""Offline native children, real evidence checks and local HTTP accounting.

These synthetic one-field records test control behavior, not scientific
acceptance, schema completeness, or provider/native-model performance.
"""
import copy
from contextlib import contextmanager, nullcontext
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import threading
from types import SimpleNamespace

import httpx
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE/'native_controls'))
from audit_controls import native, contract
from budgeted_cborg import BudgetStop, Ledger
from native_control import load_native_events
from run_native_canary import execute_child
from data_sheets_schema import source_review
from tests.test_audit_record_contract import rendered_example, fixture_files

PRICES = {'input':0.000005, 'output':0.000025, 'cache_read':0.0000005, 'cache_write':0.00000625}
ROOT = BASE.parents[1]
CHILD = r'''
import json, os, shlex, subprocess, sys, threading, time, urllib.request, urllib.error
from pathlib import Path
case=json.loads(Path(sys.argv[1]).read_text())
def send(value):print(json.dumps(value),flush=True)
init=json.loads(sys.stdin.readline())
send({'type':'control_response','response':{'subtype':'success','request_id':init['request_id'],'response':{}}})
prompt=json.loads(sys.stdin.readline())
session='11111111-2222-3333-4444-555555555555'
send({'type':'system','subtype':'init','session_id':session,'cwd':os.getcwd(),
      'model':'claude-opus-5','apiKeySource':'ANTHROPIC_API_KEY','claude_code_version':'2.1.272','tools':['Read','Write','Bash']})
def request():
    body={'model':'claude-opus-5','max_tokens':1000,'stream':True,'system':case['system_prompt'],
          'messages':[{'role':'user','content':prompt['message']['content']}]}
    req=urllib.request.Request(os.environ['ANTHROPIC_BASE_URL']+'/v1/messages',data=json.dumps(body).encode(),
        headers={'x-api-key':os.environ['ANTHROPIC_API_KEY'],'Content-Type':'application/json'})
    try:
        timeout=float(os.environ.get('API_TIMEOUT_MS',case.get('default_timeout_ms',5000)))/1000
        with urllib.request.urlopen(req,timeout=timeout) as response:return response.status, response.read().decode()
    except urllib.error.HTTPError as error:return error.code,error.read().decode()
request()
denials=[]
for index, call in enumerate(case['calls']):
    identity='audit-call-'+str(index);tool=call['name'];payload=call['input']
    send({'type':'assistant','session_id':session,'message':{'role':'assistant','content':[{
        'type':'tool_use','id':identity,'name':tool,'input':payload}]}})
    send({'type':'control_request','request_id':'callback-'+str(index),'request':{
        'subtype':'hook_callback','callback_id':'d4d_tool_policy_v2','input':{
            'hook_event_name':'PreToolUse','tool_name':tool,'tool_use_id':identity,
            'cwd':os.getcwd(),'tool_input':payload}}})
    reply=json.loads(sys.stdin.readline())
    denied=reply['response']['response'].get('hookSpecificOutput',{}).get('permissionDecision')=='deny'
    metadata={}
    if denied:
        error=True;content='Denied by synthetic native host'
        denials.append({'tool_use_id':identity,'tool_name':tool,'tool_input':payload})
    elif tool=='Write':
        Path(payload['file_path']).write_text(payload['content']);error=False;content='Written'
        metadata={'type':'create','filePath':payload['file_path'],'content':payload['content']}
    elif tool=='Read':
        content=Path(payload['file_path']).read_text();error=False
    else:
        completed=subprocess.run(shlex.split(payload['command']),capture_output=True,text=True)
        error=completed.returncode!=0;content=completed.stdout+completed.stderr
        metadata={'stdout':completed.stdout,'stderr':completed.stderr,'interrupted':False,'exitCode':completed.returncode}
        if case.get('request_before_validator_result'):
            status,_=request()
            Path(case['request_status']).write_text(str(status))
    result={'type':'tool_result','tool_use_id':identity,'content':content}
    if tool!='Write' or error:result['is_error']=error
    if case.get('missing_metadata')==tool:metadata={}
    if case.get('missing_error_flag')==tool:result.pop('is_error',None)
    race=None
    if tool=='Bash' and case.get('request_race_before_validator_result'):
        race=threading.Thread(target=request);race.start();time.sleep(0.1)
    send({'type':'user','session_id':session,'tool_use_result':metadata,'message':{'role':'user','content':[result]}})
    if race:race.join()
if case.get('final_request',True):request()
send({'type':'result','is_error':False,'terminal_reason':'completed','stop_reason':'end_turn',
      'permission_denials':denials,'modelUsage':{'claude-opus-5':{'contextWindow':200000,'maxOutputTokens':64000}}})
'''

# This helper runs the real pure contract on synthetic inputs; production
# registration/CLI pin validation is covered separately by test_contract and
# test_registration. Its exact command is the only command this child may run.
HELPER = r'''
import json,sys
from pathlib import Path
from audit_controls.contract import validate_audit
manifest=json.loads(Path(sys.argv[1]).read_text())
report=validate_audit(manifest)
report['registration_sha256']='synthetic-registration'
attempt=Path(manifest['job']['attempt_dir'])
with (attempt/'validation.json').open('x') as out:json.dump(report,out)
if not report['passed']:
    with (attempt/'validation_failure.json').open('x') as out:json.dump(report,out)
print(json.dumps(report))
raise SystemExit(int(not report['passed']))
'''


def response_events():
    values=[{'type':'message_start','message':{'id':'offline','model':'claude-opus-5','role':'assistant',
        'type':'message','content':[],'usage':{'input_tokens':100,'output_tokens':0},'stop_reason':None}},
        {'type':'content_block_start','index':0,'content_block':{'type':'text','text':''}},
        {'type':'content_block_delta','index':0,'delta':{'type':'text_delta','text':'offline response'}},
        {'type':'content_block_stop','index':0},
        {'type':'message_delta','delta':{'stop_reason':'end_turn'},'usage':{'output_tokens':12}},
        {'type':'message_stop'}]
    return ''.join(f"event: {v['type']}\ndata: {json.dumps(v)}\n\n" for v in values).encode()


@pytest.fixture
def native_case(tmp_path):
    _, raw, audit = rendered_example(tmp_path, 'Claude Code')
    files,_ = fixture_files(tmp_path,raw,audit)
    core=tmp_path/'original_core.yaml';core.write_text(raw)
    inventory=tmp_path/'source_inventory.json';inventory.write_text(json.dumps(source_review.inventory(raw,'original_full')))
    inputs={'original_full':files['artifacts']['original_full'],'original_core':core,
            'bundle':files['bundle'],'chunk_manifest':files['manifest'],'source_inventory':inventory}
    for role in contract.INPUTS-set(inputs):
        path=tmp_path/(role+'.txt');path.write_text('Synthetic reference only.\n');inputs[role]=path
    instruction=tmp_path/'instruction.txt';instruction.write_text('Complete synthetic exact inline task.\n'+raw)
    system=tmp_path/'system.txt';system.write_text('Synthetic audit-only system.\n')
    attempt=tmp_path/'attempt';attempt.mkdir();output=attempt/'output';output.mkdir()
    job={'id':'synthetic_audit','attempt_dir':str(attempt),'output_dir':str(output),'audit_path':str(output/'audit.json'),
        'instruction':str(instruction),'system_prompt':str(system),'readable_inputs':[str(p) for p in inputs.values()]}
    manifest={'job':job,'repository':str(tmp_path),'python':sys.executable,'inputs':{k:str(p) for k,p in inputs.items()},
        'protocol_version':3,'render_version':14,'model':{'model':'claude-opus-5'},
        'native_runtime':{'version':'2.1.272 (Claude Code)','context_window':200000,'max_output_tokens':64000},
        'pinned_files':{str(p):native.sha(p) for p in [*inputs.values(),instruction,system]}}
    registration=tmp_path/'registration.json'
    job['validator_argv']=[sys.executable,'-m','audit_controls.contract','--registration',str(registration)]
    policy=native.build_policy(manifest,registration)
    helper=tmp_path/'synthetic_validator.py';helper.write_text(HELPER)
    command=[sys.executable,str(helper),str(registration)]
    policy['validator_argv']=command
    policy['allowed_tools']=['Read','Write',native._literal_rule(shlex.join(command))]
    registration.write_text(json.dumps(manifest))
    case={'calls':[{'name':'Write','input':{'file_path':job['audit_path'],'content':json.dumps(audit)}},
                   {'name':'Bash','input':{'command':shlex.join(command)}}],
          'system_prompt':system.read_text(),'request_status':str(tmp_path/'request_status.txt')}
    history=native.AuditHistory(manifest,'synthetic-registration',policy)
    ledger=Ledger(tmp_path/'ledger.json',manifest_sha256='synthetic-registration',total_cap=400,attempt_cap=20)
    sdk=SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **kw:SimpleNamespace(input_tokens=100)))
    calls=[]
    def respond(request):
        calls.append(request)
        return httpx.Response(200,content=response_events(),headers={'content-type':'text/event-stream'})
    proxy=native.AuditProxy(audit_history=history,sdk=sdk,ledger=ledger,attempt='offline-audit',evidence=attempt/'requests',
        model='claude-opus-5',prices=PRICES,verify=history.verify_admission,provider_key='offline-key',
        base_url='https://api.cborg.lbl.gov',upstream=httpx.Client(transport=httpx.MockTransport(respond)))
    def run(*, phase_spec=None):
        case_path=tmp_path/'case.json';case_path.write_text(json.dumps(case))
        env={**os.environ,'PYTHONPATH':os.pathsep.join([str(ROOT/'src'),str(BASE),str(BASE/'native_controls')]),
             'ANTHROPIC_API_KEY':proxy.token}
        with proxy.running() as url:
            env['ANTHROPIC_BASE_URL']=url
            status=execute_child([sys.executable,'-c',CHILD,str(case_path),'--input-format','stream-json'],proxy=proxy,
                instruction=instruction,attempt=attempt,cwd=tmp_path,env=env,deadline_seconds=20,verify_launch=history.verify_admission,
                command_policy=policy,command_classifier=native.classify_command,event_observer=history.observe,phase_spec=phase_spec,
                record_stop=lambda reason:ledger.stop_attempt('offline-audit',reason))
        assert status==0
        return native.inspect_transcript(load_native_events(attempt/'transcript.jsonl'),policy,manifest,
            'synthetic-registration',attempt/'control.jsonl',None)
    return SimpleNamespace(manifest=manifest,job=job,policy=policy,audit=audit,case=case,history=history,
        ledger=ledger,proxy=proxy,calls=calls,run=run,attempt=attempt,registration=registration)


def test_real_child_exact_write_real_evidence_validator_terminal_and_accounting(native_case):
    c=native_case; before={p:Path(p).read_bytes() for p in c.manifest['inputs'].values()}
    evidence=c.run()
    assert evidence['phase3']['validation']['passed']
    assert evidence['phase1_phase2_performed_here'] is False
    assert evidence['control']['decisions']==2
    assert before=={p:Path(p).read_bytes() for p in before}
    rows=json.loads(c.ledger.path.read_text())['requests']
    assert len(rows)==2 and all(r['status']=='settled' for r in rows)
    assert sum(Decimal(r['cost_usd']) for r in rows)==Decimal('0.0016')
    context=SimpleNamespace(attempt=c.attempt,job=c.job)
    assert native.verify_initial_context(context,rows)['complete_inline_context_observed']


@pytest.mark.parametrize('change',['wrong_record','false_quote','missing_source_review'])
def test_real_evidence_failure_stops_without_a_repair_or_new_provider_request(native_case,change):
    c=native_case
    if change=='wrong_record':c.audit['findings'][0]['record']='original_full'
    elif change=='false_quote':c.audit['findings'][0]['evidence'][0]['quote']='invented absent source'
    else:c.audit.pop('source_review')
    c.case['calls'][0]['input']['content']=json.dumps(c.audit)
    c.case['request_before_validator_result']=True
    with pytest.raises(BudgetStop):c.run()
    assert len(c.calls)==1
    rows=json.loads(c.ledger.path.read_text())['requests']
    assert len(rows)==1 and rows[0]['status']=='settled'
    assert (c.attempt/'validation_failure.json').exists()
    assert json.loads((c.attempt/'validation.json').read_text())['passed'] is False
    assert Path(c.job['audit_path']).read_text()==c.case['calls'][0]['input']['content']


@pytest.mark.parametrize('change',['rewrite','duplicate_validator','read_after_validator'])
def test_tools_after_validator_are_stopped_before_callback_execution(native_case,change):
    c=native_case
    if change=='rewrite':extra={'name':'Write','input':{'file_path':c.job['audit_path'],'content':'tampered'}}
    elif change=='duplicate_validator':extra=copy.deepcopy(c.case['calls'][1])
    else:extra={'name':'Read','input':{'file_path':c.job['readable_inputs'][0]}}
    c.case['calls'].append(extra)
    with pytest.raises(BudgetStop):c.run()
    assert Path(c.job['audit_path']).read_text()==c.case['calls'][0]['input']['content']
    assert not (c.attempt/'validation_failure.json').exists()
    assert len(c.calls)==1
    control=[json.loads(line) for line in (c.attempt/'control.jsonl').read_text().splitlines()]
    assert not any(r.get('kind')=='decision' and r.get('tool_use_id')=='audit-call-2' for r in control)


@pytest.mark.parametrize('tool,flag',[('Write','missing_metadata'),('Bash','missing_metadata'),('Bash','missing_error_flag')])
def test_missing_typed_result_cannot_authorize_terminal_acceptance(native_case,tool,flag):
    c=native_case;c.case[flag]=tool
    with pytest.raises(BudgetStop):c.run()


@pytest.mark.parametrize('change',['validate_first','missing_validator','different_output','original_write'])
def test_no_new_generation_or_unchecked_audit_can_complete(native_case,change):
    c=native_case
    if change=='validate_first':c.case['calls'].reverse()
    elif change=='missing_validator':c.case['calls'].pop()
    elif change=='different_output':c.case['calls'][0]['input']['file_path']=str(c.attempt/'output'/'full.yaml')
    else:c.case['calls'][0]['input']['file_path']=c.manifest['inputs']['original_full']
    before=Path(c.manifest['inputs']['original_full']).read_bytes()
    with pytest.raises(BudgetStop):c.run()
    assert Path(c.manifest['inputs']['original_full']).read_bytes()==before
    assert not (c.attempt/'output'/'full.yaml').exists()


@pytest.mark.parametrize('command',['extra_argument','compound'])
def test_bash_authority_does_not_expand_past_exact_validator(native_case,command):
    c=native_case
    extra=c.case['calls'][1]['input']['command']+(' --help' if command=='extra_argument' else '; touch out')
    c.case['calls'].insert(1,{'name':'Bash','input':{'command':extra}})
    evidence=c.run()
    assert evidence['denials'][0]['classification']=='not_prescribed'
    assert not (Path(c.manifest['repository'])/'out').exists()


def test_context_is_checked_in_retained_initial_request(native_case):
    c=native_case;c.run();rows=json.loads(c.ledger.path.read_text())['requests']
    path=c.attempt/'requests'/rows[0]['id']/'native_request.json'
    value=json.loads(path.read_text());value['messages'][0]['content']='truncated context';path.write_text(json.dumps(value))
    with pytest.raises(BudgetStop,match='omitted'):native.verify_initial_context(SimpleNamespace(attempt=c.attempt,job=c.job),rows)


def test_changed_audit_or_receipt_after_validator_cannot_be_accepted(native_case):
    c=native_case;c.run()
    Path(c.job['audit_path']).write_text('{}')
    with pytest.raises(BudgetStop,match='identity changed'):c.history.verify_admission()
    with pytest.raises(BudgetStop):
        native.inspect_transcript(load_native_events(c.attempt/'transcript.jsonl'),c.policy,c.manifest,
            'synthetic-registration',c.attempt/'control.jsonl',None)


def test_failure_marker_created_during_counting_prevents_model_admission(native_case):
    c=native_case
    def count(**kwargs):
        (c.attempt/'validation_failure.json').write_text('{"passed": false}')
        return SimpleNamespace(input_tokens=100)
    c.proxy.messages.client.messages.count_tokens=count
    request={'model':'claude-opus-5','max_tokens':1000,'stream':True,'messages':[{'role':'user','content':'Synthetic'}]}
    with c.proxy.running() as url:
        response=httpx.post(url+'/v1/messages',json=request,headers={'x-api-key':c.proxy.token})
    assert response.status_code==402 and not c.calls
    assert json.loads(c.ledger.path.read_text())['requests']==[]


def test_interrupted_upstream_preserves_pending_reservation_and_blocks_retry(native_case):
    c=native_case
    class Incomplete(httpx.SyncByteStream):
        def __iter__(self):
            yield response_events().split(b'event: message_stop')[0]
            raise httpx.RemoteProtocolError('synthetic disconnect')
    c.proxy.upstream=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,stream=Incomplete(),headers={'content-type':'text/event-stream'})))
    request={'model':'claude-opus-5','max_tokens':1000,'stream':True,'messages':[{'role':'user','content':'Synthetic'}]}
    with c.proxy.running() as url:
        httpx.post(url+'/v1/messages',json=request,headers={'x-api-key':c.proxy.token})
        assert httpx.post(url+'/v1/messages',json=request,headers={'x-api-key':c.proxy.token}).status_code==402
    rows=json.loads(c.ledger.path.read_text())['requests']
    assert len(rows)==1 and rows[0]['status']=='pending' and Decimal(rows[0]['reserved_usd'])>0
    assert 'cost_usd' not in rows[0]


def test_build_policy_requires_production_exact_module_argv_and_pinned_reads(native_case):
    c=native_case
    assert native.build_policy(c.manifest,c.registration)['validator_argv']==c.job['validator_argv']
    c.job['validator_argv'].append('--help')
    with pytest.raises(BudgetStop,match='argv'):native.build_policy(c.manifest,c.registration)
    c.job['validator_argv'].pop()
    Path(c.job['readable_inputs'][0]).write_text('changed')
    with pytest.raises(BudgetStop,match='read changed'):native.build_policy(c.manifest,c.registration)


@pytest.mark.parametrize('option', ['run_in_background', 'dangerouslyDisableSandbox'])
def test_selected_validator_extra_execution_options_are_refused_before_start(native_case, option):
    c=native_case;c.case['calls'][1]['input'][option]=True
    with pytest.raises(BudgetStop,match='foreground'):c.run()
    assert not (c.attempt/'validation.json').exists()


def test_added_event_observer_composes_with_existing_generation_observer(native_case, monkeypatch):
    c=native_case
    import run_native_canary
    seen=[]
    class ExistingPhaseObserver:
        def __init__(self,*args,**kwargs):pass
        def observe(self,event):seen.append(event)
        def report(self,complete=False):return {'problems':[]}
    monkeypatch.setattr(run_native_canary,'PhaseHistory',ExistingPhaseObserver)
    assert c.run(phase_spec=SimpleNamespace(render_version=13))['phase3']['validation']['passed']
    assert any(e.get('type')=='result' for e in seen)
    assert c.history.validator and c.history.validation


def configure_execution(c, monkeypatch):
    case_path=Path(c.manifest['repository'])/'orchestration_case.json'
    case_path.write_text(json.dumps(c.case))
    executable=Path(c.manifest['repository'])/'offline-native'
    executable.write_text('#!'+sys.executable+'\nimport sys\nif "--version" in sys.argv:\n    print("2.1.272 (Claude Code)"); raise SystemExit(0)\n'+CHILD.replace('Path(sys.argv[1])','Path('+repr(str(case_path))+')'))
    executable.chmod(0o700)
    c.manifest['repository']=str(ROOT)
    c.policy['readonly_lookups']['repository']=str(ROOT)
    c.manifest['native_runtime']['executable']=str(executable)
    c.manifest['pinned_files'][str(executable)]=native.sha(executable)
    c.manifest.update(provider_base_url='https://api.cborg.lbl.gov',budget={'prices_per_token':PRICES})
    c.job['deadline_seconds']=20
    # The synthetic helper runs the real pure contract but does not manufacture
    # frozen-generation ancestry. The production exact argv is tested above;
    # root's real registration replay covers its separate lineage admission.
    monkeypatch.setattr(native,'build_policy',lambda *_:c.policy)
    context=SimpleNamespace(manifest=c.manifest,job=c.job,attempt=c.attempt,registration_path=c.registration,
        manifest_sha256='synthetic-registration',ledger=c.ledger,verify=lambda:None)
    sdk=SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **kw:SimpleNamespace(input_tokens=100)))
    return context, sdk


def test_execute_job_connects_controls_context_and_terminal_recheck(native_case,monkeypatch):
    c=native_case
    context, sdk=configure_execution(c,monkeypatch)
    result=native.execute_job(context,client=sdk,upstream=httpx.Client(transport=httpx.MockTransport(
        lambda req:httpx.Response(200,content=response_events(),headers={'content-type':'text/event-stream'}))))
    assert result['validation']['passed'] and result['runtime']['unfinished_handlers']==0
    assert result['evidence']['initial_context']['complete_inline_context_observed']
    assert result['audit_path']==Path(c.job['audit_path'])


@pytest.mark.parametrize('registered', [False, True])
def test_delayed_headers_use_only_registered_native_client_timeout(native_case, monkeypatch, registered):
    """Scaled child default versus a longer registered timeout, using real loopback HTTP."""
    import time
    c = native_case
    c.case.update(default_timeout_ms=250, final_request=False)
    context, sdk = configure_execution(c, monkeypatch)
    # A long ambient value must not rescue the unregistered child. A short
    # ambient value must not replace the explicit timeout of the registered one.
    monkeypatch.setenv('API_TIMEOUT_MS', '1' if registered else '5000')
    if registered:
        c.manifest['native_runtime']['api_timeout_ms'] = 5000
    calls = []
    def respond(request):
        calls.append(request)
        time.sleep(0.6)
        return httpx.Response(200, content=response_events(), headers={'content-type':'text/event-stream'})
    upstream = httpx.Client(transport=httpx.MockTransport(respond))
    if registered:
        result = native.execute_job(context, client=sdk, upstream=upstream)
        assert result['validation']['passed']
    else:
        with pytest.raises(BudgetStop):
            native.execute_job(context, client=sdk, upstream=upstream)
        assert 'TimeoutError' in (c.attempt / 'stderr.txt').read_text()
        assert not (c.attempt / 'validation.json').exists()
    rows = json.loads(c.ledger.path.read_text())['requests']
    assert len(calls) == len(rows) == 1
    folder = c.attempt / 'requests' / rows[0]['id']
    if registered:
        assert rows[0]['status'] == 'settled'
    # A disconnected child can still leave a complete upstream response during
    # bounded shutdown. Account it if captured; otherwise retain the reservation.
    # Neither outcome makes the timed-out child a completed audit.
    assert rows[0]['status'] == ('settled' if (folder / 'response.json').exists() else 'pending')
    assert calls[0].content == (folder / 'native_request.json').read_bytes()
    assert 'API_TIMEOUT_MS' not in calls[0].headers


@pytest.mark.parametrize('change', ['missing_metadata','missing_error_flag','missing_result'])
def test_marker_alone_cannot_admit_a_paid_request_before_typed_result(native_case,change):
    c=native_case;c.case['request_before_validator_result']=True
    if change!='missing_result':c.case[change]='Bash'
    with pytest.raises(BudgetStop):c.run()
    assert len(c.calls)==1
    rows=json.loads(c.ledger.path.read_text())['requests']
    assert len(rows)==1 and rows[0]['status']=='settled'
    assert json.loads((c.attempt/'validation.json').read_text())['passed'] is True


def test_genuine_stdout_http_race_waits_for_successful_result_then_admits(native_case):
    c=native_case;c.case['request_race_before_validator_result']=True;c.case['final_request']=False
    evidence=c.run()
    assert evidence['phase3']['validation']['passed'] and len(c.calls)==2
    assert all(r['status']=='settled' for r in json.loads(c.ledger.path.read_text())['requests'])



def configure_receipt_runner(c, monkeypatch):
    """Isolate runtime receipt behavior from separately tested lineage gates."""
    from audit_controls import registration
    context,sdk=configure_execution(c,monkeypatch)
    c.manifest['repository_commit']='synthetic-offline'
    review=c.registration.parent/'synthetic-review.json'
    review.write_text(json.dumps({'verdict':'approve','ci_conclusion':'success',
        'registration_sha256':native.sha(c.registration),'repository_commit':'synthetic-offline','allowed_jobs':[c.job['id']]}))
    monkeypatch.setattr(registration,'validate_registration',lambda _:c.manifest)
    monkeypatch.setattr(registration,'verify',lambda *_:None)
    monkeypatch.setattr(registration,'sequence_guard',lambda *_:nullcontext())
    monkeypatch.setattr(registration,'open_audit_ledger',lambda *_:c.ledger)
    # Only remove this fixture's empty directories; run_job must create them.
    Path(c.job['output_dir']).rmdir();c.attempt.rmdir()
    return context,sdk,review


def test_stopped_proxy_receipt_records_actual_drained_handlers(native_case,monkeypatch):
    c=native_case;_,sdk,review=configure_receipt_runner(c,monkeypatch)
    upstream=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(524,content=b'offline timeout')))
    def adapter(context):return native.execute_job(context,client=sdk,upstream=upstream)
    with pytest.raises(BudgetStop) as error:native.run_job(c.registration,review,adapter=adapter)
    receipt=json.loads((c.attempt/'result.json').read_text())
    assert receipt['status']=='stopped' and receipt['stop_source']=='native_proxy'
    assert receipt['runtime']=={'proxy_initialized':True,'proxy_shutdown_complete':True,'unfinished_handlers':0}
    assert receipt['runtime']==error.value.native_stop['runtime']
    assert len(receipt['unresolved_requests'])==1
    rows=json.loads(c.ledger.path.read_text())['requests']
    assert len(rows)==1 and rows[0]['status']=='pending'


def test_deadline_receipt_keeps_actual_unfinished_handler_and_original_stop_source(native_case,monkeypatch):
    c=native_case;_,sdk,review=configure_receipt_runner(c,monkeypatch)
    c.job['deadline_seconds']=0.6
    entered,released,done=threading.Event(),threading.Event(),threading.Event()
    observed=[]
    original=native.AuditProxy
    class ObservedProxy(original):
        def __init__(self,**kwargs):super().__init__(**kwargs);observed.append(self)
    monkeypatch.setattr(native,'AuditProxy',ObservedProxy)
    def wait_for_release(_):
        entered.set()
        assert released.wait(10)
        done.set()
        return httpx.Response(200,content=response_events(),headers={'content-type':'text/event-stream'})
    upstream=httpx.Client(transport=httpx.MockTransport(wait_for_release))
    def adapter(context):return native.execute_job(context,client=sdk,upstream=upstream)
    try:
        with pytest.raises(BudgetStop,match='deadline'):native.run_job(c.registration,review,adapter=adapter)
        assert entered.is_set()
        receipt=json.loads((c.attempt/'result.json').read_text())
        assert receipt['stop_source']=='native_controller' and receipt['status']=='stopped'
        assert receipt['runtime']=={'proxy_initialized':True,'proxy_shutdown_complete':True,'unfinished_handlers':1}
        assert receipt['runtime']['unfinished_handlers']==observed[0].unfinished_handlers
        assert len(receipt['unresolved_requests'])==1
        before=c.ledger.path.read_bytes()
        released.set();assert done.wait(2)
        with observed[0].state:assert observed[0].state.wait_for(lambda:observed[0].active_handlers==0,timeout=2)
        assert c.ledger.path.read_bytes()==before
        assert json.loads(before)['requests'][0]['status']=='pending'
    finally:
        released.set()


def test_preproxy_failure_records_unknown_count_instead_of_a_zero(native_case,monkeypatch):
    c=native_case;_,sdk,review=configure_receipt_runner(c,monkeypatch)
    def adapter(context):
        context.verify=lambda:(_ for _ in ()).throw(BudgetStop('synthetic prelaunch pin refusal'))
        return native.execute_job(context,client=sdk)
    with pytest.raises(BudgetStop,match='prelaunch pin'):native.run_job(c.registration,review,adapter=adapter)
    receipt=json.loads((c.attempt/'result.json').read_text())
    assert receipt['stop_source']=='native_preflight'
    assert receipt['runtime']=={'proxy_initialized':False,'proxy_shutdown_complete':False,'unfinished_handlers':None}
    assert receipt['requests_admitted']==0 and not (c.attempt/'requests').exists()


def test_incomplete_proxy_setup_does_not_claim_its_initial_zero_as_final(native_case,monkeypatch):
    c=native_case;context,sdk=configure_execution(c,monkeypatch)
    @contextmanager
    def did_not_start(self,**kwargs):
        raise BudgetStop('synthetic proxy setup failure')
        yield
    monkeypatch.setattr(native.AuditProxy,'running',did_not_start)
    with pytest.raises(BudgetStop) as error:native.execute_job(context,client=sdk)
    assert error.value.native_stop=={'stop_source':'native_setup','runtime':
        {'proxy_initialized':True,'proxy_shutdown_complete':False,'unfinished_handlers':None}}


def test_postcheck_failure_reports_the_completed_shutdown(native_case,monkeypatch):
    c=native_case;context,sdk=configure_execution(c,monkeypatch)
    monkeypatch.setattr(native,'inspect_transcript',lambda *_:(_ for _ in ()).throw(BudgetStop('synthetic transcript recheck failure')))
    upstream=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(200,content=response_events(),headers={'content-type':'text/event-stream'})))
    with pytest.raises(BudgetStop) as error:native.execute_job(context,client=sdk,upstream=upstream)
    assert error.value.native_stop=={'stop_source':'native_postcheck','runtime':
        {'proxy_initialized':True,'proxy_shutdown_complete':True,'unfinished_handlers':0}}



def test_shutdown_failure_is_named_and_does_not_invent_a_final_handler_count(native_case,monkeypatch):
    c=native_case;context,sdk=configure_execution(c,monkeypatch)
    @contextmanager
    def interrupted_shutdown(self,**kwargs):
        yield 'http://127.0.0.1:1'
        raise BudgetStop('synthetic shutdown failure')
    monkeypatch.setattr(native.AuditProxy,'running',interrupted_shutdown)
    monkeypatch.setattr(native,'execute_child',lambda *a,**kw:0)
    with pytest.raises(BudgetStop) as error:native.execute_job(context,client=sdk)
    assert error.value.native_stop=={'stop_source':'native_shutdown','runtime':
        {'proxy_initialized':True,'proxy_shutdown_complete':False,'unfinished_handlers':None}}



def test_original_controller_stop_survives_later_proxy_failure(native_case,monkeypatch):
    c=native_case;context,sdk=configure_execution(c,monkeypatch)
    original=native.execute_child
    def controller_then_late_proxy(*args,**kwargs):
        # The real child/controller fails before validation; its callback must
        # identify that cause even if proxy shutdown then produces an error.
        try:return original(*args,**kwargs)
        except BudgetStop:
            kwargs['proxy'].fail(BudgetStop('synthetic later transport close failure'))
            raise
    c.case['calls'].pop()
    (c.registration.parent/'orchestration_case.json').write_text(json.dumps(c.case))
    monkeypatch.setattr(native,'execute_child',controller_then_late_proxy)
    upstream=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(200,content=response_events(),headers={'content-type':'text/event-stream'})))
    with pytest.raises(BudgetStop,match='completion lacks') as error:native.execute_job(context,client=sdk,upstream=upstream)
    assert error.value.native_stop['stop_source']=='native_controller'
    assert error.value.native_stop['runtime']['unfinished_handlers']==0


@pytest.mark.parametrize('secondary', [BudgetStop('synthetic shutdown failure'),
                                      RuntimeError('sensitive upstream details')])
def test_controller_exception_survives_raising_proxy_cleanup(native_case,monkeypatch,secondary):
    c=native_case;_,sdk,review=configure_receipt_runner(c,monkeypatch)
    primary=BudgetStop('synthetic original controller deadline')
    def child(*args,**kwargs):
        kwargs['record_stop'](str(primary))
        raise primary
    @contextmanager
    def interrupted_shutdown(self,**kwargs):
        try:yield 'http://127.0.0.1:1'
        finally:raise secondary
    monkeypatch.setattr(native,'execute_child',child)
    monkeypatch.setattr(native.AuditProxy,'running',interrupted_shutdown)
    def adapter(context):return native.execute_job(context,client=sdk)
    with pytest.raises(BudgetStop) as error:native.run_job(c.registration,review,adapter=adapter)
    assert error.value is primary
    receipt=json.loads((c.attempt/'result.json').read_text())
    assert receipt['reason']==str(primary) and receipt['stop_source']=='native_controller'
    assert receipt['cleanup_errors']==[{'source':'native_proxy_shutdown','error_type':type(secondary).__name__,
        'reason':str(secondary) if isinstance(secondary,BudgetStop) else type(secondary).__name__}]
    assert receipt['runtime']=={'proxy_initialized':True,'proxy_shutdown_complete':False,'unfinished_handlers':None}
    assert 'sensitive' not in json.dumps(receipt)
    stops=json.loads(c.ledger.path.read_text())['stopped_attempts']
    assert stops[receipt['billing_attempt']]['reason']==receipt['reason']


def test_child_cleanup_keeps_original_controller_exception(native_case,monkeypatch):
    c=native_case;context,sdk=configure_execution(c,monkeypatch)
    primary=BudgetStop('synthetic original controller failure')
    def child(*args,**kwargs):
        try:
            kwargs['record_stop'](str(primary))
            raise primary
        finally:raise RuntimeError('sensitive child cleanup details')
    @contextmanager
    def no_server(self,**kwargs):yield 'http://127.0.0.1:1'
    monkeypatch.setattr(native,'execute_child',child)
    monkeypatch.setattr(native.AuditProxy,'running',no_server)
    with pytest.raises(BudgetStop) as error:native.execute_job(context,client=sdk)
    assert error.value is primary
    assert error.value.native_stop['cleanup_errors']==[{'source':'native_controller_cleanup',
        'error_type':'RuntimeError','reason':'RuntimeError'}]


def test_recorded_controller_reason_survives_when_child_hides_original_exception(native_case,monkeypatch):
    c=native_case;context,sdk=configure_execution(c,monkeypatch)
    def child(*args,**kwargs):
        kwargs['record_stop']('synthetic first controller failure')
        kwargs['record_stop']('synthetic later symptom')
        raise RuntimeError('sensitive replaced exception')
    @contextmanager
    def no_server(self,**kwargs):yield 'http://127.0.0.1:1'
    monkeypatch.setattr(native,'execute_child',child)
    monkeypatch.setattr(native.AuditProxy,'running',no_server)
    with pytest.raises(BudgetStop,match='synthetic first controller failure') as error:
        native.execute_job(context,client=sdk)
    assert error.value.native_stop['primary_error_recovered_from_stop_record'] is True
    assert error.value.native_stop['cleanup_errors']==[{'source':'native_controller_cleanup',
        'error_type':'RuntimeError','reason':'RuntimeError'}]


def test_real_child_controller_cleanup_cannot_replace_recorded_failure(native_case,monkeypatch):
    c=native_case;context,sdk=configure_execution(c,monkeypatch)
    import run_native_canary
    terminate=run_native_canary.terminate_group
    def failing_cleanup(process):
        terminate(process)
        raise RuntimeError('sensitive termination cleanup details')
    c.case['calls'].pop()
    (c.registration.parent/'orchestration_case.json').write_text(json.dumps(c.case))
    monkeypatch.setattr(run_native_canary,'terminate_group',failing_cleanup)
    upstream=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(200,content=response_events(),headers={'content-type':'text/event-stream'})))
    with pytest.raises(BudgetStop,match='completion lacks') as error:
        native.execute_job(context,client=sdk,upstream=upstream)
    assert error.value.native_stop['stop_source']=='native_controller'
    assert error.value.native_stop['cleanup_errors']==[{'source':'native_controller_cleanup',
        'error_type':'RuntimeError','reason':'RuntimeError'}]
    assert error.value.native_stop['runtime']['unfinished_handlers']==0


def test_execute_job_uses_registered_factory_for_counting_and_raw_stream(native_case,monkeypatch):
    c=native_case;context,sdk=configure_execution(c,monkeypatch)
    counted=[];sent=[];factory_calls=[]
    sdk.messages.count_tokens=lambda **kwargs:(counted.append(kwargs) or SimpleNamespace(input_tokens=100))
    upstream=httpx.Client(transport=httpx.MockTransport(lambda request:(sent.append(request) or
        httpx.Response(200,content=response_events(),headers={'content-type':'text/event-stream'}))))
    def factory(manifest,key):
        factory_calls.append(manifest)
        assert key=='synthetic-offline-key'
        return sdk,upstream
    monkeypatch.setenv('CBORG_API_KEY','synthetic-offline-key')
    monkeypatch.setattr(native,'provider_clients',factory)
    result=native.execute_job(context)
    assert factory_calls==[c.manifest] and counted and len(counted)==len(sent)
    assert result['validation']['passed'] and upstream.is_closed
    assert result['runtime']['unfinished_handlers']==0


@pytest.mark.parametrize('closing_fails',[False,True])
def test_created_transport_closes_if_proxy_construction_fails(native_case,monkeypatch,closing_fails):
    c=native_case;context,sdk=configure_execution(c,monkeypatch)
    upstream=httpx.Client(transport=httpx.MockTransport(lambda _:pytest.fail('no model request expected')))
    closed=[]
    def close_sdk():
        closed.append(True)
        if closing_fails:raise RuntimeError('sensitive cleanup details')
    sdk.close=close_sdk
    monkeypatch.setenv('CBORG_API_KEY','synthetic-offline-key')
    monkeypatch.setattr(native,'provider_clients',lambda *_:(sdk,upstream))
    primary=BudgetStop('synthetic constructor failure')
    def fail(**kwargs):
        assert kwargs['sdk'] is sdk and kwargs['upstream'] is upstream
        raise primary
    monkeypatch.setattr(native,'AuditProxy',fail)
    with pytest.raises(BudgetStop) as error:native.execute_job(context)
    assert error.value is primary and closed==[True] and upstream.is_closed
    assert error.value.native_stop['stop_source']=='native_setup'
    assert error.value.native_stop['runtime']['unfinished_handlers'] is None
    if closing_fails:
        assert error.value.native_stop['cleanup_errors']==[{'source':'native_setup_cleanup',
            'error_type':'RuntimeError','reason':'RuntimeError'}]
