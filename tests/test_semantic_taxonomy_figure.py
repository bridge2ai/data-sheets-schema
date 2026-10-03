"""Figure 11 uses captured structured issues, explicit selection and count units."""
import copy
import csv
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema.exceptions import ValidationError
import yaml

from data_sheets_schema import semantic_taxonomy_figure as figure
from data_sheets_schema.evaluation_context import context_digest
from data_sheets_schema.judge_contract import evaluation_contract
from data_sheets_schema.resources import resource_path
from data_sheets_schema.semantic_evidence import check_evidence, check_issue_links
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from tests.test_evaluation.test_semantic_evidence import CONTEXT, ROOT, _groups, _item, _rescore, _row
from tests.test_evaluation.test_semantic_evidence_v3 import current


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')
    return path


def fixture(tmp_path, rubric='rubric20', version='3.0', context=CONTEXT):
    raw = b'id: urn:fixture\ntitle: Fixture title\ncreators:\n- name: Alice\n- name: Bob\nversion_access:\n  version_details: Original release\n'
    path = tmp_path / f'{rubric}-{version}.yaml'
    path.write_bytes(raw)
    result = current(rubric, (yaml.safe_load(raw), sha(raw)))
    selected = select_semantic_instrument(rubric, version)
    rubric_raw = resource_path(selected.rubric_path).read_bytes()
    contract = evaluation_contract(rubric, yaml.safe_load(rubric_raw), context, yaml.safe_load(raw))
    result.update(version=version, applicability_context=contract['context'], evaluation_scope=contract['scope'])
    result['metadata'].update(instrument_sha256=sha(resource_path(selected.definition_path).read_bytes()),
                              rubric_sha256=sha(rubric_raw), context_sha256=context_digest(contract['context']))
    for group, items in _groups(result):
        for i, item in enumerate(items, 1):
            key = f'E{group["id"]}.{i}' if rubric == 'rubric10' else f'Q{item["id"]}'
            rule = contract['items'][key]
            score = rule['fixed_max_score'] if rule['applicable'] else None
            item.update(name=rule['name'], applicable=rule['applicable'], applicability_status=rule['status'],
                        applicability_evidence=rule['evidence'], score=score)
            item['unit_scores'][0]['score'] = score
    _rescore(result)
    rating = tmp_path / f'{rubric}-{version}.json'
    write_json(rating, result)
    ctx = tmp_path / f'{rubric}-{version}-context.yaml'
    ctx.write_text(yaml.safe_dump(context))
    return result, rating, path, ctx


def selection(tmp_path, rows):
    return write_json(tmp_path / 'selection.json', {'kind': figure.KIND, 'version': 1, 'ratings': rows})


def entry(rating, inp=None, context=None, group='explicit group'):
    result = {'rating': str(rating), 'group': group}
    if inp is not None:
        result['input'] = str(inp)
    if context is not None:
        result['context'] = str(context)
    return result


def issue(result, ids, **changes):
    result['semantic_analysis']['issues_detected'].append({
        'category': 'attribution', 'type': 'content_accuracy', 'severity': 'high',
        'score_effect': 'lowered', 'item_ids': ids, 'description': 'consent license privacy',
        'fields_involved': ['title'], 'recommendation': 'Review the statement', **changes})


def csv_rows(path):
    return list(csv.DictReader(path.open()))


def test_existing_evidence_findings_match_pre_extraction_bytes_and_order():
    baseline = json.loads((ROOT / 'tests/fixtures/semantic_taxonomy_evidence_baseline.json').read_bytes())
    assert baseline['source_commit'] == '601ca52ac8b620a4a5ad594c09b9973461c499e7'
    for case in baseline['cases']:
        actual = check_evidence(case['rating'], case['document'], case['rubric'])
        assert [asdict(f) for f in actual.findings] == case['findings'], case['name']
        links = [asdict(f) for f in check_issue_links(case['rating'], case['rubric']).findings]
        assert case['findings'][-len(links):] == links if links else True


