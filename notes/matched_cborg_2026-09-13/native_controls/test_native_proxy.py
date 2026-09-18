import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from budgeted_cborg import BudgetStop, Ledger, cborg_client, provider_context_headers
from native_proxy import Completion, NativeProxy

PRICES={"input":0.000005,"output":0.000025,"cache_read":0.0000005,"cache_write":0.00000625}
REQUEST={"model":"claude-opus-5","max_tokens":1000,"stream":True,
         "messages":[{"role":"user","content":"Synthetic offline fixture."}]}


def events(*, stop_reason="end_turn", output_tokens=12, stop=True):
    value=[{"type":"message_start","message":{"id":"offline","model":"claude-opus-5","role":"assistant","type":"message","content":[],"usage":{"input_tokens":100,"output_tokens":0},"stop_reason":None}},
           {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}},
           {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"offline fixture"}},
           {"type":"content_block_stop","index":0},
           {"type":"message_delta","delta":{"stop_reason":stop_reason},"usage":{"output_tokens":output_tokens}}]
    if stop: value.append({"type":"message_stop"})
    return value


def wire(values):
    return "".join(f"event: {v['type']}\ndata: {json.dumps(v)}\n\n" for v in values).encode()


@pytest.mark.parametrize("width",[1,2,17,100000])
def test_split_frames_keep_final_usage(width):
    raw=wire(events()).replace(b"\n",b"\r\n")
    observer=Completion()
    for i in range(0,len(raw),width): observer.feed(raw[i:i+width])
    response=observer.final().model_dump()
    assert response["usage"]=={"input_tokens":100,"output_tokens":12}
    assert response["stop_reason"]=="end_turn"


@pytest.mark.parametrize("values",[
    events(stop=False),
    [v for v in events() if v["type"]!="message_delta"],
    [{"type":"message_stop"}],
    events()+[{"type":"message_start","message":{}}],
    [{"type":"error","error":{"type":"api_error"}}],
    [{**v,"usage":{}} if v['type']=='message_delta' else v for v in events()],
])
def test_incomplete_or_ambiguous_streams_never_complete(values):
    observer=Completion()
    with pytest.raises(BudgetStop):
        observer.feed(wire(values));observer.final()


def fixture_proxy(tmp_path, *, values=None, cap=5, response_factory=None):
    calls=[]
    def respond(request):
        calls.append(request)
        assert str(request.url)=="https://api.cborg.lbl.gov/v1/messages?beta=true"
        assert request.headers["x-api-key"]=="offline-provider-key"
        assert json.loads(request.content)==REQUEST
        if response_factory is not None:
            return response_factory()
        return httpx.Response(200,content=wire(events() if values is None else values),headers={"content-type":"text/event-stream"})
    sdk=SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **kw:SimpleNamespace(input_tokens=100)))
    ledger=Ledger(tmp_path/'ledger.json',manifest_sha256='offline',attempt_cap=cap)
    proxy=NativeProxy(sdk=sdk,ledger=ledger,attempt='native-offline',evidence=tmp_path/'requests',
          model=REQUEST['model'],prices=PRICES,verify=lambda:None,provider_key='offline-provider-key',
          base_url='https://api.cborg.lbl.gov',upstream=httpx.Client(transport=httpx.MockTransport(respond)))
    return proxy, ledger, calls


def test_native_request_unchanged_and_accounted_before_terminal_event(tmp_path):
    proxy,ledger,calls=fixture_proxy(tmp_path)
    with proxy.running() as url:
        response=httpx.post(url+'/v1/messages?beta=true',json=REQUEST,headers={'x-api-key':proxy.token})
    assert response.status_code==200 and response.content==wire(events())
    assert len(calls)==1 and not proxy.failed.is_set()
    row=json.loads(ledger.path.read_bytes())['requests'][0]
    assert row['status']=='settled' and Decimal(row['cost_usd'])==Decimal('0.0008')
    assert len(list((tmp_path/'requests').rglob('native_request.json')))==1
    assert len(list((tmp_path/'requests').rglob('response.sse')))==1
    assert 'offline-provider-key' not in ''.join(p.read_text() for p in (tmp_path/'requests').rglob('*') if p.is_file())


