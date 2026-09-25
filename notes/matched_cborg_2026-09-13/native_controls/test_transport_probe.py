"""The one-request transport probe (#2463); synthetic lineage and upstreams only."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx
import pytest
from filelock import Timeout

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]

from budgeted_cborg import BudgetStop, Ledger, STALL_DEBIT_BASIS  # noqa: E402
import sequence_claim  # noqa: E402
from audit_controls.registration import SequenceLock  # noqa: E402
import transport_probe as probe  # noqa: E402

PRICES = {'input': 0.000005, 'output': 0.000025, 'cache_read': 0.0000005, 'cache_write': 0.00000625}
MARKER = 'SYNTHETIC-CONVERSATION-TEXT'
THINKING = 'SYNTHETIC-THINKING-SUMMARY'
BETA = 'claude-code-20250219,interleaved-thinking-2025-05-14'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    return path


def native_request(extra=None):
    value = {'model': 'claude-opus-5', 'messages': [{'role': 'user', 'content': MARKER}],
             'system': [{'type': 'text', 'text': 'Synthetic system prompt.'}], 'tools': [],
             'max_tokens': 1000, 'thinking': {'type': 'adaptive'}, 'output_config': {'effort': 'high'},
             'stream': True, **(extra or {})}
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode()


def lineage(tmp_path, *, tip_cost='10.00000000', raw=None):
    """An origin, a stopped tip with one pending row, and its full-reservation checkpoint."""
    root = tmp_path.resolve()
    origin = dump(root / 'origin' / 'registration.json', {'budget': {'ledger_path': str(root / 'origin' / 'billing.json')}})
    dump(root / 'origin' / 'billing.json', {'requests': []})
    raw = raw or native_request()
    request_dir = root / 'tip' / 'attempts' / 'job' / 'requests' / 'failed'
    request_dir.mkdir(parents=True)
    (request_dir / 'native_request.json').write_bytes(raw)
    dump(request_dir / 'request_protocol.json', {'content-type': 'application/json', 'accept': 'text/event-stream',
         'x-headroom-bypass': 'true', 'anthropic-version': '2023-06-01', 'anthropic-beta': BETA})
    source = dump(root / 'tip' / 'registration.json', {
        'kind': 'd4d_native_audit_continuation', 'model': {'model': 'claude-opus-5'},
        'provider_base_url': 'https://api.cborg.lbl.gov', 'provider_context_policy': 'headroom_bypass_v1',
        'budget': {'prices_per_token': PRICES}, 'native_upstream_read_timeout_seconds': 1200,
        'native_response_buffer': {'kind': 'complete_response_v1', 'max_bytes': 16777216, 'total_seconds': 1200}})
    identity = (json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False) + '\n').encode()
    settled = {'id': 'a' * 32, 'attempt': 'tip:job', 'status': 'settled', 'cost_usd': tip_cost,
               'reserved_usd': tip_cost, 'request_sha256': 'b' * 64}
    pending = {'id': 'c' * 32, 'attempt': 'tip:job', 'status': 'pending', 'reserved_usd': '2.45350000',
               'request_sha256': hashlib.sha256(identity).hexdigest()}
    tip_ledger = dump(root / 'tip' / 'billing.json', {'manifest_sha256': sha(source), 'additional_cap_usd': '600',
                      'attempt_cap_usd': '5', 'requests': [settled, pending]})
    reconciled = {**pending, 'status': 'settled', 'cost_usd': pending['reserved_usd'],
                  'provider_charge_confirmed': False, 'settlement_basis': 'user_authorized_full_reservation_debit'}
    checkpoint = dump(root / 'tip' / 'reconciled_billing.json', {
        'manifest_sha256': sha(source), 'additional_cap_usd': '600', 'attempt_cap_usd': '5',
        'requests': [settled, reconciled],
        'reconciled_from': {'checkpoint_sha256': sha(tip_ledger), 'request_id': pending['id']}})
    state = dump(root / 'origin' / 'audit_sequence.json', {
        'schema_version': 1, 'registration_sha256': sha(source), 'ledger_path': str(tip_ledger),
        'parent_checkpoint_sha256': 'd' * 64, 'source_registration_sha256': sha(origin)})
    authorization = dump(root / 'authorization.json', {
        name: {'exact_response': f'{name} yes', 'quoted_request': f'approve the {name}?',
               'recorded_at': '2026-09-25T18:00:31Z'} for name in probe.AUTHORIZATIONS})
    return SimpleNamespace(root=root, origin=origin, source=source, request_dir=request_dir, tip_ledger=tip_ledger,
                           checkpoint=checkpoint, state=state, authorization=authorization, raw=raw)


def prepared(tmp_path, **kwargs):
    lin = lineage(tmp_path, **kwargs)
    path, identity = probe.prepare(lin.root / 'probe', source_registration=lin.source,
                                   source_request=lin.request_dir, tip_checkpoint=lin.checkpoint,
                                   sequence_state=lin.state, origin_registration=lin.origin,
                                   authorization=lin.authorization, require_clean=False)
    lin.registration, lin.identity = path, identity
    return lin


def wire(values):
    return ''.join(f"event: {v['type']}\ndata: {json.dumps(v)}\n\n" for v in values).encode()


def summarized_stream():
    return wire([
        {'type': 'message_start', 'message': {'id': 'msg_offline', 'type': 'message', 'role': 'assistant',
         'model': 'claude-opus-5', 'content': [], 'stop_reason': None,
         'usage': {'input_tokens': 100, 'output_tokens': 0, 'cache_read_input_tokens': 0}}},
        {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'thinking', 'thinking': '', 'signature': ''}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'thinking_delta', 'thinking': THINKING}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'signature_delta', 'signature': 'sig'}},
        {'type': 'content_block_stop', 'index': 0},
        {'type': 'content_block_start', 'index': 1, 'content_block': {'type': 'text', 'text': ''}},
        {'type': 'content_block_delta', 'index': 1, 'delta': {'type': 'text_delta', 'text': MARKER}},
        {'type': 'content_block_stop', 'index': 1},
        {'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}, 'usage': {'output_tokens': 20}},
        {'type': 'message_stop'}])


class Upstream:
    def __init__(self, reply):
        self.reply, self.requests, self.counts = reply, [], []

    def clients(self, manifest, key):
        assert key == 'offline-provider-key'
        def count_tokens(**fields):
            self.counts.append(fields)
            return SimpleNamespace(input_tokens=100)
        sdk = SimpleNamespace(messages=SimpleNamespace(count_tokens=count_tokens),
                              default_headers={'x-headroom-bypass': 'true'})
        def respond(request):
            self.requests.append(request)
            return self.reply(request)
        return sdk, httpx.Client(transport=httpx.MockTransport(respond))


def run(lin, upstream, **kwargs):
    return probe.run(lin.registration, lin.identity, clients=upstream.clients, key='offline-provider-key',
                     require_clean=False, **kwargs)


def test_the_probe_request_differs_from_the_retained_one_only_in_its_thinking_display():
    raw = native_request()
    derived = probe.derive_request(raw)
    assert json.loads(derived) == {**json.loads(raw), 'thinking': {'type': 'adaptive', 'display': 'summarized'}}
    assert derived.replace(probe.PROBE_THINKING, probe.ORIGINAL_THINKING) == raw
    for refused in (native_request({'tool_input': {'thinking': {'type': 'adaptive'}}}),
                    native_request({'thinking': {'type': 'enabled', 'budget_tokens': 1024}}),
                    native_request({'stream': False}),
                    derived):
        with pytest.raises(BudgetStop):
            probe.derive_request(refused)


def test_a_completed_probe_claims_the_tip_continues_its_ledger_and_keeps_no_text(tmp_path):
    lin = prepared(tmp_path)
    previous = lin.state.read_bytes()
    upstream = Upstream(lambda request: httpx.Response(200, content=summarized_stream(),
                                                        headers={'content-type': 'text/event-stream'}))
    result = run(lin, upstream)
    assert result['finding'] == 'completed' and result['client']['status'] == 200
    # The client outlasts the proxy: three count tries and pauses, connect, read bound, margin.
    assert json.loads(lin.registration.read_text())['transport']['client_timeout_seconds'] == 1200 + 3 * 125 + 20 + 120
    assert result['thinking_display'] == 'summarized_text' and result['proxy_failure'] is None
    # One provider request: exactly the derived bytes, on the runtime's path, under the registered headers.
    [sent] = upstream.requests
    assert sent.content == probe.derive_request(lin.raw) and sent.url.raw_path == b'/v1/messages?beta=true'
    assert sent.headers['anthropic-beta'] == BETA and sent.headers['x-headroom-bypass'] == 'true'
    assert sent.headers['x-api-key'] == 'offline-provider-key'
    assert upstream.counts[0]['thinking'] == {'type': 'adaptive', 'display': 'summarized'}
    [exchange] = result['provider_exchanges']
    assert exchange['status'] == 200 and exchange['events']['content_block_delta:thinking_delta']['count'] == 1
    assert exchange['thinking_text_chars'] == len(THINKING) and exchange['output_tokens'] == 20
    # The ledger carries the tip's rows and settles the probe's by its usage.
    state = json.loads((lin.root / 'probe' / 'billing.json').read_text())
    assert state['continued_from']['checkpoint_sha256'] == sha(lin.checkpoint)
    assert state['requests'][:2] == json.loads(lin.checkpoint.read_text())['requests']
    [row] = result['probe_rows']
    assert row['status'] == 'settled' and Decimal(row['cost_usd']) == Decimal(100) * Decimal('0.000005') + Decimal(20) * Decimal('0.000025')
    assert result['successor_continues_from'] == str(lin.root / 'probe' / 'billing.json')
    # The probe owns the tip, with the durable claim naming its predecessor.
    tip = json.loads(lin.state.read_text())
    assert tip['registration_sha256'] == lin.identity and tip['ledger_path'] == str(lin.root / 'probe' / 'billing.json')
    manifest = json.loads(lin.registration.read_text())
    claim = sequence_claim.context(manifest, lin.registration, lin.identity, lin.state,
                                   {'registration_sha256': sha(lin.origin),
                                    'ledger_path': str(lin.root / 'origin' / 'billing.json')}, probe.STAGE)
    sequence_claim.verify(claim, tip, previous)
    # Neither conversation nor thinking text reaches the result.
    kept = (lin.root / 'probe' / 'result.json').read_text()
    assert MARKER not in kept and THINKING not in kept
    with pytest.raises(BudgetStop, match='runs once'):
        run(lin, upstream)
    assert len(upstream.requests) == 1


def test_a_5xx_is_counted_at_its_whole_reservation_and_not_resent(tmp_path):
    lin = prepared(tmp_path)
    upstream = Upstream(lambda request: httpx.Response(500, json={'error': 'synthetic'}))
    result = run(lin, upstream)
    assert result['finding'] == 'upstream_http_500' and result['client']['status'] == 503
    assert len(upstream.requests) == 1 and result['stalls_survived'] == 1
    [row] = result['probe_rows']
    assert row['status'] == 'settled' and row['settlement_basis'] == STALL_DEBIT_BASIS
    assert row['cost_usd'] == row['reserved_usd'] and row['provider_charge_confirmed'] is False
    assert result['reconciled_checkpoint'] is None and result['thinking_display'] is None


def test_a_pending_row_is_settled_in_a_new_checkpoint_a_successor_can_continue(tmp_path):
    lin = prepared(tmp_path)
    upstream = Upstream(lambda request: httpx.Response(400, json={'error': 'synthetic refusal'}))
    result = run(lin, upstream)
    assert result['finding'] == 'upstream_http_400' and result['client']['status'] == 402
    ledger = lin.root / 'probe' / 'billing.json'
    assert [r['status'] for r in json.loads(ledger.read_text())['requests']][-1] == 'pending'
    reconciled = result['reconciled_checkpoint']
    assert reconciled['basis'] == probe.STANDING_DEBIT_BASIS
    assert result['successor_continues_from'] == reconciled['path']
    state = json.loads(Path(reconciled['path']).read_text())
    row = state['requests'][-1]
    assert (row['status'], row['cost_usd'], row['provider_charge_confirmed']) == ('settled', row['reserved_usd'], False)
    assert row['standing_authorization'] == json.loads(lin.authorization.read_text())['full_reservation_debit']
    assert state['reconciled_from']['checkpoint_sha256'] == sha(ledger)
    total = sum(Decimal(r['cost_usd']) for r in state['requests'])
    successor = Ledger(tmp_path / 'successor.json', manifest_sha256='successor', total_cap='600', attempt_cap='5')
    successor.continue_from(reconciled['path'], expected_sha256=reconciled['sha256'], expected_cost_usd=str(total))


def test_nothing_is_sent_when_the_tip_moved_the_lock_is_held_or_a_pin_changed(tmp_path):
    upstream = Upstream(lambda request: pytest.fail('provider reached'))
    lin = prepared(tmp_path / 'moved')
    lin.state.write_text(lin.state.read_text().replace('"parent_checkpoint_sha256"', '"parent_checkpoint_sha256" '))
    with pytest.raises(BudgetStop, match='tip moved'):
        run(lin, upstream)
    lin = prepared(tmp_path / 'locked')
    with SequenceLock(str(lin.state) + '.lock').acquire(timeout=0):
        with pytest.raises(Timeout):
            run(lin, upstream)
    lin = prepared(tmp_path / 'pinned')
    lin.authorization.write_text(lin.authorization.read_text().replace('yes', 'no'))
    with pytest.raises(BudgetStop, match='pin changed'):
        run(lin, upstream)
    for case in ('moved', 'locked', 'pinned'):
        assert not (tmp_path / case / 'probe' / 'billing.json').exists()
    assert not upstream.requests


def test_preparation_refuses_a_foreign_request_a_forked_checkpoint_or_too_little_budget(tmp_path):
    lin = lineage(tmp_path / 'foreign')
    (lin.request_dir / 'native_request.json').write_bytes(native_request({'max_tokens': 999}))
    with pytest.raises(BudgetStop, match='not one the lineage admitted'):
        probe.prepare(lin.root / 'probe', source_registration=lin.source, source_request=lin.request_dir,
                      tip_checkpoint=lin.checkpoint, sequence_state=lin.state, origin_registration=lin.origin,
                      authorization=lin.authorization, require_clean=False)
    lin = lineage(tmp_path / 'forked')
    value = json.loads(lin.checkpoint.read_text())
    value['requests'][0]['cost_usd'] = '9.00000000'
    lin.checkpoint.write_text(json.dumps(value))
    with pytest.raises(BudgetStop, match='more than one'):
        probe.prepare(lin.root / 'probe', source_registration=lin.source, source_request=lin.request_dir,
                      tip_checkpoint=lin.checkpoint, sequence_state=lin.state, origin_registration=lin.origin,
                      authorization=lin.authorization, require_clean=False)
    lin = lineage(tmp_path / 'full', tip_cost='593.00000000')
    with pytest.raises(BudgetStop, match='remaining budget'):
        probe.prepare(lin.root / 'probe', source_registration=lin.source, source_request=lin.request_dir,
                      tip_checkpoint=lin.checkpoint, sequence_state=lin.state, origin_registration=lin.origin,
                      authorization=lin.authorization, require_clean=False)


def test_event_times_count_frames_split_across_chunks_without_keeping_text():
    ticks = iter(range(100))
    record = {'headers': 0}
    times = probe.EventTimes(record, lambda: next(ticks))
    raw = summarized_stream().replace(b'\n', b'\r\n')
    for offset in range(0, len(raw), 37):
        times.chunk(raw[offset:offset + 37])
    assert record['events']['message_stop']['count'] == 1 and record['unparsed_frames'] == 0
    assert record['stop_reason'] == 'end_turn' and record['thinking_text_chars'] == len(THINKING)
    assert THINKING not in json.dumps(record) and MARKER not in json.dumps(record)
