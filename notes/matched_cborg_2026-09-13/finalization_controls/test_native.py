"""Offline actual helpers, native child protocol and shared-budget integration."""
from copy import deepcopy
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

BASE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'native_controls'))
from audit_controls.test_native import CHILD, PRICES, response_events
from audit_controls import native as audit_runtime
from budgeted_cborg import BudgetStop, Ledger
from native_control import load_native_events
from run_native_canary import execute_child
from . import contract,native,registration
from .test_contract import final_fixture,write_report


@pytest.fixture
def case(tmp_path,monkeypatch):
    manifest=final_fixture(tmp_path);job=manifest['job']
    instruction=tmp_path/'instruction.md';instruction.write_text('Synthetic Phase 4 task; no real acceptance.\n')
    system=tmp_path/'system.md';system.write_text('Synthetic frozen scientific context.\n')
    manifest.update(repository=str(tmp_path),python=sys.executable,
        model={'model':'claude-opus-5'},native_runtime={'version':'2.1.272 (Claude Code)',
            'context_window':200000,'max_output_tokens':64000})
    job.update(instruction=str(instruction),system_prompt=str(system),deadline_seconds=60,
        readable_inputs=sorted(set(manifest['inputs'].values())|{str(instruction),str(system)}))
    for p in (instruction,system):manifest['pinned_files'][str(p)]=native.sha(p)
    path=tmp_path/'registration.json'
    prefix=[sys.executable,'-m','finalization_controls.contract','--registration',str(path)]
    job.update(derive_argv=[*prefix,'--operation','derive'],check_argv=[[*prefix,'--operation','check','--round',str(i)] for i in range(2)])
    path.write_text(json.dumps(manifest));identity=native.sha(path)
    policy=native.build_policy(manifest,path);history=native.FinalizationHistory(manifest,identity,policy)
    monkeypatch.setattr(registration,'validate_registration',lambda p:json.loads(Path(p).read_text()))
    monkeypatch.setattr(contract,'_report_context',lambda *args:'Actual report-context rendering tested separately.')
    monkeypatch.setattr(contract,'_run_validator',lambda *a,**kw:{'checked':True,'passed':True,'findings':[]})
    events=[]
    def call(tool,payload):
        ident='call-'+str(len(events))
        event={'type':'assistant','message':{'role':'assistant','content':[{'type':'tool_use','id':ident,'name':tool,'input':payload}]}}
        events.append(event);history.observe(event);return ident
    def result(ident,metadata,error=False,content="typed fixture result"):
        event={'type':'user','tool_use_result':metadata,'message':{'role':'user','content':[{'type':'tool_result','tool_use_id':ident,'is_error':error,'content':content}]}}
        events.append(event);history.observe(event)
    def write(role,text=None):
        target=Path(job[role+'_path']);text=text if text is not None else target.read_text()
        ident=call('Write',{'file_path':str(target),'content':text});target.write_text(text)
        result(ident,{'type':'update','filePath':str(target),'content':text})
    def read_context():
        ctx=history.context
        for selected in ctx['read_ranges']:
            ident=call('Read',{'file_path':ctx['path'],**selected})
            lines=Path(ctx['path']).read_text().split('\n')[selected['offset']-1:selected['offset']-1+selected['limit']]
            text='\n'.join(lines)
            numbered='\n'.join(str(i)+'\t'+line for i,line in enumerate(lines,selected['offset']))
            result(ident,{'type':'text','file':{'filePath':ctx['path'],'content':text,
                'startLine':selected['offset'],'numLines':selected['limit'],'totalLines':ctx['line_count']}},content=numbered)
    def helper(operation,round=None,*,deliver_context=True):
        from contextlib import redirect_stdout
        import io
        argv=job['derive_argv'] if operation=='derive' else job['check_argv'][round]
        ident=call('Bash',{'command':shlex.join(argv)})
        output=io.StringIO()
        with redirect_stdout(output):status=contract.main(argv[3:])
        result(ident,{'stdout':output.getvalue(),'stderr':'','interrupted':False,'exitCode':status},bool(status))
        value=json.loads(output.getvalue())
        if operation=='derive' and value.get('passed') is True and deliver_context:read_context()
        return value
    return SimpleNamespace(manifest=manifest,job=job,path=path,identity=identity,policy=policy,
        history=history,events=events,call=call,result=result,write=write,helper=helper,read_context=read_context,attempt=Path(job['attempt_dir']))


def complete_case(c):
    c.write('full');c.helper('derive');c.write('report');return c.helper('check',0)


def test_actual_helpers_and_current_typed_writes_complete(case):
    c=case;before={p:Path(p).read_bytes() for p in c.manifest['inputs'].values()}
    assert complete_case(c)['passed']
    assert c.history.finish()['closing_repairs']==0
    assert before=={p:Path(p).read_bytes() for p in before}


