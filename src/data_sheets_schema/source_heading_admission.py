"""Fixed ordinary-call journal for shared generation v2, never a transport API.

Count replies are endpoint declarations. They bind the complete normalized
request and output allowance; they are not hard guarantees of billed usage.
Receipt and typed stages keep their existing independent admission journals.
"""
from __future__ import annotations

import copy
from pathlib import Path
import uuid

from . import shared_generation as sg, usage_ledger as ledger
from . import receipt_completion as receipts

FORMAT = 'source_heading_admissions_v1'
KEY = 'source_heading_admissions'
MAX_BYTES = 64_000_000
MAX_CALLS = 512


def selected(spec):
    return getattr(spec, 'shared_generation_version', 0) == 2


def ordinary(phase):
    from .typed_audit_runtime import PHASES
    return phase != receipts.PHASE and phase not in PHASES


def _payload(kwargs):
    from . import api_runner as api
    requested = kwargs['max_tokens']
    if type(requested) is not int or not 1 <= requested <= api.output_limit(kwargs['model']):
        raise ledger.UsageLedgerError('routing request output cap cannot be clamped')
    request = api.PhaseRequest(phase='captured', system=kwargs['system'], messages=kwargs['messages'])
    return receipts.request_payload(request, {'name': kwargs['model'],
        'temperature': kwargs['temperature'], 'thinking': kwargs.get('thinking'),
        'effort': kwargs.get('effort')}, {'max_output_tokens': requested})


def _load(pin):
    sg._exact(pin, {'path', 'sha256'}, 'routing artifact pin')
    path = Path(pin['path'])
    if path.stat().st_size > MAX_BYTES:
        raise ledger.UsageLedgerError('routing journal artifact exceeds bound')
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or sg.sha(raw) != pin['sha256']:
        raise ledger.UsageLedgerError('routing journal artifact identity differs')
    from .audit_omissions import _mapping
    return _mapping(raw, 'routing journal artifact', limit=MAX_BYTES, json_only=True)


def _base(spec, data):
    captured = sg._context_capture(spec)
    return {'format': FORMAT, 'generation_id': data['generation_id'],
            'registration_sha256': sg.sha(captured.registration)}


def _limits(spec):
    return sg._context_capture(spec).document()['routing']['generation_limits']


def _check_wire(spec, payload):
    reg = sg._context_capture(spec).document()
    limits = reg['routing']['generation_limits']
    sg._exact(payload, {'model', 'max_tokens', 'system', 'messages'}
        | ({'temperature'} if reg['runtime']['temperature'] is not None else set())
        | ({'thinking'} if reg['runtime']['thinking'] is not None else set())
        | ({'output_config'} if reg['runtime']['effort'] is not None else set()), 'routing sent payload')
    expected = {'model': reg['runtime']['model']}
    if reg['runtime']['temperature'] is not None:
        expected['temperature'] = reg['runtime']['temperature']
    if reg['runtime']['thinking'] is not None:
        expected['thinking'] = reg['runtime']['thinking']
    if reg['runtime']['effort'] is not None:
        expected['output_config'] = {'effort': reg['runtime']['effort']}
    if any(sg.canonical(payload[k]) != sg.canonical(v) for k, v in expected.items()):
        raise ledger.UsageLedgerError('routing sent settings differ from registration')
    if (type(payload['max_tokens']) is not int or not 1 <= payload['max_tokens'] <= limits['max_output_tokens']
            or len(sg.canonical(payload)) > limits['max_request_bytes']):
        raise ledger.UsageLedgerError('complete routing request exceeds registered output/byte bounds')
    sg.require_generation_context(spec, payload['messages'])
    sg.require_routing_context(spec, payload['messages'])


def _check_payload(spec, payload, count):
    _check_wire(spec, payload)
    limits = _limits(spec)
    receipts._context_check(count, payload, limits)
    if count['input_tokens'] > limits['max_input_tokens_per_call']:
        raise ledger.UsageLedgerError('routing endpoint count exceeds registered per-call input allowance')


