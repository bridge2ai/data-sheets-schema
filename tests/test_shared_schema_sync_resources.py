"""Actual owner read sets and safe entrypoint refusals over private resources."""
import os
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api, resources, schema_sync, schema_digest
from data_sheets_schema import shared_generation_resources as closure, provenance, run_lock, usage_ledger
from tests.test_shared_generation_cli import registered, external, roster, batch, module
from tests.test_shared_generation_selection import selected_spec
from tests.test_shared_generation_resources import offline, bytes_under, unchanged, schema_files
from tests.test_shared_output_ownership_entrypoints import no_execution


def private_raw_tree(tmp_path, monkeypatch):
    """Copy source bytes, including inventory; no source inode is ever aliased."""
    original = resources.resource_path
    source = original(provenance.SOURCE_SCHEMA)
    directory = tmp_path / 'private-raw'
    directory.mkdir()
    for path in source.parent.rglob('*.yaml'):
        target = directory / path.relative_to(source.parent)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    routed = {str(provenance.SOURCE_SCHEMA): directory / source.name,
              str(provenance.CORE_SOURCE_SCHEMA): directory / provenance.CORE_SOURCE_SCHEMA.name,
              str(schema_digest.INVENTORY_LEDGER): directory / schema_digest.INVENTORY_LEDGER.name}
    monkeypatch.setattr(resources, 'resource_path', lambda path: routed.get(str(path), original(path)))
    return directory


def append_import(root, imported):
    doc = yaml.safe_load(root.read_bytes())
    doc.setdefault('imports', []).append(imported)
    root.write_text(yaml.safe_dump(doc, sort_keys=False))


def extra_authority(directory, tmp_path, kind):
    root = directory / provenance.SOURCE_SCHEMA.name
    if kind == 'motivation':
        return directory / 'D4D_Motivation.yaml'
    if kind == 'unreferenced':
        path = directory / 'unreferenced.yaml'
        path.write_text('- deliberately not a schema\n')
    elif kind == 'ignored-descendant':
        path = directory / '.hidden' / 'extra.yaml'
        path.parent.mkdir()
        (directory / '.gitignore').write_text('*.yaml\n.hidden/\n')
        path.write_text('unparsed_sibling: true\n')
    elif kind == 'outside-import':
        path = tmp_path / 'outside.yaml'
        path.write_text('id: https://example.org/outside\nname: outside\n')
        append_import(root, '../outside')
    elif kind == 'package-alias':
        package = tmp_path / 'private-package'
        package.mkdir()
        path = package / 'module.yaml'
        path.write_text('id: https://example.org/package\nname: package\n')
        doc = yaml.safe_load(root.read_bytes())
        doc['prefixes']['probe'] = str(package) + '/'
        doc['imports'].append('probe:module')
        root.write_text(yaml.safe_dump(doc, sort_keys=False))
    else:
        assert kind == 'file-symlink'
        path = tmp_path / 'linked-module.yaml'
        path.write_text('id: https://example.org/linked\nname: linked\n')
        (directory / 'linked.yaml').symlink_to(path)
        append_import(root, 'linked')
    return path


@pytest.mark.parametrize('kind', ['motivation', 'unreferenced', 'ignored-descendant',
                                 'outside-import', 'package-alias', 'file-symlink'])
@pytest.mark.parametrize('entry', ['public', 'batch'])
def test_raw_dependency_refuses_before_actual_writers(registered, tmp_path, monkeypatch, kind, entry):
    base, reg = registered
    directory = private_raw_tree(tmp_path, monkeypatch)
    authority = extra_authority(directory, tmp_path, kind)
    spec = selected_spec(base, reg)
    if entry == 'public':
        destination = usage_ledger.output_locks((spec.full_path,))[0][1]
    else:
        roster_path, _ = roster(base, reg, count=1)
        destination = run_lock._path_for('shared')
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.link(authority, destination)
    before = bytes_under(tmp_path)
    seen = no_execution(monkeypatch)
    monkeypatch.setattr(api, 'plan', lambda *a: pytest.fail('raw alias reached plan'))
    if entry == 'public':
        with pytest.raises(ValueError, match='authority aliases a run output'):
            api.execute(spec)
    else:
        result = batch(reg, roster_path, count=1)
        assert result.exit_code == 1 and 'authority aliases a run output' in result.output, result.output
    assert seen == []
    unchanged(before)


