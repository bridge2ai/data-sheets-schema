"""Actual ordinary runner/publication with synthetic private captured authority.

The same pre-execution E/C/S/started bytes bind the real owner and terminal
files. No native/provider or public execution admission is supplied or patched.
"""
from copy import deepcopy
import builtins
import fcntl
import os
from pathlib import Path
import subprocess
import time

import pytest

from data_sheets_schema import native_attribution_controller as inherited
from data_sheets_schema import native_clock_domain_v1 as clocks
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_owner_runner_v1 as runner_module
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_registration as registration
from data_sheets_schema import native_shared_results as results
from data_sheets_schema import native_shared_selection as selections
from tests.test_native_shared_selection import declaration
from tests.test_native_owner_runner import fixed_clock, selected_controls
from tests.test_native_owner_worker_scope import make_worker_case, rehash_worker_case


TERMINAL_ROLES = (
    ('owner', 'stream-owner.json', 16_384),
    ('owner_stop', 'stream-owner-stop.json', 16_384),
    ('owner_runner_report', 'stream-owner-result.json', 16_384),
    ('owner_close', 'stream-owner-close.json', 16_384),
    ('owner_failure', 'stream-owner-failure.json', 16_384),
    ('owner_control_record', 'stream-owner-control-record.bin', 16_777_216),
    ('owner_worker_clock_close', 'stream-owner-worker-clock-close.json', 16_384),
    ('owner_transcript_suffix', 'stream-owner-transcript-suffix.bin', 384_000_000),
)
RETENTION = ('owner_retention', 'stream-owner-retention.json', 65_536)


def raw_pin(raw):
    return {'bytes': len(raw), 'sha256': c.sha(raw)}


def make_terminal_case(root, controls, selection):
    """Unexecuted case with full real S and one coherent synthetic C/E chain."""
    case = make_worker_case(root, controls, selection)
    runtime_raw = c.canonical(case['execution']['runtime'])
    case['composition'].update(
        controller_sources=deepcopy(inherited.controller_sources()),
        controller_sources_sha256=inherited.SOURCES_SHA256,
        runtime_raw_json=runtime_raw.decode('utf-8'), runtime_sha256=c.sha(runtime_raw))
    case['execution']['runtime_declaration_sha256'] = c.sha(runtime_raw)
    rehash_worker_case(case)
    # These are private fixture associations, not activation/public registration.
    captured_inputs = {}
    for role, key in (('execution_capture', 'execution_raw'), ('started_capture', 'started_raw')):
        path = Path(selection.role(role))
        path.parent.mkdir(parents=True, exist_ok=True)
        assert not path.exists()
        raw = case['kwargs'][key]
        path.write_bytes(raw)
        captured_inputs[role] = evidence.read_regular(str(path), role, max_bytes=len(raw))
    authorities = (selection.registration, selection.receipt_policy, *selection.authority,
                   *(item for schema in selection.schemas for item in schema.sources))
    captured_authorities = tuple(evidence.read_regular(item.pin.path, item.pin.role,
                                                      max_bytes=item.pin.bytes)
                                 for item in authorities)
    case.update(execution_raw=case['kwargs']['execution_raw'],
                started_raw=case['kwargs']['started_raw'],
                captured_inputs=captured_inputs, captured_authorities=captured_authorities,
                terminal_paths={role: case['attempt'] / name
                                for role, name, _limit in (*TERMINAL_ROLES, RETENTION)})
    return case


@pytest.fixture
def terminal_case(declaration, selected_controls, tmp_path):
    selection = selections.capture(declaration['registration_path'])
    return make_terminal_case(tmp_path.resolve() / 'terminal-case', selected_controls, selection)


def execute_case(case):
    """Normal path only; failure tests must assert their exact raised error."""
    assert case['runner'].execute_child(**case['kwargs']) == 0
    assert case['runner'].report()['state'] == 'completed'
    return case


