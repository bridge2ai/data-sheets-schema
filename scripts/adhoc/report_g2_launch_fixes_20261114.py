#!/usr/bin/env python3
"""Produce the G2 answer-first handoff from saved verification, 2026-11-14.

Inputs: sibling scratch-g2-20261114 command/outcome/JUnit/log records, baseline,
reviews, proposals and final source audit; this committed source checkout.
Outputs: codex-pr5968-launch-fixes-20261114 Markdown and JSON in the assigned
report worktree. No tests, source imports, GitHub writes or H2 report changes.
"""
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
REPORT = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs'
STEM = 'codex-pr5968-launch-fixes-20261114'
H2_HEAD = '64fa2b4b7ac2d1b0767e2d89a5ca4109c945229b'
ISSUES = (6207, 6208, 6215, 6216, 6217, 6218, 6224, 6225)
SOURCE_SCOPE = ('src', 'tests', 'notes/matched_cborg_2026-09-13', 'pyproject.toml',
                'poetry.lock', 'conftest.py', '.github/workflows/main.yaml')
REGRESSIONS = {
    6208: {'tests/test_native_launch_sequence_signals.py': (
        'test_signal_before_claim_preserves_journal_and_starts_no_child',
        'test_signal_during_command_ownership_is_forwarded_once_then_synced',
        'test_signal_delivery_failure_never_aborts_reap',
        'test_wait_retries_interrupt_without_killing_child',
        'test_spawn_failure_restores_both_previous_handlers',
        'test_parent_signal_waits_for_slow_fake_cleanup_and_retains_record',
        'test_signal_after_reap_before_returncode_never_forwards_recycled_pid',
        'test_final_signal_cutoff_keeps_status_reason_and_list_consistent',
        'test_copied_witness_failure_always_reaps_its_owned_process')},
    6215: {'tests/test_native_sequence_start.py': (
        'test_sequence_start_accepts_registration_above_quota_event_limit',
        'test_sequence_start_rejects_registration_above_input_limit_before_lock')},
    6216: {'tests/test_native_launch_sequence_paths.py': (
        'test_packet_overlap_refuses_before_effects_and_corrected_packet_can_start',
        'test_packet_prospective_case_alias_refuses_without_creating_either_spelling')},
    6217: {'tests/test_native_publication_signals.py': (
        'test_record_only_survives_first_and_repeated_signals_and_restores_handlers',
        'test_preparation_first_signal_still_interrupts_then_cleanup_records',
        'test_late_signal_revalidates_exact_failed_mode_once',
        'test_signal_cutoff_does_not_turn_validation_refusal_into_success',
        'test_signal_after_cutoff_keeps_the_original_successful_decision',
        'test_public_first_signal_during_publication_keeps_exact_readback')},
    6218: {'tests/test_native_attempt_deadline.py': (
        'test_unplug_before_reservation_keeps_attempt_unspent',
        'test_unplug_after_reservation_retains_reading_without_consuming_dispatch',
        'test_slow_power_probe_cannot_age_an_already_checked_reservation_margin',
        'test_dispatch_guard_refusal_precedes_stage_activation')},
    6224: {'tests/test_native_launch_sequence_paths.py': (
        'test_guard_overlap_refuses_before_packet_probe_claim_or_command',
        'test_capture_output_overlap_refuses_before_any_output_effect',
        'test_unregistered_disjoint_capture_root_refuses_without_writing',
        'test_guard_prospective_alias_refuses_without_touching_reservations',
        'test_capture_output_must_use_exact_registered_spelling',
        'test_exact_registered_capture_state_is_the_allowed_overlap')},
}
FINDING_TESTS = {
    'G2-REVIEW-6208-F1': ('test_final_signal_cutoff_keeps_status_reason_and_list_consistent',),
    'G2-REVIEW-6208-F2': ('test_signal_after_reap_before_returncode_never_forwards_recycled_pid',),
    'G2-REVIEW-6208-F3': ('test_copied_witness_failure_always_reaps_its_owned_process',),
    'G2-REVIEW-6218-F1': ('test_dispatch_guard_refusal_precedes_stage_activation',),
    'G2-REVIEW-6217-F2': REGRESSIONS[6217]['tests/test_native_publication_signals.py'],
    'G2-REVIEW-6217-F4': ('test_public_first_signal_during_publication_keeps_exact_readback',),
}
REVIEW_FILES = ('review-6208.json', 'review-followups.json', 'review-runner.json',
                'offline-power-fixture-review.json', 'review-report.json', 'review-report-f2.json', 'review-report-f4.json',
                'proposal-6217-implementation/review-6217-superseding.json',
                'review-6217-f3-withdrawn-frozen.json',
                'review-legacy-component-failures-v2.json', 'review-bytecode.json', 'review-report-f3.json', 'review-6217-f4-confirmed.json',
                'scheduled-runner-review-20261114/correction.json', 'review-engine-freshness.json', 'review-retention-stability.json')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path)
    assert path.is_file(), 'required evidence does not exist: ' + str(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def read_json(path):
    return json.loads(Path(path).read_bytes())


def checked_pin(record):
    actual = pin(record['path'])
    assert actual['sha256'] == record['sha256'], record['path']
    if 'bytes' in record:
        assert actual['bytes'] == record['bytes'], record['path']
    return actual


def check_nested_pins(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
            checked_pin(value)
        for item in value.values():
            check_nested_pins(item)
    elif isinstance(value, list):
        for item in value:
            check_nested_pins(item)


def counts(cases):
    values = Counter(row['status'] for row in cases)
    return {'total': len(cases), **{key: values[key] for key in ('passed', 'failed', 'error', 'skipped', 'unconfirmed')}}


def pytest_summary(text):
    summaries = [line.strip() for line in text.splitlines()
                 if re.search(r'\b\d+ (?:passed|failed|errors?|skipped|xfailed|xpassed)\b', line)
                 and re.search(r'\bin [\d.]+s\b', line)]
    if not summaries:
        return None
    line = summaries[-1]
    values = {('error' if key == 'errors' else key): int(value)
              for value, key in re.findall(r'\b(\d+) (passed|failed|errors?|skipped|xfailed|xpassed)\b', line)}
    return {'line': line, 'counts': values, 'completed_total': sum(values.values())}


def junit(path):
    tree = ET.parse(path)
    cases = []
    for node in tree.iter('testcase'):
        status = 'passed'
        detail = None
        for candidate in ('error', 'failure', 'skipped'):
            element = node.find(candidate)
            if element is not None:
                status = 'failed' if candidate == 'failure' else candidate
                detail = {'message': element.get('message', ''), 'text': element.text or ''}
                break
        cases.append({'classname': node.get('classname', ''), 'name': node.get('name', ''),
                      'seconds': node.get('time'), 'status': status, 'detail': detail})
    suites = [{key: node.get(key) for key in ('name', 'timestamp', 'hostname', 'time', 'tests', 'failures', 'errors', 'skipped')}
              for node in tree.iter('testsuite')]
    return cases, suites


def selected_paths(command):
    result = []
    for argument in command:
        if not isinstance(argument, str):
            continue
        file_part = argument.split('::', 1)[0]
        path = Path(file_part)
        if path.is_absolute():
            try:
                relative = path.relative_to(ROOT).as_posix()
            except ValueError:
                continue
        else:
            relative = file_part.removeprefix('./')
        if relative == 'tests' or relative.startswith('tests/'):
            result.append({'path': relative, 'node': argument.split('::', 1)[1] if '::' in argument else None})
    return result


def source_equivalence(recorded, final):
    if not recorded:
        return {'passed': False, 'reason': 'command record has no source head'}
    ancestry_command = ['git', 'merge-base', '--is-ancestor', recorded, final]
    ancestry = subprocess.run(ancestry_command, cwd=ROOT, capture_output=True, check=False)
    diff_command = ['git', 'diff', '--name-only', recorded, final, '--', *SOURCE_SCOPE]
    different = subprocess.run(diff_command, cwd=ROOT, capture_output=True, check=False)
    changed = different.stdout.decode().splitlines()
    return {'passed': ancestry.returncode == different.returncode == 0 and not changed,
            'recorded_head': recorded, 'final_head': final, 'scope': list(SOURCE_SCOPE),
            'ancestry_command': ancestry_command, 'ancestry_returncode': ancestry.returncode,
            'diff_command': diff_command, 'diff_returncode': different.returncode,
            'changed': changed, 'stderr': ancestry.stderr.decode() + different.stderr.decode()}


def classify_cohort(directory, command):
    """Bind saved pytest outputs to their invocation, not an archive's name."""
    row = {'directory': str(directory), 'classification': 'invalid'}
    if not isinstance(command, dict):
        return {**row, 'reason': 'command record is not an object'}
    argv, cwd = command.get('command'), command.get('cwd')
    if (not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv)
            or not isinstance(cwd, str) or not Path(cwd).is_absolute()):
        return {**row, 'reason': 'command argv or absolute cwd is missing/malformed'}
    values = {}
    for option in ('--basetemp', '--junitxml'):
        matches = []
        for index, argument in enumerate(argv):
            if argument == option:
                value = argv[index + 1] if index + 1 < len(argv) else ''
                matches.append(value if value and not value.startswith('-') else '')
            elif argument.startswith(option + '='):
                matches.append(argument[len(option) + 1:])
        if len(matches) != 1 or not matches[0]:
            return {**row, 'reason': option + ' must have one nonempty destination'}
        target = Path(matches[0])
        values[option] = (target if target.is_absolute() else Path(cwd) / target).resolve()
    base, junit_path = values['--basetemp'], values['--junitxml']
    if base.name != 'cases' or junit_path.name != 'pytest.xml' or base.parent != junit_path.parent:
        return {**row, 'reason': 'pytest output destinations do not identify one runner directory'}
    recorded = base.parent
    if recorded == directory.resolve():
        return {**row, 'classification': 'cohort', 'recorded_directory': str(recorded),
                'reason': 'Both saved pytest output destinations bind this directory.'}
    return {**row, 'classification': 'archive', 'recorded_directory': str(recorded),
            'reason': 'Saved pytest outputs target another directory; retained artifacts are not a separate invocation.'}


def classify_auxiliary(directory, markers, raw):
    expected = ROOT.parent / 'scratch-g2-20261114/source-bytecode'
    if directory != expected or markers != ['outcome.json']:
        return None
    if hashlib.sha256(raw).hexdigest() != 'd0e2a91ea573e1995d78c47aca8b7915907c6c2a5019797dfed21b62a3f4795a':
        return None
    value = json.loads(raw)
    if (value.get('status') != 'preserved-and-verified' or value.get('after_inventory') != []
            or any(value.get(name) is not True for name in (
                'source_unchanged', 'head_unchanged', 'one_file_canary_and_full_scope'))
            or any(value.get(name) is not False for name in ('content_deleted', 'directories_removed'))
            or value['plan']['path'] != str(expected / 'plan.json')
            or value['preserved']['path'] != str(expected / 'propose_g2_dispatch_boundary_6207_20261114.cpython-313.pyc')
            or value['preserved']['bytes'] != 30228
            or value['preserved']['sha256'] != '3f2edc32a7f813ff3795ad0b384af2b93df0526b3cd5f16f217c1dc4589602a7'):
        return None
    return {'directory': str(directory), 'classification': 'auxiliary',
            'reason': 'Exact pinned completed one-file bytecode preservation; not a pytest invocation.',
            'related_artifacts': [value['plan'], value['preserved']]}


def discover_cohorts(root):
    rows = []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        evidence = [pin(directory / name) for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log')
                    if (directory / name).is_file()]
        if not evidence:
            continue
        markers = [Path(item['path']).name for item in evidence]
        auxiliary = classify_auxiliary(directory, markers, (directory / 'outcome.json').read_bytes()) if markers == ['outcome.json'] else None
        if auxiliary is not None:
            try:
                for related in auxiliary['related_artifacts']:
                    actual = pin(Path(related['path']))
                    if actual != related:
                        raise ValueError('auxiliary provenance pin differs: ' + related['path'])
                    evidence.append(actual)
            except (OSError, ValueError) as error:
                auxiliary = {'directory': str(directory), 'classification': 'invalid',
                             'reason': 'Auxiliary provenance unavailable or changed: ' + str(error)}
            rows.append({**auxiliary, 'evidence': evidence})
            continue
        try:
            command = json.loads((directory / 'command.json').read_bytes())
        except (OSError, ValueError) as error:
            row = {'directory': str(directory), 'classification': 'invalid',
                   'reason': 'Cannot read saved command: ' + str(error)}
        else:
            row = classify_cohort(directory, command)
        rows.append({**row, 'evidence': evidence})
    return rows


def cohort_directories(discovery):
    assert all(row['classification'] != 'invalid' for row in discovery), 'ambiguous cohort artifacts: inspect discovery command destinations'
    return [Path(row['directory']) for row in discovery if row['classification'] == 'cohort']


def load_cohort(directory, final, equivalence_cache):
    row = {'name': directory.name, 'evidence': {}, 'cases': [], 'suites': [], 'problems': []}
    for name, key in (('command.json', 'command'), ('outcome.json', 'outcome'),
                      ('pytest.xml', 'junit'), ('pytest.log', 'log')):
        path = directory / name
        if path.is_file():
            row['evidence'][key] = pin(path)
            if key in ('command', 'outcome'):
                row[key] = read_json(path)
            elif key == 'junit':
                try:
                    row['cases'], row['suites'] = junit(path)
                except (ET.ParseError, ValueError) as error:
                    row['problems'].append('JUnit cannot be parsed: ' + str(error))
            elif key == 'log':
                log_text = path.read_text(errors='replace')
                row['pytest_summary'] = pytest_summary(log_text)
                row['log_reports_interruption'] = bool(re.search(r'KeyboardInterrupt|Interrupted:', log_text))
        else:
            row['problems'].append('missing ' + name)
    row['junit_entry_counts'] = counts(row['cases'])
    command = row.get('command', {})
    recorded_head = command.get('head')
    if recorded_head not in equivalence_cache:
        equivalence_cache[recorded_head] = source_equivalence(recorded_head, final)
    row['source_equivalence'] = dict(equivalence_cache[recorded_head])
    # This overlay belongs only to the exact retained invocation. Never put it
    # in the head-keyed cache or grant it to another cohort at the same HEAD.
    if directory == SCRATCH / 'legacy-full-serial' and not row['source_equivalence']['passed']:
        import runpy
        helper = ROOT / 'scripts/adhoc/g2_legacy_leaf_reuse_6217_f4_20261114.py'
        try:
            validate = runpy.run_path(str(helper))['validate_reuse']
            proofs = [validate(ROOT, SCRATCH, recorded_head, final, file, directory) for file in (
                'tests/test_native_execution.py', 'tests/test_native_receipt_origin_reporting.py')]
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            row['source_equivalence']['reuse_refused'] = str(error)
        else:
            row['source_equivalence'].update(passed=True, strict_source_equality=False,
                basis='Exact legacy149 invocation reused across the reviewed F4 leaf-test correction only.',
                legacy_reuse=proofs)
    row['selected_paths'] = selected_paths(command.get('command', []))
    pytest_arguments = command.get('command', [])[3:]
    filters = ('-k', '-m', '--deselect', '--ignore', '--ignore-glob', '--last-failed', '--lf', '--collect-only')
    row['selection_filtered'] = any(arg == flag or arg.startswith(flag + '=')
                                    for arg in pytest_arguments for flag in filters)
    if command and command.get('cwd') != str(ROOT):
        row['problems'].append('command cwd differs from assigned checkout')
    inventory = command.get('source_inventory', {})
    if command and inventory.get('ignored_and_hidden_files_included') is not True:
        row['problems'].append('missing ignored-inclusive runner source inventory')
    outcome = row.get('outcome', {})
    expected = {key: row['junit_entry_counts'][key] for key in ('total', 'failed', 'error', 'skipped')}
    if outcome and outcome.get('counts') != expected:
        row['problems'].append('saved outcome counts differ from JUnit cases')
    row['returncode'] = outcome.get('returncode')
    row['interrupted'] = row['returncode'] == 2 or row.get('log_reports_interruption', False)
    summary = row.get('pytest_summary')
    row['junit_entries_without_completed_log_outcome'] = (
        row['junit_entry_counts']['total'] - summary['completed_total'] if summary else None)
    if row['interrupted']:
        row['problems'].append('pytest session interrupted; no clean completion proof')
        for case in row['cases']:
            if case['status'] == 'passed':
                case['junit_status'] = 'passed'
                case['status'] = 'unconfirmed'
                case['status_reason'] = ('An interrupted session can emit empty JUnit entries for abandoned cases. '
                                         'The log aggregate does not identify which individual entries completed.')
    row['counts'] = counts(row['cases'])
    row['complete'] = not row['problems'] and bool(row['cases'])
    row['eligible'] = row['complete'] and row['returncode'] == 0 and row['source_equivalence']['passed']
    starts = [suite['timestamp'] for suite in row['suites'] if suite.get('timestamp')]
    row['junit_started_at'] = min(starts) if starts else None
    # Saved JUnit start is preferred. For a still-incomplete invocation use its
    # command-file time so it cannot silently disappear behind an earlier pass.
    fallback = Path(row['evidence']['command']['path']).stat().st_mtime if 'command' in row['evidence'] else directory.stat().st_mtime
    row['order_time'] = datetime.fromisoformat(row['junit_started_at']).timestamp() if starts else fallback
    return row


def selected(row, file, function=None, *, whole_file=False):
    for selector in row['selected_paths']:
        path, node = selector['path'], selector['node']
        if whole_file and node is not None:
            continue
        if file == path:
            if function is None or node is None or node.split('::')[-1].split('[', 1)[0] == function:
                return True
        elif node is None and file.startswith(path.rstrip('/') + '/'):
            return True
    return False


def file_cases(row, file):
    module = str(Path(file).with_suffix('')).replace('/', '.')
    return [case for case in row['cases']
            if case['classname'] == module or case['classname'].startswith(module + '.')]


def expected_cases(file, function):
    tree = ast.parse((ROOT / file).read_bytes(), filename=file)
    node, = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function]
    count = 1
    for decorator in node.decorator_list:
        if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == 'parametrize'):
            values = decorator.args[1] if len(decorator.args) > 1 else next(
                keyword.value for keyword in decorator.keywords if keyword.arg == 'argvalues')
            assert isinstance(values, (ast.List, ast.Tuple)), 'explicit parameter census needed for ' + function
            count *= len(values.elts)
    return count


