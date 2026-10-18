"""Copied resources, trapped writers and neutral schemas; no provider calls."""
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema import audit_omissions, resources, provenance, run_lock
from data_sheets_schema import shared_generation_resources as closure
from data_sheets_schema import usage_ledger, canary
from tests.test_shared_generation_cli import (registered, external, roster, batch,
                                              module, stub_plan)
from tests.test_shared_generation_selection import selected_spec
from tests.test_shared_output_ownership_entrypoints import no_execution


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    import socket
    root = Path(__file__).resolve().parents[1]
    assert root in Path(closure.__file__).resolve().parents
    assert root in Path(api.__file__).resolve().parents
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})


def bytes_under(root):
    return {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}


def unchanged(before):
    assert {path: path.read_bytes() for path in before} == before


def schema_files(root, *, namespace=False):
    root.mkdir(exist_ok=True)
    imported = root / 'extra.yaml'
    imported.write_text('id: https://example.org/extra\nname: extra\nslots:\n  extra:\n    range: string\n')
    definition = {'id': 'https://example.org/record', 'name': 'record',
        'prefixes': {'linkml': 'https://w3id.org/linkml/'},
        'imports': ['linkml:types', 'extra'], 'default_range': 'string',
        'classes': {'GenerationRecord': {'tree_root': True, 'slots': ['extra']}}}
    if namespace:
        good = root / 'good'
        good.mkdir()
        moved = good / 'extra.yaml'
        moved.write_bytes(imported.read_bytes())
        imported = moved
        definition['prefixes']['chosen'] = str(root / 'unused') + '/'
        definition['imports'] = ['linkml:types', 'chosen:extra', 'aliases']
        (root / 'aliases.yaml').write_text(yaml.safe_dump({
            'id': 'https://example.org/aliases', 'name': 'aliases',
            'prefixes': {'chosen': str(good) + '/'}}))
    path = root / 'record.yaml'
    path.write_text(yaml.safe_dump(definition, sort_keys=False))
    return path, imported


RESOURCES = ('policy.md', 'context.schema.json', 'response.schema.json',
             'evidence', 'registry', 'record-schema', 'record-import',
             'full-version', 'core-version', 'config', 'legacy-playbook', 'naming')


def copy_resource(kind, tmp_path, monkeypatch):
    """Route only private copies; never alias a real source/package asset."""
    if kind in audit_omissions.ASSET_SHA256:
        private = tmp_path / 'omission-assets'
        private.mkdir()
        for name in audit_omissions.ASSET_SHA256:
            (private / name).write_bytes((audit_omissions.ASSETS / name).read_bytes())
        monkeypatch.setattr(audit_omissions, 'ASSETS', private)
        return private / kind
    if kind == 'naming':
        path = tmp_path / 'data/preprocessed/source_manifest.yaml'
        path.parent.mkdir(parents=True)
        path.write_text('naming: {}\n')
        return path
    original = resources.resource_path
    names = {'evidence': 'src/download/prompts/evidence_protocol_v7.md',
        'registry': 'src/download/prompts/canonical_hashes.yaml',
        'record-schema': str(provenance.RECORD_SCHEMA),
        'record-import': str(provenance.RECORD_SCHEMA),
        'full-version': str(provenance.SOURCE_SCHEMA),
        'core-version': str(provenance.CORE_SOURCE_SCHEMA),
        'config': str(provenance.DETERMINISTIC_CONFIG),
        'legacy-playbook': str(provenance.AGENT_PLAYBOOKS[0])}
    name = names[kind]
    if kind == 'record-import':
        copied, authority = schema_files(tmp_path / 'private-record-schema')
    elif kind in ('full-version', 'core-version'):
        # These version roots also feed the real schema-sync reader. Preserve
        # their actual private sibling/import closure, not an incomplete root.
        source = original(name)
        private = tmp_path / 'private-raw-schema'
        for path in source.parent.rglob('*.yaml'):
            target = private / path.relative_to(source.parent)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
        copied = authority = private / source.name
    else:
        copied = tmp_path / ('copied-' + Path(name).name)
        copied.write_bytes(original(name).read_bytes())
        authority = copied
    monkeypatch.setattr(resources, 'resource_path',
        lambda path: copied if str(path) == name else original(path))
    return authority


