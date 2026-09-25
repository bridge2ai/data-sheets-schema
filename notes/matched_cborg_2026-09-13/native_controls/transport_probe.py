"""One paid CBORG transport probe for the native arm (#2463).

Resends one retained native request through the registered native proxy and
the source registration's own provider transport, changing exactly one field:
`thinking` gains `"display": "summarized"`. It records when the provider's
response headers, first event, first thinking text and last byte arrived, so a
stream that outlives CBORG's advertised 270-second first-chunk limit can be
told from one that does not.

The probe is a link in the native lineage, not a side charge. Holding the
lineage's sequence lock, it checks that the tip is still the one it was
prepared against, takes the tip with a durable sequence claim (#2137),
continues the tip's settled checkpoint in its own ledger under the same caps,
and admits one request. A successor must continue from the probe's settled
ledger. An audit prepared from the old tip fails at its sequence guard instead
of forking the budget.

  prepare --out DIR --source-registration R --source-request DIR
          --tip-checkpoint C --sequence-state S --origin-registration O
          --authorization A
  run --registration DIR/registration.json --sha256 HEX

`run` executes at most once per registration and never resends. The proxy's
stall policy counts a 5xx, or a failure after the request left, at its whole
reservation. A row still pending afterwards is settled at its whole
reservation in a separate reconciled checkpoint, under the maintainer's
standing authorization. The ledger itself is never rewritten. Nothing of the
request, response or thinking text is printed or copied into the result. The
result records sizes, times, event types and accounting only.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
for _path in (str(HERE), str(BASE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from budgeted_cborg import (BudgetStop, LEGACY_UPSTREAM_READ_SECONDS, Ledger, POLICY_COUNT_PAUSE_SECONDS,  # noqa: E402
                            POLICY_COUNT_TRY_SECONDS, UPSTREAM_CONNECT_SECONDS, provider_context_headers, write_new)
import native_proxy  # noqa: E402
from native_proxy import NativeProxy  # noqa: E402
import sequence_claim  # noqa: E402
from audit_controls import bounded_stream, bounded_transport  # noqa: E402
from audit_controls import registration as audit_registration  # noqa: E402
from audit_controls import transport as audit_transport  # noqa: E402

KIND = 'd4d_native_transport_probe_v1'
RESULT_KIND = 'd4d_native_transport_probe_result_v1'
ATTEMPT = 'transport_probe'
STAGE = 'transport_probe'
ORIGINAL_THINKING = b'"thinking":{"type":"adaptive"}'
PROBE_THINKING = b'"thinking":{"type":"adaptive","display":"summarized"}'
VARIATION = {'field': 'thinking', 'from': {'type': 'adaptive'},
             'to': {'type': 'adaptive', 'display': 'summarized'}}
# Claude Code 2.1.272 posts its model requests to this path (#2463).
REQUEST_PATH = '/v1/messages?beta=true'
PROTOCOL_HEADERS = ('anthropic-version', 'anthropic-beta')
PROBE_CAP_USD = '5'
STALL_POLICY = {'count_attempts': 3, 'max_stall_debits': 1}
CLIENT_MARGIN_SECONDS = 120
STANDING_DEBIT_BASIS = 'standing_authorized_full_reservation_debit'
AUTHORIZATIONS = ('probe', 'full_reservation_debit')
QUOTE_FIELDS = ('exact_response', 'quoted_request', 'recorded_at')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_sha(raw):
    """The ledger's request identity: sorted-key JSON plus a newline (CappedMessages)."""
    return digest((json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False) + '\n').encode())


def now():
    return datetime.now(timezone.utc).isoformat()


def strict_json(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise BudgetStop('duplicate JSON field in probe evidence')
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(BudgetStop('nonfinite JSON in probe evidence')))


def read_json(path):
    return strict_json(Path(path).read_bytes())


def money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise BudgetStop('probe amount is not a valid decimal') from error
    if not amount.is_finite() or amount < 0:
        raise BudgetStop('probe amount must be finite and non-negative')
    return amount


