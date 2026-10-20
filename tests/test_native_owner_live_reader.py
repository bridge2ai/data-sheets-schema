"""Actual selected stream reads over synthetic private associations only.

The real captured selection is rebuilt by the binder. This fixture does not
register a public execution, invoke a helper, or claim native acceptance.
"""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import os
from pathlib import Path
import threading
import time

import pytest

from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_owner_runner_v1 as runner
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_selection as selections
from data_sheets_schema import native_shared_streams as streams
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_shared_selection import declaration
from tests.test_native_owner_runner import fixed_clock, selected_controls


def sync_case(case):
    """Rehash fixture joins, preserving raw selection and current source identity.

    Mutants may alter any dictionary first, then call this to make downstream
    hashes honest. No production admission helper is replaced or bypassed.
    """
    composition_raw = c.canonical(case['composition'])
    case['execution']['composition_raw_json'] = composition_raw.decode('utf-8')
    case['execution']['composition_sha256'] = c.sha(composition_raw)
    execution_raw = c.canonical(case['execution'])
    case['started']['registration_sha256'] = c.sha(execution_raw)
    case['started']['composition_sha256'] = c.sha(composition_raw)
    started_raw = c.canonical(case['started'])
    case['owner']['execution_sha256'] = c.sha(execution_raw)
    case['owner']['started_sha256'] = c.sha(started_raw)
    case.update(execution_raw=execution_raw, started_raw=started_raw,
                owner_raw=c.canonical(case['owner']))
    case['owner_path'].write_bytes(case['owner_raw'])
    return case


def bind_case(case, **overrides):
    """Caller owns the actual selected loader and current reader-budget scope."""
    kwargs = {name: case[name] for name in
              ('selection', 'execution_raw', 'started_raw', 'owner_raw', 'budget')}
    kwargs.update(overrides)
    return profile.bind_reader_context(case['profile'], case['controls'], **kwargs)


@contextmanager
def entered_case(case, **overrides):
    budget = overrides.get('budget', case['budget'])
    with coordination.reader_budget(budget):
        with bind_case(case, **overrides) as context:
            yield context


@pytest.fixture
def reader_case(declaration, selected_controls, fixed_clock, tmp_path):
    selection = selections.capture(declaration['registration_path'])
    root = tmp_path.resolve()
    attempt = root / 'reader-attempt'
    attempt.mkdir()
    paths = {role: attempt / (role + '.jsonl') for role in streams.ROLES}
    for role, path in paths.items():
        path.write_bytes(c.canonical({'synthetic_stream': role}) + b'\n')
    identity = authority.dependency_identity(stream_snapshot_profile=1)
    selected_profile = deepcopy(identity['stream_snapshot_profile'])
    composition = {'kind': 'd4d_native_shared_callback_composition', 'version': 1,
        'selection_raw_json': selection.registration.raw.decode('utf-8'),
        'selection_sha256': selection.registration.pin.sha256,
        'working_directory': str(root)}
    execution = {'kind': c.KINDS['execution'], 'version': 1,
        'attempt_id': attempt.name, 'attempt_directory': str(attempt),
        'working_directory': str(root), 'dependencies': identity,
        'selection_sha256': selection.registration.pin.sha256,
        'runtime': {'deadline_seconds': 120}}
    started = {'kind': 'd4d_native_shared_attempt', 'version': 1,
        'state': 'started', 'attempt_id': attempt.name, 'dispatch_limit': 1}
    start = time.monotonic_ns()
    duration = 120_000_000_000
    owner = {'format': 'native_stream_owner_v2',
        'coordination_profile': deepcopy(selected_profile),
        'owner_pid': os.getpid(), 'clock': 'monotonic_ns',
        'start_ns': start, 'deadline_ns': start + duration, 'duration_ns': duration,
        'clock_domain': deepcopy(fixed_clock),
        **{role: {'path': str(path), 'device': path.stat().st_dev,
                  'inode': path.stat().st_ino} for role, path in paths.items()}}
    stop = threading.Event()
    budget = coordination.ReaderBudget(start + duration, (stop,), clock_domain=fixed_clock)
    case = {'root': root, 'attempt': attempt, 'paths': paths,
        'owner_path': attempt / 'stream-owner.json',
        'stop_path': attempt / 'stream-owner-stop.json',
        'selection': selection, 'controls': selected_controls,
        'profile': selected_profile, 'composition': composition,
        'execution': execution, 'started': started, 'owner': owner,
        'budget': budget, 'stop': stop}
    sync_case(case)
    # Validate actual pure owner format before the selected live checks.
    assert runner.validate_owner_record_v2(case['owner']) == case['owner']
    return case


