"""U3-K offline profiling canary and pre-reservation diagnostic, 2026-11-09.

Explicit harness-only tests: the neutral diagnostic uses genuine make_case and
synthetic_launch, but stops exactly at attempt mkdir if every real prior guard
passes. It never dispatches the peer or alters a freshness/deadline policy.
The public completion nodes are separate final measurements, not these tests.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

import pytest

from scripts.adhoc import u3k_metrics_plugin_20261109 as metrics


def _recorder():
    if 'U3K_METRICS' not in os.environ:
        pytest.skip('explicit U3-K offline profiling harness required')
    return metrics.active()


def u3k_cpu_witness():
    until = time.thread_time() + 0.05
    while time.thread_time() < until:
        sum(range(20))


def test_profile_observer_canary(tmp_path):
    recorder = _recorder()
    from tests.utils.native_shared_consumer_scope import observe_consumer_calls
    target = {(Path(__file__).stem, 'u3k_cpu_witness'): ()}
    with recorder.phase('legacy_observer_canary', force_unprofiled=True):
        # The passive sys.monitoring observer must preserve the legacy
        # sys.setprofile observer's detection and refusal. cProfile is separate:
        # its non-callable Profile object cannot be chained by that observer.
        with observe_consumer_calls(target) as calls:
            u3k_cpu_witness()
        assert len(calls) == 1
        with pytest.raises(AssertionError, match='forbidden production operation'):
            with observe_consumer_calls(target, forbid=True):
                u3k_cpu_witness()
    assert recorder.phases[-1]['profiled'] is False
    with recorder.phase('canary', force_profile=True):
        # Diagnostic profiling calls synthetic_launch directly, without the
        # legacy launch_case observer; the public passive path remains intact.
        u3k_cpu_witness()
        first, second = {}, {}
        source = 'def u3k_dynamic_witness():\n    return 19\n'
        exec(compile(source, __file__, 'exec'), first)
        exec(compile(source, __file__, 'exec'), second)
        assert first['u3k_dynamic_witness']() == second['u3k_dynamic_witness']() == 19
        assert first['u3k_dynamic_witness'].__code__ is not second['u3k_dynamic_witness'].__code__
        # This ordinary temporary mkdir is a measurement canary only; no native
        # registration or guard is invented or accepted for it.
        path = tmp_path / 'observer-mkdir-canary'
        recorder.attempt_path = str(path)
        path.mkdir()
        recorder.attempt_path = None
    dynamic = [row for row in recorder.rows if row['label'] == 'canary_dynamic_code']
    assert len(dynamic) == 2
    assert len({row['code_object_id'] for row in dynamic}) == 2
    assert all(row['outcome'] == 'return' for row in dynamic)
    boundaries = [row for row in recorder.rows if row['label'] == 'attempt_mkdir']
    assert len(boundaries) == 1 and boundaries[0]['outcome'] == 'return'
    assert boundaries[0]['attempt_path'] == str(path) and path.is_dir()
    measured = recorder.phases[-1]
    assert measured['profiled'] and measured['elapsed']['thread_cpu'] >= 0.05
    assert Path(measured['profile']['path']).stat().st_size > 0
    functions = json.loads(Path(measured['profile_json']['path']).read_bytes())['functions']
    cpu = [row for row in functions if row['name'] == 'u3k_cpu_witness']
    assert cpu and sum(row['calls'] for row in cpu) >= 1
    assert all(row['self_thread_cpu'] >= 0 and row['inclusive_thread_cpu'] >= 0 for row in cpu)
    assert all(row['outcome'] != 'open' for row in recorder.rows)
    assert all(not stack for stack in recorder.stacks.values())


class _ReachedReservation(RuntimeError):
    pass


def test_neutral_pre_reservation_diagnostic(tmp_path, monkeypatch):
    recorder = _recorder()
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    monkeypatch.chdir(authority.ROOT)
    with recorder.phase('fixture'):
        case = make_case(tmp_path / 'u3k-neutral')
    attempt = Path(case['value']['attempt_directory'])
    evidence = Path(case['value']['evidence_directory'])
    guard = json.loads(Path(case['kwargs']['subscription_guard_path']).read_bytes())
    captured = datetime.fromisoformat(guard['captured_at'].replace('Z', '+00:00'))
    assert captured.tzinfo is not None
    original = Path.mkdir
    reached = []

    def stop_at_exact_attempt(path, *args, **kwargs):
        if path == attempt:
            reached.append(metrics.sample())
            raise _ReachedReservation('U3-K diagnostic stopped at exact attempt mkdir; no reservation made')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'mkdir', stop_at_exact_attempt)
    result = {'profile': 'synthetic-software-test', 'fixture': 'neutral',
        'attempt_limit_seconds': 900, 'helper_limit_seconds': 180,
        'capture_timestamp': guard['captured_at'],
        'capture_age_limit_seconds': guard['max_age_seconds'],
        'capture_margin_seconds': guard['pre_reservation_margin_seconds'],
        'scope': 'Genuine make_case + synthetic_launch; no launch_case profile observer. OS sandbox denies native/network; exact attempt mkdir is a diagnostic stop, not a passed launch.'}
    try:
        with recorder.phase('launch'):
            execute.synthetic_launch(case['raw'], **case['kwargs'])
    except _ReachedReservation as exc:
        assert len(reached) == 1
        result.update(outcome='reached_reservation_without_effect', error=str(exc),
            reservation_boundary=reached[0],
            capture_to_reservation_wall_seconds=(
                datetime.fromisoformat(reached[0]['utc']) - captured).total_seconds())
    except ValueError as exc:
        result.update(outcome='genuine_refusal', error=str(exc),
            reservation_boundary=None, capture_to_reservation_wall_seconds=None)
        if not any(text in str(exc) for text in ('subscription observation is stale or future-dated',
                'subscription pre-reservation freshness margin is insufficient')):
            raise
    else:
        raise AssertionError('diagnostic escaped the exact pre-reservation stop')
    finally:
        result.update(attempt_exists=os.path.lexists(attempt), evidence_exists=os.path.lexists(evidence),
            observed_at=datetime.now(timezone.utc).isoformat())
        recorder.save('diagnostic.json', result)
    assert not os.path.lexists(attempt)
    assert not os.path.lexists(evidence)
    assert recorder.phases[-1]['name'] == 'launch'
