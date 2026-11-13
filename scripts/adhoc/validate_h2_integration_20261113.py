#!/usr/bin/env python3
"""Serial offline integration checks for issues 6193-6202, 2026-11-13.
Inputs: exact export label and explicit cohort names. Outputs: saved runner
logs, JUnit, source identities, outcomes, and public sidecar timing summaries.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = Path.home() / 'agent-work/data-sheets-schema/helper2-integration-fixes-20261113'
PUBLIC = {
    'correction': 'tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion',
    'omissions': 'tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses',
    'pending': 'tests/test_native_pending_public_completion.py::test_pending_floor_public_completion_retains_diagnostic_reading',
}


def summarize(out):
    result = {'directory': str(out)}
    xml = out / 'pytest.xml'
    if xml.exists():
        cases = list(ET.parse(xml).iter('testcase'))
        result['junit'] = {'total': len(cases), 'passed': sum(
            not any(c.find(tag) is not None for tag in ('failure', 'error', 'skipped')) for c in cases),
            **{tag: sum(c.find(tag) is not None for c in cases) for tag in ('failure', 'error', 'skipped')}}
        result['failures'] = [dict(c.attrib, detail=ET.tostring(c, encoding='unicode'))
            for c in cases if c.find('failure') is not None or c.find('error') is not None]
    paths = list((out / 'cases').rglob('actual-result.json'))
    result['public_results'] = [{'path': str(p), 'result': json.loads(p.read_bytes())} for p in paths]
    result['sidecars'] = []
    for path in (out / 'cases').rglob('host-pre-dispatch-*.jsonl'):
        if path.is_symlink():
            result['sidecars'].append({'path': str(path), 'skipped': 'symlink fixture', 'spans': []})
            continue
        try:
            rows = [json.loads(line) for line in path.read_bytes().splitlines()]
            assert all(isinstance(row, dict) and 'boundary' in row for row in rows)
        except (ValueError, AssertionError) as exc:
            result['sidecars'].append({'path': str(path), 'parse_error': type(exc).__name__, 'spans': []})
            continue
        captures = [r for r in rows if r['boundary'] in ('capture_observed', 'synthetic_capture_minted')]
        reserved = [r for r in rows if r['boundary'] == 'attempt_reserved']
        spans = [{'capture': cap, 'reservation': end,
                  'elapsed_ns': end['elapsed_ns'] - cap['elapsed_ns']}
                 for end in reserved for cap in captures[-1:]]
        intervals = [{'before': {key: before.get(key) for key in ('boundary', 'phase', 'trace_id', 'elapsed_ns', 'wall_ns')},
                      'after': {key: after.get(key) for key in ('boundary', 'phase', 'trace_id', 'elapsed_ns', 'wall_ns')},
                      'elapsed_ns': after['elapsed_ns'] - before['elapsed_ns'],
                      'wall_ns': after['wall_ns'] - before['wall_ns']}
                     for before, after in zip(rows, rows[1:])
                     if all(isinstance(row.get(key), int) for row in (before, after)
                            for key in ('elapsed_ns', 'wall_ns'))]
        result['sidecars'].append({'path': str(path), 'rows': len(rows), 'spans': spans,
            'longest_adjacent_intervals': sorted(intervals, key=lambda item: item['elapsed_ns'], reverse=True)[:5]})
    result['outcome'] = json.loads((out / 'outcome.json').read_bytes()) if (out / 'outcome.json').exists() else None
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export')
    parser.add_argument('cohorts', nargs='+')
    parser.add_argument('--after', help='Wait for the named prior cohort cleanup receipt; never overlap public tests.')
    parser.add_argument('--stop-on-failure', action='store_true')
    parser.add_argument('--summarize-only', action='store_true', help='Read completed artifacts without launching tests.')
    args = parser.parse_args()
    if args.summarize_only:
        for name in args.cohorts:
            summary = summarize(BASE / 'tests' / (args.export + '-' + name))
            print(json.dumps({'cohort': name, 'junit': summary.get('junit'),
                              'outcome': summary.get('outcome', {}).get('returncode')}))
        raise SystemExit(0)
    if args.after:
        receipt = BASE / 'tests' / args.after / 'outcome.json'
        while not receipt.exists():
            time.sleep(.5)
        previous = json.loads(receipt.read_bytes())
        assert previous['cleanup_verified'], 'prior cohort cleanup is not verified'
    cohorts = list(args.cohorts)
    parallel = {'focused', 'dependents', 'guards'}
    if any(name in parallel for name in cohorts):
        prior_canary = BASE / 'tests' / (args.export + '-unit-canary')
        plan = json.loads((prior_canary / 'plan.json').read_bytes()) if (prior_canary / 'plan.json').exists() else {}
        outcome = json.loads((prior_canary / 'outcome.json').read_bytes()) if (prior_canary / 'outcome.json').exists() else {}
        if not (plan.get('workers') == 2 and outcome.get('cleanup_verified') and outcome.get('returncode') == 0):
            cohorts.insert(next(i for i, name in enumerate(cohorts) if name in parallel), 'parallel-canary')
    for cohort in cohorts:
        out = BASE / 'tests' / (args.export + '-' + cohort)
        command = [sys.executable, '-S', '-P', '-B', str(ROOT / 'scripts/adhoc/run_h2_integration_20261113.py'),
                   '--tree', str(BASE / args.export), '--out', str(out), '--timeout-seconds', '14400']
        if cohort in ('unit-canary', 'parallel-canary', 'focused', 'dependents', 'guards'):
            command += ['--workers', '2']
        if cohort in PUBLIC:
            command.append(PUBLIC[cohort])
        elif cohort in ('unit-canary', 'parallel-canary'):
            command.append('tests/test_native_admission_timer.py::test_existing_signal_state_is_refused_and_preserved[pending]')
        elif cohort == 'admission-retry':
            command.append('tests/test_native_admission_failure.py::test_shared_engine_stalled_admission_publishes_and_stops_timing')
        elif cohort in ('budget', 'native', 'audit'):
            command += ['--lane', cohort]
        elif cohort == 'scanner':
            command += ['--scanner']
        elif cohort == 'guards':
            command += sorted(str(p.relative_to(BASE / args.export)) for p in
                              (BASE / args.export / 'tests').glob('test_generation_specificity_*.py'))
            command += ['tests/' + name + '.py' for name in ('test_native_u1_scanner_contracts',
                'test_native_u3l_scanner', 'test_neutral_generation_schema', 'test_profiles',
                'test_external_dataset_onboarding')]
        elif cohort == 'focused':
            command += ['tests/' + name + '.py' for name in ('test_native_shared_callback_preloading',
                'test_native_admission_timer', 'test_native_admission_failure', 'test_native_attempt_deadline',
                'test_native_pre_dispatch_timing', 'test_native_attempt_timing', 'test_native_host_power',
                'test_native_shared_permission_protocol', 'test_native_launch_sequence')]
        elif cohort == 'dependents':
            command += ['tests/' + name + '.py' for name in ('test_native_subscription_capture',
                'test_native_shared_registration', 'test_native_shared_capture_split',
                'test_native_shared_capture_integration', 'test_native_failure_publication',
                'test_native_execution_engine', 'test_native_shared_controller')]
        else:
            parser.error('unknown cohort: ' + cohort)
        with (BASE / (args.export + '-' + cohort + '-runner.log')).open('xb') as log:
            code = subprocess.call(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        summary = summarize(out)
        print(json.dumps({'cohort': cohort, 'returncode': code, 'junit': summary.get('junit'),
                          'directory': str(out)}), flush=True)
        if code and (args.stop_on_failure or cohort == 'parallel-canary'):
            raise SystemExit(code)
