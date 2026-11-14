#!/usr/bin/env python3
# Integrate G2-REVIEW-BYTECODE-F1 into retained reporting, 2026-11-14.
# Inputs: current report/closure helpers; existing F1/F2 proof and source snapshots.
# Outputs: immutable pre-edit snapshots/index; bounded report/closure edits only.
# Does not run tests, move bytecode, generate the handoff or modify project source.
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUTPUT = SCRATCH / 'report-bytecode-integration-20261114'
REPORT = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
CLOSURE = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def replace_once(body, old, new):
    assert body.count(old) == 1, old
    return body.replace(old, new)


def main():
    assert not OUTPUT.exists(), 'retain earlier integration evidence'
    original = {path: path.read_bytes() for path in (REPORT, CLOSURE)}
    report = original[REPORT].decode()
    closure = original[CLOSURE].decode()
    report = replace_once(report, "'review-legacy-component-failures-v2.json')",
                          "'review-legacy-component-failures-v2.json', 'review-bytecode.json')")
    old_f1 = 'report-closure-pin-verification-after-discovery-fix/result.json'
    fresh_f1 = 'report-closure-pin-verification-after-bytecode-review/result.json'
    report = replace_once(report, old_f1, fresh_f1)
    closure = replace_once(closure, old_f1, fresh_f1)
    closure = replace_once(closure, 'report-cohort-discovery-20261114/verification/result.json',
                           'report-cohort-discovery-after-bytecode-review/result.json')
    function = '''def close_bytecode(evidence, details):
    identity = 'G2-REVIEW-BYTECODE-F1'
    ledger(identity, 'review-bytecode.json', evidence)
    result = document(OUT / 'bytecode-preservation-verification/result.json', evidence)
    require(result['finding_id'] == identity and result['status'] == 'verified'
            and result['verified_entrypoint'] == 'rename_and_verify',
            'bytecode interruption verification is incomplete')
    for name in ('helper', 'producer', 'reviewed_source', 'ledger'):
        checked_pin(result[name], evidence)
    require(Path(result['helper']['path']) == ROOT / 'scripts/adhoc/preserve_g2_source_bytecode_20261114.py'
            and Path(result['ledger']['path']) == OUT / 'review-bytecode.json',
            'bytecode proof does not name the current helper and original ledger')
    require(result['helper']['sha256'] == result['reviewed_source']['sha256']
            and result['helper']['bytes'] == result['reviewed_source']['bytes'],
            'bytecode proof snapshot differs from the current helper')
    expected = {'interruption_after_rename', 'interruption_before_rename', 'ambiguous_locations'}
    rows = result['cases']
    require(result['passed'] == 3 and result['failed'] == 0 and len(rows) == 3
            and {row['case'] for row in rows} == expected
            and all(row['passed'] is True for row in rows),
            'bytecode interruption counterexamples are incomplete or failing')
    details.append({'cases': 3, 'passed': 3, 'entrypoint': 'rename_and_verify',
                    'scope': 'Pure synthetic filesystem interruption proof; actual bytecode preservation is a separate action.'})
    return 'Synthetic interruption checks verify fresh location evidence after rename, before rename and for ambiguous locations. Actual source bytecode preservation is not inferred; lead filing remains required.'


'''
    closure = replace_once(closure, 'def review_6224(head):', function + 'def review_6224(head):')
    closure = replace_once(closure,
        "('G2-REVIEW-REPORT-F2', close_report_discovery)):",
        "('G2-REVIEW-REPORT-F2', close_report_discovery),\n                             ('G2-REVIEW-BYTECODE-F1', close_bytecode)):")
    changed = {REPORT: report.encode(), CLOSURE: closure.encode()}
    for path, body in changed.items():
        ast.parse(body, filename=str(path))
    OUTPUT.mkdir()
    snapshots = []
    for path, body in original.items():
        snapshot = OUTPUT / ('before-' + path.name)
        save(snapshot, body)
        snapshots.append({'source_name': str(path), 'snapshot': pin(snapshot)})
    historical = []
    for name, resolutions in (
        (old_f1, {'reporter': SCRATCH / 'report-closure-pin-verification-after-discovery-fix/reviewed-report-source.py'}),
        ('report-cohort-discovery-20261114/verification/result.json', {
            'reporter': SCRATCH / 'report-cohort-discovery-20261114/verification/reviewed-report_g2_launch_fixes_20261114.py',
            'closure': SCRATCH / 'report-cohort-discovery-20261114/verification/reviewed-record_g2_final_review_20261114.py'})):
        path = SCRATCH / name
        value = json.loads(path.read_bytes())
        source_rows = []
        for key, snapshot in resolutions.items():
            recorded = value[key]
            actual = pin(snapshot)
            assert all(recorded[field] == actual[field] for field in ('bytes', 'sha256'))
            source_rows.append({'key': key, 'source_name': recorded['path'], 'snapshot': actual})
        historical.append({'artifact': pin(path), 'source_resolutions': source_rows})
    for path, body in changed.items():
        assert path.read_bytes() == original[path]
        path.write_bytes(body)
        assert path.read_bytes() == body
    index = {'finding_id': 'G2-REVIEW-BYTECODE-F1', 'before_helpers': snapshots,
        'historical_proofs': historical,
        'current_helpers': [pin(path) for path in changed], 'producer': pin(Path(__file__).resolve()),
        'scope': 'Reporting integration only. Prior proof artifacts and their immutable source snapshots remain unchanged; fresh current-helper proofs are required.'}
    save(OUTPUT / 'index.json', (json.dumps(index, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'index': pin(OUTPUT / 'index.json'), 'helpers': index['current_helpers']}))


if __name__ == '__main__':
    main()
