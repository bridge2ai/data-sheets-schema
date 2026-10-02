"""Registered receipt completion: real local checks, synthetic fake delivery only."""
import builtins
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, receipt_completion as rc, usage_ledger as ledger, snapshot_store
from data_sheets_schema.cli import cli
from tests.test_download.test_api_runner import FakeClient, FakeMessages, FakeResponse
from tests.test_generation_manifest_identity import external  # noqa: F401

FULL = {'id': 'urn:loom', 'title': 'Thread archive', 'name': 'loom',
        'description': 'Shared synthetic observations', 'keywords': ['wool', 'silk']}


def raw(value):
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True)


def registration(condition='generic_v8', **changes):
    return json.dumps({'format': 'receipt_completion_registration_v1', 'registration_id': 'synthetic-test-only',
        'condition': condition, 'runtime_policy_sha256': rc.POLICY_SHA256, 'receipt_instrument_version': 4,
        'max_output_tokens': 2048, 'max_request_bytes': 2000000,
        'context_limit_tokens': 900000, 'context_limit_basis': 'synthetic caller assertion, not measured capacity',
        'coverage_floor': {'state': 'pending', 'mode': 'diagnostic_pilot'}, **changes})


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    monkeypatch.setattr(api, 'MAX_ATTEMPTS', 1)


@pytest.fixture
def selected(external):
    return replace(external, condition="generic_v8", receipt_completion_version=1, receipt_completion_registration=registration())


def receipt(spec, *, covered=False, bad_address=False):
    manifest = yaml.safe_load(spec.chunk_manifest.read_bytes())
    rows = [{'id': c['id'], 'status': 'nothing_relevant', 'reason': 'synthetic prior negative judgment'}
            for c in manifest['chunks']]
    if covered or bad_address:
        rows[0] = {'id': rows[0]['id'], 'status': 'extracted', 'extracted': [
            {'slot': p, 'snippet': 'Shared synthetic observations'}
            for p in (['missing.slot'] if bad_address else ['title', 'name', 'description', 'keywords'])]}
    return {'bundle_md5': hashlib.md5(spec.bundle.read_bytes()).hexdigest(), 'chunks': rows}


class Messages(FakeMessages):
    def __init__(self, spec, mode='unsupported', *, covered=False, bad_address=False):
        super().__init__()
        self.spec, self.mode, self.covered, self.bad_address = spec, mode, covered, bad_address
        self.completion_calls = []
        self.count_calls = []

    def count_tokens(self, **kw):
        self.count_calls.append(copy.deepcopy(kw))
        return SimpleNamespace(input_tokens=1000)

    def create(self, **kw):
        last = kw['messages'][-1]
        if isinstance(last['content'], list) and any(p.get('text') == rc.policy_text() for p in last['content']):
            self.calls.append(kw)
            self.completion_calls.append(kw)
            inventory = json.loads(last['content'][0]['text'])
            if self.mode == 'transport':
                raise RuntimeError('synthetic transport failure')
            answers = [{'path': p, 'unsupported': True, 'reason': f'Independent audit needed for {p}'}
                       for p in inventory['requested_paths']]
            if self.mode in ('receipted', 'partial'):
                answers[0] = {'path': inventory['requested_paths'][0], 'receipt':
                              {'chunk': 'c001', 'snippet': 'Shared synthetic observations'}}
            if self.mode == 'partial':
                answers = answers[:1]
            if self.mode == 'duplicate':
                answers.append(copy.deepcopy(answers[0]))
            if self.mode == 'outside':
                answers.append({'path': 'invented[99]', 'unsupported': True, 'reason': 'outside'})
            response = FakeResponse('rereceipt: [broken' if self.mode == 'malformed' else raw({'rereceipt': answers}))
            response.stop_reason = 'max_tokens' if self.mode == 'truncated' else 'end_turn'
            response.content.append(SimpleNamespace(type='thinking', thinking='Synthetic disclosed reasoning summary', signature='present'))
            return response
        blob = json.dumps(kw['messages'])
        if isinstance(last['content'], list) and any(api.PHASE_INSTRUCTIONS['full_readdress'] in p.get('text', '') for p in last['content']):
            return super().create(**kw)
        phase = next((ph for ph, instruction in api.PHASE_INSTRUCTIONS.items()
                      if instruction in ' '.join(p.get('text', '') for p in kw['messages'][0]['content'])), None)
        if phase == 'full':
            self.calls.append(kw)
            return FakeResponse(raw(FULL) + '\n' + api.RECEIPT_MARK + '\n' +
                                raw(receipt(self.spec, covered=self.covered, bad_address=self.bad_address)))
        if phase == 'reconcile_full':
            self.calls.append(kw)
            return FakeResponse(raw(FULL))
        return super().create(**kw)


