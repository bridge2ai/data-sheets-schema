"""Run assigned offline suites for issues 6259/6258, 2026-11-15.

Inputs: workflow and checkout; outputs: logs/XML in assigned scratch.
Use an external process-group timeout, never an inherited admission alarm.
"""
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import yaml

root = Path(__file__).resolve().parents[2]
scratch = root.parent / 'scratch-codex-controller-6259-20261115'
workflow = yaml.safe_load((root / '.github/workflows/main.yaml').read_text())
suites = {}
for job in workflow['jobs'].values():
    for step in job.get('steps', []):
        command = step.get('run', '')
        if 'poetry run python -m pytest' not in command:
            continue
        if 'native_controls/test_native_proxy.py' in command:
            suites['native'] = shlex.split(command)[5:]
        elif 'pytest notes/matched_cborg_2026-09-13/audit_controls' in command:
            suites['audit'] = shlex.split(command)[5:]
suites['deadline'] = ['tests/test_native_attempt_deadline.py', '-q', '-p', 'no:cacheprovider']
suites['denials'] = ['tests/test_native_shared_denials.py', '-vv', '-p', 'no:cacheprovider']
name = sys.argv[1]
args = [arg for arg in suites[name] if not arg.startswith('--junitxml=')]
if len(sys.argv) > 2:
    workers = int(sys.argv[2])
    assert 1 <= workers <= 4
    args += ['-n', str(workers)]
    name += '-parallel'
args += [f'--basetemp={scratch / (name + "-temp")}', f'--junitxml={scratch / (name + ".xml")}']
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=':'.join(str(root / p) for p in
    ('src', 'notes/matched_cborg_2026-09-13', 'notes/matched_cborg_2026-09-13/native_controls')))
command = ['/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python', '-m', 'pytest', *args]
with (scratch / (name + '.log')).open('w') as stream:
    process = subprocess.Popen(command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    timed_out = False
    try:
        code = process.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            code = process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
result = dict(suite=name, command=command, returncode=code, timed_out=timed_out)
(scratch / (name + '-result.json')).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
