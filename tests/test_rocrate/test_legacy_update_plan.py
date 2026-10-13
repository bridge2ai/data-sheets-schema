"""Opted-in legacy maintenance text stays intact through both real producers."""
from copy import deepcopy
import json
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_update_plan import MARKER, SOURCE
from .test_legacy_root_identity import implementation, crate
from .test_legacy_root_gates import legacy_imports
from .test_legacy_publication import legacy


REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
TEXT = '  Quarterly; no inferred schedule.\nCafé — release notes retain this text.\n'
SENTINEL = b'Previously reviewed output\n'
ABSENT = object()


def table(tmp_path, *, marked=True, source=SOURCE, field_type='', extra=''):
    path = tmp_path / 'selected.tsv'
    path.write_text(
        f'D4D Property\tType\tFAIRSCAPE RO-Crate Property\tFunc\t{COVERED}\t'
        'Direct mapping? Yes =1; No = 0\n'
        'id\tURI\tidentifier,@id\troot_identifier_v1\t1\t0\n'
        'title\tstr\tname\t\t1\t1\n'
        f'updates\t{field_type}\t{source}\t{MARKER if marked else ""}\t1\t1\n'
        + extra, encoding='utf-8')
    return path


def input_file(path, value=ABSENT, *, reverse=False):
    root = {'@id': './', 'identifier': 'doi:10.1234/Source/', 'name': 'Selected root'}
    if value is not ABSENT:
        root[SOURCE] = deepcopy(value)
    crate(path, root, reverse=reverse)
    document = json.loads(path.read_text())
    for item in document['@graph']:
        if item.get('@id') == 'member':
            item[SOURCE] = 'Member plan must not become the root plan.'
    path.write_text(json.dumps(document), encoding='utf-8')
    return path


def build(implementation, path, mapping):
    parser = implementation['parser'].ROCrateParser(str(path))
    loader = implementation['loader'].MappingLoader(str(mapping))
    builder = implementation['builder'].D4DBuilder(loader)
    return builder.build_dataset(parser), parser, builder


def same_json(left, right):
    assert json.dumps(left, sort_keys=True, ensure_ascii=False) == json.dumps(
        right, sort_keys=True, ensure_ascii=False)


@pytest.mark.parametrize('text', ['', ' \t\n', TEXT, 'Annual/quarterly? "No commitment."'])
@pytest.mark.parametrize('reverse', [False, True])
def test_complete_scalar_text_and_actual_publication(implementation, tmp_path, text, reverse):
    source = input_file(tmp_path / 'input.json', text, reverse=reverse)
    mapping = table(tmp_path)
    before = {p: p.read_bytes() for p in (source, mapping)}
    record, _, _ = build(implementation, source, mapping)
    assert record == {'id': 'doi:10.1234/Source/', 'title': 'Selected root',
                      'updates': {'update_details': text}}
    output = tmp_path / 'dataset.yaml'
    publication.publish([(output, publication.prepare_dataset(record))], protected=[source, mapping])
    assert yaml.safe_load(output.read_bytes()) == record
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('field_type', ['int', 'bool', 'date', 'list[str]', 'URI'])
def test_explicit_constructor_precedes_generic_type_coercion(implementation, tmp_path, field_type):
    record, _, _ = build(implementation, input_file(tmp_path / 'input.json', TEXT),
                         table(tmp_path, field_type=field_type))
    assert record['updates'] == {'update_details': TEXT}


@pytest.mark.parametrize('value', [None, ABSENT])
@pytest.mark.parametrize('reverse', [False, True])
def test_absent_root_does_not_borrow_member_plan(implementation, tmp_path, value, reverse):
    record, _, _ = build(implementation, input_file(tmp_path / 'input.json', value, reverse=reverse), table(tmp_path))
    assert 'updates' not in record
    publication.prepare_dataset(record)


@pytest.mark.parametrize('value', [False, 0, 1, [], ['same', 'same'], [TEXT, False],
    [{'update_details': TEXT}], {'unrecognized': [False, 0, TEXT]},
    {'update_details': TEXT, 'frequency': ['quarterly', 'monthly']}])
def test_nontext_assertions_remain_complete_and_gate_refuses(implementation, tmp_path, value):
    source = input_file(tmp_path / 'input.json', value)
    record, parser, _ = build(implementation, source, table(tmp_path))
    same_json(record['updates'], value)
    output = tmp_path / 'dataset.yaml'; output.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError, match='updates'):
        publication.publish([(output, publication.prepare_dataset(record))], protected=[source])
    assert output.read_bytes() == SENTINEL
    same_json(parser.require_root_dataset()[SOURCE], value)
    if isinstance(record['updates'], dict):
        record['updates']['added_after_build'] = True
        assert 'added_after_build' not in parser.require_root_dataset()[SOURCE]
    elif isinstance(record['updates'], list):
        record['updates'].append('mutation')
        same_json(parser.require_root_dataset()[SOURCE], value)


