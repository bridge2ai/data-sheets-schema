#!/usr/bin/env python3
"""Correct and prove H2-RESUME-REPORT-F1, 2026-11-13.
Inputs: resumed handoff producer. Outputs: corrected producer and saved review
with synthetic failed-session counterexample in sibling scratch. No test runs.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-h2-resume-20261113/report-proof-review.json'
SOURCE = ROOT / 'scripts/adhoc/report_h2_resume_20261113.py'


def main():
    original = SOURCE.read_text()
    source = original
    replacements = [
        ("**case, 'cohort': cohort['name'], 'cohort_complete': cohort['complete'],\n                    'junit':", "**case, 'cohort': cohort['name'], 'cohort_complete': cohort['complete'],\n                    'cohort_returncode': cohort.get('outcome', {}).get('returncode'),\n                    'junit':"),
        ("case['status'] == 'passed' and case['cohort_complete'] for case in found)", "case['status'] == 'passed' and case['cohort_complete']\n        and case['cohort_returncode'] == 0 for case in found)"),
        ("    budget_review = read_json(budget_review_path)\n", "    budget_review = read_json(budget_review_path)\n    proof_review_path = SCRATCH / 'report-proof-review.json'\n    proof_review = read_json(proof_review_path)\n"),
        ("        'budget_origin_review': budget_review,", "        'report_proof_review': proof_review, 'report_proof_review_evidence': pin(proof_review_path),\n        'budget_origin_review': budget_review,"),
        ("        '- Supplemental budget retains", "        '- H2-RESUME-REPORT-F1: `' + str(proof_review_path) + '`; corrected and verified with a failed-session counterexample. Lead filing remains needed because helper GitHub writes are prohibited.',\n        '- Supplemental budget retains"),
    ]
    for before, after in replacements:
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    ast.parse(source)
    tree = ast.parse(source)
    selected = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)
                               and node.name in ('counts', 'test_proof')], type_ignores=[])
    namespace = {}
    exec(compile(selected, str(SOURCE), 'exec'), namespace)
    samples = []
    for code in (1, 0, None):
        cohort = {'name': 'synthetic', 'complete': True, 'evidence_mtime_ns': 1,
                  'outcome': {'returncode': code}, 'evidence': {'junit': {'path': 'synthetic-only'}},
                  'cases': [{'name': 'example', 'classname': 'example', 'status': 'passed'}]}
        result = namespace['test_proof']([cohort], 'example', 1)
        assert result['passed'] is (code == 0)
        assert result['counts']['passed'] == 1
        samples.append({'session_returncode': code, 'proof_passed': result['passed'],
                        'preserved_counts': result['counts']})
    record = {
        'finding_id': 'H2-RESUME-REPORT-F1', 'status': 'corrected-before-report',
        'finding': 'Issue-level proofs ignored the originating pytest returncode; green testcase records from a failed session could yield a fixed status.',
        'correction': 'Preserve testcase counts and record the originating returncode; accept a proof only when its complete session returned zero.',
        'review_type': 'Independent internal read-only review, followed by a separate correction pass.',
        'verification': samples, 'source': str(SOURCE),
        'before_sha256': hashlib.sha256(original.encode()).hexdigest(),
        'after_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'github_issue_number': None, 'lead_filing_needed': True,
        'filing_reason': 'Helper GitHub writes are prohibited; the lead must file this finding.',
    }
    assert not OUT.exists()
    SOURCE.write_text(source)
    raw = (json.dumps(record, indent=2) + '\n').encode()
    assert bytes([64]) not in raw
    OUT.write_bytes(raw)
    print(json.dumps({'path': str(OUT), 'sha256': hashlib.sha256(raw).hexdigest()}))


if __name__ == '__main__':
    main()
