"""#4929: type three whole root assertions without changing their meaning."""
from copy import deepcopy
import csv
import json
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_documentary import MARKER
from data_sheets_schema.legacy_description_lists import (
    MARKER as NARRATIVE, DISTRIBUTION_MARKER, ROOT_NARRATIVE_MARKER,
)
from .test_legacy_root_identity import implementation, crate
from .test_legacy_root_gates import legacy_imports


REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
SOURCES = {
    'collection_mechanisms': 'rai:dataCollection,rai:dataCollectionType',
    'raw_data_sources': 'rai:dataCollectionRawData',
    'license_and_use_terms': 'license, conditionsOfAccess',
}
TEXT = '  Whole assertion; retain "quotes", Café and whitespace.\nDo not split.\n'
SENTINEL = b'previous reviewed output\n'
ABSENT = object()


def table(tmp_path, *, marker=MARKER, routes=None, field_type=''):
    path = tmp_path / 'selected.tsv'
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['D4D Property', 'Type', 'FAIRSCAPE RO-Crate Property',
                         'Func', COVERED, 'Direct mapping? Yes =1; No = 0'])
        writer.writerow(['id', 'URI', 'identifier,@id', 'root_identifier_v1', '1', '0'])
        writer.writerow(['title', 'str', 'name', '', '1', '1'])
        for field, source in (SOURCES if routes is None else routes).items():
            writer.writerow([field, field_type, source, marker, '1', '1'])
    return path


def source_file(path, values, *, reverse=False, extra=None):
    root = {'@id': './', 'identifier': 'doi:10.1234/Documentary', 'name': 'Selected root'}
    for field, value in values.items():
        if value is not ABSENT:
            root[SOURCES[field].split(',')[0]] = deepcopy(value)
    root.update(extra or {})
    crate(path, root, reverse=reverse)
    content = json.loads(path.read_text())
    member = next(row for row in content['@graph'] if row.get('@id') == 'member')
    member.update({source.strip(): 'Member-only assertion must not leak.'
                   for sources in SOURCES.values() for source in sources.split(',')})
    path.write_text(json.dumps(content), encoding='utf-8')
    return path


def build(implementation, source, mapping):
    parser = implementation['parser'].ROCrateParser(str(source))
    builder = implementation['builder'].D4DBuilder(implementation['loader'].MappingLoader(str(mapping)))
    return builder.build_dataset(parser), parser, builder


def assert_same(left, right):
    # A typed oracle: equality alone would conflate false and zero.
    assert json.dumps(left, sort_keys=True, ensure_ascii=True) == json.dumps(
        right, sort_keys=True, ensure_ascii=True)


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('value,collection,raw', [
    (TEXT, [{'mechanism_details': TEXT}], [{'source_description': TEXT}]),
    (['same', TEXT, 'same', '', ' \t\n'],
     [{'mechanism_details': 'same'}, {'mechanism_details': TEXT},
      {'mechanism_details': 'same'}, {'mechanism_details': ''}, {'mechanism_details': ' \t\n'}],
     [{'source_description': 'same'}, {'source_description': TEXT},
      {'source_description': 'same'}, {'source_description': ''}, {'source_description': ' \t\n'}]),
    ([], [], []),
])
def test_whole_text_lists_and_scalar_license_publish_without_extra_claims(
        implementation, tmp_path, reverse, value, collection, raw):
    source = source_file(tmp_path / 'source.json', {
        'collection_mechanisms': value, 'raw_data_sources': value, 'license_and_use_terms': TEXT},
        reverse=reverse)
    mapping = table(tmp_path, field_type='bool')  # Marker must precede generic coercion.
    before = {p: p.read_bytes() for p in (source, mapping)}
    record, parser, builder = build(implementation, source, mapping)
    expected = {'id': 'doi:10.1234/Documentary', 'title': 'Selected root',
                'collection_mechanisms': collection, 'raw_data_sources': raw,
                'license_and_use_terms': {'license_terms': TEXT}}
    assert_same(record, expected)
    for field, value in [('collection_mechanisms', value), ('raw_data_sources', value),
                         ('license_and_use_terms', TEXT)]:
        assert_same(builder.apply_field_transformation(field, value), expected[field])
    output = tmp_path / 'record.yaml'
    publication.publish([(output, publication.prepare_dataset(record))], protected=[source, mapping])
    assert_same(yaml.safe_load(output.read_bytes()), expected)
    record['license_and_use_terms']['license_terms'] = 'changed returned object'
    record['collection_mechanisms'].append({'mechanism_details': 'changed returned list'})
    assert_same(builder.build_dataset(parser), expected)
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('value', [ABSENT, None])
def test_absence_and_null_never_borrow_member_values(implementation, tmp_path, value):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(SOURCES, value), reverse=True)
    record, _, _ = build(implementation, source, table(tmp_path))
    assert record == {'id': 'doi:10.1234/Documentary', 'title': 'Selected root'}
    publication.prepare_dataset(record)


