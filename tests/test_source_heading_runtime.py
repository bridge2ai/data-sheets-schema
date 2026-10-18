"""Actual catalog/corpus joins; no model placement or scientific approval."""
import copy
import json
import io
from pathlib import Path
import zipfile

import pytest

from data_sheets_schema import chunking, source_heading_routing as draft
from data_sheets_schema import source_heading_runtime as runtime
from tests.test_source_heading_routing import inputs  # genuine tiny compiler fixture


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode()


def declaration(bundle, manifest, *, heading='Completeness', uri=None, lines=None):
    docs, starts, _ = runtime._documents(bundle, manifest)
    evidence = b'Explicit draft label/property correspondence, not authenticated science.'
    crosswalk = {'format': 'source_heading_span_crosswalk_v1', 'authority_status': 'draft/unreviewed',
        'rows': [{'id': 'row', 'heading': heading,
            'property_uri': uri or draft.RAI + 'dataCollectionMissingData',
            'evidence': [{'source': 'declaration', 'byte_range': [0, len(evidence)],
                         'sha256': draft._sha(evidence), 'basis': 'synthetic draft declaration'}]}]}
    # Test caller selects coordinates; production never searches for headings.
    if lines is None:
        lines = [3]
    selections = []
    for n, line in enumerate(lines, 1):
        lo, mid = starts[line - 1], starts[line]
        doc = next(d for d in docs.values() if d['byte_range'][0] <= lo < d['byte_range'][1])
        boundary = bundle.index(b'Maintenance Plan', mid)
        hi = bundle.find(b'\n', boundary)
        hi = len(bundle) if hi < 0 else hi + 1
        selections.append({'id': f'span-{n}', 'crosswalk_rows': ['row'],
            'document_ordinal': doc['document_ordinal'], 'document_sha256': doc['sha256'],
            'heading_range': [lo, mid], 'passage_range': [mid, boundary],
            'closing_boundary_range': [boundary, hi]})
    return dict(crosswalk=encoded(crosswalk),
        selection=encoded({'format': 'source_heading_span_selection_v1', 'rows': selections}),
        source_evidence={'declaration': evidence})


@pytest.fixture
def selected(inputs):
    files = draft.prepare(**inputs)
    bundle = ('FILE: neutral.txt\r\nPATH: neutral.txt\r\nCompleteness\r\n'
              'Not confidential. Café 🧪 remains incomplete.\r\n'
              'An embargo does not establish sensitive contents.\r\nMaintenance Plan\r\n'
              'Parent and following context must remain.\r\n').encode()
    rule = {**chunking.DEFAULT_RULE, 'version': '2-custom', 'max_lines': 2}
    manifest = chunking.manifest_from_bytes(bundle, 'neutral.txt', rule)
    return dict(draft_files=files, mode='declared_heading_spans_v1', bundle=bundle,
                manifest=encoded(manifest), max_projection_bytes=1_000_000,
                **declaration(bundle, manifest))


def test_exact_multichunk_utf8_crlf_and_complete_context(selected, tmp_path):
    raw = runtime.prepare_condition(**selected)
    result = runtime.check_condition(raw)
    projection = result['projection']
    span = projection['selections'][0]
    assert len(span['passage']['chunk_coverage']) == 2
    assert span['passage']['text'].endswith('contents.\r\n')
    assert 'Café 🧪' in span['passage']['text']
    assert projection['documents'][0]['text'].encode() == selected['bundle']
    assert projection['scientific_eligibility'] is False
    assert span['semantic_scope'] == 'unverified'
    assert span['heading_correspondence'] == 'draft_declared'
    assert 'Parent and following context must remain.' in result['wire']
    assert 'Explicit draft label/property correspondence' not in result['wire']
    # Arbitrary original schema/data paths are not reopened during captured check.
    for p in tmp_path.glob('*.yaml'):
        p.unlink()
    assert runtime.check_condition(raw) == result


@pytest.mark.parametrize('mutation', ['context', 'candidate', 'direction', 'span', 'mode'])
def test_repinned_derived_projection_is_not_authority(selected, mutation):
    value = json.loads(runtime.prepare_condition(**selected))
    out = value['derived']['projection']
    if mutation == 'context':
        out['documents'][0]['text'] = 'Only selected passage'
    elif mutation == 'candidate':
        out['selections'][0]['correspondences'][0]['candidates'] = []
    elif mutation == 'direction':
        out['selections'][0]['correspondences'][0]['candidates'][0]['direction'] = 'reversed'
    elif mutation == 'span':
        out['selections'][0]['passage']['text'] = 'shortened'
    else:
        value['inputs']['mode'] = 'captured_json_values_v1'
    with pytest.raises(ValueError):
        runtime.check_condition(encoded(value))


