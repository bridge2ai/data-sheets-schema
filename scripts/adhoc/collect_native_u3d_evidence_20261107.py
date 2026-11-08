#!/usr/bin/env python3
"""Collect explicit offline U3-D validation artifacts, D95, 2026-11-07.

Inputs: named external evidence directories produced by the retained runners.
Output: exclusive JSON with per-invocation outcomes, XML counts and SHA-256s.
No tests, imports of production code, network, commits or verdict synthesis.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EXECUTIONS = ROOT.parent
FILES = ('plan.json', 'outcome.json', 'worker-outcome.json', 'pytest.xml',
         'pytest.log', 'network.json', 'network-denied.sb', 'bootstrap.json',
         'origins-before.json', 'origins-after.json', 'subprocess-origins.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('directories', nargs='+')
    args = parser.parse_args()
    rows = []
    for name in args.directories:
        if Path(name).name != name or not name.startswith('native-u3d-'):
            raise ValueError('only explicitly named U3-D evidence directories')
        directory = EXECUTIONS / name
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError('missing or aliased evidence directory: ' + name)
        row = {'directory': str(directory), 'files': {}}
        for member in FILES:
            path = directory / member
            if not path.exists():
                continue
            raw = path.read_bytes()
            if not raw:
                raise ValueError('empty expected evidence: ' + str(path))
            row['files'][member] = {'bytes': len(raw),
                'sha256': hashlib.sha256(raw).hexdigest()}
            if member in ('plan.json', 'outcome.json', 'network.json'):
                row[member[:-5]] = json.loads(raw)
            if member == 'pytest.xml':
                cases = ET.fromstring(raw).findall('.//testcase')
                counts = {'cases': len(cases), 'failed': 0, 'errors': 0, 'skipped': 0, 'passed': 0}
                for case in cases:
                    if case.find('failure') is not None:
                        counts['failed'] += 1
                    elif case.find('error') is not None:
                        counts['errors'] += 1
                    elif case.find('skipped') is not None:
                        counts['skipped'] += 1
                    else:
                        counts['passed'] += 1
                row['junit_counts'] = counts
        row['completed'] = (directory / 'outcome.json').is_file()
        rows.append(row)
    value = {'scope': 'per-invocation evidence; repeated nodes are not unique-test totals',
             'invocations': rows}
    with args.out.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True); stream.write('\n')
    raw = args.out.read_bytes()
    print(json.dumps({'path': str(args.out), 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest()}))
    for row in rows:
        print(json.dumps({'directory': Path(row['directory']).name,
            'counts': row.get('junit_counts'), 'returncode': row.get('outcome', {}).get('returncode'),
            'completed': row['completed']}, sort_keys=True))


if __name__ == '__main__':
    main()
