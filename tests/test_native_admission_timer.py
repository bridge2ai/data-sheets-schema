"""Admission owns a separate clock and interrupts a blocked system call."""
import os
import signal
import threading
import time

import pytest

from data_sheets_schema.native_admission_timer import AdmissionTimer, AdmissionExpired, AdmissionRefused
from data_sheets_schema.native_elapsed import elapsed_ns


@pytest.mark.parametrize('suspend', [False, True])
def test_stalled_fifo_open_is_interrupted_and_alarm_is_restored(tmp_path, suspend):
    fifo = tmp_path / 'no-writer'
    os.mkfifo(fifo)
    ticks = [0]
    clock = (lambda: ticks[0]) if suspend else elapsed_ns
    timer = AdmissionTimer(clock(), seconds=900 if suspend else .2, clock=clock)
    previous = signal.getsignal(signal.SIGALRM)
    start = time.monotonic()
    cleaned = []
    with pytest.raises(AdmissionExpired, match='child was not dispatched'):
        with timer.armed():
            if suspend:
                ticks[0] = 901 * 10**9
            try:
                # No writer exists. A post-return deadline check cannot end it.
                fd = os.open(fifo, os.O_RDONLY)
                os.close(fd)
                pytest.fail('FIFO returned without the admission interruption')
            finally:
                cleaned.append(True)
    assert cleaned == [True]
    assert time.monotonic() - start < 5
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    assert signal.getsignal(signal.SIGALRM) == previous
    assert signal.SIGALRM not in signal.sigpending()


def test_exact_boundary_is_expired_without_waiting_for_alarm_delivery():
    timer = AdmissionTimer(100, seconds=900)
    timer.check(900 * 10**9 + 99)
    with pytest.raises(AdmissionExpired):
        timer.check(900 * 10**9 + 100)


def test_existing_signal_handler_is_not_stolen():
    previous = signal.getsignal(signal.SIGALRM)
    handler = lambda signum, frame: None
    signal.signal(signal.SIGALRM, handler)
    try:
        with pytest.raises(AdmissionRefused, match='already owned'):
            with AdmissionTimer(elapsed_ns()).armed():
                pytest.fail('accepted another signal owner')
        assert signal.getsignal(signal.SIGALRM) is handler
    finally:
        signal.signal(signal.SIGALRM, previous)


def test_worker_thread_refuses_before_running_verification():
    errors = []
    def worker():
        try:
            with AdmissionTimer(elapsed_ns()).armed():
                errors.append('entered')
        except AdmissionRefused as exc:
            errors.append(str(exc))
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert errors == ['native admission timer needs POSIX main-thread signals']
