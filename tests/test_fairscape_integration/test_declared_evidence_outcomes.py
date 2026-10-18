"""Observed legacy-assertion outcomes for #4046, independent of final-value equality."""
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

from src.fairscape_integration.fairscape_to_d4d import FairscapeToD4DConverter
from src.fairscape_integration.d4d_to_fairscape import D4DToFairscapeConverter


def typed(value):
    if type(value) is dict:
        return (dict, tuple((k, typed(v)) for k, v in value.items()))
    if type(value) is list:
        return (list, tuple(typed(v) for v in value))
    return (type(value), value.hex() if type(value) is float else value)


def crate(properties):
    root = {'@id': './', '@type': ['Dataset', 'https://w3id.org/EVI#ROCrate'],
            'name': 'Evidence outcomes', 'description': 'Synthetic fixture',
            'keywords': [], 'version': '1.0', 'author': 'Synthetic author',
            'license': 'https://example.org/license', 'hasPart': []}
    root.update(properties)
    return {'@graph': [{'@id': 'ro-crate-metadata.json', '@type': 'CreativeWork',
                       'conformsTo': {'@id': 'https://w3id.org/ro/crate/1.2'},
                       'about': {'@id': './'}}, root]}


def convert(value, converter=None):
    converter = converter or FairscapeToD4DConverter()
    with contextlib.redirect_stdout(io.StringIO()):
        record = converter.convert(value)
    assert converter.route_evidence['status'] == 'complete'
    return record, converter


def rows(converter, source):
    return [r for r in converter.route_evidence['assertions'] if r['source'] == source]


def one(converter, source):
    found = rows(converter, source)
    assert len(found) == 1
    return found[0]


def test_standalone_structured_human_alias_is_observed_as_retained():
    alias = {'description': 'Literal alias', 'involves_human_subjects': False}
    value = crate({'d4d:humanSubject': alias})
    before = typed(value)
    record, converter = convert(value)
    assert record['human_subject_research'] == alias
    row = one(converter, 'd4d:humanSubject')
    assert row['decision'] == 'legacy' and row['retention'] == 'retained'
    assert typed(row['raw']) == typed(alias)
    assert typed(row['final_value']) == typed(record['human_subject_research'])
    assert row['source_pointer'] == '/@graph/1/d4d:humanSubject'
    assert typed(value) == before


@pytest.mark.parametrize('name,target,value', [
    ('Citation', 'citation', 'Whole citation'),
    ('Human Subject', 'human_subject_research', {'description': 'Legacy human'}),
    ('Human Subject Research', 'human_subject_research', {'involves_human_subjects': False}),
    ('Data Governance', 'data_governance', {'description': 'Legacy governance'}),
    ('Cleaning Strategies', 'cleaning_strategies', [{'cleaning_details': 'Legacy cleaning'}]),
    ('Funders', 'funders', [{'grantor': 'Legacy funder'}]),
])
def test_standalone_property_value_has_its_actual_retained_outcome(name, target, value):
    prop = {'@type': 'PropertyValue', 'name': name, 'value': value, 'unmapped_qualification': [False, 0]}
    record, converter = convert(crate({'additionalProperty': [prop]}))
    assert typed(record[target]) == typed(value)
    row = one(converter, 'additionalProperty: ' + name)
    assert row['decision'] == 'legacy' and row['retention'] == 'retained'
    assert typed(row['raw']) == typed(prop)
    assert typed(row['final_value']) == typed(record[target])
    assert row['source_pointer'] == '/@graph/1/additionalProperty/0'


def test_canonical_human_wins_but_alias_final_value_is_not_alias_retention():
    alias = {'description': 'Alias opposition', 'involves_human_subjects': True}
    record, converter = convert(crate({'humanSubjectResearch': 'No', 'd4d:humanSubject': alias}))
    assert record['human_subject_research']['involves_human_subjects'] is False
    old = one(converter, 'd4d:humanSubject')
    assert old['decision'] == 'legacy' and old['retention'] == 'not_retained'
    assert typed(old['raw']) == typed(alias)
    # An observed final target is not proof that this competing occurrence made it.
    assert typed(old['final_value']) == typed(record['human_subject_research'])
    assert one(converter, 'humanSubjectResearch')['retention'] == 'retained'


