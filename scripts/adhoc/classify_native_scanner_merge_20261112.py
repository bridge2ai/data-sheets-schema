#!/usr/bin/env python3
"""Read-only JUnit classification for the native/main merge cohorts, 2026-11-12.

Input: retained cohort pytest.xml; output: JSON on stdout only.
Serves the G04 integration handoff; imports no repository production code.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('xml', type=Path)
    parser.add_argument('--details', action='store_true')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    raw = args.xml.read_bytes()
    root = ET.fromstring(raw)
    counts = Counter()
    groups = defaultdict(list)
    for case in root.iter('testcase'):
        outcome = next((child for child in case if child.tag in {'failure', 'error', 'skipped'}), None)
        tag = outcome.tag if outcome is not None else 'passed'
        counts[tag] += 1
        if tag not in {'failure', 'error'}:
            continue
        text = ''.join(outcome.itertext())
        message = outcome.attrib.get('message', '')
        classname = case.attrib['classname']
        module, last = classname.rsplit('.', 1)
        prefix = (module.replace('.', '/') + '.py::' + last
                  if last.startswith('Test') else classname.replace('.', '/') + '.py')
        record = {'node': prefix + '::' + case.attrib['name'],
                  'classname': case.attrib['classname'], 'test': case.attrib['name'],
                  'outcome': tag, 'message': message}
        if args.details:
            record['text'] = text
        signatures = (
            'model-facing native command table lacks its derived native-only route',
            "RunSpec.__init__() got an unexpected keyword argument 'native_shared_generation_version'",
            'probe isolation root overlaps selected input/source/output authority',
        )
        key = next((s for s in signatures if s in text or s in message), message)
        classification = {
            signatures[0]: 'merge_protected_api_dependency',
            signatures[1]: 'merge_protected_api_dependency',
            signatures[2]: 'environmental_in_worktree_probe_isolation',
        }.get(key, 'unclassified')
        record['classification'] = classification
        groups[key].append(record)
    result = {'xml': str(args.xml), 'sha256': hashlib.sha256(raw).hexdigest(),
              'counts': dict(counts), 'negative_count': sum(len(rows) for rows in groups.values()),
              'groups': [{'cause_signature': key, 'count': len(rows),
                          'classifications': dict(Counter(row['classification'] for row in rows)),
                          'outcomes': dict(Counter(row['outcome'] for row in rows)),
                          'messages': dict(Counter(row['message'] for row in rows)),
                          'classes': dict(Counter(row['classname'] for row in rows)),
                          **({} if args.summary else {'nodes': rows})}
                         for key, rows in groups.items()]}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
