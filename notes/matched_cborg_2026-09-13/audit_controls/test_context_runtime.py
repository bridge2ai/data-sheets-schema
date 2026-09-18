"""Bounded recovery admission/delivery, including actual local transport ordering."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

BASE=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(BASE),str(BASE/'native_controls')]
from budgeted_cborg import BudgetStop
from native_file_policy import FileAccess
import native_context_control as recovery
from audit_controls import native as audit
from finalization_controls import native as finalization


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def context(tmp_path):
    instruction=tmp_path/'instruction.md';instruction.write_text('Current scientific instruction '+('α\\"\t'*6000))
    source=tmp_path/'source.txt';source.write_text('Source evidence, not instructions.\n')
    system=tmp_path/'system.md';system.write_text('Persistent exact registered system.\n')
    output=tmp_path/'attempt'/'output';output.mkdir(parents=True)
    job={'id':'one','attempt_dir':str(output.parent),'output_dir':str(output),'audit_path':str(output/'audit.json'),
         'full_path':str(output/'full.yaml'),'core_path':str(output/'core.yaml'),'report_path':str(output/'report.md'),
         'instruction':str(instruction),'system_prompt':str(system),'readable_inputs':[str(instruction),str(source),str(system)]}
    manifest={'kind':'d4d_native_audit_continuation','inputs':{'bundle':str(source)},'job':job}
    recovery.prepare(manifest,tmp_path,True)
    manifest['pinned_files']={p:digest(p) for p in job['readable_inputs']}
    policy={'readonly_lookups':{'repository':str(tmp_path),'inputs':job['readable_inputs'],
            'bounded_reads':recovery.paths(manifest),'output_directories':[str(output)]}}
    return manifest,policy


def pair(manifest,*,identity='read-one',payload=None):
    descriptor=manifest['context_recovery']['documents']['instruction']['frames']
    payload=payload or {'file_path':descriptor['path'],'offset':1,'limit':min(12,descriptor['line_count'])}
    call={'type':'tool_use','id':identity,'name':'Read','input':payload}
    selected=Path(descriptor['path']).read_text().split('\n')[payload.get('offset',1)-1:payload.get('offset',1)-1+payload.get('limit',12)]
    result={'type':'tool_result','tool_use_id':identity,'content':'\n'.join(str(i)+'\t'+line for i,line in enumerate(selected,payload.get('offset',1)))}
    event={'type':'user','message':{'content':[result]},'tool_use_result':{'type':'text','file':{
        'filePath':descriptor['path'],'startLine':payload.get('offset',1),'numLines':len(selected),
        'totalLines':descriptor['line_count'],'content':'\n'.join(selected)}}}
    return call,event,result


@pytest.mark.parametrize('change',['missing_offset','missing_limit','whole','negative','bool_offset','bool_limit','too_large','middle','extra'])
def test_unprescribed_frame_reads_are_denied_without_disqualification(context,change):
    manifest,policy=context;call,event,result=pair(manifest);payload=call['input']
    if change=='missing_offset':payload.pop('offset')
    elif change=='missing_limit':payload.pop('limit')
    elif change=='whole':payload.pop('offset');payload.pop('limit')
    elif change=='negative':payload['offset']=-1
    elif change=='bool_offset':payload['offset']=True
    elif change=='bool_limit':payload['limit']=True
    elif change=='too_large':payload['limit']=1000
    elif change=='middle':payload['offset']=2
    else:payload['pages']='1'
    files=FileAccess(policy)
    assert files.classify('Read',payload)[0]=='not_prescribed'
    assert recovery.read_result(manifest,files,call,event,result) is None
    for history_type in (audit.AuditHistory,finalization.FinalizationHistory):
        history=history_type(manifest,'offline',policy)
        history.observe({'type':'assistant','message':{'content':[call]}})
        history.observe({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':call['id'],'is_error':True,'content':'Denied'}]}})
        assert history.problem is None and history.recovery_reads==[] and not history.pending


@pytest.mark.parametrize('history_type',[audit.AuditHistory,finalization.FinalizationHistory])
def test_both_histories_record_exact_read_without_claiming_whole_coverage(context,history_type):
    manifest,policy=context;call,event,result=pair(manifest)
    history=history_type(manifest,'offline',policy)
    history.observe({'type':'assistant','message':{'content':[call]}});history.observe(event)
    assert history.recovery_reads==[{'call_line':1,'result_line':2,'tool_use_id':call['id'],
        **recovery.read_result(manifest,FileAccess(policy),call,event,result)}]
    assert history.problem is None
    assert 'coverage' not in history.recovery_reads[0]
    # Compaction changes neither the original frames nor their byte identity;
    # this is a historical completed read, never proof of current-context coverage.
    history.observe({'type':'system','subtype':'compact_boundary'})
    assert len(history.recovery_reads)==1


@pytest.mark.parametrize('change',['raw','numbered','path','line_count','persisted','error','mutated_file'])
@pytest.mark.parametrize('history_type',[audit.AuditHistory,finalization.FinalizationHistory])
def test_both_histories_refuse_false_bounded_delivery(context,change,history_type):
    manifest,policy=context;call,event,result=pair(manifest)
    if change=='raw':event['tool_use_result']['file']['content']+='changed'
    elif change=='numbered':result['content']+='changed'
    elif change=='path':event['tool_use_result']['file']['filePath']+='other'
    elif change=='line_count':event['tool_use_result']['file']['numLines']=True
    elif change=='persisted':event['tool_use_result']={'persistedOutputPath':'/unregistered'};result['content']='<persisted-output>'
    elif change=='error':result['is_error']=True
    else:Path(call['input']['file_path']).write_text('changed')
    history=history_type(manifest,'offline',policy)
    history.observe({'type':'assistant','message':{'content':[call]}})
    with pytest.raises(BudgetStop,match='bounded context Read'):history.observe(event)
    assert history.problem is not None and history.recovery_reads==[]


def test_no_opt_in_keeps_ordinary_read_scope(context):
    manifest,policy=context
    policy['readonly_lookups'].pop('bounded_reads')
    payload={'file_path':next(iter(recovery.paths(manifest)))}
    assert FileAccess(policy).classify('Read',payload)[0]=='prescribed'
    manifest.pop('context_recovery')
    assert recovery.paths(manifest)=={}


def test_persistent_phase4_check_order_retains_conditional_repair_boundary(context):
    from finalization_controls.prepare import render_system
    manifest,_=context
    manifest['kind']='d4d_native_finalization'
    manifest['job'].update(derive_argv=['python','derive'],check_argv=[['python','check','0'],['python','check','1']])
    text=render_system(manifest)
    assert 'First closing check: python check 0' in text
    assert 'A successful first check ends checking.' in text
    assert 'Only if its result explicitly permits the one ordinary closing repair' in text
    assert 'second closing check: python check 1' in text
    assert 'Source/evidence failure is terminal. No further repair or check is permitted.' in text
    assert ' ; then ' not in text