def client(spec, mode='unsupported', **kwargs):
    c = FakeClient()
    c.messages = Messages(spec, mode, **kwargs)
    return c


@pytest.mark.parametrize('axis', [True, False, -1, 2, '1', None])
def test_axis_requires_exact_registered_int(external, axis):
    with pytest.raises(ValueError, match='receipt_completion_version'):
        replace(external, receipt_completion_version=axis)


@pytest.mark.parametrize('renderer,runtime', [(7, api.RUNTIME), (9, api.RUNTIME), (24, api.RUNTIME), (8, 'Claude Code')])
def test_only_explicit_api8_route(external, renderer, runtime):
    with pytest.raises(ValueError, match='renderer 8'):
        replace(external, receipt_completion_version=1, receipt_completion_registration=registration(),
                render_version=renderer, runtime=runtime)


def test_registration_is_required_and_cannot_be_silent_metadata(external):
    with pytest.raises(ValueError):
        replace(external, receipt_completion_version=1)
    with pytest.raises(ValueError):
        replace(external, receipt_completion_registration=registration())
    with pytest.raises(ValueError, match='condition'):
        replace(external, receipt_completion_version=1, receipt_completion_registration=registration('generic_v9'))


def test_legacy_render_replay_and_request_are_identical_without_new_module(external, monkeypatch):
    spec = external
    recorded, instruction = spec.render_spec(), spec.instruction
    request = api.build_phase(spec, 'full', carry={})
    real = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.startswith('data_sheets_schema.receipt_completion'):
            raise ImportError('new policy unavailable')
        return real(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded)
    replay = api.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)
    assert replay.instruction == instruction
    assert not any(k.startswith('receipt_completion') for k in recorded)
    assert api.build_phase(replace(spec, receipt_completion_version=0), 'full', carry={}) == request


def test_opt_in_identity_replay_and_combination_axes(selected):
    selected = replace(selected, api_playbook_version=1, removal_repair_version=1)
    recorded = selected.render_spec()
    assert recorded['receipt_completion_registration']['raw_json'] == registration()
    replay = api.RunSpec.from_render_spec(recorded, project=selected.project, method=selected.method, label=selected.label)
    assert replay.instruction == selected.instruction
    assert api.assembly_digest(8, receipt_completion_version=1) != api.assembly_digest(8)
    changed = copy.deepcopy(recorded)
    changed['receipt_completion_registration']['raw_json'] += ' '
    with pytest.raises(ValueError):
        api.RunSpec.from_render_spec(changed, project=selected.project, method=selected.method, label=selected.label)


def test_real_validation_complete_unsupported_outcome_reaches_actual_audit(selected):
    c = client(selected)
    result = api.execute(selected, client=c)
    assert len(c.messages.completion_calls) == 1
    stored = yaml.safe_load(selected.provenance_path.read_bytes())
    outcome = stored['receipt_completion']
    assert outcome['state'] == 'answers_complete' and outcome['counts']['unsupported'] > 0
    assert outcome['counts']['receipts_added'] == 0
    assert outcome['semantic_support'] == 'not mechanically established'
    assert outcome['before']['slots']['receiptable'] == outcome['after']['slots']['receiptable']
    assert [r['phase'] for r in result['usage']] == ['full', rc.PHASE, 'audit', 'reconcile_full', 'report']
    audit_request = next(k for k in c.messages.calls if any(p.get('text', '').startswith(rc.AUDIT_HEADER)
                         for p in k['messages'][0]['content']))
    text = '\n'.join(p.get('text', '') for p in audit_request['messages'][0]['content'])
    for row in outcome['unsupported_audit_candidates']:
        assert row['path'] in text and row['reason'] in text
    assert outcome['journal']['result']['sha256'] in text
    req = c.messages.completion_calls[0]
    transcript = rc._load(rc._load(outcome['journal']['inputs'])['transcript_pin'])
    assert req['messages'][:-2] == transcript['messages']
    assert req['messages'][-2] == {'role': 'assistant', 'content': transcript['response']}
    assert req['max_tokens'] == 2048
    assert yaml.safe_load(selected.full_path.read_bytes()) == FULL
    second = client(selected)
    api.execute(replace(selected), client=second)
    assert not second.messages.calls


