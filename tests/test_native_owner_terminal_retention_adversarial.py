"""Real fixed-path publication faults and synthetic saved-state contradictions.

The ordinary peer has no tools/providers; captured private declarations and the
clock backend are software fixtures, not public execution admission.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import os
from pathlib import Path
import stat

import pytest

from data_sheets_schema import native_owner_runner_v1 as runner_module
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from tests.test_native_owner_terminal_retention import (
    terminal_case, declaration, fixed_clock, selected_controls,
    execute_case, capture_terminal_pool, manifest_document, role_rows, raw_pin,
    trap_saved_io,
)
from tests.test_native_owner_worker_scope import install_reader_operation


@contextmanager
def opened_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        yield fd
    finally:
        os.close(fd)


def test_fixed_writer_loops_over_real_short_progress_and_syncs_both_inodes(tmp_path, monkeypatch):
    raw = b'{"invented":"bounded bytes for the physical writer only"}'
    real_write, real_fsync, real_fstat = os.write, os.fsync, os.fstat
    writes, syncs = [], []
    def short(fd, data):
        count = real_write(fd, data[:3] if not writes else data)
        writes.append(count)
        return count
    def synced(fd):
        syncs.append('directory' if stat.S_ISDIR(real_fstat(fd).st_mode) else 'file')
        return real_fsync(fd)
    with opened_directory(tmp_path) as directory:
        with monkeypatch.context() as patch:
            patch.setattr(os, 'write', short)
            patch.setattr(os, 'fsync', synced)
            write, retained, partial, error = runner_module._terminal_write(directory, 'owner_close', raw)
    assert error is None and partial is None
    assert write['stage'] == 'complete' and write['owned_create'] is True
    assert writes[0] == 3 and sum(writes) == len(raw)
    assert 'file' in syncs and 'directory' in syncs
    assert syncs.index('file') < syncs.index('directory')
    assert (tmp_path / 'stream-owner-close.json').read_bytes() == raw
    assert retained['pin'] == raw_pin(raw)
    assert {key: retained['metadata'][key] for key in ('device', 'inode')} == write['identity']


@pytest.mark.parametrize('progress', [0, -1, True, 'oversize'])
def test_fixed_writer_invalid_progress_refuses_and_keeps_owned_empty_file(tmp_path, monkeypatch, progress):
    raw = b'physical test only'
    with opened_directory(tmp_path) as directory:
        with monkeypatch.context() as patch:
            patch.setattr(os, 'write', lambda fd, data: len(data) + 1 if progress == 'oversize' else progress)
            write, retained, partial, error = runner_module._terminal_write(directory, 'owner_close', raw)
    assert error is not None and retained is None
    assert write['attempted'] is True and write['owned_create'] is True
    assert write['stage'] == 'write'
    assert (tmp_path / 'stream-owner-close.json').read_bytes() == b''
    assert partial is not None and partial['pin'] == raw_pin(b'')
    assert {key: partial['metadata'][key] for key in ('device', 'inode')} == write['identity']


@pytest.mark.parametrize('where', ['file', 'directory'])
def test_fixed_writer_fsync_failure_cannot_adopt_complete_bytes(tmp_path, monkeypatch, where):
    raw = b'complete bytes do not establish completed publication'
    original = OSError('invented ' + where + ' fsync failure')
    real_fsync, real_fstat = os.fsync, os.fstat
    raised = []
    def failed(fd):
        kind = 'directory' if stat.S_ISDIR(real_fstat(fd).st_mode) else 'file'
        if kind == where and not raised:
            raised.append(fd)
            raise original
        return real_fsync(fd)
    with opened_directory(tmp_path) as directory:
        with monkeypatch.context() as patch:
            patch.setattr(os, 'fsync', failed)
            write, retained, partial, error = runner_module._terminal_write(directory, 'owner_close', raw)
    assert raised and error is original and retained is None
    assert write['stage'] == where + '_fsync'
    assert (tmp_path / 'stream-owner-close.json').read_bytes() == raw
    assert partial is not None and partial['pin'] == raw_pin(raw)


@pytest.mark.parametrize('write_fails', [False, True])
def test_fixed_writer_closes_once_and_preserves_original_write_error(tmp_path, monkeypatch, write_fails):
    raw = b'original physical bytes'
    first = OSError('original write error')
    closing = OSError('later close error')
    real_open, real_write, real_close = os.open, os.write, os.close
    generations, closes, owned = {}, [], []
    def opened(path, flags, *args, **kwargs):
        fd = real_open(path, flags, *args, **kwargs)
        generations[fd] = generations.get(fd, 0) + 1
        if flags & os.O_CREAT:
            owned.append((fd, generations[fd]))
        return fd
    def written(fd, data):
        if write_fails and (fd, generations[fd]) == owned[0]:
            raise first
        return real_write(fd, data)
    def closed(fd):
        key = (fd, generations[fd])
        closes.append(key)
        real_close(fd)
        if key == owned[0]:
            raise closing
    with opened_directory(tmp_path) as directory:
        with monkeypatch.context() as patch:
            patch.setattr(os, 'open', opened)
            patch.setattr(os, 'write', written)
            patch.setattr(os, 'close', closed)
            write, retained, partial, error = runner_module._terminal_write(directory, 'owner_close', raw)
    assert len(owned) == 1 and closes.count(owned[0]) == 1
    assert error is (first if write_fails else closing)
    assert write['stage'] == ('write' if write_fails else 'close')
    assert retained is None
    assert (tmp_path / 'stream-owner-close.json').read_bytes() == (b'' if write_fails else raw)


def test_fixed_writer_does_not_adopt_preexisting_bytes_or_symlinks(tmp_path):
    target = tmp_path / 'stream-owner-close.json'
    raw = b'owned by another attempt'
    target.write_bytes(raw)
    with opened_directory(tmp_path) as directory:
        write, retained, partial, error = runner_module._terminal_write(directory, 'owner_close', raw)
    assert error is not None and retained is None and partial is None
    assert write['owned_create'] is False and write['identity'] is None
    assert target.read_bytes() == raw
    target.unlink()
    external = tmp_path / 'foreign.json'
    external.write_bytes(raw)
    target.symlink_to(external)
    with opened_directory(tmp_path) as directory:
        write, retained, partial, error = runner_module._terminal_write(directory, 'owner_close', raw)
    assert error is not None and retained is None and partial is None
    assert write['owned_create'] is False and target.is_symlink()
    assert external.read_bytes() == raw


@pytest.mark.parametrize('read_fails', [False, True])
def test_fixed_reader_closes_once_without_replacing_its_primary(tmp_path, monkeypatch, read_fails):
    raw = b'fixed owned bytes'
    (tmp_path / 'stream-owner.json').write_bytes(raw)
    real_open, real_close, real_pread = os.open, os.close, os.pread
    primary, cleanup = OSError('primary read failure'), OSError('secondary read close failure')
    opened, closed = [], []
    def open_file(*args, **kwargs):
        fd = real_open(*args, **kwargs)
        opened.append(fd)
        return fd
    def read_file(fd, *args):
        if read_fails:
            raise primary
        return real_pread(fd, *args)
    def close_file(fd):
        closed.append(fd)
        real_close(fd)
        raise cleanup
    with opened_directory(tmp_path) as directory:
        with monkeypatch.context() as patch:
            patch.setattr(os, 'open', open_file)
            patch.setattr(os, 'pread', read_file)
            patch.setattr(os, 'close', close_file)
            with pytest.raises(OSError) as caught:
                runner_module._terminal_read(directory, 'owner')
    assert len(opened) == 1 and closed == opened
    assert caught.value is (primary if read_fails else cleanup)
    assert (tmp_path / 'stream-owner.json').read_bytes() == raw


@contextmanager
def partial_role_write(monkeypatch, role, original):
    """Keep the fixed writer and actual creates; fail after seven real bytes."""
    real_writer, real_write = runner_module._terminal_write, os.write
    active, writes = [], []
    def writer(directory, selected_role, raw):
        active.append(selected_role)
        try:
            return real_writer(directory, selected_role, raw)
        finally:
            active.pop()
    def written(fd, raw):
        if active and active[-1] == role:
            if not writes:
                writes.append(real_write(fd, raw[:7]))
                return writes[-1]
            raise original
        return real_write(fd, raw)
    with monkeypatch.context() as patch:
        patch.setattr(runner_module, '_terminal_write', writer)
        patch.setattr(os, 'write', written)
        yield writes


@pytest.mark.parametrize('role', ['owner_runner_report', 'owner_close'])
def test_actual_publisher_preserves_partial_failure_and_spends_transaction(terminal_case, monkeypatch, role):
    case = execute_case(terminal_case)
    runner = case['runner']
    report_before, snapshot_before = runner.report(), runner.terminal_snapshot()
    intended = dict(snapshot_before[1])[role]
    failure = OSError('real partial terminal publication')
    with partial_role_write(monkeypatch, role, failure) as written:
        with pytest.raises(OSError) as caught:
            runner.publish_terminal()
    assert caught.value is failure and written == [7]
    assert runner.report() == report_before and runner.terminal_snapshot() == snapshot_before
    publication = runner.terminal_publication_report()
    assert publication['state'] == 'publication_failed'
    assert publication['manifest_finalized'] is True
    manifest = manifest_document(case)
    rows = role_rows(manifest)
    failed = rows[role]
    assert failed['state'] == 'publication_failed' and failed['retained'] is None
    assert failed['intended'] == raw_pin(intended)
    assert failed['observed_partial']['pin'] == raw_pin(intended[:7])
    assert case['terminal_paths'][role].read_bytes() == intended[:7]
    pool = capture_terminal_pool(case)
    if role == 'owner_runner_report':
        with pytest.raises(ValueError):
            runner_module.validate_terminal_capture(pool, case['execution'])
    else:
        saved = c.strict_json(runner_module.validate_terminal_capture(pool, case['execution']))
        assert saved['retention_complete'] is False
        assert saved['counts']['observed_partial_members'] == 1
        assert saved['publisher_completion_attested'] is False
    with monkeypatch.context() as patch:
        trap_saved_io(patch)
        with pytest.raises(ValueError):
            runner.publish_terminal()


def test_actual_operation_error_survives_separate_publication_error(terminal_case, monkeypatch):
    case = install_reader_operation(terminal_case, 'observer')
    runner = case['runner']
    operation_error = case['controls']['budgeted_cborg'].BudgetStop('original operation refusal')
    def observed(event):
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            raise operation_error
    case['kwargs']['event_observer'] = observed
    with pytest.raises(type(operation_error)) as caught:
        runner.execute_child(**case['kwargs'])
    assert caught.value is operation_error
    before, snapshot = runner.report(), runner.terminal_snapshot()
    assert before['state'] == 'failed'
    publication_error = OSError('separate terminal write failure')
    with partial_role_write(monkeypatch, 'owner_close', publication_error):
        with pytest.raises(OSError) as caught:
            runner.publish_terminal()
    assert caught.value is publication_error
    assert runner.report() == before and runner.terminal_snapshot() == snapshot
    assert runner.terminal_publication_report()['state'] == 'publication_failed'


@pytest.mark.parametrize('replacement', ['directory', 'symlink'])
def test_actual_publisher_refuses_replaced_attempt_identity(terminal_case, monkeypatch, replacement):
    case = execute_case(terminal_case)
    old = case['attempt']
    moved = old.with_name('original-attempt-kept')
    old.rename(moved)
    foreign = old.with_name('foreign-directory')
    foreign.mkdir()
    sentinel = foreign / 'sentinel'
    sentinel.write_bytes(b'must stay untouched')
    if replacement == 'directory':
        old.mkdir()
    else:
        old.symlink_to(foreign, target_is_directory=True)
    try:
        with pytest.raises((ValueError, OSError)):
            case['runner'].publish_terminal()
        assert sentinel.read_bytes() == b'must stay untouched'
        assert not (foreign / 'stream-owner-retention.json').exists()
        assert not (old / 'stream-owner-result.json').exists()
        assert (moved / 'stream-owner.json').read_bytes() == case['runner'].owner_raw()
        with monkeypatch.context() as patch:
            trap_saved_io(patch)
            with pytest.raises(ValueError):
                case['runner'].publish_terminal()
    finally:
        if old.is_symlink():
            old.unlink()
        else:
            old.rmdir()
        moved.rename(old)


def test_postexecution_new_role_collision_preserves_all_files(terminal_case, monkeypatch):
    case = execute_case(terminal_case)
    collision = case['terminal_paths']['owner_failure']
    collision.write_bytes(b'unrelated sentinel')
    with pytest.raises((ValueError, OSError)):
        case['runner'].publish_terminal()
    assert collision.read_bytes() == b'unrelated sentinel'
    assert not case['terminal_paths']['owner_runner_report'].exists()
    assert not case['terminal_paths']['owner_retention'].exists()
    publication = case['runner'].terminal_publication_report()
    assert publication['manifest_finalized'] is False
    with monkeypatch.context() as patch:
        trap_saved_io(patch)
        with pytest.raises(ValueError):
            case['runner'].publish_terminal()


def pool_role(pool, role):
    matches = [m for m in pool.members if m.captured.pin.role == role]
    assert len(matches) == 1
    return matches[0]


def rewritten_member(member, raw):
    """Invent a self-consistent saved replacement; never rewrite its live file."""
    metadata = c.strict_json(member.metadata_json)
    metadata['size'] = len(raw)
    pin = replace(member.captured.pin, bytes=len(raw), sha256=c.sha(raw))
    return evidence.PoolMember(c.CapturedArtifact(pin, raw), c.canonical(metadata))


def replace_role(pool, role, raw):
    previous = pool_role(pool, role)
    replacement = rewritten_member(previous, raw)
    return evidence.CapturePool(tuple(replacement if row is previous else row
                                      for row in pool.members), pool.stream_bindings)


def recounted_manifest(manifest):
    counts = {'retained_members': 0, 'retained_bytes': 0,
              'observed_partial_members': 0, 'observed_partial_bytes': 0}
    for row in manifest['roles']:
        for field in ('retained', 'observed_partial'):
            if row[field] is not None:
                counts[field + '_members'] += 1
                counts[field + '_bytes'] += row[field]['pin']['bytes']
    manifest['counts'] = counts
    manifest['retention_complete'] = all(row['state'] in ('retained', 'not_produced')
                                          for row in manifest['roles'])
    return manifest


def replace_document(pool, manifest, role, document):
    """Rebind role raw/pin/metadata and its manifest row, leaving other claims."""
    raw = c.canonical(document)
    pool = replace_role(pool, role, raw)
    member = pool_role(pool, role)
    row = role_rows(manifest)[role]
    assert row['state'] == 'retained'
    row['intended'] = raw_pin(raw)
    row['retained'] = {'pin': raw_pin(raw), 'metadata': c.strict_json(member.metadata_json)}
    if role == 'owner_runner_report':
        manifest['runner_report'] = raw_pin(raw)
    return pool


def saved_mutation(pool, original, mutation):
    manifest = deepcopy(original)
    mutation(manifest)
    return replace_role(pool, 'owner_retention', c.canonical(manifest))


def test_saved_manifest_refuses_closed_schema_and_lifecycle_contradictions(terminal_case, monkeypatch):
    case = execute_case(terminal_case)
    case['runner'].publish_terminal()
    pool, original = capture_terminal_pool(case), manifest_document(case)
    mutations = {
        'unknown manifest key': lambda d: d.update(unreviewed=True),
        'unsupported version': lambda d: d.update(format='native_owner_terminal_retention_v2'),
        'wrong scope': lambda d: d.update(scope='execution_acceptance'),
        'authorization': lambda d: d.update(execution_authorized=True),
        'acceptance': lambda d: d.update(native_acceptance='accepted'),
        'count bool': lambda d: d['counts'].update(retained_members=True),
        'count omitted': lambda d: d['counts'].pop('retained_bytes'),
        'count mismatch': lambda d: d['counts'].update(retained_bytes=d['counts']['retained_bytes'] + 1),
        'inverted completion': lambda d: d.update(retention_complete=False),
        'missing role': lambda d: d['roles'].pop(),
        'duplicate role': lambda d: d['roles'].__setitem__(-1, deepcopy(d['roles'][0])),
        'role order': lambda d: d['roles'].reverse(),
        'foreign path': lambda d: d['roles'][3].update(path=d['roles'][3]['path'] + '.other'),
        'unknown row field': lambda d: d['roles'][3].update(copied=True),
        'retained without write': lambda d: d['roles'][3].update(write=None),
        'unowned retained inode': lambda d: d['roles'][3]['write']['identity'].update(inode=1),
        'retained partial': lambda d: d['roles'][3].update(observed_partial=deepcopy(d['roles'][3]['retained'])),
        'no owner identity': lambda d: d['lifecycle'].update(owner_identity=None),
        'owner identity differs': lambda d: d['lifecycle']['owner_identity'].update(mtime_ns=0),
        'no directory identity': lambda d: d['lifecycle'].update(attempt_identity=None),
        'boolean directory inode': lambda d: d['lifecycle']['attempt_identity'].update(inode=True),
        'stop never attempted': lambda d: d['lifecycle'].update(stop_create_attempted=False),
        'stop not completed': lambda d: d['lifecycle'].update(stop_create_completed=False),
        'incomplete cut asserts absence': lambda d: d['lifecycle'].update(stop_cut_state='unavailable'),
        'incomplete copy asserts absence': lambda d: d['lifecycle'].update(failed_members_copy_state='unavailable'),
        'summary present discarded': lambda d: d['lifecycle'].update(failure_summary_copy_state='present'),
        'copied close absent': lambda d: d['lifecycle'].update(close_report_copy_state='absent'),
        'refused report label': lambda d: d['lifecycle'].update(runner_report_state='refused'),
        'unknown failed member': lambda d: d['lifecycle']['failed_member_pins'].update(unrecognized=raw_pin(b'')),
        'invented failed bytes': lambda d: d['lifecycle']['failed_member_pins'].update(transcript_suffix=raw_pin(b'')),
        'execution pin': lambda d: d['identities'].update(execution_sha256='0' * 64),
        'profile bool version': lambda d: d['identities']['profile'].update(version=True),
        'report pin': lambda d: d['runner_report'].update(sha256='0' * 64),
    }
    # Every mutation has a new valid captured member hash. No ambient read can
    # rescue a contradiction in the declared terminal evidence.
    for label, mutation in mutations.items():
        changed = saved_mutation(pool, original, mutation)
        with monkeypatch.context() as patch:
            trap_saved_io(patch)
            try:
                runner_module.validate_terminal_capture(changed, case['execution'])
            except ValueError:
                pass
            else:
                pytest.fail('saved terminal validator accepted: ' + label)
    assert case['terminal_paths']['owner_retention'].read_bytes() == c.canonical(original)


def test_saved_terminal_requires_every_declared_prerequisite_and_unique_role(terminal_case):
    case = execute_case(terminal_case)
    case['runner'].publish_terminal()
    pool = capture_terminal_pool(case)
    for role in ('owner', 'owner_runner_report', 'owner_retention', 'execution_capture',
                 'started_capture', 'owner_stop', 'owner_close'):
        changed = evidence.CapturePool(tuple(row for row in pool.members
                                            if row.captured.pin.role != role), ())
        with pytest.raises(ValueError):
            runner_module.validate_terminal_capture(changed, case['execution'])
    original = pool_role(pool, 'owner_close')
    metadata = c.strict_json(original.metadata_json)
    metadata['mtime_ns'] += 1
    duplicate = evidence.PoolMember(original.captured, c.canonical(metadata))
    ambiguous = evidence.CapturePool((*pool.members, duplicate), ())
    with pytest.raises(ValueError):
        runner_module.validate_terminal_capture(ambiguous, case['execution'])


def test_saved_owned_owner_cannot_claim_control_was_never_created(terminal_case, monkeypatch):
    case = execute_case(terminal_case)
    case['runner'].publish_terminal()
    original = capture_terminal_pool(case)
    manifest = manifest_document(case)
    report = c.strict_json(pool_role(original, 'owner_runner_report').captured.raw)
    report['control_close'] = None
    pool = replace_document(original, manifest, 'owner_runner_report', report)
    pool = evidence.CapturePool(tuple(row for row in pool.members
                                    if row.captured.pin.role != 'owner_close'), ())
    manifest['lifecycle'].update(control_created=False, stop_cut_state='not_created',
        failed_members_copy_state='not_created', failure_summary_copy_state='not_created',
        close_report_copy_state='not_created', failed_member_pins={})
    for row in manifest['roles'][3:]:
        row.update(state='not_produced', basis='control_not_created', intended=None,
                   retained=None, observed_partial=None, write=None)
    pool = replace_role(pool, 'owner_retention', c.canonical(recounted_manifest(manifest)))
    with monkeypatch.context() as patch:
        trap_saved_io(patch)
        with pytest.raises(ValueError):
            runner_module.validate_terminal_capture(pool, case['execution'])


def test_manifest_complete_bytes_after_failed_directory_fsync_do_not_attest_success(terminal_case, monkeypatch):
    case = execute_case(terminal_case)
    runner = case['runner']
    before = runner.report()
    primary = OSError('manifest directory fsync failed after complete bytes')
    real_writer, real_fsync, real_fstat = runner_module._terminal_write, os.fsync, os.fstat
    active, failures = [], []
    def writer(directory, role, raw):
        active.append(role)
        try:
            return real_writer(directory, role, raw)
        finally:
            active.pop()
    def synced(fd):
        if active and active[-1] == 'owner_retention' and stat.S_ISDIR(real_fstat(fd).st_mode):
            failures.append(True)
            raise primary
        return real_fsync(fd)
    with monkeypatch.context() as patch:
        patch.setattr(runner_module, '_terminal_write', writer)
        patch.setattr(os, 'fsync', synced)
        with pytest.raises(OSError) as caught:
            runner.publish_terminal()
    assert caught.value is primary and failures == [True]
    publication = runner.terminal_publication_report()
    assert publication['state'] == 'publication_failed' and publication['manifest_finalized'] is False
    assert publication['manifest']['retained'] is None
    assert publication['manifest']['observed_partial']['pin'] == publication['manifest']['intended']
    assert runner.report() == before
    pool = capture_terminal_pool(case)
    saved = c.strict_json(runner_module.validate_terminal_capture(pool, case['execution']))
    assert saved['captured_manifest_complete'] is True
    assert saved['publisher_completion_attested'] is False
    with monkeypatch.context() as patch:
        trap_saved_io(patch)
        with pytest.raises(ValueError):
            runner.publish_terminal()


def test_owner_readback_failure_cannot_fall_back_to_equal_live_bytes(terminal_case, monkeypatch):
    case = terminal_case
    original = OSError('first owned owner capture unavailable')
    real_read = evidence.read_regular
    failures = []
    def read(path, role, **kwargs):
        if role == 'owner':
            failures.append(str(path))
            raise original
        return real_read(path, role, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(evidence, 'read_regular', read)
        with pytest.raises(OSError) as caught:
            case['runner'].execute_child(**case['kwargs'])
    assert caught.value is original and len(failures) == 1
    runner = case['runner']
    assert case['terminal_paths']['owner'].read_bytes() == runner.owner_raw()
    life = c.strict_json(runner.terminal_snapshot()[0])['lifecycle']
    assert life['owner_create_completed'] is True and life['owner_identity'] is None
    with monkeypatch.context() as patch:
        trap_saved_io(patch)
        with pytest.raises(ValueError):
            runner.publish_terminal()
        assert runner.terminal_publication_report()['roles'] == []


def test_actual_report_serializer_refusal_keeps_optional_absence_unproven(terminal_case, monkeypatch):
    case = terminal_case
    primary = ValueError('normal report serialization refused')
    real_json = runner_module.owner._json
    attempts = []
    def serialized(value):
        if type(value) is dict and value.get('format') == 'native_owner_runner_report_v1':
            attempts.append(True)
            raise primary
        return real_json(value)
    with monkeypatch.context() as patch:
        patch.setattr(runner_module.owner, '_json', serialized)
        with pytest.raises(ValueError) as caught:
            case['runner'].execute_child(**case['kwargs'])
    assert caught.value is primary and attempts == [True]
    report = case['runner'].report()
    assert report['format'] == 'native_owner_runner_report_refused_v1'
    assert report['state'] == 'failed' and report['owner_published'] is True
    projection = c.strict_json(case['runner'].terminal_snapshot()[0])
    assert projection['lifecycle']['runner_report_state'] == 'refused'
    case['runner'].publish_terminal()
    manifest = manifest_document(case)
    rows = role_rows(manifest)
    assert rows['owner_runner_report']['state'] == 'retained'
    assert rows['owner_failure']['state'] == 'capture_refused'
    assert rows['owner_control_record']['state'] == 'capture_refused'
    pool = capture_terminal_pool(case)
    with monkeypatch.context() as patch:
        trap_saved_io(patch)
        saved = c.strict_json(runner_module.validate_terminal_capture(pool, case['execution']))
    assert saved['retention_complete'] is False
    assert saved['publisher_completion_attested'] is False
    assert case['runner'].report() == report


def test_failed_linked_stop_stays_refused_even_with_all_intended_bytes(terminal_case, monkeypatch):
    case = terminal_case
    primary = OSError('stop directory fsync after successful link')
    real_new, real_fsync, real_fstat = runner_module.durable.durable_new, os.fsync, os.fstat
    active = []
    def durable_new(path, raw):
        active.append(Path(path).name)
        try:
            return real_new(path, raw)
        finally:
            active.pop()
    def synced(fd):
        if active and active[-1] == 'stream-owner-stop.json' and stat.S_ISDIR(real_fstat(fd).st_mode):
            raise primary
        return real_fsync(fd)
    with monkeypatch.context() as patch:
        patch.setattr(runner_module.durable, 'durable_new', durable_new)
        patch.setattr(os, 'fsync', synced)
        with pytest.raises(OSError) as caught:
            case['runner'].execute_child(**case['kwargs'])
    assert caught.value is primary
    stop = case['terminal_paths']['owner_stop']
    raw = stop.read_bytes()
    assert stop.stat().st_nlink == 2
    before = case['runner'].report()
    publication = case['runner'].publish_terminal()
    assert publication['retention_complete'] is False
    row = role_rows(manifest_document(case))['owner_stop']
    assert row['state'] == 'capture_refused' and row['basis'] == 'stop_create_not_completed'
    assert row['intended'] == raw_pin(raw) and row['retained'] is None
    assert row['observed_partial'] is None and row['write'] is None
    assert stop.read_bytes() == raw and stop.stat().st_nlink == 2
    pool = capture_terminal_pool(case)
    assert not any(row.captured.pin.role == 'owner_stop' for row in pool.members)
    saved = c.strict_json(runner_module.validate_terminal_capture(pool, case['execution']))
    assert saved['retention_complete'] is False and case['runner'].report() == before


def test_fixed_metadata_and_payload_limits_refuse_before_file_creation(tmp_path, monkeypatch):
    raw = b' ' * 16_384
    with opened_directory(tmp_path) as directory:
        write, retained, partial, error = runner_module._terminal_write(directory, 'owner_close', raw)
    assert error is None and retained['pin'] == raw_pin(raw) and partial is None
    assert write['stage'] == 'complete'
    other = tmp_path / 'separate'
    other.mkdir()
    with opened_directory(other) as directory:
        with monkeypatch.context() as patch:
            patch.setattr(os, 'open', lambda *args, **kwargs: pytest.fail('over-limit writer opened a file'))
            with pytest.raises(ValueError, match='bound'):
                runner_module._terminal_write(directory, 'owner_close', raw + b' ')
    exact = {'padding': 'x' * (65_536 - len(c.canonical({'padding': ''})))}
    assert len(runner_module._terminal_json(exact)) == 65_536
    exact['padding'] += 'x'
    with pytest.raises(ValueError, match='bound'):
        runner_module._terminal_json(exact)


def test_rehashed_runner_and_close_documents_keep_closed_typed_accounting(terminal_case, monkeypatch):
    case = execute_case(terminal_case)
    case['runner'].publish_terminal()
    original = capture_terminal_pool(case)
    base_manifest = manifest_document(case)
    original_report = c.strict_json(pool_role(original, 'owner_runner_report').captured.raw)
    original_close = c.strict_json(pool_role(original, 'owner_close').captured.raw)
    close_changes = {
        'unknown close key': lambda d: d.update(unknown=True),
        'changed format': lambda d: d.update(format='native_owner_close_v3'),
        'admission': lambda d: d.update(admitted=True),
        'wrong role': lambda d: d.update(role='control'),
        'boolean count': lambda d: d.update(unfinished_workers=False),
        'false completion': lambda d: d.update(unfinished_workers=1),
        'renewed cleanup deadline': lambda d: d.update(close_deadline_ns=d['close_deadline_ns'] + 1),
        'over-admitted physical bytes': lambda d: d.update(admitted_bytes=d['suffix_start'] + 1),
        'negative suffix start': lambda d: d.update(suffix_start=-1),
        'wrong final offset': lambda d: d.update(final_written_bytes=d['final_written_bytes'] + 1),
        'boolean suffix bytes': lambda d: d['suffix'].update(bytes=False),
        'complete with retention error': lambda d: d.update(retention_error='injected'),
    }
    report_changes = {
        'unknown report field': lambda d: d.update(claim=True),
        'boolean dispatch count': lambda d: d.update(dispatches=True),
        'completed without dispatch': lambda d: d.update(dispatches=0),
        'boolean return code': lambda d: d.update(returncode=False),
        'failed without failure': lambda d: d.update(state='failed'),
        'public execution': lambda d: d.update(execution_authorized=True),
        'native acceptance': lambda d: d.update(native_acceptance='accepted'),
        'owner falsely absent': lambda d: d.update(owner_published=False),
        'stop falsely absent': lambda d: d.update(stop_marker_published=False),
        'missing copied close': lambda d: d.update(control_close=None),
    }
    for label, mutation in close_changes.items():
        manifest, report, close = deepcopy(base_manifest), deepcopy(original_report), deepcopy(original_close)
        mutation(close)
        # Mutate both physical copies, so ordinary cross-copy hash inequality
        # cannot mask failure of the closed close-state validator.
        report['control_close'] = close
        pool = replace_document(original, manifest, 'owner_close', close)
        pool = replace_document(pool, manifest, 'owner_runner_report', report)
        pool = replace_role(pool, 'owner_retention', c.canonical(recounted_manifest(manifest)))
        with monkeypatch.context() as patch:
            trap_saved_io(patch)
            try:
                runner_module.validate_terminal_capture(pool, case['execution'])
            except ValueError:
                pass
            else:
                pytest.fail('accepted rehashed close contradiction: ' + label)
    for label, mutation in report_changes.items():
        manifest, report = deepcopy(base_manifest), deepcopy(original_report)
        mutation(report)
        pool = replace_document(original, manifest, 'owner_runner_report', report)
        pool = replace_role(pool, 'owner_retention', c.canonical(recounted_manifest(manifest)))
        with monkeypatch.context() as patch:
            trap_saved_io(patch)
            try:
                runner_module.validate_terminal_capture(pool, case['execution'])
            except ValueError:
                pass
            else:
                pytest.fail('accepted rehashed report contradiction: ' + label)
    # Process exit status is retained data, not a new native acceptance gate.
    manifest, report = deepcopy(base_manifest), deepcopy(original_report)
    report['returncode'] = 7
    nonzero = replace_document(original, manifest, 'owner_runner_report', report)
    nonzero = replace_role(nonzero, 'owner_retention', c.canonical(recounted_manifest(manifest)))
    saved = c.strict_json(runner_module.validate_terminal_capture(nonzero, case['execution']))
    assert saved['execution_authorized'] is False and saved['native_acceptance'] == 'not_assessed'


def test_failure_cut_and_empty_suffix_remain_present_and_separate_from_absence(terminal_case, monkeypatch):
    case = install_reader_operation(terminal_case, 'observer')
    refusal = case['controls']['budgeted_cborg'].BudgetStop('captured observer refusal')
    def observed(event):
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            raise refusal
    case['kwargs']['event_observer'] = observed
    with pytest.raises(type(refusal)) as caught:
        case['runner'].execute_child(**case['kwargs'])
    assert caught.value is refusal
    case['runner'].publish_terminal()
    original = capture_terminal_pool(case)
    manifest = manifest_document(case)
    rows = role_rows(manifest)
    suffix = pool_role(original, 'owner_transcript_suffix')
    assert rows['owner_transcript_suffix']['state'] == 'retained'
    assert suffix.captured.raw == b'' and rows['owner_transcript_suffix']['intended'] == raw_pin(b'')
    saved = c.strict_json(runner_module.validate_terminal_capture(original, case['execution']))
    assert saved['native_acceptance'] == 'not_assessed'
    assert saved['execution_authorized'] is False
    summary = c.strict_json(pool_role(original, 'owner_failure').captured.raw)
    assert summary['first_stop'] == str(refusal)
    # The completed observer exception cannot be retained as a decision. Its
    # refusal summary is valid evidence, not a successfully captured result.
    assert summary['capture_state'] == 'capture_refused'
    assert summary['capture_error'] == 'ValueError'
    assert summary['completed_result_captured'] is False
    assert summary['result'] is None
    # Keep both close copies identical while denying the actual retained
    # failure summary; physical offsets and every raw pin still agree.
    false_close = c.strict_json(pool_role(original, 'owner_close').captured.raw)
    false_close['operation_failed'] = False
    false_report = c.strict_json(pool_role(original, 'owner_runner_report').captured.raw)
    false_report['control_close'] = false_close
    doc = deepcopy(manifest)
    false_pool = replace_document(original, doc, 'owner_close', false_close)
    false_pool = replace_document(false_pool, doc, 'owner_runner_report', false_report)
    false_pool = replace_role(false_pool, 'owner_retention', c.canonical(recounted_manifest(doc)))
    with pytest.raises(ValueError):
        runner_module.validate_terminal_capture(false_pool, case['execution'])

    # The same known summary remains a failure fact if its publication failed;
    # captured partial JSON is not parsed as a substitute summary authority.
    doc = deepcopy(manifest)
    missing_summary_pool = replace_document(original, doc, 'owner_close', false_close)
    missing_summary_pool = replace_document(missing_summary_pool, doc, 'owner_runner_report', false_report)
    missing_rows = role_rows(doc)
    summary_row = missing_rows['owner_failure']
    summary_row.update(state='publication_failed', basis='write_failed_partial_observed',
                       observed_partial=summary_row['retained'], retained=None)
    saved_error = {'type': 'OSError', 'message': 'invented summary write failure',
                   'message_identity': raw_pin(b'invented summary write failure')}
    summary_row['write'].update(stage='file_fsync', error=saved_error)
    missing_rows['owner_control_record'].update(state='capture_refused',
        basis='intended_record_bytes_unavailable', intended=None)
    missing_rows['owner_transcript_suffix'].update(state='publication_failed',
        basis='not_attempted_after_publication_failure', retained=None,
        write={'attempted': False, 'owned_create': False, 'identity': None,
               'stage': 'not_attempted', 'error': None})
    missing_summary_pool = evidence.CapturePool(tuple(row for row in missing_summary_pool.members
        if row.captured.pin.role != 'owner_transcript_suffix'), ())
    missing_summary_pool = replace_role(missing_summary_pool, 'owner_retention',
                                       c.canonical(recounted_manifest(doc)))
    with pytest.raises(ValueError):
        runner_module.validate_terminal_capture(missing_summary_pool, case['execution'])

    # An owned partial from a later *attempted* write contradicts the fixed
    # publisher's stop-after-first-failure rule, even if both files survived.
    doc = deepcopy(manifest)
    second_rows = role_rows(doc)
    error = {'type': 'OSError', 'message': 'invented saved publication failure',
             'message_identity': raw_pin(b'invented saved publication failure')}
    for role in ('owner_close', 'owner_failure'):
        row = second_rows[role]
        row.update(state='publication_failed', basis='write_failed_partial_observed',
                   observed_partial=row['retained'], retained=None)
        row['write'].update(stage='file_fsync', error=deepcopy(error))
    second_rows['owner_control_record'].update(state='capture_refused',
        basis='intended_record_bytes_unavailable', intended=None)
    second_rows['owner_transcript_suffix'].update(state='publication_failed',
        basis='not_attempted_after_publication_failure', retained=None,
        write={'attempted': False, 'owned_create': False, 'identity': None,
               'stage': 'not_attempted', 'error': None})
    second_pool = evidence.CapturePool(tuple(row for row in original.members
        if row.captured.pin.role != 'owner_transcript_suffix'), ())
    second_pool = replace_role(second_pool, 'owner_retention', c.canonical(recounted_manifest(doc)))
    with pytest.raises(ValueError):
        runner_module.validate_terminal_capture(second_pool, case['execution'])
    changes = {
        'unknown field': lambda d: d.update(extra=True),
        'boolean captured flag': lambda d: d.update(completed_result_captured=1),
        'unknown format': lambda d: d.update(format='native_owner_failure_v2'),
        'boolean worker timestamp': lambda d: d.update(worker_started=True),
        'negative worker timestamp': lambda d: d.update(worker_finished=-1),
        'negative physical count': lambda d: d['transcript'].update(written_bytes=-1),
        'received count exceeds cut': lambda d: d['transcript'].update(received_bytes=d['transcript']['received_bytes'] + 1),
        'physical above received': lambda d: d['transcript'].update(written_bytes=d['transcript']['received_bytes'] + 1),
        'boolean pending bytes': lambda d: d['transcript']['pending'].update(bytes=False),
        'captured state retains refusal reason': lambda d: d.update(capture_state='captured'),
        'refused state lacks refusal reason': lambda d: d.pop('capture_error'),
    }
    for label, mutation in changes.items():
        doc, changed_summary = deepcopy(manifest), deepcopy(summary)
        mutation(changed_summary)
        assert c.canonical(changed_summary) != c.canonical(summary), label
        pool = replace_document(original, doc, 'owner_failure', changed_summary)
        pool = replace_role(pool, 'owner_retention', c.canonical(recounted_manifest(doc)))
        with monkeypatch.context() as patch:
            trap_saved_io(patch)
            try:
                runner_module.validate_terminal_capture(pool, case['execution'])
            except ValueError:
                pass
            else:
                pytest.fail('accepted rehashed failure contradiction: ' + label)
    # Removing the actual zero-byte member must not turn it into nonproduction.
    without = evidence.CapturePool(tuple(m for m in original.members if m is not suffix), ())
    with pytest.raises(ValueError):
        runner_module.validate_terminal_capture(without, case['execution'])
    changed = deepcopy(manifest)
    row = role_rows(changed)['owner_transcript_suffix']
    row.update(state='not_produced', basis='close_declares_no_failed_suffix', intended=None,
               retained=None, observed_partial=None, write=None)
    changed['lifecycle']['failed_member_pins'].pop('transcript_suffix')
    without = replace_role(without, 'owner_retention', c.canonical(recounted_manifest(changed)))
    with pytest.raises(ValueError):
        runner_module.validate_terminal_capture(without, case['execution'])


def test_optional_partial_with_complete_bytes_stays_failed_in_saved_evidence(terminal_case, monkeypatch):
    case = execute_case(terminal_case)
    original = OSError('close role file fsync failed')
    real_writer, real_fsync, real_fstat = runner_module._terminal_write, os.fsync, os.fstat
    active = []
    def writer(directory, role, raw):
        active.append(role)
        try:
            return real_writer(directory, role, raw)
        finally:
            active.pop()
    def synced(fd):
        if active and active[-1] == 'owner_close' and stat.S_ISREG(real_fstat(fd).st_mode):
            raise original
        return real_fsync(fd)
    with monkeypatch.context() as patch:
        patch.setattr(runner_module, '_terminal_write', writer)
        patch.setattr(os, 'fsync', synced)
        with pytest.raises(OSError) as caught:
            case['runner'].publish_terminal()
    assert caught.value is original
    pool, manifest = capture_terminal_pool(case), manifest_document(case)
    row = role_rows(manifest)['owner_close']
    assert row['observed_partial']['pin'] == row['intended']
    baseline = c.strict_json(runner_module.validate_terminal_capture(pool, case['execution']))
    assert baseline['retention_complete'] is False
    assert baseline['counts']['observed_partial_members'] == 1
    mutations = {
        'partial without create': lambda d: role_rows(d)['owner_close']['write'].update(owned_create=False, identity=None),
        'partial foreign inode': lambda d: role_rows(d)['owner_close']['write']['identity'].update(inode=1),
        'partial without attempt': lambda d: role_rows(d)['owner_close']['write'].update(attempted=False),
        'partial falsely completed write': lambda d: role_rows(d)['owner_close']['write'].update(stage='complete', error=None),
        'failed role falsely complete manifest': lambda d: d.update(retention_complete=True),
        'partial not counted': lambda d: d['counts'].update(observed_partial_bytes=0),
    }
    for label, mutate in mutations.items():
        changed = saved_mutation(pool, manifest, mutate)
        try:
            runner_module.validate_terminal_capture(changed, case['execution'])
        except ValueError:
            pass
        else:
            pytest.fail('accepted partial publication contradiction: ' + label)
    # Equal full bytes cannot repair the failed write-accounting declaration.
    promoted = deepcopy(manifest)
    row = role_rows(promoted)['owner_close']
    row.update(state='retained', basis='retained_frozen_member', retained=row['observed_partial'], observed_partial=None)
    promoted = recounted_manifest(promoted)
    with pytest.raises(ValueError):
        runner_module.validate_terminal_capture(replace_role(pool, 'owner_retention', c.canonical(promoted)), case['execution'])
