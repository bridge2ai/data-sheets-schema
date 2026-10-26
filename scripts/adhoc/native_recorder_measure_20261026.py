#!/usr/bin/env python3
# Purpose: unchanged one-node recorder baseline measurements, 2026-10-26; N2/#4354.
# Inputs: a pristine exact 01969cbed or d41282871 worktree and existing Python.
# Outputs: exclusive external trial directory, host samples, source/origin pins, log and JUnit.
# No provider, observer injection, deadline change, installation or target-worktree edit.
"""Measure one unchanged offline neutral test. The coordinator schedules three idle trials."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HEADS = {
    'current': '01969cbed8eed93f420c640c1f1c306e5f58b033',
    'original': 'd41282871394dd8abe74e11afb0e80c95d149305',
}
NODE = 'tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion'
SCOPE = ('src', 'scripts', 'tests', 'utils', '.claude', 'notes')
INITIAL_MODULES = ('native_shared_selection', 'native_shared_receipts',
                   'native_shared_capture', 'native_shared_execution')
OFFLINE = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_ADDOPTS': '',
           'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
           'UV_OFFLINE': '1', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
           'GIT_NO_LAZY_FETCH': '1'}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def git(tree, *arguments):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1',
               GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.check_output(['git', '--no-replace-objects', '--no-optional-locks',
        '-C', str(tree), *arguments], stderr=subprocess.PIPE, env=env)


def source_identity(tree):
    """Pin all tracked source/test/policy assets plus ignored/hidden Python."""
    tree = Path(tree).resolve(strict=True)
    root_python = sorted(path.name for path in tree.glob('*.py'))
    committed, gitlinks = {}, {}
    for row in git(tree, 'ls-tree', '-r', '-z', 'HEAD').split(b'\0'):
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        mode, kind, digest = metadata.decode().split()
        name = name.decode()
        if Path(name).parts[0] in SCOPE or len(Path(name).parts) == 1:
            if mode == '160000' and kind == 'commit':
                # A gitlink identifies a submodule commit, never regular file
                # bytes. Only an absent/empty uninitialized checkout is safe
                # to exclude: populated contents need their own byte proof.
                path = tree / name
                current = tree
                for component in Path(name).parts:
                    current /= component
                    if current.is_symlink():
                        raise ValueError('symlink gitlink path: ' + name)
                try:
                    state = path.lstat()
                except FileNotFoundError:
                    worktree_state = 'absent'
                else:
                    if not stat.S_ISDIR(state.st_mode):
                        raise ValueError('non-directory gitlink path: ' + name)
                    if next(path.iterdir(), None) is not None:
                        raise ValueError('populated gitlink requires a separate byte inventory: ' + name)
                    worktree_state = 'empty_directory'
                gitlinks[name] = {'mode': mode, 'kind': kind, 'git_commit': digest,
                    'worktree_state': worktree_state, 'contents_in_byte_inventory': False}
            else:
                committed[name] = {'mode': mode, 'kind': kind, 'git_blob': digest}
    files = {tree / name for name in committed}
    files.update(tree / name for name in root_python)
    for relative in SCOPE:
        parent = tree / relative
        if parent.is_symlink():
            raise ValueError('symlink source root: ' + relative)
        for directory, children, names in os.walk(parent, followlinks=False):
            children.sort()
            for name in children:
                if (Path(directory) / name).is_symlink():
                    raise ValueError('symlink source directory: ' + str(Path(directory) / name))
            children[:] = [name for name in children
                          if (Path(directory) / name).relative_to(tree).as_posix() not in gitlinks]
            files.update(Path(directory) / name for name in names if name.endswith('.py'))
    if len(files) > 50_000:
        raise ValueError('source inventory exceeds 50,000 files')
    object_format = git(tree, 'rev-parse', '--show-object-format').decode().strip()
    if object_format not in ('sha1', 'sha256'):
        raise ValueError('unsupported Git object format')
    inventory, total = {}, 0
    for path in sorted(files):
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > 64_000_000:
            raise ValueError('nonregular or oversized source/input: ' + str(path))
        total += before.st_size
        if total > 1_000_000_000:
            raise ValueError('source inventory exceeds one GB')
        raw = path.read_bytes()
        after = path.lstat()
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if any(getattr(before, key) != getattr(after, key) for key in fields):
            raise ValueError('source changed during hashing: ' + str(path))
        relative = path.relative_to(tree).as_posix()
        blob = hashlib.new(object_format, b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        expected = committed.get(relative)
        inventory[relative] = {'sha256': sha(raw), 'bytes': len(raw), 'git_blob': blob,
            'committed_exact': bool(expected and expected['kind'] == 'blob'
                                    and expected['mode'] in ('100644', '100755')
                                    and expected['git_blob'] == blob)}
    missing = sorted(set(committed) - set(inventory))
    status = git(tree, 'status', '--porcelain=v1', '--untracked-files=no').decode()
    return {'head': git(tree, 'rev-parse', 'HEAD').decode().strip(),
            'tree': git(tree, 'rev-parse', 'HEAD^{tree}').decode().strip(),
            'tracked_status': status, 'missing_python': missing, 'files': inventory, 'gitlinks': gitlinks,
            'pristine': not status and not missing and all(row['committed_exact'] for row in inventory.values()),
            'inventory_scope': 'all tracked root files and src/scripts/tests/utils/.claude/notes assets; also ignored/hidden Python in those roots; gitlinks separately pin path/commit only and require absent/empty uninitialized directories; submodule contents and other data/docs are outside this byte inventory'}


def require_source(identity, target):
    if identity['head'] != HEADS[target] or identity['pristine'] is not True:
        raise ValueError('target must be pristine at its exact declared commit')


def origins(tree, inventory, modules=None):
    """Verify loaded project/test files and complete namespace search roots."""
    result = {}
    for name, module in sorted((modules if modules is not None else sys.modules).copy().items()):
        if not (name == 'data_sheets_schema' or name.startswith('data_sheets_schema.')
                or name == 'tests' or name.startswith('tests.')):
            continue
        filename = getattr(module, '__file__', None)
        if filename is None:
            locations = list(getattr(module, '__path__', ()))
            base = tree / 'src' if name.startswith('data_sheets_schema') else tree
            expected = base.joinpath(*name.split('.'))
            if locations != [str(expected)] or expected.resolve(strict=True) != expected:
                raise ValueError('foreign or malformed namespace origin: ' + name)
            result[name] = {'kind': 'namespace', 'paths': locations}
            continue
        path = Path(filename).resolve(strict=True)
        if not path.is_relative_to(tree) or path.suffix != '.py':
            raise ValueError('foreign project/test import: ' + name)
        relative = path.relative_to(tree).as_posix()
        pin = inventory['files'].get(relative)
        if not pin or not pin['committed_exact'] or sha(path.read_bytes()) != pin['sha256']:
            raise ValueError('imported source differs from frozen committed bytes: ' + name)
        result[name] = {'path': str(path), 'sha256': pin['sha256']}
    return result


def isolated_paths(tree, entries):
    """Put selected roots first, once each, excluding foreign package roots."""
    selected = [(tree / relative).resolve() for relative in ('src', 'scripts', '.')]
    removed, paths, seen = [], [], set()
    for entry in [*selected, *entries]:
        candidate = Path(entry or os.getcwd()).resolve()
        if candidate != selected[0] and (candidate / 'data_sheets_schema').exists():
            if str(candidate) not in removed:
                removed.append(str(candidate))
            continue
        if candidate not in seen:
            seen.add(candidate)
            paths.append(str(candidate))
    return paths, removed


def worker(args):
    tree, output = args.tree.resolve(strict=True), args.output.resolve(strict=True)
    before = json.loads((output / 'source-before.json').read_bytes())
    require_source(before, args.target)
    if any(name == 'data_sheets_schema' or name.startswith('data_sheets_schema.') for name in sys.modules):
        raise ValueError('project package imported before source isolation')
    paths, removed = isolated_paths(tree, sys.path)
    sys.path[:] = paths
    for suffix in INITIAL_MODULES:
        importlib.import_module('data_sheets_schema.' + suffix)
    write_new(output / 'origins-before.json', {'modules': origins(tree, before),
        'removed_foreign_package_roots': removed, 'sys_path': sys.path,
        'python': sys.executable, 'prefix': sys.prefix, 'version': sys.version,
        'scope': 'pytest process only; nested helpers retain the unchanged registered child environment and authority checks'})
    write_new(output / 'environment-worker.json', {
        'python': sys.executable, 'prefix': sys.prefix, 'version': sys.version,
        'installed_distributions': sorted(
            ({'name': distribution.metadata.get('Name', '<unnamed>'),
              'version': distribution.version} for distribution in importlib.metadata.distributions()),
            key=lambda row: (row['name'].casefold(), row['version'])),
        'distribution_scope': 'installed distribution metadata only; package bytes and lockfile reconciliation are not verified',
        'pytest_plugin_autoload': not bool(os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD')),
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD'),
        'PYTEST_PLUGINS': os.environ.get('PYTEST_PLUGINS'),
    })
    import pytest
    arguments = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(output / 'cases'),
                 '--junitxml', str(output / 'pytest.xml'), NODE]
    write_new(output / 'pytest-command.json', {'arguments': arguments, 'cwd': str(tree),
        'node': NODE, 'helper_timeout_seconds': 180, 'registered_test_deadline_seconds': 900,
        'deadline_basis': 'unchanged committed test and fake CLI; no driver timeout supplied'})
    started = time.monotonic()
    code = None
    try:
        code = int(pytest.main(arguments))
        return code
    finally:
        write_new(output / 'origins-after.json', {'modules': origins(tree, before)})
        write_new(output / 'worker-result.json', {'returncode': code,
            'pytest_wall_seconds': time.monotonic() - started, 'finished_at': now()})


def environment(tree, output, *, plugin_autoload='enabled'):
    env = dict(os.environ)
    removed = sorted(name for name in env if name.startswith(('ANTHROPIC_', 'CBORG_', 'OPENAI_'))
        or name.endswith(('_API_KEY', '_AUTH_TOKEN', '_ACCESS_TOKEN'))
        or name.startswith('D4D_RECORDER_OBSERVER')
        or name in {'CLAUDE_CODE_OAUTH_TOKEN', 'D4D_INSTALL_TESTS', 'PYTHONHOME', 'PYTEST_PLUGINS'})
    for name in removed:
        env.pop(name)
    env.update(OFFLINE)
    if plugin_autoload == 'enabled':
        env.pop('PYTEST_DISABLE_PLUGIN_AUTOLOAD', None)
    elif plugin_autoload == 'disabled':
        env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    else:
        raise ValueError('plugin autoload must be explicitly enabled or disabled')
    env.update(PYTHONPATH=os.pathsep.join(str(tree / path) for path in ('src', 'scripts', '.')),
               PYTHONPYCACHEPREFIX=str(output / 'pycache'))
    return env, removed


def host_sample(psutil):
    # Names only, never command arguments or environment/credentials.
    process = subprocess.run(['ps', '-A', '-o', 'pid=,ppid=,pcpu=,comm='],
        capture_output=True, text=True, check=True, timeout=10)
    return {'at': now(), 'monotonic': time.monotonic(), 'load': list(os.getloadavg()),
            'logical_cpus': os.cpu_count(), 'cpu_percent': psutil.cpu_percent(interval=None),
            'processes': parse_ps(process.stdout)}


def parse_ps(text):
    rows = []
    for line in text.splitlines():
        fields = line.split(None, 3)
        if len(fields) != 4:
            raise ValueError('host process sample is malformed')
        pid, ppid, cpu, name = fields
        rows.append({'pid': int(pid), 'ppid': int(ppid), 'cpu_percent': float(cpu), 'name': name})
    return rows


def competing_processes(sample, roots, threshold):
    """Exclude only the driver/test descendants visible in this sample."""
    owned = set(roots)
    while True:
        expanded = owned | {row['pid'] for row in sample['processes'] if row['ppid'] in owned}
        if expanded == owned:
            break
        owned = expanded
    return [row for row in sample['processes'] if row['pid'] not in owned and row['cpu_percent'] >= threshold]


def idle_decision(samples, *, max_mean_cpu, max_peak_cpu, max_load_per_cpu,
                  max_foreign_process_cpu, owned_roots):
    if not samples:
        return {'idle': False, 'reason': 'no host samples'}
    cpus = [row['logical_cpus'] for row in samples]
    if any(type(value) is not int or value <= 0 for value in cpus):
        return {'idle': False, 'reason': 'CPU count unavailable'}
    mean = sum(row['cpu_percent'] for row in samples) / len(samples)
    peak = max(row['cpu_percent'] for row in samples)
    load = max(row['load'][0] / row['logical_cpus'] for row in samples)
    competitors = [dict(at=row['at'], processes=competing_processes(row, owned_roots, max_foreign_process_cpu))
                   for row in samples]
    competitors = [row for row in competitors if row['processes']]
    return {'idle': mean <= max_mean_cpu and peak <= max_peak_cpu and load <= max_load_per_cpu and not competitors,
            'samples': len(samples), 'mean_cpu_percent': mean, 'peak_cpu_percent': peak,
            'competing_process_observations': competitors,
            'max_one_minute_load_per_cpu': load,
            'thresholds': {'mean_cpu_percent': max_mean_cpu, 'peak_cpu_percent': max_peak_cpu,
                           'one_minute_load_per_cpu': max_load_per_cpu,
                           'foreign_process_cpu_percent': max_foreign_process_cpu},
            'scope': 'declared host-idleness gate; not proof of absence of every competing process'}


def junit(path):
    root = ET.parse(path).getroot()
    cases = root.findall('.//testcase')
    if root.tag == 'testcase':
        cases = [root]
    if len(cases) != 1 or cases[0].get('name') != NODE.split('::')[1]:
        raise ValueError('JUnit must contain exactly the unchanged neutral test')
    case = cases[0]
    if case.get('classname') != 'tests.test_native_shared_execution':
        raise ValueError('JUnit test module differs from the requested node')
    return {'tests': 1, 'failures': len(case.findall('failure')), 'errors': len(case.findall('error')),
            'skipped': len(case.findall('skipped')), 'attributes': dict(case.attrib)}


def reserve_output(parent, trial, tree):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', trial):
        raise ValueError('trial must be a bounded safe path component')
    parent = parent.resolve(strict=True)
    tree = tree.resolve(strict=True)
    helper_root = Path(__file__).resolve().parents[2]
    if parent == tree or parent.is_relative_to(tree) or parent == helper_root or parent.is_relative_to(helper_root):
        raise ValueError('measurement artifacts must be outside source/helper worktrees')
    output = parent / trial
    output.mkdir(mode=0o700, exist_ok=False)
    return output


def run(args):
    tree = args.tree.resolve(strict=True)
    python = (args.python or Path(sys.executable)).absolute()  # preserve venv spelling
    if not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError('Python must be an existing executable')
    output = reserve_output(args.output, args.trial, tree)
    before = source_identity(tree)
    write_new(output / 'source-before.json', before)
    try:
        require_source(before, args.target)
    except ValueError as exc:
        write_new(output / 'preflight-refusal.json', {'status': 'source_refused', 'error': str(exc)})
        raise
    env, removed = environment(tree, output, plugin_autoload=args.plugin_autoload)
    command = [str(python), '-P', '-B', str(Path(__file__).resolve()), '--worker',
               '--tree', str(tree), '--target', args.target, '--output', str(output)]
    write_new(output / 'plan.json', {'format': 'd4d_recorder_baseline_v1', 'started_at': now(),
        'trial': args.trial, 'target': args.target, 'command': command, 'cwd': str(tree), 'node': NODE,
        'helper': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__).read_bytes())},
        'removed_environment_names': removed,
        'environment_overrides': {key: env[key] for key in (*OFFLINE, 'PYTHONPATH', 'PYTHONPYCACHEPREFIX')},
        'idle_window_seconds': args.idle_seconds, 'mode': args.mode,
        'idle_only': args.idle_only, 'outer_driver_watchdog_seconds': args.driver_seconds,
        'pytest_plugin_autoload': args.plugin_autoload,
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': env.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD'),
        'watchdog_scope': 'separate measurement censoring; never changes helper 180 s or registered test 900 s',
        'scientific_acceptance': 'not_assessed',
        'network_scope': 'offline fake-client test; named credential variables removed, no installation; other ambient config is not authenticated and this is not a network sandbox'})
    import psutil
    psutil.cpu_percent(interval=None)  # prime the first measured interval
    result = {'status': 'not_started', 'returncode': None, 'scientific_acceptance': 'not_assessed'}
    child = None
    started = time.monotonic()
    try:
        with (output / 'host.jsonl').open('x', encoding='utf-8') as host:
            def sample(stage):
                row = {**host_sample(psutil), 'stage': stage}
                host.write(json.dumps(row, sort_keys=True) + '\n')
                host.flush()
                return row
            preflight = []
            for _ in range(args.idle_seconds):
                time.sleep(1)
                preflight.append(sample('before'))
            decision = idle_decision(preflight, max_mean_cpu=args.max_mean_cpu,
                max_peak_cpu=args.max_peak_cpu, max_load_per_cpu=args.max_load_per_cpu,
                max_foreign_process_cpu=args.max_foreign_process_cpu, owned_roots={os.getpid()})
            write_new(output / 'idle-decision.json', decision)
            if args.idle_only:
                result['status'] = 'host_idle' if decision['idle'] else 'blocked_host_busy'
                return 0 if decision['idle'] else 3
            if args.mode == 'idle' and not decision['idle']:
                result['status'] = 'blocked_host_busy'
                return 3
            if source_identity(tree) != before:
                raise ValueError('source changed during the idle window')
            with (output / 'pytest.log').open('xb') as stream:
                child = subprocess.Popen(command, cwd=tree, env=env, stdout=stream,
                                         stderr=subprocess.STDOUT, start_new_session=True)
                result.update(status='running', child_pid=child.pid, test_started_at=now())
                contamination = []
                child_started = time.monotonic()
                while child.poll() is None:
                    observed = sample('test')
                    competing = competing_processes(observed, {os.getpid(), child.pid}, args.max_foreign_process_cpu)
                    if competing:
                        contamination.append({'at': observed['at'], 'processes': competing})
                    if time.monotonic() - child_started >= args.driver_seconds:
                        raise TimeoutError('outer measurement watchdog reached; test outcome is censored')
                    time.sleep(1)
                result['returncode'] = child.wait()
            result['during_test_competing_process_observations'] = contamination
            result['idle_trial_qualified'] = args.mode == 'idle' and decision['idle'] and not contamination
            for name in ('origins-before.json', 'origins-after.json', 'environment-worker.json', 'worker-result.json'):
                if not (output / name).is_file():
                    raise ValueError('missing worker evidence: ' + name)
            worker_result = json.loads((output / 'worker-result.json').read_bytes())
            if worker_result.get('returncode') != result['returncode']:
                raise ValueError('worker exit and pytest result disagree')
            result['worker'] = worker_result
            result['junit'] = junit(output / 'pytest.xml')
            result['status'] = ('software_test_passed' if result['returncode'] == 0
                and all(result['junit'][key] == 0 for key in ('failures', 'errors', 'skipped'))
                else 'software_test_failed')
            if args.mode == 'idle' and not result['idle_trial_qualified']:
                return 4  # preserve the test verdict, but do not count this as an idle replication
            return 0 if result['status'] == 'software_test_passed' else 1
    except KeyboardInterrupt:
        result['status'] = 'interrupted'
        raise
    except BaseException as exc:
        result.update(status='measurement_error', error=type(exc).__name__ + ': ' + str(exc))
        raise
    finally:
        # Only this driver's still-running process group; never unrelated jobs.
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
            result['cleanup_returncode'] = child.returncode
        try:
            after = source_identity(tree)
            write_new(output / 'source-after.json', after)
            result['source_unchanged'] = after == before
            if not result['source_unchanged']:
                result['status'] = 'source_changed'
        except BaseException as exc:
            result.update(source_unchanged=False, source_inspection_error=type(exc).__name__ + ': ' + str(exc))
        result.update(finished_at=now(), driver_wall_seconds=time.monotonic() - started)
        write_new(output / 'outcome.json', result)
        print(json.dumps({'output': str(output), **result}, sort_keys=True), flush=True)
        if result.get('source_unchanged') is not True:
            raise RuntimeError('source preservation failed; no measurement is eligible')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--target', choices=HEADS, required=True)
    parser.add_argument('--output', type=Path, required=True, help='existing external parent; worker uses its reserved trial directory')
    parser.add_argument('--trial', help='required unique trial name; existing evidence is never reused')
    parser.add_argument('--python', type=Path)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--idle-only', action='store_true', help='retain host/source evidence without launching pytest')
    parser.add_argument('--driver-seconds', type=int, help='required outer measurement watchdog; not a test/runtime limit')
    parser.add_argument('--mode', choices=('idle', 'load-diagnostic'), default='idle')
    parser.add_argument('--plugin-autoload', choices=('enabled', 'disabled'), default='enabled',
                        help='explicit identical choice for both heads; default matches archived autoload behavior')
    parser.add_argument('--idle-seconds', type=int, default=30)
    parser.add_argument('--max-mean-cpu', type=float, default=15)
    parser.add_argument('--max-peak-cpu', type=float, default=35)
    parser.add_argument('--max-load-per-cpu', type=float, default=0.5)
    parser.add_argument('--max-foreign-process-cpu', type=float, default=5)
    args = parser.parse_args(argv)
    if args.worker:
        return worker(args)
    if not args.trial or (not args.idle_only and not args.python):
        parser.error('--trial is required; test runs also require --python')
    if not args.idle_only and (args.driver_seconds is None or not 900 <= args.driver_seconds <= 7200):
        parser.error('--driver-seconds must explicitly name 900–7200 seconds')
    if not 5 <= args.idle_seconds <= 60:
        parser.error('--idle-seconds must be between 5 and 60')
    if not (0 <= args.max_mean_cpu <= args.max_peak_cpu <= 100 and 0 <= args.max_load_per_cpu <= 10
            and 0 < args.max_foreign_process_cpu <= 100):
        parser.error('invalid declared idle thresholds')
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
