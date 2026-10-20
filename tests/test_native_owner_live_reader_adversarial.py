"""Selected reader boundaries using real captured fixtures and local file locks.

The inherited clock backend is explicitly invented. No helper, native executable,
provider, public permission or execution registration is exercised here.
"""
from contextvars import copy_context
from copy import deepcopy
from dataclasses import replace
import errno
import fcntl
import os
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_shared_selection as selections
from data_sheets_schema import native_shared_streams as streams
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_owner_live_reader import (
    bind_case, declaration, entered_case, fixed_clock, read_case, reader_case,
    selected_controls, sync_case,
)


def forbidden(*args, **kwargs):
    raise AssertionError('this selected refusal must precede stream I/O')


@pytest.mark.parametrize('document', ['composition', 'execution', 'started'])
@pytest.mark.parametrize('field,value', [('kind', 'foreign-kind'), ('version', 0), ('version', True)])
def test_wrong_document_kind_or_exact_version_refuses_after_honest_rehash(reader_case, document, field, value):
    case = reader_case
    case[document][field] = value
    sync_case(case)
    with pytest.raises(ValueError):
        with entered_case(case):
            pytest.fail('wrong document kind/version reached an active reader')


@pytest.mark.parametrize('document', ['composition', 'execution'])
def test_recognized_selection_hash_cannot_contradict_unchanged_embedded_bytes(reader_case, document):
    case = reader_case
    raw = case['selection'].registration.raw
    case[document]['selection_sha256'] = '0' * 64
    sync_case(case)
    assert case['composition']['selection_raw_json'].encode() == raw
    with pytest.raises(ValueError):
        with entered_case(case):
            pytest.fail('contradictory selection digest was ignored')


@pytest.mark.parametrize('change', ['started_state', 'dispatch_bool', 'attempt_id', 'duration_bool',
                                     'different_duration', 'dependency_identity'])
def test_closed_association_does_not_ignore_conflicting_declarations(reader_case, change):
    case = reader_case
    if change == 'started_state': case['started']['state'] = 'finished'
    elif change == 'dispatch_bool': case['started']['dispatch_limit'] = True
    elif change == 'attempt_id': case['started']['attempt_id'] = 'another-attempt'
    elif change == 'duration_bool': case['execution']['runtime']['deadline_seconds'] = True
    elif change == 'different_duration': case['execution']['runtime']['deadline_seconds'] += 1
    else: case['execution']['dependencies']['unexpected_declared_authority'] = 'not selected'
    sync_case(case)
    with pytest.raises(ValueError):
        with entered_case(case):
            pytest.fail('conflicting exact association reached a reader')


@pytest.mark.parametrize('change', ['missing_authority', 'changed_projected_bound'])
def test_actual_capture_type_does_not_bypass_complete_reconstruction(reader_case, change):
    case = reader_case
    selected = case['selection']
    if change == 'missing_authority':
        assert selected.authority
        selected = replace(selected, authority=selected.authority[:-1])
    else:
        selected = deepcopy(selected)
        bounds = selected.bounds()
        bounds['max_submissions'] -= 1
        # The exact carrier type alone cannot certify caller-forged projections.
        object.__setattr__(selected, 'bounds_json', c.canonical(bounds))
    with pytest.raises(ValueError):
        with entered_case(case, selection=selected):
            pytest.fail('unreconstructed selection projection was consumed')


@pytest.mark.parametrize('change', ['replace_equal_bytes', 'different_bytes', 'hardlink', 'symlink', 'missing'])
def test_actual_owner_cannot_change_after_context_entry(reader_case, change):
    case = reader_case
    original = RuntimeError('preserve body failure over changed-owner exit')
    with pytest.raises(RuntimeError) as caught:
        with entered_case(case) as context:
            path = case['owner_path']
            raw = path.read_bytes()
            if change == 'replace_equal_bytes':
                path.rename(case['root'] / 'retained-owner')
                path.write_bytes(raw)
            elif change == 'different_bytes': path.write_bytes(raw + b' ')
            elif change == 'hardlink': os.link(path, case['root'] / 'owner-second-link')
            elif change == 'symlink':
                retained = case['root'] / 'retained-owner'
                path.rename(retained)
                path.symlink_to(retained)
            else: path.unlink()
            with pytest.raises((ValueError, OSError)):
                read_case(case, context)
            with pytest.raises((ValueError, OSError)):
                context.require_current()
            raise original
    assert caught.value is original


