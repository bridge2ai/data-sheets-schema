"""PR6302 production adapter controls over retained bytes, 2026-11-21.

Startup frames are unchanged retained observations. Recorder frames are openly
mutated software controls, with invented authority plumbing and real local
stream/provenance reads. No native process, provider or launch admission runs.
"""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_capture as captured
from data_sheets_schema import native_shared_capture_orchestration as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_observations as observations
from data_sheets_schema import native_shared_phase as phase
from data_sheets_schema import native_wire_2_1_325 as wire
from data_sheets_schema import native_attribution_results as saved_results
from data_sheets_schema import native_attribution_registration_v2 as attribution
from data_sheets_schema import source_attribution_preflight as preflight
from data_sheets_schema import source_review
from data_sheets_schema.native_shared_controller_orchestration import CallbackAdapter
from data_sheets_schema.native_shared_receipts import _ReceiptCatalogContext
from tests.test_source_attribution_preflight import inputs as preflight_inputs


class Stopped(Exception):
    pass


def prohibit_transports(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('offline production adapter control attempted a process or transport')
    for name in ('Popen', 'run', 'check_output'):
        monkeypatch.setattr(subprocess, name, blocked)
    monkeypatch.setattr(socket.socket, 'connect', blocked)


prohibit_transports = pytest.fixture(autouse=True)(prohibit_transports)


def retained():
    path = Path(__file__).parent / 'fixtures/native_permission_2_1_325/retained.json'
    files = json.loads(path.read_bytes())['traces']['r4/settled']['files']
    def decode(name):
        record = files[name]
        raw = base64.b64decode(record['raw_base64'], validate=True)
        assert len(raw) == record['decoded_bytes']
        assert hashlib.sha256(raw).hexdigest() == record['decoded_sha256']
        return raw
    rows = decode('transcript.jsonl').splitlines(keepends=True)
    events = [json.loads(row) for row in rows]
    controls = decode('control.jsonl').splitlines(keepends=True)
    policy = json.loads(decode('evidence_root/projection.json'))['probe_policy']
    executable = json.loads(decode('launch.before.json'))['executable']
    init = events[2]
    runtime = {'executable': executable, 'model': init['model'], 'auxiliary_models': [],
               'auth': {'expected_api_key_source': init['apiKeySource']}}
    return rows, events, controls, policy, runtime


def adapter(tmp_path, monkeypatch):
    """Reuse the real stream/phase readers with openly invented admission state."""
    rows, events, controls, policy, runtime = retained()
    selected = CallbackAdapter.__new__(CallbackAdapter)
    selected.raw = b'software-only composition, never admission'
    selected.execution = {'attempt_directory': str(tmp_path), 'runtime': runtime}
    selected.failure = selected.final_evidence = selected.recorder_identity = None
    selected._stream_diagnostic_json = selected._recorder_status = None
    selected.recorder_call = None
    selected.recorder_done = False
    selected._activated, selected._initialized = True, False
    selected._native_event_count = 0
    selected._prefix_session = selected._observed_session = None
    selected._stream_prefixes, selected._stream_files = {}, {}
    selected._stream_members = ()
    selected._receipt_catalogs = _ReceiptCatalogContext()
    selected._budget_stop = Stopped
    selected.policy = policy
    selected.selection = SimpleNamespace(registration=SimpleNamespace(
        pin=SimpleNamespace(path='/software-only/selection.json')))
    selected.state = SimpleNamespace(observe=lambda *a, **kw: None,
        report=lambda **kw: {'draft_gate_passed': True, 'problems': []}, checks=[])
    commands = {name: ('software-helper', name) for name in phase.COMMAND_NAMES}
    selected.phase = phase.PhaseState(commands,
        full_path='/software-only/full.yaml', core_path='/software-only/core.yaml',
        report_path='/software-only/report.json', receipt_path='/software-only/receipt.json',
        working_directory=policy['readonly_lookups']['repository'], runtime=runtime)
    monkeypatch.setattr(selected, '_phase_state', lambda *a, **kw: (SimpleNamespace(), None))
    monkeypatch.setattr(selected, '_final_unchanged', lambda *a: None)
    initialized = []
    def initialize(path, *, transcript_bytes, control_bytes, stream_files, observed_prefixes):
        assert path == '/software-only/selection.json'
        assert transcript_bytes == observed_prefixes['transcript'].bytes
        assert control_bytes == observed_prefixes['control'].bytes
        joined = observations.initialization(observed_prefixes['transcript'],
            observed_prefixes['control'], policy=policy, runtime=runtime)
        initialized.append(joined)
    monkeypatch.setattr(capture, 'initialize', initialize)
    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_bytes(b'')
    (tmp_path / 'control.jsonl').write_bytes(b''.join(controls[:2]))
    return selected, rows, events, initialized


def deliver(selected, tmp_path, raw):
    with (tmp_path / 'transcript.jsonl').open('ab') as output:
        output.write(raw)
    selected.observe(json.loads(raw))


def test_retained_prefix_ack_init_keep_raw_rows_and_actual_initialization_join(tmp_path, monkeypatch):
    selected, rows, events, initialized = adapter(tmp_path, monkeypatch)
    for raw in rows[:3]:
        deliver(selected, tmp_path, raw)
    assert (tmp_path / 'transcript.jsonl').read_bytes() == b''.join(rows[:3])
    assert selected._stream_prefixes['transcript'].lines == 3
    assert selected._stream_prefixes['transcript'].raw == b''.join(rows[:3])
    assert selected._initialized and selected._prefix_session == events[2]['session_id']
    assert len(initialized) == 1 and initialized[0][0] == events[2]['session_id']
    assert selected.phase.report()['problems'] == []


def test_adapter_retains_optional_prefix_behavior(tmp_path, monkeypatch):
    selected, rows, events, initialized = adapter(tmp_path, monkeypatch)
    for raw in rows[1:3]:
        deliver(selected, tmp_path, raw)
    assert selected._initialized and selected._prefix_session is None
    assert len(initialized) == 1 and initialized[0][0] == events[2]['session_id']


def test_adapter_rejects_repeated_late_foreign_or_unpinned_prefix(tmp_path, monkeypatch, mutation):
    selected, rows, events, initialized = adapter(tmp_path, monkeypatch)
    if mutation == 'repeated':
        deliver(selected, tmp_path, rows[0])
        raw = rows[0]
    elif mutation == 'late':
        deliver(selected, tmp_path, rows[1])
        raw = rows[0]
    elif mutation == 'foreign':
        deliver(selected, tmp_path, rows[0])
        deliver(selected, tmp_path, rows[1])
        changed = deepcopy(events[2])
        changed['session_id'] = '11111111-1111-4111-8111-111111111111'
        raw = c.canonical(changed) + b'\n'
    elif mutation == 'unpinned':
        selected.execution['runtime']['executable']['sha256'] = '0' * 64
        raw = rows[0]
    else:
        changed = deepcopy(events[0])
        changed['extra'] = 'unreviewed'
        raw = c.canonical(changed) + b'\n'
    with pytest.raises(Stopped):
        deliver(selected, tmp_path, raw)
    assert selected.failure and not initialized


test_adapter_rejects_repeated_late_foreign_or_unpinned_prefix = pytest.mark.parametrize(
    'mutation', ['repeated', 'late', 'foreign', 'unpinned', 'unknown_key'])(
        test_adapter_rejects_repeated_late_foreign_or_unpinned_prefix)


def test_adapter_prefix_cannot_hide_changed_physical_bytes(tmp_path, monkeypatch):
    selected, rows, events, initialized = adapter(tmp_path, monkeypatch)
    deliver(selected, tmp_path, rows[0])
    changed = rows[0].replace(b'ui.render', b'ui.rendeR')
    assert changed != rows[0] and len(changed) == len(rows[0])
    (tmp_path / 'transcript.jsonl').write_bytes(changed)
    with pytest.raises(Stopped, match='changed'):
        deliver(selected, tmp_path, rows[1])
    assert not initialized


def recorder_control(tmp_path, monkeypatch):
    selected, rows, events, initialized = adapter(tmp_path, monkeypatch)
    for raw in rows[:3]:
        deliver(selected, tmp_path, raw)
    # A fabricated recorder turn uses the unchanged retained metadata shape.
    result = deepcopy(next(event for event in events if type(event.get('tool_use_result')) is dict
        and 'stdout' in event['tool_use_result']))
    block = result['message']['content'][0]
    block.update(tool_use_id='software-recorder', is_error=False)
    destination = tmp_path / 'provenance.yaml'
    lineage = {'software_only': 'exact lineage'}
    destination.write_bytes(c.canonical({'native_shared_generation': lineage}))
    stdout = '✓ ' + str(destination) + '\n'
    block['content'] = stdout
    result['tool_use_result'].update(stdout=stdout, stderr='', interrupted=False,
                                    isImage=False, noOutputExpected=False)
    result['tool_use_result'].pop('exitCode', None)
    result['tool_use_result'].pop('exit_code', None)
    selected.policy = {'native_shared_helpers': {'recorder': 'software recorder',
        'advance': 'software advance', 'final_evidence': 'software final evidence'},
        'post_final_recorder': {'destination': str(destination), 'command': 'software recorder'}}
    selected.recorder_call = 'software-recorder'
    selected.phase = SimpleNamespace(observe=lambda *a, **kw: [], report=lambda **kw: {'passed': True})
    call = {'name': 'Bash', 'input': {'command': 'software recorder'}}
    trace = SimpleNamespace(calls={'software-recorder': (None, None, call)}, denial=lambda identity: None)
    run = SimpleNamespace(trace=lambda: trace)
    monkeypatch.setattr(selected, '_phase_state', lambda *a, **kw: (run, None))
    monkeypatch.setattr(captured, '_provenance_block', lambda actual: lineage)
    return selected, result, block, destination


def test_adapter_recorder_preserves_absent_exit_and_checks_saved_lineage(tmp_path, monkeypatch):
    selected, result, block, destination = recorder_control(tmp_path, monkeypatch)
    deliver(selected, tmp_path, c.canonical(result) + b'\n')
    assert selected.recorder_done
    assert selected.recorder_identity['path'] == str(destination)
    assert selected.report()['recorder_status'] == {
        'exit_code': None, 'exit_status': None, 'status_basis': wire.STATUS_BASIS}
    assert 'exitCode' not in result['tool_use_result'] and 'exit_code' not in result['tool_use_result']


def test_adapter_numeric_recorder_keeps_existing_report_shape(tmp_path, monkeypatch):
    selected, result, block, destination = recorder_control(tmp_path, monkeypatch)
    result['tool_use_result']['exitCode'] = 0
    deliver(selected, tmp_path, c.canonical(result) + b'\n')
    assert selected.recorder_done and 'recorder_status' not in selected.report()


def test_adapter_permission_denial_is_a_deliberate_failure(tmp_path, monkeypatch):
    selected, rows, events, initialized = adapter(tmp_path, monkeypatch)
    for raw in rows[:3]:
        deliver(selected, tmp_path, raw)
    denied = {'type': 'system', 'subtype': 'permission_denied', 'tool_name': 'Bash',
        'tool_use_id': 'software-denied', 'decision_reason_type': 'other',
        'decision_reason': 'software denial control', 'message': 'software denied Bash',
        'uuid': '11111111-1111-4111-8111-111111111111', 'session_id': events[2]['session_id']}
    with pytest.raises(Stopped, match='native permission denial observed'):
        deliver(selected, tmp_path, c.canonical(denied) + b'\n')
    assert 'AttributeError' not in selected.failure
    first_stop = selected.failure
    observed_bytes = (tmp_path / 'transcript.jsonl').read_bytes()
    for later in ({'type': 'result', 'is_error': False}, events[3]):
        with pytest.raises(Stopped, match='native permission denial observed'):
            selected.observe(later)
    assert selected.failure == first_stop and not selected.recorder_done
    assert (tmp_path / 'transcript.jsonl').read_bytes() == observed_bytes


def test_adapter_recorder_refuses_wrong_stdout_lineage_or_flags(tmp_path, monkeypatch, mutation):
    selected, result, block, destination = recorder_control(tmp_path, monkeypatch)
    if mutation == 'stdout':
        result['tool_use_result']['stdout'] = block['content'] = '✓ /another/provenance.yaml\n'
    elif mutation == 'lineage':
        destination.write_bytes(c.canonical({'native_shared_generation': {'wrong': True}}))
    elif mutation == 'unpinned':
        selected.execution['runtime']['executable']['sha256'] = '0' * 64
    else:
        result['tool_use_result']['interrupted'] = True
    with pytest.raises(Stopped):
        deliver(selected, tmp_path, c.canonical(result) + b'\n')
    assert not selected.recorder_done and selected._recorder_status is None


test_adapter_recorder_refuses_wrong_stdout_lineage_or_flags = pytest.mark.parametrize(
    'mutation', ['stdout', 'lineage', 'unpinned', 'interrupted'])(
        test_adapter_recorder_refuses_wrong_stdout_lineage_or_flags)


class SoftwareSavedState:
    """Invent only already-checked draft authority around the saved recorder branch."""
    def __init__(self, runtime):
        self.runtime = deepcopy(runtime)
        self.pending = {}
        self.checks = 0

    def _command_kind(self, command):
        return 'final_evidence' if command == 'software final evidence' else None

    def observe(self, event, **kwargs):
        for block in event.get('message', {}).get('content', []):
            if block['type'] == 'tool_use':
                self.pending[block['id']] = {'kind': self._command_kind(block['input']['command'])}
            elif block['type'] == 'tool_result':
                self.pending.pop(block['tool_use_id'])

    def finish(self):
        assert not self.pending
        return {'problems': [], 'draft_gate_passed': True}


def saved_recorder_control(tmp_path, monkeypatch):
    selected, recorder, block, destination = recorder_control(tmp_path, monkeypatch)
    def call(identity, command):
        return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use',
            'id': identity, 'name': 'Bash', 'input': {'command': command}}]}}
    content = json.dumps({'checked': True, 'findings': []})
    final = {'type': 'user', 'message': {'content': [{'type': 'tool_result',
        'tool_use_id': 'software-final', 'content': content, 'is_error': False}]},
        'tool_use_result': {'stdout': content, 'exitCode': 0}}
    snapshot = SimpleNamespace(path=lambda path: Path(path),
        metadata={str(destination): {'regular': True, 'links': 1}},
        alias_metadata={str(destination): {'symlink': False}},
        read=lambda path, role: Path(path).read_bytes())
    prepared = {'state': SoftwareSavedState(selected.execution['runtime']),
        'snapshot': snapshot, 'policy': selected.policy, 'readonly': {},
        'events': [call('software-final', 'software final evidence'), final,
                   call('software-recorder', 'software recorder'), recorder],
        'phase_report': {'passed': True, 'problems': [], 'checks': [
            {'tool_use_id': 'software-recorder', 'helper': 'recorder', 'exit_code': None,
             'exit_status': None, 'status_basis': wire.STATUS_BASIS}]}}
    return prepared, recorder, block


