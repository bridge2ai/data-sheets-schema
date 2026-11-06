#!/usr/bin/env python3
"""Read-only host observer for U0/#4354, amended protocol 2026-11-06.

Inputs: unchanged /bin/ps, sysctl and physical venv psutil system CPU counters.
Output: one exclusive JSONL sample file; no network or production/native code.
Runs outside the trial sandbox under the explicit ruling in the U0 brief.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

PS = Path('/bin/ps')
PS_COMMAND = ['/bin/ps', '-A', '-o', 'pid=,ppid=,pcpu=,comm=']
LOAD_COMMAND = ['/usr/sbin/sysctl', '-n', 'vm.loadavg']
CPU_COMMAND = ['/usr/sbin/sysctl', '-n', 'hw.logicalcpu']


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def command_text(command):
    completed = subprocess.run(command, capture_output=True, text=True,
                               check=True, timeout=5)
    if completed.stderr.strip():
        raise ValueError('host command wrote stderr: ' + command[0])
    return completed.stdout.strip()


def processes(text):
    rows, seen = [], set()
    for line in text.splitlines():
        fields = line.split(None, 3)
        if len(fields) != 4:
            raise ValueError('malformed host process row')
        pid, ppid, cpu = int(fields[0]), int(fields[1]), float(fields[2])
        if pid < 0 or ppid < 0 or pid in seen or not math.isfinite(cpu) or cpu < 0:
            raise ValueError('invalid host process identity or CPU value')
        seen.add(pid)
        rows.append({'pid': pid, 'ppid': ppid, 'cpu_percent': cpu, 'name': fields[3]})
    if not rows or os.getpid() not in seen or 1 not in seen:
        raise ValueError('host table omits observer or launchd, or is empty')
    return rows


def loads(text):
    if not re.fullmatch(r'\{\s*[0-9.]+\s+[0-9.]+\s+[0-9.]+\s*\}', text):
        raise ValueError('malformed sysctl load average')
    values = [float(value) for value in text.strip('{} ').split()]
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError('invalid sysctl load average')
    return values


def emit(stream, row):
    stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def observe(samples, max_seconds, psutil):
    if not 1 <= max_seconds <= 9000:
        raise ValueError('observer maximum must be 1–9000 seconds')
    samples = Path(samples)
    if not samples.is_absolute() or samples.parent.resolve(strict=True) != samples.parent:
        raise ValueError('observer output must be an exact absolute path')
    old_handlers = {}
    stop = False

    def request_stop(_signum, _frame):
        nonlocal stop
        stop = True

    with samples.open('x', encoding='utf-8') as stream:
        os.chmod(samples, 0o600)
        started = time.monotonic()
        sequence = 0
        try:
            for signum in (signal.SIGINT, signal.SIGTERM):
                old_handlers[signum] = signal.signal(signum, request_stop)
            cpu_count = int(command_text(CPU_COMMAND))
            if cpu_count <= 0:
                raise ValueError('invalid logical CPU count')
            ps_hash = hashlib.sha256(PS.read_bytes()).hexdigest()
            emit(stream, {'kind': 'observer_start', 'format': 'native_u0_host_observer_v1',
                'observer_pid': os.getpid(), 'at': utc_now(), 'monotonic': started,
                'ps_command': PS_COMMAND, 'load_command': LOAD_COMMAND, 'cpu_command': CPU_COMMAND,
                'ps_sha256': ps_hash, 'logical_cpus': cpu_count, 'max_seconds': max_seconds,
                'network_policy': 'unsandboxed read-only observer; no network operations',
                'authority': '2026-11-06-codex-native-u0.md appended lead ruling'})
            psutil.cpu_percent(interval=None)  # Prime before any eligible sample.
            while not stop and time.monotonic() - started < max_seconds:
                time.sleep(1)
                if stop:
                    break
                rows = processes(command_text(PS_COMMAND))
                load = loads(command_text(LOAD_COMMAND))
                cpu = psutil.cpu_percent(interval=None)
                if not math.isfinite(cpu) or not 0 <= cpu <= 100:
                    raise ValueError('invalid aggregate CPU observation')
                sequence += 1
                emit(stream, {'kind': 'sample', 'observer_pid': os.getpid(),
                    'sequence': sequence, 'at': utc_now(), 'monotonic': time.monotonic(),
                    'load': load, 'logical_cpus': cpu_count, 'cpu_percent': cpu, 'processes': rows})
            if hashlib.sha256(PS.read_bytes()).hexdigest() != ps_hash:
                raise ValueError('/bin/ps changed during observation')
            emit(stream, {'kind': 'observer_end', 'observer_pid': os.getpid(),
                'at': utc_now(), 'monotonic': time.monotonic(), 'samples': sequence,
                'reason': 'signal' if stop else 'maximum_elapsed', 'ps_unchanged': True})
            return 0
        except Exception as exc:
            emit(stream, {'kind': 'observer_error', 'observer_pid': os.getpid(),
                'at': utc_now(), 'monotonic': time.monotonic(),
                'error': type(exc).__name__ + ': ' + str(exc)})
            return 1
        finally:
            for signum, handler in old_handlers.items():
                signal.signal(signum, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=Path, required=True)
    parser.add_argument('--max-seconds', type=int, required=True)
    args = parser.parse_args()
    helper = Path(__file__).with_name('native_recorder_measure_20261026.py')
    spec = importlib.util.spec_from_file_location('u0_dependency_bootstrap', helper)
    measure = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(measure)
    measure.initialize_dependencies()
    import psutil
    return observe(args.samples, args.max_seconds, psutil)


if __name__ == '__main__':
    raise SystemExit(main())
