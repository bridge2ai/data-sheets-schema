"""Native S is current bounded authority; saved replay cannot discover files."""
from dataclasses import replace
import copy
import os
from pathlib import Path

import pytest

from data_sheets_schema import api_runner
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_selection as selected
from data_sheets_schema.schema_snapshot import capture_schema


def artifact(role, path, raw):
    return c.CapturedArtifact(c.ArtifactPin(role, str(path), len(raw), c.sha(raw)), raw)


def pin(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': c.sha(raw)}


def save(doc):
    Path(doc['registration_path']).write_bytes(c.canonical(doc))


def update_input(doc, name, raw):
    p = Path(doc['inputs'][name]['path'])
    p.write_bytes(raw)
    doc['inputs'][name] = pin(p, raw)
    save(doc)


@pytest.fixture
def declaration(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    inputs = root / 'inputs'
    inputs.mkdir()
    context = {'format': 'omission_context_v1', 'root_class': 'Dataset',
               'scopes': [{'owner': '', 'referent': 'Synthetic dataset', 'release': None,
                           'scope': 'The supplied source only.'}],
               'source_policy': {'allowed': 'declared bundle'}, 'vocabulary': {}}
    documents = {'bundle': b'Complete synthetic source.\n',
                 'chunk_manifest': b'{"chunks":[]}\n', 'context': c.canonical(context)}
    declared = {}
    for name, raw in documents.items():
        p = inputs / (name + '.txt')
        p.write_bytes(raw)
        declared[name] = pin(p, raw)
    for kind, cls, constant in (('full', 'Dataset', 'FULL_SCHEMA_PATH'),
                                 ('core', 'CoreDataset', 'CORE_SCHEMA_PATH')):
        p = inputs / (kind + '.yaml')
        p.write_text(f'id: https://example.org/{kind}\nname: {kind}\nclasses:\n  {cls}: {{}}\n')
        monkeypatch.setattr(api_runner, constant, p)
        snapshot = capture_schema(p, strict=True)
        declared[kind + '_schema'] = {'root': str(p), 'root_class': cls,
            'sources': [{'name': str(name), **pin(path, raw)} for name, path, raw in snapshot.sources]}
    policy = {'kind': c.KINDS['receipt_policy'], 'version': 1,
        'registration_id': 'synthetic-explicit-receipt-policy', 'condition': 'generic_v10',
        'runtime_policy_sha256': selected.RECEIPT_POLICY_SHA256, 'receipt_instrument_version': 4,
        'coverage_floor': {'state': 'pending', 'mode': 'diagnostic_pilot'}}
    policy_path = inputs / 'receipt-policy.json'
    policy_path.write_bytes(c.canonical(policy))
    assets = selected.capture_assets()
    axes = {k: v for k, v in selected.descriptor().items()
            if k not in {'typed_protocol', 'projection', 'receipt_policy', 'assets'}}
    doc = {'kind': c.KINDS['selection'], 'version': 1,
           'registration_id': 'synthetic-offline', 'registration_path': str(inputs / 'selection.json'),
           'run': {'project': 'SYNTHETIC', 'arm': 'BASELINE (input documents only)',
                   'method': 'claudecode_direct', 'label': 'offline-test'},
           'selection': {**axes, 'descriptor_sha256': selected.descriptor_capture().sha256,
                         'assets': {a.pin.role[len('asset:'):]: pin(a.pin.path, a.raw) for a in assets}},
           'inputs': {'project': 'SYNTHETIC', 'source_manifest': None, **declared,
                      'profile': {'name': 'neutral', 'basis': 'explicit caller', 'vocabulary': None}},
           'receipt_policy': pin(policy_path, c.canonical(policy)), 'bounds': dict(c.BOUND_CEILINGS),
           'stage_root': str(root / 'fresh-attempt' / 'stages')}
    save(doc)
    return doc


def test_actual_capture_and_pure_rebuild_retain_every_original_byte(declaration, monkeypatch):
    saved = selected.capture(declaration['registration_path'])
    original = saved.registration.raw
    # A later live edit is rejected by the current boundary but cannot leak
    # into reconstruction of the already captured selection.
    Path(declaration['inputs']['bundle']['path']).write_text('Different live source.\n')
    with pytest.raises(ValueError, match='bound|differ'):
        selected.capture(declaration['registration_path'])
    monkeypatch.setattr(Path, 'read_bytes', lambda *a: pytest.fail('live saved replay read'))
    monkeypatch.setattr(Path, 'resolve', lambda *a, **k: pytest.fail('live saved replay resolution'))
    monkeypatch.setattr(selected, 'resource_path', lambda *a: pytest.fail('ambient replay resource'))
    rebuilt = selected.rebuild(saved.registration, saved.authority, saved.schemas, saved.receipt_policy)
    assert rebuilt == saved
    assert rebuilt.registration.raw == original
    assert rebuilt.raw('bundle') == b'Complete synthetic source.\n'
    assert rebuilt.generation_context()['source_manifest'] is None
    assert not Path(declaration['stage_root']).exists()


def test_projection_has_one_common_policy_and_replaces_parent_procedure(declaration):
    saved = selected.capture(declaration['registration_path'])
    text = selected.projected_rules(saved)
    assert text.count('## Shared generation rules v1') == 1
    assert text.count('## Role relationship review v1') == 1
    assert 'There is no target slot count' in text
    assert 'The applicable LinkML schemas are the sole authority' in text
    assert 'OUTPUTS — do not write outside these three' not in text
    assert 'READ FIRST, IN THIS ORDER' not in text
    assert 'poetry run' not in text
    assert 'Phase 3 - Source and provenance audit' not in text
    assert 'data/preprocessed/source_manifest.yaml' not in text
    assert 'before writing one raw' in text
    assert 'draft-check allowance' in text


@pytest.mark.parametrize('mutation', ['extra_asset', 'missing_asset', 'asset_hash', 'descriptor', 'wrong_receipt_asset'])
def test_rebound_selection_cannot_select_foreign_policy(declaration, mutation):
    doc = declaration
    if mutation == 'extra_asset':
        doc['selection']['assets']['foreign.md'] = copy.deepcopy(doc['inputs']['bundle'])
    elif mutation == 'missing_asset':
        del doc['selection']['assets'][selected.POLICY]
    elif mutation == 'asset_hash':
        doc['selection']['assets'][selected.POLICY]['sha256'] = 'f' * 64
    elif mutation == 'descriptor':
        doc['selection']['descriptor_sha256'] = 'f' * 64
    else:
        p = Path(doc['receipt_policy']['path'])
        policy = c.strict_json(p.read_bytes())
        policy['runtime_policy_sha256'] = selected.ASSET_HASHES[selected.COMMON_POLICY]
        raw = c.canonical(policy)
        p.write_bytes(raw)
        doc['receipt_policy'] = pin(p, raw)
    save(doc)
    with pytest.raises(ValueError):
        selected.capture(doc['registration_path'])


def test_identical_asset_copy_cannot_replace_actual_installed_resource(declaration, tmp_path):
    doc = declaration
    expected = doc['selection']['assets'][selected.POLICY]
    raw = Path(expected['path']).read_bytes()
    foreign = tmp_path.resolve() / 'same-text.md'
    foreign.write_bytes(raw)
    doc['selection']['assets'][selected.POLICY] = pin(foreign, raw)
    save(doc)
    with pytest.raises(ValueError, match='different installed'):
        selected.capture(doc['registration_path'])


@pytest.mark.parametrize('owners', [['/child'], ['', ''], ['', '/child', '/child']])
def test_invalid_scope_inventory_refuses_before_any_stage(declaration, owners):
    context = c.strict_json(Path(declaration['inputs']['context']['path']).read_bytes())
    context['scopes'] = [{**context['scopes'][0], 'owner': owner} for owner in owners]
    update_input(declaration, 'context', c.canonical(context))
    with pytest.raises(ValueError, match='root and unique'):
        selected.capture(declaration['registration_path'])
    assert not Path(declaration['stage_root']).exists()


def test_nonroot_existence_waits_for_generated_full(declaration):
    context = c.strict_json(Path(declaration['inputs']['context']['path']).read_bytes())
    context['scopes'].append({**context['scopes'][0], 'owner': '/resources/0'})
    update_input(declaration, 'context', c.canonical(context))
    assert selected.capture(declaration['registration_path']).raw('context') == c.canonical(context)


@pytest.mark.parametrize('profile', ['unknown', 'bridge2ai'])
def test_profile_cannot_silently_fall_back_to_neutral(declaration, profile):
    declaration['inputs']['profile']['name'] = profile
    save(declaration)
    with pytest.raises(ValueError):
        selected.capture(declaration['registration_path'])


def test_pure_rebuild_rejects_missing_and_extra_authority(declaration):
    saved = selected.capture(declaration['registration_path'])
    for authority in (saved.authority[1:], saved.authority + (saved.authority[0],)):
        with pytest.raises(ValueError, match='roles'):
            selected.rebuild(saved.registration, authority, saved.schemas, saved.receipt_policy)


def test_pure_schema_reconstruction_cannot_use_ambient_missing_import(declaration, monkeypatch):
    saved = selected.capture(declaration['registration_path'])
    doc = saved.document()
    old = saved.schemas[0]
    first = old.sources[0]
    raw = first.raw + b'imports:\n  - unregistered\n'
    changed = artifact(first.pin.role, first.pin.path, raw)
    doc['inputs']['full_schema']['sources'][0].update(pin(first.pin.path, raw))
    schema = replace(old, sources=(changed,), closure_sha256=c.schema_closure_sha((changed,), old.import_roles))
    registration = artifact('selection', saved.registration.pin.path, c.canonical(doc))
    monkeypatch.setattr(Path, 'read_bytes', lambda *a: pytest.fail('ambient import read'))
    monkeypatch.setattr(Path, 'resolve', lambda *a, **k: pytest.fail('ambient schema resolution'))
    with pytest.raises(ValueError, match='outside the complete captured'):
        selected.rebuild(registration, saved.authority, (schema, saved.schemas[1]), saved.receipt_policy)


@pytest.mark.parametrize('kind', ['symlink', 'hardlink', 'fifo'])
def test_nonregular_or_aliased_input_refuses_without_reading(declaration, tmp_path, kind):
    original = Path(declaration['inputs']['bundle']['path'])
    other = tmp_path.resolve() / ('replacement-' + kind)
    if kind == 'symlink':
        other.symlink_to(original)
    elif kind == 'hardlink':
        os.link(original, other)
    else:
        os.mkfifo(other)
    declaration['inputs']['bundle']['path'] = str(other)
    save(declaration)
    with pytest.raises(ValueError, match='alias|regular'):
        selected.capture(declaration['registration_path'])


def test_stage_root_parent_symlink_is_not_normalized_into_authority(declaration, tmp_path):
    real = tmp_path.resolve() / 'real-output'
    real.mkdir()
    alias = tmp_path.resolve() / 'aliased-output'
    alias.symlink_to(real, target_is_directory=True)
    declaration['stage_root'] = str(alias / 'stages')
    save(declaration)
    with pytest.raises(ValueError, match='alias'):
        selected.capture(declaration['registration_path'])


def test_declared_small_byte_limit_refuses_before_opening_input(declaration, monkeypatch):
    declaration['bounds']['max_input_bytes'] = 1
    save(declaration)
    opened = []
    actual_open = selected.os.open

    def observed_open(path, *args):
        opened.append(str(path))
        return actual_open(path, *args)

    monkeypatch.setattr(selected.os, 'open', observed_open)
    with pytest.raises(ValueError, match='input bound'):
        selected.capture(declaration['registration_path'])
    assert opened == [declaration['registration_path']]


def test_nonnull_source_and_profile_vocabulary_survive_exact_saved_replay(declaration, tmp_path, monkeypatch):
    from data_sheets_schema import schema_digest
    manifest = tmp_path.resolve() / 'source-manifest.yaml'
    manifest_raw = b'profile: bridge2ai\nprojects: {}\n'
    manifest.write_bytes(manifest_raw)
    vocabulary = tmp_path.resolve() / 'vocabulary.yaml'
    vocabulary_raw = b'categories:\n  - Exact supplied term\n'
    vocabulary.write_bytes(vocabulary_raw)
    monkeypatch.setattr(schema_digest, 'VOCABULARY_PIN', vocabulary)
    declaration['inputs']['source_manifest'] = pin(manifest, manifest_raw)
    declaration['inputs']['profile'] = {'name': 'bridge2ai', 'basis': 'explicit caller',
                                         'vocabulary': pin(vocabulary, vocabulary_raw)}
    save(declaration)
    saved = selected.capture(declaration['registration_path'])
    monkeypatch.setattr(Path, 'read_bytes', lambda *a: pytest.fail('live source/vocabulary replay'))
    monkeypatch.setattr(Path, 'resolve', lambda *a, **k: pytest.fail('live vocabulary resolution'))
    rebuilt = selected.rebuild(saved.registration, saved.authority, saved.schemas, saved.receipt_policy)
    context = rebuilt.generation_context()
    assert context['source_manifest'] == pin(manifest, manifest_raw)
    assert context['profile'] == {'name': 'bridge2ai', 'basis': 'explicit caller',
        'vocabulary': {'identity': pin(vocabulary, vocabulary_raw),
                       'raw_text': vocabulary_raw.decode('utf-8')}}
    assert rebuilt.raw('source_manifest') == manifest_raw


def test_whole_capture_refuses_changes_after_a_file_was_read(declaration, monkeypatch):
    target = Path(declaration['inputs']['bundle']['path'])
    original = selected._Reads.read
    changed = False

    def concurrent_edit(reader, path, maximum):
        nonlocal changed
        raw = original(reader, path, maximum)
        if Path(path) == target and not changed:
            changed = True
            target.write_bytes(raw.replace(b'Complete', b'Altered!'))
        return raw

    monkeypatch.setattr(selected._Reads, 'read', concurrent_edit)
    with pytest.raises(ValueError, match='changed before capture completed'):
        selected.capture(declaration['registration_path'])


def test_actual_registered_schema_imports_are_captured_not_discovered_later(declaration):
    root = Path(declaration['inputs']['full_schema']['root'])
    imported = root.with_name('children.yaml')
    imported.write_text('id: https://example.org/children\nname: children\nclasses:\n  Child: {}\n')
    root.write_bytes(root.read_bytes() + b'imports:\n  - children\n')
    snapshot = capture_schema(root, strict=True)
    declaration['inputs']['full_schema']['sources'] = [
        {'name': str(name), **pin(path, raw)} for name, path, raw in snapshot.sources]
    save(declaration)
    saved = selected.capture(declaration['registration_path'])
    assert len(saved.schemas[0].sources) == 2
    imported.write_text('Invalid later ambient document.\n')
    assert selected.rebuild(saved.registration, saved.authority, saved.schemas, saved.receipt_policy) == saved
