"""Independent Creator construction/reporting controls; real producer paths."""
from copy import deepcopy
import json

import pytest

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_creators import MARKER
from data_sheets_schema.legacy_root_identity import scoring_fields
from .test_legacy_publication import legacy
from .test_legacy_root_identity import implementation
from .test_legacy_creators import ABSENT, TEXT, build, encoded, input_file, table


def mapping_pair(tmp_path, *, only_author=False):
    marked = table(tmp_path)
    if only_author:
        marked.write_text(marked.read_text().replace('title\tstr\tname\t\t1\t1\n', ''))
    old = tmp_path / 'unmarked.tsv'
    old.write_text(marked.read_text().replace(MARKER, ''), encoding='utf-8')
    return old, marked


@pytest.mark.parametrize('contract', ['legacy', 'dataset_v1'])
@pytest.mark.parametrize('provenance', [False, True])
@pytest.mark.parametrize('input_kind', ['path', 'dict'])
def test_same_reference_source_can_change_construction_zero_to_hundred_without_source_gain(
        legacy, tmp_path, contract, provenance, input_kind):
    """The filed #4684 counterexample must survive the actual public API."""
    _, _, api = legacy
    reference = {'@id': 'https://orcid.org/literal-reference'}
    path = input_file(tmp_path / 'source.json', reference)
    supplied = json.loads(path.read_text()) if input_kind == 'dict' else path
    before = deepcopy(supplied) if input_kind == 'dict' else path.read_bytes()
    results = []
    for mapping in mapping_pair(tmp_path, only_author=True):
        transformer = api.SemanticTransformer(api.TransformationConfig(
            mapping_file=mapping, validate_input=False, validate_output=False,
            preserve_provenance=provenance, result_contract=contract))
        assert scoring_fields(transformer.mapping_loader) == ['creators']
        results.append(transformer.rocrate_to_d4d(supplied))
    old, new = results
    assert old.coverage_percentage == 0.0 and new.coverage_percentage == 100.0
    assert old.unmapped_fields == ['creators'] and new.unmapped_fields == []
    assert old.data.get('creators') is None
    assert new.data['creators'] == [reference]
    assert old.source_presence == new.source_presence
    raw = new.source_presence['sources'][0]
    assert raw['raw_value'] == reference and raw['immediate_assertion_units'] == 1
    assert raw['author_present'] is True and raw['nonnull'] is True
    assert raw['source_name'] == ('dict' if input_kind == 'dict' else str(path))
    for result, count in [(old, 0), (new, 1)]:
        assert result.coverage_basis == {
            'kind': 'constructed_field_presence', 'count_rule': 'non_null_mapped_value',
            'numerator': count, 'denominator': 1,
            'is_source_coverage': False, 'is_validation_success': False}
        assert result.validation_passed is None
        assert 'source_presence' not in result.data and 'coverage_basis' not in result.data
    with pytest.raises(publication.PublicationError, match='creators'):
        publication.prepare_dataset(new.data)
    if provenance:
        assert 'coverage_basis' not in old.transformation_metadata
        assert new.transformation_metadata['coverage_basis'] == new.coverage_basis
        new.coverage_basis['numerator'] = 900
        assert new.transformation_metadata['coverage_basis']['numerator'] == 1
    else:
        assert old.transformation_metadata is new.transformation_metadata is None
    new.source_presence['sources'][0]['raw_value']['@id'] = 'caller mutation'
    assert old.source_presence['sources'][0]['raw_value'] == reference
    assert new.data['creators'] == [reference]
    assert (supplied if input_kind == 'dict' else path.read_bytes()) == before


