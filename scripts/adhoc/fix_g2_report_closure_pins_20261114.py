#!/usr/bin/env python3
"""Correct and verify G2-REVIEW-REPORT-F1 using pure scratch cases, 2026-11-14.

Inputs: current G2 report helper. Outputs: retained before/after source, finding
ledger, and three nested-pin counterexamples in sibling scratch-g2-20261114.
Only the report helper changes. No project imports, pytest, handoff generation,
production/test edits, native processes, host probes or GitHub writes.
"""
import ast
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
TARGET = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write_new(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    before = TARGET.read_bytes()
    text = before.decode()
    anchor = "    closure = read_json(closure_path) if closure_path.is_file() else None\n"
    roster = "                'offline-power-fixture-review.json')\n"
    assert text.count(anchor) == text.count(roster) == 1
    assert 'check_nested_pins(closure)' not in text
    original = SCRATCH / 'review-report-before.py'
    ledger = SCRATCH / 'review-report.json'
    corrected = SCRATCH / 'review-report-corrected-source.py'
    evidence = SCRATCH / 'report-closure-pin-verification'
    assert not evidence.exists()
    write_new(original, before)
    finding = {
        'finding_id': 'G2-REVIEW-REPORT-F1', 'priority': 'P3',
        'status': 'correction-and-verification-pending',
        'finding': 'The report validated per-finding closure evidence but did not verify separate nested review_6224 and producer pins before retaining the closure document.',
        'required_fix': 'Validate all nested pins immediately after loading the closure; require actual files and matching hashes before reporting.',
        'before_source': pin(original),
        'required_counterexamples': ['valid_nested_artifact', 'changed_nested_artifact', 'missing_nested_artifact'],
        'lead_filing_needed': True, 'github_issue_number': None,
        'filing_reason': 'Helper GitHub writes are prohibited; the lead must file this finding.',
    }
    write_new(ledger, (json.dumps(finding, indent=2) + '\n').encode())
    text = text.replace(anchor, anchor + '    if closure is not None:\n        check_nested_pins(closure)\n', 1)
    text = text.replace(roster, "                'offline-power-fixture-review.json', 'review-report.json')\n", 1)
    tree = ast.parse(text, filename=str(TARGET))
    TARGET.write_text(text)
    assert TARGET.read_text() == text
    write_new(corrected, TARGET.read_bytes())
    evidence.mkdir()
    fixture = evidence / 'fixture'
    fixture.mkdir()
    artifact = fixture / 'review-6224-final.json'
    write_new(artifact, b'{"finding":"retained scratch review"}\n')
    closure_path = fixture / 'final-review-closure.json'
    closure = {'findings': [], 'review_6224': pin(artifact), 'producer': pin(Path(__file__).resolve())}
    write_new(closure_path, (json.dumps(closure, indent=2) + '\n').encode())
    functions = {'sha', 'pin', 'read_json', 'checked_pin', 'check_nested_pins', 'review_ledger'}
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in functions]
    assert {node.name for node in selected} == functions
    namespace = {'Path': Path, 'hashlib': hashlib, 'json': json,
                 'SCRATCH': fixture, 'REVIEW_FILES': (), 'FINDING_TESTS': {}}
    # Execute only these stdlib-only function definitions, never module main.
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(TARGET), 'exec'), namespace)
    actual = namespace['review_ledger']([], {})
    assert actual['closure'] == closure and actual['findings'] == []
    cases = [{'case': 'valid_nested_artifact', 'passed': True, 'result': 'accepted'}]
    artifact.rename(fixture / 'review-original-retained.json')
    write_new(artifact, b'{"finding":"changed scratch review"}\n')
    try:
        namespace['review_ledger']([], {})
    except AssertionError as error:
        cases.append({'case': 'changed_nested_artifact', 'passed': True,
                      'result': 'refused', 'reason': str(error)})
    else:
        raise AssertionError('changed nested artifact was accepted')
    artifact.rename(fixture / 'review-changed-retained.json')
    try:
        namespace['review_ledger']([], {})
    except AssertionError as error:
        cases.append({'case': 'missing_nested_artifact', 'passed': True,
                      'result': 'refused', 'reason': str(error)})
    else:
        raise AssertionError('missing nested artifact was accepted')
    result = {'finding_id': finding['finding_id'], 'status': 'verified',
        'verified_entrypoint': 'review_ledger', 'reporter': pin(TARGET),
        'reviewed_source': pin(corrected), 'producer': pin(Path(__file__).resolve()),
        'ledger': pin(ledger), 'cases': cases, 'passed': len(cases), 'failed': 0,
        'python': sys.version,
        'retained_fixture_bytes': [pin(path) for path in sorted(fixture.iterdir())],
        'scope': 'Pure report-function counterexamples only. No project imports, pytest or report output execution. The expected artifact is intentionally absent in the final missing-file case; both prior byte versions remain retained.'}
    destination = evidence / 'result.json'
    write_new(destination, (json.dumps(result, indent=2) + '\n').encode())
    assert TARGET.read_bytes() == corrected.read_bytes()
    print(json.dumps({'verification': pin(destination), 'ledger': pin(ledger),
                      'reporter': pin(TARGET), 'producer': pin(Path(__file__).resolve()),
                      'passed': result['passed'], 'failed': result['failed']}))


if __name__ == '__main__':
    main()
