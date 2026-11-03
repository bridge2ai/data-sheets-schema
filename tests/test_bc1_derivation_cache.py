"""BC1 pure cache equivalence/invalidation; D44/D45, offline 2026-10-27.

Reuse the invented captured inputs and real codec/replay checks. No provider,
accepted-response cache, or scientific-support stub is used.
"""
from copy import deepcopy
import sys

import pytest
import yaml

from data_sheets_schema import bc1_audit as bc
from data_sheets_schema import audit_omissions as om, bc1_context
from data_sheets_schema.schema_view import DupCheckYamlLoader
from tests.test_bc1_audit import supplied, deliveries, stage_delta, save_delta


def arguments(packet):
    return tuple(packet[key] for key in ('inputs', 'schema_sources', 'selection', 'project', 'limits'))


def finish(packet, cache):
    workers, omission, quote = deliveries(packet)
    state = bc.start(packet, workers, omission, derivations=cache)
    saved = []
    for group in [*packet['groups'], {'id': 'final'}]:
        request = bc.stage_request(packet, state, group['id'], derivations=cache)
        assert request == bc.stage_request(packet, state, group['id'])
        raw = save_delta(packet, request, stage_delta(packet, request, quote=quote))
        state = bc.apply_transition(packet, state, request, raw, derivations=cache)
        saved.append(raw)
    return bc.assemble(packet, workers, omission, saved, derivations=cache), workers, omission, saved


def test_all_public_outputs_equal_uncached_and_one_pure_entry(supplied):
    cache = bc.DerivationCache()
    packet = bc.prepare(**supplied, derivations=cache)
    assert cache.refresh() and len(cache._rows) == 1
    assert packet == bc.prepare(**supplied)
    assert bc.roster(packet, derivations=cache) == bc.roster(packet)
    assert bc.omission_request(packet, derivations=cache) == bc.omission_request(packet)
    for worker in packet['plan']['workers']:
        assert bc.worker_request(packet, worker['id'], derivations=cache) == bc.worker_request(packet, worker['id'])
    assembly, workers, omission, stages = finish(packet, cache)
    assert assembly == bc.assemble(packet, workers, omission, stages)
    assert bc.check(assembly, derivations=cache) == bc.check(assembly)
    assert bc.audit_bytes(assembly, derivations=cache) == bc.audit_bytes(assembly)
    assert bc.project(assembly, derivations=cache) == bc.project(assembly)
    assert bc.project_bytes(assembly, derivations=cache) == bc.project_bytes(assembly)
    assert len(cache._rows) == 1


def test_private_values_prepared_and_packet_cannot_poison_cache(supplied):
    cache = bc.DerivationCache()
    packet = bc.prepare(**supplied, derivations=cache)
    expected = deepcopy(packet)
    derived, raw, prepared = bc._derive(*arguments(packet), derivations=cache)
    derived['plan']['workers'].clear()
    raw['original_full'] = b'name: wrong\n'
    prepared.request()['payload']['schema'].clear()
    packet['dictionary']['chunks'].clear()
    assert bc.prepare(**supplied, derivations=cache) == expected
    _, private_raw, private_prepared = bc._derive(*arguments(expected), derivations=cache)
    assert private_prepared is not prepared
    assert private_raw['original_full'] == supplied['original_full']
    assert private_prepared.request()['payload']['schema']['classes']
    with pytest.raises(ValueError, match='captured-byte derivation'):
        bc.roster(packet, derivations=cache)


def test_warm_lookup_avoids_uncached_work_without_replacing_functions(supplied):
    cache = bc.DerivationCache()
    packet = bc.prepare(**supplied, derivations=cache)
    assert cache.refresh() and cache._rows
    calls = []
    code = bc._derive_uncached.__code__
    def observe(frame, event, arg):
        if event == 'call' and frame.f_code is code:
            calls.append('derived')
    previous = sys.getprofile()
    try:
        sys.setprofile(observe)
        bc.roster(packet, derivations=cache)
        bc.worker_request(packet, packet['plan']['workers'][0]['id'], derivations=cache)
        assert calls == []
        bc.prepare(**dict(supplied, max_paths=2), derivations=cache)
        assert calls == ['derived']
    finally:
        sys.setprofile(previous)


