"""Real captured fictional source readings; no empirical labels or scoring runs."""
import base64
import builtins
import copy
import csv
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from data_sheets_schema import attainability_aggregation as aa
from data_sheets_schema import attainability_figure as figure
from data_sheets_schema.evaluation_context import PREDICATES
from tests.test_attainability_aggregation import fixture, repin_json
from tests.test_reference_rescore import current_record

ROOT = Path(__file__).resolve().parents[1]


def save_sidecar(path, selection):
    closure = aa.capture(selection)
    document = {'capture': closure, 'report': aa.recheck_captured(closure)}
    path.write_bytes(aa.canonical(document) + b'\n')
    return path, document


def change_score(selection, evaluation, selected, key, score):
    for group in evaluation['elements']:
        for item in group['sub_elements']:
            if item['item_id'] == key:
                item['score'] = score
                for unit in item['unit_scores']:
                    unit['score'] = score
        group['element_score'] = sum(item['score'] or 0 for item in group['sub_elements'])
    total = sum(group['element_score'] for group in evaluation['elements'])
    overall = evaluation['overall_score']
    overall.update(total_points=total, normalized_percentage=100 * total / overall['adjusted_max_points'],
                   fixed_percentage=100 * total / 50)
    return repin_json(selection, selected, 'evaluation', evaluation, 'changed-evaluation')


def prepared_fixture(tmp_path, **kwargs):
    selection, *_ = fixture(tmp_path / 'inputs', **kwargs)
    path, document = save_sidecar(tmp_path / 'sidecar.json', selection)
    return figure.prepare(path), path, document


def table(raw):
    return [{k: json.loads(v) for k, v in row.items()} for row in csv.DictReader(io.StringIO(raw.decode()))]


@pytest.mark.parametrize('name,readings,options,score,expected', [
    ('supported-zero', [('E1.2', None, 'supported')], {}, 0, ('supported', 'applicable', 0)),
    ('absent-zero', [('E1.2', None, 'not_stated_in_source')], {}, 0, ('not_stated_in_source', 'applicable', 0)),
    ('partial', [('E1.2', None, 'partly_supported')], {}, 1, ('partly_supported', 'applicable', 1)),
    ('conflict', [('E1.2', None, 'not_stated_in_source'), ('E1.2', 'a', 'supported')], {'routes': ('a',)}, 1, ('conflict', 'applicable', 1)),
    ('unregistered', [('E1.2', None, 'not_stated_in_source'), ('E1.2', 'extra', 'supported')], {}, 1, ('unknown', 'applicable', 1)),
    ('resolved', [('E1.2', None, 'not_stated_in_source'), ('E1.2', 'a', 'supported')], {'routes': ('a',), 'adjudicate': 'supported'}, 1, ('supported', 'applicable', 1)),
    ('null-score', [('E1.2', None, 'supported')], {}, None, ('supported', 'applicable', None)),
    ('absent-positive', [('E1.2', None, 'not_stated_in_source')], {}, 1, ('not_stated_in_source', 'applicable', 1)),
])
def test_literal_state_score_and_review_oracle(tmp_path, name, readings, options, score, expected):
    selection, evaluation, selected, _ = fixture(tmp_path / name, readings=readings, **options)
    if score != 1:
        selection = change_score(selection, evaluation, selected, 'E1.2', score)
    path, original = save_sidecar(tmp_path / 'sidecar.json', selection)
    prepared = figure.prepare(path)
    report = prepared.report(); row = report['rows'][0]
    item = next(i for i in row['source_inventory'] if i['item_id'] == 'E1.2')
    assert (item['final_status'], item['applicability'], item['recorded_score']) == expected
    title = json.loads(figure._cell_title(row, item))
    assert title['item'] == item and title['row_reasons'] == row['reasons']
    assert title['recorded_absent_positive_review_finding'] == (name == 'absent-positive')
    if name == 'supported-zero': assert title['display'] == '0 / declared source supported'
    if name == 'absent-zero':
        assert title['display'] == '0 / declared source absent'
        assert row['state'] == 'unavailable'
        assert row['reasons'] == [{'code': 'zero_eligible_items', 'detail': 'No known-applicable supported item maximum'}]
    if name == 'null-score':
        assert title['display'].startswith('— /') and row['state'] == 'unavailable'
    if name == 'resolved':
        assert item['initial_status'] == 'conflict' and item['resolution_sha256']
    assert prepared.report() == original['report']
    report['rows'].clear()
    assert prepared.report() == original['report']


