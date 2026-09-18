"""Evaluation wiring to the reviewed TLS factory; synthetic data and no provider."""
import json
from pathlib import Path
import ssl
import sys
from types import SimpleNamespace

import httpx
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native
import prepare_evaluation as prepare
from registration import BudgetStop, read_json, required_paths, sha, verify_manifest
from audit_controls import transport
from audit_controls.test_transport import certificates
from budgeted_cborg import Ledger
from instructions import render_instruction
from test_api import api, mock_sdk, setup_job
from test_native import native_case
from test_prepare_evaluation import accepted_fixture


def install_verified_mock(monkeypatch, responder):
    """Keep the real SDK/client options; replace only the network transport."""
    created, requests = [], []
    real_client = httpx.Client
    def respond(request):
        requests.append(request)
        assert request.url.host == 'api-local.cborg.lbl.gov'
        assert request.headers['x-api-key'] == 'offline-key'
        assert request.headers['x-headroom-bypass'] == 'true'
        return responder(request)
    def factory(**kwargs):
        assert kwargs['trust_env'] is False and kwargs['follow_redirects'] is False
        assert kwargs['verify'].verify_mode == ssl.CERT_REQUIRED
        assert kwargs['verify'].check_hostname is True
        assert not kwargs['verify'].verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN
        assert kwargs['timeout'].read == 1800 and kwargs['timeout'].connect == 20
        client = real_client(transport=httpx.MockTransport(respond), **kwargs)
        created.append(client)
        return client
    monkeypatch.setattr(transport, 'Client', factory)
    monkeypatch.setenv('CBORG_API_KEY', 'offline-key')
    for key in ('HTTPS_PROXY', 'ALL_PROXY', 'SSL_CERT_FILE', 'SSL_CERT_DIR',
                'ANTHROPIC_BASE_URL', 'ANTHROPIC_API_KEY'):
        monkeypatch.setenv(key, 'https://ambient.invalid')
    return created, requests


@pytest.mark.parametrize('style', ['grounding', 'fitness', 'subtype', 'direct_api_quality'])
@pytest.mark.parametrize('kind', ['Dataset', 'CoreDataset'])
def test_every_api_evaluator_counts_and_streams_through_registered_tls(tmp_path, monkeypatch, certificates, style, kind):
    context = setup_job(tmp_path, style, kind=kind)
    context.manifest.update(certificates[0])
    # Reuse the existing instrument-correct response fixture; the production
    # SDK below is freshly constructed through provider_clients, not injected.
    fixture_sdk, _ = mock_sdk(context)
    responder = fixture_sdk._client._transport.handler
    fixture_sdk.close()
    created, requests = install_verified_mock(monkeypatch, responder)
    result = api.execute_job(context)
    assert result['validation']['passed']
    assert len(created) == 1 and created[0].is_closed
    assert [request.url.path for request in requests] == ['/v1/messages/count_tokens', '/v1/messages']
    assert json.loads(requests[1].content)['stream'] is True
    sent = json.loads(requests[1].content); sent.pop('stream')
    assert sent == read_json(context.job['expected_request'])
    row, = read_json(context.ledger.path)['requests']
    assert row['status'] == 'settled'


def native_context(native_case, tmp_path, monkeypatch, trust, style='semantic_agent'):
    _, job, manifest, _, _, _ = native_case('rubric10', style)
    manifest.update(trust)
    # update() above replaces the pins; restore the exact native inputs too.
    manifest['pinned_files'] = dict(trust['pinned_files'])
    manifest.update(provider_context_policy='headroom_bypass_v1', budget={'prices_per_token': {
        'input': '0.000005', 'output': '0.000025', 'cache_read': '0.0000005', 'cache_write': '0.00000625'}})
    for key in ('input', 'context_path', 'agent_definition', 'rubric_file', 'instruction'):
        manifest['pinned_files'][job[key]] = sha(job[key])
    instruction = render_instruction(manifest, job)
    Path(job['instruction']).write_text(instruction)
    manifest['pinned_files'][job['instruction']] = sha(job['instruction'])
    executable = str(Path(sys.executable).resolve())
    job['native_runtime'].update(executable=executable, cli_flags=native.CLI_FLAGS, environment=native.ENVIRONMENT,
        additional_directories=native.additional_directories(manifest, job))
    manifest['pinned_files'][executable] = sha(executable)
    job['deadline_seconds'] = 20
    import data_sheets_schema.agent_pin as agent_pin
    monkeypatch.setattr(agent_pin, 'spawn_preamble', lambda name: instruction.split('\nEvaluate exactly')[0])
    monkeypatch.setattr(native.subprocess, 'check_output', lambda *a, **kw: '2.1.272 (Claude Code)\n')
    def verify():
        for filename, digest in manifest['pinned_files'].items():
            assert sha(filename) == digest
    ledger = Ledger(tmp_path / 'billing.json', manifest_sha256='registered', total_cap=400, attempt_cap=5)
    return SimpleNamespace(manifest=manifest, manifest_sha256='registered', job=job, attempt=tmp_path,
                           ledger=ledger, verify=verify)


