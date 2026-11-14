#!/usr/bin/env python3
"""Compare saved G2 freshness timing pairs, 2026-11-14.

Inputs: immutable ENGINE-FRESHNESS-F1 evidence and completed serial canary.
Outputs: exclusive saved-freshness-clock-comparison-20261114/comparison.json
plus input snapshots. Pairs only equal trace_id/PID/step_id, with equal boundary.
No project imports, profiling, probes, processes, tests, clock/source changes,
signals or commits. Serves the unresolved latency evidence for that finding.
"""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUT = SCRATCH / 'saved-freshness-clock-comparison-20261114'
LEDGER = SCRATCH / 'review-engine-freshness.json'
CANARY = SCRATCH / 'freshness-serial-canary'
NODE = 'test_v2_publication_failure_preserves_first_error[published.json]'
FILE = 'tests/test_native_shared_execution_failure.py'
CLOCK_SOURCES = ('src/data_sheets_schema/native_elapsed.py',
                 'src/data_sheets_schema/native_pre_dispatch_timing.py')


def require(value, reason):
    if not value:
        raise ValueError(reason)


def pin(path):
    raw = path.read_bytes()
    require(bool(raw), 'empty evidence: ' + str(path))
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def checked(record):
    require(pin(Path(record['path'])) == record, 'saved pin differs: ' + record['path'])
    return Path(record['path'])


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
    require(path.read_bytes() == raw, 'saved artifact readback differs')
    return pin(path)


def snapshot(path, relative):
    original = pin(path)
    saved = save(OUT / relative, path.read_bytes())
    require(pin(path) == original and all(original[k] == saved[k] for k in ('bytes', 'sha256')),
            'input changed while copied')
    return {'original': original, 'snapshot': saved}


def compare(trace_path, registration_sha256):
    rows = [json.loads(raw) for raw in trace_path.read_bytes().splitlines()]
    require(all(row['registration_sha256'] == registration_sha256 for row in rows),
            'trace registration differs from guard')
    grouped, points = defaultdict(list), []
    for line, row in enumerate(rows, 1):
        if 'phase' not in row:
            points.append({'line': line, 'boundary': row['boundary'], 'trace_id': row['trace_id'], 'pid': row['pid']})
            continue
        require(row['phase'] in ('start', 'end'), 'unexpected timing phase')
        grouped[(row['trace_id'], row['pid'], row['step_id'])].append((line, row))
    paired, unmatched = [], []
    for (trace_id, pid, step_id), entries in grouped.items():
        phases = {row['phase'] for _, row in entries}
        require(len(entries) <= 2 and len(phases) == len(entries), 'duplicate phase for the same trace/PID/step')
        identity = {'trace_id': trace_id, 'pid': pid, 'step_id': step_id}
        if phases != {'start', 'end'}:
            unmatched.append({**identity, 'records': [{'line': line, **row} for line, row in entries]})
            continue
        start_line, start = next(item for item in entries if item[1]['phase'] == 'start')
        end_line, end = next(item for item in entries if item[1]['phase'] == 'end')
        require(start_line < end_line and start['boundary'] == end['boundary'], 'invalid start/end pairing')
        require(all(type(row[key]) is int for row in (start, end) for key in ('wall_ns', 'elapsed_ns')),
                'clock observations must be integer nanoseconds')
        wall = end['wall_ns'] - start['wall_ns']
        elapsed = end['elapsed_ns'] - start['elapsed_ns']
        require(elapsed >= 0, 'elapsed clock went backwards within a paired span')
        paired.append({**identity, 'boundary': start['boundary'],
            'start_line': start_line, 'end_line': end_line,
            'start': {key: start[key] for key in ('wall_ns', 'elapsed_ns')},
            'end': {key: end[key] for key in ('wall_ns', 'elapsed_ns')},
            'end_error_type': end.get('error_type'),
            'delta_wall_ns': wall, 'delta_elapsed_ns': elapsed,
            'wall_minus_elapsed_ns': wall - elapsed,
            'absolute_divergence_ns': abs(wall - elapsed)})
    require(bool(paired), 'no complete timing pairs')
    longest = max(paired, key=lambda row: row['delta_elapsed_ns'])
    largest = max(paired, key=lambda row: row['absolute_divergence_ns'])
    reservations = [row for row in paired if row['boundary'] == 'reservation']
    require(len(reservations) == 1, 'ambiguous reservation pair')
    return {'rows': len(rows), 'trace_ids': sorted({row['trace_id'] for row in rows}),
        'paired_spans': paired, 'point_events_not_paired': points, 'unmatched_spans': unmatched,
        'summary': {'paired_count': len(paired), 'unmatched_count': len(unmatched),
            'largest_absolute_divergence': largest, 'longest_paired_span': longest,
            'reservation': reservations[0],
            'any_absolute_divergence_at_least_one_second': any(row['absolute_divergence_ns'] >= 1000000000 for row in paired)}}


