"""U3-F scanner route migration, 2026-11-09.

Inputs: reviewed v2 CLI/preparer source. Outputs: closed AST templates in scan.py.
Templates are frozen at implementation time, never inferred from scanned input.
The scanner still rejects every executable change to the recognized producers.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'

def function(relative, name):
    tree = ast.parse((ROOT / relative).read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    if ast.get_docstring(fn) is not None:
        fn.body = fn.body[1:]
    return ast.unparse(fn)

def main():
    if 'def _derive_native_v2_render(' in PATH.read_text():
        raise RuntimeError('one-time migration already applied; use the committed diff, not a second rewrite')
    cli = function('src/data_sheets_schema/cli/prompt.py', 'render_native_shared')
    prepare = function('src/data_sheets_schema/native_execution_registration_v2.py', 'prepare')
    helper = '''def _derive_native_v2_render(root, cli, command):
    """Closed source proof of the v2 preparation producer and CLI data flow.

    Exact executable AST templates bind selection/runtime arguments, RunSpec
    construction, its entry guard, runtime capture, instruction and envelope
    reads, provider comparison and exclusive output. Literal diagnostics are
    also pinned. Only leading docstrings and source formatting are ignored.
    No template is loaded from the scanned checkout, and no source is executed.
    This proves rendering structure, not preparation or launch acceptance.
    """
    fail = lambda detail: _not_derived('separate native shared render route', detail)
    dump = lambda node: ast.dump(node, include_attributes=False)
    def exact(actual, text):
        expected = ast.parse(text).body[0]
        # Copy the AST; never mutate the tree used by other derivations.
        observed = ast.parse(ast.unparse(actual)).body[0]
        observed.body = _without_docstring(observed.body)
        if dump(observed) != dump(expected):
            raise fail('unsupported v2 render producer: ' + actual.name)
    exact(command, CLI_TEMPLATE)
    relative = 'src/data_sheets_schema/native_execution_registration_v2.py'
    tree = _tree(root / relative)
    definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'prepare']
    if len(definitions) != 1:
        raise fail('v2 preparation has no unique producer')
    prepare = definitions[0]
    exact(prepare, PREPARE_TEMPLATE)
    # Imported producer/contract names must retain the bindings used by the
    # templates. A shadow, duplicate import, assignment or monkeypatch refuses.
    def bound(module, statement, name):
        expected = ast.parse(statement).body[0]
        matches = [n for n in module.body if dump(n) == dump(expected)]
        if len(matches) != 1:
            raise fail('v2 producer import is not exact: ' + name)
        alias = matches[0].names[0]
        for n in ast.walk(module):
            if n is alias:
                continue
            if ((isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, (ast.Store, ast.Del)))
                    or _rebinding(n, name, None)
                    or isinstance(n, ast.Attribute) and isinstance(n.ctx, (ast.Store, ast.Del))
                       and isinstance(n.value, ast.Name) and n.value.id == name):
                raise fail('v2 producer binding is replaced: ' + name)
    for statement, name in (
        ('from . import native_shared_contract as c', 'c'),
        ('from . import native_shared_selection as selection', 'selection'),
        ('from . import native_execution_authority_v2 as authority', 'authority'),
        ('from .native_execution_registration import validate_runtime', 'validate_runtime'),
    ):
        bound(tree, statement, name)
    for name in ('prepare',):
        if any((isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, (ast.Store, ast.Del)))
               or _rebinding(n, name, None) for n in ast.walk(tree) if n is not prepare):
            raise fail('v2 preparation producer is replaced')
    # Module-level CLI rebinding must not bypass the fixed decorated command.
    for n in cli.body:
        if n is command:
            continue
        if any((isinstance(x, ast.Name) and x.id == command.name and isinstance(x.ctx, (ast.Store, ast.Del)))
               or _rebinding(x, command.name, None) for x in ast.walk(n)):
            raise fail('v2 render command is replaced')
    return [f'{relative}:{prepare.lineno}']


'''.replace('CLI_TEMPLATE', 'r"""'+cli+'"""').replace('PREPARE_TEMPLATE', 'r"""'+prepare+'"""')
    text = PATH.read_text()
    marker = 'def derive_native_shared_route(root: Path, tree: ast.Module) -> dict | None:'
    assert text.count(marker) == 1
    text = text.replace(marker, helper+marker)
    start = text.index("    expected_imports = ast.parse('''from data_sheets_schema.api_runner import RunSpec", text.index(marker))
    end = text.index("    evidence.append(f'{cli_path}:{command.lineno}')", start)
    old = text[start:end]
    branch = '''    v2_import = ast.parse('from data_sheets_schema import native_execution_registration_v2 as preparation').body[0]
    if any(dump(n) == dump(v2_import) for n in command.body):
        evidence.extend(_derive_native_v2_render(root, cli, command))
    else:
'''
    text = text[:start] + branch + ''.join('    '+line if line.strip() else line for line in old.splitlines(keepends=True)) + text[end:]
    ast.parse(text)
    PATH.write_text(text)

if __name__ == '__main__':
    main()
