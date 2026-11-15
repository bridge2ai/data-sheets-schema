"""Issue 6243 offline comparison, 2026-11-15.
Inputs: worktree tests and base guard from git. Outputs: scratch logs and JUnit.
The base mode replaces only the guard module before test collection, including
in xdist workers. No provider or native executable is called by this helper.
"""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-subscription-windows-6243-20261115'
BASE = 'f5c7c312f41e555c8023b880eeb3da327aa815cb'
FILES = [
    'test_native_subscription_guard.py', 'test_native_subscription_guard_v2.py',
    'test_native_subscription_capture.py', 'test_native_u4b_admission.py',
    'test_native_launch_review.py', 'test_native_u4b_probe_sequence.py',
    'test_native_u4b_addendum_authority.py', 'test_native_u4b_windows_v2.py',
    'test_native_u4b_a4_real_events.py', 'test_native_u4b_a5_reasons.py',
    'test_native_latest_capture_claim.py', 'test_native_failure_publication.py',
    'test_native_shared_execution_failure.py',
]


def pytest_configure(config):
    if os.environ.get('SUBSCRIPTION_6243_BASE') == '1':
        from data_sheets_schema import native_subscription_guard_v2 as guard
        raw = subprocess.check_output(['git', 'show', BASE + ':src/data_sheets_schema/native_subscription_guard_v2.py'], cwd=ROOT)
        exec(compile(raw, guard.__file__, 'exec'), guard.__dict__)


def main():
    mode = sys.argv[1]
    assert mode in ('base', 'candidate')
    canary = len(sys.argv) > 2 and sys.argv[2] == 'canary'
    label = mode + ('-canary' if canary else '')
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'),
               PYTHONPYCACHEPREFIX=str(SCRATCH / 'pycache'),
               SUBSCRIPTION_6243_BASE='1' if mode == 'base' else '0')
    command = [sys.executable, '-m', 'pytest', '-n', '4',
               '-p', 'scripts.adhoc.check_subscription_windows_6243_20261115',
               *(['tests/test_native_subscription_guard_v2.py::test_weekly_only_warning_admits_and_replays_without_inventing_five_hour']
                 if canary else ['tests/' + name for name in FILES]),
               '--basetemp=' + str(SCRATCH / (label + '-pytest')),
               '--junitxml=' + str(SCRATCH / (label + '.xml'))]
    (SCRATCH / (label + '-command.txt')).write_text(repr(command) + '\n')
    with (SCRATCH / (label + '.log')).open('w') as output:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
    print(mode, result.returncode, flush=True)
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
