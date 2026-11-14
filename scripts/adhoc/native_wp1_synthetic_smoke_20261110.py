#!/usr/bin/env python3
"""One <=30s WP1 synthetic smoke, 2026-11-10; no native composition or launch.

Inputs: frozen local HEAD, four committed test/helper files, installed Python
3.13 dependencies. Outputs: a fresh small evidence directory. One sandboxed
child has at most 25s including parent preflight; cleanup belongs to the 30s
parent limit. No pytest collection, source-loaded consumer, Recorder or installer.
"""
import time
STARTED = time.monotonic()

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import traceback
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = ROOT.parent.parent / 'data-sheets-schema'
PYTHON = PRIMARY / '.venv/bin/python'
DEPENDENCIES = PRIMARY / '.venv/lib/python3.13/site-packages'
SCRATCH = ROOT.parent / 'scratch-native-u1u3'
QUIET_LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
FILES = (
    'scripts/adhoc/native_wp1_synthetic_smoke_20261110.py',
    'tests/utils/native_shared_consumer_scope.py',
    'tests/utils/native_consumer_observer_checks.py',
    'tests/utils/native_profile_stability.py',
)
CHILD = None
TIMEOUT_FD = None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    if path.read_bytes() != raw:
        raise RuntimeError('smoke evidence did not persist exactly')
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def git(*arguments):
    return subprocess.check_output(
        ['/usr/bin/git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null', *arguments],
        cwd=ROOT, timeout=3, env={'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1',
            'GIT_ALLOW_PROTOCOL': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
            'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'})


def frozen_files(source):
    if git('rev-parse', 'HEAD').decode().strip() != source:
        raise ValueError('smoke source is not the frozen current HEAD')
    found = {}
    for name in FILES:
        path = ROOT / name
        if path.resolve(strict=True) != path or not path.is_file():
            raise ValueError('smoke helper is not a physical regular file: ' + name)
        raw = path.read_bytes()
        if raw != git('show', source + ':' + name):
            raise ValueError('smoke helper differs from its committed bytes: ' + name)
        found[name] = {'bytes': len(raw), 'sha256': sha(raw)}
    return found


def current_files():
    found = {}
    for name in FILES:
        path = ROOT / name
        if path.resolve(strict=True) != path or not path.is_file():
            raise ValueError('smoke source changed its physical path')
        raw = path.read_bytes()
        found[name] = {'bytes': len(raw), 'sha256': sha(raw)}
    return found


def binary_identity(path):
    physical = path.resolve(strict=True)
    before = physical.stat()
    if before.st_size > 64 * 1024 * 1024:
        raise ValueError('smoke binary identity exceeds the bounded 64 MiB read')
    digest = hashlib.sha256()
    with physical.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    after = physical.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('smoke binary changed while hashing')
    return {'physical_path': str(physical), 'bytes': before.st_size, 'sha256': digest.hexdigest()}


def runtime_binaries():
    import importlib.util
    import sysconfig
    profiler = importlib.util.find_spec('_lsprof')
    if profiler is None or not profiler.origin:
        raise ValueError('installed _lsprof extension origin is unavailable')
    shared = sysconfig.get_config_var('Py_ENABLE_SHARED')
    if type(shared) is not int or shared not in (0, 1):
        raise ValueError('installed Python shared/static build identity is unavailable')
    library = None
    basis = 'Static Python runtime core is covered by the executable identity; no separate runtime library is claimed.'
    if shared:
        library = binary_identity(Path(sysconfig.get_config_var('LIBDIR')) / sysconfig.get_config_var('LDLIBRARY'))
        basis = 'Physical sysconfig LIBDIR/LDLIBRARY file for shared Python; not a loaded-image census.'
    return {'python': binary_identity(Path(sys.executable)),
            '_lsprof': binary_identity(Path(profiler.origin)),
            'libpython': library,
            'python_build': {'Py_ENABLE_SHARED': shared,
                             'LIBDIR': sysconfig.get_config_var('LIBDIR'),
                             'LDLIBRARY': sysconfig.get_config_var('LDLIBRARY')},
            'libpython_identity_basis': basis}


