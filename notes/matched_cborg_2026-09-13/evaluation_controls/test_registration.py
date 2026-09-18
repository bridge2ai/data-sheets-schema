"""Offline admission/publication probes against the actual shared ledger."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import registration as reg
import run_evaluation as runner
from budgeted_cborg import attempt_identity, write_new

ROOT = HERE.parents[2]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    return path


@pytest.fixture
def registered(tmp_path):
    full, core, context = (tmp_path / name for name in ('full.yaml', 'core.yaml', 'context.json'))
    full.write_text('id: https://example.org/offline-full\n')
    core.write_text('id: https://example.org/offline-core\n')
    context.write_text('{}\n')
    previous_ledger = tmp_path / 'generation_billing.json'
    generation = write(tmp_path / 'generation.json', {'budget': {'ledger_path': str(previous_ledger)}})
    row = {'id': 'prior-offline-request', 'attempt': 'old-generation:one', 'status': 'settled', 'cost_usd': '1.25'}
    write(previous_ledger, {'manifest_sha256': reg.sha(generation), 'additional_cap_usd': '400',
                           'attempt_cap_usd': '5', 'requests': [row]})
    checkpoint = tmp_path / 'checkpoint.json'
    checkpoint.write_bytes(previous_ledger.read_bytes())
    sequence = str(tmp_path.parent / ('sequence-' + tmp_path.name) / 'current.json')
    acceptance = write(tmp_path / 'generation_acceptance.json', {'verdict': 'accept', 'evaluation_sequence_state': sequence,
        'registration_sha256': reg.sha(generation), 'artifacts': {str(p): reg.sha(p) for p in (full, core)}})
    request = write(tmp_path / 'request.json', {'model': 'claude-opus-5', 'max_tokens': 1})
    source = {'registration': str(generation), 'registration_sha256': reg.sha(generation),
        'acceptance': str(acceptance), 'acceptance_sha256': reg.sha(acceptance),
        'billing_ledger': str(previous_ledger), 'billing_sha256': reg.sha(previous_ledger),
        'evaluation_sequence_state': sequence,
        'artifacts': {kind: {'path': str(p), 'sha256': reg.sha(p)} for kind, p in [('full', full), ('core', core)]}}
    first = {'id': 'full_grounding_canary', 'style': 'grounding', 'variant': 'full',
        'class_name': 'Dataset', 'input': str(full), 'input_sha256': reg.sha(full),
        'context_path': str(context), 'project': 'Synthetic', 'method': 'offline',
        'rating': 1, 'canary': True, 'canary_group': 'grounding:full:slots',
        'output': str(tmp_path / 'published/primary.json'),
        'candidate': str(tmp_path / 'attempts/full_grounding_canary/output/candidate.json'),
        'expected_request': str(request), 'deadline_seconds': 30}
    repeat = {**first, 'id': 'full_grounding_repeat', 'rating': 2, 'canary': False,
        'canary_acceptance': str(tmp_path / 'canary_acceptance.json'),
        'output': str(tmp_path / 'published/repeat.json'),
        'candidate': str(tmp_path / 'attempts/full_grounding_repeat/output/candidate.json')}
    manifest = {'kind': 'd4d_evaluation_registration', 'schema_version': 1,
        'repository': str(ROOT), 'repository_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'python': sys.executable, 'python_identity': {'resolved_path': str(Path(sys.executable).resolve()),
                                                    'sha256': reg.sha(sys.executable), 'prefix': str(Path(sys.prefix).resolve())},
        'model': {'model': 'claude-opus-5'},
        'provider_base_url': 'https://api.cborg.lbl.gov', 'source_generation': source,
        'attempts_dir': str(tmp_path / 'attempts'), 'evaluation_jobs': [first, repeat],
        'budget': {'additional_usd': '400', 'per_attempt_usd': '5', 'ledger_path': str(tmp_path / 'billing.json'),
            'continuation': {'checkpoint': str(checkpoint), 'sha256': reg.sha(checkpoint), 'cost_usd': '1.25'}},
        'pinned_files': {str(p): reg.sha(p) for p in (full, core, context, generation, acceptance, checkpoint)}}
    manifest['pinned_files'].update({str(path): reg.sha(path) for path in reg.required_paths(manifest)})
    path, review = tmp_path / 'registration.json', tmp_path / 'review.json'

    def save():
        write(path, manifest)
        write(review, {'verdict': 'approve', 'registration_sha256': reg.sha(path),
            'ci_conclusion': 'success', 'repository_commit': manifest['repository_commit'],
            'allowed_jobs': [row['id'] for row in manifest['evaluation_jobs']]})
        return path, review
    save()
    return manifest, path, review, save


def fake_adapter(context, *, pending=False, change_pin=False):
    """Use real reservation/settlement; no SDK, socket or synthetic scored data."""
    attempt = attempt_identity(context.manifest_sha256, context.job['id'])
    ticket = context.ledger.reserve(attempt, Decimal('0.02'), 'offline-request')
    if not pending:
        context.ledger.settle(ticket, Decimal('0.01'), response_sha256='offline-response', usage={})
    candidate = Path(context.job['candidate'])
    candidate.write_text('{"offline_lifecycle_fixture": true}\n')
    if change_pin:
        Path(context.job['input']).write_text('changed after a paid request\n')
    return {'candidate_path': candidate, 'validation': {'passed': True},
            'runtime': {'offline_fixture': True}, 'evidence': {'provider_calls': 0}}


def test_actual_ledger_carries_once_publishes_exclusively_and_does_not_accept_canary(registered):
    manifest, path, review, _ = registered
    receipt = runner.run_job(path, review, manifest['evaluation_jobs'][0]['id'], adapter=fake_adapter)
    state = reg.read_json(manifest['budget']['ledger_path'])
    assert len(state['requests']) == 2
    assert sum(Decimal(row['cost_usd']) for row in state['requests']) == Decimal('1.26')
    assert receipt['status'] == 'completed_pending_independent_review'
    assert not Path(manifest['evaluation_jobs'][1]['canary_acceptance']).exists()
    assert Path(receipt['output']).read_bytes() == Path(receipt['candidate']).read_bytes()
    with pytest.raises(reg.BudgetStop, match='never resume'):
        runner.run_job(path, review, manifest['evaluation_jobs'][0]['id'], adapter=lambda _: pytest.fail('relaunched'))


def test_repeat_requires_its_own_group_receipt_bound_independent_review(registered):
    manifest, path, review, _ = registered
    first, repeat = manifest['evaluation_jobs']
    runner.run_job(path, review, first['id'], adapter=fake_adapter)
    with pytest.raises(FileNotFoundError):
        runner.run_job(path, review, repeat['id'], adapter=lambda _: pytest.fail('unreviewed repeat'))
    receipt_path = Path(manifest['attempts_dir']) / first['id'] / 'result.json'
    acceptance = {'verdict': 'accept', 'registration_sha256': reg.sha(path), 'job_id': first['id'],
        'canary_group': first['canary_group'], 'receipt_sha256': reg.sha(receipt_path),
        'output_sha256': reg.sha(first['output'])}
    write(Path(repeat['canary_acceptance']), {**acceptance, 'canary_group': 'grounding:core:slots'})
    with pytest.raises(reg.BudgetStop, match='no independent canary'):
        runner.run_job(path, review, repeat['id'], adapter=lambda _: pytest.fail('wrong-group repeat'))
    write(Path(repeat['canary_acceptance']), acceptance)
    runner.run_job(path, review, repeat['id'], adapter=fake_adapter)
    assert len(reg.read_json(manifest['budget']['ledger_path'])['requests']) == 3


@pytest.mark.parametrize('mutation', ['generation_acceptance', 'source_bytes', 'live_billing', 'checkpoint',
                                    'default_cap', 'new_allocation', 'duplicate_job', 'input_variant', 'candidate_escape'])
def test_admission_rejects_changed_inputs_accounting_scope_and_caps_before_adapter(registered, mutation):
    manifest, path, review, save = registered
    job = manifest['evaluation_jobs'][0]
    if mutation == 'generation_acceptance':
        manifest['source_generation']['acceptance_sha256'] = '0' * 64
    elif mutation == 'source_bytes':
        Path(job['input']).write_text('changed')
    elif mutation == 'live_billing':
        Path(manifest['source_generation']['billing_ledger']).write_text('{}')
    elif mutation == 'checkpoint':
        manifest['budget']['continuation']['cost_usd'] = '0'
    elif mutation == 'default_cap':
        manifest['budget']['per_attempt_usd'] = '10'
    elif mutation == 'new_allocation':
        manifest['budget']['additional_usd'] = '401'
    elif mutation == 'duplicate_job':
        manifest['evaluation_jobs'].append(deepcopy(job))
    elif mutation == 'input_variant':
        job['variant'] = 'core'; job['canary_group'] = 'grounding:core:slots'
    elif mutation == 'candidate_escape':
        job['candidate'] = str(path.parent / 'candidate.json')
    save()
    with pytest.raises(reg.BudgetStop):
        runner.run_job(path, review, job['id'], adapter=lambda _: pytest.fail('provider admission reached'))
    assert not Path(manifest['budget']['ledger_path']).exists()


@pytest.mark.parametrize('pending,change_pin', [(True, False), (False, True)])
def test_incomplete_accounting_or_mutation_preserves_candidate_but_never_publishes(registered, pending, change_pin):
    manifest, path, review, _ = registered
    job = manifest['evaluation_jobs'][0]
    with pytest.raises(reg.BudgetStop):
        runner.run_job(path, review, job['id'], adapter=lambda context: fake_adapter(context, pending=pending, change_pin=change_pin))
    assert not Path(job['output']).exists()
    assert Path(job['candidate']).exists()
    receipt = reg.read_json(Path(manifest['attempts_dir']) / job['id'] / 'result.json')
    assert receipt['status'] == 'stopped'
    assert bool(receipt['unresolved_requests']) == pending


def test_default_five_dollar_limit_stops_before_a_request_is_recorded(registered):
    manifest, path, review, _ = registered
    def excessive(context):
        context.ledger.reserve(attempt_identity(context.manifest_sha256, context.job['id']), '5.00000001', 'offline')
        pytest.fail('excessive reservation admitted')
    with pytest.raises(reg.BudgetStop, match='exceeds remaining budget'):
        runner.run_job(path, review, manifest['evaluation_jobs'][0]['id'], adapter=excessive)
    assert len(reg.read_json(manifest['budget']['ledger_path'])['requests']) == 1


@pytest.fixture
def subtype_registration(registered):
    manifest, path, review, save = registered
    parent = manifest['evaluation_jobs'][0]
    parent.update(style='fitness', canary_group='fitness:full:slots', unit_path='$', slot='description',
        value_sha256=reg.canonical_digest('synthetic value'), profile='bridge2ai',
        schema_path=str(ROOT / 'src/data_sheets_schema/schema/data_sheets_schema.yaml'))
    later = {**parent, 'id': 'later_old_generation_job', 'style': 'grounding', 'canary_group': 'grounding:full:slots',
             'output': str(path.parent / 'published/later-old.json'),
             'candidate': str(path.parent / 'attempts/later_old_generation_job/output/candidate.json')}
    manifest['evaluation_jobs'] = [parent, later]
    manifest['pinned_files'][parent['schema_path']] = reg.sha(parent['schema_path'])
    save()
    def fitness_adapter(context):
        result = fake_adapter(context)
        write(result['candidate_path'], {'style': 'fitness', 'job_id': context.job['id'],
            'input_sha256': context.job['input_sha256'], 'unit_path': '$', 'slot': 'description',
            'value_sha256': parent['value_sha256'], 'judgement': {'failure': 'form'}})
        return result
    runner.run_job(path, review, parent['id'], adapter=fitness_adapter)
    parent_sha = reg.sha(path)
    receipt_path = Path(manifest['attempts_dir']) / parent['id'] / 'result.json'
    previous = deepcopy(manifest)
    current = deepcopy(manifest)
    child = {**parent, 'id': 'subtype_primary', 'style': 'subtype', 'canary_group': 'subtype:full:slots',
        'fitness_job_id': parent['id'], 'fitness_result': parent['output'],
        'fitness_result_sha256': reg.sha(parent['output']),
        'candidate': str(path.parent / 'subtype_attempts/subtype_primary/output/candidate.json'),
        'output': str(path.parent / 'published/subtype.json')}
    checkpoint = path.parent / 'evaluation_checkpoint.json'
    checkpoint.write_bytes(Path(previous['budget']['ledger_path']).read_bytes())
    current.update(evaluation_jobs=[child], attempts_dir=str(path.parent / 'subtype_attempts'),
        subtype_selection='all_form_failures', prior_evaluation={'registration': str(path),
            'registration_sha256': parent_sha, 'billing_ledger': previous['budget']['ledger_path']})
    current['budget'].update(ledger_path=str(path.parent / 'subtype_billing.json'),
        continuation={'checkpoint': str(checkpoint), 'sha256': reg.sha(checkpoint), 'cost_usd': '1.26'})
    current['pinned_files'].update({str(p): reg.sha(p) for p in (path, receipt_path, Path(parent['output']), checkpoint)})
    child_path, child_review = path.parent / 'subtype_registration.json', path.parent / 'subtype_review.json'
    def save_child():
        write(child_path, current)
        write(child_review, {'verdict': 'approve', 'registration_sha256': reg.sha(child_path),
            'ci_conclusion': 'success', 'repository_commit': current['repository_commit'], 'allowed_jobs': [child['id']]})
    save_child()
    return current, child_path, child_review, save_child, receipt_path


def test_subtype_subregistration_carries_prior_charges_and_pins_exact_parent(subtype_registration):
    manifest, path, review, _, _ = subtype_registration
    job = manifest['evaluation_jobs'][0]
    bound, dependencies = reg.verify_dependencies(manifest, reg.sha(path), job)
    assert bound['fitness_result_sha256'] == reg.sha(job['fitness_result'])
    assert dependencies['fitness']['registration_sha256'] == manifest['prior_evaluation']['registration_sha256']
    runner.run_job(path, review, job['id'], adapter=fake_adapter)
    state = reg.read_json(manifest['budget']['ledger_path'])
    assert len(state['requests']) == 3
    assert sum(Decimal(row['cost_usd']) for row in state['requests']) == Decimal('1.27')


@pytest.mark.parametrize('mutation', ['stale_checkpoint', 'wrong_receipt_registration', 'wrong_parent_slot', 'wrong_ancestry'])
def test_subtype_rejects_unbound_prior_evidence_before_admission(subtype_registration, mutation):
    manifest, path, review, save, receipt_path = subtype_registration
    if mutation == 'stale_checkpoint':
        ledger = Path(manifest['prior_evaluation']['billing_ledger'])
        ledger.write_text(ledger.read_text() + ' ')
    elif mutation == 'wrong_receipt_registration':
        receipt = reg.read_json(receipt_path); receipt['registration_sha256'] = reg.sha(path)
        write(receipt_path, receipt)
        manifest['pinned_files'][str(receipt_path)] = reg.sha(receipt_path)
    elif mutation == 'wrong_parent_slot':
        manifest['evaluation_jobs'][0]['slot'] = 'name'
    else:
        manifest['source_generation']['billing_sha256'] = '0' * 64
    save()
    with pytest.raises(reg.BudgetStop):
        runner.run_job(path, review, manifest['evaluation_jobs'][0]['id'], adapter=lambda _: pytest.fail('unbound subtype admitted'))
    assert not Path(manifest['budget']['ledger_path']).exists()


def test_separately_reviewed_sibling_cannot_spend_the_same_checkpoint(registered):
    manifest, path, review, _ = registered
    sibling = deepcopy(manifest)
    sibling['attempts_dir'] = str(path.parent / 'sibling_attempts')
    sibling['budget']['ledger_path'] = str(path.parent / 'sibling_billing.json')
    sibling['evaluation_jobs'] = [dict(sibling['evaluation_jobs'][0])]
    job = sibling['evaluation_jobs'][0]
    job['candidate'] = str(Path(sibling['attempts_dir']) / job['id'] / 'output/candidate.json')
    job['output'] = str(path.parent / 'sibling_published/result.json')
    sibling_path = write(path.parent / 'sibling_registration.json', sibling)
    sibling_review = write(path.parent / 'sibling_review.json', {'verdict': 'approve',
        'registration_sha256': reg.sha(sibling_path), 'ci_conclusion': 'success',
        'repository_commit': sibling['repository_commit'], 'allowed_jobs': [job['id']]})
    runner.run_job(path, review, manifest['evaluation_jobs'][0]['id'], adapter=fake_adapter)
    with pytest.raises(reg.BudgetStop, match='another successor'):
        runner.run_job(sibling_path, sibling_review, job['id'], adapter=lambda _: pytest.fail('forked sequence admitted'))
    assert not Path(sibling['budget']['ledger_path']).exists()


def test_predecessor_cannot_launch_more_jobs_after_subtype_handoff(subtype_registration):
    manifest, path, review, _, _ = subtype_registration
    runner.run_job(path, review, manifest['evaluation_jobs'][0]['id'], adapter=fake_adapter)
    prior = Path(manifest['prior_evaluation']['registration'])
    with pytest.raises(reg.BudgetStop, match='predecessor cannot resume'):
        runner.run_job(prior, prior.with_name('review.json'), 'later_old_generation_job',
                       adapter=lambda _: pytest.fail('predecessor resumed after budget handoff'))


@pytest.mark.parametrize('mutation', ['acceptance_path', 'actual_interpreter'])
def test_shared_state_path_and_actual_interpreter_are_bound_before_admission(registered, mutation):
    manifest, path, review, save = registered
    if mutation == 'acceptance_path':
        manifest['source_generation']['evaluation_sequence_state'] = str(path.parent / 'unbound-sequence/current.json')
    else:
        executable = path.parent / 'another-environment/bin/python'
        executable.parent.mkdir(parents=True)
        executable.symlink_to(Path(sys.executable).resolve())
        manifest['python'] = str(executable)
    save()
    with pytest.raises(reg.BudgetStop):
        runner.run_job(path, review, manifest['evaluation_jobs'][0]['id'], adapter=lambda _: pytest.fail('unbound runtime admitted'))


def test_sequence_state_change_during_attempt_blocks_publication(registered):
    manifest, path, review, _ = registered
    def tamper(context):
        result = fake_adapter(context)
        write(reg.sequence_path(context.manifest), {'tip': {'registration_sha256': 'different'}})
        return result
    with pytest.raises(reg.BudgetStop, match='handoff changed'):
        runner.run_job(path, review, manifest['evaluation_jobs'][0]['id'], adapter=tamper)
    assert not Path(manifest['evaluation_jobs'][0]['output']).exists()
