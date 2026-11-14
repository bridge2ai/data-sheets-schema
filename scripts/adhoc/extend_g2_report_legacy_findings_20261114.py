#!/usr/bin/env python3
# Include formal legacy verification findings in the G2 handoff, 2026-11-14.
# Inputs: frozen reporter/verifier and retained legacy review ledger.
# Outputs: helper-only revision, immutable before/after snapshots and fresh
# verifier source. Does not execute tests or generate the handoff.
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
TARGET = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
OUTPUT = SCRATCH / 'report-legacy-ledger-revision'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as handle:
        handle.write(raw)


def once(source, before, after):
    assert source.count(before) == 1, before
    return source.replace(before, after, 1)


def main():
    OUTPUT.mkdir()
    original = TARGET.read_bytes()
    source = original.decode()
    source = once(source, "                'review-6217-f3-withdrawn-frozen.json')\n",
        "                'review-6217-f3-withdrawn-frozen.json',\n"
        "                'review-legacy-component-failures-v2.json')\n")
    source = once(source, "        declaration = declared.get(identity)\n",
        "        if identity in ('G2-REVIEW-LEGACY-F1', 'G2-REVIEW-LEGACY-F2'):\n"
        "            proof = [coverage[finding['required_clean_full_file']]]\n"
        "        declaration = declared.get(identity)\n")
    source = once(source,
        "                else 'verified correction; lead filing status retained' if closed\n",
        "                else 'required clean rerun verified; original failure and undetermined cause retained; lead filing retained'\n"
        "                    if closed and identity in ('G2-REVIEW-LEGACY-F1', 'G2-REVIEW-LEGACY-F2')\n"
        "                else 'verified correction; lead filing status retained' if closed\n")
    source = once(source, "'report-closure-pin-verification-after-6217-final/result.json'",
                  "'report-closure-pin-verification-after-legacy-findings/result.json'")
    source = once(source, "        lines.append('- ' + row['id'] + ': ' + row['reported_status'] + '.')\n",
        "        description = row['finding'].get('finding', '')\n"
        "        lines.append('- ' + row['id'] + ': ' + row['reported_status'] + '.'\n"
        "                     + (' ' + description if isinstance(description, str) and description else ''))\n")
    ast.parse(source, filename=str(TARGET))
    save(OUTPUT / 'before-report.py', original)
    TARGET.write_text(source)
    save(OUTPUT / 'after-report.py', TARGET.read_bytes())
    old_verifier = ROOT / 'scripts/adhoc/verify_g2_report_final_6217_20261114.py'
    new_verifier = ROOT / 'scripts/adhoc/verify_g2_report_legacy_findings_20261114.py'
    verifier = once(old_verifier.read_text(),
        "OUTPUT = SCRATCH / 'report-closure-pin-verification-after-6217-final'",
        "OUTPUT = SCRATCH / 'report-closure-pin-verification-after-legacy-findings'")
    verifier = once(verifier,
        '# Verify final G2 reporting revision against retained evidence, 2026-11-14.',
        '# Verify G2 reporter with legacy findings against retained evidence, 2026-11-14.')
    ast.parse(verifier, filename=str(new_verifier))
    save(new_verifier, verifier.encode())
    record = {'producer': pin(Path(__file__).resolve()),
        'before': pin(OUTPUT / 'before-report.py'), 'after': pin(OUTPUT / 'after-report.py'),
        'reporter': pin(TARGET), 'ledger': pin(SCRATCH / 'review-legacy-component-failures-v2.json'),
        'prior_verifier': pin(old_verifier), 'new_verifier': pin(new_verifier),
        'scope': 'Reporting helpers only. Legacy findings require clean whole-file proof plus explicit closure evidence; rerun success is not described as a source correction or timing-cause proof.',
        'tests_run': [], 'handoff_generated': False}
    save(OUTPUT / 'revision.json', (json.dumps(record, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'revision': pin(OUTPUT / 'revision.json'), 'reporter': pin(TARGET), 'verifier': pin(new_verifier)}))


if __name__ == '__main__':
    main()