@pytest.mark.parametrize('rubric,version', [('rubric10','3.0'), ('rubric20','3.0'), ('rubric20','4.0')])
def test_supported_instruments_use_real_schema_scope_and_exact_input(tmp_path, rubric, version):
    result, rating, inp, ctx = fixture(tmp_path, rubric, version)
    prepared = figure.prepare(selection(tmp_path, [entry(rating, inp, ctx)]))
    row = prepared.report()['ratings'][0]
    assert row['validation'] == figure.BOUND
    assert row['evidence'] == {'passed': True, 'findings': []}
    assert row['resources']['definition']['sha256'] == result['metadata']['instrument_sha256']
    assert row['inputs']['input']['sha256'] == sha(inp.read_bytes())
    assert prepared.report()['groups'][0]['zero_issue_occurrences'] == 1


def test_real_plot_csv_json_share_units_repeats_zeroes_and_mixed_validation(tmp_path, monkeypatch):
    doc, rating, inp, ctx = fixture(tmp_path)
    for key in ('Q1', 'Q2'):
        _row(doc, key, score=0, cited=[{'path': 'title', 'quote': 'Fixture title'}])
    issue(doc, ['Q1','Q2'])
    issue(doc, [], score_effect='noted_only', category='count_size')
    write_json(rating, doc)
    zero, zero_rating, _, _ = fixture(tmp_path, 'rubric10')
    # Same category vocabulary but a different instrument must get a separate group.
    sel = selection(tmp_path, [entry(rating, inp, ctx), entry(rating), entry(zero_rating)])
    before = {p: p.read_bytes() for p in (sel, rating, inp, ctx, zero_rating)}
    prepared = figure.prepare(sel)
    # Rendering cannot reopen/reparse selected live inputs. Verification uses
    # Capture.verify; every remaining read must therefore be integrity checking.
    def captured_only(raw):
        assert raw == prepared.payload
        return json.loads(raw)
    monkeypatch.setattr(figure, '_json', captured_only)
    monkeypatch.setattr(figure, '_yaml', lambda _: pytest.fail('rendering reparsed a live input'))
    out = tmp_path / 'new-output'
    final = figure.publish(prepared, out)
    report = final['report']
    group = report['groups'][0]
    assert group['selection_indices'] == [0,1]
    assert group['validation_counts'] == {figure.BOUND: 1, figure.DECLARED: 1}
    assert group['category_counts']['attribution'] == group['category_counts']['count_size'] == 2
    assert group['high_severity_lowered'] == 2
    assert group['item_counts'] == {'Q1':2,'Q2':2}
    assert report['groups'][1]['issue_count'] == 0
    assert len(csv_rows(out/'ratings.csv')) == 3
    assert len(csv_rows(out/'issues.csv')) == len(csv_rows(out/'item_links.csv')) == 4
    assert csv_rows(out/'lowered.csv')[0]['high_severity_lowered_issue_count'] == '2'
    assert sum(int(r['issue_count']) for r in csv_rows(out/'categories.csv')) == 4
    svg = (out/'fig11_semantic_taxonomy.svg').read_text()
    assert '<svg' in svg and 'input-bound: 1; declaration-only: 1' in svg
    assert 'zero-issue: 1' in svg and 'Evaluator declarations only' in svg
    assert json.loads((out/'report.json').read_bytes()) == final
    assert final['payload_sha256'] == sha(prepared.payload)
    for name, pin in final['artifacts'].items():
        assert pin['sha256'] == sha((out/name).read_bytes())
        assert pin['bytes'] == (out/name).stat().st_size
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize('changes,match', [
    ({'item_ids':['Q999']}, 'unknown_item_id'),
    ({'item_ids':['Q8']}, 'non_applicable_item_id'),
    ({'item_ids':['Q1']}, 'lowered_issue_without_deduction'),
    ({'category':'invented'}, ''), ({'type':'invented'}, ''),
    ({'score_effect':'noted_only','item_ids':['Q1']}, ''),
])
def test_invalid_links_and_taxonomy_refuse_even_without_an_input(tmp_path, changes, match):
    doc, rating, _, _ = fixture(tmp_path)
    issue(doc, ['Q1'], **({k:v for k,v in changes.items() if k != 'item_ids'}))
    doc['semantic_analysis']['issues_detected'][0].update(changes)
    write_json(rating, doc)
    with pytest.raises((ValueError, ValidationError), match=match):
        figure.prepare(selection(tmp_path, [entry(rating)]))


