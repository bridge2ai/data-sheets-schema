#!/usr/bin/env python3
# Purpose: reconcile #5210 full-run failure and focused fixture-repair coverage.
# Inputs: two completed evidence roots and immutable tested Git heads.
# Outputs: fresh compact coverage JSON, preserving failure and source boundaries.
# Refs #5210/#5157; 2026-10-28. Offline evidence reads only; no tests/providers.
"""Distinct cases across named heads, never a claim of one green full-suite run."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
INITIAL = 'dc9ca46701e74e712bf1800fbda8542b84e4c91e'
FIXED = 'ad1f950df173f8ed07023faeff612feb32b4dec7'
MODULE = 'tests.test_report_admission'
CASE = (MODULE, 'test_chorus_wire_is_byte_identical_to_the_base_and_is_what_was_counted')
TEST_FILE = 'tests/test_report_admission.py'


def git(*args):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT, env=env)


def read_run(root, head, code):
    root = root.resolve(strict=True)
    raw = {name: (root / name).read_bytes() for name in
           ('outcome.json', 'pytest.xml', 'source-before.json', 'source-after.json')}
    outcome = json.loads(raw['outcome.json'])
    before, after = (json.loads(raw[name]) for name in ('source-before.json', 'source-after.json'))
    if (outcome['returncode'] != code or outcome['source_unchanged'] is not True
            or before != after or before['head'] != head or before['tracked_exact'] is not True):
        raise ValueError('run does not have the expected outcome and frozen source')
    passed, failed, seen = set(), set(), set()
    for case in ET.fromstring(raw['pytest.xml']).iter('testcase'):
        identity = (case.get('classname'), case.get('name'))
        if not all(identity) or identity in seen or any(case.find(tag) is not None for tag in ('skipped', 'error')):
            raise ValueError('ambiguous, skipped or errored case')
        seen.add(identity)
        (failed if case.find('failure') is not None else passed).add(identity)
    return passed, failed, {'root': str(root), 'head': head, 'outcome': outcome,
                           'raw_sha256': {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()}}


def fixture_ast():
    old = ast.parse(git('show', INITIAL + ':' + TEST_FILE))
    new = ast.parse(git('show', FIXED + ':' + TEST_FILE))
    def separate(tree):
        other, constants = [], {}
        for node in tree.body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id in {'BASE_WIRE_SHA256', 'HISTORICAL_F8_WIRE_SHA256'}):
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            else:
                other.append(ast.dump(node, include_attributes=False))
        return other, constants
    old_body, old_constants = separate(old)
    new_body, new_constants = separate(new)
    if (old_body != new_body or old_constants['BASE_WIRE_SHA256'] != new_constants['HISTORICAL_F8_WIRE_SHA256']
            or set(new_constants) != {'BASE_WIRE_SHA256', 'HISTORICAL_F8_WIRE_SHA256'}):
        raise ValueError('fixture change exceeds golden metadata or loses historical values')
    consumers = [node.name for node in new.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                 and any(isinstance(item, ast.Name) and item.id == 'BASE_WIRE_SHA256' for item in ast.walk(node))]
    if consumers != [CASE[1]]:
        raise ValueError('changed fixture is consumed outside the rerun case')
    return {'all_other_module_ast_unchanged': True, 'historical_values_preserved': True,
            'current_golden_consumers': consumers, 'historical_f8': old_constants['BASE_WIRE_SHA256'],
            'incoming_a13': new_constants['BASE_WIRE_SHA256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initial', type=Path, required=True)
    parser.add_argument('--fixed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    first, failures, initial = read_run(args.initial, INITIAL, 1)
    repaired, remaining, fixed = read_run(args.fixed, FIXED, 0)
    if len(first) != 236 or failures != {CASE} or repaired != failures or remaining or first & repaired:
        raise ValueError('unexpected failure/repair case partition')
    unchanged = ('src', 'data', '.claude', '.github', 'scripts/build_api_registrations.py',
                 'notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md')
    if git('diff', '--name-only', INITIAL, FIXED, '--', *unchanged).strip():
        raise ValueError('production/data/protected/decision changes require broader verification')
    changed_tests = git('diff', '--name-only', INITIAL, FIXED, '--', 'tests').decode().splitlines()
    if changed_tests != [TEST_FILE]:
        raise ValueError('unexpected other test changes')
    fixture = fixture_ast()
    unique = first | repaired
    modules = {name: sum(c == name or c.startswith(name + '.') for c, _ in unique) for name in
               ('tests.test_download.test_api_runner', 'tests.test_usage_ledger', MODULE)}
    result = {'format': 'wave5_5210_distinct_case_coverage_v1', 'initial': initial, 'fixed': fixed,
              'original_failure_retained': list(CASE), 'distinct_passing_cases': len(unique),
              'distinct_passes_by_module': modules, 'one_green_full_suite_claimed': False,
              'unchanged_scopes_between_tested_heads': list(unchanged),
              'only_changed_test': TEST_FILE, 'fixture_ast_verification': fixture,
              'scientific_acceptance': 'not_assessed'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(args.output)


if __name__ == '__main__':
    main()
