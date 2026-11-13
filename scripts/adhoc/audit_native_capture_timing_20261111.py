#!/usr/bin/env python3
"""Audit retained native capture timing, 2026-11-11; no diagnostic execution.

Purpose: reproduce baseline cost bounds for the capture-timing question / PR 5871.
Inputs: completed 382f measurement and diagnostic JSON in the fixed native evidence path.
Outputs: JSON to stdout only; no production imports, network or artifact writes.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path


EVIDENCE = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111/phase-metrics')


def main():
    inputs = {}
    loaded = {}
    for name in ('67941-measurement.json', '67941-diagnostic.json'):
        raw = (EVIDENCE / name).read_bytes()
        inputs[name] = hashlib.sha256(raw).hexdigest()
        loaded[name] = json.loads(raw)
    measurement = loaded['67941-measurement.json']
    diagnostic = loaded['67941-diagnostic.json']
    phase = next(row for row in measurement['phases'] if row['name'] == 'launch')
    captured = datetime.fromisoformat(diagnostic['capture_timestamp'])
    entry_age = (datetime.fromisoformat(phase['before']['utc']) - captured).total_seconds()
    selected = []
    for index, role in ((972, 'retained_postaccept_join'),
                        (1046, 'removed_second_unchanged_verification'),
                        (1080, 'retained_lease_verification')):
        row = measurement['calls'][index]
        assert row['label'] == 'shared_registration_verified' and row['phase'] == 'launch'
        assert row['outcome'] == 'return'
        selected.append({'row': index, 'role': role,
                         'thread_cpu_seconds': row['inclusive_thread_cpu'],
                         'wall_seconds': row['inclusive_wall']})
    removed = selected[1]['thread_cpu_seconds']
    allowance = diagnostic['capture_age_limit_seconds'] - diagnostic['capture_margin_seconds']
    needed = phase['elapsed']['process_cpu'] - (allowance - entry_age)
    freshness = []
    for index in range(phase['first_call_row'], phase['last_call_row_exclusive']):
        row = measurement['calls'][index]
        if row['label'].startswith('freshness_before_'):
            freshness.append({'row': index, 'label': row['label'], 'outcome': row['outcome'],
                              'capture_age_at_entry': (datetime.fromisoformat(row['entered_utc']) - captured).total_seconds()})
    print(json.dumps({'inputs_sha256': inputs, 'profile': diagnostic['profile'],
        'outcome': diagnostic['outcome'], 'measurement_class': diagnostic['measurement_class'],
        'age_limit': diagnostic['capture_age_limit_seconds'], 'margin': diagnostic['capture_margin_seconds'],
        'pre_reservation_allowance': allowance, 'capture_to_launch_seconds': entry_age,
        'phase_process_cpu': phase['elapsed']['process_cpu'], 'phase_wall': phase['elapsed']['wall_monotonic'],
        'self_cpu_deficit_seconds': needed, 'selected_baseline_calls': selected,
        'conditional_remaining_self_cpu_deficit_if_entire_removed_call_cost_saved': needed - removed,
        'conditional_deficit_even_with_zero_capture_to_launch_delay_and_entire_call_saved': phase['elapsed']['process_cpu'] - removed - allowance,
        'freshness_entries': freshness,
        'limits': 'Counterfactual baseline subtraction, not measured candidate speedup; nested child times are not added.'}, indent=2))


if __name__ == '__main__':
    main()