@pytest.mark.parametrize('change', ['instrument_sha256','rubric_sha256','evidence_authority_sha256'])
def test_all_recorded_instrument_digests_are_verified(tmp_path, change):
    doc, rating, _, _ = fixture(tmp_path)
    doc['metadata'][change] = '0'*64
    write_json(rating, doc)
    with pytest.raises(ValueError, match=change):
        figure.prepare(selection(tmp_path, [entry(rating)]))


def test_bound_evidence_recomputes_claims_ignores_saved_acceptance_and_keeps_warnings(tmp_path):
    doc, rating, inp, ctx = fixture(tmp_path)
    doc['evaluator_evidence'] = {'passed':True}
    _row(doc, 'Q1', counts=[{'path':'creators','claimed':38}])
    write_json(rating, doc)
    assert figure.prepare(selection(tmp_path, [entry(rating)])).report()['ratings'][0]['evidence'] is None
    with pytest.raises(ValueError, match='count_mismatch'):
        figure.prepare(selection(tmp_path, [entry(rating, inp, ctx)]))
    _row(doc, 'Q1', counts=[{'path':'creators','claimed':2}])
    _row(doc, 'Q13', score=3, cited=[{'path':'id'}])
    write_json(rating, doc)
    report = figure.prepare(selection(tmp_path, [entry(rating, inp, ctx)])).report()
    codes = [f['code'] for f in report['ratings'][0]['evidence']['findings']]
    assert 'uncovered_populated_field' in codes and 'deduction_without_linked_issue' in codes
    with pytest.raises(ValueError, match='caller context'):
        figure.prepare(selection(tmp_path, [entry(rating, inp)]))


def test_groups_do_not_pool_declared_models_types_rubrics_versions_or_caller_groups(tmp_path):
    rows = []
    for rubric, version in [('rubric20','3.0'),('rubric20','4.0'),('rubric10','3.0')]:
        doc, rating, _, _ = fixture(tmp_path, rubric, version)
        rows.append(entry(rating))
    doc, original, _, _ = fixture(tmp_path)
    rows.append(entry(original, group='another group'))
    for i, changes in enumerate([{'name':'other'}, {'evaluation_type':'other'}, {'name':''}]):
        model = {**doc['model'], **changes}
        changed = copy.deepcopy(doc)
        changed['model'] = model
        path = write_json(tmp_path/f'other-{i}.json',changed)
        rows.append(entry(path))
        if not model['name']:
            rows.append(entry(path))
    report = figure.prepare(selection(tmp_path, rows)).report()
    assert len(report['groups']) == len(rows)
    assert [g['selection_indices'] for g in report['groups']] == [[i] for i in range(len(rows))]


@pytest.mark.parametrize('version', ['1.2','2.0','5.0',[],None])
def test_legacy_and_malformed_versions_never_fall_back_to_prose(tmp_path, version):
    doc, rating, _, _ = fixture(tmp_path)
    doc['version'] = version
    write_json(rating, doc)
    with pytest.raises(ValueError, match='only structured'):
        figure.prepare(selection(tmp_path,[entry(rating)]))


