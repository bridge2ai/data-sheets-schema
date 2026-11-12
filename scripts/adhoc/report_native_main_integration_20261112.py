#!/usr/bin/env python3
"""Render the G04/G05 integration handoff from its JSON ledger, 2026-11-12.

Inputs: assigned new worktree Git state, resolution evidence, offline test logs.
Outputs: requested handoff JSON and Markdown in this report worktree.
No project imports, tests, network, native binaries, composition or Git writes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

DEV = Path(__file__).resolve().parents[2]
WT = DEV.parent / 'codex-native-main-integration-20261112'
HANDOFF = DEV / 'notes/development_efficiency_20261111/handoffs'
JSON_PATH = HANDOFF / 'codex-native-main-integration-20261112.json'
MD_PATH = JSON_PATH.with_suffix('.md')
NATIVE = '1a137b58860416a31618de44173180d021dfcc61'
MAIN = '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['/usr/bin/git', *args], cwd=WT).decode().strip()


def cell(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace('|', '\\|').replace('\n', '<br>')


def table(rows, columns):
    return '\n'.join(['| ' + ' | '.join(label for _, label in columns) + ' |',
                      '| ' + ' | '.join('---' for _ in columns) + ' |'] +
                     ['| ' + ' | '.join(cell(row.get(key, '')) for key, _ in columns) + ' |' for row in rows])


def read_tests():
    rows = []
    for plan_path in sorted((WT / '.temp/native-main-integration/tests').glob('*/plan.json')):
        folder = plan_path.parent
        plan = json.loads(plan_path.read_text())
        outcome_path = folder / 'outcome.json'
        outcome = json.loads(outcome_path.read_text()) if outcome_path.exists() else {}
        command_path = folder / 'pytest-command.json'
        pytest_command = json.loads(command_path.read_text()) if command_path.exists() else None
        xml = folder / 'pytest.xml'
        counts = {}; failures = []
        log_path = folder / 'pytest.log'
        log_text = log_path.read_text(errors='replace') if log_path.exists() else ''
        collection = re.findall(r'(\d+) tests? collected(?:, (\d+) errors?)?', log_text)
        if xml.exists():
            root = ET.parse(xml).getroot()
            suites = list(root.iter('testsuite'))
            counts = {k: sum(int(s.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
            for case in root.iter('testcase'):
                for kind in ('failure', 'error'):
                    for detail in case.findall(kind):
                        failures.append({'node': case.get('classname', '') + '::' + case.get('name', ''),
                                         'kind': kind, 'message': detail.get('message', ''),
                                         'detail': detail.text or ''})
        rows.append({'id': folder.name, 'source_commit': plan.get('source_commit'),
                     'command': plan.get('command'), 'pytest_command': pytest_command,
                     'seconds': outcome.get('seconds'), 'returncode': outcome.get('returncode'),
                     'cleanup_verified': outcome.get('cleanup_verified'), 'counts': counts,
                     'collected_count': int(collection[-1][0]) if collection else None,
                     'failures': failures, 'log': str(folder / 'pytest.log'),
                     'log_sha256': sha((folder / 'pytest.log').read_bytes()) if (folder / 'pytest.log').exists() else None,
                     'outcome': outcome, 'environment': plan.get('environment'),
                     'classification': 'pending adjudication' if failures or outcome.get('returncode') not in (0, None) else 'passed or pending; see outcome'})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['merge-created', 'part1-tested', 'complete', 'blocked'], required=True)
    parser.add_argument('--answer', required=True)
    args = parser.parse_args()
    resolution = json.loads((WT / '.temp/native-main-integration/merge-resolution.json').read_text())
    previous = json.loads(JSON_PATH.read_text()) if JSON_PATH.exists() else {}
    head = git('rev-parse', 'HEAD')
    parents = git('show', '-s', '--format=%P', head).split()
    merge_head = head if parents == [NATIVE, MAIN] else previous.get('merge_commit')
    assert merge_head, 'first handoff requires the actual merge commit'
    protected = []
    for record in resolution['protected_files']:
        path = record['path']
        current = sha((WT / path).read_bytes())
        assert current == record['main_sha256'], path
        protected.append(dict(record, candidate_sha256=current))
    conflicts = resolution['conflicts']
    for row in conflicts:
        if row['path'].endswith('scan.py'):
            row.update(native_intent='Native attribution, genuine route/API refusal, native producer/source contracts.',
                       main_intent='Expanded command discovery and alias fixes, parameter shadowing, joins and module closures.',
                       resolution='Take main in all nine blocks; preserve auto-merged native contracts. Main already defines derive_native_shared_route, so its conditional executes the same route proof.',
                       rationale='Independent read-only conflict review found no design stop; preserve both sets of behavior.')
        else:
            row.update(native_intent='Version 1.10.3 and integrated native-v2 contract documentation.',
                       main_intent='Plain-alias and expanded command-discovery coverage, with current limitations.',
                       resolution='Keep version 1.10.3 and both appended sections; reconcile obsolete unresolved-gap wording.',
                       rationale='Documentation describes combined source while retaining remaining copied-alias/helper-stdout limitations.')
    data = dict(previous, phase=args.phase, answer=args.answer, worktree=str(WT),
                branch=git('branch', '--show-current'), native_parent=NATIVE, main_parent=MAIN,
                merge_commit=merge_head, freshness_commit=head if args.phase == 'complete' and head != merge_head else None,
                current_head=head, conflicts=conflicts, protected_files=protected,
                tests=read_tests(), v1_sha256=sha((WT / 'src/data_sheets_schema/native_subscription_guard.py').read_bytes()),
                setup_notes=previous.get('setup_notes', [
                    'Initial disk check: 157074088 KiB available, above the 10 GiB gate.',
                    'New branch/worktree only. Sparse selection materialized with read-tree after two merge attempts refused the unpopulated no-checkout index; neither attempt entered a merge.',
                    'Actual content merge has two conflicted paths: nine scanner blocks and two skill-document blocks. Tests auto-merged 897 added lines.',
                    'Protected api_runner main-byte selection intentionally removes native RunSpec hooks; pending packet integration is not repaired in this brief.',
                    'No amendment/operator-guide edits, packet application, private composition, CPU diagnostic, native/provider/model call or publication.',
                ]))
    assert data['v1_sha256'] == resolution['v1_sha256'], 'historical guard v1 changed'
    for run in data['tests']:
        note = data.get('run_adjudications', {}).get(run['id'])
        if note:
            run['classification'] = note['classification']
            run['classification_evidence'] = note['evidence']
            for failure in run['failures']:
                failure['classification'] = note.get('failure_classes', {}).get(
                    failure['node'], note.get('kind_classes', {}).get(failure['kind'], note['classification']))
        if run['id'] in {'canary-freshness-1200', 'freshness-1200'}:
            patch = WT / '.temp/native-main-integration/g05-tested.patch'
            run['tested_working_delta'] = {'base_commit': merge_head,
                'path': str(patch), 'sha256': sha(patch.read_bytes()),
                'note': 'Run recorded merge HEAD plus this saved uncommitted delta; final commit equality is checked below.'}
    if args.phase == 'complete':
        patch = WT / '.temp/native-main-integration/g05-tested.patch'
        actual = subprocess.check_output(['/usr/bin/git', 'diff', '--binary', merge_head, head], cwd=WT)
        assert actual == patch.read_bytes(), 'committed freshness diff differs from tested bytes'
        data['freshness_evidence'] = {'tested_patch': str(patch), 'sha256': sha(actual),
            'committed_delta_equals_tested_delta': True,
            'parent_is_merge_commit': parents == [merge_head]}
        assert data['freshness_evidence']['parent_is_merge_commit']
        by_id = {row['id']: row for row in data['tests']}
        before, after = by_id['freshness-merge'], by_id['freshness-1200']
        before_failures = {(item['node'], item['message']) for item in before['failures']}
        after_failures = {(item['node'], item['message']) for item in after['failures']}
        assert before_failures == after_failures and len(after_failures) == 41
        assert all('probe sequence directory overlaps source or the selected executable' in message
                   for _, message in after_failures)
        assert before['counts'] == {'tests': 351, 'failures': 41, 'errors': 0, 'skipped': 0}
        assert after['counts'] == {'tests': 352, 'failures': 41, 'errors': 0, 'skipped': 0}
        after['classification'] = before['classification']
        after['classification_evidence'] = ('The exact same 41 node/message pairs fail before and after; '
            'the independent policy-pin case adds one pass (310 to 311). ' + before['classification_evidence'])
        for failure in after['failures']:
            failure['classification'] = before['classification']
        data['freshness_evidence']['before_after_failure_nodes_and_messages_identical'] = True
        data['freshness_evidence']['before_passed'] = 310
        data['freshness_evidence']['after_passed'] = 311
        data['freshness_evidence']['failures_each'] = 41
    # Raw logs retain exact diagnostics; printable deliverables contain no at-sign.
    raw = json.dumps(data, indent=2, ensure_ascii=False).replace(chr(64), '[at]') + '\n'
    data = json.loads(raw)
    parts = ['# Native main integration — 2026-11-12', '', data['answer'], '',
             'Phase: ' + data['phase'] + '. Offline preparation only; provisional age is not owner ratification.', '',
             table([{'kind': 'branch', 'value': data['branch']}, {'kind': 'worktree', 'value': str(WT)},
                    {'kind': 'native parent', 'value': NATIVE}, {'kind': 'main parent', 'value': MAIN},
                    {'kind': 'merge commit', 'value': merge_head}, {'kind': 'freshness commit', 'value': data['freshness_commit'] or 'not committed'},
                    {'kind': 'current head', 'value': head}], [('kind','Identity'),('value','Value')]), '',
             '**Conflict ledger**', '', table(conflicts, [('path','Path'),('kind','Kind'),('blocks','Blocks'),('native_intent','Native intent'),('main_intent','Main intent'),('resolution','Kept'),('rationale','Why')]), '',
             '**Protected files**', '', table(protected, [('path','Path'),('candidate_sha256','Candidate SHA-256'),('main_sha256','Main SHA-256'),('equal','Equal')]), '',
             '**Tests**', '', table(data['tests'], [('id','Run'),('source_commit','Source'),('pytest_command','Exact pytest arguments'),('seconds','Seconds'),('returncode','Exit'),('counts','Counts'),('collected_count','Collected'),('cleanup_verified','Cleanup'),('classification','Classification'),('log','Log')]), '',
             'The JSON retains wrapper commands, environment policy, every XML error/failure and raw-log digests. Literal at-signs in diagnostics are rendered as [at]; raw logs are unmodified.', '']
    if data.get('findings'):
        parts += ['**Findings and remaining gates**', '', table(data['findings'], [('id','ID'),('classification','Class'),('evidence','Evidence'),('disposition','Disposition')]), '']
    if data.get('freshness_changes'):
        parts += ['**Provisional freshness changes**', '', table(data['freshness_changes'], [('path','Path'),('change','Change'),('literals','Remaining pins')]), '']
    if data.get('freshness_evidence'):
        parts += ['Freshness tests ran before the separate commit, against merge HEAD plus the saved patch. The committed delta was compared byte-for-byte with that patch: ' + cell(data['freshness_evidence']), '']
    if data.get('helper_scripts'):
        parts += ['**Provenance helpers**', '', table(data['helper_scripts'], [('path','Path'),('status','Status')]), '']
    parts += ['**Setup and limits**', ''] + data['setup_notes'] + ['', '**Reproduce this handoff**', '',
              '```sh', 'env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/var/empty GIT_NO_LAZY_FETCH=1 \\',
              '  /opt/homebrew/Caskroom/miniforge/base/bin/python3.13 -S -B \\',
              '  scripts/adhoc/report_native_main_integration_20261112.py \\',
              '  --phase ' + args.phase + ' --answer "<the answer string in the JSON>"', '```', '',
              'All tables are generated from the JSON. No STATUS write or GitHub action is part of this handoff.', '']
    report = '\n'.join(parts)
    assert chr(64) not in raw and chr(64) not in report
    JSON_PATH.write_text(raw)
    MD_PATH.write_text(report)
    assert json.loads(JSON_PATH.read_text()) == data and MD_PATH.read_text() == report
    for path in (JSON_PATH, MD_PATH):
        assert path.stat().st_size
        print(str(path)); print(sha(path.read_bytes()))


if __name__ == '__main__':
    main()
