"""Part A of #4046: whole root assertions and detached conversion evidence.

These tests exercise the real converter and final Dataset validator. They do
not establish the later canonical/carrier routes or scientific equivalence.
"""
import contextlib
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.fairscape_integration.fairscape_to_d4d import FairscapeToD4DConverter


ABSENT = object()
KEYS = (
    'rai:dataManipulationProtocol', 'citation', 'funder', 'humanSubjects',
    'humanSubjectResearch', 'dataGovernanceCommittee', 'completeness',
)
TARGETS = {
    'rai:dataManipulationProtocol': 'cleaning_strategies',
    'citation': 'citation', 'funder': 'funders',
    'humanSubjects': 'human_subject_research',
    'humanSubjectResearch': 'human_subject_research',
    'dataGovernanceCommittee': 'data_governance', 'completeness': None,
}


def typed(value):
    if type(value) is dict:
        return (dict, tuple((key, typed(child)) for key, child in value.items()))
    if type(value) is list:
        return (list, tuple(typed(child) for child in value))
    return (type(value), value.hex() if type(value) is float else value)


def crate(properties=None, *, nodes=()):
    root = {'@id': './', '@type': ['Dataset', 'https://w3id.org/EVI#ROCrate'],
            'name': 'Root assertions', 'description': 'Synthetic root',
            'keywords': [], 'version': '1.0', 'author': 'Synthetic author',
            'license': 'https://example.org/license', 'hasPart': []}
    root.update(properties or {})
    return {'@context': {'@vocab': 'https://schema.org/'}, '@graph': [
        {'@id': 'ro-crate-metadata.json', '@type': 'CreativeWork',
         'about': {'@id': './'}, 'conformsTo': {'@id': 'https://w3id.org/ro/crate/1.2'}},
        root, *deepcopy(nodes)]}


def convert(value, converter=None):
    converter = converter or FairscapeToD4DConverter()
    with contextlib.redirect_stdout(io.StringIO()):
        record = converter.convert(value)
    return record, converter


def direct(converter, key):
    rows = [r for r in converter.route_evidence['assertions'] if r['source'] == key]
    assert len(rows) == 1
    return rows[0]


def assert_complete(converter):
    evidence = converter.route_evidence
    assert evidence['direction'] == 'fairscape_to_d4d'
    assert evidence['status'] == 'complete' and evidence['error'] is None
    assert all(row['retention'] != 'unknown_failed' for row in evidence['assertions'])
    return evidence


def test_all_seven_root_assertions_reach_their_declared_homes():
    values = {
        'rai:dataManipulationProtocol': '  Whole cleaning narrative; no inferred steps.\nα  ',
        'citation': '  First author; second author.\nCitation stays whole.  ',
        'funder': 'One funder, not two; no grant inferred',
        'humanSubjects': 'No', 'humanSubjectResearch': 'No',
        'dataGovernanceCommittee': 'Dr Example answers requests; this is a narrative.',
        'completeness': {'stated': [False, 0, None, 'unscored']},
    }
    value = crate(values)
    before = typed(value)
    record, converter = convert(value)
    assert record['cleaning_strategies'] == [{'cleaning_details': values['rai:dataManipulationProtocol']}]
    assert record['citation'] == values['citation']
    assert record['funders'] == [{'grantor': values['funder']}]
    assert record['data_governance'] == {'description': values['dataGovernanceCommittee']}
    assert record['human_subject_research'] == {
        'description': 'Source humanSubjectResearch: No\nSource humanSubjects: No',
        'involves_human_subjects': False,
    }
    assert 'completeness' not in record
    assert typed(value) == before
    evidence = assert_complete(converter)
    assert evidence['input']['kind'] == 'dict'
    assert evidence['input']['source_sha256'] is None
    for key in KEYS:
        row = direct(converter, key)
        assert typed(row['raw']) == typed(values[key])
        assert row['source_pointer'] == '/@graph/1/' + key
        assert row['target'] == TARGETS[key]
        assert row['presence'] == 'present'
        if key == 'completeness':
            assert row['decision'] == 'deferred' and row['retention'] == 'not_constructed'
        else:
            assert row['decision'] == 'constructed' and row['retention'] == 'retained'
            assert typed(row['final_value']) == typed(record[TARGETS[key]])


