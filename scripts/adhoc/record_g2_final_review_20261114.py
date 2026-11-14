#!/usr/bin/env python3
"""Close G2 review findings from retained evidence, 2026-11-14.

Inputs: scratch-g2-20261114 review ledgers, command/outcome/JUnit records,
6217 historical proposal/implementation/withdrawal and runner verification;
current source for equivalence/census, refreshed 6207 review and cohort cleanup.
Outputs: exclusive final-review-closure.json and review-6224-final.json there.
Serves G2 review findings for 6208/6218/6217 and the runner, plus the final
6224 read-only review. Does not import project code, run tests or modify source.
Run only after the coordinated test cohorts have finished.
"""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import runpy
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
SOURCE_SCOPE = ('src', 'tests', 'notes/matched_cborg_2026-09-13', 'pyproject.toml',
                'poetry.lock', 'conftest.py', '.github/workflows/main.yaml')
REVIEWED_6224 = '748ea6be5be5fdfa1174b1e0b58071bd129e1b5a'
APPLIED_6217 = '2070a2116ceb5b1f5dd9a870c803ee3311d298b9'
CORRECTED_6217_TEST = '21367471df2e7d2f761153e1b91b218a705c62c6'
PUBLICATION_FILE = 'tests/test_native_publication_signals.py'
PUBLICATION_TESTS = (
    'test_record_only_survives_first_and_repeated_signals_and_restores_handlers',
    'test_preparation_first_signal_still_interrupts_then_cleanup_records',
    'test_late_signal_revalidates_exact_failed_mode_once',
    'test_signal_cutoff_does_not_turn_validation_refusal_into_success',
    'test_signal_after_cutoff_keeps_the_original_successful_decision',
    'test_public_first_signal_during_publication_keeps_exact_readback',
)
SIGNALS = 'tests/test_native_launch_sequence_signals.py'
TEST_FINDINGS = (
    ('G2-REVIEW-6208-F1', 'review-6208.json',
     ((SIGNALS, 'test_final_signal_cutoff_keeps_status_reason_and_list_consistent'),)),
    ('G2-REVIEW-6208-F2', 'review-6208.json',
     ((SIGNALS, 'test_signal_after_reap_before_returncode_never_forwards_recycled_pid'),)),
    ('G2-REVIEW-6208-F3', 'review-6208.json',
     ((SIGNALS, 'test_copied_witness_failure_always_reaps_its_owned_process'),)),
    ('G2-REVIEW-6218-F1', 'review-followups.json',
     (('tests/test_native_attempt_deadline.py', 'test_dispatch_guard_refusal_precedes_stage_activation'),)),
    ('G2-REVIEW-6218-F2', 'offline-power-fixture-review.json',
     (('tests/test_native_u4b_a3_reservation.py', None),
      ('tests/test_native_u3k_freshness_order.py', None))),
)
RUNNER_CASES = {'tracked_file', 'tracked_directory', 'untracked_selected_test',
    'ignored_selected_test', 'untracked_import', 'ignored_import', 'hidden_ignored_stub',
    'outside_test_directory', 'untracked_selected_outside_inventory',
    'tracked_explicit_file_outside_tests', 'unrelated_helpers_allowed'}


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    if not raw:
        raise ValueError('empty evidence: ' + str(path))
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def document(path, evidence):
    evidence.append(pin(path))
    return json.loads(Path(path).read_bytes())


def checked_pin(record, evidence):
    actual = pin(record['path'])
    if actual['sha256'] != record['sha256'] or actual['bytes'] != record['bytes']:
        raise ValueError('evidence pin differs: ' + record['path'])
    evidence.append(actual)


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ledger(identity, name, evidence):
    value = document(OUT / name, evidence)
    rows = value.get('findings', [value])
    require(any(row.get('id', row.get('finding_id')) == identity for row in rows),
            'finding missing from original ledger: ' + identity)
    return value


def selectors(command):
    result = []
    for argument in command.get('command', []):
        if not isinstance(argument, str):
            continue
        path, separator, node = argument.partition('::')
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                path = candidate.relative_to(ROOT).as_posix()
            except ValueError:
                continue
        path = path.removeprefix('./')
        if path == 'tests' or path.startswith('tests/'):
            result.append((path, node if separator else None))
    return result


def selects(command, file, function):
    for path, node in selectors(command):
        if path == file:
            if function is None and node is None:
                return True
            if function is not None and (node is None or node.split('::')[-1].split('[', 1)[0] == function):
                return True
        elif node is None and file.startswith(path.rstrip('/') + '/'):
            return True
    return False


def census(file, function):
    tree = ast.parse((ROOT / file).read_bytes(), filename=file)
    result = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith('test_'):
            continue
        if function is not None and node.name != function:
            continue
        count = 1
        for decorator in node.decorator_list:
            if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == 'parametrize'):
                values = decorator.args[1] if len(decorator.args) > 1 else next(
                    item.value for item in decorator.keywords if item.arg == 'argvalues')
                require(isinstance(values, (ast.List, ast.Tuple)),
                        'explicit parameter census required: ' + node.name)
                count *= len(values.elts)
        result[node.name] = count
    require(bool(result), 'no expected tests found: ' + file)
    return result


def cases(path):
    rows = []
    for node in ET.parse(path).iter('testcase'):
        status = 'passed'
        for kind, result in (('error', 'error'), ('failure', 'failed'), ('skipped', 'skipped')):
            if node.find(kind) is not None:
                status = result
                break
        rows.append({'classname': node.get('classname', ''), 'name': node.get('name', ''), 'status': status})
    return rows


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
    require(all(row['classification'] != 'invalid' for row in discovery),
            'ambiguous cohort artifacts: inspect discovery command destinations')
    return sorted((Path(row['directory']) for row in discovery if row['classification'] == 'cohort'),
                  key=lambda path: ((path / 'command.json').stat().st_mtime_ns, path.name))


