#!/usr/bin/env python3
"""Record the static issue-6207 proposal review and G2 test roster, 2026-11-14.
Inputs: concrete review-only patch/metadata, saved cohort command JSON, and an
ignored/hidden-inclusive lexical test-reference scan. Output: exclusive sibling
scratch review-6207-final.json. No tests, source edits, commits or patch apply.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUTPUT = SCRATCH / 'review-6207-final.json'
PATCH = SCRATCH / 'proposal-6207/dispatch-boundary.patch'
PROPOSAL = SCRATCH / 'proposal-6207/proposal.json'
EXPECTED_PATCH = 'b1c60bb6fcdcdbeba922fe143b8de4b508ffd3847e727ca6613dabe6f42f5513'
EXPECTED_PROPOSAL = '2774110405bc907840cbfd513bac3921caf25380ff9f764907af071f0386eb09'


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    assert raw, str(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def scan(pattern, roots):
    command = ['rg', '-l', '--no-ignore', '--hidden', '--glob', '*.py',
               '--glob', '!**/__pycache__/**', '--glob', '!**/pycache/**', pattern, *roots]
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert result.returncode in (0, 1), result.stderr.decode()
    paths = sorted(set(result.stdout.decode().splitlines()))
    assert all((ROOT / path).is_file() for path in paths)
    return {'command': command, 'cwd': str(ROOT), 'returncode': result.returncode,
            'ignored_and_hidden_files_included': True, 'matched_paths': paths,
            'matched_files': [pin(ROOT / path) for path in paths]}


def main():
    assert not OUTPUT.exists(), 'retain the earlier review; never overwrite it'
    patch_pin, proposal_pin = pin(PATCH), pin(PROPOSAL)
    assert patch_pin['sha256'] == EXPECTED_PATCH
    assert proposal_pin['sha256'] == EXPECTED_PROPOSAL
    proposal = json.loads(PROPOSAL.read_bytes())
    assert proposal['applied'] is False and proposal['tests_run'] is False
    assert proposal['pin_rotation_applied'] is False
    commands, selected = [], set()
    for name in ('sequence-power', 'engine-admission'):
        path = SCRATCH / name / 'command.json'
        command = json.loads(path.read_bytes())
        assert command['cwd'] == str(ROOT)
        paths = [arg.partition('::')[0] for arg in command['command'] if arg.startswith('tests/')]
        assert paths and all((ROOT / path).is_file() for path in paths)
        selected.update(paths)
        commands.append({'cohort': name, 'evidence': pin(path), 'head': command['head'],
                         'selected_test_files': paths, 'command': command['command']})
    direct = scan(r'native_launch_sequence|native_sequence_start|native_host_power|native_execution_orchestration|dispatch_power\(',
                  ['tests', 'notes/matched_cborg_2026-09-13'])
    fixture = scan(r'from tests\.test_native_launch_sequence|from tests import test_native_launch_sequence', ['tests'])
    missing_direct = sorted(set(direct['matched_paths']) - selected)
    missing_fixture = sorted(set(fixture['matched_paths']) - selected)
    assert not missing_direct and not missing_fixture, (missing_direct, missing_fixture)
    value = {
        'issue': 6207, 'status': 'no-new-findings', 'review_mode': 'read-only static adversarial review',
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'reviewed_proposal_head': proposal['head'], 'findings': [],
        'patch': patch_pin, 'proposal': proposal_pin, 'generator': pin(Path(__file__).resolve()),
        'checks': [
            'Concrete patch and metadata hashes match the exact artifact assigned for review.',
            'Profile validation and power probing precede guard consumption; guard consumption precedes activation stage writes.',
            'The final hook runs after admission.armed teardown and before dispatch elapsed-clock sampling, synchronous admission check and Popen.',
            'Final caller and guard authority checks compare detached memory values and use the clock without _fresh, _static, source reconstruction, path resolution or disk I/O.',
            'The guard latches the final-check opportunity before authority or temporal refusal, rejects observations and backward time, and does not permit retry after inputs are restored.',
            'Only successful temporal revalidation replaces dispatched_at. Refusal retains its earlier valid timestamp and the existing immutable consumed marker.',
            'Known final-check refusal becomes a concrete BudgetStop and first-stop reason; no process spawn follows that refusal.',
            'Saved-snapshot shape remains unchanged; the added private guard fields do not alter historical serialized metadata.',
            'Proposal metadata explicitly records applied=false, pin_rotation_applied=false and tests_run=false.',
        ],
        'remaining_limit': proposal['remaining_limit'],
        'limits': [
            'Static review is not executed acceptance: the proposed candidate has not been imported, applied or tested.',
            'The final clock observation and Popen remain separate instructions; scheduling or suspension can occur in between.',
            'The roster audit is lexical direct-reference and shared-fixture coverage, not an exhaustive transitive dependency proof or full-repository test result.',
        ],
        'test_roster': {
            'saved_cohort_commands': commands, 'selected_test_files': sorted(selected),
            'direct_reference_scan': direct, 'shared_fixture_scan': fixture,
            'missing_direct_reference_files': missing_direct, 'missing_shared_fixture_files': missing_fixture,
            'conclusion': 'All test files returned by these ignored/hidden-inclusive scans are selected in the saved G2 cohort commands.',
            'unchanged_adjacent_consumers_not_added': [
                {'file': pin(ROOT / 'tests/test_native_launch_review.py'),
                 'reason': 'Reviewed sequence-byte binding is adjacent; its implementation was unchanged. No new test run requested.'},
                {'file': pin(ROOT / 'tests/test_native_attempt_timing.py'),
                 'reason': 'Consumes unchanged native_host_power.observation_error. No new test run requested.'},
            ],
            'test_results_claimed_by_this_review': False,
        },
        'actions': {'tests_executed': False, 'candidate_executed': False, 'patch_applied': False,
                    'source_or_tests_edited': False, 'commits_created': False},
    }
    raw = (json.dumps(value, indent=2) + '\n').replace(chr(64), '\\u0040')
    assert chr(64) not in raw
    with OUTPUT.open('x') as stream:
        stream.write(raw)
    assert OUTPUT.read_text() == raw
    print(json.dumps(pin(OUTPUT)))


if __name__ == '__main__':
    main()
