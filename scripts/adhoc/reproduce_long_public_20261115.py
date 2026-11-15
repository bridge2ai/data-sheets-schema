"""Run one offline correction case for run 43664211357 diagnosis, 2026-11-15.

Input: assigned checkout. Output: assigned scratch logs and retained pytest files.
The outer bound does not change any runtime deadline or acceptance rule.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[2]
out = root.parent / 'scratch-long-public-20261115' / 'local-correction'
out.mkdir()
command = [sys.executable, '-m', 'pytest',
    'tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion',
    '--basetemp=' + str(out / 'cases'), '-p', 'no:cacheprovider',
    '--junitxml=' + str(out / 'pytest.xml'), '-v']
env = dict(os.environ, PYTHONPATH=str(root / 'src'), PYTHONDONTWRITEBYTECODE='1')
(out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
start = time.time()
with (out / 'pytest.log').open('w') as log:
    try:
        status = subprocess.run(command, cwd=root, env=env, stdout=log,
                                stderr=subprocess.STDOUT, timeout=9000).returncode
    except subprocess.TimeoutExpired:
        status = 124
(out / 'result.json').write_text(json.dumps({
    'exit_code': status, 'elapsed_seconds': time.time() - start,
    'outer_timeout_seconds': 9000}, indent=2) + '\n')
raise SystemExit(status)
