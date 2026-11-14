#!/usr/bin/env python3
"""WP1-only quiet-host qualification, 2026-11-10; source delivery, not a run.

Inputs: an owned lease, fresh external output, physical dependency Python and
an absolute deadline at most 150 s away. Outputs: sample/decision/cleanup JSON.
No native, provider, production or historical helper is imported or executed.
The observer is a separate read-only process outside the test OS sandbox.

Copied algorithms, with bounded WP1 ownership/deadline integration, from
codex-native-u0-diag-20261106/scripts/adhoc/:
 native_u0_host_observer_20261106.py
   sha256 ba6376b3d441a7c689bc9ffc787396c22ad3c4985f50cc466e1a6bd6827e4812
 native_recorder_measure_20261026.py (HostSampleReader/idle_decision)
   sha256 61055630897be67f1758437b7569d1f7a5a55fde16c24f68721de280cfa47039
 native_u0_run_20261106.py (normal observer stop/terminal proof)
   sha256 e660b35a54a568b7bd6296d0cafdfd2b40b36d311d82894ff44b0712d019c863
The 60 s settling, 60 fresh observations over >=60 s, 15/35/0.5/5 thresholds,
sample identity/freshness and normal-terminal cleanup requirements are retained.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

SETTLING_SECONDS = 60
SAMPLE_COUNT = 60
QUALIFICATION_SECONDS = 150
CLEANUP_RESERVE = 12
PS_COMMAND = ['/bin/ps', '-A', '-o', 'pid=,ppid=,pcpu=,comm=']
LOAD_COMMAND = ['/usr/sbin/sysctl', '-n', 'vm.loadavg']
CPU_COMMAND = ['/usr/sbin/sysctl', '-n', 'hw.logicalcpu']
THRESHOLDS = {'mean_cpu_percent': 15, 'peak_cpu_percent': 35,
              'one_minute_load_per_cpu': 0.5, 'foreign_process_cpu_percent': 5}


class QualificationError(RuntimeError):
    def __init__(self, message, evidence):
        super().__init__(message)
        self.evidence = evidence


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if Path(path).read_bytes() != raw:
        raise RuntimeError('qualification evidence did not persist exactly')


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _sample(row):
    if (not isinstance(row, dict) or row.get('kind') != 'sample'
            or type(row.get('observer_pid')) is not int or row['observer_pid'] <= 0
            or type(row.get('sequence')) is not int or row['sequence'] < 1
            or not _number(row.get('monotonic'))
            or type(row.get('logical_cpus')) is not int or row['logical_cpus'] <= 0
            or not _number(row.get('cpu_percent')) or row['cpu_percent'] > 100
            or not isinstance(row.get('load'), list) or len(row['load']) != 3
            or not all(_number(value) for value in row['load'])):
        raise ValueError('host CPU/load sample is malformed')
    timestamp = datetime.fromisoformat(row['at'])
    if timestamp.tzinfo is None:
        raise ValueError('host sample timestamp requires a timezone')
    processes = row.get('processes')
    if not isinstance(processes, list) or not processes:
        raise ValueError('host process sample must be nonempty')
    pids = set()
    for process in processes:
        if (not isinstance(process, dict) or type(process.get('pid')) is not int
                or process['pid'] < 0 or process['pid'] in pids
                or type(process.get('ppid')) is not int or process['ppid'] < 0
                or not _number(process.get('cpu_percent'))
                or not isinstance(process.get('name'), str) or not process['name'].strip()):
            raise ValueError('host process row is malformed')
        pids.add(process['pid'])
    if row['observer_pid'] not in pids or 1 not in pids:
        raise ValueError('host table omits observer or launchd')
    return timestamp


def evaluate_samples(samples, *, owned_roots, elapsed_seconds):
    """Pure fixture seam; malformed/incomplete evidence raises, busy returns idle=False.

    Input rows retain the observer's schema. Freshness/file identity is checked
    separately by HostSampleReader at consumption. No clock, sampler or sleep
    is used here; elapsed_seconds is an explicit measured gate duration.
    """
    if (not isinstance(samples, list) or len(samples) < SAMPLE_COUNT
            or not _number(elapsed_seconds) or elapsed_seconds < SAMPLE_COUNT):
        raise ValueError('qualification requires >=60 observations over >=60 seconds')
    roots = set(owned_roots)
    if not roots or any(type(pid) is not int or pid <= 0 for pid in roots):
        raise ValueError('qualification requires validated positive owned root PIDs')
    prior_sequence, prior_time, observer = 0, -1, None
    competitors = []
    for row in samples:
        _sample(row)
        observer = row['observer_pid'] if observer is None else observer
        if (row['observer_pid'] != observer or row['sequence'] <= prior_sequence
                or row['monotonic'] <= prior_time):
            raise ValueError('qualification samples repeat, reorder or change observer')
        prior_sequence, prior_time = row['sequence'], row['monotonic']
        owned = set(roots)
        while True:
            expanded = owned | {p['pid'] for p in row['processes'] if p['ppid'] in owned}
            if expanded == owned:
                break
            owned = expanded
        foreign = [p for p in row['processes']
                   if p['pid'] not in owned and p['cpu_percent'] >= 5]
        if foreign:
            competitors.append({'at': row['at'], 'processes': foreign})
    mean = sum(row['cpu_percent'] for row in samples) / len(samples)
    peak = max(row['cpu_percent'] for row in samples)
    load = max(row['load'][0] / row['logical_cpus'] for row in samples)
    return {'idle': mean <= 15 and peak <= 35 and load <= 0.5 and not competitors,
            'samples': len(samples), 'elapsed_seconds': elapsed_seconds,
            'mean_cpu_percent': mean, 'peak_cpu_percent': peak,
            'max_one_minute_load_per_cpu': load,
            'competing_process_observations': competitors, 'thresholds': dict(THRESHOLDS),
            'scope': 'Declared sampled host-idleness gate; not proof of absence of every competitor.'}


class HostSampleReader:
    MAX_READ = 8 * 1024 * 1024
    MAX_LINE = 2 * 1024 * 1024
    MAX_AGE = 5.0

    def __init__(self, path, observer_pid):
        self.minimum_monotonic = time.monotonic()
        self.path, self.observer_pid = Path(path), observer_pid
        self.fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        state = os.fstat(self.fd)
        if not stat.S_ISREG(state.st_mode):
            os.close(self.fd)
            raise ValueError('host samples must be a regular file')
        self.identity = (state.st_dev, state.st_ino)
        self.offset, self.pending, self.sequence, self.delivered = 0, b'', 0, 0
        self.last_monotonic, self.metadata = None, None

    def close(self):
        os.close(self.fd)

    def _state(self):
        state = self.path.lstat()
        if (not stat.S_ISREG(state.st_mode)
                or (state.st_dev, state.st_ino) != self.identity or state.st_size < self.offset):
            raise ValueError('host sample inode/type changed or file truncated')
        return state

    def sample(self, *, lease, deadline):
        until = min(deadline, time.monotonic() + self.MAX_AGE)
        consumed = 0
        while True:
            lease.validate()
            available = self._state().st_size - self.offset
            if available < 0 or consumed + available > self.MAX_READ:
                raise ValueError('host observation read exceeds bounded byte budget')
            raw = os.read(self.fd, available) if available else b''
            consumed += len(raw)
            self.offset += len(raw)
            self._state()
            lines = (self.pending + raw).split(b'\n')
            self.pending = lines.pop()
            if any(len(line) > self.MAX_LINE for line in [*lines, self.pending]):
                raise ValueError('host observation line exceeds bounded byte budget')
            latest = None
            for line in lines:
                row = json.loads(line)
                if not isinstance(row, dict) or row.get('observer_pid') != self.observer_pid:
                    raise ValueError('host observation has wrong observer identity')
                if self.metadata is None:
                    if row.get('kind') != 'observer_start' or row.get('ps_sha256') != _hash('/bin/ps'):
                        raise ValueError('host observation lacks the pinned startup witness')
                    self.metadata = line + b'\n'
                    continue
                timestamp = _sample(row)
                if (timestamp > datetime.now(timezone.utc) or row['sequence'] != self.sequence + 1
                        or self.last_monotonic is not None and row['monotonic'] <= self.last_monotonic):
                    raise ValueError('host sample timestamp or sequence is invalid')
                self.sequence, self.last_monotonic = row['sequence'], row['monotonic']
                latest = row
            now = time.monotonic()
            if latest is not None and latest['monotonic'] >= self.minimum_monotonic:
                if not 0 <= now - latest['monotonic'] <= self.MAX_AGE or latest['sequence'] <= self.delivered:
                    raise ValueError('host sample is stale, future or already consumed')
                self.delivered = latest['sequence']
                return latest
            if now >= until:
                raise ValueError('missing fresh unique host sample within five seconds')
            time.sleep(min(0.05, until - now))


def _terminal(path, reader, pid):
    before = path.lstat()
    if (reader is None or reader.metadata is None or not stat.S_ISREG(before.st_mode)
            or (before.st_dev, before.st_ino) != reader.identity
            or not 0 < before.st_size <= 64 * 1024 * 1024):
        raise ValueError('terminal sample evidence has no unchanged bounded identity')
    digest, count, end = hashlib.sha256(), 0, None
    with path.open('rb') as stream:
        first = stream.readline(65537)
        if first != reader.metadata:
            raise ValueError('observer metadata changed')
        digest.update(first)
        while line := stream.readline(HostSampleReader.MAX_LINE + 1):
            if len(line) > HostSampleReader.MAX_LINE or not line.endswith(b'\n'):
                raise ValueError('incomplete or oversized observer terminal evidence')
            digest.update(line)
            row = json.loads(line)
            if not isinstance(row, dict) or row.get('observer_pid') != pid or end is not None:
                raise ValueError('foreign observer or data after terminal marker')
            if row.get('kind') == 'sample':
                count += 1
                if type(row.get('sequence')) is not int or row['sequence'] != count:
                    raise ValueError('terminal sample sequence is not contiguous')
                _sample(row)
            elif (row.get('kind') == 'observer_end' and row.get('ps_unchanged') is True
                  and row.get('reason') == 'signal' and type(row.get('samples')) is int
                  and row['samples'] == count):
                end = row
            else:
                raise ValueError('unexpected observer terminal record')
    after = path.lstat()
    if end is None or any(getattr(before, key) != getattr(after, key)
                         for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')):
        raise ValueError('observer terminal evidence missing or changed during read')
    return {'path': str(path), 'sha256': digest.hexdigest(), 'samples': count,
            'observer_pid': pid, 'ps_unchanged': True, 'reason': 'signal'}


def _wait_until(until, lease, deadline):
    while time.monotonic() < until:
        lease.validate()
        if time.monotonic() >= deadline:
            raise TimeoutError('qualification deadline exhausted')
        time.sleep(max(0, min(0.1, until - time.monotonic(), deadline - time.monotonic())))


def _dependency_site():
    prefix = Path(sys.executable).absolute().parent.parent
    site = prefix / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    if (not sys.flags.no_site or not sys.flags.safe_path or not sys.dont_write_bytecode
            or not (prefix / 'pyvenv.cfg').is_file() or not site.is_dir()
            or site.resolve(strict=True) != site):
        raise ValueError('qualification requires physical dependency venv Python -S -P -B')
    return site


def _wait_ready(observer, path, lease, deadline):
    """Retain U0's bounded startup interval before beginning the gate clock."""
    while time.monotonic() < deadline:
        lease.validate()
        if observer.poll() is not None:
            raise RuntimeError('host observer exited before its startup witness')
        if os.path.lexists(path):
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                state = os.fstat(fd)
                if not stat.S_ISREG(state.st_mode):
                    raise ValueError('host startup evidence is not a regular file')
                raw = os.read(fd, 65537)
                first = raw.split(b'\n', 1)[0]
                if len(first) > 65536:
                    raise ValueError('oversized host startup witness')
                if b'\n' in raw:
                    value = json.loads(first)
                    current = path.lstat()
                    if ((current.st_dev, current.st_ino) != (state.st_dev, state.st_ino)
                            or not stat.S_ISREG(current.st_mode)
                            or value.get('kind') != 'observer_start'
                            or value.get('observer_pid') != observer.pid
                            or value.get('ps_sha256') != _hash('/bin/ps')):
                        raise ValueError('host startup witness identity differs')
                    return (state.st_dev, state.st_ino)
            finally:
                os.close(fd)
        _wait_until(min(deadline, time.monotonic() + 0.05), lease, deadline)
    raise TimeoutError('host observer metadata not ready within bounded startup interval')


