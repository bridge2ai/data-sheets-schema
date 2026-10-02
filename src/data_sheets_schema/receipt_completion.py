"""One registered receipt-only continuation, with generation-bound recovery.

No import-time client or API-runner dependency. Historical renderer 24 uses the
separate rereceipt module and keeps its original identity.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

POLICY_PATH = Path('src/download/prompts/receipt_completion_runtime_v1.md')
POLICY_SHA256 = '9a2b553bb9f14a3a431469a39469f5492a3f8c3d9718dccb3b07b311b2504765'
PHASE = 'full_receipt_completion'
AUDIT_HEADER = '# Receipt completion candidates for independent audit\n\n'
TRANSCRIPT = 'receipt_completion_transcript.json'
_INPUT_CLASS = None


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def policy_text() -> str:
    from data_sheets_schema.resources import resource_path
    raw = resource_path(POLICY_PATH).read_bytes()
    if sha(raw) != POLICY_SHA256:
        raise ValueError('receipt completion runtime policy differs from its frozen SHA256')
    return raw.decode('utf-8')


def policy_identity() -> dict:
    policy_text()
    from data_sheets_schema.receipts import RERECEIPTS_INSTRUMENT
    return {'version': 1, 'path': str(POLICY_PATH), 'sha256': POLICY_SHA256,
            'receipt_instrument_version': 4, 'receipt_instrument': copy.deepcopy(RERECEIPTS_INSTRUMENT),
            'phase': PHASE, 'audit_header': AUDIT_HEADER}


def registration(spec) -> dict:
    from data_sheets_schema.receipt_completion_policy import parse_registration
    if not isinstance(spec.receipt_completion_registration, str):
        raise ValueError('receipt completion requires immutable registration JSON')
    value = parse_registration(spec.receipt_completion_registration.encode('utf-8'))
    if value['condition'] != spec.condition:
        raise ValueError('receipt completion registration condition differs from RunSpec')
    return value


def registration_identity(spec) -> dict:
    from data_sheets_schema.receipt_completion_policy import registration_identity as identify
    registration(spec)
    return identify(spec.receipt_completion_registration.encode('utf-8'))


def schema_capture() -> dict:
    from data_sheets_schema import api_runner as api
    from data_sheets_schema.schema_snapshot import capture_schema
    captured = capture_schema(api.FULL_SCHEMA_PATH, strict=True)
    return {'sources': [{'name': name, 'path': str(path), 'sha256': sha(raw),
                         'text': raw.decode('utf-8')} for name, path, raw in captured.sources]}


def schema_identity() -> dict:
    return {'sources': [{k: v for k, v in row.items() if k != 'text'}
                        for row in schema_capture()['sources']]}


def preflight(spec, settings: dict) -> dict:
    from data_sheets_schema import api_runner as api
    reg = registration(spec)
    if not spec.writes_receipt:
        raise ValueError('receipt completion requires a receipt-producing condition')
    if reg['max_output_tokens'] > api.output_limit(settings['name']):
        raise ValueError('registered receipt completion output cap exceeds the route; cannot clamp it')
    named_limit = api.context_facts(settings['name'], [])['limit_tokens']
    if named_limit is not None and reg['context_limit_tokens'] > named_limit:
        raise ValueError('registered receipt completion context exceeds the explicitly named route window')
    policy_text()
    return reg


def _state(spec):
    from data_sheets_schema import usage_ledger as ledger
    if not ledger.ledger_path(spec).exists():
        return None
    return ledger._read(spec).get('receipt_completion')


def _set_state(spec, state):
    from data_sheets_schema import usage_ledger as ledger
    data = ledger._read(spec)
    data['receipt_completion'] = copy.deepcopy(state)
    ledger._write(spec, data)


def _save(spec, name: str, value, *, usage_id=None) -> dict:
    from data_sheets_schema import api_runner as api
    raw = canonical(value)
    path = api._snapshot(spec, f'{spec.project}_{name}', raw.decode('utf-8'), usage_id=usage_id)
    return {'path': str(path), 'sha256': sha(raw)}


def _load(pin: dict) -> dict:
    from data_sheets_schema.usage_ledger import UsageLedgerError
    try:
        raw = Path(pin['path']).read_bytes()
        if sha(raw) != pin['sha256']:
            raise ValueError('SHA256 differs')
        from data_sheets_schema.evidence_assertions import load_json
        value = load_json(raw.decode('utf-8'))
        if not isinstance(value, dict):
            raise ValueError('expected mapping')
        return value
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise UsageLedgerError(f'receipt completion pinned artifact unusable: {exc}') from exc


def remember_exchange(spec, req, response: str, usage_id: str) -> None:
    """Keep exact exchange after usage, before receipt parsing or re-addressing."""
    from data_sheets_schema import usage_ledger as ledger
    state = _state(spec)
    if state is not None:
        raise ledger.UsageLedgerError('cannot replace transcript after receipt completion intent')
    pin = _save(spec, TRANSCRIPT, {'phase': req.phase, 'system': req.system,
        'messages': req.messages, 'cached_blocks': req.cached_blocks,
        'response': response, 'usage_id': usage_id}, usage_id=usage_id)
    data = ledger._read(spec)
    data['receipt_completion_transcript'] = pin
    ledger._write(spec, data)


def _validate_record(inputs: dict) -> None:
    """Validate only captured bytes, including transitive imports."""
    import tempfile
    import yaml
    from data_sheets_schema import api_runner as api
    from data_sheets_schema.schema_snapshot import SchemaSnapshot
    from data_sheets_schema.schema_view import shared_view
    from linkml_runtime.dumpers import yaml_dumper
    # Use a fresh view copy: merge_imports mutates its receiver.
    rows = inputs['schema']['sources']
    sources = tuple((r['name'], Path(r['path']), r['text'].encode('utf-8')) for r in rows)
    snap = SchemaSnapshot(sources, (rows[0]['path'], sha(canonical(inputs['schema']))))
    view = copy.deepcopy(shared_view(rows[0]['path'], snapshot=snap))
    view.merge_imports()
    merged = yaml_dumper.dumps(view.schema)
    with tempfile.TemporaryDirectory(prefix='d4d-receipt-schema-') as folder:
        schema, record = Path(folder) / 'schema.yaml', Path(folder) / 'record.yaml'
        schema.write_text(merged, encoding='utf-8')
        record.write_text(inputs['record'], encoding='utf-8')
        findings, failure = api._validator_lines(record, str(schema), 'Dataset')
        if failure or findings is None or findings:
            raise ValueError(f'persisted full fails captured schema validation: {failure or findings}')


def _inputs(spec) -> dict:
    from data_sheets_schema import api_runner as api, chunking, usage_ledger as ledger
    data = ledger._read(spec)
    transcript_pin = data.get('receipt_completion_transcript')
    transcript = _load(transcript_pin)
    if transcript.get('phase') not in ('full', 'full_readdress'):
        raise ValueError('completion transcript is not a full/readdress exchange')
    if not any(r.get('usage_id') == transcript.get('usage_id') and r.get('phase') == transcript['phase']
               for r in data['rows']):
        raise ValueError('completion transcript has no matching accounted usage')
    reg = registration(spec)
    schema = schema_capture()
    result = {'record': spec.full_path.read_bytes().decode('utf-8'),
              'receipt': api._receipt_path(spec).read_bytes().decode('utf-8'),
              'manifest': Path(spec.chunk_manifest or chunking.manifest_for(spec.bundle, source_manifest=spec.manifest)).read_bytes().decode('utf-8'),
              'bundle': spec.bundle.read_bytes().decode('utf-8'), 'schema': schema,
              'transcript': transcript, 'transcript_pin': transcript_pin,
              'registration': registration_identity(spec), 'policy': policy_identity(),
              'input_identity': spec.input_identity(), 'max_output_tokens': reg['max_output_tokens']}
    expected_schema = {'sources': [{k: v for k, v in row.items() if k != 'text'}
                                  for row in schema['sources']]}
    if result['input_identity']['receipt_completion_schema'] != expected_schema:
        raise ledger.UsageLedgerError('schema changed during completion capture')
    sealed = data.get('receipt_completion_full') or {}
    if (sha(result['record'].encode()) != sealed.get('full_sha256')
            or sha(result['receipt'].encode()) != sealed.get('receipt_sha256')
            or transcript_pin != sealed.get('transcript')):
        raise ledger.UsageLedgerError('full/receipt/transcript differs from durable phase-1 boundary')
    _validate_record(result)
    return result


def _prepared(inputs):
    # The selected merged schema is large. Cache only immutable captured-input
    # parsing, with a fresh deep copy per consumer; never cache mutable paths or
    # an acceptance verdict. The offline Inputs contract remains unchanged.
    from data_sheets_schema.rereceipt import Inputs
    from functools import lru_cache
    global _INPUT_CLASS
    if _INPUT_CLASS is None:
        @lru_cache(maxsize=8)
        def parsed(value):
            return Inputs.parsed(value)
        class PinnedInputs(Inputs):
            def parsed(self):
                return copy.deepcopy(parsed(self))
        _INPUT_CLASS = PinnedInputs
    return _INPUT_CLASS(**{k: inputs[k].encode('utf-8') for k in ('record', 'receipt', 'manifest', 'bundle')},
                  schema=inputs['schema']['sources'][0]['text'].encode('utf-8'),
                  max_output_tokens=inputs['max_output_tokens'])


def build_request(inputs):
    from data_sheets_schema import api_runner as api
    prepared = _prepared(inputs)
    prior = inputs['transcript']
    # Explicit runtime identity: do not label this request as renderer 24.
    inventory = {'requested_paths': prepared.paths(), 'record_yaml': inputs['record'],
                 'receipt_yaml': inputs['receipt'], 'registration': inputs['registration'],
                 'input_sha256': {k: sha(inputs[k].encode()) for k in ('record', 'receipt', 'manifest', 'bundle')},
                 'schema': {k: v for k, v in inputs['schema'].items()},
                 'policy': inputs['policy']}
    req = api.PhaseRequest(phase=PHASE, system=prior['system'],
        cached_blocks=copy.deepcopy(prior['cached_blocks']),
        messages=copy.deepcopy(prior['messages']) + [
            {'role': 'assistant', 'content': prior['response']},
            {'role': 'user', 'content': [{'type': 'text', 'text': canonical(inventory).decode()},
                                        {'type': 'text', 'text': policy_text()}]}])
    return req, inventory


def request_payload(req, settings, reg) -> dict:
    """Logical provider body, including settings counted by the byte bound."""
    from data_sheets_schema import api_runner as api
    payload = {'model': settings['name'], 'system': req.system, 'messages': req.messages,
               'max_tokens': reg['max_output_tokens']}
    if settings['temperature'] is not None and api.accepts_temperature(settings['name']):
        payload['temperature'] = settings['temperature']
    if settings.get('thinking') is not None:
        payload['thinking'] = copy.deepcopy(settings['thinking'])
    if settings.get('effort') is not None:
        payload['output_config'] = {'effort': settings['effort']}
    return payload


def _context_check(value, payload, reg) -> None:
    from data_sheets_schema.usage_ledger import UsageLedgerError
    count = value.get('input_tokens') if isinstance(value, dict) else None
    if (type(count) is not int or count < 0 or value.get('request_sha256') != sha(canonical(payload))
            or value.get('method') != 'endpoint messages.count_tokens'
            or value.get('context_limit_tokens') != reg['context_limit_tokens']
            or value.get('context_limit_basis') != reg['context_limit_basis']
            or count + payload['max_tokens'] > reg['context_limit_tokens']):
        raise UsageLedgerError('receipt completion context count unavailable, unbound, or exceeds registered window')


def _count_context(client, payload, reg) -> dict:
    """Endpoint-reported count against a caller-asserted window; no generation."""
    from data_sheets_schema.usage_ledger import UsageLedgerError
    kwargs = {k: copy.deepcopy(payload[k]) for k in ('model', 'system', 'messages', 'thinking') if k in payload}
    if 'output_config' in payload:
        kwargs['extra_body'] = {'output_config': copy.deepcopy(payload['output_config'])}
    try:
        counter = getattr(client.messages, 'count_tokens', None)
        if not callable(counter):
            raise ValueError('route has no callable messages.count_tokens')
        response = counter(**kwargs)
        count = response.get('input_tokens') if isinstance(response, dict) else getattr(response, 'input_tokens', None)
    except Exception as exc:
        raise UsageLedgerError(f'receipt completion endpoint token count unavailable: {exc}') from exc
    value = {'input_tokens': count, 'method': 'endpoint messages.count_tokens',
             'request_sha256': sha(canonical(payload)), 'context_limit_tokens': reg['context_limit_tokens'],
             'context_limit_basis': reg['context_limit_basis'], 'capacity_authority': 'caller assertion'}
    _context_check(value, payload, reg)
    return value


def _recover_reasoning(spec, response, row, payload) -> None:
    from data_sheets_schema import api_runner as api, reasoning, usage_ledger as ledger
    entry = response.get('reasoning_entry')
    identity = {'phase': PHASE, 'label': spec.label, 'project': spec.project,
                'model': payload['model'], 'attempt': 1, **api._reasoning_usage(spec, row)}
    if not isinstance(entry, dict) or any(entry.get(k) != v for k, v in identity.items()):
        raise ledger.UsageLedgerError('receipt completion reasoning is not bound to its accounted response')
    try:
        rows = reasoning.read(api._reasoning_path(spec))
    except (OSError, ValueError) as exc:
        raise ledger.UsageLedgerError(f'receipt completion reasoning log unreadable: {exc}') from exc
    matched = [r for r in rows if r.get('usage_id') == response['usage_id']]
    if matched and matched != [entry]:
        raise ledger.UsageLedgerError('receipt completion reasoning log contradicts its captured response')
    if not matched:
        reasoning.append(api._reasoning_path(spec), entry)


def _receipt_publish(spec, inputs, result) -> None:
    import os
    import tempfile
    from data_sheets_schema import api_runner as api
    from data_sheets_schema.usage_ledger import UsageLedgerError
    path = api._receipt_path(spec)
    raw = path.read_bytes()
    if sha(spec.full_path.read_bytes()) != sha(inputs['record'].encode()):
        raise UsageLedgerError('full record changed before receipt completion publication')
    if sha(raw) == result['receipt_after_sha256']:
        return  # interrupted after publication; never re-merge
    if sha(raw) != sha(inputs['receipt'].encode()):
        raise UsageLedgerError('receipt completion cannot overwrite unexpected receipt drift')
    with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(result['receipt_yaml'].encode())
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _result(inputs, raw: bytes, *, truncated=False) -> dict:
    import yaml
    from data_sheets_schema.rereceipt import parse_answers, complete
    problem = 'response truncated' if truncated else None
    try:
        answers = [] if problem else parse_answers(raw)
    except (ValueError, TypeError, UnicodeError, yaml.YAMLError) as exc:
        answers, problem = [], f'unusable response: {exc}'
    value = complete(_prepared(inputs), answers)
    # Offline helper identity is internal accounting, not this runtime identity.
    value.pop('input_identity')
    value.pop('policy')
    value['schema_validation'] = 'captured schema and dependency closure validated before admission'
    value.update(policy=inputs['policy'], registration=inputs['registration'],
                 input_identity=inputs['input_identity'], semantic_support='not mechanically established')
    if problem:
        value['state'] = 'answers_incomplete'
        value['response_problem'] = problem
    value['receipt_yaml'] = yaml.safe_dump(value.pop('receipt'), sort_keys=False, allow_unicode=True, width=10000)
    value['receipt_after_sha256'] = sha(value['receipt_yaml'].encode())
    return value


def recover(spec, *, allow_unfinished=False) -> dict | None:
    """Recover only pinned outcomes; missing progress can never restart full."""
    from data_sheets_schema import usage_ledger as ledger
    state = _state(spec)
    if state is None:
        return None
    if not isinstance(state, dict) or state.get('state') not in ('intent', 'admitted', 'response', 'result', 'complete', 'failed'):
        raise ledger.UsageLedgerError('invalid receipt completion journal')
    inputs = _load(state['inputs'])
    if inputs['input_identity'] != spec.input_identity() or inputs['registration'] != registration_identity(spec):
        raise ledger.UsageLedgerError('receipt completion inputs/registration changed')
    _load(inputs['transcript_pin'])
    payload = _load(state['request'])
    req, inventory = build_request(inputs)
    reg = registration(spec)
    if (payload != request_payload(req, inputs['request_settings'], reg)
            or state['requested_paths'] != inventory['requested_paths']):
        raise ledger.UsageLedgerError('receipt completion request/inventory differs from captured inputs')
    if state['requested_paths']:
        _context_check(_load(state['context']), payload, reg)
    elif state.get('context') is not None:
        raise ledger.UsageLedgerError('no-work completion cannot claim a context measurement')
    if state['state'] in ('admitted', 'failed'):
        raise ledger.UsageLedgerError('receipt completion attempt lacks an accepted recoverable response; terminal')
    if state['state'] == 'intent':
        if not allow_unfinished:
            raise ledger.UsageLedgerError('receipt completion intent must finish before other calls')
        return None
    response = _load(state['response'])
    rows = ledger._read(spec)['rows']
    if response['stop_reason'] == 'no_work':
        if state['requested_paths'] or response['usage_id'] is not None:
            raise ledger.UsageLedgerError('invalid no-work receipt completion')
    else:
        matching = [r for r in rows if r.get('usage_id') == response['usage_id'] and r.get('phase') == PHASE]
        if len(matching) != 1:
            raise ledger.UsageLedgerError('completion response has no unique matching accounted usage')
        _recover_reasoning(spec, response, matching[0], payload)
    if state['state'] == 'response':
        result = _result(inputs, response['text'].encode(), truncated=response['stop_reason'] == 'max_tokens')
        state.update(state='result', result=_save(spec, 'receipt_completion_result.json', result,
                                                usage_id=response['usage_id']))
        _set_state(spec, state)
    result = _load(state['result'])
    # Recompute every result from fixed inputs + raw response; stored passed flags
    # and mutable receipt origin markers are not acceptance authority.
    expected = _result(inputs, response['text'].encode(), truncated=response['stop_reason'] == 'max_tokens')
    if result != expected:
        raise ledger.UsageLedgerError('receipt completion saved result differs from checked response')
    if state['state'] == 'result':
        _receipt_publish(spec, inputs, result)
        state['state'] = 'complete'
        _set_state(spec, state)
    from data_sheets_schema import api_runner as api
    if sha(api._receipt_path(spec).read_bytes()) != result['receipt_after_sha256']:
        raise ledger.UsageLedgerError('completed receipt completion output receipt changed')
    if result['state'] != 'answers_complete':
        raise ledger.UsageLedgerError('receipt completion is incomplete; full and verified partial additions preserved')
    return {**result, 'journal': copy.deepcopy(state), 'response_sha256': state['response']['sha256']}


def audit_carry(spec) -> str:
    outcome = recover(spec)
    if outcome is None:
        raise ValueError('audit requires completed receipt continuation')
    return AUDIT_HEADER + canonical({'input_identity': outcome['input_identity'],
        'registration': outcome['registration'], 'result_artifact': outcome['journal']['result'],
        'unsupported_audit_candidates': outcome['unsupported_audit_candidates'],
        'scientific_support': 'unverified; independent audit required, no deletion instruction'}).decode()


def run(spec, client, settings: dict, usage: list) -> dict:
    """Called after full progress publication, before any core/audit continuation."""
    import time
    from datetime import datetime, timezone
    from data_sheets_schema import api_runner as api, reasoning, usage_ledger as ledger
    reg = preflight(spec, settings)
    old = recover(spec, allow_unfinished=True)
    if old is not None:
        return old
    state = _state(spec)
    if state is None:
        inputs = _inputs(spec)
        inputs['request_settings'] = copy.deepcopy(settings)
        req, inventory = build_request(inputs)
        payload = request_payload(req, settings, reg)
        if inventory['requested_paths'] and len(canonical(payload)) > reg['max_request_bytes']:
            raise ledger.UsageLedgerError('complete receipt request exceeds registered byte limit; inventory not truncated')
        context = (_save(spec, 'receipt_completion_context.json', _count_context(client, payload, reg))
                   if inventory['requested_paths'] else None)
        state = {'state': 'intent', 'inputs': _save(spec, 'receipt_completion_inputs.json', inputs),
                 'request': _save(spec, 'receipt_completion_request.json', payload), 'context': context,
                 'requested_paths': inventory['requested_paths']}
        _set_state(spec, state)
    else:
        inputs = _load(state['inputs'])
        req, inventory = build_request(inputs)
        if _load(state['request']) != request_payload(req, settings, reg):
            raise ledger.UsageLedgerError('receipt completion request differs from saved intent')
    if sha(spec.full_path.read_bytes()) != sha(inputs['record'].encode()):
        raise ledger.UsageLedgerError('full record changed before receipt completion admission')
    if sha(api._receipt_path(spec).read_bytes()) != sha(inputs['receipt'].encode()):
        raise ledger.UsageLedgerError('receipt changed before receipt completion admission')
    if not state['requested_paths']:
        response = {'text': 'rereceipt: []\n', 'usage_id': None, 'stop_reason': 'no_work'}
    else:
        started, start = datetime.now(timezone.utc).isoformat(timespec='seconds'), time.monotonic()
        try:
            resp, call_id = api._call_with_usage(spec, PHASE, 1, started, client,
                model=settings['name'], thinking=settings.get('thinking'), effort=settings.get('effort'),
                max_tokens=reg['max_output_tokens'], temperature=settings['temperature'],
                system=req.system, messages=req.messages,
                on_incomplete=lambda info: api._record_incomplete_stream(spec, PHASE, 1, started,
                    info, usage, max_tokens=reg['max_output_tokens']))
        except ledger.UsageLedgerError:
            raise
        except Exception:
            state = _state(spec)
            state['state'] = 'failed'
            _set_state(spec, state)
            raise
        row = api._append_usage(spec, usage, {'usage_id': call_id, 'phase': PHASE, 'attempt': 1,
            'started_at': started, 'seconds': round(time.monotonic() - start, 3),
            'input_tokens': getattr(resp.usage, 'input_tokens', None),
            'output_tokens': getattr(resp.usage, 'output_tokens', None),
            'thinking_tokens': reasoning.thinking_tokens(resp),
            'cache_read': getattr(resp.usage, 'cache_read_input_tokens', None),
            'cache_write': getattr(resp.usage, 'cache_creation_input_tokens', None),
            'max_tokens': reg['max_output_tokens'], 'stop_reason': getattr(resp, 'stop_reason', None)})
        response = {'text': ''.join(b.text for b in resp.content if getattr(b, 'type', '') == 'text'),
                    'usage_id': call_id, 'stop_reason': getattr(resp, 'stop_reason', None),
                    'reasoning_entry': {'phase': PHASE, 'label': spec.label,
                        'project': spec.project, 'model': settings['name'], 'attempt': 1,
                        **api._reasoning_usage(spec, row), **reasoning.capture(resp).to_dict()}}
        # Preserve full delivered response before reasoning/parse/result side effects.
        state = _state(spec)
        state.update(state='response', response=_save(spec, 'receipt_completion_response.json', response, usage_id=call_id))
        _set_state(spec, state)
        return recover(spec)
    state.update(state='response', response=_save(spec, 'receipt_completion_response.json', response))
    _set_state(spec, state)
    return recover(spec)


def seal_full(spec) -> None:
    """Independent durable boundary: lost progress cannot repurchase full."""
    import os
    from data_sheets_schema import api_runner as api, usage_ledger as ledger
    data = ledger._read(spec)
    if data.get('receipt_completion_full') is not None:
        raise ledger.UsageLedgerError('receipt completion full boundary already sealed')
    transcript = _load(data.get('receipt_completion_transcript'))
    for path in (spec.full_path, api._receipt_path(spec)):
        with path.open('rb') as stream:
            os.fsync(stream.fileno())
    data['receipt_completion_full'] = {'full_sha256': sha(spec.full_path.read_bytes()),
        'receipt_sha256': sha(api._receipt_path(spec).read_bytes()),
        'transcript': copy.deepcopy(data['receipt_completion_transcript']),
        'usage_id': transcript['usage_id']}
    ledger._write(spec, data)


def resume_guard(spec, progress: dict) -> None:
    from data_sheets_schema import api_runner as api, usage_ledger as ledger
    if not ledger.ledger_path(spec).exists():
        return
    data = ledger._read(spec)
    if data.get('receipt_completion_full') is None and data.get('receipt_completion') is None:
        return
    state = _state(spec)
    if state is not None:
        recover(spec, allow_unfinished=True)
    completed = progress.get('completed', []) if isinstance(progress, dict) else []
    if 'full' not in completed:
        # A completed provenance record provides independent phase completion;
        # ordinary provenance/request revalidation still runs before return.
        try:
            import yaml
            prior = yaml.safe_load(spec.provenance_path.read_bytes())
            recorded = (prior.get('run') or {}).get('generation_id')
            if (recorded == data['generation_id'] and prior.get('receipt_completion')
                    and state and state.get('state') == 'complete'):
                return
        except (OSError, ValueError, AttributeError, yaml.YAMLError):
            pass
        raise ledger.UsageLedgerError('durable receipt completion full requires saved progress; generation cannot restart')
    if 'reconcile_full' not in completed and sha(spec.full_path.read_bytes()) != data['receipt_completion_full']['full_sha256']:
        raise ledger.UsageLedgerError('durable full changed before receipt completion/audit')
    if state is None and sha(api._receipt_path(spec).read_bytes()) != data['receipt_completion_full']['receipt_sha256']:
        raise ledger.UsageLedgerError('phase-1 receipt changed before completion intent')


def require_admission(spec, phase: str) -> None:
    from data_sheets_schema import usage_ledger as ledger
    if not getattr(spec, 'receipt_completion_version', 0):
        return
    data = ledger._read(spec)
    state = data.get('receipt_completion')
    sealed = data.get('receipt_completion_full')
    if state is not None and not sealed:
        raise ledger.UsageLedgerError('receipt completion journal lost its durable full boundary')
    if phase == PHASE:
        if not sealed or not isinstance(state, dict) or state.get('state') != 'intent':
            raise ledger.UsageLedgerError('receipt completion has no unused durable intent')
        if any(r.get('phase') == PHASE for r in data['rows']):
            raise ledger.UsageLedgerError('receipt completion allowance already consumed')
        recover(spec, allow_unfinished=True)
        return
    if sealed:
        if phase in ('full', 'full_readdress'):
            raise ledger.UsageLedgerError('durable full cannot restart after receipt completion boundary')
        if not state or state.get('state') != 'complete':
            raise ledger.UsageLedgerError('receipt completion must finish before downstream calls')
        recover(spec)


def require_audit_carry(spec, req) -> None:
    """Do not admit an audit if the complete bound candidate block was dropped."""
    from data_sheets_schema.usage_ledger import UsageLedgerError
    expected = audit_carry(spec)
    blocks = [p.get('text') for m in req.messages if isinstance(m.get('content'), list)
              for p in m['content'] if isinstance(p, dict)]
    if blocks.count(expected) != 1:
        raise UsageLedgerError('audit request omits or changes receipt completion candidate carry')
