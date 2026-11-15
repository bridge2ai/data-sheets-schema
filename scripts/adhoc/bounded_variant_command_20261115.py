"""Bound offline commands; inputs argv, output directory; writes logs and timing.

Variant advance assignment, 2026-11-15. Used here only for offline Python commands.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
limit = int(sys.argv[2])
command = sys.argv[3:]
(out / 'command.json').write_text(json.dumps(command, indent=2))
start = time.monotonic()
with (out / 'output.log').open('w') as stream:
    environment = dict(os.environ, PYTHONPYCACHEPREFIX=str(out / 'pycache'))
    proc = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True,
                            env=environment)
    (out / 'process.json').write_text(json.dumps({'pid': proc.pid}))
    try:
        code = proc.wait(timeout=limit)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        code = 124
result = {'exit_code': code, 'wall_seconds': time.monotonic() - start, 'bound_seconds': limit}
(out / 'result.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
sys.exit(code)
