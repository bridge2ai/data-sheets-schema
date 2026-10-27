"""Real bounded root parsing; no native execution or scientific assertion."""
from dataclasses import replace

import pytest

from data_sheets_schema import grounding
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_receipts as nr
from tests.test_native_shared_receipt_catalog import changed_schema
from tests.test_native_shared_stages import artifact, case
from tests.test_typed_audit import supplied


def test_cold_native_root_is_parsed_once(case, monkeypatch):
    selection = case[0]
    snapshot = nr.schema_snapshot(selection)
    root = snapshot.sources[0][2]
    actual = nr.omissions._mapping
    seen = []

    def counted(raw, label, **kwargs):
        seen.append((raw, label))
        return actual(raw, label, **kwargs)

    monkeypatch.setattr(nr.omissions, '_mapping', counted)
    bases, catalog = nr._ReceiptCatalogContext().schema_data(selection, snapshot)
    assert bases == ()  # Imported prefixes cannot supply native root bases.
    assert 'Dataset' in catalog['classes']
    assert [label for raw, label in seen if raw == root] == ['captured schema']
    for _, _, imported in snapshot.sources[1:]:
        assert [label for raw, label in seen if raw == imported] == ['schema']


def test_legacy_catalog_never_acquires_native_bases_validation(case, monkeypatch):
    snapshot = nr.schema_snapshot(case[0])
    root = snapshot.sources[0][1]
    expected = nr.omissions._schema(root, schema_snapshot=snapshot, logical_paths=True)

    def forbidden(_schema):
        raise AssertionError('native-only prefix validation')

    monkeypatch.setattr(grounding, 'declared_bases_of', forbidden)
    assert nr.omissions._schema(root, schema_snapshot=snapshot, logical_paths=True) == expected
    with pytest.raises(AssertionError, match='native-only'):
        nr.omissions._schema_with_root_bases(root, schema_snapshot=snapshot)


@pytest.mark.parametrize('raw,error,message', [
    (b'id: https://example.test/bad\nname: bad\nprefixes: [wrong]\nimports: [missing]\n',
     AttributeError, "has no attribute 'items'"),
    (b'id: https://example.test/bad\nname: one\nname: two\nimports: [missing]\n',
     ValueError, 'captured schema cannot be read safely'),
])
def test_native_root_failure_still_precedes_closure_validation(case, raw, error, message):
    selection = changed_schema(case[0], raw)
    context = nr._ReceiptCatalogContext()
    with pytest.raises(error, match=message):
        context.schema_data(selection, nr.schema_snapshot(selection))
    assert context._entry is None and context._bytes == 0


@pytest.mark.parametrize('problem', ['duplicate', 'nodes', 'depth'])
def test_each_import_keeps_strict_parser_limits(case, monkeypatch, problem):
    selection = case[0]
    full = next(row for row in selection.schemas if row.kind == 'full')
    original = full.sources[1]
    if problem == 'duplicate':
        raw = b'name: first\nname: second\n'
    elif problem == 'nodes':
        monkeypatch.setattr(nr.omissions, 'MAX_NODES', 30)
        raw = b'nodes: [' + b'1,' * 40 + b'1]\n'
    else:
        monkeypatch.setattr(nr.omissions, 'MAX_DEPTH', 4)
        raw = b'deep: [[[[[1]]]]]\n'
    sources = (full.sources[0], artifact(original.pin.role, original.pin.path, raw), *full.sources[2:])
    full = replace(full, sources=sources, closure_sha256=c.schema_closure_sha(sources, full.import_roles))
    selection = replace(selection, schemas=tuple(full if row.kind == 'full' else row
                                                for row in selection.schemas))
    context = nr._ReceiptCatalogContext()
    with pytest.raises(ValueError, match='^schema cannot be read safely'):
        context.schema_data(selection, nr.schema_snapshot(selection))
    assert context._entry is None


def test_root_depth_check_is_not_skipped_by_joint_derivation(case, monkeypatch):
    raw = b'id: https://example.test/bad\nname: bad\ndeep: [[[[[1]]]]]\n'
    selection = changed_schema(case[0], raw)
    monkeypatch.setattr(nr.omissions, 'MAX_DEPTH', 4)
    with pytest.raises(ValueError, match='captured schema cannot be read safely'):
        nr._ReceiptCatalogContext().schema_data(selection, nr.schema_snapshot(selection))


def test_native_joint_derivation_keeps_captured_import_closure(case, monkeypatch):
    selection = changed_schema(case[0], b'id: https://example.test/bad\nname: bad\nimports: [missing]\n')
    snapshot = nr.schema_snapshot(selection)

    def forbidden(*_args, **_kwargs):
        raise AssertionError('ambient schema read')

    from pathlib import Path
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    with pytest.raises(ValueError, match='outside the captured closure'):
        nr._ReceiptCatalogContext().schema_data(selection, snapshot)
