"""Opted-in API results retain provenance outside accepted Dataset bytes."""
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import yaml

from .test_legacy_publication import legacy, mapping, crate, ID, SOURCE_TEXT, REPO, SENTINEL


def configured(api, mapping, **kwargs):
    return api.SemanticTransformer(api.TransformationConfig(
        mapping_file=mapping, validate_input=False, validate_output=False,
        **kwargs))


def assert_publication(metadata, path, encoding):
    raw = path.read_bytes()
    assert metadata['publication'] == {
        'format': 'd4d_dataset_publication_v1', 'path': str(path.resolve()),
        'sha256': sha256(raw).hexdigest(), 'bytes': len(raw),
        'encoding': encoding, 'root_class': 'Dataset'}


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-16'])
def test_single_preserves_provenance_and_exact_accepted_bytes(
        legacy, mapping, tmp_path, monkeypatch, encoding):
    _, _, api = legacy
    source = crate(tmp_path / 'input.json')
    source_before = source.read_bytes()
    transformer = configured(api, mapping, result_contract='dataset_v1',
                             output_encoding=encoding)
    output = tmp_path / 'out' / 'dataset.yaml'
    prepared = []
    original = api.prepare_dataset

    def prepare(*args, **kwargs):
        raw = original(*args, **kwargs)
        prepared.append(raw)
        return raw

    monkeypatch.setattr(api, 'prepare_dataset', prepare)
    result = transformer.rocrate_to_d4d(source, output_path=output)
    assert result.data == {'id': ID, 'title': 'Café control',
                           'description': SOURCE_TEXT, 'keywords': ['one', 'two']}
    assert yaml.safe_load(output.read_bytes().decode(encoding)) == result.data
    assert prepared == [output.read_bytes()]
    metadata = result.transformation_metadata
    assert metadata['source'] == str(source)
    assert metadata['mapping'] == {
        'path': str(mapping.resolve()), 'sha256': sha256(mapping.read_bytes()).hexdigest(),
        'bytes': len(mapping.read_bytes())}
    assert result.mapping_version == metadata['mapping_version'] == 'sha256:' + metadata['mapping']['sha256']
    assert result.timestamp == metadata['transformation_date']
    assert_publication(metadata, output, encoding)
    assert source.read_bytes() == source_before


def test_default_draft_and_explicit_draft_have_distinct_documented_shapes(legacy, mapping, tmp_path):
    _, _, api = legacy
    source = crate(tmp_path / 'input.json')
    transformer = configured(api, mapping)
    old = transformer.rocrate_to_d4d(source)
    new = transformer.rocrate_to_d4d(source, result_contract='dataset_v1')
    assert set(asdict(old)) == set(asdict(new))
    assert old.mapping_version == 'v2_semantic'
    assert old.data['transformation_metadata'] is old.transformation_metadata
    assert 'transformation_metadata' not in new.data
    assert new.transformation_metadata['publication'] is None
    assert old.coverage_percentage == new.coverage_percentage
    assert old.unmapped_fields == new.unmapped_fields
    assert transformer.config.result_contract == 'legacy'
    assert not list(tmp_path.glob('*.yaml'))


@pytest.mark.parametrize('preserve', [True, False])
def test_merge_explicit_envelope_and_legacy_draft(legacy, mapping, tmp_path, monkeypatch, preserve):
    _, _, api = legacy
    monkeypatch.setattr(sys.modules['rocrate_merger'], 'datetime',
                        SimpleNamespace(now=lambda: datetime(2026, 10, 7)))
    source = crate(tmp_path / 'input.json')
    transformer = configured(api, mapping, preserve_provenance=preserve)
    old = transformer.merge_rocrates([source], auto_prioritize=False)
    output = tmp_path / 'merge.yaml'
    new = transformer.merge_rocrates([source], output_path=output,
                                     auto_prioritize=False, result_contract='dataset_v1')
    assert set(old) == {'d4d', 'merge_report', 'source_presence'}
    assert set(new) == {'format', 'data', 'transformation_metadata', 'merge_report', 'source_presence'}
    assert old['source_presence'] == new['source_presence']
    assert new['source_presence']['reason'] == 'different_source_property'
    assert new['format'] == 'd4d_transformation_result_v1'
    assert new['merge_report'] == old['merge_report']
    assert yaml.safe_load(output.read_bytes()) == new['data']
    assert 'transformation_metadata' not in new['data']
    if preserve:
        assert 'transformation_metadata' in old['d4d']
        assert new['transformation_metadata']['sources'] == [str(source)]
        assert new['transformation_metadata']['source_order'] == [str(source)]
        assert 'merge_strategy' not in new['transformation_metadata']
        assert new['transformation_metadata']['configured_merge_strategy'] == 'merge'
        assert_publication(new['transformation_metadata'], output, 'utf-8')
    else:
        assert 'transformation_metadata' not in old['d4d']
        assert new['transformation_metadata'] is None


def test_explicit_no_provenance_stays_disabled(legacy, mapping, tmp_path):
    _, _, api = legacy
    transformer = configured(api, mapping, result_contract='dataset_v1', preserve_provenance=False)
    source = crate(tmp_path / 'input.json')
    result = transformer.rocrate_to_d4d(source, tmp_path / 'out.yaml')
    assert result.transformation_metadata is None
    assert 'transformation_metadata' not in result.data
    assert result.mapping_version == 'sha256:' + sha256(mapping.read_bytes()).hexdigest()