def local_imports():
    found = {}
    for name, module in list(sys.modules.items()):
        origin = getattr(module, '__file__', None)
        if not origin:
            continue
        path = Path(origin).absolute()
        if path.is_relative_to(ROOT) and path.suffix == '.py':
            if path.resolve(strict=True) != path:
                raise ValueError('aliased smoke import: ' + name)
            found[name] = {'path': str(path), 'sha256': sha(path.read_bytes())}
    return found


def worker(args):
    if int(os.environ.get('U3WP1_SMOKE_PARENT_PID', '0')) != os.getppid():
        raise ValueError('synthetic smoke child requires its own live parent')
    deadline = float(os.environ['U3WP1_SMOKE_CHILD_DEADLINE'])
    parent_started = float(os.environ['U3WP1_SMOKE_PARENT_STARTED'])
    if deadline - parent_started != 25 or not parent_started <= time.monotonic() < deadline:
        raise ValueError('synthetic smoke child cannot renew its absolute 25s deadline')
    signal.signal(signal.SIGALRM, lambda number, frame: os._exit(124))
    signal.setitimer(signal.ITIMER_REAL, max(0.001, deadline - time.monotonic()))
    if os.path.lexists(QUIET_LOCK):
        raise ValueError('quiet-window lock is active; synthetic smoke has no owner adapter')
    manifest = json.loads((args.out / 'manifest.json').read_bytes())
    if manifest['source_commit'] != args.source:
        raise ValueError('smoke child source differs from parent manifest')
    if (not sys.flags.isolated or not sys.flags.no_site or not sys.dont_write_bytecode
            or sys.pycache_prefix != str(args.out / 'unused-pycache')):
        raise ValueError('smoke requires -I -S -B and its fresh bytecode-cache prefix')
    if DEPENDENCIES.resolve(strict=True) != DEPENDENCIES:
        raise ValueError('installed dependency directory is an alias')
    for name, identity in manifest['source_files'].items():
        if sha((ROOT / name).read_bytes()) != identity['sha256']:
            raise ValueError('smoke source changed before child import')
    # -S on Python 3.13 does not provide the venv prefix. Read the explicit
    # installed dependency path without executing .pth or editable import hooks.
    sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(DEPENDENCIES)]
    import pytest
    from tests.utils import native_consumer_observer_checks as checks
    from tests.utils import native_shared_consumer_scope as observer
    from tests.utils import native_profile_stability as guard
    if not Path(pytest.__file__).resolve().is_relative_to(DEPENDENCIES):
        raise ValueError('pytest was not imported from the selected installed dependencies')
    for module, relative in ((checks, FILES[2]), (observer, FILES[1]), (guard, FILES[3])):
        if Path(module.__file__).resolve() != ROOT / relative:
            raise ValueError('smoke imported another helper tree')
    imported_before = local_imports()
    slots_before = checks._slots(sys.monitoring)
    assert sys.getprofile() is None
    assert not [thread for thread in threading.enumerate() if thread is not threading.main_thread()]
    result = {'kind': 'wp1_synthetic_smoke', 'source_commit': args.source,
              'completed_blocks': [], 'passed': False, 'recorder_instantiated': False,
              'genuine_source_loader_selected': False, 'composition_created': False,
              'interpreter': {'path': sys.executable, 'version': sys.version},
              'scope': 'Synthetic contracts only; no native acceptance, timing-arm result or general observer equivalence.'}
    try:
        entry = checks._compiled_entry()
        key = ('native_observer_canary', 'consumer_entry')
        targets = {key: ('value', 'effects', 'flag', 'unassigned')}
        for arm in ('legacy', 'monitoring'):
            checks._basic_equivalence(arm, entry, key, targets)
            result['completed_blocks'].append('basic_' + arm)
            checks._prior_hook_equivalence(arm, entry, key, targets)
            result['completed_blocks'].append('prior_hook_' + arm)
        checks._generator_equivalence()
        result['completed_blocks'].append('generator')
        # The helper needs only a mode field. This is explicitly a descriptor,
        # not a metrics Recorder; the smoke makes no Recorder-coverage claim.
        result['profile_mutation_limitation'] = checks.check_profile_mutation_limitation(
            SimpleNamespace(mode='control'))
        result['completed_blocks'].append('profile_mutation_limitation')
        result['profile_stability_guard'] = checks.check_profile_stability_guards()
        result['completed_blocks'].append('profile_stability_guard')
        assert sys.getprofile() is None
        assert checks._slots(sys.monitoring) == slots_before
        assert not [thread for thread in threading.enumerate() if thread is not threading.main_thread()]
        result['passed'] = True
    except BaseException as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error),
                           'traceback': traceback.format_exc()}
    finally:
        result['profile_hook_restored'] = sys.getprofile() is None
        result['monitoring_slots_restored'] = checks._slots(sys.monitoring) == slots_before
        result['remaining_nonmain_threads'] = [
            {'name': thread.name, 'ident': thread.ident, 'daemon': thread.daemon}
            for thread in threading.enumerate() if thread is not threading.main_thread()]
        result['bytecode_cache_created'] = os.path.lexists(args.out / 'unused-pycache')
        result['imports_before'] = imported_before
        result['imports_after'] = local_imports()
        result['source_files_after'] = current_files()
        result['sources_stable'] = result['source_files_after'] == manifest['source_files']
        result['imports_stable'] = result['imports_after'] == imported_before
        result['passed'] = (result['passed'] and result['profile_hook_restored']
            and result['monitoring_slots_restored'] and result['sources_stable'] and result['imports_stable']
            and not result['remaining_nonmain_threads'] and not result['bytecode_cache_created'])
        write_new(args.out / 'child-result.json', result)
    return 0 if result['passed'] else 1


