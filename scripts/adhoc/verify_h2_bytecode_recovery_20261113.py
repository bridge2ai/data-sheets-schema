#!/usr/bin/env python3
"""Verify H2-RESUME-BYTECODE-F1/F2 corrections, 2026-11-13.
Inputs: preservation/report helper sources. Outputs: isolated scratch recovery
fixture and review evidence. No source bytecode moves or project test runs.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-h2-resume-20261113'


def namespace(path):
    scope = {'__name__': 'verification_only', '__file__': str(path)}
    exec(compile(path.read_text(), str(path), 'exec'), scope)
    return scope


def main():
    helper = ROOT / 'scripts/adhoc/preserve_h2_generated_bytecode_20261113.py'
    reporter = ROOT / 'scripts/adhoc/report_h2_resume_20261113.py'
    move = namespace(helper)
    report = namespace(reporter)
    fixture = SCRATCH / 'bytecode-recovery-check'
    fixture.mkdir(exist_ok=False)
    source_root = fixture / 'source'
    source_root.mkdir()
    source = source_root / 'example.pyc'
    source.write_bytes(b'non-executable recovery fixture\n')
    target = fixture / 'preserved.pyc'
    entry = {'state': 'planned', 'former_relative_location': source.name,
             'destination': str(target), 'bytes': source.stat().st_size,
             'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    ledger = {'status': 'planned', 'entries': [entry]}
    move.update(ROOT=source_root, SCRATCH=fixture, LEDGER=fixture / 'ledger.json')
    move['checkpoint'](ledger)
    source.rename(target)  # Simulate process loss after rename, before checkpoint.
    move['preserve'](entry, ledger)
    recovered = json.loads(move['LEDGER'].read_bytes())
    assert recovered['entries'][0]['state'] == 'preserved'
    assert target.read_bytes() == b'non-executable recovery fixture\n' and not source.exists()
    checks = []
    for status, bad_hash, expected in (
        ('canary_verified', False, False), ('complete', False, True), ('complete', True, False)
    ):
        case = json.loads(json.dumps(recovered))
        case['status'] = status
        if bad_hash:
            case['entries'][0]['sha256'] = '0' * 64
        case_path = fixture / (status + ('-bad-hash' if bad_hash else '') + '.json')
        case_path.write_text(json.dumps(case) + '\n')
        try:
            report['verified_bytecode'](case_path)
            accepted = True
        except AssertionError:
            accepted = False
        assert accepted is expected
        checks.append({'status': status, 'bad_hash': bad_hash, 'accepted': accepted})
    record = {
        'findings': [
            {'id': 'H2-RESUME-BYTECODE-F1', 'finding': 'Moves preceded ledger persistence, so interruption could omit moved files.',
             'correction': 'Persist the complete plan first; checkpoint atomically after each verified move; reconcile an already moved destination on recovery.'},
            {'id': 'H2-RESUME-BYTECODE-F2', 'finding': 'The handoff accepted an incomplete or unverified bytecode ledger.',
             'correction': 'Require completed preservation and verify every destination size and SHA256 before reporting it.'},
        ],
        'status': 'corrected-before-relocation', 'recovery_after_rename_verified': True,
        'report_acceptance_checks': checks,
        'evidence': [report['pin'](helper), report['pin'](reporter), report['pin'](move['LEDGER'])],
        'lead_filing_needed': True, 'github_issue_numbers': [],
        'filing_reason': 'Helper GitHub writes are prohibited; the lead must file both review findings.',
        'causal_limit': 'File mtimes establish observation after lane launch, not the origin of each bytecode file.'
    }
    destination = SCRATCH / 'bytecode-review.json'
    with destination.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report['pin'](destination)))


if __name__ == '__main__':
    main()
