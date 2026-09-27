"""Hard count deadlines, cancellation and narrow subprocess protocol (#2159)."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import signal
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
    # `sent` holds the monotonic instant at which each body byte was flushed.
    observed = {'requests': [], 'arrived': threading.Event(), 'sent': []}
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
                    observed['sent'].append(time.monotonic())
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
        # SDK-facing inspection must describe the actual wire policy without
        # allowing a caller to mutate the worker's registered configuration.
        headers = client.default_headers
        assert headers == {'x-headroom-bypass': 'true'}
        headers.clear()
        try:
            assert client.messages.count_tokens(**FIELDS).input_tokens == 100
        finally:
            client.close()
    assert len(seen['requests']) == 1
    assert seen['requests'][0] == {'path': '/v1/messages/count_tokens', 'body': FIELDS, 'bypass': 'true'}
    assert len(children) == 1 and children[0].poll() == 0 and not client._active


#: From the count's deadline (its start plus the budget) to the worker's SIGKILL:
#: the wake-up of the parent's timed wait and the kill, in-process (#2697).
#: Measured median 7.7 ms, p99 105 ms, max 466 ms over 1,670 attempts at load up
#: to 442. The review's own run measured max 1.17 s at load ~450, and this keeps
#: threefold on that. It rejects a deadline enforced 3.5 s late or more, including
#: start-up left uncharged whenever start-up takes that long. It does not reject a
#: shorter lateness, which origin/main's `budget + 1.5` total only caught at loads
#: where it also flaked.
DEADLINE_KILL_SECONDS = 3.5

#: The reap of the killed worker, which may still be starting its interpreter. It
#: is a process-level cost, so it is kept out of the deadline bound and given only a
#: hang guard (#2697). Measured median 89 ms, p99 633 ms, max 796 ms (load 356);
#: the review measured max 1.56 s.
REAP_SECONDS = 10


def test_progressing_response_cannot_outlive_total_count_deadline(children, monkeypatch):
    # Every byte arrives well inside the SDK's inactivity bound. The complete
    # body takes twice the parent's total budget, so only that budget can end
    # the count. The budget also pays for starting the worker (by design,
    # bounded_transport.py), and under load start-up alone can outlast two
    # seconds, so the request is never sent (#2569). Such an attempt still
    # proves the deadline but not a progressing response. What decides a
    # repeat with a doubled budget is the server's record of body bytes
    # flushed before the deadline, not a guess about start-up; the ladder runs
    # to 32 s because start-up reached about 14 s at load 450 (#2697). No
    # assertion is retried: every attempt checks the typed timeout, that it was
    # not early, the deadline-to-SIGKILL gap, a bounded reap, one reaped worker
    # per count (the worker SDK never retries) and an empty registry, so a
    # deadline that is not enforced fails on the first attempt.
    body, attempts, killed_at = b'{"input_tokens":100}', [], []
    launch = bounded.subprocess.Popen
    def watched(*args, **kwargs):
        child = launch(*args, **kwargs)
        real_signal = child.send_signal
        def send_signal(sig):
            if sig == signal.SIGKILL:
                killed_at.append(time.monotonic())
            return real_signal(sig)
        child.send_signal = send_signal
        return child
    monkeypatch.setattr(bounded.subprocess, 'Popen', watched)
    for budget in (2, 4, 8, 16, 32):
        delay = 2 * budget / len(body)
        # Every gap is far inside the worker SDK's inactivity bound, which is
        # the budget itself (`payload['timeout']`).
        assert delay <= budget / 10
        with server(body=body, delay=delay) as (url, seen):
            client = bounded.BoundedCountClient(api_key='fake-key', base_url=url, timeout_seconds=budget)
            try:
                killed_at.clear()
                started = time.monotonic()
                with pytest.raises(anthropic.APITimeoutError):
                    client.messages.count_tokens(**FIELDS)
                elapsed = time.monotonic() - started
                assert elapsed >= budget - .5, (budget, elapsed, attempts)
                assert len(killed_at) == 1, (budget, killed_at, attempts)
                assert killed_at[0] - (started + budget) < DEADLINE_KILL_SECONDS, (budget, elapsed, attempts)
                assert started + elapsed - killed_at[0] < REAP_SECONDS, (budget, elapsed, attempts)
                assert len(children) == len(attempts) + 1, attempts
                assert all(child.poll() is not None for child in children) and not client._active
            finally:
                client.close()
        assert len(seen['requests']) <= 1, attempts
        # A byte flushed before started + budget went to a live worker: the
        # parent's deadline is never earlier than that instant and the worker
        # is killed only after it. A request that arrived at the deadline, with
        # its bytes written into a killed worker's socket, does not count.
        progressed = sum(instant < started + budget for instant in seen['sent'])
        attempts.append({'budget': budget, 'elapsed': round(elapsed, 2), 'bytes_before_deadline': progressed})
        if progressed >= 2:
            break
    assert progressed >= 2 and len(seen['requests']) == 1, attempts


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
