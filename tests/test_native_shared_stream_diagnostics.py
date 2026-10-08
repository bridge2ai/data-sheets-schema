"""Reader-only diagnostic schedules, not a reproduction of the hosted race."""
from copy import deepcopy
import os

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_streams as streams


@pytest.mark.parametrize('role', streams.ROLES)
@pytest.mark.parametrize('sample,stage,pass_number,at_end,reads', [
    (1, 'opened', None, False, 0),
    (2, 'before_read', 1, False, 0),
    (3, 'after_read', 1, True, 1),
    (4, 'before_read', 2, False, 1),
    (5, 'after_read', 2, True, 2),
    (6, 'final_fd', None, True, 2),
    (7, 'final_path', None, True, 2),
])
def test_exact_failed_sample_retained_without_extra_stream_reads(
        tmp_path, monkeypatch, role, sample, stage, pass_number, at_end, reads):
    path = tmp_path / (role + '.jsonl')
    raw = b'{"first":1}\n'
    path.write_bytes(raw)
    old = c.EvidencePrefix(role, str(path), raw, len(raw), c.sha(raw), 1)
    original_stat, original_read = evidence._stat, os.pread
    before = original_stat(path.stat())
    later = {**before, 'mtime_ns': before['mtime_ns'] + 10}
    samples, read_calls = [], []

    def sampled(info):
        value = original_stat(info)
        if len(samples) == sample:
            value['mtime_ns'] += 10
        samples.append(deepcopy(value))
        return value

    def read(fd, count, offset):
        read_calls.append((count, offset))
        return original_read(fd, count, offset)

    monkeypatch.setattr(evidence, '_stat', sampled)
    monkeypatch.setattr(streams.os, 'pread', read)
    with pytest.raises(streams._LiveStreamRefusal) as caught:
        streams.read_live_stream(str(path), role, max_bytes=4096, previous=old)
    exc = caught.value
    assert isinstance(exc, ValueError)
    assert exc.args == ('live native stream changed without appending bytes',)
    assert type(exc.__cause__) is ValueError and exc.__cause__.args == exc.args
    assert len(samples) == sample + 1 and len(read_calls) == reads
    expected = {
        'kind': 'native_live_stream_refusal', 'version': 1,
        'role': role, 'path': str(path), 'stage': stage, 'pass_number': pass_number,
        'offset': len(raw) if at_end else 0,
        'opened_extent': None if stage == 'opened' else len(raw),
        'max_bytes': 4096, 'earlier': before, 'later': later,
        'previous_prefix': {'bytes': len(raw), 'sha256': c.sha(raw)},
    }
    assert exc.diagnostic_json == c.canonical(expected)
    assert len(exc.diagnostic_json) <= streams.MAX_DIAGNOSTIC_BYTES
    assert path.read_bytes() == raw
    detached = streams.diagnostic_document(exc.diagnostic_json)
    detached['earlier']['size'] = 999
    assert streams.diagnostic_document(exc.diagnostic_json) == expected
    with pytest.raises(AttributeError):
        exc.diagnostic_json = b'{}'


@pytest.mark.parametrize('pass_number,failed_sample', [(1, 4), (2, 8)])
def test_second_chunk_reports_exact_offset_and_fixed_extent(tmp_path, monkeypatch, pass_number, failed_sample):
    path = tmp_path / 'transcript.jsonl'
    raw = b'x' * 70000
    path.write_bytes(raw)
    original = evidence._stat
    count = 0

    def sampled(info):
        nonlocal count
        value = original(info)
        if count == failed_sample:
            value['mtime_ns'] += 1
        count += 1
        return value

    monkeypatch.setattr(evidence, '_stat', sampled)
    with pytest.raises(streams._LiveStreamRefusal) as caught:
        streams.read_live_stream(str(path), 'transcript', max_bytes=100000)
    data = streams.diagnostic_document(caught.value.diagnostic_json)
    assert data['stage'] == 'before_read' and data['pass_number'] == pass_number
    assert data['offset'] == 65536 and data['opened_extent'] == len(raw)
    assert data['previous_prefix'] is None and count == failed_sample + 1


