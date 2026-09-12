"""Preserve exact-file validation while supporting its literal exit-status echo."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import reference_rescore_cborg as c
import reference_rescore_cborg_validator_status as status

RUBRIC='rubric20-semantic'
COMMAND='poetry run python scripts/validate_evaluation_schema.py --file output_evaluation.json --rubric '+RUBRIC


def trace(command=COMMAND+'; echo "EXIT=$?"', result='VALID output_evaluation.json: '+RUBRIC+'\nEXIT=0'):
    return [
        {'type':'system','subtype':'init','cwd':'/isolated'},
        {'type':'assistant','message':{'content':[{'type':'tool_use','id':'write','name':'Write','input':{'file_path':'/isolated/output_evaluation.json','content':'{}'}}]}},
        {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'write','content':'written'}]}},
        {'type':'assistant','message':{'content':[{'type':'tool_use','id':'validate','name':'Bash','input':{'command':command}}]}},
        {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'validate','is_error':False,'content':result}]}},
        {'type':'result','subtype':'success','is_error':False,'permission_denials':[]},
    ]


def test_literal_successful_status_echo_preserves_original_trace():
    runner=c.load_runner();events=trace();original=copy.deepcopy(events)
    assert not runner.evaluator_validated(events,RUBRIC)
    status.enable(runner)
    assert runner.evaluator_validated(events,RUBRIC)
    assert events==original
    assert status.proven_status_calls(runner,events,RUBRIC)[0]['exit_status']==0


@pytest.mark.parametrize('name',['EXIT','exit'])
def test_absolute_paths_and_both_registered_status_spellings(name):
    command=COMMAND.replace('scripts/','/isolated/scripts/').replace('--file output_','--file /isolated/output_')
    events=trace(command+f'; echo "{name}=$?"',f'VALID /isolated/output_evaluation.json: {RUBRIC}\n{name}=0')
    runner=c.load_runner();status.enable(runner)
    assert runner.evaluator_validated(events,RUBRIC)


@pytest.mark.parametrize('change',[
    'missing_status','nonzero_status','wrong_file','wrong_rubric','spoof_zero','extra_command',
    'missing_marker','error_result','sandbox_override','duplicate_result','late_mutation','terminal_denial',
])
def test_incomplete_ambiguous_or_mutating_evidence_cannot_pass(change):
    events=trace();call=events[3]['message']['content'][0];result=events[4]['message']['content'][0]
    if change=='missing_status':result['content']=f'VALID output_evaluation.json: {RUBRIC}'
    elif change=='nonzero_status':result['content']=f'VALID output_evaluation.json: {RUBRIC}\nEXIT=1'
    elif change=='wrong_file':call['input']['command']=call['input']['command'].replace('output_evaluation.json','other.json')
    elif change=='wrong_rubric':call['input']['command']=call['input']['command'].replace(RUBRIC,'rubric10-semantic')
    elif change=='spoof_zero':call['input']['command']=COMMAND+'; echo "EXIT=0"'
    elif change=='extra_command':call['input']['command']+='; touch changed'
    elif change=='missing_marker':result['content']='INVALID output_evaluation.json: '+RUBRIC+'\nEXIT=0'
    elif change=='error_result':result['is_error']=True
    elif change=='sandbox_override':call['input']['dangerouslyDisableSandbox']=True
    elif change=='duplicate_result':events.insert(5,copy.deepcopy(events[4]))
    elif change=='late_mutation':
        use=copy.deepcopy(events[1]);use['message']['content'][0]['id']='later'
        answer=copy.deepcopy(events[2]);answer['message']['content'][0]['tool_use_id']='later'
        events[-1:-1]=[use,answer]
    elif change=='terminal_denial':events[-1]['permission_denials']=[{'tool_use_id':'validate','tool_name':'Bash','tool_input':copy.deepcopy(call['input'])}]
    runner=c.load_runner();status.enable(runner)
    assert not runner.evaluator_validated(events,RUBRIC)


def test_canonical_validation_still_passes_and_recovery_is_not_invented():
    runner=c.load_runner();status.enable(runner)
    assert runner.evaluator_validated(trace(COMMAND,f'VALID output_evaluation.json: {RUBRIC}'),RUBRIC)
    events=trace();events[4]['message']['content'][0].update(is_error=True,content="Permission to use Bash has been denied because Claude Code is running in don't ask mode.")
    events[-1]['permission_denials']=[{'tool_use_id':'validate','tool_name':'Bash','tool_input':copy.deepcopy(events[3]['message']['content'][0]['input'])}]
    assert not runner.evaluator_validated(events,RUBRIC)


def test_router_adds_only_exact_status_permissions_without_mutating_argv():
    args=['--print','--tools','Read,Write,Bash','--allowedTools','Read','Write','Bash(validator:*)','--system-prompt','unchanged definition']
    original=args[:];routed=status.route_args(args)
    assert args==original
    assert [x for x in routed if x not in args]==list(status.PERMISSION_RULES)
    assert 'Bash(echo:*)' not in routed
    assert routed[-2:]==args[-2:]
    with pytest.raises(ValueError):status.route_args(['--print'])