@pytest.mark.parametrize('kind', RESOURCES)
@pytest.mark.parametrize('entry', ['public', 'batch'])
def test_copied_dependency_refuses_before_any_lock_or_writer(registered, tmp_path, monkeypatch, kind, entry):
    base, reg = registered
    authority = copy_resource(kind, tmp_path, monkeypatch)
    # Config routing is a copied-byte physical identity, selected explicitly.
    if kind == 'config':
        reg['runtime']['config'] = sg.file_pin(authority)
    spec = selected_spec(base, reg)
    assert authority.resolve() in {path.resolve() for path in closure.resource_paths((spec,))}
    if entry == 'public':
        destination = usage_ledger.output_locks((spec.full_path,))[0][1]
    else:
        roster_path, _ = roster(base, reg, count=1)
        destination = run_lock._path_for('shared')
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.link(authority, destination)
    before = bytes_under(tmp_path)
    seen = no_execution(monkeypatch)
    monkeypatch.setattr(api, 'plan', lambda *a: pytest.fail('alias reached planning'))
    if entry == 'public':
        with pytest.raises(ValueError, match='authority aliases a run output'):
            api.execute(spec)
    else:
        result = batch(reg, roster_path, count=1)
        assert result.exit_code == 1 and 'authority aliases a run output' in result.output, result.output
    assert seen == [] and authority.samefile(destination)
    unchanged(before)


def test_record_import_matches_actual_generator_namespace_order(tmp_path):
    from data_sheets_schema.record_schema import compile_record_schema
    root, imported = schema_files(tmp_path / 'schema', namespace=True)
    before = bytes_under(tmp_path)
    paths = closure.record_schema_paths(root)
    assert imported in paths
    assert not any('unused' in p.parts for p in paths)
    compiled = compile_record_schema(root)
    definitions = compiled.get('$defs', compiled.get('definitions', {}))
    subject = compiled if 'properties' in compiled else definitions['GenerationRecord']
    assert 'extra' in subject['properties']
    unchanged(before)


def dual_schema_roots(tmp_path, *, local_only=False):
    target, target_import = schema_files(tmp_path / 'target')
    directory = tmp_path / 'alias'
    directory.mkdir()
    logical = directory / 'record.yaml'
    logical.symlink_to(target)
    logical_import = directory / 'extra.yaml'
    logical_import.write_text(target_import.read_text().replace('range: string', 'range: integer'))
    if local_only:
        doc = yaml.safe_load(target.read_bytes()); doc['imports'] = ['extra']
        target.write_text(yaml.safe_dump(doc))
    return logical, target, logical_import, target_import


def test_symlink_root_protects_both_actual_record_consumers(tmp_path):
    from data_sheets_schema.record_schema import compile_record_schema
    logical, target, logical_import, target_import = dual_schema_roots(tmp_path)
    before = bytes_under(tmp_path)
    paths = closure.record_schema_paths(logical)
    assert {logical, target, logical_import, target_import} <= set(paths)
    validator = provenance._record_validator(logical)
    assert validator._context('GenerationRecord').schema_view.get_slot('extra').range == 'integer'
    compiled = compile_record_schema(logical)
    definitions = compiled.get('$defs', compiled.get('definitions', {}))
    subject = compiled if 'properties' in compiled else definitions['GenerationRecord']
    assert subject['properties']['extra']['type'] == ['string', 'null']
    assert list(validator.iter_results({'extra': 'compiler-side string'}, 'GenerationRecord')) == []
    unchanged(before)