def test_full_valid_dictionary_and_nested_mutation_isolation(implementation, tmp_path):
    value = {'update_details': TEXT, 'frequency': 'As explicitly stated', 'description': 'Separate assertion'}
    record, parser, builder = build(implementation, input_file(tmp_path / 'input.json', value), table(tmp_path))
    same_json(record['updates'], value)
    publication.prepare_dataset(record)
    record['updates']['update_details'] = 'mutated result'
    same_json(parser.require_root_dataset()[SOURCE], value)
    assert builder.build_dataset(parser)['updates'] == value
    malformed = {'update_details': TEXT, 'foreign': {'values': [False, 0, 'repeat', 'repeat']}}
    record, parser, _ = build(implementation, input_file(tmp_path / 'nested.json', malformed), table(tmp_path))
    record['updates']['foreign']['values'].append('changed')
    same_json(parser.require_root_dataset()[SOURCE], malformed)


@pytest.mark.parametrize('change', ['wrong_target', 'header_target', 'blank_target', 'uncovered',
    'wrong_source', 'multiple_sources', 'duplicate_marked', 'competing_unmarked'])
def test_invalid_marked_routes_refuse_before_filtering_or_shadowing(implementation, tmp_path, change):
    mapping = table(tmp_path)
    text = mapping.read_text()
    line = f'updates\t\t{SOURCE}\t{MARKER}\t1\t1\n'
    replacements = {
        'wrong_target': line.replace('updates\t', 'title\t', 1),
        'header_target': line.replace('updates\t', 'D4D: header\t', 1),
        'blank_target': line.replace('updates\t', '\t', 1),
        'uncovered': line.replace('\t1\t1\n', '\t0\t1\n'),
        'wrong_source': line.replace(SOURCE, 'unrelated'),
        'multiple_sources': line.replace(SOURCE, SOURCE + ',alternate'),
        'duplicate_marked': line + line,
        'competing_unmarked': line + 'updates\t\talternate\t\t1\t1\n',
    }
    mapping.write_text(text.replace(line, replacements[change]))
    with pytest.raises(ValueError, match='update_plan_narrative_v1 requires one covered updates row'):
        implementation['loader'].MappingLoader(str(mapping))


def test_mutated_invalid_route_refuses_before_builder_state_reset(implementation, tmp_path):
    mapping = table(tmp_path); source = input_file(tmp_path / 'input.json', TEXT)
    previous, parser, builder = build(implementation, source, mapping)
    before = deepcopy(previous)
    builder.mapping.mappings.append({'D4D Property': 'updates', COVERED: '1',
                                     'FAIRSCAPE RO-Crate Property': 'alternate'})
    with pytest.raises(ValueError, match='maintenance routes'):
        builder.build_dataset(parser)
    assert builder.d4d_data == before


@pytest.mark.parametrize('unknown_func', ['', 'custom_function_not_executed'])
def test_unmarked_custom_route_preserves_legacy_behavior(implementation, tmp_path, unknown_func):
    mapping = table(tmp_path, marked=False, source='customPlan')
    mapping.write_text(mapping.read_text().replace('customPlan\t\t1', f'customPlan\t{unknown_func}\t1'))
    source = input_file(tmp_path / 'input.json', 'Default source is not selected')
    document = json.loads(source.read_text())
    next(item for item in document['@graph'] if item.get('@id') == './')['customPlan'] = {'update_details': TEXT}
    source.write_text(json.dumps(document))
    record, _, _ = build(implementation, source, mapping)
    assert record['updates'] == str({'update_details': TEXT})
    with pytest.raises(publication.PublicationError):
        publication.prepare_dataset(record)


def test_default_table_marker_preserves_other_columns_and_root_id(implementation, tmp_path):
    record, _, _ = build(implementation, input_file(tmp_path / 'input.json', TEXT), DEFAULT)
    assert record['updates'] == {'update_details': TEXT}
    assert record['id'] == 'doi:10.1234/Source/' and record['doi'] == '10.1234/Source/'
    loader = implementation['loader'].MappingLoader(str(DEFAULT))
    route = loader.get_mapping_info('updates')
    assert route['Func'] == MARKER and route['FAIRSCAPE RO-Crate Property'] == SOURCE
    assert route['Mapping_Type'] == 'exactMatch' and route['Information_Loss'] == 'none'
    # These are preserved historical declarations, not scientific acceptance.
    publication.prepare_dataset(record)


@pytest.mark.parametrize('primary', [TEXT, '', {'update_details': '', 'frequency': 'Unknown'}, False, 0, []])
def test_merger_keeps_whole_present_primary_without_object_combination(implementation, tmp_path, primary):
    mapping = table(tmp_path)
    sources = [input_file(tmp_path / 'primary.json', primary),
               input_file(tmp_path / 'secondary.json', {'update_details': 'Secondary', 'frequency': 'Monthly'})]
    parsers = [implementation['parser'].ROCrateParser(str(p)) for p in sources]
    before = deepcopy([p.require_root_dataset() for p in parsers])
    merger = implementation['merger'].ROCrateMerger(implementation['loader'].MappingLoader(str(mapping)))
    record = merger.merge_rocrates(parsers, source_names=['Primary', 'Secondary'])
    expected = {'update_details': primary} if isinstance(primary, str) else primary
    same_json(record['updates'], expected)
    assert merger.get_provenance()['updates'] == ['Primary']
    if isinstance(record['updates'], dict):
        record['updates']['changed'] = True
    assert [p.require_root_dataset() for p in parsers] == before
    fresh = implementation['merger'].ROCrateMerger(implementation['loader'].MappingLoader(str(mapping)))
    same_json(fresh.merge_rocrates(parsers)['updates'], expected)