def test_reserved_and_repeated_source_labels_preserve_each_assertion_and_primary(
        implementation, tmp_path):
    values = [['same'], ['same', {'description': 'same'}], ['same']]
    paths = [input_file(tmp_path / f'{i}.json', value) for i, value in enumerate(values)]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    merger = implementation['merger'].ROCrateMerger(
        implementation['loader'].MappingLoader(str(table(tmp_path))))
    merged = merger.merge_rocrates(parsers, primary_index=1,
                                   source_names=['primary', 'repeated', 'repeated'])
    assert merged['creators'] == [{'description': 'same'}] * 4
    assert merger.get_provenance()['creators'] == ['repeated', 'primary', 'repeated']
    assert merger.primary_index == 1 and merger.primary_name == 'repeated'
    ledger = merger.get_creator_assertion_sources()
    assert [(r['source_index'], r['processing_index'], r['selected_primary'], r['output_range'])
            for r in ledger] == [(1, 0, True, [0, 2]), (0, 1, False, [2, 3]), (2, 2, False, [3, 4])]
    assert [r['raw_value'] for r in ledger] == [values[1], values[0], values[2]]
    assert [r['source_name'] for r in merger.get_source_presence()['sources']] == [
        'repeated', 'primary', 'repeated']
    assert merger.get_merge_stats()['fields_merged_as_arrays'] == 1


def test_diagnostics_and_result_mutation_do_not_change_reused_merger_or_inputs(
        implementation, tmp_path):
    value = [{'description': TEXT, 'unknown': {'items': [False, 0, None, ['x']]}}]
    path = input_file(tmp_path / 'source.json', value)
    parser = implementation['parser'].ROCrateParser(str(path))
    merger = implementation['merger'].ROCrateMerger(
        implementation['loader'].MappingLoader(str(table(tmp_path))))
    first = merger.merge_rocrates([parser], source_names=['source'])
    expected = deepcopy(first)
    presence, ledger = merger.get_source_presence(), merger.get_creator_assertion_sources()
    presence['sources'][0]['raw_value'][0]['unknown']['items'].append('presence mutation')
    ledger[0]['raw_value'][0]['unknown']['items'].append('ledger mutation')
    ledger[0]['output_range'][1] = 999
    first['creators'][0]['unknown']['items'].append('result mutation')
    assert encoded(parser.require_root_dataset()['author']) == encoded(value)
    assert merger.get_source_presence()['sources'][0]['raw_value'] == value
    assert merger.get_creator_assertion_sources()[0]['output_range'] == [0, 1]
    second = merger.merge_rocrates([parser], source_names=['source'])
    assert encoded(second) == encoded(expected)
    assert merger.get_creator_assertion_sources()[0]['raw_value'] == value
    with pytest.raises(publication.PublicationError, match='creators'):
        publication.prepare_dataset(second)


@pytest.mark.parametrize('consumer', ['builder', 'merger'])
def test_mutable_marker_revalidation_refuses_before_replacing_previous_state(
        implementation, tmp_path, consumer):
    mapping = implementation['loader'].MappingLoader(str(table(tmp_path)))
    path = input_file(tmp_path / 'source.json', TEXT)
    parser = implementation['parser'].ROCrateParser(str(path))
    if consumer == 'builder':
        owner = implementation['builder'].D4DBuilder(mapping)
        previous = deepcopy(owner.build_dataset(parser))
    else:
        owner = implementation['merger'].ROCrateMerger(mapping)
        previous = deepcopy(owner.merge_rocrates([parser]))
        evidence = (owner.get_source_presence(), owner.get_creator_assertion_sources())
    row = next(row for row in mapping.mappings if row.get('Func') == MARKER)
    row['FAIRSCAPE RO-Crate Property'] = 'owner,author'
    with pytest.raises(ValueError, match=MARKER):
        (owner.build_dataset(parser) if consumer == 'builder' else owner.merge_rocrates([parser]))
    assert encoded(owner.d4d_data if consumer == 'builder' else owner.get_merged_dataset()) == encoded(previous)
    if consumer == 'merger':
        assert (owner.get_source_presence(), owner.get_creator_assertion_sources()) == evidence