@pytest.mark.parametrize('side', ['logical', 'resolved'])
@pytest.mark.parametrize('entry', ['public', 'batch'])
def test_both_record_import_roots_refuse_before_actual_entrypoint_writes(registered, tmp_path, monkeypatch, side, entry):
    base, reg = registered
    logical, target, logical_import, target_import = dual_schema_roots(tmp_path)
    original = resources.resource_path
    monkeypatch.setattr(resources, 'resource_path', lambda path:
        logical if str(path) == str(provenance.RECORD_SCHEMA) else original(path))
    spec = selected_spec(base, reg)
    authority = logical_import if side == 'logical' else target_import
    if entry == 'public':
        destination = usage_ledger.output_locks((spec.full_path,))[0][1]
    else:
        roster_path, _ = roster(base, reg, count=1)
        destination = run_lock._path_for('shared')
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.link(authority, destination)
    before = bytes_under(tmp_path)
    seen = no_execution(monkeypatch)
    monkeypatch.setattr(api, 'plan', lambda *a: pytest.fail('import alias reached planning'))
    if entry == 'public':
        with pytest.raises(ValueError, match='authority aliases a run output'):
            api.execute(spec)
    else:
        result = batch(reg, roster_path, count=1)
        assert result.exit_code == 1 and 'authority aliases a run output' in result.output, result.output
    assert seen == []
    unchanged(before)


@pytest.mark.parametrize('bound', ['files', 'total_bytes'])
def test_both_record_roots_share_one_global_discovery_budget(tmp_path, monkeypatch, bound):
    logical, target, logical_import, target_import = dual_schema_roots(tmp_path, local_only=True)
    expected = {logical, target, logical_import, target_import}
    size = sum(path.stat().st_size for path in expected)
    monkeypatch.setattr(closure, 'MAX_SCHEMA_FILES', 4)
    monkeypatch.setattr(closure, 'MAX_SCHEMA_TOTAL_BYTES', size)
    assert set(closure.record_schema_paths(logical)) == expected
    if bound == 'files': monkeypatch.setattr(closure, 'MAX_SCHEMA_FILES', 3)
    else: monkeypatch.setattr(closure, 'MAX_SCHEMA_TOTAL_BYTES', size - 1)
    before = bytes_under(tmp_path)
    with pytest.raises(ValueError, match='bound'):
        closure.record_schema_paths(logical)
    unchanged(before)


@pytest.mark.parametrize('limit', ['files', 'file_bytes', 'total_bytes'])
def test_record_import_limits_are_explicit_and_nonmutating(tmp_path, monkeypatch, limit):
    root, imported = schema_files(tmp_path / 'schema')
    # Use only local imports so exact byte bounds are independent of LinkML version.
    doc = yaml.safe_load(root.read_bytes()); doc['imports'] = ['extra']
    root.write_text(yaml.safe_dump(doc))
    before = bytes_under(tmp_path)
    if limit == 'files':
        monkeypatch.setattr(closure, 'MAX_SCHEMA_FILES', 1)
    elif limit == 'file_bytes':
        monkeypatch.setattr(closure, 'MAX_SCHEMA_FILE_BYTES', root.stat().st_size - 1)
    else:
        monkeypatch.setattr(closure, 'MAX_SCHEMA_TOTAL_BYTES', root.stat().st_size + imported.stat().st_size - 1)
    with pytest.raises(ValueError, match='bound'):
        closure.record_schema_paths(root)
    unchanged(before)


def test_record_import_exact_limits_and_missing_import(tmp_path, monkeypatch):
    root, imported = schema_files(tmp_path / 'schema')
    doc = yaml.safe_load(root.read_bytes()); doc['imports'] = ['extra']
    root.write_text(yaml.safe_dump(doc))
    monkeypatch.setattr(closure, 'MAX_SCHEMA_FILES', 2)
    monkeypatch.setattr(closure, 'MAX_SCHEMA_FILE_BYTES', max(root.stat().st_size, imported.stat().st_size))
    monkeypatch.setattr(closure, 'MAX_SCHEMA_TOTAL_BYTES', root.stat().st_size + imported.stat().st_size)
    assert closure.record_schema_paths(root) == (root, imported)
    # Retain the original bytes; a separate root names a genuinely absent dependency.
    missing = tmp_path / 'missing.yaml'
    doc['imports'] = ['absent']
    missing.write_text(yaml.safe_dump(doc))
    monkeypatch.setattr(closure, 'MAX_SCHEMA_FILE_BYTES', 4096)
    monkeypatch.setattr(closure, 'MAX_SCHEMA_TOTAL_BYTES', 8192)
    with pytest.raises(FileNotFoundError):
        closure.record_schema_paths(missing)


