"""The registered thinking display the proxy adds, and first-thinking-event timing (#2464).

Synthetic upstreams and ledgers only; nothing is sent to a provider."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]

import native_proxy
from budgeted_cborg import BudgetStop, Ledger
from native_proxy import (NativeProxy, THINKING_DISPLAY, StreamTiming, substitute_thinking,
                          thinking_display_evidence, validated_thinking_display)
from native_controls.test_native_proxy import PRICES, REQUEST, events, wire

ADAPTIVE = {**REQUEST, 'thinking': {'type': 'adaptive'}}
DISPLAYED = {'type': 'adaptive', 'display': 'summarized'}
SUMMARY = 'Summary'


def compact(value):
    """The CLI's own serialization: compact separators, as `derive_request` saw live (#2463)."""
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode()


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def thinking_stream(text=SUMMARY):
    return [
        {'type': 'message_start', 'message': {'id': 'offline', 'model': 'claude-opus-5', 'role': 'assistant',
         'type': 'message', 'content': [], 'usage': {'input_tokens': 100, 'output_tokens': 0}, 'stop_reason': None}},
        {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'thinking', 'thinking': '', 'signature': ''}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'thinking_delta', 'thinking': text}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'signature_delta', 'signature': 'sig'}},
        {'type': 'content_block_stop', 'index': 0},
        {'type': 'content_block_start', 'index': 1, 'content_block': {'type': 'text', 'text': ''}},
        {'type': 'content_block_delta', 'index': 1, 'delta': {'type': 'text_delta', 'text': 'offline fixture'}},
        {'type': 'content_block_stop', 'index': 1},
        {'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}, 'usage': {'output_tokens': 12}},
        {'type': 'message_stop'}]


def ticking(values, clock, *, status=200, error=None):
    """One event per chunk, each arriving one second after the last."""
    class Body(httpx.SyncByteStream):
        def __iter__(self):
            for value in values:
                clock.now += 1.0
                yield wire([value])
            if error is not None:
                raise error
    return httpx.Response(status, stream=Body(), headers={'content-type': 'text/event-stream'})


def proxy_for(tmp_path, script, *, display=THINKING_DISPLAY, clock=None, **options):
    calls, counts, outcomes = [], [], iter(script)
    def respond(request):
        calls.append(request)
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome(request) if callable(outcome) else outcome
    def count_tokens(**fields):
        counts.append(fields)
        return SimpleNamespace(input_tokens=100)
    ledger = Ledger(tmp_path / 'ledger.json', manifest_sha256='offline', attempt_cap=5)
    proxy = NativeProxy(sdk=SimpleNamespace(messages=SimpleNamespace(count_tokens=count_tokens)), ledger=ledger,
        attempt='native-offline', evidence=tmp_path / 'requests', model=REQUEST['model'], prices=PRICES,
        verify=lambda: None, provider_key='offline-provider-key', base_url='https://api.cborg.lbl.gov',
        upstream=httpx.Client(transport=httpx.MockTransport(respond)),
        **({'thinking_display': display} if display is not None else {}),
        **({'clock': clock} if clock is not None else {}), **options)
    return proxy, ledger, calls, counts


def post(url, proxy, raw, path='/v1/messages?beta=true'):
    return httpx.post(url + path, content=raw, headers={'x-api-key': proxy.token, 'content-type': 'application/json'})


def folder_of(tmp_path):
    (folder,) = [p for p in (tmp_path / 'requests').iterdir() if p.is_dir()]
    return folder


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


# --- the selection -------------------------------------------------------------------------------

@pytest.mark.parametrize('value', [{}, {**THINKING_DISPLAY, 'display': 'omitted'},
    {**THINKING_DISPLAY, 'delivery': 'cli_flag'}, {**THINKING_DISPLAY, 'extra': 1}, 'summarized', True])
def test_only_the_exact_selection_is_accepted(tmp_path, value):
    with pytest.raises(BudgetStop, match='thinking_display_v1'):
        validated_thinking_display(value)
    with pytest.raises(BudgetStop):
        proxy_for(tmp_path, [], display=value)


