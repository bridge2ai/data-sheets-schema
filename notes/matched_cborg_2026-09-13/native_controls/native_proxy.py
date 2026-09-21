"""Draft native-runtime CBORG transport; never launched without its own review.

The child receives a loopback token, never the provider key. Original native
JSON and server-sent-event bodies are retained. Every paid request uses the
same sequence ledger as the direct API arm and is admitted before forwarding.
"""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import threading
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx

from budgeted_cborg import (BudgetStop, CBORG_ENDPOINTS, CappedMessages, LEGACY_UPSTREAM_READ_SECONDS,
                            POLICY_COUNT_TRY_SECONDS, UPSTREAM_CONNECT_SECONDS, digest, now, write_new)
from data_sheets_schema.stream_evidence import CORRELATION_HEADERS, _identifier


def response_metadata(response):
    """Bounded provider diagnostics; never a source of completed usage/cost.

    Capture before reading any body, including error bodies. Values are kept
    only under these named headers and are never forwarded to the child.
    """
    headers = response.headers
    content_type = headers.get("content-type")
    if (not isinstance(content_type, str) or len(content_type) > 160 or
            not re.fullmatch(r"[A-Za-z0-9!#$%&'*+.^_`|~-]+/[A-Za-z0-9!#$%&'*+.^_`|~-]+"
                             r"(?:; ?charset=[A-Za-z0-9._-]+)?", content_type)):
        content_type = None
    result = {"status": response.status_code, "content_type": content_type,
              "correlation_headers": {name: value for name in CORRELATION_HEADERS
                  if (value := _identifier(headers.get(name))) is not None}}
    cost = headers.get("x-litellm-response-cost")
    # Preserve exact decimal text, avoiding float rounding/overflow. Refuse
    # signs, whitespace, NaN/Infinity, joined duplicate headers and huge input.
    if (isinstance(cost, str) and len(cost) <= 64 and
            re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", cost)):
        try:
            number = Decimal(cost)
        except InvalidOperation:
            pass
        else:
            if number.is_finite() and number >= 0:
                result["reported_cost"] = {"header": "x-litellm-response-cost", "value": cost,
                                           "diagnostic_only": True}
    return result


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


UNCONFIRMED_CHARGE = "upstream HTTP response did not confirm a completed charge"


class UpstreamStall(BudgetStop):
    """A provider 5xx before any response byte reached the child. It reads as
    the historical stop reason wherever no stall policy survives it."""
    def __init__(self, status):
        super().__init__(UNCONFIRMED_CHARGE)
        self.status = status


#: Failures after the request left: the provider may have begun work. A
#: connection that was never made (connect or pool errors) sent nothing, so it
#: is not a stall; it stops the attempt as before instead of burning the
#: allowance during an outage (#2156).
POST_SEND_FAILURES = (httpx.ReadTimeout, httpx.WriteTimeout, httpx.ReadError, httpx.WriteError,
                      httpx.RemoteProtocolError)


def stall_evidence(exc, upstream_status=None):
    """What made a paid request a stall, or None. A provider status below 500
    is never a stall, whatever failed after it arrived (#2156). Otherwise a
    provider 5xx, or a failure of the exchange after the request was sent,
    qualifies. Provider exception text is never kept."""
    if upstream_status is not None and upstream_status < 500:
        return None
    if isinstance(exc, UpstreamStall):
        return {"kind": "upstream_http_status", "http_status": exc.status}
    if isinstance(exc, POST_SEND_FAILURES):
        return {"kind": "upstream_transport", "error_type": type(exc).__name__,
                **({"http_status": upstream_status} if upstream_status is not None else {})}
    return None


def validated_stall_policy(value):
    """{count_attempts: 1..5, max_stall_debits: 0..10} or None (#2150)."""
    if value is None:
        return None
    if (not isinstance(value, dict) or set(value) != {"count_attempts", "max_stall_debits"}
            or type(value["count_attempts"]) is not int or not 1 <= value["count_attempts"] <= 5
            or type(value["max_stall_debits"]) is not int or not 0 <= value["max_stall_debits"] <= 10):
        raise BudgetStop("native stall policy needs count_attempts 1-5 and max_stall_debits 0-10")
    return dict(value)


class NativeProxy:
    def __init__(self, *, sdk, ledger, attempt, evidence, model, prices, verify,
                 provider_key, base_url, upstream=None, request_headers=None,
                 upstream_read_timeout_seconds=None, stall_policy=None, count_pause=None):
        if base_url not in CBORG_ENDPOINTS:
            raise BudgetStop("native runtime requires the registered CBORG endpoint")
        # Opt-in only: None keeps every legacy path byte for byte (#2150).
        self.stall_policy = validated_stall_policy(stall_policy)
        self.stalls_survived = 0
        if upstream_read_timeout_seconds is not None and (
                type(upstream_read_timeout_seconds) is not int or upstream_read_timeout_seconds <= 0):
            raise BudgetStop('native upstream read timeout must be positive whole seconds')
        # Per-request override only: the shared SDK counting client and all
        # legacy callers keep their original timeout. None is never forwarded
        # as a timeout keyword, since HTTPX interprets that as unbounded.
        self.stream_options = ({'timeout': httpx.Timeout(LEGACY_UPSTREAM_READ_SECONDS, connect=UPSTREAM_CONNECT_SECONDS,
                                                         read=upstream_read_timeout_seconds)}
                               if upstream_read_timeout_seconds is not None else {})
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
        self.admission_closed = threading.Event()
        self.closed = False
        self.frozen = False
        self.active_handlers = 0
        self.unfinished_handlers = 0
        self.messages = CappedMessages(sdk, ledger=ledger, attempt=attempt,
            evidence=Path(evidence), model=model, prices=prices, verify=verify,
            mutation_guard=self.mutation_guard,
            **({"count_attempts": self.stall_policy["count_attempts"],
                "count_timeout": POLICY_COUNT_TRY_SECONDS,
                # The pause ends at once when admission closes (#2157).
                "count_pause": count_pause or (lambda seconds: self.admission_closed.wait(seconds))}
               if self.stall_policy is not None else {}))
        self.upstream = upstream or httpx.Client(
            timeout=httpx.Timeout(LEGACY_UPSTREAM_READ_SECONDS, connect=UPSTREAM_CONNECT_SECONDS), follow_redirects=False)
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
            self.admission_closed.set()

    def survive_stall(self, ticket, folder, evidence):
        """Count a stalled request at its whole reservation and leave the
        attempt open, under the registered allowance. Raises when the policy
        does not cover it; the caller then stops the attempt as before."""
        if self.stall_policy is None or ticket is None or evidence is None:
            raise BudgetStop("no registered stall policy covers this failure")
        with self.state:
            self.require_writable()
            self.require_open()
            index = self.messages.debit_stall(ticket, maximum=self.stall_policy["max_stall_debits"],
                                              evidence=evidence)
            self.stalls_survived = index
            try:
                # The ledger row already carries this evidence, so a failed
                # copy beside the request must not undo the survival (#2158).
                write_new(folder / "stall.json", {"at": now(), "stall_index": index, **evidence,
                    "settlement": "whole reservation counted; provider charge unconfirmed",
                    "child_reply_attempted": 503})
            except Exception:
                pass

    def stall_reply(self, handler):
        """Tell the child its request may be repeated. Nothing of the
        provider's reply is forwarded."""
        handler.reply(503, {"type":"error", "error":{"type":"api_error",
            "message":"registered transport stall; the request may be retried"}},
            headers={"retry-after": "1", "x-should-retry": "true"})

    def close_admission(self):
        with self.state:
            self.closed = True
            self.admission_closed.set()

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
            def reply(self, code, value, headers=None):
                raw = json.dumps(value).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                for name, text in (headers or {}).items():
                    self.send_header(name, text)
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
                ticket = folder = upstream_status = None
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
                        count = owner.messages.count_tokens(fields)
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
                    with owner.upstream.stream("POST", owner.base_url + self.path, content=raw, headers=headers,
                                               **owner.stream_options) as response:
                        owner.capture_json(folder / "http_status.json", response_metadata(response))
                        upstream_status = response.status_code
                        if response.status_code != 200:
                            owner.capture(folder / "upstream_error.body", b"")
                            if owner.stall_policy is not None and response.status_code >= 500:
                                # The status already establishes the policy's
                                # stall. Draining an arbitrary error body could
                                # outlive the client's retry window (#2159).
                                raise UpstreamStall(response.status_code)
                            for chunk in response.iter_bytes():
                                owner.capture(folder / "upstream_error.body", chunk, append=True)
                            if response.status_code >= 500:
                                raise UpstreamStall(response.status_code)
                            raise BudgetStop(UNCONFIRMED_CHARGE)
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
                    if not sent and owner.stall_policy is not None:
                        # Nothing reached the child, so its own retry can
                        # continue the session once the charge is counted.
                        try:
                            owner.survive_stall(ticket, folder, stall_evidence(exc, upstream_status))
                        except Exception:
                            pass
                        else:
                            try:
                                owner.stall_reply(self)
                            except (OSError, BrokenPipeError):
                                owner.fail(BudgetStop("native client closed before the registered stall reply"))
                            return
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
            def close_clients():
                if self.stall_policy is not None:
                    # Policy clients own killable I/O workers. Cancel counting
                    # first, independently of streaming cleanup, so shutdown
                    # does not leave a count alive behind a socket close.
                    for resource in (self.messages.client, self.upstream):
                        try:
                            close = getattr(resource, "close", None)
                            if close:
                                close()
                        except Exception:
                            pass
                else:
                    try:
                        self.upstream.close()
                        close = getattr(self.messages.client, "close", None)
                        if close:
                            close()
                    except Exception:
                        pass
            closer = threading.Thread(target=close_clients, daemon=True)
            if self.stall_policy is not None:
                # Wake active policy handlers before measuring closure. They
                # still face the closed-admission/evidence-freeze guards.
                closer.start()
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
            if self.stall_policy is None:
                closer.start()
            closer.join(timeout=cleanup_timeout)
