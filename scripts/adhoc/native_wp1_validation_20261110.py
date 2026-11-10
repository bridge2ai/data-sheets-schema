#!/usr/bin/env python3
"""WP1 bounded observer experiment; implementation-only delivery, 2026-11-10.

Inputs: a separately prepared fresh U3WP1_MANIFEST, physical dependency Python
(-S -P -B), one fixed canary/arm and a fresh label. Outputs: one offline evidence
directory plus outer supervisor evidence. Never prepares a composition, exports
dependencies or installs an environment itself. The inherited driver creates its
isolated test prefix only when a later explicit execution is authorized.

The closed manifest has kind=native_wp1_measurement, version=1, source_commit,
composition_manifest, composition_manifest_sha256, implementation_sha256 and
interpreter={path,sha256,version}. It belongs at u3m/wp1-contract-<source12>.json;
the referenced fresh M composition must cover that same newly committed source.
This identity envelope conveys no packet, launch or production acceptance.

Measured arms remain blocked pending a separately reviewed verified-owned
quiet-window adapter. The inherited M/C/A refusal of any existing lock is kept;
absence of a foreign lock is not falsely described as an owned quiet window.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import select
import secrets
import signal
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3/u3m'
CANARY = 'tests/test_native_u3k_profile.py::test_consumer_observer_equivalence_canary'
DIAGNOSTIC = 'tests/test_native_u3k_profile.py::test_neutral_pre_reservation_diagnostic'
KINDS = {'canary': (CANARY, 'legacy', 60),
         'legacy': (DIAGNOSTIC, 'legacy', 900),
         'monitoring': (DIAGNOSTIC, 'monitoring', 900)}
REQUIRED_FILES = frozenset({
    'tests/utils/native_shared_consumer_scope.py', 'tests/test_native_u3k_profile.py',
    'tests/utils/native_consumer_observer_checks.py',
    'tests/utils/native_profile_stability.py',
    'scripts/adhoc/native_wp1_validation_20261110.py',
    'scripts/adhoc/run_native_wp1_20261110.py',
    'scripts/adhoc/native_wp1_child_gate_20261110.py',
    'scripts/adhoc/run_native_u3m_20261109.py',
    'scripts/adhoc/u3m_metrics_plugin_20261109.py',
    'scripts/adhoc/u3k_metrics_plugin_20261109.py',
    'scripts/adhoc/run_native_u3h_20261109.py',
    'scripts/adhoc/run_native_u3g_20261109.py',
    'scripts/adhoc/run_native_u3f_20261109.py',
    'scripts/adhoc/run_native_u1u3_20261108.py',
    'scripts/adhoc/run_native_u3d_round9_20261107.py',
    'scripts/adhoc/run_native_u3c_round4_20261107.py',
    'scripts/adhoc/run_native_u3a_tests_20261107.py',
    'scripts/adhoc/hydrate_native_u3c_round4_fairscape_20261107.py',
    'tests/utils/native_test_environment.py',
})
GIT_ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
           'GIT_ALLOW_PROTOCOL': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
           'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physical(path):
    if not path.is_absolute() or path != path.resolve(strict=True) or not path.is_file():
        raise ValueError('physical absolute file required: ' + str(path))
    return path


def git(*args, cwd=ROOT):
    remaining = float(os.environ.get('U3WP1_HARD_DEADLINE', time.monotonic() + 10)) - time.monotonic() - 3
    if remaining <= 0:
        raise TimeoutError('WP1 preflight deadline exhausted')
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd, env=GIT_ENV, timeout=min(10, remaining))


def contract():
    """Read and bind a new source/composition contract; never create one."""
    path = physical(Path(os.environ['U3WP1_MANIFEST']))
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    expected = os.environ.get('U3WP1_MANIFEST_SHA', digest)
    if expected != digest:
        raise ValueError('WP1 manifest differs from the parent identity')
    value = json.loads(raw)
    required = {'kind', 'version', 'source_commit', 'composition_manifest',
                'composition_manifest_sha256', 'implementation_sha256', 'interpreter'}
    if set(value) != required or value['kind'] != 'native_wp1_measurement' or value['version'] != 1:
        raise ValueError('closed WP1 manifest required')
    head = value['source_commit']
    if not isinstance(head, str) or not re.fullmatch('[0-9a-f]{40}', head):
        raise ValueError('full WP1 source commit required')
    if path != SCRATCH / ('wp1-contract-' + head[:12] + '.json'):
        raise ValueError('WP1 manifest path does not name the fresh source')
    if git('rev-parse', 'HEAD').decode().strip() != head or git(
            'status', '--porcelain', '--untracked-files=normal').strip():
        raise ValueError('WP1 source must be frozen, committed and clean')
    composition_path = physical(Path(value['composition_manifest']))
    if composition_path != SCRATCH / ('composition-' + head[:12]) / 'composition.json':
        raise ValueError('fresh composition for this WP1 source is required')
    if sha(composition_path) != value['composition_manifest_sha256']:
        raise ValueError('WP1 composition manifest bytes differ')
    composition = json.loads(composition_path.read_bytes())
    if (composition['source_commit'] != head
            or composition['kind'] != 'native_u3m_private_composition'
            or composition['status'] != 'composed_not_tested'):
        raise ValueError('WP1 cannot borrow an interim or baseline composition')
    tree = Path(composition['worktree'])
    if tree != tree.resolve(strict=True):
        raise ValueError('physical WP1 composition worktree required')
    pins = value['implementation_sha256']
    if set(pins) != REQUIRED_FILES:
        raise ValueError('WP1 implementation closure differs')
    for relative, pin in pins.items():
        if (not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin)
                or sha(physical(ROOT / relative)) != pin
                or sha(physical(tree / relative)) != pin
                or hashlib.sha256(git('show', head + ':' + relative)).hexdigest() != pin):
            raise ValueError('WP1 implementation bytes differ: ' + relative)
    interpreter = value['interpreter']
    if set(interpreter) != {'path', 'sha256', 'version'}:
        raise ValueError('closed interpreter identity required')
    executable = Path(sys.executable).resolve(strict=True)
    if (str(executable) != interpreter['path'] or sha(executable) != interpreter['sha256']
            or sys.version != interpreter['version'] or not hasattr(sys, 'monitoring')):
        raise ValueError('WP1 interpreter identity or monitoring capability differs')
    return path, digest, value


def write_new(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        raise RuntimeError('WP1 evidence did not persist exactly')


def require_canary(path, manifest_sha):
    """A terminal, exact-identity canary is mandatory before either arm."""
    if path != path.resolve(strict=True) or path.parent != SCRATCH:
        raise ValueError('physical same-scratch canary evidence required')
    outer = json.loads(physical(path.with_suffix('.outer.json')).read_bytes())
    supervisor = json.loads(physical(path.with_suffix('.supervisor.json')).read_bytes())
    outcome = json.loads(physical(path / 'outcome.json').read_bytes())
    driver = json.loads(physical(path / 'wp1-harness.json').read_bytes())
    xml = ET.parse(physical(path / 'pytest.xml')).getroot()
    cases = list(xml.iter('testcase'))
    if (outer['kind'] != 'canary' or outer['manifest_sha256'] != manifest_sha
            or outer['returncode'] != 0 or outer['timed_out'] or not outer['cleanup_verified']
            or not outcome['cleanup_verified'] or outcome['returncode'] != 0
            or driver['manifest_sha256'] != manifest_sha or driver['node'] != CANARY
            or driver['kind'] != 'canary' or not driver['source_unchanged']
            or supervisor['kind'] != 'canary' or supervisor['manifest_sha256'] != manifest_sha
            or supervisor['returncode'] != 0 or not supervisor['cleanup_verified']
            or supervisor['forced_cleanup'] or not supervisor['sandbox_handoff']['admitted']
            or len(cases) != 1 or cases[0].get('name') != CANARY.split('::')[1]
            or any(list(case.iter(tag)) for case in cases for tag in ('failure', 'error', 'skipped'))):
        raise ValueError('WP1 canary is not a certified one-test pass on this identity')


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=tuple(KINDS))
    parser.add_argument('--label', required=True)
    parser.add_argument('--canary-out', type=Path)
    parser.add_argument('--supervised', action='store_true', help=argparse.SUPPRESS)
    return parser.parse_args()


class _SandboxHandoff:
    """One private pipe handoff; retain ownership independently of the driver."""
    def __init__(self, psutil):
        self.psutil = psutil
        self.ready_read, self.ready_write = os.pipe()
        self.release_read, self.release_write = os.pipe()
        os.set_blocking(self.ready_read, False)
        self.nonce = secrets.token_hex(32)
        self.buffer = b''
        self.supervisor = None
        self.group = None
        self.known = {}
        self.admitted = False
        self.cancelled = False
        self.errors = []

    def attach(self, child):
        self.supervisor = (child.pid, self.psutil.Process(child.pid).create_time())
        for name in ('ready_write', 'release_read'):
            os.close(getattr(self, name))
            setattr(self, name, -1)

    def close_release(self):
        self.cancelled = True
        if self.release_write >= 0:
            os.close(self.release_write)
            self.release_write = -1

    def poll(self, *, allow_release=True):
        if self.ready_read >= 0 and select.select([self.ready_read], [], [], 0)[0]:
            chunk = os.read(self.ready_read, 4096)
            self.buffer += chunk
            if len(self.buffer) > 2048:
                raise ValueError('oversized WP1 sandbox ownership message')
            if b'\n' in self.buffer:
                if self.group is not None or self.buffer.count(b'\n') != 1 or not self.buffer.endswith(b'\n'):
                    raise ValueError('WP1 accepts exactly one sandbox handoff')
                value = json.loads(self.buffer)
                if (set(value) != {'kind', 'nonce', 'pid', 'ppid', 'pgid', 'sid'}
                        or value['kind'] != 'wp1_sandbox_ready' or value['nonce'] != self.nonce
                        or any(type(value[key]) is not int or value[key] <= 1
                               for key in ('pid', 'ppid', 'pgid', 'sid'))
                        or value['pid'] != value['pgid'] or value['pid'] != value['sid']):
                    raise ValueError('WP1 sandbox ownership message differs')
                process = self.psutil.Process(value['pid'])
                parents = {(parent.pid, parent.create_time()) for parent in process.parents()}
                if (self.supervisor not in parents or process.ppid() != value['ppid']
                        or os.getpgid(process.pid) != process.pid or os.getsid(process.pid) != process.pid
                        or Path(process.exe()).resolve(strict=True) != Path(sys.executable).resolve(strict=True)):
                    raise ValueError('WP1 handoff is not this supervisor\'s detached Python child')
                # Ownership is frozen BEFORE releasing any sandbox/test code.
                self.group = process.pid
                self.known[process.pid] = process.create_time()
                os.close(self.ready_read)
                self.ready_read = -1
                if allow_release and not self.cancelled:
                    ack = (self.nonce + '\n').encode()
                    if os.write(self.release_write, ack) != len(ack):
                        raise RuntimeError('WP1 sandbox ACK was incomplete')
                    self.admitted = True
                self.close_release()
            elif not chunk:
                os.close(self.ready_read)
                self.ready_read = -1
        self.observe()

    def live(self):
        result = []
        for pid, created in tuple(self.known.items()):
            try:
                process = self.psutil.Process(pid)
                if process.create_time() == created and process.is_running() and process.status() != self.psutil.STATUS_ZOMBIE:
                    result.append(process)
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.Error as exc:
                self.errors.append(type(exc).__name__)
        return result

    def observe(self):
        for process in self.live():
            try:
                for child in process.children(recursive=True):
                    self.known[child.pid] = child.create_time()
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.Error as exc:
                self.errors.append(type(exc).__name__)

    def kill_detached(self):
        """Signal a session only with a still-matching owned creation identity."""
        self.close_release()  # Unacknowledged gates see EOF and never exec tests.
        live = self.live()
        for process in live:
            try:
                if (self.group is not None and os.getpgid(process.pid) == self.group
                        and os.getsid(process.pid) == self.group):
                    os.killpg(self.group, signal.SIGKILL)
                    break
            except ProcessLookupError:
                pass
        for process in reversed(self.live()):
            try:
                process.kill()
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.Error as exc:
                self.errors.append(type(exc).__name__)

    def close(self):
        self.close_release()
        for name in ('ready_read', 'ready_write', 'release_read'):
            fd = getattr(self, name)
            if fd >= 0:
                os.close(fd)
                setattr(self, name, -1)

    def witness(self):
        survivors = [process.pid for process in self.live()]
        return dict(admitted=self.admitted, session_id=self.group,
            known_processes=sorted(self.known.items()), errors=list(self.errors),
            observed_surviving_pids=survivors,
            scope='Inherited pipes; PID/creation and ancestry checked before ACK. Never-observed escaped descendants are not certified.')


def supervised_main(args):
    node, arm, limit = KINDS[args.kind]
    if args.kind != 'canary':
        raise RuntimeError('WP1 measured arms blocked: verified-owned quiet-window adapter not implemented')
    started = float(os.environ['U3WP1_STARTED_MONOTONIC'])
    deadline = float(os.environ['U3WP1_HARD_DEADLINE'])
    if (int(os.environ['U3WP1_SUPERVISOR_PID']) != os.getppid()
            or deadline - started != limit or not started <= time.monotonic() < deadline):
        raise ValueError('WP1 preflight requires its live bounded outer supervisor')
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError('invoke WP1 with physical dependency Python -S -P -B')
    if not re.fullmatch('[a-zA-Z0-9_-]+', args.label):
        raise ValueError('literal WP1 label required')
    manifest, manifest_sha, value = contract()
    if args.kind == 'canary' and args.canary_out is not None:
        raise ValueError('canary cannot borrow prior canary evidence')
    if args.kind != 'canary':
        if args.canary_out is None:
            raise ValueError('both arms require --canary-out')
        require_canary(args.canary_out, manifest_sha)
    out = SCRATCH / ('wp1-' + value['source_commit'][:12] + '-' + args.kind + '-' + args.label)
    if any(os.path.lexists(path) for path in (out, out.with_suffix('.outer.json'), out.with_suffix('.outer.log'))):
        raise ValueError('WP1 evidence label is already occupied')
    lock = ROOT.parent / 'plans/native_quiet_window.lock'
    if os.path.lexists(lock):
        raise ValueError('quiet window is active; WP1 does not bypass its owner')
    prefix = Path(sys.executable).absolute().parent.parent
    dependencies = prefix / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    if not (prefix / 'pyvenv.cfg').is_file() or dependencies != dependencies.resolve(strict=True):
        raise ValueError('physical installed dependency prefix required')
    sys.path.append(str(dependencies))  # No site.addsitedir, .pth or editable hook.
    import psutil
    env = {**GIT_ENV, 'PATH': str(Path(sys.executable).parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
           'LANG': 'en_US.UTF-8', 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1',
           'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
           'PYTEST_ADDOPTS': '', 'UV_OFFLINE': '1', 'PIP_NO_INDEX': '1',
           'U3WP1_MANIFEST': str(manifest), 'U3WP1_MANIFEST_SHA': manifest_sha,
           'U3WP1_KIND': args.kind, 'U3WP1_CONSUMER_ARM': arm,
           'U3WP1_STARTED_MONOTONIC': repr(started), 'U3WP1_HARD_DEADLINE': repr(deadline),
           'U3WP1_READY_FD': os.environ['U3WP1_READY_FD'],
           'U3WP1_RELEASE_FD': os.environ['U3WP1_RELEASE_FD'],
           'U3WP1_HANDOFF_NONCE': os.environ['U3WP1_HANDOFF_NONCE'],
           'U3K_PROFILE': 'control'}
    handoff_fds = (int(env['U3WP1_READY_FD']), int(env['U3WP1_RELEASE_FD']))
    command = [sys.executable, '-S', '-P', '-B',
               str(ROOT / 'scripts/adhoc/run_native_wp1_20261110.py'),
               '--out', str(out), '--workers', '1', node]
    known = {}
    errors = []
    state_lock = threading.Lock()
    stop = threading.Event()
    child = None
    observer = None
    observer_joined = True
    post_observer_cleanup_pids = []
    interrupted = None
    timed_out = False

    def observe():
        while not stop.wait(0.1):
            with state_lock:
                snapshot = tuple(known.items())
            for pid, created in snapshot:
                try:
                    process = psutil.Process(pid)
                    if process.create_time() == created:
                        for descendant in process.children(recursive=True):
                            created_child = descendant.create_time()
                            with state_lock:
                                known[descendant.pid] = created_child
                except psutil.NoSuchProcess:
                    pass
                except psutil.Error as exc:
                    with state_lock:
                        errors.append(type(exc).__name__)

    def live():
        result = []
        with state_lock:
            snapshot = tuple(known.items())
        for pid, created in snapshot:
            try:
                process = psutil.Process(pid)
                if process.create_time() == created and process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                    result.append(process)
            except psutil.NoSuchProcess:
                pass
            except psutil.Error as exc:
                with state_lock:
                    errors.append(type(exc).__name__)
        return result

    def kill_owned():
        for process in reversed(live()):
            if time.monotonic() >= deadline:
                with state_lock:
                    errors.append('owned_cleanup_deadline_exhausted')
                return
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass
            except psutil.Error as exc:
                with state_lock:
                    errors.append(type(exc).__name__)

    with out.with_suffix('.outer.log').open('xb') as log:
        try:
            remaining = deadline - 3 - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, limit)
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=False,
                                     pass_fds=handoff_fds)
            for fd in handoff_fds:
                os.close(fd)
            handoff_fds = ()
            created_child = psutil.Process(child.pid).create_time()
            with state_lock:
                known[child.pid] = created_child
            observer = threading.Thread(target=observe, daemon=True)
            observer.start()
            child.wait(timeout=max(0, deadline - 3 - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
            interrupted = 'outer_deadline'
            kill_owned()
        except BaseException as exc:
            interrupted = type(exc).__name__
            kill_owned()
        finally:
            for fd in handoff_fds:
                os.close(fd)
            handoff_fds = ()
            # Retain the direct handle even if create_time()/observer startup
            # failed before it could enter the observed PID/creation-time map.
            if child is not None and child.poll() is None:
                child.kill()
            survivors_before_cleanup = [process.pid for process in live()]
            if survivors_before_cleanup:
                kill_owned()
            stop.set()
            if observer is not None:
                observer.join(timeout=max(0, min(0.5, deadline - 1 - time.monotonic())))
                observer_joined = not observer.is_alive()
                if not observer_joined:
                    with state_lock:
                        errors.append('outer_observer_not_joined')
            # An in-flight observation may have discovered another child after
            # the first kill snapshot. Once joined, the known set is frozen;
            # kill its remaining members before the final survivor sample.
            # An unjoined observer remains uncertified even if this pass is empty.
            post_observer_cleanup_pids = [process.pid for process in live()]
            if post_observer_cleanup_pids:
                kill_owned()
            if child is not None:
                try:
                    child.wait(timeout=max(0, min(0.5, deadline - 1 - time.monotonic())))
                except subprocess.TimeoutExpired:
                    with state_lock:
                        errors.append('outer_reap_timeout')
    survivors = [process.pid for process in live()]
    with state_lock:
        known_snapshot = sorted(known.items())
        errors_snapshot = list(errors)
    elapsed = time.monotonic() - started
    outcome_path = out / 'outcome.json'
    outcome = json.loads(outcome_path.read_bytes()) if outcome_path.is_file() else None
    certified = (child is not None and child.returncode == 0 and interrupted is None
                 and observer_joined and not post_observer_cleanup_pids
                 and not survivors_before_cleanup and not survivors and not errors_snapshot
                 and elapsed <= limit and outcome is not None and outcome.get('cleanup_verified') is True)
    code = 124 if timed_out else (0 if certified else 125)
    write_new(out.with_suffix('.outer.json'), dict(kind=args.kind, arm=arm, node=node,
        manifest=str(manifest), manifest_sha256=manifest_sha, source_commit=value['source_commit'],
        command=command, seconds=elapsed, limit_seconds=limit, returncode=code,
        child_returncode=None if child is None else child.returncode, timed_out=timed_out,
        interrupted=interrupted, cleanup_verified=certified, observed_surviving_pids=survivors,
        forced_cleanup=bool(survivors_before_cleanup or post_observer_cleanup_pids or interrupted),
        observation_errors=errors_snapshot, observer_joined=observer_joined,
        post_observer_cleanup_pids=post_observer_cleanup_pids,
        observed_processes=known_snapshot,
        scope='Offline WP1 only; post-deadline cleanup time is reported, never accepted as an in-limit pass.'))
    return code


def main():
    args = arguments()
    if args.supervised:
        return supervised_main(args)
    if args.kind != 'canary':
        raise RuntimeError('WP1 measured arms blocked: verified-owned quiet-window adapter not implemented')
    # Arm the hard cap BEFORE any preflight. The outer owner, independent of
    # the driver/watchdog, admits one detached sandbox through inherited pipes.
    _, _, limit = KINDS[args.kind]
    started = time.monotonic()
    deadline = started + limit
    child = None
    handoff = None
    previous = {number: signal.getsignal(number)
                for number in (signal.SIGALRM, signal.SIGINT, signal.SIGTERM)}
    forced = False
    interrupted = None
    errors = []
    code = 125
    out = None

    class OuterInterrupted(BaseException):
        def __init__(self, number):
            self.number = number

    def external_stop(number, frame):
        raise OuterInterrupted(number)

    def kill_supervisor():
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def hard_stop(number, frame):
        # Detached sandbox ownership survives loss of the inner driver/tracker.
        # Close the release pipe first: a not-yet-admitted gate cannot exec tests.
        try:
            if handoff is not None:
                handoff.kill_detached()
        finally:
            try:
                kill_supervisor()
            finally:
                # No new grace, wait or evidence write extends the hard cap.
                os._exit(124)

    signal.signal(signal.SIGALRM, hard_stop)
    signal.signal(signal.SIGINT, external_stop)
    signal.signal(signal.SIGTERM, external_stop)
    signal.setitimer(signal.ITIMER_REAL, limit)
    try:
        if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
            raise ValueError('WP1 outer requires physical dependency Python -S -P -B')
        if not re.fullmatch('[a-zA-Z0-9_-]+', args.label):
            raise ValueError('literal WP1 output label required')
        manifest = Path(os.environ['U3WP1_MANIFEST'])
        match = re.fullmatch('wp1-contract-([0-9a-f]{12})\\.json', manifest.name)
        if not match:
            raise ValueError('fresh WP1 contract filename required')
        out = SCRATCH / ('wp1-' + match[1] + '-' + args.kind + '-' + args.label)
        if os.path.lexists(out.with_suffix('.supervisor.json')):
            raise ValueError('WP1 outer evidence label already exists')
        prefix = Path(sys.executable).absolute().parent.parent
        site = prefix / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
        if not (prefix / 'pyvenv.cfg').is_file() or site != site.resolve(strict=True):
            raise ValueError('physical installed dependency site required')
        sys.path.append(str(site))  # Never evaluate .pth or editable hooks.
        import psutil
        handoff = _SandboxHandoff(psutil)
        env = {**GIT_ENV, 'LANG': 'en_US.UTF-8', 'PYTHONNOUSERSITE': '1',
               'PYTHONSAFEPATH': '1', 'PYTHONDONTWRITEBYTECODE': '1',
               'U3WP1_MANIFEST': str(manifest), 'U3WP1_SUPERVISOR_PID': str(os.getpid()),
               'U3WP1_STARTED_MONOTONIC': repr(started), 'U3WP1_HARD_DEADLINE': repr(deadline),
               'U3WP1_READY_FD': str(handoff.ready_write),
               'U3WP1_RELEASE_FD': str(handoff.release_read),
               'U3WP1_HANDOFF_NONCE': handoff.nonce}
        command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()),
                   '--supervised', args.kind, '--label', args.label]
        if args.canary_out is not None:
            command += ['--canary-out', str(args.canary_out)]
        child = subprocess.Popen(command, cwd=ROOT, env=env, start_new_session=True,
            pass_fds=(handoff.ready_write, handoff.release_read))
        handoff.attach(child)
        while child.poll() is None:
            handoff.poll()
            if time.monotonic() >= deadline - 2:
                raise subprocess.TimeoutExpired(command, limit)
            time.sleep(min(0.05, max(0, deadline - 2 - time.monotonic())))
        handoff.poll(allow_release=False)
        code = child.returncode
    except OuterInterrupted as exc:
        interrupted = 'external_signal_' + str(exc.number)
        forced = True
    except subprocess.TimeoutExpired:
        interrupted = 'outer_deadline'
        forced = True
    except BaseException as exc:
        interrupted = type(exc).__name__
        errors.append(str(exc))
        forced = True
    finally:
        # Prevent a second external signal from aborting cleanup. SIGALRM stays
        # armed and independently kills verified detached owners at the same cap.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if handoff is not None:
            handoff.close_release()
        try:
            if forced and child is not None and child.poll() is None:
                child.send_signal(signal.SIGINT)
                until = min(time.monotonic() + 1, deadline - 0.25)
                while child.poll() is None and time.monotonic() < until:
                    if handoff is not None:
                        handoff.poll(allow_release=False)
                    time.sleep(min(0.05, max(0, until - time.monotonic())))
        except BaseException as exc:
            errors.append('graceful_cleanup:' + type(exc).__name__)
            forced = True
        ownership = {'admitted': False, 'errors': ['ownership_not_initialized'],
                     'observed_surviving_pids': []}
        try:
            if handoff is not None:
                if handoff.live():
                    forced = True
                    handoff.kill_detached()
                ownership = handoff.witness()
        except BaseException as exc:
            errors.append('detached_cleanup:' + type(exc).__name__)
            forced = True
        finally:
            # Detached owners are handled FIRST, even if the inner driver has
            # refused or hung. Killing its watchdog cannot remove outer ownership.
            if child is not None and child.poll() is None:
                forced = True
                kill_supervisor()
            if handoff is not None:
                handoff.close()
        try:
            inner_path = None if out is None else out.with_suffix('.outer.json')
            inner = json.loads(inner_path.read_bytes()) if inner_path is not None and inner_path.is_file() else None
            certified = (not forced and interrupted is None and code == 0 and not errors
                and ownership['admitted'] and not ownership['errors']
                and not ownership['observed_surviving_pids']
                and inner is not None and inner['returncode'] == 0 and inner['cleanup_verified']
                and time.monotonic() < deadline)
            result = 0 if certified else (124 if interrupted == 'outer_deadline' else 125)
            if out is not None:
                write_new(out.with_suffix('.supervisor.json'), dict(kind=args.kind,
                    manifest=str(manifest), manifest_sha256=sha(manifest),
                    returncode=result, cleanup_verified=certified, forced_cleanup=forced,
                    interrupted=interrupted, errors=errors, sandbox_handoff=ownership,
                    seconds=time.monotonic() - started, limit_seconds=limit,
                    scope='Outer ownership survives inner interruption. Hard exit or missing witness is uncertified.'))
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            for number, handler in previous.items():
                signal.signal(number, handler)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
