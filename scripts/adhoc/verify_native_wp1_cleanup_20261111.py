#!/usr/bin/env python3
"""E1/#5746 real-runner owned-process interruption witnesses, 2026-11-11.

Inputs: frozen native01bd, its completed genuine canary/private composition and
restored exact config. One scenario per invocation: post-admission SIGINT,
driver loss, or unchanged layered deadline after stopping the real sandbox.
Outputs: fresh external provenance plus unchanged full-chain runner evidence.
No toy worker, source edits, network/provider calls, shortened limit or lease.
The 75-second envelope includes a 70-second external cutoff and cleanup.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

TOOLS = Path(__file__).resolve().parents[2]
SOURCE = TOOLS.parent / 'codex-native-u1u3'
SCRATCH = TOOLS.parent / 'scratch-native-u1u3/u3m'
HEAD = '01bdcb22dad66da1a167595251b23e6352c97ab7'
COMPOSITION = SCRATCH / 'composition-01bdcb22dad6'
CONTRACT = SCRATCH / 'wp1-contract-01bdcb22dad6.json'
VALIDATOR = SOURCE / 'scripts/adhoc/native_wp1_validation_20261110.py'
DRIVER = SOURCE / 'scripts/adhoc/run_native_wp1_20261110.py'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_NO_LAZY_FETCH': '1', 'GIT_OPTIONAL_LOCKS': '0',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_CONFIG_GLOBAL': '/dev/null'}
PINS = {
    COMPOSITION / 'composition.json': '0a64114cd9332b1f1b19a0ee4708d13a7f07f6487f020aa9d794c4c699d7a748',
    COMPOSITION / 'config-restored.json': '88e3fcad8d70bf8301acd04d92c7edecab627125cd5447cd3143a32eb6df8520',
    CONTRACT: '1618c957f43048fe7ae7a899ea1f018f9c5cf1e718a4ade891fb254f7a342ace',
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    need(path.resolve(strict=True) == path and stat.S_ISREG(path.lstat().st_mode),
         'physical regular file required: ' + str(path))
    return path.read_bytes()


def write_new(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    need(path.read_bytes() == raw, 'evidence did not persist')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario', choices=('sigint', 'driver-loss', 'deadline'))
    args = parser.parse_args()
    started = time.monotonic()
    final_deadline = started + 75
    child = None
    known, sessions, errors = {}, set(), []
    config = original = configured = config_identity = None
    activated = False
    result = {'scenario': args.scenario, 'source_commit': HEAD, 'limit_seconds': 75,
              'runner_limit_seconds': 60, 'injection': None, 'external_rescue': False,
              'scope': 'Owned-process failure witness only; no acceptance, lease or performance claim.'}

    def git(cwd, *parts):
        remaining = final_deadline - time.monotonic() - 3
        need(remaining > 0, 'external evidence deadline exhausted')
        return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
            '--no-optional-locks', '-c', 'core.hooksPath=/dev/null',
            '-c', 'diff.autoRefreshIndex=false', *parts], cwd=cwd, env=ENV,
            timeout=min(5, remaining))

    def same_process(pid, created):
        try:
            p = psutil.Process(pid)
            if p.create_time() == created and p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                return p
        except psutil.NoSuchProcess:
            return None
        except psutil.Error as exc:
            errors.append('identity:' + type(exc).__name__)
        return None

    def observe():
        for pid, created in tuple(known.items()):
            p = same_process(pid, created)
            if p is None:
                continue
            try:
                for descendant in p.children(recursive=True):
                    known.setdefault(descendant.pid, descendant.create_time())
            except psutil.NoSuchProcess:
                pass
            except psutil.Error as exc:
                errors.append('observe:' + type(exc).__name__)

    def living():
        return [p for pid, created in tuple(known.items())
                if (p := same_process(pid, created)) is not None]

    def rescue():
        # Signal only processes previously observed below our direct child,
        # rechecking creation identity. Never signal a discovered foreign PID.
        result['external_rescue'] = True
        observe()
        for p in reversed(living()):
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
            except psutil.Error as exc:
                errors.append('rescue:' + type(exc).__name__)
        if child is not None and child.poll() is None:
            child.kill()  # unreaped direct Popen handle cannot have been reused

    def stop(number, frame):
        raise TimeoutError('external cleanup witness reached 70-second cutoff')

    def hard_stop(number, frame):
        # Missing terminal evidence is always failure; preserve backups for
        # explicit recovery. All process traversal/rescue belongs to the
        # 70-to-75-second cleanup window, never inside the final handler.
        os._exit(124)

    signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, 70)
    # No helper/project imports before identity/cache isolation.
    need(sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode,
         '-S -P -B required')
    need(not os.path.lexists(TOOLS.parent / 'plans/native_quiet_window.lock'), 'quiet lock exists')
    need(git(SOURCE, 'rev-parse', 'HEAD').decode().strip() == HEAD
         and not git(SOURCE, 'status', '--porcelain').strip(), 'frozen native source differs')
    tool_head = git(TOOLS, 'rev-parse', 'HEAD').decode().strip()
    relative = str(Path(__file__).resolve().relative_to(TOOLS))
    need(not git(TOOLS, 'status', '--porcelain').strip()
         and git(TOOLS, 'show', tool_head + ':' + relative) == Path(__file__).read_bytes(),
         'committed clean tools required')
    for path, digest in PINS.items():
        need(sha(regular(path)) == digest, 'retained identity differs: ' + str(path))
    manifest, contract = json.loads(regular(COMPOSITION / 'composition.json')), json.loads(regular(CONTRACT))
    need(sha(Path(sys.executable).resolve(strict=True).read_bytes()) == contract['interpreter']['sha256']
         and sys.version == contract['interpreter']['version'], 'executing interpreter differs')
    for relative, digest in {**manifest['protected_preimages_sha256'], **contract['implementation_sha256']}.items():
        need(sha(regular(SOURCE / relative)) == digest, 'source bytes differ: ' + relative)
    label = 'e1-cleanup-' + args.scenario + '-' + tool_head[:12]
    out = SCRATCH / ('wp1-01bdcb22dad6-canary-' + label)
    evidence = SCRATCH / ('cleanup-witness-' + label)
    need(not any(os.path.lexists(path) for path in (evidence, out,
         out.with_suffix('.outer.json'), out.with_suffix('.supervisor.json'), out.with_suffix('.outer.log'))),
         'fresh witness and runner paths required')
    evidence.mkdir()
    result.update(tools_commit=tool_head, helper_sha256=sha(Path(__file__).read_bytes()),
        manifest_sha256=PINS[CONTRACT], runner_output=str(out), started_monotonic=started)
    sys.pycache_prefix = str(evidence / 'unused-pycache')
    prefix = Path(sys.executable).absolute().parent.parent
    site = prefix / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    need((prefix / 'pyvenv.cfg').is_file() and site.resolve(strict=True) == site, 'physical dependencies required')
    sys.path.append(str(site))  # no .pth/editable hook execution
    import psutil
    try:
        row = manifest['private_config']
        config = COMPOSITION / 'tree/.git/config'
        need(str(config) == row['path'], 'private config path differs')
        original = regular(config)
        config_identity = config.stat()
        need(sha(original) == row['original_sha256']
             and original == regular(Path(row['backup'])), 'restored config/backup differs')
        backup = evidence / 'config-original.bin'
        with backup.open('xb') as stream:
            stream.write(original)
        candidate = evidence / 'config-configured.bin'
        with candidate.open('xb') as stream:
            stream.write(original)
        git(TOOLS, 'config', '--no-includes', '--file', str(candidate),
            'd4d.ciRepositoryUrl', row['value'])
        configured = candidate.read_bytes()
        need(sha(configured) == row['configured_sha256'], 'exact prior configured bytes required')
        temporary = config.with_name('config.activate-' + label)
        with temporary.open('xb') as stream:
            stream.write(configured)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(config_identity.st_mode))
        need(regular(config) == original and config.stat().st_ino == config_identity.st_ino,
             'private config changed before activation')
        activated = True
        os.replace(temporary, config)
        need(regular(config) == configured, 'configured bytes did not persist')
        result['config_before_sha256'] = sha(original)
        result['config_active_sha256'] = sha(configured)
        command = [sys.executable, '-S', '-P', '-B', str(VALIDATOR), 'canary', '--label', label]
        result['command'] = command
        env = {**ENV, 'U3WP1_MANIFEST': str(CONTRACT)}
        result['environment_keys'] = sorted(env)
        with (evidence / 'runner.log').open('xb') as log:
            child = subprocess.Popen(command, cwd=SOURCE, env=env, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True)
            created = psutil.Process(child.pid).create_time()
            known[child.pid] = created
            sessions.add(child.pid)
            result['outer_identity'] = [child.pid, created]
            while child.poll() is None:
                observe()
                if os.path.lexists(TOOLS.parent / 'plans/native_quiet_window.lock'):
                    raise ValueError('quiet lock appeared')
                network = out / 'network.json'
                if result['injection'] is None and network.is_file():
                    try:
                        record = json.loads(regular(network))
                    except json.JSONDecodeError:
                        time.sleep(0.01)
                        continue
                    need(record.get('network_bind_denied') is True and record.get('errno') == errno.EPERM
                         and type(record.get('pid')) is int,
                         'actual sandbox network denial required')
                    pid = record['pid']
                    need(pid in known, 'sandbox was not observed below owned outer')
                    worker = same_process(pid, known[pid])
                    need(worker is not None, 'sandbox already retired before injection')
                    ancestors = worker.parents()
                    need((child.pid, created) in {(p.pid, p.create_time()) for p in ancestors},
                         'sandbox is not below owned outer')
                    cmd = worker.cmdline()
                    plan = json.loads(regular(out / 'plan.json'))
                    need(cmd == plan['command'][3:] and plan['workers'] == 1
                         and cmd[-1] == 'tests/test_native_u3k_profile.py::test_consumer_observer_equivalence_canary'
                         and str(DRIVER) in cmd and '--worker' in cmd and str(out) in cmd
                         and Path(worker.exe()).resolve(strict=True) == Path(sys.executable).resolve(strict=True)
                         and os.getsid(pid) == pid and os.getpgid(pid) == pid,
                         'genuine admitted detached sandbox worker required')
                    runner_started = float(plan['environment']['U3WP1_STARTED_MONOTONIC'])
                    runner_deadline = float(plan['environment']['U3WP1_HARD_DEADLINE'])
                    need(runner_deadline - runner_started == 60, 'unchanged 60-second runner deadline required')
                    result.update(runner_started_monotonic=runner_started, runner_hard_deadline=runner_deadline)
                    need(not (out / 'pytest.xml').exists() and not (out / 'worker-outcome.json').exists(),
                         'work already completed before injection')
                    inner = [p for p in ancestors if str(VALIDATOR) in p.cmdline() and '--supervised' in p.cmdline()]
                    drivers = [p for p in ancestors if str(DRIVER) in p.cmdline()
                               and '--worker' not in p.cmdline() and '--child-check' not in p.cmdline()]
                    need(len(inner) == len(drivers) == 1, 'unique genuine supervisor and driver required')
                    sessions.update((pid, os.getsid(inner[0].pid)))
                    target = child.pid if args.scenario == 'sigint' else drivers[0].pid if args.scenario == 'driver-loss' else pid
                    need(target in known and same_process(target, known[target]) is not None, 'injection owner lost')
                    injected = signal.SIGINT if args.scenario == 'sigint' else signal.SIGKILL if args.scenario == 'driver-loss' else signal.SIGSTOP
                    result['injection'] = dict(target_pid=target, created=known[target], signal=int(injected),
                        seconds=time.monotonic() - started, sandbox_identity=[pid, known[pid]],
                        sandbox_command=cmd, network_record=record,
                        driver_identity=[drivers[0].pid, drivers[0].create_time()],
                        inner_identity=[inner[0].pid, inner[0].create_time()])
                    write_new(evidence / 'injection.json', result['injection'])
                    injection_target = same_process(target, known[target])
                    need(same_process(pid, known[pid]) is not None
                         and injection_target is not None
                         and not (out / 'pytest.xml').exists() and not (out / 'worker-outcome.json').exists(),
                         'work completed or ownership lost immediately before injection')
                    if args.scenario == 'sigint':
                        child.send_signal(injected)
                    else:
                        # psutil rechecks PID reuse; deadline stops only the real
                        # sandbox leader, leaving all genuine earlier guards live.
                        injection_target.send_signal(injected)
                time.sleep(0.02)
            result['runner_returncode'] = child.wait(timeout=1)
            observe()
            until = min(time.monotonic() + 1, final_deadline - 4)
            while living() and time.monotonic() < until:
                observe()
                time.sleep(0.02)
            result['survivors_before_external_rescue'] = [p.pid for p in living()]
    except BaseException as exc:
        errors.append(type(exc).__name__ + ': ' + str(exc))
    finally:
        signal.signal(signal.SIGALRM, hard_stop)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, final_deadline - time.monotonic()))
        if child is not None:
            observe()
            if child.poll() is None or living():
                rescue()
            try:
                child.wait(timeout=max(0.001, min(1, final_deadline - time.monotonic() - 2)))
            except subprocess.TimeoutExpired:
                errors.append('external_reap_timeout')
        if activated:
            try:
                current = regular(config)
                need(current in (original, configured), 'foreign config bytes preserved; cannot restore')
                if current == configured:
                    temporary = config.with_name('config.restore-' + label)
                    with temporary.open('xb') as stream:
                        stream.write(original)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.chmod(temporary, stat.S_IMODE(config_identity.st_mode))
                    need(regular(config) == configured, 'config changed before restore')
                    os.replace(temporary, config)
                result['config_restored'] = regular(config) == original
                result['config_after_sha256'] = sha(regular(config))
            except BaseException as exc:
                errors.append('restore:' + type(exc).__name__ + ': ' + str(exc))
        result['known_processes'] = sorted(known.items())
        result['observed_surviving_pids'] = [p.pid for p in living()]
        members = []
        for p in psutil.process_iter(['pid', 'create_time', 'status']):
            try:
                if os.getsid(p.pid) in sessions:
                    members.append(p.info)
            except (ProcessLookupError, psutil.NoSuchProcess):
                pass
            except (PermissionError, psutil.AccessDenied):
                errors.append('session_census_denied')
        result['owned_session_members_after'] = members
        supervisor_path = out.with_suffix('.supervisor.json')
        terminal = json.loads(regular(supervisor_path)) if supervisor_path.is_file() else None
        result['supervisor'] = terminal
        inner_path = out.with_suffix('.outer.json')
        result['inner_supervisor'] = json.loads(regular(inner_path)) if inner_path.is_file() else None
        runner_outcome = out / 'outcome.json'
        cutoff_path = out / 'wp1-cutoff.json'
        result['runner_outcome'] = json.loads(regular(runner_outcome)) if runner_outcome.is_file() else None
        result['runner_cutoff'] = json.loads(regular(cutoff_path)) if cutoff_path.is_file() else None
        xml = out / 'pytest.xml'
        result['completed_testcase_race'] = bool(xml.is_file() and list(ET.fromstring(regular(xml)).iter('testcase')))
        result['source_unchanged'] = (git(SOURCE, 'rev-parse', 'HEAD').decode().strip() == HEAD
            and not git(SOURCE, 'status', '--porcelain').strip()
            and all(sha(regular(SOURCE / path)) == digest for path, digest
                    in {**manifest['protected_preimages_sha256'], **contract['implementation_sha256']}.items()))
        result['retained_inputs_unchanged'] = all(sha(regular(path)) == digest for path, digest in PINS.items())
        result['interpreter_unchanged'] = sha(Path(sys.executable).resolve(strict=True).read_bytes()) == contract['interpreter']['sha256']
        result['errors'] = errors
        result['seconds'] = time.monotonic() - started
        result['scenario_verified'] = bool(result['injection'] and terminal is not None
            and terminal['sandbox_handoff']['admitted'] is True and terminal['returncode'] != 0
            and terminal['cleanup_verified'] is False and child.returncode != 0
            and not result['external_rescue'] and not result['observed_surviving_pids'] and not members
            and result.get('config_restored') is True and result['source_unchanged']
            and result['retained_inputs_unchanged'] and result['interpreter_unchanged']
            and not result['completed_testcase_race'] and not errors
            and result['seconds'] <= 75)
        if args.scenario == 'sigint':
            result['scenario_verified'] &= bool(terminal and terminal['interrupted'] == 'external_signal_2')
        if args.scenario == 'driver-loss':
            inner = result['inner_supervisor'] or {}
            injected = result['injection'] or {}
            result['driver_sigkill_observed'] = bool(inner.get('child_returncode') == -signal.SIGKILL
                and injected.get('driver_identity') in inner.get('observed_processes', [])
                and str(DRIVER) in inner.get('command', []) and str(out) in inner.get('command', []))
            result['scenario_verified'] &= result['driver_sigkill_observed']
        if args.scenario == 'deadline':
            result['deadline_claim'] = 'Unchanged layered 60-second deadline only; no hard-alarm coverage inferred.'
            deadline_observed = ((result['runner_outcome'] or {}).get('interrupted') == 'deadline'
                or any(event.get('reason') == 'sandbox_hard_cutoff'
                       for event in (result['runner_cutoff'] or {}).get('events', []))
                or (terminal or {}).get('interrupted') == 'outer_deadline')
            result['deadline_evidence_observed'] = deadline_observed
            result['scenario_verified'] &= bool(deadline_observed and time.monotonic()
                >= result.get('runner_hard_deadline', float('inf')) - 10)
        write_new(evidence / 'result.json', result)
        signal.setitimer(signal.ITIMER_REAL, 0)
    print(str(evidence / 'result.json') + ' sha256=' + sha((evidence / 'result.json').read_bytes()))
    return 0 if result['scenario_verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
