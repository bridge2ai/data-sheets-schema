"""Exact omission response identity for legacy and explicitly captured S7 wire.

Offline invented packets exercise real prepare/index/assemble/check paths.
The packet selector is never inferred from a response or supplied hash.
"""
from copy import deepcopy

import pytest

from data_sheets_schema import audit_omissions as om, shared_generation as sg, typed_audit as ta
from tests.test_typed_audit import supplied, replies, saved_workers, seal  # noqa: F401
from tests.test_audit_omissions import inputs, prepared, answer, raw  # noqa: F401


def reseal(packet):
    return ta._seal({key: value for key, value in packet.items() if key != 'sha256'})


@pytest.mark.parametrize('selected', [False, True])
def test_exact_omission_wire_roundtrip_and_independent_check(supplied, selected):
    cache = ta.DerivationCache()
    legacy = ta.prepare(**supplied, derivations=cache)
    packet = ta.prepare(**supplied, derivations=cache,
                        omission_wire=ta.SHARED_OMISSION_WIRE if selected else None)
    request = ta.omission_wire_request(packet, derivations=cache)
    if selected:
        assert packet['omission_wire'] == ta.SHARED_OMISSION_WIRE
        assert request['packet_request_sha256'] == packet['omission_request']['request_sha256']
        assert request['request_sha256'] != request['packet_request_sha256']
        assert request['payload']['schema'] == sg.trim_omission_schema(packet['omission_request']['payload']['schema'])
    else:
        assert packet == legacy
        assert 'omission_wire' not in packet
        assert request == packet['omission_request']
    assert request['request_sha256'] == sg.sha(sg.canonical(request['payload']))
    workers, omission, delta, _ = replies(packet)
    omission['request_sha256'] = request['request_sha256']
    assembly = seal(packet, workers, omission, delta)
    assert ta.check(assembly, derivations=ta.DerivationCache())['passed']
    assert assembly['index']['omission_check']['request_sha256'] == request['request_sha256']
    if selected:
        assert assembly['lineage']['omission_wire_request_sha256'] == request['request_sha256']
        assert assembly['lineage']['omission_request_sha256'] == request['packet_request_sha256']


@pytest.mark.parametrize('selected', [False, True])
def test_cross_wire_hash_is_refused_in_both_directions(supplied, selected):
    packet = ta.prepare(**supplied, omission_wire=ta.SHARED_OMISSION_WIRE if selected else None)
    workers, omission, _, _ = replies(packet)
    original = packet['omission_request']
    projected_payload = {**original['payload'], 'schema': sg.trim_omission_schema(original['payload']['schema'])}
    projected_hash = sg.sha(sg.canonical(projected_payload))
    assert projected_hash != original['request_sha256']
    omission['request_sha256'] = original['request_sha256'] if selected else projected_hash
    with pytest.raises(ValueError, match='omission response does not satisfy complete captured inventory'):
        ta.index(packet, saved_workers(packet, workers), raw(omission))


@pytest.mark.parametrize('value', [None, False, 2, 2.0, '', 'shared_generation_s7_v1', {}, []])
def test_packet_wire_selector_is_closed_and_not_inferred(supplied, value):
    packet = ta.prepare(**supplied)
    packet = reseal({**packet, 'omission_wire': value})
    with pytest.raises(ValueError, match='unsupported omission wire selection'):
        ta.omission_wire_request(packet)


@pytest.mark.parametrize('value', [False, 2, 2.0, '', 'shared_generation_s7_v1', {}, []])
def test_prepare_refuses_unsupported_wire_selection(supplied, value):
    with pytest.raises(ValueError, match='unsupported omission wire selection'):
        ta.prepare(**supplied, omission_wire=value)


def test_removing_wire_flag_cannot_rebind_saved_selected_workers(supplied):
    selected = ta.prepare(**supplied, omission_wire=ta.SHARED_OMISSION_WIRE)
    workers, omission, _, _ = replies(selected)
    saved = saved_workers(selected, workers)
    legacy = deepcopy(selected)
    del legacy['omission_wire']
    legacy = reseal(legacy)
    assert legacy == ta.prepare(**supplied)
    # Even rewriting the inner omission echo cannot rebind existing workers.
    omission['request_sha256'] = legacy['omission_request']['request_sha256']
    with pytest.raises(ValueError):
        ta.index(legacy, saved, raw(omission))


def test_saved_request_projection_cannot_override_public_preparation(prepared):
    saved = prepared.request()
    saved['payload']['schema'] = sg.trim_omission_schema(saved['payload']['schema'])
    saved['request_sha256'] = sg.sha(sg.canonical(saved['payload']))
    with pytest.raises(ValueError, match='saved request differs'):
        prepared.check(raw(answer(prepared)), saved_request=saved)
