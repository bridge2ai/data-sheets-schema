#!/usr/bin/env python3
# Refresh G2 reporting proof after scheduled-runner integration, 2026-11-14.
# Inputs: frozen report/closure, retained prior proofs and static driver correction.
# Outputs: fresh F1/F2 pin/discovery companions and an actual pending-runtime check.
# No project imports, pytest, canary/driver execution, source edits or final report.
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
REPORT = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
CLOSURE = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'
DRIVER = ROOT / 'scripts/adhoc/verify_g2_report_bytecode_review_20261114.py'
F1 = SCRATCH / 'report-closure-pin-verification-after-scheduled-runner'
F2 = SCRATCH / 'report-cohort-discovery-after-scheduled-runner'
INTEGRATION = SCRATCH / 'report-scheduled-runner-integration-20261114'


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
    previous_path = SCRATCH / 'report-f4-reuse-auxiliary-integration-20261114/index.json'
    previous = json.loads(previous_path.read_bytes())
    historical = list(previous['historical_proofs'])
    for relative, resolutions in (
        ('report-closure-pin-verification-after-f4-reuse-auxiliary',
         (('reporter', REPORT, 'reviewed-report-source.py'),)),
        ('report-cohort-discovery-after-f4-reuse-auxiliary',
         (('reporter', REPORT, 'reviewed-report_g2_launch_fixes_20261114.py'),
          ('closure', CLOSURE, 'reviewed-record_g2_final_review_20261114.py')))):
        directory = SCRATCH / relative
        historical.append({'artifact': pin(directory / 'result.json'),
            'source_resolutions': [{'key': key, 'source_name': str(source),
                                    'snapshot': pin(directory / snapshot)}
                                   for key, source, snapshot in resolutions]})
    before = [
        {'source_name': str(REPORT), 'snapshot': pin(SCRATCH / 'scheduled-runner-report-20261114/before-reporter.py')},
        {'source_name': str(CLOSURE), 'snapshot': pin(SCRATCH / 'scheduled-runner-closure-20261114/before-closure.py')}]
    for old, retained in zip(previous['current_helpers'], before):
        assert old['path'] == retained['source_name']
        assert all(old[key] == retained['snapshot'][key] for key in ('bytes', 'sha256'))
    INTEGRATION.mkdir()
    index = {'finding_id': 'G2-REVIEW-SCHEDULED-RUNNER-F1',
        'before_helpers': before, 'historical_proofs': historical,
        'current_helpers': [pin(REPORT), pin(CLOSURE)], 'previous_integration': pin(previous_path),
        'static_correction': pin(SCRATCH / 'scheduled-runner-review-20261114/correction.json'),
        'producer': pin(Path(__file__).resolve()),
        'scope': 'Only scheduled-runner finding integration. Historical helper identities resolve to immutable snapshots; runtime remains separately gated.'}
    document(INTEGRATION / 'index.json', index)
    source = DRIVER.read_text()
    for old, new in (
        ("'scripts/adhoc/verify_g2_cohort_discovery_20261114.py'",
         "'scripts/adhoc/verify_g2_cohort_discovery_auxiliary_20261114.py'"),
        ("'report-cohort-discovery-after-bytecode-review/result.json'",
         "'report-cohort-discovery-after-scheduled-runner/result.json'")):
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
        ('G2-REVIEW-BYTECODE-F1', 'close_bytecode')):
        row, details = module['close'](identity, module[name])
        assert row['status'] == 'verified', row
        checks.append({'result': row, 'details': details})
    assert not (SCRATCH / 'scheduled-canary/command.json').exists(), 'runtime state changed; retain this proof before reassessing'
    row, details = module['close']('G2-REVIEW-SCHEDULED-RUNNER-F1', module['close_scheduled_runner'])
    assert row['status'] == 'not_verified' and 'scheduled-canary/command.json' in row['reason'], row
    assert details == [{'static_correction_verified': True, 'runtime_proof_separate': True,
                        'historical_static_record_runtime_verified': False}], details
    report = runpy.run_path(str(REPORT))
    review = report['review_ledger']
    globals_ = review.__globals__
    original_roster = globals_['REVIEW_FILES']
    globals_['REVIEW_FILES'] = ('scheduled-runner-review-20261114/correction.json',)
    try:
        ledger = review([], {})
    finally:
        globals_['REVIEW_FILES'] = original_roster
    finding, = ledger['findings']
    assert finding['id'] == row['id'] and finding['closed_by_verified_declaration'] is False
    assert finding['reported_status'] == 'static correction retained; scheduled canary runtime verification pending; lead filing required'
    for record in index['current_helpers']:
        assert pin(record['path']) == record
    result = {'status': 'verified', 'reporter': pin(REPORT), 'closure': pin(CLOSURE),
        'producer': pin(Path(__file__).resolve()), 'integration_history': pin(INTEGRATION / 'index.json'),
        'current_closure_checks': checks, 'current_closure_checks_passed': len(checks),
        'scheduled_runner': {'closure': row, 'details': details, 'reported_finding': finding,
                             'runtime_verified': False, 'canary_not_run_by_this_producer': True},
        'report_pin_proof': pin(F1 / 'result.json'), 'discovery_proof': pin(F2 / 'result.json'),
        'scope': 'Actual standalone helper entrypoints consumed retained proofs. Static correction succeeds but absent scheduled-canary evidence keeps runtime closure not_verified and report wording pending. No final report/closure, project tests or driver execution.'}
    path = F1 / 'scheduled-runner-reporting-verification.json'
    document(path, result)
    print(json.dumps({'verification': pin(path), 'report_pin_proof': result['report_pin_proof'],
                     'discovery_proof': result['discovery_proof'], 'runtime_verified': False}))


if __name__ == '__main__':
    main()
