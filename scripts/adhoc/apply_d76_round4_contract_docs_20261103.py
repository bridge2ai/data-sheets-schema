#!/usr/bin/env python3
"""PR #5213: apply reviewed RunSpec contracts as function docstrings only.

2026-11-03. Inputs: exact SHA-bound contract proposal, protected sidecar and
selected unchanged source files. Output: fresh external JSON containing every
proposed/persisted diff and source/protected pins. Default is a read-only plan;
--apply changes only selected nonprotected function docstrings. Use one --only
file as a canary before applying the remaining files with --exclude.
"""
import argparse
import ast
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import tempfile
import textwrap


SHARED = 'src/data_sheets_schema/shared_generation.py'
LATCH = 'src/data_sheets_schema/latch_journal.py'
SIDECAR = 'tests/utils/run_spec_boundary_contracts.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular non-symlink source required: ' + str(path))
    return path.read_bytes()


def functions(tree, parents=()):
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = '.'.join((*parents, node.name))
            yield (name, node.lineno), node
            yield from functions(node, (*parents, node.name))
        elif isinstance(node, ast.ClassDef):
            yield from functions(node, (*parents, node.name))
        else:
            yield from functions(node, parents)


def has_doc(node):
    return (bool(node.body) and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str))


class WithoutFunctionDocs(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        if has_doc(node):
            node.body = node.body[1:]
        return self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


def executable_ast(tree):
    return ast.dump(WithoutFunctionDocs().visit(copy.deepcopy(tree)), include_attributes=False)


def click_callback(node):
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Attribute) and target.attr in {'command', 'group'}:
            return True
    return False


def click_help_proof(name, before, after):
    # Render only AST-extracted help through installed Click; never import or
    # execute the generation callback or its source module.
    import click
    import click.core
    import click.utils

    rendered = []
    for docstring in (before, after):
        command = click.Command(name, help=docstring or None)
        with click.Context(command) as context:
            rendered.append({'full': command.get_help(context),
                             'short': command.get_short_help_str()})
    if rendered[0] != rendered[1]:
        raise ValueError('Click help changed after contract insertion: ' + name)
    return {'name': name, 'full_help_unchanged': True, 'short_help_unchanged': True,
            'full_help_sha256': sha(rendered[0]['full'].encode()),
            'short_help_sha256': sha(rendered[0]['short'].encode()),
            'click_source_sha256': {str(Path(module.__file__)): sha(read_regular(Path(module.__file__)))
                                     for module in (click.core, click.utils)}}


def protected_snapshot(source, sidecar_raw):
    document = json.loads(sidecar_raw)
    if document.get('approval', {}).get('authorized') is not True:
        raise ValueError('protected-contract ruling must be explicit')
    shared = read_regular(source / SHARED)
    if sha(shared) != document['shared_generation_sha256']:
        raise ValueError('protected shared-generation source changed')
    raw = read_regular(source / LATCH)
    lines = raw.splitlines(keepends=True)
    found = [node for (_, _), node in functions(ast.parse(raw))
             if node.name == 'refuse_legacy_execution']
    if len(found) != 1:
        raise ValueError('protected legacy refusal definition must be unique')
    node = found[0]
    start = min([node.lineno, *(item.lineno for item in node.decorator_list)])
    actual = sha(b''.join(lines[start - 1:node.end_lineno]))
    expected = [row['function_sha256'] for row in document['contracts']
                if row['identity'] == 'data_sheets_schema.latch_journal.refuse_legacy_execution']
    if expected != [actual]:
        raise ValueError('protected legacy refusal bytes/docstring changed')
    return {'shared_generation_sha256': sha(shared), 'legacy_refusal_function_sha256': actual,
            'sidecar_sha256': sha(sidecar_raw)}


