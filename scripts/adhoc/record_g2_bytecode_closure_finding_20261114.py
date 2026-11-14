#!/usr/bin/env python3
# Preserve REPORT-F3 before correcting bytecode closure pins, 2026-11-14.
# Inputs: current closure helper. Outputs: immutable pre-fix snapshot and
# review-report-f3.json. No final closure, project imports, tests or commits.
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
DEST = OUT / 'bytecode-closure-pin-verification'
SOURCE = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    assert not DEST.exists() and not (OUT / 'review-report-f3.json').exists()
    DEST.mkdir()
    snapshot = DEST / 'before-closure.py'
    save(snapshot, SOURCE.read_bytes())
    value = {'finding_id': 'G2-REVIEW-REPORT-F3', 'priority': 'P3',
        'status': 'confirmed; pending helper repair and verification',
        'impact': 'close_bytecode neither validates nor exports the six case outcome/retained pins and two original-counterexample outcome/preserved pins; changed or missing nested artifacts do not refuse bytecode closure.',
        'scope': 'Closure evidence integrity. No observed project-test false acceptance or actual cache preservation is claimed.',
        'required_repair': 'Check and export all eight nested artifact pins and verify the actual close_bytecode entrypoint accepts valid evidence and refuses changed/missing artifacts.',
        'before_closure': pin(snapshot), 'source_name': str(SOURCE),
        'lead_filing_required': True, 'github_write_performed': False,
        'producer': pin(Path(__file__).resolve())}
    target = OUT / 'review-report-f3.json'
    save(target, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'ledger': pin(target), 'before_closure': pin(snapshot)}, indent=2))


if __name__ == '__main__':
    main()
