#!/usr/bin/env python3
# Purpose: isolated offline G1 checks; inputs: module/script and arguments.
# Outputs: selected check stdout/artifacts; generality F2-F19, 2026-10-29.
import os
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(os.environ.get('G1_CHECKOUT_ROOT', Path(__file__).resolve().parents[2])).resolve()
if not sys.flags.no_site:
    raise SystemExit('Invoke with python -S; site/.pth initialization is forbidden')
venv = Path(sys.executable).parent.parent
site = venv / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
sys.prefix = sys.exec_prefix = str(venv)
# CI initializes this local dependency. Put its actual package ahead of the
# enclosing checkout, whose submodule directory can otherwise become a cached
# namespace package during whole-tree collection.
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'fairscape_models'), str(ROOT)]
sys.path.extend(p for p in os.environ.get('G1_TEST_EXTRA_PATHS', '').split(os.pathsep) if p)
sys.path.append(str(site))
os.environ.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                  PIP_NO_INDEX='1', UV_OFFLINE='1', GIT_NO_LAZY_FETCH='1')
for key in list(os.environ):
    if key.endswith('_API_KEY'):
        os.environ.pop(key, None)

def offline(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
        # Offline CI transport controls exercise local fake servers. Match the
        # independent review harness: allow loopback/Unix sockets only.
        if event == 'socket.connect':
            address = args[1]
            if isinstance(address, str) or (isinstance(address, tuple) and address[0] in
                                           ('127.0.0.1', '::1', 'localhost')):
                return
        if event == 'socket.getaddrinfo' and args[0] in ('127.0.0.1', '::1', 'localhost', None):
            return
        raise RuntimeError('G1 offline checks forbid network: ' + event)

sys.addaudithook(offline)
# Carry -S and the socket guard into Python/LinkML children as well. Existing
# explicitly isolated children (including the foreign-tree authority fixtures)
# retain their own declared sys.path and environment.
_Popen = subprocess.Popen
_python = str(Path(sys.executable).absolute())
_launcher = str(Path(__file__).resolve())


class OfflinePopen(_Popen):
    def __init__(self, args, *positional, **kwargs):
        if isinstance(args, (list, tuple)) and args:
            command = str(args[0])
            if command == _python and '-S' not in args:
                args = [_python, '-S', '-B', _launcher, *args[1:]]
            elif command == str(Path(_python).parent / 'linkml-validate'):
                args = [_python, '-S', '-B', _launcher, 'linkml-validate', *args[1:]]
        super().__init__(args, *positional, **kwargs)


subprocess.Popen = OfflinePopen
target, *args = sys.argv[1:]
if target == 'python':
    target, *args = args
if target == '-m':
    target, *args = args
sys.argv = [target, *args]
if target == '-c':
    source, *args = args
    sys.argv = ['-c', *args]
    exec(compile(source, '<isolated-child>', 'exec'), {'__name__': '__main__'})
elif target == 'pytest':
    import pytest

    class ImmediateFailures:
        def pytest_runtest_logreport(self, report):
            if report.failed:
                print('\nG1 immediate failure:', report.nodeid, '\n', report.longreprtext, flush=True)
                if os.environ.get('G1_TEST_FAILURES_PATH'):
                    import json
                    with open(os.environ['G1_TEST_FAILURES_PATH'], 'a') as output:
                        output.write(json.dumps({'nodeid': report.nodeid, 'when': report.when,
                                                 'longrepr': report.longreprtext}) + '\n')

    raise SystemExit(pytest.main(args, plugins=[ImmediateFailures()]))
elif target.endswith('.py'):
    runpy.run_path(target, run_name='__main__')
elif target in {'gen-linkml', 'gen-project', 'd4d', 'linkml-validate'}:
    from importlib.metadata import entry_points
    raise SystemExit(next(iter(entry_points(group='console_scripts', name=target))).load()())
else:
    runpy.run_module(target, run_name='__main__', alter_sys=True)
