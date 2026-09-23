"""Killable, total-deadline raw transport for an opted-in native audit.

Only the parent sees the ledger or evidence directory. A fresh worker owns one
HTTP exchange; anonymous pipes carry its configuration and exact body bytes.
Before response headers the entire operation has one monotonic deadline,
including starting the worker and delivering the request. After headers the
existing read-inactivity limit applies. No worker survives its context or close.
"""
from contextlib import contextmanager
import base64
import json
import math
import os
from pathlib import Path
import select
import ssl
import struct
import subprocess
import sys
import threading
import time

import httpx

MAX_REQUEST_BYTES = 32 * 1024 * 1024
MAX_FRAME_BYTES = 48 * 1024 * 1024
MAX_METADATA_BYTES = 1024 * 1024
CHUNK_BYTES = 65536
ERROR_NAMES = frozenset({"ConnectTimeout", "PoolTimeout", "ConnectError", "ProxyError",
    "UnsupportedProtocol", "ReadTimeout", "WriteTimeout", "ReadError", "WriteError",
    "RemoteProtocolError", "LocalProtocolError", "DecodingError"})
LOCAL_ERROR_NAME = "BoundWorkerProtocolError"


class BoundWorkerProtocolError(RuntimeError):
    """A local worker/IPC failure, never evidence of a provider stall (#2160)."""
    def __init__(self, message, *, request=None):
        super().__init__(message)
        self.request = request


