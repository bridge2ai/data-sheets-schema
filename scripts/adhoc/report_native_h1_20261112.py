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
                        'temporary_layout_diagnostic_in_trace': 'no writable temporary directory outside d4d-executions' in trace,
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


def completed_witnesses(current):
    witnesses = {}
    for cohort in sorted(current, key=lambda row: row['ended_timestamp'] or 0):
        if cohort['state'] != 'completed':
            continue
        for case in cohort['cases']:
            if case['nodeid']:
                witnesses.setdefault(case['nodeid'], []).append(dict(case,
                    cohort=cohort['id'], source_commit=cohort['source_commit'],
                    evidence=cohort['evidence'], execution=cohort['outcome']))
    return witnesses


def reconciled_rows(old, witnesses):
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
    return rows


def prior_reconciliation(current):
    path = OUT / 'codex-g07-scanner-cohort-classification-20261112.json'
    retained = read_json(path)
    if retained is None:
        return {'state': 'prior_evidence_missing', 'evidence': reference(path)}
    old = retained['negatives']
    assert len(old) == 96 and len({row['nodeid'] for row in old}) == 96
    rows = reconciled_rows(old, completed_witnesses(current))
    return {'state': 'reconciled_by_exact_node_identity', 'evidence': reference(path),
            'prior_count': len(old), 'counts': dict(Counter(row['current_state'] for row in rows)),
            'rows': rows,
            'scope': 'Passing tests establish only their own assertions; missing, skipped or unfinished cases never count as cleared.'}


