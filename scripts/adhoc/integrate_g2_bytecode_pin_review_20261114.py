#!/usr/bin/env python3
# Retain REPORT-F3 and refresh reporting proof targets, 2026-11-14.
# Inputs: corrected closure, reporter, retained BYTECODE-F1 reporting proofs.
# Outputs: immutable reporter snapshot/index and bounded reporter ledger edit.
# No project imports, pytest, handoff/closure execution or source/test edits.
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUTPUT = SCRATCH / 'report-bytecode-pin-integration-20261114'
REPORT = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
CLOSURE = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    assert not OUTPUT.exists(), 'retain earlier integration evidence'
    original = REPORT.read_bytes()
    body = original.decode()
    for old, new in (
        ("'review-bytecode.json')", "'review-bytecode.json', 'review-report-f3.json')"),
        ('report-closure-pin-verification-after-bytecode-review/result.json',
         'report-closure-pin-verification-after-bytecode-pin-review/result.json')):
        assert body.count(old) == 1, old
        body = body.replace(old, new)
    ast.parse(body, filename=str(REPORT))
    # Closure ownership is separate; require the coordinated final targets.
    closure = CLOSURE.read_text()
    assert 'report-closure-pin-verification-after-bytecode-pin-review/result.json' in closure
    assert 'report-cohort-discovery-after-bytecode-pin-review/result.json' in closure
    assert 'G2-REVIEW-REPORT-F3' in closure
    ledger = SCRATCH / 'review-report-f3.json'
    assert json.loads(ledger.read_bytes())['finding_id'] == 'G2-REVIEW-REPORT-F3'
    OUTPUT.mkdir()
    snapshot = OUTPUT / 'before-report_g2_launch_fixes_20261114.py'
    save(snapshot, original)
    historical = []
    for name, resolutions in (
        ('report-closure-pin-verification-after-bytecode-review/result.json', {
            'reporter': SCRATCH / 'report-closure-pin-verification-after-bytecode-review/reviewed-report-source.py'}),
        ('report-cohort-discovery-after-bytecode-review/result.json', {
            'reporter': SCRATCH / 'report-cohort-discovery-after-bytecode-review/reviewed-report_g2_launch_fixes_20261114.py',
            'closure': SCRATCH / 'report-cohort-discovery-after-bytecode-review/reviewed-record_g2_final_review_20261114.py'})):
        path = SCRATCH / name
        value = json.loads(path.read_bytes())
        rows = []
        for key, frozen in resolutions.items():
            recorded, actual = value[key], pin(frozen)
            assert all(recorded[field] == actual[field] for field in ('bytes', 'sha256'))
            rows.append({'key': key, 'source_name': recorded['path'], 'snapshot': actual})
        historical.append({'artifact': pin(path), 'source_resolutions': rows})
    assert REPORT.read_bytes() == original
    REPORT.write_text(body)
    assert REPORT.read_bytes() == body.encode()
    index = {'finding_id': 'G2-REVIEW-REPORT-F3',
        'before_helpers': [{'source_name': str(REPORT), 'snapshot': pin(snapshot)}],
        'historical_proofs': historical, 'current_helpers': [pin(REPORT), pin(CLOSURE)],
        'original_review': pin(ledger),
        'previous_integration_history': pin(SCRATCH / 'report-bytecode-integration-20261114/index.json'),
        'producer': pin(Path(__file__).resolve()),
        'scope': 'New current-companion proof targets after explicit nested bytecode evidence validation. Prior ledgers, proofs and immutable sources remain unchanged.'}
    save(OUTPUT / 'index.json', (json.dumps(index, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'index': pin(OUTPUT / 'index.json'), 'helpers': index['current_helpers']}))


if __name__ == '__main__':
    main()
