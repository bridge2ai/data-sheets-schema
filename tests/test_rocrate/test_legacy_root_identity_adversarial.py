"""Independent identity-route controls: real rank reversal and coverage joins.

These use actual legacy loaders, parsers, builders, scorers, mergers and API.
The unmarked-ID arm is an observable counterexample to counting the new row;
it must change rank while the construction-only marked arm must not.
"""
from copy import deepcopy
import csv
import importlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from data_sheets_schema import legacy_root_identity as identity
from .test_legacy_root_gates import legacy_imports


ROOT = Path(__file__).resolve().parents[2]
COLUMNS = ['D4D Property', 'Type', 'FAIRSCAPE RO-Crate Property', 'Func',
           identity.COVERED, 'Direct mapping? Yes =1; No = 0']
FIELDS = [('title', 'name'), ('version', 'sourceOnly'), ('license', 'license'),
          ('citation', 'citation'), ('language', 'language'), ('format', 'format'),
          ('publisher', 'publisher'), ('purpose', 'purpose')]


@pytest.fixture(params=['packaged', 'hidden'])
def modules(request):
    names = ('d4d_builder', 'mapping_loader', 'rocrate_parser',
             'rocrate_merger', 'informativeness_scorer')
    if request.param == 'hidden':
        with legacy_imports():
            yield {name: importlib.import_module(name) for name in names}
    else:
        yield {name: importlib.import_module('fairscape_integration.utils.' + name)
               for name in names}


def table(path, route='absent', *, extra=()):
    rows = [[field, 'str', prop, '', '1', '1'] for field, prop in FIELDS]
    if route != 'absent':
        rows.append(['id', 'str', 'identifier,@id',
                     identity.MARKER if route == 'marked' else route, '1', '0'])
    rows.extend(extra)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle, delimiter='\t')
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    return path


def crate(path, root):
    value = {'@id': './', '@type': 'Dataset', **deepcopy(root)}
    path.write_text(json.dumps({'@graph': [
        {'@id': 'ro-crate-metadata.json', '@type': 'CreativeWork',
         'about': {'@id': value['@id']}}, value,
    ]}), encoding='utf-8')
    return path


def ranked_inputs(tmp_path):
    # A: 2/8 covered + 1/2 unique = .25. B: 1/8 covered + .75
    # richness and .25 technical = .225. A common unmarked ID changes the
    # denominators: A=.23333, B=.26389, so B becomes the primary.
    first = crate(tmp_path / 'ordinary-primary.json', {
        'identifier': 'ark:12345/ordinary', 'name': 'Ordinary primary',
        'sourceOnly': '1'})
    second = crate(tmp_path / 'richer-secondary.json', {
        'identifier': 'ark:12345/richer', 'name': 'Richer secondary',
        'description': 'Retained source description. ' * 12,
        'additionalProperty': [{'name': 'retained', 'value': 'text'}],
        'generatedBy': 'retained workflow', 'contentUrl': 'https://example.org/data'})
    return [first, second]


def ranking(modules, sources, mapping):
    parsers = [modules['rocrate_parser'].ROCrateParser(str(path)) for path in sources]
    scorer = modules['informativeness_scorer'].InformativenessScorer()
    loader = modules['mapping_loader'].MappingLoader(str(mapping))
    ranked = scorer.rank_rocrates(parsers, loader)
    return [(Path(parser.rocrate_path), score, rank) for parser, score, rank in ranked]


def test_marked_identity_preserves_real_ranking_where_naive_id_reverses_it(modules, tmp_path):
    sources = ranked_inputs(tmp_path)
    before = {path: path.read_bytes() for path in sources}
    original = table(tmp_path / 'original.tsv')
    marked = table(tmp_path / 'explicit-copied-table.tsv', 'marked')
    custom = table(tmp_path / 'custom.tsv', '')
    old = ranking(modules, sources, original)
    new = ranking(modules, sources, marked)
    naive = ranking(modules, sources, custom)
    assert old == new  # Complete scores, paths and ranks, not just order.
    assert [row[0] for row in old] == sources
    assert [row[0] for row in naive] == sources[::-1]
    assert old[0][1]['total_score'] == pytest.approx(.25)
    assert old[1][1]['total_score'] == pytest.approx(.225)
    assert old[0][1]['d4d_coverage'] == 2
    assert naive[0][1]['d4d_coverage'] == 2
    assert naive[1][1]['d4d_coverage'] == 3
    assert {path: path.read_bytes() for path in before} == before