def ci_reconciliation(current, g07):
    path = OUT / 'lead-ci-run-42976790438-failures-20261112.json'
    classified = OUT / 'codex-g07-ci-cause-ledger-20261112.json'
    inventory = read_json(path)
    if inventory is None:
        return {'state': 'prior_evidence_missing', 'evidence': reference(path)}
    by_node = {}
    for failure in inventory['failures']:
        if 'v2 envelope authority source changed' not in failure['message']:
            continue
        node = failure['file'] + ('::' + failure['node'] if failure['node'] else '')
        by_node.setdefault(node, {'nodeid': node, 'occurrences': []})['occurrences'].append(failure)
    prior = read_json(classified)
    classified_nodes = {item['nodeid'] for group in (prior or {}).get('groups', [])
                        if group['cause'] == 'scanner_native_authority_source_pin'
                        for item in group.get('nodes', [])}
    rows = reconciled_rows(list(by_node.values()), completed_witnesses(current))
    ci_ids = set(by_node)
    g07_ids = {row['nodeid'] for row in g07.get('rows', [])}
    return {'state': 'reconciled_by_exact_node_identity', 'evidence': reference(path),
        'classification_evidence': reference(classified), 'historical_run_id': inventory['run_id'],
        'historical_head': inventory['head'], 'prior_count': len(by_node),
        'classification_identity_set_matches_inventory': classified_nodes == ci_ids,
        'counts': dict(Counter(row['current_state'] for row in rows)), 'rows': rows,
        'file_counts': dict(Counter(node.split('::')[0] for node in ci_ids)),
        'overlap_with_g07': {'ci_is_subset_of_g07': ci_ids <= g07_ids,
            'shared_nodeids': sorted(ci_ids & g07_ids), 'ci_only_nodeids': sorted(ci_ids - g07_ids),
            'g07_only_nodeids': sorted(g07_ids - ci_ids)},
        'scope': 'Retained CI authority-pin identities are reconciled separately from the G07 cohort. Only completed JUnit passes with verified cleanup and source origin count as cleared.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', default='scanner commit; validation and integration in progress')
    parser.add_argument('--comparison', type=Path)
    parser.add_argument('--helper-controls', type=Path, default=SCRATCH / 'h1-comparison-self-check.json',
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
    retained_ci = ci_reconciliation(test_rows, reconciled)
    audit_path = OUT / 'codex-h1-authority-audit-20261112.json'
    comparison = comparison_evidence(args.comparison) if args.comparison else {
        'state': 'pending', 'data': None,
        'scope': 'No complete current D128-form arrays have been supplied. Missing counts are not zero.'}
    comparison['matches_current_branch_head'] = (comparison.get('data') or {}).get('source_branch_head') == head
    if comparison.get('data'):
        comparison['data']['matches_current_branch_head'] = comparison['matches_current_branch_head']
    scan_complete = ((comparison.get('data') or {}).get('status') == 'complete_diagnostic_not_owner_approval'
                     and comparison['matches_current_branch_head'])
    counts = reconciled.get('counts', {})
    answer = ('The scanner comparison is complete as diagnostic evidence; owner disposition remains pending. '
              if scan_complete else
              'The scanner authority repair is committed locally; a complete current scanner comparison is still pending. ')
    answer += ('Of the 96 retained scanner negatives, ' + str(counts.get('cleared', 0)) +
               ' have verified passing witnesses and ' + str(counts.get('unobserved', 0)) +
               ' remain unobserved. Detailed outcomes and integration status follow.')
    answer += (' Separately, ' + str(retained_ci.get('counts', {}).get('cleared', 0)) +
               ' of ' + str(retained_ci.get('prior_count', 'unknown')) +
               ' retained CI authority-pin identities have verified passing witnesses.')
    broad = next((row for row in test_rows if row['id'] == 'h1-scanner-cohort'), None)
    if broad is not None and broad['state'] == 'completed':
        answer += (' The broader scanner cohort remains ' +
                   str(broad['counts'].get('passed', 0)) + ' passed, ' +
                   str(broad['counts'].get('failure', 0)) + ' failed, ' +
                   str(broad['counts'].get('error', 0)) + ' errors and ' +
                   str(broad['counts'].get('skipped', 0)) +
                   ' skipped; clearing retained identities is not whole-cohort acceptance.')
    finished = [integration_record(donor, history) for donor in
                ('ddcadcdc2', 'ab07c81fe', '91fcdab33', '37a4aa5d0', '789778427')]
    restoration = restoration_records()
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
        'retained_ci_authority_negatives': retained_ci,
        'private_configuration_restoration': restoration,
        'report_helpers': report_helpers(),
        'other_helpers': helper2_acceptance(finished[2:]),
        'retained_scanner_comparisons': retained_comparison_refs(head),
        'composition_source_witnesses': source_witnesses(compositions),
        'findings': [
            {'id': 'H1-F1', 'state': 'runner_provenance_limitation', 'detail': 'The runner records HEAD and four protected hashes but does not itself attest the complete tracked working tree. Composition creation and final tracked-clean witnesses mitigate this gap; they do not establish a full before-run content manifest.'},
            portability_finding(test_rows),
            {'id': 'H1-F3', 'state': 'fix_controls_pending', 'detail': 'Independent pre-execution review found a false-completion risk when worker returncode is null but the OS exit is 1. The comparison helper must require matching, typed worker and process exit codes before treating arrays as complete. No run was claimed complete using this defect.'},
            {'id': 'H1-F4', 'state': 'fix_controls_pending', 'detail': 'Independent pre-execution review found that cleanup by numeric process-group ID risks signalling a reused group. The comparison helper must bind owned processes to their recorded identities and refuse signalling replacements. No affected helper run was performed.'}],
        'comparison_helper_controls': captured_json(args.helper_controls) if args.helper_controls else
            {'state': 'pending', 'data': None},
        'findings_publication': 'These are local review findings for lead publication. No GitHub issues, comments or reviews were created during this offline assignment.',
        'owner_pending': [
            'The API packet postimage 830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881 is not approved.',
            'D136 settles freshness age 1200 seconds. Margin remains 90 seconds in code. N1 is at ballot draft v12 and is not ratified; its proposed 300-second margin still awaits the owner.',
            'The current complete D128-form comparison needs an explicit disposition; historical approval applies only to its frozen source pair.',
            'No launch, native canary, publication or scientific acceptance is claimed.'],
        'helper': reference(Path(__file__))}
    data['findings'].append(ambiguous_alias_finding(test_rows))
    data['findings'].append(retained_gap_finding(test_rows))
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
        '**Retained CI authority-pin failures**', '',
        table([{'state': key, 'count': value} for key, value in retained_ci.get('counts', {}).items()],
              [('state', 'Current state'), ('count', 'Retained CI identities')]), '',
        table([{'path': key, 'count': value} for key, value in retained_ci.get('file_counts', {}).items()],
              [('path', 'Retained CI module'), ('count', 'Distinct identities')]), '',
        'Exact identity overlap with the prior G07 set: ' +
        str(len(retained_ci.get('overlap_with_g07', {}).get('shared_nodeids', []))) +
        '. CI identities are a subset of G07: ' +
        str(retained_ci.get('overlap_with_g07', {}).get('ci_is_subset_of_g07', 'unknown')) +
        '. All original CI job occurrences and exact current witnesses are retained in the JSON.', '',
        '**Scanner comparison**', '',
        comparison_text(data['scanner_comparison']), '',
        '**Findings and limits**', '', table(data['findings'],
             [('id', 'Finding'), ('state', 'Status'), ('detail', 'Evidence and limits')]), '',
        data['findings_publication'], '',
        'H1-F2 observed temporary-layout negatives: ' + str(next(row for row in data['findings'] if row['id'] == 'H1-F2').get(
            'observed_negative_count', 0)) + '. They are environment-scope refusals, not validated production failures.', '',
        'H1-F2 recommendation: ' + next(row for row in data['findings'] if row['id'] == 'H1-F2').get(
            'recommendation', 'Await completed portability validation.'), '',
        ambiguous_alias_text(next(row for row in data['findings'] if row['id'] == 'H1-F5')), '',
        retained_gap_text(next(row for row in data['findings'] if row['id'] == 'H1-F6')), '',
        'Comparison-helper control evidence: ' + str(data['comparison_helper_controls'].get('path', 'pending')) +
        '; SHA-256 ' + str(data['comparison_helper_controls'].get('sha256', 'pending')) + '.', '',
        '**Composition source witnesses**', '', table(data['composition_source_witnesses'],
             [('root', 'Source tree'), ('observed_head', 'Observed HEAD'),
              ('tracked_clean', 'Tracked clean'), ('scope', 'Scope')]), '',
        '**Integration**', '', table(data['integration'],
             [('donor', 'Donor commit'), ('subject_matches', 'Local matching commits'), ('state', 'Evidence state')]), '',
        data['other_helpers']['scope'], '', 'Helper 2 observer/test integration state: ' + data['other_helpers']['state'] + '.', '',
        'Lead acceptance evidence:', '', table(data['other_helpers']['status_evidence']['snippets'],
            [('purpose', 'Purpose'), ('first_line', 'First line'), ('last_line', 'Last line'),
             ('sha256', 'Exact snippet SHA-256'), ('text', 'Recorded text')]), '',
        '**Retained comparison identities**', '', table(data['retained_scanner_comparisons'],
            [('path', 'Comparison'), ('source_branch_head', 'Exact branch head'), ('status', 'Saved status'),
             ('matches_current_branch_head', 'Current head'), ('sha256', 'SHA-256')]), '',
        '**Report helpers retained locally**', '', table(data['report_helpers'],
             [('path', 'Helper path'), ('sha256', 'SHA-256'), ('git_status', 'Local Git status')]), '',
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
    summary['d128_unmatched_deltas'] = []
    summary['model_text_function_changes'] = []
    summary['unmatched_approach_pair_context'] = []
    for name, ledger in (value.get('d128_coverage') or {}).get('arrays', {}).items():
        for kind, rows in ledger['delta_occurrences'].items():
            same = sum(row['exact_finite_object_delta_match'] is True for row in rows)
            summary['d128_coverage'].append({'array': name, 'kind': kind, 'total': len(rows),
                'same_finite_object_delta': same, 'new_difference': len(rows) - same,
                'itemized_pointer': '/d128_coverage/arrays/' + name + '/delta_occurrences/' + kind})
            for index, row in enumerate(rows):
                delta = row['current']
                before, after = delta.get('before', {}), delta.get('after', {})
                changed = delta.get('differing_fields', [])
                brief = {'array': name, 'kind': kind, 'path': after.get('path', before.get('path')),
                    'before_line': before.get('line'), 'after_line': after.get('line'),
                    'differing_fields': changed,
                    'before_changed_values': {field: {'present': field in before, 'value': before.get(field)} for field in changed},
                    'after_changed_values': {field: {'present': field in after, 'value': after.get(field)} for field in changed},
                    'exact_finite_object_delta_match': row['exact_finite_object_delta_match'],
                    'itemized_pointer': '/d128_coverage/arrays/' + name + '/delta_occurrences/' + kind + '/' + str(index)}
                if not row['exact_finite_object_delta_match']:
                    summary['d128_unmatched_deltas'].append(brief)
                    if changed == ['approaches']:
                        historical = value['frozen_approval']['arrays'][name]['changed_fields']
                        related = [old for old in historical
                            if old.get('differing_fields') == ['approaches']
                            and old['before'].get('path') == before.get('path')
                            and old['after'].get('path') == after.get('path')
                            and old['before'].get('approaches') == before.get('approaches')
                            and old['after'].get('approaches') == after.get('approaches')]
                        if len(related) == 1:
                            old = related[0]
                            summary['unmatched_approach_pair_context'].append({
                                'path': brief['path'], 'line': before.get('line'),
                                'same_approaches_transition': True,
                                'current_before': before, 'current_after': after,
                                'historical_before': old['before'], 'historical_after': old['after'],
                                'before_pair_differing_fields': object_differing_fields(old['before'], before),
                                'after_pair_differing_fields': object_differing_fields(old['after'], after),
                                'scope': 'Explanatory relationship only; full object pairs remain unequal and unapproved.'})
                if 'model_text_function' in changed:
                    summary['model_text_function_changes'].append(brief)
    violation_ledgers = [item['arrays']['violations'] for item in value.get('comparisons', [])]
    summary['ordered_violations_match_current_and_frozen'] = (
        len(violation_ledgers) == 3 and all(item['exact_arrays_equal'] for item in violation_ledgers)
        and len({item['after_sha256'] for item in violation_ledgers}) == 1)
    summary['ordered_violation_count'] = violation_ledgers[0]['after_count'] if violation_ledgers else None
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
    pair_notes = []
    for row in value.get('unmatched_approach_pair_context', []):
        states = [row[key] for key in ('historical_before', 'historical_after', 'current_before', 'current_after')]
        unchanged_nongating = all(item.get('model_facing') is False and item.get('gates_in') == []
                                 and item.get('violation') is False for item in states)
        pair_notes.extend([
            'The unmatched approach-label pair at `' + row['path'] + ':' + str(row['line']) +
            '` has the same approaches-list transition as D128. It is still a different finite pair: '
            'the current before/after role annotations are `' + str(row['current_before'].get('role')) + '` / `' +
            str(row['current_after'].get('role')) + '`, whereas the historical annotations are `' +
            str(row['historical_before'].get('role')) + '` / `' + str(row['historical_after'].get('role')) +
            '`. Full before-object differences: ' + str(row['before_pair_differing_fields']) +
            '; full after-object differences: ' + str(row['after_pair_differing_fields']) + '.', '',
            'All four objects retain model_facing=false, empty gates_in and violation=false: ' +
            str(unchanged_nongating) + '. This is not a new violation. The changed annotation is not normalized away '
            'and no equivalence or approval is inferred.', ''])
    comparison_scope = ('Complete diagnostic arrays for the current branch are available. They have not been approved by the owner.'
                        if value.get('matches_current_branch_head') else
                        'These complete diagnostic arrays belong to an earlier branch head and are retained as intermediate evidence. The current head still needs its own comparison; no owner approval is implied.')
    return '\n'.join([comparison_scope, '',
        table(value['comparisons'], [('comparison', 'Source comparison'), ('array', 'Array'),
            ('before', 'Before'), ('after', 'After'), ('exact', 'Exact occurrences'),
            ('relocations', 'Line relocations'), ('field_changes', 'Field changes'),
            ('added', 'Added'), ('removed', 'Removed'), ('position_changes', 'Positional records')]), '',
        'Finite-delta comparison with D128:', '', table(value['d128_coverage'],
            [('array', 'Array'), ('kind', 'Delta type'), ('total', 'Current deltas'),
             ('same_finite_object_delta', 'Same finite D128 delta'), ('new_difference', 'New difference')]), '',
        'Current deltas without an exact finite D128 match (coordinates are retained, not normalized or waived):', '',
        table(value['d128_unmatched_deltas'], [('path', 'Path'), ('kind', 'Delta'),
            ('before_line', 'Before line'), ('after_line', 'After line'), ('differing_fields', 'Changed fields'),
            ('before_changed_values', 'Exact before values'), ('after_changed_values', 'Exact after values')]), '',
        *pair_notes,
        'Other current model-text function-coordinate changes, shown with their actual finite D128 matching status:', '',
        table(value['model_text_function_changes'], [('path', 'Path'), ('before_line', 'Before line'),
            ('after_line', 'After line'), ('differing_fields', 'Changed fields'),
            ('before_changed_values', 'Exact before values'), ('after_changed_values', 'Exact after values'),
            ('exact_finite_object_delta_match', 'Exact finite D128 match')]), '',
        'The ordered violation arrays match across current main/candidate and both frozen D128 comparisons: ' +
        str(value['ordered_violations_match_current_and_frozen']) + '; violation count ' +
        str(value['ordered_violation_count']) + '. The complete hit arrays and scanner tool identities still changed. '
        'Identical violation objects do not transfer approval or establish semantic equivalence for other differences.', '',
        value['coverage_scope'], '',
        'Complete occurrence objects, exact match indices, violations and ordering changes: `' + record['path'] +
        '`; SHA-256 `' + record['sha256'] + '`. JSON pointers in the report locate each itemized group.', '',
        'Approving the new comparison would address these new scanner findings and tool/source identities. '
        'It would not approve the API packet, the pending margin proposal or a native launch.'])


