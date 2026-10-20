"""#4687: synthetic append schedule and TEST-ONLY owner coordination contract.

These tests intentionally assert the CURRENT reader's refusal, not a production
fix or a reproduction of a hosted kernel race. The small flock harness has no
waiting/retry policy and is not imported by the controller or any live reader.
Only ordinary Python peers, tiny temporary files and explicit barriers are used.
"""
from contextlib import contextmanager
from copy import deepcopy
import errno
import fcntl
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_streams as streams
from data_sheets_schema.native_shared_controller import CallbackAdapter
from data_sheets_schema.native_shared_receipts import _ReceiptCatalogContext


REFUSAL = 'live native stream changed without appending bytes'
LIMIT = 4096
FIRST = b'{"first":1}\n'
GROWN = b'{"second":2}\n'
FUTURE = b'{"future":3}\n'


def prefix(path, raw, role):
    return c.EvidencePrefix(role, str(path), raw, len(raw), c.sha(raw), raw.count(b'\n'))


def try_lock(fd, mode):
    """Test-only, one nonblocking syscall; no contention-to-success fallback."""
    if type(mode) is not int or mode not in (fcntl.LOCK_SH, fcntl.LOCK_EX):
        raise ValueError('test lock mode must be SH or EX')
    try:
        fcntl.flock(fd, mode | fcntl.LOCK_NB)
    except OSError as exc:
        if exc.errno not in (errno.EACCES, errno.EAGAIN):
            raise
        return False
    return True


@contextmanager
def held(fd, mode):
    if not try_lock(fd, mode):
        raise BlockingIOError('test-only sample or append is busy')
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)


def sample(fd, path, *, include_path=False):
    """One protected sample; opening fd/path baseline shares ONE acquisition."""
    with held(fd, fcntl.LOCK_SH):
        before = evidence._stat(path.lstat()) if include_path else None
        opened = evidence._stat(os.fstat(fd))
        if before is not None:
            streams._progress(before, opened, LIMIT)
        return opened


@pytest.mark.parametrize('role', streams.ROLES)
@pytest.mark.parametrize('failed_sample,stage,pass_number,reads', [
    (1, 'opened', None, 0),
    (2, 'before_read', 1, 0),
    (3, 'after_read', 1, 1),
    (4, 'before_read', 2, 1),
    (5, 'after_read', 2, 2),
    (6, 'final_fd', None, 2),
    (7, 'final_path', None, 2),
])
def test_current_reader_refuses_synthetic_timestamp_before_eventual_append(
        tmp_path, monkeypatch, role, failed_sample, stage, pass_number, reads):
    """Real old/grown/later bytes; ONLY the metadata schedule is synthetic."""
    path = tmp_path / (role + '.jsonl')
    path.write_bytes(FIRST)
    previous = prefix(path, FIRST, role)
    with path.open('ab') as writer:
        writer.write(GROWN)
    opened_bytes = FIRST + GROWN
    original_stat, original_read = evidence._stat, os.pread
    opened = original_stat(path.stat())
    samples, read_calls = [], []

    def scheduled(info):
        value = original_stat(info)
        if len(samples) == failed_sample:
            value['mtime_ns'] += 1  # Explicit model, NOT an observed kernel stat.
        samples.append(deepcopy(value))
        return value

    def reading(fd, count, offset):
        read_calls.append((count, offset))
        return original_read(fd, count, offset)

    with monkeypatch.context() as patch:
        patch.setattr(evidence, '_stat', scheduled)
        patch.setattr(streams.os, 'pread', reading)
        with pytest.raises(streams._LiveStreamRefusal, match=REFUSAL) as caught:
            streams.read_live_stream(str(path), role, max_bytes=LIMIT, previous=previous)
    diagnostic = streams.diagnostic_document(caught.value.diagnostic_json)
    assert caught.value.args == (REFUSAL,)
    assert diagnostic['stage'] == stage and diagnostic['pass_number'] == pass_number
    assert diagnostic['offset'] == (len(opened_bytes) if stage in ('after_read', 'final_fd', 'final_path') else 0)
    assert diagnostic['opened_extent'] == (None if stage == 'opened' else len(opened_bytes))
    assert diagnostic['earlier'] == opened
    assert diagnostic['later'] == {**opened, 'mtime_ns': opened['mtime_ns'] + 1}
    assert diagnostic['previous_prefix'] == {'bytes': len(FIRST), 'sha256': c.sha(FIRST)}
    assert diagnostic['earlier']['size'] > previous.bytes
    assert len(samples) == failed_sample + 1 and len(read_calls) == reads
    assert path.read_bytes() == opened_bytes
    # Completing the hypothetical append afterwards cannot credit the refusal.
    with path.open('ab') as writer:
        writer.write(FUTURE)
    assert path.read_bytes() == opened_bytes + FUTURE
    assert path.read_bytes()[:previous.bytes] == previous.raw
    assert streams.diagnostic_document(caught.value.diagnostic_json) == diagnostic


