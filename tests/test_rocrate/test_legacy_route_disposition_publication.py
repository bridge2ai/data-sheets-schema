"""Marked route acquisition, API transport and real publication boundaries."""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema import legacy_route_dispositions as policy
from .test_legacy_publication import legacy
from .test_legacy_root_identity import implementation
from .test_legacy_route_dispositions_core import table, source, build, assert_json, pointer


RAW = ['whole task', {'a/b~c': ['\ud800', '\U0001f600']}, 'whole task']
SENTINEL = b'previous reviewed artifact\n'


def mapping(tmp_path, *, marked=True):
    return table(tmp_path, [('tasks', 'rai:dataUseCases'), ('version_access', 'version')], marked=marked)


def sidecar(path):
    return path.with_name(path.stem + '_route_dispositions.json')


def assert_recovered(evidence):
    # Includes generated snapshots: their bytes are explicitly labelled as
    # generated, and parent originals are independently checked below.
    for occurrence in evidence['sources']:
        snapshot = occurrence['snapshot']
        raw = snapshot['json_text'].encode('utf-8')
        assert snapshot['serialization'] == {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
        if snapshot['original_file'] is not None:
            assert Path(snapshot['original_file']['path']).read_bytes() == raw
        data = json.loads(raw)
        assert pointer(data, snapshot['root_pointer'])['@id'] == './'
        assert set(occurrence['routes']) == {'tasks', 'version_access'}
        for field, prop in [('tasks', 'rai:dataUseCases'), ('version_access', 'version')]:
            assertions = occurrence['routes'][field]
            assert len(assertions) == 1 and assertions[0]['property'] == prop
            assertion = assertions[0]
            if assertion['present']:
                assert_json(pointer(data, assertion['pointer']), assertion['raw'])
            else:
                assert 'raw' not in assertion
            for unit in assertion['units']:
                assert_json(pointer(data, unit['pointer']), unit['raw'])


def check_bundle(path, expected_raw=RAW):
    raw = path.read_bytes()
    record = yaml.safe_load(raw)
    assert publication.prepare_dataset(record, text=raw.decode('utf-8')) == raw
    wire = sidecar(path).read_bytes()
    assert wire.isascii()
    document = json.loads(wire)
    assert document['dataset'] == {'path': str(path.resolve()), 'bytes': len(raw),
                                   'sha256': sha256(raw).hexdigest()}
    assert document['schema']['sha256'] == sha256(Path(document['schema']['path']).read_bytes()).hexdigest()
    evidence = document['evidence']
    assert evidence['sources'][0]['routes']['tasks'][0]['raw'] == expected_raw
    assert_recovered(evidence)
    return record, evidence


def transformer(api, path, *, preserve=False, contract='dataset_v1'):
    return api.SemanticTransformer(api.TransformationConfig(mapping_file=path,
        validate_input=False, validate_output=False, preserve_provenance=preserve,
        result_contract=contract))


@pytest.mark.parametrize('object_graph', [False, True])
def test_generated_dict_snapshot_survives_temp_deletion(implementation, tmp_path, object_graph):
    path = source(tmp_path / 'temporary.json', {'rai:dataUseCases': RAW})
    data = json.loads(path.read_bytes())
    if object_graph:
        data['@graph'] = next(row for row in data['@graph'] if row.get('@id') == './')
        path.write_text(json.dumps(data), encoding='utf-8')
    parser = implementation['parser'].ROCrateParser(str(path))
    snapshot = policy.source_snapshot(parser, raw=path.read_bytes(), kind='generated_dict', input_value=data)
    path.unlink()
    parser.rocrate_path = tmp_path / 'future-output.json'
    parser.rocrate_path.write_bytes(SENTINEL)
    loader = implementation['loader'].MappingLoader(str(mapping(tmp_path)))
    builder = implementation['builder'].D4DBuilder(loader)
    record = builder.build_dataset(parser, source_snapshot=snapshot)
    evidence = builder.get_route_dispositions()
    assert evidence['sources'][0]['snapshot']['original_file'] is None
    assert evidence['sources'][0]['snapshot']['kind'] == 'generated_dict'
    assert evidence['sources'][0]['snapshot']['root_pointer'] == ('/@graph' if object_graph else snapshot['root_pointer'])
    policy.validate_evidence(evidence, record, loader)
    assert parser.rocrate_path.read_bytes() == SENTINEL


def test_explicit_reordering_has_new_pointers_and_verified_old_occurrences(implementation, tmp_path):
    path = source(tmp_path / 'source.json', {'rai:dataUseCases': RAW})
    parser = implementation['parser'].ROCrateParser(str(path))
    parent = policy.source_snapshot(parser)
    old_pointer = parent['root_pointer']
    permutation = [1, 2, 0]
    assert len(parser.graph) == 3
    parser.graph[:] = [parser.graph[i] for i in permutation]
    loader = implementation['loader'].MappingLoader(str(mapping(tmp_path)))
    builder = implementation['builder'].D4DBuilder(loader)
    with pytest.raises(ValueError, match='source'):
        builder.build_dataset(parser)
    snapshot = policy.source_snapshot(parser, kind='declared_reordered_graph',
                                     parents=[parent], permutation=permutation)
    record = builder.build_dataset(parser, source_snapshot=snapshot)
    evidence = builder.get_route_dispositions()
    assert snapshot['root_pointer'] != old_pointer
    assert len(snapshot['entity_origins']) == len(permutation)
    for index, old_index in enumerate(permutation):
        assert snapshot['entity_origins'][index]['original_pointer'] == '/@graph/' + str(old_index)
    assert_recovered(evidence)
    policy.validate_evidence(evidence, record, loader)
    snapshot['entity_origins'][0]['original_pointer'] = '/@graph/999'
    with pytest.raises(ValueError, match='pointer'):
        builder.build_dataset(parser, source_snapshot=snapshot)


def test_declared_in_memory_change_is_not_relabelled_as_original_bytes(implementation, tmp_path):
    path = source(tmp_path / 'source.json', {'rai:dataUseCases': RAW})
    parser = implementation['parser'].ROCrateParser(str(path))
    original = path.read_bytes()
    parser.require_root_dataset()['rai:dataUseCases'] = ['declared derived value']
    snapshot = policy.source_snapshot(parser, kind='declared_in_memory_graph')
    loader = implementation['loader'].MappingLoader(str(mapping(tmp_path)))
    builder = implementation['builder'].D4DBuilder(loader)
    record = builder.build_dataset(parser, source_snapshot=snapshot)
    assert record['tasks'] == [{'response': 'declared derived value'}]
    assert snapshot['original_file'] is None and snapshot['parents'] == []
    assert snapshot['serialization']['sha256'] != sha256(original).hexdigest()
    assert path.read_bytes() == original
    parser.require_root_dataset()['rai:dataUseCases'].append('changed after acquisition')
    with pytest.raises(ValueError, match='changed'):
        builder.get_route_dispositions()


@pytest.mark.parametrize('value', [float('nan'), float('inf'), {1: 'non-string key'}])
def test_generated_dict_must_preserve_actual_json_types(implementation, tmp_path, value):
    path = source(tmp_path / 'source.json', {'rai:dataUseCases': []})
    parser = implementation['parser'].ROCrateParser(str(path))
    original = deepcopy(parser.rocrate_data)
    original['extra'] = value
    raw = json.dumps(original).encode('utf-8')
    path.write_bytes(raw)
    parser = implementation['parser'].ROCrateParser(str(path))
    with pytest.raises(ValueError):
        policy.source_snapshot(parser, raw=raw, kind='generated_dict', input_value=original)


@pytest.mark.parametrize('preserve', [False, True])
@pytest.mark.parametrize('as_dict', [False, True])
def test_api_single_has_mandatory_detached_evidence_and_bound_sidecar(
        legacy, tmp_path, monkeypatch, preserve, as_dict):
    _, _, api = legacy
    monkeypatch.setattr(api, 'VALIDATION_AVAILABLE', False)
    path = source(tmp_path / 'input.json', {'rai:dataUseCases': RAW, 'version': '\ud800'})
    supplied = json.loads(path.read_bytes()) if as_dict else path
    output = tmp_path / 'record.yaml'
    instance = transformer(api, mapping(tmp_path), preserve=preserve)
    result = instance.rocrate_to_d4d(supplied, output_path=output)
    record, evidence = check_bundle(output)
    assert record == result.data and 'route_dispositions' not in record
    assert 'route_dispositions' in asdict(result)
    assert_json(evidence, result.route_dispositions)
    assert (result.transformation_metadata is not None) is preserve
    assert evidence['sources'][0]['snapshot']['kind'] == ('generated_dict' if as_dict else 'original_file')
    result.route_dispositions['sources'][0]['routes']['tasks'][0]['raw'].append('changed result')
    assert check_bundle(output)[1]['sources'][0]['routes']['tasks'][0]['raw'] == RAW
    if as_dict:
        assert next(row for row in supplied['@graph'] if row.get('@id') == './')['rai:dataUseCases'] == RAW


@pytest.mark.parametrize('contract', ['legacy', 'dataset_v1'])
def test_api_draft_policy_keeps_evidence_without_promoting_legacy_metadata(
        legacy, tmp_path, monkeypatch, contract):
    _, _, api = legacy
    monkeypatch.setattr(api, 'VALIDATION_AVAILABLE', False)
    path = source(tmp_path / 'input.json', {'rai:dataUseCases': RAW})
    instance = transformer(api, mapping(tmp_path), preserve=True, contract=contract)
    result = instance.rocrate_to_d4d(path)
    assert result.route_dispositions is not None
    assert ('transformation_metadata' in result.data) is (contract == 'legacy')
    output = tmp_path / 'record.yaml'
    if contract == 'legacy':
        with pytest.raises(publication.PublicationError, match='transformation_metadata'):
            instance.rocrate_to_d4d(path, output_path=output)
        assert not output.exists() and not sidecar(output).exists()
    else:
        instance.rocrate_to_d4d(path, output_path=output)
        check_bundle(output)


@pytest.mark.parametrize('rank', [False, True])
def test_api_merge_keeps_duplicate_input_occurrences_and_original_order(
        legacy, tmp_path, monkeypatch, rank):
    _, _, api = legacy
    monkeypatch.setattr(api, 'VALIDATION_AVAILABLE', False)
    path = source(tmp_path / 'same.json', {'rai:dataUseCases': RAW})
    instance = transformer(api, mapping(tmp_path))
    output = tmp_path / 'merged.yaml'
    result = instance.merge_rocrates([path, path], output_path=output, auto_prioritize=rank)
    evidence = result['route_dispositions']
    assert evidence['processed_occurrences'] == ['input:0', 'input:1']
    assert evidence['merge_order'] == ['input:0', 'input:1']
    assert result['data']['tasks'] == [{'response': 'whole task'}] * 4
    check_bundle(output)
    assert 'route_dispositions' not in result['data']


@pytest.mark.parametrize('command', ['transform', 'merge'])
@pytest.mark.parametrize('report', [False, True])
def test_packaged_publishers_require_sidecars_even_without_reports(
        tmp_path, command, report):
    from fairscape_integration.cli import cli
    path = source(tmp_path / 'input.json', {'rai:dataUseCases': RAW, 'version': '\ud800'})
    output = tmp_path / 'record.yaml'
    argv = [command, str(path), '-m', str(mapping(tmp_path)), '-o', str(output)]
    if report:
        argv.append('--report')
    result = CliRunner().invoke(cli, argv)
    assert result.exit_code == 0, result.output
    check_bundle(output)
    report_path = output.with_name(output.stem + ('_merge_report.txt' if command == 'merge' else '_report.txt'))
    assert report_path.exists() is report


@pytest.mark.parametrize('merge', [False, True])
@pytest.mark.parametrize('report', [False, True])
def test_hidden_single_and_merge_use_real_prepared_dataset_gate(
        legacy, tmp_path, monkeypatch, merge, report):
    single, _, _ = legacy
    path = source(tmp_path / 'input.json', {'rai:dataUseCases': RAW, 'version': '\ud800'})
    output = tmp_path / 'record.yaml'
    argv = ['legacy', '-m', str(mapping(tmp_path)), '-o', str(output)]
    argv += ['--merge', '--inputs', str(path)] if merge else ['--input', str(path)]
    if not report:
        argv.append('--no-report')
    monkeypatch.setattr(sys, 'argv', argv)
    assert single.main() == 0
    check_bundle(output)


@pytest.mark.parametrize('strategy', ['merge', 'concatenate', 'hybrid'])
@pytest.mark.parametrize('occupied', [False, True])
def test_auto_generated_temp_lifecycle_and_constituent_pointer_joins(
        legacy, tmp_path, monkeypatch, strategy, occupied):
    _, auto, _ = legacy
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    paths = [source(inputs / 'a-ro-crate-metadata.json', {'rai:dataUseCases': RAW})]
    if strategy == 'hybrid':
        paths.append(source(inputs / 'b-ro-crate-metadata.json', {'rai:dataUseCases': RAW}))
    before = {p: p.read_bytes() for p in paths}
    output = tmp_path / 'record.yaml'
    concat = output.with_name('record_concatenated.json')
    if occupied:
        concat.write_bytes(SENTINEL)
    monkeypatch.setattr(sys, 'argv', ['auto', '-i', str(inputs), '-m', str(mapping(tmp_path)),
        '-o', str(output), '--strategy', strategy])
    assert auto.main() == 0
    _, evidence = check_bundle(output)
    if strategy != 'merge':
        generated = next(s['snapshot'] for s in evidence['sources']
                         if s['snapshot']['kind'] == 'generated_combined')
        assert generated['original_file'] is None
        assert concat.read_bytes() == generated['json_text'].encode('utf-8')
        assert generated['parents'] and generated['entity_origins']
        assert all(parent['original_file']['path'] in {str(p.resolve()) for p in paths}
                   for parent in generated['parents'])
        assert all('original_index' in parent and 'occurrence_id' in parent for parent in generated['parents'])
        assert all(join['original_pointer'].startswith('/@graph/') for join in generated['entity_origins'])
    elif occupied:
        assert concat.read_bytes() == SENTINEL
    assert {p: p.read_bytes() for p in paths} == before


def test_combined_conflicting_roots_cannot_publish_any_prepared_artifact(
        legacy, tmp_path, monkeypatch):
    _, auto, _ = legacy
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    for name in ('a', 'b'):
        source(inputs / (name + '-ro-crate-metadata.json'), {'rai:dataUseCases': RAW})
    output = tmp_path / 'record.yaml'
    destinations = [output, sidecar(output), output.with_name('record_concatenated.json')]
    for path in destinations:
        path.write_bytes(SENTINEL)
    monkeypatch.setattr(sys, 'argv', ['auto', '-i', str(inputs), '-m', str(mapping(tmp_path)),
                                     '-o', str(output), '--strategy', 'concatenate'])
    assert auto.main() == 1
    assert all(path.read_bytes() == SENTINEL for path in destinations)


@pytest.mark.parametrize('mutation', ['source', 'mapping', 'sidecar'])
def test_marked_prepublication_binding_refusal_preserves_existing_outputs(
        legacy, tmp_path, monkeypatch, mutation):
    _, _, api = legacy
    monkeypatch.setattr(api, 'VALIDATION_AVAILABLE', False)
    path = source(tmp_path / 'source.json', {'rai:dataUseCases': RAW})
    tsv = mapping(tmp_path)
    instance = transformer(api, tsv)
    output = tmp_path / 'record.yaml'
    for p in (output, sidecar(output)):
        p.write_bytes(SENTINEL)
    original = api.prepare_dataset
    def after_real_gate(*args, **kwargs):
        raw = original(*args, **kwargs)
        if mutation in ('source', 'mapping'):
            changed = path if mutation == 'source' else tsv
            changed.write_bytes(changed.read_bytes() + b'\n')
        return raw
    monkeypatch.setattr(api, 'prepare_dataset', after_real_gate)
    if mutation == 'sidecar':
        original_sidecar = api.prepare_sidecar
        def corrupt(output_path, dataset, raw, evidence, loader):
            evidence['sources'][0]['routes']['tasks'][0]['raw'].append('not in the input')
            return original_sidecar(output_path, dataset, raw, evidence, loader)
        monkeypatch.setattr(api, 'prepare_sidecar', corrupt)
    with pytest.raises(ValueError):
        instance.rocrate_to_d4d(path, output_path=output)
    assert output.read_bytes() == sidecar(output).read_bytes() == SENTINEL


def test_all_batch_datasets_and_sidecars_prepare_before_any_publication(
        legacy, tmp_path, monkeypatch):
    _, _, api = legacy
    monkeypatch.setattr(api, 'VALIDATION_AVAILABLE', False)
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    first = source(inputs / 'a.json', {'rai:dataUseCases': RAW})
    second = source(inputs / 'z.json', {'rai:dataUseCases': RAW})
    data = json.loads(second.read_bytes())
    next(row for row in data['@graph'] if row.get('@id') == './')['unexpected'] = 'must refuse'
    second.write_text(json.dumps(data), encoding='utf-8')
    output = tmp_path / 'out'; output.mkdir()
    destinations = [output / (name + '_d4d.yaml') for name in ('a', 'z')]
    for p in destinations + [sidecar(p) for p in destinations]:
        p.write_bytes(SENTINEL)
    tsv = mapping(tmp_path)
    with tsv.open('a', encoding='utf-8') as stream:
        stream.write('unexpected_field\tstr\tunexpected\t\t1\t1\n')
    with pytest.raises(publication.PublicationError):
        api.batch_transform_rocrates(inputs, output, validate=False,
                                    result_contract='dataset_v1', mapping_file=tsv)
    assert all(p.read_bytes() == SENTINEL for p in destinations + [sidecar(p) for p in destinations])
    # Restore the actual later input; the same full batch now binds each sidecar
    # to its own Dataset rather than zipping a mixed prepared-file list.
    source(second, {'rai:dataUseCases': RAW})
    results = api.batch_transform_rocrates(inputs, output, validate=False,
                                         result_contract='dataset_v1', mapping_file=tsv)
    assert len(results) == 2
    for result, p in zip(results, destinations):
        check_bundle(p)
        assert result.transformation_metadata['publication']['path'] == str(p.resolve())
    assert first.exists()


@pytest.mark.parametrize('command', ['transform', 'merge', 'batch'])
def test_route_only_json_transport_is_safe_without_creator_policy(
        legacy, tmp_path, monkeypatch, capsys, command):
    _, _, api = legacy
    monkeypatch.setattr(api, 'VALIDATION_AVAILABLE', False)
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    path = source(inputs / 'input.json', {'rai:dataUseCases': RAW, 'version': '\ud800'})
    tsv = mapping(tmp_path)
    output = tmp_path / ('out' if command == 'batch' else 'record.yaml')
    argv = [command, '--result-contract', 'dataset_v1', '--mapping', str(tsv)]
    argv += ([str(output), str(path), str(path)] if command == 'merge' else
             [str(inputs if command == 'batch' else path), str(output)])
    capsys.readouterr()
    api.main(argv)
    wire = capsys.readouterr().out
    assert '\\ud800' in wire and wire.isascii()
    result = json.loads(wire)
    evidence = (result['results'][0]['route_dispositions'] if command == 'batch'
                else result['route_dispositions'])
    assert evidence['sources'][0]['routes']['tasks'][0]['raw'] == RAW
    assert 'creator_reference_construction' not in (result['results'][0] if command == 'batch' else result)


def test_low_level_marked_save_requires_explicit_bound_evidence(legacy, implementation, tmp_path):
    single, _, _ = legacy
    path = source(tmp_path / 'source.json', {'rai:dataUseCases': RAW})
    tsv = mapping(tmp_path)
    record, evidence, _, _, _ = build(implementation, path, tsv)
    output = tmp_path / 'record.yaml'
    output.write_bytes(SENTINEL); sidecar(output).write_bytes(SENTINEL)
    with pytest.raises(ValueError, match='evidence'):
        single.save_d4d_yaml(record, output, tsv, rocrate_path=path)
    assert output.read_bytes() == sidecar(output).read_bytes() == SENTINEL
    single.save_d4d_yaml(record, output, tsv, rocrate_path=path, route_dispositions=evidence)
    check_bundle(output)


@pytest.mark.parametrize('fault', ['sidecar_is_directory', 'second_stage_fails'])
def test_sidecar_staging_failure_never_replaces_dataset(legacy, tmp_path, monkeypatch, fault):
    _, _, api = legacy
    monkeypatch.setattr(api, 'VALIDATION_AVAILABLE', False)
    path = source(tmp_path / 'input.json', {'rai:dataUseCases': RAW})
    instance = transformer(api, mapping(tmp_path))
    output = tmp_path / 'record.yaml'; output.write_bytes(SENTINEL)
    if fault == 'sidecar_is_directory':
        sidecar(output).mkdir()
        with pytest.raises(publication.PublicationError, match='directory'):
            instance.rocrate_to_d4d(path, output_path=output)
        assert sidecar(output).is_dir()
    else:
        sidecar(output).write_bytes(SENTINEL)
        original = publication.tempfile.NamedTemporaryFile
        sentinel = OSError('second prepared artifact cannot be staged')
        calls = []
        def stage(*args, **kwargs):
            calls.append(kwargs['prefix'])
            if len(calls) == 2:
                raise sentinel
            return original(*args, **kwargs)
        monkeypatch.setattr(publication.tempfile, 'NamedTemporaryFile', stage)
        with pytest.raises(OSError) as error:
            instance.rocrate_to_d4d(path, output_path=output)
        assert error.value is sentinel and len(calls) == 2
        assert sidecar(output).read_bytes() == SENTINEL
        assert not list(tmp_path.glob('.*.tmp'))
    assert output.read_bytes() == SENTINEL


@pytest.mark.parametrize('report_kind', ['single', 'merge'])
@pytest.mark.parametrize('newline', [b'\n', b'\r\n', b'\r'])
def test_report_only_wrappers_bind_exact_existing_dataset_bytes(
        legacy, implementation, tmp_path, report_kind, newline):
    single, _, _ = legacy
    path = source(tmp_path / 'input.json', {'rai:dataUseCases': RAW})
    tsv = mapping(tmp_path)
    record, evidence, builder, parser, loader = build(implementation, path, tsv)
    output = tmp_path / 'record.yaml'
    if report_kind == 'single':
        report = tmp_path / 'transformation_report.txt'
        with pytest.raises(ValueError, match='Dataset path'):
            single.generate_transformation_report(parser, builder, loader, tmp_path)
        def save():
            single.generate_transformation_report(parser, builder, loader, tmp_path, dataset_path=output)
    else:
        report = tmp_path / 'record_merge_report.txt'
        merger = implementation['merger'].ROCrateMerger(loader)
        record = merger.merge_rocrates([parser])
        def save():
            merger.save_merge_report(output, [parser])
        with pytest.raises(FileNotFoundError):
            save()
    report.write_bytes(SENTINEL)
    assert not sidecar(output).exists()
    raw = publication.prepare_dataset(record).replace(b'\n', newline)
    # This is an actual valid saved Dataset under each newline convention.
    assert publication.prepare_dataset(record, text=raw.decode('utf-8')) == raw
    output.write_bytes(raw)
    save()
    assert report.read_bytes() != SENTINEL and output.read_bytes() == raw
    _, evidence = check_bundle(output)
    document = json.loads(sidecar(output).read_bytes())
    assert document['dataset']['sha256'] == sha256(raw).hexdigest()
    assert document['dataset']['bytes'] == len(raw)
    # A Dataset from another transformation cannot acquire this evidence.
    output.write_bytes(publication.prepare_dataset(dict(record, title='other transformation')))
    before = {p: p.read_bytes() for p in (output, report, sidecar(output))}
    with pytest.raises(publication.PublicationError, match='changed mapped'):
        save()
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('alias', [False, True])
def test_report_only_destination_cannot_replace_accepted_dataset(legacy, tmp_path, alias):
    single, _, api = legacy
    path = source(tmp_path / 'source.json', {'rai:dataUseCases': RAW})
    loader = api.MappingLoader(str(mapping(tmp_path)))
    parser = api.ROCrateParser(str(path))
    builder = api.D4DBuilder(loader)
    record = builder.build_dataset(parser)
    report = tmp_path / 'transformation_report.txt'
    raw = publication.prepare_dataset(record)
    report.write_bytes(raw)
    selected = tmp_path / 'accepted.yaml' if alias else report
    if alias:
        selected.symlink_to(report.name)
    planned_sidecar = sidecar(selected); planned_sidecar.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError, match='overlap'):
        single.generate_transformation_report(parser, builder, loader, tmp_path, dataset_path=selected)
    assert report.read_bytes() == selected.read_bytes() == raw
    assert planned_sidecar.read_bytes() == SENTINEL
    assert selected.is_symlink() is alias


