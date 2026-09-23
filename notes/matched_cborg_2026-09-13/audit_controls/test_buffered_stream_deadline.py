"""Absolute buffered-response deadline with synthetic workers/sockets (#2304)."""
import time

import httpx
import pytest

from audit_controls import bounded_stream as bounded
from audit_controls.test_bounded_stream import endpoint, processes


def test_progress_after_headers_does_not_extend_absolute_exchange_bound(processes):
    def respond(handler, body):
        handler.send_response(200)
        handler.send_header('Content-Length', '6000')
        handler.end_headers()
        for _ in range(60):
            handler.wfile.write(b'x' * 100); handler.wfile.flush()
            time.sleep(.08)
    client = bounded.BoundedStreamClient(read_timeout_seconds=1, connect_timeout_seconds=1,
                                         total_timeout_seconds=2)
    received = []
    with endpoint(respond) as url:
        started = time.monotonic()
        with pytest.raises(httpx.ReadTimeout):
            with client.stream('POST', url, content=b'synthetic', headers={}) as response:
                for chunk in response.iter_bytes():
                    received.append(chunk)
        elapsed = time.monotonic() - started
    assert received and sum(map(len, received)) < 6000 and 1.5 <= elapsed < 3.5
    assert not client._workers
    client.close()


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
