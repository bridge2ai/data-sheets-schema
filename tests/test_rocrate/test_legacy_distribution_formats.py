"""#4921: retain root format literals without inferring a MIME or format type."""
from copy import deepcopy
import csv
import json
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_description_lists import (
    DISTRIBUTION_MARKER, DISTRIBUTION_ROUTES, MARKER, ROUTES,
)
from .test_legacy_root_identity import implementation, crate
from .test_legacy_root_gates import legacy_imports


REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
SOURCE = 'evi:formats'
FIELD = 'distribution_formats'
TEXT = '  CSV; image/jpeg, unknown.\nCafé — one whole assertion.\n'
SENTINEL = b'previous reviewed output\n'
ABSENT = object()


def table(tmp_path, *, marker=DISTRIBUTION_MARKER, source=SOURCE, field_type=''):
    path = tmp_path / 'selected.tsv'
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['D4D Property', 'Type', 'FAIRSCAPE RO-Crate Property', 'Func',
                         COVERED, 'Direct mapping? Yes =1; No = 0'])
        writer.writerow(['id', 'URI', 'identifier,@id', 'root_identifier_v1', '1', '0'])
        writer.writerow(['title', 'str', 'name', '', '1', '1'])
        writer.writerow([FIELD, field_type, source, marker, '1', '1'])
    return path


def source_file(path, value, *, reverse=False, extra=None):
    root = {'@id': './', 'identifier': 'doi:10.1234/Distribution', 'name': 'Selected root'}
    if value is not ABSENT:
        root[SOURCE] = deepcopy(value)
    root.update(extra or {})
    crate(path, root, reverse=reverse)
    content = json.loads(path.read_text())
    member = next(row for row in content['@graph'] if row.get('@id') == 'member')
    member[SOURCE] = ['Member format must not become root evidence.']
    path.write_text(json.dumps(content), encoding='utf-8')
    return path


def build(implementation, source, mapping):
    parser = implementation['parser'].ROCrateParser(str(source))
    builder = implementation['builder'].D4DBuilder(implementation['loader'].MappingLoader(str(mapping)))
    return builder.build_dataset(parser), parser, builder


def assert_same(left, right):
    # Preserve false versus zero, nested structure and list order.
    assert json.dumps(left, sort_keys=True, ensure_ascii=False) == json.dumps(
        right, sort_keys=True, ensure_ascii=False)


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('value,expected', [
    (TEXT, [{'description': TEXT}]),
    ([TEXT, 'repeat', 'repeat', '', ' \t\n'], [{'description': TEXT},
        {'description': 'repeat'}, {'description': 'repeat'}, {'description': ''},
        {'description': ' \t\n'}]),
    ([], []),
])
def test_whole_root_units_and_real_publication(implementation, tmp_path, reverse, value, expected):
    source = source_file(tmp_path / 'source.json', value, reverse=reverse)
    mapping = table(tmp_path, field_type='bool')  # Constructor precedes generic coercion.
    before = {p: p.read_bytes() for p in (source, mapping)}
    record, parser, builder = build(implementation, source, mapping)
    assert record == {'id': 'doi:10.1234/Distribution', 'title': 'Selected root', FIELD: expected}
    assert builder.apply_field_transformation(FIELD, value) == expected
    assert all(set(row) == {'description'} for row in record[FIELD])
    output = tmp_path / 'record.yaml'
    publication.publish([(output, publication.prepare_dataset(record))], protected=[source, mapping])
    assert_same(yaml.safe_load(output.read_bytes()), record)
    record[FIELD].append({'description': 'changed output'})
    assert builder.build_dataset(parser)[FIELD] == expected
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('value', [ABSENT, None])
def test_absent_or_null_root_never_borrows_member(implementation, tmp_path, value):
    source = source_file(tmp_path / 'source.json', value, reverse=True)
    record, _, _ = build(implementation, source, table(tmp_path))
    assert record == {'id': 'doi:10.1234/Distribution', 'title': 'Selected root'}
    publication.prepare_dataset(record)


@pytest.mark.parametrize('value,expected', [
    (False, False), (0, 0),
    (['literal', False], [{'description': 'literal'}, False]),
    (['literal', 0], [{'description': 'literal'}, 0]),
    (['literal', None], [{'description': 'literal'}, None]),
    (['literal', ['nested', 'nested']], [{'description': 'literal'}, ['nested', 'nested']]),
    (['literal', {'@id': 'urn:reference'}], [{'description': 'literal'}, {'@id': 'urn:reference'}]),
    ({'description': 'scalar object is not a list'}, {'description': 'scalar object is not a list'}),
])
def test_malformed_units_stay_visible_and_publication_preserves_output(
        implementation, tmp_path, value, expected):
    source = source_file(tmp_path / 'source.json', value)
    record, parser, _ = build(implementation, source, table(tmp_path))
    assert_same(record[FIELD], expected)
    assert_same(parser.require_root_dataset()[SOURCE], value)
    output = tmp_path / 'record.yaml'; output.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError):
        publication.publish([(output, publication.prepare_dataset(record))], protected=[source])
    assert output.read_bytes() == SENTINEL
    if isinstance(value, list):
        record[FIELD].append('changed output')
        assert_same(parser.require_root_dataset()[SOURCE], value)


