"""Invented captured stage histories, not observed native permission evidence."""
from dataclasses import replace, asdict
import json
from pathlib import Path

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_stage as stage, native_shared_receipts as nr
from data_sheets_schema import audit_omissions as om, typed_audit as typed, resources
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_typed_audit import supplied, replies


def artifact(role, path, raw):
    return c.CapturedArtifact(c.ArtifactPin(role, path, len(raw), c.sha(raw)), raw)


def plain(item):
    return {key: getattr(item.pin, key) for key in ('path', 'bytes', 'sha256')}


@pytest.fixture
def case(supplied, request):
    options = getattr(request, 'param', {})
    root = '/neutral/native'
    authorities = []
    def authority(role, raw):
        item = artifact(role, '/neutral/inputs/' + role, raw)
        authorities.append(item)
        return item
    bundle = authority('bundle', supplied['bundle'])
    manifest = authority('chunk_manifest', supplied['manifest'])
    context = authority('context', supplied['context'])
    policy = authority('native_policy', b'Native stage policy: every worker, source chunk and role must be reviewed.')
    assets = {'src/download/prompts/native_fixture.md': plain(policy)}
    for name in om.ASSET_SHA256:
        item = authority('omission_' + name, om._asset(name))
        assets['src/data_sheets_schema/omission_inventory_v1/' + name] = plain(item)
    snapshot = capture_schema(supplied['schema_path'], strict=True)
    schemas, declarations = [], {}
    for kind, root_class in (('full', 'Dataset'), ('core', 'CoreDataset')):
        rows = snapshot.sources if kind == 'full' else (
            ('core', Path('/neutral/core.yaml'), b'id: https://example.test/core\nname: core\nclasses:\n  CoreDataset:\n    attributes:\n      name: {}\n'),)
        sources = tuple(artifact(f'{kind}_schema_{i}', str(path), raw) for i, (_, path, raw) in enumerate(rows))
        imports = tuple((str(name), item.pin.role) for (name, _, _), item in zip(rows, sources))
        schemas.append(c.SchemaClosureCapture(kind=kind, root_class=root_class, root_name=str(rows[0][0]),
            sources=sources, import_roles=imports, closure_sha256=c.schema_closure_sha(sources, imports)))
        declarations[kind + '_schema'] = {'root': sources[0].pin.path, 'root_class': root_class,
            'sources': [{'name': str(name), **plain(item)} for (name, _, _), item in zip(rows, sources)]}
    receipt_policy = authority('receipt_policy', c.canonical({'kind': c.KINDS['receipt_policy'], 'version': 1,
        'registration_id': 'native-test-floor', 'condition': c.CONDITION,
        'runtime_policy_sha256': policy.pin.sha256, 'receipt_instrument_version': 4,
        'coverage_floor': {'state': 'registered', 'numerator': 0, 'denominator': 1}}))
    descriptor_raw = c.canonical({'protocol': c.NAME, 'assets': {name: pin['sha256'] for name, pin in assets.items()}})
    descriptor = c.DescriptorCapture(descriptor_raw, c.sha(descriptor_raw))
    doc = {'kind': c.KINDS['selection'], 'version': 1, 'registration_id': 'native-offline-case',
        'registration_path': '/neutral/selection.json',
        'run': {'project': 'Example', 'arm': 'BASELINE', 'method': 'claudecode_direct', 'label': 'neutral'},
        'selection': {'protocol': c.NAME, 'version': 1, 'condition': c.CONDITION, 'renderer': 26,
            'runtime': c.RUNTIME, 'native_shared_generation_version': 1, 'native_source_attribution_version': 0,
            'shared_generation_version': 0, 'api_playbook_version': 0, 'receipt_completion_version': 0,
            'removal_repair_version': 0, 'descriptor_sha256': descriptor.sha256, 'assets': assets},
        'inputs': {'project': 'Example', 'bundle': plain(bundle), 'chunk_manifest': plain(manifest),
            'context': plain(context), 'source_manifest': None,
            'profile': {'name': 'neutral', 'basis': 'fixture declaration', 'vocabulary': None}, **declarations},
        'receipt_policy': plain(receipt_policy), 'bounds': {**dict(c.BOUND_CEILINGS), **options.get('bounds', {})}, 'stage_root': root}
    selection = c.NativeSelectionCapture(arm='BASELINE', authority=tuple(authorities),
        bounds_json=c.canonical(doc['bounds']), condition=c.CONDITION, descriptor=descriptor, project='Example',
        protocol=c.NAME, receipt_policy=receipt_policy,
        registration=artifact('selection', doc['registration_path'], c.canonical(doc)),
        roles=c.role_paths(doc['registration_path'], root), run_id=doc['registration_id'], schemas=tuple(schemas))
    def at(role, value):
        return artifact(role, selection.role(role), value if type(value) is bytes else c.canonical(value))
    runtime = artifact('runtime', '/neutral/runtime.json', c.canonical({'limits': {'maxOutputTokens': 4000}}))
    execution = c.ExecutionBinding(attempt_id='attempt-1', session_id='observed-neutral-session',
        selection_sha256=selection.registration.pin.sha256, execution=at('execution_capture', {'fixture': 'execution'}),
        started=at('started_capture', {'fixture': 'started'}), binding_artifact=at('session_binding', {'fixture': 'binding'}),
        init_observation=artifact('observation', root + '/observations/000000.json', b'{"fixture":"init"}'),
        instruction_sha256='a' * 64, permission_sha256='b' * 64,
        runtime_declaration=runtime, runtime_declaration_sha256=runtime.pin.sha256,
        registered_python='/neutral/python', working_directory='/neutral')
    receipt = json.loads(supplied['receipt'])
    for chunk in receipt['chunks']:
        chunk.update(status='nothing_relevant', reason='No initial claim receipt declared.')
    if options.get('zero_work'):
        chunk = next(row for row in json.loads(supplied['manifest'])['chunks'] if row.get('source') == 'manual.txt')
        row = next(row for row in receipt['chunks'] if row['id'] == chunk['id'])
        row.pop('reason')
        row.update(status='extracted', extracted=[{'slot': 'name', 'snippet': 'Example release provides a complete description.'}])
    phase1 = c.Phase1Capture(core=None, core_seal=None, core_seal_observation=None,
        full=at('phase1_full', supplied['original_full']), original_receipt=at('phase1_receipt', c.canonical(receipt)),
        seal=at('phase1_seal', {'fixture': 'sealed full/receipt'}),
        full_seal_observation=artifact('observation', root + '/observations/000001.json', b'{"fixture":"full helper"}'))
    journal = artifact('journal', selection.role('journal'), stage.journal_bytes(
        selection_sha256=selection.registration.pin.sha256, execution_sha256=execution.execution.pin.sha256,
        attempt_id=execution.attempt_id, records=()))
    history = c.RawHistory(journal=journal, records=(), artifacts=(), observations=())
    entries = (
        ('genesis', c.canonical({'execution': c.pin_dict(execution.execution.pin), 'started': c.pin_dict(execution.started.pin)})),
        ('session_bound', c.canonical({'binding': c.pin_dict(execution.binding_artifact.pin), 'init_observation': c.pin_dict(execution.init_observation.pin)})),
        ('phase1_sealed', c.canonical({'seal': c.pin_dict(phase1.seal.pin), 'full': c.pin_dict(phase1.full.pin),
            'original_receipt': c.pin_dict(phase1.original_receipt.pin), 'observation': c.pin_dict(phase1.full_seal_observation.pin)})))
    records, journal = stage.append_records(selection, execution, history, entries)
    history = append(history, records, journal)
    return selection, execution, phase1, history


