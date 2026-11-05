#!/usr/bin/env python3
"""Set evidence-backed SG2 scheduling estimates for PR #5213, 2026-11-02.

Inputs: SHA-bound diagnostic summary, retained0fa JUnit run, current duration
JSON and test source. Outputs: duration JSON plus a fresh provenance report.
Only file_seconds is consumed by the existing scheduler; node estimates below
explain that aggregate. Local macOS timings are not Linux/CI budget promises.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import xml.etree.ElementTree as ET

HEAD = '0fa106e4d558c1c119e8f386222e225ac3acca24'
MODULE = 'tests/test_wave7_5213_d76_registration.py'
FUNCTION = 'test_sg2_root_launch_completes_and_records_registered_paths'
LAYOUTS = ('none', 'explicit', 'conventional')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def body(raw, name):
    found = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(found) != 1:
        raise ValueError('exactly one SG2 assertion function required')
    return ast.dump(ast.Module(body=found[0].body, type_ignores=[]), include_attributes=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--diagnostic-sha256', required=True)
    parser.add_argument('--historical-run', type=Path, required=True)
    parser.add_argument('--historical-xml-sha256', required=True)
    parser.add_argument('--durations', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists() or args.report.is_symlink() or not args.report.parent.is_dir() or args.report.parent.resolve() != args.report.parent:
        raise ValueError('fresh provenance report required')
    if args.durations.is_symlink() or not args.durations.is_file() or args.durations.resolve() != args.durations:
        raise ValueError('physical regular duration file required')
    replacement = args.durations.with_name(args.durations.name + '.d76-new')
    if replacement.exists() or replacement.is_symlink():
        raise ValueError('fresh atomic replacement path required')
    diagnostic_raw = args.diagnostic.read_bytes()
    xml_raw = (args.historical_run / 'pytest.xml').read_bytes()
    if sha(diagnostic_raw) != args.diagnostic_sha256 or sha(xml_raw) != args.historical_xml_sha256:
        raise ValueError('timing evidence differs from supplied SHA256')
    diagnostic, plan, outcome = (json.loads(diagnostic_raw), read(args.historical_run / 'plan.json'),
                                 read(args.historical_run / 'outcome.json'))
    if diagnostic['head'] != HEAD or plan['head'] != HEAD or not outcome['passed']:
        raise ValueError('timings must refer to retained0fa; historical acceptance must pass')
    proof_names = ('plan.json', 'outcome.json', 'phase-accounting.json', 'nodes.json',
                   'source-before.json', 'source-after.json', 'hygiene.json', 'guard-denials.json')
    historical_proofs = {name: read(args.historical_run / name) for name in proof_names}
    before_source, after_source = historical_proofs['source-before.json'], historical_proofs['source-after.json']
    phases, nodes = historical_proofs['phase-accounting.json'], historical_proofs['nodes.json']
    if (before_source != after_source or not before_source['tracked_exact'] or before_source['head'] != HEAD
            or before_source['tree'] != plan['git_tree'] or phases['counts'] != outcome['counts']
            or not phases['all_selected_completed']
            or Counter(row['nodeid'] for row in phases['occurrences']) != Counter(nodes['selected'])
            or not all(outcome.get(key) is True for key in ('source_unchanged', 'hygiene_passed',
                'origins_verified', 'helpers_unchanged', 'targets_unchanged', 'sandbox_loaded',
                'zero_guard_denials', 'node_accounting_complete'))
            or not historical_proofs['hygiene.json']['passed']
            or not historical_proofs['guard-denials.json']['zero_denials']):
        raise ValueError('historical timing source/phase/hygiene proofs are not complete and valid')
    git_env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    git_env.update(GIT_NO_LAZY_FETCH='1', GIT_CONFIG_GLOBAL='/dev/null',
                   GIT_CONFIG_NOSYSTEM='1', GIT_OPTIONAL_LOCKS='0')
    original = subprocess.check_output(['git', '--no-replace-objects', '-c', 'protocol.allow=never',
        '-C', str(args.tree), 'show', HEAD + ':' + MODULE], env=git_env)
    current = (args.tree / MODULE).read_bytes()
    original_body, current_body = body(original, FUNCTION), body(current, '_assert_sg2_root_launch')
    if original_body != current_body:
        raise ValueError('SG2 assertion body differs from measured baseline')
    cases = [case for case in ET.fromstring(xml_raw).iter('testcase')
             if case.get('classname', '').endswith('test_wave7_5213_d76_registration')]
    if not cases or any(case.find(kind) is not None for case in cases for kind in ('failure', 'error', 'skipped')):
        raise ValueError('historical module cases must all be completed passes')
    module_phases = [row for row in phases['occurrences'] if row['nodeid'].startswith(MODULE + '::')]
    if (not all(row['complete'] and row['status'] == 'passed' for row in module_phases)
            or Counter(row['nodeid'] for row in module_phases) != Counter(MODULE + '::' + case.get('name', '') for case in cases)):
        raise ValueError('historical XML module cases do not match completed phase evidence')
    estimates, observations = {}, {}
    for layout in LAYOUTS:
        node = FUNCTION + '[' + layout + ']'
        matches = [case for case in cases if case.get('name') == node]
        if len(matches) != 1:
            raise ValueError('one historical observation required for ' + node)
        times = [{'source': 'historical_junit', 'seconds': float(matches[0].get('time'))}]
        for row in diagnostic['sg2_cases']:
            if row['nodeid'] == MODULE + '::' + node:
                times.append({'source': 'fresh_serial_diagnostic', 'seconds': row['elapsed_seconds']})
        if any(not math.isfinite(row['seconds']) or row['seconds'] <= 0 for row in times):
            raise ValueError('positive finite observed durations required')
        # Conservative scheduling estimate, not a measured future runtime:
        # choose the larger retained observation, then a declared 10% margin.
        estimates[node] = math.ceil(max(row['seconds'] for row in times) * 1.10)
        observations[node] = times
    other_times = [float(case.get('time')) for case in cases if not case.get('name', '').startswith(FUNCTION + '[')]
    if not other_times or any(not math.isfinite(value) or value < 0 for value in other_times):
        raise ValueError('nonnegative finite individual remaining observations required')
    remaining = sum(other_times)
    aggregate = round(sum(estimates.values()) + remaining, 3)
    if not math.isfinite(remaining) or remaining <= 0 or not math.isfinite(aggregate) or aggregate <= 0:
        raise ValueError('positive finite module aggregate required')
    before_raw = args.durations.read_bytes()
    data = json.loads(before_raw)
    overrides = data.setdefault('local_overrides', [])
    if not isinstance(overrides, list) or any(row.get('name') == 'd76_sg2_2026_11_02' for row in overrides):
        raise ValueError('SG2 override already applied or unexpected metadata shape')
    record = {'name': 'd76_sg2_2026_11_02', 'module': MODULE,
        'baseline_head': HEAD, 'file_seconds': aggregate, 'node_estimate_seconds': estimates,
        'observations': observations, 'other_historical_module_seconds': remaining,
        'diagnostic_complete_required_sequence': diagnostic['complete_required_sequence'],
        'diagnostic_literal_counts': diagnostic['outcome']['counts'],
        'diagnostic_literal_passed': diagnostic['outcome']['passed'],
        'diagnostic_summary_sha256': args.diagnostic_sha256,
        'historical_junit_sha256': args.historical_xml_sha256,
        'historical_plan_sha256': sha((args.historical_run / 'plan.json').read_bytes()),
        'historical_proof_sha256': {name: sha((args.historical_run / name).read_bytes()) for name in proof_names},
        'assertion_body_ast_sha256': sha(original_body.encode()),
        'method': 'Per node: ceiling(max(retained observations)*1.10). Module sum includes other retained case times.',
        'limits': 'macOS/Python3.13 observations across different concurrency modes; child isolation may change runtime. '
                  'Only the file aggregate is consumed by the current scheduler; no node scheduling or CI budget claim.'}
    overrides.append(record)
    data['file_seconds'][MODULE] = aggregate
    data['file_seconds'] = dict(sorted(data['file_seconds'].items()))
    after_raw = (json.dumps(data, indent=2) + '\n').encode()
    report = {'record': record, 'application_policy': 'Provenance is saved before replacement; successful execution verifies the installed after SHA.',
        'durations_before_sha256': sha(before_raw),
        'durations_after_sha256': sha(after_raw), 'diagnostic': str(args.diagnostic),
        'historical_run': str(args.historical_run), 'producer_sha256': sha(Path(__file__).read_bytes()),
        'test_source_sha256': sha(current), 'unchanged_assertion_body': True}
    with args.report.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    if args.durations.read_bytes() != before_raw:
        raise ValueError('duration file changed during preparation; original retained')
    with replacement.open('xb') as stream:
        stream.write(after_raw)
    replacement.chmod(stat.S_IMODE(args.durations.stat().st_mode))
    os.replace(replacement, args.durations)
    if args.durations.read_bytes() != after_raw:
        raise ValueError('duration replacement did not persist expected bytes')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
