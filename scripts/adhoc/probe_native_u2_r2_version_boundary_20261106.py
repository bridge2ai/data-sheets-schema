# Purpose: isolate frozen canary version checks for #5508 round-2 stop condition.
# Inputs: current frozen launcher source; outputs: scratch JSON evidence. 2026-11-06.
# Only AST-selected verify functions execute; launcher imports/main never execute.
import ast
import hashlib
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)

class BudgetStop(Exception):
    pass

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def function(relative, name):
    path = ROOT / relative
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = dict(Path=Path, sys=sys, sha=sha, BudgetStop=BudgetStop)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]

# Stub only the final implementation-origin import; no package side effects.
package = types.ModuleType('data_sheets_schema')
package.api_runner = types.SimpleNamespace(__file__=str(ROOT / 'src/data_sheets_schema/api_runner.py'))
sys.modules['data_sheets_schema'] = package
verify = function('notes/matched_cborg_2026-09-13/run_api_canary.py', 'verify')
direct = function('notes/claudecode_direct/run_direct_canary.py', 'verify_registration')
assert Path.cwd().resolve() == ROOT
manifest = dict(repository=str(ROOT), python=sys.executable, python_version=sys.version,
                pinned_files={str(ROOT / 'notes/matched_cborg_2026-09-13/prepare_registration_v2.py'):
                              sha(ROOT / 'notes/matched_cborg_2026-09-13/prepare_registration_v2.py')})
results = {}
for version in (1, 2):
    value = dict(manifest, schema_version=version)
    if version == 2:
        value['controller_authority'] = dict(authority_version=2,
            controller_sources_sha256=sha(ROOT / 'src/data_sheets_schema/native_controller_sources_v2.json'))
    record = OUT / f'synthetic-v{version}.json'
    record.write_text(json.dumps(value, indent=2) + '\n')
    verify(value, record, sha(record))
    results[f'api_v1_verifier_schema_{version}'] = 'accepted'
try:
    direct(dict(kind='d4d_direct_arm_registration', schema_version=2), OUT / 'synthetic-v2.json')
except BudgetStop as exc:
    assert str(exc) == 'not a direct-arm registration'
    results['direct_v1_verifier_schema_2'] = str(exc)
else:
    raise AssertionError('direct schema-2 guard missing')
results['scope'] = 'isolated unmodified verifier function bodies; synthetic records, not full preparer/launch integration'
(OUT / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
