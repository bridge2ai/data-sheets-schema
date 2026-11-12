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
from .native_path_identity import overlaps


CAPTURE_PROMPT = 'Reply with OK.'
REQUEST_KIND = 'd4d_native_subscription_capture_request_v3'
PREVIOUS_REQUEST_KIND = 'd4d_native_subscription_capture_request_v2'
LEGACY_REQUEST_KIND = 'd4d_native_subscription_capture_request_v1'
REQUEST_VERSION = 3
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


def _authority_from_value(value, registration_raw, review_bundle_raw, launch_word_raw, directory):
    from .native_launch_review import validate_bundle
    from .native_u4b_runtime import validate_prepared_runtime
    statement = validate_bundle(registration_raw, review_bundle_raw, launch_word_raw)
    runtime = value['runtime']
    validate_prepared_runtime(runtime)
    word = strict_json(launch_word_raw)
    request = statement['quota_capture']
    if (type(request) is not dict or set(request) != REQUEST_KEYS
            or type(request['version']) is not int
            or (request['kind'], request['version']) not in (
                (REQUEST_KIND, REQUEST_VERSION), (PREVIOUS_REQUEST_KIND, 2), (LEGACY_REQUEST_KIND, 1))
            or type(request['count']) is not int
            or request['count'] != (1 if request['version'] == 1 else MAX_CAPTURES)
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
    if request['kind'] == REQUEST_KIND:
        from .native_u4b_policy import registered_policy
        if directory != _path(registered_policy(runtime)['capture_state_directory']):
            raise ValueError('capture directory differs from registered state')
    protected = [ROOT, Path(runtime['executable']['path'])]
    for key in ('attempt_directory', 'evidence_directory', 'composition', 'system_path', 'permission_probe'):
        protected.append(_path(value[key]))
    composition = strict_json(value['composition_raw_json'].encode())
    protected.extend(_path(path) for path in composition['policy']['readonly_lookups']['inputs'])
    protected.extend(_path(path) for path in composition['policy']['readonly_lookups']['output_directories'])
    for other in protected:
        if overlaps(directory, other):
            raise ValueError('capture directory overlaps source, input or attempt reservations')
    binding = {'registration_sha256': sha(registration_raw), 'review_bundle_sha256': sha(review_bundle_raw),
               'launch_word_sha256': sha(launch_word_raw), 'runtime_sha256': sha(canonical(runtime)),
               'request_sha256': sha(canonical(request)), 'attempt_id': value['attempt_id']}
    return value, statement, word, binding


def _authority(registration_raw, review_bundle_raw, launch_word_raw, directory):
    from . import native_shared_registration_orchestration as registration
    value = registration.verified(registration_raw)
    return _authority_from_value(
        value, registration_raw, review_bundle_raw, launch_word_raw, directory)


def _recheck_authority(initial_authority, registration_raw, review_bundle_raw, launch_word_raw, directory):
    from . import native_shared_registration_orchestration as registration
    if type(initial_authority) is not tuple or len(initial_authority) != 4:
        raise ValueError('capture authority recheck requires the initial authority tuple')
    initial_value = initial_authority[0]
    value = registration._recheck_verified(registration_raw, initial_value)
    authority = _authority_from_value(
        value, registration_raw, review_bundle_raw, launch_word_raw, directory)
    if authority != initial_authority:
        raise ValueError('capture authority changed during event lookup')
    return authority


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
    return canonical({'kind': RESERVATION_KIND, 'version': 2,
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
    """Consume the next of three word-bound slots; never overwrite prior evidence.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies serialized registration/review/word
    and a capture path; _authority reconstructs guarded preparation before
    any capture reservation or process.
    """
    directory = _path(directory)
    from .native_launch_review import registration_fields, validate_bundle
    from .native_runtime_profiles import require_production
    require_production(registration_fields(registration_raw)['runtime'])
    validate_bundle(registration_raw, review_bundle_raw, launch_word_raw, require_current=True)
    authority = _authority(registration_raw, review_bundle_raw, launch_word_raw, directory)
    value, statement, word, binding = authority
    if statement['quota_capture']['kind'] != REQUEST_KIND:
        raise ValueError('historical capture requests are readback only')
    if _timestamp(_utc()) < _timestamp(word['authorized_at']):
        raise ValueError('capture cannot precede the owner authorization time')
    from . import native_capture_words as words
    words.validate_window(value['runtime'], launch_word_raw)
    words.require_unspent(value)
    with words.locked(value, registration_raw, create=True) as journal:
        journal.activate(launch_word_raw, review_bundle_raw, value)
        word_directory = directory / 'captures' / sha(launch_word_raw)
        with _reserve(word_directory, value, statement, word, binding) as (slot, claim, bound):
            return _perform_capture(slot, claim, bound, authority, word_directory,
                registration_raw, review_bundle_raw, launch_word_raw, journal)


def _current_authority(registration_raw, review_bundle_raw, launch_word_raw):
    from .native_launch_review import validate_bundle
    statement = validate_bundle(registration_raw, review_bundle_raw, launch_word_raw, require_current=True)
    if statement['quota_capture']['kind'] != REQUEST_KIND:
        raise ValueError('current capture authority requires the registered v3 protocol')
    return _authority(registration_raw, review_bundle_raw, launch_word_raw,
                      statement['quota_capture']['directory'])


def activate_capture_word(*, registration_raw, review_bundle_raw, launch_word_raw, now=None):
    """Record presentation of a word offline; no capture or attempt is started.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies serialized registration/review/word;
    _current_authority calls _authority to reconstruct guarded preparation
    before window checks or journal creation.
    """
    from . import native_capture_words as words
    value, _, _, _ = _current_authority(registration_raw, review_bundle_raw, launch_word_raw)
    words.validate_window(value['runtime'], launch_word_raw, now)
    words.require_unspent(value)
    with words.locked(value, registration_raw, create=True) as journal:
        return journal.activate(launch_word_raw, review_bundle_raw, value, now)


@contextmanager
def capture_admission_lease(*, registration_raw, review_bundle_raw, launch_word_raw, now=None,
                            guard_raw=None):
    """Hold current-word/refusal state stable through generation reservation.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies serialized registration/review/word;
    _current_authority reconstructs guarded preparation before locking or
    yielding current-word authority.

    When current execution supplies guard_raw, recheck its recorded selection
    inside the held lock. A word-only lease remains useful for current-word
    checks but is not a substitute for the engine's capture/guard admission.
    """
    from . import native_capture_words as words
    authority = _current_authority(registration_raw, review_bundle_raw, launch_word_raw)
    value = authority[0]
    with words.locked(value, registration_raw) as journal:
        current = journal.require(launch_word_raw, now)
        if guard_raw is not None:
            _require_latest_guard_claim(guard_raw, authority, journal, launch_word_raw)
        yield current


def _checked_claim_selection(root, authority, index):
    """Compare the index with the actual journal under its caller's word lock."""
    _, claims = _claims(root, *authority)
    if type(index) is not int or not 1 <= index <= MAX_CAPTURES or index != len(claims):
        raise ValueError('subscription guard must use the last claimed capture under the word')
    return {'capture_index': index, 'capture_claim_count': len(claims)}


def _require_latest_guard_claim(guard_raw, authority, journal, launch_word_raw):
    """Recheck a current guard inside the already-held reservation word lock.

    The caller has reconstructed authority with _current_authority, acquired
    words.locked and required the current word. Never reacquire that lock here.
    The guard's event is independently reconstructed by the current admission
    join; these numbers cannot provide that authority or consume an attempt.
    """
    from .native_subscription_guard_v2 import capture_selection
    selected = capture_selection(strict_json(guard_raw), required=True)
    root = _path(authority[1]['quota_capture']['directory'])
    if (journal.root != root or journal.header['registration_sha256'] != authority[3]['registration_sha256']
            or authority[3]['launch_word_sha256'] != sha(launch_word_raw)):
        raise ValueError('capture selection differs from the held registration authority')
    checked = _checked_claim_selection(root / 'captures' / sha(launch_word_raw),
                                       authority, selected['capture_index'])
    if selected != checked:
        raise ValueError('subscription guard capture selection differs from the current claim count')
    return checked


@contextmanager
def current_guard_preparation(manifest_path, *, registration_raw, review_bundle_raw, launch_word_raw):
    """Prepare current guard bytes while retaining the word lock through publication.

    RunSpec boundary: validated-caller

    RunSpec precondition: Serialized registration/review/word and a manifest path
    are inputs only; _current_authority reconstructs guarded preparation before
    the lock, claim reconstruction or guard construction. The caller writes the
    returned bytes inside this scope. No capture or generation claim is made.
    """
    from . import native_capture_words as words
    from . import native_subscription_guard_v2 as guard
    path, directory, root = _capture_manifest_root(
        manifest_path, registration_raw, review_bundle_raw, launch_word_raw)
    authority = _current_authority(registration_raw, review_bundle_raw, launch_word_raw)
    value, statement, _, _ = authority
    if root != _path(statement['quota_capture']['directory']):
        raise ValueError('guard capture root differs from reconstructed authority')
    with words.locked(value, registration_raw) as journal:
        journal.require(launch_word_raw)
        capture_root = root / 'captures' / sha(launch_word_raw)
        saved = _read_capture_records_at_root(path, directory, authority, capture_root,
                                             require_latest=True)
        selection = _checked_claim_selection(capture_root, authority, saved['capture_index'])
        event = saved['selected_event']
        yield guard.prepare_guard(registration_raw=registration_raw, runtime=value['runtime'],
            launch_word_raw=launch_word_raw, event_raw=event['event_json'].encode(),
            captured_at=event['captured_at'], owner_statement=statement,
            maximum_starting_utilization=statement['max_starting_weekly_utilization'],
            max_age_seconds=statement['max_age_seconds'], **selection)


def require_current_capture_authority(*, registration_raw, review_bundle_raw, launch_word_raw, now=None):
    """Current admission check; historical readback must not call this gate.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies serialized registration/review/word;
    capture_admission_lease reconstructs guarded preparation before returning
    current authority.
    """
    with capture_admission_lease(registration_raw=registration_raw, review_bundle_raw=review_bundle_raw,
            launch_word_raw=launch_word_raw, now=now) as current:
        return current


def _terminal(raw, runtime):
    from .native_capture_words import observed_limits
    lines = raw.splitlines()
    found = [(index, line) for index, line in enumerate(lines, 1)
             if type(event := strict_json(line)) is dict and event.get('type') == 'result']
    if len(found) != 1 or found[0][0] != len(lines) or not raw.endswith(b'\n'):
        raise ValueError('capture requires exactly one final terminal result')
    index, line = found[0]
    event, usage, limits = observed_limits(line, runtime)
    return {'line': index, 'terminal_json': line.decode(), 'terminal_sha256': sha(line),
        'result': event, 'modelUsage': usage, 'observed_limits': limits,
        'registered_limits': runtime['limits'],
        'limits_match': canonical(limits) == canonical(runtime['limits'])}


def _observed_limits_mismatch(raw, runtime):
    """Refusal evidence only: invalid surrounding lines cannot hide a mismatch.

    The stream has already been byte-bounded by the supervisor. A valid result
    object can permanently refuse the registration even in an otherwise failed
    or ambiguous transcript. This scan never establishes capture success.
    """
    from .native_capture_words import observed_primary_limits
    for index, line in enumerate(raw.splitlines(), 1):
        try:
            event, usage, limits = observed_primary_limits(line, runtime)
        except ValueError:
            continue
        if canonical(limits) != canonical(runtime['limits']):
            return {'line': index, 'terminal_json': line.decode(), 'terminal_sha256': sha(line),
                'result': event, 'modelUsage': usage, 'observed_limits': limits,
                'registered_limits': runtime['limits'], 'limits_match': False}
    return None


def _perform_capture(directory, claim, binding, authority, reservation_directory,
                     registration_raw, review_bundle_raw, launch_word_raw, journal):
    value, statement, word, _ = authority
    request = statement['quota_capture']
    invocation = _invocation(value['runtime'], directory)
    claimed_at = claim['claimed_at']
    outputs = {'stdout': bytearray(), 'stderr': bytearray()}
    observations = []
    lifecycle = {'spawn_count': 0, 'returncode': None, 'cleanup': None}
    result = {'kind': KIND, 'version': VERSION, **binding, 'status': 'failed',
              'claim_sha256': sha(canonical(claim)), 'selected_event': None,
              'terminal': None, 'basis': BASIS}
    failure = None
    try:
        for name in ('cwd', 'config'):
            (directory / name).mkdir(mode=0o700)
        _sync(directory)
        # Real verification repeats after the durable claim and before spawn.
        again = _authority(registration_raw, review_bundle_raw, launch_word_raw, request['directory'])
        if canonical(again) != canonical(authority):
            raise ValueError('capture authority changed after claiming the directory')
        _, claims = _claims(reservation_directory, *authority)
        if claims[-1] != canonical(claim) or _read(directory / 'claim.json', MAX_EVIDENCE_BYTES) != claims[-1]:
            raise ValueError('capture reservation changed before spawn')
        with _signals():
            _supervise(invocation, request['deadline_seconds'], outputs, observations, lifecycle)
        result['selected_event'] = _event(bytes(outputs['stdout']), observations, claimed_at)
        _authority(registration_raw, review_bundle_raw, launch_word_raw, request['directory'])
        result['status'] = 'captured'
    except BaseException as exc:
        failure = exc
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        try:
            mismatch = _observed_limits_mismatch(bytes(outputs['stdout']), value['runtime'])
            if mismatch is not None:
                result['terminal'] = mismatch
                journal.refuse_limits(launch_word_raw, mismatch['terminal_json'].encode(),
                                      directory / 'capture.json')
                raise ValueError('capture limits differ; registration permanently refused; new observation and registration required')
            terminal = result['terminal'] = _terminal(bytes(outputs['stdout']), value['runtime'])
            if not terminal['limits_match']:
                journal.refuse_limits(launch_word_raw, terminal['terminal_json'].encode(),
                                      directory / 'capture.json')
                raise ValueError('capture limits differ; registration permanently refused; new observation and registration required')
            if terminal['result'].get('is_error') is not False or terminal['result'].get('subtype') != 'success':
                raise ValueError('capture terminal does not report successful completion')
        except BaseException as exc:
            result['status'] = 'failed'
            result['terminal_error'] = {'type': type(exc).__name__, 'message': str(exc)}
            if failure is None:
                failure = exc
                result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
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


def _read_root(authority, registration_raw, launch_word_raw, require_current):
    if type(require_current) is not bool:
        raise ValueError('capture readback current selection must be boolean')
    value, statement, _, _ = authority
    root = _path(statement['quota_capture']['directory'])
    if statement['quota_capture']['kind'] == REQUEST_KIND:
        from . import native_capture_words as words
        with words.locked(value, registration_raw) as journal:
            journal.require(launch_word_raw, current=require_current)
        return root / 'captures' / sha(launch_word_raw)
    if require_current:
        raise ValueError('historical capture cannot provide current admission')
    return root


def _capture_manifest_root(manifest_path, registration_raw, review_bundle_raw, launch_word_raw):
    path = _path(manifest_path)
    if path.name != 'capture.json':
        raise ValueError('capture readback requires the fixed manifest path')
    directory = path.parent
    # The request's closed version, not a filename guess, selects historical
    # one-shot readback versus the D115 three-slot journal.
    from .native_launch_review import validate_bundle
    terms = validate_bundle(registration_raw, review_bundle_raw, launch_word_raw)
    root = _path(terms['quota_capture']['directory'])
    return path, directory, root


def _read_capture_records(path, directory, authority, *, registration_raw, launch_word_raw,
                          require_current):
    root = _read_root(authority, registration_raw, launch_word_raw, require_current)
    return _read_capture_records_at_root(path, directory, authority, root,
                                         require_latest=require_current)


def _read_capture_records_at_root(path, directory, authority, root, *, require_latest=False):
    """Reconstruct saved bytes after the caller validates the word/root authority.

    Current guard preparation holds words.locked across this call and guard
    publication. Ordinary historical readers first resolve _read_root; current
    execution independently repeats latest selection under its reservation lock.
    """
    value, statement, word, binding = authority
    journal_claim = None
    if statement['quota_capture']['kind'] in (REQUEST_KIND, PREVIOUS_REQUEST_KIND):
        reservation_raw, claims = _claims(root, value, statement, word, binding)
        if directory.parent != root or directory.name not in {
                f'capture-{index}' for index in range(1, MAX_CAPTURES + 1)}:
            raise ValueError('capture readback is outside its registered numbered slots')
        index = int(directory.name.rsplit('-', 1)[1])
        if index > len(claims):
            raise ValueError('capture slot has no durable reservation claim')
        if require_latest and index != len(claims):
            raise ValueError('subscription guard must use the last claimed capture under the word')
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
    result_keys = {'kind', 'version', *binding, 'status', 'claim_sha256', 'selected_event',
                   'basis', 'lifecycle', 'files'}
    if statement['quota_capture']['kind'] == REQUEST_KIND:
        result_keys.add('terminal')
    if (type(result) is not dict or set(result) != result_keys
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
    if statement['quota_capture']['kind'] == REQUEST_KIND:
        terminal = _terminal(raw['stdout.jsonl'], value['runtime'])
        if (canonical(result['terminal']) != canonical(terminal) or not terminal['limits_match']
                or terminal['result'].get('is_error') is not False
                or terminal['result'].get('subtype') != 'success'):
            raise ValueError('saved capture terminal limits or result differ from registration')
    return result


def _read_capture_with_authority(manifest_path, initial_authority, *, registration_raw,
                                 review_bundle_raw, launch_word_raw, require_current=False):
    path, directory, root = _capture_manifest_root(
        manifest_path, registration_raw, review_bundle_raw, launch_word_raw)
    authority = _recheck_authority(
        initial_authority, registration_raw, review_bundle_raw, launch_word_raw, root)
    return _read_capture_records(
        path, directory, authority,
        registration_raw=registration_raw, launch_word_raw=launch_word_raw,
        require_current=require_current)


def read_capture(manifest_path, *, registration_raw, review_bundle_raw, launch_word_raw,
                 require_current=False):
    """Offline byte reconstruction; a retained failure never becomes admission.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies a saved manifest path and serialized
    authorities; _authority reconstructs guarded preparation before reading
    claims/results and comparing saved capture bytes.
    """
    path, directory, root = _capture_manifest_root(
        manifest_path, registration_raw, review_bundle_raw, launch_word_raw)
    authority = (_current_authority(registration_raw, review_bundle_raw, launch_word_raw)
                 if require_current else
                 _authority(registration_raw, review_bundle_raw, launch_word_raw, root))
    return _read_capture_records(
        path, directory, authority,
        registration_raw=registration_raw, launch_word_raw=launch_word_raw,
        require_current=require_current)


def read_capture_for_event(directory, *, registration_raw, review_bundle_raw, launch_word_raw,
                           event_json, event_sha256, captured_at, require_current=False):
    """Join a guard to its exact retained capture, without a mutable latest pointer.

    Failed/incomplete slots stay spent but cannot supply admission evidence.
    Historical lookup preserves the event chosen by an earlier guard; current
    lookup additionally requires the last claimed slot, including failed claims.
    Freshness and window admission are checked independently by the guard.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies a capture directory, serialized
    authorities and exact event identity; _authority reconstructs guarded
    preparation before inspecting numbered slots, and each matching slot is
    checked by read_capture.
    """
    directory = _path(directory)
    authority = (_current_authority(registration_raw, review_bundle_raw, launch_word_raw)
                 if require_current else
                 _authority(registration_raw, review_bundle_raw, launch_word_raw, directory))
    if directory != _path(authority[1]['quota_capture']['directory']):
        raise ValueError('capture directory differs from the owner statement')
    directory = _read_root(authority, registration_raw, launch_word_raw, require_current)
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
        matches.append(_read_capture_with_authority(
            path, authority, registration_raw=registration_raw,
            review_bundle_raw=review_bundle_raw, launch_word_raw=launch_word_raw,
            require_current=require_current))
    if len(matches) != 1:
        raise ValueError('guard event does not match exactly one retained registered capture')
    return matches[0]
