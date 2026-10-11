"""#4956: validate nested metadata through the genuine JSON model dispatcher."""
from copy import deepcopy
from datetime import date, datetime
import json
import math

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from src.fairscape_integration.d4d_to_fairscape import D4DToFairscapeConverter
from src.fairscape_integration.fairscape_to_d4d import FairscapeToD4DConverter
from fairscape_models.rocrate import (
    GenericMetadataElem, ROCrateMetadataElem, ROCrateMetadataFileElem, ROCrateV1_2,
)


def dataset(collections=None):
    return {'id': 'urn:test:nested', 'title': 'Root title',
            'description': 'Root description', 'version': '1.0', 'license': 'MIT',
            'file_collections': collections if collections is not None else [
                {'id': '#child', 'name': 'Child'}]}


def encoded(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True)


def dump(model, exclude_none=True):
    return model.model_dump(mode='json', by_alias=True, exclude_none=exclude_none)


def genuine_readback(model, exclude_none=True):
    original = encoded(dump(model, exclude_none))
    rebuilt = ROCrateV1_2.model_validate(json.loads(original))
    assert encoded(dump(rebuilt, exclude_none)) == original
    assert encoded(dump(model, exclude_none)) == original
    return json.loads(original), rebuilt


def typed_child(**extra):
    return ROCrateMetadataElem(**{
        '@id': '#child', '@type': ['Dataset'], 'name': 'Child',
        'description': 'File collection', 'keywords': [], 'version': '1.0',
        'author': 'Unknown', 'license': 'Unspecified', 'hasPart': [], **extra})


def ambiguous_crate():
    """Real model construction bypasses dictionary dispatch until JSON readback."""
    descriptor = ROCrateMetadataFileElem(**{
        '@id': 'ro-crate-metadata.json', '@type': 'CreativeWork',
        'conformsTo': {'@id': 'https://w3id.org/ro/crate/1.2'}, 'about': {'@id': './'}})
    root = typed_child(**{'@id': './', '@type': ['Dataset', 'https://w3id.org/EVI#ROCrate'],
                         'hasPart': [{'@id': '#child'}]})
    return ROCrateV1_2(**{'@context': {'@vocab': 'https://schema.org/'},
                         '@graph': [descriptor, typed_child(), root]})


def old_children(builder):
    """Inject the former child type at construction, leaving validation genuine."""
    def build(data):
        children, references = builder(data)
        old = []
        for child in children:
            fields = child.model_dump(mode='python', by_alias=True, exclude_none=False)
            fields['@type'] = ['Dataset']
            old.append(ROCrateMetadataElem(**fields))
        return old, references
    return build


@pytest.mark.parametrize('count', [1, 2], ids=['minimal-child', 'two-children'])
def test_nested_children_have_exact_types_and_complete_json_roundtrip(count):
    collections = [{'id': '#child-' + str(i), 'name': 'Child ' + str(i),
                    'total_bytes': 100 + i, 'file_count': i,
                    'collection_type': 'test_split', 'path': '/data/' + str(i),
                    'compression': 'gzip'} for i in range(count)]
    data = dataset(collections)
    data['total_size_bytes'] = sum(item['total_bytes'] for item in collections)
    before = deepcopy(data)
    converter = D4DToFairscapeConverter()
    model = converter.convert(data)
    wire, readback = genuine_readback(model)
    assert len(wire['@graph']) == count + 2
    assert type(model.metadataGraph[0]) is ROCrateMetadataFileElem
    assert type(model.metadataGraph[-1]) is ROCrateMetadataElem
    assert [type(node) for node in model.metadataGraph[1:-1]] == [GenericMetadataElem] * count
    assert [type(node) for node in readback.metadataGraph[1:-1]] == [GenericMetadataElem] * count
    root = wire['@graph'][-1]
    assert root['@id'] == './' and root['@type'] == ['Dataset', 'https://w3id.org/EVI#ROCrate']
    assert root['hasPart'] == [{'@id': item['id']} for item in collections]
    assert root['contentSize'] == str(data['total_size_bytes'])
    assert wire['@graph'][0]['about'] == {'@id': './'}
    for child, source in zip(wire['@graph'][1:-1], collections):
        assert child['@id'] == source['id'] and child['name'] == source['name']
        assert child['@type'] == ['https://schema.org/Dataset']
        assert 'datePublished' not in child and 'format' not in child
        assert child['contentSize'] == str(source['total_bytes'])
        assert child['contentUrl'] == source['path'] and child['fileFormat'] == 'gzip'
        assert child['d4d:collectionType'] == 'test_split'
        assert type(child['d4d:fileCount']) is int and child['d4d:fileCount'] == source['file_count']
    recovered = FairscapeToD4DConverter().convert(json.loads(encoded(wire)))
    assert [item['id'] for item in recovered['file_collections']] == [item['id'] for item in collections]
    assert [item['total_bytes'] for item in recovered['file_collections']] == [item['total_bytes'] for item in collections]
    assert converter.validate(model) == (True, None)
    assert data == before


