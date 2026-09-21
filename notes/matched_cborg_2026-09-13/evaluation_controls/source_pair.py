"""Exact independently accepted composite pair; never manufacture generation acceptance."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

KIND = 'composite_finalization_v1'


def fitness_schema_authority(manifest):
    """Exact accepted schema roots; selected guidance never guesses new schemas."""
    from data_sheets_schema.fitness_schema import validate_selection
    if validate_selection(manifest) is None:
        return None
    Stop, _, canonical, read, sha = _tools()
    if manifest.get('schema_version') == 2:
        ref = manifest['source_pair']['finalization']['registration']
        path = canonical(ref['path'], exists=True)
        if sha(path) != ref['sha256']:
            raise Stop('selected fitness finalization authority changed')
        source = read(path)
        if source.get('kind') != 'd4d_native_finalization':
            raise Stop('selected fitness requires its accepted finalization schema')
        paths = {variant: canonical(source['inputs'][variant+'_schema'], exists=True)
                 for variant in ('full', 'core')}
    else:
        ref = manifest['source_generation']
        path = canonical(ref['registration'], exists=True)
        if sha(path) != ref['registration_sha256']:
            raise Stop('selected fitness generation authority changed')
        source = read(path)
        paths = {variant: canonical(str(Path(source['repository'])/'src/data_sheets_schema/schema'/name), exists=True)
                 for variant, name in (('full','data_sheets_schema_all.yaml'),
                                       ('core','data_sheets_schema_core_all.yaml'))}
    base = canonical(source['repository'], exists=True)
    pins = {}
    for name, identity in source['pinned_files'].items():
        key = Path(name)
        key = key if key.is_absolute() else base/key
        key = str(key.resolve(strict=True))
        if key in pins and pins[key] != identity:
            raise Stop('ambiguous accepted fitness schema pin')
        pins[key] = identity
    if any(pins.get(str(path)) != sha(path) for path in paths.values()):
        raise Stop('accepted fitness schema root lacks its exact original pin')
    return paths, pins, base


def fitness_snapshot_paths(manifest, job, snapshot, *, require_pins=True):
    """Bind the actual captured imports and vocabulary to accepted authority."""
    Stop, _, _, _, sha = _tools()
    paths, source_pins, source_root = fitness_schema_authority(manifest)
    expected = paths[job['variant']]
    if (job['schema_path'] != str(expected) or snapshot.schema_path != str(expected)
            or job['class_name'] != ('Dataset' if job['variant']=='full' else 'CoreDataset')):
        raise Stop('selected fitness schema differs from the accepted full/core authority')
    captured = []
    for path, identity in snapshot.sources:
        path = Path(path).resolve(strict=True)
        if source_pins.get(str(path)) != identity or sha(path) != identity:
            raise Stop('selected fitness import closure differs from accepted schema pins')
        captured.append((path, identity))
    for path, identity in snapshot.profile_sources:
        path = Path(path).resolve(strict=True)
        try:
            ancestor = source_root/path.relative_to(Path(manifest['repository']))
        except ValueError:
            ancestor = path
        if source_pins.get(str(ancestor.resolve(strict=True))) != identity or sha(path) != identity:
            raise Stop('selected fitness vocabulary differs from accepted profile pins')
        captured.append((path, identity))
    if require_pins and any(manifest['pinned_files'].get(str(path)) != identity for path, identity in captured):
        raise Stop('selected fitness captured schema/vocabulary closure is not pinned')
    return captured


def _tools():
    # Evaluation controls also support historical direct script entry points.
    from registration import BudgetStop, canonical_digest, canonical_path, read_json, sha
    return BudgetStop, canonical_digest, canonical_path, read_json, sha


def inspect_finalization(registration, acceptance):
    """Read a completed, independently accepted Phase4 closure without activating it."""
    Stop, digest, canonical, read, sha = _tools()
    def require(test, reason):
        if not test:
            raise Stop(reason)
    def ref(value):
        path = canonical(str(value), exists=True)
        require(path.is_file() and not path.is_symlink(), 'composite evidence is not a regular canonical file')
        return {'path': str(path), 'sha256': sha(path)}
    phase_path, acceptance_path = canonical(str(registration), exists=True), canonical(str(acceptance), exists=True)
    phase, review = read(phase_path), read(acceptance_path)
    require(phase.get('kind') == 'd4d_native_finalization' and phase.get('schema_version') == 1,
            'composite source requires a native Phase4 registration')
    job, block = phase['job'], phase['budget_sequence']
    require(block.get('protocol') == 'shared_sequence_v2' and block.get('stage') == 'reconciliation',
            'composite finalization has another accounting stage')
    attempt = canonical(job['attempt_dir'])
    require(attempt == phase_path.parent/'attempts'/job['id'] and
            canonical(job['output_dir']) == attempt/'output', 'composite attempt layout differs')
    result_path, ledger_path = attempt/'result.json', canonical(phase['budget']['ledger_path'], exists=True)
    require(ledger_path == phase_path.parent/'billing.json', 'composite ledger path differs')
    result, ledger = read(result_path), read(ledger_path)
    artifacts = {str(canonical(job[role+'_path'], exists=True)): sha(job[role+'_path'])
                 for role in ('full', 'core', 'report')}
    require(all(canonical(job[role+'_path']) == attempt/'output'/name
                for role, name in [('full','full.yaml'),('core','core.yaml'),('report','report.md')]),
            'composite artifact layout differs')
    lineage_path = attempt/'lineage.json'
    all_artifacts = {**artifacts, str(lineage_path): sha(lineage_path)}
    validation, runtime = result.get('validation', {}), result.get('runtime', {})
    require(result.get('status') == 'completed_pending_independent_review' and
            result.get('scope') == 'phase4_reconciliation' and result.get('job_id') == job['id'] and
            result.get('registration_sha256') == sha(phase_path) and result.get('unresolved_requests') == [] and
            validation.get('checked') is True and validation.get('passed') is True and
            validation.get('errors') == [] and validation.get('findings') == [] and
            digest(validation.get('artifacts')) == digest(artifacts) and
            digest(result.get('artifacts')) == digest(all_artifacts) and
            type(runtime.get('exit_code')) is int and runtime['exit_code'] == 0 and
            runtime.get('proxy_shutdown_complete') is True and type(runtime.get('unfinished_handlers')) is int and
            runtime['unfinished_handlers'] == 0, 'composite finalization lacks exact successful closed evidence')
    require(review.get('verdict') == 'accept' and review.get('registration_sha256') == sha(phase_path) and
            review.get('result_sha256') == sha(result_path) and review.get('ledger_sha256') == sha(ledger_path) and
            digest(review.get('artifacts')) == digest(all_artifacts),
            'composite pair lacks independent acceptance of every final artifact and closed accounting')
    require(ledger.get('manifest_sha256') == sha(phase_path) and isinstance(ledger.get('requests'), list) and
            all(row.get('status') == 'settled' for row in ledger['requests']), 'composite accounting is unresolved')
    costs = [Decimal(str(row['cost_usd'])) for row in ledger['requests']]
    ids = [row.get('id') for row in ledger['requests']]
    require(all(cost.is_finite() and cost >= 0 for cost in costs) and
            all(isinstance(i, str) and i for i in ids) and len(set(ids)) == len(ids), 'composite accounting rows are invalid')
    pins = dict(phase['pinned_files'])
    for name, expected in pins.items():
        require(ref(name)['sha256'] == expected, 'composite inherited input changed: '+name)
    expected_inputs = {name: {'path': value, 'sha256': pins[value]} for name, value in phase['inputs'].items()}
    lineage = read(lineage_path)
    require(lineage.get('kind') == 'd4d_composite_finalization_lineage' and
            lineage.get('schema_version') == 1 and lineage.get('registration_sha256') == sha(phase_path) and
            lineage.get('scope') == 'phase4_reconciliation' and
            digest(lineage.get('original_generation')) == digest(block['origin']['registration']) and
            digest(lineage.get('accepted_audit')) == digest(block['audit_origin']) and
            digest(lineage.get('final_artifacts')) == digest(artifacts) and
            digest(lineage.get('source_inputs')) == digest(expected_inputs) and
            isinstance(result.get('evidence', {}).get('phase4'), dict) and bool(result['evidence']['phase4']) and
            digest(lineage.get('observed_phase4')) == digest(result['evidence']['phase4']) and
            lineage.get('phase1_phase2_performed_here') is False and lineage.get('phase3_performed_here') is False and
            lineage.get('scientific_acceptance') is False,
            'composite lineage does not bind the original, accepted audit and observed finalization')
    audit_ref = block['audit_origin']['registration']
    require(digest(phase['accepted_audit']['registration']) == digest(audit_ref), 'composite accepted audit identities differ')
    audit = read(audit_ref['path'])
    require(ref(audit_ref['path']) == audit_ref and audit.get('kind') == 'd4d_native_audit_continuation' and
            digest(audit['parent']) == digest(phase['parent']) and
            phase['inputs'] == {**audit['inputs'], 'audit': audit['job']['audit_path']},
            'composite scientific audit ancestry differs')
    origin_ref = block['origin']['registration']
    require(ref(phase['parent']['registration']) == origin_ref, 'composite original registration differs')
    generation = read(origin_ref['path'])
    matches = [j for j in generation['generation']['jobs'] if j['id'] == phase['parent']['job_id']]
    require(len(matches) == 1, 'composite original job is absent or ambiguous')
    original = matches[0]
    bundle = ref(phase['inputs']['bundle'])
    base = Path(generation['repository'])
    original_bundle = Path(original['bundle'])
    original_bundle = original_bundle if original_bundle.is_absolute() else base/original_bundle
    require(ref(original_bundle) == bundle and original.get('input_identity', {}).get('bundle') == bundle and
            phase['profile'] == original['profile'], 'composite source bundle or profile differs from generation')
    source = {'kind': KIND,
        'finalization': {'registration': ref(phase_path), 'result': ref(result_path), 'acceptance': ref(acceptance_path),
                         'ledger': ref(ledger_path), 'lineage': ref(lineage_path)},
        'original_generation': {'registration': deepcopy(origin_ref), 'job_id': original['id']},
        'accepted_audit': deepcopy(block['audit_origin']),
        'artifacts': {role: ref(job[role+'_path']) for role in ('full','core')},
        'bundle': bundle, 'project': original['project'], 'method': original['method'], 'profile': original['profile']}
    for path in [phase_path, result_path, acceptance_path, ledger_path, lineage_path, *artifacts]:
        pins[str(path)] = sha(path)
    return source, pins, phase


def validate(manifest):
    """Validate the scientific source independently of the mutable sequence tip."""
    Stop, digest, _, _, _ = _tools()
    source = manifest['source_pair']
    if source.get('kind') != KIND:
        raise Stop('unsupported composite source kind')
    expected, pins, phase = inspect_finalization(source['finalization']['registration']['path'],
                                                source['finalization']['acceptance']['path'])
    if digest(expected) != digest(source):
        raise Stop('composite source differs from its immutable accepted finalization')
    if any(manifest['pinned_files'].get(name) != value for name, value in pins.items()):
        raise Stop('composite source closure is incompletely pinned')
    block = manifest['budget_sequence']
    if any(digest(block[name]) != digest(phase['budget_sequence'][name]) for name in ('origin','audit_origin','seal')):
        raise Stop('evaluation changes shared composite ancestry')
    if block['stage'] == 'evaluation':
        predecessor = block['predecessor']
        if predecessor['stage'] != 'reconciliation' or any(predecessor[name] != source['finalization'][name]
                for name in ('registration','ledger','result','acceptance')):
            raise Stop('evaluation budget predecessor differs from accepted finalization')
    elif block['stage'] != 'evaluation_subtype':
        raise Stop('unsupported composite evaluation stage')
    if any(manifest[name] != phase[name] for name in ('model','provider_base_url','provider_context_policy','profile')):
        raise Stop('evaluation changes accepted model, transport policy or profile')
    if manifest.get('provider_transport') != phase.get('provider_transport'):
        raise Stop('evaluation changes accepted pinned provider trust')
    if digest(manifest['budget'].get('prices_per_token')) != digest(phase['budget']['prices_per_token']):
        raise Stop('evaluation changes accepted provider prices')
    if manifest['project'] != source['project'] or manifest['method'] != source['method']:
        raise Stop('evaluation changes original project/method identity')
    for job in manifest['evaluation_jobs']:
        if job['style'] in {'semantic_agent','field_agent'}:
            from audit_controls.registration import native_api_timeout, native_api_force_idle_timeout
            expected_timeout = native_api_timeout(phase)
            if expected_timeout is None or native_api_force_idle_timeout(phase) is not False:
                raise Stop('accepted native runtime lacks reviewed bounded idle controls')
            runtime_manifest = {'native_runtime':job['native_runtime'], 'job':job}
            if native_api_timeout(runtime_manifest) != min(expected_timeout, job['deadline_seconds'] * 1000) or native_api_force_idle_timeout(runtime_manifest) is not False:
                raise Stop('evaluation native timeout differs from accepted runtime')
            for key in ('executable','version','context_window','max_output_tokens','effort'):
                if digest(job['native_runtime'].get(key)) != digest(phase['native_runtime'].get(key)):
                    raise Stop('evaluation changes the accepted native runtime '+key)
    validate_roster(manifest)
    return phase


def validate_roster(manifest):
    """The registered initial comparison includes every prescribed cell and slot."""
    Stop, digest, _, read, _ = _tools()
    from prepare_evaluation import slot_inventory
    from registration import group
    from data_sheets_schema.fitness_schema import validate_manifest_selection
    selected = validate_manifest_selection(manifest)
    source=manifest['source_pair'];root=Path(manifest['repository'])
    stage=manifest['budget_sequence']['stage'];jobs=manifest['evaluation_jobs']
    subtype=stage=='evaluation_subtype'
    if not jobs or any((j['style']=='subtype') != subtype for j in jobs):
        raise Stop('composite evaluation stage differs from its initial or subtype roster')
    expected_schema={variant:str(root/'src/data_sheets_schema/schema'/name) for variant,name in (
        ('full','data_sheets_schema_all.yaml'),('core','data_sheets_schema_core_all.yaml'))}
    selected_schema = fitness_schema_authority(manifest)[0] if selected else {}
    for job in jobs:
        if any(job.get(key)!=manifest[key] for key in ('context_path','project','method','profile')):
            raise Stop('evaluation job changes the registered context or dataset identity')
        schema = (str(selected_schema[job['variant']]) if selected and job['style'] in {'fitness','subtype'}
                  else expected_schema.get(job['variant']))
        if job.get('schema_path') != schema:
            raise Stop('evaluation job changes its complete class schema')
        if job['style']=='grounding' and job.get('bundle')!=source['bundle']['path']:
            raise Stop('grounding job changes the frozen source bundle')
        if job['style'] in {'semantic_agent','field_agent'}:
            number=10 if job.get('rubric','').startswith('rubric10') else 20
            suffix='-semantic' if job['style']=='semantic_agent' else ''
            if (job.get('agent_definition')!=str(root/f'.claude/agents/d4d-rubric{number}{suffix}.md') or
                    job.get('rubric_file')!=str(root/f'data/rubric/rubric{number}.txt')):
                raise Stop('native evaluator changes its registered rubric definition')
    if subtype:
        prior=manifest.get('prior_evaluation')
        if not prior:
            raise Stop('subtype evaluation lacks an exact prior registration')
        previous=read(prior['registration'])
        for key in ('source_pair','context_path','project','method','profile','model','provider_base_url',
                    'provider_context_policy','provider_transport','rubric_dir','prompts_dir','fitness_schema_guidance'):
            if digest(previous.get(key))!=digest(manifest.get(key)):
                raise Stop('subtype successor changes comparison identity '+key)
        return
    expected=[]
    for variant in ('full','core'):
        for style in ('semantic_agent','field_agent','direct_api_quality'):
            for number in (10,20):
                rubric=f'rubric{number}'+('-semantic' if style=='semantic_agent' else '')
                for rating in range(1,4 if style=='semantic_agent' else 2):
                    expected.append((variant,style,rubric,rating,None,None,None,rating==1))
        inventory=slot_inventory(source['artifacts'][variant]['path'],
            'Dataset' if variant=='full' else 'CoreDataset',expected_schema[variant])
        for style in ('grounding','fitness'):
            selected_inventory = (slot_inventory(source['artifacts'][variant]['path'],
                'Dataset' if variant=='full' else 'CoreDataset',selected_schema[variant])
                if selected and style=='fitness' else inventory)
            for index,row in enumerate(selected_inventory['included']):
                expected.append((variant,style,None,1,row['unit_path'],row['slot'],row['value_sha256'],index==0))
    actual=[(j['variant'],j['style'],j.get('rubric'),j['rating'],j.get('unit_path'),j.get('slot'),j.get('value_sha256'),j['canary']) for j in jobs]
    from collections import Counter
    if Counter(actual)!=Counter(expected):
        raise Stop('initial composite evaluation roster omits or changes a prescribed rating or eligible slot')
