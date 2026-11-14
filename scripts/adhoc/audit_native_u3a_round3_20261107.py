#!/usr/bin/env python3
"""Audit U3-A round-3 saved test evidence, 2026-11-07 (N1--N5).

Inputs: explicit bounded-driver evidence directories under scratch-native-u3a-r3.
Output: JSON summary with JUnit counts, source commits, census and artifact hashes.
No tests, imports of project code, network, deletion or provider calls.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2].parent / 'scratch-native-u3a-r3'


def audit(directory):
    if not directory.resolve().is_relative_to(ROOT) or directory.is_symlink():
        raise ValueError('evidence must be inside round-3 scratch')
    names = ('plan.json', 'outcome.json', 'pytest.xml', 'pytest.log', 'network.json',
             'origins-before.json', 'origins-after.json', 'subprocess-origins.json')
    raw = {name: (directory / name).read_bytes() for name in names}
    if not all(raw.values()):
        raise ValueError('empty evidence artifact')
    plan, outcome = (json.loads(raw[name]) for name in ('plan.json', 'outcome.json'))
    suites = list(ET.fromstring(raw['pytest.xml']).iter('testsuite'))
    counts = {key: sum(int(suite.get(key, '0')) for suite in suites)
              for key in ('tests', 'failures', 'errors', 'skipped')}
    census = [json.loads(prop.attrib['value'])
              for prop in ET.fromstring(raw['pytest.xml']).iter('property')
              if prop.attrib.get('name') == 'guard_census']
    expected_path = str(Path(plan['source_root']) / 'src') + ':' + plan['source_root']
    assert plan['workers'] <= 2 and plan['deadline_seconds'] == 3600
    assert plan['environment']['PYTHONPATH'] == expected_path
    assert outcome['cleanup_verified'] and not outcome['observed_surviving_pids']
    assert json.loads(raw['network.json'])['network_bind_denied']
    assert json.loads(raw['subprocess-origins.json'])['network']['network_bind_denied']
    return {'directory': str(directory), 'source_commit': plan['source_commit'],
            'counts': counts, 'returncode': outcome['returncode'],
            'seconds': outcome['seconds'], 'cleanup_verified': outcome['cleanup_verified'],
            'census': census,
            'sha256': {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('directories', nargs='+', type=Path)
    args = parser.parse_args()
    if not args.out.resolve().is_relative_to(ROOT):
        raise ValueError('summary must be inside round-3 scratch')
    result = {'runs': [audit(path) for path in args.directories]}
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    for row in result['runs']:
        print(row['directory'], row['counts'], 'exit', row['returncode'],
              'seconds', row['seconds'])
        for census in row['census']:
            print('census:', len(census), 'modules;',
                  sum(value == 'accepted' for value in census.values()), 'accepted')


if __name__ == '__main__':
    main()
