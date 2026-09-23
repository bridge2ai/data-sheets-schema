"""Opt-in complete-response delivery and synthetic upstream faults only (#2304)."""
from contextlib import contextmanager
from decimal import Decimal
from http.server import BaseHTTPRequestHandler
import json

import httpx
import pytest

from budgeted_cborg import BudgetStop, STALL_DEBIT_BASIS
from native_proxy import POST_SEND_FAILURES, validated_response_buffer
from native_controls.test_native_proxy import events, wire
from native_controls.test_native_stall_policy import OFFLINE, good, post, proxy_with, rows

BUFFER = {'kind': 'complete_response_v1', 'max_bytes': 16 * 1024 * 1024, 'total_seconds': 1200}


def response(chunks, error=None, *, status=200):
    class Body(httpx.SyncByteStream):
        def __iter__(self):
            yield from chunks
            if error is not None:
                raise error
    return httpx.Response(status, stream=Body(), headers={'content-type': 'text/event-stream'})


@pytest.mark.parametrize('error', POST_SEND_FAILURES)
def test_partial_tool_response_stalls_unexposed_then_retries_once(tmp_path, error):
    values = events(stop_reason='tool_use')
    values[1]['content_block'] = {'type': 'tool_use', 'id': 'synthetic_tool', 'name': 'Write', 'input': {}}
    values[2]['delta'] = {'type': 'input_json_delta', 'partial_json': '{"content":"PRIVATE_TOOL"}'}
    partial = wire(values[:4])
    proxy, ledger, calls = proxy_with(tmp_path,
        [response([partial], error('private error', request=OFFLINE)), good()], response_buffer=BUFFER)
    with proxy.running() as url:
        first = post(url, proxy)
        assert first.status_code == 503 and 'PRIVATE_TOOL' not in first.text
        second = post(url, proxy)
    assert second.status_code == 200 and second.content == wire(events())
    assert len(calls) == 2 and calls[0].content == calls[1].content and not proxy.failed.is_set()
    stalled, completed = rows(ledger)
    assert stalled['status'] == completed['status'] == 'settled'
    assert stalled['cost_usd'] == stalled['reserved_usd'] and stalled['provider_charge_confirmed'] is False
    assert stalled['settlement_basis'] == STALL_DEBIT_BASIS
    assert stalled['stall_evidence']['response_buffer'] == BUFFER
    assert stalled['stall_evidence']['response_delivery_started'] is False
    assert stalled['stall_evidence']['http_status'] == 200
    assert 'private error' not in json.dumps(stalled)
    assert Decimal(completed['cost_usd']) < Decimal(completed['reserved_usd'])


def test_upstream_closes_then_settles_before_first_local_header(tmp_path, monkeypatch):
    proxy, ledger, _ = proxy_with(tmp_path, [good()], response_buffer=BUFFER)
    upstream = proxy.upstream
    closed = []
    real_stream = upstream.stream
    @contextmanager
    def stream(*args, **kwargs):
        with real_stream(*args, **kwargs) as observed:
            yield observed
        closed.append(True)
    monkeypatch.setattr(upstream, 'stream', stream)
    real_header = BaseHTTPRequestHandler.send_response
    def header(handler, code, *args):
        if code == 200:
            assert closed and rows(ledger)[0]['status'] == 'settled'
            receipt = json.loads(next((tmp_path / 'requests').rglob('buffered_response.json')).read_bytes())
            assert receipt['complete_and_settled_before_delivery'] is True
        return real_header(handler, code, *args)
    monkeypatch.setattr(BaseHTTPRequestHandler, 'send_response', header)
    with proxy.running() as url:
        received = post(url, proxy)
    assert received.content == wire(events()) and int(received.headers['content-length']) == len(received.content)


