"""Issue 6233, 2026-11-14: probe the proposed prefix guard's alias coverage.

Inputs: current verified package sources. Output: JSON evidence at argv[1].
Offline loader probe only; no admission, controller, helper or native dispatch.
All in-memory mutations are restored before leaving the verified loader.
"""
from pathlib import Path
from types import ModuleType
import hashlib
import json
import sys

from data_sheets_schema import native_execution_authority_v2 as authority


def replacement_validator(*args, **kwargs):
    raise ValueError('probe replacement validator reached')


def main():
    output = Path(sys.argv[1])
    dependencies = authority.dependency_identity()
    pins = dependencies['base']['package_sources']
    name = 'data_sheets_schema.native_shared_stage'
    with authority.loaded_verified_package_module(name, package_sources=pins) as stage:
        original = stage.typed
        original_identity = authority.module_source_identity(stage)
        original_callable = original.check_worker
        # Keep every original global, including grammar and limits, identical.
        # Only the imported dependency binding changes on the consumer.
        substituted = ModuleType(original.__name__)
        substituted.__dict__.update(vars(original))
        substituted.check_worker = replacement_validator
        source_bytes = Path(original_identity['path']).read_bytes()
        try:
            stage.typed = substituted
            after_identity = authority.module_source_identity(stage)
            try:
                stage.typed.check_worker(None, None, None)
            except ValueError as exc:
                reached = str(exc) == 'probe replacement validator reached'
            else:
                reached = False
            result = {
                'probe_scope': 'source-verified stage dependency alias, not a live callback',
                'stage_identity_before': original_identity,
                'stage_identity_after': after_identity,
                'source_identity_unchanged': original_identity == after_identity,
                'source_bytes_unchanged': Path(original_identity['path']).read_bytes() == source_bytes,
                'original_dependency_callable_unchanged': original.check_worker is original_callable,
                'dependency_globals_other_than_validator_identical': all(
                    substituted.__dict__[key] is value for key, value in vars(original).items()
                    if key != 'check_worker'),
                'replacement_validator_reached': reached,
                'interpreter': {'executable': sys.executable, 'version': sys.version,
                                'cache_tag': sys.implementation.cache_tag},
            }
        finally:
            stage.typed = original
        result['alias_restored'] = stage.typed is original
        assert authority.module_source_identity(stage) == original_identity
    assert all(result[key] for key in (
        'source_identity_unchanged', 'source_bytes_unchanged',
        'original_dependency_callable_unchanged',
        'dependency_globals_other_than_validator_identical',
        'replacement_validator_reached', 'alias_restored'))
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    output.write_bytes(raw)
    assert output.read_bytes() == raw
    print(json.dumps({'output': str(output), 'sha256': hashlib.sha256(raw).hexdigest(),
                      'result': result}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
