"""Selected authority survives the complete writer footprint (#4364)."""
import os
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner as api, run_lock, shared_generation as sg
from data_sheets_schema import shared_write_footprint as footprint, usage_ledger as ledger
from data_sheets_schema import resources, schema_digest
from tests.test_generation_manifest_identity import external
from tests.test_shared_generation_cli import registered, roster, batch, stub_plan
from tests.test_shared_generation_selection import selected_spec
from tests.test_shared_generation_batch_authority import authority_bytes


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})
    assert Path(api.__file__).resolve().parents[1] == Path(__file__).resolve().parents[1] / 'src'


def unchanged(before):
    assert {path: path.read_bytes() for path in before} == before


def traps(monkeypatch):
    calls = []
    def forbidden(*args, **kwargs):
        calls.append('write-or-dispatch')
        raise AssertionError('write or provider dispatch before isolation')
    monkeypatch.setattr(api, '_exclusive_run', forbidden)
    monkeypatch.setattr(api, '_client', forbidden)
    monkeypatch.setattr(run_lock, 'acquire', forbidden)
    monkeypatch.setattr(run_lock, 'release', forbidden)
    return calls


@pytest.mark.parametrize('alias', ['exact', 'hardlink', 'symlink'])
def test_actual_batch_refuses_roster_lock_before_any_writer(registered, monkeypatch, alias):
    base, reg = registered
    old, rows = roster(base, reg)
    lock = run_lock._path_for('shared')
    lock.parent.mkdir(parents=True)
    if alias == 'exact':
        lock.write_bytes(old.read_bytes())
        path = lock
    else:
        path = old
        if alias == 'hardlink':
            os.link(path, lock)
        else:
            lock.symlink_to(path)
    before = authority_bytes(path, rows)
    calls = traps(monkeypatch)
    monkeypatch.setattr(api, 'plan', lambda *a: pytest.fail('collision reached plan'))
    monkeypatch.setattr(api, 'execute', lambda *a: pytest.fail('collision reached execute'))
    result = batch(reg, path)
    assert result.exit_code == 1 and 'aliases a run output' in result.output, result.output
    assert calls == [] and lock.exists()
    unchanged(before)


def test_public_execute_refuses_progress_context_alias_before_run_locks(registered, monkeypatch):
    base, reg = registered
    spec = selected_spec(base, reg)
    capture = sg.capture(spec)
    before = {Path(path): raw for path, raw in capture.files}
    source = Path(reg['inputs']['context']['path'])
    progress = api._progress_path(spec)
    progress.parent.mkdir(parents=True)
    os.link(source, progress)
    calls = traps(monkeypatch)
    with pytest.raises(ValueError, match='aliases a run output'):
        api.execute(spec)
    assert calls == [] and source.samefile(progress)
    unchanged(before)


def test_registered_asset_copy_is_protected_even_outside_capture_files(registered, tmp_path, monkeypatch):
    base, reg = registered
    original = resources.resource_path
    copies = {}
    for index, name in enumerate(sg.ASSET_HASHES):
        copy = tmp_path / f'asset-{index}.txt'
        copy.write_bytes(original(name).read_bytes())
        copies[name] = copy
    monkeypatch.setattr(resources, 'resource_path', lambda path: copies.get(str(path), original(path)))
    spec = selected_spec(base, reg)
    capture = sg.capture(spec)
    source = copies[sg.POLICY]
    assert str(source) not in dict(capture.files)
    before = {Path(path): raw for path, raw in capture.files}
    before.update({path: path.read_bytes() for path in copies.values()})
    progress = api._progress_path(spec)
    progress.parent.mkdir(parents=True)
    os.link(source, progress)
    calls = traps(monkeypatch)
    with pytest.raises(ValueError, match='aliases a run output'):
        api.execute(spec)
    assert calls == []
    unchanged(before)


def test_batch_rechecks_auxiliary_alias_introduced_after_plan(registered, monkeypatch):
    base, reg = registered
    path, rows = roster(base, reg)
    before = authority_bytes(path, rows)
    calls = traps(monkeypatch)
    plans = []
    source = Path(reg['inputs']['context']['path'])
    def plan(spec):
        result = stub_plan(spec)
        plans.append(spec.label)
        if spec.label == 'shared_rep2':
            destination = api._reasoning_path(spec)
            destination.parent.mkdir(parents=True)
            os.link(source, destination)
        return result
    monkeypatch.setattr(api, 'plan', plan)
    monkeypatch.setattr(api, 'execute', lambda *a: pytest.fail('collision reached execute'))
    result = batch(reg, path)
    assert plans == ['shared_rep1', 'shared_rep2']
    assert result.exit_code == 1 and 'aliases a run output' in result.output, result.output
    assert calls == []
    unchanged(before)


def simple(tmp_path):
    return SimpleNamespace(metadata_dir=tmp_path / 'core', full_path=tmp_path / 'full' / 'EX_d4d.yaml',
        core_path=tmp_path / 'core' / 'EX_d4d_core.yaml', report_path=tmp_path / 'core' / 'EX_report.md',
        provenance_path=tmp_path / 'core' / 'EX_provenance.yaml')


def source(tmp_path):
    path = tmp_path / 'authority.json'
    path.write_bytes(b'{"private": "untouched"}\n')
    return path


@pytest.mark.parametrize('name', ['EX_api_progress.json', 'EX_reasoning.jsonl',
    'EX_abandoned_attempts.jsonl', 'EX_coverage_receipt.yaml', 'EX_api_usage_0123456789abcdef.json',
    'intermediate/EX_snapshot_index.json', 'intermediate/.future-hidden-journal'])
