"""R13 failed-publication replay, 2026-11-08; no native generation launch.

These fixtures isolate registration reconstruction, reservation topology and
the CI/source approval prerequisite, which cannot be supplied on this base.
They do not establish full-chain registration, launch or scientific acceptance.
The fixed execution contract, public read_final body, saved runtime evidence,
capture, review bundle, guard, replay, file basis and metadata checks execute.
Only the existing scripted Python capture peer is run; never a native binary.
"""
from copy import deepcopy
from pathlib import Path
import stat

import pytest

from data_sheets_schema import native_execution_orchestration as engine
from data_sheets_schema import native_execution_registration_v2 as admission
from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_execution_orchestration as native
from data_sheets_schema import native_shared_registration_orchestration as registration
from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema import native_subscription_guard as legacy_guard
from data_sheets_schema import native_subscription_guard_v2 as guard
from tests.test_native_subscription_capture import component, read_arguments
from tests.test_native_subscription_guard import build as build_legacy, case as legacy_case
from tests.utils.native_u4b_fixtures import bundle_for


def publication(tmp_path, monkeypatch, mode='buffered'):
    """Persist a synthetic failure; every copied authority byte is still joined."""
    arguments, original = component(tmp_path, monkeypatch)
    value = deepcopy(original)
    value['composition_sha256'] = guard.sha(value['composition_raw_json'].encode())
    raw = guard.canonical({'authority_version': 2, 'controller_sources_sha256': 'f' * 64,
                           'registration': value})

    def verified(submitted):
        assert submitted == raw
        return deepcopy(value)

    def paths(submitted, *, fresh, extra_protected):
        assert submitted == value and fresh is False
        assert len(extra_protected) == 3
        return []

    monkeypatch.setattr(registration, 'verified', verified)
    monkeypatch.setattr(registration, 'execution_paths_v2', paths)
    now = guard.strict_json(arguments['launch_word_raw'])['authorized_at']
    bundle_raw, word_raw = bundle_for(raw, arguments['directory'], now=now)
    ci_raw = b'{"scope":"fabricated CI prerequisite; not acceptance"}'
    word = guard.strict_json(word_raw)
    word['ci_sha256'] = guard.sha(ci_raw)
    word_raw = guard.canonical(word)
    arguments.update(registration_raw=raw, review_bundle_raw=bundle_raw, launch_word_raw=word_raw)
    captured = capture.capture_subscription(**arguments)
    saved = capture.read_capture(captured, **read_arguments(arguments))
    terms = review.validate_bundle(raw, bundle_raw, word_raw)
    event = saved['selected_event']
    guard_raw = guard.prepare_guard(registration_raw=raw, runtime=value['runtime'],
        launch_word_raw=word_raw, event_raw=event['event_json'].encode(),
        captured_at=event['captured_at'], owner_statement=terms,
        maximum_starting_utilization=terms['max_starting_weekly_utilization'],
        max_age_seconds=terms['max_age_seconds'])
    watched = guard.SubscriptionGuard(guard_raw, expected_sha256=guard.sha(guard_raw),
        registration_raw=raw, runtime=value['runtime'], launch_word_raw=word_raw,
        owner_statement=terms)
    watched.before_dispatch()
    attempt, output = Path(value['attempt_directory']), Path(value['evidence_directory'])
    attempt.mkdir()
    output.mkdir()
    authority = {}
    original_bytes = {'review': bundle_raw, 'ci': ci_raw, 'launch_word': word_raw}
    for name, body in original_bytes.items():
        path = tmp_path / ('original-' + name + '.json')
        path.write_bytes(body)
        (attempt / (name + '.json')).write_bytes(body)
        authority[name] = {'path': str(path), 'sha256': guard.sha(body)}

    def approvals(submitted, checked, *, review_path, ci_path, launch_word_path):
        # CI/source verification is explicitly isolated. The real enclosing
        # reader still joins original and consumed bytes to started and final.
        assert submitted == raw and checked == value
        result = {}
        for name, path in {'review': review_path, 'ci': ci_path,
                           'launch_word': launch_word_path}.items():
            item = evidence.read_regular(str(path), name + ' evidence', max_bytes=1048576).captured
            assert item.raw == original_bytes[name]
            result[name] = item
        return result

    monkeypatch.setattr(admission, '_authorizations', approvals)
    started = {'kind': native.KIND, 'version': 1, 'state': 'started',
        'attempt_id': value['attempt_id'], 'started_at': now,
        'registration_sha256': guard.sha(raw), 'composition_sha256': value['composition_sha256'],
        'authority': authority, 'dispatch_limit': 1,
        'dispatch_unit': 'native CLI process, not provider transactions', **engine.UNASSESSED}
    started_raw = guard.canonical(started)
    (attempt / 'started.json').write_bytes(started_raw)
    (attempt / 'registration.json').write_bytes(raw)
    (attempt / 'subscription-guard.json').write_bytes(guard_raw)
    (attempt / 'subscription-dispatched.json').write_bytes(guard.canonical(
        {'guard_sha256': guard.sha(guard_raw), 'consumed': True}))
    transcript = None
    if mode != 'absent':
        unsafe = guard.strict_json(event['event_json'])
        unsafe['rate_limit_info']['unifiedWindows']['five_hour']['utilization'] = 1
        transcript = b'broken' if mode == 'malformed' else guard.canonical(unsafe) + b'\n'
        (attempt / 'transcript.jsonl').write_bytes(transcript)
    files, metadata = {}, {}
    if transcript is not None:
        path = attempt / 'transcript.jsonl'
        info = path.stat()
        files[str(path)] = {'bytes': len(transcript), 'sha256': guard.sha(transcript),
                            'roles': ['transcript']}
        metadata[str(path)] = {'exists': True, 'regular': stat.S_ISREG(info.st_mode),
            'links': info.st_nlink, 'device': info.st_dev, 'inode': info.st_ino,
            'size': info.st_size, 'mtime_ns': info.st_mtime_ns}
    result = {'kind': native.KIND, 'version': 1, 'attempt_id': value['attempt_id'],
        'composition_sha256': value['composition_sha256'], 'registration_sha256': guard.sha(raw),
        'started_sha256': guard.sha(started_raw), **engine.UNASSESSED,
        'authority': authority, 'state': 'failed', 'runtime_gates_passed': False,
        'first_stop': 'synthetic failed publication, not an accepted launch',
        'gates': {name: {'checked': False, 'passed': False, 'reason': 'synthetic incomplete run'}
                  for name in engine.GATES},
        'captured_files': files, 'captured_metadata': metadata, 'captured_aliases': {},
        'captured_alias_metadata': {}, 'lifecycle_artifacts': {}, 'additional_report': None,
        'subscription_guard': watched.snapshot(),
        'subscription_observation_verification': guard.validate_saved_observations(
            guard_raw, watched.snapshot(), registration_raw=raw, runtime=value['runtime'],
            launch_word_raw=word_raw, owner_statement=terms, transcript_raw=transcript, complete=False)}

    def publish():
        final_raw = guard.canonical(result)
        (output / 'final.json').write_bytes(final_raw)
        (output / 'published.json').write_bytes(guard.canonical({'final_sha256': guard.sha(final_raw),
            'started_sha256': guard.sha(started_raw), 'registration_sha256': guard.sha(raw)}))

    publish()
    return raw, result, attempt, publish


