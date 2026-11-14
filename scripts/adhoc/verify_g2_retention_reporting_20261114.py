#!/usr/bin/env python3
"""Refresh G2 reporting proofs for retained lifecycle failures, 2026-11-14.

Inputs: frozen report/closure, immutable prior proof families, original completed
failure ledger and separate diagnostic command or eventual completed outcome.
Outputs: new after-retention-stability F1/F2 proofs and bounded integration checks.
No pytest, project imports, diagnostic execution, source/test edits, commits,
actual final-review-closure, final source audit or handoff generation.
"""
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
F1 = SCRATCH / 'report-closure-pin-verification-after-retention-stability'
F2 = SCRATCH / 'report-cohort-discovery-after-retention-stability'
INTEGRATION = SCRATCH / 'report-retention-stability-integration-20261114'
ORIGINAL = SCRATCH / 'final-engine-lifecycles'
RETENTION = 'G2-REVIEW-RETENTION-STABILITY-F1'
PARSER = 'G2-REVIEW-RETENTION-LEDGER-F1'
SELECTED = ('tests/test_native_admission_failure.py', 'tests/test_native_incomplete_retention.py',
            'tests/test_native_failure_publication.py')


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
    assert not INTEGRATION.exists() and not F1.exists() and not F2.exists(), 'retain all earlier proof outputs'
    previous_path = SCRATCH / 'report-engine-freshness-integration-20261114/index.json'
    previous = json.loads(previous_path.read_bytes())
    historical = list(previous['historical_proofs'])
    for relative, resolutions in (
        ('report-closure-pin-verification-after-engine-freshness',
         (('reporter', REPORT, 'reviewed-report-source.py'),)),
        ('report-cohort-discovery-after-engine-freshness',
         (('reporter', REPORT, 'reviewed-report_g2_launch_fixes_20261114.py'),
          ('closure', CLOSURE, 'reviewed-record_g2_final_review_20261114.py'))),
        ('bytecode-closure-pin-verification-after-engine-freshness',
         (('closure', CLOSURE, 'reviewed-closure.py'),)),
        ('report-auxiliary-discovery-verification-after-engine-freshness',
         (('reporter', REPORT, 'reviewed-report_g2_launch_fixes_20261114.py'),
          ('closure', CLOSURE, 'reviewed-record_g2_final_review_20261114.py')))):
        directory = SCRATCH / relative
        historical.append({'artifact': pin(directory / 'result.json'),
            'source_resolutions': [{'key': key, 'source_name': str(source),
                                    'snapshot': pin(directory / snapshot)}
                                   for key, source, snapshot in resolutions]})
    before = [
        {'source_name': str(REPORT), 'snapshot': pin(SCRATCH / 'retention-stability-report-20261114/before-reporter.py')},
        {'source_name': str(CLOSURE), 'snapshot': pin(SCRATCH / 'retention-stability-closure-20261114/before-closure.py')}]
    for old, retained in zip(previous['current_helpers'], before):
        assert old['path'] == retained['source_name']
        assert all(old[key] == retained['snapshot'][key] for key in ('bytes', 'sha256'))
    INTEGRATION.mkdir()
    index = {'finding_id': RETENTION, 'before_helpers': before, 'historical_proofs': historical,
        'current_helpers': [pin(REPORT), pin(CLOSURE)], 'previous_integration': pin(previous_path),
        'review': pin(SCRATCH / 'review-retention-stability.json'),
        'producer': pin(Path(__file__).resolve()),
        'scope': 'Retain normal completed lifecycle failures and parser correction; add diagnostic-only input binding. Source scope, acceptance, discovery and narrow legacy reuse remain unchanged.'}
    document(INTEGRATION / 'index.json', index)
    source = DRIVER.read_text()
    for old, new in (
        ("'scripts/adhoc/verify_g2_cohort_discovery_20261114.py'",
         "'scripts/adhoc/verify_g2_cohort_discovery_auxiliary_20261114.py'"),
        ("'report-cohort-discovery-after-bytecode-review/result.json'",
         "'report-cohort-discovery-after-retention-stability/result.json'")):
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
        ('G2-REVIEW-SCHEDULED-RUNNER-F1', 'close_scheduled_runner'),
        (PARSER, 'close_retention_ledger')):
        row, details = module['close'](identity, module[name])
        assert row['status'] == 'verified', row
        checks.append({'result': row, 'details': details})
    parser = checks[-1]
    assert parser['details'][0]['cases'] == parser['details'][0]['passed'] == 3
    retained, retained_details = module['close'](RETENTION, module['retain_retention_stability'])
    assert retained['status'] == 'not_verified' and retained_details[0]['diagnostic_can_close'] is False
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    report = runpy.run_path(str(REPORT))
    original = report['load_cohort'](ORIGINAL, head, {})
    assert original['returncode'] == 1 and original['interrupted'] is False
    assert original['complete'] is True and original['eligible'] is False
    assert original['counts'] == {'total': 29, 'passed': 26, 'failed': 3, 'error': 0, 'skipped': 0, 'unconfirmed': 0}
    assert original['pytest_summary']['counts'] == {'failed': 3, 'passed': 26}
    proofs = {file: report['file_proof']([original], file) for file in SELECTED}
    assert all(proof['passed'] is False and proof['returncode'] == 1 for proof in proofs.values())
    refusals = []
    for file in SELECTED:
        row, details = module['close']('pure-original-cohort-acceptance-check',
            lambda evidence, details, file=file: module['test_proof'](file, None, [ORIGINAL], head, evidence))
        assert row['status'] == 'not_verified' and row['reason'] == 'latest selected cohort failed', row
        refusals.append({'file': file, 'closure': row})
    diagnostic = report['retention_diagnostic'](head)
    assert diagnostic['diagnostic_only'] is True and diagnostic['acceptance_evidence'] is False
    assert diagnostic['whole_file_coverage'] is False and diagnostic['closes_retention_finding'] is False
    # All generic discovery functions remain unchanged. Diagnostic.* records
    # lack every acceptance marker; no discovery exception is introduced.
    discovery = report['discover_cohorts'](SCRATCH)
    diagnostic_directory = SCRATCH / 'retention-stability-diagnostic'
    assert not any(row['directory'] == str(diagnostic_directory) for row in discovery)
    assert diagnostic_directory not in report['cohort_directories'](discovery)
    assert not module['selects'](diagnostic['command'], SELECTED[1], None)
    # Pure isolated declaration counterexample. This is not the actual final
    # closure: even a forged verified declaration cannot close retention F1.
    fixture = F1 / 'retention-review-counterexample'
    fixture.mkdir()
    original_review = SCRATCH / 'review-retention-stability.json'
    with (fixture / original_review.name).open('xb') as stream:
        stream.write(original_review.read_bytes())
    forced = {**retained, 'status': 'verified', 'reason': 'Deliberately invalid synthetic closure declaration.'}
    document(fixture / 'final-review-closure.json', {'findings': [forced, parser['result']]})
    review = report['review_ledger']
    state = review.__globals__
    saved_scratch, saved_roster = state['SCRATCH'], state['REVIEW_FILES']
    state['SCRATCH'], state['REVIEW_FILES'] = fixture, (original_review.name,)
    try:
        ledger = review([], proofs)
    finally:
        state['SCRATCH'], state['REVIEW_FILES'] = saved_scratch, saved_roster
    by_id = {row['id']: row for row in ledger['findings']}
    assert set(by_id) == {RETENTION, PARSER}
    assert by_id[RETENTION]['closed_by_verified_declaration'] is False
    assert by_id[RETENTION]['reported_status'].startswith('open; original normal completed cohort retained')
    assert by_id[PARSER]['closed_by_verified_declaration'] is True
    assert 'parser correction verified' in by_id[PARSER]['reported_status']
    for record in index['current_helpers']:
        assert pin(record['path']) == record
    assert pin(original_review) == index['review']
    result = {'status': 'verified', 'reporter': pin(REPORT), 'closure': pin(CLOSURE),
        'producer': pin(Path(__file__).resolve()), 'integration_history': pin(INTEGRATION / 'index.json'),
        'current_closure_checks': checks, 'current_closure_checks_passed': len(checks),
        'retention': {'closure': retained, 'details': retained_details, 'whole_file_proofs': proofs,
            'original_cohort_evidence': original['evidence'], 'counts': original['counts'],
            'returncode': 1, 'interrupted': False, 'eligible': False, 'acceptance_refusals': refusals},
        'parser': parser, 'diagnostic': diagnostic,
        'diagnostic_completion_binding_checked': 'outcome' in diagnostic,
        'diagnostic_completion_binding_pending': 'outcome' not in diagnostic,
        'diagnostic_discovered_as_acceptance': False,
        'forced_closure_counterexample': {'fixture': pin(fixture / 'final-review-closure.json'),
            'reported_findings': ledger['findings'], 'original_failure_stayed_open': True,
            'scope': 'Synthetic declaration tests only the standalone reporter; no final closure file is written in the actual scratch root.'},
        'report_pin_proof': pin(F1 / 'result.json'), 'discovery_proof': pin(F2 / 'result.json'),
        'scope': 'Pure existing proof families and actual standalone reporting functions only. The original completed failures remain open, the producer parser is verified separately, and a diagnostic is never acceptance. Unknown diagnostic completion is explicitly pending.'}
    target = F1 / 'retention-reporting-verification.json'
    document(target, result)
    print(json.dumps({'verification': pin(target), 'reporter': pin(REPORT), 'closure': pin(CLOSURE),
                      'current_closure_checks_passed': len(checks),
                      'diagnostic_completion_binding_pending': result['diagnostic_completion_binding_pending']}))


if __name__ == '__main__':
    main()
