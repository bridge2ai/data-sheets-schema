"""Registration-wide native capture journal, A3, 2026-11-08.

Host filesystem operations only, never a process/provider call. The capture
boundary must first reconstruct the registration and validate its raw bundle
and word. This journal records presentation of a word, not unseen files or
authenticated human identity. Local evidence must not be removed or rewritten.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import math
import os
from pathlib import Path
import stat

from .native_subscription_guard_v2 import canonical, sha, strict_json, _timestamp

PREVIOUS_KIND = 'd4d_native_capture_word_journal_v1'
KIND = 'd4d_native_capture_word_journal_v2'
VERSION = 2
MAX_EVENTS = 4096
MAX_BYTES = 2 * 1024 * 1024
MAX_JOURNAL_BYTES = 16 * 1024 * 1024


def _path(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or path.resolve() != path:
        raise ValueError('capture journal requires canonical physical paths')
    return path


def _sync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _new(path, raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('capture journal entry exceeds its bound')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    _sync(path.parent)


def _read(path):
    path = _path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_BYTES:
            raise ValueError('capture journal requires bounded regular entries')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(MAX_BYTES + 1)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    current = path.lstat()
    if (len(raw) != before.st_size or any(getattr(before, key) != getattr(after, key)
            or getattr(after, key) != getattr(current, key) for key in fields)):
        raise ValueError('capture journal changed while reading')
    return raw


def normalize_direction(value):
    moment = _timestamp(value, 'direction identity')
    return datetime.fromtimestamp(moment, timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _moment(now):
    now = datetime.now(timezone.utc).timestamp() if now is None else now
    if type(now) not in (int, float) or not math.isfinite(now):
        raise ValueError('capture journal requires a finite clock')
    return now, datetime.fromtimestamp(now, timezone.utc).isoformat().replace('+00:00', 'Z')


def _valid(policy, word, now):
    current, stamp = _moment(now)
    start, stop = (_timestamp(policy[key], key) for key in ('valid_from', 'valid_until'))
    authorized = _timestamp(word['authorized_at'], 'authorized_at')
    if not start <= authorized <= current < stop:
        raise ValueError('capture word or current time is outside registration validity')
    return stamp


def validate_window(runtime, word_raw, now=None):
    """Pure validity precheck; the held journal repeats it before activation."""
    from .native_u4b_policy import registered_policy
    return _valid(registered_policy(runtime), strict_json(word_raw), now)


def require_unspent(value):
    if any(os.path.lexists(value[key]) for key in ('attempt_directory', 'evidence_directory')):
        raise ValueError('capture word cannot renew a spent generation reservation')


def observed_primary_limits(terminal_raw, runtime):
    """Extract refusal evidence; extra model entries cannot hide a mismatch.

    This does not establish terminal success. Missing or malformed limits for
    the exact registered model are not evidence of a numerical mismatch.
    """
    event = strict_json(terminal_raw, limit=MAX_BYTES)
    if type(event) is not dict or event.get('type') != 'result':
        raise ValueError('capture requires an explicit terminal result')
    usage = event.get('modelUsage')
    if type(usage) is not dict or runtime['model'] not in usage:
        raise ValueError('capture terminal modelUsage differs from registered model')
    own = usage[runtime['model']]
    if type(own) is not dict:
        raise ValueError('capture terminal modelUsage is malformed')
    limits = {key: own.get(key) for key in ('contextWindow', 'maxOutputTokens')}
    if any(type(value) is not int or value <= 0 for value in limits.values()):
        raise ValueError('capture terminal limits must be explicit positive integers')
    return event, usage, limits


def observed_limits(terminal_raw, runtime):
    """Extract exact singleton-model limits for strict terminal success."""
    event, usage, limits = observed_primary_limits(terminal_raw, runtime)
    if set(usage) != {runtime['model']}:
        raise ValueError('capture terminal modelUsage differs from registered model')
    return event, usage, limits


class Journal:
    """An active lock scope, never serialized or accepted as launch authority."""

    def __init__(self, root, header, runtime, policy, *, historical=False):
        self.root, self.header, self.runtime, self.policy = root, header, runtime, policy
        self.historical = historical

    def events(self):
        names = []
        for path in (self.root / 'events').iterdir():
            if len(names) >= MAX_EVENTS:
                raise ValueError('capture journal event count exceeds its bound')
            names.append(path.name)
        if sorted(names) != [f'{index:06d}.json' for index in range(1, len(names) + 1)]:
            raise ValueError('capture journal has unknown entries or an event gap')
        events, previous, last_time, last_authorized, total = [], None, None, None, 0
        for name in sorted(names):
            raw = _read(self.root / 'events' / name)
            total += len(raw)
            if total > MAX_JOURNAL_BYTES:
                raise ValueError('capture journal byte count exceeds its bound')
            value = strict_json(raw, limit=MAX_BYTES)
            common = {'kind', 'version', 'index', 'previous_sha256', 'header_sha256',
                      'recorded_at', 'type', 'word_sha256'}
            if type(value) is not dict:
                raise ValueError('capture journal event is malformed')
            expected = common | ({'word_raw_json', 'authorized_at', 'review_sha256'}
                if value.get('type') == 'word' else {'terminal_raw_json', 'terminal_sha256',
                    'capture_path', 'registered_limits', 'observed_limits'})
            if value.get('type') == 'sequence_start' and self.header['version'] == VERSION:
                expected = common | {'direction_identity', 'registration_sha256',
                                     'host_confirmed_at', 'packet_directory'}
            if (set(value) != expected or value['kind'] != self.header['kind'] or type(value['version']) is not int
                    or value['version'] != self.header['version'] or type(value['index']) is not int
                    or value['index'] != len(events) + 1 or value['previous_sha256'] != previous
                    or value['header_sha256'] != sha(canonical(self.header))
                    or raw != canonical(value)):
                raise ValueError('capture journal hash chain differs from registered authority')
            moment = _timestamp(value['recorded_at'], 'journal recorded_at')
            if last_time is not None and moment < last_time:
                raise ValueError('capture journal chronology moved backwards')
            if value['type'] == 'word':
                raw_word = value['word_raw_json'].encode()
                word = strict_json(raw_word)
                authorized = _timestamp(word['authorized_at'], 'authorized_at')
                if (value['word_sha256'] != sha(raw_word) or value['authorized_at'] != word['authorized_at']
                        or value['review_sha256'] != word['review_sha256']
                        or word['registration_sha256'] != self.header['registration_sha256']
                        or word['attempt_id'] != self.header['attempt_id']
                        or authorized > moment or (last_authorized is not None and authorized <= last_authorized)
                        or any(event['type'] == 'limits_refusal' for event in events)):
                    raise ValueError('capture journal word binding or chronology differs')
                _valid(self.policy, word, moment)
                last_authorized = authorized
            elif value['type'] == 'limits_refusal':
                if not events or events[-1]['word_sha256'] != value['word_sha256']:
                    raise ValueError('capture limits refusal lacks its active word')
                terminal_raw = value['terminal_raw_json'].encode()
                _, _, limits = observed_primary_limits(terminal_raw, self.runtime)
                expected_root = self.root / 'captures' / value['word_sha256']
                path = _path(value['capture_path'])
                if (value['terminal_sha256'] != sha(terminal_raw)
                        or canonical(value['registered_limits']) != canonical(self.runtime['limits'])
                        or canonical(value['observed_limits']) != canonical(limits)
                        or canonical(limits) == canonical(self.runtime['limits'])
                        or path.parent.parent != expected_root or path.name != 'capture.json'):
                    raise ValueError('capture limits refusal is not an actual bound mismatch')
            elif value['type'] == 'sequence_start' and self.header['version'] == VERSION:
                direction = value['direction_identity']
                confirmation = value['host_confirmed_at']
                if (not events or events[-1]['word_sha256'] != value['word_sha256']
                        or any(row['type'] == 'limits_refusal' for row in events)
                        or value['registration_sha256'] != self.header['registration_sha256']):
                    raise ValueError('sequence start lacks its current recorded word')
                _path(value['packet_directory'])
                if direction is None:
                    if confirmation is not None:
                        raise ValueError('owner start cannot carry a delegated confirmation')
                else:
                    if normalize_direction(direction) != direction:
                        raise ValueError('sequence direction is not normalized UTC')
                    if any(row['type'] == 'sequence_start' and row['direction_identity'] == direction
                           for row in events):
                        raise ValueError('delegated direction already consumed')
                    if any(not 0 <= moment - _timestamp(stamp, 'delegated start') <= 1800
                           for stamp in (direction, confirmation)):
                        raise ValueError('sequence start is outside its delegated window')
            else:
                raise ValueError('unknown capture journal event')
            events.append(value)
            previous, last_time = sha(raw), moment
        return events

    def _append(self, payload, now):
        self._require_current_format()
        events = self.events()
        if len(events) >= MAX_EVENTS:
            raise ValueError('capture journal event count exceeds its bound')
        _, stamp = _moment(now)
        value = {'kind': KIND, 'version': VERSION, 'index': len(events) + 1,
            'previous_sha256': sha(canonical(events[-1])) if events else None,
            'header_sha256': sha(canonical(self.header)), 'recorded_at': stamp, **payload}
        if events and _timestamp(stamp, 'recorded_at') < _timestamp(events[-1]['recorded_at'], 'recorded_at'):
            raise ValueError('capture journal clock moved backwards')
        if sum(len(canonical(row)) for row in events) + len(canonical(value)) > MAX_JOURNAL_BYTES:
            raise ValueError('capture journal byte count exceeds its bound')
        _new(self.root / 'events' / f'{len(events) + 1:06d}.json', canonical(value))
        return value

    def activate(self, word_raw, review_raw, value, now=None):
        self._require_current_format()
        require_unspent(value)
        word = strict_json(word_raw)
        _valid(self.policy, word, now)
        events = self.events()
        if any(row['type'] == 'limits_refusal' for row in events):
            raise ValueError('registration permanently refused by capture limits; new observation and registration required')
        recorded = [row for row in events if row['type'] == 'word']
        if recorded:
            last = recorded[-1]
            if last['word_sha256'] == sha(word_raw):
                return last
            if _timestamp(word['authorized_at'], 'authorized_at') <= _timestamp(last['authorized_at'], 'authorized_at'):
                raise ValueError('capture word is superseded or has ambiguous authorization time')
        return self._append({'type': 'word', 'word_sha256': sha(word_raw),
            'word_raw_json': word_raw.decode(), 'authorized_at': word['authorized_at'],
            'review_sha256': sha(review_raw)}, now)

    def require(self, word_raw, now=None, *, current=True):
        events = self.events()
        selected = [row for row in events if row['type'] == 'word' and row['word_sha256'] == sha(word_raw)]
        if len(selected) != 1:
            raise ValueError('capture word has not been recorded for this registration')
        if current:
            self._require_current_format()
            if any(row['type'] == 'limits_refusal' for row in events):
                raise ValueError('registration permanently refused by capture limits; new observation and registration required')
            if [row for row in events if row['type'] == 'word'][-1]['word_sha256'] != sha(word_raw):
                raise ValueError('capture word is superseded by a newer recorded word')
            _valid(self.policy, strict_json(word_raw), now)
        return selected[0]

    def _require_current_format(self):
        if self.historical or self.header['kind'] != KIND or self.header['version'] != VERSION:
            raise ValueError('historical journal cannot authorize current activity')

    def start(self, word_raw, *, direction, confirmation, packet, now):
        """Append under the caller's word lock; no state initialization or retry."""
        self._require_current_format()
        self.require(word_raw, now)
        identity = None if direction is None else normalize_direction(direction)
        if (direction is None) != (confirmation is None):
            raise ValueError('delegated direction and confirmation must be paired')
        if identity is not None:
            if any(not 0 <= now - _timestamp(stamp, 'delegated start') <= 1800 for stamp in (identity, confirmation)):
                raise ValueError('sequence start is outside its delegated window')
            if any(row['type'] == 'sequence_start' and row['direction_identity'] == identity
                   for row in self.events()):
                raise ValueError('delegated direction already consumed; a new recorded direction is required')
        return self._append({'type': 'sequence_start', 'word_sha256': sha(word_raw),
            'direction_identity': identity, 'host_confirmed_at': confirmation,
            'registration_sha256': self.header['registration_sha256'],
            'packet_directory': str(_path(packet))}, now)

    def refuse_limits(self, word_raw, terminal_raw, capture_path, now=None):
        self._require_current_format()
        self.require(word_raw, now, current=False)
        _, _, limits = observed_primary_limits(terminal_raw, self.runtime)
        if canonical(limits) == canonical(self.runtime['limits']):
            raise ValueError('equal capture limits cannot invalidate a registration')
        return self._append({'type': 'limits_refusal', 'word_sha256': sha(word_raw),
            'terminal_raw_json': terminal_raw.decode(), 'terminal_sha256': sha(terminal_raw),
            'capture_path': str(capture_path), 'registered_limits': self.runtime['limits'],
            'observed_limits': limits}, now)

    def require_start(self, word_raw, expected, now=None):
        """Check the parent's exact current start while holding the capture lock."""
        self.require(word_raw, now)
        if (type(expected) is not dict or set(expected) != {'path', 'sha256'}
                or type(expected['path']) is not str or type(expected['sha256']) is not str):
            raise ValueError('sequence capture requires an exact start-event pin')
        events = self.events()
        event = events[-1]
        path = self.root / 'events' / f"{event['index']:06d}.json"
        if (event['type'] != 'sequence_start' or event['word_sha256'] != sha(word_raw)
                or expected['path'] != str(path) or expected['sha256'] != sha(canonical(event))):
            raise ValueError('sequence capture lacks its matching current start event')
        return event


