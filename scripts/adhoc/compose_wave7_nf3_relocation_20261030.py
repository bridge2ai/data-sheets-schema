#!/usr/bin/env python3
# Purpose: reproduce the reviewed #5213/#5399 relocation union without importing E3x history.
# Inputs: pinned local Git blobs; outputs: resolver, CLI, report and 37-function test union.
# Ref: #5213 NF3 prompt/check6 relocation review; 2026-10-30. No remote operations.
import ast
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
COPIES = {
    'src/data_sheets_schema/evaluation/arm_comparison.py': '9fc613b4c14c1fc6d0c7faae8d4179f1dfc6c1a7',
    'scripts/arm_comparison.py': 'db727038a53555da8d0e0a00dcca001bf9b3830f',
    'notes/arm_comparison.md': '6d86073e95bf4c283642675c9c731243f504a7e1',
}
E3X_TESTS = '28506eabde40e9f807b2227ab5a5901319832c25'
PACKET_TESTS = 'c465a109e7328b1181e4d6f4e8a9d9145ca086d5'
NAMES = {
    'test_absolute_owned_manifest_keeps_its_exact_git_path',
    'test_foreign_tail_does_not_follow_an_escape_symlink',
    'test_unowned_or_malformed_paths_remain_unknown',
}


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def blob(oid):
    data = git('cat-file', 'blob', oid)
    actual = subprocess.check_output(['git', 'hash-object', '--stdin'], input=data).decode().strip()
    if actual != oid:
        raise ValueError(f'Git blob mismatch {oid}')
    return data


def main():
    copies = {path: blob(oid) for path, oid in COPIES.items()}
    target = blob(E3X_TESTS).decode()
    source = blob(PACKET_TESTS).decode()
    existing = ast.parse(target)
    if NAMES & {node.name for node in existing.body if isinstance(node, ast.FunctionDef)}:
        raise ValueError('Union preimage already contains packet-only cases')
    lines = source.splitlines(keepends=True)
    found = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name in NAMES:
            start = min([node.lineno, *(deco.lineno for deco in node.decorator_list)]) - 1
            target += '\n\n' + ''.join(lines[start:node.end_lineno])
            found.add(node.name)
    union = ast.parse(target)
    top = sum(isinstance(node, ast.FunctionDef) and node.name.startswith('test_') for node in union.body)
    total = sum(isinstance(node, ast.FunctionDef) and node.name.startswith('test_') for node in ast.walk(union))
    if found != NAMES or (top, total) != (37, 69):
        raise ValueError(f'Unexpected test union: {found}, {top}, {total}')
    copies['tests/test_arm_comparison.py'] = target.encode()
    helper = ROOT / 'scripts/adhoc/preserve_wave5_validation_20261028.py'
    if helper.read_bytes() != blob('09c84644d1a372e36a2dacaf3b001117cb220e06'):
        raise ValueError('Reviewed helper changed; historical manifests must not be restamped')
    for path in ('src/data_sheets_schema/shared_generation.py', 'src/download/prompts/canonical_hashes.yaml'):
        if (ROOT / path).read_bytes() != git('show', 'fa304cd803396307263407592455be548d837bcd:' + path):
            raise ValueError(f'Protected source differs from pinned main: {path}')
    for path, raw in copies.items():
        (ROOT / path).write_bytes(raw)
        print(path)
    print(f'test_functions: top_level={top}, including_methods={total}')


if __name__ == '__main__':
    main()
