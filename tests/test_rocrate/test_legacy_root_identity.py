"""Explicit root identity works through both real legacy construction paths."""
from copy import deepcopy
import importlib
import importlib.util
import json
from pathlib import Path
import sys

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_root_identity import MARKER, resolve_root_identity
from .test_legacy_root_gates import legacy_imports


REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
SENTINEL = b'previous reviewed output\n'


@pytest.fixture(params=['packaged', 'hidden'])
def implementation(request):
    names = dict(builder='d4d_builder', loader='mapping_loader', parser='rocrate_parser',
                 merger='rocrate_merger', scorer='informativeness_scorer')
    if request.param == 'hidden':
        with legacy_imports():
            yield {key: importlib.import_module(name) for key, name in names.items()}
    else:
        yield {key: importlib.import_module('fairscape_integration.utils.' + name)
               for key, name in names.items()}


def mapping(tmp_path, *, marked=True, include_id=True, fields=()):
    path = tmp_path / 'selected.tsv'
    path.write_text(
        'D4D Property\tType\tFAIRSCAPE RO-Crate Property\tFunc\t'
        'Covered by FAIRSCAPE? Yes =1; No = 0\tDirect mapping? Yes =1; No = 0\n'
        + (f'id\tURI\tidentifier,@id\t{MARKER if marked else ""}\t1\t0\n'
           if include_id else '')
        + 'title\tstr\tname\t\t1\t1\n'
        + ''.join(f'{field}\tstr\t{prop}\t\t1\t1\n' for field, prop in fields),
        encoding='utf-8')
    return path


def crate(path, root, *, reverse=False):
    selected = {'@type': 'Dataset', **deepcopy(root)}
    graph = [selected]
    if selected.get('@id'):
        graph = [
            {'@id': 'ro-crate-metadata.json', '@type': 'CreativeWork',
             'about': {'@id': selected['@id']}}, selected,
            {'@id': 'member', '@type': 'Dataset', 'identifier': 'doi:10.9999/Member',
             'name': 'Unselected member'},
        ]
    path.write_text(json.dumps({'@graph': graph[::-1] if reverse else graph}), encoding='utf-8')
    return path


def build(implementation, source, table):
    loader = implementation['loader'].MappingLoader(str(table))
    parser = implementation['parser'].ROCrateParser(str(source))
    return implementation['builder'].D4DBuilder(loader).build_dataset(parser)


@pytest.mark.parametrize('prefix', ['', 'doi:', 'DOI:', 'http://doi.org/',
    'https://doi.org/', 'http://dx.doi.org/', 'HTTPS://DX.DOI.ORG/'])
@pytest.mark.parametrize('reverse', [False, True])
def test_root_scalar_doi_complete_suffix_and_publication(implementation, tmp_path, prefix, reverse):
    value = prefix + '10.1234/MiXeD/Part///'
    source = crate(tmp_path / 'input.json', {'@id': './', 'identifier': value,
                                           'name': 'Selected root'}, reverse=reverse)
    table = mapping(tmp_path)
    before = {path: path.read_bytes() for path in (source, table)}
    record = build(implementation, source, table)
    assert record == {'id': 'doi:10.1234/MiXeD/Part///', 'title': 'Selected root'}
    raw = publication.prepare_dataset(record)
    output = tmp_path / 'record.yaml'
    publication.publish([(output, raw)], protected=[source, table])
    assert yaml.safe_load(output.read_bytes()) == record
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize('identifier', [None, '', ' \t\n'])
def test_fallback_preserves_selected_root_ark(implementation, tmp_path, identifier):
    value = 'ark:59853/Case/Suffix/'
    source = crate(tmp_path / 'input.json', {'@id': value, 'identifier': identifier})
    assert build(implementation, source, mapping(tmp_path))['id'] == value


def test_absent_identifier_falls_back_without_member_selection(implementation, tmp_path):
    source = crate(tmp_path / 'input.json', {'@id': './', 'name': 'Root'})
    assert build(implementation, source, mapping(tmp_path))['id'] == './'