def captured(item):
    return c.CapturedArtifact(item.pin, item.raw)


def append(history, records, journal, outputs=()):
    return replace(history, records=history.records + tuple(captured(item) for item in records),
                   journal=captured(journal), artifacts=history.artifacts + tuple(captured(item) for item in outputs))


def publish(history, decision):
    records, outputs, journal = [], [], None
    for pub in decision.publications:
        if pub.artifact.pin.role == 'journal':
            assert pub.predecessor_sha256 == history.journal.pin.sha256
            journal = pub.artifact
        elif pub.artifact.pin.role == 'record':
            records.append(pub.artifact)
        else:
            outputs.append(pub.artifact)
    return history if journal is None else append(history, records, journal, outputs)


def consume(case, decision, raw):
    selection, execution, phase1, history = case
    assert decision.state == 'awaiting_response'
    response = artifact('response', decision.response.path, raw)
    base = len(history.observations) + 2
    read = artifact('observation', selection.role('observations_root') + f'/{base:06d}.json',
                    c.canonical({'fixture': 'settled complete read', 'request': c.pin_dict(decision.request.pin)}))
    wrote = artifact('observation', selection.role('observations_root') + f'/{base+1:06d}.json',
                     c.canonical({'fixture': 'first settled write', 'response': c.pin_dict(response.pin)}))
    history = replace(history, artifacts=history.artifacts + (response,), observations=history.observations + (read, wrote))
    payload = {'cursor': asdict(decision.cursor), 'request_sha256': c.strict_json(decision.request.raw)['request_sha256'],
        'response': c.pin_dict(response.pin), 'read_observation': c.pin_dict(read.pin), 'response_observation': c.pin_dict(wrote.pin)}
    records, journal = stage.append_records(selection, execution, history, (('response_consumed', c.canonical(payload)),))
    return selection, execution, phase1, append(history, records, journal)


