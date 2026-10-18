"""Immutable label evidence is complete only after real output validation."""
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from data_sheets_schema import deterministic_publication as publication


COMMIT = "f" * 40
REPORT = """- Mapping table: `mapping.tsv` (1 table rows declared, plus the record's `id`)
- Distinct top-level `Dataset` slots filled: 2 (from 2 filled rows)
## Outcome
| Status | Rows | Meaning |
|---|---|---|
| filled | 2 | placed |
## Fidelity of what was filled
| Mapping type | Filled fields |
|---|---|
| exactMatch | 2 |
| Information loss | Filled fields |
|---|---|
| none | 2 |
## Per-field detail
| D4D path | Status | Mapping | Loss | Source path | Value / note |
|---|---|---|---|---|---|
| Dataset.id | filled | exactMatch | none | crate root identifier/@id | doi:10.1234/example |
| Dataset.name | filled | exactMatch | none | name | Fixture |
"""


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    repo.mkdir()
    monkeypatch.chdir(repo)
    packages = repo / 'data/ro-crate_packages'
    concat = repo / 'data/d4d_concatenated'
    code = sorted(publication.STATIC_PRODUCER_FILES)
    fixture_files = [(name, f'# fixture {name}\n'.encode()) for name in code]
    fixture_files += [(publication.SCHEMA, b'fixture schema\n'),
                      (publication.TABLE, b'fixture table\n')]
    for name, raw in fixture_files:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    packages.mkdir(parents=True)
    (packages / 'crate_manifest.yaml').write_bytes(b'projects: {}\n')
    monkeypatch.setattr(publication, '_code', lambda repo: (COMMIT, code))
    old = concat / 'rocrate_static_map/old-label/CHORUS_d4d.yaml'
    old.parent.mkdir(parents=True)
    old.write_bytes(b'id: historical\n')

    def add(project='CHORUS', upstream=False):
        raw = b'{"@graph": [{"@id": "./", "@type": "Dataset", "name": "Fixture"}]}'
        base = packages / project
        (base / 'raw').mkdir(parents=True, exist_ok=True)
        (base / 'processed').mkdir(exist_ok=True)
        (base / 'raw/ro-crate-metadata.json').write_bytes(raw)
        record = b'id: doi:10.1234/example\nname: Fixture\n'
        variant = 'crate_d4d' if upstream else 'crate_mapped_d4d'
        (base / 'processed' / f'{project}_{variant}.yaml').write_bytes(record)
        if upstream:
            (base / 'raw/ro-crate-linkml.yaml').write_bytes(b'id: original\n')
            (base / 'processed' / f'{project}_crate_changes.md').write_bytes(b'Original repair report\n')
        else:
            (base / 'processed' / f'{project}_crate_mapping_provenance.md').write_text(REPORT)
            sidecar = {'format_version': 1, 'project': project,
                       'source': {'path': str((base / 'raw/ro-crate-metadata.json').relative_to(repo)), 'sha256': sha(raw)},
                       'record_sha256': sha(record),
                       'producer': {'files_sha256': {name: sha((repo / name).read_bytes()) for name in code}},
                       'mapping_table': {'path': publication.TABLE, 'sha256': sha((repo / publication.TABLE).read_bytes())},
                       'schema': {'path': publication.SCHEMA, 'sha256': sha((repo / publication.SCHEMA).read_bytes())},
                       'rows': [{'rule_id': 'r1', 'execution': 'active', 'd4d_path': 'Dataset.name',
                                 'destination_slot': 'name', 'source_expression': 'name', 'status': 'filled',
                                 'root_assertions': [{'entity_id': './', 'json_pointer': '/@graph/0/name',
                                                      'property': 'name', 'value': 'Fixture'}],
                                 'member_assertions': []}]}
            (base / 'processed' / f'{project}_crate_mapping_sources.json').write_text(json.dumps(sidecar))
        return base

    add()
    return repo, packages, concat, old, add


def valid(record, schema):
    assert Path(record).is_file() and Path(schema).is_file()
    return {'argv': ['fixture-validator', str(record)], 'exit_code': 0,
            'stdout': 'No issues found\n', 'stderr': '', 'valid': True}


