#!/usr/bin/env python3
"""Summarize retained U4 offline validation evidence, 2026-11-08 (#4354).

Inputs: named run directories under assigned scratch and this checkout's Git
identity. Output: one new JSON manifest with exact hashes and JUnit counts.
Reads existing artifacts only; never executes tests or updates prior evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u4-prep'
BASE = '59d2982cfa3f0e88acc66047d2d9428c61eed74b'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_OPTIONAL_LOCKS': '0',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', *args],
                                   cwd=ROOT, env=ENV, timeout=30, text=True).strip()


def summarize(name):
    if not name or Path(name).name != name or name in ('.', '..'):
        raise ValueError('run must be a single explicit directory component')
    run = SCRATCH / name
    if run.resolve(strict=True) != run or not run.is_dir():
        raise ValueError('run must be an existing literal directory in assigned scratch')
    outcome = json.loads((run / 'outcome.json').read_bytes())
    stability = json.loads((run / 'source-stability.json').read_bytes())
    artifacts = {}
    for filename in ('outcome.json', 'source-stability.json', 'plan.json',
                     'worker-outcome.json', 'pytest.xml', 'pytest.log',
                     'bootstrap.json', 'network.json', 'origins-before.json',
                     'origins-after.json', 'subprocess-origins.json', 'pytest-command.json'):
        path = run / filename
        if path.is_file():
            artifacts[filename] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    counts = {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
    nodes = []
    junit = run / 'pytest.xml'
    if junit.is_file():
        for case in ET.parse(junit).getroot().iter('testcase'):
            state = ('failed' if case.find('failure') is not None else
                     'errors' if case.find('error') is not None else
                     'skipped' if case.find('skipped') is not None else 'passed')
            counts[state] += 1
            detail = case.find({'failed': 'failure', 'errors': 'error', 'skipped': 'skipped'}.get(state, '_none'))
            nodes.append({'classname': case.get('classname'), 'name': case.get('name'),
                          'state': state, 'message': None if detail is None else detail.get('message')})
    return {'name': name, 'path': str(run), 'outcome': outcome,
            'source_stability': stability, 'counts': counts, 'nodes': nodes,
            'artifacts': artifacts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('runs', nargs='+')
    args = parser.parse_args()
    if len(set(args.runs)) != len(args.runs):
        raise ValueError('duplicate run names')
    output = args.output.absolute()
    if (output.parent != SCRATCH or output.resolve() != output
            or os.path.lexists(output)):
        raise ValueError('output must be a new literal file directly in assigned scratch')
    result = {'kind': 'native_u4_preparation_validation', 'version': 1,
              'base': BASE, 'head': git('rev-parse', 'HEAD'),
              'status': git('status', '--porcelain', '--untracked-files=all'),
              'changed_paths': git('diff', '--name-only', BASE, 'HEAD').splitlines(),
              'generator_sha256': sha(Path(__file__)),
              'runs': [summarize(name) for name in args.runs],
              'scope': 'offline preparation; counts overlap; no native acceptance or timing claim'}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'path': str(output), 'sha256': sha(output),
                      'runs': [{'name': run['name'], 'counts': run['counts'],
                                'returncode': run['outcome']['returncode']}
                               for run in result['runs']]}, sort_keys=True))


if __name__ == '__main__':
    main()
