#!/usr/bin/env python3
"""Read saved U0 causal-pair evidence, #4354/D92, 2026-11-06.

Inputs: one trial, or control/treatment trials, and their recorder observer parent.
Output: an exclusively created JSON analysis. No production imports, subprocesses,
reruns, network, edits to inputs, or acceptance/scientific/timing decisions.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import xml.etree.ElementTree as ET


_SPEC = importlib.util.spec_from_file_location(
    '_u0_saved_cpu_reader', Path(__file__).with_name('summarize_native_u0_cpu_20261106.py'))
reader = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(reader)
NODE = 'tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion'
CPU_FIELDS = ('thread_cpu_ns', 'process_cpu_ns', 'ru_utime', 'ru_stime')
LIMITATIONS = [
    'One diagnostic pair under contention is not a wall-time threshold or scientific acceptance test.',
    'Completed phase CPU is inclusive, includes observer overhead, and overlaps nested phases; never sum across targets.',
    'Owner-thread CPU excludes other threads; process CPU and getrusage include every recorder thread.',
    'Counter and document snapshots have separate cutoffs from individual phase-end events; active partial phases are separate.',
    'Document identity here is the native-schema member visit SHA/count multiset, not proof that all downstream outputs agree.',
    'Source closure attests loaded project modules and monitored project source bytes; external dependencies and earlier site/.pth execution remain outside that proof.',
    'Recorder-local monitoring does not observe the later parent-process read_final implementation; a passing exact test plus persisted bindings supplies separate readback evidence.',
    'No cProfile timing or caller graph is used. Generator starts are document parser starts, not generator resumptions.',
]


def nonnegative(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def relative(path, root):
    path, root = Path(path), Path(root)
    if not path.is_absolute() or '..' in path.parts or not root.is_absolute():
        raise ValueError('expected lexical absolute source/artifact path without parent traversal')
    return path.relative_to(root).as_posix()


def read_json(path, pins, errors, *, optional=False):
    try:
        value, pin = reader.json_file(path)
        pins[str(path)] = pin
        return value
    except FileNotFoundError as exc:
        if not optional:
            errors.append(reader.failure(path, exc))
    except Exception as exc:
        errors.append(reader.failure(path, exc))
    return None


def closure_verification(closure, root, source):
    """Validate saved closure evidence against the saved committed-byte inventory."""
    errors = []
    if not isinstance(closure, dict):
        return {'verified': False, 'errors': ['missing source closure'], 'evidence': closure}
    if (closure.get('root') != root
            or closure.get('package_root') != str(Path(root) / 'src/data_sheets_schema')
            or closure.get('ordinary_root_package') is not True
            or closure.get('project_finder_first') is not True
            or closure.get('namespace_pruned') is not False):
        errors.append('closure root/package/finder or no-pruning invariant differs')
    files = source.get('files', {})
    modules = closure.get('modules', [])
    if not isinstance(modules, list) or not modules:
        errors.append('closure has no loaded project modules')
        modules = []
    names = [row.get('name') for row in modules if isinstance(row, dict)]
    if (len(names) != len(modules) or len(names) != len(set(names))
            or 'data_sheets_schema' not in names
            or closure.get('project_module_count') != len(modules)):
        errors.append('closure project module roster differs')

    def pin_matches(pin, description):
        try:
            name = relative(pin.get('file') or pin['path'], root)
            expected = files[name]
            if (pin.get('sha256') != expected.get('sha256')
                    or pin.get('bytes') != expected.get('bytes')
                    or expected.get('committed_exact') is not True):
                raise ValueError('SHA/size/committed identity differs')
        except Exception as exc:
            errors.append(description + ': ' + str(exc))

    for row in modules:
        try:
            name = row['name']
            if name != 'data_sheets_schema' and not name.startswith('data_sheets_schema.'):
                raise ValueError('foreign module in project roster')
            expected_dir = Path(root) / 'src' / Path(*name.split('.'))
            namespaces = row.get('namespace')
            if namespaces is not None and namespaces != [str(expected_dir)]:
                raise ValueError('module namespace is widened or foreign')
            if row.get('namespace_only') is True:
                if namespaces != [str(expected_dir)] or row.get('file') is not None:
                    raise ValueError('invalid project namespace package')
            else:
                if row.get('file') != row.get('spec_origin'):
                    raise ValueError('module file/spec identity differs')
                actual = Path(row['file'])
                if actual not in (expected_dir.with_suffix('.py'), expected_dir / '__init__.py'):
                    raise ValueError('module path differs from import name')
                pin_matches(row, name)
        except Exception as exc:
            errors.append('module closure: ' + str(exc))
    for key in ('helper', 'package_bootstrap'):
        pin_matches(closure.get(key, {}), key)
    return {'verified': not errors, 'errors': errors, 'evidence': closure}


def phase_summary(rows):
    starts, ended, errors = {}, set(), []
    phases = defaultdict(lambda: {'logged_starts': 0, 'completed': 0, 'outcomes': {},
        'inclusive_rusage_totals': {key: 0 for key in CPU_FIELDS}, 'last_end_sequence': None,
        'last_end_elapsed_ns': None})
    counters = [row for row in rows if row['event'] == 'counter_snapshot']
    snapshots = [row for row in rows if row['event'] == 'thread_cpu_checkpoint']
    for row in rows:
        if row['event'] not in ('phase_start', 'phase_end'):
            continue
        key, target = row.get('call'), row.get('target')
        if type(key) is not int or not isinstance(target, str):
            errors.append('invalid phase call/target')
            continue
        bucket = phases[target]
        if row['event'] == 'phase_start':
            if key in starts:
                errors.append('duplicate phase call ' + str(key))
            starts[key] = row
            bucket['logged_starts'] += 1
            bucket['phase'] = row.get('phase')
            continue
        if key not in starts or key in ended or starts[key].get('target') != target:
            errors.append('missing/duplicate/mismatched phase end ' + str(key))
            continue
        ended.add(key)
        values = row.get('inclusive_rusage_delta', {})
        if not all(nonnegative(values.get(field)) for field in CPU_FIELDS):
            errors.append('invalid CPU delta for ' + target)
            continue
        if row.get('outcome') not in ('returns', 'unwinds'):
            errors.append('invalid phase outcome for ' + target)
            continue
        bucket['completed'] += 1
        kind = row['outcome']
        bucket['outcomes'][kind] = bucket['outcomes'].get(kind, 0) + 1
        for field in CPU_FIELDS:
            bucket['inclusive_rusage_totals'][field] += values[field]
        bucket['last_end_sequence'] = row['sequence']
        bucket['last_end_elapsed_ns'] = row.get('elapsed_ns')
    last_counter = counters[-1] if counters else None
    stats = (last_counter or {}).get('stats', {})
    for target, bucket in phases.items():
        bucket['logged_active_calls'] = [key for key, value in starts.items()
            if value['target'] == target and key not in ended]
        counted = stats.get(target, {})
        bucket['latest_counters'] = counted
        bucket['complete_detail_coverage'] = bool(
            counted.get('calls') == bucket['logged_starts']
            and counted.get('returns', 0) + counted.get('unwinds', 0) == bucket['completed']
            and bucket['completed'] == bucket['logged_starts']
            and not bucket['logged_active_calls'])
    return {'targets': dict(phases), 'errors': errors,
        'latest_counter_snapshot': last_counter,
        'latest_thread_cpu_checkpoint': snapshots[-1] if snapshots else None,
        'partial_active_phases': (snapshots[-1].get('active_phases', []) if snapshots else []),
        'phase_detail_note': 'Targets beyond the observer phase-detail cap cannot qualify for matched completed-phase totals.'}


def summarize_recorder(directory, root, source):
    rows, evidence = reader.observer_events(directory / 'observer.jsonl')
    starts = [row for row in rows if row['event'] == 'observer_start']
    ends = [row for row in rows if row['event'] == 'observer_end']
    errors = list(evidence['parse_errors'])
    if len(starts) != 1 or starts[0].get('root') != root:
        errors.append('recorder requires exactly one matching observer_start')
    if len(ends) > 1:
        errors.append('multiple observer_end events')
    start, end = (starts[0] if starts else {}), (ends[-1] if ends else {})
    invalid = [row for row in rows if row.get('valid') is False or row['event'] == 'observer_error']
    start_closure = closure_verification(start.get('source_closure'), root, source)
    end_closure = closure_verification(end.get('source_closure'), root, source)
    project_pins, external_pins = [], []
    for name, pin in start.get('source_pins', {}).items():
        try:
            rel = relative(name, root)
        except ValueError:
            external_pins.append({'path': name, **pin})
            if '/data_sheets_schema/' in name:
                errors.append('monitored project file outside diagnostic source root: ' + name)
            continue
        expected = source.get('files', {}).get(rel, {})
        project_pins.append({'path': name, **pin})
        if (pin.get('sha256') != expected.get('sha256')
                or pin.get('bytes') != expected.get('bytes')
                or expected.get('committed_exact') is not True):
            errors.append('monitored source differs from saved committed inventory: ' + rel)
    if not project_pins:
        errors.append('no monitored project source pins')
    phases = phase_summary(rows)
    errors.extend(phases['errors'])
    checkpoint = phases['latest_thread_cpu_checkpoint'] or {}
    checkpoint_paths = []
    for child in sorted(directory.iterdir()):
        if child.name == 'observer.jsonl' or not child.is_file():
            continue
        try:
            _, pin = reader.read_regular(child)
            checkpoint_paths.append(pin)
        except Exception as exc:
            errors.append(reader.failure(child, exc))
    prefix_valid = bool(not errors and not invalid and start_closure['verified']
        and (not ends or end.get('valid') is True and not end.get('changed_sources')
             and end_closure['verified']))
    return {'directory': str(directory), 'observer_jsonl': evidence,
        'observer_start': start, 'observer_end': end or None,
        'source_closure_start': start_closure, 'source_closure_end': end_closure,
        'observed_prefix_valid': prefix_valid,
        'complete_observer_valid': bool(prefix_valid and ends and end_closure['verified']),
        'invalid_events': invalid, 'errors': errors, 'phases': phases,
        'documents_at_checkpoint': checkpoint.get('documents', {}),
        'treatment_cache_at_checkpoint': checkpoint.get('treatment_cache'),
        'parser_inflight_at_checkpoint': checkpoint.get('parser_inflight'),
        'checkpoint_cutoff': {key: checkpoint.get(key) for key in ('sequence', 'elapsed_ns', 'checkpoint', 'reason')},
        'project_source_pins': project_pins, 'external_source_pins': external_pins,
        'other_artifact_pins': checkpoint_paths}


def summarize_host(path, owned_roots):
    """Stream large saved host evidence; never launch host commands."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    digest, rows, total_cpu, peak_cpu, peak_load = hashlib.sha256(), 0, 0.0, 0.0, 0.0
    competitors = defaultdict(lambda: {'samples': 0, 'peak_cpu_percent': 0.0})
    first = last = None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 512 * 1024 * 1024:
            raise ValueError('host evidence must be a nonempty regular file no larger than 512 MiB')
        with os.fdopen(os.dup(descriptor), 'rb') as stream:
            while True:
                raw = stream.readline(2 * 1024 * 1024 + 1)
                if not raw:
                    break
                if len(raw) > 2 * 1024 * 1024 or not raw.endswith(b'\n'):
                    raise ValueError('host JSONL line oversized or unterminated')
                digest.update(raw)
                row = reader.strict_json(raw)
                if (row.get('kind') != 'sample' or not nonnegative(row.get('cpu_percent'))
                        or type(row.get('logical_cpus')) is not int or row['logical_cpus'] <= 0
                        or not isinstance(row.get('load'), list) or not row['load']
                        or not nonnegative(row['load'][0])):
                    raise ValueError('malformed host sample')
                if last and (row['sequence'] <= last['sequence'] or row['monotonic'] <= last['monotonic']):
                    raise ValueError('host samples not strictly ordered')
                first, last = first or row, row
                rows += 1
                total_cpu += row['cpu_percent']
                peak_cpu = max(peak_cpu, row['cpu_percent'])
                peak_load = max(peak_load, row['load'][0] / row['logical_cpus'])
                processes, excluded = row.get('processes', []), set(owned_roots)
                changed = True
                while changed:
                    new = {p['pid'] for p in processes if p['ppid'] in excluded} - excluded
                    changed = bool(new)
                    excluded.update(new)
                for process in processes:
                    if process['pid'] not in excluded and process['cpu_percent'] >= 10:
                        key = str(process['pid']) + ' ' + process['name']
                        item = competitors[key]
                        item['samples'] += 1
                        item['peak_cpu_percent'] = max(item['peak_cpu_percent'], process['cpu_percent'])
        after, current = os.fstat(descriptor), path.lstat()
        keys = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if not stat.S_ISREG(current.st_mode) or any(
                getattr(before, key) != getattr(after, key) or getattr(after, key) != getattr(current, key)
                for key in keys):
            raise ValueError('host evidence changed while reading')
        return {'artifact': {'path': str(path), 'bytes': before.st_size, 'sha256': digest.hexdigest()},
            'samples': rows, 'mean_cpu_percent': total_cpu / rows, 'peak_cpu_percent': peak_cpu,
            'peak_load1_per_logical_cpu': peak_load, 'first_at': first.get('at'), 'last_at': last.get('at'),
            'excluded_owned_roots_and_visible_descendants': sorted(owned_roots),
            'competitors_at_least_10_percent': dict(sorted(competitors.items())),
            'scope': 'saved contended-host context; ps CPU is not interval attribution; no idle/timing verdict'}
    finally:
        os.close(descriptor)