def read_case(case, context, role='transcript', **kwargs):
    options = {'max_bytes': 1_000_000, **kwargs}
    return streams.read_live_stream(str(case['paths'][role]), role,
                                    coordination=context, **options)


@pytest.mark.parametrize('role', streams.ROLES)
def test_selected_real_reader_retains_exact_bytes_and_opened_metadata(reader_case, role):
    case = reader_case
    path = case['paths'][role]
    raw = path.read_bytes()
    before = {p: p.read_bytes() for p in [*case['paths'].values(), case['owner_path']]}
    with entered_case(case) as context:
        member = read_case(case, context, role, max_bytes=len(raw))
        assert member.captured.raw == raw
        assert member.captured.pin == c.ArtifactPin(role, str(path), len(raw), c.sha(raw))
        meta = c.strict_json(member.metadata_json)
        assert {name: meta[name] for name in ('device', 'inode')} == context.identity(role, str(path))
        assert meta['size'] == len(raw)
        assert streams.prefix(member).raw == raw
    assert {p: p.read_bytes() for p in before} == before
    assert not case['stop_path'].exists()


def test_absent_selector_preserves_default_reader_without_owner_context(tmp_path, monkeypatch):
    path = tmp_path.resolve() / 'transcript.jsonl'
    path.write_bytes(b'{"ordinary":true}\n')
    expected = streams.read_live_stream(str(path), 'transcript', max_bytes=100)
    def forbidden(*args, **kwargs):
        pytest.fail('default reader entered selected helper')
    monkeypatch.setattr(streams, '_read_owner_stream', forbidden)
    assert streams.read_live_stream(str(path), 'transcript', max_bytes=100) == expected
    assert streams.read_live_stream(str(path), 'transcript', max_bytes=100, coordination=None) == expected


@pytest.mark.parametrize('value', [False, True, 0, {}, object()])
def test_noncontext_selector_refuses_before_any_file_operation(tmp_path, monkeypatch, value):
    def forbidden(*args, **kwargs):
        pytest.fail('invalid context attempted file access')
    monkeypatch.setattr(os, 'open', forbidden)
    with pytest.raises(ValueError, match='fixed owner reader context'):
        streams.read_live_stream(str(tmp_path.resolve() / 'absent.jsonl'), 'transcript',
                                 max_bytes=100, coordination=value)


def test_waits_for_actual_ex_append_then_takes_one_finite_extent(reader_case, monkeypatch):
    """A deliberately staged utime/write schedule, not a kernel-race claim."""
    case = reader_case
    path = case['paths']['transcript']
    initial, later = path.read_bytes(), b'{"later":true}\n'
    previous = c.EvidencePrefix('transcript', str(path), initial, len(initial),
                                c.sha(initial), initial.count(b'\n'))
    writer_fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    fcntl.flock(writer_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    info = os.fstat(writer_fd)
    os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000_000))
    release = threading.Event()
    failures = []
    def writer():
        try:
            if not release.wait(10):
                raise AssertionError('reader never encountered the held exclusive lease')
            assert os.write(writer_fd, later) == len(later)
            os.fsync(writer_fd)
        except BaseException as error:
            failures.append(error)
        finally:
            fcntl.flock(writer_fd, fcntl.LOCK_UN)
    actual_lease = coordination.try_lease
    contended = []
    def observed_lease(fd, mode):
        result = actual_lease(fd, mode)
        if result is None:
            contended.append(mode)
            release.set()
        return result
    monkeypatch.setattr(coordination, 'try_lease', observed_lease)
    thread = threading.Thread(target=writer)
    thread.start()
    try:
        with entered_case(case) as context:
            member = read_case(case, context, previous=previous)
        assert member.captured.raw == initial + later
        assert streams.prefix(member, len(initial)) == previous
        assert contended and set(contended) == {fcntl.LOCK_SH}
    finally:
        release.set()
        thread.join(10)
        os.close(writer_fd)
    assert not thread.is_alive() and failures == []