def prepared(inputs, method='rocrate_static_map', projects=None, label='new-label'):
    repo, packages, concat, _, _ = inputs
    return publication.prepare(repo, packages, concat, method, label, projects or ['CHORUS'])


def test_complete_label_retains_hashes_reports_actual_verdict_and_prior_bytes(inputs):
    repo, packages, concat, old, _ = inputs
    before = old.read_bytes()
    ready = prepared(inputs)
    manifest = publication.publish(ready, validator=valid)
    output = concat / 'rocrate_static_map/new-label'
    assert manifest['state'] == 'complete' and manifest['code_commit'] == COMMIT
    assert manifest['code_commit_role'] == 'publication_code'
    binding = manifest['projects'][0]['producer_binding']
    assert binding['kind'] == 'source_sidecar_code_hashes' and binding['verified'] is True
    assert set(binding['files_sha256']) == publication.STATIC_PRODUCER_FILES
    assert manifest['prior_labels_unchanged'] and manifest['method_core_created'] is False
    assert old.read_bytes() == before
    assert manifest['prior_label_sha256']['rocrate_static_map/old-label/CHORUS_d4d.yaml'] == sha(before)
    assert manifest['projects'][0]['validation']['argv'][0] == 'fixture-validator'
    assert (output / 'provenance/CHORUS/CHORUS_crate_mapping_sources.json').read_bytes() == (
        packages / 'CHORUS/processed/CHORUS_crate_mapping_sources.json').read_bytes()
    emitted = (output / 'CHORUS_d4d.yaml').read_text()
    assert '# Source crate: data/ro-crate_packages/CHORUS\n' in emitted
    assert str(repo) not in emitted
    frozen = (output / 'manifest.json').read_bytes()
    with pytest.raises(FileExistsError):
        publication.publish(ready, validator=valid)
    assert (output / 'manifest.json').read_bytes() == frozen


def test_invalid_record_leaves_no_completion_marker_and_retains_failure(inputs):
    ready = prepared(inputs)
    def rejected(*_):
        return {'argv': ['validator'], 'exit_code': 1, 'stdout': '', 'stderr': 'invalid', 'valid': False}
    with pytest.raises(ValueError, match='failed validation'):
        publication.publish(ready, validator=rejected)
    assert not (ready['destination'] / 'manifest.json').exists()
    assert json.loads((ready['destination'] / 'validation-failure.json').read_bytes())['validation']['stderr'] == 'invalid'
    assert inputs[3].read_bytes() == b'id: historical\n'


def test_validator_cannot_replace_emitted_record_and_bless_replacement(inputs):
    ready = prepared(inputs)

    def replaces_record(record, schema):
        result = valid(record, schema)
        record.write_bytes(b'id: doi:10.1234/replacement\nname: Replacement\n')
        return result

    with pytest.raises(ValueError, match='record changed after emission'):
        publication.publish(ready, validator=replaces_record)
    assert not (ready['destination'] / 'manifest.json').exists()
    assert inputs[3].read_bytes() == b'id: historical\n'


def test_record_mutation_before_manifest_completion_is_rejected(inputs, monkeypatch):
    ready = prepared(inputs)
    complete = publication.figure_publication.complete

    def replace_before_completion(directory, marker, raw, verify):
        (ready['destination'] / 'CHORUS_d4d.yaml').write_bytes(b'id: replaced-after-validation\n')
        return complete(directory, marker, raw, verify)

    monkeypatch.setattr(publication.figure_publication, 'complete', replace_before_completion)
    with pytest.raises(ValueError, match='record changed after emission'):
        publication.publish(ready, validator=valid)
    assert not (ready['destination'] / 'manifest.json').exists()
    assert inputs[3].read_bytes() == b'id: historical\n'


@pytest.mark.parametrize('target', ['source', 'history'])
def test_concurrent_input_or_old_label_change_prevents_completion(inputs, target):
    ready = prepared(inputs)
    def change(record, schema):
        result = valid(record, schema)
        path = inputs[1] / 'CHORUS/raw/ro-crate-metadata.json' if target == 'source' else inputs[3]
        path.write_bytes(b'changed externally')
        return result
    with pytest.raises(ValueError, match='changed'):
        publication.publish(ready, validator=change)
    assert not (ready['destination'] / 'manifest.json').exists()