@pytest.mark.parametrize('outcome', ['complete', 'http524', 'cut_before_body', 'cut_after_start'])
def test_response_diagnostics_precede_body_and_never_settle_incomplete_charge(tmp_path, outcome):
    observations = []
    reported = '9.87654321' if outcome == 'complete' else '0'
    correlation = {'request-id': 'offline-request', 'x-request-id': 'offline-upstream',
                   'x-litellm-call-id': 'offline-litellm', 'cf-ray': 'offline-ray-SJC'}
    class Body(httpx.SyncByteStream):
        def __iter__(self):
            # This executes only when the parent starts reading the upstream
            # body, after headers. Inspect real evidence/ledger at that boundary.
            evidence = json.loads(next((tmp_path/'requests').rglob('http_status.json')).read_bytes())
            row = json.loads((tmp_path/'ledger.json').read_bytes())['requests'][0]
            observations.append((evidence, row['status']))
            if outcome == 'http524':
                yield b'<html>Synthetic timeout</html>'
            elif outcome == 'complete':
                yield wire(events())
            else:
                if outcome == 'cut_after_start':
                    yield wire(events()[:1])
                raise httpx.RemoteProtocolError('synthetic interrupted body')
    proxy, ledger, calls = fixture_proxy(tmp_path, response_factory=lambda: httpx.Response(
        524 if outcome == 'http524' else 200, stream=Body(), headers={
            'content-type': 'text/html; charset=UTF-8' if outcome == 'http524' else 'text/event-stream',
            **correlation, 'x-litellm-response-cost': reported,
            'authorization': 'sensitive-response-auth', 'set-cookie': 'sensitive-response-cookie',
            'x-api-key': 'sensitive-response-key', 'x-source-text': 'sensitive-response-source'}))
    with proxy.running() as url:
        response = httpx.post(url+'/v1/messages?beta=true', json=REQUEST, headers={'x-api-key': proxy.token})
        if outcome != 'complete':
            again = httpx.post(url+'/v1/messages?beta=true', json=REQUEST, headers={'x-api-key': proxy.token})
            assert again.status_code == 402
    assert len(calls) == 1 and len(observations) == 1
    metadata, status_at_body = observations[0]
    assert status_at_body == 'pending'
    assert metadata['status'] == (524 if outcome == 'http524' else 200)
    assert metadata['correlation_headers'] == correlation
    assert metadata['reported_cost'] == {'header': 'x-litellm-response-cost', 'value': reported,
                                         'diagnostic_only': True}
    assert all(name not in response.headers for name in (*correlation, 'x-litellm-response-cost',
                                                         'authorization', 'set-cookie', 'x-api-key', 'x-source-text'))
    assert all(value not in response.text for value in correlation.values())
    evidence_text = ''.join(path.read_text() for path in (tmp_path/'requests').rglob('*') if path.is_file())
    assert 'sensitive-response-' not in evidence_text
    row = json.loads(ledger.path.read_bytes())['requests'][0]
    if outcome == 'complete':
        assert response.content == wire(events()) and not proxy.failed.is_set()
        assert row['status'] == 'settled' and Decimal(row['cost_usd']) == Decimal('0.0008')
    else:
        assert proxy.failed.is_set() and row['status'] == 'pending' and 'cost_usd' not in row
        assert Decimal(row['reserved_usd']) > 0
        with pytest.raises(BudgetStop, match='pending or unknown'):
            ledger.reserve('another-attempt', Decimal('0.01'), 'next')
        if outcome == 'http524':
            assert response.status_code == 402
            assert next((tmp_path/'requests').rglob('upstream_error.body')).read_bytes() == b'<html>Synthetic timeout</html>'


@pytest.mark.parametrize('cost', ['', '-0', '-1', '+1', '.25', '1.', '01', ' 0.2', '0.2 ',
                                 'NaN', 'Infinity', '1,2', '1\n2', '9'*65, '1e'+'9'*61])
def test_invalid_reported_cost_is_omitted_without_changing_completed_accounting(tmp_path, cost):
    proxy, ledger, calls = fixture_proxy(tmp_path, response_factory=lambda: httpx.Response(
        200, content=wire(events()), headers={'content-type': 'text/event-stream',
            'x-litellm-response-cost': cost, 'request-id': 'safe-request'}))
    with proxy.running() as url:
        response = httpx.post(url+'/v1/messages?beta=true', json=REQUEST, headers={'x-api-key': proxy.token})
    assert response.status_code == 200 and not proxy.failed.is_set() and len(calls) == 1
    metadata = json.loads(next((tmp_path/'requests').rglob('http_status.json')).read_bytes())
    assert 'reported_cost' not in metadata and metadata['correlation_headers'] == {'request-id': 'safe-request'}
    row = json.loads(ledger.path.read_bytes())['requests'][0]
    assert row['status'] == 'settled' and Decimal(row['cost_usd']) == Decimal('0.0008')


