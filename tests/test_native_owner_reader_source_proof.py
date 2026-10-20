"""Fresh source proof for each private reader association; no native launch.

Purpose: guard the one-scan owner-reader integration for #4354, 2026-10-20.
Inputs: existing synthetic reader/clock fixtures and actual local source/Git.
Outputs: offline assertions only; no corpus, provider, or helper execution.
"""
from copy import deepcopy
import sys

import pytest

from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_owner_live_reader import (
    declaration, entered_case, fixed_clock, reader_case, selected_controls,
    sync_case,
)


def test_each_association_performs_one_fresh_scan_and_actual_git_proof(
        reader_case, monkeypatch):
    case = reader_case
    identity = authority.dependency_identity
    committed = authority.require_committed
    run = authority.subprocess.run
    scans, proofs, git_calls = [], [], []

    def scanned(*, stream_snapshot_profile=0):
        scans.append(stream_snapshot_profile)
        return identity(stream_snapshot_profile=stream_snapshot_profile)

    def proved(selected):
        proofs.append(deepcopy(selected))
        return committed(selected)

    def executed(args, *positional, **kwargs):
        if isinstance(args, (list, tuple)) and args[:2] == ['git', '--no-replace-objects']:
            if args[2] in ('ls-tree', 'cat-file'):
                git_calls.append(args[2])
        return run(args, *positional, **kwargs)

    monkeypatch.setattr(authority, 'dependency_identity', scanned)
    monkeypatch.setattr(authority, 'require_committed', proved)
    monkeypatch.setattr(authority.subprocess, 'run', executed)
    deadline = case['budget'].deadline_ns
    for count in (1, 2):
        with entered_case(case):
            pass
        assert scans == [1] * count
        assert proofs == [case['execution']['dependencies']] * count
        assert git_calls == ['ls-tree', 'cat-file'] * count
        assert case['budget'].deadline_ns == deadline


@pytest.mark.parametrize('change', [
    'missing', 'null', 'nonobject', 'v1', 'boolean_version', 'extra',
    'missing_profile', 'selected_profile', 'owner_profile',
])
def test_invalid_selected_identity_refuses_before_proof_or_owner_stream_reads(
        reader_case, monkeypatch, change):
    case = reader_case
    selected = case['execution']['dependencies']
    if change == 'missing':
        case['execution'].pop('dependencies')
    elif change == 'null':
        case['execution']['dependencies'] = None
    elif change == 'nonobject':
        case['execution']['dependencies'] = []
    elif change == 'v1':
        selected['version'] = 1
        selected.pop('stream_snapshot_profile')
    elif change == 'boolean_version':
        selected['version'] = True
    elif change == 'extra':
        selected['unexpected_authority'] = True
    elif change == 'missing_profile':
        selected.pop('stream_snapshot_profile')
    elif change == 'selected_profile':
        selected['stream_snapshot_profile']['implementations']['control']['sha256'] = '0' * 64
    else:
        case['owner']['coordination_profile']['implementations']['control']['sha256'] = '0' * 64
    sync_case(case)
    read = coordination.evidence.read_regular
    forbidden_paths = {str(case['owner_path']), *(str(path) for path in case['paths'].values())}

    def forbidden_proof(selected):
        pytest.fail('invalid selected envelope reached committed source proof')

    def checked_read(path, *args, **kwargs):
        if str(path) in forbidden_paths:
            pytest.fail('invalid selected envelope reached owner/stream I/O')
        return read(path, *args, **kwargs)

    monkeypatch.setattr(authority, 'require_committed', forbidden_proof)
    monkeypatch.setattr(coordination.evidence, 'read_regular', checked_read)
    with pytest.raises(ValueError):
        with entered_case(case):
            pytest.fail('invalid selected envelope reached an active reader')


@pytest.mark.parametrize('field', ['package_digest', 'source_commit', 'python_version'])
def test_honestly_rehashed_stale_source_identity_still_fails_the_fresh_scan(
        reader_case, monkeypatch, field):
    case = reader_case
    selected = case['execution']['dependencies']
    if field == 'package_digest':
        selected['base']['package_sources'][profile.RESOLVER_PATH] = '0' * 64
    elif field == 'source_commit':
        selected['base']['source_commit'] = '0' * 40
    else:
        selected['base']['python_version'] += ' stale declaration'
    sync_case(case)
    identity = authority.dependency_identity
    scans = []

    def scanned(*, stream_snapshot_profile=0):
        scans.append(stream_snapshot_profile)
        return identity(stream_snapshot_profile=stream_snapshot_profile)

    def forbidden_roster(*args, **kwargs):
        pytest.fail('stale source declaration reached Git proof before equality')

    monkeypatch.setattr(authority, 'dependency_identity', scanned)
    monkeypatch.setattr(authority, '_require_package_roster', forbidden_roster)
    with pytest.raises(ValueError, match='native execution dependency identity changed'):
        with entered_case(case):
            pytest.fail('stale source identity reached an active reader')
    assert scans == [1]


def test_failed_actual_git_roster_boundary_is_not_ignored(reader_case, monkeypatch):
    refusal = OSError('invented local Git roster read failure')
    def failed(*args, **kwargs):
        raise refusal
    monkeypatch.setattr(authority, '_require_package_roster', failed)
    with pytest.raises(OSError) as caught:
        with entered_case(reader_case):
            pytest.fail('failed Git proof reached an active reader')
    assert caught.value is refusal


@pytest.mark.parametrize('change', ['stop', 'qualified_origin'])
def test_final_scope_and_budget_are_rechecked_after_actual_source_proof(
        reader_case, monkeypatch, tmp_path, change):
    case = reader_case
    committed = authority.require_committed
    module = sys.modules[profile._MODULES['coordination']]
    original_file = module.__file__
    calls = []

    def proved_then_changed(selected):
        committed(selected)
        calls.append('proved')
        if change == 'stop':
            case['stop'].set()
        else:
            monkeypatch.setattr(module, '__file__', str(tmp_path / 'foreign-origin.py'))

    monkeypatch.setattr(authority, 'require_committed', proved_then_changed)
    try:
        with pytest.raises(ValueError):
            with entered_case(case):
                pytest.fail('changed final scope/budget reached an active reader')
        assert calls == ['proved']
    finally:
        case['stop'].clear()
        module.__file__ = original_file
