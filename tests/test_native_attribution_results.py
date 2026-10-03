"""Fresh neutral callback traces and strict offline saved-byte replay."""
from copy import deepcopy
import json
from pathlib import Path
import os
import shlex

import pytest

from data_sheets_schema import native_attribution_results as results
from data_sheets_schema import native_attribution_registration as draft
from tests.test_native_attribution_controller import inputs, case, selected, run_fake, draft_step, final_step, recorder_step


@pytest.fixture(scope='module')
def trace(tmp_path_factory):
    root=tmp_path_factory.mktemp('saved-native-trace')
    source=inputs.__wrapped__()
    base=case.__wrapped__(root,source)
    selection=selected.__wrapped__(base,root)
    (root/'composition.json').write_bytes(selection[-1])
    adapter,status,stops=run_fake(selection,root,[draft_step(selection[0]),final_step(selection[0],root/'final-marker')],deadline_seconds=60)
    assert status==0 and not stops and adapter.report(complete=True)['draft_gate_passed']
    return root,selection


def prepare(trace):
    root,_=trace
    return results.capture(root/'composition.json',root/'new-attempt/transcript.jsonl',root/'new-attempt/control.jsonl')


def test_actual_saved_trace_replays_under_same_policy(trace):
    prepared=prepare(trace)
    report=results.check_capture(prepared)
    assert report['additional_gate_passed'],report['problems']
    assert report['generation_acceptance']=='not_assessed'
    assert report['control_history']['decisions']==2
    assert report['command_history']['calls'][0]['classification']=='prescribed'
    assert report['draft_history']['observations'][-1]['verified_against_current_saved_bytes']
    assert {'composition','transcript','control','audit','original_full','original_core','final_full','final_core','report'} <= {r for row in report['raw_files'].values() for r in row['roles']}


@pytest.mark.parametrize('mode',['passed','failed','unusable'])
def test_offline_cli_distinguishes_gate_failure_and_unusable_input(trace,tmp_path,capsys,mode):
    root,_=trace
    transcript=root/'new-attempt/transcript.jsonl'
    if mode=='failed':
        changed=tmp_path/'failed-attempt';changed.mkdir()
        transcript=_changed_events(trace,changed,lambda rows: rows[-1].update(is_error=True))
    elif mode=='unusable':
        transcript=tmp_path/'missing-transcript.jsonl'
    output=tmp_path/'replay-result.json'
    status=results.main(['--composition',str(root/'composition.json'),'--transcript',str(transcript),
                         '--control',str(root/'new-attempt/control.jsonl'),'--out',str(output)])
    report=json.loads(capsys.readouterr().out)
    assert status=={'passed':0,'failed':1,'unusable':2}[mode]
    assert report['additional_gate_passed'] is (mode=='passed')
    assert report['generation_acceptance']=='not_assessed'
    assert output.exists() is (mode!='unusable')
    if output.exists():assert json.loads(output.read_bytes())==report


def test_sealed_replay_never_reads_live_file_bytes(trace,monkeypatch):
    prepared=prepare(trace)
    def forbidden(*args,**kwargs):raise AssertionError('live file read after snapshot seal')
    monkeypatch.setattr(Path,'read_bytes',forbidden)
    monkeypatch.setattr(Path,'read_text',forbidden)
    monkeypatch.setattr(Path,'open',forbidden)
    monkeypatch.setattr(Path,'resolve',forbidden)
    assert results.check_capture(prepared)['additional_gate_passed']


def test_current_final_snapshot_matches_actual_checker(trace):
    prepared=prepare(trace)
    from data_sheets_schema.native_attribution_controller import CallbackAdapter
    actual=CallbackAdapter(prepared['composition_raw'])._current_final()
    assert results._final_evidence(prepared['snapshot'],prepared['state'].spec)==actual


@pytest.mark.parametrize('mutation',['terminal_error','missing_terminal','after_terminal','missing_callback','duplicate_result'])
def test_bad_saved_trace_does_not_pass_current_files(trace,tmp_path,mutation):
    root,_=trace
    events=[draft._json(line) for line in (root/'new-attempt/transcript.jsonl').read_bytes().splitlines()]
    if mutation=='terminal_error':events[-1]['is_error']=True
    elif mutation=='missing_terminal':events.pop()
    elif mutation=='after_terminal':events.append(deepcopy(next(e for e in events if e.get('type')=='assistant')))
    elif mutation=='missing_callback':events.remove(next(e for e in events if e.get('type')=='control_request'))
    else:events.insert(-1,deepcopy(next(e for e in events if e.get('type')=='user')))
    path=tmp_path/'changed-transcript.jsonl';path.write_bytes(b''.join(draft._encoded(e).replace(b'\n',b' ')+b'\n' for e in events))
    report=results.check_files(root/'composition.json',path,root/'new-attempt/control.jsonl')
    assert not report['additional_gate_passed'] and report['problems']