def capture_terminal_pool(case):
    """Read actual declared retained/owned-partial files, never ambient extras."""
    path = case['terminal_paths']['owner_retention']
    manifest_member = evidence.read_regular(str(path), 'owner_retention', max_bytes=RETENTION[2])
    manifest = c.strict_json(manifest_member.captured.raw, 'fixture terminal manifest', RETENTION[2])
    assert [row['role'] for row in manifest['roles']] == [row[0] for row in TERMINAL_ROLES]
    members = [*case['captured_authorities'], *case['captured_inputs'].values(), manifest_member]
    for row, (role, name, maximum) in zip(manifest['roles'], TERMINAL_ROLES):
        expected_path = str(case['attempt'] / name)
        assert row['path'] == expected_path
        retained = row['retained'] if row['state'] == 'retained' else None
        partial = row['observed_partial'] if row['state'] == 'publication_failed' else None
        if retained is None and partial is None:
            continue
        assert (retained is None) != (partial is None)
        declared = retained if retained is not None else partial
        member = evidence.read_regular(expected_path, role, max_bytes=maximum)
        assert raw_pin(member.captured.raw) == declared['pin']
        assert c.strict_json(member.metadata_json) == declared['metadata']
        if partial is not None:
            write = row['write']
            assert write['attempted'] is True and write['owned_create'] is True
            assert {key: declared['metadata'][key] for key in ('device', 'inode')} == write['identity']
        members.append(member)
    assert len({(m.captured.pin.role, m.captured.pin.path) for m in members}) == len(members)
    return evidence.CapturePool(tuple(members), ())


def manifest_document(case):
    return c.strict_json(case['terminal_paths']['owner_retention'].read_bytes(),
                         'fixture terminal manifest', RETENTION[2])


def role_rows(document):
    rows = document['roles']
    assert len({row['role'] for row in rows}) == len(rows)
    return {row['role']: row for row in rows}


def trap_saved_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('saved terminal validation attempted live I/O or admission')
    for name in ('open', 'read_bytes', 'read_text', 'write_bytes', 'write_text', 'resolve', 'stat', 'lstat'):
        monkeypatch.setattr(Path, name, forbidden)
    monkeypatch.setattr(builtins, 'open', forbidden)
    for name in ('open', 'read', 'write', 'stat', 'lstat', 'fstat', 'getpid'):
        monkeypatch.setattr(os, name, forbidden)
    monkeypatch.setattr(fcntl, 'flock', forbidden)
    for name in ('monotonic', 'monotonic_ns'):
        monkeypatch.setattr(time, name, forbidden)
    for name in ('run', 'Popen', 'check_output'):
        monkeypatch.setattr(subprocess, name, forbidden)
    monkeypatch.setattr(evidence, 'read_regular', forbidden)
    for name in ('dependency_identity', 'require_committed', 'loaded_dependencies'):
        monkeypatch.setattr(authority, name, forbidden)
    monkeypatch.setattr(profile, 'source_profile', forbidden)
    monkeypatch.setattr(clocks, 'capture_domain', forbidden)
    monkeypatch.setattr(clocks, '_capture', forbidden)
    return forbidden


