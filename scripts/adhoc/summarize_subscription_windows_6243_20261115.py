"""Summarize issue 6243 JUnit comparisons, 2026-11-15.
Inputs: scratch base/candidate XML. Outputs: scratch summary JSON and stdout.
"""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-subscription-windows-6243-20261115'
report = {}
for mode in ('base', 'candidate'):
    tree = ET.parse(SCRATCH / (mode + '.xml'))
    counts, files, failures = Counter(), {}, []
    for case in tree.findall('.//testcase'):
        status = next((tag for tag in ('failure', 'error', 'skipped') if case.find(tag) is not None), 'passed')
        counts[status] += 1
        name = case.get('classname')
        files.setdefault(name, Counter())[status] += 1
        if status in ('failure', 'error'):
            failures.append({'test': name + '::' + case.get('name'), 'status': status,
                             'message': case.find(status).get('message')})
    report[mode] = {'counts': counts, 'files': files, 'failures': failures}
base = {row['test'] for row in report['base']['failures']}
candidate = {row['test'] for row in report['candidate']['failures']}
report['base_only_failures'] = sorted(base - candidate)
report['candidate_only_failures'] = sorted(candidate - base)
report['shared_failures'] = sorted(base & candidate)
raw = json.dumps(report, indent=2) + '\n'
(SCRATCH / 'test-summary.json').write_text(raw)
print(raw)
