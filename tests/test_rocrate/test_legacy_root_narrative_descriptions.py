"""#4924: preserve five root assertions without inferring structured details."""
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
    ROOT_NARRATIVE_MARKER, ROOT_NARRATIVE_ROUTES,
)
from .test_legacy_root_identity import implementation, crate
from .test_legacy_root_gates import legacy_imports


REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
EXPECTED_ROUTES = {
    'missing_data_documentation': 'rai:dataCollectionMissingData',
    'ethical_reviews': 'ethicalReview',
    'intended_uses': 'rai:dataUseCases',
    'prohibited_uses': 'prohibitedUses',
    'raw_sources': 'rai:dataCollectionRawData',
}
TEXT = '  Whole assertion; retain "quotes", Café and whitespace.\nDo not split.\n'
SENTINEL = b'previous reviewed output\n'
ABSENT = object()


def table(tmp_path, *, marker=ROOT_NARRATIVE_MARKER, field_type='', routes=None):
    path = tmp_path / 'selected.tsv'
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['D4D Property', 'Type', 'FAIRSCAPE RO-Crate Property', 'Func',
                         COVERED, 'Direct mapping? Yes =1; No = 0'])
        writer.writerow(['id', 'URI', 'identifier,@id', 'root_identifier_v1', '1', '0'])
        writer.writerow(['title', 'str', 'name', '', '1', '1'])
        for field, source in (EXPECTED_ROUTES if routes is None else routes).items():
            writer.writerow([field, field_type, source, marker, '1', '1'])
    return path


def source_file(path, values, *, reverse=False, extra=None):
    root = {'@id': './', 'identifier': 'doi:10.1234/Narratives', 'name': 'Selected root'}
    for field, value in values.items():
        if value is not ABSENT:
            root[EXPECTED_ROUTES[field]] = deepcopy(value)
    root.update(extra or {})
    crate(path, root, reverse=reverse)
    content = json.loads(path.read_text())
    member = next(row for row in content['@graph'] if row.get('@id') == 'member')
    member.update({source: 'Member-only assertion must not leak.' for source in EXPECTED_ROUTES.values()})
    path.write_text(json.dumps(content), encoding='utf-8')
    return path


def build(implementation, source, mapping):
    parser = implementation['parser'].ROCrateParser(str(source))
    builder = implementation['builder'].D4DBuilder(implementation['loader'].MappingLoader(str(mapping)))
    return builder.build_dataset(parser), parser, builder


def assert_same(left, right):
    # JSON spellings distinguish false/zero and preserve nested list structure.
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
def test_five_whole_root_assertions_and_actual_publication(
        implementation, tmp_path, reverse, value, expected):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(EXPECTED_ROUTES, value), reverse=reverse)
    mapping = table(tmp_path, field_type='bool')  # Explicit route precedes generic coercion.
    before = {p: p.read_bytes() for p in (source, mapping)}
    record, parser, builder = build(implementation, source, mapping)
    assert record == {'id': 'doi:10.1234/Narratives', 'title': 'Selected root',
                      **{field: expected for field in EXPECTED_ROUTES}}
    for field in EXPECTED_ROUTES:
        assert builder.apply_field_transformation(field, value) == expected
        assert all(set(item) == {'description'} for item in record[field])
    output = tmp_path / 'record.yaml'
    publication.publish([(output, publication.prepare_dataset(record))], protected=[source, mapping])
    assert_same(yaml.safe_load(output.read_bytes()), record)
    record['ethical_reviews'].append({'description': 'changed result'})
    assert builder.build_dataset(parser)['ethical_reviews'] == expected
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('value', [ABSENT, None])
def test_root_absence_or_null_does_not_borrow_a_member(implementation, tmp_path, value):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(EXPECTED_ROUTES, value), reverse=True)
    record, _, _ = build(implementation, source, table(tmp_path))
    assert record == {'id': 'doi:10.1234/Narratives', 'title': 'Selected root'}
    publication.prepare_dataset(record)


