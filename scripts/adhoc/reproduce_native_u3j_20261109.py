#!/usr/bin/env python3
"""U3-J/UCPU3-1 guard reproduction and scope-stop evidence, 2026-11-09.

Inputs: exact private c6c5dc821 Git repository and retained round-3 runtime.
Outputs: new scratch worktree, sandboxed refusal evidence and verified cleanup.
Never launches a native program or public attempt, installs packets, or changes
a runtime guard/deadline. Invoke with physical dependency Python -S -P -B.
"""
from __future__ import annotations
import errno
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
BASE = EXEC / 'scratch-native-u1u3/u3j'
TREE = BASE / 'tree'
PRIVATE = EXEC / 'scratch-native-u1u3/u3g/composition-26d3b0449b01/tree/.git'
HEAD = 'c6c5dc821fda057a984155aeb8388ca41b22be02'
PRIMARY = EXEC.parent / 'data-sheets-schema'
LOCK = EXEC / 'plans/native_quiet_window.lock'
CONFIG = PRIVATE / 'config'
BACKUP = PRIVATE / 'config.bak-u3j-20261109'
CONFIG_SHA = 'cae33efdb02cf774435c1ff9cb16bcc1014606908530c6e1dc727615fe3e8cda'
RUNTIME = EXEC / ('scratch-native-u3-deadline/cpu-profile2-20261109/'
    'round3-correction-control/cases/popen-gw0/'
    'test_actual_public_correction_0/native26/authority/runtime-execution.json')
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def git(*args, cwd=ROOT):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd, env=ENV, text=True, timeout=120).strip()


def private(*args):
    return git('--git-dir=' + str(PRIVATE), *args)


def quiet():
    if os.path.lexists(LOCK):
        raise RuntimeError('quiet-window lock active; stopped')


def setup():
    quiet()
    assert ROOT.name == 'codex-native-u1u3' and not git('status', '--porcelain')
    assert private('rev-parse', 'HEAD') == HEAD and sha(CONFIG) == CONFIG_SHA
    assert not os.path.lexists(BASE) and not os.path.lexists(BACKUP)
    BASE.mkdir()
    with BACKUP.open('xb') as stream:
        stream.write(CONFIG.read_bytes())
    private('worktree', 'add', '--detach', str(TREE), HEAD)
    url = git('config', '--local', '--get', 'remote.origin.url', cwd=PRIMARY)
    assert url == 'https://github.com/bridge2ai/data-sheets-schema.git'
    private('config', '--local', 'd4d.ciRepositoryUrl', url)
    save(BASE / 'setup.json', dict(head=HEAD, harness_head=git('rev-parse', 'HEAD'),
        worktree=str(TREE), private_git=str(PRIVATE), original_config_sha256=CONFIG_SHA,
        configured_sha256=sha(CONFIG), ci_url=url, runtime_path=str(RUNTIME),
        runtime_sha256=sha(RUNTIME), helper_sha256=sha(Path(__file__))))


def refusal(function, value, expected):
    try:
        function(value)
    except ValueError as exc:
        if str(exc) != expected:
            raise
        return dict(function=function.__module__ + '.' + function.__name__,
            exception=type(exc).__name__, message=str(exc),
            traceback=traceback.format_exc())
    raise AssertionError('required refusal did not occur')