def _recheck(spec, data, *, allow_prepared=False, allow_pending=False, allow_response_capture=False, _reader=None):
    if _reader is not None:
        from .source_heading_completed import _Reader
        if type(_reader) is not _Reader:
            raise TypeError("invalid captured journal reader")
    state = data.get(KEY)
    usage = {row['usage_id']: row for row in data['rows'] if ordinary(row.get('phase'))}
    if state is None:
        if usage or (data.get('pending_call') and ordinary(data['pending_call'].get('phase'))):
            raise ledger.UsageLedgerError('ordinary routing usage lacks its counted request journal')
        return None, []
    sg._exact(state, {'format', 'generation_id', 'registration_sha256', 'rows'}, 'routing journal')
    if any(state[k] != v for k, v in _base(spec, data).items()):
        raise ledger.UsageLedgerError('routing journal belongs to another generation or registration')
    rows = state['rows']
    if type(rows) is not list or not len(rows) <= min(_limits(spec)['max_calls'], MAX_CALLS):
        raise ledger.UsageLedgerError('routing journal exceeds call allowance')
    admitted, checked, previous = set(), [], []
    for n, row in enumerate(rows):
        sg._exact(row, {'phase', 'attempt', 'request', 'usage_id', 'response'}, 'routing journal row')
        if (type(row['phase']) is not str or not ordinary(row['phase'])
                or type(row['attempt']) is not int or row['attempt'] < 1):
            raise ledger.UsageLedgerError('invalid ordinary routing phase or attempt')
        captured = (_load(row['request']) if _reader is None else _reader.load(row['request']))
        sg._exact(captured, {'generation_id', 'registration_sha256', 'phase', 'attempt', 'prior_usage_ids',
                            'payload', 'count'}, 'routing counted request')
        if (captured['generation_id'] != data['generation_id']
                or captured['registration_sha256'] != state['registration_sha256']
                or captured['phase'] != row['phase'] or captured['attempt'] != row['attempt']
                or captured['prior_usage_ids'] != previous):
            raise ledger.UsageLedgerError('routing request chronology or association differs')
        _check_payload(spec, captured['payload'], captured['count'])
        uid = row['usage_id']
        if uid is None:
            if not allow_prepared or n != len(rows) - 1 or row['response'] is not None:
                raise ledger.UsageLedgerError('routing prepared request is unresolved')
        else:
            if type(uid) is not str or not uid or uid in admitted:
                raise ledger.UsageLedgerError('duplicate or invalid routing usage identity')
            admitted.add(uid)
            current = usage.get(uid)
            if current is None:
                pending = data.get('pending_call')
                if not (allow_pending and n == len(rows) - 1 and pending
                        and pending['usage_id'] == uid and pending['phase'] == row['phase']):
                    raise ledger.UsageLedgerError('routing admitted request lacks settled usage')
            else:
                if (current.get('phase') != row['phase'] or current.get('attempt') != row['attempt']
                        or current.get('max_tokens') != captured['payload']['max_tokens']):
                    raise ledger.UsageLedgerError('routing usage differs from exact request/response association')
                if row['response'] is None:
                    if allow_response_capture and n == len(rows) - 1:
                        # The SDK just returned; usage was persisted first.
                        # Only this private response-write path may finish it.
                        previous.append(uid)
                        checked.append((row, captured))
                        continue
                    raise ledger.UsageLedgerError('routing settled usage lacks response evidence; no restart')
                response = (_load(row['response']) if _reader is None else _reader.load(row['response']))
                sg._exact(response, {'usage_id', 'request_sha256', 'stop_reason', 'text', 'usage'}, 'routing response')
                if (response['usage_id'] != uid or response['request_sha256'] != row['request']['sha256']
                        or response['stop_reason'] != current.get('stop_reason')
                        or type(response['text']) is not str):
                    raise ledger.UsageLedgerError('routing response belongs to another admitted request')
                if receipts._usage_problems(response['usage']) or any(
                        response['usage'].get(k) != current.get(k)
                        for k in ('input_tokens', 'output_tokens', 'cache_read', 'cache_write', 'thinking_tokens')):
                    raise ledger.UsageLedgerError('routing response usage is unknown or differs from accounted usage')
                if (response['usage']['input_tokens'] > _limits(spec)['max_input_tokens_per_call']
                        or response['usage']['output_tokens'] > captured['payload']['max_tokens']):
                    raise ledger.UsageLedgerError('observed routing usage exceeded its declared allowance')
                previous.append(uid)
        checked.append((row, captured))
    if set(usage) - admitted:
        raise ledger.UsageLedgerError('ordinary routing usage has no exactly associated request')
    if list(usage) != [r['usage_id'] for r, _ in checked if r['usage_id'] in usage]:
        raise ledger.UsageLedgerError('ordinary routing usage order differs from admitted chronology')
    return state, checked


