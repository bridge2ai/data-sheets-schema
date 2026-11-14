#!/usr/bin/env python3
"""Integrate retained lifecycle failures into the G2 reporter, 2026-11-14.

Inputs: frozen reporter and retained retention-stability ledger. Outputs: exclusive
before/revision snapshots in scratch and bounded reporter edits. No final report,
closure, project import, test, probe, source/test edit or commit is executed.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
REPORTER = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
OUT = SCRATCH / 'retention-stability-report-20261114'
BEFORE_SHA = 'de0ceb63a6e6bd672f8f839011c918786003275e246c373e64351692e07e5539'
LEDGER_SHA = 'a4a88048b816e0f69fecb61a803cb3d6f054cb93e9d15677be38e9f457a16a40'

DIAGNOSTIC = r'''
def retention_diagnostic(head):
    """Bind the separate one-node diagnostic without granting acceptance."""
    directory = SCRATCH / 'retention-stability-diagnostic'
    names = {'command': 'diagnostic.command.json', 'log': 'diagnostic.pytest.log',
             'junit': 'diagnostic.junit.xml', 'outcome': 'diagnostic.outcome.json'}
    file = 'tests/test_native_incomplete_retention.py'
    function = 'test_public_failed_attempt_retains_records_and_reads_back_exactly[False]'
    node = file + '::' + function
    helper = ROOT / 'scripts/adhoc/diagnose_g2_retention_stability_20261114.py'
    base = ROOT / 'scripts/adhoc/run_g2_checks_20261114.py'
    helper_commit = 'af8730f2e1b2bf848dbe171f54e32c7d295dd88e'
    helper_sha = '81e551ae57142acb2dfabc212f706a929a3ff6f82bf07da873b2e3703b3e8d46'
    source_files = ('tests/test_native_incomplete_retention.py',
        'tests/test_native_shared_execution.py', 'tests/native_shared_fixture.py',
        'src/data_sheets_schema/native_shared_selection.py',
        'src/data_sheets_schema/schema_snapshot.py', 'src/data_sheets_schema/schema_view.py')
    path = directory / names['command']
    command = read_json(path)
    command_pin = pin(path)
    schedule = ['-n', '4', '--dist', 'load', '--maxschedchunk=1']
    argv = [str(ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'),
            '-m', 'pytest', '-q', '-p', 'no:cacheprovider', node, '--showlocals', *schedule,
            '--basetemp=' + str(directory / 'cases'), '--junitxml=' + str(directory / names['junit'])]
    expected_env = {'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1',
                    'PYTHONPYCACHEPREFIX': str(directory / 'pycache'), 'TMPDIR': str(directory)}
    assert command['kind'] == 'g2_retention_stability_diagnostic'
    assert command['diagnostic_only'] is True and command['acceptance_evidence'] is False
    assert command['selected_node'] == node and command['command'] == argv
    assert command['cwd'] == str(ROOT) and command['destination'] == str(directory)
    assert command['environment'] == expected_env and command['scheduling'] == schedule
    assert command['output_names'] == names and command['source_scope'] == list(SOURCE_SCOPE)
    assert command['pytest_environment_overrides_absent'] is True
    assert command['source_inventory']['ignored_and_hidden_files_included'] is True
    assert command['source_inventory']['selected_paths'] == [file]
    assert command['head'] == helper_commit
    assert checked_pin(command['producer']) == pin(helper)
    assert command['producer']['sha256'] == helper_sha
    assert sha(git('show', helper_commit + ':' + helper.relative_to(ROOT).as_posix())) == helper_sha
    assert checked_pin(command['base_runner']) == pin(base)
    assert command['base_runner']['sha256'] == 'dff66b0c12df58b65c9e1a7b395cccf472bf040edbe86fec193e727b46934675'
    assert command['source_pins'] == [pin(ROOT / name) for name in source_files]
    equivalent = source_equivalence(command['head'], head)
    assert equivalent['passed'], 'diagnostic source is not equivalent to final source'
    assert not git('diff', '--name-only', 'HEAD', '--', *SOURCE_SCOPE)
    result = {'diagnostic_only': True, 'acceptance_evidence': False,
        'whole_file_coverage': False, 'closes_retention_finding': False,
        'status': 'pending; no completion result recorded', 'selected_node': node,
        'command': command, 'evidence': {'command': command_pin},
        'helper_commit': helper_commit, 'source_equivalence': equivalent,
        'limitations': ['One diagnostic node cannot satisfy whole-file or source acceptance.',
            'Original normal completed lifecycle failures remain open regardless of this diagnostic result.',
            'A diagnostic traceback cannot reconstruct the original failing observed metadata tuple.']}
    outcome_path = directory / names['outcome']
    if not outcome_path.is_file():
        # A running log or partially written JUnit is deliberately not read or pinned.
        return result
    outcome = read_json(outcome_path)
    check_nested_pins(outcome)
    assert outcome['kind'] == command['kind'] and outcome['diagnostic_only'] is True
    assert outcome['acceptance_evidence'] is False and outcome['selected_node'] == node
    assert outcome['command_evidence'] == command_pin and outcome['head'] == command['head']
    for key in ('producer', 'base_runner', 'source_pins'):
        assert outcome[key] == command[key]
    code = outcome['returncode']
    assert isinstance(code, int) and not isinstance(code, bool)
    assert outcome['normal_pytest_completion'] is (code in (0, 1))
    assert isinstance(outcome['seconds'], (int, float)) and outcome['seconds'] >= 0
    result['evidence']['outcome'] = pin(outcome_path)
    result.update(outcome=outcome, returncode=code, cases=[], junit_entry_counts=None,
                  pytest_summary=None, missing_completion_artifacts=[])
    retained = []
    for key in ('log', 'junit'):
        artifact = directory / names[key]
        if artifact.is_file():
            record = pin(artifact)
            result['evidence'][key] = record
            if record['bytes']:
                retained.append(record)
        else:
            result['missing_completion_artifacts'].append(names[key])
    assert outcome['artifacts'] == retained
    if 'log' in result['evidence']:
        text = (directory / names['log']).read_text(errors='replace')
        result['pytest_summary'] = pytest_summary(text)
        result['log_reports_interruption'] = bool(re.search(r'KeyboardInterrupt|Interrupted:', text))
    if 'junit' in result['evidence'] and outcome['case_count_parse_error'] is None:
        rows, suites = junit(directory / names['junit'])
        assert len(rows) == 1 and rows[0]['classname'] == file[:-3].replace('/', '.')
        assert rows[0]['name'] == function
        raw_counts = counts(rows)
        assert outcome['counts'] == {key: raw_counts[key] for key in ('total', 'failed', 'error', 'skipped')}
        assert outcome['one_selected_case_reported'] is True
        result['junit_entry_counts'], result['suites'] = raw_counts, suites
        if code not in (0, 1) or result.get('log_reports_interruption'):
            rows = [{**row, 'status': 'unconfirmed'} if row['status'] == 'passed' else row for row in rows]
        result['cases'] = rows
    else:
        assert outcome['counts'] is None and outcome['one_selected_case_reported'] is False
    result['counts'] = counts(result['cases'])
    normal = (outcome['normal_pytest_completion'] and not result['missing_completion_artifacts']
              and outcome['case_count_parse_error'] is None and bool(result['cases'])
              and not result.get('log_reports_interruption'))
    result['status'] = ('completed single diagnostic; not acceptance' if normal
                        else 'incomplete diagnostic; not acceptance')
    assert pin(path) == command_pin and pin(outcome_path) == result['evidence']['outcome']
    return result

'''


def pin(path):
    raw = Path(path).read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw
    return pin(path)


def change(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


def main():
    assert not OUT.exists(), 'preserve prior reporter integration'
    before = REPORTER.read_text()
    assert pin(REPORTER)['sha256'] == BEFORE_SHA
    ledger = SCRATCH / 'review-retention-stability.json'
    assert pin(ledger)['sha256'] == LEDGER_SHA
    after = change(before, "'review-engine-freshness.json')", "'review-engine-freshness.json', 'review-retention-stability.json')")
    after = change(after,
        "        findings.extend(document.get('findings', [document] if 'finding_id' in document or 'id' in document else []))",
        "        findings.extend(document.get('findings', [document] if 'finding_id' in document or 'id' in document else []))\n"
        "        findings.extend(document.get('producer_review_findings', []))")
    after = change(after,
        "        withdrawn = identity == 'G2-REVIEW-6217-F3'",
        "        if identity == 'G2-REVIEW-RETENTION-STABILITY-F1':\n"
        "            closed = False  # A single diagnostic never closes the original whole-file failure.\n"
        "        withdrawn = identity == 'G2-REVIEW-6217-F3'")
    after = change(after,
        "                else 'verified correction; lead filing status retained' if closed",
        "                else 'open; original normal completed cohort retained (3 failed, 26 passed, exit 1); offending path/metadata field and cause unknown; diagnostic is not acceptance; lead filing required'\n"
        "                    if identity == 'G2-REVIEW-RETENTION-STABILITY-F1'\n"
        "                else 'producer traceback-header parser correction verified against all three retained failures; original fixture failure remains open; lead filing required'\n"
        "                    if closed and identity == 'G2-REVIEW-RETENTION-LEDGER-F1'\n"
        "                else 'producer traceback-header parser correction retained; verification pending; original fixture failure remains open; lead filing required'\n"
        "                    if identity == 'G2-REVIEW-RETENTION-LEDGER-F1'\n"
        "                else 'verified correction; lead filing status retained' if closed")
    after = change(after, '\ndef clean_text(value):', '\n' + DIAGNOSTIC + '\ndef clean_text(value):')
    after = change(after,
        "    inventory_path = SCRATCH / 'runner-inventory-verification/result.json'",
        "    diagnostic = retention_diagnostic(head)\n    inventory_path = SCRATCH / 'runner-inventory-verification/result.json'")
    after = change(after, "'report-closure-pin-verification-after-engine-freshness/result.json'",
                   "'report-closure-pin-verification-after-retention-stability/result.json'")
    after = change(after, "        'review_ledger': ledger, 'report_producer': pin(Path(__file__).resolve()),",
                   "        'review_ledger': ledger, 'report_producer': pin(Path(__file__).resolve()),\n"
                   "        'retention_stability_diagnostic': diagnostic,")
    anchor = "    lines += ['', '6207 proposal: `"
    assert after.count(anchor) == 1
    insertion = "    lines += ['', 'Retention diagnostic: ' + diagnostic['status'] + '; node `' + diagnostic['selected_node']\n"
    insertion += "        + '`; exit ' + str(diagnostic.get('returncode')) + '. Original lifecycle failures remain open; this node is never whole-file acceptance.']\n"
    after = after.replace(anchor, insertion + anchor)
    old_tree, new_tree = ast.parse(before), ast.parse(after)
    old_functions = {node.name: ast.dump(node, include_attributes=False) for node in old_tree.body if isinstance(node, ast.FunctionDef)}
    new_functions = {node.name: ast.dump(node, include_attributes=False) for node in new_tree.body if isinstance(node, ast.FunctionDef)}
    assert set(new_functions) - set(old_functions) == {'retention_diagnostic'}
    assert all(new_functions[name] == value for name, value in old_functions.items() if name not in ('main', 'review_ledger'))
    assert next(ast.dump(node, include_attributes=False) for node in old_tree.body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'SOURCE_SCOPE' for target in node.targets)) == next(
        ast.dump(node, include_attributes=False) for node in new_tree.body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'SOURCE_SCOPE' for target in node.targets))
    OUT.mkdir()
    before_pin = save(OUT / 'before-reporter.py', before.encode())
    REPORTER.write_text(after)
    assert REPORTER.read_text() == after
    result = {'finding_id': 'G2-REVIEW-RETENTION-STABILITY-F1', 'review': pin(ledger),
        'producer': pin(Path(__file__).resolve()), 'before': before_pin, 'after': pin(REPORTER),
        'acceptance_and_source_scope_functions_unchanged': True,
        'diagnostic_cannot_close_finding': True, 'final_report_executed': False,
        'scope': 'Retain normal completed lifecycle failures and producer parser finding; bind a separate diagnostic without any discovery or acceptance exception.'}
    save(OUT / 'revision.json', (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
