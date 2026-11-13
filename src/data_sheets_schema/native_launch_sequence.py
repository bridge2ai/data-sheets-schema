"""One explicit native capture, guard and launch sequence; never retries.

Proposed amendment N1, not authorization to run. Inputs are explicit paths;
children use this source checkout and a fixed environment. Raw command outputs
are retained before interpretation. Completion still needs independent review.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import sys

from . import native_subscription_guard as guard

SEQUENCE_KIND = 'd4d_native_launch_sequence'
SEQUENCE_VERSION = 1
MAX_COMMAND_OUTPUT_BYTES = 32 * 1024 * 1024
SOURCE_ROOT = Path(__file__).resolve().parents[2]
COMMANDS = ('capture-subscription-event', 'prepare-subscription-guard-v2', 'launch')
OUTPUTS = ('capture-command.json', 'guard-command.json', 'launch-command.json')
START_FILENAME = 'sequence-start.json'
SCRIPT_FILENAME = 'sequence-script.py'
# -I excludes ambient PYTHONPATH/cwd; explicitly select this file's checkout.
BOOTSTRAP = ('import sys; sys.path.insert(0, sys.argv.pop(1)); '
             'from data_sheets_schema.native_generation import main; '
             'raise SystemExit(main())')
CHILD_ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': '/nonexistent',
             'LANG': 'C.UTF-8', 'GIT_CONFIG_GLOBAL': '/dev/null',
             'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_TERMINAL_PROMPT': '0',
             'GIT_NO_LAZY_FETCH': '1', 'GIT_NO_REPLACE_OBJECTS': '1'}


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _strict_utc(value):
    if type(value) is not str or re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z', value) is None:
        raise ValueError('delegated start times must be strict UTC timestamps')
    return datetime.fromisoformat(value[:-1] + '+00:00')


def _delegation(direction, confirmation, now):
    if (direction is None) != (confirmation is None):
        raise ValueError('delegated start needs both recorded times')
    if direction is None:
        return
    current = _strict_utc(now)
    for value in (direction, confirmation):
        seconds = (current - _strict_utc(value)).total_seconds()
        if not 0 <= seconds <= 1800:
            raise ValueError('delegated start must be within thirty minutes after both recorded times')


def _path(value):
    path = Path(value)
    if (not path.is_absolute() or str(path) != str(value)
            or path.parent.resolve(strict=True) != path.parent or path.is_symlink()):
        raise ValueError('sequence paths must be canonical, absolute and non-symlinked')
    return path


def _new(path):
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb')


def _write_new(path, raw):
    with _new(path) as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _digest(raw, label):
    if type(raw) is not str or re.fullmatch('[0-9a-f]{64}', raw) is None:
        raise ValueError(label + ' must be a lowercase SHA-256')
    return raw


def _unchanged(inputs):
    for path, raw in inputs.items():
        if guard.read_regular(path, limit=MAX_COMMAND_OUTPUT_BYTES) != raw:
            raise ValueError('sequence input changed between commands')


def _run_step(command, flags, output, steps):
    argv = [sys.executable, '-I', '-B', '-c', BOOTSTRAP, str(SOURCE_ROOT / 'src'), command, *flags]
    stderr_path = output.with_suffix('.stderr.txt')
    step = {'step': command, 'argv': argv, 'started_at': _utc_now(),
            'completed_at': None, 'return_code': None, 'output_path': str(output),
            'stderr_path': str(stderr_path)}
    # Reserve both outputs before the command, including on spawn failure.
    with _new(output) as stdout, _new(stderr_path) as stderr:
        steps.append(step)
        try:
            result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                    cwd=SOURCE_ROOT, env=dict(CHILD_ENV), check=False)
            step['return_code'] = result.returncode
        finally:
            stdout.flush(); stderr.flush()
            os.fsync(stdout.fileno()); os.fsync(stderr.fileno())
            step['completed_at'] = _utc_now()
    if result.returncode != 0:
        raise ValueError(command + ' exited nonzero; see retained command output')
    raw = guard.read_regular(output, limit=MAX_COMMAND_OUTPUT_BYTES)
    step['output_sha256'] = guard.sha(raw)
    try:
        doc = guard.strict_json(raw)
    except ValueError as exc:
        raise ValueError(command + ' output is not strict JSON') from exc
    if type(doc) is not dict or doc.get('command') != command:
        raise ValueError(command + ' output lacks its exact command identity')
    body = doc.get('result')
    if type(body) is not dict or not body:
        raise ValueError(command + ' output lacks its result object')
    return body


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('registration', 'review', 'launch-word', 'account-choice', 'ci', 'output-directory'):
        result.add_argument('--' + name, required=True)
    result.add_argument('--subscription-guard', '--output', dest='subscription_guard', required=True)
    result.add_argument('--packet-directory', '--packet', dest='packet_directory', required=True)
    result.add_argument('--direction-recorded-at', help='Recorded UTC time of the owner direction')
    result.add_argument('--host-confirmed-at', help='Recorded UTC time of the owner host-state confirmation')
    return result


def _run_verified(argv, *, verified_script, entry_inputs):
    invocation = globals().get('_entry_invocation')
    if not callable(invocation):
        raise ValueError('sequence body requires a live verified entry namespace')
    invocation(globals(), argv, verified_script, entry_inputs)
    args = parser().parse_args(argv)
    started = _utc_now()
    record = {'kind': SEQUENCE_KIND, 'version': SEQUENCE_VERSION, 'started_at': started,
              'completed_at': None, 'status': 'stopped', 'stop_reason': None,
              'capture_manifest': None, 'guard_sha256': None, 'steps': [],
              'direction_recorded_at': args.direction_recorded_at,
              'host_confirmed_at': args.host_confirmed_at, 'delegation_checked_at': None,
              'script_path': None}
    sequence = None
    try:
        inputs = {_path(getattr(args, name)): None for name in
                  ('registration', 'review', 'launch_word', 'account_choice', 'ci')}
        capture_root = _path(args.output_directory)
        guard_path = _path(args.subscription_guard)
        packet = _path(args.packet_directory)
        if packet.exists():
            if not packet.is_dir() or packet.resolve(strict=True) != packet:
                raise ValueError('packet must be a resolved directory')
        else:
            packet.mkdir(mode=0o700)
        outputs = [packet / name for name in OUTPUTS]
        sequence_candidate = packet / 'sequence.json'
        targets = [*outputs, *(p.with_suffix('.stderr.txt') for p in outputs),
                   sequence_candidate, packet / START_FILENAME, packet / SCRIPT_FILENAME, guard_path]
        if len(set(targets)) != len(targets) or any(p in inputs for p in targets):
            raise ValueError('sequence output paths collide')
        for path in targets:
            if os.path.lexists(path):
                raise FileExistsError('sequence refuses an existing output')
        # Exclusive claim prevents concurrent starts sharing one packet.
        _write_new(packet / START_FILENAME, guard.canonical({'started_at': started}))
        sequence = sequence_candidate
        script_path = packet / SCRIPT_FILENAME
        _write_new(script_path, verified_script)
        record['script_path'] = str(script_path)
        _delegation(args.direction_recorded_at, args.host_confirmed_at, started)
        for path in inputs:
            inputs[path] = guard.read_regular(path, limit=MAX_COMMAND_OUTPUT_BYTES)
        if any(inputs.get(path) != raw for path, raw in entry_inputs.items()):
            raise ValueError('sequence entry inputs changed before use')
        if capture_root.exists() and (not capture_root.is_dir() or capture_root.resolve() != capture_root):
            raise ValueError('capture root must be a resolved directory')
        word_raw = inputs[Path(args.launch_word)]
        slots = [capture_root / 'captures' / guard.sha(word_raw) / ('capture-' + str(i)) / 'capture.json'
                 for i in range(1, 4)]
        existed = {path for path in slots if os.path.lexists(path)}
        common = ['--registration', args.registration, '--review', args.review,
                  '--launch-word', args.launch_word, '--account-choice', args.account_choice]
        pins = {name: {'path': str(_path(getattr(args, name))),
                      'sha256': guard.sha(inputs[_path(getattr(args, name))])}
                for name in ('registration', 'review', 'launch_word', 'account_choice', 'ci')}
        def bound(extra=None):
            return [*common, '--sequence-inputs', guard.canonical({**pins, **(extra or {})}).decode()]
        _unchanged(inputs)
        record['delegation_checked_at'] = _utc_now()
        _delegation(args.direction_recorded_at, args.host_confirmed_at, record['delegation_checked_at'])
        from .native_sequence_start import claim
        record['start_claim'] = claim(inputs[Path(args.registration)], launch_word_raw=word_raw,
            direction=args.direction_recorded_at, confirmation=args.host_confirmed_at,
            packet=packet, started_at=record['delegation_checked_at'])
        # Durable claiming is preflight too; it must not carry a start across
        # either delegated deadline before the first child dispatch.
        record['delegation_checked_at'] = _utc_now()
        _delegation(args.direction_recorded_at, args.host_confirmed_at, record['delegation_checked_at'])
        start_pin = {'path': record['start_claim'],
                     'sha256': guard.sha(guard.read_regular(record['start_claim'], limit=MAX_COMMAND_OUTPUT_BYTES))}
        captured = _run_step(COMMANDS[0], [*bound({'sequence_start': start_pin}), '--output-directory', str(capture_root)],
                             outputs[0], record['steps'])
        manifest_value = captured.get('capture_manifest')
        if type(manifest_value) is not str:
            raise ValueError('capture output lacks its manifest path')
        manifest = _path(manifest_value)
        if manifest not in slots or manifest in existed:
            raise ValueError('capture output must name a new capture under this word')
        manifest_raw = guard.read_regular(manifest, limit=MAX_COMMAND_OUTPUT_BYTES)
        if guard.sha(manifest_raw) != _digest(captured.get('sha256'), 'capture digest'):
            raise ValueError('capture output digest differs from saved manifest')
        record['capture_manifest'] = str(manifest)
        _unchanged(inputs)
        prepared = _run_step(COMMANDS[1], [*bound({'capture': {'path': str(manifest), 'sha256': guard.sha(manifest_raw)}}), '--capture', str(manifest), '--output', str(guard_path)],
                             outputs[1], record['steps'])
        if prepared.get('path') != str(guard_path):
            raise ValueError('guard output lacks the requested path')
        digest = _digest(prepared.get('guard_sha256'), 'guard digest')
        if guard.sha(guard.read_regular(guard_path, limit=MAX_COMMAND_OUTPUT_BYTES)) != digest:
            raise ValueError('guard output digest differs from saved guard')
        record['guard_sha256'] = digest
        _unchanged(inputs)
        if guard.read_regular(manifest, limit=MAX_COMMAND_OUTPUT_BYTES) != manifest_raw:
            raise ValueError('capture manifest changed before launch')
        final = _run_step(COMMANDS[2], [*bound({'subscription_guard': {'path': str(guard_path), 'sha256': digest}}), '--ci', args.ci, '--subscription-guard', str(guard_path),
                         '--subscription-guard-sha256', digest], outputs[2], record['steps'])
        if (final.get('state') != 'completed_pending_independent_review'
                or final.get('runtime_gates_passed') is not True):
            raise ValueError('launch did not report complete runtime gates')
        record['status'] = 'completed'
    except Exception as exc:
        # Do not print child stderr, JSON values or arbitrary exception text.
        record['stop_reason'] = type(exc).__name__
        print('native launch sequence stopped; inspect the retained packet', file=sys.stderr)
    finally:
        record['completed_at'] = _utc_now()
        if sequence is not None:
            try:
                _write_new(sequence, guard.canonical(record))
            except OSError:
                record['status'] = 'stopped'
                print('native launch sequence could not save its record', file=sys.stderr)
    return 0 if record['status'] == 'completed' else 1


def main(argv=None):
    # Compatibility route; the documented trusted entry avoids importing this
    # implementation until after its byte check.
    from .native_launch_entry import main as entry
    return entry(argv)


if __name__ == '__main__':
    raise SystemExit(main())