def prepare(spec, phase, attempt, client, kwargs):
    """Count and save before the existing usage transaction admits the call."""
    if not selected(spec) or not ordinary(phase):
        return client, kwargs
    ledger.require_resolved(spec)
    data = ledger._read(spec)
    state, checked = _recheck(spec, data)
    limits = _limits(spec)
    if len(checked) >= limits['max_calls']:
        raise ledger.UsageLedgerError('routing generation call allowance exhausted')
    payload = _payload(kwargs)
    _check_wire(spec, payload)  # known byte/output/settings refusals precede counting
    bounded = receipts._single_attempt_client(client)
    sg.require_client(spec, bounded)
    count = receipts._count_context(bounded, payload, limits)
    _check_payload(spec, payload, count)
    if (sum(c['count']['input_tokens'] for _, c in checked) + count['input_tokens'] > limits['aggregate_input_tokens']
            or sum(c['payload']['max_tokens'] for _, c in checked) + payload['max_tokens'] > limits['aggregate_output_tokens']):
        raise ledger.UsageLedgerError('routing aggregate counted/reserved allowance exhausted')
    base = _base(spec, data)
    value = {k: base[k] for k in ('generation_id', 'registration_sha256')}
    value.update(phase=phase, attempt=attempt, prior_usage_ids=[r['usage_id'] for r, _ in checked],
                 payload=payload, count=count)
    pin = receipts._save(spec, 'routing_request_' + uuid.uuid4().hex + '.json', value)
    if state is None:
        state = {**base, 'rows': []}
    state['rows'].append({'phase': phase, 'attempt': attempt, 'request': pin, 'usage_id': None, 'response': None})
    data[KEY] = state
    ledger._write(spec, data)
    return bounded, {**kwargs, 'transport_attempts': 1}


def bind_admission(spec, phase, attempt, *, data, usage_id):
    """Called only by begin_call, before its single pending-call atomic write."""
    if not selected(spec) or not ordinary(phase):
        return
    state, _ = _recheck(spec, data, allow_prepared=True)
    if not state or not state['rows']:
        raise ledger.UsageLedgerError('routing dispatch has no prepared counted request')
    row = state['rows'][-1]
    if row['usage_id'] is not None or row['phase'] != phase or row['attempt'] != attempt:
        raise ledger.UsageLedgerError('routing admission does not match its prepared phase/attempt')
    row['usage_id'] = usage_id


def require_wire(spec, phase, usage_id, kwargs):
    if not selected(spec) or not ordinary(phase):
        return
    data = ledger._read(spec)
    state, checked = _recheck(spec, data, allow_pending=True)
    if not checked or checked[-1][0]['usage_id'] != usage_id or _payload(kwargs) != checked[-1][1]['payload']:
        raise ledger.UsageLedgerError('actual ordinary send differs from its counted admitted wire')


def remember_response(spec, phase, usage_id, response):
    if not selected(spec) or not ordinary(phase):
        return
    from . import reasoning
    data = ledger._read(spec)
    state, checked = _recheck(spec, data, allow_response_capture=True)
    row = state['rows'][-1]
    if row['usage_id'] != usage_id or row['response'] is not None:
        raise ledger.UsageLedgerError('routing response cannot replace another delivery')
    usage = response.usage
    observed = {k: getattr(usage, name, None) for k, name in (
        ('input_tokens', 'input_tokens'), ('output_tokens', 'output_tokens'),
        ('cache_read', 'cache_read_input_tokens'), ('cache_write', 'cache_creation_input_tokens'))}
    observed['thinking_tokens'] = reasoning.thinking_tokens(response)
    value = {'usage_id': usage_id, 'request_sha256': row['request']['sha256'],
        'stop_reason': getattr(response, 'stop_reason', None),
        'text': ''.join(b.text for b in response.content if getattr(b, 'type', '') == 'text'),
        'usage': {k: receipts._counter_evidence(v) for k, v in observed.items()}}
    if len(sg.canonical(value)) > MAX_BYTES:
        raise ledger.UsageLedgerError('routing response evidence exceeds bound')
    row['response'] = receipts._save(spec, 'routing_response.json', value, usage_id=usage_id)
    ledger._write(spec, data)


def completion_check(spec):
    return _completion_check(spec, ledger._read(spec))


def _completion_check(spec, data, *, _reader=None):
    state, checked = _recheck(spec, data, _reader=_reader)
    if not state or data.get('pending_call') is not None:
        raise ledger.UsageLedgerError('routing completion requires settled exact request associations')
    limits = _limits(spec)
    counted = sum(c['count']['input_tokens'] for _, c in checked)
    reserved = sum(c['payload']['max_tokens'] for _, c in checked)
    if counted > limits['aggregate_input_tokens'] or reserved > limits['aggregate_output_tokens']:
        raise ledger.UsageLedgerError('routing saved aggregate allowance exceeded')
    return {**_base(spec, data), 'rows': copy.deepcopy(state['rows']),
        'counted_input_tokens': counted, 'reserved_output_tokens': reserved,
        'scientific_eligibility': False,
        'basis': 'Exact local request/count/usage association; not provider authentication or a guaranteed spend cap.'}