def test_marker_removal_on_reuse_clears_only_constructed_ranges(implementation, tmp_path):
    mapping = implementation['loader'].MappingLoader(str(table(tmp_path)))
    parser = implementation['parser'].ROCrateParser(str(input_file(tmp_path / 'source.json', ['A', 'A'])))
    merger = implementation['merger'].ROCrateMerger(mapping)
    assert merger.merge_rocrates([parser])['creators'] == [{'description': 'A'}, {'description': 'A'}]
    presence = merger.get_source_presence()
    next(row for row in mapping.mappings if row.get('Func') == MARKER)['Func'] = ''
    assert merger.merge_rocrates([parser])['creators'] == ['A']
    assert merger.get_creator_assertion_sources() is None
    assert merger.get_source_presence() == presence
    assert 'CREATOR ASSERTION CONSTRUCTION' not in merger.generate_merge_report([parser])


@pytest.mark.parametrize('change,reason', [
    ('absent', 'no_covered_creators_route'),
    ('different', 'different_source_property'),
    ('multiple', 'multiple_covered_creators_routes'),
])
def test_unmarked_custom_routes_disclose_not_measured_without_claiming_source_absence(
        legacy, tmp_path, change, reason):
    _, _, api = legacy
    mapping = table(tmp_path, marked=False)
    text = mapping.read_text()
    creator = 'creators\tstr\tauthor\t\t1\t1\n'
    if change == 'absent': text = text.replace(creator, '')
    elif change == 'different': text = text.replace(creator, creator.replace('author', 'owner'))
    else: text += creator.replace('author', 'owner')
    mapping.write_text(text)
    transformer = api.SemanticTransformer(api.TransformationConfig(
        mapping_file=mapping, validate_input=False, validate_output=False,
        preserve_provenance=False, result_contract='dataset_v1'))
    result = transformer.rocrate_to_d4d(input_file(tmp_path / 'source.json', ['Available author']))
    assert result.source_presence == {
        'format': 'legacy_author_source_presence_v1', 'status': 'not_measured',
        'reason': reason, 'target': 'creators', 'source_property': 'author',
        'root_scope': 'selected_root', 'sources': []}
    assert result.coverage_basis['is_source_coverage'] is False


@pytest.mark.parametrize('contract', ['legacy', 'dataset_v1'])
def test_actual_scoring_and_auto_ranking_are_marker_independent(legacy, tmp_path, contract):
    _, _, api = legacy
    values = [ABSENT, ['A', 'A'], {'@id': 'https://orcid.org/reference'}, False]
    paths = [input_file(tmp_path / f'{i}.json', value) for i, value in enumerate(values)]
    tables = mapping_pair(tmp_path)
    ranks, outputs = [], []
    for mapping in tables:
        transformer = api.SemanticTransformer(api.TransformationConfig(
            mapping_file=mapping, validate_input=False, validate_output=False,
            preserve_provenance=False, result_contract=contract))
        parsers = [api._parse_rocrate(path) for path in paths]
        ranked = api.InformativenessScorer().rank_rocrates(parsers, transformer.mapping_loader)
        ranks.append([(str(p.rocrate_path), scores, rank) for p, scores, rank in ranked])
        outputs.append(transformer.merge_rocrates(paths, auto_prioritize=True))
    assert encoded(ranks[0]) == encoded(ranks[1])
    assert outputs[0]['source_presence'] == outputs[1]['source_presence']
    rows = outputs[1]['source_presence']['sources']
    assert [r['source_name'] for r in rows] == [p.rsplit('/', 1)[-1][:-5] for p, _, _ in ranks[1]]
    assert [r['source_index'] for r in rows] == list(range(len(paths)))
    assert [r['selected_primary'] for r in rows] == [True, False, False, False]
    assert sum(r['immediate_assertion_units'] for r in rows) == 4
    assert 'coverage_percentage' not in outputs[1]
    assert 'source_presence' not in outputs[1]['d4d' if contract == 'legacy' else 'data']


