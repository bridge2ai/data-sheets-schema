#!/usr/bin/env python3
"""#5212 round 5, 2026-11-01: inventory literal production pin emitters.

Inputs: source tree, output JSON under scratch-5212fix. Outputs: AST locations,
enclosing functions, key expressions and source hashes for every dict carrying
a literal path key. Includes ignored Python files; no imports or execution.
The report separately traces these descriptors into the allowed output sections.
"""
import ast
import hashlib
import json
from pathlib import Path
import sys

root, output = map(Path, sys.argv[1:])
assert 'scratch-5212fix' in output.parts
rows, sources = [], {}


class Visitor(ast.NodeVisitor):
    functions = []

    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Dict(self, node):
        fields = {key.value: ast.get_source_segment(source, value)
                  for key, value in zip(node.keys, node.values)
                  if isinstance(key, ast.Constant) and isinstance(key.value, str)}
        if 'path' in fields:
            rows.append({'file': relative, 'line': node.lineno,
                         'function': '.'.join(self.functions), 'fields': fields})
        self.generic_visit(node)


for path in sorted((root / 'src/data_sheets_schema').rglob('*.py')):
    raw = path.read_bytes()
    source, relative = raw.decode('utf-8'), str(path.relative_to(root))
    sources[relative] = hashlib.sha256(raw).hexdigest()
    Visitor().visit(ast.parse(source))
output.write_text(json.dumps({'source_sha256': sources, 'path_descriptors': rows}, indent=2) + '\n')
print(f'{len(sources)} source files; {len(rows)} literal path descriptors; {output}')
