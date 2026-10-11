"""Creator assertions survive real legacy construction and mandatory publication."""
from copy import deepcopy
import csv
import json
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_creators import MARKER, REFERENCE_MARKER, KEY_BASIS_LABEL, VALUE_BASIS_LABEL
from .test_legacy_root_identity import implementation, crate
from .test_legacy_publication import legacy


REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
TEXT = '  Alice¹, Smith, B.\n¹ Institute; café — no inferred affiliations.\n'
SENTINEL = b'Previously reviewed output\n'
ABSENT = object()


def table(tmp_path, *, marked=True, source='author', field_type='str', extra=''):
    path = tmp_path / 'selected.tsv'
    path.write_text(
        f'D4D Property\tType\tFAIRSCAPE RO-Crate Property\tFunc\t{COVERED}\t'
        'Direct mapping? Yes =1; No = 0\n'
        'id\tURI\tidentifier,@id\troot_identifier_v1\t1\t0\n'
        'title\tstr\tname\t\t1\t1\n'
        f'creators\t{field_type}\t{source}\t{MARKER if marked else ""}\t1\t1\n'
        + extra, encoding='utf-8')
    return path


def input_file(path, value=ABSENT, *, reverse=False):
    root = {'@id': './', 'identifier': 'doi:10.1234/Source/', 'name': 'Selected root'}
    if value is not ABSENT:
        root['author'] = deepcopy(value)
    crate(path, root, reverse=reverse)
    document = json.loads(path.read_text())
    for item in document['@graph']:
        if item.get('@id') == 'member':
            item['author'] = ['Member author must not be borrowed']
    path.write_text(json.dumps(document), encoding='utf-8')
    return path


def build(implementation, path, mapping):
    parser = implementation['parser'].ROCrateParser(str(path))
    loader = implementation['loader'].MappingLoader(str(mapping))
    builder = implementation['builder'].D4DBuilder(loader)
    return builder.build_dataset(parser), parser, builder


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


@pytest.mark.parametrize('text', [TEXT, '', ' \t\n', 'Smith, B.', 'https://orcid.org/literal'])
@pytest.mark.parametrize('reverse', [False, True])
def test_whole_literal_is_a_description_not_an_inferred_person(implementation, tmp_path, text, reverse):
    path = input_file(tmp_path / 'input.json', text, reverse=reverse)
    mapping = table(tmp_path)
    before = {p: p.read_bytes() for p in (path, mapping)}
    result, _, _ = build(implementation, path, mapping)
    assert result == {'id': 'doi:10.1234/Source/', 'title': 'Selected root',
                      'creators': [{'description': text}]}
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('field_type', ['int', 'bool', 'date', 'list[str]', 'URI'])
def test_marker_precedes_generic_coercion(implementation, tmp_path, field_type):
    result, _, _ = build(implementation, input_file(tmp_path / 'source.json', TEXT),
                         table(tmp_path, field_type=field_type))
    assert result['creators'] == [{'description': TEXT}]


def test_mixed_assertion_types_duplicates_and_detachment(implementation, tmp_path):
    values = ['Alice', 'Alice', {'description': 'Alice'}, {'@id': 'https://orcid.org/x'},
              {'@type': 'Person', 'name': 'Explicit name', 'affiliation': {'@id': 'org'}},
              False, 0, None, ['nested', False], {'unknown': ['same', 'same']}]
    path = input_file(tmp_path / 'source.json', values)
    result, parser, _ = build(implementation, path, table(tmp_path))
    expected = [{'description': 'Alice'}, {'description': 'Alice'}, *deepcopy(values[2:])]
    assert encoded(result['creators']) == encoded(expected)
    with pytest.raises(publication.PublicationError, match='creators'):
        publication.prepare_dataset(result)
    result['creators'][4]['affiliation']['@id'] = 'caller mutation'
    result['creators'][8].append('extra')
    assert encoded(parser.require_root_dataset()['author']) == encoded(values)
    assert encoded(json.loads(path.read_text())['@graph'][1]['author']) == encoded(values)


@pytest.mark.parametrize('value', [False, 0, {'@id': 'https://orcid.org/x'}, [None]])
def test_nonliteral_assertions_are_preserved_and_refused(implementation, tmp_path, value):
    result, _, _ = build(implementation, input_file(tmp_path / 'source.json', value), table(tmp_path))
    expected = value if isinstance(value, list) else [value]
    assert encoded(result['creators']) == encoded(expected)
    with pytest.raises(publication.PublicationError, match='creators'):
        publication.prepare_dataset(result)