def portability_finding(test_rows):
    diagnostic = 'no writable temporary directory outside d4d-executions'
    observed = []
    for cohort in test_rows:
        if cohort['state'] != 'completed':
            continue
        for case in cohort['cases']:
            if case['outcome'] in ('error', 'failure') and (
                    diagnostic in case['message'] or case.get('temporary_layout_diagnostic_in_trace')):
                observed.append(dict(case, cohort=cohort['id'],
                    source_commit=cohort['source_commit'], execution=cohort['outcome'],
                    evidence=cohort['evidence']))
    if not observed:
        return {'id': 'H1-F2', 'state': 'portability_validation_pending',
                'detail': 'The test portability temp_base selection may reject TMPDIR under d4d-executions and choose system tmp outside the permitted scratch location. No completed matching setup-error witness has been observed.'}
    return {'id': 'H1-F2', 'state': 'observed_scope_layout_blocker',
        'detail': 'Completed test evidence records temporary-layout refusals: the copied-helper fixtures reject the allowed TMPDIR under d4d-executions, while system tmp is outside the permitted sandbox scratch. This conflicts with the authorized test environment and is not a demonstrated production failure. The affected copied-helper assertions are not validated.',
        'observed_negative_count': len(observed),
        'observed_error_count': sum(row['outcome'] == 'error' for row in observed),
        'observed_failure_count': sum(row['outcome'] == 'failure' for row in observed),
        'observed_negatives': observed,
        'recommendation': 'Request a narrow lead ruling on permitted temporary layout, or refactor the copied-helper fixtures to meet the approved layout while preserving production guards. No fixture assertion weakening, sandbox expansion or out-of-scope repair is authorized here.',
        'changes_performed': 'None: failure retained, no guard relaxation or additional temporary write location.'}


