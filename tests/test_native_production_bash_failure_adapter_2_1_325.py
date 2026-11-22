"""PR6302 failed Bash adapter controls, 2026-11-22; entirely offline.

The primary controls append the unchanged retained round-two line-8 result to
explicitly constructed command/admission histories. Startup rows remain exact.
The real Trace, adapter stream reader and PhaseState consume those histories;
stage authority, effects and attribution are software fixtures, not production
admission or qualification. Recorder controls reuse the existing saved/live
authority scaffolds and openly mutate the retained result identity or output.
"""

from copy import deepcopy
import json
import shlex
from types import SimpleNamespace
from uuid import UUID

import pytest

from data_sheets_schema import native_shared_capture as captured
from data_sheets_schema import native_shared_capture_orchestration as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_observations as observations
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_wire_2_1_325 as wire
from data_sheets_schema import native_attribution_results as saved_results
from tests import test_native_production_wire_adapter_2_1_325 as existing
from tests import test_native_production_wire_round2_2_1_325 as round2


prohibit_transports = existing.prohibit_transports


def failure_control(identity, session, *, output=None):
    """Construct a control from real failure fields; never call it original raw."""
    rows, events, _, _, _ = round2.retained('settled')
    value = deepcopy(events[7])
    block = value['message']['content'][0]
    assert block['tool_use_id'] == 'stage_receipt' and block['is_error'] is True
    value['session_id'] = session
    block['tool_use_id'] = identity
    value['tool_result_meta'][0]['id'] = identity
    if output is not None:
        block['content'] = 'Exit code 1\n' + output
        value['tool_use_result'] = 'Error: ' + block['content']
    return value


class AdapterHistory:
    """Use real observed-prefix joins with openly fabricated callback authority."""

    def __init__(self, tmp_path, monkeypatch):
        self.directory = tmp_path
        self.selected, self.rows, self.events, self.initialized = round2.adapter(
            tmp_path, monkeypatch, 'settled')
        self.controls = round2.retained('settled')[2]
        self.number = 0
        self.seals = []
        self.traces = []
        for raw in self.rows[:2]:
            existing.deliver(self.selected, tmp_path, raw)
        self.session = self.events[1]['session_id']

        def phase_state(*args, **kwargs):
            trace = observations.Trace(self.selected._stream_prefixes['transcript'],
                self.selected._stream_prefixes['control'], session_id=self.session,
                policy=self.selected.policy, runtime=self.selected.execution['runtime'])
            self.traces.append(trace)
            self.run = SimpleNamespace(trace=lambda: trace)
            return self.run, None

        monkeypatch.setattr(self.selected, '_phase_state', phase_state)
        monkeypatch.setattr(self.selected, '_run', lambda *a, **kw: self.run)
        monkeypatch.setattr(captured, '_effect_view_from_decision', lambda *a, **kw: None)
        monkeypatch.setattr(policy, 'stage_overlay_governs', lambda *a, **kw: False)
        monkeypatch.setattr(capture, 'seal_originals', lambda run, action: self.seals.append(action))

    def deliver(self, event):
        existing.deliver(self.selected, self.directory, c.canonical(event) + b'\n')

    def command(self, kind):
        return shlex.join(self.selected.phase._command_argv[kind])

    def call(self, name, inputs, *, identity=None, admitted=True):
        self.number += 1
        identity = identity or 'software-tool-' + str(self.number)
        call = deepcopy(self.events[5])
        call['uuid'] = str(UUID(int=1000 + self.number))
        call['message']['id'] = 'software-message-' + str(self.number)
        call['message']['content'] = [{'type': 'tool_use', 'id': identity,
            'name': name, 'input': inputs}]
        self.deliver(call)
        callback = deepcopy(self.events[6])
        callback['request_id'] = str(UUID(int=2000 + self.number))
        callback['request']['tool_use_id'] = identity
        callback['request']['input'].update(tool_use_id=identity, tool_name=name,
            tool_input=inputs)
        self.deliver(callback)
        if admitted:
            decision = deepcopy(json.loads(self.controls[3]))
            decision.update(request=callback, classification='prescribed',
                basis='software-only callback admission')
            decision['response'] = {'type': 'control_response', 'response': {
                'subtype': 'success', 'request_id': callback['request_id'], 'response': {}}}
            with (self.directory / 'control.jsonl').open('ab') as stream:
                stream.write(c.canonical(decision) + b'\n')
        return identity

    def success(self, identity, *, text='checked', bash=True):
        result = failure_control(identity, self.session)
        block = result['message']['content'][0]
        block.update(is_error=False, content=text)
        result['tool_use_result'] = {'exitCode': 0, 'stdout': text} if bash else {}
        self.deliver(result)

    def helper(self, kind):
        identity = self.call('Bash', {'command': self.command(kind)})
        if kind == 'phase1_receipts':
            text = json.dumps({'mode': 'initial_structure', 'structure_passed': True,
                'floors': 'pending', 'floor_acceptance_claimed': False,
                'summary': None, 'reason': None, 'findings': [], 'structural_checks': {},
                'native_initial_inputs': {'selection_sha256': 'a' * 64,
                    'full_sha256': 'b' * 64, 'receipt_sha256': 'c' * 64},
                'receipt_completion_policy': None})
        else:
            text = 'checked'
        self.success(identity, text=text)

    def initial_checks(self):
        for kind in ('chunk_check', 'source_scope'):
            self.helper(kind)
        for role in ('full', 'receipt'):
            identity = self.call('Write', {'file_path': self.selected.phase.paths[role],
                'content': 'software-only record'})
            self.success(identity, bash=False)
        for kind in ('full_schema', 'full_terms'):
            self.helper(kind)

    def original_failure(self):
        raw = self.rows[7]
        assert json.loads(raw)['message']['content'][0]['tool_use_id'] == 'stage_receipt'
        existing.deliver(self.selected, self.directory, raw)
        assert (self.directory / 'transcript.jsonl').read_bytes().splitlines(keepends=True)[-1] == raw


