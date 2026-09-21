"""Actual child transport and synthetic sockets only; no provider or ledger."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import ssl
import struct
import subprocess
import sys
import threading
import time

import httpx
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from audit_controls import bounded_stream as bounded
from audit_controls.test_transport import certificates


@contextmanager
def endpoint(respond, *, tls=None):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *args):
            pass
        def do_POST(self):
            body = self.rfile.read(int(self.headers["content-length"]))
            try:
                respond(self, body)
            except (BrokenPipeError, ConnectionResetError):
                pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    if tls is not None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(tls[0]), str(tls[1]))
        server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
    thread.start()
    try:
        origin = "https://localhost" if tls is not None else "http://127.0.0.1"
        yield f"{origin}:{server.server_port}/v1/messages"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


@pytest.fixture
def processes(monkeypatch):
    created = []
    real = subprocess.Popen
    def start(*args, **kwargs):
        process = real(*args, **kwargs)
        created.append((process, args, kwargs))
        return process
    monkeypatch.setattr(bounded.subprocess, "Popen", start)
    yield created
    assert all(process.poll() is not None for process, _, _ in created), "child survived its transport context"


def test_exact_bytes_status_headers_and_secret_only_in_pipe(processes, monkeypatch):
    request = b'{"data":"synthetic request"}'
    response = b'data: {"type":"ping"}\r\n\r\n' + bytes(range(256))
    seen = []
    monkeypatch.setenv("CBORG_API_KEY", "must-not-inherit-environment")
    def respond(handler, body):
        seen.append((body, handler.headers["x-api-key"]))
        handler.send_response(200); handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("X-Synthetic", "caf\xe9")
        handler.send_header("Content-Length", str(len(response))); handler.end_headers()
        handler.wfile.write(response); handler.wfile.flush()
    client = bounded.BoundedStreamClient(read_timeout_seconds=2, connect_timeout_seconds=.5)
    with endpoint(respond) as url:
        with client.stream("POST", url, content=request, headers={"x-api-key":"synthetic-pipe-secret"}) as value:
            assert value.status_code == 200
            assert value.headers["x-synthetic"] == "caf\xe9"
            assert b"".join(value.iter_bytes()) == response
    assert seen == [(request, "synthetic-pipe-secret")]
    process, args, kwargs = processes[0]
    assert "synthetic-pipe-secret" not in repr(args)
    assert not any(name.startswith(("CBORG_", "ANTHROPIC_", "OPENAI_")) for name in kwargs["env"])
    assert kwargs["stderr"] == subprocess.DEVNULL
    assert not client._workers and process.poll() is not None
    client.close()


def test_total_preheader_deadline_outwaits_neither_header_drips_nor_write_phase(processes):
    # Each byte arrives comfortably inside the HTTPX read-inactivity timeout.
    # The entire header remains incomplete beyond the parent total deadline.
    sent = threading.Event()
    def respond(handler, body):
        sent.set()
        for byte in b"HTTP/1.1 200 OK\r\nX-Slow: never-finished":
            handler.wfile.write(bytes([byte])); handler.wfile.flush(); time.sleep(.05)
    client = bounded.BoundedStreamClient(read_timeout_seconds=.45, connect_timeout_seconds=.25)
    with endpoint(respond) as url:
        started = time.monotonic()
        with pytest.raises(httpx.ReadTimeout):
            with client.stream("POST", url, content=b"synthetic", headers={}):
                pytest.fail("incomplete headers were accepted")
        elapsed = time.monotonic() - started
    assert sent.is_set() and .6 <= elapsed < 2
    assert not client._workers
    client.close()


def test_after_headers_read_deadline_and_exact_incremental_chunks(processes):
    first_sent = threading.Event()
    def respond(handler, body):
        handler.send_response(200); handler.send_header("Content-Length", "10"); handler.end_headers()
        handler.wfile.write(b"first"); handler.wfile.flush(); first_sent.set()
        time.sleep(.8)
        handler.wfile.write(b"later"); handler.wfile.flush()
    client = bounded.BoundedStreamClient(read_timeout_seconds=.3, connect_timeout_seconds=1)
    with endpoint(respond) as url:
        with pytest.raises(httpx.ReadTimeout):
            with client.stream("POST", url, content=b"synthetic", headers={}) as value:
                chunks = value.iter_bytes()
                assert next(chunks) == b"first" and first_sent.is_set()
                next(chunks)
    assert not client._workers
    client.close()


@pytest.mark.parametrize("send_started", [False, True])
def test_expired_startup_or_sent_write_is_classified_and_reaped(processes, monkeypatch, send_started):
    # A worker that cannot progress emulates startup/DNS/pool or an in-flight
    # request write. No socket or ledger exists in this diagnostic.
    source = "import sys,time,struct\n"
    if send_started:
        source += "sys.stdout.buffer.write(struct.pack('!I',5)+b'Psent');sys.stdout.buffer.flush()\n"
    source += "time.sleep(30)\n"
    monkeypatch.setattr(bounded, "_worker_command", lambda: [sys.executable, "-B", "-c", source])
    client = bounded.BoundedStreamClient(read_timeout_seconds=.1, connect_timeout_seconds=.1)
    error = httpx.ReadTimeout if send_started else httpx.ConnectTimeout
    with pytest.raises(error):
        with client.stream("POST", "http://127.0.0.1/unused", content=b"small", headers={}):
            pytest.fail("sleeping worker returned headers")
    assert not client._workers
    client.close()


def test_large_pipe_input_delivery_is_inside_deadline(processes, monkeypatch):
    monkeypatch.setattr(bounded, "_worker_command", lambda: [sys.executable, "-B", "-c", "import time;time.sleep(30)"])
    client = bounded.BoundedStreamClient(read_timeout_seconds=.15, connect_timeout_seconds=.15)
    started = time.monotonic()
    with pytest.raises(httpx.ConnectTimeout):
        with client.stream("POST", "http://127.0.0.1/unused", content=b"x" * (2 * 1024 * 1024), headers={}):
            pytest.fail("unread pipe was accepted")
    assert time.monotonic() - started < 2 and not client._workers
    client.close()


def test_close_kills_and_reaps_an_inflight_worker_before_return(processes, monkeypatch):
    monkeypatch.setattr(bounded, "_worker_command", lambda: [sys.executable, "-B", "-c", "import time;time.sleep(30)"])
    client = bounded.BoundedStreamClient(read_timeout_seconds=10, connect_timeout_seconds=1)
    errors = []
    def run():
        try:
            with client.stream("POST", "http://127.0.0.1/unused", content=b"small", headers={}):
                pass
        except Exception as exc:
            errors.append(type(exc).__name__)
    thread = threading.Thread(target=run); thread.start()
    until = time.monotonic() + 2
    while not processes and time.monotonic() < until:
        time.sleep(.005)
    assert processes
    client.close()
    assert processes[0][0].poll() is not None
    thread.join(timeout=2)
    assert not thread.is_alive() and errors and not client._workers
    with pytest.raises(httpx.ConnectError):
        with client.stream("POST", "http://127.0.0.1/unused", content=b"small", headers={}):
            pass


def test_a_5xx_can_be_classified_without_draining_its_body(processes):
    def respond(handler, body):
        handler.send_response(524); handler.send_header("Content-Length", "500"); handler.end_headers()
        handler.wfile.flush(); time.sleep(2)
    client = bounded.BoundedStreamClient(read_timeout_seconds=.5, connect_timeout_seconds=1)
    with endpoint(respond) as url:
        started = time.monotonic()
        with client.stream("POST", url, content=b"synthetic", headers={}) as value:
            assert value.status_code == 524
        assert time.monotonic() - started < 1.5
    assert not client._workers
    client.close()


@pytest.mark.parametrize("frame", [b"\xff\xff\xff\xff", struct.pack("!I", 3) + b"Pxx",
    struct.pack("!I", 3) + b"H{}", struct.pack("!I", 3) + b"E{}"])
def test_bad_worker_frames_fail_closed_and_reap(processes, monkeypatch, frame):
    source = f"import sys,time;sys.stdout.buffer.write({frame!r});sys.stdout.buffer.flush();time.sleep(30)"
    monkeypatch.setattr(bounded, "_worker_command", lambda: [sys.executable, "-B", "-c", source])
    client = bounded.BoundedStreamClient(read_timeout_seconds=1, connect_timeout_seconds=1)
    with pytest.raises(bounded.BoundWorkerProtocolError):
        with client.stream("POST", "http://127.0.0.1/unused", content=b"small", headers={}):
            pass
    assert not client._workers
    client.close()


def test_get_delegates_only_to_explicit_metadata_client_and_overrides_are_checked():
    class Delegate:
        closed = False
        def get(self, url, **kwargs):
            return url, kwargs
        def close(self):
            self.closed = True
    delegate = Delegate()
    client = bounded.BoundedStreamClient(delegate, read_timeout_seconds=1200)
    assert client.get("synthetic-metadata", timeout=3) == ("synthetic-metadata", {"timeout":3})
    with pytest.raises(ValueError, match="registered bounds"):
        with client.stream("POST", "http://127.0.0.1/unused", content=b"small", headers={},
                           timeout=httpx.Timeout(1)):
            pass
    client.close(); assert delegate.closed
    with pytest.raises(RuntimeError):
        client.get("synthetic-metadata")


def test_actual_tls_requires_registered_ca_and_hostname(certificates, processes):
    _, ca, cert, key = certificates
    received = []
    def respond(handler, body):
        received.append(body)
        handler.send_response(200); handler.send_header("Content-Length", "2")
        handler.end_headers(); handler.wfile.write(b"ok")
    with endpoint(respond, tls=(cert, key)) as url:
        correct = bounded.BoundedStreamClient(ca_bundle=ca, read_timeout_seconds=2)
        with correct.stream("POST", url, content=b"verified", headers={}) as value:
            assert b"".join(value.iter_bytes()) == b"ok"
        correct.close()
        for ca_path, target in [(None, url), (ca, url.replace("localhost", "127.0.0.1"))]:
            client = bounded.BoundedStreamClient(ca_bundle=ca_path, read_timeout_seconds=2)
            with pytest.raises(httpx.ConnectError):
                with client.stream("POST", target, content=b"untrusted", headers={}):
                    pytest.fail("unverified TLS reached response")
            client.close()
    assert received == [b"verified"]


def test_real_connection_refusal_is_not_a_post_send_failure(processes):
    with socket.socket() as unused:
        unused.bind(("127.0.0.1", 0))
        port = unused.getsockname()[1]
        # Bound but not listening: no connection, headers or body can be sent.
        client = bounded.BoundedStreamClient(read_timeout_seconds=1, connect_timeout_seconds=.5)
        with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
            with client.stream("POST", f"http://127.0.0.1:{port}/unused", content=b"synthetic", headers={}):
                pytest.fail("refused connection returned a response")
        client.close()


def test_redirect_is_returned_without_following(processes):
    hits = []
    def respond(handler, body):
        hits.append(body)
        handler.send_response(307); handler.send_header("Location", "/must-not-follow")
        handler.send_header("Content-Length", "0"); handler.end_headers()
    client = bounded.BoundedStreamClient(read_timeout_seconds=1, connect_timeout_seconds=1)
    with endpoint(respond) as url:
        with client.stream("POST", url, content=b"once", headers={}) as value:
            assert value.status_code == 307 and b"".join(value.iter_bytes()) == b""
    assert hits == [b"once"]
    client.close()


@pytest.mark.parametrize("sent", [False, True], ids=["before-send", "after-send"])
@pytest.mark.parametrize("defect", ["length", "headers", "eof", "progress", "unknown-error", "local-error", "missing-headers", "false-sent-error"])
def test_local_worker_failure_never_debits_real_proxy_ledger(tmp_path, monkeypatch, processes, sent, defect):
    """#2160: IPC faults remain pending even after a sent progress witness."""
    from native_controls.test_native_stall_policy import proxy_with, post, rows
    frames = bounded._frame(b"P", b"sent") if sent else b""
    frames += {
        "length": b"\xff\xff\xff\xff",
        "headers": bounded._frame(b"H", b"{}"),
        "eof": b"",
        "progress": bounded._frame(b"P", b"invalid"),
        "unknown-error": bounded._frame(b"E", json.dumps({"error":"InventedError", "sent":sent}).encode()),
        "local-error": bounded._frame(b"E", json.dumps({"error":bounded.LOCAL_ERROR_NAME, "sent":sent}).encode()),
        "missing-headers": bounded._frame(b"D", b"unexpected data"),
        "false-sent-error": bounded._frame(b"E", json.dumps({"error":"RemoteProtocolError", "sent":not sent}).encode()),
    }[defect]
    source = f"import sys;sys.stdin.buffer.read();sys.stdout.buffer.write({frames!r});sys.stdout.buffer.flush()"
    monkeypatch.setattr(bounded, "_worker_command", lambda: [sys.executable, "-B", "-c", source])
    proxy, ledger, provider_calls = proxy_with(tmp_path, [])
    proxy.upstream.close()
    proxy.upstream = bounded.BoundedStreamClient(read_timeout_seconds=2, connect_timeout_seconds=1)
    with proxy.running() as url:
        assert post(url, proxy).status_code == 402
        assert post(url, proxy).status_code == 402
    row, = rows(ledger)
    assert row["status"] == "pending" and "settlement_basis" not in row and "cost_usd" not in row
    assert proxy.stalls_survived == 0 and proxy.failure == "BoundWorkerProtocolError"
    assert proxy.unfinished_handlers == 0 and not proxy.upstream._workers
    assert provider_calls == [] and not list(tmp_path.rglob("stall.json"))