def test_same_actual_runner_publication_validates_complete_terminal_closure(terminal_case):
    case = terminal_case
    original_inputs = {row.captured.pin.path: row.captured.raw for row in
                       (*case['captured_authorities'], *case['captured_inputs'].values())}
    expected_instruction = case['instruction'].read_bytes()
    execute_case(case)
    original_report = case['runner'].report()
    original_owner = case['runner'].owner_raw()
    snapshot = case['runner'].terminal_snapshot()
    assert type(snapshot) is tuple and len(snapshot) == 2
    projection_raw, payload_pairs = snapshot
    assert type(projection_raw) is bytes and type(payload_pairs) is tuple
    assert all(type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str
               and type(pair[1]) is bytes for pair in payload_pairs)
    assert len({role for role, _raw in payload_pairs}) == len(payload_pairs)
    payloads = dict(payload_pairs)
    projection = c.strict_json(projection_raw)
    assert projection_raw == c.canonical(projection)
    assert projection['format'] == 'native_owner_terminal_snapshot_v1'
    assert projection['runner_report'] == raw_pin(payloads['owner_runner_report'])
    assert projection['close_report'] == raw_pin(payloads['owner_close'])
    assert projection['failure_summary'] is None and projection['failed_members'] == {}
    assert payloads['owner'] == original_owner
    assert c.strict_json(payloads['owner_runner_report']) == original_report
    assert c.strict_json(payloads['owner_close']) == original_report['control_close']
    owner = c.strict_json(original_owner)
    assert owner['execution_sha256'] == c.sha(case['execution_raw'])
    assert owner['started_sha256'] == c.sha(case['started_raw'])
    assert (case['root'] / 'received-instruction.txt').read_bytes() == expected_instruction

    assert case['runner'].terminal_publication_report() is None
    published = case['runner'].publish_terminal()
    assert published['format'] == 'native_owner_terminal_publication_v1'
    assert published['state'] == 'published' and published['error'] is None
    assert published['manifest_finalized'] is True and published['retention_complete'] is True
    assert published['execution_authorized'] is False and published['native_acceptance'] == 'not_assessed'
    manifest = manifest_document(case)
    rows = role_rows(manifest)
    assert tuple(rows) == tuple(row[0] for row in TERMINAL_ROLES)
    assert manifest['scope'] == 'terminal_retention_only'
    assert manifest['runner_report'] == raw_pin(payloads['owner_runner_report'])
    assert manifest['identities'] == {
        'selection_sha256': case['selection'].registration.pin.sha256,
        'execution_sha256': c.sha(case['execution_raw']),
        'composition_sha256': case['execution']['composition_sha256'],
        'started_sha256': c.sha(case['started_raw']), 'owner_sha256': c.sha(original_owner),
        'profile': case['profile']}
    for role in ('owner', 'owner_stop', 'owner_runner_report', 'owner_close'):
        assert rows[role]['state'] == 'retained'
    for role in ('owner_failure', 'owner_control_record', 'owner_worker_clock_close',
                 'owner_transcript_suffix'):
        assert rows[role]['state'] == 'not_produced'
        assert not case['terminal_paths'][role].exists()
    assert manifest['counts'] == {
        'retained_members': 4,
        'retained_bytes': sum(row['retained']['pin']['bytes'] for row in rows.values()
                              if row['state'] == 'retained'),
        'observed_partial_members': 0, 'observed_partial_bytes': 0}
    pool = capture_terminal_pool(case)
    encoded = pool.encode()
    assert evidence.decode(encoded) == pool
    raw = runner_module.validate_terminal_capture(evidence.decode(encoded), deepcopy(case['execution']))
    assert type(raw) is bytes
    saved = c.strict_json(raw)
    assert raw == c.canonical(saved)
    assert set(saved) == {'format', 'scope', 'identities', 'roles', 'counts',
        'captured_manifest_complete', 'publisher_completion_attested', 'retention_complete',
        'execution_authorized', 'native_acceptance'}
    assert saved['format'] == 'native_owner_terminal_evidence_v1'
    assert saved['scope'] == 'terminal_retention_only'
    assert saved['identities'] == manifest['identities'] and saved['roles'] == manifest['roles']
    assert saved['counts'] == {'members': len(pool.members),
        'raw_bytes': sum(len(row.captured.raw) for row in pool.members), **manifest['counts']}
    assert saved['captured_manifest_complete'] is True
    assert saved['publisher_completion_attested'] is False
    assert saved['retention_complete'] is True
    assert saved['execution_authorized'] is False and saved['native_acceptance'] == 'not_assessed'
    assert not any(row.captured.pin.role in ('transcript', 'control', 'session_binding',
                   'observation', 'journal', 'record') for row in pool.members)
    assert case['runner'].report() == original_report
    assert case['runner'].owner_raw() == original_owner
    assert case['runner'].terminal_snapshot() == snapshot
    assert {path: Path(path).read_bytes() for path in original_inputs} == original_inputs


def test_terminal_ready_boundary_and_detached_accessors(terminal_case):
    case = terminal_case
    with pytest.raises(ValueError):
        case['runner'].terminal_snapshot()
    seen = []
    def during_execution():
        # The owner already exists, but cleanup/report freeze has not happened.
        assert case['runner'].owner_raw() is not None
        with pytest.raises(ValueError):
            case['runner'].terminal_snapshot()
        seen.append(True)
    case['kwargs']['verify_launch'] = during_execution
    execute_case(case)
    assert seen == [True]
    snapshot = case['runner'].terminal_snapshot()
    report = case['runner'].report()
    report['cleanup_errors'].append({'invented': True})
    projection = c.strict_json(snapshot[0])
    projection['lifecycle']['owner_create_completed'] = False
    projection['failed_members']['invented'] = raw_pin(b'invented')
    payloads = dict(snapshot[1])
    payloads['owner'] = b'invented'
    assert case['runner'].terminal_snapshot() == snapshot
    assert case['runner'].report()['cleanup_errors'] == []
    published = case['runner'].publish_terminal()
    expected = deepcopy(published)
    published['roles'].clear()
    published['manifest_finalized'] = False
    again = case['runner'].terminal_publication_report()
    assert again == expected
    again['roles'][0]['state'] = 'invented'
    assert case['runner'].terminal_publication_report() == expected
    assert case['runner'].terminal_snapshot() == snapshot


def test_successful_publication_spends_call_before_further_io(terminal_case, monkeypatch):
    case = execute_case(terminal_case)
    expected = case['runner'].publish_terminal()
    snapshot = case['runner'].terminal_snapshot()
    with monkeypatch.context() as patch:
        trap_saved_io(patch)
        with pytest.raises(ValueError):
            case['runner'].publish_terminal()
        assert case['runner'].terminal_snapshot() == snapshot
        assert case['runner'].terminal_publication_report() == expected


