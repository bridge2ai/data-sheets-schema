#!/usr/bin/env python3
# Verify G2 freshness reporting bindings while the serial canary is active, 2026-11-14.
# Inputs: frozen report/closure, completed interrupted cohort, fresh proof records,
# and only the active canary's immutable command. Output: pending-check companion.
# The earlier refresh retained F1/F2 then refused the empty active log. Preserve it.
# No final discovery/closure/report, project imports, pytest, source edits or commits.
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
REPORT = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
CLOSURE = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'
OUT = SCRATCH / 'report-closure-pin-verification-after-engine-freshness'


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    target = OUT / 'engine-freshness-reporting-verification.json'
    assert not target.exists()
    before = [pin(REPORT), pin(CLOSURE)]
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
    required = 'tests/test_native_shared_execution_failure.py'
    canary_path = SCRATCH / 'freshness-serial-canary/command.json'
    canary = json.loads(canary_path.read_bytes())
    node = required + '::test_v2_publication_failure_preserves_first_error[published.json]'
    assert node in canary['command'] and required not in canary['command']
    assert module['selects'](canary, required, None) is False, 'node-only canary unexpectedly qualifies as a whole file'
    identity = 'G2-REVIEW-ENGINE-FRESHNESS-F1'
    original_directory = SCRATCH / 'final-engine-dependents'
    row, details = module['close'](identity, lambda evidence, details:
        module['close_engine_freshness']([original_directory], head, evidence, details))
    assert row['status'] == 'not_verified' and row['reason'] == 'latest selected cohort failed', row
    report = runpy.run_path(str(REPORT))
    original = report['load_cohort'](original_directory, head, {})
    assert original['returncode'] == 2 and original['interrupted'] is True
    assert original['complete'] is original['eligible'] is False
    assert original['junit_entry_counts']['total'] == 241
    assert original['counts'] == {'total': 241, 'passed': 0, 'failed': 3, 'error': 0, 'skipped': 0, 'unconfirmed': 238}
    assert original['pytest_summary']['counts'] == {'failed': 3, 'passed': 237}
    assert original['junit_entries_without_completed_log_outcome'] == 1
    proof = report['file_proof']([original], required)
    assert proof['passed'] is False
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
    for record in before:
        assert pin(record['path']) == record
    result = {'status': 'verified', 'reporter': pin(REPORT), 'closure': pin(CLOSURE),
        'producer': pin(Path(__file__).resolve()),
        'integration_history': pin(SCRATCH / 'report-engine-freshness-integration-20261114/index.json'),
        'prior_partial_refresh': {'producer': pin(ROOT / 'scripts/adhoc/verify_g2_engine_freshness_reporting_20261114.py'),
            'completed': False,
            'retained_phase': 'F1/F2 and bytecode integration proofs saved before subsequent discovery',
            'subsequent_refusal': 'empty evidence in the active freshness-serial-canary/pytest.log',
            'policy_changed': False},
        'current_closure_checks': checks, 'current_closure_checks_passed': len(checks),
        'engine_freshness': {'closure': row, 'details': details, 'reported_finding': finding,
                            'whole_file_proof': proof, 'verified_rerun': False},
        'node_only_canary': {'command': pin(canary_path), 'node': node, 'whole_file_selector': False,
                            'outcome_or_log_read': False, 'pass_claimed': False},
        'interrupted_cohort': {'evidence': original['evidence'], 'counts': original['counts'],
            'junit_entry_counts': original['junit_entry_counts'], 'completed_log_summary': original['pytest_summary'],
            'unmatched_aggregate_entries': original['junit_entries_without_completed_log_outcome'],
            'eligible': original['eligible'], 'returncode': original['returncode']},
        'report_pin_proof': pin(OUT / 'result.json'),
        'discovery_proof': pin(SCRATCH / 'report-cohort-discovery-after-engine-freshness/result.json'),
        'scope': 'Actual standalone helper entrypoints against the completed interrupted cohort; recorded node-only canary selection checked separately. No generic final discovery over active partial artifacts, no acceptance from the canary, no failure erased or cause correction claimed.'}
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    with target.open('xb') as stream:
        stream.write(raw)
    assert target.read_bytes() == raw
    print(json.dumps({'verification': pin(target), 'current_closure_checks_passed': len(checks),
                     'verified_rerun': False, 'canary_whole_file_selector': False}))


if __name__ == '__main__':
    main()