@pytest.mark.parametrize('value', [ABSENT, None, []])
@pytest.mark.parametrize('reverse', [False, True])
def test_selected_root_missing_null_and_empty_never_borrow_members(implementation, tmp_path, value, reverse):
    result, _, _ = build(implementation, input_file(tmp_path / 'source.json', value, reverse=reverse), table(tmp_path))
    if value == []:
        assert result['creators'] == []
    else:
        assert 'creators' not in result


@pytest.mark.parametrize('conflict', ['duplicate_root', 'descriptor'])
def test_ambiguous_root_refuses_before_a_previous_creator_result_changes(implementation, tmp_path, conflict):
    source = input_file(tmp_path / 'source.json', TEXT)
    result, _, builder = build(implementation, source, table(tmp_path))
    previous = deepcopy(result)
    document = json.loads(source.read_text())
    if conflict == 'duplicate_root':
        document['@graph'].append(deepcopy(document['@graph'][1]))
    else:
        document['@graph'].append({'@id': 'ro-crate-metadata.jsonld', '@type': 'CreativeWork',
                                  'about': {'@id': 'member'}})
    source.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        parser = implementation['parser'].ROCrateParser(str(source))
        builder.build_dataset(parser)
    assert builder.d4d_data == previous


@pytest.mark.parametrize('invalid', ['uncovered', 'wrong_source', 'wrong_target', 'duplicate', 'competing'])
def test_named_route_refuses_ambiguous_or_misplaced_activation(implementation, tmp_path, invalid):
    path = table(tmp_path)
    source = path.read_text()
    row = f'creators\tstr\tauthor\t{MARKER}\t1\t1\n'
    replacement = {
        'uncovered': row.replace('\t1\t1\n', '\t0\t1\n'),
        'wrong_source': row.replace('\tauthor\t', '\towner,author\t'),
        'wrong_target': row.replace('creators\t', 'created_by\t'),
        'duplicate': row + row,
        'competing': 'creators\tstr\towner\t\t1\t1\n' + row,
    }[invalid]
    path.write_text(source.replace(row, replacement))
    with pytest.raises(ValueError, match=MARKER):
        implementation['loader'].MappingLoader(str(path))


def test_unmarked_custom_behavior_and_other_fields_remain(implementation, tmp_path):
    mapping = table(tmp_path, marked=False, extra='created_by\tstr\towner\t\t1\t1\n')
    path = input_file(tmp_path / 'source.json', ['Alice', 'Alice'])
    document = json.loads(path.read_text()); document['@graph'][1]['owner'] = {'name': 'Owner'}
    path.write_text(json.dumps(document))
    old, _, _ = build(implementation, path, mapping)
    mapping.write_text(mapping.read_text().replace('creators\tstr\tauthor\t\t',
                                                  f'creators\tstr\tauthor\t{MARKER}\t'))
    new, _, _ = build(implementation, path, mapping)
    assert old['creators'] == ['Alice', 'Alice']
    assert new['creators'] == [{'description': 'Alice'}, {'description': 'Alice'}]
    assert {k: v for k, v in old.items() if k != 'creators'} == {
        k: v for k, v in new.items() if k != 'creators'}
    assert new['created_by'] == 'Owner'