def test_growing_file_is_read_only_to_limit_plus_one(tmp_path, monkeypatch):
    path = tmp_path / 'large.yaml'
    path.write_bytes(b'x' * 100)
    monkeypatch.setattr(closure, 'MAX_SCHEMA_FILE_BYTES', 16)
    original_stat, original_open = os.fstat, os.fdopen
    monkeypatch.setattr(os, 'fstat', lambda fd: SimpleNamespace(st_mode=original_stat(fd).st_mode, st_size=1))
    sizes = []
    class BoundedReader:
        def __init__(self, stream): self.stream = stream
        def __enter__(self): return self
        def __exit__(self, *args): self.stream.close()
        def fileno(self): return self.stream.fileno()
        def read(self, size):
            sizes.append(size)
            assert size == 17
            return self.stream.read(size)
    monkeypatch.setattr(os, 'fdopen', lambda *a, **k: BoundedReader(original_open(*a, **k)))
    with pytest.raises(ValueError, match='byte bound'):
        closure.record_schema_paths(path)
    assert sizes == [17] and path.read_bytes() == b'x' * 100


def test_fifo_dependency_refuses_without_blocking(tmp_path):
    path = tmp_path / 'schema.fifo'
    os.mkfifo(path)
    with pytest.raises(ValueError, match='not a regular file'):
        closure.record_schema_paths(path)


def test_missing_optional_observations_and_disjoint_inputs_still_admit(registered, tmp_path, monkeypatch):
    base, reg = registered
    spec = selected_spec(base, reg)
    original = resources.resource_path
    optional = {str(provenance.SOURCE_SCHEMA), str(provenance.CORE_SOURCE_SCHEMA),
                *(str(p) for p in provenance.AGENT_PLAYBOOKS)}
    monkeypatch.setattr(resources, 'resource_path', lambda path:
        tmp_path / ('absent-' + Path(path).name) if str(path) in optional else original(path))
    assert not (tmp_path / 'data/preprocessed/source_manifest.yaml').exists()
    before = bytes_under(tmp_path)
    captured = sg.assert_current(spec)
    sg._separate_authorities((spec, spec), tuple(p for p, _ in captured.files))
    assert captured.registration == sg.canonical(reg)
    unchanged(before)


def test_legacy_execute_does_not_discover_selected_resources(external, monkeypatch):
    from contextlib import nullcontext
    monkeypatch.setattr(closure, 'resource_paths', lambda *a: pytest.fail('legacy resource discovery'))
    monkeypatch.setattr(api, '_exclusive_run', lambda spec: nullcontext())
    monkeypatch.setattr(api, '_restore_resume_date', lambda *a, **k: None)
    marker = object()
    monkeypatch.setattr(api, '_execute', lambda *a, **k: marker)
    assert api.execute(external, client=object()) is marker


def baseline_file(tmp_path, project, *, method='claudecode_agent'):
    base = tmp_path / 'selected-baselines'
    path = base / (method + '_core') / 'previous_rep1' / (project + '_provenance.yaml')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('record_type: synthetic baseline-only fixture\n')
    return base, path


def test_explicit_canary_baseline_uses_actual_selector_before_writers(registered, tmp_path, monkeypatch):
    base, reg = registered
    root, authority = baseline_file(tmp_path, base.project)
    monkeypatch.setattr(provenance, 'CONCAT_DIR', root)
    roster_path, _ = roster(base, reg, count=1)
    control = run_lock._path_for('shared'); control.parent.mkdir(parents=True)
    os.link(authority, control)
    before = bytes_under(tmp_path)
    seen = no_execution(monkeypatch)
    monkeypatch.setattr(api, 'plan', lambda *a: pytest.fail('baseline alias reached plan'))
    result = batch(reg, roster_path, count=1, extra=('--canary-baseline', 'previous'))
    assert result.exit_code == 1 and 'authority aliases a run output' in result.output, result.output
    assert seen == []
    unchanged(before)