@pytest.mark.parametrize('value', [None, False, 0, ['', False, 0, None, 'duplicate', 'duplicate']],
                         ids=['null', 'false', 'zero', 'ordered-extra-list'])
@pytest.mark.parametrize('exclude_none', [False, True], ids=['with-null', 'without-null'])
def test_child_transfer_matches_typed_validation_in_both_null_modes(value, exclude_none):
    source = {'id': '#child', 'name': 'Child', 'license': None,
              'keywords': ['B', '', 'B'], 'path': None, 'compression': None,
              'collection_type': value, 'file_count': value}
    reference = typed_child(**{'license': None, 'keywords': ['B', '', 'B'],
                               'contentUrl': None, 'fileFormat': None,
                               'd4d:collectionType': deepcopy(value), 'd4d:fileCount': deepcopy(value)})
    expected = dump(reference, exclude_none)
    expected['@type'] = ['https://schema.org/Dataset']
    data = dataset([source]); before = encoded(data)
    model = D4DToFairscapeConverter().convert(data)
    wire, _ = genuine_readback(model, exclude_none)
    assert encoded(wire['@graph'][1]) == encoded(expected)
    assert wire['@graph'][1]['keywords'] == ['B', '', 'B']
    assert encoded(data) == before


@pytest.mark.parametrize('bad', [{'keywords': False}, {'name': {'label': 'invalid name'}}],
                         ids=['invalid-keywords', 'nonempty-object-name'])
def test_generic_child_transfer_does_not_bypass_original_typed_refusals(bad):
    converter = D4DToFairscapeConverter()
    data = dataset([{'id': '#child', 'name': 'Child', **bad}]); before = deepcopy(data)
    with pytest.raises(ValidationError) as failure:
        converter.convert(data)
    assert next(iter(bad)) in str(failure.value)
    evidence = converter.route_evidence
    assert evidence['status'] == 'failed' and evidence['error']
    assert evidence['projection_summary']['model_valid'] is False
    assert data == before


def test_validate_refuses_old_ambiguous_child_after_actual_json_dispatch():
    model = ambiguous_crate()
    original = encoded(dump(model))
    assert 'datePublished' not in dump(model)['@graph'][1]
    assert 'format' not in dump(model)['@graph'][1]
    valid, errors = D4DToFairscapeConverter().validate(model)
    assert valid is False
    assert any('datePublished' in item for item in errors)
    assert any('format' in item for item in errors)
    assert encoded(dump(model)) == original


def test_real_readback_failure_preserves_exception_and_resets_evidence_on_reuse(monkeypatch):
    converter = D4DToFairscapeConverter()
    previous = dataset(); previous['known_limitations'] = [{'description': 'previous'}]
    converter.convert(previous)
    builder = converter._build_file_collections
    actual_validate = ROCrateV1_2.model_validate
    observed = []

    def record_real_error(cls, value, *args, **kwargs):
        try:
            return actual_validate(value, *args, **kwargs)
        except ValidationError as exc:
            observed.append(exc)
            raise

    monkeypatch.setattr(converter, '_build_file_collections', old_children(builder))
    monkeypatch.setattr(ROCrateV1_2, 'model_validate', classmethod(record_real_error))
    current = dataset(); current['known_limitations'] = [{'description': 'current'}]
    before = deepcopy(current)
    with pytest.raises(ValidationError) as failure:
        converter.convert(current)
    assert len(observed) == 1 and failure.value is observed[0]
    failed = converter.route_evidence
    assert failed['status'] == 'failed' and failed['error']
    assert failed['projection_summary']['model_valid'] is False
    row = next(row for row in failed['assertions'] if row['source'] == 'known_limitations')
    assert row['raw'] == current['known_limitations']
    assert 'previous' not in encoded(failed)
    assert current == before
    monkeypatch.undo()
    result = converter.convert(dataset())
    genuine_readback(result)
    complete = converter.route_evidence
    assert complete['status'] == 'complete' and complete['error'] is None
    assert complete['projection_summary']['model_valid'] is True
    assert next(row for row in complete['assertions'] if row['source'] == 'known_limitations')['presence'] == 'missing'
    assert failed['status'] == 'failed'  # detached snapshot survives later reuse