@pytest.mark.parametrize('mutation',['cancel','duplicate_ack','late_ack','extra_error_response',
    'failed_ack','missing_ack','callback_before_ack','result_before_ack','ack_after_terminal',
    'unknown_control','callback_uses_init_id'])
def test_live_control_lifecycle_is_required_by_public_replay(trace,tmp_path,mutation):
    def change(events):
        ack=next(e for e in events if e.get('type')=='control_response')
        if mutation=='cancel':
            index=next(n for n,e in enumerate(events) if e.get('type')=='user')
            events.insert(index,{'type':'control_cancel_request','request_id':'request-0'})
        elif mutation=='duplicate_ack':events.insert(0,deepcopy(ack))
        elif mutation=='late_ack':events.remove(ack);events.insert(-1,ack)
        elif mutation=='extra_error_response':events.insert(1,{'type':'control_response','response':{'subtype':'error','request_id':'extra'}})
        elif mutation=='failed_ack':ack['response']['subtype']='error'
        elif mutation=='missing_ack':events.remove(ack)
        elif mutation=='callback_before_ack':
            callback=next(e for e in events if e.get('type')=='control_request');events.remove(callback);events.insert(0,callback)
        elif mutation=='result_before_ack':
            result=next(e for e in events if e.get('type')=='user');events.remove(result);events.insert(0,result)
        elif mutation=='ack_after_terminal':events.remove(ack);events.append(ack)
        elif mutation=='unknown_control':events.insert(1,{'type':'control_future_request','request_id':'new'})
        else:next(e for e in events if e.get('type')=='control_request')['request_id']=ack['response']['request_id']
    path=_changed_events(trace,tmp_path,change)
    report=results.check_files(trace[0]/'composition.json',path,trace[0]/'new-attempt/control.jsonl')
    assert not report['additional_gate_passed']
    assert report['control_lifecycle']['checked'] and report['control_lifecycle']['problems']


def test_control_journal_initialization_order_is_required(trace,tmp_path):
    prepared=prepare(trace);records=deepcopy(prepared['records'])
    records[0],records[1]=records[1],records[0]
    control=tmp_path/'reordered-control.jsonl'
    control.write_text(''.join(json.dumps(row)+'\n' for row in records))
    report=results.check_files(trace[0]/'composition.json',trace[0]/'new-attempt/transcript.jsonl',control)
    assert not report['additional_gate_passed'] and report['control_lifecycle']['problems']


@pytest.mark.parametrize('kind',['regular','hardlink','symlink'])
def test_actual_completed_recorder_retains_live_file_requirements(tmp_path,kind):
    source=inputs.__wrapped__();base=case.__wrapped__(tmp_path,source);selection=selected.__wrapped__(base,tmp_path)
    spec=selection[0]
    adapter,status,stops=run_fake(selection,tmp_path,[draft_step(spec),final_step(spec,tmp_path/'final'),recorder_step(selection)],deadline_seconds=60)
    assert status==0 and not stops
    composition=tmp_path/'composition.json';composition.write_bytes(selection[-1])
    destination=Path(draft._json(selection[-1])['policy']['post_final_recorder']['destination'])
    before=destination.read_bytes();alias=tmp_path/'preserved-provenance.yaml'
    if kind=='hardlink':alias.hardlink_to(destination)
    elif kind=='symlink':destination.rename(alias);destination.symlink_to(alias)
    prepared=results.capture(composition,tmp_path/'new-attempt/transcript.jsonl',tmp_path/'new-attempt/control.jsonl')
    report=results.check_capture(prepared)
    assert report['additional_gate_passed'] is (kind=='regular')
    assert report['recorder_completed_in_trace'] is (kind=='regular')
    if kind!='regular':assert any('regular non-symlink single-link' in p for p in report['problems'])
    else:assert adapter.report(complete=True)['draft_gate_passed']
    assert destination.read_bytes()==before



