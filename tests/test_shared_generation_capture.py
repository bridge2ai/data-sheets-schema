"""New selected requests consume the registered immutable closure."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner as api, shared_generation as sg
from tests.test_shared_generation_selection import selected, external, offline  # noqa: F401


def test_pure_memo_binds_every_raw_part_and_returns_fresh_values():
    spec = SimpleNamespace()
    calls = []
    def build():
        calls.append(1)
        return {'values': [len(calls)]}
    first = sg.memo(spec, 'one', [b'authority', b'response'], build)
    first['values'].append(99)
    assert sg.memo(spec, 'one', [b'authority', b'response'], build) == {'values': [1]}
    assert sg.memo(spec, 'one', [b'changed authority', b'response'], build) == {'values': [2]}
    assert sg.memo(spec, 'one', [b'authority', b'changed response'], build) == {'values': [3]}
    assert sg.memo(spec, 'another', [b'authority', b'response'], build) == {'values': [4]}


def test_pure_memo_bound_evicts_and_rebuilds(monkeypatch):
    spec = SimpleNamespace()
    monkeypatch.setattr(sg, 'MAX_MEMO_ENTRIES', 1)
    assert sg.memo(spec, 'a', [b'1'], lambda: 1) == 1
    assert sg.memo(spec, 'a', [b'2'], lambda: 2) == 2
    assert len(spec._shared_generation_derivations) == 1
    assert sg.memo(spec, 'a', [b'1'], lambda: 3) == 3


def test_captured_wire_does_not_use_legacy_live_readers(selected, monkeypatch):
    selected.bind_api_header_values(api._model_settings())
    expected = api.build_phase(selected, 'full', carry={})
    def absent(*args, **kwargs):
        pytest.fail('new request read a legacy live authority reader')
    from data_sheets_schema import schema_digest, grounding, scope, registry
    monkeypatch.setattr(schema_digest, 'digest_text', absent)
    monkeypatch.setattr(api, 'chunk_marked_bundle', absent)
    monkeypatch.setattr(grounding, 'declared_naming', absent)
    monkeypatch.setattr(scope, 'scope_of', absent)
    monkeypatch.setattr(registry, 'load_registry', absent)
    actual = api.build_phase(selected, 'full', carry={})
    assert actual.messages == expected.messages
    assert actual.system == expected.system
    pin = sg.capture(selected).document()['inputs']['source_manifest']
    assert api.source_metadata_authority(selected)['source_manifest_raw'] == sg.capture(selected).raw(pin['path'])


def test_cache_never_bypasses_fresh_authority_bytes(selected):
    first = sg.digest_text(selected, 'Dataset')
    assert first
    pin = sg.capture(selected).document()['inputs']['context']
    Path(pin['path']).write_bytes(Path(pin['path']).read_bytes() + b' ')
    with pytest.raises(ValueError, match='authority changed'):
        sg.digest_text(selected, 'Dataset')