def qualify(*, lease, output_path, psutil_module, deadline, register_child=None):
    """Acquire no lock; qualify once under the caller's owned lease and total150s cap.

    lease.validate() must raise on loss. register_child(proc), if supplied,
    transfers immediate observer supervision to the outer interruption handler.
    QualificationError.evidence always distinguishes a failed gate from cleanup.
    """
    started = time.monotonic()
    if not _number(deadline) or not 0 < deadline - started <= QUALIFICATION_SECONDS:
        raise ValueError('qualification requires an absolute deadline at most150s away')
    lease.validate()
    site = _dependency_site()
    if Path(psutil_module.__file__).resolve(strict=True).parent.parent != site:
        raise ValueError('qualification psutil differs from physical dependency site')
    out = Path(output_path)
    if not out.is_absolute() or out.parent.resolve(strict=True) != out.parent or os.path.lexists(out):
        raise ValueError('qualification requires a fresh physical output directory')
    out.mkdir(mode=0o700)
    samples_path = out / 'host-samples.jsonl'
    observer = reader = None
    evidence = {'started_at': _utc(), 'settling_seconds': SETTLING_SECONDS,
                'total_limit_seconds': QUALIFICATION_SECONDS, 'deadline_monotonic': deadline,
                'qualification_passed': False, 'cleanup_verified': False,
                'source_sha256': _hash(__file__), 'thresholds': dict(THRESHOLDS)}
    failure = None
    try:
        _wait_until(started + SETTLING_SECONDS, lease, deadline - CLEANUP_RESERVE)
        command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()),
                   '--observe', '--samples', str(samples_path), '--deadline', repr(deadline - 1)]
        env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
               'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
        with (out / 'observer.log').open('xb') as log:
            observer = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            if register_child is not None:
                register_child(observer)
            created = psutil_module.Process(observer.pid).create_time()
            evidence['observer'] = {'pid': observer.pid, 'create_time': created, 'command': command}
            ready_deadline = min(deadline - CLEANUP_RESERVE, time.monotonic() + 15)
            ready_identity = _wait_ready(observer, samples_path, lease, ready_deadline)
            reader = HostSampleReader(samples_path, observer.pid)
            if reader.identity != ready_identity:
                raise ValueError('host sample file changed after startup witness')
            gate_started, samples = time.monotonic(), []
            for _ in range(SAMPLE_COUNT):
                _wait_until(time.monotonic() + 1, lease, deadline - CLEANUP_RESERVE)
                if observer.poll() is not None:
                    raise RuntimeError('host observer exited during qualification')
                samples.append(reader.sample(lease=lease, deadline=deadline - CLEANUP_RESERVE))
            decision = evaluate_samples(samples, owned_roots={os.getpid(), observer.pid},
                                        elapsed_seconds=time.monotonic() - gate_started)
            _write(out / 'gate-samples.json', samples)
            _write(out / 'idle-decision.json', decision)
            evidence['decision'] = decision
            if not decision['idle']:
                raise RuntimeError('host qualification failed; no retry or timing arm authorized')
            lease.validate()
    except BaseException as error:
        failure = error
        evidence['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        cleanup = {'observer_launched': observer is not None, 'forced': False,
                   'process_stopped': observer is None, 'cleanup_verified': observer is None}
        if observer is not None:
            try:
                if observer.poll() is not None:
                    raise RuntimeError('observer exited before normal stop request')
                observer.send_signal(signal.SIGTERM)
                try:
                    observer.wait(timeout=max(0, deadline - 1 - time.monotonic()))
                except subprocess.TimeoutExpired:
                    cleanup['forced'] = True
                    if observer.poll() is None:
                        os.killpg(observer.pid, signal.SIGKILL)
                    observer.wait(timeout=max(0, min(0.5, deadline - time.monotonic())))
                cleanup.update(process_stopped=observer.returncode is not None,
                               returncode=observer.returncode)
                if cleanup['forced'] or observer.returncode != 0:
                    raise RuntimeError('observer stop was forced or unsuccessful')
                try:
                    os.killpg(observer.pid, 0)
                except ProcessLookupError:
                    pass
                else:
                    raise RuntimeError('observer group remains; never signal a reaped/reused identity')
                cleanup['terminal'] = _terminal(samples_path, reader, observer.pid)
                cleanup['cleanup_verified'] = True
            except BaseException as error:
                cleanup['error'] = {'type': type(error).__name__, 'message': str(error)}
        if reader is not None:
            try:
                reader.close()
                cleanup['reader_close_verified'] = True
            except BaseException as error:
                cleanup['reader_close_verified'] = False
                evidence.setdefault('finalization_errors', []).append({
                    'stage': 'reader_close', 'type': type(error).__name__, 'message': str(error)})
                if failure is None:
                    failure = error
        try:
            lease.validate()
        except BaseException as error:
            if failure is None:
                failure = error
            evidence['lease_error'] = {'type': type(error).__name__, 'message': str(error)}
        evidence['cleanup'] = cleanup
        evidence['cleanup_verified'] = cleanup['cleanup_verified']
        evidence['elapsed_seconds'] = time.monotonic() - started
        evidence['qualification_passed'] = (failure is None and cleanup['cleanup_verified']
            and evidence['elapsed_seconds'] <= QUALIFICATION_SECONDS and time.monotonic() < deadline)
        try:
            _write(out / 'qualification.json', evidence)
        except BaseException as error:
            evidence['qualification_passed'] = False
            evidence.setdefault('finalization_errors', []).append({
                'stage': 'qualification_evidence_write',
                'type': type(error).__name__, 'message': str(error)})
            # Preserve the established process-cleanup verdict. Failed evidence
            # persistence prevents admission but does not erase an earlier proof.
            failure = error
    if not evidence['qualification_passed']:
        raise QualificationError('WP1 host qualification did not pass with verified cleanup', evidence) from failure
    return evidence