def completion(trial, source, plan, outcome, pins):
    errors, missing = [], []
    result = {'verified_synthetic_completion': False, 'errors': errors, 'missing': missing,
        'progress': {}, 'scope': 'saved artifacts and exact passing test; no fresh execution or scientific acceptance'}
    xml = trial / 'pytest.xml'
    try:
        raw, pin = reader.read_regular(xml)
        pins[str(xml)] = pin
        if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
            raise ValueError('unexpected XML declarations')
        cases = ET.fromstring(raw).findall('.//testcase')
        expected = NODE.split('::')[1]
        junit_ok = bool(len(cases) == 1 and cases[0].get('name') == expected
            and cases[0].get('classname') == 'tests.test_native_shared_execution'
            and not list(cases[0]))
        result['exact_test_passed'] = junit_ok
    except Exception as exc:
        errors.append(reader.failure(xml, exc))
        junit_ok = False
    candidates = sorted((trial / 'cases').glob('**/native26/actual-result.json'))
    if len(candidates) != 1:
        missing.append('exactly one native26/actual-result.json (found %s)' % len(candidates))
        return result
    actual_path = candidates[0]
    case = actual_path.parent
    relative(case, trial)
    actual = read_json(actual_path, pins, errors) or {}
    result['progress']['actual_state'] = actual.get('state')
    result['progress']['runtime_gates_passed'] = actual.get('runtime_gates_passed')
    result['progress']['gates'] = actual.get('gates')
    result['case'] = str(case)
    final = read_json(case / 'native-evidence/final.json', pins, errors, optional=True)
    published = read_json(case / 'native-evidence/published.json', pins, errors, optional=True)
    runtime = read_json(case / 'authority/runtime-execution.json', pins, errors) or {}
    composition = read_json(case / 'authority/composition-execution.json', pins, errors) or {}
    destination = composition.get('policy', {}).get('post_final_recorder', {}).get('destination')
    result['progress']['recorder_destination'] = destination
    result['progress']['persisted_record_nonempty'] = False
    if destination:
        try:
            relative(destination, case)
            _, pin = reader.read_regular(Path(destination))
            pins[destination] = pin
            result['progress']['persisted_record_nonempty'] = True
            result['progress']['record_content_note'] = 'bytes pinned; no YAML/schema validation is re-executed'
        except FileNotFoundError:
            missing.append('recorder destination')
        except Exception as exc:
            errors.append(reader.failure(destination, exc))
    peer = case / 'ordinary-python-test-peer'
    peer_ok = False
    try:
        raw, pin = reader.read_regular(peer)
        pins[str(peer)] = pin
        prefix = ('#!' + plan['command'][0] + '\n').encode()
        fixture = source['files']['tests/fixtures/native_shared_execution/fake_cli.py']
        peer_ok = bool(raw.startswith(prefix)
            and reader.digest(raw[len(prefix):]) == fixture['sha256']
            and len(raw) - len(prefix) == fixture['bytes'] and fixture['committed_exact'] is True
            and runtime.get('deadline_seconds') == 900
            and runtime.get('executable', {}).get('path') == str(peer)
            and runtime['executable'].get('sha256') == pin['sha256']
            and runtime['executable'].get('version') == 'SYNTHETIC PYTHON SOFTWARE TEST')
    except Exception as exc:
        errors.append(reader.failure(peer, exc))
    result['synthetic_peer_verified'] = peer_ok
    bindings = bool(published)
    for field, suffix in [('final_sha256', 'native-evidence/final.json'),
            ('registration_sha256', 'native-attempt/registration.json'),
            ('started_sha256', 'native-attempt/started.json')]:
        try:
            _, pin = reader.read_regular(case / suffix)
            pins[str(case / suffix)] = pin
            bindings = bool(bindings and published.get(field) == pin['sha256'])
        except FileNotFoundError:
            missing.append(suffix)
            bindings = False
        except Exception as exc:
            errors.append(reader.failure(case / suffix, exc))
            bindings = False
    result['progress']['publication_bindings_verified'] = bindings
    result['progress']['final_equals_actual'] = final is not None and final == actual
    gates = actual.get('gates', {})
    gate_values = list(gates.values()) if isinstance(gates, dict) else gates if isinstance(gates, list) else []
    gate_ok = bool(gate_values and all(isinstance(row, dict)
        and row.get('checked') is True and row.get('passed') is True for row in gate_values))
    result['verified_synthetic_completion'] = bool(not errors and junit_ok and peer_ok
        and bindings and final == actual and result['progress']['persisted_record_nonempty']
        and gate_ok and actual.get('runtime_gates_passed') is True
        and actual.get('state') == 'completed_pending_independent_review'
        and actual.get('scientific_acceptance') == 'not_assessed'
        and outcome.get('status') == 'software_test_passed')
    result['readback_and_one_use_refusal'] = ('proved by the saved exact passing test and persisted result bindings'
        if result['verified_synthetic_completion'] else 'not established by this saved completion check')
    return result