@pytest.mark.parametrize('role', streams.ROLES)
@pytest.mark.parametrize('failed_sample', [3, 4])
def test_synthetic_append_refusal_does_not_commit_either_endpoint_cursor(
        tmp_path, monkeypatch, role, failed_sample):
    adapter = CallbackAdapter.__new__(CallbackAdapter)
    adapter.execution = {'attempt_directory': str(tmp_path)}
    adapter._stream_prefixes, adapter._stream_files = {}, {}
    adapter._receipt_catalogs = _ReceiptCatalogContext()
    for name in streams.ROLES:
        (tmp_path / (name + '.jsonl')).write_bytes(FIRST)
    adapter._observed_endpoint({'first': 1})
    old = deepcopy((adapter._stream_prefixes, adapter._stream_files))
    for name in streams.ROLES:
        with (tmp_path / (name + '.jsonl')).open('ab') as writer:
            writer.write(GROWN)
    target = tmp_path / (role + '.jsonl')
    inode = target.stat().st_ino
    actual_stat, seen = evidence._stat, []

    def scheduled(info):
        value = actual_stat(info)
        if value['inode'] == inode:
            if len(seen) == failed_sample:
                value['mtime_ns'] += 1
            seen.append(deepcopy(value))
        return value

    with monkeypatch.context() as patch:
        patch.setattr(evidence, '_stat', scheduled)
        with pytest.raises(streams._LiveStreamRefusal, match=REFUSAL):
            adapter._observed_endpoint({'second': 2})
    assert (adapter._stream_prefixes, adapter._stream_files) == old
    assert len(seen) == failed_sample + 1
    with target.open('ab') as writer:
        writer.write(FUTURE)
    assert target.read_bytes() == FIRST + GROWN + FUTURE
    assert (adapter._stream_prefixes, adapter._stream_files) == old


@pytest.mark.parametrize('text_writer', [False, True])
def test_writer_lock_excludes_timestamp_then_buffered_append_until_flush(tmp_path, text_writer):
    """utime is a deliberate test barrier, not a proposed production write."""
    path = tmp_path / 'stream.jsonl'
    path.write_bytes(FIRST)
    reader = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = sample(reader, path, include_path=True)
        with path.open('a' if text_writer else 'ab') as writer:
            with held(writer.fileno(), fcntl.LOCK_EX):
                stat = os.fstat(writer.fileno())
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
                intermediate = evidence._stat(os.fstat(reader))
                assert intermediate['size'] == before['size']
                assert intermediate['mtime_ns'] != before['mtime_ns']
                with pytest.raises(ValueError, match=REFUSAL):
                    streams._progress(before, intermediate, LIMIT)
                with pytest.raises(BlockingIOError):
                    sample(reader, path, include_path=True)
                writer.write(GROWN.decode('ascii') if text_writer else GROWN)
                # These tiny writes remain buffered. Releasing before flush
                # would expose the very intermediate state being excluded.
                assert os.fstat(reader).st_size == len(FIRST)
                with pytest.raises(BlockingIOError):
                    sample(reader, path)
                writer.flush()
                assert os.fstat(reader).st_size == len(FIRST + GROWN)
                with pytest.raises(BlockingIOError):
                    sample(reader, path)
        after = sample(reader, path, include_path=True)
        assert streams._progress(before, after, LIMIT) == after
        assert os.pread(reader, LIMIT, 0) == FIRST + GROWN
    finally:
        os.close(reader)


def test_opening_path_and_fd_are_sampled_under_one_shared_lock(tmp_path, monkeypatch):
    path = tmp_path / 'stream.jsonl'
    path.write_bytes(FIRST)
    reader = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    writer = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    original_lstat, original_fstat = Path.lstat, os.fstat
    sampled = []

    def path_stat(selected, *args, **kwargs):
        assert selected == path
        assert not try_lock(writer, fcntl.LOCK_EX)
        sampled.append('path')
        return original_lstat(selected, *args, **kwargs)

    def fd_stat(fd):
        assert fd == reader
        assert not try_lock(writer, fcntl.LOCK_EX)
        sampled.append('fd')
        return original_fstat(fd)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(Path, 'lstat', path_stat)
            patch.setattr(os, 'fstat', fd_stat)
            before = sample(reader, path, include_path=True)
        assert sampled == ['path', 'fd']
        with held(writer, fcntl.LOCK_EX):
            assert os.write(writer, GROWN) == len(GROWN)
        after = sample(reader, path, include_path=True)
        assert streams._progress(before, after, LIMIT) == after
        assert path.read_bytes() == FIRST + GROWN
    finally:
        os.close(writer)
        os.close(reader)