def test_canonical_citation_supersedes_a_valid_property_value():
    prop = {'name': 'Citation', 'value': 'Legacy citation'}
    record, converter = convert(crate({'citation': 'Canonical citation', 'additionalProperty': [prop]}))
    assert record['citation'] == 'Canonical citation'
    row = one(converter, 'additionalProperty: Citation')
    assert row['retention'] == 'not_retained'
    assert row['raw'] == prop and row['final_value'] == 'Canonical citation'
    assert one(converter, 'citation')['retention'] == 'retained'


def test_equal_canonical_and_property_value_text_does_not_credit_both_sources():
    prop = {'name': 'Citation', 'value': 'Same literal'}
    value = crate({'citation': 'Same literal', 'additionalProperty': [prop]})
    before = typed(value)
    record, converter = convert(value)
    assert record['citation'] == 'Same literal'
    canonical = one(converter, 'citation')
    legacy = one(converter, 'additionalProperty: Citation')
    assert canonical['retention'] == 'retained'
    assert legacy['decision'] == 'legacy' and legacy['retention'] == 'not_retained'
    assert canonical['final_value'] == legacy['final_value'] == 'Same literal'
    assert legacy['source_pointer'] == '/@graph/1/additionalProperty/0'
    assert typed(legacy['raw']) == typed(prop)
    assert typed(value) == before


@pytest.mark.parametrize('value', [False, {'unsupported': 'shape'}])
def test_never_constructed_legacy_alias_is_not_a_final_validation_removal(value):
    record, converter = convert(crate({'d4d:humanSubject': value}))
    assert 'human_subject_research' not in record
    row = one(converter, 'd4d:humanSubject')
    assert row['decision'] == 'legacy' and row['retention'] == 'not_constructed'
    assert typed(row['raw']) == typed(value)
    assert row['final_value'] is None


def test_legacy_numeric_zero_keeps_original_generic_name_shape():
    record, converter = convert(crate({'d4d:humanSubject': 0}))
    assert record['human_subject_research'] == {'name': '0'}
    row = one(converter, 'd4d:humanSubject')
    assert row['decision'] == 'legacy' and row['retention'] == 'retained'
    assert type(row['raw']) is int and row['raw'] == 0
    assert row['final_value'] == {'name': '0'}
    evidence = converter.route_evidence
    assert evidence['final_dataset_binding'] == 'bound'
    assert evidence['final_dataset_binding_reason'] is None
    assert len(evidence['final_dataset_sha256']) == 64


def test_genuine_final_validator_removal_is_not_never_constructed(monkeypatch):
    converter = FairscapeToD4DConverter()
    settle = converter._settle
    def invalidate(record, origin, rivals):
        assert record['human_subject_research'] == {'involves_human_subjects': False}
        record['human_subject_research']['involves_human_subjects'] = 'not a boolean'
        return settle(record, origin, rivals)
    monkeypatch.setattr(converter, '_settle', invalidate)
    alias = {'involves_human_subjects': False}
    record, converter = convert(crate({'d4d:humanSubject': alias}), converter)
    assert 'human_subject_research' not in record
    row = one(converter, 'd4d:humanSubject')
    assert row['retention'] == 'not_retained' and row['final_value'] is None
    assert typed(row['raw']) == typed(alias)
    assert any('schema rejects' in reason for _, reason in converter.dropped)


def test_genuine_partial_validation_removal_preserves_surviving_alias_field(monkeypatch):
    converter = FairscapeToD4DConverter()
    settle = converter._settle
    def invalidate(record, origin, rivals):
        record['human_subject_research']['involves_human_subjects'] = 'not a boolean'
        return settle(record, origin, rivals)
    monkeypatch.setattr(converter, '_settle', invalidate)
    alias = {'description': 'Surviving narrative', 'involves_human_subjects': False}
    record, converter = convert(crate({'d4d:humanSubject': alias}), converter)
    assert record['human_subject_research'] == {'description': 'Surviving narrative'}
    row = one(converter, 'd4d:humanSubject')
    assert row['retention'] == 'partial'
    assert typed(row['raw']) == typed(alias)
    assert row['final_value'] == record['human_subject_research']


