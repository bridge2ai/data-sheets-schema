"""PR6302 production startup controls from real round-2 bytes, 2026-11-22.

All seven retained traces omit the optional UI frame. The adapter admission
scaffold and runtime declaration are explicitly software fixtures; original
native/control rows remain unchanged. These controls exercise production
readers, not probe qualification, native execution or production admission.
"""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_observations as observations
from data_sheets_schema import native_wire_2_1_325 as wire
from tests import test_native_production_wire_adapter_2_1_325 as adapter_controls


prohibit_transports = adapter_controls.prohibit_transports
PACK = Path(__file__).parent / 'fixtures/native_permission_2_1_325/round2_frontmatter.json'
TRACES = ('settled', 'stop-source_write', 'stop-sealed_request_write',
          'stop-helper_owned_write', 'stop-outside_response_write',
          'stop-stale_response_write', 'stop-future_response_write')


def retained(name):
    """Decode the original records; never infer or add a missing native row."""
    pack = json.loads(PACK.read_bytes())
    trace = pack['traces'][name]
    assert trace['qualification_expected'] == 'refuse'

    def decode(path):
        record = trace['files'][path]
        assert record['encoding'] == 'base64'
        raw = base64.b64decode(record['raw_base64'], validate=True)
        assert type(record['decoded_bytes']) is int and len(raw) == record['decoded_bytes']
        assert hashlib.sha256(raw).hexdigest() == record['decoded_sha256']
        return raw

    rows = decode('transcript.jsonl').splitlines(keepends=True)
    controls = decode('control.jsonl').splitlines(keepends=True)
    events = [json.loads(row) for row in rows]
    assert events[0]['type'] == 'control_response'
    assert (events[1]['type'], events[1]['subtype']) == ('system', 'init')
    assert not any(event.get('subtype') == 'ui_invalidate' for event in events)
    assert decode('stdout.unprocessed') == b''
    policy = json.loads(decode('evidence_root/projection.json'))['probe_policy']
    executable = json.loads(decode('launch.before.json'))['executable']
    init = events[1]
    runtime = {'executable': executable, 'model': init['model'], 'auxiliary_models': [],
               'auth': {'expected_api_key_source': init['apiKeySource']}}
    assert wire.profile(runtime)
    return rows, events, controls, policy, runtime


def adapter(tmp_path, monkeypatch, name):
    value = retained(name)
    monkeypatch.setattr(adapter_controls, 'retained', lambda: deepcopy(value))
    return adapter_controls.adapter(tmp_path, monkeypatch)


def prefix(stream, rows):
    raw = b''.join(rows)
    assert raw.endswith(b'\n')
    return c.EvidencePrefix(stream, '/software-only/' + stream, raw,
        len(raw), c.sha(raw), len(raw.split(b'\n')) - 1)


def test_real_round2_absent_prefix_keeps_adapter_and_phase_endpoints(tmp_path, monkeypatch, name):
    selected, rows, events, initialized = adapter(tmp_path, monkeypatch, name)
    for raw in rows[:2]:
        adapter_controls.deliver(selected, tmp_path, raw)
    native = selected._stream_prefixes['transcript']
    assert native.raw == (tmp_path / 'transcript.jsonl').read_bytes() == b''.join(rows[:2])
    assert native.lines == 2 and native.bytes == sum(map(len, rows[:2]))
    assert selected._initialized and selected._prefix_session is None
    assert selected._native_event_count == selected.phase._index == 2
    assert selected.phase._session == events[1]['session_id']
    assert len(initialized) == 1
    session, sent, ack, init = initialized[0]
    assert session == events[1]['session_id']
    assert sent.stream == 'control' and sent.line == 1
    assert ack.stream == init.stream == 'transcript'
    assert (ack.line, init.line) == (1, 2)
    assert ack == observations.reference(native, 1)
    assert init == observations.reference(native, 2)
    report = selected.phase.report()
    assert report['passed'] and report['checks'] == [] and report['current_checks'] == []
    assert not report['phase1_sealed'] and not report['core_sealed']
    assert not selected.phase.report(complete=True)['passed']


test_real_round2_absent_prefix_keeps_adapter_and_phase_endpoints = pytest.mark.parametrize(
    'name', TRACES)(test_real_round2_absent_prefix_keeps_adapter_and_phase_endpoints)


def test_real_round2_first_call_callback_keep_physical_references_without_admission(name):
    rows, events, controls, policy, runtime = retained(name)
    transcript, control = prefix('transcript', rows[:4]), prefix('control', controls[:2])
    session = events[1]['session_id']
    trace = observations.Trace(transcript, control, session_id=session, policy=policy, runtime=runtime)
    calls = [(index, item) for index, item in enumerate(events[2]['message']['content'])
             if item.get('type') == 'tool_use']
    assert len(calls) == 1
    offset, call = calls[0]
    identity = call['id']
    request = trace.request(identity)
    assert request.call == observations.reference(transcript, 3, offset)
    assert request.callback == observations.reference(transcript, 4)
    assert request.session_id == session and request.tool_name == call['name']
    assert request.input_json == c.canonical(call['input'])
    assert trace.transcript.raw == b''.join(rows[:4])
    assert trace.control.raw == b''.join(controls[:2])
    assert trace.pending() == (identity,) and trace.results == {} and trace.decisions == {}
    with pytest.raises(ValueError, match='admission'):
        trace.admitted(identity)
    with pytest.raises(ValueError, match='admission'):
        trace.settled(identity)


test_real_round2_first_call_callback_keep_physical_references_without_admission = pytest.mark.parametrize(
    'name', TRACES)(test_real_round2_first_call_callback_keep_physical_references_without_admission)


def test_absent_prefix_does_not_permit_effects_or_incomplete_initialization(tmp_path, monkeypatch, mutation):
    selected, rows, events, initialized = adapter(tmp_path, monkeypatch, 'settled')
    if mutation == 'effect_first':
        attempted = [rows[2]]
    elif mutation == 'effect_before_init':
        attempted = [rows[0], rows[2]]
    elif mutation == 'missing_ack':
        attempted = [rows[1]]
    else:
        attempted = [rows[0], rows[0], rows[1]]
    with pytest.raises(adapter_controls.Stopped):
        for raw in attempted:
            adapter_controls.deliver(selected, tmp_path, raw)
    assert selected.failure and not selected._initialized and initialized == []
    assert selected.phase.report()['checks'] == [] and not selected.recorder_done
    with pytest.raises(adapter_controls.Stopped):
        adapter_controls.deliver(selected, tmp_path, rows[1])
    assert initialized == []


test_absent_prefix_does_not_permit_effects_or_incomplete_initialization = pytest.mark.parametrize(
    'mutation', ['effect_first', 'effect_before_init', 'missing_ack', 'duplicate_ack'])(
        test_absent_prefix_does_not_permit_effects_or_incomplete_initialization)


def test_absent_prefix_cannot_hide_mutation_of_observed_ack_bytes(tmp_path, monkeypatch):
    selected, rows, events, initialized = adapter(tmp_path, monkeypatch, 'settled')
    adapter_controls.deliver(selected, tmp_path, rows[0])
    changed = rows[0].replace(b'd4d_initialize_v1', b'd4d_initialize_v2')
    assert changed != rows[0] and len(changed) == len(rows[0])
    (tmp_path / 'transcript.jsonl').write_bytes(changed)
    with pytest.raises(adapter_controls.Stopped, match='changed'):
        adapter_controls.deliver(selected, tmp_path, rows[1])
    assert selected.failure and not selected._initialized and initialized == []
