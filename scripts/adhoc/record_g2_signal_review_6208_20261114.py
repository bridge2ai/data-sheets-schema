#!/usr/bin/env python3
"""Retain the separate read-only #6208 review before corrections, 2026-11-14.
Inputs: reviewed source/test bytes and installed Python wait/signal source.
Outputs: exclusive scratch snapshots/finding ledger; no tests, signals or edits.
"""
import hashlib
import json
from pathlib import Path
import sysconfig

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    directory = OUT / 'review-6208-before-fixes'
    directory.mkdir(exist_ok=False)
    snapshots = []
    for relative in ('src/data_sheets_schema/native_launch_sequence.py',
                     'tests/test_native_launch_sequence.py',
                     'tests/test_native_launch_sequence_signals.py'):
        source = ROOT / relative
        target = directory / source.name
        target.write_bytes(source.read_bytes())
        snapshots.append({'source': str(source), 'snapshot': pin(target)})
    standard = Path(sysconfig.get_path('stdlib')) / 'subprocess.py'
    lines = standard.read_text().splitlines()
    excerpts = [{'start_line': begin, 'end_line': end, 'source': '\n'.join(lines[begin - 1:end])}
                for begin, end in ((2010, 2021), (2040, 2091), (2210, 2250))]
    findings = [
        {'id': 'G2-REVIEW-6208-F1', 'priority': 'P2',
         'finding': 'Final signal status, reason and list use different observations. A signal between reconciliation and list copying can produce completed with signals and no reason; a signal in the later clock call can be omitted before serialization.',
         'required_fix': 'Define one signal snapshot as the decision cutoff and derive status, reason and signals from that same snapshot; test boundary injections.'},
        {'id': 'G2-REVIEW-6208-F2', 'priority': 'P2',
         'finding': 'The asynchronous handler calls Popen.send_signal while wait may have reaped its PID before setting returncode. Reentrant poll cannot acquire the held wait lock and can leave os.kill targeting a released PID.',
         'required_fix': 'The handler only latches. Forward from ordinary supervisor control between bounded wait polls, without an overall cleanup deadline or forced kill; test the reap-before-returncode boundary without signaling an unrelated process.'},
        {'id': 'G2-REVIEW-6208-F3', 'priority': 'P3',
         'finding': 'The converted pre-existing copied-package witness uses Popen.communicate(timeout) without failure cleanup, allowing a timed-out or interrupted test to leave owned fake jobs alive.',
         'required_fix': 'Retain owned synthetic process cleanup and reap in a finally on failure; verify the witness cleanup path.'},
    ]
    for finding in findings:
        finding.update(status='correction-and-verification-pending', lead_filing_needed=True,
            github_issue_number=None, filing_reason='Helper GitHub writes are prohibited; the lead must file this finding.')
    record = {'issue': 6208, 'review_kind': 'Separate read-only adversarial pass; no tests or source writes in review.',
              'findings': findings, 'reviewed_snapshots': snapshots,
              'python_subprocess': {'evidence': pin(standard), 'excerpts': excerpts}}
    destination = OUT / 'review-6208.json'
    with destination.open('x') as stream:
        stream.write((json.dumps(record, indent=2) + '\n').replace(chr(64), '\\u0040'))
    print(json.dumps(pin(destination)))


if __name__ == '__main__':
    main()
