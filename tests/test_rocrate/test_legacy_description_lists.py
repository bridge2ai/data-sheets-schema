"""#4913: whole protocol assertions become explicit description objects only."""
from copy import deepcopy
import csv
import json
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_description_lists import MARKER, ROUTES
from .test_legacy_root_identity import implementation, crate
from .test_legacy_root_gates import legacy_imports


REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
TEXT = '  Whole protocol; do not split, trim or infer.\nCafé — repeat.\n'
SENTINEL = b'previous reviewed output\n'
ABSENT = object()


def table(tmp_path, *, marker=MARKER, field_type=''):
    path = tmp_path / 'selected.tsv'
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['D4D Property', 'Type', 'FAIRSCAPE RO-Crate Property', 'Func',
                         COVERED, 'Direct mapping? Yes =1; No = 0'])
        writer.writerow(['id', 'URI', 'identifier,@id', 'root_identifier_v1', '1', '0'])
        writer.writerow(['title', 'str', 'name', '', '1', '1'])
        for field, source in ROUTES.items():
            writer.writerow([field, field_type, source, marker, '1', '1'])
    return path


def source_file(path, values, *, reverse=False, extra=None):
    root = {'@id': './', 'identifier': 'doi:10.1234/WholeText', 'name': 'Selected root'}
    for field, value in values.items():
        if value is not ABSENT:
            root[ROUTES[field]] = deepcopy(value)
    root.update(extra or {})
    crate(path, root, reverse=reverse)
    content = json.loads(path.read_text())
    member = next(row for row in content['@graph'] if row.get('@id') == 'member')
    member.update({source: 'Member-only text must not become root text.' for source in ROUTES.values()})
    path.write_text(json.dumps(content), encoding='utf-8')
    return path


def build(implementation, source, mapping):
    parser = implementation['parser'].ROCrateParser(str(source))
    builder = implementation['builder'].D4DBuilder(implementation['loader'].MappingLoader(str(mapping)))
    return builder.build_dataset(parser), parser, builder


def assert_same(left, right):
    # JSON spellings distinguish False from zero as well as retaining structure.
    assert json.dumps(left, sort_keys=True, ensure_ascii=False) == json.dumps(
        right, sort_keys=True, ensure_ascii=False)


@pytest.mark.parametrize('reverse', [False, True])
def test_all_four_routes_preserve_whole_units_and_real_publication(implementation, tmp_path, reverse):
    values = {'preprocessing_strategies': [TEXT, 'duplicate', 'duplicate', ''],
              'cleaning_strategies': TEXT, 'labeling_strategies': '',
              'annotation_analyses': [' \t\n', 'First. Second; still one unit.']}
    expected = {'preprocessing_strategies': [{'description': TEXT}, {'description': 'duplicate'},
                                           {'description': 'duplicate'}, {'description': ''}],
                'cleaning_strategies': [{'description': TEXT}],
                'labeling_strategies': [{'description': ''}],
                'annotation_analyses': [{'description': ' \t\n'},
                                        {'description': 'First. Second; still one unit.'}]}
    source = source_file(tmp_path / 'source.json', values, reverse=reverse)
    mapping = table(tmp_path, field_type='int')  # Explicit constructors precede generic coercion.
    before = {p: p.read_bytes() for p in (source, mapping)}
    record, parser, builder = build(implementation, source, mapping)
    assert {field: record[field] for field in ROUTES} == expected
    assert record['title'] == 'Selected root' and record['id'] == 'doi:10.1234/WholeText'
    for field, raw in values.items():
        assert builder.apply_field_transformation(field, raw) == expected[field]
    output = tmp_path / 'record.yaml'
    publication.publish([(output, publication.prepare_dataset(record))], protected=[source, mapping])
    assert yaml.safe_load(output.read_bytes()) == record
    record['preprocessing_strategies'][0]['description'] = 'changed result'
    record['preprocessing_strategies'].append({'description': 'new result'})
    assert builder.build_dataset(parser)['preprocessing_strategies'] == expected['preprocessing_strategies']
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('value', [ABSENT, None])
def test_absent_root_never_borrows_members(implementation, tmp_path, value):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(ROUTES, value), reverse=True)
    record, _, _ = build(implementation, source, table(tmp_path))
    assert set(record) == {'id', 'title'}
    publication.prepare_dataset(record)


