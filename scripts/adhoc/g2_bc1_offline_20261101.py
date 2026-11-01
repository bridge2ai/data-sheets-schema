#!/usr/bin/env python3
# Purpose: isolated offline G2 checks, adapted from G1's reviewed launcher.
# Inputs: pinned checkout, module/script and arguments; outputs: logs and optional
# collected-node/event ledgers. G2 task-7 acceptance / 2026-11-01.
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
if not sys.flags.isolated:
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'fairscape_models'), str(ROOT)]
sys.path.extend(p for p in os.environ.get('G1_TEST_EXTRA_PATHS', '').split(os.pathsep) if p)
sys.path.append(str(site))
os.environ.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                  PIP_NO_INDEX='1', UV_OFFLINE='1', GIT_NO_LAZY_FETCH='1',
                  VIRTUAL_ENV=str(venv))
# Clear actual credentials before tests start. Descendants must retain the
# synthetic credentials that tests subsequently install for local fake peers.
if os.environ.get('G1_PROVIDER_KEYS_CLEARED') != '1':
    for key in list(os.environ):
        if key.endswith('_API_KEY'):
            os.environ.pop(key, None)
os.environ['G1_PROVIDER_KEYS_CLEARED'] = '1'

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
# -S suppresses ambient site startup, but tests explicitly install import guards
# on PYTHONPATH. Honor that one declared hook without processing any .pth files.
if not sys.flags.ignore_environment:
    for directory in os.environ.get('PYTHONPATH', '').split(os.pathsep):
        hook = Path(directory) / 'sitecustomize.py'
        if directory and hook.is_file():
            import importlib.util
            hook_spec = importlib.util.spec_from_file_location('sitecustomize', hook)
            hook_module = importlib.util.module_from_spec(hook_spec)
            sys.modules['sitecustomize'] = hook_module
            hook_spec.loader.exec_module(hook_module)
            break
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
            if (Path(command).name == 'poetry' and len(args) > 2 and args[1] == 'run'
                    and args[2] in {'python', 'gen-linkml', 'gen-project', 'd4d', 'linkml-validate'}):
                # Use the selected installed entry point, with no Poetry
                # environment creation or site/.pth startup in the child.
                args = [_python, '-S', '-B', _launcher, *args[2:]]
                command = _python
            if command == _python and '-S' not in args:
                rest = list(args[1:])
                flags = []
                # execnet's offline xdist coverage tests use python -u -c.
                while rest and rest[0] in ('-u', '-B', '-I', '-E', '-O', '-OO'):
                    flags.append(rest.pop(0))
                if rest and rest[0] in ('-V', '-VV', '--version'):
                    args = [_python, '-S', '-B', *flags, *rest]
                else:
                    args = [_python, '-S', '-B', *flags, _launcher, *rest]
            elif command == str(Path(_python).parent / 'linkml-validate'):
                args = [_python, '-S', '-B', _launcher, 'linkml-validate', *args[1:]]
            if _launcher in args and kwargs.get('env') is not None:
                # Native controls intentionally whitelist the child environment.
                # Carry the root's sanitization fact without modifying their dict.
                kwargs['env'] = dict(kwargs['env'], G1_PROVIDER_KEYS_CLEARED='1')
        # Nested pytest controls deliberately exercise child failures and their
        # own collections. Only the outer session owns the acceptance ledgers.
        child_env = dict(kwargs.get('env') if kwargs.get('env') is not None else os.environ)
        for key in ('G1_TEST_FAILURES_PATH', 'G2_COLLECTED_PATH', 'G2_TEST_EVENTS_PATH'):
            child_env.pop(key, None)
        kwargs['env'] = child_env
        super().__init__(args, *positional, **kwargs)


subprocess.Popen = OfflinePopen
target, *args = sys.argv[1:]
if target == 'python':
    target, *args = args
if target == '-m':
    target, *args = args
sys.argv = [target, *args]
if target == '-c':
    import types
    source, *args = args
    sys.argv = ['-c', *args]
    main_module = types.ModuleType('__main__')
    sys.modules['__main__'] = main_module
    exec(compile(source, '<string>', 'exec'), main_module.__dict__)
elif target in ('-V', '-VV', '--version'):
    raise SystemExit(subprocess.call([_python, '-S', target, *args]))
elif target == 'pytest':
    import pytest
    import json
    # Evidence is outside the system under test. Bind its I/O and destinations
    # before tests replace builtins.open or the environment to forbid product
    # access; otherwise a passing no-I/O control can abort pytest's reporting.
    evidence_open = open
    evidence_dumps = json.dumps
    evidence_paths = {key: os.environ.get(key) for key in
                      ('G2_COLLECTED_PATH', 'G2_TEST_EVENTS_PATH', 'G1_TEST_FAILURES_PATH')}
    if any(a == '-n' or a.startswith('--numprocesses') for a in args) and 'xdist.plugin' not in args:
        # Autoload stays disabled; explicitly load the plugin only when a
        # nested CI-partition coverage test requests workers. Top-level runs
        # remain serial, as required for this host.
        args += ['-p', 'xdist.plugin']

    class ImmediateFailures:
        def pytest_collection_finish(self, session):
            if evidence_paths['G2_COLLECTED_PATH']:
                with evidence_open(evidence_paths['G2_COLLECTED_PATH'], 'w') as output:
                    output.write(evidence_dumps([item.nodeid for item in session.items], indent=2) + '\n')

        def pytest_runtest_logreport(self, report):
            if evidence_paths['G2_TEST_EVENTS_PATH']:
                with evidence_open(evidence_paths['G2_TEST_EVENTS_PATH'], 'a') as output:
                    output.write(evidence_dumps({'nodeid': report.nodeid, 'when': report.when,
                        'outcome': report.outcome, 'seconds': report.duration}) + '\n')
            if report.failed:
                print('\nG1 immediate failure:', report.nodeid, '\n', report.longreprtext, flush=True)
                if evidence_paths['G1_TEST_FAILURES_PATH']:
                    with evidence_open(evidence_paths['G1_TEST_FAILURES_PATH'], 'a') as output:
                        output.write(evidence_dumps({'nodeid': report.nodeid, 'when': report.when,
                                                 'longrepr': report.longreprtext}) + '\n')

    raise SystemExit(pytest.main(args, plugins=[ImmediateFailures()]))
elif target.endswith('.py'):
    if not sys.flags.isolated:
        sys.path.insert(0, str(Path(target).resolve().parent))
    runpy.run_path(target, run_name='__main__')
elif target in {'gen-linkml', 'gen-project', 'd4d', 'linkml-validate'}:
    from importlib.metadata import entry_points
    raise SystemExit(next(iter(entry_points(group='console_scripts', name=target))).load()())
else:
    runpy.run_module(target, run_name='__main__', alter_sys=True)