def test_actual_saved_draft_preserves_absent_recorder_exit(tmp_path, monkeypatch):
    prepared, recorder, block = saved_recorder_control(tmp_path, monkeypatch)
    report, final, done = saved_results._saved_draft(prepared, None)
    assert done and report['draft_gate_passed'] and report['problems'] == []
    assert final == {'checked': True, 'findings': []}
    assert report['recorder_status'] == {
        'exit_code': None, 'exit_status': None, 'status_basis': wire.STATUS_BASIS}


def test_actual_saved_draft_refuses_unbound_recorder_success(tmp_path, monkeypatch, mutation):
    prepared, recorder, block = saved_recorder_control(tmp_path, monkeypatch)
    if mutation == 'phase':
        prepared['phase_report']['checks'] = []
    elif mutation == 'duplicate_phase':
        prepared['phase_report']['checks'] *= 2
    elif mutation == 'foreign_phase':
        prepared['phase_report']['checks'][0]['tool_use_id'] = 'another-recorder'
    elif mutation == 'stdout':
        recorder['tool_use_result']['stdout'] = block['content'] = '✓ /wrong/provenance.yaml\n'
    elif mutation == 'unpinned':
        prepared['state'].runtime['executable']['sha256'] = '0' * 64
    else:
        recorder['tool_use_result']['interrupted'] = True
    report, final, done = saved_results._saved_draft(prepared, None)
    assert not done and not report['draft_gate_passed'] and report['problems']
    assert 'recorder_status' not in report


