"""Actual captured reconstruction; invented replies are not calibration."""
import copy
from datetime import date
import json
from pathlib import Path
import shutil
import socket

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import evidence_score, nested_support_results as support
from data_sheets_schema import schema_digest, support_plan, support_targets
from data_sheets_schema import top_level_fitness_results as fit
from data_sheets_schema.cli.evaluate import evaluate
from tests.test_evaluation.test_support_plan import fixture, rewrite_roster  # noqa: F401
from tests.test_evaluation.test_nested_support_plan import build, change_record


def native(value=None, **changes):
    score = {"fitness": 0.75, "failure": "form", "reason": "Invented partial fit."} if value is None else value
    return {"id": "invented", "type": "message", "role": "assistant", "model": "judge",
            "stop_reason": "end_turn", "usage": {"input_tokens": 12, "output_tokens": 23},
            "content": [{"type": "text", "text": json.dumps(score)}], **changes}


@pytest.fixture
def prepared(fixture, tmp_path):
    source, plan = fixture
    manifest = build(fixture, max_tokens=417)
    selected = [{"target_id": t["id"], "attempt_id": f"fitness-{i}"}
                for i, t in enumerate(manifest["targets"]) if t["axis"] == "fitness"]
    descriptor = tmp_path / "descriptor"
    value = fit.prepare(plan, descriptor, selections=selected, protocol=fit.FORMAT)
    return source, plan, manifest, selected, descriptor, value


def attempt(prepared, tmp_path, message=None, *, ordinal=0, name="accepted"):
    *_, selections, descriptor, value = prepared
    raw = support_plan.canonical(native() if message is None else message)
    envelope = fit.package_response((descriptor / "descriptor.json").read_bytes(),
                                   attempt_id=selections[ordinal]["attempt_id"], native_message=raw)
    response = tmp_path / (name + ".json")
    response.write_bytes(envelope)
    output = tmp_path / name
    result = fit.accept(descriptor, response, output, attempt_id=selections[ordinal]["attempt_id"])
    return result, output


def replace_artifact(directory, pin, raw):
    changed = {**pin, "sha256": support_plan.sha256(raw), "bytes": len(raw)}
    (directory / "artifacts" / changed["sha256"]).write_bytes(raw)
    return changed


def test_actual_cli_roundtrip_and_relocated_index_keep_missing_and_ineligible(prepared, tmp_path, monkeypatch):
    source, plan, manifest, selections, descriptor, _ = prepared
    value, accepted = attempt(prepared, tmp_path)
    _, rejected = attempt(prepared, tmp_path, native(stop_reason="max_tokens"), ordinal=1, name="rejected")
    runner = CliRunner()
    output = tmp_path / "index"
    result = runner.invoke(evaluate, ["fitness-results", "index", "--descriptor", str(descriptor),
        "--result", str(accepted), "--result", str(rejected), "--output", str(output)])
    assert result.exit_code == 0, result.output
    index = json.loads(result.output)
    assert index["strata"]["fitness_top_level"] == {"selected": 5, "accepted": 1, "rejected": 1, "missing": 3}
    assert index["scientific_scoring_eligible"] is False
    assert index["mode"] == "caller_saved"
    assert all(r["spent"] is None and r["dispatch_state"] == "unknown" for r in index["fitness_rows"])
    assert index["readiness"] == manifest["readiness"]
    assert fit.recheck(accepted) == value
    moved = tmp_path / "relocated"
    shutil.copytree(output, moved)
    for path in (source, plan, descriptor, accepted, rejected, output):
        path.rename(path.with_name(path.name + "-unavailable"))
    old = Path.read_bytes
    def captured_only(path):
        assert path.is_relative_to(moved), path
        return old(path)
    monkeypatch.setattr(Path, "read_bytes", captured_only)
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("network forbidden"))
    checked = runner.invoke(evaluate, ["fitness-results", "recheck-index", "--index", str(moved)])
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.output) == index


def test_actual_requests_keep_typed_values_and_legacy_system(prepared):
    source, _, manifest, _, descriptor, value = prepared
    record = yaml.safe_load((source / "record.yaml").read_text())
    for selection in value["selections"]:
        b = selection["binding"]
        raw = (descriptor / "artifacts" / b["request"]["sha256"]).read_bytes()
        request = json.loads(raw)
        slot = support_targets.pointer_tokens(b["pointer"])[0]
        assert request["system"] == evidence_score.FITNESS_SYSTEM
        assert yaml.safe_dump({slot: record[slot]}, sort_keys=False, allow_unicode=True) in request["messages"][0]["content"]
        assert b["value_sha256"] == support_plan.sha256(support_plan.value_identity(record[slot]))
        assert b["context"]["schema"] == manifest["schema"]["generation_digest"]
        assert b["context"]["corpus"] == ""
    assert any('/enabled' == s["binding"]["pointer"] for s in value["selections"])
    assert any('/count' == s["binding"]["pointer"] for s in value["selections"])


