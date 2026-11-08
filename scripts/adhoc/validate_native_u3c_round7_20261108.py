#!/usr/bin/env python3
"""R7 offline regression roster and evidence summary, 2026-11-08.

Inputs: retained R6 C partitions/roster and R7 runner artifacts.
Outputs: new r7-plan.json, per-group artifacts, r7-summary.json in C scratch.
Serves the R9-4/Round 7 coordination brief; no GitHub or provider operation.
Historical rosters select work, never establish current passing evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3c-r4'
RUNNER = ROOT / 'scripts/adhoc/run_native_u3c_round4_20261107.py'
PREFIX = 'r7-complete-'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def plan():
    old = json.loads((SCRATCH / 'r6-plan.json').read_bytes())['groups']
    parts = json.loads((SCRATCH / 'r6-c-partitions.json').read_bytes())['partitions']
    groups = {name: old[name]['nodes'] for name in
              ('a-core', 'b-focused', 'b-schema-remaining', 'census', 'collect')}
    groups['focused'] = ['tests/test_native_shared_callback_preloading.py']
    groups['canary'] = ['tests/test_native_shared_callback_preloading.py::test_historical_worker_runs_preloaded_c_classifier[classifier]']
    groups.update({name.replace('r6-', ''): row['nodes'] for name, row in parts.items()})
    return {name: {'nodes': nodes, 'command': [sys.executable, '-S', '-P', '-B', str(RUNNER),
        '--out', str(SCRATCH / (PREFIX + name)), '--workers', '0' if name in ('collect', 'census') else '2',
        *(['--collect-only'] if name == 'collect' else []), *nodes]} for name, nodes in groups.items()}


def summary():
    result = {}
    for directory in sorted(SCRATCH.glob('r7-*')):
        if not directory.is_dir():
            continue
        row = {'artifacts': {p.name: pin(p) for p in directory.iterdir() if p.is_file()}}
        for name in ('outcome', 'source-stability'):
            path = directory / (name + '.json')
            if path.is_file():
                row[name] = json.loads(path.read_bytes())
        xml = directory / 'pytest.xml'
        if xml.is_file():
            cases = list(ET.parse(xml).iter('testcase'))
            row['counts'] = {'tests': len(cases), **{tag: sum(case.find(tag) is not None for case in cases)
                for tag in ('failure', 'error', 'skipped')}}
            row['failed'] = [{'class': case.get('classname'), 'name': case.get('name'),
                'reason': ''.join(child.text or '' for child in case if child.tag in ('failure', 'error'))}
                for case in cases if case.find('failure') is not None or case.find('error') is not None]
        result[directory.name] = row
    collection = SCRATCH / (PREFIX + 'collect/pytest.log')
    if collection.is_file():
        current = {line.strip() for line in collection.read_text().splitlines()
                   if line.startswith('tests/') and '::' in line}
        expected = {node for name, row in plan().items() if name.startswith('c-part') for node in row['nodes']}
        files = set(json.loads((SCRATCH / 'r6-plan.json').read_bytes())['groups']['c']['nodes'])
        actual = {node for node in current if node.split('::', 1)[0] in files}
        result['c_coverage'] = {'matches_retained_roster': actual == expected,
                              'collected': len(actual), 'selected': len(expected),
                              'new_file': sorted(node for node in current
                                  if node.startswith('tests/test_native_shared_callback_preloading.py::'))}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'run', 'summary'))
    parser.add_argument('groups', nargs='*')
    args = parser.parse_args()
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        parser.error('use physical dependency Python -S -P -B')
    if args.action in ('plan', 'summary'):
        value = plan() if args.action == 'plan' else summary()
        path = SCRATCH / (PREFIX + args.action + '.json')
        raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
        with path.open('xb') as stream:
            stream.write(raw)
        assert path.read_bytes() == raw
        print(json.dumps(pin(path)))
        return
    roster = plan()
    if json.loads((SCRATCH / (PREFIX + 'plan.json')).read_bytes()) != roster:
        raise RuntimeError('saved R7 roster differs')
    if not args.groups or any(group not in roster for group in args.groups):
        parser.error('name explicit saved groups')
    for group in args.groups:
        print('START ' + group, flush=True)
        code = subprocess.call(roster[group]['command'], cwd=ROOT)
        print('END ' + group + ': ' + str(code), flush=True)
        if not (SCRATCH / (PREFIX + group) / 'outcome.json').is_file():
            # In particular, do not repoll a quiet-window refusal by starting
            # successive groups. Leave the lock and resume only after 60 s.
            raise SystemExit(code or 125)
        if code not in (0, 1):
            raise SystemExit(code)


if __name__ == '__main__':
    main()
