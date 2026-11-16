"""Purpose: reproduce offline validation for issues 6263 through 6272.

Inputs: primary checkout, scratch root, optional --dry-run.
Outputs: lane logs, summaries and JUnit in scratch. 2026-11-16.
"""
from pathlib import Path
import subprocess
import sys

primary, scratch = map(Path, sys.argv[1:3])
root = Path(__file__).resolve().parents[2]
dry = ['--dry-run'] if '--dry-run' in sys.argv[3:] else []
focused = [
    'prepared_worker', 'prepared_sequence', 'launch_sequence', 'launch_sequence_signals',
    'launch_sequence_paths', 'sequence_start', 'sequence_inputs', 'sequence_capture_dispatch',
    'subscription_guard', 'subscription_guard_v2', 'dispatch_boundary_d156',
    'shared_controller', 'attribution_controller', 'environment_census',
]
plans = [
    ('focused', ['--lane', 'unit', '--workers', '3', '--allow-overcommit', '--',
                 *['tests/test_native_' + name + '.py' for name in focused]]),
    ('controls', ['--lane', 'offline-canary', '--', '-n', '3', '--dist', 'load']),
    ('scanners', ['--lane', 'unit', '--workers', '3', '--allow-overcommit', '--',
                  'tests/test_native_h1_scanner_authority.py', 'tests/test_native_u1_scanner_contracts.py']),
    ('collection', ['--lane', 'unit', '--', '--collect-only', '-q', 'tests']),
]
for name, flags in plans:
    command = [sys.executable, str(primary / 'scripts/adhoc/run_lane_20261115.py'),
        '--root', str(root), '--python', str(scratch / 'isolated-venv/bin/python'),
        '--scratch-dir', str(scratch / name), '--gate-wait-seconds', '1800',
        '--timeout-seconds', '1800', *dry, *flags]
    print('COMMAND: ' + ' '.join(command), flush=True)
    result = subprocess.run(command, cwd=root)
    print('LANE RESULT: ' + name + ' ' + str(result.returncode), flush=True)
