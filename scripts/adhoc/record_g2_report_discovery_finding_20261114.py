#!/usr/bin/env python3
# Preserve REPORT-F2 before repair, 2026-11-14. Inputs: current report/closure
# helpers and original/copied cohort evidence. Outputs: immutable snapshots and
# review-report-f2.json in scratch-g2-20261114. No project/test execution.
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
SNAPSHOTS = OUT / 'report-cohort-discovery-20261114'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    ledger = OUT / 'review-report-f2.json'
    assert not SNAPSHOTS.exists() and not ledger.exists(), 'preserve prior evidence'
    SNAPSHOTS.mkdir()
    helpers = []
    for name in ('report_g2_launch_fixes_20261114.py', 'record_g2_final_review_20261114.py'):
        source = ROOT / 'scripts/adhoc' / name
        snapshot = SNAPSHOTS / ('before-' + name)
        save(snapshot, source.read_bytes())
        helpers.append({'source_name': str(source), 'snapshot': pin(snapshot)})
    originals, copies = [], []
    for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log'):
        original = OUT / 'final-components' / name
        copied = OUT / 'legacy-component-failures-20261114' / name
        assert original.read_bytes() == copied.read_bytes(), 'archive differs: ' + name
        originals.append(pin(original))
        copies.append(pin(copied))
    archive_time = (OUT / 'legacy-component-failures-20261114/command.json').stat().st_mtime_ns
    serial_time = (OUT / 'legacy-full-serial/command.json').stat().st_mtime_ns
    value = {
        'finding_id': 'G2-REVIEW-REPORT-F2', 'status': 'confirmed; pending helper repair and verification',
        'impact': 'Reporter and closure discover the copied archive as a second executed cohort because discovery does not bind saved output destinations to the containing directory.',
        'observed_false_acceptance': False,
        'ordering_observation': {'archive_command_mtime_ns': archive_time,
            'serial_command_mtime_ns': serial_time, 'archive_is_older_than_serial': archive_time < serial_time},
        'scope': 'Archive duplication is demonstrated; no observed override of the later serial result or false acceptance is claimed.',
        'required_repair': 'Bind both saved --basetemp and --junitxml to the discovered cohort directory; retain archives separately and reject malformed command identity.',
        'before_helpers': helpers, 'original_artifacts': originals, 'archive_artifacts': copies,
        'lead_filing_required': True, 'github_write_performed': False,
        'producer': pin(Path(__file__).resolve())}
    save(ledger, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'ledger': pin(ledger), 'snapshots': helpers}, indent=2))


if __name__ == '__main__':
    main()