def test_proof(file, function, directories, head, evidence):
    expected = census(file, function)
    evidence.append(pin(ROOT / file))
    matching = []
    for directory in directories:
        value = json.loads((directory / 'command.json').read_bytes())
        if selects(value, file, function):
            matching.append((directory, value))
    require(bool(matching), 'no matching complete-file or regression invocation: ' + file)
    directory, command = matching[-1]
    for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log'):
        evidence.append(pin(directory / name))
    outcome = json.loads((directory / 'outcome.json').read_bytes())
    require(command.get('cwd') == str(ROOT), 'cohort ran in another checkout')
    require(command.get('source_inventory', {}).get('ignored_and_hidden_files_included') is True,
            'cohort lacks ignored-inclusive source inventory')
    filters = ('-k', '-m', '--deselect', '--ignore', '--ignore-glob', '--last-failed', '--lf', '--collect-only')
    require(not any(arg == flag or arg.startswith(flag + '=')
                    for arg in command.get('command', [])[3:] for flag in filters),
            'latest selected invocation was filtered')
    recorded = command.get('head')
    require(isinstance(recorded, str) and len(recorded) == 40, 'cohort lacks source HEAD')
    ancestry = git('merge-base', '--is-ancestor', recorded, head)
    changed = git('diff', '--exit-code', recorded, head, '--', *SOURCE_SCOPE)
    require(ancestry.returncode == changed.returncode == 0, 'cohort source is not equivalent to final source')
    require(git('diff', '--exit-code', 'HEAD', '--', *SOURCE_SCOPE).returncode == 0,
            'tracked source changed after the recorded HEAD')
    rows = cases(directory / 'pytest.xml')
    totals = Counter(row['status'] for row in rows)
    require(outcome.get('counts') == {'total': len(rows), 'failed': totals['failed'],
                                    'error': totals['error'], 'skipped': totals['skipped']},
            'outcome counts differ from JUnit')
    require(outcome.get('returncode') == 0, 'latest selected cohort failed')
    module = file[:-3].replace('/', '.')
    chosen = [row for row in rows if (row['classname'] == module or row['classname'].startswith(module + '.'))
              and (function is None or row['name'].split('[', 1)[0] == function)]
    require(len({(row['classname'], row['name']) for row in chosen}) == len(chosen),
            'duplicate JUnit test identities')
    observed = Counter(row['name'].split('[', 1)[0] for row in chosen)
    require(dict(observed) == expected, 'JUnit does not contain the full expected test/parameter census')
    require(all(row['status'] == 'passed' for row in chosen), 'required tests failed, errored or skipped')
    return {'file': file, 'test': function, 'cohort': directory.name, 'cases': len(chosen),
            'expected': expected, 'recorded_head': recorded}


def close(identity, action):
    evidence, details = [], []
    try:
        reason = action(evidence, details)
        status = 'verified'
    except (OSError, ValueError, KeyError, TypeError, StopIteration, ET.ParseError, SyntaxError) as error:
        status, reason = 'not_verified', str(error)
    unique = {item['path']: item for item in evidence}
    return {'id': identity, 'status': status, 'evidence': list(unique.values()),
            'reason': reason}, details


def close_tests(identity, ledger_name, requirements, directories, head, evidence, details):
    ledger(identity, ledger_name, evidence)
    for file, function in requirements:
        details.append(test_proof(file, function, directories, head, evidence))
    return 'All required cases passed in retained exit-0, source-equivalent invocations; full files required where specified.'


def close_engine_freshness(directories, head, evidence, details):
    identity = 'G2-REVIEW-ENGINE-FRESHNESS-F1'
    original = ledger(identity, 'review-engine-freshness.json', evidence)
    finding, = [row for row in original['findings'] if row['finding_id'] == identity]
    file = 'tests/test_native_shared_execution_failure.py'
    expected = {
        'test_v2_publication_failure_preserves_first_error[published.json]',
        'test_v2_injected_transport_timeout_keeps_registered_limit_and_failure',
        'test_v2_publication_failure_preserves_first_error[final.json]',
    }
    module = file[:-3].replace('/', '.')
    require(original['cohort'] == 'final-engine-dependents'
            and original['outcome']['returncode'] == 2
            and original['outcome']['counts'] == {'total': 241, 'failed': 3, 'error': 0, 'skipped': 0}
            and finding['required_clean_full_file'] == file,
            'original interrupted freshness finding differs')
    checked_pin(original['producer'], evidence)
    for pair in [*original['artifacts'].values(), original['cleanup']]:
        for key in ('original', 'snapshot'):
            checked_pin(pair[key], evidence)
    for pair in original['reviewed_sources'].values():
        checked_pin(pair['snapshot'], evidence)
        require(all(pair['snapshot'][key] == pair['original'][key] for key in ('bytes', 'sha256')),
                'historical source snapshot differs from its recorded original')
    cleanup = document(original['cleanup']['snapshot']['path'], evidence)
    require(cleanup['status'] == 'cleanup-confirmed'
            and cleanup['safe_to_release_source_freeze'] is True
            and all(row['original_reaped'] for row in [cleanup['runner'], cleanup['coordinator'],
                    *cleanup['workers'], *cleanup['observed_descendants']]),
            'original cohort cleanup is unconfirmed')
    recorded_cases = finding['cases']
    require(len(recorded_cases) == 3 and {row['name'] for row in recorded_cases} == expected
            and all(row['classname'] == module and row['nodeid'] == file + '::' + row['name']
                    for row in recorded_cases), 'original exact failed identities differ')
    for row in recorded_cases:
        for key, artifact in row['evidence'].items():
            if key == 'artifact_inventory':
                checked_pin(artifact, evidence)
            else:
                checked_pin(artifact['original'], evidence)
                checked_pin(artifact['snapshot'], evidence)
    proof = test_proof(file, None, directories, head, evidence)
    rows = cases(OUT / proof['cohort'] / 'pytest.xml')
    exact = [row for row in rows if row['classname'] == module and row['name'] in expected]
    require(len(exact) == 3 and {row['name'] for row in exact} == expected
            and all(row['status'] == 'passed' for row in exact),
            'the three exact failed parameter identities did not all pass')
    details.extend([proof, {'exact_failed_identities_passed': sorted(expected),
        'original_interrupted_cohort': original['cohort'], 'original_source_head': original['source_head'],
        'original_returncode': 2, 'original_junit_entries': 241,
        'original_log_passes': 237, 'original_failures': 3,
        'cause_established': False, 'source_correction_claimed': False}])
    return ('Required clean whole-file rerun verified in its recorded execution mode; '
            'original parallel failures and interrupted evidence retained, latency cause unresolved, '
            'no code correction claimed; lead filing remains required.')