def test_old_authority_cannot_be_relabelled_with_rehashed_outer_fields(trace,tmp_path):
    root,_=trace
    original=(root/'composition.json').read_bytes()
    value=draft._json(original)
    registration=draft._json(value['registration_raw_json'])
    registration['code_commit']='4ee87580c5472aee2d30cabec4dff1b230de8436'
    raw=draft._encoded(registration)
    value['registration_raw_json']=raw.decode()
    value['registration_sha256']=draft._sha(raw)
    changed=tmp_path/'old-authority.json';changed.write_bytes(draft._encoded(value))
    with pytest.raises(ValueError,match='registration differs'):
        results.capture(changed,root/'new-attempt/transcript.jsonl',root/'new-attempt/control.jsonl')
    assert (root/'composition.json').read_bytes()==original


def _changed_events(trace,tmp_path,change):
    root,_=trace
    events=[draft._json(line) for line in (root/'new-attempt/transcript.jsonl').read_bytes().splitlines()]
    change(events)
    path=tmp_path/'changed.jsonl'
    path.write_bytes(b''.join(json.dumps(e,separators=(',',':')).encode()+b'\n' for e in events))
    return path


@pytest.mark.parametrize('bad',[False,[],4,{},'bad'])
def test_malformed_callback_request_is_explicitly_uncheckable(trace,tmp_path,bad):
    def change(events):next(e for e in events if e.get('type')=='control_request')['request']=bad
    path=_changed_events(trace,tmp_path,change)
    with pytest.raises(ValueError,match='malformed saved callback'):
        results.check_files(trace[0]/'composition.json',path,trace[0]/'new-attempt/control.jsonl')


@pytest.mark.parametrize('kind',['blank','duplicate_key','nonfinite'])
def test_invalid_raw_jsonl_never_disappears_during_normalization(trace,tmp_path,kind):
    root,_=trace
    path=tmp_path/'bad.jsonl'
    extra={'blank':b'\n','duplicate_key':b'{"type":"result","type":"result"}\n','nonfinite':b'{"type":"result","value":NaN}\n'}[kind]
    path.write_bytes((root/'new-attempt/transcript.jsonl').read_bytes()+extra)
    with pytest.raises(ValueError):results.check_files(root/'composition.json',path,root/'new-attempt/control.jsonl')


@pytest.mark.parametrize('field',['timeout','version'])
def test_control_metadata_numeric_type_cannot_impersonate_selected_integer(trace,tmp_path,field):
    root,_=trace
    rows=[draft._json(line) for line in (root/'new-attempt/control.jsonl').read_bytes().splitlines()]
    sent=next(r for r in rows if r['kind']=='initialize_sent')
    if field=='timeout':
        hook=sent['frame']['request']['hooks']['PreToolUse'][0];hook['timeout']=float(hook['timeout'])
    else:sent['frame']['request_id']=False
    path=tmp_path/'control.jsonl';path.write_bytes(b''.join(json.dumps(r).encode()+b'\n' for r in rows))
    report=results.check_files(root/'composition.json',root/'new-attempt/transcript.jsonl',path)
    assert not report['additional_gate_passed'] and report['control_history']['problems']


@pytest.mark.parametrize('role',['report','final_full','final_core','audit'])
def test_raw_artifact_change_invalidates_trace_but_not_already_captured_bytes(trace,tmp_path,role):
    prepared=prepare(trace)
    path=next(Path(p) for p,row in prepared['snapshot'].identity().items() if role in row['roles'])
    original=path.read_bytes()
    try:
        path.write_bytes(original+b'\n')
        # Immutable snapshot still describes its original bytes; publication
        # cannot silently present those bytes as the now-modified inputs.
        assert results.check_capture(prepared)['additional_gate_passed']
        target=tmp_path/'must-not-publish.json'
        with pytest.raises(ValueError,match='changed before report publication'):
            results.write_report(prepared,target)
        assert not target.exists()
        changed=prepare(trace)
        report=results.check_capture(changed)
        assert not report['additional_gate_passed'] and report['problems']
    finally:path.write_bytes(original)


