#!/usr/bin/env python3
"""Save the internal read-only H1-420-F1 review, 2026-11-13.
Inputs: current missing-gate test diff and resume launcher bytes.
Output: sibling scratch-h2-resume-20261113/review.json; no tests or source edits.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-h2-resume-20261113/review.json'
TEST = 'tests/test_native_shared_execution_failure.py'
LAUNCHER = 'scripts/adhoc/run_h2_resume_20261113.py'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    diff = subprocess.check_output(['git', 'diff', 'HEAD', '--', TEST], cwd=ROOT)
    assert diff, 'The reviewed missing-gate test diff must be present.'
    files = [TEST, LAUNCHER,
        'src/data_sheets_schema/native_shared_execution_orchestration.py',
        'src/data_sheets_schema/native_execution_orchestration.py',
        'src/data_sheets_schema/native_shared_registration_orchestration.py',
        'src/data_sheets_schema/native_subscription_admission.py',
        'src/data_sheets_schema/native_pre_dispatch_timing.py',
        '.github/workflows/main.yaml']
    record = {
        'review_type': 'internal read-only source review',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'scope': [
            'H1-420-F1 missing-gate test diff against actual registration timing emission.',
            'Preservation of every other snapshot byte, forbidden effect and absent attempt/evidence directory.',
            'Resume launcher interpreter, explicit cohort selection, workflow environment and output placement.'
        ],
        'findings': [],
        'verdict': 'No blocking findings for the reviewed test diff and intended explicit cohort invocations.',
        'tests_run': [],
        'limitations': ['Static review only; no runtime or test result certified.'],
        'diff_command': ['git', 'diff', 'HEAD', '--', TEST],
        'current_diff_sha256': sha(diff),
        'reviewed_inputs': [{'path': str(ROOT / name), 'sha256': sha((ROOT / name).read_bytes())}
                            for name in files],
        'reasoning': [
            'Missing review and word refuse after successful registration verification; missing CI refuses after further successful registration checks.',
            'The expected appended rows are completed registration.verified spans with null end errors.',
            'The test waits after preparation and launch outcomes, permits exactly the digest sidecar append and checks all other saved bytes unchanged.',
            'The launcher selects the primary interpreter and preserves native/audit workflow file lists and environment; public cases use no xdist.'
        ]
    }
    raw = (json.dumps(record, indent=2) + '\n').encode()
    assert bytes([64]) not in raw
    with OUT.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'path': str(OUT), 'sha256': sha(OUT.read_bytes()),
                      'current_diff_sha256': record['current_diff_sha256']}))

if __name__ == '__main__':
    main()
