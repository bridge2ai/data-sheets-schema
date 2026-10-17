"""Paired #4046 routes through genuine FAIRSCAPE models, with explicit limits.

Canonical wire projections do not prove scientific equivalence or literal
JSON-shape fidelity. Complete explicit compatibility groups remain separate.
"""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.fairscape_integration.d4d_to_fairscape import D4DToFairscapeConverter
from src.fairscape_integration.fairscape_to_d4d import FairscapeToD4DConverter
from fairscape_models.rocrate import ROCrateMetadataElem, ROCrateV1_2


ABSENT = object()
CARRIERS = (
    ('confidential_elements', 'd4d:confidentialElements'),
    ('acquisition_methods', 'd4d:acquisitionMethods'),
    ('data_protection_impacts', 'd4d:dataProtectionImpacts'),
    ('labeling_strategies', 'd4d:labelingStrategies'),
)


def typed(value):
    if type(value) is dict:
        return (dict, tuple((k, typed(v)) for k, v in value.items()))
    if type(value) is list:
        return (list, tuple(typed(v) for v in value))
    return (type(value), value.hex() if type(value) is float else value)


def dataset(properties=None):
    value = {'id': './', 'title': 'Paired route probe', 'description': 'Whole narrative',
             'keywords': [], 'version': '1.0'}
    value.update(properties or {})
    return value


def crate(properties=None, *, nodes=()):
    root = {'@id': './', '@type': ['Dataset', 'https://w3id.org/EVI#ROCrate'],
            'name': 'Paired route probe', 'description': 'Whole narrative',
            'keywords': [], 'version': '1.0', 'author': 'Synthetic author',
            'license': 'https://example.org/license', 'hasPart': []}
    root.update(properties or {})
    return {'@context': {'@vocab': 'https://schema.org/'}, '@graph': [
        {'@id': 'ro-crate-metadata.json', '@type': 'CreativeWork',
         'conformsTo': {'@id': 'https://w3id.org/ro/crate/1.2'}, 'about': {'@id': './'}},
        root, *deepcopy(nodes)]}


def reverse(value, converter=None):
    converter = converter or FairscapeToD4DConverter()
    with contextlib.redirect_stdout(io.StringIO()):
        record = converter.convert(value)
    return record, converter


def forward(value, *, source_evidence=ABSENT, converter=None):
    converter = converter or D4DToFairscapeConverter()
    kwargs = {} if source_evidence is ABSENT else {'source_evidence': source_evidence}
    with contextlib.redirect_stdout(io.StringIO()):
        model = converter.convert(value, **kwargs)
    assert type(model) is ROCrateV1_2
    dumped = model.model_dump(mode='json', by_alias=True, exclude_none=True)
    encoded = json.dumps(dumped, ensure_ascii=True, allow_nan=False).encode('utf-8')
    # Ordinary model_validate consumes a separate JSON graph, never caller input.
    readback = ROCrateV1_2.model_validate(json.loads(encoded))
    redumped = readback.model_dump(mode='json', by_alias=True, exclude_none=True)
    assert typed(dumped) == typed(redumped)
    roots = [v for v in readback.metadataGraph if v.guid == './']
    assert len(roots) == 1 and type(roots[0]) is ROCrateMetadataElem
    wire_roots = [v for v in redumped['@graph'] if v['@id'] == './']
    assert len(wire_roots) == 1
    return wire_roots[0], readback, converter


def row_for(converter, source, target=ABSENT):
    rows = [r for r in converter.route_evidence['assertions'] if r['source'] == source
            and (target is ABSENT or r['target'] == target)]
    assert len(rows) == 1
    return rows[0]


