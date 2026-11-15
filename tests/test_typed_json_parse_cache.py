"""Pure bounded JSON reuse: identity, isolation, refusals and retention bounds."""
import pytest
import sys

from data_sheets_schema import typed_audit as ta


def test_hit_is_fresh_and_equal(monkeypatch):
    cache = ta._JSONParseCache(4, 100_000)
    raw = b'{"nested":[{"value":1}]}'
    calls = []
    original = ta.omissions._mapping
    def parse(*args, **kwargs):
        calls.append(args[0])
        return original(*args, **kwargs)
    monkeypatch.setattr(ta.omissions, '_mapping', parse)
    first = cache.parse(raw, 'first', 1000, ('parser', 64, 200000, 0))
    first['nested'][0]['value'] = 9
    second = cache.parse(raw, 'second', 1000, ('parser', 64, 200000, 0))
    assert second == original(raw, 'fresh', json_only=True, limit=1000)
    assert second is not first and second['nested'] is not first['nested']
    second['nested'].append({'value': 10})
    assert cache.parse(raw, 'third', 1000, ('parser', 64, 200000, 0)) == {'nested': [{'value': 1}]}
    assert calls == [raw]


def test_every_identity_component_misses(monkeypatch):
    cache = ta._JSONParseCache(20, 100_000)
    calls = []
    original = ta.omissions._mapping
    def parse(*args, **kwargs):
        calls.append(args[0])
        return original(*args, **kwargs)
    monkeypatch.setattr(ta.omissions, '_mapping', parse)
    identity = ('digest', 64, 200000, 0)
    raw = b'{"a":1}'
    cache.parse(raw, 'x', 1000, identity)
    cache.parse(b'{"a":2}', 'x', 1000, identity)
    cache.parse(raw, 'x', 1001, identity)
    for index, replacement in enumerate(('changed-digest', 63, 199999, 1)):
        changed = list(identity)
        changed[index] = replacement
        cache.parse(raw, 'x', 1000, tuple(changed))
    assert len(calls) == 7


def test_refusals_reparse_and_do_not_retain(monkeypatch):
    cache = ta._JSONParseCache(4, 100_000)
    original = ta.omissions._mapping
    calls = []
    def parse(*args, **kwargs):
        calls.append(args[0])
        return original(*args, **kwargs)
    monkeypatch.setattr(ta.omissions, '_mapping', parse)
    for raw in (b'{"a":1,"a":2}', b'{', b'[]', b'{"a":NaN}'):
        for label in ('first', 'second'):
            with pytest.raises(ValueError, match=label):
                cache.parse(raw, label, 1000, ('parser',))
    assert len(calls) == 8
    assert not cache._entries and cache._bytes == 0


