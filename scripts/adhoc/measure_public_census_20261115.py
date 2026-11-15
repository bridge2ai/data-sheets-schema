"""Measure one unchanged public correction test, 2026-11-15 census ruling.

Inputs: timing JSONL path and pytest arguments. Outputs: boundary timestamps and
ordinary pytest artifacts. Wrappers only observe calls; no gate is replaced.
"""
from datetime import datetime
import json
from pathlib import Path
import sys
import time

root = Path(__file__).resolve().parents[2]
sys.path[0] = str(root)
from tests import test_native_shared_execution as public
import pytest

output = Path(sys.argv[1]).open('x', buffering=1)
make_case, launch_case = public.make_case, public.launch_case


def measured_make(*args, **kwargs):
    start = time.monotonic()
    try:
        return make_case(*args, **kwargs)
    finally:
        output.write(json.dumps({'phase': 'make_case', 'seconds': time.monotonic() - start}) + '\n')


def measured_launch(case, *args, **kwargs):
    guard = json.loads(case['kwargs']['subscription_guard_path'].read_bytes())
    start = time.monotonic()
    interval = time.time() - datetime.fromisoformat(guard['captured_at'].replace('Z', '+00:00')).timestamp()
    output.write(json.dumps({'phase': 'launch_entry', 'capture_to_launch_seconds': interval,
        'freshness_margin_seconds': guard['max_age_seconds'] - interval,
        'max_age_seconds': guard['max_age_seconds']}) + '\n')
    try:
        return launch_case(case, *args, **kwargs)
    finally:
        output.write(json.dumps({'phase': 'launch_return', 'seconds': time.monotonic() - start}) + '\n')


public.make_case, public.launch_case = measured_make, measured_launch
raise SystemExit(pytest.main(sys.argv[2:]))