def regression_proof(cohorts, file, function):
    expected = expected_cases(file, function)
    invocations = [row for row in cohorts if selected(row, file, function)]
    cases = {}
    for row in invocations:
        for case in file_cases(row, file):
            if case['name'].split('[', 1)[0] == function:
                cases[(case['classname'], case['name'])] = {**case, 'cohort': row['name'],
                    'cohort_complete': row['complete'], 'cohort_returncode': row['returncode'],
                    'source_equivalent': row['source_equivalence']['passed'],
                    'junit': row['evidence'].get('junit')}
    records = list(cases.values())
    newest = invocations[-1] if invocations else None
    passed = bool(newest and newest['eligible'] and not newest['selection_filtered']) and len(records) == expected and all(
        case['status'] == 'passed' and case['cohort_complete'] and case['cohort_returncode'] == 0
        and case['source_equivalent'] for case in records)
    return {'file': file, 'test': function, 'expected_cases_from_source': expected,
            'source': pin(ROOT / file), 'counts': counts(records), 'passed': passed,
            'cases': records, 'invocations': [row['name'] for row in invocations]}


def file_proof(cohorts, file):
    invocations = [row for row in cohorts if selected(row, file, whole_file=True)
                   and not row['selection_filtered']]
    row = invocations[-1] if invocations else None
    cases = file_cases(row, file) if row else []
    result = counts(cases)
    passed = bool(row and row['eligible'] and result['passed'] > 0
                  and result['failed'] == result['error'] == 0)
    return {'file': file, 'source': pin(ROOT / file), 'passed': passed, 'counts': result,
            'cohort': row['name'] if row else None, 'returncode': row['returncode'] if row else None,
            'status': ('complete with skips' if passed and result['skipped'] else 'passed') if passed
                      else ('session failed or incomplete' if row else 'no complete-file invocation'),
            'invocations': [item['name'] for item in invocations],
            'junit': row['evidence'].get('junit') if row else None}


