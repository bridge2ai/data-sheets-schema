#!/usr/bin/env python3
# Verify G2 reporter with legacy findings against retained evidence, 2026-11-14.
# Inputs: reporter, F1 ledger, interrupted cohort, current tracked source/test list.
# Outputs: fresh three-case closure-pin proof, interrupted-count check and roster.
# No project imports, pytest, report generation, production/test edits or commits.
import ast
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
TARGET = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
OUTPUT = SCRATCH / 'report-closure-pin-verification-after-legacy-findings'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def document(path, value):
    save(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def main():
    if OUTPUT.exists():
        raise ValueError('retain prior verification; output already exists')
    body = TARGET.read_bytes()
    tree = ast.parse(body, filename=str(TARGET))
    OUTPUT.mkdir()
    reviewed = OUTPUT / 'reviewed-report-source.py'
    save(reviewed, body)
    fixture = OUTPUT / 'fixture'
    fixture.mkdir()
    artifact = fixture / 'review-6224-final.json'
    save(artifact, b'{"finding":"retained scratch review"}\n')
    closure = {'findings': [], 'review_6224': pin(artifact), 'producer': pin(Path(__file__).resolve())}
    document(fixture / 'final-review-closure.json', closure)
    names = {'sha', 'pin', 'read_json', 'checked_pin', 'check_nested_pins', 'review_ledger',
             'counts', 'pytest_summary', 'junit', 'selected_paths', 'load_cohort', 'required_files'}
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in selected} == names
    namespace = {'Path': Path, 'hashlib': hashlib, 'json': json, 'Counter': Counter,
                 'datetime': datetime, 're': re, 'ET': ET, 'ROOT': ROOT,
                 'SCRATCH': fixture, 'REVIEW_FILES': (), 'FINDING_TESTS': {},
                 'source_equivalence': lambda *args: {'passed': True, 'basis': 'fixture assumption isolates interruption accounting'}}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(TARGET), 'exec'), namespace)
    review_roster, = [ast.literal_eval(node.value) for node in tree.body
                     if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == 'REVIEW_FILES'
                             for target in node.targets)]
    checked_documents = []
    for name in (*review_roster, 'proposal-6207-after-6217/proposal.json',
                 'review-6207-after-6217.json', 'issue-6217-proposal.json', 'issue-6225-proposal.json'):
        path = SCRATCH / name
        namespace['check_nested_pins'](json.loads(path.read_bytes()))
        checked_documents.append(pin(path))
    document(OUTPUT / 'saved-review-pin-checks.json', {
        'status': 'verified', 'reporter': pin(TARGET), 'producer': pin(Path(__file__).resolve()),
        'documents': checked_documents, 'scope': 'Recursive saved-document pin validation only; no report output or project execution.'})
    actual = namespace['review_ledger']([], {})
    assert actual['closure'] == closure and actual['findings'] == []
    cases = [{'case': 'valid_nested_artifact', 'passed': True, 'result': 'accepted'}]
    artifact.rename(fixture / 'review-original-retained.json')
    save(artifact, b'{"finding":"changed scratch review"}\n')
    try:
        namespace['review_ledger']([], {})
    except AssertionError as error:
        cases.append({'case': 'changed_nested_artifact', 'passed': True,
                      'result': 'refused', 'reason': str(error)})
    else:
        raise AssertionError('changed nested artifact was accepted')
    artifact.rename(fixture / 'review-changed-retained.json')
    try:
        namespace['review_ledger']([], {})
    except AssertionError as error:
        cases.append({'case': 'missing_nested_artifact', 'passed': True,
                      'result': 'refused', 'reason': str(error)})
    else:
        raise AssertionError('missing nested artifact was accepted')
    result = {'finding_id': 'G2-REVIEW-REPORT-F1', 'status': 'verified',
        'verified_entrypoint': 'review_ledger', 'reporter': pin(TARGET),
        'reviewed_source': pin(reviewed), 'producer': pin(Path(__file__).resolve()),
        'ledger': pin(SCRATCH / 'review-report.json'), 'cases': cases,
        'passed': len(cases), 'failed': 0, 'python': sys.version,
        'retained_fixture_bytes': [pin(path) for path in sorted(fixture.iterdir())],
        'scope': 'Pure report-function counterexamples only. No project imports, pytest or report output execution. Both altered fixture versions are retained; the expected file is intentionally absent after the missing-file case.'}
    document(OUTPUT / 'result.json', result)
    row = namespace['load_cohort'](SCRATCH / 'engine-admission', 'fixture-final-head', {})
    assert row['returncode'] == 2 and row['interrupted'] is True
    assert row['complete'] is row['eligible'] is False
    assert row['junit_entry_counts']['total'] == row['junit_entry_counts']['passed'] == 194
    assert row['pytest_summary']['counts'] == {'passed': 190}
    assert row['junit_entries_without_completed_log_outcome'] == 4
    assert row['counts']['passed'] == 0 and row['counts']['unconfirmed'] == 194
    assert all(case['status'] == 'unconfirmed' and case['junit_status'] == 'passed' for case in row['cases'])
    document(OUTPUT / 'interrupted-accounting.json', {
        'status': 'verified', 'reporter': pin(TARGET), 'producer': pin(Path(__file__).resolve()),
        'evidence': row['evidence'], 'returncode': row['returncode'],
        'interrupted': row['interrupted'], 'complete': row['complete'], 'eligible': row['eligible'],
        'junit_entry_counts': row['junit_entry_counts'], 'completed_log_summary': row['pytest_summary'],
        'counts': row['counts'], 'entries_without_completed_log_outcome': 4,
        'scope': 'Actual saved XML/log/outcome parsing. Source equivalence was deliberately assumed true to demonstrate interruption alone prevents acceptance; no claim about source equivalence is made here.'})
    baseline = json.loads((SCRATCH / 'baseline/index.json').read_bytes())
    head = git('rev-parse', 'HEAD')
    changed = git('diff', '--name-only', baseline['base'], head, '--', 'src', 'tests').splitlines()
    tracked = [name for name in git('ls-files', 'tests').splitlines()
               if Path(name).name.startswith('test_') and name.endswith('.py')]
    required = namespace['required_files'](changed, tracked)
    native = namespace['required_files'](['src/data_sheets_schema/native_execution.py'], tracked)
    document(OUTPUT / 'required-files.json', {
        'head': head, 'baseline': baseline['base'], 'reporter': pin(TARGET),
        'producer': pin(Path(__file__).resolve()), 'changed_source_and_tests': changed,
        'required_files': required, 'native_execution_exact_references': native,
        'source_pins': [pin(ROOT / name) for name in required],
        'selection': 'Exact identifier-token references to changed modules, plus changed test files. Separate module names with a shared prefix are not direct references.'})
    assert TARGET.read_bytes() == body
    print(json.dumps({'verification': pin(OUTPUT / 'result.json'),
                      'interrupted_accounting': pin(OUTPUT / 'interrupted-accounting.json'),
                      'required_files': pin(OUTPUT / 'required-files.json'),
                      'reporter': pin(TARGET), 'passed': len(cases), 'failed': 0}))


if __name__ == '__main__':
    main()