def object_differing_fields(left, right):
    return sorted(key for key in set(left) | set(right)
                  if key not in left or key not in right
                  or json.dumps(left[key], sort_keys=True) != json.dumps(right[key], sort_keys=True))


def ambiguous_alias_finding(test_rows):
    path = OUT / 'codex-h1-ambiguous-table-finding-20261112.json'
    value = read_json(path)
    if value is None:
        return {'id': 'H1-F5', 'state': 'classification_evidence_pending',
                'detail': 'Two ambiguous argv alias expectations failed; classification remains pending.',
                'evidence': reference(path)}
    witnesses = completed_witnesses(test_rows)
    cases = []
    for observed in value['observed']['failures']:
        element = ET.Element('testcase', observed['testcase'])
        node = canonical_node(element, WT)
        cases.append({'nodeid': node, 'message': observed['failure']['message'],
                      'current_witnesses': witnesses.get(node, [])})
    return {'id': 'H1-F5', 'state': 'requires_lead_contract_ruling', 'priority': 'P2',
        'detail': 'Two observed ambiguous argv alias tests conflict with main scanner precision policy. '
                  'Static source and AST comparisons show the four direct-call-path functions are identical '
                  'from main through the pre-pin candidate and tested composition; this path does not read '
                  'the native authority pin. This is a pre-existing integration contract disagreement, '
                  'not a regression caused by the authority digest update. No historical test rerun was performed.',
        'evidence': reference(path), 'observed_failed_tests': cases,
        'observed_totals': value['observed']['totals'],
        'source_comparisons': value['comparisons'], 'history': value['history_conclusion'],
        'static_call_path': value['static_call_path'], 'recommendation': value['proposed_disposition'],
        'changes_performed': 'None: no test deletion, xfail, assertion weakening or scanner behavior change.'}


