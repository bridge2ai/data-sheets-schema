#!/usr/bin/env python3
"""Report H1 scanner repair and integration from retained evidence, 2026-11-12.

Inputs: local Git objects, H1 composition/test/comparison artifacts, G07 exact
negative identities and the authority audit. Outputs: H1 JSON/Markdown handoff.
No project imports, tests, source edits, network or Git writes. Issue G07-F1.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

DEV = Path(__file__).resolve().parents[2]
EXEC = DEV.parent
WT = EXEC / 'codex-native-main-integration-20261112'
SCRATCH = EXEC / 'scratch-native-h1-scanner-20261112'
OUT = DEV / 'notes/development_efficiency_20261111/handoffs'
MAIN = '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1'
START = '5d63d0a77dc43c064cfc2b376355f98009dd5b6e'
PROTECTED = ('src/data_sheets_schema/shared_generation.py',
             'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml',
             'tests/utils/run_spec_boundary_contracts.json')
JSON_PATH = OUT / 'codex-h1-scanner-pin-20261112.json'
MD_PATH = JSON_PATH.with_suffix('.md')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['/usr/bin/git', *args], cwd=WT, env=git_environment())


def git_environment():
    return dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0',
                GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null')


def reference(path):
    path = Path(path)
    if not path.is_file():
        return {'path': str(path), 'state': 'pending'}
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw), 'state': 'present'}


def read_json(path):
    if not Path(path).is_file():
        return None
    return json.loads(Path(path).read_bytes())


def captured_json(path):
    return dict(reference(path), data=read_json(path))


def table(rows, columns):
    def cell(value):
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        return str(value).replace('|', '\\|').replace('\n', '<br>')
    return '\n'.join(['| ' + ' | '.join(label for _, label in columns) + ' |',
        '| ' + ' | '.join('---' for _ in columns) + ' |'] +
        ['| ' + ' | '.join(cell(row.get(key, '')) for key, _ in columns) + ' |' for row in rows])


def canonical_node(case, root):
    """Resolve JUnit classname through an actual source file, not dot guessing."""
    classname = case.get('classname', '')
    direct = case.get('file', '')
    candidates = []
    if direct:
        path = Path(direct)
        if path.is_absolute():
            try:
                direct = str(path.relative_to(root))
            except ValueError:
                direct = ''
        if direct.endswith('.py') and (root / direct).is_file():
            dotted = direct[:-3].replace('/', '.')
            suffix = classname[len(dotted):].strip('.') if classname.startswith(dotted) else ''
            candidates.append((direct, suffix))
    parts = classname.split('.')
    for length in range(len(parts), 0, -1):
        relative = '/'.join(parts[:length]) + '.py'
        for candidate in (relative, 'tests/' + relative):
            if (root / candidate).is_file():
                candidates.append((candidate, '.'.join(parts[length:])))
        if candidates:
            break
    candidates = sorted(set(candidates))
    if len(candidates) != 1:
        return None
    path, suffix = candidates[0]
    return '::'.join([path, *([part for part in suffix.split('.') if part]), case.get('name', '')])


def cohorts():
    result = []
    for path in sorted((SCRATCH / 'tests').glob('*/plan.json')):
        directory = path.parent
        plan = read_json(path)
        outcome = read_json(directory / 'outcome.json')
        xml_path = directory / 'pytest.xml'
        root = Path(plan.get('source_root', WT))
        cases = []
        parsing_error = None
        if xml_path.is_file():
            try:
                tree = ET.parse(xml_path).getroot()
                for case in tree.iter('testcase'):
                    children = [child for child in case if child.tag in ('failure', 'error', 'skipped')]
                    finding = next((child for child in children if child.tag in ('failure', 'error')), None)
                    if finding is None:
                        finding = next(iter(children), None)
                    state = finding.tag if finding is not None else 'passed'
                    trace = finding.text or '' if finding is not None else ''
                    cases.append({'nodeid': canonical_node(case, root),
                        'junit_classname': case.get('classname', ''), 'name': case.get('name', ''),
                        'outcome': state, 'message': finding.get('message', '') if finding is not None else '',
                        'trace_sha256': sha(trace.encode()), 'seconds': case.get('time')})
            except ET.ParseError as exc:
                parsing_error = str(exc)
        result.append({'id': directory.name, 'plan': plan, 'outcome': outcome,
            'state': 'completed' if outcome is not None and parsing_error is None else 'pending',
            'source_commit': plan.get('source_commit'), 'command': plan.get('command'),
            'counts': dict(Counter(case['outcome'] for case in cases)), 'cases': cases,
            'xml_parse_error': parsing_error,
            'evidence': [reference(directory / name) for name in
                ('plan.json', 'outcome.json', 'pytest.xml', 'pytest.log')],
            'ended_timestamp': (directory / 'outcome.json').stat().st_mtime if outcome else None})
    return result


def prior_reconciliation(current):
    path = OUT / 'codex-g07-scanner-cohort-classification-20261112.json'
    retained = read_json(path)
    if retained is None:
        return {'state': 'prior_evidence_missing', 'evidence': reference(path)}
    old = retained['negatives']
    assert len(old) == 96 and len({row['nodeid'] for row in old}) == 96
    witnesses = {}
    for cohort in sorted(current, key=lambda row: row['ended_timestamp'] or 0):
        if cohort['state'] != 'completed':
            continue
        for case in cohort['cases']:
            if case['nodeid']:
                witnesses.setdefault(case['nodeid'], []).append(dict(case,
                    cohort=cohort['id'], source_commit=cohort['source_commit'],
                    evidence=cohort['evidence'], execution=cohort['outcome']))
    rows = []
    for before in old:
        observed = witnesses.get(before['nodeid'], [])
        after = observed[-1] if observed else None
        state = 'unobserved' if after is None else after['outcome']
        if after and after['outcome'] == 'passed':
            execution = after['execution'] or {}
            verified = execution.get('cleanup_verified') is True and (
                (execution.get('worker') or {}).get('source_origin_checks_passed') is True
                or execution.get('source_origin_checks_passed') is True)
            state = 'cleared' if verified else 'passed_without_verified_execution'
        rows.append({'nodeid': before['nodeid'], 'before': before,
                     'current_state': state, 'latest_witness': after, 'all_witnesses': observed})
    return {'state': 'reconciled_by_exact_node_identity', 'evidence': reference(path),
            'prior_count': len(old), 'counts': dict(Counter(row['current_state'] for row in rows)),
            'rows': rows,
            'scope': 'Passing tests establish only their own assertions; missing, skipped or unfinished cases never count as cleared.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', default='scanner commit; validation and integration in progress')
    parser.add_argument('--comparison', type=Path)
    parser.add_argument('--helper-controls', type=Path,
                        help='Saved comparison-helper controls; absent evidence leaves review findings pending')
    args = parser.parse_args()
    head = git('rev-parse', 'HEAD').decode().strip()
    history = []
    for line in git('log', '--reverse', '--format=%H%x09%s', START + '..HEAD').decode().splitlines():
        commit, subject = line.split('\t', 1)
        history.append({'commit': commit, 'subject': subject})
    protected = []
    for path in PROTECTED:
        main_raw = git('show', MAIN + ':' + path)
        branch_raw = git('show', head + ':' + path)
        worktree_raw = (WT / path).read_bytes()
        protected.append({'path': path, 'main_sha256': sha(main_raw),
            'branch_sha256': sha(branch_raw), 'worktree_sha256': sha(worktree_raw),
            'equal_main': main_raw == branch_raw == worktree_raw})
    composition_paths = sorted(SCRATCH.glob('*/composition.json'))
    compositions = [captured_json(path) for path in composition_paths]
    test_rows = cohorts()
    reconciled = prior_reconciliation(test_rows)
    audit_path = OUT / 'codex-h1-authority-audit-20261112.json'
    comparison = comparison_evidence(args.comparison) if args.comparison else {
        'state': 'pending', 'data': None,
        'scope': 'No complete current D128-form arrays have been supplied. Missing counts are not zero.'}
    scan_complete = (comparison.get('data') or {}).get('status') == 'complete_diagnostic_not_owner_approval'
    counts = reconciled.get('counts', {})
    answer = ('The scanner comparison is complete as diagnostic evidence; owner disposition remains pending. '
              if scan_complete else
              'The scanner authority repair is committed locally; a complete current scanner comparison is still pending. ')
    answer += ('Of the 96 retained scanner negatives, ' + str(counts.get('cleared', 0)) +
               ' have verified passing witnesses and ' + str(counts.get('unobserved', 0)) +
               ' remain unobserved. Detailed outcomes and integration status follow.')
    finished = []
    for donor in ('ddcadcdc2', 'ab07c81fe'):
        full = git('rev-parse', donor).decode().strip()
        subject = git('show', '-s', '--format=%s', donor).decode().strip()
        matches = [row for row in history if row['subject'] == subject]
        finished.append({'donor': full, 'subject': subject, 'subject_matches': matches,
            'state': 'commit_subject_present_review_diff_and_tests' if matches else 'not_yet_present'})
    restoration = [captured_json(path) for path in sorted(SCRATCH.glob('*/config-restored.json'))]
    data = {'kind': 'native_h1_scanner_pin_and_integration_handoff',
        'generated_utc': datetime.now(timezone.utc).isoformat(), 'phase': args.phase,
        'answer': answer,
        'current_branch': git('branch', '--show-current').decode().strip(), 'current_branch_head': head,
        'fixed_main': MAIN, 'assignment_start': START, 'local_commits': history,
        'tracked_status': git('status', '--porcelain', '--untracked-files=no').decode(),
        'protected_files': protected, 'all_protected_equal_main': all(row['equal_main'] for row in protected),
        'authority_audit': dict(reference(audit_path), summary={key: value for key, value in (read_json(audit_path) or {}).items() if key not in ('commands', 'all_authority_top_level_comparisons', 'pin_history_stdout')}),
        'semantic_review': {
            'decision': 'Update the integrated authority digest only; retain exact render AST templates and the legacy digest.',
            'claim': 'The scanner proves fixed rendering source structure and runtime/instruction transport; it does not establish preparation or launch acceptance.',
            'changes': [
                '5503684ee extends launch-scoped schema import metadata reuse.',
                'e282f0596 clears snapshot LRUs on donor state or phase changes.',
                'd6f51f8ed replaces consumer-registry membership with exact snapshot name/path/digest attestation and fresh byte checks.',
                '033cd731f retains immutable import facts while applying current source checks, lint, origins and graph traversal.'],
            'qualification': 'Rendering meaning is preserved. Full authority behavior changed, including legitimate nonconsumer snapshot admission; it is not merely formatting.',
            'source_evidence': ['scan.py:13023-13031', 'scan.py:13408-13416',
                'native_execution_authority_v2.py:85-322', 'native_execution_authority_v2.py:607-830'],
            'validation_modules': ['tests/test_native_h1_scanner_authority.py',
                'tests/test_native_u3l_scanner.py', 'tests/test_native_u1_scanner_contracts.py',
                'tests/test_native_import_facts.py', 'tests/test_native_launch_schema_metadata.py']},
        'compositions': compositions, 'scanner_comparison': comparison, 'tests': test_rows,
        'prior_96_negatives': reconciled, 'integration': finished,
        'private_configuration_restoration': restoration,
        'composition_source_witnesses': source_witnesses(compositions),
        'findings': [
            {'id': 'H1-F1', 'state': 'runner_provenance_limitation', 'detail': 'The runner records HEAD and four protected hashes but does not itself attest the complete tracked working tree. Composition creation and final tracked-clean witnesses mitigate this gap; they do not establish a full before-run content manifest.'},
            {'id': 'H1-F2', 'state': 'portability_validation_pending', 'detail': 'The test portability temp_base selection may reject TMPDIR under d4d-executions and choose system tmp outside the permitted scratch location. This is a risk to verify after the test-only cherry-picks, not an observed test failure yet.'},
            {'id': 'H1-F3', 'state': 'fix_controls_pending', 'detail': 'Independent pre-execution review found a false-completion risk when worker returncode is null but the OS exit is 1. The comparison helper must require matching, typed worker and process exit codes before treating arrays as complete. No run was claimed complete using this defect.'},
            {'id': 'H1-F4', 'state': 'fix_controls_pending', 'detail': 'Independent pre-execution review found that cleanup by numeric process-group ID risks signalling a reused group. The comparison helper must bind owned processes to their recorded identities and refuse signalling replacements. No affected helper run was performed.'}],
        'comparison_helper_controls': captured_json(args.helper_controls) if args.helper_controls else
            {'state': 'pending', 'data': None},
        'findings_publication': 'These are local review findings for lead publication. No GitHub issues, comments or reviews were created during this offline assignment.',
        'owner_pending': [
            'The API packet postimage 830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881 is not approved.',
            'D136 settles freshness age 1200 seconds. Margin remains 90 seconds in code; N1 draft v10 proposes 300 seconds, awaiting the owner.',
            'The current complete D128-form comparison needs an explicit disposition; historical approval applies only to its frozen source pair.',
            'No launch, native canary, publication or scientific acceptance is claimed.'],
        'helper': reference(Path(__file__))}
    for finding in data['findings']:
        finding['record_location'] = 'local_handoff_for_lead_publication'
    apply_control_dispositions(data)
    raw = json.dumps(data, indent=2, ensure_ascii=False).replace(chr(64), '[at]') + '\n'
    data = json.loads(raw)
    lines = ['# Native scanner authority repair and integration — 2026-11-12', '', data['answer'], '',
        'Phase: ' + args.phase + '. Branch head: `' + head + '`.', '',
        '**Owner-facing interpretation**', '',
        'The scanner checks how local source code selects and constructs model-facing instructions. '
        'The repair recognizes reviewed authority bytes while keeping exact rendering templates and refusal checks. '
        'It does not authorize native execution or certify successful generation.', '',
        'The historical D128 approval covers its original source pair. The current itemized comparison below '
        'identifies what remains covered and what is new. Approving that comparison would dispose of this new '
        'scanner evidence; it would not approve the pending protected API packet, the margin change or a launch.', '',
        '**Pending decisions**', '', *['- ' + text for text in data['owner_pending']], '',
        '**Local commits**', '', table(data['local_commits'], [('commit', 'Full SHA'), ('subject', 'Change')]), '',
        '**Protected branch files**', '', table(data['protected_files'],
            [('path', 'Path'), ('branch_sha256', 'Branch SHA-256'), ('equal_main', 'Working and committed bytes equal main')]), '',
        '**Authority review**', '', data['semantic_review']['qualification'], '',
        '- ' + '\n- '.join(data['semantic_review']['changes']), '',
        authority_text(data['authority_audit']), '',
        '**Composition attempts**', '', table([{'path': row['path'], 'sha256': row.get('sha256'),
             'status': (row.get('data') or {}).get('status', 'pending'),
             'source': (row.get('data') or {}).get('source_commit'),
             'error': (row.get('data') or {}).get('error')} for row in compositions],
             [('path', 'Manifest'), ('status', 'Status'), ('source', 'Source'), ('error', 'Error'), ('sha256', 'SHA-256')]), '',
        '**Test evidence**', '', table([{'cohort': row['id'], 'state': row['state'],
             'source': row['source_commit'], 'counts': row['counts'],
             'exit': (row['outcome'] or {}).get('returncode')} for row in test_rows],
             [('cohort', 'Cohort'), ('state', 'State'), ('source', 'Exact source'), ('counts', 'JUnit cases'), ('exit', 'Exit')]), '',
        '**Exact prior-negative reconciliation**', '',
        table([{'state': key, 'count': value} for key, value in reconciled.get('counts', {}).items()],
              [('state', 'Current state'), ('count', 'Prior negative identities')]), '',
        'Every original negative identity and its current witnesses are retained in the JSON. '
        'Classnames are mapped through actual source files; absent or unfinished evidence cannot clear a case.', '',
        '**Scanner comparison**', '',
        comparison_text(data['scanner_comparison']), '',
        '**Findings and limits**', '', table(data['findings'],
             [('id', 'Finding'), ('state', 'Status'), ('detail', 'Evidence and limits')]), '',
        data['findings_publication'], '',
        'Comparison-helper control evidence: ' + str(data['comparison_helper_controls'].get('path', 'pending')) +
        '; SHA-256 ' + str(data['comparison_helper_controls'].get('sha256', 'pending')) + '.', '',
        '**Composition source witnesses**', '', table(data['composition_source_witnesses'],
             [('root', 'Source tree'), ('observed_head', 'Observed HEAD'),
              ('tracked_clean', 'Tracked clean'), ('scope', 'Scope')]), '',
        '**Integration**', '', table(data['integration'],
             [('donor', 'Donor commit'), ('subject_matches', 'Local matching commits'), ('state', 'Evidence state')]), '',
        'Private configuration restoration receipts: ' + str(len(restoration)) + '. Exact receipts and all '
        'commands, origins, cleanup evidence, output hashes and test identities are retained in the JSON. '
        'This report does not execute tests. At-sign characters are represented as [at]; referenced raw evidence retains its original bytes.', '']
    markdown = '\n'.join(lines).replace(chr(64), '[at]')
    JSON_PATH.write_text(raw)
    MD_PATH.write_text(markdown)
    assert JSON_PATH.stat().st_size and MD_PATH.stat().st_size
    print(json.dumps({'json': reference(JSON_PATH), 'markdown': reference(MD_PATH)}, indent=2))


def source_witnesses(compositions):
    rows = []
    for item in compositions:
        value = item.get('data') or {}
        commit = value.get('composition_commit')
        if not commit:
            continue
        root = Path(item['path']).parent / 'tree'
        if not (root / '.git').exists():
            rows.append({'root': str(root), 'state': 'source_unavailable'})
            continue
        command = ['/usr/bin/git', '-C', str(root)]
        environment = git_environment()
        head = subprocess.check_output(command + ['rev-parse', 'HEAD'], env=environment).decode().strip()
        status = subprocess.check_output(command + ['status', '--porcelain', '--untracked-files=no'], env=environment).decode()
        diff_run = subprocess.run(command + ['diff', '--exit-code', 'HEAD', '--'],
                                  env=environment, capture_output=True, check=False)
        diff = diff_run.stdout
        rows.append({'root': str(root), 'state': 'observed_after_evidence_read',
            'expected_commit': commit, 'observed_head': head, 'head_matches': head == commit,
            'tracked_status': status, 'tracked_clean': not status and diff_run.returncode == 0,
            'diff_sha256': sha(diff), 'diff_returncode': diff_run.returncode,
            'commands': [command + ['rev-parse', 'HEAD'], command + ['status', '--porcelain', '--untracked-files=no'],
                         command + ['diff', '--exit-code', 'HEAD', '--']],
            'environment_overrides': {key: environment[key] for key in
                ('GIT_NO_LAZY_FETCH', 'GIT_OPTIONAL_LOCKS', 'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_SYSTEM')},
            'scope': 'Post-run observation when cohorts are complete; otherwise an interim snapshot. Creation manifest provides the initial witness. This is not continuous attestation.'})
    return rows


def comparison_evidence(path):
    record = reference(path)
    value = read_json(path)
    if value is None:
        return dict(record, data=None)
    summary = {key: value[key] for key in ('status', 'source_branch_head', 'main',
        'd128_gate_passed', 'reference_arrays_match', 'tool_asset_delta',
        'protected_branch_equal_main', 'full_comparisons_present', 'failure', 'error') if key in value}
    summary['full_itemized_ledger'] = record
    summary['scan_sources'] = []
    for label in ('baseline', 'candidate'):
        scan = value.get(label) or {}
        summary['scan_sources'].append(dict(label=label, **{key: scan[key] for key in
            ('source_commit', 'tool_commit', 'tool_assets_sha256', 'derivation_complete', 'returncode') if key in scan}))
    summary['comparisons'] = []
    for index, comparison in enumerate(value.get('comparisons', [])):
        for name, ledger in comparison['arrays'].items():
            summary['comparisons'].append({'comparison': comparison['label'], 'array': name,
                'before': ledger['before_count'], 'after': ledger['after_count'],
                'exact': ledger['exact_match_count'], 'relocations': len(ledger['relocations']),
                'field_changes': len(ledger['changed_fields']), 'added': len(ledger['added']),
                'removed': len(ledger['removed']), 'position_changes': len(ledger['positional_differences']),
                'exact_arrays_equal': ledger['exact_arrays_equal'],
                'itemized_pointer': '/comparisons/' + str(index) + '/arrays/' + name})
    summary['d128_coverage'] = []
    for name, ledger in (value.get('d128_coverage') or {}).get('arrays', {}).items():
        for kind, rows in ledger['delta_occurrences'].items():
            same = sum(row['exact_finite_object_delta_match'] is True for row in rows)
            summary['d128_coverage'].append({'array': name, 'kind': kind, 'total': len(rows),
                'same_finite_object_delta': same, 'new_difference': len(rows) - same,
                'itemized_pointer': '/d128_coverage/arrays/' + name + '/delta_occurrences/' + kind})
    summary['coverage_scope'] = 'Matching finite object deltas do not approve changed tool, source or array ordering. Every full occurrence object remains in the hash-linked itemized ledger.'
    return dict(record, data=summary)


def authority_text(record):
    audit = record.get('summary') or {}
    if not audit:
        return 'Detailed authority audit is pending.'
    lines = ['The first source drift and subsequent unsynchronized commits are recorded below.', '',
        table(audit.get('lineage', []), [('commit', 'Authority-changing commit'),
             ('authority_sha256', 'Authority SHA-256'), ('scanner_authority_pin', 'Scanner pin'),
             ('scanner_touched', 'Scanner edited'), ('pin_matches_source', 'Pin matches source')]), '',
        'Requested historical checkpoints:', '',
        table(audit.get('checkpoints', []), [('commit', 'Full checkpoint SHA'),
             ('authority_sha256', 'Authority SHA-256'), ('scanner_authority_pin', 'Scanner pin'),
             ('pin_matches_source', 'Pin matches source')]), '']
    conclusion = audit.get('synchronization_conclusion') or {}
    lines.extend([conclusion.get('fact', ''), conclusion.get('inference', ''), '',
        table(audit.get('rendering_proof_helpers', []), [('name', 'Rendering authority helper'),
             ('exact_source_equal', 'Exact source unchanged'), ('normalized_ast_equal', 'AST unchanged')]), '',
        'Audit path: `' + record['path'] + '`; SHA-256 `' + record.get('sha256', '') + '`. Raw Git command outputs and all seven other source-pin checks are retained there.'])
    return '\n'.join(lines)


def comparison_text(record):
    value = record.get('data')
    if value is None:
        return 'The current scanner comparison is pending. Complete arrays and current counts are unavailable, not zero.'
    if value.get('status') != 'complete_diagnostic_not_owner_approval':
        return ('The current scanner comparison is incomplete; no clean or accepted result is claimed. '
                'Evidence: `' + record['path'] + '`; SHA-256 `' + record.get('sha256', '') + '`.\n\n' +
                str(value.get('failure', value.get('error', 'See the retained incomplete comparison record.'))))
    return '\n'.join(['Complete diagnostic arrays are available. They have not been approved by the owner.', '',
        table(value['comparisons'], [('comparison', 'Source comparison'), ('array', 'Array'),
            ('before', 'Before'), ('after', 'After'), ('exact', 'Exact occurrences'),
            ('relocations', 'Line relocations'), ('field_changes', 'Field changes'),
            ('added', 'Added'), ('removed', 'Removed'), ('position_changes', 'Positional records')]), '',
        'Finite-delta comparison with D128:', '', table(value['d128_coverage'],
            [('array', 'Array'), ('kind', 'Delta type'), ('total', 'Current deltas'),
             ('same_finite_object_delta', 'Same finite D128 delta'), ('new_difference', 'New difference')]), '',
        value['coverage_scope'], '',
        'Complete occurrence objects, exact match indices, violations and ordering changes: `' + record['path'] +
        '`; SHA-256 `' + record['sha256'] + '`. JSON pointers in the report locate each itemized group.', '',
        'Approving the new comparison would address these new scanner findings and tool/source identities. '
        'It would not approve the API packet, the pending margin proposal or a native launch.'])


def apply_control_dispositions(report):
    """Require recorded controls and exact helper identity; code inspection is insufficient."""
    evidence = report['comparison_helper_controls']
    value = evidence.get('data') or {}
    helper = DEV / 'scripts/adhoc/native_h1_scanner_comparison_20261112.py'
    control_record = value.get('controls')
    if isinstance(control_record, dict):
        control_record = control_record.get('controls')
    controls = set(control_record) if isinstance(control_record, list) else set()
    verified = (helper.is_file()
                and value.get('helper_sha256') == sha(helper.read_bytes())
                and value.get('status') == 'synthetic_comparator_controls_passed')
    required = {
        'H1-F3': {'worker_returncode_matches_os_exit'},
        'H1-F4': {'recycled_process_identity_not_signalled'},
    }
    for finding in report['findings']:
        if finding['id'] not in required:
            continue
        finding['required_recorded_controls'] = sorted(required[finding['id']])
        finding['control_evidence'] = {key: evidence[key] for key in ('path', 'sha256', 'state') if key in evidence}
        if verified and required[finding['id']] <= controls:
            finding['state'] = 'resolved_by_recorded_helper_controls'
            finding['verified_helper_sha256'] = value['helper_sha256']


if __name__ == '__main__':
    main()
