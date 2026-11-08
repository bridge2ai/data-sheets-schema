#!/usr/bin/env python3
"""Recover C6 validation with exact disjoint bounded cohorts, 2026-11-07.

Inputs: current C6 collection, original C roster, R5 XML timing hints.
Outputs: immutable six-part selection ledger and new r6-c-partN run evidence.
No test edits or timeout changes; no partial-dot result is credited.
The original deadline-stopped attempt remains intact. No network/native calls.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3c-r4'
LEDGER = SCRATCH / 'r6-c-partitions.json'
INPUTS = {'roster': SCRATCH / 'r6-plan.json',
          'collection': SCRATCH / 'r6-collect/pytest.log',
          'collection_outcome': SCRATCH / 'r6-collect/outcome.json',
          'collection_stability': SCRATCH / 'r6-collect/source-stability.json',
          'timing_hint': SCRATCH / 'r5-c-final/pytest.xml'}


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def head():
    return subprocess.check_output(['git', '--no-replace-objects', 'rev-parse', 'HEAD'],
        cwd=ROOT, env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'}, text=True).strip()


def key(node):
    parts = node.split('::')
    return ('.'.join([parts[0][:-3].replace('/', '.'), *parts[1:-1]]), parts[-1])


def plan():
    outcome = json.loads(INPUTS['collection_outcome'].read_bytes())
    stable = json.loads(INPUTS['collection_stability'].read_bytes())
    current = head()
    if (outcome['returncode'] != 0 or not outcome['cleanup_verified']
            or not stable['unchanged'] or stable['after']['head'] != current):
        raise RuntimeError('require completed collection on the current unchanged head')
    roster = set(json.loads(INPUTS['roster'].read_bytes())['groups']['c']['nodes'])
    selected = [line for line in INPUTS['collection'].read_text().splitlines()
                if '::' in line and line.split('::', 1)[0] in roster]
    if not selected or len(set(selected)) != len(selected):
        raise RuntimeError('empty or duplicate current C collection')
    timing = {}
    for case in ET.parse(INPUTS['timing_hint']).iter('testcase'):
        identity = (case.attrib['classname'], case.attrib['name'])
        if identity in timing:
            raise RuntimeError('duplicate historical timing identity')
        timing[identity] = max(float(case.attrib['time']), 0.005)
    if set(timing) != {key(node) for node in selected}:
        raise RuntimeError('historical C nodes and current collection differ')
    groups = [{'nodes': [], 'historical_weight_seconds': 0.0} for _ in range(6)]
    for node in sorted(selected, key=lambda value: (-timing[key(value)], value)):
        group = min(groups, key=lambda value: (value['historical_weight_seconds'], len(value['nodes'])))
        group['nodes'].append(node)
        group['historical_weight_seconds'] += timing[key(node)]
    selected_set = set(selected)
    union = set()
    rows = {}
    for index, group in enumerate(groups, 1):
        nodes = sorted(group['nodes'], key=selected.index)
        if union.intersection(nodes):
            raise RuntimeError('overlapping C cohorts')
        union.update(nodes)
        name = 'r6-c-part' + str(index)
        rows[name] = {**group, 'nodes': nodes,
                     'command': [sys.executable, '-S', '-P', '-B',
                         str(ROOT / 'scripts/adhoc/run_native_u3c_round4_20261107.py'),
                         '--out', str(SCRATCH / name), '--workers', '2', *nodes]}
    if union != selected_set:
        raise RuntimeError('C cohort coverage differs from collection')
    return {'head': current, 'selected_count': len(selected), 'partitions': rows,
            'inputs': {name: pin(path) for name, path in INPUTS.items()},
            'scope': 'Complete disjoint C node coverage; not one-process or full-order acceptance. '
                     'Historical timings schedule work only; partial deadline attempt earns no counts.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'run'))
    parser.add_argument('partition', nargs='?')
    args = parser.parse_args()
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise RuntimeError('invoke with physical dependency Python -S -P -B')
    value = plan()
    if args.action == 'plan':
        raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
        with LEDGER.open('xb') as stream:
            stream.write(raw)
        assert LEDGER.read_bytes() == raw
        print(json.dumps({'ledger': pin(LEDGER), 'head': value['head'],
                          'selected_count': value['selected_count'],
                          'partition_counts': {name: len(row['nodes'])
                                               for name, row in value['partitions'].items()}}, sort_keys=True))
        return 0
    if args.partition not in value['partitions']:
        parser.error('choose one explicit partition from the saved ledger')
    if json.loads(LEDGER.read_bytes()) != value:
        raise RuntimeError('current candidate/roster differs from saved ledger')
    return subprocess.call(value['partitions'][args.partition]['command'], cwd=ROOT)


if __name__ == '__main__':
    raise SystemExit(main())
