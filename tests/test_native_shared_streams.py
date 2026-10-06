"""Controlled append races at real selected readers; no child or transport."""
from copy import deepcopy
from pathlib import Path
import os
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_streams as streams
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema.native_shared_controller import CallbackAdapter
from data_sheets_schema.native_shared_receipts import _ReceiptCatalogContext


def prefix(path, raw, role='transcript'):
    return c.EvidencePrefix(role, str(path), raw, len(raw), c.sha(raw), raw.count(b'\n'))


def append(path, raw):
    with path.open('ab') as out:
        out.write(raw)


def files(tmp_path):
    native = tmp_path / 'transcript.jsonl'
    control = tmp_path / 'control.jsonl'
    native.write_bytes(b'{"first":1}\n')
    control.write_bytes(b'{"control":1}\n')
    return native, control


def endpoint(value):
    # Only the real endpoint method is under test, not invented E admission.
    adapter = CallbackAdapter.__new__(CallbackAdapter)
    adapter.execution = value
    adapter._stream_prefixes, adapter._stream_files = {}, {}
    adapter._receipt_catalogs = _ReceiptCatalogContext()
    return adapter


@pytest.mark.parametrize('schedule', ['before_open', 'before_open_stat', 'after_open_stat', 'first_read', 'second_read'])
def test_fixed_extent_accepts_append_without_chasing_eof(tmp_path, monkeypatch, schedule):
    path, _ = files(tmp_path)
    initial = path.read_bytes()
    later = b'{"next":2}\n'
    old = prefix(path, initial)
    actual_open, actual_stat, actual_read = os.open, os.fstat, os.pread
    seen = {'open': 0, 'stat': 0, 'read': 0, 'appends': 0}
    opened_meta = []
    def grow():
        append(path, later); seen['appends'] += 1
    def opening(name, flags, *args, **kwargs):
        seen['open'] += 1
        if schedule == 'before_open': grow()
        return actual_open(name, flags, *args, **kwargs)
    def statting(fd):
        seen['stat'] += 1
        if seen['stat'] == 1 and schedule == 'before_open_stat': grow()
        result = actual_stat(fd)
        if seen['stat'] == 1:
            opened_meta.append(evidence._stat(result))
            if schedule == 'after_open_stat': grow()
        return result
    def reading(fd, count, offset):
        seen['read'] += 1
        result = actual_read(fd, count, offset)
        if (schedule == 'first_read' and seen['read'] == 1) or (schedule == 'second_read' and seen['read'] == 2): grow()
        return result
    monkeypatch.setattr(streams.os, 'open', opening)
    monkeypatch.setattr(streams.os, 'fstat', statting)
    monkeypatch.setattr(streams.os, 'pread', reading)
    member = streams.read_live_stream(str(path), 'transcript', max_bytes=4096, previous=old)
    expected = initial + later if schedule in {'before_open', 'before_open_stat'} else initial
    assert member.captured.raw == expected
    assert c.strict_json(member.metadata_json) == opened_meta[0]
    assert member.captured.pin.bytes == opened_meta[0]['size'] == len(expected)
    assert streams.prefix(member, len(initial)) == old
    assert path.read_bytes() == initial + later and seen['appends'] == 1
    assert seen['open'] == 1 and seen['read'] == 2
    pool = evidence.CapturePool((member,), ())
    assert evidence.decode(pool.encode()) == pool


@pytest.mark.parametrize('change', ['rewrite', 'truncate', 'regrown_changed', 'replace', 'hardlink', 'symlink', 'oversize', 'short_read'])
def test_live_reader_refuses_visible_mutation_and_identity_changes(tmp_path, monkeypatch, change):
    path, _ = files(tmp_path)
    original = path.read_bytes(); (tmp_path / 'original-evidence').write_bytes(original)
    before = streams.read_live_stream(str(path), 'transcript', max_bytes=4096)
    anchor = c.strict_json(before.metadata_json)
    old = streams.prefix(before)
    actual = os.pread; calls = 0
    def reading(fd, count, offset):
        nonlocal calls
        calls += 1
        raw = actual(fd, count, offset)
        if calls == 1:
            if change == 'rewrite': path.write_bytes(original.replace(b'1', b'9'))
            elif change == 'truncate': path.write_bytes(b'')
            elif change == 'regrown_changed': path.write_bytes(original.replace(b'1', b'9') + b'{}\n')
            elif change == 'replace':
                replacement = tmp_path / 'replacement'; replacement.write_bytes(original)
                path.rename(tmp_path / 'old-inode'); replacement.rename(path)
            elif change == 'hardlink': os.link(path, tmp_path / 'new-link')
            elif change == 'symlink':
                path.rename(tmp_path / 'old-inode'); path.symlink_to(tmp_path / 'old-inode')
            elif change == 'oversize': append(path, b'x' * 4096)
            elif change == 'short_read': return b''
        return raw
    monkeypatch.setattr(streams.os, 'pread', reading)
    with pytest.raises(ValueError):
        streams.read_live_stream(str(path), 'transcript', max_bytes=4096, previous=old,
            identity={k: anchor[k] for k in ('device', 'inode')})
    assert calls <= 2
    assert (tmp_path / 'original-evidence').read_bytes() == original