def test_one_report_repair_rederives_refreshes_and_replays_final_artifacts(case):
    c=case;c.write('full');c.helper('derive')
    write_report(c.manifest,disposition='removed');c.write('report')
    first=c.helper('check',0);assert first['repairable'] and not first['passed']
    c.helper('derive');write_report(c.manifest);c.write('report');assert c.helper('check',1)['passed']
    assert c.history.finish()['closing_repairs']==1
    replay=native.FinalizationHistory(c.manifest,c.identity,c.policy,replay=True)
    for event in c.events:replay.observe(event)
    assert replay.finish()['closing_repairs']==1


@pytest.mark.parametrize('role',['core','unregistered'])
def test_untrusted_write_cannot_edit_core_or_controller_files(case,role):
    c=case;target=c.job['core_path'] if role=='core' else str(c.attempt/'check-0.json')
    with pytest.raises(BudgetStop,match='may write only'):
        c.call('Write',{'file_path':target,'content':'forged'})


@pytest.mark.parametrize('stage',['without_full_write','pending_full_write','without_derive','without_report_write','check_one_first'])
def test_early_or_pending_gate_is_not_completion(case,stage):
    c=case
    with pytest.raises(BudgetStop):
        if stage=='without_full_write':c.helper('derive')
        elif stage=='pending_full_write':
            c.call('Write',{'file_path':c.job['full_path'],'content':'description: unfinished'})
            c.helper('derive')
        else:
            c.write('full')
            if stage=='without_derive':c.write('report')
            else:
                c.helper('derive')
                if stage=='check_one_first':c.write('report');c.helper('check',1)
                else:c.helper('check',0)


def test_full_write_invalidates_derived_pair_and_report(case):
    c=case;c.write('full');c.helper('derive');c.write('report')
    c.write('full','description: The service is planned.\n# second native write\n')
    with pytest.raises(BudgetStop,match='current derivation'):c.helper('check',0)


def test_source_failure_is_terminal_and_admits_no_repair(case):
    c=case;c.write('full');c.helper('derive')
    Path(c.job['report_path']).write_text('# Missing final source review\n');c.write('report')
    with pytest.raises(BudgetStop):c.helper('check',0)
    with pytest.raises(BudgetStop):c.history.verify_admission()
    assert (c.attempt/'failure.json').exists()


def test_second_ordinary_failure_is_terminal(case):
    c=case;c.write('full');c.helper('derive');write_report(c.manifest,disposition='removed');c.write('report')
    assert c.helper('check',0)['repairable']
    c.helper('derive');c.write('report')
    with pytest.raises(BudgetStop):c.helper('check',1)
    assert (c.attempt/'failure.json').exists()


def test_success_freezes_artifacts_and_all_future_tools(case):
    c=case;complete_case(c)
    with pytest.raises(BudgetStop,match='cannot continue'):c.call('Read',{'file_path':c.job['full_path']})


def test_current_file_tampering_after_pass_is_detected(case):
    c=case;complete_case(c);Path(c.job['full_path']).write_text('description: altered outside controller\n')
    with pytest.raises(BudgetStop):c.history.verify_admission()


def test_pending_helper_receipt_alone_cannot_admit(case,monkeypatch):
    c=case;c.write('full')
    c.call('Bash',{'command':shlex.join(c.job['derive_argv'])})
    monkeypatch.setattr(audit_runtime,'VALIDATOR_RESULT_WAIT_SECONDS',0)
    with pytest.raises(BudgetStop,match='typed result'):c.history.verify_admission()


@pytest.mark.parametrize('damage',['missing_metadata','error_flag','exit','interrupted'])
def test_helper_requires_typed_success_even_if_file_receipt_exists(case,damage):
    c=case;c.write('full');ident=c.call('Bash',{'command':shlex.join(c.job['derive_argv'])})
    metadata={'stdout':'{}','stderr':'','interrupted':False,'exitCode':0};error=False
    if damage=='missing_metadata':metadata={}
    elif damage=='error_flag':error=True
    elif damage=='exit':metadata['exitCode']=1
    else:metadata['interrupted']=True
    with pytest.raises(BudgetStop):c.result(ident,metadata,error)


READ_CHILD = CHILD.replace(
    "content=Path(payload['file_path']).read_text();error=False",
    """whole=Path(payload['file_path']).read_text().split('\\n');offset=payload['offset'];limit=payload['limit']
        selected=whole[offset-1:offset-1+limit];text='\\n'.join(selected)
        content='\\n'.join(str(i)+'\\t'+line for i,line in enumerate(selected,offset));error=False
        metadata={'type':'text','file':{'filePath':payload['file_path'],'content':text,
            'startLine':offset,'numLines':len(selected),'totalLines':len(whole)}}""").replace(
    "error=completed.returncode!=0;content=completed.stdout+completed.stderr",
    """error=completed.returncode!=0;content=completed.stdout+completed.stderr
        if not error:
            context=json.loads(completed.stdout).get('report_context')
            if context:
                case['calls'][index+1:index+1]=[{'name':'Read','input':{'file_path':context['path'],**part}} for part in context['read_ranges']]""")

