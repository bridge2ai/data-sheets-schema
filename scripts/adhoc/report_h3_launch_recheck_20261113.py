#!/usr/bin/env python3
"""6048/6047, 2026-11-13: update the owned launch-hardening handoff.
Inputs: local repair commits, saved JUnit/outcomes, private candidate rehearsal.
Outputs: archived prior handoff and updated MD/JSON; no external effects.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import argparse

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
W = E / 'codex-native-launch-sequence-hardening-20261112'
R = E / 'codex-development-efficiency-20261111'
S = E / 'scratch-h3-launch-hardening-20261112'
H = R / 'notes/development_efficiency_20261111/handoffs/codex-h3-launch-sequence-hardening-20261112'
OLD = 'c39526da9a01c41f4a168e58d45f2dea4ad10c00'
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
             'src/data_sheets_schema/native_subscription_guard.py')


def git(*args):
    return subprocess.check_output(['git', '-C', str(W), *args]).decode().strip()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--packaging', choices=('pending', 'two-commits', 'followup'), required=True)
    args = parser.parse_args()
    pending = args.packaging == 'pending'
    if not pending:
        assert not git('status', '--porcelain')
    commits = {issue: ', '.join(git('log', '--reverse', '--format=%H', '--grep=' + issue, OLD + '..HEAD').splitlines())
               for issue in ('6048', '6047')}
    assert all(commits.values()) and commits['6048'] != commits['6047']
    assert git('rev-list', '--count', OLD + '..HEAD') == ('3' if args.packaging == 'followup' else '2')
    verified = {}
    for relative in PROTECTED:
        raw = subprocess.check_output(['git', '-C', str(W), 'show', OLD + ':' + relative])
        current = (W / relative).read_bytes()
        assert raw == current
        verified[relative] = {'unchanged': True, 'sha256': hashlib.sha256(current).hexdigest()}
    composition = json.loads((S / 'recheck-composed/composition.json').read_bytes())
    composed = Path(composition['tree'])
    changes = git('diff', '--name-only', OLD, 'HEAD').splitlines()
    exact = []
    for relative in changes:
        assert (W / relative).read_bytes() == (composed / relative).read_bytes()
        exact.append(pin(W / relative))
    cohorts = []
    for name in ('recheck-6048-02', 'recheck-6048-plumbing', 'recheck-6047-01',
                 'recheck-6047-final', 'recheck-composed-final', 'recheck-unspent-before',
                 'recheck-unspent-after', 'recheck-composed-unspent'):
        directory = S / 'tests' / name
        cases = ET.parse(directory / 'pytest.xml').getroot().findall('.//testcase')
        outcome = json.loads((directory / 'outcome.json').read_bytes())
        cohorts.append({'name': name, 'cases': len(cases),
            'failures': sum(row.find('failure') is not None for row in cases),
            'errors': sum(row.find('error') is not None for row in cases),
            'skipped': sum(row.find('skipped') is not None for row in cases),
            'outcome': outcome, 'evidence': [pin(directory / p) for p in ('pytest.xml', 'pytest.log', 'outcome.json')]})
    final = cohorts[-1]
    assert final['outcome']['returncode'] == 0 and final['outcome']['cleanup_verified']
    assert not final['failures'] and not final['errors'] and not final['skipped']
    restoration = json.loads((S / 'recheck-composed/config-restoration.json').read_bytes())
    assert restoration['byte_exact']
    backup = S / 'recheck-prior-handoff'
    if not backup.exists():
        backup.mkdir()
        for suffix in ('.md', '.json'):
            (backup / ('handoff' + suffix)).write_bytes(H.with_suffix(suffix).read_bytes())
    assert pin(backup / 'handoff.md')['sha256'] == '4977253817928799bd3e6cf9c322fb6c64f763da732719a96980534078b25400'
    md = f"""# Launch re-check follow-up: helper 3

Issue 6048: {commits['6048']}.
Issue 6047: {commits['6047']}.

A sequence-dispatched capture now requires the existing current word journal and the exact parent-pinned, current sequence_start event under the capture lock. It opens with create=False and never activates a word on that route. The body now calls data_sheets_schema.native_launch_entry._require_invocation through an absolute local import; no callback or validator is accepted from the sequence namespace.

Saved test counts (overlapping cohorts, not a unique-test total):

| Cohort | Cases | Failures | Errors | Skipped | Exit |
|---|---:|---:|---:|---:|---:|
"""
    for row in cohorts:
        md += f"| {row['name']} | {row['cases']} | {row['failures']} | {row['errors']} | {row['skipped']} | {row['outcome']['returncode']} |\n"
    md += """
The 345-case candidate cohort predates the extra under-lock unspent correction. The two new reservation-race cases fail before that correction; afterward all 158 focused worktree tests and all 26 candidate-composition capture/CLI tests pass. These are separate saved cohorts, not a claim that the entire 345-case cohort was repeated after the one-line correction.

## Issue 6048

The sequence adds its durable start-event path and digest to the capture child's closed invocation pin roster. The child checks those bytes during pin preflight and passes the pin to capture_subscription. Under the existing journal lock, Journal.require_start rechecks current format, current word, validity, refusal state, the event's type and word, and the exact current event path/digest before any capture-slot reservation or execution. A word-only journal, absent start, incorrect pin or later start refuses.

