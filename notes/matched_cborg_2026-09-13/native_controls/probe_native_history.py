"""Real pinned CLI with an invented tool and in-memory provider; no external API.

Each case owns a fresh config/work directory. Cancellation fault explicitly feeds
one synthetic frame through the production intake parser for an actual callback.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

CLI_VERSION='2.1.272'
CLI_SHA='195e24e8e1f9bf46f1eaee72d434a33e18f9f5796f29a6348a00d16c5f8aee75'
PYTHON=sys.executable
CASES=('legacy_quick','selected_slow','selected_reject','selected_cancel','selected_deadline','legacy_slow')


def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as f:
        while b:=f.read(1024*1024):value.update(b)
    return value.hexdigest()


def validate_runtime(path):
    path=Path(path).resolve(strict=True)
    if sha(path)!=CLI_SHA:raise ValueError('offline probe requires its exact pinned runtime')
    version=subprocess.check_output([str(path),'--version'],text=True).strip()
    if not version.startswith(CLI_VERSION+' '):raise ValueError('offline probe runtime version changed')
    return path


def public_summary(commit,source_hashes,unchanged,reports):
    """Only fixed summaries and relative source names; raw fixture bodies stay local."""
    if any(Path(name).is_absolute() or '..' in Path(name).parts for name in source_hashes):
        raise ValueError('public probe source names must be relative')
    fields=('case','passed','selected_history_contract','contract','exit_code','error_class','stop_reason_code',
        'tool_executions','observer_entered','observer_finished','observer_duration_seconds','classifier_calls',
        'classification_followed_observer','stop_duration_seconds','counts','fault_injected_cancel_frames',
        'controller_shutdown_snapshots','workers_alive_after_fixture_release','ledger_rows','unsettled_rows',
        'unfinished_proxy_handlers','scripted_upstream_calls','real_provider_calls','evidence_sha256')
    summaries=[{key:row[key] for key in fields} for row in reports]
    return {'kind':'synthetic_real_native_history_barrier_probe_v1','passed':all(r['passed'] for r in reports) and unchanged,
        'native_version':CLI_VERSION,'native_executable_sha256':CLI_SHA,'repository_commit':commit,
        'source_sha256':source_hashes,'source_unchanged_during_probe':unchanged,'probe_sha256':sha(__file__),
        'cases':summaries,'provider_calls':0,'actual_scientific_or_experiment_artifact_reads':0,
        'limits':'Synthetic tool and scripted upstream only; cancellation case explicitly injects a frame; no actual-run causal proof or scientific acceptance.'}


def run_case(repo,cli,destination,name):
    import httpx
    from budgeted_cborg import Ledger,BudgetStop
    import native_control as control
    import run_native_canary as runner
    from native_proxy import NativeProxy
    from native_command_policy import permission_arguments,_literal_rule
    from audit_controls.native import classify_command

    root=destination/name;root.mkdir();work=root/'work';work.mkdir();config=root/'config';config.mkdir()
    helper=work/'synthetic_tool.py'
    helper.write_text('from pathlib import Path\nimport time\np=Path("executions.jsonl")\nwith p.open("a") as f:f.write(str(time.monotonic())+"\\n")\nprint("SYNTHETIC_TOOL_COMPLETE")\n')
    argv=[PYTHON,str(helper)];command=shlex.join(argv)
    marker=work/'executions.jsonl';selected=name.startswith('selected_')
    policy={'version':1,'pretool_control':deepcopy(control.HISTORY_CONTRACT if selected else control.CONTRACT),
        'python':PYTHON,'programs':[],'manifest_paths':[],'validator_argv':argv,'assemble_argv':[],
        'allowed_tools':[_literal_rule(command)],'readonly_lookups':{'repository':str(work),'inputs':[str(helper)],
        'output_directories':[str(work)],'write_paths':{str(marker):1024}}}
    instruction=root/'instruction.txt';instruction.write_text('Run only the supplied synthetic helper once and finish. No other files or networks.\n')
    calls=[];tooled=[];observed=[];classified=[];stops=[];entered=threading.Event();released=threading.Event();finished=threading.Event()
    controls=[];injected=[]
    def respond(request):
        assert request.url.host=='api.cborg.lbl.gov'  # Virtual URL only: MockTransport performs no network.
        body=json.loads(request.content);calls.append(body)
        if body.get('tools'):tooled.append(body)
        block=({'type':'tool_use','id':'offline_history_tool','name':'Bash',
                'input':{'command':command,'description':'Run the synthetic owned fixture'}}
               if body.get('tools') and len(tooled)==1 else {'type':'text','text':'SYNTHETIC_COMPLETE'})
        tool=block['type']=='tool_use';start={**block,'input' if tool else 'text':{} if tool else ''}
        delta={'type':'input_json_delta','partial_json':json.dumps(block['input'])} if tool else {'type':'text_delta','text':block['text']}
        events=[{'type':'message_start','message':{'id':f'fixture_{len(calls)}','type':'message','role':'assistant',
            'model':body['model'],'content':[],'stop_reason':None,'stop_sequence':None,'usage':{'input_tokens':100,'output_tokens':0}}},
            {'type':'content_block_start','index':0,'content_block':start},
            {'type':'content_block_delta','index':0,'delta':delta},{'type':'content_block_stop','index':0},
            {'type':'message_delta','delta':{'stop_reason':'tool_use' if tool else 'end_turn','stop_sequence':None},'usage':{'output_tokens':12}},
            {'type':'message_stop'}]
        raw=''.join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        return httpx.Response(200,content=raw,headers={'content-type':'text/event-stream'})
    def observe(event):
        message=event.get('message');blocks=message.get('content',[]) if isinstance(message,dict) else []
        if any(isinstance(b,dict) and b.get('type')=='tool_use' for b in blocks if isinstance(blocks,list)):
            observed.append({'event':'start','at':time.monotonic()});entered.set()
            try:
                if name in ('selected_cancel','selected_deadline'):released.wait(20)
                elif name in ('selected_slow','selected_reject','legacy_slow'):time.sleep(4.0)
                if name=='selected_reject':raise BudgetStop('synthetic history rejected before execution')
            finally:observed.append({'event':'finish','at':time.monotonic()});finished.set()
    def classify(*args):
        classified.append(time.monotonic());return classify_command(*args)
    Original=runner.NativeControl
    class Instrumented(Original):
        def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);controls.append(self)
        def _intake_history(self):
            super()._intake_history()
            if name=='selected_cancel' and entered.is_set() and self._callback_intake and not injected:
                rid=next(iter(self._callback_intake));frame={'type':'control_cancel_request','request_id':rid}
                injected.append({'at':time.monotonic(),'request_id_sha256':hashlib.sha256(rid.encode()).hexdigest()})
                raw=(json.dumps(frame)+'\n').encode();original_read=control.os.read;target=self.process.stdout.fileno()
                def fault_read(fd,size):return raw if fd==target else original_read(fd,size)
                control.os.read=fault_read
                try:super()._intake_history()
                finally:control.os.read=original_read
    runner.NativeControl=Instrumented
    ledger=Ledger(root/'ledger.json',manifest_sha256='synthetic-history-probe-only')
    sdk=SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **kw:SimpleNamespace(input_tokens=100)))
    proxy=NativeProxy(sdk=sdk,ledger=ledger,attempt='offline',evidence=root/'requests',model='claude-opus-5',
        prices={'input':.000005,'output':.000025,'cache_read':.0000005,'cache_write':.00000625},verify=lambda:None,
        provider_key='offline-fake-key',base_url='https://api.cborg.lbl.gov',upstream=httpx.Client(transport=httpx.MockTransport(respond),trust_env=False))
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','SHELL','TMPDIR','LANG','LC_ALL','TERM'}}
    env.update(CLAUDE_CONFIG_DIR=str(config),DISABLE_NON_ESSENTIAL_MODEL_CALLS='1',DISABLE_TELEMETRY='1',
        CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS='1',ANTHROPIC_API_KEY=proxy.token,PYTHONPATH=str(work))
    cli_args=[str(cli),'--print','--safe-mode','--restricted','--strict-mcp-config','--no-session-persistence',
        '--model','claude-opus-5','--name','d4d-synthetic-history-'+name,'--disable-slash-commands',
        '--max-budget-usd','5','--prompt-suggestions','false','--output-format','stream-json','--verbose',
        '--permission-mode','dontAsk','--tools','Bash',*permission_arguments(policy),
        '--system-prompt','Synthetic local fixture. Run only the provided helper. No other files or network.']
    exit_code=None;error_class=None;error_code=None;start=time.monotonic()
    try:
        with proxy.running() as url:
            env['ANTHROPIC_BASE_URL']=url
            exit_code=runner.execute_child(cli_args,proxy=proxy,instruction=instruction,attempt=root,cwd=work,env=env,
                deadline_seconds=8 if name=='selected_deadline' else 45,
                verify_launch=lambda:runner.verified_executable({'claude_executable':str(cli),'pinned_files':{str(cli):CLI_SHA}}),
                command_policy=policy,command_classifier=classify,event_observer=observe,
                record_stop=lambda reason:stops.append({'at':time.monotonic(),'reason':reason}))
    except BaseException as error:
        error_class=type(error).__name__;error_code=str(error) if isinstance(error,BudgetStop) else 'non_budget_exception'
    finally:
        stop_end=time.monotonic();released.set()
        if entered.is_set():finished.wait(3)
        for controller in controls:
            worker=getattr(controller,'_work_thread',None)
            if worker is not None:worker.join(3)
        runner.NativeControl=Original
    if not (root/'ledger.json').exists():raise RuntimeError('synthetic setup failed before ledger: '+str(error_class)+' / '+str(error_code))
    rows=json.loads((root/'ledger.json').read_bytes())['requests']
    events=[json.loads(line) for line in (root/'transcript.jsonl').read_text().splitlines() if line.strip()]
    records=[json.loads(line) for line in (root/'control.jsonl').read_text().splitlines() if line.strip()]
    times=[float(line) for line in marker.read_text().splitlines()] if marker.exists() else []
    counts={'callback':sum(e.get('type')=='control_request' for e in events),
        'cancel':sum(e.get('type')=='control_cancel_request' for e in events),
        'decision':sum(e.get('kind')=='decision' for e in records)}
    allowed=name in ('legacy_quick','selected_slow')
    passed=(exit_code==0 and len(times)==1 and not error_class) if allowed else (error_class=='BudgetStop' and not times)
    passed=passed and entered.is_set() and all(r['status']=='settled' for r in rows) and proxy.unfinished_handlers==0
    if name=='selected_slow':passed=passed and observed[-1]['at']-observed[0]['at']>=4 and times[0]>=observed[-1]['at'] and classified[0]>=observed[-1]['at']
    if name=='selected_reject':passed=passed and error_code=='synthetic history rejected before execution' and not classified
    if name=='selected_cancel':passed=passed and len(injected)==1 and counts['cancel']>=1 and not classified
    if name=='selected_deadline':passed=passed and stop_end-start<12 and not classified and bool(stops) and stops[0]['reason']=='native attempt deadline elapsed; retain all incomplete charge reservations'
    if name=='legacy_slow':passed=passed and counts['cancel']>=1
    if name in ('selected_cancel','selected_deadline'):
        passed=passed and len(controls)==1 and controls[0].unfinished_control_workers==1 and controls[0].control_shutdown_complete is False
        passed=passed and not (getattr(controls[0],'_work_thread',None) and controls[0]._work_thread.is_alive())
    if name=='selected_slow':passed=passed and controls[0].unfinished_control_workers==0 and controls[0].control_shutdown_complete is True
    report={'case':name,'passed':bool(passed),'selected_history_contract':selected,'contract':policy['pretool_control'],
        'exit_code':exit_code,'error_class':error_class,'stop_reason_code':{'synthetic history rejected before execution':'synthetic_history_rejected',
            'native control callback was cancelled or timed out':'native_callback_cancelled',
            'native attempt deadline elapsed; retain all incomplete charge reservations':'aggregate_deadline',
            'native control worker remains active; closure incomplete':'unfinished_control_worker'}.get(error_code,'none' if error_code is None else 'other_refusal'),'tool_executions':len(times),
        'observer_entered':entered.is_set(),'observer_finished':finished.is_set(),
        'observer_duration_seconds':observed[-1]['at']-observed[0]['at'] if len(observed)>1 else None,
        'classifier_calls':len(classified),'classification_followed_observer':not classified or classified[0]>=observed[-1]['at'],
        'stop_duration_seconds':stop_end-start,'counts':counts,'fault_injected_cancel_frames':len(injected),
        'controller_shutdown_snapshots':[{'unfinished_control_workers':getattr(c,'unfinished_control_workers',None),
            'control_shutdown_complete':getattr(c,'control_shutdown_complete',None)} for c in controls],
        'workers_alive_after_fixture_release':sum(bool(getattr(c,'_work_thread',None) and c._work_thread.is_alive()) for c in controls),
        'ledger_rows':len(rows),'unsettled_rows':sum(r['status']!='settled' for r in rows),'unfinished_proxy_handlers':proxy.unfinished_handlers,
        'scripted_upstream_calls':len(calls),'real_provider_calls':0,
        'evidence_sha256':{str(f.relative_to(root)):sha(f) for f in (root/'transcript.jsonl',root/'control.jsonl',root/'ledger.json')}}
    (root/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repository',type=Path,default=Path(__file__).resolve().parents[3]);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--claude-executable',type=Path,default=Path.home()/'.local/share/claude/versions'/CLI_VERSION)
    ap.add_argument('--case',choices=CASES,action='append');args=ap.parse_args()
    repo=args.repository.resolve(strict=True);destination=args.output.resolve();destination.mkdir(exist_ok=False)
    support=repo/'notes/matched_cborg_2026-09-13';native=support/'native_controls'
    sys.path[:0]=[str(native),str(support),str(repo/'src')]
    cli=validate_runtime(args.claude_executable)
    files=[native/'native_control.py',native/'run_native_canary.py',native/'native_proxy.py',support/'audit_controls/native.py']
    before={str(f.relative_to(repo)):sha(f) for f in files}
    commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    reports=[]
    for name in args.case or CASES:
        result=run_case(repo,cli,destination,name);reports.append(result)
        print(json.dumps({'case':name,'passed':result['passed'],'exit_code':result['exit_code'],'error_class':result['error_class'],
            'tool_executions':result['tool_executions'],'observer_duration_seconds':result['observer_duration_seconds']}),flush=True)
        if not result['passed']:break
    unchanged=all(sha(repo/f)==value for f,value in before.items())
    value=public_summary(commit,before,unchanged,reports)
    (destination/'result.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'passed':value['passed'],'sha256':sha(destination/'result.json'),'case_count':len(reports)}),flush=True)
    return 0 if value['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
