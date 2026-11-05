#!/usr/bin/env python3
"""Observe PR #5213 round-3 test timing and retained cache state, 2026-11-02.

Inputs: D76_OUTPUT and the already-loaded pytest process; output: append-only
per-process phase snapshots. Does not collect garbage, clear caches, import
production modules, or change a production function. RSS is peak RSS from
getrusage; the outer supervisor records current RSS separately where available.
"""
import gc
import json
import os
from pathlib import Path
import resource
import sys
import time

import pytest


def snapshot():
    caches = {}
    for module_name, module in tuple(sys.modules.items()):
        if not module_name.startswith('data_sheets_schema.'):
            continue
        for name, value in tuple(vars(module).items()):
            if type(value) in (dict, list, set) and any(word in name.lower() for word in ('cache', 'memo', 'views')):
                caches[module_name + '.' + name] = {'type': type(value).__name__, 'entries': len(value)}
    view_module = sys.modules.get('data_sheets_schema.schema_view')
    if view_module is not None:
        schema_view = vars(view_module).get('SchemaView')
        if schema_view is not None:
            for name, method in vars(schema_view).items():
                seen = set()
                while id(method) not in seen:
                    seen.add(id(method))
                    info = getattr(method, 'cache_info', None)
                    if callable(info):
                        caches['SchemaView.' + name] = dict(info()._asdict())
                        break
                    wrapped = getattr(method, '__wrapped__', None)
                    if wrapped is None:
                        break
                    method = wrapped
    usage = resource.getrusage(resource.RUSAGE_SELF)
    child_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    multiplier = 1 if sys.platform == 'darwin' else 1024
    return {'peak_rss_bytes': usage.ru_maxrss * multiplier,
            'completed_children_peak_rss_bytes': child_usage.ru_maxrss * multiplier,
            'user_seconds': usage.ru_utime, 'system_seconds': usage.ru_stime,
            'gc_count': list(gc.get_count()), 'gc_stats': gc.get_stats(),
            'gc_garbage_count': len(gc.garbage), 'caches': caches}


def emit(event, **values):
    output = Path(os.environ['D76_OUTPUT']) / ('metrics-' + str(os.getpid()) + '.jsonl')
    record = {'event': event, 'pid': os.getpid(), 'monotonic': time.monotonic(),
              'wall_time': time.time(), **values, 'state': snapshot()}
    with output.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(record, sort_keys=True) + '\n')


def pytest_sessionstart(session):
    emit('session_start')


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    emit('test_start', nodeid=item.nodeid)
    start = time.monotonic()
    yield
    emit('test_end', nodeid=item.nodeid, elapsed_seconds=time.monotonic() - start)


def pytest_runtest_logreport(report):
    emit('phase', nodeid=report.nodeid, when=report.when,
         outcome=report.outcome, duration_seconds=report.duration)


def pytest_sessionfinish(session, exitstatus):
    emit('session_end', exitstatus=int(exitstatus))
