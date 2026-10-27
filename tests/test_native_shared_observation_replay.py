"""Real tiny-schema captures retain every observation check during local reuse.

Synthetic native frames provide Read/Write/advance observations. Capture, pure
stage reconstruction and observation checks stay real; no transport/helper runs.
The literal parent function is the complete-return/refusal parity oracle.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_stage as stage
from tests.test_native_shared_phase_replay import (
    PhaseFixture, offline, native_spec, basic_native_spec, basic_declaration,
    declaration, started, execution, bound)

_PARENT = 'def _checked_observations(run):\n    """Validate raw joins and current-request chronology, not saved success flags."""\n    previous = {\'transcript\': 0, \'control\': 0}\n    seen_reads, seen_intents, seen_writes, seen_advances = {}, {}, set(), set()\n    checked = []\n    for index, artifact in enumerate(run.observations):\n        doc, transcript, control = observation(artifact, run.selection, run.binding, run.pool)\n        for prefix in (transcript, control):\n            if prefix.bytes < previous[prefix.stream]:\n                raise ValueError(\'durable observation prefixes move backwards\')\n            previous[prefix.stream] = prefix.bytes\n        kind, payload = doc[\'observation_type\'], doc[\'payload\']\n        if (index == 0) != (kind == \'initialized\'):\n            raise ValueError(\'durable observations lack one first actual initialization\')\n        trace = run.trace(transcript, control)\n        if kind == \'initialized\':\n            if artifact != run.binding.init_observation:\n                raise ValueError(\'initial observation differs from bound session\')\n        elif kind in (\'request_read\', \'response_written\', \'advance_settled\'):\n            call = _call(payload[\'call\'])\n            actual = trace.settled(call.tool_use_id)\n            if (actual.call != call or asdict(actual.result) != payload[\'result\']\n                    or asdict(actual.result_event) != payload[\'result_event\']):\n                raise ValueError(\'settled observation does not match actual raw tool events\')\n            if kind == \'request_read\':\n                request = run.reader.pinned(payload[\'request\'])\n                current = _decision_at(run, payload[\'history_sha256\'])\n                if current.state != \'awaiting_response\' or current.request != request:\n                    raise ValueError(\'Read observation names a stale or unpublished request\')\n                observed.complete_request_read(trace, actual, request)\n                if call.tool_use_id in seen_reads or request.pin.path in {row[1].pin.path for row in seen_reads.values()}:\n                    raise ValueError(\'current request has duplicate delivered-read authority\')\n                seen_reads[call.tool_use_id] = (artifact, request, current)\n            elif kind == \'response_written\':\n                intent = seen_intents.get(payload[\'intent_observation\'][\'sha256\'])\n                if intent is None or c.pin_dict(intent[0].pin) != payload[\'intent_observation\']:\n                    raise ValueError(\'response result lacks the preceding exact Write intent\')\n                response = run.reader.pinned(payload[\'response\'])\n                intent_doc = intent[1]\n                if (call.tool_use_id != intent_doc[\'tool_use_id\'] or call.input_json.decode(\'utf-8\') != intent_doc[\'input_json\']\n                        or payload[\'history_sha256\'] != intent_doc[\'history_sha256\']\n                        or response.pin.path != intent_doc[\'response\'][\'path\'] or response.pin.path in seen_writes):\n                    raise ValueError(\'response was replaced, retried or moved to another stage\')\n                observed.first_response_write(trace, actual, response, intent_input_json=call.input_json)\n                seen_writes.add(response.pin.path)\n            else:\n                result = payload[\'advance_result\']\n                if result.get(\'advance_tool_use_id\') != call.tool_use_id or call.tool_use_id not in seen_advances:\n                    raise ValueError(\'advance settlement lacks actual earlier selected admission\')\n                observed.helper_result(trace, actual, result)\n                _history_prefix(run, result[\'before_history_sha256\'])\n                after = _decision_at(run, result[\'after_history_sha256\'])\n                if after.state != result[\'state\']:\n                    raise ValueError(\'advance settlement differs from actual post-publication state\')\n                for pin in result[\'publications\']:\n                    if pin.get(\'role\') == \'journal\':\n                        actual = _history_prefix(run, pin[\'sha256\']).journal\n                        if c.pin_dict(actual.pin) != pin:\n                            raise ValueError(\'advance acknowledgement names another journal version\')\n                    else:\n                        run.reader.pinned(pin)\n        elif kind == \'response_intent\':\n            current = _decision_at(run, payload[\'history_sha256\'])\n            request = trace.request(payload[\'tool_use_id\'])\n            if (asdict(request.call) != payload[\'call\'] or asdict(request.callback) != payload[\'callback\']\n                    or request.tool_name != \'Write\' or request.input_json.decode(\'utf-8\') != payload[\'input_json\']\n                    or current.state != \'awaiting_response\' or current.request is None or current.response is None\n                    or c.pin_dict(current.request.pin) != payload[\'request\'] or asdict(current.response) != payload[\'response\']):\n                raise ValueError(\'Write intent differs from actual current request/callback\')\n            reads = [row for row in seen_reads.values() if c.pin_dict(row[0].pin) == payload[\'read_observation\']]\n            if len(reads) != 1 or reads[0][1] != current.request or current.response.path in {v[1][\'response\'][\'path\'] for v in seen_intents.values()}:\n                raise ValueError(\'Write intent reuses a stale Read or spent response destination\')\n            inputs = _document(request.input_json, \'Write intent\')\n            if (set(inputs) != {\'file_path\', \'content\'} or inputs[\'file_path\'] != current.response.path\n                    or type(inputs[\'content\']) is not str or not inputs[\'content\']\n                    or len(inputs[\'content\'].encode(\'utf-8\')) > current.response.max_bytes):\n                raise ValueError(\'Write intent exceeds the exact response contract\')\n            read_call = _call(c.strict_json(reads[0][0].raw)[\'payload\'][\'call\'])\n            _require_completed_read_before_write(request, trace.settled(read_call.tool_use_id))\n            seen_intents[artifact.pin.sha256] = (artifact, payload)\n        elif kind == \'advance_admitted\':\n            call = _call(payload[\'call\'])\n            actual = trace.current_advance(call.tool_use_id, run.composition[\'policy\'][\'native_shared_helpers\'][\'advance\'])\n            if actual != call or call.tool_use_id in seen_advances:\n                raise ValueError(\'advance admission repeats or differs from the actual pending callback\')\n            _history_prefix(run, payload[\'before_history_sha256\'])\n            seen_advances.add(call.tool_use_id)\n        elif kind in (\'phase1_sealed\', \'core_sealed\'):\n            if type(payload[\'helper_calls\']) is not list or not payload[\'helper_calls\']:\n                raise ValueError(\'seal lacks actual settled helper identities\')\n            for identity in payload[\'helper_calls\']:\n                trace.settled(identity)\n            names = (\'full\', \'original_receipt\') if kind == \'phase1_sealed\' else (\'core\',)\n            for name in names:\n                run.reader.pinned(payload[name])\n        else:\n            raise ValueError(\'unsupported durable native observation\')\n        checked.append((artifact, doc, transcript, control))\n    return tuple(checked)'
_PARENT_SHA = 'ca510704b67508643f6e745aa934d4c1df8db61a722f62f5df071d29e056de3d'


def parent_check():
    assert c.sha(_PARENT.encode()) == _PARENT_SHA
    namespace = dict(capture.__dict__)
    exec(compile(_PARENT, '<checked observations at 7ba1203>', 'exec'), namespace)
    return namespace['_checked_observations']


class WorkerFixture(PhaseFixture):
    def begin(self, tool, inputs):
        self.last_call = super().begin(tool, inputs)
        return self.last_call

    def worker_observations(self):
        identity, result = self.last_call
        invocation = capture.capture_stage(self.path)
        proposal = stage.prepare_next(invocation.selection, invocation.execution,
                                      invocation.phase1, invocation.history)
        published = capture.publish_stage(invocation, proposal)
        assert published['state'] == 'awaiting_response'
        self.settle(result, published)
        capture.observe_advance_settled(self.load(), identity)
        decision = self.load().decision()
        request = decision.request
        identity, result = self.begin('Read', {'file_path': request.pin.path})
        lines = request.raw.decode().split('\n')
        result['message']['content'][0]['content'] = '\n'.join(
            f'{number}\t{line}' for number, line in enumerate(lines, 1))
        result['tool_use_result'] = {'type': 'text', 'file': {
            'filePath': request.pin.path, 'content': request.raw.decode(),
            'numLines': len(lines), 'startLine': 1,
            'totalLines': len(lines)}}
        self.native.append(result); self.streams()
        capture.observe_request_read(self.load(), identity)
        response = b'{"findings":[]}'
        identity, result = self.begin('Write', {'file_path': decision.response.path,
                                               'content': response.decode()})
        grant = self.parent.pop(); self.streams()
        capture.observe_response_intent(self.load(), identity)
        Path(decision.response.path).parent.mkdir(parents=True, exist_ok=True)
        Path(decision.response.path).write_bytes(response)
        self.parent.append(grant)
        result['tool_use_result'] = {'type': 'create', 'filePath': decision.response.path,
                                    'content': response.decode()}
        result['message']['content'][0]['content'] = 'File created successfully at: ' + decision.response.path
        self.native.append(result); self.streams()
        capture.observe_response_written(self.load(), identity)
        return self.load()


@pytest.fixture
def worker_run(started):
    return WorkerFixture(started).worker_observations()


def test_complete_observation_return_matches_parent_and_rebuilds_packet_once(worker_run, monkeypatch):
    calls = []; packets = []; owner = ['parent']
    original = capture._decision_at; packet = stage._Replay._packet
    def counted(run, digest):
        answer = original(run, digest)
        calls.append((owner[0], digest, answer))
        return answer
    def counted_packet(*args, **kwargs):
        answer = packet(*args, **kwargs); packets.append(owner[0]); return answer
    monkeypatch.setattr(capture, '_decision_at', counted)
    monkeypatch.setattr(stage._Replay, '_packet', counted_packet)
    expected = parent_check()(worker_run)
    owner[0] = 'candidate'; actual = capture._checked_observations(worker_run)
    assert actual == expected
    assert packets.count('parent') == 3 and packets.count('candidate') == 1
    parent = [(digest, answer) for who, digest, answer in calls if who == 'parent']
    reduced = [(digest, answer) for who, digest, answer in calls if who == 'candidate']
    assert len(parent) == 4 and len(reduced) == 2
    assert dict(parent) == dict(reduced)
    # Full immutable decisions are safe to share only inside this invocation.
    answer = reduced[-1][1]
    with pytest.raises(FrozenInstanceError): answer.state = 'failed'
    with pytest.raises(FrozenInstanceError): answer.request.raw = b'changed'
    owner[0] = 'second'; assert capture._checked_observations(worker_run) == expected
    assert len([row for row in calls if row[0] == 'second']) == 2


def rehashed_observation(run, index, change):
    original = run.observations[index]; value = c.strict_json(original.raw)
    change(value['payload'])
    raw = c.canonical(value)
    replacement = c.CapturedArtifact(replace(original.pin, bytes=len(raw), sha256=c.sha(raw)), raw)
    observations = tuple(replacement if item == original else item for item in run.observations)
    members = []
    for member in run.pool.members:
        if member.captured == original:
            metadata = c.strict_json(member.metadata_json); metadata['size'] = len(raw)
            member = evidence.PoolMember(replacement, c.canonical(metadata))
        members.append(member)
    pool = evidence.CapturePool(tuple(members), run.pool.stream_bindings)
    return replace(run, observations=observations, pool=pool,
        history=replace(run.history, observations=observations),
        reader=capture._Reader(run.selection, pool=pool))


def test_rehashed_intent_still_checks_every_join_after_cached_read(worker_run):
    for mutation in ('request-pin', 'response-destination', 'read-reference',
                     'callback-line', 'history-prefix'):
        index = next(i for i, item in enumerate(worker_run.observations)
                     if c.strict_json(item.raw)['observation_type'] == 'response_intent')
        def change(payload):
            if mutation == 'request-pin': payload['request']['sha256'] = 'f' * 64
            elif mutation == 'response-destination': payload['response']['path'] += '.foreign'
            elif mutation == 'read-reference': payload['read_observation']['sha256'] = 'f' * 64
            elif mutation == 'callback-line': payload['callback']['line'] -= 1
            else: payload['history_sha256'] = 'f' * 64
        bad = rehashed_observation(worker_run, index, change)
        messages = []
        for check in (parent_check(), capture._checked_observations):
            with pytest.raises(ValueError) as exc: check(bad)
            messages.append(str(exc.value))
        assert messages[0] == messages[1]


def test_fresh_invocation_does_not_reuse_a_previous_success(worker_run, monkeypatch):
    capture._checked_observations(worker_run)
    def refused(*args): raise ValueError('fresh reconstruction refused')
    monkeypatch.setattr(capture, '_decision_at', refused)
    for _ in range(2):
        with pytest.raises(ValueError, match='fresh reconstruction refused'):
            capture._checked_observations(worker_run)
