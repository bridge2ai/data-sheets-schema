#!/usr/bin/env python3
"""Run remaining G2 parallel checks with the existing CI scheduling, 2026-11-14.

Inputs: explicit pytest selectors, --canary for one node in scheduled-canary.
Outputs: exclusive command/log/JUnit/outcome under scratch-g2-20261114. Reuses
the reviewed runner inventory/case helpers; preserves that runner and its proof.
Adds --dist load --maxschedchunk=1 at four workers, as in main.yaml:62.
No project/provider/native call is added. Run only after the current cohort ends.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

sys.dont_write_bytecode = True  # Keep the imported helper's bytecode out of W.
from run_g2_checks_20261114 import ROOT, OUT, PYTHON, cases, python_inventory

BASE = Path(__file__).with_name('run_g2_checks_20261114.py').resolve()
PRODUCER = Path(__file__).resolve()
SCHEDULE = ['-n', '4', '--dist', 'load', '--maxschedchunk=1']
PREFIX = [str(PYTHON), '-m', 'pytest', '-q', '-p', 'no:cacheprovider']
SOURCE_SCOPE = ('src', 'tests', 'notes/matched_cborg_2026-09-13', 'pyproject.toml',
                'poetry.lock', 'conftest.py', '.github/workflows/main.yaml')


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def canary_proof():
    directory = OUT / 'scheduled-canary'
    command = json.loads((directory / 'command.json').read_bytes())
    outcome = json.loads((directory / 'outcome.json').read_bytes())
    assert command['producer'] == pin(PRODUCER) and command['base_runner'] == pin(BASE), 'driver changed; preserve prior canary and review a new canary plan'
    assert command['cwd'] == str(ROOT) and command['canary'] is True
    assert command['command'][:6] == PREFIX and command['command'][-7:-2] == SCHEDULE
    assert len(command['command'][6:-7]) == 1 and '::' in command['command'][6]
    assert command['command'][-2:] == ['--basetemp=' + str(directory / 'cases'), '--junitxml=' + str(directory / 'pytest.xml')]
    assert command['environment'] == {'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONPYCACHEPREFIX': str(directory / 'pycache'), 'TMPDIR': str(directory)}
    assert outcome['returncode'] == 0 and outcome['counts'] == {'total': 1, 'failed': 0, 'error': 0, 'skipped': 0}
    assert cases(directory / 'pytest.xml') == outcome['counts']
    assert any(path.is_file() and path.stat().st_size for path in (directory / 'cases').rglob('*')), 'canary persisted no nonempty case artifact'
    subprocess.check_call(['git', 'diff', '--exit-code', command['head'], 'HEAD', '--', *SOURCE_SCOPE], cwd=ROOT)
    return [pin(directory / name) for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cohort')
    parser.add_argument('nodes', nargs='+')
    parser.add_argument('--workers', type=int, choices=(4,), default=4)
    parser.add_argument('--canary', action='store_true')
    args = parser.parse_intermixed_args()
    assert re.fullmatch(r'[a-z0-9][a-z0-9-]*', args.cohort), 'cohort must be one direct scratch directory name'
    if args.canary:
        assert args.cohort == 'scheduled-canary' and len(args.nodes) == 1 and '::' in args.nodes[0]
        previous = None
    else:
        assert args.cohort != 'scheduled-canary', 'scheduled-canary requires --canary'
        previous = canary_proof()
    inventory = python_inventory(ROOT, args.nodes)
    subprocess.check_call(['git', 'diff', '--exit-code', 'HEAD', '--', *SOURCE_SCOPE, *inventory['selected_paths']], cwd=ROOT)
    directory = OUT / args.cohort
    directory.mkdir(exist_ok=False)
    env = {key: value for key, value in os.environ.items() if not (key.endswith('_API_KEY') or key in (
        'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL'))}
    env.update(PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1',
               PYTHONPYCACHEPREFIX=str(directory / 'pycache'), TMPDIR=str(directory))
    command = [*PREFIX, *args.nodes, *SCHEDULE,
               '--basetemp=' + str(directory / 'cases'), '--junitxml=' + str(directory / 'pytest.xml')]
    record = {'command': command, 'cwd': str(ROOT), 'environment': {key: env[key] for key in (
        'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PYTHONPYCACHEPREFIX', 'TMPDIR')},
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'status_before': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
        'source_inventory': inventory, 'producer': pin(PRODUCER), 'base_runner': pin(BASE),
        'scheduling': SCHEDULE, 'canary': args.canary, 'canary_evidence': previous}
    with (directory / 'command.json').open('x') as stream:
        stream.write(json.dumps(record, indent=2) + '\n')
    started = time.monotonic()
    with (directory / 'pytest.log').open('xb') as log:
        code = subprocess.call(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    outcome = {'returncode': code, 'seconds': time.monotonic() - started,
               'counts': cases(directory / 'pytest.xml') if (directory / 'pytest.xml').is_file() else None}
    with (directory / 'outcome.json').open('x') as stream:
        stream.write(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps(outcome))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
