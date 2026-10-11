"""Recover each original assertion through the real marked builders and mergers."""
from copy import deepcopy
import csv
from hashlib import sha256
import json

import pytest

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema import legacy_route_dispositions as policy
from .test_legacy_root_identity import implementation, crate


ABSENT = object()
TEXT = '  Preserve "quoted" prose; Café.\nSecond line, unchanged.\n'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
DIRECT = 'Direct mapping? Yes =1; No = 0'
FIELDS = [
    ('tasks', 'rai:dataUseCases', 'tasks', 'response'),
    ('discouraged_uses', 'prohibitedUses', 'discouraged_uses', 'discouragement_details'),
    ('future_use_impacts', 'rai:dataSocialImpact', 'future_use_impacts', 'impact_details'),
    ('machine_annotation_analyses', 'rai:machineAnnotationTools', 'machine_annotation_tools', 'tool_descriptions'),
    ('external_resource', 'associatedPublication', 'external_resources', 'external_resources'),
]
DEFERRED = [
    ('encoding', 'evi:formats'), ('existing_uses', 'rai:dataUseCases'),
    ('other_tasks', 'rai:dataUseCases'), ('data_protection_impacts', 'rai:dataSocialImpact'),
    ('confidential_elements', 'rai:personalSensitiveInformation'),
    ('ip_restrictions', 'license,conditionsOfAccess'),
    ('extension_mechanism', 'license,conditionsOfAccess'), ('version_access', 'version'),
]
ALL_ROUTES = [(field, prop) for field, prop, _, _ in FIELDS] + [('bytes', 'contentSize')] + DEFERRED


def assert_json(actual, expected):
    assert json.dumps(actual, sort_keys=True, ensure_ascii=True) == json.dumps(
        expected, sort_keys=True, ensure_ascii=True)


def table(tmp_path, rows, *, marked=True, name='routes.tsv'):
    path = tmp_path / name
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['D4D Property', 'Type', 'FAIRSCAPE RO-Crate Property', 'Func', COVERED, DIRECT])
        writer.writerow(['id', 'URI', 'identifier,@id', 'root_identifier_v1', '1', '0'])
        writer.writerow(['title', 'str', 'name', '', '1', '1'])
        for field, predicates in rows:
            writer.writerow([field, '', predicates, policy.MARKER if marked else '', '1', '1'])
    return path


def source(path, properties, *, reverse=False):
    root = {'@id': './', 'identifier': 'doi:10.1234/Disposition', 'name': 'Selected root'}
    root.update(deepcopy(properties))
    crate(path, root, reverse=reverse)
    data = json.loads(path.read_bytes())
    member = next(item for item in data['@graph'] if item.get('@id') == 'member')
    member.update({predicate: 'MEMBER ONLY' for _, predicates in ALL_ROUTES
                   for predicate in predicates.split(',')})
    member['evi:totalContentSizeBytes'] = 999
    path.write_text(json.dumps(data, ensure_ascii=True), encoding='utf-8')
    return path


def build(implementation, path, mapping_path):
    mapping = implementation['loader'].MappingLoader(str(mapping_path))
    parser = implementation['parser'].ROCrateParser(str(path))
    builder = implementation['builder'].D4DBuilder(mapping)
    record = builder.build_dataset(parser)
    evidence = builder.get_route_dispositions()
    policy.validate_evidence(evidence, record, mapping)
    return record, evidence, builder, parser, mapping


def pointer(document, path):
    value = document
    for part in path.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if type(value) is list else value[part]
    return value


