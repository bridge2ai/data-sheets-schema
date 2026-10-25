"""Real durable publication from declared synthetic captured stage contexts.

These tests establish write/CAS behavior, not native observation or admission.
The public capture boundary validates that independent requirement.
"""
from dataclasses import replace
from pathlib import Path
import shlex

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_publication as pub
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema.native_shared_evidence import read_regular
from tests.test_native_shared_stages import case, artifact, append, supplied


@pytest.fixture
def private_case(case, tmp_path):
    selection, execution, phase1, _ = case
    root = str(tmp_path.resolve() / 'stage')
    doc = selection.document(); doc['stage_root'] = root
    selection = replace(selection, registration=artifact('selection', selection.registration.pin.path, c.canonical(doc)),
                        roles=c.role_paths(doc['registration_path'], root))
    def move(item):
        return artifact(item.pin.role, selection.role(item.pin.role), item.raw)
    def observation(item, number):
        return artifact('observation', selection.role('observations_root')+f'/{number:06d}.json', item.raw)
    execution = replace(execution, selection_sha256=selection.registration.pin.sha256,
        execution=move(execution.execution), started=move(execution.started),
        binding_artifact=move(execution.binding_artifact), init_observation=observation(execution.init_observation, 0))
    phase1 = replace(phase1, full=move(phase1.full), original_receipt=move(phase1.original_receipt),
        seal=move(phase1.seal), full_seal_observation=observation(phase1.full_seal_observation, 1))
    journal = artifact('journal', selection.role('journal'), stage.journal_bytes(
        selection_sha256=selection.registration.pin.sha256, execution_sha256=execution.execution.pin.sha256,
        attempt_id=execution.attempt_id, records=()))
    history = c.RawHistory(journal=journal, records=(), artifacts=(), observations=())
    records, journal = stage.append_records(selection, execution, history, (
        ('genesis', c.canonical({'execution': c.pin_dict(execution.execution.pin), 'started': c.pin_dict(execution.started.pin)})),
        ('session_bound', c.canonical({'binding': c.pin_dict(execution.binding_artifact.pin), 'init_observation': c.pin_dict(execution.init_observation.pin)})),
        ('phase1_sealed', c.canonical({'seal': c.pin_dict(phase1.seal.pin), 'full': c.pin_dict(phase1.full.pin),
            'original_receipt': c.pin_dict(phase1.original_receipt.pin), 'observation': c.pin_dict(phase1.full_seal_observation.pin)}))))
    history = append(history, records, journal)
    for item in (execution.execution, execution.started, execution.binding_artifact, execution.init_observation,
                 phase1.full, phase1.original_receipt, phase1.seal, phase1.full_seal_observation,
                 *history.records, history.journal):
        path=Path(item.pin.path);path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(item.raw)
    return selection, execution, phase1, history


def invocation(case):
    selection, execution, phase1, history = case
    raw = b'{"fixture":"synthetic declared event, not a native observation"}\n'
    def prefix(stream):
        return c.EvidencePrefix(stream=stream,path='/neutral/'+stream,raw=raw,bytes=len(raw),sha256=c.sha(raw),lines=1)
    def ref(stream):
        return c.EventRef(stream=stream,line=1,block=None,raw_line_sha256=c.sha(raw),value_sha256=c.sha(c.canonical(c.strict_json(raw))))
    argv=(execution.registered_python,'-m','data_sheets_schema.native_shared_stage','advance','--registration',selection.registration.pin.path)
    call=c.ObservedCall(call=ref('transcript'),callback=ref('transcript'),admission=ref('control'),
        input_json=c.canonical({'command':shlex.join(argv)}),session_id=execution.session_id,
        tool_name='Bash',tool_use_id='synthetic-advance')
    advance=c.CurrentAdvance(admission_observation=artifact('observation',selection.role('observations_root')+'/000002.json',b'{}'),
        argv=argv,call=call,command=shlex.join(argv),control_prefix=prefix('control'),transcript_prefix=prefix('transcript'),
        predecessor_history_sha256=history.journal.pin.sha256,working_directory=execution.working_directory)
    return c.StageInvocationCapture(selection=selection,execution=execution,phase1=phase1,history=history,current_advance=advance)