def test_genuine_worker_upstream_protocol_error_preserves_debit_and_retry(tmp_path, monkeypatch, processes):
    """The distinct local error does not weaken an actual upstream stall."""
    from native_controls.test_native_stall_policy import proxy_with, post, rows, STALL_DEBIT_BASIS
    from native_controls.test_native_proxy import events, wire
    calls = []
    # Run the actual worker and HTTPX exchange; the first local upstream closes
    # after receiving the request without returning a valid status line.
    def respond(handler, body):
        calls.append(body)
        if len(calls) == 1:
            handler.connection.shutdown(socket.SHUT_RDWR)
            handler.connection.close()
            return
        payload = wire(events())
        handler.send_response(200); handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Content-Length", str(len(payload))); handler.end_headers()
        handler.wfile.write(payload)
    with endpoint(respond) as target:
        # Rewrite the synthetic URL inside the worker, so NativeProxy retains
        # its real endpoint validation without any provider connection.
        helper = str(Path(bounded.__file__).resolve())
        source = ("import runpy;module=runpy.run_path(" + repr(helper) + ");"
                  "original=module['_read_input'];"
                  "module['_run_worker'].__globals__['_read_input']=lambda:{**original(),'url':" + repr(target) + "};"
                  "module['_run_worker']()")
        monkeypatch.setattr(bounded, "_worker_command", lambda: [sys.executable, "-B", "-c", source])
        proxy, ledger, provider_calls = proxy_with(tmp_path, [])
        proxy.upstream.close()
        proxy.upstream = bounded.BoundedStreamClient(read_timeout_seconds=2, connect_timeout_seconds=1)
        with proxy.running() as url:
            assert post(url, proxy).status_code == 503
            assert post(url, proxy).status_code == 200
    first, second = rows(ledger)
    assert first["settlement_basis"] == STALL_DEBIT_BASIS
    assert first["stall_evidence"]["error_type"] == "RemoteProtocolError"
    assert second["status"] == "settled" and "settlement_basis" not in second
    assert proxy.stalls_survived == 1 and proxy.failure is None
    assert len(calls) == 2 and provider_calls == []