@pytest.mark.parametrize('scenario',['valid','missing_result','duplicate_call','earlier_result','denied_success','denied_error','unknown','bad_identity'])
def test_legacy_command_structured_outputs_match_frozen_helper(trace,scenario):
    prepared=prepare(trace);native=prepared['controls']['run_native_canary'];policy=prepared['policy']
    events=[deepcopy(e) for e in prepared['events'] if e.get('type') in ('assistant','user')][-2:]
    identity=events[0]['message']['content'][0]['id'];denials=[]
    if scenario=='missing_result':events.pop()
    elif scenario=='duplicate_call':events.insert(1,deepcopy(events[0]))
    elif scenario=='earlier_result':events.reverse()
    elif scenario in ('denied_success','denied_error'):
        denials=[{'tool_use_id':identity}]
        if scenario=='denied_error':events[-1]['message']['content'][0]['is_error']=True
    elif scenario=='unknown':events[0]['message']['content'][0]['input']['command']='unexpected program'
    elif scenario=='bad_identity':events[0]['message']['content'][0]['id']=False
    assert results.command_history(events,policy,denials,native._classify_command)==native.command_history(events,policy,denials)


@pytest.mark.parametrize('raw',[None,[],{},[None],[{'tool_name':'Bash','tool_input':{}}],
    [{'tool_name':'Bash','tool_input':{'command':'unexpected program'}}],
    [{'tool_name':'Read','tool_input':{'file_path':'/unregistered-neutral-path'}}]])
def test_legacy_denial_structured_outputs_match_frozen_helper(trace,raw):
    prepared=prepare(trace);native=prepared['controls']['run_native_canary'];policy=prepared['policy']
    expected=native.classify_denials(raw,instruction_text=prepared['instruction'],python=policy['python'],
        repository=policy['readonly_lookups']['repository'],output_directories=policy['readonly_lookups']['output_directories'],
        readable_inputs=policy['readonly_lookups']['inputs'],command_policy=policy)
    assert results.classify_denials(raw,policy,native._classify_command,prepared['controls'],prepared['instruction'])==expected


def test_prescribed_draft_denial_is_disqualifying(trace,tmp_path):
    command=json.loads((trace[0]/'composition.json').read_bytes())['policy']['attribution_command']
    def change(events):events[-1]['permission_denials']=[{'tool_name':'Bash','tool_use_id':'tool-0','tool_input':{'command':command}}]
    path=_changed_events(trace,tmp_path,change)
    report=results.check_files(trace[0]/'composition.json',path,trace[0]/'new-attempt/control.jsonl')
    assert report['denial_classification'][0]['classification']=='prescribed'
    assert not report['additional_gate_passed'] and report['problems']


@pytest.mark.parametrize('mode',['same','hardlink','symlink'])
def test_writer_preserves_all_input_aliases(trace,tmp_path,mode):
    prepared=prepare(trace);source=trace[0]/'new-attempt/transcript.jsonl';before=source.read_bytes()
    destination=source if mode=='same' else tmp_path/'report.json'
    if mode=='hardlink':os.link(source,destination)
    elif mode=='symlink':destination.symlink_to(source)
    with pytest.raises(ValueError,match='aliases|metadata changed'):results.write_report(prepared,destination)
    assert source.read_bytes()==before


@pytest.mark.parametrize('kind',['attempt','registered_output'])
def test_writer_cannot_add_artifacts_to_retained_attempt(trace,kind):
    prepared=prepare(trace)
    directory=(trace[0]/'new-attempt' if kind=='attempt' else
               Path(prepared['policy']['readonly_lookups']['output_directories'][0]))
    destination=directory/'new-replay-report.json'
    assert not destination.exists()
    with pytest.raises(ValueError,match='retained attempt or registered output'):
        results.write_report(prepared,destination)
    assert not destination.exists()


def test_writer_is_exclusive_and_successful_json_binds_raw_files(trace,tmp_path):
    prepared=prepare(trace);target=tmp_path/'report.json'
    report=results.write_report(prepared,target)
    assert json.loads(target.read_bytes())==report and report['additional_gate_passed']
    before=target.read_bytes()
    with pytest.raises(FileExistsError):results.write_report(prepared,target)
    assert target.read_bytes()==before and target.stat().st_nlink==1


def test_writer_io_failure_leaves_no_final_report(trace,tmp_path,monkeypatch):
    prepared=prepare(trace);target=tmp_path/'must-not-publish.json'
    def failed(*a,**k):raise OSError('synthetic fsync failure')
    monkeypatch.setattr(os,'fsync',failed)
    with pytest.raises(OSError,match='synthetic'):results.write_report(prepared,target)
    assert not target.exists()


