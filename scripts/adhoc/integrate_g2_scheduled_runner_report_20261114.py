#!/usr/bin/env python3
# Retain scheduled-runner review in the G2 handoff, 2026-11-14.
# Inputs: frozen reporter and static scheduled-runner correction companion.
# Outputs: immutable before-reporter snapshot and minimal reporter edits.
# No canary, project tests/imports, source edits, final report or commits.
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
TARGET = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
OUT = SCRATCH / 'scheduled-runner-report-20261114'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    assert not OUT.exists(), 'retain prior scheduled-runner report revision'
    companion = SCRATCH / 'scheduled-runner-review-20261114/correction.json'
    value = json.loads(companion.read_bytes())
    assert value['finding_id'] == 'G2-REVIEW-SCHEDULED-RUNNER-F1' and value['runtime_verified'] is False
    before = TARGET.read_bytes()
    source = before.decode()
    edits = (
        ("'review-6217-f4-confirmed.json')",
         "'review-6217-f4-confirmed.json',\n                'scheduled-runner-review-20261114/correction.json')"),
        ('report-closure-pin-verification-after-f4-reuse-auxiliary/result.json',
         'report-closure-pin-verification-after-scheduled-runner/result.json'),
        ("                else 'verified correction; lead filing status retained' if closed",
         "                else 'scheduled canary verified; static correction retained; lead filing required'\n"
         "                    if closed and identity == 'G2-REVIEW-SCHEDULED-RUNNER-F1'\n"
         "                else 'static correction retained; scheduled canary runtime verification pending; lead filing required'\n"
         "                    if identity == 'G2-REVIEW-SCHEDULED-RUNNER-F1'\n"
         "                else 'verified correction; lead filing status retained' if closed"),
    )
    for old, new in edits:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    ast.parse(source, filename=str(TARGET))
    OUT.mkdir()
    snapshot = OUT / 'before-reporter.py'
    save(snapshot, before)
    assert TARGET.read_bytes() == before
    TARGET.write_text(source)
    assert TARGET.read_bytes() == source.encode()
    record = {'finding_id': value['finding_id'], 'before_reporter': pin(snapshot),
        'current_reporter': pin(TARGET), 'static_correction': pin(companion),
        'producer': pin(Path(__file__).resolve()),
        'scope': 'Only the finding roster, current proof target and explicit static/pending-runtime wording changed. A verified closure requires the exact saved scheduled canary; no runtime result is claimed by this producer.'}
    save(OUT / 'revision.json', (json.dumps(record, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'revision': pin(OUT / 'revision.json'), 'reporter': record['current_reporter']}))


if __name__ == '__main__':
    main()