def derive_request(raw):
    """The retained request with only `thinking.display` added, byte for byte elsewhere."""
    if raw.count(ORIGINAL_THINKING) != 1 or PROBE_THINKING in raw:
        raise BudgetStop('retained request lacks exactly one adaptive thinking setting')
    original = strict_json(raw)
    if (not isinstance(original, dict) or original.get('thinking') != VARIATION['from']
            or original.get('stream') is not True):
        raise BudgetStop('retained request is not a streamed adaptive-thinking request')
    probe = raw.replace(ORIGINAL_THINKING, PROBE_THINKING)
    if strict_json(probe) != {**original, 'thinking': VARIATION['to']}:
        raise BudgetStop('display substitution changed more than the thinking setting')
    return probe


def implementation_paths():
    """Every module whose bytes decide what the probe sends, counts or records."""
    modules = [Path(__file__), Path(native_proxy.__file__), Path(sys.modules[Ledger.__module__].__file__),
               Path(sequence_claim.__file__), Path(audit_registration.__file__), Path(audit_transport.__file__),
               Path(bounded_stream.__file__), Path(bounded_transport.__file__),
               Path(sys.modules['data_sheets_schema.stream_evidence'].__file__)]
    return sorted({str(p.resolve()) for p in modules} | {str(p) for p in sequence_claim.IMPLEMENTATIONS})


def client_timeout(source):
    """Outlast the proxy: every count try and pause, the connect allowance and the read bound."""
    read = source.get('native_upstream_read_timeout_seconds') or LEGACY_UPSTREAM_READ_SECONDS
    counting = STALL_POLICY['count_attempts'] * (POLICY_COUNT_TRY_SECONDS + POLICY_COUNT_PAUSE_SECONDS)
    return read + counting + UPSTREAM_CONNECT_SECONDS + CLIENT_MARGIN_SECONDS


def verify_pins(manifest):
    for name, expected in manifest['pinned_files'].items():
        if sha(name) != expected:
            raise BudgetStop('a registered probe pin changed')


def repository_state(paths, *, require_clean):
    root = Path(__file__).resolve().parents[3]
    commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if require_clean:
        dirty = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain', '--', *paths], text=True)
        if dirty.strip():
            raise BudgetStop('probe implementation differs from the committed tree')
    return str(root), commit


def validated_authorization(value):
    if not isinstance(value, dict) or set(value) != set(AUTHORIZATIONS):
        raise BudgetStop('probe authorization needs the probe and the full-reservation debit quotes')
    for name in AUTHORIZATIONS:
        quote = value[name]
        if (not isinstance(quote, dict) or set(quote) != set(QUOTE_FIELDS)
                or any(not isinstance(quote[k], str) or not quote[k].strip() for k in QUOTE_FIELDS)):
            raise BudgetStop('each probe authorization quotes a request, a response and when it was recorded')
    return value


def settled_total(state):
    rows = state.get('requests')
    if not isinstance(rows, list) or any(not isinstance(r, dict) or r.get('status') != 'settled' for r in rows):
        raise BudgetStop('lineage tip checkpoint has an unsettled charge')
    return sum((money(r.get('cost_usd')) for r in rows), Decimal(0))


def check_tip(checkpoint, ledger, state, *, source_sha, origin_sha, ledger_sha):
    """The checkpoint is the tip ledger with at most its one pending row settled at full reservation."""
    if (state.get('schema_version') != 1 or state.get('registration_sha256') != source_sha
            or state.get('source_registration_sha256') != origin_sha
            or checkpoint.get('manifest_sha256') != source_sha or ledger.get('manifest_sha256') != source_sha):
        raise BudgetStop('lineage tip does not name the source registration')
    old, new = ledger.get('requests'), checkpoint.get('requests')
    if not isinstance(old, list) or not isinstance(new, list) or len(old) != len(new):
        raise BudgetStop('tip checkpoint rows differ from the tip ledger')
    changed = [(a, b) for a, b in zip(old, new) if a != b]
    if any(a.get('id') != b.get('id') for a, b in zip(old, new)):
        raise BudgetStop('tip checkpoint reorders or replaces tip ledger rows')
    if not changed:
        return
    if len(changed) != 1:
        raise BudgetStop('tip checkpoint changes more than one tip ledger row')
    before, after = changed[0]
    reconciled = checkpoint.get('reconciled_from') or {}
    if (before.get('status') != 'pending' or after.get('status') != 'settled'
            or after.get('cost_usd') != before.get('reserved_usd') or after.get('provider_charge_confirmed') is not False
            or after.get('request_sha256') != before.get('request_sha256')
            or reconciled.get('checkpoint_sha256') != ledger_sha or reconciled.get('request_id') != before.get('id')):
        raise BudgetStop('tip checkpoint does not settle the tip ledger\'s pending row at its reservation')


