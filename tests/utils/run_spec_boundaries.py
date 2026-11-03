"""Discover source-visible RunSpec boundaries without importing generation code.

PR #5213 round four, 2026-11-02. Input: a repository source root. Output:
immutable candidate records and explicit source-docstring contract gaps. This
is a conservative source inventory, not a proof about dynamic Python rebinding.
The runtime tests separately exercise every declared guarded entry.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class Boundary:
    module: str
    qualname: str
    path: str
    line: int
    reasons: tuple[str, ...]
    parameters: tuple[tuple[str, str | None], ...]
    docstring: str
    member_kind: str

    @property
    def identity(self) -> str:
        return self.module + '.' + self.qualname


@dataclass
class _Definition:
    module: str
    qualname: str
    path: str
    node: ast.FunctionDef | ast.AsyncFunctionDef
    public: bool
    runspec_member: bool
    member_kind: str
    bindings: dict[str, str]

    @property
    def identity(self):
        return self.module + '.' + self.qualname


def _qualified(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _qualified(node.value)
        return prefix + '.' + node.attr if prefix else None
    return None


def _annotation_text(node):
    if node is None:
        return None
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ast.unparse(node)


def _mentions_runspec(text, bindings):
    if not text:
        return False
    names = set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*', text))
    return 'RunSpec' in names or any(bindings.get(name, '').endswith('.RunSpec') for name in names)


def _imports(tree, module, package):
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom):
            prefix = module.split('.') if package else module.split('.')[:-1]
            if node.level:
                prefix = prefix[:len(prefix) - node.level + 1]
                target = '.'.join([*prefix, *([node.module] if node.module else [])])
            else:
                target = node.module or ''
            for alias in node.names:
                if alias.name != '*':
                    result[alias.asname or alias.name] = '.'.join(filter(None, (target, alias.name)))
    return result


def _definitions(root):
    source = root / 'src' / 'data_sheets_schema'
    if not source.is_dir():
        raise ValueError('RunSpec inventory requires src/data_sheets_schema')
    definitions = []
    # Path enumeration intentionally includes ignored and hidden source files.
    for path in sorted(source.rglob('*.py')):
        if path.is_symlink():
            raise ValueError(f'RunSpec inventory refuses a symlinked source: {path}')
        relative = path.relative_to(root)
        parts = list(path.relative_to(root / 'src').with_suffix('').parts)
        package = parts[-1] == '__init__'
        if package:
            parts.pop()
        module = '.'.join(parts)
        tree = ast.parse(path.read_text(), filename=str(relative))
        bindings = _imports(tree, module, package)

        def walk(statements, parents=(), inside_function=False, runspec_class=False, public_classes=True):
            for node in statements:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decorators = {_qualified(item) for item in node.decorator_list}
                    kind = ('property' if 'property' in decorators else
                            'cached_property' if 'cached_property' in decorators else
                            'classmethod' if 'classmethod' in decorators else
                            'staticmethod' if 'staticmethod' in decorators else
                            'method' if parents and not inside_function else 'function')
                    definitions.append(_Definition(
                        module, '.'.join((*parents, node.name)), str(relative), node,
                        not inside_function and public_classes and not node.name.startswith('_'),
                        runspec_class and not inside_function, kind, bindings))
                    walk(node.body, (*parents, node.name), True, False, public_classes)
                elif isinstance(node, ast.ClassDef):
                    is_runspec = node.name == 'RunSpec' or any(
                        _mentions_runspec(ast.unparse(base), bindings) for base in node.bases)
                    walk(node.body, (*parents, node.name), inside_function, is_runspec,
                         public_classes and not node.name.startswith('_'))
                else:
                    # Module/class conditional declarations are still public.
                    for field in ('body', 'orelse', 'finalbody'):
                        nested = getattr(node, field, None)
                        if isinstance(nested, list):
                            walk(nested, parents, inside_function, runspec_class, public_classes)
                    for handler in getattr(node, 'handlers', ()):
                        walk(handler.body, parents, inside_function, runspec_class, public_classes)
        walk(tree.body)
    return definitions


def discover(root: Path) -> tuple[Boundary, ...]:
    """Collect public signatures, annotations, constructors and factory callers.

    Untyped ``spec``/``specs`` parameters remain candidates until explicitly
    classified. Discovery is independent of docstrings and guard declarations.
    Nested/private factories participate in the call graph but are not exports.
    """
    root = Path(root)
    definitions = _definitions(root)
    identities = {definition.identity for definition in definitions}
    factory = set()
    calls = {}
    reasons = {}
    for definition in definitions:
        node = definition.node
        why = set()
        parameters = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        parameters += [arg for arg in (node.args.vararg, node.args.kwarg) if arg is not None]
        if any(arg.arg in {'spec', 'specs'} for arg in parameters):
            why.add('spec-signature')
        if any(_mentions_runspec(_annotation_text(arg.annotation), definition.bindings) for arg in parameters):
            why.add('RunSpec-parameter-annotation')
        if _mentions_runspec(_annotation_text(node.returns), definition.bindings):
            why.add('RunSpec-return-annotation')
            factory.add(definition.identity)
        if definition.runspec_member:
            why.add('RunSpec-public-member')
        targets = set()
        for item in ast.walk(node):
            if not isinstance(item, ast.Call):
                continue
            spelling = _qualified(item.func)
            if not spelling:
                continue
            first, *rest = spelling.split('.')
            resolved = '.'.join([definition.bindings.get(first, first), *rest])
            if (spelling == 'RunSpec' or resolved.endswith('.RunSpec')
                    or resolved.endswith('.RunSpec.from_render_spec')
                    or spelling == 'RunSpec.from_render_spec'):
                why.add('RunSpec-construction')
                factory.add(definition.identity)
            if spelling == 'cls' and definition.qualname.endswith('.from_render_spec'):
                why.add('RunSpec-construction')
                factory.add(definition.identity)
            for prefix in (definition.qualname.rpartition('.')[0], ''):
                local = '.'.join(filter(None, (definition.module, prefix, spelling)))
                if local in identities:
                    targets.add(local)
            if resolved in identities:
                targets.add(resolved)
        calls[definition.identity] = targets
        reasons[definition.identity] = why
    while True:
        additions = {name for name, targets in calls.items() if targets & factory} - factory
        if not additions:
            break
        factory.update(additions)
    result = []
    for definition in definitions:
        why = reasons[definition.identity]
        if definition.identity in factory:
            why.add('RunSpec-factory-or-caller')
        if not definition.public or not why:
            continue
        node = definition.node
        parameters = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        parameters += [arg for arg in (node.args.vararg, node.args.kwarg) if arg is not None]
        result.append(Boundary(
            definition.module, definition.qualname, definition.path, node.lineno,
            tuple(sorted(why)), tuple((arg.arg, _annotation_text(arg.annotation)) for arg in parameters),
            ast.get_docstring(node) or '', definition.member_kind))
    return tuple(sorted(result, key=lambda candidate: (candidate.path, candidate.line, candidate.qualname)))


def contract(boundary: Boundary) -> tuple[str | None, str | None]:
    """Read an explicit source contract; never infer an exemption from a name."""
    declarations = re.findall(r'^RunSpec boundary:\s*(\S+)\s*$', boundary.docstring, re.MULTILINE)
    if len(declarations) != 1:
        return None, 'needs exactly one RunSpec boundary declaration'
    mode = declarations[0]
    if mode == 'guarded':
        return mode, None
    if mode not in {'validated-caller', 'unrelated'}:
        return None, 'unsupported RunSpec boundary declaration: ' + mode
    if not re.search(r'^RunSpec precondition:\s*\S', boundary.docstring, re.MULTILINE):
        return None, 'needs a stated RunSpec precondition in its source docstring'
    if mode == 'unrelated':
        if set(boundary.reasons) != {'spec-signature'}:
            return None, 'a RunSpec annotation, factory or member cannot be classified unrelated'
        selected = [annotation for name, annotation in boundary.parameters if name in {'spec', 'specs'}]
        if not selected or any(not annotation or re.search(r'\b(Any|object|RunSpec)\b', annotation) for annotation in selected):
            return None, 'an unrelated spec parameter requires an explicit other-type annotation'
    return mode, None


def missing_contracts(root: Path) -> tuple[str, ...]:
    """Return all unresolved candidates, including ignored/hidden Python files."""
    missing = []
    for candidate in discover(root):
        _, error = contract(candidate)
        if error:
            missing.append(f'{candidate.path}:{candidate.line} {candidate.identity}: {error}')
    return tuple(missing)
