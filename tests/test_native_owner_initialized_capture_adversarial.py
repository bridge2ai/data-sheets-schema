"""Independent saved-only controls; selected declarations are synthetic.

These cases exercise actual immutable pools and reconstructors, never native
launches, live owner admission or public verification bypasses.
"""
from copy import deepcopy
from dataclasses import replace
import builtins
import fcntl
import os
from pathlib import Path
import time

import pytest

from data_sheets_schema import native_attribution_controller as controller
from data_sheets_schema import native_clock_domain_v1 as clocks
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_publication as publication
from data_sheets_schema import native_shared_results as results
from data_sheets_schema import native_shared_streams as streams
from tests.test_native_owner_initialized_capture import (
    artifact, member, pool_member, replace_pool_member, selected_case,
    initial_v1, initialized_case, started, execution, bound, native_spec, declaration,
)


def set_field(path, value):
    def change(document):
        target = document
        parts = path.split('.')
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = deepcopy(value)
    return change


def refuses(case, *, pool=None, value=None, match=None):
    with pytest.raises(ValueError, match=match):
        results.rebuild(case['pool'] if pool is None else pool,
                        case['value'] if value is None else value)


@pytest.mark.parametrize('node,path,value', [
    ('execution', 'kind', 'foreign'),
    ('execution', 'version', True),
    ('execution', 'version', 1.0),
    ('composition', 'kind', 'foreign'),
    ('composition', 'version', True),
    ('composition', 'version', 2),
    ('started', 'kind', 'foreign'),
    ('started', 'version', True),
    ('started', 'version', 1.0),
    ('started', 'state', 'registered'),
    ('started', 'dispatch_limit', True),
    ('started', 'dispatch_limit', 2),
    ('execution', 'selection_sha256', '1' * 64),
    ('composition', 'selection_sha256', '1' * 64),
    ('execution', 'dependencies.version', True),
    ('execution', 'dependencies.version', 1),
    ('execution', 'dependencies.stream_snapshot_profile', None),
    ('started', 'registration_sha256', '1' * 64),
    ('started', 'composition_sha256', '1' * 64),
    ('started', 'attempt_id', 'other'),
])
def test_rehashed_declared_identity_conflicts_refuse(initial_v1, node, path, value):
    case = selected_case(initial_v1, mutations={node: set_field(path, value)})
    # Every downstream raw pin is honestly recomputed; saved passing flags or a
    # merely stale hash cannot explain refusal of these declarations.
    refuses(case)


@pytest.mark.parametrize('mode', ['empty', 'altered_complete'])
def test_matching_rehashed_controller_manifest_and_base_cannot_redefine_roster(initial_v1, mode):
    manifest = deepcopy(initial_v1['live'].composition['controller_sources'])
    base_modules = deepcopy(initial_v1['selected_dependencies']['base']['modules'])
    if mode == 'empty':
        manifest['modules'] = {}
        base_modules = {}
    else:
        name = sorted(manifest['modules'])[0]
        manifest['modules'][name]['sha256'] = '1' * 64
        base_modules[name] = deepcopy(manifest['modules'][name])
    case = selected_case(initial_v1, mutations={
        'composition': set_field('controller_sources', manifest),
        'execution': set_field('dependencies.base.modules', base_modules),
    })
    assert all(case['value']['dependencies']['base']['modules'][name] == pin
               for name, pin in case['composition']['controller_sources']['modules'].items())
    refuses(case, match='controller/package')


def test_profile_hash_must_match_captured_package_entry(initial_v1):
    def change(value):
        pin = value['dependencies']['stream_snapshot_profile']['implementations']['control']
        value['dependencies']['base']['package_sources'][pin['path']] = '1' * 64
    case = selected_case(initial_v1, mutations={'execution': change})
    refuses(case, match='controller/package')


@pytest.mark.parametrize('path,value', [
    ('execution_sha256', '1' * 64),
    ('started_sha256', '1' * 64),
    ('transcript.inode', 1),
    ('control.path', '/foreign/control.jsonl'),
    ('clock_domain.boot_uuid', 'not-a-uuid'),
    ('owner_pid', True),
    ('deadline_ns', 1001),
])
def test_owner_rehashed_conflicts_refuse(initial_v1, path, value):
    case = selected_case(initial_v1, mutations={'owner': set_field(path, value)})
    refuses(case)


