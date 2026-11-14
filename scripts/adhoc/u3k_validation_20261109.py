#!/usr/bin/env python3
"""One bounded offline U3-K cohort, 2026-11-09.

Inputs: exact U3-J2 selector functions and U3K_MANIFEST. Outputs: one fresh
u3k evidence directory. Control/profile are the same diagnostic; final public
nodes are separate once-only measurements. No providers or packet changes.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3/u3k'
spec = importlib.util.spec_from_file_location('u3k_retained_selectors',
    ROOT / 'scripts/adhoc/u3j2_validation_20261109.py')
selectors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selectors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cohort')
    parser.add_argument('--label', required=True)
    parser.add_argument('--node', action='append', default=[])
    args = parser.parse_args()
    if not args.label.replace('-', '').replace('_', '').isalnum():
        raise ValueError('literal output label required')
    env = os.environ.copy()
    env['U3K_OBSERVE'] = '1' if args.cohort in {
        'metrics-canary', 'control', 'profile', 'public-correction', 'public-omissions'} else '0'
    env['U3K_PROFILE'] = 'control'
    if args.cohort == 'metrics-canary':
        nodes, workers = ['tests/test_native_u3k_profile.py::test_profile_observer_canary'], 1
        env['U3K_PROFILE'] = 'control'
    elif args.cohort in ('control', 'profile'):
        nodes, workers = ['tests/test_native_u3k_profile.py::test_neutral_pre_reservation_diagnostic'], 1
        env['U3K_PROFILE'] = 'cprofile' if args.cohort == 'profile' else 'control'
    elif args.cohort == 'focused':
        if not args.node:
            raise ValueError('focused checks require exact nodes')
        nodes, workers = args.node, 2
    else:
        if args.node:
            raise ValueError('fixed cohort cannot replace its nodes')
        nodes, workers = selectors.nodes(args.cohort)
    if args.cohort.startswith('parity'):
        env['U3F_PARITY'] = '1'
    composition = json.loads(Path(env['U3K_MANIFEST']).read_bytes())
    tree = Path(composition['worktree'])
    for node in nodes:
        if not (tree / node.split('::')[0]).is_file():
            raise ValueError('selected node file is absent: ' + node)
    command = [sys.executable, '-S', '-P', '-B',
        str(ROOT / 'scripts/adhoc/run_native_u3k_20261109.py'),
        '--out', str(SCRATCH / args.label), '--workers', str(workers), *nodes]
    return subprocess.run(command, cwd=ROOT, env=env, timeout=3290).returncode


if __name__ == '__main__':
    raise SystemExit(main())
