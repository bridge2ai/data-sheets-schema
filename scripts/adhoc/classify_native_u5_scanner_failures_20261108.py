#!/usr/bin/env python3
"""Preserve U5 scanner failure attribution, 2026-11-08 (#4354).

Input: retained specificity JUnit under assigned U5 scratch. Output: fresh
classification JSON, including every nonpassing node and its original message.
This reads evidence only; no tests or production code are executed.
"""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u5-prep'


def main():
    source = SCRATCH / 'specificity/pytest.xml'
    output = SCRATCH / 'specificity-classification.json'
    if source.resolve(strict=True) != source or output.resolve() != output:
        raise ValueError('evidence must remain at literal assigned paths')
    raw = source.read_bytes()
    counts = {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
    groups, cases = {}, []
    for case in ET.fromstring(raw).iter('testcase'):
        state, detail = 'passed', None
        for tag, name in (('failure', 'failed'), ('error', 'errors'), ('skipped', 'skipped'):
            detail = case.find(tag)
            if detail is not None:
                state = name
                break
        counts[state] += 1
        if state == 'passed':
            continue
        message = detail.get('message', '')
        trace = detail.text or ''
        identity = case.get('classname', '') + '::' + case.get('name', '')
        alias = ('typed_audit.py:311' in message
                 and 'nested or copied receiver alias' in message)
        comparison = ('tests.test_native_u5_scanner_comparison::'
                      'test_scanner_before_after_retains_complete_arrays_or_explicit_blocker')
        if identity.startswith('tests.test_native_u5_scanner_comparison::'):
            proved = (identity == comparison and alias and '"before":' in message
                      and '"after":' in message and message.count('"returncode": 2') == 2)
            group = ('initial_comparison_incomplete_derivation_and_incomplete_input_U5_R5'
                     if proved else 'UNCLASSIFIED')
        elif 'shared selector call guards/order changed' in message:
            group = 'shared_selector_constructor_proof'
        elif alias:
            group = 'typed_audit_container_alias_proof'
        else:
            group = 'UNCLASSIFIED'
        row = groups.setdefault(group, {key: 0 for key in counts})
        row[state] += 1
        cases.append({'node': identity, 'state': state, 'group': group,
                      'message': message, 'trace': trace})
    result = {'source': str(source), 'source_sha256': hashlib.sha256(raw).hexdigest(),
              'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'counts': counts, 'groups': groups, 'cases': cases,
              'scope': 'source-derivation attribution; no runtime defect or acceptance inferred'}
    encoded = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(encoded)
    print(json.dumps({'path': str(output), 'sha256': hashlib.sha256(encoded).hexdigest(),
                      'counts': counts, 'groups': groups}, sort_keys=True))
    if 'UNCLASSIFIED' in groups:
        raise SystemExit('unclassified evidence retained; review before reporting completion')


if __name__ == '__main__':
    main()