@pytest.mark.parametrize('which_pass', [1, 2])
def test_append_between_samples_never_expands_opened_extent(reader_case, monkeypatch, which_pass):
    case = reader_case
    path = case['paths']['transcript']
    initial, later = path.read_bytes(), b'{"future":true}\n'
    actual_read = os.pread
    reads = []
    def reading(fd, count, offset):
        raw = actual_read(fd, count, offset)
        reads.append((count, offset))
        if len(reads) == which_pass:
            writer = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
            try:
                fcntl.flock(writer, fcntl.LOCK_EX | fcntl.LOCK_NB)
                assert os.write(writer, later) == len(later)
            finally:
                os.close(writer)
        return raw
    with entered_case(case) as context:
        with monkeypatch.context() as patch:
            patch.setattr(os, 'pread', reading)
            member = read_case(case, context)
    assert member.captured.raw == initial
    assert c.strict_json(member.metadata_json)['size'] == len(initial)
    assert reads == [(len(initial), 0), (len(initial), 0)]
    assert path.read_bytes() == initial + later


@pytest.mark.parametrize('change', ['rewrite', 'shrink', 'rewrite_append', 'replacement',
                                  'symlink', 'hardlink', 'touch', 'over_bound', 'short_read'])
def test_selected_reader_retains_destructive_change_refusals(reader_case, monkeypatch, change):
    case = reader_case
    path = case['paths']['transcript']
    initial = path.read_bytes()
    previous = c.EvidencePrefix('transcript', str(path), initial, len(initial),
                                c.sha(initial), initial.count(b'\n'))
    limit = len(initial) + 16
    actual_read = os.pread
    calls = []
    def reading(fd, count, offset):
        raw = actual_read(fd, count, offset)
        calls.append((count, offset))
        if len(calls) == 1:
            if change == 'rewrite':
                path.write_bytes(initial.replace(b'transcript', b'TRANSCRIPT'))
            elif change == 'shrink':
                path.write_bytes(initial[:2])
            elif change == 'rewrite_append':
                path.write_bytes(initial.replace(b'transcript', b'TRANSCRIPT') + b'{}\n')
            elif change in ('replacement', 'symlink'):
                retained = path.with_name('retained-original')
                path.rename(retained)
                if change == 'replacement':
                    path.write_bytes(initial)
                else:
                    path.symlink_to(retained)
            elif change == 'hardlink':
                os.link(path, path.with_name('second-link'))
            elif change == 'touch':
                info = path.stat()
                os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000))
            elif change == 'over_bound':
                with path.open('ab') as writer:
                    writer.write(b'x' * limit)
            else:
                return b''
        return raw
    with entered_case(case) as context:
        with monkeypatch.context() as patch:
            patch.setattr(os, 'pread', reading)
            with pytest.raises(ValueError):
                read_case(case, context, max_bytes=limit, previous=previous)
    assert 1 <= len(calls) <= 2
    assert case['owner_path'].read_bytes() == case['owner_raw']


def test_previous_prefix_rewrite_before_open_is_not_credited(reader_case):
    case = reader_case
    path = case['paths']['transcript']
    initial = path.read_bytes()
    previous = c.EvidencePrefix('transcript', str(path), initial, len(initial),
                                c.sha(initial), initial.count(b'\n'))
    path.write_bytes(initial.replace(b'transcript', b'TRANSCRIPT') + b'{}\n')
    with entered_case(case) as context:
        with pytest.raises(ValueError, match='previously observed'):
            read_case(case, context, previous=previous)


def test_selected_fixed_prefix_keeps_incomplete_line_uncredited(reader_case):
    case = reader_case
    path = case['paths']['transcript']
    initial = path.read_bytes()
    path.write_bytes(initial + b'{"partial":')
    with entered_case(case) as context:
        member = read_case(case, context)
        assert member.captured.raw == initial + b'{"partial":'
        assert streams.prefix(member).raw == initial


def test_private_association_does_not_activate_public_execution(reader_case):
    from data_sheets_schema import native_shared_registration as registration
    with entered_case(reader_case) as context:
        assert read_case(reader_case, context).captured.raw
    with pytest.raises(ValueError):
        registration.verified(reader_case['execution_raw'])