def test_owner_valid_arithmetic_cannot_replace_original_duration(initial_v1):
    def change(owner):
        owner['duration_ns'] += 1_000_000_000
        owner['deadline_ns'] += 1_000_000_000
    case = selected_case(initial_v1, mutations={'owner': change})
    refuses(case, match='original duration')


@pytest.mark.parametrize('mutation', [
    'execution_duration', 'execution_hash', 'composition_raw_hash',
    'composition_hash_without_execution_hash', 'typed_runtime',
])
def test_runtime_joins_survive_complete_downstream_rehashing(initial_v1, mutation):
    original_c = initial_v1['live'].composition
    original_runtime = deepcopy(initial_v1['live'].value['runtime'])
    original_duration = original_runtime['deadline_seconds']
    runtime = deepcopy(original_runtime)
    composition_raw = original_c['runtime_raw_json']
    composition_hash = original_c['runtime_sha256']
    execution_hash = initial_v1['live'].value['runtime_declaration_sha256']
    owner_duration = original_duration
    if mutation == 'execution_duration':
        runtime['deadline_seconds'] += 1
        owner_duration += 1
    elif mutation == 'execution_hash':
        execution_hash = '0' * 64
    elif mutation == 'composition_raw_hash':
        # Equal parsed content, unequal raw identity; keep both declared hashes.
        composition_raw = '\n' + composition_raw
    elif mutation == 'composition_hash_without_execution_hash':
        runtime['deadline_seconds'] += 1
        owner_duration += 1
        composition_raw = c.canonical(runtime).decode('utf-8')
        composition_hash = c.sha(composition_raw.encode('utf-8'))
    else:
        declared = deepcopy(runtime)
        declared['deadline_seconds'] = float(original_duration)
        assert declared == runtime and c.canonical(declared) != c.canonical(runtime)
        composition_raw = c.canonical(declared).decode('utf-8')
        composition_hash = execution_hash = c.sha(composition_raw.encode('utf-8'))

    def change_composition(document):
        document.update(runtime_raw_json=composition_raw, runtime_sha256=composition_hash)
    def change_execution(document):
        document.update(runtime=deepcopy(runtime), runtime_declaration_sha256=execution_hash)
    def change_owner(document):
        document['duration_ns'] = owner_duration * 1_000_000_000
        document['deadline_ns'] = document['start_ns'] + document['duration_ns']
    case = selected_case(initial_v1, mutations={
        'composition': change_composition, 'execution': change_execution, 'owner': change_owner})
    # These are distinct runtime contradictions. Owner arithmetic, raw E/C
    # pins, started, initialization and journal descendants remain coherent.
    assert case['owner']['duration_ns'] == case['value']['runtime']['deadline_seconds'] * 1_000_000_000
    assert case['value']['composition_sha256'] == c.sha(c.canonical(case['composition']))
    assert case['owner']['execution_sha256'] == case['artifacts']['execution'].pin.sha256
    refuses(case, match='runtime')


def test_runtime_json_formatting_is_allowed_with_exact_rebound_hashes(initial_v1):
    original = initial_v1['live'].composition['runtime_raw_json']
    raw = '\n' + original + '\n'
    digest = c.sha(raw.encode('utf-8'))
    def change_composition(document):
        document.update(runtime_raw_json=raw, runtime_sha256=digest)
    case = selected_case(initial_v1, mutations={
        'composition': change_composition,
        'execution': set_field('runtime_declaration_sha256', digest)})
    assert raw != original
    assert c.canonical(c.strict_json(raw.encode('utf-8'))) == c.canonical(case['value']['runtime'])
    result = results.rebuild(case['pool'], case['value']).as_dict()
    assert result['owner']['declaration'] == case['owner']
    assert result['identities']['composition_sha256'] == case['value']['composition_sha256']
    assert result['counts']['observations'] == 1


