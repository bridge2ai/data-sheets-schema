#!/usr/bin/env python3
"""Diagnose U0 late cache refusal, 2026-11-06, without a recorder run.

Inputs: immutable treatment tree and existing interpreter; output: new external
JSON evidence after ordinary staged imports and record-validator construction.
The child is network-denied, source-write-denied and credential-free. No guards
are changed, no production code is edited, and no provider/native is invoked.
"""
from __future__ import annotations
import argparse
import errno
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
import time
import traceback
import types

PIN = '2747e86c3f0521c1ef5c455d9be82428e4ca5be7'


def describe(value):
    if isinstance(value, (types.FunctionType, types.CodeType)):
        code = value if isinstance(value, types.CodeType) else value.__code__
        return {'type': type(value).__name__, 'name': getattr(value, '__qualname__', code.co_name),
                'file': code.co_filename, 'line': code.co_firstlineno}
    if isinstance(value, types.ModuleType):
        return {'module': value.__name__, 'file': getattr(value, '__file__', None)}
    if isinstance(value, type):
        return {'class': value.__module__ + '.' + value.__qualname__}
    if value is None or type(value) in (bool, str, int, float):
        return value
    return {'type': type(value).__module__ + '.' + type(value).__qualname__, 'repr': repr(value)[:250]}


def differences(left, right, prefix=(), found=None):
    found = [] if found is None else found
    if len(found) >= 60 or left == right:
        return found
    if type(left) is type(right) and type(left) in (tuple, list) and len(left) == len(right):
        for i, (a, b) in enumerate(zip(left, right)):
            differences(a, b, (*prefix, i), found)
    else:
        found.append({'path': list(prefix), 'before': describe(left), 'after': describe(right)})
    return found


def child(tree, out):
    network_denied = False
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', 0))
        except OSError as exc:
            network_denied = exc.errno == errno.EPERM
    if not network_denied:
        raise RuntimeError('sandbox network self-check did not fail with EPERM')
    import data_sheets_schema
    closure = runpy.run_path(str(tree / 'scripts/adhoc/native_u0_source_closure_20261106.py'))
    from data_sheets_schema import provenance
    from data_sheets_schema import native_shared_capture
    from data_sheets_schema import native_catalog_reuse as catalog
    from data_sheets_schema import native_schema_event_reuse as events
    initial_closure = closure['assert_source_closure'](tree)
    snapshots = []
    validators = []

    def snapshot(stage):
        row = {'stage': stage, 'catalog_ready': catalog.runtime_token() is not None,
               'catalog_bindings_ready': catalog._FUNCTIONS.ready,
               'events_ready': events._token(8_000_000) is not None,
               'events_initial_error': events._BOUND_ERROR}
        for name, actual, baseline in (
            ('catalog_state', catalog._state, catalog._STATE),
            ('events_state', events._bindings, events._BOUND)):
            try:
                value = actual()
                row[name] = {'matches_initial': value == baseline,
                             'differences': differences(baseline, value)}
                if name == 'catalog_state':
                    row[name]['matches_initialized'] = value == catalog._INITIALIZED_STATE
                    row[name]['initialized_differences'] = differences(catalog._INITIALIZED_STATE, value)
            except Exception as exc:
                row[name] = {'error': type(exc).__name__ + ': ' + str(exc),
                             'traceback': traceback.format_exc()}
        snapshots.append(row)
        (out / 'snapshots.json').write_text(json.dumps(snapshots, indent=2) + '\n')
        return row

    snapshot('initial-native-imports')
    for name in ('linkml.validator', 'data_sheets_schema.record_schema', 'data_sheets_schema.backfill_checks'):
        importlib.import_module(name)
        snapshot('import:' + name)
    validators.append(provenance._record_validator(provenance.record_schema_path()))
    snapshot('record-validator-constructed')
    result = validators[0].validate({}, 'GenerationRecord')
    snapshot('record-validator-validated-empty-record')
    final_closure = closure['assert_source_closure'](tree)
    outcome = {'network_bind_denied': network_denied, 'source_head': PIN,
        'source_closure_start': initial_closure, 'source_closure_end': final_closure,
        'validator_result_count': len(result.results), 'snapshots': snapshots,
        'scope': 'ordinary imports and synthetic empty-record validation only; no recorder'}
    (out / 'evidence.json').write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps({'stages': [{'stage': row['stage'], 'catalog_ready': row['catalog_ready'],
            'events_ready': row['events_ready']} for row in snapshots],
            'source_closure_project_modules': final_closure['project_module_count']}))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args()
    tree = args.tree.resolve(strict=True)
    out = args.out.absolute()
    if args.child:
        return child(tree, out)
    tool = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('eligibility_wrapper',
        tool / 'scripts/adhoc/native_u0_run_20261106.py')
    wrapper = importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)
    if wrapper.LOCK_PATH.exists():
        raise RuntimeError('quiet measurement lock exists; probe must pause')
    if (not tree.is_relative_to(wrapper.EXEC_ROOT) or out.is_relative_to(tree)
            or out.is_relative_to(tool) or not out.parent.resolve(strict=True).is_relative_to(wrapper.EXEC_ROOT)):
        raise ValueError('source must be prepared execution tree and output external')
    head = subprocess.check_output(['/usr/bin/git', '-C', str(tree), 'rev-parse', 'HEAD'], text=True).strip()
    if head != PIN:
        raise ValueError('treatment source pin differs')
    out.mkdir(mode=0o700, exist_ok=False)
    home, temporary = out / 'home', out / 'tmp'
    home.mkdir(); temporary.mkdir()
    env = wrapper.clean_environment(home, temporary)
    env['PYTHONPATH'] = os.pathsep.join(str(tree / p) for p in ('src', 'scripts', '.'))
    env['PYTHONPYCACHEPREFIX'] = str(out / 'pycache')
    command = [str(wrapper.SANDBOX), '-D', 'FROZEN_TREE=' + str(tree), '-D',
        'HOST_SAMPLES=' + str(out / 'unused-samples.jsonl'), '-f', str(wrapper.PROFILE),
        str(args.python.absolute()), '-P', '-B', str(Path(__file__).resolve()),
        '--child', '--tree', str(tree), '--out', str(out)]
    (out / 'command.json').write_text(json.dumps({'command': command, 'environment_names': sorted(env),
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'profile_sha256': hashlib.sha256(wrapper.PROFILE.read_bytes()).hexdigest()}, indent=2) + '\n')
    started = time.monotonic()
    with (out / 'child.log').open('xb') as log:
        complete = subprocess.run(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT,
                                  timeout=120, check=False)
    outcome = {'returncode': complete.returncode, 'wall_seconds': time.monotonic()-started,
               'evidence_exists': (out / 'evidence.json').is_file()}
    (out / 'outcome.json').write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps(outcome))
    return complete.returncode


if __name__ == '__main__':
    raise SystemExit(main())
