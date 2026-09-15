"""Draft native-runtime CBORG transport; never launched without its own review.

The child receives a loopback token, never the provider key. Original native
JSON and server-sent-event bodies are retained. Every paid request uses the
same sequence ledger as the direct API arm and is admitted before forwarding.
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx

from budgeted_cborg import BudgetStop, CappedMessages, digest, write_new


class Completion:
    """Accumulate just the accounting fields; raw SSE remains original evidence."""
    def __init__(self):
        self.buffer = b""
        self.started = False
        self.stopped = False
        self.delta = False
        self.message = None

    def event(self, value):
        kind = value.get("type")
        if kind == "ping":
            return
        if self.stopped:
            raise BudgetStop("non-ping event follows terminal stream marker")
        if kind == "message_start":
            if self.started or not isinstance(value.get("message"), dict):
                raise BudgetStop("ambiguous stream start")
            self.started = True
            self.message = dict(value["message"])
            self.message["usage"] = dict(self.message.get("usage") or {})
        elif kind == "message_delta":
            if not self.started:
                raise BudgetStop("usage delta precedes stream start")
            usage = value.get("usage")
            if not isinstance(usage, dict) or type(usage.get("output_tokens")) is not int or usage["output_tokens"] < 0:
                raise BudgetStop("final stream usage is unverified")
            self.delta = True
            self.message.update(value.get("delta") or {})
            self.message["usage"].update(value.get("usage") or {})
        elif kind == "message_stop":
            if not self.started or not self.delta:
                raise BudgetStop("terminal stream marker lacks final usage delta")
            self.stopped = True
        elif kind == "error":
            raise BudgetStop("upstream stream reports an error; charge remains unknown")
        elif kind not in {"content_block_start", "content_block_delta", "content_block_stop"}:
            raise BudgetStop("unregistered stream event type")
        elif not self.started:
            raise BudgetStop("content precedes stream start")

    def feed(self, raw):
        self.buffer += raw
        # Accept LF and CRLF framing without changing the retained original.
        normalized = self.buffer.replace(b"\r\n", b"\n")
        while b"\n\n" in normalized:
            frame, normalized = normalized.split(b"\n\n", 1)
            lines = [line[5:].lstrip(b" ") for line in frame.split(b"\n") if line.startswith(b"data:")]
            if lines:
                self.event(json.loads(b"\n".join(lines)))
        self.buffer = normalized

    def final(self):
        if self.buffer.strip() or not self.started or not self.stopped or not self.delta:
            raise BudgetStop("stream completion is unverified; charge remains reserved")
        return SimpleNamespace(model_dump=lambda **kw: self.message)


class NativeProxy:
    def __init__(self, *, sdk, ledger, attempt, evidence, model, prices, verify,
                 provider_key, base_url, upstream=None, request_headers=None):
        if base_url != "https://api.cborg.lbl.gov":
            raise BudgetStop("native runtime requires the registered CBORG endpoint")
        if request_headers is not None and not isinstance(request_headers, dict):
            raise BudgetStop("native provider headers must be a mapping")
        self.request_headers = dict(request_headers) if request_headers is not None else {}
        if self.request_headers not in ({}, {"x-headroom-bypass": "true"}):
            raise BudgetStop("unregistered native provider headers")
        sdk_headers = httpx.Headers(getattr(sdk, "default_headers", {}))
        if sdk_headers.get("x-headroom-bypass") != self.request_headers.get("x-headroom-bypass"):
            raise BudgetStop("native token counting and generation context policies differ")
        self.token = secrets.token_urlsafe(32)
        self.key, self.base_url = provider_key, base_url
        self.state = threading.Condition(threading.RLock())
        self.closed = False
        self.frozen = False
        self.active_handlers = 0
        self.unfinished_handlers = 0
        self.messages = CappedMessages(sdk, ledger=ledger, attempt=attempt,
            evidence=Path(evidence), model=model, prices=prices, verify=verify,
            mutation_guard=self.mutation_guard)
        self.upstream = upstream or httpx.Client(timeout=httpx.Timeout(1800, connect=20), follow_redirects=False)
        self.failure = None
        self.failed = threading.Event()
        self.serial = threading.Lock()
        self.server = None
        self.thread = None

    def fail(self, exc):
        # Provider exception strings may include HTTP headers. Preserve only
        # controller-authored explanations or an exception class.
        with self.state:
            if self.frozen:
                return
            if self.failure is None:
                self.failure = str(exc) if isinstance(exc, BudgetStop) else type(exc).__name__
            self.closed = True
            self.failed.set()

    def close_admission(self):
        with self.state:
            self.closed = True

    def require_open(self):
        if self.closed:
            raise BudgetStop("native admission is closed")

    def require_writable(self):
        if self.frozen:
            raise BudgetStop("native evidence is frozen after shutdown")

    @contextmanager
    def mutation_guard(self, phase):
        with self.state:
            self.require_writable()
            if phase == "admit":
                self.require_open()
            yield

    def capture(self, path, raw, *, append=False):
        with self.state:
            self.require_writable()
            with path.open("ab" if append else "xb") as out:
                out.write(raw)

    def capture_json(self, path, value):
        with self.state:
            self.require_writable()
            write_new(path, value)

    @contextmanager
    def running(self, *, cleanup_timeout=2):
        owner = self
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"
            def log_message(self, *args):
                pass
            def reply(self, code, value):
                raw = json.dumps(value).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def do_POST(self):
                # Native runtimes may issue auxiliary calls concurrently.
                # Serialize admission so every charge settles before the next.
                with owner.state:
                    owner.active_handlers += 1
                    owner.state.notify_all()
                try:
                    with owner.serial:
                        self._post_serially()
                finally:
                    with owner.state:
                        owner.active_handlers -= 1
                        owner.state.notify_all()
            def _post_serially(self):
                self.connection.settimeout(20)
                sent = False
                try:
                    supplied = self.headers.get("x-api-key", "")
                    if not supplied:
                        supplied = self.headers.get("authorization", "").removeprefix("Bearer ")
                    if not secrets.compare_digest(supplied, owner.token):
                        self.reply(401, {"type":"error", "error":{"type":"authentication_error", "message":"invalid local transport token"}})
                        return
                    if owner.failed.is_set():
                        raise BudgetStop("native attempt previously stopped")
                    with owner.state:
                        owner.require_open()
                    path = urlsplit(self.path).path
                    if path not in {"/v1/messages", "/v1/messages/count_tokens"}:
                        raise BudgetStop("unregistered native transport endpoint")
                    length = int(self.headers.get("content-length", "0"))
                    if length <= 0 or length > 32 * 1024 * 1024:
                        raise BudgetStop("invalid native request size")
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise BudgetStop("incomplete native request body")
                    request = json.loads(raw)
                    if not isinstance(request, dict) or request.get("model") != owner.messages.model:
                        raise BudgetStop("native request model differs from registration")
                    owner.messages.verify()
                    if path.endswith("/count_tokens"):
                        fields = {k:v for k,v in request.items() if k in {"model", "system", "messages", "tools", "tool_choice", "thinking"}}
                        count = owner.messages.client.messages.count_tokens(**fields).input_tokens
                        if type(count) is not int or count < 0:
                            raise BudgetStop("invalid native input count")
                        self.reply(200, {"input_tokens":count})
                        return
                    if request.get("stream") is not True:
                        raise BudgetStop("native runtime must use reviewed streamed transport")
                    if request.get("service_tier") not in (None, "auto", "standard_only"):
                        raise BudgetStop("unregistered native service tier")
                    ticket, folder = owner.messages.prepare(request)
                    owner.capture(folder / "native_request.json", raw)
                    headers = {"x-api-key":owner.key, "content-type":"application/json", "accept":"text/event-stream"}
                    # Set by the registered controller; the child cannot override it.
                    headers.update(owner.request_headers)
                    for name in ("anthropic-version", "anthropic-beta"):
                        if self.headers.get(name):
                            headers[name] = self.headers[name]
                    owner.capture_json(folder / "request_protocol.json", {k:v for k,v in headers.items() if k != "x-api-key"})
                    completion = Completion()
                    with owner.state:
                        owner.require_open()
                    with owner.upstream.stream("POST", owner.base_url + self.path, content=raw, headers=headers) as response:
                        owner.capture_json(folder / "http_status.json", {"status":response.status_code, "content_type":response.headers.get("content-type")})
                        if response.status_code != 200:
                            owner.capture(folder / "upstream_error.body", b"")
                            for chunk in response.iter_bytes():
                                owner.capture(folder / "upstream_error.body", chunk, append=True)
                            raise BudgetStop("upstream HTTP response did not confirm a completed charge")
                        if "text/event-stream" not in response.headers.get("content-type", ""):
                            raise BudgetStop("unregistered upstream response format")
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.end_headers()
                        sent = True
                        deferred = []
                        owner.capture(folder / "response.sse", b"")
                        for chunk in response.iter_bytes():
                            owner.capture(folder / "response.sse", chunk, append=True)
                            completion.feed(chunk)
                            if completion.stopped:
                                deferred.append(chunk)
                            else:
                                self.wfile.write(chunk); self.wfile.flush()
                        with owner.state:
                            owner.require_writable()
                            owner.messages.finish(ticket, folder, completion.final(), stream_complete=True)
                        # Do not let the child issue its next request before
                        # the preceding completed request has been accounted.
                        for chunk in deferred:
                            self.wfile.write(chunk)
                        self.wfile.flush()
                except Exception as exc:
                    owner.fail(exc)
                    if not sent:
                        try:
                            self.reply(402, {"type":"error", "error":{"type":"invalid_request_error", "message":"registered native attempt stopped; inspect its retained receipt"}})
                        except (OSError, BrokenPipeError):
                            pass
                finally:
                    self.close_connection = True
            def do_GET(self):
                self.reply(404, {"type":"error", "error":{"type":"not_found_error", "message":"no registered read endpoint"}})
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.05), daemon=True)
        self.thread.start()
        try:
            yield f"http://127.0.0.1:{self.server.server_port}"
        finally:
            self.close_admission()
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=2)
            with self.state:
                self.state.wait_for(lambda: self.active_handlers == 0, timeout=cleanup_timeout)
                self.unfinished_handlers = self.active_handlers
                self.frozen = True
            # HTTP pool closure can block on an in-flight socket. Receipt
            # finalization is bounded; frozen handlers cannot settle charges
            # or change evidence afterward. Unknown reservations stay pending.
            def close_clients():
                try:
                    self.upstream.close()
                    close = getattr(self.messages.client, "close", None)
                    if close:
                        close()
                except Exception:
                    pass
            closer = threading.Thread(target=close_clients, daemon=True)
            closer.start()
            closer.join(timeout=cleanup_timeout)
