"""Real private runner workers over honest synthetic captured associations.

The peer emits protocol frames only; it never executes the declared tool command.
No public permission, helper, native/provider or platform acceptance is implied.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_owner_control_v1 as control_module
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_selection as selections
from data_sheets_schema import native_shared_streams as streams
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_shared_selection import declaration
from tests.test_native_owner_runner import fixed_clock, make_case, selected_controls
from tests.test_native_owner_clock_binding_adversarial import clock_probe


TOOL_PEER = r'''
import json, pathlib, sys
def emit(value):
    print(json.dumps(value), flush=True)
init = json.loads(sys.stdin.buffer.readline())
emit({'type': 'control_response', 'response': {'subtype': 'success',
    'request_id': init['request_id'], 'response': {}}})
prompt = json.loads(sys.stdin.buffer.readline())
pathlib.Path('received-instruction.txt').write_bytes(prompt['message']['content'].encode('utf-8'))
session = '11111111-2222-4333-8444-555555555555'
cwd = str(pathlib.Path.cwd())
emit({'type': 'system', 'subtype': 'init', 'session_id': session, 'cwd': cwd})
payload = {'command': 'synthetic command never executed'}
emit({'type': 'assistant', 'session_id': session, 'message': {'content': [
    {'type': 'tool_use', 'id': 'synthetic-tool', 'name': 'Bash', 'input': payload}]}})
emit({'type': 'control_request', 'request_id': 'synthetic-request', 'request': {
    'subtype': 'hook_callback', 'callback_id': CALLBACK_TOKEN, 'input': {
        'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_use_id': 'synthetic-tool',
        'tool_input': payload, 'cwd': cwd}}})
response = json.loads(sys.stdin.buffer.readline())
assert response['response']['request_id'] == 'synthetic-request'
pathlib.Path('received-response.json').write_text(json.dumps(response))
# The software peer settles its fictional call without running any command.
emit({'type': 'user', 'session_id': session, 'message': {'content': [
    {'type': 'tool_result', 'tool_use_id': 'synthetic-tool', 'content': 'No command executed.', 'is_error': False}]}})
emit({'type': 'result', 'session_id': session, 'result': 'No tools or providers.'})
'''


def rehash_worker_case(case):
    """Keep the real runner's private C/E/started binding after fixture edits."""
    composition_raw = c.canonical(case['composition'])
    case['execution']['composition_raw_json'] = composition_raw.decode('utf-8')
    case['execution']['composition_sha256'] = c.sha(composition_raw)
    execution_raw = c.canonical(case['execution'])
    case['started']['registration_sha256'] = c.sha(execution_raw)
    case['started']['composition_sha256'] = c.sha(composition_raw)
    case['kwargs'].update(execution_raw=execution_raw, started_raw=c.canonical(case['started']))
    return case


def make_worker_case(root, controls, selection):
    case = make_case(root, controls)
    case.update(selection=selection, profile=deepcopy(case['identity']['stream_snapshot_profile']),
                parent_scope=profile._ACTIVE.get(), reader_observations=[])
    raw = selection.registration.raw
    case['composition'].update(selection_raw_json=raw.decode('utf-8'), selection_sha256=c.sha(raw))
    case['execution']['selection_sha256'] = c.sha(raw)
    return rehash_worker_case(case)


@pytest.fixture
def worker_case(declaration, selected_controls, tmp_path):
    selected = selections.capture(declaration['registration_path'])
    return make_worker_case(tmp_path.resolve() / 'worker-case', selected_controls, selected)


def read_in_worker(case, role='transcript'):
    """Use the actual published owner and current worker budget; no stand-ins."""
    budget = coordination.current_reader_budget()
    captured = evidence.read_regular(str(case['attempt'] / 'stream-owner.json'),
                                     'stream_owner', max_bytes=16 * 1024)
    raw = captured.captured.raw
    with profile.bind_reader_context(case['profile'], case['controls'],
            selection=case['selection'], execution_raw=case['kwargs']['execution_raw'],
            started_raw=case['kwargs']['started_raw'], owner_raw=raw, budget=budget) as context:
        member = streams.read_live_stream(str(case['attempt'] / (role + '.jsonl')), role,
                                         max_bytes=1_000_000, coordination=context)
        row = {'thread': threading.current_thread(), 'scope': profile._ACTIVE.get(),
               'budget': budget, 'owner_raw': raw, 'member': member, 'context': context}
        case['reader_observations'].append(row)
        return row


