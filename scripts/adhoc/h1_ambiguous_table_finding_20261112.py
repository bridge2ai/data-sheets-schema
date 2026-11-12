#!/usr/bin/env python3
"""Classify H1's two ambiguous-table failures, 2026-11-12.
Inputs: frozen Git source objects and retained H1 JUnit evidence. Output: one
new coordination JSON report. AST/read-only Git only; no tests or imports of
scanner/native/project code, no network, no production edit. Local H1 finding.
"""
from __future__ import annotations
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
REPO = EXEC / 'codex-native-main-integration-20261112'
PRIVATE = EXEC / 'scratch-native-h1-scanner-20261112/h1-b/tree'
COHORT = EXEC / 'scratch-native-h1-scanner-20261112/tests/h1-scanner-cohort'
OUT = ROOT / 'notes/development_efficiency_20261111/handoffs/codex-h1-ambiguous-table-finding-20261112.json'
SCAN = '.claude/skills/d4d-generation-specificity-audit/scan.py'
TEST = 'tests/test_native_u1_scanner_contracts.py'
TEST_NAME = 'test_model_named_table_ambiguous_argv_alias_refuses'
REFS = {
 'native_test_introduction': '85ff9bbff76d96f29ae61bc3528f682d92154261',
 'main_before_narrowing': 'b85ac0fb7843866aa767f50e3e2e889ac706f8ba',
 'main_refusal_narrowing': 'a939fed2eeddc1a6487269230be8b97dde8e6863',
 'main_round3': '2a5db4ac5c5f18d1397a4b0aaa17a5e1e13a4cd7',
 'main_pr5665_merge': '8b7f58913f4dec394580697719e0b6a8a31514a2',
 'native_parent': '1a137b58860416a31618de44173180d021dfcc61',
 'main_parent': '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1',
 'integration_merge': 'b11931410305569aba30b0f593193ae894bd0dc7',
 'prepin_candidate': '5d63d0a77dc43c064cfc2b376355f98009dd5b6e',
 'pin_update': '66fecb7be53aea49e371e224593203990f33763e',
 'cohort_source_parent': '8a00bb828d9df29bfedda3b6745121dc746b6742',
 'tested_composition': '3a582243c4277934415bceb92cb888d617fd7a14',
}
FUNCTIONS = ('_model_command_tables', 'discover_model_commands', '_argv_runs', '_run_module_target')
COMMANDS = []
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(repo, *parts, retain=False):
    command = ['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never', '-c', 'core.fsmonitor=false', '-C', str(repo), *parts]
    result = subprocess.run(command, env=ENV, capture_output=True, check=True)
    row = dict(argv=command, returncode=result.returncode,
               stdout_sha256=sha(result.stdout), stdout_bytes=len(result.stdout), stderr=result.stderr.decode())
    if retain:
        row['stdout'] = result.stdout.decode()
    COMMANDS.append(row)
    return result.stdout


def node_parts(raw, names):
    lines = raw.splitlines(keepends=True)
    result = {}
    for node in ast.parse(raw).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            start = min([node.lineno] + [item.lineno for item in node.decorator_list])
            text = b''.join(lines[start-1:node.end_lineno])
            normalized = ast.dump(node, include_attributes=False).encode()
            result[node.name] = dict(source_sha256=sha(text), normalized_ast_sha256=sha(normalized),
                                     start_line=start, def_line=node.lineno, end_line=node.end_lineno,
                                     source=text.decode())
    return result