@pytest.mark.parametrize('mode',['correction','recorder'])
def test_actual_correction_and_recorder_saved_trace(tmp_path,mode):
    source=inputs.__wrapped__();base=case.__wrapped__(tmp_path,source);selection=selected.__wrapped__(base,tmp_path)
    spec=selection[0];steps=[draft_step(spec)]
    if mode=='correction':
        steps += [{'tool':'Write','input':{'file_path':str(spec.report_path),'content':source['report_raw'].decode()+'\n'}},draft_step(spec)]
    steps.append(final_step(spec,tmp_path/'final'))
    if mode=='recorder':steps.append(recorder_step(selection))
    adapter,status,stops=run_fake(selection,tmp_path,steps,deadline_seconds=60)
    assert status==0 and not stops
    path=tmp_path/'composition.json';path.write_bytes(selection[-1])
    report=results.check_files(path,tmp_path/'new-attempt/transcript.jsonl',tmp_path/'new-attempt/control.jsonl')
    assert report['additional_gate_passed'],report['problems']
    if mode=='correction':
        assert report['draft_history']['checks']==2
        assert [r['verified_against_current_saved_bytes'] for r in report['draft_history']['observations']]==[False,True]
    else:assert report['recorder_completed_in_trace']


@pytest.mark.parametrize('renderer',[17,18,19,20,21,22,23])
def test_each_selected_native_protocol_replays_actual_neutral_trace(tmp_path,renderer):
    from dataclasses import replace
    from data_sheets_schema import native_attribution_controller as controller
    source=inputs.__wrapped__();base=case.__wrapped__(tmp_path,source)
    selection=selected.__wrapped__(base,tmp_path)
    spec=replace(selection[0],render_version=renderer)
    raw=draft._encoded(draft.registration(spec));instruction=tmp_path/'selected-instruction.md';instruction.write_text(spec.instruction)
    encoded=draft._encoded(controller.composition(raw,instruction))
    selection=(spec,raw,source,instruction,encoded)
    adapter,status,stops=run_fake(selection,tmp_path,[draft_step(spec),final_step(spec,tmp_path/'final')],deadline_seconds=60)
    assert status==0 and not stops
    path=tmp_path/'selected-composition.json';path.write_bytes(encoded)
    report=results.check_files(path,tmp_path/'new-attempt/transcript.jsonl',tmp_path/'new-attempt/control.jsonl')
    assert report['additional_gate_passed'],report['problems']


def test_persisted_output_cannot_make_capture_read_arbitrary_config_files(trace,tmp_path,monkeypatch):
    config=tmp_path/'config';config.mkdir();sensitive=config/'private-config.json';sensitive.write_text('must not be read')
    def change(events):
        event=next(e for e in events if e.get('type')=='user')
        event.update(session_id='00000000-0000-0000-0000-000000000000')
        event['tool_use_result'].update(persistedOutputPath=str(sensitive),persistedOutputSize=sensitive.stat().st_size)
    path=_changed_events(trace,tmp_path,change)
    original=Path.open
    def guarded(self,*args,**kwargs):
        assert self!=sensitive,'unregistered config content was read'
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'open',guarded)
    prepared=results.capture(trace[0]/'composition.json',path,trace[0]/'new-attempt/control.jsonl',config_root=config)
    report=results.check_capture(prepared)
    assert not report['additional_gate_passed'] and report['control_history']['problems']
    assert str(sensitive) not in report['raw_files']


def test_current_captured_file_policy_matches_frozen_structured_outcomes(trace,tmp_path):
    prepared=prepare(trace);snapshot=prepared['snapshot'];policy=prepared['policy'];controls=prepared['controls']
    # A separate pre-seal snapshot records current metadata for valid inputs,
    # outputs, missing outputs, an unregistered path and a hard-linked output.
    snap=results.Capture(Path.cwd())
    source=trace[1][0].bundle;output=trace[1][0].report_path
    missing=output.parent/'missing-neutral-output';unknown=tmp_path/'unregistered'
    link=output.parent/'linked-neutral-output'
    os.link(output,link)
    try:
        for path in (source,output,missing,unknown,link):snap.path(path)
        current=results.CapturedFiles(snap,policy,controls)
        old=controls['native_file_policy'].FileAccess(policy)
        snap.sealed=True
        for tool in ('Read','Write'):
            for path in (source,output,missing,unknown,link):
                payload={'file_path':str(path)}
                assert current.classify(tool,payload)==old.classify(tool,payload)
    finally:link.unlink()  # Only this test's new neutral hard link.


@pytest.mark.parametrize('scenario',['valid','missing_decision','duplicate_decision','wrong_policy','wrong_response',
    'callback_before_call','unknown_record','missing_result','spurious_result'])
