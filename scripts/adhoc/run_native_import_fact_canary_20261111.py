#!/usr/bin/env python3
"""Run the one authorized import-fact canary using the existing owned deadline.

Inputs: this worktree at the reviewed source/test hashes and existing interpreter.
Outputs: fresh tmp/import-facts-canary-20261111 command, log, JUnit and deadline
evidence. Serves native import-fact draft / issues #5844 and #5845, 2026-11-11.
No provider calls, dependency installation or additional test selection.
"""
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
NODE = 'tests/test_native_import_facts.py::test_real_graph_reuses_facts_while_reapplying_lint_and_resolution'
PINS = {
    'src/data_sheets_schema/native_execution_authority_v2.py':
        'abbb97ec4058564c16702135a68df259bab0de52442595c5e0632bb3a31f5b7d',
    'tests/test_native_import_facts.py':
        '60c208d20e87cc2c3064bb18eb0ca2c587f02e64aa659d80b611271c8ac63675',
}


def main():
    if not sys.dont_write_bytecode:
        raise ValueError('run this helper with -B')
    observed = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in PINS}
    if observed != PINS:
        raise ValueError('canary source or test differs from its reviewed snapshot')
    sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
    from tests.utils.subprocess_deadline import run, save
    output = ROOT / 'tmp/import-facts-canary-20261111'
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
         'node': NODE, 'scope': 'single component canary; no performance or whole-launch claim'})
    print(json.dumps({'returncode': result.returncode, 'expired': result.expired, 'evidence': str(output)}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
