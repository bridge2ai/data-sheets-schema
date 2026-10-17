"""#4931: preserve acquisition assertions through both real legacy builders."""
from copy import deepcopy
import csv
import json
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_documentary import ACQUISITION_MARKER, MARKER
from data_sheets_schema.legacy_description_lists import (
    MARKER as DESCRIPTION, DISTRIBUTION_MARKER, ROOT_NARRATIVE_MARKER,
)
from .test_legacy_root_identity import implementation, crate
from .test_legacy_root_gates import legacy_imports


REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
SOURCES = 'rai:dataCollection,rai:dataCollectionType'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
TEXT = '  Clinical sensors; retain "quotes", Café and whitespace.\nDo not split.\n'
ABSENT = object()
SENTINEL = b'previous reviewed output\n'


def table(tmp_path, *, marker=ACQUISITION_MARKER, field_type=''):
    path = tmp_path / 'selected.tsv'
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['D4D Property', 'Type', 'FAIRSCAPE RO-Crate Property',
                         'Func', COVERED, 'Direct mapping? Yes =1; No = 0'])
        writer.writerow(['id', 'URI', 'identifier,@id', 'root_identifier_v1', '1', '0'])
        writer.writerow(['title', 'str', 'name', '', '1', '1'])
        writer.writerow(['acquisition_methods', field_type, SOURCES, marker, '1', '1'])
    return path


def source_file(path, primary=ABSENT, alternate=ABSENT, *, reverse=False):
    root = {'@id': './', 'identifier': 'doi:10.1234/Acquisition', 'name': 'Selected root'}
    for key, value in [('rai:dataCollection', primary), ('rai:dataCollectionType', alternate)]:
        if value is not ABSENT:
            root[key] = deepcopy(value)
    crate(path, root, reverse=reverse)
    content = json.loads(path.read_text())
    member = next(row for row in content['@graph'] if row.get('@id') == 'member')
    member.update({'rai:dataCollection': 'Member-only assertion must not leak.',
                   'rai:dataCollectionType': 'Member-only alternate must not leak.'})
    path.write_text(json.dumps(content), encoding='utf-8')
    return path


def build(implementation, source, mapping):
    parser = implementation['parser'].ROCrateParser(str(source))
    builder = implementation['builder'].D4DBuilder(implementation['loader'].MappingLoader(str(mapping)))
    return builder.build_dataset(parser), parser, builder


def assert_same(left, right):
    # Unlike ordinary equality, this distinguishes false, zero and empty values.
    assert json.dumps(left, sort_keys=True, ensure_ascii=True) == json.dumps(
        right, sort_keys=True, ensure_ascii=True)


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('value,expected', [
    (TEXT, [{'acquisition_details': TEXT}]),
    ('', [{'acquisition_details': ''}]),
    (['same', TEXT, 'same', '', ' \t\n'],
     [{'acquisition_details': 'same'}, {'acquisition_details': TEXT},
      {'acquisition_details': 'same'}, {'acquisition_details': ''},
      {'acquisition_details': ' \t\n'}]),
    ([], []),
])
def test_whole_text_units_publish_without_inventing_flags(
        implementation, tmp_path, reverse, value, expected):
    source = source_file(tmp_path / 'source.json', value, reverse=reverse)
    mapping = table(tmp_path, field_type='bool')  # Explicit marker precedes generic coercion.
    before = {path: path.read_bytes() for path in (source, mapping)}
    record, parser, builder = build(implementation, source, mapping)
    wanted = {'id': 'doi:10.1234/Acquisition', 'title': 'Selected root',
              'acquisition_methods': expected}
    assert_same(record, wanted)
    assert_same(builder.apply_field_transformation('acquisition_methods', value), expected)
    assert all(set(item) == {'acquisition_details'} for item in record['acquisition_methods'])
    output = tmp_path / 'record.yaml'
    publication.publish([(output, publication.prepare_dataset(record))], protected=[source, mapping])
    assert_same(yaml.safe_load(output.read_bytes()), wanted)
    record['acquisition_methods'].append({'acquisition_details': 'Changed returned list'})
    assert_same(builder.build_dataset(parser), wanted)
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize('value', [ABSENT, None])
def test_absent_and_null_root_values_do_not_borrow_members(implementation, tmp_path, value):
    source = source_file(tmp_path / 'source.json', value, value, reverse=True)
    record, _, _ = build(implementation, source, table(tmp_path))
    assert record == {'id': 'doi:10.1234/Acquisition', 'title': 'Selected root'}
    publication.prepare_dataset(record)


