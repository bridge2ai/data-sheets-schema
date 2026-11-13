"""Invented C histories exercise real B reuse; they are not execution admission."""
from functools import wraps
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from data_sheets_schema import native_catalog_initialization as initialization
from data_sheets_schema import native_catalog_reuse as catalogs
from data_sheets_schema import native_schema_event_reuse as events
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_receipts as receipts
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import typed_audit as typed
from tests.test_native_shared_stages import (
    add_core, case, full_roundtrip, publish, receipt_answer, respond,
)
from tests.test_typed_audit import replies, supplied


STANDALONE_SCHEMA = b'''id: https://example.test/native-owner
name: native_owner
prefixes: {xsd: 'http://www.w3.org/2001/XMLSchema#'}
types:
  string: {base: str, uri: 'xsd:string'}
classes:
  Dataset:
    attributes:
      name: {range: string}
      description: {range: string}
'''


def typed_case(case):
    updated, transition = respond(case, receipt_answer(case))
    assert transition.disposition == 'checked'
    waiting = stage.prepare_next(*updated)
    assert waiting.state == 'await_core'
    return add_core((*updated[:3], publish(updated[3], waiting)))


@pytest.mark.parametrize('case', [{'schema_raw': STANDALONE_SCHEMA}], indirect=True)
def test_replay_owner_reuses_catalog_and_unknown_initialization_is_fresh(case, monkeypatch):
    # This scenario asserts that optional reuse is enabled, so it needs an
    # interpreter whose guarded dependencies have not been changed by earlier
    # tests. Unknown parent state must keep disabling production reuse (#6192).
    schema = next(row for row in case[0].schemas if row.kind == 'full')
    output = Path(schema.sources[0].pin.path).parent / 'owner-delivery.json'
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(root / 'src'), str(root))),
               PYTHONDONTWRITEBYTECODE='1', PYTHONOPTIMIZE='0')
    result = subprocess.run(
        [sys.executable, '-P', '-B', '-m', 'tests.utils.native_shared_owner_delivery_probe',
         '--output', str(output)], cwd=root, env=env, capture_output=True,
        text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    observed = json.loads(output.read_bytes())
    assert observed == json.loads(result.stdout)
    assert observed == {'source_root': str(root), 'reuse_initially_eligible': True,
                        'original_owner_assertions_completed': True,
                        'unknown_initialization_refused': True}


def _assert_replay_owner_reuses_catalog_and_unknown_initialization_is_fresh(case, monkeypatch):
    """Original warm/fresh/refusal scenario, executed by the isolated probe."""
    selected = typed_case(case)
    owner = receipts._ReceiptCatalogContext()
    replay = stage._Replay(*selected, _catalogs=owner).run()
    assert replay.pending[0] == 'request_ready'
    marker = catalogs.runtime_token()
    assert owner._typed_marker is marker and marker is not None
    assert len(owner.derivations()._rows) == 1
    worker = replay.packet['plan']['workers'][0]['id']
    before = events.counters()['documents']
    request = typed.worker_request(replay.packet, worker, **replay.options)
    assert events.counters()['documents'] == before
    # The same real helper without the private owner association must construct
    # a fresh schema. This makes the zero-document hit assertion non-vacuous.
    assert typed.worker_request(replay.packet, worker,
        captured_assets=replay.options['captured_assets'], derivations=replay.cache) == request
    assert events.counters()['documents'] > before
    workers, _, _, _ = replies(replay.packet)
    valid = typed.capture_response(request, workers[worker])
    assert typed.check_worker(replay.packet, worker, valid, **replay.options)['passed']
    changed = c.strict_json(workers[worker])
    changed['source_review']['values'] = []
    invalid = typed.capture_response(request, c.canonical(changed))
    assert not typed.check_worker(replay.packet, worker, invalid, **replay.options)['passed']

    # Preserve all warm pure entries and change the real eligibility predicate.
    # The next replay must rebuild even though the captured bytes are identical.
    before = events.counters()['documents']
    monkeypatch.setattr(initialization, 'INITIALIZATION_ERROR', 'unsupported current initialization')
    assert catalogs.runtime_token() is None
    fresh = stage._Replay(*selected, _catalogs=owner).run()
    assert fresh.packet == replay.packet and fresh.packet is not replay.packet
    assert fresh.pending[2].raw == replay.pending[2].raw
    assert owner._typed_marker is None
    assert events.counters()['documents'] > before
    assert typed.check_worker(fresh.packet, worker, valid, **fresh.options)['passed']
    assert not typed.check_worker(fresh.packet, worker, invalid, **fresh.options)['passed']


@pytest.mark.parametrize('case', [{'schema_raw': STANDALONE_SCHEMA}], indirect=True)
def test_owner_delivery_isolated_from_changed_parent_json_encoder(case, monkeypatch):
    """A prior worker-local dependency change must not poison this scenario."""
    original = json.JSONEncoder.default

    def changed_default(self, value):
        return original(self, value)

    monkeypatch.setattr(json.JSONEncoder, 'default', changed_default)
    monkeypatch.setenv('PYTHONOPTIMIZE', '1')
    # The production guard must keep refusing this unfamiliar binding.
    assert catalogs.runtime_token() is None
    test_replay_owner_reuses_catalog_and_unknown_initialization_is_fresh(case, monkeypatch)
    assert json.JSONEncoder.default is changed_default
    assert catalogs.runtime_token() is None


def test_complete_replay_threads_owner_to_every_typed_call_and_rechecks_final(case, monkeypatch):
    completed, completion = full_roundtrip(case)
    owner = receipts._ReceiptCatalogContext()
    calls = {name: [] for name in ('_prepare', 'worker_request', 'check_worker', 'index', 'assemble', 'check')}

    def observe(name, original):
        @wraps(original)
        def checked(*args, **kwargs):
            lookup = kwargs.get('_catalog_lookup')
            assert type(lookup) is catalogs._CatalogLookup
            assert lookup._context is owner and lookup._selection is completed[0]
            calls[name].append(kwargs['derivations'])
            return original(*args, **kwargs)
        return checked

    for name in calls:
        monkeypatch.setattr(typed, name, observe(name, getattr(typed, name)))
    assert stage._check_assembly(*completed, completion.assembly.raw, owner) == completion
    assert all(calls.values())
    assert calls['_prepare'][0] is owner.derivations()
    # Completion intentionally opens a new derivation cache. The owner stores
    # pure catalog/packet work, never a completed response or acceptance result.
    final_cache = calls['check'][-1]
    assert final_cache is not owner.derivations()
    assert stage._check_assembly(*completed, completion.assembly.raw, owner) == completion
    assert calls['check'][-1] is not final_cache

    original_check = typed.check
    def current_refusal(*args, **kwargs):
        result = original_check(*args, **kwargs)
        assert result['passed']
        return {**result, 'passed': False}
    monkeypatch.setattr(typed, 'check', current_refusal)
    with pytest.raises(ValueError, match='final typed assembly did not pass reconstruction'):
        stage._check_assembly(*completed, completion.assembly.raw, owner)