@pytest.mark.parametrize('mode', ['partial', 'duplicate', 'outside', 'malformed', 'truncated', 'transport'])
def test_failed_or_incomplete_turn_preserves_full_and_never_regenerates(selected, mode):
    c = client(selected, mode)
    with pytest.raises((RuntimeError, ledger.UsageLedgerError)):
        api.execute(selected, client=c)
    full = selected.full_path.read_bytes()
    assert yaml.safe_load(full) == FULL
    assert 'full' in json.loads(api._progress_path(selected).read_bytes())['completed']
    assert not selected.core_path.exists()
    state = rc._state(selected)
    if mode == 'partial':
        result = rc._load(state['result'])
        assert result['counts']['receipts_added'] == 1
        assert result['counts']['unanswered'] > 0
        assert 'origin: rereceipt' in api._receipt_path(selected).read_text()
    second = client(selected)
    with pytest.raises((RuntimeError, ledger.UsageLedgerError)):
        api.execute(replace(selected), client=second)
    assert not second.messages.calls and selected.full_path.read_bytes() == full


def test_no_work_makes_no_completion_request(selected):
    selected = replace(selected, receipt_completion_registration=registration(max_request_bytes=1))
    c = client(selected, covered=True)
    c.messages.count_tokens = lambda **kw: pytest.fail('no-work cannot call the counter')
    create = c.messages.create
    def guarded_create(**kw):
        content = kw['messages'][-1]['content']
        if isinstance(content, list) and any(p.get('text') == rc.policy_text() for p in content):
            pytest.fail('no-work cannot call receipt completion')
        return create(**kw)
    c.messages.create = guarded_create
    api.execute(selected, client=c)
    out = rc.recover(selected)
    assert out['counts']['requested'] == 0 and out['state'] == 'answers_complete'
    assert not c.messages.completion_calls
    assert rc._load(out['journal']['response'])['stop_reason'] == 'no_work'
    assert out['journal']['context'] is None


@pytest.mark.parametrize('boundary', ['response', 'result', 'published'])
def test_crash_recovery_never_readmits_or_remerges(selected, monkeypatch, boundary):
    c = client(selected, 'receipted')
    if boundary == 'published':
        original = rc._receipt_publish
        def interrupt(*args):
            original(*args)
            raise KeyboardInterrupt('after receipt publication')
        monkeypatch.setattr(rc, '_receipt_publish', interrupt)
    else:
        original = rc._set_state
        def interrupt(spec, state):
            original(spec, state)
            if state['state'] == boundary:
                raise KeyboardInterrupt('after durable ' + boundary)
        monkeypatch.setattr(rc, '_set_state', interrupt)
    with pytest.raises(KeyboardInterrupt):
        api.execute(selected, client=c)
    assert len(c.messages.completion_calls) == 1
    full = selected.full_path.read_bytes()
    monkeypatch.setattr(rc, '_receipt_publish' if boundary == 'published' else '_set_state', original)
    second = client(selected)
    api.execute(replace(selected), client=second)
    assert not second.messages.completion_calls
    assert not any(api.PHASE_INSTRUCTIONS['full'] in json.dumps(k) for k in second.messages.calls)
    out = rc.recover(selected)
    assert out['counts']['receipts_added'] == 1
    assert selected.full_path.read_bytes() == full or yaml.safe_load(selected.full_path.read_bytes()) == yaml.safe_load(full)


@pytest.mark.parametrize('progress', ['missing', 'corrupt', 'partial'])
def test_lost_progress_after_admission_refuses_all_generation(selected, monkeypatch, progress):
    original = rc._set_state
    def interrupt(spec, state):
        original(spec, state)
        if state['state'] == 'complete':
            raise KeyboardInterrupt('after completion')
    monkeypatch.setattr(rc, '_set_state', interrupt)
    with pytest.raises(KeyboardInterrupt):
        api.execute(selected, client=client(selected))
    p = api._progress_path(selected)
    if progress == 'missing': p.unlink()
    elif progress == 'corrupt': p.write_text('{broken')
    else: p.write_text(json.dumps({'completed': []}))
    monkeypatch.setattr(rc, '_set_state', original)
    second = client(selected)
    with pytest.raises((ValueError, ledger.UsageLedgerError)):
        api.execute(replace(selected), client=second)
    assert not second.messages.calls


