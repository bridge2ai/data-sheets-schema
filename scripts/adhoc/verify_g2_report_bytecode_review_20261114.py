#!/usr/bin/env python3
# Refresh G2 reporting proof after BYTECODE-F1 integration, 2026-11-14.
# Inputs: current report/closure, immutable prior proofs/snapshots, bytecode proof.
# Outputs: exclusive fresh F2 discovery and F1 nested-pin proofs plus integration.
# Reuses retained pure verifiers; no pytest, project imports, bytecode relocation,
# process signals, final report generation, source/test edits or commits.
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
REPORT = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
CLOSURE = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'
INTEGRATION = SCRATCH / 'report-bytecode-integration-20261114/index.json'
F1 = SCRATCH / 'report-closure-pin-verification-after-bytecode-review'
F2 = SCRATCH / 'report-cohort-discovery-after-bytecode-review'
PRIOR_F1 = ROOT / 'scripts/adhoc/verify_g2_report_discovery_fix_20261114.py'
PRIOR_F2 = ROOT / 'scripts/adhoc/verify_g2_cohort_discovery_20261114.py'


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def checked(record):
    assert pin(record['path']) == record, record['path']


def document(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def retained_verifier(path, replacements=()):
    # Only the retained standalone stdlib verifier is evaluated; its main guard
    # is false. New exclusive output globals and current producer provenance
    # are explicit, while its actual verification functions remain unchanged.
    source = path.read_text()
    for old, new in replacements:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    namespace = {'__name__': 'retained_pure_verifier', '__file__': str(Path(__file__).resolve())}
    exec(compile(source, str(path), 'exec'), namespace)
    return namespace


def main():
    assert not F1.exists() and not F2.exists(), 'retain prior verification'
    index = json.loads(INTEGRATION.read_bytes())
    for row in index['current_helpers']:
        checked(row)
    for row in index['before_helpers']:
        checked(row['snapshot'])
    for row in index['historical_proofs']:
        checked(row['artifact'])
        prior = json.loads(Path(row['artifact']['path']).read_bytes())
        for resolution in row['source_resolutions']:
            checked(resolution['snapshot'])
            old = prior[resolution['key']]
            assert old['path'] == resolution['source_name']
            assert all(old[field] == resolution['snapshot'][field] for field in ('bytes', 'sha256'))
    discovery = retained_verifier(PRIOR_F2)
    discovery['DEST'] = F2
    discovery['main']()
    nested = retained_verifier(PRIOR_F1, ((
        'report-cohort-discovery-20261114/verification/result.json',
        'report-cohort-discovery-after-bytecode-review/result.json'),))
    nested['OUTPUT'] = F1
    original_document = nested['document']
    def documented(path, value):
        if path == F1 / 'result.json':
            value = {**value, 'integration_history': pin(INTEGRATION),
                     'retained_verifier_sources': [pin(PRIOR_F1), pin(PRIOR_F2)]}
        original_document(path, value)
    nested['document'] = documented
    nested['main']()
    tree = ast.parse(CLOSURE.read_bytes(), filename=str(CLOSURE))
    names = {'pin', 'document', 'checked_pin', 'require', 'ledger', 'close_bytecode'}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    namespace = {'Path': Path, 'json': json, 'hashlib': hashlib, 'ROOT': ROOT, 'OUT': SCRATCH}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(CLOSURE), 'exec'), namespace)
    evidence, details = [], []
    reason = namespace['close_bytecode'](evidence, details)
    assert details[0]['cases'] == details[0]['passed'] == 3
    for record in evidence:
        checked(record)
    for row in index['current_helpers']:
        checked(row)
    result = {'finding_id': 'G2-REVIEW-BYTECODE-F1', 'status': 'verified',
        'verified_entrypoint': 'close_bytecode', 'reason': reason, 'details': details,
        'evidence': evidence, 'reporter': pin(REPORT), 'closure': pin(CLOSURE),
        'producer': pin(Path(__file__).resolve()), 'integration_history': pin(INTEGRATION),
        'report_pin_proof': pin(F1 / 'result.json'), 'discovery_proof': pin(F2 / 'result.json'),
        'historical_proof_policy': 'Original proofs remain unchanged. Their old live-source identities are resolved to matching immutable snapshots in the integration index; fresh companions bind current helpers.',
        'scope': 'Actual standalone closure function consumed the saved three-case synthetic bytecode proof. No source bytecode move, project tests or final report execution.'}
    document(F1 / 'bytecode-closure-integration.json', result)
    print(json.dumps({'integration': pin(F1 / 'bytecode-closure-integration.json'),
        'report_pin_proof': result['report_pin_proof'], 'discovery_proof': result['discovery_proof']}))


if __name__ == '__main__':
    main()