@pytest.mark.parametrize('node,path,value', [
    ('observation', 'version', 1),
    ('observation', 'version', True),
    ('observation', 'session_id', '00000000-0000-4000-8000-000000000099'),
    ('binding', 'attempt_id', 'other'),
    ('genesis', 'sequence', 1),
    ('session_bound', 'previous_record_sha256', '1' * 64),
])
def test_checkpoint_chain_is_not_accepted_from_rehashed_documents(initial_v1, node, path, value):
    refuses(selected_case(initial_v1, mutations={node: set_field(path, value)}))


def test_default_execution_cannot_adopt_initialized_v2(initial_v1):
    old_dependencies = deepcopy(initial_v1['live'].value['dependencies'])
    case = selected_case(initial_v1, mutations={
        'execution': set_field('dependencies', old_dependencies)})
    refuses(case, match='selected saved owner')


def test_supplied_execution_uses_typed_canonical_equality(initialized_case):
    value = deepcopy(initialized_case['value'])
    assert type(value['version']) is int and value['version'] == 1
    value['version'] = 1.0
    assert value == initialized_case['value']  # Python equality is insufficient.
    refuses(initialized_case, value=value, match='typed value')


def test_reader_rebuilds_complete_selection_before_using_projected_bounds(initialized_case):
    case = initialized_case
    bounds = case['selection'].bounds()
    bounds['max_submissions'] -= 1
    # The real carrier already closes this easy projection gap. Keep that
    # refusal at its actual constructor boundary (#4722), without bypassing it.
    with pytest.raises(ValueError, match='selection carrier disagrees'):
        replace(case['selection'], bounds_json=c.canonical(bounds))
    # A complete, internally valid captured artifact can still disagree with
    # the registered pool. That deeper projection reaches Reader's rebuild.
    original = next(item for item in case['selection'].authority if item.pin.role == 'bundle')
    changed = artifact('bundle', original.pin.path, original.raw + b'\nDifferent captured source.\n')
    projected = replace(case['selection'], authority=tuple(
        changed if item is original else item for item in case['selection'].authority))
    assert projected.registration == case['selection'].registration
    assert projected.bounds() == case['selection'].bounds()
    assert projected.authority != case['selection'].authority
    with pytest.raises(ValueError, match='complete captured reconstruction'):
        capture._Reader(projected, pool=case['pool'], execution=case['artifacts']['execution'])


def test_reader_rejects_an_unpooled_but_valid_execution_artifact(initialized_case):
    case = initialized_case
    changed = deepcopy(case['value'])
    changed['unused_claim'] = 'not present in captured execution'
    item = artifact('execution_capture', case['artifacts']['execution'].pin.path, c.canonical(changed))
    with pytest.raises(ValueError, match='unique captured pool member'):
        capture._Reader(case['selection'], pool=case['pool'], execution=item)


@pytest.mark.parametrize('role', ['owner', 'execution_capture', 'receipt_policy'])
def test_missing_required_pool_member_refuses(initialized_case, role):
    case = initialized_case
    target = pool_member(case['pool'], role)
    pool = evidence.CapturePool(tuple(row for row in case['pool'].members if row is not target),
                                case['pool'].stream_bindings)
    refuses(case, pool=pool)


@pytest.mark.parametrize('role', ['owner', 'execution_capture'])
def test_distinct_pool_versions_at_same_required_path_refuse(initialized_case, role):
    case = initialized_case
    old = pool_member(case['pool'], role)
    extra = member(artifact(role, old.captured.pin.path, old.captured.raw + b'\n'), old)
    pool = evidence.CapturePool(case['pool'].members + (extra,), case['pool'].stream_bindings)
    assert len(pool.members) == len(case['pool'].members) + 1
    refuses(case, pool=pool)


