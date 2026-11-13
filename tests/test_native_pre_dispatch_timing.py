"""Diagnostic spans persist without becoming admission authority."""
import json

import pytest

from data_sheets_schema import native_pre_dispatch_timing as timing


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_capture_and_later_launch_share_file_and_continuous_clock(tmp_path, monkeypatch):
    tick = iter(range(100, 1000))
    monkeypatch.setattr(timing, 'elapsed_ns', lambda: next(tick))
    value = {'attempt_directory': str(tmp_path / 'attempt')}
    raw = b'explicit-test-registration'
    with timing.scope(raw) as capture:
        timing.bind(value)
        timing.record('capture_observed', captured_at='invented')
    with timing.scope(raw) as launch:
        with timing.step('registration.verified'):
            assert launch.path is None
            timing.bind(value)
        with timing.step('current_guard_preparation'):
            with timing.step('_current_authority'):
                pass
        with timing.step('admission_with_classifier'):
            pass
        with timing.step('controller_prewarm'):
            pass
        with timing.step('reservation'):
            timing.record('attempt_reserved')
    assert capture.path == launch.path
    saved = rows(launch.path)
    assert saved[0]['boundary'] == 'capture_observed'
    assert [row['elapsed_ns'] for row in saved] == sorted(row['elapsed_ns'] for row in saved)
    starts = {row['step_id']: row for row in saved if row.get('phase') == 'start'}
    ends = {row['step_id']: row for row in saved if row.get('phase') == 'end'}
    assert starts.keys() == ends.keys() and len(starts) == 6
    assert all(starts[key]['elapsed_ns'] < ends[key]['elapsed_ns'] for key in starts)
    assert not (tmp_path / 'attempt').exists()


def test_failure_end_records_original_exception_and_readback_has_no_scope(tmp_path):
    with timing.scope(b'failure') as trace:
        timing.bind({'attempt_directory': str(tmp_path / 'attempt')})
        with pytest.raises(ValueError, match='original'):
            with timing.step('_current_authority'):
                raise ValueError('original')
    assert rows(trace.path)[-1]['error_type'] == 'ValueError'
    before = trace.path.read_bytes()
    with timing.step('registration.verified'):
        timing.bind({'attempt_directory': str(tmp_path / 'attempt')})
    assert trace.path.read_bytes() == before


def test_diagnostic_disk_failure_does_not_replace_verification_error(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise OSError('invented disk failure')
    with timing.scope(b'disk') as trace:
        monkeypatch.setattr(timing.os, 'open', broken)
        timing.bind({'attempt_directory': str(tmp_path / 'attempt')})
        with pytest.raises(KeyError, match='real verification error'):
            with timing.step('admission_with_classifier'):
                raise KeyError('real verification error')
        assert trace.disabled


def test_symlink_sidecar_refuses_without_touching_target(tmp_path):
    trace = timing.Trace(b'symlink')
    target = tmp_path / 'unrelated'
    target.write_bytes(b'unchanged')
    path = tmp_path / ('host-pre-dispatch-' + trace.identity + '.jsonl')
    path.symlink_to(target)
    trace.bind({'attempt_directory': str(tmp_path / 'attempt')})
    trace.record('capture_observed')
    assert trace.disabled and target.read_bytes() == b'unchanged'


def test_size_limit_disables_observation_only(tmp_path, monkeypatch):
    monkeypatch.setattr(timing, 'MAX_BYTES', 1)
    with timing.scope(b'bounded') as trace:
        timing.bind({'attempt_directory': str(tmp_path / 'attempt')})
        timing.record('capture_observed')
        assert trace.disabled
        assert trace.path.stat().st_size == 0
