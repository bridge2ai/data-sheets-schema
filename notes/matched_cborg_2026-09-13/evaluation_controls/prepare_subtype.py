"""Prepare all applicable form subtypes after independent aggregate acceptance.

No provider/token calls, budget activation, acceptance, retry or output repair.
An empty applicable set creates only an offline selection receipt.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
for directory in (HERE, HERE.parent):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
import continuation_sequence as sequence
from budgeted_cborg import BudgetStop, write_new
from evaluation_controls.closure import build_aggregate, require
from evaluation_controls.registration import (canonical_path, canonical_digest, read_json, sha,
    required_paths, verify_manifest)
from evaluation_controls.api import render_request, slot_instrument


def prepare(*, destination, prior_registration, aggregate_result, aggregate_acceptance, durable_sequence_claim=False):
    from sequence_claim import select
    claim_selection = {}; select(claim_selection, durable_sequence_claim)
    destination = canonical_path(str(destination))
    require(not destination.exists(), 'subtype preparation directory already exists')
    prior_path = canonical_path(str(prior_registration), exists=True)
    result_path = canonical_path(str(aggregate_result), exists=True)
    acceptance_path = canonical_path(str(aggregate_acceptance), exists=True)
    previous, closure, acceptance = (read_json(path) for path in (prior_path, result_path, acceptance_path))
    prior_sha = sha(prior_path)
    verify_manifest(previous, prior_path, prior_sha)
    expected = build_aggregate(previous, prior_path)
    require(canonical_digest(closure) == canonical_digest(expected), 'subtype aggregate is incomplete or changed')
    require(acceptance.get('verdict') == 'accept' and acceptance.get('registration_sha256') == prior_sha and
            acceptance.get('result_sha256') == sha(result_path) and
            acceptance.get('ledger_sha256') == closure['ledger_sha256'] and
            acceptance.get('artifacts') == closure['artifacts'],
            'subtype requires independent acceptance of the exact complete evaluation roster')
    state_path = canonical_path(previous['budget_sequence']['state_path'], exists=True)
    state_bytes = state_path.read_bytes()
    state = read_json(state_path)
    require(state == sequence._activation_state(previous, prior_path, prior_sha),
            'subtype predecessor no longer owns the shared budget')
    selected = closure['selected_form_failures']
    selection = {'kind': 'd4d_conditional_subtype_selection', 'schema_version': 1,
        'selection': 'all_form_failures', 'prior_registration': {'path': str(prior_path), 'sha256': prior_sha},
        'aggregate_result': {'path': str(result_path), 'sha256': sha(result_path)},
        'aggregate_acceptance': {'path': str(acceptance_path), 'sha256': sha(acceptance_path)},
        'source_pair_sha256': closure['source_pair_sha256'], 'selected_form_failures': selected,
        'provider_calls': 0, 'token_count_calls': 0, 'budget_activated': False}
    if not selected:
        selection.update(status='not_applicable', reason='All registered fitness judgments completed; none classified a form failure.',
                         paid_registration=None)
        destination.mkdir(parents=True, exist_ok=False)
        write_new(destination / 'selection.json', selection)
        return {'registration': None, 'selection': str(destination / 'selection.json'), 'jobs': 0}
    manifest = deepcopy(previous)
    manifest.pop('sequence_claim', None)
    manifest.update(claim_selection)
    manifest.update(registered_at=datetime.now(timezone.utc).isoformat(), evaluation_jobs=[],
        attempts_dir=str(destination / 'attempts'), subtype_selection='all_form_failures',
        prior_evaluation={'registration': str(prior_path), 'registration_sha256': prior_sha,
            'billing_ledger': previous['budget']['ledger_path'],
            'result': {'path': str(result_path), 'sha256': sha(result_path)},
            'acceptance': {'path': str(acceptance_path), 'sha256': sha(acceptance_path)}},
        canary_acceptances={}, conditional_subtype={'selection': 'all_form_failures', 'status': 'registered_exact_complete_set'})
    manifest.pop('offline_results_dir', None)
    manifest['budget'].update(ledger_path=str(destination / 'billing.json'), per_job_attempt_usd={},
        continuation={'checkpoint': previous['budget']['ledger_path'], 'sha256': closure['ledger_sha256'],
                      'cost_usd': closure['settled_cost_usd']})
    snapshot_path = destination / 'predecessor_state.json'
    manifest['budget_sequence'].update(stage='evaluation_subtype', predecessor={
        'stage': 'evaluation', 'registration': {'path': str(prior_path), 'sha256': prior_sha},
        'ledger': {'path': previous['budget']['ledger_path'], 'sha256': closure['ledger_sha256']},
        'state': {'path': str(snapshot_path), 'sha256': ''},
        'result': {'path': str(result_path), 'sha256': sha(result_path)},
        'acceptance': {'path': str(acceptance_path), 'sha256': sha(acceptance_path)}})
    by_id = {job['id']: job for job in previous['evaluation_jobs']}
    seen_groups = set()
    for row in selected:
        job = deepcopy(by_id[row['fitness_job_id']])
        identity = job['id'] + '_subtype'
        job.update(id=identity, style='subtype', rating=1,
            candidate=str(destination / 'attempts' / identity / 'output/candidate.json'),
            output=str(destination / 'published' / (identity + '.json')),
            expected_request=str(destination / 'requests' / (identity + '.json')),
            fitness_job_id=row['fitness_job_id'], fitness_result=row['fitness_result'],
            fitness_result_sha256=row['fitness_result_sha256'])
        from evaluation_controls.registration import group
        cell = group(job)
        job.update(canary_group=cell, canary=cell not in seen_groups)
        seen_groups.add(cell)
        accepted = str(destination / 'acceptances' / (cell.replace(':', '_') + '.json'))
        manifest['canary_acceptances'][cell] = accepted
        job.pop('canary_acceptance', None)
        if not job['canary']:
            job['canary_acceptance'] = accepted
        job['instrument'] = slot_instrument(job)
        manifest['evaluation_jobs'].append(job)
    manifest['evaluation_jobs'].sort(key=lambda job: (not job['canary'], job['variant'] != 'full', job['id']))
    manifest['planned_execution_order'] = [job['id'] for job in manifest['evaluation_jobs']]
    # Render everything before creating the destination; failures cannot leave
    # a partly rendered registration that resembles a launchable condition.
    requests = {job['id']: render_request(manifest, job) for job in manifest['evaluation_jobs']}
    selection.update(status='applicable', paid_registration=str(destination / 'registration.json'))
    destination.mkdir(parents=True, exist_ok=False)
    with snapshot_path.open('xb') as stream:
        stream.write(state_bytes)
    manifest['budget_sequence']['predecessor']['state']['sha256'] = sha(snapshot_path)
    write_new(destination / 'selection.json', selection)
    pins = manifest['pinned_files']
    for path in (prior_path, result_path, acceptance_path, snapshot_path, destination / 'selection.json',
                 Path(previous['budget']['ledger_path'])):
        pins[str(path)] = sha(path)
    pins.update(closure['artifacts'])
    for job in manifest['evaluation_jobs']:
        path = Path(job['expected_request'])
        write_new(path, requests[job['id']]); pins[str(path)] = sha(path)
    for path in required_paths(manifest):
        pins[str(path)] = sha(path)
    registration = destination / 'registration.json'
    write_new(registration, manifest)
    verify_manifest(manifest, registration, sha(registration))
    require(state_path.read_bytes() == state_bytes and sha(previous['budget']['ledger_path']) == closure['ledger_sha256'],
            'subtype preparation raced with predecessor accounting')
    report = {'provider_calls': 0, 'token_count_calls': 0, 'budget_activated': False,
        'jobs': len(requests), 'sum_of_attempt_caps_usd': str(Decimal('5') * len(requests)),
        'remaining_allocation_usd': str(Decimal('400') - Decimal(closure['settled_cost_usd'])),
        'estimate_basis': 'Attempt-cap exposure, not predicted charge or an admission guarantee.',
        'request_json_bytes': {job['id']: Path(job['expected_request']).stat().st_size for job in manifest['evaluation_jobs']}}
    write_new(destination / 'preparation_report.json', report)
    return {'registration': str(registration), 'selection': str(destination / 'selection.json'), **report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('destination', 'prior-registration', 'aggregate-result', 'aggregate-acceptance'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--durable-sequence-claim', action='store_true',
        help='require durable ownership evidence for this new shared subtype condition')
    prepare(**vars(parser.parse_args()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
