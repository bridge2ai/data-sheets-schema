"""Bounded registered, word-bound subscription observations (D115, 2026-11-08).

Only capture_subscription invokes the explicitly pinned executable. It sends
fixed trivial text with no tools or repository content. One process is not a
claim of one provider request; its emitted quota is not authenticated account
state. Up to three captures share one immutable word reservation. Failed and
stale captures stay spent and retained, never retried in place.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import time

from .native_subscription_guard import canonical, sha, strict_json, _timestamp


CAPTURE_PROMPT = 'Reply with OK.'
REQUEST_KIND = 'd4d_native_subscription_capture_request_v2'
LEGACY_REQUEST_KIND = 'd4d_native_subscription_capture_request_v1'
REQUEST_VERSION = 2
RESERVATION_KIND = 'd4d_native_subscription_capture_reservation_v2'
MAX_CAPTURES = 3
KIND = 'd4d_native_subscription_capture_v1'
VERSION = 1
MAX_STREAM_BYTES = 1048576
MAX_EVIDENCE_BYTES = 4 * MAX_STREAM_BYTES
MAX_OBSERVATIONS = 4096
MAX_DEADLINE_SECONDS = 60
REQUEST_KEYS = {'kind', 'version', 'count', 'directory', 'deadline_seconds',
                'prompt_sha256', 'max_stdout_bytes', 'max_stderr_bytes'}
ROOT = Path(__file__).resolve().parents[2]
BASIS = ('Pinned process emitted observations; not authenticated account/quota state, '
         'provider request count or generation acceptance.')
ISOLATION_FLAGS = ('--print', '--safe-mode', '--restricted', '--disable-slash-commands',
    '--no-session-persistence', '--prompt-suggestions', 'false', '--output-format',
    'stream-json', '--verbose', '--permission-mode', 'dontAsk', '--tools', '',
    '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
    '--setting-sources', '', '--settings', '{"disableAllHooks":true}')


def _utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _path(value):
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or path.resolve() != path:
        raise ValueError('capture paths must be canonical absolute paths')
    return path


def _sync(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _new(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    _sync(path.parent)


def _read(path, limit):
    path = _path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError('capture evidence must be a bounded regular file')
    except BaseException:
        os.close(descriptor)
        raise
    with os.fdopen(descriptor, 'rb') as stream:
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    witness = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns)
    if (len(raw) != before.st_size or len(raw) > limit
            or witness(before) != witness(after) or witness(after) != witness(path.lstat())):
        raise ValueError('capture evidence changed while reading')
    return raw


def _authority(registration_raw, review_bundle_raw, launch_word_raw, directory):
    from . import native_shared_registration_orchestration as registration
    from .native_launch_review import validate_bundle
    from .native_u4b_runtime import validate_prepared_runtime
    value = registration.verified(registration_raw)
    statement = validate_bundle(registration_raw, review_bundle_raw, launch_word_raw)
    runtime = value['runtime']
    validate_prepared_runtime(runtime)
    word = strict_json(launch_word_raw)
    request = statement['quota_capture']
    if (type(request) is not dict or set(request) != REQUEST_KEYS
            or type(request['version']) is not int
            or (request['kind'], request['version']) not in (
                (REQUEST_KIND, REQUEST_VERSION), (LEGACY_REQUEST_KIND, 1))
            or type(request['count']) is not int
            or request['count'] != (MAX_CAPTURES if request['version'] == REQUEST_VERSION else 1)
            or request['prompt_sha256'] != sha(CAPTURE_PROMPT.encode())
            or type(request['deadline_seconds']) is not int
            or not 0 < request['deadline_seconds'] <= MAX_DEADLINE_SECONDS
            or request['deadline_seconds'] > runtime['deadline_seconds']
            or any(type(request[key]) is not int or request[key] != MAX_STREAM_BYTES
                   for key in ('max_stdout_bytes', 'max_stderr_bytes'))):
        raise ValueError('owner statement must authorize the closed bounded capture request')
    directory = _path(directory)
    if _path(request['directory']) != directory:
        raise ValueError('capture directory differs from the owner statement')
    protected = [ROOT, Path(runtime['executable']['path'])]
    for key in ('attempt_directory', 'evidence_directory', 'composition', 'system_path', 'permission_probe'):
        protected.append(_path(value[key]))
    composition = strict_json(value['composition_raw_json'].encode())
    protected.extend(_path(path) for path in composition['policy']['readonly_lookups']['inputs'])
    protected.extend(_path(path) for path in composition['policy']['readonly_lookups']['output_directories'])
    for other in protected:
        if directory == other or directory.is_relative_to(other) or other.is_relative_to(directory):
            raise ValueError('capture directory overlaps source, input or attempt reservations')
    binding = {'registration_sha256': sha(registration_raw), 'review_bundle_sha256': sha(review_bundle_raw),
               'launch_word_sha256': sha(launch_word_raw), 'runtime_sha256': sha(canonical(runtime)),
               'request_sha256': sha(canonical(request)), 'attempt_id': value['attempt_id']}
    return value, statement, word, binding


def _invocation(runtime, directory):
    from .native_shared_runtime_values import POLICY_ENV
    environment = {**runtime['environment'], **POLICY_ENV,
                   'CLAUDE_CONFIG_DIR': str(directory / 'config')}
    # Never inherit environment variables, source paths, tokens or caller argv.
    argv = [runtime['executable']['path'], *ISOLATION_FLAGS, '--model', runtime['model'],
            '--effort', runtime['effort'], '--max-budget-usd', runtime['budget_guard_usd'], CAPTURE_PROMPT]
    return {'argv': argv, 'environment': environment, 'cwd': str(directory / 'cwd'),
            'stdin': 'DEVNULL', 'process_limit': 1, 'prompt_sha256': sha(CAPTURE_PROMPT.encode())}


@contextmanager
def _signals():
    previous = {}
    def interrupt(number, frame):
        raise InterruptedError('capture interrupted by signal ' + str(number))
    try:
        for number in (signal.SIGINT, signal.SIGTERM):
            previous[number] = signal.signal(number, interrupt)
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def _cleanup(process):
    from .native_permission_probe import _terminate
    if process is None:
        return {'child_started': False, 'leader_reaped': True, 'group_absent': True}
    _terminate(process)
    deadline = time.monotonic() + 2
    while True:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return {'child_started': True, 'leader_reaped': process.poll() is not None, 'group_absent': True}
        if time.monotonic() >= deadline:
            raise RuntimeError('capture process group remains after cleanup')
        time.sleep(0.01)


def _supervise(invocation, deadline_seconds, outputs, observations, lifecycle):
    process = None
    pending = bytearray()
    line_number = 0
    began = time.monotonic()
    wall = time.time()
    try:
        with selectors.DefaultSelector() as selector:
            process = subprocess.Popen(invocation['argv'], cwd=invocation['cwd'],
                env=invocation['environment'], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, start_new_session=True)
            lifecycle['spawn_count'] = 1
            for name in outputs:
                stream = getattr(process, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() or process.poll() is None:
                if max(time.monotonic() - began, time.time() - wall) >= deadline_seconds:
                    raise TimeoutError('registered capture deadline elapsed')
                for key, _ in selector.select(timeout=0.02):
                    remaining = MAX_STREAM_BYTES - len(outputs[key.data])
                    raw = os.read(key.fd, min(65536, remaining + 1))
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    outputs[key.data].extend(raw[:remaining])
                    if len(raw) > remaining:
                        raise ValueError('capture stream exceeded its registered byte bound')
                    if key.data == 'stdout':
                        pending.extend(raw)
                        while b'\n' in pending:
                            line, _, rest = pending.partition(b'\n')
                            pending = bytearray(rest)
                            line_number += 1
                            if not line.strip():
                                raise ValueError('capture stdout contains a blank JSON line')
                            event = strict_json(bytes(line))
                            if type(event) is not dict:
                                raise ValueError('capture stdout event is not an object')
                            if event.get('type') == 'rate_limit_event':
                                if len(observations) >= MAX_OBSERVATIONS:
                                    raise ValueError('capture observation count exceeds its bound')
                                observations.append({'line': line_number, 'captured_at': _utc(),
                                    'event_sha256': sha(bytes(line)), 'event_json': line.decode()})
            if pending:
                raise ValueError('capture stdout ends with an incomplete JSON line')
            lifecycle['returncode'] = process.returncode
            if process.returncode != 0:
                raise ValueError('registered capture process failed')
            if not observations:
                raise ValueError('capture emitted no rate_limit_event')
    except BaseException as exc:
        lifecycle['first_error'] = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        try:
            try:
                lifecycle['cleanup'] = _cleanup(process)
            except BaseException as exc:
                lifecycle['cleanup_error'] = {'type': type(exc).__name__, 'message': str(exc)}
                if 'first_error' not in lifecycle:
                    raise
        finally:
            if process is not None:
                lifecycle['returncode'] = process.poll()
                for stream in (process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()


def _event(raw, observations, authorized_at):
    if type(observations) is not list or not 0 < len(observations) <= MAX_OBSERVATIONS:
        raise ValueError('capture observations must be a bounded nonempty list')
    lines = raw.splitlines()
    observed = []
    for index, line in enumerate(lines, 1):
        event = strict_json(line)
        if type(event) is not dict:
            raise ValueError('capture stdout event is not an object')
        if event.get('type') == 'rate_limit_event':
            observed.append((index, line))
    if not raw.endswith(b'\n') or not observed or len(observed) != len(observations):
        raise ValueError('capture rate-limit event inventory is incomplete')
    previous = _timestamp(authorized_at)
    for (index, line), item in zip(observed, observations):
        if (type(item) is not dict or set(item) != {'line', 'captured_at', 'event_sha256', 'event_json'}
                or type(item['line']) is not int or item['line'] != index
                or item['event_sha256'] != sha(line) or item['event_json'].encode() != line):
            raise ValueError('captured event differs from its actual stdout line')
        moment = _timestamp(item['captured_at'])
        if moment < previous:
            raise ValueError('capture event chronology precedes word or prior observation')
        previous = moment
    return observations[-1]


def _reservation_raw(directory, request, binding):
    return canonical({'kind': RESERVATION_KIND, 'version': REQUEST_VERSION,
        **binding, 'directory': str(directory), 'max_captures': MAX_CAPTURES,
        'request': request})


def _slot_binding(binding, index, reservation_raw, previous_raw):
    return {**binding, 'capture_index': index,
            'reservation_sha256': sha(reservation_raw),
            'previous_claim_sha256': sha(previous_raw) if previous_raw else None}


def _claim(directory, request, runtime, binding, claimed_at):
    return {'kind': KIND, 'version': VERSION, **binding, 'directory': str(directory),
            'claimed_at': claimed_at, 'count': 1, 'request': request,
            'invocation': _invocation(runtime, directory)}


def _claims(directory, value, statement, word, binding):
    """Validate the bounded immutable reservation/claim journal, without repair.

    A claim with no slot/result is a retained interrupted capture, not a free
    slot. No generation attempt identity is created or consumed by this journal.
    """
    reservation_raw = _reservation_raw(directory, statement['quota_capture'], binding)
    if _read(directory / 'reserve.json', MAX_EVIDENCE_BYTES) != reservation_raw:
        raise ValueError('capture reservation differs from the exact word and bundle')
    allowed = {'reserve.json'} | {f'{prefix}-{index}{suffix}'
        for index in range(1, MAX_CAPTURES + 1)
        for prefix, suffix in (('claim', '.json'), ('capture', ''))}
    names = set()
    for item in directory.iterdir():
        if item.name not in allowed or len(names) >= len(allowed):
            raise ValueError('capture reservation contains unknown evidence entries')
        names.add(item.name)
    claims = []
    previous_time = _timestamp(word['authorized_at'])
    for index in range(1, MAX_CAPTURES + 1):
        slot = directory / f'capture-{index}'
        claim_path = directory / f'claim-{index}.json'
        if os.path.lexists(slot) and not stat.S_ISDIR(slot.lstat().st_mode):
            raise ValueError('capture slot must be a physical directory')
        if not os.path.lexists(claim_path):
            if os.path.lexists(slot) or any(f'claim-{later}.json' in names
                    for later in range(index + 1, MAX_CAPTURES + 1)):
                raise ValueError('capture reservation has a missing claim or claim gap')
            continue
        raw = _read(claim_path, MAX_EVIDENCE_BYTES)
        item = strict_json(raw)
        bound = _slot_binding(binding, index, reservation_raw, claims[-1] if claims else None)
        if (type(item) is not dict or raw != canonical(_claim(slot, statement['quota_capture'],
                value['runtime'], bound, item.get('claimed_at')))):
            raise ValueError('capture claim journal differs from its exact authority')
        moment = _timestamp(item['claimed_at'])
        if moment < previous_time:
            raise ValueError('capture claim journal chronology precedes its authority')
        previous_time = moment
        claims.append(raw)
    return reservation_raw, claims


@contextmanager
def _reserve(directory, value, statement, word, binding):
    """Reserve one durable numbered capture while holding the word's flock."""
    if not os.path.lexists(directory):
        if not directory.parent.is_dir():
            raise ValueError('capture reservation requires an existing physical parent')
        directory.mkdir(mode=0o700)
        _sync(directory.parent)
        _new(directory / 'reserve.json',
             _reservation_raw(directory, statement['quota_capture'], binding))
    if not stat.S_ISDIR(directory.lstat().st_mode):
        raise ValueError('capture reservation must be a physical directory')
    descriptor = os.open(directory / 'reserve.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError('capture reservation must be a bounded regular file')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('another capture holds this word reservation') from exc
        reservation_raw, claims = _claims(directory, value, statement, word, binding)
        if len(claims) >= MAX_CAPTURES:
            raise ValueError('word capture allowance exhausted; all three claims stay spent')
        index = len(claims) + 1
        slot = directory / f'capture-{index}'
        bound = _slot_binding(binding, index, reservation_raw, claims[-1] if claims else None)
        claim = _claim(slot, statement['quota_capture'], value['runtime'], bound, _utc())
        previous_time = strict_json(claims[-1])['claimed_at'] if claims else word['authorized_at']
        if _timestamp(claim['claimed_at']) < _timestamp(previous_time):
            raise ValueError('capture claim time precedes word or previous claim')
        # This root-level record remains even if interruption prevents creating
        # the slot. Every subsequently attempted capture must consume a new index.
        _new(directory / f'claim-{index}.json', canonical(claim))
        slot.mkdir(mode=0o700)
        _sync(directory)
        _new(slot / 'claim.json', canonical(claim))
        yield slot, claim, bound
    finally:
        os.close(descriptor)


def capture_subscription(*, registration_raw, review_bundle_raw, launch_word_raw, directory):
    """Consume the next of three word-bound slots; never overwrite prior evidence."""
    directory = _path(directory)
    authority = _authority(registration_raw, review_bundle_raw, launch_word_raw, directory)
    value, statement, word, binding = authority
    if statement['quota_capture']['kind'] != REQUEST_KIND:
        raise ValueError('historical one-shot capture requests are readback only')
    if _timestamp(_utc()) < _timestamp(word['authorized_at']):
        raise ValueError('capture cannot precede the owner authorization time')
    with _reserve(directory, value, statement, word, binding) as (slot, claim, bound):
        return _perform_capture(slot, claim, bound, authority, directory,
                                registration_raw, review_bundle_raw, launch_word_raw)


def _perform_capture(directory, claim, binding, authority, reservation_directory,
                     registration_raw, review_bundle_raw, launch_word_raw):
    value, statement, word, _ = authority
    request = statement['quota_capture']
    invocation = _invocation(value['runtime'], directory)
    claimed_at = claim['claimed_at']
    outputs = {'stdout': bytearray(), 'stderr': bytearray()}
    observations = []
    lifecycle = {'spawn_count': 0, 'returncode': None, 'cleanup': None}
    result = {'kind': KIND, 'version': VERSION, **binding, 'status': 'failed',
              'claim_sha256': sha(canonical(claim)), 'selected_event': None,
              'basis': BASIS}
    failure = None
    try:
        for name in ('cwd', 'config'):
            (directory / name).mkdir(mode=0o700)
        _sync(directory)
        # Real verification repeats after the durable claim and before spawn.
        again = _authority(registration_raw, review_bundle_raw, launch_word_raw, reservation_directory)
        if canonical(again) != canonical(authority):
            raise ValueError('capture authority changed after claiming the directory')
        _, claims = _claims(reservation_directory, *authority)
        if claims[-1] != canonical(claim) or _read(directory / 'claim.json', MAX_EVIDENCE_BYTES) != claims[-1]:
            raise ValueError('capture reservation changed before spawn')
        with _signals():
            _supervise(invocation, request['deadline_seconds'], outputs, observations, lifecycle)
        result['selected_event'] = _event(bytes(outputs['stdout']), observations, claimed_at)
        _authority(registration_raw, review_bundle_raw, launch_word_raw, reservation_directory)
        result['status'] = 'captured'
    except BaseException as exc:
        failure = exc
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        for name, raw in outputs.items():
            _new(directory / (name + '.jsonl' if name == 'stdout' else name + '.txt'), bytes(raw))
        observations_raw = canonical(observations)
        if len(observations_raw) > MAX_EVIDENCE_BYTES:
            raise ValueError('capture observation evidence exceeds its byte bound')
        _new(directory / 'observations.json', observations_raw)
        result['lifecycle'] = lifecycle
        result['files'] = {name: {'sha256': sha(raw), 'bytes': len(raw)} for name, raw in {
            'stdout.jsonl': bytes(outputs['stdout']), 'stderr.txt': bytes(outputs['stderr']),
            'observations.json': observations_raw}.items()}
        _new(directory / 'capture.json', canonical(result))
    if failure is not None:
        raise failure
    return directory / 'capture.json'


def read_capture(manifest_path, *, registration_raw, review_bundle_raw, launch_word_raw):
    """Offline byte reconstruction; a retained failure never becomes admission."""
    path = _path(manifest_path)
    if path.name != 'capture.json':
        raise ValueError('capture readback requires the fixed manifest path')
    directory = path.parent
    # The request's closed version, not a filename guess, selects historical
    # one-shot readback versus the D115 three-slot journal.
    from .native_launch_review import validate_bundle
    terms = validate_bundle(registration_raw, review_bundle_raw, launch_word_raw)
    root = _path(terms['quota_capture']['directory'])
    value, statement, word, binding = _authority(registration_raw, review_bundle_raw, launch_word_raw, root)
    journal_claim = None
    if statement['quota_capture']['kind'] == REQUEST_KIND:
        reservation_raw, claims = _claims(root, value, statement, word, binding)
        if directory.parent != root or directory.name not in {
                f'capture-{index}' for index in range(1, MAX_CAPTURES + 1)}:
            raise ValueError('capture readback is outside its registered numbered slots')
        index = int(directory.name.rsplit('-', 1)[1])
        if index > len(claims):
            raise ValueError('capture slot has no durable reservation claim')
        binding = _slot_binding(binding, index, reservation_raw, claims[index - 2] if index > 1 else None)
        journal_claim = claims[index - 1]
    elif directory != root:
        raise ValueError('historical capture readback differs from its registered directory')
    result = strict_json(_read(path, MAX_EVIDENCE_BYTES))
    claim_raw = _read(directory / 'claim.json', MAX_EVIDENCE_BYTES)
    claim = strict_json(claim_raw)
    expected_claim = _claim(directory, statement['quota_capture'], value['runtime'], binding,
                            claim.get('claimed_at') if type(claim) is dict else None)
    if (canonical(claim) != canonical(expected_claim)
            or (journal_claim is not None and claim_raw != journal_claim)
            or _timestamp(claim['claimed_at']) < _timestamp(word['authorized_at'])):
        raise ValueError('capture claim differs from the registered authority or chronology')
    if (type(result) is not dict or set(result) != {'kind', 'version', *binding, 'status',
            'claim_sha256', 'selected_event', 'basis', 'lifecycle', 'files'}
            or result['kind'] != KIND or type(result['version']) is not int or result['version'] != VERSION
            or canonical({key: result.get(key) for key in binding}) != canonical(binding)
            or result['basis'] != BASIS
            or result['status'] != 'captured' or result['claim_sha256'] != sha(claim_raw)
            or canonical(result['lifecycle']) != canonical({'spawn_count': 1, 'returncode': 0,
                'cleanup': {'child_started': True, 'leader_reaped': True, 'group_absent': True}})):
        raise ValueError('capture did not complete exactly one process with observed cleanup')
    raw = {name: _read(directory / name, MAX_EVIDENCE_BYTES if name == 'observations.json' else MAX_STREAM_BYTES)
           for name in ('stdout.jsonl', 'stderr.txt', 'observations.json')}
    if canonical(result['files']) != canonical({name: {'sha256': sha(data), 'bytes': len(data)} for name, data in raw.items()}):
        raise ValueError('capture evidence file hashes differ')
    selected = _event(raw['stdout.jsonl'], strict_json(raw['observations.json']), claim['claimed_at'])
    if (canonical(result['selected_event']) != canonical(selected)
            or _timestamp(selected['captured_at']) < _timestamp(claim['claimed_at'])):
        raise ValueError('selected capture event differs from saved stdout or claim chronology')
    return result


def read_capture_for_event(directory, *, registration_raw, review_bundle_raw, launch_word_raw,
                           event_json, event_sha256, captured_at):
    """Join a guard to its exact retained capture, without a mutable latest pointer.

    Failed/incomplete slots stay spent but cannot supply admission evidence. A
    later re-capture does not rewrite the saved event chosen by an earlier guard.
    Freshness and window admission are checked independently by the guard.
    """
    directory = _path(directory)
    authority = _authority(registration_raw, review_bundle_raw, launch_word_raw, directory)
    if authority[1]['quota_capture']['kind'] == LEGACY_REQUEST_KIND:
        paths = [directory / 'capture.json']
    else:
        _, claims = _claims(directory, *authority)
        paths = [directory / f'capture-{index}' / 'capture.json'
                 for index in range(1, len(claims) + 1)]
    expected = {'event_json': event_json, 'event_sha256': event_sha256, 'captured_at': captured_at}
    matches = []
    for path in paths:
        if not os.path.lexists(path):
            continue  # Durable claim retained; interrupted before result capture.
        result = strict_json(_read(path, MAX_EVIDENCE_BYTES))
        selected = result.get('selected_event') if type(result) is dict else None
        if (type(selected) is not dict or any(selected.get(key) != item for key, item in expected.items())):
            continue
        # Matching text alone is never proof: run genuine saved reconstruction.
        matches.append(read_capture(path, registration_raw=registration_raw,
            review_bundle_raw=review_bundle_raw, launch_word_raw=launch_word_raw))
    if len(matches) != 1:
        raise ValueError('guard event does not match exactly one retained registered capture')
    return matches[0]