@pytest.mark.parametrize('field,primary,alternate', [
    ('collection_mechanisms', 'rai:dataCollection', 'rai:dataCollectionType'),
    ('license_and_use_terms', 'license', 'conditionsOfAccess'),
])
@pytest.mark.parametrize('first,selected', [
    (TEXT, TEXT), ('', ''), ([], []), (False, False), (0, 0),
    ({'@id': 'member'}, {'@id': 'member'}),
    (None, 'Fallback assertion'), (ABSENT, 'Fallback assertion'),
])
def test_first_nonnull_source_property_retains_conflicts_and_falsy_values(
        implementation, tmp_path, field, primary, alternate, first, selected):
    source = source_file(tmp_path / 'source.json', {field: first}, reverse=True,
                         extra={alternate: 'Fallback assertion'})
    record, parser, _ = build(implementation, source, table(tmp_path))
    if isinstance(selected, str):
        expected = ([{'mechanism_details': selected}] if field == 'collection_mechanisms'
                    else {'license_terms': selected})
    else:
        expected = selected
    assert_same(record[field], expected)
    root = parser.require_root_dataset()
    assert root[alternate] == 'Fallback assertion'
    if first is ABSENT:
        assert primary not in root
    else:
        assert_same(root[primary], first)
    if isinstance(selected, str) or (field == 'collection_mechanisms' and selected == []):
        publication.prepare_dataset(record)
    else:
        with pytest.raises(publication.PublicationError, match=field):
            publication.prepare_dataset(record)


@pytest.mark.parametrize('field', list(SOURCES))
@pytest.mark.parametrize('value', [False, 0, {'@id': 'member'},
                                  ['whole', {'@id': 'member'}],
                                  ['whole', None], ['whole', ['nested', 'nested']]])
def test_unsupported_units_are_detached_preserved_and_refused(
        implementation, tmp_path, field, value):
    source = source_file(tmp_path / 'source.json', {field: value})
    record, parser, _ = build(implementation, source, table(tmp_path))
    if isinstance(value, list) and field != 'license_and_use_terms':
        child = 'mechanism_details' if field == 'collection_mechanisms' else 'source_description'
        expected = [{child: 'whole'}, value[1]]
    else:
        expected = value
    assert_same(record[field], expected)
    output = tmp_path / 'record.yaml'; output.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError, match=field):
        publication.publish([(output, publication.prepare_dataset(record))], protected=[source])
    assert output.read_bytes() == SENTINEL
    if isinstance(record[field], list):
        record[field].append('changed result')
    elif isinstance(record[field], dict):
        record[field]['@id'] = 'changed result'
    assert_same(parser.require_root_dataset()[SOURCES[field].split(',')[0]], value)


@pytest.mark.parametrize('value', [[], [TEXT], [TEXT, TEXT], [{'license_terms': TEXT}]])
def test_scalar_licensing_never_selects_joins_or_wraps_source_list(implementation, tmp_path, value):
    source = source_file(tmp_path / 'source.json', {'license_and_use_terms': value},
                         extra={'conditionsOfAccess': 'Do not fall through to this'})
    record, _, _ = build(implementation, source, table(tmp_path))
    assert_same(record['license_and_use_terms'], value)
    with pytest.raises(publication.PublicationError, match='license_and_use_terms'):
        publication.prepare_dataset(record)


def test_existing_explicit_objects_remain_detached_and_valid(implementation, tmp_path):
    values = {'collection_mechanisms': [{'mechanism_details': TEXT}],
              'raw_data_sources': [{'source_description': TEXT}],
              'license_and_use_terms': {'license_terms': TEXT}}
    source = source_file(tmp_path / 'source.json', values)
    record, parser, _ = build(implementation, source, table(tmp_path))
    for field in SOURCES:
        assert_same(record[field], values[field])
    publication.prepare_dataset(record)
    record['raw_data_sources'][0]['source_description'] = 'changed'
    record['license_and_use_terms']['license_terms'] = 'changed'
    for field, value in values.items():
        assert_same(parser.require_root_dataset()[SOURCES[field].split(',')[0]], value)


@pytest.mark.parametrize('marker', ['', 'custom_function_not_executed'])
def test_custom_unmarked_routes_keep_existing_raw_behavior(implementation, tmp_path, marker):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(SOURCES, TEXT))
    record, _, _ = build(implementation, source, table(tmp_path, marker=marker))
    assert all(record[field] == TEXT for field in SOURCES)
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(record)