def add_core(case):
    selection, execution, phase1, history = case
    phase1 = replace(phase1,
        core=artifact('phase1_core', selection.role('phase1_core'), b'name: Example\n'),
        core_seal=artifact('core_seal', selection.role('core_seal'), b'{"fixture":"core sealed"}'),
        core_seal_observation=artifact('observation', selection.role('observations_root') + '/000001.json', b'{"fixture":"core helper"}'))
    payload = {'seal': c.pin_dict(phase1.core_seal.pin), 'core': c.pin_dict(phase1.core.pin),
               'observation': c.pin_dict(phase1.core_seal_observation.pin)}
    records, journal = stage.append_records(selection, execution, history, (('core_sealed', c.canonical(payload)),))
    return selection, execution, phase1, append(history, records, journal)


def respond(case, raw):
    selection, execution, phase1, history = case
    decision = stage.prepare_next(*case)
    if decision.state == 'request_ready':
        history = publish(history, decision)
        case = selection, execution, phase1, history
        decision = stage.prepare_next(*case)
    consumed = consume(case, decision, raw)
    transition = stage.check_response(*consumed, decision.request.raw, raw)
    updated = append(consumed[3], transition.records_to_append, transition.predicted_journal,
                     tuple(pub.artifact for pub in transition.publications))
    return (*consumed[:3], updated), transition


def receipt_answer(case):
    paths = nr.prepare(*case[:3])['requested_paths']
    return c.canonical({'rereceipt': [{'path': path, 'unsupported': True, 'reason': 'Candidate requires independent audit.'} for path in paths]})


def full_roundtrip(case):
    case, transition = respond(case, receipt_answer(case))
    assert transition.disposition == 'checked'
    wait = stage.prepare_next(*case)
    assert wait.state == 'await_core' and wait.cursor is wait.request is wait.response is None
    case = (*case[:3], publish(case[3], wait))
    case = add_core(case)
    while True:
        decision = stage.prepare_next(*case)
        if decision.state == 'assembly_complete':
            return case, decision.completion
        assert decision.state == 'request_ready' and decision.response is None
        inner = c.strict_json(decision.request.raw, max_bytes=64_000_000)['payload']['inner_request']
        packet = stage._Replay(*case).run().packet
        workers, omission, delta, _ = replies(packet, 2)
        raw = workers[decision.cursor.target_id] if decision.cursor.kind == 'worker' else c.canonical(
            omission if decision.cursor.kind == 'omission' else delta)
        case, transition = respond(case, raw)
        assert transition.disposition == 'checked'