@pytest.mark.parametrize('reverse', [False, True])
def test_ranked_api_sources_keep_original_occurrences_and_raw_rankings(
        legacy, tmp_path, monkeypatch, reverse):
    _, _, api = legacy
    monkeypatch.setattr(api, 'VALIDATION_AVAILABLE', False)
    sparse = source(tmp_path / 'sparse.json', {})
    rich = source(tmp_path / 'rich.json', {'rai:dataUseCases': RAW, 'version': 'release only'})
    paths = [rich, sparse] if reverse else [sparse, rich]
    tsv = mapping(tmp_path)
    instance = transformer(api, tsv)
    parsers = [api.ROCrateParser(str(p)) for p in paths]
    ranks = api.InformativenessScorer().rank_rocrates(parsers, instance.mapping_loader)
    expected = [parsers.index(parser) for parser, _, _ in ranks]
    result = instance.merge_rocrates(paths, auto_prioritize=True)
    evidence = result['route_dispositions']
    assert evidence['processed_occurrences'] == ['input:' + str(i) for i in expected]
    for row, original_index in zip(evidence['sources'], expected):
        assert row['original_index'] == original_index
        assert row['snapshot']['original_file']['path'] == str(paths[original_index].resolve())
        assert row['snapshot']['json_text'].encode('utf-8') == paths[original_index].read_bytes()
    assert result['data']['tasks'] == [{'response': 'whole task'}] * 2
    assert_recovered(evidence)


