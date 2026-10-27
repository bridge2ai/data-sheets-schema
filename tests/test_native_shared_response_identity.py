"""Synthetic settled events join the real response observer to real stage replay.

Only artifact loading and durable publication are adapted to in-memory captures.
The Read/Write evidence checks, effect classifier, request builder, serializers,
stage replay and receipt checker are the production implementations. These are
component regressions, not evidence of an observed native session.
"""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_effects as effects
from data_sheets_schema import native_shared_stage as stage
from tests.test_native_shared_observations import POLICY, events, initial, prefix
from tests.test_native_shared_stages import append, artifact, case, publish, receipt_answer
from tests.test_typed_audit import supplied


class SettledResponse:
    def __init__(self, case, monkeypatch, answer):
        selection, execution, phase1, history = case
        proposal = stage.prepare_next(*case)
        assert proposal.state == 'request_ready'
        history = publish(history, proposal)
        decision = stage.prepare_next(selection, execution, phase1, history)
        assert decision.state == 'awaiting_response'
        self.request = decision.request
        self.response = artifact('response', decision.response.path, answer)
        self.before_consumption = None
        policy = deepcopy(POLICY)
        policy['readonly_lookups']['inputs'] = []
        policy['native_shared_helpers'] = {'advance':
            '/neutral/python -m data_sheets_schema.native_shared_stage advance --registration /neutral/selection.json'}
        self.native, self.parent, runtime = initial()
        self.native[1]['session_id'] = execution.session_id
        self.parent[0]['policy_sha256'] = c.sha(json.dumps(policy, sort_keys=True, separators=(',', ':')).encode())
        composition = {'policy': policy, 'policy_sha256': c.sha(c.canonical(policy))}
        self.run = capture._CapturedRun(selection, {'runtime': runtime}, composition,
            SimpleNamespace(_agentic_artifact_paths={'receipt': '/neutral/original-receipt-output'}),
            SimpleNamespace(read=self.read), None, prefix('transcript', self.native),
            prefix('control', self.parent), execution, history, (), phase1)
        monkeypatch.setattr(capture, '_persist_observation', self.persist)
        monkeypatch.setattr(capture, '_append', self.append_consumed)

    def read(self, role, path):
        assert (role, path) == (self.response.pin.role, self.response.pin.path)
        return self.response

    def persist(self, run, kind, payload):
        assert run is self.run
        raw = capture.observation_bytes(kind, run.selection, run.binding.execution.pin.sha256,
            run.binding.attempt_id, run.binding.session_id, run.transcript, run.control, payload)
        # The carrier fixture already reserves observations 0/1 for init/seal.
        item = artifact('observation', run.selection.role('observations_root') +
                        f'/{len(run.observations) + 2:06d}.json', raw)
        run.observations += (item,)
        run.history = replace(run.history, observations=run.observations)
        return item

    def append_consumed(self, selection, execution, history, kind, payload):
        assert selection is self.run.selection and execution is self.run.binding
        assert history is self.run.history and kind == 'response_consumed'
        history = replace(history, artifacts=history.artifacts + (self.response,))
        self.before_consumption = history
        records, journal = stage.append_records(selection, execution, history, ((kind, c.canonical(payload)),))
        self.run.history = append(history, records, journal)

    def frames(self, tool, identity, item):
        native, parent, _ = events(tool, item.raw)
        call, callback, result = native
        call['session_id'] = result['session_id'] = self.run.binding.session_id
        block = call['message']['content'][0]
        block['id'] = identity
        block['input']['file_path'] = item.pin.path
        callback['request_id'] = 'callback-' + identity
        callback['request']['input'].update(tool_use_id=identity, tool_input=deepcopy(block['input']))
        result['message']['content'][0]['tool_use_id'] = identity
        if tool == 'Read':
            result['tool_use_result']['file']['filePath'] = item.pin.path
        else:
            result['tool_use_result']['filePath'] = item.pin.path
            result['message']['content'][0]['content'] = 'File created successfully at: ' + item.pin.path
        parent[0]['request'] = deepcopy(callback)
        parent[0]['response']['response']['request_id'] = callback['request_id']
        return native, parent

    def extend(self, native, parent):
        self.native.extend(native)
        self.parent.extend(parent)
        self.run.transcript = prefix('transcript', self.native)
        self.run.control = prefix('control', self.parent)

    def whole_read(self, identity):
        self.extend(*self.frames('Read', identity, self.request))
        capture.observe_request_read(self.run, identity)

    def consume(self):
        self.whole_read('request-read')
        native, parent = self.frames('Write', 'response-write', self.response)
        self.extend(native[:2], [])
        capture.observe_response_intent(self.run, 'response-write')
        self.extend(native[2:], parent)
        capture.observe_response_written(self.run, 'response-write')

    def retain(self, root):
        root.mkdir()
        for name, raw in (('request.json', self.request.raw), ('response.bin', self.response.raw),
                          ('transcript.jsonl', self.run.transcript.raw), ('control.jsonl', self.run.control.raw),
                          ('consumed.json', self.run.history.records[-1].raw), ('journal.json', self.run.history.journal.raw)):
            (root / name).write_bytes(raw)
        for index, item in enumerate(self.run.observations):
            (root / f'observation-{index}.json').write_bytes(item.raw)
        (root / 'identities.json').write_bytes(c.canonical({
            'request_artifact': c.pin_dict(self.request.pin),
            'semantic_request_sha256': c.strict_json(self.request.raw)['request_sha256'],
            'response': c.pin_dict(self.response.pin)}))


