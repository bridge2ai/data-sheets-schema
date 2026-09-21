"""Prepare one accepted full/core pair's evaluation roster without provider calls.

This creates immutable requests and instructions, never an acceptance or a
launch approval. Conditional subtype requests require a later registration
because their exact prompts depend on the observed fitness reasons.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import shutil
import subprocess
import sys

from registration import (BudgetStop, NATIVE_STYLES, canonical_path, group,
    read_json, required_paths, sha, source_artifacts, verify_implementation, verify_manifest)
from budgeted_cborg import write_new
from audit_controls.transport import transport_paths, verified_context
from api import render_request, slot_instrument, value_digest
from native import CLI_FLAGS, ENVIRONMENT, additional_directories
from instructions import render_instruction
from validation import validator_argv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
_UNSELECTED = object()


def _fitness_selection(value):
    from data_sheets_schema.fitness_schema import SELECTOR, validate_selection
    selection = {} if value is _UNSELECTED else {SELECTOR:value}
    validate_selection(selection)
    return selection


def _fitness_snapshots(manifest):
    from data_sheets_schema.fitness_schema import validate_selection, capture
    from data_sheets_schema.profiles import profile_named
    if validate_selection(manifest) is None:
        return {}
    from source_pair import fitness_schema_authority, fitness_snapshot_paths
    paths, _, _ = fitness_schema_authority(manifest)
    snapshots = {}
    for variant in ('full','core'):
        kind = 'Dataset' if variant=='full' else 'CoreDataset'
        snapshot = capture(kind, paths[variant], profile=profile_named(manifest['profile']))
        job = {'variant':variant,'class_name':kind,'schema_path':str(paths[variant])}
        for path, identity in fitness_snapshot_paths(manifest, job, snapshot, require_pins=False):
            manifest['pinned_files'][str(path)] = identity
        snapshots[variant] = snapshot
    return snapshots


def _source_path(repository, value):
    path = Path(value)
    return (path if path.is_absolute() else repository / path).resolve(strict=True)


def _pin(manifest, *paths):
    for path in paths:
        path = Path(path).resolve(strict=True)
        manifest['pinned_files'][str(path)] = sha(path)


def runtime_snapshot(executable=None):
    executable = executable or shutil.which('claude')
    if not executable:
        raise BudgetStop('the native evaluator executable must be supplied or installed locally')
    path = Path(executable).resolve(strict=True)
    version = subprocess.check_output([str(path), '--version'], text=True).strip()
    if version != '2.1.272 (Claude Code)':
        raise BudgetStop('this registration preparer requires the reviewed native runtime 2.1.272')
    return {'executable': str(path), 'version': version, 'cli_flags': list(CLI_FLAGS),
        'environment': dict(ENVIRONMENT), 'context_window': 200000, 'max_output_tokens': 64000,
        'effort': 'native_default'}


def slot_inventory(path, class_name, schema_path):
    """Schema-known, nonempty top-level fields; no cross-record propagation."""
    from data_sheets_schema.duplicate_keys import duplicate_keys_in
    from data_sheets_schema.evaluation_context import dataset_units, declared_class, load_document
    from data_sheets_schema.schema_digest import build_for_judgement
    if duplicate_keys_in(Path(path)):
        raise BudgetStop('accepted evaluation input contains duplicate YAML keys')
    document, digest = load_document(Path(path))
    declared = declared_class(document)
    if declared is not None and declared != class_name:
        raise BudgetStop('accepted record declares a different full/core class')
    if declared is None and document.get('resources'):
        raise BudgetStop('undeclared resource container has ambiguous dataset/collection evaluation scope')
    _, schema = build_for_judgement(class_name, Path(schema_path))
    known = {slot.name for slot in schema.slots}
    included, excluded = [], []
    for unit_path, unit in dataset_units(document):
        unit_class = declared_class(unit)
        if unit_class is not None and unit_class != class_name:
            raise BudgetStop('evaluation unit has a different declared class')
        for slot, value in sorted(unit.items()):
            reason = None
            if slot not in known:
                reason = 'not a slot of the selected schema class'
            elif value is None or value == '' or value == [] or value == {}:
                reason = 'empty value; no populated-slot judgment applies'
            row = {'unit_path': unit_path, 'slot': slot, 'value_sha256': value_digest(value)}
            if reason:
                excluded.append({**row, 'reason': reason})
            else:
                included.append(row)
    return {'input_sha256': digest, 'class_name': class_name,
            'included': sorted(included, key=lambda row: (row['unit_path'], row['slot'])),
            'excluded': excluded}


def _job(manifest, destination, variant, style, identity, *, rating=1, canary=True, rubric=None):
    source = source_artifacts(manifest)[variant]
    kind = 'Dataset' if variant == 'full' else 'CoreDataset'
    row = {'id': identity, 'style': style, 'variant': variant, 'class_name': kind,
        'input': source['path'], 'input_sha256': source['sha256'], 'context_path': manifest['context_path'],
        # Method is the caller's identity. Variant/class are separate fields;
        # inventing or appending a suffix can corrupt an already named method.
        'project': manifest['project'], 'method': manifest['method'],
        'profile': manifest['profile'], 'rating': rating, 'canary': canary,
        'candidate': str(destination / 'attempts' / identity / 'output/candidate.json'),
        'output': str(destination / 'published' / (identity + '.json')),
        'schema_path': str(ROOT / 'src/data_sheets_schema/schema' /
                           ('data_sheets_schema_all.yaml' if variant == 'full' else 'data_sheets_schema_core_all.yaml')),
        'deadline_seconds': 10800 if style in NATIVE_STYLES else 1800,
        'max_tokens': 64000 if style in NATIVE_STYLES else (32000 if style == 'direct_api_quality' else 8000)}
    if rubric:
        row['rubric'] = rubric
    if style == 'fitness' and 'fitness_schema_guidance' in manifest:
        from source_pair import fitness_schema_authority
        row['fitness_schema_guidance'] = manifest['fitness_schema_guidance']
        row['schema_path'] = str(fitness_schema_authority(manifest)[0][variant])
    row['canary_group'] = group(row)
    if not canary:
        row['canary_acceptance'] = str(destination / 'acceptances' / (row['canary_group'].replace(':', '_') + '.json'))
    return row


def build_registration(destination, *, generation_registration, generation_acceptance,
                       generation_job_id, context_path, billing_checkpoint,
                       native_executable=None, project=None, method=None, profile=None,
                       provider_base_url=None, provider_ca_bundle=None,
                       fitness_schema_guidance=_UNSELECTED):
    """Build an exclusive offline condition; caller must supply actual acceptance.

    The source generation ledger must already be settled and match the
    checkpoint. This first evaluation registration cannot fork an existing
    evaluation chain; the execution controller enforces the handoff atomically.
    """
    fitness_selection = _fitness_selection(fitness_schema_guidance)
    destination = canonical_path(str(destination))
    if destination.exists():
        raise BudgetStop('evaluation preparation directory already exists; never overwrite it')
    generation_path = canonical_path(str(generation_registration), exists=True)
    acceptance_path = canonical_path(str(generation_acceptance), exists=True)
    context_path = canonical_path(str(context_path), exists=True)
    billing_checkpoint = canonical_path(str(billing_checkpoint), exists=True)
    generation, acceptance = read_json(generation_path), read_json(acceptance_path)
    source_sha = sha(generation_path)
    if acceptance.get('verdict') != 'accept' or acceptance.get('registration_sha256') != source_sha:
        raise BudgetStop('supply independent acceptance of this exact generation before preparing evaluations')
    source_repository = canonical_path(generation['repository'], exists=True)
    matches = [job for job in generation['generation']['jobs'] if job['id'] == generation_job_id]
    if len(matches) != 1:
        raise BudgetStop('generation job is absent or ambiguous')
    source_job = matches[0]
    if acceptance.get('job_id', generation_job_id) != generation_job_id:
        raise BudgetStop('acceptance names a different generation job')
    artifacts = {variant: _source_path(source_repository, source_job['outputs'][variant]) for variant in ('full', 'core')}
    for artifact in artifacts.values():
        if acceptance.get('artifacts', {}).get(str(artifact)) != sha(artifact):
            raise BudgetStop('independent acceptance does not bind the unchanged full/core pair')
    ledger_path = canonical_path(generation['budget']['ledger_path'], exists=True)
    if sha(ledger_path) != sha(billing_checkpoint):
        raise BudgetStop('billing checkpoint is not the final generation ledger')
    state = read_json(billing_checkpoint)
    rows = state.get('requests')
    if (state.get('manifest_sha256') != source_sha or state.get('additional_cap_usd') != '400' or
        state.get('attempt_cap_usd') != '5' or not isinstance(rows, list) or
        any(row.get('status') != 'settled' for row in rows)):
        raise BudgetStop('generation billing is unresolved or does not carry the approved allocation')
    spent = sum((Decimal(str(row['cost_usd'])) for row in rows), Decimal(0))
    if not spent.is_finite() or spent < 0 or spent > 400:
        raise BudgetStop('generation settled total is invalid')
    sequence = canonical_path(acceptance['evaluation_sequence_state'])
    from data_sheets_schema.evaluation_context import load_context
    from data_sheets_schema.profiles import profile_named
    load_context(context_path)
    selected_profile = profile if profile is not None else source_job['profile']
    if selected_profile != source_job['profile']:
        raise BudgetStop('evaluation profile must match the accepted generation profile')
    profile_object = profile_named(selected_profile)
    native_runtime = runtime_snapshot(native_executable)
    bundle = _source_path(source_repository, source_job['bundle'])
    original_bundle = source_job.get('input_identity', {}).get('bundle', {})
    original_pins = [generation.get('pinned_files', {}).get(key) for key in
                     {source_job['bundle'], str(bundle)}]
    original_pins = [digest for digest in original_pins if digest is not None]
    if (original_bundle.get('path') != str(bundle) or original_bundle.get('sha256') != sha(bundle) or
        not original_pins or any(digest != original_bundle['sha256'] for digest in original_pins)):
        raise BudgetStop('grounding bundle differs from the accepted generation source identity')
    manifest = {'kind': 'd4d_evaluation_registration', 'schema_version': 1,
        'registered_at': datetime.now(timezone.utc).isoformat(), 'repository': str(ROOT),
        'repository_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'python': sys.executable, 'python_identity': {'resolved_path': str(Path(sys.executable).resolve()),
            'sha256': sha(sys.executable), 'prefix': str(Path(sys.prefix).resolve())},
        'provider_base_url': provider_base_url if provider_base_url is not None else generation['provider_base_url'],
        'provider_context_policy': generation['provider_context_policy'], 'model': deepcopy(generation['model']),
        'project': project or source_job['project'], 'method': method or source_job['method'],
        'profile': selected_profile, 'context_path': str(context_path),
        'rubric_dir': str(ROOT / 'data/rubric'), 'prompts_dir': str(ROOT / 'src/download/prompts'),
        'attempts_dir': str(destination / 'attempts'), 'evaluation_jobs': [], 'pinned_files': {},
        'source_generation': {'registration': str(generation_path), 'registration_sha256': source_sha,
            'job_id': generation_job_id, 'acceptance': str(acceptance_path), 'acceptance_sha256': sha(acceptance_path),
            'billing_ledger': str(ledger_path), 'billing_sha256': sha(ledger_path),
            'evaluation_sequence_state': str(sequence),
            'artifacts': {variant: {'path': str(path), 'sha256': sha(path)} for variant, path in artifacts.items()}},
        'budget': {'additional_usd': '400', 'per_attempt_usd': '5', 'ledger_path': str(destination / 'billing.json'),
            'prices_per_token': deepcopy(generation['budget']['prices_per_token']),
            'continuation': {'checkpoint': str(destination / 'generation_billing_checkpoint.json'),
                             'sha256': sha(billing_checkpoint), 'cost_usd': str(spent)}},
        'conditional_subtype': {'selection': 'all_form_failures', 'status': 'deferred_until_all_fitness_results',
            'requires': 'new reviewed registration with exact parent receipts/results/requests and the settled evaluation ledger'},
        'offline_checks': ['schema', 'pair', 'duplicate_keys', 'provenance', 'receipts', 'report_grounding',
                           'literal_grounding', 'field_presence_rubric10', 'field_presence_rubric20'],
        'slot_selection': 'every populated schema-known top-level slot of each explicit dataset unit; no propagation'}
    manifest.update(fitness_selection)
    if provider_ca_bundle is not None:
        manifest['provider_transport'] = {'kind': 'pinned_ca_v1',
            'ca_bundle': str(canonical_path(str(provider_ca_bundle), exists=True))}
    _pin(manifest, *transport_paths(manifest))
    verified_context(manifest)
    _pin(manifest, generation_path, acceptance_path, context_path, bundle, *artifacts.values())
    if profile_object.pin_path is not None:
        _pin(manifest, profile_object.pin_path)
    return _materialize(manifest, destination, bundle, native_runtime, spent, billing_checkpoint=billing_checkpoint)


def _materialize(manifest, destination, bundle, native_runtime, spent, *, billing_checkpoint=None, prepared_directory=False,
                 fitness_snapshots=None):
    snapshots = _fitness_snapshots(manifest) if fitness_snapshots is None else fitness_snapshots
    jobs = manifest['evaluation_jobs']
    for variant in ('full', 'core'):
        for style in ('semantic_agent', 'field_agent', 'direct_api_quality'):
            for number in (10, 20):
                rubric = f'rubric{number}' + ('-semantic' if style == 'semantic_agent' else '')
                for rating in range(1, 4 if style == 'semantic_agent' else 2):
                    identity = f'{variant}_{style}_r{number}_rating{rating}'
                    jobs.append(_job(manifest, destination, variant, style, identity,
                                     rubric=rubric, rating=rating, canary=rating == 1))
    inventory = {}
    for variant in ('full', 'core'):
        base = next(job for job in jobs if job['variant'] == variant)
        inventory[variant] = slot_inventory(base['input'], base['class_name'], base['schema_path'])
        for style in ('grounding', 'fitness'):
            selected_inventory = inventory[variant]
            if style=='fitness' and snapshots:
                selected_inventory = slot_inventory(base['input'],base['class_name'],snapshots[variant].schema_path)
                inventory[variant]['selected_fitness_inventory'] = selected_inventory
            for index, selected in enumerate(selected_inventory['included'], 1):
                identity = f'{variant}_{style}_slot{index:04d}'
                row = _job(manifest, destination, variant, style, identity, canary=index == 1)
                row.update(selected)
                if style == 'grounding':
                    row['bundle'] = str(bundle)
                row['instrument'] = (slot_instrument(row, schema_snapshot=snapshots[variant])
                                     if style=='fitness' and snapshots else slot_instrument(row))
                jobs.append(row)
    style_order = {name: index for index, name in enumerate(
        ('semantic_agent', 'field_agent', 'direct_api_quality', 'grounding', 'fitness'))}
    # Review every primary canary before expanding any dependent slot sweep;
    # finish primary judgments before the semantic repeats. Each noncanary
    # still requires its own group's independent acceptance.
    jobs.sort(key=lambda job: (not job['canary'], job['rating'] > 1, style_order[job['style']],
                               job['variant'] != 'full', job['id']))
    manifest['planned_execution_order'] = [job['id'] for job in jobs]
    if manifest.get('schema_version') == 2:
        manifest['canary_acceptances'] = {job['canary_group']:str(destination/'acceptances'/(job['canary_group'].replace(':','_')+'.json')) for job in jobs if job['canary']}
    if not prepared_directory:
        destination.mkdir(parents=True, exist_ok=False)
    if billing_checkpoint is not None:
        checkpoint_copy = destination / 'generation_billing_checkpoint.json'
        with checkpoint_copy.open('xb') as stream:
            stream.write(billing_checkpoint.read_bytes())
        _pin(manifest, checkpoint_copy)
    request_sizes = []
    for job in jobs:
        if job['style'] in NATIVE_STYLES:
            suffix = '-semantic' if job['style'] == 'semantic_agent' else ''
            number = 10 if job['rubric'].startswith('rubric10') else 20
            job.update(agent_definition=str(ROOT / f'.claude/agents/d4d-rubric{number}{suffix}.md'),
                rubric_file=str(ROOT / f'data/rubric/rubric{number}.txt'),
                instruction=str(destination / 'instructions' / (job['id'] + '.txt')),
                native_runtime=deepcopy(native_runtime))
            if manifest.get('schema_version') == 2:
                job['native_runtime']['api_timeout_ms'] = min(native_runtime['api_timeout_ms'], job['deadline_seconds'] * 1000)
                job['native_runtime']['api_force_idle_timeout'] = False
            job['validator_argv'] = validator_argv(manifest, job)
            job['native_runtime']['additional_directories'] = additional_directories(manifest, job)
            _pin(manifest, job['agent_definition'], job['rubric_file'], job['native_runtime']['executable'])
            text = render_instruction(manifest, job)
            instruction = Path(job['instruction']); instruction.parent.mkdir(exist_ok=True)
            with instruction.open('x', encoding='utf-8', newline='') as stream:
                stream.write(text)
            _pin(manifest, instruction)
            request_sizes.append({'job_id': job['id'], 'instruction_utf8_bytes': len(text.encode()),
                                  'system_utf8_bytes': Path(job['agent_definition']).stat().st_size})
        else:
            request = (render_request(manifest, job, schema_snapshot=snapshots[job['variant']])
                       if job['style']=='fitness' and snapshots else render_request(manifest, job))
            path = destination / 'requests' / (job['id'] + '.json')
            write_new(path, request)
            job['expected_request'] = str(path)
            _pin(manifest, path)
            request_sizes.append({'job_id': job['id'], 'request_json_bytes': path.stat().st_size})
    _pin(manifest, *required_paths(manifest))
    inventory_path = destination / 'slot_inventory.json'; write_new(inventory_path, inventory)
    _pin(manifest, inventory_path)
    manifest_path = destination / 'registration.json'; write_new(manifest_path, manifest)
    verify_manifest(manifest, manifest_path, sha(manifest_path))
    counts = dict(Counter(job['style'] for job in jobs))
    prices = {key: Decimal(str(value)) for key, value in manifest['budget']['prices_per_token'].items()}
    input_price = max(prices['input'], prices['cache_write'])
    estimates = []
    by_id = {job['id']: job for job in jobs}
    for size in request_sizes:
        job = by_id[size['job_id']]
        if job['style'] in NATIVE_STYLES:
            raw_bytes = size['instruction_utf8_bytes'] + size['system_utf8_bytes']
            estimates.append({'job_id': job['id'], 'input_token_heuristic': (raw_bytes + 3) // 4,
                'cost_usd': '5', 'basis': 'entire native attempt ceiling, including multiple requests',
                'context_limit': 200000})
        else:
            tokens = (size['request_json_bytes'] + 3) // 4
            cost = Decimal(tokens) * input_price + Decimal(job['max_tokens']) * prices['output']
            estimates.append({'job_id': job['id'], 'input_token_heuristic': tokens,
                'output_token_ceiling': job['max_tokens'], 'cost_usd': str(cost),
                'basis': 'serialized request bytes / 4, highest registered input/cache-write price, maximum output tokens'})
    estimate_total = sum((Decimal(row['cost_usd']) for row in estimates), Decimal(0))
    report = {'registration_sha256': sha(manifest_path), 'provider_calls': 0, 'token_count_calls': 0,
        'registered_jobs': len(jobs), 'style_counts': counts, 'rubric_ratings': 20,
        'native_primary_canaries': 8, 'semantic_repeat_ratings': 8,
        'remaining_allocation_usd': str(Decimal('400') - spent), 'per_attempt_limit_usd': '5',
        'sum_attempt_limits_usd': str(Decimal(5) * len(jobs)), 'request_sizes': request_sizes,
        'planning_cost_usd': str(estimate_total), 'planning_estimates': estimates,
        'planning_estimate_exceeds_remaining': estimate_total > Decimal('400') - spent,
        'native_context_estimate_exceeds_observed_limit': [row['job_id'] for row in estimates
            if row.get('context_limit') and row['input_token_heuristic'] > row['context_limit']],
        'cost_estimate': 'Offline planning estimate only; bytes/4 is a heuristic, not a token count or admission guarantee. '
                         'Native estimates use the whole five-dollar attempt ceiling and omit runtime-added system/tool '
                         'context from the rough size check. Sum-of-attempt ceilings is exposure, not forecast. '
                         'No token-count endpoint was contacted or assumed free. Actual counted reservations and settled '
                         'charges remain enforced by the shared ledger before every paid request.',
        'status': 'prepared_pending_independent_review_and_ci', 'conditional_subtype_jobs': 0,
        'scope': 'one accepted full/core pair; no production cohort or historical rescore launch'}
    write_new(destination / 'preparation_report.json', report)
    return {'registration': manifest_path, 'report': report}


def build_composite_registration(destination, *, finalization_registration, finalization_acceptance,
                                 context_path, native_executable=None, durable_sequence_claim=False,
                                 fitness_schema_guidance=_UNSELECTED):
    """Prepare the accepted composite pair without claiming accounting ownership."""
    fitness_selection = _fitness_selection(fitness_schema_guidance)
    from source_pair import inspect_finalization
    import continuation_sequence
    from sequence_claim import select
    claim_selection = {}; select(claim_selection, durable_sequence_claim)
    destination = canonical_path(str(destination))
    if destination.exists():
        raise BudgetStop('evaluation preparation directory already exists; never overwrite it')
    source, inherited_pins, phase = inspect_finalization(finalization_registration, finalization_acceptance)
    context_path = canonical_path(str(context_path), exists=True)
    from data_sheets_schema.evaluation_context import load_context
    from data_sheets_schema.profiles import profile_named
    load_context(context_path)
    profile_object = profile_named(source['profile'])
    native_runtime = runtime_snapshot(native_executable or phase['native_runtime']['executable'])
    for key in ('executable','version','context_window','max_output_tokens','effort'):
        if native_runtime[key] != phase['native_runtime'][key]:
            raise BudgetStop('composite evaluator changes the accepted native runtime '+key)
    from audit_controls.registration import native_api_timeout, native_api_force_idle_timeout
    timeout = native_api_timeout(phase)
    if timeout is None or native_api_force_idle_timeout(phase) is not False:
        raise BudgetStop('composite native evaluation requires reviewed bounded API and explicit idle-timeout controls')
    native_runtime.update(api_timeout_ms=timeout, api_force_idle_timeout=False)
    ledger_path = Path(source['finalization']['ledger']['path'])
    ledger = read_json(ledger_path)
    if str(ledger['additional_cap_usd']) != '400' or str(ledger['attempt_cap_usd']) != '5':
        raise BudgetStop('composite predecessor changes the approved allocation/default cap')
    spent = sum((Decimal(str(row['cost_usd'])) for row in ledger['requests']), Decimal(0))
    if spent > Decimal(400):
        raise BudgetStop('composite predecessor exceeds the approved allocation')
    block = deepcopy(phase['budget_sequence'])
    snapshot = destination/'predecessor_state.json'
    state = canonical_path(block['state_path'], exists=True)
    expected_state = continuation_sequence._activation_state(phase,
        Path(source['finalization']['registration']['path']), source['finalization']['registration']['sha256'])
    if continuation_sequence.canonical(read_json(state)) != continuation_sequence.canonical(expected_state):
        raise BudgetStop('accepted finalization is not the exact current sequence owner')
    predecessor = {'stage':'reconciliation', **{key:deepcopy(source['finalization'][key])
        for key in ('registration','result','acceptance','ledger')}, 'state':{'path':str(snapshot),'sha256':sha(state)}}
    block.update(stage='evaluation',predecessor=predecessor)
    manifest = {'kind':'d4d_evaluation_registration','schema_version':2,
        'registered_at':datetime.now(timezone.utc).isoformat(), 'repository':str(ROOT),
        'repository_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'python':sys.executable,'python_identity':{'resolved_path':str(Path(sys.executable).resolve()),
            'sha256':sha(sys.executable),'prefix':str(Path(sys.prefix).resolve())},
        **{key:deepcopy(phase[key]) for key in ('provider_base_url','provider_context_policy','model','profile')},
        'project':source['project'],'method':source['method'],'context_path':str(context_path),
        'rubric_dir':str(ROOT/'data/rubric'),'prompts_dir':str(ROOT/'src/download/prompts'),
        'attempts_dir':str(destination/'attempts'),'evaluation_jobs':[],'pinned_files':inherited_pins,
        'source_pair':source,'budget_sequence':block,
        'budget':{'additional_usd':'400','per_attempt_usd':'5','ledger_path':str(destination/'billing.json'),
            'prices_per_token':deepcopy(phase['budget']['prices_per_token']),
            'continuation':{'checkpoint':str(ledger_path),'sha256':sha(ledger_path),'cost_usd':str(spent)}},
        'conditional_subtype':{'selection':'all_form_failures','status':'deferred_until_all_fitness_results',
            'requires':'exact aggregate evaluation closure and independent acceptance; bounded shared subtype successor'},
        'offline_checks':['schema','pair','duplicate_keys','provenance','receipts','report_grounding',
            'literal_grounding','field_presence_rubric10','field_presence_rubric20'],
        'slot_selection':'every populated schema-known top-level slot of each explicit dataset unit; no propagation'}
    manifest.update(claim_selection)
    manifest.update(fitness_selection)
    if 'provider_transport' in phase:
        manifest['provider_transport'] = deepcopy(phase['provider_transport'])
    verify_implementation(manifest)
    _pin(manifest, context_path, *transport_paths(manifest))
    verified_context(manifest)
    if profile_object.pin_path is not None:
        _pin(manifest, profile_object.pin_path)
    snapshots = _fitness_snapshots(manifest)
    destination.mkdir(parents=True,exist_ok=False)
    with snapshot.open('xb') as stream:
        stream.write(state.read_bytes())
    _pin(manifest,snapshot)
    return _materialize(manifest,destination,Path(source['bundle']['path']),native_runtime,spent,
                        prepared_directory=True, fitness_snapshots=snapshots)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--generation-registration', type=Path)
    parser.add_argument('--generation-acceptance', type=Path)
    parser.add_argument('--generation-job-id')
    parser.add_argument('--context-path', type=Path, required=True)
    parser.add_argument('--billing-checkpoint', type=Path)
    parser.add_argument('--finalization-registration', type=Path)
    parser.add_argument('--finalization-acceptance', type=Path)
    parser.add_argument('--native-executable', type=Path)
    parser.add_argument('--durable-sequence-claim', action='store_true',
        help='require durable ownership evidence for new shared composite evaluations')
    parser.add_argument('--provider-base-url', choices=('https://api.cborg.lbl.gov', 'https://api-local.cborg.lbl.gov'))
    parser.add_argument('--provider-ca-bundle', type=Path,
        help='Explicit pinned CA bundle; required for the direct CBORG endpoint')
    parser.add_argument('--project'); parser.add_argument('--method'); parser.add_argument('--profile')
    parser.add_argument('--fitness-schema-guidance', choices=('nested_semantics_v1',), default=argparse.SUPPRESS,
        help='Explicit new fitness/subtype instrument; requires accepted schema/import authority')
    args = vars(parser.parse_args())
    if args['finalization_registration'] is not None:
        allowed = {'destination','finalization_registration','finalization_acceptance','context_path','native_executable',
                   'durable_sequence_claim','fitness_schema_guidance'}
        if args['finalization_acceptance'] is None or any(v is not None for k,v in args.items() if k not in allowed):
            parser.error('composite preparation requires finalization acceptance and excludes legacy source/provider overrides')
        result = build_composite_registration(**{k:v for k,v in args.items() if k in allowed})
    else:
        if args.pop('durable_sequence_claim'):
            parser.error('durable sequence claims require composite finalization ancestry')
        if args['finalization_acceptance'] is not None or any(args[k] is None for k in
                ('generation_registration','generation_acceptance','generation_job_id','billing_checkpoint')):
            parser.error('legacy preparation requires generation registration, acceptance, job and checkpoint')
        args.pop('finalization_registration'); args.pop('finalization_acceptance')
        result = build_registration(**args)
    print(json.dumps({'registration': str(result['registration']), **result['report']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
