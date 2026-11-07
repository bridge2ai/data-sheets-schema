"""U3-B cold/warm/refusal, bounded events and exact initialization tests."""
from dataclasses import replace
from copy import deepcopy
import json
import time
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import audit_omissions as om
from data_sheets_schema import native_catalog_reuse as catalog
from data_sheets_schema import native_catalog_initialization as init
from data_sheets_schema import native_schema_event_reuse as events
from data_sheets_schema import native_shared_receipts as receipts
from data_sheets_schema import native_shared_selection as selection
from data_sheets_schema import typed_audit as typed
from tests.test_native_shared_selection import declaration, pin, save
from tests.test_typed_audit import supplied, replies
from tests.test_typed_audit_derivations import roundtrip


def test_supported_bindings():
    assert init.INITIALIZATION_ERROR is None
    assert catalog._FUNCTIONS.ready
    assert catalog.runtime_token() is init.marker()
    assert events._token(om.MAX_INPUT_BYTES) is not None, events.counters()


def test_optional_libyaml_import_preserves_m8_fallback(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / 'optional-libyaml.json'
    result = subprocess.run([sys.executable, str(root / 'scripts/adhoc/native_u3b_no_libyaml_probe.py'),
        '--source', str(root), '--output', str(output)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    observed = json.loads(output.read_bytes())
    assert observed == json.loads(result.stdout)
    assert observed['import_error'] is None
    assert observed['default_binding_ready'] is False
    assert observed['blocked_extension_imports'] == 1


def test_lazy_initialization_and_within_state_refusal_parity():
    script = Path(__file__).resolve().parents[1] / 'scripts/adhoc/native_u3b_lazy_probe.py'
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['within_state_parity'] is True


@pytest.fixture
def captured(declaration):
    selected = selection.capture(declaration['registration_path'])
    return selected, receipts.schema_snapshot(selected)


def test_catalog_cold_warm_private_objects(captured):
    selected, snapshot = captured
    context = receipts._ReceiptCatalogContext()
    first = context.schema_data(selected, snapshot)
    assert first[0] == ()  # Empty root bases do not inherit ambient defaults.
    assert context._entry_marker is catalog.runtime_token() is not None
    stored = context._entry
    second = context.schema_data(selected, snapshot)
    assert first == second and first[1] is not second[1]
    assert context._entry is stored
    second[1]['classes'].clear()
    assert context.schema_data(selected, snapshot) == first


@pytest.mark.parametrize('mutation', ['parser', 'parser_code', 'loader', 'events', 'characters'])
def test_target_parser_guard_refuses_warm_catalog(captured, monkeypatch, mutation):
    selected, snapshot = captured
    context = receipts._ReceiptCatalogContext()
    context.schema_data(selected, snapshot)
    assert context._typed_catalog(selected, snapshot.sources[0][1], snapshot) is not None
    def refuse(*args, **kwargs):
        raise ValueError('current schema-event refusal')
    if mutation == 'parser':
        monkeypatch.setattr(om, '_schema_yaml', refuse)
    elif mutation == 'parser_code':
        monkeypatch.setattr(om._schema_yaml, '__code__', refuse.__code__)
    elif mutation == 'loader':
        monkeypatch.setattr(om._SchemaEventLoader, 'get_event', refuse)
    else:
        monkeypatch.setattr(om, 'MAX_SCHEMA_EVENTS' if mutation == 'events' else 'MAX_SCHEMA_EVENT_CHARS', 0)
    assert catalog.runtime_token() is None
    assert context._typed_catalog(selected, snapshot.sources[0][1], snapshot) is None
    if mutation in ('parser', 'parser_code', 'loader'):
        with pytest.raises(ValueError):
            context.schema_data(selected, snapshot)


def test_catalog_identity_and_size_bounds(captured, monkeypatch):
    selected, snapshot = captured
    context = receipts._ReceiptCatalogContext()
    expected = context.schema_data(selected, snapshot)
    size = context._bytes
    assert 0 < size <= receipts._CATALOG_PAYLOAD_BYTES == 40_000_000
    monkeypatch.setattr(receipts, '_CATALOG_PAYLOAD_BYTES', size)
    exact = receipts._ReceiptCatalogContext()
    assert exact.schema_data(selected, snapshot) == expected
    assert exact._entry is not None
    monkeypatch.setattr(receipts, '_CATALOG_PAYLOAD_BYTES', size - 1)
    small = receipts._ReceiptCatalogContext()
    assert small.schema_data(selected, snapshot) == expected and small._entry is None
    bad = replace(snapshot, sources=((snapshot.sources[0][0], snapshot.sources[0][1], b'changed'),))
    with pytest.raises(ValueError, match='differs'):
        context.schema_data(selected, bad)


@pytest.mark.parametrize('mutation', ['mark_alias', 'callback_code', 'callback_defaults', 'callback_global', 'module_identity'])
def test_unknown_initialization_is_never_learned(monkeypatch, mutation):
    import linkml.utils.rawloader as rawloader
    assert init.phase() == 1
    if mutation == 'mark_alias':
        monkeypatch.setattr(yaml, 'Mark', init.LINKML_MARK)
    elif mutation == 'callback_code':
        def replacement(self, field_name):
            pass
        monkeypatch.setattr(rawloader.mrf, '__code__', replacement.__code__)
    elif mutation == 'callback_defaults':
        monkeypatch.setattr(rawloader.mrf, '__defaults__', ('name',))
    elif mutation == 'callback_global':
        monkeypatch.setattr(rawloader, 'YAMLRoot', object)
    else:
        monkeypatch.setattr(rawloader, '__file__', '/unrecognized/rawloader.py')
    with pytest.raises(TypeError):
        init.phase()
    assert catalog.runtime_token() is None
    assert events._token(om.MAX_INPUT_BYTES) is None


def test_unknown_state_rebuilds_every_time(captured, monkeypatch):
    selected, snapshot = captured
    context = receipts._ReceiptCatalogContext()
    expected = context.schema_data(selected, snapshot)
    monkeypatch.setattr(init, 'INITIALIZATION_ERROR', 'unknown installed provenance')
    assert catalog.runtime_token() is None
    assert context.schema_data(selected, snapshot) == expected
    first = context._entry
    assert context.schema_data(selected, snapshot) == expected
    assert context._entry is not first and context._entry_marker is None


def test_unknown_typed_lookup_cannot_revive_old_entry(captured, monkeypatch):
    selected, snapshot = captured
    context = receipts._ReceiptCatalogContext()
    expected = context.schema_data(selected, snapshot)
    with monkeypatch.context() as state:
        state.setattr(init, 'INITIALIZATION_ERROR', 'unknown current state')
        assert context._typed_catalog(selected, snapshot.sources[0][1], snapshot) is None
    assert context._entry is None
    assert context._typed_catalog(selected, snapshot.sources[0][1], snapshot) is None
    assert context.schema_data(selected, snapshot) == expected


def test_marker_change_during_hit_decoding_forces_fresh(captured, monkeypatch):
    selected, snapshot = captured
    context = receipts._ReceiptCatalogContext()
    expected = context.schema_data(selected, snapshot)
    old = context._entry
    marker = catalog.runtime_token()
    observations = iter((marker, None, None, None))
    monkeypatch.setattr(catalog, 'runtime_token', lambda: next(observations, None))
    # Simulate a dependency transition between lookup and decoded-hit return.
    assert context.schema_data(selected, snapshot) == expected
    assert context._entry is not old and context._entry_marker is None


def test_initialization_transition_and_callback_semantics(captured, monkeypatch):
    selected, snapshot = captured
    # Exercise the actual shipped callback without running a native executable.
    import linkml.utils.rawloader as rawloader
    with monkeypatch.context() as state:
        state.setattr(yaml.error, 'Mark', init.ORIGINAL_MARK)
        state.delattr(init._SCHEMA, 'MissingRequiredField')
        assert init.phase() == 0
        context = receipts._ReceiptCatalogContext()
        before = context.schema_data(selected, snapshot)
        old = context._entry
        token = catalog.runtime_token()
        assert token is not None
        with pytest.raises(ValueError):
            init._SCHEMA(id='https://example.test/missing')
        state.setattr(yaml.error, 'Mark', init.LINKML_MARK)
        state.setattr(init._SCHEMA, 'MissingRequiredField', rawloader.mrf, raising=False)
        assert init.phase() == 1
        assert catalog.runtime_token() is not token
        assert context.schema_data(selected, snapshot) == before
        assert context._entry is not old
        warm = context._entry
        assert context.schema_data(selected, snapshot) == before
        assert context._entry is warm
        assert str(init._SCHEMA(id='https://example.test/missing').name) == 'missing'


@pytest.mark.parametrize('raw', [b'a: 1\na: 2\n', b'a: *absent\n', b'[', b'- x\n',
                               b'a: !!python/object:unknown {}\n', b'a: .nan\n'])
def test_refusal_parity_no_retention(raw):
    def signature(native):
        try:
            om._mapping(raw, 'schema', _schema_events=True, _native_events=native)
        except Exception as exc:
            return type(exc), str(exc), type(exc.__cause__), str(exc.__cause__)
        pytest.fail('expected refusal')
    before = events.counters()['stored']
    assert signature(True) == signature(False)
    assert signature(True) == signature(False)
    assert events.counters()['stored'] == before


def test_fresh_mapping_and_constructor_on_event_hit(monkeypatch):
    raw = b'u3b_fresh: [one, two]\n'
    first = om._mapping(raw, 'schema', _native_events=True)
    before = events.counters()['hits']
    second = om._mapping(raw, 'schema', _native_events=True)
    assert events.counters()['hits'] > before
    second['u3b_fresh'].clear()
    assert first == om._mapping(raw, 'schema', _native_events=True)
    def reject(loader, node):
        raise ValueError('fresh constructor refusal')
    monkeypatch.setitem(om._UniqueLoader.yaml_constructors, 'tag:yaml.org,2002:seq', reject)
    with pytest.raises(ValueError):
        om._mapping(raw, 'schema', _native_events=True)


def test_exact_event_budget_and_overflow(monkeypatch):
    assert (events.MAX_ENTRIES, events.MAX_EVENTS_PER_ENTRY, events.MAX_TOTAL_EVENTS,
            events.MAX_EVENT_CHARS, events.MAX_PAYLOAD_BYTES, events.MAX_INPUT_BYTES) == (
                4, 131072, 262144, 8000000, 40000000, 8000000)
    raw = b'boundary: value\n'
    expected = om._mapping(raw, 'schema', _schema_events=True)
    _, candidate = events.load_native(raw.decode(), limit=om.MAX_INPUT_BYTES)
    assert candidate is not None
    for name, exact in [('MAX_EVENTS_PER_ENTRY', candidate.event_count),
                        ('MAX_TOTAL_EVENTS', candidate.event_count),
                        ('MAX_PAYLOAD_BYTES', candidate.payload_bytes),
                        ('MAX_EVENT_CHARS', len('boundaryvalue')),
                        ('MAX_INPUT_BYTES', len(raw))]:
        with monkeypatch.context() as patch:
            patch.setattr(events, name, exact)
            assert om._mapping(raw, 'schema', _native_events=True) == expected
            before = events.counters()['stored']
            patch.setattr(events, name, exact - 1)
            assert om._mapping(raw, 'schema', _native_events=True) == expected
            assert events.counters()['stored'] == before
    for n in range(8):
        om._mapping(f'unique_{n}: value\n'.encode(), 'schema', _native_events=True)
    counts = events.counters()
    assert counts['entries'] <= 4 and counts['events'] <= 262144 and counts['payload_bytes'] <= 40000000


def test_native_typed_capture_and_receipt_reconstruction_smoke(supplied):
    # One synthetic receipt -> typed record reconstruction, owner-thread CPU.
    # This is functional smoke only; no speedup or timing acceptance assertion.
    snapshot = typed._snapshot(typed._snapshot_rows(typed._capture(supplied['schema_path'])))
    assets = tuple((name, om._asset(name)) for name in om.ASSET_SHA256)
    cache = typed.DerivationCache()
    started = time.thread_time()
    packet = typed.prepare(**supplied, schema_snapshot=snapshot, captured_assets=assets, derivations=cache)
    assembled = roundtrip(packet, cache)
    checked = typed.check(assembled, captured_assets=assets, derivations=cache)
    cold = time.thread_time() - started
    started = time.thread_time()
    again = typed.prepare(**supplied, schema_snapshot=snapshot, captured_assets=assets, derivations=cache)
    repeated = roundtrip(again, cache)
    assert typed.check(repeated, captured_assets=assets, derivations=cache) == checked
    warm = time.thread_time() - started
    assert packet == again
    assert assembled == repeated
    out = Path(__file__).resolve().parents[2] / 'scratch-native-u3b/cpu-smoke.json'
    artifact = out.with_name('cpu-smoke-assembly.json')
    artifact.write_bytes(typed._json(assembled))
    assert artifact.stat().st_size
    assert typed.check(json.loads(artifact.read_bytes()), captured_assets=assets,
                       derivations=typed.DerivationCache())['passed']
    out.write_text(json.dumps({'scope': 'synthetic typed receipt-to-record preparation and reconstruction smoke; not timing evidence',
                               'cold_owner_thread_cpu_s': cold, 'warm_owner_thread_cpu_s': warm,
                               'independent_reconstruction_passed': True}, indent=2) + '\n')


def test_fresh_catalog_content_participates_in_native_derivation_identity(supplied):
    packet = typed.prepare(**supplied)
    snapshot = typed._snapshot(packet['schema_sources'])
    first = om._schema(snapshot.sources[0][1], schema_snapshot=snapshot, logical_paths=True)
    second = deepcopy(first)
    second['classes']['Dataset']['definition']['description'] = 'Changed current derivation'
    assets = tuple((name, om._asset(name)) for name in om.ASSET_SHA256)
    cache = typed.DerivationCache()
    products = [typed._derive(packet['inputs'], packet['schema_sources'], packet['project'], packet['limits'],
        derivations=cache, captured_assets=assets, _schema_reuse=typed._SchemaReuse(snapshot.sources, value))
        for value in (first, second)]
    assert products[0][0] != products[1][0]
    assert len(cache._rows) == 2


def test_api_and_native_derivations_share_one_budget(supplied):
    snapshot = typed._snapshot(typed._snapshot_rows(typed._capture(supplied['schema_path'])))
    assets = tuple((name, om._asset(name)) for name in om.ASSET_SHA256)
    cache = typed.DerivationCache(max_entries=1)
    typed.prepare(**supplied, derivations=cache)
    original = next(iter(cache._rows))
    typed.prepare(**supplied, schema_snapshot=snapshot, captured_assets=assets, derivations=cache)
    assert len(cache._rows) == 1 and original not in cache._rows
    assert cache._bytes == sum(map(len, cache._rows.values())) <= cache.max_bytes
    typed.prepare(**supplied, derivations=cache)
    assert len(cache._rows) == 1 and original in cache._rows


def test_owner_association_reuses_catalog_through_real_typed_prepare(declaration, supplied, monkeypatch):
    path = Path(declaration['inputs']['full_schema']['root'])
    raw = b'''id: https://example.org/full
name: full
prefixes: {xsd: 'http://www.w3.org/2001/XMLSchema#'}
types:
  string: {base: str, uri: 'xsd:string'}
classes:
  Dataset:
    attributes:
      name: {range: string}
      description: {range: string}
'''
    path.write_bytes(raw)
    declaration['inputs']['full_schema']['sources'] = [{'name': 'full', **pin(path, raw)}]
    save(declaration)
    selected = selection.capture(declaration['registration_path'])
    snapshot = receipts.schema_snapshot(selected)
    context = receipts._ReceiptCatalogContext()
    context.schema_data(selected, snapshot)
    lookup = catalog._CatalogLookup(context, selected)
    args = {**supplied, 'schema_path': path, 'schema_snapshot': snapshot,
            'captured_assets': tuple((name, om._asset(name)) for name in om.ASSET_SHA256)}
    expected = typed.prepare(**args)
    before = events.counters()['documents']
    actual = typed._prepare(**args, derivations=context.derivations(), _catalog_lookup=lookup)
    assert actual == expected and actual['plan']['workers']
    assert events.counters()['documents'] == before
    assert len(context.derivations()._rows) == 1
    monkeypatch.setattr(init, 'INITIALIZATION_ERROR', 'unknown current state')
    assert typed._prepare(**args, derivations=context.derivations(), _catalog_lookup=lookup) == expected
    assert events.counters()['documents'] > before
