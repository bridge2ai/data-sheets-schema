#!/usr/bin/env python3
"""Run the authorized focused import-fact module using the existing owned deadline.

Inputs: this worktree at the reviewed source/test hashes and existing interpreter.
Outputs: fresh tmp/import-facts-module-20261111 command, log, JUnit and deadline
evidence. Serves native import-fact draft / issues #5846 and #5848, 2026-11-11.
No provider calls, dependency installation or additional test selection.
"""
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
NODE = 'tests/test_native_import_facts.py'
PINS = {
    'src/data_sheets_schema/native_execution_authority_v2.py':
        '98f18a06619fa50aee89f61b924fbabf27928ec7b82e9f9941b6dab50bebb557',
    'tests/test_native_import_facts.py':
        '60ddb6a0949642d6b465bdaea462fcaf2af4c013ad8c2e60d300c4b1042f2c9b',
}


def main():
    if not sys.dont_write_bytecode:
        raise ValueError('run this helper with -B')
    observed = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in PINS}
    if observed != PINS:
        raise ValueError('canary source or test differs from its reviewed snapshot')
    sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
    from tests.utils.subprocess_deadline import run, save
    output = ROOT / 'tmp/import-facts-module-20261111'
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, '-B', '-m', 'pytest', '-o', 'addopts=', '-p', 'no:xdist',
               '-q', NODE, '--junitxml=' + str(output / 'pytest.xml')]
    excluded = {'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN',
                'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS'}
    env = {name: value for name, value in os.environ.items()
           if name not in excluded and not name.endswith('_API_KEY')}
    overrides = {'PYTHONDONTWRITEBYTECODE': '1',
                 'PYTHONPATH': str(ROOT / 'src') + os.pathsep + str(ROOT)}
    env.update(overrides)
    save(output / 'command.json', {'command': command, 'cwd': str(ROOT),
         'source_sha256': observed, 'environment_overrides': overrides, 'deadline_seconds': 30,
         'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    with (output / 'pytest.log').open('w') as stream:
        result = run(command, cwd=ROOT, env=env, evidence=output / 'deadline', stream=stream, seconds=30)
    save(output / 'outcome.json', {'returncode': result.returncode, 'expired': result.expired,
         'node': NODE, 'scope': 'focused component module; no performance or whole-launch claim'})
    print(json.dumps({'returncode': result.returncode, 'expired': result.expired, 'evidence': str(output)}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