@pytest.mark.parametrize('field', list(EXPECTED_ROUTES))
@pytest.mark.parametrize('value,expected', [
    (False, False), (0, 0),
    (['literal', False], [{'description': 'literal'}, False]),
    (['literal', 0], [{'description': 'literal'}, 0]),
    (['literal', None], [{'description': 'literal'}, None]),
    (['literal', ['nested', 'nested']], [{'description': 'literal'}, ['nested', 'nested']]),
    (['literal', {'@id': 'member'}], [{'description': 'literal'}, {'@id': 'member'}]),
    ({'description': 'scalar object is not a list'}, {'description': 'scalar object is not a list'}),
])
def test_each_malformed_field_stays_visible_and_refuses_publication(
        implementation, tmp_path, field, value, expected):
    source = source_file(tmp_path / 'source.json', {field: value}, reverse=True)
    record, parser, _ = build(implementation, source, table(tmp_path))
    assert_same(record[field], expected)
    assert set(record) == {'id', 'title', field}
    assert_same(parser.require_root_dataset()[EXPECTED_ROUTES[field]], value)
    output = tmp_path / 'record.yaml'; output.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError, match=field):
        publication.publish([(output, publication.prepare_dataset(record))], protected=[source])
    assert output.read_bytes() == SENTINEL
    if isinstance(value, list):
        record[field].append('changed output')
        assert_same(parser.require_root_dataset()[EXPECTED_ROUTES[field]], value)


def test_explicit_objects_detach_without_synthesized_review_or_access_fields(implementation, tmp_path):
    value = [{'description': TEXT}, 'additional unparsed assertion']
    source = source_file(tmp_path / 'source.json', dict.fromkeys(EXPECTED_ROUTES, value))
    record, parser, _ = build(implementation, source, table(tmp_path))
    for field in EXPECTED_ROUTES:
        assert record[field] == [{'description': TEXT}, {'description': 'additional unparsed assertion'}]
        assert all(set(item) == {'description'} for item in record[field])
    publication.prepare_dataset(record)
    for field in EXPECTED_ROUTES:
        record[field][0]['description'] = 'changed nested output'
        assert_same(parser.require_root_dataset()[EXPECTED_ROUTES[field]], value)


@pytest.mark.parametrize('marker', ['', 'custom_function_not_executed'])
def test_unmarked_selected_routes_keep_generic_behavior(implementation, tmp_path, marker):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(EXPECTED_ROUTES, TEXT))
    record, _, _ = build(implementation, source, table(tmp_path, marker=marker))
    assert all(record[field] == TEXT for field in EXPECTED_ROUTES)
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(record)


@pytest.mark.parametrize('change', ['wrong_target', 'header_target', 'blank_target', 'uncovered',
                                   'wrong_source', 'multiple_sources', 'duplicate',
                                   'uncovered_duplicate', 'competing_unmarked'])
def test_bad_marker_refuses_before_loader_filtering(implementation, tmp_path, change):
    path = table(tmp_path)
    with path.open(newline='') as stream:
        rows = list(csv.reader(stream, delimiter='\t'))
    row = rows[3]
    if change == 'wrong_target': row[0] = 'raw_data_sources'
    elif change == 'header_target': row[0] = 'D4D: ignored header'
    elif change == 'blank_target': row[0] = ''
    elif change == 'uncovered': row[4] = '0'
    elif change == 'wrong_source': row[2] = 'dataCollectionMissingData'
    elif change == 'multiple_sources': row[2] += ',alternate'
    elif change == 'duplicate': rows.append(list(row))
    elif change == 'uncovered_duplicate':
        other = list(row); other[4] = '0'; rows.append(other)
    else: rows.append([row[0], '', 'alternate', '', '1', '1'])
    with path.open('w', newline='') as stream:
        csv.writer(stream, delimiter='\t', lineterminator='\n').writerows(rows)
    with pytest.raises(ValueError, match='root_narrative_descriptions_v1 requires one covered row'):
        implementation['loader'].MappingLoader(str(path))


