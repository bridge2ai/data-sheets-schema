"""Actual adapter cleanup evidence and common shared-owner lifecycle; offline."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import httpx
import pytest
from filelock import FileLock, Timeout

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import native
import run_evaluation as runner
from evaluation_controls import api, closure
from evaluation_controls.adapter_closure import require_closed
from registration import BudgetStop, read_json, sha
from test_api import setup_job, mock_sdk
from test_native import native_case
from test_provider_transport import native_context, install_verified_mock
from audit_controls.test_transport import certificates
from test_source_pair import composite, build
from budgeted_cborg import attempt_identity, write_new


@pytest.mark.parametrize('style', ['grounding', 'fitness', 'subtype', 'direct_api_quality'])
@pytest.mark.parametrize('kind', ['Dataset', 'CoreDataset'])
def test_actual_api_result_revalidates_with_closed_owned_client(tmp_path, monkeypatch, style, kind):
    context = setup_job(tmp_path, style, kind=kind)
    sdk, calls = mock_sdk(context)
    monkeypatch.setenv('CBORG_API_KEY', 'offline-only')
    monkeypatch.setattr(api, 'provider_clients', lambda *a, **kw: (sdk, None))
    result = api.execute_job(context)
    require_closed(result['runtime'], style)
    assert sdk.is_closed and len(calls) == 2
    assert closure.validate_output(context.manifest, context.job, result['candidate_path'])['passed']
    assert read_json(context.attempt / 'adapter_closure.json')['client_cleanup'] == {'owned':True,'completed':True}


@pytest.mark.parametrize('registered', [False, True])
def test_native_actual_proxy_shutdown_and_registered_timeout_environment(native_case, tmp_path, monkeypatch, certificates, registered):
    from native_controls.test_native_proxy import REQUEST, events, wire
    context = native_context(native_case, tmp_path, monkeypatch, certificates[0])
    if registered:
        context.manifest['schema_version'] = 2
        context.job['native_runtime'].update(api_timeout_ms=10000, api_force_idle_timeout=False)
    monkeypatch.setenv('API_TIMEOUT_MS', '1')
    monkeypatch.setenv('API_FORCE_IDLE_TIMEOUT', 'true')
    def respond(request):
        if request.url.path.endswith('/count_tokens'):
            return httpx.Response(200, json={'input_tokens':100})
        return httpx.Response(200, content=wire(events()), headers={'content-type':'text/event-stream'})
    created, requests = install_verified_mock(monkeypatch, respond)
    def child(argv, **kwargs):
        environment = kwargs['env']
        if registered:
            assert environment['API_TIMEOUT_MS'] == '10000' and environment['API_FORCE_IDLE_TIMEOUT'] == 'false'
        else:
            assert 'API_TIMEOUT_MS' not in environment and 'API_FORCE_IDLE_TIMEOUT' not in environment
        with httpx.Client(trust_env=False) as local:
            response = local.post(environment['ANTHROPIC_BASE_URL'] + '/v1/messages', json=REQUEST,
                                  headers={'x-api-key':kwargs['proxy'].token})
        assert response.status_code == 200
        (tmp_path / 'transcript.jsonl').write_text('')
        return 0
    monkeypatch.setattr(native, 'execute_child', child)
    # Isolate transport/closure; test_native separately uses real child tools
    # and actual semantic/field validators, with no synthetic acceptance here.
    monkeypatch.setattr(native, 'inspect_transcript', lambda *args: {})
    monkeypatch.setattr(native, 'validate_native', lambda *args: {'passed':True})
    result = native.execute_job(context)
    require_closed(result['runtime'], 'semantic_agent')
    assert result['runtime']['unfinished_handlers'] == 0 and created[0].is_closed
    assert len(requests) == 2


@pytest.mark.parametrize('mutation', ['missing_timeout','missing_idle','above_deadline','true_idle'])
def test_composite_native_timeout_refused_before_provider(native_case, tmp_path, monkeypatch, certificates, mutation):
    context = native_context(native_case, tmp_path, monkeypatch, certificates[0])
    context.manifest['schema_version'] = 2
    runtime = context.job['native_runtime']; runtime.update(api_timeout_ms=10000, api_force_idle_timeout=False)
    if mutation == 'missing_timeout': runtime.pop('api_timeout_ms')
    elif mutation == 'missing_idle': runtime.pop('api_force_idle_timeout')
    elif mutation == 'above_deadline': runtime['api_timeout_ms'] = 20001
    else: runtime['api_force_idle_timeout'] = True
    monkeypatch.setattr(native, 'provider_clients', lambda *a, **k: pytest.fail('provider constructed'))
    with pytest.raises(BudgetStop): native.execute_job(context)
    evidence = read_json(tmp_path / 'adapter_closure.json')
    assert evidence['proxy_initialized'] is False and evidence['unfinished_handlers'] is None


def test_actual_composite_common_owner_spans_publication_and_expires(composite, monkeypatch):
    result = build(composite); registration = Path(result['registration'])
    manifest = read_json(registration); job = next(j for j in manifest['evaluation_jobs'] if j['style']=='fitness' and j['canary'])
    review = registration.parent / 'launch_review.json'
    write_new(review, {'verdict':'approve','registration_sha256':sha(registration), 'ci_conclusion':'success',
        'repository_commit':manifest['repository_commit'],'allowed_jobs':[job['id']]})
    source_state = composite['state']; old_ledger = Path(composite['phase']['budget']['ledger_path'])
    old_bytes = old_ledger.read_bytes(); observed=[]
    def adapter(context):
        context.verify(); observed.append(context.ledger.owner)
        with pytest.raises(Timeout):
            with FileLock(str(source_state)+'.lock', timeout=0): pass
        ticket = context.ledger.reserve(attempt_identity(context.manifest_sha256, job['id']), '.02', 'offline')
        context.ledger.settle(ticket, '.01', response_sha256='offline', usage={})
        Path(job['candidate']).write_text('{}\n')
        return {'candidate_path':Path(job['candidate']), 'validation':{'passed':True},
            'runtime':{'adapter':'api','complete_response':True,'request_lifetime_frozen':True,
                'independent_requests':1,'client_cleanup':{'owned':True,'completed':True}}}
    real_write = runner.write_new
    def write(path, value):
        if Path(path).name == 'result.json':
            assert observed[0].active and observed[0].lock.is_locked
        return real_write(path, value)
    monkeypatch.setattr(runner, 'write_new', write)
    receipt = runner.run_job(registration, review, job['id'], adapter=adapter)
    assert receipt['status'] == 'completed_pending_independent_review'
    assert old_ledger.read_bytes() == old_bytes and len(read_json(manifest['budget']['ledger_path'])['requests']) == 3
    assert read_json(source_state)['active_tip']['stage'] == 'evaluation'
    with pytest.raises(BudgetStop): observed[0].verify_admission()
    with pytest.raises(BudgetStop, match='never resume'):
        runner.run_job(registration, review, job['id'], adapter=lambda _: pytest.fail('replayed'))


def test_composite_common_owner_does_not_publish_incomplete_adapter(composite):
    result = build(composite); registration = Path(result['registration']); m = read_json(registration)
    job = next(j for j in m['evaluation_jobs'] if j['style']=='fitness' and j['canary'])
    review = registration.parent / 'launch_review.json'
    write_new(review, {'verdict':'approve','registration_sha256':sha(registration),'ci_conclusion':'success',
        'repository_commit':m['repository_commit'],'allowed_jobs':[job['id']]})
    def adapter(context):
        ticket = context.ledger.reserve(attempt_identity(context.manifest_sha256, job['id']), '.02', 'offline')
        context.ledger.settle(ticket, '.01', response_sha256='offline', usage={})
        Path(job['candidate']).write_text('{}\n')
        return {'candidate_path':Path(job['candidate']),'validation':{'passed':True},
            'runtime':{'adapter':'api','complete_response':True,'request_lifetime_frozen':True,
                       'independent_requests':1,'client_cleanup':{'owned':True,'completed':False}}}
    with pytest.raises(BudgetStop, match='did not close'):
        runner.run_job(registration, review, job['id'], adapter=adapter)
    assert not Path(job['output']).exists()
    receipt = read_json(Path(m['attempts_dir'])/job['id']/'result.json')
    assert receipt['status']=='stopped' and receipt['unresolved_requests']==[]
    assert receipt['runtime']['client_cleanup']['completed'] is False
