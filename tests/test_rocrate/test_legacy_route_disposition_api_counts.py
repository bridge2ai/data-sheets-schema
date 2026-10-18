"""API construction diagnostics follow declared output slots, not source coverage."""
from copy import deepcopy
import csv
from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_root_identity import scoring_fields
from .test_legacy_publication import legacy
from .test_legacy_route_dispositions_core import assert_json, source, table


REPO = Path(__file__).resolve().parents[2]
ABSENT = object()
ALIASES = [
    ('machine_annotation_analyses', 'rai:machineAnnotationTools',
     'machine_annotation_tools', 'tool_descriptions'),
    ('external_resource', 'associatedPublication',
     'external_resources', 'external_resources'),
]
DEFERRED = [
    ('encoding', 'evi:formats'), ('existing_uses', 'rai:dataUseCases'),
    ('other_tasks', 'rai:dataUseCases'), ('data_protection_impacts', 'rai:dataSocialImpact'),
    ('confidential_elements', 'rai:personalSensitiveInformation'),
    ('ip_restrictions', 'license,conditionsOfAccess'),
    ('extension_mechanism', 'license,conditionsOfAccess'), ('version_access', 'version'),
]


def transformer(api, monkeypatch, mapping, *, contract='dataset_v1', provenance=False):
    # Optional validation is separate from the real final Dataset publication gate.
    monkeypatch.setattr(api, 'VALIDATION_AVAILABLE', False)
    return api.SemanticTransformer(api.TransformationConfig(
        mapping_file=mapping, validate_input=False, validate_output=False,
        preserve_provenance=provenance, result_contract=contract))


def basis(numerator, denominator):
    return {'kind': 'constructed_field_presence', 'count_rule': 'non_null_mapped_value',
            'numerator': numerator, 'denominator': denominator,
            'is_source_coverage': False, 'is_validation_success': False}


