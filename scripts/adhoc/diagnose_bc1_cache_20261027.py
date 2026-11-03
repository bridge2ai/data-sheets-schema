"""Diagnose BC1 dependency-token changes without changing production bindings.

Inputs: this checkout, explicit Python venv, existing invented BC1 fixture.
Output: exclusive JSON report and private fixture schema; D44/D45, 2026-10-27.
Offline only. Reports names/types/token locations, not object reprs or secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import sysconfig
import types

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def description(value):
    if type(value) in (type(None), bool, int, float):
        return {'type': type(value).__name__, 'value': value}
    if type(value) in (str, bytes):
        raw = value.encode() if type(value) is str else value
        return {'type': type(value).__name__, 'length': len(value),
                'sha256': hashlib.sha256(raw).hexdigest()}
    if type(value) is types.CodeType:
        return {'type': 'code', 'name': value.co_qualname, 'line': value.co_firstlineno}
    if isinstance(value, (types.ModuleType, type)) or callable(value):
        return {'type': type(value).__name__, 'module': getattr(value, '__module__', None),
                'name': getattr(value, '__qualname__', getattr(value, '__name__', None))}
    return {'type': type(value).__name__, 'length': len(value) if isinstance(value, (tuple, list, dict, set, frozenset)) else None}


def differences(left, right, path=(), found=None):
    found = [] if found is None else found
    if len(found) >= 100 or left is right:
        return found
    if type(left) is tuple and type(right) is tuple:
        if len(left) != len(right):
            found.append({'path': list(path), 'before': description(left), 'after': description(right)})
        for index, (a, b) in enumerate(zip(left, right)):
            differences(a, b, (*path, index), found)
    elif type(left) is not type(right) or left != right:
        found.append({'path': list(path), 'before': description(left), 'after': description(right)})
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--venv', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not sys.flags.no_site or not sys.flags.safe_path or not sys.dont_write_bytecode:
        raise SystemExit('require the explicit interpreter with -S -P -B')
    venv = args.venv.resolve(strict=True)
    if not (venv / 'pyvenv.cfg').is_file():
        raise SystemExit('explicit venv is not identified')
    site = venv / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    site = site.resolve(strict=True)
    stdlib = Path(sysconfig.get_path('stdlib')).resolve()
    standard_paths = [str(Path(p).resolve()) for p in sys.path if p and
        (Path(p).resolve() == stdlib or stdlib in Path(p).resolve().parents
         or Path(p).resolve() == stdlib.parent / f'python{sys.version_info.major}{sys.version_info.minor}.zip')
        and 'site-packages' not in Path(p).parts]
    # No site import or .pth execution; preserve actual Python 3.13 venv prefixes.
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path[:] = list(dict.fromkeys([str(ROOT / 'src'), str(ROOT), *standard_paths, str(site)]))
    def deny_network(event, values):
        if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto'):
            raise RuntimeError('offline cache diagnostic forbids network')
    sys.addaudithook(deny_network)
    output = args.output.absolute()
    if output.exists() or output.is_symlink():
        raise SystemExit('output must be fresh')
    output.mkdir(parents=True)
    source_paths = [Path(__file__).resolve(), ROOT / 'src/data_sheets_schema/bc1_audit.py',
                    ROOT / 'tests/test_bc1_audit.py']
    before = {str(path): sha(path) for path in source_paths}
    from data_sheets_schema import bc1_audit as bc
    from tests.test_bc1_audit import supplied
    events = []
    def traced_token():
        def trace(frame, event, arg):
            if event == 'exception' and frame.f_code.co_filename.endswith(('/bc1_audit.py', '/cache_dependencies.py')):
                cls, exc, _tb = arg
                if len(events) < 100:
                    events.append({'function': frame.f_code.co_name, 'line': frame.f_lineno,
                                   'exception': cls.__name__, 'message': str(exc)[:240]})
            return trace
        previous = sys.gettrace()
        try:
            sys.settrace(trace)
            return bc._cache_dependency_token()
        finally:
            sys.settrace(previous)
    initial = traced_token()
    fixture_dir = output / 'fixture'
    fixture_dir.mkdir()
    inputs = supplied.__wrapped__(fixture_dir)
    after_fixture = traced_token()
    cache = bc.DerivationCache()
    packet = bc.prepare(**inputs, derivations=cache)
    after_prepare = traced_token()
    retained_before_refresh = len(cache._rows)
    refresh = cache.refresh()
    origins = {}
    for name, module in sorted(sys.modules.items()):
        if name.startswith(('data_sheets_schema.', 'tests.')) and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            if ROOT not in path.parents:
                raise SystemExit('foreign project/test module origin: ' + name)
            origins[name] = {'path': str(path), 'sha256': sha(path)}
    after = {str(path): sha(path) for path in source_paths}
    result = {'format': 'bc1_cache_diagnostic_v1', 'root': str(ROOT),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'python': sys.version, 'source_before': before, 'source_after': after,
        'source_unchanged': before == after, 'origins': origins,
        'token_components': ['pure_functions', 'settings', 'loader_tables', 'parsers', 'schema_key'],
        'initial_available': initial is not None, 'after_fixture_available': after_fixture is not None,
        'after_prepare_available': after_prepare is not None, 'refresh_after_prepare': refresh,
        'retained_before_refresh': retained_before_refresh, 'retained_after_refresh': len(cache._rows),
        'fixture_delta': differences(initial, after_fixture),
        'prepare_delta': differences(after_fixture, after_prepare),
        'token_exceptions': events, 'packet_sha256': packet['sha256'],
        'limits': 'One invented offline fixture; no provider or performance-causality claim.'}
    (output / 'report.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    if before != after:
        raise SystemExit('source changed during diagnostic')
    print(json.dumps({key: result[key] for key in ('initial_available', 'after_fixture_available',
        'after_prepare_available', 'refresh_after_prepare', 'retained_before_refresh',
        'retained_after_refresh', 'fixture_delta', 'prepare_delta', 'token_exceptions')}, indent=2))


if __name__ == '__main__':
    main()