@pytest.mark.parametrize('value', ['https://example.org/Id/', 'ark:12345/Raw/',
    '  doi:10.1234/Untouched/  ', '10.1234/Not A DOI', 'plain asserted identity'])
def test_nonrecognized_scalar_is_not_rewritten(implementation, tmp_path, value):
    source = crate(tmp_path / 'input.json', {'@id': './', 'identifier': value})
    assert build(implementation, source, mapping(tmp_path))['id'] == value


@pytest.mark.parametrize('value', [False, 0, 7, [], ['doi:10.1234/One'],
    ['doi:10.1234/One', 'doi:10.1234/One'], {'@id': 'doi:10.1234/One'}])
def test_present_nonscalar_identifier_refuses_before_state_change(implementation, tmp_path, value):
    table = mapping(tmp_path)
    loader = implementation['loader'].MappingLoader(str(table))
    builder = implementation['builder'].D4DBuilder(loader)
    source = crate(tmp_path / 'good.json', {'@id': './', 'identifier': 'doi:10.1234/Good'})
    previous = deepcopy(builder.build_dataset(implementation['parser'].ROCrateParser(str(source))))
    invalid = crate(tmp_path / 'bad.json', {'@id': './', 'identifier': value})
    before = invalid.read_bytes()
    with pytest.raises(ValueError, match='root identifier must be scalar text'):
        builder.build_dataset(implementation['parser'].ROCrateParser(str(invalid)))
    assert builder.d4d_data == previous
    assert invalid.read_bytes() == before


@pytest.mark.parametrize('value', [False, 0, [], ['ark:123/One'], {'@id': 'ark:123/One'}])
def test_fallback_nonscalar_id_is_not_stringified(value):
    with pytest.raises(ValueError, match='root @id must be scalar text'):
        resolve_root_identity({'@id': value})


def test_missing_identity_remains_missing_and_publication_refuses(implementation, tmp_path):
    source = crate(tmp_path / 'input.json', {'name': 'Anonymous selected Dataset'})
    record = build(implementation, source, mapping(tmp_path))
    assert record == {'title': 'Anonymous selected Dataset'}
    with pytest.raises(publication.PublicationError, match='id'):
        publication.prepare_dataset(record)


@pytest.mark.parametrize('id_first', [False, True])
def test_reverse_mapping_keeps_ordinary_doi_target(implementation, tmp_path, id_first):
    table = mapping(tmp_path, fields=[('doi', 'identifier')])
    lines = table.read_text().splitlines()
    if not id_first:
        lines[1], lines[-1] = lines[-1], lines[1]
        table.write_text('\n'.join(lines) + '\n')
    loader = implementation['loader'].MappingLoader(str(table))
    assert loader.get_d4d_field('identifier') == 'doi'
    assert loader.get_d4d_field('@id') == 'id'
    assert 'id' in loader.get_covered_fields()


def test_custom_no_id_and_unmarked_id_retain_existing_routing(implementation, tmp_path):
    source = crate(tmp_path / 'input.json', {'@id': './', 'identifier': 'doi:10.1234/Custom'})
    table = mapping(tmp_path, include_id=False)
    assert 'id' not in build(implementation, source, table)
    table = mapping(tmp_path, marked=False)
    assert build(implementation, source, table)['id'] == 'doi:10.1234/Custom'
    table.write_text(table.read_text().replace('identifier,@id', 'customId'))
    source = crate(tmp_path / 'custom.json', {'@id': './', 'customId': 'https://example.org/Explicit'})
    assert build(implementation, source, table)['id'] == 'https://example.org/Explicit'


def test_scoring_and_tie_order_exactly_match_table_without_construction_id(implementation, tmp_path):
    paths = [crate(tmp_path / f'{index}.json', root) for index, root in enumerate([
        {'@id': './', 'name': 'A', 'identifier': 'doi:10.1234/A'},
        {'@id': 'ark:123/B', 'name': 'B'}, {'name': 'Anonymous'}])]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    scorer = implementation['scorer'].InformativenessScorer()
    old = implementation['loader'].MappingLoader(str(mapping(tmp_path, include_id=False)))
    new = implementation['loader'].MappingLoader(str(mapping(tmp_path)))
    assert scorer.rank_rocrates(parsers, new) == scorer.rank_rocrates(parsers, old)