def test_four_canonical_homes_do_not_assert_confidentiality_acquisition_or_dpia():
    raw = {'rai:personalSensitiveInformation': ['S; whole', 'S; whole', ''],
           'rai:dataCollection': 'Collection narrative', 'rai:dataSocialImpact': 'Future risk narrative',
           'rai:dataAnnotationProtocol': 'Annotation protocol'}
    record, converter = reverse(crate(raw))
    assert record['sensitive_elements'] == [{'sensitivity_details': v} for v in raw['rai:personalSensitiveInformation']]
    assert record['collection_mechanisms'] == [{'mechanism_details': raw['rai:dataCollection']}]
    assert record['future_use_impacts'] == [{'impact_details': raw['rai:dataSocialImpact']}]
    assert record['labeling_strategies'] == [{'data_annotation_protocol': raw['rai:dataAnnotationProtocol']}]
    assert all(k not in record for k in ('confidential_elements', 'acquisition_methods', 'data_protection_impacts'))
    assert all('sensitive_elements_present' not in v for v in record['sensitive_elements'])
    wire, _, _ = forward(record)
    for key, value in raw.items():
        assert typed(wire[key]) == typed(value)
        assert typed(row_for(converter, key)['raw']) == typed(value)
    assert all(k not in wire for k in ('d4d:confidentialElements', 'd4d:acquisitionMethods', 'd4d:dataProtectionImpacts'))
    assert wire['d4d:labelingStrategies'] == record['labeling_strategies']


@pytest.mark.parametrize('slot,carrier', CARRIERS)
def test_explicit_carrier_records_retain_duplicate_ids_order_and_whole_objects(slot, carrier):
    values = [{'id': '#same', 'description': 'Second α\nwhole'},
              {'id': '#other', 'description': 'First'},
              {'id': '#same', 'description': 'Second α\nwhole'}]
    supplied = dataset({slot: values})
    before = typed(supplied)
    wire, model, converter = forward(supplied)
    assert typed(wire[carrier]) == typed(values)
    assert typed(supplied) == before
    record, reverse_converter = reverse(model)
    assert typed(record[slot]) == typed(values)
    assert typed(row_for(reverse_converter, carrier)['raw']) == typed(values)
    assert typed(row_for(converter, slot, carrier)['raw']) == typed(values)


def test_independently_supplied_old_slots_coexist_with_canonical_homes():
    raw = {'rai:personalSensitiveInformation': ['Sensitive description'],
           'rai:dataCollection': 'Collection description', 'rai:dataSocialImpact': 'Future impact description',
           'd4d:confidentialElements': [{'description': 'Explicit confidentiality assertion'}],
           'd4d:acquisitionMethods': [{'description': 'Explicit acquisition assertion'}],
           'd4d:dataProtectionImpacts': [{'impact_details': 'Explicit DPIA assertion'}]}
    record, _ = reverse(crate(raw))
    assert record['sensitive_elements'] == [{'sensitivity_details': 'Sensitive description'}]
    assert record['confidential_elements'] == raw['d4d:confidentialElements']
    assert record['collection_mechanisms'] == [{'mechanism_details': 'Collection description'}]
    assert record['acquisition_methods'] == raw['d4d:acquisitionMethods']
    assert record['future_use_impacts'] == [{'impact_details': 'Future impact description'}]
    assert record['data_protection_impacts'] == raw['d4d:dataProtectionImpacts']
    wire, _, _ = forward(record)
    for key, value in raw.items():
        assert typed(wire[key]) == typed(value)


def test_matching_annotation_summary_is_one_record_not_a_canonical_echo():
    summary = {'data_annotation_protocol': 'P', 'data_annotation_platform': 'A', 'annotations_per_item': 0}
    value = crate({'d4d:labelingStrategies': [summary], 'rai:dataAnnotationProtocol': 'P',
                   'rai:dataAnnotationPlatform': ['A'], 'rai:annotationsPerItem': '0'})
    before = typed(value)
    record, converter = reverse(value)
    assert record['labeling_strategies'] == [summary]
    assert typed(value) == before
    for key in ('d4d:labelingStrategies', 'rai:dataAnnotationProtocol', 'rai:dataAnnotationPlatform', 'rai:annotationsPerItem'):
        assert typed(row_for(converter, key)['raw']) == typed(value['@graph'][1][key])
    wire, readback, _ = forward(record)
    assert wire['d4d:labelingStrategies'] == [summary]
    assert wire['rai:dataAnnotationProtocol'] == 'P'
    assert wire['rai:dataAnnotationPlatform'] == ['A']
    assert wire['rai:annotationsPerItem'] == '0'
    assert reverse(readback)[0]['labeling_strategies'] == [summary]