def test_explicit_objects_detach_without_inventing_format_fields(implementation, tmp_path):
    value = [{'description': TEXT, 'format': 'explicit source format'}, 'unclassified text']
    source = source_file(tmp_path / 'source.json', value)
    record, parser, _ = build(implementation, source, table(tmp_path))
    assert record[FIELD] == [value[0], {'description': 'unclassified text'}]
    publication.prepare_dataset(record)
    record[FIELD][0]['format'] = 'changed result'
    record[FIELD][0]['description'] = 'changed result'
    assert_same(parser.require_root_dataset()[SOURCE], value)


@pytest.mark.parametrize('marker', ['', 'custom_function_not_executed'])
def test_unmarked_custom_routes_stay_generic(implementation, tmp_path, marker):
    value = [TEXT, TEXT]
    source = source_file(tmp_path / 'source.json', 'not the custom assertion',
                         extra={'customFormats': value})
    record, _, _ = build(implementation, source,
                         table(tmp_path, marker=marker, source='customFormats'))
    assert record[FIELD] == value
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(record)


@pytest.mark.parametrize('change', ['wrong_target', 'header_target', 'blank_target', 'uncovered',
                                   'wrong_source', 'multiple_sources', 'duplicate',
                                   'uncovered_duplicate', 'competing_unmarked'])
def test_invalid_marker_refuses_before_loader_filtering(implementation, tmp_path, change):
    path = table(tmp_path)
    with path.open(newline='') as stream:
        rows = list(csv.reader(stream, delimiter='\t'))
    row = rows[3]
    if change == 'wrong_target': row[0] = 'media_type'
    elif change == 'header_target': row[0] = 'D4D: ignored header'
    elif change == 'blank_target': row[0] = ''
    elif change == 'uncovered': row[4] = '0'
    elif change == 'wrong_source': row[2] = 'rai:dataPreprocessingProtocol'
    elif change == 'multiple_sources': row[2] += ',alternate'
    elif change == 'duplicate': rows.append(list(row))
    elif change == 'uncovered_duplicate':
        other = list(row); other[4] = '0'; rows.append(other)
    else: rows.append([FIELD, '', 'alternate', '', '1', '1'])
    with path.open('w', newline='') as stream:
        csv.writer(stream, delimiter='\t', lineterminator='\n').writerows(rows)
    with pytest.raises(ValueError, match='distribution_formats_description_v1 requires one covered row'):
        implementation['loader'].MappingLoader(str(path))


def test_marker_domains_remain_separate(implementation, tmp_path):
    # A new recognized marker does not widen the old four-route contract.
    old_routes = {
        'preprocessing_strategies': 'rai:dataPreprocessingProtocol',
        'cleaning_strategies': 'rai:dataManipulationProtocol',
        'labeling_strategies': 'rai:dataAnnotationProtocol',
        'annotation_analyses': 'rai:dataAnnotationAnalysis',
    }
    assert MARKER == 'description_list_narrative_v1' and ROUTES == old_routes
    assert DISTRIBUTION_ROUTES == {FIELD: SOURCE}
    with pytest.raises(ValueError, match='description_list_narrative_v1 requires one covered row'):
        implementation['loader'].MappingLoader(str(table(tmp_path, marker=MARKER)))
    for old_field, old_source in old_routes.items():
        path = table(tmp_path, source=old_source)
        with path.open(newline='') as stream:
            rows = list(csv.reader(stream, delimiter='\t'))
        rows[3][0] = old_field
        with path.open('w', newline='') as stream:
            csv.writer(stream, delimiter='\t', lineterminator='\n').writerows(rows)
        with pytest.raises(ValueError, match='distribution_formats_description_v1 requires one covered row'):
            implementation['loader'].MappingLoader(str(path))


def test_changed_route_refuses_before_builder_state_reset(implementation, tmp_path):
    record, parser, builder = build(implementation,
        source_file(tmp_path / 'source.json', TEXT), table(tmp_path))
    before = deepcopy(record)
    builder.mapping.mappings.append({'D4D Property': FIELD, COVERED: '1',
                                     'FAIRSCAPE RO-Crate Property': 'alternate'})
    with pytest.raises(ValueError, match='conflicting distribution routes'):
        builder.build_dataset(parser)
    assert builder.d4d_data == before


