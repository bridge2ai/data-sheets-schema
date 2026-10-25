"""Target schema-event changes cannot hide behind a warm native typed catalog."""
import pytest

from data_sheets_schema import audit_omissions as omissions
from data_sheets_schema import native_catalog_reuse as guard
from tests.test_native_typed_catalog import constructions, error, ready, run
from tests.test_typed_audit import supplied


@pytest.mark.parametrize('mutation', ['reader', 'reader_code', 'loader_method', 'loader_class'])
def test_warm_catalog_preserves_current_schema_event_refusal(ready, monkeypatch, mutation):
    args, choice, context = ready
    assert context._typed_catalog(choice, args['schema_path'], args['schema_snapshot']) is not None

    def refuse(*args, **kwargs):
        raise ValueError('current schema-event dependency refused')

    if mutation == 'reader':
        monkeypatch.setattr(omissions, '_schema_yaml', refuse)
    elif mutation == 'reader_code':
        monkeypatch.setattr(omissions._schema_yaml, '__code__', refuse.__code__)
    elif mutation == 'loader_method':
        monkeypatch.setattr(omissions._SchemaEventLoader, 'get_event', refuse)
    else:
        class RefusingLoader(omissions._SchemaEventLoader):
            get_event = refuse
        monkeypatch.setattr(omissions, '_SchemaEventLoader', RefusingLoader)
    # The literal old constructor must actually observe the injected refusal.
    expected = error(lambda: run(args, choice, context, original=True))
    assert 'current schema-event dependency refused' in str(expected)
    assert guard.runtime_token() is None
    assert context._typed_catalog(choice, args['schema_path'], args['schema_snapshot']) is None
    assert error(lambda: run(args, choice, context)) == expected


@pytest.mark.parametrize('constant', ['MAX_SCHEMA_EVENTS', 'MAX_SCHEMA_EVENT_CHARS'])
def test_schema_event_retention_limit_change_uses_current_constructor(ready, monkeypatch, constant):
    args, choice, context = ready
    monkeypatch.setattr(omissions, constant, 0)
    assert guard.runtime_token() is None
    assert context._typed_catalog(choice, args['schema_path'], args['schema_snapshot']) is None
    expected = run(args, choice, context, original=True)
    with constructions() as calls:
        actual = run(args, choice, context)
    assert len(calls) == 1
    assert actual == expected
