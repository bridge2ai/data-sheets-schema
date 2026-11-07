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
    result = subprocess.run([sys.executable, str(root / 'tests/utils/native_u3b_no_libyaml_probe.py'),
        '--source', str(root), '--output', str(output)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    observed = json.loads(output.read_bytes())
    assert observed == json.loads(result.stdout)
    assert observed['import_error'] is None
    assert observed['default_binding_ready'] is False
    assert observed['blocked_extension_imports'] == 1


def test_lazy_initialization_and_within_state_refusal_parity():
    script = Path(__file__).resolve().parents[1] / 'tests/utils/native_u3b_lazy_probe.py'
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['within_state_parity'] is True


@pytest.fixture
def captured(declaration):
    path = Path(declaration['inputs']['full_schema']['root'])
    raw = b'''id: https://example.org/full
name: full
prefixes: {ex: 'https://example.org/', xsd: 'http://www.w3.org/2001/XMLSchema#'}
imports: [linkml:types]
enums:
  Status:
    permissible_values: {active: {}, archived: {}}
slots:
  name: {range: string, description: 'Display name'}
  status: {range: Status}
classes:
  Dataset:
    slots: [name, status]
    attributes:
      contributors: {range: Person, multivalued: true}
  Person:
    slots: [name]
'''
    path.write_bytes(raw)
    from data_sheets_schema.schema_snapshot import capture_schema
    snapshot = capture_schema(path, strict=True)
    declaration['inputs']['full_schema']['sources'] = [
        {'name': str(name), **pin(p, data)} for name, p, data in snapshot.sources]
    save(declaration)
    selected = selection.capture(declaration['registration_path'])
    return selected, receipts.schema_snapshot(selected)


def test_catalog_cold_warm_private_objects(captured):
    selected, snapshot = captured
    context = receipts._ReceiptCatalogContext()
    first = context.schema_data(selected, snapshot)
    assert ('https://example.org/', 'ex') in first[0]
    assert set(first[1]['classes']) >= {'Dataset', 'Person'}
    assert first[1]['classes']['Dataset'] != first[1]['classes']['Person']
    assert context._entry_marker is catalog.runtime_token() is not None
    stored = context._entry
    second = context.schema_data(selected, snapshot)
    assert first == second and first[1] is not second[1]
    assert context._entry is stored
    second[1]['classes'].clear()
    assert context.schema_data(selected, snapshot) == first


@pytest.mark.parametrize('mutation', ['parser', 'parser_code', 'loader', 'loader_class', 'events', 'characters'])
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
    elif mutation == 'loader_class':
        class RefusingLoader(om._SchemaEventLoader):
            get_event = refuse
        monkeypatch.setattr(om, '_SchemaEventLoader', RefusingLoader)
    else:
        monkeypatch.setattr(om, 'MAX_SCHEMA_EVENTS' if mutation == 'events' else 'MAX_SCHEMA_EVENT_CHARS', 0)
    assert catalog.runtime_token() is None
    assert context._typed_catalog(selected, snapshot.sources[0][1], snapshot) is None
    def original():
        bases, value = om._schema_with_root_bases(snapshot.sources[0][1], schema_snapshot=snapshot)
        return bases, json.loads(om._json(value))
    if mutation in ('parser', 'parser_code', 'loader', 'loader_class'):
        expected = error_signature(original)
        assert 'current schema-event refusal' in str(expected)
        assert error_signature(lambda: context.schema_data(selected, snapshot)) == expected
    else:
        expected = original()
        calls = []
        constructor = om._schema_with_root_bases
        def counted(*args, **kwargs):
            calls.append(1)
            return constructor(*args, **kwargs)
        monkeypatch.setattr(om, '_schema_with_root_bases', counted)
        assert context.schema_data(selected, snapshot) == expected
        assert calls == [1]


def error_signature(call):
    with pytest.raises(Exception) as caught:
        call()
    chain = []
    exc = caught.value
    while exc is not None:
        chain.append((type(exc), str(exc)))
        exc = exc.__cause__
    return chain


def test_empty_root_bases_ignore_imported_prefixes(declaration):
    from data_sheets_schema.schema_snapshot import capture_schema
    path = Path(declaration['inputs']['full_schema']['root'])
    imported = path.with_name('imported.yaml')
    imported.write_text('''id: https://example.org/imported
name: imported
prefixes: {ambient: 'https://ambient.example/'}
classes:
  Person:
    attributes:
      friend: {range: Person}
''')
    path.write_text('''id: https://example.org/full
name: full
prefixes: {}
imports: [imported]
classes:
  Dataset:
    attributes:
      creator: {range: Person}
''')
    snapshot = capture_schema(path, strict=True)
    declaration['inputs']['full_schema']['sources'] = [
        {'name': str(name), **pin(p, raw)} for name, p, raw in snapshot.sources]
    save(declaration)
    selected = selection.capture(declaration['registration_path'])
    snapshot = receipts.schema_snapshot(selected)
    assert len(snapshot.sources) > 1
    context = receipts._ReceiptCatalogContext()
    bases, value = context.schema_data(selected, snapshot)
    assert bases == ()
    assert set(value['classes']) >= {'Dataset', 'Person'}
    assert context.schema_data(selected, snapshot) == (bases, value)


def test_merged_schema_owner_cold_warm_bytes(declaration, monkeypatch):
    from data_sheets_schema import api_runner
    from data_sheets_schema.schema_snapshot import capture_schema
    path = Path(__file__).resolve().parents[1] / 'src/data_sheets_schema/schema/data_sheets_schema_all.yaml'
    monkeypatch.setattr(api_runner, 'FULL_SCHEMA_PATH', path)
    snapshot = capture_schema(path, strict=True)
    declaration['inputs']['full_schema']['root'] = str(path)
    declaration['inputs']['full_schema']['sources'] = [
        {'name': str(name), **pin(p, raw)} for name, p, raw in snapshot.sources]
    save(declaration)
    selected = selection.capture(declaration['registration_path'])
    snapshot = receipts.schema_snapshot(selected)
    expected = om._json(om._schema(path, schema_snapshot=snapshot, logical_paths=True))
    context = receipts._ReceiptCatalogContext()
    cold = context.schema_data(selected, snapshot)
    entry = context._entry
    warm = context.schema_data(selected, snapshot)
    assert context._entry is entry and context._entry_marker is not None
    assert cold[0] == warm[0] and len(cold[0]) > 1
    assert om._json(cold[1]) == om._json(warm[1]) == expected


def test_metamodel_callback_override_disables_warm_reuse(captured, monkeypatch):
    selected, snapshot = captured
    context = receipts._ReceiptCatalogContext()
    context.schema_data(selected, snapshot)
    monkeypatch.setattr(init.meta.SlotDefinition, 'MissingRequiredField',
                        lambda *args: None, raising=False)
    with pytest.raises(TypeError, match='metamodel callback ownership'):
        init.phase()
    assert catalog.runtime_token() is None
    assert context._typed_catalog(selected, snapshot.sources[0][1], snapshot) is None
    assert context._entry is None


def test_event_fields_match_live_pyyaml_and_unknown_field_falls_back(monkeypatch):
    raw = b'%TAG !e! tag:example.org,2000:\n---\nfield_guard: &a [one, two]\nagain: *a\n...\n'
    seen = set()
    for event in yaml.parse(raw.decode(), Loader=yaml.SafeLoader):
        seen.add(type(event).__name__)
        assert set(vars(event)) == set(events._EVENT_FIELDS[type(event).__name__]) | {'start_mark', 'end_mark'}
    assert seen == set(events._EVENT_FIELDS)
    # Alter the retained schema rather than the parser binding so capture itself
    # must reject the mismatch and use the original fresh constructor.
    monkeypatch.setitem(events._EVENT_FIELDS, 'ScalarEvent', ('anchor', 'tag', 'implicit', 'value'))
    value, candidate = events.load_native(raw.decode(), limit=om.MAX_INPUT_BYTES)
    assert value == om._mapping(raw, 'schema', _schema_events=True)
    assert candidate is None


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
            key = raw, events._token(om.MAX_INPUT_BYTES)
            assert key in events._CACHE
            before = events.counters()['stored']
            patch.setattr(events, name, exact - 1)
            assert om._mapping(raw, 'schema', _native_events=True) == expected
            assert events.counters()['stored'] == before
    for n in range(8):
        om._mapping(f'unique_{n}: value\n'.encode(), 'schema', _native_events=True)
    counts = events.counters()
    assert counts['entries'] <= 4 and counts['events'] <= 262144 and counts['payload_bytes'] <= 40000000


@pytest.mark.parametrize('raw', [
    b'%TAG !e! tag:example.com,2000:\n---\na: &x [1, 2.5, true, null, 2001-12-14]\nb: *x\nc: !!str 3\nd: !!binary aGk=\n...\n',
    b'a: \xff\xfe\n',
    b'a: ' + b'[' * 70 + b']' * 70 + b'\n',
    b'a: &x 1\nb: &x 2\nc: ' + b'[' * 70 + b']' * 70 + b'\n',
    b'a: &x 1\nb: &x 2\n', b'a:\n  b: 1\n  b: 2\n',
    b'base: &b {x: 1}\nderived:\n  <<: *b\n  y: 2\n',
    b'a: 1\n---\nb: 2\n', b'a: 1\n---\nb: [\n', b'a: \x07\n',
    ('a: [' + ','.join(['1'] * 200_001) + ']\n').encode(),
], ids=['tags-anchors', 'utf8', 'depth', 'depth-precedence', 'duplicate-anchor', 'nested-key',
        'merge-key', 'documents', 'second-parse', 'nonprintable', 'nodes'])
def test_review_probe_ordinary_event_native_refusal_parity(raw):
    ordinary = error_signature(lambda: om._mapping(raw, 'schema'))
    assert error_signature(lambda: om._mapping(raw, 'schema', _schema_events=True)) == ordinary
    before = events.counters()['stored']
    for _ in range(2):
        assert error_signature(lambda: om._mapping(raw, 'schema', _native_events=True)) == ordinary
    assert events.counters()['stored'] == before


def test_review_probe_bom_and_input_size_parity():
    raw = b'\xef\xbb\xbfa: 1\n'
    expected = om._mapping(raw, 'schema')
    assert expected == {'a': 1}
    for options in ({'_schema_events': True}, {'_native_events': True}, {'_native_events': True}):
        assert om._mapping(raw, 'schema', **options) == expected
    ordinary = error_signature(lambda: om._mapping(raw, 'schema', limit=len(raw) - 1))
    for options in ({'_schema_events': True}, {'_native_events': True}):
        assert error_signature(lambda: om._mapping(raw, 'schema', limit=len(raw) - 1, **options)) == ordinary


def test_native_typed_capture_and_receipt_reconstruction_smoke(supplied, declaration, tmp_path):
    # One synthetic receipt -> typed record reconstruction, owner-thread CPU.
    # This is functional smoke only; no speedup or timing acceptance assertion.
    path = Path(declaration['inputs']['full_schema']['root'])
    raw = b'''id: https://example.org/full
name: full
prefixes: {linkml: 'https://w3id.org/linkml/'}
imports: [linkml:types]
default_range: string
classes:
  Dataset:
    attributes:
      name: {}
      description: {}
      issued: {range: date}
'''
    path.write_bytes(raw)
    from data_sheets_schema.schema_snapshot import capture_schema
    snapshot = capture_schema(path, strict=True)
    declaration['inputs']['full_schema']['sources'] = [
        {'name': str(name), **pin(p, data)} for name, p, data in snapshot.sources]
    save(declaration)
    selected = selection.capture(declaration['registration_path'])
    snapshot = receipts.schema_snapshot(selected)
    context = receipts._ReceiptCatalogContext()
    lookup = catalog._CatalogLookup(context, selected)
    supplied = {**supplied, 'schema_path': path}
    assets = tuple((name, om._asset(name)) for name in om.ASSET_SHA256)
    cache = context.derivations()
    options = {'captured_assets': assets, 'derivations': cache, '_catalog_lookup': lookup}
    def native_roundtrip(packet):
        from data_sheets_schema import audit_batches as batches
        workers, omission, delta, _ = replies(packet, 2)
        saved = {key: typed.capture_response(typed.worker_request(packet, key, **options), response)
                 for key, response in workers.items()}
        raw_omission = batches.canonical_bytes(omission)
        index = typed.index(packet, saved, raw_omission, **options)
        return typed.assemble(packet, saved, raw_omission,
            typed.capture_response(index, batches.canonical_bytes(delta)), **options)
    started = time.thread_time()
    context.schema_data(selected, snapshot)
    assert context._typed_catalog(selected, path, snapshot) is not None
    packet = typed._prepare(**supplied, schema_snapshot=snapshot, **options)
    assembled = native_roundtrip(packet)
    checked = typed.check(assembled, **options)
    cold = time.thread_time() - started
    started = time.thread_time()
    context.schema_data(selected, snapshot)
    again = typed._prepare(**supplied, schema_snapshot=snapshot, **options)
    repeated = native_roundtrip(again)
    assert typed.check(repeated, **options) == checked
    warm = time.thread_time() - started
    assert packet == again
    assert assembled == repeated
    out = tmp_path / 'cpu-smoke.json'
    artifact = out.with_name('cpu-smoke-assembly.json')
    artifact.write_bytes(typed._json(assembled))
    assert artifact.stat().st_size
    assert typed.check(json.loads(artifact.read_bytes()), captured_assets=assets,
                       derivations=typed.DerivationCache())['passed']
    out.write_text(json.dumps({'scope': 'owner-context synthetic typed receipt-to-record preparation and reconstruction smoke; not timing evidence',
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