@pytest.mark.parametrize('role', ['transcript', 'control'])
def test_every_compared_metadata_sample_holds_sh_and_both_byte_passes_release_it(reader_case, monkeypatch, role):
    case = reader_case
    target = case['paths'][role]
    expected = target.read_bytes()
    writer = os.open(target, os.O_WRONLY | os.O_APPEND)
    observed = {'reader': None, 'fd_samples': 0, 'path_samples': 0, 'reads': 0}
    opening, closing, fstat, lstat, pread = os.open, os.close, os.fstat, Path.lstat, os.pread

    def blocked_writer():
        try:
            fcntl.flock(writer, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            assert error.errno in (errno.EACCES, errno.EAGAIN)
            return
        fcntl.flock(writer, fcntl.LOCK_UN)
        pytest.fail('compared stream metadata was sampled outside an SH lease')

    def tracked_open(path, flags, *args, **kwargs):
        fd = opening(path, flags, *args, **kwargs)
        if str(path) == str(target):
            assert observed['reader'] is None
            observed['reader'] = fd
        return fd

    def fd_sample(fd):
        if fd == observed['reader']:
            blocked_writer(); observed['fd_samples'] += 1
        return fstat(fd)

    def tracked_close(fd):
        if fd == observed['reader']:
            observed['reader'] = None
        return closing(fd)

    def path_sample(path, *args, **kwargs):
        if path == target:
            blocked_writer(); observed['path_samples'] += 1
        return lstat(path, *args, **kwargs)

    def reading(fd, count, offset):
        if fd == observed['reader']:
            # A separately opened writer can lock while either pread executes.
            fcntl.flock(writer, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                observed['reads'] += 1
                return pread(fd, count, offset)
            finally:
                fcntl.flock(writer, fcntl.LOCK_UN)
        return pread(fd, count, offset)

    try:
        with entered_case(case) as context:
            with monkeypatch.context() as patch:
                patch.setattr(os, 'open', tracked_open)
                patch.setattr(os, 'close', tracked_close)
                patch.setattr(os, 'fstat', fd_sample)
                patch.setattr(Path, 'lstat', path_sample)
                patch.setattr(os, 'pread', reading)
                result = read_case(case, context, role)
        assert result.captured.raw == expected
        assert observed['fd_samples'] >= 6 and observed['path_samples'] >= 2
        assert observed['reads'] == 2
        assert target.read_bytes() == expected
    finally:
        os.close(writer)


def test_stop_during_real_ex_contention_refuses_before_metadata_or_bytes(reader_case, monkeypatch):
    case = reader_case
    path = case['paths']['transcript']
    writer = os.open(path, os.O_WRONLY | os.O_APPEND)
    fcntl.flock(writer, fcntl.LOCK_EX | fcntl.LOCK_NB)
    waiting = threading.Event()
    original_wait = coordination.ReaderBudget.wait
    waits = []

    def wait(budget):
        if waits and case['stop_path'].exists():
            pytest.fail('selected SH loop waited again after a visible stop')
        waits.append(budget.deadline_ns)
        waiting.set()
        return original_wait(budget)

    def publish_stop():
        assert waiting.wait(2), 'the actual SH attempt must observe writer contention'
        case['stop_path'].write_bytes(b'not even a valid marker')

    publisher = threading.Thread(target=publish_stop)
    try:
        with pytest.raises(ValueError):
            with entered_case(case) as context:
                publisher.start()
                with monkeypatch.context() as patch:
                    patch.setattr(coordination.ReaderBudget, 'wait', wait)
                    patch.setattr(os, 'pread', forbidden)
                    read_case(case, context)
        publisher.join(2)
        assert not publisher.is_alive()
        assert waits and set(waits) == {case['budget'].deadline_ns}
        assert time.monotonic_ns() < case['budget'].deadline_ns
        assert case['stop_path'].read_bytes() == b'not even a valid marker'
    finally:
        fcntl.flock(writer, fcntl.LOCK_UN)
        os.close(writer)
        if publisher.ident is not None:
            publisher.join(2)


@pytest.mark.parametrize('change', ['empty', 'malformed', 'symlink'])
def test_stop_appearing_during_first_pass_prevents_return(reader_case, monkeypatch, change):
    case = reader_case
    original = os.pread
    calls = []

    def reading(fd, count, offset):
        raw = original(fd, count, offset)
        calls.append((count, offset))
        if len(calls) == 1:
            if change == 'symlink': case['stop_path'].symlink_to(case['root'] / 'absent-target')
            else: case['stop_path'].write_bytes(b'' if change == 'empty' else b'[]')
        return raw

    with pytest.raises(ValueError):
        with entered_case(case) as context:
            with monkeypatch.context() as patch:
                patch.setattr(os, 'pread', reading)
                read_case(case, context)
    assert len(calls) == 1


@pytest.mark.parametrize('change', ['stop', 'deadline'])
def test_final_result_hashing_cannot_bypass_last_admission_check(reader_case, monkeypatch, change):
    case = reader_case
    raw = case['paths']['transcript'].read_bytes()
    digest = c.sha
    now = [time.monotonic_ns()]
    hashes = []

    def hashing(value):
        result = digest(value)
        if value == raw:
            hashes.append(result)
            if change == 'stop': case['stop_path'].write_bytes(b'appeared during final hash')
            else: now[0] = case['budget'].deadline_ns
        return result

    with pytest.raises(ValueError):
        with entered_case(case) as context:
            with monkeypatch.context() as patch:
                patch.setattr(c, 'sha', hashing)
                patch.setattr(coordination, 'time', SimpleNamespace(monotonic_ns=lambda: now[0]))
                read_case(case, context)
    assert hashes, 'the refusal must exercise actual result construction'


def test_selected_declared_evidence_bound_rejects_larger_read_request_before_open(reader_case, monkeypatch):
    case = reader_case
    original = case['selection']
    declaration = original.document()
    declaration['bounds']['max_evidence_bytes'] = c.HARD_LIMITS['finalization_reserve_raw_bytes'] + 1
    raw = c.canonical(declaration)
    registration = c.CapturedArtifact(c.ArtifactPin('selection', original.registration.pin.path,
        len(raw), c.sha(raw)), raw)
    case['selection'] = selections.rebuild(registration, original.authority, original.schemas,
        original.receipt_policy)
    case['composition']['selection_raw_json'] = raw.decode('utf-8')
    case['composition']['selection_sha256'] = case['execution']['selection_sha256'] = c.sha(raw)
    sync_case(case)
    maximum = case['selection'].bounds()['max_evidence_bytes']
    assert maximum < c.HARD_LIMITS['stream_bytes']
    original_open = os.open
    attempts = []

    def opening(path, flags, *args, **kwargs):
        if str(path) == str(case['paths']['transcript']):
            attempts.append(str(path))
            pytest.fail('an over-bound selected request opened its stream')
        return original_open(path, flags, *args, **kwargs)

    with entered_case(case) as context:
        with monkeypatch.context() as patch:
            patch.setattr(os, 'open', opening)
            with pytest.raises(ValueError):
                read_case(case, context, max_bytes=maximum + 1)
    assert attempts == []


def test_contended_reader_uses_shorter_budget_and_never_renews_owner_deadline(reader_case, monkeypatch):
    case = reader_case
    deadline = case['owner']['start_ns'] + 60_000_000_000
    budget = coordination.ReaderBudget(deadline, (case['stop'],), clock_domain=case['budget'].clock_domain())
    writer = os.open(case['paths']['transcript'], os.O_WRONLY)
    fcntl.flock(writer, fcntl.LOCK_EX | fcntl.LOCK_NB)
    now = [deadline - 1]
    original_wait = coordination.ReaderBudget.wait
    seen = []

    def wait(selected):
        seen.append(selected)
        now[0] = deadline
        return original_wait(selected)

    try:
        with pytest.raises(ValueError, match='deadline'):
            with entered_case(case, budget=budget) as context:
                with monkeypatch.context() as patch:
                    patch.setattr(coordination, 'time', SimpleNamespace(monotonic_ns=lambda: now[0]))
                    patch.setattr(coordination.ReaderBudget, 'wait', wait)
                    patch.setattr(os, 'pread', forbidden)
                    read_case(case, context)
        assert seen == [budget]
        assert budget.deadline_ns == deadline < case['owner']['deadline_ns']
    finally:
        fcntl.flock(writer, fcntl.LOCK_UN)
        os.close(writer)


@pytest.mark.parametrize('state', ['not_entered', 'copied_expired', 'wrong_nested', 'foreign_thread'])
def test_selected_context_cannot_escape_exact_consuming_scope(reader_case, monkeypatch, state):
    case = reader_case
    if state == 'copied_expired':
        with entered_case(case) as context:
            saved = copy_context()
        with monkeypatch.context() as patch:
            patch.setattr(os, 'open', forbidden)
            with pytest.raises(ValueError): saved.run(read_case, case, context)
        return
    with coordination.reader_budget(case['budget']):
        context = bind_case(case)
        if state == 'not_entered':
            with monkeypatch.context() as patch:
                patch.setattr(os, 'open', forbidden)
                with pytest.raises(ValueError): read_case(case, context)
            return
        with context:
            if state == 'wrong_nested':
                other = coordination.ReaderBudget(case['budget'].deadline_ns, (threading.Event(),),
                    clock_domain=case['budget'].clock_domain())
                with coordination.reader_budget(other):
                    with monkeypatch.context() as patch:
                        patch.setattr(os, 'open', forbidden)
                        with pytest.raises(ValueError): read_case(case, context)
            else:
                saved, errors = copy_context(), []
                def read_elsewhere():
                    try: saved.run(read_case, case, context)
                    except BaseException as error: errors.append(error)
                with monkeypatch.context() as patch:
                    patch.setattr(os, 'open', forbidden)
                    thread = threading.Thread(target=read_elsewhere)
                    thread.start(); thread.join(2)
                assert not thread.is_alive() and len(errors) == 1
                assert isinstance(errors[0], ValueError)


def test_failed_entry_is_terminal_after_stop_is_removed(reader_case, monkeypatch):
    case = reader_case
    with coordination.reader_budget(case['budget']):
        context = bind_case(case)
        case['stop_path'].write_bytes(b'stopped before entry')
        with pytest.raises(ValueError): context.__enter__()
        case['stop_path'].unlink()
        with monkeypatch.context() as patch:
            patch.setattr(os, 'open', forbidden)
            with pytest.raises(ValueError): context.__enter__()
            with pytest.raises(ValueError): read_case(case, context)


@pytest.mark.parametrize('secondary', ['stop', 'owner'])
def test_context_exit_does_not_replace_original_body_failure(reader_case, secondary):
    case = reader_case
    original = OSError('the exact original reader body failure')
    with pytest.raises(OSError) as caught:
        with entered_case(case):
            if secondary == 'stop': case['stop_path'].write_bytes(b'secondary stop')
            else: case['owner_path'].unlink()
            raise original
    assert caught.value is original


@pytest.mark.parametrize('foreign', ['thread', 'nested_reader', 'nested_budget', 'nested_loader'])
@pytest.mark.parametrize('body_error', [False, True])
def test_foreign_exit_cannot_invalidate_the_legitimate_reader(reader_case, foreign, body_error):
    case = reader_case
    original = RuntimeError('invented body error supplied from another context')
    args = (RuntimeError, original, None) if body_error else (None, None, None)
    with entered_case(case) as outer:
        if foreign == 'thread':
            errors = []
            def exit_elsewhere():
                try: outer.__exit__(*args)
                except BaseException as error: errors.append(error)
            thread = threading.Thread(target=exit_elsewhere)
            thread.start(); thread.join(2)
            assert not thread.is_alive()
            assert len(errors) == 1 and isinstance(errors[0], ValueError)
        elif foreign == 'nested_reader':
            with bind_case(case) as inner:
                with pytest.raises(ValueError): outer.__exit__(*args)
                assert read_case(case, inner).captured.raw == case['paths']['transcript'].read_bytes()
        elif foreign == 'nested_budget':
            other = coordination.ReaderBudget(case['budget'].deadline_ns, (threading.Event(),),
                clock_domain=case['budget'].clock_domain())
            with coordination.reader_budget(other):
                with pytest.raises(ValueError): outer.__exit__(*args)
                assert coordination.current_reader_budget() is other and other.remaining() > 0
        else:
            with authority.loaded_dependencies(case['execution']['dependencies']):
                with pytest.raises(ValueError): outer.__exit__(*args)
        assert read_case(case, outer).captured.raw == case['paths']['transcript'].read_bytes()


@pytest.mark.parametrize('body_error', [False, True])
def test_selected_unlock_failure_cannot_replace_an_original_metadata_failure(reader_case, monkeypatch, body_error):
    case = reader_case
    target = case['paths']['transcript']
    opening, closing, fstat, flock = os.open, os.close, os.fstat, fcntl.flock
    reader, closes, unlocks = [], [], []
    original = OSError('exact original selected metadata failure')
    secondary = OSError('secondary selected unlock failure')

    def tracked_open(path, flags, *args, **kwargs):
        fd = opening(path, flags, *args, **kwargs)
        if str(path) == str(target): reader.append(fd)
        return fd

    def tracked_close(fd):
        if reader and fd == reader[0]: closes.append(fd)
        return closing(fd)

    def sample(fd):
        if body_error and reader and fd == reader[0]: raise original
        return fstat(fd)

    def locked(fd, operation):
        result = flock(fd, operation)
        if reader and fd == reader[0] and operation == fcntl.LOCK_UN:
            unlocks.append(fd)
            raise secondary
        return result

    with pytest.raises(OSError) as caught:
        with entered_case(case) as context:
            with monkeypatch.context() as patch:
                patch.setattr(os, 'open', tracked_open)
                patch.setattr(os, 'close', tracked_close)
                patch.setattr(os, 'fstat', sample)
                patch.setattr(fcntl, 'flock', locked)
                read_case(case, context)
    assert caught.value is (original if body_error else secondary)
    assert len(reader) == 1 and unlocks == closes == reader


@pytest.mark.parametrize('body_failure', [False, True])
def test_selected_descriptor_closes_once_and_preserves_the_primary_error(reader_case, monkeypatch, body_failure):
    case = reader_case
    target = case['paths']['transcript']
    opened, closes = [], []
    opening, closing = os.open, os.close
    original = OSError('exact original pread failure')
    secondary = OSError('exact descriptor close failure')

    def tracked_open(path, flags, *args, **kwargs):
        fd = opening(path, flags, *args, **kwargs)
        if str(path) == str(target): opened.append(fd)
        return fd

    def close(fd):
        result = closing(fd)
        if opened and fd == opened[0]:
            closes.append(fd)
            raise secondary
        return result

    def read(*args):
        raise original

    with pytest.raises(OSError) as caught:
        with entered_case(case) as context:
            with monkeypatch.context() as patch:
                patch.setattr(os, 'open', tracked_open)
                patch.setattr(os, 'close', close)
                if body_failure: patch.setattr(os, 'pread', read)
                read_case(case, context)
    assert caught.value is (original if body_failure else secondary)
    assert len(opened) == 1 and closes == opened