def test_property_value_final_schema_rejection_has_its_own_occurrence(monkeypatch):
    converter = FairscapeToD4DConverter()
    settle = converter._settle
    def invalidate(record, origin, rivals):
        assert record['citation'] == 'Constructed literal'
        record['citation'] = False
        return settle(record, origin, rivals)
    monkeypatch.setattr(converter, '_settle', invalidate)
    prop = {'name': 'Citation', 'value': 'Constructed literal'}
    record, converter = convert(crate({'additionalProperty': [prop]}), converter)
    assert 'citation' not in record
    row = one(converter, 'additionalProperty: Citation')
    assert row['raw'] == prop and row['retention'] == 'not_retained'
    assert row['final_value'] is None
    assert any('schema rejects' in reason for _, reason in converter.dropped)


def test_equal_property_values_are_separate_occurrences_not_two_retained_claims():
    prop = {'name': 'Human Subject', 'value': {'description': 'Same', 'involves_human_subjects': False}}
    props = [deepcopy(prop), deepcopy(prop)]
    record, converter = convert(crate({'additionalProperty': props}))
    assert record['human_subject_research'] == prop['value']
    found = rows(converter, 'additionalProperty: Human Subject')
    assert [r['source_pointer'] for r in found] == ['/@graph/1/additionalProperty/0', '/@graph/1/additionalProperty/1']
    assert [r['retention'] for r in found] == ['retained', 'not_retained']
    assert all(typed(r['raw']) == typed(prop) for r in found)
    assert any(word in found[1]['reason'].lower() for word in ('duplicate', 'redundant'))


def test_distinct_property_values_follow_existing_later_candidate_precedence():
    props = [{'name': 'Citation', 'value': 'First'}, {'name': 'Citation', 'value': 'Second'}]
    record, converter = convert(crate({'additionalProperty': props}))
    assert record['citation'] == 'Second'
    found = rows(converter, 'additionalProperty: Citation')
    assert [r['retention'] for r in found] == ['not_retained', 'retained']
    assert [r['source_pointer'] for r in found] == ['/@graph/1/additionalProperty/0', '/@graph/1/additionalProperty/1']
    assert [r['raw'] for r in found] == props


def test_boolean_alias_and_numeric_property_value_are_not_reported_as_equal_duplicates():
    alias = {'involves_human_subjects': False}
    prop = {'name': 'Human Subject', 'value': {'involves_human_subjects': 0}}
    record, converter = convert(crate({'d4d:humanSubject': alias, 'additionalProperty': [prop]}))
    assert record['human_subject_research']['involves_human_subjects'] is False
    assert one(converter, 'd4d:humanSubject')['retention'] == 'retained'
    row = one(converter, 'additionalProperty: Human Subject')
    assert type(row['raw']['value']['involves_human_subjects']) is int
    # The valid alias wins before the rival is shaped. Its hypothetical schema
    # validity is not observed and must not be invented by evidence tracking.
    assert row['retention'] == 'not_retained'
    assert any(word in row['reason'].lower() for word in ('unselected', 'superseded'))
    assert not any(word in row['reason'].lower() for word in ('duplicate', 'redundant'))


@pytest.mark.parametrize('name', ['Completeness', 'Data Governance Committee'])
def test_evidence_only_property_values_do_not_gain_a_nonexistent_target(name):
    prop = {'name': name, 'value': {'raw': [False, 0, None]}}
    record, converter = convert(crate({'additionalProperty': [prop]}))
    row = one(converter, 'additionalProperty: ' + name)
    assert row['target'] is None and row['retention'] == 'not_constructed'
    assert typed(row['raw']) == typed(prop) and row['final_value'] is None
    assert 'completeness' not in record and 'data_governance_committee' not in record