def _positive(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError("transport deadlines must be finite positive seconds")
    return float(value)


def _worker_command():
    return [sys.executable, "-B", str(Path(__file__).resolve()), "--stream-worker"]


def _frame(kind, payload):
    body = kind + payload
    if len(body) > MAX_FRAME_BYTES:
        raise ValueError("bounded transport frame too large")
    return struct.pack("!I", len(body)) + body


def _json(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=False).encode("utf-8")


class _Worker:
    def __init__(self, deadline, request):
        self.deadline, self.request = deadline, request
        self.sent = False
        self.headers_received = False
        self.buffer = bytearray()
        self._close_lock = threading.Lock()
        self._closed = False
        self.process = subprocess.Popen(_worker_command(), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0,
            env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"})
        try:
            os.set_blocking(self.process.stdin.fileno(), False)
            os.set_blocking(self.process.stdout.fileno(), False)
        except BaseException:
            # stream() cannot register this worker until construction returns.
            # A partial setup therefore owns its cleanup here (#2161).
            self.close()
            raise

    def timeout(self):
        # Absence of a sent witness fails closed: never burn a stall allowance
        # merely because DNS, startup, pooling, connect or TLS took too long.
        cls = httpx.ReadTimeout if self.sent else httpx.ConnectTimeout
        return cls("bounded transport deadline exceeded", request=self.request)

    def _ready(self, fd, *, write, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise self.timeout()
        readable, writable, _ = select.select([] if write else [fd], [fd] if write else [], [], remaining)
        if not (writable if write else readable):
            raise self.timeout()

    def send(self, payload):
        data = memoryview(_frame(b"C", payload))
        fd = self.process.stdin.fileno()
        while data:
            self._ready(fd, write=True, deadline=self.deadline)
            try:
                amount = os.write(fd, data)
            except BlockingIOError:
                continue
            if not amount:
                raise BoundWorkerProtocolError("bounded transport input closed", request=self.request)
            data = data[amount:]
        self.process.stdin.close()

    def _take(self, size, deadline):
        fd = self.process.stdout.fileno()
        while len(self.buffer) < size:
            self._ready(fd, write=False, deadline=deadline)
            try:
                raw = os.read(fd, min(CHUNK_BYTES, size - len(self.buffer)))
            except BlockingIOError:
                continue
            if not raw:
                raise BoundWorkerProtocolError("bounded transport worker ended without a complete result", request=self.request)
            self.buffer.extend(raw)
        result = bytes(self.buffer[:size])
        del self.buffer[:size]
        return result

    def receive(self, deadline):
        length = struct.unpack("!I", self._take(4, deadline))[0]
        if not 1 <= length <= MAX_METADATA_BYTES:
            raise BoundWorkerProtocolError("invalid bounded transport frame length", request=self.request)
        body = self._take(length, deadline)
        kind, payload = body[:1], body[1:]
        if kind == b"P":
            if payload != b"sent" or self.sent:
                raise BoundWorkerProtocolError("invalid bounded transport progress", request=self.request)
            self.sent = True
        elif kind == b"E":
            try:
                data = json.loads(payload)
                if (not isinstance(data, dict) or set(data) != {"error", "sent"}
                        or not isinstance(data["error"], str)
                        or data["error"] not in ERROR_NAMES | {LOCAL_ERROR_NAME}
                        or type(data["sent"]) is not bool or data["sent"] != self.sent):
                    raise ValueError()
            except (ValueError, TypeError, KeyError):
                raise BoundWorkerProtocolError("invalid bounded transport error", request=self.request) from None
            name = data["error"]
            if name == LOCAL_ERROR_NAME:
                raise BoundWorkerProtocolError("bounded transport worker failed locally", request=self.request)
            if not self.sent:
                name = "ConnectTimeout" if name.endswith("Timeout") else "ConnectError"
            raise getattr(httpx, name)("bounded transport worker failed", request=self.request)
        return kind, payload

    def close(self):
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
            try:
                if self.process.poll() is None:
                    self.process.kill()
                self.process.wait()
            finally:
                self.process.stdin.close()
                self.process.stdout.close()


class _Response:
    def __init__(self, worker, status, headers, read_timeout, total_deadline=None):
        self._worker, self._read_timeout = worker, read_timeout
        self._total_deadline = total_deadline
        self.status_code = status
        self.headers = httpx.Headers([(key.encode("ascii"), value.encode("latin-1")) for key, value in headers])
        self._iterated = False

    def iter_bytes(self):
        if self._iterated:
            raise httpx.StreamConsumed()
        self._iterated = True
        while True:
            deadline = time.monotonic() + self._read_timeout
            if self._total_deadline is not None:
                deadline = min(deadline, self._total_deadline)
                if time.monotonic() >= deadline:
                    raise self._worker.timeout()
            kind, payload = self._worker.receive(deadline)
            if self._total_deadline is not None and time.monotonic() >= self._total_deadline:
                raise self._worker.timeout()
            if kind == b"D":
                if not payload or len(payload) > CHUNK_BYTES:
                    raise BoundWorkerProtocolError("invalid bounded stream chunk", request=self._worker.request)
                yield payload
            elif kind == b"Z" and not payload:
                return
            else:
                raise BoundWorkerProtocolError("invalid bounded stream event", request=self._worker.request)


class BoundedStreamClient:
    """Synchronous NativeProxy facade; GETs use only the supplied metadata client."""
    def __init__(self, delegate=None, *, ca_bundle=None, read_timeout_seconds=1800,
                 connect_timeout_seconds=20, total_timeout_seconds=None):
        self.delegate = delegate
        self.read_timeout = _positive(read_timeout_seconds)
        self.connect_timeout = _positive(connect_timeout_seconds)
        self.total_timeout = (_positive(total_timeout_seconds)
                              if total_timeout_seconds is not None else None)
        self.ca_data = Path(ca_bundle).read_text(encoding="ascii") if ca_bundle is not None else None
        self._lock = threading.Lock()
        self._closed = False
        self._workers = set()

    @property
    def is_closed(self):
        return self._closed

    def get(self, *args, **kwargs):
        with self._lock:
            if self._closed:
                raise RuntimeError("bounded transport is closed")
            if self.delegate is None:
                raise RuntimeError("no metadata transport supplied")
        return self.delegate.get(*args, **kwargs)

    @contextmanager
    def stream(self, method, url, *, content, headers, timeout=None):
        started = time.monotonic()
        deadline = started + self.read_timeout + self.connect_timeout
        # Opt-in whole exchange bound (#2304): progress/pings cannot extend it.
        # Counting and controller admission happen before stream(), outside it.
        total_deadline = (started + self.total_timeout if self.total_timeout is not None else None)
        if total_deadline is not None:
            deadline = min(deadline, total_deadline)
        if not isinstance(content, bytes) or len(content) > MAX_REQUEST_BYTES:
            raise ValueError("bounded transport requires bounded exact request bytes")
        if timeout is not None:
            selected = httpx.Timeout(timeout)
            if selected.read != self.read_timeout or selected.connect != self.connect_timeout:
                raise ValueError("stream override differs from the registered bounds")
        request = httpx.Request(method, url)
        payload = _json({"method": method, "url": str(url), "headers": dict(headers),
            "content": base64.b64encode(content).decode("ascii"), "ca_data": self.ca_data,
            "read_timeout": self.read_timeout, "connect_timeout": self.connect_timeout})
        if time.monotonic() >= deadline:
            raise httpx.ConnectTimeout("bounded transport setup deadline exceeded", request=request)
        worker = None
        try:
            with self._lock:
                if self._closed:
                    raise httpx.ConnectError("bounded transport is closed", request=request)
                worker = _Worker(deadline, request)
                self._workers.add(worker)
            worker.send(payload)
            while True:
                kind, raw = worker.receive(deadline)
                if kind == b"P":
                    continue
                if kind != b"H" or not worker.sent:
                    raise BoundWorkerProtocolError("missing bounded transport headers", request=request)
                try:
                    value = json.loads(raw)
                    if (not isinstance(value, dict) or set(value) != {"status", "headers"}
                            or type(value["status"]) is not int or not 100 <= value["status"] <= 599
                            or not isinstance(value["headers"], list)
                            or any(not isinstance(row, list) or len(row) != 2
                                   or any(not isinstance(s, str) for s in row) for row in value["headers"])):
                        raise ValueError()
                    response = _Response(worker, value["status"], value["headers"], self.read_timeout,
                                         total_deadline)
                except (ValueError, TypeError, KeyError):
                    raise BoundWorkerProtocolError("invalid bounded transport headers", request=request) from None
                worker.headers_received = True
                if time.monotonic() >= deadline:
                    raise worker.timeout()
                yield response
                return
        finally:
            if worker is not None:
                # Kill and reap before any exception reaches the proxy's debit,
                # evidence, retry or shutdown handling.
                worker.close()
                with self._lock:
                    self._workers.discard(worker)

    def close(self):
        with self._lock:
            self._closed = True
            workers = tuple(self._workers)
        for worker in workers:
            worker.close()
        if self.delegate is not None:
            self.delegate.close()


def _write_frame(kind, payload):
    sys.stdout.buffer.write(_frame(kind, payload))
    sys.stdout.buffer.flush()


def _read_input():
    source = sys.stdin.buffer
    prefix = source.read(4)
    if len(prefix) != 4:
        raise ValueError("missing worker configuration")
    length = struct.unpack("!I", prefix)[0]
    if not 1 <= length <= MAX_FRAME_BYTES:
        raise ValueError("invalid worker configuration length")
    data = source.read(length)
    if len(data) != length or data[:1] != b"C":
        raise ValueError("incomplete worker configuration")
    return json.loads(data[1:])


def _run_worker():
    sent = False
    try:
        config = _read_input()
        verify = True
        if config["ca_data"] is not None:
            verify = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            verify.verify_flags &= ~ssl.VERIFY_X509_PARTIAL_CHAIN
            verify.load_verify_locations(cadata=config["ca_data"])

        def trace(event, info):
            nonlocal sent
            if not sent and event in {"http11.send_request_headers.started", "http2.send_request_headers.started"}:
                _write_frame(b"P", b"sent")
                sent = True

        with httpx.Client(verify=verify, trust_env=False, follow_redirects=False,
                # Preserve the established write/pool inactivity settings;
                # the parent total deadline bounds these phases as a whole.
                timeout=httpx.Timeout(1800, connect=config["connect_timeout"], read=config["read_timeout"])) as client:
            with client.stream(config["method"], config["url"],
                    content=base64.b64decode(config["content"], validate=True), headers=config["headers"],
                    extensions={"trace": trace}) as response:
                _write_frame(b"H", _json({"status": response.status_code,
                    "headers": [[key.decode("ascii"), value.decode("latin-1")]
                                for key, value in response.headers.raw]}))
                for chunk in response.iter_bytes():
                    for offset in range(0, len(chunk), CHUNK_BYTES):
                        _write_frame(b"D", chunk[offset:offset + CHUNK_BYTES])
                _write_frame(b"Z", b"")
    except Exception as exc:
        name = type(exc).__name__
        if not isinstance(exc, httpx.HTTPError) or name not in ERROR_NAMES:
            name = LOCAL_ERROR_NAME
        try:
            _write_frame(b"E", _json({"error": name, "sent": sent}))
        except (BrokenPipeError, OSError):
            pass


if __name__ == "__main__":
    if sys.argv[1:] != ["--stream-worker"]:
        raise SystemExit("bounded stream worker entry only")
    _run_worker()
