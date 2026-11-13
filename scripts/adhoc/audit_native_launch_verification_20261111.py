#!/usr/bin/env python3
"""Read-only native verification audit, 2026-11-11; no execution or new probe.

Inputs: retained 382f CPU monitoring JSON or named historical pstats files.
Output: stdout only, for the assigned native launch verification report.
No production imports, test/diagnostic invocation, network or source writes.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import pstats

BASE = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
RUN = BASE / 'scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111'
LABELS = ('shared_registration_verified', 'execution_registration_verified', 'preparer_verified', 'controller_prewarm')


def counts():
    path = RUN / 'phase-metrics/67941-measurement.json'
    raw = path.read_bytes()
    doc = json.loads(raw)
    phase = next(p for p in doc['phases'] if p['name'] == 'launch')
    first, last = phase['first_call_row'], phase['last_call_row_exclusive']
    rows = doc['calls']
    stack = []
    parents, children = {}, defaultdict(list)
    for i in range(first, last):
        row = rows[i]
        assert row['phase'] == 'launch' and row['outcome'] != 'open'
        end = row['entered_wall'] + row['inclusive_wall']
        while stack and rows[stack[-1]]['entered_wall'] + rows[stack[-1]]['inclusive_wall'] < row['entered_wall']:
            stack.pop()
        parent = stack[-1] if stack else None
        if parent is not None:
            assert rows[parent]['thread'] == row['thread']
            assert end <= rows[parent]['entered_wall'] + rows[parent]['inclusive_wall'] + 1e-6
            children[parent].append(i)
        parents[i] = parent
        stack.append(i)
    self_cpu = {i: rows[i]['inclusive_thread_cpu'] - sum(rows[j]['inclusive_thread_cpu'] for j in children[i])
                for i in range(first, last)}
    assert min(self_cpu.values()) >= -1e-6
    summary = {}
    for label in LABELS:
        chosen = [i for i in range(first, last) if rows[i]['label'] == label]
        summary[label] = {'count': len(chosen), 'inclusive_thread_cpu': sum(rows[i]['inclusive_thread_cpu'] for i in chosen),
            'inclusive_thread_cpu_min': min(rows[i]['inclusive_thread_cpu'] for i in chosen),
            'inclusive_thread_cpu_max': max(rows[i]['inclusive_thread_cpu'] for i in chosen),
            'inclusive_wall': sum(rows[i]['inclusive_wall'] for i in chosen),
            'unmonitored_self_cpu': sum(self_cpu[i] for i in chosen),
            'code_objects': len({rows[i]['code_object_id'] for i in chosen}),
            'source_locations': sorted({(Path(rows[i]['file']).name, rows[i]['first_line']) for i in chosen}),
            'parent_counts': dict(Counter(rows[parents[i]]['label'] if parents[i] is not None else 'phase' for i in chosen))}
        assert len(chosen) == doc['call_counts']['launch:' + label]
    diagnostic_path = RUN / 'phase-metrics/67941-diagnostic.json'
    diagnostic_raw = diagnostic_path.read_bytes()
    diagnostic = json.loads(diagnostic_raw)
    captured = datetime.fromisoformat(diagnostic['capture_timestamp'])
    entry_age = (datetime.fromisoformat(phase['before']['utc']) - captured).total_seconds()
    remaining = 210 - entry_age
    freshness = [{'row': i, 'label': rows[i]['label'], 'outcome': rows[i]['outcome'],
                  'capture_age_at_entry': (datetime.fromisoformat(rows[i]['entered_utc']) - captured).total_seconds()}
                 for i in range(first, last) if rows[i]['label'].startswith('freshness_before_')]
    budget = {'capture_to_launch': entry_age, 'remaining_210_budget': remaining,
              'self_cpu_excess_over_remaining_budget': phase['elapsed']['process_cpu'] - remaining,
              'freshness': freshness}
    print(json.dumps({'measurement': str(path), 'sha256': hashlib.sha256(raw).hexdigest(),
        'diagnostic_sha256': hashlib.sha256(diagnostic_raw).hexdigest(), 'budget': budget,
        'phase': phase, 'cpu_policy': doc['cpu_policy'], 'summary': summary,
        'all_monitored_self_cpu': sum(self_cpu.values()), 'thread_count': len({rows[i]['thread'] for i in range(first, last)})}, indent=2))
    print('\nROW | LABEL | PARENT ROW/LABEL | THREAD CPU | UNMONITORED SELF | CALLEE')
    for i in range(first, last):
        row = rows[i]
        if row['label'] not in LABELS:
            continue
        parent = parents[i]
        label = rows[parent]['label'] if parent is not None else 'phase'
        print(f"{i} | {row['label']} | {parent}/{label} | {row['inclusive_thread_cpu']:.9f} | {self_cpu[i]:.9f} | {Path(row['file']).name}:{row['first_line']}")
    for i in range(first, last):
        if rows[i]['label'] == 'controller_prewarm':
            print('\nPREWARM COARSE', json.dumps(rows[i]['coarse_elapsed'], sort_keys=True))
            print('PREWARM DIRECT CHILDREN', [(j, rows[j]['label'], rows[j]['inclusive_thread_cpu']) for j in children[i]])


def profiles(paths):
    targets = ('prewarm_before_acceptance', 'preloaded_callbacks', 'verify_preparer', 'verified',
               '_wire', 'dependency_identity', 'require_committed', 'verified_source_module', 'check_active')
    for name in paths:
        path = Path(name)
        raw = path.read_bytes()
        stats = pstats.Stats(str(path))
        print('\nPROFILE', json.dumps({'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'total_tt': stats.total_tt}))
        selected = [(k, v) for k, v in stats.stats.items() if k[2] in targets and 'native_' in k[0]]
        for key, value in sorted(selected, key=lambda pair: pair[1][3], reverse=True):
            callers = [{'file': k[0], 'line': k[1], 'name': k[2], 'metrics': v} for k, v in value[4].items()]
            print(json.dumps({'function': key, 'primitive_calls': value[0], 'calls': value[1],
                              'self': value[2], 'cumulative': value[3], 'callers': callers}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('counts', 'profiles'))
    parser.add_argument('paths', nargs='*')
    args = parser.parse_args()
    counts() if args.mode == 'counts' else profiles(args.paths)
