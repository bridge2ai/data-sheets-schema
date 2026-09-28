"""Actual child transport and synthetic sockets only; no provider or ledger."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import select
import signal
import socket
import ssl
import struct
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

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
            # One exchange per connection. Keep-alive would have this daemon
            # thread read a next request line from a socket whose worker was
            # killed, and a reset there prints a traceback, possibly during
            # interpreter finalisation (#2540, #2604). Every worker opens its
            # own connection, so no test relies on keep-alive.
            self.close_connection = True
            try:
                respond(self, self.rfile.read(int(self.headers["content-length"])))
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


# Real-time bounds. None holds interpreter start-up, and each keeps at least a
# threefold margin over the maximum measured for it. KILL_GAP, PARENT_GAP and
# CALL_GAP were measured over 768 runs of the two stream tests (the count test's in
# test_bounded_transport.py) under 64-256 concurrent copies on 10 cores, at load
# 114-336 (2026-09-27); each later constant states its own samples and load. Most
# time steps inside one process. PARENT_GAP and READ_HOP_SECONDS also include a hop
# between the worker and another process, and say so; CALL_GAP's sum includes the
# header flush-to-yield hop PARENT_GAP bounds, and READ_EARLY exists because of the
# first chunk's worker-to-parent lead (#2793). Each bound gives up power
# against shorter delays: origin/main's wall-clock totals caught delays of about
# 1.2-1.5 s, but flaked under load (#2618, #2643, #2678, #2698).

#: The parent's close decision (the deadline expiring, or leaving the context) to
#: the worker's SIGKILL. Measured median 0.1 ms, p99 69 ms, max 141 ms (load 336).
#: It rejects a grace of 0.5 s or more before the kill; a shorter one passes.
KILL_GAP_SECONDS = .5

#: Gaps around a running worker: the parent's spawn to its request write, the
#: server's receipt of the request to the kill, and the server's header flush to the
#: yielded response. A worker-to-parent pipe hop is in them (#2676, #2677). Measured
#: maxima: spawn to the request written 216 ms, receipt to kill 102 ms, header flush to yield
#: 791 ms (median 42 ms, p99 613 ms). It rejects a delay of 2.5 s or more in any of
#: them; a shorter one passes.
PARENT_GAP_SECONDS = 2.5

#: The registered read timeout of the after-headers test. The worker applies it to
#: every read (HTTPX's read-inactivity timeout) and the parent to every chunk, so it
#: bounds two phases that must complete, not only the withheld read it ends
#: (#2604, #2737):
#: - the worker's wait for the headers once its request is written: the test
#:   server's accept, handler thread and response, in the loaded pytest process.
#:   Measured median 20-48 ms, p99 406-410 ms, max 588 ms over 1,536 exchanges
#:   under 256 concurrent copies at load 176-477;
#: - the first chunk's hop from the worker to the parent, already flushed by the
#:   server. Measured max 373 ms over the same 1,536, and 324 ms over 1,536 more at
#:   load 82-272; the same hop for the headers (PARENT_GAP_SECONDS) reached 791 ms
#:   at load 336.
#: This keeps threefold on all of them. A phase of 2.5 s or more fails the test,
#: where origin/main's 0.3 s bound failed one of 0.3 s.
READ_HOP_SECONDS = 2.5

#: How much sooner than READ_HOP_SECONDS after the parent begins its second read
#: the withheld read may end. The worker's read timer starts when it has written
#: the first chunk, before the parent begins that read (#2762). Measured at most
#: 43 ms early over 1,536 reads at load 176-477, and 20 ms over 960 at load
#: 435-548. It rejects a read deadline that fires more than about 0.5 s early; one
#: exactly 0.5 s early can still pass, as the bound is inclusive (#2807).
READ_EARLY_SECONDS = .5

#: The whole call less the worker's start-up window (from just before Popen to the
#: server receiving the request, or flushing its headers). That covers every
#: in-process step, including a wait before the spawn and one after the kill (#2696).
#: Measured median 207-278 ms, p99 870-911 ms, max 1129 ms (load 336). It rejects
#: 3.5 s or more spent outside start-up; less passes.
CALL_GAP_SECONDS = 3.5

#: From a parent deadline to the refusal it raises: the wake-up of the parent's
#: timed wait and, for the absolute bound, the entry into stream(), in-process
#: (#2735). Measured median 15 ms, p99 72 ms, max 203 ms over 2,421 refusals under
#: 256 concurrent copies at load 296-518, and max 156 ms over 2,702 at load 169-307;
#: none was early. The timed wait's wake-up in the count test reached 1.17 s at load
#: ~450 (#2697). It rejects a refusal 1.5 s late or more, at every rung of the
#: buffered test's ladder; a later one than origin/main's 1.5 s total still passes.
REFUSAL_GAP_SECONDS = 1.5

#: After a refusal: from the refusal to the worker's SIGKILL, and from the worker's
#: reap to the caller receiving the refusal. Both are the exception unwinding
#: through the stream context, in-process (#2760). Measured: refusal to kill median
#: 0.1 ms, p99 92 ms, max 759 ms; reap to release max 129 ms; over 3,427 refusals
#: under 320 concurrent copies at load 108-510. It rejects a delay of 2.5 s or more
#: on either side of the reap. KILL_GAP_SECONDS (0.5 s) was measured at load up to
#: 336 only, on other paths.
UNWIND_GAP_SECONDS = 2.5

#: The reap of a killed worker. It is a process-level cost, so this is a hang guard,
#: as REAP_SECONDS is in test_bounded_transport.py. Measured median 201 ms, p99
#: 864 ms, max 1.60 s over the same 3,427 reaps (#2760).
REAP_SECONDS = 10


# A hang guard, not a real-time bound: nothing measured it and a passing run never
# reaches it.

#: The bounds a test gives a worker where no deadline is its subject. A pre-header
#: bound also pays for the worker's interpreter start-up, which took about 14 s at
#: load 450 (#2697), so a short one ended exchanges these tests expected to finish
#: (#2604). This is a hang guard, not a measurement: a passing run never reaches it,
#: and a run that did would raise a timeout the test does not expect, so it is never
#: what ends a passing exchange.
HANG_SECONDS = 120


def killed_before_reaped(process, killed_at=None, reaped_at=None):
    """For each wait on `process`, whether it had been sent SIGKILL (or was
    already reaped) when the wait began (#2540, #2569 reviews).

    A close that waits on a live worker first through `Popen.wait`, for any
    length, records False. A grace spent some other way (a sleep, an event
    wait) is not seen here (#2619): each test bounds it by the real time from
    its close decision to the SIGKILL, appended to `killed_at` (#2618). The
    instant each wait returns with the worker reaped is appended to `reaped_at`
    (#2760), and so is the first poll that finds it reaped, since poll() reaps too:
    a stall after a poll-reap is then charged to the release, not the reap (#2813)."""
    killed, waits = [], []
    real_signal, real_wait, real_poll = process.send_signal, process.wait, process.poll
    def send_signal(sig):
        if sig == signal.SIGKILL:
            killed.append(sig)
            if killed_at is not None:
                killed_at.append(time.monotonic())
        return real_signal(sig)
    def wait(*args, **kwargs):
        waits.append(bool(killed) or process.returncode is not None)
        try:
            return real_wait(*args, **kwargs)
        finally:
            if reaped_at is not None and process.returncode is not None:
                reaped_at.append(time.monotonic())
    def poll(*args, **kwargs):
        result = real_poll(*args, **kwargs)
        if reaped_at is not None and result is not None and not reaped_at:
            reaped_at.append(time.monotonic())
        return result
    process.send_signal, process.wait, process.poll = send_signal, wait, poll
    return waits


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
    # The verdict is the bytes and where the secret went; the bounds are hang guards (#2604).
    client = bounded.BoundedStreamClient(read_timeout_seconds=HANG_SECONDS, connect_timeout_seconds=HANG_SECONDS)
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


class ParentClock:
    """The parent's monotonic time, moved only by the phases the test names (#2540).

    The worker, its socket and the header drips stay real. Only the parent's
    deadline accounting reads this clock, so a loaded scheduler can neither
    spend the budget on a slow interpreter start nor move the instant of
    refusal. Starting the worker and writing the request each spend a fixed
    part of the budget, so both phases still count against the one deadline.
    The clock reaches the deadline only from inside the parent's own wait,
    once the server holds the request and the parent holds the sent witness.
    Every move is on the parent's thread, so nothing moves the clock between
    the parent reading it and waiting on it.

    The exact-deadline check relies on the product reading
    `bounded.time.monotonic` and waiting with `bounded.select.select` for
    exactly the remaining time. A refactor to `selectors` or to sliced polls
    fails this test rather than slipping past it."""
    def __init__(self, *, startup, write, deadline, expire_when):
        self.now, self.waits, self.expired_at = 1000.0, [], None
        self.startup, self.write, self.deadline = startup, write, deadline
        self.expire_when, self._written = expire_when, False

    def monotonic(self):
        return self.now

    def spawned(self):
        self.now += self.startup

    def select(self, readable, writable, errors, timeout):
        end = self.now + timeout
        self.waits.append(end)
        if end != pytest.approx(self.deadline, abs=1e-9):
            raise AssertionError(f"the parent waits until {end}, not its one deadline {self.deadline}")
        if writable and not self._written:
            self._written, self.now = True, self.now + self.write
        hang = time.monotonic() + 60
        while True:
            if not writable and self.now < self.deadline and self.expire_when():
                self.now, self.expired_at = self.deadline, time.monotonic()   # real time, for the kill gap
            expired = self.now >= end
            ready = select.select(readable, writable, errors, 0 if expired else .01)
            if expired or any(ready):
                return ready
            if time.monotonic() > hang:
                raise AssertionError("the sent witness never arrived")


def test_total_preheader_deadline_outwaits_neither_header_drips_nor_write_phase(processes, monkeypatch):
    # Each byte arrives comfortably inside the HTTPX read-inactivity timeout.
    # The header stays incomplete for as long as the worker is connected, so
    # only the parent's total deadline can refuse it. The parent's budget is
    # virtual (ParentClock); the real-time limits bound only the worker, so
    # they can be generous at no cost to the verdict.
    read, connect = 5, 2
    sent, stop = threading.Event(), threading.Event()
    client = bounded.BoundedStreamClient(read_timeout_seconds=read, connect_timeout_seconds=connect)
    def witnessed():
        with client._lock:
            return sent.is_set() and any(worker.sent for worker in client._workers)
    clock = ParentClock(startup=.5, write=1, deadline=1000.0 + read + connect, expire_when=witnessed)
    monkeypatch.setattr(bounded, "time", SimpleNamespace(monotonic=clock.monotonic))
    monkeypatch.setattr(bounded, "select", SimpleNamespace(select=clock.select))
    spawn, reaped, killed_at, spawned_at, written_at, sent_at = bounded.subprocess.Popen, [], [], [], [], []
    popen_at = []
    def charged(*args, **kwargs):
        clock.spawned()
        popen_at.append(time.monotonic())          # the start-up window opens here
        process = spawn(*args, **kwargs)
        spawned_at.append(time.monotonic())          # Popen returns before the interpreter starts
        reaped.append(killed_before_reaped(process, killed_at))
        return process
    monkeypatch.setattr(bounded.subprocess, "Popen", charged)
    real_send = bounded._Worker.send
    def timed_send(worker, payload):
        try:
            return real_send(worker, payload)
        finally:
            written_at.append(time.monotonic())      # the request is in the worker's pipe
    monkeypatch.setattr(bounded._Worker, "send", timed_send)
    def respond(handler, body):
        sent_at.append(time.monotonic())
        sent.set()
        header = b"HTTP/1.1 200 OK\r\nX-Slow: never-finished"
        for index in range(400):
            handler.wfile.write(header[index:index + 1] or b"."); handler.wfile.flush()
            if stop.wait(.05):
                return
    with endpoint(respond) as url:
        try:
            with pytest.raises(httpx.ReadTimeout, match="bounded transport deadline exceeded"):
                called = time.monotonic()
                with client.stream("POST", url, content=b"synthetic", headers={}):
                    pytest.fail("incomplete headers were accepted")
            returned = time.monotonic()
        finally:
            stop.set()
    # Start-up, the request write and the dripping header all waited on one
    # deadline, read + connect after entry, and the clock reached it only
    # there: no phase moved it. The refusal is the parent's own, and the
    # worker was killed once the deadline passed, within KILL_GAP_SECONDS of
    # real time, and never waited on first (#2618).
    assert sent.is_set() and len(clock.waits) >= 3 and clock.now == clock.deadline
    (process, _, _), = processes
    assert process.returncode == -signal.SIGKILL
    (waits,) = reaped
    assert waits and all(waits), "the worker was waited on before it was killed"
    assert len(killed_at) == 1, f"expected one SIGKILL, saw {len(killed_at)}"          # #2644
    assert killed_at[0] - clock.expired_at < KILL_GAP_SECONDS, "the worker was killed long after its deadline"
    # The virtual clock is charged only inside the parent's own waits, so real time the
    # parent spends elsewhere is bounded here (#2677): from its spawn to the request write,
    # and from the server's receipt of the request to the kill.
    assert written_at[0] - spawned_at[0] < PARENT_GAP_SECONDS, "the request was written long after the spawn"
    assert killed_at[0] - sent_at[0] < PARENT_GAP_SECONDS, "the worker was killed long after the request arrived"
    # And the whole call less the worker's start-up window, from just before Popen to
    # the server's receipt of the request: a wait before the spawn, or after the kill
    # before the refusal reaches the caller, is in-process time too (#2696).
    assert (returned - called) - (sent_at[0] - popen_at[0]) < CALL_GAP_SECONDS, \
        "the call spent long outside the worker's start-up"
    assert not client._workers
    client.close()


def test_after_headers_read_deadline_and_exact_incremental_chunks(processes):
    # The server flushes the first chunk with the headers and withholds the rest
    # until the test has its verdict, so only a read deadline can end the second
    # read, and it must end it within READ_HOP_SECONDS plus the parent's wake-up
    # (#2734). A watchdog would release the rest after HANG_SECONDS; the test
    # asserts it did not. The parent's pre-header bound is a hang guard, so the
    # worker's interpreter start-up is no longer charged to a 1.3 s budget
    # (#2604); what READ_HOP_SECONDS does bound before the headers is said at its
    # definition (#2737). A first read that timed out fails on `received`: a
    # ReadTimeout from anywhere but the second read is not the one this test is
    # about.
    first_sent, done, released, waited = threading.Event(), threading.Event(), [], []
    def respond(handler, body):
        handler.send_response(200); handler.send_header("Content-Length", "10"); handler.end_headers()
        handler.wfile.write(b"first"); handler.wfile.flush(); first_sent.set()
        if not done.wait(HANG_SECONDS):
            released.append(True); handler.wfile.write(b"later"); handler.wfile.flush()
    client = bounded.BoundedStreamClient(read_timeout_seconds=READ_HOP_SECONDS, connect_timeout_seconds=HANG_SECONDS)
    received = []
    with endpoint(respond) as url:
        try:
            with pytest.raises(httpx.ReadTimeout):
                with client.stream("POST", url, content=b"synthetic", headers={}) as value:
                    chunks = value.iter_bytes()
                    received.append(next(chunks))
                    # The server thread sets this after its flush; the chunk can reach the
                    # caller first, so wait for it rather than read it at once (#2792).
                    assert first_sent.wait(HANG_SECONDS)
                    began = time.monotonic()
                    try:
                        received.append(next(chunks))
                    finally:
                        waited.append(time.monotonic() - began)   # before the context kills the worker
        finally:
            done.set()
    # Exactly the flushed chunk, yielded before the rest existed: nothing was buffered.
    assert received == [b"first"] and not released
    # The read deadline ended the withheld read when it was due: not late (measured at
    # most 68 ms after READ_HOP_SECONDS over 1,536 reads at load up to 477, #2734) and
    # not early (#2762).
    assert READ_HOP_SECONDS - READ_EARLY_SECONDS <= waited[0] < READ_HOP_SECONDS + REFUSAL_GAP_SECONDS, \
        f"the read deadline fired {waited[0]:.2f} s after the read began; {READ_HOP_SECONDS} s is registered"
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
    if not send_started:
        # Any start-up time leaves the witness absent, so a real 0.2 s bound is exact.
        client = bounded.BoundedStreamClient(read_timeout_seconds=.1, connect_timeout_seconds=.1)
        witnessed = None
    else:
        # The witness is written only once the interpreter runs, which under load
        # took longer than a 0.2 s bound, so the deadline came first and the
        # attempt was classified as never sent (#2604). The parent's clock
        # passes the deadline only once the parent holds the witness; the real
        # bound is a hang guard, and a stop by it would be a ConnectTimeout.
        client = bounded.BoundedStreamClient(read_timeout_seconds=HANG_SECONDS / 2,
                                             connect_timeout_seconds=HANG_SECONDS / 2)
        witnessed = []
        def monotonic():
            with client._lock:
                sent = any(worker.sent for worker in client._workers)
            if sent and not witnessed:
                witnessed.append(True)
            return time.monotonic() + (HANG_SECONDS if sent else 0)
        monkeypatch.setattr(bounded, "time", SimpleNamespace(monotonic=monotonic))
    error = httpx.ReadTimeout if send_started else httpx.ConnectTimeout
    with pytest.raises(error):
        with client.stream("POST", "http://127.0.0.1/unused", content=b"small", headers={}):
            pytest.fail("sleeping worker returned headers")
    assert witnessed is None or witnessed == [True]
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


def test_a_5xx_can_be_classified_without_draining_its_body(processes, monkeypatch):
    # The body is withheld until the context has exited; only a watchdog
    # releases it. The verdict is that ordering, the parent's reads from the
    # worker after the headers, killing before reaping, and the real time from
    # leaving the context to the kill, not a wall-clock total that also
    # counted the worker's interpreter start-up (#2569, #2618).
    exited, body_released = threading.Event(), threading.Event()
    reads_after_headers = []
    real_take = bounded._Worker._take
    def take(worker, size, deadline):
        if worker.headers_received:
            reads_after_headers.append(size)
        return real_take(worker, size, deadline)
    monkeypatch.setattr(bounded._Worker, "_take", take)
    spawn, popen_at = bounded.subprocess.Popen, []
    def timed_spawn(*args, **kwargs):
        popen_at.append(time.monotonic())          # the start-up window opens here
        return spawn(*args, **kwargs)
    monkeypatch.setattr(bounded.subprocess, "Popen", timed_spawn)
    flushed = []
    def respond(handler, body):
        handler.send_response(524); handler.send_header("Content-Length", "500"); handler.end_headers()
        handler.wfile.flush()
        flushed.append(time.monotonic())
        if not exited.wait(timeout=10):
            body_released.set(); handler.wfile.write(b"x" * 500); handler.wfile.flush()
    # The read bound outlasts the watchdog, so a draining exit receives the
    # body rather than timing out. read + connect is the pre-header deadline,
    # which keeps a loaded interpreter start-up out of the verdict.
    client = bounded.BoundedStreamClient(read_timeout_seconds=30, connect_timeout_seconds=10)
    with endpoint(respond) as url:
        try:
            killed_at = []
            called = time.monotonic()
            with client.stream("POST", url, content=b"synthetic", headers={}) as value:
                entered = time.monotonic()
                assert value.status_code == 524
                waits = killed_before_reaped(processes[0][0], killed_at)
                leaving = time.monotonic()
            exited_at = time.monotonic()
            drained = body_released.is_set()
        finally:
            exited.set()
    assert not drained, "the context waited for the withheld body"
    assert reads_after_headers == [], "the context read from the worker after its headers"
    assert waits and all(waits), "the context waited on a live worker before killing it"
    assert len(killed_at) == 1, f"expected one SIGKILL, saw {len(killed_at)}"          # #2644
    assert killed_at[0] - leaving < KILL_GAP_SECONDS, "the kill came long after the close"
    # And from the headers leaving the server to the response reaching the caller (#2676).
    assert entered - flushed[0] < PARENT_GAP_SECONDS, "the response was yielded long after its headers"
    # And the whole call less the worker's start-up window, from just before Popen to
    # the server's header flush: a wait before the spawn or after the kill (#2696).
    assert (exited_at - called) - (flushed[0] - popen_at[0]) < CALL_GAP_SECONDS, \
        "the call spent long outside the worker's start-up"
    assert not client._workers
    client.close()


@pytest.mark.parametrize("frame", [b"\xff\xff\xff\xff", struct.pack("!I", 3) + b"Pxx",
    struct.pack("!I", 3) + b"H{}", struct.pack("!I", 3) + b"E{}"])
def test_bad_worker_frames_fail_closed_and_reap(processes, monkeypatch, frame):
    # The bounds are hang guards, not a 2 s budget that also paid for the worker's
    # start-up, and the worker outlives them, so only rejecting its frame can end the
    # exchange: a frame ignored runs to the deadline instead (#2862).
    source = (f"import sys,time;sys.stdout.buffer.write({frame!r});sys.stdout.buffer.flush();"
              f"time.sleep({3 * HANG_SECONDS})")
    monkeypatch.setattr(bounded, "_worker_command", lambda: [sys.executable, "-B", "-c", source])
    client = bounded.BoundedStreamClient(read_timeout_seconds=HANG_SECONDS, connect_timeout_seconds=HANG_SECONDS)
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
    # The verdict is the one request the server saw; the bounds are hang guards (#2604).
    client = bounded.BoundedStreamClient(read_timeout_seconds=HANG_SECONDS, connect_timeout_seconds=HANG_SECONDS)
    with endpoint(respond) as url:
        with client.stream("POST", url, content=b"once", headers={}) as value:
            assert value.status_code == 307 and b"".join(value.iter_bytes()) == b""
    assert hits == [b"once"]
    client.close()


def _local_worker_failure(tmp_path, monkeypatch, sent, defect, start_delay=0):
    """#2160: IPC faults remain pending even after a sent progress witness. The worker is
    a bare interpreter, so its bounds, the caller's and the proxy's handler cleanup are
    hang guards, not a 3 s, 5 s or 2 s budget that also paid for its start-up or a
    descheduled handler (#2772, #2853). The worker keeps its pipe open after its defect,
    so the defect, not the worker's exit, ends the exchange: a defect the transport
    ignored would run to the caller's timeout instead. Only the eof case exits, since
    its exit is the defect (#2861)."""
    from native_controls.test_native_stall_policy import proxy_with, rows
    from native_controls.test_native_proxy import REQUEST
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
    hold = "" if defect == "eof" else f";time.sleep({3 * HANG_SECONDS})"
    source = (f"import sys,time;time.sleep({start_delay});sys.stdin.buffer.read();"
              f"sys.stdout.buffer.write({frames!r});sys.stdout.buffer.flush(){hold}")
    monkeypatch.setattr(bounded, "_worker_command", lambda: [sys.executable, "-B", "-c", source])
    proxy, ledger, provider_calls = proxy_with(tmp_path, [])
    proxy.upstream.close()
    proxy.upstream = bounded.BoundedStreamClient(read_timeout_seconds=HANG_SECONDS, connect_timeout_seconds=HANG_SECONDS)
    def post(url, proxy):
        return httpx.post(url + '/v1/messages?beta=true', json=REQUEST, headers={'x-api-key': proxy.token},
                          timeout=HANG_SECONDS)
    with proxy.running(cleanup_timeout=HANG_SECONDS) as url:
        assert post(url, proxy).status_code == 402
        assert post(url, proxy).status_code == 402
    row, = rows(ledger)
    assert row["status"] == "pending" and "settlement_basis" not in row and "cost_usd" not in row
    assert proxy.stalls_survived == 0 and proxy.failure == "BoundWorkerProtocolError"
    assert proxy.unfinished_handlers == 0 and not proxy.upstream._workers
    assert provider_calls == [] and not list(tmp_path.rglob("stall.json"))


@pytest.mark.parametrize("sent", [False, True], ids=["before-send", "after-send"])
@pytest.mark.parametrize("defect", ["length", "headers", "eof", "progress", "unknown-error", "local-error", "missing-headers", "false-sent-error"])
def test_local_worker_failure_never_debits_real_proxy_ledger(tmp_path, monkeypatch, processes, sent, defect):
    _local_worker_failure(tmp_path, monkeypatch, sent, defect)


def test_a_slow_worker_start_does_not_turn_a_local_failure_into_a_timeout(tmp_path, monkeypatch, processes):
    """#2772, #2852: a worker that takes 6 s to start, past both the 3 s the test once
    allowed the exchange and the caller's former 5 s, still fails as the worker protocol
    error it is, and debits nothing."""
    _local_worker_failure(tmp_path, monkeypatch, False, "eof", start_delay=6)


def test_genuine_worker_upstream_protocol_error_preserves_debit_and_retry(tmp_path, monkeypatch, processes):
    """The distinct local error does not weaken an actual upstream stall."""
    from native_controls.test_native_stall_policy import proxy_with, rows, STALL_DEBIT_BASIS
    from native_controls.test_native_proxy import events, wire, REQUEST
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
        # Each request starts a worker that imports HTTPX: its bounds and the
        # caller's are hang guards, not a 3 s and a 5 s budget (#2604). A worker
        # that never sent would end the caller's own 120 s timeout first, a
        # ReadTimeout here, never the stall asserted below (#2807).
        proxy.upstream = bounded.BoundedStreamClient(read_timeout_seconds=HANG_SECONDS, connect_timeout_seconds=HANG_SECONDS)
        def post(url, proxy):
            return httpx.post(url + '/v1/messages?beta=true', json=REQUEST, headers={'x-api-key': proxy.token},
                              timeout=HANG_SECONDS)
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
