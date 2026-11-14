#!/usr/bin/env python3
"""Collect exact G2 legacy test identities after the serial run, 2026-11-14.

Inputs: two committed legacy test files, assigned checkout and primary venv.
Outputs: exclusive scratch-g2-20261114/legacy-collection-census command, log,
normalized node identities, source pins and result. Serves LEGACY-F1/F2 only.
This invokes pytest collection, never test execution; the serial run must have
a saved outcome first. No native/provider/probe call or source edit is requested.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from run_g2_checks_20261114 import python_inventory

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUT = SCRATCH / 'legacy-collection-census'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'
FILES = ('tests/test_native_execution.py', 'tests/test_native_receipt_origin_reporting.py')
SOURCE_SCOPE = ('src', 'tests', 'notes/matched_cborg_2026-09-13', 'pyproject.toml',
                'poetry.lock', 'conftest.py', '.github/workflows/main.yaml')


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write_json(name, value):
    path = OUT / name
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw
    return pin(path)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def normalize(nodeid):
    file, separator, item = nodeid.partition('::')
    if not separator or file not in FILES:
        raise ValueError('unexpected collection node identity')
    # Parameter IDs may themselves contain ::; split class/function components
    # only before the parameter suffix, matching pytest's JUnit identity shape.
    prefix, bracket, parameters = item.partition('[')
    components = prefix.split('::')
    if not all(components) or not components[-1].startswith('test_'):
        raise ValueError('collection node lacks a test function')
    return {'nodeid': nodeid, 'file': file,
            'classname': '.'.join([file[:-3].replace('/', '.'), *components[:-1]]),
            'name': components[-1] + (bracket + parameters if bracket else '')}


def main():
    assert Path(sys.executable).resolve() == PYTHON.resolve(), 'use the primary assigned venv'
    assert not os.environ.get('PYTEST_ADDOPTS'), 'ambient pytest options could filter collection'
    prerequisite = SCRATCH / 'legacy-full-serial/outcome.json'
    prior = json.loads(prerequisite.read_bytes())
    assert type(prior.get('returncode')) is int, 'wait for the serial cohort outcome before collection'
    inventory = python_inventory(ROOT, list(FILES))
    subprocess.check_call(['git', 'diff', '--exit-code', 'HEAD', '--', *SOURCE_SCOPE], cwd=ROOT)
    head = git('rev-parse', 'HEAD')
    source_pins = {name: pin(ROOT / name) for name in (*FILES, 'conftest.py', 'pyproject.toml')}
    command = [str(PYTHON), '-m', 'pytest', '--collect-only', '-q', '-p', 'no:cacheprovider',
               *FILES, '--basetemp=' + str(OUT / 'cases')]
    env = {key: value for key, value in os.environ.items()
           if not (key.endswith('_API_KEY') or key in (
               'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL'))}
    env.update(PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1',
               PYTHONPYCACHEPREFIX=str(OUT / 'pycache'), TMPDIR=str(OUT))
    OUT.mkdir(exist_ok=False)
    # Distinct names keep a collection census from being mistaken for an
    # executed test cohort by the handoff's direct-cohort inventory.
    command_pin = write_json('collection-command.json', {'kind': 'pytest_collection_only',
        'command': command, 'cwd': str(ROOT), 'head': head, 'files': list(FILES),
        'environment': {key: env[key] for key in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE',
                                                'PYTHONPYCACHEPREFIX', 'TMPDIR')},
        'source_inventory': inventory, 'source_pins': source_pins,
        'serial_run_finished': pin(prerequisite), 'recorded_at': datetime.now(timezone.utc).isoformat()})
    started = time.monotonic()
    with (OUT / 'collection.log').open('xb') as log:
        returncode = subprocess.call(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    problems, rows = [], []
    text = (OUT / 'collection.log').read_text(errors='strict')
    if returncode != 0:
        problems.append('pytest collection returned nonzero')
    try:
        for line in text.splitlines():
            value = line.strip()
            if value.startswith('tests/') and '::' in value:
                rows.append(normalize(value))
        identities = {(row['classname'], row['name']) for row in rows}
        if len(identities) != len(rows) or not rows:
            problems.append('empty or duplicate normalized collection identities')
        totals = [int(match.group(1)) for match in re.finditer(r'(?m)^(\d+) tests? collected(?:,| in|$)', text)]
        if not totals or totals[-1] != len(rows):
            problems.append('collection summary does not equal the captured node census')
        if {row['file'] for row in rows} != set(FILES):
            problems.append('collection lacks one of the two complete files')
    except ValueError as error:
        problems.append(str(error))
    if git('rev-parse', 'HEAD') != head:
        problems.append('source HEAD changed during collection')
    if subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', *SOURCE_SCOPE],
                      cwd=ROOT, capture_output=True, check=False).returncode != 0:
        problems.append('tracked source changed during collection')
    after = {name: pin(ROOT / name) for name in source_pins}
    if after != source_pins:
        problems.append('pinned collection source changed')
    nodes_pin = write_json('nodes.json', rows)
    result = {'kind': 'pytest_collection_census', 'status': 'verified' if not problems else 'not_verified',
        'returncode': returncode, 'seconds': time.monotonic() - started, 'head': head,
        'cwd': str(ROOT), 'files': list(FILES), 'source_pins': source_pins,
        'command': command_pin, 'log': pin(OUT / 'collection.log'), 'nodes': nodes_pin,
        'node_count': len(rows), 'nodes_by_file': dict(Counter(row['file'] for row in rows)),
        'problems': problems, 'tests_executed': False,
        'producer': pin(Path(__file__).resolve()),
        'inventory_helper': pin(ROOT / 'scripts/adhoc/run_g2_checks_20261114.py'),
        'scope': 'Actual pytest collection includes fixture parametrization. It supplies identities, never passing-test proof.'}
    result_pin = write_json('census.json', result)
    print(json.dumps({'result': result_pin, 'status': result['status'], 'node_count': len(rows)}))
    return 0 if not problems else 1


if __name__ == '__main__':
    raise SystemExit(main())