@pytest.mark.parametrize('key', KEYS)
def test_root_only_selection_and_original_graph_position(key):
    member = {'@id': '#member', '@type': 'Dataset', 'name': 'Member', key: 'MEMBER MUST NOT LEAK'}
    value = crate({key: 'Root text'}, nodes=[member])
    records = []
    for graph in (value['@graph'], list(reversed(value['@graph']))):
        supplied = {'@context': value['@context'], '@graph': deepcopy(graph)}
        before = typed(supplied)
        record, converter = convert(supplied)
        records.append(record)
        index = next(i for i, node in enumerate(graph) if node.get('@id') == './')
        row = direct(converter, key)
        assert row['source_pointer'] == '/@graph/' + str(index) + '/' + key
        assert row['raw'] == 'Root text'
        assert 'MEMBER MUST NOT LEAK' not in json.dumps(converter.route_evidence)
        assert 'MEMBER MUST NOT LEAK' not in json.dumps(record)
        assert typed(supplied) == before
    assert typed(records[0]) == typed(records[1])
    record, converter = convert(crate(nodes=[member]))
    assert direct(converter, key)['presence'] == 'missing'
    assert direct(converter, key)['decision'] == 'missing'
    assert 'MEMBER MUST NOT LEAK' not in json.dumps(record)


@pytest.mark.parametrize('key', KEYS)
@pytest.mark.parametrize('value', [ABSENT, None, False, 0, [], {}],
                         ids=['missing', 'null', 'false', 'zero', 'empty-list', 'empty-object'])
def test_presence_and_raw_type_survive_all_falsy_forms(key, value):
    properties = {} if value is ABSENT else {key: value}
    supplied = crate(properties)
    before = typed(supplied)
    _, converter = convert(supplied)
    row = direct(converter, key)
    expected_presence = 'missing' if value is ABSENT else 'null' if value is None else 'present'
    assert row['presence'] == expected_presence
    assert typed(row['raw']) == typed(None if value is ABSENT else value)
    assert row['source_pointer'] == '/@graph/1/' + key
    assert typed(supplied) == before
    assert_complete(converter)


def test_cleaning_keeps_order_duplicates_empty_strings_and_unparsed_text():
    values = ['B; α\nwhole', '', 'A', 'B; α\nwhole']
    record, converter = convert(crate({'rai:dataManipulationProtocol': values}))
    assert record['cleaning_strategies'] == [{'cleaning_details': value} for value in values]
    row = direct(converter, 'rai:dataManipulationProtocol')
    assert typed(row['raw']) == typed(values)
    assert row['retention'] == 'retained'
    assert all(set(obj) == {'cleaning_details'} for obj in record['cleaning_strategies'])


def test_mixed_cleaning_units_are_retained_without_recursive_stringification():
    values = ['whole', False, 0, None, ['nested'], {'description': 'not a protocol'}, 'whole']
    record, converter = convert(crate({'rai:dataManipulationProtocol': values}))
    assert record['cleaning_strategies'] == [{'cleaning_details': 'whole'}, {'cleaning_details': 'whole'}]
    row = direct(converter, 'rai:dataManipulationProtocol')
    assert typed(row['raw']) == typed(values)
    assert row['retention'] == 'partial'
    assert converter.dropped


@pytest.mark.parametrize('value', [['one'], ['one', 'two'], {'@id': '#citation'}, False, 0])
def test_citation_requires_one_literal_and_never_first_picks_or_joins(value):
    record, converter = convert(crate({'citation': value}))
    assert 'citation' not in record
    row = direct(converter, 'citation')
    assert typed(row['raw']) == typed(value)
    assert row['decision'] == 'unplaced' and row['retention'] == 'not_constructed'


def test_funder_names_and_sole_ids_preserve_multiplicity_without_minted_grants():
    values = ['A, B', {'@id': 'urn:funder:explicit'}, 'A, B', '']
    record, converter = convert(crate({'funder': values}))
    assert record['funders'] == [{'grantor': 'A, B'}, {'grantor': 'urn:funder:explicit'},
                                 {'grantor': 'A, B'}, {'grantor': ''}]
    assert all(set(item) == {'grantor'} for item in record['funders'])
    assert typed(direct(converter, 'funder')['raw']) == typed(values)


@pytest.mark.parametrize('value', [{'@id': '#org', 'name': 'Rich'}, {'name': 'Name only'},
                                  {'@id': ''}, {'@id': False}, ['nested']])
