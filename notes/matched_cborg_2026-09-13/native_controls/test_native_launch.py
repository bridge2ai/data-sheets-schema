"""Exercise the launch identity and deadline using local synthetic processes."""
import os
import json
from contextlib import contextmanager
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from budgeted_cborg import BudgetStop
from run_native_canary import execute_child, sha, verified_executable


def executable(path, marker):
    path.write_text(f'#!/bin/sh\nif [ "$1" = "--version" ]; then echo same-version; else echo {marker}; fi\n')
    path.chmod(0o700)


def test_same_version_alias_retarget_cannot_change_launched_bytes(tmp_path):
    one=tmp_path/'one';two=tmp_path/'two';alias=tmp_path/'cli'
    executable(one,'one');executable(two,'two');alias.symlink_to(one)
    target=alias.resolve()
    overlay={'claude_executable':str(target),'pinned_files':{str(target):sha(target)}}
    alias.unlink();alias.symlink_to(two)
    assert subprocess.check_output([str(one),'--version'])==subprocess.check_output([str(alias),'--version'])
    assert subprocess.check_output([verified_executable(overlay)],text=True).strip()=='one'
    executable(one,'changed')
    with pytest.raises(BudgetStop,match='bytes differ'):
        verified_executable(overlay)


def test_unresolved_launch_alias_is_refused(tmp_path):
    target=tmp_path/'target';alias=tmp_path/'alias'
    executable(target,'one');alias.symlink_to(target)
    with pytest.raises(BudgetStop,match='resolved path'):
        verified_executable({'claude_executable':str(alias),'pinned_files':{str(target):sha(target)}})


def test_deadline_closes_admission_and_kills_child_before_proxy_cleanup(tmp_path):
    instruction=tmp_path/'input.txt';instruction.write_text('offline')
    pidfile=tmp_path/'pid'
    closed=[]
    proxy=SimpleNamespace(failed=threading.Event(),failure=None,close_admission=lambda:closed.append(time.monotonic()))
    code='import os,time,pathlib,signal;pathlib.Path("pid").write_text(str(os.getpid()));signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(30)'
    start=time.monotonic()
    with pytest.raises(BudgetStop,match='deadline elapsed'):
        execute_child([sys.executable,'-c',code],proxy=proxy,instruction=instruction,attempt=tmp_path,
            cwd=tmp_path,env=dict(os.environ),deadline_seconds=0.2,verify_launch=lambda:None)
    assert closed and time.monotonic()-start < 4
    with pytest.raises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)


def test_launch_verification_failure_never_starts_process(tmp_path):
    instruction=tmp_path/'input.txt';instruction.write_text('offline')
    proxy=SimpleNamespace(close_admission=lambda:None)
    def changed():raise BudgetStop('changed pin')
    with pytest.raises(BudgetStop,match='changed pin'):
        execute_child([sys.executable,'-c','open("should-not-exist","w").close()'],proxy=proxy,
            instruction=instruction,attempt=tmp_path,cwd=tmp_path,env=dict(os.environ),
            deadline_seconds=1,verify_launch=changed)
    assert not (tmp_path/'should-not-exist').exists()


@pytest.mark.parametrize('override, expected', [(None, '5'), (15, '15')])
@pytest.mark.parametrize('bypass', [False, True])
@pytest.mark.parametrize('render_version, binding', [(7, 'omitted'), (9, 'matched'),
                                                   (9, 'omitted'), (9, 'different')])