def simple_sync(tmp_path, monkeypatch):
    directory = tmp_path / 'raw'
    directory.mkdir()
    root = directory / 'source.yaml'
    root.write_text('id: https://example.org/source\nname: source\n')
    merged = directory / 'merged.yaml'
    merged.write_text('synthetic_merged: true\n')
    monkeypatch.setattr(schema_sync, 'MERGED_SCHEMAS', ((merged, root, 'Dataset', False),))
    return root, merged


def test_complete_eager_and_external_set_equals_owner_snapshot(tmp_path, monkeypatch):
    root, merged = simple_sync(tmp_path, monkeypatch)
    extra = tmp_path / 'outside.yaml'
    extra.write_text('id: https://example.org/outside\nname: outside\n')
    append_import(root, '../outside')
    sibling = root.parent / 'not-a-schema.yaml'
    sibling.write_text('- unreferenced\n')
    hidden = root.parent / '.hidden' / 'ignored.yaml'
    hidden.parent.mkdir()
    hidden.write_text('not_schema: true\n')
    (root.parent / '.gitignore').write_text('*.yaml\n.hidden/\n')
    before = bytes_under(tmp_path)
    _state, owner = schema_sync._source_snapshot(root)
    assert {root, extra, sibling, hidden} == set(owner)
    assert set(closure.schema_sync_paths()) == set(owner) | {merged}
    unchanged(before)


def test_raw_root_alias_keeps_logical_import_and_siblings(tmp_path, monkeypatch):
    target, merged = simple_sync(tmp_path, monkeypatch)
    logical_dir = tmp_path / 'alias'
    logical_dir.mkdir()
    logical = logical_dir / target.name
    logical.symlink_to(target)
    append_import(target, 'extra')
    child = logical_dir / 'extra.yaml'
    child.write_text('id: https://example.org/logical\nname: logical\n')
    target_child = target.parent / 'extra.yaml'
    target_child.write_text('id: https://example.org/target\nname: target\n')
    monkeypatch.setattr(schema_sync, 'MERGED_SCHEMAS', ((merged, logical, 'Dataset', False),))
    _state, owner = schema_sync._source_snapshot(logical)
    assert set(owner) == {logical, child}
    assert set(closure.schema_sync_paths()) == {merged, logical, child}
    assert target_child not in closure.schema_sync_paths()


def test_namespace_order_matches_actual_source_snapshot(tmp_path, monkeypatch):
    root, imported = schema_files(tmp_path / 'schema', namespace=True)
    merged = root.parent / 'merged.yaml'
    merged.write_text('synthetic: true\n')
    monkeypatch.setattr(schema_sync, 'MERGED_SCHEMAS', ((merged, root, 'Dataset', False),))
    _state, owner = schema_sync._source_snapshot(root)
    assert imported in owner
    assert set(closure.schema_sync_paths()) == set(owner) | {merged}
    assert not any('unused' in path.parts for path in owner)


def test_nonmatching_directory_symlink_is_not_read_or_followed(tmp_path, monkeypatch):
    root, merged = simple_sync(tmp_path, monkeypatch)
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'secret.yaml').write_text('do not read\n')
    link = root.parent / 'ignored-directory'
    link.symlink_to(outside, target_is_directory=True)
    before = bytes_under(tmp_path)
    original_scan, original_open = os.scandir, os.open
    def scan(path):
        assert Path(path) not in (outside, link), 'followed directory symlink'
        return original_scan(path)
    def opened(path, *args, **kwargs):
        assert outside not in Path(path).parents and link not in Path(path).parents
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(os, 'scandir', scan)
    monkeypatch.setattr(os, 'open', opened)
    _state, owner = schema_sync._source_snapshot(root)
    assert set(owner) == {root}
    assert set(closure.schema_sync_paths()) == {merged, root}
    unchanged(before)


@pytest.mark.parametrize('symlink', [False, True])
def test_matching_yaml_directory_refuses_as_owner_read_does(tmp_path, monkeypatch, symlink):
    root, _merged = simple_sync(tmp_path, monkeypatch)
    bad = root.parent / 'directory.yaml'
    if symlink:
        target = tmp_path / 'directory-target'
        target.mkdir()
        bad.symlink_to(target, target_is_directory=True)
    else:
        bad.mkdir()
    with pytest.raises(OSError):
        schema_sync._source_snapshot(root)
    with pytest.raises((ValueError, OSError)):
        closure.schema_sync_paths()


