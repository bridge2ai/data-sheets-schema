"""#4917: preserve whole sensitivity assertions through the actual legacy paths."""
from copy import deepcopy
import csv
import json
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_sensitive_elements import MARKER, SOURCE
from .test_legacy_root_identity import implementation, crate
from .test_legacy_root_gates import legacy_imports


REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
TEXT = '  Whole asserted sensitivity; do not split or infer.\nCafé — repeated.\n'
SENTINEL = b'previous reviewed output\n'
ABSENT = object()


def table(tmp_path, *, marker=MARKER, source=SOURCE, field_type=''):
    path = tmp_path / 'selected.tsv'
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['D4D Property', 'Type', 'FAIRSCAPE RO-Crate Property', 'Func',
                         COVERED, 'Direct mapping? Yes =1; No = 0'])
        writer.writerow(['id', 'URI', 'identifier,@id', 'root_identifier_v1', '1', '0'])
        writer.writerow(['title', 'str', 'name', '', '1', '1'])
        writer.writerow(['sensitive_elements', field_type, source, marker, '1', '1'])
    return path


def source_file(path, value, *, reverse=False, extra=None):
    root = {'@id': './', 'identifier': 'doi:10.1234/Sensitivity', 'name': 'Selected root'}
    if value is not ABSENT:
        root[SOURCE] = deepcopy(value)
    root.update(extra or {})
    crate(path, root, reverse=reverse)
    content = json.loads(path.read_text())
    member = next(row for row in content['@graph'] if row.get('@id') == 'member')
    member[SOURCE] = ['Member-only assertion must not become root evidence.']
    path.write_text(json.dumps(content), encoding='utf-8')
    return path


def build(implementation, source, mapping):
    parser = implementation['parser'].ROCrateParser(str(source))
    builder = implementation['builder'].D4DBuilder(implementation['loader'].MappingLoader(str(mapping)))
    return builder.build_dataset(parser), parser, builder


def assert_same(left, right):
    # Distinguish false/zero while retaining every original assertion unit.
    assert json.dumps(left, sort_keys=True, ensure_ascii=False) == json.dumps(
        right, sort_keys=True, ensure_ascii=False)


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('value,expected', [
    (TEXT, [{'sensitivity_details': TEXT}]),
    ([TEXT, 'repeat', 'repeat', ''], [{'sensitivity_details': TEXT},
        {'sensitivity_details': 'repeat'}, {'sensitivity_details': 'repeat'}, {'sensitivity_details': ''}]),
    ([], []),
])
def test_whole_strings_root_order_and_real_publication(implementation, tmp_path, reverse, value, expected):
    source = source_file(tmp_path / 'source.json', value, reverse=reverse)
    mapping = table(tmp_path, field_type='bool')  # Explicit constructor precedes generic coercion.
    before = {p: p.read_bytes() for p in (source, mapping)}
    record, parser, builder = build(implementation, source, mapping)
    assert record == {'id': 'doi:10.1234/Sensitivity', 'title': 'Selected root', 'sensitive_elements': expected}
    assert builder.apply_field_transformation('sensitive_elements', value) == expected
    assert all(set(row) == {'sensitivity_details'} for row in record['sensitive_elements'])
    output = tmp_path / 'record.yaml'
    publication.publish([(output, publication.prepare_dataset(record))], protected=[source, mapping])
    assert yaml.safe_load(output.read_bytes()) == record
    record['sensitive_elements'].append({'sensitivity_details': 'new output'})
    assert builder.build_dataset(parser)['sensitive_elements'] == expected
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('value', [ABSENT, None])
def test_absent_or_null_root_never_borrows_member(implementation, tmp_path, value):
    source = source_file(tmp_path / 'source.json', value, reverse=True)
    record, _, _ = build(implementation, source, table(tmp_path))
    assert record == {'id': 'doi:10.1234/Sensitivity', 'title': 'Selected root'}
    publication.prepare_dataset(record)