@pytest.mark.parametrize('primary_index', [0, 1])
def test_merger_keeps_only_chosen_primary_identity_and_reports_conflict(
        implementation, tmp_path, primary_index):
    paths = [crate(tmp_path / f'{index}.json', {'@id': './', 'name': f'Root {index}',
             'identifier': f'doi:10.1234/Identity{index}/'}) for index in range(2)]
    before = {path: path.read_bytes() for path in paths}
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    merger = implementation['merger'].ROCrateMerger(
        implementation['loader'].MappingLoader(str(mapping(tmp_path))))
    result = merger.merge_rocrates(parsers, primary_index=primary_index, source_names=['A', 'B'])
    assert result['id'] == f'doi:10.1234/Identity{primary_index}/'
    assert merger.provenance['id'] == [['A', 'B'][primary_index]]
    evidence = merger.root_identity_sources
    assert [row['selected_primary'] for row in evidence] == [primary_index == 0, primary_index == 1]
    assert [row['different_written_id'] for row in evidence] == [primary_index != 0, primary_index != 1]
    report = merger.generate_merge_report(parsers, ['A', 'B'])
    assert 'ROOT IDENTITY SELECTION' in report and 'not a source-coverage gain' in report
    assert all(f'doi:10.1234/Identity{index}/' in report for index in range(2))
    assert {path: path.read_bytes() for path in before} == before


def test_secondary_cannot_fill_missing_primary_identity(implementation, tmp_path):
    paths = [crate(tmp_path / 'primary.json', {'name': 'Anonymous primary'}),
             crate(tmp_path / 'secondary.json', {'@id': 'ark:123/Secondary'})]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    merger = implementation['merger'].ROCrateMerger(
        implementation['loader'].MappingLoader(str(mapping(tmp_path))))
    result = merger.merge_rocrates(parsers)
    assert 'id' not in result and 'id' not in merger.provenance
    with pytest.raises(publication.PublicationError, match='id'):
        publication.prepare_dataset(result)


def test_later_ambiguous_identity_preserves_entire_previous_merge(implementation, tmp_path):
    merger = implementation['merger'].ROCrateMerger(
        implementation['loader'].MappingLoader(str(mapping(tmp_path))))
    good = implementation['parser'].ROCrateParser(str(crate(
        tmp_path / 'good.json', {'@id': './', 'identifier': 'doi:10.1234/Good'})))
    merger.merge_rocrates([good])
    before = deepcopy((merger.merged_data, merger.provenance, merger.merge_stats,
                       merger.root_identity_sources, merger.primary_name))
    bad = implementation['parser'].ROCrateParser(str(crate(
        tmp_path / 'bad.json', {'@id': './', 'identifier': ['doi:10.1234/Bad']})))
    with pytest.raises(ValueError, match='bad.json.*scalar text'):
        merger.merge_rocrates([good, bad], source_names=['new good', 'bad'])
    assert (merger.merged_data, merger.provenance, merger.merge_stats,
            merger.root_identity_sources, merger.primary_name) == before


def test_default_mapping_real_cli_publishes_explicit_identity(tmp_path, monkeypatch):
    from data_sheets_schema.cli import cli
    source = crate(tmp_path / 'input.json', {'@id': './', 'identifier': 'https://doi.org/10.1234/Full/',
                                           'name': 'Selected root'})
    output = tmp_path / 'out.yaml'
    before = source.read_bytes()
    monkeypatch.chdir(REPO)
    with legacy_imports():
        result = CliRunner().invoke(cli, ['rocrate', 'transform', str(source), '-o', str(output)])
    assert result.exit_code == 0, result.output
    record = yaml.safe_load(output.read_bytes())
    assert record['id'] == 'doi:10.1234/Full/' and record['doi'] == '10.1234/Full/'
    assert source.read_bytes() == before


