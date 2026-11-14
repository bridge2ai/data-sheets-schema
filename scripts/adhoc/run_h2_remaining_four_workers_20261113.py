#!/usr/bin/env python3
"""Canary four workers, then finish H2 required suites, 2026-11-13.
Inputs: exact saved single-case canary and completed focused outcome. Outputs:
runner command/outcome/log/JUnit artifacts under sibling H2 scratch. No retries.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from queue_h2_resume_20261113 import require_canary, files

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-h2-resume-20261113'
RUNNER = ROOT / 'scripts/adhoc/run_h2_resume_20261113.py'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('canary', 'remaining'))
    args = parser.parse_args()
    assert (OUT / 'focused/outcome.json').is_file()
    if args.phase == 'canary':
        cohorts = [('parallel-canary-four', [
            'tests/test_native_admission_timer.py::test_existing_signal_state_is_refused_and_preserved[pending]'])]
    else:
        require_canary('parallel-canary-four')
        command = json.loads((OUT / 'parallel-canary-four/command.json').read_bytes())['command']
        assert command[command.index('-n') + 1] == '4'
        cohorts = [
            ('failure', files('shared_execution_failure')),
            ('guards', [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'tests').glob('test_generation_specificity_*.py'))]
                + files('u1_scanner_contracts', 'u3l_scanner')
                + ['tests/test_neutral_generation_schema.py', 'tests/test_profiles.py', 'tests/test_external_dataset_onboarding.py']),
            ('dependents', files('subscription_capture', 'shared_registration', 'shared_capture_split',
                'shared_capture_integration', 'failure_publication', 'execution_engine', 'shared_controller')),
        ]
    for name, nodes in cohorts:
        code = subprocess.call([sys.executable, str(RUNNER), name, '--workers', '4', *nodes], cwd=ROOT)
        if code:
            raise SystemExit(code)


if __name__ == '__main__':
    main()