def analyze_trial(trial, observer_parent):
    trial, observer_parent = Path(trial).absolute(), Path(observer_parent).absolute()
    pins, errors = {}, []
    docs = {name: read_json(trial / name, pins, errors) or {}
        for name in ('plan.json', 'outcome.json', 'source-before.json', 'source-after.json')}
    plan, outcome = docs['plan.json'], docs['outcome.json']
    before, after = docs['source-before.json'], docs['source-after.json']
    root = plan.get('cwd')
    command = plan.get('command', [])
    root_valid = bool(isinstance(root, str) and Path(root).is_absolute()
        and '..' not in Path(root).parts and command.count('--tree') == 1
        and command.index('--tree') + 1 < len(command)
        and command[command.index('--tree') + 1] == root and plan.get('node') == NODE)
    if not root_valid:
        errors.append('plan cwd/unique --tree/exact test node binding differs')
    source_ok = bool(before and before == after and before.get('pristine') is True
        and outcome.get('source_unchanged') is True)
    wrapper = trial.with_name(trial.name + '.wrapper')
    wrapper_plan = read_json(wrapper / 'plan.json', pins, errors) or {}
    wrapper_outcome = read_json(wrapper / 'outcome.json', pins, errors) or {}
    for name in ('network-self-check.json',):
        read_json(wrapper / name, pins, errors, optional=True)
    selected, unrelated = [], []
    if root_valid:
        for directory in sorted(observer_parent.glob('recorder-*')):
            try:
                if directory.is_symlink() or not directory.is_dir():
                    raise ValueError('recorder evidence must be a nonsymlink directory')
                rows, evidence = reader.observer_events(directory / 'observer.jsonl')
                starts = [row for row in rows if row['event'] == 'observer_start']
                if any(row.get('root') == root for row in starts):
                    selected.append(directory)
                else:
                    unrelated.append({'directory': str(directory), 'start_roots': [r.get('root') for r in starts],
                        'parse_errors': evidence['parse_errors']})
            except Exception as exc:
                errors.append(reader.failure(directory, exc))
    recorder = None
    if len(selected) != 1:
        errors.append('expected exactly one recorder with the diagnostic root; found ' + str(len(selected)))
    else:
        recorder = summarize_recorder(selected[0], root, before)
    owned = {value for value in (outcome.get('child_pid'), wrapper_plan.get('driver_pid'),
        wrapper_plan.get('observer_pid'), plan.get('host_observation', {}).get('observer_pid'))
        if type(value) is int and value > 0}
    host = None
    try:
        host = summarize_host(trial / 'host.jsonl', owned)
        pins[str(trial / 'host.jsonl')] = host['artifact']
    except Exception as exc:
        errors.append(reader.failure(trial / 'host.jsonl', exc))
    progress = completion(trial, before, plan, outcome, pins)
    prefix_valid = bool(not errors and root_valid and source_ok and recorder
        and recorder['observed_prefix_valid'])
    return {'trial': str(trial), 'source_root': root, 'source_head': before.get('head'),
        'source_binding_verified': root_valid, 'source_preservation_verified': source_ok,
        'observed_measurement_prefix_valid': prefix_valid,
        'errors': errors, 'artifact_pins': pins, 'recorder': recorder,
        'other_recorder_directories': unrelated, 'driver_outcome': outcome,
        'wrapper_outcome': wrapper_outcome, 'host_context': host,
        'completion': progress, 'same_run_readback_verified': progress['verified_synthetic_completion'],
        'cleanup_verified': outcome.get('cleanup_verified'),
        'wall_time_verdict': 'not_assessed', 'scientific_acceptance': 'not_assessed'}


