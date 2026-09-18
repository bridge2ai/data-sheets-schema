"""A real local child exercises the phase observer before tool execution."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shlex
import sys
import threading
from types import SimpleNamespace

import pytest

from budgeted_cborg import BudgetStop
from native_control import CONTRACT
from run_native_canary import execute_child
from tests.test_evidence_generation_gate import specification


CHILD = r'''
import json, os, sys
from pathlib import Path
def send(value): print(json.dumps(value), flush=True)
init = json.loads(sys.stdin.readline())
send({'type':'control_response','response':{'subtype':'success','request_id':init['request_id']}})
json.loads(sys.stdin.readline())
for n, row in enumerate(json.loads(Path('steps.json').read_text())):
    identity = f'tool-{n}'
    tool = row.get('tool', 'Bash')
    inputs = row['input']
    send({'type':'assistant','message':{'content':[{'type':'tool_use','id':identity,'name':tool,'input':inputs}]}})
    send({'type':'control_request','request_id':f'callback-{n}','request':{
        'subtype':'hook_callback','callback_id':'d4d_tool_policy_v2','input':{
        'hook_event_name':'PreToolUse','tool_name':tool,'tool_use_id':identity,
        'cwd':os.getcwd(),'tool_input':inputs}}})
    reply = json.loads(sys.stdin.readline())
    assert not reply['response']['response']
    if row.get('marker'): Path(row['marker']).write_text('executed')
    if tool == 'Write': Path(inputs['file_path']).write_text(inputs['content'])
    send({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':identity,
        'is_error':row.get('error',False),'content':'synthetic checker result'}]}})
send({'type':'result'})
'''


@pytest.mark.parametrize('scenario', ['correct_phase1', 'early_derive', 'terminal_evidence'])
def test_controller_distinguishes_draft_correction_from_terminal_failure(tmp_path, monkeypatch, scenario):
    import run_native_canary as runner
    spec = replace(specification(tmp_path, 'Claude Code'), render_version=13)
    spec.full_path.parent.mkdir(parents=True, exist_ok=True)
    paths = spec._agentic_artifact_paths
    python = spec._agentic_toolchain['python']
    def cli(*args):
        return shlex.join([python, '-m', 'data_sheets_schema.cli', *map(str, args)])
    receipt = cli('--manifest', 'none', 'receipts', 'check', '--method', spec.method,
                  '--label', spec.label, '--project', spec.project, '--bundle', spec.bundle,
                  '--chunk-manifest', spec.chunk_manifest, '--strict')
    derive = cli('derive', 'core', '--full', paths['full'], '--out', paths['core'])
    marker = tmp_path / 'phase2-executed'
    steps = [
        {'input': {'command': receipt}, 'error': True},
        {'tool': 'Write', 'input': {'file_path': paths['receipt'], 'content': 'corrected draft'}},
        {'input': {'command': receipt}},
        {'input': {'command': derive}, 'marker': str(marker)},
    ]
    expected = None
    if scenario == 'early_derive':
        steps = [steps[-1]]
        expected = 'core derivation precedes a passing receipt'
    elif scenario == 'terminal_evidence':
        evidence = spec.metadata_dir / 'evidence'
        command = shlex.join([python, '-m', 'data_sheets_schema.evidence_assertions',
            '--audit', str(evidence / 'audit.json'), '--bundle', str(spec.bundle),
            '--manifest', str(spec.chunk_manifest), '--original-full', str(evidence / 'original_full.yaml'),
            '--original-core', str(evidence / 'original_core.yaml'), '--protocol-version', '3'])
        steps.extend([{'input': {'command': command}, 'error': True},
                      {'input': {'command': receipt}, 'marker': str(tmp_path / 'continued-after-failure')}])
        expected = 'terminal evidence check failed'
    (tmp_path / 'steps.json').write_text(json.dumps(steps))
    instruction = tmp_path / 'instruction'; instruction.write_text('synthetic input')
    policy = {'python': python, 'programs': [], 'manifest_paths': ['none'],
              'readonly_lookups': {'repository': str(tmp_path), 'inputs': [],
                                   'output_directories': [str(spec.full_path.parent)]},
              'pretool_control': deepcopy(CONTRACT)}
    # Permission classification is tested separately. Here every named tool is
    # admitted by it, so only the real phase observer can prevent execution.
    monkeypatch.setattr(runner, '_classify_command', lambda *a: ('prescribed', 'synthetic helper'))
    closed, stops = [], []
    proxy = SimpleNamespace(failed=threading.Event(), failure=None,
                            close_admission=lambda: closed.append(True))
    def launch():
        return execute_child([sys.executable, '-c', CHILD, '--input-format', 'stream-json'],
            proxy=proxy, instruction=instruction, attempt=tmp_path, cwd=tmp_path, env={},
            deadline_seconds=4, verify_launch=lambda: None, command_policy=policy,
            phase_spec=spec, record_stop=stops.append)
    if expected:
        with pytest.raises(BudgetStop, match=expected):
            launch()
        assert stops and expected in stops[0]
    else:
        assert launch() == 0 and not stops
    assert closed
    assert marker.exists() is (scenario != 'early_derive')
    assert not (tmp_path / 'continued-after-failure').exists()
    assert (tmp_path / 'transcript.jsonl').stat().st_size


@pytest.mark.parametrize('form', ['help', 'compound', 'wrong_manifest', 'evidence_help', 'derive_help'])
def test_denied_helper_does_not_become_a_terminal_phase_failure(tmp_path, form):
    from test_native_control import CHILD as denied_child
    from run_native_canary import _classify_command
    from native_phase_history import phase_history
    spec = replace(specification(tmp_path, 'Claude Code'), render_version=13)
    python = spec._agentic_toolchain['python']
    command = shlex.join([python, '-m', 'data_sheets_schema.cli', '--manifest', 'none',
                         'receipts', 'check', '--help'])
    if form == 'compound':
        command = command.replace(' --help', '') + '; true'
    elif form == 'wrong_manifest':
        command = command.replace('--manifest none', '--manifest another.yaml').replace(' --help', '')
    elif form == 'evidence_help':
        command = shlex.join([python, '-m', 'data_sheets_schema.evidence_assertions', '--help'])
    elif form == 'derive_help':
        command = shlex.join([python, '-m', 'data_sheets_schema.cli', 'derive', 'core', '--help'])
    policy = {'python': python, 'programs': [], 'manifest_paths': ['none'],
              'readonly_lookups': {'repository': str(tmp_path), 'inputs': [], 'output_directories': []},
              'pretool_control': deepcopy(CONTRACT)}
    assert _classify_command(command, python, set(), policy)[0] == 'not_prescribed'
    (tmp_path / 'case.json').write_text(json.dumps({'command': command}))
    instruction = tmp_path / 'instruction'; instruction.write_text('synthetic input')
    stops = []
    proxy = SimpleNamespace(failed=threading.Event(), failure=None, close_admission=lambda: None)
    code = execute_child([sys.executable, '-c', denied_child, '--input-format', 'stream-json'],
        proxy=proxy, instruction=instruction, attempt=tmp_path, cwd=tmp_path, env={},
        deadline_seconds=4, verify_launch=lambda: None, command_policy=policy,
        phase_spec=spec, record_stop=stops.append)
    assert code == 0 and stops == []
    events = [json.loads(line) for line in (tmp_path / 'transcript.jsonl').read_text().splitlines()]
    terminal = next(event for event in events if event.get('type') == 'result')
    assert len(terminal['permission_denials']) == 1
    assert phase_history(events, spec, repository=tmp_path, command_policy=policy)['problems'] == []