@pytest.mark.parametrize('change', ['wrong_target', 'blank_target', 'header_target', 'uncovered',
                                   'wrong_source', 'source_order', 'extra_source', 'duplicate',
                                   'uncovered_duplicate', 'competing_unmarked'])
def test_closed_marker_is_validated_before_loader_filtering(implementation, tmp_path, change):
    path = table(tmp_path)
    with path.open(newline='') as stream:
        rows = list(csv.reader(stream, delimiter='\t'))
    row = rows[3]
    if change == 'wrong_target': row[0] = 'acquisition_methods'
    elif change == 'blank_target': row[0] = ''
    elif change == 'header_target': row[0] = 'D4D: header'
    elif change == 'uncovered': row[4] = '0'
    elif change == 'wrong_source': row[2] = 'dataCollection'
    elif change == 'source_order': row[2] = 'rai:dataCollectionType,rai:dataCollection'
    elif change == 'extra_source': row[2] += ',unrelated'
    elif change == 'duplicate': rows.append(list(row))
    elif change == 'uncovered_duplicate':
        other = list(row); other[4] = '0'; rows.append(other)
    else: rows.append([row[0], '', 'alternate', '', '1', '1'])
    with path.open('w', newline='') as stream:
        csv.writer(stream, delimiter='\t', lineterminator='\n').writerows(rows)
    with pytest.raises(ValueError, match=MARKER + ' requires one covered row'):
        implementation['loader'].MappingLoader(str(path))


@pytest.mark.parametrize('field', list(SOURCES))
def test_old_marker_domains_are_not_extended(implementation, tmp_path, field):
    for marker in (NARRATIVE, DISTRIBUTION_MARKER, ROOT_NARRATIVE_MARKER):
        with pytest.raises(ValueError, match=marker + ' requires one covered row'):
            implementation['loader'].MappingLoader(str(table(tmp_path, marker=marker,
                routes={field: SOURCES[field]})))
    for old_field, source in [('preprocessing_strategies', 'rai:dataPreprocessingProtocol'),
                              ('distribution_formats', 'evi:formats'),
                              ('raw_sources', 'rai:dataCollectionRawData')]:
        with pytest.raises(ValueError, match=MARKER + ' requires one covered row'):
            implementation['loader'].MappingLoader(str(table(tmp_path, routes={old_field: source})))


def test_route_mutation_refuses_before_previous_builder_result_is_reset(implementation, tmp_path):
    record, parser, builder = build(implementation,
        source_file(tmp_path / 'source.json', dict.fromkeys(SOURCES, TEXT)), table(tmp_path))
    before = deepcopy(record)
    builder.mapping.mappings.append({'D4D Property': 'raw_data_sources', COVERED: '1',
                                     'FAIRSCAPE RO-Crate Property': 'unrelated'})
    with pytest.raises(ValueError, match='conflicting documentary routes'):
        builder.build_dataset(parser)
    assert_same(builder.d4d_data, before)


@pytest.mark.parametrize('primary,first,later,selected,origin', [
    (TEXT, 'First', 'Later', TEXT, 'Primary'),
    ('', 'First', 'Later', '', 'Primary'),
    ([], 'First', 'Later', [], 'Primary'),
    (False, 'First', 'Later', False, 'Primary'),
    (0, 'First', 'Later', 0, 'Primary'),
    (['same', 'same'], 'First', 'Later', ['same', 'same'], 'Primary'),
    (None, 'First', 'Later', 'First', 'First'),
    (ABSENT, [], 'Later', [], 'First'),
    (None, False, 'Later', False, 'First'),
    (ABSENT, 0, 'Later', 0, 'First'),
    (None, None, 'Later', 'Later', 'Later'),
    (ABSENT, ABSENT, None, ABSENT, None),
])
def test_primary_wins_and_ordered_secondary_fallback_preserve_types_and_provenance(
        implementation, tmp_path, primary, first, later, selected, origin):
    paths = [source_file(tmp_path / f'{i}.json', dict.fromkeys(SOURCES, value))
             for i, value in enumerate([first, primary, later])]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    before = deepcopy([p.require_root_dataset() for p in parsers])
    merger = implementation['merger'].ROCrateMerger(
        implementation['loader'].MappingLoader(str(table(tmp_path))))
    for field in SOURCES:
        assert merger.prioritizer.get_merge_strategy(field).value == 'primary_wins'
    record = merger.merge_rocrates(parsers, primary_index=1, source_names=['First', 'Primary', 'Later'])
    for field, child in [('collection_mechanisms', 'mechanism_details'),
                         ('raw_data_sources', 'source_description'),
                         ('license_and_use_terms', 'license_terms')]:
        if selected is ABSENT:
            assert field not in record and field not in merger.get_provenance()
            continue
        if isinstance(selected, str):
            expected = {child: selected} if field == 'license_and_use_terms' else [{child: selected}]
        elif isinstance(selected, list) and field != 'license_and_use_terms':
            expected = [{child: item} for item in selected]
        else:
            expected = selected
        assert_same(record[field], expected)
        assert merger.get_provenance()[field] == [origin]
    output = tmp_path / 'merged.yaml'; output.write_bytes(SENTINEL)
    if type(selected) in (bool, int, list):
        with pytest.raises(publication.PublicationError):
            publication.publish([(output, publication.prepare_dataset(record))], protected=paths)
        assert output.read_bytes() == SENTINEL
    else:
        publication.publish([(output, publication.prepare_dataset(record))], protected=paths)
        assert_same(yaml.safe_load(output.read_bytes()), record)
    assert_same([p.require_root_dataset() for p in parsers], before)


