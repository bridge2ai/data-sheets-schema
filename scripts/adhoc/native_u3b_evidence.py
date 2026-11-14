"""Record U3-B offline artifacts and exact API render parity, 2026-11-07.

Inputs: scratch logs, M8/candidate render bytes, current source and local Git.
Output: committed evidence JSON, or scratch BC1 comparison with --bc1-only.
Does not publish, send or alter test results.
"""
from pathlib import Path
import hashlib
import json
import importlib.metadata
import os
import re
import subprocess
import sys
from collections import Counter

os.environ['GIT_NO_LAZY_FETCH'] = '1'
os.environ['GIT_TERMINAL_PROMPT'] = '0'

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3b'
if (ROOT.parent / 'plans/native_quiet_window.lock').exists():
    raise SystemExit('Quiet window active; defer evidence scan')
BASE = 'f101652f53f23d9be83a213b6d5850bd6e9341fc'
M8 = 'cf50d9a1c059f3b5030103378ccef33619475dde'
PROTECTED = ('src/data_sheets_schema/shared_generation.py',
             'src/download/prompts/canonical_hashes.yaml',
             'tests/utils/run_spec_boundaries.py',
             'tests/utils/run_spec_boundary_contracts.json')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def identity(path):
    raw = path.read_bytes()
    assert raw, path
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}

protected = []
for name in PROTECTED:
    raw = (ROOT / name).read_bytes()
    for revision in (BASE, M8):
        assert raw == subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT), name
    protected.append(identity(ROOT / name))

base_unchanged = []
for name in ('src/data_sheets_schema/api_runner.py', '.claude/skills/d4d-generation-specificity-audit/scan.py'):
    assert (ROOT / name).read_bytes() == subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)
    base_unchanged.append(identity(ROOT / name))

test_paths = set()
for group in ('api', 'shared', 'bc1'):
    test_paths.update((SCRATCH / (group + '-roster.txt')).read_text().splitlines())
test_paths.remove('tests/test_typed_audit_captured_assets.py')  # New coverage, absent at the base.
for name in test_paths:
    assert (ROOT / name).read_bytes() == subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT), name
assert (SCRATCH / 'm8/tests/test_native_u1_api_parity.py').read_bytes() == (ROOT / 'tests/test_native_u1_api_parity.py').read_bytes()

def events(name):
    return [json.loads(line) for line in (SCRATCH / (name + '.events.jsonl')).read_text().splitlines()]

def done(rows):
    return {row['nodeid'] for row in rows if row['phase'] == 'call' or row['outcome'] in ('failed', 'skipped')}

def failures(rows):
    return {(row['nodeid'], row['phase']): row['failure'].splitlines()[-1]
            for row in rows if row['outcome'] == 'failed'}

initial, continued, baseline = events('bc1'), events('bc1-final'), events('bc1-base-failures')
pending = set(re.findall(r'^(tests/[^\n]+::[^\n]+)$', (SCRATCH / 'bc1-pending-collect.log').read_text(), re.M))
assert len(done(initial)) == 126 and len(pending) == 147
assert not done(initial) & done(continued)
assert done(continued) == pending
candidate_failures, base_failures = failures(initial + continued), failures(baseline)
assert candidate_failures == base_failures, (candidate_failures, base_failures)
bc1_comparison = {'base': BASE, 'candidate_nodes_attempted': len(done(initial) | done(continued)),
                  'initial_nodes': len(done(initial)), 'continuation_nodes': len(done(continued)),
                  'all_failures_reproduced_on_base': True,
                  'failures': [{'nodeid': node, 'phase': phase, 'message': message}
                               for (node, phase), message in sorted(candidate_failures.items())]}
if sys.argv[1:] == ['--bc1-only']:
    output = SCRATCH / 'bc1-comparison.json'
    output.write_text(json.dumps(bc1_comparison, indent=2) + '\n')
    print(output)
    raise SystemExit(0)

collection = {}
for label in ('collect-final', 'collect-base'):
    path = SCRATCH / (label + '.log')
    content = path.read_text()
    collection[label] = {
        **identity(path),
        'nodes': set(re.findall(r'^(tests/[^\n]+::[^\n]+)$', content, re.M)),
        'error_modules': re.findall(r'^ERROR (tests/[^\n]+)$', content, re.M),
        'import_errors': re.findall(r'^E   ModuleNotFoundError: (.+)$', content, re.M),
    }
final_collection, base_collection = collection['collect-final'], collection['collect-base']
assert final_collection['error_modules'] == base_collection['error_modules']
assert len(final_collection['error_modules']) == 3
assert final_collection['import_errors'] == base_collection['import_errors'] == [
    "No module named 'fairscape_models.rocrate'"] * 3