@pytest.mark.parametrize('value,expected', [
    (False, False), (0, 0), (5, 5),
    (['whole', False], [{'description': 'whole'}, False]),
    (['whole', 0], [{'description': 'whole'}, 0]),
    (['whole', None], [{'description': 'whole'}, None]),
    (['whole', ['nested', 'nested']], [{'description': 'whole'}, ['nested', 'nested']]),
    (['whole', {'@id': 'urn:reference'}], [{'description': 'whole'}, {'@id': 'urn:reference'}]),
    ({'description': 'scalar object is not a list'}, {'description': 'scalar object is not a list'}),
])
def test_unsupported_units_are_not_laundered_and_publication_refuses(
        implementation, tmp_path, value, expected):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(ROUTES, value))
    record, parser, _ = build(implementation, source, table(tmp_path))
    for field in ROUTES:
        assert_same(record[field], expected)
        assert_same(parser.require_root_dataset()[ROUTES[field]], value)
    output = tmp_path / 'record.yaml'; output.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError):
        publication.publish([(output, publication.prepare_dataset(record))], protected=[source])
    assert output.read_bytes() == SENTINEL
    if isinstance(value, list):
        record['preprocessing_strategies'].append('changed result')
        assert_same(parser.require_root_dataset()[ROUTES['preprocessing_strategies']], value)


def test_existing_structured_units_detach_and_empty_lists_remain_empty(implementation, tmp_path):
    values = {'preprocessing_strategies': [{'description': TEXT}, 'additional text'],
              'cleaning_strategies': [], 'labeling_strategies': [], 'annotation_analyses': []}
    source = source_file(tmp_path / 'source.json', values)
    record, parser, _ = build(implementation, source, table(tmp_path))
    assert record['preprocessing_strategies'] == [{'description': TEXT}, {'description': 'additional text'}]
    assert all(record[field] == [] for field in ('cleaning_strategies', 'labeling_strategies', 'annotation_analyses'))
    publication.prepare_dataset(record)
    record['preprocessing_strategies'][0]['description'] = 'changed nested output'
    assert parser.require_root_dataset()[ROUTES['preprocessing_strategies']] == values['preprocessing_strategies']


@pytest.mark.parametrize('marker', ['', 'custom_function_not_executed'])
def test_unmarked_custom_routes_retain_generic_behavior(implementation, tmp_path, marker):
    values = {'preprocessing_strategies': TEXT, 'cleaning_strategies': ['same', 'same'],
              'labeling_strategies': TEXT, 'annotation_analyses': ['a', 'b']}
    mapping = table(tmp_path, marker=marker)
    source = source_file(tmp_path / 'source.json', values)
    record, _, _ = build(implementation, source, mapping)
    for field, expected in values.items():
        assert record[field] == expected
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(record)


@pytest.mark.parametrize('change', ['wrong_target', 'header_target', 'blank_target', 'uncovered',
                                   'wrong_source', 'multiple_sources', 'duplicate', 'competing_unmarked'])
def test_invalid_marked_route_refuses_before_filtering(implementation, tmp_path, change):
    path = table(tmp_path)
    with path.open(newline='') as stream:
        rows = list(csv.reader(stream, delimiter='\t'))
    row = rows[3]
    if change == 'wrong_target': row[0] = 'description'
    elif change == 'header_target': row[0] = 'D4D: ignored header'
    elif change == 'blank_target': row[0] = ''
    elif change == 'uncovered': row[4] = '0'
    elif change == 'wrong_source': row[2] = 'unrelated'
    elif change == 'multiple_sources': row[2] += ',alternate'
    elif change == 'duplicate': rows.append(list(row))
    else:
        rows.append([row[0], '', 'alternate', '', '1', '1'])
    with path.open('w', newline='') as stream:
        csv.writer(stream, delimiter='\t', lineterminator='\n').writerows(rows)
    with pytest.raises(ValueError, match='description_list_narrative_v1 requires one covered row'):
        implementation['loader'].MappingLoader(str(path))