def test_native_cli_receives_the_same_attempt_cap_as_its_proxy(tmp_path, monkeypatch, override, expected,
                                                            render_version, binding, bypass):
    import anthropic
    import run_native_canary as runner

    job = {'id': 'external_native', 'canary': True, 'execution_arm': 'agentic',
           'render_spec': {}, 'input_identity': {}, 'output_directories': [], 'outputs': {}}
    instruction = tmp_path / 'instruction.md'
    instruction.write_text('Synthetic offline instruction')
    job['instruction'] = str(instruction)
    base = {'repository': str(tmp_path), 'claude_version': 'test-version',
            'provider_base_url': 'https://unused.invalid', 'model': {'model': 'test-model'},
            'budget': {'additional_usd': 200, 'per_attempt_usd': 5,
                       'ledger_path': str(tmp_path / 'billing.json'), 'prices_per_token': {}},
            'generation': {'jobs': [job], 'canary_order': [job['id']],
                           'agentic_attempt_deadline_seconds': 1}}
    if override is not None:
        base['budget']['per_job_attempt_usd'] = {job['id']: override}
    if bypass:
        base['provider_context_policy'] = 'headroom_bypass_v1'
    registration = tmp_path / 'registration.json'
    registration.write_text(json.dumps(base))
    overlay = tmp_path / 'overlay.json'
    environment = ({} if binding == 'omitted' else {'D4D_LAUNCH_INSTRUCTION':
                   str(instruction) if binding == 'matched' else str(tmp_path / 'another.md')})
    overlay.write_text(json.dumps({'registration': str(registration),
        'registration_sha256': sha(registration), 'allowed_jobs': [job['id']],
        'pinned_files': {}, 'environment': {}, 'per_job_environment': {job['id']: environment},
        'cli_flags': [], 'allowed_tools': ['Read'], 'system_prompt': str(instruction)}))
    review = tmp_path / 'review.json'
    review.write_text(json.dumps({'verdict': 'approve', 'ci_conclusion': 'success',
        'overlay_sha256': sha(overlay), 'allowed_jobs': [job['id']]}))
    observed = {}

    class OfflineProxy:
        token = 'synthetic-local-token'
        unfinished_handlers = 0
        failed = threading.Event()

        def __init__(self, **kwargs):
            observed['proxy_cap'] = str(kwargs['ledger'].limit_for_attempt(kwargs['attempt']))
            assert kwargs['request_headers'] == ({'x-headroom-bypass': 'true'} if bypass else {})

        @contextmanager
        def running(self):
            yield 'http://127.0.0.1:1'

    def capture(argv, **kwargs):
        observed['cli_cap'] = argv[argv.index('--max-budget-usd') + 1]
        if render_version >= 9:
            assert kwargs['env']['D4D_LAUNCH_INSTRUCTION'] == str(instruction)
        raise BudgetStop('synthetic probe stops before process or provider execution')

    monkeypatch.setattr(runner, 'verify', lambda *args: None)
    monkeypatch.setattr(runner, 'verify_history', lambda *args: None)
    monkeypatch.setattr(runner, 'verified_executable', lambda *args: sys.executable)
    monkeypatch.setattr(runner.subprocess, 'check_output', lambda *args, **kwargs: 'test-version')
    monkeypatch.setattr(runner, 'spec_for', lambda *args: SimpleNamespace(
        render_spec=lambda: {}, input_identity=lambda: {}, render_version=render_version))
    def sdk(**kwargs):
        assert kwargs['default_headers'] == ({'x-headroom-bypass': 'true'} if bypass else {})
        return object()
    monkeypatch.setattr(anthropic, 'Anthropic', sdk)
    monkeypatch.setattr(runner, 'NativeProxy', OfflineProxy)
    monkeypatch.setattr(runner, 'execute_child', capture)
    monkeypatch.setenv('CBORG_API_KEY', 'synthetic-never-sent')
    monkeypatch.setattr(sys, 'argv', ['run_native_canary', '--overlay', str(overlay),
                                    '--review', str(review), '--job', job['id']])
    if render_version >= 9 and binding != 'matched':
        with pytest.raises(BudgetStop, match='exact registered launch instruction'):
            runner.main()
        assert observed == {}
        assert not (tmp_path / 'billing.json').exists()
        return
    assert runner.main() == 1
    assert observed == {'proxy_cap': expected, 'cli_cap': expected}
    receipt = json.loads((tmp_path/'attempts'/job['id']/'started.json').read_bytes())
    assert receipt['provider_context']['requested_headers'] == ({'x-headroom-bypass': 'true'} if bypass else {})
    assert receipt['provider_context']['provider_behavior_independently_observed'] is False


def test_stop_explanation_prefers_the_ledger_then_the_controller_then_the_proxy(tmp_path):
    """#1914: the v10q receipt said PermissionError and nothing else while the
    ledger held the cause. The ledger's stop entry for this attempt wins;
    a BudgetStop the controller raised is next; the proxy's recorded failure
    is last; a bare exception with none of them explains nothing."""
    from run_native_canary import stop_explanation
    ledger = tmp_path / 'billing.json'
    ledger.write_text(json.dumps({'requests': [], 'stopped_attempts': {'reg:job': {'reason': 'request reserve $2.30 exceeds remaining budget', 'paid_request': False}}}))
    out = stop_explanation(PermissionError('x'), ledger, 'reg:job', 'PermissionError')
    assert out['reason'].startswith('request reserve') and out['reason_source'] == 'ledger' and out['ledger_stop']['paid_request'] is False
    assert out['proxy_failure'] == 'PermissionError'
    out = stop_explanation(BudgetStop('deadline elapsed'), ledger, 'reg:other', None)
    assert out == {'reason': 'deadline elapsed', 'reason_source': 'controller'}
    out = stop_explanation(RuntimeError('boom'), ledger, 'reg:other', 'OSError')
    assert out == {'reason': 'OSError', 'reason_source': 'proxy', 'proxy_failure': 'OSError'}
    out = stop_explanation(RuntimeError('boom'), tmp_path / 'missing.json', 'reg:other', None)
    assert out == {}