def retained_gap_finding(test_rows):
    audit_path = OUT / 'codex-h1-retained-gap-finding-20261112.json'
    audit = read_json(audit_path)
    audit_paths = {
        'F3d_module_helper_print': audit_path,
        'B2_typed_container_alias_token': OUT / 'codex-h1-retained-container-finding-20261112.json',
    }
    witnesses = completed_witnesses(test_rows)
    mismatch = []
    baselines = []
    ignored_aliases = []
    seen_runs, seen_fixtures = set(), set()
    for path in sorted((SCRATCH / 'tests/h1-ci-scanner/cases').glob('*/*/scanner/run.json')):
        physical = path.resolve(strict=True)
        if physical != path.absolute():
            ignored_aliases.append({'path': str(path), 'physical_target': str(physical),
                                    'reason': 'Symlink in leaf or parent path; not a distinct physical fixture run.'})
            continue
        assert physical not in seen_runs, 'duplicate physical fixture run: ' + str(path)
        seen_runs.add(physical)
        value = read_json(path)
        assert value['fixture'] not in seen_fixtures, 'duplicate physical fixture identity: ' + value['fixture']
        seen_fixtures.add(value['fixture'])
        if value.get('fixture') == 'F0':
            baselines.append(dict(reference(path), data=value))
        expected, actual = value.get('expected_violations'), value.get('violation_count')
        if type(expected) is not int or type(actual) is not int or expected == actual:
            continue
        node = 'tests/test_native_u3l_review_fixtures.py::test_retained_review_outcome[' + value['fixture'] + ']'
        classified_path = audit_paths.get(value['fixture'])
        classified = read_json(classified_path) if classified_path else None
        classification = (dict(reference(classified_path), fixture_scope=value['fixture'],
            summary={key: data for key, data in (classified or {}).items() if key != 'commands'})
            if classified_path else {'state': 'pending', 'fixture_scope': value['fixture']})
        mismatch.append({'nodeid': node, 'fixture': value['fixture'], 'expected_violations': expected,
            'actual_violations': actual, 'fixture_run_status': value.get('status'),
            'derivation_complete': value.get('derivation_complete'), 'failure': value.get('failure'),
            'scan_run': dict(reference(path), data=value), 'scan_arrays': reference(path.parent / 'scan.json'),
            'current_witnesses': witnesses.get(node, []), 'classification': classification})
    return {'id': 'H1-F6', 'state': 'requires_lead_fixture_disposition' if mismatch else 'fixture_evidence_pending',
        'priority': 'P2', 'detail': 'Retained historical known-gap fixture expectations disagree with the current complete scanner arrays. '
        'Separate source-history audits establish that the F3d and B2 expectations predate intentional main scanner improvements. '
        'The current positive controls support those bounded improvements; the historical fixture assertions still fail. Keep each failure visible and '
        'do not change frozen fixtures or count retained CI identities as cleared without completed passing witnesses.',
        'observed_mismatches': mismatch, 'unmutated_baseline_runs': baselines,
        'ignored_alias_paths': ignored_aliases,
        'physical_run_count': len(seen_runs), 'unique_physical_fixture_count': len(seen_fixtures),
        'classification': dict(reference(audit_path), summary={key: value for key, value in (audit or {}).items() if key != 'commands'}),
        'recommendation': 'Keep the known-gap expectation disagreement separate from the authority-pin repair. '
        'Preserve the frozen U3-L fixture and D128 evidence. Subject to lead approval, version the current '
        'expectation separately around the unmutated baseline plus the exact newly detected planted occurrences '
        'and their actual gate membership, only after its own source-history classification and violation objects are reviewed. '
        'Do not silently relax counts or mark the currently failing CI identity cleared by judgement.',
        'changes_performed': 'None: no fixture edits, scanner behavior changes or new baseline runs by the report helper.'}