def test_matching_file_symlink_is_an_eager_logical_point(tmp_path, monkeypatch):
    root, merged = simple_sync(tmp_path, monkeypatch)
    outside = tmp_path / 'ordinary.yaml'
    outside.write_text('- not an imported schema\n')
    link = root.parent / 'file.yaml'
    link.symlink_to(outside)
    _state, owner = schema_sync._source_snapshot(root)
    assert set(owner) == {root, link}
    assert set(closure.schema_sync_paths()) == {root, link, merged}


@pytest.mark.parametrize('missing', ['source', 'merged'])
def test_missing_owner_prerequisite_does_not_discover_snapshot(tmp_path, monkeypatch, missing):
    root, merged = simple_sync(tmp_path, monkeypatch)
    # Retain the old fixture, select a separately absent path instead.
    source = tmp_path / 'absent-source.yaml' if missing == 'source' else root
    artifact = tmp_path / 'absent-merged.yaml' if missing == 'merged' else merged
    monkeypatch.setattr(schema_sync, 'MERGED_SCHEMAS', ((artifact, source, 'Dataset', False),))
    monkeypatch.setattr(os, 'scandir', lambda *a: pytest.fail('missing prerequisite was scanned'))
    assert closure.schema_sync_paths() == (() if missing == 'merged' else (merged,))
    result = schema_sync.check_one(artifact, source, 'Dataset')
    assert result['status'] == (schema_sync.UNCHECKED if missing == 'source' else schema_sync.STALE)


def test_inventory_incidental_exception_does_not_hide_import_or_alias(tmp_path, monkeypatch):
    root, merged = simple_sync(tmp_path, monkeypatch)
    inventory = root.parent / 'digest_inventory.yaml'
    inventory.write_text('id: https://example.org/inventory\nname: inventory\n')
    monkeypatch.setattr(schema_digest, 'INVENTORY_LEDGER', inventory)
    assert set(closure.schema_sync_paths()) == {root, merged}
    alias = root.parent / 'inventory-alias.yaml'
    os.link(inventory, alias)
    assert set(closure.schema_sync_paths()) == {root, merged, alias}
    append_import(root, 'digest_inventory')
    assert set(closure.schema_sync_paths()) == {root, merged, alias, inventory}


@pytest.mark.parametrize('bound', ['files', 'bytes'])
def test_one_global_budget_spans_record_and_eager_sync_reads(tmp_path, monkeypatch, bound):
    root, _merged = simple_sync(tmp_path, monkeypatch)
    sibling = root.parent / 'unparsed.yaml'
    sibling.write_text('- not schema\n')
    record = tmp_path / 'record.yaml'
    record.write_text('id: https://example.org/record\nname: record\n')
    total = sum(p.stat().st_size for p in (root, sibling, record))
    monkeypatch.setattr(closure, 'MAX_SCHEMA_FILES', 3)
    monkeypatch.setattr(closure, 'MAX_SCHEMA_TOTAL_BYTES', total)
    def capture():
        reader = closure._SchemaReads()
        closure.record_schema_paths(record, _reader=reader)
        closure.schema_sync_paths(_reader=reader)
        return reader
    assert capture().total == total
    if bound == 'files': monkeypatch.setattr(closure, 'MAX_SCHEMA_FILES', 2)
    else: monkeypatch.setattr(closure, 'MAX_SCHEMA_TOTAL_BYTES', total - 1)
    with pytest.raises(ValueError, match='bound'):
        capture()


@pytest.mark.parametrize('bound', ['entries', 'depth'])
def test_metadata_walk_limits_are_explicit(tmp_path, monkeypatch, bound):
    root, _merged = simple_sync(tmp_path, monkeypatch)
    (root.parent / 'nested').mkdir()
    if bound == 'entries': monkeypatch.setattr(closure, 'MAX_SCHEMA_ENTRIES', 1)
    else: monkeypatch.setattr(closure, 'MAX_SCHEMA_DEPTH', 0)
    with pytest.raises(ValueError, match='bound'):
        closure.schema_sync_paths()


