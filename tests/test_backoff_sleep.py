"""Regression coverage for sleep patches around subprocess timeout waits."""
import subprocess
import sys
import time

from tests.backoff_sleep import BackoffSleeps


def test_short_sleeps_delegate_but_backoffs_are_recorded(monkeypatch):
    from tests import backoff_sleep

    delegated = []
    monkeypatch.setattr(backoff_sleep, "_real_sleep", delegated.append)
    sleeps = BackoffSleeps()
    monkeypatch.setattr(time, "sleep", sleeps)
    for delay in (0, 0.001, 0.032, 0.05, 1.0, 2, 4):
        time.sleep(delay)
    assert delegated == [0, 0.001, 0.032, 0.05]
    assert sleeps == [1.0, 2, 4]


def test_timeout_wait_preserves_child_progress_without_recording_backoff(monkeypatch):
    sleeps = BackoffSleeps()
    monkeypatch.setattr(time, "sleep", sleeps)
    with subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.1)"]) as child:
        assert child.wait(timeout=10) == 0
    assert sleeps == []
