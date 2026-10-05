"""Attempt-owned pure catalog, with actual loader/observation validation.

The filesystem fixture declares a never-invoked executable, fabricates native
frames and materializes a tiny phase-1 seal/request. No helper or phase observer
is claimed to have run. Registration, stream readers, binding/history/pin joins,
observed Read validation, stage replay and catalog derivation are real. Counters
only delegate; no validator or decision result is replaced.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
import socket

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as controller
from data_sheets_schema import native_shared_receipts as receipts
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema.chunking import build_manifest
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_native_shared_selection import declaration as basic_declaration, pin, save, update_input
from tests.test_native_shared_live_capture import started, native_init, stream_capture
from tests.test_native_shared_registration import execution, bound, native_spec
from tests.test_native_shared_observations import events


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('offline component test attempted network access')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture
def declaration(basic_declaration):
    doc = basic_declaration
    root = Path(doc['inputs']['full_schema']['root'])
    root.write_text('id: https://example.org/full\nname: full\nclasses:\n'
                    '  Dataset:\n    attributes:\n      name: {}\n      description: {}\n')
    snapshot = capture_schema(root, strict=True)
    doc['inputs']['full_schema']['sources'] = [
        {'name': str(name), **pin(path, raw)} for name, path, raw in snapshot.sources]
    bundle = Path(doc['inputs']['bundle']['path'])
    manifest = build_manifest(bundle)
    update_input(doc, 'chunk_manifest', c.canonical(manifest))
    save(doc)
    return doc


def publish_proposal(proposal):
    """Materialize pure fixture publications, not an observed helper success."""
    for publication in proposal.publications:
        item = publication.artifact
        path = Path(item.pin.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(item.raw)


class LiveFixture:
    def __init__(self, started):
        self.cap, self.value, self.selected, self.raw, _ = started
        self.path = self.cap.registration.pin.path
        transcript, control = native_init(self.cap, self.value, self.selected)
        self.native = [c.strict_json(line) for line in transcript.splitlines()]
        self.parent = [c.strict_json(line) for line in control.splitlines()]
        self.session = self.native[1]['session_id']
        capture.initialize(self.path, transcript_bytes=len(transcript), control_bytes=len(control),
                           **stream_capture(self.value))
        self.add_frames('Bash', 'fixture-helper', None)
        run = self.load()
        full = capture._create(self.cap, 'phase1_full', b'name: Synthetic\ndescription: Fictional source description.\n')
        manifest = c.strict_json(self.cap.raw('chunk_manifest'))
        receipt = capture._create(self.cap, 'phase1_receipt', c.canonical({
            'bundle_md5': hashlib.md5(self.cap.raw('bundle')).hexdigest(),
            'chunks': [{'id': row['id'], 'status': 'nothing_relevant',
                        'reason': 'No initial claim receipt in this fictional fixture.'}
                       for row in manifest['chunks']]}))
        payload = {'full': c.pin_dict(full.pin), 'original_receipt': c.pin_dict(receipt.pin),
                   'helper_calls': ['fixture-helper']}
        observation = capture._persist_observation(run, 'phase1_sealed', payload)
        seal = capture._create(self.cap, 'phase1_seal', c.canonical({
            'kind': 'd4d_native_shared_phase1_seal', 'version': 1,
            'selection_sha256': self.cap.registration.pin.sha256,
            'execution_sha256': run.binding.execution.pin.sha256,
            'session_id': run.binding.session_id, 'full': payload['full'],
            'original_receipt': payload['original_receipt'], 'observation': c.pin_dict(observation.pin)}))
        capture._append(self.cap, run.binding, run.history, 'phase1_sealed', {
            'seal': c.pin_dict(seal.pin), 'full': payload['full'],
            'original_receipt': payload['original_receipt'], 'observation': c.pin_dict(observation.pin)})
        run = self.load()
        ready = run.decision()
        assert ready.state == 'request_ready'
        publish_proposal(ready)
        run = self.load()
        self.request = run.decision().request
        self.add_frames('Read', 'whole-request', self.request)
        capture.observe_request_read(self.load(), 'whole-request')
        self.adapter = self.new_adapter()

    def add_frames(self, tool, identity, item):
        native, parent, _ = events('Read', item.raw if item is not None else b'{}')
        call, callback, result = native
        call['session_id'] = result['session_id'] = self.session
        block = call['message']['content'][0]
        block['id'] = identity
        if tool == 'Bash':
            inputs = {'command': self.selected['policy']['native_shared_helpers']['chunk_check']}
            block.update(name='Bash', input=inputs)
            result['message']['content'][0]['content'] = '{}'
            result['tool_use_result'] = {'stdout': '{}', 'stderr': '', 'exitCode': 0}
        else:
            inputs = {'file_path': item.pin.path}
            block['input'] = inputs
            result['tool_use_result']['file']['filePath'] = item.pin.path
        callback['request_id'] = 'callback-' + identity
        callback['request']['callback_id'] = self.selected['policy']['pretool_control']['callback_id']
        callback['request']['input'].update(tool_use_id=identity, tool_name=tool,
            cwd=self.value['working_directory'], tool_input=deepcopy(inputs))
        result['message']['content'][0]['tool_use_id'] = identity
        parent[0]['request'] = deepcopy(callback)
        parent[0]['response']['response']['request_id'] = callback['request_id']
        self.native.extend(native); self.parent.extend(parent)
        self.write_streams()

    def write_streams(self):
        attempt = Path(self.value['attempt_directory'])
        for role, rows in (('transcript', self.native), ('control', self.parent)):
            (attempt / (role + '.jsonl')).write_bytes(b''.join(c.canonical(row) + b'\n' for row in rows))

    def load(self):
        return capture._load_live(self.path)

    def new_adapter(self):
        adapter = controller.CallbackAdapter(c.canonical(self.selected),
            execution=self.value, registration_raw=self.raw)
        observed = stream_capture(self.value)
        adapter._stream_files = observed['stream_files']
        adapter._stream_prefixes = observed['observed_prefixes']
        return adapter

    @property
    def endpoints(self):
        return tuple(self.adapter._stream_prefixes[role].bytes for role in ('transcript', 'control'))


@pytest.fixture
def live(started):
    return LiveFixture(started)


def counters(monkeypatch):
    calls = []
    targets = ((capture, '_base'), (capture, '_live_streams'), (capture, '_binding'),
               (capture._Reader, 'history'), (capture, '_checked_observations'),
               (receipts.omissions, '_schema'))
    for owner, name in targets:
        actual = getattr(owner, name)
        def counted(*args, _actual=actual, _name=name, **kwargs):
            calls.append(_name)
            return _actual(*args, **kwargs)
        monkeypatch.setattr(owner, name, counted)
    return calls


def test_two_real_live_captures_share_only_pure_catalog(live, monkeypatch, tmp_path):
    calls = counters(monkeypatch)
    first = live.adapter._run(live.endpoints)
    first_decision = first.decision()
    second = live.adapter._run(live.endpoints)
    second_decision = second.decision()
    assert first is not second and first.reader is not second.reader
    assert first.history is not second.history and first.history == second.history
    assert first_decision == second_decision
    assert first_decision.state == 'awaiting_response'
    assert first_decision.request == live.request
    assert len(first.observations) == len(second.observations) == 3
    for name in ('_base', '_live_streams', '_binding', 'history', '_checked_observations'):
        assert calls.count(name) == 2, (name, calls)
    (tmp_path / 'capture-counts.json').write_bytes(c.canonical({'calls': calls,
        'request_sha256': live.request.pin.sha256, 'journal_sha256': second.history.journal.pin.sha256}))
    # BEFORE regression: both actual validators derived the same catalog.
    assert calls.count('_schema') == 1
    assert first._catalogs is second._catalogs is live.adapter._receipt_catalogs


def test_strict_default_replaced_public_and_other_adapter_stay_fresh(live, monkeypatch):
    calls = counters(monkeypatch)
    warm = live.adapter._run(live.endpoints)
    expected = warm.decision()
    assert calls.count('_schema') == 1
    bases, private = warm._catalogs.schema_data(warm.selection, receipts.schema_snapshot(warm.selection))
    private['classes'].clear()
    assert type(bases) is tuple
    assert live.adapter._run(live.endpoints).decision() == expected
    assert calls.count('_schema') == 1
    other = live.new_adapter()
    assert other._receipt_catalogs is not warm._catalogs
    assert other._receipt_catalogs._entry is None
    assert other._run(live.endpoints).decision() == expected
    assert calls.count('_schema') == 2
    strict = live.adapter._run()
    assert strict._catalogs is not warm._catalogs and strict.decision() == expected
    assert calls.count('_schema') == 3
    default = capture._load_live(live.path)
    assert default._catalogs is not warm._catalogs and default.decision() == expected
    assert calls.count('_schema') == 4
    copied = replace(warm)
    assert copied._catalogs is not warm._catalogs and copied.decision() == expected
    assert calls.count('_schema') == 5
    public = stage.prepare_next(warm.selection, warm.binding, warm.phase1, warm.history)
    assert public == expected and calls.count('_schema') == 6
    # A callback failure stays latched; warmed storage supplies no retry path.
    with pytest.raises(live.adapter.controls['budgeted_cborg'].BudgetStop):
        live.adapter.observe({})  # This fixture never activated a live transport.
    first_failure = live.adapter.failure
    def no_retry(*args, **kwargs):
        pytest.fail('latched observer attempted another acquisition')
    monkeypatch.setattr(capture, '_load_live', no_retry)
    with pytest.raises(live.adapter.controls['budgeted_cborg'].BudgetStop):
        live.adapter.observe({})
    assert live.adapter.failure == first_failure


@pytest.mark.parametrize('mutation', ['registration', 'observation', 'stream'])
def test_warm_adapter_rechecks_actual_authority_observation_and_stream(live, mutation, tmp_path):
    live.adapter._run(live.endpoints)
    entry = live.adapter._receipt_catalogs._entry
    assert entry is not None
    if mutation == 'registration':
        path = Path(live.value['attempt_directory']) / 'started.json'
        original = path.read_bytes()
        path.write_bytes(original + b' ')
        message = 'actual one-use'
    elif mutation == 'observation':
        path = Path(live.cap.role('observations_root')) / '000002.json'
        original = path.read_bytes()
        doc = c.strict_json(original)
        doc['payload']['history_sha256'] = 'f' * 64
        path.write_bytes(c.canonical(doc))
        message = 'observation does not name one exact actual journal prefix'
    else:
        path = Path(live.value['attempt_directory']) / 'transcript.jsonl'
        original = path.read_bytes()
        path.rename(tmp_path / 'original-transcript-retained.jsonl')
        path.write_bytes(original)
        message = 'identity'
    (tmp_path / 'mutation-original.bin').write_bytes(original)
    with pytest.raises(ValueError, match=message):
        live.adapter._run(live.endpoints)
    assert live.adapter._receipt_catalogs._entry == entry


def test_live_context_rejects_nonexact_storage_before_observation_validation(live, monkeypatch):
    class Foreign(receipts._ReceiptCatalogContext):
        pass
    calls = counters(monkeypatch)
    for foreign in (object(), Foreign()):
        with pytest.raises(ValueError, match='private derivation storage'):
            capture._load_live(live.path, _catalogs=foreign)
    assert calls.count('_base') == calls.count('_binding') == calls.count('history') == 2
    assert '_checked_observations' not in calls and '_schema' not in calls
