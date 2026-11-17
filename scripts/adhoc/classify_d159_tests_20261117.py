"""Classify saved D159 pytest reports without rerunning or changing tests.

Inputs: scratch JUnit reports. Output: evidence/test-classification.json with
per-case failures, pin-refusal groups and counts for the lead, 2026-11-17.
"""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
scratch = root.parent / 'scratch-d159-limits-20261117'
reports = []
for path in sorted(scratch.glob('rerun-*/*/results/*.xml')):
    tree = ET.parse(path)
    suites = list(tree.getroot().iter('testsuite'))
    counts = {key: sum(int(s.get(key, '0')) for s in suites)
              for key in ['tests', 'failures', 'errors', 'skipped']}
    failures = []
    for case in tree.getroot().iter('testcase'):
        for kind in ['failure', 'error']:
            for problem in case.findall(kind):
                body = problem.text or ''
                message = problem.get('message', '')
                pin = ('frozen native controller bytes changed:' in body
                       or ('CONTROL_SHA' in body and 'sha256' in body))
                category = 'pin-refusal' if pin else 'other'
                if 'process environment verification pin bound exceeded' in body:
                    category = 'environment-pin-count-bound'
                failures.append({'node': case.get('classname', '')+'::'+case.get('name', ''),
                    'kind': kind, 'category': category,
                    'message': message, 'traceback': body})
    reports.append({'xml': str(path), 'counts': counts,
        'categories': dict(Counter(row['category'] for row in failures)), 'failures': failures})
text = json.dumps(reports, indent=2).replace(chr(64), '[at]')+'\n'
target = scratch / 'evidence/test-classification.json'
target.write_text(text)
print(target)
for report in reports:
    print(json.dumps({key: report[key] for key in ['xml', 'counts', 'categories']}))
    for row in report['failures']:
        if row['category'] == 'other':
            print((row['node']+': '+row['message']).replace(chr(64), '[at]'))
