"""Selected output ownership, using real path helpers and neutral local files."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os

import pytest
import yaml

from data_sheets_schema import api_runner as api, output_ownership as ownership
from data_sheets_schema import usage_ledger as ledger, snapshot_store


def spec(root, project='A', label='one', *, shared=1, flat=False):
    full = root / ('flat' if flat else 'full') / label
    metadata = root / ('flat' if flat else 'core') / label
    return SimpleNamespace(project=project, label=label, method='claudecode_api',
        condition='generic_v10', shared_generation_version=shared,
        full_path=full / f'{project}_d4d.yaml',
        core_path=metadata / f'{project}_d4d_core.yaml',
        report_path=metadata / f'{project}_reconciliation.md',
        provenance_path=metadata / f'{project}_provenance.yaml',
        metadata_dir=metadata)


def snapshot(root):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def declarations(s, generation='generation-one'):
    ident = ledger.run_identity(s)
    return {
        'ledger': (ledger.ledger_path(s), {'version':1, 'identity':ident,
            'generation_id':generation, 'rows':[], 'input_identity':{}}),
        'progress': (api._progress_path(s), {'run_identity':ident,
            'generation_id':generation, 'label':s.label, 'completed':[]}),
        'provenance': (s.provenance_path, {'run':{**ident, 'generation_id':generation}}),
        'index': (snapshot_store.index_path(s.metadata_dir,s.project), {'version':1,
            'run_identity':ident, 'generation_id':generation, 'snapshots':[], 'input_identity':{}}),
    }


def install(s, kinds=('ledger','progress','provenance','index')):
    values=declarations(s)
    for kind in kinds:
        write(*values[kind])
    return values


def test_shared_container_disjoint_projects_and_readonly_inputs_are_valid(tmp_path):
    a,b=spec(tmp_path,'A'),spec(tmp_path,'AB')
    install(a);install(b)
    a.full_path.parent.mkdir(parents=True,exist_ok=True)
    a.full_path.write_text('first');b.full_path.write_text('second')
    shared_input=tmp_path/'read-only.txt';shared_input.write_text('shared input authority')
    a.bundle=b.bundle=shared_input
    before=snapshot(tmp_path)
    ownership.require_disjoint_selected_outputs([a,b])
    ownership.require_selected_resume_owner(a,resume=True)
    ownership.require_selected_resume_owner(b,resume=True)
    assert snapshot(tmp_path)==before


@pytest.mark.parametrize('flat',[False,True])
def test_same_project_directory_alias_fails_without_writes(tmp_path,flat):
    a,b=spec(tmp_path,label='one',flat=flat),spec(tmp_path,label='two',flat=flat)
    for first,second in {(a.full_path.parent,b.full_path.parent),(a.metadata_dir,b.metadata_dir)}:
        first.mkdir(parents=True,exist_ok=True);second.symlink_to(first,target_is_directory=True)
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='ownership|namespaces'):
        ownership.require_disjoint_selected_outputs([a,b])
    assert snapshot(tmp_path)==before


@pytest.mark.parametrize('point',['full','receipt','progress','reasoning','abandoned','ledger','index','lock'])
def test_existing_auxiliary_or_primary_inode_alias_fails(tmp_path,point):
    a,b=spec(tmp_path,label='one'),spec(tmp_path,label='two')
    def chosen(s):
        return {'full':s.full_path,'receipt':api._receipt_path(s),'progress':api._progress_path(s),
            'reasoning':api._reasoning_path(s),'abandoned':ledger.abandoned_journal_path(s),
            'ledger':ledger.ledger_path(s),'index':snapshot_store.index_path(s.metadata_dir,s.project),
            'lock':ledger.output_locks((s.full_path,))[0][1]}[point]
    p,q=chosen(a),chosen(b)
    p.parent.mkdir(parents=True,exist_ok=True);q.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(b'original neutral bytes');os.link(p,q)
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='ownership'):
        ownership.require_disjoint_selected_outputs([a,b])
    assert snapshot(tmp_path)==before


def test_primary_to_other_runs_immutable_evidence_alias_fails(tmp_path):
    a,b=spec(tmp_path,'A'),spec(tmp_path,'B')
    evidence=b.metadata_dir/'intermediate'/'B_full_2.yaml'
    evidence.parent.mkdir(parents=True);evidence.write_text('retained phase')
    a.full_path.parent.mkdir(parents=True);os.link(evidence,a.full_path)
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='ownership'):
        ownership.require_disjoint_selected_outputs([a,b])
    assert snapshot(tmp_path)==before


@pytest.mark.parametrize('other',['a','A_more'])
def test_conservative_case_and_delimiter_nested_names_require_distinct_containers(tmp_path,other):
    a,b=spec(tmp_path,'A'),spec(tmp_path,other)
    with pytest.raises(ValueError,match='ownership|namespaces'):
        ownership.require_disjoint_selected_outputs([a,b])
    ownership.require_disjoint_selected_outputs([a,spec(tmp_path,other,label='other')])


def test_different_project_same_container_without_existing_leaves_passes(tmp_path):
    ownership.require_disjoint_selected_outputs([spec(tmp_path,'A'),spec(tmp_path,'B')])
    assert list(tmp_path.iterdir())==[]


def test_directory_symlink_inside_owned_namespace_is_not_followed(tmp_path):
    s=spec(tmp_path);external=tmp_path/'outside';external.mkdir()
    secret=external/'retained';secret.write_bytes(b'unchanged')
    s.metadata_dir.mkdir(parents=True)
    (s.metadata_dir/'A_nested').symlink_to(external,target_is_directory=True)
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='regular file'):
        ownership.require_disjoint_selected_outputs([s])
    assert snapshot(tmp_path)==before


def test_bounded_inventory_and_state_bytes_refuse(tmp_path,monkeypatch):
    s=spec(tmp_path);s.metadata_dir.mkdir(parents=True)
    for n in range(3):(s.metadata_dir/f'other-{n}').write_text('untouched')
    before=snapshot(tmp_path)
    monkeypatch.setattr(ownership,'MAX_ENTRIES',2)
    with pytest.raises(ValueError,match='entry limit'):
        ownership.require_disjoint_selected_outputs([s])
    assert snapshot(tmp_path)==before
    monkeypatch.setattr(ownership,'MAX_ENTRIES',100)
    install(s,('ledger',));before=snapshot(tmp_path)
    monkeypatch.setattr(ownership,'MAX_STATE_BYTES',10)
    with pytest.raises(ValueError,match='byte limit'):
        ownership.require_selected_resume_owner(s,resume=True)
    assert snapshot(tmp_path)==before


def test_fresh_and_stable_locks_only_are_not_spent(tmp_path):
    s=spec(tmp_path)
    ownership.require_selected_resume_owner(s,resume=True)
    ownership.require_selected_resume_owner(s,resume=False)
    for _,lock in ledger.output_locks((s.full_path,s.core_path,s.report_path,s.provenance_path)):
        lock.parent.mkdir(parents=True,exist_ok=True);lock.write_bytes(b'')
    before=snapshot(tmp_path)
    ownership.require_selected_resume_owner(s,resume=True)
    ownership.require_selected_resume_owner(s,resume=False)
    assert snapshot(tmp_path)==before


@pytest.mark.parametrize('kind',['ledger','progress','provenance','index'])
@pytest.mark.parametrize('field',['label','generation'])
def test_each_live_declaration_independently_refuses_disagreement(tmp_path,kind,field):
    s=spec(tmp_path);rows=install(s)
    path,value=deepcopy(rows[kind])
    if field=='label':
        identity=value['identity' if kind=='ledger' else 'run' if kind=='provenance' else 'run_identity']
        identity['label']='foreign-label'
    elif kind=='provenance':value['run']['generation_id']='different-generation'
    else:value['generation_id']='different-generation'
    write(path,value);before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='foreign|disagree'):
        ownership.require_selected_resume_owner(s,resume=True)
    assert snapshot(tmp_path)==before


@pytest.mark.parametrize('kind',['ledger','progress','provenance','index'])
def test_malformed_live_declaration_cannot_hide_behind_matching_other_state(tmp_path,kind):
    s=spec(tmp_path);rows=install(s)
    rows[kind][0].write_text('[]')
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='mapping'):
        ownership.require_selected_resume_owner(s,resume=True)
    assert snapshot(tmp_path)==before


def test_progress_label_alias_and_typed_version_are_checked(tmp_path):
    s=spec(tmp_path);rows=install(s)
    path,value=deepcopy(rows['progress']);value['label']='foreign';write(path,value)
    with pytest.raises(ValueError,match='progress label'):
        ownership.require_selected_resume_owner(s,resume=True)
    write(*rows['progress'])
    path,value=deepcopy(rows['ledger']);value['version']=True;write(path,value)
    with pytest.raises(ValueError,match='version'):
        ownership.require_selected_resume_owner(s,resume=True)


@pytest.mark.parametrize('kind',['ledger','provenance'])
def test_duplicate_owner_keys_fail_closed(tmp_path,kind):
    s=spec(tmp_path);rows=install(s)
    path,value=rows[kind]
    if kind=='ledger':
        raw=json.dumps(value);path.write_text(raw[:-1]+', "generation_id": "generation-one"}')
    else:
        path.write_text(yaml.safe_dump(value)+'run: '+json.dumps(value['run'])+'\n')
    with pytest.raises(ValueError,match='duplicate'):
        ownership.require_selected_resume_owner(s,resume=True)


@pytest.mark.parametrize('kinds',[('ledger',),('ledger','progress'),('provenance',),('ledger','provenance')])
def test_matching_owner_with_optional_missing_index_resumes(tmp_path,kinds):
    s=spec(tmp_path);install(s,kinds)
    s.full_path.parent.mkdir(parents=True,exist_ok=True);s.full_path.write_text('owned output')
    before=snapshot(tmp_path)
    ownership.require_selected_resume_owner(s,resume=True)
    assert snapshot(tmp_path)==before
    assert not snapshot_store.index_path(s.metadata_dir,s.project).exists()


def test_automatic_date_or_instruction_is_not_consulted(tmp_path):
    s=spec(tmp_path);install(s)
    s.run_date='different day'
    def forbidden():raise AssertionError('input identity must remain with existing date-aware recovery')
    s.input_identity=forbidden
    ownership.require_selected_resume_owner(s,resume=True)


@pytest.mark.parametrize('where',['full','receipt','evidence','foreign-ledger'])
def test_unknown_spent_output_refuses_before_any_mutation(tmp_path,where):
    s=spec(tmp_path)
    point={'full':s.full_path,'receipt':api._receipt_path(s),
        'evidence':s.metadata_dir/'intermediate'/'A_full_2.yaml',
        'foreign-ledger':s.metadata_dir/'A_api_usage_0000000000000000.json'}[where]
    point.parent.mkdir(parents=True,exist_ok=True);point.write_text('unknown prior bytes')
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='ownership'):
        ownership.require_selected_resume_owner(s,resume=True)
    assert snapshot(tmp_path)==before


def test_explicit_no_resume_rejects_matching_spent_state(tmp_path):
    s=spec(tmp_path);install(s,('ledger',));before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='already spent'):
        ownership.require_selected_resume_owner(s,resume=False)
    assert snapshot(tmp_path)==before


def test_unrelated_project_and_legacy_foreign_state_do_not_change_contract(tmp_path):
    a,b=spec(tmp_path,'A'),spec(tmp_path,'B');install(b)
    before=snapshot(tmp_path)
    ownership.require_selected_resume_owner(a,resume=True)
    ownership.require_disjoint_selected_outputs([a,b])
    legacy=spec(tmp_path,'B',shared=0)
    ownership.require_selected_resume_owner(legacy,resume=False)
    ownership.require_disjoint_selected_outputs([legacy,legacy])
    assert snapshot(tmp_path)==before


def test_entrypoint_recheck_detects_new_foreign_owner(tmp_path):
    s=spec(tmp_path);install(s,('ledger',))
    ownership.require_selected_resume_owner(s,resume=True)
    row=declarations(s)['progress'];row[1]['run_identity']['label']='other-run';write(*row)
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='foreign'):
        ownership.require_selected_resume_owner(s,resume=True)
    assert snapshot(tmp_path)==before


def test_matching_own_ledger_does_not_hide_foreign_live_ledger(tmp_path):
    s=spec(tmp_path);install(s,('ledger',))
    foreign=spec(tmp_path,label='foreign')
    foreign.metadata_dir=s.metadata_dir
    path,value=declarations(foreign)['ledger'];write(path,value)
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='foreign'):
        ownership.require_selected_resume_owner(s,resume=True)
    assert snapshot(tmp_path)==before


def test_preserved_previous_ledger_archive_is_not_current_ownership(tmp_path):
    s=spec(tmp_path);install(s,('ledger',))
    archived=ledger.ledger_path(s).with_name(ledger.ledger_path(s).stem+'.previous-abc.json')
    write(archived,{'identity':{'label':'old foreign owner'},'generation_id':'old'})
    before=snapshot(tmp_path)
    ownership.require_selected_resume_owner(s,resume=True)
    assert snapshot(tmp_path)==before