def test_mutated_route_refuses_before_builder_state_reset(implementation, tmp_path):
    record, parser, builder = build(implementation,
        source_file(tmp_path / 'source.json', dict.fromkeys(ROUTES, TEXT)), table(tmp_path))
    before = deepcopy(record)
    builder.mapping.mappings.append({'D4D Property': 'preprocessing_strategies', COVERED: '1',
                                     'FAIRSCAPE RO-Crate Property': 'alternate'})
    with pytest.raises(ValueError, match='conflicting narrative routes'):
        builder.build_dataset(parser)
    assert builder.d4d_data == before


@pytest.mark.parametrize('primary_value,expected,origin', [
    (['repeat', 'repeat', TEXT], [{'description': 'repeat'}, {'description': 'repeat'}, {'description': TEXT}], 'Primary'),
    ([], [], 'Primary'), (False, False, 'Primary'),
    (None, [{'description': 'First secondary'}], 'First'),
    (ABSENT, [{'description': 'First secondary'}], 'First'),
])
def test_existing_primary_wins_merge_preserves_units_and_provenance(
        implementation, tmp_path, primary_value, expected, origin):
    mapping = table(tmp_path)
    # A non-first primary also proves selection is not accidentally tied to array order.
    paths = [source_file(tmp_path / f'{i}.json', dict.fromkeys(ROUTES, value))
             for i, value in enumerate(['First secondary', primary_value, 'Later secondary'])]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    before = deepcopy([p.require_root_dataset() for p in parsers])
    merger = implementation['merger'].ROCrateMerger(implementation['loader'].MappingLoader(str(mapping)))
    record = merger.merge_rocrates(parsers, primary_index=1, source_names=['First', 'Primary', 'Later'])
    for field in ROUTES:
        assert_same(record[field], expected)
        assert merger.get_provenance()[field] == [origin]
    if isinstance(expected, list) and expected:
        record['preprocessing_strategies'][0]['description'] = 'mutated merged output'
    assert [p.require_root_dataset() for p in parsers] == before


def test_default_routes_keep_metadata_and_other_validation_errors(implementation, tmp_path):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(ROUTES, TEXT))
    record, _, _ = build(implementation, source, DEFAULT)
    assert all(record[field] == [{'description': TEXT}] for field in ROUTES)
    publication.prepare_dataset(record)
    loader = implementation['loader'].MappingLoader(str(DEFAULT))
    for field, source_name in ROUTES.items():
        row = loader.get_mapping_info(field)
        assert row['Func'] == MARKER and row['FAIRSCAPE RO-Crate Property'] == source_name
        assert row['Inverse_Mapping'] == field + '[].description'
        assert row['Mapping_Type'] == 'closeMatch' and row['Information_Loss'] == 'minimal'
    bad = source_file(tmp_path / 'bad.json', dict.fromkeys(ROUTES, TEXT),
                      extra={'author': {'@id': 'https://orcid.org/explicit-reference'}})
    bad_record, _, _ = build(implementation, bad, DEFAULT)
    assert all(bad_record[field] == [{'description': TEXT}] for field in ROUTES)
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(bad_record)


@pytest.mark.parametrize('entrypoint', ['packaged', 'd4d'])
@pytest.mark.parametrize('value', [TEXT, ['whole', False]])
def test_real_cli_keeps_required_publication_gate(tmp_path, monkeypatch, entrypoint, value):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(ROUTES, value))
    mapping = table(tmp_path)
    output = tmp_path / 'record.yaml'; output.write_bytes(SENTINEL)
    before = {p: p.read_bytes() for p in (source, mapping)}
    monkeypatch.chdir(REPO)
    with legacy_imports():
        if entrypoint == 'packaged':
            from fairscape_integration.cli import cli
            argv = ['transform', str(source), '-m', str(mapping), '-o', str(output)]
        else:
            from data_sheets_schema.cli import cli
            argv = ['rocrate', 'transform', str(source), '--mapping', str(mapping), '-o', str(output)]
        result = CliRunner().invoke(cli, argv)
    if isinstance(value, str):
        assert result.exit_code == 0, result.output
        assert all(yaml.safe_load(output.read_bytes())[field] == [{'description': TEXT}] for field in ROUTES)
    else:
        assert result.exit_code == 1 and 'Dataset publication refused' in result.output
        assert output.read_bytes() == SENTINEL
    assert {p: p.read_bytes() for p in before} == before