def test_without_the_selection_every_request_is_forwarded_as_sent(tmp_path):
    raw = compact(ADAPTIVE)
    proxy, ledger, calls, _ = proxy_for(tmp_path, [httpx.Response(200, content=wire(events()),
                                        headers={'content-type': 'text/event-stream'})], display=None)
    with proxy.running() as url:
        assert post(url, proxy, raw).content == wire(events())
    assert calls[0].content == raw
    folder = folder_of(tmp_path)
    assert not any((folder / name).exists() for name in native_proxy.THINKING_EVIDENCE)
    assert not (tmp_path / 'thinking_refusals').exists()


# --- substitution ------------------------------------------------------------------------------

def test_the_registered_display_is_added_and_only_it(tmp_path):
    raw = compact(ADAPTIVE)
    proxy, ledger, calls, counts = proxy_for(tmp_path, [httpx.Response(200, content=wire(events()),
                                             headers={'content-type': 'text/event-stream'})])
    with proxy.running() as url:
        reply = post(url, proxy, raw)
    assert reply.status_code == 200 and reply.content == wire(events())
    sent = calls[0].content
    assert sent == raw.replace(b'"thinking":{"type":"adaptive"}', b'"thinking":{"type":"adaptive","display":"summarized"}')
    assert json.loads(sent) == {**ADAPTIVE, 'thinking': DISPLAYED}
    folder = folder_of(tmp_path)
    assert (folder / 'native_request.json').read_bytes() == raw               # the child's own bytes
    assert (folder / 'forwarded_request.json').read_bytes() == sent
    record = json.loads((folder / 'thinking_request.json').read_text())
    assert record == {'kind': 'thinking_display_request_v1', 'registered': THINKING_DISPLAY,
                      'disposition': 'substituted', 'native_request_sha256': sha(raw),
                      'forwarded_request_sha256': sha(sent)}
    # Counted, reserved and bound in the ledger as it was sent.
    assert counts[-1]['thinking'] == DISPLAYED
    (row,) = json.loads(ledger.path.read_text())['requests']
    assert json.loads((folder / 'request.json').read_text()) == json.loads(sent)
    assert row['request_sha256'] == sha((folder / 'request.json').read_bytes())
    summary = thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=True)
    assert [r['disposition'] for r in summary['requests']] == ['substituted'] and summary['refusals'] == 0


def test_a_side_call_with_thinking_disabled_is_forwarded_unchanged(tmp_path):
    raw = compact({**REQUEST, 'thinking': {'type': 'disabled'}})
    proxy, _, calls, _ = proxy_for(tmp_path, [httpx.Response(200, content=wire(events()),
                                   headers={'content-type': 'text/event-stream'})])
    with proxy.running() as url:
        assert post(url, proxy, raw).status_code == 200
    assert calls[0].content == raw
    folder = folder_of(tmp_path)
    assert not (folder / 'forwarded_request.json').exists()
    assert json.loads((folder / 'thinking_request.json').read_text())['disposition'] == 'disabled_forwarded'
    thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=True)


@pytest.mark.parametrize('raw', [
    compact(REQUEST),                                                                   # no thinking at all
    compact({**REQUEST, 'thinking': {'type': 'enabled', 'budget_tokens': 1024}}),
    compact({**REQUEST, 'thinking': DISPLAYED}),                                        # already displayed
    compact({**REQUEST, 'thinking': {'type': 'adaptive', 'extra': True}}),
    compact({**ADAPTIVE, 'metadata': {'thinking': {'type': 'adaptive'}}}),              # the pattern twice
    json.dumps(ADAPTIVE, indent=1).encode(),                                            # not the CLI's bytes
], ids=['absent', 'enabled', 'displayed', 'extra_key', 'twice', 'indented'])
def test_anything_else_is_refused_before_it_is_counted_reserved_or_sent(tmp_path, raw):
    proxy, ledger, calls, counts = proxy_for(tmp_path, [])
    with proxy.running() as url:
        reply = post(url, proxy, raw)
    assert reply.status_code == 402 and calls == [] and counts == []
    assert proxy.failure and 'thinking' in proxy.failure
    assert not ledger.path.exists() or json.loads(ledger.path.read_text())['requests'] == []
    (refusal,) = (tmp_path / 'thinking_refusals').iterdir()
    value = json.loads(refusal.read_text())
    assert value['paid_request'] is False and value['native_request_sha256'] == sha(raw)
    assert thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=False)['refusals'] == 1


