"""Issue 6214: bounded teardown preserves live loaders and refuses reuse."""
from contextlib import contextmanager
import gc
import sys
import threading
import weakref

import pytest

from data_sheets_schema import native_shared_callback_orchestration as preload


def exercise_timeout(monkeypatch, exceptional):
    monkeypatch.setattr(preload, 'CALLBACK_TEARDOWN_SECONDS', 0.02)
    lock = preload._CallbackLock()
    entered, release = threading.Event(), threading.Event()
    closed = []
    errors = []
    original = RuntimeError('original failure')

    class Loader:
        pass

    def loader():
        resource = Loader()
        yield resource
        closed.append(True)

    def work():
        try:
            with lock:
                entered.set()
                assert release.wait(60)
                assert reference() is not None
                assert not closed
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=work)
    try:
        with pytest.raises(RuntimeError if exceptional else ValueError) as caught:
            with preload._locked_stack(lock) as stack:
                resource = stack.enter_context(contextmanager(loader)())
                reference = weakref.ref(resource)
                del resource
                worker.start()
                assert entered.wait(30)
                if exceptional:
                    raise original
        refusal = caught.value.__cause__ if exceptional else caught.value
        if exceptional:
            assert caught.value is original
        assert '0.02 seconds' in str(refusal)
        assert stack in preload._POISONED_STACKS
        assert stack in sys.__dict__['_d4d_poisoned_callback_stacks']
        gc.collect()
        assert reference() is not None
        assert not closed
        with pytest.raises(ValueError, match='poisoned'):
            with lock:
                pytest.fail('poisoned entry accepted')
        guard = object.__new__(preload._ValidatorGuard)
        guard.scope = lock
        with pytest.raises(ValueError, match='poisoned'):
            guard.reusable()
        with pytest.raises(ValueError, match='poisoned'):
            with preload._locked_stack(lock):
                pytest.fail('poisoned scope body entered')
    finally:
        release.set()
        worker.join(30)
    assert not worker.is_alive()
    assert not errors
    gc.collect()
    assert not closed
    assert reference() is not None
    with pytest.raises(ValueError, match='poisoned'):
        with lock:
            pass


def test_normal_timeout(monkeypatch):
    exercise_timeout(monkeypatch, False)


def test_exception_timeout(monkeypatch):
    exercise_timeout(monkeypatch, True)


def test_acquired_stack_closes_and_preserves_exception():
    closed = []
    with preload._locked_stack(preload._CallbackLock()) as stack:
        stack.callback(closed.append, 'normal')
    original = RuntimeError('original')
    with pytest.raises(RuntimeError) as caught:
        with preload._locked_stack(preload._CallbackLock()) as stack:
            stack.callback(closed.append, 'exception')
            raise original
    assert caught.value is original
    assert closed == ['normal', 'exception']


def test_acquired_stack_can_suppress_exception():
    def suppress(*exc):
        return True
    with preload._locked_stack(preload._CallbackLock()) as stack:
        stack.push(suppress)
        raise RuntimeError('suppressed')


def test_poisoned_classifier_refuses_both_entries_before_calling_code():
    lock = preload._CallbackLock()
    lock.poisoned = True
    def forbidden(*args, **kwargs):
        pytest.fail('poisoned classifier called retained code')
    classifier = preload.Classifier(forbidden, forbidden, object(), forbidden, forbidden, lock)
    with pytest.raises(ValueError, match='poisoned'):
        classifier.classify('pwd', 'python', set(), {})
    with pytest.raises(ValueError, match='poisoned'):
        classifier.readonly('pwd', {})
