"""Report #6015/#6016 from local Git and saved tests, 2026-11-12.

Inputs: owned branch heads, saved isolated test results and prior handoff.
Outputs: updated report-worktree handoff Markdown/JSON; no remote operations.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
R = E / 'codex-development-efficiency-20261111'
S = E / 'scratch-h3-failure-record-20261112'
H = R / 'notes/development_efficiency_20261111/handoffs/codex-h3-failure-record-and-retention-20261112'
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json')


def git(tree, *args):
    return subprocess.check_output(['git', '-C', str(tree), *args])


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    branches = {}
    for name in ('launch-sequence-hardening', 'failure-record', 'incomplete-capture-retention'):
        tree = E / ('codex-native-' + name + '-20261112')
        protected = {path: (tree / path).read_bytes() == git(tree, 'show',
            '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1:' + path) for path in PROTECTED}
        guard = 'src/data_sheets_schema/native_subscription_guard.py'
        same_guard = (tree / guard).read_bytes() == git(tree, 'show', 'c1ad9baa1:' + guard)
        assert all(protected.values()) and same_guard
        branches[name] = {'head': git(tree, 'rev-parse', 'HEAD').decode().strip(),
            'branch': git(tree, 'branch', '--show-current').decode().strip(),
            'status': git(tree, 'status', '--porcelain').decode(),
            'protected_equal_main': protected, 'guard_v1_unchanged': same_guard,
            'followup_commits': git(tree, 'log', '--format=%H %s', '--grep=#601[56]',
                                   'c1ad9baa1..HEAD').decode().splitlines(),
            'diagnostic_carry_message': git(tree, 'log', '-1', '--format=%B', '--grep=#6015',
                                           'c1ad9baa1..HEAD').decode()}
        if name != 'launch-sequence-hardening':
            assert not branches[name]['status'], 'repair branch must be clean: ' + name
    cohorts = []
    for directory in sorted((S / 'tests').glob('review-60*')):
        result = directory / 'outcome.json'
        xml = directory / 'pytest.xml'
        if not result.exists() or not xml.exists():
            raise ValueError('incomplete test evidence: ' + str(directory))
        cases = ET.parse(xml).getroot().findall('.//testcase')
        cohorts.append({'name': directory.name, 'cases': len(cases),
            'failures': sum(row.find('failure') is not None for row in cases),
            'errors': sum(row.find('error') is not None for row in cases),
            'skipped': sum(row.find('skipped') is not None for row in cases),
            'outcome': json.loads(result.read_bytes()),
            'pins': [pin(result), pin(xml), pin(directory / 'pytest.log')]})
    compositions = []
    for directory in sorted(S.glob('review-60*')):
        if directory.is_dir() and (directory / 'composition.json').exists():
            compositions.append({'composition': pin(directory / 'composition.json'),
                                 'restoration': pin(directory / 'config-restoration.json')})
    first = branches['failure-record']['head']
    second = branches['incomplete-capture-retention']['head']
    tested_sources = {}
    for name, cohort in (('failure-record', 'review-6015-whole'),
                         ('incomplete-capture-retention', 'review-6016-whole')):
        tree = E / ('codex-native-' + name + '-20261112')
        tested = Path(json.loads((S / 'tests' / cohort / 'plan.json').read_bytes())['source_root'])
        paths = set(git(tree, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').decode().splitlines())
        paths.add('src/data_sheets_schema/native_execution_orchestration.py')
        for path in sorted(paths):
            if path.startswith(('src/', 'tests/')):
                assert (tree / path).read_bytes() == (tested / path).read_bytes(), path
                tested_sources[str(tree / path)] = pin(tested / path)
    summary = f'''# Failure-record and retention review follow-up

Issue 6015 repair: {first}. Issue 6016 repair: {second}.

Diagnostic readback now cross-checks lifecycle membership and hashes with diagnostic pins, then applies the ordinary reader's byte-based runtime-observation, selected-runtime, cleanup-policy, cleanup-outcome and gate consistency checks. Publication pins already-consumed identity, lifecycle and captured bytes. If a later disk read differs or fails, the pin retains the consumed hash and records changed_after_consumption explicitly. Readback refuses while the file differs; restoring the original bytes permits exact readback without erasing the recorded change.

Incomplete capture now verifies optional artifacts separately. An unstable artifact becomes an omission with its exception reason; rebuilding the snapshot removes its member, raw bytes, aliases, metadata and roles. Stable records and streams remain available for projection and publication. Successful capture keeps its strict all-or-nothing verification.

## Saved test results

Counts below come from saved JUnit files. Cohorts overlap and are not a distinct-test total. Public-path tests use the established isolated private four-postimage composition; branch protected files remain main-identical. The first uncomposed canary failed in fixture setup because main RunSpec lacks native_shared_generation_version; it did not reach the repair. Its log is retained.

'''
    for row in cohorts:
        summary += (f"- {row['name']}: {row['cases']} cases, {row['failures']} failures, "
                    f"{row['errors']} errors, {row['skipped']} skipped; runner exit "
                    f"{row['outcome']['returncode']}.\n")
    summary += '''
The public diagnostic regressions cover publication-time cleanup mutation, rehashed lifecycle hash/assessment/gate contradictions, removed diagnostic discriminator, deleted pinned evidence and symlink replacement. The public retention regression changes full after its initial read, then requires the unchanged core and all streams, an explicit full omission, clean catalogs and exact readback. Separate cases cover removal and symlink replacement. The final-floor public test injects a failed final_receipts phase outcome at the transport seam and exercises actual public finalization, retention, publication and readback. It does not execute a real receipt helper, native process or provider and does not establish real coverage-floor behavior.

## Reader routing observations

The final file is still opened through the bounded existing reader before fresh registration verification, after closed-envelope and physical-path checks, to select historical diagnostics. Moving full verification ahead of this dispatch is not cost-free: the diagnostic route intentionally remains readable when that validation fails, and repeating the failing validator would require a new exception-routing policy. Ordinary records still require fresh registration verification; removing the diagnostic discriminator is tested and cannot bypass it. No diagnostic can assert completion, acceptance or resumption.

The publication catch still includes ValueError and OSError from both subscription context reconstruction and observation validation. That is intentional failure-evidence retention, not an authenticated claim that one specific runtime validator failed. The stage and exception are historical diagnostics; readback checks consistency and byte identity but does not reproduce or authenticate the claimed cause. This broader route cannot create successful results.

## Integration order and remaining hold

'''
    for name, row in branches.items():
        summary += f"- {row['branch']}: {row['head']}.\n"
    summary += '''
The issue 6015 commit is cherry-picked with its origin recorded onto retention before the issue 6016 commit. The adjacent publication conflict was resolved by retaining both consumed-byte diagnostic pinning and the existing retention manifest/capture-problems fields. Exact branch log mappings and the carry commit message are in the JSON. Integration order remains hardening, failure record, retention, but hardening issues 5992 and 5993 are still unresolved: the prior follow-up stopped for the recorded state-format decision. These branches do not contain those repairs and are not ready for production integration. After the lead settles that design and the hardening repairs pass independent review, carry them before integrating these failure/retention changes. No branch is described here as already containing the missing hardening fixes.

No protected file, guard v1 or registered document kind/version changed. Nothing was pushed or published; no native executable, real probe/capture/reservation, provider or model call occurred. Synthetic test artifacts are isolated under this helper's scratch. Earlier handoff evidence is preserved below and in JSON; its prior acceptance is superseded by this follow-up for issues 6015 and 6016.

'''
    backup = S / 'review-followup-prior-handoff'
    backup.mkdir(exist_ok=False)
    for suffix in ('.md', '.json'):
        (backup / ('handoff' + suffix)).write_bytes(H.with_suffix(suffix).read_bytes())
    prior = json.loads((backup / 'handoff.json').read_bytes())
    result = {'issue_6015_commit': first, 'issue_6016_commit': second,
        'status': 'repairs-complete-pending-independent-review', 'branches': branches,
        'cohorts': cohorts, 'compositions': compositions, 'tested_sources': tested_sources,
        'hardening_5992_5993_unresolved': True,
        'prior_handoff': prior,
        'prior_handoff_files': [pin(backup / ('handoff' + suffix)) for suffix in ('.md', '.json')],
        'summary_markdown': summary}
    md = summary + '\n## Historical handoff\n\n' + (backup / 'handoff.md').read_text()
    js = json.dumps(result, indent=2) + '\n'
    assert '@' not in md and '@' not in js
    H.with_suffix('.md').write_text(md)
    H.with_suffix('.json').write_text(js)
    for suffix in ('.md', '.json'):
        print(json.dumps(pin(H.with_suffix(suffix))))


if __name__ == '__main__':
    main()