def test_missing_captured_request_is_not_regenerated_on_read(prepared, tmp_path):
    _, output = attempt(prepared, tmp_path)
    request = prepared[-1]['selections'][0]['binding']['request']
    (output/'artifacts'/request['sha256']).unlink()
    with pytest.raises(fit.ResultError, match='cannot read evidence file'):
        fit.recheck(output)


def test_returned_metadata_cannot_change_contract_or_future_results(prepared, tmp_path):
    _, plan, _, selections, _, value = prepared
    expected = copy.deepcopy(fit.CONTRACT)
    limitations = list(fit.LIMITATIONS)
    value['contract']['limits']['response_bytes'] = 1
    value['limitations'].append('foreign')
    result, _ = attempt(prepared, tmp_path)
    result['contract']['completion'] = 'max_tokens'
    result['limitations'].append('foreign')
    fresh = fit.prepare(plan, tmp_path/'fresh-descriptor', selections=selections, protocol=fit.FORMAT)
    assert fresh['contract'] == fit.CONTRACT == expected
    assert fresh['limitations'] == fit.LIMITATIONS == limitations


def test_complete_index_document_bound_refuses_before_any_publication(prepared, tmp_path, monkeypatch):
    _, result = attempt(prepared, tmp_path)
    monkeypatch.setattr(fit, 'MAX_DOCUMENT_BYTES', 1)
    output = tmp_path/'oversized-index'
    with pytest.raises(fit.ResultError, match='document exceeds byte bound'):
        fit.build_index(prepared[-2], [result], output)
    assert not output.exists()


def test_fitness_only_record_does_not_require_nested_support_selection(fixture, tmp_path):
    source, plan = fixture
    (source / "record.yaml").write_text('creators: invalid-inline-object\n')
    rewrite_roster(source, lambda d: d['pinned_files'].update({'record.yaml': support_plan.sha256((source/'record.yaml').read_bytes())}))
    manifest = build(fixture)
    assert manifest['counts']['by_axis'] == {'fitness': 1}
    selection = [{"target_id": manifest["targets"][0]["id"], "attempt_id": "only"}]
    value = fit.prepare(plan, tmp_path / "descriptor", selections=selection, protocol=fit.FORMAT)
    assert value['selections'][0]['binding']['pointer'] == '/creators'


@pytest.mark.parametrize('kind,cls,filename', [('full','Dataset','schema.yaml'),
    ('full','Dataset','data_sheets_schema_all.yaml'),('core','CoreDataset','schema.yaml'),
    ('core','CoreDataset','data_sheets_schema_core_all.yaml'),('collection','Collection','schema.yaml')])
def test_known_custom_and_collection_inventory_paths_are_exact(fixture, tmp_path, kind, cls, filename):
    source, plan = fixture
    schema = yaml.safe_load((source/'schema.yaml').read_text())
    if cls != 'Dataset':schema['classes'][cls] = schema['classes'].pop('Dataset')
    selected = source / filename
    selected.write_text(yaml.safe_dump(schema))
    provenance = yaml.safe_load((source/'provenance.yaml').read_text())
    provenance['outputs'] = {kind: {'path': 'record.yaml'}}
    (source/'provenance.yaml').write_text(yaml.safe_dump(provenance))
    manifest = build(fixture, artifact_kind=kind, class_name=cls, schema_path=selected)
    t = next(t for t in manifest['targets'] if t['axis']=='fitness')
    value=fit.prepare(plan,tmp_path/'descriptor',selections=[{'target_id':t['id'],'attempt_id':'path'}],protocol=fit.FORMAT)
    assert value['selections'][0]['binding']['context']['schema'] == manifest['schema']['generation_digest']
    # Concrete path rule, independent of the descriptor reconstruction helper.
    original=schema_digest.build_for_judgement(cls,selected)[0]
    expected=str(schema_digest.CLASS_SCHEMA[cls]) if cls in schema_digest.CLASS_SCHEMA and filename==schema_digest.CLASS_SCHEMA[cls].name else str(selected)
    assert original.schema_path==expected