def test_default_mapping_other_type_errors_still_refuse(implementation, tmp_path):
    source = crate(tmp_path / 'input.json', {'@id': './', 'identifier': 'doi:10.1234/Valid',
                                           'name': 'Selected root', 'author': {'@id': 'https://orcid.org/explicit-reference'}})
    record = build(implementation, source, DEFAULT)
    assert record['id'] == 'doi:10.1234/Valid'
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(record)


@pytest.mark.parametrize('entrypoint', ['packaged', 'd4d'])
@pytest.mark.parametrize('marked', [False, True])
@pytest.mark.parametrize('only_id', [False, True])
def test_actual_cli_reports_exclude_only_marked_construction_identity(
        tmp_path, monkeypatch, entrypoint, marked, only_id):
    table = mapping(tmp_path, marked=marked,
                    fields=[('description', 'description'), ('language', 'language')])
    if only_id:
        table.write_text('\n'.join(table.read_text().splitlines()[:2]) + '\n')
    source = crate(tmp_path / 'input.json', {'@id': './', 'identifier': 'doi:10.1234/Id',
                                           'name': 'Actual source title'})
    before = {path: path.read_bytes() for path in (table, source)}
    output = tmp_path / 'record.yaml'
    monkeypatch.chdir(REPO)
    with legacy_imports():
        if entrypoint == 'packaged':
            from fairscape_integration.cli import cli
            result = CliRunner().invoke(cli, ['transform', str(source), '-m', str(table),
                                             '-o', str(output), '--report'])
            report_path = tmp_path / 'record_report.txt'
        else:
            from data_sheets_schema.cli import cli
            result = CliRunner().invoke(cli, ['rocrate', 'transform', str(source),
                                             '--mapping', str(table), '-o', str(output)])
            report_path = tmp_path / 'transformation_report.txt'
    assert result.exit_code == 0, result.output
    assert yaml.safe_load(output.read_bytes())['id'] == 'doi:10.1234/Id'
    count = (0 if only_id else 1) + (0 if marked else 1)
    denominator = (0 if only_id else 3) + (0 if marked else 1)
    percentage = count / denominator * 100 if denominator else 0
    report = report_path.read_text()
    if entrypoint == 'packaged':
        assert f'Constructed output keys: {count}/{denominator}' in report
        assert f'Constructed-field presence (output keys; null-valued keys included): {percentage:.1f}%' in report
        assert f'Constructed-field presence (output keys; null-valued keys included): {percentage:.1f}%' in result.output
    else:
        assert f'Constructed-field presence (output keys; null-valued keys included): {count}/{denominator} ({percentage:.1f}%)' in report
        assert f'Constructed-field presence (output keys; null-valued keys included): {count}/{denominator} mapped fields' in result.output
        assert f'Construction percentage: {percentage:.1f}%' in result.output
    assert ('Required Dataset.id construction is excluded' in report) is marked
    assert {path: path.read_bytes() for path in before} == before


def test_dataset_api_batch_ambiguous_later_id_preserves_all_outputs(tmp_path, monkeypatch):
    inputs, outputs = tmp_path / 'inputs', tmp_path / 'outputs'
    inputs.mkdir()
    outputs.mkdir()
    paths = [crate(inputs / 'a.json', {'@id': './', 'identifier': 'doi:10.1234/A'}),
             crate(inputs / 'z.json', {'@id': './', 'identifier': ['doi:10.1234/Z']})]
    table = mapping(tmp_path)
    for name in ('a_d4d.yaml', 'z_d4d.yaml'):
        (outputs / name).write_bytes(SENTINEL)
    before = {path: path.read_bytes() for path in [*paths, table, *outputs.iterdir()]}
    monkeypatch.chdir(REPO)
    with legacy_imports():
        spec = importlib.util.spec_from_file_location(
            '_root_gates_transform_api', REPO / 'src/transformation/transform_api.py')
        api = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)
        with pytest.raises(ValueError, match='scalar text'):
            api.batch_transform_rocrates(inputs, outputs, mapping_file=table,
                                        result_contract='dataset_v1', validate=False)
    assert {path: path.read_bytes() for path in before} == before