@pytest.mark.parametrize('mode', ['buffered', 'malformed', 'absent'])
def test_failed_public_readback_preserves_unverified_diagnostic(tmp_path, monkeypatch, mode):
    raw, result, attempt, publish = publication(tmp_path, monkeypatch, mode)
    actual = native.read_final(raw)
    assert actual == result and actual['state'] == 'failed'
    observed = actual['subscription_observation_verification']
    assert observed['checked'] is observed['complete'] is observed['passed'] is False
    diagnostic = observed['transcript_diagnostic']
    if mode == 'absent':
        assert diagnostic is None
    elif mode == 'malformed':
        assert diagnostic['complete'] is False and diagnostic['error']
    else:
        assert diagnostic['observed_rate_limit_events'] == 1
        assert diagnostic['observed_windows']['five_hour']['highest']['utilization'] == 1
        assert diagnostic['first_stop'] == 'five_hour subscription window is exhausted'
        # Buffered events were never delivered to this synthetic observer.
        assert result['subscription_guard']['observed_rate_limit_events'] == 0


@pytest.mark.parametrize('mutation', ['bytes', 'digest', 'size', 'missing_pin', 'diagnostic'])
def test_failed_public_readback_refuses_changed_transcript_basis(tmp_path, monkeypatch, mutation):
    raw, result, attempt, publish = publication(tmp_path, monkeypatch)
    assert native.read_final(raw) == result
    path = str(attempt / 'transcript.jsonl')
    if mutation == 'bytes':
        Path(path).write_bytes(b'changed\n')
    elif mutation == 'digest':
        result['captured_files'][path]['sha256'] = '0' * 64
    elif mutation == 'size':
        result['captured_files'][path]['bytes'] += 1
    elif mutation == 'missing_pin':
        del result['captured_files'][path]
    else:
        result['subscription_observation_verification']['transcript_diagnostic']['observed_rate_limit_events'] = 99
    publish()  # Rehash final/marker, so refusal must come from the underlying basis.
    with pytest.raises(ValueError):
        native.read_final(raw)


