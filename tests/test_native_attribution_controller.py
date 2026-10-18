"""Offline real-dispatch tests; no native binary, auth or provider is invoked."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shlex
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_attribution_controller as controller
from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_source_attribution as supplement
from data_sheets_schema import source_attribution_preflight as preflight
from data_sheets_schema import evidence_assertions as evidence
from tests.test_native_source_attribution import case, call, result, valid_events
from tests.test_source_attribution_preflight import inputs, edited, claim


@pytest.fixture
def selected(case, tmp_path):
    spec, _, source = case
    clean = tmp_path / 'neutral-inputs'; clean.mkdir()
    for name,key in [('bundle.txt','bundle_raw'),('chunks.yaml','chunk_manifest_raw'),('sources.yaml','source_manifest_raw')]:
        (clean/name).write_bytes(source[key])
    spec = replace(spec, prompt_text_env=True, bundle=clean/'bundle.txt',
                   chunk_manifest=clean/'chunks.yaml', manifest=clean/'sources.yaml', manifest_line='# Source manifest: '+str(clean/'sources.yaml'),
                   out_dir=tmp_path/'neutral-output')
    spec.full_path.parent.mkdir()
    spec.full_path.write_bytes(source['record_raw']); spec.report_path.write_bytes(source['report_raw'])
    spec.core_path.write_bytes(source['record_raw'])
    folder = spec.full_path.parent/'evidence'; folder.mkdir()
    for name in ('original_full.yaml','original_core.yaml'):(folder/name).write_bytes(source['record_raw'])
    review=deepcopy(evidence.report_payload(source['report_raw'].decode(),protocol_version=5)['source_review'])
    review['artifact']='original_full'
    (folder/'audit.json').write_text(json.dumps({'findings':[],'summary':'Neutral unchanged record','source_review':review}))
    raw = draft._encoded(draft.registration(spec))
    instruction = tmp_path / 'instruction.md'
    instruction.write_bytes(spec.instruction.encode())
    value = controller.composition(raw, instruction)
    return spec, raw, source, instruction, draft._encoded(value)


def test_composition_can_prepare_and_matches_every_selected_command(selected):
    spec, raw, _, instruction, encoded = selected
    value = controller.verified_composition(encoded)
    adapter = controller.CallbackAdapter(encoded)
    assert adapter.policy['pretool_control'] == adapter.controls['native_control'].HISTORY_CONTRACT
    assert adapter.classify(shlex.join(supplement.command_args(spec)), adapter.policy['python'], set(), adapter.policy)[0] == 'prescribed'
    assert value['registration_sha256'] == draft._sha(raw)


CHILD = r'''
import json,os,subprocess,sys
from pathlib import Path
def send(value): print(json.dumps(value),flush=True)
init=json.loads(sys.stdin.readline()); callback=init['request']['hooks']['PreToolUse'][0]['hookCallbackIds'][0]
send({'type':'control_response','response':{'subtype':'success','request_id':init['request_id']}})
json.loads(sys.stdin.readline())
for number,step in enumerate(json.loads(Path(sys.argv[1]).read_text())):
    identity='tool-'+str(number); tool=step.get('tool','Bash'); args=step['input']
    send({'type':'assistant','message':{'content':[{'type':'tool_use','id':identity,'name':tool,'input':args}]}})
    for extra in step.get('before_callback',[]):send(extra)
    send({'type':'control_request','request_id':'request-'+str(number),'request':{'subtype':'hook_callback','callback_id':callback,'input':{'hook_event_name':'PreToolUse','tool_name':tool,'tool_use_id':identity,'cwd':os.getcwd(),'tool_input':args}}})
    line=sys.stdin.readline()
    if not line:sys.exit(7)
    reply=json.loads(line)
    assert not reply['response']['response'],reply
    if step.get('marker'):Path(step['marker']).write_text('executed only after callback')
    if tool=='Write':Path(args['file_path']).write_text(args['content']);code=0;text='{}'
    elif step.get('actual'):
        proc=subprocess.run(step['actual'],text=True,capture_output=True);code=proc.returncode;text=proc.stdout
    else:code=step.get('exit',0);text=json.dumps(step.get('payload',{}))
    stdout=text
    if step.get('stdout_mutation'):
        altered=json.loads(text);altered['checked']=1 if step['stdout_mutation']=='numeric' else False
        stdout=json.dumps(altered)
    send({'type':'user','tool_use_result':{'exitCode':code,'stdout':stdout},'message':{'content':[{'type':'tool_result','tool_use_id':identity,'is_error':bool(code),'content':text}]}})
send({'type':'result'})
'''


def run_fake(selected, tmp_path, steps, *, before=None, deadline_seconds=15):
    spec,raw,source,instruction,encoded=selected
    adapter=controller.CallbackAdapter(encoded)
    attempt=tmp_path/'new-attempt';attempt.mkdir(exist_ok=False)
    path=tmp_path/'steps.json';path.write_text(json.dumps(steps))
    stopped=[];closed=[]
    proxy=SimpleNamespace(failed=threading.Event(),failure=None,close_admission=lambda:closed.append(True))
    if before:before(adapter,proxy)
    try:
        status=adapter.controls['run_native_canary'].execute_child(
            [sys.executable,'-c',CHILD,str(path),'--input-format','stream-json'],proxy=proxy,
            instruction=instruction,attempt=attempt,cwd=Path.cwd(),env={**__import__('os').environ, 'D4D_LAUNCH_INSTRUCTION':str(instruction)},
            deadline_seconds=deadline_seconds,verify_launch=lambda:controller.verified_composition(encoded),
            command_policy=adapter.policy,phase_spec=spec,command_classifier=adapter.classify,
            event_observer=adapter.observe,record_stop=stopped.append)
        return adapter,status,stopped
    finally:
        assert closed
        assert (attempt/'transcript.jsonl').exists() and (attempt/'control.jsonl').exists()


def draft_step(spec, **extras):
    argv=supplement.command_args(spec)
    return {'input':{'command':shlex.join(argv)},'actual':argv,**extras}


def final_step(spec, marker):
    cmd=next(c for c,k in draft._commands(spec).items() if k=='final_evidence')
    return {'input':{'command':cmd},'actual':shlex.split(cmd),'marker':str(marker)}


def recorder_step(selected, **extras):
    command=json.loads(selected[-1])['policy']['post_final_recorder']['command']
    return {'input':{'command':command},'actual':shlex.split(command),**extras}


def test_actual_recorder_after_final_only_writes_new_provenance(selected,tmp_path):
    spec=selected[0]
    protected={p:p.read_bytes() for p in spec.full_path.parent.rglob('*') if p.is_file()}
    protected.update({p:p.read_bytes() for p in (spec.bundle,spec.chunk_manifest,spec.manifest,selected[3])})
    before={p for p in spec.full_path.parent.rglob('*') if p.is_file()}
    adapter,status,stops=run_fake(selected,tmp_path,[draft_step(spec),
        final_step(spec,tmp_path/'final'),recorder_step(selected)],deadline_seconds=60)
    destination=Path(adapter.policy['post_final_recorder']['destination'])
    assert status==0 and not stops and adapter.report(complete=True)['recorder_completed']
    assert destination.is_file() and destination.stat().st_nlink==1
    assert {p for p in spec.full_path.parent.rglob('*') if p.is_file()}-before=={destination}
    assert all(p.read_bytes()==raw for p,raw in protected.items())
    assert adapter.report(complete=True)['draft_gate_passed']
    assert adapter.report()['recorder_identity']['sha256']==draft._sha(destination.read_bytes())
    destination.write_bytes(destination.read_bytes()+b'\n')
    report=adapter.report(complete=True)
    assert not report['draft_gate_passed'] and 'metadata changed' in report['controller_stop']


@pytest.mark.parametrize('path',['core','audit'])
def test_completed_report_rechecks_final_inputs_without_another_tool(selected,tmp_path,path):
    spec=selected[0]
    adapter,status,stops=run_fake(selected,tmp_path,[draft_step(spec),final_step(spec,tmp_path/'final')])
    assert status==0 and not stops and adapter.report(complete=True)['draft_gate_passed']
    target=spec.core_path if path=='core' else spec.full_path.parent/'evidence'/'audit.json'
    target.write_bytes(target.read_bytes()+b'\n')
    report=adapter.report(complete=True)
    assert not report['draft_gate_passed'] and 'changed' in report['controller_stop']


def test_completed_recorder_cannot_repeat_or_start_another_tool(selected,tmp_path):
    marker=tmp_path/'second-recorder-must-not-run'
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='continuation after completed'):
        run_fake(selected,tmp_path,[draft_step(selected[0]),final_step(selected[0],tmp_path/'final'),
            recorder_step(selected),recorder_step(selected,marker=str(marker))],deadline_seconds=60)
    assert not marker.exists()


def test_recorder_cannot_run_before_real_final_pass(selected,tmp_path):
    marker=tmp_path/'recorder-must-not-run'
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='settled final'):
        run_fake(selected,tmp_path,[draft_step(selected[0]),recorder_step(selected,marker=str(marker))])
    assert not marker.exists()


@pytest.mark.parametrize('mode',['regular','symlink','hardlink'])
def test_recorder_refuses_existing_destination_without_overwrite(selected,tmp_path,mode):
    target=Path(json.loads(selected[-1])['policy']['post_final_recorder']['destination'])
    original=tmp_path/'preserved-metadata';original.write_bytes(b'preserve this metadata')
    if mode=='regular':target.write_bytes(original.read_bytes())
    elif mode=='symlink':target.symlink_to(original)
    else:__import__('os').link(original,target)
    marker=tmp_path/'recorder-must-not-run'
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='destination exists'):
        run_fake(selected,tmp_path,[draft_step(selected[0]),final_step(selected[0],tmp_path/'final'),
            recorder_step(selected,marker=str(marker))])
    assert not marker.exists() and target.read_bytes()==original.read_bytes()==b'preserve this metadata'


def test_failed_recorder_is_terminal_and_never_retried(selected,tmp_path):
    attempted=tmp_path/'recorder-attempted';again=tmp_path/'recorder-retry-forbidden'
    step=recorder_step(selected,actual=None,exit=1,marker=str(attempted))
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='recorder failed'):
        run_fake(selected,tmp_path,[draft_step(selected[0]),final_step(selected[0],tmp_path/'final'),
            step,recorder_step(selected,marker=str(again))])
    assert attempted.exists() and not again.exists()


def test_recorder_result_cannot_hide_dataset_mutation(selected,tmp_path):
    spec=selected[0];destination=json.loads(selected[-1])['policy']['post_final_recorder']['destination']
    # An adversarial local child claims it ran the prescribed command but changes
    # the full file. This is not the real recorder's behavior.
    program='from pathlib import Path; import sys; Path(sys.argv[1]).write_text("changed"); Path(sys.argv[2]).write_text("fake metadata")'
    step=recorder_step(selected,actual=[sys.executable,'-c',program,str(spec.full_path),destination])
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='current|changed'):
        run_fake(selected,tmp_path,[draft_step(spec),final_step(spec,tmp_path/'final'),step])


def test_correction_window_refuses_derive_even_after_old_phase2_completed(selected,tmp_path):
    policy=json.loads(selected[-1])['policy'];spellings=policy['helper_arguments']['spellings']
    # Synthetic successful phase metadata solely exercises the unchanged old
    # phase gate. It does not claim this neutral fixture completed generation.
    receipt={'input':{'command':spellings['receipts'][0]},'payload':{}}
    derive={'input':{'command':spellings['derive'][0]},'payload':{}}
    marker=tmp_path/'second-derive-must-not-run'
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='correction permits'):
        run_fake(selected,tmp_path,[receipt,derive,draft_step(selected[0]),{**derive,'marker':str(marker)}])
    assert not marker.exists()


def test_actual_callback_permits_valid_draft_before_final_command(selected,tmp_path):
    spec=selected[0]; marker=tmp_path/'final-was-admitted'
    adapter,status,stops=run_fake(selected,tmp_path,[draft_step(spec),final_step(spec,marker)])
    assert status==0 and not stops and marker.read_text()
    assert adapter.report(complete=True)['draft_gate_passed']


@pytest.mark.parametrize('mutation',['numeric','false'])
def test_actual_final_result_duplicate_stdout_must_agree_with_strict_types(selected,tmp_path,mutation):
    marker=tmp_path/'recorder-must-not-run'
    final={**final_step(selected[0],tmp_path/'final-check-executed'),'stdout_mutation':mutation}
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='stdout disagree'):
        run_fake(selected,tmp_path,[draft_step(selected[0]),final,recorder_step(selected,marker=str(marker))])
    assert not marker.exists()


@pytest.mark.parametrize('scenario',['missing','failed','unusable','changed_report','protected_write','terminal_failure'])
def test_real_callback_stops_before_bad_tool_marker(selected,tmp_path,scenario):
    spec,_,source,_,_=selected;marker=tmp_path/'must-not-run'
    steps=[draft_step(spec)]
    if scenario=='missing':steps=[]
    elif scenario=='failed':
        spec.report_path.write_bytes(edited(source,lambda r:claim(r).update(attributed_to=['project_documentation']))['report_raw'])
    elif scenario=='unusable':
        steps=[{'input':{'command':shlex.join(supplement.command_args(spec))},'exit':2,'payload':{'checked':False,'passed':False}}]
    elif scenario in ('changed_report','protected_write'):
        path=spec.report_path if scenario=='changed_report' else spec.full_path
        steps += [{'tool':'Write','input':{'file_path':str(path),'content':'changed'},'marker':str(marker) if scenario=='protected_write' else str(tmp_path/'report-write')}]
    else:
        command=next(c for c,k in draft._commands(spec).items() if k=='source_inventory')
        steps=[{'input':{'command':command},'exit':1}]
    steps.append(final_step(spec,marker))
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop):run_fake(selected,tmp_path,steps)
    assert not marker.exists()


def test_real_callback_allows_report_only_correction_and_fresh_check(selected,tmp_path):
    spec,_,source,_,_=selected
    spec.report_path.write_bytes(edited(source,lambda r:claim(r).update(attributed_to=['project_documentation']))['report_raw'])
    marker=tmp_path/'final-after-correction'
    steps=[draft_step(spec),{'tool':'Write','input':{'file_path':str(spec.report_path),'content':source['report_raw'].decode()}},draft_step(spec),final_step(spec,marker)]
    adapter,status,stops=run_fake(selected,tmp_path,steps)
    assert status==0 and not stops and marker.exists()
    assert adapter.report(complete=True)['checks']==2


@pytest.mark.parametrize('kind',['overlap_write','overlap_read'])
def test_same_frame_pending_tool_blocks_draft_callback(selected,tmp_path,kind):
    spec=selected[0];marker=tmp_path/'draft-must-not-run'
    pending={'type':'assistant','message':{'content':[{'type':'tool_use','id':'pending',
        'name':'Write' if kind=='overlap_write' else 'Read',
        'input':{'file_path':str(spec.report_path),'content':'changed'} if kind=='overlap_write' else {'file_path':str(spec.report_path)}}]}}
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='pending tool'):
        run_fake(selected,tmp_path,[draft_step(spec,marker=str(marker),before_callback=[pending])])
    assert not marker.exists()


def test_existing_proxy_stop_does_not_retry_or_admit_a_tool(selected,tmp_path):
    marker=tmp_path/'must-not-run'
    def stop(adapter,proxy):proxy.failed.set();proxy.failure='already stopped synthetic upstream'
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='already stopped'):
        run_fake(selected,tmp_path,[draft_step(selected[0],marker=str(marker))],before=stop)
    assert not marker.exists()
    before=(tmp_path/'new-attempt'/'transcript.jsonl').read_bytes()
    with pytest.raises(FileExistsError):run_fake(selected,tmp_path,[])
    assert (tmp_path/'new-attempt'/'transcript.jsonl').read_bytes()==before


def test_unchanged_phase_history_still_stops_early_core_derivation(selected,tmp_path):
    spec=selected[0];marker=tmp_path/'core-must-not-run'
    command=shlex.join([spec._agentic_toolchain['python'],'-m','data_sheets_schema.cli','derive','core','--full',str(spec.full_path),'--out',str(spec.core_path)])
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='passing receipt'):
        run_fake(selected,tmp_path,[{'input':{'command':command},'marker':str(marker)}])
    assert not marker.exists()


@pytest.mark.parametrize('field',['version','policy','policy_sha256','controller_sources','registration_sha256','instruction_sha256'])
def test_composition_pin_and_selection_drift_refuses(selected,field):
    value=json.loads(selected[-1])
    if field=='version':value[field]=True
    elif field=='policy':
        value[field]['attribution_command']+=' --help'
        value['policy_sha256']=draft._sha(draft._encoded(value[field]))
    elif field=='controller_sources':value[field]['modules'].pop('native_control')
    else:value[field]='0'*64
    with pytest.raises(ValueError):controller.CallbackAdapter(draft._encoded(value))


def test_dependency_origin_is_checked_before_ambient_module_is_used(selected,monkeypatch,tmp_path):
    fake=SimpleNamespace(__file__=str(tmp_path/'foreign.py'))
    monkeypatch.setitem(sys.modules,'native_control',fake)
    with pytest.raises(ValueError,match='another origin'):controller.verified_composition(selected[-1])


def test_missing_controller_dependency_refuses_without_modifying_it(selected,monkeypatch):
    original=Path.read_bytes
    target=controller.ROOT/'notes/matched_cborg_2026-09-13/native_controls/native_control.py'
    def read(path):
        if path==target:raise FileNotFoundError('synthetic missing dependency')
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',read)
    with pytest.raises(FileNotFoundError):controller.verified_composition(selected[-1])


def test_exclusive_composition_writer_preserves_inputs_and_existing_destination(selected,tmp_path):
    spec,raw,_,instruction,_=selected
    target=tmp_path/'composition.json'
    before=instruction.read_bytes()
    controller.write_composition(raw,instruction,target)
    captured=target.read_bytes()
    for path in (target,instruction):
        with pytest.raises(FileExistsError):controller.write_composition(raw,instruction,path)
    assert target.read_bytes()==captured and instruction.read_bytes()==before


def test_incremental_prefix_does_not_require_an_already_completed_draft(selected):
    state=draft.NativeAttributionState(selected[1],live=True)
    assert state.report()['problems']==[] and not state.report()['draft_gate_passed']
    assert state.report(complete=True)['problems']==['no current passing draft check']
    for event in valid_events(selected[0]):state.observe(event)
    assert state.report(complete=True)['draft_gate_passed']


def test_recomputation_barrier_holds_next_real_callback(selected,tmp_path):
    marker=tmp_path/'final-after-verification'; entered=threading.Event(); release=threading.Event(); observed=[]
    threads=[]
    def before(adapter,proxy):
        original=adapter.state._check_current
        def blocked(problems):
            entered.set()
            assert release.wait(5),'test must release checker'
            return original(problems)
        adapter.state._check_current=blocked
        def check_barrier():
            try:
                assert entered.wait(5),'real checker observer was not reached'
                transcript=tmp_path/'new-attempt'/'transcript.jsonl'
                limit=time.monotonic()+5
                while 'request-1' not in transcript.read_text():
                    assert time.monotonic()<limit,'later callback was not queued behind observer'
                    time.sleep(.005)
                control=(tmp_path/'new-attempt'/'control.jsonl').read_text()
                observed.append(not marker.exists() and 'request-1' not in control)
            finally:release.set()
        worker=threading.Thread(target=check_barrier);worker.start();threads.append(worker)
    try:
        adapter,status,stops=run_fake(selected,tmp_path,[draft_step(selected[0]),final_step(selected[0],marker)],before=before)
        assert status==0 and not stops and observed==[True] and marker.exists()
    finally:
        release.set()
        for worker in threads:worker.join(5);assert not worker.is_alive()


def test_observer_exception_stops_and_preserves_first_cause(selected,tmp_path):
    marker=tmp_path/'must-not-run'; adapters=[]
    def before(adapter,proxy):
        adapters.append(adapter)
        def broken(problems):raise OSError('synthetic checker read failure')
        adapter.state._check_current=broken
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='synthetic checker read failure'):
        run_fake(selected,tmp_path,[draft_step(selected[0]),final_step(selected[0],marker)],before=before)
    assert not marker.exists()
    saved=adapters[0].failure
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop):adapters[0].observe({})
    assert adapters[0].failure==saved


def test_existing_deadline_stops_without_a_tool_or_retry(selected,tmp_path):
    marker=tmp_path/'must-not-run'
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='deadline'):
        run_fake(selected,tmp_path,[draft_step(selected[0],marker=str(marker))],deadline_seconds=0.000001)
    assert not marker.exists()


def test_registered_draft_limit_stops_before_fourth_call(selected,tmp_path):
    marker=tmp_path/'fourth-must-not-run'
    steps=[draft_step(selected[0]) for _ in range(3)]+[draft_step(selected[0],marker=str(marker))]
    with pytest.raises(controller.load_controls()['budgeted_cborg'].BudgetStop,match='limit exceeded'):
        run_fake(selected,tmp_path,steps)
    assert not marker.exists()


@pytest.mark.parametrize('mode',['absent','unused'])
def test_no_draft_authority_added_for_omitted_or_unused_manifest(selected,tmp_path,mode):
    spec=replace(selected[0],manifest=None if mode=='absent' else selected[0].manifest,
                 manifest_line='# Source manifest: not used')
    raw=draft._encoded(draft.registration(spec)); instruction=tmp_path/'new-instruction.md';instruction.write_text(spec.instruction)
    value=controller.composition(raw,instruction)
    assert '--source-manifest' not in shlex.split(value['policy']['attribution_command'])
    assert 'source_manifest' not in json.loads(raw)['inputs']
    assert bool(value['metadata_inputs']) is (mode=='unused')
    if mode=='unused':
        spec.manifest.write_bytes(spec.manifest.read_bytes()+b'\n')
        with pytest.raises(ValueError):controller.verified_composition(draft._encoded(value))


def test_runtime_inadmissible_quoted_recording_identity_refuses_before_output(case,tmp_path):
    spec=replace(case[0],prompt_text_env=True);raw=draft._encoded(draft.registration(spec))
    instruction=tmp_path/'quoted-instruction.md';instruction.write_text(spec.instruction)
    destination=tmp_path/'must-not-exist.json'
    with pytest.raises(ValueError,match='not admitted'):
        controller.write_composition(raw,instruction,destination)
    assert not destination.exists()
