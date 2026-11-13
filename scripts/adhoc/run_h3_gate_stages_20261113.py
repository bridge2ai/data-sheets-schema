#!/usr/bin/env python3
"""Closed offline stage orchestration for H3-RF17, 2026-11-13.

Inputs: one frozen G commit and an owned cohort; outputs: separately bounded,
immutable stage evidence. Builders inherit the OS sandbox; gate parents do not.
Their validation workers retain the unchanged read-only OS sandbox. This file
is a draft until its fixed G stage worker and launcher repair are reviewed.
No arbitrary command, provider, native execution, probe, capture or reservation.
"""
from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

N = Path(__file__).resolve().parents[2]
E = N.parent
G = E / 'codex-native-pin-comparison-20261113'
S = E / 'scratch-h3-gate-refinements-20261113'
LOCK = E / 'plans/native_quiet_window.lock'
SELF = Path(__file__).resolve()
RUNNER = 'scripts/adhoc/run_h3_refinement_tests_20261113.py'
WORKER = 'scripts/adhoc/h3_gate_stage_worker_20261113.py'
PLAN = 'scripts/adhoc/h3_gate_stage_roles_20261113.json'
DRIVER = 'scripts/adhoc/run_h3_refinement_demonstration_20261113.py'
CONTROL = 'scripts/adhoc/h3_source_commit_control_20261113.py'
PARENT_LAUNCH = 'scripts/adhoc/h3_gate_parent_launch_20261113.py'
MUTATOR = 'scripts/adhoc/h3_refinement_mutations_20261113.py'
VALIDATOR = 'scripts/native_registration_validation_worker.py'
GATE = 'scripts/native_registration_pin_gate.py'
BOUNDS = N / 'scripts/adhoc/h3_gate_bounds_20261113.json'
ROLES = ('reference', 'later', 'AI_READI', 'CM4AI', 'VOICE',
         'VOICE_PEDIATRIC', 'registered', 'expired')
STAGES = ('bootstrap', 'setup-peer', 'build', 'canary', 'snapshots',
          'private-controls', 'assemble-report', 'full')
DATA = (PLAN, 'scripts/adhoc/h3_refinement_cases_20261113.json',
        'scripts/native_registration_fields_v1.json')
GIT = '/Library/Developer/CommandLineTools/usr/bin/git'
COUNTERS = {'native_executions': 0, 'model_calls': 0, 'probes_executed': 0, 'captures': 0, 'reservations': 0}