@pytest.mark.parametrize('contract', ['legacy', 'dataset_v1'])
@pytest.mark.parametrize('provenance', [False, True])
@pytest.mark.parametrize('input_kind', ['path', 'dict'])
def test_alias_counts_follow_constructed_slots_in_both_api_contracts(
        legacy, tmp_path, monkeypatch, contract, provenance, input_kind):
    _, _, api = legacy
    mapping = table(tmp_path, [
        ('bytes', 'contentSize'), ('external_resource', 'associatedPublication'),
        ('machine_annotation_analyses', 'rai:machineAnnotationTools'), ('version_access', 'version')])
    path = source(tmp_path / 'source.json', {
        'contentSize': '2.3 TB', 'evi:totalContentSizeBytes': 0,
        'associatedPublication': ['same', 'same'], 'rai:machineAnnotationTools': ' Tool ',
        'version': 'documentary version'})
    supplied = json.loads(path.read_bytes()) if input_kind == 'dict' else path
    supplied_before = deepcopy(supplied) if input_kind == 'dict' else path.read_bytes()
    mapping_before = mapping.read_bytes()
    producer = transformer(api, monkeypatch, mapping, contract=contract, provenance=provenance)
    output = tmp_path / 'record.yaml' if contract == 'dataset_v1' else None
    result = producer.rocrate_to_d4d(supplied, output_path=output)
    expected = {'id': 'doi:10.1234/Disposition', 'title': 'Selected root',
                'total_size_bytes': 0,
                'external_resources': [{'external_resources': ['same']}, {'external_resources': ['same']}],
                'machine_annotation_tools': [{'tool_descriptions': ' Tool '}]}
    data = deepcopy(result.data)
    data.pop('transformation_metadata', None)
    assert_json(data, expected)
    assert scoring_fields(producer.mapping_loader) == [
        'title', 'bytes', 'external_resource', 'machine_annotation_analyses', 'version_access']
    assert result.unmapped_fields == ['version_access']
    assert result.coverage_percentage == 80.0
    assert result.coverage_basis == basis(4, 5)
    assert result.validation_passed is None
    assert_json(result.route_dispositions['constructed_values'], {
        key: expected[key] for key in ['total_size_bytes', 'external_resources', 'machine_annotation_tools']})
    for obsolete in ['bytes', 'external_resource', 'machine_annotation_analyses', 'version_access']:
        assert obsolete not in result.data
    if provenance:
        assert result.transformation_metadata['coverage_basis'] == basis(4, 5)
        assert result.transformation_metadata['unmapped_fields'] == ['version_access']
        result.coverage_basis['numerator'] = 999
        assert result.transformation_metadata['coverage_basis'] == basis(4, 5)
    else:
        assert result.transformation_metadata is None
    if output is not None:
        raw = output.read_bytes()
        assert_json(yaml.safe_load(raw), expected)
        assert publication.prepare_dataset(expected, text=raw.decode('utf-8')) == raw
        sidecar = json.loads(output.with_name('record_route_dispositions.json').read_bytes())
        assert sidecar['dataset'] == {
            'path': str(output.resolve()), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
        assert_json(sidecar['evidence'], result.route_dispositions)
    assert (supplied if input_kind == 'dict' else path.read_bytes()) == supplied_before
    assert mapping.read_bytes() == mapping_before


@pytest.mark.parametrize('field,predicate,target,child', ALIASES, ids=['machine', 'external'])
@pytest.mark.parametrize('value,strings', [
    (ABSENT, None), (None, None), (False, None), (0, None),
    ('', ['']), ([], []), (['same', 'same'], ['same', 'same']), ([False, 0, None], []),
], ids=['absent', 'null', 'false', 'zero', 'empty-string', 'empty-list', 'duplicates', 'declined-units'])
def test_narrative_alias_presence_uses_non_null_construction_not_truthiness(
        legacy, tmp_path, monkeypatch, field, predicate, target, child, value, strings):
    _, _, api = legacy
    mapping = table(tmp_path, [(field, predicate)])
    path = source(tmp_path / 'source.json', {} if value is ABSENT else {predicate: value})
    before = path.read_bytes()
    result = transformer(api, monkeypatch, mapping).rocrate_to_d4d(path)
    expected = {'id': 'doi:10.1234/Disposition', 'title': 'Selected root'}
    if strings is not None:
        expected[target] = [{child: [s] if target == 'external_resources' else s} for s in strings]
    assert_json(result.data, expected)
    assert result.unmapped_fields == ([field] if strings is None else [])
    assert result.coverage_basis == basis(1 if strings is None else 2, 2)
    assert result.coverage_percentage == (50.0 if strings is None else 100.0)
    assert field not in result.data
    publication.prepare_dataset(result.data)
    assert path.read_bytes() == before


@pytest.mark.parametrize('value,constructed', [
    (ABSENT, False), (None, False), (False, False), (0, True), (17, True),
    (-1, False), (0.0, False), ('17', False), ('', False), ([], False), ({}, False),
], ids=['absent', 'null', 'false', 'zero', 'positive', 'negative', 'float', 'numeric-text',
        'empty-string', 'empty-list', 'object'])
def test_only_exact_nonnegative_supplemental_integer_constructs_bytes_route(
        legacy, tmp_path, monkeypatch, value, constructed):
    _, _, api = legacy
    mapping = table(tmp_path, [('bytes', 'contentSize')])
    properties = {'contentSize': '2.3 TB'}
    if value is not ABSENT:
        properties['evi:totalContentSizeBytes'] = value
    path = source(tmp_path / 'source.json', properties)
    before = path.read_bytes()
    result = transformer(api, monkeypatch, mapping).rocrate_to_d4d(path)
    expected = {'id': 'doi:10.1234/Disposition', 'title': 'Selected root'}
    if constructed:
        expected['total_size_bytes'] = value
        assert type(result.data['total_size_bytes']) is int
    assert_json(result.data, expected)
    assert result.unmapped_fields == ([] if constructed else ['bytes'])
    assert result.coverage_basis == basis(2 if constructed else 1, 2)
    assert result.coverage_percentage == (100.0 if constructed else 50.0)
    assert 'bytes' not in result.data
    publication.prepare_dataset(result.data)
    assert path.read_bytes() == before


@pytest.mark.parametrize('value', [ABSENT, None, False, 0, '', []],
                         ids=['absent', 'null', 'false', 'zero', 'empty-string', 'empty-list'])
def test_all_deferred_routes_stay_in_denominator_and_unmapped_even_with_assertions(
        legacy, tmp_path, monkeypatch, value):
    _, _, api = legacy
    mapping = table(tmp_path, DEFERRED)
    properties = ({} if value is ABSENT else
                  {predicate: deepcopy(value) for _, predicates in DEFERRED
                   for predicate in predicates.split(',')})
    path = source(tmp_path / 'source.json', properties)
    result = transformer(api, monkeypatch, mapping).rocrate_to_d4d(path)
    assert_json(result.data, {'id': 'doi:10.1234/Disposition', 'title': 'Selected root'})
    assert result.unmapped_fields == [field for field, _ in DEFERRED]
    assert result.coverage_basis == basis(1, 9)
    assert result.coverage_percentage == 1 / 9 * 100
    assert result.route_dispositions['constructed_values'] == {}
    for field, predicates in DEFERRED:
        assertions = result.route_dispositions['sources'][0]['routes'][field]
        assert [row['property'] for row in assertions] == predicates.split(',')
        for row in assertions:
            assert row['present'] is (value is not ABSENT)
            if value is not ABSENT:
                assert_json(row['raw'], value)
    publication.prepare_dataset(result.data)


@pytest.mark.parametrize('value,expected', [
    (ABSENT, ABSENT), (None, ABSENT), (False, 'False'), (0, '0'), ('', ''), ([], []),
], ids=['absent', 'null', 'false', 'zero', 'empty-string', 'empty-list'])
def test_unmarked_custom_alias_keeps_original_field_lookup_and_metadata_contract(
        legacy, tmp_path, monkeypatch, value, expected):
    _, _, api = legacy
    mapping = table(tmp_path, [('bytes', 'custom:bytes')], marked=False)
    path = source(tmp_path / 'source.json', {} if value is ABSENT else {'custom:bytes': value})
    result = transformer(api, monkeypatch, mapping, provenance=True).rocrate_to_d4d(path)
    constructed = expected is not ABSENT
    assert ('bytes' in result.data) is constructed
    if constructed:
        assert_json(result.data['bytes'], expected)
    assert 'total_size_bytes' not in result.data
    assert result.unmapped_fields == ([] if constructed else ['bytes'])
    assert result.coverage_basis == basis(2 if constructed else 1, 2)
    assert result.coverage_percentage == (100.0 if constructed else 50.0)
    assert not hasattr(result, 'route_dispositions')
    assert 'coverage_basis' not in result.transformation_metadata


def test_unmarked_actual_dataset_slots_keep_false_zero_and_empty_values(
        legacy, tmp_path, monkeypatch):
    _, _, api = legacy
    mapping = table(tmp_path, [
        ('is_tabular', 'custom:boolean'), ('total_size_bytes', 'custom:size'),
        ('description', 'custom:text'), ('keywords', 'custom:keywords')], marked=False)
    with mapping.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.reader(stream, delimiter='\t'))
    types = {'is_tabular': 'bool', 'total_size_bytes': 'int', 'description': 'str', 'keywords': 'list[str]'}
    for row in rows[1:]:
        if row[0] in types:
            row[1] = types[row[0]]
    with mapping.open('w', newline='', encoding='utf-8') as stream:
        csv.writer(stream, delimiter='\t', lineterminator='\n').writerows(rows)
    path = source(tmp_path / 'source.json', {
        'custom:boolean': False, 'custom:size': 0, 'custom:text': '', 'custom:keywords': []})
    result = transformer(api, monkeypatch, mapping).rocrate_to_d4d(path)
    assert_json(result.data, {'id': 'doi:10.1234/Disposition', 'title': 'Selected root',
                             'is_tabular': False, 'total_size_bytes': 0, 'description': '', 'keywords': []})
    assert result.coverage_basis == basis(5, 5)
    assert result.coverage_percentage == 100.0 and result.unmapped_fields == []
    publication.prepare_dataset(result.data)