def test_actual_pure_stage_proposal_publishes_once_and_journal_last(private_case):
    selected=invocation(private_case);proposal=stage.prepare_next(*private_case)
    assert proposal.state=='request_ready'
    old=Path(selected.history.journal.pin.path).read_bytes()
    result, observed=pub.publish_derived(selected,proposal)
    assert result['advance_tool_use_id']=='synthetic-advance'
    assert result['state']=='awaiting_response'
    assert observed[-1].captured.pin.role=='journal'
    assert result['before_history_sha256']==c.sha(old)
    assert Path(selected.history.journal.pin.path).read_bytes()==observed[-1].captured.raw
    for publication, actual in zip(proposal.publications,observed):
        assert publication.artifact.raw==actual.captured.raw
        assert publication.artifact.pin==actual.captured.pin
    before={item.captured.pin.path:Path(item.captured.pin.path).read_bytes() for item in observed}
    with pytest.raises(ValueError,match='already exists|differs before'):
        pub.publish_derived(selected,proposal)
    assert all(Path(path).read_bytes()==raw for path,raw in before.items())


def test_late_preexisting_output_refuses_before_first_write(private_case,monkeypatch):
    selected=invocation(private_case);proposal=stage.prepare_next(*private_case)
    creates=[item for item in proposal.publications if item.action=='create_once']
    assert len(creates)>1
    last=Path(creates[-1].artifact.pin.path);last.parent.mkdir(parents=True,exist_ok=True);last.write_bytes(b'existing evidence')
    def blocked(*args,**kwargs):raise AssertionError('preflight allowed a writer')
    monkeypatch.setattr(pub,'durable_new',blocked);monkeypatch.setattr(pub,'_replace_journal',blocked)
    with pytest.raises(ValueError,match='already exists'):
        pub.publish_derived(selected,proposal)
    assert last.read_bytes()==b'existing evidence'
    assert not Path(creates[0].artifact.pin.path).exists()


@pytest.mark.parametrize('field',['current_advance','proposal'])
def test_foreign_current_or_proposal_refuses_before_writer(private_case,monkeypatch,field):
    selected=invocation(private_case);proposal=stage.prepare_next(*private_case)
    if field=='current_advance':
        selected=replace(selected,current_advance=replace(selected.current_advance,predecessor_history_sha256='f'*64))
    else:
        proposal=replace(proposal,history_sha256='f'*64)
    monkeypatch.setattr(pub,'_physical_destination',lambda *a:pytest.fail('writer preflight before pure authority'))
    with pytest.raises(ValueError,match='differs'):
        pub.publish_derived(selected,proposal)


def test_cas_detects_drift_during_persistence_and_retains_partial(tmp_path,monkeypatch):
    root=tmp_path.resolve();path=root/'journal.json';path.write_bytes(b'old')
    before=read_regular(str(path),'journal',max_bytes=100).captured
    after=c.ProposedArtifact(c.ArtifactPin('journal',str(path),3,c.sha(b'new')),b'new')
    real_fsync=pub.os.fsync
    def drift(fd):
        real_fsync(fd);path.write_bytes(b'external drift')
    monkeypatch.setattr(pub.os,'fsync',drift)
    with pytest.raises(ValueError,match='changed while'):
        pub._replace_journal(path,before,after)
    assert path.read_bytes()==b'external drift'
    partials=list(root.glob('journal.partial-*'))
    assert len(partials)==1 and partials[0].read_bytes()==b'new'


def test_post_replace_fsync_failure_preserves_published_bytes_without_success(tmp_path,monkeypatch):
    root=tmp_path.resolve();path=root/'journal.json';path.write_bytes(b'old')
    before=read_regular(str(path),'journal',max_bytes=100).captured
    after=c.ProposedArtifact(c.ArtifactPin('journal',str(path),3,c.sha(b'new')),b'new')
    error=OSError('synthetic directory durability fault')
    monkeypatch.setattr(pub,'_sync_directory',lambda *a:(_ for _ in ()).throw(error))
    with pytest.raises(OSError) as raised:pub._replace_journal(path,before,after)
    assert raised.value is error and path.read_bytes()==b'new'


def test_symlink_destination_parent_refused_without_external_write(private_case,monkeypatch,tmp_path):
    selected=invocation(private_case);proposal=stage.prepare_next(*private_case)
    directory=Path(selected.selection.role('requests_root'))
    external=tmp_path/'external';external.mkdir();directory.symlink_to(external,target_is_directory=True)
    monkeypatch.setattr(pub,'durable_new',lambda *a:pytest.fail('aliased output writer called'))
    with pytest.raises(ValueError,match='exact regular stage root'):
        pub.publish_derived(selected,proposal)
    assert list(external.iterdir())==[]
