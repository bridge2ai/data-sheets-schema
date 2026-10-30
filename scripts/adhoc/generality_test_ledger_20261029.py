#!/usr/bin/env python3
# Purpose: summarize every G1 CI unit and retain exact failing node IDs for base replay.
# Inputs: external directory of JUnit/result files, argv[1]; outputs: summary.json,
# failed-nodeids.json. G1 N1 acceptance and failure classification, 2026-10-29.
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

root = Path(os.environ.get('G1_CHECKOUT_ROOT', Path(__file__).resolve().parents[2]))
directory = Path(sys.argv[1])
summary, failed = {}, set()
for path in sorted(directory.glob('*.xml')):
    doc = ET.parse(path)
    suites = doc.findall('.//testsuite')
    counts = {name: sum(int(s.get(name, 0)) for s in suites)
              for name in ('tests', 'failures', 'errors', 'skipped')}
    counts['passed'] = counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']
    cases = []
    for case in doc.findall('.//testcase'):
        problem = case.find('failure')
        if problem is None:
            problem = case.find('error')
        if problem is None:
            continue
        parts = case.get('classname', '').split('.')
        node = None
        for split in range(len(parts), 0, -1):
            file = '/'.join(parts[:split]) + '.py'
            if (root / file).is_file():
                node = '::'.join([file, *parts[split:], case.get('name')])
                break
        if node is None:
            node = case.get('name')
        cases.append({'nodeid': node, 'message': problem.get('message'),
                      'detail': problem.text})
        failed.add(node)
    result_path = path.with_name(path.stem + '.result.json')
    summary[path.stem] = {'counts': counts, 'failed': cases,
        'execution': json.loads(result_path.read_text()) if result_path.exists() else None}
(directory / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
(directory / 'failed-nodeids.json').write_text(json.dumps(sorted(failed), indent=2) + '\n')
for name, row in summary.items():
    print(name, row['counts'])
if len(sys.argv) > 2:
    for row in summary[sys.argv[2]]['failed']:
        print('FAIL', row['nodeid'], '\n', row['message'])
else:
    for node in sorted(failed):
        print('FAIL', node)