def hard_timeout(number, frame):
    # poll() only signals an unreaped, still-owned child. Never signal a PGID
    # after its direct child has been reaped; that numerical group can be reused.
    if CHILD is not None and CHILD.poll() is None:
        try:
            os.killpg(CHILD.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if TIMEOUT_FD is not None:
        os.write(TIMEOUT_FD, b'Parent 30s deadline reached; cleanup is not certified.\n')
    os._exit(124)


def terminate_parent(number, frame):
    if CHILD is not None and CHILD.poll() is None:
        try:
            os.killpg(CHILD.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            CHILD.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            if CHILD.poll() is None:
                try:
                    os.killpg(CHILD.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    CHILD.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    pass
    if TIMEOUT_FD is not None:
        os.write(TIMEOUT_FD, b'Parent termination signal; forced cleanup is not certified.\n')
    os._exit(128 + number)


def parent(args):
    global CHILD, TIMEOUT_FD
    if (not sys.flags.isolated or not sys.flags.no_site or not sys.dont_write_bytecode
            or sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 13)):
        raise ValueError('invoke the smoke with installed CPython 3.13 -I -S -B')
    if Path(sys.executable).resolve(strict=True) != PYTHON.resolve(strict=True):
        raise ValueError('smoke interpreter differs from the selected installed Python')
    if os.path.lexists(QUIET_LOCK):
        raise ValueError('quiet-window lock is active; synthetic smoke has no owner adapter')
    if (args.out.parent != SCRATCH or args.out.parent.resolve(strict=True) != SCRATCH
            or not re.fullmatch(r'wp1-synthetic-smoke-[A-Za-z0-9_-]+', args.out.name)
            or os.path.lexists(args.out)):
        raise ValueError('a fresh physical assigned smoke directory is required')
    source_files = frozen_files(args.source)
    args.out.mkdir()
    (args.out / 'tmp').mkdir()
    TIMEOUT_FD = os.open(args.out / 'hard-timeout.txt', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    executable = PYTHON.resolve(strict=True)
    profile = '\n'.join((
        '(version 1)', '(allow default)', '(deny network*)', '(deny process-fork)',
        '(deny process-exec (require-not (literal ' + json.dumps(str(executable)) + ')))',
        '(deny file-write* (require-all (require-not (subpath ' + json.dumps(str(args.out)) + '))',
        ' (require-not (literal "/dev/null"))))', ''))
    with (args.out / 'sandbox.sb').open('x') as stream:
        stream.write(profile)
    binaries = runtime_binaries()
    manifest = {'source_commit': args.source, 'source_files': source_files,
                'interpreter': {'requested_path': str(PYTHON), 'physical_path': str(executable),
                    'sha256': binaries['python']['sha256'], 'version': sys.version},
                'runtime_binaries': binaries,
                'parent_limit_seconds': 30, 'child_deadline_seconds_from_parent_start': 25,
                'sandbox_sha256': sha(profile.encode()),
                'network_policy': 'OS sandbox denies all network; no network probe selected.',
                'child_process_policy': 'OS sandbox denies fork and all executable paths except the selected Python.',
                'scope': 'One synthetic smoke; no composition, native executable, provider, installation or pytest collection.'}
    write_new(args.out / 'manifest.json', manifest)
    command = ['/usr/bin/sandbox-exec', '-f', str(args.out / 'sandbox.sb'), str(executable),
               '-I', '-S', '-B', '-X', 'pycache_prefix=' + str(args.out / 'unused-pycache'),
               str(Path(__file__).resolve()), '--child', '--source', args.source, '--out', str(args.out)]
    environment = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
        'TMPDIR': str(args.out / 'tmp'), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        'PYTEST_ADDOPTS': '', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
        'U3WP1_SMOKE_PARENT_PID': str(os.getpid()),
        'U3WP1_SMOKE_PARENT_STARTED': repr(STARTED),
        'U3WP1_SMOKE_CHILD_DEADLINE': repr(STARTED + 25)}
    outcome = {'status': 'not_started', 'command': command, 'cleanup_certified': False,
               'forced_cleanup': False, 'observed_group_absent': None,
               'parent_pid': os.getpid(), 'source_commit': args.source}
    with (args.out / 'child.log').open('xb') as log:
        try:
            if os.path.lexists(QUIET_LOCK):
                raise ValueError('quiet-window lock became active before smoke launch')
            remaining = STARTED + 25 - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('smoke preflight exhausted the child deadline')
            CHILD = subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            outcome['child_pid'] = CHILD.pid
            CHILD.wait(timeout=max(0.001, STARTED + 25 - time.monotonic()))
            outcome.update(status='child_finished', returncode=CHILD.returncode)
        except BaseException as error:
            outcome.update(status='interrupted_or_failed', error=type(error).__name__ + ': ' + str(error))
        finally:
            if CHILD is not None:
                if CHILD.poll() is None:
                    outcome['forced_cleanup'] = True
                    try:
                        os.killpg(CHILD.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        CHILD.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        if CHILD.poll() is None:
                            try:
                                os.killpg(CHILD.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                        CHILD.wait(timeout=1)
                outcome['reaped_returncode'] = CHILD.returncode
                try:
                    os.killpg(CHILD.pid, 0)
                except ProcessLookupError:
                    outcome['observed_group_absent'] = True
                    outcome['cleanup_certified'] = not outcome['forced_cleanup']
                else:
                    # Fork is denied in the child policy. A surviving/reused
                    # group is uncertified; do not signal an unowned identity.
                    outcome['observed_group_absent'] = False
            else:
                outcome['cleanup_certified'] = True
    try:
        outcome['source_files_after'] = current_files()
        outcome['sources_stable'] = outcome['source_files_after'] == source_files
        outcome['runtime_binaries_after'] = runtime_binaries()
        outcome['runtime_binaries_stable'] = outcome['runtime_binaries_after'] == binaries
    except BaseException as error:
        outcome.update(sources_stable=False, runtime_binaries_stable=False,
                       postflight_error=type(error).__name__ + ': ' + str(error))
    child_result = args.out / 'child-result.json'
    child = json.loads(child_result.read_bytes()) if child_result.is_file() else None
    outcome['child_result'] = ({'bytes': child_result.stat().st_size,
        'sha256': sha(child_result.read_bytes())} if child is not None else None)
    outcome['log'] = {'bytes': (args.out / 'child.log').stat().st_size,
                      'sha256': sha((args.out / 'child.log').read_bytes())}
    outcome['elapsed_seconds'] = time.monotonic() - STARTED
    outcome['passed'] = bool(outcome['status'] == 'child_finished' and outcome.get('returncode') == 0
        and outcome['cleanup_certified'] and outcome['sources_stable'] and outcome['runtime_binaries_stable']
        and child and child.get('passed') is True)
    write_new(args.out / 'outcome.json', outcome)
    return 0 if outcome['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}', args.source):
        raise ValueError('a frozen full source SHA is required')
    if args.child:
        return worker(args)
    signal.signal(signal.SIGALRM, hard_timeout)
    signal.signal(signal.SIGTERM, terminate_parent)
    signal.signal(signal.SIGINT, terminate_parent)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, STARTED + 30 - time.monotonic()))
    try:
        return parent(args)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if TIMEOUT_FD is not None:
            os.close(TIMEOUT_FD)


if __name__ == '__main__':
    raise SystemExit(main())
