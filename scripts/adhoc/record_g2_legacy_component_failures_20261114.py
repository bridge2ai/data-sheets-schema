#!/usr/bin/env python3
# Retain actual G2 legacy acceptance failures, issues 6217 / PR 5968, 2026-11-14.
# Inputs: completed final-components command/outcome/log/JUnit, prior immutable
# artifact/source observations. Outputs: frozen evidence and formal review ledger.
# No source/test changes, test execution, process monitoring or external writes.
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
COHORT = SCRATCH / 'final-components'
OUTPUT = SCRATCH / 'legacy-component-failures-20261114'
STOP = 'native attempt deadline elapsed; retain all incomplete charge reservations'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)


def main():
    OUTPUT.mkdir()
    artifacts = {}
    for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log'):
        source = COHORT / name
        destination = OUTPUT / name
        save(destination, source.read_bytes())
        artifacts[name] = {'original_path': str(source), 'snapshot': pin(destination)}
    command = json.loads((OUTPUT / 'command.json').read_bytes())
    outcome = json.loads((OUTPUT / 'outcome.json').read_bytes())
    log = (OUTPUT / 'pytest.log').read_text()
    cases = []
    for node in ET.parse(OUTPUT / 'pytest.xml').iter('testcase'):
        status, detail = 'passed', None
        for tag, label in (('failure', 'failed'), ('error', 'error'), ('skipped', 'skipped')):
            element = node.find(tag)
            if element is not None:
                status = label
                detail = {'message': element.get('message', ''), 'text': element.text or ''}
                break
        cases.append({'classname': node.get('classname'), 'name': node.get('name'),
                      'seconds': node.get('time'), 'status': status, 'detail': detail})
    census = Counter(row['status'] for row in cases)
    counts = {'total': len(cases), **{name: census[name] for name in ('passed', 'failed', 'error', 'skipped')}}
    assert outcome['returncode'] == 1
    assert outcome['counts'] == {name: counts[name] for name in ('total', 'failed', 'error', 'skipped')}
    failed = [row for row in cases if row['status'] == 'failed']
    errors = [row for row in cases if row['status'] == 'error']
    assert len(failed) == 1 and len(errors) == 4
    assert failed[0]['name'] == 'test_actual_closed_consumer_real_helpers_complete[no_correction]'
    assert failed[0]['classname'].endswith('test_native_execution')
    assert all(row['classname'].endswith('test_native_receipt_origin_reporting') for row in errors)
    assert all(STOP in row['detail']['text'] for row in failed + errors)
    assert all('completed_origin_case' in row['detail']['text'] for row in errors)
    trace_path = SCRATCH / 'legacy-deadline-static-trace-6217/analysis.json'
    trace = json.loads(trace_path.read_bytes())
    assert trace['after_commit'] == command['head']
    failure_artifact, = [row for row in trace['saved_deadline_stops'] if 'test_actual_closed_consumer_re1' in row['observed_path']]
    fixture_artifact, = [row for row in trace['saved_deadline_stops'] if '/popen-gw0/origin-consumer1/' in row['observed_path']]
    for row in (failure_artifact, fixture_artifact):
        assert pin(Path(row['snapshot']['path'])) == row['snapshot']
        assert row['first_stop'] == STOP and row['signals_received'] == []
    common = {
        'status': 'open; unresolved required verification failure',
        'lead_filing_needed': True, 'github_issue_number': None,
        'filing_reason': 'Helper GitHub writes are prohibited; the lead retains filing responsibility.',
        'observed_first_stop': STOP,
        'baseline_reproduction_established': False,
        'internal_or_timing_cause_established': False,
        'regression_assessment': 'No concrete 6217 regression demonstrated. The relevant legacy launch/reader and fixture functions are unchanged across 6217; its new record-only callback is unused by legacy launch. Saved deadline outcomes report no received signals. This does not reproduce the pre-6217 baseline or prove the cause of the deadline stop.',
        'source_proof': pin(trace_path),
        'change_policy': 'Retain deadlines, validation and evidence requirements. No source or test fix is justified by timing speculation.'}
    findings = [
        {**common, 'finding_id': 'G2-REVIEW-LEGACY-F1',
         'finding': 'Required legacy no_correction completion witness failed its runtime-gates assertion after the registered native attempt deadline elapsed.',
         'cases': failed, 'artifact_proof': failure_artifact,
         'assertion_site': {'path': 'tests/test_native_execution.py', 'line': 111},
         'required_clean_full_file': 'tests/test_native_execution.py',
         'verification_plan': 'Root will run the exact failed node alone at the same source head and unchanged limits as a serial canary, then decide the full-file run. No rerun result is claimed here.'},
        {**common, 'finding_id': 'G2-REVIEW-LEGACY-F2',
         'finding': 'The native_attribution module fixture failed its completion assertion, producing four setup errors before the consumer/readback test bodies ran.',
         'cases': errors, 'artifact_proof': fixture_artifact,
         'assertion_site': {'path': 'tests/test_native_receipt_origin_reporting.py', 'line': 335},
         'required_clean_full_file': 'tests/test_native_receipt_origin_reporting.py',
         'verification_plan': 'Require an independently completed clean full-file run and the affected cases passed; a different worker fixture succeeding does not erase these errors.'}]
    summaries = [line for line in log.splitlines() if ' passed' in line and ' errors in ' in line]
    assert len(summaries) == 1
    record = {'producer': pin(Path(__file__).resolve()), 'cohort': 'final-components',
        'source_head': command['head'], 'command_evidence': artifacts['command.json'],
        'outcome': outcome, 'junit_counts': counts, 'pytest_summary': summaries[0],
        'artifacts': artifacts, 'findings': findings,
        'scope': 'Completed saved pytest diagnostics and immutable source/artifact observations. The four setup errors share a cached failing module fixture on gw0; no claim that four independent child runs failed. The common observed stop does not establish a common internal cause across the two findings.',
        'tests_run_by_this_helper': [], 'source_or_test_changes': []}
    destination = SCRATCH / 'review-legacy-component-failures.json'
    save(destination, (json.dumps(record, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'ledger': pin(destination), 'counts': counts,
                      'returncode': outcome['returncode'], 'findings': [row['finding_id'] for row in findings]}))


if __name__ == '__main__':
    main()