def test_injected_split_field_ambiguity_is_recorded_not_diagnosed(tmp_path, monkeypatch):
    """A synthetic metadata schedule cannot establish the hosted failure cause."""
    path = tmp_path / 'control.jsonl'
    path.write_bytes(b'{}\n')
    real = evidence._stat
    before = real(path.stat())
    # The first fstat presents a larger extent but the original timestamp;
    # the next presents that same extent and another timestamp. No retry is
    # allowed and no byte read occurs. This models observations, not stat(2).
    first = {**before, 'size': before['size'] + 4}
    second = {**first, 'mtime_ns': before['mtime_ns'] + 1}
    schedule = iter([before, first, second])
    monkeypatch.setattr(evidence, '_stat', lambda info: next(schedule))
    monkeypatch.setattr(streams.os, 'pread', lambda *args: pytest.fail('refusal must precede first read'))
    with pytest.raises(streams._LiveStreamRefusal) as caught:
        streams.read_live_stream(str(path), 'control', max_bytes=4096)
    data = streams.diagnostic_document(caught.value.diagnostic_json)
    assert data['earlier'] == first and data['later'] == second
    assert data['opened_extent'] == first['size']
    assert data['stage'] == 'before_read' and data['pass_number'] == 1 and data['offset'] == 0
    assert 'cause' not in data and 'diagnosis' not in data


@pytest.mark.parametrize('change,message', [
    ({'inode': 999999}, 'live native stream physical identity changed'),
    ({'device': 999999}, 'live native stream physical identity changed'),
    ({'links': 2}, 'captured member requires exact regular single-link metadata'),
    ({'regular': False}, 'captured member requires exact regular single-link metadata'),
    ({'symlink': True}, 'captured member requires exact regular single-link metadata'),
    ({'size': 0}, 'live native stream shrank or exceeded its byte bound'),
    ({'size': 4097}, 'live native stream shrank or exceeded its byte bound'),
])
def test_other_sample_guards_retain_original_refusal_and_exact_metadata(tmp_path, monkeypatch, change, message):
    path = tmp_path / 'transcript.jsonl'
    path.write_bytes(b'{}\n')
    real = evidence._stat
    before = real(path.stat())
    later = {**before, **change}
    schedule = iter([before, later])
    monkeypatch.setattr(evidence, '_stat', lambda info: next(schedule))
    monkeypatch.setattr(streams.os, 'pread', lambda *args: pytest.fail('guard must precede read'))
    with pytest.raises(streams._LiveStreamRefusal) as caught:
        streams.read_live_stream(str(path), 'transcript', max_bytes=4096)
    assert caught.value.args == (message,)
    data = streams.diagnostic_document(caught.value.diagnostic_json)
    assert data['earlier'] == before and data['later'] == later and data['stage'] == 'opened'


def test_no_diagnostic_compatibility_progress_call_keeps_exact_exception_type(tmp_path):
    path = tmp_path / 'sample'
    path.write_bytes(b'x')
    before = evidence._stat(path.stat())
    with pytest.raises(ValueError) as caught:
        streams._progress(before, {**before, 'mtime_ns': before['mtime_ns'] + 1}, 4096)
    assert type(caught.value) is ValueError


def test_reader_guard_before_sample_has_no_invented_diagnostic(tmp_path):
    path = tmp_path / 'transcript.jsonl'
    path.write_bytes(b'{}\n')
    with pytest.raises(ValueError, match='exceeds its byte bound') as caught:
        streams.read_live_stream(str(path), 'transcript', max_bytes=1)
    assert type(caught.value) is ValueError
    assert not hasattr(caught.value, 'diagnostic_json')
