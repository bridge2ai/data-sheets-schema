"""Issues 6259/6258, 2026-11-15: summarize saved pytest XML for handoff.

Input: assigned scratch XML; output: JSON counts and exact failure messages.
"""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

scratch = Path(__file__).resolve().parents[2].parent / 'scratch-codex-controller-6259-20261115'
results = {}
for path in sorted(scratch.glob('*.xml')):
    root = ET.parse(path).getroot()
    suites = list(root.iter('testsuite'))
    failures = []
    for case in root.iter('testcase'):
        for kind in ('failure', 'error'):
            node = case.find(kind)
            if node is not None:
                failures.append(dict(name=case.get('classname') + '::' + case.get('name'),
                                     kind=kind, message=node.get('message'), text=node.text))
    results[path.name] = dict(
        counts={key: sum(int(s.get(key, 0)) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')},
        messages=dict(Counter(row['message'] for row in failures)), failures=failures)
print(json.dumps(results, indent=2).replace(chr(64), '\\u0040'))