@pytest.mark.parametrize('field', list(EXPECTED_ROUTES))
def test_each_route_is_closed_and_old_marker_domains_stay_unchanged(implementation, tmp_path, field):
    assert ROOT_NARRATIVE_ROUTES == EXPECTED_ROUTES
    assert MARKER == 'description_list_narrative_v1'
    assert ROUTES == {'preprocessing_strategies': 'rai:dataPreprocessingProtocol',
        'cleaning_strategies': 'rai:dataManipulationProtocol',
        'labeling_strategies': 'rai:dataAnnotationProtocol',
        'annotation_analyses': 'rai:dataAnnotationAnalysis'}
    assert DISTRIBUTION_MARKER == 'distribution_formats_description_v1'
    assert DISTRIBUTION_ROUTES == {'distribution_formats': 'evi:formats'}
    for marker in (MARKER, DISTRIBUTION_MARKER):
        with pytest.raises(ValueError, match=marker + ' requires one covered row'):
            implementation['loader'].MappingLoader(str(table(tmp_path,
                marker=marker, routes={field: EXPECTED_ROUTES[field]})))
    for old_field, old_source in {**ROUTES, **DISTRIBUTION_ROUTES}.items():
        with pytest.raises(ValueError, match='root_narrative_descriptions_v1 requires one covered row'):
            implementation['loader'].MappingLoader(str(table(tmp_path, routes={old_field: old_source})))
    with pytest.raises(ValueError, match='root_narrative_descriptions_v1 requires one covered row'):
        implementation['loader'].MappingLoader(str(table(tmp_path, routes={field: 'unrelated'})))


def test_mutated_route_refuses_before_builder_state_reset(implementation, tmp_path):
    record, parser, builder = build(implementation,
        source_file(tmp_path / 'source.json', dict.fromkeys(EXPECTED_ROUTES, TEXT)), table(tmp_path))
    before = deepcopy(record)
    builder.mapping.mappings.append({'D4D Property': 'raw_sources', COVERED: '1',
                                     'FAIRSCAPE RO-Crate Property': 'alternate'})
    with pytest.raises(ValueError, match='conflicting root narrative routes'):
        builder.build_dataset(parser)
    assert builder.d4d_data == before


@pytest.mark.parametrize('primary_value,first_value,later_value,expected,origin', [
    (['same', 'same', TEXT], 'First secondary', 'Later secondary',
        [{'description': 'same'}, {'description': 'same'}, {'description': TEXT}], 'Primary'),
    ([], 'First secondary', 'Later secondary', [], 'Primary'),
    (False, 'First secondary', 'Later secondary', False, 'Primary'),
    (0, 'First secondary', 'Later secondary', 0, 'Primary'),
    ('', 'First secondary', 'Later secondary', [{'description': ''}], 'Primary'),
    (None, 'First secondary', 'Later secondary', [{'description': 'First secondary'}], 'First'),
    (ABSENT, 'First secondary', 'Later secondary', [{'description': 'First secondary'}], 'First'),
    (None, [], 'Later secondary', [], 'First'),
    (ABSENT, False, 'Later secondary', False, 'First'),
    (None, 0, 'Later secondary', 0, 'First'),
    (ABSENT, '', 'Later secondary', [{'description': ''}], 'First'),
    (None, None, 'Later secondary', [{'description': 'Later secondary'}], 'Later'),
    (ABSENT, ABSENT, 'Later secondary', [{'description': 'Later secondary'}], 'Later'),
    (None, ABSENT, None, ABSENT, None),
    (ABSENT, None, ABSENT, ABSENT, None),
])
def test_default_and_explicit_primary_wins_preserve_units_and_ordered_fallback(
        implementation, tmp_path, primary_value, first_value, later_value, expected, origin):
    mapping = table(tmp_path)
    paths = [source_file(tmp_path / f'{i}.json', dict.fromkeys(EXPECTED_ROUTES, value))
             for i, value in enumerate([first_value, primary_value, later_value])]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    before = deepcopy([p.require_root_dataset() for p in parsers])
    merger = implementation['merger'].ROCrateMerger(implementation['loader'].MappingLoader(str(mapping)))
    for field in EXPECTED_ROUTES:
        assert merger.prioritizer.get_merge_strategy(field).value == 'primary_wins'
    record = merger.merge_rocrates(parsers, primary_index=1, source_names=['First', 'Primary', 'Later'])
    for field in EXPECTED_ROUTES:
        if expected is ABSENT:
            assert field not in record and field not in merger.get_provenance()
        else:
            assert_same(record[field], expected)
            assert merger.get_provenance()[field] == [origin]
    output = tmp_path / 'merged.yaml'; output.write_bytes(SENTINEL)
    if type(expected) in (bool, int):
        with pytest.raises(publication.PublicationError):
            publication.publish([(output, publication.prepare_dataset(record))], protected=paths)
        assert output.read_bytes() == SENTINEL
    else:
        publication.publish([(output, publication.prepare_dataset(record))], protected=paths)
        assert_same(yaml.safe_load(output.read_bytes()), record)
    if isinstance(expected, list) and expected:
        record['missing_data_documentation'][0]['description'] = 'changed output'
    assert_same([p.require_root_dataset() for p in parsers], before)