def test_ambiguous_canary_selection_is_clean_prewrite_cli_refusal(registered, tmp_path, monkeypatch):
    base, reg = registered
    root, _ = baseline_file(tmp_path, base.project)
    baseline_file(tmp_path, base.project, method='claudecode_api')
    monkeypatch.setattr(provenance, 'CONCAT_DIR', root)
    roster_path, _ = roster(base, reg, count=1)
    before = bytes_under(tmp_path)
    seen = no_execution(monkeypatch)
    monkeypatch.setattr(api, 'plan', lambda *a: pytest.fail('ambiguity reached plan'))
    result = batch(reg, roster_path, count=1, extra=('--canary-baseline', 'previous'))
    assert result.exit_code == 1 and 'matches runs under' in result.output and 'Error:' in result.output, result.output
    assert seen == []
    unchanged(before)


@pytest.mark.parametrize('boundary', ['after-plan', 'before-dispatch'])
def test_actual_batch_rechecks_resource_alias_at_late_boundaries(registered, tmp_path, monkeypatch, boundary):
    base, reg = registered
    authority = copy_resource('policy.md', tmp_path, monkeypatch)
    roster_path, _ = roster(base, reg, count=1)
    control = run_lock._path_for('shared')
    protected = {}
    def mutate():
        control.parent.mkdir(parents=True, exist_ok=True)
        os.link(authority, control)
        protected.update(bytes_under(tmp_path))
    seen = no_execution(monkeypatch)
    def plan(spec):
        if boundary == 'after-plan': mutate()
        return stub_plan(spec)
    monkeypatch.setattr(api, 'plan', plan)
    if boundary == 'before-dispatch':
        def acquire(*args):
            mutate()
            return control
        # No lock writer: only this declared safe layout simulation occurs.
        monkeypatch.setattr(run_lock, 'acquire', acquire)
        monkeypatch.setattr(run_lock, 'release', lambda *a: None)
    result = batch(reg, roster_path, count=1)
    assert result.exit_code != 0 and 'authority aliases a run output' in result.output, result.output
    assert seen == [] and protected
    unchanged(protected)


def test_canary_selector_forwarded_at_all_three_boundaries(registered, tmp_path, monkeypatch):
    base, reg = registered
    root, _ = baseline_file(tmp_path, base.project)
    monkeypatch.setattr(provenance, 'CONCAT_DIR', root)
    roster_path, _ = roster(base, reg, count=1)
    original = canary._baseline_records
    calls = []
    def selected(*args):
        calls.append(args)
        return original(*args)
    monkeypatch.setattr(canary, '_baseline_records', selected)
    monkeypatch.setattr(api, 'plan', stub_plan)
    monkeypatch.setattr(run_lock, 'acquire', lambda *a: run_lock._path_for('shared'))
    monkeypatch.setattr(run_lock, 'release', lambda *a: None)
    def stop(*args): raise ValueError('synthetic stop before real execution')
    monkeypatch.setattr(api, 'execute', stop)
    before = bytes_under(tmp_path)
    result = batch(reg, roster_path, count=1, extra=('--canary-baseline', 'previous'))
    assert result.exit_code != 0 and 'synthetic stop' in result.output, result.output
    assert calls == [(root, None, 'previous', base.project)] * 3
    unchanged(before)


@pytest.mark.parametrize('prefix', [None, ''])
def test_omitted_baseline_never_discovers_comparison_records(registered, monkeypatch, prefix):
    base, reg = registered
    roster_path, _ = roster(base, reg, count=1)
    monkeypatch.setattr(canary, '_baseline_records', lambda *a: pytest.fail('unsupplied baseline discovery'))
    monkeypatch.setattr(api, 'plan', stub_plan)
    extra = ('--dry-run',) + (() if prefix is None else ('--canary-baseline', prefix))
    result = batch(reg, roster_path, count=1, extra=extra)
    assert result.exit_code == 0, result.output
