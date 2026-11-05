"""Isolation and byte-key controls for the #5489/#5490 test helper."""
import pytest

from tests.bc1_catalog_fixture import catalog_copy
from tests.test_bc1_context import fixture  # noqa: F401
from data_sheets_schema import audit_omissions as omissions, bc1_context as context
from data_sheets_schema.schema_snapshot import capture_schema


@pytest.mark.parametrize('kind', ['full', 'core'])
def test_catalog_copies_are_isolated_and_changed_bytes_rederive(fixture, kind):
    _, inputs = fixture
    snapshot = inputs['schema_snapshot']
    path = inputs['schema_path']
    cache = {}

    def read(selected):
        if kind == 'full':
            return catalog_copy(cache, omissions._schema, selected, path, schema_snapshot=selected)
        return catalog_copy(cache, context._core_catalog, selected, selected)

    expected = (omissions._schema(path, schema_snapshot=snapshot) if kind == 'full'
                else context._core_catalog(snapshot))
    first, second = read(snapshot), read(snapshot)
    assert first == second == expected and first is not second
    root = 'Dataset' if kind == 'full' else 'CoreDataset'
    first['classes'][root]['slots'].clear()
    assert second == expected and read(snapshot) == expected
    assert len(cache) == 1 and all(type(value) is bytes for value in cache.values())
    _, source, raw = snapshot.sources[0]
    source.write_bytes(raw.replace(b'Complete', b'Changed'))
    changed = capture_schema(source, strict=True)
    derived = read(changed)
    assert derived != expected and len(cache) == 2
    assert read(snapshot) == expected  # Captured bytes never fall back to disk.
    with pytest.raises(ValueError, match='root differs'):
        catalog_copy(cache, omissions._schema, snapshot, path.parent / 'other.yaml', schema_snapshot=snapshot)