def test_legacy_outcome_accessor_is_detached_from_inputs_and_returned_values():
    prop = {'name': 'Human Subject', 'value': {'description': 'Literal'}}
    value = crate({'additionalProperty': [prop]})
    record, converter = convert(value)
    before = typed(converter.route_evidence)
    prop['value']['description'] = 'Changed input'
    record['human_subject_research']['description'] = 'Changed output'
    retrieved = converter.route_evidence
    retrieved['assertions'].clear()
    assert typed(converter.route_evidence) == before
    assert json.loads(json.dumps(converter.route_evidence))['status'] == 'complete'


def test_repeated_scalar_candidate_moves_to_the_existing_later_priority():
    same = ''.join(['Same', ' literal'])
    props = [{'name': 'Citation', 'value': same},
             {'name': 'Citation', 'value': 'Other literal'},
             {'name': 'Citation', 'value': same}]
    assert props[0]['value'] is props[2]['value']
    record, converter = convert(crate({'additionalProperty': props}))
    assert record['citation'] == same
    found = rows(converter, 'additionalProperty: Citation')
    assert [r['source_pointer'] for r in found] == [
        '/@graph/1/additionalProperty/0', '/@graph/1/additionalProperty/1',
        '/@graph/1/additionalProperty/2']
    assert [r['retention'] for r in found] == ['not_retained', 'not_retained', 'retained']
    assert typed([r['raw'] for r in found]) == typed(props)


def test_single_property_value_dictionary_keeps_its_actual_object_pointer():
    prop = {'name': 'Citation', 'value': 'Singleton assertion'}
    record, converter = convert(crate({'additionalProperty': prop}))
    assert record['citation'] == 'Singleton assertion'
    row = one(converter, 'additionalProperty: Citation')
    assert row['retention'] == 'retained'
    assert row['source_pointer'] == '/@graph/1/additionalProperty'
    assert typed(row['raw']) == typed(prop)


def test_wrong_typed_property_value_does_not_shift_later_occurrence_lineage():
    props = [{'@type': 'Person', 'name': 'Citation', 'value': 'Rejected wrong type'},
             {'@type': 'PropertyValue', 'name': 'Citation', 'value': 'Actual citation'}]
    record, converter = convert(crate({'additionalProperty': props}))
    assert record['citation'] == 'Actual citation'
    found = rows(converter, 'additionalProperty: Citation')
    assert [r['source_pointer'] for r in found] == [
        '/@graph/1/additionalProperty/0', '/@graph/1/additionalProperty/1']
    assert [r['retention'] for r in found] == ['not_constructed', 'retained']
    assert typed([r['raw'] for r in found]) == typed(props)
    assert any(source == 'additionalProperty[0]' and 'not a PropertyValue' in reason
               for source, reason in converter.dropped)


def test_unrelated_nonfinite_variable_preserves_output_with_unavailable_binding():
    infinity = float('inf')
    prop = {'name': 'Variables', 'value': [{'variable_name': 'x', 'minimum_value': infinity}]}
    value = crate({'citation': 'Covered finite literal', 'additionalProperty': [prop]})
    before = typed(value)
    record, converter = convert(value)
    assert record['variables'] == [{'variable_name': 'x', 'minimum_value': infinity}]
    assert type(record['variables'][0]['minimum_value']) is float
    assert record['citation'] == 'Covered finite literal'
    assert typed(value) == before
    assert not any('minimum_value' in source or source == 'additionalProperty[Variables]'
                   for source, _ in converter.dropped)
    evidence = converter.route_evidence
    assert evidence['status'] == 'complete' and evidence['error'] is None
    assert evidence['final_dataset_sha256'] is None
    assert evidence['final_dataset_binding'] == 'unavailable'
    assert type(evidence['final_dataset_binding_reason']) is str
    assert evidence['final_dataset_binding_reason']
    assert one(converter, 'citation')['retention'] == 'retained'
    assert not rows(converter, 'additionalProperty: Variables')
    encoded = json.dumps(evidence, ensure_ascii=True, allow_nan=False)
    assert typed(json.loads(encoded)) == typed(evidence)
    forward = D4DToFairscapeConverter()
    with pytest.raises(ValueError, match='source_evidence'):
        forward.convert(record, source_evidence=evidence)
    assert forward.route_evidence['status'] == 'failed'
    assert record['variables'][0]['minimum_value'] == infinity
