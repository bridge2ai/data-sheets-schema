"""#6170: dispatch origin and suspended deadlines; no real model or sleep."""
from pathlib import Path
import json
import sys
from types import SimpleNamespace
import threading

import pytest
from data_sheets_schema import native_elapsed as clock
from data_sheets_schema import native_host_power as power
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401

pytestmark = pytest.mark.usefixtures('isolated_modules')


def runner_module():
    from data_sheets_schema import native_attribution_controller as controller
    return controller.load_controls()['run_native_canary']


@pytest.mark.parametrize('seconds', [900, 21600, 43200])
@pytest.mark.parametrize('exited_during_sleep', [False, True])
def test_suspension_expires_every_registered_deadline(tmp_path, monkeypatch, seconds, exited_during_sleep):
    runner = runner_module()
    ticks = {'continuous': 0}
    process = SimpleNamespace()
    closed, killed = [], []
    proxy = SimpleNamespace(failed=threading.Event(), failure=None, close_admission=lambda: closed.append(True))
    instruction = tmp_path / 'instruction'; instruction.write_text('inert fixture')
    def verify():
        ticks['continuous'] += 899 * 10**9  # Within admission's own bound; excluded from child time.
    def spawn(*a, **kw):
        ticks['continuous'] += (seconds + 1) * 10**9  # Suspend immediately at dispatch.
        return process
    monkeypatch.setattr(runner, 'elapsed_ns', lambda: ticks['continuous'])
    monkeypatch.setattr(runner, 'exit_check_available', lambda: True)
    monkeypatch.setattr(runner, 'leader_exited', lambda p: exited_during_sleep)
    monkeypatch.setattr(runner.subprocess, 'Popen', spawn)
    monkeypatch.setattr(runner, 'terminate_group', lambda p: killed.append(p))
    with pytest.raises(runner.BudgetStop, match='attempt deadline elapsed'):
        runner.execute_child(['inert'], proxy=proxy, instruction=instruction, attempt=tmp_path,
            cwd=tmp_path, env={}, deadline_seconds=seconds, verify_launch=verify)
    assert closed and killed == [process]


@pytest.mark.parametrize('seconds', [900, 21600, 43200])
def test_admission_time_is_excluded_from_child_deadline(tmp_path, monkeypatch, seconds):
    runner = runner_module()
    ticks = {'continuous': 0}
    instruction = tmp_path / 'instruction'; instruction.write_text('inert')
    def verify(): ticks['continuous'] += 899 * 10**9
    monkeypatch.setattr(runner, 'elapsed_ns', lambda: ticks['continuous'])
    monkeypatch.setattr(runner, 'exit_check_available', lambda: True)
    monkeypatch.setattr(runner, 'leader_exited', lambda p: True)
    def spawn(*args, **kwargs):
        # Correct origin: child is still within its own budget. Wrong entry
        # origin: admission plus child time is one second beyond the deadline.
        ticks['continuous'] += (seconds - 898) * 10**9
        return object()
    monkeypatch.setattr(runner.subprocess, 'Popen', spawn)
    monkeypatch.setattr(runner, 'terminate_group', lambda p: None)
    monkeypatch.setattr(runner, 'exit_status', lambda p: 0)
    proxy = SimpleNamespace(failed=threading.Event(), failure=None, close_admission=lambda: None)
    assert runner.execute_child(['inert'], proxy=proxy, instruction=instruction, attempt=tmp_path,
        cwd=tmp_path, env={}, deadline_seconds=seconds, verify_launch=verify) == 0