@pytest.fixture
def api():
    with legacy_imports():
        name = '_root_gates_transform_api'
        spec = importlib.util.spec_from_file_location(
            name, ROOT / 'src/transformation/transform_api.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        yield module


def transformer(api, mapping, *, contract='dataset_v1', provenance=True):
    # These controls inspect the actual no-output draft result. Publication
    # validation is not replaced, stubbed or invoked by this test helper.
    return api.SemanticTransformer(api.TransformationConfig(
        mapping_file=mapping, validate_input=False, validate_output=False,
        result_contract=contract, preserve_provenance=provenance))


@pytest.mark.parametrize('contract', ['legacy', 'dataset_v1'])
def test_api_source_coverage_excludes_only_explicit_construction_id(api, tmp_path, contract):
    source = ranked_inputs(tmp_path)[0]
    mappings = {kind: table(tmp_path / (kind + '.tsv'), route)
                for kind, route in [('old', 'absent'), ('marked', 'marked'), ('custom', '')]}
    before = {path: path.read_bytes() for path in [source, *mappings.values()]}
    results = {kind: transformer(api, mapping, contract=contract).rocrate_to_d4d(source)
               for kind, mapping in mappings.items()}
    old, marked, custom = (results[key] for key in ('old', 'marked', 'custom'))
    assert old.coverage_percentage == marked.coverage_percentage == 25.0
    assert old.unmapped_fields == marked.unmapped_fields
    assert 'id' not in marked.unmapped_fields
    assert custom.coverage_percentage == pytest.approx(100 / 3)
    assert 'id' not in old.data
    assert marked.data['id'] == custom.data['id'] == 'ark:12345/ordinary'
    for result in results.values():
        assert result.transformation_metadata['coverage_percentage'] == result.coverage_percentage
        assert result.transformation_metadata['unmapped_fields'] == result.unmapped_fields
    assert {path: path.read_bytes() for path in before} == before


def test_actual_api_auto_merge_keeps_primary_and_non_identity_output(api, tmp_path):
    sources = ranked_inputs(tmp_path)
    original = table(tmp_path / 'old.tsv')
    marked = table(tmp_path / 'new.tsv', 'marked')
    custom = table(tmp_path / 'custom.tsv', '')
    results = [transformer(api, mapping).merge_rocrates(sources)
               for mapping in (original, marked, custom)]
    old, new, naive = results
    assert old['transformation_metadata']['source_order'] == [str(path) for path in sources]
    assert new['transformation_metadata']['source_order'] == old['transformation_metadata']['source_order']
    assert naive['transformation_metadata']['source_order'] == [str(path) for path in sources[::-1]]
    assert new['data']['id'] == 'ark:12345/ordinary'
    assert naive['data']['id'] == 'ark:12345/richer'
    assert {key: value for key, value in new['data'].items() if key != 'id'} == old['data']
    assert 'ROOT IDENTITY SELECTION' in new['merge_report']
    assert 'ROOT IDENTITY SELECTION' not in old['merge_report']


@pytest.mark.parametrize('field', ['', 'D4D: structural heading', 'title'])
@pytest.mark.parametrize('covered', ['0', '1'])
def test_ignored_or_wrong_field_marker_is_rejected_before_loader_skips(modules, tmp_path, field, covered):
    path = table(tmp_path / 'wrong-row.tsv', extra=[
        [field, 'str', 'identifier,@id', identity.MARKER, covered, '0']])
    before = path.read_bytes()
    with pytest.raises(ValueError, match='root_identifier_v1'):
        modules['mapping_loader'].MappingLoader(str(path))
    assert path.read_bytes() == before


@pytest.mark.parametrize('rows', [
    [['id', 'str', '@id,identifier', identity.MARKER, '1', '0']],
    [['id', 'str', 'identifier,@id,memberId', identity.MARKER, '1', '0']],
    [['id', 'str', 'identifier,@id', identity.MARKER, '0', '0']],
    [['id', 'str', 'identifier,@id', identity.MARKER, '1', '0'],
     ['id', 'str', 'customId', '', '1', '1']],
    [['id', 'str', 'identifier,@id', identity.MARKER, '1', '0'],
     ['id', 'str', 'identifier,@id', identity.MARKER, '1', '0']],
])
def test_incompatible_and_ambiguous_route_tables_refuse(modules, tmp_path, rows):
    mapping = table(tmp_path / 'conflicting.tsv', extra=rows)
    with pytest.raises(ValueError, match='root_identifier_v1'):
        modules['mapping_loader'].MappingLoader(str(mapping))


def test_unmarked_arbitrary_function_remains_inert_and_custom_id_is_not_normalized(modules, tmp_path):
    effect = tmp_path / 'not-created'
    expression = f"__import__('pathlib').Path({str(effect)!r}).touch()"
    mapping = table(tmp_path / 'custom-expression.tsv', expression)
    source = crate(tmp_path / 'input.json', {
        'identifier': 'https://doi.org/10.1234/MiXeD///', 'name': 'Source'})
    loader = modules['mapping_loader'].MappingLoader(str(mapping))
    parser = modules['rocrate_parser'].ROCrateParser(str(source))
    result = modules['d4d_builder'].D4DBuilder(loader).build_dataset(parser)
    assert result['id'] == 'https://doi.org/10.1234/MiXeD///'
    assert 'id' in identity.scoring_fields(loader)
    assert not effect.exists()


@pytest.mark.parametrize('source', [
    ' https://doi.org/10.1234/MiXeD///', 'doi:10.1234/MiXeD///\t',
    'https://example.org/?value=doi:10.1234/MiXeD///',
    'ark:/12345/Record%2fMiXeD///', 'https://doi.org/10.1234/Has space/',
])
def test_whole_value_recognition_preserves_outside_contract_text(modules, tmp_path, source):
    path = crate(tmp_path / 'input.json', {'identifier': source, 'name': 'Source'})
    before = path.read_bytes()
    loader = modules['mapping_loader'].MappingLoader(str(table(tmp_path / 'selected.tsv', 'marked')))
    parser = modules['rocrate_parser'].ROCrateParser(str(path))
    result = modules['d4d_builder'].D4DBuilder(loader).build_dataset(parser)
    assert result['id'] == source
    assert path.read_bytes() == before


def test_identity_evidence_detaches_even_unused_raw_input():
    root = {'identifier': 'https://doi.org/10.1234/MiXeD%2fPart///',
            '@id': {'source': ['retained unused assertion']}}
    before = deepcopy(root)
    evidence = identity.resolve_root_identity(root)
    assert evidence['id'] == 'doi:10.1234/MiXeD%2fPart///'
    assert evidence['source_property'] == 'identifier'
    assert evidence['source_value'] == root['identifier']
    assert evidence['inputs']['@id']['value'] == root['@id']
    evidence['inputs']['@id']['value']['source'].append('caller mutation')
    assert root == before


def test_reused_marked_merger_does_not_leak_identity_into_unmarked_no_id_table(modules, tmp_path):
    source = crate(tmp_path / 'input.json', {'identifier': 'ark:12345/retained', 'name': 'Source'})
    parser = modules['rocrate_parser'].ROCrateParser(str(source))
    marked = modules['mapping_loader'].MappingLoader(str(table(tmp_path / 'marked.tsv', 'marked')))
    old = modules['mapping_loader'].MappingLoader(str(table(tmp_path / 'old.tsv')))
    merger = modules['rocrate_merger'].ROCrateMerger(marked)
    assert merger.merge_rocrates([parser])['id'] == 'ark:12345/retained'
    assert merger.root_identity_sources is not None
    merger.mapping = old
    assert merger.merge_rocrates([parser]) == {'title': 'Source'}
    assert merger.root_identity_sources is None
    assert 'id' not in merger.provenance
