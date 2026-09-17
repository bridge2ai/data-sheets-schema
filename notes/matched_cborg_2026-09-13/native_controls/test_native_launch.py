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
    is last. A BudgetStop carrying the proxy's recorded failure is the
    proxy's, and a bare exception with none of them is named by its type
    (#2038)."""
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
    assert out == {'reason': 'unexpected RuntimeError', 'reason_source': 'controller'}
    out = stop_explanation(BudgetStop('unregistered upstream response format'), tmp_path / 'missing.json', 'reg:other',
                           'unregistered upstream response format')
    assert out['reason_source'] == 'proxy' and out['reason'] == 'unregistered upstream response format'
    out = stop_explanation(BudgetStop('native attempt deadline elapsed'), tmp_path / 'missing.json', 'reg:other', 'OSError')
    assert out['reason_source'] == 'controller' and out['proxy_failure'] == 'OSError'


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
    """#2018/#2023: a deadline stop marks the attempt stopped in the ledger; a
    ledger stop is left as the ledger recorded it; an entry the ledger already
    holds is reported, not overwritten."""
    from run_native_canary import record_controller_stop
    from budgeted_cborg import Ledger
    ledger = Ledger(tmp_path / 'billing.json', manifest_sha256='m', total_cap=200, attempt_cap=5)
    out = record_controller_stop(ledger, 'm:job', {'reason': 'native attempt deadline elapsed', 'reason_source': 'controller'})
    state = json.loads((tmp_path / 'billing.json').read_bytes())
    assert state['stopped_attempts']['m:job']['reason'] == 'controller: native attempt deadline elapsed'
    assert out == {'ledger_stop_recorded': 'controller: native attempt deadline elapsed'}
    # recording again (the except path after a pre-close record) is idempotent
    assert record_controller_stop(ledger, 'm:job', {'reason': 'native attempt deadline elapsed'}) == out
    assert record_controller_stop(ledger, 'm:job', {'reason': 'x', 'reason_source': 'ledger'}) == {}
    ledger.stop_attempt('m:other', 'attempt cap reached')
    note = record_controller_stop(ledger, 'm:other', {'reason': 'native attempt deadline elapsed'})
    assert note == {'ledger_stop_record_note': 'the ledger already held a stop entry: attempt cap reached'}
    class Broken:
        path = tmp_path / 'none.json'
        def stop_attempt(self, *a): raise OSError('disk')
    assert 'could not record' in record_controller_stop(Broken(), 'm:x', {'reason': 'x'})['ledger_stop_record_note']


def _deadline_while_counting(tmp_path, *, record_first):
    """The real NativeProxy.running() and execute_child: the deadline fires
    while a /v1/messages handler is still counting tokens, so the handler
    meets the admission the controller has just closed (#2023/#2024)."""
    import threading, time
    from types import SimpleNamespace
    from test_native_proxy import fixture_proxy, REQUEST
    import run_native_canary as rnc
    proxy, ledger, calls = fixture_proxy(tmp_path)
    counting = threading.Event()
    def count(**kw):
        counting.set()
        while not proxy.closed:
            time.sleep(0.01)
        time.sleep(0.2)   # returns inside running()'s cleanup window
        return SimpleNamespace(input_tokens=100)
    proxy.messages.client.messages.count_tokens = count
    at_close = {}
    original_close = proxy.close_admission
    def close_and_snapshot():
        # What the ledger holds at the moment admission first closes (#2029).
        if 'stops' not in at_close:
            at_close['stops'] = json.loads(ledger.path.read_bytes()).get('stopped_attempts') if ledger.path.exists() else None
        original_close()
    proxy.close_admission = close_and_snapshot
    attempt = tmp_path / 'attempt'; attempt.mkdir()
    instruction = tmp_path / 'instruction.txt'; instruction.write_text('offline')
    child = ("import json,os,time,urllib.request\n"
             "req=urllib.request.Request(os.environ['URL']+'/v1/messages?beta=true',data=json.dumps(%r).encode(),"
             "headers={'x-api-key':os.environ['TOKEN'],'content-type':'application/json'})\n"
             "print(json.dumps({'type':'system','subtype':'init'}),flush=True)\n"
             "try:\n urllib.request.urlopen(req,timeout=30)\nexcept Exception: pass\n"
             "time.sleep(30)\n") % (REQUEST,)
    record = (lambda reason: rnc.record_controller_stop(ledger, 'native-offline', {'reason': reason})) if record_first else None
    receipt = {}
    try:
        with proxy.running() as url:
            env = dict(os.environ, URL=url, TOKEN=proxy.token)
            rnc.execute_child([sys.executable, '-c', child], proxy=proxy, instruction=instruction, attempt=attempt,
                              cwd=tmp_path, env=env, deadline_seconds=1.0, verify_launch=lambda: None, record_stop=record)
    except Exception as exc:
        receipt.update(status='stopped', error_type=type(exc).__name__)
        receipt.update(rnc.stop_explanation(exc, ledger.path, 'native-offline', getattr(proxy, 'failure', None)))
        receipt.update(rnc.transcript_terminal_state(attempt / 'transcript.jsonl'))
        receipt.update(rnc.record_controller_stop(ledger, 'native-offline', receipt))
    assert counting.is_set() and calls == []
    receipt['stops_at_close'] = at_close.get('stops')
    return receipt, json.loads(ledger.path.read_bytes()).get('stopped_attempts')


def test_a_deadline_during_an_in_flight_request_is_recorded_as_the_deadline(tmp_path):
    receipt, stops = _deadline_while_counting(tmp_path, record_first=True)
    assert receipt['status'] == 'stopped' and receipt['reason_source'] == 'controller'
    assert receipt['reason'].startswith('native attempt deadline elapsed')
    assert stops['native-offline']['reason'].startswith('controller: native attempt deadline elapsed')
    assert receipt['ledger_stop_recorded'] == stops['native-offline']['reason']
    # the deadline was already in the ledger when admission closed (#2029)
    assert receipt['stops_at_close']['native-offline']['reason'].startswith('controller: native attempt deadline elapsed')


def test_the_admission_closed_consequence_never_masks_a_controller_stop(tmp_path):
    """Even when the pre-close record did not happen, the entry the refused
    handler wrote is reported as a consequence, not as the cause."""
    receipt, stops = _deadline_while_counting(tmp_path, record_first=False)
    assert stops['native-offline']['reason'] == 'native admission is closed'
    assert receipt['reason_source'] == 'controller' and receipt['reason'].startswith('native attempt deadline elapsed')
    assert 'consequence' not in receipt['reason'] and 'refused after the controller closed admission' in receipt['ledger_stop_note']
    assert receipt['ledger_stop_record_note'] == 'the ledger already held a stop entry: native admission is closed'


PY = '/opt/env/bin/python'
SNAPSHOT = ("from pathlib import Path\nimport hashlib, json\npairs = [('out/full.yaml', 'out/evidence/original_full.yaml')]\n"
            "pins = {}\nfor src, dst in pairs:\n    raw = Path(src).read_bytes()\n    pins[dst] = hashlib.sha256(raw).hexdigest()\n"
            "print(json.dumps({'original_sha256': pins}, sort_keys=True))\n")
VALIDATE = 'from linkml.validator.cli import cli; cli()'


def _instruction():
    import shlex
    return (f"VALIDATE both files:\n\n    {PY} -c '{VALIDATE}' -s /repo/schema_all.yaml -C Dataset <full>\n\n"
            f"Freeze the originals:\n\n{PY} -c {shlex.quote(SNAPSHOT)}\n\nThen run {PY} -m data_sheets_schema.cli derive core --full x\n")


def _classify(*denials):
    from run_native_canary import classify_denials
    return classify_denials(list(denials), instruction_text=_instruction(), python=PY, repository='/repo',
                            output_directories=['out', 'out_core'], readable_inputs=['data/bundle.txt', 'data/chunks.yaml'])


def _bash(command):
    return {'tool_name': 'Bash', 'tool_use_id': 't', 'tool_input': {'command': command, 'description': 'x'}}


def test_the_instruction_programs_are_read_verbatim_including_the_multi_line_one():
    from run_native_canary import prescribed_programs
    assert prescribed_programs(_instruction(), PY) == {VALIDATE, SNAPSHOT.strip()}


def test_denials_of_forbidden_commands_are_listed_and_not_disqualifying():
    """#2026: the shapes the v10q and v10r runs were denied, all forbidden by the system prompt."""
    import shlex
    from run_native_canary import denial_problems
    forbidden = [
        _bash(f'{PY} -m data_sheets_schema.cli --help 2>&1 | head -60'),
        _bash(f'{PY} -m data_sheets_schema.cli --help'),
        _bash(f'{PY} -m data_sheets_schema.cli schema --help'),
        _bash(f'{PY} -m data_sheets_schema.cli agents digest 2>&1 | head -30'),
        _bash(f"{PY} - <<'PY' > /tmp/digest.txt\nprint(1)\nPY"),
        _bash(f'{PY} -c {shlex.quote("import sys; print(sys.argv)")}'),
        _bash("cat >> out/receipt.yaml <<'EOF'\n- id: c002\nEOF"),
        _bash('grep -o "python -c" /repo/cli_config/projects/session.jsonl'),
        _bash('grep -n "Leadership" data/bundle.txt | head -20; grep -n "Cohort" data/bundle.txt'),
        {'tool_name': 'Write', 'tool_use_id': 'w', 'tool_input': {'file_path': '/tmp/scratch/digest.py', 'content': 'x'}},
        {'tool_name': 'WebFetch', 'tool_use_id': 'f', 'tool_input': {'url': 'https://example.org'}},
    ]
    classified = _classify(*forbidden)
    assert [d['classification'] for d in classified] == ['not_prescribed'] * len(forbidden)
    assert all(d['basis'] for d in classified) and denial_problems(classified) == []


def test_a_denied_prescribed_command_disqualifies():
    import shlex
    from run_native_canary import denial_problems
    prescribed = [
        _bash(f'{PY} -m data_sheets_schema.cli receipts check --label L --project P --strict'),
        _bash(f'{PY} -m data_sheets_schema.cli --manifest /repo/manifest.yaml download priority --project P'),
        _bash(f'{PY} -m data_sheets_schema.agentic_observed --bundle data/bundle.txt t.jsonl'),
        _bash(f"{PY} -c '{VALIDATE}' -s /repo/schema_all.yaml -C Dataset out/full.yaml"),
        _bash(f'{PY} -c {shlex.quote(SNAPSHOT)}'),
        {'tool_name': 'Write', 'tool_use_id': 'w', 'tool_input': {'file_path': '/repo/out/full.yaml', 'content': 'x'}},
        {'tool_name': 'Read', 'tool_use_id': 'r', 'tool_input': {'file_path': 'data/bundle.txt'}},
    ]
    classified = _classify(*prescribed)
    assert [d['classification'] for d in classified] == ['prescribed'] * len(prescribed), classified
    assert len(denial_problems(classified)) == len(prescribed)
    # a roster command whose form the system prompt forbids is not the prescribed command
    assert _classify(_bash(f'{PY} -m data_sheets_schema.cli receipts check --label L; ls'))[0]['classification'] == 'not_prescribed'
    # a command outside the roster, and the mentioned-not-prescribed backfill, are not prescribed
    assert _classify(_bash(f'{PY} -m data_sheets_schema.cli provenance backfill --label L'))[0]['classification'] == 'not_prescribed'


def test_an_unreadable_denial_record_disqualifies():
    from run_native_canary import classify_denials, denial_problems
    kw = dict(instruction_text='', python=PY, repository='/repo', output_directories=[], readable_inputs=[])
    assert classify_denials(None, **kw) == [] and classify_denials([], **kw) == []
    odd = classify_denials({'tool_name': 'Bash'}, **kw)
    assert odd[0]['classification'] == 'unclassifiable' and denial_problems(odd)
    assert classify_denials(['Bash'], **kw)[0]['classification'] == 'unclassifiable'


ROSTER = f'{PY} -m data_sheets_schema.cli'


def test_commands_bash_would_split_or_redirect_are_not_the_prescribed_command():
    """#2031: shlex reads a newline as whitespace, merges operator runs into
    one token and treats a `#` inside a word as a comment. Bash reads each of
    these as a second command, a redirection or a substitution."""
    from run_native_canary import FORBIDDEN_SHELL, denial_problems
    shapes = [
        f'{ROSTER} runs list\nrm -rf data/d4d_concatenated',
        f'{ROSTER} derive core --full a --out b\ncp a /tmp/b',
        f'{ROSTER} runs list >| /tmp/x.txt',
        f'{ROSTER} runs list &>> /tmp/x.txt',
        f'{ROSTER} runs list <> /tmp/x.txt',
        f'{ROSTER} runs check <(cat /etc/hosts)|tee /tmp/y',
        f"{PY} -c '{VALIDATE}' -s x -C Dataset out/full.yaml\ncurl http://example.org",
        f'{ROSTER} runs list #x\nls /',
        f"{ROSTER} runs list # don't\nrm -rf x",
        f'{ROSTER} runs list --label a#b; rm x',
        f'{ROSTER} runs list --label "$(cat /etc/hosts)"',
        f'{ROSTER} runs list --label "`id`"',
        f'{ROSTER} runs list\r\nls',
        f'{ROSTER} runs list \\\n\nls',
    ]
    classified = _classify(*[_bash(c) for c in shapes])
    assert [(d['classification'], d['basis']) for d in classified] == [('not_prescribed', FORBIDDEN_SHELL)] * len(shapes)
    assert denial_problems(classified) == []


def test_forms_bash_reads_as_one_prescribed_command_stay_prescribed():
    """A continuation line, a comment, surrounding newlines and quoted
    operator characters leave one simple command (#2031); a three-word roster
    command is matched word by word."""
    shapes = {
        f'{ROSTER} receipts check \\\n  --label L --project P': 'receipts check',
        f'{ROSTER} runs list  # just the list': 'runs list',
        f'{ROSTER} runs list\n# a note\n': 'runs list',
        f'\n{ROSTER} runs list\n': 'runs list',
        f"{ROSTER} runs list --label 'a;b|c>d'": 'runs list',
        f'{ROSTER} runs list --label "x(y)"': 'runs list',
        f'{ROSTER} api prompts check --strict': 'api prompts check',
        f'{ROSTER} api prompts check': 'api prompts check',
        f'{ROSTER} --manifest /repo/m.yaml api prompts check': 'api prompts check',
        f"{PY} -c '{VALIDATE}' -s x -C Dataset out/full.yaml  # validate": None,
    }
    classified = _classify(*[_bash(c) for c in shapes])
    assert [d['classification'] for d in classified] == ['prescribed'] * len(shapes), classified
    for d, roster in zip(classified, shapes.values()):
        assert roster is None or d['basis'] == f"the roster command '{roster}'"
    others = _classify(*[_bash(c) for c in (f'{ROSTER} api prompts pin --file x', f'{ROSTER} api prompts',
                                              f'{ROSTER} runs\rlist', f'{ROSTER} runs lister')])
    assert [d['classification'] for d in others] == ['not_prescribed'] * 4


def test_malformed_denial_records_are_unclassifiable(tmp_path):
    from run_native_canary import classify_denials, denial_problems
    odd = [
        {'tool_name': None, 'tool_use_id': 'a', 'tool_input': {'command': 'ls'}},
        {'tool_use_id': 'b', 'tool_input': {'command': 'ls'}},
        {'tool_name': 'Bash', 'tool_use_id': 'c', 'tool_input': {}},
        {'tool_name': 'Bash', 'tool_use_id': 'd', 'tool_input': {'command': ['ls']}},
        {'tool_name': 'Write', 'tool_use_id': 'e', 'tool_input': {'path': 'out/x.yaml'}},
        {'tool_name': 'Read', 'tool_use_id': 'f', 'tool_input': {'file_path': ''}},
        {'tool_name': 'Write', 'tool_use_id': 'g', 'tool_input': {'file_path': 'out/x\x00y'}},
    ]
    classified = _classify(*odd)
    assert [d['classification'] for d in classified] == ['unclassifiable'] * len(odd), classified
    assert len(denial_problems(classified)) == len(odd)
    # a path the filesystem cannot encode, under a directory that exists
    (tmp_path / 'out').mkdir()
    surrogate = classify_denials([{'tool_name': 'Write', 'tool_use_id': 'h', 'tool_input': {'file_path': 'out/x\ud800y'}}],
                                 instruction_text='', python=PY, repository=str(tmp_path),
                                 output_directories=['out'], readable_inputs=[])
    assert surrogate[0]['classification'] == 'unclassifiable', surrogate


def test_reads_of_the_registered_instruction_schemas_and_playbooks_are_prescribed():
    """#2033/#2039: the manifest, the instruction, the two schemas and the
    playbook closure are registered reads; the other agent definitions the
    toolchain inventories (evaluation rubrics among them) are not."""
    from run_native_canary import classify_denials, registered_reads
    resources = {
        'src/data_sheets_schema/schema/data_sheets_schema_all.yaml': '/repo/src/schema_all.yaml',
        'src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml': '/repo/src/schema_core_all.yaml',
        '.claude/commands/d4d-full-core.md': '/repo/.claude/commands/d4d-full-core.md',
        '.claude/commands/d4d-uniform-rules.md': '/repo/.claude/commands/d4d-uniform-rules.md',
        '.claude/commands/d4d-agent.md': '/repo/.claude/commands/d4d-agent.md',
        '.claude/agents/d4d-provenance-guard.md': '/repo/.claude/agents/d4d-provenance-guard.md',
        '.claude/agents/d4d-rubric10.md': '/repo/.claude/agents/d4d-rubric10.md',
        '.claude/commands/d4d-webfetch.md': '/repo/.claude/commands/d4d-webfetch.md',
    }
    job = {'bundle': 'data/b.txt', 'chunks': 'data/c.yaml', 'manifest': '/repo/m.yaml',
           'instruction': '/repo/prompts/job.md',
           'input_identity': {'source_manifest': {'path': '/repo/m2.yaml'},
                              'instruction': {'spec': {'agentic_toolchain': {'resources': resources}}}}}
    reads = registered_reads(job)
    def read(path):
        return {'tool_name': 'Read', 'tool_use_id': 'r', 'tool_input': {'file_path': path}}
    registered = ['/repo/m.yaml', '/repo/m2.yaml', '/repo/prompts/job.md', 'data/c.yaml',
                  *[v for k, v in resources.items() if 'rubric' not in k and 'webfetch' not in k]]
    other = ['/repo/.claude/agents/d4d-rubric10.md', '/repo/.claude/commands/d4d-webfetch.md',
             '/repo/data/prior_record.yaml']
    classified = classify_denials([read(p) for p in registered + other], instruction_text='', python=PY,
                                  repository='/repo', output_directories=[], readable_inputs=reads)
    assert [d['classification'] for d in classified] == ['prescribed'] * len(registered) + ['not_prescribed'] * len(other)
    assert registered_reads({}) == []


def test_a_blank_command_is_listed_and_not_disqualifying():
    """#2036: the runtime accepts an empty or whitespace command and would
    deny it; it is harmless and prescribed by nothing."""
    from run_native_canary import denial_problems
    classified = _classify(*[_bash(c) for c in ('', ' ', '\n', '\t')])
    assert [(d['classification'], d['basis']) for d in classified] == [('not_prescribed', 'an empty command')] * 4
    assert denial_problems(classified) == []


def test_each_bash_reading_rule_decides_a_classification():
    """#2040: each rule of the scan changes a classification when removed."""
    from run_native_canary import FORBIDDEN_SHELL
    cases = [
        # an unquoted parenthesis is an operator on its own
        (f'{ROSTER} runs list (x)', 'not_prescribed', FORBIDDEN_SHELL),
        (f'{ROSTER} runs list x)', 'not_prescribed', FORBIDDEN_SHELL),
        # a # inside a word is part of the word, never a comment
        (f'{ROSTER} agents playbook#x', 'not_prescribed', 'a CLI command outside the prescribed roster'),
        (f"{PY} -c '{VALIDATE}'#x -s s -C Dataset out/full.yaml", 'not_prescribed',
         'an ad-hoc -c script the system prompt forbids'),
        # an escaped character ends the start of a word, so a following # is not a comment
        (f'{ROSTER} agents playbook \\x#; rm -rf data', 'not_prescribed', FORBIDDEN_SHELL),
        # a backslash-newline joins lines anywhere, before the roster words included
        (f'{ROSTER} \\\nreceipts check --label L', 'prescribed', "the roster command 'receipts check'"),
        (f'{PY} \\\n-m data_sheets_schema.cli runs list', 'prescribed', "the roster command 'runs list'"),
        (f'{ROSTER} run\\\ns list', 'prescribed', "the roster command 'runs list'"),
    ]
    classified = _classify(*[_bash(c) for c, _, _ in cases])
    assert [(d['classification'], d['basis']) for d in classified] == [(c, b) for _, c, b in cases]


def test_a_stopped_attempt_classifies_its_single_result_line(tmp_path):
    """#2037: a stopped attempt that holds one result line is classified from
    it; with none, or with two, the receipt says it classified nothing."""
    from run_native_canary import stopped_denials, STOPPED_DENIALS_NOTE, classify_denials
    def classify(denials):
        return classify_denials(denials, instruction_text=_instruction(), python=PY, repository='/repo',
                                output_directories=['out'], readable_inputs=[])
    prescribed = _bash(f'{ROSTER} receipts check --label L')
    forbidden = _bash(f'{ROSTER} --help')
    path = tmp_path / 'transcript.jsonl'
    init = json.dumps({'type': 'system', 'subtype': 'init'}) + '\n'
    result = json.dumps({'type': 'result', 'is_error': True, 'permission_denials': [prescribed, forbidden]}) + '\n'
    path.write_bytes(init.encode() + b'\xff\xfe not json\n' + result.encode())
    out = stopped_denials(path, classify)
    assert [d['classification'] for d in out['permission_denials']] == ['prescribed', 'not_prescribed']
    assert len(out['disqualifying_denials']) == 1 and 'permission_denials_note' not in out
    path.write_text(init)
    assert stopped_denials(path, classify) == {'permission_denials_note': STOPPED_DENIALS_NOTE}
    path.write_text(init + result + result)
    assert '2 runtime result lines' in stopped_denials(path, classify)['permission_denials_note']
    assert 'FileNotFoundError' in stopped_denials(tmp_path / 'missing.jsonl', classify)['permission_denials_note']
    path.write_text(init + result)
    assert 'ZeroDivisionError' in stopped_denials(path, lambda denials: 1 / 0)['permission_denials_note']


def test_the_pre_close_record_waits_for_a_handler_holding_the_proxy_state(tmp_path):
    """#2029: the controller's record takes proxy.state, so a handler writing
    the ledger under it is not interrupted by a lock Timeout, and the
    controller's entry still lands before admission closes."""
    import threading, time
    from test_native_proxy import fixture_proxy
    from run_native_canary import record_then_close, record_controller_stop
    proxy, ledger, calls = fixture_proxy(tmp_path)
    ready, outcome = threading.Event(), {}
    def handler():
        with proxy.state:
            with ledger.transaction() as state:
                ready.set(); time.sleep(0.3)
                state.setdefault('handler_note', 'written')
        outcome['handler'] = 'ok'
    thread = threading.Thread(target=handler); thread.start(); ready.wait(5)
    seen = {}
    record_then_close(proxy, lambda reason: seen.update(r=record_controller_stop(ledger, 'native-offline', {'reason': reason})),
                      'native attempt deadline elapsed')
    thread.join(5)
    state = json.loads(ledger.path.read_bytes())
    assert outcome == {'handler': 'ok'} and state['handler_note'] == 'written'
    assert seen['r'] == {'ledger_stop_recorded': 'controller: native attempt deadline elapsed'}
    assert state['stopped_attempts']['native-offline']['reason'] == 'controller: native attempt deadline elapsed'
    assert proxy.closed
    # a record that raises never prevents admission from closing
    proxy2, _, _ = fixture_proxy(tmp_path / 'second')
    record_then_close(proxy2, lambda reason: 1 / 0, 'x')
    assert proxy2.closed
