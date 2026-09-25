"""One paid CBORG transport probe for the native arm (#2463).

Resends one retained native request through the registered native proxy and
the source registration's own provider transport, changing exactly one field:
`thinking` gains `"display": "summarized"`. It records when the provider's
response headers, first event, first thinking text and last byte arrived, so a
stream that outlives CBORG's advertised 270-second first-chunk limit can be
told from one that does not. One request, one sample, no control: a result
before 270 seconds says nothing about whether the display made the difference.

The probe is a link in the native lineage, not a side charge. Its
registration has an audit continuation's budget block and carries the tip's
budget amendment, so the audit's own validators check its predecessor: the
settled checkpoint, its reconciliation (`validate_audit_reconciliation`) and
the amendment (`validate_predecessor`). Holding the lineage's sequence lock,
it does all free work first: the clients, the proxy, one free token count of
the exact request, and the import of the checkpoint into its own ledger. Only
then does it take the tip with a durable sequence claim (#2137) and admit the
one paid request. A failure before the claim leaves the tip unchanged. A
successor continues from the probe's settled ledger. An audit prepared from
the earlier tip fails at its sequence guard instead of forking the budget
(#2469).

  prepare --out DIR --source-registration R --source-request DIR
          --tip-checkpoint C --sequence-state S --origin-registration O
          [--tip-reconciliation-receipt RECEIPT] --authorization A
  run --registration DIR/registration.json --sha256 HEX
  settle --registration DIR/registration.json --sha256 HEX

`run` executes at most once per registration and never resends. The proxy's
stall policy counts a 5xx, or a failure after the request left, at its whole
reservation. A row still pending afterwards is settled at its whole
reservation in a separate checkpoint with its own debit receipt, under the
maintainer's standing authorization, once the proxy has closed with no
handler running. The ledger itself is never rewritten. `result.json` is
written after the tip is claimed, whatever happens, and for a refused or
failed claim. A failure before the ledger import writes nothing and leaves the
probe runnable. From the import on, the registration is consumed; the tip
moves only with the claim. When a proxy handler outlived shutdown with a row
still pending, `settle` applies the deferred debit once the probe's process
has exited.
`result.json` records sizes, times, event types, bounded CBORG diagnostic
headers and accounting, and no request, response or thinking text. The
proxy's evidence folders under `attempt/requests/` keep the full request and
response, including any thinking summaries, as every native attempt does.
"""
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import time

