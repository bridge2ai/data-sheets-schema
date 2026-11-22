"""PR6302 A2-SOURCE-1: real Write rows and adversarial reader controls.

2026-11-22. Original frames, parent decisions and response file bytes are retained
losslessly. Mutations and legacy bare messages are explicitly software controls.
These tests exercise readers only, never native execution or run qualification.
"""

import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_observations as observations
from data_sheets_schema import native_shared_permissions as permissions
from data_sheets_schema import native_wire_2_1_325 as wire


PACK = Path(__file__).parent / 'fixtures/native_permission_2_1_325/round3_write_results.json'
WRITES = (
    ('response_receipt_write', 14, '49c78aff165b869749321f033642a2db8640cb2de475e71d91fbc17c6996104e'),
    ('response_worker_write', 23, 'db2e4d2ec3d8b9103ec1cf743d2c6d03557d667f0aef258c8b103983b7ac5c49'),
    ('response_omission_write', 32, 'fe620ed788cb52e674dc82921cb9466a3179f524000ebe321c99a8d2e3c9976d'),
    ('response_integration_write', 41, '47d6aa3bdcc21f3209a05a1174124a056205132f42a6cf3e8e808591a12f04b5'),
)
READERS = ('permission_result', 'production_observation')


def prohibit_transports(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('offline Write control attempted a process or transport')
    for name in ('Popen', 'run', 'check_output'):
        monkeypatch.setattr(subprocess, name, blocked)
    monkeypatch.setattr(socket.socket, 'connect', blocked)


prohibit_transports = pytest.fixture(autouse=True)(prohibit_transports)


def decode(record):
    assert record['encoding'] == 'base64'
    raw = base64.b64decode(record['raw_base64'], validate=True)
    assert type(record['decoded_bytes']) is int and len(raw) == record['decoded_bytes']
    assert hashlib.sha256(raw).hexdigest() == record['decoded_sha256']
    return raw


def retained():
    pack = json.loads(PACK.read_bytes())
    files = {name: decode(record) for name, record in pack['files'].items()}
    native = [row + b'\n' for row in files['transcript.jsonl'].split(b'\n')[:-1]]
    control = [row + b'\n' for row in files['control.jsonl'].split(b'\n')[:-1]]
    assert b''.join(native) == files['transcript.jsonl']
    assert b''.join(control) == files['control.jsonl']
    events = [json.loads(row) for row in native]
    init = next(row for row in events if row.get('type') == 'system' and row.get('subtype') == 'init')
    runtime = {'executable': json.loads(files['launch.before.json'])['executable'],
               'model': init['model'], 'auxiliary_models': [],
               'auth': {'expected_api_key_source': init['apiKeySource']}}
    policy = json.loads(files['evidence_root/projection.json'])['probe_policy']
    assert wire.profile(runtime)
    return pack, native, control, policy, runtime, init['session_id']


def prefix(stream, raw):
    assert raw.endswith(b'\n')
    return c.EvidencePrefix(stream, '/offline-retained/' + stream, raw,
                            len(raw), c.sha(raw), len(raw.split(b'\n')) - 1)


def context(name=WRITES[0][0]):
    pack, native, control, policy, runtime, session = retained()
    record = pack['writes'][name]
    call = json.loads(decode(record['call']))['message']['content'][0]
    event = json.loads(decode(record['result']))
    raw = decode(record['response'])
    response = c.CapturedArtifact(c.ArtifactPin('response',
        record['response']['original_path'], len(raw), c.sha(raw)), raw)
    assert call['input'] == {'file_path': response.pin.path, 'content': raw.decode('utf-8')}
    return {'record': record, 'native': native, 'control': control,
            'policy': policy, 'runtime': runtime, 'session': session,
            'call': call, 'event': event, 'response': response}


def observed_trace(value, event, runtime):
    """Preserve genuine prefixes; only a selected mutated result is re-encoded."""
    number = value['record']['result']['physical_line']
    native = value['native'][:number]
    if c.canonical(event) != c.canonical(value['event']):
        native[-1] = c.canonical(event) + b'\n'
    decision_line = value['record']['decision']['physical_line']
    return observations.Trace(prefix('transcript', b''.join(native)),
        prefix('control', b''.join(value['control'][:decision_line])),
        session_id=value['session'], policy=value['policy'], runtime=runtime)


def read_result(reader, value, event, runtime):
    call = value['call']
    if reader == 'permission_result':
        case = {'id': call['id'], 'tool': 'Write', 'mode': 'allowed', 'input': call['input']}
        expected = {} if runtime is None else {'runtime': runtime}
        permissions._tool_result(event, case, expected, None, None, value['session'], b'')
        return None
    trace = observed_trace(value, event, runtime)
    evidence = trace.settled(call['id'])
    assert evidence.call.call.line == value['record']['call']['physical_line']
    assert evidence.call.callback.line == value['record']['callback']['physical_line']
    assert evidence.call.admission.line == value['record']['decision']['physical_line']
    assert evidence.result.line == value['record']['result']['physical_line']
    assert observations.first_response_write(trace, evidence, value['response'],
        intent_input_json=c.canonical(call['input'])) == evidence
    return trace


def test_lossless_write_pack_has_original_frames_and_independent_file_bytes():
    pack, native, control, _, _, _ = retained()
    assert pack['kind'] == 'round3_native_write_results' and pack['version'] == 1
    assert pack['source_unchanged'] is True and pack['source_before'] == pack['source_after']
    assert pack['collector']['original_files_checked_unchanged'] == 8
    collector = Path(__file__).parents[1] / pack['collector']['path']
    assert hashlib.sha256(collector.read_bytes()).hexdigest() == pack['collector']['sha256']
    assert len(native) == pack['transcript_physical_line_count']
    assert len(control) == pack['control_physical_line_count']
    for name, number, sha in WRITES:
        record = pack['writes'][name]
        assert record['result']['physical_line'] == number
        assert record['result']['decoded_sha256'] == sha
        for role in ('call', 'callback', 'result', 'decision'):
            frame = record[role]
            rows = native if frame['source_file'] == 'transcript.jsonl' else control
            assert decode(frame) == rows[frame['physical_line'] - 1]
            assert frame['source_sha256'] == pack['files'][frame['source_file']]['decoded_sha256']
        raw = decode(record['response'])
        call = json.loads(decode(record['call']))['message']['content'][0]
        event = json.loads(decode(record['result']))
        assert raw == call['input']['content'].encode('utf-8')
        assert raw == event['tool_use_result']['content'].encode('utf-8')
        text = event['message']['content'][0]['content']
        assert '\u2014' in text and text == (
            'File created successfully at: ' + record['response']['original_path']
            + ' (file state is current in your context \u2014 no need to Read it back)')
    assert bytes([64]) not in PACK.read_bytes()
    assert bytes([64]) not in collector.read_bytes()
    assert bytes([64]) not in Path(__file__).read_bytes()


def test_both_readers_accept_retained_writes_and_legacy_bare_control(reader, name, form):
    value = context(name)
    event = deepcopy(value['event'])
    if form == 'software_bare':
        event['message']['content'][0]['content'] = 'File created successfully at: ' + value['response'].pin.path
    trace = read_result(reader, value, event, value['runtime'])
    if trace is not None and form == 'retained':
        number = value['record']['result']['physical_line']
        assert trace.transcript.raw == b''.join(value['native'][:number])


test_both_readers_accept_retained_writes_and_legacy_bare_control = pytest.mark.parametrize(
    'reader', READERS)(pytest.mark.parametrize('name', [row[0] for row in WRITES])(
    pytest.mark.parametrize('form', ['retained', 'software_bare'])(
        test_both_readers_accept_retained_writes_and_legacy_bare_control)))


TEXT_MUTATIONS = ('ascii_hyphen', 'en_dash', 'leading_space', 'trailing_space',
    'newline', 'carriage_return', 'embedded_newline', 'truncated_suffix', 'repeated_suffix',
    'changed_word', 'wrong_path', 'normalized_path', 'nontext', 'list_content')


def change_text(text, path, change):
    if change == 'ascii_hyphen': return text.replace('\u2014', '-')
    if change == 'en_dash': return text.replace('\u2014', '\u2013')
    if change == 'leading_space': return ' ' + text
    if change == 'trailing_space': return text + ' '
    if change == 'newline': return text + '\n'
    if change == 'carriage_return': return text + '\r\n'
    if change == 'embedded_newline': return text.replace(' (file state', '\n(file state')
    if change == 'truncated_suffix': return text[:-1]
    if change == 'repeated_suffix': return text + wire.WRITE_SUCCESS_SUFFIX
    if change == 'changed_word': return text.replace('Read it back', 'read it back')
    if change == 'wrong_path': return text.replace(path, path + '.foreign')
    if change == 'normalized_path': return text.replace('/responses/', '/responses/../responses/')
    if change == 'nontext': return None
    if change == 'list_content': return [{'type': 'text', 'text': text}]
    raise AssertionError(change)


def test_both_readers_refuse_unreviewed_write_text(reader, change):
    value = context()
    event = deepcopy(value['event'])
    block = event['message']['content'][0]
    block['content'] = change_text(block['content'], value['response'].pin.path, change)
    with pytest.raises(ValueError):
        read_result(reader, value, event, value['runtime'])


test_both_readers_refuse_unreviewed_write_text = pytest.mark.parametrize('reader', READERS)(
    pytest.mark.parametrize('change', TEXT_MUTATIONS)(test_both_readers_refuse_unreviewed_write_text))


RESULT_MUTATIONS = ('type', 'metadata_path', 'metadata_content', 'original_file',
    'modified', 'modified_zero', 'patch', 'metadata_missing', 'metadata_string',
    'is_error', 'is_error_zero', 'error', 'error_empty', 'interrupted',
    'interrupted_zero', 'background', 'persisted', 'exit_nonzero', 'exit_bool',
    'exit_conflict', 'foreign_identity')


def change_result(event, change):
    block = event['message']['content'][0]
    metadata = event['tool_use_result']
    if change == 'type': metadata['type'] = 'update'
    elif change == 'metadata_path': metadata['filePath'] += '.foreign'
    elif change == 'metadata_content': metadata['content'] += 'changed'
    elif change == 'original_file': metadata['originalFile'] = 'existing bytes'
    elif change == 'modified': metadata['userModified'] = True
    elif change == 'modified_zero': metadata['userModified'] = 0
    elif change == 'patch': metadata['structuredPatch'] = [{'oldLines': []}]
    elif change == 'metadata_missing': event.pop('tool_use_result')
    elif change == 'metadata_string': event['tool_use_result'] = 'created'
    elif change == 'is_error': block['is_error'] = True
    elif change == 'is_error_zero': block['is_error'] = 0
    elif change == 'error': metadata['error'] = 'failed'
    elif change == 'error_empty': metadata['error'] = ''
    elif change == 'interrupted': metadata['interrupted'] = True
    elif change == 'interrupted_zero': metadata['interrupted'] = 0
    elif change == 'background': metadata['backgroundTaskId'] = 'pending'
    elif change == 'persisted': metadata['persistedOutputPath'] = '/foreign'
    elif change == 'exit_nonzero': metadata['exitCode'] = 1
    elif change == 'exit_bool': metadata['exitCode'] = False
    elif change == 'exit_conflict': metadata.update(exitCode=0, exit_code=1)
    elif change == 'foreign_identity': block['tool_use_id'] += '-foreign'
    else: raise AssertionError(change)


def test_suffix_does_not_override_existing_result_guards(reader, change):
    value = context()
    event = deepcopy(value['event'])
    change_result(event, change)
    with pytest.raises(ValueError):
        read_result(reader, value, event, value['runtime'])


test_suffix_does_not_override_existing_result_guards = pytest.mark.parametrize('reader', READERS)(
    pytest.mark.parametrize('change', RESULT_MUTATIONS)(test_suffix_does_not_override_existing_result_guards))


def inactive_runtime(runtime, change):
    value = deepcopy(runtime)
    if change == 'absent': return None
    if change == 'empty': return {}
    if change.startswith('missing_'):
        value['executable'].pop(change[len('missing_'):])
    else:
        value['executable'][change] = 'unreviewed'
    return value


PROFILES = ('absent', 'empty', 'version', 'init_version', 'sha256',
            'missing_version', 'missing_init_version', 'missing_sha256')


def test_suffix_requires_complete_profile_but_bare_remains_universal(change):
    value = context()
    runtime = inactive_runtime(value['runtime'], change)
    path = value['response'].pin.path
    text = value['event']['message']['content'][0]['content']
    assert not wire.profile(runtime)
    assert not wire.write_success_text(text, path, runtime)
    assert wire.write_success_text('File created successfully at: ' + path, path, runtime)
    with pytest.raises(ValueError):
        read_result('permission_result', value, value['event'], runtime)
    bare = deepcopy(value['event'])
    bare['message']['content'][0]['content'] = 'File created successfully at: ' + path
    read_result('permission_result', value, bare, runtime)


test_suffix_requires_complete_profile_but_bare_remains_universal = pytest.mark.parametrize(
    'change', PROFILES)(test_suffix_requires_complete_profile_but_bare_remains_universal)


def test_production_observation_uses_selected_trace_profile(change):
    value = context()
    runtime = inactive_runtime(value['runtime'], change)
    trace = observed_trace(value, value['event'], runtime)
    assert not wire.profile(trace.runtime)
    evidence = trace.settled(value['call']['id'])
    with pytest.raises(ValueError, match='successful first file creation'):
        observations.first_response_write(trace, evidence, value['response'],
            intent_input_json=c.canonical(value['call']['input']))
    bare = deepcopy(value['event'])
    bare['message']['content'][0]['content'] = 'File created successfully at: ' + value['response'].pin.path
    read_result('production_observation', value, bare, runtime)


test_production_observation_uses_selected_trace_profile = pytest.mark.parametrize(
    'change', ['version', 'sha256', 'missing_version', 'missing_sha256'])(
        test_production_observation_uses_selected_trace_profile)


def test_production_write_still_requires_original_intent_and_file_bytes(change):
    value = context()
    trace = observed_trace(value, value['event'], value['runtime'])
    evidence = trace.settled(value['call']['id'])
    response = value['response']
    intent = c.canonical(value['call']['input'])
    if change == 'intent':
        inputs = deepcopy(value['call']['input'])
        inputs['content'] += 'changed'
        intent = c.canonical(inputs)
    else:
        raw = response.raw + b'changed'
        response = c.CapturedArtifact(c.ArtifactPin('response', response.pin.path,
            len(raw), c.sha(raw)), raw)
    with pytest.raises(ValueError, match='original admitted Write intent'):
        observations.first_response_write(trace, evidence, response, intent_input_json=intent)


test_production_write_still_requires_original_intent_and_file_bytes = pytest.mark.parametrize(
    'change', ['intent', 'file_bytes'])(test_production_write_still_requires_original_intent_and_file_bytes)


def test_pure_write_predicate_does_not_coerce_path_or_text():
    value = context()
    path = value['response'].pin.path
    text = value['event']['message']['content'][0]['content']
    for other in (None, False, 0, Path(path), [path]):
        assert not wire.write_success_text(text, other, value['runtime'])
    for other in (None, False, 0, text.encode(), [text]):
        assert not wire.write_success_text(other, path, value['runtime'])
    assert not wire.write_success_text(text, path + '.foreign', value['runtime'])