@pytest.mark.parametrize('value,expected', [
    (False, False), (0, 0),
    (['literal', None], [{'sensitivity_details': 'literal'}, None]),
    (['literal', ['nested']], [{'sensitivity_details': 'literal'}, ['nested']]),
    (['literal', {'@id': 'urn:reference'}], [{'sensitivity_details': 'literal'}, {'@id': 'urn:reference'}]),
    ({'sensitivity_details': 'scalar object is not a list'}, {'sensitivity_details': 'scalar object is not a list'}),
])
def test_unsupported_units_remain_visible_and_gate_preserves_output(implementation, tmp_path, value, expected):
    source = source_file(tmp_path / 'source.json', value)
    record, parser, _ = build(implementation, source, table(tmp_path))
    assert_same(record['sensitive_elements'], expected)
    assert_same(parser.require_root_dataset()[SOURCE], value)
    output = tmp_path / 'record.yaml'; output.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError):
        publication.publish([(output, publication.prepare_dataset(record))], protected=[source])
    assert output.read_bytes() == SENTINEL
    if isinstance(value, list):
        record['sensitive_elements'].append('changed output')
        assert_same(parser.require_root_dataset()[SOURCE], value)


def test_explicit_structured_units_preserve_flags_without_aliases(implementation, tmp_path):
    # Preserve an explicitly supplied false flag; never manufacture a flag for text.
    value = [{'sensitivity_details': TEXT, 'sensitive_elements_present': False}, 'unclassified whole text']
    source = source_file(tmp_path / 'source.json', value)
    record, parser, _ = build(implementation, source, table(tmp_path))
    assert record['sensitive_elements'] == [value[0], {'sensitivity_details': 'unclassified whole text'}]
    publication.prepare_dataset(record)
    record['sensitive_elements'][0]['sensitive_elements_present'] = True
    record['sensitive_elements'][0]['sensitivity_details'] = 'changed output'
    assert_same(parser.require_root_dataset()[SOURCE], value)


@pytest.mark.parametrize('marker', ['', 'custom_function_not_executed'])
def test_unmarked_custom_source_and_transform_stay_generic(implementation, tmp_path, marker):
    value = [TEXT, TEXT]
    source = source_file(tmp_path / 'source.json', 'not the selected custom value',
                         extra={'customSensitive': value})
    record, _, _ = build(implementation, source, table(tmp_path, marker=marker, source='customSensitive'))
    assert record['sensitive_elements'] == value
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(record)


@pytest.mark.parametrize('change', ['wrong_target', 'header_target', 'uncovered', 'wrong_source',
                                   'multiple_sources', 'duplicate', 'competing_unmarked'])
def test_conflicting_marked_route_refuses_before_loader_filtering(implementation, tmp_path, change):
    path = table(tmp_path)
    with path.open(newline='') as stream:
        rows = list(csv.reader(stream, delimiter='\t'))
    row = rows[3]
    if change == 'wrong_target': row[0] = 'confidential_elements'
    elif change == 'header_target': row[0] = 'D4D: ignored header'
    elif change == 'uncovered': row[4] = '0'
    elif change == 'wrong_source': row[2] = 'unrelated'
    elif change == 'multiple_sources': row[2] += ',alternate'
    elif change == 'duplicate': rows.append(list(row))
    else: rows.append([row[0], '', 'alternate', '', '1', '1'])
    with path.open('w', newline='') as stream:
        csv.writer(stream, delimiter='\t', lineterminator='\n').writerows(rows)
    with pytest.raises(ValueError, match='sensitive_elements_details_v1 requires one covered'):
        implementation['loader'].MappingLoader(str(path))


def test_changed_route_refuses_before_builder_state_reset(implementation, tmp_path):
    record, parser, builder = build(implementation, source_file(tmp_path / 'source.json', TEXT), table(tmp_path))
    before = deepcopy(record)
    builder.mapping.mappings.append({'D4D Property': 'sensitive_elements', COVERED: '1',
                                     'FAIRSCAPE RO-Crate Property': 'alternate'})
    with pytest.raises(ValueError, match='conflicting sensitivity routes'):
        builder.build_dataset(parser)
    assert builder.d4d_data == before


