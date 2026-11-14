#!/usr/bin/env python3
"""Audit helper-2 Part C sources, test evidence and identity impact, 2026-11-12.
Inputs: assigned branch, local Git objects, saved isolated-runner cohorts.
Outputs: sibling scratch JSON/search files; no source, pin or external writes.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-h2-launch-sequence-20261112'
OUT = SCRATCH / 'review-bundle-v3'
BASE = 'e936cbb83d091cfab5c2e8b85bdd4c08a1b6b1e0'
CANDIDATE = '5d63d0a77dc43c064cfc2b376355f98009dd5b6e'
MAIN = '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1'
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
def git(*args): return subprocess.check_output(['git', '--no-replace-objects', '-C', str(ROOT), *args])
def save(path, data): path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')

OUT.mkdir(exist_ok=True)
protected = []
for name in PROTECTED:
    raw = (ROOT / name).read_bytes()
    assert raw == git('show', CANDIDATE + ':' + name) == git('show', MAIN + ':' + name)
    protected.append({'path': name, 'sha256': sha(raw)})
fixed_history = ('tests/utils/native_u4b_fixtures.py', 'tests/test_native_launch_review.py',
                 'tests/test_native_subscription_guard_v2.py', 'tests/fixtures/native_u4b_real_events.json')
for name in fixed_history:
    assert (ROOT / name).read_bytes() == git('show', BASE + ':' + name)
changed = git('diff', '--name-only', BASE, '--', 'src/data_sheets_schema').decode().splitlines()
pins = []
for name in changed:
    before, after = git('show', BASE + ':' + name), (ROOT / name).read_bytes()
    pins.append({'path': name, 'before_sha256': sha(before), 'after_sha256': sha(after),
                 'before_bytes': len(before), 'after_bytes': len(after)})
current = {str(path.relative_to(ROOT)): sha(path.read_bytes())
           for path in sorted((ROOT / 'src/data_sheets_schema').rglob('*'))
           if path.is_file() and path.suffix in ('.py', '.yaml', '.json')}
previous = {**current, **{row['path']: row['before_sha256'] for row in pins}}
sequence = 'src/data_sheets_schema/native_launch_sequence.py'
assert (ROOT / sequence).read_bytes() == git('show', BASE + ':' + sequence)
searches = []
for label, patterns, literal in (
    ('current-and-history-consumers', ['validate_bundle\\(|validate_terms\\(|_authorizations\\('], False),
    ('prior-source-pin-references', [row['before_sha256'] for row in pins], True),
    ('sequence-pin-references', [current[sequence]], True)):
    argv = ['rg', '--hidden', '--no-ignore', '-n', '-g', '!.git']
    if literal: argv.append('-F')
    for pattern in patterns: argv.extend(('-e', pattern))
    argv.append('.')
    result = subprocess.run(argv, cwd=ROOT, capture_output=True)
    assert result.returncode in (0, 1), result.stderr
    path = OUT / (label + '.txt')
    path.write_bytes(result.stdout)
    searches.append({'command': argv, 'returncode': result.returncode, 'path': str(path),
                     'bytes': len(result.stdout), 'sha256': sha(result.stdout)})
cohorts = []
for directory in sorted((SCRATCH / 'tests').glob('v3-*')):
    if not (directory / 'outcome.json').is_file():
        raise RuntimeError('cohort still running: ' + directory.name)
    outcome = json.loads((directory / 'outcome.json').read_bytes())
    assert outcome['cleanup_verified'] is True
    files = ('pytest.log', 'pytest.xml', 'pytest-command.json', 'network.json',
             'origins-before.json', 'origins-after.json', 'subprocess-origins.json', 'outcome.json')
    if not (directory / 'pytest.xml').is_file():
        files = tuple(name for name in ('scanner.md', 'scanner.json', 'scanner-command.json',
            'pytest.log', 'network.json', 'origins-before.json', 'origins-after.json',
            'subprocess-origins.json', 'outcome.json') if (directory / name).is_file())
        cohorts.append({'name': directory.name, 'outcome': outcome,
                        'files': {name: sha((directory / name).read_bytes()) for name in files}})
        continue
    counts, failures = Counter(), []
    root = ET.fromstring((directory / 'pytest.xml').read_bytes())
    for case in root.iter('testcase'):
        kind = next((key for key in ('failure', 'error', 'skipped') if case.find(key) is not None), 'passed')
        counts[kind] += 1
        if kind in ('failure', 'error'):
            failures.append({'node': case.attrib['classname'] + '::' + case.attrib['name'],
                             'message': case.find(kind).attrib.get('message'),
                             'trace': case.find(kind).text})
    cohorts.append({'name': directory.name, 'counts': dict(counts), 'failures': failures, 'outcome': outcome,
                    'files': {name: sha((directory / name).read_bytes()) for name in files}})
data = {'base': BASE, 'head': git('rev-parse', 'HEAD').decode().strip(),
        'branch': git('branch', '--show-current').decode().strip(),
        'status': git('status', '--short').decode(), 'diff_check': git('diff', '--check', BASE).decode(),
        'commits': git('log', '--reverse', '--format=%H %s', BASE + '..HEAD').decode().splitlines(),
        'source_changes': pins, 'protected': protected, 'unchanged_history_fixtures': fixed_history,
        'sequence_script_sha256': current[sequence],
        'static_package_map_sha256': {'before': sha(canonical(previous)), 'after': sha(canonical(current))},
        'source_map_scope': 'Static source inventory only; not a new registration or authority.',
        'searches': searches, 'cohorts': cohorts,
        'script': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__).read_bytes())}}
path = OUT / 'audit.json'
save(path, data)
print(json.dumps({'audit': str(path), 'sha256': sha(path.read_bytes()),
                  'cohorts': {c['name']: c.get('counts', c['outcome']) for c in cohorts}}, indent=2))