def test_guard_discovery_does_not_cache_success_across_boundaries(tmp_path, monkeypatch):
    root, merged = simple_sync(tmp_path, monkeypatch)
    assert set(closure.schema_sync_paths()) == {root, merged}
    new = root.parent / 'later.yaml'
    new.write_text('- newly present resource\n')
    assert set(closure.schema_sync_paths()) == {root, merged, new}


def private_comparison_pin(tmp_path, monkeypatch, kind):
    from data_sheets_schema import profiles
    path = tmp_path / ('private-comparison-' + kind + '.yaml')
    path.write_bytes(profiles.BRIDGE2AI.pin_path.read_bytes())
    if kind == 'resource':
        original = resources.resource_path
        monkeypatch.setattr(resources, 'resource_path', lambda selected:
            path if str(selected) == str(profiles.STUDY_VOCABULARY_PIN) else original(selected))
    elif kind == 'tracking-override':
        monkeypatch.setattr(schema_digest, 'VOCABULARY_PIN', path)
    else:
        assert kind == 'registered-nontracking'
        monkeypatch.setitem(profiles.PROFILES, 'private_comparison',
                            profiles.Profile(name='private_comparison', vocabulary_pin=path))
    return path


@pytest.mark.parametrize('kind', ['resource', 'tracking-override', 'registered-nontracking'])
@pytest.mark.parametrize('entry', ['public', 'batch'])
def test_all_profile_comparison_inputs_are_protected_for_neutral_run(registered, tmp_path, monkeypatch, kind, entry):
    base, reg = registered
    authority = private_comparison_pin(tmp_path, monkeypatch, kind)
    spec = selected_spec(base, reg)
    assert spec.profile == 'neutral' and reg['inputs']['profile']['vocabulary'] is None
    if entry == 'public':
        destination = usage_ledger.output_locks((spec.full_path,))[0][1]
    else:
        roster_path, _ = roster(base, reg, count=1)
        destination = run_lock._path_for('shared')
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.link(authority, destination)
    before = bytes_under(tmp_path)
    seen = no_execution(monkeypatch)
    monkeypatch.setattr(api, 'plan', lambda *a: pytest.fail('vocabulary alias reached plan'))
    if entry == 'public':
        with pytest.raises(ValueError, match='authority aliases a run output'):
            api.execute(spec)
    else:
        result = batch(reg, roster_path, count=1)
        assert result.exit_code == 1 and 'authority aliases a run output' in result.output, result.output
    assert seen == []
    unchanged(before)


def test_disjoint_comparison_pin_override_is_rechecked_without_reselecting_profile(registered, tmp_path, monkeypatch):
    from data_sheets_schema import profiles, shared_generation
    base, reg = registered
    spec = selected_spec(base, reg)
    before_instruction = spec.instruction
    before_spec = spec.render_spec()
    first = private_comparison_pin(tmp_path, monkeypatch, 'tracking-override')
    assert first in closure.resource_paths((spec,))
    second = tmp_path / 'second-comparison.yaml'
    second.write_bytes(first.read_bytes())
    monkeypatch.setattr(schema_digest, 'VOCABULARY_PIN', second)
    paths = closure.resource_paths((spec,))
    assert second in paths and first not in paths
    assert profiles.NEUTRAL.pin_path is None
    shared_generation.assert_current(spec)
    assert spec.instruction == before_instruction
    assert spec.render_spec() == before_spec


def test_absent_comparison_pin_preserves_actual_missing_vocabulary_finding(registered, tmp_path, monkeypatch):
    from data_sheets_schema import profiles
    base, reg = registered
    spec = selected_spec(base, reg)
    digest = schema_digest.fingerprint(schema_digest.digest_text('Dataset', profile=profiles.NEUTRAL))
    absent = tmp_path / 'absent-comparison.yaml'
    monkeypatch.setattr(schema_digest, 'VOCABULARY_PIN', absent)
    assert absent not in closure.resource_paths((spec,))
    with pytest.raises(profiles.MissingVocabulary):
        profiles.vocabulary_bytes(profiles.BRIDGE2AI)
    actual = provenance._profile_digest_disagreement({'schema': {'profile': 'neutral', 'digest_md5': digest}})
    assert actual and 'cannot be checked here' in actual and str(absent) in actual
    assert not absent.exists() and profiles.NEUTRAL.pin_path is None
