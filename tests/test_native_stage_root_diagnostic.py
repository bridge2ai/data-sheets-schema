"""PR 6302 marker-capture diagnostics, pure and local-file tests, 2026-11-21.

All payloads are constructed software fixtures, never native observations.
No native binary, provider, network, or original retained evidence is touched.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_stage_root_diagnostic as diagnostic
from data_sheets_schema import native_stage_root_grant as grant


def _block_transports(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('native and network transports are forbidden in diagnostic unit tests')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


def _pin(raw):
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def _launch(root):
    effect = str(root / 'effect-root')
    return {'cwd': str(root / 'worktree'), 'effect_root': effect,
            'argv': ['never-run-native', '--restricted', '--safe-mode', '--strict-mcp-config',
                     *grant.permission_arguments({'allowed_tools': ['Read', 'Write', 'Bash']}, effect)]}


def _captured_case(root):
    launch = _launch(root)
    capture = diagnostic.GrantCapture(root, launch)
    transcript = b'{"type":"result","result":"OFFLINE_COMPLETE"}\n'
    (root / 'transcript.jsonl').write_bytes(transcript)
    requests = {
        'requests/000001.json': b'{ "messages" : [{"role":"user","content":"first"}] }\n',
        'requests/000002.json': b'{"messages":[{"role":"user","content":"second"}]}\n',
    }
    capture.capture(requests['requests/000001.json'], endpoint='/v1/messages')
    capture.capture(requests['requests/000002.json'], endpoint='/v1/messages/count_tokens')
    capture.finish(launch, request_count=2)
    document = json.loads((root / 'diagnostics/grant.json').read_bytes())
    return launch, document, transcript, requests


def _verify(document, launch, transcript, requests):
    return diagnostic.validate_grant_diagnostic(document, launch=launch,
        transcript_raw=transcript, request_raws=requests)


def test_diagnostic_fixture_is_exact_and_optional(monkeypatch):
    _block_transports(monkeypatch)
    assert diagnostic.require_fixture(None) is None
    assert diagnostic.require_fixture(deepcopy(diagnostic.FIXTURE)) is None
    invalid = [False, True, 1, [], '', {},
        {**diagnostic.FIXTURE, 'capture_requests': 1},
        {**diagnostic.FIXTURE, 'capture_requests': False},
        {**diagnostic.FIXTURE, 'marker': 'caller-selected-marker'},
        {**diagnostic.FIXTURE, 'kind': 'unregistered'},
        {**diagnostic.FIXTURE, 'path': '/caller/selected'},
        {key: value for key, value in diagnostic.FIXTURE.items() if key != 'marker'}]
    for value in invalid:
        with pytest.raises(ValueError):
            diagnostic.require_fixture(value)


def test_capture_preserves_raw_requests_and_two_marker_identities(tmp_path, monkeypatch):
    _block_transports(monkeypatch)
    launch, document, transcript, requests = _captured_case(tmp_path)
    for relative in ('CLAUDE.md', 'requests/CLAUDE.md'):
        assert (Path(launch['effect_root']) / relative).read_bytes() == diagnostic.MARKER_BYTES
    for relative, raw in requests.items():
        assert (tmp_path / 'diagnostics' / relative).read_bytes() == raw
    assert document['provider_request_count'] == 2
    assert document['markers'] == [{'relative_path': name,
        'before': _pin(diagnostic.MARKER_BYTES), 'after': _pin(diagnostic.MARKER_BYTES)}
        for name in ('CLAUDE.md', 'requests/CLAUDE.md')]
    assert _verify(document, launch, transcript, requests) == {
        'checked': True, 'marker_absent': True, 'requests': 2}


def test_capture_never_overwrites_an_existing_marker(tmp_path, monkeypatch):
    _block_transports(monkeypatch)
    launch = _launch(tmp_path)
    existing = Path(launch['effect_root']) / 'CLAUDE.md'
    existing.parent.mkdir()
    existing.write_bytes(b'previous evidence\n')
    with pytest.raises(FileExistsError):
        diagnostic.GrantCapture(tmp_path, launch)
    assert existing.read_bytes() == b'previous evidence\n'


def test_capture_rejects_unknown_endpoint_types_and_bounded_overflow(tmp_path, monkeypatch):
    _block_transports(monkeypatch)
    capture = diagnostic.GrantCapture(tmp_path, _launch(tmp_path))
    for raw, endpoint in ((b'', '/v1/messages'), ('{}', '/v1/messages'),
                          (bytearray(b'{}'), '/v1/messages'), (b'{}', '/other'),
                          (b'x' * (8 * 1024 * 1024 + 1), '/v1/messages')):
        with pytest.raises(ValueError):
            capture.capture(raw, endpoint=endpoint)
    assert capture.requests == []
    monkeypatch.setattr(diagnostic, 'MAX_CAPTURE', 1)
    with pytest.raises(ValueError):
        capture.capture(b'{}', endpoint='/v1/messages')
    assert capture.requests == []


def test_capture_detects_changed_marker_bytes_at_finish(tmp_path, monkeypatch):
    _block_transports(monkeypatch)
    launch = _launch(tmp_path)
    capture = diagnostic.GrantCapture(tmp_path, launch)
    transcript = b'{"type":"result","result":"OFFLINE_COMPLETE"}\n'
    (tmp_path / 'transcript.jsonl').write_bytes(transcript)
    raw = b'{"messages":[]}'
    capture.capture(raw, endpoint='/v1/messages')
    (Path(launch['effect_root']) / 'requests/CLAUDE.md').write_bytes(b'changed\n')
    capture.finish(launch, request_count=1)
    document = json.loads((tmp_path / 'diagnostics/grant.json').read_bytes())
    assert document['markers'][1]['before'] != document['markers'][1]['after']
    with pytest.raises(ValueError, match='marker identity'):
        _verify(document, launch, transcript, {'requests/000001.json': raw})


def test_grant_sidecar_mutations_cannot_substitute_capture_or_launch(tmp_path, monkeypatch):
    _block_transports(monkeypatch)
    launch, baseline, transcript, original_requests = _captured_case(tmp_path)
    changes = ('extra', 'fixture_none', 'fixture_integer', 'version_bool', 'cwd', 'stage_root',
        'parent_grant', 'allow_policy', 'marker_before', 'marker_after', 'marker_reorder',
        'request_hash', 'request_bytes', 'request_bytes_float', 'request_endpoint', 'request_reorder', 'request_extra_field',
        'request_path', 'request_count', 'request_count_bool', 'request_row_extra', 'request_row_missing',
        'raw_extra', 'raw_missing', 'raw_substitution', 'transcript_pin', 'transcript_pin_float', 'transcript_bytes',
        'marker_claim_false', 'marker_claim_integer')
    for change in changes:
        document, requests, seen = deepcopy(baseline), dict(original_requests), transcript
        if change == 'extra':
            document['unknown'] = True
        elif change == 'fixture_none':
            document['fixture'] = None
        elif change == 'fixture_integer':
            document['fixture']['capture_requests'] = 1
        elif change == 'version_bool':
            document['version'] = True
        elif change == 'cwd':
            document['cwd'] += '-other'
        elif change == 'stage_root':
            document['stage_root'] = str(Path(launch['effect_root']).parent)
        elif change in ('parent_grant', 'allow_policy'):
            argv = document['argv']
            index = argv.index('--settings') + 1
            settings = json.loads(argv[index])
            if change == 'parent_grant':
                settings['permissions']['additionalDirectories'] = [str(Path(launch['effect_root']).parent)]
            else:
                settings['permissions']['allow'].append('Bash(anything)')
            argv[index] = json.dumps(settings)
        elif change == 'marker_before':
            document['markers'][0]['before'] = _pin(b'changed')
        elif change == 'marker_after':
            document['markers'][1]['after'] = _pin(b'changed')
        elif change == 'marker_reorder':
            document['markers'].reverse()
        elif change == 'request_hash':
            document['provider_requests'][0]['sha256'] = '0' * 64
        elif change == 'request_bytes':
            document['provider_requests'][0]['bytes'] += 1
        elif change == 'request_bytes_float':
            document['provider_requests'][0]['bytes'] = float(document['provider_requests'][0]['bytes'])
        elif change == 'request_endpoint':
            document['provider_requests'][0]['endpoint'] = '/other'
        elif change == 'request_reorder':
            document['provider_requests'].reverse()
        elif change == 'request_extra_field':
            document['provider_requests'][0]['unknown'] = True
        elif change == 'request_path':
            document['provider_requests'][0]['relative_path'] = '../outside.json'
        elif change == 'request_count':
            document['provider_request_count'] += 1
        elif change == 'request_count_bool':
            document['provider_request_count'] = True
        elif change == 'request_row_extra':
            document['provider_requests'].append(deepcopy(document['provider_requests'][0]))
            document['provider_request_count'] += 1
        elif change == 'request_row_missing':
            document['provider_requests'].pop()
            document['provider_request_count'] -= 1
        elif change == 'raw_extra':
            requests['requests/000003.json'] = b'{}'
        elif change == 'raw_missing':
            del requests['requests/000002.json']
        elif change == 'raw_substitution':
            requests['requests/000001.json'] = b'{"different":true}'
        elif change == 'transcript_pin':
            document['transcript']['sha256'] = '0' * 64
        elif change == 'transcript_pin_float':
            document['transcript']['bytes'] = float(document['transcript']['bytes'])
        elif change == 'transcript_bytes':
            seen += b'{"unexpected":true}\n'
        elif change == 'marker_claim_false':
            document['marker_absent']['provider_requests'] = False
        else:
            document['marker_absent']['provider_requests'] = 1
        with pytest.raises(ValueError):
            _verify(document, launch, seen, requests)


def test_marker_detection_checks_decoded_json_with_fresh_valid_pins(tmp_path, monkeypatch):
    _block_transports(monkeypatch)
    launch, baseline, transcript, original_requests = _captured_case(tmp_path)
    escaped = ''.join('\\u%04x' % ord(character) for character in diagnostic.MARKER)
    samples = (
        json.dumps({'nested': [{'text': diagnostic.MARKER}]}).encode(),
        ('{"nested":[{"text":"' + escaped + '"}]}').encode(),
        ('{"' + escaped + '":"value"}').encode(),
    )
    for location in ('provider', 'transcript'):
        for raw in samples:
            document, requests, seen = deepcopy(baseline), dict(original_requests), transcript
            if location == 'provider':
                requests['requests/000001.json'] = raw
                document['provider_requests'][0].update(_pin(raw))
            else:
                seen = raw + b'\n'
                document['transcript'].update(_pin(seen))
            assert document['marker_absent'] == {'transcript': True, 'provider_requests': True}
            with pytest.raises(ValueError, match='marker'):
                _verify(document, launch, seen, requests)


def test_finish_records_escaped_marker_detection(tmp_path, monkeypatch):
    _block_transports(monkeypatch)
    launch = _launch(tmp_path)
    capture = diagnostic.GrantCapture(tmp_path, launch)
    escaped = ''.join('\\u%04x' % ord(character) for character in diagnostic.MARKER)
    raw = ('{"content":"' + escaped + '"}').encode()
    assert diagnostic.MARKER.encode() not in raw
    capture.capture(raw, endpoint='/v1/messages')
    (tmp_path / 'transcript.jsonl').write_bytes(raw + b'\n')
    capture.finish(launch, request_count=1)
    document = json.loads((tmp_path / 'diagnostics/grant.json').read_bytes())
    assert document['marker_absent'] == {'transcript': False, 'provider_requests': False}


def test_malformed_json_cannot_hide_marker_presence(tmp_path, monkeypatch):
    _block_transports(monkeypatch)
    launch, baseline, transcript, original_requests = _captured_case(tmp_path)
    for raw in (b'{', b'{"duplicate":1,"duplicate":2}', b'{"value":NaN}'):
        for location in ('provider', 'transcript'):
            document, requests, seen = deepcopy(baseline), dict(original_requests), transcript
            if location == 'provider':
                requests['requests/000001.json'] = raw
                document['provider_requests'][0].update(_pin(raw))
            else:
                seen = raw + b'\n'
                document['transcript'].update(_pin(seen))
            with pytest.raises(ValueError):
                _verify(document, launch, seen, requests)


def test_secondary_diagnostic_failure_does_not_mask_active_native_failure(tmp_path, monkeypatch):
    _block_transports(monkeypatch)
    from data_sheets_schema import native_permission_probe as producer
    launch = _launch(tmp_path)
    (tmp_path / 'transcript.jsonl').write_bytes(b'{"retained":"partial-native-stream"}\n')
    secondary = ValueError('diagnostic retention failed')
    calls = []

    def fail_finish(observed_launch, *, request_count):
        assert observed_launch is launch and request_count == 3
        calls.append(True)
        raise secondary

    capture = SimpleNamespace(directory=tmp_path, finish=fail_finish)
    server = SimpleNamespace(requests=3)
    primary = TimeoutError('native deadline elapsed')
    with pytest.raises(TimeoutError) as caught:
        try:
            raise primary
        finally:
            producer._finish_diagnostic(capture, launch, server)
    assert caught.value is primary
    assert calls == [True]
    retained = json.loads((tmp_path / 'diagnostics/failure.json').read_bytes())
    assert retained == {'kind': 'native_stage_root_diagnostic_failure', 'version': 1,
                        'error_type': 'ValueError', 'message': str(secondary)}


def test_diagnostic_failure_without_active_native_failure_propagates(tmp_path, monkeypatch):
    _block_transports(monkeypatch)
    from data_sheets_schema import native_permission_probe as producer
    launch = _launch(tmp_path)
    (tmp_path / 'transcript.jsonl').write_bytes(b'{"retained":"completed-native-stream"}\n')
    secondary = ValueError('diagnostic retention failed')

    def fail_finish(observed_launch, *, request_count):
        assert observed_launch is launch and request_count == 2
        raise secondary

    capture = SimpleNamespace(directory=tmp_path, finish=fail_finish)
    with pytest.raises(ValueError) as caught:
        producer._finish_diagnostic(capture, launch, SimpleNamespace(requests=2))
    assert caught.value is secondary
    retained = json.loads((tmp_path / 'diagnostics/failure.json').read_bytes())
    assert retained == {'kind': 'native_stage_root_diagnostic_failure', 'version': 1,
                        'error_type': 'ValueError', 'message': str(secondary)}
