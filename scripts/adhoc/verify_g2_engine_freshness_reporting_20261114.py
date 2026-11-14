#!/usr/bin/env python3
# Refresh G2 reporting proof after retained engine freshness failures, 2026-11-14.
# Inputs: frozen report/closure, immutable prior proofs, interrupted cohort and review.
# Outputs: fresh F1/F2 companions, current proof bindings and pending whole-file check.
# No pytest, project imports, driver execution, source edits or final report/closure.
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
REPORT = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
CLOSURE = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'
DRIVER = ROOT / 'scripts/adhoc/verify_g2_report_bytecode_review_20261114.py'
F1 = SCRATCH / 'report-closure-pin-verification-after-engine-freshness'
F2 = SCRATCH / 'report-cohort-discovery-after-engine-freshness'
INTEGRATION = SCRATCH / 'report-engine-freshness-integration-20261114'


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def document(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    assert not INTEGRATION.exists() and not F1.exists() and not F2.exists()
    previous_path = SCRATCH / 'report-scheduled-runner-integration-20261114/index.json'
    previous = json.loads(previous_path.read_bytes())
    historical = list(previous['historical_proofs'])
    for relative, resolutions in (
        ('report-closure-pin-verification-after-scheduled-runner',
         (('reporter', REPORT, 'reviewed-report-source.py'),)),
        ('report-cohort-discovery-after-scheduled-runner',
         (('reporter', REPORT, 'reviewed-report_g2_launch_fixes_20261114.py'),
          ('closure', CLOSURE, 'reviewed-record_g2_final_review_20261114.py'))),
        ('bytecode-closure-pin-verification-after-scheduled-runner',
         (('closure', CLOSURE, 'reviewed-closure.py'),)),
        ('report-auxiliary-discovery-verification-after-scheduled-runner',
         (('reporter', REPORT, 'reviewed-report_g2_launch_fixes_20261114.py'),
          ('closure', CLOSURE, 'reviewed-record_g2_final_review_20261114.py')))):
        directory = SCRATCH / relative
        historical.append({'artifact': pin(directory / 'result.json'),
            'source_resolutions': [{'key': key, 'source_name': str(source),
                                    'snapshot': pin(directory / snapshot)}
                                   for key, source, snapshot in resolutions]})
    before = [
        {'source_name': str(REPORT), 'snapshot': pin(SCRATCH / 'engine-freshness-report-20261114/before-reporter.py')},
        {'source_name': str(CLOSURE), 'snapshot': pin(SCRATCH / 'engine-freshness-closure-20261114/before-closure.py')}]
    for old, retained in zip(previous['current_helpers'], before):
        assert old['path'] == retained['source_name']
        assert all(old[key] == retained['snapshot'][key] for key in ('bytes', 'sha256'))
    INTEGRATION.mkdir()
    index = {'finding_id': 'G2-REVIEW-ENGINE-FRESHNESS-F1',
        'before_helpers': before, 'historical_proofs': historical,
        'current_helpers': [pin(REPORT), pin(CLOSURE)], 'previous_integration': pin(previous_path),
        'review': pin(SCRATCH / 'review-engine-freshness.json'),
        'producer': pin(Path(__file__).resolve()),
        'scope': 'Retained freshness failures and exact interruption only. Historical helper pins resolve to immutable snapshots; source acceptance and narrow legacy reuse policies are unchanged.'}
    document(INTEGRATION / 'index.json', index)
    source = DRIVER.read_text()
    for old, new in (
        ("'scripts/adhoc/verify_g2_cohort_discovery_20261114.py'",
         "'scripts/adhoc/verify_g2_cohort_discovery_auxiliary_20261114.py'"),
        ("'report-cohort-discovery-after-bytecode-review/result.json'",
         "'report-cohort-discovery-after-engine-freshness/result.json'")):
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    namespace = {'__name__': 'retained_reporting_driver', '__file__': str(Path(__file__).resolve())}
    exec(compile(source, str(DRIVER), 'exec'), namespace)
    namespace.update(INTEGRATION=INTEGRATION / 'index.json', F1=F1, F2=F2)
    namespace['main']()
    module = runpy.run_path(str(CLOSURE))
    checks = []
    for identity, name in (
        ('G2-REVIEW-REPORT-F1', 'close_report'),
        ('G2-REVIEW-REPORT-F2', 'close_report_discovery'),
        ('G2-REVIEW-REPORT-F3', 'close_bytecode_pins'),
        ('G2-REVIEW-REPORT-F4', 'close_auxiliary_discovery'),
        ('G2-REVIEW-BYTECODE-F1', 'close_bytecode'),
        ('G2-REVIEW-SCHEDULED-RUNNER-F1', 'close_scheduled_runner')):
        row, details = module['close'](identity, module[name])
        assert row['status'] == 'verified', row
        checks.append({'result': row, 'details': details})
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    discovery = module['discover_cohorts'](SCRATCH)
    directories = module['cohort_directories'](discovery)
    identity = 'G2-REVIEW-ENGINE-FRESHNESS-F1'
    row, details = module['close'](identity, lambda evidence, details:
        module['close_engine_freshness'](directories, head, evidence, details))
    assert row['status'] == 'not_verified', row
    report = runpy.run_path(str(REPORT))
    original = report['load_cohort'](SCRATCH / 'final-engine-dependents', head, {})
    assert original['returncode'] == 2 and original['interrupted'] is True
    assert original['complete'] is original['eligible'] is False
    assert original['junit_entry_counts']['total'] == 241
    assert original['counts'] == {'total': 241, 'passed': 0, 'failed': 3, 'error': 0, 'skipped': 0, 'unconfirmed': 238}
    assert original['pytest_summary']['counts'] == {'failed': 3, 'passed': 237}
    assert original['junit_entries_without_completed_log_outcome'] == 1
    cache = {}
    cohorts = sorted((report['load_cohort'](directory, head, cache) for directory in directories),
                     key=lambda item: (item['order_time'], item['name']))
    required = 'tests/test_native_shared_execution_failure.py'
    proof = report['file_proof'](cohorts, required)
    assert proof['passed'] is False, 'new whole-file proof arrived; retain current output and reassess'
    review = report['review_ledger']
    globals_ = review.__globals__
    original_roster = globals_['REVIEW_FILES']
    globals_['REVIEW_FILES'] = ('review-engine-freshness.json',)
    try:
        ledger = review([], {required: proof})
    finally:
        globals_['REVIEW_FILES'] = original_roster
    finding, = ledger['findings']
    assert finding['id'] == identity and finding['closed_by_verified_declaration'] is False
    assert finding['reported_status'] == 'whole-file rerun pending; original three freshness failures and interrupted cohort retained; latency cause unknown; lead filing required'
    for record in index['current_helpers']:
        assert pin(record['path']) == record
    result = {'status': 'verified', 'reporter': pin(REPORT), 'closure': pin(CLOSURE),
        'producer': pin(Path(__file__).resolve()), 'integration_history': pin(INTEGRATION / 'index.json'),
        'current_closure_checks': checks, 'current_closure_checks_passed': len(checks),
        'engine_freshness': {'closure': row, 'details': details, 'reported_finding': finding,
                            'whole_file_proof': proof, 'verified_rerun': False},
        'interrupted_cohort': {'evidence': original['evidence'], 'counts': original['counts'],
            'junit_entry_counts': original['junit_entry_counts'], 'completed_log_summary': original['pytest_summary'],
            'unmatched_aggregate_entries': original['junit_entries_without_completed_log_outcome'],
            'eligible': original['eligible'], 'returncode': original['returncode']},
        'report_pin_proof': pin(F1 / 'result.json'), 'discovery_proof': pin(F2 / 'result.json'),
        'scope': 'Actual standalone helper entrypoints and saved records only. Interrupted entries remain unconfirmed individually. Current canary cannot establish whole-file proof; no failure is erased or root-cause correction claimed.'}
    path = F1 / 'engine-freshness-reporting-verification.json'
    document(path, result)
    print(json.dumps({'verification': pin(path), 'report_pin_proof': result['report_pin_proof'],
                     'discovery_proof': result['discovery_proof'], 'verified_rerun': False}))


if __name__ == '__main__':
    main()