def physical(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or path.resolve(strict=True) != path:
        raise ValueError('stage path must be physical and absolute')
    return path


def read(path):
    path = physical(path)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 256_000_000:
            raise ValueError('stage input must be a bounded regular file')
        raw = stream.read(256_000_001)
        after = os.fstat(stream.fileno())
    names = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    identity = lambda info: tuple(getattr(info, name) for name in names)
    if identity(before) != identity(after) or identity(after) != identity(path.lstat()) or len(raw) != before.st_size:
        raise ValueError('stage input changed while read')
    return raw


def pin(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def checked(item):
    if type(item) is not dict or set(item) != {'path', 'bytes', 'sha256'}:
        raise ValueError('stage requires an exact file pin')
    raw = read(item['path'])
    if type(item['bytes']) is not int or len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
        raise ValueError('stage input differs from its pinned bytes')
    return raw


def save(path, value):
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n'
    with Path(path).open('xb') as stream:
        stream.write(raw)
    Path(path).chmod(0o444)
    return pin(path)


def source_module(item, name):
    namespace = {'__name__': name, '__file__': item['path']}
    exec(compile(checked(item), item['path'], 'exec'), namespace)
    return namespace


def git_environment():
    return {'PATH': '/Library/Developer/CommandLineTools/usr/bin:/usr/bin:/bin',
        'HOME': '/var/empty', 'LANG': 'en_US.UTF-8', 'GIT_NO_LAZY_FETCH': '1',
        'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}


def git(*args):
    return subprocess.check_output([GIT, '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
        '-c', 'core.fsmonitor=false', '-c', 'protocol.allow=never', *args],
        cwd=G, env=git_environment(), timeout=60)


def capture_sources(commit):
    if not re.fullmatch('[0-9a-f]{40}', commit) or git('rev-parse', '--verify', 'HEAD^{commit}').decode().strip() != commit:
        raise ValueError('actual G HEAD differs from the fixed stratum commit')
    sources = {}
    for row in git('ls-tree', '-rz', '--full-tree', commit).decode().split('\0'):
        if not row:
            continue
        metadata, name = row.split('\t', 1)
        mode, kind, blob = metadata.split()
        if not (name.endswith('.py') or name in DATA):
            continue
        if kind != 'blob' or mode not in ('100644', '100755') or '..' in Path(name).parts or Path(name).is_absolute():
            raise ValueError('stage source roster contains a nonregular member')
        raw = read(G / name)
        git_digest = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if git_digest != blob:
            raise ValueError('working source differs from frozen commit: ' + name)
        sources[name] = {'path': str(G / name), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    for name in (RUNNER, WORKER, DRIVER, CONTROL, PARENT_LAUNCH, VALIDATOR, GATE, MUTATOR, *DATA):
        if name not in sources:
            raise ValueError('required fixed stage source is absent: ' + name)
    return sources


def cohort_path(path, *, fresh=False):
    path = Path(path)
    if path.parent != S / 'tests' or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]*', path.name):
        raise ValueError('cohort must be a direct named child of the owned test root')
    physical(path.parent)
    if fresh:
        if path.exists() or path.is_symlink():
            raise ValueError('bootstrap requires a fresh cohort')
    else:
        physical(path)
    return path


def stage_name(action, role=None):
    if action not in STAGES or (action == 'build') != (role in ROLES):
        raise ValueError('unknown stage or role')
    if action != 'build' and role is not None:
        raise ValueError('only the fixed build stage takes a role')
    return action + ('-' + role if action == 'build' else '')


def predecessors(action, role=None):
    stage_name(action, role)
    if action == 'bootstrap':
        return []
    if action == 'setup-peer':
        return ['bootstrap']
    if action == 'build':
        index = ROLES.index(role)
        return ['setup-peer'] if index == 0 else ['canary', 'build-' + ROLES[index - 1]]
    return {'canary': ['build-reference'], 'snapshots': ['build-expired'],
        'private-controls': ['snapshots'], 'assemble-report': ['private-controls'],
        'full': ['assemble-report']}[action]


def verify_predecessors(cohort, action, role=None):
    declarations = {}
    configuration = pin(cohort / 'stage-config.json')
    for name in predecessors(action, role):
        declaration = pin(cohort / 'stages' / name / 'outcome.json')
        outcome = json.loads(checked(declaration))
        if outcome.get('status') != 'passed' or outcome.get('cleanup_verified') is not True:
            raise ValueError('required stage did not complete cleanly: ' + name)
        result = json.loads(checked(outcome['result']))
        expected_action, expected_role = ('build', name[6:]) if name.startswith('build-') else (name, None)
        if (result.get('status') != 'passed' or result.get('config') != configuration
                or result.get('action') != expected_action or result.get('role') != expected_role
                or name != 'bootstrap' and result.get('side_effects') != COUNTERS):
            raise ValueError('required stage lacks its persisted result: ' + name)
        for item in result.get('outputs', {}).values():
            checked(item)
        declarations[name] = declaration
    return declarations


def install_orchestrator_audit(command, write_roots):
    """The N supervisor is also explicit about its own non-sandboxed boundary."""
    allowed = None if command is None else tuple(map(str, command))
    roots = tuple(map(Path, write_roots))
    git_prefix = [GIT, '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
                  '-c', 'core.fsmonitor=false', '-c', 'protocol.allow=never']
    def audit(event, args):
        if event in {'socket.bind', 'socket.connect', 'socket.getaddrinfo', 'socket.sendto',
                     'os.system', 'os.exec', 'os.posix_spawn', 'ctypes.dlopen'}:
            raise PermissionError('fixed orchestrator network/native escape denied')
        if event == 'subprocess.Popen':
            executable, argv, cwd, environment = args
            values = tuple(map(str, argv))
            if allowed is not None and values == allowed:
                return
            if (list(values[:8]) == git_prefix and len(values) > 8
                    and values[8] in ('rev-parse', 'ls-tree') and str(cwd) == str(G)):
                return
            raise PermissionError('orchestrator may launch only its exact planned stage')
        paths = []
        if event == 'open':
            path, mode, flags = args
            if (isinstance(mode, str) and any(char in mode for char in 'wax+')
                    or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                paths = [path]
        elif event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.utime'}:
            paths = [args[0]]
        elif event in {'os.rename', 'os.link'}:
            paths = list(args[:2])
        elif event == 'os.symlink':
            paths = [args[1]]
        for value in paths:
            if isinstance(value, int):
                continue
            target = Path(os.fsdecode(value)).absolute().resolve()
            if target != Path('/dev/null') and not any(target == root or target.is_relative_to(root) for root in roots):
                raise PermissionError('orchestrator write escaped its fixed stage')
    sys.addaudithook(audit)


def bootstrap(cohort, commit):
    cohort = cohort_path(cohort, fresh=True)
    sources = capture_sources(commit)
    runner = source_module(sources[RUNNER], 'fixed_stage_lifecycle')
    dependency = runner['dependency_site']()
    if LOCK.exists():
        raise ValueError('quiet window active; bootstrap refused')
    for parent in (S / 'demonstrations', S / 'source-commit'):
        if not parent.exists():
            parent.mkdir()
        physical(parent)
    install_orchestrator_audit(None, [cohort])
    cohort.mkdir(mode=0o700)
    for name in ('home', 'tmp', 'stages', 'cases'):
        (cohort / name).mkdir()
    stage = cohort / 'stages/bootstrap'
    stage.mkdir()
    python = runner['make_test_venv'](cohort, dependency)
    sites = list((cohort / 'venv/lib').glob('python*/site-packages'))
    if len(sites) != 1:
        raise ValueError('new cohort has an ambiguous installed dependency root')
    packet_root = cohort / 'cases/test_final_format_registration0'
    packet_root.mkdir()
    peer_root = packet_root / 'SYNTHETIC-shared-peer'
    config = {'kind': 'SYNTHETIC-native-gate-stage-config', 'version': 1,
        'source_root': str(G), 'source_commit': commit, 'cohort': str(cohort),
        'python': str(python), 'dependency_prefix': str(cohort / 'venv'),
        'dependency_roots': [str(sites[0]), str(dependency)], 'packet_root': str(packet_root),
        'peer_root': str(peer_root), 'home': str(peer_root / 'synthetic-home'), 'bounds': pin(BOUNDS),
        'code_inputs': sources,
        'plan': sources[PLAN], 'bootstrap': pin(cohort / 'bootstrap.json')}
    declaration = save(cohort / 'stage-config.json', config)
    envelope = save(cohort / 'orchestration-inputs.json', {'config': declaration,
        'sources': sources, 'launcher': pin(SELF), 'source_commit': commit,
        'interpreter': pin(python.resolve(strict=True)), 'venv_config': pin(cohort / 'venv/pyvenv.cfg')})
    result = save(stage / 'result.json', {'status': 'passed', 'action': 'bootstrap', 'role': None,
        'config': declaration, 'outputs': {'configuration': declaration, 'orchestration': envelope},
        'scope': 'venv/bootstrap only; shared peer has not been created or executed'})
    return save(stage / 'outcome.json', {'status': 'passed', 'cleanup_verified': True,
        'result': result, 'scope': 'synchronous fixed venv bootstrap; no child stage launched'})


def load_cohort(cohort, commit):
    cohort = cohort_path(cohort)
    envelope = json.loads(read(cohort / 'orchestration-inputs.json'))
    if envelope['config']['path'] != str(cohort / 'stage-config.json'):
        raise ValueError('orchestration envelope names another cohort configuration')
    if envelope['source_commit'] != commit or checked(envelope['launcher']) != read(SELF):
        raise ValueError('stage launcher or source identity changed')
    config = json.loads(checked(envelope['config']))
    packet_root = cohort / 'cases/test_final_format_registration0'
    expected = {'cohort': str(cohort), 'source_root': str(G), 'source_commit': commit,
        'python': str(cohort / 'venv/bin/python'), 'dependency_prefix': str(cohort / 'venv'),
        'packet_root': str(packet_root), 'peer_root': str(packet_root / 'SYNTHETIC-shared-peer'),
        'home': str(packet_root / 'SYNTHETIC-shared-peer/synthetic-home')}
    if (any(config.get(name) != value for name, value in expected.items())
            or config.get('code_inputs') != envelope['sources']):
        raise ValueError('configuration differs from the requested cohort/source identity')
    if capture_sources(commit) != envelope['sources']:
        raise ValueError('stage source bytes changed after bootstrap')
    for key in ('interpreter', 'venv_config'):
        checked(envelope[key])
    checked(config['bounds']); checked(config['bootstrap'])
    boot = json.loads(checked(config['bootstrap']))
    sites = list((cohort / 'venv/lib').glob('python*/site-packages'))
    if (len(sites) != 1 or config['dependency_roots'] != [str(sites[0]), boot['dependency_site']]
            or config['bootstrap']['path'] != str(cohort / 'bootstrap.json')
            or boot['test_python'] != config['python']
            or envelope['interpreter']['path'] != str(Path(config['python']).resolve(strict=True))
            or envelope['venv_config']['path'] != str(cohort / 'venv/pyvenv.cfg')):
        raise ValueError('configuration differs from its actual original cohort bootstrap')
    for name, digest in boot['files'].items():
        if pin(Path(name))['sha256'] != digest:
            raise ValueError('cohort bootstrap bytes changed')
    for name, expected in boot['controlled_distribution']['files'].items():
        current = pin(Path(name))
        if any(current[key] != expected[key] for key in ('bytes', 'sha256')):
            raise ValueError('controlled installed distribution is not at its restored baseline')
    return config, envelope


def sandbox_profile(runner, cohort, stage):
    # Only packet stages inherit this. A gate parent must never inherit it.
    return runner['sandbox_profile']() + (
        '(deny file-write* (require-all (require-not (subpath ' + json.dumps(str(cohort)) + '))'
        ' (require-not (literal "/dev/null")) (require-not (literal "/dev/tty"))))\n'
        '(deny file-write* (subpath ' + json.dumps(str(G)) + '))\n'
        '(deny file-write* (subpath ' + json.dumps(str(N)) + '))\n')


def supervise(child, owned, quiet, *, seconds, clock=time.monotonic, sleep=time.sleep):
    started = previous = clock()
    active, interrupted, forced = 0.0, None, False
    try:
        while child.poll() is None:
            tick = clock()
            if not quiet.paused:
                active += tick - previous
            previous = tick
            owned.observe()
            if active >= seconds:
                interrupted = 'active_deadline'
                break
            quiet.update(owned)
            sleep(0.25)
    except BaseException as error:
        interrupted = type(error).__name__
    finally:
        owned.observe()
        if quiet.paused:
            owned.signal(signal.SIGCONT)
        if owned.live():
            forced = True
            owned.signal(signal.SIGTERM)
            until = clock() + 5
            while owned.live() and clock() < until:
                sleep(0.1)
            if owned.live():
                owned.signal(signal.SIGKILL)
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            interrupted = interrupted or 'cleanup_timeout'
    return {'active_seconds': active, 'wall_seconds': clock() - started,
        'interrupted': interrupted, 'forced_cleanup': forced,
        'observed_surviving_pids': [process.pid for process in owned.live()],
        'observation_errors': list(owned.errors), 'observed_processes': sorted(owned.known)}


def program(item, arguments):
    raw = checked(item)
    return ('import sys\nsys.argv = ' + repr([item['path'], *arguments]) + '\n'
        + 'exec(compile(' + repr(raw) + ', ' + repr(item['path']) + ", 'exec'), "
        + repr({'__name__': '__main__', '__file__': item['path']}) + ')\n').encode()


def run_stage(cohort, commit, action, role, timeout):
    if not 1 <= timeout <= 14400:
        raise ValueError('stage active-time bound must be 1..14400 seconds')
    name = stage_name(action, role)
    config, envelope = load_cohort(cohort, commit)
    cohort = Path(config['cohort'])
    prior = verify_predecessors(cohort, action, role)
    if LOCK.exists():
        raise ValueError('quiet window active; no stage was launched')
    stage = cohort / 'stages' / name
    stage.mkdir()
    inputs = save(stage / 'inputs.json', {'config': envelope['config'], 'launcher': envelope['launcher'],
        'action': action, 'role': role, 'predecessors': prior, 'timeout_active_seconds': timeout})
    sources = envelope['sources']
    runner = source_module(sources[RUNNER], 'fixed_stage_lifecycle')
    dependency = runner['dependency_site']()
    sys.path.append(str(dependency))
    import psutil
    builder = action in ('setup-peer', 'build', 'snapshots', 'assemble-report')
    if builder:
        arguments = ['--config', envelope['config']['path'], '--config-sha256', envelope['config']['sha256'],
                     '--config-bytes', str(envelope['config']['bytes']), '--action', action]
        if role is not None:
            arguments += ['--role', role]
        raw = program(sources[WORKER], arguments)
    elif action in ('canary', 'full'):
        launcher = source_module(sources[PARENT_LAUNCH], 'fixed_stage_gate_parent_launcher')
        report = Path(config['packet_root']) / ('reference-report.json' if action == 'canary' else 'expanded-project-report.json')
        destination = S / 'demonstrations' / (cohort.name + ('-self-canary' if action == 'canary' else '-full'))
        command = [config['python'], '-I', '-S', '-B', str(G / DRIVER),
            '--cohort', str(cohort), '--report', str(report), '--output', str(destination),
            '--worker-timeout-seconds', '3600']
        if action == 'canary':
            command += ['--canary-only']
        raw = launcher['captured_driver_program'](command, code_inputs=sources)
        save(stage / 'driver-command.json', {'original_command': command,
            'source': sources[DRIVER], 'launcher': sources[PARENT_LAUNCH]})
    else:
        raw = program(envelope['launcher'], ['--child-inputs', inputs['path'],
            '--child-sha256', inputs['sha256'], '--child-bytes', str(inputs['bytes'])])
    bootstrap_pin = save(stage / 'captured-bootstrap.py', raw)
    command = [config['python'], '-I', '-S', '-B', '-']
    profile = None
    if builder:
        profile = save(stage / 'builder.sb', sandbox_profile(runner, cohort, stage).encode())
        command = ['/usr/bin/sandbox-exec', '-f', profile['path'], *command]
    environment = runner['clean_environment'](cohort, Path(config['python']).parent)
    environment.update(git_environment())
    environment['HOME'] = str(cohort / 'home')
    environment['TMPDIR'] = str(cohort / 'tmp')
    save(stage / 'command.json', {'command': command, 'environment': environment,
        'cwd': str(G), 'bootstrap': bootstrap_pin, 'input': inputs, 'sandbox': profile,
        'gate_parent_inherits_os_sandbox': False if not builder else 'not a gate parent'})
    install_orchestrator_audit(command, [stage])
    child = owned = None
    outcome = {}
    with (stage / 'stdout.log').open('xb') as stdout, (stage / 'stderr.log').open('xb') as stderr:
        try:
            child = subprocess.Popen(command, cwd=G, env=environment, stdin=subprocess.PIPE,
                stdout=stdout, stderr=stderr, start_new_session=True)
            owned = runner['OwnedProcesses'](psutil, child.pid)
            child.stdin.write(raw)
            child.stdin.close()
            outcome = supervise(child, owned, runner['QuietWindow'](LOCK), seconds=timeout)
        except BaseException as error:
            if owned is not None:
                owned.signal(signal.SIGTERM)
            elif child is not None and child.poll() is None:
                child.terminate()
            if child is not None:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if owned is not None:
                        owned.signal(signal.SIGKILL)
                    else:
                        child.kill()
                    child.wait(timeout=5)
            outcome = {'interrupted': type(error).__name__ + ': ' + str(error),
                'forced_cleanup': child is not None, 'observed_surviving_pids': [] if owned is None else [p.pid for p in owned.live()],
                'observation_errors': [] if owned is None else list(owned.errors),
                'observed_processes': [] if owned is None else sorted(owned.known)}
    returncode = None if child is None else child.returncode
    outcome['inputs'] = inputs
    return finalize_stage(stage, cohort=cohort, commit=commit, action=action, role=role,
        envelope=envelope, prior=prior, outcome=outcome, returncode=returncode,
        destination=destination if action in ('canary', 'full') else None)


def finalize_stage(stage, *, cohort, commit, action, role, envelope, prior, outcome, returncode, destination=None):
    """Always preserve attempted-stage outcome, even when child proof is absent."""
    outcome = dict(outcome)
    result, document, proof_error = None, {}, None
    try:
        if action in ('canary', 'full') and returncode == 0:
            aggregate_pin = pin(destination / 'demonstration-results.json')
            outcome['demonstration_proof'] = aggregate_pin
            aggregate = json.loads(checked(aggregate_pin))
            expected_status = 'canary_passed' if action == 'canary' else 'all_requested_demonstrations_passed'
            expected_count = (1 if action == 'canary' else len(json.loads(checked(
                envelope['sources']['scripts/adhoc/h3_refinement_cases_20261113.json']))['cases']))
            if aggregate.get('status') != expected_status or len(aggregate.get('cases', [])) != expected_count:
                raise ValueError('fixed driver exit lacks its persisted complete comparison proof')
            if action == 'canary' and aggregate['cases'][0]['status'] != 'equal':
                raise ValueError('reference self-gate did not establish equality')
            save(stage / 'result.json', {'status': 'passed', 'action': action, 'role': role,
                'config': envelope['config'], 'outputs': {'demonstration': aggregate_pin}, 'side_effects': COUNTERS})
        result_path = stage / 'result.json'
        result = pin(result_path) if result_path.is_file() else None
        document = json.loads(checked(result)) if result is not None else {}
        if type(document) is not dict:
            document = {}
            raise ValueError('child stage result must be a JSON object')
    except Exception as error:
        proof_error = type(error).__name__ + ': ' + str(error)
    clean = (returncode is not None and returncode >= 0
        and not outcome['interrupted'] and not outcome['forced_cleanup']
        and not outcome['observed_surviving_pids'] and not outcome['observation_errors'])
    passed = (clean and proof_error is None and returncode == 0 and document.get('status') == 'passed'
        and document.get('config') == envelope['config'] and document.get('action') == action
        and document.get('role') == role and document.get('side_effects') == COUNTERS)
    outcome.update(status='passed' if passed else 'held', returncode=returncode,
        cleanup_verified=clean, result=result, proof_error=proof_error,
        cleanup_scope='observed PID/creation-time descendants only; no proof about never-observed orphans')
    try:
        load_cohort(cohort, commit)
        for item in prior.values():
            checked(item)
        for item in document.get('outputs', {}).values():
            checked(item)
    except Exception as error:
        outcome.update(status='held', postflight_error=type(error).__name__ + ': ' + str(error))
    return save(stage / 'outcome.json', outcome)


def child(inputs_pin):
    inputs = json.loads(checked(inputs_pin))
    if inputs['action'] != 'private-controls' or inputs['role'] is not None:
        raise ValueError('only the fixed private-control coordinator uses this child entry')
    config = json.loads(checked(inputs['config']))
    cohort = Path(config['cohort'])
    if (not sys.flags.isolated or not sys.flags.no_site or not sys.dont_write_bytecode
            or sys.executable != config['python'] or Path(config['dependency_prefix']) != cohort / 'venv'):
        raise ValueError('private coordinator requires its actual isolated cohort interpreter')
    config, envelope = load_cohort(cohort, config['source_commit'])
    stage = cohort / 'stages/private-controls'
    if inputs_pin['path'] != str(stage / 'inputs.json'):
        raise ValueError('private coordinator input is outside its fixed stage')
    sources = envelope['sources']
    original = [value for value in sys.path if value and Path(value).is_absolute()]
    first_party = [str(G / 'src'), str(G)]
    if (G / 'fairscape_models/fairscape_models').is_dir():
        first_party.append(str(G / 'fairscape_models'))
    sys.path[:] = list(dict.fromkeys([*first_party, *original, *config['dependency_roots']]))
    sys.prefix = sys.exec_prefix = config['dependency_prefix']
    worker = source_module(sources[VALIDATOR], 'fixed_private_coordinator_source_loader')
    sys.meta_path.insert(0, worker['ReferenceSourceFinder'](G,
        {name: item['sha256'] for name, item in sources.items()}, config['dependency_roots']))
    launcher = source_module(sources[PARENT_LAUNCH], 'fixed_private_coordinator_audit')
    output = S / 'source-commit' / cohort.name
    launcher['install_parent_audit']('private-coordinator', source_root=str(G), code_inputs=sources,
        write_roots=[str(output), str(stage), str(cohort / 'source-commit-controls.json')],
        python_paths=[config['python']])
    from tests.utils.native_test_environment import origin_witness
    save(stage / 'origins-before.json', origin_witness(G))
    import socket
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', 0))
        except PermissionError:
            save(stage / 'network.json', {'network_bind_denied': True,
                'scope': 'fixed coordinator Python audit; gate workers retain their own OS sandbox'})
        else:
            raise ValueError('private coordinator network denial did not hold')
    control = source_module(sources[CONTROL], 'fixed_stage_private_controls')
    result = control['prepare_control'](output, trusted_root=G, scratch=S,
        dependency_roots=[Path(config['dependency_roots'][-1])], bounds_path=Path(config['bounds']['path']),
        main_reference_report=pin(Path(config['packet_root']) / 'reference-report.json'),
        timeout_seconds=3600)
    declaration = save(cohort / 'source-commit-controls.json', result)
    save(stage / 'origins-after.json', origin_witness(G))
    save(stage / 'result.json', {'status': 'passed', 'action': 'private-controls', 'role': None,
        'config': inputs['config'], 'outputs': {'source_commit_controls': declaration},
        'side_effects': {'native_executions': 0, 'model_calls': 0, 'probes_executed': 0, 'captures': 0, 'reservations': 0}})
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--cohort', type=Path)
    parser.add_argument('--source-commit')
    parser.add_argument('--stage', choices=STAGES)
    parser.add_argument('--role', choices=ROLES)
    parser.add_argument('--timeout-seconds', type=int, default=3600)
    parser.add_argument('--child-inputs', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--child-sha256', help=argparse.SUPPRESS)
    parser.add_argument('--child-bytes', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.child_inputs is not None:
        return child({'path': str(args.child_inputs), 'sha256': args.child_sha256, 'bytes': args.child_bytes})
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        parser.error('use the physical dependency Python -S -P -B')
    if args.cohort is None or args.source_commit is None or args.stage is None:
        parser.error('cohort, source-commit and one fixed stage are required')
    stage_name(args.stage, args.role)
    if args.stage == 'bootstrap':
        result = bootstrap(args.cohort, args.source_commit)
    else:
        cohort = cohort_path(args.cohort)
        with (cohort / 'orchestrator.lock').open('a+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = run_stage(cohort, args.source_commit, args.stage, args.role, args.timeout_seconds)
    print(json.dumps(result, sort_keys=True))
    return 0 if json.loads(checked(result)).get('status') == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