@contextmanager
def locked(value, registration_raw, *, create=False, historical=False):
    """Lock state after the caller's full raw-authority verification.

    Creation is authorized only for explicit word presentation/capture, never
    readback. Hold this scope across generation reservation to close renewal
    races; do not nest another journal lock within that reservation scope.
    """
    from .native_u4b_policy import registered_policy
    policy = registered_policy(value['runtime'])
    root = _path(policy['capture_state_directory'])
    if historical and create:
        raise ValueError('historical journal access cannot create state')
    header = {'kind': KIND, 'version': VERSION, 'registration_sha256': sha(registration_raw),
        'attempt_id': value['attempt_id'], 'runtime_sha256': sha(canonical(value['runtime'])),
        'policy': policy}
    if not os.path.lexists(root):
        if not create:
            raise ValueError('capture registration has no recorded word state')
        root.mkdir(mode=0o700)
        _sync(root.parent)
        _new(root / 'authority.json', canonical(header))
        (root / 'events').mkdir(mode=0o700)
        (root / 'captures').mkdir(mode=0o700)
        _sync(root)
    names = set()
    for path in root.iterdir():
        if len(names) >= 3:
            raise ValueError('capture state root contains unknown entries')
        names.add(path.name)
    if (not stat.S_ISDIR(root.lstat().st_mode)
            or names != {'authority.json', 'events', 'captures'}
            or any(not stat.S_ISDIR((root / name).lstat().st_mode) for name in ('events', 'captures'))):
        raise ValueError('capture state root is incomplete, aliased or has unknown entries')
    fd = os.open(root / 'authority.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('capture state authority must be a regular file')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('capture registration state is already in use') from exc
        authority_raw = _read(root / 'authority.json')
        supplied = strict_json(authority_raw)
        if type(supplied) is dict and supplied.get('kind') == PREVIOUS_KIND:
            if not historical:
                raise ValueError('historical journal cannot authorize current activity')
            header = {**header, 'kind': PREVIOUS_KIND, 'version': 1}
        if authority_raw != canonical(header):
            raise ValueError('capture state belongs to another registration; use a fresh state directory')
        journal = Journal(root, header, value['runtime'], policy, historical=historical)
        journal.events()
        yield journal
    finally:
        os.close(fd)
