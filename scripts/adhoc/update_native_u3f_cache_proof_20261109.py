"""U3-F closed cache producer templates, 2026-11-09.

Inputs: reviewed typed_audit DerivationCache._derive/_store. Output: frozen
executable AST templates replacing the obsolete inline-store derivation proof.
No scanned source is trusted as a template at scanner runtime.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'
source = ast.parse((ROOT / 'src/data_sheets_schema/typed_audit.py').read_text())
cls = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == 'DerivationCache')
text = path.read_text()
start = text.index("    cache = function('typed_audit', '_derive', 'DerivationCache')")
end = text.index("    derived = function('typed_audit', '_derive_uncached')", start)
replacement = '    # Fixed cache transport includes all fresh fallbacks and the runtime-token\n    # race checks. The store is separately pinned; no new return or mutation\n    # can be treated as the old cached producer. This is not cache admission.\n'
for name in ('_derive', '_store'):
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
    body = fn.body[1:] if ast.get_docstring(fn) is not None else fn.body
    code = '\n'.join(ast.unparse(n) for n in body)
    # exact_body prefixes the first line and parses all following statements
    # within the same dummy function.
    code = code.replace('\n', '\n    ')
    replacement += "    exact_body(function('typed_audit', " + repr(name) + ", 'DerivationCache'), r'''" + code + "''')\n"
text = text[:start]+replacement+text[end:]
ast.parse(text)
path.write_text(text)