def main():
    require(not OUT.exists(), 'preserve existing comparison')
    ledger = json.loads(LEDGER.read_bytes())
    finding, = [row for row in ledger['findings'] if row['finding_id'] == 'G2-REVIEW-ENGINE-FRESHNESS-F1']
    require(len(finding['cases']) == 3, 'unexpected failed-case scope')
    command = json.loads((CANARY / 'command.json').read_bytes())
    outcome = json.loads((CANARY / 'outcome.json').read_bytes())
    require(outcome['returncode'] == 0 and outcome['counts'] == {'total': 1, 'failed': 0, 'error': 0, 'skipped': 0},
            'serial canary did not finish successfully')
    junit = list(ET.parse(CANARY / 'pytest.xml').iter('testcase'))
    require(len(junit) == 1 and junit[0].get('name') == NODE
            and junit[0].get('classname') == FILE[:-3].replace('/', '.')
            and not any(junit[0].find(tag) is not None for tag in ('failure', 'error', 'skipped')),
            'serial canary exact identity/status differs')
    require(FILE + '::' + NODE in command['command'] and '-n' not in command['command'],
            'serial canary invocation differs')
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, check=True).stdout.decode().strip()
    for recorded in (ledger['source_head'], command['head']):
        subprocess.run(['git', 'diff', '--exit-code', recorded, head, '--', *CLOCK_SOURCES],
                       cwd=ROOT, capture_output=True, check=True)
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', *CLOCK_SOURCES],
                   cwd=ROOT, capture_output=True, check=True)
    OUT.mkdir()
    inputs = {'failure_ledger': snapshot(LEDGER, 'review-engine-freshness.json'),
              'canary': {name: snapshot(CANARY / name, 'canary-' + name)
                         for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log')},
              'clock_sources': {name: snapshot(ROOT / name, 'clock-sources/' + Path(name).name)
                                for name in CLOCK_SOURCES}}
    results = []
    for index, case in enumerate(finding['cases'], 1):
        guard_path = checked(case['evidence']['guard']['snapshot'])
        trace_path = checked(case['evidence']['reservation_trace']['snapshot'])
        guard = json.loads(guard_path.read_bytes())
        result = compare(trace_path, guard['registration_sha256'])
        require(result['summary']['reservation']['end_error_type'] == 'ValueError', 'failed reservation trace differs')
        results.append({'case': case['nodeid'], 'cohort': 'final-engine-dependents',
            'status': 'confirmed pre-reservation margin failure in interrupted cohort',
            'guard': snapshot(guard_path, f'case-{index}/guard.json'),
            'trace': snapshot(trace_path, f'case-{index}/timing.jsonl'), **result})
    case_root = CANARY / 'cases/test_v2_publication_failure_pr0/v2-lifecycle'
    guard_path = case_root / 'authority/invented-subscription.json'
    guard = json.loads(guard_path.read_bytes())
    trace_path = case_root / ('host-pre-dispatch-' + guard['registration_sha256'] + '.jsonl')
    result = compare(trace_path, guard['registration_sha256'])
    require(result['summary']['reservation']['end_error_type'] is None, 'serial reservation did not complete')
    results.append({'case': FILE + '::' + NODE, 'cohort': 'freshness-serial-canary',
        'status': 'completed single serial test; not whole-file acceptance',
        'guard': snapshot(guard_path, 'serial-canary/guard.json'),
        'trace': snapshot(trace_path, 'serial-canary/timing.jsonl'), **result})
    spans = [(row['cohort'], row['case'], pair) for row in results for pair in row['paired_spans']]
    largest = max(spans, key=lambda item: item[2]['absolute_divergence_ns'])
    comparison = {'kind': 'saved_paired_clock_comparison', 'finding_id': finding['finding_id'],
        'producer': pin(Path(__file__).resolve()), 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'current_head': head, 'inputs': inputs, 'cases': results,
        'summary': {'cases': len(results), 'matched_pairs': len(spans),
            'maximum_absolute_divergence_ns': largest[2]['absolute_divergence_ns'],
            'maximum_divergence_location': {'cohort': largest[0], 'case': largest[1], **largest[2]},
            'signed_divergence_ns_range': [min(row[2]['wall_minus_elapsed_ns'] for row in spans),
                                          max(row[2]['wall_minus_elapsed_ns'] for row in spans)],
            'any_absolute_divergence_at_least_one_second': any(row[2]['absolute_divergence_ns'] >= 1000000000 for row in spans)},
        'interpretation_limits': [
            'Only start/end rows with equal trace_id, PID and step_id and matching boundary are paired; no subtraction across trace-relative bases or use of digits in trace_id as clock samples.',
            'Nested spans overlap and are not summed. Point events and unmatched spans remain recorded without a duration claim.',
            'wall_ns and elapsed_ns are sampled consecutively, not atomically; small differences do not identify their internal source.',
            'The retained Darwin elapsed implementation uses mach_continuous_time and explicitly includes suspension. Agreement with wall time cannot establish uninterrupted execution or exclude sleep.',
            'Divergence, if observed, would not by itself prove sleep, host load or any particular cause. These observations neither profile execution nor establish why validation took so long.',
            'One second is an explicit descriptive comparison threshold, not an acceptance limit. The exact integer differences are retained.',
            'A serial pass is not a source correction or full-file acceptance; original parallel failures and review ledger remain unchanged.'],
        'tests_run': [], 'project_imports': [], 'host_probes': [], 'signals': [],
        'source_test_clock_or_limit_changes': [], 'commits': []}
    path = OUT / 'comparison.json'
    saved = save(path, (json.dumps(comparison, indent=2, sort_keys=True) + '\n').encode())
    require(json.loads(path.read_bytes()) == comparison, 'comparison readback differs')
    print(json.dumps({'comparison': saved, 'summary': comparison['summary'],
        'per_case': [{'cohort': row['cohort'], 'case': row['case'],
            'paired_count': row['summary']['paired_count'], 'unmatched_count': row['summary']['unmatched_count'],
            'max_divergence_ns': row['summary']['largest_absolute_divergence']['absolute_divergence_ns'],
            'reservation_wall_ns': row['summary']['reservation']['delta_wall_ns'],
            'reservation_elapsed_ns': row['summary']['reservation']['delta_elapsed_ns']}
            for row in results]}, indent=2))


if __name__ == '__main__':
    main()