def test_identical_byte_replacement_between_captures_is_not_the_same_stream(tmp_path):
    path, _ = files(tmp_path)
    first = streams.read_live_stream(str(path), 'transcript', max_bytes=4096)
    anchor = c.strict_json(first.metadata_json)
    path.rename(tmp_path / 'retained-first-inode'); path.write_bytes(first.captured.raw)
    with pytest.raises(ValueError, match='file identity'):
        streams.read_live_stream(str(path), 'transcript', max_bytes=4096, previous=streams.prefix(first),
            identity={k: anchor[k] for k in ('device', 'inode')})


def test_prior_prefix_rewrite_with_append_is_refused(tmp_path):
    path, _ = files(tmp_path)
    first = streams.read_live_stream(str(path), 'transcript', max_bytes=4096)
    path.write_bytes(first.captured.raw.replace(b'1', b'9') + b'{}\n')
    with pytest.raises(ValueError, match='previously observed'):
        streams.read_live_stream(str(path), 'transcript', max_bytes=4096, previous=streams.prefix(first))


@pytest.mark.parametrize('change', ['role', 'bound_bool', 'foreign_previous', 'bool_inode', 'extra_anchor'])
def test_malformed_role_bound_or_anchor_refuses_before_open(tmp_path, monkeypatch, change):
    path, _ = files(tmp_path)
    kwargs = {'role': 'transcript', 'max_bytes': 100}
    if change == 'role': kwargs['role'] = 'response'
    elif change == 'bound_bool': kwargs['max_bytes'] = True
    elif change == 'foreign_previous': kwargs['previous'] = prefix(path, b'{}\n', 'control')
    elif change == 'bool_inode': kwargs['identity'] = {'device': 0, 'inode': True}
    else: kwargs['identity'] = {'device': 0, 'inode': 0, 'size': 0}
    monkeypatch.setattr(streams.os, 'open', lambda *a, **k: pytest.fail('malformed declaration opened a file'))
    with pytest.raises(ValueError): streams.read_live_stream(str(path), **kwargs)


@pytest.mark.parametrize('schedule', ['open', 'read'])
def test_immutable_reader_still_refuses_the_same_append(tmp_path, monkeypatch, schedule):
    path, _ = files(tmp_path)
    original_open, original_read = os.open, os.read
    appended = False
    def grow():
        nonlocal appended
        if not appended: append(path, b'{"later":1}\n'); appended = True
    def opening(*args, **kwargs):
        if schedule == 'open': grow()
        return original_open(*args, **kwargs)
    def reading(*args, **kwargs):
        raw = original_read(*args, **kwargs)
        if schedule == 'read': grow()
        return raw
    monkeypatch.setattr(evidence.os, 'open', opening)
    monkeypatch.setattr(evidence.os, 'read', reading)
    with pytest.raises(ValueError, match='changed'):
        evidence.read_regular(str(path), 'transcript', max_bytes=4096)
    assert appended