def prescribed_playbook_commands(text):
    """Every `d4d <group> <command>[ <subcommand>]` the playbook text names —
    fenced or inline, with or without `poetry run` — as the roster spells
    them (`api prompts check` keeps its third token)."""
    import re
    found = set()
    for m in re.finditer(r'(?<![\w/.-])d4d\s+([a-z][a-z-]*)\s+([a-z][a-z-]*)(?:\s+([a-z][a-z-]*))?', text):
        group, command, sub = m.group(1), m.group(2), m.group(3)
        if command.startswith('-'):
            continue
        found.add(f'{group} {command} {sub}' if group == 'api' and command == 'prompts' and sub else f'{group} {command}')
    return found


def test_every_command_the_playbook_prescribes_is_allowed():
    """#1916/#1927: the v10q run lacked `prompt render`, which the playbook
    prescribes; the roster must cover every command the whole playbook names
    (inline text too, since the receipts-check gate is inline), except the
    ones the playbook mentions only to forbid."""
    from prepare_overlay_roster import PLAYBOOK_COMMANDS, MENTIONED_NOT_PRESCRIBED
    playbook = Path(__file__).resolve().parents[3] / '.claude/commands/d4d-full-core.md'
    prescribed = prescribed_playbook_commands(playbook.read_text(encoding='utf-8'))
    for expected in ('receipts check', 'bundle chunk', 'runs validate', 'download list-projects',
                     'api prompts check', 'prompt render', 'provenance record', 'derive core'):
        assert expected in prescribed, f'extraction lost {expected}'
    missing = sorted(p for p in prescribed - set(MENTIONED_NOT_PRESCRIBED) if p not in PLAYBOOK_COMMANDS)
    assert missing == [], f'playbook commands the overlay does not allow: {missing}'
    assert 'provenance backfill' not in PLAYBOOK_COMMANDS


def test_the_extractor_reads_inline_fenced_and_nested_forms():
    text = ("Run `poetry run d4d receipts check --label X --strict` first.\n```bash\nd4d bundle chunk --check\n"
            "d4d api prompts check --strict\n```\nNever `d4d provenance backfill` here. See d4d-agent.md and /d4d-full-core.")
    assert prescribed_playbook_commands(text) == {'receipts check', 'bundle chunk', 'api prompts check', 'provenance backfill'}


def test_the_instruction_module_entry_points_are_allowed():
    """#1923: renderer 12 prescribes source_review before audit and report."""
    from prepare_overlay_roster import MODULE_ENTRY_POINTS
    assert {'source_review', 'evidence_assertions', 'agentic_observed', 'd4d_pair_consistency'} <= set(MODULE_ENTRY_POINTS)


def test_stop_explanation_never_raises_on_a_malformed_ledger(tmp_path):
    """#1925: a diagnostic that fails must not displace the stop it explains."""
    from run_native_canary import stop_explanation
    ledger = tmp_path / 'billing.json'
    ledger.write_text(json.dumps({'requests': [], 'stopped_attempts': ['bad']}))
    out = stop_explanation(PermissionError('x'), ledger, 'reg:job', 'PermissionError')
    assert out['reason'] == 'PermissionError' and out['reason_source'] == 'proxy' and 'ledger_stop_note' in out
    ledger.write_bytes(b'{not json')
    out = stop_explanation(BudgetStop('deadline'), ledger, 'reg:job', None)
    assert out['reason'] == 'deadline' and out['ledger_stop_note'].startswith('ledger unreadable')