def test_real_all_stage_roundtrip_is_pure_and_rebuilds_final(case, monkeypatch):
    # Dependencies are imported before the no-I/O barrier. The actual stage
    # constructors/checkers only see immutable captures from this point onward.
    import data_sheets_schema.schema_view
    def blocked(*args, **kwargs):
        raise AssertionError('native pure stage attempted an ambient resource lookup')
    monkeypatch.setattr(Path, 'read_bytes', blocked)
    monkeypatch.setattr(Path, 'resolve', blocked)
    monkeypatch.setattr(resources, 'resource_path', blocked)
    monkeypatch.setattr(om, '_asset', blocked)
    completed_case, completion = full_roundtrip(case)
    check = stage.check_assembly(*completed_case, completion.assembly.raw)
    assert check == completion
    counts = c.strict_json(check.counts_json)
    assert counts['workers'] >= 1 and counts['omissions']['retained'] == 2
    assert counts['findings']['omission'] == 1
    records = [c.strict_json(item.raw) for item in completed_case[3].records]
    workers = [row for row in records if row['record_type'] == 'stage_checked' and row['payload']['cursor']['kind'] == 'worker']
    assert all(row['payload']['derived_response']['origin'] == 'helper_derived_typed_response_v1' for row in workers)
    for item in completed_case[3].artifacts:
        if item.pin.role == 'request':
            body = c.strict_json(item.raw, max_bytes=64_000_000)['payload']
            assert body['generation_context'] == case[0].generation_context()
            assert body['owner_context']['original_full_yaml'] == case[2].full.raw.decode()
            if body['cursor']['kind'] != 'receipt':
                assert body['receipt_carry']['unsupported_audit_candidates']


def test_malformed_first_response_stays_consumed(case):
    updated, transition = respond(case, b'{rereceipt: nope}')
    assert transition.disposition == 'failed'
    assert stage.prepare_next(*updated).state == 'failed'
    with pytest.raises(ValueError, match='no unique durable'):
        stage.check_response(*updated, b'{}', receipt_answer(case))
    assert any(item.raw == b'{rereceipt: nope}' for item in updated[3].artifacts)


def test_wrong_request_or_later_answer_cannot_replace_first_bytes(case):
    selection, execution, phase1, history = case
    ready = stage.prepare_next(*case)
    case = selection, execution, phase1, publish(history, ready)
    observed = stage.prepare_next(*case)
    raw = receipt_answer(case)
    case = consume(case, observed, raw)
    for request, answer in ((b'{}', raw), (observed.request.raw, raw + b' ')):
        with pytest.raises(ValueError, match='first consumed'):
            stage.check_response(*case, request, answer)


def test_all_stages_required_and_foreign_original_refuses(case):
    complete_case, completion = full_roundtrip(case)
    with pytest.raises(ValueError):
        stage.check_assembly(*complete_case[:3], replace(complete_case[3], records=complete_case[3].records[:-1]), completion.assembly.raw)
    phase1 = replace(complete_case[2], core=artifact('phase1_core', complete_case[2].core.pin.path,
                                                   complete_case[2].core.raw + b'# different original\n'))
    with pytest.raises(ValueError, match='core_sealed'):
        stage.check_assembly(complete_case[0], complete_case[1], phase1, complete_case[3], completion.assembly.raw)


