"""U3-C quiet-lock runner regressions, 2026-11-07.

Synthetic clocks, locks and process signals only; no job or subprocess starts.
"""
import importlib.util
from pathlib import Path
import shutil
import signal
import tempfile

import pytest


SOURCE = Path(__file__).resolve().parents[1] / 'scripts/adhoc/run_native_u3a_tests_20261107.py'


def _temp_base():
    for candidate in (Path(tempfile.gettempdir()), Path('/tmp')):
        try:
            resolved = candidate.resolve(strict=True)
            if 'd4d-executions' in resolved.parts:
                continue
            with tempfile.TemporaryDirectory(dir=resolved):
                pass
            return resolved
        except OSError:
            continue
    raise RuntimeError('no writable temporary directory outside d4d-executions')


def _driver():
    with tempfile.TemporaryDirectory(dir=_temp_base()) as raw_temp:
        root = Path(raw_temp).resolve(strict=True) / 'd4d-executions'
        (root / 'plans').mkdir(parents=True)
        copy = root / 'checkout/scripts/adhoc/run_native_u3a_tests_20261107.py'
        copy.parent.mkdir(parents=True)
        shutil.copy2(SOURCE, copy)
        spec = importlib.util.spec_from_file_location('native_u3c_quiet_runner', copy)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


driver = pytest.fixture(scope='module')(_driver)


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class Lock:
    def __init__(self, clock):
        self.clock = clock
        self.present = False
        self.reads = []
        self.read_duration = 0.0

    def exists(self):
        self.reads.append(self.clock.now)
        self.clock.now += self.read_duration
        return self.present


class Owned:
    def __init__(self, clock):
        self.clock = clock
        self.signals = []

    def signal(self, number):
        self.signals.append((self.clock.now, number))


def _setup(driver_module):
    clock = Clock()
    lock, owned = Lock(clock), Owned(clock)
    return clock, lock, owned, driver_module.QuietWindow(lock, clock)


def test_new_lock_is_detected_on_next_quarter_second_tick(driver):
    clock, lock, owned, quiet = _setup(driver)
    quiet.update(owned)
    assert not quiet.paused and owned.signals == []
    lock.present = True
    clock.now = 0.25
    quiet.update(owned)
    assert quiet.paused
    assert lock.reads == [0.0, 0.25]
    assert owned.signals == [(0.25, signal.SIGSTOP)]


def test_paused_runner_does_not_poll_removal_more_than_once_per_minute(driver):
    clock, lock, owned, quiet = _setup(driver)
    lock.present = True
    quiet.update(owned)
    for tick in range(1, 240):
        clock.now = tick / 4
        quiet.update(owned)
    assert lock.reads == [0.0]
    assert owned.signals == [(0.0, signal.SIGSTOP)]
    clock.now = 60.0
    quiet.update(owned)
    clock.now = 119.75
    quiet.update(owned)
    assert lock.reads == [0.0, 60.0]
    assert quiet.paused and owned.signals == [(0.0, signal.SIGSTOP)]


def test_release_is_detected_at_next_minute_then_acquisition_is_prompt_again(driver):
    clock, lock, owned, quiet = _setup(driver)
    lock.present = True
    quiet.update(owned)
    lock.present = False
    clock.now = 0.25
    quiet.update(owned)
    clock.now = 59.75
    quiet.update(owned)
    assert lock.reads == [0.0] and quiet.paused
    clock.now = 60.0
    quiet.update(owned)
    assert not quiet.paused
    assert owned.signals == [(0.0, signal.SIGSTOP), (60.0, signal.SIGCONT)]
    lock.present = True
    clock.now = 60.25
    quiet.update(owned)
    assert lock.reads == [0.0, 60.0, 60.25]
    assert quiet.paused and owned.signals[-1] == (60.25, signal.SIGSTOP)


def test_removal_poll_interval_starts_after_filesystem_observation(driver):
    clock, lock, owned, quiet = _setup(driver)
    lock.present, lock.read_duration = True, 2.0
    quiet.update(owned)
    assert quiet.next_removal_check == 62.0
    clock.now = 60.0
    quiet.update(owned)
    assert lock.reads == [0.0]
    clock.now = 62.0
    quiet.update(owned)
    assert lock.reads == [0.0, 62.0]