def test_default_81_route_denominator_and_source_ranking_do_not_gain_from_size_supplement(
        legacy, tmp_path, monkeypatch):
    _, _, api = legacy
    mapping = REPO / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
    original_mapping = mapping.read_bytes()
    producer = transformer(api, monkeypatch, mapping)
    fields = scoring_fields(producer.mapping_loader)
    assert len(fields) == 81 and 'bytes' in fields and 'total_size_bytes' not in fields
    projection = [{'field': field, 'ordered_sources': [p.strip() for p in
                   producer.mapping_loader.get_rocrate_property(field).split(',')]} for field in fields]
    encoded = json.dumps(projection, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode('utf-8')
    assert sha256(encoded).hexdigest() == '5d087ececc9d8cc50a4b1a95114483410382117ef821d916d8f6ddc8c025a587'
    paths = [source(tmp_path / 'without.json', {'contentSize': '2.3 TB'}),
             source(tmp_path / 'with.json', {'contentSize': '2.3 TB', 'evi:totalContentSizeBytes': 0})]
    inputs = [json.loads(path.read_bytes()) for path in paths]
    before_inputs = deepcopy(inputs)
    old, new = [producer.rocrate_to_d4d(value) for value in inputs]
    assert old.source_presence == new.source_presence
    assert 'bytes' in old.unmapped_fields and 'bytes' not in new.unmapped_fields
    assert new.unmapped_fields == [field for field in old.unmapped_fields if field != 'bytes']
    assert new.coverage_basis == basis(old.coverage_basis['numerator'] + 1, 81)
    assert old.coverage_basis['denominator'] == 81
    expected = deepcopy(old.data)
    expected['total_size_bytes'] = 0
    assert_json(new.data, expected)
    scorer = api.InformativenessScorer()
    scores = [scorer.score_rocrate(api.ROCrateParser(str(path)), producer.mapping_loader) for path in paths]
    assert scores[0]['d4d_coverage'] == scores[1]['d4d_coverage']
    # Metadata richness may see the extra property; no complete score equality is claimed.
    assert_json(inputs, before_inputs)
    assert mapping.read_bytes() == original_mapping