@pytest.mark.parametrize('known', [False, True])
def test_actual_unknown_and_not_applicable_remain_independent(tmp_path, known):
    selection, evaluation, selected, _ = fixture(tmp_path / 'inputs', readings=[('E4.4', None, 'supported')], context=known)
    if known:
        context = {predicate: False for predicate in PREDICATES}
        evaluation = current_record(selection.parent / 'record.yaml', context=context)
        old = json.loads((selection.parent / selected['rows'][0]['evaluation']['path']).read_bytes())
        evaluation['metadata'].update({k:v for k,v in old['metadata'].items() if k != 'context_sha256'})
        selection = repin_json(selection, selected, 'context', context, 'negative-context')
        selection = repin_json(selection, json.loads(selection.read_bytes()), 'evaluation', evaluation, 'negative-evaluation')
    path, document = save_sidecar(tmp_path / 'sidecar.json', selection)
    prepared = figure.prepare(path); row = prepared.report()['rows'][0]
    item = next(i for i in row['source_inventory'] if i['item_id'] == 'E4.4')
    assert item['final_status'] == 'supported'
    assert item['applicability'] == ('not_applicable' if known else 'unknown')
    assert item['recorded_score'] == (None if known else 1)
    svg = figure._svg([row], 0, 1, figure.DEFAULT_LIMITS.svg_bytes)
    ET.fromstring(svg)
    assert (b'N/A' if known else b'Applicability ?') in svg
    assert json.loads(prepared.checked_payload) == document['report']


def mixed_sidecar(tmp_path):
    captures = []
    for number in [20, 10]:
        selection, *_ = fixture(tmp_path / str(number), number=number)
        captures.append(aa.capture(selection))
    # Compose one explicit fictional selection from actual individually captured
    # inputs, without changing any source/contract/evaluation bytes or verdicts.
    blobs = {}; rows = []
    for capture in captures:
        for blob in capture['blobs']:
            if blob['sha256'] != capture['selection']['sha256']:
                blobs[blob['sha256']] = blob
            else:
                rows.extend(json.loads(base64.b64decode(blob['content_base64']))['rows'])
    raw = aa.canonical({'format': 'd4d-attainability-report-selection', 'version': 1, 'rows': rows})
    selection = aa.pin(str(tmp_path / 'explicit-mixed-selection.json'), raw)
    blobs[selection['sha256']] = {'sha256': selection['sha256'], 'bytes': len(raw),
                                 'content_base64': base64.b64encode(raw).decode()}
    capture = {**captures[0], 'selection': selection, 'blobs': sorted(blobs.values(), key=lambda v:v['sha256'])}
    document = {'capture': capture, 'report': aa.recheck_captured(capture)}
    path = tmp_path / 'mixed.json'; path.write_bytes(aa.canonical(document))
    return path, document


def test_actual_cli_all_products_equal_checked_mixed_rosters(tmp_path):
    path, document = mixed_sidecar(tmp_path)
    before = {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    output = tmp_path / 'rendered'
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(ROOT / 'src'),
           'MPLCONFIGDIR': str(tmp_path / 'matplotlib-cache')}
    done = subprocess.run([sys.executable, str(ROOT / 'scripts/figures/attainability_heatmap.py'),
                           '--sidecar', str(path), '--output-dir', str(output)], env=env,
                          cwd=tmp_path, capture_output=True, timeout=90)
    assert done.returncode == 0, done.stderr.decode()
    report = json.loads((output / 'checked_report.json').read_bytes())
    assert report == document['report']
    rows = table((output / 'rows.csv').read_bytes()); items = table((output / 'items.csv').read_bytes())
    assert [r['historical_bases']['fixed_max'] for r in rows] == [88, 50]
    assert [r['basis']['percentage'] for r in rows] == [100, 100]
    assert [len(r['source_inventory']) for r in report['rows']] == [20, 50]
    assert len(items) == 70
    for index, row in enumerate(report['rows'], 1):
        assert rows[index-1] == {'selection_index': index, **{k:v for k,v in row.items() if k != 'source_inventory'}}
        actual = [item for item in items if item['selection_index'] == index]
        assert [{k:v for k,v in item.items() if k in row['source_inventory'][0]} for item in actual] == row['source_inventory']
    root = ET.parse(output / 'attainability-001.svg').getroot()
    ns = {'s': 'http://www.w3.org/2000/svg'}
    titles = {g.attrib['id']:json.loads(g.find('s:title', ns).text) for g in root.findall('.//s:g', ns)
              if g.attrib.get('id', '').startswith('row-')}
    assert len(titles) == 70
    assert titles['row-1-item-1']['item'] == report['rows'][0]['source_inventory'][0]
    assert titles['row-2-item-50']['item'] == report['rows'][1]['source_inventory'][-1]
    manifest = json.loads((output / 'manifest.json').read_bytes())
    assert manifest['state'] == 'complete' and manifest['rows'] == 2 and manifest['items'] == 70
    assert not {'cohort', 'project', 'model', 'aggregate_score'} & manifest.keys()
    for name, identity in manifest['artifacts'].items():
        raw = (output / name).read_bytes(); assert len(raw) == identity['bytes'] and hashlib.sha256(raw).hexdigest() == identity['sha256']
    assert all(p.read_bytes() == raw for p, raw in before.items())