test_actual_saved_draft_refuses_unbound_recorder_success = pytest.mark.parametrize(
    'mutation', ['phase', 'duplicate_phase', 'foreign_phase', 'stdout', 'unpinned', 'interrupted'])(
        test_actual_saved_draft_refuses_unbound_recorder_success)


def test_actual_saved_draft_keeps_numeric_recorder_behavior(tmp_path, monkeypatch):
    prepared, recorder, block = saved_recorder_control(tmp_path, monkeypatch)
    recorder['tool_use_result']['exitCode'] = 0
    prepared.pop('phase_report')
    report, final, done = saved_results._saved_draft(prepared, None)
    assert done and report['draft_gate_passed'] and 'recorder_status' not in report


def attribution_control(tmp_path, preflight_inputs):
    """Construct software authority; retain the actual observer and file checker."""
    paths = {}
    for name, raw_name in (('full', 'record_raw'), ('report', 'report_raw'),
                          ('bundle', 'bundle_raw'), ('chunk_manifest', 'chunk_manifest_raw'),
                          ('source_manifest', 'source_manifest_raw')):
        paths[name] = tmp_path / (name + '.txt')
        paths[name].write_bytes(preflight_inputs[raw_name])
    spec = SimpleNamespace(_agentic_artifact_paths={
        'full': paths['full'], 'report': paths['report'], 'core': tmp_path / 'core.yaml'},
        bundle=paths['bundle'], chunk_manifest=paths['chunk_manifest'],
        manifest=paths['source_manifest'], manifest_used=True, project='EXAMPLE', render_version=26)
    selected = attribution.NativeAttributionState.__new__(attribution.NativeAttributionState)
    selected.spec = spec
    selected.reg = {'max_draft_checks': 3, 'inputs': {
        name: {'path': str(paths[name]), 'sha256': hashlib.sha256(paths[name].read_bytes()).hexdigest()}
        for name in ('bundle', 'chunk_manifest', 'source_manifest')}}
    selected.registration_raw = b'explicit software-only attribution authority'
    selected.runtime = retained()[4]
    selected.live = True
    selected.problems, selected.observations = [], []
    selected.pending, selected.seen = {}, set()
    selected.epoch, selected.checks, selected.accepted, selected.terminal = 0, 0, None, False
    selected.protected = {paths['full'], paths['bundle'], paths['chunk_manifest']}
    selected.report_path = paths['report']
    selected.index = 0
    commands = {name: 'software ' + name for name in ('draft', 'evidence', 'final_evidence', 'source_inventory')}
    selected._command_kind = lambda command: next(
        (name for name, literal in commands.items() if literal == command), None)
    payload = preflight.check_files(**attribution._arguments(spec))
    assert payload['checked'] is True and payload['passed'] is True and payload['protocol_version'] == 7
    return selected, payload, paths, commands


