"""Frozen identities for Phase 4; shared accounting is activated only by run_job."""
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
from audit_controls import registration as audit_registration
from audit_controls.registration import BudgetStop, canonical_path, pinned, read_json, sha, strict_json
from audit_controls.transport import verified_context
import continuation_sequence as sequence

KIND = 'd4d_native_finalization'


def implementation_paths(manifest):
    paths = (audit_registration.implementation_paths(manifest)
            | set(Path(__file__).parent.glob('*.py')) | {Path(sequence.__file__).resolve()})
    if (manifest.get('accepted_audit') and
            'audit_output' in read_json(manifest['accepted_audit']['registration']['path'])):
        from audit_controls import output_parts
        paths.add(Path(output_parts.__file__).resolve())
    if (manifest.get('accepted_audit') and
            'audit_drafting' in read_json(manifest['accepted_audit']['registration']['path'])):
        from audit_controls import draft_output, output_parts
        paths.update({Path(draft_output.__file__).resolve(), Path(output_parts.__file__).resolve()})
    return paths


def required_paths(manifest):
    from audit_controls.transport import transport_paths
    accepted = read_json(manifest['accepted_audit']['registration']['path'])
    paths = implementation_paths(manifest) | set(transport_paths(manifest))
    if 'context_recovery' in manifest:
        from native_context_control import paths as recovery_paths
        paths.update(Path(name) for name in recovery_paths(manifest))
    paths.update(Path(name) for name in accepted['pinned_files'])
    if 'audit_output' in accepted:
        from audit_controls.output_parts import closure_paths
        result_ref = manifest['budget_sequence']['audit_origin']['result']
        if sha(result_ref['path']) != result_ref['sha256']:
            raise BudgetStop('accepted staged audit result changed before pinning')
        paths.update(closure_paths(accepted, manifest['accepted_audit']['registration']['path'], read_json(result_ref['path'])))
    if 'audit_drafting' in accepted:
        from audit_controls.draft_output import closure_paths
        result_ref = manifest['budget_sequence']['audit_origin']['result']
        if sha(result_ref['path']) != result_ref['sha256']:
            raise BudgetStop('accepted drafted audit result changed before pinning')
        paths.update(closure_paths(accepted, manifest['accepted_audit']['registration']['path'], read_json(result_ref['path'])))
    if 'audit_batches' in accepted:
        from audit_controls.batch_output import closure_paths
        result_ref = manifest['budget_sequence']['audit_origin']['result']
        if sha(result_ref['path']) != result_ref['sha256']:
            raise BudgetStop('accepted batched audit result changed before pinning')
        paths.update(closure_paths(accepted, manifest['accepted_audit']['registration']['path'], read_json(result_ref['path'])))
    paths.update(Path(name) for name in manifest['inputs'].values())
    paths.update(audit_registration.schema_semantic_paths(manifest))
    paths.update(Path(manifest['job'][name]) for name in ('instruction', 'system_prompt'))
    paths.add(Path(manifest['native_runtime']['executable']))
    paths.add(Path(manifest['python_identity']['resolved_path']))
    config = Path(manifest['python']).parent.parent / 'pyvenv.cfg'
    if config.exists():
        paths.add(config.resolve())
    pending = [manifest['budget_sequence'], manifest['accepted_audit']]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if set(value) == {'path', 'sha256'}:
                paths.add(Path(value['path']))
            else:
                pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return paths


