"""#4926: escaped source JSON remains evidence, never an encoding failure."""
from copy import deepcopy
from hashlib import sha256
import json

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema.legacy_creator_references import reference_lines
from data_sheets_schema.legacy_creators import MARKER
from .test_legacy_creator_references import (
    ID, NAME, ORG, REPO, SENTINEL, build, evidence, implementation, legacy,
    person, projected, source, table,
)

UNICODE = ['\ud800', '\udfff', 'café e\u0301 — \U0001f9ec']


def escaped_source(path, kind, text):
    # The file itself is valid ASCII JSON, exactly the reader boundary at issue.
    source(path, {'@id': ID})
    document = json.loads(path.read_text())
    member = next(row for row in document['@graph'] if row.get('@id') == ID)
    if kind == 'unknown':
        member['unmapped_fact'] = {'nested': [text, text]}
    elif kind == 'duplicate':
        duplicate = deepcopy(member)
        duplicate['extra'] = text
        document['@graph'].append(duplicate)
    elif kind == 'name':
        member['name'] = text
    elif kind == 'affiliation':
        member['affiliation']['name'] = text
    else:
        raise AssertionError(kind)
    path.write_bytes(json.dumps(document, ensure_ascii=True).encode('ascii'))
    return path, [row for row in document['@graph'] if row.get('@id') == ID]


def admitted_bytes(record):
    """Use the actual unchanged mandatory gate; do not assume surrogate admission."""
    try:
        return publication.prepare_dataset(record), None
    except publication.PublicationError as error:
        return None, error


@pytest.mark.parametrize('kind', ['unknown', 'duplicate', 'name', 'affiliation'])
@pytest.mark.parametrize('text', UNICODE)
def test_escaped_member_evidence_and_utf8_reports_preserve_parsed_values(
        implementation, tmp_path, kind, text):
    path, members = escaped_source(tmp_path / 'source.json', kind, text)
    mapping = table(tmp_path)
    before = {p: p.read_bytes() for p in (path, mapping)}
    assert before[path].isascii()
    record, parser, builder = build(implementation, path, mapping)
    details = evidence(builder.mapping, parser, builder)
    entry = details['sources'][0]['entries'][0]
    assert entry['original_unit'] == {'@id': ID}
    assert [m['raw_member'] for m in entry['matches']] == members
    for match, member in zip(entry['matches'], members):
        canonical = json.dumps(member, ensure_ascii=True, sort_keys=True,
                               separators=(',', ':')).encode('ascii')
        assert match['parsed_json_sha256'] == sha256(canonical).hexdigest()
    if kind in ('unknown', 'duplicate'):
        assert record['creators'] == [{'@id': ID}]
        assert entry['status'] == 'unresolved'
        assert entry['reason'] == ('unsupported_person_fields' if kind == 'unknown'
                                   else 'duplicate_reference_id')
        with pytest.raises(publication.PublicationError, match='creators'):
            publication.prepare_dataset(record)
    else:
        assert record['creators'] == [projected(members[0])]
        assert entry['status'] == 'resolved'
        raw, refused = admitted_bytes(record)
        if refused is None:
            assert yaml.safe_load(raw) == record
        else:
            # Refusal is the unchanged schema/readback boundary, not _digest.
            assert isinstance(refused, publication.PublicationError)
    rendered = '\n'.join(reference_lines(details))
    wire = rendered.encode('utf-8')
    encoded = next(line for line in wire.decode('utf-8').splitlines() if line.startswith('{'))
    assert json.loads(encoded) == details
    assert encoded.isascii()
    # Both actual report implementations include complete matched-member data.
    merger = implementation['merger'].ROCrateMerger(builder.mapping)
    merger.merge_rocrates([parser], source_names=['neutral source'])
    report = merger.generate_merge_report([parser], source_names=['neutral source'])
    report.encode('utf-8')
    reference_row = next(json.loads(line) for line in report.splitlines()
                         if line.startswith('{') and '"policy": "creator_author_references_v1"' in line)
    assert reference_row['sources'][0]['entries'][0]['matches'] == entry['matches']
    details['sources'][0]['entries'][0]['matches'][0]['raw_member']['name'] = 'caller mutation'
    assert builder.get_creator_reference_construction()['entries'][0]['matches'][0]['raw_member'] == members[0]
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('entrypoint', ['packaged', 'd4d'])
@pytest.mark.parametrize('kind', ['unknown', 'duplicate', 'name', 'affiliation'])
@pytest.mark.parametrize('text', ['\ud800', '\U0001f9ec café'])
def test_real_cli_unicode_reports_or_exact_gate_refusal_preserve_destinations(
        legacy, tmp_path, monkeypatch, entrypoint, kind, text):
    single, _, _ = legacy
    path, members = escaped_source(tmp_path / 'source.json', kind, text)
    mapping = table(tmp_path)
    parser = single.ROCrateParser(str(path))
    builder = single.D4DBuilder(single.MappingLoader(str(mapping)))
    record = builder.build_dataset(parser)
    prepared, refused = admitted_bytes(record)
    output = tmp_path / 'dataset.yaml'; output.write_bytes(SENTINEL)
    report = tmp_path / ('dataset_report.txt' if entrypoint == 'packaged' else 'transformation_report.txt')
    report.write_bytes(SENTINEL)
    before = {p: p.read_bytes() for p in (path, mapping)}
    monkeypatch.chdir(REPO)
    if entrypoint == 'packaged':
        from fairscape_integration.cli import cli
        args = ['transform', str(path), '-m', str(mapping), '-o', str(output), '--report']
    else:
        from data_sheets_schema.cli import cli
        args = ['rocrate', 'transform', str(path), '--mapping', str(mapping), '-o', str(output)]
    outcome = CliRunner().invoke(cli, args)
    if refused is not None:
        assert outcome.exit_code == 1
        assert 'creators' in outcome.output or 'publication' in outcome.output.lower()
        assert output.read_bytes() == report.read_bytes() == SENTINEL
    else:
        assert outcome.exit_code == 0, outcome.output
        assert yaml.safe_load(output.read_bytes()) == yaml.safe_load(prepared)
        raw_report = report.read_bytes()
        assert raw_report.decode('utf-8').encode('utf-8') == raw_report
        row = next(json.loads(line) for line in raw_report.decode().splitlines()
                   if line.startswith('{') and '"policy": "creator_author_references_v1"' in line)
        assert row['sources'][0]['entries'][0]['matches'][0]['raw_member'] == members[0]
        outcome.output.encode('utf-8')
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize('command', ['transform', 'batch', 'merge'])
@pytest.mark.parametrize('text', ['\ud800', '\U0001f9ec café'])
def test_actual_api_json_transport_is_safe_after_the_real_publication_gate(
        legacy, tmp_path, monkeypatch, capsys, command, text):
    single, _, api = legacy
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    first, members = escaped_source(inputs / 'a.json', 'name', text)
    second, _ = escaped_source(inputs / 'b.json', 'affiliation', text)
    mapping = table(tmp_path)
    builder = single.D4DBuilder(single.MappingLoader(str(mapping)))
    first_record = builder.build_dataset(single.ROCrateParser(str(first)))
    second_record = builder.build_dataset(single.ROCrateParser(str(second)))
    _, first_refusal = admitted_bytes(first_record)
    _, second_refusal = admitted_bytes(second_record)
    expected_refusal = first_refusal or (second_refusal if command != 'transform' else None)
    # Select supported config flags; retain actual producers and mandatory
    # final-byte prepare_dataset/publish, rather than substituting a gate.
    original_config = api.TransformationConfig
    def config(**kwargs):
        kwargs.update(validate_input=False, validate_output=False)
        return original_config(**kwargs)
    monkeypatch.setattr(api, 'TransformationConfig', config)
    output = tmp_path / ('outputs' if command == 'batch' else 'dataset.yaml')
    paths = ([output / 'a_d4d.yaml', output / 'b_d4d.yaml'] if command == 'batch' else [output])
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(SENTINEL)
    args = {'transform': [str(first), str(output)], 'batch': [str(inputs), str(output)],
            'merge': [str(output), str(first), str(second)]}[command]
    capsys.readouterr()
    if expected_refusal is not None:
        with pytest.raises(publication.PublicationError):
            api.main([command, *args, '--result-contract', 'dataset_v1', '--mapping', str(mapping)])
        assert all(p.read_bytes() == SENTINEL for p in paths)
    else:
        api.main([command, *args, '--result-contract', 'dataset_v1', '--mapping', str(mapping)])
        wire = capsys.readouterr().out.encode('utf-8')
        assert wire.isascii()
        document = json.loads(wire)
        rows = document['results'] if command == 'batch' else [document]
        for row in rows:
            for source_row in row['creator_reference_construction']['sources']:
                member = source_row['entries'][0]['matches'][0]['raw_member']
                assert member['name'] == text or member['affiliation']['name'] == text
        assert all(p.read_bytes() != SENTINEL for p in paths)