def prepare(out, *, source_registration, source_request, tip_checkpoint, sequence_state, origin_registration,
            authorization, require_clean=True):
    out = Path(out).resolve()
    if out.exists():
        raise BudgetStop('probe directory already exists; a probe is prepared once')
    source_path, request_dir = Path(source_registration).resolve(), Path(source_request).resolve()
    checkpoint_path, state_path = Path(tip_checkpoint).resolve(), Path(sequence_state).resolve()
    origin_path, authorization_path = Path(origin_registration).resolve(), Path(authorization).resolve()
    source, origin = read_json(source_path), read_json(origin_path)
    ledger_path = source_path.parent / 'billing.json'
    origin_ledger = Path(origin['budget']['ledger_path']).resolve()
    if origin_ledger.with_name('audit_sequence.json') != state_path:
        raise BudgetStop('sequence state is not the origin ledger\'s')
    state, checkpoint, tip_ledger = read_json(state_path), read_json(checkpoint_path), read_json(ledger_path)
    if Path(state.get('ledger_path', '')).resolve() != ledger_path:
        raise BudgetStop('lineage tip names another ledger')
    check_tip(checkpoint, tip_ledger, state, source_sha=sha(source_path), origin_sha=sha(origin_path),
              ledger_sha=sha(ledger_path))
    total = settled_total(checkpoint)
    cap = money(checkpoint.get('additional_cap_usd'))
    if total + money(PROBE_CAP_USD) > cap:
        raise BudgetStop('probe cap exceeds the lineage\'s remaining budget')
    native, protocol = request_dir / 'native_request.json', request_dir / 'request_protocol.json'
    raw = native.read_bytes()
    probe = derive_request(raw)
    if canonical_sha(raw) not in {row.get('request_sha256') for row in checkpoint['requests']}:
        raise BudgetStop('retained request is not one the lineage admitted')
    if strict_json(raw).get('model') != source['model']['model']:
        raise BudgetStop('retained request model differs from its registration')
    headers = read_json(protocol)
    if any(not isinstance(headers.get(name), str) or not headers[name] for name in PROTOCOL_HEADERS):
        raise BudgetStop('retained request lacks its protocol headers')
    quotes = validated_authorization(read_json(authorization_path))
    pinned = [source_path, native, protocol, checkpoint_path, ledger_path, origin_path, authorization_path]
    ca = (source.get('provider_transport') or {}).get('ca_bundle')
    if ca is not None:
        pinned.append(Path(ca).resolve())
    implementation = implementation_paths()
    repository, commit = repository_state(implementation, require_clean=require_clean)
    manifest = {
        'kind': KIND, 'schema_version': 1, 'issue': 2463, 'prepared_at': now(),
        'repository': repository, 'code_commit': commit, 'attempt': ATTEMPT,
        'source': {'registration': str(source_path), 'registration_sha256': sha(source_path),
                   'request_dir': str(request_dir), 'native_request_sha256': digest(raw),
                   'canonical_request_sha256': canonical_sha(raw), 'request_protocol_sha256': sha(protocol)},
        'request': {'path': REQUEST_PATH, 'headers': {name: headers[name] for name in PROTOCOL_HEADERS},
                    'native_sha256': digest(probe), 'canonical_sha256': canonical_sha(probe),
                    'bytes': len(probe), 'variation': VARIATION},
        'lineage': {'sequence_state': str(state_path), 'sequence_state_sha256': sha(state_path),
                    'tip_ledger': str(ledger_path), 'tip_ledger_sha256': sha(ledger_path),
                    'tip_checkpoint': str(checkpoint_path), 'tip_checkpoint_sha256': sha(checkpoint_path),
                    'tip_cost_usd': str(total), 'origin_registration': str(origin_path),
                    'origin_registration_sha256': sha(origin_path), 'origin_ledger': str(origin_ledger)},
        'budget': {'ledger_path': str(out / 'billing.json'),
                   'additional_cap_usd': checkpoint['additional_cap_usd'], 'attempt_cap_usd': PROBE_CAP_USD,
                   'prices_per_token': source['budget']['prices_per_token']},
        'transport': {'stall_policy': STALL_POLICY, 'client_timeout_seconds': client_timeout(source)},
        'authorization': quotes,
        'sequence_claim': {'protocol': sequence_claim.PROTOCOL},
        'pinned_files': {str(p): sha(p) for p in sorted({*map(str, pinned), *implementation})},
    }
    out.mkdir(parents=True)
    raw_manifest = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    (out / 'registration.json').write_bytes(raw_manifest)
    return out / 'registration.json', digest(raw_manifest)


