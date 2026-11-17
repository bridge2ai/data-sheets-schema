"""Reproduce assigned offline D159 checks through the canonical lane runner.

Inputs: this checkout, sibling isolated interpreter, selected lane. Outputs:
dry-run command JSON by default; --run creates fresh timestamped scratch evidence.
Purpose: D159 lead handoff, 2026-11-17. Never invokes a native model binary.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
scratch = root.parent / 'scratch-d159-limits-20261117'
runner = root.parent.parent / 'data-sheets-schema/scripts/adhoc/run_lane_20261115.py'
python = scratch / 'isolated-venv/bin/python'
focused = [
    'native_admission_timer', 'native_admission_failure', 'native_subscription_guard_v2',
    'native_dispatch_boundary_d156', 'native_u4b_a3_policy', 'native_attempt_deadline',
    'native_shared_controller', 'native_shared_runtime_values', 'native_shared_runtime_constants',
    'native_launch_sequence', 'native_launch_sequence_signals', 'native_prepared_worker',
    'native_prepared_sequence', 'ci_sharding', 'native_ci_evidence', 'native_run_limits',
    'native_synthetic_profiles', 'native_permission_probe', 'native_host_power',
    'native_shared_observations', 'native_shared_permission_protocol',
    'native_shared_callback_teardown', 'native_shared_callback_report_bound',
    'native_launch_review', 'native_u4b_runtime', 'native_u4b_a4_review',
    'native_u4b_probe_sequence', 'native_probe_drafts', 'native_recorder_env',
    'native_canary_packet_builder', 'native_execution_registration_v2',
]
parser = argparse.ArgumentParser()
parser.add_argument('--lane', required=True, choices=['focused', 'native-controls', 'corrections', 'collection'])
parser.add_argument('--run', action='store_true')
args = parser.parse_args()
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
destination = scratch / ('rerun-'+stamp) / args.lane
lane = 'offline-canary' if args.lane == 'native-controls' else 'unit'
command = [sys.executable, str(runner), '--root', str(root), '--lane', lane,
    '--python', str(python), '--gate-wait-seconds', '1800', '--timeout-seconds', '3600',
    '--scratch-dir', str(destination)]
if args.lane == 'focused':
    targets = ['tests/test_'+name+'.py' for name in focused]
    assert all((root / name).is_file() for name in targets)
    command += ['--', *targets]
elif args.lane == 'collection':
    command += ['--', '--collect-only', '-q', 'tests']
elif args.lane == 'corrections':
    targets = [
        'tests/test_native_prepared_sequence.py::test_readiness_refuses_dead_or_expired_worker',
        'tests/test_native_run_limits.py::test_canary_same_input_bytes_preserved_but_old_deadline_policy_refuses',
        'tests/test_native_permission_probe.py::test_denied_group_signal_still_attempts_reap_and_preserves_refusal',
    ]
    targets += ['tests/test_native_execution_registration_v2.py::test_execution_prefix_must_match_rederived_preparation_before_consumer['+name+']'
                for name in ['working_directory', 'composition_digest', 'composition',
                             'composition_instruction', 'composition_selection', 'composition_runtime']]
    assert all((root / name.split('::')[0]).is_file() for name in targets)
    command += ['--', *targets]
assert runner.is_file() and python.is_file()
plan = {'lane': args.lane, 'cwd': str(root), 'argv': command, 'scratch': str(destination)}
if args.run:
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'command.json').write_text(json.dumps(plan, indent=2)+'\n')
    with (destination / 'launcher.log').open('x') as stream:
        result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
    plan['returncode'] = result.returncode
    (destination / 'result.json').write_text(json.dumps(plan, indent=2)+'\n')
print(json.dumps(plan, indent=2))
if args.run:
    raise SystemExit(result.returncode)