@pytest.mark.parametrize('same_parser', [False, True])
def test_repeated_path_is_two_occurrences_with_nonzero_primary(implementation, tmp_path, same_parser):
    path = source(tmp_path / 'same.json', {'rai:dataUseCases': RAW})
    loader = implementation['loader'].MappingLoader(str(mapping(tmp_path)))
    first = implementation['parser'].ROCrateParser(str(path))
    second = first if same_parser else implementation['parser'].ROCrateParser(str(path))
    merger = implementation['merger'].ROCrateMerger(loader)
    record = merger.merge_rocrates([first, second], primary_index=1,
                                   source_names=['first occurrence', 'primary occurrence'])
    evidence = merger.get_route_dispositions()
    assert evidence['processed_occurrences'] == ['input:0', 'input:1']
    assert evidence['merge_order'] == ['input:1', 'input:0']
    assert evidence['primary_occurrence'] == 'input:1'
    assert [row['snapshot']['original_file']['path'] for row in evidence['sources']] == [str(path.resolve())] * 2
    assert record['tasks'] == [{'response': 'whole task'}] * 4
    assert merger.get_provenance()['tasks'] == ['primary occurrence', 'first occurrence']
    assert [unit['output_pointer'] for unit in evidence['sources'][1]['routes']['tasks'][0]['units']
            if unit['disposition'] == 'constructed'] == ['/tasks/0/response', '/tasks/1/response']
    assert [unit['output_pointer'] for unit in evidence['sources'][0]['routes']['tasks'][0]['units']
            if unit['disposition'] == 'constructed'] == ['/tasks/2/response', '/tasks/3/response']
    policy.validate_evidence(evidence, record, loader)
    assert_recovered(evidence)