def test_sample_releases_on_failure_and_does_not_convert_io_error_to_contention(tmp_path, monkeypatch):
    path = tmp_path / 'stream.jsonl'
    path.write_bytes(FIRST)
    reader = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    writer = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    try:
        def failed_stat(fd):
            raise OSError(errno.EIO, 'synthetic stat failure')
        with monkeypatch.context() as patch:
            patch.setattr(os, 'fstat', failed_stat)
            with pytest.raises(OSError) as caught:
                sample(reader, path)
            assert caught.value.errno == errno.EIO
        with held(writer, fcntl.LOCK_EX):
            assert os.write(writer, GROWN) == len(GROWN)
    finally:
        os.close(writer)
        os.close(reader)
    with pytest.raises(OSError) as caught:
        try_lock(reader, fcntl.LOCK_SH)
    assert caught.value.errno == errno.EBADF


def test_dup_is_not_an_independent_flock_owner(tmp_path):
    path = tmp_path / 'stream.jsonl'
    path.write_bytes(FIRST)
    reader = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    duplicate = os.dup(reader)
    separate = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    try:
        assert try_lock(reader, fcntl.LOCK_SH)
        assert not try_lock(separate, fcntl.LOCK_EX)
        # An unlock through dup releases the SAME open-file-description lock.
        fcntl.flock(duplicate, fcntl.LOCK_UN)
        assert try_lock(separate, fcntl.LOCK_EX)
        assert not try_lock(reader, fcntl.LOCK_SH)
    finally:
        os.close(separate)
        os.close(duplicate)
        os.close(reader)


def test_per_sample_harness_releases_before_reads_and_keeps_fixed_extent(tmp_path, monkeypatch):
    """Instrument actual reader samples; this is not a new admission route.

    The initial pair's single-acquisition property is tested separately above.
    These hooks test that sample locks do not become whole-snapshot locks.
    """
    path = tmp_path / 'transcript.jsonl'
    path.write_bytes(FIRST + GROWN)
    previous = prefix(path, FIRST, 'transcript')
    reader = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    writer = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    real_fstat, real_lstat, real_read = os.fstat, Path.lstat, os.pread
    seen = []

    def fd_sample(fd):
        with held(fd, fcntl.LOCK_SH):
            assert not try_lock(writer, fcntl.LOCK_EX)
            return real_fstat(fd)

    def path_sample(selected, *args, **kwargs):
        if selected != path:
            return real_lstat(selected, *args, **kwargs)
        with held(reader, fcntl.LOCK_SH):
            assert not try_lock(writer, fcntl.LOCK_EX)
            return real_lstat(selected, *args, **kwargs)

    def reading(fd, count, offset):
        with held(writer, fcntl.LOCK_EX):
            if not seen:
                assert os.write(writer, FUTURE) == len(FUTURE)
        seen.append((count, offset))
        return real_read(fd, count, offset)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, 'fstat', fd_sample)
            patch.setattr(Path, 'lstat', path_sample)
            patch.setattr(os, 'pread', reading)
            captured = streams.read_live_stream(str(path), 'transcript', max_bytes=LIMIT, previous=previous)
        assert captured.captured.raw == FIRST + GROWN
        assert streams.prefix(captured, len(FIRST)) == previous
        assert captured.captured.pin.bytes == len(FIRST + GROWN)
        assert seen == [(len(FIRST + GROWN), 0)] * 2
        assert path.read_bytes() == FIRST + GROWN + FUTURE
        with held(writer, fcntl.LOCK_EX):
            pass  # Final path/fd samples also released their locks.
    finally:
        os.close(writer)
        os.close(reader)