def verify(manifest, path, expected_sha):
    if sha(path) != expected_sha or sequence.canonical(read_json(path)) != sequence.canonical(manifest):
        raise BudgetStop('finalization registration changed')
    repository = canonical_path(manifest['repository'], exists=True)
    if Path.cwd() != repository or sys.executable != manifest['python'] or sys.version != manifest['python_version']:
        raise BudgetStop('finalization requires its registered working directory and interpreter')
    if (str(Path(sys.executable).resolve()) != manifest['python_identity']['resolved_path'] or
            sys.prefix != manifest['python_identity']['prefix']):
        raise BudgetStop('finalization Python environment differs')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repository, text=True).strip() != manifest['repository_commit']:
        raise BudgetStop('finalization code commit changed')
    from data_sheets_schema import api_runner
    if Path(api_runner.__file__).resolve() != repository/'src/data_sheets_schema/api_runner.py':
        raise BudgetStop('finalization imported scientific code from another checkout')
    code = [str(value.relative_to(repository)) for value in implementation_paths(manifest)]
    for argv in (['git','ls-files','--error-unmatch','--',*code], ['git','diff','--quiet','HEAD','--',*code]):
        if subprocess.run(argv,cwd=repository,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
            raise BudgetStop('finalization implementation differs from registered committed code')
    for name in manifest['pinned_files']:
        pinned(manifest,name)
    if (Path(manifest['job']['attempt_dir'])/'failure.json').exists():
        raise BudgetStop('finalization recorded a terminal checker failure')


def validate_budget_identity(manifest,accepted):
    budget,prior=manifest['budget'],accepted['budget']
    if sequence.canonical(budget.get('prices_per_token'))!=sequence.canonical(prior.get('prices_per_token')):
        raise BudgetStop('finalization changes the accepted price table')
    caps=budget.get('per_job_attempt_usd')
    if not isinstance(caps,dict) or set(caps)!={manifest['job']['id']}:
        raise BudgetStop('finalization must declare only its exact job cap')
    try:
        current=Decimal(str(caps[manifest['job']['id']]))
        prior_cap=Decimal(str(prior.get('per_job_attempt_usd',{}).get(accepted['job']['id'],prior['per_attempt_usd'])))
    except (InvalidOperation,ValueError,TypeError) as error:
        raise BudgetStop('finalization attempt cap is invalid') from error
    if not current.is_finite() or current<=0 or not prior_cap.is_finite() or prior_cap<=0 or current>prior_cap:
        raise BudgetStop('finalization exceeds its inherited approved attempt cap')


def validate_scientific_identity(manifest, accepted):
    for name in ('api_runner.py','evidence_assertions.py','source_review.py','report_claims.py','derive_core.py','d4d_pair_consistency.py','profiles.py','schema_digest.py'):
        relative=Path('src/data_sheets_schema')/name
        if sha(Path(manifest['repository'])/relative)!=sha(Path(accepted['repository'])/relative):
            raise BudgetStop('finalization changes the inherited scientific instrument: '+name)
    if audit_registration.scientific_contract(manifest):
        if manifest['protocol_version'] == 7:
            batch_files = ('audit_batches.py', 'audit_batch_context.py', 'audit_grammar.py')
            if manifest['render_version'] == 21:
                batch_files += ('audit_batch_format.py',)
            for name in batch_files:
                relative = Path('src/data_sheets_schema') / name
                if sha(Path(manifest['repository']) / relative) != sha(Path(accepted['repository']) / relative):
                    raise BudgetStop('finalization changes the accepted batch scientific implementation: ' + name)
        if audit_registration.schema_semantic_context(manifest):
            relative=Path('src/data_sheets_schema/schema_semantics.py')
            if sha(Path(manifest['repository'])/relative)!=sha(Path(accepted['repository'])/relative):
                raise BudgetStop('finalization changes the accepted schema-semantics implementation')
        relative=Path('src/data_sheets_schema/anonymous_removals.py')
        if sha(Path(manifest['repository'])/relative)!=sha(Path(accepted['repository'])/relative):
            raise BudgetStop('finalization changes the accepted anonymous-removal implementation')
        if manifest['protocol_version'] >= 5:
            relative=Path('src/data_sheets_schema/source_metadata.py')
            if sha(Path(manifest['repository'])/relative)!=sha(Path(accepted['repository'])/relative):
                raise BudgetStop('finalization changes the accepted source-metadata implementation')
        protocol=Path(manifest['repository'])/f"src/download/prompts/evidence_protocol_v{manifest['protocol_version']}.md"
        if sha(protocol)!=sha(accepted['inputs']['protocol']):
            raise BudgetStop('finalization changes the accepted evidence protocol')


def validate_registration(path):
    path = canonical_path(str(Path(path).absolute()), exists=True)
    manifest = read_json(path)
    if 'audit_batches' in manifest:
        raise BudgetStop('audit_batches is audit-only; Phase 4 cannot select it')
    if 'audit_drafting' in manifest:
        raise BudgetStop('audit_drafting is audit-only; Phase 4 cannot select it')
    if 'audit_contract_context' in manifest:
        raise BudgetStop('audit_contract_context is audit-only; Phase 4 cannot select it')
    if 'audit_output' in manifest:
        raise BudgetStop('audit staged output cannot become a Phase 4 output mode')
    if (manifest.get('kind') != KIND or type(manifest.get('schema_version')) is not int or
            manifest['schema_version'] != 1):
        raise BudgetStop('unsupported Phase 4 continuation registration')
    upgraded = audit_registration.scientific_contract(manifest)
    verified_context(manifest)
    verify(manifest,path,sha(path))
    if required_paths(manifest)-{Path(name) for name in manifest['pinned_files']}:
        raise BudgetStop('finalization implementation and inherited input closure is not pinned')
    # Read-only foundation validation: validates exact acceptance and complete
    # carried accounting without claiming a tip, opening a ledger or locking.
    sequence._validate(manifest,path,sha(path))
    block = manifest['budget_sequence']
    if block['stage'] != 'reconciliation' or block['predecessor']['stage'] != 'audit':
        raise BudgetStop('finalization must directly follow its independently accepted audit')
    ref = manifest['accepted_audit']['registration']
    if ref != block['predecessor']['registration']:
        raise BudgetStop('scientific audit differs from the accepted budget predecessor')
    accepted = read_json(pinned(manifest,ref['path'],ref['sha256']))
    if (audit_registration.scientific_contract(accepted) != upgraded or
            any(manifest.get(key) != accepted.get(key) for key in
                ('protocol_version', 'render_version', audit_registration.TRANSITION))):
        raise BudgetStop('finalization changes the accepted scientific contract version')
    validate_budget_identity(manifest,accepted)
    expected_inputs = {**accepted['inputs'], 'audit':accepted['job']['audit_path']}
    if manifest['inputs'] != expected_inputs or manifest['parent'] != accepted['parent']:
        raise BudgetStop('finalization changes original source, record or audit ancestry')
    for name,digest in accepted['pinned_files'].items():
        pinned(manifest,name,digest)
    for key in ('model','profile','provider_base_url','provider_context_policy','native_runtime'):
        if manifest[key] != accepted[key]:
            raise BudgetStop('finalization changes the accepted audit '+key)
    if manifest.get('provider_transport') != accepted.get('provider_transport'):
        raise BudgetStop('finalization changes the reviewed provider transport')
    validate_scientific_identity(manifest, accepted)
    job=manifest['job']
    if not isinstance(job.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,150}',job['id']):
        raise BudgetStop('invalid finalization job identity')
    attempt,output=canonical_path(job['attempt_dir']),canonical_path(job['output_dir'])
    if attempt != path.parent/'attempts'/job['id'] or output != attempt/'output':
        raise BudgetStop('finalization attempt must use its exclusive registered destination')
    for key,name in [('full_path','full.yaml'),('core_path','core.yaml'),('report_path','report.md')]:
        if canonical_path(job[key])!=output/name:
            raise BudgetStop('finalization artifact differs from the registered layout')
    for name in manifest['pinned_files']:
        p=Path(name)
        if p==attempt or attempt in p.parents or p in attempt.parents:
            raise BudgetStop('finalization writes overlap immutable evidence')
    prefix=[manifest['python'],'-m','finalization_controls.contract','--registration',str(path)]
    if (job['derive_argv'] != [*prefix,'--operation','derive'] or
            job['check_argv'] != [[*prefix,'--operation','check','--round',str(i)] for i in range(2)]):
        raise BudgetStop('finalization helper commands differ from the selected registration')
    readable=set(manifest['inputs'].values())|{job['instruction'],job['system_prompt']}
    if 'context_recovery' in manifest:
        from native_context_control import paths as recovery_paths, validate as validate_recovery
        from .prepare import render_system
        validate_recovery(manifest,path)
        readable.update(recovery_paths(manifest))
        if Path(job['system_prompt']).read_text(encoding='utf-8')!=render_system(manifest):
            raise BudgetStop('finalization system prompt differs from its registered recovery contract')
    if set(job['readable_inputs'])!=readable:
        raise BudgetStop('finalization read scope differs from its exact input roster')
    if type(job['deadline_seconds']) is not int or job['deadline_seconds']<=0:
        raise BudgetStop('finalization deadline must be positive whole seconds')
    audit_registration.native_api_timeout(manifest)
    from .contract import render_instruction
    if Path(job['instruction']).read_text()!=render_instruction(manifest):
        raise BudgetStop('finalization instruction does not replay its complete scientific contract')
    return manifest