@pytest.mark.parametrize('cost', ['0', '1e-9', '0.01234567890123456789'])
def test_finite_reported_cost_retains_exact_decimal_text_only(tmp_path, cost):
    proxy, ledger, calls = fixture_proxy(tmp_path, response_factory=lambda: httpx.Response(
        200, content=wire(events()), headers={'content-type': 'text/event-stream', 'x-litellm-response-cost': cost}))
    with proxy.running() as url:
        response = httpx.post(url+'/v1/messages?beta=true', json=REQUEST, headers={'x-api-key': proxy.token})
    assert response.status_code == 200 and not proxy.failed.is_set()
    metadata = json.loads(next((tmp_path/'requests').rglob('http_status.json')).read_bytes())
    assert metadata['reported_cost']['value'] == cost and metadata['reported_cost']['diagnostic_only'] is True
    assert Decimal(json.loads(ledger.path.read_bytes())['requests'][0]['cost_usd']) == Decimal('0.0008')


def test_response_headers_refuse_sensitive_invalid_unbounded_and_duplicate_values(tmp_path):
    headers = [('content-type', 'text/event-stream'), ('request-id', 'x'*161),
               ('x-request-id', 'invalid\nvalue'), ('x-litellm-call-id', 'untrusted source text'),
               ('cf-ray', 'safe-ray-1'), ('x-litellm-response-cost', '0.1'),
               ('x-litellm-response-cost', '0.2'), ('authorization', 'never-record-auth'),
               ('set-cookie', 'never-record-cookie'), ('x-unregistered-id', 'never-record-extra')]
    proxy, ledger, calls = fixture_proxy(tmp_path, response_factory=lambda: httpx.Response(
        200, content=wire(events()), headers=headers))
    with proxy.running() as url:
        response = httpx.post(url+'/v1/messages?beta=true', json=REQUEST, headers={'x-api-key': proxy.token})
    assert response.status_code == 200 and not proxy.failed.is_set()
    metadata = json.loads(next((tmp_path/'requests').rglob('http_status.json')).read_bytes())
    assert metadata == {'status': 200, 'content_type': 'text/event-stream',
                        'correlation_headers': {'cf-ray': 'safe-ray-1'}}
    archived = ''.join(path.read_text() for path in (tmp_path/'requests').rglob('*') if path.is_file())
    assert 'never-record-' not in archived and 'untrusted source text' not in archived