def test_known_parser_loader_default_is_identity_only_and_cacheable():
    assert bc._CACHE_DEPENDENCIES is not None
    assert bc.DerivationCache().refresh()
    assert bc._cache_default_state(yaml.parse.__defaults__) == (
        tuple, ((type(yaml.Loader), yaml.Loader),))
    with pytest.raises(TypeError):
        bc._cache_default_state(object())


def test_shipped_loader_first_use_tables_are_bound_before_any_packet(supplied):
    assert bc._CACHE_DEPENDENCIES is not None
    before = bc._cache_dependency_token()
    loader = DupCheckYamlLoader('')
    loader.dispose()
    assert bool(bc._cache_dependency_token() == before)
    cache = bc.DerivationCache()
    bc.prepare(**supplied, derivations=cache)
    assert cache.refresh() and len(cache._rows) == 1
    assert bool(bc._cache_dependency_token() == before)


@pytest.mark.parametrize('change', ['record', 'schema', 'selection', 'limits', 'context'])
def test_exact_captured_inputs_invalidate_or_refuse(supplied, change):
    cache = bc.DerivationCache()
    packet = bc.prepare(**supplied, derivations=cache)
    altered = deepcopy(supplied)
    if change == 'record':
        altered['original_full'] += b'missing: Proposed missing value\n'
    elif change == 'schema':
        rows = deepcopy(packet['schema_sources'])
        raw = bc.typed._unblob(rows[0]['content'])
        rows[0]['content'] = bc.typed._blob(raw.replace(b'      missing: {}', b'      missing: {description: "Changed captured definition"}'))
        altered['schema_snapshot'] = bc.typed._snapshot(rows)
        altered['selection']['inputs']['full_schema'] = bc1_context._schema_pin(altered['schema_snapshot'])
    elif change == 'selection':
        altered['selection']['inputs']['profile']['basis'] += ' Another explicit source.'
    elif change == 'limits':
        altered['max_paths'] = 2
    else:
        altered['context'] += b' '
        with pytest.raises(ValueError, match='registered byte pin'):
            bc.prepare(**altered, derivations=cache)
        assert len(cache._rows) == 1
        return
    changed = bc.prepare(**altered, derivations=cache)
    assert changed != packet and changed == bc.prepare(**altered)
    assert len(cache._rows) == 2


def test_real_asset_change_refuses_even_with_warmed_packet(supplied, tmp_path, monkeypatch):
    private = tmp_path / 'omission-assets'
    private.mkdir()
    for name in om.ASSET_SHA256:
        (private / name).write_bytes((om.ASSETS / name).read_bytes())
    monkeypatch.setattr(om, 'ASSETS', private)
    cache = bc.DerivationCache()
    packet = bc.prepare(**supplied, derivations=cache)
    assert len(cache._rows) == 1
    (private / 'policy.md').write_bytes((private / 'policy.md').read_bytes() + b'\nchanged')
    with pytest.raises(ValueError, match='frozen omission policy/schema changed'):
        bc.roster(packet, derivations=cache)


def test_current_contract_change_refuses_a_warmed_selection(supplied, monkeypatch):
    cache = bc.DerivationCache()
    packet = bc.prepare(**supplied, derivations=cache)
    monkeypatch.setattr(bc, 'MAX_OPEN_CONCERNS', bc.MAX_OPEN_CONCERNS + 1)
    with pytest.raises(ValueError, match='contract mismatch'):
        bc.roster(packet, derivations=cache)


@pytest.mark.parametrize('change', ['schema_parser', 'schema_budget', 'schema_file_count',
                                  'code', 'defaults', 'loader_default', 'loader_table', 'captured_loader_table'])