def test_raw_presence_and_ranking_do_not_count_constructor_output(implementation, tmp_path):
    paths = [source_file(tmp_path / f'{i}.json', dict.fromkeys(EXPECTED_ROUTES, value))
             for i, value in enumerate([TEXT, None, [], False])]
    parsers = [implementation['parser'].ROCrateParser(str(p)) for p in paths]
    before = deepcopy([p.require_root_dataset() for p in parsers])
    old = implementation['loader'].MappingLoader(str(table(tmp_path, marker='')))
    new = implementation['loader'].MappingLoader(str(table(tmp_path)))
    scorer = implementation['scorer'].InformativenessScorer()
    assert scorer.rank_rocrates(parsers, new) == scorer.rank_rocrates(parsers, old)
    mergers = [implementation['merger'].ROCrateMerger(loader) for loader in (old, new)]
    for merger in mergers:
        merger.merge_rocrates(parsers, primary_index=0, source_names=['Primary', 'Null', 'Empty', 'False'])
    assert_same(mergers[0].source_presence, mergers[1].source_presence)
    assert_same([p.require_root_dataset() for p in parsers], before)


def test_default_table_preserves_sibling_routes_and_unassessed_declarations(implementation, tmp_path):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(EXPECTED_ROUTES, TEXT))
    record, _, _ = build(implementation, source, DEFAULT)
    for field in EXPECTED_ROUTES:
        assert record[field] == [{'description': TEXT}]
    # Related slots keep their existing raw values and errors; no silent rerouting.
    for field in ('tasks', 'existing_uses', 'other_tasks', 'discouraged_uses', 'raw_data_sources'):
        assert record[field] == TEXT
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(record)
    loader = implementation['loader'].MappingLoader(str(DEFAULT))
    for field, source_name in EXPECTED_ROUTES.items():
        row = loader.get_mapping_info(field)
        assert row['Func'] == ROOT_NARRATIVE_MARKER and row['FAIRSCAPE RO-Crate Property'] == source_name
        assert row['Mapping_Type'] == 'exactMatch'
        assert row['SKOS_Relation'] == 'http://www.w3.org/2004/02/skos/core#exactMatch'
        assert row['Information_Loss'] == 'none' and row['Inverse_Mapping'] == field
    assert all(loader.get_mapping_info(field)['Func'] == MARKER for field in ROUTES)
    assert loader.get_mapping_info('distribution_formats')['Func'] == DISTRIBUTION_MARKER


@pytest.mark.parametrize('entrypoint', ['packaged', 'd4d'])
@pytest.mark.parametrize('value', [TEXT, ['whole', False]])
def test_real_cli_retains_final_byte_publication_gate(tmp_path, monkeypatch, entrypoint, value):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(EXPECTED_ROUTES, value))
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
        record = yaml.safe_load(output.read_bytes())
        assert all(record[field] == [{'description': TEXT}] for field in EXPECTED_ROUTES)
    else:
        assert result.exit_code == 1 and 'Dataset publication refused' in result.output
        assert output.read_bytes() == SENTINEL
    assert {p: p.read_bytes() for p in before} == before