def test_wire_validation_distinguishes_boolean_from_equal_numeric_readback(monkeypatch):
    converter = D4DToFairscapeConverter()
    data = dataset([{'id': '#child', 'name': 'Child', 'file_count': False}])
    model = converter.convert(data)
    before = encoded(dump(model))
    actual_validate = ROCrateV1_2.model_validate

    def change_type_after_real_validation(cls, value, *args, **kwargs):
        rebuilt = actual_validate(value, *args, **kwargs)
        child = next(node for node in rebuilt.metadataGraph if node.guid == '#child')
        setattr(child, 'd4d:fileCount', 0)
        return rebuilt

    monkeypatch.setattr(ROCrateV1_2, 'model_validate', classmethod(change_type_after_real_validation))
    valid, errors = converter.validate(model)
    assert valid is False and any('ValueError' in error and 'readback' in error for error in errors)
    with pytest.raises(ValueError, match='readback'):
        converter.convert(data)
    assert converter.route_evidence['status'] == 'failed'
    assert converter.route_evidence['projection_summary']['model_valid'] is False
    assert encoded(dump(model)) == before
    assert type(data['file_collections'][0]['file_count']) is bool


@pytest.mark.parametrize('value', [float('inf'), object()], ids=['nonfinite', 'nonserializable'])
def test_unserializable_publication_is_never_marked_model_valid(value):
    converter = D4DToFairscapeConverter()
    data = dataset([{'id': '#child', 'name': 'Child', 'file_count': value}])
    with pytest.raises((ValueError, PydanticSerializationError)):
        converter.convert(data)
    assert data['file_collections'][0]['file_count'] is value
    assert converter.route_evidence['status'] == 'failed'
    assert converter.route_evidence['projection_summary']['model_valid'] is False
    # Isolate serialization from the separate old-child dispatch refusal.
    model = converter.convert(dataset())
    genuine_readback(model)
    child = next(node for node in model.metadataGraph if node.guid == '#child')
    assert type(child) is GenericMetadataElem
    setattr(child, 'd4d:fileCount', value)
    valid, errors = converter.validate(model)
    assert valid is False and errors
    assert any('ValueError' in error or 'PydanticSerializationError' in error for error in errors)


NONFINITE_CASES = [
    'direct-inf', 'direct-negative-inf', 'direct-nan', 'nested-list',
    'nested-map', 'tuple', 'set', 'frozen-set', 'dictionary-key',
]


def nonfinite_value(case):
    return {
        'direct-inf': float('inf'),
        'direct-negative-inf': float('-inf'),
        'direct-nan': float('nan'),
        'nested-list': ['finite', [float('inf')]],
        'nested-map': {'outer': {'inner': float('nan')}},
        'tuple': ('finite', float('-inf')),
        'set': {float('inf')},
        'frozen-set': frozenset({float('nan')}),
        'dictionary-key': {float('inf'): 'finite value'},
    }[case]


def selected_leaf(case, value):
    """Identify the one explicit sentinel; this does not implement a tree guard."""
    if case == 'nested-list':
        return value[1][0]
    if case == 'nested-map':
        return value['outer']['inner']
    if case == 'tuple':
        return value[1]
    if case in ('set', 'frozen-set', 'dictionary-key'):
        return next(iter(value))
    return value


@pytest.mark.parametrize('case', NONFINITE_CASES, ids=NONFINITE_CASES)
@pytest.mark.parametrize('owner', ['child', 'root'], ids=['generic-child', 'typed-root'])
def test_validated_python_nonfinite_values_and_keys_are_refused_before_json_normalization(case, owner):
    converter = D4DToFairscapeConverter()
    model = converter.convert(dataset())
    genuine_readback(model)
    entity_id = '#child' if owner == 'child' else './'
    entity = next(node for node in model.metadataGraph if node.guid == entity_id)
    assert type(entity) is (GenericMetadataElem if owner == 'child' else ROCrateMetadataElem)
    value = nonfinite_value(case)
    setattr(entity, 'd4d:nonfiniteProbe', value)
    before = repr(value)
    python_node = next(node for node in model.model_dump(mode='python', by_alias=True)['@graph']
                       if node['@id'] == entity_id)
    observed = python_node['d4d:nonfiniteProbe']
    assert type(observed) is type(value)
    assert isinstance(selected_leaf(case, observed), float)
    assert not math.isfinite(selected_leaf(case, observed))
    valid, errors = converter.validate(model)
    assert valid is False
    assert any('ValueError' in error and 'finite' in error.lower() for error in errors)
    assert repr(value) == before and not math.isfinite(selected_leaf(case, value))
    after = next(node for node in model.model_dump(mode='python', by_alias=True)['@graph']
                 if node['@id'] == entity_id)['d4d:nonfiniteProbe']
    assert type(after) is type(observed) and not math.isfinite(selected_leaf(case, after))