def test_unsupported_funder_shapes_do_not_infer_a_name_or_reference(value):
    record, converter = convert(crate({'funder': [value]}))
    assert 'funders' not in record
    assert typed(direct(converter, 'funder')['raw']) == typed([value])
    assert direct(converter, 'funder')['retention'] == 'not_constructed'


@pytest.mark.parametrize('value,expected', [(False, False), (True, True), ('No', False),
    (' yes ', True), (['No', 'no'], False), (0, ABSENT), (1, ABSENT),
    ('false', ABSENT), ('No participants were enrolled', ABSENT), (['Yes', 'No'], ABSENT)])
def test_human_research_normalizes_only_explicit_whole_tokens(value, expected):
    record, converter = convert(crate({'humanSubjectResearch': value}))
    human = record['human_subject_research']
    if expected is ABSENT:
        assert 'involves_human_subjects' not in human
    else:
        assert human['involves_human_subjects'] is expected
    assert human['description'].startswith('Source humanSubjectResearch: ')
    assert not any(k in human for k in ('irb_approval', 'exemption', 'ethics_review_board'))
    assert typed(direct(converter, 'humanSubjectResearch')['raw']) == typed(value)


def test_human_subjects_is_separate_and_opposition_suppresses_research_boolean():
    record, converter = convert(crate({'humanSubjects': True}))
    assert record['human_subject_research'] == {'description': 'Source humanSubjects: true'}
    record, converter = convert(crate({'humanSubjects': False, 'humanSubjectResearch': 'Yes'}))
    assert record['human_subject_research'] == {
        'description': 'Source humanSubjectResearch: Yes\nSource humanSubjects: false'}
    assert direct(converter, 'humanSubjects')['raw'] is False
    assert direct(converter, 'humanSubjectResearch')['raw'] == 'Yes'


def test_supplemental_human_assertions_and_exact_referenced_irb_are_visible():
    board = {'@id': '#board', '@type': 'Organization', 'name': 'Stated board',
             'extra': {'values': [False, 0, None, 'whole']}}
    properties = {'humanSubjectResearch': 'Yes', 'humanSubjectExemption': 'source narrative',
                  'irb': {'@id': '#board'}, 'irbProtocolId': 'P-0'}
    record, converter = convert(crate(properties, nodes=[board]))
    human = record['human_subject_research']
    assert human['ethics_review_board'] == 'Stated board'
    assert 'irb_approval' not in human
    assert 'P-0' in human['description'] and 'source narrative' in human['description']
    rows = converter.route_evidence['assertions']
    for key in ('humanSubjectExemption', 'irb', 'irbProtocolId'):
        assert any(r['source'] == key and typed(r['raw']) == typed(properties[key]) for r in rows)
    matches = [r for r in rows if r['source'] == 'irb.referenced_entity']
    assert len(matches) == 1 and matches[0]['source_pointer'] == '/@graph/2'
    assert typed(matches[0]['raw']) == typed(board)


def test_duplicate_irb_identities_keep_all_consulted_nodes_without_board_inference():
    nodes = [{'@id': '#board', '@type': 'Organization', 'name': 'First'},
             {'@id': '#board', '@type': 'Organization', 'name': 'Second', 'extra': [False, 0]}]
    record, converter = convert(crate({'humanSubjectResearch': 'Yes', 'irb': {'@id': '#board'}}, nodes=nodes))
    assert 'ethics_review_board' not in record['human_subject_research']
    rows = [r for r in converter.route_evidence['assertions'] if r['source'] == 'irb.referenced_entity']
    assert [r['source_pointer'] for r in rows] == ['/@graph/2', '/@graph/3']
    assert typed([r['raw'] for r in rows]) == typed(nodes)


def test_canonical_human_assertion_precedes_structured_alias_without_hiding_it():
    alias = {'description': 'Independent alias assertion', 'involves_human_subjects': True}
    record, converter = convert(crate({'humanSubjectResearch': 'No', 'd4d:humanSubject': alias}))
    assert record['human_subject_research']['involves_human_subjects'] is False
    assert 'Source humanSubjectResearch: No' in record['human_subject_research']['description']
    rows = [r for r in converter.route_evidence['assertions'] if r['source'] == 'd4d:humanSubject']
    assert len(rows) == 1 and typed(rows[0]['raw']) == typed(alias)
    assert rows[0]['source_pointer'] == '/@graph/1/d4d:humanSubject'
    assert converter.dropped