class EventTimes:
    """Arrival times of the stream's events; keeps counts, never text."""
    def __init__(self, record, clock):
        self.record, self.clock, self.buffer = record, clock, b''
        record.update(chunks=0, bytes=0, first_chunk=None, last_chunk=None, largest_gap_seconds=0.0,
                      events={}, unparsed_frames=0, thinking_text_chars=0, first_thinking_text=None,
                      output_tokens=None, stop_reason=None, message_usage=None)

    def chunk(self, raw):
        at, record = self.clock(), self.record
        previous = record['last_chunk'] if record['last_chunk'] is not None else record['headers']
        if previous is not None:
            record['largest_gap_seconds'] = max(record['largest_gap_seconds'], at - previous)
        record['chunks'] += 1
        record['bytes'] += len(raw)
        if record['first_chunk'] is None:
            record['first_chunk'] = at
        record['last_chunk'] = at
        self.buffer = (self.buffer + raw).replace(b'\r\n', b'\n')
        while b'\n\n' in self.buffer:
            frame, self.buffer = self.buffer.split(b'\n\n', 1)
            lines = [line[5:].lstrip(b' ') for line in frame.split(b'\n') if line.startswith(b'data:')]
            if lines:
                self.event(b'\n'.join(lines), at)

    def event(self, data, at):
        record = self.record
        try:
            value = json.loads(data)
            kind = value['type']
        except (ValueError, TypeError, KeyError):
            record['unparsed_frames'] += 1
            return
        key = kind
        if kind == 'content_block_start':
            key += ':' + str((value.get('content_block') or {}).get('type'))
        elif kind == 'content_block_delta':
            delta = value.get('delta') or {}
            key += ':' + str(delta.get('type'))
            if delta.get('type') == 'thinking_delta':
                chars = len(delta.get('thinking') or '')
                record['thinking_text_chars'] += chars
                if chars and record['first_thinking_text'] is None:
                    record['first_thinking_text'] = at
        elif kind == 'message_start':
            usage = (value.get('message') or {}).get('usage') or {}
            record['message_usage'] = {k: v for k, v in usage.items() if type(v) is int}
        elif kind == 'message_delta':
            usage = value.get('usage') or {}
            if type(usage.get('output_tokens')) is int:
                record['output_tokens'] = usage['output_tokens']
            record['stop_reason'] = (value.get('delta') or {}).get('stop_reason')
        entry = record['events'].setdefault(key, {'count': 0, 'first': at, 'last': at})
        entry['count'] += 1
        entry['last'] = at


