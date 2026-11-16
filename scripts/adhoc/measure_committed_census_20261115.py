"""Observe the committed census public canary for the lead, 2026-11-15.

Inputs: fresh JSONL output and pytest arguments. Outputs: call durations,
host load and ordinary pytest artifacts. No source or gate replacement.
"""
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[0] = str(ROOT)
import pytest

stream = Path(sys.argv[1]).open('x', buffering=1)
monitor = sys.monitoring
tool = 4
monitor.use_tool_id(tool, 'committed-census-measurement')
selected = {
    'test_native_shared_execution.py': {'make_case', 'launch_case'},
    'native_control.py': {'_observe_event', '_classify_frame'},
    'native_execution_orchestration.py': {'_admit_subscription_guard'},
    'native_shared_capture.py': {'at_callback'},
    'native_shared_registration_orchestration.py': {'verified'},
    'native_subscription_capture.py': {'_current_authority'},
    'native_environment_manifest.py': {'_light_live'},
}
active = {}


def emit(row):
    stream.write(json.dumps(dict(wall_ns=time.time_ns(), load=os.getloadavg(), **row)) + '\n')


def start(code, offset):
    name = Path(code.co_filename).name
    if code.co_name not in selected.get(name, ()):
        return monitor.DISABLE
    frame = sys._getframe(1)
    if frame.f_code is not code:
        raise RuntimeError('measurement frame identity mismatch')
    key = (threading.get_ident(), code)
    row = {'file': name, 'function': code.co_name, 'thread': key[0]}
    if name == 'test_native_shared_execution.py' and code.co_name == 'launch_case':
        case = frame.f_locals['case']
        row['guard'] = json.loads(case['kwargs']['subscription_guard_path'].read_bytes())
    event = frame.f_locals.get('event', frame.f_locals.get('frame'))
    if isinstance(event, dict):
        row['event'] = event
    active.setdefault(key, []).append((time.monotonic(), row))
    emit(dict(row, boundary='start'))
    monitor.set_local_events(tool, code, monitor.events.PY_RETURN)


def finish(code, offset, value):
    stack = active.get((threading.get_ident(), code))
    if stack:
        began, row = stack.pop()
        emit(dict(row, boundary='end', seconds=time.monotonic() - began))


monitor.register_callback(tool, monitor.events.PY_START, start)
monitor.register_callback(tool, monitor.events.PY_RETURN, finish)
monitor.set_events(tool, monitor.events.PY_START)
emit({'boundary': 'measurement_start'})
try:
    result = pytest.main(sys.argv[2:])
    emit({'boundary': 'pytest_end', 'returncode': int(result)})
finally:
    monitor.set_events(tool, 0)
    for _, code in active:
        monitor.set_local_events(tool, code, 0)
    monitor.free_tool_id(tool)
    stream.close()
raise SystemExit(result)
