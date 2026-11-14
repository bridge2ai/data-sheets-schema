#!/usr/bin/env python3
"""One bounded offline U3-M cohort, 2026-11-09.

Inputs: exact U3-J2 selector functions and U3M_MANIFEST. Outputs: one fresh
u3m evidence directory. Final public nodes are separate once-only measurements
with the retained passive observer. No providers or packet changes.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3/u3m'
spec = importlib.util.spec_from_file_location('u3m_retained_selectors',
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
    env['U3M_OBSERVE'] = '1' if args.cohort in {
        'metrics-canary', 'public-correction', 'public-omissions'} else '0'
    env['U3M_PROFILE'] = 'control'
    if args.cohort == 'metrics-canary':
        nodes, workers = ['tests/test_native_u3k_profile.py::test_profile_observer_canary'], 1
        env['U3M_PROFILE'] = 'control'
    elif args.cohort == 'canary':
        nodes, workers = ['tests/test_native_generation_frontdoor.py::test_validate_probe_uses_saved_bytes_and_never_runs_a_producer'], 1
        env['U3M_DEPENDENCY_CANARY'] = '1'
    elif args.cohort in ('d126-canary', 'd126-u4b'):
        parameter = 'historical-runtime' if args.cohort == 'd126-canary' else 'u4b-runtime'
        nodes, workers = ['tests/test_native_u4b_a5_producer_integration.py::test_d126_in_checkout_manifest_pins_every_native_instruction_delta[' + parameter + ']'], 1
        env['U3M_D126'] = '1'
    elif args.cohort == 'freshness':
        nodes, workers = ['tests/test_native_u3k_freshness_order.py'], 2
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
    composition = json.loads(Path(env['U3M_MANIFEST']).read_bytes())
    tree = Path(composition['worktree'])
    for node in nodes:
        if not (tree / node.split('::')[0]).is_file():
            raise ValueError('selected node file is absent: ' + node)
    command = [sys.executable, '-S', '-P', '-B',
        str(ROOT / 'scripts/adhoc/run_native_u3m_20261109.py'),
        '--out', str(SCRATCH / args.label), '--workers', str(workers), *nodes]
    if args.cohort in ('public-correction', 'public-omissions'):
        marker = SCRATCH / (args.cohort + '.once.json')
        with marker.open('x') as stream:
            json.dump(dict(command=command, source=composition['source_commit'], manifest=env['U3M_MANIFEST'], policy='once-only public measurement; do not retry'), stream, indent=2)
    return subprocess.run(command, cwd=ROOT, env=env, timeout=3290).returncode


if __name__ == '__main__':
    raise SystemExit(main())
