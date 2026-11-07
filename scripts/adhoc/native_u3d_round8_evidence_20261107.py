#!/usr/bin/env python3
"""Run and summarize offline U3-D round-eight checks, 2026-11-07.

Inputs: this source tree, preserved C/A roster and round-six D/B roster.
Outputs: new scratch-native-u3d/round8-* evidence and one digest manifest.
No network, provider, real native executable, or existing evidence mutation.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_u3d_round6_evidence_20261107 as prior

ROOT, BASE, EXEC = prior.ROOT, prior.BASE, prior.EXEC
NEW = ('native_shared_runtime_values', 'native_shared_gate_primitives',
       'native_shared_layer_split', 'native_shared_permission_split',
       'native_shared_consumer_census')


def roster(mode):
    if mode == 'canary':
        return ['tests/test_native_shared_gate_primitives.py::test_neutral_gate_primitive_is_accepted_by_the_unchanged_guard']
    if mode == 'd':
        return [f'tests/test_{name}.py' for name in (*prior.D_MODULES, *NEW)]
    if mode == 'b':
        path = ROOT / 'tests/test_native_u3b_reuse.py'
        return ['tests/test_native_u3b_reuse.py::' + node.name
                for node in ast.parse(path.read_text()).body
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')
                and node.name != 'test_native_typed_capture_and_receipt_reconstruction_smoke']
    if mode == 'ca':
        return prior.nodes('ca')
    if mode == 'collection':
        return ['tests']
    raise ValueError(mode)


def collect():
    result = {'head': prior.git('rev-parse', 'HEAD').decode().strip(),
        'excluded_execution_node': prior.FORBIDDEN_TEST,
        'scope': 'offline synthetic checks; no C stand-in or native launch', 'runs': {}}
    for plan in sorted(BASE.glob('round8-*/plan.json')):
        directory = plan.parent
        doc = json.loads(plan.read_bytes())
        outcome = json.loads((directory / 'outcome.json').read_bytes())
        assert outcome['cleanup_verified'] and outcome['worker']['source_origin_checks_passed']
        for key, file in [('tested_diff_sha256', 'tested.diff'),
                          ('tested_status_sha256', 'tested.status'),
                          ('tested_untracked_sha256', 'tested-untracked.json')]:
            assert doc[key] == prior.sha(directory / file)
        xml = ET.parse(directory / 'pytest.xml').getroot()
        cases = []
        for case in xml.iter('testcase'):
            failed = next((child for child in case if child.tag in ('failure', 'error')), None)
            skipped = any(child.tag == 'skipped' for child in case)
            cases.append({'node': case.get('classname', '') + '::' + case.get('name', ''),
                'state': failed.tag if failed is not None else ('skipped' if skipped else 'passed'),
                'message': None if failed is None else failed.get('message'),
                'detail': None if failed is None else failed.text,
                'properties': [dict(prop.attrib) for prop in case.iter('property')]})
        counts = {state: sum(row['state'] == state for row in cases)
                  for state in ('passed', 'failure', 'error', 'skipped')}
        collected = re.findall(r'(\d+) tests? collected', (directory / 'pytest.log').read_text())
        result['runs'][directory.name] = {'source_commit': doc['source_commit'],
            'seconds': outcome['seconds'], 'returncode': outcome['returncode'],
            'counts': counts, 'junit': [dict(item.attrib) for item in xml.iter('testsuite')],
            'collected': int(collected[-1]) if collected else None, 'testcases': cases,
            'artifacts': {name: prior.sha(directory / name) for name in (
                'plan.json', 'outcome.json', 'pytest-command.json', 'pytest.log', 'pytest.xml',
                'tested.diff', 'tested.status', 'tested-untracked.json', 'network.json',
                'origins-before.json', 'origins-after.json', 'subprocess-origins.json')}}
    prior.save(BASE / 'round8-evidence.json', result)
    print(json.dumps({name: {key: row[key] for key in ('counts', 'collected', 'returncode')}
        for name, row in result['runs'].items()}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('canary', 'd', 'b', 'ca', 'collection', 'collect'))
    parser.add_argument('--label')
    args = parser.parse_args()
    assert not os.path.lexists(EXEC / 'plans/native_quiet_window.lock'), 'quiet window active'
    assert prior.git('branch', '--show-current').decode().strip() == 'codex/native-u3d-integration-20261107'
    if args.mode == 'collect':
        collect()
        return
    label = args.label or args.mode
    assert label and all(char.isalnum() or char == '-' for char in label)
    nodes = roster(args.mode)
    assert prior.FORBIDDEN_TEST not in nodes and 'tests/test_native_u3b_reuse.py' not in nodes
    command = [str(prior.PYTHON), '-S', '-P', '-B',
        str(ROOT / 'scripts/adhoc/run_native_u3d_tests_20261107.py'),
        '--out', str(BASE / ('round8-' + label)), '--workers',
        '0' if args.mode in ('collection', 'canary') else '2']
    if args.mode == 'collection':
        command += ['--collect-only']
    raise SystemExit(subprocess.call(command + nodes, cwd=ROOT, env=prior.ENV))


if __name__ == '__main__':
    main()
