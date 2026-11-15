"""Run bounded offline checks for issues 6255 and 6257, 2026-11-15.

Inputs: pytest arguments. Outputs: scratch log and exit status JSON.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-test-lanes-6255-20261115'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'


def main():
    label, seconds, *arguments = sys.argv[1:]
    SCRATCH.mkdir(exist_ok=True)
    command = [str(PYTHON), '-m', 'pytest', '-p', 'no:cacheprovider',
               '--basetemp=' + str(SCRATCH / (label + '-tmp')), *arguments]
    environment = dict(os.environ, PYTHONPATH=str(ROOT / 'src'),
                       PYTHONPYCACHEPREFIX=str(SCRATCH / 'pycache'))
    with (SCRATCH / (label + '.log')).open('w') as output:
        process = subprocess.Popen(command, cwd=ROOT, env=environment,
                                   stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            code = process.wait(timeout=int(seconds))
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code = 124
    result = dict(command=command, timeout_seconds=int(seconds), returncode=code)
    (SCRATCH / (label + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