@pytest.mark.parametrize('name', ['stream-owner.json', 'stream-owner-stop.json'])
def test_prelaunch_collision_never_grants_owner_or_publication(terminal_case, monkeypatch, name):
    case = terminal_case
    path = case['attempt'] / name
    sentinel = b'foreign prelaunch file; not this runner owner'
    path.write_bytes(sentinel)
    with pytest.raises(ValueError, match='destination already exists'):
        case['runner'].execute_child(**case['kwargs'])
    report = case['runner'].report()
    assert report['state'] == 'failed' and report['dispatches'] == 0
    assert report['owner_published'] is False
    assert case['runner'].owner_raw() is None
    snapshot = case['runner'].terminal_snapshot()
    assert c.strict_json(snapshot[0])['lifecycle']['owner_create_completed'] is False
    with monkeypatch.context() as patch:
        trap_saved_io(patch)
        with pytest.raises(ValueError):
            case['runner'].publish_terminal()
        published = case['runner'].terminal_publication_report()
        assert published['state'] == 'refused'
        assert published['manifest_finalized'] is False
        assert published['roles'] == []
        assert case['runner'].report() == report
        assert case['runner'].terminal_snapshot() == snapshot
    assert path.read_bytes() == sentinel
    assert sorted(p.name for p in case['attempt'].iterdir()) == [name]


def test_publication_after_real_loader_exit_needs_no_new_authority(declaration, fixed_clock,
                                                                 tmp_path, monkeypatch):
    # Own the real context; never invalidate a shared fixture's active scope.
    selection = selections.capture(declaration['registration_path'])
    identity = authority.dependency_identity(stream_snapshot_profile=1)
    with authority.loaded_dependencies(identity) as controls:
        case = make_terminal_case(tmp_path.resolve() / 'released-context', controls, selection)
        execute_case(case)
    def forbidden(*args, **kwargs):
        raise AssertionError('diagnostic publication acquired new execution authority')
    for name in ('dependency_identity', 'require_committed', 'loaded_dependencies'):
        monkeypatch.setattr(authority, name, forbidden)
    monkeypatch.setattr(profile, 'source_profile', forbidden)
    monkeypatch.setattr(clocks, 'capture_domain', forbidden)
    monkeypatch.setattr(clocks, '_capture', forbidden)
    for name in ('run', 'Popen', 'check_output'):
        monkeypatch.setattr(subprocess, name, forbidden)
    assert case['runner'].publish_terminal()['manifest_finalized'] is True


def test_relocated_terminal_bytes_validate_without_original_paths(terminal_case, tmp_path, monkeypatch):
    case = execute_case(terminal_case)
    case['runner'].publish_terminal()
    pool = capture_terminal_pool(case)
    expected = runner_module.validate_terminal_capture(pool, case['execution'])
    relocated = tmp_path / 'relocated-terminal.json'
    relocated.write_bytes(pool.encode())
    saved = evidence.decode(relocated.read_bytes())
    root = tmp_path.resolve()
    originals = {}
    for row in pool.members:
        path = Path(row.captured.pin.path)
        if root in path.parents and path.is_file():
            originals[path] = path.read_bytes()
            path.unlink()
    assert originals and case['terminal_paths']['owner_retention'] in originals
    try:
        with monkeypatch.context() as patch:
            trap_saved_io(patch)
            actual = runner_module.validate_terminal_capture(saved, deepcopy(case['execution']))
        assert actual == expected
    finally:
        # Exact fixture bytes restored; no inode/mtime preservation is claimed.
        for path, raw in originals.items():
            path.write_bytes(raw)


def test_terminal_pool_never_becomes_public_or_initialized_authority(terminal_case):
    case = terminal_case
    with pytest.raises(ValueError):
        registration.verified(case['execution_raw'])
    execute_case(case)
    case['runner'].publish_terminal()
    pool = capture_terminal_pool(case)
    with pytest.raises(ValueError):
        results.rebuild(pool, case['execution'])
    assert c.strict_json(runner_module.validate_terminal_capture(pool, case['execution']))[
        'scope'] == 'terminal_retention_only'


@pytest.mark.parametrize('role', ['transcript', 'control'])
def test_terminal_only_denominator_rejects_actual_stream_extras(terminal_case, role):
    case = execute_case(terminal_case)
    case['runner'].publish_terminal()
    pool = capture_terminal_pool(case)
    path = case['attempt'] / (role + '.jsonl')
    extra = evidence.read_regular(str(path), role, max_bytes=c.HARD_LIMITS['stream_bytes'])
    expanded = evidence.CapturePool(pool.members + (extra,), ())
    assert len(expanded.members) == len(pool.members) + 1
    with pytest.raises(ValueError):
        runner_module.validate_terminal_capture(expanded, case['execution'])
