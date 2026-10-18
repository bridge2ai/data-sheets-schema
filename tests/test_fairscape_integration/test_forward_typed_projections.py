"""#4954: finite typed projections, genuine models, and visible omissions.

The field policy is independently enumerated from the adopted proposal, not
imported from the implementation. A valid wire model is not a lossless D4D
encoding; complete unsupported values belong in detached diagnostic evidence.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import warnings

import pytest

from src.fairscape_integration.d4d_to_fairscape import (
    D4DToFairscapeConverter, ForwardProjectionWarning, convert_d4d_to_fairscape,
)
from fairscape_models.rocrate import ROCrateMetadataElem, ROCrateV1_2


# source, wire alias, D4D cardinality, wire cardinality, allowed text members
FIELDS = (
    ('known_limitations', 'rai:dataLimitations', 'list', 'scalar',
     ('limitation_description', 'description', 'name')),
    ('known_biases', 'rai:dataBiases', 'list', 'scalar',
     ('bias_description', 'description', 'name')),
    ('intended_uses', 'rai:dataUseCases', 'list', 'scalar',
     ('usage_notes', 'description', 'name')),
    ('updates', 'rai:dataReleaseMaintenancePlan', 'object', 'scalar',
     ('update_details', 'description', 'name')),
    ('missing_data_documentation', 'rai:dataCollectionMissingData', 'list', 'scalar',
     ('missing_data_patterns', 'description', 'name')),
    ('raw_data_sources', 'rai:dataCollectionRawData', 'list', 'scalar',
     ('source_description',)),
    ('collection_timeframes', 'rai:dataCollectionTimeframe', 'list', 'list',
     ('timeframe_details', 'description', 'name')),
    ('preprocessing_strategies', 'rai:dataPreprocessingProtocol', 'list', 'list',
     ('preprocessing_details', 'description', 'name')),
    ('annotation_analyses', 'rai:dataAnnotationAnalysis', 'list', 'list',
     ('annotation_quality_details', 'description', 'name')),
    ('distribution_formats', 'evi:formats', 'list', 'list',
     ('format', 'media_type', 'name')),
    ('addressing_gaps', 'd4d:addressingGaps', 'list', 'scalar',
     ('response', 'description', 'name')),
    ('anomalies', 'd4d:dataAnomalies', 'list', 'scalar',
     ('anomaly_details', 'description', 'name')),
    ('content_warnings', 'd4d:contentWarning', 'list', 'scalar',
     ('description', 'name')),
    ('informed_consent', 'd4d:informedConsent', 'list', 'scalar',
     ('description', 'name')),
    ('at_risk_populations', 'd4d:atRiskPopulations', 'object', 'scalar',
     ('description', 'name')),
)
SCALAR_LIST_FIELDS = tuple(f for f in FIELDS if f[2:4] == ('list', 'scalar'))
OBJECT_FIELDS = tuple(f for f in FIELDS if f[2] == 'object')
LIST_FIELDS = tuple(f for f in FIELDS if f[3] == 'list')
MEMBERS = tuple((f, member) for f in FIELDS for member in f[4])
ABSENT = object()


def typed(value):
    if type(value) is dict:
        return (dict, tuple((key, typed(item)) for key, item in value.items()))
    if type(value) is list:
        return (list, tuple(typed(item) for item in value))
    return (type(value), value.hex() if type(value) is float else value)


def dataset(fields=None):
    return {'id': 'urn:test:typed-forward', 'title': 'Typed projection',
            'description': 'Unrelated original narrative', 'keywords': [],
            'version': '1.0', 'license': 'https://example.org/license',
            **(fields or {})}


def input_value(field, member, text):
    item = {member: text}
    return [item] if field[2] == 'list' else item


def converted(fields, converter=None):
    data = dataset(fields)
    before = typed(data)
    converter = converter or D4DToFairscapeConverter()
    model = converter.convert(data)
    assert type(model) is ROCrateV1_2
    dump = model.model_dump(mode='json', by_alias=True, exclude_none=True)
    raw = json.dumps(dump, ensure_ascii=True, allow_nan=False).encode('utf-8')
    readback = ROCrateV1_2.model_validate(json.loads(raw))
    assert typed(readback.model_dump(mode='json', by_alias=True, exclude_none=True)) == typed(dump)
    roots = [node for node in readback.metadataGraph if node.guid == './']
    assert len(roots) == 1 and type(roots[0]) is ROCrateMetadataElem
    wire = [node for node in dump['@graph'] if node['@id'] == './']
    assert len(wire) == 1 and typed(data) == before
    return wire[0], converter


def row_for(converter, source):
    rows = [r for r in converter.route_evidence['assertions'] if r['source'] == source]
    assert len(rows) == 1
    row = rows[0]
    assert row['source_pointer'] == '/' + source
    return row


@pytest.mark.parametrize('field,member', MEMBERS,
                         ids=[f[0] + '-' + member for f, member in MEMBERS])
@pytest.mark.parametrize('text', ['  whole α; first\nsecond  ', ''], ids=['literal', 'empty'])
def test_each_admitted_member_uses_real_model_without_text_normalization(field, member, text):
    value = input_value(field, member, text)
    wire, converter = converted({field[0]: value})
    expected = [text] if field[3] == 'list' else text
    assert typed(wire[field[1]]) == typed(expected)
    row = row_for(converter, field[0])
    assert typed(row['raw']) == typed(value)
    assert row['target'] == field[1]
    assert row['decision'] == 'constructed' and row['retention'] == 'retained'
    assert typed(row['final_value']) == typed(expected)


@pytest.mark.parametrize('field', FIELDS, ids=[f[0] for f in FIELDS])
@pytest.mark.parametrize('kind', ['missing', 'null', 'false', 'zero'])
def test_presence_and_invalid_scalar_types_are_not_scientific_negatives(field, kind):
    raw = {'null': None, 'false': False, 'zero': 0}.get(kind, ABSENT)
    values = {} if raw is ABSENT else {field[0]: raw}
    wire, converter = converted(values)
    assert field[1] not in wire
    row = row_for(converter, field[0])
    assert row['presence'] == ('missing' if raw is ABSENT else 'null' if raw is None else 'present')
    assert typed(row['raw']) == typed(None if raw is ABSENT else raw)
    assert row['retention'] == ('not_emitted' if kind == 'null' else 'not_constructed')
    assert row['final_value'] is None


@pytest.mark.parametrize('field', SCALAR_LIST_FIELDS, ids=[f[0] for f in SCALAR_LIST_FIELDS])
@pytest.mark.parametrize('second', ['other', 'same'])
def test_scalar_target_never_first_picks_joins_or_deduplicates_records(field, second):
    member = field[4][0]
    values = [{member: 'same'}, {member: second}]
    wire, converter = converted({field[0]: values})
    assert field[1] not in wire
    row = row_for(converter, field[0])
    assert typed(row['raw']) == typed(values)
    assert row['decision'] == 'unplaced' and row['retention'] == 'not_constructed'
    assert row['reason']


@pytest.mark.parametrize('field', SCALAR_LIST_FIELDS, ids=[f[0] for f in SCALAR_LIST_FIELDS])
def test_scalar_target_does_not_convert_empty_source_list_to_empty_text(field):
    wire, converter = converted({field[0]: []})
    assert field[1] not in wire
    row = row_for(converter, field[0])
    assert row['presence'] == 'present' and row['raw'] == []
    assert row['retention'] == 'not_constructed'


@pytest.mark.parametrize('field', OBJECT_FIELDS, ids=[f[0] for f in OBJECT_FIELDS])
def test_object_slot_is_not_repaired_by_unwrapping_wrong_cardinality(field):
    raw = [{field[4][0]: 'not an object-valued input'}]
    wire, converter = converted({field[0]: raw})
    assert field[1] not in wire and row_for(converter, field[0])['raw'] == raw


@pytest.mark.parametrize('field', FIELDS, ids=[f[0] for f in FIELDS])
@pytest.mark.parametrize('extra', [None, {'original': [False, 0, 'α']}], ids=['null-member', 'rich-member'])
def test_extra_object_members_refuse_without_losing_complete_raw_value(field, extra):
    item = {field[4][0]: 'would otherwise fit', 'notes': extra}
    raw = [item] if field[2] == 'list' else item
    wire, converter = converted({field[0]: raw})
    assert field[1] not in wire
    row = row_for(converter, field[0])
    assert typed(row['raw']) == typed(raw)
    assert row['retention'] == 'not_constructed' and row['reason']


@pytest.mark.parametrize('field', LIST_FIELDS, ids=[f[0] for f in LIST_FIELDS])
def test_list_target_retains_immediate_order_duplicates_and_empty_strings(field):
    member = field[4][0]
    raw = [{member: 'B'}, {member: 'A'}, {member: 'B'}, {member: ''}, 'legacy literal']
    wire, converter = converted({field[0]: raw})
    assert wire[field[1]] == ['B', 'A', 'B', '', 'legacy literal']
    row = row_for(converter, field[0])
    assert typed(row['raw']) == typed(raw) and row['retention'] == 'retained'


@pytest.mark.parametrize('field', LIST_FIELDS, ids=[f[0] for f in LIST_FIELDS])
def test_explicit_empty_list_and_nonempty_all_refused_are_distinct(field):
    wire, converter = converted({field[0]: []})
    assert wire[field[1]] == [] and row_for(converter, field[0])['retention'] == 'retained'
    raw = [False, 0, [{field[4][0]: 'nested, not flattened'}]]
    wire, converter = converted({field[0]: raw})
    assert field[1] not in wire
    assert typed(row_for(converter, field[0])['raw']) == typed(raw)
    assert row_for(converter, field[0])['retention'] == 'not_constructed'


@pytest.mark.parametrize('field', FIELDS, ids=[f[0] for f in FIELDS])
def test_existing_wire_literal_shapes_remain_compatible(field):
    value = ['a', 'a', ''] if field[3] == 'list' else '  existing literal α\n '
    wire, converter = converted({field[0]: value})
    assert typed(wire[field[1]]) == typed(value)
    assert typed(row_for(converter, field[0])['raw']) == typed(value)


@pytest.mark.parametrize('source,target,raw', [
    ('collection_timeframes', 'rai:dataCollectionTimeframe', [{'end_date': '2026-01-01'}]),
    ('collection_timeframes', 'rai:dataCollectionTimeframe', [{'start_date': '2025-01-01', 'end_date': '2026-01-01'}]),
    ('informed_consent', 'd4d:informedConsent', [{'consent_obtained': False}]),
    ('content_warnings', 'd4d:contentWarning', [{'content_warnings_present': False}]),
    ('at_risk_populations', 'd4d:atRiskPopulations', {'at_risk_groups_included': False}),
    ('annotation_analyses', 'rai:dataAnnotationAnalysis', [{'inter_annotator_agreement_score': 0.9}]),
    ('distribution_formats', 'evi:formats', [{'download_url': 'https://example.org/data.csv'}]),
    ('distribution_formats', 'evi:formats', [{'format': 'CSV', 'checksum': 'abc'}]),
], ids=['end-date', 'date-interval', 'consent-false', 'warning-false', 'risk-false', 'agreement', 'format-url', 'format-checksum'])
def test_dates_metrics_booleans_and_locations_are_not_inferred_narratives(source, target, raw):
    wire, converter = converted({source: raw})
    assert target not in wire
    assert typed(row_for(converter, source)['raw']) == typed(raw)
    assert row_for(converter, source)['retention'] == 'not_constructed'


@pytest.mark.parametrize('alias,expected', [
    ({'name': 'alias'}, 'alias'), ({'description': 'canonical'}, 'canonical'),
    (None, ABSENT), ('', ''), (False, ABSENT),
    ({'name': 'alias', 'special_protections': ['extra']}, ABSENT),
], ids=['different', 'equal', 'null', 'empty', 'false', 'richer'])
def test_at_risk_compatibility_winner_and_superseded_source_are_explicit(alias, expected):
    fields = {'at_risk_populations': {'description': 'canonical'}, 'vulnerable_populations': alias}
    wire, converter = converted(fields)
    if expected is ABSENT:
        assert 'd4d:atRiskPopulations' not in wire
    else:
        assert wire['d4d:atRiskPopulations'] == expected
    canonical = row_for(converter, 'at_risk_populations')
    legacy = row_for(converter, 'vulnerable_populations')
    assert canonical['raw'] == fields['at_risk_populations']
    assert typed(legacy['raw']) == typed(alias)
    assert canonical['decision'] == 'superseded'
    assert canonical['reason'] and 'vulnerable_populations' in canonical['reason']
    assert canonical['retention'] != 'retained'


def test_alias_alone_uses_its_own_raw_pointer():
    wire, converter = converted({'vulnerable_populations': {'name': 'explicit alias'}})
    assert wire['d4d:atRiskPopulations'] == 'explicit alias'
    row = row_for(converter, 'vulnerable_populations')
    assert row['retention'] == 'retained' and row['raw'] == {'name': 'explicit alias'}


def test_root_projection_does_not_scan_nested_collections_or_unrelated_fields():
    fields = {'known_limitations': [{'description': 'root'}],
              'file_collections': [{'id': '#child', 'name': 'Child',
                                    'known_limitations': [{'description': 'child must not compete'}]}],
              'unrelated': {'known_limitations': [{'description': 'not a root'}]}}
    data = dataset(fields)
    before = deepcopy(data)
    converter = D4DToFairscapeConverter()
    model = converter.convert(data)
    graph = model.model_dump(mode='json', by_alias=True, exclude_none=True)['@graph']
    root = next(node for node in graph if node['@id'] == './')
    child = next(node for node in graph if node['@id'] == '#child')
    assert root['rai:dataLimitations'] == 'root'
    assert 'rai:dataLimitations' not in child
    assert row_for(converter, 'known_limitations')['raw'] == fields['known_limitations']
    assert data == before


def test_evidence_is_detached_and_failed_conversion_then_reuse_resets_it():
    converter = D4DToFairscapeConverter()
    raw = [{'description': 'kept', 'notes': {'original': ['α', False, 0]}}]
    data = dataset({'known_limitations': raw})
    converter.convert(data)
    evidence = converter.route_evidence
    data['known_limitations'][0]['notes']['original'].clear()
    evidence['assertions'].clear()
    # Check an independently captured value; data and raw intentionally alias.
    retained = row_for(converter, 'known_limitations')['raw']
    assert retained[0]['notes']['original'] == ['α', False, 0]
    with pytest.raises(ValueError):
        converter.convert(dataset({'known_biases': [{'description': 'this attempt'}], 'keywords': False}))
    failed = converter.route_evidence
    assert failed['status'] == 'failed' and failed['error']
    assert row_for(converter, 'known_biases')['raw'] == [{'description': 'this attempt'}]
    assert row_for(converter, 'known_limitations')['presence'] == 'missing'
    converted({'updates': {'description': 'next'}}, converter)
    assert converter.route_evidence['status'] == 'complete'
    assert row_for(converter, 'known_biases')['presence'] == 'missing'
    assert row_for(converter, 'updates')['retention'] == 'retained'


def test_unrelated_non_json_object_does_not_trigger_a_whole_input_evidence_sweep():
    unrelated = object()
    data = dataset({'unknown_unconsulted_field': unrelated,
                    'known_limitations': [{'description': 'supported'}]})
    converter = D4DToFairscapeConverter()
    model = converter.convert(data)
    assert data['unknown_unconsulted_field'] is unrelated
    root = next(node for node in model.model_dump(by_alias=True)['@graph'] if node['@id'] == './')
    assert root['rai:dataLimitations'] == 'supported'
    json.dumps(converter.route_evidence, allow_nan=False)


@pytest.mark.parametrize('field', FIELDS, ids=[f[0] for f in FIELDS])
@pytest.mark.parametrize('value', [False, 0], ids=['boolean', 'integer'])
def test_text_member_is_not_coerced_from_boolean_or_integer(field, value):
    raw = input_value(field, field[4][0], value)
    wire, converter = converted({field[0]: raw})
    assert field[1] not in wire
    assert typed(row_for(converter, field[0])['raw']) == typed(raw)
    assert row_for(converter, field[0])['retention'] == 'not_constructed'


@pytest.mark.parametrize('field', LIST_FIELDS, ids=[f[0] for f in LIST_FIELDS])
def test_partial_list_evidence_preserves_original_indices_and_complete_unsupported_units(field):
    member = field[4][0]
    raw = [{member: 'B'}, {member: 'not stringified', 'notes': [False, 0]},
           {member: 'B'}, [{member: 'not flattened'}], '', None]
    wire, converter = converted({field[0]: raw})
    assert wire[field[1]] == ['B', 'B', '']
    row = row_for(converter, field[0])
    assert typed(row['raw']) == typed(raw) and row['retention'] == 'partial'
    units = row['units']
    assert [unit['source_index'] for unit in units] == list(range(len(raw)))
    assert [unit['source_pointer'] for unit in units] == ['/' + field[0] + '/' + str(i) for i in range(len(raw))]
    assert typed([unit['raw'] for unit in units]) == typed(raw)
    assert [unit['decision'] for unit in units] == ['constructed', 'unplaced', 'constructed', 'unplaced', 'constructed', 'unplaced']
    assert [units[i]['final_value'] for i in (0, 2, 4)] == ['B', 'B', '']
    assert all(units[i]['reason'] and units[i]['retention'] == 'not_constructed' for i in (1, 3, 5))
    summary = converter.route_evidence['projection_summary']
    assert summary['model_valid'] is True and summary['incomplete'] is True
    assert any(item['source_pointer'] == '/' + field[0] for item in summary['partial'])


def test_equal_multiple_narrative_members_are_not_collapsed():
    raw = [{'limitation_description': 'same', 'description': 'same'}]
    wire, converter = converted({'known_limitations': raw})
    assert 'rai:dataLimitations' not in wire
    assert row_for(converter, 'known_limitations')['raw'] == raw
    assert converter.route_evidence['projection_summary']['incomplete'] is True


def test_summary_distinguishes_valid_model_omission_and_null_normalization():
    fields = {'known_limitations': [{'description': 'A'}, {'description': 'B'}],
              'updates': None, 'known_biases': [{'description': 'retained'}]}
    _, converter = converted(fields)
    summary = converter.route_evidence['projection_summary']
    assert summary['model_valid'] is True and summary['incomplete'] is True
    assert any(item['source_pointer'] == '/known_limitations' for item in summary['omitted'])
    assert any(item['source_pointer'] == '/updates' for item in summary['null_not_emitted'])
    assert all(item['source_pointer'] != '/known_biases' for item in summary['omitted'])
    assert converter.route_evidence['status'] == 'complete'


def test_null_alone_is_reported_without_false_unsupported_omission_warning():
    _, converter = converted({'updates': None})
    summary = converter.route_evidence['projection_summary']
    assert summary['incomplete'] is False
    assert any(item['source_pointer'] == '/updates' for item in summary['null_not_emitted'])


def test_convenience_wrapper_preserves_tuple_but_warns_about_actual_omission():
    raw = dataset({'known_limitations': [{'description': 'A'}, {'description': 'B'}]})
    before = typed(raw)
    with pytest.warns(ForwardProjectionWarning, match='known_limitations'):
        model, validation = convert_d4d_to_fairscape(raw)
    assert type(model) is ROCrateV1_2 and validation == (True, None)
    assert typed(raw) == before
    encoded = model.model_dump(mode='json', by_alias=True, exclude_none=True)
    assert typed(ROCrateV1_2.model_validate(json.loads(json.dumps(encoded))).model_dump(
        mode='json', by_alias=True, exclude_none=True)) == typed(encoded)


def test_convenience_wrapper_does_not_warn_for_supported_finite_projection():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        _, validation = convert_d4d_to_fairscape(dataset({'known_limitations': [{'description': 'A'}]}))
    assert validation == (True, None)
    assert not [item for item in caught if issubclass(item.category, ForwardProjectionWarning)]


def test_successful_alias_still_warns_about_superseded_nonnull_canonical_source():
    data = dataset({'at_risk_populations': {'description': 'canonical source'},
                    'vulnerable_populations': {'name': 'winning alias'}})
    with pytest.warns(ForwardProjectionWarning, match='/at_risk_populations'):
        model, validation = convert_d4d_to_fairscape(data)
    assert validation == (True, None)
    root = next(node for node in model.model_dump(by_alias=True)['@graph'] if node['@id'] == './')
    assert root['d4d:atRiskPopulations'] == 'winning alias'


def cli_runner():
    from click.testing import CliRunner
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


def invoke_cli(source, *args):
    from fairscape_integration.cli import cli
    return cli_runner().invoke(cli, ['d4d-to-rocrate', str(source), *map(str, args)])


def source_file(tmp_path, *, omitted=True):
    source = tmp_path / 'source.yaml'
    value = [{'description': 'α\nA'}, {'description': 'B'}] if omitted else [{'description': 'supported'}]
    source.write_text(json.dumps(dataset({'known_limitations': value}), ensure_ascii=False), encoding='utf-8')
    return source


def test_cli_warns_without_report_and_keeps_stdout_valid_model_json(tmp_path):
    source = source_file(tmp_path)
    before = source.read_bytes()
    result = invoke_cli(source)
    assert result.exit_code == 0, result.output
    wire = json.loads(result.stdout)
    readback = ROCrateV1_2.model_validate(wire)
    assert type(readback) is ROCrateV1_2
    assert 'incomplete' in result.stderr.lower()
    assert '/known_limitations' in result.stderr
    assert 'not saved' in result.stderr.lower() and '--report' in result.stderr
    assert source.read_bytes() == before


def test_cli_report_preserves_full_raw_values_without_wire_carriers(tmp_path):
    source = source_file(tmp_path)
    output, report = tmp_path / 'crate.json', tmp_path / 'report.json'
    result = invoke_cli(source, '-o', output, '--report', report, '--pretty')
    assert result.exit_code == 0, result.output
    assert 'model-valid' in result.stdout.lower() and 'incomplete' in result.stderr.lower()
    evidence = json.loads(report.read_text(encoding='utf-8'))
    rows = [row for row in evidence['assertions'] if row['source'] == 'known_limitations']
    assert len(rows) == 1
    assert rows[0]['raw'] == [{'description': 'α\nA'}, {'description': 'B'}]
    assert rows[0]['source_pointer'] == '/known_limitations'
    assert evidence['projection_summary']['incomplete'] is True
    wire = json.loads(output.read_text(encoding='utf-8'))
    root = next(node for node in wire['@graph'] if node['@id'] == './')
    assert 'rai:dataLimitations' not in root
    assert not any('known_limitations' in key or 'limitationsEvidence' in key for key in root)
    ROCrateV1_2.model_validate(wire)


def test_cli_complete_projection_has_no_false_incomplete_warning(tmp_path):
    source = source_file(tmp_path, omitted=False)
    result = invoke_cli(source)
    assert result.exit_code == 0, result.output
    assert 'incomplete' not in result.stderr.lower()
    wire = json.loads(result.stdout)
    assert next(node for node in wire['@graph'] if node['@id'] == './')['rai:dataLimitations'] == 'supported'


@pytest.mark.parametrize('collision', ['input-report', 'input-output', 'output-report', 'symlink-input-report', 'hardlink-input-report'])
def test_cli_collisions_refuse_before_any_write(tmp_path, collision):
    source = source_file(tmp_path)
    output, report = tmp_path / 'output.json', tmp_path / 'report.json'
    output.write_bytes(b'original output\n')
    if collision == 'input-report':
        report = source
    elif collision == 'input-output':
        output = source
    elif collision == 'output-report':
        report = output
    elif collision == 'symlink-input-report':
        report.symlink_to(source)
    else:
        os.link(source, report)
    before = {path: path.read_bytes() for path in (source, output, report) if path.exists()}
    result = invoke_cli(source, '-o', output, '--report', report)
    assert result.exit_code != 0
    assert all(path.read_bytes() == raw for path, raw in before.items())
    assert 'written to' not in result.stdout.lower()


def test_cli_report_write_error_is_not_successful_export(tmp_path):
    source = source_file(tmp_path)
    report = tmp_path / 'directory-not-a-report'
    report.mkdir()
    result = invoke_cli(source, '-o', tmp_path / 'output.json', '--report', report)
    assert result.exit_code != 0
    assert 'error' in result.stderr.lower()
    assert 'written to' not in result.stdout.lower()
    assert report.is_dir()


def test_cli_model_error_is_not_downgraded_to_partial_projection_success(tmp_path):
    source = tmp_path / 'invalid.yaml'
    source.write_text(json.dumps(dataset({'keywords': False,
                                        'known_limitations': [{'description': 'A'}, {'description': 'B'}]})))
    result = invoke_cli(source, '-o', tmp_path / 'output.json')
    assert result.exit_code != 0 and 'error' in result.stderr.lower()
    assert not (tmp_path / 'output.json').exists()
