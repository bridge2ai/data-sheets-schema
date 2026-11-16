"""Regression for the lazily imported D156 fixture clock, PR 5968."""
from contextlib import contextmanager
from datetime import datetime
import sys
import data_sheets_schema

from data_sheets_schema import native_shared_callback_orchestration as callbacks
from data_sheets_schema import native_subscription_guard_v2 as ambient
from tests.utils.native_prepared_test_scope import freeze_subscription_clock


def test_clock_reaches_lazy_module_and_restores_external_datetime(monkeypatch):
    name = ambient.__name__
    def fresh_scope():
        with monkeypatch.context() as patch:
            patch.delitem(sys.modules, name)
            patch.delattr(data_sheets_schema, 'native_subscription_guard_v2')
            yield
    monkeypatch.setattr(callbacks, 'preloaded_callbacks', contextmanager(fresh_scope))
    now = [1000000000.0]
    with monkeypatch.context() as patch:
        freeze_subscription_clock(patch, lambda: now[0])
        assert ambient._now() == now[0]
        with callbacks.preloaded_callbacks():
            current = sys.modules[name]
            assert current is not ambient
            assert current._now() == now[0]
            now[0] += current.MAX_AGE_SECONDS + 1
            assert current._now() == ambient._now() == now[0]
        assert current.datetime is datetime
    assert ambient.datetime is datetime
