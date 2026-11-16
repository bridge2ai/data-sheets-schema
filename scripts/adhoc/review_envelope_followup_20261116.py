"""Read-only PR 5968 follow-up scope review, 2026-11-16.

Inputs: baseline commit and worktree files. Output: JSON syntax, scope and
unchanged assertion-body evidence. Never updates files, pins or Git state.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode()


def body(tree, name):
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.dump(ast.Module(body=node.body, type_ignores=[]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='ddf50f2df6a2cfa673f72e44a429bedf4a65ed65')
    args = parser.parse_args()
    tracked = git('diff', '--name-only', args.base).splitlines()
    untracked = git('ls-files', '--others', '--exclude-standard').splitlines()
    files = sorted(set(tracked + untracked))
    protected = ['src/data_sheets_schema/shared_generation.py',
                 'src/data_sheets_schema/api_runner.py',
                 'src/download/prompts/canonical_hashes.yaml',
                 'tests/utils/run_spec_boundary_contracts.json']
    assert not set(files).intersection(protected)
    assert all(path.startswith(('tests/', 'scripts/adhoc/')) for path in files)
    diff = git('diff', '--unified=0', args.base)
    added = '\n'.join(line[1:] for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++'))
    assert chr(64) not in added
    hashes = {}
    for relative in files:
        raw = (ROOT / relative).read_bytes()
        if relative.endswith('.py'):
            ast.parse(raw)
        if relative in untracked:
            assert bytes([64]) not in raw
        hashes[relative] = hashlib.sha256(raw).hexdigest()
    relative = 'tests/test_typed_json_parse_cache.py'
    before = ast.parse(git('show', args.base + ':' + relative))
    after = ast.parse((ROOT / relative).read_text())
    preserved = {}
    names = {node.name for node in after.body if isinstance(node, ast.FunctionDef)}
    for name in ('test_replaced_copy_alias_disables_shared_values',
                 'test_interpreter_integer_limit_change_refuses_a_warm_value'):
        target = '_assert_' + name[5:]
        if target not in names:
            target = name
        preserved[name] = body(before, name) == body(after, target)
        assert preserved[name]
    print(json.dumps({'base': args.base, 'head': git('rev-parse', 'HEAD').strip(),
        'protected_files_unchanged': True, 'test_and_helper_only': True,
        'python_syntax_valid': True, 'added_text_has_no_prohibited_character': True,
        'identity_assertion_bodies_unchanged': preserved, 'files_sha256': hashes}, indent=2))


if __name__ == '__main__':
    main()
