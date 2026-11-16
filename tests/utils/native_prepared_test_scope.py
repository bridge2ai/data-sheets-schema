"""Test inputs for D156 fresh modules; preserve verified callable identities."""
from contextlib import contextmanager
from datetime import datetime, timezone
import sys


def configure_prepared_scope(monkeypatch, configure):
    from data_sheets_schema import native_shared_callback_orchestration as callbacks
    original = callbacks.preloaded_callbacks

    def scoped(*args, **kwargs):
        with original(*args, **kwargs) as prepared:
            with monkeypatch.context() as patch:
                configure(patch)
                yield prepared

    monkeypatch.setattr(callbacks, 'preloaded_callbacks', contextmanager(scoped))


def freeze_subscription_clock(monkeypatch, clock):
    """Freeze external datetime inputs in ambient and D156 source-loaded modules."""
    from tests.utils import native_synthetic_evidence as evidence
    from data_sheets_schema import native_subscription_guard_v2 as guard

    class FixtureDateTime(datetime):
        def now(tz=None):
            value = datetime.fromtimestamp(clock(), timezone.utc)
            return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)

    monkeypatch.setattr(evidence, 'datetime', FixtureDateTime)
    monkeypatch.setattr(guard, 'datetime', FixtureDateTime)

    def configure(patch):
        current = sys.modules['data_sheets_schema.native_subscription_guard_v2']
        patch.setattr(current, 'datetime', FixtureDateTime)

    configure_prepared_scope(monkeypatch, configure)