def test_a_refusal_under_a_stall_policy_stops_without_a_debit(tmp_path):
    """Pins the combined behaviour, whatever the mechanism: the refusal precedes any
    ticket, so no stall policy can debit it and the attempt stops (#2556)."""
    proxy, ledger, calls, _ = proxy_for(tmp_path, [], stall_policy={'count_attempts': 3, 'max_stall_debits': 4},
                                        count_pause=lambda seconds: None)
    with proxy.running() as url:
        assert post(url, proxy, compact(REQUEST)).status_code == 402
    assert calls == [] and proxy.stalls_survived == 0 and proxy.failed.is_set()
    assert not ledger.path.exists() or json.loads(ledger.path.read_text())['requests'] == []


def test_the_childs_own_count_passes_untouched(tmp_path):
    proxy, _, _, counts = proxy_for(tmp_path, [])
    with proxy.running() as url:
        reply = post(url, proxy, compact(ADAPTIVE), '/v1/messages/count_tokens')
    assert reply.status_code == 200 and counts[-1]['thinking'] == {'type': 'adaptive'}


def test_substitution_proves_its_own_result():
    raw = compact(ADAPTIVE)
    forwarded, disposition = substitute_thinking(raw, THINKING_DISPLAY)
    assert disposition == 'substituted' and json.loads(forwarded)['thinking'] == DISPLAYED


# --- timing of the first thinking event --------------------------------------------------------

def test_the_first_thinking_event_is_timed_without_changing_delivery(tmp_path):
    clock = Clock()
    values = thinking_stream()
    proxy, _, _, _ = proxy_for(tmp_path, [lambda request: ticking(values, clock)], clock=clock)
    with proxy.running() as url:
        reply = post(url, proxy, compact(ADAPTIVE))
    assert reply.content == wire(values)                                    # the child's bytes, exactly
    kept = (folder_of(tmp_path) / 'stream_timing.json').read_text()
    timing = json.loads(kept)
    assert SUMMARY not in kept                                              # counts and times, never text
    assert (timing['first_chunk_seconds'], timing['first_thinking_block_seconds'],
            timing['first_thinking_text_seconds'], timing['first_output_block_seconds'],
            timing['last_chunk_seconds']) == (1.0, 2.0, 3.0, 6.0, 10.0)
    assert timing['thinking_text_chars'] == len(SUMMARY) and timing['thinking_display_observed'] == 'summarized_text'
    assert timing['outcome'] == 'completed' and timing['observer_errors'] == 0 and timing['upstream_status'] == 200
    # Headers arrive before the first second's chunk; the child's headers are sent before the first byte (#2553).
    assert timing['headers_seconds'] == 0.0 and timing['child_headers_seconds'] == 0.0
    assert timing['largest_gap_between_chunks_seconds'] == 1.0 and timing['chunks'] == len(values)
    assert timing['bytes'] == len(wire(values)) and timing['error_type'] is None
    assert timing['events']['content_block_start:thinking'] == {'count': 1, 'first_seconds': 2.0, 'last_seconds': 2.0}
    assert timing['events']['content_block_delta:thinking_delta']['count'] == 1
    summary = thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=True)
    assert summary['requests'][0]['timing']['first_thinking_block_seconds'] == 2.0


def test_a_hidden_thinking_block_is_no_text(tmp_path):
    clock = Clock()
    proxy, _, _, _ = proxy_for(tmp_path, [lambda request: ticking(thinking_stream(''), clock)], clock=clock)
    with proxy.running() as url:
        assert post(url, proxy, compact(ADAPTIVE)).status_code == 200
    timing = json.loads((folder_of(tmp_path) / 'stream_timing.json').read_text())
    assert timing['thinking_display_observed'] == 'no_text' and timing['first_thinking_text_seconds'] is None


def test_buffered_delivery_is_timed_after_the_last_upstream_byte(tmp_path):
    clock = Clock()
    values = thinking_stream()
    proxy, _, _, _ = proxy_for(tmp_path, [lambda request: ticking(values, clock)], clock=clock,
        stall_policy={'count_attempts': 3, 'max_stall_debits': 4}, count_pause=lambda seconds: None,
        response_buffer={'kind': 'complete_response_v1', 'max_bytes': 16 * 1024 * 1024, 'total_seconds': 1200})
    with proxy.running() as url:
        assert post(url, proxy, compact(ADAPTIVE)).content == wire(values)
    timing = json.loads((folder_of(tmp_path) / 'stream_timing.json').read_text())
    assert timing['child_headers_seconds'] >= timing['last_chunk_seconds'] == 10.0


