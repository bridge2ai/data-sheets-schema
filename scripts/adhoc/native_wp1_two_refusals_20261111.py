#!/usr/bin/env python3
"""Run two fixed integration refusals sequentially; E1, 2026-11-11.

Input: clean combined native7ee4 and existing dependencies. Output: new external
logs/JUnit/network/origin/deadline evidence. Reuses D76's owned-group supervisor.
First JUnit is verified before the second unit;180s includes a20s cleanup reserve.
No composition, provider/native binary, installation or general cohort interface.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

TOOLS = Path(__file__).resolve().parents[2]
ROOT = TOOLS.parent / 'codex-native-u1u3'
HEAD = '7ee4cd8ba4fa591b03fbea69824d4364709766b1'
OUT = TOOLS.parent / 'scratch-native-u1u3/u3m/refusals-7ee4cd8ba4fa-20261111'
NODES = (
    'tests/test_native_launch_schema_metadata.py::test_warm_pure_rebuild_keeps_effective_producer_refusal[posixpath_os]',
    'tests/test_native_u4b_addendum_authority.py::test_expired_capture_stays_spent_and_refuses_before_generation_reservation',
)
NATIVE_PATHS = (
    '/Users/marcin/.local/bin/claude', '/Users/marcin/.local/bin/agy',
    '/Users/marcin/.nvm/versions/node/v22.16.0/bin/codex',
    '/Users/marcin/.nvm/versions/node/v22.16.0/bin/gemini',
    '/opt/homebrew/bin/claude', '/usr/local/bin/claude',
)
GIT_ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
           'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': '', 'GIT_OPTIONAL_LOCKS': '0',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def git(root, *args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '--no-optional-locks', '-c', 'diff.autoRefreshIndex=false', *args],
        cwd=root, env=GIT_ENV, timeout=5).decode().strip()


def source():
    need(git(ROOT, 'rev-parse', 'HEAD') == HEAD
         and not git(ROOT, 'status', '--porcelain'), 'combined native source changed')


def worker(index):
    node = NODES[index]
    unit = OUT / str(index)
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', 0))
        except PermissionError as exc:
            save(unit / 'network.json', {'network_bind_denied': True, 'errno': exc.errno})
        else:
            raise RuntimeError('network-denied sandbox required')
    import pytest
    code = int(pytest.main(['-q', '-o', 'addopts=', '-p', 'no:cacheprovider',
        '--basetemp', str(unit / 'cases'), '--junitxml', str(unit / 'pytest.xml'), node]))
    origins = {}
    for name in ('data_sheets_schema.api_runner', 'data_sheets_schema.native_execution_authority_v2'):
        module = sys.modules.get(name)
        need(module is not None and Path(module.__file__).resolve().is_relative_to(ROOT / 'src'),
             'source origin differs: ' + name)
        origins[name] = str(Path(module.__file__).resolve())
    save(unit / 'worker.json', {'returncode': code, 'origins': origins, 'sys_path': sys.path})
    return code


def parent():
    started = time.monotonic()
    deadline = started + 180
    source()
    need(not os.path.lexists(TOOLS.parent / 'plans/native_quiet_window.lock'), 'quiet window active')
    tool_head = git(TOOLS, 'rev-parse', 'HEAD')
    need(not git(TOOLS, 'status', '--porcelain'), 'clean committed tools required')
    need(not os.path.lexists(OUT) and OUT.parent.resolve(strict=True) == OUT.parent,
         'fresh physical external output required')
    dependencies = Path(sys.executable).absolute().parent.parent / 'lib' / 'python3.13' / 'site-packages'
    need(dependencies.is_dir() and dependencies.resolve() == dependencies, 'physical dependencies required')
    sys.pycache_prefix = str(OUT / 'unused-parent-pycache')
    guard_path = ROOT / 'scripts/adhoc/d76_process_deadline_20261102.py'
    spec = importlib.util.spec_from_file_location('wp1_refusal_deadline', guard_path)
    guard = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = guard
    spec.loader.exec_module(guard)
    OUT.mkdir()
    (OUT / 'home').mkdir()
    (OUT / 'tmp').mkdir()
    profile = OUT / 'offline.sb'
    native_paths = sorted({path for item in NATIVE_PATHS for path in (item, str(Path(item).resolve()))})
    profile.write_text('(version 1)\n(allow default)\n(deny network*)\n'
        '(deny process-exec (regex #"/(claude|codex|gemini|agy)(/|$)"))\n'
        '(deny process-exec ' + ' '.join('(literal ' + json.dumps(path) + ')' for path in native_paths) + ')\n'
        '(deny file-write* (require-all (require-not (subpath "' + str(OUT) + '"))\n'
        ' (require-not (literal "/dev/null")) (require-not (literal "/dev/tty"))))\n')
    env = {**GIT_ENV, 'HOME': str(OUT / 'home'), 'TMPDIR': str(OUT / 'tmp'),
        'PYTHONPATH': os.pathsep.join(map(str, (ROOT / 'src', ROOT, dependencies))),
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTEST_ADDOPTS': '',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1',
        'PYTHONPYCACHEPREFIX': str(OUT / 'unused-pycache'), 'UV_OFFLINE': '1', 'PIP_NO_INDEX': '1'}
    save(OUT / 'plan.json', {'source': HEAD, 'tools': tool_head, 'nodes': NODES,
        'seconds': 180, 'cleanup_reserve_seconds': 20, 'environment': env,
        'interpreter': str(Path(sys.executable).resolve()),
        'interpreter_sha256': sha(Path(sys.executable).resolve()),
        'helper_sha256': sha(Path(__file__)), 'supervisor_sha256': sha(guard_path)})
    rows, error = [], None
    try:
        for index, node in enumerate(NODES):
            source()
            need(not os.path.lexists(TOOLS.parent / 'plans/native_quiet_window.lock'), 'quiet window active')
            seconds = deadline - time.monotonic() - 20
            need(seconds > 0, 'combined180s deadline exhausted')
            unit = OUT / str(index)
            unit.mkdir()
            command = ['/usr/bin/sandbox-exec', '-f', str(profile), sys.executable,
                       '-S', '-P', '-B', str(Path(__file__).resolve()), '--worker', str(index)]
            with (unit / 'pytest.log').open('xb') as stream:
                result = guard.run(command, cwd=ROOT, env=env, evidence=unit / 'deadline',
                                   stream=stream, seconds=seconds)
            need(not result.expired and result.returncode == 0, 'unit failed: ' + node)
            xml = unit / 'pytest.xml'
            cases = list(ET.parse(xml).getroot().iter('testcase'))
            need(len(cases) == 1 and cases[0].get('name') == node.split('::')[1]
                 and not any(list(cases[0].iter(tag)) for tag in ('failure', 'error', 'skipped')),
                 'unit is not an exact one-test pass')
            need(json.loads((unit / 'worker.json').read_bytes())['returncode'] == 0,
                 'worker outcome differs')
            rows.append({'node': node, 'junit_sha256': sha(xml), 'log_sha256': sha(unit / 'pytest.log')})
        source()
        need(time.monotonic() <= deadline, 'combined180s deadline exceeded outside subprocess work')
    except BaseException as exc:
        error = repr(exc)
        raise
    finally:
        elapsed = time.monotonic() - started
        save(OUT / 'outcome.json', {'passed': error is None and len(rows) == 2 and elapsed <= 180,
            'completed': rows, 'error': error, 'seconds': elapsed,
            'limit_seconds': 180, 'scope': 'Two cheap refusal checks; no genuine native acceptance.'})


if __name__ == '__main__':
    need(sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode, '-S -P -B required')
    if sys.argv[1:2] == ['--worker']:
        need(len(sys.argv) == 3 and sys.argv[2] in {'0', '1'}, 'fixed worker index required')
        raise SystemExit(worker(int(sys.argv[2])))
    need(len(sys.argv) == 1, 'no cohort selection is supported')
    parent()
