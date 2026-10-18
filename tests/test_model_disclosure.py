"""Declared family disclosure is not generator inference or score calibration."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from data_sheets_schema import model_disclosure as m


@pytest.fixture
def bound(tmp_path):
    input_file = tmp_path / 'input.yaml'
    input_file.write_bytes(b'id: doi:10.1/test\ntitle: Example\n')
    digest = hashlib.sha256(input_file.read_bytes()).hexdigest()
    evaluation = tmp_path / 'rating.json'
    doc = {'rubric':'rubric10-semantic', 'version':'1.0', 'project':'EXTERNAL',
           'method':'arbitrary_method', 'label':'a-run', 'd4d_file': str(input_file),
           'model':{'name':'Display evaluator', 'evaluator_model':'google/claude-opus-5-high',
                    'evaluation_type':'semantic_llm_judge'},
           'metadata':{'input_sha256':digest,'d4d_file_hash':digest}}
    evaluation.write_text(json.dumps(doc))
    provenance = tmp_path / 'provenance.yaml'
    record = {'run':{'project':'EXTERNAL','method':'arbitrary_method','label':'a-run'},
              'model':{'model':'claude-sonnet-4-5-20250929'},
              'outputs':{'full':{'path':str(input_file),'bytes':input_file.stat().st_size}}}
    provenance.write_text(yaml.safe_dump(record))
    return evaluation,input_file,provenance,doc,record


def build(bound, paths=None):
    e,i,p,*_=bound
    return m.build_report(paths or [e],bindings=[m.GenerationBinding(e,i,p)])


def save(bound):
    e,_,p,doc,record=bound
    e.write_text(json.dumps(doc));p.write_text(yaml.safe_dump(record))


def test_positive_records_exact_binding_hashes_not_route_vendor(bound):
    result=build(bound); row=result['rows'][0]
    assert row['same_family']=='yes'
    assert row['evaluator_family']==row['generator_family']=='claude'
    assert row['evaluator_display']=='Display evaluator'
    assert row['evaluator']=='google/claude-opus-5-high'
    assert row['association_status']=='associated'
    assert {x['field'] for x in row['binding_checks']['hashes']}=={'metadata.input_sha256','metadata.d4d_file_hash'}
    assert row['binding_checks']['output_kind']=='full'
    assert row['provenance_sha256']==hashlib.sha256(bound[2].read_bytes()).hexdigest()
    assert 'not provider-authenticated' in result['disclaimer']


@pytest.mark.parametrize('generator,evaluator,expected',[
 ('openai:gpt-5','claude-fable-5','no'),('google/claude-opus-5','claude-sonnet-4','yes'),
 ('future-model','claude-opus-5','unknown'),('claude-opus-5','unrecognized','unknown'),
 ('claude-opus-5','us.anthropic.claude-sonnet-4-v1:0','yes')])
def test_declared_family_tri_state(bound,generator,evaluator,expected):
    bound[4]['model']['model']=generator;bound[3]['model']['evaluator_model']=evaluator;save(bound)
    assert build(bound)['rows'][0]['same_family']==expected


@pytest.mark.parametrize('hint', ['gpt5','claude-opus-5','google/claude-opus-5'])
def test_unbound_never_infers_generator_from_method_filename_or_metadata(bound,hint):
    e,_,_,doc,_=bound
    doc['method']=hint;doc['metadata']['generator']=hint
    path=e.with_name(hint.replace('/','_')+'_evaluation.json');path.write_text(json.dumps(doc))
    row=m.build_report([path])['rows'][0]
    assert row['generator'] is None and row['same_family']=='unknown'
    assert row['association_basis']=='no_binding_supplied'


@pytest.mark.parametrize('kind', ['rule_based_with_quality_heuristics','field_presence','new_unclassified_type'])
def test_non_llm_or_unclassified_type_never_yields_family_agreement(bound,kind):
    bound[3]['model']['evaluation_type']=kind;save(bound)
    row=build(bound)['rows'][0]
    assert row['generator_family']=='claude' and row['evaluator_family'] is None
    assert row['same_family']=='unknown' and row['evaluation_type']==kind


def test_model_identifier_precedence_and_legacy_name_fallback(bound):
    doc=bound[3];doc['model']={'name':'claude-fable-5','model_id':'gpt-5'};save(bound)
    assert build(bound)['rows'][0]['same_family']=='no'
    del doc['model']['model_id'];bound[4]['model']={'name':'claude-opus-5'};save(bound)
    assert build(bound)['rows'][0]['same_family']=='yes'
    doc['model']['evaluator_model']=['claude-opus-5'];save(bound)
    assert build(bound)['rows'][0]['evaluator'] is None


@pytest.mark.parametrize('model', [None, [], 'claude-opus-5', {}, {'model':['gpt-5'],'name':'claude-opus-5'}])
def test_missing_or_malformed_provenance_model_is_unknown(bound,model):
    bound[4]['model']=model;save(bound)
    row=build(bound)['rows'][0]
    assert row['generator'] is None and row['same_family']=='unknown'
    assert any('model absent or malformed' in reason for reason in row['association_reasons'])


@pytest.mark.parametrize('field', ['project','method','label'])
def test_contradictory_run_identity_refuses(bound,field):
    bound[4]['run'][field]='another';save(bound)
    with pytest.raises(m.DisclosureError,match='disagrees'): build(bound)


@pytest.mark.parametrize('field', ['project','method','label'])
def test_missing_required_run_identity_stays_unknown(bound,field):
    del bound[4]['run'][field];save(bound)
    assert build(bound)['rows'][0]['association_status']=='unknown'


@pytest.mark.parametrize('field', ['input_sha256','d4d_file_hash'])
def test_all_recorded_evaluation_hashes_checked_even_when_another_matches(bound,field):
    bound[3]['metadata'][field]='0'*64;save(bound)
    with pytest.raises(m.DisclosureError,match='recorded hash'): build(bound)


@pytest.mark.parametrize('field', ['sha256','md5','bytes'])
def test_matching_output_path_cannot_hide_wrong_provenance_hash_or_size(bound,field):
    bound[4]['outputs']['full'][field]=1 if field=='bytes' else '0'*(64 if field=='sha256' else 32)
    save(bound)
    with pytest.raises(m.DisclosureError): build(bound)


def test_sha256_legacy_prefix_supported_but_bare_md5_not_guessed(bound):
    doc=bound[3];doc['metadata']['d4d_file_hash']='sha256:'+doc['metadata']['d4d_file_hash'];save(bound)
    assert build(bound)['rows'][0]['association_status']=='associated'
    doc['metadata']['d4d_file_hash']=hashlib.md5(bound[1].read_bytes()).hexdigest();save(bound)
    with pytest.raises(m.DisclosureError,match='expected a sha256'): build(bound)


def test_changed_input_is_detected_and_all_sources_remain_unchanged(bound):
    bound[1].write_bytes(bound[1].read_bytes()+b'notes: changed\n')
    before={p:p.read_bytes() for p in bound[:3]}
    with pytest.raises(m.DisclosureError,match='recorded hash'): build(bound)
    assert before=={p:p.read_bytes() for p in bound[:3]}


@pytest.mark.parametrize('target', ['rating','provenance','both-kinds'])
def test_wrong_or_ambiguous_recorded_paths_refuse(bound,target):
    if target=='rating': bound[3]['d4d_file']=str(bound[1].with_name('other.yaml'))
    elif target=='provenance': bound[4]['outputs']['full']['path']=str(bound[1].with_name('other.yaml'))
    else: bound[4]['outputs']['core']=dict(bound[4]['outputs']['full'])
    save(bound)
    with pytest.raises(m.DisclosureError): build(bound)


def test_basename_requires_hash_while_root_anchored_path_is_explicit(bound,tmp_path):
    doc=bound[3];doc['d4d_file']=bound[1].name;save(bound)
    assert build(bound)['rows'][0]['association_status']=='associated'
    doc['metadata']={};save(bound)
    row=m.build_report([bound[0]],bindings=[m.GenerationBinding(*bound[:3])],root=tmp_path)['rows'][0]
    assert row['association_status']=='unknown'
    doc['d4d_file']='./input.yaml';save(bound)
    # An explicitly relative path is anchored to the caller-supplied root.
    assert m.build_report([bound[0]],bindings=[m.GenerationBinding(*bound[:3])],root=tmp_path)['rows'][0]['association_status']=='associated'


def test_missing_input_or_provenance_path_is_unknown_not_certified(bound):
    bound[3].pop('d4d_file');bound[3]['metadata']={};bound[4].pop('outputs');save(bound)
    row=build(bound)['rows'][0]
    assert row['association_status']=='unknown' and len(row['association_reasons'])==2


def test_repeated_ratings_preserved_and_capture_once_under_change(bound,monkeypatch):
    e,i,p,*_=bound
    original=m._Capture.read;counts={}
    def read(self,path):
        value=original(self,path)
        counts[str(path)]=counts.get(str(path),0)+1
        if path==i and counts[str(path)]==1: i.write_text('different later bytes')
        return value
    monkeypatch.setattr(m._Capture,'read',read)
    rows=build(bound,paths=[e,e])['rows']
    assert len(rows)==2 and rows[0]['rating']==1 and rows[1]['rating']==2
    assert rows[0]['input_sha256']==rows[1]['input_sha256']
    assert rows[0]['same_family']==rows[1]['same_family']=='yes'


def test_unknown_and_bound_rows_same_identity_across_formats(bound):
    result=build(bound,paths=[bound[0],bound[0]])
    json_rows=json.loads(m.render(result,'json'))['rows']
    csv_rows=list(csv.DictReader(io.StringIO(m.render(result,'csv'))))
    markdown=m.render(result)
    for a,b in zip(json_rows,csv_rows):
        assert set(b)=={'report_version','disclaimer',*a}
        for key in ('evaluation_sha256','input_sha256','provenance_sha256','evaluator','generator','same_family'):
            assert a[key]==b[key] and a[key] in markdown
        assert json.loads(b['binding_checks'])==a['binding_checks']
    assert len(csv_rows)==2


def test_literal_markdown_and_csv_quotes_preserve_hostile_metadata(bound):
    bound[3]['model']['name']='a|b\n<script>[link](x)`';save(bound)
    report=build(bound)
    md=m.render(report)
    assert '<script>' not in md and '&lt;script&gt;' in md and 'a&#124;b<br>' in md
    row=next(csv.DictReader(io.StringIO(m.render(report,'csv'))))
    assert row['evaluator_display']==bound[3]['model']['name']


@pytest.mark.parametrize('kind', ['same','hardlink','symlink','existing','broken-symlink'])
def test_writer_never_replaces_inputs_or_existing_outputs(bound,tmp_path,kind):
    report=build(bound);output=tmp_path/'out'
    if kind=='same': output=bound[1]
    elif kind=='hardlink': os.link(bound[2],output)
    elif kind=='symlink': output.symlink_to(bound[0])
    elif kind=='broken-symlink': output.symlink_to(tmp_path/'absent')
    else: output.write_text('existing output')
    before={p:p.read_bytes() for p in bound[:3]}
    with pytest.raises((m.DisclosureError,FileExistsError)): m.write_report(report,output)
    assert before=={p:p.read_bytes() for p in bound[:3]}
    if kind=='existing': assert output.read_text()=='existing output'


@pytest.mark.parametrize('raw', ['[]','{"model":{},"model":{}}','{"score":NaN}'])
def test_malformed_json_or_duplicate_identity_refuses(bound,raw):
    bound[0].write_text(raw)
    with pytest.raises((m.DisclosureError,ValueError)): build(bound)


def test_duplicate_or_malformed_yaml_refuses_before_output(bound):
    bound[2].write_text('model: {}\nmodel: {}\n')
    with pytest.raises(m.DisclosureError,match='duplicate'): build(bound)
    bound[2].write_text('model: [broken')
    with pytest.raises(m.DisclosureError,match='malformed'): build(bound)


def test_binding_must_name_report_once(bound,tmp_path):
    binding=m.GenerationBinding(*bound[:3])
    with pytest.raises(m.DisclosureError,match='more than one'): m.build_report([bound[0]],bindings=[binding,binding])
    with pytest.raises(m.DisclosureError,match='outside'): m.build_report([tmp_path/'elsewhere'],bindings=[binding])


def test_actual_cli_preserves_inputs_and_refuses_contradiction_before_output(bound,tmp_path):
    script=Path(__file__).parents[1]/'scripts/report_model_disclosure.py'
    output=tmp_path/'new.json'
    cmd=[sys.executable,str(script),str(bound[0]),'--generation-binding',*[str(p) for p in bound[:3]],
         '--format','json','--output',str(output)]
    env={**os.environ,'PYTHONPATH':str(Path(__file__).parents[1]/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
    before={p:p.read_bytes() for p in bound[:3]}
    result=subprocess.run(cmd,capture_output=True,text=True,env=env)
    assert result.returncode==0,result.stderr
    assert json.loads(output.read_text())['rows'][0]['same_family']=='yes'
    assert before=={p:p.read_bytes() for p in bound[:3]}
    # Existing output is never replaced, even by a valid repeat invocation.
    output_before=output.read_bytes();result=subprocess.run(cmd,capture_output=True,text=True,env=env)
    assert result.returncode==2 and output.read_bytes()==output_before
    bound[4]['run']['project']='another';save(bound)
    cmd[-1]=str(tmp_path/'refused.json');result=subprocess.run(cmd,capture_output=True,text=True,env=env)
    assert result.returncode==2 and 'disagrees' in result.stderr
    assert not Path(cmd[-1]).exists()


@pytest.mark.parametrize('source_index,alias_kind', [(0,'hardlink'),(1,'symlink'),(2,'hardlink')])
def test_actual_cli_rejects_output_aliases_of_every_binding_source(bound,tmp_path,source_index,alias_kind):
    output=tmp_path/'output.json';source=bound[source_index]
    if alias_kind=='hardlink': os.link(source,output)
    else: output.symlink_to(source)
    original=source.read_bytes()
    script=Path(__file__).parents[1]/'scripts/report_model_disclosure.py'
    result=subprocess.run([sys.executable,str(script),str(bound[0]),'--generation-binding',
        *map(str,bound[:3]),'--output',str(output)],capture_output=True,text=True,
        env={**os.environ,'PYTHONPATH':str(Path(__file__).parents[1]/'src'),'PYTHONDONTWRITEBYTECODE':'1'})
    assert result.returncode==2 and 'aliases a captured input' in result.stderr
    assert source.read_bytes()==original and output.read_bytes()==original


def test_default_configuration_is_never_consulted(bound,monkeypatch):
    import data_sheets_schema.evaluation_model as selection
    def trap(*a,**kw): raise AssertionError('current configuration cannot fill historical identity')
    monkeypatch.setattr(selection,'evaluation_model_settings',trap)
    monkeypatch.setattr(selection,'evaluation_model_name',trap)
    assert build(bound)['rows'][0]['same_family']=='yes'


@pytest.mark.parametrize('value', [False, True, '', [], ['semantic_llm_judge'], 1, {}, {'kind':'semantic_llm_judge'}])
@pytest.mark.parametrize('location', ['model','top_level'])
def test_malformed_declared_type_stays_unknown_and_is_preserved(bound,value,location):
    bound[3]['model'].pop('evaluation_type')
    target=bound[3]['model'] if location=='model' else bound[3]
    target['evaluation_type']=value;save(bound)
    row=build(bound)['rows'][0]
    assert row['evaluation_type'] is None and row['evaluation_type_basis']==location
    assert row['evaluation_type_declarations']=={location:value}
    assert row['same_family']=='unknown' and row['evaluator_family'] is None


@pytest.mark.parametrize('model_type,top_type,expected', [
    ('semantic_llm_judge','rule_based_with_quality_heuristics','unknown'),
    (False,'semantic_llm_judge','unknown'),
    ('semantic_llm_judge',{},'unknown'),
    ('semantic_llm_judge','llm_as_judge','unknown'),
    ('semantic_llm_judge','semantic_llm_judge','yes'),
    (None,None,'yes'), (False,0,'unknown')])
def test_conflicting_type_declarations_do_not_silently_become_llm(bound,model_type,top_type,expected):
    bound[3]['model']['evaluation_type']=model_type;bound[3]['evaluation_type']=top_type;save(bound)
    row=build(bound)['rows'][0]
    assert row['evaluation_type_basis']=='model'
    assert row['evaluation_type_conflict']==(json.dumps(model_type,sort_keys=True)!=json.dumps(top_type,sort_keys=True))
    assert row['evaluation_type_declarations']=={'model':model_type,'top_level':top_type}
    assert row['same_family']==expected


def test_matching_basename_without_hash_stays_unknown_for_any_root(bound,tmp_path):
    bound[3]['d4d_file']=bound[1].name;bound[3]['metadata']={};save(bound)
    for root in (tmp_path,tmp_path/'another-root'):
        row=m.build_report([bound[0]],bindings=[m.GenerationBinding(*bound[:3])],root=root)['rows'][0]
        assert row['association_status']=='unknown'
        assert row['binding_checks']['input_paths'][0]['basis']=='basename_only_unbound'