def member_work(recorder):
    document = (recorder or {}).get('documents_at_checkpoint', {}).get('native_schema_member_visits')
    if not isinstance(document, dict):
        return False, document
    counts = document.get('hash_counts', {})
    valid = bool(document.get('hash_coverage_complete') is True
        and document.get('non_text_inputs') == 0 and counts
        and all(isinstance(key, str) and len(key) == 64 and type(value) is int and value > 0
            for key, value in counts.items())
        and document.get('calls') == sum(counts.values()) and nonnegative(document.get('input_bytes')))
    return valid, document


def compare(control, treatment):
    c_rec, t_rec = control.get('recorder'), treatment.get('recorder')
    c_ok, c_work = member_work(c_rec)
    t_ok, t_work = member_work(t_rec)
    same_work = bool(c_ok and t_ok and c_work == t_work)
    def instrumentation(recorder):
        start = (recorder or {}).get('observer_start', {})
        closure = start.get('source_closure', {})
        shared = [start.get('helper', {}), closure.get('helper', {}), closure.get('package_bootstrap', {})]
        if not all(isinstance(row.get('sha256'), str) and len(row['sha256']) == 64
                   and type(row.get('bytes')) is int and row['bytes'] > 0 for row in shared):
            return None
        python = start.get('python', {})
        if not all(isinstance(python.get(key), str) and python[key] for key in ('executable', 'version')):
            return None
        return {'helpers': [(row['sha256'], row['bytes']) for row in shared],
            'python': {key: python[key] for key in ('executable', 'version')},
            'external_monitored_sources': sorted((row.get('path'), row.get('sha256'), row.get('bytes'))
                for row in (recorder or {}).get('external_source_pins', []))}
    c_instrumentation, t_instrumentation = instrumentation(c_rec), instrumentation(t_rec)
    same_instrumentation = bool(c_instrumentation is not None and c_instrumentation == t_instrumentation)
    source_distinct = bool(control.get('source_root') != treatment.get('source_root')
        and control.get('source_head') != treatment.get('source_head'))
    common_valid = bool(control['observed_measurement_prefix_valid']
        and treatment['observed_measurement_prefix_valid'] and same_work and source_distinct
        and same_instrumentation)
    compared, rejected = {}, {}
    c_targets = (c_rec or {}).get('phases', {}).get('targets', {})
    t_targets = (t_rec or {}).get('phases', {}).get('targets', {})
    for target in sorted(c_targets.keys() | t_targets.keys()):
        a, b = c_targets.get(target, {}), t_targets.get(target, {})
        reasons = []
        if not common_valid:
            reasons.append('valid distinct arm prefixes, identical common instrumentation pins and complete schema-member work required')
        if not a.get('complete_detail_coverage') or not b.get('complete_detail_coverage'):
            reasons.append('phase detail/counter coverage incomplete or phase remains active')
        if not a.get('completed') or a.get('completed') != b.get('completed') or a.get('outcomes') != b.get('outcomes'):
            reasons.append('completed phase counts/outcomes differ')
        if reasons:
            rejected[target] = reasons
            continue
        metrics = {}
        for field in CPU_FIELDS:
            c, t = a['inclusive_rusage_totals'][field], b['inclusive_rusage_totals'][field]
            metrics[field] = {'control': c, 'treatment': t, 'treatment_minus_control': t - c,
                'treatment_over_control': t / c if c else None}
        compared[target] = {'completed_calls_per_arm': a['completed'], 'outcomes': a['outcomes'],
            'inclusive_cpu_comparison': metrics,
            'scope': 'matched completed observations; source IDs and later outputs may differ; not an automatic causal or timing verdict'}
    return {'matching_native_schema_member_work': same_work,
        'matching_common_instrumentation_and_external_monitored_pins': same_instrumentation,
        'control_member_work': c_work, 'treatment_member_work': t_work,
        'distinct_source_roots_and_heads': source_distinct,
        'matched_completed_phase_observations': compared, 'excluded_phase_comparisons': rejected,
        'both_synthetic_completions_verified': bool(control['same_run_readback_verified']
            and treatment['same_run_readback_verified']),
        'causal_verdict': 'not_automatically_assessed', 'wall_time_verdict': 'not_assessed'}