def rewritten(raw, rows, relative):
    tree = ast.parse(raw, filename=relative)
    available = dict(functions(tree))
    lines = raw.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    edits = []
    click_docs = []
    for row in rows:
        identity = row['identity']
        if row['protected_no_source_edit'] or relative == SHARED or identity.endswith('.latch_journal.refuse_legacy_execution'):
            raise ValueError('protected source may not be edited')
        if row['classification_pending']:
            raise ValueError('unclassified contract cannot be applied')
        mode = row['proposed_mode']
        if mode not in {'guarded', 'validated-caller', 'unrelated'}:
            raise ValueError('unsupported contract mode')
        qualname = identity.removeprefix('data_sheets_schema.' + relative.removeprefix('src/data_sheets_schema/').removesuffix('.py').replace('/', '.') + '.')
        # Use the path-derived module exactly; no suffix-only function matching.
        node = available.get((qualname, row['line']))
        if node is None or ast.get_docstring(node) != (row['existing_docstring'] or None):
            raise ValueError('reviewed function/docstring differs: ' + identity)
        old = ast.get_docstring(node) or ''
        if 'RunSpec boundary:' in old:
            raise ValueError('function already has a boundary declaration: ' + identity)
        block = 'RunSpec boundary: ' + mode
        if mode != 'guarded':
            precondition = row['proposed_precondition']
            if not isinstance(precondition, str) or not precondition.strip():
                raise ValueError('caller contract requires its reviewed precondition')
            block += '\n\n' + textwrap.fill('RunSpec precondition: ' + precondition, width=88)
        if click_callback(node):
            value = old + ('\n\n' if old else '') + '\f\n\n' + block
            click_docs.append((qualname, node.name, old))
        else:
            value = old + ('\n\n' if old else '') + block
        escaped = value.replace('\\', '\\\\').replace('"""', '\\"\\"\\"').replace('\f', '\\f')
        first = node.body[0]
        if first.lineno == node.lineno:
            raise ValueError('inline function body requires separate reviewed formatting')
        indent = lines[first.lineno - 1][:first.col_offset].decode()
        parts = escaped.split('\n')
        literal = ('"""' + parts[0]
                   + ''.join('\n' + (indent + line if line.strip() else '') for line in parts[1:])
                   + '\n' + indent + '"""')
        if has_doc(node):
            start = offsets[first.lineno - 1] + first.col_offset
            end = offsets[first.end_lineno - 1] + first.end_col_offset
            replacement = literal.encode()
        else:
            start = end = offsets[first.lineno - 1]
            replacement = (indent + literal + '\n').encode()
        edits.append((start, end, replacement))
    result = raw
    for start, end, replacement in sorted(edits, reverse=True):
        result = result[:start] + replacement + result[end:]
    after_tree = ast.parse(result, filename=relative)
    if executable_ast(tree) != executable_ast(after_tree):
        raise ValueError('change extends beyond function docstrings: ' + relative)
    after_functions = {}
    for (qualname, _), node in functions(after_tree):
        after_functions.setdefault(qualname, []).append(node)
    help_proofs = []
    for qualname, name, old in click_docs:
        candidates = after_functions[qualname]
        if len(candidates) != 1:
            raise ValueError('Click callback must have a unique qualified definition: ' + qualname)
        help_proofs.append(click_help_proof(name, old, ast.get_docstring(candidates[0])))
    return result, help_proofs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--proposal', type=Path, required=True)
    parser.add_argument('--proposal-sha256', required=True)
    parser.add_argument('--sidecar-sha256', required=True)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument('--only', action='append', default=[])
    scope.add_argument('--exclude', action='append', default=[])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    report = args.report
    if (not report.is_absolute() or '..' in report.parts or report.exists() or report.is_symlink()
            or report.parent.resolve(strict=True) != report.parent or report.is_relative_to(source)):
        raise ValueError('fresh physical absolute report path outside source required')
    proposal_raw = read_regular(args.proposal)
    if sha(proposal_raw) != args.proposal_sha256:
        raise ValueError('proposal SHA differs')
    proposal = json.loads(proposal_raw)
    sidecar_raw = read_regular(source / SIDECAR)
    if sha(sidecar_raw) != args.sidecar_sha256:
        raise ValueError('sidecar SHA differs')
    protected = protected_snapshot(source, sidecar_raw)
    groups = {}
    for row in proposal['candidates']:
        if not row['protected_no_source_edit']:
            groups.setdefault(row['path'], []).append(row)
    if set(args.only + args.exclude) - groups.keys():
        raise ValueError('selected path is not in the reviewed nonprotected roster')
    selected = sorted(set(args.only) if args.only else groups.keys() - set(args.exclude))
    if not selected:
        raise ValueError('no source files selected')
    plans = []
    for relative in selected:
        path = source / relative
        if (not path.is_relative_to(source) or '..' in Path(relative).parts
                or path.resolve(strict=True) != path):
            raise ValueError('source path must stay physically in the selected tree')
        before = read_regular(path)
        if sha(before) != proposal['candidate_source_sha256'][relative]:
            raise ValueError('reviewed source hash differs: ' + relative)
        after, help_proofs = rewritten(before, groups[relative], relative)
        plans.append((path, before, after, {
            'path': relative, 'functions': [row['identity'] for row in groups[relative]],
            'before_sha256': sha(before), 'after_sha256': sha(after),
            'function_docstrings_only': True, 'persisted': False,
            'click_help_proofs': help_proofs,
            'diff': ''.join(difflib.unified_diff(before.decode().splitlines(keepends=True),
                                               after.decode().splitlines(keepends=True),
                                               fromfile='a/' + relative, tofile='b/' + relative)),
        }))
    result = {'apply_requested': args.apply, 'complete': False, 'source': str(source),
              'producer_sha256': sha(read_regular(Path(__file__))),
              'proposal_sha256': sha(proposal_raw), 'protected_before': protected,
              'files': [row for _, _, _, row in plans]}
    with report.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    try:
        for path, before, after, row in plans:
            if read_regular(path) != before:
                raise ValueError('selected source changed before application: ' + str(path))
            if args.apply:
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.d76-contract-', delete=False) as stream:
                        temporary = Path(stream.name)
                        stream.write(after)
                    os.chmod(temporary, path.stat().st_mode & 0o777)
                    os.replace(temporary, path)
                    temporary = None
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
                if read_regular(path) != after:
                    raise ValueError('persisted source differs: ' + str(path))
                row['persisted'] = True
        if read_regular(source / SIDECAR) != sidecar_raw:
            raise ValueError('protected sidecar changed during application')
        result['protected_after'] = protected_snapshot(source, sidecar_raw)
        if result['protected_after'] != protected:
            raise ValueError('protected source changed during application')
        result['complete'] = True
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        report.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'report': str(report), 'sha256': sha(read_regular(report)),
                      'files': len(plans), 'functions': sum(len(row['functions']) for _, _, _, row in plans),
                      'applied': args.apply, 'protected_unchanged': True}, indent=2))


if __name__ == '__main__':
    main()
