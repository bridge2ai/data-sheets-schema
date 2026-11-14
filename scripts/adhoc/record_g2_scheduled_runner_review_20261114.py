#!/usr/bin/env python3
# Retain scheduled-runner F1 before correction, 2026-11-14. Inputs: reviewed
# new-driver bytes. Outputs: immutable snapshot and review ledger in S2.
# No driver execution, pytest, source/test edits, report changes or commits.
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
DEST = OUT / 'scheduled-runner-review-20261114'
SOURCE = ROOT / 'scripts/adhoc/run_g2_scheduled_checks_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    assert not DEST.exists() and not (OUT / 'review-scheduled-runner.json').exists()
    assert pin(SOURCE)['sha256'] == '7a52485d3cdc922217985add96bef575db372098d2de6f8fd547d8644edd75dc'
    DEST.mkdir()
    snapshot = DEST / 'before-driver.py'
    save(snapshot, SOURCE.read_bytes())
    value = {'finding_id': 'G2-REVIEW-SCHEDULED-RUNNER-F1', 'priority': 'P2',
        'status': 'confirmed by separate read-only review; correction pending',
        'impact': 'The pre-run dirty worktree check covers src/tests/selected paths only, so uncommitted root conftest.py or pyproject.toml changes can evade the full committed-head canary source comparison and alter batch setup.',
        'required_repair': 'Require git diff --exit-code HEAD over full SOURCE_SCOPE plus selected paths before either canary or batch.',
        'before_helper': pin(snapshot), 'source_name': str(SOURCE),
        'review_scope': 'Separate static review: this single finding, no additional findings; driver never executed.',
        'observed_test_execution_with_dirty_config': False,
        'lead_filing_required': True, 'github_write_performed': False,
        'producer': pin(Path(__file__).resolve())}
    target = OUT / 'review-scheduled-runner.json'
    save(target, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'ledger': pin(target), 'before_helper': pin(snapshot)}, indent=2))


if __name__ == '__main__':
    main()
