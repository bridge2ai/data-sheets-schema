"""D156 process ownership tests using an ordinary sleeping Python child only."""
import os
import signal
import sys

import pytest

from data_sheets_schema import native_launch_sequence as sequence


def test_prepared_failure_kills_group_and_reaps_leader(tmp_path):
    state = sequence._SequenceSignals()
    steps = []
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', steps, state)
    owned.step['argv'] = [sys.executable, '-I', '-c', 'import time; time.sleep(60)']
    try:
        owned.start()
        assert os.getpgid(owned.child.pid) == owned.child.pid
        assert owned.child.poll() is None
        raise ValueError('synthetic capture refusal')
    except ValueError:
        owned.close()
    assert owned.child.returncode == -signal.SIGKILL
    assert steps[0]['return_code'] == -signal.SIGKILL
    assert steps[0]['completed_at'] is not None
    with pytest.raises(ProcessLookupError):
        os.killpg(owned.child.pid, 0)
    assert owned.stdout.closed and owned.stderr.closed


def test_spawn_failure_closes_reserved_streams(tmp_path, monkeypatch):
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', [], sequence._SequenceSignals())
    def refused(*args, **kwargs):
        raise OSError('synthetic spawn failure')
    monkeypatch.setattr(sequence.subprocess, 'Popen', refused)
    try:
        with pytest.raises(OSError, match='synthetic spawn failure'):
            owned.start()
    finally:
        owned.close()
    assert owned.child is None
    assert owned.stdout.closed and owned.stderr.closed
