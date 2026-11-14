"""Audit U3-F executable production deltas, 2026-11-09.

Inputs: starting 49a5f2b74 and current committed worktree source.
Output: assigned scratch/u3f/production-delta-review.json for local review.
No imports of project code, source mutations, network or native-agent calls.
"""
import ast
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)

class StripDocs(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:]
        return node
    visit_AsyncFunctionDef = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef
    visit_Module = visit_FunctionDef

rows = []
for path in git('diff', '--name-only', '49a5f2b74', 'HEAD', '--', 'src').decode().splitlines():
    assert path.endswith('.py'), path
    old = ast.parse(git('show', '49a5f2b74:'+path))
    new = ast.parse((ROOT / path).read_bytes())
    same = ast.dump(StripDocs().visit(old)) == ast.dump(StripDocs().visit(new))
    rows.append({'path': path, 'docstring_only': same})
assert {r['path'] for r in rows if not r['docstring_only']} == {
    'src/data_sheets_schema/typed_audit.py',
    'src/data_sheets_schema/native_shared_registration.py'}
result = {'start': git('rev-parse', '49a5f2b74').decode().strip(),
          'head': git('rev-parse', 'HEAD').decode().strip(), 'source_files': rows,
          'executable_delta_scope': 'typed omission producer branch; explicit native parent refusal',
          'limitation': 'AST equality after removing docstrings is a scope check, not a semantic proof.'}
out = ROOT.parent / 'scratch-native-u1u3/u3f/production-delta-review.json'
out.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
