"""Captured native derivations must not reopen mutable omission resources."""
from copy import deepcopy
from pathlib import Path

import pytest

from data_sheets_schema import audit_batches as batches, audit_omissions as omissions
from data_sheets_schema import typed_audit as typed
from data_sheets_schema import resources
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_typed_audit import supplied, replies


def assets():
    return tuple((name, omissions._asset(name)) for name in omissions.ASSET_SHA256)


def forbidden(*args, **kwargs):
    raise AssertionError("captured consumer attempted a live resource read")


def test_captured_roundtrip_is_byte_identical_without_live_assets(supplied, monkeypatch):
    snapshot, captured = capture_schema(supplied['schema_path'], strict=True), assets()
    packet = typed.prepare(**supplied, schema_snapshot=snapshot)
    workers, omission, delta, _ = replies(packet, 2)
    saved = {key: typed.capture_response(typed.worker_request(packet, key), raw)
             for key, raw in workers.items()}
    omission_raw = batches.canonical_bytes(omission)
    integration = typed.capture_response(typed.index(packet, saved, omission_raw),
                                         batches.canonical_bytes(delta))
    baseline = typed.assemble(packet, saved, omission_raw, integration)
    expected = typed.check(baseline)
    monkeypatch.setattr(omissions, '_asset', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(Path, 'resolve', forbidden)
    monkeypatch.setattr(resources, 'resource_path', forbidden)
    for cache in (None, typed.DerivationCache()):
        kwargs = dict(captured_assets=captured, derivations=cache)
        actual = typed.prepare(**supplied, schema_snapshot=snapshot, **kwargs)
        assert batches.canonical_bytes(actual) == batches.canonical_bytes(packet)
        for key in saved:
            assert typed.check_worker(actual, key, saved[key], **kwargs)['passed']
        assert typed.check_integration(actual, saved, omission_raw, integration, **kwargs)['passed']
        assembled = typed.assemble(actual, saved, omission_raw, integration, **kwargs)
        assert batches.canonical_bytes(assembled) == batches.canonical_bytes(baseline)
        assert typed.check(assembled, **kwargs) == expected
    with pytest.raises(AssertionError, match='live resource'):
        typed.check(baseline)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'unknown', 'mutated', 'list', 'bytearray'])
def test_capture_refuses_inexact_roster_even_after_cache_hit(supplied, monkeypatch, change):
    captured = assets()
    packet = typed.prepare(**supplied)
    cache = typed.DerivationCache()
    worker = packet['plan']['workers'][0]['id']
    typed.worker_request(packet, worker, captured_assets=captured, derivations=cache)
    bad = list(captured)
    if change == 'missing':
        bad.pop()
    elif change == 'duplicate':
        bad[-1] = bad[0]
    elif change == 'unknown':
        bad[0] = ('foreign.md', bad[0][1])
    elif change == 'mutated':
        bad[0] = (bad[0][0], bad[0][1] + b' ')
    elif change == 'bytearray':
        bad[0] = (bad[0][0], bytearray(bad[0][1]))
    bad = bad if change == 'list' else tuple(bad)
    monkeypatch.setattr(omissions, '_asset', forbidden)
    with pytest.raises(ValueError, match='captured omission'):
        typed.worker_request(packet, worker, captured_assets=bad, derivations=cache)


def test_changed_saved_response_is_rechecked_with_captured_assets(supplied):
    captured = assets()
    packet = typed.prepare(**supplied, captured_assets=captured,
                           schema_snapshot=capture_schema(supplied['schema_path'], strict=True))
    workers, _, _, _ = replies(packet, 0)
    worker_id = next(iter(workers))
    saved = typed.capture_response(typed.worker_request(packet, worker_id, captured_assets=captured), workers[worker_id])
    assert typed.check_worker(packet, worker_id, saved, captured_assets=captured)['passed']
    bad = deepcopy(packet)
    bad['inputs']['original_full']['sha256'] = '0' * 64
    with pytest.raises(ValueError):
        typed.check_worker(bad, worker_id, saved, captured_assets=captured)


def test_logical_replay_never_falls_back_and_separates_cache_identity(supplied, monkeypatch):
    from dataclasses import replace
    snapshot = capture_schema(supplied['schema_path'], strict=True)
    captured = assets()
    frozen = {path: raw for _, path, raw in snapshot.sources}
    monkeypatch.setattr(Path, 'resolve', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(resources, 'resource_path', forbidden)
    replay = capture_schema(supplied['schema_path'], read_bytes=frozen.__getitem__,
                            strict=True, logical_paths=True)
    assert replay.sources == snapshot.sources
    assert replay.key != snapshot.key
    for bad in (replace(snapshot, sources=snapshot.sources[:-1]),
                replace(snapshot, sources=(snapshot.sources[0],
                    (snapshot.sources[1][0], snapshot.sources[1][1].with_name('foreign.yaml'),
                     snapshot.sources[1][2]), *snapshot.sources[2:]))):
        with pytest.raises(ValueError, match='captured closure|import closure'):
            typed.prepare(**supplied, schema_snapshot=bad, captured_assets=captured)
    with pytest.raises(ValueError, match='strict captured reader'):
        capture_schema(supplied['schema_path'], strict=True, logical_paths=True)
    with pytest.raises(ValueError, match='captured schema'):
        typed.prepare(**supplied, captured_assets=captured)


@pytest.mark.parametrize('captured_first', [False, True])
def test_cache_mode_boundary_rederives_once_in_each_direction(supplied, monkeypatch, captured_first):
    captured, packet = assets(), typed.prepare(**supplied)
    worker = packet['plan']['workers'][0]['id']
    cache, calls, original = typed.DerivationCache(), [], typed._derive_uncached
    def counted(*args, **kwargs):
        calls.append(kwargs.get('captured_assets') is not None)
        return original(*args, **kwargs)
    monkeypatch.setattr(typed, '_derive_uncached', counted)
    outputs = []
    for mode in (captured_first, captured_first, not captured_first, not captured_first):
        outputs.append(typed.worker_request(packet, worker, derivations=cache,
                                            captured_assets=captured if mode else None))
    assert calls == [captured_first, not captured_first]
    assert all(output == outputs[0] for output in outputs)
