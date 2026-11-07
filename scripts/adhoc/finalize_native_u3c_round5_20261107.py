"""Append the reviewed C5 report and one coordination entry, 2026-11-07.

Inputs: reviewed Round 5 section and single-line STATUS entry in C4 scratch.
Outputs: append-only review section, one entry under primary ### codex, and
before/after snapshots/digests in scratch/handoff-r5. Round 4 is never rewritten.
Based on finalize_native_u3c_round4_20261107.py. No Git/network action.
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
MARKER = '## Round 5 — verified projection lifetime'
CORRECTION = ("Correction to Round 4: the instruction to keep A's loader unchanged "
              "came from the lead's brief, not from the owner.")


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
            or not entry.startswith('- ') or '\n' in entry or '\r' in entry):
        raise ValueError('expected one Round 5 section and one single-line STATUS entry')
    if CORRECTION not in section or CORRECTION not in entry:
        raise ValueError('both additions must explicitly correct the Round 4 lead/owner attribution')
    report_before, status_before = REPORT.read_bytes(), STATUS.read_bytes()
    append = b'\n\n' + section.encode().rstrip() + b'\n'
    report_expected = report_before + append
    entry = entry.replace('{REPORT_SHA256}', sha(report_expected))
    if MARKER.encode() in report_before or entry.encode() in status_before:
        raise ValueError('Round 5 handoff already present; refuse duplicate entry')
    heading = b'### codex\n'
    if status_before.count(heading) != 1:
        raise ValueError('coordination section must be unique')
    if REPORT != REPORT.resolve(strict=True) or STATUS != STATUS.resolve(strict=True):
        raise ValueError('handoff targets must not be symlinks')
    evidence = SCRATCH / 'handoff-r5'
    evidence.mkdir(exist_ok=False)
    (evidence / 'section-input.md').write_bytes(args.section.read_bytes())
    (evidence / 'entry-input.md').write_bytes(args.entry.read_bytes())
    (evidence / 'report-before.md').write_bytes(report_before)
    (evidence / 'status-before.md').write_bytes(status_before)
    status_after = status_before.replace(heading, heading + b'\n' + entry.encode() + b'\n', 1)
    staged = evidence / 'status-staged.md'
    staged.write_bytes(status_after)
    os.chmod(staged, STATUS.stat().st_mode & 0o777)
    # This is not a cross-file transaction. Refuse concurrent changes and
    # retain the staged snapshots so a partial append can be reconciled.
    if REPORT.read_bytes() != report_before or STATUS.read_bytes() != status_before:
        raise RuntimeError('coordination changed during preparation; no target written')
    with REPORT.open('ab') as stream:
        stream.write(append)
    report_after = REPORT.read_bytes()
    if report_after != report_expected:
        raise RuntimeError('report changed concurrently; appended report retained, STATUS untouched')
    if STATUS.read_bytes() != status_before:
        raise RuntimeError('STATUS changed; report appended, STATUS untouched')
    os.replace(staged, STATUS)
    if REPORT.read_bytes() != report_expected or STATUS.read_bytes() != status_after:
        raise RuntimeError('handoff verification failed; retained snapshots require review')
    (evidence / 'report-after.md').write_bytes(report_after)
    (evidence / 'status-after.md').write_bytes(status_after)
    result = {'report': str(REPORT), 'report_before_sha256': sha(report_before),
        'report_after_sha256': sha(report_after), 'section_sha256': sha(append),
        'status': str(STATUS), 'status_before_sha256': sha(status_before),
        'status_after_sha256': sha(status_after), 'entry_sha256': sha(entry.encode()),
        'correction': CORRECTION, 'historical_report_prefix_unchanged': True}
    (evidence / 'manifest.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
