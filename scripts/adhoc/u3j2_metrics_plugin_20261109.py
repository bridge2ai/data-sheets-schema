"""U3-J2 worker-local timing evidence, 2026-11-09.

Inputs: pytest phase hooks and U3J2_METRICS scratch directory. Outputs: one
append-only JSONL per process, including wall/process CPU and reaped-child CPU.
No production monkeypatches, deadline changes, profiling or provider effects.
Process CPU is this pytest worker's CPU, not a fabricated process-tree total.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import resource
import time

import pytest


def sample():
    own = resource.getrusage(resource.RUSAGE_SELF)
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {'wall_monotonic': time.monotonic(), 'process_cpu': time.process_time(),
            'self_user_cpu': own.ru_utime, 'self_system_cpu': own.ru_stime,
            'reaped_child_user_cpu': child.ru_utime,
            'reaped_child_system_cpu': child.ru_stime}


def event(node, phase, kind, start=None, outcome=None):
    directory = Path(os.environ['U3J2_METRICS'])
    directory.mkdir(exist_ok=True)
    now = sample()
    row = {'utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
           'worker': os.environ.get('PYTEST_XDIST_WORKER', 'controller'),
           'node': node, 'phase': phase, 'event': kind, 'sample': now}
    if start is not None:
        row['elapsed'] = {key: now[key] - value for key, value in start.items()}
    if outcome is not None:
        row['outcome'] = outcome
    with (directory / (str(os.getpid()) + '.jsonl')).open('a') as stream:
        stream.write(json.dumps(row, sort_keys=True) + '\n')
        stream.flush()
    return now


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    start = event(item.nodeid, 'setup', 'begin')
    result = yield
    event(item.nodeid, 'setup', 'end', start, 'error' if result.excinfo else 'returned')


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    start = event(item.nodeid, 'call', 'begin')
    result = yield
    event(item.nodeid, 'call', 'end', start, 'error' if result.excinfo else 'returned')


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item):
    start = event(item.nodeid, 'teardown', 'begin')
    result = yield
    event(item.nodeid, 'teardown', 'end', start, 'error' if result.excinfo else 'returned')


def pytest_runtest_logreport(report):
    event(report.nodeid, report.when, 'report', outcome=report.outcome)
