#!/usr/bin/env python3
"""U3-J2 reproducible single-cohort selector, 2026-11-09.

Inputs: retained U3-H exact selector roster and U3J2_MANIFEST. Outputs: one
fresh bounded offline cohort per invocation. No parallel cohorts, reruns of
public completion tests, provider operations, or protected-file changes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3'
PLAN = SCRATCH / 'u3h/composed-r1-plan.json'
PLAN_SHA = '2761622cdc90b457216ab5e69209488c6008b2d7d3f677b407feee9163752945'
PUBLIC = {
    'public-correction': ['tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion'],
    'public-omissions': ['tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses'],
}


def nodes(name):
    if name in PUBLIC:
        return PUBLIC[name], 1
    if name == 'd128':
        return ['tests/test_native_d128_scanner_comparison.py', 'tests/test_native_u5_scanner_comparison.py'], 2
    if name == 'execution-v2':
        suffixes = ('bridge_v2', 'registration_v2', 'verified_loader_v2', 'ci_v2',
            'authority_v2', 'round3_v2', 'round5_v2', 'round6_v2', 'engine',
            'gates', 'observation', 'permissions')
        return ['tests/test_native_execution_' + item + '.py' for item in suffixes], 2
    if name == 'shared-policy':
        suffixes = ('controls', 'permission_protocol', 'permission_split', 'callback_preloading',
            'gate_primitives', 'gates', 'consumer_census', 'projection_handoff',
            'permissions', 'runtime_values', 'registration')
        result = ['tests/test_native_shared_' + item + '.py' for item in suffixes]
        result += ['tests/test_native_u3d_guard_contract.py']
        result += ['tests/test_native_u3d_round9_' + item + '.py'
                   for item in ('capabilities', 'boundaries', 'preparation', 'arguments')]
        return result, 2
    if name.startswith('failure-'):
        groups = {
            'failure-reservation': ['test_missing_external_gate_refuses_before_reservation_or_probe',
                'test_v2_partial_reservation_stays_spent_without_probe',
                'test_subscription_expiring_during_admission_refuses_before_reservation'],
            'failure-lifecycle': ['test_public_pre_dispatch_failure_is_readable_and_cannot_resume',
                'test_v2_signal_is_sticky_and_previous_handlers_are_restored',
                'test_v2_injected_transport_timeout_keeps_registered_limit_and_failure',
                'test_v2_publication_failure_preserves_first_error'],
            'failure-readback': ['test_v2_saved_failure_rechecks_runtime_and_cleanup_after_successful_read',
                'test_saved_readback_revalidates_consumed_v2_approvals'],
        }
        if name not in groups:
            raise ValueError('use explicit existing failure selectors')
        return ['tests/test_native_shared_execution_failure.py::' + x for x in groups[name]], 2
    raw = PLAN.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PLAN_SHA
    rows = [row for row in json.loads(raw)['cohorts'] if row['name'] == name]
    assert len(rows) == 1
    result = rows[0]['nodes']
    assert not any(x.split('::')[0] in {v[0].split('::')[0] for v in PUBLIC.values()} for x in result)
    return result, 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cohort')
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label.replace('-', '').replace('_', '').isalnum():
        raise ValueError('literal output label required')
    selected, workers = nodes(args.cohort)
    manifest = Path(os.environ['U3J2_MANIFEST'])
    composition = json.loads(manifest.read_bytes())
    tree = Path(composition['worktree'])
    for node in selected:
        if not (tree / node.split('::')[0]).is_file():
            raise ValueError('missing selected test: ' + node)
    env = os.environ.copy()
    if args.cohort == 'parity':
        env['U3F_PARITY'] = '1'
    command = [sys.executable, '-S', '-P', '-B',
        str(ROOT / 'scripts/adhoc/run_native_u3j2_20261109.py'),
        '--out', str(SCRATCH / 'u3j2' / args.label), '--workers', str(workers), *selected]
    # Each invocation is one cohort; the inherited 3200s bound and 3250s
    # independent descendant watchdog remain in force.
    return subprocess.run(command, cwd=ROOT, env=env, timeout=3290).returncode


if __name__ == '__main__':
    raise SystemExit(main())
