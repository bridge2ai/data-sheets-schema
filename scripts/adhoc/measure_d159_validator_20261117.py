"""Measure the unchanged validator through the native final schema gate.

Input: public-case fixture full seed and current schemas. Output: full/core YAML
and timing JSON in the supplied scratch directory. D159 ruling, 2026-11-17.
Executes the exact nested schema gate in isolation; no native binary or provider.
"""
import ast
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import yaml
from data_sheets_schema import api_runner as api
from data_sheets_schema.derive_core import derive_core
from data_sheets_schema.duplicate_keys import duplicate_keys_in, describe

root = Path(__file__).resolve().parents[2]
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
tree = ast.parse((root / 'tests/native_shared_fixture.py').read_text())
builder = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'build_native_fixture')
seed = next(x.value for x in builder.body if isinstance(x, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'full' for t in x.targets))
full = ast.literal_eval(seed)
core = derive_core(full)
paths = {}
for kind, record in [('full', full), ('core', core)]:
    paths[kind] = out / (kind + '.yaml')
    paths[kind].write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True))
source = root / 'src/data_sheets_schema/native_execution_gates.py'
check = next(x for x in ast.parse(source.read_text()).body if isinstance(x, ast.FunctionDef) and x.name == 'check')
gate = next(x for x in check.body if isinstance(x, ast.FunctionDef) and x.name == 'schemas')
measurements = []
original = api._validator_lines
def measured(path, schema, cls):
    start = time.perf_counter()
    lines, failure = original(path, schema, cls)
    measurements.append({'class': cls, 'record_bytes': path.stat().st_size,
        'record_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'wall_seconds': time.perf_counter() - start, 'timeout_seconds': 180,
        'failure': failure, 'findings': lines})
    return lines, failure
api._validator_lines = measured
scope = {'api': api, 'duplicate_keys_in': duplicate_keys_in, 'describe': describe,
    'projected': Path, 'spec': SimpleNamespace(_agentic_artifact_paths=paths),
    'prepared': {'schema_paths': {'full': api.FULL_SCHEMA_PATH, 'core': api.CORE_SCHEMA_PATH}}}
exec(compile(ast.Module(body=[gate], type_ignores=[]), str(source), 'exec'), scope)
result = scope['schemas']()
report = {'scope': 'exact native final schema closure in isolation, public fixture seed',
    'gate_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'measurements': measurements, 'result': result}
text = json.dumps(report, indent=2).replace(chr(64), '[at]')
(out / 'timing.json').write_text(text + '\n')
print(text)
assert result['passed'], report
