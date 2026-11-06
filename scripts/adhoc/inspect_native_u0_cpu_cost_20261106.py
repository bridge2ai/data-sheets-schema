#!/usr/bin/env python3
"""Extract saved U0 CPU-cost evidence for #4354, 2026-11-06.

Inputs: the saved U0 summary and its already-recorded local pstats/JSONL files.
Output: an exclusive compact JSON artifact with hashes, measured costs/callers,
phase status and profiler limitations. No rerun, production import or network.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path


HELPER = Path(__file__).with_name('summarize_native_u0_cpu_20261106.py')
SPEC = importlib.util.spec_from_file_location('u0_saved_summary_reader', HELPER)
reader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reader)


def by_cpu(rows, limit=30, field='inclusive_cpu_seconds'):
    return sorted(rows, key=lambda row: row[field], reverse=True)[:limit]


def compact_function(row):
    return {**row, 'top_callers': row['top_callers'][:6]}


def extract(recorder):
    selected = recorder.get('selected_profile')
    if not selected:
        return {'directory': recorder['directory'], 'status': 'no_verified_profile',
                'warnings': recorder.get('warnings', [])}
    metadata = selected['metadata']
    raw, pin = reader.read_regular(Path(selected['profile_pin']['path']))
    if pin != selected['profile_pin']:
        raise ValueError('profile changed since saved summary')
    functions = [compact_function(row) for row in reader.profile_functions(raw)]
    production = [row for row in functions if '/src/data_sheets_schema/' in row['file']]
    observer = [row for row in functions if 'native_recorder_' in row['file']]
    yaml_rows = [row for row in functions if '/yaml/' in row['file']]
    schema_rows = [row for row in functions if '/linkml' in row['file'] or '/jsonschema/' in row['file']]
    wanted = {'_rebuild', '_schemas', '_capture_native_schema', '_schema_product',
              '_schema_with_root_bases', 'schema_data', 'capture_schema', 'captured_view',
              '_record_validator', 'check_record', '_base', '_recorded_run',
              'runtime_token', '_inline_checks', 'compute', 'apply', 'read_final',
              'load', 'safe_load', 'full_load', 'load_yaml', 'load_schema_wrap',
              '_derive', '_store', '_bounded_json', '_open', 'memo'}
    selected_functions = [row for row in functions if row['function'] in wanted
        and ('/src/data_sheets_schema/' in row['file'] or '/yaml/' in row['file'] or '/linkml' in row['file'])]
    events, jsonl = reader.observer_events(Path(recorder['directory']) / 'observer.jsonl')
    if jsonl['artifact'] != recorder['observer_jsonl']['artifact']:
        raise ValueError('observer JSONL changed since saved summary')
    counters = [row for row in events if row['event'] == 'counter_snapshot']
    stats = counters[-1].get('stats', {}) if counters else {}
    phase_definitions = {item['id']: item['phase'] for row in events if row['event'] == 'observer_start'
                         for item in row.get('targets', []) if item.get('phase')}
    completed = {row['target']: row for row in recorder.get('completed_phases', [])}
    active = {row['target']: row for row in metadata.get('active_phases', [])}
    phases = []
    for target, phase in phase_definitions.items():
        counts = stats.get(target)
        logged_calls = sum(row['event'] == 'phase_start' and row.get('target') == target for row in events)
        calls = max(counts.get('calls', 0) if counts else 0, logged_calls)
        returns = max(counts.get('returns', 0) if counts else 0, completed.get(target, {}).get('returns', 0))
        unwinds = max(counts.get('unwinds', 0) if counts else 0, completed.get(target, {}).get('unwinds', 0))
        state = ('not_reached' if calls == 0 else 'inflight' if calls > returns + unwinds
                 else 'completed')
        phases.append({'target': target, 'phase': phase, 'state': state,
            'calls': calls, 'returns': returns, 'unwinds': unwinds,
            'completed_cost': completed.get(target), 'active_checkpoint_cost': active.get(target),
            'latest_counters': counts.get('counters', {}) if counts else {},
            'active_at_selected_checkpoint': target in active,
            'counts_scope': 'maximum observed snapshot/logged-event counts; counter snapshot can predate final phase events'})
    checkpoints = [row for row in events if row['event'] == 'cpu_profile_checkpoint']
    checkpoint_cpu = max((row.get('checkpoint_thread_cpu_ns', 0) for row in checkpoints), default=0)
    checkpoint_wall = max((row.get('checkpoint_body_wall_ns', 0) for row in checkpoints), default=0)
    callbacks = counters[-1] if counters else {}
    timing = {'selected_checkpoint': metadata.get('checkpoint'),
        'selected_reason': metadata.get('reason'), 'selected_process_age_seconds': metadata.get('process_age_seconds'),
        'selected_rusage': metadata.get('rusage'),
        'latest_event_checkpoint': checkpoints[-1].get('checkpoint') if checkpoints else None,
        'latest_event_process_age_seconds': checkpoints[-1].get('process_age_seconds') if checkpoints else None,
        'latest_event_rusage': checkpoints[-1].get('rusage') if checkpoints else None,
        'checkpoint_body_thread_cpu_seconds': checkpoint_cpu / 1e9,
        'checkpoint_body_wall_seconds': checkpoint_wall / 1e9,
        'monitoring_callback_body_wall_seconds': callbacks.get('callback_body_ns', 0) / 1e9,
        'monitoring_callback_count': callbacks.get('callback_count'),
        'scope': 'checkpoint thread CPU is measured with thread_time; callback body metric is wall time; neither captures all instrumentation overhead'}
    return {'directory': recorder['directory'], 'status': recorder['status'],
        'profile_pin': pin, 'profile_metadata_pin': selected['metadata_pin'],
        'observer_jsonl': jsonl, 'observer_end_valid': recorder.get('observer_end_valid'),
        'selected_complete_final': selected['selected_complete_final'], 'timing': timing,
        'top_production_inclusive_cpu': by_cpu(production),
        'top_production_self_cpu': by_cpu(production, field='self_cpu_seconds'),
        'selected_schema_cache_readback_functions': by_cpu(selected_functions, limit=100),
        'top_pyyaml_functions': by_cpu(yaml_rows, limit=25),
        'top_external_schema_functions': by_cpu(schema_rows, limit=25),
        'observer_functions_for_attribution_audit': by_cpu(observer, limit=20),
        'observer_functions_with_production_or_yaml_callers': [
            {'function': row['function'], 'file': row['file'], 'reported_callers': [
                caller for caller in row['top_callers']
                if '/src/data_sheets_schema/' in caller['file'] or '/site-packages/yaml/' in caller['file']]}
            for row in observer if any('/src/data_sheets_schema/' in caller['file']
                or '/site-packages/yaml/' in caller['file'] for caller in row['top_callers'])],
        'phases': phases, 'latest_cache_counters': recorder.get('latest_cache_counters'),
        'initial_checkpoint_rusage': recorder.get('initial_checkpoint_rusage'),
        'recorder_entry_rusage': recorder.get('recorder_entry_rusage'),
        'warnings': recorder.get('warnings', []),
        'interpretation_limits': [
            'Rankings are observations, not an automated hotspot or causal conclusion.',
            'cProfile uses process_time: concurrent checkpoint-thread CPU can be attributed to overlapping frames; do not classify background observer functions as production hotspots.',
            'Observed production/PyYAML caller edges into observer checkpoint routines require independent source validation; the caller graph is not reliable causal evidence for this multithreaded profile.',
            'Compare checkpoint thread_time overhead separately; inclusive profiler and phase costs overlap and must not be summed.',
            'Partial getstats checkpoints can omit costs of active frames; active phase rusage remains process-wide.',
            'Saved function names/counts do not by themselves prove a cache hit, miss or repeated validation cause.',
            'Wall time is contended and provides no 180-second helper performance acceptance verdict.',
            'Parent-process final readback is outside recorder-only profiling.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    summary, summary_pin = reader.json_file(args.summary)
    _, script_pin = reader.read_regular(Path(__file__))
    _, helper_pin = reader.read_regular(HELPER)
    context = summary.get('trial_context', {})
    result = {'format': 'native_u0_cpu_cost_detail_v1', 'input_summary': summary_pin,
        'extractor': script_pin, 'reader_helper': helper_pin,
        'source_before_head': context.get('source_before_head'),
        'source_after_head': context.get('source_after_head'),
        'source_preservation_verified': context.get('source_preservation_verified'),
        'driver_status': context.get('driver_outcome', {}).get('status'),
        'worker_returncode': context.get('driver_outcome', {}).get('returncode'),
        'cleanup_verified': context.get('driver_outcome', {}).get('cleanup_verified'),
        'recorders': [extract(row) for row in summary.get('recorders', [])],
        'walltime_scope': 'contended_diagnostic_not_threshold_evidence',
        'causal_assessment': 'not_assessed'}
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    _, output_pin = reader.read_regular(args.out)
    compact = []
    for row in result['recorders']:
        compact.append({'recorder': Path(row['directory']).name, 'status': row['status'],
            'timing': row.get('timing'),
            'production_top10': [{'file': Path(item['file']).name, 'function': item['function'],
                'calls': item['ncalls'], 'self_cpu': item['self_cpu_seconds'],
                'inclusive_cpu': item['inclusive_cpu_seconds']}
                for item in row.get('top_production_inclusive_cpu', [])[:10]],
            'phases': [{'target': phase['target'], 'state': phase['state'], 'calls': phase['calls'],
                'completed_cost': phase['completed_cost'], 'active': phase['active_checkpoint_cost']}
                for phase in row.get('phases', []) if phase['state'] != 'not_reached']})
    print(json.dumps({'output': output_pin, 'driver_status': result['driver_status'],
                      'cleanup_verified': result['cleanup_verified'], 'recorders': compact}, sort_keys=True))


if __name__ == '__main__':
    main()
