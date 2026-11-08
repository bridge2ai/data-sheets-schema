#!/usr/bin/env python3
"""Append C6's report and one STATUS entry, 2026-11-07.

Inputs: reviewed section/entry in the assigned C4 scratch; outputs: append-only
review, single coordination entry and before/after digest snapshots in handoff-r6.
No tests, source edits, network or Git mutations. Stop after verified handoff.
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
MARKER = '## Round 6 — reconciled C head for D'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--section', type=Path, required=True)
    parser.add_argument('--entry', type=Path, required=True)
    args = parser.parse_args()
    for path in (args.section, args.entry):
        if (path != path.resolve(strict=True) or not path.is_relative_to(SCRATCH)
                or not path.is_file()):
            raise ValueError('handoff inputs must be literal C4 scratch files')
    section = args.section.read_text()
    entry = args.entry.read_text().strip()
    if (not section.startswith(MARKER + '\n') or section.count(MARKER) != 1
            or not entry.startswith('- ') or '\n' in entry or '\r' in entry
            or 'final C head for D' not in section or 'final C head for D' not in entry):
        raise ValueError('expected one Round 6 section and single-line entry naming final C head for D')
    report_before, status_before = REPORT.read_bytes(), STATUS.read_bytes()
    append = b'\n\n' + section.encode().rstrip() + b'\n'
    report_expected = report_before + append
    entry = entry.replace('{REPORT_SHA256}', sha(report_expected))
    if MARKER.encode() in report_before or entry.encode() in status_before:
        raise ValueError('Round 6 handoff already present')
    heading = b'### codex\n'
    if status_before.count(heading) != 1:
        raise ValueError('coordination section must be unique')
    if REPORT != REPORT.resolve(strict=True) or STATUS != STATUS.resolve(strict=True):
        raise ValueError('handoff targets must not be symlinks')
    evidence = SCRATCH / 'handoff-r6'
    evidence.mkdir(exist_ok=False)
    for name, raw in (('section-input.md', args.section.read_bytes()),
                      ('entry-input.md', args.entry.read_bytes()),
                      ('report-before.md', report_before), ('status-before.md', status_before)):
        (evidence / name).write_bytes(raw)
    status_after = status_before.replace(heading, heading + b'\n' + entry.encode() + b'\n', 1)
    staged = evidence / 'status-staged.md'
    staged.write_bytes(status_after)
    os.chmod(staged, STATUS.stat().st_mode & 0o777)
    if REPORT.read_bytes() != report_before or STATUS.read_bytes() != status_before:
        raise RuntimeError('coordination changed during preparation; no target written')
    with REPORT.open('ab') as stream:
        stream.write(append)
    if REPORT.read_bytes() != report_expected or STATUS.read_bytes() != status_before:
        raise RuntimeError('concurrent change; report appended, STATUS untouched')
    os.replace(staged, STATUS)
    if REPORT.read_bytes() != report_expected or STATUS.read_bytes() != status_after:
        raise RuntimeError('handoff verification failed; reconcile saved snapshots')
    (evidence / 'report-after.md').write_bytes(report_expected)
    (evidence / 'status-after.md').write_bytes(status_after)
    result = {'report': str(REPORT), 'report_before_sha256': sha(report_before),
              'report_after_sha256': sha(report_expected), 'section_sha256': sha(append),
              'status': str(STATUS), 'status_before_sha256': sha(status_before),
              'status_after_sha256': sha(status_after), 'entry_sha256': sha(entry.encode()),
              'historical_report_prefix_unchanged': True}
    (evidence / 'manifest.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