@pytest.mark.parametrize('style', ['semantic_agent', 'field_agent'])
def test_native_evaluators_use_one_verified_client_for_count_and_raw_stream(native_case, tmp_path, monkeypatch, certificates, style):
    from native_controls.test_native_proxy import REQUEST, events, wire
    context = native_context(native_case, tmp_path, monkeypatch, certificates[0], style)
    def respond(request):
        if request.url.path.endswith('/count_tokens'):
            return httpx.Response(200, json={'input_tokens': 100})
        assert json.loads(request.content) == REQUEST
        return httpx.Response(200, content=wire(events()), headers={'content-type': 'text/event-stream'})
    created, requests = install_verified_mock(monkeypatch, respond)
    proxies = []
    real_proxy = native.NativeProxy
    def proxy(**kwargs):
        assert kwargs['sdk']._client is kwargs['upstream'] is created[0]
        assert kwargs['sdk'].max_retries == 0
        value = real_proxy(**kwargs); proxies.append(value)
        return value
    monkeypatch.setattr(native, 'NativeProxy', proxy)
    def child(argv, **kwargs):
        assert kwargs['env']['ANTHROPIC_API_KEY'] == kwargs['proxy'].token
        assert 'HTTPS_PROXY' not in kwargs['env'] and 'SSL_CERT_FILE' not in kwargs['env']
        with httpx.Client(trust_env=False) as local:
            response = local.post(kwargs['env']['ANTHROPIC_BASE_URL'] + '/v1/messages',
                                  json=REQUEST, headers={'x-api-key': kwargs['proxy'].token})
        assert response.status_code == 200 and response.content == wire(events())
        (tmp_path / 'transcript.jsonl').write_text('')
        return 0
    monkeypatch.setattr(native, 'execute_child', child)
    # This test isolates transport; real-child validator acceptance remains in
    # test_native.py. No fabricated validation is written to an attempt file.
    monkeypatch.setattr(native, 'inspect_transcript', lambda *args: {})
    monkeypatch.setattr(native, 'validate_native', lambda *args: {'passed': True})
    result = native.execute_job(context)
    assert result['runtime']['effort'] == 'native_default'
    assert len(created) == 1 and created[0].is_closed and proxies[0].frozen
    assert [request.url.path for request in requests] == ['/v1/messages/count_tokens', '/v1/messages']
    row, = read_json(context.ledger.path)['requests']
    assert row['status'] == 'settled'


def test_native_setup_failure_closes_owned_shared_transport(native_case, tmp_path, monkeypatch, certificates):
    context = native_context(native_case, tmp_path, monkeypatch, certificates[0])
    created, requests = install_verified_mock(monkeypatch, lambda r: pytest.fail('unexpected request'))
    def fail(**kwargs):
        raise RuntimeError('synthetic constructor failure')
    monkeypatch.setattr(native, 'NativeProxy', fail)
    with pytest.raises(RuntimeError, match='constructor failure'):
        native.execute_job(context)
    assert len(created) == 1 and created[0].is_closed and not requests
    assert not context.ledger.path.exists()


def test_api_setup_failure_closes_owned_shared_transport(tmp_path, monkeypatch, certificates):
    context = setup_job(tmp_path)
    context.manifest.update(certificates[0])
    created, requests = install_verified_mock(monkeypatch, lambda r: pytest.fail('unexpected request'))
    def fail(*args, **kwargs):
        raise RuntimeError('synthetic capped-client setup failure')
    monkeypatch.setattr(api, 'CappedClient', fail)
    with pytest.raises(RuntimeError, match='setup failure'):
        api.execute_job(context)
    assert len(created) == 1 and created[0].is_closed and not requests
    assert read_json(context.attempt / 'client_cleanup.json') == {'completed': True}
    assert not context.ledger.path.exists()


