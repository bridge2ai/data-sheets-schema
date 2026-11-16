"""Read-only scope review for issue 6273 and CI repairs, 2026-11-16.

Inputs: explicit base revision and working tree. Output: JSON scope, syntax and unchanged-body
checks on stdout. This does not execute tests or claim scanner derivation.
"""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


def body(source, name):
    node = next(node for node in ast.parse(source).body
                if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.get_source_segment(source, node)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    args = parser.parse_args()
    files = git('diff', '--name-only', args.base).splitlines()
    protected = {
        'src/data_sheets_schema/shared_generation.py',
        'src/data_sheets_schema/api_runner.py',
        'src/download/prompts/canonical_hashes.yaml',
        'tests/utils/run_spec_boundary_contracts.json',
    }
    comparisons = {}
    for path, names in {
        'src/data_sheets_schema/typed_audit.py': ['prepare', '_prepare'],
        'tests/test_typed_audit_derivations.py': [
            'test_real_cached_requests_assembly_and_fresh_final_check_are_identical'],
    }.items():
        before = git('show', args.base + ':' + path)
        after = (ROOT / path).read_text()
        for name in names:
            comparisons[path + '::' + name] = body(before, name) == body(after, name)
    syntax = []
    loader_test = 'tests/test_native_catalog_fast_guards.py'
    original_name = 'test_loader_transition_with_same_marker_and_empty_slot_cache'
    comparisons[loader_test + '::original_transition_assertions'] = (
        body(git('show', args.base + ':' + loader_test), original_name).splitlines()[1:]
        == body((ROOT / loader_test).read_text(), '_assert_loader_transition_with_same_marker_and_empty_slot_cache').splitlines()[1:]
    )
    for path in files:
        if path.endswith('.py'):
            ast.parse((ROOT / path).read_text())
            syntax.append(path)
    added = [line[1:] for line in git('diff', '--unified=0', args.base).splitlines()
             if line.startswith('+') and not line.startswith('+++')]
    result = {
        'base': git('rev-parse', args.base).strip(),
        'unchanged_bodies': comparisons,
        'protected_changes': sorted(set(files) & protected),
        'syntax_checked': syntax,
        'added_text_contains_forbidden_character': any(chr(64) in line for line in added),
        'source_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                          for path in files if path.startswith('src/')},
    }
    print(json.dumps(result, indent=2))
    assert all(comparisons.values())
    assert not result['protected_changes']
    assert not result['added_text_contains_forbidden_character']


if __name__ == '__main__':
    main()