HELPER='''
import json,sys
from pathlib import Path
from finalization_controls import contract,registration
registration.validate_registration=lambda path:json.loads(Path(path).read_bytes())
contract._report_context=lambda *args:'Synthetic shared-context stub; rendering covered separately.'
contract._run_validator=lambda *args,**kwargs:{'checked':True,'passed':True,'findings':[]}
raise SystemExit(contract.main(sys.argv[1:]))
'''


@pytest.mark.parametrize('mode',['complete','bad_evidence','core_write','context_write'])
def test_real_child_http_control_history_and_terminal_checks(case,tmp_path,mode):
    c=case;helper=tmp_path/'helper.py';helper.write_text(HELPER)
    prefix=[sys.executable,str(helper),'--registration',str(c.path)]
    c.job['derive_argv']=[*prefix,'--operation','derive']
    c.job['check_argv']=[[*prefix,'--operation','check','--round',str(i)] for i in range(2)]
    c.path.write_text(json.dumps(c.manifest));identity=native.sha(c.path)
    policy=deepcopy(c.policy);policy['helper_argv']=[c.job['derive_argv'],*c.job['check_argv']]
    policy['allowed_tools']=['Read','Write',*[native._literal_rule(shlex.join(v)) for v in policy['helper_argv']]]
    history=native.FinalizationHistory(c.manifest,identity,policy)
    report=Path(c.job['report_path']).read_text() if mode!='bad_evidence' else '# No source review\n'
    calls=[{'name':'Write','input':{'file_path':c.job['full_path'],'content':Path(c.job['full_path']).read_text()}},
        {'name':'Bash','input':{'command':shlex.join(c.job['derive_argv'])}},
        {'name':'Write','input':{'file_path':c.job['report_path'],'content':report}},
        {'name':'Bash','input':{'command':shlex.join(c.job['check_argv'][0])}}]
    if mode in ('core_write','context_write'):
        target=c.job['core_path'] if mode=='core_write' else str(Path(c.job['output_dir'])/'report_contexts'/'000001.jsonl')
        calls.insert(2,{'name':'Write','input':{'file_path':target,'content':'must never overwrite helper evidence'}})
    child_case=tmp_path/'child.json';child_case.write_text(json.dumps({'calls':calls,'system_prompt':Path(c.job['system_prompt']).read_text()}))
    ledger=Ledger(tmp_path/'synthetic_billing.json',manifest_sha256=identity,total_cap=400,attempt_cap=20)
    observed=[]
    def respond(request):observed.append(request);return httpx.Response(200,content=response_events(),headers={'content-type':'text/event-stream'})
    proxy=audit_runtime.AuditProxy(audit_history=history,
        sdk=SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **kwargs:SimpleNamespace(input_tokens=100))),
        ledger=ledger,attempt=identity+':'+c.job['id'],evidence=c.attempt/'requests',model='claude-opus-5',prices=PRICES,
        verify=history.verify_admission,provider_key='offline-key',base_url='https://api.cborg.lbl.gov',
        upstream=httpx.Client(transport=httpx.MockTransport(respond)))
    env={**os.environ,'PYTHONPATH':os.pathsep.join([str(BASE.parents[1]/'src'),str(BASE),str(BASE/'native_controls')]),'ANTHROPIC_API_KEY':proxy.token}
    def run():
        with proxy.running() as url:
            env['ANTHROPIC_BASE_URL']=url
            return execute_child([sys.executable,'-c',READ_CHILD,str(child_case),'--input-format','stream-json'],
                proxy=proxy,instruction=Path(c.job['instruction']),attempt=c.attempt,cwd=tmp_path,env=env,deadline_seconds=60,
                verify_launch=history.verify_admission,command_policy=policy,command_classifier=native.classify_command,
                event_observer=history.observe,record_stop=lambda why:ledger.stop_attempt(identity+':'+c.job['id'],why))
    if mode!='complete':
        with pytest.raises(BudgetStop):run()
        assert len(observed)==1
        if mode in ('core_write','context_write'):
            derivative=json.loads((c.attempt/'derivations'/'000001.json').read_text())
            expected=derivative['artifacts'][target] if mode=='core_write' else derivative['report_context']['sha256']
            assert native.sha(target)==expected
    else:
        assert run()==0
        evidence=native.inspect_transcript(load_native_events(c.attempt/'transcript.jsonl'),policy,c.manifest,identity,c.attempt/'control.jsonl',None)
        assert evidence['phase4']['closing_repairs']==0 and len(observed)==2
    assert all(r['status']=='settled' for r in json.loads(ledger.path.read_text())['requests'])
    assert proxy.frozen and proxy.unfinished_handlers==0


