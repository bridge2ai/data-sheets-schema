"""Live pure-schema reuse; saved/final derivation remains independent."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_receipts as receipts
from data_sheets_schema import native_shared_results as results
from data_sheets_schema import native_shared_selection as selected
from tests.test_native_shared_schema_derivation_once import _no_io, _pool
from tests.test_native_shared_selection import artifact, declaration, pin, save, update_input


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch):
    cache = selected._SchemaDerivationCache()
    monkeypatch.setattr(selected, '_SCHEMA_DERIVATIONS', cache)
    return cache


@pytest.fixture
def views(monkeypatch):
    seen = []
    actual = selected.captured_view

    @contextmanager
    def observe(snapshot):
        seen.append(str(snapshot.sources[0][1]))
        with actual(snapshot) as view:
            yield view

    monkeypatch.setattr(selected, 'captured_view', observe)
    return seen


def _artifacts(saved):
    return {a.pin.role: a for a in (saved.receipt_policy, *saved.authority,
            *(a for schema in saved.schemas for a in schema.sources))}


def test_warm_live_capture_and_fresh_public_saved_rebuild(declaration, monkeypatch, views):
    first = selected.capture(declaration['registration_path'])
    assert len(views) == 2
    second = selected.capture(declaration['registration_path'])
    assert len(views) == 2
    assert first == second and first is not second
    assert first.schemas[0] is not second.schemas[0]
    assert first.schemas[0].sources[0] is not second.schemas[0].sources[0]
    with pytest.raises(FrozenInstanceError):
        second.schemas[0].kind = 'core'
    second.document()['inputs']['full_schema']['sources'].clear()
    second.generation_context()['profile']['name'] = 'changed returned copy'
    assert selected.capture(declaration['registration_path']) == first
    assert len(views) == 2
    pool, value = _pool(first)
    with monkeypatch.context() as trapped:
        _no_io(trapped)
        assert selected.rebuild(first.registration, first.authority,
                                first.schemas, first.receipt_policy) == first
        assert len(views) == 4
        assert results._captured_selection(pool, value) == first
        assert len(views) == 6
    for key, (metadata, _) in selected._SCHEMA_DERIVATIONS._entries.items():
        assert type(key[0]) is bytes and type(key[1]) is tuple
        assert all(type(raw) is bytes for raw in key[1])
        assert type(metadata) is bytes


@pytest.mark.parametrize('mutation,diagnostic', [
    ('class', 'lacks Dataset'),
    ('import', 'outside the complete captured closure'),
    ('name', 'names, order or import closure differ'),
    ('extra', 'names, order or import closure differ'),
])
def test_rehashed_same_path_changes_rederive_and_never_cache_refusal(
        declaration, monkeypatch, mutation, diagnostic):
    saved = selected.capture(declaration['registration_path'])
    original_entries = tuple(selected._SCHEMA_DERIVATIONS._entries.items())
    full = declaration['inputs']['full_schema']
    path = Path(full['root'])
    original = path.read_bytes()
    path.with_name('original-full.bin').write_bytes(original)
    if mutation in ('class', 'import'):
        raw = (original.replace(b'Dataset:', b'Awayset:') if mutation == 'class'
               else original + b'imports:\n  - absent\n')
        path.write_bytes(raw)
        full['sources'][0].update(pin(path, raw))
    elif mutation == 'name':
        full['sources'][0]['name'] = 'foreign'
    else:
        unused = path.with_name('unused.yaml')
        raw = b'id: https://example.org/unused\nname: unused\nclasses:\n  Unused: {}\n'
        unused.write_bytes(raw)
        full['sources'].append({'name': 'unused', **pin(unused, raw)})
    save(declaration)
    derived = []
    actual = selected._schemas

    def observe(doc, artifacts):
        derived.append(doc['inputs']['full_schema'])
        return actual(doc, artifacts)

    monkeypatch.setattr(selected, '_schemas', observe)
    for _ in range(2):
        with pytest.raises(ValueError, match=diagnostic):
            selected.capture(declaration['registration_path'])
    assert len(derived) == 2
    assert tuple(selected._SCHEMA_DERIVATIONS._entries.items()) == original_entries
    assert saved.schemas[0].sources[0].raw == original


def test_warm_cache_keeps_complete_import_order_validation(declaration):
    from data_sheets_schema.schema_snapshot import capture_schema
    full = declaration['inputs']['full_schema']
    root = Path(full['root'])
    for name in ('left', 'right'):
        root.with_name(name + '.yaml').write_text(
            f'id: https://example.org/{name}\nname: {name}\nclasses:\n  {name.title()}: {{}}\n')
    root.write_bytes(root.read_bytes() + b'imports:\n  - left\n  - right\n')
    snapshot = capture_schema(root, strict=True)
    full['sources'] = [{'name': str(name), **pin(path, raw)}
                       for name, path, raw in snapshot.sources]
    save(declaration)
    selected.capture(declaration['registration_path'])
    assert len(full['sources']) == 3
    full['sources'][1:] = reversed(full['sources'][1:])
    save(declaration)
    with pytest.raises(ValueError, match='names, order or import closure differ'):
        selected.capture(declaration['registration_path'])


@pytest.mark.parametrize('mutation,diagnostic', [
    ('bytes', 'bytes differ from their registration'),
    ('context', 'exactly one root'),
    ('receipt', 'native receipt asset differs'),
    ('bounds', 'declared input exceeds'),
    ('late_change', 'changed before capture completed'),
])
def test_warm_schema_result_cannot_replace_current_authority_checks(
        declaration, monkeypatch, mutation, diagnostic):
    selected.capture(declaration['registration_path'])
    target = Path(declaration['inputs']['bundle']['path'])
    original = target.read_bytes()
    target.with_name('original-bundle.bin').write_bytes(original)
    if mutation == 'bytes':
        target.write_bytes(original.replace(b'Complete', b'Altered!'))
    elif mutation == 'context':
        context = c.strict_json(Path(declaration['inputs']['context']['path']).read_bytes())
        context['scopes'].append(context['scopes'][0])
        update_input(declaration, 'context', c.canonical(context))
    elif mutation == 'receipt':
        path = Path(declaration['receipt_policy']['path'])
        value = c.strict_json(path.read_bytes())
        value['runtime_policy_sha256'] = 'f' * 64
        raw = c.canonical(value)
        path.write_bytes(raw)
        declaration['receipt_policy'] = pin(path, raw)
        save(declaration)
    elif mutation == 'bounds':
        declaration['bounds']['max_input_bytes'] = 1
        save(declaration)
    else:
        actual = selected._Reads.read
        changed = False

        def edit_after_read(reader, path, maximum):
            nonlocal changed
            raw = actual(reader, path, maximum)
            if Path(path) == target and not changed:
                target.write_bytes(raw.replace(b'Complete', b'Altered!'))
                changed = True
            return raw

        monkeypatch.setattr(selected._Reads, 'read', edit_after_read)
    with pytest.raises(ValueError, match=diagnostic):
        selected.capture(declaration['registration_path'])


def test_key_binds_raw_role_path_declaration_and_limits(declaration, monkeypatch):
    from copy import deepcopy
    saved = selected.capture(declaration['registration_path'])
    doc, artifacts = saved.document(), _artifacts(saved)
    key = selected._schema_cache_key(doc, artifacts)
    metadata = c.strict_json(key[0])
    assert metadata['domain'] == 'native_shared_schema_derivation_v1'
    assert metadata['strict'] is True and metadata['logical_paths'] is True
    assert metadata['namespace_orders'] is None
    assert [row['kind'] for row in metadata['schemas']] == ['full', 'core']
    source = artifacts['full_schema:0']
    for field, new_value in [('root', source.pin.path + '.other'), ('root_class', 'Other')]:
        changed = deepcopy(doc)
        changed['inputs']['full_schema'][field] = new_value
        assert selected._schema_cache_key(changed, artifacts) != key
    for changed in (
        artifact(source.pin.role, source.pin.path, source.raw + b'\n'),
        artifact('different-role', source.pin.path, source.raw),
        artifact(source.pin.role, source.pin.path + '.other', source.raw),
    ):
        assert selected._schema_cache_key(doc, {**artifacts, 'full_schema:0': changed}) != key
    monkeypatch.setattr(c, 'HARD_LIMITS', {**c.HARD_LIMITS, 'schema_member_bytes': len(source.raw) - 1})
    assert selected._schema_cache_key(doc, artifacts) != key
    with pytest.raises(ValueError, match='byte bound'):
        selected._cached_schemas(doc, artifacts)


def _payload_key(total, *, name=b'{}', value=b'[]'):
    """Synthetic immutable payloads exercise accounting, not schema admission."""
    remaining = total - len(name) - len(value)
    chunk = b'x' * 78_125
    count, extra = divmod(remaining, len(chunk))
    return (name, (chunk,) * count + ((chunk[:extra],) if extra else ())), value


def test_actual_payload_limit_counts_repeated_members_and_skips_oversize():
    cache = selected._SchemaDerivationCache()
    exact, value = _payload_key(40_000_000)
    cache.put(exact, value)
    assert cache.get(exact) == value and cache._bytes == 40_000_000
    oversized, value = _payload_key(40_000_001)
    cache.put(oversized, value)
    assert cache.get(oversized) is None
    assert cache.get(exact) == value and cache._bytes == 40_000_000
    replacement, value = _payload_key(20_000_000, name=b'{"other":1}')
    cache.put(replacement, value)
    assert cache.get(exact) is None
    assert cache.get(replacement) == value and cache._bytes == 20_000_000


def test_entry_eviction_and_duplicate_insert_accounting():
    cache = selected._SchemaDerivationCache()
    entries = [_payload_key(100, name=str(i).encode()) for i in range(3)]
    for key, value in entries[:2]:
        cache.put(key, value)
    cache.put(*entries[0])
    assert cache._bytes == 200
    cache.put(*entries[2])
    assert cache.get(entries[1][0]) is None
    assert cache.get(entries[0][0]) == entries[0][1]
    assert cache.get(entries[2][0]) == entries[2][1]
    assert len(cache._entries) == 2 and cache._bytes == 200


def test_cache_refuses_mutable_payloads_without_retaining_them():
    cache = selected._SchemaDerivationCache()
    for key, value in [((b'{}', [b'raw']), b'[]'), ((b'{}', (bytearray(b'raw'),)), b'[]'),
                       ((b'{}', (b'raw',)), {'checked': True})]:
        with pytest.raises(ValueError, match='immutable'):
            cache.put(key, value)
    assert cache._bytes == 0 and not cache._entries


def test_oversize_derivation_computes_without_retaining_or_refusing(declaration, monkeypatch, views):
    monkeypatch.setattr(selected, '_SCHEMA_CACHE_BYTES', 1)
    first = selected.capture(declaration['registration_path'])
    assert selected.capture(declaration['registration_path']) == first
    assert len(views) == 4 and not selected._SCHEMA_DERIVATIONS._entries


def test_concurrent_identical_misses_derive_outside_cache_lock(declaration, monkeypatch):
    barrier = Barrier(2)
    actual = selected._schemas
    entered = []

    def synchronized(doc, artifacts):
        entered.append(doc['registration_id'])
        barrier.wait(timeout=10)
        return actual(doc, artifacts)

    monkeypatch.setattr(selected, '_schemas', synchronized)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(selected.capture, declaration['registration_path']) for _ in range(2)]
        values = [future.result(timeout=20) for future in futures]
    assert len(entered) == 2 and values[0] == values[1]
    assert values[0] is not values[1]
    assert len(selected._SCHEMA_DERIVATIONS._entries) == 1
    assert selected.capture(declaration['registration_path']) == values[0]
    assert len(entered) == 2


def test_concurrent_distinct_payloads_stay_bounded():
    cache = selected._SchemaDerivationCache()
    entries = [_payload_key(100, name=str(i).encode()) for i in range(32)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda pair: cache.put(*pair), entries))
    assert len(cache._entries) == 2 and cache._bytes == 200


@pytest.mark.parametrize('route', ['live', 'recorded'])
def test_final_receipt_routes_fresh_rebuild_before_assessment(
        declaration, monkeypatch, tmp_path, views, route):
    # Actual S reconstruction and views; stage/receipt adapters are explicit
    # spies, so this tests routing/order, not an invented complete native run.
    saved = selected.capture(declaration['registration_path'])
    selected.capture(declaration['registration_path'])
    assert len(views) == 2
    full_path, receipt_path = str(tmp_path / 'full.yaml'), str(tmp_path / 'receipt.yaml')
    full = artifact('final_full', full_path, b'id: sample\n')
    original = artifact('original_receipt_output', receipt_path, b'original\n')
    effective = artifact('effective_receipt', str(tmp_path / 'effective.yaml'), b'effective\n')
    assembly = artifact('typed_assembly', str(tmp_path / 'assembly.json'), b'{}')
    seen, selections = [], []

    def decision(selection, *_args):
        assert selection == saved and selection is not saved
        assert len(views) == 4
        seen.append('decision')
        return SimpleNamespace(state='assembly_complete', completion=SimpleNamespace(assembly=assembly))

    run = SimpleNamespace(selection=saved, spec=SimpleNamespace(_agentic_artifact_paths={
        'full': full_path, 'receipt': receipt_path}), phase1=SimpleNamespace(original_receipt=original),
        binding=object(), history=object(), decision=lambda: pytest.fail('final reused live decision'))
    completion = SimpleNamespace(effective_receipt=effective)

    def check_assembly(selection, *args):
        assert seen == ['decision'] and selection == saved and selection is not saved
        selections.append(selection)
        seen.append('assembly')
        return completion

    def check_final(selection, *args, **kwargs):
        assert seen == ['decision', 'assembly'] and selection is selections[0]
        assert kwargs == {'final_full': full.raw, 'final_receipt': effective.raw}
        seen.append('receipt')
        return {'passed': True}

    monkeypatch.setattr(capture, 'current_artifact', lambda _run, role, _path:
                        {'final_full': full, 'original_receipt_output': original}[role])
    monkeypatch.setattr(capture, '_load_live', lambda _path: run)
    monkeypatch.setattr(capture, '_recorded_run', lambda _spec, _record: run)
    monkeypatch.setattr(capture, 'phase_replay', lambda _run: ({'passed': True}, None))
    monkeypatch.setattr(capture.stage, 'prepare_next', decision)
    monkeypatch.setattr(capture.stage, 'check_assembly', check_assembly)
    monkeypatch.setattr(receipts, 'check_final', check_final)
    with monkeypatch.context() as trapped:
        _no_io(trapped)
        if route == 'live':
            block = capture.live_receipt_block(declaration['registration_path'],
                                               full_path=full_path, receipt_path=receipt_path)
        else:
            block = capture.recorded_receipt_block(None, record={}, full_path=full_path, receipt_path=receipt_path)
    assert seen == ['decision', 'assembly', 'receipt'] and block['passed'] is True
    assert block['native_receipt_inputs']['selected_original']['sha256'] == original.pin.sha256
    assert block['native_receipt_inputs']['assessed_effective']['sha256'] == effective.pin.sha256