@pytest.mark.parametrize('complete', [False, True])
def test_transcript_absence_never_opens_an_uncaptured_file(tmp_path, monkeypatch, complete):
    def forbidden(*args, **kwargs):
        pytest.fail('uncaptured transcript was opened')
    monkeypatch.setattr(evidence, 'read_regular', forbidden)
    result = {'runtime_gates_passed': complete, 'captured_files': {}}
    if complete:
        with pytest.raises(ValueError, match='lacks a captured transcript'):
            engine._subscription_transcript(result, tmp_path)
    else:
        assert engine._subscription_transcript(result, tmp_path) is None


@pytest.mark.parametrize('size', [True, -1, engine.c.HARD_LIMITS['stream_bytes'] + 1])
def test_invalid_transcript_size_refuses_before_open(tmp_path, monkeypatch, size):
    def forbidden(*args, **kwargs):
        pytest.fail('invalid transcript declaration was opened')
    monkeypatch.setattr(evidence, 'read_regular', forbidden)
    result = {'runtime_gates_passed': False, 'captured_files': {
        str(tmp_path / 'transcript.jsonl'): {'bytes': size, 'sha256': '0' * 64, 'roles': ['transcript']}}}
    with pytest.raises(ValueError, match='untyped or oversized'):
        engine._subscription_transcript(result, tmp_path)


def test_empty_captured_transcript_remains_bytes_not_absence(tmp_path):
    path = tmp_path / 'transcript.jsonl'
    path.write_bytes(b'')
    result = {'runtime_gates_passed': False, 'captured_files': {
        str(path): {'bytes': 0, 'sha256': guard.sha(b''), 'roles': ['transcript']}}}
    assert engine._subscription_transcript(result, tmp_path) == b''


def test_legacy_failed_replay_ignores_retained_transcript_as_before(tmp_path, legacy_case):
    instance = build_legacy(legacy_case)
    instance.before_dispatch()
    path = tmp_path / 'transcript.jsonl'
    body = b'not JSON; failed legacy replay deliberately ignores its buffered suffix'
    path.write_bytes(body)
    result = {'runtime_gates_passed': False, 'captured_files': {
        str(path): {'bytes': len(body), 'sha256': guard.sha(body), 'roles': ['transcript']}}}
    actual = engine._subscription_transcript(result, tmp_path)
    _, runtime, registration_raw, launch_word_raw, _ = legacy_case
    arguments = {'registration_raw': registration_raw, 'runtime': runtime,
        'launch_word_raw': launch_word_raw, 'complete': False}
    observed = legacy_guard.validate_saved_observations(instance.raw, instance.snapshot(),
        transcript_raw=actual, **arguments)
    absent = legacy_guard.validate_saved_observations(instance.raw, instance.snapshot(),
        transcript_raw=None, **arguments)
    assert observed == absent
    assert observed['checked'] is observed['complete'] is observed['passed'] is False
