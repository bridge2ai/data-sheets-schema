"""Bounded local host observations, separate from registered acceptance documents.

AC is required only at sequence/proof start. Clock divergence is suspension
evidence, not proof of its cause; local sleep events supply that attribution.
No provider, network, native-model executable, or power-setting operation.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import time

MAX_EVENTS = 4096
MAX_RECORD_BYTES = 128 * 1024
CLOCK_TOLERANCE_NS = 1_000_000_000


def _local(argv, *, limit, timeout=8):
    """Drain at most limit bytes and reap the exact owned local subprocess."""
    child = None
    try:
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, env={'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C'})
        deadline = time.monotonic() + timeout
        chunks, count = [], 0
        with selectors.DefaultSelector() as selected:
            selected.register(child.stdout, selectors.EVENT_READ)
            while selected.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('local host probe timed out')
                if not selected.select(min(remaining, 0.1)):
                    continue
                part = os.read(child.stdout.fileno(), min(65536, limit + 1 - count))
                if not part:
                    selected.unregister(child.stdout)
                    break
                count += len(part)
                if count > limit:
                    raise ValueError('local host probe exceeded output bound')
                chunks.append(part)
        code = child.wait(timeout=max(0.001, deadline - time.monotonic()))
        if code:
            return {'status': 'unknown', 'reason': 'nonzero_exit', 'returncode': code, 'text': ''}
        return {'status': 'read', 'reason': None, 'returncode': code,
                'text': b''.join(chunks).decode('utf-8', errors='replace')}
    except (OSError, ValueError, TimeoutError, subprocess.TimeoutExpired) as exc:
        return {'status': 'unknown', 'reason': type(exc).__name__, 'text': ''}
    finally:
        if child is not None:
            if child.poll() is None:
                child.kill()
            child.wait()
            child.stdout.close()


def parse_power(battery_text, lid_text):
    sources = re.findall(r"^Now drawing from '(AC Power|Battery Power)'\s*$", battery_text, re.M)
    percent = re.search(r'\b(\d{1,3})%;', battery_text)
    lid = re.search(r'"AppleClamshellState"\s*=\s*(Yes|No|true|false)\b', lid_text)
    level = int(percent[1]) if percent and 0 <= int(percent[1]) <= 100 else None
    return {'source': {'AC Power': 'ac', 'Battery Power': 'battery'}[sources[0]] if len(sources) == 1 else 'unknown',
            'battery_percent': level,
            'lid': ('closed' if lid[1] in ('Yes', 'true') else 'open') if lid else 'unknown'}


def probe():
    battery = _local(['/usr/bin/pmset', '-g', 'batt'], limit=16384)
    lid = _local(['/usr/sbin/ioreg', '-r', '-n', 'IOPMrootDomain', '-d', '1'], limit=1024 * 1024)
    return {**parse_power(battery['text'], lid['text']),
            'observed_wall_ns': time.time_ns(),
            'interfaces': {'battery': {k: v for k, v in battery.items() if k != 'text'},
                           'lid': {k: v for k, v in lid.items() if k != 'text'}}}


def require_ac(reading):
    if reading.get('source') != 'ac':
        raise ValueError('host power must be positively observed as AC before sequence start')


def dispatch_power():
    """Read the power source last, without a subsequent slow lid query."""
    battery = _local(['/usr/bin/pmset', '-g', 'batt'], limit=16384)
    reading = parse_power(battery['text'], '')
    if reading['source'] != 'ac' or battery['status'] != 'read':
        raise ValueError('host power must be positively observed as AC immediately before dispatch')
    return reading


def clock_reading(label):
    return {'label': label, 'wall_ns': time.time_ns(), 'monotonic_ns': time.monotonic_ns()}


def _write_new(path, value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


def _read_record(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
        raw = stream.read(MAX_RECORD_BYTES + 1)
    if len(raw) > MAX_RECORD_BYTES:
        raise ValueError('host clock record exceeds bound')
    return json.loads(raw)


def sequence_start(path, started_at):
    """Exclusive start evidence survives battery/unknown refusal; no child runs."""
    reading = probe()
    _write_new(Path(path), {'started_at': started_at, 'host_power': reading,
                           'clock': clock_reading('sequence_start')})
    require_ac(reading)


def start_run(directory, *, require_ac_power=False):
    reading = probe()
    record = {**clock_reading('start'), 'host_power': reading}
    _write_new(Path(directory) / 'host-clock-start.json', record)
    if require_ac_power:
        require_ac(reading)
    return record


def observe(directory, boundary, action, *args):
    """Supplemental writes never change the outcome of the observed operation."""
    try:
        return action(*args)
    except Exception as exc:
        observation_error(directory, boundary, exc)
        return None


def observation_error(directory, boundary, exc):
    # Exception messages can contain sensitive subprocess arguments. Retain the
    # boundary and class only; stderr remains available if the disk write fails.
    record = {'boundary': boundary, 'error_type': type(exc).__name__}
    try:
        _write_new(Path(directory) / ('host-observation-error-' + boundary + '.json'), record)
    except Exception:
        try:
            print('host observation unavailable: ' + boundary + ': ' + type(exc).__name__, file=sys.stderr)
        except Exception:
            pass


def checkpoint(directory, label):
    directory = Path(directory)
    if not (directory / 'host-clock-start.json').exists():
        return None  # Historical replay/standalone publication has no active host observation.
    if re.fullmatch(r'stage-[0-9a-f]{64}', label) is None:
        raise ValueError('host stage clock requires its published journal identity')
    path = directory / ('host-clock-' + label + '.json')
    if path.exists():
        return _read_record(path)  # Same journal is not a newly published stage.
    record = clock_reading(label)
    _write_new(path, record)
    return record


def clock_gaps(records):
    ordered = sorted(records, key=lambda item: item['monotonic_ns'])
    gaps = []
    for before, after in zip(ordered, ordered[1:]):
        wall = after['wall_ns'] - before['wall_ns']
        monotonic = after['monotonic_ns'] - before['monotonic_ns']
        difference = wall - monotonic
        if abs(difference) > CLOCK_TOLERANCE_NS:
            gaps.append({'before': before['label'], 'after': after['label'],
                'wall_elapsed_ns': wall, 'monotonic_elapsed_ns': monotonic,
                'difference_ns': difference, 'suspension_detected': difference > 0,
                'basis': 'clock divergence; sleep or a wall-clock adjustment requires separate attribution'})
    return gaps


def parse_sleep_events(text, start_ns, end_ns):
    """No-sleep requires ordered, paired, recognized events bracketing the run.

    Unknown formats and incomplete coverage retain any parsed positive evidence
    but cannot certify absence. A DarkWake ends sleep just like a full Wake.
    """
    events, intervals, sleeping, stamps, problems = [], [], None, [], set()
    if end_ns < start_ns:
        problems.add('wall clock moved backwards')
    for line in text.splitlines():
        match = re.match(r'(.{25})\s+(Sleep|Wake|DarkWake)\s+(Entering Sleep|Wake from|DarkWake from)', line)
        if not match:
            if re.search(r'sleep|wake', line, re.I) and not line.startswith('#'):
                problems.add('unrecognized sleep-like record')
            continue
        try:
            instant = int(datetime.strptime(match[1], '%Y-%m-%d %H:%M:%S %z').timestamp() * 1_000_000_000)
        except ValueError:
            problems.add('unrecognized sleep timestamp')
            continue
        if stamps and instant < stamps[-1]:
            problems.add('sleep log is not ordered')
        stamps.append(instant)
        if len(stamps) > MAX_EVENTS:
            raise ValueError('sleep event count exceeds bound')
        kind = match[2]
        if match[3] != {'Sleep': 'Entering Sleep', 'Wake': 'Wake from', 'DarkWake': 'DarkWake from'}[kind]:
            problems.add('unrecognized sleep event wording')
        if start_ns <= instant <= end_ns:
            events.append({'wall_ns': instant, 'event': kind, 'raw': line[:2048]})
            if len(events) > MAX_EVENTS:
                raise ValueError('sleep event count exceeds bound')
        if kind == 'Sleep':
            if sleeping is not None:
                problems.add('unmatched sleep event')
            sleeping = instant
        elif sleeping is not None:
            if sleeping <= end_ns and instant >= start_ns:
                intervals.append({'sleep_wall_ns': sleeping, 'wake_wall_ns': instant,
                                  'overlap_ns': max(0, min(instant, end_ns) - max(sleeping, start_ns))})
            sleeping = None
        else:
            problems.add('unmatched wake event')
    if sleeping is not None and sleeping <= end_ns:
        intervals.append({'sleep_wall_ns': sleeping, 'wake_wall_ns': None,
                          'overlap_ns': max(0, end_ns - max(sleeping, start_ns))})
    if sleeping is not None:
        problems.add('unmatched sleep event')
    covered = bool(stamps) and stamps[0] <= start_ns and stamps[-1] >= end_ns
    if not covered:
        problems.add('recognized log does not cover requested interval')
    return {'status': 'unknown' if problems else 'read',
            'reason': '; '.join(sorted(problems)) if problems else None,
            'coverage': {'start_ns': stamps[0] if stamps else None,
                         'end_ns': stamps[-1] if stamps else None, 'covers_interval': covered},
            'events': events, 'intervals': intervals}


def sleep_events(start_ns, end_ns):
    if end_ns < start_ns:
        return {'status': 'unknown', 'reason': 'wall clock moved backwards', 'events': [], 'intervals': []}
    reading = _local(['/usr/bin/pmset', '-g', 'log'], limit=64 * 1024 * 1024)
    if reading['status'] != 'read':
        return {'status': 'unknown', 'reason': reading['reason'], 'events': [], 'intervals': []}
    try:
        return parse_sleep_events(reading['text'], start_ns, end_ns)
    except ValueError as exc:
        return {'status': 'unknown', 'reason': str(exc), 'events': [], 'intervals': []}


def finish_run(directory):
    directory = Path(directory)
    ending = clock_reading('end')
    _write_new(directory / 'host-clock-end.json', ending)
    paths = []
    for path in directory.glob('host-clock-*.json'):
        paths.append(path)
        if len(paths) > MAX_EVENTS:
            raise ValueError('host clock record count exceeds bound')
    records = [_read_record(path) for path in paths]
    start = _read_record(directory / 'host-clock-start.json')
    events = sleep_events(start['wall_ns'], ending['wall_ns'])
    gaps = clock_gaps(records)
    result = {'scope': 'supplemental local host observations; no acceptance decision',
        'clocks': records, 'clock_gaps': gaps, 'system_sleep': events,
        'host_slept': any(row['overlap_ns'] > 0 for row in events['intervals']) if events['status'] == 'read' else None,
        'suspension_detected': bool(events['intervals']) or any(g['suspension_detected'] for g in gaps)}
    _write_new(directory / 'host-observation.json', result)
    return result


@contextmanager
def finishing_run(directory):
    """End observation cannot replace active or previously caught failures."""
    try:
        yield
    finally:
        original = sys.exc_info()[1]
        try:
            finish_run(directory)
        except Exception as exc:
            observation_error(directory, 'end', exc)
            if original is not None:
                original.__notes__ = [*getattr(original, '__notes__', []),
                                      'host observation could not be persisted: ' + type(exc).__name__]