@pytest.mark.parametrize('drift', ['full', 'receipt', 'transcript', 'schema', 'registration'])
def test_mutated_inputs_after_intent_do_not_buy_a_call(selected, monkeypatch, drift):
    original = rc._set_state
    def interrupt(spec, state):
        original(spec, state)
        if state['state'] == 'intent': raise KeyboardInterrupt('intent')
    monkeypatch.setattr(rc, '_set_state', interrupt)
    with pytest.raises(KeyboardInterrupt):
        api.execute(selected, client=client(selected))
    monkeypatch.setattr(rc, '_set_state', original)
    changed = replace(selected)
    if drift in ('full', 'receipt'):
        p = selected.full_path if drift == 'full' else api._receipt_path(selected)
        p.write_bytes(p.read_bytes() + b'\n# external drift\n')
    elif drift == 'transcript':
        p = Path(rc._load(rc._state(selected)['inputs'])['transcript_pin']['path'])
        p.write_bytes(p.read_bytes() + b' ')
    elif drift == 'schema':
        real = rc.schema_identity
        monkeypatch.setattr(rc, 'schema_identity', lambda: {**real(), 'drift': True})
    else:
        changed = replace(selected, receipt_completion_registration=registration() + ' ')
    second = client(changed)
    with pytest.raises((ValueError, ledger.UsageLedgerError)):
        api.execute(changed, client=second)
    assert not second.messages.calls


def test_cap_refusal_is_before_any_model_call(selected):
    spec = replace(selected, receipt_completion_registration=registration(max_output_tokens=99999999, context_limit_tokens=999999999))
    c = client(spec)
    with pytest.raises(ValueError, match='cannot clamp'):
        api.execute(spec, client=c)
    assert not c.messages.calls


def test_request_bound_preserves_whole_full_without_call(selected):
    spec = replace(selected, receipt_completion_registration=registration(max_request_bytes=1))
    c = client(spec)
    with pytest.raises(ledger.UsageLedgerError, match='byte limit'):
        api.execute(spec, client=c)
    assert len(c.messages.calls) == 1 and yaml.safe_load(spec.full_path.read_bytes()) == FULL
    second = client(spec)
    with pytest.raises(ledger.UsageLedgerError, match='byte limit'):
        api.execute(replace(spec), client=second)
    assert not second.messages.calls


def test_actual_readdress_exchange_is_preserved_for_completion(selected):
    c = client(selected, bad_address=True)
    api.execute(selected, client=c)
    outcome = rc.recover(selected)
    transcript = rc._load(rc._load(outcome['journal']['inputs'])['transcript_pin'])
    assert transcript['phase'] == 'full_readdress'
    assert transcript['response'] == 'readdress: []\n'
    actual = c.messages.completion_calls[0]['messages']
    assert actual[:-2] == transcript['messages']
    assert [r['phase'] for r in ledger.merge_usage(selected, [])][:3] == ['full', 'full_readdress', rc.PHASE]


def test_cli_plan_selects_exact_registration_and_does_not_run(selected, tmp_path):
    path = tmp_path / 'registration.json'
    path.write_text(registration())
    args = ['api', 'plan', '--project', selected.project, '--label', 'synthetic',
            '--bundle', str(selected.bundle), '--manifest', str(selected.manifest),
            '--chunk-manifest', str(selected.chunk_manifest), '--condition', selected.condition,
            '--receipt-completion-version', '1', '--receipt-completion-registration', str(path), '--json']
    out = CliRunner().invoke(cli, args)
    assert out.exit_code == 0, out.output
    plan = json.loads(out.output)
    assert plan['receipt_completion_version'] == 1
    assert plan['receipt_completion_registration']['raw_json'] == path.read_text()
    assert any(t.startswith(rc.PHASE + ':') for t in plan['conditional_calls'])
    assert not selected.full_path.exists()


