#!/usr/bin/env python3
# Retain withdrawn G2-REVIEW-6217-F3, 2026-11-14, issue 6217 / PR 5968.
# Inputs: frozen engine and unapplied candidate. Output: new scratch review JSON.
# Read-only source analysis; no imports from the project, edits or test execution.
import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
REVISION = SCRATCH / 'proposal-6217-implementation'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def calls(path):
    source = path.read_text()
    tree = ast.parse(source)
    out = []
    for function in tree.body:
        if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for node in ast.walk(function):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == '_publication_subscription':
                        out.append({'enclosing_function': function.name, 'line': node.lineno,
                                    'text': source.splitlines()[node.lineno - 1].strip()})
    return out


def main():
    original = ROOT / 'src/data_sheets_schema/native_execution_orchestration.py'
    candidate = REVISION / 'candidate/src/data_sheets_schema/native_execution_orchestration.py'
    patch = REVISION / 'implementation.patch'
    if pin(patch)['sha256'] != '65dccec06fbf7a153d779f639bffd7765fde54cc689013d04070c64bd09139c9':
        raise ValueError('reviewed candidate patch changed')
    evidence = []
    for path in (original, candidate):
        found = calls(path)
        if any(row['enclosing_function'] in ('read_final', '_read_failure_diagnostic') for row in found):
            raise ValueError('the reviewed reader call path changed')
        lines = path.read_text().splitlines()
        direct = [{'line': index + 1, 'text': line.strip()}
                  for index, line in enumerate(lines)
                  if 'observation_verification = validate_saved_observations(' in line]
        if len(direct) != 1:
            raise ValueError('direct readback verification anchor changed')
        evidence.append({'source': pin(path), 'publication_helper_call_sites': found,
                         'reader_direct_validator_call': direct})
    record = {
        'finding_id': 'G2-REVIEW-6217-F3', 'status': 'disputed; withdrawn by reviewer',
        'original_claim': 'The public test would invoke its signal-raising _publication_subscription monkeypatch during independent read_final after prior signal handlers were restored.',
        'disposition': 'The stated call path is absent. read_final directly invokes validate_saved_observations; the diagnostic reader does not invoke the publication helper either. No demonstrated worker interruption and no source/test correction required.',
        'review_instruction': 'Root withdrew the finding after reading the direct validator call; retain the record without changing the candidate.',
        'source_analysis': evidence, 'reviewed_patch': pin(patch),
        'producer': pin(Path(__file__).resolve()), 'tests_run': [],
        'candidate_changes': [],
        'scope': 'Static direct-call analysis of the exact original and candidate engine; this is not dynamic test proof.'}
    destination = SCRATCH / 'review-6217-f3-withdrawn.json'
    with destination.open('x') as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps({'result': pin(destination), 'status': record['status']}))


if __name__ == '__main__':
    main()