def test_matching_platform_projection_preserves_internal_duplicate_records():
    repeated = [{'data_annotation_platform': 'A'}, {'data_annotation_platform': 'A'}]
    record, converter = reverse(crate({'d4d:labelingStrategies': repeated,
                                       'rai:dataAnnotationPlatform': ['A', 'A']}))
    assert record['labeling_strategies'] == repeated
    assert row_for(converter, 'rai:dataAnnotationPlatform')['raw'] == ['A', 'A']
    wire, _, _ = forward(record)
    assert wire['rai:dataAnnotationPlatform'] == ['A', 'A']
    assert wire['d4d:labelingStrategies'] == repeated


def test_disagreeing_canonical_platform_is_an_independent_assertion_after_carrier():
    groups = [{'data_annotation_protocol': 'Group protocol', 'data_annotation_platform': 'A'}]
    record, converter = reverse(crate({'d4d:labelingStrategies': groups, 'rai:dataAnnotationPlatform': ['B']}))
    assert record['labeling_strategies'] == groups + [{'data_annotation_platform': 'B'}]
    assert row_for(converter, 'd4d:labelingStrategies')['raw'] == groups
    assert row_for(converter, 'rai:dataAnnotationPlatform')['raw'] == ['B']


def test_multiple_protocols_and_platforms_never_zip_or_broadcast_count():
    record, converter = reverse(crate({'rai:dataAnnotationProtocol': ['P2', 'P1', 'P2'],
                                       'rai:dataAnnotationPlatform': ['B', 'A'],
                                       'rai:annotationsPerItem': '3'}))
    groups = record['labeling_strategies']
    assert groups == [{'data_annotation_protocol': 'P2'}, {'data_annotation_protocol': 'P1'},
                      {'data_annotation_protocol': 'P2'}, {'data_annotation_platform': 'B'},
                      {'data_annotation_platform': 'A'}, {'annotations_per_item': 3}]
    assert all(len(group) == 1 for group in groups)
    assert sum('annotations_per_item' in group for group in groups) == 1
    for key, expected in [('rai:dataAnnotationProtocol', ['P2', 'P1', 'P2']),
                          ('rai:dataAnnotationPlatform', ['B', 'A']), ('rai:annotationsPerItem', '3')]:
        assert typed(row_for(converter, key)['raw']) == typed(expected)


@pytest.mark.parametrize('platforms', [[], ['A'], ['B', 'A', 'B'], ['']])
def test_platform_list_cardinality_order_and_empty_strings(platforms):
    record, converter = reverse(crate({'rai:dataAnnotationPlatform': platforms}))
    expected = [{'data_annotation_platform': v} for v in platforms]
    assert record.get('labeling_strategies', []) == expected
    assert typed(row_for(converter, 'rai:dataAnnotationPlatform')['raw']) == typed(platforms)
    if platforms:
        wire, _, _ = forward(record)
        assert wire['rai:dataAnnotationPlatform'] == platforms


@pytest.mark.parametrize('key,target,detail', [
    ('rai:personalSensitiveInformation', 'sensitive_elements', 'sensitivity_details'),
    ('rai:dataAnnotationPlatform', 'labeling_strategies', 'data_annotation_platform'),
])
def test_mixed_string_lists_preserve_supported_units_without_flattening(key, target, detail):
    supplied = ['A', False, 0, {'nested': 'B'}, ['C'], '', 'A']
    value = crate({key: supplied})
    before = typed(value)
    record, converter = reverse(value)
    assert record[target] == [{detail: 'A'}, {detail: ''}, {detail: 'A'}]
    row = row_for(converter, key)
    assert typed(row['raw']) == typed(supplied)
    assert row['retention'] == 'partial'
    assert converter.dropped
    assert typed(value) == before


