#!/usr/bin/env python3
"""Issue #5834 import-only loader lifetime probe, 2026-11-11.

Inputs: this checkout's genuine dependency identity and the existing interpreter.
Output: new tmp/lead-loader-5834 report, trace, and bounded supervisor record.
No source, registry, guard, fixture, provider, or execution-state modifications.
"""
from __future__ import annotations
import hashlib
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'tmp/lead-loader-5834'
EXPECTED_HEAD = 'e282f05960a2b397844acb3ac5f140b1fe192cd8'
SNAPSHOT = 'data_sheets_schema.schema_snapshot'
GUARD = 'data_sheets_schema.native_catalog_reuse'
SELECTION = 'data_sheets_schema.native_shared_selection'
sys.dont_write_bytecode = True


def write_new(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def checkout_state():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    paths = subprocess.check_output(['git', 'ls-files', '-z', 'src/data_sheets_schema/*.py', 'tests/*.py'], cwd=ROOT).split(b'\0')
    state = hashlib.sha256()
    for raw in sorted(path for path in paths if path):
        path = ROOT / os.fsdecode(raw)
        state.update(raw + b'\0')
        state.update(hashlib.sha256(path.read_bytes()).digest())
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--', 'src', 'tests'],
                                    cwd=ROOT, text=True)
    return {'head': head, 'source_tests_sha256': state.hexdigest(), 'source_tests_status': dirty}


def child():
    sys.path.insert(0, str(ROOT / 'src'))
    os.chdir(ROOT)
    result = {'issue': 5834, 'kind': 'import_only_loader_lifetime', 'stages': []}
    authority = None

    def inspect(stage):
        guard = sys.modules.get(GUARD)
        selected = authority._VERIFIED_PACKAGE_MODULES.get(SELECTION) or sys.modules.get(SELECTION)
        actual = getattr(guard, 'snapshots', None)
        canonical = sys.modules.get(SNAPSHOT)
        registered = authority._VERIFIED_PACKAGE_MODULES.get(SNAPSHOT)
        def identity(module):
            if module is None:
                return None
            row = {'object_id': id(module), 'name': getattr(module, '__name__', None),
                   'file': getattr(module, '__file__', None),
                   'loader_type': type(getattr(module, '__loader__', None)).__name__}
            try:
                row['same_authority_source_identity'] = authority.module_source_identity(module)
            except Exception as exc:
                row['attestation_error'] = type(exc).__name__ + ': ' + str(exc)
            context = getattr(module, '_SCHEMA_LAUNCH_CONTEXT', None)
            row['launch_context'] = None if context is None else {
                'enabled': context[1], 'domain_sha256': hashlib.sha256(context[0]).hexdigest()}
            return row
        memo = getattr(authority._LAUNCH_DERIVATIONS, 'memo', None)
        row = {'stage': stage, 'guard': identity(guard), 'guard_snapshot': identity(actual),
               'canonical_snapshot': identity(canonical), 'registry_snapshot': identity(registered),
               'selection': identity(selected), 'registry_missing': SNAPSHOT not in authority._VERIFIED_PACKAGE_MODULES,
               'guard_is_canonical': actual is not None and actual is canonical,
               'guard_is_registry': actual is not None and actual is registered,
               'selection_capture_is_guard_snapshot_capture': selected is not None and actual is not None
                   and getattr(selected, '_capture_native_schema', None) is getattr(actual, '_capture_native_schema', None),
               'donor': identity(None if memo is None else memo.donor)}
        result['stages'].append(row)

    try:
        from data_sheets_schema import native_execution_authority_v2 as authority
        from data_sheets_schema import native_shared_controls_orchestration as controls
        expected = authority.dependency_identity()
        result['dependency_identity_sha256'] = hashlib.sha256(
            json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        result['snapshot_pin'] = expected['base']['package_sources']['src/data_sheets_schema/schema_snapshot.py']
        with authority.launch_derivations():
            with controls.loaded_controls(expected):
                inspect('controls_entered')
                with authority.loaded_dependencies(expected):
                    inspect('nested_dependencies_1_entered')
                    with authority.loaded_dependencies(expected):
                        inspect('nested_dependencies_2_entered')
                    inspect('nested_dependencies_2_exited')
                inspect('nested_dependencies_1_exited')
                try:
                    importlib.import_module('data_sheets_schema.api_runner')
                    inspect('late_api_runner_imported')
                    importlib.import_module('data_sheets_schema.native_shared_render')
                    inspect('late_native_shared_render_imported')
                except Exception:
                    inspect('late_import_failed_before_scope_exit')
                    raise
        result['outcome'] = 'completed_without_reproducing'
    except Exception as exc:
        result['outcome'] = 'exception'
        result['error'] = type(exc).__name__ + ': ' + str(exc)
        result['traceback'] = traceback.format_exc()
    finally:
        write_new('probe.json', result)
    return 0 if result['outcome'] == 'completed_without_reproducing' else 1


def main():
    if sys.argv[1:] == ['--child']:
        return child()
    before = checkout_state()
    if before['head'] != EXPECTED_HEAD or before['source_tests_status']:
        raise SystemExit('Refusing changed HEAD or dirty source/tests before the one authorized probe')
    OUT.mkdir(parents=True, exist_ok=False)
    write_new('before.json', before)
    started = time.monotonic()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    with (OUT / 'stdout.log').open('x') as stdout, (OUT / 'stderr.log').open('x') as stderr:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--child'],
            cwd=ROOT, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        timed_out = False
        try:
            code = process.wait(timeout=26)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait(timeout=1)
    after = checkout_state()
    write_new('supervisor.json', {'returncode': code, 'timed_out': timed_out,
        'elapsed_seconds': time.monotonic() - started, 'before': before, 'after': after,
        'source_unchanged': before == after, 'interpreter': sys.executable,
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    print(json.dumps({'output': str(OUT), 'returncode': code, 'timed_out': timed_out,
                      'source_unchanged': before == after}))
    return code if before == after else 3


if __name__ == '__main__':
    raise SystemExit(main())