@pytest.mark.parametrize('command', ['transform', 'batch', 'merge'])
@pytest.mark.parametrize('marker', [MARKER, ''])
def test_inactive_api_policies_retain_unicode_wire_spelling(
        legacy, tmp_path, capsys, command, marker):
    _, _, api = legacy
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    # Literal-only and unmarked construction both produce valid Creator
    # dictionaries here; they must not silently acquire the new JSON encoding.
    value = {'description': 'café \U0001f9ec'} if not marker else 'café \U0001f9ec'
    first = source(inputs / 'a.json', value, members=[])
    second = source(inputs / 'b.json', value, members=[])
    mapping = table(tmp_path, marker=marker, field_type='list')
    # A scalar dictionary with Type=list follows the historical early wrapping
    # branch, producing one valid Creator without the reference policy.
    transformer = api.SemanticTransformer(api.TransformationConfig(mapping_file=mapping,
        validate_input=False, validate_output=False, preserve_provenance=False, result_contract='dataset_v1'))
    record = transformer.rocrate_to_d4d(first).data
    publication.prepare_dataset(record)
    assert 'creator_reference_construction' not in vars(transformer.rocrate_to_d4d(first))
    output = tmp_path / ('outputs' if command == 'batch' else 'dataset.yaml')
    args = {'transform': [str(first), str(output)], 'batch': [str(inputs), str(output)],
            'merge': [str(output), str(first), str(second)]}[command]
    capsys.readouterr()
    api.main([command, *args, '--result-contract', 'dataset_v1', '--mapping', str(mapping)])
    rendered = capsys.readouterr().out
    assert 'café' in rendered and '\U0001f9ec' in rendered
    document = json.loads(rendered)
    rows = document['results'] if command == 'batch' else [document]
    assert all('creator_reference_construction' not in row for row in rows)