@pytest.mark.parametrize('key,target', [
    ('rai:personalSensitiveInformation', 'sensitive_elements'),
    ('rai:dataCollection', 'collection_mechanisms'),
    ('rai:dataSocialImpact', 'future_use_impacts'),
    ('rai:dataAnnotationProtocol', 'labeling_strategies'),
    ('rai:dataAnnotationPlatform', 'labeling_strategies'),
    ('rai:annotationsPerItem', 'labeling_strategies'),
])
@pytest.mark.parametrize('presence', ['missing', 'null'])
def test_canonical_missing_and_null_are_recorded_without_constructed_assertions(key, target, presence):
    raw = {} if presence == 'missing' else {key: None}
    record, converter = reverse(crate(raw))
    assert target not in record
    row = row_for(converter, key)
    assert row['presence'] == presence and row['raw'] is None
    assert row['retention'] == 'not_constructed'


def test_rich_sensitivity_does_not_silently_drop_its_qualification_for_wire_text():
    values = [{'sensitivity_details': 'Stated sensitivity', 'description': 'Separate qualification'}]
    wire, _, converter = forward(dataset({'sensitive_elements': values}))
    assert 'rai:personalSensitiveInformation' not in wire
    row = row_for(converter, 'sensitive_elements', 'rai:personalSensitiveInformation')
    assert typed(row['raw']) == typed(values)
    assert row['retention'] == 'not_constructed'


@pytest.mark.parametrize('count', [0, 7, -2])
def test_canonical_count_string_and_integer_roundtrip_with_actual_models(count):
    supplied = dataset({'labeling_strategies': [{'annotations_per_item': count}]})
    wire, model, converter = forward(supplied)
    assert type(wire['rai:annotationsPerItem']) is str
    assert wire['rai:annotationsPerItem'] == str(count)
    assert type(wire['d4d:labelingStrategies'][0]['annotations_per_item']) is int
    record, reverse_converter = reverse(model)
    assert record['labeling_strategies'] == [{'annotations_per_item': count}]
    assert type(record['labeling_strategies'][0]['annotations_per_item']) is int
    assert row_for(reverse_converter, 'rai:annotationsPerItem')['raw'] == str(count)
    assert typed(row_for(converter, 'labeling_strategies', 'rai:annotationsPerItem')['raw']) == typed(supplied['labeling_strategies'])


@pytest.mark.parametrize('value', ['+3', '03', '-0', ' 3 ', '3.0', '3e0', 'three',
    '3 annotations', '٣', '３', '', False, True, 3.0, ['3'], {'count': 3}])
def test_noncanonical_count_spelling_or_type_is_not_interpreted(value):
    record, converter = reverse(crate({'rai:annotationsPerItem': value}))
    assert not any('annotations_per_item' in group for group in record.get('labeling_strategies', []))
    assert typed(row_for(converter, 'rai:annotationsPerItem')['raw']) == typed(value)
    assert row_for(converter, 'rai:annotationsPerItem')['decision'] == 'unplaced'


@pytest.mark.parametrize('count', [0, 3, -1])
def test_explicit_raw_integer_is_distinct_from_a_model_string(count):
    record, converter = reverse(crate({'rai:annotationsPerItem': count}))
    assert record['labeling_strategies'] == [{'annotations_per_item': count}]
    assert type(row_for(converter, 'rai:annotationsPerItem')['raw']) is int
    wire, _, _ = forward(record)
    assert wire['rai:annotationsPerItem'] == str(count)


