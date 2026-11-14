#!/usr/bin/env python3
"""Freeze historical report source for H2 bytecode review, 2026-11-13.
Inputs: saved review hashes and committed d0e630607 report bytes. Outputs:
immutable source snapshot, original review archive, and rebound review evidence.
Preserves the exact version exercised before later queue-report additions.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-h2-resume-20261113'
RELATIVE = 'scripts/adhoc/report_h2_resume_20261113.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    path = SCRATCH / 'bytecode-review.json'
    original = path.read_bytes()
    value = json.loads(original)
    entry = next(row for row in value['evidence'] if row['path'] == str(ROOT / RELATIVE))
    commit = subprocess.check_output(['git', 'rev-parse', 'd0e630607'], cwd=ROOT, text=True).strip()
    raw = subprocess.check_output(['git', 'show', commit + ':' + RELATIVE], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == entry['sha256']
    snapshot = SCRATCH / 'bytecode-reviewed-report-source.txt'
    archive = SCRATCH / 'bytecode-review-original.json'
    with snapshot.open('xb') as stream:
        stream.write(raw)
    with archive.open('xb') as stream:
        stream.write(original)
    entry.update(pin(snapshot))
    value['historical_report_source_commit'] = commit
    value['historical_report_repository_path'] = RELATIVE
    value['original_review_archive'] = pin(archive)
    value['snapshot_scope'] = 'Exact report source exercised in the bytecode-proof check; later queue-report additions are covered by final source audit and separate read-only review.'
    value['snapshot_producer'] = pin(Path(__file__).resolve())
    path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({'review': pin(path), 'source_snapshot': pin(snapshot), 'archive': pin(archive)}))


if __name__ == '__main__':
    main()