def main():
    if OUT.exists():
        raise SystemExit('refusing to overwrite prior finding evidence')
    snapshots = {}
    for label, commit in REFS.items():
        repo = PRIVATE if label == 'tested_composition' else REPO
        raw = git(repo, 'show', commit + ':' + SCAN)
        entry = dict(commit=commit, repository=str(repo), scanner_sha256=sha(raw),
                     functions=node_parts(raw, FUNCTIONS))
        roster = git(repo, 'ls-tree', commit, '--', TEST).decode()
        entry['test_file_present_in_commit'] = bool(roster.strip())
        if roster.strip():
            test = git(repo, 'show', commit + ':' + TEST)
            entry['test_file_sha256'] = sha(test)
            entry['test'] = node_parts(test, (TEST_NAME,))[TEST_NAME]
        snapshots[label] = entry
    comparisons = []
    for left, right in (('native_parent', 'main_parent'), ('main_parent', 'integration_merge'),
                        ('integration_merge', 'prepin_candidate'), ('prepin_candidate', 'pin_update'),
                        ('pin_update', 'tested_composition')):
        rows = {}
        for name in FUNCTIONS:
            a, b = snapshots[left]['functions'][name], snapshots[right]['functions'][name]
            rows[name] = dict(exact_source_equal=a['source_sha256'] == b['source_sha256'],
                              normalized_ast_equal=a['normalized_ast_sha256'] == b['normalized_ast_sha256'])
        comparisons.append(dict(before=left, after=right, functions=rows,
            test_exact_equal=(snapshots[left].get('test', {}).get('source_sha256') == snapshots[right].get('test', {}).get('source_sha256'))
                if 'test' in snapshots[left] and 'test' in snapshots[right] else None))
    for label in ('native_test_introduction', 'main_refusal_narrowing', 'main_round3', 'main_pr5665_merge', 'integration_merge', 'pin_update'):
        git(REPO, 'show', '--format=fuller', '--stat', REFS[label], retain=True)
    git(REPO, 'log', '--format=%H %P %s', '-S', 'ambiguous argv alias:', REFS['main_parent'], '--', SCAN, retain=True)
    git(REPO, 'diff', REFS['prepin_candidate'], REFS['pin_update'], '--', SCAN, retain=True)
    resolution = git(REPO, 'show', REFS['integration_merge'] + ':scripts/adhoc/resolve_native_main_integration_20261112.py', retain=True)
    git(REPO, 'merge-base', '--is-ancestor', REFS['main_refusal_narrowing'], REFS['main_parent'])
    git(REPO, 'merge-base', '--is-ancestor', REFS['main_parent'], REFS['prepin_candidate'])
    raw_xml = (COHORT / 'pytest.xml').read_bytes()
    document = ET.fromstring(raw_xml)
    suites = [dict(node.attrib) for node in document.iter('testsuite')]
    failures = []
    for case in document.iter('testcase'):
        failure = case.find('failure')
        if failure is not None:
            failures.append(dict(testcase=dict(case.attrib), failure=dict(failure.attrib), text=failure.text))
    if len(failures) != 2 or not all(TEST_NAME in row['testcase']['name'] for row in failures):
        raise ValueError('retained cohort failure roster differs')
    retained = {}
    for name in ('plan.json', 'outcome.json', 'worker-outcome.json', 'pytest-command.json'):
        raw = (COHORT / name).read_bytes()
        retained[name] = dict(path=str(COHORT / name), sha256=sha(raw), value=json.loads(raw))
    report = dict(
        finding='H1 ambiguous named command-table alias contract mismatch',
        status='open_local_finding_no_code_change', created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        helper=str(Path(__file__).resolve()), helper_sha256=sha(Path(__file__).read_bytes()),
        scope='Read-only historical source/AST comparison and parsing of existing JUnit; no new test/scanner execution.',
        observed=dict(path=str(COHORT / 'pytest.xml'), sha256=sha(raw_xml), suites=suites, failures=failures,
                      totals=dict(passed=740, failed=2, skipped=9, collected=751), retained=retained),
        snapshots=snapshots, comparisons=comparisons,
        static_call_path=[
          'The two tests create only src/data_sheets_schema/table_fixture.py with a named COMMANDS mapping and two complete literal argv alternatives.',
          'Surfaces.add marks that fixture native_agentic/model_facing; discover_model_commands parses it and selects the marked approach.',
          'The derive_native_shared_route call is conditional on rel == src/data_sheets_schema/native_shared_render.py. table_fixture.py does not take that path; no authority digest is read.',
          'Old _model_command_tables.literal saw two args bindings, recursively detected -m and raised ambiguous argv alias before target lookup.',
          'Current record_bindings accumulates both assignments. literals resolves every complete branch into argv tuples; the refusal triggers only when a branch cannot resolve while another contains literal -m.',
          'Both supplied parameter cases resolve completely. check_m_operands validates the two literal module operands, then _argv_runs asks _run_module_target to locate them.',
          'The test creates neither referenced second_command nor third_command module. Module lookup returns None, no import closure is added, and discover_model_commands returns an empty mapping. This last sequence is static interpretation, consistent with the retained DID NOT RAISE evidence, not a fresh execution.'
        ],
        history_conclusion={
          'test_contract_origin': REFS['native_test_introduction'],
          'main_behavior_change': REFS['main_refusal_narrowing'],
          'main_intent': 'Commit explicitly narrows command-table refusals to unresolvable argv slots in sequences containing literal -m, addressing #5681 false refusals. This is recorded intent, not inferred motive.',
          'main_merge': REFS['main_pr5665_merge'],
          'native_integration': REFS['integration_merge'],
          'integration_resolution': 'Saved resolution helper takes main for all nine scanner conflict blocks. Native-only tests remain, whereas the test file is absent from the main-parent commit.',
          'classification': 'Pre-existing on the integrated pre-pin candidate: native test expectations conflict with main scanner behavior. Not introduced by the authority source-pin update.',
          'runtime_limit': 'The audit does not claim a historical test rerun. Static source equality and the retained actual run establish independence from the pin update.'
        },
        proposed_disposition={
          'priority': 'P2 scanner integration gate: keep visible and unresolved until policy/tests are reconciled',
          'recommendation': 'Preserve main precision behavior pending lead disposition. Replace these two old unconditional-refusal expectations only after adding explicit positive coverage witnesses with both target modules materialized, proving every complete literal alternative is discovered; retain negatives for unresolved alternatives and ambiguous -m operands.',
          'alternative': 'If unconditional alias ambiguity must still refuse, authorize a narrowly scoped scanner change and revalidate existing #5681 precision examples; do not restore the old broad rule silently.',
          'scope': 'Separate scanner contract follow-up, not an authority-pin repair. No test deletion, xfail, approval expansion or production change performed here.',
          'owner_or_lead_question': 'Confirm which command-table policy is intended before changing these tests. Current commit history favors conservative discovery of all complete literal alternatives.'
        },
        commands=COMMANDS)
    encoded = (json.dumps(report, indent=2, ensure_ascii=True) + '\n').replace(chr(64), '\\u0040').encode()
    with OUT.open('xb') as stream:
        stream.write(encoded)
    persisted = OUT.read_bytes()
    if persisted != encoded or not persisted or chr(64).encode() in persisted:
        raise RuntimeError('evidence persistence verification failed')
    print(json.dumps(dict(path=str(OUT), sha256=sha(persisted), bytes=len(persisted),
                         helper_sha256=report['helper_sha256'], comparisons=comparisons)))


if __name__ == '__main__':
    main()
