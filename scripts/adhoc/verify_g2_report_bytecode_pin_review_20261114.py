#!/usr/bin/env python3
# Refresh G2 report proof after REPORT-F3 nested bytecode pins, 2026-11-14.
# Inputs: corrected helpers, retained pure verifier, nested bytecode pin proof.
# Outputs: exclusive after-bytecode-pin-review F1/F2 and closure integration.
# No pytest, project imports, bytecode relocation, final handoff or source edits.
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
DRIVER = ROOT / 'scripts/adhoc/verify_g2_report_bytecode_review_20261114.py'
CLOSURE = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'
F1 = SCRATCH / 'report-closure-pin-verification-after-bytecode-pin-review'
F2 = SCRATCH / 'report-cohort-discovery-after-bytecode-pin-review'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    source = DRIVER.read_text()
    old = "'report-cohort-discovery-after-bytecode-review/result.json'"
    new = "'report-cohort-discovery-after-bytecode-pin-review/result.json'"
    assert source.count(old) == 1
    source = source.replace(old, new)
    namespace = {'__name__': 'retained_reporting_driver', '__file__': str(Path(__file__).resolve())}
    exec(compile(source, str(DRIVER), 'exec'), namespace)
    namespace.update(INTEGRATION=SCRATCH / 'report-bytecode-pin-integration-20261114/index.json', F1=F1, F2=F2)
    namespace['main']()
    tree = ast.parse(CLOSURE.read_bytes(), filename=str(CLOSURE))
    names = {'pin', 'document', 'checked_pin', 'require', 'ledger', 'close_bytecode_pins'}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    check = {'Path': Path, 'json': json, 'hashlib': hashlib, 'ROOT': ROOT, 'OUT': SCRATCH}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(CLOSURE), 'exec'), check)
    evidence, details = [], []
    reason = check['close_bytecode_pins'](evidence, details)
    assert details[0]['cases'] == details[0]['passed'] == 3
    result = {'finding_id': 'G2-REVIEW-REPORT-F3', 'status': 'verified',
        'verified_entrypoint': 'close_bytecode_pins', 'reason': reason,
        'details': details, 'evidence': evidence, 'closure': pin(CLOSURE),
        'producer': pin(Path(__file__).resolve()), 'retained_driver': pin(DRIVER),
        'report_pin_proof': pin(F1 / 'result.json'), 'discovery_proof': pin(F2 / 'result.json'),
        'scope': 'Actual standalone closure consumed the saved valid/changed/missing eight-artifact proof. No final closure/handoff, source-cache move or project test execution.'}
    namespace['document'](F1 / 'bytecode-pin-closure-integration.json', result)
    print(json.dumps({'integration': pin(F1 / 'bytecode-pin-closure-integration.json'),
                     'report_pin_proof': result['report_pin_proof'], 'discovery_proof': result['discovery_proof']}))


if __name__ == '__main__':
    main()