@pytest.mark.parametrize('first,expected', [
    (TEXT, [{'acquisition_details': TEXT}]),
    ('', [{'acquisition_details': ''}]), ([], []), (False, False), (0, 0),
    ({'unrecognized': 'Keep malformed'}, {'unrecognized': 'Keep malformed'}),
    (None, [{'acquisition_details': 'Fallback assertion'}]),
    (ABSENT, [{'acquisition_details': 'Fallback assertion'}]),
])
def test_first_nonnull_property_preserves_conflicts_and_falsy_types(
        implementation, tmp_path, first, expected):
    source = source_file(tmp_path / 'source.json', first, 'Fallback assertion', reverse=True)
    record, parser, _ = build(implementation, source, table(tmp_path))
    assert_same(record['acquisition_methods'], expected)
    root = parser.require_root_dataset()
    assert root['rai:dataCollectionType'] == 'Fallback assertion'
    if first is ABSENT:
        assert 'rai:dataCollection' not in root
    else:
        assert_same(root['rai:dataCollection'], first)
    if isinstance(expected, list):
        publication.prepare_dataset(record)
    else:
        with pytest.raises(publication.PublicationError, match='acquisition_methods'):
            publication.prepare_dataset(record)


@pytest.mark.parametrize('value,expected', [
    (False, False), (0, 0), ({'unrecognized': 'whole'}, {'unrecognized': 'whole'}),
    (['whole', None], [{'acquisition_details': 'whole'}, None]),
    (['whole', False], [{'acquisition_details': 'whole'}, False]),
    (['whole', ['nested', 'nested']], [{'acquisition_details': 'whole'}, ['nested', 'nested']]),
    (['whole', {'unrecognized': 'whole'}],
     [{'acquisition_details': 'whole'}, {'unrecognized': 'whole'}]),
])
def test_unsupported_units_remain_visible_to_real_gate(
        implementation, tmp_path, value, expected):
    source = source_file(tmp_path / 'source.json', value)
    record, parser, _ = build(implementation, source, table(tmp_path))
    assert_same(record['acquisition_methods'], expected)
    output = tmp_path / 'record.yaml'; output.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError, match='acquisition_methods'):
        publication.publish([(output, publication.prepare_dataset(record))], protected=[source])
    assert output.read_bytes() == SENTINEL
    result = record['acquisition_methods']
    if isinstance(result, list):
        if isinstance(result[-1], dict):
            result[-1]['unrecognized'] = 'Changed returned object'
        elif isinstance(result[-1], list):
            result[-1].append('Changed returned nested list')
        result.append('Changed returned list')
    elif isinstance(result, dict):
        result['unrecognized'] = 'Changed returned object'
    assert_same(parser.require_root_dataset()['rai:dataCollection'], value)


def test_explicit_typed_objects_stay_detached_with_only_source_asserted_flags(
        implementation, tmp_path):
    value = [{'acquisition_details': TEXT, 'was_directly_observed': False}]
    source = source_file(tmp_path / 'source.json', value)
    record, parser, _ = build(implementation, source, table(tmp_path))
    assert_same(record['acquisition_methods'], value)
    publication.prepare_dataset(record)
    record['acquisition_methods'][0]['was_directly_observed'] = True
    assert_same(parser.require_root_dataset()['rai:dataCollection'], value)


@pytest.mark.parametrize('marker', ['', 'custom_function_not_executed'])
def test_unmarked_custom_routes_keep_their_original_behavior(implementation, tmp_path, marker):
    source = source_file(tmp_path / 'source.json', TEXT)
    record, _, _ = build(implementation, source, table(tmp_path, marker=marker))
    assert record['acquisition_methods'] == TEXT
    with pytest.raises(publication.PublicationError, match='acquisition_methods'):
        publication.prepare_dataset(record)


@pytest.mark.parametrize('change', ['wrong_target', 'blank_target', 'header_target', 'uncovered',
                                   'wrong_source', 'source_order', 'extra_source', 'duplicate',
                                   'uncovered_duplicate', 'competing_unmarked'])
def test_closed_marker_refuses_contradictory_routes_before_filtering(
        implementation, tmp_path, change):
    path = table(tmp_path)
    with path.open(newline='') as stream:
        rows = list(csv.reader(stream, delimiter='\t'))
    row = rows[3]
    if change == 'wrong_target': row[0] = 'collection_mechanisms'
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
    with pytest.raises(ValueError, match=ACQUISITION_MARKER + ' requires one covered row'):
        implementation['loader'].MappingLoader(str(path))


def test_existing_marker_domains_remain_closed(implementation, tmp_path):
    for marker in (MARKER, DESCRIPTION, DISTRIBUTION_MARKER, ROOT_NARRATIVE_MARKER):
        with pytest.raises(ValueError, match=marker + ' requires one covered row'):
            implementation['loader'].MappingLoader(str(table(tmp_path, marker=marker)))


def test_mutated_route_refuses_before_resetting_prior_builder_output(implementation, tmp_path):
    record, parser, builder = build(
        implementation, source_file(tmp_path / 'source.json', TEXT), table(tmp_path))
    before = deepcopy(record)
    builder.mapping.mappings.append({'D4D Property': 'acquisition_methods', COVERED: '1',
                                     'FAIRSCAPE RO-Crate Property': 'unrelated'})
    with pytest.raises(ValueError, match='conflicting documentary routes'):
        builder.build_dataset(parser)
    assert_same(builder.d4d_data, before)