assert not base_collection['nodes'] - final_collection['nodes']
added_nodes = sorted(final_collection['nodes'] - base_collection['nodes'])
assert len(added_nodes) == 42
assert all(node.split('::')[0] in (
    'tests/test_native_u3b_reuse.py', 'tests/test_typed_audit_captured_assets.py') for node in added_nodes)
for row in collection.values():
    row['collected_nodes'] = len(row.pop('nodes'))

before, after = SCRATCH / 'parity-m8', SCRATCH / 'parity-u3b'
left = {p.name for p in before.glob('*.txt')}
right = {p.name for p in after.glob('*.txt')}
assert left == right and len(left) == 14, (left, right)
parity = []
for name in sorted(left):
    a, b = (before / name).read_bytes(), (after / name).read_bytes()
    parity.append({'condition': Path(name).stem, 'm8_sha256': sha(a),
                   'u3b_sha256': sha(b), 'm8_bytes': len(a), 'u3b_bytes': len(b), 'equal': a == b})
logs = []
for path in sorted(SCRATCH.glob('*.log')):
    text = path.read_text()
    summaries = [line for line in text.splitlines() if
                 re.search(r'\b\d+ (?:passed|failed|errors?|tests collected).* in ', line)]
    exits = re.findall(r'U3B_EXIT=(\d+); elapsed_seconds=([\d.]+)', text)
    events_path = path.with_suffix('.events.jsonl')
    events = [json.loads(line) for line in events_path.read_text().splitlines()] if events_path.exists() else []
    logs.append({**identity(path), 'summary': summaries[-1:],
                 'exit': int(exits[-1][0]) if exits else None,
                 'elapsed_seconds': float(exits[-1][1]) if exits else None,
                 'incremental_outcomes': dict(Counter(row['outcome'] for row in events)),
                 'failed_nodes': [row['nodeid'] for row in events if row['outcome'] == 'failed']})
sources = [identity(ROOT / 'src/data_sheets_schema' / name) for name in (
    'audit_omissions.py', 'cache_dependencies.py', 'schema_snapshot.py', 'typed_audit.py',
    'native_shared_selection.py', 'native_catalog_reuse.py', 'native_catalog_initialization.py',
    'native_schema_event_reuse.py', 'native_shared_receipts.py')]
extension_probes = {}
for label, filename in (
    ('m8_control', 'no-libyaml-m8-corrected.json'),
    ('candidate_before_correction', 'no-libyaml-before.json'),
    ('candidate_after_correction', 'no-libyaml-after.json'),
):
    path = SCRATCH / filename
    extension_probes[label] = {**identity(path), 'result': json.loads(path.read_text())}
for label in ('m8_control', 'candidate_after_correction'):
    probe = extension_probes[label]['result']
    assert probe['import_error'] is None and probe['default_binding_ready'] is False
    assert probe['blocked_extension_imports'] == 1
assert extension_probes['candidate_after_correction']['result']['source_sha256'] == sha(
    (ROOT / 'src/data_sheets_schema/cache_dependencies.py').read_bytes())
result = {'base': BASE, 'render_control': M8, 'protected_unchanged': protected,
          'collection_baseline_comparison': {'runs': collection, 'added_nodes': added_nodes,
              'all_collection_errors_reproduced_on_base': True},
          'optional_libyaml_import_probes': extension_probes,
          'scanner_and_runner_unchanged_from_base': base_unchanged,
          'existing_api_shared_bc1_tests_unchanged': sorted(test_paths),
          'bc1_baseline_comparison': bc1_comparison,
          'python': sys.version,
          'dependencies': {name: importlib.metadata.version(name) for name in
                           ('PyYAML', 'linkml', 'linkml-runtime', 'jsonasobj2', 'pytest', 'pytest-xdist')},
          'source_files': sources, 'logs': logs, 'api_render_parity': parity,
          'source_origin_artifacts': [identity(path) for folder in (before, after)
                                      for path in sorted(folder.glob('source-origin-*.json'))],
          'cpu_smoke': json.loads((SCRATCH / 'cpu-smoke.json').read_text()),
          'cpu_scope': 'Synthetic typed receipt preparation, assembly and independent reconstruction; not a native recorder timing trial.',
          'native_executable_or_provider_calls': False}
out = ROOT / 'scripts/adhoc/native_u3b_evidence.json'
out.write_text(json.dumps(result, indent=2) + '\n')
assert all(row['equal'] for row in parity), parity
print(out)
