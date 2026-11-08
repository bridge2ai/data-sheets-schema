#!/usr/bin/env python3
"""One offline same-schema API instruction capture for U5, 2026-11-08.

Inputs: explicit source root, unchanged external 3.2.0 schemas, synthetic input
directory. Outputs: instruction/render-spec bytes and import/schema witnesses.
Invoked only by the network-denied U5 pytest harness. No provider construction,
native process, protected overlay or full-phase/canary acceptance is performed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--schema-dir', required=True, type=Path)
    parser.add_argument('--input-dir', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    source = args.source_root.resolve(strict=True)
    checkout = Path(__file__).resolve().parents[2]
    scratch = checkout.parent / 'scratch-native-u5-prep'
    allowed = {checkout, scratch / 'baseline-d258611c5/tree'}
    if args.source_root != source or source not in allowed:
        raise ValueError('render source must be the assigned candidate or pinned baseline')
    expected_schema = scratch / 'schema-5e382f0c4/tree/src/data_sheets_schema/schema'
    if args.schema_dir != expected_schema or expected_schema.resolve(strict=True) != expected_schema:
        raise ValueError('render requires the exact named external schema directory')
    for target in (args.input_dir, args.out):
        if not target.is_absolute() or target.resolve() != target or not target.is_relative_to(scratch):
            raise ValueError('render artifacts must stay at literal assigned scratch paths')
    if args.out.exists():
        raise ValueError('render output already exists')
    # The physical venv remains the same; remove any other editable checkout
    # before the first data_sheets_schema/tests import.
    sys.path[:] = [p for p in sys.path if p and not
                  ((Path(p) / 'data_sheets_schema').is_dir() or
                   (Path(p) / 'src/data_sheets_schema').is_dir())]
    sys.path[:0] = [str(source / 'src'), str(source)]
    import pytest
    from data_sheets_schema import api_runner as api
    from data_sheets_schema import shared_generation as shared
    from tests.test_generation_manifest_identity import external
    from tests.test_shared_generation_selection import registration_for, selected_spec
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(api, 'FULL_SCHEMA_PATH', args.schema_dir / 'data_sheets_schema_all.yaml')
        patch.setattr(api, 'CORE_SCHEMA_PATH', args.schema_dir / 'data_sheets_schema_core_all.yaml')
        patch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})
        args.input_dir.mkdir(exist_ok=True)
        specification = external.__wrapped__(args.input_dir)
        specification.run_date = '2026-11-08'
        registration = registration_for(specification)
        specification = selected_spec(specification, registration)
        specification.bind_api_header_values(api._model_settings(specification.condition))
        instruction = specification.instruction.encode()
        render_spec = specification.render_spec()
        assert instruction and 'Shared generation rules v1' in instruction.decode()
        args.out.mkdir()
        (args.out / 'instruction.txt').write_bytes(instruction)
        (args.out / 'render-spec.json').write_bytes(shared.canonical(render_spec))
        (args.out / 'registration.json').write_bytes(shared.canonical(registration))
        origins = {}
        for name, module in tuple(sys.modules.items()):
            if not (name == 'data_sheets_schema' or name.startswith('data_sheets_schema.')
                    or name == 'tests' or name.startswith('tests.')):
                continue
            filename = getattr(module, '__file__', None)
            if filename is not None:
                resolved = Path(filename).resolve(strict=True)
                if not resolved.is_relative_to(source):
                    raise AssertionError('foreign render import: ' + name)
                origins[name] = str(resolved)
            for namespace in getattr(module, '__path__', ()):
                if not Path(namespace).resolve(strict=True).is_relative_to(source):
                    raise AssertionError('foreign render package path: ' + name)
        result = {'source_root': str(source), 'module_origins': origins,
                  'schema_directory': str(args.schema_dir),
                  'schema_pins': {k: registration['inputs'][k] for k in ('full_schema', 'core_schema')},
                  'instruction_sha256': hashlib.sha256(instruction).hexdigest(),
                  'instruction_bytes': len(instruction),
                  'scope': 'generic_v10 shared-v1 API instruction only; external schema input; no phase or launch acceptance'}
        (args.out / 'witness.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