def test_governance_and_completeness_property_values_are_independently_preserved():
    pv = [{'name': 'Data Governance Committee', 'value': 'PropertyValue narrative'},
          {'name': 'Completeness', 'value': [False, 0, None, 'unknown']}]
    record, converter = convert(crate({'dataGovernanceCommittee': 'Canonical narrative',
        'completeness': {'raw': 'unscored'}, 'additionalProperty': pv}))
    assert record['data_governance'] == {'description': 'Canonical narrative'}
    assert 'data_governance_committee' not in record and 'completeness' not in record
    rows = converter.route_evidence['assertions']
    for i, item in enumerate(pv):
        pointer = '/@graph/1/additionalProperty/' + str(i)
        matched = [r for r in rows if r['source_pointer'] == pointer]
        assert len(matched) == 1
        assert matched[0]['source'] == 'additionalProperty: ' + item['name']
        assert typed(matched[0]['raw']) == typed(item)
    assert typed(direct(converter, 'completeness')['raw']) == typed({'raw': 'unscored'})


def test_path_hash_binds_the_single_acquisition_not_a_later_reread(tmp_path, monkeypatch):
    path = tmp_path / 'crate.json'
    first = (json.dumps(crate({'citation': 'First α', 'completeness': False}),
                        ensure_ascii=False, indent=3) + '\n').encode('utf-8')
    later = json.dumps(crate({'citation': 'Later contents'})).encode('utf-8')
    path.write_bytes(first)
    original = Path.read_bytes
    calls = []
    def read_once(self):
        raw = original(self)
        if self == path:
            calls.append(raw)
            self.write_bytes(later)
        return raw
    monkeypatch.setattr(Path, 'read_bytes', read_once)
    record, converter = convert(path)
    assert calls == [first]
    assert record['citation'] == 'First α'
    meta = converter.route_evidence['input']
    assert meta['kind'] == 'path' and meta['source_path'] == str(path)
    assert meta['source_sha256'] == hashlib.sha256(first).hexdigest()
    assert meta['source_bytes'] == len(first)
    assert original(path) == later
    assert direct(converter, 'completeness')['raw'] is False


@pytest.mark.parametrize('supplied', [False, True])
def test_genuine_model_supplied_null_is_distinct_from_default_null(supplied):
    from fairscape_models.rocrate import ROCrateMetadataElem, ROCrateMetadataFileElem, ROCrateV1_2
    value = crate({'citation': None} if supplied else {})
    root = ROCrateMetadataElem(**deepcopy(value['@graph'][1]))
    descriptor = ROCrateMetadataFileElem(**deepcopy(value['@graph'][0]))
    model = ROCrateV1_2(**{'@context': value['@context'], '@graph': [descriptor, root]})
    before = typed(model.model_dump(mode='json', by_alias=True, exclude_none=False))
    fields = set(root.model_fields_set)
    _, converter = convert(model)
    row = direct(converter, 'citation')
    assert row['presence'] == ('null' if supplied else 'missing')
    assert row['raw'] is None
    meta = converter.route_evidence['input']
    assert meta['kind'] == 'model' and meta['model_projection'] == 'by_alias_exclude_unset'
    assert meta['source_sha256'] is None and meta['source_bytes'] is None
    assert typed(model.model_dump(mode='json', by_alias=True, exclude_none=False)) == before
    assert set(root.model_fields_set) == fields


def test_evidence_is_detached_from_input_accessor_and_returned_record():
    value = crate({'rai:dataManipulationProtocol': ['A', 'A'], 'completeness': {'list': [False, 0]}})
    record, converter = convert(value)
    saved = typed(converter.route_evidence)
    returned = converter.route_evidence
    returned['assertions'].clear()
    value['@graph'][1]['completeness']['list'].append('changed')
    record['cleaning_strategies'][0]['cleaning_details'] = 'changed output'
    assert typed(converter.route_evidence) == saved


def test_failure_and_reuse_never_publish_previous_assertion_rows():
    converter = FairscapeToD4DConverter()
    convert(crate({'citation': 'PREVIOUS'}), converter)
    with pytest.raises(ValueError, match='root'):
        convert({'@graph': []}, converter)
    failed = converter.route_evidence
    assert failed['status'] == 'failed' and failed['error']
    assert failed['assertions'] == []
    assert 'PREVIOUS' not in json.dumps(failed)
    convert(crate({'funder': 'NEXT'}), converter)
    assert_complete(converter)
    assert direct(converter, 'citation')['presence'] == 'missing'
    assert direct(converter, 'funder')['raw'] == 'NEXT'


