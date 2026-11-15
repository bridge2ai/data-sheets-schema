"""Build reviewed AST contracts from f5c7c312f for issues 6246–6248.

Inputs: committed candidate source. Output: scanner edits, no source edits.
Purpose: reproducible structural templates without rotating pins, 2026-11-15.
"""
import ast
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCAN = ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'


def source(relative):
    return subprocess.check_output(['git', 'show', 'f5c7c312f:' + relative], cwd=ROOT).decode()


def strip_docstrings(node):
    for child in ast.walk(node):
        if isinstance(child, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            if child.body and isinstance(child.body[0], ast.Expr) and isinstance(child.body[0].value, ast.Constant) and isinstance(child.body[0].value.value, str):
                child.body.pop(0)
    return node


def main():
    text = SCAN.read_text()
    if 'Issue 6246: close module execution' in text:
        raise SystemExit('contracts already present; use this builder only on the base scanner')
    producer = strip_docstrings(ast.parse(source('src/data_sheets_schema/native_execution_registration_v2.py')))
    # Bodies are separately proved where they participate in rendering. Keep
    # every signature, decorator, class body, import and module initializer.
    for node in producer.body:
        if isinstance(node, ast.FunctionDef):
            node.body = [ast.Pass()]
    skeleton = ast.unparse(producer)
    # Store the decorator as an escape, keeping this assignment's text free
    # of notification syntax while retaining its exact AST at runtime.
    def literal_source(value, indent):
        return '(\n' + ''.join(' ' * indent + repr(line).replace(chr(64), '\\x40') + '\n' for line in value.splitlines(keepends=True)) + ' ' * (indent - 4) + ')'

    literal = literal_source(skeleton, 8)
    contract = '''
    # Issue 6246: close module execution, including definition-time expressions.
    # Function bodies retain their existing detailed producer proofs above.
    module_shape = ast.parse(ast.unparse(tree))
    for node in ast.walk(module_shape):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            node.body = _without_docstring(node.body)
    for node in module_shape.body:
        if isinstance(node, ast.FunctionDef):
            node.body = [ast.Pass()]
    expected_module = ast.parse(PRODUCER_TEMPLATE)
    if dump(module_shape) != dump(expected_module):
        raise fail('v2 producer module execution is not exact')
'''.replace('PRODUCER_TEMPLATE', literal)
    marker = '    # Module-level CLI rebinding must not bypass the fixed decorated command.'
    assert text.count(marker) == 1
    text = text.replace(marker, contract + '\n' + marker)
    runner = ast.parse(source('src/data_sheets_schema/api_runner.py'))
    invariant = next(n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name == '_require_registered_input_spellings')
    invariant = strip_docstrings(invariant)
    contract = "            # Issue 6247: a name/signature alone cannot prove this guard.\n            expected_invariant_body = ast.parse(" + literal_source(ast.unparse(invariant), 16) + ").body[0]\n            if [dump(n) for n in _without_docstring(definitions[0].body)] != [dump(n) for n in expected_invariant_body.body]:\n                raise fail('phase input invariant body is not exact')\n"
    marker = "            evidence.append(f'{RUNNER}:{body[0].lineno}')"
    assert text.count(marker) == 1
    text = text.replace(marker, contract + marker)
    cli = strip_docstrings(ast.parse(source('src/data_sheets_schema/native_shared_stage/__main__.py')))
    contract = "    # Issue 6248: the registered module command executes this entry point.\n    stage_cli = _tree(root / (prefix + 'native_shared_stage/__main__.py'))\n    for node in ast.walk(stage_cli):\n        if isinstance(node, (ast.Module, ast.FunctionDef)):\n            node.body = _without_docstring(node.body)\n    if dump(stage_cli) != dump(ast.parse(" + literal_source(ast.unparse(cli), 8) + ")):\n        raise fail('native stage CLI execution is not exact')\n"
    contract = contract.replace(
        "stage_cli = _tree(root / (prefix + 'native_shared_stage/__main__.py'))",
        "stage_cli = ast.parse(ast.unparse(_tree(root / (prefix + 'native_shared_stage/__main__.py'))))")
    marker = "    fixed_import('native_shared_stage', '', 'native_shared_receipts', 'nr')"
    assert text.count(marker) == 1
    text = text.replace(marker, contract + '\n' + marker)
    SCAN.write_text(text)


if __name__ == '__main__':
    main()
