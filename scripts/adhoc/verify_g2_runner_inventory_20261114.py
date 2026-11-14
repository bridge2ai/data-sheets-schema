#!/usr/bin/env python3
"""Verify G2-REVIEW-RUNNER-F1 with isolated Git-index fixtures, 2026-11-14.
Inputs: G2 runner helper only. Outputs: scratch fixture repos and JSON proof.
Imports no project package and runs no pytest, commits, provider or native call.
Each fixture stages synthetic files without committing; the runner's separate
HEAD diff remains the tracked-change guard for its actual source worktree.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
RUNNER = ROOT / 'scripts/adhoc/run_g2_checks_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def fixture(directory, additions=(), extra_tracked=()):
    directory.mkdir()
    files = {'.gitignore': 'src/ignored.py\ntests/ignored_test.py\nsrc/.hidden/\n',
             'src/payload.py': 'VALUE = 1\n',
             'tests/test_saved.py': 'def test_saved():\n    assert True\n'}
    files.update(additions)
    for name, raw in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw)
    env = dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null',
               GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0')
    subprocess.check_call(['git', 'init', '-q'], cwd=directory, env=env)
    subprocess.check_call(['git', 'add', '--', '.gitignore', 'src/payload.py',
                           'tests/test_saved.py', *extra_tracked], cwd=directory, env=env)
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', default='runner-inventory-verification')
    args = parser.parse_args()
    if Path(args.cohort).name != args.cohort or args.cohort in ('', '.', '..'):
        parser.error('cohort must be one scratch directory name')
    output = SCRATCH / args.cohort
    output.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('g2_runner_inventory_under_review', RUNNER)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    rows = []

    def check(name, selectors, additions=(), *, rejected=None, ignored=None, extra_tracked=()):
        directory = fixture(output / name, additions, extra_tracked)
        if ignored is not None:
            subprocess.check_call(['git', 'check-ignore', '-q', '--', ignored], cwd=directory)
        try:
            actual = runner.python_inventory(directory, selectors)
        except ValueError as exc:
            if rejected is None or rejected not in str(exc):
                raise AssertionError(name + ': unexpected rejection') from exc
            rows.append({'case': name, 'passed': True, 'refused': str(exc),
                         'ignored_path_confirmed': ignored})
        else:
            if rejected is not None:
                raise AssertionError(name + ': unsafe input was accepted')
            assert actual['ignored_and_hidden_files_included'] is True
            assert '--no-ignore' in actual['inventory_command']
            assert '--hidden' in actual['inventory_command']
            rows.append({'case': name, 'passed': True, 'inventory': actual})

    check('tracked_file', ['tests/test_saved.py::test_saved'])
    check('tracked_directory', ['tests'])
    check('untracked_selected_test', ['tests/test_untracked.py'],
          [('tests/test_untracked.py', 'def test_untracked(): pass\n')],
          rejected='tests/test_untracked.py')
    check('ignored_selected_test', ['tests/ignored_test.py'],
          [('tests/ignored_test.py', 'def test_ignored(): pass\n')],
          rejected='tests/ignored_test.py', ignored='tests/ignored_test.py')
    check('untracked_import', ['tests/test_saved.py'],
          [('src/untracked.py', 'VALUE = 2\n')], rejected='src/untracked.py')
    check('ignored_import', ['tests/test_saved.py'],
          [('src/ignored.py', 'VALUE = 2\n')], rejected='src/ignored.py', ignored='src/ignored.py')
    check('hidden_ignored_stub', ['tests/test_saved.py'],
          [('src/.hidden/extra.pyi', 'VALUE: int\n')],
          rejected='src/.hidden/extra.pyi', ignored='src/.hidden/extra.pyi')
    check('outside_test_directory', ['src'], rejected='directory selectors are allowed only within tests')
    check('untracked_selected_outside_inventory', ['notes/test_untracked.py'],
          [('notes/test_untracked.py', 'def test_untracked(): pass\n')],
          rejected='selected test file must be tracked')
    check('tracked_explicit_file_outside_tests', ['notes/test_saved.py'],
          [('notes/test_saved.py', 'def test_saved(): pass\n')], extra_tracked=('notes/test_saved.py',))
    check('unrelated_helpers_allowed', ['tests/test_saved.py'],
          [('scripts/adhoc/untracked.py', 'VALUE = 2\n'), ('notes/proposal.py', 'PROPOSAL = True\n')])
    result = {'finding_id': 'G2-REVIEW-RUNNER-F1', 'status': 'verified',
              'runner': pin(RUNNER), 'review': pin(SCRATCH / 'review-runner.json'),
              'cases': rows, 'passed': len(rows), 'failed': 0,
              'scope': 'Source inventory and selector preconditions only; no project pytest, source mutation, subprocess cleanup or complete G2 acceptance claim.'}
    path = output / 'result.json'
    with path.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'evidence': pin(path), 'passed': len(rows), 'failed': 0}))


if __name__ == '__main__':
    main()
