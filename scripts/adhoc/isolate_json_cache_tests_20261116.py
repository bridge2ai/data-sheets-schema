"""PR 5968 lead-approved fresh-process identity-test isolation, 2026-11-16.

Input/output: JSON cache tests. Move original assertion bodies unchanged into
helpers, then call them through a fresh interpreter without rebinding authority.
Run after the serial order diagnosis, before final verification.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'tests/test_typed_json_parse_cache.py'
source = path.read_text()
names = ('test_replaced_copy_alias_disables_shared_values',
         'test_interpreter_integer_limit_change_refuses_a_warm_value')
original = ast.parse(source)
source = source.replace('import sys\n', 'import sys\nimport subprocess\nfrom pathlib import Path\n', 1)
for name in names:
    source = source.replace('def ' + name + '(', 'def _assert_' + name[5:] + '(', 1)
    wrapper = '''

def NAME(tmp_path):
    probe = Path(__file__).resolve().parents[1] / 'scripts/adhoc/json_cache_test_probe_20261116.py'
    result = subprocess.run([sys.executable, str(probe), 'NAME'],
                            capture_output=True, text=True, timeout=60)
    (tmp_path / 'json-cache-probe.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == 'NAME passed'
'''.replace('NAME', name)
    if name == names[1]:
        wrapper = wrapper.replace('    probe =',
            "    if not hasattr(sys, 'get_int_max_str_digits'):\n"
            "        pytest.skip('this interpreter has no integer-string limit')\n"
            '    probe =', 1)
    source += wrapper
changed = ast.parse(source)
for name in names:
    before = next(node for node in original.body if isinstance(node, ast.FunctionDef) and node.name == name)
    after = next(node for node in changed.body if isinstance(node, ast.FunctionDef) and node.name == '_assert_' + name[5:])
    assert ast.dump(ast.Module(body=before.body, type_ignores=[])) == ast.dump(ast.Module(body=after.body, type_ignores=[]))
assert chr(64) not in source
path.write_text(source)
print('Both original identity assertion bodies preserved exactly')
