"""Summarize persisted census-ruling evidence, 2026-11-15 public-stale task.

Inputs: scratch phase logs and test logs. Outputs: JSON and Markdown phase table
under notes/reviews. No external requests or inferred successful outcomes.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
scratch = Path(sys.argv[1]).resolve()
summary = {}
for name, directory in (('before', 'before-ruling-canonical'), ('after', 'after-ruling')):
    location = scratch / directory
    rows = [json.loads(line) for line in (location / 'phases.jsonl').read_text().splitlines()]
    groups = {}
    for row in rows:
        key = row['file'] + ':' + row['function']
        group = groups.setdefault(key, {'calls': 0, 'seconds': 0.0})
        group['calls'] += 1
        group['seconds'] += row['seconds']
    values = []
    for line in (location / 'run.log').read_text().splitlines():
        try:
            values.append(json.loads(line))
        except ValueError:
            continue
    result = next((row for row in values if 'guard' in row), None)
    timing = None
    if result is not None:
        guard = result['guard']
        captured = datetime.fromisoformat(guard['captured_at'].replace('Z', '+00:00')).timestamp()
        interval = result['ready_wall_ns'] / 1e9 - captured
        timing = {'make_case_seconds': groups['test_native_shared_execution.py:make_case']['seconds'],
                  'ready_elapsed_seconds': result['seconds'], 'capture_to_ready_seconds': interval,
                  'freshness_margin_at_ready_seconds': guard['max_age_seconds'] - interval,
                  'max_age_seconds': guard['max_age_seconds']}
    first_phases = {}
    for row in rows:
        first_phases.setdefault(row['file'] + ':' + row['function'], row['seconds'])
    summary[name] = {'phases': groups, 'first_phase_seconds': first_phases, 'timing': timing,
                     'watchdog': next((row for row in values if 'returncode' in row), None)}

manifest = root / 'src/data_sheets_schema/native_environment_manifest.py'
summary['pin_proposal'] = {'path': str(manifest.relative_to(root)),
    'old_sha256': '790040b275d4d67aed40a6805835bb688030ec0ef3e7e004984aadcf4a2c10b7',
    'new_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()}
summary['evidence'] = {}
for pattern in ('before-ruling-canonical/*.jsonl', 'before-ruling-canonical/*.log',
                'before-ruling-canonical/*.txt',
                'after-ruling/*.jsonl', 'after-ruling/*.log', 'ruling-*.log',
                'ruling-*.xml', 'public-ruling*.jsonl', 'candidate-*.log',
                'ruling-runs/**/*.xml', 'ruling-runs/**/*.jsonl', 'ruling-runs/**/*.log',
                'ruling-runs/**/manifest-cost.json'):
    for path in sorted(scratch.glob(pattern)):
        summary['evidence'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()

summary['tests'] = {}
for label, path in (('focused', scratch / 'ruling-focused.xml'),
                    ('canaries', scratch / 'ruling-runs/canaries.xml'),
                    ('commit_boundary', scratch / 'ruling-runs/commit-boundary.xml'),
                    ('scanner', scratch / 'ruling-runs/scanner.xml')):
    if path.exists():
        cases = list(ET.parse(path).getroot().iter('testcase'))
        summary['tests'][label] = {'cases': len(cases),
            'failures': sum(case.find('failure') is not None for case in cases),
            'errors': sum(case.find('error') is not None for case in cases),
            'skipped': sum(case.find('skipped') is not None for case in cases)}
lines = ['Before is complete; after stops at the source-commit proof. Zero calls means no completed call.',
         'Phase durations include callees; rows must not be summed.', '',
         '| Phase | Before calls | Before seconds | After calls | After seconds |',
         '| --- | ---: | ---: | ---: | ---: |']
keys = sorted(set(summary['before']['phases']) | set(summary['after']['phases']))
for key in keys:
    before = summary['before']['phases'].get(key, {'calls': 0, 'seconds': 0})
    after = summary['after']['phases'].get(key, {'calls': 0, 'seconds': 0})
    lines.append(f"| {key} | {before['calls']} | {before['seconds']:.3f} | {after['calls']} | {after['seconds']:.3f} |")
data = root / 'notes/reviews/census_ruling_20261115.json'
table = data.with_suffix('.md')
data.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
table.write_text('\n'.join(lines) + '\n')
print(json.dumps(summary, indent=2, sort_keys=True))
