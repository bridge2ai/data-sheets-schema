"""Build exact v3 producer skeleton for issue 6246, 2026-11-15.
Inputs: reviewed f10e8ae20 source and scanner. Output: scanner edit.
"""
import ast
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'
text = path.read_text()
start = text.index('    # Issue 6246: close module execution')
end = text.index('    # Module-level CLI rebinding', start)
block = text[start:end]
literal_start = block.index('    expected_module = ast.parse(')
literal_end = block.index('\n    if dump(module_shape)', literal_start)
v2 = block[literal_start:literal_end].replace('    expected_module = ast.parse(', '    v2_template = ', 1)[:-1]
source = subprocess.check_output(['git', 'show', 'f10e8ae20:src/data_sheets_schema/native_execution_registration_v2.py'], cwd=ROOT)
tree = ast.parse(source)
for node in ast.walk(tree):
    if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body.pop(0)
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        node.body = [ast.Pass()]
literal = '(\n' + ''.join('        ' + repr(line).replace(chr(64), '\\x40') + '\n' for line in ast.unparse(tree).splitlines(keepends=True)) + '    )'
helper = '''def _native_producer_module_matches(tree, *, v3):
    """Compare only the selected reviewed version, including definition time.

    Historical v2 is retained verbatim; v3 derives from f10e8ae20.
    Render-relevant function bodies have separate exact proofs.
    """
'''
shape = block[block.index('    module_shape ='):literal_start]
helper += shape + v2 + '\n    v3_template = ' + literal + '\n'
helper += '    expected_module = ast.parse(v3_template if v3 else v2_template)\n    return ast.dump(module_shape) == ast.dump(expected_module)\n\n\n'
replacement = "    # Issue 6246: version-selected exact module execution proof.\n    if not _native_producer_module_matches(tree, v3=v3):\n        raise fail('v2 producer module execution is not exact')\n\n"
text = text[:start] + replacement + text[end:]
marker = 'def _derive_native_v2_render('
text = text.replace(marker, helper + marker, 1)
path.write_text(text)
