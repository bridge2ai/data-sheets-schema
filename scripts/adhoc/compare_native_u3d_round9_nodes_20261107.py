#!/usr/bin/env python3
"""Compare U3-D R8 failures with R9 JUnit by exact node identity, 2026-11-07.

Inputs: retained R8 JUnit and final R9 cohort XMLs. Output: a JSON identity
ledger under scratch-native-u3d, including missing nodes, never count-only proof.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def read(path):
    result = {}
    for case in ET.parse(path).iter('testcase'):
        key = case.attrib['classname'] + '::' + case.attrib['name']
        status = next((name for name in ('error', 'failure', 'skipped')
                       if case.find(name) is not None), 'passed')
        if key in result:
            raise ValueError('duplicate node in JUnit: ' + key)
        result[key] = status
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, nargs='+', required=True)
    parser.add_argument('--recheck', type=Path, nargs='+', default=[],
                        help='Explicit later runs; archive every replaced baseline outcome.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before = read(args.before)
    after = {}
    for path in args.after:
        for key, status in read(path).items():
            if key in after and after[key] != status:
                raise ValueError('conflicting final cohort results for: ' + key)
            after[key] = status
    rechecked, replacements = {}, []
    for path in args.recheck:
        for key, status in read(path).items():
            if key in rechecked and rechecked[key] != status:
                raise ValueError('conflicting explicit recheck results for: ' + key)
            rechecked[key] = status
    for key, status in sorted(rechecked.items()):
        replacements.append({'node': key, 'baseline': after.get(key, 'not_in_cohort'),
                             'recheck': status})
        after[key] = status
    groups = {
        'former_setup_errors': {key: status for key, status in before.items() if status == 'error'},
        'former_lifecycle_failures': {key: status for key, status in before.items()
            if status == 'failure' and key.startswith('tests.test_native_shared_execution')},
        'all_former_nonpasses': {key: status for key, status in before.items()
                               if status in ('failure', 'error')},
    }
    result = {'kind': 'native_u3d_round9_node_identity_ledger', 'version': 1,
              'inputs': [{'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                         for path in (args.before, *args.after, *args.recheck)],
              'explicit_rechecks': replacements, 'groups': {}}
    for name, nodes in groups.items():
        rows = [{'node': key, 'before': nodes[key], 'after': after.get(key, 'missing')}
                for key in sorted(nodes)]
        result['groups'][name] = {'count': len(rows),
            'outcomes': dict(sorted(Counter(row['after'] for row in rows).items())), 'nodes': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps({name: {'count': group['count'], 'outcomes': group['outcomes']}
                      for name, group in result['groups'].items()}, sort_keys=True))


if __name__ == '__main__':
    main()