@pytest.mark.parametrize("fail_on", [1, 2], ids=["stdin", "stdout"])
@pytest.mark.parametrize("exception", [OSError, KeyboardInterrupt])
def test_partial_worker_pipe_setup_is_reaped_before_constructor_raises(processes, monkeypatch, fail_on, exception):
    """#2161: the unregistered child still has an owner during partial setup."""
    monkeypatch.setattr(bounded, "_worker_command", lambda: [sys.executable, "-B", "-c", "import time;time.sleep(30)"])
    original = bounded.os.set_blocking
    calls = []
    def fail(fd, blocking):
        calls.append(fd)
        if len(calls) == fail_on:
            raise exception("synthetic pipe setup fault")
        return original(fd, blocking)
    monkeypatch.setattr(bounded.os, "set_blocking", fail)
    client = bounded.BoundedStreamClient(read_timeout_seconds=1, connect_timeout_seconds=1)
    with pytest.raises(exception, match="synthetic pipe setup fault"):
        with client.stream("POST", "http://127.0.0.1/unused", content=b"synthetic", headers={}):
            pytest.fail("partially initialized worker returned")
    process, _, _ = processes[0]
    assert process.poll() is not None and process.stdin.closed and process.stdout.closed
    assert not client._workers
    client.close()


@pytest.mark.parametrize("sent", [False, True])
def test_unknown_worker_exception_has_distinct_local_category(monkeypatch, sent):
    """Even a worker bug after its send witness cannot masquerade as HTTPX."""
    emitted = []
    monkeypatch.setattr(bounded, "_write_frame", lambda kind, payload: emitted.append((kind, payload)))
    monkeypatch.setattr(bounded, "_read_input", lambda: {"ca_data":None, "read_timeout":1,
        "connect_timeout":1, "method":"POST", "url":"http://127.0.0.1/unused",
        "content":"c3ludGhldGlj", "headers":{}})
    class BadClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def stream(self, *args, **kwargs):
            if sent:
                kwargs["extensions"]["trace"]("http11.send_request_headers.started", {})
            raise RuntimeError("synthetic internal detail must not escape")
    monkeypatch.setattr(bounded.httpx, "Client", BadClient)
    bounded._run_worker()
    kind, payload = emitted[-1]
    assert kind == b"E" and json.loads(payload) == {"error":"BoundWorkerProtocolError", "sent":sent}
    assert b"synthetic internal detail" not in payload
