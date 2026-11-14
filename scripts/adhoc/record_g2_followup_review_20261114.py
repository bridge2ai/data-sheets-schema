#!/usr/bin/env python3
"""Retain G2 review findings for power ordering and proposal accuracy.
Inputs: reviewed #6218 source and #6217 proposal. Outputs: immutable scratch
snapshots and finding ledger, 2026-11-14. No tests or production source edits.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    directory = OUT / 'review-followups-before-fixes'
    directory.mkdir(exist_ok=False)
    snapshots = []
    for source in (ROOT / 'src/data_sheets_schema/native_execution_orchestration.py',
                   ROOT / 'src/data_sheets_schema/native_shared_capture_orchestration.py',
                   OUT / 'issue-6217-proposal.json', OUT / 'issue-6217-proposal.md'):
        target = directory / source.name
        target.write_bytes(source.read_bytes())
        snapshots.append({'source': str(source), 'snapshot': pin(target)})
    findings = [
        {'id': 'G2-REVIEW-6218-F1', 'priority': 'P2',
         'finding': 'The initial power fix moved stage activation before the consuming guard refusal, permitting genesis/capture writes before a changed or expired consumed guard is rejected.',
         'required_fix': 'Put profile/power before the consuming guard check and preserve activation after that guard; test changed consumed guard before verify_launch and absent activation artifacts. Keep the actual-dispatch temporal gap explicit under issue 6207.'},
        {'id': 'G2-REVIEW-6217-F1', 'priority': 'P3',
         'finding': 'The proposal overstated the need for a new versioned finalization-signal field. Existing first_stop plus its failed gate can retain a late interruption without rewriting consumed keep-awake bytes.',
         'required_fix': 'Narrow the unresolved choice to the final decision cutoff and later-signal policy; treat a structured signal field as optional.'},
    ]
    for row in findings:
        row.update(status='correction-and-verification-pending', lead_filing_needed=True,
                   github_issue_number=None, filing_reason='Helper GitHub writes are prohibited; lead filing is required.')
    target = OUT / 'review-followups.json'
    with target.open('x') as stream:
        stream.write((json.dumps({'findings': findings, 'reviewed_snapshots': snapshots}, indent=2)
                      + '\n').replace(chr(64), '\\u0040'))
    print(json.dumps(pin(target)))


if __name__ == '__main__':
    main()