def test_a_malformed_observation_refuses_completion():
    """#1930: the observer's malformed-event count must reach the completion
    decision, not only the receipt's observation block."""
    from run_native_canary import observation_problems
    assert observation_problems({'output_tokens': 5, 'usage_from_terminal_result': 1}) == []
    assert observation_problems({'malformed_message_events': 2, 'usage_from_terminal_result': 1}) == ['transcript carries 2 malformed measurement events']
    assert observation_problems({'overlapping_evidence': 1, 'usage_from_terminal_result': 1}) == ['transcript carries 1 overlapping evidence events (#1972)']
    assert observation_problems({'output_tokens': 3}) == ['transcript carries no terminal result with complete usage']
    assert observation_problems({'output_tokens': 3, 'usage_from_terminal_result': 1}) == []
    assert observation_problems(None) == ['transcript observation unavailable']


def test_a_stopped_attempt_records_whether_the_transcript_reached_its_result(tmp_path):
    """#2014: a deadline stop leaves no runtime result line; the receipt says so."""
    from run_native_canary import transcript_terminal_state
    t = tmp_path / 'transcript.jsonl'
    t.write_text('{"type":"system","subtype":"init"}\n{"type":"assistant","message":{"id":"m1"}}\n')
    state = transcript_terminal_state(t)
    assert state['transcript_terminal_result'] == 'absent' and 'ledger' in state['transcript_accounting_note']
    t.write_text(t.read_text() + '{"type":"result","usage":{"input_tokens":1,"output_tokens":1}}\n')
    assert transcript_terminal_state(t) == {'transcript_terminal_result': 'present'}
    assert transcript_terminal_state(tmp_path / 'missing.jsonl')['transcript_terminal_result'] == 'missing'


def test_the_attempt_deadline_is_a_registration_parameter():
    """#2010/#2020/#2021: the deadline is parsed as a positive whole number,
    defaults to what v10q and v10r registered, and is what the generation
    block records."""
    import pytest
    from types import SimpleNamespace
    import prepare_registration as prep
    parser = prep.build_parser()
    assert parser.parse_args([]).agentic_deadline_seconds == 1800
    explicit = parser.parse_args(['--agentic-deadline-seconds', '10800'])
    assert explicit.agentic_deadline_seconds == 10800 and isinstance(explicit.agentic_deadline_seconds, int)
    for bad in ('0', '-1', '1.5', 'soon'):
        with pytest.raises(SystemExit):
            parser.parse_args(['--agentic-deadline-seconds', bad])
    assert prep.generation_deadline(SimpleNamespace(agentic_deadline_seconds=10800)) == 10800
    import inspect
    assert '"agentic_attempt_deadline_seconds": generation_deadline(args)' in inspect.getsource(prep.main)


def test_the_transcript_diagnostic_never_raises(tmp_path):
    """#2019: undecodable bytes and a missing file are reported, not raised."""
    from run_native_canary import transcript_terminal_state
    t = tmp_path / 'transcript.jsonl'
    t.write_bytes(b'{"type":"system"}\n\xff\xfe\x80 cut mid-write')
    assert transcript_terminal_state(t)['transcript_terminal_result'] == 'absent'
    t.write_bytes(b'\xff\n{"type":"result","usage":{"input_tokens":1,"output_tokens":1}}\n')
    assert transcript_terminal_state(t) == {'transcript_terminal_result': 'present'}
    assert transcript_terminal_state(tmp_path / 'none.jsonl')['transcript_terminal_result'] == 'missing'
    assert transcript_terminal_state(tmp_path)['transcript_terminal_result'] == 'unreadable'


def test_a_controller_stop_is_recorded_in_the_ledger(tmp_path):
    """#2018: a deadline stop marks the attempt stopped in the ledger; a
    ledger stop is left as the ledger recorded it."""
    from run_native_canary import record_controller_stop
    from budgeted_cborg import Ledger
    ledger = Ledger(tmp_path / 'billing.json', manifest_sha256='m', total_cap=200, attempt_cap=5)
    out = record_controller_stop(ledger, 'm:job', {'reason': 'native attempt deadline elapsed', 'reason_source': 'controller'})
    state = json.loads((tmp_path / 'billing.json').read_bytes())
    assert state['stopped_attempts']['m:job']['reason'] == 'controller: native attempt deadline elapsed'
    assert out == {'ledger_stop_recorded': 'controller: native attempt deadline elapsed'}
    assert record_controller_stop(ledger, 'm:job', {'reason': 'x', 'reason_source': 'ledger'}) == {}
    class Broken:
        def stop_attempt(self, *a): raise OSError('disk')
    assert 'could not record' in record_controller_stop(Broken(), 'm:other', {'reason': 'x'})['ledger_stop_record_note']
