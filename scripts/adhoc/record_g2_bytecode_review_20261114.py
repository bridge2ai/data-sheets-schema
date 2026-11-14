#!/usr/bin/env python3
# Preserve BYTECODE-F1 and its pre-fix helper, 2026-11-14. Inputs: reviewed helper
# bytes. Outputs: exclusive immutable snapshot and review-bytecode.json. No
# preservation operation, cache movement, project imports, tests or commits.
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
DEST = OUT / 'bytecode-preservation-verification'
SOURCE = ROOT / 'scripts/adhoc/preserve_g2_source_bytecode_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    assert not DEST.exists() and not (OUT / 'review-bytecode.json').exists()
    assert pin(SOURCE)['sha256'] == '4a30efddba94c294e9bcc0b776d07ca96866131dd902d4f51bb4614623c81b61'
    DEST.mkdir()
    snapshot = DEST / 'before-preserve-helper.py'
    save(snapshot, SOURCE.read_bytes())
    value = {'finding_id': 'G2-REVIEW-BYTECODE-F1', 'priority': 'P3',
        'status': 'confirmed; pending helper repair and verification',
        'impact': 'KeyboardInterrupt after os.rename returns but before moved=True causes the failure ledger to claim rename_completed=false even though the file has moved.',
        'scope': 'Failure-ledger correctness; no content loss or executed preservation operation is claimed.',
        'required_repair': 'Reconcile fresh original/preserved file identities on failure, or mark the location state unknown.',
        'before_helper': pin(snapshot), 'source_name': str(SOURCE),
        'lead_filing_required': True, 'github_write_performed': False,
        'producer': pin(Path(__file__).resolve())}
    target = OUT / 'review-bytecode.json'
    save(target, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'ledger': pin(target), 'before_helper': pin(snapshot)}, indent=2))


if __name__ == '__main__':
    main()
