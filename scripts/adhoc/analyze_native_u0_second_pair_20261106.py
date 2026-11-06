#!/usr/bin/env python3
"""Read saved U0 second-pair evidence, D92 next step 2, 2026-11-06.

Inputs: two frozen diagnostic trials, observer directory, source manifest, and
optional historical analysis. Output: exclusive JSON. No production imports,
processes, reruns, network, or alterations to the original equal-work gate.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location('_u0_second_saved_base',
    Path(__file__).with_name('analyze_native_u0_causal_pair_20261106.py'))
base = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(base)
reader = base.reader
FIRST_TREATMENT = '2747e86c3f0521c1ef5c455d9be82428e4ca5be7'
CHANGES = frozenset(('src/data_sheets_schema/native_catalog_reuse.py',
    'src/data_sheets_schema/native_shared_receipts.py',
    'src/data_sheets_schema/native_catalog_initialization.py'))
COMMON = ('scripts/adhoc/native_recorder_observer_20261026.py',
    'scripts/adhoc/native_recorder_thread_cpu_20261106.py',
    'scripts/adhoc/native_recorder_second_cpu_20261106.py',
    'scripts/adhoc/native_recorder_second_cpu_20261106.config.json',
    'scripts/adhoc/native_u0_source_closure_20261106.py',
    'src/data_sheets_schema/__init__.py', 'src/data_sheets_schema/cli/__init__.py')
TESTS = ('tests/test_native_shared_execution.py',
    'tests/fixtures/native_shared_execution/fake_cli.py')
TOP = frozenset(('cli.provenance:record', 'cli.provenance:_inline_checks',
    'backfill_checks:compute', 'backfill_checks:apply',
    'native_shared_capture:live_provenance_block', 'native_shared_capture:_recorded_run',
    'receipts:block_for', 'provenance:build_record', 'provenance:ProvenanceRecord.write',
    'provenance:check_record'))
LIMITS = {'helper_seconds': 180, 'attempt_seconds': 900}
LIMITATIONS = [*base.LIMITATIONS,
    'The unchanged original global equal-work comparison is retained separately; its failures are never relabeled as passes.',
    'Top-level comparisons pair completed returning calls by target and ordinal under the same pinned fixture and inputs; internal reconstruction counts may differ by design.',
    'Identical published full/core bytes establish those outputs only, not full record equivalence or scientific acceptance.',
    'Historical first-control observations used different instrumentation and include censoring: no cumulative causal speedup, threshold margin, or quiet-host acceptance is inferred.',
]


def signature(pin):
    if (not isinstance(pin, dict) or type(pin.get('bytes')) is not int or pin['bytes'] < 0
            or not isinstance(pin.get('sha256'), str) or len(pin['sha256']) != 64):
        raise ValueError('malformed byte pin')
    return pin['sha256'], pin['bytes']


def saved_json(path, pins):
    value, pin = reader.json_file(path)
    pins[str(path)] = pin
    return value


def source_contract(manifest, arms, inventories):
    """Bind saved manifests to saved complete inventories, without Git operations."""
    errors = []
    try:
        if (manifest.get('format') != 'native_u0_second_pair_sources_v1'
                or manifest.get('first_treatment') != FIRST_TREATMENT
                or manifest.get('limits') != LIMITS
                or manifest.get('common_instrumentation_byte_identical') is not True):
            raise ValueError('source-manifest version/base/limits/common declaration differs')
        for label, arm, inventory in zip(('control', 'treatment'), arms, inventories):
            declared = manifest[label]
            if (declared['head'] != arm['source_head'] or declared['worktree'] != arm['source_root']
                    or inventory['head'] != declared['head'] or inventory.get('pristine') is not True):
                raise ValueError(label + ' source head/root binding differs')
            for name, pin in declared['files'].items():
                actual = inventory['files'][name]
                if signature(actual) != signature(pin) or actual.get('committed_exact') is not True:
                    raise ValueError(label + ' manifest file differs: ' + name)
        if manifest['treatment']['parent'] != manifest['control']['head']:
            raise ValueError('second treatment is not directly based on control')
        if manifest['control']['parent'] != FIRST_TREATMENT:
            raise ValueError('second control is not directly based on first treatment')
        left, right = (row['files'] for row in inventories)
        changed = {name for name in left.keys() | right.keys()
            if name not in left or name not in right or signature(left[name]) != signature(right[name])}
        if changed != CHANGES or set(manifest['treatment']['changed_paths']) != CHANGES:
            raise ValueError('complete source-inventory difference is not the exact T2 roster')
        treatment = manifest['treatment_manifest']
        if (set(treatment['changed_paths']) != CHANGES
                or treatment['control_head'] != manifest['control']['head']):
            raise ValueError('treatment change manifest differs')
        for row in treatment['files']:
            name = row['path']
            if name not in CHANGES or row['after_sha256'] != right[name]['sha256']:
                raise ValueError('treatment after-image differs')
            before = left.get(name)
            if row['before_sha256'] != (before['sha256'] if before else None):
                raise ValueError('treatment before-image differs')
        if {row['path'] for row in treatment['files']} != CHANGES:
            raise ValueError('treatment file pin roster differs')
        for name in (*COMMON, *TESTS):
            if (signature(left[name]) != signature(right[name])
                    or left[name].get('committed_exact') is not True
                    or right[name].get('committed_exact') is not True):
                raise ValueError('common instrumentation/test differs: ' + name)
    except Exception as exc:
        errors.append(str(exc))
    return {'verified': not errors, 'errors': errors,
        'required_treatment_paths': sorted(CHANGES), 'common_paths': list(COMMON),
        'test_paths': list(TESTS), 'limits': LIMITS}


def read_rows(arm):
    recorder = arm.get('recorder') or {}
    evidence = recorder['observer_jsonl']
    rows, current = reader.observer_events(Path(evidence['artifact']['path']))
    if signature(current['artifact']) != signature(evidence['artifact']) or current['parse_errors']:
        raise ValueError('observer changed or cannot be parsed')
    return rows


def completed_calls(rows):
    starts, ends, ordinals, completed, partial = {}, {}, Counter(), {}, []
    for row in rows:
        if row['event'] == 'phase_start':
            call, target = row['call'], row['target']
            if call in starts:
                raise ValueError('duplicate phase start')
            ordinals[target] += 1
            starts[call] = (row, ordinals[target])
        elif row['event'] == 'phase_end':
            if row['call'] in ends:
                raise ValueError('duplicate phase end')
            ends[row['call']] = row
    for call, (start, ordinal) in starts.items():
        target = start['target']
        if target not in TOP:
            continue
        row = {'target': target, 'ordinal': ordinal, 'call': call,
            'start_sequence': start['sequence'], 'start_elapsed_ns': start.get('elapsed_ns')}
        end = ends.get(call)
        if end is None:
            row['state'] = 'censored_no_phase_end'
            partial.append(row)
            continue
        if (end['target'] != target or end['sequence'] <= start['sequence']
                or end.get('outcome') not in ('returns', 'unwinds')
                or not all(base.nonnegative(end.get('inclusive_rusage_delta', {}).get(key))
                           for key in base.CPU_FIELDS)):
            raise ValueError('invalid phase endpoint or CPU')
        row.update(state='completed', outcome=end['outcome'], end_sequence=end['sequence'],
            end_elapsed_ns=end.get('elapsed_ns'), inclusive_rusage_delta=end['inclusive_rusage_delta'])
        completed[(target, ordinal)] = row
    return completed, partial


def top_comparison(arms, rows, common_valid):
    completed, partial = zip(*(completed_calls(value) for value in rows))
    matched, excluded = [], []
    for key in sorted(completed[0].keys() | completed[1].keys()):
        a, b = (value.get(key) for value in completed)
        if not common_valid or not a or not b or a['outcome'] != 'returns' or b['outcome'] != 'returns':
            excluded.append({'target': key[0], 'ordinal': key[1], 'control': a, 'treatment': b,
                'reason': 'common validity/pins/inputs or two completed returning endpoints missing'})
            continue
        metrics = {}
        for field in base.CPU_FIELDS:
            x, y = a['inclusive_rusage_delta'][field], b['inclusive_rusage_delta'][field]
            metrics[field] = {'control': x, 'treatment': y, 'treatment_minus_control': y-x,
                'treatment_over_control': y/x if x else None}
        matched.append({'target': key[0], 'ordinal': key[1], 'control': a, 'treatment': b,
            'inclusive_cpu_comparison': metrics})
    return {'scope': 'completed top-level calls under identical pinned fixture/inputs; internal call-count equality is not assumed',
        'common_gate_passed': common_valid, 'matched_completed_calls': matched,
        'excluded_calls': excluded, 'control_censored_calls': partial[0], 'treatment_censored_calls': partial[1],
        'causal_verdict': 'not_automatically_assessed', 'quiet_wall_time_verdict': 'not_assessed'}


def enrich(arm):
    pins, errors = {}, []
    result = {'errors': errors, 'artifact_pins': pins, 'fixture_inputs': {}, 'published_outputs': {}}
    try:
        trial = Path(arm['trial'])
        plan = saved_json(trial / 'plan.json', pins)
        source = saved_json(trial / 'source-before.json', pins)
        after = saved_json(trial / 'source-after.json', pins)
        if source != after:
            raise ValueError('source inventory changed')
        result['inventory'] = source
        if plan.get('node') != base.NODE:
            raise ValueError('test node differs')
        outcome = arm['wrapper_outcome']
        result['limits_verified'] = (outcome.get('helper_limit_seconds') == 180
            and outcome.get('attempt_limit_seconds') == 900)
        result['cleanup_verified'] = bool(arm.get('cleanup_verified') is True
            and outcome.get('driver_cleanup_completed') is True
            and outcome.get('observer_cleanup_completed') is True and outcome.get('lock_released') is True)
        if not result['limits_verified'] or not result['cleanup_verified']:
            raise ValueError('180/900 limits or terminal cleanup/lock proof missing')
        if arm['completion'].get('errors'):
            raise ValueError('saved completion artifacts contain read/identity errors')
        case = Path(arm['completion']['case'])
        base.relative(case, trial)
        composition = saved_json(case / 'authority/composition-execution.json', pins)
        runtime = saved_json(case / 'authority/runtime-execution.json', pins)
        if runtime.get('deadline_seconds') != 900:
            raise ValueError('runtime attempt limit differs')
        spec = composition['render_spec']
        if spec.get('profile') != 'neutral' or spec.get('native_shared_generation_version') != 1:
            raise ValueError('fixture profile/shared generation differs')
        result['fixture_contract'] = {key: spec.get(key) for key in
            ('profile', 'condition', 'arm', 'render_version', 'native_shared_generation_version')}
        final_path = case / 'native-evidence/final.json'
        final = saved_json(final_path, pins) if final_path.exists() else None
        if final is None:
            raise ValueError('final capture missing; fixture input identity cannot be verified')
        # Root normalization is restricted to the literal fixture manifest. Raw
        # pins remain visible; YAML is not parsed or production-validated here.
        for field in ('bundle', 'manifest', 'chunk_manifest'):
            path = Path(spec[field]); base.relative(path, case)
            raw, pin = reader.read_regular(path); pins[str(path)] = pin
            normalized = raw.replace(str(case).encode(), b'<FIXTURE_CASE>') if field == 'manifest' else raw
            result['fixture_inputs'][field] = {'raw_pin': pin,
                'comparison_sha256': reader.digest(normalized), 'comparison_bytes': len(normalized),
                'normalization': 'literal case prefix only' if field == 'manifest' else 'none'}
            if final is not None:
                captured = final.get('captured_files', {}).get(str(path))
                if captured is None or signature(captured) != signature(pin):
                    raise ValueError('final captured fixture input differs: ' + field)
        for role in ('full', 'core'):
            path = Path(spec['agentic_artifact_paths'][role]); base.relative(path, case)
            if not path.exists():
                if str(path) in (final or {}).get('captured_files', {}):
                    raise ValueError('captured final output is missing: ' + role)
                result['published_outputs'][role] = {'state': 'not_reached'}
                continue
            raw, pin = reader.read_regular(path); pins[str(path)] = pin
            captured = (final or {}).get('captured_files', {}).get(str(path))
            if not captured or 'final_' + role not in captured.get('roles', []):
                result['published_outputs'][role] = {'state': 'bytes_present_without_final_capture', 'pin': pin}
                continue
            if signature(captured) != signature(pin):
                raise ValueError('final published bytes differ from captured pin: ' + role)
            result['published_outputs'][role] = {'state': 'captured_final_bytes', 'pin': pin}
        rows = read_rows(arm)
        result['rows'] = rows
        checkpoints = [row for row in rows if row['event'] in ('thread_cpu_checkpoint', 'observer_end')]
        last = checkpoints[-1] if checkpoints else {}
        result['guard_reason_totals'] = {key: last.get(key) for key in
            ('guard_reason_counts', 'guard_reason_parent_phase_counts', 'guard_reason_details',
             'guard_reason_details_suppressed', 'guard_reason_callback_thread_cpu_ns')}
        if not isinstance(result['guard_reason_totals']['guard_reason_counts'], dict):
            raise ValueError('second observer guard counters missing')
        previous = {}
        for checkpoint in checkpoints:
            counts = checkpoint.get('guard_reason_counts')
            if (not isinstance(counts, dict)
                    or any(not isinstance(key, str) or type(value) is not int or value < 0
                           for key, value in counts.items())
                    or any(counts.get(key, -1) < value for key, value in previous.items())):
                raise ValueError('guard reason totals malformed or regressed')
            previous = counts
        result['guard_reason_cutoff'] = {key: last.get(key) for key in ('sequence', 'elapsed_ns', 'event')}
        result['censored'] = not arm['recorder'].get('complete_observer_valid')
        result['completed_phase_totals'] = arm['recorder']['phases']['targets']
        result['document_counters_at_own_cutoff'] = arm['recorder']['documents_at_checkpoint']
        result['partial_active_phases'] = arm['recorder']['phases']['partial_active_phases']
        result['last_cpu_checkpoint'] = arm['recorder']['phases']['latest_thread_cpu_checkpoint']
    except Exception as exc:
        errors.append(str(exc))
    result['valid'] = bool(not errors and arm.get('observed_measurement_prefix_valid'))
    return result


def compare_inputs(extra):
    left, right = extra
    if left.get('fixture_contract') != right.get('fixture_contract') or not left.get('fixture_contract'):
        return False
    for field in ('bundle', 'manifest', 'chunk_manifest'):
        a, b = (row.get('fixture_inputs', {}).get(field, {}) for row in extra)
        if (not a or not b or any(a.get(key) != b.get(key) for key in
                ('comparison_sha256', 'comparison_bytes', 'normalization'))):
            return False
    return True


def outputs(extra):
    result = {}
    for role in ('full', 'core'):
        a, b = (row.get('published_outputs', {}).get(role, {}) for row in extra)
        available = a.get('state') == b.get('state') == 'captured_final_bytes'
        result[role] = {'control': a, 'treatment': b, 'both_captured': available,
            'byte_equal': signature(a['pin']) == signature(b['pin']) if available else None}
    return result


def historical_observations(value):
    result = {'scope': 'unpaired historical observations only; different instrumentation and censored prefixes',
        'causal_comparison_allowed': False, 'arms': {}}
    for label in ('control', 'treatment'):
        arm = value.get(label, {})
        recorder = arm.get('recorder') or {}
        result['arms'][label] = {'source_head': arm.get('source_head'),
            'prefix_valid_as_previously_reported': arm.get('observed_measurement_prefix_valid'),
            'censored': not recorder.get('complete_observer_valid'),
            'completed_phase_totals': recorder.get('phases', {}).get('targets'),
            'last_cpu_checkpoint': recorder.get('phases', {}).get('latest_thread_cpu_checkpoint'),
            'automatic_ratios_or_speedups': None}
    return result


def historical_censored_cpu(history, treatment):
    """Describe a censored amount, never a paired cumulative speedup."""
    control = history.get('control', {})
    old = control.get('recorder') or {}
    new = treatment.get('recorder') or {}
    a = old.get('phases', {}).get('latest_thread_cpu_checkpoint') or {}
    b = new.get('phases', {}).get('latest_thread_cpu_checkpoint') or {}
    valid = bool(control.get('observed_measurement_prefix_valid')
        and not old.get('complete_observer_valid') and new.get('complete_observer_valid')
        and treatment.get('same_run_readback_verified'))
    return {'historical_control_censored_prefix': a.get('rusage'),
        'second_treatment_completed_recorder_checkpoint': b.get('rusage'),
        'descriptive_censored_lower_bound_available': valid,
        'scope': 'historical CPU consumed before censoring is a lower bound on that interrupted run only; differing observer overhead and host conditions prevent a cumulative causal comparison',
        'ratio': None, 'wall_time_margin': None, 'quiet_host_verdict': 'not_assessed'}


def analyze(control_trial, treatment_trial, observer_parent, source_manifest, historical=None):
    pins, errors = {}, []
    arms = [base.analyze_trial(path, observer_parent) for path in (control_trial, treatment_trial)]
    original = base.compare(*arms)  # Deliberately unchanged original gate.
    extra = [enrich(arm) for arm in arms]
    manifest = saved_json(source_manifest, pins)
    contract = source_contract(manifest, arms, [row.get('inventory', {}) for row in extra])
    same_inputs = compare_inputs(extra)
    common = bool(all(row['valid'] for row in extra) and contract['verified'] and same_inputs
        and original['matching_common_instrumentation_and_external_monitored_pins']
        and original['distinct_source_roots_and_heads'])
    try:
        phase_comparison = top_comparison(arms, [row.get('rows', []) for row in extra], common)
    except Exception as exc:
        errors.append(str(exc)); phase_comparison = {'common_gate_passed': False, 'errors': [str(exc)]}
    for row in extra:
        row.pop('rows', None); row.pop('inventory', None)
    result = {'format': 'native_u0_second_pair_saved_analysis_v1', 'limitations': LIMITATIONS,
        'errors': errors, 'valid': bool(common and not errors), 'artifact_pins': pins,
        'control': arms[0], 'treatment': arms[1], 'control_details': extra[0], 'treatment_details': extra[1],
        'unchanged_original_global_comparison': original, 'source_contract': contract,
        'matching_fixture_inputs': same_inputs, 'top_level_phase_comparison': phase_comparison,
        'published_full_core_comparison': outputs(extra),
        'quiet_wall_time_verdict': 'not_assessed', 'scientific_acceptance': 'not_assessed'}
    if historical:
        old = saved_json(historical, pins)
        result['historical_observations'] = historical_observations(old)
        result['historical_censored_cpu_observations'] = historical_censored_cpu(old, arms[1])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('control-trial', 'treatment-trial', 'observer-parent', 'sources', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--historical-analysis', type=Path)
    args = parser.parse_args(argv)
    if args.out.exists() or args.out.is_symlink():
        parser.error('output already exists; saved evidence is never overwritten')
    result = analyze(args.control_trial, args.treatment_trial, args.observer_parent,
                     args.sources, args.historical_analysis)
    result['analyzer_pin'] = reader.read_regular(Path(__file__))[1]
    result['base_analyzer_pin'] = reader.read_regular(Path(base.__file__))[1]
    result['reader_pin'] = reader.read_regular(Path(reader.__file__))[1]
    base.write_result(args.out, result)
    print(json.dumps({'output': str(args.out), 'sha256': reader.read_regular(args.out)[1]['sha256'],
        'valid': result['valid'], 'quiet_wall_time_verdict': 'not_assessed'}))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
