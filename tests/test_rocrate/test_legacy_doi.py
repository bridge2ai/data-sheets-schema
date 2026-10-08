"""Both real legacy constructors retain evidence while repairing only DOI form."""
from copy import deepcopy
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from .test_legacy_root_gates import legacy_imports


REPO = Path(__file__).resolve().parents[2]
BARE = '10.1234/MixedCase'
ID = 'https://example.org/retained-record'
SENTINEL = b'previous reviewed output\n'
MISSING = object()


@pytest.fixture(params=['packaged', 'hidden'])
def implementation(request):
    if request.param == 'hidden':
        with legacy_imports():
            yield tuple(importlib.import_module(name) for name in
                        ('d4d_builder', 'mapping_loader', 'rocrate_parser'))
    else:
        yield tuple(importlib.import_module('fairscape_integration.utils.' + name)
                    for name in ('d4d_builder', 'mapping_loader', 'rocrate_parser'))


def mapping(tmp_path, *, properties='identifier', field_type='URI', include_id=True):
    path = tmp_path / 'selected.tsv'
    path.write_text(
        'D4D Property\tType\tFAIRSCAPE RO-Crate Property\t'
        'Covered by FAIRSCAPE? Yes =1; No = 0\tDirect mapping? Yes =1; No = 0\n'
        + ('id\tstr\trecordId\t1\t1\n' if include_id else '')
        + f'doi\t{field_type}\t{properties}\t1\t1\n'
        + 'title\tstr\tname\t1\t1\n'
        + 'download_url\turi\tcontentUrl\t1\t1\n', encoding='utf-8')
    return path


def crate(tmp_path, value=MISSING, *, second=MISSING, reverse=False, name='input.json'):
    root = {'@id': './', '@type': 'Dataset', 'recordId': ID, 'name': 'Source title',
            'contentUrl': 'https://example.org/retained-download'}
    if value is not MISSING:
        root['identifier'] = deepcopy(value)
    if second is not MISSING:
        root['alternateIdentifier'] = deepcopy(second)
    graph = [
        {'@id': 'ro-crate-metadata.json', '@type': 'CreativeWork', 'about': {'@id': './'}},
        root,
        {'@id': 'child', '@type': 'Dataset', 'identifier': '10.5678/Member',
         'alternateIdentifier': '10.5678/OtherMember'},
    ]
    path = tmp_path / name
    path.write_text(json.dumps({'@graph': graph[::-1] if reverse else graph}), encoding='utf-8')
    return path


def build(implementation, source, table):
    builder, loader, parser = implementation
    return builder.D4DBuilder(loader.MappingLoader(str(table))).build_dataset(
        parser.ROCrateParser(str(source)))


@pytest.mark.parametrize('prefix', ['', 'doi:', 'DOI:', 'http://doi.org/',
    'https://doi.org/', 'http://dx.doi.org/', 'https://dx.doi.org/', 'HTTPS://DOI.ORG/'])
def test_real_builders_normalize_scalar_doi_and_validate(implementation, tmp_path, prefix):
    source, table = crate(tmp_path, prefix + BARE), mapping(tmp_path)
    before = {p: p.read_bytes() for p in (source, table)}
    record = build(implementation, source, table)
    assert record['doi'] == BARE
    assert record['download_url'] == 'https://example.org/retained-download'
    assert yaml.safe_load(publication.prepare_dataset(record)) == record
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('value', ['10.1234567890/LongRegistrant', '10.1234/Space suffix',
    '10.1234/Tab\tsuffix', '10.1234/Trailing/'])
def test_schema_valid_bare_values_are_not_narrowed_or_trimmed(implementation, tmp_path, value):
    record = build(implementation, crate(tmp_path, value), mapping(tmp_path))
    assert record['doi'] == value
    assert yaml.safe_load(publication.prepare_dataset(record))['doi'] == value


@pytest.mark.parametrize('prefix', ['doi:', 'DOI:', 'http://doi.org/',
    'https://doi.org/', 'http://dx.doi.org/', 'https://dx.doi.org/', 'HTTPS://DOI.ORG/'])