def install_reader_operation(case, kind):
    """Preserve real control handling, selecting one actual operation to read."""
    if kind not in ('observer', 'classifier'):
        raise ValueError('unknown synthetic worker kind')
    peer = Path(case['execution']['argv'][3])
    callback = case['controls']['native_control'].HISTORY_CONTRACT['callback_id']
    peer.write_text(TOOL_PEER.replace('CALLBACK_TOKEN', repr(callback)))
    def observe(event):
        case['observed'].append(event)
        if kind == 'observer' and event.get('type') == 'system' and event.get('subtype') == 'init':
            read_in_worker(case)
    def classify(*args):
        if kind == 'classifier':
            read_in_worker(case)
        return ('prescribed', 'Synthetic software fixture only; the peer executes no command.')
    case['kwargs'].update(event_observer=observe, command_classifier=classify)
    return case


@pytest.mark.parametrize('kind', ['observer', 'classifier'])
def test_actual_runner_worker_reads_under_fresh_scope_without_new_budget_or_lease(
        worker_case, clock_probe, monkeypatch, kind):
    case = install_reader_operation(worker_case, kind)
    parent = case['parent_scope']
    original_scope = profile._worker_scope
    entries, starts = [], []
    real_ns = time.monotonic_ns
    original_path = list(sys.path)
    original_modules = {name: sys.modules.get(name) for name in case['controls']}

    def timed_start():
        now = real_ns()
        frame = sys._getframe(1)
        if frame.f_code.co_name == '_start_work':
            channel = frame.f_locals['self']
            starts.append({'kind': frame.f_locals['kind'], 'start_ns': now,
                           'owner_budget': channel._owner_budget,
                           'contract': deepcopy(channel.contract)})
        return now

    def tracked_scope(selected_parent, owner_budget):
        budget = coordination.current_reader_budget()
        scope = original_scope(selected_parent, owner_budget)
        entries.append({'scope': scope, 'budget': budget, 'owner_budget': owner_budget,
                        'thread': threading.current_thread(), 'parent': selected_parent})
        return scope

    monkeypatch.setattr(control_module, 'time', SimpleNamespace(
        monotonic_ns=timed_start, sleep=time.sleep))
    monkeypatch.setattr(profile, '_worker_scope', tracked_scope)
    expected_instruction = case['instruction'].read_bytes()
    assert case['runner'].execute_child(**case['kwargs']) == 0
    assert case['runner'].report()['state'] == 'completed'
    assert case['runner'].report()['cleanup_errors'] == []
    assert (case['root'] / 'received-instruction.txt').read_bytes() == expected_instruction
    assert len(case['reader_observations']) == 1
    observed = case['reader_observations'][0]
    owner = json.loads(observed['owner_raw'])
    assert observed['owner_raw'] == case['runner'].owner_raw()
    assert observed['owner_raw'] == (case['attempt'] / 'stream-owner.json').read_bytes()
    assert owner['execution_sha256'] == c.sha(case['kwargs']['execution_raw'])
    assert owner['started_sha256'] == c.sha(case['kwargs']['started_raw'])
    raw = observed['member'].captured.raw
    assert raw and (case['attempt'] / 'transcript.jsonl').read_bytes().startswith(raw)
    assert observed['thread'] is not threading.current_thread()
    assert observed['scope'] is not parent and observed['scope']._parent is parent
    assert observed['scope']._budget is observed['budget']
    assert len(entries) == len(starts) > 1
    assert len({id(entry['scope']) for entry in entries}) == len(entries)
    assert all(entry['scope'] is not parent and entry['parent'] is parent for entry in entries)
    for entry, started in zip(entries, starts):
        scope, budget, owner_budget = entry['scope'], entry['budget'], entry['owner_budget']
        key = ('observer_timeout_seconds' if started['kind'] == 'observer'
               else 'callback_timeout_seconds')
        expected = min(owner_budget.deadline_ns,
            started['start_ns'] + int(started['contract'][key] * 1_000_000_000))
        assert budget.deadline_ns == expected
        assert owner_budget is started['owner_budget'] and budget is not owner_budget
        assert budget.clock_domain() == owner_budget.clock_domain() == owner['clock_domain']
        assert len(budget.stop_events) == len(owner_budget.stop_events)
        assert all(actual is saved for actual, saved in zip(budget.stop_events, owner_budget.stop_events))
        assert scope.controls is parent.controls and scope.profile == parent.profile
        assert scope._creator is entry['thread'] and scope._budget is budget
        assert scope._guard.scope.budget is budget
        assert not scope.live
    # Exact frozen limits, including the short classifier budget, remain real.
    assert starts[0]['contract']['observer_timeout_seconds'] == 120
    assert starts[0]['contract']['callback_timeout_seconds'] == 2
    assert any(row['kind'] == 'classifier' for row in starts)
    # The real clock probe separates persistent owning leases from temporary
    # rechecks. Borrowing profile authority adds neither an owning lease nor close.
    assert len(clock_probe.leases) == 1 + len(entries)
    assert len(clock_probe.closes) == len(clock_probe.leases)
    assert all(lease._closed for lease in clock_probe.leases)
    assert {id(lease) for lease, _ in clock_probe.closes} == {id(lease) for lease in clock_probe.leases}
    assert all(thread is lease._fixture_thread for lease, thread in clock_probe.closes)
    assert profile._ACTIVE.get() is parent and parent.live
    parent.require()
    assert list(sys.path) == original_path
    assert all(sys.modules.get(name) is module for name, module in original_modules.items())
    for entry in entries:
        with pytest.raises(ValueError): entry['scope'].require()
    with pytest.raises(ValueError): observed['context'].require_current()
    response = json.loads((case['root'] / 'received-response.json').read_text())
    assert response['response']['request_id'] == 'synthetic-request'
    assert case['runner'].report()['execution_authorized'] is False