@pytest.mark.parametrize('site', ['endpoint', 'live_streams'])
@pytest.mark.parametrize('schedule', ['open', 'read'])
def test_actual_consumers_accept_later_callback_but_do_not_credit_it(tmp_path, monkeypatch, site, schedule):
    path, control = files(tmp_path); base = path.read_bytes()
    value = {'attempt_directory': str(tmp_path)}
    anchors = streams.stream_files(capture._streams(value)[0])
    adapter = endpoint(value)
    original_open, original_read = os.open, os.pread
    target_fd = None; appended = False
    def grow():
        nonlocal appended
        if not appended: append(path, b'{"future_callback":true}\n'); appended = True
    def opening(name, *args, **kwargs):
        nonlocal target_fd
        if name == str(path) and schedule == 'open': grow()
        fd = original_open(name, *args, **kwargs)
        if name == str(path): target_fd = fd
        return fd
    def reading(fd, *args, **kwargs):
        raw = original_read(fd, *args, **kwargs)
        if fd == target_fd and schedule == 'read': grow()
        return raw
    monkeypatch.setattr(streams.os, 'open', opening)
    monkeypatch.setattr(streams.os, 'pread', reading)
    if site == 'endpoint':
        assert adapter._observed_endpoint({'first': 1}) == (len(base), len(control.read_bytes()))
        assert adapter._stream_prefixes['transcript'].raw == base
    else:
        members, prefixes = capture._live_streams(value, stream_files=anchors,
            transcript_bytes=len(base), control_bytes=len(control.read_bytes()))
        assert prefixes[0].raw == base and prefixes[0].lines == 1
    assert appended


def test_partial_tail_is_retained_raw_and_endpoints_are_independent(tmp_path):
    native, control = files(tmp_path)
    first = native.read_bytes(); parent = control.read_bytes()
    append(native, b'{"second":2}\n{"unfinished":')
    append(control, b'{"pending":')
    adapter = endpoint({'attempt_directory': str(tmp_path)})
    assert adapter._observed_endpoint({'first': 1}) == (len(first), len(parent))
    assert adapter._observed_endpoint({'second': 2}) == (len(first + b'{"second":2}\n'), len(parent))
    member = streams.read_live_stream(str(native), 'transcript', max_bytes=4096)
    assert member.captured.raw.endswith(b'{"unfinished":')
    assert not streams.prefix(member).raw.endswith(b'{"unfinished":')
    with pytest.raises(ValueError, match='line boundary'): capture._streams(adapter.execution)
    with pytest.raises(ValueError, match='line boundary'): streams.prefix(member, len(member.captured.raw))


@pytest.mark.parametrize('role', ['transcript', 'control'])
def test_both_prior_cursors_are_compared_and_failure_does_not_advance_either(tmp_path, role):
    native, control = files(tmp_path)
    adapter = endpoint({'attempt_directory': str(tmp_path)})
    adapter._observed_endpoint({'first': 1})
    prefixes, anchors = deepcopy(adapter._stream_prefixes), deepcopy(adapter._stream_files)
    append(native, b'{"second":2}\n')
    target = native if role == 'transcript' else control
    target.write_bytes(target.read_bytes().replace(b'1', b'9', 1))
    with pytest.raises(ValueError, match='previously observed'): adapter._observed_endpoint({'second': 2})
    assert adapter._stream_prefixes == prefixes and adapter._stream_files == anchors


def test_endpoint_exact_event_mismatch_retains_both_cursors(tmp_path):
    files(tmp_path); adapter = endpoint({'attempt_directory': str(tmp_path)})
    with pytest.raises(ValueError, match='next exact raw'): adapter._observed_endpoint({'wrong': 1})
    assert adapter._stream_prefixes == adapter._stream_files == {}


def test_complete_report_run_remains_strict_and_live_recapture_rechecks_prefixes(tmp_path, monkeypatch):
    adapter = endpoint({'attempt_directory': str(tmp_path)})
    adapter.selection = SimpleNamespace(registration=SimpleNamespace(pin=SimpleNamespace(path='/selected/S')))
    strict = object(); calls = []
    monkeypatch.setattr(capture, '_load', lambda path: calls.append(path) or strict)
    monkeypatch.setattr(capture, '_load_live', lambda *a, **k: pytest.fail('strict complete route used live reader'))
    assert adapter._run() is strict and calls == ['/selected/S']
    native, control = files(tmp_path)
    adapter._observed_endpoint({'first': 1})
    wrong = SimpleNamespace(transcript=prefix(native, b'{"first":9}\n'),
        control=prefix(control, control.read_bytes(), 'control'))
    def live(*args, **kwargs):
        assert kwargs['_catalogs'] is adapter._receipt_catalogs
        return wrong
    monkeypatch.setattr(capture, '_load_live', live)
    with pytest.raises(ValueError, match='parent-observed'): adapter._run((adapter._stream_prefixes['transcript'].bytes,
        adapter._stream_prefixes['control'].bytes))