@pytest.mark.parametrize('primary,first,later,expected,origin,valid', [
    (TEXT, 'First', 'Later', [{'acquisition_details': TEXT}], 'Primary', True),
    ('', 'First', 'Later', [{'acquisition_details': ''}], 'Primary', True),
    ([], 'First', 'Later', [], 'Primary', True),
    (False, 'First', 'Later', False, 'Primary', False),
    (0, 'First', 'Later', 0, 'Primary', False),
    (['same', 'same'], 'First', 'Later',
     [{'acquisition_details': 'same'}, {'acquisition_details': 'same'}], 'Primary', True),
    (None, 'First', 'Later', [{'acquisition_details': 'First'}], 'First', True),
    (ABSENT, [], 'Later', [], 'First', True),
    (None, False, 'Later', False, 'First', False),
    (ABSENT, 0, 'Later', 0, 'First', False),
    (None, None, 'Later', [{'acquisition_details': 'Later'}], 'Later', True),
    (ABSENT, ABSENT, None, ABSENT, None, True),
])
def test_default_primary_wins_keeps_order_multiplicity_and_falsy_fallbacks(
        implementation, tmp_path, primary, first, later, expected, origin, valid):
    paths = [source_file(tmp_path / f'{i}.json', value, reverse=i % 2 == 0)
             for i, value in enumerate([first, primary, later])]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    before = deepcopy([p.require_root_dataset() for p in parsers])
    merger = implementation['merger'].ROCrateMerger(
        implementation['loader'].MappingLoader(str(table(tmp_path))))
    assert merger.prioritizer.get_merge_strategy('acquisition_methods').value == 'primary_wins'
    record = merger.merge_rocrates(parsers, primary_index=1, source_names=['First', 'Primary', 'Later'])
    if expected is ABSENT:
        assert 'acquisition_methods' not in record
        assert 'acquisition_methods' not in merger.get_provenance()
    else:
        assert_same(record['acquisition_methods'], expected)
        assert merger.get_provenance()['acquisition_methods'] == [origin]
    output = tmp_path / 'merged.yaml'; output.write_bytes(SENTINEL)
    if valid:
        publication.publish([(output, publication.prepare_dataset(record))], protected=paths)
        assert_same(yaml.safe_load(output.read_bytes()), record)
    else:
        with pytest.raises(publication.PublicationError, match='acquisition_methods'):
            publication.publish([(output, publication.prepare_dataset(record))], protected=paths)
        assert output.read_bytes() == SENTINEL
    assert_same([p.require_root_dataset() for p in parsers], before)


def test_default_row_changes_only_acquisition_shape_and_keeps_mapping_declarations(
        implementation, tmp_path):
    source = source_file(tmp_path / 'source.json', TEXT)
    with DEFAULT.open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream, delimiter='\t'); names = reader.fieldnames; rows = list(reader)
    old = deepcopy(rows)
    selected = [row for row in old if row['D4D Property'] == 'acquisition_methods']
    assert len(selected) == 1 and selected[0]['Func'] == ACQUISITION_MARKER
    selected[0]['Func'] = ''
    unmarked = tmp_path / 'unmarked-default.tsv'
    with unmarked.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=names, delimiter='\t', lineterminator='\n')
        writer.writeheader(); writer.writerows(old)
    record, parser, builder = build(implementation, source, DEFAULT)
    previous, _, _ = build(implementation, source, unmarked)
    assert previous.pop('acquisition_methods') == TEXT
    assert_same({k: v for k, v in record.items() if k != 'acquisition_methods'}, previous)
    assert record['acquisition_methods'] == [{'acquisition_details': TEXT}]
    assert record['collection_mechanisms'] == [{'mechanism_details': TEXT}]
    row = builder.mapping.get_mapping_info('acquisition_methods')
    assert row['FAIRSCAPE RO-Crate Property'] == SOURCES
    assert row[COVERED] == row['Direct mapping? Yes =1; No = 0'] == '1'
    assert row['Mapping_Type'] == 'exactMatch'
    assert row['SKOS_Relation'] == 'http://www.w3.org/2004/02/skos/core#exactMatch'
    assert row['Information_Loss'] == 'none' and row['Inverse_Mapping'] == 'acquisition_methods'
    assert parser.require_root_dataset()['rai:dataCollection'] == TEXT


def test_raw_rankings_and_source_presence_are_unchanged(implementation, tmp_path):
    paths = [source_file(tmp_path / f'{i}.json', value)
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


@pytest.mark.parametrize('entrypoint', ['packaged', 'd4d'])
@pytest.mark.parametrize('value', [TEXT, ['whole', None]])
def test_real_cli_keeps_final_byte_gate_and_existing_output(
        tmp_path, monkeypatch, entrypoint, value):
    source = source_file(tmp_path / 'source.json', value)
    mapping = table(tmp_path)
    output = tmp_path / 'record.yaml'; output.write_bytes(SENTINEL)
    before = {path: path.read_bytes() for path in (source, mapping)}
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
        assert yaml.safe_load(output.read_bytes())['acquisition_methods'] == [{'acquisition_details': TEXT}]
    else:
        assert result.exit_code == 1 and 'Dataset publication refused' in result.output
        assert output.read_bytes() == SENTINEL
    assert {path: path.read_bytes() for path in before} == before