@pytest.mark.parametrize('role,path_key,filename', [
    ('observation', 'observations_root', '000001.json'),
    ('record', 'journal_records_root', '000002.json'),
    ('request', 'stage_root', 'later-request.json'),
])
def test_later_or_unrecognized_members_are_not_dropped(initialized_case, role, path_key, filename):
    case = initialized_case
    extra = member(artifact(role, Path(case['selection'].role(path_key)) / filename, b'{}'))
    pool = evidence.CapturePool(case['pool'].members + (extra,), case['pool'].stream_bindings)
    refuses(case, pool=pool, match='one-observation/two-record pool')


@pytest.mark.parametrize('hidden_by_prefix', [False, True])
def test_additional_actual_stream_rows_cannot_gain_initialization_credit(initial_v1, hidden_by_prefix):
    old = pool_member(initial_v1['pool'], 'transcript')
    extra = c.canonical({'type': 'result', 'session_id': initial_v1['live'].binding.session_id}) + b'\n'
    changed = member(artifact('transcript', old.captured.pin.path, old.captured.raw + extra), old)
    mutations = {}
    if hidden_by_prefix:
        def shorten(doc):
            doc['transcript_prefix'].update(through_bytes=len(old.captured.raw),
                lines=old.captured.raw.count(b'\n'), sha256=c.sha(old.captured.raw))
        mutations['observation'] = shorten
    case = selected_case(initial_v1, streams={'transcript': changed}, mutations=mutations)
    refuses(case, match='complete captured streams|additional stream rows')


def test_stream_binding_cannot_substitute_same_path_new_inode(initialized_case):
    case = initialized_case
    old = pool_member(case['pool'], 'control')
    metadata = c.strict_json(old.metadata_json)
    metadata['inode'] += 1
    changed = evidence.PoolMember(old.captured, c.canonical(metadata))
    pool = replace_pool_member(case['pool'], old, changed)
    refuses(case, pool=pool, match='physical identities')


def trap_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('saved structural evidence attempted live I/O or source/clock admission')
    for name in ('read_bytes', 'read_text', 'open', 'resolve', 'stat', 'lstat', 'write_bytes', 'write_text'):
        monkeypatch.setattr(Path, name, forbidden)
    monkeypatch.setattr(builtins, 'open', forbidden)
    for name in ('open', 'read', 'write', 'stat', 'lstat', 'fstat', 'getpid'):
        monkeypatch.setattr(os, name, forbidden)
    monkeypatch.setattr(fcntl, 'flock', forbidden)
    for name in ('monotonic', 'monotonic_ns'):
        monkeypatch.setattr(time, name, forbidden)
    monkeypatch.setattr(evidence, 'read_regular', forbidden)
    monkeypatch.setattr(streams, 'read_live_stream', forbidden)
    monkeypatch.setattr(authority, 'dependency_identity', forbidden)
    monkeypatch.setattr(authority, 'require_committed', forbidden)
    monkeypatch.setattr(authority, 'loaded_dependencies', forbidden)
    monkeypatch.setattr(profile, 'source_profile', forbidden)
    monkeypatch.setattr(controller, 'load_controls', forbidden)
    monkeypatch.setattr(clocks, 'capture_domain', forbidden)
    monkeypatch.setattr(clocks, '_capture', forbidden)
    return forbidden


def test_relocated_saved_pool_rebuilds_with_original_files_unavailable(initialized_case, tmp_path, monkeypatch):
    case = initialized_case
    destination = tmp_path / 'relocated-pool.json'
    destination.write_bytes(case['pool'].encode())
    saved = evidence.decode(destination.read_bytes())
    expected = results.rebuild(saved, case['value']).as_dict()
    # Temporarily remove only fixture-owned captured files, retaining their
    # exact bytes. Restoration in finally preserves the original v1 fixture.
    root = tmp_path.resolve()
    originals = {}
    for name in case['baseline']['original_files']:
        path = Path(name)
        if root in path.parents and path.is_file():
            originals[path] = path.read_bytes()
            path.unlink()
    assert originals
    try:
        with monkeypatch.context() as patch:
            trap_io(patch)
            actual = results.rebuild(saved, deepcopy(case['value'])).as_dict()
        assert actual == expected
    finally:
        for path, raw in originals.items():
            path.write_bytes(raw)