def test_imported_vocabulary_specs_dates_and_deep_inline_ranges(fixture,tmp_path):
    source,plan=fixture
    schema=yaml.safe_load((source/'schema.yaml').read_text())
    schema['imports'].append('child')
    schema['slots']['notes']['values_from']=['terms']
    schema['classes']['Creator']['attributes']['child']={'range':'Child','inlined':True}
    (source/'schema.yaml').write_text(yaml.safe_dump(schema))
    (source/'child.yaml').write_text('id: https://example.org/child\nname: child\nclasses:\n  Child:\n    attributes:\n      description:\n        range: string\n        required: true\n')
    vocab=source/'vocab.yaml';vocab.write_text('vocabularies:\n  terms:\n    ex:yes: Yes label\n')
    change_record(source,{'notes':'ex:yes','title':date(2026,1,2)})
    manifest=build(fixture,vocabulary_path=vocab)
    selections=[{'target_id':t['id'],'attempt_id':'a'+str(i)} for i,t in enumerate(manifest['targets']) if t['axis']=='fitness']
    value=fit.prepare(plan,tmp_path/'descriptor',selections=selections,protocol=fit.FORMAT)
    title=next(s['binding'] for s in value['selections'] if s['binding']['pointer']=='/title')
    assert title['value_sha256']==support_plan.sha256(support_plan.value_identity(date(2026,1,2)))
    assert title['value_sha256']!=support_plan.sha256(support_plan.value_identity('2026-01-02'))
    spec=json.loads((plan/'artifacts'/manifest['schema']['fitness_specifications']['sha256']).read_text())
    assert 'Yes label' in spec['slots']['notes']
    assert 'Child' in spec['slots']['creators']


@pytest.mark.parametrize('mutation',['spec','generation','context','value','request','model','record','replicate',
                                    'replicate_bool','provenance_replicate_bool','missing_target'])
def test_repinned_manifest_drift_refuses_at_actual_binding(prepared,tmp_path,mutation):
    _,plan,manifest,selections,_,_=prepared
    doc=copy.deepcopy(manifest);target=next(t for t in doc['targets'] if t['id']==selections[0]['target_id'])
    if mutation=='spec':
        pin=doc['schema']['fitness_specifications'];raw=(plan/'artifacts'/pin['sha256']).read_bytes();data=json.loads(raw);data['slots']['title']='Foreign';new=replace_artifact(plan,pin,json.dumps(data,sort_keys=True).encode());doc['schema']['fitness_specifications']=new
        for t in doc['targets']:
            if t['axis']=='fitness':t['specification_artifact']=new;t['judgement_context']['specification']=new['sha256']
    elif mutation=='generation':doc['schema']['generation_digest']='0'*64
    elif mutation=='context':target['judgement_context']['corpus']='foreign'
    elif mutation=='value':target['value_sha256']='0'*64
    elif mutation=='request':target['request_sha256']='0'*64
    elif mutation=='model':doc['model']['name']='other-model'
    elif mutation=='record':
        row=doc['records'][0];row['record']=replace_artifact(plan,row['record'],b'title: foreign\n')
    elif mutation=='replicate':doc['records'][0]['generation_rep']=2
    elif mutation=='replicate_bool':doc['records'][0]['generation_rep']=True
    elif mutation=='provenance_replicate_bool':
        record=doc['records'][0];pin=record['provenance'];provenance=yaml.safe_load((plan/'artifacts'/pin['sha256']).read_bytes())
        provenance['run']['replicate']=True
        record['provenance']=replace_artifact(plan,pin,yaml.safe_dump(provenance).encode())
    elif mutation=='missing_target':doc['targets'].remove(target)
    (plan/'manifest.json').write_bytes(support_plan.canonical(doc))
    with pytest.raises((fit.ResultError,ValueError)):
        fit.prepare(plan,tmp_path/'invalid',selections=selections,protocol=fit.FORMAT)
    assert not (tmp_path/'invalid').exists()


@pytest.mark.parametrize('score',[0,1,0.375])
def test_strict_native_numeric_controls(score):
    raw=support_plan.canonical(native({'fitness':score,'failure':'none','reason':'Invented fit.'}))
    checked=fit._assess(raw,{'model':{'name':'judge'},'max_tokens':417})
    assert checked['status']=='accepted' and checked['fitness']==score


@pytest.mark.parametrize('mode',['truncated','fenced','prose','duplicate','boolean','nan','infinite','outside',
    'missing_reason','empty_reason','25words','extra','bad_failure','numeric_text','max_tokens','unknown_stop',
    'model_alias','usage_bool','usage_missing','excess_output','two_texts','tool','thinking_bool'])
