"""Native Phase 4 with exact helpers, bounded closing repair and shared ownership."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shlex
import sys
import threading
import time
from types import SimpleNamespace

BASE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'native_controls'))
from audit_controls import native as runtime
from budgeted_cborg import BudgetStop, attempt_identity, now, write_new
from continuation_sequence import owned_sequence
from native_command_policy import _literal_rule, _simple_command
from native_control import CONTRACT
from native_file_policy import FileAccess
from .registration import sha, strict_json


def classify_command(command, python, programs, command_policy=None):
    tokens,problem=_simple_command(command) if isinstance(command,str) else (None,'missing command')
    if tokens is None:
        return ('unclassifiable' if not isinstance(command,str) else 'not_prescribed'),problem
    if tokens and tokens[0]==python and tokens in (command_policy or {}).get('helper_argv',[]):
        return 'prescribed','exact registered finalization helper'
    return 'not_prescribed','outside registered finalization helper commands'


def build_policy(manifest, registration_path):
    job=manifest['job'];prefix=[manifest['python'],'-m','finalization_controls.contract','--registration',str(registration_path)]
    helpers=[[*prefix,'--operation','derive'],*[[*prefix,'--operation','check','--round',str(i)] for i in range(2)]]
    if [job['derive_argv'],*job['check_argv']]!=helpers:
        raise BudgetStop('finalization helper arguments differ from registration')
    reads=sorted(set([*job['readable_inputs'],job['instruction'],job['system_prompt']]))
    if any(manifest['pinned_files'].get(name)!=sha(name) for name in reads):
        raise BudgetStop('finalization native read is unpinned or changed')
    recovery={}
    if 'context_recovery' in manifest:
        from native_context_control import paths as recovery_paths
        recovery={'bounded_reads':recovery_paths(manifest)}
    return {'version':1,'pretool_control':CONTRACT,'python':manifest['python'],'programs':[],
        'manifest_paths':[],'helper_argv':helpers,
        'allowed_tools':['Read','Write',*[_literal_rule(shlex.join(argv)) for argv in helpers]],
        'readonly_lookups':{'repository':manifest['repository'],'inputs':reads,
            'output_directories':[job['output_dir']],**recovery}}


class FinalizationHistory:
    """Live and retrospective Phase 4 gate; artifacts alone never prove order."""
    def __init__(self,manifest,registration_sha256,policy,*,replay=False):
        self.replay=replay
        self.texts={}
        self.manifest,self.job,self.registration_sha256=manifest,manifest['job'],registration_sha256
        self.policy,self.files=policy,FileAccess(policy)
        self.attempt=Path(self.job['attempt_dir'])
        self.targets={role:Path(self.job[role+'_path']) for role in ('full','core','report')}
        self.lock=threading.Condition(threading.RLock())
        self.calls,self.results,self.pending={},set(),set()
        self.writes,self.derivations,self.checks={},[],[]
        self.derivation,self.current_check=None,None
        self.helper=None;self.problem=None;self.line=0
        self.context=None;self.context_reads=set();self.read_calls={}
        self.recovery_reads=[]

    def _artifacts(self,report,*,complete=False,force_current=False):
        roles=('full','core','report') if complete else ('full','core')
        if self.replay and not force_current:
            expected={str(self.targets[role]):self.writes[role]['sha256'] for role in roles if role!='core'}
            expected[str(self.targets['core'])]=(self.derivation['artifacts'][str(self.targets['core'])]
                if complete else report.get('artifacts',{}).get(str(self.targets['core'])))
        else:
            expected={str(self.targets[role]):sha(self.targets[role]) for role in roles}
        if report.get('artifacts')!=expected:
            raise BudgetStop('finalization helper artifacts differ from current exact files')
        return expected

    def _receipt(self,operation,report):
        if (not isinstance(report,dict) or report.get('operation')!=operation or
                report.get('registration_sha256')!=self.registration_sha256 or report.get('job_id')!=self.job['id']):
            raise BudgetStop('finalization helper receipt has wrong identity')
        if operation=='derive':
            index=report.get('index')
            if type(index) is not int or index!=len(self.derivations)+1:
                raise BudgetStop('finalization derivation receipt sequence differs')
            path=self.attempt/'derivations'/f'{index:06d}.json'
        else:
            index=report.get('round')
            if type(index) is not int or index!=len(self.checks):
                raise BudgetStop('finalization closing check sequence differs')
            path=self.attempt/f'check-{index}.json'
        if strict_json(path.read_text())!=report:
            raise BudgetStop('finalization helper stdout differs from its retained receipt')
        if report.get('terminal') is not False:
            raise BudgetStop('finalization helper recorded a terminal failure')
        if report.get('checked') is not True:
            raise BudgetStop('finalization helper could not check its record')
        if operation=='derive' and report.get('passed') is False:
            if report.get('artifacts',{}).get(str(self.targets['full']))!=self.writes['full']['sha256']:
                raise BudgetStop('failed derivation differs from the observed full Write')
            return report
        self._artifacts(report,complete=operation=='check')
        inventory=self.attempt/'final_inventory.json'
        if report.get('inventory_path')!=str(inventory) or (not self.replay and report.get('inventory_sha256')!=sha(inventory)):
            raise BudgetStop('finalization inventory is absent, stale or changed')
        return report

    def _report_context(self,report):
        context=report.get('report_context')
        if not isinstance(context,dict):raise BudgetStop('derivation lacks bounded report-context delivery')
        path=Path(self.job['output_dir'])/'report_contexts'/f"{report['index']:06d}.jsonl"
        if context.get('path')!=str(path) or path.is_symlink() or not path.is_file() or path.stat().st_nlink!=1:
            raise BudgetStop('report context is outside its exact helper destination')
        raw=path.read_bytes();lines=raw.decode().split('\n')
        if (context.get('sha256')!=hashlib.sha256(raw).hexdigest() or
                type(context.get('bytes')) is not int or context['bytes']!=len(raw) or
                type(context.get('line_count')) is not int or context['line_count']!=len(lines)):
            raise BudgetStop('report-context identity differs')
        texts=[]
        for index,line in enumerate(lines,1):
            value=strict_json(line)
            if (not isinstance(value,dict) or set(value)!={'index','text'} or
                    type(value['index']) is not int or value['index']!=index or
                    not isinstance(value['text'],str) or len(line.encode())>1000):
                raise BudgetStop('report-context fragment is malformed or oversized')
            texts.append(value['text'])
        if context.get('text_sha256')!=hashlib.sha256(''.join(texts).encode()).hexdigest():
            raise BudgetStop('report-context reconstruction differs')
        ranges=[{'offset':i+1,'limit':min(12,len(lines)-i)} for i in range(0,len(lines),12)]
        if context.get('read_ranges')!=ranges:
            raise BudgetStop('report-context read ranges differ from complete bounded coverage')
        return context

    def _context_read(self,call,block,event):
        context,selected=self.read_calls[call['id']]
        raw=Path(context['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=context['sha256']:
            raise BudgetStop('report context changed while being read')
        offset,limit=selected
        lines=raw.decode().split('\n')[offset-1:offset-1+limit]
        content='\n'.join(lines)
        numbered='\n'.join(str(i)+'\t'+line for i,line in enumerate(lines,offset))
        metadata=event.get('tool_use_result');file=metadata.get('file') if isinstance(metadata,dict) else None
        if ((block.get('is_error') is not None and block.get('is_error') is not False) or not isinstance(file,dict) or
                metadata.get('type')!='text' or file.get('filePath')!=context['path'] or
                type(file.get('startLine')) is not int or file['startLine']!=offset or
                type(file.get('numLines')) is not int or file['numLines']!=limit or
                type(file.get('totalLines')) is not int or file['totalLines']!=context['line_count'] or
                file.get('content')!=content or block.get('content')!=numbered):
            raise BudgetStop('report-context Read is missing, truncated or lacks exact typed delivery')
        self.context_reads.add(selected)

    def _current_derivation(self):
        if self.derivation is None or self.derivation.get('passed') is not True:
            raise BudgetStop('finalization report requires successful current derivation')
        self._artifacts(self.derivation)
        current=self.derivation if self.replay else strict_json((self.attempt/'current_derivation.json').read_text())
        if current!=self.derivation:
            raise BudgetStop('finalization current derivation differs from observed helper result')

    def verify_admission(self):
        with self.lock:
            deadline=time.monotonic()+runtime.VALIDATOR_RESULT_WAIT_SECONDS
            while True:
                if self.problem:raise BudgetStop(self.problem)
                if (self.attempt/'failure.json').exists():raise BudgetStop('finalization checker failure is terminal')
                if self.helper is None:
                    if self.current_check and self.current_check.get('passed') is True:
                        self._artifacts(self.current_check,complete=True,force_current=True)
                    return
                remaining=deadline-time.monotonic()
                if remaining<=0:raise BudgetStop('finalization helper lacks observed complete typed result; no further request admitted')
                self.lock.wait(min(remaining,.05))

    def observe(self,event):
        with self.lock:
            try:self._observe(event)
            except BaseException as error:
                self.problem=str(error) if isinstance(error,BudgetStop) else 'finalization observer failed: '+type(error).__name__
                raise
            finally:self.lock.notify_all()

    def _observe(self,event):
        self.line+=1
        if not isinstance(event,dict):raise BudgetStop('finalization transcript event must be an object')
        for block in runtime._blocks(event):
            if not isinstance(block,dict):continue
            if block.get('type')=='tool_use':
                identity,tool,payload=block.get('id'),block.get('name'),block.get('input')
                if not isinstance(identity,str) or not identity or identity in self.calls or not isinstance(payload,dict):
                    raise BudgetStop('finalization tool call identity or input is malformed')
                if self.current_check and self.current_check.get('passed') is True:
                    raise BudgetStop('finalization tools cannot continue after acceptance gates pass')
                if self.helper is not None:raise BudgetStop('finalization tools cannot overlap a pending helper')
                self.calls[identity]=(self.line,block)
                if tool=='Write':
                    target=self.files.target(payload.get('file_path'))
                    role=next((r for r in ('full','report') if target==self.targets[r]),None)
                    if role is None or not isinstance(payload.get('content'),str):
                        raise BudgetStop('native finalization may write only its full record and report')
                    if self.pending:raise BudgetStop('finalization Write cannot overlap pending tools')
                    if self.checks and (len(self.checks)!=1 or self.checks[0].get('repairable') is not True):
                        raise BudgetStop('no further finalization repair is permitted')
                    if role=='report':
                        self._current_derivation()
                        required={(r['offset'],r['limit']) for r in self.context['read_ranges']} if self.context else set()
                        if not required or self.context_reads!=required:
                            raise BudgetStop('report Write requires complete observed report-context Reads')
                    else:self.derivation=None;self.context=None;self.context_reads=set();self.writes.pop('report',None)
                    self.writes.pop(role,None);self.current_check=None
                if tool=='Read' and self.context and self.files.target(payload.get('file_path'))==Path(self.context['path']):
                    selected=(payload.get('offset'),payload.get('limit'))
                    if (set(payload)!={'file_path','offset','limit'} or any(type(n) is not int for n in selected) or
                            selected not in {(r['offset'],r['limit']) for r in self.context['read_ranges']}):
                        raise BudgetStop('report-context Read must use one exact registered bounded range')
                    remaining=[(r['offset'],r['limit']) for r in self.context['read_ranges'] if (r['offset'],r['limit']) not in self.context_reads]
                    if selected not in self.context_reads and (not remaining or selected!=remaining[0] or any(key in self.pending for key in self.read_calls)):
                        raise BudgetStop('report-context ranges must be delivered in order')
                    self.read_calls[identity]=(dict(self.context),selected)
                if tool=='Bash' and classify_command(payload.get('command'),self.policy['python'],[],self.policy)[0]=='prescribed':
                    if set(payload)-{'command','description','timeout'} or ('timeout' in payload and (type(payload['timeout']) is not int or payload['timeout']<=0)):
                        raise BudgetStop('finalization helpers require exact foreground Bash calls')
                    if self.pending:raise BudgetStop('finalization helper cannot overlap pending tools')
                    tokens,_=_simple_command(payload['command'])
                    operation='derive' if tokens==self.job['derive_argv'] else 'check'
                    if 'full' not in self.writes or (not self.replay and sha(self.targets['full'])!=self.writes['full']['sha256']):
                        raise BudgetStop('finalization helper requires a completed current native full Write')
                    if operation=='check':
                        self._current_derivation()
                        if 'report' not in self.writes or (not self.replay and sha(self.targets['report'])!=self.writes['report']['sha256']):
                            raise BudgetStop('closing check requires a current native report Write')
                        if len(self.checks)>=2 or tokens!=self.job['check_argv'][len(self.checks)]:
                            raise BudgetStop('finalization closing check exceeds the single repair boundary')
                        if self.checks and self.checks[0].get('repairable') is not True:
                            raise BudgetStop('failed evidence cannot be repaired')
                    if operation=='derive':
                        self.derivation=None;self.context=None;self.context_reads=set();self.writes.pop('report',None);self.current_check=None
                    self.helper={'id':identity,'operation':operation,'call_line':self.line}
                self.pending.add(identity)
            elif block.get('type')=='tool_result':
                identity=block.get('tool_use_id')
                if identity not in self.calls or identity in self.results:raise BudgetStop('finalization result lacks a unique call')
                self.results.add(identity);self.pending.discard(identity)
                start,call=self.calls[identity]
                if 'context_recovery' in self.manifest:
                    from native_context_control import read_result
                    observed=read_result(self.manifest,self.files,call,event,block)
                    if observed is not None:
                        self.recovery_reads.append({'call_line':start,'result_line':self.line,**observed})
                if call['name']=='Write':
                    target=self.files.target(call['input'].get('file_path'))
                    if not runtime._write_success(call,block,event,target):raise BudgetStop('finalization Write lacks exact typed success')
                    role=next(r for r,p in self.targets.items() if p==target)
                    self.texts[role]=call['input']['content']
                    self.writes[role]={'sha256':hashlib.sha256(call['input']['content'].encode()).hexdigest(),
                        'call_line':start,'result_line':self.line}
                if call['name']=='Read' and identity in self.read_calls:
                    self._context_read(call,block,event)
                if self.helper and identity==self.helper['id']:
                    metadata=event.get('tool_use_result')
                    if (not isinstance(metadata,dict) or metadata.get('interrupted') is not False or
                            not isinstance(metadata.get('stdout'),str) or not isinstance(metadata.get('stderr'),str) or
                            block.get('is_error') is not False or any(k in metadata and (type(metadata[k]) is not int or metadata[k]!=0) for k in ('exitCode','exit_code'))):
                        raise BudgetStop('finalization helper failed or lacks typed successful result')
                    operation=self.helper['operation'];report=self._receipt(operation,strict_json(metadata['stdout']))
                    if operation=='derive':
                        self.derivations.append(report);self.derivation=report
                        if report.get('passed') is True:self.context=self._report_context(report);self.context_reads=set()
                    else:
                        from .contract import _repair_admitted
                        if not report.get('passed') and (len(self.checks) or not _repair_admitted(report)):
                            raise BudgetStop('finalization check failed outside permitted closing repair')
                        self.checks.append(report);self.current_check=report
                    self.helper=None
        if event.get('type')=='result':self.finish()

    def finish(self):
        if self.pending or self.helper or not self.current_check or self.current_check.get('passed') is not True:
            raise BudgetStop('finalization lacks completed current gates')
        self._current_derivation();self._artifacts(self.current_check,complete=True,force_current=True)
        return {'writes':self.writes,'derivations':self.derivations,'checks':self.checks,
                'closing_repairs':max(0,len(self.checks)-1),
                **({'context_recovery_reads':self.recovery_reads} if 'context_recovery' in self.manifest else {}),
                'report_context_reads':[{'tool_use_id':key,'path':value[0]['path'],'sha256':value[0]['sha256'],
                    'offset':value[1][0],'limit':value[1][1]} for key,value in self.read_calls.items()]}


AuditHistory=FinalizationHistory


def inspect_transcript(events,policy,manifest,registration_sha256,control_path,config_root):
    return runtime.inspect_transcript(events,policy,manifest,registration_sha256,control_path,config_root,
        history_factory=lambda *args:FinalizationHistory(*args,replay=True),command_classifier=classify_command,phase_key='phase4')


def complete(context,evidence,runtime_evidence):
    from .contract import validate_final
    validation=validate_final(context.manifest)
    if validation.get('passed') is not True:raise BudgetStop('finalization failed independent mechanical recheck')
    return {'validation':validation,'evidence':evidence,'runtime':runtime_evidence,
            'artifacts':validation['artifacts']}


def execute_job(context,*,client=None,upstream=None):
    return runtime.execute_job(context,client=client,upstream=upstream,protocol=sys.modules[__name__])


class OwnedLedger:
    """Existing transport settles real rows; every reservation rechecks owner."""
    def __init__(self,owner):self.owner=owner
    def __getattr__(self,name):return getattr(self.owner.ledger,name)
    def reserve(self,attempt,estimate,request_sha256):return self.owner.reserve(attempt,estimate,request_sha256)


def lineage(manifest,registration_sha256,artifacts,evidence):
    return {'kind':'d4d_composite_finalization_lineage','schema_version':1,
        'registration_sha256':registration_sha256,'scope':'phase4_reconciliation',
        'original_generation':manifest['budget_sequence']['origin']['registration'],
        'accepted_audit':manifest['budget_sequence']['audit_origin'],
        'final_artifacts':artifacts,'observed_phase4':evidence['phase4'],
        'source_inputs':{name:{'path':path,'sha256':manifest['pinned_files'][path]} for name,path in manifest['inputs'].items()},
        'original_generation_status':'preserved; no retroactive completion claimed',
        'phase1_phase2_performed_here':False,'phase3_performed_here':False,
        'scientific_acceptance':False,'sampling_temperature':'unknown (not observed from the native runtime)'}


def run_job(registration_path,review_path,*,adapter=None):
    from .registration import validate_registration,verify
    path,review=Path(registration_path).resolve(),Path(review_path).resolve()
    manifest=validate_registration(path);identity,review_sha=sha(path),sha(review);job=manifest['job']
    def verify_all():
        verify(manifest,path,identity)
        if sha(review)!=review_sha:raise BudgetStop('finalization launch review changed')
        value=strict_json(review.read_text())
        if (value.get('verdict')!='approve' or value.get('registration_sha256')!=identity or
                value.get('repository_commit')!=manifest['repository_commit'] or value.get('ci_conclusion')!='success' or value.get('allowed_jobs')!=[job['id']]):
            raise BudgetStop('finalization requires exact independent review and successful CI')
    verify_all();build_policy(manifest,path);runtime.verify_runtime(manifest)
    attempt=Path(job['attempt_dir'])
    # Check consumed paths before any handoff. Repeat under the canonical lock.
    if attempt.exists():raise BudgetStop('finalization attempt is already consumed')
    with owned_sequence(manifest,path,identity) as owner:
        if attempt.exists():raise BudgetStop('finalization attempt is already consumed')
        ledger=OwnedLedger(owner);billing_attempt=attempt_identity(identity,job['id'])
        def admission():verify_all();owner.verify_admission()
        admission();ledger.require_resolved(billing_attempt)
        attempt.mkdir(parents=True,exist_ok=False);Path(job['output_dir']).mkdir()
        receipt={'schema_version':1,'job_id':job['id'],'registration_sha256':identity,
            'review_sha256':review_sha,'status':'incomplete','started_at':now(),
            'scope':'phase4_reconciliation','billing_attempt':billing_attempt,
            'phase1_phase2_performed_here':False,'phase3_performed_here':False}
        write_new(attempt/'started.json',receipt)
        context=SimpleNamespace(manifest=manifest,job=job,attempt=attempt,manifest_sha256=identity,
            registration_path=path,ledger=ledger,verify=admission)
        error=result=None
        try:
            result=(adapter or execute_job)(context)
            admission();ledger.require_resolved(billing_attempt)
            if result.get('validation',{}).get('passed') is not True:
                raise BudgetStop('finalization adapter did not pass final checks')
            artifacts=dict(result['artifacts'])
            provenance=attempt/'lineage.json'
            write_new(provenance,lineage(manifest,identity,artifacts,result['evidence']))
            artifacts[str(provenance)]=sha(provenance)
            receipt.update(status='completed_pending_independent_review',artifacts=artifacts,
                validation=result['validation'],runtime=result['runtime'],evidence=result['evidence'])
        except BaseException as exc:
            error=exc;reason=getattr(exc,'native_stop_reason',str(exc) if isinstance(exc,BudgetStop) else type(exc).__name__)
            observation=getattr(exc,'native_stop',None) or {'stop_source':'finalization_orchestrator',
                'runtime':result.get('runtime',runtime.shutdown_evidence(None)) if isinstance(result,dict) else runtime.shutdown_evidence(None)}
            receipt.update(status='stopped',reason=reason,error_type=type(exc).__name__,**observation)
            ledger.stop_attempt(billing_attempt,reason)
        finally:
            rows=[r for r in strict_json(ledger.path.read_text())['requests'] if r['attempt']==billing_attempt]
            receipt.update(finished_at=now(),requests_admitted=len(rows),
                settled_cost_usd=str(sum((Decimal(r['cost_usd']) for r in rows if r['status']=='settled'),Decimal(0))),
                unresolved_requests=[r['id'] for r in rows if r['status']!='settled'])
            write_new(attempt/'result.json',receipt)
        if error:raise error
        return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration',required=True,type=Path);parser.add_argument('--review',required=True,type=Path)
    args=parser.parse_args();run_job(args.registration,args.review)


if __name__=='__main__':main()
