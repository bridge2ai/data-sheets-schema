"""Issue 6260: phase-specific guard plans and immediate dependency refusal."""
import sys
import types
import subprocess
from pathlib import Path

import pytest

from data_sheets_schema import native_catalog_reuse as catalog
from data_sheets_schema import native_catalog_initialization as initialization
from tests.test_typed_audit import supplied, packet


def set_phase(monkeypatch, phase):
    import linkml.utils.rawloader as rawloader
    monkeypatch.setattr(catalog, '_FAST_PLANS', {})
    if phase:
        monkeypatch.setattr(catalog.yaml.error, 'Mark', initialization.LINKML_MARK)
        monkeypatch.setattr(initialization._SCHEMA, 'MissingRequiredField', rawloader.mrf, raising=False)
    else:
        monkeypatch.setattr(catalog.yaml.error, 'Mark', initialization.ORIGINAL_MARK)
        if 'MissingRequiredField' in vars(initialization._SCHEMA):
            monkeypatch.delattr(initialization._SCHEMA, 'MissingRequiredField')
    assert initialization.phase() == phase
    marker = catalog.runtime_token()
    assert marker is initialization.marker()
    assert any(catalog._guards_match(plan) for plan in catalog._FAST_PLANS[marker].values())
    return marker


def test_warm_phase_never_reconstructs_state(monkeypatch, phase):
    marker = set_phase(monkeypatch, phase)
    def unexpected():
        raise AssertionError('warm guard reconstructed full state')
    monkeypatch.setattr(catalog, '_state', unexpected)
    for _ in range(3):
        assert catalog.runtime_token() is marker


test_warm_phase_never_reconstructs_state = pytest.mark.parametrize('phase', [0, 1])(
    test_warm_phase_never_reconstructs_state)


def test_each_guard_refuses_and_uses_full_fallback(monkeypatch, phase, mutation):
    set_phase(monkeypatch, phase)
    original = catalog._state
    calls = []
    def counted():
        calls.append(1)
        return original()
    monkeypatch.setattr(catalog, '_state', counted)
    def replacement(*args, **kwargs):
        return None
    if mutation == 'meta':
        monkeypatch.setattr(catalog.meta.SlotDefinition, '__post_init__', replacement)
    elif mutation == 'meta_attribute':
        monkeypatch.setattr(catalog.meta.SlotDefinition, 'range', 'changed')
    elif mutation == 'slotnames':
        monkeypatch.setattr(catalog.meta.SlotDefinition, '__slotnames__', ['injected'], raising=False)
    elif mutation == 'loader':
        monkeypatch.setitem(catalog.yaml.SafeLoader.yaml_constructors, 'tag:yaml.org,2002:str', replacement)
    elif mutation == 'copy':
        monkeypatch.setitem(catalog.copy.dispatch_table, catalog.meta.SlotDefinition, replacement)
    elif mutation == 'synapse_json_default':
        # The SDK replaces this serializer entry point globally; that must
        # never acquire the native schema producer's reuse identity.
        monkeypatch.setattr(catalog.json.JSONEncoder, 'default', replacement)
    elif mutation == 'code':
        monkeypatch.setattr(catalog.omissions._sha, '__code__', replacement.__code__)
    elif mutation == 'defaults':
        monkeypatch.setattr(catalog.omissions._sha, '__defaults__', (None,))
    elif mutation == 'kwdefaults':
        monkeypatch.setattr(catalog.omissions._sha, '__kwdefaults__', {'changed': True})
    elif mutation == 'function_dict':
        monkeypatch.setattr(catalog.omissions._sha, '__dict__', {'__wrapped__': replacement})
    elif mutation == 'encoder_dict':
        encoder = catalog.json._default_encoder
        monkeypatch.setattr(encoder, '__dict__', {**vars(encoder), 'skipkeys': True})
    elif mutation == 'encoder_class':
        class ChangedEncoder(catalog.json.JSONEncoder):
            pass
        monkeypatch.setattr(catalog.json._default_encoder, '__class__', ChangedEncoder)
    elif mutation == 'dumper_dict':
        monkeypatch.setattr(catalog.json_dumper, '__dict__', {'unexpected': True})
    elif mutation == 'limit_reader':
        limit = sys.getrecursionlimit()
        monkeypatch.setattr(sys, 'getrecursionlimit', lambda: limit)
    elif mutation == 'closure':
        fn = next(fn for fn in catalog._FUNCTIONS._functions
                  if type(fn) is types.FunctionType and fn.__closure__
                  and fn.__code__.co_freevars != ('__class__',))
        monkeypatch.setattr(fn.__closure__[0], 'cell_contents', replacement)
    else:
        prior = sys.getrecursionlimit()
        sys.setrecursionlimit(prior + 100)
        try:
            assert catalog.runtime_token() is None
        finally:
            sys.setrecursionlimit(prior)
    if mutation != 'recursion':
        assert catalog.runtime_token() is None
    assert calls


