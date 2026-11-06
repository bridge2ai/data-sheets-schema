#!/usr/bin/env python3
"""Prepare committed instrumentation-only U0 diagnostic source, 2026-11-06.

Inputs: local failed commit and reviewed profiler tooling, ruling 2/#4354.
Outputs: a new isolated worktree/diagnostic branch and exclusive pin manifest.
No test, native executable, provider, network operation or guard bypass.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

BASE = '01969cbed8eed93f420c640c1f1c306e5f58b033'
BRANCH = 'codex/native-u0-cpu-fixture-20261106'
EXEC = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
BOOT_PATH = 'src/data_sheets_schema/cli/__init__.py'
HELPERS = ('scripts/adhoc/native_recorder_observer_20261026.py',
           'scripts/adhoc/native_recorder_cpu_profile_20261106.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *arguments):
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C',
           'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}
    return subprocess.check_output(['git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
        '-c', 'protocol.allow=never', '-c', 'gc.auto=0',
        '-c', 'user.name=Codex', '-c', 'user.email=codex@localhost', *arguments], cwd=root,
        env=env, timeout=120)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    destination = args.destination.absolute()
    manifest = args.manifest.absolute()
    if (destination.parent.resolve(strict=True) != EXEC or destination.exists()
            or destination.is_symlink() or manifest.exists()
            or not manifest.parent.resolve(strict=True).is_relative_to(EXEC)):
        raise ValueError('only a new direct execution worktree and new evidence manifest are allowed')
    if git(root, 'status', '--porcelain').strip():
        raise ValueError('tooling must be committed before preparing its diagnostic copy')
    helper_sha = git(root, 'rev-parse', 'HEAD').decode().strip()
    for path in HELPERS:
        if (root / path).read_bytes() != git(root, 'show', helper_sha + ':' + path):
            raise ValueError('profiler helper differs from its committed tooling blob: ' + path)
    spec = importlib.util.spec_from_file_location('cpu_profiler_configuration', root / HELPERS[1])
    cpu = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cpu
    spec.loader.exec_module(cpu)
    config_path = 'scripts/adhoc/' + cpu.CONFIG_NAME
    bound_helpers = {path: sha((root / path).read_bytes()) for path in HELPERS}
    bound_helpers[config_path] = sha(cpu.CONFIG_BYTES)
    verification = (
        '# U0 diagnostic-only dependency binding; no production authority exception.\n'
        'import sys as _u0_profile_sys\n'
        'if _u0_profile_sys.argv[1:3] == ["provenance", "record"]:\n'
        '    from pathlib import Path as _u0_profile_Path\n'
        '    import hashlib as _u0_profile_hashlib\n'
        '    _u0_profile_root = _u0_profile_Path(__file__).resolve().parents[3]\n'
        '    for _u0_profile_rel, _u0_profile_sha in ' + repr(bound_helpers) + '.items():\n'
        '        if _u0_profile_hashlib.sha256((_u0_profile_root / _u0_profile_rel).read_bytes()).hexdigest() != _u0_profile_sha:\n'
        '            raise RuntimeError("U0 diagnostic tooling hash differs")\n')
    bootstrap = verification + cpu.BOOTSTRAP
    original = git(root, 'show', BASE + ':' + BOOT_PATH)
    parsed = ast.parse(original)
    if not isinstance(parsed.body[0], ast.Expr) or not isinstance(parsed.body[0].value, ast.Constant):
        raise ValueError('expected leading CLI package docstring')
    lines = original.splitlines(keepends=True)
    split = parsed.body[0].end_lineno
    patched = b''.join(lines[:split]) + b'\n' + bootstrap.encode() + b'\n' + b''.join(lines[split:])
    ast.parse(patched)
    git(root, 'worktree', 'add', '--no-checkout', '-b', BRANCH, str(destination), BASE)
    git(destination, 'sparse-checkout', 'init', '--cone')
    git(destination, 'sparse-checkout', 'set', 'src', 'scripts', 'tests', 'utils', '.claude', 'notes')
    git(destination, 'read-tree', '-mu', 'HEAD')  # Fresh empty worktree only.
    pins = {}
    for path in HELPERS:
        raw = (root / path).read_bytes()
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ValueError('diagnostic helper already exists at base: ' + path)
        target.write_bytes(raw)
        pins[path] = {'sha256': sha(raw), 'bytes': len(raw)}
    (destination / config_path).write_bytes(cpu.CONFIG_BYTES)
    (destination / BOOT_PATH).write_bytes(patched)
    pins[config_path] = {'sha256': sha(cpu.CONFIG_BYTES), 'bytes': len(cpu.CONFIG_BYTES)}
    pins[BOOT_PATH] = {'before_sha256': sha(original), 'sha256': sha(patched), 'bytes': len(patched)}
    git(destination, 'add', '--', *pins)
    changed = git(destination, 'diff', '--cached', '--name-only').decode().splitlines()
    if sorted(changed) != sorted(pins):
        raise ValueError('unexpected diagnostic source changes')
    git(destination, 'diff', '--cached', '--check')
    git(destination, 'commit', '-m', 'Instrument recorder CPU cost for U0 diagnostic only')
    head = git(destination, 'rev-parse', 'HEAD').decode().strip()
    parents = git(destination, 'show', '-s', '--format=%P', 'HEAD').decode().strip().split()
    if parents != [BASE]:
        raise ValueError('diagnostic commit must have exactly the frozen failed parent')
    if sorted(git(destination, 'diff', '--name-only', BASE, head).decode().splitlines()) != sorted(pins):
        raise ValueError('committed diagnostic diff differs from its declared instrumentation files')
    if git(destination, 'status', '--porcelain').strip():
        raise ValueError('diagnostic tree is not clean after commit')
    # Every original byte remains in its original order around the one bootstrap.
    if patched.replace(b'\n' + bootstrap.encode() + b'\n', b'', 1) != original:
        raise ValueError('bootstrap did not preserve original CLI bytes')
    evidence = {'base': BASE, 'parents': parents, 'head': head, 'branch': BRANCH, 'worktree': str(destination),
        'tooling_head': helper_sha, 'files': pins, 'unchanged_original_cli_bytes': True,
        'changed_paths': changed, 'limits': {'helper_seconds': 180, 'attempt_seconds': 900},
        'scope': 'instrumentation-only committed descendant; no production fix or guard edits',
        'bootstrap_placement': 'cli/__init__.py after docstring, before click/subcommand imports',
        'placement_reason': 'python -m imports cli package before __main__; capture recorder import CPU',
        'protocol': '2026-11-06-codex-native-u0.md Lead ruling 2'}
    with manifest.open('x') as stream:
        json.dump(evidence, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'head': head, 'manifest': str(manifest), 'changed_paths': changed}, sort_keys=True))


if __name__ == '__main__':
    main()
