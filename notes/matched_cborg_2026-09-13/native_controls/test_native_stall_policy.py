"""The registered in-attempt stall policy; synthetic upstreams only (#2150)."""
from decimal import Decimal
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import anthropic
import httpx
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from budgeted_cborg import BudgetStop, CappedMessages, Ledger, STALL_DEBIT_BASIS, retryable_count_error
from native_proxy import NativeProxy, UNCONFIRMED_CHARGE, stall_evidence, validated_stall_policy
from native_controls.test_native_proxy import REQUEST, PRICES, events, wire

POLICY = {'count_attempts': 3, 'max_stall_debits': 2}
OFFLINE = httpx.Request('POST', 'https://offline.invalid/v1/messages')


def good():
    return httpx.Response(200, content=wire(events()), headers={'content-type': 'text/event-stream'})


def proxy_with(tmp_path, script, *, policy=POLICY, count=None, cap=5):
    """`script` yields one upstream outcome per paid request: a Response, or an exception to raise."""
    calls, outcomes = [], iter(script)
    def respond(request):
        calls.append(request)
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    sdk = SimpleNamespace(messages=SimpleNamespace(
        count_tokens=count or (lambda **kw: SimpleNamespace(input_tokens=100))))
    ledger = Ledger(tmp_path / 'ledger.json', manifest_sha256='offline', attempt_cap=cap)
    proxy = NativeProxy(sdk=sdk, ledger=ledger, attempt='native-offline', evidence=tmp_path / 'requests',
        model=REQUEST['model'], prices=PRICES, verify=lambda: None, provider_key='offline-provider-key',
        base_url='https://api.cborg.lbl.gov', upstream=httpx.Client(transport=httpx.MockTransport(respond)),
        **({'stall_policy': policy, 'count_pause': lambda seconds: None} if policy is not None else {}))
    return proxy, ledger, calls


def post(url, proxy):
    return httpx.post(url + '/v1/messages?beta=true', json=REQUEST, headers={'x-api-key': proxy.token})


def rows(ledger):
    return json.loads(ledger.path.read_bytes())['requests']


@pytest.mark.parametrize('stall', [httpx.Response(524, content=b'origin timeout'), httpx.Response(502), httpx.Response(503),
                                   httpx.ReadTimeout('no headers', request=OFFLINE), httpx.ConnectTimeout('x', request=OFFLINE),
                                   httpx.ReadError('reset', request=OFFLINE), httpx.RemoteProtocolError('cut', request=OFFLINE)],
                         ids=['http524', 'http502', 'http503', 'read_timeout', 'connect_timeout', 'read_error', 'protocol'])
def test_a_stall_before_any_relayed_byte_is_debited_and_the_attempt_continues(tmp_path, stall):
    proxy, ledger, calls = proxy_with(tmp_path, [stall, good()])
    with proxy.running() as url:
        first = post(url, proxy)
        second = post(url, proxy)
    # The child is told to retry, and nothing of the provider's reply reaches it.
    assert first.status_code == 503 and first.headers['x-should-retry'] == 'true'
    assert first.json()['error']['type'] == 'api_error' and 'origin timeout' not in first.text
    assert second.status_code == 200 and second.content == wire(events())
    assert not proxy.failed.is_set() and proxy.failure is None and proxy.stalls_survived == 1
    stalled, settled = rows(ledger)
    assert stalled['status'] == 'settled' and stalled['cost_usd'] == stalled['reserved_usd']
    assert stalled['settlement_basis'] == STALL_DEBIT_BASIS and stalled['stall_index'] == 1
    assert stalled['provider_charge_confirmed'] is False and stalled['provider_charge_usd'] is None
    assert stalled['provider_usage_is_final'] is False and stalled['released_excess_reservation_usd'] == '0'
    assert 'usage' not in stalled and 'response_sha256' not in stalled
    assert settled['status'] == 'settled' and 'settlement_basis' not in settled
    assert Decimal(settled['cost_usd']) < Decimal(settled['reserved_usd'])
    (evidence,) = (tmp_path / 'requests').rglob('stall.json')
    recorded = json.loads(evidence.read_text())
    assert recorded['stall_index'] == 1 and recorded['child_reply_status'] == 503
    assert recorded == {**recorded, **stalled['stall_evidence']}
    assert len(calls) == 2 and 'offline-provider-key' not in evidence.read_text()


def test_the_allowance_is_bounded_and_the_next_stall_stops_as_before(tmp_path):
    proxy, ledger, calls = proxy_with(tmp_path, [httpx.Response(524)] * 3)
    with proxy.running() as url:
        replies = [post(url, proxy) for _ in range(3)]
        refused = post(url, proxy)
    assert [r.status_code for r in replies] == [503, 503, 402] and refused.status_code == 402
    assert proxy.failed.is_set() and proxy.failure == UNCONFIRMED_CHARGE and proxy.stalls_survived == 2
    first, second, third = rows(ledger)
    assert [r.get('settlement_basis') for r in (first, second)] == [STALL_DEBIT_BASIS] * 2
    assert third['status'] == 'pending' and 'cost_usd' not in third     # the historical unresolved reservation
    assert len(calls) == 3