def test_report_cannot_skip_current_context_reads(case):
    c=case;c.write('full');c.helper('derive',deliver_context=False)
    with pytest.raises(BudgetStop,match='complete observed'):c.write('report')


@pytest.mark.parametrize('damage',['truncated_content','wrong_range','wrong_file','missing_metadata','numbered_surrogate'])
def test_report_context_requires_exact_typed_delivery(case,damage):
    c=case;c.write('full');c.helper('derive',deliver_context=False)
    ctx=c.history.context;selected=ctx['read_ranges'][0]
    ident=c.call('Read',{'file_path':ctx['path'],**selected})
    lines=Path(ctx['path']).read_text().split('\n')[selected['offset']-1:selected['offset']-1+selected['limit']]
    content='\n'.join(lines);numbered='\n'.join(str(i)+'\t'+line for i,line in enumerate(lines,selected['offset']))
    metadata={'type':'text','file':{'filePath':ctx['path'],'content':content,
        'startLine':selected['offset'],'numLines':selected['limit'],'totalLines':ctx['line_count']}}
    if damage=='truncated_content':metadata['file']['content']=content[:10]
    elif damage=='wrong_range':metadata['file']['startLine']+=1
    elif damage=='wrong_file':metadata['file']['filePath']=c.job['full_path']
    elif damage=='missing_metadata':metadata={}
    else:numbered='Tool output saved elsewhere'
    with pytest.raises(BudgetStop,match='exact typed delivery'):c.result(ident,metadata,content=numbered)


def test_phase4_backend_uses_production_native_engine(case,tmp_path,monkeypatch):
    c=case;helper=tmp_path/'engine_helper.py';helper.write_text(HELPER)
    prefix=[sys.executable,str(helper),'--registration',str(c.path)]
    c.job.update(derive_argv=[*prefix,'--operation','derive'],check_argv=[[*prefix,'--operation','check','--round',str(i)] for i in range(2)])
    c.manifest.update(repository=str(BASE.parents[1]),provider_base_url='https://api.cborg.lbl.gov',provider_context_policy='headroom_bypass_v1',
        budget={'prices_per_token':PRICES})
    c.path.write_text(json.dumps(c.manifest));identity=native.sha(c.path)
    policy=deepcopy(c.policy);policy['helper_argv']=[c.job['derive_argv'],*c.job['check_argv']]
    policy['allowed_tools']=['Read','Write',*[native._literal_rule(shlex.join(v)) for v in policy['helper_argv']]]
    calls=[{'name':'Write','input':{'file_path':c.job['full_path'],'content':Path(c.job['full_path']).read_text()}},
        {'name':'Bash','input':{'command':shlex.join(c.job['derive_argv'])}},
        {'name':'Write','input':{'file_path':c.job['report_path'],'content':Path(c.job['report_path']).read_text()}},
        {'name':'Bash','input':{'command':shlex.join(c.job['check_argv'][0])}}]
    policy['readonly_lookups']['repository']=c.manifest['repository']
    child=tmp_path/'engine_child.json';child.write_text(json.dumps({'calls':calls,'system_prompt':Path(c.job['system_prompt']).read_text()}))
    monkeypatch.setattr(native,'build_policy',lambda *args:policy)
    monkeypatch.setattr(audit_runtime,'verify_runtime',lambda *args:Path(sys.executable))
    def run_child(argv,**kwargs):
        assert isinstance(kwargs['event_observer'].__self__,native.FinalizationHistory)
        assert kwargs['command_classifier'] is native.classify_command
        return execute_child([sys.executable,'-c',READ_CHILD,str(child),'--input-format','stream-json'],**kwargs)
    monkeypatch.setattr(audit_runtime,'execute_child',run_child)
    ledger=Ledger(tmp_path/'engine_billing.json',manifest_sha256=identity,total_cap=400,attempt_cap=20)
    context=SimpleNamespace(manifest=c.manifest,job=c.job,attempt=c.attempt,manifest_sha256=identity,
        registration_path=c.path,ledger=ledger,verify=lambda:None)
    sdk=SimpleNamespace(default_headers={'x-headroom-bypass':'true'},messages=SimpleNamespace(count_tokens=lambda **kwargs:SimpleNamespace(input_tokens=100)))
    upstream=httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=response_events(),headers={'content-type':'text/event-stream'})))
    result=native.execute_job(context,client=sdk,upstream=upstream)
    assert result['validation']['passed'] and result['runtime']['proxy_shutdown_complete']
    assert result['evidence']['initial_context']['complete_inline_context_observed']
    assert result['evidence']['phase4']['report_context_reads']
    assert len(json.loads(ledger.path.read_text())['requests'])==2
