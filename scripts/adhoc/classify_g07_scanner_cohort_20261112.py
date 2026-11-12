#!/usr/bin/env python3
"""Classify retained G07 scanner/neutrality results, 2026-11-12.

Inputs: completed cohort plan, outcome and JUnit XML. Output: one fresh report
JSON under the report worktree handoffs. No test, scanner, project imports,
subprocess or network execution. Serves the native protected-packet G07 review.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


SIGNATURE = ('v2 envelope authority source changed: '
             'src/data_sheets_schema/native_execution_authority_v2.py')
REPORT_ROOT = Path(__file__).resolve().parents[2]
HANDOFFS = REPORT_ROOT / 'notes/development_efficiency_20261111/handoffs'
NEUTRALITY = ('tests/test_neutral_generation_schema.py', 'tests/test_profiles.py',
              'tests/test_external_dataset_onboarding.py')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cohort', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.parent.resolve(strict=True) != HANDOFFS or args.output.exists():
        raise ValueError('fresh output in assigned report handoffs required')
    raw = {name: (args.cohort / name).read_bytes()
           for name in ('plan.json', 'outcome.json', 'pytest.xml')}
    plan = json.loads(raw['plan.json'])
    outcome = json.loads(raw['outcome.json'])
    root = ET.fromstring(raw['pytest.xml'])
    counts, modules = Counter(), defaultdict(Counter)
    negatives, skips = [], []
    for case in root.iter('testcase'):
        last = case.attrib['classname'].split('.')[-1]
        classname = case.attrib['classname']
        module = classname.rsplit('.', 1)[0] if last.startswith('Test') else classname
        path = module.replace('.', '/') + '.py'
        node = path + ('::' + last if last.startswith('Test') else '') + '::' + case.attrib['name']
        detail = next((child for child in case if child.tag in ('failure', 'error', 'skipped')), None)
        status = detail.tag if detail is not None else 'passed'
        counts[status] += 1
        modules[path][status] += 1
        if detail is None:
            continue
        message = detail.attrib.get('message', '')
        trace = ''.join(detail.itertext())
        item = dict(nodeid=node, outcome=status, message=message,
                    trace_sha256=digest(trace.encode()))
        if status == 'skipped':
            item['reason'] = trace
            skips.append(item)
        else:
            item['classification'] = ('pre_existing_native_authority_scanner_pin_drift'
                                      if SIGNATURE in message and SIGNATURE in trace else 'unclassified')
            negatives.append(item)
    source = Path(plan['source_root'])
    source_files = ('src/data_sheets_schema/native_execution_authority_v2.py',
                    '.claude/skills/d4d-generation-specificity-audit/scan.py',
                    *NEUTRALITY, 'src/data_sheets_schema/schema_digest.py',
                    'src/data_sheets_schema/profiles.py')
    value = dict(
        kind='g07_scanner_neutrality_retained_result_classification',
        source_commit=plan['source_commit'], source_root=str(source),
        cohort=str(args.cohort), helper_sha256=digest(Path(__file__).read_bytes()),
        artifact_sha256={name: digest(data) for name, data in raw.items()},
        counts=dict(counts), module_counts={name: dict(values) for name, values in modules.items()},
        negative_count=len(negatives),
        cause_counts=dict(Counter(row['classification'] for row in negatives)),
        neutrality_negative_count=sum(sum(modules[name][status] for status in ('failure', 'error'))
                                      for name in NEUTRALITY),
        negatives=negatives, skips=skips,
        execution=dict(returncode=outcome['returncode'], seconds=outcome['seconds'],
                       cleanup_verified=outcome['cleanup_verified'],
                       source_origin_checks_passed=outcome['worker']['source_origin_checks_passed']),
        source_file_sha256={name: digest((source / name).read_bytes()) for name in source_files},
        classification_evidence=[
            'Every negative is classified by its own JUnit message and traceback, never aggregate counts.',
            'Scanner source contracts compare raw authority bytes at scan.py lines 13408-13415.',
            'The native parent already contains the changed authority bytes and old scanner pin.',
            'Expected integrated authority SHA256 is bfdb5c86feb4c071ebf17e6ececa8fd60f1bc23bda98fefd42c0c211ecd7511a.',
            'All three neutrality test files, schema_digest.py and profiles.py compare identical to both pinned main7ad8 and native1a137 by Git object diff.',
            'An earlier scanner refusal masks later assertions; no claim is made that all96 would pass after a pin repair.',
            'A separate full scanner exit2 is incomplete derivation, not clean output or empty accepted arrays.'
        ])
    encoded = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with args.output.open('xb') as stream:
        stream.write(encoded)
    if args.output.read_bytes() != encoded:
        raise ValueError('report persistence mismatch')
    print(json.dumps(dict(path=str(args.output), sha256=digest(encoded), counts=value['counts'],
                          modules=value['module_counts'], causes=value['cause_counts'],
                          neutrality_negative_count=value['neutrality_negative_count'])))


if __name__ == '__main__':
    main()
