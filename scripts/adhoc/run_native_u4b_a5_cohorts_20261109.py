#!/usr/bin/env python3
"""A5 cohort provenance (#4354), 2026-11-09.

Inputs: retained A4 pytest commands, current test roster, completed A5 canary.
Output: fresh A5 run directories under scratch-native-u4b. Sequential, offline;
the existing supervisor enforces two workers, quiet windows and 3200 seconds.
Default is a read-only plan. No provider/native executable is invoked.
"""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u4b'
GROUPS = {'u4': 'a4-u4-final', 'u5-core': 'a4-u5-core',
          'u5-typed': 'a4-u5-typed', 'u5-receipts': 'a4-u5-receipts',
          'u5-specificity': 'a4-u5-specificity', 'u5-delegated': 'a4-u5-delegated',
          'u5-scanner': 'a4-u5-scanner-final',
          'u5-registration': 'a4-u5-registration-control',
          'u5-readback': 'a4-u5-readback-control'}


def nodes(group):
    if group == 'neutral':
        return ['tests/test_neutral_generation_schema.py', 'tests/test_profiles.py',
                'tests/test_external_dataset_onboarding.py', 'tests/test_native_u4b_a5_scanner.py',
                'tests/test_native_u4b_toolchain.py']
    if group == 'u4b':
        return sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'tests').glob('test_native_u4b_*.py')) + [
            'tests/test_native_subscription_guard_v2.py', 'tests/test_native_subscription_capture.py',
            'tests/test_native_launch_review.py', 'tests/test_native_model_aliases.py',
            'tests/test_native_receipt_unopened.py', 'tests/test_native_shared_permissions.py']
    return [arg for arg in json.loads((SCRATCH / GROUPS[group] / 'pytest-command.json').read_bytes())['args']
            if arg.startswith('tests/')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--prefix', default='a5')
    parser.add_argument('groups', nargs='+', choices=['u4b', 'neutral', *GROUPS])
    args = parser.parse_args()
    if re.fullmatch(r'a5(?:r[0-9]+)?', args.prefix) is None:
        raise ValueError('require an A5 evidence prefix')
    commands = [[sys.executable, '-S', '-P', '-B',
                 str(ROOT / 'scripts/adhoc/run_native_u4b_tests_20261108.py'),
                 '--out', str(SCRATCH / (args.prefix + '-' + group)), '--workers', '2', *nodes(group)]
                for group in args.groups]
    print(json.dumps(commands, indent=2), flush=True)
    if not args.run:
        return
    canary = SCRATCH / 'a5-canary2'
    outcome = json.loads((canary / 'outcome.json').read_bytes())
    assert outcome['returncode'] == 0 and outcome['cleanup_verified']
    assert (canary / 'pytest.xml').stat().st_size > 0
    assert list((canary / 'cases').glob('popen-*/test_prepare*/instruction.txt'))
    for command in commands:
        if os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'):
            raise SystemExit('quiet window active; no next cohort started')
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode not in (0, 1):
            raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
