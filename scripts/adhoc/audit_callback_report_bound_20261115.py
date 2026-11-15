"""Issue 6214, 2026-11-15: audit wait sites and pins; source to scratch JSON."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

scratch = Path('../scratch-callback-teardown-20261115')
root = Path('src/data_sheets_schema')
paths = sorted(set(root.glob('native_shared_callback_*.py')) | set((root / 'native_shared_stage').rglob('*.py')) | {root / 'native_execution_orchestration.py', root / 'native_shared_controller_orchestration.py'})
rows = []
for path in paths:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ('acquire', 'join', 'wait', 'get'):
            rows.append(dict(file=str(path), line=node.lineno, kind=node.func.attr, expression=ast.unparse(node)))
        elif isinstance(node, ast.With):
            for item in node.items:
                expression = ast.unparse(item.context_expr)
                if 'lock' in expression:
                    rows.append(dict(file=str(path), line=node.lineno, kind='with', expression=expression))
(scratch / 'report-wait-sites.json').write_text(json.dumps(rows, indent=2) + '\n')
source = root / 'native_shared_controller_orchestration.py'
old = hashlib.sha256(subprocess.check_output(['git', 'show', 'HEAD:' + str(source)])).hexdigest()
new = hashlib.sha256(source.read_bytes()).hexdigest()
searches = []
for name, pattern in [('hash', old), ('path', source.name)]:
    command = ['grep', '-rn', '--exclude-dir=.git', pattern, '.']
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    assert result.returncode in (0, 1), result.stderr
    (scratch / ('report-pin-' + name + '.txt')).write_text(result.stdout)
    searches.append(dict(command=command, code=result.returncode, matches=len(result.stdout.splitlines())))
result = dict(source=str(source), old=old, new=new, searches=searches, wait_sites=len(rows))
(scratch / 'report-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