@pytest.mark.parametrize('primary', [None, ABSENT])
def test_merger_absence_uses_first_nonnull_secondary_in_existing_order(implementation, tmp_path, primary):
    mapping = table(tmp_path)
    sources = [input_file(tmp_path / f'{i}.json', v) for i, v in enumerate([primary, None, 'First', 'Second'])]
    parsers = [implementation['parser'].ROCrateParser(str(p)) for p in sources]
    merger = implementation['merger'].ROCrateMerger(implementation['loader'].MappingLoader(str(mapping)))
    record = merger.merge_rocrates(parsers, source_names=['Primary', 'Absent', 'First', 'Second'])
    assert record['updates'] == {'update_details': 'First'}
    assert merger.get_provenance()['updates'] == ['First']


def test_scorer_ranks_and_merge_accounting_match_unmarked_table(implementation, tmp_path):
    path = table(tmp_path); old_path = tmp_path / 'unmarked.tsv'
    old_path.write_text(path.read_text().replace(MARKER, ''))
    sources = [input_file(tmp_path / f'{i}.json', v) for i, v in enumerate([TEXT, None, 'Secondary'])]
    parsers = [implementation['parser'].ROCrateParser(str(p)) for p in sources]
    loaders = [implementation['loader'].MappingLoader(str(p)) for p in (old_path, path)]
    scorer = implementation['scorer'].InformativenessScorer()
    assert scorer.rank_rocrates(parsers, loaders[0]) == scorer.rank_rocrates(parsers, loaders[1])
    for primary in (0, 1):
        mergers = [implementation['merger'].ROCrateMerger(mapping) for mapping in loaders]
        records = [merger.merge_rocrates(parsers, primary_index=primary, source_names=['A','B','C']) for merger in mergers]
        assert records[1]['updates'] == {'update_details': records[0]['updates']}
        assert {k:v for k,v in records[0].items() if k!='updates'} == {k:v for k,v in records[1].items() if k!='updates'}
        assert mergers[0].get_provenance() == mergers[1].get_provenance()
        assert mergers[0].get_merge_stats() == mergers[1].get_merge_stats()


@pytest.mark.parametrize('entrypoint', ['packaged', 'd4d'])
@pytest.mark.parametrize('value', [TEXT, {'foreign': [False, 0]}, False])
def test_real_cli_gate_and_existing_output_sentinel(tmp_path, monkeypatch, entrypoint, value):
    mapping = table(tmp_path); source = input_file(tmp_path / 'input.json', value)
    output = tmp_path / 'dataset.yaml'; output.write_bytes(SENTINEL)
    before = {p:p.read_bytes() for p in (source,mapping)}
    monkeypatch.chdir(REPO)
    with legacy_imports():
        if entrypoint == 'packaged':
            from fairscape_integration.cli import cli
            command = ['transform',str(source),'-m',str(mapping),'-o',str(output)]
        else:
            from data_sheets_schema.cli import cli
            command = ['rocrate','transform',str(source),'--mapping',str(mapping),'-o',str(output)]
        result = CliRunner().invoke(cli, command)
    if isinstance(value, str):
        assert result.exit_code == 0, result.output
        assert yaml.safe_load(output.read_bytes())['updates'] == {'update_details': value}
    else:
        assert result.exit_code == 1 and 'Dataset publication refused' in result.output
        assert output.read_bytes() == SENTINEL
    assert {p:p.read_bytes() for p in before} == before


def test_api_later_invalid_batch_preserves_all_outputs(legacy, tmp_path):
    _, _, api = legacy
    mapping = table(tmp_path)
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    good = input_file(inputs / 'a_good.json', TEXT)
    bad = input_file(inputs / 'z_bad.json', {'unknown': [TEXT, False]})
    directory = tmp_path / 'published'; directory.mkdir()
    first = directory / 'a_good_d4d.yaml'; second = directory / 'z_bad_d4d.yaml'
    first.write_bytes(SENTINEL); second.write_bytes(SENTINEL)
    before = {p:p.read_bytes() for p in (good,bad,mapping,first,second)}
    with pytest.raises(publication.PublicationError, match='updates'):
        api.batch_transform_rocrates(inputs, output_dir=directory, mapping_file=mapping,
                                    validate=False, result_contract='dataset_v1')
    assert {p:p.read_bytes() for p in before} == before
    assert sorted(p.name for p in directory.iterdir()) == sorted([first.name,second.name])
