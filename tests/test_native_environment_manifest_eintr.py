"""PR 6302: real census controls for bounded directory EINTR, 2026-11-22.

The installed distribution is synthetic; enumeration uses real filesystem
entries with faults injected at opening or after a counted entry was yielded.
"""
import errno
from pathlib import Path

import pytest

from data_sheets_schema import native_environment_manifest as m
from tests.test_native_environment_manifest import installed  # noqa: F401
from tests.test_native_environment_modes import pin_document


class _ObservedIterator:
    def __init__(self, iterator, error, action):
        self.iterator = iterator
        self.error = error
        self.action = action
        self.yielded = []
        self.counted_entry_yielded = False
        self.closed = False
        self.exit_error = None

    def __enter__(self):
        self.iterator.__enter__()
        return self

    def __iter__(self):
        return self

    def __next__(self):
        if self.error is not None and self.counted_entry_yielded:
            if self.action is not None:
                self.action()
            raise self.error
        entry = next(self.iterator)
        self.yielded.append(entry.name)
        if not entry.name.endswith('.pyc'):
            self.counted_entry_yielded = True
        return entry

    def __exit__(self, kind, error, traceback):
        try:
            return self.iterator.__exit__(kind, error, traceback)
        finally:
            self.closed = True
            self.exit_error = error


class _ScandirFault:
    def __init__(self, original, target, stage, errors, action=None):
        self.original = original
        self.target = target
        self.stage = stage
        self.errors = errors
        self.action = action
        self.attempts = 0
        self.iterators = []

    def __call__(self, path):
        if Path(path) != self.target:
            return self.original(path)
        self.attempts += 1
        error = self.errors[self.attempts - 1] if self.attempts <= len(self.errors) else None
        if error is not None and self.stage == 'open':
            if self.action is not None:
                self.action()
            raise error
        iterator = _ObservedIterator(self.original(path), error, self.action)
        self.iterators.append(iterator)
        return iterator

    def require_closed(self):
        for iterator in self.iterators:
            assert iterator.closed
            assert iterator.exit_error is iterator.error
            with pytest.raises(StopIteration):
                next(iterator.iterator)
            if iterator.error is not None:
                assert sum(not name.endswith('.pyc') for name in iterator.yielded) == 1


def _prepare(installed, tmp_path):
    (installed.root / 'unowned-a.txt').write_bytes(b'a' * 30)
    (installed.root / 'unowned-z.txt').write_bytes(b'z' * 5)
    nested = installed.root / 'nested'
    nested.mkdir()
    (nested / 'source.py').write_bytes(b'unowned\n')
    (installed.root / 'ignored.pyc').write_bytes(b'ignored bytecode')
    value = m.generate()
    pin = pin_document(tmp_path / 'manifest.json', value)
    # file.py, dist-info, RECORD, two loose files, nested, nested/source.py.
    return value, pin, 7


def _exercise(mode, pin):
    return m.generate() if mode == 'full' else m.verify(pin, mode='light')


def _interruptions(count):
    return [InterruptedError(errno.EINTR, 'synthetic directory interruption ' + str(index))
            for index in range(count)]


def test_actual_census_retries_complete_listing_without_duplicate_entries_or_hashing(
        installed, tmp_path, monkeypatch, mode, stage, failures):
    expected, pin, entry_count = _prepare(installed, tmp_path)
    monkeypatch.setattr(m, 'MAX_IMPORT_ENTRIES', entry_count)
    total_bytes = (sum(row['verified_files']['bytes'] for row in expected['distributions'])
                   + sum(row['bytes'] for row in expected['unowned_files']))
    monkeypatch.setattr(m, 'MAX_VERIFIED_BYTES', total_bytes)
    payload_calls, unowned_calls = [], []
    verify_payload, capture_unowned = m._verify_payload, m._capture_unowned_file

    def observed_payload(path, *args):
        assert mode == 'full', 'light census must not hash installed payloads'
        payload_calls.append(Path(path))
        return verify_payload(path, *args)

    def observed_unowned(path):
        assert mode == 'full', 'light census must not hash unowned payloads'
        unowned_calls.append(Path(path))
        return capture_unowned(path)

    monkeypatch.setattr(m, '_verify_payload', observed_payload)
    monkeypatch.setattr(m, '_capture_unowned_file', observed_unowned)
    fault = _ScandirFault(m.os.scandir, installed.root, stage, _interruptions(failures))
    monkeypatch.setattr(m.os, 'scandir', fault)
    assert _exercise(mode, pin) == expected
    assert fault.attempts == failures + 1
    fault.require_closed()
    if mode == 'full':
        assert payload_calls == [installed.root / 'file.py']
        assert unowned_calls == [installed.root / row['path'] for row in expected['unowned_files']]
    else:
        assert payload_calls == unowned_calls == []


test_actual_census_retries_complete_listing_without_duplicate_entries_or_hashing = pytest.mark.parametrize(
    'mode,stage,failures', [(mode, stage, failures) for mode in ('full', 'light')
                          for stage in ('open', 'partial') for failures in (1, 2)]
)(test_actual_census_retries_complete_listing_without_duplicate_entries_or_hashing)


def test_actual_census_exhausts_three_attempts_and_preserves_last_error(
        installed, tmp_path, monkeypatch, mode, stage):
    _, pin, _ = _prepare(installed, tmp_path)
    errors = _interruptions(3)
    fault = _ScandirFault(m.os.scandir, installed.root, stage, errors)
    monkeypatch.setattr(m.os, 'scandir', fault)
    with pytest.raises(ValueError, match='unreadable') as caught:
        _exercise(mode, pin)
    assert caught.value.__cause__ is errors[-1]
    assert fault.attempts == 3
    fault.require_closed()


