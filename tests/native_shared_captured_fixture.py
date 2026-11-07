"""Synthetic immutable U3-C carriers with real stage and tool-observation joins.

These invented streams are not native execution or admitted execution authority.
The execution wire has the closed field roster, with explicitly synthetic values;
U3-D's verification, permission and runtime gates are deliberately not exercised.
"""
from copy import deepcopy
from dataclasses import asdict, replace

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as controller
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_observations as observed
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import typed_audit as typed
from tests import test_native_shared_stages as stages
from tests.test_native_shared_observations import SESSION, POLICY, events, initial, prefix
from tests.test_typed_audit import replies
from tests.utils.native_execution_carrier_v2 import execution_body


def v2_case(case):
    """Rebind the synthetic stage fixture to the explicit outer-v2 wire."""
    selection, execution, phase1, history = case
    body = execution_body(attempt_directory='/neutral/attempt')
    raw = c.canonical({'authority_version': 2,
        'controller_sources_sha256': controller.wire.CONTROLLER_SOURCES_SHA256,
        'registration': body})
    execution = replace(execution, session_id=SESSION,
        execution=stages.artifact('execution_capture', execution.execution.pin.path, raw))
    # Rebuild the initial immutable history; no old digest is retained after E changes.
    rows = [c.strict_json(item.raw) for item in history.records]
    rows[0]['payload']['execution'] = c.pin_dict(execution.execution.pin)
    empty = replace(history, records=(), journal=stages.artifact('journal', history.journal.pin.path,
        stage.journal_bytes(selection_sha256=selection.registration.pin.sha256,
            execution_sha256=execution.execution.pin.sha256, attempt_id=execution.attempt_id, records=())))
    records, journal = stage.append_records(selection, execution, empty,
        tuple((row['record_type'], c.canonical(row['payload'])) for row in rows))
    return selection, execution, phase1, stages.append(empty, records, journal)


def _events(tool, item, identity):
    native, parent, _ = events(tool, item.raw)
    inputs = {'file_path': item.pin.path}
    if tool == 'Write':
        inputs['content'] = item.raw.decode('utf-8')
    native[0]['message']['content'][0].update(id=identity, input=inputs)
    native[1]['request_id'] = identity + '-callback'
    native[1]['request']['input'].update(tool_use_id=identity, tool_input=deepcopy(inputs))
    native[-1]['message']['content'][0]['tool_use_id'] = identity
    metadata = native[-1]['tool_use_result']
    if tool == 'Read':
        metadata['file']['filePath'] = item.pin.path
    else:
        metadata['filePath'] = item.pin.path
        native[-1]['message']['content'][0]['content'] = 'File created successfully at: ' + item.pin.path
    parent[0]['request'] = deepcopy(native[1])
    parent[0]['response']['response']['request_id'] = identity + '-callback'
    return native, parent


def _prefix(role, rows):
    result = prefix(role, rows)
    return replace(result, path='/neutral/attempt/' + role + '.jsonl')


def _pool(execution, transcript, control):
    members = tuple(evidence.PoolMember(
        stages.artifact(item.stream, item.path, item.raw),
        c.canonical({'exists': True, 'regular': True, 'symlink': False, 'links': 1,
            'device': 0, 'inode': index + 1, 'size': item.bytes, 'mtime_ns': 0}))
        for index, item in enumerate((transcript, control)))
    return evidence.CapturePool(members, tuple((evidence.stream_id(
        execution.execution.pin.sha256, item.captured.pin.role, item.captured.pin.path), item.member_id)
        for item in members))