def test_pagination_preserves_selected_order_and_all_item_ids(tmp_path):
    path, document = mixed_sidecar(tmp_path)
    prepared = figure.prepare(path, limits=replace(figure.DEFAULT_LIMITS, rows_per_page=1))
    artifacts = figure._artifacts(prepared.report(), prepared.checked_payload, prepared.limits)
    assert sorted(n for n in artifacts if n.endswith('.svg')) == ['attainability-001.svg', 'attainability-002.svg']
    assert b'row-1-item-20' in artifacts['attainability-001.svg'] and b'row-2-item-50' in artifacts['attainability-002.svg']
    assert b'row-2-item-' not in artifacts['attainability-001.svg']


@pytest.mark.parametrize('mutation', ['label', 'score', 'bool-number', 'missing_blob', 'corrupt_blob', 'extra_blob', 'implementation'])
def test_tampered_report_or_capture_cannot_supply_a_verdict(tmp_path, mutation):
    _, path, document = prepared_fixture(tmp_path)
    if mutation in ('label', 'score', 'bool-number'):
        item = document['report']['rows'][0]['source_inventory'][1]
        item[{'label':'final_status', 'score':'recorded_score', 'bool-number':'maximum'}[mutation]] = {
            'label':'not_stated_in_source', 'score':0, 'bool-number':True}[mutation]
    elif mutation == 'missing_blob': document['capture']['blobs'].pop()
    elif mutation == 'corrupt_blob': document['capture']['blobs'][0]['content_base64'] = 'AAAA'
    elif mutation == 'extra_blob':
        raw = b'unrelated'; document['capture']['blobs'].append({'sha256': aa.sha(raw), 'bytes':len(raw), 'content_base64':base64.b64encode(raw).decode()})
    else: document['capture']['implementation'][0]['sha256'] = '0' * 64
    path.write_bytes(aa.canonical(document))
    with pytest.raises(ValueError): figure.prepare(path)


@pytest.mark.parametrize('raw', [b'{"capture":{},"capture":{},"report":{}}', b'{"capture":NaN,"report":{}}',
                                  b'{"report":{}}', b'{}', b'[]', b'{"capture":{},"report":{},"extra":1}'])
def test_bare_duplicate_nonfinite_and_extra_envelopes_refuse(tmp_path, raw):
    path = tmp_path / 'invalid.json'; path.write_bytes(raw)
    with pytest.raises(ValueError): figure.prepare(path)


def test_captured_recheck_and_projection_with_original_paths_unavailable(tmp_path, monkeypatch):
    prepared, path, expected = prepared_fixture(tmp_path)
    (tmp_path / 'inputs').rename(tmp_path / 'retained-inputs')
    def refuse(*args, **kwargs): pytest.fail('ambient I/O during captured recheck/projection')
    with monkeypatch.context() as m:
        for name in ('open', 'read_bytes', 'read_text', 'resolve', 'cwd'):
            m.setattr(Path, name, refuse)
        m.setattr(builtins, 'open', refuse); m.setattr(subprocess, 'Popen', refuse); m.setattr(socket, 'socket', refuse)
        envelope, payload = figure._checked(prepared.selected.raw, prepared.limits)
        assert json.loads(payload) == expected['report']
        assert figure._csv(({'item': i} for i in expected['report']['rows'][0]['source_inventory']), 1_000_000)
        assert figure._cell_title(expected['report']['rows'][0], expected['report']['rows'][0]['source_inventory'][0])
    # Ordinary prepare also consults only the sidecar and current implementation,
    # not any missing original evaluation/source/rubric input.
    assert figure.prepare(path).report() == expected['report']


@pytest.mark.parametrize('mode', ['directory', 'sidecar', 'symlink', 'dangling', 'hardlink'])
def test_existing_destination_and_aliases_are_preserved(tmp_path, mode):
    prepared, path, _ = prepared_fixture(tmp_path); raw = path.read_bytes(); output = tmp_path / 'output'
    if mode == 'directory': output.mkdir(); (output / 'keep').write_bytes(b'keep')
    elif mode == 'sidecar': output = path
    elif mode == 'hardlink': os.link(path, output)
    else: output.symlink_to(path if mode == 'symlink' else tmp_path / 'missing')
    with pytest.raises(ValueError, match='new'): figure.publish(prepared, output)
    assert path.read_bytes() == raw
    if mode == 'directory': assert (output / 'keep').read_bytes() == b'keep'