def test_raw_source_presence_and_ranking_are_unchanged(implementation, tmp_path):
    paths = [source_file(tmp_path / f'{i}.json', dict.fromkeys(SOURCES, value))
             for i, value in enumerate([TEXT, None, [], False])]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    old = implementation['loader'].MappingLoader(str(table(tmp_path, marker='')))
    new = implementation['loader'].MappingLoader(str(table(tmp_path)))
    scorer = implementation['scorer'].InformativenessScorer()
    assert scorer.rank_rocrates(parsers, old) == scorer.rank_rocrates(parsers, new)
    mergers = [implementation['merger'].ROCrateMerger(mapping) for mapping in (old, new)]
    for merger in mergers:
        merger.merge_rocrates(parsers, primary_index=0, source_names=['Primary', 'Null', 'Empty', 'False'])
    assert_same(mergers[0].source_presence, mergers[1].source_presence)


def test_default_table_types_only_selected_routes_and_keeps_semantic_declarations(implementation, tmp_path):
    source = source_file(tmp_path / 'source.json', dict.fromkeys(SOURCES, TEXT))
    record, _, builder = build(implementation, source, DEFAULT)
    assert record['collection_mechanisms'] == [{'mechanism_details': TEXT}]
    assert record['raw_data_sources'] == [{'source_description': TEXT}]
    assert record['license_and_use_terms'] == {'license_terms': TEXT}
    assert record['raw_sources'] == [{'description': TEXT}]
    assert record['acquisition_methods'] == [{'acquisition_details': TEXT}]
    # The reviewed #4932 default declines IP/contribution claims from a
    # license literal, retaining each original assertion outside Dataset.
    evidence = builder.get_route_dispositions()
    for field in ('ip_restrictions', 'extension_mechanism'):
        assert field not in record
        assertions = evidence['sources'][0]['routes'][field]
        assert assertions[0]['raw'] == TEXT
        assert assertions[0]['disposition'] == 'declined'
    publication.prepare_dataset(record)
    for field in SOURCES:
        row = builder.mapping.get_mapping_info(field)
        assert row['Func'] == MARKER and row['FAIRSCAPE RO-Crate Property'] == SOURCES[field]
        relation = 'closeMatch' if field == 'license_and_use_terms' else 'exactMatch'
        assert row['Mapping_Type'] == relation
        assert row['SKOS_Relation'] == 'http://www.w3.org/2004/02/skos/core#' + relation
        assert row['Information_Loss'] == ('moderate' if field == 'license_and_use_terms' else 'none')
        assert row['Inverse_Mapping'] == ('license + conditionsOfAccess'
                                          if field == 'license_and_use_terms' else field)


@pytest.mark.parametrize('entrypoint', ['packaged', 'd4d'])
@pytest.mark.parametrize('license_value', [TEXT, [TEXT, TEXT]])
def test_real_cli_preserves_final_byte_gate_and_existing_output(
        tmp_path, monkeypatch, entrypoint, license_value):
    source = source_file(tmp_path / 'source.json', {'collection_mechanisms': TEXT,
        'raw_data_sources': TEXT, 'license_and_use_terms': license_value})
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
    if isinstance(license_value, str):
        assert result.exit_code == 0, result.output
        record = yaml.safe_load(output.read_bytes())
        assert record['collection_mechanisms'] == [{'mechanism_details': TEXT}]
        assert record['raw_data_sources'] == [{'source_description': TEXT}]
        assert record['license_and_use_terms'] == {'license_terms': TEXT}
    else:
        assert result.exit_code == 1 and 'Dataset publication refused' in result.output
        assert output.read_bytes() == SENTINEL
    assert {p: p.read_bytes() for p in before} == before
