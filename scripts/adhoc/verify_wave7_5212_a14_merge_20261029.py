#!/usr/bin/env python3
# Purpose: verify the protected automatic union and sole test resolution for Wave7 integration.
# Inputs: exact Git parents/base and the current isolated packet; output: JSON byte/ancestry proof.
# Refs #5212 / #5162; 2026-10-29. Reads protected files; never edits them or runs tests.
"""A14's complete source plus D41's single routing-code entry, without normalization."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = 'cd07f2a3738e146eeaa30ae86d35d3161eb3413b'
LEFT = '39d6c33b5abdcd05bd8ec830211adb9caf013acb'
RIGHT = '8b885ee68262474275316755c3fc55dc05517dcb'
MERGE = 'c119d58ddf18cc7c4a77bc8293d09335ab24f921'
PROTECTED = 'src/data_sheets_schema/shared_generation.py'
TEST = 'tests/test_source_heading_runtime_api.py'
ANCHOR = b'                "src/data_sheets_schema/usage_ledger.py",\n'
LINE = b'                "src/data_sheets_schema/latch_journal.py",\n'
MONITOR = (b'\n\n# D57: retain externally observed journal heads across fixture resumes.\n'
           b'pytestmark = pytest.mark.usefixtures("journal_launch_monitor")\n')


def git(*args):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    return subprocess.run(['git', '--no-replace-objects', '-C', str(ROOT), *args],
                          check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env).stdout


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify():
    assert git('merge-base', LEFT, RIGHT).decode().strip() == BASE
    assert git('rev-parse', MERGE + '^1').decode().strip() == LEFT
    assert git('rev-parse', MERGE + '^2').decode().strip() == RIGHT
    git('merge-base', '--is-ancestor', MERGE, 'HEAD')
    base, left, right = (git('show', ref + ':' + PROTECTED) for ref in (BASE, LEFT, RIGHT))
    actual = (ROOT / PROTECTED).read_bytes()
    assert base.count(ANCHOR) == right.count(ANCHOR) == 1
    assert LINE not in base and LINE not in right
    assert left == base.replace(ANCHOR, ANCHOR + LINE, 1)
    expected = right.replace(ANCHOR, ANCHOR + LINE, 1)
    assert actual == expected and actual.count(LINE) == 1
    assert actual.replace(LINE, b'', 1) == right
    assert actual == git('show', MERGE + ':' + PROTECTED)
    assert actual == git('show', ':' + PROTECTED)
    assert (ROOT / TEST).read_bytes() == git('show', RIGHT + ':' + TEST) + MONITOR
    assert (ROOT / TEST).read_bytes() == git('show', MERGE + ':' + TEST)
    assert (ROOT / TEST).read_bytes().count(MONITOR) == 1
    canonical = 'src/download/prompts/canonical_hashes.yaml'
    assert (ROOT / canonical).read_bytes() == git('show', RIGHT + ':' + canonical)
    assert not git('diff', '--name-only', LEFT, MERGE, '--', 'data/ATTIC/',
                   'data/d4d_concatenated/', 'notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md')
    return {'format': 'wave7_5212_a14_exact_union_v1', 'base': BASE, 'left': LEFT,
        'right': RIGHT, 'merge': MERGE, 'verification_head': git('rev-parse', 'HEAD').decode().strip(),
        'protected_path': PROTECTED,
        'protected_sources': {label: {'sha256': sha(raw), 'bytes': len(raw)}
                              for label, raw in (('base', base), ('left', left), ('right', right), ('merged', actual))},
        'left_change': 'Exactly one latch_journal.py line added after usage_ledger.py in ROUTING_CODE.',
        'merged_exact_union': True, 'right_recovered_by_removing_only_left_line': True,
        'protected_worktree_index_and_merge_blob_identical': True,
        'test_resolution': 'Exact A14 file followed by exact D57 module-level journal_launch_monitor marker.',
        'test_sha256': sha((ROOT / TEST).read_bytes()),
        'canonical_hashes_matches_a14_sha256': sha((ROOT / canonical).read_bytes()),
        'run_attic_and_decision_diff_empty': True,
        'source_was_only_auto_merged': 'No helper write operation targets source or tests; Git auto-merge was retained.',
        'scientific_acceptance': 'not_assessed'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof = verify()
    with args.output.open('x') as stream:
        json.dump(proof, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(proof, sort_keys=True))