def write_result(path, result):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', type=Path)
    parser.add_argument('--control-trial', type=Path)
    parser.add_argument('--treatment-trial', type=Path)
    parser.add_argument('--observer-parent', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error('--out already exists; evidence is never overwritten')
    if bool(args.trial) == bool(args.control_trial or args.treatment_trial):
        parser.error('choose --trial or both --control-trial and --treatment-trial')
    if not args.trial and not (args.control_trial and args.treatment_trial):
        parser.error('both pair trials are required')
    result = {'format': 'native_u0_causal_pair_saved_analysis_v1', 'limitations': LIMITATIONS,
        'analyzer_pin': reader.read_regular(Path(__file__))[1],
        'reader_pin': reader.read_regular(Path(reader.__file__))[1]}
    if args.trial:
        result['single_arm'] = analyze_trial(args.trial, args.observer_parent)
    else:
        control = analyze_trial(args.control_trial, args.observer_parent)
        treatment = analyze_trial(args.treatment_trial, args.observer_parent)
        result.update(control=control, treatment=treatment, comparison=compare(control, treatment))
    write_result(args.out, result)
    print(json.dumps({'output': str(args.out), 'sha256': reader.read_regular(args.out)[1]['sha256'],
        'mode': 'single_arm' if args.trial else 'pair', 'wall_time_verdict': 'not_assessed'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