def test_stale_sidecar_record_hash_refused_before_reserving_output(inputs):
    sidecar = inputs[1] / 'CHORUS/processed/CHORUS_crate_mapping_sources.json'
    content = json.loads(sidecar.read_bytes())
    content['record_sha256'] = '0' * 64
    sidecar.write_text(json.dumps(content))
    with pytest.raises(ValueError, match='record hash'):
        prepared(inputs)
    assert not (inputs[2] / 'rocrate_static_map/new-label').exists()


@pytest.mark.parametrize('change', ['stale', 'missing', 'incomplete', 'untracked'])
def test_static_record_requires_current_complete_producer_binding(inputs, change):
    sidecar = inputs[1] / 'CHORUS/processed/CHORUS_crate_mapping_sources.json'
    content = json.loads(sidecar.read_bytes())
    hashes = content['producer']['files_sha256']
    name = sorted(publication.STATIC_PRODUCER_FILES)[0]
    if change == 'stale':
        # A working record from an older producer must not acquire the current
        # code's provenance merely because publication runs under that code.
        (inputs[0] / name).write_bytes(b'# changed producer implementation\n')
    elif change == 'missing':
        del content['producer']
    elif change == 'incomplete':
        del hashes[name]
    else:
        hashes['untracked.py'] = '0' * 64
    sidecar.write_text(json.dumps(content))
    with pytest.raises(ValueError, match='producer code'):
        prepared(inputs)
    assert not (inputs[2] / 'rocrate_static_map/new-label').exists()


@pytest.mark.parametrize('change', ['outcomes', 'path'])
def test_sidecar_must_reconcile_report_counts_and_per_field_identity(inputs, change):
    path = inputs[1] / 'CHORUS/processed/CHORUS_crate_mapping_sources.json'
    content = json.loads(path.read_bytes())
    if change == 'outcomes':
        content['rows'][0]['status'] = 'deferred'
    else:
        content['rows'][0]['d4d_path'] = 'Dataset.title'
    path.write_text(json.dumps(content))
    with pytest.raises(ValueError, match='report'):
        prepared(inputs)
    assert not (inputs[2] / 'rocrate_static_map/new-label').exists()


def test_cm4ai_member_hash_is_bound_to_archive_and_extracted_copy(inputs):
    repo, packages, concat, _, add = inputs
    base = add('CM4AI')
    metadata = (base / 'raw/ro-crate-metadata.json').read_bytes()
    archive = base / 'raw/cm4ai_release_metadata.zip'
    with zipfile.ZipFile(archive, 'w') as handle:
        handle.writestr('cm4ai_release_metadata/ro-crate-metadata.json', metadata)
    ready = prepared(inputs, projects=['CM4AI'])
    source = ready['items'][0]['sources'][0]
    assert source['member'] == 'cm4ai_release_metadata/ro-crate-metadata.json'
    assert source['sha256'] == sha(metadata)
    assert source['archive_sha256'] == sha(archive.read_bytes())
    (base / 'raw/ro-crate-metadata.json').write_bytes(b'not the archive copy')
    with pytest.raises(ValueError, match='differs from archive'):
        prepared(inputs, projects=['CM4AI'])


def test_upstream_arm_binds_original_linkml_and_retains_repair_report(inputs):
    _, packages, _, _, add = inputs
    add('CHORUS', upstream=True)
    ready = prepared(inputs, method='rocrate_mapped')
    assert len(ready['items'][0]['sources']) == 2
    manifest = publication.publish(ready, validator=valid)
    assert manifest['method'] == 'rocrate_mapped'
    assert manifest['code_commit_role'] == 'publication_code'
    assert manifest['projects'][0]['producer_binding']['verified'] is False
    assert manifest['projects'][0]['producer_binding']['kind'] == 'unrecorded'
    assert manifest['projects'][0]['retained_reports'] == ['provenance/CHORUS/CHORUS_crate_changes.md']


@pytest.mark.parametrize('label', ['../old-label', 'nested/label', '.'])
def test_label_cannot_target_another_path(inputs, label):
    with pytest.raises(ValueError, match='label'):
        prepared(inputs, label=label)