@pytest.mark.parametrize('suffix', ['Record/', 'MiXeD/Part///'])
def test_prefixed_suffix_slashes_survive_real_construction_and_publication(
        implementation, tmp_path, prefix, suffix):
    """#4671: recognition must not delete the source DOI's suffix ending."""
    expected = '10.1234/' + suffix
    source, table = crate(tmp_path, prefix + expected), mapping(tmp_path)
    before = {path: path.read_bytes() for path in (source, table)}
    record = build(implementation, source, table)
    assert record['doi'] == expected
    raw = publication.prepare_dataset(record)
    output = tmp_path / 'record.yaml'
    publication.publish([(output, raw)], protected=[source, table])
    assert output.read_bytes() == raw
    assert yaml.safe_load(output.read_bytes())['doi'] == expected
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize('prefix', ['DOI:', 'https://dx.doi.org/'])
def test_outer_whitespace_does_not_remove_suffix_slashes(implementation, tmp_path, prefix):
    expected = '10.1234/MiXeD/Part///'
    record = build(implementation, crate(tmp_path, ' \t' + prefix + expected + '\t\n'),
                   mapping(tmp_path))
    assert record['doi'] == expected
    assert yaml.safe_load(publication.prepare_dataset(record))['doi'] == expected


INVALID = ['', '10.', '10.123/x', 'not a DOI', 'ark:12345/record',
    'https://example.org/?persistentId=doi:10.1234/Example',
    'https://doi.org/10.1234/two words', 'doi:10.1234///',
    'https://example.org/10.1234/Record///', ' 10.1234/NoPrefix/ ',
    {'@id': 'doi:' + BARE}, False, 0,
    [], [BARE], [BARE, BARE], [BARE, '10.5678/Conflicting'], [BARE, None],
    ['not DOI', 'doi:' + BARE]]


@pytest.mark.parametrize('value', INVALID)
def test_invalid_and_list_assertions_survive_draft_and_fail_publication(
        implementation, tmp_path, value):
    source, table = crate(tmp_path, value), mapping(tmp_path)
    before = source.read_bytes()
    record = build(implementation, source, table)
    assert type(record['doi']) is type(value) and record['doi'] == value
    with pytest.raises(publication.PublicationError, match='doi|DOI'):
        publication.prepare_dataset(record)
    assert source.read_bytes() == before


@pytest.mark.parametrize('field_type', ['', 'str', 'int', 'bool', 'list[str]', 'date', 'SomeEnum'])
def test_stale_tsv_type_cannot_override_the_doi_slot(implementation, tmp_path, field_type):
    record = build(implementation, crate(tmp_path, 'doi:' + BARE),
                   mapping(tmp_path, field_type=field_type))
    assert record['doi'] == BARE


@pytest.mark.parametrize('second', ['10.5678/Other', BARE.lower(), 'doi:' + BARE,
    'not DOI', False, [BARE]])
@pytest.mark.parametrize('reverse', [False, True])
def test_competing_root_properties_refuse_in_either_mapping_and_graph_order(
        implementation, tmp_path, second, reverse):
    names = ['identifier', 'alternateIdentifier']
    source = crate(tmp_path, BARE, second=second, reverse=reverse)
    table = mapping(tmp_path, properties=','.join(names[::-1] if reverse else names))
    before = {p: p.read_bytes() for p in (source, table)}
    with pytest.raises(ValueError, match='Conflicting DOI source assertions'):
        build(implementation, source, table)
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('value,second,expected', [
    (MISSING, MISSING, MISSING), (None, BARE, BARE), (BARE, BARE, BARE)])
def test_missing_root_never_uses_member_and_identical_sources_need_no_choice(
        implementation, tmp_path, value, second, expected):
    table = mapping(tmp_path, properties='identifier,alternateIdentifier')
    record = build(implementation, crate(tmp_path, value, second=second, reverse=True), table)
    if expected is MISSING:
        assert 'doi' not in record
    else:
        assert record['doi'] == expected


def test_retained_draft_objects_do_not_alias_parser_input(implementation, tmp_path):
    builder, loader, parser_module = implementation
    parser = parser_module.ROCrateParser(str(crate(tmp_path, [{'@id': 'doi:' + BARE}])))
    before = deepcopy(parser.require_root_dataset())
    record = builder.D4DBuilder(loader.MappingLoader(str(mapping(tmp_path)))).build_dataset(parser)
    record['doi'][0]['@id'] = 'changed local draft'
    assert parser.require_root_dataset() == before


