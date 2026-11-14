"""Verify real native lane selection without execution for PR 5968, 2026-11-13.

Inputs: actual tests suite and lane constants. Outputs: scratch logs and JSON.
Run --canary first, inspect its saved result, then run --remaining.
Known uninitialized FAIRSCAPE collection errors are recorded, never hidden.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utils.pytest_shard import NATIVE_CASE_LANES

parser = argparse.ArgumentParser()
parser.add_argument('scratch', type=Path)
parser.add_argument('--canary', action='store_true')
parser.add_argument('--remaining', action='store_true')
args = parser.parse_args()
assert args.canary != args.remaining
lanes = list(NATIVE_CASE_LANES)
if args.remaining:
    first = json.loads((args.scratch / (lanes[0] + '.json')).read_text())
    assert first['selection_verified']
    lanes = lanes[1:]
else:
    lanes = lanes[:1]
def verify(lane):
    command = [sys.executable, '-m', 'pytest', 'tests', '--collect-only', '-q',
               '-p', 'no:cacheprovider', '-p', 'utils.pytest_shard', '--ci-lane=' + lane,
               '--continue-on-collection-errors', '--basetemp=' + str(args.scratch / (lane + '-tmp'))]
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'),
               PYTHONPYCACHEPREFIX=str(args.scratch / 'collection-pycache'))
    env.pop('PYTHONDONTWRITEBYTECODE', None)
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    log = args.scratch / (lane + '.log')
    log.write_text(result.stdout + result.stderr)
    nodes = [line for line in result.stdout.splitlines() if line.startswith('tests/') and '::' in line]
    errors = [line for line in result.stdout.splitlines() if line.startswith('ERROR tests/')]
    verified = nodes == [NATIVE_CASE_LANES[lane]]
    value = dict(lane=lane, command=command, returncode=result.returncode,
                 selected_nodes=nodes, selection_verified=verified, collection_errors=errors,
                 execution_pass=False, log=str(log))
    (args.scratch / (lane + '.json')).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(value), flush=True)
    assert verified, log
    assert result.returncode == 1, (result.returncode, log)
    assert len(errors) == 3 and all(line.startswith('ERROR tests/test_fairscape_integration/') for line in errors), errors


# Same launcher, environment and executor for the one-lane canary and remainder.
# Two collection processes plus the acceptance tests' two nested xdist workers.
with ThreadPoolExecutor(max_workers=2) as executor:
    list(executor.map(verify, lanes))
