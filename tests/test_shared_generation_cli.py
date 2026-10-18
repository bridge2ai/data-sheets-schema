"""Opt-in CLI authority/routing only; downstream execution is explicitly stubbed.

Actual RunSpec/capture/rendering and receipt policy checks are used. These tests
are not acceptance evidence for C's separate complete typed runtime pipeline.
"""
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from pathlib import Path
import socket

from click.testing import CliRunner
import pytest

from data_sheets_schema import api_runner as api, shared_generation as sg, run_lock
from data_sheets_schema.cli import cli
from tests.test_generation_manifest_identity import external
from tests.test_shared_generation_selection import registration_for

module = importlib.import_module('data_sheets_schema.cli.api')


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})


@pytest.fixture
def registered(external):
    base = replace(external, method='claudecode_api', label='shared_rep1')
    reg = registration_for(base)
    Path(reg['registration_path']).write_bytes(sg.canonical(reg))
    return base, reg


def options(reg):
    return ['--shared-generation-version', '1', '--shared-generation-registration', reg['registration_path']]


def single(reg, command='plan', extra=()):
    return CliRunner().invoke(cli, ['api', command, '--project', reg['run']['project'],
        '--label', reg['run']['label'], *options(reg), *extra])


def stub_plan(spec):
    return {'project': spec.project, 'condition': spec.condition,
        'approx_total_input_tokens': None, 'full_request_approx_input_tokens': 7,
        'registered_audit_allowances': sg.capture(spec).document()['audit_limits'],
        'outputs': {'full': str(spec.full_path)}, 'model': {'name': 'synthetic'},
        'shared_generation_version': spec.shared_generation_version}


@pytest.mark.parametrize('command', ['plan', 'render-prompt', 'run'])
def test_each_single_route_constructs_actual_selected_spec(registered, monkeypatch, command):
    base, reg = registered
    observed=[]
    def plan(spec):observed.append(spec);return stub_plan(spec)
    def execute(spec):
        observed.append(spec)
        return {'project': spec.project, 'label': spec.label, 'usage': [], 'outputs': {}, 'validation_problems': []}
    monkeypatch.setattr(api, 'plan', plan)
    monkeypatch.setattr(api, 'execute', execute)
    result=single(reg,command,('--yes',) if command=='run' else ())
    assert result.exit_code==0,result.output
    if command=='render-prompt':
        assert 'Shared generation rules v1' in result.output
        assert 'Claude API (direct)' in result.output
    else:
        assert 'dynamic total unavailable' in result.output
        for spec in observed:
            assert (spec.condition,spec.render_version,spec.runtime,spec.api_playbook_version,spec.receipt_completion_version)==('generic_v10',25,api.RUNTIME,2,2)
            assert spec.bundle==base.bundle and spec.manifest==base.manifest
            assert json.loads(spec.shared_generation_registration)==reg
            assert spec.profile_basis==reg['inputs']['profile']['basis']


@pytest.mark.parametrize('flag,value', [('--condition','generic_v9'),('--arm','crate_only'),
    ('--api-playbook-version','0'),('--api-playbook-version','1'),
    ('--receipt-completion-version','0'),('--receipt-completion-version','1'),
    ('--removal-repair-version','1'),('--runtime','Claude Code'),('--provider','Anthropic'),
    ('--bundle','/unrelated'),('--chunk-manifest','/unrelated'),('--manifest','none')])
def test_explicit_conflicts_refuse_before_render(registered, flag, value):
    result=single(registered[1],'render-prompt',(flag,value))
    assert result.exit_code==1,result.output
    assert 'conflicts with shared registration' in result.output


def test_matching_explicit_axes_and_paths_are_allowed(registered):
    base,reg=registered
    result=single(reg,'render-prompt',('--runtime',api.RUNTIME,'--provider',reg['runtime']['provider'],
        '--condition','generic_v10','--api-playbook-version','2','--receipt-completion-version','2',
        '--bundle',str(base.bundle),'--manifest',str(base.manifest),'--chunk-manifest',str(base.chunk_manifest)))
    assert result.exit_code==0,result.output


