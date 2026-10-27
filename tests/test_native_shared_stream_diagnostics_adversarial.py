"""Independent diagnostic-only refusal controls; no native runtime or helper.

Real reader/adapter methods run against tiny local streams. Only diagnostic
failure injection and the already-authorized lifetime/state plumbing are stubs.
"""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_streams as streams
from data_sheets_schema.native_shared_controller import CallbackAdapter
from data_sheets_schema.native_shared_receipts import _ReceiptCatalogContext


TEXT = 'live native stream changed without appending bytes'
STOP = 'native shared observation failed: ValueError: ' + TEXT


class Stopped(Exception):
    pass


def metadata():
    return dict(exists=True, regular=True, symlink=False, links=1,
                device=1, inode=2, size=16, mtime_ns=3)


def context(path='/synthetic/transcript.jsonl'):
    return dict(role='transcript', path=path, stage='before_read',
                pass_number=2, offset=0, opened_extent=16,
                previous_prefix={'bytes': 4, 'sha256': c.sha(b'old\n')})


def refusal(*, selected=None):
    earlier = metadata()
    with pytest.raises(streams._LiveStreamRefusal) as caught:
        streams._progress(earlier, {**earlier, 'mtime_ns': 4}, 4096,
                          diagnostic=context() if selected is None else selected)
    return caught.value


def adapter(tmp_path):
    """Exercise actual observation/report methods without launch admission."""
    selected = CallbackAdapter.__new__(CallbackAdapter)
    selected.raw = b'invented test-only composition'
    selected.execution = {'attempt_directory': str(tmp_path)}
    selected.failure = selected.final_evidence = selected.recorder_identity = None
    selected._stream_diagnostic_json = None
    selected.recorder_done = False
    selected._activated = selected._initialized = True
    selected._stream_prefixes, selected._stream_files = {}, {}
    selected._receipt_catalogs = _ReceiptCatalogContext()
    selected.controls = {'budgeted_cborg': SimpleNamespace(BudgetStop=Stopped)}
    selected.state = SimpleNamespace(report=lambda **kw: {'draft_gate_passed': True, 'problems': []})
    selected.phase = SimpleNamespace(report=lambda **kw: {'synthetic_phase': 'unchanged'})
    return selected


def seed(tmp_path):
    first, second = {'first': 1}, {'second': 2}
    raw = c.canonical(first) + b'\n'
    transcript = tmp_path / 'transcript.jsonl'
    control = tmp_path / 'control.jsonl'
    transcript.write_bytes(raw)
    control.write_bytes(b'{"control":1}\n')
    selected = adapter(tmp_path)
    selected._observed_endpoint(first)
    old = deepcopy(selected._stream_prefixes), deepcopy(selected._stream_files)
    with transcript.open('ab') as out:
        out.write(c.canonical(second) + b'\n')
    return selected, old, second, transcript, control


def test_exception_owns_complete_metadata_bytes_and_decodes_detached():
    earlier, later, detail = metadata(), metadata(), context()
    later['mtime_ns'] += 1
    expected = {'kind': 'native_live_stream_refusal', 'version': 1,
                **deepcopy(detail), 'max_bytes': 4096,
                'earlier': deepcopy(earlier), 'later': deepcopy(later)}
    with pytest.raises(streams._LiveStreamRefusal) as caught:
        streams._progress(earlier, later, 4096, diagnostic=detail)
    error = caught.value
    assert isinstance(error, ValueError) and error.args == (TEXT,)
    assert type(error.__cause__) is ValueError and error.__cause__.args == error.args
    raw = error.diagnostic_json
    assert type(raw) is bytes and raw == c.canonical(expected)
    earlier['size'] = 900
    later['mtime_ns'] = -1
    detail['previous_prefix']['sha256'] = 'mutated'
    detached = streams.diagnostic_document(raw)
    detached['earlier']['size'] = 0
    detached['previous_prefix']['bytes'] = 0
    assert streams.diagnostic_document(error.diagnostic_json) == expected
    with pytest.raises(AttributeError):
        error.diagnostic_json = b'{}'


@pytest.mark.parametrize('change', [dict(mtime_ns=4), dict(inode=7), dict(size=0), dict(links=2)])
def test_existing_progress_reason_and_arguments_are_unchanged(change, monkeypatch):
    before = metadata(); after = {**before, **change}
    def forbidden(*args, **kwargs):
        pytest.fail('diagnostic attempted additional filesystem acquisition')
    with monkeypatch.context() as patch:
        for name in ('open', 'stat', 'lstat', 'fstat', 'pread', 'read', 'write'):
            patch.setattr(streams.os, name, forbidden)
        with pytest.raises(ValueError) as original:
            streams._progress(before, after, 4096)
        with pytest.raises(streams._LiveStreamRefusal) as enriched:
            streams._progress(before, after, 4096, diagnostic=context())
    assert type(original.value) is ValueError
    assert enriched.value.args == original.value.args
    assert str(enriched.value) == str(original.value)
    saved = streams.diagnostic_document(enriched.value.diagnostic_json)
    assert saved['earlier'] == before and saved['later'] == after


@pytest.mark.parametrize('failure', ['encoding', 'decoding', 'byte_bound'])
def test_diagnostic_failure_preserves_plain_original_valueerror(monkeypatch, failure):
    before = metadata()
    def broken(*args, **kwargs):
        raise RuntimeError('synthetic diagnostic failure')
    if failure == 'encoding':
        monkeypatch.setattr(streams.c, 'canonical', broken)
    elif failure == 'decoding':
        monkeypatch.setattr(streams, 'diagnostic_document', broken)
    else:
        monkeypatch.setattr(streams, 'MAX_DIAGNOSTIC_BYTES', 1)
    with pytest.raises(ValueError) as caught:
        streams._progress(before, {**before, 'mtime_ns': 4}, 4096, diagnostic=context())
    assert type(caught.value) is ValueError and caught.value.args == (TEXT,)
    assert not hasattr(caught.value, 'diagnostic_json')


