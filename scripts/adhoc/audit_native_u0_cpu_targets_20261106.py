#!/usr/bin/env python3
"""U0/#4354, 2026-11-06: validate default profiling targets on frozen source.

Inputs: --tree exact diagnostic/failed source and current profiler tooling.
Output: new --out JSON with source pins, valid ordinary targets and absences.
AST-only inspection; no source, native executable, provider or test is run.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    script = Path(__file__).with_name('native_recorder_cpu_profile_20261106.py')
    spec = importlib.util.spec_from_file_location('u0_cpu_target_roster', script)
    cpu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cpu)
    rows, missing, invalid, pins = [], [], [], {}
    targets = {module: set(names) for module, names in cpu.PHASES.items()}
    for module, names in cpu.base.CACHE_TARGETS.items():
        targets.setdefault(module, set()).update(names)
    for module, names in sorted(targets.items()):
        path = args.tree / 'src/data_sheets_schema' / (module.replace('.', '/') + '.py')
        if not path.is_file():
            missing.extend(module + ':' + name for name in sorted(names))
            continue
        raw = path.read_bytes()
        pins[str(path)] = hashlib.sha256(raw).hexdigest()
        definitions = cpu.base._definitions(ast.parse(raw, filename=str(path)))
        for name in sorted(names):
            identity = module + ':' + name
            node = definitions.get(name)
            if node is None:
                missing.append(identity)
            elif isinstance(node, ast.AsyncFunctionDef) or any(
                    isinstance(child, (ast.Yield, ast.YieldFrom)) for child in ast.walk(node)):
                invalid.append(identity)
            else:
                rows.append(identity)
    mandatory = {'cli.provenance:record', 'provenance:ProvenanceRecord.write',
        'provenance:check_record', 'cli.provenance:_inline_checks', 'backfill_checks:compute',
        'backfill_checks:apply', 'native_shared_capture:_base',
        'native_shared_capture:_recorded_run', 'native_shared_receipts:_ReceiptCatalogContext.catalog'}
    absent_required = sorted(mandatory - set(rows))
    result = {'tree': str(args.tree), 'profiler_sha256': hashlib.sha256(script.read_bytes()).hexdigest(),
        'source_pins': pins, 'ordinary_targets': rows, 'absent_optional_targets': missing,
        'invalid_generator_or_async_targets': invalid, 'missing_required': absent_required,
        'passed': not invalid and not absent_required,
        'scope': 'AST target eligibility only; complete profiler runtime tested separately'}
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'passed': result['passed'], 'ordinary_targets': len(rows),
                      'missing_optional': missing, 'invalid': invalid, 'missing_required': absent_required}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