def attribution_turn(selected, kind, payload, commands, *, mutate=None):
    identity = 'software-' + kind + '-' + str(selected.index)
    selected.observe({'type': 'assistant', 'message': {'content': [{'type': 'tool_use',
        'id': identity, 'name': 'Bash', 'input': {'command': commands[kind]}}]}})
    raw = json.dumps(payload)
    event = {'type': 'user', 'message': {'content': [{'type': 'tool_result',
        'tool_use_id': identity, 'is_error': False, 'content': raw}]},
        'tool_use_result': {'stdout': raw, 'stderr': '', 'interrupted': False,
                           'isImage': False, 'noOutputExpected': False}}
    if mutate is not None:
        mutate(event)
    selected.observe(event)
    return event


def test_inherited_attribution_checks_adapted_draft_hashes_and_current_bytes(tmp_path, preflight_inputs):
    selected, payload, paths, commands = attribution_control(tmp_path, preflight_inputs)
    event = attribution_turn(selected, 'draft', payload, commands)
    assert type(selected).observe is attribution.NativeAttributionState.observe
    report = selected.report(complete=True)
    assert report['draft_gate_passed'] and report['problems'] == []
    observation = report['observations'][0]
    assert observation['exit_code'] is None and observation['exit_status'] is None
    assert observation['status_basis'] == wire.STATUS_BASIS
    assert observation['input_sha256'] == payload['input_sha256']
    assert observation['verified_against_current_saved_bytes'] is True
    assert 'exitCode' not in event['tool_use_result'] and 'exit_code' not in event['tool_use_result']
    paths['full'].write_bytes(b'description: Changed after the observed draft.\n')
    changed = selected.report(complete=True)
    assert not changed['draft_gate_passed']
    assert any('current saved bytes' in problem for problem in changed['problems'])


