"""PR 5968 CI shard reconstruction and cache-state trace, 2026-11-16.

Inputs: pytest collection, optional saved CI worker order. Outputs: scratch JSON
collection and before/after cache support records. Run only through run_lane.
"""
import json
from pathlib import Path
import sys


def pytest_addoption(parser):
    parser.addoption('--cache-order-output')
    parser.addoption('--cache-order-input')


def pytest_collection_modifyitems(config, items):
    source = config.getoption('--cache-order-input')
    if source:
        nodes = json.loads(Path(source).read_text())
        lookup = {item.nodeid: item for item in items}
        missing = [node for node in nodes if node not in lookup]
        if missing:
            raise ValueError(f'missing replay nodes: {missing}')
        items[:] = [lookup[node] for node in nodes]


def pytest_collection_finish(session):
    destination = session.config.getoption('--cache-order-output')
    if destination:
        Path(destination).write_text(json.dumps([item.nodeid for item in session.items], indent=2) + '\n')


def _record(item, phase):
    destination = item.config.getoption('--cache-order-output')
    catalog = sys.modules.get('data_sheets_schema.native_catalog_reuse')
    if not destination or catalog is None:
        return
    record = {'node': item.nodeid, 'phase': phase,
              'supported': catalog.runtime_token() is not None}
    if not record['supported']:
        try:
            actual = catalog._state()
            record['changed_components'] = [index for index, (old, new) in
                enumerate(zip(catalog._STATE, actual)) if old != new]
        except Exception as exc:
            record['state_error'] = str(exc)
    with Path(destination + '.trace.jsonl').open('a') as stream:
        stream.write(json.dumps(record) + '\n')


def pytest_runtest_setup(item):
    _record(item, 'before')


def pytest_runtest_logfinish(nodeid, location):
    # The next setup sees the preceding test's fully completed teardown.
    pass
