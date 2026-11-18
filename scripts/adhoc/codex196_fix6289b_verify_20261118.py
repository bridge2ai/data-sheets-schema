"""Verify bounded F1/F2 changes for PR 5968 issue 6289; 2026-11-18.

Inputs: assigned checkout and immutable 7b9497fc1 baseline.
Outputs: JSON evidence for historical bytes, assertions, effective weights and pins.
No edits, provider calls or lifecycle execution.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

BASE = '7b9497fc17672e9ede94cebdd556085c8119f3cc'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    assert not subprocess.check_output(['git', 'diff', '--name-only', BASE, '--', 'src'], cwd=root)
    def blob(path, revision=BASE):
        return subprocess.check_output(['git', 'show', revision + ':' + path], cwd=root)
    unchanged = {}
    for name in ('src/data_sheets_schema/shared_generation.py',
                 'src/data_sheets_schema/api_runner.py',
                 'src/download/prompts/canonical_hashes.yaml',
                 'tests/utils/run_spec_boundary_contracts.json',
                 'tests/test_ci_timing_update.py', '.github/workflows/main.yaml'):
        raw = (root / name).read_bytes()
        assert raw == blob(name), name
        unchanged[name] = digest(raw)
    denial_files = sorted(root.glob('tests/test_native_shared_denials*.py'))
    denials = {}
    for path in denial_files:
        relative = path.relative_to(root).as_posix()
        before, after = ast.parse(blob(relative)), ast.parse(path.read_bytes())
        def assertions(tree):
            return [ast.dump(node.test, include_attributes=False)
                    for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        assert assertions(before) == assertions(after), relative
        for tree in (before, after):
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert):
                    node.msg = None
            tree.body = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
        assert ast.dump(before, include_attributes=False) == ast.dump(after, include_attributes=False), relative
        assert '_native_helper_import_environment' in path.read_text()
        denials[relative] = {'assertions_unchanged': True, 'nonimport_nonmessage_ast_unchanged': True,
                             'sha256': digest(path.read_bytes())}
    measured_raw = (root / 'utils/ci_test_durations.json').read_bytes()
    assert measured_raw == blob('utils/ci_test_durations.json', 'a6d773e6a^')
    measured = json.loads(measured_raw)
    estimates_raw = (root / 'utils/ci_scheduling_estimates.json').read_bytes()
    estimates = json.loads(estimates_raw)
    assert estimates['base_sha256'] == digest(measured_raw)
    effective = {**measured['file_seconds'], **estimates['file_seconds']}
    before = json.loads(blob('utils/ci_test_durations.json'))['file_seconds']
    result = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'base': BASE, 'source_tree_unchanged': True, 'unchanged': unchanged, 'denials': denials,
        'measured_sha256': digest(measured_raw), 'estimates_sha256': digest(estimates_raw),
        'effective_matches_7b9497fc1': effective == before,
        'effective_changes_from_7b9497fc1': {name: {'before': before.get(name), 'after': seconds}
            for name, seconds in effective.items() if before.get(name) != seconds},
        'helper_sha256': digest(Path(__file__).read_bytes())}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'head': result['head'], 'unchanged_files': len(unchanged),
        'denial_modules_verified': len(denials), 'effective_matches_7b9497fc1': effective == before,
        'output': str(args.output), 'sha256': digest(args.output.read_bytes())}))


if __name__ == '__main__':
    main()