@pytest.mark.parametrize('mutation', ['truncated', 'wrong-document', 'wrong-boundary', 'omit-correspondence'])
def test_declaration_boundaries_are_checked_before_admission(selected, mutation):
    args = dict(selected)
    selection = json.loads(args['selection'])
    row = selection['rows'][0]
    if mutation == 'truncated':
        row['passage_range'][0] += 1
    elif mutation == 'wrong-document':
        row['document_ordinal'] += 1
    elif mutation == 'wrong-boundary':
        row['closing_boundary_range'][1] -= 1
    else:
        crosswalk = json.loads(args['crosswalk'])
        other = copy.deepcopy(crosswalk['rows'][0]); other['id'] = 'another'
        other['property_uri'] = draft.RAI + 'personalSensitiveInformation'
        crosswalk['rows'].append(other)
        args['crosswalk'] = encoded(crosswalk)
    args['selection'] = encoded(selection)
    with pytest.raises(ValueError):
        runtime.prepare_condition(**args)


def test_all_many_to_one_predicates_and_direction_preserved(selected):
    crosswalk = json.loads(selected['crosswalk'])
    crosswalk['rows'][0]['property_uri'] = draft.RAI + 'personalSensitiveInformation'
    value = runtime.check_condition(runtime.prepare_condition(**{**selected, 'crosswalk': encoded(crosswalk)}))
    rows = value['projection']['selections'][0]['correspondences'][0]['candidates']
    assert {(r['slot'], r['predicate']) for r in rows} == {
        ('sensitive_elements', 'skos:exactMatch'), ('confidential_elements', 'skos:relatedMatch')}
    assert {r['direction'] for r in rows} == {'Dataset slot to external property'}


def test_strict_complete_values_never_fall_back_to_heading_declarations(inputs):
    files = draft.prepare(**inputs)
    record = json.loads(files['evidence.json'])['records'][0]
    bundle = ('FILE: neutral.txt\nPATH: neutral.txt\n' + record['values']['local']['text'] + '\n'
              + record['values']['external']['text'] + '\n').encode()
    manifest = chunking.manifest_from_bytes(bundle, 'neutral.txt')
    doc = runtime._documents(bundle, manifest)[0][1]
    rows = []
    for kind, value in record['values'].items():
        raw = value['text'].encode(); start = bundle.index(raw)
        rows.append({'evidence_id': record['evidence_id'], 'value_kind': kind,
            'document_ordinal': 1, 'document_sha256': doc['sha256'], 'byte_range': [start, start+len(raw)]})
    args = dict(draft_files=files, mode='captured_json_values_v1', bundle=bundle,
        manifest=encoded(manifest), selection=encoded({'format': 'source_heading_value_membership_v1', 'rows': rows}),
        max_projection_bytes=1_000_000)
    raw = runtime.prepare_condition(**args)
    assert len(runtime.check_condition(raw)['projection']['selections']) == 2
    rows[0]['byte_range'][1] -= 1
    with pytest.raises(ValueError, match='complete JSON value'):
        runtime.prepare_condition(**{**args, 'selection': encoded({'format': 'source_heading_value_membership_v1', 'rows': rows})})


def test_actual_wire_cap_exact_and_one_under(selected):
    raw = runtime.prepare_condition(**selected)
    size = len(runtime.check_condition(raw)['wire'].encode())
    assert runtime.prepare_condition(**{**selected, 'max_projection_bytes': size})
    with pytest.raises(ValueError, match='complete wire bytes'):
        runtime.prepare_condition(**{**selected, 'max_projection_bytes': size - 1})


