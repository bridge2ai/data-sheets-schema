"""Collect each new CI capacity lane against the real suite, 2026-11-14.

Inputs: full tests suite/current lane constants. Outputs: external logs and JSON
for the Claude lead CI assignment. Run --canary, verify, then --remaining.
Known uninitialized FAIRSCAPE errors are reported, never accepted as a pass.
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
from utils.pytest_shard import NATIVE_CAPACITY_CASE_LANES

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('scratch', type=Path)
parser.add_argument('--canary', action='store_true')
parser.add_argument('--remaining', action='store_true')
args = parser.parse_args()
assert args.canary != args.remaining
lanes = list(NATIVE_CAPACITY_CASE_LANES)
if args.remaining:
    assert json.loads((args.scratch / (lanes[0] + '.json')).read_text())['selection_verified']
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
    known = {
        'tests/test_fairscape_integration/test_canonical_routes.py',
        'tests/test_fairscape_integration/test_forward_typed_projections.py',
        'tests/test_fairscape_integration/test_nested_dataset_readback.py',
    }
    expected_errors = {line.split(' - ')[0].removeprefix('ERROR ') for line in errors}
    verified = nodes == [NATIVE_CAPACITY_CASE_LANES[lane]]
    value = dict(lane=lane, command=command, returncode=result.returncode,
        selected_nodes=nodes, selection_verified=verified, collection_errors=errors,
        execution_pass=False, log=str(log))
    (args.scratch / (lane + '.json')).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(value), flush=True)
    assert verified, log
    assert result.returncode == 1, (result.returncode, log)
    assert expected_errors == known and len(errors) == 3, errors


# Canary and remainder use the same launcher/environment/executor. Two
# collection processes leave room for the sharding tests' two nested workers.
with ThreadPoolExecutor(max_workers=2) as executor:
    list(executor.map(verify, lanes))
