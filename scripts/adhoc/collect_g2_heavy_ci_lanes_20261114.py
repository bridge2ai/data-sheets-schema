"""Verify real G2 lane collections for the Claude lead, 2026-11-14.

Input: scratch lane-map.json and repository tests. Output: per-lane logs and
JSON evidence in assignment scratch. Run --canary, inspect, then --remaining.
The local checkout lacks the FAIRSCAPE submodule; exclude only that directory.
Collection must fail the unchanged dedicated execution gate after selecting
exactly one expected node. No tests or providers execute.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-ci-lanes-g2-heavy-20261114'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--canary', action='store_true')
parser.add_argument('--remaining', action='store_true')
args = parser.parse_args()
assert args.canary != args.remaining
lanes = json.loads((SCRATCH / 'lane-map.json').read_text())
if args.remaining:
    previous = json.loads((SCRATCH / 'collection-native-capacity-34.json').read_text())
    assert previous['verified'] is True
for lane, node in list(lanes.items())[:1] if args.canary else list(lanes.items())[1:]:
    command = [str(PYTHON), '-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider',
               '-p', 'utils.pytest_shard', '--ci-lane=' + lane, '--collect-only',
               '--ignore=tests/test_fairscape_integration',
               '--basetemp=' + str(SCRATCH / ('collect-' + lane))]
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    output = result.stdout + result.stderr
    log = SCRATCH / ('collection-' + lane + '.log')
    log.write_text(output)
    selected = [line.strip() for line in output.splitlines() if line.startswith('tests/') and '::' in line]
    verified = (result.returncode == 1 and selected == [node]
                and 'dedicated CI case did not pass setup, call and teardown' in output
                and 'ERROR collecting' not in output)
    record = dict(command=command, exit_code=result.returncode, selected=selected,
                  verified=verified, log=str(log))
    (SCRATCH / ('collection-' + lane + '.json')).write_text(json.dumps(record, indent=2) + '\n')
    print(lane, 'verified' if verified else 'FAILED', flush=True)
    assert verified, output[-4000:]
