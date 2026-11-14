#!/usr/bin/env python3
# Retain confirmed F4 traceback and committed oracle correction, 2026-11-14.
# Inputs: original F4 review, interrupted cohort, exact Git commits and closure.
# Outputs: immutable companion ledger, traceback/patch/test/closure snapshots.
# No project import, pytest, source edit, final closure, signals or commits.
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
DEST = OUT / 'publication-oracle-correction-6217'
APPLIED = '2070a2116ceb5b1f5dd9a870c803ee3311d298b9'
FIX = '21367471df2e7d2f761153e1b91b218a705c62c6'
TEST = 'tests/test_native_publication_signals.py'
SCOPE = ('src', 'tests', 'notes/matched_cborg_2026-09-13', 'pyproject.toml', 'poetry.lock', 'conftest.py', '.github/workflows/main.yaml')


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw
    return pin(path)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    ledger = OUT / 'review-6217-f4-confirmed.json'
    assert not DEST.exists() and not ledger.exists()
    assert git('diff', '--name-only', APPLIED, FIX, '--', *SCOPE).decode().splitlines() == [TEST]
    assert not git('diff', '--name-only', FIX, 'HEAD', '--', *SCOPE)
    assert not git('diff', '--name-only', 'HEAD', '--', *SCOPE)
    corrected = git('show', FIX + ':' + TEST)
    assert (ROOT / TEST).read_bytes() == corrected
    old_review = json.loads((OUT / 'review-6217-f4.json').read_bytes())
    assert old_review['finding_id'] == 'G2-REVIEW-6217-F4'
    cohort = OUT / 'final-regressions'
    outcome = json.loads((cohort / 'outcome.json').read_bytes())
    assert outcome['returncode'] == 2 and outcome['counts'] == {'total': 30, 'failed': 1, 'error': 0, 'skipped': 0}
    failed = [node for node in ET.parse(cohort / 'pytest.xml').iter('testcase') if node.find('failure') is not None]
    assert len(failed) == 1
    node = failed[0]
    assert node.get('classname') == 'tests.test_native_publication_signals'
    assert node.get('name') == 'test_public_first_signal_during_publication_keeps_exact_readback[2]'
    trace = node.find('failure').text or ''
    assert 'tests/test_native_publication_signals.py:157' in trace and 'c.canonical(result)' in trace
    cleanups = sorted((OUT / 'final-regressions-interruption-6217-oracle').glob('cleanup-*.json'))
    cleanup = json.loads(cleanups[-1].read_bytes())
    assert cleanup['safe_to_release_source_freeze'] is True
    assert all(row['original_reaped'] for row in [cleanup['coordinator'], cleanup['runner'], *cleanup['workers'], *cleanup['observed_descendants']])
    DEST.mkdir()
    before_closure = save(DEST / 'before-closure.py', (ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py').read_bytes())
    current_test = save(DEST / 'corrected-publication-test.py', corrected)
    patch = save(DEST / 'oracle-correction.patch', git('diff', APPLIED, FIX, '--', TEST))
    traceback = save(DEST / 'confirmed-traceback.txt', trace.encode())
    value = {'finding_id': 'G2-REVIEW-6217-F4', 'priority': 'P2',
        'status': 'traceback confirmed; oracle correction committed; complete regression proof pending',
        'original_review': pin(OUT / 'review-6217-f4.json'), 'before_closure': before_closure,
        'pytest_failure_attribution': {'status': 'confirmed from completed interrupted-cohort JUnit and log',
            'classname': node.get('classname'), 'name': node.get('name'), 'path': TEST, 'line': 157,
            'assertion': "assert (evidence / 'final.json').read_bytes() == c.canonical(result)",
            'traceback': traceback},
        'correction_commit': FIX, 'production_commit': APPLIED,
        'production_unchanged_since_implementation': True,
        'source_scope_changes': [TEST], 'corrected_test': current_test, 'patch': patch,
        'correction': 'Use engine.draft._encoded(result), the established publication encoding; exact-byte, marker-hash, cleanup and independent read_final assertions remain.',
        'required_clean_full_file': TEST,
        'required_public_regression': 'test_public_first_signal_during_publication_keeps_exact_readback',
        'interrupted_cohort': {'artifacts': [pin(cohort / name) for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log')],
            'cleanup': pin(cleanups[-1]), 'returncode': 2, 'seconds': outcome['seconds'],
            'log_passed': 25, 'log_failed': 1, 'junit_entries': 30, 'abandoned_entries': 4,
            'individual_empty_junit_passes_unconfirmed': True, 'all_observed_processes_reaped': True},
        'test_success_claimed': False, 'runtime_hang_established': False,
        'lead_filing_required': True, 'github_write_performed': False,
        'producer': pin(Path(__file__).resolve())}
    result = save(ledger, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'ledger': result, 'before_closure': before_closure, 'corrected_test': current_test}, indent=2))


if __name__ == '__main__':
    main()