def test_legacy_control_structured_outputs_match_frozen_helper(trace,tmp_path,scenario):
    prepared=prepare(trace);control=prepared['controls']['native_control'];native=prepared['controls']['run_native_canary']
    events=[deepcopy(e) for e in prepared['events']]
    # Retain only the pre-existing final-evidence command, removing the extra
    # attribution command from this parity fixture.
    events=[e for e in events if not (
        any(isinstance(b,dict) and (b.get('id')=='tool-0' or b.get('tool_use_id')=='tool-0') for b in results._blocks(e))
        or e.get('request_id')=='request-0')]
    records=[deepcopy(r) for r in prepared['records'] if (r.get('request') or {}).get('request_id')!='request-0']
    decision=next(r for r in records if r['kind']=='decision')
    if scenario=='missing_decision':records.remove(decision)
    elif scenario=='duplicate_decision':records.append(deepcopy(decision))
    elif scenario=='wrong_policy':next(r for r in records if r['kind']=='initialize_sent')['policy_sha256']='0'*64
    elif scenario=='wrong_response':decision['response']['response']['subtype']='error'
    elif scenario=='callback_before_call':
        callback=next(e for e in events if e.get('type')=='control_request');events.remove(callback);events.insert(0,callback)
    elif scenario=='unknown_record':records.append({'kind':'unknown'})
    elif scenario=='missing_result':events.remove(next(e for e in events if e.get('type')=='user'))
    elif scenario=='spurious_result':events.append({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'unknown','is_error':True}]}})
    path=tmp_path/'control.jsonl';path.write_bytes(b''.join(json.dumps(r).encode()+b'\n' for r in records))
    expected=control.check_control_history(events,path,prepared['policy'],native._classify_command)
    actual=results._control_history(events,records,prepared['policy'],native._classify_command,
        deepcopy(prepared['files']),prepared['controls'])
    assert actual==expected


def test_persisted_output_validates_from_captured_bytes_with_legacy_parity(trace,tmp_path,monkeypatch):
    prepared=prepare(trace);policy=prepared['policy'];controls=prepared['controls']
    config=tmp_path/'config';session='00000000-0000-0000-0000-000000000000'
    import re
    directory=config/'projects'/re.sub(r'[^a-zA-Z0-9]','-',policy['readonly_lookups']['repository'])/session/'tool-results'
    directory.mkdir(parents=True);path=directory/'neutral-output.txt';path.write_text('neutral persisted output')
    snap=results.Capture(Path.cwd());snap.path(config);snap.read(path,'persisted_output')
    actual=results.CapturedFiles(snap,policy,controls,config);old=controls['native_file_policy'].FileAccess(policy,config)
    init={'type':'system','subtype':'init','session_id':session,'cwd':policy['readonly_lookups']['repository']}
    calls={'tool':{'name':'Bash'}};decisions={'tool':'prescribed'}
    event={'type':'user','session_id':session,'tool_use_result':{'persistedOutputPath':str(path),'persistedOutputSize':path.stat().st_size},
        'message':{'content':[{'type':'tool_result','tool_use_id':'tool','content':f'<persisted-output>\nFull output saved to: {path}\n'}]}}
    old.observe(init,calls,decisions);expected=old.observe(event,calls,decisions)
    expected_classification=old.classify('Read',{'file_path':str(path)})
    snap.sealed=True
    def forbidden(*a,**k):raise AssertionError('persisted replay read live bytes or metadata')
    for name in ('open','read_bytes','read_text','resolve','stat'):monkeypatch.setattr(Path,name,forbidden)
    actual.observe(init,calls,decisions)
    assert actual.observe(event,calls,decisions)==expected
    assert actual.classify('Read',{'file_path':str(path)})==expected_classification


def test_publication_refuses_metadata_drift_even_if_input_bytes_match(trace,tmp_path):
    prepared=prepare(trace);source=trace[1][0].report_path;link=tmp_path/'new-link'
    os.link(source,link)
    try:
        with pytest.raises(ValueError,match='metadata changed'):
            results.write_report(prepared,tmp_path/'must-not-publish.json')
    finally:link.unlink()


def test_writer_cannot_use_absent_registered_artifact_target(trace):
    prepared=prepare(trace)
    target=Path(prepared['policy']['post_final_recorder']['destination'])
    assert not target.exists()
    with pytest.raises(ValueError,match='captured artifact'):
        results.write_report(prepared,target)
    assert not target.exists()