def test_selected_unbound_component_keeps_ordinary_worker_without_reader_authority(
        worker_case, monkeypatch):
    case = worker_case
    selected = profile.bind_control(case['profile'], case['controls'])
    policy = case['kwargs']['command_policy']
    external_stop = threading.Event()
    channel = selected(policy, lambda *args: ('prescribed', 'component fixture'),
        event_observer=lambda event: None, attempt_deadline_ns=time.monotonic_ns() + 30_000_000_000,
        stop_event=external_stop)
    rows = []
    def borrowed_is_forbidden(*args, **kwargs):
        pytest.fail('unbound component must not acquire borrowed profile authority')
    monkeypatch.setattr(profile, '_worker_scope', borrowed_is_forbidden)

    def operation():
        budget = coordination.current_reader_budget()
        rows.append({'thread': threading.current_thread(), 'budget': budget,
                     'scope': profile._ACTIVE.get()})
        assert budget.clock_domain() is None
        assert budget.remaining() > 0
        with pytest.raises(ValueError, match='selected loader scope'):
            profile.bind_reader_context(case['profile'], case['controls'],
                selection=case['selection'], execution_raw=case['kwargs']['execution_raw'],
                started_raw=case['kwargs']['started_raw'], owner_raw=b'{}', budget=budget)
        return None

    try:
        channel._start_work('observer', {'type': 'system'}, operation)
        worker = channel._work_thread
        worker.join(5)
        assert not worker.is_alive()
        # This component has no process or journal: inspect the actual worker's
        # published reply without pretending the journal-dependent pump started.
        _, result = channel._work_replies.get_nowait()
        if isinstance(result, BaseException):
            raise result
        assert result is None
        assert len(rows) == 1
        assert rows[0]['thread'] is not threading.current_thread() and rows[0]['scope'] is None
        assert channel._owner_budget.clock_domain() is None
        assert rows[0]['budget'].stop_events == channel._owner_budget.stop_events
        assert not (case['attempt'] / 'stream-owner.json').exists()
        assert profile._ACTIVE.get() is case['parent_scope']
    finally:
        channel._stop_history()
        if channel._work_thread is not None:
            channel._work_thread.join(5)
            assert not channel._work_thread.is_alive()
        channel.selector.close()
