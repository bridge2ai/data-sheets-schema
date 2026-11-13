#!/usr/bin/env python3
"""Verify the D128 refresh command without a scan, helper-1 followups, 2026-11-13.
Inputs: saved refresh wrapper and accepted candidate checkout; outputs: JSON witness.
Checks real preflight, synthetic comparator controls and wrong-head/label refusal.
No export, source edit, provider or native executable is invoked.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
R = E / 'codex-development-efficiency-20261111'
S = R / 'scripts/adhoc'
WRAPPER = S / 'refresh_h1_d128_20261113.py'
PYTHON = E.parent / 'data-sheets-schema/.venv/bin/python'
COMMIT = '99ac3432daab7f6161b321038986e489d5e6fd14'
LABEL = 'followup-plan-20261113-01'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': '/var/empty', 'LC_ALL': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': 'file', 'GIT_TERMINAL_PROMPT': '0',
       'PYTHONOPTIMIZE': '0', 'UV_OFFLINE': '1', 'PIP_NO_INDEX': '1'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('preserve existing witness')
    forbidden = [E / 'scratch-native-main-integration-20261112' / ('h1-ci-' + LABEL),
                 E / 'scratch-native-h1-scanner-20261112' / ('h1-d128-' + LABEL)]
    if any(os.path.lexists(p) for p in forbidden):
        raise RuntimeError('verification label has existing evidence')
    cases = [
        ('plan', ['--plan', '--commit', COMMIT, '--label', LABEL], 0, None),
        ('controls', ['--self-check'], 0, None),
        ('wrong_head', ['--plan', '--commit', '0' * 40, '--label', LABEL], 1, 'assigned HEAD differs'),
        ('bad_label', ['--plan', '--commit', COMMIT, '--label', '../escape'], 1, 'label suffix must'),
    ]
    rows = []
    for name, tail, expected, error in cases:
        command = [str(PYTHON), '-S', '-P', '-B', str(WRAPPER), *tail]
        completed = subprocess.run(command, env=ENV, capture_output=True, text=True, timeout=60)
        if completed.returncode != expected or (error and error not in completed.stderr):
            raise RuntimeError(name + ': unexpected result: ' + completed.stderr)
        rows.append({'case': name, 'command': command, 'returncode': completed.returncode,
                     'stdout': completed.stdout, 'stderr': completed.stderr})
    plan = json.loads(rows[0]['stdout'])
    controls = json.loads(rows[1]['stdout'])
    if (plan['status'] != 'read_only_plan' or controls['result']['real_scans_run'] is not False
            or controls['result']['status'] != 'synthetic_comparator_controls_passed'
            or any(os.path.lexists(p) for p in forbidden)):
        raise RuntimeError('read-only verification side effects differ')
    result = {'status': 'plan_and_controls_passed', 'cases': rows,
              'wrapper_sha256': hashlib.sha256(WRAPPER.read_bytes()).hexdigest(),
              'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'new_scans_run': False, 'export_directories_created': False,
              'run_orchestration_verified_end_to_end': False,
              'limitation': 'The unchanged donors have prior real-scan evidence; this new wrapper was validated in plan/control modes only.'}
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    with args.output.open('xb') as stream:
        stream.write(raw)
    if args.output.read_bytes() != raw:
        raise RuntimeError('persisted witness differs')
    print(json.dumps({'path': str(args.output), 'sha256': hashlib.sha256(raw).hexdigest(),
                      'status': result['status'], 'synthetic_controls': len(controls['result']['controls'])}))


if __name__ == '__main__':
    main()
