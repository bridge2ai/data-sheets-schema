"""Absolute buffered-response deadline with synthetic workers/sockets (#2304)."""
import threading
import time

import httpx
import pytest

from audit_controls import bounded_stream as bounded
from audit_controls.test_bounded_stream import (endpoint, processes, killed_before_reaped, HANG_SECONDS,
                                                REAP_SECONDS, REFUSAL_GAP_SECONDS, UNWIND_GAP_SECONDS)


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
    # late (REFUSAL_GAP_SECONDS, which a bound 1.5 s late or more fails at every
    # rung, #2735), that the body was cut short, and that the exchange then ended:
    # the worker killed before any wait on it and within UNWIND_GAP_SECONDS of the
    # refusal, so it cannot go on reading the response, and the caller released
    # within UNWIND_GAP_SECONDS of the reap (#2760).
    refused_at, killed_at, reaped_at, waits = [], [], [], []
    real_timeout = bounded._Worker.timeout
    def timeout(worker):
        refused_at.append(time.monotonic())
        return real_timeout(worker)
    monkeypatch.setattr(bounded._Worker, "timeout", timeout)
    spawn = bounded.subprocess.Popen
    def watched(*args, **kwargs):
        process = spawn(*args, **kwargs)
        waits.append(killed_before_reaped(process, killed_at, reaped_at))
        return process
    monkeypatch.setattr(bounded.subprocess, "Popen", watched)
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
        received, refused_at[:], killed_at[:], reaped_at[:], waits[:] = [], [], [], [], []
        with endpoint(respond) as url:
            try:
                started = time.monotonic()
                with pytest.raises(httpx.TimeoutException) as caught:
                    with client.stream('POST', url, content=b'synthetic', headers={}) as response:
                        for chunk in response.iter_bytes():
                            received.append(chunk)
                released = time.monotonic()
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
        (worker_waits,) = waits
        assert worker_waits and all(worker_waits), ("the worker was waited on before it was killed", attempts)
        assert len(killed_at) == 1 and killed_at[0] - refused_at[0] < UNWIND_GAP_SECONDS, \
            ("the worker was killed long after the refusal", killed_at, refused_at, attempts)
        assert reaped_at and reaped_at[0] - killed_at[0] < REAP_SECONDS, attempts
        # Reaped before the caller hears of it: kill and reap precede any debit, evidence or
        # retry the refusal leads to (bounded_stream.stream's finally, #2777).
        assert reaped_at[0] <= released, ("the caller was released before its worker was reaped", attempts)
        assert released - reaped_at[0] < UNWIND_GAP_SECONDS, ("the caller was released long after the reap", attempts)
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