def assert_recoverable(evidence, expected_paths, expected_fields):
    """Bind snapshots to actual inputs and the independently stated route roster."""
    assert len(evidence['sources']) == len(expected_paths)
    declarations = dict(ALL_ROUTES)
    for occurrence, path in zip(evidence['sources'], expected_paths):
        snapshot = occurrence['snapshot']
        raw = snapshot['json_text'].encode('utf-8')
        assert snapshot['kind'] == 'original_file' and raw == path.read_bytes()
        assert snapshot['serialization'] == {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
        assert snapshot['original_file'] == {
            'path': str(path.resolve()), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
        parsed = json.loads(raw)
        assert pointer(parsed, snapshot['root_pointer'])['@id'] == './'
        assert set(occurrence['routes']) == set(expected_fields)
        for field in expected_fields:
            assertions = occurrence['routes'][field]
            expected_properties = declarations[field].split(',')
            expected_supplements = [False] * len(expected_properties)
            if field == 'bytes':
                expected_properties.append('evi:totalContentSizeBytes')
                expected_supplements.append(True)
            assert [a['property'] for a in assertions] == expected_properties
            assert [a['supplemental'] for a in assertions] == expected_supplements
            for assertion in assertions:
                if assertion['present']:
                    assert_json(pointer(parsed, assertion['pointer']), assertion['raw'])
                else:
                    assert 'raw' not in assertion
                for unit in assertion['units']:
                    assert_json(pointer(parsed, unit['pointer']), unit['raw'])


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('field,predicate,target,child', FIELDS)
def test_whole_narratives_have_only_the_explicit_typed_child(
        implementation, tmp_path, reverse, field, predicate, target, child):
    path = source(tmp_path / 'source.json', {predicate: TEXT}, reverse=reverse)
    mapping_path = table(tmp_path, [(field, predicate)])
    original = {p: p.read_bytes() for p in (path, mapping_path)}
    record, evidence, _, _, _ = build(implementation, path, mapping_path)
    value = [TEXT] if field == 'external_resource' else TEXT
    assert_json(record, {'id': 'doi:10.1234/Disposition', 'title': 'Selected root',
                         target: [{child: value}]})
    publication.prepare_dataset(record)
    assert_recoverable(evidence, [path], [field])
    assertion = evidence['sources'][0]['routes'][field][0]
    assert assertion['selected_within_source'] and assertion['selected_for_merge']
    assert_json(pointer(record, assertion['units'][0]['output_pointer']), value)
    assert {p: p.read_bytes() for p in original} == original


@pytest.mark.parametrize('field,predicate,target,child', FIELDS)
def test_mixed_units_preserve_every_value_without_stringifying_or_deduplicating(
        implementation, tmp_path, field, predicate, target, child):
    raw = [TEXT, 'same', 'same', '', False, 0, None,
           {'a/b~c': ['\ud800', '\U0001f600']}, ['nested', 'nested']]
    path = source(tmp_path / 'source.json', {predicate: raw})
    record, evidence, builder, parser, mapping = build(
        implementation, path, table(tmp_path, [(field, predicate)]))
    expected = [{child: [s] if field == 'external_resource' else s} for s in raw[:4]]
    assert_json(record[target], expected)
    publication.prepare_dataset(record)
    assertion = evidence['sources'][0]['routes'][field][0]
    assert_json(assertion['raw'], raw)
    assert_json([unit['raw'] for unit in assertion['units']], raw)
    assert [unit['disposition'] for unit in assertion['units']] == ['constructed'] * 4 + ['declined'] * 5
    assert_recoverable(evidence, [path], [field])
    wire = policy.encoded(evidence)
    assert wire.isascii() and b'\\ud800' in wire
    assert_json(json.loads(wire), evidence)
    evidence['sources'][0]['routes'][field][0]['raw'].append('tampered')
    assert_json(builder.get_route_dispositions()['sources'][0]['routes'][field][0]['raw'], raw)
    assert_json(parser.require_root_dataset()[predicate], raw)
    with pytest.raises(ValueError, match='evidence'):
        policy.validate_evidence(evidence, record, mapping)


@pytest.mark.parametrize('field,predicates', DEFERRED)
@pytest.mark.parametrize('value', [False, 0, '', [], [TEXT, TEXT, None, {'a/b~c': '\ud800'}]])
def test_declined_routes_remain_recoverable_without_claiming_absence(
        implementation, tmp_path, field, predicates, value):
    props = {p: deepcopy(value) for p in predicates.split(',')}
    record, evidence, _, _, _ = build(
        implementation, source(tmp_path / 'source.json', props), table(tmp_path, [(field, predicates)]))
    assert record == {'id': 'doi:10.1234/Disposition', 'title': 'Selected root'}
    publication.prepare_dataset(record)
    assertions = evidence['sources'][0]['routes'][field]
    assert assertions[0]['disposition'] == 'declined'
    for assertion in assertions:
        assert assertion['present']
        assert_json(assertion['raw'], value)
    assert_recoverable(evidence, [tmp_path / 'source.json'], [field])


@pytest.mark.parametrize('field', ['ip_restrictions', 'extension_mechanism'])
@pytest.mark.parametrize('first,selected', [(None, 1), (False, 0), (0, 0), ('', 0), ([], 0)])
def test_conflicting_property_alternatives_remain_separate_in_evidence(
        implementation, tmp_path, field, first, selected):
    other = ['Distinct access assertion', {'a/b~c': False}]
    record, evidence, _, _, _ = build(
        implementation, source(tmp_path / 'source.json', {'license': first, 'conditionsOfAccess': other}),
        table(tmp_path, [(field, 'license,conditionsOfAccess')]))
    assert field not in record
    assertions = evidence['sources'][0]['routes'][field]
    assert_json([a['raw'] for a in assertions], [first, other])
    assert [a['selected_within_source'] for a in assertions] == [selected == 0, selected == 1]
    assert assertions[selected]['disposition'] == 'declined'
    assert_recoverable(evidence, [tmp_path / 'source.json'], [field])


@pytest.mark.parametrize('field,predicates', ALL_ROUTES)
@pytest.mark.parametrize('value', [ABSENT, None])
def test_absent_or_null_root_never_promotes_member_assertions(
        implementation, tmp_path, field, predicates, value):
    props = {} if value is ABSENT else {p: None for p in predicates.split(',')}
    record, evidence, _, _, _ = build(
        implementation, source(tmp_path / 'source.json', props, reverse=True),
        table(tmp_path, [(field, predicates)]))
    assert record == {'id': 'doi:10.1234/Disposition', 'title': 'Selected root'}
    assert_recoverable(evidence, [tmp_path / 'source.json'], [field])
    for assertion in evidence['sources'][0]['routes'][field]:
        if assertion['supplemental'] or value is ABSENT:
            assert not assertion['present'] and assertion['disposition'] == 'missing'
        else:
            assert assertion['present'] and assertion['raw'] is None
            assert assertion['disposition'] == 'null'


@pytest.mark.parametrize('exact,expected', [
    (ABSENT, ABSENT), (None, ABSENT), (False, ABSENT), (True, ABSENT),
    (0, 0), (17, 17), (-1, ABSENT), (17.0, ABSENT), ('17', ABSENT),
    ([], ABSENT), ({'value': 17}, ABSENT),
])
def test_size_uses_only_an_explicit_nonnegative_integer_supplement(
        implementation, tmp_path, exact, expected):
    props = {'contentSize': '2.3 TB'}
    if exact is not ABSENT:
        props['evi:totalContentSizeBytes'] = exact
    record, evidence, _, _, _ = build(
        implementation, source(tmp_path / 'source.json', props), table(tmp_path, [('bytes', 'contentSize')]))
    assert 'bytes' not in record
    if expected is ABSENT:
        assert 'total_size_bytes' not in record
    else:
        assert type(record['total_size_bytes']) is int and record['total_size_bytes'] == expected
    publication.prepare_dataset(record)
    assertions = evidence['sources'][0]['routes']['bytes']
    assert assertions[0]['raw'] == '2.3 TB' and assertions[0]['disposition'] == 'declined'
    assert assertions[1]['supplemental'] and assertions[1]['property'] == 'evi:totalContentSizeBytes'
    if exact is not ABSENT:
        assert_json(assertions[1]['raw'], exact)
    assert_recoverable(evidence, [tmp_path / 'source.json'], ['bytes'])


@pytest.mark.parametrize('rounded', [ABSENT, None])
@pytest.mark.parametrize('exact', [0, 17])
def test_explicit_size_does_not_require_a_rounded_size(implementation, tmp_path, rounded, exact):
    props = {'evi:totalContentSizeBytes': exact}
    if rounded is not ABSENT:
        props['contentSize'] = rounded
    path = source(tmp_path / 'source.json', props)
    record, evidence, _, _, _ = build(implementation, path, table(tmp_path, [('bytes', 'contentSize')]))
    assert type(record['total_size_bytes']) is int and record['total_size_bytes'] == exact
    assert 'bytes' not in record
    publication.prepare_dataset(record)
    assert_recoverable(evidence, [path], ['bytes'])
    ordinary, supplement = evidence['sources'][0]['routes']['bytes']
    assert ordinary['disposition'] == ('missing' if rounded is ABSENT else 'null')
    assert supplement['selected_for_merge'] and supplement['disposition'] == 'constructed'
    assert_json(supplement['raw'], exact)


@pytest.mark.parametrize('field,predicate,target,child', [FIELDS[0], FIELDS[2], FIELDS[4]])
def test_concat_uses_primary_then_processed_order_and_distinct_occurrences(
        implementation, tmp_path, field, predicate, target, child):
    mapping_path = table(tmp_path, [(field, predicate)])
    mapping = implementation['loader'].MappingLoader(str(mapping_path))
    paths = [source(tmp_path / f'{i}.json', {predicate: value}, reverse=i == 1)
             for i, value in enumerate(['secondary', ['primary', 'primary'], 'last'])]
    parsers = [implementation['parser'].ROCrateParser(str(p)) for p in paths]
    merger = implementation['merger'].ROCrateMerger(mapping)
    record = merger.merge_rocrates(parsers, primary_index=1, source_indices=[8, 3, 5],
                                  source_names=['same display name'] * 3)
    expected = ['primary', 'primary', 'secondary', 'last']
    assert_json(record[target], [{child: [s] if field == 'external_resource' else s} for s in expected])
    evidence = merger.get_route_dispositions()
    assert evidence['processed_occurrences'] == ['input:8', 'input:3', 'input:5']
    assert evidence['merge_order'] == ['input:3', 'input:8', 'input:5']
    assert evidence['primary_occurrence'] == 'input:3'
    assert [s['processed_index'] for s in evidence['sources']] == [0, 1, 2]
    assert [s['original_index'] for s in evidence['sources']] == [8, 3, 5]
    for occurrence in evidence['sources']:
        for unit in occurrence['routes'][field][0]['units']:
            assert_json(pointer(record, unit['output_pointer']),
                        [unit['raw']] if field == 'external_resource' else unit['raw'])
    policy.validate_evidence(evidence, record, mapping)
    publication.prepare_dataset(record)
    assert_recoverable(evidence, paths, [field])


@pytest.mark.parametrize('field,predicate,target,child', [FIELDS[1], FIELDS[3]])
@pytest.mark.parametrize('primary,expected', [(False, ABSENT), (0, ABSENT), ([], []), ('', '')])
def test_primary_selection_precedes_construction_and_cannot_promote_secondary(
        implementation, tmp_path, field, predicate, target, child, primary, expected):
    mapping = implementation['loader'].MappingLoader(str(table(tmp_path, [(field, predicate)])))
    parsers = [implementation['parser'].ROCrateParser(str(source(
        tmp_path / f'{i}.json', {predicate: value})))
        for i, value in enumerate(['first secondary', primary, 'last secondary'])]
    merger = implementation['merger'].ROCrateMerger(mapping)
    record = merger.merge_rocrates(parsers, primary_index=1)
    if expected is ABSENT:
        assert target not in record
    elif expected == []:
        assert record[target] == []
    else:
        assert record[target] == [{child: ''}]
    evidence = merger.get_route_dispositions()
    assert [s['routes'][field][0]['selected_for_merge'] for s in evidence['sources']] == [False, True, False]
    assert_json(evidence['sources'][1]['routes'][field][0]['raw'], primary)
    assert_recoverable(evidence, [tmp_path / f'{i}.json' for i in range(3)], [field])
    policy.validate_evidence(evidence, record, mapping)


@pytest.mark.parametrize('primary,expected', [
    (ABSENT, 5), (None, 5), (False, ABSENT), (0, 0),
    ('42', ABSENT), ([], ABSENT), (12, 12),
])
def test_exact_size_selection_does_not_promote_past_an_unsupported_primary(
        implementation, tmp_path, primary, expected):
    mapping = implementation['loader'].MappingLoader(str(table(tmp_path, [('bytes', 'contentSize')])))
    parsers = []
    for i, value in enumerate([5, primary, 19]):
        props = {'contentSize': '2.3 TB'}
        if value is not ABSENT:
            props['evi:totalContentSizeBytes'] = value
        parsers.append(implementation['parser'].ROCrateParser(str(source(tmp_path / f'{i}.json', props))))
    merger = implementation['merger'].ROCrateMerger(mapping)
    record = merger.merge_rocrates(parsers, primary_index=1)
    if expected is ABSENT:
        assert 'total_size_bytes' not in record
    else:
        assert type(record['total_size_bytes']) is int and record['total_size_bytes'] == expected
    evidence = merger.get_route_dispositions()
    selected = [s['routes']['bytes'][1]['selected_for_merge'] for s in evidence['sources']]
    assert selected == ([True, False, False] if primary is ABSENT or primary is None else [False, True, False])
    assert_recoverable(evidence, [tmp_path / f'{i}.json' for i in range(3)], ['bytes'])
    policy.validate_evidence(evidence, record, mapping)


@pytest.mark.parametrize('mutation', ['bytes_only', 'disable_marker', 'covered_rows', 'forward_lookup', 'getter'])
def test_loaded_mapping_mutation_refuses_before_resetting_previous_builder_result(
        implementation, tmp_path, monkeypatch, mutation):
    mapping_path = table(tmp_path, [('tasks', 'rai:dataUseCases')])
    record, _, builder, parser, mapping = build(
        implementation, source(tmp_path / 'source.json', {'rai:dataUseCases': TEXT}), mapping_path)
    previous = deepcopy(record)
    if mutation == 'bytes_only':
        mapping_path.write_bytes(mapping_path.read_bytes() + b'\n')
    elif mutation == 'disable_marker':
        next(row for row in mapping.mappings if row['D4D Property'] == 'tasks')['Func'] = ''
    elif mutation == 'covered_rows':
        mapping.covered_mappings.pop()
    elif mutation == 'forward_lookup':
        mapping.d4d_to_rocrate['tasks'] = 'member:replacement'
    else:
        monkeypatch.setattr(mapping, 'get_mapping_info', lambda field: {'D4D Property': field})
    with pytest.raises(ValueError):
        builder.build_dataset(parser)
    assert_json(builder.d4d_data, previous)


@pytest.mark.parametrize('mutation', ['raw_bytes_only', 'parsed_graph'])
def test_source_changes_cannot_reuse_an_earlier_bound_result(implementation, tmp_path, mutation):
    path = source(tmp_path / 'source.json', {'rai:dataUseCases': TEXT})
    record, evidence, builder, parser, mapping = build(
        implementation, path, table(tmp_path, [('tasks', 'rai:dataUseCases')]))
    previous = deepcopy(record)
    if mutation == 'raw_bytes_only':
        path.write_bytes(path.read_bytes() + b'\n')
        with pytest.raises(ValueError):
            policy.validate_evidence(evidence, record, mapping)
    else:
        parser.require_root_dataset()['rai:dataUseCases'] = 'Changed parsed assertion'
    with pytest.raises(ValueError):
        builder.build_dataset(parser)
    assert_json(builder.d4d_data, previous)


def test_rankings_and_scoring_field_roster_do_not_gain_credit_from_dispositions(implementation, tmp_path):
    old_path = table(tmp_path, ALL_ROUTES, marked=False, name='old.tsv')
    new_path = table(tmp_path, ALL_ROUTES, name='new.tsv')
    old = implementation['loader'].MappingLoader(str(old_path))
    new = implementation['loader'].MappingLoader(str(new_path))
    props = {'rai:dataUseCases': TEXT, 'contentSize': '2.3 TB', 'version': '1', 'evi:formats': ['CSV']}
    parsers = [implementation['parser'].ROCrateParser(str(source(tmp_path / f'{i}.json', p)))
               for i, p in enumerate([props, {**props, 'evi:totalContentSizeBytes': 123}, {}])]
    scorer = implementation['scorer'].InformativenessScorer()
    old_ranking, new_ranking = scorer.rank_rocrates(parsers, old), scorer.rank_rocrates(parsers, new)
    assert len(old_ranking) == len(new_ranking) == len(parsers)
    for (old_parser, old_scores, old_rank), (new_parser, new_scores, new_rank) in zip(old_ranking, new_ranking):
        assert old_parser is new_parser
        assert type(old_rank) is type(new_rank) is int and old_rank == new_rank
        assert_json(old_scores, new_scores)
    assert old.get_covered_fields() == new.get_covered_fields()
    assert old.get_d4d_to_rocrate_mapping() == new.get_d4d_to_rocrate_mapping()
    assert 'total_size_bytes' not in new.get_covered_fields()


@pytest.mark.parametrize('extra_field', ['machine_annotation_tools', 'external_resources', 'total_size_bytes'])
def test_unmarked_rows_cannot_collide_with_marked_output_aliases(implementation, tmp_path, extra_field):
    marked_field, source_prop = {
        'machine_annotation_tools': ('machine_annotation_analyses', 'rai:machineAnnotationTools'),
        'external_resources': ('external_resource', 'associatedPublication'),
        'total_size_bytes': ('bytes', 'contentSize'),
    }[extra_field]
    mapping_path = table(tmp_path, [(marked_field, source_prop)])
    with mapping_path.open('a', encoding='utf-8') as stream:
        stream.write(f'{extra_field}\t\tcustom:assertion\t\t1\t1\n')
    with pytest.raises(ValueError, match='duplicate output target'):
        implementation['loader'].MappingLoader(str(mapping_path))


def test_unmarked_custom_route_keeps_scalar_output_and_has_no_route_evidence(implementation, tmp_path):
    record, evidence, _, _, _ = build(
        implementation, source(tmp_path / 'source.json', {'rai:dataUseCases': TEXT}),
        table(tmp_path, [('tasks', 'rai:dataUseCases')], marked=False))
    assert record['tasks'] == TEXT and evidence is None
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(record)
