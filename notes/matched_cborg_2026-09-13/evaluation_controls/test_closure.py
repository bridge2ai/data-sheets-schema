"""Real offline SDK/Ledger closures and the bounded third shared handoff."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx
import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import test_continuation_sequence as foundation
import continuation_sequence as sequence
from evaluation_controls import api, closure, prepare_subtype, source_pair
from evaluation_controls.adapter_closure import require_closed
from evaluation_controls.run_evaluation import OwnedLedger
from evaluation_controls.registration import BudgetStop, canonical_digest, read_json, sha
from test_api import setup_job, mock_sdk
from budgeted_cborg import attempt_identity, write_new


def completed_evaluation(tmp_path, monkeypatch, *, form=True, amended=False):
    """Synthetic source ancestry; actual requests, scoring library and billing."""
    # The source/complete scientific roster is covered by test_source_pair.
    # Here two actual API jobs isolate the accounting and closure boundaries.
    monkeypatch.setattr(source_pair, 'validate_roster', lambda manifest: None)
    m, r, state = foundation.fixture(tmp_path, cost='410' if amended else '2.1', amended=amended)
    with foundation.enter(m, r):
        pass
    e, er = foundation.evaluation_successor(m, r, state)
    contexts = []
    for variant, kind in (('full', 'Dataset'), ('core', 'CoreDataset')):
        directory = tmp_path / ('api-' + variant); directory.mkdir()
        context = setup_job(directory, 'fitness', kind=kind)
        job = context.job
        job.pop('rubric')
        job.update(id=variant + '_fitness', variant=variant, rating=1, canary=True,
                   canary_group='fitness:' + variant + ':slots')
        job['candidate'] = str(er.parent / 'attempts' / job['id'] / 'output/candidate.json')
        job['output'] = str(er.parent / 'published' / (job['id'] + '.json'))
        contexts.append(context)
    e.update(kind='d4d_evaluation_registration', schema_version=2,
        evaluation_jobs=[c.job for c in contexts], attempts_dir=str(er.parent / 'attempts'),
        source_pair={'kind': 'synthetic_source_for_accounting_fixture'},
        context_path=contexts[0].job['context_path'], canary_acceptances={},
        model=contexts[0].manifest['model'])
    if amended:
        e['source_pair']['original_generation']={'registration':e['budget_sequence']['origin']['registration']}
    e['budget']['prices_per_token'] = contexts[0].manifest['budget']['prices_per_token']
    for context in contexts:
        cell = context.job['canary_group']
        e['canary_acceptances'][cell] = str(er.parent / 'acceptances' / (cell.replace(':', '_') + '.json'))
        for name in ('input', 'context_path', 'expected_request', 'schema_path'):
            e['pinned_files'][context.job[name]] = sha(context.job[name])
    for path in (Path(closure.__file__), Path(sequence.__file__)):
        e['pinned_files'][str(path)] = sha(path)
    foundation.finish_registration(e, er)
    monkeypatch.setenv('CBORG_API_KEY', 'offline-only')
    for context in contexts:
        job = context.job
        context.manifest = e; context.manifest_sha256 = sha(er)
        context.attempt = Path(e['attempts_dir']) / job['id']; context.attempt.mkdir(parents=True)
        sdk, calls = mock_sdk(context)
        original_handler = sdk._client._transport.handler
        if form:
            def handler(request, original=original_handler):
                response = original(request)
                if request.url.path.endswith('/messages'):
                    # Actual synthetic SSE reaches the real library and ledger.
                    content = response.content.replace(b'\\"failure\\": \\"none\\"', b'\\"failure\\": \\"form\\"')
                    response = httpx.Response(200, content=content, headers={'content-type':'text/event-stream'})
                return response
            sdk._client._transport.handler = handler
        monkeypatch.setattr(api, 'provider_clients', lambda *a, sdk=sdk, **kw: (sdk, None))
        with foundation.enter(e, er) as owner:
            context.ledger = OwnedLedger(owner); context.verify = owner.verify_admission
            result = api.execute_job(context)
        assert sdk.is_closed and len(calls) == 2
        candidate = Path(job['candidate']); output = Path(job['output'])
        output.parent.mkdir(exist_ok=True); output.write_bytes(candidate.read_bytes())
        rows = [row for row in read_json(e['budget']['ledger_path'])['requests']
                if row['attempt'] == attempt_identity(sha(er), job['id'])]
        receipt = {'status':'completed_pending_independent_review', 'registration_sha256':sha(er),
            'job_id':job['id'], 'registered_job_sha256':canonical_digest(job),
            'bound_job_sha256':canonical_digest(job), 'dependencies':{}, 'candidate':str(candidate),
            'candidate_sha256':sha(candidate), 'output':str(output), 'output_sha256':sha(output),
            'unresolved_requests':[], 'runtime':result['runtime'], 'validation':result['validation'],
            'model_requests':len(rows), 'model_requests_admitted':len(rows),
            'cost_usd':str(sum(Decimal(row['cost_usd']) for row in rows))}
        receipt_path = context.attempt / 'result.json'; write_new(receipt_path, receipt)
        write_new(Path(e['canary_acceptances'][job['canary_group']]), {'verdict':'accept',
            'registration_sha256':sha(er), 'job_id':job['id'], 'canary_group':job['canary_group'],
            'receipt_sha256':sha(receipt_path), 'output_sha256':sha(output)})
    return e, er, state


def test_amended_aggregate_and_subtype_keep_effective_cap_and_history(tmp_path, monkeypatch):
    e, er, state = completed_evaluation(tmp_path, monkeypatch, amended=True)
    proof=e['budget_amendment']
    before={Path(proof[k]['path']):Path(proof[k]['path']).read_bytes()
            for k in ('origin_registration','predecessor_registration','predecessor_ledger','predecessor_owner','authorization')}
    result=closure.build_aggregate(e,er)
    assert Decimal(result['settled_cost_usd']) > 400
    assert closure.validate_aggregate(e,er,result,read_json(e['budget']['ledger_path']))==result
    args=prepare_from_fixture(e,er,state,tmp_path,monkeypatch)
    owner_before=state.read_bytes(); ledger_before=Path(e['budget']['ledger_path']).read_bytes()
    prepared=prepare_subtype.prepare(**args)
    subtype=read_json(prepared['registration'])
    assert subtype['budget_amendment']==proof
    assert subtype['budget']['additional_usd']=='500' and subtype['budget']['per_attempt_usd']=='5'
    assert Decimal(prepared['remaining_allocation_usd'])==Decimal(500)-Decimal(result['settled_cost_usd'])
    assert state.read_bytes()==owner_before and Path(e['budget']['ledger_path']).read_bytes()==ledger_before
    with foundation.enter(subtype,Path(prepared['registration'])) as owner:
        ledger=read_json(owner.ledger.path)
        assert ledger['additional_cap_usd']=='500'
        assert ledger['requests']==read_json(e['budget']['ledger_path'])['requests']
    assert all(p.read_bytes()==raw for p,raw in before.items())
    with pytest.raises(BudgetStop):
        with foundation.enter(e,er): pass


def test_amended_aggregate_still_refuses_cost_above_authorized_cap(tmp_path, monkeypatch):
    e,er,_=completed_evaluation(tmp_path,monkeypatch,amended=True)
    ledger=read_json(e['budget']['ledger_path'])
    ledger['requests'][-1]['cost_usd']='501'
    foundation.save(Path(e['budget']['ledger_path']),ledger)
    with pytest.raises(BudgetStop,match='aggregate settled accounting is invalid'):
        closure.build_aggregate(e,er)


def test_amended_closed_aggregate_rejects_boolean_history_changed_to_number(tmp_path,monkeypatch):
    e,er,_=completed_evaluation(tmp_path,monkeypatch,amended=True)
    assert closure.build_aggregate(e,er)['validation']['passed'] is True
    ledger=read_json(e['budget']['ledger_path'])
    assert ledger['requests'][0]['provider_charge_confirmed'] is False
    ledger['requests'][0]['provider_charge_confirmed']=0
    foundation.save(Path(e['budget']['ledger_path']),ledger)
    # Python container equality considers False and 0 equal. Frozen accounting
    # evidence must retain their distinct JSON types even after owner shutdown.
    with pytest.raises(BudgetStop,match='aggregate lost carried charge history'):
        closure.build_aggregate(e,er)


def test_complete_actual_api_results_and_cleanup_aggregate(tmp_path, monkeypatch):
    e, er, state = completed_evaluation(tmp_path, monkeypatch)
    before = {path:Path(path).read_bytes() for path in (str(state), e['budget']['ledger_path'])}
    result = closure.build_aggregate(e, er)
    assert len(result['validation']['jobs']) == 2
    assert len(result['selected_form_failures']) == 2
    assert result['settled_requests'] == 3
    assert closure.validate_aggregate(e, er, result, read_json(e['budget']['ledger_path'])) == result
    assert {path:Path(path).read_bytes() for path in before} == before


@pytest.mark.parametrize('defect', ['missing_job','missing_canary','unfinished_client','unknown_native_shutdown',
                                  'pending_request','changed_candidate','wrong_count','wrong_instrument','omitted_result'])
def test_incomplete_or_misbound_aggregate_refused(tmp_path, monkeypatch, defect):
    e, er, _ = completed_evaluation(tmp_path, monkeypatch)
    job = e['evaluation_jobs'][0]
    receipt_path = Path(e['attempts_dir']) / job['id'] / 'result.json'
    if defect == 'missing_job': receipt_path.unlink()
    elif defect == 'missing_canary': Path(e['canary_acceptances'][job['canary_group']]).unlink()
    elif defect in ('unfinished_client', 'unknown_native_shutdown'):
        path = receipt_path.with_name('adapter_closure.json'); value = read_json(path)
        if defect == 'unfinished_client': value['client_cleanup']['completed'] = False
        else: value = {'adapter':'native','exit_code':0,'proxy_initialized':True,
                       'proxy_shutdown_complete':True,'unfinished_handlers':None}
        foundation.save(path, value)
    elif defect == 'pending_request':
        path = Path(e['budget']['ledger_path']); value = read_json(path)
        value['requests'][-1]['status'] = 'pending'; foundation.save(path, value)
    elif defect == 'changed_candidate': Path(job['candidate']).write_text('{}')
    elif defect == 'wrong_count':
        value = read_json(receipt_path); value['model_requests'] = 50; foundation.save(receipt_path, value)
    elif defect == 'wrong_instrument': Path(job['expected_request']).write_text('{}')
    else:
        value = closure.build_aggregate(e, er); value['validation']['jobs'].pop()
        with pytest.raises(BudgetStop): closure.validate_aggregate(e, er, value, read_json(e['budget']['ledger_path']))
        return
    with pytest.raises((BudgetStop, OSError, ValueError)):
        closure.build_aggregate(e, er)


def subtype_successor(e, er, state, root):
    aggregate = closure.build_aggregate(e, er)
    result = foundation.save(root / 'aggregate.json', aggregate)
    ledger = {'path':e['budget']['ledger_path'], 'sha256':sha(e['budget']['ledger_path'])}
    accepted = foundation.save(root / 'aggregate_acceptance.json', {'verdict':'accept',
        'registration_sha256':sha(er),'result_sha256':result['sha256'],
        'ledger_sha256':ledger['sha256'],'artifacts':aggregate['artifacts']})
    snapshot = foundation.save(root / 'evaluation_state.json', read_json(state))
    s = deepcopy(e); sr = root / 'subtype/registration.json'
    s['budget_sequence'].update(stage='evaluation_subtype', predecessor={
        'stage':'evaluation','registration':{'path':str(er),'sha256':sha(er)},
        'ledger':ledger,'state':snapshot,'result':result,'acceptance':accepted})
    s['evaluation_jobs'] = [{'id':'full_subtype'}, {'id':'core_subtype'}]
    s['budget'].update(ledger_path=str(sr.parent / 'billing.json'), continuation={
        'checkpoint':ledger['path'],'sha256':ledger['sha256'],'cost_usd':aggregate['settled_cost_usd']})
    s['pinned_files'].update(aggregate['artifacts'])
    for ref in s['budget_sequence']['predecessor'].values():
        if isinstance(ref, dict): s['pinned_files'][ref['path']] = ref['sha256']
    foundation.finish_registration(s, sr)
    return s, sr, result, accepted


def test_actual_third_transfer_preserves_all_costs_and_seals_ancestors(tmp_path, monkeypatch):
    e, er, state = completed_evaluation(tmp_path, monkeypatch)
    s, sr, _, _ = subtype_successor(e, er, state, tmp_path)
    prefix = read_json(e['budget']['ledger_path'])['requests']
    for job in ('full_subtype', 'core_subtype'):
        with foundation.enter(s, sr) as owner:
            ticket = owner.reserve(sha(sr) + ':' + job, '.01', 'synthetic subtype')
            owner.ledger.settle(ticket, '.01', response_sha256='retained', usage={})
    actual = read_json(s['budget']['ledger_path'])
    assert actual['requests'][:len(prefix)] == prefix and len(actual['requests']) == len(prefix) + 2
    assert len(read_json(state)['transfers']) == 3
    with pytest.raises(BudgetStop):
        with foundation.enter(e, er): pass
    fourth = deepcopy(s); fr = tmp_path / 'fourth/registration.json'
    fourth['budget_sequence']['predecessor']['stage'] = 'evaluation_subtype'
    fourth['budget']['ledger_path'] = str(fr.parent / 'billing.json')
    foundation.finish_registration(fourth, fr)
    with pytest.raises(BudgetStop):
        with foundation.enter(fourth, fr): pass
    assert not Path(fourth['budget']['ledger_path']).exists()


def test_aggregate_acceptance_omission_cannot_activate_third_owner(tmp_path, monkeypatch):
    e, er, state = completed_evaluation(tmp_path, monkeypatch)
    s, sr, _, accepted = subtype_successor(e, er, state, tmp_path)
    value = read_json(accepted['path']); value['artifacts'].pop(next(iter(value['artifacts'])))
    foundation.repin(s, s['budget_sequence']['predecessor']['acceptance'], value)
    foundation.finish_registration(s, sr); before = state.read_bytes()
    with pytest.raises(BudgetStop):
        with foundation.enter(s, sr): pass
    assert state.read_bytes() == before and not Path(s['budget']['ledger_path']).exists()


@pytest.mark.parametrize('native', [False, True])
def test_closure_does_not_coerce_boolean_request_counts(native):
    runtime = {'adapter':'native','exit_code':False,'proxy_initialized':True,
               'proxy_shutdown_complete':True,'unfinished_handlers':0} if native else {
        'adapter':'api','complete_response':True,'request_lifetime_frozen':True,
        'independent_requests':True,'client_cleanup':{'owned':True,'completed':True}}
    with pytest.raises(BudgetStop): require_closed(runtime, 'semantic_agent' if native else 'fitness')


def prepare_from_fixture(e, er, state, root, monkeypatch):
    s, sr, result, accepted = subtype_successor(e, er, state, root)
    # This fixture isolates preparation/actual subtype renderers from the full
    # source roster. Source/prep tests cover committed-code and pair admission.
    monkeypatch.setattr(prepare_subtype, 'verify_manifest',
        lambda m, p, d: sequence._validate(m, Path(p), d))
    monkeypatch.setattr(prepare_subtype, 'required_paths', lambda m: [])
    monkeypatch.setattr(api, 'provider_clients', lambda *a, **kw: pytest.fail('provider constructed during preparation'))
    return {'destination':root / 'prepared-subtypes','prior_registration':er,
            'aggregate_result':Path(result['path']),'aggregate_acceptance':Path(accepted['path'])}


@pytest.mark.parametrize('durable', [False, True])
def test_subtype_preparation_preserves_all_fitness_reasons_without_spending(tmp_path, monkeypatch, durable):
    import sequence_claim
    e, er, state = completed_evaluation(tmp_path, monkeypatch)
    args = prepare_from_fixture(e, er, state, tmp_path, monkeypatch)
    before = state.read_bytes(), Path(e['budget']['ledger_path']).read_bytes()
    if durable:
        # Keep this fixture's narrowed implementation closure, including the
        # selected helper; full closure pinning is covered by composite prep.
        monkeypatch.setattr(prepare_subtype, 'required_paths', lambda m: sequence_claim.IMPLEMENTATIONS)
    result = prepare_subtype.prepare(**args, durable_sequence_claim=durable)
    m = read_json(result['registration'])
    assert sequence_claim.enabled(m) is durable
    assert result['jobs'] == 2 and result['provider_calls'] == result['token_count_calls'] == 0
    assert m['source_pair'] == e['source_pair']
    assert m['budget_sequence']['stage'] == 'evaluation_subtype'
    assert m['budget']['continuation']['checkpoint'] == e['budget']['ledger_path']
    assert {job['fitness_job_id'] for job in m['evaluation_jobs']} == {job['id'] for job in e['evaluation_jobs']}
    for job in m['evaluation_jobs']:
        request = read_json(job['expected_request'])
        assert request == api.render_request(m, job)
        assert 'Appropriate description.' in json.dumps(request)
        assert job['canary']
    assert before == (state.read_bytes(), Path(e['budget']['ledger_path']).read_bytes())
    assert not Path(m['budget']['ledger_path']).exists()
    with foundation.enter(m, Path(result['registration'])) as owner:
        assert len(read_json(owner.ledger.path)['requests']) == 3
        if durable:
            assert (Path(result['registration']).parent/'sequence_claim/owner.json').read_bytes() == state.read_bytes()
    with pytest.raises(BudgetStop):
        with foundation.enter(e, er): pass


def test_no_form_failures_creates_offline_noop_without_paid_registration(tmp_path, monkeypatch):
    e, er, state = completed_evaluation(tmp_path, monkeypatch, form=False)
    args = prepare_from_fixture(e, er, state, tmp_path, monkeypatch)
    before = state.read_bytes(), Path(e['budget']['ledger_path']).read_bytes()
    result = prepare_subtype.prepare(**args)
    selection = read_json(result['selection'])
    assert selection['status'] == 'not_applicable' and selection['selected_form_failures'] == []
    assert result['registration'] is None and result['jobs'] == 0
    assert list(args['destination'].iterdir()) == [Path(result['selection'])]
    assert before == (state.read_bytes(), Path(e['budget']['ledger_path']).read_bytes())


@pytest.mark.parametrize('defect', ['not_accepted','omitted_form_failure','changed_reason'])
def test_subtype_preparation_refuses_incomplete_or_changed_fitness_closure(tmp_path, monkeypatch, defect):
    e, er, state = completed_evaluation(tmp_path, monkeypatch)
    args = prepare_from_fixture(e, er, state, tmp_path, monkeypatch)
    if defect == 'not_accepted':
        path = args['aggregate_acceptance']; value = read_json(path); value['verdict'] = 'pending'
    else:
        path = args['aggregate_result']; value = read_json(path)
        if defect == 'omitted_form_failure': value['selected_form_failures'].pop()
        else: value['selected_form_failures'][0]['judgement']['reason'] = 'Different unsupported explanation.'
    foundation.save(path, value)
    with pytest.raises(BudgetStop): prepare_subtype.prepare(**args)
    assert not args['destination'].exists()


def test_third_transfer_rejects_sibling_alias_and_changed_history(tmp_path, monkeypatch):
    e, er, state = completed_evaluation(tmp_path, monkeypatch)
    s, sr, _, _ = subtype_successor(e, er, state, tmp_path)
    with foundation.enter(s, sr): pass
    original = state.read_bytes()
    sibling = deepcopy(s); sibling_path = tmp_path / 'sibling-subtypes/registration.json'
    sibling['budget']['ledger_path'] = str(sibling_path.parent / 'billing.json')
    foundation.finish_registration(sibling, sibling_path)
    with pytest.raises(BudgetStop):
        with foundation.enter(sibling, sibling_path): pass
    assert not Path(sibling['budget']['ledger_path']).exists()
    prior = read_json(e['budget_sequence']['predecessor']['registration']['path'])
    prior_path = Path(e['budget_sequence']['predecessor']['registration']['path'])
    with pytest.raises(BudgetStop):
        with foundation.enter(prior, prior_path): pass
    mutated = read_json(state); mutated['transfers'].pop(0); foundation.save(state, mutated)
    with pytest.raises(BudgetStop):
        with foundation.enter(s, sr): pass
    state.write_bytes(original)
    alias = tmp_path / 'state-alias.json'; alias.symlink_to(state)
    sibling['budget_sequence']['state_path'] = str(alias)
    foundation.finish_registration(sibling, sibling_path)
    with pytest.raises(BudgetStop):
        with foundation.enter(sibling, sibling_path): pass
    assert state.read_bytes() == original