@pytest.mark.parametrize('bypass', [False, True])
def test_pending_floor_blocks_cli_batch_fanout_before_spend(selected, tmp_path, bypass):
    path = tmp_path / 'registration.json'
    path.write_text(registration())
    args = ['api', 'batch', '--projects', selected.project, '--project-bundle', f'{selected.project}={selected.bundle}',
            '--manifest', str(selected.manifest), '--condition', selected.condition, '--replicates', '2',
            '--label-prefix', 'synthetic', '--receipt-completion-version', '1',
            '--receipt-completion-registration', str(path), '--yes']
    if bypass: args.append('--no-canary-gate')
    out = CliRunner().invoke(cli, args)
    assert out.exit_code != 0
    assert ('cannot bypass' if bypass else 'fan-out is blocked') in out.output
    assert not selected.full_path.exists()


def test_saved_schema_validation_failure_stops_after_durable_full(selected, monkeypatch):
    original = api._validator_lines
    calls = []
    def fail_record(path, schema, cls):
        if Path(path).name == 'record.yaml':
            calls.append((path, schema, cls))
            return ['synthetic declared-type violation'], None
        return original(path, schema, cls)
    monkeypatch.setattr(api, '_validator_lines', fail_record)
    c = client(selected)
    with pytest.raises(ValueError, match='captured schema validation'):
        api.execute(selected, client=c)
    assert calls and len(c.messages.calls) == 1
    full = selected.full_path.read_bytes()
    second = client(selected)
    with pytest.raises(ValueError, match='captured schema validation'):
        api.execute(replace(selected), client=second)
    assert not second.messages.calls and selected.full_path.read_bytes() == full


@pytest.mark.parametrize('mode', ['drop', 'shorten', 'duplicate'])
def test_altered_actual_audit_candidate_carry_is_refused(selected, monkeypatch, mode):
    build = api.build_phase
    def mutate(spec, phase, **kwargs):
        req = build(spec, phase, **kwargs)
        if phase == 'audit':
            parts = req.messages[0]['content']
            block = next(b for b in parts if b.get('text', '').startswith(rc.AUDIT_HEADER))
            if mode == 'drop': parts.remove(block)
            elif mode == 'duplicate': parts.append(copy.deepcopy(block))
            else: block['text'] = block['text'][:100]
        return req
    monkeypatch.setattr(api, 'build_phase', mutate)
    c = client(selected)
    with pytest.raises(ledger.UsageLedgerError, match='candidate carry'):
        api.execute(selected, client=c)
    assert [r['phase'] for r in ledger.merge_usage(selected, [])] == ['full', rc.PHASE]


def test_full_mutation_during_response_cannot_hide_behind_unchanged_receipt(selected, monkeypatch):
    c = client(selected)
    create = c.messages.create
    def mutate(**kwargs):
        out = create(**kwargs)
        if c.messages.completion_calls:
            selected.full_path.write_bytes(selected.full_path.read_bytes() + b'\n# external drift\n')
        return out
    monkeypatch.setattr(c.messages, 'create', mutate)
    with pytest.raises(ledger.UsageLedgerError, match='full record changed'):
        api.execute(selected, client=c)
    assert len(c.messages.completion_calls) == 1
    assert not selected.core_path.exists()


def test_counter_uses_complete_logical_request_and_pins_its_measurement(selected):
    c = client(selected)
    api.execute(selected, client=c)
    out = rc.recover(selected)
    payload = rc._load(out['journal']['request'])
    count = rc._load(out['journal']['context'])
    assert len(c.messages.count_calls) == 1
    actual = c.messages.count_calls[0]
    import inspect
    from anthropic.resources.messages import Messages as SDKMessages
    inspect.signature(SDKMessages.count_tokens).bind(None, **actual)
    assert {k: actual[k] for k in ('model', 'system', 'messages')} == {k: payload[k] for k in ('model', 'system', 'messages')}
    if 'thinking' in payload:
        assert actual['thinking'] == payload['thinking']
    if 'output_config' in payload:
        assert actual['extra_body']['output_config'] == payload['output_config']
    assert count['request_sha256'] == rc.sha(rc.canonical(payload))
    assert count['input_tokens'] == 1000 and count['capacity_authority'] == 'caller assertion'


