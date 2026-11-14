"""Write G3 evidence and answer-first handoff for PR 5968, 2026-11-14.

Inputs: local Git history, retained issue JSON and pytest logs in .temp/g3-evidence.
Outputs: verification.json there and the lead-assigned handoff. No GitHub calls.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[2]
evidence = root / '.temp/g3-evidence'
handoff = root.parent / ('codex-development-efficiency-20261111/notes/'
    'development_efficiency_20261111/handoffs/codex-pr5968-shared-fixes-20261114.md')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


protected = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
    'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
    'src/data_sheets_schema/native_controller_sources_v1.json',
    'src/data_sheets_schema/native_controller_sources_v2.json']
for manifest in protected[-2:]:
    protected.extend(row['path'] for row in json.loads((root / manifest).read_text())['modules'].values())
assert not git('diff', 'f8604be5a', '--', *sorted(set(protected)))
history = git('log', 'f8604be5a..HEAD', '--format=%H %s').splitlines()
issues = (6205, 6206, 6212, 6213, 6214, 6222, 6223)
for issue in issues:
    assert json.loads((evidence / f'issue-{issue}.json').read_text())['body']
logs = ('tests-focused-final.txt', 'tests-6205-followup.txt', 'tests-preloading-advance.txt')
summaries = {}
for name in logs:
    raw = (evidence / name).read_text()
    matches = [line for line in raw.splitlines() if re.search(r'\b\d+ passed\b', line)]
    assert matches and not re.search(r'\b\d+ (failed|error|errors)\b', matches[-1]), name
    summaries[name] = matches[-1].strip('= ')
blocked = ('tests-live-diagnosis.txt', 'tests-results-diagnosis.txt', 'tests-permissions-diagnosis.txt')
for name in blocked:
    assert 'neutral roots overlap authority' in (evidence / name).read_text(), name
subprocess.run(['git', 'apply', '--check', '--unidiff-zero', 'notes/pr5968_g3/6214-review-only.patch'],
               cwd=root, check=True)
metadata = {'head': git('rev-parse', 'HEAD'), 'commits': history, 'tests': summaries,
    'review_only_patch_check': 'git apply --check --unidiff-zero passed; patch not applied',
    'protected_unchanged': sorted(set(protected)),
    'logs': {name: hashlib.sha256((evidence / name).read_bytes()).hexdigest() for name in (*logs, *blocked)}}
(evidence / 'verification.json').write_text(json.dumps(metadata, indent=2) + '\n')
details = {
    6205: 'Fixed. Relative and quoted stage paths reach the restrictive overlay in live and saved routing. '
          'Routing conservatively inspects lexical words; ordinary admission still uses the frozen shell grammar.',
    6206: 'Fixed. Initial helper identities require the complete digest roster. Live sealing compares captured '
          'bytes before publication; saved phase replay repeats the comparison against the settled helper result.',
    6212: 'Fixed. A directory-sync exception after linking preserves the final evidence bytes, removes the '
          'redundant staging link, attempts directory synchronization, and rethrows the original failure.',
    6213: 'Fixed. A repeated complete Read of the same request pin keeps the first delivery observation '
          'even after the journal changes; the duplicate-authority refusal remains intact.',
    6214: 'Not fixed; owner policy decision required. Recommend fatal refusals, matching current saved acceptance. '
          'The committed review-only patch changes both misleading text copies but is NOT applied. '
          'It is only the model-text part of the proposal: live termination at the first denied command or file '
          'effect, with a specific retained reason and end-to-end denial tests, still needs lead-owned implementation. '
          'Do not apply the text patch alone as a complete fix.',
    6222: 'Fixed. Removed the unused alternate trace validator. The pre-edit search included hidden and ignored '
          'files under src, tests and scripts and found only its definition.',
    6223: 'Fixed. Observation staging now uses a physical sibling directory; failed bytes remain available '
          'without occupying or poisoning the closed observation ordinal namespace.',
}
lines = ['Fixed: 6205, 6206, 6212, 6213, 6222, 6223. Not fixed: 6214; review-only proposal retained for the lead and owner.',
    '', 'G3 only. All implementation and proposal work is committed locally. No push, GitHub write, '
    'provider call, native binary invocation, pin rotation, or protected-file change was made.',
    '', 'Head: ' + metadata['head'], '', 'Per-issue disposition:']
for issue in issues:
    commits = [row for row in history if f'#{issue}:' in row]
    assert commits, issue
    lines += ['', f'- {issue}: {details[issue]}', '  Commits: ' + '; '.join(commits)]
    test_files, log = {
        6205: ('test_native_shared_effects.py', 'tests-6205-followup.txt'),
        6206: ('test_native_shared_seal_identity.py, test_native_shared_phase.py, test_native_shared_initial_receipts.py', 'tests-focused-final.txt'),
        6212: ('test_native_shared_callback_io.py', 'tests-focused-final.txt'),
        6213: ('test_native_shared_read_repeat.py, test_native_shared_capture_integration.py', 'tests-focused-final.txt'),
        6222: ('test_native_shared_saved_advance.py, test_native_shared_callback_preloading.py', 'tests-preloading-advance.txt'),
        6223: ('test_native_shared_callback_io.py', 'tests-focused-final.txt'),
    }.get(issue, (None, None))
    if test_files:
        test_paths = [root / 'tests' / name for name in test_files.split(', ')]
        assert all(path.is_file() for path in test_paths)
        lines += ['  Proving tests: ' + ', '.join(str(path) for path in test_paths)
                  + '; included in run: ' + summaries[log] + '.']
    else:
        lines += ['  Evidence: static trace confirmed both misleading classifier messages and fatal saved denial accounting. '
                  'git apply --check --unidiff-zero passes for the unapplied proposal; no denial-policy fix is claimed.']
lines += ['', 'Validation:', '']
for name, summary in summaries.items():
    lines += [f'- {summary}. Saved output: {evidence / name}']
lines += ['', 'Passing runs cover callback I/O and preloading, effects, seal identity, phase, initial receipts, '
    'repeat reads, capture integration and split boundaries, saved advances, observations, and publication. '
    'The follow-up run covers the final shell-alias changes.',
    '', 'Blocked checks: live-capture, saved-results and permission test files stop at fixture setup with '
    'native shared permission: neutral roots overlap authority. The assignment requires basetemp inside '
    'the worktree, but these fixtures put their neutral probe under basetemp and production admission '
    'correctly rejects overlap with repository authority. Each file was attempted with stop-on-first-failure '
    'and the refusal was preserved. The lead must authorize an external scratch location to complete these '
    'checks; no production check or test assertion was relaxed.',
    *('- Saved setup traceback: ' + str(evidence / name) for name in blocked),
    '', 'All pytest runs used PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=$PWD/src and '
    '/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest, '
    'with separate basetemp directories under this worktree .temp. No xdist workers were used.',
    '', 'Earlier iteration failures are retained: tests-6212.txt failed committed-source identity checks while '
    'edits were uncommitted; tests-6213.txt exposed a missing fixture import in the new regression. '
    'Both were corrected and the focused committed-tree runs supersede them. The initial broad run '
    '(tests-final.txt) was interrupted after repeated fixture setup errors; pytest teardown also reported a '
    'stash KeyError on that interruption. The separate diagnosis logs retain the actual setup causes. '
    'No assertion or production refusal was weakened.',
    '', 'Limits: these are offline synthetic evidence tests. The repeat-read regression uses real joined Read/Write/Read '
    'frames with an advanced journal identity and checks that no duplicate is persisted; it is not a complete live '
    'reload after that exact sequence. Seal tests inject replacement bytes before the first seal read and exercise '
    'the shared saved identity check; they do not claim external host authentication. OS refusal of cleanup itself '
    'or uncatchable termination between link and unlink remains outside the sync-fault guarantee. '
    'Failed staging bytes remain on disk and are not promoted into successful observation evidence.',
    '', 'Review: a separate read-only diff pass found additional line-continuation and double-leading-slash '
    'spellings under 6205; those are covered by the follow-up commit and regressions. Proposal-diff whitespace '
    'was corrected. These belong to the already assigned issues; no new GitHub issue was written under the no-write instruction.',
    '', 'Review-only patch: ' + str(root / 'notes/pr5968_g3/6214-review-only.patch'),
    'Verification data: ' + str(evidence / 'verification.json'),
    'Pre-edit reference search: ' + str(evidence / 'trace-references.txt'),
    '', 'Helper provenance on this branch:',
    '- ' + str(root / 'scripts/adhoc/remove_unused_native_trace_6222.py'),
    '- ' + str(root / 'scripts/adhoc/propose_native_refusal_text_6214.py'),
    '- ' + str(Path(__file__).resolve()),
    '', 'The .temp evidence and test scratch directory is untracked in this checkout; it was deliberately retained. '
    'The handoff is in the lead-assigned report worktree, outside this branch.', '']
text = '\n'.join(lines)
assert chr(64) not in text
for path in (root / 'notes/pr5968_g3/6214-review-only.patch', evidence / 'verification.json',
             evidence / 'trace-references.txt', *(root / 'scripts/adhoc' / name for name in
             ('remove_unused_native_trace_6222.py', 'propose_native_refusal_text_6214.py', Path(__file__).name))):
    assert path.is_file(), path
handoff.write_text(text)
print(handoff)
print(hashlib.sha256(handoff.read_bytes()).hexdigest())
