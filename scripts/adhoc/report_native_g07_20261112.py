#!/usr/bin/env python3
"""Render G07/capture handoffs and owner packet from JSON, 2026-11-12.

Inputs: immutable scratch packet/composition/test artifacts and local Git state.
Outputs: requested JSON, Markdown and owner-review Markdown in this report repo.
No project imports, tests, network, protected edits or Git writes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

DEV = Path(__file__).resolve().parents[2]
EXEC = DEV.parent
WT = EXEC / 'codex-native-main-integration-20261112'
SCRATCH = EXEC / 'scratch-native-main-integration-20261112'
OUT = DEV / 'notes/development_efficiency_20261111/handoffs'
JSON_PATH = OUT / 'codex-native-packets-g07-20261112.json'
MD_PATH = JSON_PATH.with_suffix('.md')
OWNER_PATH = OUT / 'codex-native-packets-owner-review-20261112.md'
ASSESSMENT_PATH = OUT / 'codex-g07-assessment-20261112.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def cell(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace('|', '\\|').replace('\n', '<br>')


def table(rows, columns):
    return '\n'.join(['| ' + ' | '.join(label for _, label in columns) + ' |',
        '| ' + ' | '.join('---' for _ in columns) + ' |'] +
        ['| ' + ' | '.join(cell(row.get(key, '')) for key, _ in columns) + ' |' for row in rows])


def scanner_text(value):
    lines = [value.get('reason', value.get('state', 'pending'))]
    if value.get('state') == 'blocked_before_complete_arrays':
        lines += ['', 'Current exact matches, relocations, field changes, additions, removals and '
                  'violation objects are **unavailable**. They are not zero.', '',
                  'Observed source: `src/data_sheets_schema/native_execution_authority_v2.py`.',
                  'Scanner expected: `' + value['authority_expected_sha256'] + '`.',
                  'Current bytes: `' + value['authority_actual_sha256'] + '`.', '',
                  value['protected_packet_scope']]
    old = value.get('retained_d128')
    if old:
        lines += ['', 'The retained D128 comparison covers its original source pair only:', '',
                  table([{'measure': key, 'count': number} for key, number in old['counts'].items()],
                        [('measure', 'Retained measure'), ('count', 'Historical count')]), '',
                  old['scope'], '', 'Itemized historical ledger: `' + old['itemized_ledger'] + '`; SHA-256 `' +
                  old['itemized_ledger_sha256'] + '`. The JSON preserves the complete source and array references.']
    if value.get('required_followup'):
        lines += ['', value['required_followup']]
    return '\n'.join(lines)


def capture_text(value):
    lines = [value.get('state', 'pending') + '.', '']
    if value.get('commit'):
        lines += ['Separate local commit: `' + value['commit'] + '`.', '']
    if value.get('finding_confirmed'):
        lines += [value['finding_confirmed'], '']
    lines += ['- ' + item for item in value.get('implementation', [])]
    for key in ('design_ruling', 'validation', 'coverage_limit'):
        if value.get(key):
            lines += ['', str(value[key])]
    return '\n'.join(lines)


def tests():
    rows = []
    for path in sorted((SCRATCH / 'tests').glob('*/plan.json')):
        folder = path.parent
        plan = json.loads(path.read_bytes())
        outcome_path = folder / 'outcome.json'
        outcome = json.loads(outcome_path.read_bytes()) if outcome_path.exists() else {}
        counts = {}; negatives = []
        if (folder / 'pytest.xml').exists():
            root = ET.parse(folder / 'pytest.xml').getroot()
            counts = {key: sum(int(s.get(key, '0')) for s in root.iter('testsuite'))
                      for key in ('tests', 'failures', 'errors', 'skipped')}
            counts['passed'] = counts['tests'] - sum(counts[k] for k in ('failures', 'errors', 'skipped'))
            for case in root.iter('testcase'):
                for item in case:
                    if item.tag in {'failure', 'error'}:
                        negatives.append({'node': case.get('classname', '') + '::' + case.get('name', ''),
                            'kind': item.tag, 'message': item.get('message', ''), 'traceback': item.text})
        log = folder / 'pytest.log'
        rows.append({'id': folder.name, 'plan': plan, 'outcome': outcome,
            'seconds': outcome.get('seconds'), 'returncode': outcome.get('returncode'),
            'counts': counts, 'negatives': negatives, 'log': str(log),
            'log_sha256': sha(log.read_bytes()) if log.exists() else None,
            'command': plan['command'], 'source_commit': plan['source_commit']})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--composition', type=Path, required=True)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--answer', required=True)
    args = parser.parse_args()
    manifest = json.loads(args.composition.read_bytes())
    previous = json.loads(JSON_PATH.read_bytes()) if JSON_PATH.exists() else {}
    if ASSESSMENT_PATH.exists():
        previous.update(json.loads(ASSESSMENT_PATH.read_bytes()))
        previous['assessment'] = {'path': str(ASSESSMENT_PATH),
                                  'sha256': sha(ASSESSMENT_PATH.read_bytes())}
    rows = manifest['packets']
    for row in rows:
        row['branch_sha256'] = sha((WT / row['path']).read_bytes())
        assert row['branch_sha256'] == row['main_sha256']
        row['postimage'] = str(Path(row['patch']).with_suffix('.postimage'))
        assert sha(Path(row['postimage']).read_bytes()) == row['postimage_sha256']
        assert sha(Path(row['patch']).read_bytes()) == row['patch_sha256']
    head = subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=WT).decode().strip()
    data = dict(previous, phase=args.phase, answer=args.answer, current_branch_head=head,
        composition_manifest=str(args.composition), composition_manifest_sha256=sha(args.composition.read_bytes()),
        composition=manifest, packets=rows, tests=tests(),
        owner_value='D136 decides 1200 seconds and unchanged margin 90; N1 as a whole remains unratified.',
        scanner_comparison=previous.get('scanner_comparison', {'state': 'pending', 'exact': None,
            'line_relocations': None, 'field_changes': None, 'additions': None, 'removals': None,
            'violations': None, 'reason': 'No current complete scan arrays yet; null is not zero.'}),
        capture_selection=previous.get('capture_selection', {'state': 'not yet assessed'}))
    comparison = OUT / 'codex-g07-cohort-comparison-20261112.json'
    if comparison.exists():
        compared = json.loads(comparison.read_bytes())
        data['cohort_comparison'] = {'path': str(comparison), 'sha256': sha(comparison.read_bytes()),
            'pairs': [{key: row[key] for key in ('before', 'after', 'merge_cause_negatives',
                       'merge_cause_after_outcomes', 'old_signature_still_present', 'after_not_observed')}
                      for row in compared['cohort_pairs']]}
    data['private_configuration_restoration'] = []
    for label in ('g07-b', 'g07-c'):
        receipt = SCRATCH / label / 'config-restored.json'
        if receipt.exists():
            restored = json.loads(receipt.read_bytes())
            assert sha(Path(restored['config']).read_bytes()) == restored['restored_sha256']
            data['private_configuration_restoration'].append({
                'path': str(receipt), 'sha256': sha(receipt.read_bytes()), 'receipt': restored})
    helper_names = (
        'report_native_g07_20261112.py', 'classify_g07_ci_scanner_20261112.py',
        'restore_g07_private_config_20261112.py', 'compare_g07_cohorts_20261112.py',
        'run_g07_ci_selectors_20261112.py', 'classify_g07_scanner_cohort_20261112.py')
    data['helpers'] = [{'path': str(DEV / 'scripts/adhoc' / name),
                       'sha256': sha((DEV / 'scripts/adhoc' / name).read_bytes()),
                       'status': 'local report helper; not committed by this assignment'}
                      for name in helper_names]
    for name in ('codex-g07-ci-cause-ledger-20261112.json',
                 'codex-g07-scanner-cohort-classification-20261112.json'):
        evidence = OUT / name
        if evidence.exists():
            data.setdefault('supporting_evidence', {})[name] = {
                'path': str(evidence), 'sha256': sha(evidence.read_bytes())}
    for row in data['tests']:
        note = data.get('test_adjudications', {}).get(row['id'])
        if note:
            row['adjudication'] = note
    raw = json.dumps(data, indent=2, ensure_ascii=False).replace(chr(64), '[at]') + '\n'
    data = json.loads(raw)
    intro = ['# Native protected packets and capture selection — 2026-11-12', '', data['answer'], '',
        data['owner_value'], '', 'Branch head: `' + head + '`. Composition manifest: ' + str(args.composition), '',
        table(rows, [('path','Protected file'),('postimage_sha256','Proposed postimage SHA-256'),
            ('d127_approved_sha256','D127 SHA-256'),('equals_d127','Equal'),('branch_sha256','Unchanged branch SHA-256')]), '',
        '**Validation**', '', table(data['tests'], [('id','Cohort'),('source_commit','Source'),('seconds','Seconds'),
            ('returncode','Exit'),('counts','Counts'),('adjudication','Disposition'),('log','Log')]), '',
        'Commands, environment, cleanup/origin checks and every negative traceback are in the JSON. '
        'At-sign characters are displayed as [at]; exact raw evidence remains in the referenced logs and XML.', '',
        '**Scanner comparison**', '', scanner_text(data['scanner_comparison']), '',
        '**Capture selection**', '', capture_text(data['capture_selection']), '']
    for key, title in [('findings','Findings and remaining gates'), ('ci_classes','Retained CI failure classes')]:
        if data.get(key):
            intro += ['**' + title + '**', '', table(data[key], [('id','ID'),('count','Count'),
                ('evidence','Evidence'),('disposition','Disposition')]), '']
    for key, title in [('cohort_comparison', 'Exact test identity comparison'),
                       ('private_configuration_restoration', 'Private test configuration restoration'),
                       ('review', 'Independent review'), ('helpers', 'Saved helper scripts')]:
        if data.get(key):
            intro += ['**' + title + '**', '', cell(data[key]), '']
    intro += ['**Reproduce the reports**', '', '```sh',
        'env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/var/empty \\',
        '  /opt/homebrew/Caskroom/miniforge/base/bin/python3.13 -S -B \\',
        '  scripts/adhoc/report_native_g07_20261112.py \\',
        '  --composition ' + str(args.composition) + ' \\',
        '  --phase ' + args.phase + ' --answer "<answer from JSON>"', '```', '',
        'Tables are generated from this JSON. No publication, provider/native call, protected branch edit or packet approval is implied.', '']
    owner = ['# Owner review: four protected native packets — 2026-11-12', '',
        table(rows, [('path','File'),('postimage_sha256','Proposed SHA-256')]), '',
        'These are proposed scratch bytes, not installed branch bytes. Three postimages match D127 exactly. '
        'The API postimage differs and needs a fresh exact-hash decision. This document requests no launch, merge or spend.', '',
        data['answer'], '', '**Comparison with D127**', '',
        table(rows, [('path','File'),('d127_approved_sha256','D127 approved SHA-256'),('equals_d127','Equal'),('patch','Main-relative patch')]), '',
        'The current main protected blobs equal the earlier main 2cfc4666. The API postimage preserves '
        'main\'s newer datatype handling: multivalued slots whose range is a declared type or enum are '
        'included, rather than only slots whose range is literally string. This is the entire difference '
        'from the D127-approved API postimage.', '']
    api = next(row for row in rows if row['name'] == 'api_runner_companion')
    owner += ['The display spells diff hunk markers as [at] to satisfy the report format. '
              'Use the linked raw patch for machine replay.', '',
        '```diff', Path(api['since_d127_diff']).read_text().rstrip(), '```', '',
        'Relative to current main, the native API patch restores the reviewed native RunSpec fields, '
        'renderer/native admission, selection and replay binding, metadata/toolchain handling, assembly '
        'digest, native instruction route and API execution refusal. Shared selection remains unconditional '
        'and delegates the native validation to the shared-generation hook. The complete patch is linked above; '
        'its SHA-256 is `' + api['patch_sha256'] + '`.', '',
        'The shared-generation packet adds native validation to selection. The canonical packet adds the '
        'two native prompt pins at repository-relative location dot, preserving existing entries. The sidecar '
        'updates exact function/source pins while preserving the 21 D76 contracts and their approval semantics.', '',
        '**Current review gates**', '', scanner_text(data['scanner_comparison']), '', capture_text(data['capture_selection']), '',
        'Approval must name the exact postimage hashes above. Equal historical bytes retain their identity; '
        'this report does not extend D128 to any new scanner output or waive complete final-source validation.', '']
    for path, body in ((JSON_PATH, raw), (MD_PATH, '\n'.join(intro)), (OWNER_PATH, '\n'.join(owner))):
        body = body.replace(chr(64), '[at]')
        assert chr(64) not in body
        path.write_text(body)
        assert path.read_text() == body and path.stat().st_size > 0
        print(str(path)); print(sha(path.read_bytes()))


if __name__ == '__main__':
    main()