@pytest.mark.parametrize('count', [True, -1, None, '100', 1.5, 898000])
def test_unusable_or_over_window_count_preserves_full_without_admission(selected, count):
    c = client(selected)
    c.messages.count_tokens = lambda **kw: SimpleNamespace(input_tokens=count)
    with pytest.raises(ledger.UsageLedgerError, match='context count'):
        api.execute(selected, client=c)
    assert yaml.safe_load(selected.full_path.read_bytes()) == FULL
    assert not selected.core_path.exists() and not c.messages.completion_calls
    assert not any(r['phase'] == rc.PHASE for r in ledger.merge_usage(selected, []))
    assert rc._state(selected) is None


@pytest.mark.parametrize('mode', ['absent', 'exception'])
def test_unavailable_counter_does_not_admit_generation(selected, mode):
    c = client(selected)
    def fail(**kw): raise RuntimeError('route count unavailable')
    c.messages.count_tokens = None if mode == 'absent' else fail
    with pytest.raises(ledger.UsageLedgerError, match='token count unavailable'):
        api.execute(selected, client=c)
    assert not c.messages.completion_calls and selected.full_path.exists()


def test_saved_intent_reuses_bound_count_without_new_counter_call(selected, monkeypatch):
    original = rc._set_state
    def stop(spec, state):
        original(spec, state)
        if state['state'] == 'intent': raise KeyboardInterrupt('count and intent durable')
    monkeypatch.setattr(rc, '_set_state', stop)
    first = client(selected)
    with pytest.raises(KeyboardInterrupt): api.execute(selected, client=first)
    assert len(first.messages.count_calls) == 1 and not first.messages.completion_calls
    monkeypatch.setattr(rc, '_set_state', original)
    second = client(selected)
    second.messages.count_tokens = lambda **kw: pytest.fail('cannot recount a saved admitted request')
    api.execute(replace(selected), client=second)
    assert len(second.messages.completion_calls) == 1


@pytest.mark.parametrize('boundary', ['before_append', 'after_append'])
def test_reasoning_envelope_recovers_exactly_once_after_interruption(selected, monkeypatch, boundary):
    from data_sheets_schema import reasoning
    original = reasoning.append
    def stop(path, entry):
        if entry['phase'] == rc.PHASE:
            if boundary == 'after_append': original(path, entry)
            raise KeyboardInterrupt('reasoning boundary')
        original(path, entry)
    monkeypatch.setattr(reasoning, 'append', stop)
    first = client(selected)
    with pytest.raises(KeyboardInterrupt): api.execute(selected, client=first)
    state = rc._state(selected)
    response = rc._load(state['response'])
    assert response['reasoning_entry']['blocks'][0]['thinking'] == 'Synthetic disclosed reasoning summary'
    monkeypatch.setattr(reasoning, 'append', original)
    second = client(selected)
    api.execute(replace(selected), client=second)
    assert not second.messages.completion_calls and not second.messages.count_calls
    entries = [e for e in reasoning.read(api._reasoning_path(selected)) if e['phase'] == rc.PHASE]
    assert entries == [response['reasoning_entry']]


@pytest.mark.parametrize('artifact', ['request', 'context'])
def test_complete_recovery_rejects_request_or_count_snapshot_drift(selected, artifact):
    c = client(selected)
    api.execute(selected, client=c)
    pin = rc._state(selected)[artifact]
    path = Path(pin['path'])
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ledger.UsageLedgerError, match='pinned artifact'):
        rc.recover(selected)
    second = client(selected)
    with pytest.raises(ledger.UsageLedgerError): api.execute(replace(selected), client=second)
    assert not second.messages.calls


def test_all_three_opt_in_axes_execute_and_replay_without_extra_generation(selected):
    spec = replace(selected, api_playbook_version=1, removal_repair_version=1)
    c = client(spec)
    result = api.execute(spec, client=c)
    assert len(c.messages.completion_calls) == 1
    assert result['checks']['removal_repair']['findings'] == []
    recorded = yaml.safe_load(spec.provenance_path.read_bytes())
    replay = api.RunSpec.from_render_spec(recorded['prompts']['request']['spec'],
                                         project=spec.project, method=spec.method, label=spec.label)
    assert replay.render_spec() == spec.render_spec()
    assert replay.receipt_completion_version == replay.api_playbook_version == replay.removal_repair_version == 1
    second = client(spec)
    api.execute(replace(spec), client=second)
    assert not second.messages.calls


