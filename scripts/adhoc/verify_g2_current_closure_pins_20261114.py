#!/usr/bin/env python3
# Verify current G2 closure proof bindings after F4/auxiliary repair, 2026-11-14.
# Inputs: frozen closure and saved REPORT-F1 through F4/BYTECODE-F1 proofs.
# Output: exclusive current-closure-pins.json in the fresh reporting proof dir.
# Calls standalone read-only checks only; no final closure, pytest or project import.
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
TARGET = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'
OUT = SCRATCH / 'report-closure-pin-verification-after-f4-reuse-auxiliary/current-closure-pins.json'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    assert OUT.parent.is_dir() and not OUT.exists()
    module = runpy.run_path(str(TARGET))
    rows = []
    for identity, name in (
        ('G2-REVIEW-REPORT-F1', 'close_report'),
        ('G2-REVIEW-REPORT-F2', 'close_report_discovery'),
        ('G2-REVIEW-REPORT-F3', 'close_bytecode_pins'),
        ('G2-REVIEW-REPORT-F4', 'close_auxiliary_discovery'),
        ('G2-REVIEW-BYTECODE-F1', 'close_bytecode')):
        row, details = module['close'](identity, module[name])
        assert row['status'] == 'verified', row
        rows.append({'result': row, 'details': details})
    result = {'status': 'verified', 'closure': pin(TARGET), 'producer': pin(Path(__file__).resolve()),
        'checks': rows, 'passed': len(rows), 'failed': 0,
        'scope': 'Actual standalone current closure entrypoints consume the saved proof pins. No project tests, source edits or final closure generation.'}
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    with OUT.open('xb') as stream:
        stream.write(raw)
    assert OUT.read_bytes() == raw
    print(json.dumps({'output': pin(OUT), 'passed': len(rows), 'failed': 0}))


if __name__ == '__main__':
    main()
