#!/usr/bin/env python3
"""Summarize saved U0 CPU diagnostics for #4354, 2026-11-06.

Inputs: an existing driver trial and recorder profile parent (or one profile
directory). Output: one exclusively created JSON summary. No production imports,
tests, subprocesses, network, source edits or causal/hotspot classification.
Only trusted locally generated pstats marshal artifacts are accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import marshal
import math
import os
from pathlib import Path
import stat


MAX_BYTES = 64 * 1024 * 1024
MATCHES = ('provenance', 'record_schema', 'check_record', 'schema', 'catalog',
           'read_final', 'readback', '_recorded_run', 'backfill', 'typed_audit',
           'cache', 'memo', '_base', '_load', 'native_shared_capture')
CPU_FIELDS = ('ru_utime', 'ru_stime', 'process_cpu_ns', 'wall_ns')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_regular(path):
    """Read one bounded non-symlink regular file, verifying stable identity."""
    path = Path(path).absolute()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_BYTES:
            raise ValueError('expected a nonempty regular file of at most 64 MiB')
        chunks, remaining = [], before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise ValueError('file shortened during read')
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
        current = path.lstat()
        keys = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(before, key) != getattr(after, key) for key in keys)
                or not stat.S_ISREG(current.st_mode)
                or any(getattr(after, key) != getattr(current, key) for key in keys)):
            raise ValueError('file changed during read')
        raw = b''.join(chunks)
        return raw, {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}
    finally:
        os.close(descriptor)


def strict_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('duplicate JSON key')
            value[key] = item
        return value
    def invalid(value):
        raise ValueError('nonfinite JSON number: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def json_file(path):
    raw, pin = read_regular(path)
    value = strict_json(raw)
    if not isinstance(value, dict):
        raise ValueError('expected JSON object')
    return value, pin


def failure(path, exc):
    return {'path': str(path), 'error': type(exc).__name__ + ': ' + str(exc)}


def trial_context(trial):
    documents, pins, errors = {}, {}, []
    for name in ('outcome.json', 'source-before.json', 'source-after.json', 'plan.json'):
        try:
            documents[name], pins[name] = json_file(trial / name)
        except Exception as exc:
            errors.append(failure(trial / name, exc))
    before, after = documents.get('source-before.json'), documents.get('source-after.json')
    outcome = documents.get('outcome.json', {})
    result = {'trial': str(trial), 'artifact_pins': pins,
        'missing_or_invalid_trial_context': errors,
        'source_before_head': before.get('head') if before else None,
        'source_after_head': after.get('head') if after else None,
        'source_documents_equal': before == after if before is not None and after is not None else None,
        'driver_source_unchanged': outcome.get('source_unchanged'),
        'source_preservation_verified': bool(before is not None and after is not None
            and before == after and outcome.get('source_unchanged') is True),
        'driver_outcome': outcome, 'tooling_plan': documents.get('plan.json')}
    wrapper_plan = trial.with_name(trial.name + '.wrapper') / 'plan.json'
    if wrapper_plan.exists():
        try:
            result['wrapper_plan'], result['wrapper_plan_pin'] = json_file(wrapper_plan)
        except Exception as exc:
            result['missing_or_invalid_trial_context'].append(failure(wrapper_plan, exc))
    return result


def observer_events(path):
    raw, pin = read_regular(path)
    events, errors = [], []
    lines = raw.splitlines(keepends=True)
    bad_last_line = False
    previous = 0
    for index, line in enumerate(lines, 1):
        try:
            if not line.endswith(b'\n'):
                raise ValueError('unterminated last JSONL line')
            row = strict_json(line)
            if not isinstance(row, dict) or not isinstance(row.get('event'), str):
                raise ValueError('malformed observer event')
            sequence = row.get('sequence')
            if type(sequence) is not int or sequence != previous + 1:
                raise ValueError('observer event sequence is not contiguous')
            previous = sequence
            events.append(row)
        except Exception as exc:
            errors.append({'line': index, 'error': type(exc).__name__ + ': ' + str(exc)})
            if index == len(lines):
                bad_last_line = True
    return events, {'artifact': pin, 'events_read': len(events),
                    'bad_last_line': bad_last_line, 'parse_errors': errors}


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def function_key(key):
    if (not isinstance(key, tuple) or len(key) != 3 or not isinstance(key[0], str)
            or type(key[1]) is not int or not isinstance(key[2], str)):
        raise ValueError('malformed pstats function key')
    return {'file': key[0], 'line': key[1], 'function': key[2]}


def profile_functions(raw):
    # Trusted local pstats format only; marshal is never used on remote input.
    mapping = marshal.loads(raw)
    if not isinstance(mapping, dict):
        raise ValueError('pstats marshal must contain a dictionary')
    result = []
    for key, value in mapping.items():
        identity = function_key(key)
        if (not isinstance(value, tuple) or len(value) != 5
                or any(type(value[i]) is not int or value[i] < 0 for i in (0, 1))
                or not numeric(value[2]) or not numeric(value[3]) or not isinstance(value[4], dict)):
            raise ValueError('malformed pstats counts, CPU values or caller map')
        callers = []
        for caller, costs in value[4].items():
            if (not isinstance(costs, tuple) or len(costs) != 4
                    or any(type(costs[i]) is not int or costs[i] < 0 for i in (0, 1))
                    or not numeric(costs[2]) or not numeric(costs[3])):
                raise ValueError('malformed cProfile caller values')
            callers.append({**function_key(caller), 'ncalls': costs[0],
                'primitive_calls': costs[1], 'self_cpu_seconds': costs[2],
                'inclusive_cpu_seconds': costs[3]})
        result.append({**identity, 'primitive_calls': value[0], 'ncalls': value[1],
            'self_cpu_seconds': value[2], 'inclusive_cpu_seconds': value[3],
            'top_callers': sorted(callers, key=lambda row: row['inclusive_cpu_seconds'], reverse=True)[:10]})
    return result


def select_profile(directory, complete):
    candidates, rejected = [], []
    for metadata_path in sorted(directory.glob('*.prof.json')):
        try:
            metadata, metadata_pin = json_file(metadata_path)
            artifact = metadata['profile']
            profile_path = metadata_path.with_suffix('')
            if (Path(artifact['path']).absolute() != profile_path.absolute()
                    or type(metadata.get('checkpoint')) is not int or metadata['checkpoint'] < 1
                    or metadata.get('profile_timer') != 'time.process_time'):
                raise ValueError('profile metadata identity, checkpoint or CPU timer differs')
            raw, pin = read_regular(profile_path)
            if pin['sha256'] != artifact['sha256'] or pin['bytes'] != artifact['bytes']:
                raise ValueError('profile SHA-256/size differs from metadata')
            # Validate every candidate before choosing the freshest valid pair.
            functions = profile_functions(raw)
            final = complete and metadata.get('reason') == 'final' and profile_path.name == 'profile-final.prof'
            candidates.append((final, metadata['checkpoint'], metadata, metadata_pin, pin, functions))
        except Exception as exc:
            rejected.append(failure(metadata_path, exc))
    if not candidates:
        return None, rejected
    _, _, metadata, metadata_pin, pin, functions = max(candidates, key=lambda item: (item[0], item[1]))
    inclusive = sorted(functions, key=lambda row: row['inclusive_cpu_seconds'], reverse=True)
    own = sorted(functions, key=lambda row: row['self_cpu_seconds'], reverse=True)
    matched = [row for row in inclusive if any(term in (row['file'] + ':' + row['function']).lower() for term in MATCHES)]
    return {'metadata': metadata, 'metadata_pin': metadata_pin, 'profile_pin': pin,
        'function_count': len(functions), 'top40_inclusive_cpu': inclusive[:40],
        'top40_self_cpu': own[:40], 'record_schema_catalog_readback_cache_functions': matched,
        'selected_complete_final': bool(complete and metadata.get('reason') == 'final'
                                       and Path(pin['path']).name == 'profile-final.prof')}, rejected


def summarize_recorder(directory):
    result = {'directory': str(directory), 'status': 'incomplete', 'warnings': []}
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('recorder evidence must be a regular directory')
    rows, evidence = observer_events(directory / 'observer.jsonl')
    result['observer_jsonl'] = evidence
    ended = [row for row in rows if row['event'] == 'observer_end']
    complete = bool(ended and ended[-1].get('valid') is True and not evidence['parse_errors'])
    result['observer_end_valid'] = complete
    result['observer_end'] = ended[-1] if ended else None
    starts = [row for row in rows if row['event'] in ('observer_start', 'cpu_profile_start')]
    result['startup_evidence'] = starts
    phases = {}
    for row in rows:
        if row['event'] != 'phase_end':
            continue
        key = row['target']
        group = phases.setdefault(key, {'target': key, 'phase': row['phase'], 'completed_calls': 0,
            'returns': 0, 'unwinds': 0, 'inclusive_process_rusage_delta_sum': {name: 0 for name in CPU_FIELDS},
            'inclusive_thread_cpu_ns_sum': 0})
        group['completed_calls'] += 1
        if row.get('outcome') in ('returns', 'unwinds'):
            group[row['outcome']] += 1
        for name in CPU_FIELDS:
            group['inclusive_process_rusage_delta_sum'][name] += row.get('inclusive_process_rusage_delta', {}).get(name, 0)
        group['inclusive_thread_cpu_ns_sum'] += row.get('inclusive_thread_cpu_ns', 0)
    result['completed_phases'] = sorted(phases.values(), key=lambda row: row['inclusive_process_rusage_delta_sum']['process_cpu_ns'], reverse=True)
    snapshots = [row for row in rows if row['event'] == 'counter_snapshot']
    result['latest_cache_counters'] = ({target: value for target, value in snapshots[-1].get('stats', {}).items()
        if value.get('counters')} if snapshots else {})
    checkpoints = [row for row in rows if row['event'] == 'cpu_profile_checkpoint']
    result['latest_checkpoint_event'] = checkpoints[-1] if checkpoints else None
    result['initial_checkpoint_rusage'] = next((row.get('rusage') for row in checkpoints if row.get('reason') == 'initial'), None)
    entry = next((row for row in rows if row['event'] == 'phase_start' and row.get('target') == 'cli.provenance:record'), None)
    result['recorder_entry_rusage'] = entry.get('process_rusage_enter') if entry else None
    result['startup_cpu_scope'] = 'cumulative process CPU at initial checkpoint and recorder entry; includes observer/import costs, not exclusively production startup'
    result['selected_profile'], rejected = select_profile(directory, complete)
    result['rejected_profile_pairs'] = rejected
    result['unfinished_phases'] = (result['selected_profile']['metadata'].get('active_phases', [])
        if result['selected_profile'] else checkpoints[-1].get('active_phases', []) if checkpoints else [])
    if not complete:
        result['warnings'].append('no clean valid observer_end; retain as partial or invalid diagnostic evidence')
    if evidence['bad_last_line']:
        result['warnings'].append('last observer JSONL line is malformed or incomplete')
    if not result['selected_profile']:
        result['warnings'].append('no valid bounded SHA/size-matching CPU profile pair')
    if rejected:
        result['warnings'].append('one or more profile pairs were rejected, including possible interrupted rolling replacement')
    if complete and result['selected_profile'] and result['selected_profile']['selected_complete_final']:
        result['status'] = 'complete_diagnostic_evidence'
    result['coverage_limits'] = [
        'CPU clock includes all process threads; cProfile observes the recorder thread',
        'active frames may be incomplete in partial pstats snapshots',
        'phase deltas overlap and must not be summed across nested targets',
        'observer, profiler and checkpoint overhead are included and not subtracted',
        'final parent-process native read_final is outside recorder-only instrumentation',
        'wall durations are contended diagnostics, never 180-second timing acceptance evidence']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', type=Path, required=True)
    parser.add_argument('--profile-parent', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    trial, parent = args.trial.absolute(), args.profile_parent.absolute()
    result = {'format': 'native_u0_saved_cpu_summary_v1', 'trial_context': trial_context(trial),
        'profile_parent': str(parent), 'recorders': [], 'discovery_errors': [],
        'walltime_scope': 'contended_diagnostic_not_threshold_evidence',
        'causal_assessment': 'not_assessed; this reader ranks saved measurements only'}
    try:
        directories = ([parent] if (parent / 'observer.jsonl').exists()
            else sorted(path for path in parent.iterdir() if path.name.startswith('recorder-')))
    except Exception as exc:
        directories = []
        result['discovery_errors'].append(failure(parent, exc))
    for directory in directories:
        try:
            result['recorders'].append(summarize_recorder(directory))
        except Exception as exc:
            result['recorders'].append({'directory': str(directory), 'status': 'unreadable',
                                        'error': failure(directory, exc)})
    result['recorder_count'] = len(directories)
    result['recorder_phase_status'] = 'not_reached' if not directories else 'saved_evidence_present'
    if not directories:
        result['warnings'] = ['zero recorder directories; no recorder profiling success is established']
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    summary_raw, summary_pin = read_regular(args.out)
    saved = strict_json(summary_raw)
    compact = []
    for recorder in saved['recorders']:
        selected = recorder.get('selected_profile') or {}
        compact.append({'recorder': Path(recorder['directory']).name, 'status': recorder['status'],
            'top10_cpu': [{key: row[key] for key in ('function', 'ncalls', 'primitive_calls', 'inclusive_cpu_seconds', 'self_cpu_seconds')}
                for row in selected.get('top40_inclusive_cpu', [])[:10]],
            'phases': [{'target': row['target'], 'calls': row['completed_calls'],
                        'cpu_seconds': row['inclusive_process_rusage_delta_sum']['process_cpu_ns'] / 1e9}
                for row in recorder.get('completed_phases', [])]})
    print(json.dumps({'summary': summary_pin, 'recorder_phase_status': saved['recorder_phase_status'],
                      'recorders': compact}, sort_keys=True))


if __name__ == '__main__':
    main()
