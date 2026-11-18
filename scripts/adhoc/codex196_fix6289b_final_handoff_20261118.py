"""Write the approved F1/F2/F3 continuation handoff for PR 5968, 2026-11-18.

Inputs: final branch, saved checks, current CI analysis and simulation tables.
Outputs: requested external handoff and a final evidence receipt in scratch.
All tables are produced by the referenced capacity-report script from JSON.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def results(path):
    cases = list(ET.parse(path).iter('testcase'))
    return {'cases': len(cases),
            'failed': sum(row.find('failure') is not None for row in cases),
            'errors': sum(row.find('error') is not None for row in cases),
            'skipped': sum(row.find('skipped') is not None for row in cases)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--capacity-markdown', type=Path, required=True)
    parser.add_argument('--capacity-json', type=Path, required=True)
    parser.add_argument('--collection-proof', type=Path, required=True)
    parser.add_argument('--handoff', type=Path, required=True)
    args = parser.parse_args()
    root, scratch = args.root, args.scratch
    def git(*words):
        return subprocess.check_output(['git', *words], cwd=root, text=True).strip()
    assert not git('status', '--porcelain'), 'final branch must be clean'
    head = git('rev-parse', 'HEAD')
    focused = results(scratch / 'focused-junit.xml')
    refreshed = results(scratch / 'refreshed-estimates-junit.xml')
    for row in (focused, refreshed):
        assert row['cases'] and not any(row[key] for key in ('failed', 'errors', 'skipped')), row
    focused_summary = json.loads((scratch / 'focused-summary.json').read_bytes())
    assert focused_summary['overall_returncode'] == 0
    assert focused_summary['post_cleanliness']['passed']
    chain = json.loads((scratch / 'pin-chain-final.json').read_bytes())
    assert chain['head_commit'] == head and not chain['failures'] and chain['protected_files_ok']
    source = json.loads((scratch / 'final-source-audit.json').read_bytes())
    assert source['head'] == head and source['source_tree_unchanged']
    application = json.loads((scratch / 'f3-application.json').read_bytes())
    assert pin(root / 'utils/ci_scheduling_estimates.json') == application['after']
    full_log = (scratch / 'full-collection.log').read_text()
    match = re.search(r'(\d+) tests collected, (\d+) errors', full_log)
    assert match and int(match[2]) == 3
    expected_errors = {'tests/test_fairscape_integration/test_canonical_routes.py',
        'tests/test_fairscape_integration/test_forward_typed_projections.py',
        'tests/test_fairscape_integration/test_nested_dataset_readback.py'}
    assert set(re.findall(r'^ERROR (tests/\S+)', full_log, re.M)) == expected_errors
    capacity = json.loads(args.capacity_json.read_bytes())
    branch = git('branch', '--show-current')
    commits = git('log', '--reverse', '--format=%H %s', '7b9497fc1..HEAD').splitlines()
    f1 = next(row.split()[0] for row in commits if 'Separate ordinary scheduling' in row)
    f2 = next(row.split()[0] for row in commits if 'Normalize denial helper' in row)
    sources = [scratch / name for name in ('f1-canary-junit.xml', 'f1-canary-summary.json',
        'focused-junit.xml', 'focused-summary.json', 'full-collection.log',
        'full-collection-summary.json', 'refreshed-estimates-junit.xml',
        'refreshed-estimates-summary.json', 'pin-chain-final.json', 'final-source-audit.json',
        'f3-application.json', 'cleanup.tsv', 'cleanup.md', 'f1-f2-audit.json')]
    sources += [args.capacity_markdown, args.capacity_json, args.collection_proof]
    receipt_path = scratch / 'final-handoff-receipt.json'
    receipt = {'head': head, 'branch': branch, 'commits': commits,
        'focused': focused, 'post_refresh': refreshed, 'local_collected': int(match[1]),
        'expected_collection_errors': sorted(expected_errors),
        'artifacts': [pin(path) for path in sources], 'writer': pin(Path(__file__))}
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    commit_lines = '\n'.join('- `' + row + '`.' for row in commits)
    helpers = sorted([*root.glob('scripts/adhoc/codex196_fix6289b_*.py'),
                      root / 'scripts/adhoc/codex196_fix6289_simulate_20261118.py'])
    helper_lines = '\n'.join('- `' + str(path) + '`.' for path in helpers)
    capacity_text = args.capacity_markdown.read_text().replace(
        'No source-worktree edits or commits were made by this F3 helper.', '')
    report = f'''# CI failures continuation: F1/F2 fixed; F3 capacity remains unresolved

F1 and F2 are committed locally and the required focused checks pass. F3's estimates are refreshed from the current CI evidence, but whole-file balancing cannot establish the requested ten-minute margin. Four separate case lanes are the smallest proposed structural response to the long unfinished cases; the unresolved small-test stalls and missing successful Read runtime prevent a capacity guarantee even for that alternative. The lane proposal is not implemented.

Final head: `{head}` on `{branch}`, in `{root}`. The branch is clean and based on the assigned `7b9497fc17672e9ede94cebdd556085c8119f3cc`. Commits:

{commit_lines}

## F1

Commit `{f1}` restores the measured timing file byte-for-byte, keeps the historical timing test unchanged, and loads base-bound scheduling estimates only for the explicit ordinary lane using this repository's measured timing path. The workflow is unchanged, following the lead's preference. Dedicated lanes still reject timing options; custom timing files and unlaned sharding retain their standalone behavior. Missing estimates, stale base bytes, duplicate keys, invalid durations and malformed paths refuse before execution.

The original failing invariant now passes. The migration audit proves that separating the initial estimates preserved every prior effective weight; F3 then deliberately refreshed them. Read-only adversarial review found no issue in the loader and validation changes. Measured-file SHA-256: `{application['base']['sha256']}`.

F1 summary: fixed and committed; unchanged historical tests and scheduling validation pass.

## F2

Commit `{f2}` imports the existing helper-environment fixture into all five denial modules and replaces only the opaque runtime assertion message with focused JSON diagnostics. The fixture aligns preparation with the real helper interpreter paths before the environment manifest is captured. A static AST audit verifies that every assertion condition and all non-import, non-message test logic remain unchanged.

The existing helper-environment regressions pass, and all changed denial modules collect. No full denial lifecycle was rerun. The fixture omission is established; its causal role in the prior CI failure remains unconfirmed until the next run exposes the first stop and failing gate rows. The earlier source diagnosis is preserved in `{scratch / 'handoff-before-lead-decision.md'}`.

F2 summary: approved test-only correction committed; isolation checks and collection pass; CI root-cause confirmation remains pending.

## F3

The current-run refresh applies {application['estimate_count']} estimates relative to the unchanged measured base. The committed document retains input hashes and provenance, explicitly labels failed paths and censored occupied intervals, and excludes the three unresolved tiny final-case stalls from intrinsic scheduling estimates. The script-produced tables below include their separate sensitivity. GitHub-supplied ZIP digests were verified; XML hashes were computed locally.

{capacity_text}

F3 summary: exact unfinished inventory and corrected estimates committed; the requested capacity margin is not established. The lead must decide on the four-case lane proposal and obtain successful completion and worker-stall evidence before treating either profile as qualified.

## Verification and retained evidence

The focused cohort passed {focused['cases']} tests: `tests/test_ci_timing_update.py`, `tests/test_ci_scheduling_estimates.py`, `tests/test_ci_sharding.py`, `tests/test_ci_shard_initial_load.py`, and `tests/test_native_helper_environment.py`. It included the real nested xdist partition checks with bounded workers. The sidecar refresh received a separate final validation of {refreshed['cases']} test cases after its final bytes were applied. Native lifecycle tests were not run.

Full collection found {match[1]} tests, with exactly the three documented FAIRSCAPE errors caused by the uninitialized submodule. The changed files collect, and the saved collection proof reconciles the new tests with the prior collection plus the unchanged CI-only FAIRSCAPE supplement used by the model. This is not a claim of error-free full local collection.

The committed-head pin-chain check passes with protected files intact. The source audit confirms that `src/`, the protected files, the workflow and the historical timing test were not changed. The lead owns the new D128 refresh and publication. No push, merge or history rewrite occurred.

Timing-invariant canary: `{scratch / 'f1-canary-junit.xml'}`. Focused results: `{scratch / 'focused-junit.xml'}` and `{scratch / 'focused-summary.json'}`. Final estimate validation: `{scratch / 'refreshed-estimates-junit.xml'}`. Pin check: `{scratch / 'pin-chain-final.json'}`. Collection proof: `{args.collection_proof}`. Source audit: `{scratch / 'final-source-audit.json'}`. Complete hash inventory: `{receipt_path}`.

Only completed disposable basetemp trees were removed under the lead's retention instruction. Logs, JUnit, receipts, CI artifacts and cited simulation inputs remain. Cleanup was verified with the Safe Delete skill, with the task-local audit in `{scratch / 'cleanup.tsv'}` and `{scratch / 'cleanup.md'}`. The audit stays in task scratch to respect the assignment's output boundary.

All newly authored helper scripts are committed on this branch; the capacity helpers also remain in the designated report checkout. Committed copies:

{helper_lines}

The focused checks used the existing `run_lane_20261115.py` with the primary interpreter, external scratch, no inherited alarm, and a serial outer pytest. Read-only collection ran in a separate cooperative slot, without executing test bodies. The full logs and runner receipts preserve the exact commands and environment warnings. The primary editable install still points to the primary checkout; these checks used the assigned source path and do not claim native manifest acceptance.
'''
    assert chr(64) not in report
    args.handoff.write_text(report)
    assert args.handoff.stat().st_size > 0
    print('F1/F2 fixed; focused checks pass; F3 estimates refreshed, but capacity margin remains unresolved.')
    print('Head ' + head)
    print(str(args.handoff) + '\nSHA-256 ' + pin(args.handoff)['sha256'])
    print(str(receipt_path) + '\nSHA-256 ' + pin(receipt_path)['sha256'])


if __name__ == '__main__':
    main()
