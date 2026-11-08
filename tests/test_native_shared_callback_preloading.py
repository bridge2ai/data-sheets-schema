"""R7 historical worker scheduling, with no native process or admitted run.

The observer/classifier worker is real; minimal adapter state isolates C's
classifier body. This deliberately does not claim full observer admission.
"""
from dataclasses import FrozenInstanceError
import queue
import sys
import threading

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_callback_orchestration as preload
from data_sheets_schema import native_shared_capture_orchestration as capture
from data_sheets_schema import native_shared_controls_orchestration as controls
from data_sheets_schema.native_shared_controller_orchestration import CallbackAdapter
from tests.test_native_execution_authority_v2 import isolated_modules


def work(historical, kind, callback):
    worker = object.__new__(historical.NativeControl)
    worker._stopped = threading.Event()
    worker._publication_lock = threading.Lock()
    worker._active_work = None
    worker._work_replies = queue.Queue(maxsize=1)
    worker._start_work(kind, None, callback)
    worker._work_thread.join(timeout=10)
    assert not worker._work_thread.is_alive()
    _, result = worker._work_replies.get_nowait()
    return result


@pytest.mark.parametrize('kind', ['observer', 'classifier'])
def test_historical_worker_runs_preloaded_c_classifier(kind, isolated_modules):
    dependencies = authority.dependency_identity()
    with preload.preloaded_classifier(dependencies) as selected:
        historical = sys.modules['native_control']
        adapter = object.__new__(CallbackAdapter)
        adapter.failure = None
        adapter.policy = {'python': sys.executable}
        adapter._classifier = selected
        expected = adapter.classify('pwd', sys.executable, set(), adapter.policy)
        actual = work(historical, kind,
            lambda: adapter.classify('pwd', sys.executable, set(), adapter.policy))
        assert not isinstance(actual, BaseException), repr(actual)
        assert actual == expected


@pytest.mark.parametrize('kind', ['observer', 'classifier'])
@pytest.mark.parametrize('operation', ['controls', 'captures', 'preload'])
def test_worker_load_refused_before_dependency_or_capture_effects(kind, operation, monkeypatch, isolated_modules):
    dependencies = authority.dependency_identity()
    with authority.loaded_dependencies(dependencies):
        historical = sys.modules['native_control']
        def forbidden(*args, **kwargs):
            pytest.fail('worker refusal occurred after an effect')
        with monkeypatch.context() as patch:
            patch.setattr(authority, 'dependency_identity', forbidden)
            patch.setattr(capture, '_Reader', forbidden)
            if operation == 'controls':
                def invoke():
                    with controls.loaded_controls():
                        forbidden()
            elif operation == 'captures':
                invoke = lambda: capture._base('/never/read')
            else:
                def invoke():
                    with preload.preloaded_classifier(dependencies):
                        forbidden()
            result = work(historical, kind, invoke)
        assert type(result) is ValueError
        noun = 'controls' if operation == 'controls' else 'captures'
        assert str(result) == f'native callback cannot load {noun}; preload on the main thread at admission'


def test_preloaded_identity_cannot_be_rebound_and_expires(isolated_modules):
    with preload.preloaded_classifier(authority.dependency_identity()) as selected:
        adapter = object.__new__(CallbackAdapter)
        adapter._classifier = selected
        with pytest.raises(AttributeError, match='cannot be replaced'):
            adapter._classifier = object()
        with pytest.raises(AttributeError, match='cannot be removed'):
            del adapter._classifier
        with pytest.raises(FrozenInstanceError):
            selected._controls = {}
        with pytest.raises(FrozenInstanceError):
            selected._classify.function = lambda *args: ('prescribed', 'forged')
        module = selected._classify.module
        original = module.classify_bash
        try:
            module.classify_bash = lambda *args, **kwargs: ('prescribed', 'forged')
            with pytest.raises(ValueError, match='callable code changed'):
                selected.classify('pwd', sys.executable, set(), {'python': sys.executable})
        finally:
            module.classify_bash = original
    with pytest.raises(ValueError, match='active loader'):
        selected.classify('pwd', sys.executable, set(), {'python': sys.executable})
