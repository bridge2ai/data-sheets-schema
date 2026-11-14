#!/usr/bin/env python3
"""Record refreshed static review of the unapplied 6207 proposal, 2026-11-14.

Inputs: proposal-6207-after-6217, immutable historical review/proposal, current
sources and saved cohort command records. Output: exclusive sibling scratch
review-6207-after-6217.json. No tests, source edits, commits or patch application.
"""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
CURRENT = SCRATCH / 'proposal-6207-after-6217'
HISTORICAL = SCRATCH / 'proposal-6207'
OUTPUT = SCRATCH / 'review-6207-after-6217.json'
PATCH_SHA256 = 'b1174b9a610074f1a1602b0ce0ee1adbe2af26352383d38dc3b6ec505f832850'
PROPOSAL_SHA256 = '484dc412efc7e85ba988f26f04429e5a540ddb60d8343183f8f16f993ce17da7'
ENGINE = 'src/data_sheets_schema/native_execution_orchestration.py'
GUARD = 'src/data_sheets_schema/native_subscription_guard_v2.py'
TRANSPORT = 'notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py'

def pin(path):
    raw = path.read_bytes()
    assert raw, str(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def functions(raw, names):
    tree = ast.parse(raw)
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            assert node.name not in result
            result[node.name] = ast.dump(node, include_attributes=False)
    assert set(result) == set(names)
    return result

def main():
    assert not OUTPUT.exists(), 'review output is exclusive'
    patch_pin, proposal_pin = pin(CURRENT / 'dispatch-boundary.patch'), pin(CURRENT / 'proposal.json')
    assert patch_pin['sha256'] == PATCH_SHA256
    assert proposal_pin['sha256'] == PROPOSAL_SHA256
    proposal = json.loads((CURRENT / 'proposal.json').read_bytes())
    assert proposal['applied'] is proposal['pin_rotation_applied'] is proposal['tests_run'] is False
    assert json.loads((CURRENT / 'apply-check.json').read_bytes())['returncode'] == 0
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    assert head == proposal['head'] == '2070a2116ceb5b1f5dd9a870c803ee3311d298b9'
    source_pins = []
    for entry in proposal['sources']:
        current = pin(ROOT / entry['path'])
        assert current == entry['current']
        assert (ROOT / entry['path']).read_bytes() == (CURRENT / 'original' / entry['path']).read_bytes()
        source_pins.append(current)
    for path in (GUARD, TRANSPORT):
        assert (CURRENT / 'candidate' / path).read_bytes() == (HISTORICAL / 'candidate' / path).read_bytes()
    before = (CURRENT / 'original' / ENGINE).read_text()
    candidate = (CURRENT / 'candidate' / ENGINE).read_text()
    old_candidate = (HISTORICAL / 'candidate' / ENGINE).read_text()
    dispatch_functions = ('_dispatch_memory_authority', 'launch_check', 'dispatch_check')
    assert functions(candidate, dispatch_functions) == functions(old_candidate, dispatch_functions)
    preserved_functions = ('_publication_signal_cutoff', '_publication_subscription', 'read_final')
    assert functions(before, preserved_functions) == functions(candidate, preserved_functions)
    boundary = '                finally:\n                    # Transport/preparation has ended.'
    assert before[before.index(boundary):] == candidate[candidate.index(boundary):]
    previous_review_path = SCRATCH / 'review-6207-final.json'
    previous = json.loads(previous_review_path.read_bytes())
    commands = []
    for path in sorted(SCRATCH.glob('*/command.json')):
        value = json.loads(path.read_bytes())
        assert value['cwd'] == str(ROOT)
        selections = [arg for arg in value['command'] if arg.startswith('tests/')]
        commands.append({
            'cohort': path.parent.name, 'evidence': pin(path), 'head': value['head'],
            'source_relation': 'current proposal source head' if value['head'] == head else 'historical source head',
            'test_selections': [{'selection': arg, 'whole_file': '::' not in arg} for arg in selections],
            'command': value['command'],
        })
    value = {
        'issue': 6207, 'status': 'no-new-findings',
        'review_mode': 'read-only static adversarial review',
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'reviewed_proposal_head': head, 'findings': [],
        'patch': patch_pin, 'proposal': proposal_pin, 'generator': pin(Path(__file__).resolve()),
        'current_sources': source_pins,
        'historical_artifacts': {
            'review': pin(previous_review_path),
            'proposal': pin(HISTORICAL / 'proposal.json'),
            'patch': pin(HISTORICAL / 'dispatch-boundary.patch'),
            'disposition': 'Retained as historical evidence at its recorded head; no historical source or generator pin is recomputed as current.',
        },
        'checks': previous['checks'] + [
            'Refreshed guard and transport candidates exactly equal their previously reviewed candidate bytes.',
            'Refreshed engine dispatch helpers and launch_check are AST-equivalent to the earlier reviewed dispatch design at the new nesting depth.',
            'The complete engine tail from record-only transition through publication and independent readback remains byte-identical to the committed 6217 source.',
            'The 6217 publication cutoff, subscription publication verifier and independent reader retain identical ASTs.',
            'Committed current source bytes equal the fresh proposal original snapshots; no source or manifest pin is rotated.',
        ],
        'remaining_limit': proposal['remaining_limit'],
        'limits': [
            'Static review and syntax/apply checks do not establish runtime acceptance; no proposed candidate was imported, applied or tested.',
            'The final clock observation and Popen remain separate instructions; scheduling or suspension can occur in between.',
            'The historical dependency roster is retained in the prior review. Current saved command selections below are inputs only, not completion or all-files coverage claims.',
            'The 6217 signal cutoff does not make publication atomic against power loss or non-signal I/O errors.',
        ],
        'test_roster': {
            'saved_cohort_commands': commands,
            'historical_dependency_audit': pin(previous_review_path),
            'test_results_claimed_by_this_review': False,
            'new_tests_requested_by_this_review': [],
            'conclusion': 'Actual saved selections are recorded with their source head and file-versus-node distinction; execution results belong to the parent validation artifacts.',
        },
        'actions': {
            'tests_executed': False, 'candidate_executed': False, 'patch_applied': False,
            'source_or_tests_edited': False, 'commits_created': False,
        },
    }
    raw = (json.dumps(value, indent=2) + '\n').replace(chr(64), '\\u0040')
    assert chr(64) not in raw
    with OUTPUT.open('x') as stream:
        stream.write(raw)
    assert OUTPUT.read_text() == raw
    print(json.dumps(pin(OUTPUT)))

if __name__ == '__main__':
    main()