class TimedResponse:
    def __init__(self, response, record, clock):
        self._response = response
        self.status_code, self.headers = response.status_code, response.headers
        self._events = EventTimes(record, clock)

    def iter_bytes(self):
        for chunk in self._response.iter_bytes():
            self._events.chunk(chunk)
            yield chunk

    def __getattr__(self, name):
        return getattr(self._response, name)


class TimedUpstream:
    """Pass-through upstream that notes when bytes arrived; the bytes are the inner client's."""
    def __init__(self, inner, clock=time.monotonic):
        self.inner, self.clock, self.exchanges = inner, clock, []

    def __getattr__(self, name):
        return getattr(self.inner, name)

    @contextmanager
    def stream(self, method, url, **kwargs):
        record = {'started': self.clock(), 'started_at': now(), 'headers': None, 'status': None,
                  'error': None, 'error_at': None, 'ended': None}
        self.exchanges.append(record)
        try:
            with self.inner.stream(method, url, **kwargs) as response:
                record['headers'], record['status'] = self.clock(), response.status_code
                yield TimedResponse(response, record, self.clock)
        except BaseException as error:
            record['error'], record['error_at'] = type(error).__name__, self.clock()
            raise
        finally:
            record['ended'] = self.clock()


def relative(record):
    """Seconds from the exchange's start, to the millisecond."""
    start = record['started']
    def at(value):
        return None if value is None else round(value - start, 3)
    out = {k: v for k, v in record.items() if k not in {'started', 'headers', 'first_chunk', 'last_chunk',
                                                        'first_thinking_text', 'error_at', 'ended', 'events'}}
    out.update(headers_seconds=at(record['headers']), first_chunk_seconds=at(record.get('first_chunk')),
               last_chunk_seconds=at(record.get('last_chunk')),
               first_thinking_text_seconds=at(record.get('first_thinking_text')),
               error_seconds=at(record['error_at']), ended_seconds=at(record['ended']),
               largest_gap_seconds=round(record.get('largest_gap_seconds') or 0.0, 3),
               events={k: {'count': v['count'], 'first_seconds': at(v['first']), 'last_seconds': at(v['last'])}
                       for k, v in (record.get('events') or {}).items()})
    return out


def settle_pending(ledger_path, out, manifest, attempt):
    """Settle the probe's one pending row at its whole reservation, in a new checkpoint."""
    raw = ledger_path.read_bytes()
    state = strict_json(raw)
    open_rows = [row for row in state['requests'] if row.get('status') != 'settled']
    if not open_rows:
        return None
    if len(open_rows) != 1 or open_rows[0].get('status') != 'pending' or open_rows[0].get('attempt') != attempt:
        raise BudgetStop('probe ledger needs a person\'s reconciliation')
    row = dict(open_rows[0])
    quote = manifest['authorization']['full_reservation_debit']
    row.update(status='settled', cost_usd=row['reserved_usd'], settled_at=now(),
               settlement_basis=STANDING_DEBIT_BASIS, provider_charge_confirmed=False,
               provider_charge_usd=None, provider_usage_is_final=False, released_excess_reservation_usd='0',
               standing_authorization=dict(quote))
    reconciled = {**state, 'requests': [row if r.get('id') == row['id'] else r for r in state['requests']],
                  'reconciled_from': {'checkpoint_sha256': digest(raw), 'request_id': row['id'],
                                      'previous_status': 'pending', 'settlement_basis': STANDING_DEBIT_BASIS,
                                      'budget_debit_usd': row['reserved_usd'], 'provider_charge_confirmed': False,
                                      'source_attempt_completed': False}}
    path = out / 'reconciled_billing.json'
    write_new(path, reconciled)
    return {'path': str(path), 'sha256': sha(path), 'request_id': row['id'], 'basis': STANDING_DEBIT_BASIS,
            'budget_debit_usd': row['reserved_usd']}


def thinking_display(exchanges):
    """What the stream showed of thinking: None where no thinking block was streamed."""
    streamed = [r for r in exchanges if (r.get('events') or {}).get('content_block_start:thinking')]
    if not streamed:
        return None
    return 'summarized_text' if any(r['thinking_text_chars'] for r in streamed) else 'no_text'


