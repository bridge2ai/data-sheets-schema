"""Recorded authority is opt-in; synthetic controls are not quality evidence."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import related_datasets as legacy
from data_sheets_schema import related_dataset_diagnostics as diagnostics
from data_sheets_schema.cli.evaluate import evaluate

ROOT = Path(__file__).resolve().parents[1]


def schema(*, core=False, aliases=None, related=True, owner='SelectedRelationship', target='string'):
    root = 'CoreDataset' if core else 'Dataset'
    doc = {'id':'https://example.org/test','name':'related_test','imports':['linkml:types'],
           'prefixes':{'linkml':'https://w3id.org/linkml/'},
           'classes':{root:{'attributes':{'related_datasets':{'range':owner}}} if related else {},
                      owner:{'attributes':{'relationship_type':{'range':'SelectedType'},
                                            'target_dataset':{'range':target}}}},
           'enums':{'OtherRelationshipType':{'permissible_values':{'wrong':{'aliases':['IsNewVersionOf']}}},
                    'SelectedType':{'permissible_values':{'is_new_version_of':{'aliases':aliases or []},'has_part':{}}}}}
    return yaml.safe_dump(doc,sort_keys=False).encode()


@pytest.fixture
def inputs(tmp_path):
    full_schema,core_schema=tmp_path/'full-schema.yaml',tmp_path/'core-schema.yaml'
    full_schema.write_bytes(schema())
    core_schema.write_bytes(schema(core=True,aliases=['IsNewVersionOf']))
    full,core=tmp_path/'full.yaml',tmp_path/'core.yaml'
    raw=b'id: example:one\nrelated_datasets:\n- relationship_type: IsNewVersionOf\n  target_dataset: x\n'
    full.write_bytes(raw);core.write_bytes(raw)
    prov=tmp_path/'provenance.yaml'
    data={'schema':{},'outputs':{}}
    for kind,path,schema_path in (('full',full,full_schema),('core',core,core_schema)):
        data['schema'].update({kind+'_path':str(schema_path),kind+'_sha256':hashlib.sha256(schema_path.read_bytes()).hexdigest()})
        data['outputs'][kind]={'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'md5':hashlib.md5(raw).hexdigest()}
    prov.write_text(yaml.safe_dump(data))
    return {'full':full,'core':core,'provenance':prov,'full_schema':full_schema,'core_schema':core_schema}


def alter_provenance(inputs, fn):
    path=inputs['provenance'];data=yaml.safe_load(path.read_bytes());fn(data);path.write_text(yaml.safe_dump(data))


def replace_schema(inputs, raw, kind='full'):
    path=inputs[kind+'_schema'];path.write_bytes(raw)
    alter_provenance(inputs,lambda p:p['schema'].update({kind+'_sha256':hashlib.sha256(raw).hexdigest()}))


def check(inputs,kind='full'):
    return diagnostics.check_record(inputs[kind],inputs['provenance'],kind=kind)


def invoke(inputs,*flags,kind='full'):
    return CliRunner().invoke(evaluate,['related-datasets','--schema-policy','recorded',
        '--provenance',str(inputs['provenance']),'--kind',kind,*flags,str(inputs[kind])])


def test_actual_owner_and_distinct_full_core_authority_without_current_table(inputs):
    with patch.object(legacy,'_vocabulary',side_effect=AssertionError('must not read current vocabulary')):
        full,core=check(inputs),check(inputs,'core')
    assert full['checked'] and core['checked']
    assert [d['mode'] for d in full['defects']]==['unknown_type']
    assert [d['mode'] for d in core['defects']]==['aliased_type']
    assert full['selected_schema']['owner']=='SelectedRelationship'
    assert full['selected_schema']['enum']=='SelectedType'
    assert full['selected_schema']['sha256']!=core['selected_schema']['sha256']
    assert full['selected_schema']['root']=='Dataset'
    assert core['selected_schema']['root']=='CoreDataset'
    assert full['output_association']['hashes_verified']==['sha256','md5']


def test_legacy_defaults_and_explicit_cli_policy_match_captured_baseline(tmp_path):
    baseline=json.loads((ROOT/'tests/fixtures/related_datasets_legacy.json').read_text())
    for case in baseline['cases']:
        assert [asdict(d) for d in legacy.inspect(case['record'])]==case['defects']
    record=tmp_path/'legacy.yaml';record.write_text(baseline['cli_input'])
    expected=baseline['cli']['output'].replace(baseline['cli']['argv'][-1],str(record))
    for flags in ([],['--schema-policy','legacy_current']):
        result=CliRunner().invoke(evaluate,['related-datasets',*flags,str(record)])
        assert result.exit_code==baseline['cli']['exit_code']
        assert result.output==expected


def test_recorded_cli_reports_basis_unpinned_outputs_and_correct_modes(inputs):
    alter_provenance(inputs,lambda p:[p['outputs']['full'].pop(k) for k in ('sha256','md5')])
    result=invoke(inputs,'--json');data=json.loads(result.output)
    assert result.exit_code==1
    assert data['coverage']=={'selected':1,'checked':1,'unavailable':0,'defects':1}
    one=data['records'][0]
    assert one['output_association']['historical_output']=='unpinned'
    assert one['artifact']['sha256']==hashlib.sha256(inputs['full'].read_bytes()).hexdigest()
    assert one['provenance']['sha256']==hashlib.sha256(inputs['provenance'].read_bytes()).hexdigest()
    assert one['defects'][0]['mode']=='unknown_type'
    text=invoke(inputs)
    assert 'policy=recorded' in text.output and 'output=unpinned' in text.output
    assert 'schema='+one['selected_schema']['sha256'] in text.output


@pytest.mark.parametrize('case',['core-slot-absent','full-root-absent','other-range','local-import','bad-yaml','missing-schema','schema-fallback'])
def test_unavailable_is_not_zero_findings_or_current_authority(inputs,case):
    kind='core' if case=='core-slot-absent' else 'full'
    if case=='core-slot-absent':replace_schema(inputs,schema(core=True,related=False),'core')
    elif case=='full-root-absent':replace_schema(inputs,schema(core=True))
    elif case=='other-range':replace_schema(inputs,schema(target='SelectedRelationship'))
    elif case=='local-import':
        doc=yaml.safe_load(schema());doc['imports'].append('uncaptured-local');replace_schema(inputs,yaml.safe_dump(doc).encode())
    elif case=='bad-yaml':replace_schema(inputs,b'not: [valid')
    elif case=='missing-schema':alter_provenance(inputs,lambda p:p.update(schema={}))
    if case=='schema-fallback':
        from data_sheets_schema import run_schema
        with patch.object(run_schema,'run_schema_bytes',return_value=(schema(),{'source':run_schema.TODAY,'reason':'historical missing'})):
            one=check(inputs)
    else:one=check(inputs,kind)
    assert not one['checked'] and one['selected_schema'] is None and one['defects']==[]
    assert one['reason']
    if case!='schema-fallback':
        result=invoke(inputs,'--json',kind=kind);data=json.loads(result.output)
        assert result.exit_code==2 and data['coverage']['unavailable']==1 and data['coverage']['checked']==0


@pytest.mark.parametrize('case',['path','bytes','bool-size','sha256','md5','both-hashes','missing-output','missing-path'])
def test_every_supplied_output_declaration_is_bound(inputs,case):
    def change(p):
        out=p['outputs']['full']
        if case=='path':out['path']=str(inputs['core'])
        elif case=='bytes':out['bytes']+=1
        elif case=='bool-size':out['bytes']=True
        elif case in ('sha256','md5'):out[case]='0'*len(out[case])
        elif case=='both-hashes':out['md5']='0'*32
        elif case=='missing-output':p['outputs'].pop('full')
        else:out.pop('path')
    alter_provenance(inputs,change)
    one=check(inputs)
    assert not one['checked'] and one['selected_schema'] is None and one['reason']


@pytest.mark.parametrize('algorithm',['sha256','md5'])
@pytest.mark.parametrize('value',[None,123,True,'',[],{},'0'*31,'g'*64])
def test_malformed_schema_hash_cannot_hide_behind_another_valid_hash(inputs,algorithm,value):
    from data_sheets_schema import run_schema
    raw=inputs['full_schema'].read_bytes()
    def change(p):
        p['schema'].update(full_sha256=hashlib.sha256(raw).hexdigest(),full_md5=hashlib.md5(raw).hexdigest())
        p['schema']['full_'+algorithm]=value
    alter_provenance(inputs,change)
    with patch.object(run_schema,'run_schema_bytes',side_effect=AssertionError('must reject before recovery')) as recover:
        one=check(inputs)
        result=invoke(inputs,'--json')
    assert not one['checked'] and one['selected_schema'] is None
    assert f'malformed recorded schema full_{algorithm}' in one['reason']
    assert result.exit_code==2 and json.loads(result.output)['coverage']['unavailable']==1
    recover.assert_not_called()


def test_valid_md5_only_and_other_kind_bad_hash_stay_separate(inputs):
    raw=inputs['full_schema'].read_bytes()
    def change(p):
        p['schema'].pop('full_sha256')
        p['schema'].update(full_md5=hashlib.md5(raw).hexdigest(),core_sha256=None)
    alter_provenance(inputs,change)
    full,core=check(inputs),check(inputs,'core')
    assert full['checked'] and full['selected_schema']['sha256']==hashlib.sha256(raw).hexdigest()
    assert not core['checked'] and 'core_sha256' in core['reason']


def test_returned_schema_bytes_must_match_every_supplied_hash(inputs):
    from data_sheets_schema import run_schema
    raw=inputs['full_schema'].read_bytes()
    alter_provenance(inputs,lambda p:p['schema'].update(full_md5='0'*32))
    with patch.object(run_schema,'run_schema_bytes',return_value=(raw,{'source':"the run's schema, a git blob"})):
        one=check(inputs)
    assert not one['checked'] and one['selected_schema'] is None
    assert 'differs from a supplied schema hash' in one['reason']


@pytest.mark.parametrize('case',['schema','output-path','output-hash','record-key','merge-pin','record-merge'])
def test_ambiguous_yaml_declarations_cannot_disappear_before_binding(inputs,case):
    path=inputs['provenance']
    raw=path.read_text()
    if case=='schema':raw='schema: {}\n'+raw
    elif case in ('output-path','output-hash'):
        key='path' if case=='output-path' else 'sha256'
        lines=raw.splitlines(keepends=True)
        index=next(i for i,line in enumerate(lines) if line.startswith('    '+key+':'))
        lines.insert(index,'    '+key+': contradictory\n');raw=''.join(lines)
    elif case=='merge-pin':
        raw=raw.replace('outputs:\n','pin: &pin {sha256: contradictory}\noutputs:\n',1)
        raw=raw.replace('  full:\n','  full:\n    <<: *pin\n',1)
    else:
        path=inputs['full'];raw=path.read_text()
        raw=('related_datasets: []\n'+raw if case=='record-key' else 'defaults: &defaults {id: hidden}\n<<: *defaults\n'+raw)
        path.write_text(raw)
        alter_provenance(inputs,lambda p:p['outputs']['full'].update(bytes=len(raw.encode()),
            sha256=hashlib.sha256(raw.encode()).hexdigest(),md5=hashlib.md5(raw.encode()).hexdigest()))
    path.write_text(raw)
    one=check(inputs)
    assert not one['checked'] and one['selected_schema'] is None
    assert 'duplicate' in one['reason'].lower() or 'merge' in one['reason'].lower()


def test_unrelated_typed_yaml_scalars_do_not_change_identity_or_parse_policy(inputs):
    raw=inputs['full'].read_bytes()+b'issued: 2026-01-02\nmetadata: {1: one, "2": two}\n'
    inputs['full'].write_bytes(raw)
    alter_provenance(inputs,lambda p:p['outputs']['full'].update(bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),md5=hashlib.md5(raw).hexdigest()))
    assert check(inputs)['checked']


def test_capture_does_not_reopen_schema_or_current_vocabulary(inputs):
    from data_sheets_schema import run_schema
    raw=inputs['full_schema'].read_bytes();inputs['full_schema'].unlink()
    with patch.object(run_schema,'run_schema_bytes',return_value=(raw,{'source':"the run's schema, a git blob",'commit':'test'})) as selected, \
         patch.object(legacy,'_vocabulary',side_effect=AssertionError('ambient current table')):
        one=check(inputs)
    assert one['checked'] and selected.call_count==1
    assert one['selected_schema']['sha256']==hashlib.sha256(raw).hexdigest()
    assert one['defects'][0]['mode']=='unknown_type'


def test_induced_inherited_owner_slots_and_explicit_overrides(inputs):
    doc=yaml.safe_load(schema())
    doc['classes']['Parent']=doc['classes'].pop('Dataset')
    doc['classes']['Dataset']={'is_a':'Parent'}
    doc['classes']['RelationParent']=doc['classes'].pop('SelectedRelationship')
    doc['classes']['SelectedRelationship']={'is_a':'RelationParent','slot_usage':{'relationship_type':{'range':'OverrideType'}}}
    doc['enums']['OverrideType']={'permissible_values':{'is_new_version_of':{'aliases':['IsNewVersionOf']}}}
    replace_schema(inputs,yaml.safe_dump(doc).encode())
    one=check(inputs)
    assert one['checked'] and one['selected_schema']['enum']=='OverrideType'
    assert one['defects'][0]['mode']=='aliased_type'


def test_conflicting_aliases_and_snapshot_replacement_are_not_order_dependent(inputs):
    assert check(inputs)['defects'][0]['mode']=='unknown_type'
    replace_schema(inputs,schema(aliases=['IsNewVersionOf']))
    assert check(inputs)['defects'][0]['mode']=='aliased_type'
    doc=yaml.safe_load(schema(aliases=['IsNewVersionOf']))
    doc['enums']['SelectedType']['permissible_values']['has_part']={'aliases':['IsNewVersionOf']}
    replace_schema(inputs,yaml.safe_dump(doc).encode())
    one=check(inputs)
    assert not one['checked'] and 'multiple targets' in one['reason']


@pytest.mark.parametrize('slot',['relationship_type','target_dataset'])
def test_schema_permitted_lists_are_not_labeled_scalar_defects(inputs,slot):
    doc=yaml.safe_load(schema())
    doc['classes']['SelectedRelationship']['attributes'][slot]['multivalued']=True
    replace_schema(inputs,yaml.safe_dump(doc).encode())
    one=check(inputs)
    assert not one['checked'] and 'multivalued' in one['reason']


def test_canonical_cli_preserves_variant_and_provenance_and_exposes_core_unavailability(inputs):
    replace_schema(inputs,schema(core=True,related=False),'core')
    from data_sheets_schema import runs
    marked={'EXAMPLE':{'full':str(inputs['full']),'core':str(inputs['core']),'provenance':str(inputs['provenance'])}}
    with patch.object(runs,'canonical_runs',return_value=marked) as canonical:
        result=CliRunner().invoke(evaluate,['related-datasets','--schema-policy','recorded','--runtime','api','--json'])
    assert result.exit_code==2
    data=json.loads(result.output)
    assert data['coverage']=={'selected':2,'checked':1,'unavailable':1,'defects':1}
    assert [r['kind'] for r in data['records']]==['full','core']
    assert not data['records'][1]['checked']
    canonical.assert_called_once_with(runtime='api')


@pytest.mark.parametrize('flags',[
    ['--schema-policy','recorded'],
    ['--schema-policy','recorded','--kind','full'],
    ['--provenance','no-file','--kind','full'],
    ['--json'],
])
def test_explicit_cli_association_is_required_without_changing_legacy_default(inputs,flags):
    result=CliRunner().invoke(evaluate,['related-datasets',*flags,str(inputs['full'])])
    assert result.exit_code==2


def test_no_record_provenance_or_schema_mutation(inputs):
    before={p:p.read_bytes() for p in inputs.values()}
    for kind in ('full','core'):
        assert check(inputs,kind)['checked']
        assert invoke(inputs,'--json',kind=kind).exit_code==1
    assert {p:p.read_bytes() for p in inputs.values()}==before


def test_checked_zero_defects_still_displays_selected_authority(inputs):
    raw=inputs['full'].read_bytes().replace(b'IsNewVersionOf',b'has_part')
    inputs['full'].write_bytes(raw)
    alter_provenance(inputs,lambda p:p['outputs']['full'].update(bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),md5=hashlib.md5(raw).hexdigest()))
    result=invoke(inputs)
    assert result.exit_code==0 and 'schema=' in result.output and 'output=hash_verified' in result.output
    assert '0 defect(s) across 1 checked record(s); 0 unavailable of 1 selected' in result.output


@pytest.mark.corpus
def test_four_tracked_full_records_correct_eighteen_modes_without_gate_or_input_changes():
    selected=[('claudecode_agent','2026-07-31_claude-opus-5-generic-v2_rep2','AI_READI',3),
              ('claudecode_agent','2026-07-31_claude-opus-5-generic-v2_rep3','AI_READI',3),
              ('claudecode_agent','2026-07-31_claude-opus-5-generic-v2_rep3','VOICE',3),
              ('claudecode_agent_crate','2026-07-31_claude-opus-5-api-generic_rep1','CM4AI',9)]
    before={}
    for method,label,project,count in selected:
        full=ROOT/'data/d4d_concatenated'/method/label/f'{project}_d4d.yaml'
        core=ROOT/'data/d4d_concatenated'/(method+'_core')/label/f'{project}_d4d_core.yaml'
        prov=core.with_name(f'{project}_provenance.yaml')
        for p in (full,core,prov):before[p]=p.read_bytes()
        assert [d.mode for d in legacy.inspect(yaml.safe_load(before[full]))]==['aliased_type']*count
        result=CliRunner().invoke(evaluate,['related-datasets','--schema-policy','recorded',
            '--provenance',str(prov),'--kind','full','--json',str(full)])
        assert result.exit_code==1,result.output
        data=json.loads(result.output)
        one=data['records'][0]
        assert one['checked'] and data['coverage']['defects']==count
        assert [d['mode'] for d in one['defects']]==['unknown_type']*count
        assert one['selected_schema']['sha256']=='2065cea2d1a01c390ac1ef1d3db94be101f203f2a2682c0eee489ec29e45ebe9'
        assert one['output_association']['historical_output']=='unpinned'
        core_result=diagnostics.check_record(core,prov,kind='core')
        assert not core_result['checked'] and 'CoreDataset.related_datasets' in core_result['reason']
    assert all(p.read_bytes()==raw for p,raw in before.items())