@pytest.mark.parametrize('first_value,primary_value,later_value,expected,origin', [
    (['same', 'same', TEXT], 'Primary assertion', 'Later secondary',
        [{'description': 'same'}, {'description': 'same'}, {'description': TEXT}], 'First'),
    ([], 'Primary assertion', 'Later secondary', [], 'First'),
    (False, 'Primary assertion', 'Later secondary', False, 'First'),
    (0, 'Primary assertion', 'Later secondary', 0, 'First'),
    ('', 'Primary assertion', 'Later secondary', [{'description': ''}], 'First'),
    (None, 'Primary assertion', 'Later secondary', [{'description': 'Later secondary'}], 'Later'),
    (ABSENT, 'Primary assertion', 'Later secondary', [{'description': 'Later secondary'}], 'Later'),
    (None, 'Primary assertion', ABSENT, [{'description': 'Primary assertion'}], 'Primary'),
    (ABSENT, 'Primary assertion', None, [{'description': 'Primary assertion'}], 'Primary'),
    (ABSENT, [], None, [], 'Primary'),
    (None, False, ABSENT, False, 'Primary'),
    (ABSENT, 0, None, 0, 'Primary'),
    (None, None, ABSENT, ABSENT, None),
    (ABSENT, ABSENT, None, ABSENT, None),
])
def test_secondary_wins_retains_explicit_units_and_falls_back_only_for_missing_values(
        implementation, tmp_path, first_value, primary_value, later_value, expected, origin):
    mapping = table(tmp_path)
    # The non-first primary leaves two ordered secondary sources. This field's
    # existing policy is SECONDARY_WINS, not the narrative routes' default.
    paths = [source_file(tmp_path / f'{i}.json', value)
             for i, value in enumerate([first_value, primary_value, later_value])]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    before = deepcopy([p.require_root_dataset() for p in parsers])
    merger = implementation['merger'].ROCrateMerger(implementation['loader'].MappingLoader(str(mapping)))
    assert merger.prioritizer.get_merge_strategy(FIELD).value == 'secondary_wins'
    record = merger.merge_rocrates(parsers, primary_index=1, source_names=['First', 'Primary', 'Later'])
    if expected is ABSENT:
        assert FIELD not in record and FIELD not in merger.get_provenance()
    else:
        assert_same(record[FIELD], expected)
        assert merger.get_provenance()[FIELD] == [origin]
    output = tmp_path / 'merged.yaml'; output.write_bytes(SENTINEL)
    if type(expected) in (bool, int):
        with pytest.raises(publication.PublicationError):
            publication.publish([(output, publication.prepare_dataset(record))], protected=paths)
        assert output.read_bytes() == SENTINEL
    else:
        publication.publish([(output, publication.prepare_dataset(record))], protected=paths)
        assert_same(yaml.safe_load(output.read_bytes()), record)
    if isinstance(expected, list) and expected:
        record[FIELD][0]['description'] = 'changed merged output'
    assert_same([p.require_root_dataset() for p in parsers], before)


def test_default_row_keeps_old_routes_shared_source_and_fidelity_declarations(implementation, tmp_path):
    source = source_file(tmp_path / 'source.json', [TEXT, TEXT],
                         extra={name: [TEXT, TEXT] for name in ROUTES.values()})
    record, _, _ = build(implementation, source, DEFAULT)
    assert record[FIELD] == [{'description': TEXT}, {'description': TEXT}]
    for field in ROUTES:
        assert record[field] == [{'description': TEXT}, {'description': TEXT}]
    # The separate legacy encoding route shares evi:formats; this repair does
    # not remove or repair its value, or weaken the full Dataset gate.
    assert record['encoding'] == [TEXT, TEXT]
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(record)
    loader = implementation['loader'].MappingLoader(str(DEFAULT))
    row = loader.get_mapping_info(FIELD)
    assert row['Func'] == DISTRIBUTION_MARKER and row['FAIRSCAPE RO-Crate Property'] == SOURCE
    assert row['Mapping_Type'] == 'exactMatch'
    assert row['SKOS_Relation'] == 'http://www.w3.org/2004/02/skos/core#exactMatch'
    assert row['Information_Loss'] == 'none' and row['Inverse_Mapping'] == FIELD
    for field in ROUTES:
        old_row = loader.get_mapping_info(field)
        assert old_row['Func'] == MARKER and old_row['Inverse_Mapping'] == field + '[].description'


@pytest.mark.parametrize('entrypoint', ['packaged', 'd4d'])
@pytest.mark.parametrize('value', [TEXT, ['whole', False]])
def test_real_cli_retains_required_publication_gate(tmp_path, monkeypatch, entrypoint, value):
    source = source_file(tmp_path / 'source.json', value)
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
        assert yaml.safe_load(output.read_bytes())[FIELD] == [{'description': TEXT}]
    else:
        assert result.exit_code == 1 and 'Dataset publication refused' in result.output
        assert output.read_bytes() == SENTINEL
    assert {p: p.read_bytes() for p in before} == before
