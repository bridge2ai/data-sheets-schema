"""Neutral reproductions of omitted attribution and operational-scope reviews."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking, evidence_assertions as evidence, source_review
from tests.test_evidence_generation_gate import run, specification
from tests.test_evidence_phase_contract import PhaseContractFake
from tests.test_download.test_api_runner import FakeResponse

CHUNKS = {
    'c001': {'source':'protocol.txt', 'text':'The project plans an independent validation set. The deployment is planned.'},
    'c002': {'source':'overview.txt', 'text':'Instructions: prepare extracts following the procedure and report progress.'},
}


def review_for(raw, artifact='original_full', *, chunks=CHUNKS):
    inv = source_review.inventory(raw, artifact)
    chunk, source = next(iter(chunks.items()))
    rows=[]
    for row in inv['values']:
        if row['record_metadata_allowed']:
            rows.append({'path':row['path'], 'metadata_reason':'Synthetic record structure.'})
        else:
            rows.append({'path':row['path'], 'claims':[{
                'text':row['text'], 'verdict':'supported', 'attributed_to':[],
                'claim_status':'fact', 'source_status':'fact',
                'evidence':[{'source':source['source'], 'chunk':chunk, 'quote':source['text']}],
                'reason':'Synthetic structural harness; this does not measure semantic accuracy.'}]})
    return {**{k:inv[k] for k in ('artifact','sha256')}, 'values':rows}


def first_claim(review):
    return next(row['claims'][0] for row in review['values'] if 'claims' in row)


@pytest.mark.parametrize('claim_status,source_status', [
    ('applied','instruction'), ('applied','capability'), ('applied','planned'),
    ('applied','in_progress'), ('fact','unstated')])
def test_declared_status_strengthening_is_rejected(claim_status, source_status):
    raw='description: Sites follow the procedure.\n'
    review=review_for(raw)
    first_claim(review).update(claim_status=claim_status, source_status=source_status)
    out=source_review.check(review,raw=raw,artifact='original_full',chunks=CHUNKS)
    assert any('status does not support' in f['detail'] for f in out['findings'])


def test_attribution_requires_evidence_in_each_credited_document():
    raw='description: The overview describes a planned independent validation set.\n'
    review=review_for(raw)
    claim=first_claim(review)
    claim.update(attributed_to=['overview.txt'], claim_status='planned',source_status='planned')
    out=source_review.check(review,raw=raw,artifact='original_full',chunks=CHUNKS)
    assert any('document attribution' in f['detail'] for f in out['findings'])
    # Merely changing the source label does not move the source quotation.
    claim['evidence'][0].update(source='overview.txt',chunk='c002')
    out=source_review.check(review,raw=raw,artifact='original_full',chunks=CHUNKS)
    assert any(f['kind']=='source_quote_not_found' for f in out['findings'])


def test_supported_plan_retains_its_document_and_status():
    raw='description: The protocol describes a planned independent validation set.\n'
    review=review_for(raw)
    first_claim(review).update(attributed_to=['protocol.txt'],claim_status='planned',source_status='planned')
    assert source_review.check(review,raw=raw,artifact='original_full',chunks=CHUNKS)['findings']==[]


def test_mixed_status_prose_requires_separate_complete_reviews():
    chunks={**CHUNKS,'c003':{'source':'methods.txt','text':'The procedure is applied.'}}
    raw='notes: The deployment is planned. The procedure is applied.\n'
    review=review_for(raw,chunks=chunks)
    plan=first_claim(review)
    plan.update(text='The deployment is planned.',attributed_to=['protocol.txt'],
                claim_status='planned',source_status='planned')
    applied={**copy.deepcopy(plan),'text':'The procedure is applied.',
             'attributed_to':['methods.txt'],'claim_status':'applied','source_status':'applied',
             'evidence':[{'source':'methods.txt','chunk':'c003','quote':'The procedure is applied.'}]}
    review['values'][0]['claims'].append(applied)
    assert source_review.check(review,raw=raw,artifact='original_full',chunks=chunks)['findings']==[]
    applied['source_status']='instruction'
    assert source_review.check(review,raw=raw,artifact='original_full',chunks=chunks)['findings']


@pytest.mark.parametrize('change',['missing','duplicate','unknown','partial','stale','final_as_original','metadata_escape'])
def test_coverage_cannot_omit_nested_repeated_values_or_reuse_another_artifact(change):
    raw=yaml.safe_dump({'notes':'A planned deployment. An applied procedure.',
                        'methods':[{'details':'An applied procedure.'}]})
    review=review_for(raw)
    if change=='missing': review['values'].pop()
    elif change=='duplicate': review['values'].append(copy.deepcopy(review['values'][0]))
    elif change=='unknown': review['values'][0]['path']='/absent'
    elif change=='partial': first_claim(review)['text']='An applied'
    elif change=='stale': review['sha256']='0'*64
    elif change=='final_as_original': review['artifact']='final_full'
    elif change=='metadata_escape': review['values'][0]={'path':review['values'][0]['path'],'metadata_reason':'Convenient exception'}
    assert source_review.check(review,raw=raw,artifact='original_full',chunks=CHUNKS)['findings']


def test_audit_revisions_need_actionable_findings_and_cannot_survive_final_review():
    raw='description: Sites follow the procedure.\n'
    review=review_for(raw)
    first_claim(review).update(verdict='revise',claim_status='applied',source_status='instruction')
    assert source_review.check(review,raw=raw,artifact='original_full',chunks=CHUNKS)['findings']
    linked=[{'review_paths':['/description']}]
    assert source_review.check(review,raw=raw,artifact='original_full',chunks=CHUNKS,audit_findings=linked)['findings']==[]
    review['artifact']='final_full'
    assert source_review.check(review,raw=raw,artifact='final_full',chunks=CHUNKS)['findings']


def test_inventory_preserves_zero_false_dates_and_pointer_escaping():
    raw='id: https://example.org/study\na/b: {"~x": [0, false, 2020-04-03, null, ""]}\nparts: [{id: "https://example.org/study#part"}]\n'
    inv=source_review.inventory(raw,'original_full')
    assert [(r['path'],r['text']) for r in inv['values']][1:4]==[
        ('/a~1b/~0x/0','0'),('/a~1b/~0x/1','false'),('/a~1b/~0x/2','2020-04-03')]
    assert inv['values'][-1]['record_metadata_allowed']
    assert not inv['values'][0]['record_metadata_allowed']
    with pytest.raises(ValueError): source_review.inventory('x: &x {self: *x}','original_full')
    with pytest.raises(ValueError): source_review.inventory('notes: one\nnotes: two\n','original_full')


@pytest.mark.parametrize('value,fragments',[(12,['1','2']),(1.5,['1.','.5']),
                                         (False,['fal','se']),(True,['tr','ue'])])
def test_nontext_scalars_cannot_be_reviewed_as_separate_fragments(value,fragments):
    raw=yaml.safe_dump({'instances':[{'counts':value}]})
    review=review_for(raw)
    assert source_review.check(review,raw=raw,artifact='original_full',chunks=CHUNKS)['findings']==[]
    claim=first_claim(review)
    review['values'][0]['claims']=[{**copy.deepcopy(claim),'text':part} for part in fragments]
    out=source_review.check(review,raw=raw,artifact='original_full',chunks=CHUNKS)
    assert any('complete scalar value' in f['detail'] for f in out['findings'])


def test_passing_declarations_do_not_claim_to_prove_semantic_labels():
    raw='description: Sites follow the procedure.\n'
    review=review_for(raw)
    # A model can misclassify prose. This check must not be described as entailment.
    first_claim(review).update(claim_status='applied',source_status='applied')
    out=source_review.check(review,raw=raw,artifact='original_full',chunks=CHUNKS)
    assert out['findings']==[] and 'require independent review' in out['scope']


class SourceReviewFake(PhaseContractFake):
    def __init__(self, mode='valid'):
        super().__init__();self.mode=mode

    def create(self, **kwargs):
        terminal=kwargs['messages'][0]['content'][-1]['text']
        response=super().create(**kwargs)
        if terminal.startswith('Phase 3.') or terminal.startswith('Phase 4c.') or terminal.startswith('Report re-check.'):
            block=next(p['text'] for p in kwargs['messages'][0]['content']
                       if p['text'].startswith(source_review.INVENTORY_HEADER))
            inv=json.loads(block[len(source_review.INVENTORY_HEADER):])
            raw=next(p['text'][len(api.CARRY_LABEL.format(name=name)):] for p in kwargs['messages'][0]['content']
                     for name in ['Completed full record','Reconciled full record']
                     if p['text'].startswith(api.CARRY_LABEL.format(name=name)))
            chunks={'c001':{'source':'protocol.txt','text':'A sample dataset is planned.'}}
            review=review_for(raw,inv['artifact'],chunks=chunks)
            assert review['sha256']==inv['sha256']
            if self.mode=='missing_audit' and terminal.startswith('Phase 3.'): review['values'].pop()
            if self.mode=='audit_status' and terminal.startswith('Phase 3.'):
                first_claim(review).update(claim_status='applied',source_status='instruction')
            if self.mode=='final_status' and not terminal.startswith('Phase 3.'):
                first_claim(review).update(claim_status='applied',source_status='planned')
            if terminal.startswith('Phase 3.'):
                return FakeResponse(json.dumps({'findings':[],'summary':'Synthetic audit.','source_review':review}))
            report=response.content[0].text
            payload=evidence.report_payload(report)
            if self.mode!='header_fix' or terminal.startswith('Report re-check.'):
                payload['claims'][0]['op']='lacks'
            payload['source_review']=review
            report=re.sub(r'```json\n[\s\S]*?\n```','```json\n'+json.dumps(payload)+'\n```',report)
            return FakeResponse(report)
        return response


@pytest.mark.parametrize('mode,calls',[('missing_audit',2),('audit_status',2),('final_status',4)])
def test_real_api_flow_stops_on_source_defects_and_cannot_spend_on_resume(tmp_path,monkeypatch,mode,calls):
    spec=replace(specification(tmp_path),render_version=12)
    fake=SourceReviewFake(mode)
    with pytest.raises(RuntimeError,match='evidence assertions failed'):run(spec,fake,monkeypatch)
    assert len(fake.calls)==calls
    before={p:p.read_bytes() for p in spec.metadata_dir.rglob('*') if p.is_file()}
    with pytest.raises(RuntimeError,match='evidence assertions failed'):run(spec,fake,monkeypatch)
    assert len(fake.calls)==calls
    assert before=={p:p.read_bytes() for p in spec.metadata_dir.rglob('*') if p.is_file()}


@pytest.mark.parametrize('mode,calls',[('valid',4),('header_fix',5)])
def test_api_success_and_fresh_report_recheck_use_same_source_protocol(tmp_path,monkeypatch,mode,calls):
    spec=replace(specification(tmp_path),render_version=12)
    fake=SourceReviewFake(mode)
    result=run(spec,fake,monkeypatch)
    assert len(fake.calls)==calls
    out=api.saved_evidence_checks(spec,yaml.safe_load(spec.provenance_path.read_bytes()))
    assert out['checked'] and out['findings']==[]
    assert out['source_review_original']['values_required']>0
    assert out['source_review_final']['values_required']>0
    assert api.assembly_digest(12)!=api.assembly_digest(11)
    planned=api.plan(spec)
    assert 'not a bound' in planned['estimate_basis']
    assert result['validation_problems']==[]


def assert_resume_refuses_unchanged(spec, fake, calls):
    from data_sheets_schema.usage_ledger import evidence_refusal
    assert len(fake.calls)==calls and evidence_refusal(spec)
    before={p:p.read_bytes() for p in spec.metadata_dir.rglob('*') if p.is_file()}
    with pytest.raises(RuntimeError,match='evidence assertions failed'):
        api.execute(spec,client=SimpleNamespace(messages=fake))
    assert len(fake.calls)==calls
    assert before=={p:p.read_bytes() for p in spec.metadata_dir.rglob('*') if p.is_file()}


class ShapeRepairFake(SourceReviewFake):
    def __init__(self, spec, mode='valid'):
        super().__init__(mode);self.spec=spec;self.repaired=False

    def create(self, **kwargs):
        terminal=kwargs['messages'][0]['content'][-1]['text']
        if terminal.startswith('Shape repair.'):
            self.calls.append(kwargs);self.repaired=True
            return FakeResponse(self.spec.full_path.read_text().replace('description: d','description: revised'))
        return super().create(**kwargs)


@pytest.mark.parametrize('rejected',[False,True])
def test_source_review_precedes_shape_repair_and_fresh_report(tmp_path,monkeypatch,rejected):
    spec=replace(specification(tmp_path),render_version=12)
    fake=ShapeRepairFake(spec,'final_status' if rejected else 'valid')
    monkeypatch.setattr(api,'_validator_lines',lambda *args:
        (['Synthetic shape finding'],None) if not fake.repaired else ([],None))
    if rejected:
        with pytest.raises(RuntimeError,match='report evidence assertions failed'):
            api.execute(spec,client=SimpleNamespace(messages=fake))
        assert not fake.repaired
        assert_resume_refuses_unchanged(spec,fake,4)
    else:
        result=api.execute(spec,client=SimpleNamespace(messages=fake))
        assert [row['phase'] for row in result['usage']]==[
            'full','audit','reconcile_full','report','repair_full','report_after_repair']
        assert fake.repaired and not result['validation_problems']
        review=api.saved_evidence_checks(spec,yaml.safe_load(spec.provenance_path.read_bytes()))
        assert review['findings']==[]
        assert review['source_review_final']['sha256']==hashlib.sha256(spec.full_path.read_bytes()).hexdigest()


@pytest.mark.parametrize('phase,kind,calls',[
    ('audit','malformed',2),('audit','empty',2),('audit','truncated',2),
    ('report','empty',4),('report','truncated',4),
    ('report_regate','empty',5),('report_regate','truncated',5),
    ('report_after_repair','empty',6),('report_after_repair','truncated',6),
])
def test_unusable_reviews_never_retry_or_resume(tmp_path,monkeypatch,phase,kind,calls):
    spec=replace(specification(tmp_path),render_version=12)
    class UnusableReviewFake(ShapeRepairFake):
        def create(self, **kwargs):
            terminal=kwargs['messages'][0]['content'][-1]['text']
            target={'audit':'Phase 3.','report':'Phase 4c.',
                    'report_regate':'Report re-check.','report_after_repair':'Phase 4c.'}[phase]
            if terminal.startswith(target) and (phase!='report_after_repair' or self.repaired):
                self.calls.append(kwargs)
                response=FakeResponse('' if kind=='empty' else '{"source_review":')
                if kind=='truncated':response.stop_reason='max_tokens'
                return response
            return super().create(**kwargs)
    fake=UnusableReviewFake(spec,'header_fix' if phase=='report_regate' else 'valid')
    monkeypatch.setattr(api,'MAX_ATTEMPTS',2)
    monkeypatch.setattr(api.time,'sleep',lambda _:None)
    monkeypatch.setattr(api,'_validator_lines',lambda *args:
        (['Synthetic shape finding'],None) if phase=='report_after_repair' and not fake.repaired else ([],None))
    with pytest.raises(RuntimeError,match='evidence assertions failed'):
        api.execute(spec,client=SimpleNamespace(messages=fake))
    assert_resume_refuses_unchanged(spec,fake,calls)
    snapshots=list((spec.metadata_dir/'intermediate').glob(f'EXAMPLE_{phase}_rejected_response_*.txt'))
    assert len(snapshots)==1
    assert snapshots[0].read_text()==('' if kind=='empty' else '{"source_review":')


@pytest.mark.parametrize('writer',['reasoning','progress','phase_snapshot'])
@pytest.mark.parametrize('mode,calls',[('empty_audit',2),('final_status',4)])
def test_rejected_response_is_latched_before_ancillary_write_failures(tmp_path,monkeypatch,writer,mode,calls):
    spec=replace(specification(tmp_path),render_version=12)
    class FailingReviewFake(SourceReviewFake):
        def create(self, **kwargs):
            if mode=='empty_audit' and kwargs['messages'][0]['content'][-1]['text'].startswith('Phase 3.'):
                self.calls.append(kwargs);return FakeResponse('')
            return super().create(**kwargs)
    fake=FailingReviewFake('final_status' if mode=='final_status' else 'valid')
    target='audit' if mode=='empty_audit' else 'report'
    reached=[]
    def fail():
        reached.append(writer)
        raise OSError('Synthetic ancillary write failure')
    if writer=='reasoning':
        original=api.reasoning.append
        def write(path,entry):
            if entry['phase']==target:fail()
            return original(path,entry)
        monkeypatch.setattr(api.reasoning,'append',write)
    elif writer=='progress':
        original=api._save_progress
        def write(spec,completed,*args,**kwargs):
            if target in completed:fail()
            return original(spec,completed,*args,**kwargs)
        monkeypatch.setattr(api,'_save_progress',write)
    else:
        original=api._snapshot
        def write(spec,name,*args,**kwargs):
            if name==f'EXAMPLE_{target}.'+('json' if target=='audit' else 'md'):fail()
            return original(spec,name,*args,**kwargs)
        monkeypatch.setattr(api,'_snapshot',write)
    with pytest.raises(RuntimeError,match='evidence assertions failed'):
        run(spec,fake,monkeypatch)
    assert reached==[]  # rejection precedes the failing write, rather than relying on it
    fake.mode='valid'
    assert_resume_refuses_unchanged(spec,fake,calls)


def test_refusal_survives_failure_to_preserve_its_response_snapshot(tmp_path,monkeypatch):
    spec=replace(specification(tmp_path),render_version=12)
    fake=SourceReviewFake('final_status')
    original=api._snapshot
    def fail(spec,name,*args,**kwargs):
        if '_rejected_response_' in name:raise OSError('Synthetic refusal snapshot failure')
        return original(spec,name,*args,**kwargs)
    monkeypatch.setattr(api,'_snapshot',fail)
    with pytest.raises(OSError,match='refusal snapshot failure'):run(spec,fake,monkeypatch)
    from data_sheets_schema.usage_ledger import evidence_refusal
    refusal=evidence_refusal(spec)
    assert refusal['reading']['response_sha256']
    assert refusal['reading']['source_review_final']['findings']
    fake.mode='valid'
    assert_resume_refuses_unchanged(spec,fake,4)


@pytest.mark.parametrize('phase,calls',[('audit',2),('report',4),
                                      ('report_regate',5),('report_after_repair',6)])
def test_interruption_between_accounting_and_review_blocks_resume_and_direct_calls(tmp_path,monkeypatch,phase,calls):
    spec=replace(specification(tmp_path),render_version=12)
    fake=ShapeRepairFake(spec,'header_fix' if phase=='report_regate' else 'valid')
    monkeypatch.setattr(api,'_validator_lines',lambda *args:
        (['Synthetic shape finding'],None) if phase=='report_after_repair' and not fake.repaired else ([],None))
    admit=api._admit_source_response
    def interrupt(spec,actual,*args,**kwargs):
        if actual==phase:raise SystemExit('Synthetic process interruption after durable usage')
        return admit(spec,actual,*args,**kwargs)
    with monkeypatch.context() as interrupted:
        interrupted.setattr(api,'_admit_source_response',interrupt)
        with pytest.raises(SystemExit,match='process interruption'):
            api.execute(spec,client=SimpleNamespace(messages=fake))
    from data_sheets_schema import usage_ledger
    rows=usage_ledger.merge_usage(spec,[])
    assert rows[-1]['phase']==phase
    assert rows[-1]['source_review_admission']['state']=='pending'
    assert rows[-1]['source_review_admission']['response_sha256']
    assert len(fake.calls)==calls
    generation=usage_ledger.generation_id(spec)
    before={p:p.read_bytes() for p in spec.metadata_dir.rglob('*') if p.is_file()}
    with pytest.raises(api.UsageLedgerError,match='source-review admission'):
        api.execute(spec,client=SimpleNamespace(messages=fake))
    with pytest.raises(api.UsageLedgerError,match='source-review admission'):
        usage_ledger.begin_call(spec,'report',2,'2026-09-15T00:00:00Z')
    assert usage_ledger.generation_id(spec)==generation and len(fake.calls)==calls
    assert before=={p:p.read_bytes() for p in spec.metadata_dir.rglob('*') if p.is_file()}


@pytest.mark.parametrize('runtime',['Claude API (direct)','Claude Code'])
def test_both_arms_share_protocol_and_native_commands_pin_version(tmp_path,runtime):
    spec=replace(specification(tmp_path,runtime),render_version=12)
    text=spec.instruction
    assert '## Evidence protocol v3' in text and 'source_review' in text
    if spec.is_agentic:
        assert '--protocol-version 3' in text
        assert '-m data_sheets_schema.source_review' in text
        assert '--artifact original_full' in text and '--artifact final_full' in text
    replay=api.RunSpec.from_render_spec(spec.render_spec(),project=spec.project,method=spec.method,label=spec.label)
    assert replay.instruction==text


@pytest.mark.parametrize('unsupported',[False,True])
def test_real_native_final_checker_and_cli_require_final_source_review(tmp_path,monkeypatch,unsupported):
    controls=Path(__file__).resolve().parents[1]/'notes/matched_cborg_2026-09-13'
    monkeypatch.syspath_prepend(str(controls));monkeypatch.syspath_prepend(str(controls/'native_controls'))
    from run_native_canary import native_evidence_check
    bundle=tmp_path/'bundle.txt'
    bundle.write_text('FILE: protocol.txt\nPATH: protocol.txt\nThe deployment is planned.\n')
    manifest=tmp_path/'chunks.yaml';manifest.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
    chunks,_=evidence.source_chunks(bundle,manifest)
    folder=tmp_path/'evidence';folder.mkdir()
    original='notes: The deployment is planned.\n'
    final='notes: The deployment is complete.\n' if unsupported else original
    audit_review=review_for(original,chunks=chunks)
    first_claim(audit_review).update(claim_status='planned',source_status='planned')
    final_review=review_for(final,'final_full',chunks=chunks)
    first_claim(final_review).update(claim_status='applied' if unsupported else 'planned',source_status='planned')
    for name in ('full','core'):
        (folder/f'original_{name}.yaml').write_text(original)
        (tmp_path/f'{name}.yaml').write_text(final)
    (folder/'audit.json').write_text(json.dumps({'findings':[],'summary':'No original defect.','source_review':audit_review}))
    report=tmp_path/'report.md'
    report.write_text('## Evidence assertions\n```json\n'+json.dumps({'claims':[],'source_review':final_review})+'\n```\n')
    spec=SimpleNamespace(metadata_dir=tmp_path,bundle=bundle,chunk_manifest=manifest,
        report_path=report,full_path=tmp_path/'full.yaml',core_path=tmp_path/'core.yaml',render_version=12)
    before={p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    out=native_evidence_check(spec)
    assert out['checked'] and bool(out['findings']) is unsupported
    assert out['source_review_original']['findings']==[]
    assert bool(out['source_review_final']['findings']) is unsupported
    cli=subprocess.run([sys.executable,'-m','data_sheets_schema.evidence_assertions','--protocol-version','3',
        '--audit',str(folder/'audit.json'),'--bundle',str(bundle),'--manifest',str(manifest),
        '--original-full',str(folder/'original_full.yaml'),'--original-core',str(folder/'original_core.yaml'),
        '--final-full',str(spec.full_path),'--final-core',str(spec.core_path),'--report',str(report)],capture_output=True,text=True)
    assert cli.returncode==int(unsupported),(cli.stdout,cli.stderr)
    assert json.loads(cli.stdout)==out
    inv=subprocess.run([sys.executable,'-m','data_sheets_schema.source_review','--record',str(spec.full_path),
                        '--artifact','final_full'],capture_output=True,text=True,check=True)
    assert json.loads(inv.stdout)==source_review.inventory(final,'final_full')
    assert before=={p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