@pytest.mark.parametrize('default_mapping', [False, True])
def test_transform_report_publishes_unmapped_root_text_and_exact_evidence(
        tmp_path, default_mapping):
    from fairscape_integration.cli import cli
    prop = 'unmapped/report~field'
    unmapped = 'Unmapped "quoted"\nvalue \ud800 and \U0001f600'
    task = '  Whole intended task; unchanged.\n'
    path = source(tmp_path / 'input.json', {'rai:dataUseCases': task, prop: unmapped})
    mapping_path = (Path(__file__).resolve().parents[2] /
                    'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
                    if default_mapping else mapping(tmp_path))
    original = {p: p.read_bytes() for p in (path, mapping_path)}
    output = tmp_path / 'published' / 'record.yaml'
    result = CliRunner().invoke(cli, ['transform', str(path), '--mapping', str(mapping_path),
                                      '--output', str(output), '--report'])
    assert result.exit_code == 0, result.output
    report_path = output.with_name('record_report.txt')
    evidence_path = sidecar(output)
    assert {p.name for p in output.parent.iterdir()} == {
        'record.yaml', 'record_report.txt', 'record_route_dispositions.json'}
    dataset_raw = output.read_bytes()
    record = yaml.safe_load(dataset_raw)
    assert record['tasks'] == [{'response': task}]
    assert prop not in record and 'route_dispositions' not in record
    # Real schema gate, readback and saved-byte identity, without a mock validator.
    assert publication.prepare_dataset(record, text=dataset_raw.decode('utf-8')) == dataset_raw
    report_text = report_path.read_bytes().decode('utf-8')
    assert json.dumps(prop, ensure_ascii=True, allow_nan=False) in report_text
    assert json.dumps(unmapped, ensure_ascii=True, allow_nan=False) in report_text
    assert 'Construction counts are not source coverage or validation success.' in report_text
    document = json.loads(evidence_path.read_bytes())
    assert document['dataset'] == {'path': str(output.resolve()), 'bytes': len(dataset_raw),
                                   'sha256': sha256(dataset_raw).hexdigest()}
    schema_raw = Path(document['schema']['path']).read_bytes()
    assert document['schema']['bytes'] == len(schema_raw)
    assert document['schema']['sha256'] == sha256(schema_raw).hexdigest()
    evidence = document['evidence']
    assert evidence['mapping'] == {'path': str(mapping_path.resolve()),
        'bytes': len(original[mapping_path]), 'sha256': sha256(original[mapping_path]).hexdigest()}
    assert len(evidence['sources']) == 1
    occurrence = evidence['sources'][0]
    snapshot = occurrence['snapshot']
    assert snapshot['kind'] == 'original_file'
    assert snapshot['json_text'].encode('utf-8') == original[path]
    assert snapshot['original_file'] == {'path': str(path.resolve()), 'bytes': len(original[path]),
                                         'sha256': sha256(original[path]).hexdigest()}
    assert snapshot['serialization'] == {'bytes': len(original[path]),
                                          'sha256': sha256(original[path]).hexdigest()}
    captured = json.loads(snapshot['json_text'])
    root = pointer(captured, snapshot['root_pointer'])
    assert root[prop] == unmapped and root['rai:dataUseCases'] == task
    assertion, = occurrence['routes']['tasks']
    assert assertion['raw'] == task and pointer(captured, assertion['pointer']) == task
    unit, = assertion['units']
    assert unit['raw'] == task and pointer(record, unit['output_pointer']) == task
    assert all(p.read_bytes() == raw for p, raw in original.items())
