#!/usr/bin/env python3
# Purpose: offline validation/report evidence for issue #5483 J-a, 2026-11-05.
# Inputs: assigned checkout and local dependencies; outputs: external logs and JSON.
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path('/private/tmp/issue-j-a-20261105')
PYTHON = '/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python'

def run(name, command):
    env = {k: v for k, v in os.environ.items() if not (k.startswith(('ANTHROPIC_', 'OPENAI_', 'CBORG_')) or k.endswith(('_API_KEY', '_AUTH_TOKEN', '_ACCESS_TOKEN')))}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               PYTEST_ADDOPTS='', UV_OFFLINE='1', PIP_NO_INDEX='1', GIT_NO_LAZY_FETCH='1',
               PYTHONPATH=str(ROOT / 'src') + os.pathsep + str(ROOT) + os.pathsep + '/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/fairscape_models')
    start = time.monotonic()
    with (OUT / (name + '.log')).open('w') as stream:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = child.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
            code = 124
    result = dict(command=command, exit_code=code, seconds=time.monotonic()-start, deadline=3600)
    (OUT / (name + '.execution.json')).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return code

if __name__ == '__main__':
    name = sys.argv[1]
    if name == 'tests':
        command = [PYTHON, '-B', '-m', 'pytest', '-o', 'addopts=', '-q', '-p', 'no:cacheprovider',
                   'tests/test_d41_request_parity.py', 'tests/test_generation_specificity_skill.py',
                   'tests/test_neutral_generation_schema.py', 'tests/test_profiles.py',
                   'tests/test_external_dataset_onboarding.py', '--junitxml='+str(OUT/'tests.xml')]
    elif name == 'collect':
        command = [PYTHON, '-B', '-m', 'pytest', '-o', 'addopts=', 'tests', '--collect-only', '-q', '-p', 'no:cacheprovider']
    else:
        command = [PYTHON, '-B', '.claude/skills/d4d-generation-specificity-audit/scan.py', '--root', str(ROOT), '--report', str(OUT/'after.md'), '--json', str(OUT/'after.json')]
    sys.exit(run(name, command))
