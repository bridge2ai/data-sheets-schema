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
        rows = [json.loads(line) for line in path.read_bytes().splitlines()]
        captures = [r for r in rows if r['boundary'] in ('capture_observed', 'synthetic_capture_minted')]
        reserved = [r for r in rows if r['boundary'] == 'attempt_reserved']
        spans = [{'capture': cap, 'reservation': end,
                  'elapsed_ns': end['elapsed_ns'] - cap['elapsed_ns']}
                 for end in reserved for cap in captures[-1:]]
        result['sidecars'].append({'path': str(path), 'rows': len(rows), 'spans': spans})
    result['outcome'] = json.loads((out / 'outcome.json').read_bytes()) if (out / 'outcome.json').exists() else None
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export')
    parser.add_argument('cohorts', nargs='+')
    args = parser.parse_args()
    for cohort in args.cohorts:
        out = BASE / 'tests' / (args.export + '-' + cohort)
        command = [sys.executable, '-S', '-P', '-B', str(ROOT / 'scripts/adhoc/run_h2_integration_20261113.py'),
                   '--tree', str(BASE / args.export), '--out', str(out), '--timeout-seconds', '14400']
        if cohort in PUBLIC:
            command.append(PUBLIC[cohort])
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
        else:
            parser.error('unknown cohort: ' + cohort)
        with (BASE / (args.export + '-' + cohort + '-runner.log')).open('xb') as log:
            code = subprocess.call(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        summary = summarize(out)
        print(json.dumps({'cohort': cohort, 'returncode': code, 'junit': summary.get('junit'),
                          'directory': str(out)}), flush=True)
