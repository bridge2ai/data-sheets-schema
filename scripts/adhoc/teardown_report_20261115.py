"""Issue 6214, 2026-11-15: retain per-test outcomes for bounded pytest runs."""
import json
import os
from pathlib import Path


def pytest_runtest_logreport(report):
    path = os.environ.get('TEARDOWN_REPORT_PATH')
    if path and not os.environ.get("PYTEST_XDIST_WORKER") and (report.when == 'call' or report.failed):
        row = dict(nodeid=report.nodeid, when=report.when, outcome=report.outcome,
                   duration=report.duration, detail=str(report.longrepr) if report.failed else None)
        with Path(path).open('a') as stream:
            stream.write(json.dumps(row) + '\n')