@pytest.mark.parametrize('policy', [None, {'count_attempts': 3, 'max_stall_debits': 0}], ids=['absent', 'no_debits'])
def test_without_a_debit_allowance_the_first_stall_stops_exactly_as_before(tmp_path, policy):
    proxy, ledger, calls = proxy_with(tmp_path, [httpx.Response(524), good()], policy=policy)
    with proxy.running() as url:
        first = post(url, proxy)
        second = post(url, proxy)
    assert first.status_code == 402 and second.status_code == 402 and len(calls) == 1
    assert proxy.failure == UNCONFIRMED_CHARGE
    (row,) = rows(ledger)
    assert row['status'] == 'pending' and not list((tmp_path / 'requests').rglob('stall.json'))


@pytest.mark.parametrize('status', [400, 401, 404, 413, 429])
def test_a_provider_client_error_is_never_a_stall(tmp_path, status):
    proxy, ledger, _ = proxy_with(tmp_path, [httpx.Response(status), good()])
    with proxy.running() as url:
        reply = post(url, proxy)
    assert reply.status_code == 402 and proxy.failure == UNCONFIRMED_CHARGE
    assert rows(ledger)[0]['status'] == 'pending' and proxy.stalls_survived == 0


def test_a_failure_after_bytes_were_relayed_stays_terminal(tmp_path):
    class Cut(httpx.SyncByteStream):
        def __iter__(self):
            yield wire(events())[:40]
            raise httpx.ReadTimeout('mid-stream', request=OFFLINE)
    cut = httpx.Response(200, stream=Cut(), headers={'content-type': 'text/event-stream'})
    proxy, ledger, _ = proxy_with(tmp_path, [cut, good()])
    with proxy.running() as url:
        reply = post(url, proxy)
        refused = post(url, proxy)
    # The child already holds part of the reply, so no retryable status can be sent.
    assert reply.status_code == 200 and reply.content == wire(events())[:40] and refused.status_code == 402
    assert proxy.failed.is_set() and proxy.failure == 'ReadTimeout' and proxy.stalls_survived == 0
    assert rows(ledger)[0]['status'] == 'pending'


def test_a_stall_after_admission_closed_is_not_survived(tmp_path):
    proxy, ledger, _ = proxy_with(tmp_path, [])
    def respond(request):
        proxy.close_admission()             # the controller's deadline fires while the request is in flight
        return httpx.Response(524)
    proxy.upstream = httpx.Client(transport=httpx.MockTransport(respond))
    with proxy.running() as url:
        reply = post(url, proxy)
    assert reply.status_code == 402 and proxy.failure == UNCONFIRMED_CHARGE
    assert rows(ledger)[0]['status'] == 'pending'


def test_the_debited_ledger_continues_like_any_settled_checkpoint(tmp_path):
    proxy, ledger, _ = proxy_with(tmp_path, [httpx.Response(524), good()])
    with proxy.running() as url:
        post(url, proxy); post(url, proxy)
    raw = ledger.path.read_bytes()
    import hashlib
    total = sum(Decimal(r['cost_usd']) for r in json.loads(raw)['requests'])
    successor = Ledger(tmp_path / 'next.json', manifest_sha256='successor', attempt_cap=5)
    successor.continue_from(ledger.path, expected_sha256=hashlib.sha256(raw).hexdigest(), expected_cost_usd=str(total))
    assert json.loads(successor.path.read_bytes())['requests'] == json.loads(raw)['requests']
    assert successor.reserve('successor:job', '0.01', 'sha')


def timeout_error():
    return anthropic.APITimeoutError(request=OFFLINE)


def status_error(code):
    response = httpx.Response(code, request=OFFLINE)
    kind = anthropic.InternalServerError if code >= 500 else anthropic.BadRequestError
    return kind('synthetic', response=response, body=None)


@pytest.mark.parametrize('failures, survives', [(0, True), (1, True), (2, True), (3, False)])
def test_token_counting_is_repeated_only_within_the_registered_tries(tmp_path, failures, survives):
    tries = []
    def count(**kw):
        tries.append(kw)
        if len(tries) <= failures:
            raise timeout_error()
        return SimpleNamespace(input_tokens=100)
    proxy, ledger, calls = proxy_with(tmp_path, [good()], count=count)
    with proxy.running() as url:
        reply = post(url, proxy)
    assert reply.status_code == (200 if survives else 402)
    assert len(tries) == min(failures + 1, 3) and proxy.messages.count_retries == min(failures, 2)
    if survives:
        assert rows(ledger)[0]['status'] == 'settled' and not proxy.failed.is_set()
    else:
        # No reservation was ever made: a failed count is free.
        assert proxy.failure == 'APITimeoutError' and rows(ledger) == [] and calls == []
    log = tmp_path / 'requests' / 'count_retries.jsonl'
    recorded = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    assert [r['failed_try'] for r in recorded] == list(range(1, min(failures, 2) + 1))
    assert all(set(r) == {'at', 'failed_try', 'error_type'} for r in recorded)


