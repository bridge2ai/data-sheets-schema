#!/usr/bin/env python3
# Verify exact legacy reuse plus refreshed report proof after F4, 2026-11-14.
# Inputs: saved149 evidence, reviewed leaf commit, current standalone helpers.
# Outputs: fresh F1/F2 companions and pure reuse/interruption checks.
# No pytest/project imports, source edits, actual preservation or final report.
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
DRIVER = ROOT / 'scripts/adhoc/verify_g2_report_bytecode_pin_review_20261114.py'
F1 = SCRATCH / 'report-closure-pin-verification-after-f4-reuse'
F2 = SCRATCH / 'report-cohort-discovery-after-f4-reuse'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def document(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    source = DRIVER.read_text()
    for old, new in (
        ('report-cohort-discovery-after-bytecode-pin-review/result.json',
         'report-cohort-discovery-after-f4-reuse/result.json'),
        ('report-bytecode-pin-integration-20261114/index.json',
         'report-f4-reuse-integration-20261114/index.json')):
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    namespace = {'__name__': 'retained_reporting_driver', '__file__': str(Path(__file__).resolve())}
    exec(compile(source, str(DRIVER), 'exec'), namespace)
    namespace.update(F1=F1, F2=F2)
    namespace['main']()
    helper = ROOT / 'scripts/adhoc/g2_legacy_leaf_reuse_6217_f4_20261114.py'
    module = runpy.run_path(str(helper))
    validate = module['validate_reuse']
    globals_ = validate.__globals__
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    original = module['ORIGINAL']
    directory = SCRATCH / 'legacy-full-serial'
    files = module['FILES']
    cases = []
    proofs = [validate(ROOT, SCRATCH, original, head, file, directory) for file in files]
    assert all(row['passed'] and row['original_head'] == original for row in proofs)
    assert sum(len(row['test_nodes']) for row in proofs) == 149
    cases.append({'case': 'exact_legacy_and_collection149', 'passed': True, 'node_count': 149})

    def refuses(name, call):
        try:
            call()
        except ValueError as error:
            cases.append({'case': name, 'passed': True, 'reason': str(error)})
        else:
            raise AssertionError('reuse wrongly accepted: ' + name)

    refuses('other_cohort_refused', lambda: validate(ROOT, SCRATCH, original, head, files[0],
                                                    SCRATCH / 'legacy-serial-canary'))
    refuses('changed_test_file_refused', lambda: validate(ROOT, SCRATCH, original, head,
                                                         module['LEAF'], directory))
    refuses('different_recorded_head_refused', lambda: validate(ROOT, SCRATCH, head, head, files[0], directory))
    real_git = globals_['git']
    def extra_scope(*args):
        raw = real_git(*args)
        if args[:4] == ('diff', '--name-only', original, head):
            return raw + b'tests/conftest.py\n'
        return raw
    globals_['git'] = extra_scope
    try:
        refuses('additional_shared_scope_delta_refused', lambda: validate(ROOT, SCRATCH, original, head, files[0], directory))
    finally:
        globals_['git'] = real_git
    after = globals_['AFTER_SHA']
    globals_['AFTER_SHA'] = 'f' * 64
    try:
        refuses('different_leaf_hash_refused', lambda: validate(ROOT, SCRATCH, original, head, files[0], directory))
    finally:
        globals_['AFTER_SHA'] = after
    real_pin = globals_['pin']
    def altered_pin(path):
        value = real_pin(path)
        if Path(path) == directory / 'pytest.xml':
            value = {**value, 'sha256': 'f' * 64}
        return value
    globals_['pin'] = altered_pin
    try:
        refuses('changed_exact_junit_identity_refused', lambda: validate(ROOT, SCRATCH, original, head, files[0], directory))
    finally:
        globals_['pin'] = real_pin
    reporter = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
    report = runpy.run_path(str(reporter))
    cache = {}
    legacy = report['load_cohort'](directory, head, cache)
    other = report['load_cohort'](SCRATCH / 'legacy-serial-canary', head, cache)
    assert legacy['eligible'] is True and legacy['counts']['passed'] == 149
    assert legacy['source_equivalence']['legacy_reuse'] and legacy['command']['head'] == original
    assert other['command']['head'] == original and other['eligible'] is False
    assert cache[original]['passed'] is False and 'legacy_reuse' not in cache[original]
    cases.append({'case': 'report_reuse_does_not_leak_through_same_head_cache', 'passed': True,
                  'eligible': legacy['name'], 'ineligible': other['name']})
    interrupted = report['load_cohort'](SCRATCH / 'final-regressions', head, {})
    assert interrupted['returncode'] == 2 and interrupted['interrupted'] is True
    assert interrupted['complete'] is interrupted['eligible'] is False
    assert interrupted['junit_entry_counts']['total'] == 30
    assert interrupted['counts']['failed'] == 1 and interrupted['counts']['unconfirmed'] == 29
    assert interrupted['pytest_summary']['counts'] == {'failed': 1, 'passed': 25}
    assert interrupted['junit_entries_without_completed_log_outcome'] == 4
    cases.append({'case': 'interrupted_oracle_cohort_remains_ineligible', 'passed': True,
                  'junit_entries': 30, 'completed_log_counts': {'failed': 1, 'passed': 25},
                  'unconfirmed_junit_entries': 29, 'abandoned_entries_in_aggregate': 4})
    result = {'status': 'verified', 'cases': cases, 'passed': len(cases), 'failed': 0,
        'original_head': original, 'current_head': head, 'correction_commit': module['CORRECTION'],
        'reuse_record': pin(module['RECORD']), 'validator': pin(helper), 'reporter': pin(reporter),
        'closure': pin(ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'),
        'producer': pin(Path(__file__).resolve()), 'retained_driver': pin(DRIVER),
        'legacy_proof': proofs, 'interrupted_evidence': interrupted['evidence'],
        'scope': 'Actual saved evidence and pure helper functions. Negative delta/hash cases replace only in-memory read results, never source/artifact files. No tests, project imports, final report or legacy replay at the new HEAD.'}
    document(F1 / 'legacy-reuse-verification.json', result)
    print(json.dumps({'reuse_verification': pin(F1 / 'legacy-reuse-verification.json'),
        'passed': len(cases), 'failed': 0, 'report_pin_proof': pin(F1 / 'result.json'),
        'discovery_proof': pin(F2 / 'result.json')}))


if __name__ == '__main__':
    main()