@pytest.mark.parametrize('admission_seconds', [900, 901])
def test_dispatch_backstop_refuses_without_any_alarm_delivery(tmp_path, monkeypatch, admission_seconds):
    from data_sheets_schema.native_admission_timer import AdmissionExpired
    runner = runner_module()
    ticks = [0]
    instruction = tmp_path / 'instruction'; instruction.write_text('inert')
    opened, closed, spawned = [], [], []
    original_open = Path.open
    def tracked_open(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        if path in (instruction, tmp_path / 'transcript.jsonl', tmp_path / 'stderr.txt'):
            opened.append(stream)
        return stream
    monkeypatch.setattr(Path, 'open', tracked_open)
    monkeypatch.setattr(runner, 'elapsed_ns', lambda: ticks[0])
    # Deliberately suppress delivery to isolate the authoritative synchronous
    # check. Removing check(dispatch_ns) must make this regression fail.
    monkeypatch.setattr(runner.AdmissionTimer, '_alarm', lambda *args: None)
    monkeypatch.setattr(runner, 'exit_check_available', lambda: True)
    monkeypatch.setattr(runner.subprocess, 'Popen', lambda *a, **k: spawned.append(True))
    monkeypatch.setattr(runner, 'terminate_group', lambda process: None)
    proxy = SimpleNamespace(failed=threading.Event(), failure=None, close_admission=lambda: closed.append(True))
    def verify():
        ticks[0] = admission_seconds * 10**9
    with pytest.raises(AdmissionExpired, match='child was not dispatched'):
        runner.execute_child(['inert'], proxy=proxy, instruction=instruction, attempt=tmp_path,
            cwd=tmp_path, env={}, deadline_seconds=900, verify_launch=verify)
    assert spawned == [] and closed
    assert len(opened) == 3 and all(stream.closed for stream in opened)


def test_macos_continuous_ticks_use_integer_timebase_and_no_wall_clock(monkeypatch):
    monkeypatch.setattr(clock.sys, 'platform', 'darwin')
    monkeypatch.setattr(clock, '_mach_clock', lambda: (lambda: 12_000_000_000, 125, 3))
    monkeypatch.setattr(clock.time, 'time_ns', lambda: pytest.fail('adjustable clock'))
    assert clock.elapsed_ns() == 500_000_000_000


def _power_refusal_probe(source):
    if source == 'probe_failure':
        return {'status': 'unknown', 'reason': 'TimeoutError', 'text': ''}
    return {'status': 'read', 'reason': None, 'returncode': 0,
            'text': "Now drawing from '" + source + "'\n"}


@pytest.mark.parametrize('source,persistence_failure', [
    ('Battery Power', False), ('unrecognized', False), ('probe_failure', False),
    ('Battery Power', True),
])
def test_unplug_before_reservation_keeps_attempt_unspent(tmp_path, monkeypatch, source, persistence_failure):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_execution_orchestration as engine
    from data_sheets_schema import native_pre_dispatch_timing as timing
    monkeypatch.chdir(authority.ROOT)
    traces = []
    handoff = timing._handoff
    def remember(trace):
        traces.append(trace)
        handoff(trace)
    monkeypatch.setattr(timing, '_handoff', remember)
    power.sequence_start(tmp_path / 'sequence-start.json', 'synthetic')
    case = make_case(tmp_path / 'unplug-before-reservation')
    for trace in traces:
        assert trace._persisted.wait(5)
    traces.clear()
    attempt = Path(case['value']['attempt_directory'])
    evidence = Path(case['value']['evidence_directory'])
    sidecar = attempt.parent / ('host-pre-dispatch-' + execute.c.sha(case['raw']) + '.jsonl')
    before = sidecar.read_bytes() if sidecar.exists() else b''
    if persistence_failure:
        real_open = timing.os.open
        def unavailable(path, *args, **kwargs):
            if path == sidecar or path == str(sidecar):
                raise OSError('synthetic diagnostic disk failure')
            return real_open(path, *args, **kwargs)
        monkeypatch.setattr(timing.os, 'open', unavailable)
    def forbidden(*args, **kwargs):
        pytest.fail('power refusal reached reserved runtime work')
    monkeypatch.setattr(engine, '_execute_child', forbidden)
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', forbidden)
    monkeypatch.setattr(power, '_local', lambda *a, **k: _power_refusal_probe(source))
    with pytest.raises(power.DispatchPowerRefused, match='positively observed as AC') as caught:
        execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert not attempt.exists() and not evidence.exists()
    assert len(traces) == 1 and traces[0]._persisted.wait(5)
    assert traces[0].disabled is persistence_failure
    current = sidecar.read_bytes() if sidecar.exists() else b''
    if persistence_failure:
        assert current == before
    else:
        assert current.startswith(before)
        rows = [json.loads(line) for line in current[len(before):].splitlines()]
        power_rows = [row for row in rows if row['boundary'] == 'reservation_power']
        assert len(power_rows) == 1 and power_rows[0]['passed'] is False
        assert all(power_rows[0][key] == value for key, value in caught.value.reading.items())
        assert not any(row['boundary'] == 'attempt_reserved' for row in rows)


@pytest.mark.parametrize('source', ['Battery Power', 'unrecognized', 'probe_failure'])
def test_unplug_after_reservation_retains_reading_without_consuming_dispatch(tmp_path, monkeypatch, source):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_execution_orchestration as engine
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'unplug-after-reservation')
    original_execute = engine._execute_child
    original_power = power.dispatch_power
    readings, refusals, entered = [], [], []
    def observe_power():
        try:
            reading = original_power()
        except power.DispatchPowerRefused as exc:
            refusals.append(exc)
            raise
        readings.append(reading)
        return reading
    monkeypatch.setattr(power, 'dispatch_power', observe_power)
    def no_native_dispatch(controls, argv, **kwargs):
        entered.append(True)
        # Keep the actual reviewed transport, timer, verify_launch and error
        # handling. Only switch the synthetic power reading before admission.
        runner = sys.modules['run_native_canary']
        real_popen = runner.subprocess.Popen
        def popen(command, *args, **named):
            if list(command) == list(argv):
                pytest.fail('unplugged host reached child dispatch')
            return real_popen(command, *args, **named)
        with monkeypatch.context() as patch:
            patch.setattr(power, '_local', lambda *a, **k: _power_refusal_probe(source))
            patch.setattr(runner.subprocess, 'Popen', popen)
            return original_execute(controls, argv, **kwargs)
    monkeypatch.setattr(engine, '_execute_child', no_native_dispatch)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert entered == [True] and len(readings) == len(refusals) == 1
    assert readings[0]['source'] == 'ac'
    assert result['state'] == 'failed' and result['child_exit_code'] is None
    assert result['first_stop'] == 'dispatch power refused: ' + str(refusals[0])
    assert result['gates']['first_stop'] == {
        'checked': True, 'passed': False, 'reason': result['first_stop']}
    assert result['subscription_guard']['dispatched'] is False
    assert result['subscription_guard']['dispatched_at'] is None
    attempt = Path(case['value']['attempt_directory'])
    assert attempt.is_dir() and not (attempt / 'subscription-dispatched.json').exists()
    assert (attempt / 'transcript.jsonl').read_bytes() == b''
    assert execute.read_final(case['raw']) == result


def test_slow_power_probe_cannot_age_an_already_checked_reservation_margin(tmp_path, monkeypatch):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_execution_orchestration as engine
    from data_sheets_schema import native_subscription_guard_v2 as subscription
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'slow-power-probe')
    guard = json.loads(Path(case['kwargs']['subscription_guard_path']).read_bytes())
    captured = subscription._timestamp(guard['captured_at'], 'synthetic capture time')
    ticks = [captured + guard['max_age_seconds'] - guard['pre_reservation_margin_seconds'] - 1]
    monkeypatch.setattr(subscription, '_now', lambda: ticks[0])
    original = power.dispatch_power
    probes = []
    def slow_probe():
        probes.append(True)
        result = original()
        ticks[0] += 2  # Still fresh for dispatch, but below the required reserve margin.
        return result
    monkeypatch.setattr(power, 'dispatch_power', slow_probe)
    monkeypatch.setattr(engine, '_execute_child',
        lambda *a, **k: pytest.fail('expired preparation margin reached transport'))
    with pytest.raises(ValueError, match='pre-reservation freshness margin is insufficient'):
        execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert probes == [True]
    assert not Path(case['value']['attempt_directory']).exists()
    assert not Path(case['value']['evidence_directory']).exists()