def _observe(samples, deadline):
    site = _dependency_site()
    sys.path.append(str(site))  # No site.addsitedir, dependency .pth or editable hook.
    import psutil
    if Path(psutil.__file__).resolve(strict=True).parent.parent != site:
        raise ValueError('observer psutil import identity differs')
    if not 0 < deadline - time.monotonic() <= QUALIFICATION_SECONDS:
        raise ValueError('observer deadline is invalid')
    if os.getsid(0) != os.getpid() or os.getpgid(0) != os.getpid():
        raise ValueError('observer requires its own process session')
    stop = False

    def stop_requested(number, frame):
        nonlocal stop
        stop = True

    def cutoff(number, frame):
        os.killpg(os.getpid(), signal.SIGKILL)  # Own unreaped session includes a bounded ps/sysctl.

    signal.signal(signal.SIGALRM, cutoff)
    signal.signal(signal.SIGTERM, stop_requested)
    signal.signal(signal.SIGINT, stop_requested)
    signal.setitimer(signal.ITIMER_REAL, deadline - time.monotonic())

    def command_text(command):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('host sampler deadline exhausted')
        completed = subprocess.run(command, capture_output=True, text=True, check=True,
                                   timeout=min(5, remaining))
        if completed.stderr.strip():
            raise ValueError('host command wrote stderr: ' + command[0])
        return completed.stdout.strip()

    def emit(stream, row):
        stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())

    if not samples.is_absolute() or samples.parent.resolve(strict=True) != samples.parent:
        raise ValueError('observer output must be physical and absolute')
    with samples.open('x', encoding='utf-8') as stream:
        os.chmod(samples, 0o600)
        sequence = 0
        try:
            cpu_count = int(command_text(CPU_COMMAND))
            if cpu_count <= 0:
                raise ValueError('logical CPU count unavailable')
            ps_hash = _hash('/bin/ps')
            emit(stream, {'kind': 'observer_start', 'observer_pid': os.getpid(), 'at': _utc(),
                'monotonic': time.monotonic(), 'logical_cpus': cpu_count, 'ps_sha256': ps_hash,
                'ps_command': PS_COMMAND, 'load_command': LOAD_COMMAND, 'cpu_command': CPU_COMMAND,
                'scope': 'Separate unsandboxed read-only host observer; no network operations.'})
            psutil.cpu_percent(interval=None)
            while not stop:
                time.sleep(1)
                if stop:
                    break
                rows = []
                for line in command_text(PS_COMMAND).splitlines():
                    fields = line.split(None, 3)
                    if len(fields) != 4:
                        raise ValueError('malformed host process row')
                    rows.append({'pid': int(fields[0]), 'ppid': int(fields[1]),
                                 'cpu_percent': float(fields[2]), 'name': fields[3]})
                text = command_text(LOAD_COMMAND)
                if not re.fullmatch(r'\{\s*[0-9.]+\s+[0-9.]+\s+[0-9.]+\s*\}', text):
                    raise ValueError('malformed sysctl load average')
                sequence += 1
                row = {'kind': 'sample', 'observer_pid': os.getpid(), 'sequence': sequence,
                    'at': _utc(), 'monotonic': time.monotonic(), 'logical_cpus': cpu_count,
                    'cpu_percent': psutil.cpu_percent(interval=None),
                    'load': [float(value) for value in text.strip('{} ').split()], 'processes': rows}
                _sample(row)
                emit(stream, row)
            if _hash('/bin/ps') != ps_hash:
                raise ValueError('/bin/ps changed during observation')
            emit(stream, {'kind': 'observer_end', 'observer_pid': os.getpid(), 'at': _utc(),
                'monotonic': time.monotonic(), 'samples': sequence, 'ps_unchanged': True, 'reason': 'signal'})
            return 0
        except BaseException as error:
            emit(stream, {'kind': 'observer_error', 'observer_pid': os.getpid(), 'at': _utc(),
                          'error': type(error).__name__ + ': ' + str(error)})
            return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observe', action='store_true', required=True)
    parser.add_argument('--samples', type=Path, required=True)
    parser.add_argument('--deadline', type=float, required=True)
    args = parser.parse_args()
    raise SystemExit(_observe(args.samples, args.deadline))