@pytest.mark.parametrize('site', ['endpoint_control', 'recapture'])
def test_first_stream_failure_keeps_existing_cursor_timing_and_stop(tmp_path, monkeypatch, site):
    selected, old, event, transcript, control = seed(tmp_path)
    source_bytes = transcript.read_bytes(), control.read_bytes()
    progress = streams._progress
    if site == 'endpoint_control':
        def changed(before, after, maximum, *, diagnostic=None):
            if diagnostic and diagnostic['role'] == 'control' and diagnostic['stage'] == 'opened':
                after = {**after, 'size': before['size'], 'mtime_ns': before['mtime_ns'] + 1}
            return progress(before, after, maximum, diagnostic=diagnostic)
        monkeypatch.setattr(streams, '_progress', changed)
        monkeypatch.setattr(selected, '_run', lambda *a: pytest.fail('failed endpoint reached recapture'))
    else:
        error = refusal(selected=context(str(transcript)))
        def recapture(endpoints=None):
            assert endpoints == (len(source_bytes[0]), len(source_bytes[1]))
            raise error
        monkeypatch.setattr(selected, '_run', recapture)
    with pytest.raises(Stopped, match=TEXT):
        selected.observe(event)
    assert selected.failure == STOP
    if site == 'endpoint_control':
        assert (selected._stream_prefixes, selected._stream_files) == old
    else:
        assert selected._stream_prefixes['transcript'].raw == source_bytes[0]
        assert selected._stream_prefixes['transcript'] != old[0]['transcript']
        assert selected._stream_files == old[1]
    first = selected.report(complete=True)
    assert first['controller_stop'] == STOP and first['draft_gate_passed'] is False
    assert first['phase_history'] == {'synthetic_phase': 'unchanged'}
    assert first['stream_diagnostic']['role'] == ('control' if site == 'endpoint_control' else 'transcript')
    raw = c.canonical(first['stream_diagnostic'])
    first['stream_diagnostic']['earlier']['size'] = 0
    first['stream_diagnostic']['path'] = 'caller mutation'
    monkeypatch.setattr(selected, '_observed_endpoint', lambda *a: pytest.fail('stopped adapter reacquired streams'))
    monkeypatch.setattr(selected, '_run', lambda *a: pytest.fail('failed report recovered live history'))
    with pytest.raises(Stopped) as later:
        selected.observe({'third': 3})
    assert str(later.value) == STOP
    report = selected.report(complete=True)
    assert c.canonical(report['stream_diagnostic']) == raw
    assert json.loads(c.canonical(report))['controller_stop'] == STOP
    assert (transcript.read_bytes(), control.read_bytes()) == source_bytes


def test_unrelated_first_stop_cannot_later_acquire_stream_diagnostic(tmp_path, monkeypatch):
    selected = adapter(tmp_path)
    def unrelated(*args):
        raise ValueError('ordinary existing refusal')
    monkeypatch.setattr(selected, '_observed_endpoint', unrelated)
    with pytest.raises(Stopped):
        selected.observe({})
    original = selected.failure
    selected._failure_detail(refusal())
    monkeypatch.setattr(selected, '_run', lambda *a: pytest.fail('prior failure entered complete replay'))
    result = selected.report(complete=True)
    assert result['controller_stop'] == original
    assert 'stream_diagnostic' not in result
    assert selected._stream_diagnostic_json is None


@pytest.mark.parametrize('site', ['latching', 'report'])
def test_adapter_decode_failure_cannot_replace_or_hide_stop(tmp_path, monkeypatch, site):
    selected = adapter(tmp_path); error = refusal()
    def failed(*args):
        raise error
    monkeypatch.setattr(selected, '_observed_endpoint', failed)
    def bad_decode(*args):
        raise ValueError('diagnostic decode deliberately unavailable')
    if site == 'latching':
        monkeypatch.setattr(streams, 'diagnostic_document', bad_decode)
    with pytest.raises(Stopped) as caught:
        selected.observe({})
    assert str(caught.value) == STOP
    if site == 'report':
        assert selected._stream_diagnostic_json == error.diagnostic_json
        monkeypatch.setattr(streams, 'diagnostic_document', bad_decode)
    report = selected.report(complete=True)
    assert report['controller_stop'] == STOP and report['draft_gate_passed'] is False
    assert 'stream_diagnostic' not in report


def test_complete_report_first_failure_preserves_valueerror_qualified_text(tmp_path, monkeypatch):
    selected = adapter(tmp_path); error = refusal()
    def fail(*args):
        raise error
    monkeypatch.setattr(selected, '_run', fail)
    report = selected.report(complete=True)
    expected = 'completed native shared history cannot be verified: ValueError: ' + TEXT
    assert report['controller_stop'] == expected and selected.failure == expected
    assert report['stream_diagnostic'] == streams.diagnostic_document(error.diagnostic_json)
    monkeypatch.setattr(selected, '_run', lambda *a: pytest.fail('failed completion was retried'))
    assert selected.report(complete=True) == report


def test_successful_ordinary_report_shape_has_no_invented_diagnostic(tmp_path):
    selected = adapter(tmp_path)
    report = selected.report()
    assert report['controller_stop'] is None and report['draft_gate_passed'] is True
    assert 'stream_diagnostic' not in report