test_each_guard_refuses_and_uses_full_fallback = pytest.mark.parametrize('phase', [0, 1])(
    pytest.mark.parametrize('mutation', ['meta', 'meta_attribute', 'slotnames', 'loader', 'copy', 'synapse_json_default',
        'code', 'defaults', 'kwdefaults', 'closure', 'recursion', 'limit_reader',
        'function_dict', 'encoder_dict', 'encoder_class', 'dumper_dict'])(test_each_guard_refuses_and_uses_full_fallback))


def _assert_loader_transition_with_same_marker_and_empty_slot_cache(monkeypatch):
    loader = catalog.views.DupCheckYamlLoader
    if 'yaml_constructors' in vars(loader):
        monkeypatch.delattr(loader, 'yaml_constructors')
    marker = set_phase(monkeypatch, 1)
    constructors = loader.yaml_constructors.copy()
    constructors.update(catalog._loader_handlers())
    monkeypatch.setattr(loader, 'yaml_constructors', constructors)
    assert catalog.runtime_token() is marker
    assert len(catalog._FAST_PLANS[marker]) == 2
    monkeypatch.setattr(catalog.meta.SlotDefinition, '__slotnames__', [], raising=False)
    def unexpected():
        raise AssertionError('accepted loader transition returned to full state')
    monkeypatch.setattr(catalog, '_state', unexpected)
    assert catalog.runtime_token() is marker


def test_loader_transition_with_same_marker_and_empty_slot_cache(tmp_path):
    # The process may already have initialized the loader before catalog import.
    # Exercise the forward transition from a fresh interpreter, never by
    # resetting the production cache's captured authority in this process.
    probe = Path(__file__).resolve().parents[1] / 'scripts/adhoc/cache_test_probe_20261116.py'
    result = subprocess.run([sys.executable, str(probe)], capture_output=True,
                            text=True, timeout=60)
    (tmp_path / 'loader-probe.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == 'loader transition assertions passed'


def test_packet_open_memo_is_private_and_checks_live_packet(packet, monkeypatch):
    from copy import deepcopy
    from data_sheets_schema import typed_audit as typed
    cache = typed._OpenPacketCache()
    monkeypatch.setattr(typed, '_OPEN_PACKET_CACHE', cache)
    expected, prepared = typed._open(packet)
    assert len(cache._entries) == 1
    raw, again = typed._open(packet)
    assert raw == expected and again == prepared and cache.hits == 1
    raw.clear()
    assert typed._open(packet)[0] == expected
    broken = deepcopy(packet)
    broken['unrecognized'] = True
    with pytest.raises(ValueError):
        typed._open(broken)
    broken = deepcopy(packet)
    broken['plan']['workers'] = []
    with pytest.raises(ValueError):
        typed._open(broken)
    assets = tuple(typed.omissions.captured_asset_bytes().items())
    typed._open(packet, captured_assets=assets)
    changed = ((assets[0][0], assets[0][1] + b' '),) + assets[1:]
    with pytest.raises(ValueError, match='hash mismatch'):
        typed._open(packet, captured_assets=changed)
    with monkeypatch.context() as installed_change:
        def refuse_asset(name):
            raise ValueError('changed installed asset')
        installed_change.setattr(typed.omissions, '_asset', refuse_asset)
        with pytest.raises(ValueError, match='changed installed asset'):
            typed._open(packet)
    before = cache.hits
    monkeypatch.setattr(typed, '_parse_identity', lambda: None)
    assert typed._open(packet)[0] == expected
    assert cache.hits == before


def test_packet_cache_exact_bytes_bounds_and_identity_transition():
    from data_sheets_schema import typed_audit as typed
    prepared = typed.omissions.Prepared('{}')
    cache = typed._OpenPacketCache(max_entries=2, max_bytes=4096)
    key = ('hash', 1, 'identity', None)
    cache.put(key, b'a', {'x': b'one'}, prepared, lambda: 'changed')
    assert not cache._entries
    cache.put(key, b'a', {'x': b'one'}, prepared, lambda: 'identity')
    assert cache.get(key, b'b') is None
    assert cache.get(key, b'a')[0] == {'x': b'one'}
    for number in range(5):
        current = (str(number), 1, 'identity', None)
        cache.put(current, b'a', {'x': b'one'}, prepared, lambda: 'identity')
        assert len(cache._entries) <= 2 and cache._bytes <= 4096
        assert cache._bytes == sum(value[3] for value in cache._entries.values())
    tiny = typed._OpenPacketCache(max_bytes=1)
    tiny.put(key, b'a', {}, prepared, lambda: 'identity')
    assert not tiny._entries and tiny._bytes == 0