@pytest.mark.parametrize('case',['missing_version','missing_path','zero_version','wrong_project','wrong_label','duplicate_json','invalid_utf8'])
def test_invalid_registration_selection_is_named_refusal(registered, case):
    _,reg=registered
    args=['api','plan','--project',reg['run']['project'],'--label',reg['run']['label'],*options(reg)]
    if case=='missing_version':del args[6:8]
    elif case=='missing_path':del args[8:10]
    elif case=='zero_version':args[7]='0'
    elif case=='wrong_project':args[3]='OTHER'
    elif case=='wrong_label':args[5]='other'
    else:
        path=Path(reg['registration_path']);raw=path.read_bytes()
        path.write_bytes(raw[:-1]+b',"format":"duplicate"}' if case=='duplicate_json' else b'\xff')
    result=CliRunner().invoke(cli,args)
    assert result.exit_code==1,result.output
    assert 'Error:' in result.output and 'Traceback' not in result.output


def test_render_cannot_overwrite_input_authority(registered):
    _,reg=registered;path=Path(reg['registration_path']);before=path.read_bytes()
    result=single(reg,'render-prompt',('--out',str(path)))
    assert result.exit_code==1 and path.read_bytes()==before


def test_changed_registration_after_plan_refuses_before_execute(registered, monkeypatch):
    _,reg=registered
    def plan(spec):
        value=stub_plan(spec);Path(reg['registration_path']).write_bytes(sg.canonical(reg)+b'\n');return value
    monkeypatch.setattr(api,'plan',plan)
    monkeypatch.setattr(api,'execute',lambda *a:pytest.fail('changed authority reached execution'))
    result=single(reg,'run',('--yes',))
    assert result.exit_code==1 and 'authority changed' in result.output


def roster(base,reg,*,count=2,pending=False):
    rows=[]
    for i in range(1,count+1):
        current=deepcopy(reg);current['run']['label']=f'shared_rep{i}'
        current['registration_id']=f'synthetic-{i}'
        path=Path(reg['registration_path']).with_name(f'registration-{i}.json')
        current['registration_path']=str(path)
        if not pending:current['receipt']['coverage_floor']={'state':'registered','numerator':1,'denominator':2}
        path.write_bytes(sg.canonical(current))
        rows.append({'project':base.project,'label':current['run']['label'],'registration_path':str(path)})
    path=base.bundle.parent/'roster.json';path.write_bytes(sg.canonical({'format':'shared_generation_batch_roster_v1','registrations':rows}))
    return path,rows


def batch(reg,path,count=2,extra=()):
    return CliRunner().invoke(cli,['api','batch','--projects',reg['run']['project'],
        '--label-prefix','shared','--replicates',str(count),'--shared-generation-version','1',
        '--shared-generation-registration',str(path),'--no-branch-guard','--yes',*extra])


def test_batch_exact_roster_routes_each_registration(registered,monkeypatch):
    base,reg=registered;path,rows=roster(base,reg);seen=[]
    def plan(spec):seen.append(spec);return stub_plan(spec)
    monkeypatch.setattr(api,'plan',plan)
    result=batch(reg,path,extra=('--dry-run',))
    assert result.exit_code==0,result.output
    assert [s.label for s in seen]==['shared_rep1','shared_rep2']
    assert [json.loads(s.shared_generation_registration)['registration_path'] for s in seen]==[r['registration_path'] for r in rows]
    assert result.output.count('dynamic total unavailable')==2


@pytest.mark.parametrize('damage',['single','missing','extra','duplicate','reused_id','wrong_row','duplicate_key','unrequested_bundle'])
def test_batch_roster_is_complete_unique_and_explicit(registered, monkeypatch,damage):
    base,reg=registered;path,rows=roster(base,reg)
    value=json.loads(path.read_bytes());extra=('--dry-run',)
    if damage=='single':path=Path(reg['registration_path'])
    elif damage=='missing':value['registrations'].pop()
    elif damage=='extra':value['registrations'].append({**rows[0],'label':'extra'})
    elif damage=='duplicate':value['registrations'].append(rows[0])
    elif damage=='reused_id':
        target=Path(rows[1]['registration_path']);item=json.loads(target.read_bytes());item['registration_id']='synthetic-1';target.write_bytes(sg.canonical(item))
    elif damage=='wrong_row':value['registrations'][0]['project']='OTHER'
    elif damage=='unrequested_bundle':extra+=('--project-bundle','UNREQUESTED=/not/used')
    if damage not in ('single','reused_id'):
        raw=sg.canonical(value)
        path.write_bytes(raw[:-1]+b',"format":"duplicate"}' if damage=='duplicate_key' else raw)
    monkeypatch.setattr(api,'plan',lambda *a:pytest.fail('invalid roster reached planning'))
    result=batch(reg,path,extra=extra)
    assert result.exit_code==1,result.output