@pytest.mark.parametrize('consumer', [
    'seal', 'request', 'intent', 'written', 'settled', 'persist', 'effect',
    'decision_effect', 'receipt', 'provenance', 'publish_stage', 'publish_derived', 'write_report',
])
def test_detached_evidence_refuses_effect_consumers_before_io(initialized_case, monkeypatch, consumer):
    case = initialized_case
    saved = results.rebuild(case['pool'], case['value'])
    calls = {
        'seal': lambda: capture.seal_originals(saved, 'seal_phase1'),
        'request': lambda: capture.observe_request_read(saved, None),
        'intent': lambda: capture.observe_response_intent(saved, None),
        'written': lambda: capture.observe_response_written(saved, None),
        'settled': lambda: capture.observe_advance_settled(saved, None),
        'persist': lambda: capture._persist_observation(saved, 'initialized', {}),
        'effect': lambda: capture.current_effect_view(saved),
        'decision_effect': lambda: capture._effect_view_from_decision(saved, None),
        'receipt': lambda: capture._receipt_assessment(saved, full_path='/not-read', receipt_path='/not-read'),
        'provenance': lambda: capture._provenance_block(saved),
        'publish_stage': lambda: capture.publish_stage(saved, None),
        'publish_derived': lambda: publication.publish_derived(saved, None),
        'write_report': lambda: results.write_report(saved, '/not-written'),
    }
    with monkeypatch.context() as patch:
        forbidden = trap_io(patch)
        patch.setattr(capture, '_create', forbidden)
        patch.setattr(capture, '_append', forbidden)
        patch.setattr(publication, 'durable_new', forbidden)
        patch.setattr(publication, 'read_regular', forbidden)
        with pytest.raises(ValueError):
            calls[consumer]()


@pytest.mark.parametrize('consumer', ['prepare', 'saved_no_report', 'saved_report', 'files'])
def test_selected_full_result_routes_refuse_before_any_live_basis(initialized_case, monkeypatch, consumer):
    case = initialized_case
    calls = {
        'prepare': lambda: results.prepare(case['pool'], case['value'], None),
        'saved_no_report': lambda: results.require_saved_basis(case['value'],
            {'additional_report': None, 'runtime_gates_passed': False, 'gates': {'receipts': {}}}),
        'saved_report': lambda: results.require_saved_basis(case['value'],
            {'additional_report': {'passed': True}, 'runtime_gates_passed': True, 'gates': {'receipts': {}}}),
        'files': lambda: results.validate_file_basis(case['value'], {'captured_files': {'/not-read': {}}}),
    }
    with monkeypatch.context() as patch:
        trap_io(patch)
        with pytest.raises(ValueError, match='initialization-only'):
            calls[consumer]()


@pytest.mark.parametrize('consumer', ['block', 'claims'])
def test_actual_recorded_route_rejects_selected_execution_before_receipt_assessment(initialized_case, consumer):
    case = initialized_case
    live = case['baseline']['live']
    record = {'prompts': {'request': {'spec': deepcopy(live.composition['render_spec'])}}}
    def consume():
        options = {'record': record, 'full_path': '/not-assessed', 'receipt_path': '/not-assessed'}
        if consumer == 'block':
            return capture.recorded_receipt_block(live.spec, **options)
        return capture.recorded_receipt_claims(live.spec, expected_block={}, **options)

    # The legitimate baseline passes the actual record/render/load route and
    # reaches its ordinary incomplete-checkpoint refusal. No verifier is patched.
    with pytest.raises(ValueError, match='native provenance requires complete'):
        consume()
    target = Path(case['selection'].role('execution_capture'))
    original = target.read_bytes()
    assert original == live.binding.execution.raw
    # Explicit fixture-only exception to byte preservation during the call:
    # place the private selected E at the actual captured role, then restore it.
    # This does not claim unchanged filesystem metadata or publish a native run.
    try:
        target.write_bytes(case['artifacts']['execution'].raw)
        with pytest.raises(ValueError, match='execution registration differs from its selected authorities'):
            consume()
    finally:
        target.write_bytes(original)
    assert target.read_bytes() == original