def finding(exchanges, client):
    if not exchanges:
        return 'refused_before_send'
    last = exchanges[-1]
    if last['status'] == 200 and last.get('stop_reason') is not None and client.get('status') == 200:
        return 'completed'
    if last['status'] is not None and last['status'] != 200:
        return f"upstream_http_{last['status']}"
    return 'transport_failure' if last['error'] else 'incomplete'


def run(registration, expected_sha256, *, clients=None, key=None, require_clean=True, clock=time.monotonic):
    registration = Path(registration).resolve()
    raw_manifest = registration.read_bytes()
    if digest(raw_manifest) != expected_sha256:
        raise BudgetStop('probe registration differs from the bound hash')
    manifest = strict_json(raw_manifest)
    if manifest.get('kind') != KIND or registration.name != 'registration.json':
        raise BudgetStop('not a transport probe registration')
    out = registration.parent
    attempt_dir, ledger_path = out / 'attempt', Path(manifest['budget']['ledger_path'])
    if ledger_path != out / 'billing.json':
        raise BudgetStop('probe ledger is not beside its registration')
    if attempt_dir.exists() or ledger_path.exists() or (out / 'result.json').exists():
        raise BudgetStop('probe already ran; a probe runs once')
    verify_pins(manifest)
    if not set(implementation_paths()) <= set(manifest['pinned_files']):
        raise BudgetStop('probe implementation is not the registered one')
    _, commit = repository_state(implementation_paths(), require_clean=require_clean)
    source = read_json(manifest['source']['registration'])
    raw = (Path(manifest['source']['request_dir']) / 'native_request.json').read_bytes()
    probe = derive_request(raw)
    if digest(probe) != manifest['request']['native_sha256']:
        raise BudgetStop('probe request differs from its registration')
    key = key or os.environ.get('CBORG_API_KEY')
    if not key:
        raise BudgetStop('CBORG_API_KEY is required')
    lineage = manifest['lineage']
    state_path = Path(lineage['sequence_state'])
    origin = {'registration_sha256': lineage['origin_registration_sha256'], 'ledger_path': lineage['origin_ledger']}
    lock = audit_registration.SequenceLock(str(state_path) + '.lock')
    with lock.acquire(timeout=0):
        previous_raw = state_path.read_bytes()
        if digest(previous_raw) != lineage['sequence_state_sha256']:
            raise BudgetStop('the lineage tip moved since the probe was prepared')
        claim = sequence_claim.context(manifest, registration, expected_sha256, state_path, origin, STAGE)
        value = {'schema_version': 1, 'registration_sha256': expected_sha256,
                 'ledger_path': manifest['budget']['ledger_path'],
                 'parent_checkpoint_sha256': lineage['tip_checkpoint_sha256'],
                 'source_registration_sha256': lineage['origin_registration_sha256']}
        temporary = state_path.with_name(state_path.name + '.tmp')
        with temporary.open('x') as handle:
            json.dump(value, handle, indent=2)
            handle.write('\n')
        temporary.replace(state_path)
        sequence_claim.record(claim, value, previous_raw)
        # The probe now owns the tip; any failure from here leaves it consumed.
        attempt_dir.mkdir()
        budget = manifest['budget']
        ledger = Ledger(ledger_path, manifest_sha256=expected_sha256,
                        total_cap=budget['additional_cap_usd'], attempt_cap=budget['attempt_cap_usd'])
        ledger.continue_from(lineage['tip_checkpoint'], expected_sha256=lineage['tip_checkpoint_sha256'],
                             expected_cost_usd=lineage['tip_cost_usd'])
        attempt = f'{expected_sha256}:{ATTEMPT}'
        sdk, upstream = (clients or audit_transport.provider_clients)(source, key)
        timed = TimedUpstream(upstream, clock)
        proxy = NativeProxy(sdk=sdk, ledger=ledger, attempt=attempt, evidence=attempt_dir / 'requests',
                            model=source['model']['model'], prices=budget['prices_per_token'],
                            verify=lambda: verify_pins(manifest), provider_key=key,
                            base_url=source['provider_base_url'], request_headers=provider_context_headers(source),
                            upstream=timed,
                            upstream_read_timeout_seconds=source.get('native_upstream_read_timeout_seconds'),
                            stall_policy=manifest['transport']['stall_policy'],
                            response_buffer=source.get('native_response_buffer'))
        started_at, client = now(), {}
        with proxy.running() as url:
            headers = {'x-api-key': proxy.token, 'content-type': 'application/json',
                       **manifest['request']['headers']}
            begun = clock()
            try:
                with httpx.Client(timeout=httpx.Timeout(manifest['transport']['client_timeout_seconds'], connect=10),
                                  trust_env=False) as local:
                    response = local.post(url + manifest['request']['path'], content=probe, headers=headers)
                client = {'status': response.status_code, 'bytes': len(response.content),
                          'retry_advised': response.headers.get('x-should-retry')}
            except httpx.HTTPError as error:
                client = {'status': None, 'error': type(error).__name__}
            client['elapsed_seconds'] = round(clock() - begun, 3)
        reconciled = settle_pending(ledger_path, out, manifest, attempt)
        rows = [row for row in read_json(ledger_path)['requests'] if row.get('attempt') == attempt]
        result = {
            'kind': RESULT_KIND, 'registration_sha256': expected_sha256, 'code_commit': commit,
            'started_at': started_at,
            'ended_at': now(), 'finding': finding(timed.exchanges, client), 'client': client,
            'provider_exchanges': [relative(record) for record in timed.exchanges],
            'thinking_display': thinking_display(timed.exchanges),
            'proxy_failure': proxy.failure, 'stalls_survived': proxy.stalls_survived,
            'count_retries': proxy.messages.count_retries, 'unfinished_handlers': proxy.unfinished_handlers,
            'probe_rows': [{k: row.get(k) for k in ('id', 'status', 'reserved_usd', 'cost_usd', 'settlement_basis',
                                                    'provider_charge_confirmed', 'usage')} for row in rows],
            'ledger': {'path': str(ledger_path), 'sha256': sha(ledger_path)},
            'reconciled_checkpoint': reconciled,
            'successor_continues_from': reconciled['path'] if reconciled else str(ledger_path),
        }
        write_new(out / 'result.json', result)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    commands = parser.add_subparsers(dest='command', required=True)
    make = commands.add_parser('prepare')
    for name in ('out', 'source-registration', 'source-request', 'tip-checkpoint', 'sequence-state',
                 'origin-registration', 'authorization'):
        make.add_argument('--' + name, required=True)
    go = commands.add_parser('run')
    go.add_argument('--registration', required=True)
    go.add_argument('--sha256', required=True)
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        path, identity = prepare(args.out, source_registration=args.source_registration,
                                 source_request=args.source_request, tip_checkpoint=args.tip_checkpoint,
                                 sequence_state=args.sequence_state, origin_registration=args.origin_registration,
                                 authorization=args.authorization)
        print(json.dumps({'registration': str(path), 'sha256': identity}))
        return 0
    result = run(args.registration, args.sha256)
    summary = {k: result[k] for k in ('finding', 'client', 'thinking_display', 'proxy_failure',
                                      'stalls_survived', 'successor_continues_from')}
    summary['provider_exchanges'] = [{k: e.get(k) for k in ('status', 'headers_seconds', 'first_chunk_seconds',
                                                            'first_thinking_text_seconds', 'last_chunk_seconds',
                                                            'largest_gap_seconds', 'error', 'error_seconds')}
                                     for e in result['provider_exchanges']]
    summary['probe_rows'] = [{k: r.get(k) for k in ('status', 'cost_usd', 'settlement_basis')}
                             for r in result['probe_rows']]
    print(json.dumps(summary, indent=2))
    return 0 if result['finding'] == 'completed' else 1


if __name__ == '__main__':
    sys.exit(main())