def commits():
    result = []
    for line in git('log', '--first-parent', '--reverse', '--format=%H%x00%s', H2_HEAD + '..HEAD').decode().splitlines():
        commit, subject = line.split('\0', 1)
        files = git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).decode().splitlines()
        result.append({'commit': commit, 'subject': subject, 'files': files,
                       'issues': [issue for issue in ISSUES if re.search(r'(?<!\d)' + str(issue) + r'(?!\d)', subject)]})
    return result


def required_files(changed, tracked_tests):
    modules = {Path(name).stem for name in changed if name.startswith('src/data_sheets_schema/') and name.endswith('.py')}
    needed = {name for name in changed if name.startswith('tests/') and Path(name).name.startswith('test_') and name.endswith('.py')}
    for name in tracked_tests:
        text = (ROOT / name).read_text()
        if any(re.search(r'(?<!\w)' + re.escape(module) + r'(?!\w)', text) for module in modules):
            needed.add(name)
    return sorted(needed)


def audit_proof(path, head):
    audit = read_json(path)
    assert audit['head'] == head, 'final audit must describe current HEAD'
    for row in audit['protected']:
        assert pin(ROOT / row['path'])['sha256'] == row['sha256']
    for manifest in audit['manifests']:
        assert pin(ROOT / manifest['path'])['sha256'] == manifest['sha256']
        for module in manifest['modules']:
            assert pin(ROOT / module['path'])['sha256'] == module['actual_sha256']
    for name, digest in audit['changed_file_hashes'].items():
        assert pin(ROOT / name)['sha256'] == digest, name
    return {'record': audit, 'evidence': pin(path),
            'passed': all(row['unchanged'] for row in audit['protected']) and not audit['pin_proposal_required']
                      and all(module['matches'] for manifest in audit['manifests'] for module in manifest['modules'])}