def test_an_observer_failure_never_touches_accounting_or_delivery(tmp_path, monkeypatch):
    def broken(self, raw):
        raise RuntimeError('observer')
    monkeypatch.setattr(StreamTiming, '_chunk', broken)
    clock = Clock()
    values = thinking_stream()
    proxy, ledger, _, _ = proxy_for(tmp_path, [lambda request: ticking(values, clock)], clock=clock)
    with proxy.running() as url:
        assert post(url, proxy, compact(ADAPTIVE)).content == wire(values)
    (row,) = json.loads(ledger.path.read_text())['requests']
    assert row['status'] == 'settled'
    assert json.loads((folder_of(tmp_path) / 'stream_timing.json').read_text())['observer_errors'] == len(values)


def test_timing_is_kept_for_a_survived_stall_and_a_cut_stream(tmp_path):
    clock = Clock()
    policy = {'count_attempts': 3, 'max_stall_debits': 4}
    cut = httpx.ReadError('cut', request=httpx.Request('POST', 'https://offline.invalid'))
    proxy, _, _, _ = proxy_for(tmp_path, [httpx.Response(524), lambda request: ticking(thinking_stream()[:3], clock, error=cut)],
                               clock=clock, stall_policy=policy, count_pause=lambda seconds: None)
    with proxy.running() as url:
        assert post(url, proxy, compact(ADAPTIVE)).status_code == 503
        post(url, proxy, compact(ADAPTIVE))
    outcomes = sorted((json.loads(p.read_text())['outcome'], json.loads(p.read_text())['error_type'])
                      for p in (tmp_path / 'requests').rglob('stream_timing.json'))
    assert outcomes == [('failed', 'ReadError'), ('stalled_survived', 'UpstreamStall')]
    assert all('cut' not in p.read_text() for p in (tmp_path / 'requests').rglob('stream_timing.json'))


# --- the retained bytes prove the handling -----------------------------------------------------

@pytest.mark.parametrize('tamper', ['forwarded', 'native', 'record', 'canonical'])
def test_the_evidence_is_re_read_from_the_bytes(tmp_path, tamper):
    proxy, _, _, _ = proxy_for(tmp_path, [httpx.Response(200, content=wire(events()),
                               headers={'content-type': 'text/event-stream'})])
    with proxy.running() as url:
        post(url, proxy, compact(ADAPTIVE))
    folder = folder_of(tmp_path)
    if tamper == 'forwarded':
        (folder / 'forwarded_request.json').write_bytes(compact({**ADAPTIVE, 'thinking': {'type': 'adaptive'}}))
    elif tamper == 'native':
        (folder / 'native_request.json').write_bytes(compact({**ADAPTIVE, 'max_tokens': 7}))
    elif tamper == 'record':
        (folder / 'thinking_request.json').unlink()
    else:
        (folder / 'request.json').write_text(json.dumps({**ADAPTIVE, 'max_tokens': 7}))
    with pytest.raises(BudgetStop, match='not proven'):
        thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=True)
    report = thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=False)
    assert report['requests'] == [] and len(report['problems']) == 1


def test_the_report_form_never_raises(tmp_path):
    report = thinking_display_evidence(tmp_path / 'missing', THINKING_DISPLAY, strict=False)
    assert report['requests'] == [] and report['problems'] == []
    assert thinking_display_evidence(tmp_path, {'bad': 1}, strict=False)['problems']


def test_a_completed_run_cannot_carry_a_refusal(tmp_path):
    """The strict form fails where any request was refused, even if every admitted one is proven."""
    proxy, _, _, _ = proxy_for(tmp_path, [httpx.Response(200, content=wire(events()),
                               headers={'content-type': 'text/event-stream'})])
    with proxy.running() as url:
        post(url, proxy, compact(ADAPTIVE))
    assert thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=True)['refusals'] == 0
    (tmp_path / 'thinking_refusals').mkdir()
    (tmp_path / 'thinking_refusals' / 'synthetic.json').write_text('{}')
    with pytest.raises(BudgetStop, match='refused thinking setting'):
        thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=True)



# --- review of #2543 --------------------------------------------------------------------------

