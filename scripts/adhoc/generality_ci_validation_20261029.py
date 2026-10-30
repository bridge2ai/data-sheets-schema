#!/usr/bin/env python3
# Purpose: serial, complete CI-layout validation for G1 N1/N9 acceptance.
# Inputs: current checkout, main.yaml, unit name and external evidence directory.
# Outputs: exact commands, logs, JUnit and exit statuses; 2026-10-29.
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('unit')
parser.add_argument('output', type=Path)
args = parser.parse_args()
assert Path.cwd() == ROOT
assert not args.output.resolve().is_relative_to(ROOT)
args.output.mkdir(parents=True, exist_ok=True)
workflow_path = ROOT / '.github/workflows/main.yaml'
workflow = yaml.safe_load(workflow_path.read_bytes())
units = {'collect-all': ['--collect-only', '-q'], 'collect-tests': ['tests', '--collect-only', '-q']}
extra_paths = {}
for shard in range(1, 7):
    units[f'shard-{shard}'] = ['tests', '-v', '-p', 'utils.pytest_shard',
        f'--ci-shard={shard}/6', '--ci-shard-timings=utils/ci_test_durations.json',
        '--ci-lane=ordinary', '--durations=25']
for lane in workflow['jobs']['api-completion']['strategy']['matrix']['case']:
    units[lane] = ['tests', '-v', '-p', 'utils.pytest_shard', f'--ci-lane={lane}', '--durations=25']
for job in ('offline-canary', 'offline-audit', 'offline-evaluation'):
    for step in workflow['jobs'][job]['steps']:
        run = step.get('run', '')
        if 'python -m pytest' not in run:
            continue
        tokens = shlex.split(run.replace('\\\n', ' '))
        start = tokens.index('pytest') + 1
        name = job + ('-native' if 'test_native_proxy.py' in run else '-budget' if 'test_budgeted_cborg.py' in run else '')
        units[name] = [arg for arg in tokens[start:] if not arg.startswith('--junitxml=')]
        extra_paths[name] = os.pathsep.join(str(ROOT / p) for p in
            step.get('env', {}).get('PYTHONPATH', '').split(':') if p and p != 'src')

selected = list(units) if args.unit in ('all', 'remaining') else [args.unit]
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
for name in selected:
    previous = args.output / (name + '.result.json')
    if args.unit == 'remaining' and previous.exists():
        saved = json.loads(previous.read_text())
        assert saved['head'] == head and saved['returncode'] in (0, 1), saved
        continue
    command = [sys.executable, '-S', '-B', str(ROOT / 'scripts/adhoc/generality_g1_offline_20261029.py'),
        'pytest', *units[name], '-p', 'no:cacheprovider',
        f'--basetemp=/private/tmp/g1-validation-{name}',
        f'--junitxml={args.output / (name + ".xml")}']
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1',
               G1_TEST_EXTRA_PATHS=extra_paths.get(name, ''),
               G1_TEST_FAILURES_PATH=str(args.output / (name + '.failures.jsonl')))
    for key in list(env):
        if key.endswith('_API_KEY'):
            env.pop(key)
    started = time.time()
    print('START', name, flush=True)
    with (args.output / (name + '.log')).open('w') as log:
        proc = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    result = {'unit': name, 'command': command, 'returncode': proc.returncode,
              'seconds': time.time() - started, 'python': sys.version,
              'head': head,
              'workflow_sha256': hashlib.sha256(workflow_path.read_bytes()).hexdigest()}
    (args.output / (name + '.result.json')).write_text(json.dumps(result, indent=2) + '\n')
    assert (args.output / (name + '.log')).stat().st_size
    assert (args.output / (name + '.xml')).stat().st_size
    print('END', json.dumps(result), flush=True)
    if name.startswith('collect-'):
        assert proc.returncode == 0, 'collection must be repaired before suite execution'
    else:
        assert proc.returncode in (0, 1), 'pytest did not complete the selected CI unit'
        assert ET.parse(args.output / (name + '.xml')).findall('.//testcase'), 'no cases recorded'