@pytest.mark.parametrize('destination', ['file', 'ancestor', 'aliased-parent'])
def test_absent_captured_inputs_and_ancestors_cannot_become_outputs(tmp_path, destination):
    prepared, _, _ = prepared_fixture(tmp_path)
    source = tmp_path / 'inputs'; source.rename(tmp_path / 'retained')
    if destination == 'file':
        source.mkdir(); output = source / 'bundle.txt'
    elif destination == 'ancestor': output = source
    else:
        source.mkdir(); alias = tmp_path / 'alias'; alias.symlink_to(source, target_is_directory=True)
        output = alias / 'bundle.txt'
    with pytest.raises(ValueError, match='aliases'): figure.publish(prepared, output)
    assert not output.exists()


@pytest.mark.parametrize('mutation', ['raw', 'same-bytes-new-inode', 'forged-report', 'missing-implementation'])
def test_post_prepare_drift_and_fabricated_private_verdict_refuse(tmp_path, mutation):
    prepared, path, _ = prepared_fixture(tmp_path)
    if mutation == 'raw': path.write_bytes(path.read_bytes() + b'\n')
    elif mutation == 'same-bytes-new-inode':
        replacement = tmp_path / 'replacement'; replacement.write_bytes(path.read_bytes()); replacement.replace(path)
    elif mutation == 'forged-report': prepared = replace(prepared, checked_payload=b'{}')
    else: prepared = replace(prepared, implementation=())
    with pytest.raises(ValueError): figure.publish(prepared, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_partial_publication_retained_without_complete_manifest(tmp_path, monkeypatch):
    prepared, _, _ = prepared_fixture(tmp_path)
    original = figure._publish_file; calls = []
    def fail_second(fd, name, raw):
        calls.append(name)
        if len(calls) == 2: raise OSError('injected publication failure')
        original(fd, name, raw)
    monkeypatch.setattr(figure, '_publish_file', fail_second)
    output = tmp_path / 'out'
    with pytest.raises(OSError, match='injected'): figure.publish(prepared, output)
    assert (output / calls[0]).is_file() and not (output / 'manifest.json').exists()
    with pytest.raises(ValueError, match='new'): figure.publish(prepared, output)


def test_publication_directory_replacement_does_not_gain_manifest(tmp_path, monkeypatch):
    prepared, _, _ = prepared_fixture(tmp_path)
    output = tmp_path / 'out'; displaced = tmp_path / 'displaced'; original = figure._publish_file; moved = []
    def move_directory(fd, name, raw):
        original(fd, name, raw)
        if not moved:
            output.rename(displaced); output.mkdir(); moved.append(True)
    monkeypatch.setattr(figure, '_publish_file', move_directory)
    with pytest.raises(ValueError, match='moved or replaced'): figure.publish(prepared, output)
    assert not (output / 'manifest.json').exists() and not (displaced / 'manifest.json').exists()


@pytest.mark.parametrize('limit,value', [('envelope_bytes', 1), ('artifact_bytes', 1), ('svg_bytes', 1),
                                         ('total_output_bytes', 1), ('items_per_row', 1)])
def test_finite_limits_refuse_without_creating_destination(tmp_path, limit, value):
    _, path, _ = prepared_fixture(tmp_path)
    limits = replace(figure.DEFAULT_LIMITS, **{limit:value})
    with pytest.raises(ValueError, match='limit|bounded'):
        figure.publish(figure.prepare(path, limits=limits), tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


@pytest.mark.parametrize('value', [True, 0, 257])
def test_limits_cannot_be_raised_or_bool_coerced(value):
    with pytest.raises(ValueError): replace(figure.DEFAULT_LIMITS, rows=value)


def test_xml_escaping_csv_literals_and_full_state_retention(tmp_path):
    selection, evaluation, selected, _ = fixture(tmp_path / 'inputs')
    source = selection.parent / selected['rows'][0]['evaluation']['path']
    strange = '=1+1<&".json'; changed = source.with_name(strange); changed.write_bytes(source.read_bytes())
    selected['rows'][0]['evaluation']['path'] = strange
    selection.write_bytes(aa.canonical(selected))
    path, expected = save_sidecar(tmp_path / 'sidecar.json', selection)
    prepared = figure.prepare(path); output = tmp_path / 'out'; figure.publish(prepared, output)
    assert table((output / 'rows.csv').read_bytes())[0]['evaluation']['path'] == strange
    root = ET.parse(output / 'attainability-001.svg').getroot()
    assert strange in ''.join(root.itertext())
    assert json.loads((output / 'checked_report.json').read_bytes()) == expected['report']
    raw = figure._csv(iter([{'text': '=cmd()', 'zero':0, 'null':None, 'boolean':False}]), 1000)
    parsed = next(csv.DictReader(io.StringIO(raw.decode())))
    assert parsed == {'text':'"=cmd()"', 'zero':'0', 'null':'null', 'boolean':'false'}