@pytest.mark.parametrize('owner', ['child', 'root'], ids=['generic-child', 'typed-root'])
def test_finite_values_null_boolean_zero_and_dates_keep_existing_json_behavior(owner):
    converter = D4DToFairscapeConverter()
    model = converter.convert(dataset())
    entity_id = '#child' if owner == 'child' else './'
    entity = next(node for node in model.metadataGraph if node.guid == entity_id)
    value = {'list': [False, 0, None, 1.25], 'tuple': (False, 0, None),
             'set': {2.5}, 'frozen': frozenset({3.5}),
             'date': date(2026, 10, 11), 'time': datetime(2026, 10, 11, 12, 30)}
    before = deepcopy(value)
    setattr(entity, 'd4d:finiteProbe', value)
    assert converter.validate(model) == (True, None)
    wire, _ = genuine_readback(model)
    actual = next(node for node in wire['@graph'] if node['@id'] == entity_id)['d4d:finiteProbe']
    expected = {'list': [False, 0, None, 1.25], 'tuple': [False, 0, None],
                'set': [2.5], 'frozen': [3.5], 'date': '2026-10-11', 'time': '2026-10-11T12:30:00'}
    assert encoded(actual) == encoded(expected)
    assert value == before
    assert type(value['list'][0]) is bool and type(value['list'][1]) is int


def test_unemitted_source_only_nonfinite_value_is_not_a_raw_input_sweep():
    data = dataset()
    data['unrelated_unmapped_value'] = {'inner': float('inf')}
    converter = D4DToFairscapeConverter()
    model = converter.convert(data)
    wire, _ = genuine_readback(model)
    assert converter.validate(model) == (True, None)
    assert 'unrelated_unmapped_value' not in encoded(wire)
    assert math.isinf(data['unrelated_unmapped_value']['inner'])
    assert converter.route_evidence['status'] == 'complete'
    assert converter.route_evidence['projection_summary']['model_valid'] is True


@pytest.mark.parametrize('case', ['nested-list', 'nested-map'], ids=['list-infinity', 'map-nan'])
def test_nested_nonfinite_conversion_refuses_with_fresh_evidence_and_successful_reuse(case):
    converter = D4DToFairscapeConverter()
    converter.convert(dataset())
    value = nonfinite_value(case)
    data = dataset([{'id': '#child', 'name': 'Child', 'file_count': value}])
    data['known_limitations'] = [{'description': 'current input'}]
    with pytest.raises(ValueError, match='[Ff]inite'):
        converter.convert(data)
    failed = converter.route_evidence
    assert failed['status'] == 'failed' and failed['error']
    assert failed['projection_summary']['model_valid'] is False
    assert next(row for row in failed['assertions'] if row['source'] == 'known_limitations')['raw'] == data['known_limitations']
    assert not math.isfinite(selected_leaf(case, data['file_collections'][0]['file_count']))
    genuine_readback(converter.convert(dataset()))
    current = converter.route_evidence
    assert current['status'] == 'complete' and current['error'] is None
    assert current['projection_summary']['model_valid'] is True
    assert next(row for row in current['assertions'] if row['source'] == 'known_limitations')['presence'] == 'missing'
    assert failed['status'] == 'failed'


def test_nonfinite_introduced_after_genuine_readback_cannot_normalize_to_expected_null(monkeypatch):
    converter = D4DToFairscapeConverter()
    model = converter.convert(dataset([{'id': '#child', 'name': 'Child', 'file_count': [None]}]))
    genuine_readback(model)
    actual_validate = ROCrateV1_2.model_validate

    def insert_after_real_validation(cls, value, *args, **kwargs):
        rebuilt = actual_validate(value, *args, **kwargs)
        child = next(node for node in rebuilt.metadataGraph if node.guid == '#child')
        setattr(child, 'd4d:fileCount', [float('inf')])
        return rebuilt

    monkeypatch.setattr(ROCrateV1_2, 'model_validate', classmethod(insert_after_real_validation))
    valid, errors = converter.validate(model)
    assert valid is False and any('finite' in error.lower() for error in errors)
    assert dump(model)['@graph'][1]['d4d:fileCount'] == [None]