def test_natural_integer_conversion_limit_is_reported_without_changing_it():
    limit_reader = getattr(sys, 'get_int_max_str_digits', None)
    limit = limit_reader() if limit_reader is not None else None
    text = '9' * ((limit + 1) if limit else 5000)
    try:
        expected = int(text)
    except ValueError:
        expected = ABSENT
    record, converter = reverse(crate({'rai:annotationsPerItem': text}))
    if expected is ABSENT:
        assert not any('annotations_per_item' in group for group in record.get('labeling_strategies', []))
        assert row_for(converter, 'rai:annotationsPerItem')['decision'] == 'unplaced'
    else:
        assert record['labeling_strategies'] == [{'annotations_per_item': expected}]
    assert row_for(converter, 'rai:annotationsPerItem')['raw'] == text
    if limit_reader is not None:
        assert limit_reader() == limit


@pytest.mark.parametrize('slot,detail,wire_key', [
    ('collection_mechanisms', 'mechanism_details', 'rai:dataCollection'),
    ('future_use_impacts', 'impact_details', 'rai:dataSocialImpact'),
    ('cleaning_strategies', 'cleaning_details', 'rai:dataManipulationProtocol'),
    ('funders', 'grantor', 'funder'),
])
@pytest.mark.parametrize('shape', ['multiple', 'richer'])
def test_scalar_model_fields_do_not_join_or_discard_richer_source_objects(slot, detail, wire_key, shape):
    values = [{detail: 'A'}, {detail: 'B'}] if shape == 'multiple' else [{detail: 'A', 'description': 'Additional assertion'}]
    wire, _, converter = forward(dataset({slot: values}))
    assert wire_key not in wire
    row = row_for(converter, slot, wire_key)
    assert typed(row['raw']) == typed(values)
    assert row['retention'] == 'not_constructed'


@pytest.mark.parametrize('field,key', [('data_annotation_protocol', 'rai:dataAnnotationProtocol'),
                                     ('annotations_per_item', 'rai:annotationsPerItem')])
def test_repeated_annotation_records_do_not_become_one_arbitrarily_selected_scalar(field, key):
    item = {field: 2 if field == 'annotations_per_item' else 'P'}
    groups = [deepcopy(item), deepcopy(item)]
    wire, _, converter = forward(dataset({'labeling_strategies': groups}))
    assert key not in wire
    assert wire['d4d:labelingStrategies'] == groups
    assert typed(row_for(converter, 'labeling_strategies', key)['raw']) == typed(groups)


def test_single_part_a_projections_survive_genuine_alias_dump_and_readback():
    values = {'citation': '  Citation α\nwhole  ',
              'cleaning_strategies': [{'cleaning_details': 'Clean; whole'}],
              'funders': [{'grantor': 'A, B'}],
              'human_subject_research': {'involves_human_subjects': False},
              'data_governance': {'description': 'Unbound narrative is not a committee assertion'}}
    supplied = dataset(values)
    before = typed(supplied)
    wire, model, _ = forward(supplied)
    assert wire['citation'] == values['citation']
    assert wire['rai:dataManipulationProtocol'] == 'Clean; whole'
    assert wire['funder'] == 'A, B'
    assert wire['humanSubjectResearch'] == 'No'
    assert 'humanSubjects' not in wire and 'dataGovernanceCommittee' not in wire and 'completeness' not in wire
    assert typed(supplied) == before
    record, _ = reverse(model)
    assert record['human_subject_research']['involves_human_subjects'] is False
    assert record['citation'] == values['citation']
    assert record['cleaning_strategies'] == values['cleaning_strategies']
    assert record['funders'] == values['funders']


@pytest.mark.parametrize('value,token', [(False, 'No'), (True, 'Yes')])
def test_human_boolean_wire_projection_never_creates_human_subjects(value, token):
    wire, model, converter = forward(dataset({'human_subject_research': {'involves_human_subjects': value}}))
    assert wire['humanSubjectResearch'] == token and 'humanSubjects' not in wire
    record, _ = reverse(model)
    assert record['human_subject_research']['involves_human_subjects'] is value
    assert converter.route_evidence['direction'] == 'd4d_to_fairscape'


