"""Summarize saved committed census measurements for the lead, 2026-11-15.

Input: assignment scratch root. Output: JSON and phase Markdown in scratch.
All numbers derive from saved measurement rows; no production calls.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

scratch = Path(sys.argv[1])
out = scratch / 'committed-after'


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


summary = {}
for label, directory in [('before', 'before-ruling-canonical'), ('after', 'committed-after')]:
    groups = {}
    for row in rows(scratch / directory / 'phases.jsonl'):
        key = row['file'] + ':' + row['function']
        group = groups.setdefault(key, {'calls': 0, 'seconds': 0})
        group['calls'] += 1
        group['seconds'] += row['seconds']
    summary[label] = groups

before_total = summary['before']['test_native_shared_execution.py:make_case']['seconds']
after_total = summary['after']['test_native_shared_execution.py:make_case']['seconds']
summary['comparison'] = {'before_seconds': before_total, 'after_seconds': after_total,
    'reduction_seconds': before_total - after_total,
    'reduction_percent': 100 * (before_total - after_total) / before_total}
for line in (out / 'run.log').read_text().splitlines():
    try:
        value = json.loads(line)
    except ValueError:
        continue
    if 'guard' in value:
        captured = datetime.fromisoformat(value['guard']['captured_at'].replace('Z', '+00:00')).timestamp()
        summary['capture_to_ready_seconds'] = value['ready_wall_ns'] / 1e9 - captured

lines = ['Phase times include callees and must not be summed.', '',
         '| Phase | Before calls | Before seconds | After calls | After seconds |',
         '| --- | ---: | ---: | ---: | ---: |']
for key in sorted(set(summary['before']) | set(summary['after'])):
    before = summary['before'].get(key, {'calls': 0, 'seconds': 0})
    after = summary['after'].get(key, {'calls': 0, 'seconds': 0})
    lines.append(f"| {key} | {before['calls']} | {before['seconds']:.3f} | {after['calls']} | {after['seconds']:.3f} |")

public = scratch / 'committed-public-retry'
if public.exists():
    measurements = rows(public / 'timing.jsonl')
    summary['public_measurements'] = measurements
    cases = list(ET.parse(public / 'result.xml').getroot().iter('testcase'))
    summary['public_test'] = {'cases': len(cases),
        'failures': sum(case.find('failure') is not None for case in cases),
        'seconds': sum(float(case.get('time')) for case in cases)}
    assert len(cases) == 1 and cases[0].find('failure') is not None
    assert 'subscription observation is stale or future-dated' in cases[0].find('failure').text
    assert not list(public.rglob('subscription-dispatched.json'))
    assert not list(public.rglob('host-controller-timing.jsonl'))
    guard_path = next(public.rglob('invented-subscription.json'))
    guard = json.loads(guard_path.read_text())
    summary['guard_max_age_seconds'] = guard['max_age_seconds']
    pre_paths = list(public.rglob('host-pre-dispatch-*.jsonl'))
    pre_rows = [row for path in pre_paths for row in rows(path)]
    summary['pre_dispatch_files'] = [str(p) for p in pre_paths]
    launch = next(r for r in measurements if r.get('function') == 'launch_case' and r['boundary'] == 'start')
    capture_row = next(r for r in pre_rows if r['boundary'] == 'capture_selected')
    capture = datetime.fromisoformat(capture_row['captured_at'].replace('Z', '+00:00')).timestamp()
    ended = next(r for r in measurements if r['boundary'] == 'pytest_end')
    launch_rows = [r for r in pre_rows if r['wall_ns'] >= launch['wall_ns']]
    summary['public_intervals'] = {
        'capture_timestamp': capture_row['captured_at'],
        'capture_to_launch_seconds': launch['wall_ns'] / 1e9 - capture,
        'capture_to_last_authority_end_seconds': max(r['wall_ns'] for r in launch_rows) / 1e9 - capture,
        'capture_to_pytest_end_seconds': ended['wall_ns'] / 1e9 - capture,
        'launch_to_pytest_end_seconds': (ended['wall_ns'] - launch['wall_ns']) / 1e9,
        'dispatch_occurred': False,
        'scope': 'No dispatch timestamp exists. Pytest end is an upper envelope for refusal age, not its exact timestamp.'}
    starts = {(r['trace_id'], r['step_id']): r for r in launch_rows if r.get('phase') == 'start'}
    groups = {}
    for row in launch_rows:
        if row.get('phase') != 'end':
            continue
        begin = starts[(row['trace_id'], row['step_id'])]
        group = groups.setdefault(row['boundary'], {'calls': 0, 'seconds': 0})
        group['calls'] += 1
        group['seconds'] += (row['elapsed_ns'] - begin['elapsed_ns']) / 1e9
    summary['launch_phases'] = groups
    launch_table = ['Nested launch phase durations; do not sum overlapping rows.', '',
        '| Phase | Calls | Seconds |', '| --- | ---: | ---: |']
    for name, group in sorted(groups.items()):
        launch_table.append(f"| {name} | {group['calls']} | {group['seconds']:.3f} |")
    (out / 'launch-phases.md').write_text('\n'.join(launch_table) + '\n')
    timing_files = list(public.rglob('host-controller-timing.jsonl'))
    summary['controller_files'] = [str(p) for p in timing_files]
    for path in timing_files:
        timing = rows(path)
        summary['controller_timing'] = timing
        guard = json.loads((path.parent / 'subscription-guard.json').read_text())
        capture = datetime.fromisoformat(guard['captured_at'].replace('Z', '+00:00')).timestamp()
        dispatch = next((r for r in timing if r['boundary'] == 'child_dispatch'), None)
        if dispatch:
            interval = dispatch['wall_ns'] / 1e9 - capture
            summary['freshness'] = {'capture_to_dispatch_seconds': interval,
                'max_age_seconds': guard['max_age_seconds'],
                'margin_seconds': guard['max_age_seconds'] - interval}
        starts = {r['tool_use_id']: r for r in timing if r['boundary'] == 'helper_start'}
        summary['helper_intervals'] = [dict(tool_use_id=r['tool_use_id'],
            seconds=(r['monotonic_ns'] - starts[r['tool_use_id']]['monotonic_ns']) / 1e9,
            command_sha256=starts[r['tool_use_id']]['command_sha256'])
            for r in timing if r['boundary'] == 'helper_end' and r['tool_use_id'] in starts]
    summary['actual_results'] = {str(p): json.loads(p.read_text()) for p in public.rglob('actual-result.json')}

summary['evidence_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
    for directory in (out, public) if directory.exists()
    for p in directory.iterdir() if p.is_file() and p.name not in ('summary.json', 'phases.md', 'launch-phases.md', 'summary-output.txt')}
for path in public.rglob('host-pre-dispatch-*.jsonl'):
    summary['evidence_sha256'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
summary['evidence_sha256'][str(guard_path)] = hashlib.sha256(guard_path.read_bytes()).hexdigest()
summary['host_load_samples'] = {}
for directory in (out, public):
    samples = [list(map(float, match)) for match in re.findall(
        r'load averages: ([\d.]+) ([\d.]+) ([\d.]+)', (directory / 'host-start.txt').read_text())]
    summary['host_load_samples'][directory.name] = {'samples': samples,
        'minimum_one_minute': min(row[0] for row in samples),
        'maximum_one_minute': max(row[0] for row in samples)}
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
(out / 'phases.md').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
print(json.dumps({key: summary[key] for key in ('comparison', 'capture_to_ready_seconds',
    'public_test', 'public_intervals', 'launch_phases') if key in summary}, indent=2))
if 'freshness' in summary:
    print(json.dumps(summary['freshness']))
