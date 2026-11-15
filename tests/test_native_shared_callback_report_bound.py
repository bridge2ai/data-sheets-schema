"""Issue 6214: report refuses a stuck worker without unwinding its scope."""
from contextlib import contextmanager
import gc
import threading
from types import SimpleNamespace
import weakref

import pytest

from data_sheets_schema import native_shared_callback_orchestration as preload
from data_sheets_schema.native_shared_controller_orchestration import CallbackAdapter


def exercise_report_timeout(monkeypatch, exceptional, complete):
    monkeypatch.setattr(preload, 'CALLBACK_TEARDOWN_SECONDS', 0.02)
    lock = preload._CallbackLock()
    entered, release = threading.Event(), threading.Event()
    closed, errors = [], []
    original = RuntimeError('original runtime failure')

    class Loader:
        pass

    def loader():
        resource = Loader()
        try:
            yield resource
        finally:
            closed.append(True)

    def scope_body():
        with preload._locked_stack(lock) as stack:
            resource = stack.enter_context(contextmanager(loader)())
            yield weakref.ref(resource)

    scope = contextmanager(scope_body)()
    reference = scope.__enter__()
    adapter = object.__new__(CallbackAdapter)
    adapter._classifier = SimpleNamespace(_lock=lock)
    adapter._classifier_scope = scope
    adapter.failure = 'earlier failure' if exceptional else None
    adapter._report = lambda **kwargs: pytest.fail('report accessed running worker state')

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
    worker.start()
    try:
        assert entered.wait(30)
        with pytest.raises(RuntimeError if exceptional else ValueError) as caught:
            if exceptional:
                try:
                    raise original
                except RuntimeError:
                    adapter.report(complete=complete)
            else:
                adapter.report(complete=complete)
        refusal = caught.value.__cause__ if exceptional else caught.value
        assert '0.02 seconds' in str(refusal)
        if exceptional:
            assert caught.value is original
            assert adapter.failure == 'earlier failure'
        else:
            assert adapter.failure == str(refusal)
        assert lock.poisoned
        assert scope in preload._POISONED_STACKS
        assert not closed
        with pytest.raises(ValueError, match='poisoned'):
            adapter.report(complete=complete)
        with pytest.raises(ValueError, match='poisoned'):
            with lock:
                pytest.fail('callback reentry accepted')
        del adapter, scope
        gc.collect()
        assert reference() is not None
    finally:
        release.set()
        worker.join(30)
    assert not worker.is_alive()
    assert not errors
    gc.collect()
    assert reference() is not None
    assert not closed


def test_report_timeout(monkeypatch):
    exercise_report_timeout(monkeypatch, False, True)


def test_report_timeout_preserves_original(monkeypatch):
    exercise_report_timeout(monkeypatch, True, True)


def test_partial_report_timeout(monkeypatch):
    exercise_report_timeout(monkeypatch, False, False)


def test_acquired_report_closes_only_when_complete():
    lock = preload._CallbackLock()
    closed = []
    scope = preload._locked_stack(lock)
    scope.__enter__().callback(closed.append, True)
    adapter = object.__new__(CallbackAdapter)
    adapter._classifier = SimpleNamespace(_lock=lock)
    adapter._classifier_scope = scope
    adapter._report = lambda **kwargs: kwargs
    assert adapter.report(complete=False) == {'complete': False}
    assert not closed
    assert adapter.report(complete=True) == {'complete': True}
    assert closed == [True]
    assert not hasattr(adapter, '_classifier_scope')


def test_acquired_report_preserves_error_and_closes():
    lock = preload._CallbackLock()
    closed = []
    scope = preload._locked_stack(lock)
    scope.__enter__().callback(closed.append, True)
    adapter = object.__new__(CallbackAdapter)
    adapter._classifier = SimpleNamespace(_lock=lock)
    adapter._classifier_scope = scope
    original = RuntimeError('report failed')
    def fail(**kwargs):
        raise original
    adapter._report = fail
    with pytest.raises(RuntimeError) as caught:
        adapter.report(complete=True)
    assert caught.value is original
    assert closed == [True]
