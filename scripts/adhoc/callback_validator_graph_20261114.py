"""Issue 6233, 2026-11-14: inventory verified validator graph for the prefix guard.

Input: current pinned package sources. Output: JSON graph in assigned scratch.
"""
import json
import sys
from contextlib import ExitStack
from pathlib import Path
from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_callback_orchestration as callbacks


def main():
    pins = authority.dependency_identity()['base']['package_sources']
    graph = {}
    for short in ('native_shared_capture', 'native_shared_stage', 'native_shared_observations'):
        name = 'data_sheets_schema.' + short
        with authority.loaded_verified_package_module(name, package_sources=pins) as module:
            identity = authority.module_source_identity(module)
            raw = authority._verified_source_bytes(identity['path'], identity['sha256'])
            graph.update(authority.refuse_legacy_consumer_imports(raw, name=name, package_sources=pins))
    raw = json.dumps(graph, sort_keys=True, indent=2) + '\n'
    output = Path(sys.argv[1])
    output.write_text(raw)
    assert output.read_text() == raw
    print(raw)
    with ExitStack() as stack:
        modules = [stack.enter_context(authority.loaded_verified_package_module(name, package_sources=pins))
                   for name in sorted(callbacks.VALIDATOR_MODULES)]
        for module in modules:
            for name, value in sorted(vars(module).items()):
                if name.isupper() and not name.startswith('_') and callbacks._binding_identity(value) is None:
                    try:
                        callbacks._constant_value(value)
                    except ValueError:
                        print('Unsupported constant:', module.__name__, name, type(value).__name__)
        guard = callbacks._ValidatorGuard(modules, lambda: None, b'probe')
        print('Reusable:', guard.reusable())


if __name__ == '__main__':
    main()