def close_legacy_rerun(identity, directories, head, evidence, details):
    original = ledger(identity, 'review-legacy-component-failures-v2.json', evidence)
    finding, = [row for row in original['findings'] if row['finding_id'] == identity]
    file = finding['required_clean_full_file']
    require(file in ('tests/test_native_execution.py', 'tests/test_native_receipt_origin_reporting.py'),
            'unexpected legacy required file')
    require(finding['baseline_reproduction_established'] is False
            and finding['internal_or_timing_cause_established'] is False,
            'legacy causal disposition changed; require explicit review')
    checked_pin(finding['artifact_proof']['snapshot'], evidence)
    checked_pin(finding['source_proof'], evidence)
    collection = document(OUT / 'legacy-collection-census/census.json', evidence)
    require(collection['kind'] == 'pytest_collection_census' and collection['status'] == 'verified'
            and collection['returncode'] == 0 and collection['tests_executed'] is False,
            'successful collection census is missing')
    require(collection['cwd'] == str(ROOT) and set(collection['files']) == {
        'tests/test_native_execution.py', 'tests/test_native_receipt_origin_reporting.py'},
        'collection used a different checkout or file set')
    for key in ('command', 'log', 'nodes', 'producer', 'inventory_helper'):
        checked_pin(collection[key], evidence)
    for source in collection['source_pins'].values():
        checked_pin(source, evidence)
    require(file in collection['source_pins'] and collection['source_pins'][file] == pin(ROOT / file),
            'collection does not pin the current required test file')
    collect_command = json.loads(Path(collection['command']['path']).read_bytes())
    require(collect_command['kind'] == 'pytest_collection_only'
            and '--collect-only' in collect_command['command']
            and collect_command['cwd'] == str(ROOT)
            and collect_command['head'] == collection['head']
            and collect_command['source_pins'] == collection['source_pins']
            and collect_command['source_inventory']['ignored_and_hidden_files_included'] is True,
            'collection provenance differs from its result')
    nodes = json.loads(Path(collection['nodes']['path']).read_bytes())
    require(collection['node_count'] == len(nodes)
            and collection['nodes_by_file'] == dict(Counter(row['file'] for row in nodes)),
            'collection counts differ from saved node identities')
    expected_rows = [row for row in nodes if row['file'] == file]
    expected = {(row['classname'], row['name']) for row in expected_rows}
    require(bool(expected) and len(expected) == len(expected_rows), 'empty or duplicate collection identities')
    filters = ('-k', '-m', '--deselect', '--ignore', '--ignore-glob', '--last-failed', '--lf', '--collect-only')
    invocations = []
    for directory in directories:
        command = json.loads((directory / 'command.json').read_bytes())
        filtered = any(arg == flag or arg.startswith(flag + '=')
                       for arg in command.get('command', [])[3:] for flag in filters)
        if selects(command, file, None) and not filtered:
            invocations.append((directory, command))
    require(bool(invocations), 'no complete-file legacy rerun invocation')
    directory, command = invocations[-1]
    for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log'):
        evidence.append(pin(directory / name))
    outcome = json.loads((directory / 'outcome.json').read_bytes())
    require(command['cwd'] == str(ROOT)
            and command['source_inventory']['ignored_and_hidden_files_included'] is True,
            'legacy rerun lacks the assigned checkout/source inventory')
    reuse_details = []
    for label, recorded in (('collection', collection['head']), ('rerun', command['head'])):
        require(isinstance(recorded, str) and len(recorded) == 40
                and git('merge-base', '--is-ancestor', recorded, head).returncode == 0,
                label + ' source is not an ancestor of final source')
        if git('diff', '--exit-code', recorded, head, '--', *SOURCE_SCOPE).returncode != 0:
            helper = ROOT / 'scripts/adhoc/g2_legacy_leaf_reuse_6217_f4_20261114.py'
            evidence.append(pin(helper))
            reuse = runpy.run_path(str(helper))['validate_reuse'](
                ROOT, OUT, recorded, head, file, directory)
            require(reuse['passed'] is True, label + ' lacks the exact approved legacy149 reuse proof')
            for artifact in reuse['evidence']:
                checked_pin(artifact, evidence)
            reuse_details.append({'label': label, 'recorded_head': recorded, **reuse})
    require(git('diff', '--exit-code', 'HEAD', '--', *SOURCE_SCOPE).returncode == 0,
            'tracked source changed after HEAD')
    rows = cases(directory / 'pytest.xml')
    totals = Counter(row['status'] for row in rows)
    require(outcome['returncode'] == 0 and totals['failed'] == totals['error'] == 0
            and outcome['counts'] == {'total': len(rows), 'failed': totals['failed'],
                                     'error': totals['error'], 'skipped': totals['skipped']},
            'latest whole-file rerun failed or has inconsistent JUnit/outcome evidence')
    module = file[:-3].replace('/', '.')
    chosen = [row for row in rows if row['classname'] == module or row['classname'].startswith(module + '.')]
    actual = {(row['classname'], row['name']) for row in chosen}
    require(len(actual) == len(chosen) and actual == expected,
            'whole-file JUnit identities differ from actual pytest collection')
    require(all(row['status'] == 'passed' for row in chosen), 'legacy full file includes a failed, errored or skipped case')
    formerly_failed = {(row['classname'], row['name']) for row in finding['cases']}
    require(bool(formerly_failed) and formerly_failed <= actual,
            'one or more original failed/error nodes are absent from the clean rerun')
    details.append({'file': file, 'cohort': directory.name, 'all_cases_passed': len(chosen),
        'original_recorded_head': command['head'], 'collection_recorded_head': collection['head'],
        'narrow_f4_reuse': reuse_details,
        'expected_from_pytest_collection': len(expected),
        'original_failed_nodes_now_passed': [{'classname': cls, 'name': name}
                                            for cls, name in sorted(formerly_failed)],
        'baseline_reproduction_established': False, 'internal_or_timing_cause_established': False,
        'code_correction_claimed': False})
    return 'Later complete-file rerun passed every collected node, including all originally failed/error nodes. Original failure and undetermined cause are retained; no code correction, baseline reproduction or timing cause is claimed.'