def test_default_table_has_only_explicit_creator_marker_and_historical_labels(implementation):
    with DEFAULT.open(newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert len(rows) == 84
    loader = implementation['loader'].MappingLoader(str(DEFAULT))
    assert len(loader.mappings) == 83 and len(loader.covered_mappings) == 82
    selected = [row for row in rows if row['Func'] == REFERENCE_MARKER]
    assert len(selected) == 1
    assert selected[0]['D4D Property'] == 'creators'
    assert selected[0]['FAIRSCAPE RO-Crate Property'] == 'author'
    assert selected[0]['Type'] == 'str'
    assert selected[0]['SKOS_Relation'] == 'http://www.w3.org/2004/02/skos/core#closeMatch'
    assert selected[0]['Information_Loss'] == 'minimal'


def test_real_merge_preserves_every_assertion_and_records_half_open_ranges(implementation, tmp_path):
    values = [['Alice', {'description': 'Alice'}], [], ['Alice', {'@id': 'person'}], None]
    paths = [input_file(tmp_path / f'{i}.json', value) for i, value in enumerate(values)]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    merger = implementation['merger'].ROCrateMerger(implementation['loader'].MappingLoader(str(table(tmp_path))))
    result = merger.merge_rocrates(parsers, primary_index=2, source_names=['First', 'Empty', 'Chosen', 'Null'])
    assert result['creators'] == [{'description': 'Alice'}, {'@id': 'person'},
                                 {'description': 'Alice'}, {'description': 'Alice'}]
    assert merger.get_provenance()['creators'] == ['Chosen', 'First', 'Empty']
    ledger = merger.get_creator_assertion_sources()
    assert [row['source_index'] for row in ledger] == [2, 0, 1, 3]
    assert [row['processing_index'] for row in ledger] == [0, 1, 2, 3]
    assert [row['output_range'] for row in ledger] == [[0, 2], [2, 4], [4, 4], [4, 4]]
    assert [row['raw_value'] for row in ledger] == [values[2], values[0], [], None]
    assert merger.get_merge_stats()['fields_merged_as_arrays'] == 1
    report = merger.generate_merge_report(parsers)
    assert 'CREATOR ASSERTION CONSTRUCTION' in report and 'ROOT AUTHOR SOURCE PRESENCE' in report
    assert 'Total constructed Dataset fields' in report
    ledger[0]['raw_value'][1]['@id'] = 'changed'
    assert merger.get_creator_assertion_sources()[0]['raw_value'][1]['@id'] == 'person'
    assert parsers[2].require_root_dataset()['author'] == values[2]


@pytest.mark.parametrize('values,present', [([None, ABSENT], False), ([None, []], True)])
def test_merge_omission_and_explicit_empty_list_stay_distinct(implementation, tmp_path, values, present):
    parsers = [implementation['parser'].ROCrateParser(str(input_file(tmp_path / f'{i}.json', value)))
               for i, value in enumerate(values)]
    merger = implementation['merger'].ROCrateMerger(implementation['loader'].MappingLoader(str(table(tmp_path))))
    result = merger.merge_rocrates(parsers)
    assert ('creators' in result) is present
    if present:
        assert result['creators'] == []
    assert [row['output_range'] for row in merger.get_creator_assertion_sources()] == [[0, 0], [0, 0]]
    assert merger.get_merge_stats()['fields_merged_as_arrays'] == int(present)


@pytest.mark.parametrize('entrypoint', ['packaged', 'd4d'])
@pytest.mark.parametrize('value', [TEXT, {'@id': 'https://orcid.org/x'}])
def test_actual_cli_publication_and_reports(legacy, tmp_path, monkeypatch, entrypoint, value):
    source = input_file(tmp_path / 'source.json', value)
    mapping = table(tmp_path)
    output = tmp_path / 'dataset.yaml'; output.write_bytes(SENTINEL)
    report = tmp_path / ('dataset_report.txt' if entrypoint == 'packaged' else 'transformation_report.txt')
    report.write_bytes(SENTINEL)
    before = {p: p.read_bytes() for p in (source, mapping)}
    monkeypatch.chdir(REPO)
    if entrypoint == 'packaged':
        from fairscape_integration.cli import cli
        args = ['transform', str(source), '-m', str(mapping), '-o', str(output), '--report']
    else:
        from data_sheets_schema.cli import cli
        args = ['rocrate', 'transform', str(source), '--mapping', str(mapping), '-o', str(output)]
    result = CliRunner().invoke(cli, args)
    if isinstance(value, str):
        assert result.exit_code == 0, result.output
        assert yaml.safe_load(output.read_bytes())['creators'] == [{'description': value}]
        assert KEY_BASIS_LABEL in result.output and KEY_BASIS_LABEL in report.read_text()
        assert 'not source coverage or validation success' in report.read_text()
        assert json.dumps(value, ensure_ascii=False) in report.read_text()
        assert 'immediate_assertion_units' in result.output
    else:
        assert result.exit_code == 1 and 'creators' in result.output
        assert output.read_bytes() == report.read_bytes() == SENTINEL
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('contract', ['legacy', 'dataset_v1'])
@pytest.mark.parametrize('provenance', [False, True])
def test_api_measurement_survives_provenance_choice(legacy, tmp_path, contract, provenance):
    _, _, api = legacy
    source = input_file(tmp_path / 'source.json', [TEXT, TEXT])
    instance = api.SemanticTransformer(api.TransformationConfig(
        mapping_file=table(tmp_path), validate_input=False, validate_output=False,
        preserve_provenance=provenance, result_contract=contract))
    result = instance.rocrate_to_d4d(source)
    assert result.data['creators'] == [{'description': TEXT}, {'description': TEXT}]
    assert result.coverage_percentage == 100.0 and result.unmapped_fields == []
    assert result.coverage_basis == {'kind': 'constructed_field_presence',
        'count_rule': 'non_null_mapped_value', 'numerator': 2, 'denominator': 2,
        'is_source_coverage': False, 'is_validation_success': False}
    row = result.source_presence['sources'][0]
    assert row['raw_value'] == [TEXT, TEXT] and row['immediate_assertion_units'] == 2
    assert row['source_name'] == str(source)
    if provenance:
        assert result.transformation_metadata['coverage_basis'] == result.coverage_basis
        assert result.transformation_metadata['coverage_basis'] is not result.coverage_basis
    else:
        assert result.transformation_metadata is None and 'transformation_metadata' not in result.data
    assert 'source_presence' not in result.data


def test_later_invalid_batch_preserves_all_publication_destinations(legacy, tmp_path):
    _, _, api = legacy
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    good = input_file(inputs / 'a.json', TEXT)
    bad = input_file(inputs / 'z.json', {'@id': 'https://orcid.org/x'})
    outputs = tmp_path / 'outputs'; outputs.mkdir()
    paths = [outputs / name for name in ('a_d4d.yaml', 'z_d4d.yaml')]
    for path in paths:
        path.write_bytes(SENTINEL)
    mapping = table(tmp_path)
    before = {p: p.read_bytes() for p in [good, bad, mapping, *paths]}
    with pytest.raises(publication.PublicationError, match='creators'):
        api.batch_transform_rocrates(inputs, outputs, result_contract='dataset_v1',
                                     mapping_file=mapping, validate=False)
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('command', ['transform', 'batch', 'merge'])
def test_real_api_cli_json_exposes_measurements_without_dataset_pollution(legacy, tmp_path, capsys, command):
    _, _, api = legacy
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    first = input_file(inputs / 'a.json', TEXT)
    second = input_file(inputs / 'b.json', ['Other', 'Other'])
    output = tmp_path / ('outputs' if command == 'batch' else 'dataset.yaml')
    args = {'transform': [str(first), str(output)], 'batch': [str(inputs), str(output)],
            'merge': [str(output), str(first), str(second)]}[command]
    capsys.readouterr()
    api.main([command, *args, '--result-contract', 'dataset_v1', '--mapping', str(table(tmp_path))])
    document = json.loads(capsys.readouterr().out)
    rows = document['results'] if command == 'batch' else [document]
    for row in rows:
        assert row['source_presence']['status'] == 'measured'
        assert 'source_presence' not in row['data']
        if command != 'merge':
            assert row['validation_passed'] is True
            assert row['validation_errors'] == []
            assert row['coverage_basis']['kind'] == 'constructed_field_presence'
            assert row['transformation_metadata']['coverage_basis'] == row['coverage_basis']
        else:
            assert 'coverage_percentage' not in row
            assert len(row['data']['creators']) == 3


@pytest.mark.parametrize('command', ['transform', 'batch', 'merge'])
def test_real_api_legacy_cli_summaries_name_the_measurement(legacy, tmp_path, capsys, monkeypatch, command):
    _, _, api = legacy
    # The CLI's default legacy provenance would itself be refused by the
    # Dataset gate. Exercise its summary with a real supported API config
    # that disables provenance, without replacing any producer or validator.
    original_config = api.TransformationConfig
    monkeypatch.setattr(api, 'TransformationConfig',
                        lambda **kwargs: original_config(preserve_provenance=False, **kwargs))
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    source = input_file(inputs / 'a.json', TEXT)
    second = input_file(inputs / 'b.json', ['Other', 'Other']) if command == 'merge' else None
    output = tmp_path / ('outputs' if command == 'batch' else 'dataset.yaml')
    args = {'transform': [str(source), str(output)], 'batch': [str(inputs), str(output)],
            'merge': [str(output), str(source), str(second)]}[command]
    capsys.readouterr()
    api.main([command, *args, '--mapping', str(table(tmp_path))])
    text = capsys.readouterr().out
    assert 'ROOT AUTHOR SOURCE PRESENCE' in text and 'immediate_assertion_units' in text
    if command != 'merge':
        assert VALUE_BASIS_LABEL in text
        assert 'Construction counts are not source coverage or validation success.' in text
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.startswith('{')]
        assert len(rows) == 2
        assert {row['source_name'] for row in rows} == {'a', 'b'}
        assert sorted(row['immediate_assertion_units'] for row in rows) == [1, 2]
        assert [row['processing_index'] for row in rows] == [0, 1]
        assert sum(row['selected_primary'] for row in rows) == 1
        assert VALUE_BASIS_LABEL not in text and 'Construction percentage:' not in text
        assert 'coverage_percentage' not in text
