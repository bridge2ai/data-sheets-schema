"""Supplemental size evidence is accounted separately from mapping/coverage."""
from hashlib import sha256
import json
from pathlib import Path
import sys

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from data_sheets_schema import legacy_route_dispositions as policy
from fairscape_integration.utils.mapping_loader import MappingLoader
from .test_legacy_publication import legacy
from .test_legacy_route_dispositions_core import source, table, pointer, assert_json


ABSENT = object()
EXACT = 'evi:totalContentSizeBytes'
UNRELATED = 'unmappedControl'


def publish(renderer, request, monkeypatch, tmp_path, mapping, properties, *, move_root=False):
    path = source(tmp_path / 'input.json', dict(properties, **{UNRELATED: 'Still unmapped'}))
    if move_root:
        graph = json.loads(path.read_bytes())
        assert len(graph['@graph']) == 3
        graph['@graph'] = [graph['@graph'][i] for i in (2, 0, 1)]
        path.write_text(json.dumps(graph, ensure_ascii=True), encoding='utf-8')
    original = {p: p.read_bytes() for p in (path, mapping)}
    output = tmp_path / 'published' / 'record.yaml'
    if renderer == 'packaged':
        from fairscape_integration.cli import cli
        result = CliRunner().invoke(cli, ['transform', str(path), '--mapping', str(mapping),
                                          '--output', str(output), '--report'])
        assert result.exit_code == 0, result.output
        report_path = output.with_name('record_report.txt')
    else:
        single, _, _ = request.getfixturevalue('legacy')
        monkeypatch.setattr(sys, 'argv', ['legacy', '--input', str(path), '--mapping', str(mapping),
                                        '--output', str(output)])
        assert single.main() == 0
        report_path = output.with_name('transformation_report.txt')
    raw = output.read_bytes()
    record = yaml.safe_load(raw)
    assert publication.prepare_dataset(record, text=raw.decode('utf-8')) == raw
    report = report_path.read_bytes().decode('utf-8')
    assert 'Construction counts are not source coverage or validation success.' in report
    assert UNRELATED in report.split('UNMAPPED RO-CRATE PROPERTIES\n', 1)[1]
    assert all(p.read_bytes() == v for p, v in original.items())
    evidence_path = output.with_name('record_route_dispositions.json')
    document = json.loads(evidence_path.read_bytes()) if evidence_path.exists() else None
    if document is not None:
        assert document['dataset'] == {'path': str(output.resolve()), 'bytes': len(raw),
                                       'sha256': sha256(raw).hexdigest()}
        schema_raw = Path(document['schema']['path']).read_bytes()
        assert document['schema']['bytes'] == len(schema_raw)
        assert document['schema']['sha256'] == sha256(schema_raw).hexdigest()
        occurrence, = document['evidence']['sources']
        snapshot = occurrence['snapshot']
        assert snapshot['kind'] == 'original_file'
        assert snapshot['json_text'].encode('utf-8') == original[path]
        assert snapshot['original_file'] == {'path': str(path.resolve()), 'bytes': len(original[path]),
                                             'sha256': sha256(original[path]).hexdigest()}
    return record, report, document, original[path]