def test_existing_auxiliary_inodes_are_protected_without_filename_allowlist(tmp_path, name):
    spec = simple(tmp_path)
    authority = source(tmp_path)
    target = spec.metadata_dir / name
    target.parent.mkdir(parents=True)
    os.link(authority, target)
    with pytest.raises(ValueError, match='aliases a run output'):
        footprint.require_separate((authority,), (footprint.for_run(spec),))
    assert authority.read_bytes() == b'{"private": "untouched"}\n'


def test_resolved_primary_lock_sidecar_is_the_actual_writer_path(tmp_path):
    spec = simple(tmp_path)
    authority = source(tmp_path)
    actual = tmp_path / 'external' / 'record.yaml'
    actual.parent.mkdir()
    actual.write_text('id: https://example.org/record\n')
    spec.full_path.parent.mkdir()
    spec.full_path.symlink_to(actual)
    lock = dict(ledger.output_locks((spec.full_path,)))[actual]
    assert lock == actual.with_name('.record.yaml_api_run.lock')
    os.link(authority, lock)
    with pytest.raises(ValueError, match='aliases a run output'):
        footprint.require_separate((authority,), (footprint.for_run(spec),))
    assert authority.read_bytes() == b'{"private": "untouched"}\n'


def test_conditional_inventory_uses_actual_resource_resolution(tmp_path, monkeypatch):
    spec = simple(tmp_path)
    authority = source(tmp_path)
    inventory = tmp_path / 'external-inventory.yaml'
    os.link(authority, inventory)
    original = resources.resource_path
    monkeypatch.setattr(resources, 'resource_path', lambda path: inventory if path == schema_digest.INVENTORY_LEDGER else original(path))
    selected = footprint.for_run(spec)
    assert inventory in selected.points
    with pytest.raises(ValueError, match='aliases a run output'):
        footprint.require_separate((authority,), (selected,))
    assert authority.read_bytes() == b'{"private": "untouched"}\n'


def test_nested_directory_symlink_refuses_without_scanning_external_tree(tmp_path, monkeypatch):
    spec = simple(tmp_path)
    authority = source(tmp_path)
    external = tmp_path / 'unrelated-private-tree'
    external.mkdir()
    spec.metadata_dir.mkdir()
    (spec.metadata_dir / 'intermediate').symlink_to(external, target_is_directory=True)
    original = footprint.os.scandir
    def scan(path):
        assert Path(path).resolve() != external, 'external directory must never be scanned'
        return original(path)
    monkeypatch.setattr(footprint.os, 'scandir', scan)
    with pytest.raises(ValueError, match='nested directory symlink'):
        footprint.require_separate((authority,), (footprint.for_run(spec),))


def test_file_symlink_cannot_hide_authority_alias(tmp_path):
    spec = simple(tmp_path)
    authority = source(tmp_path)
    spec.metadata_dir.mkdir()
    (spec.metadata_dir / 'EX_reasoning.jsonl').symlink_to(authority)
    with pytest.raises(ValueError, match='aliases a run output'):
        footprint.require_separate((authority,), (footprint.for_run(spec),))


def test_broken_nested_link_is_not_treated_as_empty_namespace(tmp_path):
    spec = simple(tmp_path)
    authority = source(tmp_path)
    spec.metadata_dir.mkdir()
    (spec.metadata_dir / 'broken').symlink_to(tmp_path / 'missing')
    with pytest.raises(OSError):
        footprint.require_separate((authority,), (footprint.for_run(spec),))


@pytest.mark.parametrize('limit', ['entries', 'depth'])
def test_scan_bounds_refuse_without_truncating(tmp_path, monkeypatch, limit):
    spec = simple(tmp_path)
    authority = source(tmp_path)
    nested = spec.metadata_dir / 'one' / 'two'
    nested.mkdir(parents=True)
    (nested / '.ignored').write_text('retained')
    monkeypatch.setattr(footprint, 'MAX_ENTRIES' if limit == 'entries' else 'MAX_DEPTH', 1)
    with pytest.raises(ValueError, match='bound'):
        footprint.require_separate((authority,), (footprint.for_run(spec),))
    assert (nested / '.ignored').read_text() == 'retained'


def test_scan_error_is_not_treated_as_empty_namespace(tmp_path, monkeypatch):
    spec = simple(tmp_path)
    authority = source(tmp_path)
    spec.metadata_dir.mkdir()
    def refuse(path):
        raise PermissionError('synthetic unreadable directory')
    monkeypatch.setattr(footprint.os, 'scandir', refuse)
    with pytest.raises(PermissionError, match='unreadable'):
        footprint.require_separate((authority,), (footprint.for_run(spec),))


def test_shared_roots_and_top_level_aliases_preserve_read_only_inputs(tmp_path, monkeypatch):
    spec = simple(tmp_path)
    authority = source(tmp_path)
    spec.metadata_dir.mkdir()
    (spec.metadata_dir / 'first').write_text('one existing file')
    alias = tmp_path / 'allowed-root-link'
    alias.symlink_to(spec.metadata_dir, target_is_directory=True)
    selected = footprint.Footprint((spec.metadata_dir, alias, spec.metadata_dir / 'nested'), ())
    monkeypatch.setattr(footprint, 'MAX_ENTRIES', 1)
    # Duplicate authorities/roots do not imply multiple writes or a cycle.
    footprint.require_separate((authority, authority), (selected, selected))
    assert authority.read_bytes() == b'{"private": "untouched"}\n'


def test_fresh_footprint_and_unrelated_existing_files_are_allowed(tmp_path):
    spec = simple(tmp_path)
    authority = source(tmp_path)
    footprint.require_separate((authority,), (footprint.for_run(spec),))
    spec.metadata_dir.mkdir()
    (spec.metadata_dir / '.prior-evidence').write_text('kept')
    footprint.require_separate((authority,), (footprint.for_run(spec),))