def review_ledger(regressions, coverage):
    sources, findings = [], []
    for name in REVIEW_FILES:
        path = SCRATCH / name
        document = read_json(path)
        check_nested_pins(document)
        sources.append({'evidence': pin(path), 'record': document})
        findings.extend(document.get('findings', [document] if 'finding_id' in document or 'id' in document else []))
        findings.extend(document.get('producer_review_findings', []))
    closure_path = SCRATCH / 'final-review-closure.json'
    closure = read_json(closure_path) if closure_path.is_file() else None
    if closure is not None:
        check_nested_pins(closure)
    declared = {row.get('id', row.get('finding_id')): row for row in closure.get('findings', [])} if closure else {}
    by_test = {row['test']: row for row in regressions}
    result = []
    for finding in findings:
        identity = finding.get('id', finding.get('finding_id'))
        proof = [by_test[name] for name in FINDING_TESTS.get(identity, ())]
        if identity == 'G2-REVIEW-6217-F4':
            proof.append(coverage['tests/test_native_publication_signals.py'])
        if identity == 'G2-REVIEW-6218-F2':
            proof = [coverage[name] for name in ('tests/test_native_u4b_a3_reservation.py', 'tests/test_native_u3k_freshness_order.py')]
        if identity == 'G2-REVIEW-ENGINE-FRESHNESS-F1':
            proof = [coverage['tests/test_native_shared_execution_failure.py']]
        if identity in ('G2-REVIEW-LEGACY-F1', 'G2-REVIEW-LEGACY-F2'):
            proof = [coverage[finding['required_clean_full_file']]]
        declaration = declared.get(identity)
        declared_evidence = [checked_pin(item) for item in declaration.get('evidence', [])] if declaration else []
        test_passed = all(row['passed'] for row in proof) if proof else None
        closed = bool(declaration and declaration.get('status') in ('closed', 'corrected-and-verified', 'verified')
                      and declared_evidence and (test_passed is True if proof else True))
        if identity == 'G2-REVIEW-RETENTION-STABILITY-F1':
            closed = False  # A single diagnostic never closes the original whole-file failure.
        withdrawn = identity == 'G2-REVIEW-6217-F3' and finding.get('status') == 'disputed; withdrawn by reviewer'
        result.append({'finding': finding, 'id': identity, 'relevant_proof': proof,
            'relevant_tests_passed': test_passed, 'closure_declaration': declaration,
            'closure_evidence': declared_evidence, 'closed_by_verified_declaration': closed,
            'reported_status': 'disputed/withdrawn after source check; no fix required; lead filing retained' if withdrawn
                else 'required clean rerun verified; original failure and undetermined cause retained; lead filing retained'
                    if closed and identity in ('G2-REVIEW-LEGACY-F1', 'G2-REVIEW-LEGACY-F2')
                else 'required clean whole-file rerun verified; original three freshness failures and unknown latency cause retained; no code correction claimed; lead filing required'
                    if closed and identity == 'G2-REVIEW-ENGINE-FRESHNESS-F1'
                else 'whole-file rerun pending; original three freshness failures and interrupted cohort retained; latency cause unknown; lead filing required'
                    if identity == 'G2-REVIEW-ENGINE-FRESHNESS-F1'
                else 'scheduled canary verified; static correction retained; lead filing required'
                    if closed and identity == 'G2-REVIEW-SCHEDULED-RUNNER-F1'
                else 'static correction retained; scheduled canary runtime verification pending; lead filing required'
                    if identity == 'G2-REVIEW-SCHEDULED-RUNNER-F1'
                else 'open; original normal completed cohort retained (3 failed, 26 passed, exit 1); offending path/metadata field and cause unknown; diagnostic is not acceptance; lead filing required'
                    if identity == 'G2-REVIEW-RETENTION-STABILITY-F1'
                else 'producer traceback-header parser correction verified against all three retained failures; original fixture failure remains open; lead filing required'
                    if closed and identity == 'G2-REVIEW-RETENTION-LEDGER-F1'
                else 'producer traceback-header parser correction retained; verification pending; original fixture failure remains open; lead filing required'
                    if identity == 'G2-REVIEW-RETENTION-LEDGER-F1'
                else 'verified correction; lead filing status retained' if closed
                else 'open for lead closure' + ('; relevant regressions passed' if test_passed else '')})
    return {'sources': sources, 'findings': result, 'closure': closure,
            'closure_evidence': pin(closure_path) if closure else None}



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


