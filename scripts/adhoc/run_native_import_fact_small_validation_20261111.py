#!/usr/bin/env python3
"""Run the authorized focused import-fact module using the existing owned deadline.

Inputs: this worktree at the reviewed source/test hashes and existing interpreter.
Outputs: fresh tmp/import-facts-small-validation-20261111 command, log, JUnit and deadline
evidence. Serves native import-fact draft / issue #5849, 2026-11-11.
No provider calls, dependency installation or additional test selection.
"""
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
NODE = 'tests/test_native_import_facts.py'
REGRESSIONS = ['tests/test_native_execution_verified_loader_v2.py::' + name for name in (
    'test_consumer_graph_refuses_direct_and_relative_legacy_aliases',
    'test_consumer_graph_refuses_transitive_legacy_import_and_changed_dependency',
    'test_consumer_graph_refuses_dynamic_loading',
    'test_consumer_graph_accepts_explicit_pinned_helpers',
    'test_consumer_graph_allows_ordinary_fixed_field_introspection',
    'test_consumer_context_recompiles_cached_transitive_graph_and_restores_bindings',
    'test_implicit_parent_initializer_cannot_import_legacy_authority',
    'test_implicit_parent_is_source_compiled_and_all_bindings_restore',
    'test_implicit_parent_without_initializer_pin_refuses_before_import',
    'test_implicit_parent_with_pinned_empty_initializer_is_verified',
)]
PINS = {
    'src/data_sheets_schema/native_execution_authority_v2.py':
        'b2189db86428b5977bfcbaa72adc5f504f3449c31b583359555b074916a95558',
    'tests/test_native_import_facts.py':
        'cb565125f92baa095cf0f8489381d7fe82888fd7e8280768f7085e49b772ac9e',
}


def main():
    if not sys.dont_write_bytecode:
        raise ValueError('run this helper with -B')
    observed = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in PINS}
    if observed != PINS:
        raise ValueError('canary source or test differs from its reviewed snapshot')
    sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
    from tests.utils.subprocess_deadline import run, save
    output = ROOT / 'tmp/import-facts-small-validation-20261111'
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, '-B', '-m', 'pytest', '-o', 'addopts=', '-p', 'no:xdist',
               '-q', NODE, *REGRESSIONS, '--junitxml=' + str(output / 'pytest.xml')]
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
         'node': NODE, 'scope': 'focused module and same existing regressions; no performance or whole-launch claim'})
    print(json.dumps({'returncode': result.returncode, 'expired': result.expired, 'evidence': str(output)}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