def retained_gap_text(finding):
    if not finding.get('observed_mismatches'):
        return 'H1-F6 retained-gap fixture evidence remains pending.'
    audits = [dict(fixture=row['fixture'], **row['classification']) for row in finding['observed_mismatches']]
    classified_text = []
    for row in finding['observed_mismatches']:
        summary = row['classification'].get('summary') or {}
        if not summary:
            continue
        explanation = summary.get('causal_explanation', summary.get('explanation', []))
        recommendation = summary.get('recommendation') or {}
        classified_text.extend(['**' + row['fixture'] + ' source evidence**', '',
            *['- ' + text for text in explanation], '', recommendation.get('action', ''), '',
            recommendation.get('restrictions', recommendation.get('prohibit', '')), ''])
    return '\n'.join(['**H1-F6: retained known-gap fixture disagreements**', '', finding['detail'], '',
        table(finding['observed_mismatches'], [('nodeid', 'Observed fixture'),
            ('expected_violations', 'Expected violations'), ('actual_violations', 'Actual violations'),
            ('derivation_complete', 'Scanner derivation complete'), ('fixture_run_status', 'Fixture run status'),
            ('failure', 'Saved assertion')]), '',
        'Exact scan arrays, command, stable-input census and completed-test witnesses are hash-linked in the JSON. '
        'A saved fixture run does not substitute for the final cohort JUnit and cleanup evidence.', '',
        'Per-fixture source-history classification:', '', table(audits,
             [('fixture', 'Fixture'), ('state', 'Evidence state'), ('path', 'Audit'), ('sha256', 'SHA-256')]), '',
        *classified_text, finding['recommendation']])


