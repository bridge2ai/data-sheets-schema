"""Append the requested C4 report and one coordination entry, 2026-11-07.

Inputs: reviewed Markdown section and STATUS entry in the assigned scratch.
Outputs: append-only external review section, one entry under primary ### codex,
and exact before/after snapshots and digests in scratch. No Git/network action.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXECUTIONS = ROOT.parent
SCRATCH = EXECUTIONS / 'scratch-native-u3c-r4'
REPORT = EXECUTIONS / 'plans/reviews/native_u3c_2026-11-07.md'
STATUS = EXECUTIONS.parent / 'data-sheets-schema/notes/coordination/STATUS.md'
MARKER = '## Round 4 — consumer split and pure permission interface'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--section', type=Path, required=True)
    parser.add_argument('--entry', type=Path, required=True)
    args = parser.parse_args()
    for path in (args.section, args.entry):
        if path != path.resolve(strict=True) or not path.is_relative_to(SCRATCH):
            raise ValueError('handoff inputs must be literal C4 scratch files')
    section, entry = args.section.read_text(), args.entry.read_text()
    if not section.startswith(MARKER) or not entry.startswith('- '):
        raise ValueError('unexpected handoff format')
    report_before, status_before = REPORT.read_bytes(), STATUS.read_bytes()
    append = b'\n\n' + section.encode().rstrip() + b'\n'
    entry = entry.replace('{REPORT_SHA256}', sha(report_before + append))
    if MARKER.encode() in report_before or entry.encode().strip() in status_before:
        raise ValueError('C4 handoff already present; refuse duplicate entry')
    heading = b'### codex\n'
    if status_before.count(heading) != 1:
        raise ValueError('coordination section must be unique')
    if REPORT != REPORT.resolve(strict=True) or STATUS != STATUS.resolve(strict=True):
        raise ValueError('handoff targets must not be symlinks')
    evidence = SCRATCH / 'handoff'
    evidence.mkdir(exist_ok=False)
    (evidence / 'report-before.md').write_bytes(report_before)
    (evidence / 'status-before.md').write_bytes(status_before)
    status_after = status_before.replace(heading, heading + b'\n' + entry.encode().rstrip() + b'\n', 1)
    staged = evidence / 'status-staged.md'
    staged.write_bytes(status_after)
    os.chmod(staged, STATUS.stat().st_mode & 0o777)
    # Refuse concurrent changes instead of overwriting another session's work.
    if REPORT.read_bytes() != report_before or STATUS.read_bytes() != status_before:
        raise RuntimeError('coordination changed during preparation; no target written')
    with REPORT.open('ab') as stream:
        stream.write(append)
    if STATUS.read_bytes() != status_before:
        raise RuntimeError('STATUS changed; report appended, STATUS untouched')
    os.replace(staged, STATUS)
    report_after = REPORT.read_bytes()
    if not report_after.startswith(report_before) or STATUS.read_bytes() != status_after:
        raise RuntimeError('handoff verification failed')
    (evidence / 'report-after.md').write_bytes(report_after)
    (evidence / 'status-after.md').write_bytes(status_after)
    result = {'report': str(REPORT), 'report_before_sha256': sha(report_before),
        'report_after_sha256': sha(report_after), 'section_sha256': sha(append),
        'status': str(STATUS), 'status_before_sha256': sha(status_before),
        'status_after_sha256': sha(status_after), 'entry_sha256': sha(entry.encode())}
    (evidence / 'manifest.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
