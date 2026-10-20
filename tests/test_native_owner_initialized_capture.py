"""Captured-only selected initialization, derived from a genuine v1 fixture.

The successor is an invented declaration, not a live runner publication or a
public verified execution. Original files and immutable v1 pool are preserved.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path, PurePosixPath

import pytest

from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_registration as registration
from data_sheets_schema import native_shared_results as results
from data_sheets_schema import native_shared_stage as stage
from tests.test_native_owner_runner import SYNTHETIC_CLOCK
from tests.test_native_shared_live_capture import started
from tests.test_native_shared_registration import execution, bound, native_spec, declaration
from tests.test_native_shared_results import initial


def artifact(role, path, raw):
    return c.CapturedArtifact(c.ArtifactPin(role, str(path), len(raw), c.sha(raw)), raw)


def member(item, template=None):
    """Synthetic successor metadata; unchanged stream metadata stays actual."""
    metadata = (c.strict_json(template.metadata_json) if template is not None else
        {'exists': True, 'regular': True, 'symlink': False, 'links': 1,
         'device': 7101, 'inode': 7102, 'size': len(item.raw), 'mtime_ns': 1000})
    metadata['size'] = len(item.raw)
    return evidence.PoolMember(item, c.canonical(metadata))


def pool_member(pool, role, path=None):
    matches = [row for row in pool.members if row.captured.pin.role == role
               and (path is None or row.captured.pin.path == str(path))]
    assert len(matches) == 1, (role, path, len(matches))
    return matches[0]


def replace_pool_member(pool, target, replacement):
    """Replace exact member and its stream reference, without repairing pins."""
    assert sum(row is target for row in pool.members) == 1
    return evidence.CapturePool(tuple(replacement if row is target else row
        for row in pool.members), tuple((stream, replacement.member_id if identity == target.member_id
                                       else identity) for stream, identity in pool.stream_bindings))


@pytest.fixture
def initial_v1(started):
    live, pool = initial(started)
    # A genuine current declaration is captured during setup only. Saved
    # reconstruction must not recompute it or claim its live verification.
    selected_dependencies = authority.dependency_identity(stream_snapshot_profile=1)
    return {'live': live, 'pool': pool, 'pool_raw': pool.encode(),
            'selected_dependencies': selected_dependencies,
            'original_files': {row.captured.pin.path: row.captured.raw for row in pool.members}}


def selected_case(baseline, *, mutations=None, selection=None, streams=None):
    """Build a detached successor, with mutations before downstream rehashes.

    Mutators take one detached node and may mutate it or return a replacement.
    Nodes: composition, execution (alias value), started, owner, payload,
    observation, binding, genesis, session_bound, journal. Serializers first
    create the valid shape; later mutations may deliberately violate it. Thus
    malformed owner tests can reach saved validation instead of being preempted
    by the serializer's separate live-input guard. No production guard is patched.
    """
    mutations = {} if mutations is None else mutations
    known = {'composition', 'execution', 'value', 'started', 'owner', 'payload',
             'observation', 'binding', 'genesis', 'session_bound', 'journal'}
    assert set(mutations) <= known and not ({'execution', 'value'} <= set(mutations))

    def mutate(name, value):
        action = mutations.get(name)
        if action is None and name == 'execution':
            action = mutations.get('value')
        if action is None:
            return value
        changed = action(value)
        return value if changed is None else changed

    live, original = baseline['live'], baseline['pool']
    selection = live.selection if selection is None else selection
    composition = mutate('composition', deepcopy(live.composition))
    # Default fixture keeps complete raw S. Explicit composition mutants may
    # contradict it, and the downstream raw C pin must still honestly match.
    if 'composition' not in mutations:
        composition.update(selection_raw_json=selection.registration.raw.decode('utf-8'),
                           selection_sha256=selection.registration.pin.sha256)
    composition_raw = c.canonical(composition)
    value = deepcopy(live.value)
    value.update(dependencies=deepcopy(baseline['selected_dependencies']),
        composition_raw_json=composition_raw.decode('utf-8'), composition_sha256=c.sha(composition_raw),
        selection_sha256=selection.registration.pin.sha256)
    value = mutate('execution', value)
    execution_item = artifact('execution_capture', selection.role('execution_capture'), c.canonical(value))
    started_doc = c.strict_json(live.binding.started.raw)
    started_doc.update(registration_sha256=execution_item.pin.sha256,
                       composition_sha256=c.sha(composition_raw), attempt_id=value['attempt_id'])
    started_doc = mutate('started', started_doc)
    started_item = artifact('started_capture', selection.role('started_capture'), c.canonical(started_doc))
    stream_members = {role: pool_member(original, role) for role in ('transcript', 'control')}
    if streams is not None:
        assert set(streams) <= set(stream_members)
        stream_members.update(streams)
    anchors = {role: {key: c.strict_json(row.metadata_json)[key] for key in ('device', 'inode')}
               for role, row in stream_members.items()}
    prefixes = {role: capture._prefix(row) for role, row in stream_members.items()}
    duration = live.value['runtime']['deadline_seconds'] * 1_000_000_000
    owner_template = {'format': 'native_stream_owner_v2',
        'coordination_profile': deepcopy(baseline['selected_dependencies']['stream_snapshot_profile']),
        'execution_sha256': execution_item.pin.sha256, 'started_sha256': started_item.pin.sha256,
        'owner_pid': 7103, 'clock': 'monotonic_ns', 'start_ns': 1000,
        'deadline_ns': 1000 + duration, 'duration_ns': duration,
        'clock_domain': deepcopy(SYNTHETIC_CLOCK),
        **{role: {'path': row.captured.pin.path, **anchors[role]}
           for role, row in stream_members.items()}}
    owner_path = str(PurePosixPath(value['attempt_directory']) / 'stream-owner.json')
    serializer_owner = artifact('owner', owner_path, c.canonical(owner_template))
    owner = mutate('owner', deepcopy(owner_template))
    owner_item = artifact('owner', owner_path, c.canonical(owner))
    payload = deepcopy(c.strict_json(live.binding.init_observation.raw)['payload'])
    payload['stream_files'] = anchors
    raw = capture.observation_bytes('initialized', selection, execution_item.pin.sha256,
        value['attempt_id'], live.binding.session_id, prefixes['transcript'], prefixes['control'],
        payload, owner=serializer_owner)
    observation = c.strict_json(raw)
    observation['payload']['owner'] = c.pin_dict(owner_item.pin)
    observation['payload'] = mutate('payload', observation['payload'])
    observation = mutate('observation', observation)
    observation_item = artifact('observation', live.binding.init_observation.pin.path, c.canonical(observation))
    binding = mutate('binding', capture._binding_document(selection, value, composition,
        execution_item, started_item, observation_item, live.binding.session_id))
    binding_item = artifact('session_binding', selection.role('session_binding'), c.canonical(binding))

    def record(name, number, previous, session, payload):
        raw = stage.record_bytes(record_type=name, sequence=number, previous_record_sha256=previous,
            selection_sha256=selection.registration.pin.sha256, execution_sha256=execution_item.pin.sha256,
            attempt_id=value['attempt_id'], session_id=session, payload=payload)
        doc = mutate(name, c.strict_json(raw))
        item = artifact('record', stage._dynamic(selection, 'record', number), c.canonical(doc))
        return doc, item

    genesis, genesis_item = record('genesis', 0, None, None,
        {'execution': c.pin_dict(execution_item.pin), 'started': c.pin_dict(started_item.pin)})
    session_bound, session_item = record('session_bound', 1, genesis_item.pin.sha256, live.binding.session_id,
        {'binding': c.pin_dict(binding_item.pin), 'init_observation': c.pin_dict(observation_item.pin)})
    journal_raw = stage.journal_bytes(selection_sha256=selection.registration.pin.sha256,
        execution_sha256=execution_item.pin.sha256, attempt_id=value['attempt_id'],
        records=(genesis_item.pin, session_item.pin))
    journal = mutate('journal', c.strict_json(journal_raw))
    journal_item = artifact('journal', selection.role('journal'), c.canonical(journal))
    artifacts = {'execution': execution_item, 'started': started_item, 'owner': owner_item,
        'observation': observation_item, 'binding': binding_item, 'genesis': genesis_item,
        'session_bound': session_item, 'journal': journal_item}
    by_identity = {(row.captured.pin.role, row.captured.pin.path): row for row in original.members}
    assert len(by_identity) == len(original.members)
    for item in artifacts.values():
        key = (item.pin.role, item.pin.path)
        by_identity[key] = member(item, by_identity.get(key))
    item = selection.registration
    by_identity[(item.pin.role, item.pin.path)] = member(item,
        by_identity[(item.pin.role, item.pin.path)])
    for role, row in stream_members.items():
        by_identity[(role, row.captured.pin.path)] = row
    pool = evidence.CapturePool(tuple(by_identity[key] for key in sorted(by_identity)),
        tuple((evidence.stream_id(execution_item.pin.sha256, role, row.captured.pin.path), row.member_id)
              for role, row in sorted(stream_members.items())))
    return {'baseline': baseline, 'selection': selection, 'pool': pool, 'value': value,
        'composition': composition, 'started': started_doc, 'owner': owner,
        'observation': observation, 'binding': binding, 'genesis': genesis,
        'session_bound': session_bound, 'journal': journal, 'artifacts': artifacts,
        'stream_members': stream_members, 'prefixes': prefixes}


@pytest.fixture
def initialized_case(initial_v1):
    return selected_case(initial_v1)


def test_omitted_owner_preserves_exact_v1_bytes_and_real_saved_run(initial_v1):
    live, pool = initial_v1['live'], initial_v1['pool']
    original = live.binding.init_observation
    doc = c.strict_json(original.raw)
    assert set(doc['payload']) == {'initialize_sent', 'initialize_ack', 'native_init', 'stream_files'}
    expected = c.canonical({'kind': c.KINDS['observation'], 'version': 1,
        'observation_type': 'initialized', 'selection_sha256': live.selection.registration.pin.sha256,
        'execution_sha256': live.binding.execution.pin.sha256,
        'attempt_id': live.binding.attempt_id, 'session_id': live.binding.session_id,
        'transcript_prefix': evidence.prefix_reference(live.transcript,
            execution_sha256=live.binding.execution.pin.sha256),
        'control_prefix': evidence.prefix_reference(live.control,
            execution_sha256=live.binding.execution.pin.sha256), 'payload': doc['payload']})
    assert original.raw == expected
    for options in ({}, {'owner': None}):
        assert capture.observation_bytes('initialized', live.selection,
            live.binding.execution.pin.sha256, live.binding.attempt_id, live.binding.session_id,
            live.transcript, live.control, doc['payload'], **options) == expected
    rebuilt = results.rebuild(pool, live.value)
    assert type(rebuilt) is capture._CapturedRun
    assert rebuilt.binding == live.binding and rebuilt.history == live.history
    assert rebuilt.selection == live.selection and rebuilt.phase1 is None
    assert pool.encode() == initial_v1['pool_raw']


def test_selected_initialization_roundtrip_is_detached_counted_evidence(initialized_case):
    case = initialized_case
    encoded = case['pool'].encode()
    pool = evidence.decode(encoded)
    assert pool == case['pool']
    result = results.rebuild(pool, case['value'])
    assert type(result) is results._OwnerInitializationEvidence
    assert not isinstance(result, (capture._CapturedRun, c.StageInvocationCapture, c.ExecutionBinding))
    assert [field.name for field in fields(result)] == ['_raw']
    assert type(result._raw) is bytes and not hasattr(result, '__dict__')
    for name in ('pool', 'reader', 'selection', 'spec', 'binding', 'trace', 'decision', 'invocation'):
        assert not hasattr(result, name)
    doc = result.as_dict()
    assert doc['format'] == 'native_owner_initialized_evidence_v1'
    assert doc['scope'] == 'captured_initialization_only'
    assert doc['counts'] == {'members': len(pool.members),
        'raw_bytes': sum(len(row.captured.raw) for row in pool.members),
        'observations': 1, 'history_records': 2}
    assert doc['owner'] == {'pin': c.pin_dict(case['artifacts']['owner'].pin), 'declaration': case['owner']}
    assert doc['identities'] == {'selection_sha256': case['selection'].registration.pin.sha256,
        'execution_sha256': case['artifacts']['execution'].pin.sha256,
        'composition_sha256': c.sha(c.canonical(case['composition'])),
        'started_sha256': case['artifacts']['started'].pin.sha256,
        'attempt_id': case['value']['attempt_id'], 'session_id': case['binding']['session_id']}
    assert doc['history']['records'] == [c.pin_dict(case['artifacts'][key].pin)
                                        for key in ('genesis', 'session_bound')]
    assert len(doc['members']) == len(pool.members)
    assert {(row['pin']['role'], row['pin']['path']) for row in doc['members']} == {
        (row.captured.pin.role, row.captured.pin.path) for row in pool.members}
    detached = result.as_dict()
    detached['owner']['declaration']['clock_domain']['boot_uuid'] = 'changed'
    detached['members'].clear()
    assert result.as_dict() == doc
    with pytest.raises(FrozenInstanceError):
        result._raw = b'{}'
    assert result._raw == c.canonical(doc)
    assert case['baseline']['pool'].encode() == case['baseline']['pool_raw']
    for path, raw in case['baseline']['original_files'].items():
        assert Path(path).read_bytes() == raw
    # Actual public admission remains strict. Success above is captured parsing.
    with pytest.raises(ValueError):
        registration.verified(case['artifacts']['execution'].raw)


def serialize_owner(case, owner, *, kind='initialized', payload=None):
    if payload is None:
        payload = deepcopy(c.strict_json(case['baseline']['live'].binding.init_observation.raw)['payload'])
    return capture.observation_bytes(kind, case['selection'], case['artifacts']['execution'].pin.sha256,
        case['value']['attempt_id'], case['binding']['session_id'],
        case['prefixes']['transcript'], case['prefixes']['control'], payload, owner=owner)


@pytest.mark.parametrize('change', ['not_artifact', 'role', 'basename', 'malformed_raw',
                                  'encoding', 'oversized', 'execution_sha'])
def test_owner_serializer_refuses_bad_captured_authority(initialized_case, change):
    case = initialized_case
    owner = case['artifacts']['owner']
    if change == 'not_artifact':
        owner = {'pin': c.pin_dict(owner.pin), 'raw': owner.raw}
    elif change == 'role':
        owner = artifact('unregistered_owner', owner.pin.path, owner.raw)
    elif change == 'basename':
        owner = artifact('owner', str(PurePosixPath(owner.pin.path).with_name('foreign-owner.json')), owner.raw)
    elif change == 'malformed_raw':
        owner = artifact('owner', owner.pin.path, b'{}')
    elif change == 'encoding':
        owner = artifact('owner', owner.pin.path, b'\xff')
    elif change == 'oversized':
        raw = owner.raw + b' ' * (16_385 - len(owner.raw))
        assert len(raw) == 16_385
        owner = artifact('owner', owner.pin.path, raw)
    else:
        doc = c.strict_json(owner.raw)
        doc['execution_sha256'] = '0' * 64
        owner = artifact('owner', owner.pin.path, c.canonical(doc))
    with pytest.raises(ValueError):
        serialize_owner(case, owner)


def test_owner_is_only_an_initialized_serializer_extension(initialized_case):
    case = initialized_case
    with pytest.raises(ValueError):
        serialize_owner(case, case['artifacts']['owner'], kind='phase1_sealed',
            payload={'full': {}, 'original_receipt': {}, 'helper_calls': []})
    # Serializer checks only its stated local contract. Exact E-derived path
    # admission remains the saved resolver's responsibility, never implied here.
    original = case['artifacts']['owner']
    elsewhere = artifact('owner', '/explicit-synthetic-unbound/stream-owner.json', original.raw)
    doc = c.strict_json(serialize_owner(case, elsewhere))
    assert doc['version'] == 2 and doc['payload']['owner'] == c.pin_dict(elsewhere.pin)


def test_saved_owner_reader_uses_exact_execution_and_counts_member_once(initialized_case):
    case = initialized_case
    owner = case['artifacts']['owner']
    reader = capture._Reader(case['selection'], pool=case['pool'], execution=case['artifacts']['execution'])
    before = reader.total, len(reader.members)
    assert reader.read('owner', owner.pin.path, owner.pin) == owner
    assert (reader.total, len(reader.members)) == (before[0] + len(owner.raw), before[1] + 1)
    assert reader.read('owner', owner.pin.path, owner.pin) == owner
    assert (reader.total, len(reader.members)) == (before[0] + len(owner.raw), before[1] + 1)
    for kwargs in ({}, {'pool': case['pool']}, {'execution': case['artifacts']['execution']},
                   {'pool': case['pool'], 'execution': pool_member(case['pool'], 'execution_capture')}):
        with pytest.raises(ValueError):
            capture._Reader(case['selection'], **kwargs).read('owner', owner.pin.path, owner.pin)