def test_dependency_change_bypasses_and_clears_both_pure_caches(supplied, monkeypatch, change):
    cache = bc.DerivationCache()
    packet = bc.prepare(**supplied, derivations=cache)
    assert cache.refresh() and cache._rows
    cache._shared_generation_derivations = {'invented': b'"stale schema text"'}
    if change == 'schema_parser':
        def refuse(*args, **kwargs):
            raise ValueError('changed schema parser')
        monkeypatch.setattr(om, '_schema', refuse)
    elif change == 'schema_budget':
        monkeypatch.setattr(om, 'MAX_SCHEMA_BYTES', 1)
    elif change == 'schema_file_count':
        monkeypatch.setattr(bc.typed, 'MAX_SCHEMA_FILES', 0)
    elif change == 'code':
        def replacement(value):
            return 'changed code'
        monkeypatch.setattr(om._sha, '__code__', replacement.__code__)
    elif change == 'defaults':
        monkeypatch.setattr(om._read, '__kwdefaults__', {**om._read.__kwdefaults__, 'limit': 1})
    elif change == 'loader_default':
        monkeypatch.setattr(yaml.parse, '__defaults__', (yaml.SafeLoader,))
    elif change == 'captured_loader_table':
        table = dict(DupCheckYamlLoader.yaml_constructors)
        table['tag:yaml.org,2002:str'] = lambda loader, node: 'changed captured string'
        monkeypatch.setattr(DupCheckYamlLoader, 'yaml_constructors', table)
    else:
        table = dict(om._UniqueLoader.yaml_constructors)
        table['tag:yaml.org,2002:str'] = lambda loader, node: 'changed parsed string'
        monkeypatch.setattr(om._UniqueLoader, 'yaml_constructors', table)
    assert not cache.refresh()
    assert not cache._rows and cache._bytes == 0
    assert not hasattr(cache, '_shared_generation_derivations')
    if change in ('schema_parser', 'schema_budget', 'schema_file_count', 'defaults'):
        with pytest.raises(ValueError):
            bc.roster(packet, derivations=cache)
        assert not cache._rows


@pytest.mark.parametrize('kwargs', [dict(max_entries=True), dict(max_entries=0), dict(max_entries=33),
    dict(max_bytes=True), dict(max_bytes=0), dict(max_bytes=128_000_001)])
def test_strict_cache_capacity(kwargs):
    with pytest.raises(ValueError, match='bounded positive integer'):
        bc.DerivationCache(**kwargs)


def test_retained_key_and_value_bytes_count_and_oversized_results_are_not_cached(supplied):
    cache = bc.DerivationCache(max_entries=1)
    first = bc.prepare(**supplied, derivations=cache)
    assert cache._bytes == sum(len(key) + len(value) for key, value in cache._rows.items())
    changed = dict(supplied, max_paths=2)
    bc.prepare(**changed, derivations=cache)
    assert len(cache._rows) == 1
    assert cache._bytes == sum(len(key) + len(value) for key, value in cache._rows.items())
    assert bc.prepare(**supplied, derivations=cache) == first
    small = bc.DerivationCache(max_bytes=1)
    assert bc.prepare(**supplied, derivations=small) == first
    assert small._bytes == 0 and small._rows == {}


def test_warm_cache_still_replays_responses_and_default_check_is_fresh(supplied, monkeypatch):
    cache = bc.DerivationCache()
    packet = bc.prepare(**supplied, derivations=cache)
    assembly, workers, omission, stages = finish(packet, cache)
    altered = deepcopy(assembly)
    altered['acceptance']['scientific_support'] = 'invented acceptance'
    altered = bc._seal({key: value for key, value in altered.items() if key != 'sha256'})
    with pytest.raises(ValueError, match='independent captured-byte replay'):
        bc.check(altered, derivations=cache)
    # The implicit independent check has no access to the caller's warm cache.
    observed = []
    original = bc._derive_uncached
    def recording(*args, **kwargs):
        observed.append('fresh derivation')
        return original(*args, **kwargs)
    monkeypatch.setattr(bc, '_derive_uncached', recording)
    assert bc.check(assembly)['passed']
    assert observed == ['fresh derivation']
    # A new failure from the terminal evidence checker is never memoized away.
    def reject(*args, **kwargs):
        raise ValueError('fresh terminal evidence check')
    monkeypatch.setattr(bc.evidence, 'check_audit', reject)
    with pytest.raises(ValueError, match='fresh terminal evidence check'):
        bc.check(assembly, derivations=cache)