The regression moves the journal aside after the start is durable but immediately before the child acquires the lock. Missing and empty replacement cases refuse, leave retained state byte-identical, and never reach capture reservation or execution. The positive synthetic test verifies that the journal lock remains held through capture dispatch. CLI tests verify that sequence dispatch passes the pin and standalone dispatch omits it.

Standalone explicit capture is unchanged: it may initialize current word state, activates the presented word, and retains the existing three-slot allowance, chronology, validity, unspent-reservation and limits-refusal checks. The owner word-recording step remains the initializer for the sequence route. Tests use invented state and fake peers only.

Read-only review finding H3-LR1: bypassing activation on the new sequence route also bypassed activation's under-lock unspent-generation check. The prepared correction explicitly repeats require_unspent inside the journal lock before either route can reserve a capture. Regression cases create the attempt directory or evidence directory after preflight but before lock acquisition and assert refusal before capture reservation/execution. This finding is recorded locally because GitHub writes are prohibited.

## Issue 6047

The entry no longer injects a validator callback. The body's absolute local import ignores an assigned no-op _entry_invocation, a same-named global validator, and caller-changed package metadata. The trusted entry still consumes the one-use namespace/argument/source/input binding before packet creation or journal access. Tests cover ordinary imports, no-op injection, loaded-A/retained-B and supplied input maps, with zero packet and zero journal effects. The documented module-execution route dispatches through the canonical trusted entry instance so it shares the same invocation registry; both supported module routes pass with fabricated commands.

Rewriting the trusted entry itself or the interpreter remains out of scope, stated in the sequence module documentation string.

## Integration, failures and known limit

The first runner attempt could not start its child sandbox or enumerate macOS processes under the outer tool sandbox. Its saved log says sandbox_apply: Operation not permitted. The approved rerun used the existing network/native-denying child sandbox and process-cleanup monitor.

The first private-tree invocation refused before tests because its composition manifest lacked the runner's ready status, commit field and protected-file hash roster. Those fields were supplied only after checking the private HEAD, clean source diff and all four protected bytes against the published candidate. The initial manifest remains saved beside the completed manifest; no source or assertion was changed for this correction.

The uncomposed hardening branch retains the four protected main-file bytes. Its genuine-registration fixture needs the candidate's approved protected post-images; that setup refusal is retained in the uncomposed cohort above. The private rehearsal first applies the two repair commits onto published candidate 8760de5efe88b5af62e9d77e6335fa7e248017b6, which already contains those approved files, then adds the prepared H3-LR1 correction for the focused rerun. Both patches applied cleanly. All changed source/test files match the current hardening worktree byte for byte. The private tree has no remote, and its temporary CI configuration was restored byte-exactly. This is a scratch test composition, not a carry onto either previously merged branch.

Optional Part 3 was not implemented: no optional branch or tip-format commit was created. Issue 6049 remains the lead-accepted nonblocking limit. Deleting a valid journal suffix or restoring a consistent older state is not detected by the current unanchored journal; no new crash-safety claim is made for a count/tip protocol.

The source remains on codex/native-launch-sequence-hardening-20261112 for lead integration and independent review. The other two branches were not changed. The four protected files and guard v1 are byte-identical to the accepted hardening head. Nothing was pushed or published; no real native binary, probe, capture, reservation, provider or model was called. Synthetic word state stayed in this helper's scratch.
"""
    if pending:
        notice = ('COMMIT PACKAGING PENDING: the two hashes above are provisional and do not contain H3-LR1. '
                  'Do not cherry-pick them as the final repair. The corrected source and regressions are tested but uncommitted. '
                  'The user has been asked whether to rewrite only these two new unpublished commits to retain one commit per issue, '
                  'or preserve them and add a follow-up. No existing history has been rewritten.\n\n')
        md = md.replace('A sequence-dispatched capture now requires', notice + 'A sequence-dispatched capture now requires', 1)
    result = {'status': 'tested-awaiting-commit-packaging-approval' if pending else 'repaired-tested-pending-independent-review',
        'packaging': args.packaging, 'commits_are_final': not pending, 'commits': commits,
        'head': git('rev-parse', 'HEAD'), 'base': OLD, 'branch': git('branch', '--show-current'),
        'cohorts': cohorts, 'protected_and_guard': verified, 'changed_source_pins': exact,
        'composition': pin(S / 'recheck-composed/composition.json'),
        'initial_composition_manifest': pin(S / 'recheck-composed/composition-before-runner-seal.json'),
        'working_correction': pin(S / 'recheck-composed/unspent-followup.patch'),
        'full_cohort_composition': pin(S / 'recheck-composed/composition-before-unspent.json'),
        'configuration_restoration': pin(S / 'recheck-composed/config-restoration.json'),
        'prior_handoff': [pin(backup / ('handoff' + suffix)) for suffix in ('.md', '.json')],
        'optional_6049_implemented': False, 'tail_deletion_detected': False,
        'other_branches_carried': False, 'summary_markdown': md}
    js = json.dumps(result, indent=2) + '\n'
    assert '@' not in md and '@' not in js
    H.with_suffix('.md').write_text(md)
    H.with_suffix('.json').write_text(js)
    print(json.dumps({'handoff': pin(H.with_suffix('.md')), 'json': pin(H.with_suffix('.json')), 'commits': commits}))


if __name__ == '__main__':
    main()
