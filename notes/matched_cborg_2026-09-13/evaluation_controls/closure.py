"""Provider-free aggregate closure of every registered primary and repeat rating.

This computes mechanical evidence, never independent scientific acceptance and
never opens a ledger or claims budget ownership. No failed/missing job is omitted.
"""
import argparse
from decimal import Decimal
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
for directory in (HERE, HERE.parent):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
from budgeted_cborg import BudgetStop, attempt_identity, write_new
from evaluation_controls.registration import (canonical_digest, canonical_path, read_json, sha,
    receipt_for, verify_dependencies)
from evaluation_controls.adapter_closure import require_closed


def require(value, reason):
    if not value:
        raise BudgetStop(reason)


def validate_output(manifest, job, output):
    """Reuse each instrument's real exact-file/score contract without a provider."""
    from evaluation_controls import api
    if job['style'] in {'semantic_agent', 'field_agent'}:
        from evaluation_controls.validation import validate_native
        return validate_native(output, job, manifest)
    value = read_json(output)
    expected = read_json(job['expected_request'])
    require(expected == api.render_request(manifest, job), 'aggregate API request differs from its instrument')
    if job['style'] != 'direct_api_quality':
        api.selected_value(job)
        instrument = api.slot_instrument(job)
        require(instrument == job['instrument'], 'aggregate slot instrument changed')
        require(value == {'version': 1, 'job_id': job['id'], 'style': job['style'],
            **{key: job[key] for key in ('input_sha256', 'unit_path', 'slot', 'value_sha256')},
            'instrument': instrument, 'judgement': value.get('judgement')},
            'aggregate slot output identifies a different value or instrument')
        api.validate_slot_json(value['judgement'], job['style'])
    else:
        import yaml
        from data_sheets_schema.evaluation_context import load_context, context_digest, unwrap_document
        from data_sheets_schema.judge_contract import evaluation_contract, validate_result, VERSION
        rubric_path = Path(manifest['rubric_dir']) / (job['rubric'] + '.txt')
        rubric = yaml.safe_load(rubric_path.read_text())
        context = load_context(Path(job['context_path']))
        document = unwrap_document(yaml.safe_load(Path(job['input']).read_text()))
        contract = evaluation_contract(job['rubric'], rubric, context, document)
        validate_result(value, job['rubric'], job['project'], job['method'], contract)
        metadata = value.get('metadata', {})
        checks = {'rubric_hash': sha(rubric_path), 'd4d_file_hash': job['input_sha256'],
            'instrument_kind': 'api_system_prompt', 'instrument_version': VERSION,
            'instrument_sha256': hashlib.sha256(expected['system'].encode()).hexdigest(),
            'request_user_prompt_sha256': hashlib.sha256(expected['messages'][0]['content'].encode()).hexdigest(),
            'context_sha256': context_digest(context), 'model': manifest['model']['model'],
            'response_transport': 'streaming', 'temperature': expected.get('temperature')}
        require(all(metadata.get(key) == wanted for key, wanted in checks.items()),
                'aggregate API quality identity differs from its exact instrument')
        require(value.get('d4d_file') == Path(job['input']).name and
                value.get('model', {}).get('name') == manifest['model']['model'],
                'aggregate API quality names a different input/model')
    return {'passed': True, 'candidate_sha256': sha(output)}


