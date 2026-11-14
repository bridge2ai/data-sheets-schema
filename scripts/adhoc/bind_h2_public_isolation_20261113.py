#!/usr/bin/env python3
"""Close H2-RESUME-REPORT-F2: bind reported correction to verified JUnit.
Inputs: handoff producer source. Outputs: bounded source edit and scratch review.
Issue 6200 provenance, 2026-11-13. No tests, launches, or external publication.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'scripts/adhoc/report_h2_resume_20261113.py'


def main():
    raw = PATH.read_text()
    insertion = '''def require_isolation_binding(public, cohorts, isolation):
    assert isolation['status'] == 'corrected-by-serial-rerun'
    selected, = [row for row in public if row['name'] == 'correction']
    assert selected['cohort'] == isolation['required_rerun_cohort']
    cohort, = [row for row in cohorts if row['name'] == selected['cohort']]
    expected = isolation['rerun_interval']['evidence']
    assert cohort['evidence']['junit'] == expected
    assert pin(expected['path']) == expected


'''
    assert 'def require_isolation_binding(' not in raw
    raw = raw.replace('def lane_proof(cohorts, name):', insertion + 'def lane_proof(cohorts, name):', 1)
    needle = "    assert isolation['status'] == 'corrected-by-serial-rerun'\n    callback_analysis_path"
    assert needle in raw
    raw = raw.replace(needle, "    require_isolation_binding(public, cohorts, isolation)\n    isolation_binding_path = SCRATCH / 'public-isolation-binding-review.json'\n    isolation_binding = read_json(isolation_binding_path)\n    callback_analysis_path", 1)
    needle = "        'public_isolation_review': isolation, 'public_isolation_review_evidence': pin(isolation_path),"
    assert needle in raw
    raw = raw.replace(needle, needle + "\n        'public_isolation_binding_review': isolation_binding,\n        'public_isolation_binding_review_evidence': pin(isolation_binding_path),", 1)
    needle = "        '- Supplemental budget retains an explicit local src PYTHONPATH override"
    assert needle in raw
    raw = raw.replace(needle, "        '- H2-RESUME-REPORT-F2: `' + str(isolation_binding_path) + '`; the selected correction invocation and JUnit bytes are bound to the isolation review. Lead filing remains needed because helper GitHub writes are prohibited.',\n" + needle, 1)
    PATH.write_text(raw)
    spec = importlib.util.spec_from_file_location('checked_h2_report', PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pinned = module.pin(module.SCRATCH / 'correction/pytest.xml')
    public = [{'name': 'correction', 'cohort': 'verified-fixture'}]
    cohorts = [{'name': 'verified-fixture', 'evidence': {'junit': pinned}}]
    isolation = {'status': 'corrected-by-serial-rerun', 'required_rerun_cohort': 'verified-fixture',
                 'rerun_interval': {'evidence': pinned}}
    module.require_isolation_binding(public, cohorts, isolation)
    outcomes = {}
    for name in ('wrong-cohort', 'changed-junit-hash', 'changed-junit-path'):
        changed_public, changed_cohorts = deepcopy(public), deepcopy(cohorts)
        if name == 'wrong-cohort':
            changed_public[0]['cohort'] = 'original'
        elif name == 'changed-junit-hash':
            changed_cohorts[0]['evidence']['junit']['sha256'] = '0' * 64
        else:
            changed_cohorts[0]['evidence']['junit']['path'] = str(module.SCRATCH / 'preload.xml')
        try:
            module.require_isolation_binding(changed_public, changed_cohorts, isolation)
        except AssertionError:
            outcomes[name] = 'rejected'
        else:
            raise AssertionError(name + ' was accepted')
    result = {'finding_id': 'H2-RESUME-REPORT-F2', 'status': 'corrected',
        'finding': 'Mutable evidence mtimes could select a public invocation different from the one certified by the isolation review.',
        'correction': 'The report requires the selected correction cohort and exact JUnit pin to equal the verified isolation record, and rechecks the file bytes.',
        'verification': {'matching-fixture': 'accepted', **outcomes},
        'fixture_evidence': pinned, 'producer': module.pin(PATH),
        'lead_filing_needed': True, 'github_issue_number': None,
        'filing_reason': 'Helper GitHub writes are prohibited; lead filing is required.'}
    destination = module.SCRATCH / 'public-isolation-binding-review.json'
    with destination.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(module.pin(destination)))


if __name__ == '__main__':
    main()