def test_original_six_explicit_spans_and_three_documents_keep_strict_unsupported(tmp_path):
    root = Path(__file__).resolve().parents[1]
    bundle = (root / 'data/preprocessed/concatenated/CM4AI_preprocessed.txt').read_bytes()
    assert draft._sha(bundle) == '5f81bb53f43f9ec6debc3ab7297bb3897d30c675888eefeaf840ebbbaca9ecc4'
    archive = (root / 'data/ro-crate_packages/CM4AI/raw/cm4ai_release_metadata.zip').read_bytes()
    with zipfile.ZipFile(io.BytesIO(archive)) as stream:
        source = stream.read('cm4ai_release_metadata/ro-crate-metadata.json')
        html = stream.read('cm4ai_release_metadata/ro-crate-datasheet.html')
    value = json.loads(source)['@graph'][1]
    row = {'id': 'observed-development-correspondence', 'heading': 'Completeness',
        'profile_id': 'development-profile', 'local_property': 'completeness',
        'external_property': 'rai:dataCollectionMissingData',
        'external_uri': draft.RAI + 'dataCollectionMissingData'}
    profile = {'format': 'source_heading_profile_v1', 'id': 'development-profile',
        'authority_status': 'draft/unreviewed', 'prefixes': {'rai': draft.RAI},
        'bindings': [{'row_id': row['id'], 'evidence_id': 'development-evidence',
            'source_sha256': draft._sha(source), 'entity_pointer': '/@graph/1',
            'entity_id': value['@id'], 'local_value_sha256': draft._sha(value['completeness'].encode()),
            'external_value_sha256': draft._sha(value['rai:dataCollectionMissingData'].encode())}]}
    # A new lawful capture under this checkout, not a rewritten historical draft.
    files = draft.prepare(base=b'', source=source, profile=encoded(profile),
        crosswalk=encoded({'format': 'source_heading_crosswalk_v1', 'authority_status': 'draft/unreviewed', 'rows': [row]}),
        scope=encoded({'source_sha256': draft._sha(source), 'entity_pointers': ['/@graph/1']}),
        schema_path=root / 'src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
        ttl=(root / 'src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl').read_bytes(),
        recommendations=(root / 'notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv').read_bytes(),
        comprehensive=(root / 'src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv').read_bytes())
    original = json.loads(files['evidence.json'])
    assert original['counts'] == {'matched': 0, 'unmatched': 0, 'ambiguous': 0, 'unsupported': 1}
    assert 'source-local prefix' in original['records'][0]['reason']
    manifest = chunking.manifest_from_bytes(bundle, 'CM4AI_preprocessed.txt')
    args = declaration(bundle, manifest, lines=[5437, 5835, 6244, 6666, 7086, 7536])
    crosswalk = json.loads(args['crosswalk'])
    lo = html.index(b'<div class="summary-label">Completeness</div>')
    hi = html.index(b'</div>', html.index(b'id="completeness"', lo)) + 6
    crosswalk['rows'][0]['evidence'] = [{'source': 'publisher-html', 'byte_range': [lo, hi],
        'sha256': draft._sha(html[lo:hi]),
        'basis': 'Observed label/local-property pair; URI correspondence remains a draft declaration.'}]
    args.update(crosswalk=encoded(crosswalk), source_evidence={'publisher-html': html})
    raw = runtime.prepare_condition(draft_files=files, mode='declared_heading_spans_v1',
        bundle=bundle, manifest=encoded(manifest), max_projection_bytes=2_000_000, **args)
    result = runtime.check_condition(raw)
    out = result['projection']
    assert out['original_structural_status'] == original['counts']
    assert len(out['selections']) == 6 and len(out['documents']) == 3
    assert sum(d['bytes'] for d in out['documents']) == 87_665
    assert {s['passage']['bytes'] for s in out['selections']} == {311}
    assert {s['passage']['sha256'] for s in out['selections']} == {
        'e368a3b44c1b5822e81e2a5deb5cbe0be97d02be299654945c6a3fd70d87741b'}
    for doc in out['documents']:
        assert doc['text'].encode() == bundle[slice(*doc['byte_range'])]
    catalog = json.loads(files['catalog.json'])
    expected = [r for r in catalog['rows'] if r['property_uri'] == row['external_uri']]
    assert expected and all(s['correspondences'][0]['candidates'] == expected for s in out['selections'])
    assert all(value[k] not in result['wire'] for k in ('completeness', 'rai:dataCollectionMissingData'))
    (tmp_path / 'routing-capture.json').write_bytes(raw)
    (tmp_path / 'routing-projection.json').write_bytes(encoded(result))


def test_captured_schema_replay_never_resolves_original_aliases(selected, monkeypatch):
    raw = runtime.prepare_condition(**selected)
    before = runtime.check_condition(raw)
    rows = json.loads(selected['draft_files']['inputs.json'])['authority']['schema']
    import os
    forbidden = {os.path.abspath(row['path']) for row in rows}
    original = Path.resolve
    def checked(path, *a, **kw):
        if os.path.abspath(path) in forbidden:
            raise AssertionError('captured schema path must not be resolved')
        return original(path, *a, **kw)
    monkeypatch.setattr(Path, 'resolve', checked)
    assert runtime.check_condition(raw) == before
