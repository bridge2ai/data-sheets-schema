"""Draft single native generation canary, requiring a separately reviewed overlay."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from budgeted_cborg import BudgetStop, open_ledger, attempt_identity, write_new
from budgeted_cborg import cborg_client, provider_context_headers, provider_context_evidence
from native_proxy import NativeProxy
from prepare_registration import spec_for
from run_api_canary import verify, verify_history, sha, check_canary_receipts


def now():
    return datetime.now(timezone.utc).isoformat()


def verified_executable(overlay):
    path = Path(overlay['claude_executable'])
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise BudgetStop('native executable must be an absolute resolved path')
    if overlay['pinned_files'].get(str(path)) != sha(path):
        raise BudgetStop('native executable bytes differ from the launch pin')
    return str(path)


def stop_explanation(exc, ledger_path, billing_attempt, proxy_failure):
    """Why a native attempt stopped, from the strongest source available.

    The v10q CHORUS attempt stopped on a ledger refusal, but the receipt
    recorded only `error_type: PermissionError` with no reason: the proxy
    keeps the class name of a non-BudgetStop exception and the controller
    copied a reason only from a BudgetStop it raised itself (#1914). The
    ledger's own stop entry for this attempt is the authoritative cause
    whenever it exists; the proxy's recorded failure and the exception's
    BudgetStop message follow.
    """
    out = {}
    try:
        state = json.loads(Path(ledger_path).read_bytes()) if Path(ledger_path).exists() else {}
    except Exception:
        state = {}
    entry = (state.get('stopped_attempts') or {}).get(billing_attempt)
    if isinstance(entry, dict) and entry.get('reason'):
        out['reason'] = entry['reason']; out['reason_source'] = 'ledger'; out['ledger_stop'] = entry
    elif isinstance(exc, BudgetStop):
        out['reason'] = str(exc); out['reason_source'] = 'controller'
    elif isinstance(proxy_failure, str) and proxy_failure:
        out['reason'] = proxy_failure; out['reason_source'] = 'proxy'
    if proxy_failure is not None:
        out['proxy_failure'] = proxy_failure
    return out


def native_evidence_check(spec):
    """Recheck the exact originals using the generation's selected protocol."""
    from data_sheets_schema.evidence_assertions import check_files, protocol_for_renderer
    evidence_dir = spec.metadata_dir / 'evidence'
    return check_files(audit=evidence_dir/'audit.json', bundle=spec.bundle,
        manifest=spec.chunk_manifest, report=spec.report_path,
        artifacts={'original_full':evidence_dir/'original_full.yaml',
                   'original_core':evidence_dir/'original_core.yaml',
                   'final_full':spec.full_path,'final_core':spec.core_path},
        protocol_version=protocol_for_renderer(spec.render_version))


def terminate_group(process):
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    # Also remove descendants if the parent exited before them.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=2)


def execute_child(argv, *, proxy, instruction, attempt, cwd, env, deadline_seconds, verify_launch):
    process = None
    deadline = time.monotonic() + deadline_seconds
    try:
        with Path(instruction).open('r') as incoming, (attempt/'transcript.jsonl').open('x') as out, (attempt/'stderr.txt').open('x') as err:
            verify_launch()  # Bind the executable immediately before Popen.
            process = subprocess.Popen(argv, stdin=incoming, text=True, cwd=cwd,
                env=env, stdout=out, stderr=err, start_new_session=True)
            while process.poll() is None:
                if proxy.failed.is_set():
                    raise BudgetStop(proxy.failure)
                if time.monotonic() >= deadline:
                    raise BudgetStop('native attempt deadline elapsed; retain all incomplete charge reservations')
                time.sleep(0.05)
        if proxy.failed.is_set():
            raise BudgetStop(proxy.failure)
        return process.returncode
    finally:
        # This runs INSIDE proxy.running(), before server/pool cleanup.
        proxy.close_admission()
        terminate_group(process)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overlay',type=Path,required=True)
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--job',required=True)
    args=parser.parse_args()
    overlay=json.loads(args.overlay.read_bytes())
    base_path=Path(overlay['registration']);base=json.loads(base_path.read_bytes())
    here=base_path.parent;registration_sha=sha(base_path);overlay_sha=sha(args.overlay)
    review=json.loads(args.review.read_bytes())
    if review.get('verdict')!='approve' or review.get('ci_conclusion')!='success' or review.get('overlay_sha256')!=overlay_sha or args.job not in review.get('allowed_jobs',[]):
        raise BudgetStop('this native execution overlay and job need independent approval and CI')
    if overlay.get('registration_sha256')!=registration_sha:
        raise BudgetStop('native overlay refers to another source/instrument registration')
    if args.job not in overlay['allowed_jobs']:
        raise BudgetStop('native job is outside this overlay')
    def verify_all():
        verify(base,base_path,registration_sha)
        if sha(args.overlay)!=overlay_sha:
            raise BudgetStop('native execution overlay changed')
        if any(not Path(p).is_file() or sha(p)!=h for p,h in overlay['pinned_files'].items()):
            raise BudgetStop('native controller or runtime pin changed')
    verify_all();verify_history(base)
    job=next(j for j in base['generation']['jobs'] if j['id']==args.job)
    if not job['canary'] or job['execution_arm']!='agentic':
        raise BudgetStop('this controller only launches registered agentic generation canaries')
    order=base['generation']['canary_order']
    for previous in order[:order.index(args.job)]:
        accepted=json.loads((here/'acceptances'/f'{previous}.json').read_bytes())
        if accepted.get('verdict')!='accept' or accepted.get('registration_sha256')!=registration_sha or not accepted.get('artifacts') or any(not Path(p).is_file() or sha(p)!=h for p,h in accepted['artifacts'].items()):
            raise BudgetStop('earlier canary lacks acceptance of unchanged original artifacts')
    if any(Path(p).exists() for p in job['output_directories']):
        raise BudgetStop('native canary output already exists; never overwrite or resume')
    spec=spec_for(job)
    if spec.render_spec()!=job['render_spec'] or spec.input_identity()!=job['input_identity']:
        raise BudgetStop('native generation instruction or input identity changed')
    if spec.render_version >= 9 and overlay['per_job_environment'][job['id']].get('D4D_LAUNCH_INSTRUCTION') != job['instruction']:
        raise BudgetStop('native provenance must read the exact registered launch instruction')
    key=os.environ.get('CBORG_API_KEY')
    if not key: raise BudgetStop('CBORG_API_KEY is required')
    executable=verified_executable(overlay)
    if subprocess.check_output([executable,'--version'],text=True).strip()!=base['claude_version']:
        raise BudgetStop('native runtime version changed')
    attempt=here/'attempts'/args.job;attempt.mkdir(parents=True,exist_ok=False)
    config=attempt/'cli_config';config.mkdir(mode=0o700)
    ledger=open_ledger(base,registration_sha)
    billing_attempt=attempt_identity(registration_sha,job['id'])
    proxy=NativeProxy(sdk=cborg_client(base,key,max_retries=0),
          ledger=ledger,attempt=billing_attempt,evidence=attempt/'requests',model=base['model']['model'],
          prices=base['budget']['prices_per_token'],verify=verify_all,provider_key=key,base_url=base['provider_base_url'],
          request_headers=provider_context_headers(base))
    # Explicitly whitelist non-credential environment fields. The child gets
    # only the local transport token; provider credentials stay in the parent.
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','SHELL','TMPDIR','LANG','LC_ALL','TERM'}}
    env.update(overlay['environment'])
    env.update(overlay['per_job_environment'][job['id']])
    env.update(CLAUDE_CONFIG_DIR=str(config),ANTHROPIC_API_KEY=proxy.token,
               PYTHONPATH=str(Path(base['repository'])/'src'),VIRTUAL_ENV=sys.prefix)
    argv=[executable,*overlay['cli_flags'],'--model',base['model']['model'],'--name',job['id'],
          '--max-budget-usd',str(ledger.limit_for_attempt(billing_attempt)),
          '--allowedTools',*overlay['allowed_tools'],'--system-prompt',Path(overlay['system_prompt']).read_text()]
    receipt={'job':job['id'],'registration_sha256':registration_sha,'overlay_sha256':overlay_sha,
             'provider_context':provider_context_evidence(base),
             'review_sha256':sha(args.review),'started_at':now(),'status':'incomplete',
             'launch_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
             'provider':base['provider_base_url'],'model':base['model']['model'],
             'instruction_sha256':sha(job['instruction']),'native_system_sha256':sha(overlay['system_prompt'])}
    write_new(attempt/'started.json',receipt)
    try:
        with proxy.running() as url:
            env['ANTHROPIC_BASE_URL']=url
            receipt['exit_code']=execute_child(argv,proxy=proxy,instruction=job['instruction'],attempt=attempt,
                cwd=base['repository'],env=env,deadline_seconds=base['generation']['agentic_attempt_deadline_seconds'],
                verify_launch=lambda: verified_executable(overlay))
        if proxy.failed.is_set() or proxy.unfinished_handlers:
            raise BudgetStop(proxy.failure or 'native handlers did not finish before evidence freeze')
        events=[json.loads(line) for line in (attempt/'transcript.jsonl').read_text().splitlines() if line.strip()]
        initializers=[e for e in events if e.get('type')=='system' and e.get('subtype')=='init']
        finals=[e for e in events if e.get('type')=='result']
        if len(initializers)!=1 or len(finals)!=1:
            raise BudgetStop('native runtime initialization or terminal result is missing or ambiguous')
        init,terminal=initializers[0],finals[0]
        if init.get('model')!=base['model']['model'] or init.get('apiKeySource')!='ANTHROPIC_API_KEY' or init.get('claude_code_version')!=base['claude_version'].split()[0] or set(init.get('tools',[]))!={'Read','Write','Bash'}:
            raise BudgetStop('native runtime initialization differs from registration')
        if receipt['exit_code'] or terminal.get('is_error') or terminal.get('permission_denials') or terminal.get('terminal_reason')!='completed' or terminal.get('stop_reason')!='end_turn':
            raise BudgetStop('native attempt failed, stopped, or had a tool permission denial')
        if set(terminal.get('modelUsage',{}))!={base['model']['model']}:
            raise BudgetStop('native terminal model accounting differs from registration')
        observed=terminal['modelUsage'][base['model']['model']]
        expected_limits=overlay['native_limits_observed_offline']
        if observed.get('contextWindow')!=expected_limits['context_window'] or observed.get('maxOutputTokens')!=expected_limits['max_output_tokens']:
            raise BudgetStop('native runtime limits differ from the registered observation')
        state=json.loads(ledger.path.read_bytes())
        rows=[r for r in state['requests'] if r['attempt']==billing_attempt]
        if not rows or any(r['status']!='settled' for r in rows):
            raise BudgetStop('native attempt has missing or unresolved request accounting')
        if not all(Path(p).is_file() for p in job['outputs'].values()):
            raise BudgetStop('native generation did not produce every registered artifact')
        from data_sheets_schema import api_runner, agentic_observed
        problems=api_runner.validate_outputs(spec)
        pair=api_runner.pair_consistency(spec)
        receipt_check=check_canary_receipts(spec,job['input_identity'])
        receipt['receipt_acceptance']=receipt_check
        if not receipt_check['passed']:
            problems=list(problems)+['coverage receipt acceptance failed']
        if spec.render_version >= 9:
            evidence = native_evidence_check(spec)
            receipt['evidence_assertions'] = evidence
            if not evidence['checked'] or evidence['findings']:
                problems = list(problems) + ['explicit evidence assertions failed']
        receipt.update(validation_problems=problems,pair_consistency=pair,
                       native_observed=agentic_observed.observe([attempt/'transcript.jsonl'],Path(job['bundle'])),
                       cli_reported_cost_usd=terminal.get('total_cost_usd'),cli_model_usage=terminal.get('modelUsage'),
                       status='validation_failed' if problems or not pair or not pair.get('ran') or not pair.get('consistent') else 'completed_pending_independent_review')
        verify_all();verify_history(base)
    except Exception as exc:
        receipt.update(status='stopped',error_type=type(exc).__name__,
                       **stop_explanation(exc, ledger.path, billing_attempt, getattr(proxy, 'failure', None)))
        # The traceback names controller code paths only; provider exception
        # strings are never copied into the receipt.
        write_new(attempt/'controller_traceback.txt', {'error_type':type(exc).__name__,'traceback':traceback.format_exc()})
    finally:
        state=json.loads(ledger.path.read_bytes()) if ledger.path.exists() else {'requests':[]}
        admitted=[row for row in state['requests'] if row['attempt']==billing_attempt]
        receipt.update(finished_at=now(),model_requests_admitted=len(admitted),
            unfinished_handlers_at_freeze=proxy.unfinished_handlers,
            artifacts={str(p):sha(p) for folder in job['output_directories'] for p in sorted(Path(folder).rglob('*')) if p.is_file()})
        write_new(attempt/'result.json',receipt)
        print(json.dumps({k:v for k,v in receipt.items() if k not in {'artifacts','validation_problems','pair_consistency','native_observed','cli_model_usage'}},indent=2))
    return 0 if receipt['status']=='completed_pending_independent_review' else 1


if __name__=='__main__':
    raise SystemExit(main())
