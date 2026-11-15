"""External watchdog for offline issue 6246 checks, 2026-11-15.
Inputs: label, seconds, command. Outputs: scratch log and outcome JSON.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

scratch = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-scanner-v3-template-20261115')
scratch.mkdir(exist_ok=True)
label, seconds, *command = sys.argv[1:]
env = dict(os.environ, PYTHONPATH=str(Path.cwd() / 'src'), PYTHONDONTWRITEBYTECODE='1')
with (scratch / (label + '.log')).open('x') as log:
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    timed_out = False
    try:
        code = process.wait(timeout=int(seconds))
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            code = process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
result = dict(command=command, exit=code, timed_out=timed_out)
(scratch / (label + '.json')).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
raise SystemExit(code)