def close_proposal(evidence, details):
    identity = 'G2-REVIEW-6217-F1'
    ledger(identity, 'review-followups.json', evidence)
    proposal = document(OUT / 'issue-6217-proposal.json', evidence)
    evidence.append(pin(OUT / 'issue-6217-proposal.md'))
    correction = proposal['review_correction']
    require(correction['finding_id'] == identity and correction['status'] == 'corrected',
            'proposal lacks this correction')
    checked_pin(correction['prior_proposal'], evidence)
    require(pin(OUT / 'issue-6217-proposal.json')['sha256'] != correction['prior_proposal']['sha256'],
            'proposal remains the original bytes')
    recommendation = '\n'.join(proposal['recommendation'])
    require('existing first_stop and its failed gate' in recommendation,
            'proposal does not retain the existing stop/gate mechanism')
    require('optional, not a prerequisite' in recommendation,
            'proposal still requires a new evidence field')
    require('after that cutoff' in proposal['decision_required']
            and 'later-signal policy' in proposal['why_no_partial_patch'],
            'proposal does not identify the cutoff and later-signal choice')
    require(proposal['status'] == 'not fixed' and proposal['applied_source_changes'] == []
            and proposal['tests_run_for_proposal'] == [], 'proposal overstates production status')
    details.append({'issue': 6217, 'historical_proposal_status': 'not fixed',
                    'superseded_by_finding': 'G2-REVIEW-6217-F2',
                    'verified_scope': 'historical proposal rationale correction only'})
    return 'Historical proposal correction verified: existing first_stop/gate suffice; a new field is optional. Its implementation deferral was subsequently superseded under F2; this F1 closure makes no current production-status claim.'


def publication_binding(head, evidence):
    value = ledger('G2-REVIEW-6217-F2',
                   'proposal-6217-implementation/review-6217-superseding.json', evidence)
    require(git('merge-base', '--is-ancestor', APPLIED_6217, head).returncode == 0,
            '6217 implementation commit is not in current source history')
    correction = ledger('G2-REVIEW-6217-F4', 'review-6217-f4-confirmed.json', evidence)
    require(correction['correction_commit'] == CORRECTED_6217_TEST
            and correction['production_commit'] == APPLIED_6217
            and git('merge-base', '--is-ancestor', CORRECTED_6217_TEST, head).returncode == 0,
            '6217 oracle correction is not the reviewed commit')
    for key in ('original_review', 'before_closure', 'corrected_test', 'patch', 'producer'):
        checked_pin(correction[key], evidence)
    checked_pin(correction['pytest_failure_attribution']['traceback'], evidence)
    for artifact in correction['interrupted_cohort']['artifacts']:
        checked_pin(artifact, evidence)
    checked_pin(correction['interrupted_cohort']['cleanup'], evidence)
    require(git('diff', '--name-only', APPLIED_6217, CORRECTED_6217_TEST, '--', *SOURCE_SCOPE).stdout.decode().splitlines()
            == [PUBLICATION_FILE], '6217 correction includes an unreviewed source-scope change')
    require(git('diff', '--exit-code', CORRECTED_6217_TEST, head, '--', *SOURCE_SCOPE).returncode == 0,
            'source changed after the reviewed 6217 oracle correction')
    checked_pin(value['original_proposal_preserved'], evidence)
    candidate_root = OUT / 'proposal-6217-implementation/candidate'
    for candidate in value['candidates']:
        checked_pin(candidate, evidence)
        relative = Path(candidate['path']).relative_to(candidate_root).as_posix()
        current = pin(ROOT / relative)
        committed = git('show', APPLIED_6217 + ':' + relative)
        require(committed.returncode == 0 and hashlib.sha256(committed.stdout).hexdigest() == candidate['sha256'],
                'original committed 6217 implementation differs from reviewed candidate: ' + relative)
        if relative == PUBLICATION_FILE:
            corrected = git('show', CORRECTED_6217_TEST + ':' + relative)
            require(corrected.returncode == 0
                    and hashlib.sha256(corrected.stdout).hexdigest() == correction['corrected_test']['sha256']
                    and current['sha256'] == correction['corrected_test']['sha256'],
                    'current publication test differs from committed corrected oracle')
        else:
            require(current['sha256'] == candidate['sha256'],
                    'current 6217 production differs from reviewed implementation: ' + relative)
        evidence.append(current)
    return {'issue': 6217, 'applied_commit': APPLIED_6217,
            'test_correction_commit': CORRECTED_6217_TEST, 'production_unchanged': True,
            'historical_candidate_ledger_preserved': True}


def close_publication_repair(directories, head, evidence, details):
    details.append(publication_binding(head, evidence))
    details.append(test_proof(PUBLICATION_FILE, None, directories, head, evidence))
    for function in PUBLICATION_TESTS:
        details.append(test_proof(PUBLICATION_FILE, function, directories, head, evidence))
    return '6217 production remains the reviewed 2070 implementation; the publication oracle is the committed 21367471 correction. Every publication regression and the full file passed on equivalent current source; historical deferral is superseded.'


def close_publication_oracle(directories, head, evidence, details):
    details.append(publication_binding(head, evidence))
    details.append(test_proof(PUBLICATION_FILE, None, directories, head, evidence))
    details.append(test_proof(PUBLICATION_FILE, PUBLICATION_TESTS[-1], directories, head, evidence))
    return 'Confirmed line157 oracle defect is corrected using established publication bytes. Fresh public-signal regressions and the complete publication file passed; original traceback/interrupted evidence remain retained and no runtime-hang cause is claimed.'