@pytest.mark.parametrize('renderer', ['packaged', 'hidden'])
@pytest.mark.parametrize('exact,expected,status', [
    (ABSENT, ABSENT, 'missing'), (None, ABSENT, 'null'), (0, 0, 'constructed'),
    (17, 17, 'constructed'), (False, ABSENT, 'declined'), (-1, ABSENT, 'declined'),
    (17.0, ABSENT, 'declined'), ('17', ABSENT, 'declined'),
    ([17, 17], ABSENT, 'declined'), ({'bad': '\ud800'}, ABSENT, 'declined'),
])
def test_present_supplements_have_visible_disposition_not_unmapped_credit(
        renderer, exact, expected, status, request, monkeypatch, tmp_path):
    mapping = table(tmp_path, [('bytes', 'contentSize')])
    # Rounded contentSize stays independent and never establishes exact bytes.
    properties = {'contentSize': '12 MB'}
    if exact is not ABSENT:
        properties[EXACT] = exact
    record, report, document, raw = publish(renderer, request, monkeypatch, tmp_path, mapping, properties,
                                             move_root=exact is ABSENT)
    assert ('total_size_bytes' in record) is (expected is not ABSENT)
    if expected is not ABSENT:
        assert type(record['total_size_bytes']) is int and record['total_size_bytes'] == expected
    assert 'bytes' not in record
    occurrence, = document['evidence']['sources']
    rounded, assertion = occurrence['routes']['bytes']
    assert rounded['raw'] == '12 MB' and rounded['disposition'] == 'declined'
    assert rounded['units'][0]['reason'] == 'rounded_size_not_converted'
    assert assertion['property'] == EXACT and assertion['supplemental'] is True
    assert assertion['disposition'] == status
    assert assertion['present'] is (exact is not ABSENT)
    assert EXACT not in report.split('UNMAPPED RO-CRATE PROPERTIES\n', 1)[1]
    if exact is ABSENT:
        assert 'raw' not in assertion and assertion['units'] == []
        graph = json.loads(raw)['@graph']
        assert graph[0]['@id'] == 'member' and graph[0][EXACT] == 999
        assert graph[2]['@id'] == './' and EXACT not in graph[2]
        assert occurrence['snapshot']['root_pointer'] == '/@graph/2'
        assert 'SUPPLEMENTAL ROUTE ASSERTIONS' not in report
    else:
        assert_json(assertion['raw'], exact)
        assert_json(pointer(json.loads(raw), assertion['pointer']), exact)
        section = report.split('SUPPLEMENTAL ROUTE ASSERTIONS\n', 1)[1].split(
            'UNMAPPED RO-CRATE PROPERTIES\n', 1)[0]
        rows = [json.loads(line.strip()) for line in section.splitlines() if line.startswith('  {')]
        assert rows == [{'source_occurrence': 'input:0', 'legacy_field': 'bytes', 'property': EXACT,
                         'pointer': assertion['pointer'], 'disposition': status,
                         'output_pointers': ['/total_size_bytes'] if expected is not ABSENT else []}]
        assert 'Evidence accounting alone is not mapping, source coverage or validation success.' in section
        assert "declined/null assertions add no construction credit" in section
        if exact is not None:
            unit, = assertion['units']
            assert_json(unit['raw'], exact)
            assert unit['disposition'] == status
            assert unit['output_pointer'] == ('/total_size_bytes' if expected is not ABSENT else None)
    # Supplemental report accounting must not mutate the declared TSV roster.
    assert EXACT not in MappingLoader(str(mapping)).get_all_mapped_rocrate_properties()


@pytest.mark.parametrize('renderer', ['packaged', 'hidden'])
@pytest.mark.parametrize('exact', [0, 17])
def test_default_supplement_only_constructs_and_reports_exact_size(
        renderer, exact, request, monkeypatch, tmp_path):
    mapping = Path(__file__).resolve().parents[2] / 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
    record, report, document, raw = publish(renderer, request, monkeypatch, tmp_path, mapping, {EXACT: exact})
    assert record['total_size_bytes'] == exact and type(record['total_size_bytes']) is int
    occurrence, = document['evidence']['sources']
    rounded, assertion = occurrence['routes']['bytes']
    assert rounded['present'] is False and rounded['disposition'] == 'missing'
    assert assertion['raw'] == exact and assertion['disposition'] == 'constructed'
    assert pointer(json.loads(raw), assertion['pointer']) == exact
    assert EXACT not in report.split('UNMAPPED RO-CRATE PROPERTIES\n', 1)[1]
    assert 'SUPPLEMENTAL ROUTE ASSERTIONS' in report
    assert EXACT not in MappingLoader(str(mapping)).get_all_mapped_rocrate_properties()


@pytest.mark.parametrize('renderer', ['packaged', 'hidden'])
@pytest.mark.parametrize('route', ['unmarked_bytes', 'marked_other'])
def test_unmarked_or_unrelated_policy_does_not_claim_supplement_accounting(
        renderer, route, request, monkeypatch, tmp_path):
    mapping = (table(tmp_path, [('bytes', 'contentSize')], marked=False)
               if route == 'unmarked_bytes' else table(tmp_path, [('tasks', 'rai:dataUseCases')]))
    record, report, document, _ = publish(renderer, request, monkeypatch, tmp_path, mapping, {EXACT: 17})
    assert 'total_size_bytes' not in record
    assert EXACT in report.split('UNMAPPED RO-CRATE PROPERTIES\n', 1)[1]
    assert 'SUPPLEMENTAL ROUTE ASSERTIONS' not in report
    assert (document is None) is (route == 'unmarked_bytes')
