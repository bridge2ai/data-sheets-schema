"""#6170: dispatch origin and suspended deadlines; no real model or sleep."""
from pathlib import Path
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


@pytest.mark.parametrize('source', ['Battery Power', 'unrecognized'])
def test_unplug_after_sequence_start_refuses_public_dispatch(tmp_path, monkeypatch, source):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_execution_orchestration as engine
    monkeypatch.chdir(authority.ROOT)
    power.sequence_start(tmp_path / 'sequence-start.json', 'synthetic')
    case = make_case(tmp_path / 'unplug')
    attempted = []
    def attempt_dispatch(controls, argv, **kw):
        kw['verify_launch']()
        attempted.append(True)
        pytest.fail('unplugged host reached child dispatch')
    monkeypatch.setattr(engine, '_execute_child', attempt_dispatch)
    monkeypatch.setattr(power, '_local', lambda *a, **k: {'status': 'read', 'reason': None,
        'text': "Now drawing from '" + source + "'\n"})
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert attempted == []
    assert result['state'] == 'failed' and result['child_exit_code'] is None
    assert result['first_stop'] == 'launch or runtime failed: ValueError'
    assert execute.read_final(case['raw']) == result
