"""Record U3-C Round 3 evidence before transient cleanup, 2026-11-07.

Inputs: completed assigned-scratch runs and merged Git tree. Outputs: JSON
manifest, per-run basetemp inventories and verified smoke copies. No deletion.
Serves the Round 3 integration report; includes ignored temporary files.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u3c-r3'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)
def write(path, value):
    raw = json.dumps(value, indent=2, sort_keys=True) + '\n'
    if path.exists():
        assert path.read_text() == raw, 'refusing to replace different evidence: ' + str(path)
    else:
        with path.open('x') as stream:
            stream.write(raw)

if (ROOT.parent / 'plans/native_quiet_window.lock').exists():
    raise SystemExit('Quiet lock active; defer inventory')
result = {'head': git('rev-parse', 'HEAD').decode().strip(), 'runs': {}}
scratch_links = []
result['unresolved_symlinks'] = []
for path in OUT.rglob('*'):
    if path.is_symlink():
        try:
            scratch_links.append((path, path.resolve()))
        except (OSError, RuntimeError) as exc:
            # Synthetic refusal fixtures may deliberately retain symlink loops.
            assert 'cases' in path.relative_to(OUT).parts, path
            result['unresolved_symlinks'].append({'path': str(path), 'error': str(exc)})
for outcome in sorted(OUT.glob('*/outcome.json')):
    folder = outcome.parent
    observed = json.loads(outcome.read_text())
    assert observed['cleanup_verified'], folder
    assert observed['seconds'] < 3600, folder
    log = (folder / 'pytest.log').read_text()
    xml = ET.parse(folder / 'pytest.xml')
    case_outcomes = {}
    for case in xml.iter('testcase'):
        if 'classname' not in case.attrib:
            continue  # Retained interruption diagnostic, not a collected test node.
        tags = {child.tag for child in case}
        state = next((tag for tag in ('error', 'failure', 'skipped') if tag in tags), 'passed')
        case_outcomes[case.attrib['classname'] + '::' + case.attrib['name']] = state
    suites = [dict(s.attrib) for s in xml.iter('testsuite')]
    failures = [{'case': case.attrib, 'kind': child.tag, 'message': child.attrib,
                 'text': child.text} for case in xml.iter('testcase') for child in case
                if child.tag in ('failure', 'error')]
    cases = folder / 'cases'
    if cases.exists():
        inbound = [str(path) for path, target in scratch_links
                   if target.is_relative_to(cases) and not path.is_relative_to(cases)]
        assert not inbound, inbound
        inventory = {}
        # Path.rglob includes hidden/ignored entries, does not follow symlink dirs.
        for path in sorted(cases.rglob('*')):
            if path.is_symlink():
                inventory[str(path.relative_to(cases))] = {'symlink': str(path.readlink())}
            elif path.is_file():
                inventory[str(path.relative_to(cases))] = {'bytes': path.stat().st_size,
                    'nlink': path.stat().st_nlink, 'sha256': sha(path)}
        write(folder / 'basetemp-inventory.json', inventory)
        for path in cases.rglob('cpu-smoke*.json'):
            dest = folder / path.name
            if not dest.exists():
                shutil.copyfile(path, dest)
            assert dest.stat().st_size and sha(dest) == sha(path)
        if folder.name == 'b-api-1':
            path = cases / 'popen-gw0/test_actual_completed_capture_0/relocated-capture.json'
            if path.exists():
                dest = folder / 'retained-relocated-capture.json'
                if not dest.exists():
                    shutil.copyfile(path, dest)
                assert sha(dest) == sha(path)
    artifacts = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)}
                 for p in folder.iterdir() if p.is_file()}
    result['runs'][folder.name] = {'outcome': observed, 'suites': suites,
        'case_outcomes': case_outcomes,
        'gracefully_stopped_incomplete': (folder / 'graceful-stop-requested.txt').exists(),
        'failures': failures, 'artifacts': artifacts,
        'summary': [line for line in log.splitlines()
                    if re.search(r'\d+ (passed|failed|tests collected|errors?)', line)][-4:]}
base = 'b9c144a182ccba84fac27e3b5717363c769d4a97'
donor = '35d1aae4a631ce55660c45f838c6f03688ea38d3'
common = git('merge-base', base, donor).decode().strip()
ours = set(git('diff', '--name-only', common, base).decode().splitlines())
theirs = set(git('diff', '--name-only', common, donor).decode().splitlines())
result['both_side_paths'] = sorted(ours & theirs)
result['donor_paths_preserved'] = {p: git('show', donor + ':' + p) == (ROOT / p).read_bytes()
                                  for p in sorted(theirs)}
result['changed_paths_from_start'] = git('diff', '--name-only', base, 'HEAD').decode().splitlines()
result['source_changes'] = [p for p in result['changed_paths_from_start'] if p.startswith('src/')]
assert set(result['source_changes']) == {
    'src/data_sheets_schema/native_catalog_initialization.py',
    'src/data_sheets_schema/native_schema_event_reuse.py'}
assert all(result['donor_paths_preserved'].values())
result['source_hashes'] = {str(p.relative_to(ROOT)): sha(p)
                         for p in sorted((ROOT / 'src/data_sheets_schema').glob('*.py'))}
result['git_status'] = git('status', '--short').decode()
assert not result['git_status'], result['git_status']
assert not git('diff', '1e784ed91', 'HEAD', '--', 'src', 'tests')
result['merge_parents'] = git('show', '-s', '--format=%P', '11d6b77fc').decode().strip().split()
baseline_path = ROOT.parent / 'scratch-native-u3b/bc1-comparison.json'
baseline = json.loads(baseline_path.read_text())
expected = {row['nodeid']: row['message'].removeprefix('E   ')
            for row in baseline['failures']}
actual = {}
for failure in result['runs']['b-bc1']['failures']:
    case = failure['case']
    node = case['classname'].replace('.', '/') + '.py::' + case['name']
    text = failure['text'] or ''
    message = expected.get(node)
    actual[node] = {'kind': failure['kind'], 'matches_message': message is not None and message in text}
result['bc1_baseline_comparison'] = {
    'baseline_path': str(baseline_path), 'baseline_sha256': sha(baseline_path),
    'expected_nodeids': sorted(expected), 'actual': actual,
    'matches': set(actual) == set(expected) and all(
        row['kind'] == 'error' and row['matches_message'] for row in actual.values())}
rosters = json.loads((OUT / 'rosters.json').read_text())
checks = {}
for name, key in [('api-wall-final', 'b-api-'), ('shared-wall-final', 'b-shared'), ('bc1-wall-final', 'b-bc1')]:
    original = ROOT.parent / 'scratch-native-u3b/round2-20261107T064201Z' / (name + '-roster.txt')
    ours = {node for group, nodes in rosters.items() if group.startswith(key) for node in nodes}
    checks[name] = ours == set(original.read_text().splitlines())
result['b_broad_rosters_equal'] = checks
assert all(checks.values())
api_files = {name for group, nodes in rosters.items() if group.startswith('b-api-') for name in nodes}
api_nodes = {line for line in (OUT / 'collect/pytest.log').read_text().splitlines()
             if line.split('::', 1)[0] in api_files and '::' in line}
def api_key(node):
    parts = node.split('::')
    return '.'.join([parts[0][:-3].replace('/', '.'), *parts[1:-1]]) + '::' + parts[-1]
expected_api = {api_key(node): node for node in api_nodes}
assert len(expected_api) == 522
effective = {}
for name in ['b-api-1', 'b-api-2', 'b-api-3', 'b-api-4', 'launcher-final', 'b-api-unfinished']:
    if name in result['runs']:
        effective.update(result['runs'][name]['case_outcomes'])
assert set(effective) <= set(expected_api)
result['api_effective'] = {'selected': len(expected_api), 'counts': dict(Counter(effective.values())),
    'missing': sorted(node for key, node in expected_api.items() if key not in effective),
    'scope': 'per-node broad coverage across separate processes; not full-order evidence'}
write(OUT / 'evidence.json', result)
print(json.dumps({name: run['summary'] for name, run in result['runs'].items()}, indent=2))
