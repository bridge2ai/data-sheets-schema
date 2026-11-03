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
    owner_class: str | None
    member_kind: str
    bindings: dict[str, str]
    call_bindings: dict[str, str]

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


def _mentions_runspec(text, bindings, runspec_classes=()):
    if not text:
        return False
    names = set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*', text))
    if ('RunSpec' in names or any(bindings.get(name, '').endswith('.RunSpec')
            or bindings.get(name) in runspec_classes for name in names)):
        return True
    # Preserve the full module-qualified spelling: splitting m.Derived into
    # unrelated identifiers loses a known subclass reached through an import.
    # Parse syntax only; annotations and their referenced modules are not run.
    try:
        annotation = ast.parse(text, mode='eval')
    except SyntaxError:
        return False
    return any(spelling and _resolve(spelling, bindings) in runspec_classes
               for node in ast.walk(annotation)
               for spelling in (_qualified(node),))


def _scope_nodes(tree):
    """Walk one lexical namespace, including control-flow declaration arms."""
    def visit(node):
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        for child in ast.iter_child_nodes(node):
            yield from visit(child)
    for statement in tree.body:
        yield from visit(statement)


def _resolve(spelling, bindings):
    first, *rest = spelling.split('.')
    return '.'.join([bindings.get(first, first), *rest])


def _imports(tree, module, package, *, inherited=None, qualname=''):
    """Resolve visible imports/simple aliases without flattening child scopes.

    Annotation bindings belong to the enclosing scope. Function-local imports
    are used only for that function's calls, never another function's annotation.
    """
    visible = dict(inherited or {})
    result = {}
    nodes = tuple(_scope_nodes(tree))
    for node in nodes:
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
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result[node.name] = '.'.join(filter(None, (module, qualname, node.name)))
    visible.update(result)
    # Follow finite source aliases to imported or declared functions/classes.
    # Unresolved/dynamic assignments are not treated as proof of a new type.
    aliases = []
    for node in nodes:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        spelling = _qualified(value)
        if spelling:
            aliases.extend((target.id, spelling) for target in targets if isinstance(target, ast.Name))
    for _ in range(len(aliases) + 1):
        changed = False
        for target, spelling in aliases:
            if spelling.split('.')[0] not in visible:
                continue
            resolved = _resolve(spelling, visible)
            if visible.get(target) != resolved:
                visible[target] = result[target] = resolved
                changed = True
        if not changed:
            break
    return result


def _definitions(root):
    source = root / 'src' / 'data_sheets_schema'
    if not source.is_dir():
        raise ValueError('RunSpec inventory requires src/data_sheets_schema')
    definitions = []
    classes = []
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

        def walk(statements, parents=(), inside_function=False, owner_class=None,
                 public_classes=True, visible=None):
            visible = bindings if visible is None else visible
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
                        owner_class if not inside_function else None, kind, visible,
                        {**visible, **_imports(node, module, package, inherited=visible,
                                             qualname='.'.join((*parents, node.name)))}))
                    local = definitions[-1].call_bindings
                    walk(node.body, (*parents, node.name), True, None, public_classes, local)
                elif isinstance(node, ast.ClassDef):
                    identity = '.'.join((module, *parents, node.name))
                    classes.append((identity, node, visible))
                    local = {**visible, **_imports(node, module, package, inherited=visible,
                                                  qualname='.'.join((*parents, node.name)))}
                    walk(node.body, (*parents, node.name), inside_function, identity,
                         public_classes and not node.name.startswith('_'), local)
                else:
                    # Module/class conditional declarations are still public.
                    for field in ('body', 'orelse', 'finalbody'):
                        nested = getattr(node, field, None)
                        if isinstance(nested, list):
                            walk(nested, parents, inside_function, owner_class, public_classes, visible)
                    for handler in getattr(node, 'handlers', ()):
                        walk(handler.body, parents, inside_function, owner_class, public_classes, visible)
                    for case in getattr(node, 'cases', ()):
                        walk(case.body, parents, inside_function, owner_class, public_classes, visible)
        walk(tree.body)
    return definitions, classes


def discover(root: Path) -> tuple[Boundary, ...]:
    """Collect public signatures, annotations, constructors and factory callers.

    Untyped ``spec``/``specs`` parameters remain candidates until explicitly
    classified. Discovery is independent of docstrings and guard declarations.
    Nested/private factories participate in the call graph but are not exports.
    """
    root = Path(root)
    definitions, classes = _definitions(root)
    runspec_classes = {identity for identity, node, _ in classes if node.name == 'RunSpec'}
    while True:
        additions = {identity for identity, node, bindings in classes
                     if any(_mentions_runspec(ast.unparse(base), bindings, runspec_classes)
                            for base in node.bases)} - runspec_classes
        if not additions:
            break
        runspec_classes.update(additions)
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
        if any(_mentions_runspec(_annotation_text(arg.annotation), definition.bindings, runspec_classes)
               for arg in parameters):
            why.add('RunSpec-parameter-annotation')
        if _mentions_runspec(_annotation_text(node.returns), definition.bindings, runspec_classes):
            why.add('RunSpec-return-annotation')
            factory.add(definition.identity)
        if definition.owner_class in runspec_classes:
            why.add('RunSpec-public-member')
        targets = set()
        for item in ast.walk(node):
            if not isinstance(item, ast.Call):
                continue
            spelling = _qualified(item.func)
            if not spelling:
                continue
            resolved = _resolve(spelling, definition.call_bindings)
            if (spelling == 'RunSpec' or resolved.endswith('.RunSpec')
                    or resolved.endswith('.RunSpec.from_render_spec')
                    or spelling == 'RunSpec.from_render_spec'
                    or resolved in runspec_classes
                    or resolved.endswith('.from_render_spec')
                    and resolved.removesuffix('.from_render_spec') in runspec_classes):
                why.add('RunSpec-construction')
                factory.add(definition.identity)
            if spelling == 'cls' and definition.qualname.endswith('.from_render_spec'):
                why.add('RunSpec-construction')
                factory.add(definition.identity)
            for prefix in (definition.qualname, definition.qualname.rpartition('.')[0], ''):
                local = '.'.join(filter(None, (definition.module, prefix, spelling)))
                if local in identities:
                    targets.add(local)
            if resolved in identities:
                targets.add(resolved)
        # Conditional declarations may share a qualified name. Retain the
        # conservative union so a later untyped arm cannot erase an earlier
        # RunSpec contract or factory call; every visible arm is then reviewed.
        calls.setdefault(definition.identity, set()).update(targets)
        reasons.setdefault(definition.identity, set()).update(why)
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
