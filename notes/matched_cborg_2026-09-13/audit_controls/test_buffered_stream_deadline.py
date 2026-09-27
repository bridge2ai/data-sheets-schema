"""Absolute buffered-response deadline with synthetic workers/sockets (#2304)."""
import threading
import time

import httpx
import pytest

from audit_controls import bounded_stream as bounded
from audit_controls.test_bounded_stream import endpoint, processes, HANG_SECONDS


#: From the absolute bound (the test's start plus the bound) to the parent's own
#: refusal: the entry into stream() and the wake-up of the parent's timed wait, both
#: in-process (#2604). Measured median 12 ms, p99 35 ms, max 156 ms over 2,702
#: refusals under 128-192 concurrent copies at load 169-307, none early. The same
#: kind of wake-up in the count test reached 1.17 s at load ~450 (#2697), and this
#: keeps threefold on that. It rejects a refusal 3.5 s late or more. origin/main's
#: `elapsed < 3.5` at a 2 s bound also rejected one about 1.5-3.5 s late at normal
#: load; this gives that up (at a 2 s bound a refusal 2 s late still fails, because
#: the 4 s body then completes).
REFUSAL_GAP_SECONDS = 3.5


def test_progress_after_headers_does_not_extend_absolute_exchange_bound(processes, monkeypatch):
    # Body chunks arrive far inside the read-inactivity bound (a hang guard here)
    # for twice the absolute bound, so only the absolute bound can end the
    # exchange. That bound also pays for starting the worker, by design: it runs
    # from the call to stream(). Under load start-up alone outlasted a 2 s bound,
    # so no body reached the parent before it expired (#2604). Such an attempt
    # proves the bound but not that progress after the headers cannot extend it,
    # so it is repeated with the bound doubled. What decides the repeat is the
    # parent's own receipt of body bytes, which it yields only before the bound,
    # not a guess about start-up. No assertion is retried: every attempt checks
    # the timeout type, that the refusal was the parent's own, not early and not
    # late, that the body was cut short, and that its worker was reaped.
    refused_at = []
    real_timeout = bounded._Worker.timeout
    def timeout(worker):
        refused_at.append(time.monotonic())
        return real_timeout(worker)
    monkeypatch.setattr(bounded._Worker, "timeout", timeout)
    chunks, size, attempts = 50, 100, []
    for bound in (2, 4, 8, 16, 32):
        gap, stop = 2 * bound / chunks, threading.Event()
        def respond(handler, body):
            handler.send_response(200)
            handler.send_header('Content-Length', str(chunks * size))
            handler.end_headers()
            for _ in range(chunks):
                handler.wfile.write(b'x' * size); handler.wfile.flush()
                if stop.wait(gap):
                    return
        client = bounded.BoundedStreamClient(read_timeout_seconds=HANG_SECONDS, connect_timeout_seconds=HANG_SECONDS,
                                             total_timeout_seconds=bound)
        received, refused_at[:] = [], []
        with endpoint(respond) as url:
            try:
                started = time.monotonic()
                with pytest.raises(httpx.TimeoutException) as caught:
                    with client.stream('POST', url, content=b'synthetic', headers={}) as response:
                        for chunk in response.iter_bytes():
                            received.append(chunk)
            finally:
                stop.set()
        body = sum(map(len, received))
        attempts.append({'bound': bound, 'body_bytes': body, 'error': type(caught.value).__name__,
                         'refused_after': round(refused_at[0] - started, 2) if refused_at else None})
        assert len(refused_at) == 1, attempts                       # the parent's own refusal, once
        assert refused_at[0] >= started + bound - .01, attempts      # not before the bound
        assert refused_at[0] - (started + bound) < REFUSAL_GAP_SECONDS, attempts
        assert body < chunks * size, attempts
        if body:
            assert type(caught.value) is httpx.ReadTimeout, attempts
        assert not client._workers and all(p.poll() is not None for p, _, _ in processes), attempts
        client.close()
        if body >= 2 * size:   # at least two of the server's writes reached the caller
            break
    assert body >= 2 * size, attempts


def test_queued_worker_frames_cannot_bypass_expired_absolute_deadline(monkeypatch):
    class Worker:
        def timeout(self):return httpx.ReadTimeout('synthetic expiry')
        def receive(self, deadline):pytest.fail('expired response read a queued frame')
    monkeypatch.setattr(bounded.time, 'monotonic', lambda: 20)
    response = bounded._Response(Worker(), 200, [], 10, total_deadline=19)
    with pytest.raises(httpx.ReadTimeout):next(response.iter_bytes())


def test_receive_returning_after_deadline_cannot_publish_last_frame(monkeypatch):
    clock = [10]
    class Worker:
        def timeout(self):return httpx.ReadTimeout('synthetic expiry')
        def receive(self, deadline):clock[0] = 20; return b'Z', b''
    monkeypatch.setattr(bounded.time, 'monotonic', lambda: clock[0])
    response = bounded._Response(Worker(), 200, [], 10, total_deadline=19)
    with pytest.raises(httpx.ReadTimeout):next(response.iter_bytes())


@pytest.mark.parametrize('bad', [0, -1, True, float('nan'), float('inf'), '1200'])
def test_invalid_absolute_bound_refused_before_worker(bad, monkeypatch):
    monkeypatch.setattr(bounded, '_Worker', lambda *a: pytest.fail('worker constructed'))
    with pytest.raises(ValueError):bounded.BoundedStreamClient(total_timeout_seconds=bad)