def test_upstream_reaped_before_stall_debit(tmp_path, monkeypatch):
    proxy, ledger, _ = proxy_with(tmp_path,
        [response([wire(events()[:1])], httpx.ReadTimeout('x', request=OFFLINE))], response_buffer=BUFFER)
    real = proxy.upstream.stream
    closed = []
    @contextmanager
    def stream(*a, **kw):
        try:
            with real(*a, **kw) as observed:
                yield observed
        finally:
            closed.append(True)
    monkeypatch.setattr(proxy.upstream, 'stream', stream)
    debit = ledger.debit_unconfirmed
    def guarded(*a, **kw):
        assert closed
        return debit(*a, **kw)
    monkeypatch.setattr(ledger, 'debit_unconfirmed', guarded)
    with proxy.running() as url:
        assert post(url, proxy).status_code == 503


@pytest.mark.parametrize('defect', ['malformed', 'incomplete', 'invalid_usage', 'invalid_model', 'invalid_stop',
                                   'byte_cap', 'disk', 'ipc', 'accounting'])
def test_non_remote_or_completion_failure_stays_terminal(tmp_path, monkeypatch, defect):
    values = events()
    if defect == 'invalid_usage':
        values[0]['message']['usage']['input_tokens'] = -1
    elif defect == 'invalid_model':
        values[0]['message']['model'] = 'wrong'
    elif defect == 'invalid_stop':
        values[-2]['delta']['stop_reason'] = 'wrong'
    raw = b'data: invalid\n\n' if defect == 'malformed' else wire(values[:-1] if defect == 'incomplete' else values)
    error = RuntimeError('local IPC') if defect == 'ipc' else None
    config = {**BUFFER, 'max_bytes': len(raw) - 1} if defect == 'byte_cap' else BUFFER
    proxy, ledger, calls = proxy_with(tmp_path, [response([raw], error), good()], response_buffer=config)
    if defect == 'disk':
        capture = proxy.capture
        def broken(path, *a, **kw):
            if path.name == 'response.sse':
                raise OSError('disk full')
            return capture(path, *a, **kw)
        monkeypatch.setattr(proxy, 'capture', broken)
    if defect == 'accounting':
        # Even a transport-shaped exception from local accounting is not a stall.
        monkeypatch.setattr(proxy.messages, 'finish', lambda *a, **kw: (_ for _ in ()).throw(httpx.ReadTimeout('local')))
    with proxy.running() as url:
        assert post(url, proxy).status_code == 402
        assert post(url, proxy).status_code == 402
    assert proxy.failed.is_set() and len(calls) == 1
    assert not any(r.get('settlement_basis') == STALL_DEBIT_BASIS for r in rows(ledger))


@pytest.mark.parametrize('status', [400, 429])
def test_4xx_body_timeout_is_not_new_stall(tmp_path, status):
    proxy, ledger, _ = proxy_with(tmp_path,
        [response([b'partial'], httpx.ReadTimeout('x', request=OFFLINE), status=status)], response_buffer=BUFFER)
    with proxy.running() as url:
        assert post(url, proxy).status_code == 402
    assert rows(ledger)[0]['status'] == 'pending' and proxy.stalls_survived == 0


def test_header_delivery_failure_is_terminal_after_settlement(tmp_path, monkeypatch):
    proxy, ledger, calls = proxy_with(tmp_path, [good(), good()], response_buffer=BUFFER)
    original = BaseHTTPRequestHandler.send_response
    def fail(handler, code, *args):
        if code == 200:
            raise httpx.ReadTimeout('local header failure')
        return original(handler, code, *args)
    monkeypatch.setattr(BaseHTTPRequestHandler, 'send_response', fail)
    with proxy.running() as url:
        with pytest.raises(httpx.HTTPError):
            post(url, proxy)
        assert post(url, proxy).status_code == 402
    assert len(calls) == 1 and rows(ledger)[0]['status'] == 'settled' and proxy.stalls_survived == 0