def integration_record(donor, history):
    full = git('rev-parse', donor).decode().strip()
    subject = git('show', '-s', '--format=%s', donor).decode().strip()
    matches = [row for row in history if row['subject'] == subject]
    source_paths = git('diff', '--name-only', full + '^', full, '--').decode().splitlines()
    source_diff = git('diff', '--binary', full + '^', full, '--', *source_paths)
    verified = []
    for matched in matches:
        local = matched['commit']
        local_paths = git('diff', '--name-only', local + '^', local, '--').decode().splitlines()
        local_diff = git('diff', '--binary', local + '^', local, '--', *local_paths)
        postimages = []
        for path in sorted(set(source_paths) | set(local_paths)):
            row = {'path': path}
            for name, commit in (('donor', full), ('local', local)):
                entry = git('ls-tree', commit, '--', path).decode().strip()
                row[name + '_tree_entry'] = entry
                row[name + '_blob_sha256'] = sha(git('show', commit + ':' + path)) if entry else None
            row['postimage_equal'] = row['donor_tree_entry'] == row['local_tree_entry'] and row['donor_blob_sha256'] == row['local_blob_sha256']
            postimages.append(row)
        exact = (source_paths == local_paths and source_diff == local_diff
                 and all(row['postimage_equal'] for row in postimages))
        verified.append({'local_commit': local, 'donor_paths': source_paths, 'local_paths': local_paths,
            'path_rosters_equal': source_paths == local_paths, 'postimages': postimages,
            'donor_binary_diff_sha256': sha(source_diff), 'local_binary_diff_sha256': sha(local_diff),
            'binary_diffs_equal': source_diff == local_diff, 'exact_cherry_pick_verified': exact})
    return {'donor': full, 'subject': subject, 'subject_matches': matches, 'verification': verified,
        'state': 'exact_cherry_pick_verified' if len(verified) == 1 and verified[0]['exact_cherry_pick_verified']
                 else 'needs_diff_review' if matches else 'not_yet_present',
        'scope': 'Commit identity, exact changed-path roster, modes/postimage bytes and binary patch verified independently of the subject. Test evidence remains separate.'}


def report_helpers():
    names = ('prepare_native_h1_helpers_20261112.py', 'restore_native_h1_config_20261112.py',
             'report_native_h1_20261112.py', 'native_h1_authority_audit_20261112.py',
             'native_h1_scanner_comparison_20261112.py', 'h1_ambiguous_table_finding_20261112.py',
             'h1_retained_gap_finding_20261112.py', 'h1_retained_container_finding_20261112.py')
    rows = []
    for name in names:
        path = DEV / 'scripts/adhoc' / name
        command = ['/usr/bin/git', '-C', str(DEV), 'status', '--porcelain', '--', str(path.relative_to(DEV))]
        status = subprocess.check_output(command, env=git_environment()).decode().strip()
        rows.append(dict(reference(path), git_status=status,
                         scope='Local provenance helper; this assignment does not commit or publish this report-worktree file.'))
    return rows