@pytest.mark.parametrize('raw', [
    compact(ADAPTIVE)[:-1] + b',"max_tokens":5}',
    compact({**REQUEST, 'thinking': {'type': 'disabled'}})[:-1] + b',"thinking":{"type":"adaptive"}}',
    # Forwarded unchanged if read last-wins: only the strict admission parse refuses these.
    compact(ADAPTIVE)[:-1] + b',"thinking":{"type":"disabled"}}',
    compact({**REQUEST, 'thinking': {'type': 'disabled'}})[:-1] + b',"stream":true}',
], ids=['duplicate_max_tokens', 'two_thinking_members', 'disabled_last', 'duplicate_on_side_call'])
def test_a_duplicate_key_is_refused_before_it_is_paid(tmp_path, raw):
    """#2544: admission parses as strictly as the evidence gate re-reads."""
    proxy, ledger, calls, counts = proxy_for(tmp_path, [])
    with proxy.running() as url:
        assert post(url, proxy, raw).status_code == 402
    assert calls == [] and counts == [] and len(list((tmp_path / 'thinking_refusals').iterdir())) == 1


def test_an_already_displayed_nested_member_is_refused(tmp_path):
    """#2549: the child cannot carry the displayed setting anywhere, even nested."""
    raw = compact({**ADAPTIVE, 'metadata': {'thinking': DISPLAYED}})
    with pytest.raises(BudgetStop, match='registered display exactly'):
        substitute_thinking(raw, THINKING_DISPLAY)


def _settled(tmp_path, body):
    proxy, _, _, _ = proxy_for(tmp_path, [httpx.Response(200, content=wire(events()),
                               headers={'content-type': 'text/event-stream'})])
    with proxy.running() as url:
        assert post(url, proxy, compact(body)).status_code == 200
    return folder_of(tmp_path)


def _rehash(folder, **changes):
    record = json.loads((folder / 'thinking_request.json').read_text())
    record.update(changes)
    if (folder / 'forwarded_request.json').exists():
        record['forwarded_request_sha256'] = sha((folder / 'forwarded_request.json').read_bytes())
    (folder / 'thinking_request.json').write_text(json.dumps(record))


@pytest.mark.parametrize('forwarded', [
    lambda raw: raw.replace(b'"thinking":{"type":"adaptive"}', b'"thinking":{"type":"adaptive", "display":"summarized"}'),
    lambda raw: raw,                                                   # the display was never added
    lambda raw: raw.replace(b'"thinking":{"type":"adaptive"}', b'"thinking":{"type":"adaptive","display":"summarized"}').replace(b'1000', b'1001'),
], ids=['respaced', 'undisplayed', 'other_field'])
def test_the_forwarded_bytes_must_be_the_child_bytes_with_only_the_display(tmp_path, forwarded):
    """#2547: the record's hash is made consistent, so only the proof itself can refuse."""
    folder = _settled(tmp_path, ADAPTIVE)
    (folder / 'forwarded_request.json').write_bytes(forwarded((folder / 'native_request.json').read_bytes()))
    _rehash(folder)
    with pytest.raises(BudgetStop, match='only the registered display'):
        thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=True)


@pytest.mark.parametrize('damage, match', [
    ('forwarded_file', 'forwarded unchanged'), ('adaptive_child', 'forwarded unchanged'),
    ('unknown', 'unknown thinking disposition'), ('registered', 'does not name'), ('kind', 'does not name')])
def test_each_refusal_of_the_evidence_proof_is_reachable(tmp_path, damage, match):
    """#2548: the disabled branch, an unknown disposition and the record's own fields."""
    folder = _settled(tmp_path, {**REQUEST, 'thinking': {'type': 'disabled'}})
    if damage == 'forwarded_file':
        (folder / 'forwarded_request.json').write_bytes((folder / 'native_request.json').read_bytes())
    elif damage == 'adaptive_child':
        child = compact(ADAPTIVE)
        (folder / 'native_request.json').write_bytes(child)
        (folder / 'request.json').write_text(json.dumps(ADAPTIVE, sort_keys=True) + '\n')
        _rehash(folder, native_request_sha256=sha(child), forwarded_request_sha256=sha(child))
    elif damage == 'unknown':
        _rehash(folder, disposition='rewritten')
    elif damage == 'registered':
        _rehash(folder, registered={**THINKING_DISPLAY, 'display': 'omitted'})
    else:
        _rehash(folder, kind='thinking_display_request_v0')
    with pytest.raises(BudgetStop, match=match):
        thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=True)