def test_batch_binds_each_published_record_and_preserves_inputs(legacy, mapping, tmp_path):
    _, _, api = legacy
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    sources = [crate(inputs / 'b.json', title='second'), crate(inputs / 'a.json', title='first')]
    before = {path: path.read_bytes() for path in sources}
    output = tmp_path / 'outputs'
    results = api.batch_transform_rocrates(inputs, output, result_contract='dataset_v1',
                                         mapping_file=str(mapping))
    assert [item.data['title'] for item in results] == ['first', 'second']
    for result, name in zip(results, ['a_d4d.yaml', 'b_d4d.yaml']):
        assert yaml.safe_load((output / name).read_bytes()) == result.data
        assert_publication(result.transformation_metadata, output / name, 'utf-8')
    assert {path: path.read_bytes() for path in sources} == before


@pytest.mark.parametrize('command', ['transform', 'batch', 'merge'])
def test_opted_in_cli_emits_parseable_results_without_switching_yaml_file_format(
        legacy, mapping, tmp_path, capsys, command):
    _, _, api = legacy
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    first = crate(inputs / 'a.json')
    second = crate(inputs / 'b.json')
    output = tmp_path / ('outputs' if command == 'batch' else 'output.yaml')
    args = {'transform': [str(first), str(output)],
            'batch': [str(inputs), str(output)],
            'merge': [str(output), str(first), str(second)]}[command]
    capsys.readouterr()
    api.main([command, *args, '--result-contract', 'dataset_v1', '--mapping', str(mapping)])
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert document['format'] == 'd4d_transformation_result_v1'
    rows = document['results'] if command == 'batch' else [document]
    for row in rows:
        assert row['transformation_metadata']['publication']['root_class'] == 'Dataset'
        assert row['transformation_metadata']['mapping']['sha256'] == sha256(mapping.read_bytes()).hexdigest()
        assert 'transformation_metadata' not in row['data']
        published = row['transformation_metadata']['publication']['path']
        assert yaml.safe_load(Path(published).read_bytes()) == row['data']
    assert captured.err  # Legacy progress is retained away from JSON stdout.


def test_convenience_accepts_explicit_mapping_without_changing_default_provenance(legacy, mapping, tmp_path):
    _, _, api = legacy
    source = crate(tmp_path / 'input.json')
    output = tmp_path / 'dataset.yaml'
    result = api.transform_rocrate_file(source, output, mapping_file=mapping,
                                        result_contract='dataset_v1')
    assert result.data['id'] == ID
    assert result.transformation_metadata is not None
    assert result.transformation_metadata['mapping']['path'] == str(mapping.resolve())
    assert_publication(result.transformation_metadata, output, 'utf-8')


@pytest.mark.parametrize('operation', ['convenience', 'batch'])
def test_explicit_helper_mapping_is_protected_from_output_replacement(legacy, mapping, tmp_path, operation):
    _, _, api = legacy
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    source = crate(inputs / 'source.json')
    if operation == 'batch':
        destination = tmp_path / 'source_d4d.yaml'
        mapping.rename(destination)
        mapping = destination  # Selection uses content, not the TSV suffix.
    before = mapping.read_bytes()
    with pytest.raises(api.PublicationError, match='overlap'):
        if operation == 'convenience':
            api.transform_rocrate_file(source, mapping, mapping_file=mapping,
                                       result_contract='dataset_v1', validate=False)
        else:
            api.batch_transform_rocrates(inputs, tmp_path, mapping_file=mapping,
                                        result_contract='dataset_v1', validate=False)
    assert mapping.read_bytes() == before


@pytest.mark.parametrize('command', ['transform', 'batch', 'merge'])
@pytest.mark.parametrize('selection', ['default_table', 'legacy_contract'])
def test_cli_does_not_silently_replace_default_table_or_legacy_contract(
        legacy, mapping, tmp_path, monkeypatch, capsys, command, selection):
    _, _, api = legacy
    # Resolve the real unchanged default exactly as documented, without any
    # substituted TransformationConfig or validator.
    monkeypatch.chdir(REPO)
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    first = crate(inputs / 'a.json')
    second = crate(inputs / 'b.json')
    output = tmp_path / ('outputs' if command == 'batch' else 'output.yaml')
    if command == 'batch':
        output.mkdir()
        destinations = [output / 'a_d4d.yaml', output / 'b_d4d.yaml']
    else:
        destinations = [output]
    for destination in destinations:
        destination.write_bytes(SENTINEL)
    args = {'transform': [str(first), str(output)],
            'batch': [str(inputs), str(output)],
            'merge': [str(output), str(first), str(second)]}[command]
    options = (['--result-contract', 'dataset_v1'] if selection == 'default_table'
               else ['--mapping', str(mapping)])
    capsys.readouterr()
    with pytest.raises(api.PublicationError):
        api.main([command, *args, *options])
    assert {path: path.read_bytes() for path in destinations} == {
        path: SENTINEL for path in destinations}
    assert '"format": "d4d_transformation_result_v1"' not in capsys.readouterr().out
