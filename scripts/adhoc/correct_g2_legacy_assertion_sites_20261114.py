#!/usr/bin/env python3
# Correct authored assertion line references from retained pytest tracebacks.
# Inputs: immutable legacy review ledger/log. Output: v2 ledger, preserving v1.
# PR 5968 / issue 6217 follow-up, 2026-11-14; no source/tests or execution changes.
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    original = SCRATCH / 'review-legacy-component-failures.json'
    record = json.loads(original.read_bytes())
    log_pin = record['artifacts']['pytest.log']['snapshot']
    path = Path(log_pin['path'])
    assert pin(path) == log_pin
    log = path.read_text()
    corrections = []
    for finding in record['findings']:
        site = finding['assertion_site']
        matches = {int(number) for number in re.findall(
            re.escape(site['path']) + r':(\d+): AssertionError', log)}
        line, = matches
        if site['line'] != line:
            corrections.append({'finding_id': finding['finding_id'],
                                'recorded_line': site['line'], 'traceback_line': line})
        site['line'] = line
        site['basis'] = 'actual saved pytest traceback'
    record['line_reference_correction'] = {
        'prior_ledger': pin(original), 'producer': pin(Path(__file__).resolve()),
        'corrections': corrections, 'scope': 'Correct source references only; counts, failures, evidence and dispositions are unchanged.'}
    destination = SCRATCH / 'review-legacy-component-failures-v2.json'
    with destination.open('x') as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps({'ledger': pin(destination), 'corrections': corrections}))


if __name__ == '__main__':
    main()
