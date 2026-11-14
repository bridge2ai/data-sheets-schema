#!/usr/bin/env python3
"""Resume held local validation after failure classification, issues 6197/6198.
Inputs: fixed7 cleanup receipt, hold and refused-launch log. Outputs: archived
hold/log and resume receipt; no active process is interrupted. 2026-11-13.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

BASE = Path.home() / 'agent-work/data-sheets-schema/helper2-integration-fixes-20261113'


def pin(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    receipt = BASE / 'tests/fixed7-focused/outcome.json'
    outcome = json.loads(receipt.read_bytes())
    assert outcome['cleanup_verified'] and not outcome['observed_surviving_pids']
    moves = [('fixed7.hold.json', 'fixed7-hold-released.json'),
             ('fixed7-dependents-runner.log', 'fixed7-dependents-held-runner.log')]
    for old, new in moves:
        assert (BASE / old).is_file() and not (BASE / new).exists()
    assert not (BASE / 'tests/fixed7-dependents').exists()
    out = BASE / 'fixed7-resume.json'
    assert not out.exists()
    records = []
    for old, new in moves:
        before = pin(BASE / old)
        (BASE / old).rename(BASE / new)
        after = pin(BASE / new)
        assert before['sha256'] == after['sha256']
        records.append({'before': before, 'after': after})
    result = {'at': datetime.now(timezone.utc).isoformat(), 'cleanup_receipt': pin(receipt),
              'moves': records, 'source_changes': False, 'active_process_interrupted': False,
              'reason': 'Two freshness refusals precede intended assertions; retry each alone without changing any authority, freshness or deadline check.'}
    with out.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(pin(out)))


if __name__ == '__main__':
    main()
