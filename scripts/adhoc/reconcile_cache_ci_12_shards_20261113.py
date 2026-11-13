#!/usr/bin/env python3
"""Reconcile the 43 assigned 12-shard cache failures against retained passes.
Inputs saved CI inventory, exact local commits and JUnit evidence; outputs an
answer-first handoff section/JSON with --report. Offline only, 2026-11-13.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

W = Path(__file__).resolve().parents[2]
E = W.parent
R = E / 'codex-development-efficiency-20261111'
H = R / 'notes/development_efficiency_20261111/handoffs/codex-h2-public-path-proof-20261112'
I = H.parent / 'lead-ci-run-43367502045-failures-20261113.json'
B = Path.home() / 'agent-work/data-sheets-schema/helper2-ci-20261113/tests/fixed-cache-final'
Q = E / 'scratch-h2-run-limits-20261113/tests/pair-composed-final'
EXPECTED = {
    'tests/test_native_generation_frontdoor.py': 28,
    'tests/test_native_permission_probe.py': 8,
    'tests/test_native_u4b_probe_sequence.py': 1,
    'tests/test_native_lexical_ancestry.py': 6,
}
REPAIRS = {
    'tests/test_native_generation_frontdoor.py': ['cb572f4a1', '60affb4b5'],
    'tests/test_native_permission_probe.py': ['cb572f4a1', '60affb4b5'],
    'tests/test_native_u4b_probe_sequence.py': ['4bb78e6d4'],
    'tests/test_native_lexical_ancestry.py': ['44aecb06d'],
}


def git(*args):
    return subprocess.check_output(['/usr/bin/git', *args], cwd=W, text=True).strip()


def pin(path):
    return {'path': str(path), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def reconcile():
    inventory = json.loads(I.read_bytes())
    assert inventory['run_id'] == '43367502045'
    published = inventory['head']
    cases = {}
    cohorts = []
    for root in (B, Q):
        status = json.loads((root / 'outcome.json').read_bytes())
        assert status['cleanup_verified'] and not status['observed_surviving_pids']
        plan = json.loads((root / 'plan.json').read_bytes())
        for case in ET.parse(root / 'pytest.xml').iter('testcase'):
            file = case.attrib['classname'].replace('.', '/') + '.py'
            node = file + '::' + case.attrib['name']
            result = next((k for k in ('failure', 'error', 'skipped') if case.find(k) is not None), 'passed')
            cases.setdefault(node, []).append({'result': result, 'cohort': str(root),
                'source_commit': plan['source_commit'], 'source_root': plan['source_root']})
        cohorts.append({'root': str(root), 'plan': plan, 'outcome': status,
                        'files': [pin(root / name) for name in ('pytest.xml', 'pytest.log', 'plan.json', 'outcome.json')]})
    rows = []
    for failure in inventory['failures']:
        if failure['file'] not in EXPECTED:
            continue
        node = failure['file'] + '::' + failure['node']
        passed = [row for row in cases.get(node, []) if row['result'] == 'passed']
        assert passed, 'no retained pass for ' + node
        rows.append({'node': node, 'ci_failure': failure, 'retained_passes': passed,
                     'repair_commits': [git('rev-parse', ref) for ref in REPAIRS[failure['file']]]})
    counts = {file: sum(row['ci_failure']['file'] == file for row in rows) for file in EXPECTED}
    assert counts == EXPECTED and len(rows) == len({row['node'] for row in rows}) == 43
    assert not git('diff', '8760de5ef', published, '--', *EXPECTED)
    assert not git('diff', '8760de5ef', published, '--', 'src/data_sheets_schema/native_helper_cache.py')
    assert not git('diff', 'e079e2f3a', 'HEAD', '--', 'src')
    commits = sorted({commit for row in rows for commit in row['repair_commits']})
    for commit in commits:
        ancestor = subprocess.run(['/usr/bin/git', 'merge-base', '--is-ancestor', commit, published], cwd=W)
        assert ancestor.returncode == 1, 'repair already in published CI head or git check failed'
    return {'run_id': inventory['run_id'], 'published_ci_head': published,
        'inventory': pin(I), 'assigned_cases': len(rows), 'retained_passing_cases': len(rows),
        'counts_by_file': counts, 'cases': rows, 'cohorts': cohorts,
        'repair_commits_absent_from_published_head': commits,
        'cache_branch_head': git('rev-parse', 'HEAD'), 'helper': pin(Path(__file__)),
        'test_files_and_cache_module_unchanged_between_ci_bases': True,
        'production_delta': git('diff', '8760de5ef', published, '--',
            'src/data_sheets_schema/native_shared_registration.py',
            'src/data_sheets_schema/native_shared_permissions.py'),
        'scope': 'Retained local passing evidence; not a new exact-head test run on 7b851213f. The newer production diff adds D4D_RENDER_SPEC to environment construction and its expected field set; cache binding is unchanged. No code or assertion changes needed for this assignment.'}


def report(value):
    assert not git('status', '--porcelain'), 'commit provenance helper before reporting'
    for suffix in ('.md', '.json'):
        backup = H.with_name(H.name + '-pre-ci-12-shards-20261113').with_suffix(suffix)
        with backup.open('xb') as stream:
            stream.write(H.with_suffix(suffix).read_bytes())
    report_path = H.parent / 'codex-h2-ci-12-shards-20261113.json'
    with report_path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True).replace(chr(64), '\\u0040') + '\n')
    data = json.loads(H.with_suffix('.json').read_bytes())
    data['ci_12_shards_reconciliation'] = value
    H.with_suffix('.json').write_text(json.dumps(data, indent=2, sort_keys=True).replace(chr(64), '\\u0040') + '\n')
    lines = ['# Helper 2: 12-shard cache failures already repaired', '',
        'All 43 assigned failures from CI run 43367502045 match retained passing test IDs from the preceding CI-regression work. No further code change is needed. The four affected test files and the helper-cache module are unchanged between the earlier candidate and this CI head; the repair commits are absent from that published head.', '',
        '| File | CI failures matched to passes | Existing repair |', '| --- | ---: | --- |']
    for file, count in value['counts_by_file'].items():
        lines.append('| `' + file + '` | ' + str(count) + ' | ' + ', '.join('`' + ref + '`' for ref in REPAIRS[file]) + ' |')
    lines += ['',
        'Frontdoor and permission probe share saved_case: its config now derives from the declared attempt cache. The probe-sequence helper rebinds config when replacing a runtime. Lexical ancestry declares the required disjoint HOME/cache paths. Production HOME, cache-binding and physical reservation checks, and the assertions under test, remain unchanged.', '',
        'The 28 frontdoor, 8 permission-probe and 6 lexical cases passed in fixed-cache-final. That combined cohort was 141 passed with one unrelated 0.5-second Python-peer startup timeout; the four peer cases passed in a separate unchanged rerun. The bound-probe case passed in its repaired canary and the final 404-pass composition. These are retained results, not a new exact-head run of 7b851213f.', '',
        value['scope'], '',
        'The cache branch now ends at `' + value['cache_branch_head'] + '`; this assignment adds only the reconciliation helper. Nothing published. Prior handoffs and all failures remain retained.', '',
        'Reconciliation: `' + str(report_path) + '`, SHA-256 `' + pin(report_path)['sha256'] + '`.',
        'Updated full JSON SHA-256: `' + pin(H.with_suffix('.json'))['sha256'] + '`.', '', '---', '', H.with_suffix('.md').read_text()]
    text = '\n'.join(lines)
    assert chr(64) not in text
    H.with_suffix('.md').write_text(text)
    for path in (H.with_suffix('.md'), H.with_suffix('.json'), report_path):
        print(json.dumps(pin(path)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    value = reconcile()
    if args.report:
        report(value)
    else:
        print(json.dumps({'counts_by_file': value['counts_by_file'], 'passed': value['retained_passing_cases'], 'repair_commits': value['repair_commits_absent_from_published_head']}))