@pytest.mark.parametrize('when', ['settlement', 'header'])
def test_changed_retained_spool_never_replaces_replayed_bytes_or_passes_silently(tmp_path, monkeypatch, when):
    proxy, ledger, calls = proxy_with(tmp_path, [good(), good()], response_buffer=BUFFER)
    def corrupt():
        next((tmp_path / 'requests').rglob('response.sse')).write_bytes(b'PRIVATE_REPLACEMENT')
    if when == 'settlement':
        real = proxy.messages.finish
        def finish(*a, **kw):
            result = real(*a, **kw); corrupt(); return result
        monkeypatch.setattr(proxy.messages, 'finish', finish)
    else:
        real = BaseHTTPRequestHandler.send_response
        def header(handler, code, *a):
            if code == 200:
                corrupt()
            return real(handler, code, *a)
        monkeypatch.setattr(BaseHTTPRequestHandler, 'send_response', header)
    with proxy.running() as url:
        reply = post(url, proxy)
        assert 'PRIVATE_REPLACEMENT' not in reply.text
        assert reply.status_code == (402 if when == 'settlement' else 200)
        if when == 'header':
            assert reply.content == wire(events())
        assert post(url, proxy).status_code == 402
    assert proxy.failure == 'native response buffer evidence changed' and len(calls) == 1
    assert rows(ledger)[0]['status'] == 'settled' and proxy.stalls_survived == 0


@pytest.mark.parametrize('at_settlement', [False, True])
def test_admission_close_never_delivers_or_retries_buffered_response(tmp_path, monkeypatch, at_settlement):
    proxy, ledger, _ = proxy_with(tmp_path, [good()], response_buffer=BUFFER)
    if at_settlement:
        real = proxy.messages.finish
        def finish(*a, **kw):
            result = real(*a, **kw); proxy.close_admission(); return result
        monkeypatch.setattr(proxy.messages, 'finish', finish)
    else:
        real = proxy.capture
        def capture(path, *a, **kw):
            result = real(path, *a, **kw)
            if path.name == 'response.sse' and kw.get('append'):
                proxy.close_admission()
                raise httpx.ReadTimeout('read stopped after closure')
            return result
        monkeypatch.setattr(proxy, 'capture', capture)
    with proxy.running() as url:
        assert post(url, proxy).status_code == 402
    assert proxy.stalls_survived == 0
    assert rows(ledger)[0]['status'] == ('settled' if at_settlement else 'pending')


@pytest.mark.parametrize('config', [False, {}, {**BUFFER, 'extra': 1}, {**BUFFER, 'kind': 'wrong'},
                                  {**BUFFER, 'max_bytes': True}, {**BUFFER, 'max_bytes': 0},
                                  {**BUFFER, 'max_bytes': 64*1024*1024+1},
                                  {**BUFFER, 'total_seconds': 0}, {**BUFFER, 'total_seconds': 1.5}])
def test_buffer_configuration_fails_closed(config):
    with pytest.raises(BudgetStop):
        validated_response_buffer(config)


def test_buffer_requires_registered_stall_policy(tmp_path):
    with pytest.raises(BudgetStop, match='requires a registered stall policy'):
        proxy_with(tmp_path, [], policy=None, response_buffer=BUFFER)


def test_buffered_stalls_share_the_registered_debit_limit(tmp_path):
    partial = wire(events()[:1])
    failures = [response([partial], httpx.ReadTimeout('x', request=OFFLINE)) for _ in range(2)]
    proxy, ledger, calls = proxy_with(tmp_path, failures, response_buffer=BUFFER,
        policy={'count_attempts': 3, 'max_stall_debits': 1})
    with proxy.running() as url:
        assert post(url, proxy).status_code == 503
        assert post(url, proxy).status_code == 402
    first, second = rows(ledger)
    assert first['settlement_basis'] == STALL_DEBIT_BASIS and second['status'] == 'pending'
    assert len(calls) == 2 and proxy.stalls_survived == 1


def test_retry_needs_fresh_headroom_before_another_upstream_call(tmp_path):
    partial = response([wire(events()[:1])], httpx.ReadTimeout('x', request=OFFLINE))
    proxy, ledger, calls = proxy_with(tmp_path, [partial, good()], response_buffer=BUFFER, cap='0.04')
    with proxy.running() as url:
        assert post(url, proxy).status_code == 503
        assert post(url, proxy).status_code == 402
    assert len(calls) == 1 and len(rows(ledger)) == 1 and rows(ledger)[0]['status'] == 'settled'
    assert list((tmp_path / 'denied_requests').rglob('admission.json'))
