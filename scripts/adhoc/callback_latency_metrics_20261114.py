"""Measure issue 6233 without replacing the public test's profiler guard.

2026-11-14. Input: CALLBACK_METRICS output path and an ordinary pytest case.
Output: nested wall/thread CPU spans in JSON. Diagnostic only, no authority edits.
Load as a pytest plugin before the test installs its monitoring/audit guard.
"""
import json
import os
from pathlib import Path
import sys
import threading
import time

TARGETS = {
    'native_shared_controller_orchestration.py': {'observe', '_observe', '_run', '_phase_state', 'report'},
    'native_shared_callback_orchestration.py': {'classify', '__call__', 'check'},
    'native_shared_callback_capture.py': {'reconstruct', 'base'},
    'native_execution_authority_v2.py': {'_verified_source_bytes', 'module_source_identity'},
    'native_shared_selection.py': {'capture', '_schemas', '_rebuild'},
    'native_shared_registration.py': {'rebuild_v2_body', '_selection'},
    'native_shared_permissions.py': {'verify_saved_probe'},
    'native_shared_receipts.py': {'schema_data', '_fresh_schema_data'},
    'native_catalog_reuse.py': {'runtime_token'},
    'native_shared_capture.py': {'_checked_observations', 'decision', '_loaded'},
    'native_control.py': {'_intake_history', '_start_work', '_collect_work',
                          '_classify_frame', '_observe_event', 'close'},
    'native_shared_evidence.py': {'read_regular'},
    'native_shared_contract.py': {'sha'},
}
ROWS = []
STACKS = {}
INTAKES = {}
TOOL = 3


def enter(code, offset):
    name = code.co_filename.rsplit('/', 1)[-1]
    if code.co_name not in TARGETS.get(name, ()):
        return sys.monitoring.DISABLE
    sys.monitoring.set_local_events(TOOL, code, sys.monitoring.events.PY_RETURN)
    frame = sys._getframe(1)
    event = frame.f_locals.get('event', frame.f_locals.get('frame'))
    row = {'file': name, 'function': code.co_qualname, 'thread': threading.get_ident(),
           'start': time.monotonic(), 'cpu_start': time.thread_time()}
    if isinstance(event, dict):
        row['event'] = {key: event.get(key) for key in ('type', 'request_id')}
    ROWS.append(row)
    STACKS.setdefault(threading.get_ident(), []).append((code, row))


def leave(code, offset, value):
    stack = STACKS.get(threading.get_ident(), [])
    if not stack or stack[-1][0] is not code:
        return
    _, row = stack.pop()
    row['end'] = time.monotonic()
    row['wall'] = row['end'] - row['start']
    row['cpu'] = time.thread_time() - row['cpu_start']
    if code.co_name == '_intake_history':
        control = sys._getframe(1).f_locals.get('self')
        for request, received in getattr(control, '_callback_intake', {}).items():
            INTAKES.setdefault(request, received)


def pytest_sessionstart(session):
    monitor = sys.monitoring
    monitor.use_tool_id(TOOL, 'callback-latency-6233')
    monitor.register_callback(TOOL, monitor.events.PY_START, enter)
    monitor.register_callback(TOOL, monitor.events.PY_RETURN, leave)
    monitor.register_callback(TOOL, monitor.events.PY_UNWIND, leave)
    monitor.set_events(TOOL, monitor.events.PY_START | monitor.events.PY_UNWIND)


def pytest_sessionfinish(session, exitstatus):
    monitor = sys.monitoring
    monitor.set_events(TOOL, 0)
    for event in (monitor.events.PY_START, monitor.events.PY_RETURN, monitor.events.PY_UNWIND):
        monitor.register_callback(TOOL, event, None)
    monitor.free_tool_id(TOOL)
    path = Path(os.environ['CALLBACK_METRICS'])
    path.write_text(json.dumps({'exitstatus': int(exitstatus), 'intakes': INTAKES,
                               'spans': ROWS}, separators=(',', ':')))
    assert path.stat().st_size > 0