def test_inherited_attribution_refuses_runtime_hash_or_numeric_contradiction(tmp_path, preflight_inputs, mutation):
    selected, payload, paths, commands = attribution_control(tmp_path, preflight_inputs)
    mutate = None
    if mutation == 'absent_runtime':
        selected.runtime = None
    elif mutation == 'wrong_runtime':
        selected.runtime['executable']['sha256'] = '0' * 64
    elif mutation == 'input_hash':
        payload['input_sha256']['bundle'] = '0' * 64
    else:
        mutate = lambda event: event['tool_use_result'].update(exitCode=1)
    attribution_turn(selected, 'draft', payload, commands, mutate=mutate)
    report = selected.report(complete=True)
    assert not report['draft_gate_passed'] and report['problems']
    assert not any(row.get('reported_passed') for row in report['observations'])


test_inherited_attribution_refuses_runtime_hash_or_numeric_contradiction = pytest.mark.parametrize(
    'mutation', ['absent_runtime', 'wrong_runtime', 'input_hash', 'numeric_contradiction'])(
        test_inherited_attribution_refuses_runtime_hash_or_numeric_contradiction)


def test_inherited_attribution_keeps_explicit_numeric_success(tmp_path, preflight_inputs):
    selected, payload, paths, commands = attribution_control(tmp_path, preflight_inputs)
    attribution_turn(selected, 'draft', payload, commands,
        mutate=lambda event: event['tool_use_result'].update(exitCode=0))
    report = selected.report(complete=True)
    assert report['draft_gate_passed']
    assert report['observations'][0]['exit_code'] == 0
    assert 'status_basis' not in report['observations'][0]


