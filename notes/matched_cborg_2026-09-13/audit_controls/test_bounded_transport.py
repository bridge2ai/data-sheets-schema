"""Hard count deadlines, cancellation and narrow subprocess protocol (#2159)."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import ssl
import sys
import threading
import time
from types import SimpleNamespace

import anthropic
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from audit_controls import bounded_transport as bounded


FIELDS = {'model': 'synthetic-count', 'messages': [{'role': 'user', 'content': 'synthetic only'}]}


@contextmanager
def server(*, status=200, body=b'{"input_tokens":100}', delay=0, hold=None):
    observed = {'requests': [], 'arrived': threading.Event()}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            raw = self.rfile.read(int(self.headers['content-length']))
            observed['requests'].append({'path': self.path, 'body': json.loads(raw),
                                         'bypass': self.headers.get('x-headroom-bypass')})
            observed['arrived'].set()
            if hold is not None:
                hold.wait(timeout=10)
            try:
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                for byte in body:
                    if delay:
                        time.sleep(delay)
                    self.wfile.write(bytes([byte]))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
    instance = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    instance.daemon_threads = True
    thread = threading.Thread(target=lambda: instance.serve_forever(poll_interval=0.02), daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{instance.server_port}', observed
    finally:
        if hold is not None:
            hold.set()
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=2)


@pytest.fixture
def children(monkeypatch):
    actual, started = bounded.subprocess.Popen, []
    def launch(*args, **kwargs):
        child = actual(*args, **kwargs)
        started.append(child)
        return child
    monkeypatch.setattr(bounded.subprocess, 'Popen', launch)
    return started


def test_real_worker_returns_typed_count_and_registered_headers(children):
    with server() as (url, seen):
        client = bounded.BoundedCountClient(api_key='fake-key', base_url=url,
            default_headers={'x-headroom-bypass': 'true'}, timeout_seconds=5)
        try:
            assert client.messages.count_tokens(**FIELDS).input_tokens == 100
        finally:
            client.close()
    assert len(seen['requests']) == 1
    assert seen['requests'][0] == {'path': '/v1/messages/count_tokens', 'body': FIELDS, 'bypass': 'true'}
    assert len(children) == 1 and children[0].poll() == 0 and not client._active


def test_progressing_response_cannot_outlive_total_count_deadline(children):
    # Every byte arrives well inside the SDK's inactivity bound. The complete
    # body takes longer than the parent's two-second total budget.
    with server(delay=0.2) as (url, seen):
        client = bounded.BoundedCountClient(api_key='fake-key', base_url=url, timeout_seconds=2)
        started = time.monotonic()
        with pytest.raises(anthropic.APITimeoutError):
            client.messages.count_tokens(**FIELDS)
        elapsed = time.monotonic() - started
        assert seen['arrived'].is_set() and len(seen['requests']) == 1
        assert 1.5 <= elapsed < 3.5
        assert len(children) == 1 and children[0].poll() is not None and not client._active
        client.close()


def test_close_cancels_and_reaps_active_worker_and_forbids_new_counts(children):
    hold = threading.Event()
    with server(hold=hold) as (url, seen):
        client = bounded.BoundedCountClient(api_key='fake-key', base_url=url, timeout_seconds=30)
        errors = []
        def count():
            try:
                client.messages.count_tokens(**FIELDS)
            except Exception as exc:
                errors.append(exc)
        thread = threading.Thread(target=count)
        thread.start()
        try:
            assert seen['arrived'].wait(timeout=5)
            started = time.monotonic()
            client.close()
            assert time.monotonic() - started < 2
            assert all(child.poll() is not None for child in children)
            thread.join(timeout=2)
            assert not thread.is_alive() and len(errors) == 1
            assert isinstance(errors[0], bounded.CountClientClosed)
            assert not client._active
            with pytest.raises(bounded.CountClientClosed):
                client.messages.count_tokens(**FIELDS)
            assert len(children) == len(seen['requests']) == 1
        finally:
            client.close()
            hold.set()
            thread.join(timeout=2)


@pytest.mark.parametrize('status, exception', [(400, anthropic.BadRequestError),
    (401, anthropic.AuthenticationError), (429, anthropic.RateLimitError), (503, anthropic.InternalServerError)])
def test_error_categories_preserve_retry_decisions_without_provider_text(children, status, exception):
    secret = 'SYNTHETIC_PROVIDER_PROSE_MUST_NOT_ESCAPE'
    with server(status=status, body=json.dumps({'error': {'message': secret}}).encode()) as (url, seen):
        client = bounded.BoundedCountClient(api_key='fake-key', base_url=url, timeout_seconds=5)
        try:
            with pytest.raises(exception) as caught:
                client.messages.count_tokens(**FIELDS)
            assert secret not in str(caught.value) and caught.value.status_code == status
        finally:
            client.close()
    assert len(children) == len(seen['requests']) == 1  # worker SDK never retries
    assert all(child.poll() is not None for child in children)


@pytest.mark.parametrize('value', [True, -1, '100', None])
def test_invalid_provider_count_is_not_a_retryable_transport_failure(value):
    with server(body=json.dumps({'input_tokens': value}).encode()) as (url, _):
        client = bounded.BoundedCountClient(api_key='fake-key', base_url=url, timeout_seconds=5)
        try:
            with pytest.raises(bounded.CountWorkerError):
                client.messages.count_tokens(**FIELDS)
        finally:
            client.close()


def test_secret_configuration_and_request_use_only_anonymous_stdin(monkeypatch):
    observed = {}
    class Child:
        stdin = io.BytesIO()
        stdout = io.BytesIO()
        returncode = 0
        def __init__(self, args, **kwargs):
            observed.update(args=args, **kwargs)
        def communicate(self, *, input, timeout):
            observed.update(payload=json.loads(input), timeout=timeout)
            return b'{"input_tokens":7}', None
        def poll(self): return 0
        def wait(self): return 0
    monkeypatch.setattr(bounded.subprocess, 'Popen', Child)
    client = bounded.BoundedCountClient(api_key='SECRET_KEY', base_url='https://registered.invalid',
        ca_bundle='/synthetic/registered-ca.pem', default_headers={'x-headroom-bypass':'true'})
    assert client.messages.count_tokens(timeout=1, **FIELDS).input_tokens == 7
    assert observed['args'] == [sys.executable, '-B', str(Path(bounded.__file__).resolve()), '--count-worker']
    assert observed['env'] == {'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'}
    assert observed['stdin'] == bounded.subprocess.PIPE and observed['stdout'] == bounded.subprocess.PIPE
    assert observed['stderr'] == bounded.subprocess.DEVNULL and observed['close_fds'] is True
    assert observed['payload']['config']['api_key'] == 'SECRET_KEY'
    assert observed['payload']['fields'] == FIELDS and 0 < observed['timeout'] <= 1
    assert 'SECRET_KEY' not in repr(observed['args']) + repr(observed['env'])


def test_worker_uses_only_pinned_certificate_trust_and_zero_retries(monkeypatch):
    import httpx
    seen = {}
    class Context:
        verify_flags = ssl.VERIFY_X509_PARTIAL_CHAIN
        def __init__(self, protocol): seen['protocol'] = protocol
        def load_verify_locations(self, *, cafile): seen['cafile'] = cafile
    def transport(**kwargs):
        seen['http'] = kwargs
        return object()
    class SDK:
        def __init__(self, **kwargs):
            seen['sdk'] = kwargs
            self.messages = SimpleNamespace(count_tokens=lambda **fields: SimpleNamespace(input_tokens=3))
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(bounded.ssl, 'SSLContext', Context)
    monkeypatch.setattr(httpx, 'Client', transport)
    monkeypatch.setattr(anthropic, 'Anthropic', SDK)
    assert bounded._count_once({'config': {'api_key':'fake', 'base_url':'https://registered.invalid',
        'ca_bundle':'/pinned.pem', 'default_headers':{'x-headroom-bypass':'true'}},
        'timeout':120, 'fields':FIELDS}) == {'input_tokens':3}
    assert seen['protocol'] == ssl.PROTOCOL_TLS_CLIENT and seen['cafile'] == '/pinned.pem'
    assert not seen['http']['verify'].verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN
    assert seen['http']['trust_env'] is False and seen['http']['follow_redirects'] is False
    assert seen['sdk']['max_retries'] == 0 and seen['sdk']['default_headers'] == {'x-headroom-bypass':'true'}


@pytest.mark.parametrize('timeout', [True, 0, -1, float('inf'), float('nan'), '1'])
def test_invalid_total_deadlines_cannot_start_a_worker(monkeypatch, timeout):
    monkeypatch.setattr(bounded.subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('spawned'))
    with pytest.raises(ValueError):
        bounded.BoundedCountClient(api_key='fake', base_url='https://registered.invalid', timeout_seconds=timeout)
