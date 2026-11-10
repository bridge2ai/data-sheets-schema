#!/usr/bin/env python3
"""Atomically publish the U3-M report and one coordination entry, 2026-11-09.

Inputs: reviewed report draft and status-entry.md under the assigned evidence
paths. Outputs: final report, primary STATUS.md, preserved originals and a
publication witness. Reporting only; no tests, subprocesses or network.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = ROOT.parent.parent / 'data-sheets-schema'
M = ROOT.parent / 'scratch-native-u1u3/u3m'
REPORT = ROOT.parent / 'plans/reviews/native_u3m_2026-11-09.md'
DRAFT = REPORT.with_name('native_u3m_2026-11-09.final-draft.md')
STATUS = PRIMARY / 'notes/coordination/STATUS.md'
ENTRY = M / 'status-entry.md'
MARKER = b'<!-- codex-native-u3m-final-20261109 -->'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    assert path.is_absolute() and path.resolve(strict=True) == path and path.is_file()
    raw = path.read_bytes()
    assert raw
    return raw


def save(path, raw, mode=0o600):
    assert path.parent.resolve(strict=True) == path.parent
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, mode)
    assert path.read_bytes() == raw


def main():
    assert ROOT.name == 'codex-native-u1u3'
    assert not os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock')
    assert shutil.disk_usage(M).free > 64 * 1024 * 1024, 'need reporting working space'
    report, draft, status, entry = map(read, (REPORT, DRAFT, STATUS, ENTRY))
    assert MARKER not in status and entry.count(MARKER) == 1
    assert entry.count(b'REPORT_SHA256') == 1
    assert b'IN PROGRESS' not in draft and b'FINAL_HEAD_PENDING' not in draft
    header = b'### codex\n'
    assert status.count(header) == 1
    new_status = status.replace(header, header + b'\n' + entry.replace(
        b'REPORT_SHA256', digest(draft).encode()).rstrip() + b'\n', 1)
    backup = M / 'report-publication-backups'
    backup.mkdir(exist_ok=False)
    save(backup / 'report-before.md', report)
    save(backup / 'STATUS-before.md', status)
    report_tmp = REPORT.with_name(REPORT.name + '.u3m-publish-tmp')
    status_tmp = STATUS.with_name(STATUS.name + '.u3m-publish-tmp')
    save(report_tmp, draft, stat.S_IMODE(REPORT.stat().st_mode))
    save(status_tmp, new_status, stat.S_IMODE(STATUS.stat().st_mode))
    assert read(REPORT) == report and read(STATUS) == status, 'concurrent edit; stop without replacement'
    os.replace(report_tmp, REPORT)
    assert read(STATUS) == status, 'concurrent STATUS edit; report published, STATUS left untouched'
    os.replace(status_tmp, STATUS)
    assert read(REPORT) == draft and read(STATUS) == new_status
    witness = dict(report=str(REPORT), report_bytes=len(draft), report_sha256=digest(draft),
        status=str(STATUS), status_before_sha256=digest(status), status_after_sha256=digest(new_status),
        status_entry_sha256=digest(entry), original_report_sha256=digest(report),
        originals_preserved=str(backup), single_entry_marker=MARKER.decode(),
        helper_sha256=digest(read(Path(__file__).resolve())))
    save(M / 'report-publication.json', (json.dumps(witness, indent=2) + '\n').encode())
    print(json.dumps(witness))


if __name__ == '__main__':
    main()