@pytest.mark.parametrize('primary_value,expected,origin', [
    (['same', 'same', TEXT], [{'sensitivity_details': 'same'}, {'sensitivity_details': 'same'},
                            {'sensitivity_details': TEXT}], 'Primary'),
    ([], [], 'Primary'), (False, False, 'Primary'),
    (None, [{'sensitivity_details': 'First secondary'}], 'First'),
    (ABSENT, [{'sensitivity_details': 'First secondary'}], 'First'),
])
def test_primary_wins_preserves_duplicates_empty_false_and_first_secondary(
        implementation, tmp_path, primary_value, expected, origin):
    mapping = table(tmp_path)
    paths = [source_file(tmp_path / f'{i}.json', value)
             for i, value in enumerate(['First secondary', primary_value, 'Later secondary'])]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    before = deepcopy([p.require_root_dataset() for p in parsers])
    merger = implementation['merger'].ROCrateMerger(implementation['loader'].MappingLoader(str(mapping)))
    record = merger.merge_rocrates(parsers, primary_index=1, source_names=['First', 'Primary', 'Later'])
    assert_same(record['sensitive_elements'], expected)
    assert merger.get_provenance()['sensitive_elements'] == [origin]
    if isinstance(expected, list) and expected:
        record['sensitive_elements'][0]['sensitivity_details'] = 'changed merged output'
    assert [p.require_root_dataset() for p in parsers] == before


def test_default_route_keeps_four_previous_constructors_and_fidelity_declarations(implementation, tmp_path):
    original_routes = {
        'preprocessing_strategies': 'rai:dataPreprocessingProtocol',
        'cleaning_strategies': 'rai:dataManipulationProtocol',
        'labeling_strategies': 'rai:dataAnnotationProtocol',
        'annotation_analyses': 'rai:dataAnnotationAnalysis',
    }
    source = source_file(tmp_path / 'source.json', TEXT,
                         extra={source: [TEXT, TEXT] for source in original_routes.values()})
    record, _, _ = build(implementation, source, DEFAULT)
    assert record['sensitive_elements'] == [{'sensitivity_details': TEXT}]
    for field in original_routes:
        assert record[field] == [{'description': TEXT}, {'description': TEXT}]
    # The existing separate confidential route shares this predicate; leave its
    # raw value and resulting schema refusal unchanged (#4046 is not this fix).
    assert record['confidential_elements'] == TEXT
    assert 'sensitive_elements_present' not in record
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(record)
    loader = implementation['loader'].MappingLoader(str(DEFAULT))
    row = loader.get_mapping_info('sensitive_elements')
    assert row['Func'] == MARKER and row['FAIRSCAPE RO-Crate Property'] == SOURCE
    assert row['Inverse_Mapping'] == 'sensitive_elements[].sensitivity_details'
    assert row['Mapping_Type'] == 'exactMatch' and row['Information_Loss'] == 'none'
    for field in original_routes:
        row = loader.get_mapping_info(field)
        assert row['Func'] == 'description_list_narrative_v1'
        assert row['Inverse_Mapping'] == field + '[].description'


@pytest.mark.parametrize('entrypoint', ['packaged', 'd4d'])
@pytest.mark.parametrize('value', [TEXT, ['whole', False]])
def test_real_cli_required_publication_gate(tmp_path, monkeypatch, entrypoint, value):
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
        assert yaml.safe_load(output.read_bytes())['sensitive_elements'] == [{'sensitivity_details': TEXT}]
    else:
        assert result.exit_code == 1 and 'Dataset publication refused' in result.output
        assert output.read_bytes() == SENTINEL
    assert {p: p.read_bytes() for p in before} == before