def clean_text(value):
    return value.replace(chr(64), '[at]')


def main():
    assert REPORT.is_dir() and SCRATCH.is_dir()
    baseline_path = SCRATCH / 'baseline/index.json'
    baseline = read_json(baseline_path)
    for record in baseline['issues'] + baseline['reviews']:
        checked_pin(record)
    for source in baseline['sources']:
        checked_pin(source['snapshot'])
    head = git('rev-parse', 'HEAD').decode().strip()
    assert not git('status', '--porcelain', '--', *SOURCE_SCOPE), 'source and tests must be committed'
    audit = audit_proof(SCRATCH / 'source-audit-final.json', head)
    history = commits()
    changed = git('diff', '--name-only', baseline['base'], head, '--', 'src', 'tests').decode().splitlines()
    tracked_tests = [name for name in git('ls-files', 'tests').decode().splitlines()
                     if Path(name).name.startswith('test_') and name.endswith('.py')]
    required = required_files(changed, tracked_tests)
    # A touched test remains required even if a later repair restored its bytes.
    touched = {name for row in history if row['issues'] for name in row['files']}
    required = sorted(set(required) | set(required_files(touched, tracked_tests)))
    equivalent = {}
    discovery = discover_cohorts(SCRATCH)
    cohort_dirs = cohort_directories(discovery)
    cohorts = sorted((load_cohort(path, head, equivalent) for path in cohort_dirs),
                     key=lambda row: (row['order_time'], row['name']))
    coverage = {name: file_proof(cohorts, name) for name in required}
    regressions = {issue: [regression_proof(cohorts, file, function)
        for file, names in files.items() for function in names] for issue, files in REGRESSIONS.items()}
    proposals = {}
    for issue, relative in ((6207, 'proposal-6207-after-6217/proposal.json'),
                             (6225, 'issue-6225-proposal.json')):
        path = SCRATCH / relative
        proposals[issue] = {'record': read_json(path), 'evidence': pin(path)}
        check_nested_pins(proposals[issue]['record'])
    proposal = proposals[6207]['record']
    assert proposal['applied'] is False and proposal['pin_rotation_applied'] is False
    for key in ('patch', 'apply_check', 'test_plan', 'generator'):
        checked_pin(proposal[key])
    assert read_json(proposal['apply_check']['path'])['returncode'] == 0
    proposal['head_equivalence'] = source_equivalence(proposal['head'], head)
    proposal_review_path = SCRATCH / 'review-6207-after-6217.json'
    proposal_review = read_json(proposal_review_path)
    check_nested_pins(proposal_review)
    assert proposal_review['proposal'] == proposals[6207]['evidence']
    proposals[6207]['review'] = {'record': proposal_review, 'evidence': pin(proposal_review_path)}
    # Proposal applicability is a source/patch check, never test acceptance.
    import runpy
    reuse_helper = ROOT / 'scripts/adhoc/g2_legacy_leaf_reuse_6217_f4_20261114.py'
    leaf_scope = runpy.run_path(str(reuse_helper))['scope_proof'](head)
    assert proposal['head'] == '2070a2116ceb5b1f5dd9a870c803ee3311d298b9'
    production_scope = tuple(name for name in SOURCE_SCOPE if name != 'tests')
    assert not git('diff', '--name-only', proposal['head'], head, '--', *production_scope)
    current_sources = [checked_pin(row) for row in proposal_review['current_sources']]
    apply_command = ['git', 'apply', '--check', proposal['patch']['path']]
    apply_result = subprocess.run(apply_command, cwd=ROOT, capture_output=True, check=False)
    assert apply_result.returncode == 0, apply_result.stderr.decode()
    proposals[6207]['current_applicability'] = {
        'passed': True, 'proposal_head': proposal['head'], 'current_head': head,
        'production_scope': list(production_scope), 'current_sources': current_sources,
        'reviewed_leaf_test_drift': leaf_scope, 'scope_validator': pin(reuse_helper),
        'apply_check': {'command': apply_command, 'returncode': apply_result.returncode,
                        'stdout': apply_result.stdout.decode(), 'stderr': apply_result.stderr.decode()},
        'basis': 'Exact proposal base bytes and production scope remain unchanged; the F4 leaf-test drift is recorded separately. No proposed code or test was executed.'}
    for issue in (6225,):
        assert proposals[issue]['record']['status'] == 'not fixed'
        proposals[issue]['markdown'] = pin(SCRATCH / ('issue-' + str(issue) + '-proposal.md'))
    historical_path = SCRATCH / 'issue-6217-proposal.json'
    historical_6217 = {'record': read_json(historical_path), 'evidence': pin(historical_path),
        'markdown': pin(SCRATCH / 'issue-6217-proposal.md'),
        'disposition': 'Superseded: the assignment authorized the implementation; this is retained history, not the current issue status.',
        'superseding_record': pin(SCRATCH / 'proposal-6217-implementation/review-6217-superseding.json')}
    check_nested_pins(historical_6217['record'])
    ledger = review_ledger([proof for proofs in regressions.values() for proof in proofs], coverage)
    diagnostic = retention_diagnostic(head)
    inventory_path = SCRATCH / 'runner-inventory-verification/result.json'
    inventory = read_json(inventory_path)
    check_nested_pins(inventory)
    assert inventory['passed'] == sum(row['passed'] is True for row in inventory['cases'])
    assert inventory['failed'] == sum(row['passed'] is not True for row in inventory['cases'])
    report_verification_path = SCRATCH / 'report-closure-pin-verification-after-retention-stability/result.json'
    report_verification = read_json(report_verification_path)
    check_nested_pins(report_verification)
    assert report_verification['reporter'] == pin(Path(__file__).resolve())
    interruption_path = SCRATCH / 'engine-admission-interruption-20261114/cleanup-1794630386052545000.json'
    interruption = read_json(interruption_path)
    check_nested_pins(interruption)
    assert interruption['safe_to_release_source_freeze'] is True
    oracle_cleanup_path = SCRATCH / 'final-regressions-interruption-6217-oracle/cleanup-1794637161740208000.json'
    oracle_cleanup = read_json(oracle_cleanup_path)
    check_nested_pins(oracle_cleanup)
    assert oracle_cleanup['status'] == 'cleanup-confirmed' and oracle_cleanup['safe_to_release_source_freeze'] is True
    assert all(row['original_reaped'] is True for row in (
        oracle_cleanup['coordinator'], oracle_cleanup['runner'], *oracle_cleanup['workers'],
        *oracle_cleanup['observed_descendants']))
    freshness_cleanup_path = SCRATCH / 'final-engine-freshness-interruption/cleanup-1794646795499479000.json'
    freshness_cleanup = read_json(freshness_cleanup_path)
    check_nested_pins(freshness_cleanup)
    assert freshness_cleanup['status'] == 'cleanup-confirmed' and freshness_cleanup['safe_to_release_source_freeze'] is True
    assert all(row['original_reaped'] is True for row in (
        freshness_cleanup['coordinator'], freshness_cleanup['runner'], *freshness_cleanup['workers'],
        *freshness_cleanup['observed_descendants']))
    issues = []
    for issue in ISSUES:
        linked = [row for row in history if issue in row['issues']]
        repairs = [row for row in linked if any(name.startswith(('src/', 'tests/')) for name in row['files'])]
        files = required_files({name for row in repairs for name in row['files']}, tracked_tests)
        proofs = regressions.get(issue, [])
        if issue in proposals:
            status = 'not fixed'
            reason = ('Unapplied controller-pin proposal; approval and validation required.' if issue == 6207
                      else proposals[issue]['record']['decision_required'])
        else:
            passed = bool(repairs and proofs and files) and audit['passed'] and all(row['passed'] for row in proofs)
            passed = passed and all(coverage[name]['passed'] for name in files)
            status = 'fixed' if passed else 'not fixed'
            reason = ('Required regressions and complete-file checks passed on equivalent source.' if passed
                      else 'Implementation is recorded, but required saved verification is incomplete or failing.'
                      if repairs else 'No applied repair commit with the required saved verification is recorded.')
        issues.append({'issue': issue, 'status': status, 'reason': reason, 'commits': linked,
                       'repair_commits': repairs, 'regressions': proofs, 'required_files': files,
                       'file_proof': [coverage[name] for name in files], 'proposal': proposals.get(issue)})
    data = {'answer': [{'issue': row['issue'], 'status': row['status'], 'reason': row['reason']} for row in issues],
        'branch': git('branch', '--show-current').decode().strip(), 'head': head,
        'issues': issues, 'cohorts': cohorts, 'cohort_artifact_discovery': discovery,
        'required_file_coverage': list(coverage.values()),
        'source_audit': audit, 'baseline': baseline, 'baseline_evidence': pin(baseline_path),
        'commits_since_h2_handoff': history, 'g2_changed_source_and_tests': changed,
        'review_ledger': ledger, 'report_producer': pin(Path(__file__).resolve()),
        'retention_stability_diagnostic': diagnostic,
        'superseded_6217_proposal': historical_6217,
        'report_revision_verification': {'record': report_verification, 'evidence': pin(report_verification_path)},
        'interrupted_cohort_cleanup': {'record': interruption, 'evidence': pin(interruption_path)},
        'publication_oracle_interruption': {'record': oracle_cleanup, 'evidence': pin(oracle_cleanup_path)},
        'engine_freshness_interruption': {'record': freshness_cleanup, 'evidence': pin(freshness_cleanup_path)},
        'runner_inventory_verification': {'record': inventory, 'evidence': pin(inventory_path)},
        'runner': pin(ROOT / 'scripts/adhoc/run_g2_checks_20261114.py'),
        'environment': {'report_python': sys.version, 'platform': sys.platform,
            'scope': 'Local macOS primary Python 3.13 evidence; no CI Python 3.12 or complete CI result is claimed.'},
        'limitations': ['Source commits alone are never accepted as fix proof.',
            'No provider, model, native binary, real host probe or production campaign is authorized by this report.',
            'Skipped cases remain skipped; every named issue regression must pass individually.',
            'Interrupted-session JUnit entries without a failure element are unconfirmed individually; the log completed-test aggregate is retained separately.',
            'The completed H2 handoff is a separate immutable record and is not rewritten here.']}
    lines = ['G2 launch fixes: ' + '; '.join(str(row['issue']) + ' ' + row['status'] for row in issues) + '.', '',
             'Branch `' + data['branch'] + '`, HEAD `' + head + '`.', '']
    for row in issues:
        commit_text = ', '.join(item['commit'][:12] for item in row['commits']) or 'none recorded'
        proof_cases = [case for proof in row['regressions'] for case in proof['cases']]
        result = counts(proof_cases)
        summary = ', '.join(str(result[key]) + ' ' + key for key in ('passed', 'failed', 'error', 'skipped', 'unconfirmed'))
        verification = (' Required regression results: ' + summary + '.' if row['regressions']
                        else ' No applied-fix test proof is claimed.')
        lines.append('- ' + str(row['issue']) + ': ' + row['status'] + '. ' + row['reason']
                     + ' Commits: ' + commit_text + '.' + verification)
    lines += ['', 'Verification cohorts:', '']
    for row in cohorts:
        summary = ', '.join(str(row['counts'][key]) + ' ' + key for key in ('passed', 'failed', 'error', 'skipped', 'unconfirmed'))
        lines.append('- ' + row['name'] + ': ' + summary + '; exit ' + str(row['returncode'])
            + '; ' + ('interrupted and incomplete' if row['interrupted'] else 'complete' if row['complete'] else 'incomplete')
            + '; source ' + ('equivalent' if row['source_equivalence']['passed'] else 'unverified or changed') + '.')
        if row['source_equivalence'].get('legacy_reuse'):
            lines.append('  Reused exact legacy149 evidence from HEAD 2070a2116 across only the reviewed publication-test oracle correction 21367471; all shared source, fixtures and selected nodes remain unchanged.')
        if row['interrupted']:
            log_summary = row.get('pytest_summary')
            lines.append('  JUnit contains ' + str(row['junit_entry_counts']['total']) + ' entries; '
                         + ('pytest completed-test summary: `' + log_summary['line'] + '`; '
                            + str(row['junit_entries_without_completed_log_outcome']) + ' entries have no corresponding completed outcome in that aggregate.'
                            if log_summary else 'no completed-test summary was saved.')
                         + ' Apparent JUnit passes are not individual completion proof.')
        for case in row['cases']:
            if case['status'] in ('failed', 'error'):
                reason = ' '.join((case['detail']['message'] or case['detail']['text']).split())
                lines.append('  - ' + case['name'] + ': ' + reason[:400])
    lines += ['', 'Required complete-file checks:', '']
    for row in coverage.values():
        summary = ', '.join(str(row['counts'][key]) + ' ' + key for key in ('passed', 'failed', 'error', 'skipped', 'unconfirmed'))
        lines.append('- `' + row['file'] + '`: ' + row['status'] + '; ' + summary
                     + '; cohort ' + str(row['cohort']) + '; exit ' + str(row['returncode']) + '.')
    lines += ['', 'Review findings:', '']
    for row in ledger['findings']:
        description = row['finding'].get('finding', '')
        lines.append('- ' + row['id'] + ': ' + row['reported_status'] + '.'
                     + (' ' + description if isinstance(description, str) and description else ''))
    lines += ['', 'Retention diagnostic: ' + diagnostic['status'] + '; node `' + diagnostic['selected_node']
        + '`; exit ' + str(diagnostic.get('returncode')) + '. Original lifecycle failures remain open; this node is never whole-file acceptance.']
    lines += ['', '6207 proposal: `' + proposals[6207]['evidence']['path'] + '`; no source or pin rotation applied. '
        + proposal['remaining_limit'],
        '6217 former decision proposal is superseded by the authorized implementation; retained history: `'
        + historical_6217['evidence']['path'] + '`.',
        '6225 decision proposal: `' + proposals[6225]['evidence']['path'] + '`.',
        'Source/protected/pin audit: `' + audit['evidence']['path'] + '`; '
        + ('passed.' if audit['passed'] else 'requires attention.'),
        'Exact commands, JUnit pins, parameter counts, source comparisons and review evidence are retained in the JSON twin.',
        'Local macOS Python 3.13 checks do not certify CI Python 3.12 or the full CI suite. Helper GitHub writes are prohibited; lead filing and publication remain separate.']
    markdown = clean_text('\n'.join(lines) + '\n')
    json_path, md_path = REPORT / (STEM + '.json'), REPORT / (STEM + '.md')
    assert not json_path.exists() and not md_path.exists(), 'retain any earlier G2 handoff'
    encoded = (json.dumps(data, indent=2) + '\n').replace(chr(64), '\\u0040')
    assert chr(64) not in markdown and chr(64) not in encoded
    json_path.write_text(encoded)
    md_path.write_text(markdown)
    assert json.loads(json_path.read_bytes()) == data and md_path.read_text() == markdown
    print(json.dumps({'markdown': pin(md_path), 'json': pin(json_path)}))


if __name__ == '__main__':
    main()