def retain_withdrawal(evidence, details):
    identity = 'G2-REVIEW-6217-F3'
    value = ledger(identity, 'review-6217-f3-withdrawn-frozen.json', evidence)
    require(value['status'] == 'disputed; withdrawn by reviewer'
            and value['candidate_changes'] == [] and value['tests_run'] == [],
            'F3 is not the saved withdrawal without a code correction')
    for key in ('original_review_ledger', 'producer', 'reconciliation_producer', 'reviewed_patch'):
        checked_pin(value[key], evidence)
    original = json.loads(Path(value['original_review_ledger']['path']).read_bytes())
    require(original['finding_id'] == identity and original['status'] == value['status']
            and original['disposition'] == value['disposition'], 'withdrawal disposition differs from original ledger')
    resolution = value['historical_source_resolution']
    checked_pin(resolution['immutable_snapshot'], evidence)
    require(resolution['recorded_sha256'] == resolution['immutable_snapshot']['sha256']
            == original['source_analysis'][0]['source']['sha256'],
            'historical source does not resolve to the reviewed immutable bytes')
    for row in value['source_analysis']:
        checked_pin(row['source'], evidence)
    details.append({'disposition': 'withdrawn', 'scope': value['scope'],
                    'code_correction_claimed': False, 'test_success_claimed': False})
    return 'Withdrawn false finding retained with the original ledger and immutable reviewed sources; no code correction or test success is claimed. ' + value['disposition']


def close_runner(evidence, details):
    identity = 'G2-REVIEW-RUNNER-F1'
    ledger(identity, 'review-runner.json', evidence)
    result = document(OUT / 'runner-inventory-verification/result.json', evidence)
    require(result['finding_id'] == identity and result['status'] == 'verified', 'runner verification identity/status differs')
    checked_pin(result['runner'], evidence)
    checked_pin(result['review'], evidence)
    evidence.append(pin(ROOT / 'scripts/adhoc/verify_g2_runner_inventory_20261114.py'))
    rows = result['cases']
    require(len(rows) == 11 and {row['case'] for row in rows} == RUNNER_CASES,
            'runner verification lacks the eleven named counterexamples')
    require(result['passed'] == 11 and result['failed'] == 0 and all(row['passed'] is True for row in rows),
            'runner verification has incomplete/failing cases')
    details.append({'cases': 11, 'passed': 11, 'scope': result['scope']})
    return 'All eleven inventory/selector harness cases passed; retained runner and original finding pins match. This is not project pytest proof.'