def test_failure_after_construction_preserves_this_attempt_and_error_identity(monkeypatch):
    converter = FairscapeToD4DConverter()
    error = RuntimeError('controlled final-validator boundary failure')
    def failed_settle(*args, **kwargs):
        raise error
    monkeypatch.setattr(converter, '_settle', failed_settle)
    with pytest.raises(RuntimeError) as caught:
        convert(crate({'citation': 'This attempt'}), converter)
    assert caught.value is error
    evidence = converter.route_evidence
    assert evidence['status'] == 'failed'
    row = direct(converter, 'citation')
    assert row['raw'] == 'This attempt' and row['retention'] == 'unknown_failed'


def test_actual_settle_removal_is_not_reported_as_retained(monkeypatch):
    converter = FairscapeToD4DConverter()
    original = converter._settle
    def invalid_citation(record, origin, rivals):
        assert record['citation'] == 'Constructed first'
        record['citation'] = False
        return original(record, origin, rivals)
    monkeypatch.setattr(converter, '_settle', invalid_citation)
    record, converter = convert(crate({'citation': 'Constructed first'}), converter)
    assert 'citation' not in record
    row = direct(converter, 'citation')
    assert row['decision'] == 'constructed' and row['retention'] == 'not_retained'
    assert row['final_value'] is None and row['raw'] == 'Constructed first'
    assert any('citation' in path and 'schema rejects' in reason for path, reason in converter.dropped)


def test_actual_settle_partial_removal_keeps_the_other_occurrence(monkeypatch):
    converter = FairscapeToD4DConverter()
    original = converter._settle
    def invalid_first(record, origin, rivals):
        record['cleaning_strategies'][0]['cleaning_details'] = False
        return original(record, origin, rivals)
    monkeypatch.setattr(converter, '_settle', invalid_first)
    record, converter = convert(crate({'rai:dataManipulationProtocol': ['A', 'B']}), converter)
    assert record['cleaning_strategies'] == [{'cleaning_details': 'B'}]
    row = direct(converter, 'rai:dataManipulationProtocol')
    assert row['decision'] == 'constructed' and row['retention'] == 'partial'
    assert row['raw'] == ['A', 'B']
    assert typed(row['final_value']) == typed(record['cleaning_strategies'])


def test_escaped_surrogate_and_normal_unicode_remain_exact_json_evidence():
    values = ['normal α\nsecond line', '\ud800', 'normal α\nsecond line']
    record, converter = convert(crate({'rai:dataManipulationProtocol': values,
                                       'completeness': {'raw': '\ud800'}}))
    assert [v['cleaning_details'] for v in record['cleaning_strategies']] == values
    raw = json.dumps(converter.route_evidence, ensure_ascii=True, allow_nan=False).encode('utf-8')
    restored = json.loads(raw)
    assert typed(restored) == typed(converter.route_evidence)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), object()])
def test_non_json_consulted_assertions_fail_without_stale_evidence(value):
    converter = FairscapeToD4DConverter()
    convert(crate({'citation': 'PREVIOUS'}), converter)
    with pytest.raises(ValueError, match='evidence|JSON|finite'):
        convert(crate({'completeness': value}), converter)
    evidence = converter.route_evidence
    assert evidence['status'] == 'failed'
    assert 'PREVIOUS' not in json.dumps(evidence)


@pytest.mark.parametrize('location', ['root', 'unreferenced-member'])
def test_unrelated_python_value_does_not_expand_the_evidence_validation_scope(location):
    opaque = object()
    value = crate({'citation': 'Covered literal'})
    if location == 'root':
        owner = value['@graph'][1]
    else:
        owner = {'@id': '#unreferenced', '@type': 'Dataset', 'name': 'Unreferenced'}
        value['@graph'].append(owner)
    owner['unrelatedOpaqueValue'] = opaque
    graph = value['@graph']
    record, converter = convert(value)
    assert record['citation'] == 'Covered literal'
    assert value['@graph'] is graph and owner['unrelatedOpaqueValue'] is opaque
    assert owner in value['@graph']
    evidence = assert_complete(converter)
    assert 'unrelatedOpaqueValue' not in json.dumps(evidence, allow_nan=False)
    assert direct(converter, 'citation')['raw'] == 'Covered literal'
