"""Retain U3-B pytest outcomes before a deadline, 2026-11-07.

Input: ordinary pytest reports. Output: controller-only scratch JSONL with
node IDs, outcomes and failure text. Observation only; no test monkeypatching.
"""
import json
import os
from pathlib import Path

_WORKER = False

def pytest_configure(config):
    global _WORKER
    _WORKER = hasattr(config, 'workerinput')

def pytest_runtest_logreport(report):
    path = os.environ.get('U3B_EVENT_LOG')
    if _WORKER or not path or not (report.when == 'call' or report.failed or report.skipped):
        return
    row = {'nodeid': report.nodeid, 'phase': report.when, 'outcome': report.outcome,
           'duration': report.duration}
    if report.failed:
        row['failure'] = report.longreprtext
    with Path(path).open('a') as stream:
        stream.write(json.dumps(row) + '\n')
