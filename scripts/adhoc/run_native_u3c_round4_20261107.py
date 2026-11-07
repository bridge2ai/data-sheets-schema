#!/usr/bin/env python3
"""U3-C4 offline validation launcher, 2026-11-07.

Inputs: committed C4 checkout, physical dependency-venv Python (-S -P -B),
explicit pytest nodes. Outputs: a new directory strictly below C4 scratch.
Reuses the checked-in A4 runner without editing it; both worker entry points
return through this wrapper. No provider or real native executable is allowed.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
INHERITED = ROOT / 'scripts/adhoc/run_native_u3a_tests_20261107.py'
spec = importlib.util.spec_from_file_location('u3c4_inherited_runner', INHERITED)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
SCRATCH = runner.EXECUTIONS / 'scratch-native-u3c-r4'
NATIVE_PATHS = (
    '/Users/marcin/.local/bin/claude', '/Users/marcin/.local/bin/agy',
    '/Users/marcin/.nvm/versions/node/v22.16.0/bin/codex',
    '/Users/marcin/.nvm/versions/node/v22.16.0/bin/gemini',
    '/opt/homebrew/bin/claude', '/usr/local/bin/claude',
)
SMOKE_NODE = 'test_native_typed_capture_and_receipt_reconstruction_smoke'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sandbox_profile():
    # Deny known physical targets too; resolving a path does not execute it.
    paths = sorted({p for item in NATIVE_PATHS for p in (item, str(Path(item).resolve()))})
    return ('(version 1)\n(allow default)\n(deny network*)\n'
            '(deny process-exec (regex #"/(claude|codex|gemini|agy)(/|$)"))\n'
            '(deny process-exec\n'
            + ''.join('  (literal ' + json.dumps(p) + ')\n' for p in paths) + ')\n'
            '(deny file-write* (require-all\n'
            '  (require-not (subpath ' + json.dumps(str(SCRATCH)) + '))\n'
            '  (require-not (literal "/dev/null"))\n'
            '  (require-not (literal "/dev/tty"))))\n')


def smoke_evidence():
    """Check the existing B repair; OS write denial is the actual safeguard."""
    path = ROOT / 'tests/test_native_u3b_reuse.py'
    tree = ast.parse(path.read_bytes(), filename=str(path))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == SMOKE_NODE]
    if len(functions) != 1:
        raise RuntimeError('B smoke test identity changed; review artifact destinations')
    assignments = [n for n in ast.walk(functions[0]) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'out' for t in n.targets)]
    expected = ast.parse("out = tmp_path / 'cpu-smoke.json'").body[0].value
    if len(assignments) != 1 or ast.dump(assignments[0].value) != ast.dump(expected):
        raise RuntimeError('B smoke test no longer writes through pytest tmp_path')
    return {'test': 'tests/test_native_u3b_reuse.py::' + SMOKE_NODE,
            'file_sha256': digest(path), 'destination': 'pytest tmp_path/cpu-smoke*.json',
            'policy': 'retained; basetemp and OS file-write policy restrict it to C4 scratch'}


def git_state():
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}
    def git(*args):
        return subprocess.check_output(['git', '--no-replace-objects', *args],
                                       cwd=ROOT, env=env, text=True).strip()
    return {'head': git('rev-parse', 'HEAD'),
            'status': git('status', '--porcelain', '--untracked-files=normal'),
            'wrapper_sha256': digest(Path(__file__)), 'inherited_sha256': digest(INHERITED)}


class DeadlineClock:
    """Retain C3's conservative deadline across suspend/clock divergence."""
    def __init__(self):
        self.mono = time.monotonic()
        self.wall = time.time()

    def monotonic(self):
        return self.mono + max(time.monotonic() - self.mono, time.time() - self.wall)

    sleep = staticmethod(time.sleep)


# Setting __file__ is deliberate: A's parent and subprocess witness both use
# it to choose the child entry point. Overriding SCRATCH in the parent alone
# would send the worker back to A's incompatible hardcoded scratch root.
runner.ROOT = ROOT
runner.SCRATCH = SCRATCH
runner.__file__ = str(Path(__file__).resolve())
runner.PROFILE = sandbox_profile()
_save = runner.save
_parent = runner.parent


def save(path, value):
    if path.name == 'plan.json':
        value = {**value, 'inherited_runner': str(INHERITED),
                 'inherited_runner_sha256': digest(INHERITED),
                 'b_smoke_artifact_policy': smoke_evidence(),
                 'file_write_scope': str(SCRATCH) + ' plus /dev/null and /dev/tty',
                 'native_execution_policy': 'known literal/physical targets and native command-name regex denied'}
    _save(path, value)


def parent(args):
    if os.path.lexists(runner.LOCK):
        raise SystemExit('quiet window active; no tests started')
    before = git_state()
    if before['status']:
        raise RuntimeError('C4 candidate must be committed and clean before validation')
    smoke_evidence()
    code = _parent(args)
    after = git_state()
    stable = before == after
    out = args.out.absolute()
    if out.is_dir():
        _save(out / 'source-stability.json', {'before': before, 'after': after,
                                             'unchanged': stable})
    return code if stable else 125


runner.save = save
runner.parent = parent


if __name__ == '__main__':
    runner.time = DeadlineClock()
    raise SystemExit(runner.main())
