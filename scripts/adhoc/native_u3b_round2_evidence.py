"""Summarize U3-B round-2 evidence, 2026-11-07.

Inputs: unique scratch directory and current source; output: JSON summary.
Records failures by node ID and checks log source hashes against final bytes.
Supports P2-1/2/3 and the round-2 review report; no network or test execution.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
directory = Path(sys.argv[1]).resolve()
result = {'directory': str(directory), 'runs': {}, 'artifacts': {}, 'protected_unchanged': {}}
result['final_files'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in [ROOT / 'tests/test_native_u3b_reuse.py',
                 *sorted((ROOT / 'src/data_sheets_schema').glob('native_*.py'))]}
for log in sorted(directory.glob('*.log')):
    text = log.read_text()
    header = json.loads(text.splitlines()[0])
    event_file = log.with_suffix('.events.jsonl')
    events = [json.loads(line) for line in event_file.read_text().splitlines()] if event_file.exists() else []
    source = Path(header['cwd'])
    matches = all(hashlib.sha256((source / name).read_bytes()).hexdigest() == digest
                  for name, digest in header['source_sha256'].items())
    result['runs'][log.stem] = {
        'start_utc': header['start_utc'], 'cwd': str(source), 'source_hashes_match': matches,
        'exit': re.findall(r'U3B_EXIT=(-?\d+)', text),
        'elapsed_seconds': re.findall(r'elapsed_seconds=([\d.]+)', text),
        'wall_seconds': re.findall(r'wall_seconds=([\d.]+)', text),
        'summary': [line for line in text.splitlines() if re.search(r'\d+ (passed|failed|error|tests collected)', line)
                    and not line.startswith('{')][-3:],
        'outcomes': dict(Counter(row['phase'] + ':' + row['outcome'] for row in events)),
        'failures': [row for row in events if row['outcome'] == 'failed'],
        'sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
    }
for path in sorted(directory.glob('*cpu-smoke*.json')):
    result['artifacts'][path.name] = {'bytes': path.stat().st_size,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    if 'assembly' not in path.name:
        result['artifacts'][path.name]['content'] = json.loads(path.read_bytes())
for name in ['audit_omissions.py', 'cache_dependencies.py', 'typed_audit.py', 'schema_snapshot.py',
             'shared_generation.py', 'native_shared_selection.py']:
    relative = 'src/data_sheets_schema/' + name
    old = subprocess.check_output(['git', 'show', 'a3aac3bed:' + relative], cwd=ROOT)
    result['protected_unchanged'][relative] = old == (ROOT / relative).read_bytes()
for relative in ['src/download/prompts/canonical_hashes.yaml',
                 'tests/utils/run_spec_boundaries.py', 'tests/utils/run_spec_boundary_contracts.json']:
    old = subprocess.check_output(['git', 'show', 'a3aac3bed:' + relative], cwd=ROOT)
    result['protected_unchanged'][relative] = old == (ROOT / relative).read_bytes()
for run_name in ('bc1', 'bc1-wall-final'):
    bc1 = result['runs'].get(run_name, {})
    if not bc1.get('exit'):
        continue
    baseline = json.loads((directory.parent / 'bc1-comparison.json').read_bytes())
    expected = {(row['nodeid'], row['phase']): row['message'] for row in baseline['failures']}
    actual = {(row['nodeid'], row['phase']): row['failure'].splitlines()[-1]
              for row in bc1['failures']}
    result[run_name + '_matches_saved_exact_base_failures'] = actual == expected
    result['bc1_baseline_comparison_sha256'] = hashlib.sha256(
        (directory.parent / 'bc1-comparison.json').read_bytes()).hexdigest()
for name in ('collect', 'collect-final'):
    path = directory / (name + '.log')
    if path.exists() and 'U3B_EXIT=' in path.read_text():
        text = path.read_text()
        baseline = (directory.parent / 'collect-base.log').read_text()
        errors = lambda value: (re.findall(r'^ERROR (tests/[^\n]+)$', value, re.M),
                               re.findall(r'^E   ModuleNotFoundError: (.+)$', value, re.M))
        result[name + '_matches_saved_exact_base_errors'] = errors(text) == errors(baseline)
api_events = directory / 'api-wall-final.events.jsonl'
if api_events.exists():
    files = (directory / 'api-wall-final-roster.txt').read_text().splitlines()
    nodes = re.findall(r'^(tests/[^\n]+::[^\n]+)$',
                       (directory / 'collect-final.log').read_text(), re.M)
    expected = [node for filename in files for node in nodes if node.split('::', 1)[0] == filename]
    observed = [row['nodeid'] for row in map(json.loads, api_events.read_text().splitlines())
                if row['phase'] == 'call']
    result['api_order'] = {'expected_nodes': len(expected), 'observed_nodes': len(observed),
        'matches_collection_prefix': observed == expected[:len(observed)],
        'complete_order': observed == expected,
        'observed_order_sha256': hashlib.sha256('\n'.join(observed).encode()).hexdigest()}
    continuation = directory / 'api-remaining-final.events.jsonl'
    if continuation.exists():
        selections = sorted(directory.glob('api-remaining*-selection.json'))
        labels = ['api-wall-final', *[path.name.removesuffix('-selection.json') for path in selections]]
        passed = []
        failures = []
        for label in labels:
            path = directory / (label + '.events.jsonl')
            rows = list(map(json.loads, path.read_text().splitlines())) if path.exists() else []
            passed.extend(row['nodeid'] for row in rows
                          if row['phase'] == 'call' and row['outcome'] == 'passed')
            failures.extend(row for row in rows if row['outcome'] == 'failed')
        ledgers = [json.loads(path.read_bytes()) for path in selections]
        result['api_broad_coverage'] = {
            'runs': labels, 'expected_nodes': len(expected), 'passed_nodes': len(passed),
            'disjoint': len(passed) == len(set(passed)),
            'complete': set(passed) == set(expected), 'failures': failures,
            'continuation_selection_matches': all(
                set(ledger['pending']) == set(expected) - set(ledger['completed']) for ledger in ledgers),
            'scope': 'Broad-suite coverage only; continuation does not preserve full-order process state',
        }
output = directory / 'round2-evidence.json'
output.write_text(json.dumps(result, indent=2) + '\n')
assert output.stat().st_size
print(json.dumps({name: {k: v for k, v in value.items() if k in ('exit', 'outcomes', 'source_hashes_match', 'summary')}
                  for name, value in result['runs'].items()}, indent=2))