@pytest.mark.parametrize('exception', [KeyboardInterrupt, SystemExit, GeneratorExit],
                         ids=['keyboard-interrupt', 'system-exit', 'generator-exit'])
def test_validate_does_not_swallow_cancellation_during_serialization(monkeypatch, exception):
    model = ambiguous_crate()
    sentinel = exception('cancel the wire check')

    def interrupt(*args, **kwargs):
        raise sentinel

    monkeypatch.setattr(ROCrateV1_2, 'model_dump', interrupt)
    with pytest.raises(exception) as failure:
        D4DToFairscapeConverter().validate(model)
    assert failure.value is sentinel


def cli_runner():
    from click.testing import CliRunner
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


def test_cli_readback_failure_preserves_occupied_output_and_report(monkeypatch, tmp_path):
    from fairscape_integration import cli as cli_module
    converter = cli_module.D4DToFairscapeConverter()
    converter._build_file_collections = old_children(converter._build_file_collections)
    monkeypatch.setattr(cli_module, 'D4DToFairscapeConverter', lambda: converter)
    source, output, report = (tmp_path / name for name in ['source.yaml', 'crate.json', 'report.json'])
    source.write_text(json.dumps(dataset()), encoding='utf-8')
    output.write_bytes(b'occupied output\n'); report.write_bytes(b'occupied report\n')
    before = {path: path.read_bytes() for path in (source, output, report)}
    result = cli_runner().invoke(cli_module.cli, ['d4d-to-rocrate', str(source), '-o', str(output), '--report', str(report)])
    assert result.exit_code != 0
    assert 'datePublished' in result.stderr and 'format' in result.stderr
    assert 'written to' not in result.stdout.lower() and 'model-valid' not in result.stdout.lower()
    assert all(path.read_bytes() == content for path, content in before.items())
    assert converter.route_evidence['status'] == 'failed'
    assert converter.route_evidence['projection_summary']['model_valid'] is False


def test_cli_success_publishes_complete_readable_nested_graph_and_evidence(tmp_path):
    from fairscape_integration.cli import cli
    source, output, report = (tmp_path / name for name in ['source.yaml', 'crate.json', 'report.json'])
    data = dataset([{'id': '#A', 'name': 'A'}, {'id': '#B', 'name': 'B'}])
    source.write_text(json.dumps(data), encoding='utf-8'); before = source.read_bytes()
    result = cli_runner().invoke(cli, ['d4d-to-rocrate', str(source), '-o', str(output), '--report', str(report)])
    assert result.exit_code == 0, result.output
    wire = json.loads(output.read_text(encoding='utf-8'))
    model = ROCrateV1_2.model_validate(deepcopy(wire))
    assert encoded(dump(model)) == encoded(wire)
    assert len(wire['@graph']) == 4
    assert [node['@id'] for node in wire['@graph'][1:-1]] == ['#A', '#B']
    assert all(node['@type'] == ['https://schema.org/Dataset'] for node in wire['@graph'][1:-1])
    evidence = json.loads(report.read_text(encoding='utf-8'))
    assert evidence['status'] == 'complete' and evidence['projection_summary']['model_valid'] is True
    assert source.read_bytes() == before


def test_cli_nested_nonfinite_refusal_keeps_occupied_files_and_input(tmp_path):
    from fairscape_integration.cli import cli
    source, output, report = (tmp_path / name for name in ['nonfinite.yaml', 'crate.json', 'report.json'])
    source.write_text("title: Nonfinite nested extra\nfile_collections:\n"
                      "  - id: '#child'\n    name: Child\n    file_count: [.inf]\n", encoding='utf-8')
    output.write_bytes(b'occupied output\n'); report.write_bytes(b'occupied report\n')
    before = {path: path.read_bytes() for path in (source, output, report)}
    result = cli_runner().invoke(cli, ['d4d-to-rocrate', str(source), '-o', str(output), '--report', str(report)])
    assert result.exit_code != 0 and 'finite' in result.stderr.lower()
    assert 'written to' not in result.stdout.lower() and 'model-valid' not in result.stdout.lower()
    assert all(path.read_bytes() == raw for path, raw in before.items())
