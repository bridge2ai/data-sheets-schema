#!/usr/bin/env python3
# Preserve REPORT-F4 before narrow auxiliary-discovery repair, 2026-11-14.
# Inputs: current report/closure and completed bytecode-preservation outcome.
# Outputs: immutable snapshots/ledger. Prior partial proofs remain untouched.
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
DEST = OUT / 'report-auxiliary-discovery-verification'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    assert not DEST.exists() and not (OUT / 'review-report-f4.json').exists()
    DEST.mkdir()
    before = []
    for name in ('report_g2_launch_fixes_20261114.py', 'record_g2_final_review_20261114.py'):
        source = ROOT / 'scripts/adhoc' / name
        target = DEST / ('before-' + name)
        save(target, source.read_bytes())
        before.append(pin(target))
    partial = OUT / 'report-cohort-discovery-after-f4-reuse'
    assert partial.is_dir() and not (partial / 'result.json').exists()
    value = {'finding_id': 'G2-REVIEW-REPORT-F4', 'priority': 'P3',
        'status': 'confirmed; bounded helper repair and proof pending',
        'impact': 'The completed source-bytecode outcome-only auxiliary record is classified as invalid pytest evidence, blocking discovery. No report was accepted.',
        'required_repair': 'Recognize only the exact pinned source-bytecode completed outcome as auxiliary, retaining its provenance; unknown outcome-only and pytest-marker records remain invalid.',
        'before_helpers': before, 'auxiliary_outcome': pin(OUT / 'source-bytecode/outcome.json'),
        'partial_proof_preserved': {'directory': str(partial), 'result_written': False,
            'reviewed_sources': [pin(path) for path in sorted(partial.glob('reviewed-*.py'))]},
        'lead_filing_required': True, 'github_write_performed': False,
        'producer': pin(Path(__file__).resolve())}
    target = OUT / 'review-report-f4.json'
    save(target, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'ledger': pin(target), 'before_helpers': before}, indent=2))


if __name__ == '__main__':
    main()