def close_scheduled_runner(evidence, details):
    identity = 'G2-REVIEW-SCHEDULED-RUNNER-F1'
    ledger(identity, 'review-scheduled-runner.json', evidence)
    correction = document(OUT / 'scheduled-runner-review-20261114/correction.json', evidence)
    require(correction['finding_id'] == identity and correction['runtime_verified'] is False,
            'original static scheduled-runner correction record changed')
    for key in ('original_review', 'before_helper', 'corrected_snapshot', 'current_driver',
                'base_runner', 'patch', 'producer'):
        checked_pin(correction[key], evidence)
    require(Path(correction['current_driver']['path']) == ROOT / 'scripts/adhoc/run_g2_scheduled_checks_20261114.py'
            and Path(correction['base_runner']['path']) == ROOT / 'scripts/adhoc/run_g2_checks_20261114.py',
            'scheduled-runner correction names different drivers')
    before = Path(correction['before_helper']['path']).read_text()
    after = Path(correction['corrected_snapshot']['path']).read_text()
    old = "    subprocess.check_call(['git', 'diff', '--exit-code', 'HEAD', '--', 'src', 'tests', *inventory['selected_paths']], cwd=ROOT)\n"
    new = "    subprocess.check_call(['git', 'diff', '--exit-code', 'HEAD', '--', *SOURCE_SCOPE, *inventory['selected_paths']], cwd=ROOT)\n"
    require(before.count(old) == 1 and before.replace(old, new) == after
            and correction['corrected_snapshot']['sha256'] == correction['current_driver']['sha256'],
            'scheduled-runner differs from the reviewed one-line scope correction')
    details.append({'static_correction_verified': True, 'runtime_proof_separate': True,
                    'historical_static_record_runtime_verified': False})
    directory = OUT / 'scheduled-canary'
    command = document(directory / 'command.json', evidence)
    outcome = document(directory / 'outcome.json', evidence)
    evidence.extend(pin(directory / name) for name in ('pytest.xml', 'pytest.log'))
    node = 'tests/test_native_sequence_start.py::test_sequence_start_accepts_registration_above_quota_event_limit'
    schedule = ['-n', '4', '--dist', 'load', '--maxschedchunk=1']
    argv = [str(ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'), '-m', 'pytest', '-q', '-p',
            'no:cacheprovider', node, *schedule, '--basetemp=' + str(directory / 'cases'),
            '--junitxml=' + str(directory / 'pytest.xml')]
    require(command['command'] == argv and command['cwd'] == str(ROOT)
            and command['producer'] == correction['current_driver']
            and command['base_runner'] == correction['base_runner']
            and command['canary'] is True and command['scheduling'] == schedule,
            'scheduled canary does not match the exact reviewed driver, node and scheduling')
    require(command['environment'] == {'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONPYCACHEPREFIX': str(directory / 'pycache'), 'TMPDIR': str(directory)}
            and command['source_inventory']['ignored_and_hidden_files_included'] is True
            and command['source_inventory']['selected_paths'] == [node.partition('::')[0]],
            'scheduled canary environment or source inventory differs')
    head = git('rev-parse', 'HEAD').stdout.decode().strip()
    require(git('merge-base', '--is-ancestor', command['head'], head).returncode == 0
            and git('diff', '--exit-code', command['head'], head, '--', *SOURCE_SCOPE).returncode == 0
            and git('diff', '--exit-code', 'HEAD', '--', *SOURCE_SCOPE).returncode == 0,
            'scheduled canary source is not equivalent to clean current source')
    expected = {'classname': 'tests.test_native_sequence_start',
                'name': node.partition('::')[2], 'status': 'passed'}
    require(outcome['returncode'] == 0 and outcome['counts'] == {'total': 1, 'failed': 0, 'error': 0, 'skipped': 0}
            and cases(directory / 'pytest.xml') == [expected],
            'scheduled canary lacks its one clean passing JUnit case')
    artifact = next((path for path in sorted((directory / 'cases').rglob('*'))
                     if path.is_file() and path.stat().st_size), None)
    require(artifact is not None, 'scheduled canary persisted no nonempty case artifact')
    evidence.append(pin(artifact))
    details.append({'runtime_verified': True, 'cohort': 'scheduled-canary', 'node': node,
                    'recorded_head': command['head'], 'workers': 4, 'scheduling': schedule})
    return 'Scheduled-runner scope correction is statically verified and its exact four-worker scheduled canary passed with a nonempty case artifact. This is one-canary proof, not completed batch coverage; lead filing remains required.'


def close_report(evidence, details):
    identity = 'G2-REVIEW-REPORT-F1'
    ledger(identity, 'review-report.json', evidence)
    result = document(OUT / 'report-closure-pin-verification-after-engine-freshness/result.json', evidence)
    require(result['finding_id'] == identity and result['status'] == 'verified'
            and result['verified_entrypoint'] == 'review_ledger',
            'report closure-pin verification is incomplete')
    checked_pin(result['reporter'], evidence)
    checked_pin(result['producer'], evidence)
    checked_pin(result['reviewed_source'], evidence)
    checked_pin(result['ledger'], evidence)
    rows = result['cases']
    expected = {'valid_nested_artifact', 'changed_nested_artifact', 'missing_nested_artifact'}
    require(result['passed'] == 3 and result['failed'] == 0
            and len(rows) == 3 and {row['case'] for row in rows} == expected
            and all(row['passed'] is True for row in rows),
            'report closure-pin counterexamples are incomplete or failing')
    details.append({'cases': 3, 'passed': 3, 'entrypoint': 'review_ledger',
                    'scope': 'pure saved closure/pin validation, not project pytest'})
    return 'Actual review_ledger accepted valid nested evidence and rejected changed/missing nested artifacts; reporter and verification producer pins match.'


def close_report_discovery(evidence, details):
    identity = 'G2-REVIEW-REPORT-F2'
    ledger(identity, 'review-report-f2.json', evidence)
    result = document(OUT / 'report-cohort-discovery-after-engine-freshness/result.json', evidence)
    require(result['finding_id'] == identity and result['status'] == 'verified',
            'cohort discovery verification is incomplete')
    for name in ('reporter', 'closure', 'producer', 'ledger'):
        checked_pin(result[name], evidence)
    expected = {'real_equals', 'real_split', 'relative_outputs', 'copied_archive',
                'missing_basetemp', 'missing_junitxml', 'duplicate_destination',
                'mixed_destinations', 'malformed_argv', 'missing_command',
                'invalid_json', 'newer_archive_excluded', 'actual_saved_original', 'actual_saved_archive'}
    rows = result['cases']
    require(len(rows) == len(expected) and {row['case'] for row in rows} == expected
            and result['passed'] == len(expected) and result['failed'] == 0
            and all(row['passed'] is True for row in rows),
            'cohort discovery counterexamples are incomplete or failing')
    details.append({'cases': len(rows), 'passed': len(rows), 'scope': result['scope']})
    return 'Both helpers bind saved output destinations to the containing directory, retain copied archives separately, and reject malformed identities. No observed false acceptance or project test result is claimed.'


def close_auxiliary_discovery(evidence, details):
    identity = 'G2-REVIEW-REPORT-F4'
    ledger(identity, 'review-report-f4.json', evidence)
    result = document(OUT / 'report-auxiliary-discovery-verification-after-engine-freshness/result.json', evidence)
    require(result['finding_id'] == identity and result['status'] == 'verified',
            'auxiliary discovery verification is incomplete')
    for key in ('reporter', 'closure', 'producer', 'ledger', 'auxiliary_outcome'):
        checked_pin(result[key], evidence)
    for artifact in result['reviewed_sources']:
        checked_pin(artifact, evidence)
    expected = {'known_auxiliary_retained', 'unknown_outcome_only_invalid', 'changed_known_hash_invalid',
                'known_with_junit_invalid', 'known_with_log_invalid', 'known_with_command_invalid',
                'changed_provenance_invalid', 'missing_provenance_invalid'}
    rows = result['cases']
    require(result['passed'] == 8 and result['failed'] == 0 and len(rows) == 8
            and {row['case'] for row in rows} == expected and all(row['passed'] is True for row in rows),
            'auxiliary discovery counterexamples are incomplete or failing')
    details.append({'cases': 8, 'passed': 8, 'scope': result['scope']})
    return 'Only the exact pinned completed bytecode outcome is retained as auxiliary; it never becomes a test cohort. Unknown outcomes, pytest markers without valid commands, and changed/missing provenance refuse verification.'


def close_bytecode(evidence, details):
    identity = 'G2-REVIEW-BYTECODE-F1'
    ledger(identity, 'review-bytecode.json', evidence)
    result = document(OUT / 'bytecode-preservation-verification/result.json', evidence)
    require(result['finding_id'] == identity and result['status'] == 'verified'
            and result['verified_entrypoint'] == 'rename_and_verify',
            'bytecode interruption verification is incomplete')
    for name in ('helper', 'producer', 'reviewed_source', 'ledger'):
        checked_pin(result[name], evidence)
    require(Path(result['helper']['path']) == ROOT / 'scripts/adhoc/preserve_g2_source_bytecode_20261114.py'
            and Path(result['ledger']['path']) == OUT / 'review-bytecode.json',
            'bytecode proof does not name the current helper and original ledger')
    require(result['helper']['sha256'] == result['reviewed_source']['sha256']
            and result['helper']['bytes'] == result['reviewed_source']['bytes'],
            'bytecode proof snapshot differs from the current helper')
    expected = {'interruption_after_rename', 'interruption_before_rename', 'ambiguous_locations'}
    rows = result['cases']
    require(result['passed'] == 3 and result['failed'] == 0 and len(rows) == 3
            and {row['case'] for row in rows} == expected
            and all(row['passed'] is True for row in rows),
            'bytecode interruption counterexamples are incomplete or failing')
    for row in rows:
        checked_pin(row['outcome'], evidence)
        checked_pin(row['retained'], evidence)
    original = result['original_counterexample']
    require(original['false_negative_reproduced'] is True,
            'original bytecode failure-ledger counterexample was not reproduced')
    checked_pin(original['outcome'], evidence)
    checked_pin(original['preserved'], evidence)
    details.append({'cases': 3, 'passed': 3, 'entrypoint': 'rename_and_verify',
                    'scope': 'Pure synthetic filesystem interruption proof; actual bytecode preservation is a separate action.'})
    return 'Synthetic interruption checks verify fresh location evidence after rename, before rename and for ambiguous locations. Actual source bytecode preservation is not inferred; lead filing remains required.'


def close_bytecode_pins(evidence, details):
    identity = 'G2-REVIEW-REPORT-F3'
    ledger(identity, 'review-report-f3.json', evidence)
    result = document(OUT / 'bytecode-closure-pin-verification-after-engine-freshness/result.json', evidence)
    require(result['finding_id'] == identity and result['status'] == 'verified'
            and result['verified_entrypoint'] == 'close_bytecode',
            'bytecode closure-pin verification is incomplete')
    for key in ('closure', 'producer', 'reviewed_source', 'ledger'):
        checked_pin(result[key], evidence)
    require(Path(result['closure']['path']) == ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'
            and Path(result['ledger']['path']) == OUT / 'review-report-f3.json'
            and result['closure']['sha256'] == result['reviewed_source']['sha256']
            and result['closure']['bytes'] == result['reviewed_source']['bytes'],
            'bytecode closure proof does not pin the current reviewed helper')
    expected = {'valid_nested_bytecode_artifact', 'changed_nested_bytecode_artifact',
                'missing_nested_bytecode_artifact'}
    rows = result['cases']
    require(result['passed'] == 3 and result['failed'] == 0 and len(rows) == 3
            and {row['case'] for row in rows} == expected
            and all(row['passed'] is True and row['nested_artifacts_checked'] == 8 for row in rows),
            'bytecode closure-pin counterexamples are incomplete or failing')
    details.append({'cases': 3, 'passed': 3, 'nested_artifacts_per_case': 8,
                    'entrypoint': 'close_bytecode', 'scope': result['scope']})
    return 'Actual close_bytecode accepts and exports all eight valid nested artifact pins and refuses each changed/missing artifact. Historical evidence remains unchanged; lead filing remains required.'


def review_6224(head):
    names = ('src/data_sheets_schema/native_launch_sequence.py',
             'src/data_sheets_schema/native_path_identity.py',
             'src/data_sheets_schema/native_u4b_policy.py',
             'src/data_sheets_schema/native_launch_entry.py',
             'tests/test_native_launch_sequence_paths.py',
             'tests/test_native_launch_sequence.py', 'tests/test_native_launch_entry.py',
             'tests/test_native_sequence_start.py')
    reviewed = []
    for name in names:
        result = git('show', REVIEWED_6224 + ':' + name)
        require(result.returncode == 0, 'reviewed commit blob missing: ' + name)
        reviewed.append({'path': name, 'commit': REVIEWED_6224, 'bytes': len(result.stdout),
                         'sha256': hashlib.sha256(result.stdout).hexdigest()})
    equivalent = git('diff', '--exit-code', REVIEWED_6224, head, '--', *names).returncode == 0
    return {'issue': 6224, 'review_kind': 'Separate read-only adversarial review; no edits, commits or tests.',
        'reviewed_commit': REVIEWED_6224, 'recorded_head': head,
        'reviewed_files_unchanged_at_recording_head': equivalent,
        'verdict': 'No findings in the reviewed commit.', 'findings': [],
        'issue_evidence': pin(OUT / 'baseline/issue-6224.json'), 'reviewed_blobs': reviewed,
        'trace': [
            {'path': names[0], 'line': 73, 'finding': 'Output separation uses registration bytes already captured by the trusted entry.'},
            {'path': names[0], 'line': 80, 'finding': 'Packet and guard use physical overlap checks against attempt, evidence and capture-state roots.'},
            {'path': names[0], 'line': 86, 'finding': 'Capture output must exactly equal validated registered capture-state and remain disjoint from attempt/evidence.'},
            {'path': names[0], 'line': 262, 'finding': 'Preflight precedes packet.mkdir at line 268, sequence_start at line 279, script writing and claim.'},
            {'path': names[1], 'finding': 'Existing ancestors/inodes establish physical containment; ambiguous prospective case/Unicode aliases refuse.'},
            {'path': names[4], 'finding': 'Refusal harness snapshots the entire tree including hidden/ignored entries and prohibits host probe, claim and Popen; the exact-root fake-flow test asserts success.'},
            {'path': names[5], 'line': 110, 'finding': 'Preservation helper retains every prior journal byte and all capture slots, allowing only sequence_start additions when explicitly requested.'}],
        'limitation': 'Static review only; no test outcome is inferred from this no-findings record.'}


def write_new(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    require(path.read_bytes() == raw, 'written review artifact differs')


def superseded_cohort():
    cleanup_path = OUT / 'engine-admission-interruption-20261114/cleanup-1794630386052545000.json'
    evidence = []
    cleanup = document(cleanup_path, evidence)
    require(cleanup['status'] == 'cleanup-confirmed' and cleanup['safe_to_release_source_freeze'] is True,
            'superseded cohort cleanup was not confirmed')
    require(all(row['original_reaped'] is True for row in (
        cleanup['coordinator'], cleanup['runner'], *cleanup['workers'], *cleanup['observed_descendants'])),
        'superseded cohort retained an unreaped observed process')
    for artifact in cleanup['artifacts'].values():
        if artifact is not None:
            checked_pin(artifact, evidence)
    outcome = json.loads((OUT / 'engine-admission/outcome.json').read_bytes())
    require(outcome['returncode'] == 2, 'superseded cohort interruption outcome changed')
    return {'status': 'interrupted; incomplete', 'returncode': 2, 'evidence': evidence,
        'reason': 'Pre-6217 validation was superseded. Clean JUnit entries from this interrupted run do not prove completed tests or complete-file coverage.'}


def proposal_applicability(review, proposal, head):
    evidence = []
    for artifact in review['current_sources']:
        checked_pin(artifact, evidence)
    proposal_head = proposal['head']
    scope = tuple(name for name in SOURCE_SCOPE if name != 'tests')
    require(proposal_head == review['reviewed_proposal_head']
            and git('merge-base', '--is-ancestor', proposal_head, head).returncode == 0
            and git('diff', '--exit-code', proposal_head, head, '--', *scope).returncode == 0,
            '6207 proposal production/controller/config source is no longer equivalent')
    changed = git('diff', '--name-only', proposal_head, head, '--', 'tests').stdout.decode().splitlines()
    require(changed == [PUBLICATION_FILE]
            and git('merge-base', '--is-ancestor', CORRECTED_6217_TEST, head).returncode == 0
            and git('diff', '--exit-code', CORRECTED_6217_TEST, head, '--', *SOURCE_SCOPE).returncode == 0,
            '6207 proposal has test drift beyond the reviewed F4 leaf correction')
    correction = ledger('G2-REVIEW-6217-F4', 'review-6217-f4-confirmed.json', evidence)
    checked_pin(correction['corrected_test'], evidence)
    current = pin(ROOT / PUBLICATION_FILE)
    require(current['sha256'] == correction['corrected_test']['sha256'],
            '6207 applicability does not match corrected F4 test bytes')
    evidence.append(current)
    return {'passed': True, 'proposal_head_retained': proposal_head, 'current_head': head,
        'production_scope_unchanged': list(scope), 'current_sources_checked': evidence,
        'reviewed_test_drift': {'path': PUBLICATION_FILE, 'commit': CORRECTED_6217_TEST,
                                'finding_id': 'G2-REVIEW-6217-F4'},
        'scope': 'Unapplied proposal applicability only; no test-proof allowance, patch application or pin rotation.'}


def main():
    head_result = git('rev-parse', 'HEAD')
    require(head_result.returncode == 0, 'cannot identify final HEAD')
    head = head_result.stdout.decode().strip()
    discovery = discover_cohorts(OUT)
    directories = cohort_directories(discovery)
    findings, proofs = [], {}
    for identity, ledger_name, requirements in TEST_FINDINGS:
        row, details = close(identity, lambda evidence, details: close_tests(
            identity, ledger_name, requirements, directories, head, evidence, details))
        findings.append(row)
        proofs[identity] = details
    for identity, action in (('G2-REVIEW-6217-F1', close_proposal),
                             ('G2-REVIEW-6217-F3', retain_withdrawal), ('G2-REVIEW-RUNNER-F1', close_runner),
                             ('G2-REVIEW-REPORT-F1', close_report),
                             ('G2-REVIEW-REPORT-F2', close_report_discovery),
                             ('G2-REVIEW-REPORT-F3', close_bytecode_pins),
                             ('G2-REVIEW-REPORT-F4', close_auxiliary_discovery),
                             ('G2-REVIEW-SCHEDULED-RUNNER-F1', close_scheduled_runner),
                             ('G2-REVIEW-BYTECODE-F1', close_bytecode)):
        row, details = close(identity, action)
        if identity == 'G2-REVIEW-6217-F3' and row['status'] == 'verified':
            row['status'] = 'withdrawn'
        findings.append(row)
        proofs[identity] = details
    identity = 'G2-REVIEW-6217-F2'
    row, details = close(identity, lambda evidence, details: close_publication_repair(
        directories, head, evidence, details))
    findings.append(row)
    proofs[identity] = details
    identity = 'G2-REVIEW-6217-F4'
    row, details = close(identity, lambda evidence, details: close_publication_oracle(
        directories, head, evidence, details))
    findings.append(row)
    proofs[identity] = details
    identity = 'G2-REVIEW-ENGINE-FRESHNESS-F1'
    row, details = close(identity, lambda evidence, details: close_engine_freshness(
        directories, head, evidence, details))
    findings.append(row)
    proofs[identity] = details
    for identity in ('G2-REVIEW-LEGACY-F1', 'G2-REVIEW-LEGACY-F2'):
        row, details = close(identity, lambda evidence, details: close_legacy_rerun(
            identity, directories, head, evidence, details))
        findings.append(row)
        proofs[identity] = details
    review_path = OUT / 'review-6224-final.json'
    closure_path = OUT / 'final-review-closure.json'
    require(not review_path.exists() and not closure_path.exists(), 'final review outputs already exist; preserve prior evidence')
    review_6207_path = OUT / 'review-6207-after-6217.json'
    review_6207 = json.loads(review_6207_path.read_bytes())
    require(review_6207['issue'] == 6207 and review_6207['status'] == 'no-new-findings'
            and review_6207['findings'] == []
            and review_6207['review_mode'] == 'read-only static adversarial review',
            '6207 review is not the recorded static no-findings review')
    require(all(review_6207['actions'][name] is False for name in (
        'tests_executed', 'candidate_executed', 'patch_applied', 'source_or_tests_edited', 'commits_created'))
        and review_6207['test_roster']['test_results_claimed_by_this_review'] is False,
        '6207 review overstates execution or acceptance')
    for key in ('patch', 'proposal', 'generator'):
        checked_pin(review_6207[key], [])
    require(Path(review_6207['proposal']['path']) == OUT / 'proposal-6207-after-6217/proposal.json',
            '6207 review must describe the refreshed proposal, not historical evidence')
    proposal_6207 = json.loads(Path(review_6207['proposal']['path']).read_bytes())
    require(all(proposal_6207[name] is False for name in ('applied', 'pin_rotation_applied', 'tests_run')),
            '6207 proposal must remain unapplied and untested')
    applicability = proposal_applicability(review_6207, proposal_6207, head)
    obsolete = superseded_cohort()
    write_new(review_path, review_6224(head))
    result = {'head': head, 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'findings': findings, 'verification_details': proofs, 'cohort_artifact_discovery': discovery,
        'review_6207': pin(review_6207_path),
        'review_6207_applicability': applicability,
        'historical_review_6207': pin(OUT / 'review-6207-final.json'),
        'superseded_cohort': obsolete,
        'review_6224': pin(review_path), 'producer': pin(Path(__file__).resolve()),
        'original_ledgers_unchanged': True,
        'limitations': ['No tests or production code imports were run by this helper.',
            'Missing, failing, skipped or source-inequivalent required proof stays not_verified.',
            'Closure does not file a GitHub issue; every original lead-filing requirement remains.',
            'Source commits alone do not establish test success.']}
    write_new(closure_path, result)
    print(json.dumps({'output': pin(closure_path), 'review_6224': pin(review_path),
                      'statuses': {row['id']: row['status'] for row in findings}}, indent=2))


if __name__ == '__main__':
    main()
