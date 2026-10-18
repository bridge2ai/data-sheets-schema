"""An explicit pure cache preserves real packet and response checking."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json

import pytest

from data_sheets_schema import typed_audit as ta, audit_batches as batches
from tests.test_typed_audit import supplied, replies  # noqa: F401


def roundtrip(packet, cache=None, count=2):
    workers, omission, delta, _ = replies(packet, count)
    saved = {key: ta.capture_response(ta.worker_request(packet, key, derivations=cache), raw)
             for key, raw in workers.items()}
    raw = batches.canonical_bytes(omission)
    index = ta.index(packet, saved, raw, derivations=cache)
    result = ta.assemble(packet, saved, raw, ta.capture_response(index, batches.canonical_bytes(delta)),
                         derivations=cache)
    return result


def test_real_cached_requests_assembly_and_fresh_final_check_are_identical(supplied, monkeypatch):
    old = ta.prepare(**supplied)
    expected = roundtrip(old)
    calls, original = [], ta._derive_uncached
    def derive(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(ta, '_derive_uncached', derive)
    cache = ta.DerivationCache()
    actual = ta.prepare(**supplied, derivations=cache)
    assert actual == old
    assert roundtrip(actual, cache) == expected
    assert len(calls) == 1
    checked = ta.check(expected, derivations=ta.DerivationCache())
    assert checked['passed'] and checked['independently_reconstructed']
    assert len(calls) == 2  # A new final check derives independently, once.
    assert ta.check(expected) == checked
    assert len(calls) > 2  # Historical default remains uncached.


@pytest.mark.parametrize('mutation', ['packet', 'assembly', 'worker', 'omission', 'integration'])
def test_warm_cache_cannot_cache_packet_or_response_verdicts(supplied, mutation):
    cache = ta.DerivationCache()
    packet = ta.prepare(**supplied, derivations=cache)
    assembly = roundtrip(packet, cache)
    if mutation == 'packet':
        assembly['packet']['requests']['shared_context'] += 'forged'
    elif mutation == 'assembly':
        assembly['acceptance']['passed'] = False
    elif mutation == 'worker':
        key = next(iter(assembly['workers']))
        assembly['workers'][key]['sha256'] = '0' * 64
    elif mutation == 'omission':
        assembly['omission_response']['sha256'] = '0' * 64
    else:
        assembly['integration_response']['sha256'] = '0' * 64
    for selected in (cache, None):
        with pytest.raises(ValueError):
            ta.check(assembly, derivations=selected)


def test_rebuild_keys_cover_captured_schema_inputs_project_and_limits(supplied, monkeypatch):
    packet = ta.prepare(**supplied)
    calls, original = [], ta._derive_uncached
    def derive(*args):
        calls.append(deepcopy(args))
        return original(*args)
    monkeypatch.setattr(ta, '_derive_uncached', derive)
    cache = ta.DerivationCache()
    args = [packet['inputs'], packet['schema_sources'], packet['project'], packet['limits']]
    ta._derive(*args, derivations=cache)
    for kind in ('record', 'context', 'schema', 'limits', 'project'):
        changed = deepcopy(args)
        if kind == 'record':
            changed[0]['original_full'] = ta._blob(b'name: Changed\n')
        elif kind == 'context':
            context = json.loads(ta._unblob(changed[0]['context']))
            context['scopes'][0]['release'] = 'changed'
            changed[0]['context'] = ta._blob(batches.canonical_bytes(context))
        elif kind == 'schema':
            row = changed[1][0]
            row['content'] = ta._blob(ta._unblob(row['content']) + b'\n# captured change\n')
        elif kind == 'limits':
            changed[3]['max_paths'] += 1
        else:
            changed[2] = 'unpaired-source-manifest'
        before = len(calls)
        if kind == 'project':
            for _ in range(2):
                with pytest.raises(ValueError, match='captured together'):
                    ta._derive(*changed, derivations=cache)
            assert len(calls) == before + 2  # Exceptions are never stored.
        else:
            ta._derive(*changed, derivations=cache)
            ta._derive(*changed, derivations=cache)
            assert len(calls) == before + 1


def test_cached_products_are_independent_and_assets_checked_on_every_hit(supplied, monkeypatch):
    packet = ta.prepare(**supplied)
    args = [packet['inputs'], packet['schema_sources'], packet['project'], packet['limits']]
    cache = ta.DerivationCache()
    first = ta._derive(*args, derivations=cache)
    expected = deepcopy(first[0])
    first[0]['plan']['workers'].clear()
    first[1].clear()
    second = ta._derive(*args, derivations=cache)
    assert second[0] == expected and second[1]
    assert first[2] is not second[2]
    with pytest.raises(FrozenInstanceError):
        second[2].payload_json = '{}'
    def changed_asset(name):
        raise ValueError('asset changed')
    monkeypatch.setattr(ta.omissions, '_asset', changed_asset)
    with pytest.raises(ValueError, match='asset changed'):
        ta._derive(*args, derivations=cache)


def test_cache_bounds_and_exact_type_keys(monkeypatch):
    calls = []
    def derive(*args):
        calls.append(args)
        return {'value': len(calls)}, {'data': b'exact'}, ta.omissions.Prepared('{}')
    monkeypatch.setattr(ta, '_derive_uncached', derive)
    cache = ta.DerivationCache(max_entries=1)
    for value in (True, 1, 1.0, '1', True):
        ta._derive({'key': value}, [], None, {}, derivations=cache)
    assert len(calls) == 5 and len(cache._rows) == 1
    assert cache._bytes == sum(map(len, cache._rows.values()))
    tiny = ta.DerivationCache(max_bytes=1)
    for _ in range(2):
        ta._derive({}, [], None, {}, derivations=tiny)
    assert not tiny._rows and tiny._bytes == 0 and len(calls) == 7
    class SubDict(dict):
        pass
    for value in ({1: 'bad'}, {'key': ()}, SubDict()):
        with pytest.raises(ValueError, match='exact'):
            ta._derive(value, [], None, {}, derivations=cache)
    for options in ({'max_entries': True}, {'max_entries': 33}, {'max_bytes': 0}, {'max_bytes': 128_000_001}):
        with pytest.raises(ValueError):
            ta.DerivationCache(**options)
