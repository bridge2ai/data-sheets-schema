#!/usr/bin/env python3
"""Invoke the approved offline G07 runner on retained CI selectors, 2026-11-12.

Input: digest-pinned 27-node selector packet and a private composition label.
Output: ordinary runner artifacts in sibling scratch; no native/provider calls.
The caller must wait for every other cohort to finish before invocation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--composition', choices=['g07-b', 'g07-c'], required=True)
    parser.add_argument('--out-label', required=True)
    args = parser.parse_args()
    dev = Path(__file__).resolve().parents[2]
    executions = dev.parent
    repository = executions / 'codex-native-main-integration-20261112'
    scratch = executions / 'scratch-native-main-integration-20261112'
    packet = dev / 'notes/development_efficiency_20261111/handoffs/codex-g07-ci-selectors-20261112.json'
    raw = packet.read_bytes()
    if hashlib.sha256(raw).hexdigest() != '63d7d21ff6e03e68157083816e8559af80888360d3121c5929eccd65be92c1bd':
        raise ValueError('selector packet differs from reviewed bytes')
    nodes = json.loads(raw)['selector_shape_27']
    if len(set(nodes)) != 27 or any(not node.startswith('tests/test_') for node in nodes):
        raise ValueError('unexpected selector roster')
    if not args.out_label.startswith('g07-') or Path(args.out_label).name != args.out_label:
        raise ValueError('output label must be a new literal G07 cohort name')
    python = executions.parent / 'data-sheets-schema/.venv/bin/python'
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': '/var/empty', 'GIT_NO_LAZY_FETCH': '1'}
    command = [str(python), '-S', '-P', '-B',
        str(repository / 'scripts/adhoc/run_native_g07_tests_20261112.py'),
        '--tree', str(scratch / args.composition / 'tree'),
        '--out', str(scratch / 'tests' / args.out_label), '--workers', '2',
        '--timeout-seconds', '3600', *nodes]
    return subprocess.call(command, cwd=repository, env=env)


if __name__ == '__main__':
    raise SystemExit(main())
