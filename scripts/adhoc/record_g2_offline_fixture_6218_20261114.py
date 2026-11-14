#!/usr/bin/env python3
"""Record G2-REVIEW-6218-F2 and its offline power fixture correction.
Inputs: Git baseline, corrected fixture, ignored-inclusive test search.
Output: scratch review evidence, 2026-11-14. No project tests or host probes.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
RELATIVE = 'tests/test_native_u4b_a3_reservation.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    before = OUT / 'offline-power-fixture-before.py'
    with before.open('xb') as stream:
        stream.write(subprocess.check_output(['git', 'show', 'HEAD:' + RELATIVE], cwd=ROOT))
    scan = ['rg', '-l', '--hidden', '--no-ignore',
            'native_execution_orchestration|native_host_power|native_launch_sequence|native_sequence_start',
            'tests', '-g', 'test_*.py']
    inspected = subprocess.check_output(scan, cwd=ROOT, text=True).splitlines()
    value = {'finding_id': 'G2-REVIEW-6218-F2', 'status': 'corrected-test-verification-pending',
        'finding': 'The new pre-reservation power check is reachable from a component reservation fixture that did not previously stub the host interface; running that fixture could invoke a real host probe.',
        'correction': 'reservation_case supplies invented AC interface bytes, asserts the exact fixed battery command and bound, and retains the real dispatch_power parser/refusal path. Freshness-order tests reuse that fixture. Existing trace assertions remain unchanged.',
        'before': pin(before), 'corrected_source': pin(ROOT / RELATIVE),
        'inspection': {'command': scan, 'files': inspected,
            'finding': 'No other newly reachable missing host stub was found in this inspected scope. Full-lifetime cases use isolated_modules; sequence tests use their host/fake-command seams; other direct-engine cases stop before reservation.'},
        'tests_run': [], 'required_full_files': ['tests/test_native_u4b_a3_reservation.py',
                                               'tests/test_native_u3k_freshness_order.py'],
        'lead_filing_needed': True, 'github_issue_number': None,
        'filing_reason': 'Helper GitHub writes are prohibited; lead filing is required.'}
    destination = OUT / 'offline-power-fixture-review.json'
    with destination.open('x') as stream:
        stream.write((json.dumps(value, indent=2) + '\n').replace(chr(64), '\\u0040'))
    print(json.dumps(pin(destination)))


if __name__ == '__main__':
    main()