def test_admitted_failure_passes_real_trace_into_phase_and_allows_later_success(
        tmp_path, monkeypatch, kind):
    history = AdapterHistory(tmp_path, monkeypatch)
    history.initial_checks()
    selected = history.selected
    history.call('Bash', {'command': history.command(kind)}, identity='stage_receipt')
    history.original_failure()
    trace = history.traces[-1]
    assert type(trace) is observations.Trace
    assert trace.denial('stage_receipt') is None
    assert trace.settled('stage_receipt').call.tool_use_id == 'stage_receipt'
    assert trace.frames[trace.results['stage_receipt'][0]] == history.events[7]
    report = selected.phase.report()
    check = report['checks'][-1]
    assert selected.failure is None and report['problems'] == []
    assert check['helper'] == kind and type(check['exit_code']) is int and check['exit_code'] == 1
    assert check['stdout'] is None and check['status_basis'] == wire.FAILURE_STATUS_BASIS
    assert check['merged_output'] == history.events[7]['message']['content'][0]['content'].split('\n', 1)[1]
    assert kind not in report['current_checks'] and not report['phase1_sealed']
    assert report['pending_tool_ids'] == [] and history.seals == []
    history.helper(kind)
    repaired = selected.phase.report()
    assert selected.failure is None and repaired['problems'] == []
    assert kind in repaired['current_checks'] and repaired['checks'][-1]['exit_code'] == 0
    assert history.seals == (['seal_phase1'] if kind == 'phase1_receipts' else [])
    assert not selected.recorder_done and not selected.phase.report(complete=True)['passed']


test_admitted_failure_passes_real_trace_into_phase_and_allows_later_success = pytest.mark.parametrize(
    'kind', ['full_schema', 'phase1_receipts'])(
        test_admitted_failure_passes_real_trace_into_phase_and_allows_later_success)


