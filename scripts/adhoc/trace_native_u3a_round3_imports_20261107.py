#!/usr/bin/env python3
"""Trace N2 static versus import-time paths, 2026-11-07.

Inputs: this worktree's Python source only. Output: JSON shortest paths to v1
registration from api_runner, including function-deferred edges. No execution.
"""
import ast
from collections import deque
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def nodes(tree):
    yield tree
    if not isinstance(tree, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        for child in ast.iter_child_nodes(tree):
            yield from nodes(child)


def path_for(name):
    stem = ROOT / 'src' / name.replace('.', '/')
    for path in (stem.with_suffix('.py'), stem / '__init__.py'):
        if path.is_file():
            return path


def edges(name, eager):
    path = path_for(name)
    if path is None:
        return []
    tree = ast.parse(path.read_bytes())
    package = name if path.name == '__init__.py' else name.rpartition('.')[0]
    targets = []
    for node in nodes(tree) if eager else ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            target = node.module or ''
            if node.level:
                target = importlib.util.resolve_name('.' * node.level + target, package)
            targets.append(target)
            targets.extend(target + '.' + alias.name for alias in node.names)
    return sorted({target for target in targets
                   if target.startswith('data_sheets_schema.') and path_for(target)})


def trace(eager):
    queue = deque([['data_sheets_schema.api_runner']])
    seen = set()
    while queue:
        path = queue.popleft()
        name = path[-1]
        if name in seen:
            continue
        seen.add(name)
        if name == 'data_sheets_schema.native_execution_registration':
            return path
        queue.extend(path + [target] for target in edges(name, eager) if target not in seen)
    return None


if __name__ == '__main__':
    print(json.dumps({'all_static': trace(False), 'import_time': trace(True)}, indent=2))
