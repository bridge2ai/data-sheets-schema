"""Pure JSON reuse preserves caller isolation, refusal order and finite storage."""
from concurrent.futures import ThreadPoolExecutor
import json
from types import MappingProxyType

import pytest

from data_sheets_schema import native_shared_contract as c


@pytest.fixture
def fresh(monkeypatch):
    cache = c._JSONValidationCache()
    monkeypatch.setattr(c, '_JSON_VALIDATION', cache)
    return cache


@pytest.mark.parametrize('raw', [
    b'null', b'true', b'-0.0', b'123456789012345678901234567890',
    b'{"a":[1,{"b":"escaped \\\" quote \\\\ slash"}],"z":false}',
    b'"\\ud83d\\ude00"', ' {"unicode":"α\u2028終"}\n'.encode(),
])
def test_real_decoder_returns_equal_values_for_cold_and_reused_bytes(fresh, raw):
    cold = c.strict_json(raw)
    expected = json.loads(raw)
    assert cold == expected
    for _ in range(3):
        assert c.strict_json(bytes(bytearray(raw)), 'another label') == expected
    assert fresh._bytes == len(raw) and len(fresh._entries) == 1


def test_success_reuses_only_validation_and_returns_private_nested_values(fresh, monkeypatch):
    calls = []
    original = c._lexical_budget
    def measured(text):
        calls.append(text)
        return original(text)
    monkeypatch.setattr(c, '_lexical_budget', measured)
    raw = b'{"nested":[{"x":[1,2]}]}'
    first = c.strict_json(raw)
    first['nested'][0]['x'].append('private mutation')
    second = c.strict_json(raw)
    assert second == {'nested': [{'x': [1, 2]}]}
    second.clear()
    assert c.strict_json(raw) == {'nested': [{'x': [1, 2]}]}
    assert len(calls) == 1


@pytest.mark.parametrize('raw,fragment', [
    (b'{"x":1,"x":2}', 'duplicate'),
    (b'{"x":NaN}', 'nonfinite'), (b'{"x":Infinity}', 'nonfinite'),
    (b'{"x":1e999}', 'nonfinite'), (b'"\\ud800"', 'canonical UTF-8'),
    (b'\xff', 'strict UTF-8'), (b'{"x":', 'strict UTF-8'),
    (b'[] trailing', 'strict UTF-8'),
])
def test_invalid_inputs_never_enter_success_cache(fresh, raw, fragment):
    for label in ('first', 'second'):
        with pytest.raises(ValueError, match=fragment):
            c.strict_json(raw, label)
    assert not fresh._entries and fresh._bytes == 0


def test_changed_structural_limits_require_new_validation(fresh, monkeypatch):
    raw = b'{"a":[[0]]}'
    assert c.strict_json(raw) == {'a': [[0]]}
    for key, value in (('json_yaml_depth', 2), ('json_yaml_nodes_per_document', 3)):
        with monkeypatch.context() as context:
            context.setattr(c, 'HARD_LIMITS', MappingProxyType({**c.HARD_LIMITS, key: value}))
            with pytest.raises(ValueError, match='structural bound'):
                c.strict_json(raw)
    assert c.strict_json(raw) == {'a': [[0]]}
    assert len(fresh._entries) == 1


def test_byte_bound_type_and_label_checks_precede_a_cache_hit(fresh):
    raw = b'{"a":1}'
    assert c.strict_json(raw, max_bytes=len(raw)) == {'a': 1}
    with pytest.raises(ValueError, match='later requires bounded nonempty immutable bytes'):
        c.strict_json(raw, 'later', max_bytes=len(raw) - 1)
    for bound in (True, 0, -1, 1.5):
        with pytest.raises(ValueError, match='JSON byte bound must be a positive integer'):
            c.strict_json(raw, 'later', max_bytes=bound)
    for invalid in (bytearray(raw), memoryview(raw), raw.decode(), b''):
        with pytest.raises(ValueError, match='later requires bounded nonempty immutable bytes'):
            c.strict_json(invalid, 'later')
    assert c.strict_json(raw, 'later') == {'a': 1}


@pytest.mark.parametrize('entries,byte_cap', [(2, 100), (100, 2)])
def test_lru_eviction_respects_count_and_exact_byte_bound(monkeypatch, entries, byte_cap):
    cache = c._JSONValidationCache(entries, byte_cap)
    monkeypatch.setattr(c, '_JSON_VALIDATION', cache)
    calls = []
    original = c._lexical_budget
    def measured(text):
        calls.append(text)
        return original(text)
    monkeypatch.setattr(c, '_lexical_budget', measured)
    for raw in (b'0', b'1', b'0', b'2', b'0'):
        assert c.strict_json(raw) == int(raw)
    assert calls == ['0', '1', '2']
    assert cache._bytes == 2 and len(cache._entries) == 2
    assert c.strict_json(b'1') == 1
    assert calls == ['0', '1', '2', '1']
    assert cache._bytes == 2 and len(cache._entries) == 2


def test_oversized_success_does_not_displace_reusable_small_inputs(monkeypatch):
    cache = c._JSONValidationCache(2, 2)
    monkeypatch.setattr(c, '_JSON_VALIDATION', cache)
    c.strict_json(b'0'); c.strict_json(b'1')
    keys = list(cache._entries)
    assert c.strict_json(b'[1,2,3]') == [1, 2, 3]
    assert list(cache._entries) == keys and cache._bytes == 2


def test_parallel_calls_keep_results_independent_and_storage_bounded(monkeypatch):
    cache = c._JSONValidationCache(8, 160)
    monkeypatch.setattr(c, '_JSON_VALIDATION', cache)
    def parse(number):
        expected = {'n': [number % 17]}
        raw = json.dumps(expected, separators=(',', ':')).encode()
        got = c.strict_json(raw)
        assert got == expected
        got['n'].append('caller mutation')
        assert c.strict_json(raw) == expected
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(parse, range(256)))
    assert len(cache._entries) <= 8 and cache._bytes <= 160
    assert cache._bytes == sum(len(key[0]) for key in cache._entries)
