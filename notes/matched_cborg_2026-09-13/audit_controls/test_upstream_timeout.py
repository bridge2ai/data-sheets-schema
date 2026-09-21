"""Registered raw-stream timeouts; synthetic clients/loopback only (#2147)."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import ssl
import sys
import threading
import time
from types import SimpleNamespace

import httpx
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import native, prepare, registration, transport
from audit_controls.test_native import native_case, configure_execution, response_events
from audit_controls.test_transport import certificates
from budgeted_cborg import BudgetStop, Ledger, provider_context_headers
from native_proxy import NativeProxy
from native_controls.test_native_proxy import REQUEST, PRICES, events, wire
from finalization_controls import native as final_native
import run_api_canary
import run_native_canary

KEY = 'native_upstream_read_timeout_seconds'


def manifest(value=2700):
    return {'kind': 'd4d_native_audit_continuation', KEY: value,
            'native_runtime': {'api_timeout_ms': 3600000}, 'job': {'deadline_seconds': 10800}}


@pytest.mark.parametrize('value', [None, True, False, 0, -1, 1.5, '2700', [], {}, 3600, 3601])
def test_invalid_selector_rejected_before_runtime_setup_or_client(value, tmp_path, monkeypatch):
    m = manifest(value)
    monkeypatch.setattr(native, 'build_policy', lambda *_: pytest.fail('policy before selector validation'))
    monkeypatch.setattr(native, 'verify_runtime', lambda *_: pytest.fail('runtime before selector validation'))
    monkeypatch.setattr(transport, 'Client', lambda **kw: pytest.fail('HTTP client before selector validation'))
    context = SimpleNamespace(manifest=m, job=m['job'], attempt=tmp_path)
    with pytest.raises(BudgetStop): native.execute_job(context)
    with pytest.raises(BudgetStop): transport.provider_clients(m, 'offline-key')
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('change', ['sdk_absent', 'sdk_outside_job', 'sdk_bool', 'job_bool'])
def test_selector_requires_explicit_sdk_and_job_bounds(change):
    m = manifest()
    if change == 'sdk_absent': m['native_runtime'].clear()
    elif change == 'sdk_outside_job': m['job']['deadline_seconds'] = 3500
    elif change == 'sdk_bool': m['native_runtime']['api_timeout_ms'] = True
    else: m['job']['deadline_seconds'] = True
    with pytest.raises(BudgetStop): registration.native_upstream_read_timeout(m)


def test_omission_and_strict_sdk_boundary():
    assert registration.native_upstream_read_timeout({}) is None
    assert registration.native_upstream_read_timeout(manifest(3599)) == 3599
    with pytest.raises(BudgetStop): registration.native_upstream_read_timeout(manifest(3600))


@pytest.mark.parametrize('kind', ['d4d_native_finalization', 'd4d_evaluation', 'd4d_evaluation_source_pair'])
def test_other_stages_reject_selector_before_shared_transport(kind, monkeypatch):
    m = manifest(); m['kind'] = kind
    monkeypatch.setattr(transport, 'Client', lambda **kw: pytest.fail('HTTP client constructed'))
    with pytest.raises(BudgetStop, match='audit-only'): transport.provider_clients(m, 'offline-key')


@pytest.mark.parametrize('kind', ['d4d_native_finalization', 'd4d_native_audit_continuation'])
def test_actual_phase4_entry_rejects_selector_even_with_audit_kind(tmp_path, monkeypatch, kind):
    m = manifest(); m['kind'] = kind
    monkeypatch.setattr(final_native, 'build_policy', lambda *_: pytest.fail('Phase4 policy constructed'))
    context = SimpleNamespace(manifest=m, job=m['job'], attempt=tmp_path)
    with pytest.raises(BudgetStop, match='audit-only|native audit controller'):
        final_native.execute_job(context)
    assert list(tmp_path.iterdir()) == []


def generation_manifest(tmp_path, monkeypatch):
    """Use the actual imported generation implementation and shared verifier."""
    from data_sheets_schema import api_runner
    repository = Path(api_runner.__file__).resolve().parents[2]
    monkeypatch.chdir(repository)
    pinned = tmp_path / 'synthetic-input.txt'
    pinned.write_text('Synthetic offline generation input')
    return {'repository': str(repository), 'python': sys.executable,
            'python_version': sys.version,
            'pinned_files': {str(pinned): run_api_canary.sha(pinned)}}


@pytest.mark.parametrize('value', [2700, None, True, 0, '2700'])
def test_shared_generation_verifier_rejects_selector_before_other_checks(tmp_path, monkeypatch, value):
    m = generation_manifest(tmp_path, monkeypatch)
    m[KEY] = value
    path = tmp_path / 'registration.json'; path.write_text(json.dumps(m))
    digest = run_api_canary.sha(path)
    monkeypatch.setattr(run_api_canary, 'sha', lambda *_: pytest.fail('hash check before audit-only rejection'))
    with pytest.raises(BudgetStop, match='audit-only'):
        run_api_canary.verify(m, path, digest)


@pytest.mark.parametrize('arm', ['api', 'agentic'])
@pytest.mark.parametrize('selection', [{}, {KEY: 2700}, {KEY: None}], ids=['absent', 'integer', 'null'])
def test_generation_entrypoints_reject_audit_selector_before_setup(tmp_path, monkeypatch, arm, selection):
    """Run both real CLI entrypoints through their actual shared verifier (#2148)."""
    m = generation_manifest(tmp_path, monkeypatch)
    job = {'id': 'synthetic', 'canary': True, 'execution_arm': arm,
           'output_directories': [str(tmp_path / 'output')]}
    m.update(selection)
    m['generation'] = {'external_canary': {'status': 'registered'}, 'jobs': [job],
                       'canary_order': [job['id']]}
    path = tmp_path / 'registration.json'; path.write_text(json.dumps(m))
    review = {'registration_sha256': run_api_canary.sha(path), 'verdict': 'approve',
              'ci_conclusion': 'success', 'allowed_jobs': [job['id']]}
    args = ['--registration', str(path)]
    runner = run_api_canary
    if arm == 'agentic':
        runner = run_native_canary
        overlay = tmp_path / 'overlay.json'
        overlay.write_text(json.dumps({'registration': str(path),
            'registration_sha256': review['registration_sha256'],
            'allowed_jobs': [job['id']], 'pinned_files': {}}))
        review['overlay_sha256'] = run_api_canary.sha(overlay)
        args = ['--overlay', str(overlay)]
    review_path = tmp_path / 'review.json'; review_path.write_text(json.dumps(review))
    assert runner.verify is run_api_canary.verify
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    history_calls = []
    class NextExistingGate(Exception): pass
    def history(manifest):
        history_calls.append(manifest)
        raise NextExistingGate()
    def forbidden(*args, **kwargs): pytest.fail('mutable setup or provider before verification')
    monkeypatch.setattr(runner, 'verify_history', history)
    monkeypatch.setattr(runner, 'open_ledger', forbidden)
    monkeypatch.setattr(runner, 'cborg_client', forbidden)
    monkeypatch.setattr(runner, 'spec_for', forbidden)
    monkeypatch.setattr(sys, 'argv', ['synthetic-generation', *args,
                                     '--review', str(review_path), '--job', job['id']])
    if selection:
        with pytest.raises(BudgetStop, match='audit-only'): runner.main()
        assert history_calls == []
    else:
        with pytest.raises(NextExistingGate): runner.main()
        assert history_calls == [m]
    assert {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == before
    assert not (tmp_path / 'attempts').exists() and not (tmp_path / 'output').exists()


@pytest.mark.parametrize('selected', [None, 2700])
def test_verified_counting_and_raw_stream_use_distinct_request_timeouts(certificates, tmp_path, monkeypatch, selected):
    m = certificates[0]
    if selected is not None: m.update(manifest(selected))
    real_client, created, requests, stream_options = httpx.Client, [], [], []
    def respond(request):
        requests.append(request)
        assert request.headers['x-api-key'] == 'offline-key'
        assert request.headers['x-headroom-bypass'] == 'true'
        if request.url.path.endswith('/count_tokens'):
            return httpx.Response(200, json={'input_tokens': 100})
        assert json.loads(request.content) == REQUEST
        return httpx.Response(200, content=wire(events()), headers={'content-type': 'text/event-stream'})
    def factory(**kwargs):
        assert kwargs['trust_env'] is False and kwargs['follow_redirects'] is False
        assert kwargs['verify'].verify_mode == ssl.CERT_REQUIRED and kwargs['verify'].check_hostname is True
        client = real_client(transport=httpx.MockTransport(respond), **kwargs)
        original = client.stream
        def stream(*args, **options):
            stream_options.append(options.copy())
            return original(*args, **options)
        client.stream = stream
        created.append(client)
        return client
    monkeypatch.setattr(transport, 'Client', factory)
    sdk, upstream = transport.provider_clients(m, 'offline-key')
    assert sdk._client is upstream and sdk.max_retries == 0
    ledger = Ledger(tmp_path / 'billing.json', manifest_sha256='synthetic')
    options = { 'upstream_read_timeout_seconds': selected } if selected is not None else {}
    proxy = NativeProxy(sdk=sdk, ledger=ledger, attempt='synthetic', evidence=tmp_path / 'requests',
        model=REQUEST['model'], prices=PRICES, verify=lambda: None, provider_key='offline-key',
        base_url=m['provider_base_url'], upstream=upstream, request_headers=provider_context_headers(m), **options)
    with proxy.running() as url, real_client(trust_env=False) as local:
        response = local.post(url + '/v1/messages', json=REQUEST, headers={'x-api-key': proxy.token})
    assert response.status_code == 200 and response.content == wire(events())
    assert [r.url.path for r in requests] == ['/v1/messages/count_tokens', '/v1/messages']
    default = {'connect': 20, 'read': 1800, 'write': 1800, 'pool': 1800}
    assert requests[0].extensions['timeout'] == default
    assert requests[1].extensions['timeout'] == {**default, 'read': selected or 1800}
    assert upstream.timeout.as_dict() == default
    assert ('timeout' in stream_options[0]) is (selected is not None)
    assert len(created) == 1 and upstream.is_closed and proxy.unfinished_handlers == 0
    row, = json.loads(ledger.path.read_text())['requests']
    assert row['status'] == 'settled'


def test_real_audit_entry_forwards_only_registered_stream_override(native_case, monkeypatch):
    c = native_case
    context, sdk = configure_execution(c, monkeypatch)
    c.manifest.update(kind='d4d_native_audit_continuation', **{KEY: 2})
    c.manifest['native_runtime']['api_timeout_ms'] = 5000
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(200, content=response_events(), headers={'content-type': 'text/event-stream'})
    upstream = httpx.Client(transport=httpx.MockTransport(respond), timeout=httpx.Timeout(1800, connect=20))
    result = native.execute_job(context, client=sdk, upstream=upstream)
    assert result['validation']['passed'] and result['runtime']['unfinished_handlers'] == 0
    assert requests and all(r.extensions['timeout'] == {'connect':20, 'read':2, 'write':1800, 'pool':1800} for r in requests)
    assert upstream.timeout.read == 1800


@pytest.mark.parametrize('selected,delay,client_read,completed', [
    (None, .2, .05, False), (1, .2, .05, True), (1, 1.2, 1800, False)])
def test_actual_delayed_header_socket_obeys_raw_read_timeout(tmp_path, selected, delay, client_read, completed):
    """Use a small local boundary, not a provider or a long timeout sleep."""
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            calls.append(self.rfile.read(int(self.headers['Content-Length'])))
            time.sleep(delay)
            raw = wire(events())
            try:
                self.send_response(200); self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    class Loopback(httpx.BaseTransport):
        def __init__(self): self.inner = httpx.HTTPTransport(retries=0)
        def handle_request(self, request):
            request.url = request.url.copy_with(scheme='http', host='127.0.0.1', port=server.server_port)
            return self.inner.handle_request(request)
        def close(self): self.inner.close()
    upstream = httpx.Client(transport=Loopback(), timeout=httpx.Timeout(1800, connect=20, read=client_read))
    sdk = SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **kw: SimpleNamespace(input_tokens=100)))
    ledger = Ledger(tmp_path / 'billing.json', manifest_sha256='synthetic')
    options = {'upstream_read_timeout_seconds': selected} if selected is not None else {}
    proxy = NativeProxy(sdk=sdk, ledger=ledger, attempt='synthetic', evidence=tmp_path / 'requests',
        model=REQUEST['model'], prices=PRICES, verify=lambda: None, provider_key='offline-key',
        base_url='https://api.cborg.lbl.gov', upstream=upstream, **options)
    try:
        with proxy.running() as url, httpx.Client(trust_env=False) as local:
            response = local.post(url + '/v1/messages', json=REQUEST, headers={'x-api-key':proxy.token})
        assert response.status_code == (200 if completed else 402)
        assert len(calls) == 1 and json.loads(calls[0]) == REQUEST  # No automatic retries.
        row, = json.loads(ledger.path.read_text())['requests']
        assert row['status'] == ('settled' if completed else 'pending')
        assert proxy.unfinished_handlers == 0
        if not completed:
            assert proxy.failure == 'ReadTimeout'
            assert 'cost_usd' not in row
            assert not list((tmp_path / 'requests').rglob('http_status.json'))
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
