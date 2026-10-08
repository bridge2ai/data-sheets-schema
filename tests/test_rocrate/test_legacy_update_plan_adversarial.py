"""Independent UpdatePlan controls for precedence and coverage compatibility.

These retain real loaders, parsers, builders, mergers, scorers and API results.
Invalid first-secondary assertions must remain visible through final validation.
"""
from copy import deepcopy
import json

import pytest

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_root_identity import scoring_fields
from data_sheets_schema.legacy_update_plan import MARKER, SOURCE
from .test_legacy_publication import legacy
from .test_legacy_root_identity import implementation
from .test_legacy_update_plan import TEXT, build, input_file, table


def encoded(value):
    """Distinguish false/zero and preserve complete list/object contents."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


@pytest.mark.parametrize('first', [False, 0, [], {}, '',
    {'update_details': TEXT, 'unknown': {'values': [False, 0, 'repeat', 'repeat']}}])
def test_nonzero_primary_uses_first_present_secondary_even_if_invalid(
        implementation, tmp_path, first):
    mapping = table(tmp_path)
    sources = [input_file(tmp_path / f'{i}.json', value) for i, value in enumerate([
        first, {'update_details': 'Later valid plan', 'frequency': 'Monthly'}, None])]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in sources]
    before = [deepcopy(parser.require_root_dataset()) for parser in parsers]
    merger = implementation['merger'].ROCrateMerger(
        implementation['loader'].MappingLoader(str(mapping)))
    result = merger.merge_rocrates(parsers, primary_index=2,
                                   source_names=['First', 'Later', 'Selected'])
    expected = {'update_details': first} if isinstance(first, str) else first
    assert encoded(result['updates']) == encoded(expected)
    assert merger.get_provenance()['updates'] == ['First']
    assert merger.primary_index == 2 and merger.primary_name == 'Selected'
    assert merger.get_provenance()['id'] == ['Selected']
    if isinstance(first, (bool, int, list)) or isinstance(first, dict) and 'unknown' in first:
        output = tmp_path / 'existing.yaml'
        output.write_bytes(b'reviewed sentinel\n')
        with pytest.raises(publication.PublicationError, match='updates'):
            publication.publish([(output, publication.prepare_dataset(result))],
                                protected=[mapping, *sources])
        assert output.read_bytes() == b'reviewed sentinel\n'
    assert encoded([p.require_root_dataset() for p in parsers]) == encoded(before)


def test_selected_nested_object_is_detached_across_reused_merger_runs(implementation, tmp_path):
    value = {'update_details': TEXT, 'unknown': {'array': [False, 0, {'text': 'source'}]}}
    sources = [input_file(tmp_path / 'absent.json', None),
               input_file(tmp_path / 'selected.json', value),
               input_file(tmp_path / 'other.json', {'frequency': 'Unselected'})]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in sources]
    mapping = table(tmp_path)
    merger = implementation['merger'].ROCrateMerger(
        implementation['loader'].MappingLoader(str(mapping)))
    before = [deepcopy(p.require_root_dataset()) for p in parsers]
    first = merger.merge_rocrates(parsers, source_names=['Absent', 'Selected', 'Other'])
    provenance, stats = deepcopy(merger.get_provenance()), merger.get_merge_stats()
    first['updates']['unknown']['array'][2]['text'] = 'caller mutation'
    first['updates']['unknown']['array'].append('extra')
    assert encoded([p.require_root_dataset() for p in parsers]) == encoded(before)
    second = merger.merge_rocrates(parsers, source_names=['Absent', 'Selected', 'Other'])
    assert encoded(second['updates']) == encoded(value)
    assert 'frequency' not in second['updates']
    assert merger.get_provenance() == provenance
    assert merger.get_merge_stats() == stats


@pytest.mark.parametrize('function', [MARKER.upper(), MARKER + '_other', 'expression'])
def test_similar_names_and_expressions_do_not_activate_or_execute(implementation, tmp_path, function):
    marker = tmp_path / 'unexecuted'
    if function == 'expression':
        function = f"__import__('pathlib').Path({str(marker)!r}).touch()"
    mapping = table(tmp_path)
    mapping.write_text(mapping.read_text().replace(MARKER, function), encoding='utf-8')
    value = {'update_details': TEXT, 'unknown': [False, 0]}
    result, _, _ = build(implementation, input_file(tmp_path / 'source.json', value), mapping)
    assert result['updates'] == str(value)
    assert not marker.exists()


def test_unmarked_first_duplicate_cannot_hide_later_named_route(implementation, tmp_path):
    mapping = table(tmp_path)
    marked = f'updates\t\t{SOURCE}\t{MARKER}\t1\t1\n'
    mapping.write_text(mapping.read_text().replace(
        marked, 'updates\tstr\talternative\t\t1\t1\n' + marked), encoding='utf-8')
    original = mapping.read_bytes()
    with pytest.raises(ValueError, match='update_plan_narrative_v1'):
        implementation['loader'].MappingLoader(str(mapping))
    assert mapping.read_bytes() == original


@pytest.mark.parametrize('row', [
    f'updates\t\t{SOURCE}\t{MARKER}\n',
    f'\t\t{SOURCE}\t{MARKER}\t1\t1\n',
    f'D4D: skipped\t\t{SOURCE}\t{MARKER}\t1\t1\n',
])
def test_truncated_or_skipped_marker_declarations_refuse(implementation, tmp_path, row):
    mapping = table(tmp_path)
    marked = f'updates\t\t{SOURCE}\t{MARKER}\t1\t1\n'
    mapping.write_text(mapping.read_text().replace(marked, row), encoding='utf-8')
    with pytest.raises(ValueError, match='update_plan_narrative_v1'):
        implementation['loader'].MappingLoader(str(mapping))


@pytest.mark.parametrize('contract', ['legacy', 'dataset_v1'])
@pytest.mark.parametrize('value', [TEXT, None, False, []])
def test_api_coverage_still_counts_updates_and_excludes_only_identity(legacy, tmp_path, contract, value):
    _, _, api = legacy
    marked = table(tmp_path, extra='version\tstr\tmissingVersion\t\t1\t1\n')
    unmarked = tmp_path / 'unmarked.tsv'
    unmarked.write_text(marked.read_text().replace(MARKER, ''), encoding='utf-8')
    source = input_file(tmp_path / 'source.json', value)
    results = []
    for mapping in (unmarked, marked):
        transformer = api.SemanticTransformer(api.TransformationConfig(
            mapping_file=mapping, validate_input=False, validate_output=False,
            result_contract=contract))
        assert scoring_fields(transformer.mapping_loader) == ['title', 'updates', 'version']
        results.append(transformer.rocrate_to_d4d(source))
    old, new = results
    assert old.coverage_percentage == new.coverage_percentage
    assert new.coverage_percentage == pytest.approx((1 if value is None else 2) / 3 * 100)
    assert old.unmapped_fields == new.unmapped_fields == (
        ['updates', 'version'] if value is None else ['version'])
    for result in results:
        assert result.transformation_metadata['coverage_percentage'] == result.coverage_percentage
        assert result.transformation_metadata['unmapped_fields'] == result.unmapped_fields
    if value is not None:
        expected = {'update_details': value} if isinstance(value, str) else value
        assert encoded(new.data['updates']) == encoded(expected)
    assert new.data['id'] == old.data['id'] == 'doi:10.1234/Source/'


def test_full_scores_keep_update_marker_contribution_for_false_and_missing_roots(implementation, tmp_path):
    marked = table(tmp_path)
    unmarked = tmp_path / 'unmarked.tsv'
    unmarked.write_text(marked.read_text().replace(MARKER, ''), encoding='utf-8')
    paths = [input_file(tmp_path / f'{i}.json', value) for i, value in enumerate([False, None, TEXT])]
    parsers = [implementation['parser'].ROCrateParser(str(path)) for path in paths]
    scorer = implementation['scorer'].InformativenessScorer()
    ranks = []
    for mapping in (unmarked, marked):
        loader = implementation['loader'].MappingLoader(str(mapping))
        assert scoring_fields(loader) == ['title', 'updates']
        assert scorer.score_rocrate(parsers[0], loader)['d4d_coverage'] == 2
        assert scorer.score_rocrate(parsers[1], loader)['d4d_coverage'] == 1
        ranks.append(scorer.rank_rocrates(parsers, loader))
    assert ranks[0] == ranks[1]
