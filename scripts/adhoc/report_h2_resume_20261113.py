#!/usr/bin/env python3
"""Produce the resumed H2 integration handoff, 2026-11-13.
Inputs: saved JUnit, launch commands/outcomes, timing sidecars, source audit,
review, compatibility proof and commit map in sibling scratch-h2-resume-20261113.
Outputs: answer-first Markdown and JSON in the assigned report worktree.
Issues 6193-6202 and H1-420-F1; no tests, launches, source edits or publishing.
"""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-h2-resume-20261113'
REPORT = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs'
STEM = 'codex-h2-integration-fixes-20261113'
PUBLIC = {
    'correction': 'tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion',
    'omissions': 'tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses',
    'pending': 'tests/test_native_pending_public_completion.py::test_pending_floor_public_completion_retains_diagnostic_reading',
}
COMMIT_ISSUES = {
    '0b7ab4669': ['6200'], 'c03dc762f': ['6201', '6202'],
    '54d724fb7': ['6193', '6194'], 'f90492c46': ['6195', '6196'],
    '3fdaf7c6d': ['6197', '6198', '6199'], 'f59b0e8e8': ['6202'],
    'ca4685f65': ['6195', '6196'], 'c615b9685': ['6194'],
    'd457ffa65': ['6193', '6194'], '7cae29746': ['6198'], '82a5bcf41': ['6201'],
}
PROOFS = {
    '6193': [('test_expiry_does_not_interrupt_slow_nested_cleanup', 1),
             ('test_stalled_fifo_open_is_interrupted_and_alarm_is_restored', 2)],
    '6194': [('test_late_post_cancel_alarm_is_consumed_before_restoration', 1),
             ('test_teardown_step_exception_does_not_skip_remaining_restoration', 7),
             ('test_existing_signal_state_is_refused_and_preserved', 3)],
    '6195': [('test_no_filesystem_work_until_outcome_and_lock_release', 1),
             ('test_buffer_bound_drops_diagnostics_without_writing', 1),
             ('test_slow_persistence_does_not_hold_the_completed_operation', 1),
             ('test_queue_capacity_drops_only_excess_diagnostics', 1),
             ('test_shared_engine_stalled_admission_publishes_and_stops_timing', 1)],
    '6196': [('test_operator_interrupt_is_never_swallowed', 4),
             ('test_diagnostic_disk_failure_does_not_replace_verification_error', 1)],
    '6197': [('test_admission_time_is_excluded_from_child_deadline', 3)],
    '6198': [('test_dispatch_backstop_refuses_without_any_alarm_delivery', 2),
             ('test_existing_signal_state_is_refused_and_preserved', 3),
             ('test_stalled_fifo_open_is_interrupted_and_alarm_is_restored', 2),
             ('test_shared_engine_stalled_admission_publishes_and_stops_timing', 1)],
    'H1-420-F1': [('test_missing_external_gate_refuses_before_reservation_or_probe', 3)],
}
REASONS = {
    '6193': 'One-shot expiry leaves nested cleanup uninterrupted.',
    '6194': 'Timer cancellation, quiet tick, pending-signal drain and mask restoration retain independent cleanup attempts.',
    '6195': 'Bounded rows persist after outcome and lock release; the asynchronous writer cannot delay the completed operation.',
    '6196': 'InterruptedError propagates through explicit diagnostic operations; ordinary persistence errors drop diagnostics.',
    '6197': 'The deadline-origin test distinguishes dispatch from entry across registered child durations.',
    '6198': 'Regression coverage reaches the synchronous dispatch backstop, signal mask and shared-engine publication/sealing paths.',
    'H1-420-F1': 'The missing-gate test permits only the registration-digest sidecar append while retaining every other byte and forbidden effect assertion.',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path)
    assert path.is_file(), str(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def read_json(path):
    assert path.is_file(), str(path)
    return json.loads(path.read_bytes())


def counts(cases):
    result = {'total': len(cases)}
    for key in ('passed', 'failed', 'error', 'skipped'):
        result[key] = sum(case['status'] == key for case in cases)
    return result


def junit(path):
    result = []
    for case in ET.parse(path).iter('testcase'):
        children = {tag: case.find(tag) for tag in ('failure', 'error', 'skipped')}
        tag = next((key for key, value in children.items() if value is not None), None)
        row = {'name': case.get('name', ''), 'classname': case.get('classname', ''),
               'seconds': case.get('time'),
               'status': {'failure': 'failed', 'error': 'error', 'skipped': 'skipped'}.get(tag, 'passed')}
        if tag:
            row['detail'] = ET.tostring(children[tag], encoding='unicode')
            if tag in ('failure', 'error'):
                row['message'] = (children[tag].get('message')
                                  or ''.join(children[tag].itertext()).strip())
        result.append(row)
    return result


def load_cohort(directory, preload=False):
    name = 'preload' if preload else directory.name
    paths = ({'junit': SCRATCH / 'preload.xml', 'log': SCRATCH / 'preload.log',
              'command': SCRATCH / 'preload-command.json', 'outcome': SCRATCH / 'preload-outcome.json'}
             if preload else {'junit': directory / 'pytest.xml', 'log': directory / 'pytest.log',
                              'command': directory / 'command.json', 'outcome': directory / 'outcome.json'})
    row = {'name': name, 'evidence': {}, 'cases': [], 'missing_artifacts': []}
    for kind, path in paths.items():
        if path.is_file():
            row['evidence'][kind] = pin(path)
            if kind in ('command', 'outcome'):
                row[kind] = read_json(path)
            elif kind == 'junit':
                row['cases'] = junit(path)
        else:
            row['missing_artifacts'].append(path.name)
    row['counts'] = counts(row['cases'])
    row['complete'] = bool(row['cases']) and 'outcome' in row and 'junit' in row['evidence']
    row['passed'] = row['complete'] and row['outcome'].get('returncode') == 0 and all(
        case['status'] == 'passed' for case in row['cases'])
    row['evidence_mtime_ns'] = max((Path(p['path']).stat().st_mtime_ns for p in row['evidence'].values()), default=0)
    step = directory / 'ci-step.json'
    if not preload and step.is_file():
        row['ci_step'] = read_json(step)
        row['evidence']['ci_step'] = pin(step)
    return row


def test_proof(cohorts, name, expected):
    # Preserve all executions in the cohort ledger; use the newest saved result
    # for each parameter identity when a focused case was deliberately rerun.
    selected = {}
    for cohort in sorted(cohorts, key=lambda row: row['evidence_mtime_ns']):
        for case in cohort['cases']:
            if case['name'].split('[', 1)[0] == name:
                selected[(case['classname'], case['name'])] = {
                    **case, 'cohort': cohort['name'], 'cohort_complete': cohort['complete'],
                    'junit': cohort['evidence']['junit']}
    found = list(selected.values())
    passed = len(found) == expected and all(
        case['status'] == 'passed' and case['cohort_complete'] for case in found)
    return {'test': name, 'required_cases': expected, 'counts': counts(found),
            'passed': passed, 'cases': found}


def status_for(proofs):
    if proofs and all(proof['passed'] for proof in proofs):
        return 'fixed'
    if any(proof.get('counts', {}).get('passed', 0) or proof['passed'] for proof in proofs):
        return 'partly fixed'
    return 'not fixed'


def timing_evidence(directory):
    result = []
    if not directory.is_dir():
        return result
    for path in sorted(directory.rglob('host-pre-dispatch-*.jsonl')):
        if path.is_symlink():
            continue
        item = {'evidence': pin(path), 'capture_to_reservation': []}
        try:
            rows = [json.loads(line) for line in path.read_bytes().splitlines()]
            digest = path.name.removeprefix('host-pre-dispatch-').removesuffix('.jsonl')
            assert rows and all(isinstance(row, dict) and row.get('registration_sha256') == digest for row in rows)
            captures = [row for row in rows if row.get('boundary') in ('capture_observed', 'synthetic_capture_minted')]
            reservations = [row for row in rows if row.get('boundary') == 'attempt_reserved']
            for end in reservations:
                candidates = [row for row in captures if isinstance(row.get('elapsed_ns'), int)
                              and isinstance(end.get('elapsed_ns'), int) and row['elapsed_ns'] <= end['elapsed_ns']]
                if candidates:
                    start = max(candidates, key=lambda row: row['elapsed_ns'])
                    duration = end['elapsed_ns'] - start['elapsed_ns']
                    item['capture_to_reservation'].append({'elapsed_ns': duration,
                        'seconds': duration / 1_000_000_000, 'capture': start, 'reservation': end})
            item.update(rows=len(rows), capture_rows=len(captures), reservation_rows=len(reservations))
            if not item['capture_to_reservation']:
                item['unavailable_reason'] = 'No matching retained capture/reservation pair; duration is unknown.'
        except (ValueError, AssertionError, TypeError) as exc:
            item['parse_error'] = type(exc).__name__ + ': ' + str(exc)
        result.append(item)
    return result


def public_proof(cohorts, name, node):
    cohort = next((row for row in cohorts if row['name'] == name), None)
    item = {'name': name, 'node': node, 'passed': False, 'status': 'not run', 'counts': counts([]),
            'results': [], 'timing': []}
    if cohort is None:
        return item
    item['counts'] = cohort['counts']
    item['pytest_failures'] = [case for case in cohort['cases'] if case['status'] in ('failed', 'error')]
    messages = [' '.join(case.get('message', '').split()) for case in item['pytest_failures']]
    item['failure_summary'] = '; '.join(message for message in messages if message)
    if item['pytest_failures'] and not item['failure_summary']:
        item['failure_summary'] = 'JUnit records a failure without an exception message; inspect retained detail.'
    if len(item['failure_summary']) > 600:
        item['failure_summary'] = item['failure_summary'][:597] + '...'
    command = cohort.get('command', {}).get('command', [])
    selectors = [arg for arg in command if arg.startswith('tests/')]
    isolated = selectors == [node] and not any(arg == '-n' or arg.startswith('-n=') or arg.startswith('--numprocesses') for arg in command)
    item['isolated_command'] = isolated
    case_root = SCRATCH / name / 'cases'
    if case_root.is_dir():
        for path in sorted(case_root.rglob('actual-result.json')):
            item['results'].append({'evidence': pin(path), 'result': read_json(path)})
        item['timing'] = timing_evidence(case_root)
    result = item['results'][0]['result'] if len(item['results']) == 1 else None
    completed = bool(result and result.get('state') == 'completed_pending_independent_review')
    item['status'] = ('complete' if completed else str(result.get('first_stop') or result.get('state'))
                      if result else 'pytest failed before saved public result' if item['pytest_failures']
                      else 'no saved public result')
    item['passed'] = isolated and cohort['passed'] and cohort['counts']['total'] == 1 and completed
    return item


def lane_proof(cohorts, name):
    cohort = next((row for row in cohorts if row['name'] == name), None)
    item = {'lane': name, 'passed': False, 'counts': counts([]), 'status': 'not run'}
    if cohort is None:
        return item
    item.update(counts=cohort['counts'], status='complete' if cohort['complete'] else 'incomplete')
    step = cohort.get('ci_step')
    command = cohort.get('command', {})
    if step:
        expected = [arg for arg in shlex.split(step['run'])[5:] if not arg.startswith('--junitxml=')]
        actual = [arg for arg in command.get('command', [])[3:]
                  if not arg.startswith(('--junitxml=', '--basetemp='))]
        item['exact_ci_arguments'] = actual == expected
        item['exact_ci_environment'] = all(command.get('environment', {}).get(k) == str(v)
                                           for k, v in step.get('env', {}).items())
        item['passed'] = (cohort['complete'] and cohort['outcome'].get('returncode') == 0
            and cohort['counts']['passed'] > 0 and cohort['counts']['failed'] == 0
            and cohort['counts']['error'] == 0 and item['exact_ci_arguments']
            and item['exact_ci_environment'])
    else:
        item['status'] = 'missing saved CI step'
    return item


def file_proof(cohorts, path):
    relative = str(path.relative_to(ROOT))
    classname = relative.removesuffix('.py').replace('/', '.')
    candidates = []
    for cohort in cohorts:
        argv = cohort.get('command', {}).get('command', [])
        full_selected = any(arg == relative or (not arg.startswith('-') and '::' not in arg
                            and (ROOT / arg).is_dir() and path.is_relative_to(ROOT / arg)) for arg in argv[3:])
        if full_selected:
            cases = [case for case in cohort['cases'] if case['classname'] == classname
                     or case['classname'].startswith(classname + '.')]
            candidates.append({'cohort': cohort['name'], 'counts': counts(cases),
                'passed': cohort['complete'] and bool(cases) and all(case['status'] == 'passed' for case in cases),
                'evidence_mtime_ns': cohort['evidence_mtime_ns']})
    if not candidates:
        return {'path': str(path), 'passed': False, 'status': 'no complete-file invocation recorded'}
    chosen = max(candidates, key=lambda row: row['evidence_mtime_ns'])
    return {'path': str(path), **chosen}


def main():
    assert REPORT.is_dir() and SCRATCH.is_dir()
    source_path = SCRATCH / 'source-audit-final.json'
    source = read_json(source_path)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == source['head'], 'Final source audit must name current HEAD.'
    for relative, digest in source.get('changed_file_hashes', {}).items():
        assert sha((ROOT / relative).read_bytes()) == digest, 'Source changed after audit: ' + relative
    for entry in source['protected']:
        assert entry['unchanged'] and sha((ROOT / entry['path']).read_bytes()) == entry['sha256']
    cohorts = [load_cohort(path) for path in sorted(SCRATCH.iterdir()) if path.is_dir()
               and any((path / name).is_file() for name in ('pytest.xml', 'command.json', 'outcome.json'))]
    if any((SCRATCH / name).is_file() for name in ('preload.xml', 'preload.log')):
        cohorts.append(load_cohort(SCRATCH, preload=True))
    public = [public_proof(cohorts, name, node) for name, node in PUBLIC.items()]
    issues = []
    preload = test_proof(cohorts, 'test_worker_host_and_timing_utilities_never_load_a_module', 2)
    proofs = [preload, *public]
    issues.append({'issue': '6200', 'status': status_for(proofs), 'proofs': proofs,
        'reason': 'Callback host/timing utilities preload on the main thread; completion requires all public cases to pass in separate serial invocations.'})
    compatibility_path = SCRATCH / 'checkpoint-compatibility.json'
    compatibility = read_json(compatibility_path)
    compatibility_ok = bool(compatibility.get('sources')) and all(item.get('byte_identical') is True
                         for item in compatibility['sources'])
    for issue, lane in (('6201', 'native'), ('6202', 'audit')):
        proof = lane_proof(cohorts, lane)
        proofs = [proof]
        if issue == '6202':
            proofs.append({'passed': compatibility_ok, 'evidence': pin(compatibility_path),
                           'scope': compatibility.get('scope')})
        issues.append({'issue': issue, 'status': status_for(proofs), 'proofs': proofs,
            'reason': ('Deadline and reason-source failures were stale fixture clock injection; continuous dispatch clock binding preserves timing/interrupt assertions.'
                       if issue == '6201' else 'The compatibility admission has exact-definition byte proof; the audit deadline fixture uses the continuous dispatch clock.')})
    for issue, requirements in PROOFS.items():
        proofs = [test_proof(cohorts, name, expected) for name, expected in requirements]
        issues.append({'issue': issue, 'status': status_for(proofs), 'proofs': proofs, 'reason': REASONS[issue]})
    doc = ROOT / 'docs/native-run-limits.md'
    doc_pin = pin(doc)
    doc_audit = SCRATCH / 'run-limit-audit/run-limit-audit.json'
    doc_hash = SCRATCH / 'run-limit-doc.sha256'
    recorded_digest = doc_hash.read_text().split()[0] if doc_hash.is_file() else None
    doc_ok = doc_audit.is_file() and recorded_digest == doc_pin['sha256']
    issues.append({'issue': '6199', 'status': 'fixed' if doc_ok else 'not fixed',
        'reason': 'Run-limit documentation regenerated from the integrated worktree as a single source root.',
        'proofs': [{'passed': doc_ok, 'document': doc_pin,
                    'audit': pin(doc_audit) if doc_audit.is_file() else None,
                    'saved_digest': pin(doc_hash) if doc_hash.is_file() else None}]})
    required = [ROOT / 'tests' / name for name in (
        'test_native_shared_permission_protocol.py', 'test_native_launch_sequence.py',
        'test_native_u1_scanner_contracts.py', 'test_native_u3l_scanner.py',
        'test_neutral_generation_schema.py', 'test_profiles.py',
        'test_external_dataset_onboarding.py', 'test_native_shared_execution_failure.py',
        'test_native_admission_timer.py', 'test_native_pre_dispatch_timing.py',
        'test_native_attempt_deadline.py', 'test_native_admission_failure.py',
        'test_native_attempt_timing.py', 'test_native_host_power.py',
        'test_native_shared_callback_preloading.py',
        'test_native_subscription_capture.py', 'test_native_shared_registration.py',
        'test_native_shared_capture_split.py', 'test_native_shared_capture_integration.py',
        'test_native_failure_publication.py', 'test_native_execution_engine.py',
        'test_native_shared_controller.py')]
    required += sorted((ROOT / 'tests').glob('test_generation_specificity_*.py'))
    assert all(path.is_file() for path in required)
    coverage = [file_proof(cohorts, path) for path in required]
    commits_path = SCRATCH / 'commit-map-source.txt'
    commits = []
    for line in commits_path.read_text().splitlines():
        commit, subject = line.split(' ', 1)
        mapped = next((values for prefix, values in COMMIT_ISSUES.items() if commit.startswith(prefix)), [])
        commits.append({'commit': commit, 'subject': subject, 'issues': mapped,
                        'scope': 'assigned repair' if mapped else 'integration, provenance or test-runner support'})
    review_path = SCRATCH / 'review.json'
    review = read_json(review_path)
    pin_changes = [entry for manifest in source['manifests'] for entry in manifest['modules'] if not entry['matches']]
    incomplete = [row['name'] for row in cohorts if not row['complete']]
    unavailable = [name for name in (*PUBLIC, 'native', 'audit', 'budget', 'focused', 'guards', 'failure', 'dependents')
                   if not any(row['name'] == name for row in cohorts)]
    record = {'answer': issues, 'head': head, 'source_audit': source, 'source_audit_evidence': pin(source_path),
        'cohorts': cohorts, 'public_paths': public, 'required_file_coverage': coverage,
        'incomplete_cohorts': incomplete, 'required_cohorts_not_run': unavailable,
        'commits': commits, 'commit_map_evidence': pin(commits_path),
        'review': review, 'review_evidence': pin(review_path),
        'compatibility': compatibility, 'compatibility_evidence': pin(compatibility_path),
        'controller_pin_mismatches': pin_changes, 'report_producer': pin(Path(__file__).resolve()),
        'environment': {'report_interpreter': sys.version, 'platform': sys.platform,
            'scope': 'Local macOS Python 3.13 verification; CI Python 3.12 and its full suite are not certified by this report.'},
        'limitations': ['No provider, model or native binary invocation is part of this software-test report.',
            'No push, PR, GitHub write, protected-file change or applied controller pin rotation is reported.',
            'Capture-to-reservation durations are retained diagnostic evidence; missing pairs remain unknown.',
            'Saved commands identify their starting HEAD; that field alone does not identify uncommitted test bytes.',
            'The lead owns full CI verification and publishing.']}
    # Serialize exact external strings with escaped codepoints rather than literal at-signs.
    json_text = (json.dumps(record, indent=2) + '\n').replace(chr(64), '\\u0040')
    json_path = REPORT / (STEM + '.json')
    json_path.write_text(json_text)
    json_pin = pin(json_path)
    lines = ['; '.join(row['issue'] + ': ' + row['status'] for row in issues) + '.', '',
        'Each status below comes from the saved verification evidence. Partial or missing verification remains explicit.', '']
    for row in issues:
        lines.append('- ' + row['issue'] + ' — ' + row['status'] + '. ' + row['reason'])
        for proof in row['proofs']:
            label = proof.get('test') or proof.get('lane') or proof.get('node') or 'saved source evidence'
            result = proof.get('counts')
            detail = ', '.join(str(result[key]) + ' ' + key for key in ('passed', 'failed', 'error', 'skipped')) if result else ('verified' if proof['passed'] else 'not verified')
            lines.append('  - ' + label + ': ' + detail + '.')
    lines += ['', 'Public-path outcomes and capture-to-reservation evidence:', '']
    for item in public:
        spans = [span['seconds'] for entry in item['timing'] for span in entry['capture_to_reservation']]
        duration = ', '.join(format(value, '.9f') + ' s' for value in spans) if spans else 'unknown; no retained capture/reservation pair'
        lines.append('- ' + item['name'] + ': ' + item['status'] + '; capture to reservation: ' + duration + '.')
        if item.get('failure_summary'):
            lines.append('  - Pytest failure: ' + item['failure_summary'])
        for result in item['results']:
            lines.append('  - Result: `' + result['evidence']['path'] + '`.')
        for timing in item['timing']:
            lines.append('  - Sidecar: `' + timing['evidence']['path'] + '`.')
    lines += ['', 'Saved verification cohorts:', '']
    for cohort in cohorts:
        result = cohort['counts']
        lines.append('- ' + cohort['name'] + ': ' + ', '.join(str(result[key]) + ' ' + key for key in ('passed', 'failed', 'error', 'skipped'))
                     + '; ' + ('completed' if cohort['complete'] else 'incomplete') + '.')
        if 'junit' in cohort['evidence']:
            lines.append('  - JUnit: `' + cohort['evidence']['junit']['path'] + '`.')
        if 'command' in cohort['evidence']:
            lines.append('  - Exact command/environment: `' + cohort['evidence']['command']['path'] + '`.')
            environment = cohort.get('command', {}).get('environment', {})
            settings = {key: environment.get(key, 'unset') for key in
                        ('PYTHONDONTWRITEBYTECODE', 'PYTHONPYCACHEPREFIX')}
            lines.append('  - Recorded bytecode settings: ' + '; '.join(
                key + '=' + str(value) for key, value in settings.items()) + '. No causal inference is made from these settings.')
        if 'log' in cohort['evidence']:
            lines.append('  - Log: `' + cohort['evidence']['log']['path'] + '`.')
        if cohort['missing_artifacts']:
            lines.append('  - Missing saved artifacts: ' + ', '.join(cohort['missing_artifacts']) + '.')
    lines += ['', 'Required complete-file coverage:', '']
    for item in coverage:
        lines.append('- `' + item['path'] + '`: ' + ('passed' if item['passed'] else 'not fully verified')
                     + ('; ' + item['cohort'] if item.get('cohort') else '') + '.')
    lines += ['', 'Missing required cohorts: ' + (', '.join(unavailable) or 'none') + '.',
        'Incomplete recorded cohorts: ' + (', '.join(incomplete) or 'none') + '.', '',
        'Prior commit mapping is retained from `' + str(commits_path) + '`:', '']
    for item in commits:
        lines.append('- `' + item['commit'] + '`: ' + (', '.join(item['issues']) if item['issues'] else item['scope']) + '; ' + item['subject'] + '.')
    lines += ['', 'Source and review:', '',
        '- Final source audit: `' + str(source_path) + '`.',
        '- Exact-definition compatibility proof: `' + str(compatibility_path) + '`.',
        '- Internal read-only review: `' + str(review_path) + '`; no findings; no tests were run by that review.',
        '- ' + ('Controller pin mismatches require a review-only proposal; no rotation applied.' if pin_changes else 'Controller manifest entries match the final audit; no pin rotation applied.'),
        '- Local macOS Python 3.13 results do not establish CI Python 3.12 results or a full-suite pass.',
        '- Saved command HEADs and complete case details are preserved in the JSON twin; uncommitted test bytes are not independently identified by HEAD alone.',
        '- Nothing published; production launch remains outside this assignment.', '',
        'JSON twin: `' + str(json_path) + '`; SHA-256 `' + json_pin['sha256'] + '`.',
        'Producer: `' + str(Path(__file__).resolve()) + '`.',
        'Reproduce: `' + str(ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python') + ' ' + str(Path(__file__).resolve()) + '`.']
    markdown = ('\n'.join(lines) + '\n').replace(chr(64), '[at]')
    md_path = REPORT / (STEM + '.md')
    md_path.write_text(markdown)
    assert md_path.stat().st_size and json_path.stat().st_size
    assert chr(64) not in markdown and chr(64) not in json_text
    print(json.dumps({'markdown': pin(md_path), 'json': pin(json_path)}, indent=2))


if __name__ == '__main__':
    main()