def test_frames_split_anywhere_and_crlf_lines_are_observed_alike():
    """#2552: every chunk boundary, LF and CRLF framing give the same timing."""
    values = thinking_stream()
    whole = wire(values)
    def observe(raw, cuts):
        clock = Clock(); timing = StreamTiming(clock, clock.now)
        pieces = [raw[a:b] for a, b in zip([0, *cuts], [*cuts, len(raw)])]
        for piece in pieces:
            timing.chunk(piece)
        return timing.result('completed', None)
    expected = observe(whole, [])
    for raw in (whole, whole.replace(b'\n', b'\r\n')):
        for cut in range(1, len(raw)):
            got = observe(raw, [cut])
            assert (got['events'], got['thinking_text_chars'], got['observer_errors']) == (
                expected['events'], expected['thinking_text_chars'], 0), cut


def test_an_unterminated_frame_beyond_the_bound_is_dropped_not_buffered(monkeypatch):
    """#2546: observation is bounded; delivery never depends on it."""
    monkeypatch.setattr(StreamTiming, 'MAX_FRAME_BYTES', 64)
    clock = Clock(); timing = StreamTiming(clock, clock.now)
    timing.chunk(b'data: ' + b'x' * 100)
    assert timing.result('completed', None)['observer_errors'] == 1 and len(timing.buffer) == 0
    timing.chunk(wire(thinking_stream()))
    assert timing.result('completed', None)['thinking_display_observed'] == 'summarized_text'



def _write_folder(folder, native, forwarded=None, *, disposition='substituted', canonical=None, forwarded_sha=None):
    """Replace a settled folder's retained bytes with a consistent-looking set."""
    (folder / 'native_request.json').write_bytes(native)
    if forwarded is None:
        (folder / 'forwarded_request.json').unlink(missing_ok=True)
    else:
        (folder / 'forwarded_request.json').write_bytes(forwarded)
    sent = forwarded if forwarded is not None else native
    (folder / 'request.json').write_text(json.dumps(canonical if canonical is not None else json.loads(sent),
                                                    sort_keys=True) + '\n')
    (folder / 'thinking_request.json').write_text(json.dumps({'kind': 'thinking_display_request_v1',
        'registered': THINKING_DISPLAY, 'disposition': disposition, 'native_request_sha256': sha(native),
        'forwarded_request_sha256': forwarded_sha or sha(sent)}))


@pytest.mark.parametrize('case', ['wrong_forwarded_hash', 'already_displayed_child', 'doubly_rewritten'])
def test_each_substituted_clause_refuses_on_its_own(tmp_path, case):
    """#2559: the proof holds from the retained bytes, without assuming admission."""
    folder = _settled(tmp_path, ADAPTIVE)
    swap = lambda raw: raw.replace(b'"thinking":{"type":"adaptive"}', b'"thinking":{"type":"adaptive","display":"summarized"}')
    if case == 'wrong_forwarded_hash':
        native = compact(ADAPTIVE)
        _write_folder(folder, native, swap(native), forwarded_sha='0' * 64)
    elif case == 'already_displayed_child':
        native = compact({**REQUEST, 'thinking': DISPLAYED})
        _write_folder(folder, native, native)                        # the replace is a no-op
    else:
        native = compact({**ADAPTIVE, 'metadata': {'thinking': {'type': 'adaptive'}}})
        _write_folder(folder, native, swap(native))                  # both occurrences rewritten
    with pytest.raises(BudgetStop, match='only the registered display'):
        thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=True)


@pytest.mark.parametrize('case', ['wrong_forwarded_hash', 'rewritten_request'])
def test_each_disabled_clause_refuses_on_its_own(tmp_path, case):
    """#2560: the side call's record hash and its canonical request are both proven."""
    body = {**REQUEST, 'thinking': {'type': 'disabled'}}
    folder = _settled(tmp_path, body)
    native = compact(body)
    if case == 'wrong_forwarded_hash':
        _write_folder(folder, native, disposition='disabled_forwarded', forwarded_sha='0' * 64)
    else:
        _write_folder(folder, native, disposition='disabled_forwarded', canonical={**body, 'max_tokens': 7})
    with pytest.raises(BudgetStop, match='forwarded unchanged'):
        thinking_display_evidence(tmp_path / 'requests', THINKING_DISPLAY, strict=True)
