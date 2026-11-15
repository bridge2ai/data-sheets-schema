"""Issue 6214, 2026-11-15: apply bounded teardown; input/output local source."""
from pathlib import Path
p = Path('src/data_sheets_schema/native_shared_callback_orchestration.py')
s = p.read_text()
a = s.index('def _locked_stack(lock):')
b = s.index('\n\n' + chr(64) + 'dataclass', a)
s = s[:a] + '''def _locked_stack(lock):
    """Retain poisoned loaders until process exit; never revoke under a worker."""
    stack = ExitStack()
    try:
        yield stack
    except BaseException as original:
        require_main_thread()
        if not lock.acquire(timeout=CALLBACK_TEARDOWN_SECONDS):
            refusal = _poison_stack(lock, stack)
            raise original from refusal
        try:
            if not stack.__exit__(*sys.exc_info()):
                raise
        finally:
            lock.release()
    else:
        require_main_thread()
        if not lock.acquire(timeout=CALLBACK_TEARDOWN_SECONDS):
            raise _poison_stack(lock, stack)
        try:
            stack.close()
        finally:
            lock.release()
''' + s[b:]
pos = s.index('\n\n' + chr(64) + 'contextmanager\ndef _locked_stack')
s = s[:pos] + '''

# Match the classifier's existing 2-second window. Teardown is a separate
# grace period, not an extension of the 120-second observer acceptance window.
CALLBACK_TEARDOWN_SECONDS = 2.0
_POISONED_STACKS = []


class _CallbackLock:
    """Shared admission gate; poison is checked before and after waiting."""
    def __init__(self):
        self.lock = RLock()
        self.poisoned = False

    def check(self):
        if self.poisoned:
            raise ValueError('native callback scope is poisoned; reuse refused')

    def acquire(self, *, timeout):
        self.check()
        return self.lock.acquire(timeout=timeout)

    def release(self):
        self.lock.release()

    def __enter__(self):
        self.check()
        self.lock.acquire()
        try:
            self.check()
        except BaseException:
            self.lock.release()
            raise
        return self

    def __exit__(self, *exc):
        self.lock.release()


def _poison_stack(lock, stack):
    lock.poisoned = True
    _POISONED_STACKS.append(stack)
    return ValueError('native callback teardown exceeded '
                      + str(CALLBACK_TEARDOWN_SECONDS)
                      + ' seconds; scope poisoned and loaders retained')
''' + s[pos:]
s = s.replace('lock = RLock() if _lock is None else _lock', 'lock = _CallbackLock() if _lock is None else _lock')
s = s.replace('    lock = RLock()\n    with _locked_stack', '    lock = _CallbackLock()\n    with _locked_stack')
s = s.replace('        self.disabled = False', '        self.disabled = False\n        self.scope = None')
s = s.replace('    def reusable(self):\n', '    def reusable(self):\n        if self.scope is not None:\n            self.scope.check()\n')
s = s.replace('        prefix = capture_inputs._PrefixOwner(guard, admitted)', '        guard.scope = lock\n        prefix = capture_inputs._PrefixOwner(guard, admitted)')
p.write_text(s)
p = Path('tests/test_native_shared_callback_preloading.py')
s = p.read_text().replace('        def __enter__(self):\n            if threading.current_thread() is threading.main_thread():\n                closing.set()\n            lock.acquire()', '        def acquire(self, *, timeout):\n            closing.set()\n            return lock.acquire(timeout=timeout)\n        def release(self):\n            lock.release()')
p.write_text(s)
