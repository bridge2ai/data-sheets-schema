"""Offline BC1 controller tests with explicit invented capture/receipt preconditions.

These exercise the real call/admission journal, snapshots, codec and independent
assembly. They do not simulate installing the protected registration hook or
claim a registered end-to-end generation. No provider or scientific labels.
"""
from copy import deepcopy
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner as api, bc1_audit as audit, bc1_codec as codec
from data_sheets_schema import bc1_context, bc1_runtime as runtime, bc1_selection
from data_sheets_schema import receipt_completion as receipts, shared_generation as shared
from data_sheets_schema import snapshot_store, typed_audit as typed, typed_audit_runtime as legacy
from data_sheets_schema import usage_ledger as ledger
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_bc1_audit import supplied, deliveries, stage_delta  # noqa: F401
from tests.test_download.test_api_runner import FakeResponse
from tests.test_evidence_generation_gate import specification


@pytest.fixture
def case(tmp_path, supplied, monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    spec = specification(tmp_path)
    spec.bounded_carry_version = 1
    spec.shared_generation_version = 1
    monkeypatch.setattr(bc1_selection, 'validate_spec_mode', lambda selected: None)
    reg = deepcopy(supplied['selection'])
    files = {}
    for name, source in (('bundle', 'bundle'), ('chunk_manifest', 'manifest'), ('context', 'context')):
        path = tmp_path / ('captured-' + name)
        path.write_bytes(supplied[source])
        files[str(path)] = supplied[source]
        reg['inputs'][name] = shared.file_pin(path)
    reg['inputs']['source_manifest'] = None
    core_path = tmp_path / 'captured-core-schema.yaml'
    core_path.write_text("""id: https://example.test/bc1-core
name: bc1_core
prefixes: {linkml: 'https://w3id.org/linkml/'}
imports: [linkml:types]
default_range: string
classes:
  CoreDataset:
    description: Complete invented core semantics retained in every request.
    attributes:
      name: {}
      description: {}
      title: {}
""")
    core_schema = capture_schema(core_path, strict=True)
    reg['inputs']['core_schema'] = bc1_context._schema_pin(core_schema)
    reg['selection'] = {'protocol': 'shared_generation_v1'}
    reg['audit_limits'] = {'max_paths': 1, 'max_inventory_bytes': 16_384, 'max_workers': 32,
        'max_request_bytes': 32_000_000, 'max_calls': 66, 'max_input_tokens_per_call': 850_000,
        'worker_output_tokens': 4000, 'omission_output_tokens': 4000, 'integration_output_tokens': 4000,
        'aggregate_input_tokens': 4_000_000, 'aggregate_output_tokens': 264_000,
        'context_limit_tokens': 900_000, 'context_limit_basis': 'Invented test ceiling.'}
    captured = SimpleNamespace(registration=shared.canonical(reg), full_schema=supplied['schema_snapshot'], core_schema=core_schema,
        document=lambda: deepcopy(reg), raw=lambda path: files[path], identity=lambda: {'fixture': 'captured'})
    identity = {'fixture': 'captured-BC1-controller-preconditions',
        'bundle': deepcopy(reg['inputs']['bundle']),
        'chunks': deepcopy(reg['inputs']['chunk_manifest']), 'source_manifest': None,
        'instruction': {'sha256': shared.sha(b'Explicit invented BC1 controller test instruction')},
        'captured_registration_sha256': shared.sha(captured.registration)}
    monkeypatch.setattr(spec, 'input_identity', lambda: deepcopy(identity))
    monkeypatch.setattr(shared, 'assert_current', lambda selected: captured)
    monkeypatch.setattr(shared, 'capture', lambda selected: captured)
    monkeypatch.setattr(shared, 'preflight', lambda selected, settings: captured)
    monkeypatch.setattr(shared, 'identity', lambda selected: captured.identity())
    outcome = {'input_identity': {'bundle': {'sha256': shared.sha(supplied['bundle'])},
                                 'unknown_source_fact': ['preserve', False]},
        'registration': {'sha256': shared.sha(b'{"budget":1}'), 'raw_json': '{"budget":1}'},
        'journal': {'result': {'path': 'fixture-receipt-result', 'sha256': 'a' * 64}},
        'unsupported_audit_candidates': [{'path': '/title', 'reason': 'Explicit unknown support.'}]}
    monkeypatch.setattr(receipts, 'recover', lambda selected: deepcopy(outcome))
    ledger.prepare_usage(spec, resume=False)
    full = supplied['original_full']
    api._snapshot(spec, f'{spec.project}_full.yaml', full.decode())
    api._snapshot(spec, f'{spec.project}_core.yaml', full.decode())
    receipt = api._receipt_path(spec)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_bytes(supplied['receipt'])
    packet = runtime.prepare_packet(spec)
    workers, omission, quote = deliveries(packet, omission_count=1)
    settings = {'name': 'claude-sonnet-4-20250514', 'temperature': 0, 'thinking': None, 'effort': None}
    carry = {'Original full record': full.decode(), 'Original core record': full.decode()}
    return SimpleNamespace(spec=spec, packet=packet, workers=workers, omission=omission, quote=quote,
        settings=settings, carry=carry, captured=captured, reg=reg, receipt_outcome=outcome)


class Messages:
    def __init__(self, case, *, fail_before=None, oversize=False, bad_count=None):
        self.case, self.calls, self.counts = case, [], []
        self.fail_before, self.oversize, self.bad_count = fail_before, oversize, bad_count

    def count_tokens(self, **kwargs):
        self.counts.append(deepcopy(kwargs))
        return SimpleNamespace(input_tokens=1000 if self.bad_count is None else self.bad_count)

    def create(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        blocks = [part['text'] for part in kwargs['messages'][0]['content']]
        inner = json.loads(next(text for text in blocks if text.startswith('# Exact BC1 stage request\n\n')).split('\n\n', 1)[1])
        if self.fail_before == len(self.calls):
            raise KeyboardInterrupt('invented admitted interruption')
        if self.oversize:
            raw = b' ' * (codec.WORKER_BYTES + 1)
        elif inner.get('kind') == 'bc1_worker_request_v1':
            saved = json.loads(self.case.workers[inner['payload']['worker_id']])
            raw = typed._unblob(saved['response'])
        elif inner.get('kind') == 'bc1_stage_request_v1':
            state = audit.start(self.case.packet, self.case.workers, self.case.omission)
            delta = stage_delta(self.case.packet, inner, quote=self.case.quote,
                                omissions=state['omission_check']['declared_candidates'])
            raw = codec.encode_candidate(delta, dictionary=self.case.packet['dictionary'], max_bytes=codec.INTEGRATION_BYTES)
        else:
            raw = self.case.omission
        response = FakeResponse(raw.decode('utf-8'))
        response.stop_reason = 'end_turn'
        return response


def client(messages):
    value = SimpleNamespace(messages=messages, max_retries=0, base_url='https://example.invalid')
    value.with_options = lambda **options: value
    return value


def run(case, messages):
    return legacy.run(case.spec, carry=case.carry, client=client(messages), settings=case.settings, usage=[])


def publish(case, outcome):
    state = runtime._state(case.spec)
    api._snapshot(case.spec, f'{case.spec.project}_audit.json', outcome.audit,
                  usage_id=state['stages'][-1]['usage_id'])


def evidence(case):
    return {str(path): path.read_bytes() for path in case.spec.metadata_dir.rglob('*') if path.is_file()}


def test_complete_fixed_roster_and_verified_model_projection(case):
    messages = Messages(case)
    outcome = run(case, messages)
    expected = runtime.roster(case.packet)
    assert len(messages.calls) == len(messages.counts) == len(expected)
    state = runtime._state(case.spec)
    assert state['state'] == 'accepted'
    assert [row['selection'] for row in state['stages']] == expected
    assert [row['phase'] for row in ledger._read(case.spec)['rows']] == [s['phase'] for s in expected]
    assert len({r['usage_id'] for r in state['stages']}) == len(expected)
    publish(case, outcome)
    checked = legacy.completion_check(case.spec, {'Audit findings': outcome.audit})
    assert checked['acceptance']['passed'] and checked['acceptance']['independently_reconstructed']
    encoded = runtime.model_carry(case.spec, outcome.audit)
    decoded = codec.decode_candidate(encoded.encode(), dictionary=codec.build_dictionary(chunks={}), max_bytes=codec.CARRY_BYTES)
    assert decoded == audit.project(receipts._load(state['assembly']))
    before = evidence(case)
    replay = Messages(case)
    assert run(case, replay).audit == outcome.audit
    assert not replay.calls and not replay.counts and evidence(case) == before
    with pytest.raises(ledger.UsageLedgerError, match='complete checked BC1 audit'):
        runtime.model_carry(case.spec, outcome.audit + ' ')


def test_saved_delivery_resumes_without_buying_that_stage_again(case, monkeypatch):
    original = api._append_usage
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt('after complete raw snapshot before accounting')
    monkeypatch.setattr(api, '_append_usage', interrupted)
    first = Messages(case)
    with pytest.raises(KeyboardInterrupt, match='after complete raw'):
        run(case, first)
    state = runtime._state(case.spec)
    assert len(first.calls) == 1 and state['stages'][0]['state'] == 'response_saved'
    saved_id = state['stages'][0]['usage_id']
    monkeypatch.setattr(api, '_append_usage', original)
    legacy.recover_delivered(case.spec)
    second = Messages(case)
    run(case, second)
    assert len(second.calls) == len(runtime.roster(case.packet)) - 1
    assert [r['usage_id'] for r in ledger._read(case.spec)['rows']].count(saved_id) == 1


def test_admitted_missing_delivery_is_terminal_and_never_repurchased(case):
    first = Messages(case, fail_before=1)
    with pytest.raises(KeyboardInterrupt, match='admitted interruption'):
        run(case, first)
    before = evidence(case)
    again = Messages(case)
    with pytest.raises(ledger.UsageLedgerError, match='failed terminally'):
        run(case, again)
    assert len(first.calls) == 1 and not again.calls and not again.counts
    assert before == evidence(case)


def test_oversize_raw_response_and_real_charge_survive_terminal_refusal(case):
    first = Messages(case, oversize=True)
    with pytest.raises(ValueError):
        run(case, first)
    state = runtime._state(case.spec)
    assert state['state'] == 'failed'
    response = receipts._load(state['stages'][0]['response'])
    assert len(response['text'].encode()) == codec.WORKER_BYTES + 1
    assert len(ledger._read(case.spec)['rows']) == 1
    again = Messages(case)
    with pytest.raises(ledger.UsageLedgerError):
        run(case, again)
    assert not again.calls and not again.counts


@pytest.mark.parametrize('bad_count', [0, True, 900001])
def test_invalid_or_oversize_count_is_saved_and_refuses_without_generation(case, bad_count):
    first = Messages(case, bad_count=bad_count)
    with pytest.raises(ledger.UsageLedgerError):
        run(case, first)
    state = runtime._state(case.spec)
    assert state['state'] == 'failed' and not first.calls and len(first.counts) == 1
    assert receipts._load(state['stages'][0]['context'])['input_tokens'] == bad_count
    again = Messages(case)
    with pytest.raises(ledger.UsageLedgerError):
        run(case, again)
    assert not again.calls and not again.counts


@pytest.mark.parametrize('mutation', ['delete_ledger', 'delete_state', 'erase_row', 'rewind_state', 'response_bytes', 'response_pin'])
def test_saved_state_or_response_mutation_refuses_without_another_call(case, monkeypatch, mutation):
    original = api._append_usage
    monkeypatch.setattr(api, '_append_usage', lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        run(case, Messages(case))
    monkeypatch.setattr(api, '_append_usage', original)
    account = ledger.ledger_path(case.spec)
    data = json.loads(account.read_bytes())
    row = data['typed_audit']['stages'][0]
    if mutation == 'delete_ledger':
        pass
    elif mutation == 'delete_state':
        del data['typed_audit']
    elif mutation == 'erase_row':
        data['typed_audit']['stages'] = []
    elif mutation == 'rewind_state':
        row['state'] = 'prepared'
    else:
        Path(row['response']['path']).write_text('{"changed":true}')
        if mutation == 'response_pin':
            row['response']['sha256'] = shared.sha(Path(row['response']['path']).read_bytes())
    if mutation == 'delete_ledger':
        account.unlink()
    else:
        account.write_bytes(shared.canonical(data))
    before = evidence(case)
    with pytest.raises(ledger.UsageLedgerError):
        legacy.recover_delivered(case.spec)
    again = Messages(case)
    with pytest.raises(ledger.UsageLedgerError):
        run(case, again)
    assert not again.calls and not again.counts and evidence(case) == before


def test_receipt_projection_preserves_all_candidates_and_unknown_source_metadata(case):
    original = deepcopy(case.receipt_outcome)
    value = json.loads(receipts.bc1_audit_carry(original).split('\n\n', 1)[1])
    assert value['input_identity'] == original['input_identity']
    assert value['unsupported_audit_candidates'] == original['unsupported_audit_candidates']
    assert value['registration'] == {'sha256': shared.sha(b'{"budget":1}'), 'raw_json_bytes': 12}
    assert original == case.receipt_outcome


def test_off_mode_receipt_carry_remains_exact_legacy_bytes(case):
    case.spec.bounded_carry_version = 0
    assert receipts.audit_carry(case.spec) == receipts._audit_carry(case.receipt_outcome)


def test_unbilled_prepared_stage_erasure_is_detected_by_immutable_controller(case, monkeypatch):
    monkeypatch.setattr(api, '_call_with_usage', lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
    first = Messages(case)
    with pytest.raises(KeyboardInterrupt):
        run(case, first)
    assert not first.calls and len(first.counts) == 1
    data = ledger._read(case.spec)
    assert data['typed_audit']['stages'][0]['state'] == 'prepared' and not data['rows']
    data['typed_audit']['stages'] = []
    ledger.ledger_path(case.spec).write_bytes(shared.canonical(data))
    before = evidence(case)
    second = Messages(case)
    with pytest.raises(ledger.UsageLedgerError, match='checkpoint'):
        run(case, second)
    assert not second.calls and not second.counts and evidence(case) == before


def test_intact_prepared_stage_resumes_with_saved_count_without_recount(case, monkeypatch):
    original = api._call_with_usage
    monkeypatch.setattr(api, '_call_with_usage', lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
    first = Messages(case)
    with pytest.raises(KeyboardInterrupt):
        run(case, first)
    monkeypatch.setattr(api, '_call_with_usage', original)
    second = Messages(case)
    run(case, second)
    assert len(second.calls) == len(runtime.roster(case.packet))
    assert len(second.counts) == len(second.calls) - 1


def test_downstream_codec_contract_and_projection_cannot_be_dropped(case):
    outcome = run(case, Messages(case))
    publish(case, outcome)
    records = case.carry['Original full record']
    projection = api.CARRY_LABEL.format(name='Audit findings') + runtime.model_carry(case.spec, outcome.audit)
    contract = shared.canonical(audit.downstream_contract()).decode()
    texts = [bc1_context.generation_context(case.captured), bc1_context.schema_context(case.captured, records),
             api.CARRY_LABEL.format(name='Completed full record') + records, projection, contract]
    kwargs = {'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': text} for text in texts]}]}
    runtime.require_request(case.spec, 'reconcile_full', kwargs)
    for missing in (projection, contract):
        altered = deepcopy(kwargs)
        altered['messages'][0]['content'] = [p for p in altered['messages'][0]['content'] if p['text'] != missing]
        with pytest.raises(ledger.UsageLedgerError):
            runtime.require_request(case.spec, 'reconcile_full', altered)
