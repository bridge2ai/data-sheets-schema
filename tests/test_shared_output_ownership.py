"""Selected output ownership, using real path helpers and neutral local files."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
from itertools import permutations

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


@pytest.fixture
def no_effects(monkeypatch):
    """Even a regression cannot run an unsafe lock, writer or transport."""
    import socket
    from filelock import FileLock
    from data_sheets_schema import run_lock, schema_digest
    calls = []

    def forbidden(*args, **kwargs):
        calls.append('unexpected effect')
        raise AssertionError('read-only admission must precede writers and transports')

    for module, name in ((FileLock, 'acquire'), (run_lock, 'acquire'),
                         (run_lock, 'release'), (api, 'execute'), (api, '_execute'),
                         (api, '_call_with_usage'), (api, '_call_with_retry'),
                         (schema_digest, 'record_inventory'), (socket.socket, 'connect')):
        monkeypatch.setattr(module, name, forbidden)
    yield
    assert calls == []


def alias(source, destination, kind):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if kind == 'symlink':
        destination.symlink_to(source)
    else:
        os.link(source, destination)


def check_one(s, mode):
    if mode == 'batch':
        ownership.require_disjoint_selected_outputs([s])
    else:
        ownership.require_selected_resume_owner(s, resume=True)


@pytest.mark.parametrize('mode', ['batch', 'resume'])
@pytest.mark.parametrize('kind', ['hardlink', 'symlink'])
def test_own_full_and_actual_sidecar_refuse_before_any_writer(tmp_path, no_effects, mode, kind):
    s = spec(tmp_path)
    install(s, ('progress',))
    s.full_path.parent.mkdir(parents=True)
    s.full_path.write_bytes(b'neutral full record must remain intact')
    lock = ledger.output_locks((s.full_path,))[0][1]
    alias(s.full_path, lock, kind)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='conflicting output ownership'):
        check_one(s, mode)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('mode', ['batch', 'resume'])
@pytest.mark.parametrize('other', ['core', 'receipt', 'evidence'])
@pytest.mark.parametrize('kind', ['hardlink', 'symlink'])
def test_own_distinct_artifact_alias_refuses(tmp_path, no_effects, mode, other, kind):
    s = spec(tmp_path)
    install(s, ('progress',))
    s.full_path.parent.mkdir(parents=True)
    s.full_path.write_bytes(b'neutral exact original')
    target = {'core': s.core_path, 'receipt': api._receipt_path(s),
              'evidence': s.metadata_dir / 'intermediate' / 'A_full_2.yaml'}[other]
    alias(s.full_path, target, kind)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='conflicting output ownership'):
        check_one(s, mode)
    assert snapshot(tmp_path) == before


def test_distinct_mutable_roles_do_not_collapse_equal_paths(tmp_path, no_effects):
    s = spec(tmp_path)
    s.core_path = s.full_path
    before = snapshot(tmp_path)
    for mode in ('batch', 'resume'):
        with pytest.raises(ValueError, match='conflicting output ownership'):
            check_one(s, mode)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('kind', ['regular', 'symlink'])
def test_exact_artifact_repeated_as_evidence_is_harmless(tmp_path, no_effects, kind):
    s = spec(tmp_path, flat=True)
    install(s, ('progress',))
    if kind == 'symlink':
        target = tmp_path / 'same-intended-artifact.yaml'
        target.write_bytes(b'neutral full record')
        s.full_path.symlink_to(target)
    else:
        s.full_path.write_bytes(b'neutral full record')
    before = snapshot(tmp_path)
    for mode in ('batch', 'resume'):
        check_one(s, mode)
    assert snapshot(tmp_path) == before


def test_parent_alias_preserves_exact_leaf_evidence_identity(tmp_path, no_effects):
    s = spec(tmp_path, flat=True)
    install(s, ('progress',))
    s.full_path.write_bytes(b'neutral full record')
    parent_alias = tmp_path / 'same-parent'
    parent_alias.symlink_to(s.metadata_dir, target_is_directory=True)
    s.full_path = parent_alias / s.full_path.name
    before = snapshot(tmp_path)
    check_one(s, 'batch')
    check_one(s, 'resume')
    assert snapshot(tmp_path) == before


def test_two_distinct_evidence_spellings_cannot_hide_writer_in_any_order(tmp_path, no_effects):
    first, second = tmp_path / 'first.yaml', tmp_path / 'second.yaml'
    first.write_bytes(b'one preserved immutable inode')
    os.link(first, second)
    points = [ownership._Point(0, 'evidence', first),
              ownership._Point(0, 'evidence', second),
              ownership._Point(0, 'full', first)]
    before = snapshot(tmp_path)
    ownership._check_points(points[:2])  # Immutable evidence alone is not banned.
    for ordered in permutations(points):
        with pytest.raises(ValueError, match='conflicting output ownership'):
            ownership._check_points(ordered)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('target', ['progress', 'full', 'evidence'])
@pytest.mark.parametrize('kind', ['hardlink', 'symlink'])
def test_actual_batch_control_alias_refuses(tmp_path, no_effects, target, kind):
    from data_sheets_schema import run_lock
    s = spec(tmp_path)
    install(s, ('progress',))
    point = {'progress': api._progress_path(s), 'full': s.full_path,
             'evidence': s.metadata_dir / 'intermediate' / 'A_full_2.yaml'}[target]
    if not point.exists():
        point.parent.mkdir(parents=True, exist_ok=True)
        point.write_bytes(b'preserved neutral artifact')
    control = run_lock._path_for('neutral/batch', lock_dir=tmp_path / 'locks')
    alias(point, control, kind)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='conflicting output ownership'):
        ownership.require_disjoint_selected_outputs([s], control_paths=(control,))
    assert snapshot(tmp_path) == before


def test_separate_batch_control_and_exact_repeated_enumeration_pass(tmp_path, no_effects):
    from data_sheets_schema import run_lock
    a, b = spec(tmp_path, 'A'), spec(tmp_path, 'AB')
    install(a); install(b)
    control = run_lock._path_for('neutral/batch', lock_dir=tmp_path / 'locks')
    before = snapshot(tmp_path)
    ownership.require_disjoint_selected_outputs([a, b], control_paths=(control, control))
    assert snapshot(tmp_path) == before


def test_different_control_leaves_sharing_inode_refuse(tmp_path, no_effects):
    from data_sheets_schema import run_lock
    first = run_lock._path_for('one', lock_dir=tmp_path / 'locks')
    second = run_lock._path_for('two', lock_dir=tmp_path / 'locks')
    first.parent.mkdir()
    first.write_bytes(b'neutral control')
    os.link(first, second)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='conflicting output ownership'):
        ownership.require_disjoint_selected_outputs([spec(tmp_path)], control_paths=(first, second))
    assert snapshot(tmp_path) == before


@pytest.fixture
def private_inventory(tmp_path, monkeypatch):
    """Use the real resource resolver; never link or write the source resource."""
    from data_sheets_schema import resources, schema_digest
    original = resources.resource_path(schema_digest.INVENTORY_LEDGER).resolve()
    raw = original.read_bytes()
    private = tmp_path / schema_digest.INVENTORY_LEDGER
    private.parent.mkdir(parents=True)
    private.write_bytes(raw)
    monkeypatch.chdir(tmp_path)
    assert resources.resource_path(schema_digest.INVENTORY_LEDGER).resolve() == private
    yield private
    assert original.read_bytes() == raw


def test_actual_shared_inventory_is_not_a_per_run_conflict(tmp_path, no_effects, private_inventory):
    a, b = spec(tmp_path, 'A'), spec(tmp_path, 'AB')
    install(a); install(b)
    before = snapshot(tmp_path)
    ownership.require_disjoint_selected_outputs([a, b])
    check_one(a, 'resume'); check_one(b, 'resume')
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('mode', ['batch', 'resume'])
@pytest.mark.parametrize('target', ['full', 'sidecar', 'evidence'])
@pytest.mark.parametrize('kind', ['hardlink', 'symlink'])
def test_resource_inventory_cannot_alias_run_roles(tmp_path, no_effects, private_inventory,
                                                  mode, target, kind):
    s = spec(tmp_path)
    install(s, ('progress',))
    point = {'full': s.full_path, 'sidecar': ledger.output_locks((s.full_path,))[0][1],
             'evidence': s.metadata_dir / 'intermediate' / 'A_full_2.yaml'}[target]
    alias(private_inventory, point, kind)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='conflicting output ownership'):
        check_one(s, mode)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('kind', ['hardlink', 'symlink'])
def test_resource_inventory_cannot_alias_batch_control(tmp_path, no_effects, private_inventory, kind):
    from data_sheets_schema import run_lock
    control = run_lock._path_for('neutral/batch', lock_dir=tmp_path / 'locks')
    alias(private_inventory, control, kind)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='conflicting output ownership'):
        ownership.require_disjoint_selected_outputs([spec(tmp_path)], control_paths=(control,))
    assert snapshot(tmp_path) == before


def test_legacy_only_does_not_resolve_inventory_or_controls(tmp_path, monkeypatch, no_effects):
    from data_sheets_schema import resources
    def forbidden(*args, **kwargs):
        raise AssertionError('legacy admission must not impose new resource contracts')
    monkeypatch.setattr(resources, 'resource_path', forbidden)
    legacy = spec(tmp_path, shared=0)
    ownership.require_disjoint_selected_outputs([legacy], control_paths=(object(),))
    ownership.require_selected_resume_owner(legacy, resume=False)
