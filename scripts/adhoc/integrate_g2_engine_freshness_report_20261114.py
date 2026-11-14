#!/usr/bin/env python3
# Retain G2 engine freshness failures and exact interruption cleanup, 2026-11-14.
# Inputs: frozen reporter, immutable freshness review and completed cleanup.
# Outputs: before-reporter snapshot, minimal reporter edits and revision pins.
# No project imports, tests, source edits, final handoff or commits.
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
TARGET = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
OUT = SCRATCH / 'engine-freshness-report-20261114'
CLEANUP = 'final-engine-freshness-interruption/cleanup-1794646795499479000.json'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    assert not OUT.exists(), 'retain prior reporter revision'
    review = SCRATCH / 'review-engine-freshness.json'
    record = json.loads(review.read_bytes())
    value, = record['findings']
    assert value['finding_id'] == 'G2-REVIEW-ENGINE-FRESHNESS-F1'
    cleanup = json.loads((SCRATCH / CLEANUP).read_bytes())
    assert cleanup['status'] == 'cleanup-confirmed' and cleanup['safe_to_release_source_freeze'] is True
    before = TARGET.read_bytes()
    source = before.decode()
    edits = (
        ("'scheduled-runner-review-20261114/correction.json')",
         "'scheduled-runner-review-20261114/correction.json', 'review-engine-freshness.json')"),
        ('report-closure-pin-verification-after-scheduled-runner/result.json',
         'report-closure-pin-verification-after-engine-freshness/result.json'),
        ("        if identity in ('G2-REVIEW-LEGACY-F1', 'G2-REVIEW-LEGACY-F2'):\n",
         "        if identity == 'G2-REVIEW-ENGINE-FRESHNESS-F1':\n"
         "            proof = [coverage['tests/test_native_shared_execution_failure.py']]\n"
         "        if identity in ('G2-REVIEW-LEGACY-F1', 'G2-REVIEW-LEGACY-F2'):\n"),
        ("                else 'scheduled canary verified; static correction retained; lead filing required'",
         "                else 'required clean whole-file rerun verified; original three freshness failures and unknown latency cause retained; no code correction claimed; lead filing required'\n"
         "                    if closed and identity == 'G2-REVIEW-ENGINE-FRESHNESS-F1'\n"
         "                else 'whole-file rerun pending; original three freshness failures and interrupted cohort retained; latency cause unknown; lead filing required'\n"
         "                    if identity == 'G2-REVIEW-ENGINE-FRESHNESS-F1'\n"
         "                else 'scheduled canary verified; static correction retained; lead filing required'"),
        ("    issues = []\n",
         "    freshness_cleanup_path = SCRATCH / '" + CLEANUP + "'\n"
         "    freshness_cleanup = read_json(freshness_cleanup_path)\n"
         "    check_nested_pins(freshness_cleanup)\n"
         "    assert freshness_cleanup['status'] == 'cleanup-confirmed' and freshness_cleanup['safe_to_release_source_freeze'] is True\n"
         "    assert all(row['original_reaped'] is True for row in (\n"
         "        freshness_cleanup['coordinator'], freshness_cleanup['runner'], *freshness_cleanup['workers'],\n"
         "        *freshness_cleanup['observed_descendants']))\n"
         "    issues = []\n"),
        ("        'publication_oracle_interruption': {'record': oracle_cleanup, 'evidence': pin(oracle_cleanup_path)},\n",
         "        'publication_oracle_interruption': {'record': oracle_cleanup, 'evidence': pin(oracle_cleanup_path)},\n"
         "        'engine_freshness_interruption': {'record': freshness_cleanup, 'evidence': pin(freshness_cleanup_path)},\n"),
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
        'current_reporter': pin(TARGET), 'review': pin(review), 'cleanup': pin(SCRATCH / CLEANUP),
        'producer': pin(Path(__file__).resolve()),
        'scope': 'Retains original failures and exact interrupted-session cleanup. General cohort accounting and eligibility remain unchanged. Later whole-file proof can verify a rerun, never infer a corrected latency cause.'}
    save(OUT / 'revision.json', (json.dumps(record, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'revision': pin(OUT / 'revision.json'), 'reporter': record['current_reporter']}))


if __name__ == '__main__':
    main()
