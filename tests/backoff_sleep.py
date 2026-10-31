"""Record retry backoff without disabling the shared time module's polling."""
from time import sleep as _real_sleep


class BackoffSleeps(list):
    """Callable recorder for API backoff (>= 1s), preserving short real sleeps.

    Patching api_runner.time.sleep also patches subprocess.time.sleep: both
    reference the stdlib time module. Popen.wait(timeout=...) polls with sleeps
    capped at 0.05s. Those waits must yield to the child and must not count as
    runner retries. Capture the original sleep before installing any patch.
    """

    def __call__(self, seconds):
        if seconds <= 0.05:
            _real_sleep(seconds)
        else:
            self.append(seconds)
