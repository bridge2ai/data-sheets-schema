"""Pure catalog reuse with real tiny schemas; no observed native run claimed."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields, replace
import json
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_receipts as nr
from data_sheets_schema import native_shared_stage as stage
from tests.test_native_shared_stages import (case, artifact, publish, receipt_answer,
                                             respond)
from tests.test_typed_audit import supplied


@pytest.fixture
def derivations(monkeypatch):
    actual = nr.omissions._schema
    seen = []

    def counted(*args, **kwargs):
        seen.append(kwargs['schema_snapshot'].sources)
        return actual(*args, **kwargs)

    monkeypatch.setattr(nr.omissions, '_schema', counted)
    return seen


@pytest.fixture
def root_derivations(monkeypatch):
    actual = nr.omissions._mapping
    seen = []

    def counted(raw, label, **kwargs):
        if label == 'captured schema':
            seen.append(raw)
        return actual(raw, label, **kwargs)

    monkeypatch.setattr(nr.omissions, '_mapping', counted)
    return seen


def changed_schema(selection, raw=None, *, name=None, role=None, path=None):
    full = next(row for row in selection.schemas if row.kind == 'full')
    first = full.sources[0]
    new = artifact(role or first.pin.role, path or first.pin.path,
                   first.raw if raw is None else raw)
    sources = (new, *full.sources[1:])
    imports = tuple((name or n, new.pin.role) if r == first.pin.role else (n, r)
                    for n, r in full.import_roles)
    full = replace(full, root_name=name or full.root_name, sources=sources,
                   import_roles=imports, closure_sha256=c.schema_closure_sha(sources, imports))
    return replace(selection, schemas=tuple(full if row.kind == 'full' else row for row in selection.schemas))


def fake_run(case):
    # Only pure stage methods are exercised: no fabricated observation claim.
    s, e, p, h = case
    return capture._CapturedRun(s, {}, {}, object(), None, None, None, None,
                                e, h, (), p)


@pytest.mark.parametrize('completed', [False, True])
def test_real_catalog_counts_and_complete_request_result_byte_parity(case, monkeypatch, derivations, completed):
    if completed:
        case, transition = respond(case, receipt_answer(case))
        assert transition.disposition == 'checked'
    else:
        case = (*case[:3], publish(case[3], stage.prepare_next(*case)))
    derivations.clear()
    with monkeypatch.context() as uncached:
        uncached.setattr(nr, '_CATALOG_PAYLOAD_BYTES', 0)
        old = stage._Replay(*case).run()
    assert len(derivations) == (4 if completed else 2)
    derivations.clear()
    current = stage._Replay(*case).run()
    assert len(derivations) == 1
    assert current.pending == old.pending and current.receipt == old.receipt
    if completed:
        assert current.receipt.request_json and current.receipt.result_json and current.receipt.carry_json
        assert current.pending[0] == 'await_core'
    else:
        assert current.pending[0] == 'awaiting_response'


def test_private_run_reuses_catalog_but_new_public_and_replaced_runs_are_fresh(case, derivations, root_derivations, monkeypatch):
    run = fake_run(case)
    first = run.decision()
    assert run.decision() == first and len(derivations) == 1
    # Actual stage work; only the already-covered captured-prefix lookup is a spy.
    monkeypatch.setattr(capture, '_history_prefix', lambda actual, digest: actual.history)
    monkeypatch.setattr(capture, '_phase1', lambda *_args: run.phase1)
    assert capture._decision_at(run, run.history.journal.pin.sha256) == first
    assert len(derivations) == 1
    duplicate = replace(run)
    assert duplicate == run and duplicate._catalogs is not run._catalogs
    assert duplicate.decision() == first and len(derivations) == 2
    saved_constructor = fake_run(case)
    assert saved_constructor._catalogs is not run._catalogs
    assert saved_constructor.decision() == first and len(derivations) == 3
    assert stage.prepare_next(*case) == first and len(derivations) == 4
    field = next(row for row in fields(run) if row.name == '_catalogs')
    assert not field.init and not field.compare and not field.repr
    assert '_catalogs' not in repr(run)
    assert len(root_derivations) == len(derivations) == 4


def test_public_receipt_and_claim_inputs_stay_fresh_and_returns_are_private(case, derivations, root_derivations):
    s, e, p, _ = case
    first = nr.prepare(s, e, p)
    assert len(derivations) == 1
    first['schema']['classes'].clear()
    assert nr.prepare(s, e, p)['schema']['classes'] and len(derivations) == 2
    raw = receipt_answer(case)
    derivations.clear()
    root_derivations.clear()
    completed = nr.complete(s, e, p, raw)
    assert len(derivations) == 1
    assert nr.complete(s, e, p, raw) == completed and len(derivations) == 2
    nr._inputs(s, p)  # Exact existing recorded_receipt_claims signature.
    nr._raw_inputs(s, p.full.raw, p.original_receipt.raw)
    assert len(derivations) == 4
    assert len(root_derivations) == 4


def test_initial_and_final_public_receipts_do_not_inherit_a_warm_context(case, derivations, root_derivations):
    s, e, p, _ = case
    context = nr._ReceiptCatalogContext()
    nr._prepare(s, e, p, context)
    assert len(derivations) == 1
    nr.check_initial(s, full_raw=p.full.raw, receipt_raw=p.original_receipt.raw)
    assert len(derivations) == 2
    completion = SimpleNamespace(selection_sha256=s.registration.pin.sha256,
        execution_sha256=e.execution.pin.sha256, phase1_seal_sha256=p.seal.pin.sha256,
        effective_receipt=p.original_receipt, history_sha256='a' * 64)
    # Real final receipt check; completion is an explicit lineage fixture only.
    nr.check_final(s, e, p, completion, final_full=p.full.raw, final_receipt=p.original_receipt.raw)
    assert len(derivations) == 3
    assert len(root_derivations) == 3


@pytest.mark.parametrize('mutation', ['raw', 'role', 'path', 'name', 'order', 'bounds', 'limit', 'domain'])
def test_complete_key_changes(case, monkeypatch, mutation):
    s = case[0]
    before = nr._catalog_key(s, nr.schema_snapshot(s))
    root = s.schemas[0].sources[0]
    if mutation == 'raw': s = changed_schema(s, root.raw + b'\n# changed captured bytes\n')
    elif mutation == 'role': s = changed_schema(s, role='another_full_root')
    elif mutation == 'path': s = changed_schema(s, path='/elsewhere/full.yaml')
    elif mutation == 'name': s = changed_schema(s, name='another_logical_name')
    elif mutation == 'order':
        full = s.schemas[0]
        sources = (full.sources[0], *reversed(full.sources[1:]))
        full = replace(full, sources=sources, closure_sha256=c.schema_closure_sha(sources, full.import_roles))
        s = replace(s, schemas=(full, s.schemas[1]))
    elif mutation == 'bounds':
        bounds = {**s.bounds(), 'max_populated_paths': s.bounds()['max_populated_paths'] - 1}
        doc = s.document(); doc['bounds'] = bounds
        s = replace(s, bounds_json=c.canonical(bounds),
                    registration=artifact('selection', s.registration.pin.path, c.canonical(doc)))
    elif mutation == 'limit': monkeypatch.setattr(nr.omissions, 'MAX_DEPTH', nr.omissions.MAX_DEPTH - 1)
    else: monkeypatch.setattr(nr, '_CATALOG_DOMAIN', 'independent_catalog_mode')
    after = nr._catalog_key(s, nr.schema_snapshot(s))
    assert before != after


def test_bad_pin_and_missing_import_cannot_hit_or_store_exception(case, derivations):
    s = case[0]; context = nr._ReceiptCatalogContext()
    snapshot = nr.schema_snapshot(s)
    context.catalog(s, snapshot)
    original_entry = context._entry
    raw = s.schemas[0].sources[0].raw
    assert b'imports: [child]' in raw
    bad = changed_schema(s, raw.replace(b'imports: [child]', b'imports: [child, absent_private_import]'))
    for _ in range(2):
        with pytest.raises(ValueError, match='outside'):
            context.catalog(bad, nr.schema_snapshot(bad))
    assert len(derivations) == 3 and context._entry == original_entry
    # Deliberately bypass frozen-carrier construction; key integrity still refuses.
    tampered = changed_schema(s, raw)
    object.__setattr__(tampered.schemas[0].sources[0], 'raw', raw + b' ')
    with pytest.raises(ValueError, match='pin'):
        context.catalog(tampered, nr.schema_snapshot(tampered))
    assert len(derivations) == 3 and context._entry == original_entry


@pytest.mark.parametrize('mutation', ['full', 'receipt', 'context', 'manifest', 'policy', 'runtime'])
def test_current_noncatalog_inputs_are_rechecked_on_warm_context(case, derivations, mutation):
    s, e, p, _ = case; context = nr._ReceiptCatalogContext()
    nr._prepare(s, e, p, context)
    assert len(derivations) == 1
    key = nr._catalog_key(s, nr.schema_snapshot(s))
    if mutation == 'full':
        p = replace(p, full=artifact(p.full.pin.role, p.full.pin.path, b'invented_slot: value\n'))
    elif mutation == 'receipt':
        doc = c.strict_json(p.original_receipt.raw); doc['bundle_md5'] = '0' * 32
        p = replace(p, original_receipt=artifact(p.original_receipt.pin.role, p.original_receipt.pin.path, c.canonical(doc)))
    elif mutation == 'runtime':
        runtime = artifact(e.runtime_declaration.pin.role, e.runtime_declaration.pin.path,
                           c.canonical({'limits': {'maxOutputTokens': False}}))
        e = replace(e, runtime_declaration=runtime, runtime_declaration_sha256=runtime.pin.sha256)
    else:
        role = {'context': 'context', 'manifest': 'chunk_manifest', 'policy': 'native_policy'}[mutation]
        original = next(item for item in s.authority if item.pin.role == role)
        if mutation == 'context':
            doc = c.strict_json(original.raw); doc['scopes'].append({'owner': '/missing', 'scope': 'unknown'})
            raw = c.canonical(doc)
        elif mutation == 'manifest': raw = b'{"chunks": []}'
        else: raw = original.raw + b' foreign policy'
        replacement = artifact(role, original.pin.path, raw)
        s = replace(s, authority=tuple(replacement if item == original else item for item in s.authority))
    assert nr._catalog_key(s, nr.schema_snapshot(s)) == key
    with pytest.raises((ValueError, KeyError)):
        nr._prepare(s, e, p, context)
    assert len(derivations) == 1


def test_payload_accounting_eviction_oversize_and_copy_isolation(case, monkeypatch, derivations):
    s = case[0]; context = nr._ReceiptCatalogContext()
    value = context.catalog(s, nr.schema_snapshot(s))
    key, raw, bases = context._entry
    assert type(key[0]) is bytes and type(key[1]) is tuple and type(raw) is bytes
    assert all(type(item) is bytes for item in key[1])
    assert type(bases) is tuple and all(type(pair) is tuple for pair in bases)
    size = len(key[0]) + sum(map(len, key[1])) + len(raw) + len(
        json.dumps(bases, ensure_ascii=True, separators=(',', ':')).encode('ascii'))
    assert context._bytes == size and nr._CATALOG_PAYLOAD_BYTES == 40_000_000
    value['classes'].clear()
    assert context.catalog(s, nr.schema_snapshot(s))['classes'] and len(derivations) == 1
    monkeypatch.setattr(nr, '_CATALOG_PAYLOAD_BYTES', size)
    exact = nr._ReceiptCatalogContext(); exact.catalog(s, nr.schema_snapshot(s))
    assert exact._bytes == size
    monkeypatch.setattr(nr, '_CATALOG_PAYLOAD_BYTES', size - 1)
    over = nr._ReceiptCatalogContext()
    for _ in range(2): assert over.catalog(s, nr.schema_snapshot(s))['classes']
    assert over._entry is None and over._bytes == 0
    monkeypatch.setattr(nr, '_CATALOG_PAYLOAD_BYTES', 40_000_000)
    changed = changed_schema(s, s.schemas[0].sources[0].raw + b'\n# different bytes\n')
    context.catalog(changed, nr.schema_snapshot(changed))
    assert context._entry[0] != key
    before = len(derivations)
    context.catalog(s, nr.schema_snapshot(s))
    assert len(derivations) == before + 1 and context._entry[0] == key


def test_concurrent_misses_compute_outside_lock_and_return_independent_data(case, monkeypatch):
    s = case[0]; context = nr._ReceiptCatalogContext(); gate = Barrier(2)
    actual = nr.omissions._schema

    def together(*args, **kwargs):
        gate.wait(timeout=10)
        return actual(*args, **kwargs)

    monkeypatch.setattr(nr.omissions, '_schema', together)
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(lambda _: context.catalog(s, nr.schema_snapshot(s)), range(2)))
    assert values[0] == values[1] and values[0] is not values[1]
    values[0]['classes'].clear()
    assert values[1]['classes']
    assert context._bytes <= nr._CATALOG_PAYLOAD_BYTES


def test_public_response_and_assembly_checks_cannot_inherit_run_context(case, derivations, root_derivations):
    run = fake_run(case)
    ready = run.decision()
    assert len(derivations) == 1
    observed_case = (*case[:3], publish(case[3], ready))
    # Both real public paths reconstruct the catalog before their history refusal.
    with pytest.raises(ValueError, match='unique durable'):
        stage.check_response(*observed_case, ready.request.raw, b'{}')
    assert len(derivations) == 2
    with pytest.raises(ValueError, match='before every mandatory'):
        stage.check_assembly(*observed_case, b'{}')
    assert len(derivations) == 3
    assert len(root_derivations) == 3


def test_root_only_bases_are_immutable_and_explicit_empty_stays_empty(case, monkeypatch, derivations, root_derivations):
    from data_sheets_schema import grounding

    def no_default():
        raise AssertionError('captured roots must not consult installed identifier bases')

    monkeypatch.setattr(grounding, 'declared_bases', no_default)
    s = case[0]; context = nr._ReceiptCatalogContext()
    assert b'prefixes:' not in s.schemas[0].sources[0].raw
    assert any(b'prefixes:' in item.raw for item in s.schemas[0].sources[1:])
    empty, catalog = context.schema_data(s, nr.schema_snapshot(s))
    assert empty == () and catalog['classes']
    assert nr._raw_inputs(s, case[2].full.raw, case[2].original_receipt.raw, _catalogs=context)[5] == ()
    assert len(derivations) == len(root_derivations) == 1
    root = s.schemas[0].sources[0].raw
    s = changed_schema(s, root + b"prefixes: {short: 'https://x/', First: 'https://EXAMPLE.test/a/', Second: 'https://example.test/b/'}\n")
    bases, value = context.schema_data(s, nr.schema_snapshot(s))
    assert bases == (('https://example.test/a/', 'First'), ('https://example.test/b/', 'Second'), ('https://x/', 'short'))
    with pytest.raises(TypeError):
        bases[0][0] = 'mutated'
    value['classes'].clear()
    warm_bases, warm = context.schema_data(s, nr.schema_snapshot(s))
    assert warm_bases == bases and warm['classes']
    assert context.catalog(s, nr.schema_snapshot(s)) == warm
    assert len(derivations) == len(root_derivations) == 2


def test_changed_root_and_import_rederive_one_matched_pair(case, derivations, root_derivations):
    s = case[0]; context = nr._ReceiptCatalogContext()
    root = s.schemas[0].sources[0].raw
    first = changed_schema(s, root + b"prefixes: {left: 'https://left.test/'}\n")
    second = changed_schema(s, root + b"prefixes: {right: 'https://right.test/'}\n")
    left = context.schema_data(first, nr.schema_snapshot(first))
    right = context.schema_data(second, nr.schema_snapshot(second))
    assert left[0] == (('https://left.test/', 'left'),)
    assert right[0] == (('https://right.test/', 'right'),) and left[1] != right[1]
    full = second.schemas[0]; old = full.sources[1]
    updated = artifact(old.pin.role, old.pin.path, old.raw + b'\n# changed actual imported bytes\n')
    sources = (full.sources[0], updated, *full.sources[2:])
    full = replace(full, sources=sources, closure_sha256=c.schema_closure_sha(sources, full.import_roles))
    imported = replace(second, schemas=(full, second.schemas[1]))
    changed = context.schema_data(imported, nr.schema_snapshot(imported))
    assert changed[0] == right[0] and changed[1] != right[1]
    assert len(derivations) == len(root_derivations) == 3


def test_failed_root_derivation_never_replaces_valid_pair(case, derivations, root_derivations):
    s = case[0]; context = nr._ReceiptCatalogContext()
    original = context.schema_data(s, nr.schema_snapshot(s))
    entry, size = context._entry, context._bytes
    bad = changed_schema(s, b'id: [unterminated\n')
    for _ in range(2):
        with pytest.raises(ValueError):
            context.schema_data(bad, nr.schema_snapshot(bad))
    assert context._entry is entry and context._bytes == size
    assert context.schema_data(s, nr.schema_snapshot(s)) == original
    assert len(root_derivations) == 3 and len(derivations) == 1


def test_bases_storage_counts_without_an_extra_catalog_envelope_limit(case, monkeypatch, derivations):
    s = case[0]
    # Valid YAML scalar aliases expand into more bases bytes than root bytes.
    prefixes = "prefixes:\n  p000: &base 'https://example.test/" + 'a' * 500 + "/'\n"
    prefixes += ''.join(f'  p{i:03d}: *base\n' for i in range(1, 100))
    raw = s.schemas[0].sources[0].raw + prefixes.encode()
    s = changed_schema(s, raw); snapshot = nr.schema_snapshot(s)
    context = nr._ReceiptCatalogContext()
    expected = context.schema_data(s, snapshot)
    key, catalog_raw, bases = context._entry
    base_size = len(json.dumps(bases, ensure_ascii=True, separators=(',', ':')).encode('ascii'))
    catalog_bound = max(sum(map(len, key[1])), len(catalog_raw))
    assert len(catalog_raw) + base_size > catalog_bound
    monkeypatch.setattr(nr.omissions, 'MAX_SCHEMA_BYTES', catalog_bound)
    exact = nr._ReceiptCatalogContext()
    assert exact.schema_data(s, snapshot) == expected
    size = exact._bytes
    assert size == len(exact._entry[0][0]) + sum(map(len, key[1])) + len(catalog_raw) + base_size
    monkeypatch.setattr(nr, '_CATALOG_PAYLOAD_BYTES', size)
    retained = nr._ReceiptCatalogContext()
    assert retained.schema_data(s, snapshot) == expected and retained._bytes == size
    monkeypatch.setattr(nr, '_CATALOG_PAYLOAD_BYTES', size - 1)
    skipped = nr._ReceiptCatalogContext(); before = len(derivations)
    assert skipped.schema_data(s, snapshot) == skipped.schema_data(s, snapshot) == expected
    assert skipped._entry is None and skipped._bytes == 0
    assert len(derivations) == before + 2


def test_concurrent_distinct_keys_never_mix_catalog_and_root_bases(case, monkeypatch):
    s = case[0]; root = s.schemas[0].sources[0].raw
    selections = [changed_schema(s, root + f"prefixes: {{{side}: 'https://{side}.test/'}}\n".encode())
                  for side in ('left', 'right')]
    expected = [nr._ReceiptCatalogContext().schema_data(item, nr.schema_snapshot(item)) for item in selections]
    context = nr._ReceiptCatalogContext(); gate = Barrier(2)
    actual = nr.omissions._schema

    def together(*args, **kwargs):
        gate.wait(timeout=10)
        return actual(*args, **kwargs)

    with monkeypatch.context() as concurrent:
        concurrent.setattr(nr.omissions, '_schema', together)
        with ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(lambda item: context.schema_data(item, nr.schema_snapshot(item)), selections))
    assert values == expected and values[0] != values[1]
    key, raw, bases = context._entry
    assert (bases, c.strict_json(raw)) in expected
    assert key in [nr._catalog_key(item, nr.schema_snapshot(item)) for item in selections]
    for item, wanted in zip(selections, expected):
        assert context.schema_data(item, nr.schema_snapshot(item)) == wanted
    assert context._bytes <= nr._CATALOG_PAYLOAD_BYTES