@pytest.mark.parametrize('extra',[(),('--no-canary-gate',),('--continue-on-error',)])
def test_pending_selected_floor_never_fans_out_from_raw_default_zero(registered,monkeypatch,extra):
    base,reg=registered;path,_=roster(base,reg,pending=True)
    monkeypatch.setattr(api,'execute',lambda *a:pytest.fail('pending floor reached execution'))
    result=batch(reg,path,extra=extra)
    assert result.exit_code==1 and ('pending' in result.output or 'cannot bypass' in result.output)


def test_changed_roster_after_confirmation_refuses_before_lock(registered,monkeypatch):
    base,reg=registered;path,_=roster(base,reg,count=1)
    def plan(spec):
        value=stub_plan(spec);path.write_bytes(path.read_bytes()+b'\n');return value
    monkeypatch.setattr(api,'plan',plan)
    monkeypatch.setattr(run_lock,'acquire',lambda *a:pytest.fail('changed roster reached lock'))
    result=batch(reg,path,count=1)
    assert result.exit_code==1 and 'roster changed' in result.output


def test_roster_inside_run_output_is_refused(registered,monkeypatch):
    base,reg=registered;path,rows=roster(base,reg,count=1)
    captured=module._capture_shared_registration(rows[0]['registration_path'])
    spec=module._shared_spec(base.project,'baseline','shared_rep1',None,None,None,None,None,
        module._UNSET,None,0,0,0,None,captured)
    spec.full_path.parent.mkdir(parents=True)
    inside=spec.full_path.parent/'roster.json';inside.write_bytes(path.read_bytes())
    monkeypatch.setattr(api,'plan',lambda *a:pytest.fail('run-owned roster reached planning'))
    result=batch(reg,inside,count=1,extra=('--dry-run',))
    assert result.exit_code==1 and 'outside every run' in result.output


def test_no_shared_selection_retains_old_spec_and_display(external,monkeypatch):
    args=['api','render-prompt','--project',external.project,'--label',external.label,
          '--bundle',str(external.bundle),'--manifest',str(external.manifest),'--condition','generic_v6']
    first=CliRunner().invoke(cli,args)
    second=CliRunner().invoke(cli,[*args,'--shared-generation-version','0'])
    assert first.exit_code==second.exit_code==0
    assert first.output==second.output
    spec=module._spec(external.project,'baseline',external.label,'generic_v6',external.bundle,manifest=external.manifest)
    assert 'shared_generation_version' not in spec.render_spec()


@pytest.mark.parametrize('damage',['missing','foreign_policy','unchecked','passed'])
def test_actual_selected_receipt_policy_controls_each_batch_dispatch(registered,monkeypatch,damage):
    from data_sheets_schema import receipt_completion_policy as cp, receipts
    base,reg=registered;path,_=roster(base,reg,count=2)
    calls=[];released=[]
    monkeypatch.setattr(api,'plan',stub_plan)
    monkeypatch.setattr(run_lock,'acquire',lambda *a:base.bundle.parent/'test-lock')
    monkeypatch.setattr(run_lock,'release',released.append)
    def execute(spec):
        calls.append(spec.label)
        policy=cp.select_policy(spec.render_spec())
        receipt={'checked':True,'expected':True,'instrument':receipts.RERECEIPTS_INSTRUMENT,
            'slots':{'with_receipt':3,'receiptable':3},'findings':[],
            'chunks':{'total':1,'reviewed':1},'snippets':{'verified':1},cp.BLOCK_KEY:cp.block_identity(policy)}
        if damage=='foreign_policy':
            other=deepcopy(policy['registration']);other['registration_id']='unrelated'
            receipt[cp.BLOCK_KEY]['registration']=cp.registration_identity(sg.canonical(other),version=2)
        if damage=='unchecked':receipt['checked']=False
        checks={'pair':{'ran':True,'errors':0},'report':{'checked':True,'claims_checked':1,'findings':[]},
            'grounding':{'checked':True,'distinct':{'absent':0}},
            'form':{'checked':True,'organisational_fragments':0,'undeclared_prefix_occurrences':0,'british_spellings':0}}
        if damage!='missing':checks['receipts']=receipt
        provenance=base.bundle.parent/(spec.label+'.yaml')
        provenance.write_bytes(sg.canonical({'run':{'project':spec.project}}))
        return {'usage':[],'skipped':[],'validation_problems':[],'checks':checks,
                'outputs':{'provenance':str(provenance)}}
    monkeypatch.setattr(api,'execute',execute)
    result=batch(reg,path,extra=('--continue-on-error',))
    assert len(released)==1,result.output
    if damage=='passed':
        assert result.exit_code==0 and calls==['shared_rep1','shared_rep2'],result.output
        assert result.output.count('registered receipt gate passed')==2
    else:
        assert result.exit_code==1 and calls==['shared_rep1'],result.output
        assert 'Remaining runs were stopped' in result.output
        assert '--no-canary-gate' not in result.output