test_actual_census_exhausts_three_attempts_and_preserves_last_error = pytest.mark.parametrize(
    'mode,stage', [(mode, stage) for mode in ('full', 'light') for stage in ('open', 'partial')]
)(test_actual_census_exhausts_three_attempts_and_preserves_last_error)


def _other_error(kind):
    return {
        'permission': lambda: PermissionError(errno.EACCES, 'synthetic permission denial'),
        'other_oserror': lambda: OSError(errno.EIO, 'synthetic I/O failure'),
        'wrong_errno_interrupted': lambda: InterruptedError(errno.EIO, 'not EINTR'),
        'no_errno_interrupted': lambda: InterruptedError(),
        'operator_stop': lambda: InterruptedError('capture interrupted by signal 2'),
        'keyboard_interrupt': lambda: KeyboardInterrupt('synthetic operator interrupt'),
    }[kind]()


def test_actual_census_never_retries_other_errors_or_operator_stops(
        installed, tmp_path, monkeypatch, mode, stage, kind):
    _, pin, _ = _prepare(installed, tmp_path)
    error = _other_error(kind)
    fault = _ScandirFault(m.os.scandir, installed.root, stage, [error])
    monkeypatch.setattr(m.os, 'scandir', fault)
    if isinstance(error, KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt) as caught:
            _exercise(mode, pin)
        assert caught.value is error
    else:
        with pytest.raises(ValueError, match='unreadable') as caught:
            _exercise(mode, pin)
        assert caught.value.__cause__ is error
    assert fault.attempts == 1
    fault.require_closed()


test_actual_census_never_retries_other_errors_or_operator_stops = pytest.mark.parametrize(
    'mode,stage,kind', [(mode, stage, kind) for mode in ('full', 'light')
                      for stage in ('open', 'partial')
                      for kind in ('permission', 'other_oserror', 'wrong_errno_interrupted',
                                   'no_errno_interrupted', 'operator_stop', 'keyboard_interrupt')]
)(test_actual_census_never_retries_other_errors_or_operator_stops)


def test_retry_preserves_original_directory_snapshot_for_semantically_ignored_mutation(
        installed, tmp_path, monkeypatch, mode, stage):
    expected, pin, _ = _prepare(installed, tmp_path)
    before = installed.root.stat()
    target = installed.root / 'added-during-retry.pyc'

    def add_ignored_bytecode():
        target.write_bytes(b'excluded from every manifest inventory')
        # Make the metadata difference deterministic even on coarse clocks.
        m.os.utime(installed.root, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))

    fault = _ScandirFault(m.os.scandir, installed.root, stage, _interruptions(1), add_ignored_bytecode)
    with monkeypatch.context() as patch:
        patch.setattr(m.os, 'scandir', fault)
        with pytest.raises(ValueError, match='directory changed during environment census'):
            _exercise(mode, pin)
    assert fault.attempts == 2
    fault.require_closed()
    assert target.read_bytes() == b'excluded from every manifest inventory'
    assert m.generate() == expected


test_retry_preserves_original_directory_snapshot_for_semantically_ignored_mutation = pytest.mark.parametrize(
    'mode,stage', [(mode, stage) for mode in ('full', 'light') for stage in ('open', 'partial')]
)(test_retry_preserves_original_directory_snapshot_for_semantically_ignored_mutation)


def test_retried_census_still_enforces_entry_and_aggregate_byte_bounds(
        installed, tmp_path, monkeypatch, mode, bound):
    expected, pin, entry_count = _prepare(installed, tmp_path)
    total_bytes = (sum(row['verified_files']['bytes'] for row in expected['distributions'])
                   + sum(row['bytes'] for row in expected['unowned_files']))

    def tighten_bound():
        # The public light entry point validates the saved document first;
        # tighten here to exercise the live census's own bound after retry.
        name, value = ('MAX_IMPORT_ENTRIES', entry_count - 1) if bound == 'entries' else (
            'MAX_VERIFIED_BYTES', total_bytes - 1)
        monkeypatch.setattr(m, name, value)

    fault = _ScandirFault(m.os.scandir, installed.root, 'partial', _interruptions(1), tighten_bound)
    monkeypatch.setattr(m.os, 'scandir', fault)
    message = 'entry bound' if bound == 'entries' else 'aggregate byte bound'
    with pytest.raises(ValueError, match=message):
        _exercise(mode, pin)
    assert fault.attempts == 2
    fault.require_closed()


test_retried_census_still_enforces_entry_and_aggregate_byte_bounds = pytest.mark.parametrize(
    'mode,bound', [(mode, bound) for mode in ('full', 'light') for bound in ('entries', 'bytes')]
)(test_retried_census_still_enforces_entry_and_aggregate_byte_bounds)


def test_retried_full_census_still_enforces_unowned_file_byte_bound(installed, tmp_path, monkeypatch):
    _, pin, _ = _prepare(installed, tmp_path)
    monkeypatch.setattr(m, 'MAX_PAYLOAD_BYTES', 20)
    fault = _ScandirFault(m.os.scandir, installed.root, 'partial', _interruptions(1))
    monkeypatch.setattr(m.os, 'scandir', fault)
    with pytest.raises(ValueError, match='unowned file.*byte bound'):
        _exercise('full', pin)
    assert fault.attempts == 2
    fault.require_closed()
