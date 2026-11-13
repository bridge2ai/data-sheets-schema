"""Separate continuous-clock admission bound; never charged to child runtime.

The periodic POSIX alarm is a wakeup, not the time authority. Its handler
raises through interruptible Python system calls (including PEP 475 retries).
An uninterruptible kernel call or C extension that never services signals
cannot be preempted by this in-process mechanism.
"""
from contextlib import contextmanager
import signal
import threading

from .native_elapsed import elapsed_ns

ADMISSION_SECONDS = 900
POLL_SECONDS = 0.1


class AdmissionRefused(BaseException):
    """Bypass broad verification/diagnostic Exception handlers; unwind cleanup."""


class AdmissionExpired(AdmissionRefused):
    pass


class AdmissionTimer:
    def __init__(self, start_ns, *, seconds=ADMISSION_SECONDS, clock=elapsed_ns):
        self.start_ns = start_ns
        self.deadline_ns = start_ns + int(seconds * 1_000_000_000)
        self.clock = clock

    def check(self, now_ns=None):
        if (self.clock() if now_ns is None else now_ns) >= self.deadline_ns:
            raise AdmissionExpired('native admission deadline elapsed; child was not dispatched')

    def _alarm(self, signum, frame):
        self.check()

    @contextmanager
    def armed(self):
        """Own SIGALRM only within admission, restoring disposition and mask."""
        names = ('SIGALRM', 'ITIMER_REAL', 'pthread_sigmask', 'sigwait', 'sigpending')
        if threading.current_thread() is not threading.main_thread() or any(
                not hasattr(signal, name) for name in names):
            raise AdmissionRefused('native admission timer needs POSIX main-thread signals')
        blocked = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        previous = signal.getsignal(signal.SIGALRM)
        owned = False
        try:
            if (signal.SIGALRM in blocked or previous != signal.SIG_DFL
                    or signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0)
                    or signal.SIGALRM in signal.sigpending()):
                raise AdmissionRefused('native admission timer signal is already owned or blocked')
            self.check()
            signal.signal(signal.SIGALRM, self._alarm)
            owned = True
            signal.siginterrupt(signal.SIGALRM, True)
            remaining = (self.deadline_ns - self.clock()) / 1_000_000_000
            self.check()
            signal.setitimer(signal.ITIMER_REAL, max(0.000001, min(remaining, POLL_SECONDS)), POLL_SECONDS)
            signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
            yield self
        finally:
            signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
            if owned:
                signal.setitimer(signal.ITIMER_REAL, 0)
                if signal.SIGALRM in signal.sigpending():
                    signal.sigwait({signal.SIGALRM})
                signal.signal(signal.SIGALRM, previous)
            signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
