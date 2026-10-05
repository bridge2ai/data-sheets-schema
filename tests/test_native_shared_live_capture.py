"""Real offline registration/capture with explicitly invented native frames.

These tests do not run the declared executable or claim actual permissions.
They exercise durable actual stage files and the same strict observed joins.
"""
from pathlib import Path
import json

import pytest

from tests.test_native_shared_registration import execution, bound, native_spec, declaration
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_registration as registration
from data_sheets_schema import native_shared_selection as selection


@pytest.fixture
def started(execution):
    args, selected, _ = execution
    value = registration.registration(**args)
    raw = c.canonical(value)
    cap = selection.capture(c.parse_selection(selected['selection_raw_json'].encode())['registration_path'])
    attempt = args['attempt_directory']; attempt.mkdir()
    (attempt / 'registration.json').write_bytes(raw)
    start = c.canonical({'kind': c.KINDS['attempt'], 'version': 1, 'state': 'started',
        'attempt_id': value['attempt_id'], 'registration_sha256': c.sha(raw),
        'composition_sha256': value['composition_sha256'], 'dispatch_limit': 1})
    (attempt / 'started.json').write_bytes(start)
    Path(cap.role('stage_root')).mkdir(parents=True)
    capture.activate(cap, raw, start)
    return cap, value, selected, raw, start


def native_init(cap, value, selected):
    policy = selected['policy']; contract = policy['pretool_control']
    sent = {'kind': 'initialize_sent', 'policy_sha256': c.sha(json.dumps(policy, sort_keys=True, separators=(',', ':')).encode()),
        'frame': {'type': 'control_request', 'request_id': 'd4d_initialize_v1', 'request': {'subtype': 'initialize',
            'hooks': {contract['event']: [{'matcher': contract['matcher'], 'hookCallbackIds': [contract['callback_id']],
                                        'timeout': contract['runtime_callback_timeout_seconds']}]}}}}
    ack = {'type': 'control_response', 'response': {'subtype': 'success', 'request_id': 'd4d_initialize_v1'}}
    init = {'type': 'system', 'subtype': 'init', 'session_id': '00000000-0000-4000-8000-000000000010',
        'cwd': value['working_directory'], 'model': value['runtime']['model'],
        'claude_code_version': value['runtime']['executable']['init_version'],
        'apiKeySource': value['runtime']['auth']['expected_api_key_source'], 'tools': ['Bash', 'Read', 'Write']}
    transcript = b''.join(c.canonical(row) + b'\n' for row in (ack, init))
    control = b''.join(c.canonical(row) + b'\n' for row in (sent, {'kind': 'initialize_ack', 'frame': ack}))
    attempt = Path(value['attempt_directory'])
    (attempt / 'transcript.jsonl').write_bytes(transcript)
    (attempt / 'control.jsonl').write_bytes(control)
    return transcript, control


def stream_capture(value):
    from data_sheets_schema.native_shared_streams import stream_files as identities
    members, prefixes = capture._streams(value)
    return {'stream_files': identities(members),
            'observed_prefixes': dict(zip(('transcript', 'control'), prefixes))}


def test_actual_reserved_genesis_then_observed_init_and_no_premature_stage(started):
    cap, value, selected, raw, start = started
    genesis = c.strict_json(Path(cap.role('journal')).read_bytes())
    assert len(genesis['records']) == 1
    assert not Path(cap.role('session_binding')).exists()
    with pytest.raises(ValueError, match='spent'):
        capture.activate(cap, raw, start)
    transcript, control = native_init(cap, value, selected)
    capture.initialize(cap.registration.pin.path, transcript_bytes=len(transcript), control_bytes=len(control), **stream_capture(value))
    actual = capture._load(cap.registration.pin.path)
    assert actual.phase1 is None
    assert len(actual.history.records) == 2 and len(actual.observations) == 1
    assert actual.binding.execution.raw == raw and actual.binding.started.raw == start
    assert actual.binding.session_id == '00000000-0000-4000-8000-000000000010'
    assert actual.trace().pending() == ()
    with pytest.raises(ValueError, match='spent'):
        capture.initialize(cap.registration.pin.path, transcript_bytes=len(transcript), control_bytes=len(control), **stream_capture(value))
    with pytest.raises(ValueError, match='sealed originals'):
        capture.capture_stage(cap.registration.pin.path)


def test_binding_cannot_use_foreign_init_or_changed_actual_attempt(started):
    cap, value, selected, raw, start = started
    transcript, control = native_init(cap, value, selected)
    attempt = Path(value['attempt_directory'])
    changed = transcript.replace(value['runtime']['model'].encode(), b'foreign-model')
    (attempt / 'transcript.jsonl').write_bytes(changed)
    with pytest.raises(ValueError, match='runtime'):
        capture.initialize(cap.registration.pin.path, transcript_bytes=len(changed), control_bytes=len(control), **stream_capture(value))
    assert not Path(cap.role('session_binding')).exists()
    (attempt / 'transcript.jsonl').write_bytes(transcript)
    (attempt / 'started.json').write_bytes(start + b' ')
    with pytest.raises(ValueError, match='actual one-use'):
        capture.initialize(cap.registration.pin.path, transcript_bytes=len(transcript), control_bytes=len(control), **stream_capture(value))
    assert not Path(cap.role('session_binding')).exists()


@pytest.mark.parametrize('kind', ['gap', 'unknown', 'symlink'])
def test_observation_catalog_is_bounded_closed_namespace(case, tmp_path, kind):
    from dataclasses import replace
    selected = case[0]
    root = tmp_path.resolve() / 'stage'
    doc = selected.document(); doc['stage_root'] = str(root)
    selected = replace(selected, registration=capture._captured('selection', selected.registration.pin.path, c.canonical(doc)),
                       roles=c.role_paths(selected.registration.pin.path, str(root)))
    path = root / 'observations'; path.mkdir(parents=True)
    if kind == 'gap': (path / '000001.json').write_bytes(b'{}')
    elif kind == 'unknown': (path / 'last.json').write_bytes(b'{}')
    else:
        target = tmp_path / 'other.json'; target.write_bytes(b'{}')
        (path / '000000.json').symlink_to(target)
    with pytest.raises(ValueError): capture._observation_paths(selected)


# Neutral carrier setup only; the three metadata cases never read registration.
from tests.test_native_shared_stages import case, supplied