def child():
    wall, cpu = time.monotonic(), time.process_time()
    deps = PRIMARY / '.venv' / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    assert deps == deps.resolve(strict=True)
    fair = EXEC / 'scratch-native-u1u3/dependencies/fairscape-8c80311d7d8b0fadac07dca9567d632103691f48/tree'
    sys.path[:0] = [str(TREE / 'src'), str(TREE), str(fair), str(deps)]
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', 0))
        except OSError as exc:
            assert exc.errno == errno.EPERM
        else:
            raise AssertionError('OS network denial missing')
    from data_sheets_schema.native_supervisor_authority_v2 import head
    from data_sheets_schema.native_execution_registration_v2 import _ci_repository_url
    from data_sheets_schema import native_u4b_runtime as runtime_guard
    from data_sheets_schema import native_u4b_policy as policy
    assert head() == HEAD
    assert _ci_repository_url() == 'https://github.com/bridge2ai/data-sheets-schema'
    original = json.loads(RUNTIME.read_bytes())
    first = refusal(runtime_guard.validate_prepared_runtime, original,
        'U4b requires D106 high/Max, D112 model/context and D110 decimal-string budget')
    corrected = json.loads(json.dumps(original))
    corrected['model'] = runtime_guard.MODEL
    corrected['environment']['CLAUDE_CODE_DISABLE_1M_CONTEXT'] = '0'
    corrected['budget_guard_usd'] = '90'
    corrected['auth']['subscriptionType'] = 'max'
    # In-memory diagnostic only: no new observation or launch evidence is made.
    # This shows profile correction cannot reconcile the next mandatory term.
    runtime_guard._profile(corrected)
    assert corrected['deadline_seconds'] == original['deadline_seconds'] == 900
    second = refusal(policy.validate_runtime_terms, corrected,
                     'registered deadline must equal N1.8 21600 seconds')
    origins = {}
    for name, module in list(sys.modules.items()):
        if name == 'data_sheets_schema' or name.startswith('data_sheets_schema.'):
            path = getattr(module, '__file__', None)
            if path:
                actual = Path(path).resolve(strict=True)
                assert actual.is_relative_to(TREE / 'src'), (name, str(actual))
                origins[name] = str(actual)
    save(BASE / 'refusals.json', dict(head=HEAD, pid=os.getpid(), ppid=os.getppid(), first=first, deadline=second,
        runtime_sha256=sha(RUNTIME), original_fields=dict(model=original['model'],
            effort=original['effort'], context_disable=original['environment']['CLAUDE_CODE_DISABLE_1M_CONTEXT'],
            budget=original['budget_guard_usd'], subscription=original['auth']['subscriptionType']),
        preserved_attempt_limit=original['deadline_seconds'], required_policy_limit=policy.N1_DEADLINE_SECONDS,
        profile_only_correction_valid=True, public_attempt_started=False,
        full_prepared_runtime_after_correction_validated=False,
        network_denied=True, source_origins=origins,
        process_cpu_seconds=time.process_time()-cpu, wall_seconds=time.monotonic()-wall,
        production_files={name: sha(TREE / 'src/data_sheets_schema' / name) for name in (
            'native_u4b_runtime.py', 'native_u4b_policy.py',
            'native_shared_execution_orchestration.py', 'native_execution_orchestration.py')},
        scope='Exact original public runtime guard plus mandatory deadline guard; not a completed public test or real-binary observation'))


def run():
    quiet()
    setup_data = json.loads((BASE / 'setup.json').read_bytes())
    assert sha(CONFIG) == setup_data['configured_sha256']
    assert git('rev-parse', 'HEAD', cwd=TREE) == HEAD and not git('status', '--porcelain', cwd=TREE)
    for sub in ('home', 'tmp'):
        (BASE / sub).mkdir()
    profile = BASE / 'deny.sb'
    profile.write_text('(version 1)\n(allow default)\n(deny network*)\n'
        '(deny process-exec (regex #"/(claude|codex|gemini|agy)(/|$)"))\n'
        '(deny file-write* (require-all (require-not (subpath ' + json.dumps(str(BASE)) + ')) '
        '(require-not (literal "/dev/null")) (require-not (literal "/dev/tty"))))\n')
    env = {**ENV, 'HOME': str(BASE / 'home'), 'TMPDIR': str(BASE / 'tmp'),
           'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
           'PIP_NO_INDEX': '1', 'UV_OFFLINE': '1', 'LANG': 'en_US.UTF-8'}
    command = ['/usr/bin/sandbox-exec', '-f', str(profile), sys.executable,
               '-S', '-P', '-B', str(Path(__file__).resolve()), 'child']
    start = time.monotonic()
    with (BASE / 'guard.log').open('xb') as log:
        result = subprocess.run(command, cwd=TREE, env=env, stdout=log,
                                stderr=subprocess.STDOUT, timeout=90)
    assert result.returncode == 0 and (BASE / 'refusals.json').stat().st_size > 0
    assert not git('status', '--porcelain', cwd=TREE)
    save(BASE / 'outcome.json', dict(returncode=result.returncode,
        wall_seconds=time.monotonic()-start, invocation_limit_seconds=90,
        command=command, environment=env, source_unchanged=True,
        refusal_sha256=sha(BASE / 'refusals.json'), public_tests_run=0))
    print((BASE / 'outcome.json').read_text())


def cleanup():
    setup_data = json.loads((BASE / 'setup.json').read_bytes())
    assert sha(CONFIG) == setup_data['configured_sha256'], 'concurrent private config edit'
    assert sha(BACKUP) == CONFIG_SHA
    private('config', '--local', '--unset', 'd4d.ciRepositoryUrl')
    assert sha(CONFIG) == CONFIG_SHA and CONFIG.read_bytes() == BACKUP.read_bytes()
    # Remove only this newly-created, clean scratch worktree, as the brief asks.
    assert TREE.resolve() == TREE and git('rev-parse', 'HEAD', cwd=TREE) == HEAD
    assert not git('status', '--porcelain', cwd=TREE)
    private('worktree', 'remove', str(TREE))
    assert not os.path.lexists(TREE)
    retained = BASE / 'private-config.original'
    assert not os.path.lexists(retained)
    BACKUP.rename(retained)
    save(BASE / 'cleanup.json', dict(config_restored_sha256=sha(CONFIG),
        original_config_sha256=sha(retained), new_worktree_removed=True,
        worktrees=private('worktree', 'list', '--porcelain')))


if __name__ == '__main__':
    {'setup': setup, 'run': run, 'child': child, 'cleanup': cleanup}[sys.argv[1]]()