def build_aggregate(manifest, registration_path, ledger=None):
    """Reconstruct the complete closure from actual files; no acceptance implied."""
    registration_path = canonical_path(str(registration_path), exists=True)
    registration_sha = sha(registration_path)
    require(read_json(registration_path) == manifest, 'aggregate registration changed')
    require(manifest.get('schema_version') == 2 and
            manifest.get('budget_sequence', {}).get('stage') == 'evaluation',
            'aggregate closure only follows the initial composite evaluation roster')
    from evaluation_controls.source_pair import validate_roster
    validate_roster(manifest)  # Pure check; avoid recursive sequence admission.
    for name, digest in manifest['pinned_files'].items():
        require(sha(canonical_path(name, exists=True)) == digest, 'aggregate pinned evidence changed')
    ledger_path = canonical_path(manifest['budget']['ledger_path'], exists=True)
    actual = read_json(ledger_path)
    require(ledger is None or ledger == actual, 'aggregate does not name the actual final evaluation ledger')
    ledger = actual
    rows = ledger.get('requests')
    require(ledger.get('manifest_sha256') == registration_sha and isinstance(rows, list) and
            all(row.get('status') == 'settled' for row in rows), 'aggregate has unresolved accounting')
    require(ledger.get('additional_cap_usd') == '400' and ledger.get('attempt_cap_usd') == '5' and
            not ledger.get('attempt_caps_usd'), 'aggregate changed the evaluation allocation or attempt caps')
    identifiers = [row.get('id') for row in rows]
    require(all(isinstance(value, str) and value for value in identifiers) and
            len(identifiers) == len(set(identifiers)), 'aggregate request identities are invalid')
    costs = [Decimal(str(row.get('cost_usd'))) for row in rows]
    require(all(value.is_finite() and value >= 0 for value in costs) and sum(costs) <= 400,
            'aggregate settled accounting is invalid')
    prior = read_json(manifest['budget']['continuation']['checkpoint'])
    require(rows[:len(prior['requests'])] == prior['requests'], 'aggregate lost carried charge history')
    jobs = manifest.get('evaluation_jobs')
    require(isinstance(jobs, list) and bool(jobs) and all(job['style'] != 'subtype' for job in jobs),
            'aggregate initial evaluation roster is empty or already contains subtypes')
    ids = [job['id'] for job in jobs]
    require(len(ids) == len(set(ids)), 'aggregate job identities are duplicated')
    attempts = {attempt_identity(registration_sha, identity) for identity in ids}
    require(all(row.get('attempt') in attempts for row in rows[len(prior['requests']):]),
            'aggregate contains an unregistered evaluation attempt')
    artifacts, completed, selected = {}, [], []
    def bind(name):
        path = canonical_path(str(name), exists=True)
        require(path.is_file() and not path.is_symlink() and path.stat().st_nlink == 1,
                'aggregate artifact is not one ordinary unchanged file')
        artifacts[str(path)] = sha(path)
        return path
    for job in jobs:
        bound, dependencies = verify_dependencies(manifest, registration_sha, job)
        receipt_path, receipt = receipt_for(manifest, registration_sha, job)
        bind(receipt_path); output = bind(job['output']); candidate = bind(job['candidate'])
        require(sha(candidate) == sha(output) == receipt.get('candidate_sha256') and
                receipt.get('candidate') == str(candidate) and receipt.get('unresolved_requests') == [] and
                receipt.get('bound_job_sha256') == canonical_digest(bound) and receipt.get('dependencies') == dependencies and
                receipt.get('validation', {}).get('passed') is True,
                'aggregate job lacks its unchanged successful candidate and dependencies')
        closure_path = bind(Path(manifest['attempts_dir']) / job['id'] / 'adapter_closure.json')
        adapter = require_closed(read_json(closure_path), job['style'])
        require(all(receipt.get('runtime', {}).get(key) == value for key, value in adapter.items()),
                'aggregate receipt contradicts its actual adapter shutdown evidence')
        owned = [row for row in rows if row.get('attempt') == attempt_identity(registration_sha, job['id'])]
        require(bool(owned) and receipt.get('model_requests') == len(owned) and
                receipt.get('model_requests_admitted') == len(owned) and
                Decimal(receipt.get('cost_usd', '-1')) == sum(Decimal(row['cost_usd']) for row in owned),
                'aggregate job request count or charges differ from actual settled ledger')
        if job['style'] not in {'semantic_agent', 'field_agent'}:
            require(len(owned) == 1, 'aggregate API judgement is not one independent request')
            cleanup = bind(closure_path.with_name('client_cleanup.json'))
            require({'owned': True, **read_json(cleanup)} == adapter['client_cleanup'], 'aggregate API cleanup evidence changed')
        validate_output(manifest, bound, output)
        if job['canary']:
            acceptance_path = bind(manifest['canary_acceptances'][job['canary_group']])
            accepted = read_json(acceptance_path)
            require(accepted.get('verdict') == 'accept' and accepted.get('registration_sha256') == registration_sha and
                    accepted.get('job_id') == job['id'] and accepted.get('canary_group') == job['canary_group'] and
                    accepted.get('receipt_sha256') == sha(receipt_path) and accepted.get('output_sha256') == sha(output),
                    'aggregate lacks independent acceptance for a primary canary')
        completed.append({'job_id': job['id'], 'receipt_sha256': sha(receipt_path), 'output_sha256': sha(output),
                          'adapter_closure_sha256': sha(closure_path), 'model_requests': len(owned)})
        if job['style'] == 'fitness':
            value = read_json(output)
            if value['judgement']['failure'] == 'form':
                selected.append({'fitness_job_id': job['id'], 'fitness_result': job['output'],
                    'fitness_result_sha256': sha(output), 'fitness_receipt': str(receipt_path),
                    'fitness_receipt_sha256': sha(receipt_path),
                    **{key: job[key] for key in ('variant', 'class_name', 'input', 'input_sha256', 'unit_path',
                                               'slot', 'value_sha256', 'profile', 'schema_path')},
                    'instrument': value['instrument'], 'judgement': value['judgement']})
    return {'kind': 'd4d_evaluation_aggregate_closure', 'schema_version': 1,
        'scope': 'complete_initial_evaluation_roster', 'status': 'completed_pending_independent_review',
        'registration_sha256': registration_sha, 'roster_sha256': canonical_digest(jobs),
        'source_pair_sha256': canonical_digest(manifest['source_pair']),
        'context_sha256': sha(manifest['context_path']), 'ledger_sha256': sha(ledger_path),
        'settled_requests': len(rows), 'settled_cost_usd': str(sum(costs)), 'unresolved_requests': [],
        'validation': {'passed': True, 'jobs': completed}, 'artifacts': artifacts,
        'subtype_selection': 'all_form_failures', 'selected_form_failures': selected}


def validate_aggregate(manifest, registration_path, closure, ledger):
    expected = build_aggregate(manifest, registration_path, ledger)
    require(canonical_digest(closure) == canonical_digest(expected),
            'aggregate closure omits or changes actual registered evaluation evidence')
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = build_aggregate(read_json(args.registration), args.registration)
    write_new(args.output, value)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
