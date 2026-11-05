"""Read-only BC1 schema derivations (#5489/#5490, 2026-11-05).

Only captured schema -> catalog work is shared. Live capture, source-byte
revalidation, record parsing, sizing, admission and response replay still run.
"""
import json

import pytest

from data_sheets_schema import audit_omissions as omissions, bc1_context as context
from data_sheets_schema.schema_snapshot import SchemaSnapshot


@pytest.fixture(scope='module')
def catalog_bytes():
    # Cache values are immutable serialized bytes, never a dict or SchemaView.
    return {}


def catalog_copy(cache, function, snapshot, *args, **kwargs):
    # Invalid/unfrozen inputs take the original refusal path, without a lookup.
    if (type(snapshot) is not SchemaSnapshot or type(snapshot.sources) is not tuple
            or not snapshot.sources or any(type(row) is not tuple or len(row) != 3
                or type(row[2]) is not bytes for row in snapshot.sources)):
        return function(*args, **kwargs)
    key = (function, snapshot.sources, snapshot.key, args)
    try:
        hash(key)
    except TypeError:
        return function(*args, **kwargs)
    if key not in cache:
        cache[key] = json.dumps(function(*args, **kwargs), ensure_ascii=False).encode()
    assert type(cache[key]) is bytes
    return json.loads(cache[key])


@pytest.fixture
def immutable_catalogs(monkeypatch, catalog_bytes):
    schema, core = omissions._schema, context._core_catalog

    def schema_copy(path, *, schema_snapshot=None):
        if schema_snapshot is None:
            return schema(path)
        return catalog_copy(catalog_bytes, schema, schema_snapshot, path,
                            schema_snapshot=schema_snapshot)

    def core_copy(snapshot):
        return catalog_copy(catalog_bytes, core, snapshot, snapshot)

    monkeypatch.setattr(omissions, '_schema', schema_copy)
    monkeypatch.setattr(context, '_core_catalog', core_copy)
    # Leave production dependency tokens untouched: they may conservatively
    # bypass their own caches when they see these test-only replacements.
