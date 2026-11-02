#!/usr/bin/env python3
"""Make one explicit scratch-only ordering mutant for PR #5213, 2026-11-02.

Inputs: exact committed head, pristine source and distinct fresh archive copy,
SHA-bound scratch archive proof, one selected public route, fresh evidence dir.
Outputs: scratch-only two-file diff, original/mutated source hashes and complete
source manifests; no test launch, Git writes, network or source-authoring edits.
CLI mutants deliberately relocate nested guards too: otherwise the nested
library guard could mask a misplaced CLI guard. Inspection mutants put D76
after model/body access, never invent an execution inventory in inspection.
"""
import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('d76_order_source_proof',
                                             HERE / 'd76_suite_common_20261031.py')
common = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(common)
FILES = ('src/data_sheets_schema/api_runner.py', 'src/data_sheets_schema/cli/api.py')
ROUTES = ('execute', 'dry-run', 'plan', 'resolve', 'cli-run', 'cli-plan', 'cli-render', 'batch')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def git(root, *args, check=True):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0', GIT_CONFIG_GLOBAL='/dev/null',
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_COUNT='1',
               GIT_CONFIG_KEY_0='protocol.allow', GIT_CONFIG_VALUE_0='never')
    return subprocess.run(['git', '--no-replace-objects', '-C', str(root), *args],
                          env=env, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def function(tree, name):
    values = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(values) != 1:
        raise ValueError(f'expected one top-level function {name}')
    return values[0]


def called(node, name):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name


def direct_call_statement(node, name):
    return isinstance(node, ast.Expr) and called(node.value, name)


def statement_containing(fn, call_name):
    values = [node for node in fn.body
              if any(called(child, call_name) for child in ast.walk(node))]
    if len(values) != 1:
        raise ValueError(f'expected one direct statement containing {call_name} in {fn.name}')
    return values[0]


def remove_guard(source, name, guard):
    tree = ast.parse(source)
    fn = function(tree, name)
    values = [node for node in ast.walk(fn) if direct_call_statement(node, guard)]
    if len(values) != 1 or values[0].lineno != values[0].end_lineno:
        raise ValueError(f'expected one single-line {guard} in {name}')
    lines = source.splitlines(keepends=True)
    del lines[values[0].lineno - 1]
    return ''.join(lines)


def insert_after(source, name, boundary, statement):
    fn = function(ast.parse(source), name)
    anchor = statement_containing(fn, boundary)
    lines = source.splitlines(keepends=True)
    lines.insert(anchor.end_lineno, statement)
    return ''.join(lines)


def mutate(originals, route):
    api, cli = originals[FILES[0]], originals[FILES[1]]
    description = []
    if route == 'execute':
        api = remove_guard(api, 'execute', '_require_registered_input_spellings')
        api = insert_after(api, 'execute', '_prelock_checks',
                           '    _require_registered_input_spellings(spec)\n')
        description.append('execute D76 moved after unchanged _prelock_checks in both resume modes')
    elif route == 'dry-run':
        api = remove_guard(api, 'plan', '_require_registered_input_spellings')
        api = remove_guard(api, 'resolve_prompt', '_require_registered_input_spellings')
        fn = function(ast.parse(api), 'execute')
        values = [node for node in fn.body if isinstance(node, ast.If)
                  and isinstance(node.test, ast.Name) and node.test.id == 'dry_run']
        if len(values) != 1 or len(values[0].body) != 1:
            raise ValueError('dry-run delegation changed')
        original = values[0].body[0]
        if not isinstance(original, ast.Return) or not called(original.value, 'plan'):
            raise ValueError('dry-run is no longer the direct plan delegation')
        lines = api.splitlines(keepends=True)
        lines[original.lineno - 1:original.end_lineno] = [
            '        _d76_mutant_plan = plan(spec)\n',
            '        _require_registered_input_spellings(spec)\n',
            '        return _d76_mutant_plan\n']
        api = ''.join(lines)
        description.append('dry-run guard moved after planning, nested plan/renderer guards removed only here')
    elif route in ('plan', 'resolve'):
        name, boundary = ('plan', '_model_settings') if route == 'plan' else ('resolve_prompt', 'prompt_body')
        api = remove_guard(api, name, '_require_registered_input_spellings')
        api = insert_after(api, name, boundary, '    _require_registered_input_spellings(spec)\n')
        description.append(f'{name} guard moved after its real {boundary} read boundary')
    elif route == 'batch':
        cli = remove_guard(cli, 'batch_cmd', '_require_input_binding')
        fn = function(ast.parse(cli), 'batch_cmd')
        candidates = [node for node in fn.body if isinstance(node, ast.If)
                      and isinstance(node.test, ast.Name) and node.test.id == 'roster'
                      and any(called(child, '_shared_current') for child in ast.walk(node))]
        if len(candidates) != 1:
            raise ValueError('expected exactly one initial roster authority block')
        lines = cli.splitlines(keepends=True)
        lines.insert(candidates[0].end_lineno,
                     '    for s in specs:\n        _require_input_binding(s)\n')
        cli = ''.join(lines)
        description.append('batch per-spec D76 checks moved after first _shared_current; exercise invalid second spec')
    else:
        name = {'cli-run': 'run_cmd', 'cli-plan': 'plan_cmd', 'cli-render': 'render_prompt_cmd'}[route]
        cli = remove_guard(cli, name, '_require_input_binding')
        # Retain the public route's deliberately late D76 call, but prevent a
        # nested guard from concealing the route-order defect under test.
        api = remove_guard(api, 'resolve_prompt', '_require_registered_input_spellings')
        if route in ('cli-run', 'cli-plan'):
            api = remove_guard(api, 'plan', '_require_registered_input_spellings')
        boundary = '_plan_or_refuse' if route == 'cli-plan' else '_shared_current'
        cli = insert_after(cli, name, boundary, '    _require_input_binding(spec)\n')
        description.append(f'{name} D76 moved after {boundary}; nested plan/render guards removed only in this mutant')
    result = {FILES[0]: api, FILES[1]: cli}
    for text in result.values():
        ast.parse(text)
    return result, description


def physical(path):
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('absolute nontraversing path required')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError('symlinked path refused')
    return path.resolve(strict=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--head', required=True)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('--archive-proof', required=True, type=Path)
    parser.add_argument('--archive-proof-sha256', required=True)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--route', required=True, choices=ROUTES)
    args = parser.parse_args()
    source, scratch = physical(args.source), physical(args.scratch)
    if not re.fullmatch(r'[0-9a-f]{40}', args.head):
        raise ValueError('full commit SHA required')
    if (source == scratch or source.is_relative_to(scratch) or scratch.is_relative_to(source)
            or scratch == HERE.parents[1]
            or not scratch.name.startswith('codex-5213-order-mutant-')):
        raise ValueError('only a distinct dedicated codex-5213-order-mutant-* archive may be edited')
    if not args.evidence.is_absolute() or '..' in args.evidence.parts or args.evidence.exists():
        raise ValueError('fresh absolute evidence directory required')
    parent = physical(args.evidence.parent)
    if parent.is_relative_to(source) or parent.is_relative_to(scratch):
        raise ValueError('evidence must be outside both checkouts')
    proof_raw = args.archive_proof.read_bytes()
    if sha(proof_raw) != args.archive_proof_sha256:
        raise ValueError('scratch archive proof digest mismatch')
    proof = json.loads(proof_raw)
    if proof['head'] != args.head or Path(proof['destination']) != scratch:
        raise ValueError('scratch archive proof identity mismatch')
    snapshots = {}
    for label, root in (('source', source), ('scratch', scratch)):
        if git(root, 'symbolic-ref', '-q', 'HEAD', check=False).returncode != 1:
            raise ValueError('both copies must be detached archives, never authoring branches')
        snapshots[label] = common.source(root)
        if (snapshots[label]['head'] != args.head or snapshots[label]['tracked_exact'] is not True
                or snapshots[label]['tree'] != proof['git_tree']
                or git(root, 'status', '--porcelain=v1', '--untracked-files=all').stdout
                or git(root, 'ls-files', '--others').stdout):
            raise ValueError(f'{label} is not pristine at the pinned archive head')
    if snapshots['source'] != snapshots['scratch']:
        raise ValueError('source and scratch tracked bytes differ before mutation')
    originals = {}
    for name in FILES:
        original, target = source / name, scratch / name
        if original.samefile(target):
            raise ValueError('scratch target aliases a source inode')
        originals[name] = target.read_text()
    replacements, description = mutate(originals, args.route)
    changed = [name for name in FILES if replacements[name] != originals[name]]
    if not changed:
        raise ValueError('mutation made no change')
    args.evidence.mkdir()
    save(args.evidence / 'source-before.json', snapshots['source'])
    save(args.evidence / 'scratch-before.json', snapshots['scratch'])
    patch = ''.join(''.join(difflib.unified_diff(originals[name].splitlines(keepends=True),
                     replacements[name].splitlines(keepends=True),
                     fromfile='a/' + name, tofile='b/' + name)) for name in changed)
    with (args.evidence / 'mutation.diff').open('x') as stream:
        stream.write(patch)
    # All path/proof/syntax checks precede the first scratch mutation.
    for name in changed:
        (scratch / name).write_text(replacements[name])
    after = common.source(scratch)
    source_after = common.source(source)
    save(args.evidence / 'source-after.json', source_after)
    save(args.evidence / 'scratch-after.json', after)
    differences = sorted(name for name, row in after['entries'].items()
                         if row != snapshots['scratch']['entries'][name])
    if source_after != snapshots['source'] or differences != sorted(changed):
        raise ValueError('unexpected source/scratch mutation; retain evidence and stop')
    save(args.evidence / 'mutation.json', {
        'head': args.head, 'route': args.route, 'source': str(source), 'scratch': str(scratch),
        'archive_proof': str(args.archive_proof), 'archive_proof_sha256': args.archive_proof_sha256,
        'description': description, 'changed_files': changed, 'source_unchanged': True,
        'scope': 'ordering mutant only; not a production candidate or validation pass',
        'files': {name: {'before_sha256': sha(originals[name].encode()),
                         'after_sha256': sha(replacements[name].encode())} for name in changed},
        'diff_sha256': sha(patch.encode()), 'tests_executed': False})
    print(args.evidence / 'mutation.json')


if __name__ == '__main__':
    main()
