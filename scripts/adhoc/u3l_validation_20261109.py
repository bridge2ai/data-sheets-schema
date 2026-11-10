#!/usr/bin/env python3
"""One bounded offline U3-L cohort, 2026-11-09.

Inputs: frozen U3L_MANIFEST and exact retained selectors or explicit focused
nodes. Outputs: a fresh u3l run directory. No providers, packet changes, or
automatic continuation beyond the D128 review gate.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3/u3l'
spec = importlib.util.spec_from_file_location('u3l_retained_selectors',
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
        raise ValueError('literal fresh output label required')
    env = os.environ.copy()
    if args.cohort == 'canary':
        if args.node:
            raise ValueError('canary selection is fixed')
        nodes = ['tests/test_native_u3l_scanner.py::test_integrated_profile_route_derives']
        workers = 1
        env['U3L_DEPENDENCY_CANARY'] = '1'
    elif args.cohort == 'focused':
        if not args.node:
            raise ValueError('focused cohort requires explicit nodes')
        nodes, workers = args.node, 2
    elif args.cohort == 'review-canary':
        if args.node:
            raise ValueError('review canary selection is fixed')
        nodes = ['tests/test_native_u3l_review_fixtures.py::test_retained_review_outcome[F0]']
        workers = 1
    elif args.cohort == 'review-fixtures':
        if args.node:
            raise ValueError('review fixture selection is fixed')
        nodes = ['tests/test_native_u3l_review_fixtures.py']
        workers = 2
    else:
        if args.node or args.cohort not in {
            'u4b', 'f2-specificity', 'f2-delegated', 'd128', 'hooks',
            'f2-core', 'parity-canary', 'parity'}:
            raise ValueError('unsupported U3-L cohort')
        nodes, workers = selectors.nodes(args.cohort)
    if args.cohort.startswith('parity'):
        env['U3F_PARITY'] = '1'
    composition = json.loads(Path(env['U3L_MANIFEST']).read_bytes())
    tree = Path(composition['worktree'])
    for node in nodes:
        if not (tree / node.split('::')[0]).is_file():
            raise ValueError('selected test file is absent: ' + node)
    command = [sys.executable, '-S', '-P', '-B',
        str(ROOT / 'scripts/adhoc/run_native_u3l_20261109.py'),
        '--out', str(SCRATCH / args.label), '--workers', str(workers), *nodes]
    return subprocess.run(command, cwd=ROOT, env=env, timeout=3290).returncode


if __name__ == '__main__':
    raise SystemExit(main())