@pytest.mark.parametrize('values', [[False, 0, None, ['x']], ['', [], {}, None]])
def test_raw_measurement_counts_immediate_units_without_flattening_or_truthiness(
        implementation, tmp_path, values):
    mapping = table(tmp_path)
    parser = implementation['parser'].ROCrateParser(str(input_file(tmp_path / 'source.json', values)))
    merger = implementation['merger'].ROCrateMerger(implementation['loader'].MappingLoader(str(mapping)))
    merged = merger.merge_rocrates([parser])
    row = merger.get_source_presence()['sources'][0]
    assert row['immediate_assertion_units'] == len(values)
    assert encoded(row['raw_value']) == encoded(values)
    assert len(merged['creators']) == len(values)
    assert merger.get_creator_assertion_sources()[0]['output_range'] == [0, len(values)]
    with pytest.raises(publication.PublicationError, match='creators'):
        publication.prepare_dataset(merged)


@pytest.mark.parametrize('index', [-1, -3, True, False, 0.0, 1.0, '0', None, 2, 100])
def test_marked_invalid_primary_refuses_before_root_reads_or_state_changes(
        implementation, tmp_path, monkeypatch, index):
    mapping = implementation['loader'].MappingLoader(str(table(tmp_path)))
    parsers = [implementation['parser'].ROCrateParser(str(input_file(tmp_path / f'{n}.json', [str(n)])))
               for n in range(2)]
    merger = implementation['merger'].ROCrateMerger(mapping)
    merger.merge_rocrates(parsers, primary_index=1, source_names=['other', 'chosen'])
    previous = deepcopy(merger.__dict__)
    def forbidden():
        pytest.fail('invalid marked primary reached source acquisition')
    for parser in parsers:
        monkeypatch.setattr(parser, 'require_root_dataset', forbidden)
    with pytest.raises(ValueError, match='primary_index'):
        merger.merge_rocrates(parsers, primary_index=index, source_names=['other', 'chosen'])
    # Compare actual retained values; helper objects may not define equality.
    for key in ('merged_data', 'provenance', 'merge_stats', 'primary_index', 'primary_name',
                'source_presence', 'creator_assertion_sources', 'root_identity_sources'):
        assert encoded(merger.__dict__[key]) == encoded(previous[key])


def test_unmarked_negative_primary_keeps_legacy_result_but_raw_roster_visits_once(
        implementation, tmp_path):
    mapping = implementation['loader'].MappingLoader(str(table(tmp_path, marked=False)))
    values = [['A'], ['B']]
    parsers = [implementation['parser'].ROCrateParser(str(input_file(tmp_path / f'{i}.json', value)))
               for i, value in enumerate(values)]
    merger = implementation['merger'].ROCrateMerger(mapping)
    record = merger.merge_rocrates(parsers, primary_index=-1, source_names=['first', 'last'])
    assert record['creators'] == ['B', 'A']
    assert merger.primary_index == -1 and merger.primary_name == 'last'
    rows = merger.get_source_presence()['sources']
    assert [row['source_index'] for row in rows] == [1, 0]
    assert [row['processing_index'] for row in rows] == [0, 1]
    assert [row['raw_value'] for row in rows] == [['B'], ['A']]
    assert sum(row['immediate_assertion_units'] for row in rows) == 2
    assert merger.get_creator_assertion_sources() is None
    assert all('output_range' not in row for row in rows)


def test_marked_route_ignores_tampered_property_cache_and_uses_same_raw_root(
        implementation, tmp_path):
    path = input_file(tmp_path / 'source.json', ['Actual author'])
    document = json.loads(path.read_text())
    root = next(row for row in document['@graph'] if row.get('@id') == './')
    root['owner'] = ['Unrelated owner']
    path.write_text(json.dumps(document))
    mapping = implementation['loader'].MappingLoader(str(table(tmp_path)))
    mapping.d4d_to_rocrate['creators'] = 'owner'
    parser = implementation['parser'].ROCrateParser(str(path))
    builder = implementation['builder'].D4DBuilder(mapping)
    assert builder.build_dataset(parser)['creators'] == [{'description': 'Actual author'}]
    merger = implementation['merger'].ROCrateMerger(mapping)
    assert merger.merge_rocrates([parser])['creators'] == [{'description': 'Actual author'}]
    assert merger.get_source_presence()['sources'][0]['raw_value'] == ['Actual author']