@pytest.mark.parametrize('which', ['selection','rating','input','context','resource'])
def test_changed_captured_bytes_refuse_before_publication(tmp_path, monkeypatch, which):
    _, rating, inp, ctx = fixture(tmp_path)
    sel = selection(tmp_path,[entry(rating,inp,ctx)])
    if which == 'resource':
        original = figure.resource_path
        copied = tmp_path/'definition.md'
        selected = select_semantic_instrument('rubric20','3.0')
        copied.write_bytes(original(selected.definition_path).read_bytes())
        monkeypatch.setattr(figure,'resource_path',lambda path: copied if path == selected.definition_path else original(path))
        target = copied
    else:
        target = {'selection':sel,'rating':rating,'input':inp,'context':ctx}[which]
    prepared = figure.prepare(sel)
    target.write_bytes(target.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='changed'):
        figure.publish(prepared,tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('kind',['directory','symlink','hardlink','input'])
def test_publication_never_overwrites_or_follows_existing_targets(tmp_path, kind):
    _, rating, _, _ = fixture(tmp_path)
    prepared = figure.prepare(selection(tmp_path,[entry(rating)]))
    out = tmp_path/'out'
    if kind == 'directory': out.mkdir()
    elif kind == 'symlink': out.symlink_to(rating)
    elif kind == 'hardlink': os.link(rating,out)
    else: out=rating
    before = rating.read_bytes()
    with pytest.raises(FileExistsError): figure.publish(prepared,out)
    assert rating.read_bytes()==before


def test_partial_publication_never_gets_a_complete_manifest(tmp_path, monkeypatch):
    _, rating, _, _ = fixture(tmp_path)
    prepared = figure.prepare(selection(tmp_path,[entry(rating)]))
    original = figure._publish_file
    def failure(fd,name,raw):
        if name=='issues.csv': raise OSError('injected publication failure')
        original(fd,name,raw)
    monkeypatch.setattr(figure,'_publish_file',failure)
    out=tmp_path/'out'
    with pytest.raises(OSError,match='injected'): figure.publish(prepared,out)
    assert out.is_dir() and (out/'ratings.csv').is_file()
    assert not (out/'report.json').exists()
    with pytest.raises(FileExistsError): figure.publish(prepared,out)


@pytest.mark.parametrize('bad', [b'{"kind":"x","kind":"y"}', b'{"version":NaN}',
    b'{"kind":"semantic_taxonomy_figure_selection","version":true,"ratings":[]}',
    b'{"kind":"semantic_taxonomy_figure_selection","version":1,"ratings":[]}'])
def test_selection_refuses_ambiguous_or_empty_values(tmp_path,bad):
    path=tmp_path/'selection.json'; path.write_bytes(bad)
    with pytest.raises(ValueError): figure.prepare(path)


@pytest.mark.parametrize('raw',[b'id: one\nid: two\n',b'foo: &a [*a]\n',b'foo: .nan\n',b'1: ambiguous\n', b'foo: {<<: {id: one}}\n'])
def test_captured_yaml_refuses_ambiguity_and_unbounded_graphs(raw):
    with pytest.raises(ValueError): figure._yaml(raw)


def test_cli_writes_actual_svg_and_returns_nonzero_without_overwriting(tmp_path):
    _, rating, _, _ = fixture(tmp_path)
    sel=selection(tmp_path,[entry(rating)])
    out=tmp_path/'out'
    cmd=[sys.executable,str(ROOT/'scripts/report_semantic_taxonomy.py'),'--selection',str(sel),'--output-dir',str(out)]
    first=subprocess.run(cmd,capture_output=True,text=True)
    assert first.returncode==0,first.stderr
    assert json.loads(first.stdout)['state']=='complete'
    hashes={p.name:sha(p.read_bytes()) for p in out.iterdir()}
    again=subprocess.run(cmd,capture_output=True,text=True)
    assert again.returncode==1 and 'fresh' in again.stderr
    assert hashes=={p.name:sha(p.read_bytes()) for p in out.iterdir()}


def test_structured_consumer_never_invokes_a_legacy_classifier(tmp_path, monkeypatch):
    doc, rating, _, _ = fixture(tmp_path)
    _row(doc,'Q1',score=0,cited=[{'path':'title'}])
    issue(doc,['Q1'])
    write_json(rating,doc)
    shared = figure.issue_taxonomy
    calls = []
    def checked(value):
        calls.append(value['version'])
        return shared(value,legacy_classifier=lambda _: pytest.fail('legacy prose classifier invoked'))
    monkeypatch.setattr(figure,'issue_taxonomy',checked)
    report=figure.prepare(selection(tmp_path,[entry(rating)])).report()
    assert calls==['3.0']
    assert report['groups'][0]['category_counts']['attribution']==1
    assert report['groups'][0]['category_counts']['consent_ethics']==0


def test_shared_validation_resource_drift_is_refused(tmp_path,monkeypatch):
    _, rating, _, _=fixture(tmp_path)
    selected=select_semantic_instrument('rubric20','3.0')
    schema=tmp_path/'schema.json'
    schema.write_bytes(figure.resource_path(selected.schema_path).read_bytes())
    original=figure.resource_path
    monkeypatch.setattr(figure,'resource_path',lambda path: schema if path==selected.schema_path else original(path))
    validate=figure.validate_scope
    def drift(*args,**kwargs):
        result=validate(*args,**kwargs)
        schema.write_bytes(schema.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(figure,'validate_scope',drift)
    with pytest.raises(ValueError,match='changed'):
        figure.prepare(selection(tmp_path,[entry(rating)]))


def test_drift_during_plotting_refuses_without_reserving_output(tmp_path,monkeypatch):
    _,rating,_,_=fixture(tmp_path)
    prepared=figure.prepare(selection(tmp_path,[entry(rating)]))
    def drift(_):
        rating.write_bytes(rating.read_bytes()+b'\n')
        return b'<svg/>'
    monkeypatch.setattr(figure,'_svg',drift)
    with pytest.raises(ValueError,match='changed'):
        figure.publish(prepared,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_written_output_drift_cannot_receive_complete_manifest(tmp_path,monkeypatch):
    _,rating,_,_=fixture(tmp_path)
    prepared=figure.prepare(selection(tmp_path,[entry(rating)]))
    out=tmp_path/'out'
    original=figure._publish_file
    def tamper(fd,name,raw):
        original(fd,name,raw)
        if name=='issues.csv':
            (out/'ratings.csv').write_bytes(b'changed')
    monkeypatch.setattr(figure,'_publish_file',tamper)
    with pytest.raises(ValueError,match='published artifact changed'):
        figure.publish(prepared,out)
    assert not (out/'report.json').exists()


def test_destination_created_during_render_is_preserved(tmp_path,monkeypatch):
    _,rating,_,_=fixture(tmp_path)
    prepared=figure.prepare(selection(tmp_path,[entry(rating)]))
    out=tmp_path/'out'
    def occupy(_):
        out.mkdir()
        (out/'sentinel').write_bytes(b'keep')
        return b'<svg/>'
    monkeypatch.setattr(figure,'_svg',occupy)
    with pytest.raises(FileExistsError): figure.publish(prepared,out)
    assert {p.name:p.read_bytes() for p in out.iterdir()}=={'sentinel':b'keep'}


@pytest.mark.parametrize('bound',['MAX_ROWS','MAX_GROUPS','MAX_LABEL_CHARS','MAX_FILE_BYTES','MAX_TOTAL_BYTES'])
def test_bounds_refuse_instead_of_truncating(tmp_path,monkeypatch,bound):
    _,rating,_,_=fixture(tmp_path)
    sel=selection(tmp_path,[entry(rating,group='first'),entry(rating,group='second')])
    monkeypatch.setattr(figure,bound,1)
    with pytest.raises(ValueError): figure.prepare(sel)


def test_fifo_input_is_refused_without_blocking(tmp_path):
    if not hasattr(os,'mkfifo'): pytest.skip('POSIX named pipe test')
    pipe=tmp_path/'fifo'
    os.mkfifo(pipe)
    with pytest.raises(ValueError,match='regular file'): figure.prepare(pipe)