def test_bounds_and_oversize_bypass():
    cache = ta._JSONParseCache(2, 100_000)
    for raw in (b'{"a":1}', b'{"b":2}', b'{"c":3}'):
        cache.parse(raw, 'x', 1000, ('parser',))
    assert len(cache._entries) == 2
    assert cache._bytes <= cache._max_bytes
    size = cache._bytes
    small = ta._JSONParseCache(10, size // 2)
    for raw in (b'{"a":1}', b'{"b":2}', b'{"c":3}'):
        small.parse(raw, 'x', 1000, ('parser',))
    assert len(small._entries) <= 1 and small._bytes <= small._max_bytes
    tiny = ta._JSONParseCache(1, 1)
    assert tiny.parse(b'{"a":1}', 'x', 1000, ('parser',)) == {'a': 1}
    assert not tiny._entries


def test_byte_limit_checked_even_after_hit():
    cache = ta._JSONParseCache(4, 100_000)
    raw = b'{"a":1}'
    cache.parse(raw, 'x', 1000, ('parser',))
    with pytest.raises(ValueError):
        cache.parse(raw, 'x', 1, ('parser',))


def test_live_depth_and_node_limits_are_not_reused(monkeypatch):
    from data_sheets_schema import native_catalog_reuse
    assert native_catalog_reuse.runtime_token() is not None
    raw = b'{"a":[[1,2,3]]}'
    assert ta._bounded_json(raw, 'valid', 1000) == {'a': [[1, 2, 3]]}
    monkeypatch.setattr(ta.omissions, 'MAX_DEPTH', 1)
    with pytest.raises(ValueError):
        ta._bounded_json(raw, 'deep', 1000)
    monkeypatch.setattr(ta.omissions, 'MAX_DEPTH', 64)
    monkeypatch.setattr(ta.omissions, 'MAX_NODES', 2)
    with pytest.raises(ValueError):
        ta._bounded_json(raw, 'nodes', 1000)


def test_changed_parser_binding_bypasses_cache(monkeypatch):
    from data_sheets_schema import native_catalog_reuse
    assert native_catalog_reuse.runtime_token() is not None
    raw = b'{"a":1}'
    ta._bounded_json(raw, 'first', 1000)
    def refuse(raw):
        raise ValueError('replacement parser refusal')
    monkeypatch.setattr(ta.evidence, 'load_json', refuse)
    with pytest.raises(ValueError):
        ta._bounded_json(raw, 'changed', 1000)


def test_source_digest_change_misses(monkeypatch):
    from data_sheets_schema import native_catalog_reuse
    assert native_catalog_reuse.runtime_token() is not None
    cache = ta._JSONParseCache(4, 100_000)
    monkeypatch.setattr(ta, '_JSON_PARSE_CACHE', cache)
    raw = b'{"a":1}'
    ta._bounded_json(raw, 'first', 1000)
    ta._bounded_json(raw, 'hit', 1000)
    assert cache.hits == 1
    monkeypatch.setattr(ta, '_JSON_PARSER_SOURCE_SHA256', 'changed-source')
    ta._bounded_json(raw, 'changed', 1000)
    assert cache.hits == 1 and len(cache._entries) == 2


def test_digest_collision_still_compares_exact_bytes(monkeypatch):
    cache = ta._JSONParseCache(4, 100_000)
    monkeypatch.setattr(ta, '_sha', lambda raw: 'collision')
    assert cache.parse(b'{"a":1}', 'x', 1000, ('parser',)) == {'a': 1}
    assert cache.parse(b'{"a":2}', 'x', 1000, ('parser',)) == {'a': 2}
    assert cache.hits == 0
    assert len(cache._entries) == 1 and cache._bytes <= cache._max_bytes


def test_replaced_copy_alias_disables_shared_values(monkeypatch):
    from data_sheets_schema import native_catalog_reuse
    assert native_catalog_reuse.runtime_token() is not None
    raw = b'{"a":[1]}'
    ta._bounded_json(raw, 'first', 1000)
    monkeypatch.setattr(ta, 'deepcopy', lambda value: value)
    assert ta._parse_identity() is None
    changed = ta._bounded_json(raw, 'changed-copy', 1000)
    changed['a'].append(2)
    assert ta._bounded_json(raw, 'fresh', 1000) == {'a': [1]}


def test_interpreter_integer_limit_change_refuses_a_warm_value():
    if not hasattr(sys, 'get_int_max_str_digits'):
        pytest.skip('this interpreter has no integer-string limit')
    from data_sheets_schema import native_catalog_reuse
    assert native_catalog_reuse.runtime_token() is not None
    before = sys.get_int_max_str_digits()
    raw = b'{"number":' + b'1' * 1000 + b'}'
    try:
        sys.set_int_max_str_digits(4300)
        ta._bounded_json(raw, 'warm', 2000)
        sys.set_int_max_str_digits(640)
        with pytest.raises(ValueError):
            ta._bounded_json(raw, 'limited', 2000)
    finally:
        sys.set_int_max_str_digits(before)


def test_interpreter_recursion_limit_is_part_of_identity():
    from data_sheets_schema import native_catalog_reuse
    assert native_catalog_reuse.runtime_token() is not None
    before = sys.getrecursionlimit()
    identity = ta._parse_identity()
    assert identity is not None
    try:
        sys.setrecursionlimit(before + 100)
        assert ta._parse_identity() != identity
    finally:
        sys.setrecursionlimit(before)