# This peer has no repository imports, network, native executable, fixture
# helper, or caller-supplied code. Its one absolute IPC deadline cannot renew.
PEER = r'''
import errno, fcntl, json, os, select, sys, time
deadline = time.monotonic() + 10
fd = os.open(sys.argv[1], os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW)
locked = False
def reply(value):
    print(json.dumps(value, sort_keys=True), flush=True)
def acquire(mode):
    try:
        fcntl.flock(fd, mode | fcntl.LOCK_NB)
    except OSError as exc:
        if exc.errno not in (errno.EACCES, errno.EAGAIN):
            raise
        return False
    return True
try:
    value = os.fstat(fd)
    reply({'ready': True, 'device': value.st_dev, 'inode': value.st_ino})
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([0], [], [], remaining)[0]:
            raise TimeoutError('ordinary test peer deadline')
        command = os.read(0, 32)
        if command == b'hold\n':
            assert not locked
            locked = acquire(fcntl.LOCK_EX)
            reply({'held': locked})
        elif command == b'append\n':
            assert locked
            raw = b'{"peer":4}\n'
            assert os.write(fd, raw) == len(raw)
            reply({'appended': len(raw)})
        elif command == b'release\n':
            assert locked
            fcntl.flock(fd, fcntl.LOCK_UN)
            locked = False
            reply({'released': True})
        elif command == b'close\n':
            assert not locked
            break
        else:
            raise ValueError('unexpected bounded test peer command')
finally:
    os.close(fd)
'''


@contextmanager
def peer(path):
    """Fixed child, bounded IPC/cleanup, no sleeps or scheduling assumptions."""
    child = subprocess.Popen([sys.executable, '-I', '-B', '-S', '-c', PEER, str(path)],
        cwd=path.parent, env={'LC_ALL': 'C'}, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, bufsize=0)
    deadline = time.monotonic() + 10
    selector = selectors.DefaultSelector()
    selector.register(child.stdout, selectors.EVENT_READ)
    pending = b''

    def receive(command=None):
        nonlocal pending
        if command is not None:
            assert child.stdin.write(command + b'\n') == len(command) + 1
        while b'\n' not in pending:
            remaining = deadline - time.monotonic()
            assert remaining > 0 and selector.select(remaining), 'ordinary peer timed out'
            part = os.read(child.stdout.fileno(), 1024)
            assert part, 'ordinary peer closed its response pipe'
            pending += part
            assert len(pending) <= 4096, 'ordinary peer response exceeded bound'
        line, pending = pending.split(b'\n', 1)
        return json.loads(line)

    try:
        ready = receive()
        selected = path.stat()
        assert ready == {'ready': True, 'device': selected.st_dev, 'inode': selected.st_ino}
        yield receive
        assert child.stdin.write(b'close\n') == 6
        child.stdin.close()
        remaining = deadline - time.monotonic()
        assert remaining > 0
        assert child.wait(timeout=remaining) == 0
        assert child.stderr.read() == b'' and pending == b''
    finally:
        if child.poll() is None:
            try:
                child.kill()
            except ProcessLookupError:
                pass
        child.wait(timeout=5)
        selector.close()
        for pipe in (child.stdin, child.stdout, child.stderr):
            pipe.close()


def test_separately_opened_process_writer_excludes_sample_until_append_finishes(tmp_path):
    path = tmp_path / 'stream.jsonl'
    path.write_bytes(FIRST)
    reader = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = sample(reader, path, include_path=True)
        with peer(path) as request:
            assert request(b'hold') == {'held': True}
            with pytest.raises(BlockingIOError):
                sample(reader, path, include_path=True)
            assert request(b'append') == {'appended': len(b'{"peer":4}\n')}
            with pytest.raises(BlockingIOError):
                sample(reader, path)
            assert request(b'release') == {'released': True}
            after = sample(reader, path, include_path=True)
            assert streams._progress(before, after, LIMIT) == after
            assert path.read_bytes() == FIRST + b'{"peer":4}\n'
    finally:
        os.close(reader)


def test_process_writer_cannot_begin_inside_parent_sample_and_can_proceed_afterward(tmp_path):
    path = tmp_path / 'stream.jsonl'
    path.write_bytes(FIRST)
    reader = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        with peer(path) as request:
            with held(reader, fcntl.LOCK_SH):
                before = evidence._stat(path.lstat())
                assert request(b'hold') == {'held': False}
                opened = evidence._stat(os.fstat(reader))
                assert opened == before and path.read_bytes() == FIRST
            assert request(b'hold') == {'held': True}
            assert request(b'append') == {'appended': len(b'{"peer":4}\n')}
            assert request(b'release') == {'released': True}
            assert streams._progress(opened, sample(reader, path), LIMIT)['size'] > opened['size']
            assert path.read_bytes() == FIRST + b'{"peer":4}\n'
    finally:
        os.close(reader)
