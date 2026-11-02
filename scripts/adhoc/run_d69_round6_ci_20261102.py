#!/usr/bin/env python3
"""#5212 round 6, 2026-11-02: run one exact workflow test lane offline.

Inputs: pinned archive, scratch evidence prefix, workflow lane (or plan).
Outputs: resolved command/environment ledger, pytest log/JSON/XML and wall time.
Uses workflow commands, with four explicit PR workers and external XML/temp
paths. The caller runs lanes serially; this launcher never fans out jobs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('--tree', type=Path, required=True)
p.add_argument('--basetemp', type=Path, required=True)
p.add_argument('--lane', required=True)
p.add_argument('--plan', action='store_true')
a = p.parse_args()
assert 'scratch-5212fix' in a.basetemp.parts
site = Path(sys.executable).parent.parent / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
sys.path.append(str(site))
import yaml

workflow = a.tree / '.github/workflows/main.yaml'
raw = workflow.read_bytes()
jobs = yaml.safe_load(raw)['jobs']
lanes = {}
for number in range(1, 7):
    step = next(step for step in jobs['python-tests']['steps'] if step.get('name') == 'Run the suite shard including corpus checks')
    command = step['run']
    command = command.replace("${{ matrix.shard }}/${{ github.event_name == 'pull_request' && 6 || 4 }}", f'{number}/6')
    command = command.replace('-n logical --maxprocesses=4', '-n 4')
    lanes[f'shard-{number}'] = (command, False)
for lane in ('routing-dispatch', 'routing-portable', 'routing-regate', 'routing-default-layout'):
    step = next(step for step in jobs['api-completion']['steps'] if step.get('name') == 'Run the required offline API case')
    command = re.search(r'poetry run python -m pytest\s+(.*?)2>&1', step['run'].replace('\\\n', ' '), re.S).group(1)
    lanes[lane] = ('poetry run python -m pytest ' + command.replace('${{ matrix.case }}', lane), False)
for job, names in (
    ('offline-canary', ('budget', 'native')),
    ('offline-audit', ('audit',)),
    ('offline-evaluation', ('evaluation',)),
):
    steps = [step for step in jobs[job]['steps'] if 'poetry run python -m pytest' in step.get('run', '')]
    assert len(steps) == len(names)
    for name, step in zip(names, steps):
        lanes[name] = (step['run'], True)
assert a.lane in lanes, sorted(lanes)
command, notes = lanes[a.lane]
tokens = shlex.split(command)
assert tokens[:5] == ['poetry', 'run', 'python', '-m', 'pytest']
args = [token for token in tokens[5:] if not token.startswith('--junitxml=')]
assert '${{' not in ' '.join(args)
args.append('--junitxml=' + str(a.basetemp.with_suffix('.xml')))
runner = Path(__file__).with_name('run_d68_round4_20261101.py')
argv = [sys.executable, '-S', '-P', '-B', str(runner), '--tree', str(a.tree),
        '--basetemp', str(a.basetemp), *(['--notes'] if notes else []), *args]
record = {'lane': a.lane, 'workflow_sha256': hashlib.sha256(raw).hexdigest(),
          'workflow_command': command, 'pytest_args': args, 'launcher': argv,
          'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=a.tree, text=True).strip(),
          'notes_lane': notes, 'max_workers': 4 if a.lane.startswith('shard-') else 1}
scope = ['notes/'] if notes else ['notes/', 'tests/', 'utils/']
status_command = ['git', 'status', '--ignored', '--porcelain', '--', *scope]
record['hygiene_before'] = subprocess.check_output(status_command, cwd=a.tree, text=True).splitlines()
target = a.basetemp.with_suffix('.command.json')
target.write_text(json.dumps(record, indent=2))
if a.plan:
    print(json.dumps(record, indent=2))
    raise SystemExit(0)
started = time.monotonic()
with a.basetemp.with_suffix('.log').open('w') as stream:
    result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
record.update(exit_code=result.returncode, wall_seconds=time.monotonic() - started)
record['hygiene_after'] = subprocess.check_output(status_command, cwd=a.tree, text=True).splitlines()
allowed_bytecode = a.lane in ('budget', 'native', 'audit')
record['bytecode_warnings'] = [line for line in record['hygiene_after']
                             if allowed_bytecode and re.fullmatch(r'!! .*/__pycache__/', line)]
record['hygiene_errors'] = [line for line in record['hygiene_after']
                          if line not in record['bytecode_warnings']]
record['tracked_changes'] = subprocess.check_output(
    ['git', 'status', '--porcelain', '--untracked-files=no'], cwd=a.tree, text=True).splitlines()
record['hygiene_passed'] = not record['hygiene_errors'] and not record['tracked_changes']
target.write_text(json.dumps(record, indent=2))
print(json.dumps({key: record[key] for key in ('lane', 'head', 'exit_code', 'wall_seconds')}))
raise SystemExit(result.returncode or (0 if record['hygiene_passed'] else 1))
