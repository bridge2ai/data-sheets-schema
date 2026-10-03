"""New selected requests consume the registered immutable closure."""
from pathlib import Path
from types import SimpleNamespace
import json

import yaml

import pytest

from data_sheets_schema import api_runner as api, shared_generation as sg
from tests.test_shared_generation_selection import selected, external, offline  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec


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


@pytest.mark.parametrize('key,value', [('model', 'different-model'), ('thinking', {'type': 'disabled'}),
    ('effort', 'a-different-declared-effort')])
def test_direct_execution_preflights_before_client_or_call(external, monkeypatch, key, value):
    reg = registration_for(external)
    reg['runtime'][key] = value
    spec = selected_spec(external, reg)
    calls = []
    monkeypatch.setattr(api, '_client', lambda: calls.append('constructed'))
    with pytest.raises(ValueError, match='differs from resolved'):
        api.execute(spec)
    assert calls == []
    assert not spec.provenance_path.exists()


@pytest.mark.parametrize('raw', [b'{"format":"omission_context_v1"}',
    b'format: omission_context_v1\nroot_class: Dataset\n'])
def test_invalid_context_refused_before_generation(external, raw):
    reg = registration_for(external)
    path = Path(reg['inputs']['context']['path'])
    path.write_bytes(raw)
    reg['inputs']['context'] = sg.file_pin(path)
    with pytest.raises(ValueError):
        selected_spec(external, reg)


def test_whole_owner_context_preserves_native_dates_nested_values_and_lookalikes(selected):
    from data_sheets_schema.support_targets import _typed
    record = """id: urn:fictional
issued: 2026-01-02
modified: 2026-01-02T03:04:05+02:00
creators:
  - name: sample
    description: '2026-01-02'
annotations:
  nested:
    - 2026-01-02
    - '2026-01-02'
    - {type: date, value: '2026-01-02'}
"""
    value = yaml.safe_load(record)
    result = json.loads(sg.schema_context(selected, record).split('\n\n', 1)[1])
    root = next(row for row in result['owners'] if row['path'] == '')
    assert root['whole_value_identity'] == _typed(value)
    assert yaml.safe_load(root['whole_value_yaml']) == value
    creator = next(row for row in result['owners'] if row['path'] == '/creators/0')
    assert creator['whole_value_identity'] == _typed(value['creators'][0])
    assert _typed(value['annotations']['nested'][0]) != _typed(value['annotations']['nested'][1])
    assert _typed(value['annotations']['nested'][0]) != _typed(value['annotations']['nested'][2])
    quoted = record.replace('issued: 2026-01-02', "issued: '2026-01-02'")
    assert sg.schema_context(selected, quoted) != sg.schema_context(selected, record)