import httpx

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
for _path in (str(HERE), str(BASE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import budget_amendment  # noqa: E402
from budgeted_cborg import (BudgetStop, LEGACY_UPSTREAM_READ_SECONDS, Ledger, POLICY_COUNT_PAUSE_SECONDS,  # noqa: E402
                            POLICY_COUNT_TRY_SECONDS, UPSTREAM_CONNECT_SECONDS, provider_context_headers,
                            write_new)
import native_proxy  # noqa: E402
from native_proxy import NativeProxy  # noqa: E402
import sequence_claim  # noqa: E402
import audit_controls  # noqa: E402
from audit_controls import bounded_stream, bounded_transport  # noqa: E402
from audit_controls import registration as audit_registration  # noqa: E402
from audit_controls import transport as audit_transport  # noqa: E402

KIND = 'd4d_native_transport_probe_v1'
RESULT_KIND = 'd4d_native_transport_probe_result_v1'
AUDIT_KIND = 'd4d_native_audit_continuation'
ATTEMPT = 'transport_probe'
STAGE = 'transport_probe'
ORIGINAL_THINKING = b'"thinking":{"type":"adaptive"}'
PROBE_THINKING = b'"thinking":{"type":"adaptive","display":"summarized"}'
VARIATION = {'field': 'thinking', 'from': {'type': 'adaptive'},
             'to': {'type': 'adaptive', 'display': 'summarized'}}
# Claude Code 2.1.272 posts its model requests to this path (#2463).
REQUEST_PATH = '/v1/messages?beta=true'
PROTOCOL_HEADERS = ('anthropic-version', 'anthropic-beta')
COUNT_FIELDS = ('model', 'system', 'messages', 'tools', 'tool_choice', 'thinking')
PROBE_CAP_USD = '5'
# The probe's own policy: one debit covers its one request.
STALL_POLICY = {'count_attempts': 3, 'max_stall_debits': 1}
CLIENT_MARGIN_SECONDS = 120
DEBIT_KIND = 'user_authorized_full_reservation_debit'
AUTHORIZATIONS = ('probe', 'full_reservation_debit')
RUN_ONCE = ('attempt', 'billing.json', 'result.json', 'reconciled_billing.json', 'sequence_claim',
            'sequence_claim_failed.json')
QUOTE_FIELDS = ('exact_response', 'quoted_request', 'recorded_at')
LIBRARIES = ('httpx', 'httpcore', 'h11', 'anthropic', 'certifi')
# The transport the source registration pinned; the probe runs the same bytes.
TRANSPORT_MODULES = ('notes/matched_cborg_2026-09-13/native_controls/native_proxy.py',
                     'notes/matched_cborg_2026-09-13/budgeted_cborg.py',
                     'notes/matched_cborg_2026-09-13/audit_controls/transport.py',
                     'notes/matched_cborg_2026-09-13/audit_controls/bounded_stream.py',
                     'notes/matched_cborg_2026-09-13/audit_controls/bounded_transport.py')
# Provider diagnostics kept in the result: named headers, bounded plain values.
DIAGNOSTIC_HEADERS = ('x-litellm-call-id', 'x-litellm-attempted-retries', 'x-litellm-attempted-fallbacks',
                      'x-litellm-response-duration-ms', 'x-litellm-overhead-duration-ms', 'x-litellm-version',
                      'x-litellm-model-group', 'x-litellm-model-id', 'x-litellm-timeout', 'retry-after')
DIAGNOSTIC_VALUE = re.compile(r'[A-Za-z0-9._:+-]{1,96}')
REQUEST_REFUSALS = frozenset({400, 413, 422})
NOT_SENT = frozenset({'ConnectError', 'ConnectTimeout', 'PoolTimeout', 'UnsupportedProtocol'})
SCOPE = ('One request and one sample, with no control. The replayed history\'s thinking blocks were '
         'produced with thinking omitted, so this tests the same history under a new display. Header '
         'times include the bounded worker\'s start and upload.')


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
               Path(budget_amendment.__file__), Path(sequence_claim.__file__), Path(audit_controls.__file__),
               Path(audit_registration.__file__), Path(audit_transport.__file__), Path(bounded_stream.__file__),
               Path(bounded_transport.__file__), Path(sys.modules['data_sheets_schema.stream_evidence'].__file__)]
    return sorted({str(p.resolve()) for p in modules} | {str(p) for p in sequence_claim.IMPLEMENTATIONS})


def interpreter():
    """The interpreter and libraries the bounded workers run under (#2475)."""
    executable = Path(sys.executable).resolve()
    return {'executable': sys.executable, 'resolved': str(executable), 'sha256': sha(executable),
            'version': sys.version,
            'libraries': {name: importlib.metadata.version(name) for name in LIBRARIES},
            'openssl': ssl.OPENSSL_VERSION}


def source_python(source):
    """The interpreter the source ran under, beside this one, for the record (#2475)."""
    path = source.get('python')
    resolved = Path(path).resolve() if isinstance(path, str) and Path(path).exists() else None
    return {'path': path, 'resolved': str(resolved) if resolved else None,
            'sha256': sha(resolved) if resolved else None,
            'same_binary': bool(resolved) and sha(resolved) == sha(Path(sys.executable).resolve()),
            # The same base binary can run another environment's libraries.
            'same_environment': path == sys.executable}


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


def source_transport(source):
    """The source registration's pins for the transport modules, which must be this checkout's bytes."""
    root, repository = Path(__file__).resolve().parents[3], Path(source['repository'])
    pins = {}
    for relative in TRANSPORT_MODULES:
        pinned = source['pinned_files'].get(str(repository / relative))
        if pinned is None or sha(root / relative) != pinned:
            raise BudgetStop('probe transport differs from the source registration\'s pinned transport')
        pins[relative] = pinned
    return pins


def validated_authorization(value):
    if not isinstance(value, dict) or set(value) != set(AUTHORIZATIONS):
        raise BudgetStop('probe authorization needs the probe and the full-reservation debit quotes')
    for name in AUTHORIZATIONS:
        quote = value[name]
        if (not isinstance(quote, dict) or set(quote) != set(QUOTE_FIELDS)
                or any(not isinstance(quote[k], str) or not quote[k].strip() for k in QUOTE_FIELDS)):
            raise BudgetStop('each probe authorization quotes a request, a response and when it was recorded')
    return value


def check_lineage(manifest):
    """The predecessor, checked by the audit's own validators; returns (source, checkpoint state).

    The checkpoint is the tip ledger itself, or its reconciliation, which
    `validate_audit_reconciliation` recomputes from the source ledger and
    receipt (#2471). Caps must equal the tip's in the checkpoint and the
    source registration alike, and the inherited amendment must prove the
    checkpoint (#2474)."""
    budget = manifest['budget']
    continuation = budget['continuation']
    checkpoint = audit_registration.pinned(manifest, continuation['checkpoint'], continuation['sha256'])
    bridge = continuation.get('reconciliation')
    if bridge is not None:
        state = audit_registration.validate_audit_reconciliation(manifest)
        source_path = audit_registration.pinned(manifest, bridge['source_registration'])
    else:
        state = read_json(checkpoint)
        source_path = audit_registration.pinned(manifest, str(checkpoint.with_name('registration.json')))
    source = read_json(source_path)
    rows = state.get('requests')
    if (source.get('kind') != AUDIT_KIND or state.get('manifest_sha256') != sha(source_path)
            or not isinstance(rows, list) or any(not isinstance(r, dict) or r.get('status') != 'settled' for r in rows)):
        raise BudgetStop('lineage tip checkpoint is not a settled audit checkpoint')
    if bridge is None and Path(source['budget']['ledger_path']) != checkpoint:
        raise BudgetStop('an unreconciled checkpoint must be the tip\'s own ledger')
    origin = audit_registration.pinned(manifest, manifest['parent']['registration'])
    if sha(Path(source['parent']['registration'])) != sha(origin):
        raise BudgetStop('the tip descends from another origin')
    for mine, tip, theirs in (('additional_usd', 'additional_cap_usd', 'additional_usd'),
                              ('per_attempt_usd', 'attempt_cap_usd', 'per_attempt_usd')):
        if not money(budget[mine]) == money(state[tip]) == money(source['budget'][theirs]):
            raise BudgetStop('probe caps differ from the tip checkpoint or its registration')
    if manifest.get('budget_amendment') != source.get('budget_amendment'):
        raise BudgetStop('probe drops or changes its tip\'s budget amendment')
    if 'budget_amendment' in manifest:
        budget_amendment.validate_predecessor(manifest, state, checkpoint_sha256=continuation['sha256'])
    if (budget['per_job_attempt_usd'] != {ATTEMPT: PROBE_CAP_USD}
            or money(PROBE_CAP_USD) > money(budget['per_attempt_usd'])):
        raise BudgetStop('probe attempt cap differs from its registration')
    total = sum((money(r.get('cost_usd')) for r in rows), Decimal(0))
    cap = money(budget['per_job_attempt_usd'][ATTEMPT])
    if total != money(continuation['cost_usd']) or total + cap > money(budget['additional_usd']):
        raise BudgetStop('probe cost or cap exceeds the lineage\'s remaining budget')
    return source, state


def check_tip_state(manifest, raw):
    """The live tip names the probe's predecessor."""
    state, source = strict_json(raw), manifest['budget']['continuation']
    tip = source['reconciliation']['source_registration'] if 'reconciliation' in source else str(
        Path(source['checkpoint']).with_name('registration.json'))
    ledger = source['reconciliation']['source_ledger'] if 'reconciliation' in source else source['checkpoint']
    if (state.get('schema_version') != 1 or state.get('registration_sha256') != sha(tip)
            or state.get('ledger_path') != ledger
            or state.get('source_registration_sha256') != sha(manifest['parent']['registration'])):
        raise BudgetStop('the lineage tip is not the probe\'s predecessor')


def prepare(out, *, source_registration, source_request, tip_checkpoint, sequence_state, origin_registration,
            authorization, tip_reconciliation_receipt=None, require_clean=True):
    out = Path(out).resolve()
    if out.exists():
        raise BudgetStop('probe directory already exists; a probe is prepared once')
    source_path, request_dir = Path(source_registration).resolve(), Path(source_request).resolve()
    checkpoint_path, state_path = Path(tip_checkpoint).resolve(), Path(sequence_state).resolve()
    origin_path, authorization_path = Path(origin_registration).resolve(), Path(authorization).resolve()
    source, origin = read_json(source_path), read_json(origin_path)
    origin_ledger = Path(origin['budget']['ledger_path']).resolve()
    if origin_ledger.with_name('audit_sequence.json') != state_path:
        raise BudgetStop('sequence state is not the origin ledger\'s')
    tip_ledger = Path(source['budget']['ledger_path']).resolve()
    native, protocol = request_dir / 'native_request.json', request_dir / 'request_protocol.json'
    raw = native.read_bytes()
    probe = derive_request(raw)
    if strict_json(raw).get('model') != source['model']['model']:
        raise BudgetStop('retained request model differs from its registration')
    headers = read_json(protocol)
    if any(not isinstance(headers.get(name), str) or not headers[name] for name in PROTOCOL_HEADERS):
        raise BudgetStop('retained request lacks its protocol headers')
    quotes = validated_authorization(read_json(authorization_path))
    checkpoint = read_json(checkpoint_path)
    continuation = {'checkpoint': str(checkpoint_path), 'sha256': sha(checkpoint_path),
                    'cost_usd': str(sum((money(r.get('cost_usd')) for r in checkpoint['requests']), Decimal(0)))}
    pinned = [source_path, native, protocol, checkpoint_path, tip_ledger, origin_path, authorization_path]
    if checkpoint_path != tip_ledger:
        if tip_reconciliation_receipt is None:
            raise BudgetStop('a reconciled tip checkpoint needs its reconciliation receipt')
        result = Path(source['job']['attempt_dir']) / 'result.json'
        continuation['reconciliation'] = {'source_registration': str(source_path), 'source_ledger': str(tip_ledger),
                                          'receipt': str(Path(tip_reconciliation_receipt).resolve()),
                                          'result': str(result)}
        pinned += [Path(tip_reconciliation_receipt).resolve(), result]
    implementation = implementation_paths()
    repository, commit = repository_state(implementation, require_clean=require_clean)
    manifest = {
        'kind': KIND, 'schema_version': 1, 'issue': 2463, 'prepared_at': now(),
        'repository': repository, 'code_commit': commit, 'require_clean': require_clean,
        'attempt': ATTEMPT, 'scope': SCOPE,
        'parent': {'registration': str(origin_path)},
        'sequence_state': str(state_path),
        'source': {'registration': str(source_path), 'registration_sha256': sha(source_path),
                   'request_dir': str(request_dir), 'native_request_sha256': digest(raw),
                   'canonical_request_sha256': canonical_sha(raw), 'request_protocol_sha256': sha(protocol)},
        'request': {'path': REQUEST_PATH, 'headers': {name: headers[name] for name in PROTOCOL_HEADERS},
                    'native_sha256': digest(probe), 'canonical_sha256': canonical_sha(probe),
                    'bytes': len(probe), 'variation': VARIATION},
        'lineage': {'sequence_state_sha256': sha(state_path), 'origin_ledger': str(origin_ledger)},
        # An audit continuation's budget block, so successor validators read it (#2474).
        'budget': {'additional_usd': checkpoint['additional_cap_usd'],
                   'per_attempt_usd': checkpoint['attempt_cap_usd'],
                   'per_job_attempt_usd': {ATTEMPT: PROBE_CAP_USD},
                   'prices_per_token': source['budget']['prices_per_token'],
                   'ledger_path': str(out / 'billing.json'), 'continuation': continuation},
        'transport': {'stall_policy': STALL_POLICY, 'client_timeout_seconds': client_timeout(source),
                      'source_pins': source_transport(source)},
        'runtime': interpreter(),
        'source_python': source_python(source),
        'authorization': quotes,
        'sequence_claim': {'protocol': sequence_claim.PROTOCOL},
    }
    budget_amendment.inherit(source, manifest)
    pins = {str(p): sha(p) for p in {*map(str, pinned), *implementation, manifest['runtime']['resolved']}}
    if 'budget_amendment' in manifest:
        pins.update({str(p): sha(p) for p in budget_amendment.paths(manifest)})
    ca = (source.get('provider_transport') or {}).get('ca_bundle')
    if ca is not None:
        pins[str(Path(ca).resolve())] = sha(ca)
    if 'reconciliation' in continuation and 'audit_batches' in source:
        # The reconciliation check re-verifies the stopped batch's closure
        # through the source's own pins, as an audit successor's does.
        from audit_controls.batch_native import require_closed_batch_runtime
        pins.update(source['pinned_files'])
        pins.update({str(p): sha(p) for p in require_closed_batch_runtime(source, read_json(result))})
    manifest['pinned_files'] = dict(sorted(pins.items()))
    source, state = check_lineage(manifest)
    check_tip_state(manifest, state_path.read_bytes())
    if canonical_sha(raw) not in {row.get('request_sha256') for row in state['requests']}:
        raise BudgetStop('retained request is not one the lineage admitted')
    out.mkdir(parents=True)
    raw_manifest = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    (out / 'registration.json').write_bytes(raw_manifest)
    return out / 'registration.json', digest(raw_manifest)


class EventTimes:
    """Arrival times of the stream's events; keeps counts, never text, and never raises (#2473)."""
    def __init__(self, record, clock):
        self.record, self.clock, self.buffer = record, clock, b''
        record.update(chunks=0, bytes=0, first_chunk=None, last_chunk=None, largest_gap_seconds=0.0,
                      events={}, unparsed_frames=0, timing_errors=0, thinking_text_chars=0,
                      first_thinking_text=None, output_tokens=None, stop_reason=None, message_usage=None)

    def chunk(self, raw):
        try:
            self._chunk(raw)
        except Exception:
            self.record['timing_errors'] += 1

    def _chunk(self, raw):
        at, record = self.clock(), self.record
        if record['last_chunk'] is not None:
            record['largest_gap_seconds'] = max(record['largest_gap_seconds'], at - record['last_chunk'])
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
            if not isinstance(kind, str):
                raise TypeError
        except (ValueError, TypeError, KeyError):
            record['unparsed_frames'] += 1
            return
        mapping = lambda name: value.get(name) if isinstance(value.get(name), dict) else {}
        key = kind
        if kind == 'content_block_start':
            key += ':' + str(mapping('content_block').get('type'))
        elif kind == 'content_block_delta':
            delta = mapping('delta')
            key += ':' + str(delta.get('type'))
            if delta.get('type') == 'thinking_delta' and isinstance(delta.get('thinking'), str):
                record['thinking_text_chars'] += len(delta['thinking'])
                if delta['thinking'] and record['first_thinking_text'] is None:
                    record['first_thinking_text'] = at
        elif kind == 'message_start':
            usage = mapping('message').get('usage')
            record['message_usage'] = ({k: v for k, v in usage.items() if type(v) is int}
                                       if isinstance(usage, dict) else None)
        elif kind == 'message_delta':
            usage = mapping('usage')
            if type(usage.get('output_tokens')) is int:
                record['output_tokens'] = usage['output_tokens']
            stop = mapping('delta').get('stop_reason')
            record['stop_reason'] = stop if isinstance(stop, str) else None
        entry = record['events'].setdefault(key[:80], {'count': 0, 'first': at, 'last': at})
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


def diagnostics(headers):
    """Named CBORG diagnostic headers with bounded plain values (#2478)."""
    kept = {}
    for name in DIAGNOSTIC_HEADERS:
        value = headers.get(name)
        if isinstance(value, str) and DIAGNOSTIC_VALUE.fullmatch(value):
            kept[name] = value
    return kept


class TimedUpstream:
    """Pass-through upstream that notes when bytes arrived; the bytes are the inner client's."""
    def __init__(self, inner, clock=time.monotonic):
        self.inner, self.clock, self.exchanges = inner, clock, []

    def __getattr__(self, name):
        return getattr(self.inner, name)

    @contextmanager
    def stream(self, method, url, **kwargs):
        record = {'started': self.clock(), 'started_at': now(), 'headers': None, 'status': None,
                  'diagnostics': {}, 'error': None, 'error_reason': None, 'error_at': None, 'ended': None}
        self.exchanges.append(record)
        try:
            with self.inner.stream(method, url, **kwargs) as response:
                record['headers'], record['status'] = self.clock(), response.status_code
                try:
                    record['diagnostics'] = diagnostics(response.headers)
                except Exception:
                    pass
                yield TimedResponse(response, record, self.clock)
        except BaseException as error:
            record['error'], record['error_at'] = type(error).__name__, self.clock()
            if isinstance(error, BudgetStop):
                record['error_reason'] = str(error)          # controller-authored, never provider text
            raise
        finally:
            record['ended'] = self.clock()


def relative(record):
    """Seconds from the exchange's start, to the millisecond."""
    start = record['started']
    def at(value):
        return None if value is None else round(value - start, 3)
    hidden = {'started', 'headers', 'first_chunk', 'last_chunk', 'first_thinking_text', 'error_at', 'ended', 'events'}
    out = {k: v for k, v in record.items() if k not in hidden}
    headers, first = record['headers'], record.get('first_chunk')
    out.update(headers_seconds=at(headers), first_chunk_seconds=at(first),
               headers_to_first_chunk_seconds=(None if headers is None or first is None else round(first - headers, 3)),
               last_chunk_seconds=at(record.get('last_chunk')),
               first_thinking_text_seconds=at(record.get('first_thinking_text')),
               error_seconds=at(record['error_at']), ended_seconds=at(record['ended']),
               largest_gap_between_chunks_seconds=round(record.get('largest_gap_seconds') or 0.0, 3),
               events={k: {'count': v['count'], 'first_seconds': at(v['first']), 'last_seconds': at(v['last'])}
                       for k, v in (record.get('events') or {}).items()})
    out.pop('largest_gap_seconds', None)
    return out


def thinking_display(exchanges):
    """What the stream showed of thinking: None where no thinking block was streamed."""
    streamed = [r for r in exchanges if (r.get('events') or {}).get('content_block_start:thinking')]
    if not streamed:
        return None
    return 'summarized_text' if any(r['thinking_text_chars'] for r in streamed) else 'no_text'


def finding(exchanges, client):
    """One label for the provider exchange (#2473)."""
    if not exchanges:
        return 'not_sent'
    last = exchanges[-1]
    events = last.get('events') or {}
    if last['status'] is None:
        return 'not_sent' if last['error'] in NOT_SENT else 'no_response_headers'
    if last['status'] != 200:
        return f"upstream_http_{last['status']}"
    if 'error' in events:
        return 'stream_error_event'
    if 'message_stop' in events:
        return 'completed' if client.get('status') == 200 else 'completed_not_delivered'
    if not last.get('chunks'):
        return 'no_stream'
    return 'stream_cut' if last['error'] else 'stream_ended_without_stop'


def settle_pending(ledger_path, out, manifest, registration_sha256, attempt, runtime):
    """Settle the probe's one pending row at its whole reservation, in a new checkpoint.

    Returns what happened; never raises on an outcome a person must resolve,
    so the timing record is always written (#2473). A handler still running at
    shutdown could still hold the request, so it is left to a person, as the
    audit's own reconciliation check requires a closed runtime."""
    raw = ledger_path.read_bytes()
    state = strict_json(raw)
    rows = state.get('requests') if isinstance(state, dict) else None
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return {'status': 'needs_person', 'reason': 'probe ledger is malformed'}
    unsettled = [row for row in rows if row.get('status') != 'settled']
    if not unsettled:
        return {'status': 'settled'}
    if runtime['unfinished_handlers'] != 0 or runtime['proxy_shutdown_complete'] is not True:
        # `settle` applies the debit once the probe's process has exited.
        return {'status': 'needs_person', 'reason': HANDLER_RUNNING}
    if len(unsettled) != 1 or unsettled[0].get('status') != 'pending' or unsettled[0].get('attempt') != attempt:
        return {'status': 'needs_person', 'reason': 'unsettled rows the standing debit does not cover',
                'rows': [{k: row.get(k) for k in ('id', 'status', 'reserved_usd', 'cost_usd')} for row in unsettled]}
    row = dict(unsettled[0])
    quote = manifest['authorization']['full_reservation_debit']
    observation = ledger_path.parent / 'attempt' / 'requests' / row['id'] / 'admission.json'
    receipt = {'kind': DEBIT_KIND, 'attempt': attempt, 'request_id': row['id'],
               'request_sha256': row['request_sha256'], 'previous_reservation_usd': row['reserved_usd'],
               'budget_debit_usd': row['reserved_usd'], 'released_excess_reservation_usd': '0',
               'provider_charge_confirmed': False, 'provider_charge_usd': None, 'provider_usage_is_final': False,
               'accounting_observation_sha256': sha(observation), 'new_provider_requests': 0,
               'scientific_acceptance': False, 'source_attempt_completed': False,
               'source_attempt_kind': ATTEMPT, 'source_ledger_modified': False,
               'source_ledger_sha256': digest(raw), 'source_registration_sha256': registration_sha256,
               'recorded_at': now(), 'user_authorization': {**quote, 'standing': True},
               'runtime_at_settlement': dict(runtime)}
    receipt_path = out / 'debit_receipt.json'
    write_new(receipt_path, receipt)
    row.update(status='settled', cost_usd=row['reserved_usd'], settled_at=receipt['recorded_at'],
               settlement_basis=DEBIT_KIND, reconciliation_receipt_sha256=sha(receipt_path),
               accounting_observation_sha256=receipt['accounting_observation_sha256'],
               provider_charge_confirmed=False, provider_charge_usd=None, provider_usage_is_final=False,
               released_excess_reservation_usd='0', source_attempt_kind=ATTEMPT, source_attempt_outcome='stopped')
    reconciled = {**state, 'requests': [row if r.get('id') == row['id'] else r for r in rows],
                  'reconciled_from': {'checkpoint_sha256': digest(raw), 'receipt_sha256': sha(receipt_path),
                                      'request_id': row['id'], 'previous_status': 'pending',
                                      'budget_debit_usd': row['reserved_usd'], 'settlement_basis': DEBIT_KIND,
                                      'provider_charge_confirmed': False, 'source_attempt_completed': False}}
    path = out / 'reconciled_billing.json'
    write_new(path, reconciled)
    return {'status': 'reconciled', 'path': str(path), 'sha256': sha(path), 'receipt': str(receipt_path),
            'receipt_sha256': sha(receipt_path), 'request_id': row['id'], 'budget_debit_usd': row['reserved_usd']}


def free_count(sdk, raw):
    """One free count of a request exactly as it would be sent (#2472)."""
    request = strict_json(raw)
    fields = {k: v for k, v in request.items() if k in COUNT_FIELDS}
    return sdk.messages.count_tokens(**fields, timeout=POLICY_COUNT_TRY_SECONDS).input_tokens


def count_refused(error):
    """A refusal of the request as it would be sent. A key, permission or route
    error (401, 403, 404) says nothing about the display and leaves the probe
    runnable."""
    import anthropic
    return isinstance(error, anthropic.APIStatusError) and error.status_code in REQUEST_REFUSALS


def close_quietly(*resources):
    for resource in resources:
        try:
            close = getattr(resource, 'close', None)
            if close:
                close()
        except Exception:
            pass


def run(registration, expected_sha256, *, clients=None, key=None, require_clean=True, clock=time.monotonic):
    registration = Path(registration).resolve()
    raw_manifest = registration.read_bytes()
    if digest(raw_manifest) != expected_sha256:
        raise BudgetStop('probe registration differs from the bound hash')
    manifest = strict_json(raw_manifest)
    if manifest.get('kind') != KIND or registration.name != 'registration.json':
        raise BudgetStop('not a transport probe registration')
    if manifest.get('require_clean') is not require_clean:
        raise BudgetStop('probe runs under the clean-tree rule it was prepared with')
    out = registration.parent
    ledger_path = Path(manifest['budget']['ledger_path'])
    if ledger_path != out / 'billing.json':
        raise BudgetStop('probe ledger is not beside its registration')
    if any((out / name).exists() for name in RUN_ONCE):
        raise BudgetStop('probe already ran; a probe runs once')
    verify_pins(manifest)
    if not set(implementation_paths()) <= set(manifest['pinned_files']):
        raise BudgetStop('probe implementation is not the registered one')
    if interpreter() != manifest['runtime']:
        raise BudgetStop('probe interpreter or libraries differ from the registered ones')
    _, commit = repository_state(implementation_paths(), require_clean=require_clean)
    source, state = check_lineage(manifest)
    raw = (Path(manifest['source']['request_dir']) / 'native_request.json').read_bytes()
    probe = derive_request(raw)
    if digest(probe) != manifest['request']['native_sha256']:
        raise BudgetStop('probe request differs from its registration')
    key = key or os.environ.get('CBORG_API_KEY')
    if not key:
        raise BudgetStop('CBORG_API_KEY is required')
    budget, lineage, continuation = manifest['budget'], manifest['lineage'], manifest['budget']['continuation']
    attempt = f'{expected_sha256}:{ATTEMPT}'
    identity = dict(manifest_sha256=expected_sha256, total_cap=budget['additional_usd'],
                    attempt_cap=budget['per_attempt_usd'], attempt_caps_usd={attempt: budget['per_job_attempt_usd'][ATTEMPT]})
    carried = dict(expected_sha256=continuation['sha256'], expected_cost_usd=continuation['cost_usd'],
                   **(budget_amendment.ledger_bridge(manifest, state, checkpoint_sha256=continuation['sha256'])
                      if 'budget_amendment' in manifest else {}))
    state_path = Path(manifest['sequence_state'])
    origin = {'registration_sha256': sha(manifest['parent']['registration']), 'ledger_path': lineage['origin_ledger']}
    lock = audit_registration.SequenceLock(str(state_path) + '.lock')
    with lock.acquire(timeout=0):
        if any((out / name).exists() for name in RUN_ONCE):
            raise BudgetStop('probe already ran; a probe runs once')
        previous_raw = state_path.read_bytes()
        if digest(previous_raw) != lineage['sequence_state_sha256']:
            raise BudgetStop('the lineage tip moved since the probe was prepared')
        check_tip_state(manifest, previous_raw)
        claim = sequence_claim.context(manifest, registration, expected_sha256, state_path, origin, STAGE)
        # Everything that can fail without cost happens before the tip changes hands (#2472).
        ledger = Ledger(ledger_path, **identity)
        sdk, upstream = (clients or audit_transport.provider_clients)(source, key)
        started_at, client, interrupted = now(), {}, None
        timed = TimedUpstream(upstream, clock)
        try:
            proxy = NativeProxy(sdk=sdk, ledger=ledger, attempt=attempt, evidence=out / 'attempt' / 'requests',
                                model=source['model']['model'], prices=budget['prices_per_token'],
                                verify=lambda: verify_pins(manifest), provider_key=key,
                                base_url=source['provider_base_url'], request_headers=provider_context_headers(source),
                                upstream=timed,
                                upstream_read_timeout_seconds=source.get('native_upstream_read_timeout_seconds'),
                                stall_policy=manifest['transport']['stall_policy'],
                                response_buffer=source.get('native_response_buffer'))
            # The retained request first, as a control: a key, budget or route
            # error refuses it too, and leaves the probe runnable (#2493).
            control = free_count(sdk, raw)
            counted = free_count(sdk, probe)
        except Exception as error:
            close_quietly(sdk, upstream)
            if 'control' in locals() and count_refused(error):
                # The provider refused to count the request as it would be
                # sent: a finding, with nothing claimed or spent. Anything
                # else leaves nothing written, so the probe can run later.
                result = {'kind': RESULT_KIND, 'registration_sha256': expected_sha256, 'code_commit': commit,
                          'started_at': started_at, 'ended_at': now(), 'finding': 'count_refused',
                          'count_error': type(error).__name__,
                          'count_status': getattr(error, 'status_code', None), 'control_count': control,
                          'tip_claimed': False, 'provider_exchanges': [], 'scope': SCOPE}
                write_new(out / 'result.json', result)
                return result
            raise
        # The ledger exists before the tip names it. A failure after this
        # leaves the tip unchanged beside an unspent ledger that nothing reads
        # and that consumes this registration, never a tip naming a ledger
        # that does not exist.
        try:
            ledger.continue_from(continuation['checkpoint'], **carried)
        except BaseException:
            close_quietly(sdk, upstream)
            raise
        value = {'schema_version': 1, 'registration_sha256': expected_sha256,
                 'ledger_path': budget['ledger_path'], 'parent_checkpoint_sha256': continuation['sha256'],
                 'source_registration_sha256': origin['registration_sha256']}
        temporary, written = state_path.with_name(state_path.name + '.tmp'), False
        try:
            with temporary.open('x') as handle:
                written = True
                json.dump(value, handle, indent=2)
                handle.write('\n')
            temporary.replace(state_path)
            written = False
            sequence_claim.record(claim, value, previous_raw)
        except BaseException as error:
            close_quietly(sdk, upstream)
            if written:
                # Our own temporary, never replaced: left behind it would
                # block every later owner's claim.
                try:
                    temporary.unlink()
                except OSError:
                    pass
            try:
                claimed = strict_json(state_path.read_bytes()).get('registration_sha256') == expected_sha256
            except Exception:
                claimed = None
            write_new(out / 'result.json', {'kind': RESULT_KIND, 'registration_sha256': expected_sha256,
                'code_commit': commit, 'started_at': started_at, 'ended_at': now(), 'finding': 'claim_failed',
                'claim_error': type(error).__name__, 'tip_claimed': claimed, 'free_count': counted,
                'provider_exchanges': [], 'successor_continues_from': None, 'scope': SCOPE})
            raise
        try:
            with proxy.running() as url:
                headers = {'x-api-key': proxy.token, 'content-type': 'application/json',
                           **manifest['request']['headers']}
                begun = clock()
                try:
                    with httpx.Client(timeout=httpx.Timeout(manifest['transport']['client_timeout_seconds'],
                                                            connect=10), trust_env=False) as local:
                        response = local.post(url + manifest['request']['path'], content=probe, headers=headers)
                    client = {'status': response.status_code, 'bytes': len(response.content),
                              'retry_advised': response.headers.get('x-should-retry')}
                except httpx.HTTPError as error:
                    client = {'status': None, 'error': type(error).__name__}
                client['elapsed_seconds'] = round(clock() - begun, 3)
        except BaseException as error:
            interrupted = error
            client.setdefault('error', type(error).__name__)
        finally:
            runtime = {'proxy_initialized': True, 'proxy_shutdown_complete': proxy.frozen is True,
                       'unfinished_handlers': proxy.unfinished_handlers}
            try:
                # A handler still running could be writing these records.
                snapshot = copy.deepcopy(list(timed.exchanges))
                exchanges = [relative(record) for record in snapshot]
            except Exception:
                snapshot, exchanges = [], None
            try:
                settlement = settle_pending(ledger_path, out, manifest, expected_sha256, attempt, runtime)
            except Exception as error:
                settlement = {'status': 'needs_person', 'reason': type(error).__name__}
            rows, successor, successor_cost = [], None, None
            try:
                rows = [row for row in read_json(ledger_path)['requests'] if row.get('attempt') == attempt]
                successor = (settlement['path'] if settlement['status'] == 'reconciled' else
                             str(ledger_path) if settlement['status'] == 'settled' else None)
                if successor:
                    successor_cost = str(sum((money(r['cost_usd']) for r in read_json(successor)['requests']),
                                             Decimal(0)))
            except Exception:
                pass
            result = {
                'kind': RESULT_KIND, 'registration_sha256': expected_sha256, 'code_commit': commit,
                'started_at': started_at, 'ended_at': now(), 'tip_claimed': True, 'free_count': counted,
                'finding': ('interrupted' if isinstance(interrupted, (KeyboardInterrupt, SystemExit)) else
                            'controller_error' if interrupted is not None else
                            'unrecorded' if exchanges is None else finding(snapshot, client)),
                'client': client, 'interrupted': type(interrupted).__name__ if interrupted is not None else None,
                'provider_exchanges': exchanges, 'exchanges_complete': runtime['unfinished_handlers'] == 0,
                'runtime': runtime, 'thinking_display': thinking_display(snapshot),
                'proxy_failure': proxy.failure, 'stalls_survived': proxy.stalls_survived,
                'probe_rows': [{k: row.get(k) for k in ('id', 'status', 'reserved_usd', 'cost_usd',
                                                        'settlement_basis', 'provider_charge_confirmed', 'usage')}
                               for row in rows],
                'settlement': settlement,
                'successor_continues_from': successor, 'successor_cost_usd': successor_cost,
                'scope': SCOPE,
            }
            write_new(out / 'result.json', result)
        if interrupted is not None:
            raise interrupted
        return result


HANDLER_RUNNING = 'a proxy handler was still running at shutdown'


def settle(registration, expected_sha256):
    """Apply the standing debit the runtime gate deferred, once the probe's process has exited (#2493).

    A running probe holds the sequence lock for its whole run, so holding it
    here shows the process, and with it every proxy handler, has ended."""
    registration = Path(registration).resolve()
    if digest(registration.read_bytes()) != expected_sha256:
        raise BudgetStop('probe registration differs from the bound hash')
    manifest = read_json(registration)
    out = registration.parent
    result = read_json(out / 'result.json')
    if (manifest.get('kind') != KIND or (result.get('settlement') or {}).get('reason') != HANDLER_RUNNING
            or (out / 'reconciled_billing.json').exists() or (out / 'settlement_after_exit.json').exists()):
        raise BudgetStop('this probe has no settlement deferred for a running handler')
    state_path = Path(manifest['sequence_state'])
    try:
        lock = audit_registration.SequenceLock(str(state_path) + '.lock').acquire(timeout=0)
    except Exception as error:
        raise BudgetStop('the sequence lock is held; the probe or another owner is still running') from error
    with lock:
        runtime = {'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0,
                   'basis': 'the probe process had exited: its sequence lock was free'}
        settlement = settle_pending(Path(manifest['budget']['ledger_path']), out, manifest, expected_sha256,
                                    f'{expected_sha256}:{ATTEMPT}', runtime)
        settlement['successor_continues_from'] = (settlement['path'] if settlement['status'] == 'reconciled' else
                                                  manifest['budget']['ledger_path']
                                                  if settlement['status'] == 'settled' else None)
        write_new(out / 'settlement_after_exit.json', settlement)
    return settlement


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    commands = parser.add_subparsers(dest='command', required=True)
    make = commands.add_parser('prepare')
    for name in ('out', 'source-registration', 'source-request', 'tip-checkpoint', 'sequence-state',
                 'origin-registration', 'authorization'):
        make.add_argument('--' + name, required=True)
    make.add_argument('--tip-reconciliation-receipt')
    go = commands.add_parser('run')
    go.add_argument('--registration', required=True)
    go.add_argument('--sha256', required=True)
    later = commands.add_parser('settle')
    later.add_argument('--registration', required=True)
    later.add_argument('--sha256', required=True)
    args = parser.parse_args(argv)
    if args.command == 'settle':
        print(json.dumps(settle(args.registration, args.sha256), indent=2))
        return 0
    if args.command == 'prepare':
        path, identity = prepare(args.out, source_registration=args.source_registration,
                                 source_request=args.source_request, tip_checkpoint=args.tip_checkpoint,
                                 sequence_state=args.sequence_state, origin_registration=args.origin_registration,
                                 authorization=args.authorization,
                                 tip_reconciliation_receipt=args.tip_reconciliation_receipt)
        print(json.dumps({'registration': str(path), 'sha256': identity}))
        return 0
    result = run(args.registration, args.sha256)
    summary = {k: result.get(k) for k in ('finding', 'client', 'thinking_display', 'proxy_failure',
                                          'stalls_survived', 'settlement', 'successor_continues_from',
                                          'successor_cost_usd', 'tip_claimed')}
    summary['provider_exchanges'] = [{k: e.get(k) for k in ('status', 'headers_seconds', 'first_chunk_seconds',
                                                            'first_thinking_text_seconds', 'last_chunk_seconds',
                                                            'largest_gap_between_chunks_seconds', 'error',
                                                            'error_seconds', 'diagnostics')}
                                     for e in result.get('provider_exchanges', [])]
    summary['probe_rows'] = [{k: r.get(k) for k in ('status', 'cost_usd', 'settlement_basis')}
                             for r in result.get('probe_rows', [])]
    print(json.dumps(summary, indent=2))
    return 0 if result['finding'] == 'completed' else 1


if __name__ == '__main__':
    sys.exit(main())
