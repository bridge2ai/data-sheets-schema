"""Separate continuous-clock admission bound; never charged to child runtime.

The periodic POSIX alarm is a wakeup, not the time authority. Its handler
raises through interruptible Python system calls (including PEP 475 retries).
An uninterruptible kernel call or C extension that never services signals
cannot be preempted by this in-process mechanism.
"""
from contextlib import contextmanager
import signal
import threading
import time

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
        self._closing = True
        self._fired = False

    def check(self, now_ns=None):
        if (self.clock() if now_ns is None else now_ns) >= self.deadline_ns:
            raise AdmissionExpired('native admission deadline elapsed; child was not dispatched')

    def _alarm(self, signum, frame):
        if self._closing or self._fired:
            return
        try:
            self.check()
        except AdmissionExpired as expired:
            # One exception initiates unwinding. A queued tick must never raise
            # into nested verification cleanup before armed() regains control.
            self._fired = True
            try:
                signal.setitimer(signal.ITIMER_REAL, 0)
            except BaseException:
                # _restore retries cancellation; the fired latch already makes
                # every queued alarm inert. Preserve the original expiry.
                pass
            raise expired

    def _restore(self, blocked, previous, owned):
        """Defer a raising cleanup step until every restoration was attempted.

        A Python signal can raise immediately after a signal syscall changed
        state. Retry idempotent operations once, retaining the first exception.
        Never restore a default disposition if timer cancellation failed.
        """
        errors = []
        def attempt(action):
            for _ in range(2):
                try:
                    action()
                    return True
                except BaseException as exc:
                    errors.append(exc)
            return False
        attempt(lambda: signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM}))
        if owned:
            cancelled = attempt(lambda: signal.setitimer(signal.ITIMER_REAL, 0))
            # XNU may post one already-dequeued callout after cancellation.
            # Keep the alarm blocked and our handler inert through another tick.
            until = time.monotonic() + POLL_SECONDS
            while True:
                try:
                    remaining = until - time.monotonic()
                    if remaining <= 0:
                        break
                    time.sleep(remaining)
                except BaseException as exc:
                    errors.append(exc)
            def drain():
                if signal.SIGALRM in signal.sigpending():
                    signal.sigwait({signal.SIGALRM})
            drained = attempt(drain)
            if cancelled and drained:
                attempt(lambda: signal.signal(signal.SIGALRM, previous))
        attempt(lambda: signal.pthread_sigmask(signal.SIG_SETMASK, blocked))
        if errors:
            raise errors[0]

    @contextmanager
    def armed(self):
        """Own SIGALRM only within admission, restoring disposition and mask."""
        names = ('SIGALRM', 'ITIMER_REAL', 'pthread_sigmask', 'sigwait', 'sigpending')
        if threading.current_thread() is not threading.main_thread() or any(
                not hasattr(signal, name) for name in names):
            raise AdmissionRefused('native admission timer needs POSIX main-thread signals')
        blocked = signal.pthread_sigmask(signal.SIG_BLOCK, ())
        previous = signal.getsignal(signal.SIGALRM)
        owned = False
        self._fired = False
        try:
            signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
            if (signal.SIGALRM in blocked or previous != signal.SIG_DFL
                    or signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0)
                    or signal.SIGALRM in signal.sigpending()):
                raise AdmissionRefused('native admission timer signal is already owned or blocked')
            self.check()
            owned = True
            signal.signal(signal.SIGALRM, self._alarm)
            self._closing = False
            signal.siginterrupt(signal.SIGALRM, True)
            remaining = (self.deadline_ns - self.clock()) / 1_000_000_000
            self.check()
            signal.setitimer(signal.ITIMER_REAL, max(0.000001, min(remaining, POLL_SECONDS)), POLL_SECONDS)
            signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
            yield self
        finally:
            self._closing = True
            self._restore(blocked, previous, owned)
