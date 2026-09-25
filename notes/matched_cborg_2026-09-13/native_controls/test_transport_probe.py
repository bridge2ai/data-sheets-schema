"""The one-request transport probe (#2463); synthetic lineages and upstreams only."""
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import anthropic
import httpx
import pytest
from filelock import Timeout

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]

from budgeted_cborg import BudgetStop, Ledger, STALL_DEBIT_BASIS  # noqa: E402
import sequence_claim  # noqa: E402
from audit_controls import registration as r  # noqa: E402
from audit_controls.registration import SequenceLock, _full_reservation_debit  # noqa: E402
from audit_controls.test_registration import accounting  # noqa: E402,F401  (fixture)
import transport_probe as probe  # noqa: E402

PRICES = {'input': 0.000005, 'output': 0.000025, 'cache_read': 0.0000005, 'cache_write': 0.00000625}
MARKER = 'SYNTHETIC-CONVERSATION-TEXT'
THINKING = 'SYNTHETIC-THINKING-SUMMARY'
BETA = 'claude-code-20250219,interleaved-thinking-2025-05-14'
REPOSITORY = Path(probe.__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    return path


def native_request(extra=None):
    value = {'model': 'claude-opus-5', 'messages': [{'role': 'user', 'content': MARKER}],
             'system': [{'type': 'text', 'text': 'Synthetic system prompt.'}], 'tools': [],
             'max_tokens': 1000, 'thinking': {'type': 'adaptive'}, 'output_config': {'effort': 'high'},
             'stream': True, **(extra or {})}
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode()


@pytest.fixture
def lineage(accounting):
    """A generation checkpoint, then one stopped audit whose one pending request
    was debited at its whole reservation, as audit27's was."""
    m, _, _, _, reg = accounting
    first = copy.deepcopy(m)
    first.update(kind=probe.AUDIT_KIND, repository=str(REPOSITORY), repository_commit='a' * 40,
                 model={'model': 'claude-opus-5'}, provider_base_url='https://api.cborg.lbl.gov',
                 provider_context_policy='headroom_bypass_v1', native_upstream_read_timeout_seconds=1200,
                 native_response_buffer={'kind': 'complete_response_v1', 'max_bytes': 16777216, 'total_seconds': 1200})
    first['budget']['prices_per_token'] = PRICES
    first['job']['attempt_dir'] = str(reg.parent / 'attempts' / first['job']['id'])
    first['pinned_files'].update({str(REPOSITORY / rel): sha(REPOSITORY / rel) for rel in probe.TRANSPORT_MODULES})
    save(reg, first)
    source_sha = r.sha(reg)
    raw = native_request()
    identity = (json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False) + '\n').encode()
    with r.sequence_guard(first, source_sha):
        ledger = r.open_audit_ledger(first, reg, source_sha)
        attempt = r.attempt_identity(source_sha, first['job']['id'])
        request_id = ledger.reserve(attempt, Decimal('2.45350000'), hashlib.sha256(identity).hexdigest())
        ledger.stop_attempt(attempt, 'upstream HTTP response did not confirm a completed charge')
    requests = Path(first['job']['attempt_dir']) / 'requests' / request_id
    requests.mkdir(parents=True)
    (requests / 'native_request.json').write_bytes(raw)
    save(requests / 'request_protocol.json', {'content-type': 'application/json', 'x-headroom-bypass': 'true',
         'anthropic-version': '2023-06-01', 'anthropic-beta': BETA})
    source = Path(first['budget']['ledger_path'])
    old = r.read_json(source)
    row = old['requests'][-1]
    result = save(Path(first['job']['attempt_dir']) / 'result.json', {
        'registration_sha256': source_sha, 'job_id': first['job']['id'], 'scope': 'phase3_audit_only',
        'status': 'stopped', 'unresolved_requests': [row['id']],
        'runtime': {'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0}})
    receipt = save(reg.parent / 'debit_receipt.json', {
        'kind': 'user_authorized_full_reservation_debit', 'source_attempt_kind': 'phase3_audit_only',
        'source_registration_sha256': source_sha, 'source_ledger_sha256': r.sha(source),
        'stopped_result_sha256': r.sha(result), 'request_id': row['id'], 'attempt': row['attempt'],
        'request_sha256': row['request_sha256'], 'previous_reservation_usd': row['reserved_usd'],
        'budget_debit_usd': row['reserved_usd'], 'released_excess_reservation_usd': '0',
        'provider_charge_confirmed': False, 'provider_charge_usd': None, 'provider_usage_is_final': False,
        'source_attempt_completed': False, 'scientific_acceptance': False, 'accounting_observation_sha256': 'e' * 64,
        'recorded_at': '2026-09-25T05:58:25+00:00',
        'user_authorization': {'exact_response': 'Count it', 'quoted_request': 'May I count it?'}})
    reconciled = copy.deepcopy(old)
    reconciled['requests'][-1].update(status='settled', cost_usd=row['reserved_usd'], settled_at='2026-09-25T05:58:25+00:00',
        settlement_basis='user_authorized_full_reservation_debit', reconciliation_receipt_sha256=r.sha(receipt),
        accounting_observation_sha256='e' * 64, provider_charge_confirmed=False, provider_charge_usd=None,
        provider_usage_is_final=False, released_excess_reservation_usd='0',
        source_attempt_kind='phase3_audit_only', source_attempt_outcome='stopped')
    reconciled['reconciled_from'] = {'checkpoint_sha256': r.sha(source), 'receipt_sha256': r.sha(receipt),
        'request_id': row['id'], 'previous_status': 'pending', 'budget_debit_usd': row['reserved_usd'],
        'settlement_basis': 'user_authorized_full_reservation_debit', 'provider_charge_confirmed': False,
        'source_attempt_completed': False}
    checkpoint = save(reg.parent / 'reconciled_billing.json', reconciled)
    origin = Path(m['parent']['registration'])
    authorization = save(reg.parent.parent / 'authorization.json', {
        name: {'exact_response': f'{name} yes', 'quoted_request': f'approve the {name}?',
               'recorded_at': '2026-09-25T18:00:31Z'} for name in probe.AUTHORIZATIONS})
    return SimpleNamespace(root=reg.parent.parent, source=reg, request_dir=requests, checkpoint=checkpoint,
                           receipt=receipt, state=Path(m['sequence_state']), origin=origin, raw=raw,
                           authorization=authorization, tip_ledger=source)


def prepare(lin, **overrides):
    arguments = dict(source_registration=lin.source, source_request=lin.request_dir, tip_checkpoint=lin.checkpoint,
                     tip_reconciliation_receipt=lin.receipt, sequence_state=lin.state,
                     origin_registration=lin.origin, authorization=lin.authorization, require_clean=False)
    arguments.update(overrides)
    return probe.prepare(lin.root / 'probe', **arguments)


@pytest.fixture
def prepared(lineage):
    lineage.registration, lineage.identity = prepare(lineage)
    return lineage


def wire(values):
    return ''.join(f"event: {v['type']}\ndata: {json.dumps(v)}\n\n" for v in values).encode()


def summarized_stream(model='claude-opus-5'):
    return [
        {'type': 'message_start', 'message': {'id': 'msg_offline', 'type': 'message', 'role': 'assistant',
         'model': model, 'content': [], 'stop_reason': None,
         'usage': {'input_tokens': 100, 'output_tokens': 0, 'cache_read_input_tokens': 0}}},
        {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'thinking', 'thinking': '', 'signature': ''}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'thinking_delta', 'thinking': THINKING}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'signature_delta', 'signature': 'sig'}},
        {'type': 'content_block_stop', 'index': 0},
        {'type': 'content_block_start', 'index': 1, 'content_block': {'type': 'text', 'text': ''}},
        {'type': 'content_block_delta', 'index': 1, 'delta': {'type': 'text_delta', 'text': MARKER}},
        {'type': 'content_block_stop', 'index': 1},
        {'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}, 'usage': {'output_tokens': 20}},
        {'type': 'message_stop'}]


class Clock:
    """Fake monotonic time the synthetic upstream advances."""
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Upstream:
    def __init__(self, reply, *, clock=None, count=None):
        self.reply, self.clock, self.count = reply, clock, count
        self.requests, self.counts, self.tips = [], [], []

    def clients(self, manifest, key):
        assert key == 'offline-provider-key'
        def count_tokens(**fields):
            self.counts.append(fields)
            if self.count is not None:
                raise self.count
            return SimpleNamespace(input_tokens=100)
        sdk = SimpleNamespace(messages=SimpleNamespace(count_tokens=count_tokens),
                              default_headers={'x-headroom-bypass': 'true'})
        def respond(request):
            self.requests.append(request)
            self.tips.append(json.loads(self.state.read_text())['registration_sha256'])
            return self.reply(request, self.clock)
        return sdk, httpx.Client(transport=httpx.MockTransport(respond))


def run(lin, upstream, **kwargs):
    upstream.state = lin.state
    return probe.run(lin.registration, lin.identity, clients=upstream.clients, key='offline-provider-key',
                     require_clean=False, **kwargs)


def streamed(values, clock=None, *, headers=None, status=200, per_chunk=1.0, wait=300.0):
    class Body(httpx.SyncByteStream):
        def __iter__(self):
            for value in values:
                if clock is not None:
                    clock.now += per_chunk
                yield wire([value])
    if clock is not None:
        clock.now += wait
    return httpx.Response(status, stream=Body(), headers={'content-type': 'text/event-stream', **(headers or {})})


# --- the request -------------------------------------------------------------------------------

def test_the_probe_request_differs_from_the_retained_one_only_in_its_thinking_display(monkeypatch):
    raw = native_request()
    derived = probe.derive_request(raw)
    assert json.loads(derived) == {**json.loads(raw), 'thinking': {'type': 'adaptive', 'display': 'summarized'}}
    assert derived.replace(probe.PROBE_THINKING, probe.ORIGINAL_THINKING) == raw
    for refused in (native_request({'tool_input': {'thinking': {'type': 'adaptive'}}}),
                    native_request({'thinking': {'type': 'enabled', 'budget_tokens': 1024}}),
                    native_request({'stream': False}), derived):
        with pytest.raises(BudgetStop):
            probe.derive_request(refused)
    monkeypatch.setattr(probe, 'PROBE_THINKING', probe.PROBE_THINKING + b',"extra":1')
    with pytest.raises(BudgetStop, match='more than the thinking setting'):
        probe.derive_request(raw)


# --- a completed probe -------------------------------------------------------------------------

def test_a_completed_probe_claims_the_tip_before_it_sends_and_times_the_stream(prepared):
    lin, clock = prepared, Clock()
    previous = lin.state.read_bytes()
    manifest = json.loads(lin.registration.read_text())
    assert manifest['sequence_claim'] == {'protocol': sequence_claim.PROTOCOL}
    upstream = Upstream(lambda request, clock: streamed(summarized_stream(), clock,
                        headers={'x-litellm-call-id': 'call-1', 'x-litellm-model-api-base': 'https://elsewhere'}),
                        clock=clock)
    result = run(lin, upstream, clock=clock)
    assert result['finding'] == 'completed' and result['client']['status'] == 200 and result['tip_claimed']
    assert result['thinking_display'] == 'summarized_text' and result['proxy_failure'] is None
    # The tip named the probe before the one paid request left (#2472).
    assert upstream.tips == [lin.identity]
    [sent] = upstream.requests
    assert sent.content == probe.derive_request(lin.raw) and sent.url.raw_path == b'/v1/messages?beta=true'
    assert sent.headers['anthropic-beta'] == BETA and sent.headers['x-headroom-bypass'] == 'true'
    assert sent.headers['x-api-key'] == 'offline-provider-key'
    # One free count before the tip moved, one the proxy made; both of the exact request.
    assert len(upstream.counts) == 2 and all(c['thinking'] == probe.VARIATION['to'] for c in upstream.counts)
    [exchange] = result['provider_exchanges']
    assert exchange['headers_seconds'] == 300.0 and exchange['first_chunk_seconds'] == 301.0
    assert exchange['headers_to_first_chunk_seconds'] == 1.0 and exchange['last_chunk_seconds'] == 310.0
    assert exchange['first_thinking_text_seconds'] == 303.0 and exchange['largest_gap_between_chunks_seconds'] == 1.0
    assert exchange['events']['content_block_delta:thinking_delta'] == {'count': 1, 'first_seconds': 303.0,
                                                                       'last_seconds': 303.0}
    assert exchange['diagnostics'] == {'x-litellm-call-id': 'call-1'}
    assert exchange['thinking_text_chars'] == len(THINKING) and exchange['output_tokens'] == 20
    # The ledger carries the tip's rows once and settles the probe's by its usage.
    state = json.loads((lin.root / 'probe' / 'billing.json').read_text())
    assert state['continued_from']['checkpoint_sha256'] == sha(lin.checkpoint)
    carried = json.loads(lin.checkpoint.read_text())['requests']
    assert state['requests'][:len(carried)] == carried
    [row] = result['probe_rows']
    assert row['status'] == 'settled' and Decimal(row['cost_usd']) == (
        Decimal(100) * Decimal('0.000005') + Decimal(20) * Decimal('0.000025'))
    assert result['settlement'] == {'status': 'settled'}
    assert result['successor_continues_from'] == str(lin.root / 'probe' / 'billing.json')
    assert Decimal(result['successor_cost_usd']) == sum(Decimal(x['cost_usd']) for x in state['requests'])
    # The probe owns the tip, with the durable claim naming its predecessor.
    tip = json.loads(lin.state.read_text())
    assert tip['registration_sha256'] == lin.identity and tip['ledger_path'] == str(lin.root / 'probe' / 'billing.json')
    claim = sequence_claim.context(manifest, lin.registration, lin.identity, lin.state,
                                   {'registration_sha256': sha(lin.origin),
                                    'ledger_path': manifest['lineage']['origin_ledger']}, probe.STAGE)
    sequence_claim.verify(claim, tip, previous)
    # result.json keeps no conversation or thinking text; the evidence folder does.
    kept = (lin.root / 'probe' / 'result.json').read_text()
    assert MARKER not in kept and THINKING not in kept
    successor = Ledger(lin.root / 'successor.json', manifest_sha256='next', total_cap='400', attempt_cap='5')
    successor.continue_from(result['successor_continues_from'], expected_sha256=sha(result['successor_continues_from']),
                            expected_cost_usd=result['successor_cost_usd'])
    with pytest.raises(BudgetStop, match='runs once'):
        run(lin, upstream)
    assert len(upstream.requests) == 1


def test_a_5xx_is_counted_at_its_whole_reservation_and_not_resent(prepared):
    upstream = Upstream(lambda request, clock: httpx.Response(500, json={'error': 'synthetic'},
                                                             headers={'x-litellm-attempted-retries': '0'}))
    result = run(prepared, upstream)
    assert result['finding'] == 'upstream_http_500' and result['client']['status'] == 503
    assert len(upstream.requests) == 1 and result['stalls_survived'] == 1
    [row] = result['probe_rows']
    assert (row['status'], row['settlement_basis'], row['provider_charge_confirmed']) == (
        'settled', STALL_DEBIT_BASIS, False)
    assert row['cost_usd'] == row['reserved_usd'] and result['settlement'] == {'status': 'settled'}
    assert result['provider_exchanges'][0]['diagnostics'] == {'x-litellm-attempted-retries': '0'}


def test_a_pending_row_is_debited_in_a_new_checkpoint_with_a_receipt_the_audit_accepts(prepared):
    upstream = Upstream(lambda request, clock: httpx.Response(400, json={'error': 'synthetic refusal'}))
    result = run(prepared, upstream)
    assert result['finding'] == 'upstream_http_400' and result['client']['status'] == 402
    ledger = prepared.root / 'probe' / 'billing.json'
    pending = json.loads(ledger.read_text())['requests'][-1]
    assert pending['status'] == 'pending'
    settlement = result['settlement']
    assert settlement['status'] == 'reconciled' and result['successor_continues_from'] == settlement['path']
    receipt = json.loads(Path(settlement['receipt']).read_text())
    assert _full_reservation_debit(receipt, pending) == Decimal(pending['reserved_usd'])
    assert receipt['user_authorization']['standing'] is True
    state = json.loads(Path(settlement['path']).read_text())
    row = state['requests'][-1]
    assert (row['status'], row['cost_usd'], row['reconciliation_receipt_sha256']) == (
        'settled', pending['reserved_usd'], sha(settlement['receipt']))
    assert state['reconciled_from']['checkpoint_sha256'] == sha(ledger)
    successor = Ledger(prepared.root / 'successor.json', manifest_sha256='next', total_cap='400', attempt_cap='5')
    successor.continue_from(settlement['path'], expected_sha256=settlement['sha256'],
                            expected_cost_usd=result['successor_cost_usd'])


def test_an_outcome_a_person_must_resolve_still_writes_the_timing_record(prepared):
    upstream = Upstream(lambda request, clock: httpx.Response(200, content=wire(summarized_stream('another-model')),
                                                             headers={'content-type': 'text/event-stream'}))
    result = run(prepared, upstream)
    assert result['settlement']['status'] == 'needs_person' and result['successor_continues_from'] is None
    assert result['provider_exchanges'][0]['status'] == 200
    assert (prepared.root / 'probe' / 'result.json').exists()


def test_an_interrupt_writes_the_record_settles_and_is_raised(prepared, monkeypatch):
    upstream = Upstream(lambda request, clock: httpx.Response(400, json={}))
    def interrupted(self, *args, **kwargs):
        raise KeyboardInterrupt
    monkeypatch.setattr(httpx.Client, 'post', interrupted)
    with pytest.raises(KeyboardInterrupt):
        run(prepared, upstream)
    result = json.loads((prepared.root / 'probe' / 'result.json').read_text())
    assert result['interrupted'] == 'KeyboardInterrupt' and result['finding'] == 'interrupted'
    assert result['settlement'] == {'status': 'settled'} and result['tip_claimed'] is True


# --- nothing is claimed or spent -------------------------------------------------------------

def test_a_count_refusal_is_a_finding_with_the_tip_untouched(prepared):
    before = prepared.state.read_bytes()
    refusal = anthropic.BadRequestError('count refused', body=None,
        response=httpx.Response(400, request=httpx.Request('POST', 'https://offline.invalid')))
    upstream = Upstream(lambda request, clock: pytest.fail('provider reached'), count=refusal)
    result = run(prepared, upstream)
    assert (result['finding'], result['tip_claimed'], result['count_error']) == ('count_refused', False, 'BadRequestError')
    assert prepared.state.read_bytes() == before and not (prepared.root / 'probe' / 'billing.json').exists()
    assert not (prepared.root / 'probe' / 'sequence_claim').exists()


@pytest.mark.parametrize('failure', ['transient_count', 'clients'])
def test_a_failure_before_the_claim_leaves_the_probe_runnable(prepared, failure):
    before = prepared.state.read_bytes()
    transient = anthropic.APIConnectionError(request=httpx.Request('POST', 'https://offline.invalid'))
    upstream = Upstream(lambda request, clock: pytest.fail('provider reached'),
                        count=transient if failure == 'transient_count' else None)
    if failure == 'clients':
        upstream.clients = lambda manifest, key: (_ for _ in ()).throw(RuntimeError('no clients'))
    with pytest.raises((anthropic.APIConnectionError, RuntimeError)):
        run(prepared, upstream)
    assert prepared.state.read_bytes() == before
    assert not any((prepared.root / 'probe' / name).exists()
                   for name in ('billing.json', 'result.json', 'attempt', 'sequence_claim'))
    working = Upstream(lambda request, clock: httpx.Response(200, content=wire(summarized_stream()),
                                                            headers={'content-type': 'text/event-stream'}))
    assert run(prepared, working)['finding'] == 'completed'


def test_nothing_is_sent_when_the_tip_moved_the_lock_is_held_or_the_binding_changed(lineage, monkeypatch):
    upstream = Upstream(lambda request, clock: pytest.fail('provider reached'))
    lineage.registration, lineage.identity = prepare(lineage)
    probe_dir = lineage.root / 'probe'
    original = lineage.state.read_text()
    lineage.state.write_text(original.replace('"schema_version"', '"schema_version" '))
    with pytest.raises(BudgetStop, match='tip moved'):
        run(lineage, upstream)
    lineage.state.write_text(original)
    with SequenceLock(str(lineage.state) + '.lock').acquire(timeout=0):
        with pytest.raises(Timeout):
            run(lineage, upstream)
    with monkeypatch.context() as patch:
        patch.setattr(probe, 'interpreter', lambda: {'executable': 'elsewhere'})
        with pytest.raises(BudgetStop, match='interpreter'):
            run(lineage, upstream)
    with pytest.raises(BudgetStop, match='clean-tree rule'):
        probe.run(lineage.registration, lineage.identity, clients=upstream.clients, key='k', require_clean=True)
    lineage.authorization.write_text(lineage.authorization.read_text().replace('yes', 'no'))
    with pytest.raises(BudgetStop, match='pin changed'):
        run(lineage, upstream)
    assert not upstream.requests and not (probe_dir / 'billing.json').exists()


# --- preparation --------------------------------------------------------------------------------

def test_preparation_refuses_what_the_lineage_does_not_support(lineage, monkeypatch):
    def refused(match, **overrides):
        with pytest.raises(BudgetStop, match=match):
            prepare(lineage, **overrides)
        assert not (lineage.root / 'probe').exists()
    refused('reconciliation receipt', tip_reconciliation_receipt=None)
    # A checkpoint whose cap is inflated no longer reproduces from the stopped ledger (#2471).
    value = json.loads(lineage.checkpoint.read_text())
    inflated = lineage.root / 'inflated.json'
    save(inflated, {**value, 'additional_cap_usd': '1000'})
    refused('reconciled audit checkpoint', tip_checkpoint=inflated)
    # A request the lineage never admitted.
    other = lineage.root / 'other_request'
    other.mkdir()
    (other / 'native_request.json').write_bytes(native_request({'max_tokens': 999}))
    (other / 'request_protocol.json').write_text((lineage.request_dir / 'request_protocol.json').read_text())
    refused('not one the lineage admitted', source_request=other)
    with monkeypatch.context() as patch:
        # A probe cap above the lineage's per-attempt cap; the shared cap is
        # also enforced by the ledger at reservation.
        patch.setattr(probe, 'PROBE_CAP_USD', '396')
        refused('attempt cap')
    with monkeypatch.context() as patch:
        patch.setattr(probe, 'TRANSPORT_MODULES', (*probe.TRANSPORT_MODULES, 'notes/matched_cborg_2026-09-13/sequence_claim.py'))
        refused('pinned transport')


# --- measurement --------------------------------------------------------------------------------

def test_event_times_count_split_frames_and_never_raise_or_keep_text():
    ticks = iter(range(1000))
    record = {'headers': 0}
    times = probe.EventTimes(record, lambda: next(ticks))
    raw = wire(summarized_stream()).replace(b'\n', b'\r\n')
    for offset in range(0, len(raw), 37):
        times.chunk(raw[offset:offset + 37])
    assert record['events']['message_stop']['count'] == 1 and record['unparsed_frames'] == 0
    assert record['stop_reason'] == 'end_turn' and record['thinking_text_chars'] == len(THINKING)
    assert THINKING not in json.dumps(record) and MARKER not in json.dumps(record)
    for malformed in (b'data: {"type": "content_block_delta", "delta": "x"}\n\n',
                      b'data: {"type": "message_delta", "usage": [1], "delta": null}\n\n',
                      b'data: {"type": 7}\n\ndata: [1]\n\n'):
        times.chunk(malformed)
    assert record['timing_errors'] == 0 and record['unparsed_frames'] == 2


@pytest.mark.parametrize('exchange, client, expected', [
    ({'status': None, 'error': 'ConnectError'}, {}, 'not_sent'),
    ({'status': None, 'error': 'ReadTimeout'}, {}, 'no_response_headers'),
    ({'status': 500, 'error': 'UpstreamStall'}, {'status': 503}, 'upstream_http_500'),
    ({'status': 200, 'events': {'error': {}}, 'chunks': 2, 'error': 'BudgetStop'}, {'status': 402}, 'stream_error_event'),
    ({'status': 200, 'events': {'message_stop': {}}, 'chunks': 9, 'error': None}, {'status': 200}, 'completed'),
    ({'status': 200, 'events': {'message_stop': {}}, 'chunks': 9, 'error': None}, {'status': None}, 'completed_not_delivered'),
    ({'status': 200, 'events': {}, 'chunks': 0, 'error': 'BudgetStop'}, {'status': 402}, 'no_stream'),
    ({'status': 200, 'events': {'message_start': {}}, 'chunks': 3, 'error': 'ReadTimeout'}, {'status': 503}, 'stream_cut'),
    ({'status': 200, 'events': {'message_start': {}}, 'chunks': 3, 'error': None}, {'status': 402}, 'stream_ended_without_stop'),
])
def test_each_outcome_has_its_own_finding(exchange, client, expected):
    assert probe.finding([exchange], client) == expected
    assert probe.finding([], {}) == 'not_sent'


def test_only_named_diagnostic_headers_with_plain_values_are_kept():
    headers = httpx.Headers({'x-litellm-call-id': 'd768a75f-b5bf', 'x-litellm-response-duration-ms': '272585.1',
                             'x-litellm-attempted-retries': '0', 'x-litellm-version': 'a b', 'x-litellm-key-spend': '9',
                             'retry-after': '1' * 97})
    assert probe.diagnostics(headers) == {'x-litellm-call-id': 'd768a75f-b5bf',
                                          'x-litellm-response-duration-ms': '272585.1',
                                          'x-litellm-attempted-retries': '0'}


# --- round two (#2470 review) ------------------------------------------------------------------

def ok_stream(request, clock):
    return httpx.Response(200, content=wire(summarized_stream()), headers={'content-type': 'text/event-stream'})


def test_preparation_refuses_a_tip_that_is_no_longer_the_predecessor(lineage):
    """Without this check the probe would displace a newer tip and drop its charges."""
    other = save(lineage.root / 'audit28' / 'registration.json', {'kind': probe.AUDIT_KIND, 'n': 28})
    ledger = save(lineage.root / 'audit28' / 'billing.json', {'requests': []})
    lineage.state.write_text(json.dumps({'schema_version': 1, 'registration_sha256': sha(other),
        'ledger_path': str(ledger), 'parent_checkpoint_sha256': sha(lineage.checkpoint),
        'source_registration_sha256': sha(lineage.origin)}, indent=2) + '\n')
    with pytest.raises(BudgetStop, match='not the probe'):
        prepare(lineage)
    assert not (lineage.root / 'probe').exists()


@pytest.mark.parametrize('kind, status', [(anthropic.AuthenticationError, 401),
                                          (anthropic.PermissionDeniedError, 403), (anthropic.NotFoundError, 404)])
def test_a_key_or_route_error_on_the_count_is_not_a_finding_and_leaves_the_probe_runnable(prepared, kind, status):
    error = kind('count failed', body=None,
                 response=httpx.Response(status, request=httpx.Request('POST', 'https://offline.invalid')))
    with pytest.raises(kind):
        run(prepared, Upstream(lambda request, clock: pytest.fail('provider reached'), count=error))
    assert not any((prepared.root / 'probe' / name).exists() for name in ('result.json', 'billing.json'))
    assert run(prepared, Upstream(ok_stream))['finding'] == 'completed'


def test_a_ledger_failure_leaves_the_tip_unchanged_and_the_probe_runnable(prepared, monkeypatch):
    before = prepared.state.read_bytes()
    real = Ledger.continue_from
    calls = []
    def flaky(self, *args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise OSError('disk full')
        return real(self, *args, **kwargs)
    monkeypatch.setattr(Ledger, 'continue_from', flaky)
    with pytest.raises(OSError):
        run(prepared, Upstream(lambda request, clock: pytest.fail('provider reached')))
    assert prepared.state.read_bytes() == before
    assert not any((prepared.root / 'probe' / name).exists() for name in ('result.json', 'billing.json'))
    assert run(prepared, Upstream(ok_stream))['finding'] == 'completed'


def test_a_claim_that_cannot_be_preserved_is_recorded_and_closes_the_clients(prepared, monkeypatch):
    upstream = Upstream(lambda request, clock: pytest.fail('provider reached'))
    made, original = {}, upstream.clients
    def clients(manifest, key):
        sdk, client = original(manifest, key)
        made['client'] = client
        return sdk, client
    upstream.clients = clients
    monkeypatch.setattr(sequence_claim, '_fsync', lambda descriptor: (_ for _ in ()).throw(OSError('fsync')))
    with pytest.raises(BudgetStop, match='owner remains consumed'):
        run(prepared, upstream)
    result = json.loads((prepared.root / 'probe' / 'result.json').read_text())
    assert result['finding'] == 'claim_failed' and result['tip_claimed'] is True
    assert result['successor_continues_from'] is None and made['client'].is_closed


def test_a_snapshot_failure_still_settles_and_writes_the_record(prepared, monkeypatch):
    monkeypatch.setattr(probe, 'relative', lambda record: (_ for _ in ()).throw(RuntimeError('changed size')))
    result = run(prepared, Upstream(lambda request, clock: httpx.Response(400, json={})))
    assert result['provider_exchanges'] is None and result['settlement']['status'] == 'reconciled'


def test_no_standing_debit_while_a_handler_may_still_hold_the_request(prepared, monkeypatch):
    from contextlib import contextmanager
    from native_proxy import NativeProxy
    real = NativeProxy.running
    @contextmanager
    def running(self, **kwargs):
        with real(self, **kwargs) as url:
            yield url
        self.unfinished_handlers = 1
    monkeypatch.setattr(NativeProxy, 'running', running)
    result = run(prepared, Upstream(lambda request, clock: httpx.Response(400, json={})))
    assert result['exchanges_complete'] is False and result['runtime']['unfinished_handlers'] == 1
    assert result['settlement']['status'] == 'needs_person' and result['successor_continues_from'] is None
    assert not (prepared.root / 'probe' / 'reconciled_billing.json').exists()


def test_the_debit_receipt_records_the_closed_runtime(prepared):
    result = run(prepared, Upstream(lambda request, clock: httpx.Response(400, json={})))
    receipt = json.loads(Path(result['settlement']['receipt']).read_text())
    assert receipt['runtime_at_settlement'] == {'proxy_initialized': True, 'proxy_shutdown_complete': True,
                                                'unfinished_handlers': 0}
    assert 'runtime_closure' not in receipt       # that key names reviewed reboot evidence in the audit


def test_a_registration_with_another_attempt_cap_is_refused(prepared):
    manifest = json.loads(prepared.registration.read_text())
    manifest['budget']['per_job_attempt_usd'] = {probe.ATTEMPT: '6'}
    with pytest.raises(BudgetStop, match='attempt cap'):
        probe.check_lineage(manifest)


def test_the_source_interpreter_is_recorded(prepared):
    manifest = json.loads(prepared.registration.read_text())
    assert set(manifest['source_python']) == {'path', 'resolved', 'sha256', 'same_binary'}


# --- a tip whose own ledger is settled, with no reconciliation -----------------------------------

def test_a_settled_tip_prepares_and_runs_without_a_reconciliation(accounting):
    m, _, _, _, reg = accounting
    first = copy.deepcopy(m)
    first.update(kind=probe.AUDIT_KIND, repository=str(REPOSITORY), repository_commit='a' * 40,
                 model={'model': 'claude-opus-5'}, provider_base_url='https://api.cborg.lbl.gov',
                 provider_context_policy='headroom_bypass_v1')
    first['budget']['prices_per_token'] = PRICES
    first['job']['attempt_dir'] = str(reg.parent / 'attempts' / first['job']['id'])
    first['pinned_files'].update({str(REPOSITORY / rel): sha(REPOSITORY / rel) for rel in probe.TRANSPORT_MODULES})
    save(reg, first)
    source_sha = r.sha(reg)
    raw = native_request()
    identity = (json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False) + '\n').encode()
    with r.sequence_guard(first, source_sha):
        ledger = r.open_audit_ledger(first, reg, source_sha)
        ticket = ledger.reserve(r.attempt_identity(source_sha, first['job']['id']), Decimal('2.4535'),
                                hashlib.sha256(identity).hexdigest())
        ledger.settle(ticket, Decimal('1.0'), response_sha256='f' * 64, usage={'input_tokens': 1, 'output_tokens': 1})
    requests = Path(first['job']['attempt_dir']) / 'requests' / ticket
    requests.mkdir(parents=True)
    (requests / 'native_request.json').write_bytes(raw)
    save(requests / 'request_protocol.json', {'anthropic-version': '2023-06-01', 'anthropic-beta': BETA})
    authorization = save(reg.parent.parent / 'authorization.json', {
        name: {'exact_response': 'y', 'quoted_request': 'q?', 'recorded_at': '2026-09-25T18:00:31Z'}
        for name in probe.AUTHORIZATIONS})
    tip = SimpleNamespace(root=reg.parent.parent, state=Path(m['sequence_state']))
    tip.registration, tip.identity = probe.prepare(
        tip.root / 'probe', source_registration=reg, source_request=requests,
        tip_checkpoint=Path(first['budget']['ledger_path']), sequence_state=tip.state,
        origin_registration=Path(m['parent']['registration']), authorization=authorization, require_clean=False)
    assert 'reconciliation' not in json.loads(tip.registration.read_text())['budget']['continuation']
    assert run(tip, Upstream(ok_stream))['finding'] == 'completed'


# --- the real bounded stream worker under the timing wrapper, against a local fake ---------------

def test_the_timing_wrapper_over_the_real_bounded_worker(prepared):
    from contextlib import contextmanager
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading
    import time
    from audit_controls.bounded_stream import BoundedStreamClient
    seen = []
    class Fake(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.0'
        def log_message(self, *args):
            pass
        def do_POST(self):
            self.rfile.read(int(self.headers['content-length']))
            seen.append(self.path)
            time.sleep(0.3)
            self.send_response(200)
            self.send_header('content-type', 'text/event-stream')
            self.send_header('x-litellm-attempted-retries', '2')
            self.end_headers()
            for value in summarized_stream():
                self.wfile.write(wire([value]))
                self.wfile.flush()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Fake)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    local = f'http://127.0.0.1:{server.server_port}'
    class Redirect:
        def __init__(self, inner):
            self.inner = inner
        def __getattr__(self, name):
            return getattr(self.inner, name)
        @contextmanager
        def stream(self, method, url, **kwargs):
            with self.inner.stream(method, local + url[len('https://api.cborg.lbl.gov'):], **kwargs) as response:
                yield response
    def clients(manifest, key):
        sdk = SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **fields: SimpleNamespace(input_tokens=100)),
                              default_headers={'x-headroom-bypass': 'true'})
        return sdk, Redirect(BoundedStreamClient(None, read_timeout_seconds=1200, connect_timeout_seconds=20,
                                                 total_timeout_seconds=1200))
    try:
        result = probe.run(prepared.registration, prepared.identity, clients=clients, key='offline-provider-key',
                           require_clean=False)
    finally:
        server.shutdown()
    [exchange] = result['provider_exchanges']
    assert seen == ['/v1/messages?beta=true'] and result['finding'] == 'completed'
    assert exchange['headers_seconds'] >= 0.3 and exchange['diagnostics'] == {'x-litellm-attempted-retries': '2'}
    assert exchange['thinking_text_chars'] == len(THINKING)
