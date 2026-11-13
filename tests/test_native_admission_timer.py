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
    assert signal.SIGALRM not in signal.pthread_sigmask(signal.SIG_BLOCK, ())


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


def test_expiry_does_not_interrupt_slow_nested_cleanup(tmp_path):
    fifo = tmp_path / 'no-writer'
    os.mkfifo(fifo)
    completed = []
    timer = AdmissionTimer(elapsed_ns(), seconds=.1)
    with pytest.raises(AdmissionExpired, match='child was not dispatched'):
        with timer.armed():
            try:
                os.open(fifo, os.O_RDONLY)
            finally:
                # More than several original polling intervals; repeated
                # exceptions here would skip the cleanup completion marker.
                time.sleep(.35)
                timer._alarm(signal.SIGALRM, None)  # Already-posted Python tick.
                completed.append(True)
    assert completed == [True]
    assert signal.SIGALRM not in signal.pthread_sigmask(signal.SIG_BLOCK, ())


def test_late_post_cancel_alarm_is_consumed_before_restoration(monkeypatch):
    from data_sheets_schema import native_admission_timer as module
    original_sleep = time.sleep
    seen = []
    timer = AdmissionTimer(elapsed_ns())
    def late_tick(seconds):
        assert timer._closing
        assert signal.SIGALRM in signal.pthread_sigmask(signal.SIG_BLOCK, ())
        assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
        os.kill(os.getpid(), signal.SIGALRM)
        assert signal.SIGALRM in signal.sigpending()
        timer._alarm(signal.SIGALRM, None)
        seen.append(seconds)
        original_sleep(seconds)
    monkeypatch.setattr(module.time, 'sleep', late_tick)
    with timer.armed():
        pass
    assert seen
    assert signal.getsignal(signal.SIGALRM) == signal.SIG_DFL
    assert not signal.sigpending() & {signal.SIGALRM}
    assert signal.SIGALRM not in signal.pthread_sigmask(signal.SIG_BLOCK, ())


@pytest.mark.parametrize('step', ['block', 'cancel', 'wait-clock', 'wait', 'pending', 'handler', 'mask'])
def test_teardown_step_exception_does_not_skip_remaining_restoration(monkeypatch, step):
    from data_sheets_schema import native_admission_timer as module
    timer = AdmissionTimer(elapsed_ns())
    raised = []
    originals = {name: getattr(signal, name) for name in ('pthread_sigmask', 'setitimer', 'sigpending', 'signal')}
    original_sleep = time.sleep
    original_monotonic = time.monotonic
    def interrupt(name, action, *args):
        result = action(*args)
        if timer._closing and name == step and not raised:
            raised.append(name)
            raise KeyboardInterrupt('injected teardown interruption')
        return result
    with pytest.raises(KeyboardInterrupt, match='injected teardown'):
        with timer.armed():
            monkeypatch.setattr(signal, 'pthread_sigmask', lambda how, mask: interrupt(
                'block' if how == signal.SIG_BLOCK else 'mask', originals['pthread_sigmask'], how, mask))
            monkeypatch.setattr(signal, 'setitimer', lambda *args: interrupt('cancel', originals['setitimer'], *args))
            monkeypatch.setattr(signal, 'sigpending', lambda: interrupt('pending', originals['sigpending']))
            monkeypatch.setattr(signal, 'signal', lambda *args: interrupt('handler', originals['signal'], *args))
            monkeypatch.setattr(module.time, 'sleep', lambda seconds: interrupt('wait', original_sleep, seconds))
            monkeypatch.setattr(module.time, 'monotonic', lambda: interrupt('wait-clock', original_monotonic))
    assert raised == [step]
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    assert signal.getsignal(signal.SIGALRM) == signal.SIG_DFL
    assert signal.SIGALRM not in originals['pthread_sigmask'](signal.SIG_BLOCK, ())


@pytest.mark.parametrize('ownership', ['blocked', 'pending', 'timer'])
def test_existing_signal_state_is_refused_and_preserved(ownership):
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
    try:
        if ownership == 'pending':
            os.kill(os.getpid(), signal.SIGALRM)
        elif ownership == 'timer':
            signal.setitimer(signal.ITIMER_REAL, 30)
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        with pytest.raises(AdmissionRefused, match='already owned'):
            with AdmissionTimer(elapsed_ns()).armed():
                pytest.fail('accepted preexisting signal state')
        assert signal.getsignal(signal.SIGALRM) == signal.SIG_DFL
        current = signal.pthread_sigmask(signal.SIG_BLOCK, ())
        assert (signal.SIGALRM in current) == (ownership != 'timer')
        if ownership == 'pending':
            assert signal.SIGALRM in signal.sigpending()
        if ownership == 'timer':
            assert signal.getitimer(signal.ITIMER_REAL)[0] > 0
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if signal.SIGALRM in signal.sigpending():
            signal.sigwait({signal.SIGALRM})
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)