def test_inherited_attribution_validates_terminal_helper_stdout(tmp_path, preflight_inputs, kind, changed):
    selected, draft_payload, paths, commands = attribution_control(tmp_path, preflight_inputs)
    attribution_turn(selected, 'draft', draft_payload, commands)
    payload = (source_review.inventory(paths['full'].read_text(), 'final_full')
               if kind == 'source_inventory' else {'checked': True, 'findings': []})
    mutation = (lambda event: event['tool_use_result'].update(stdout='{}')) if changed else None
    attribution_turn(selected, kind, payload, commands, mutate=mutation)
    report = selected.report(complete=True)
    if changed:
        assert not report['draft_gate_passed'] and report['terminal_failure_observed']
        assert any('stdout' in problem for problem in report['problems'])
    else:
        assert report['draft_gate_passed'] and report['problems'] == []
        row = report['observations'][-1]
        assert row['kind'] == kind and row['exit_code'] is None and row['exit_status'] is None
        assert row['status_basis'] == wire.STATUS_BASIS


test_inherited_attribution_validates_terminal_helper_stdout = pytest.mark.parametrize(
    'kind,changed', [(kind, changed) for kind in ('evidence', 'final_evidence', 'source_inventory')
                     for changed in (False, True)])(test_inherited_attribution_validates_terminal_helper_stdout)