def join_response(case, decision, raw, *, mutation=None, streams=None):
    """Exercise actual complete Read, first Write and durable-prefix resolution.

    Every response is joined to that stage's complete request and unique path.
    Mutations affect actual raw frames before any Trace/observation is derived.
    """
    selection, execution, _, history = case
    response = stages.artifact('response', decision.response.path, raw)
    read_id, write_id = f'read-{decision.cursor.ordinal}', f'write-{decision.cursor.ordinal}'
    reads, read_parent = _events('Read', decision.request, read_id)
    writes, write_parent = _events('Write', response, write_id)
    if mutation == 'foreign_reply':
        writes[-1]['session_id'] = 'foreign-session'
    elif mutation == 'duplicate_request':
        reads.insert(1, deepcopy(reads[0]))
    elif mutation == 'spent_request':
        writes[-1]['tool_use_result']['type'] = 'update'
        writes[-1]['tool_use_result']['originalFile'] = 'already consumed'
    native, parent, runtime = initial()
    if streams is not None:
        native, parent = streams
    read_rows = native + reads
    intent_rows = read_rows + writes[:2]
    all_rows = read_rows + writes
    if mutation == 'reordered_callback':
        # Delivering the Read eventually is insufficient: both the Write
        # announcement and its callback preceded that delivery.
        intent_rows = native + reads[:2] + writes[:2] + reads[2:]
        all_rows = intent_rows + writes[2:]
    read_transcript = _prefix('transcript', read_rows)
    read_control = _prefix('control', parent + read_parent)
    intent_transcript = _prefix('transcript', intent_rows)
    full_transcript = _prefix('transcript', all_rows)
    full_control = _prefix('control', parent + read_parent + write_parent)
    read_trace = observed.Trace(read_transcript, read_control,
        session_id=SESSION, policy=POLICY, runtime=runtime)
    intent_trace = observed.Trace(intent_transcript, full_control,
        session_id=SESSION, policy=POLICY, runtime=runtime)
    full_trace = observed.Trace(full_transcript, full_control,
        session_id=SESSION, policy=POLICY, runtime=runtime)
    delivered = observed.complete_request_read(read_trace, read_trace.settled(read_id), decision.request)
    pending = intent_trace.request(write_id)
    # Use the same prefix as Write to compare raw event coordinates.
    capture._require_completed_read_before_write(pending, intent_trace.settled(read_id))
    written = observed.first_response_write(full_trace, full_trace.settled(write_id), response,
        intent_input_json=pending.input_json)
    pool = _pool(execution, full_transcript, full_control)
    ordinal = len(history.observations) + 2

    def saved(kind, payload, transcript, control):
        nonlocal ordinal
        raw = capture.observation_bytes(kind, selection, execution.execution.pin.sha256,
            execution.attempt_id, execution.session_id, transcript, control, payload)
        item = stages.artifact('observation', selection.role('observations_root') + f'/{ordinal:06d}.json', raw)
        ordinal += 1
        doc, captured_transcript, captured_control = capture.observation(item, selection, execution, pool)
        assert doc['payload'] == payload
        assert captured_transcript == transcript and captured_control == control
        return item

    read = saved('request_read', {'call': capture.call_document(delivered.call),
        'result': asdict(delivered.result), 'result_event': asdict(delivered.result_event),
        'request': c.pin_dict(decision.request.pin), 'history_sha256': history.journal.pin.sha256},
        read_transcript, read_control)
    intent = saved('response_intent', {'request': c.pin_dict(decision.request.pin),
        'response': asdict(decision.response), 'call': asdict(pending.call), 'callback': asdict(pending.callback),
        'tool_use_id': write_id, 'input_json': pending.input_json.decode('utf-8'),
        'history_sha256': history.journal.pin.sha256, 'read_observation': c.pin_dict(read.pin)},
        intent_transcript, full_control)
    wrote = saved('response_written', {'call': capture.call_document(written.call),
        'result': asdict(written.result), 'result_event': asdict(written.result_event),
        'response': c.pin_dict(response.pin), 'intent_observation': c.pin_dict(intent.pin),
        'history_sha256': history.journal.pin.sha256}, full_transcript, full_control)
    return response, (read, intent, wrote), (all_rows, parent + read_parent + write_parent)


class CapturedStages:
    """Real typed stage sequence, with invented raw evidence for each delivery."""
    def __init__(self, case):
        self.case = v2_case(case)
        self.joins = []
        self.streams = None

    def respond(self, raw, *, mutation=None):
        selection, execution, phase1, history = self.case
        decision = stage.prepare_next(*self.case)
        if decision.state == 'request_ready':
            history = stages.publish(history, decision)
            self.case = selection, execution, phase1, history
            decision = stage.prepare_next(*self.case)
        assert decision.state == 'awaiting_response'
        response, observations, streams = join_response(self.case, decision, raw,
            mutation=mutation, streams=self.streams)
        history = replace(history, artifacts=history.artifacts + (response,),
            observations=history.observations + observations)
        payload = {'cursor': asdict(decision.cursor),
            'request_sha256': c.strict_json(decision.request.raw, max_bytes=c.HARD_LIMITS['request_bytes'])['request_sha256'],
            'response': c.pin_dict(response.pin), 'read_observation': c.pin_dict(observations[0].pin),
            'response_observation': c.pin_dict(observations[-1].pin)}
        records, journal = stage.append_records(selection, execution, history,
            (('response_consumed', c.canonical(payload)),))
        consumed = stages.append(history, records, journal)
        transition = stage.check_response(selection, execution, phase1, consumed, decision.request.raw, raw)
        self.case = selection, execution, phase1, stages.append(consumed, transition.records_to_append,
            transition.predicted_journal, tuple(pub.artifact for pub in transition.publications))
        self.joins.append((decision, response, observations))
        self.streams = streams
        return transition

    def final_pool(self):
        """One final pair of streams must resolve every earlier observation."""
        assert self.streams is not None
        transcript = _prefix('transcript', self.streams[0])
        control = _prefix('control', self.streams[1])
        pool = _pool(self.case[1], transcript, control)
        previous = {'transcript': 0, 'control': 0}
        for _, _, observations in self.joins:
            for item in observations:
                _, current_transcript, current_control = capture.observation(item, self.case[0], self.case[1], pool)
                for current in (current_transcript, current_control):
                    assert current.bytes >= previous[current.stream]
                    previous[current.stream] = current.bytes
        assert previous == {'transcript': transcript.bytes, 'control': control.bytes}
        return pool

    def complete(self):
        assert self.respond(stages.receipt_answer(self.case)).disposition == 'checked'
        wait = stage.prepare_next(*self.case)
        assert wait.state == 'await_core'
        self.case = (*self.case[:3], stages.publish(self.case[3], wait))
        self.case = stages.add_core(self.case)
        while True:
            decision = stage.prepare_next(*self.case)
            if decision.state == 'assembly_complete':
                return decision.completion
            assert decision.state == 'request_ready'
            packet = stage._Replay(*self.case).run().packet
            workers, omission, delta, _ = replies(packet, 2)
            raw = workers[decision.cursor.target_id] if decision.cursor.kind == 'worker' else c.canonical(
                omission if decision.cursor.kind == 'omission' else delta)
            assert self.respond(raw).disposition == 'checked'
