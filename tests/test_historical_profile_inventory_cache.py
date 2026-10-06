"""Repeated historical checks reuse pure work without retaining authority."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

import pytest

from data_sheets_schema import profile_identity as identity
from data_sheets_schema import profiles, run_schema, schema_digest, schema_view
from tests.test_historical_profile_identity import SCHEMA, VOCABULARY


@pytest.fixture(autouse=True)
def empty_cache():
    schema_view.version_document(b'name: initialize\n')
    previous_profile = sys.getprofile()
    identity._inventory_cache_clear()
    yield
    sys.setprofile(previous_profile)
    identity._inventory_cache_clear()


@pytest.fixture
def case(tmp_path, monkeypatch):
    raw = SCHEMA.replace(b'imports: [linkml:types]\n', b'')
    path = tmp_path / 'historical.yaml'
    path.write_bytes(raw)
    pin = tmp_path / 'vocabulary.yaml'
    pin.write_bytes(VOCABULARY)
    monkeypatch.setattr(schema_digest, 'VOCABULARY_PIN', pin)
    digest = schema_digest.fingerprint(schema_digest.digest_text(
        'Dataset', schema_path=path, profile=profiles.NEUTRAL))
    record = {'schema': {'full_path': str(path), 'full_sha256': hashlib.sha256(raw).hexdigest(),
                         'full_md5': hashlib.md5(raw).hexdigest(), 'profile': 'neutral',
                         'digest_md5': digest}}
    return record, path, pin


def _replace(record, path, raw):
    path.write_bytes(raw)
    record['schema'].update(full_path=str(path), full_sha256=hashlib.sha256(raw).hexdigest(),
                            full_md5=hashlib.md5(raw).hexdigest())


def _count_builds(monkeypatch):
    calls = []
    code = schema_digest._build_from_view.__code__
    def observe(frame, event, _arg):
        if event == 'call' and frame.f_code is code:
            calls.append(1)
    sys.setprofile(observe)
    return calls


def test_same_inventory_keeps_every_authority_and_judgement_fresh(case, monkeypatch):
    record, _, pin = case
    calls = _count_builds(monkeypatch)
    resolve, read, render = run_schema.run_schema_bytes, Path.read_bytes, schema_digest.render
    activity = {'resolve': 0, 'vocabulary': 0, 'render': 0}

    def resolving(*args, **kwargs):
        activity['resolve'] += 1
        return resolve(*args, **kwargs)

    def reading(path):
        if path == pin:
            activity['vocabulary'] += 1
        return read(path)

    def rendering(*args, **kwargs):
        activity['render'] += 1
        return render(*args, **kwargs)

    monkeypatch.setattr(run_schema, 'run_schema_bytes', resolving)
    monkeypatch.setattr(Path, 'read_bytes', reading)
    monkeypatch.setattr(schema_digest, 'render', rendering)
    first = identity.capture(record)
    assert first['status'] == 'match'
    record['schema']['digest_md5'] = '0' * 32
    first['candidate_digests'].clear()
    second = identity.capture(record)
    assert second['status'] == 'unknown' and second['candidate_digests']
    assert len(calls) == 1
    assert activity == {'resolve': 2, 'vocabulary': 2, 'render': 4}


@pytest.mark.parametrize('change', ['raw', 'path', 'builder', 'runtime', 'renderer_source'])
def test_inventory_input_changes_invalidate(case, monkeypatch, tmp_path, change):
    record, path, _ = case
    calls = _count_builds(monkeypatch)
    assert identity.capture(record)['status'] == 'match'
    if change == 'raw':
        _replace(record, path, path.read_bytes().replace(b'topic:', b'other:'))
    elif change == 'path':
        _replace(record, tmp_path / 'other.yaml', path.read_bytes())
    elif change == 'builder':
        original = schema_digest._build_from_view
        monkeypatch.setattr(schema_digest, '_build_from_view', lambda *a, **kw: original(*a, **kw))
    elif change == 'runtime':
        monkeypatch.setattr(identity, 'version', lambda _: 'different-runtime')
    else:
        source = tmp_path / 'renderer.py'
        source.write_bytes(Path(schema_digest.__file__).read_bytes() + b'\n# distinct source identity\n')
        monkeypatch.setattr(schema_digest, '__file__', str(source))
    identity.capture(record)
    assert len(calls) == 2


@pytest.mark.parametrize('name,value', [
    ('CLASS_SCHEMA', {'Dataset': Path('elsewhere/historical.yaml')}),
    ('MAX_ENUM_VALUES', 1), ('NESTING_DEPTH', 0),
    ('UNIVERSAL_ATTRIBUTES', frozenset({'topic'})),
    ('TERM_SOURCES_ANNOTATION', 'example:source'),
    ('TERM_SOURCES', {('Dataset', 'topic'): 'Different source'}),
])
def test_effective_builder_settings_are_keyed(case, monkeypatch, name, value):
    record, _, _ = case
    calls = _count_builds(monkeypatch)
    identity.capture(record)
    monkeypatch.setattr(schema_digest, name, value)
    identity.capture(record)
    assert len(calls) == 2


def test_in_place_term_source_edit_is_seen(case, monkeypatch):
    record, _, _ = case
    calls = _count_builds(monkeypatch)
    identity.capture(record)
    monkeypatch.setitem(schema_digest.TERM_SOURCES, ('Dataset', 'topic'), 'New source')
    result = identity.capture(record)
    assert len(calls) == 2
    assert result['status'] == 'unknown'


@pytest.mark.parametrize('function,attribute,value', [
    ('_truncate', '__defaults__', (1,)),
    ('_build_from_view', '__kwdefaults__', {'complete': True}),
])
def test_effective_function_defaults_are_keyed(case, monkeypatch, function, attribute, value):
    record, _, _ = case
    identity.capture(record)
    before = identity._inventory_cache_info()['entries']
    monkeypatch.setattr(getattr(schema_digest, function), attribute, value)
    actual = identity.capture(record)
    assert identity._inventory_cache_info()['entries'] == before
    identity._inventory_cache_clear()
    assert identity.capture(record) == actual


def test_stateful_replacement_builder_never_retains_first_observed_state(case, monkeypatch):
    record, _, _ = case
    original, state = schema_digest._build_from_view, {'change': False}
    def builder(*args, **kwargs):
        inventory = original(*args, **kwargs)
        if state['change']:
            inventory.slots[0].description = 'Changed closed-over builder state'
        return inventory
    monkeypatch.setattr(schema_digest, '_build_from_view', builder)
    assert identity.capture(record)['status'] == 'match'
    state['change'] = True
    actual = identity.capture(record)
    assert actual['status'] == 'unknown' and identity._inventory_cache_info()['entries'] == 0
    identity._inventory_cache_clear()
    assert identity.capture(record) == actual


_GLOBAL_BUILDER_STATE = {}


def _global_builder(*args, **kwargs):
    inventory = _GLOBAL_BUILDER_STATE['original'](*args, **kwargs)
    if _GLOBAL_BUILDER_STATE['change']:
        inventory.slots[0].description = 'Changed module-global builder state'
    return inventory


@pytest.mark.parametrize('warm_original', [False, True])
def test_global_reading_builder_bypasses_before_and_after_warming(case, monkeypatch, warm_original):
    record, _, _ = case
    if warm_original:
        assert identity.capture(record)['status'] == 'match'
    retained = identity._inventory_cache_info()['entries']
    monkeypatch.setitem(_GLOBAL_BUILDER_STATE, 'original', schema_digest._build_from_view)
    monkeypatch.setitem(_GLOBAL_BUILDER_STATE, 'change', False)
    assert _global_builder.__closure__ is None
    monkeypatch.setattr(schema_digest, '_build_from_view', _global_builder)
    assert identity.capture(record)['status'] == 'match'
    _GLOBAL_BUILDER_STATE['change'] = True
    actual = identity.capture(record)
    assert actual['status'] == 'unknown' and identity._inventory_cache_info()['entries'] == retained
    identity._inventory_cache_clear()
    assert identity.capture(record) == actual


def test_runtime_view_method_replacement_is_fresh_with_identical_source_file(case, monkeypatch):
    record, _, _ = case
    assert identity.capture(record)['status'] == 'match'
    descriptor = schema_view._ReleasableView.class_induced_slots
    original, state = descriptor.function, {'change': False}
    def induced(self, *args, **kwargs):
        slots = original(self, *args, **kwargs)
        if state['change']:
            for slot in slots:
                slot.description = 'Changed effective view method'
        return slots
    monkeypatch.setattr(descriptor, 'function', induced)
    assert identity.capture(record)['status'] == 'match'
    state['change'] = True
    actual = identity.capture(record)
    assert actual['status'] == 'unknown'
    identity._inventory_cache_clear()
    assert identity.capture(record) == actual


@pytest.mark.parametrize('changed', [None, b'vocabularies: false\n',
    VOCABULARY.replace(b'Synthetic topic', b'Different topic')])
def test_warm_inventory_does_not_attest_vocabulary(case, monkeypatch, changed):
    record, _, pin = case
    calls = _count_builds(monkeypatch)
    first = identity.capture(record)
    if changed is None:
        pin.unlink()
    else:
        pin.write_bytes(changed)
    second = identity.capture(record)
    assert len(calls) == 1
    if changed is None or b'false' in changed:
        assert second['status'] == 'unknown'
        assert 'vocabulary' in second['reason'].lower() or 'FileNotFoundError' in second['reason']
    else:
        assert second['candidate_digests']['bridge2ai'] != first['candidate_digests']['bridge2ai']
        assert second['vocabularies']['bridge2ai']['sha256'] == hashlib.sha256(changed).hexdigest()


@pytest.mark.parametrize('failure', ['missing', 'different_bytes', 'second_hash', 'runtime_missing'])
def test_warm_inventory_does_not_attest_schema_or_runtime(case, monkeypatch, failure):
    record, _, _ = case
    assert identity.capture(record)['status'] == 'match'
    if failure == 'missing':
        monkeypatch.setattr(run_schema, 'run_schema_bytes', lambda _: (None, {'reason': 'gone'}))
    elif failure == 'different_bytes':
        monkeypatch.setattr(run_schema, 'run_schema_bytes', lambda _: (b'different', {}))
    elif failure == 'second_hash':
        record['schema']['full_md5'] = '0' * 32
    else:
        def unavailable(_):
            raise ModuleNotFoundError('renderer dependency unavailable')
        monkeypatch.setattr(identity, 'version', unavailable)
    assert identity.capture(record)['status'] == 'unknown'


def test_renderer_mutation_cannot_poison_stored_inventory(case, monkeypatch):
    record, _, _ = case
    calls = _count_builds(monkeypatch)
    render = schema_digest.render

    def mutating(inventory, **kwargs):
        inventory.slots[0].name = 'mutated'
        return render(inventory, **kwargs)

    monkeypatch.setattr(schema_digest, 'render', mutating)
    assert identity.capture(record)['status'] == 'unknown'
    monkeypatch.setattr(schema_digest, 'render', render)
    assert identity.capture(record)['status'] == 'match'
    assert len(calls) == 1


def test_same_class_with_replaced_initializer_rebuilds(case, monkeypatch):
    record, _, _ = case
    calls = _count_builds(monkeypatch)
    assert identity.capture(record)['status'] == 'match'
    constructor = schema_digest.SlotDigest
    original = constructor.__init__

    def changed(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.description = 'Changed effective constructor'

    monkeypatch.setattr(constructor, '__init__', changed)
    result = identity.capture(record)
    assert schema_digest.SlotDigest is constructor
    assert result['status'] == 'unknown'
    assert len(calls) == 2


def test_replaced_new_method_invalidates_same_class(case, monkeypatch):
    record, _, _ = case
    # Use an owned class with an explicit allocator. Restoring object.__new__
    # after mutating a shared class can leave CPython's type slot changed.
    class LocalSlot(schema_digest.SlotDigest):
        def __new__(cls, *args, **kwargs):
            return object.__new__(cls)

    monkeypatch.setattr(schema_digest, 'SlotDigest', LocalSlot)
    calls = _count_builds(monkeypatch)
    assert identity.capture(record)['status'] == 'match'

    def changed(cls, *args, **kwargs):
        return object.__new__(cls)

    monkeypatch.setattr(LocalSlot, '__new__', staticmethod(changed))
    assert identity.capture(record)['status'] == 'match'
    assert len(calls) == 2


def test_effective_schema_post_init_rebuilds(case, monkeypatch):
    record, _, _ = case
    calls = _count_builds(monkeypatch)
    assert identity.capture(record)['status'] == 'match'
    original = schema_view.SchemaDefinition.__post_init__

    def changed(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.classes['Dataset'].attributes['topic'].description = 'Changed schema normalization'

    monkeypatch.setattr(schema_view.SchemaDefinition, '__post_init__', changed)
    assert identity.capture(record)['status'] == 'unknown'
    assert len(calls) == 2


def test_same_initializer_with_changed_defaults_is_keyed(case, monkeypatch):
    record, _, _ = case
    assert identity.capture(record)['status'] == 'match'
    initializer = schema_digest.SlotDigest.__init__
    before = identity._inventory_cache_info()['entries']
    monkeypatch.setattr(initializer, '__defaults__', (True,) + initializer.__defaults__[1:])
    actual = identity.capture(record)
    assert identity._inventory_cache_info()['entries'] == before
    identity._inventory_cache_clear()
    assert identity.capture(record) == actual


def test_imported_schema_bypasses_retention(case, monkeypatch):
    record, path, _ = case
    _replace(record, path, SCHEMA)
    calls = _count_builds(monkeypatch)
    first = identity.capture(record)
    second = identity.capture(record)
    assert first['candidate_digests'] == second['candidate_digests']
    assert len(calls) == 2 and identity._inventory_cache_info()['entries'] == 0


def test_invalid_inventory_is_never_cached(case, monkeypatch):
    record, path, _ = case
    _replace(record, path, b'name: invalid\n')
    for _ in range(2):
        assert identity.capture(record)['status'] == 'unknown'
        assert identity._inventory_cache_info()['entries'] == 0


def test_lru_entry_limit_and_clear(case, monkeypatch, tmp_path):
    record, path, _ = case
    raw = path.read_bytes()
    calls = _count_builds(monkeypatch)
    monkeypatch.setattr(identity, '_INVENTORY_CACHE_MAX_ENTRIES', 2)
    records = []
    for name in ('a.yaml', 'b.yaml', 'c.yaml'):
        item = deepcopy(record)
        _replace(item, tmp_path / name, raw)
        records.append(item)
    for i in (0, 1, 0, 2, 0, 1):
        identity.capture(records[i])
        assert identity._inventory_cache_info()['entries'] <= 2
    assert len(calls) == 4
    identity._inventory_cache_clear()
    assert identity._inventory_cache_info()['entries'] == 0
    assert identity._inventory_cache_info()['bytes'] == 0


def test_exact_byte_bound_oversize_and_lowered_limits(case, monkeypatch):
    record, _, _ = case
    calls = _count_builds(monkeypatch)
    identity.capture(record)
    weight = identity._inventory_cache_info()['bytes']
    assert weight > len(SCHEMA)
    identity._inventory_cache_clear()
    monkeypatch.setattr(identity, '_INVENTORY_CACHE_MAX_BYTES', weight)
    identity.capture(record)
    assert identity._inventory_cache_info()['bytes'] == weight
    monkeypatch.setattr(identity, '_INVENTORY_CACHE_MAX_BYTES', weight - 1)
    for _ in range(2):
        assert identity.capture(record)['status'] == 'match'
        assert identity._inventory_cache_info()['entries'] == 0
        assert identity._inventory_cache_info()['bytes'] == 0
    assert len(calls) == 4


def test_byte_budget_evicts_older_inventory(case, monkeypatch):
    record, path, _ = case
    raw = path.read_bytes()
    calls = _count_builds(monkeypatch)
    identity.capture(record)
    weight = identity._inventory_cache_info()['bytes']
    monkeypatch.setattr(identity, '_INVENTORY_CACHE_MAX_BYTES', weight + 256)
    _replace(record, path, raw.replace(b'topic:', b'other:'))
    identity.capture(record)
    assert identity._inventory_cache_info()['entries'] == 1
    assert identity._inventory_cache_info()['bytes'] <= weight + 256
    _replace(record, path, raw)
    identity.capture(record)
    assert len(calls) == 3