@pytest.mark.parametrize('human', [ABSENT, {}, {'description': 'No boolean stated'}, {'involves_human_subjects': None}])
def test_missing_or_null_research_is_not_projected_as_No(human):
    values = {} if human is ABSENT else {'human_subject_research': human}
    wire, _, _ = forward(dataset(values))
    assert 'humanSubjectResearch' not in wire and 'humanSubjects' not in wire


def test_valid_bound_source_evidence_reemits_separate_literal_assertions():
    raw = {'citation': 'Citation', 'humanSubjects': False, 'humanSubjectResearch': 'No',
           'dataGovernanceCommittee': 'Source committee narrative', 'completeness': 'not measured'}
    record, reverse_converter = reverse(crate(raw))
    evidence = reverse_converter.route_evidence
    original_record, original_evidence = typed(record), typed(evidence)
    wire, model, forward_converter = forward(record, source_evidence=evidence)
    assert wire['humanSubjects'] == 'No' and wire['humanSubjectResearch'] == 'No'
    assert wire['dataGovernanceCommittee'] == raw['dataGovernanceCommittee']
    assert wire['completeness'] == 'not measured'
    assert typed(record) == original_record and typed(evidence) == original_evidence
    actual, _ = reverse(model)
    assert actual['human_subject_research']['involves_human_subjects'] is False
    assert actual['data_governance'] == {'description': raw['dataGovernanceCommittee']}
    assert 'completeness' not in actual
    assert forward_converter.route_evidence['status'] == 'complete'


def test_bound_richer_source_is_visible_without_becoming_a_model_string():
    raw = {'completeness': {'values': [False, 0, None]}, 'dataGovernanceCommittee': ['not', 'scalar']}
    record, reverse_converter = reverse(crate(raw))
    wire, _, converter = forward(record, source_evidence=reverse_converter.route_evidence)
    assert 'completeness' not in wire and 'dataGovernanceCommittee' not in wire
    rows = converter.route_evidence['assertions']
    for value in raw.values():
        assert any(typed(row['raw']) == typed(value) for row in rows)


@pytest.mark.parametrize('mutation', ['dataset', 'status', 'contract', 'duplicate', 'missing', 'target', 'pointer'])
def test_source_evidence_must_bind_the_complete_record_and_finite_direct_roster(mutation):
    record, reverse_converter = reverse(crate({'citation': 'Original', 'completeness': 'Unscored'}))
    evidence = reverse_converter.route_evidence
    if mutation == 'dataset':
        record['title'] = 'Changed unrelated Dataset field'
    elif mutation == 'status':
        evidence['status'] = 'pending'
    elif mutation == 'contract':
        evidence['contract'] = 'unknown-contract'
    else:
        at = next(i for i, r in enumerate(evidence['assertions']) if r['source'] == 'citation')
        if mutation == 'duplicate':
            evidence['assertions'].append(deepcopy(evidence['assertions'][at]))
        elif mutation == 'missing':
            evidence['assertions'].pop(at)
        elif mutation == 'target':
            evidence['assertions'][at]['target'] = 'description'
        elif mutation == 'pointer':
            evidence['assertions'][at]['source_pointer'] = '/@graph/999/citation'
    converter = D4DToFairscapeConverter()
    with pytest.raises(ValueError, match='evidence|binding|record|contract|assertion|pointer'):
        converter.convert(record, source_evidence=evidence)
    assert converter.route_evidence['status'] == 'failed'


