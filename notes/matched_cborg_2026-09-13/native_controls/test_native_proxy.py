import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from budgeted_cborg import BudgetStop, Ledger
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


def fixture_proxy(tmp_path, *, values=None, cap=5):
    calls=[]
    def respond(request):
        calls.append(request)
        assert str(request.url)=="https://api.cborg.lbl.gov/v1/messages?beta=true"
        assert request.headers["x-api-key"]=="offline-provider-key"
        assert json.loads(request.content)==REQUEST
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