@pytest.mark.parametrize('adapter', ['api', 'native'])
@pytest.mark.parametrize('defect', ['missing_ca', 'missing_pin', 'changed_ca'])
def test_adapter_rejects_invalid_trust_before_any_http_client(native_case, tmp_path, monkeypatch, certificates, adapter, defect):
    if adapter == 'api':
        context = setup_job(tmp_path)
        context.manifest.update(certificates[0])
        execute = api.execute_job
    else:
        context = native_context(native_case, tmp_path, monkeypatch, certificates[0])
        execute = native.execute_job
    if defect == 'missing_ca':
        context.manifest.pop('provider_transport')
    elif defect == 'missing_pin':
        context.manifest['pinned_files'].pop(str(certificates[1]))
    else:
        certificates[1].write_bytes(certificates[1].read_bytes() + b'\n')
    # Isolate the factory's own refusal in addition to the real registration
    # pin check above; no provider construction can be hidden by a stub verifier.
    context.verify = lambda: None
    monkeypatch.setenv('CBORG_API_KEY', 'offline-key')
    monkeypatch.setattr(transport, 'Client', lambda **kw: pytest.fail('unverified client constructed'))
    with pytest.raises(BudgetStop):
        execute(context)
    assert not context.ledger.path.exists()


def test_preparation_pins_direct_trust_and_shared_implementation_without_provider(accepted_fixture, certificates):
    ca = certificates[1]
    result = prepare.build_registration(**accepted_fixture,
        provider_base_url='https://api-local.cborg.lbl.gov', provider_ca_bundle=ca)
    manifest = read_json(result['registration'])
    assert manifest['provider_transport'] == {'kind': 'pinned_ca_v1', 'ca_bundle': str(ca)}
    assert manifest['pinned_files'][str(ca)] == sha(ca)
    required = required_paths(manifest)
    for name in ('transport.py', 'registration.py', '__init__.py'):
        path = HERE.parent / 'audit_controls' / name
        assert path in required and manifest['pinned_files'][str(path)] == sha(path)
    assert ca in required
    assert result['report']['provider_calls'] == result['report']['token_count_calls'] == 0
    ca.write_bytes(ca.read_bytes() + b'\n')
    with pytest.raises(BudgetStop, match='changed'):
        verify_manifest(manifest, result['registration'], sha(result['registration']))


@pytest.mark.parametrize('defect', ['missing_ca', 'invalid_ca', 'wrong_endpoint', 'aliased_ca'])
def test_bad_direct_registration_fails_before_creating_condition(accepted_fixture, certificates, defect):
    args = dict(accepted_fixture, provider_base_url='https://api-local.cborg.lbl.gov', provider_ca_bundle=certificates[1])
    if defect == 'missing_ca':
        args.pop('provider_ca_bundle')
    elif defect == 'invalid_ca':
        certificates[1].write_text('not a trust bundle\n')
    elif defect == 'wrong_endpoint':
        args['provider_base_url'] += '/'
    else:
        alias = certificates[1].with_name('alias.pem'); alias.symlink_to(certificates[1])
        args['provider_ca_bundle'] = alias
    with pytest.raises((BudgetStop, ssl.SSLError)):
        prepare.build_registration(**args)
    assert not args['destination'].exists()


def test_default_public_preparation_keeps_legacy_transport(accepted_fixture):
    result = prepare.build_registration(**accepted_fixture)
    manifest = read_json(result['registration'])
    assert manifest['provider_base_url'] == 'https://api.cborg.lbl.gov'
    assert 'provider_transport' not in manifest
    assert transport.verified_context(manifest) is None


@pytest.mark.parametrize('style', ['grounding', 'fitness', 'subtype', 'direct_api_quality'])
def test_public_api_factory_retains_default_sdk_options(tmp_path, monkeypatch, style):
    context = setup_job(tmp_path, style)
    sdk, calls = mock_sdk(context)
    def default_sdk(manifest, key, *, max_retries):
        assert manifest is context.manifest and key == 'offline-key' and max_retries == 0
        assert 'provider_transport' not in manifest
        return sdk
    monkeypatch.setenv('CBORG_API_KEY', 'offline-key')
    monkeypatch.setattr(transport, 'cborg_client', default_sdk)
    monkeypatch.setattr(transport, 'Client', lambda **kw: pytest.fail('legacy transport was replaced'))
    assert api.execute_job(context)['validation']['passed']
    assert len(calls) == 2 and sdk.is_closed()
