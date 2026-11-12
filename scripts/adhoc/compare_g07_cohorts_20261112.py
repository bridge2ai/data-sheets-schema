#!/usr/bin/env python3
"""Compare exact retained G04/CI test identities with G07, 2026-11-12.

Inputs: retained JUnit XML and CI inventory; outputs: a JSON evidence ledger.
Only reads local evidence and writes the named report artifact. No test runs.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

DEV = Path(__file__).resolve().parents[2]
EXEC = DEV.parent
WT = EXEC / 'codex-native-main-integration-20261112'
TESTS = EXEC / 'scratch-native-main-integration-20261112/tests'
OUT = DEV / 'notes/development_efficiency_20261111/handoffs'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases(path):
    rows = []
    for case in ET.parse(path).getroot().iter('testcase'):
        parts = case.get('classname', '').split('.')
        for count in range(len(parts), 0, -1):
            file = '/'.join(parts[:count]) + '.py'
            if (WT / file).is_file():
                name = '::'.join([file, *parts[count:], case.get('name', '')])
                break
        else:
            raise ValueError('cannot map JUnit classname to test file: ' + str(parts))
        negative = next((item for item in case if item.tag in {'failure', 'error', 'skipped'}), None)
        rows.append({'nodeid': name, 'result': 'passed' if negative is None else negative.tag,
                     'message': '' if negative is None else negative.get('message', '')})
    return rows


def main():
    current = defaultdict(list)
    artifacts = []
    for path in sorted(TESTS.glob('*/pytest.xml')):
        plan = json.loads((path.parent / 'plan.json').read_bytes())
        artifacts.append({'path': str(path), 'sha256': sha(path), 'source': plan['source_commit']})
        for row in cases(path):
            current[row['nodeid']].append(dict(row, cohort=path.parent.name, source=plan['source_commit']))
    pairs = []
    for old, new, marker in (
        ('execution-merge', 'g07-execution', 'native_shared_generation_version'),
        ('shared-policy-merge', 'g07-shared-policy', 'native_shared_generation_version'),
        ('scanner-merge', 'g07-scanner-cohort', 'model-facing native command table lacks its derived native-only route'),
    ):
        path = WT / '.temp/native-main-integration/tests' / old / 'pytest.xml'
        prior = [row for row in cases(path) if row['result'] in {'failure', 'error'}]
        rows = []
        for row in prior:
            matches = [item for item in current.get(row['nodeid'], []) if item['cohort'] == new]
            rows.append(dict(row, protected_integration_cause=marker in row['message'], after=matches))
        pairs.append({'before': old, 'after': new, 'before_xml': str(path),
                      'before_sha256': sha(path), 'before_negatives': len(prior),
                      'merge_cause_negatives': sum(row['protected_integration_cause'] for row in rows),
                      'after_outcomes': dict(Counter(item['result'] for row in rows for item in row['after'])),
                      'merge_cause_after_outcomes': dict(Counter(item['result'] for row in rows
                          if row['protected_integration_cause'] for item in row['after'])),
                      'old_signature_still_present': sum(marker in item['message']
                          for row in rows if row['protected_integration_cause'] for item in row['after']),
                      'after_negative_messages': dict(Counter(item['message'] for row in rows
                          for item in row['after'] if item['result'] in {'failure', 'error'})),
                      'after_not_observed': sum(not row['after'] for row in rows), 'nodes': rows})
    inventory = OUT / 'lead-ci-run-42976790438-failures-20261112.json'
    ci = json.loads(inventory.read_bytes())
    identities = {}
    for row in ci['failures']:
        node = row['file'] + ('::' + row['node'] if row['node'] else '')
        identities.setdefault(node, {'nodeid': node, 'ci_class': row['class'],
                                    'ci_messages': [], 'local': current.get(node, [])})
        if row['message'] not in identities[node]['ci_messages']:
            identities[node]['ci_messages'].append(row['message'])
    result = {'kind': 'g07_exact_test_identity_comparison', 'artifacts': artifacts,
              'cohort_pairs': pairs, 'ci_inventory': str(inventory), 'ci_sha256': sha(inventory),
              'ci_nodes': list(identities.values()),
              'limitations': ['A local result does not establish a GitHub CI outcome.',
                             'Distinct cohorts and source commits are not pooled as a unique suite.',
                             'Missing local observations remain untested, not passed.']}
    path = OUT / 'codex-g07-cohort-comparison-20261112.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    assert json.loads(path.read_bytes()) == result
    print(path)
    print(sha(path))
    for row in pairs:
        print(json.dumps({key: row[key] for key in ('before', 'after', 'before_negatives',
            'merge_cause_negatives', 'after_outcomes', 'after_not_observed')}))


if __name__ == '__main__':
    main()
