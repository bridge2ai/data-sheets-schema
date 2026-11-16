"""Pytest timing observer for the D156 public correction case, 2026-11-16.

Input: D4D_CAPTURE_ORDER_TIMING names a new JSONL file outside the repository.
Output: completed observer/callback spans; no source, clock or gate replacement.
Serves the capture-order handoff. Load with pytest's explicit plugin option.
"""
import json
import os
from pathlib import Path
import sys
import threading
import time

SELECTED = {
    'native_control.py': {'_observe_event', '_classify_frame'},
    'native_shared_capture.py': {'at_callback'},
    'native_prepared_worker.py': {'exchange', 'recheck'},
    'native_synthetic_evidence.py': {'_mint_capture'},
    'native_execution_orchestration.py': {'_admit_subscription_guard'},
}
active = {}
stream = None
tool = 4


def begin(code, offset):
    name = Path(code.co_filename).name
    if code.co_name not in SELECTED.get(name, ()):
        return sys.monitoring.DISABLE
    key = (threading.get_ident(), code)
    active.setdefault(key, []).append((time.monotonic(), time.time()))
    sys.monitoring.set_local_events(tool, code, sys.monitoring.events.PY_RETURN)


def end(code, offset, result):
    key = (threading.get_ident(), code)
    stack = active.get(key)
    if stack:
        began, wall = stack.pop()
        stream.write(json.dumps({'file': Path(code.co_filename).name,
            'function': code.co_name, 'thread': key[0], 'started_wall': wall,
            'completed_wall': time.time(), 'seconds': time.monotonic() - began}) + '\n')


def pytest_configure(config):
    global stream
    destination = Path(os.environ['D4D_CAPTURE_ORDER_TIMING'])
    if not destination.is_absolute():
        raise ValueError('timing output must be absolute')
    stream = destination.open('x', buffering=1)
    stream.write(json.dumps({'event': 'observer_started', 'wall': time.time()}) + '\n')
    sys.monitoring.use_tool_id(tool, 'capture-order-measurement')
    sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, begin)
    sys.monitoring.register_callback(tool, sys.monitoring.events.PY_RETURN, end)
    sys.monitoring.set_events(tool, sys.monitoring.events.PY_START)


def pytest_unconfigure(config):
    if stream is None:
        return
    sys.monitoring.set_events(tool, 0)
    for _, code in active:
        sys.monitoring.set_local_events(tool, code, 0)
    sys.monitoring.free_tool_id(tool)
    stream.write(json.dumps({'event': 'observer_finished', 'wall': time.time()}) + '\n')
    stream.close()
