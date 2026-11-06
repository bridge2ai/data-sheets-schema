#!/usr/bin/env python3
"""Validate real source bindings before U0's CPU pair, 2026-11-06.

Inputs: prepared diagnostic tree, existing Python and frozen thread observer.
Outputs: a fresh external preflight directory with child log, JSON and origins.
No recorder/native executable/provider; child environment is empty then allowlisted
and runs under OS network denial with ordinary site startup as the recorder does.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('u0_preflight_wrapper',
        root / 'scripts/adhoc/native_u0_run_20261106.py')
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    if wrapper.LOCK_PATH.exists():
        raise SystemExit('quiet measurement lock exists; preflight must pause')
    tree, out = args.tree.resolve(strict=True), args.out.absolute()
    if (not tree.is_relative_to(wrapper.EXEC_ROOT) or not out.parent.resolve(strict=True).is_relative_to(wrapper.EXEC_ROOT)
            or out.is_relative_to(tree) or out.is_relative_to(root) or out.exists() or out.is_symlink()):
        raise ValueError('requires prepared execution tree and new external evidence output')
    out.mkdir(mode=0o700)
    home, temporary = out / 'home', out / 'tmp'
    home.mkdir(); temporary.mkdir()
    env = wrapper.clean_environment(home, temporary)
    env['PYTHONPATH'] = os.pathsep.join(str(tree / path) for path in ('src', 'scripts', '.'))
    env['PYTHONPYCACHEPREFIX'] = str(out / 'pycache')
    observer = tree / 'scripts/adhoc/native_recorder_thread_cpu_20261106.py'
    command = [str(wrapper.SANDBOX), '-D', 'FROZEN_TREE=' + str(tree),
        '-D', 'HOST_SAMPLES=' + str(out / 'unused-host-samples.jsonl'), '-f', str(wrapper.PROFILE),
        str(args.python.absolute()), '-P', '-B', str(observer),
        '--tree', str(tree), '--out', str(out / 'probe')]
    wrapper.write_new(out / 'command.json', {'command': command, 'environment': env,
        'purpose': 'real frozen source binding only; no recorder/provider execution'})
    with (out / 'child.log').open('xb') as log:
        completed = subprocess.run(command, cwd=tree, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, timeout=180, check=False)
    outcome = {'returncode': completed.returncode,
               'artifacts': [str(path.relative_to(out)) for path in sorted(out.rglob('*')) if path.is_file()]}
    wrapper.write_new(out / 'outcome.json', outcome)
    print(json.dumps(outcome))
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