def test_strict_native_refusals_never_salvage_a_score(mode):
    message=native();value={'fitness':0.75,'failure':'none','reason':'Invented fit.'}
    if mode=='truncated':message['content'][0]['text']='{"fitness":0.75,"reason":"cut'
    elif mode=='fenced':message['content'][0]['text']='```json\n'+json.dumps(value)+'\n```'
    elif mode=='prose':message['content'][0]['text']='Answer: '+json.dumps(value)
    elif mode=='duplicate':message['content'][0]['text']='{"fitness":1,"fitness":0,"failure":"none","reason":"x"}'
    elif mode in {'boolean','nan','infinite','outside','numeric_text'}:
        value['fitness']={'boolean':True,'nan':float('nan'),'infinite':float('inf'),'outside':1.1,'numeric_text':'0.75'}[mode];message['content'][0]['text']=json.dumps(value)
    elif mode in {'missing_reason','empty_reason','25words','extra','bad_failure'}:
        if mode=='missing_reason':value.pop('reason')
        elif mode=='empty_reason':value['reason']=' '
        elif mode=='25words':value['reason']=' '.join(['word']*25)
        elif mode=='extra':value['confidence']=1
        else:value['failure']='truth'
        message['content'][0]['text']=json.dumps(value)
    elif mode in {'max_tokens','unknown_stop'}:message['stop_reason']=mode
    elif mode=='model_alias':message['model']='judge-alias'
    elif mode=='usage_bool':message['usage']['input_tokens']=True
    elif mode=='usage_missing':message.pop('usage')
    elif mode=='excess_output':message['usage']['output_tokens']=418
    elif mode=='two_texts':message['content']*=2
    elif mode=='tool':message['content'].append({'type':'tool_use','id':'fake'})
    elif mode=='thinking_bool':message['usage']['output_tokens_details']={'thinking_tokens':True}
    checked=fit._assess(support_plan.canonical(message),{'model':{'name':'judge'},'max_tokens':417})
    assert checked['status']=='rejected' and checked['fitness'] is None and checked['failure'] is None
    assert checked['problems']


def test_legacy_truncation_and_support_fitness_refusal_unchanged(prepared):
    _,plan,_,selections,_,_=prepared
    assert evidence_score._parse_fitness('{"fitness":0.75,"reason":"cut').fitness==0.75
    with pytest.raises(support.ResultError,match='fitness cannot'):
        support.prepare(plan,plan.with_name('support-refused'),selections=selections,protocol=support.FORMAT)


def test_foreign_envelope_and_forged_result_index_flags_refuse(prepared,tmp_path):
    value,output=attempt(prepared,tmp_path)
    raw=(output/'result.json').read_bytes();forged=json.loads(raw);forged['assessment']['fitness']=1
    (output/'result.json').write_bytes(support_plan.canonical(forged))
    with pytest.raises(fit.ResultError,match='reconstructed evidence'):fit.recheck(output)
    (output/'result.json').write_bytes(raw)
    descriptor=prepared[-2];indexdir=tmp_path/'index';index=fit.build_index(descriptor,[output],indexdir)
    index['scientific_scoring_eligible']=True
    (indexdir/'index.json').write_bytes(support_plan.canonical(index))
    with pytest.raises(fit.ResultError,match='reconstructed evidence'):fit.recheck_index(indexdir)
    with pytest.raises(fit.ResultError,match='duplicate'):fit.build_index(descriptor,[output,output],tmp_path/'duplicate')


def test_real_support_join_keeps_strata_and_no_nested_fitness_propagation(prepared,tmp_path):
    _,plan,manifest,_,descriptor,_=prepared
    fitvalue,fitdir=attempt(prepared,tmp_path)
    target=next(t for t in manifest['targets'] if t['axis']==support_targets.AXIS)
    sd=tmp_path/'support-descriptor';support.prepare(plan,sd,selections=[{'target_id':target['id'],'attempt_id':'support-a'}],protocol=support.FORMAT)
    message=native();message['content'][0]['text']=json.dumps({'verdict':'supported','reason':'Invented support.'})
    response=tmp_path/'support.json';response.write_bytes(support.package_response((sd/'descriptor.json').read_bytes(),attempt_id='support-a',native_message=support_plan.canonical(message)))
    sr=tmp_path/'support-result';support.accept(sd,response,sr,attempt_id='support-a')
    index=fit.build_index(descriptor,[fitdir],tmp_path/'joined',support_results=[sr])
    assert set(index['strata'])=={'fitness_top_level','attribute_value','relationship_edge'}
    assert index['support_rows'][0]['fitness_propagated'] is False
    assert 'fitness' not in index['support_rows'][0]['assessment']
    assert fit.recheck_index(tmp_path/'joined')==index
