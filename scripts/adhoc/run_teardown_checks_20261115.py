"""Issue 6214, 2026-11-15: bounded offline pytest; output logs and run JSON."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

scratch = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-callback-teardown-20261115')
name, bound, *args = sys.argv[1:]
env = dict(os.environ, PYTHONPATH=str(Path.cwd() / 'src'), PYTHONDONTWRITEBYTECODE='1',
           TEARDOWN_REPORT_PATH=str(scratch / (name + '.reports.jsonl')))
command = ['/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python', '-m', 'pytest', '-p', 'no:cacheprovider', '-p', 'scripts.adhoc.teardown_report_20261115', '--basetemp=' + str(scratch / (name + '-temp')), *args]
start = time.monotonic()
with (scratch / (name + '.log')).open('w') as log:
    process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    timed_out = False
    try:
        code = process.wait(timeout=float(bound))
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait(timeout=5)
result = dict(command=command, code=code, timed_out=timed_out, seconds=time.monotonic()-start)
(scratch / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
print((scratch / (name + '.log')).read_text()[-5000:])