def test_the_child_s_own_count_requests_share_the_same_retry(tmp_path):
    tries = []
    def count(**kw):
        tries.append(kw)
        if len(tries) == 1:
            raise anthropic.APIConnectionError(request=OFFLINE)
        return SimpleNamespace(input_tokens=77)
    proxy, _, _ = proxy_with(tmp_path, [], count=count)
    with proxy.running() as url:
        reply = httpx.post(url + '/v1/messages/count_tokens', json={k: REQUEST[k] for k in ('model', 'messages')},
                           headers={'x-api-key': proxy.token})
    assert reply.status_code == 200 and reply.json() == {'input_tokens': 77} and len(tries) == 2


@pytest.mark.parametrize('error', [status_error(400), ValueError('bad count'), BudgetStop('refused')])
def test_a_count_failure_that_is_not_transport_is_never_repeated(tmp_path, error):
    tries = []
    def count(**kw):
        tries.append(kw); raise error
    proxy, ledger, _ = proxy_with(tmp_path, [good()], count=count)
    with proxy.running() as url:
        assert post(url, proxy).status_code == 402
    assert len(tries) == 1 and proxy.failed.is_set() and rows(ledger) == []


def test_legacy_clients_count_once(tmp_path):
    tries = []
    def count(**kw):
        tries.append(kw); raise timeout_error()
    client = SimpleNamespace(messages=SimpleNamespace(count_tokens=count))
    messages = CappedMessages(client, ledger=Ledger(tmp_path / 'l.json', manifest_sha256='x'), attempt='a',
                              evidence=tmp_path / 'requests', model='m', prices=PRICES, verify=lambda: None)
    with pytest.raises(anthropic.APITimeoutError):
        messages.count_tokens({'model': 'm'})
    assert len(tries) == 1 and not (tmp_path / 'requests').exists()


def test_retryable_count_errors_are_transport_only():
    assert retryable_count_error(timeout_error()) and retryable_count_error(status_error(500))
    assert retryable_count_error(anthropic.APIConnectionError(request=OFFLINE))
    assert not retryable_count_error(status_error(400)) and not retryable_count_error(ValueError())
    assert not retryable_count_error(BudgetStop('x'))


def test_only_upstream_failures_are_stall_evidence():
    assert stall_evidence(httpx.ReadTimeout('x', request=OFFLINE)) == {'kind': 'upstream_transport', 'error_type': 'ReadTimeout'}
    for other in (BrokenPipeError(), OSError(), BudgetStop(UNCONFIRMED_CHARGE), ValueError(), KeyError()):
        assert stall_evidence(other) is None


@pytest.mark.parametrize('value', [{}, [], 'x', {'count_attempts': 3}, {'count_attempts': 0, 'max_stall_debits': 1},
    {'count_attempts': 6, 'max_stall_debits': 1}, {'count_attempts': 3, 'max_stall_debits': -1},
    {'count_attempts': 3, 'max_stall_debits': 11}, {'count_attempts': True, 'max_stall_debits': 1},
    {'count_attempts': 3, 'max_stall_debits': 1.0}, {'count_attempts': 3, 'max_stall_debits': 1, 'extra': 1}])
def test_a_malformed_policy_is_refused_before_any_transport(tmp_path, value):
    with pytest.raises(BudgetStop):
        validated_stall_policy(value)
    with pytest.raises(BudgetStop):
        proxy_with(tmp_path, [], policy=value)
    assert list(tmp_path.iterdir()) in ([], [tmp_path / 'ledger.json.lock'])


@pytest.mark.parametrize('maximum', [True, -1, 1.5, '2', None])
def test_the_ledger_refuses_a_malformed_allowance(tmp_path, maximum):
    ledger = Ledger(tmp_path / 'l.json', manifest_sha256='x')
    ticket = ledger.reserve('a', '0.5', 'sha')
    with pytest.raises(BudgetStop):
        ledger.debit_unconfirmed(ticket, maximum=maximum, evidence={})
    assert rows(ledger)[0]['status'] == 'pending'


def test_the_ledger_counts_debits_per_attempt_and_never_debits_twice(tmp_path):
    ledger = Ledger(tmp_path / 'l.json', manifest_sha256='x', attempt_cap=5)
    one = ledger.reserve('a', '0.5', 'sha1')
    assert ledger.debit_unconfirmed(one, maximum=1, evidence={'kind': 'k'}) == 1
    with pytest.raises(BudgetStop, match='already settled'):
        ledger.debit_unconfirmed(one, maximum=5, evidence={})
    other = ledger.reserve('b', '0.5', 'sha2')        # another attempt has its own allowance
    assert ledger.debit_unconfirmed(other, maximum=1, evidence={}) == 1
    two = ledger.reserve('a', '0.5', 'sha3')
    with pytest.raises(BudgetStop, match='exhausted'):
        ledger.debit_unconfirmed(two, maximum=1, evidence={})
    assert [r['status'] for r in rows(ledger)] == ['settled', 'settled', 'pending']
