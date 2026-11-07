#!/usr/bin/env python3
"""Reproduce U3-A P2-3 against the actual pinned helper, 2026-11-07.

Inputs: exact local commit, existing isolated dependency-venv Python, fresh output.
Outputs: fresh Git archive and evidence venv, retained forged pyc, witness JSON.
Default only prints a plan. --run creates the archive and runs one worker under
OS network denial. No native executable, authentication or provider is invoked.
The worker uses -S -P -B and explicit archive/dependency paths; no .pth or site
customization runs. The fresh venv is retained as interpreter/bootstrap evidence.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
EXECUTIONS = ROOT.parent
LOCK = EXECUTIONS / 'plans/native_quiet_window.lock'
HELPER = 'notes/claudecode_direct/run_direct_canary_awake.py'
PROFILE = '(version 1)\n(allow default)\n(deny network*)\n'
LIMIT = 180


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def environment(out, python):
    return {'PATH': str(python.parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
        'HOME': str(out/'home'), 'TMPDIR': str(out/'tmp'), 'LANG': 'en_US.UTF-8',
        'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
        'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_NO_LAZY_FETCH': '1',
        'UV_OFFLINE': '1', 'PIP_NO_INDEX': '1'}


def saved_module(path, name):
    module = ModuleType(name); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def dependency_site(python):
    prefix = python.parent.parent
    if python.resolve(strict=True) != Path(sys.executable).resolve(strict=True):
        raise RuntimeError('dependency interpreter differs from the probe parent interpreter')
    bootstrap_path = prefix.parent/'bootstrap.json'
    if bootstrap_path.is_file():
        bootstrap = json.loads(bootstrap_path.read_bytes())
        if Path(bootstrap['test_python']).absolute() != python:
            raise RuntimeError('dependency evidence venv differs from its bootstrap record')
        for name, digest in bootstrap['files'].items():
            if sha(Path(name).read_bytes()) != digest:
                raise RuntimeError('dependency evidence bootstrap bytes changed')
        dependencies = Path(bootstrap['dependency_site'])
    else:
        dependencies = prefix/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages'
    if not dependencies.is_dir() or dependencies.resolve(strict=True) != dependencies:
        raise RuntimeError('dependency site is not an explicit physical directory')
    return dependencies


def origins(root):
    import data_sheets_schema
    wanted = root/'src/data_sheets_schema'
    paths = [str(Path(path).resolve()) for path in data_sheets_schema.__path__]
    if not paths or set(paths) != {str(wanted)}:
        raise RuntimeError('mixed project namespace: ' + repr(paths))
    modules = {}
    for name, module in tuple(sys.modules.items()):
        if name != 'data_sheets_schema' and not name.startswith('data_sheets_schema.'):
            continue
        source = getattr(module, '__file__', None)
        if source is not None:
            resolved = Path(source).resolve()
            if not resolved.is_relative_to(wanted):
                raise RuntimeError('foreign production module: ' + name)
            modules[name] = str(resolved)
        if any(not Path(path).resolve().is_relative_to(wanted)
               for path in getattr(module, '__path__', ())):
            raise RuntimeError('foreign production package: ' + name)
    return {'namespace': paths, 'module_origins': modules, 'sys_path': list(sys.path)}


def worker(args):
    root, out = args.source_root.resolve(strict=True), args.out.resolve(strict=True)
    if root != out/'source' or not (root/'.git').is_dir():
        raise RuntimeError('probe must use its own fresh archived source repository')
    prefix = args.expected_prefix.resolve(strict=True)
    if (Path(sys.executable).absolute() != prefix/'bin/python'
            or not (prefix/'pyvenv.cfg').is_file()):
        raise RuntimeError('probe executable is outside the explicitly selected evidence venv')
    if not (sys.flags.no_site and sys.flags.safe_path and sys.flags.no_user_site and sys.dont_write_bytecode):
        raise RuntimeError('worker requires -S -P -B and disabled user site')
    if any(name in sys.modules for name in ('site', 'sitecustomize', 'usercustomize')):
        raise RuntimeError('site initialization ran before the probe bootstrap')
    if sys.pycache_prefix is not None:
        raise RuntimeError('probe cache must be retained inside its own scratch source')
    if LOCK.exists():
        raise RuntimeError('quiet-window lock exists; no probe started')
    if any(name == 'data_sheets_schema' or name.startswith('data_sheets_schema.')
           for name in sys.modules):
        raise RuntimeError('production package was imported before explicit source isolation')
    if any('__editable__' in repr(finder) for finder in sys.meta_path):
        raise RuntimeError('editable-install finder is active')
    # -S skips all .pth/customization. Keep only interpreter standard-library
    # roots, then add the one physical dependency directory without processing
    # its .pth files. No old MA or primary source path can enter this bootstrap.
    retained, removed = [], []
    for entry in sys.path:
        if not entry:
            removed.append(entry)
            continue
        path = Path(entry)
        if (not path.resolve().is_relative_to(Path(sys.base_prefix).resolve())
                or (path/'data_sheets_schema').is_dir() or (path/'src/data_sheets_schema').is_dir()):
            removed.append(entry)
        else:
            retained.append(entry)
    dependencies = args.dependency_site.resolve(strict=True)
    if dependencies != args.dependency_site or not dependencies.is_dir():
        raise RuntimeError('worker requires one physical dependency site')
    sys.path[:] = [str(root/'src'), str(root), *retained, str(dependencies)]
    os.chdir(root)
    sock = socket.socket()
    try:
        try:
            sock.bind(('127.0.0.1', 0))
        except OSError as error:
            if error.errno != errno.EPERM:
                raise
            save(out/'network.json', {'network_bind_denied': True, 'errno': error.errno})
        else:
            raise RuntimeError('network denial self-check unexpectedly succeeded')
    finally:
        sock.close()

    spawns = []
    def audit(event, values):
        if event == 'subprocess.Popen':
            executable, argv = values[:2]
            if executable not in ('git', '/usr/bin/git') or not argv or argv[0] not in ('git', '/usr/bin/git'):
                raise RuntimeError('only local Git children are permitted by this probe')
            if any(word in {'fetch', 'push', 'clone', 'pull', 'ls-remote'} for word in argv):
                raise RuntimeError('outbound Git operation refused')
            spawns.append(list(argv))
    sys.addaudithook(audit)
    from data_sheets_schema import native_execution_authority_v2 as authority
    if authority.ROOT != root or Path(authority.__file__).resolve() != root/'src/data_sheets_schema/native_execution_authority_v2.py':
        raise RuntimeError('authority was imported from a different checkout')
    save(out/'origins-before.json', origins(root))
    helper = root/HELPER
    if helper.is_symlink() or helper.resolve(strict=True) != helper:
        raise RuntimeError('helper is not the exact archived regular source')
    original = helper.read_bytes()
    source_pin = authority.ADDITIONAL['run_direct_canary_awake']
    if source_pin['path'] != HELPER or source_pin['sha256'] != sha(original):
        raise RuntimeError('actual helper source does not match its reviewed pin')
    import importlib._bootstrap_external as bytecode
    info = helper.stat()
    forged = compile(original + b'\nFORGED_BY_REVIEW_PROBE = True\n', str(helper), 'exec', dont_inherit=True)
    cache = Path(importlib.util.cache_from_source(str(helper)))
    if cache.parent != helper.parent/'__pycache__' or not cache.is_relative_to(root):
        raise RuntimeError('cache destination escaped the fresh archive')
    cache.parent.mkdir(exist_ok=True)
    cache_raw = bytecode._code_to_timestamp_pyc(forged, int(info.st_mtime), info.st_size)
    with cache.open('xb') as stream:
        stream.write(cache_raw)
    identity = authority.dependency_identity()
    if identity['base']['source_commit'] != args.source_commit:
        raise RuntimeError('actual authority commit differs from requested candidate')
    names = set(identity['base']['modules']) | set(identity['additional_modules'])
    absent = object()
    before = {name: sys.modules.get(name, absent) for name in names}
    old_path, old_meta, old_policy = list(sys.path), list(sys.meta_path), sys.dont_write_bytecode
    with authority.loaded_dependencies(identity) as controls:
        loaded = controls['run_direct_canary_awake']
        forged_executed = getattr(loaded, 'FORGED_BY_REVIEW_PROBE', False)
        module_identity = authority.module_source_identity(loaded)
        loaded_cache = loaded.__cached__
        exposed = sorted(controls)
    restored = all(sys.modules.get(name, absent) is prior for name, prior in before.items())
    source_unchanged = helper.read_bytes() == original
    cache_untouched = cache.read_bytes() == cache_raw
    restored_state = sys.path == old_path and sys.meta_path == old_meta and sys.dont_write_bytecode is old_policy
    witness = origins(root)
    result = {'valid': bool(source_unchanged and cache_untouched and restored and restored_state
                           and forged_executed is False and loaded_cache is None
                           and module_identity['sha256'] == source_pin['sha256']),
        'source_root': str(root), 'source_commit': identity['base']['source_commit'],
        'authority_source_sha256': sha(Path(authority.__file__).read_bytes()),
        'source': {'path': str(helper), 'bytes': len(original), 'sha256': sha(original),
                   'pin_match': True, 'unchanged': source_unchanged},
        'retained_forged_cache': {'path': str(cache), 'bytes': len(cache_raw), 'sha256': sha(cache_raw),
                                 'unchanged': cache_untouched, 'timestamp_source_size': info.st_size,
                                 'timestamp_source_mtime': int(info.st_mtime)},
        'executed_forged_bytecode': forged_executed, 'loaded_cache': loaded_cache,
        'module_source_identity': module_identity, 'exposed_controls': exposed,
        'aliases_restored_exactly': restored, 'import_policy_restored': restored_state,
        'rebound_source_paths': removed, 'git_children': spawns,
        'python': sys.executable, 'prefix': sys.prefix,
        'script_sha256': sha(Path(__file__).read_bytes()),
        'scope': 'One actual pinned helper import; no runtime/native/provider call. Bootstrap and external libraries remain outside the pinned-helper claim.'}
    save(out/'origins-after.json', witness)
    save(out/'probe-result.json', result)
    return 0 if result['valid'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--source-root', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--expected-prefix', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--dependency-site', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', args.source_commit) is None:
        parser.error('--source-commit requires the exact full local object id')
    if args.worker:
        return worker(args)
    if args.python is None:
        parser.error('--python is the known dependency/evidence-venv interpreter')
    out, python = args.out.absolute(), args.python.absolute()
    plan = {'source_commit': args.source_commit, 'out': str(out), 'python': str(python),
            'deadline_seconds': LIMIT, 'fresh_archive': str(out/'source'),
            'network': 'OS deny network*', 'native_executable': 'never invoked',
            'forged_cache': 'preserved only inside the new archived source'}
    if not args.run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise RuntimeError('invoke the probe parent with Python -S -P -B')
    if LOCK.exists():
        raise RuntimeError('quiet-window lock exists; no probe started')
    if out != out.resolve() or not out.is_relative_to(EXECUTIONS) or out.exists():
        raise RuntimeError('output must be a new canonical evidence path under d4d-executions')
    if any((parent/'.git').exists() for parent in (out.parent, *out.parents)
           if parent.is_relative_to(EXECUTIONS)):
        raise RuntimeError('output must not be inside an existing source checkout')
    prefix = python.parent.parent
    if not python.is_file() or not (prefix/'pyvenv.cfg').is_file():
        raise RuntimeError('explicit existing evidence venv is required')
    dependencies = dependency_site(python)
    out.mkdir(mode=0o700); (out/'home').mkdir(); (out/'tmp').mkdir()
    saved_helper = ROOT/'scripts/adhoc/mutate_native_u3a_round2_20261107.py'
    helper = saved_module(saved_helper, '_u3a_archive_probe_helper')
    helper.new_copy(args.source_commit, out/'source')
    saved_runner = out/'source/scripts/adhoc/run_native_u3a_tests_20261107.py'
    runner = saved_module(saved_runner, '_u3a_probe_environment_helper')
    child_python = runner.make_test_venv(out, dependencies)
    profile = out/'network-denied.sb'; profile.write_text(PROFILE)
    command = ['/usr/bin/sandbox-exec', '-f', str(profile), str(child_python), '-S', '-P', '-B', str(Path(__file__).resolve()),
        '--worker', '--source-root', str(out/'source'), '--expected-prefix', str(out/'venv'),
        '--dependency-site', str(dependencies), '--source-commit', args.source_commit, '--out', str(out)]
    save(out/'plan.json', {**plan, 'command': command, 'sandbox_sha256': sha(profile.read_bytes()),
        'archive_helper_sha256': sha(saved_helper.read_bytes()), 'runner_sha256': sha(saved_runner.read_bytes()),
        'script_sha256': sha(Path(__file__).read_bytes()), 'dependency_site': str(dependencies)})
    if LOCK.exists():
        save(out/'outcome.json', {'status': 'blocked_quiet_window', 'launched': False})
        return 75
    sys.path.append(str(dependencies))  # plain path: never process dependency .pth
    import psutil
    started = time.monotonic()
    child, owned, stopped, parent_error = None, None, None, None
    previous_handlers = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}
    def parent_signal(number, frame):
        nonlocal stopped
        stopped = 'parent_signal_' + str(number)
        raise KeyboardInterrupt('probe parent interrupted')
    def group_signal(number):
        if child is not None:
            proved_owned_group = child.poll() is None
            if not proved_owned_group and owned is not None:
                for process in owned.live():
                    try:
                        if os.getpgid(process.pid) == child.pid:
                            proved_owned_group = True
                    except ProcessLookupError:
                        pass
            if not proved_owned_group:
                return
            try:
                os.killpg(child.pid, number)
            except ProcessLookupError:
                pass
    for number in previous_handlers:
        signal.signal(number, parent_signal)
    try:
        with (out/'probe.log').open('xb') as log:
            try:
                child = subprocess.Popen(command, cwd=out/'source', env=environment(out, child_python),
                                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                owned = runner.OwnedProcesses(psutil, child.pid)
                while child.poll() is None:
                    owned.observe()
                    if LOCK.exists():
                        stopped = 'quiet_window'
                        break
                    if time.monotonic() - started >= LIMIT:
                        stopped = 'deadline'
                        break
                    time.sleep(0.1)
            except BaseException as error:
                parent_error = type(error).__name__
                stopped = stopped or 'parent_error'
            finally:
                # Repeated terminal signals cannot abort the owned cleanup.
                for number in previous_handlers:
                    signal.signal(number, signal.SIG_IGN)
                if child is not None:
                    if stopped or child.poll() is None or owned is not None and owned.live():
                        group_signal(signal.SIGTERM)
                        if owned is not None:
                            owned.signal(signal.SIGTERM)
                        until = time.monotonic() + 5
                        while time.monotonic() < until:
                            if owned is not None:
                                owned.observe()
                            if child.poll() is not None and (owned is None or not owned.live()):
                                break
                            time.sleep(0.1)
                        if child.poll() is None or owned is not None and owned.live():
                            group_signal(signal.SIGKILL)
                            if owned is not None:
                                owned.signal(signal.SIGKILL)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        stopped = stopped or 'cleanup_timeout'
    finally:
        for number, handler in previous_handlers.items():
            signal.signal(number, handler)
    group_alive = None
    if child is not None:
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            group_alive = False
        else:
            group_alive = True
    survivors = [] if owned is None else [{'pid': process.pid, 'created': process.create_time()}
                                          for process in owned.live()]
    observation_errors = ['observer_not_initialized'] if owned is None else owned.errors
    cleanup = bool(child is not None and child.poll() is not None and group_alive is False
                   and owned is not None and not survivors and not observation_errors)
    result_path = out/'probe-result.json'
    result_raw = result_path.read_bytes() if result_path.is_file() else b''
    result_valid = bool(result_raw) and json.loads(result_raw).get('valid') is True
    save(out/'outcome.json', {'returncode': None if child is None else child.returncode,
        'stopped': stopped, 'parent_error': parent_error, 'timed_out': stopped == 'deadline',
        'cleanup_verified': cleanup, 'elapsed_seconds': time.monotonic()-started,
        'process_group_alive': group_alive, 'observed_survivors': survivors,
        'observation_errors': observation_errors,
        'observed_processes': [] if owned is None else [{'pid': pid, 'created': created}
                                                       for pid, created in sorted(owned.known)],
        'result_exists': bool(result_raw), 'result_valid': result_valid,
        'result_sha256': sha(result_raw) if result_raw else None})
    return 0 if child is not None and child.returncode == 0 and stopped is None and cleanup and result_valid else 1


if __name__ == '__main__':
    raise SystemExit(main())
