#!/usr/bin/env python3
"""Run bounded offline G2 checks with saved provenance, 2026-11-14.
Inputs: explicit pytest nodes and assigned source checkout. Outputs: command,
log, JUnit and outcome under sibling scratch-g2-20261114. Issues 6207-6225.
No project provider/native call. A one-case canary precedes parallel batches.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'


def cases(path):
    nodes = list(ET.parse(path).iter('testcase'))
    return {'total': len(nodes), 'failed': sum(n.find('failure') is not None for n in nodes),
            'error': sum(n.find('error') is not None for n in nodes),
            'skipped': sum(n.find('skipped') is not None for n in nodes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cohort')
    parser.add_argument('nodes', nargs='+')
    parser.add_argument('--workers', type=int, choices=(0, 4), default=4)
    parser.add_argument('--canary', action='store_true')
    args = parser.parse_intermixed_args()
    if args.canary:
        assert args.cohort == 'canary' and len(args.nodes) == 1 and args.workers == 4
    elif args.workers:
        canary = json.loads((OUT / 'canary/outcome.json').read_bytes())
        assert canary['returncode'] == 0 and canary['counts'] == {
            'total': 1, 'failed': 0, 'error': 0, 'skipped': 0}
        assert cases(OUT / 'canary/pytest.xml') == canary['counts']
        assert any(path.is_file() and path.stat().st_size for path in (OUT / 'canary/cases').rglob('*'))
    # Synthetic authority must see committed implementation and tests.
    subprocess.check_call(['git', 'diff', '--exit-code', 'HEAD', '--', 'src', 'tests'], cwd=ROOT)
    directory = OUT / args.cohort
    directory.mkdir(exist_ok=False)
    env = {k: v for k, v in os.environ.items() if not (k.endswith('_API_KEY') or k in (
        'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL'))}
    env.update(PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1',
               PYTHONPYCACHEPREFIX=str(directory / 'pycache'), TMPDIR=str(directory))
    command = [str(PYTHON), '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *args.nodes]
    if args.workers:
        command += ['-n', str(args.workers)]
    command += ['--basetemp=' + str(directory / 'cases'), '--junitxml=' + str(directory / 'pytest.xml')]
    record = {'command': command, 'cwd': str(ROOT), 'environment': {key: env[key] for key in (
        'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PYTHONPYCACHEPREFIX', 'TMPDIR')},
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'status_before': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True)}
    (directory / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
    start = time.monotonic()
    with (directory / 'pytest.log').open('xb') as log:
        code = subprocess.call(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    outcome = {'returncode': code, 'seconds': time.monotonic() - start,
               'counts': cases(directory / 'pytest.xml') if (directory / 'pytest.xml').is_file() else None}
    (directory / 'outcome.json').write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps(outcome))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