def assert_spent(value):
    # New Read credit at the consumed journal cannot mask a missing spent join.
    value.whole_read('current-history-reread')
    view = capture.current_effect_view(value.run)
    consumed = c.strict_json(value.run.history.records[-1].raw)['payload']
    assert view.request_read_observation_sha256 == value.run.observations[-1].pin.sha256
    assert view.response_intent_observation_sha256 == consumed['response_observation']['sha256']
    classification, basis = effects.classify_effect(view, tool_name='Write',
        tool_input={'file_path': value.response.pin.path, 'content': value.response.raw.decode()})
    assert (classification, basis) == ('not_prescribed',
        'first response intent is already consumed; no replacement or retry')


@pytest.mark.parametrize('malformed', [False, True], ids=['valid', 'malformed-first-answer'])
def test_actual_observer_consumption_replays_and_remains_spent(case, monkeypatch, tmp_path, malformed):
    value = SettledResponse(case, monkeypatch, b'{' if malformed else receipt_answer(case))
    original_request = value.request
    value.consume()
    value.retain(tmp_path / 'observed-consumption')
    # This actual consumer is the retained BEFORE failure at #4440.
    current = value.run.decision()
    assert current.state == 'awaiting_response' and current.request == original_request
    semantic = c.strict_json(original_request.raw)['request_sha256']
    assert semantic != original_request.pin.sha256
    consumed = c.strict_json(value.run.history.records[-1].raw)['payload']
    assert consumed['request_sha256'] == semantic
    assert consumed['response'] == c.pin_dict(value.response.pin)
    admitted = c.strict_json(value.before_consumption.records[-1].raw)['payload']
    assert admitted['request'] == c.pin_dict(original_request.pin)
    for item in value.run.observations[:2]:
        assert c.strict_json(item.raw)['payload']['request'] == c.pin_dict(original_request.pin)
    assert_spent(value)
    run = value.run
    transition = stage.check_response(run.selection, run.binding, run.phase1, run.history,
                                      original_request.raw, value.response.raw)
    assert transition.disposition == ('failed' if malformed else 'checked')
    assert transition.request_sha256 == semantic and transition.first_response == value.response
    payload = c.strict_json(transition.records_to_append[-1].raw)['payload']
    assert payload['request_sha256'] == semantic and payload['response_sha256'] == value.response.pin.sha256
    run.history = append(run.history, transition.records_to_append, transition.predicted_journal,
                         tuple(pub.artifact for pub in transition.publications))
    assert run.decision().state == ('failed' if malformed else 'await_core')
    view = capture.current_effect_view(run)
    classification, basis = effects.classify_effect(view, tool_name='Write',
        tool_input={'file_path': value.response.pin.path, 'content': value.response.raw.decode()})
    assert classification == 'not_prescribed'
    if malformed:
        assert basis == 'selected stage failure is terminal'
    (tmp_path / 'final-transition.json').write_bytes(transition.records_to_append[-1].raw)


@pytest.mark.parametrize('mutation', ['artifact-hash', 'other-payload', 'foreign-cursor'])
def test_rehashed_consumption_cannot_substitute_request_identity(case, monkeypatch, tmp_path, mutation):
    value = SettledResponse(case, monkeypatch, receipt_answer(case))
    value.consume()
    assert value.run.decision().state == 'awaiting_response'
    payload = c.strict_json(value.run.history.records[-1].raw)['payload']
    if mutation == 'artifact-hash':
        payload['request_sha256'] = value.request.pin.sha256
    elif mutation == 'other-payload':
        other = deepcopy(c.strict_json(value.request.raw)['payload'])
        other['selection_sha256'] = 'f' * 64
        payload['request_sha256'] = c.sha(c.canonical(other))
    else:
        payload['cursor']['ordinal'] += 1
    records, journal = stage.append_records(value.run.selection, value.run.binding,
        value.before_consumption, (('response_consumed', c.canonical(payload)),))
    value.run.history = append(value.before_consumption, records, journal)
    value.retain(tmp_path / 'rehashed-refusal')
    # Both record/journal hashes are valid; refusal must reach the stage join.
    stage._history(value.run.selection, value.run.binding, value.run.history)
    with pytest.raises(ValueError, match='native consumed response belongs to another stage or complete request'):
        value.run.decision()
