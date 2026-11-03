#!/usr/bin/env python3
"""PR #5213 round four: persist the source-discovered RunSpec boundary inventory.

2026-11-03. Input: an explicit source tree. Output: one fresh JSON report with
source/utility hashes, every candidate and unresolved source-docstring contract.
This parses source only; it does not import or execute generation modules/tests.
"""
import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    output = args.output
    if not output.is_absolute() or '..' in output.parts or output.exists() or output.is_symlink():
        raise ValueError('fresh absolute output required')
    if output.parent.resolve(strict=True) != output.parent or output.is_relative_to(source):
        raise ValueError('physical output parent outside source required')
    utility = Path(__file__).resolve().parents[2] / 'tests/utils/run_spec_boundaries.py'
    spec = importlib.util.spec_from_file_location('_d76_boundary_inventory', utility)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    candidates = module.discover(source)
    files = sorted({candidate.path for candidate in candidates})
    hashes = {path: sha(source / path) for path in files}
    sidecar = source / module.SIDECAR
    sidecar_sha256 = sha(sidecar) if sidecar.is_file() else None
    rows = []
    for candidate in candidates:
        if candidate.source_sha256 != hashes[candidate.path]:
            raise ValueError('source changed between discovery and contract inventory')
        mode, error = module.contract(candidate, source)
        rows.append({**asdict(candidate), 'identity': candidate.identity,
                     'contract': mode, 'contract_error': error})
    if hashes != {path: sha(source / path) for path in files}:
        raise ValueError('candidate source changed during inventory')
    if sidecar_sha256 != (sha(sidecar) if sidecar.is_file() else None):
        raise ValueError('protected-contract sidecar changed during inventory')
    result = {'source': str(source), 'method': 'all package Python files, including ignored/hidden; AST only',
              'producer': str(Path(__file__).resolve()), 'producer_sha256': sha(Path(__file__)),
              'utility': str(utility), 'utility_sha256': sha(utility),
              'protected_contract_sidecar': str(sidecar),
              'protected_contract_sidecar_sha256': sidecar_sha256,
              'candidate_count': len(rows), 'candidate_source_sha256': hashes,
              'missing_contract_count': sum(row['contract_error'] is not None for row in rows),
              'candidates': rows,
              'limits': ['source-visible signatures, annotations, constructors and factory callers',
                         'not a dynamic Python call graph or runtime guard acceptance result']}
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'output': str(output), 'sha256': sha(output),
                      'candidates': len(rows), 'missing_contracts': result['missing_contract_count'],
                      'affected_source_files': files}, indent=2))


if __name__ == '__main__':
    main()
