#!/usr/bin/env python3
# Refresh REPORT-F3 after scheduled-runner closure integration, 2026-11-14. Inputs: current
# closure, original bytecode proof and ledger. Outputs: exclusive three-case
# proof with isolated valid/changed/missing artifact fixtures. Historical files
# stay untouched; no final closure, project imports, pytest or source edits.
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUT = SCRATCH / 'bytecode-closure-pin-verification-after-scheduled-runner'
TARGET = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def document(path, value):
    save(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    return pin(path)


def functions(source, scratch):
    tree = ast.parse(source.read_bytes(), filename=str(source))
    names = {'pin', 'document', 'checked_pin', 'require', 'ledger', 'close_bytecode'}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    namespace = {'Path': Path, 'hashlib': hashlib, 'json': json, 'ROOT': ROOT, 'OUT': scratch}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
    return namespace


def nested_records(value):
    result = [row[key] for row in value['cases'] for key in ('outcome', 'retained')]
    result.extend(value['original_counterexample'][key] for key in ('outcome', 'preserved'))
    assert len(result) == 8
    return result


def fixture(name, mutation=None, index=None):
    directory = OUT / name
    artifacts = directory / 'artifacts'
    artifacts.mkdir(parents=True)
    ledger = directory / 'review-bytecode.json'
    save(ledger, (SCRATCH / 'review-bytecode.json').read_bytes())
    value = json.loads((SCRATCH / 'bytecode-preservation-verification/result.json').read_bytes())
    value['ledger'] = pin(ledger)
    records = nested_records(value)
    for number, record in enumerate(records):
        source = Path(record['path'])
        copy = artifacts / (str(number) + source.suffix)
        save(copy, source.read_bytes())
        record.clear()
        record.update(pin(copy))
    if mutation is not None:
        target = Path(records[index]['path'])
        target.rename(target.with_name(target.name + '.original-retained'))
        if mutation == 'changed':
            save(target, b'changed isolated proof artifact\n')
        else:
            assert mutation == 'missing'
    proof = directory / 'bytecode-preservation-verification'
    proof.mkdir()
    document(proof / 'result.json', value)
    return directory, records


def main():
    assert not OUT.exists(), 'retain prior verification'
    OUT.mkdir()
    reviewed = OUT / 'reviewed-closure.py'
    save(reviewed, TARGET.read_bytes())
    originals = [pin(SCRATCH / 'bytecode-preservation-verification/result.json'),
                 pin(SCRATCH / 'review-bytecode.json')]
    original_value = json.loads((SCRATCH / 'bytecode-preservation-verification/result.json').read_bytes())
    originals.extend(pin(Path(row['path'])) for row in nested_records(original_value))
    # Retain proof of the original defect using actual prior close_bytecode.
    before = SCRATCH / 'bytecode-closure-pin-verification/before-closure.py'
    baseline = []
    for mode in ('changed', 'missing'):
        directory, _ = fixture('before-fix-' + mode, mode, 0)
        evidence, details = [], []
        functions(before, directory)['close_bytecode'](evidence, details)
        baseline.append({'mutation': mode, 'incorrectly_accepted': True, 'nested_index': 0})
    directory, records = fixture('valid')
    evidence, details = [], []
    functions(TARGET, directory)['close_bytecode'](evidence, details)
    exported = {row['path'] for row in evidence}
    assert all(record['path'] in exported for record in records), 'nested evidence was not exported'
    cases = [{'case': 'valid_nested_bytecode_artifact', 'passed': True,
              'nested_artifacts_checked': 8, 'nested_artifacts_exported': 8}]
    for mode, name in (('changed', 'changed_nested_bytecode_artifact'),
                       ('missing', 'missing_nested_bytecode_artifact')):
        checked = []
        for index in range(8):
            directory, records = fixture(mode + '-' + str(index), mode, index)
            try:
                functions(TARGET, directory)['close_bytecode']([], [])
            except (ValueError, FileNotFoundError) as error:
                assert records[index]['path'] in str(error), 'refusal did not identify changed/missing nested artifact'
                checked.append({'nested_index': index, 'refused': True, 'error_type': type(error).__name__})
            else:
                raise AssertionError('invalid nested bytecode evidence accepted: ' + mode + '-' + str(index))
        cases.append({'case': name, 'passed': True, 'nested_artifacts_checked': len(checked),
                      'checks': checked})
    # Check the actual saved proof too, without writing final closure output.
    actual_evidence, actual_details = [], []
    functions(TARGET, SCRATCH)['close_bytecode'](actual_evidence, actual_details)
    assert all(pin(Path(row['path'])) == row for row in originals), 'historical artifact changed'
    result = {'finding_id': 'G2-REVIEW-REPORT-F3', 'status': 'verified',
        'verified_entrypoint': 'close_bytecode', 'closure': pin(TARGET),
        'producer': pin(Path(__file__).resolve()), 'reviewed_source': pin(reviewed),
        'ledger': pin(SCRATCH / 'review-report-f3.json'),
        'cases': cases, 'passed': 3, 'failed': 0, 'original_counterexamples': baseline,
        'historical_artifacts_unchanged': originals, 'actual_saved_proof_accepted': True,
        'scope': 'Actual close_bytecode on isolated copies; eight nested artifact pins each checked/exported or refused. No final closure, project imports or pytest.'}
    output = document(OUT / 'result.json', result)
    print(json.dumps({'output': output, 'passed': 3, 'failed': 0,
                      'nested_artifacts_checked_per_case': 8}, indent=2))


if __name__ == '__main__':
    main()
