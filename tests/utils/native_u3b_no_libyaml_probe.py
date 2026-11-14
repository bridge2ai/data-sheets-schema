"""Probe M8-compatible optional LibYAML import fallback for U3-B, 2026-11-07.

Inputs: a local source tree and an output path. Output: JSON import/binding
evidence. The import hook is confined to this test process; no files in the
installed library or production implementation are modified.
"""
import argparse
import builtins
import hashlib
import importlib
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
source = args.source.resolve()
sys.path.insert(0, str(source / 'src'))
import yaml  # Establish the ordinary YAML package before masking its optional extension.

original_import = builtins.__import__
blocked = []


def without_extension(name, *positional, **keywords):
    if name == 'yaml._yaml':
        blocked.append(name)
        raise ImportError('simulated unavailable optional LibYAML extension')
    return original_import(name, *positional, **keywords)


result = {'source': str(source), 'source_sha256': hashlib.sha256(
    (source / 'src/data_sheets_schema/cache_dependencies.py').read_bytes()).hexdigest(),
    'import_error': None, 'module_path': None, 'default_binding_ready': None}
try:
    builtins.__import__ = without_extension
    module = importlib.import_module('data_sheets_schema.cache_dependencies')
    result['module_path'] = str(Path(module.__file__).resolve())
    assert result['module_path'] == str(source / 'src/data_sheets_schema/cache_dependencies.py')
    bindings = module.FunctionBindings()
    bindings.bind(lambda: bindings.key(None))
    result['default_binding_ready'] = bindings.ready
except Exception as exc:
    result['import_error'] = type(exc).__name__ + ': ' + str(exc)
finally:
    builtins.__import__ = original_import
result['blocked_extension_imports'] = len(blocked)
raw = json.dumps(result, indent=2) + '\n'
args.output.write_text(raw)
assert args.output.stat().st_size
print(raw, end='')