def test_forward_evidence_is_detached_and_resets_after_a_failed_binding():
    record, reverse_converter = reverse(crate({'completeness': 'FIRST'}))
    converter = D4DToFairscapeConverter()
    wire, _, _ = forward(record, source_evidence=reverse_converter.route_evidence, converter=converter)
    assert wire['completeness'] == 'FIRST'
    saved = typed(converter.route_evidence)
    returned = converter.route_evidence
    returned['assertions'].clear()
    assert typed(converter.route_evidence) == saved
    stale = reverse_converter.route_evidence
    stale['final_dataset_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        converter.convert(record, source_evidence=stale)
    assert converter.route_evidence['status'] == 'failed'
    wire, _, _ = forward(dataset({'citation': 'NEXT'}), converter=converter)
    assert wire['citation'] == 'NEXT' and 'completeness' not in wire
    assert 'FIRST' not in json.dumps(converter.route_evidence)


def test_member_canonical_keys_and_carriers_do_not_replace_a_missing_root_assertion():
    member = {'@id': '#member', '@type': 'Dataset', 'name': 'Unreferenced member',
              'rai:personalSensitiveInformation': ['MEMBER'], 'rai:dataCollection': 'MEMBER',
              'rai:dataSocialImpact': 'MEMBER', 'rai:dataAnnotationProtocol': 'MEMBER',
              'rai:dataAnnotationPlatform': ['MEMBER'], 'rai:annotationsPerItem': '7'}
    for _, carrier in CARRIERS:
        member[carrier] = [{'description': 'MEMBER'}]
    for graph in (crate(nodes=[member])['@graph'], list(reversed(crate(nodes=[member])['@graph']))):
        record, converter = reverse({'@graph': graph})
        assert all(k not in record for k in ('sensitive_elements', 'collection_mechanisms',
            'future_use_impacts', 'labeling_strategies', 'confidential_elements',
            'acquisition_methods', 'data_protection_impacts'))
        assert 'MEMBER' not in json.dumps(converter.route_evidence)


def test_rich_labeling_group_survives_carrier_without_invented_workflow_fields():
    groups = [{'id': '#group', 'data_annotation_protocol': 'Literal protocol α\nline',
               'data_annotation_platform': 'Tool name as stated', 'annotations_per_item': 0,
               'inter_annotator_agreement': 'Source reports κ=0.8',
               'description': 'Whole independent qualification'}]
    wire, model, _ = forward(dataset({'labeling_strategies': groups}))
    assert typed(wire['d4d:labelingStrategies']) == typed(groups)
    record, _ = reverse(model)
    assert typed(record['labeling_strategies']) == typed(groups)
    assert not any('annotator_type' in group or 'steps' in group for group in record['labeling_strategies'])


def test_genuine_model_carrier_is_still_checked_by_final_d4d_schema():
    groups = [{'description': 'Survives', 'annotations_per_item': False}]
    raw = crate({'d4d:labelingStrategies': groups})
    before = typed(raw)
    model = ROCrateV1_2.model_validate(deepcopy(raw))
    dumped = model.model_dump(mode='json', by_alias=True, exclude_none=True)
    modeled_root = next(node for node in dumped['@graph'] if node['@id'] == './')
    assert type(modeled_root['d4d:labelingStrategies'][0]['annotations_per_item']) is bool
    record, converter = reverse(model)
    assert record['labeling_strategies'] == [{'description': 'Survives'}]
    row = row_for(converter, 'd4d:labelingStrategies')
    assert typed(row['raw']) == typed(groups)
    assert row['retention'] == 'partial'
    assert typed(row['final_value']) == typed(record['labeling_strategies'])
    assert any('annotations_per_item' in source and 'schema rejects' in reason
               for source, reason in converter.dropped)
    wire, _, _ = forward(record)
    assert 'rai:annotationsPerItem' not in wire
    assert wire['d4d:labelingStrategies'] == [{'description': 'Survives'}]
    assert typed(raw) == before


def test_removed_carrier_cannot_leave_retained_canonical_echo_credit(monkeypatch):
    groups = [{'data_annotation_protocol': 'P'}]
    raw = crate({'d4d:labelingStrategies': groups, 'rai:dataAnnotationProtocol': 'P'})
    converter = FairscapeToD4DConverter()
    settle = converter._settle
    def invalidate(record, origin, rivals):
        assert record['labeling_strategies'] == groups
        record['labeling_strategies'][0]['data_annotation_protocol'] = False
        return settle(record, origin, rivals)
    monkeypatch.setattr(converter, '_settle', invalidate)
    record, converter = reverse(raw, converter)
    assert 'labeling_strategies' not in record
    carrier = row_for(converter, 'd4d:labelingStrategies')
    echo = row_for(converter, 'rai:dataAnnotationProtocol')
    assert typed(carrier['raw']) == typed(groups) and echo['raw'] == 'P'
    assert echo['decision'] == 'redundant_projection'
    assert carrier['retention'] == echo['retention'] == 'not_retained'
    assert carrier['final_value'] is None and echo['final_value'] is None
    assert any('data_annotation_protocol' in source and 'schema rejects' in reason
               for source, reason in converter.dropped)


def test_labeling_property_value_and_independent_canonical_assertion_keep_lineage():
    prop = {'@type': 'PropertyValue', 'name': 'Labeling Strategies',
            'value': [{'description': 'Independent PropertyValue group'}],
            'qualification': 'Retained in raw evidence'}
    raw = crate({'additionalProperty': [prop], 'rai:dataAnnotationProtocol': 'P'})
    before = typed(raw)
    record, converter = reverse(raw)
    assert record['labeling_strategies'] == [
        {'description': 'Independent PropertyValue group'}, {'data_annotation_protocol': 'P'}]
    legacy = row_for(converter, 'additionalProperty: Labeling Strategies')
    assert legacy['decision'] == 'legacy' and legacy['retention'] == 'retained'
    assert legacy['source_pointer'] == '/@graph/1/additionalProperty/0'
    assert typed(legacy['raw']) == typed(prop)
    assert typed(legacy['final_value']) == typed(record['labeling_strategies'])
    canonical = row_for(converter, 'rai:dataAnnotationProtocol')
    assert canonical['raw'] == 'P' and canonical['retention'] == 'retained'
    assert typed(raw) == before


def test_explicit_carriers_keep_schema_valid_empty_null_and_false_values():
    groups = [{'data_annotation_platform': '', 'data_annotation_protocol': '',
               'annotations_per_item': None, 'description': None,
               'annotator_demographics': ['']}]
    confidential = [{'confidential_elements_present': False,
                     'confidentiality_details': '', 'description': None}]
    supplied = dataset({'labeling_strategies': groups, 'confidential_elements': confidential})
    before = typed(supplied)
    wire, model, _ = forward(supplied)
    assert typed(wire['d4d:labelingStrategies']) == typed(groups)
    assert typed(wire['d4d:confidentialElements']) == typed(confidential)
    record, converter = reverse(model)
    assert typed(record['labeling_strategies']) == typed(groups)
    assert typed(record['confidential_elements']) == typed(confidential)
    for carrier, original in [('d4d:labelingStrategies', groups),
                              ('d4d:confidentialElements', confidential)]:
        row = row_for(converter, carrier)
        assert typed(row['raw']) == typed(original)
        assert typed(row['final_value']) == typed(original)
        assert row['retention'] == 'retained'
    assert typed(supplied) == before


@pytest.mark.parametrize('slot,carrier', CARRIERS)
def test_explicit_empty_carrier_list_remains_an_empty_list(slot, carrier):
    supplied = dataset({slot: []})
    before = typed(supplied)
    wire, model, forward_converter = forward(supplied)
    assert carrier in wire and wire[carrier] == []
    outgoing = row_for(forward_converter, slot, carrier)
    assert outgoing['raw'] == [] and outgoing['retention'] == 'retained'
    record, reverse_converter = reverse(model)
    assert slot in record and record[slot] == []
    incoming = row_for(reverse_converter, carrier)
    assert incoming['presence'] == 'present' and incoming['raw'] == []
    assert incoming['retention'] == 'retained' and incoming['final_value'] == []
    assert typed(supplied) == before
