#!/usr/bin/env python3
# Preserve pre-6217 reporter and reconcile withdrawn F3 history, 2026-11-14.
# Inputs: reporter, old F3 ledger, immutable original engine snapshot.
# Outputs: new scratch snapshot and companion frozen review ledger only.
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    report = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
    before = SCRATCH / 'report-before-6217.py'
    save(before, report.read_bytes())
    original = SCRATCH / 'review-6217-f3-withdrawn.json'
    record = json.loads(original.read_bytes())
    old_pin = record['source_analysis'][0]['source']
    snapshot = SCRATCH / 'proposal-6217-implementation/original/src/data_sheets_schema/native_execution_orchestration.py'
    frozen = pin(snapshot)
    assert all(old_pin[key] == frozen[key] for key in ('bytes', 'sha256'))
    record['source_analysis'][0]['source'] = frozen
    record['original_review_ledger'] = pin(original)
    record['historical_source_resolution'] = {
        'historical_live_path': old_pin['path'], 'recorded_sha256': old_pin['sha256'],
        'immutable_snapshot': frozen,
        'reason': 'The implementation changed the live engine after review. These retained identical bytes are the historical review source, not a current-source claim.'}
    record['reconciliation_producer'] = pin(Path(__file__).resolve())
    destination = SCRATCH / 'review-6217-f3-withdrawn-frozen.json'
    save(destination, (json.dumps(record, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'report_before': pin(before), 'reconciled_review': pin(destination)}))


if __name__ == '__main__':
    main()