def test_lost_progress_immediately_after_full_seal_cannot_regenerate(selected, monkeypatch):
    original = rc.seal_full
    def stop(spec):
        original(spec)
        raise KeyboardInterrupt('full durable but progress not published')
    monkeypatch.setattr(rc, 'seal_full', stop)
    first = client(selected)
    with pytest.raises(KeyboardInterrupt): api.execute(selected, client=first)
    assert selected.full_path.exists() and rc._state(selected) is None
    monkeypatch.setattr(rc, 'seal_full', original)
    second = client(selected)
    with pytest.raises(ledger.UsageLedgerError, match='generation cannot restart'):
        api.execute(replace(selected), client=second)
    assert not second.messages.calls and not second.messages.count_calls


def test_unknown_completion_usage_never_readmits_or_restarts_full(selected, monkeypatch):
    original = api._append_usage
    def fail(spec, usage, row):
        if row['phase'] == rc.PHASE: raise ledger.UsageLedgerError('simulated unknown usage')
        return original(spec, usage, row)
    monkeypatch.setattr(api, '_append_usage', fail)
    first = client(selected)
    with pytest.raises(ledger.UsageLedgerError): api.execute(selected, client=first)
    assert len(first.messages.completion_calls) == 1 and selected.full_path.exists()
    monkeypatch.setattr(api, '_append_usage', original)
    second = client(selected)
    with pytest.raises(ledger.UsageLedgerError): api.execute(replace(selected), client=second)
    assert not second.messages.calls and not second.messages.count_calls


def test_saved_reasoning_conflict_is_not_silently_overwritten(selected):
    from data_sheets_schema import reasoning
    api.execute(selected, client=client(selected))
    path = api._reasoning_path(selected)
    entries = reasoning.read(path)
    next(e for e in entries if e['phase'] == rc.PHASE)['blocks'][0]['thinking'] = 'changed'
    path.write_text(''.join(json.dumps(e) + '\n' for e in entries))
    with pytest.raises(ledger.UsageLedgerError, match='contradicts'):
        rc.recover(selected)


def test_context_equality_passes_and_route_named_limit_cannot_be_inflated(selected):
    payload = {'model': 'synthetic', 'max_tokens': 2048, 'system': 's', 'messages': []}
    reg = json.loads(registration(context_limit_tokens=3048))
    c = client(selected)
    measured = rc._count_context(c, payload, reg)
    assert measured['input_tokens'] + payload['max_tokens'] == reg['context_limit_tokens']
    spec = replace(selected, receipt_completion_registration=registration(context_limit_tokens=1000001))
    with pytest.raises(ValueError, match='explicitly named route'):
        rc.preflight(spec, {'name': 'claude-opus-5[1m]'})


def test_selected_runtime_uses_existing_exclusive_output_lock(selected):
    c = client(selected)
    with ledger.exclusive_run(selected):
        with pytest.raises(ledger.UsageLedgerError, match='already active'):
            api.execute(selected, client=c)
    assert not c.messages.calls and not c.messages.count_calls
    assert not ledger.ledger_path(selected).exists()


@pytest.mark.parametrize('terminal', ['evidence', 'source_review', 'accepted_restoration'])
@pytest.mark.parametrize('phase', ['full', rc.PHASE])
def test_new_axis_does_not_reopen_terminal_generation_admission(selected, terminal, phase):
    ledger.prepare_usage(selected, resume=True)
    data = ledger._read(selected)
    if terminal == 'evidence':
        data['evidence_refusal'] = {'stage': 'audit', 'reading': {'checked': True, 'findings': ['refused']}}
    elif terminal == 'source_review':
        data['rows'] = [{'usage_id': 'review', 'phase': 'audit', 'source_review_admission': {'state': 'pending'}}]
    else:
        data['rows'] = [{'usage_id': 'repair', 'phase': 'removal_repair_full'}]
        data['removal_repair_attempted'] = True
        data['removal_repair_admission'] = {'state': 'accepted', 'usage_id': 'repair',
                                          'response_sha256': 'a' * 64, 'report_refresh': 'complete'}
    ledger._write(selected, data)
    with pytest.raises(ledger.UsageLedgerError, match='evidence refusal|source-review admission|after removal repair'):
        ledger.begin_call(selected, phase, 1, 'synthetic')
    assert ledger._read(selected) == data