@pytest.mark.parametrize('entrypoint', ['packaged', 'hidden'])
@pytest.mark.parametrize('kind', ['valid', 'malformed', 'list', 'conflict', 'missing_id'])
def test_real_publishers_preserve_destinations_on_unaccepted_doi(
        tmp_path, monkeypatch, entrypoint, kind):
    value = {'valid': 'doi:' + BARE, 'malformed': 'not DOI', 'list': [BARE],
             'conflict': BARE, 'missing_id': 'doi:' + BARE}[kind]
    source = crate(tmp_path, value, second='10.5678/Other' if kind == 'conflict' else MISSING)
    table = mapping(tmp_path, properties='identifier,alternateIdentifier', include_id=kind != 'missing_id')
    output = tmp_path / 'record.yaml'
    report = output.with_name('record_report.txt' if entrypoint == 'packaged'
                              else 'transformation_report.txt')
    output.write_bytes(SENTINEL); report.write_bytes(SENTINEL)
    before = {p: p.read_bytes() for p in (source, table)}
    if entrypoint == 'packaged':
        from fairscape_integration.cli import cli
        result = CliRunner().invoke(cli, ['transform', str(source), '-m', str(table),
                                         '-o', str(output), '--report'])
        status = result.exit_code
    else:
        with legacy_imports():
            single = importlib.import_module('rocrate_to_d4d')
            monkeypatch.setattr(sys, 'argv', ['transform', '--input', str(source),
                '-m', str(table), '-o', str(output)])
            status = single.main()
    if kind == 'valid':
        assert status == 0
        assert yaml.safe_load(output.read_bytes())['doi'] == BARE
    else:
        assert status == 1
        assert output.read_bytes() == report.read_bytes() == SENTINEL
    assert {p: p.read_bytes() for p in before} == before


def test_actual_default_table_constructs_root_id_without_changing_bare_doi(implementation, tmp_path):
    table = REPO / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
    before = table.read_bytes()
    record = build(implementation, crate(tmp_path, 'doi:' + BARE), table)
    assert record['doi'] == BARE and record['id'] == 'doi:' + BARE
    assert yaml.safe_load(publication.prepare_dataset(record)) == record
    assert table.read_bytes() == before


@pytest.mark.parametrize('late_invalid', [False, True])
def test_real_api_batch_validates_all_dois_before_first_publication(tmp_path, late_invalid):
    inputs, output = tmp_path / 'inputs', tmp_path / 'outputs'
    inputs.mkdir(); output.mkdir()
    sources = [crate(inputs, 'doi:' + BARE, name='a.json'),
               crate(inputs, [BARE, None] if late_invalid else 'https://doi.org/' + BARE,
                     name='z.json')]
    table = mapping(tmp_path)
    destinations = [output / f'{source.stem}_d4d.yaml' for source in sources]
    for destination in destinations:
        destination.write_bytes(SENTINEL)
    before = {path: path.read_bytes() for path in [*sources, table]}
    with legacy_imports():
        spec = importlib.util.spec_from_file_location('_root_gates_transform_api',
            REPO / 'src/transformation/transform_api.py')
        api = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)
        def publish_batch():
            return api.batch_transform_rocrates(inputs, output, validate=False,
                mapping_file=table, result_contract='dataset_v1')
        if late_invalid:
            with pytest.raises(publication.PublicationError, match='z.json.*doi'):
                publish_batch()
            assert [path.read_bytes() for path in destinations] == [SENTINEL, SENTINEL]
        else:
            assert len(publish_batch()) == 2
            assert [yaml.safe_load(path.read_bytes())['doi'] for path in destinations] == [BARE, BARE]
    assert {path: path.read_bytes() for path in before} == before


def test_hidden_builder_direct_script_keeps_source_checkout_import(tmp_path):
    source, table = crate(tmp_path, 'doi:' + BARE), mapping(tmp_path)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONPATH', None)
    result = subprocess.run([sys.executable, '-B',
        str(REPO / '.claude/agents/scripts/d4d_builder.py'), str(table), str(source)],
        cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert f'doi: {BARE}' in result.stdout
