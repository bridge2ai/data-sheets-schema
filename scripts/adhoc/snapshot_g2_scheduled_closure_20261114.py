#!/usr/bin/env python3
# Preserve closure before scheduled-runner integration, 2026-11-14.
# Input: current closure. Output: exclusive immutable snapshot/index in S2.
# No tests, project imports, closure execution or source changes.
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114/scheduled-runner-closure-20261114'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    assert not OUT.exists(), 'retain previous snapshot'
    OUT.mkdir()
    source = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'
    snapshot = OUT / 'before-closure.py'
    raw = source.read_bytes()
    with snapshot.open('xb') as stream:
        stream.write(raw)
    assert snapshot.read_bytes() == raw
    record = {'before_closure': pin(snapshot), 'producer': pin(Path(__file__).resolve()),
              'reason': 'Scheduled-runner finding integration; earlier current-helper proofs remain historical.'}
    target = OUT / 'snapshot.json'
    raw = (json.dumps(record, indent=2, sort_keys=True) + '\n').encode()
    with target.open('xb') as stream:
        stream.write(raw)
    assert target.read_bytes() == raw
    print(json.dumps({'snapshot': pin(snapshot), 'record': pin(target)}))


if __name__ == '__main__':
    main()