def helper2_acceptance(integrations):
    status = EXEC.parent / 'data-sheets-schema/notes/coordination/STATUS.md'
    raw = status.read_bytes()
    lines = raw.splitlines(keepends=True)
    marker = b'Helper 2, three handoffs, all accepted by the lead'
    matches = [index for index, line in enumerate(lines) if marker in line]
    snippets = []
    accepted = False
    if len(matches) == 1:
        index = matches[0]
        body = b''.join(lines[index:index + 2])
        accepted = all(token in body for token in (b'91fcdab33', b'37a4aa5d0', b'789778427',
                                                   b'codex-h2-observer-alias-20261112.md'))
        snippets.append({'purpose': 'Lead acceptance of the original observer and test lane only',
            'first_line': index + 1, 'last_line': index + 2, 'sha256': sha(body), 'text': body.decode()})
        headers = [n for n in range(index) if b'2026-11-12T18:48:30Z' in lines[n]]
        if headers:
            start = headers[-1]
            context = b''.join(lines[start:start + 2])
            snippets.append({'purpose': 'Dated lead entry and N1 ballot v12 context',
                'first_line': start + 1, 'last_line': start + 2,
                'sha256': sha(context), 'text': context.decode()})
    integrated = [item for item in integrations if item['state'] == 'exact_cherry_pick_verified']
    state = ('lead_accepted_all_three_integrated_tests_reported_separately' if accepted and len(integrated) == 3
             else 'lead_accepted_integration_in_progress' if accepted
             else 'acceptance_evidence_not_verified')
    return {'state': state, 'lead_acceptance_verified': accepted,
        'status_evidence': {'path': str(status), 'sha256': sha(raw), 'bytes': len(raw),
                            'state': 'present', 'snippets': snippets},
        'authorized_donors': [item['donor'] for item in integrations],
        'helper2_commits_integrated': [item['verification'][0]['local_commit'] for item in integrated],
        'scope': 'Lead acceptance authorizes only the original observer repair and its two test commits, including public-completion verification in a protected-file scratch composition. The later launch-sequence and review-bundle lanes are not included or authorized by this report.'}


def retained_comparison_refs(head):
    rows = []
    for path in sorted(SCRATCH.glob('*/comparison.json')):
        value = read_json(path)
        if value.get('kind') != 'native_h1_scanner_comparison':
            continue
        rows.append(dict(reference(path), status=value.get('status'),
            source_branch_head=value.get('source_branch_head'),
            matches_current_branch_head=value.get('source_branch_head') == head,
            scope='Saved source-bound diagnostic; earlier complete comparisons remain intermediate evidence.'))
    return rows


def restoration_records():
    rows = []
    for path in sorted(SCRATCH.glob('*/config-restored.json')):
        value = read_json(path)
        config = Path(value['config'])
        current = reference(config)
        rows.append(dict(reference(path), data=value, current_config=current,
                         current_config_matches_restoration=current.get('sha256') == value.get('restored_sha256')))
    return rows


def ambiguous_alias_text(finding):
    if finding.get('id') != 'H1-F5':
        return ''
    evidence = finding.get('evidence') or {}
    if finding.get('state') == 'classification_evidence_pending':
        return 'H1-F5 classification evidence is pending.'
    recommendation = finding['recommendation']
    return '\n'.join(['**H1-F5: unresolved scanner integration contract**', '',
        finding['detail'], '',
        table(finding['observed_failed_tests'], [('nodeid', 'Observed failed test'), ('message', 'Actual failure')]), '',
        'Source-history classification: `' + evidence['path'] + '`; SHA-256 `' + evidence['sha256'] + '`.', '',
        'Main changed this behavior deliberately in `' + finding['history']['main_behavior_change'] +
        '`; the older native test contract originated in `' + finding['history']['test_contract_origin'] + '`.', '',
        'Recommended separate follow-up, requiring lead disposition: ' + recommendation['recommendation'], '',
        recommendation['scope'], '', finding['changes_performed']])


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