@pytest.mark.parametrize('bypass', [False, True])
def test_registered_context_policy_covers_native_counts_and_raw_forwarding(tmp_path, bypass):
    manifest = {'provider_base_url': 'https://api.cborg.lbl.gov'}
    if bypass:
        manifest['provider_context_policy'] = 'headroom_bypass_v1'
    calls = []
    def respond(request):
        calls.append(request)
        if request.url.path.endswith('/count_tokens'):
            return httpx.Response(200, json={'input_tokens': 100})
        return httpx.Response(200, content=wire(events()), headers={'content-type': 'text/event-stream'})
    sdk = cborg_client(manifest, 'offline-provider-key', max_retries=0,
                       http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    ledger = Ledger(tmp_path/'ledger.json', manifest_sha256='offline')
    proxy = NativeProxy(sdk=sdk, ledger=ledger, attempt='offline', evidence=tmp_path/'requests',
        model=REQUEST['model'], prices=PRICES, verify=lambda: None, provider_key='offline-provider-key',
        base_url=manifest['provider_base_url'], request_headers=provider_context_headers(manifest),
        upstream=httpx.Client(transport=httpx.MockTransport(respond)))
    raw = json.dumps(REQUEST, indent=3).encode()
    with proxy.running() as url:
        # Neither a child-supplied bypass nor its opposite selects the policy.
        headers = {'x-api-key': proxy.token, 'x-headroom-bypass': 'false' if bypass else 'true'}
        count = httpx.post(url+'/v1/messages/count_tokens', json=REQUEST, headers=headers)
        response = httpx.post(url+'/v1/messages?beta=true', content=raw, headers=headers)
    assert count.status_code == response.status_code == 200
    assert count.json() == {'input_tokens': 100} and response.content == wire(events())
    assert [call.url.path for call in calls] == ['/v1/messages/count_tokens', '/v1/messages/count_tokens', '/v1/messages']
    assert all(call.headers.get('x-headroom-bypass') == ('true' if bypass else None) for call in calls)
    assert calls[-1].content == raw
    assert all(json.loads(call.content) == {k: v for k, v in REQUEST.items() if k not in {'max_tokens', 'stream'}}
               for call in calls[:-1])
    protocol = json.loads(next((tmp_path/'requests').rglob('request_protocol.json')).read_bytes())
    assert protocol.get('x-headroom-bypass') == ('true' if bypass else None)
    assert 'x-api-key' not in protocol
    assert json.loads(ledger.path.read_bytes())['requests'][0]['status'] == 'settled'


@pytest.mark.parametrize('sdk_headers, forwarding_headers', [
    ({}, {'x-headroom-bypass': 'true'}),
    ({'x-headroom-bypass': 'true'}, None),
    ({'x-headroom-bypass': 'true'}, {}),
    ({'X-Headroom-Bypass': 'true'}, None),
    ({'X-Headroom-Bypass': 'true'}, {}),
])
def test_native_rejects_different_counting_and_forwarding_policy(tmp_path, sdk_headers, forwarding_headers):
    proxy, ledger, calls = fixture_proxy(tmp_path)
    with pytest.raises(BudgetStop, match='context policies differ'):
        NativeProxy(sdk=SimpleNamespace(default_headers=sdk_headers), ledger=ledger, attempt='offline',
            evidence=tmp_path/'other', model=REQUEST['model'], prices=PRICES, verify=lambda: None,
            provider_key='offline', base_url='https://api.cborg.lbl.gov',
            request_headers=forwarding_headers)
    assert not calls and not ledger.path.exists()
    proxy.upstream.close()


@pytest.mark.parametrize('headers', [[], '', {'x-headroom-bypass': 'false'},
                                     {'x-api-key': 'unregistered'}, {'unknown': 'true'}])
def test_native_rejects_unregistered_provider_headers_before_network(tmp_path, headers):
    ledger = Ledger(tmp_path/'ledger.json', manifest_sha256='offline')
    with pytest.raises(BudgetStop, match='headers'):
        NativeProxy(sdk=SimpleNamespace(default_headers={}), ledger=ledger, attempt='offline',
            evidence=tmp_path/'requests', model=REQUEST['model'], prices=PRICES, verify=lambda: None,
            provider_key='offline', base_url='https://api.cborg.lbl.gov', request_headers=headers)
    assert not ledger.path.exists() and not (tmp_path/'requests').exists()


@pytest.mark.parametrize('bad_events',[events(stop_reason=None),events(stop=False)])
def test_native_unknown_charge_blocks_further_provider_calls(tmp_path,bad_events):
    proxy,ledger,calls=fixture_proxy(tmp_path,values=bad_events)
    with proxy.running() as url:
        response=httpx.post(url+'/v1/messages?beta=true',json=REQUEST,headers={'x-api-key':proxy.token})
        again=httpx.post(url+'/v1/messages?beta=true',json=REQUEST,headers={'x-api-key':proxy.token})
    assert response.status_code==200 and again.status_code==402
    assert proxy.failed.is_set() and len(calls)==1
    assert json.loads(ledger.path.read_bytes())['requests'][0]['status']=='pending'
    with pytest.raises(BudgetStop): ledger.reserve('other-attempt',0.01,'other')


def test_native_unaffordable_request_stops_before_provider(tmp_path):
    proxy,ledger,calls=fixture_proxy(tmp_path,cap=0.01)
    with proxy.running() as url:
        response=httpx.post(url+'/v1/messages?beta=true',json=REQUEST,headers={'x-api-key':proxy.token})
    assert response.status_code==402 and not calls


def test_wrong_loopback_token_never_uses_provider(tmp_path):
    proxy,ledger,calls=fixture_proxy(tmp_path)
    with proxy.running() as url:
        response=httpx.post(url+'/v1/messages?beta=true',json=REQUEST,headers={'x-api-key':'wrong'})
    assert response.status_code==401 and not calls
    assert not ledger.path.exists()


def test_concurrent_native_requests_are_serialized_until_settled(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    import time
    proxy,ledger,calls=fixture_proxy(tmp_path)
    first_started=threading.Event()
    release_first=threading.Event()
    original=proxy.upstream._transport.handler
    def delayed(request):
        if not first_started.is_set():
            first_started.set()
            assert release_first.wait(timeout=5)
        return original(request)
    proxy.upstream._transport.handler=delayed
    with proxy.running() as url,ThreadPoolExecutor(max_workers=2) as pool:
        def post():
            return httpx.post(url+'/v1/messages?beta=true',json=REQUEST,headers={'x-api-key':proxy.token},timeout=5)
        first=pool.submit(post)
        assert first_started.wait(timeout=5)
        second=pool.submit(post)
        # Hold the first upstream response while the second local HTTP
        # request arrives; it must wait instead of colliding with accounting.
        time.sleep(0.1)
        assert not second.done()
        release_first.set()
        assert first.result(timeout=5).status_code==second.result(timeout=5).status_code==200
    assert not proxy.failed.is_set() and len(calls)==2
    rows=json.loads(ledger.path.read_bytes())['requests']
    assert len(rows)==2 and all(row['status']=='settled' for row in rows)


def test_shutdown_blocks_queued_admission_and_freezes_late_evidence(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    import time
    proxy,ledger,calls=fixture_proxy(tmp_path)
    first_started=threading.Event();release_first=threading.Event()
    original=proxy.upstream._transport.handler
    def delayed(request):
        first_started.set()
        assert release_first.wait(timeout=5)
        return original(request)
    proxy.upstream._transport.handler=delayed
    with ThreadPoolExecutor(max_workers=2) as pool:
        with proxy.running(cleanup_timeout=0.05) as url:
            def post():
                return httpx.post(url+'/v1/messages?beta=true',json=REQUEST,headers={'x-api-key':proxy.token},timeout=5)
            first=pool.submit(post)
            assert first_started.wait(timeout=5)
            second=pool.submit(post)
            with proxy.state:
                assert proxy.state.wait_for(lambda: proxy.active_handlers==2,timeout=5)
            # Simulate a deadline while the first response is blocked and the
            # auxiliary handler is already queued behind it.
            before=time.monotonic()
        assert time.monotonic()-before < 1
        assert proxy.closed and proxy.frozen and proxy.unfinished_handlers==2
        frozen={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
        assert len(json.loads(ledger.path.read_bytes())['requests'])==1
        release_first.set()
        assert first.result(timeout=5).status_code==402
        assert second.result(timeout=5).status_code==402
        with proxy.state:
            assert proxy.state.wait_for(lambda: proxy.active_handlers==0,timeout=5)
        assert frozen=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert len(calls)==1
    assert json.loads(ledger.path.read_bytes())['requests'][0]['status']=='pending'


def test_shutdown_while_counting_cannot_later_reserve_or_forward(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    proxy,ledger,calls=fixture_proxy(tmp_path)
    counting=threading.Event();release=threading.Event()
    def count(**kw):
        counting.set();assert release.wait(timeout=5)
        return SimpleNamespace(input_tokens=100)
    proxy.messages.client.messages.count_tokens=count
    with ThreadPoolExecutor(max_workers=1) as pool:
        with proxy.running(cleanup_timeout=0.05) as url:
            future=pool.submit(httpx.post,url+'/v1/messages?beta=true',json=REQUEST,headers={'x-api-key':proxy.token},timeout=5)
            assert counting.wait(timeout=5)
        frozen={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
        release.set()
        assert future.result(timeout=5).status_code==402
        assert not calls
        assert frozen=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert json.loads(ledger.path.read_bytes())['requests']==[]


def test_queued_request_cannot_start_when_active_stream_settles_during_shutdown(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    proxy,ledger,calls=fixture_proxy(tmp_path)
    started=threading.Event();release=threading.Event()
    original=proxy.upstream._transport.handler
    def delayed(request):
        started.set();assert release.wait(timeout=5)
        return original(request)
    proxy.upstream._transport.handler=delayed
    close=proxy.close_admission
    def closing():
        close()
        release.set()  # The first call settles during shutdown's grace period.
    proxy.close_admission=closing
    with ThreadPoolExecutor(max_workers=2) as pool:
        with proxy.running() as url:
            def post():
                return httpx.post(url+'/v1/messages?beta=true',json=REQUEST,headers={'x-api-key':proxy.token},timeout=5)
            first=pool.submit(post);assert started.wait(timeout=5)
            second=pool.submit(post)
            with proxy.state:
                assert proxy.state.wait_for(lambda:proxy.active_handlers==2,timeout=5)
        assert len(calls)==1
        assert first.result(timeout=5).status_code==200
        assert second.result(timeout=5).status_code==402
    rows=json.loads(ledger.path.read_bytes())['requests']
    assert len(rows)==1 and rows[0]['status']=='settled'
