"""One cheap U3-J2 harness canary; inspect its persisted worker timing witness."""
import json
import os
from pathlib import Path
import pytest


def test_timing_plugin_runs_in_selected_xdist_worker():
    if 'U3J2_METRICS' not in os.environ:
        pytest.skip('U3-J2 harness-specific worker witness')
    assert os.environ['PYTEST_XDIST_WORKER'] == 'gw0'
    path = Path(os.environ['U3J2_METRICS']) / (str(os.getpid()) + '.jsonl')
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert any(row['phase'] == 'call' and row['event'] == 'begin' for row in rows)
    assert all(row['worker'] == 'gw0' and row['pid'] == os.getpid() for row in rows)
    assert rows[-1]['sample']['process_cpu'] > 0
