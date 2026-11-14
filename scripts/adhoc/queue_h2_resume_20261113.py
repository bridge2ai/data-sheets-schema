#!/usr/bin/env python3
"""Serial acceptance cohorts for helper-2 resume, issues 6193-6202, 2026-11-13.
Inputs: explicit phase, reviewed prior canary artifacts. Outputs: subprocess
logs/XML through run_h2_resume_20261113.py in sibling scratch, never exports.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-h2-resume-20261113'
RUNNER = ROOT / 'scripts/adhoc/run_h2_resume_20261113.py'

def require_canary(name):
    out = OUT / name
    result = json.loads((out / 'outcome.json').read_bytes())
    assert result['returncode'] == 0, name
    cases = list(ET.parse(out / 'pytest.xml').iter('testcase'))
    assert len(cases) == 1 and not any(c.find(t) is not None for c in cases for t in ('failure', 'error', 'skipped'))
    assert (out / 'pytest.log').stat().st_size > 0

def files(*names):
    return ['tests/test_native_' + name + '.py' for name in names]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('public', 'lanes', 'canary', 'acceptance'))
    args = p.parse_args()
    if args.phase == 'public':
        require_canary('correction')
        cohorts = [('omissions', []), ('pending', [])]
    elif args.phase == 'lanes':
        cohorts = [(name, []) for name in ('native', 'audit', 'budget')]
    elif args.phase == 'canary':
        cohorts = [('parallel-canary', ['--workers', '2',
            'tests/test_native_admission_timer.py::test_exact_boundary_is_expired_without_waiting_for_alarm_delivery'])]
    else:
        require_canary('parallel-canary')
        cohorts = [
            ('focused', files('admission_timer', 'pre_dispatch_timing', 'attempt_deadline',
                'admission_failure', 'attempt_timing', 'host_power', 'shared_permission_protocol', 'launch_sequence')),
            ('failure', files('shared_execution_failure')),
            ('guards', [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'tests').glob('test_generation_specificity_*.py'))]
                + files('u1_scanner_contracts', 'u3l_scanner')
                + ['tests/test_neutral_generation_schema.py', 'tests/test_profiles.py', 'tests/test_external_dataset_onboarding.py']),
            ('dependents', files('subscription_capture', 'shared_registration', 'shared_capture_split',
                'shared_capture_integration', 'failure_publication', 'execution_engine', 'shared_controller')),
        ]
        cohorts = [(name, ['--workers', '2', *nodes]) for name, nodes in cohorts]
    for name, nodes in cohorts:
        command = [sys.executable, str(RUNNER), name, *nodes]
        code = subprocess.call(command, cwd=ROOT)
        if code:
            raise SystemExit(code)

if __name__ == '__main__':
    main()
