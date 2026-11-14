"""Reconcile D148 registration coverage after a bounded cohort, 2026-11-14.

Inputs: the isolated collection, immutable timed-out pytest log and optional
resumed JUnit cohort in assigned scratch. Outputs: an exact resume-node plan
and coverage ledger. A timeout remains a timeout; completed log events are
distinguished from JUnit results. No test, manifest or production check changes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-manifest-integration-20261114/continuation'


def read(path):
    return json.loads(path.read_bytes())


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def audit(scratch):
    assert scratch.resolve(strict=True) == SCRATCH
    original = scratch / 'final-registration'
    collection = scratch / 'registration-collection'
    resumed = scratch / 'final-registration-resumed'
    files = runpy.run_path(str(ROOT / 'scripts/adhoc/run_manifest_integration_checks_20261114.py'))['STAGES']['registration']
    collection_plan = read(collection / 'plan.json')
    original_plan = read(original / 'plan.json')
    assert collection_plan['source_commit'] == original_plan['source_commit']
    assert read(collection / 'outcome.json')['returncode'] == 0
    collection_log = (collection / 'pytest.log').read_text()
    expected_count = int(re.search(r'collecting \.\.\. collected (\d+) items', collection_log)[1])
    module = None
    roster = []
    for line in collection_log.splitlines():
        found = re.fullmatch(r'\s*<Module (test_[^>]+\.py)>', line)
        if found:
            module = 'tests/' + found[1]
            assert module in files, module
        found = re.fullmatch(r'\s*<Function ([^>]+)>', line)
        if found:
            assert module is not None
            roster.append(module + '::' + found[1])
    assert len(roster) == len(set(roster)) == expected_count
    outcome = read(original / 'outcome.json')
    assert outcome['returncode'] == 124 and outcome['interrupted'] == 'deadline'
    assert outcome['observed_surviving_pids'] == [] and outcome['observation_errors'] == []
    assert not (original / 'pytest.xml').exists(), 'use JUnit if the original cohort produced it'
    completed = {}
    for line in (original / 'pytest.log').read_text().splitlines():
        found = re.fullmatch(r'\[gw\d+\] \[\s*\d+%\] (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (tests/.*)', line.strip())
        if found:
            status, node = found[1], found[2].strip()
            assert node in roster and node not in completed, node
            completed[node] = status
    assert completed and set(completed.values()) == {'PASSED'}, 'a failure requires triage, not omission from the resume'
    pending = [node for node in roster if node not in completed]
    assert pending
    inputs = [collection / 'plan.json', collection / 'pytest.log', collection / 'outcome.json',
              original / 'plan.json', original / 'pytest.log', original / 'outcome.json']
    plan = {'initial_source_commit': original_plan['source_commit'],
            'collected': len(roster), 'completed_log_passes': len(completed),
            'pending_nodes': pending, 'input_pins': [pin(path) for path in inputs],
            'original_returncode': outcome['returncode'], 'original_seconds': outcome['seconds'],
            'original_cleanup_verified': outcome['cleanup_verified'],
            'scope': 'resume only unfinished cases; the initial cohort timeout remains recorded'}
    result = {'plan': plan, 'roster': roster, 'original_log_statuses': completed,
              'resumed': None, 'all_cases_completed': False, 'all_cases_passed': False}
    if (resumed / 'outcome.json').exists():
        resumed_outcome = read(resumed / 'outcome.json')
        resumed_plan = read(resumed / 'plan.json')
        assert resumed_plan['command'][-len(pending):] == pending
        statuses = {}
        xml = resumed / 'pytest.xml'
        if xml.exists():
            for case in ET.parse(xml).iter('testcase'):
                node = case.get('classname').replace('.', '/') + '.py::' + case.get('name')
                assert node in pending and node not in statuses, node
                child = next((n for n in case if n.tag in {'failure', 'error', 'skipped'}), None)
                statuses[node] = {'failure': 'FAILED', 'error': 'ERROR', 'skipped': 'SKIPPED'}.get(
                    child.tag if child is not None else None, 'PASSED')
        result['resumed'] = {'source_commit': resumed_plan['source_commit'],
                             'returncode': resumed_outcome['returncode'],
                             'cleanup_verified': resumed_outcome['cleanup_verified'],
                             'statuses': statuses,
                             'input_pins': [pin(path) for path in (resumed / 'plan.json', resumed / 'outcome.json')]
                                          + ([pin(xml)] if xml.exists() else [])}
        result['all_cases_completed'] = set(statuses) == set(pending) and resumed_outcome['cleanup_verified']
        result['all_cases_passed'] = (result['all_cases_completed']
                                      and set(statuses.values()) == {'PASSED'}
                                      and resumed_outcome['returncode'] == 0)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.scratch)
    plan_path = args.scratch / 'registration-resume-plan.json'
    if plan_path.exists():
        assert read(plan_path) == result['plan'], 'the frozen original cohort changed'
    else:
        plan_path.write_text(json.dumps(result['plan'], indent=2, sort_keys=True) + '\n')
    coverage_path = args.scratch / 'registration-coverage.json'
    coverage_path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'plan': str(plan_path), 'coverage': str(coverage_path),
                      'collected': result['plan']['collected'],
                      'completed_log_passes': result['plan']['completed_log_passes'],
                      'pending_nodes': result['plan']['pending_nodes'],
                      'all_cases_completed': result['all_cases_completed'],
                      'all_cases_passed': result['all_cases_passed']}, indent=2))


if __name__ == '__main__':
    main()