@pytest.mark.parametrize('case', [{'zero_work': True}], indirect=True)
def test_zero_work_retains_exact_receipt_bytes_and_no_response_authority(case):
    decision = stage.prepare_next(*case)
    assert decision.state == 'receipt_zero_work'
    assert decision.cursor is decision.request is decision.response is None
    updated = (*case[:3], publish(case[3], decision))
    assert next(item for item in updated[3].artifacts if item.pin.role == 'effective_receipt').raw == case[2].original_receipt.raw
    wait = stage.prepare_next(*updated)
    assert wait.state == 'await_core' and wait.request is wait.response is None
    waiting = (*updated[:3], publish(updated[3], wait))
    assert not stage.prepare_next(*waiting).publications
    with pytest.raises(ValueError, match='zero-work'):
        nr.complete(*case[:3], b'{"rereceipt":[]}')


@pytest.mark.parametrize('case', [{'bounds': {'max_request_bytes': 100}}], indirect=True)
def test_complete_outer_context_cannot_be_truncated_to_fit(case):
    with pytest.raises(ValueError, match='bounded'):
        stage.prepare_next(*case)


def test_missing_observed_read_or_forged_consumed_bytes_refuse(case):
    ready = stage.prepare_next(*case)
    observed_case = (*case[:3], publish(case[3], ready))
    observed = stage.prepare_next(*observed_case)
    consumed = consume(observed_case, observed, receipt_answer(case))
    broken = replace(consumed[3], observations=consumed[3].observations[1:])
    with pytest.raises(ValueError, match='exact captured artifact'):
        stage.check_response(*consumed[:3], broken, observed.request.raw, receipt_answer(case))


def test_even_consistently_rehashed_admission_cannot_drop_scope_context(case):
    ready = stage.prepare_next(*case)
    history = publish(case[3], ready)
    raw = c.strict_json(ready.request.raw, max_bytes=64_000_000)
    raw['payload']['generation_context'] = None
    raw['request_sha256'] = c.sha(c.canonical(raw['payload']))
    replacement = artifact('request', ready.request.pin.path, c.canonical(raw))
    records = []
    for previous in history.records:
        row = c.strict_json(previous.raw)
        if row['record_type'] == 'request_admitted':
            row['payload']['request'] = c.pin_dict(replacement.pin)
        row['previous_record_sha256'] = records[-1].pin.sha256 if records else None
        records.append(artifact('record', previous.pin.path, c.canonical(row)))
    journal = artifact('journal', history.journal.pin.path, stage.journal_bytes(
        selection_sha256=case[0].registration.pin.sha256, execution_sha256=case[1].execution.pin.sha256,
        attempt_id=case[1].attempt_id, records=tuple(item.pin for item in records)))
    changed = replace(history, records=tuple(records), journal=journal,
        artifacts=tuple(replacement if item.pin.role == 'request' else item for item in history.artifacts))
    with pytest.raises(ValueError, match='request_admitted'):
        stage.prepare_next(*case[:3], changed)


def test_receipt_floor_never_certifies_pending_or_empty_scope(case):
    assert nr.floor({'receiptable': 1, 'with_receipt': 0}, case[0])['passed']
    assert nr.floor({'receiptable': 0, 'with_receipt': 0}, case[0])['state'] == 'not_applicable'
    for bad in ({'receiptable': True, 'with_receipt': 0}, {'receiptable': 1, 'with_receipt': 2},
                {'receiptable': 1, 'with_receipt': 0, 'populated': 3, 'exempt': 1}):
        with pytest.raises(ValueError):
            nr.floor(bad, case[0])
    value = c.strict_json(case[0].receipt_policy.raw)
    value['coverage_floor'] = {'state': 'pending', 'mode': 'diagnostic_pilot'}
    policy = artifact('receipt_policy', case[0].receipt_policy.pin.path, c.canonical(value))
    doc = case[0].document()
    doc['receipt_policy'] = plain(policy)
    selected = replace(case[0], receipt_policy=policy,
        registration=artifact('selection', case[0].registration.pin.path, c.canonical(doc)),
        authority=tuple(policy if item.pin.role == 'receipt_policy' else item for item in case[0].authority))
    assert nr.floor({'receiptable': 10, 'with_receipt': 10}, selected)['passed'] is False