@pytest.mark.parametrize('command',['plan','run'])
def test_downstream_value_errors_are_named_cli_refusals(registered,monkeypatch,command):
    def refused(*a):raise ValueError('synthetic selected contract refusal')
    monkeypatch.setattr(api,'plan',refused if command=='plan' else stub_plan)
    monkeypatch.setattr(api,'execute',refused)
    result=single(registered[1],command,('--yes',) if command=='run' else ())
    assert result.exit_code==1 and 'Error: synthetic selected contract refusal' in result.output


def test_shared_batch_never_discovers_projects_from_default_manifest(registered):
    base,reg=registered;path,_=roster(base,reg)
    result=CliRunner().invoke(cli,['api','batch','--label-prefix','shared','--replicates','2',
        '--shared-generation-version','1','--shared-generation-registration',str(path),'--dry-run'])
    assert result.exit_code==1 and 'requires explicit --projects' in result.output


def test_registration_special_file_is_refused_without_blocking(tmp_path):
    import os
    import click
    pipe=tmp_path/'registration.pipe';os.mkfifo(pipe)
    with pytest.raises(click.ClickException,match='regular file'):
        module._bounded_registration_bytes(pipe)


def test_two_projects_two_replicates_keep_distinct_registered_contexts(registered,tmp_path,monkeypatch):
    import yaml
    first,reg=registered
    other_root=tmp_path/'other';other_root.mkdir()
    other=external.__wrapped__(other_root)
    metadata=yaml.safe_load(other.manifest.read_bytes())
    metadata['projects']['SECOND']=metadata['projects'].pop('EXTERNAL')
    metadata['naming']['SECOND']=metadata['naming'].pop('EXTERNAL')
    other.manifest.write_text(yaml.safe_dump(metadata))
    other=replace(other,project='SECOND',method='claudecode_api',label='shared_rep1')
    second_reg=registration_for(other)
    first_path,first_rows=roster(first,reg)
    _,second_rows=roster(other,second_reg)
    for row in second_rows:
        path=Path(row['registration_path']);value=json.loads(path.read_bytes())
        value['registration_id']='second-'+value['registration_id'];path.write_bytes(sg.canonical(value))
    first_path.write_bytes(sg.canonical({'format':'shared_generation_batch_roster_v1',
                                       'registrations':first_rows+second_rows}))
    seen=[]
    def plan(spec):seen.append(spec);return stub_plan(spec)
    monkeypatch.setattr(api,'plan',plan)
    result=CliRunner().invoke(cli,['api','batch','--projects','EXTERNAL,SECOND','--label-prefix','shared',
        '--replicates','2','--shared-generation-version','1','--shared-generation-registration',str(first_path),'--dry-run'])
    assert result.exit_code==0,result.output
    assert [(s.project,s.label) for s in seen]==[(p,f'shared_rep{n}') for p in ('EXTERNAL','SECOND') for n in (1,2)]
    assert [s.bundle for s in seen]==[first.bundle,first.bundle,other.bundle,other.bundle]
    contexts=[json.loads(s.shared_generation_registration)['inputs']['context']['path'] for s in seen]
    assert contexts[0]==contexts[1] and contexts[2]==contexts[3] and contexts[0]!=contexts[2]


def test_render_status_names_registered_arm_with_omitted_cli_arm(registered):
    _base, reg = registered
    reg['run']['arm'], reg['run']['method'] = module.ARMS['de_novo'][:2]
    Path(reg['registration_path']).write_bytes(sg.canonical(reg))
    result = single(reg, 'render-prompt')
    assert result.exit_code == 0, result.output
    assert ' / de_novo / runtime=Claude API (direct)' in result.output
    assert ' / baseline / runtime=' not in result.output


@pytest.mark.parametrize('command', ['plan', 'render-prompt', 'run', 'batch'])
def test_help_discloses_selected_v2_boundaries(command):
    result = CliRunner().invoke(cli, ['api', command, '--help'])
    assert result.exit_code == 0
    text = ' '.join(result.output.split())
    assert '2 requires shared generation 1 / API renderer 25' in text