def test_accept_annotation_without_parent_admission_stops_adapter_before_failure_credit(tmp_path, monkeypatch):
    history = AdapterHistory(tmp_path, monkeypatch)
    history.initial_checks()
    before = len(history.selected.phase.report()['checks'])
    history.call('Bash', {'command': history.command('full_schema')},
        identity='stage_receipt', admitted=False)
    with pytest.raises(existing.Stopped, match='admission'):
        history.original_failure()
    assert history.selected.failure
    assert len(history.selected.phase.report()['checks']) == before
    assert history.seals == [] and not history.selected.recorder_done


def test_failed_advance_never_enters_publication_settlement_and_stop_stays_sticky(tmp_path, monkeypatch):
    history = AdapterHistory(tmp_path, monkeypatch)
    attempted = []
    monkeypatch.setattr(capture, 'observe_advance_settled',
        lambda *a, **kw: attempted.append('unexpected publication settlement'))
    # The real selected spelling takes the adapter's advance branch. Its
    # surrounding callback authority is fabricated; no stage grant is claimed.
    history.call('Bash', {'command': history.selected.policy['native_shared_helpers']['advance']},
        identity='stage_receipt')
    with pytest.raises(existing.Stopped, match='advance helper failed'):
        history.original_failure()
    assert history.selected.failure and attempted == [] and history.seals == []
    assert history.selected.phase.report()['checks'] == []
    with pytest.raises(existing.Stopped, match='advance helper failed'):
        history.original_failure()
    assert attempted == [] and not history.selected.recorder_done


def test_live_recorder_failure_stops_before_provenance_read_or_completion(tmp_path, monkeypatch, output):
    selected, _, _, destination = existing.recorder_control(tmp_path, monkeypatch)
    text = None if output == 'retained' else '✓ ' + str(destination) + '\n'
    failed = failure_control('software-recorder', selected._observed_session, output=text)
    reads = []
    def forbidden_read(*args, **kwargs):
        reads.append(args)
        raise AssertionError('failed recorder must not read provenance as success')
    monkeypatch.setattr(evidence, 'read_regular', forbidden_read)
    with pytest.raises(existing.Stopped, match='recorder did not settle successfully'):
        existing.deliver(selected, tmp_path, c.canonical(failed) + b'\n')
    assert selected.failure and reads == []
    assert not selected.recorder_done and selected.recorder_identity is None
    assert selected._recorder_status is None
    with pytest.raises(existing.Stopped):
        existing.deliver(selected, tmp_path, c.canonical(failed) + b'\n')
    assert reads == [] and not selected.recorder_done


test_live_recorder_failure_stops_before_provenance_read_or_completion = pytest.mark.parametrize(
    'output', ['retained', 'success_looking'])(
        test_live_recorder_failure_stops_before_provenance_read_or_completion)


def test_saved_recorder_failure_never_receives_completion_or_status_credit(tmp_path, monkeypatch, output):
    prepared, recorder, block = existing.saved_recorder_control(tmp_path, monkeypatch)
    text = None if output == 'retained' else json.dumps({'checked': True, 'passed': True, 'findings': []})
    failed = failure_control(block['tool_use_id'], recorder['session_id'], output=text)
    prepared['events'][-1] = failed
    reads = []
    def forbidden_read(*args, **kwargs):
        reads.append(args)
        raise AssertionError('failed saved recorder must not credit provenance')
    prepared['snapshot'].read = forbidden_read
    report, final, done = saved_results._saved_draft(prepared, None)
    assert done is False and report['draft_gate_passed'] is False
    assert any('recorder failed' in problem for problem in report['problems'])
    assert 'recorder_status' not in report and reads == []


test_saved_recorder_failure_never_receives_completion_or_status_credit = pytest.mark.parametrize(
    'output', ['retained', 'success_looking'])(
        test_saved_recorder_failure_never_receives_completion_or_status_credit)
