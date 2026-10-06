"""Pure ordered native receipt/typed stages and the fixed advance command.

No stage function reads files, clients, environment or runtime state. The CLI
delegates all observation and durable publication to native_shared_capture.
Scientific conclusions remain declarations checked by the released consumers.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict
from pathlib import PurePosixPath

from . import native_shared_contract as c
from . import native_shared_receipts as nr
from . import typed_audit as typed
from . import native_catalog_reuse as catalog_reuse


PAYLOAD_KEYS = {
    'genesis': {'execution', 'started'},
    'session_bound': {'binding', 'init_observation'},
    'phase1_sealed': {'seal', 'full', 'original_receipt', 'observation'},
    'core_sealed': {'seal', 'core', 'observation'},
    'request_admitted': {'cursor', 'request', 'response', 'predecessor_history_sha256'},
    'response_consumed': {'cursor', 'request_sha256', 'response', 'read_observation', 'response_observation'},
    'stage_checked': {'cursor', 'request_sha256', 'response_sha256', 'outputs', 'derived_response'},
    'receipt_zero_work': {'outputs'},
    'waiting_for_core': {'receipt_result_sha256'},
    'failed': {'cursor', 'request_sha256', 'response_sha256', 'diagnostic'},
    'assembly_checked': {'assembly', 'audit', 'completion'},
}
RECORD_KEYS = {'kind', 'version', 'record_type', 'sequence', 'previous_record_sha256',
               'selection_sha256', 'execution_sha256', 'attempt_id', 'session_id', 'payload'}
JOURNAL_KEYS = {'kind', 'version', 'selection_sha256', 'execution_sha256', 'attempt_id',
                'records', 'head_sha256'}
OUTPUT_ROLES = ('effective_receipt', 'receipt_result', 'receipt_carry', 'packet',
                'typed_index', 'typed_assembly', 'audit', 'completion')


class _IncompleteReceipt(ValueError):
    def __init__(self, outputs):
        super().__init__('native receipt answers are incomplete; first response remains consumed')
        self.outputs = outputs


def _artifact(raw, role, path, *, observed=False):
    pin = c.ArtifactPin(role=role, path=path, bytes=len(raw), sha256=c.sha(raw))
    return (c.CapturedArtifact if observed else c.ProposedArtifact)(pin=pin, raw=raw)


def _pin(value):
    c.exact(value, {'role', 'path', 'bytes', 'sha256'}, 'stage artifact pin')
    return c.ArtifactPin(**value)


def _dynamic(selection, role, ordinal):
    if type(ordinal) is not int or ordinal < (1 if role in ('request', 'response') else 0):
        raise ValueError('invalid native artifact ordinal')
    root, suffix, limit = {
        'record': ('journal_records_root', 'json', selection.bounds()['max_history_records']),
        'request': ('requests_root', 'json', selection.bounds()['max_submissions'] + 1),
        'response': ('responses_root', 'bin', selection.bounds()['max_submissions'] + 1),
    }[role]
    if ordinal >= limit:
        raise ValueError('native artifact ordinal exceeds its complete bound')
    return str(PurePosixPath(selection.role(root)) / f'{ordinal:06d}.{suffix}')


def journal_bytes(*, selection_sha256, execution_sha256, attempt_id, records):
    """A uses this same serializer for empty/genesis history before observed init."""
    if type(records) is not tuple or any(type(pin) is not c.ArtifactPin for pin in records):
        raise ValueError('journal records must be an immutable pin tuple')
    value = {'kind': c.KINDS['journal'], 'version': c.VERSION,
        'selection_sha256': selection_sha256, 'execution_sha256': execution_sha256,
        'attempt_id': attempt_id, 'records': [c.pin_dict(pin) for pin in records],
        'head_sha256': records[-1].sha256 if records else None}
    raw = c.canonical(value)
    c.strict_json(raw, 'native stage journal', c.HARD_LIMITS['journal_bytes'])
    return raw


def record_bytes(*, record_type, sequence, previous_record_sha256, selection_sha256,
                 execution_sha256, attempt_id, session_id, payload):
    """Canonical closed record, with no own hash or future result reference."""
    if record_type not in PAYLOAD_KEYS:
        raise ValueError('unknown native stage record type')
    c.exact(payload, PAYLOAD_KEYS[record_type], 'native ' + record_type + ' payload')
    if type(sequence) is not int or not 0 <= sequence < c.HARD_LIMITS['history_records']:
        raise ValueError('invalid native record sequence')
    if (sequence == 0) != (record_type == 'genesis') or (sequence == 0) != (previous_record_sha256 is None):
        raise ValueError('native genesis/record predecessor is inconsistent')
    if (record_type == 'genesis') != (session_id is None):
        raise ValueError('only native genesis may lack an observed session')
    raw = c.canonical({'kind': c.KINDS['record'], 'version': c.VERSION, 'record_type': record_type,
        'sequence': sequence, 'previous_record_sha256': previous_record_sha256,
        'selection_sha256': selection_sha256, 'execution_sha256': execution_sha256,
        'attempt_id': attempt_id, 'session_id': session_id, 'payload': payload})
    c.strict_json(raw, 'native stage record', c.HARD_LIMITS['metadata_record_bytes'])
    return raw


def _history(selection, execution, history):
    if type(history) is not c.RawHistory or history.journal.pin.path != selection.role('journal'):
        raise ValueError('native history does not name the selected journal')
    if execution.selection_sha256 != selection.registration.pin.sha256:
        raise ValueError('native execution belongs to another selection')
    bounds = selection.bounds()
    # Refuse oversized captures before parsing or independently reconstructing
    # any historical request. The outer evidence pool has additional bounds;
    # these checks are also necessary at this public pure entry point.
    if len(history.records) > bounds['max_history_records']:
        raise ValueError('native history record bound exceeded')
    if len(history.observations) > c.HARD_LIMITS['observation_records']:
        raise ValueError('native history observation bound exceeded')
    members = (history.journal, *history.records, *history.artifacts, *history.observations)
    if len(members) > c.HARD_LIMITS['captured_members']:
        raise ValueError('native history member bound exceeded')
    if sum(len(item.raw) for item in history.records) + len(history.journal.raw) > bounds['max_history_bytes']:
        raise ValueError('native history byte bound exceeded')
    if sum(len(item.raw) for item in members) > bounds['max_evidence_bytes']:
        raise ValueError('native history evidence byte bound exceeded')
    rows, previous = [], None
    for sequence, artifact in enumerate(history.records):
        if artifact.pin.role != 'record' or artifact.pin.path != _dynamic(selection, 'record', sequence):
            raise ValueError('native record path/ordinal differs from complete ordered history')
        row = c.strict_json(artifact.raw, 'native stage record', c.HARD_LIMITS['metadata_record_bytes'])
        c.exact(row, RECORD_KEYS, 'native stage record')
        expected = record_bytes(record_type=row['record_type'], sequence=sequence,
            previous_record_sha256=previous, selection_sha256=selection.registration.pin.sha256,
            execution_sha256=execution.execution.pin.sha256, attempt_id=execution.attempt_id,
            session_id=None if sequence == 0 else execution.session_id, payload=row['payload'])
        if artifact.raw != expected:
            raise ValueError('native record chronology/identity differs from the captured session')
        rows.append(row)
        previous = artifact.pin.sha256
    expected = journal_bytes(selection_sha256=selection.registration.pin.sha256,
        execution_sha256=execution.execution.pin.sha256, attempt_id=execution.attempt_id,
        records=tuple(item.pin for item in history.records))
    if history.journal.raw != expected:
        raise ValueError('native journal omits, reorders or changes captured records')
    artifacts = {}
    for item in (*history.artifacts, *history.observations):
        if item.pin.path in artifacts:
            raise ValueError('native history repeats an artifact path')
        artifacts[item.pin.path] = item
    return rows, artifacts


def append_records(selection, execution, history, entries):
    """Return proposed records and journal; never write or accept saved verdicts."""
    _history(selection, execution, history)
    if type(entries) is not tuple or not entries:
        raise ValueError('native record append requires an immutable nonempty entry tuple')
    pins = [item.pin for item in history.records]
    proposed = []
    failed = False
    for entry in entries:
        if type(entry) is not tuple or len(entry) != 2 or type(entry[1]) is not bytes:
            raise ValueError('record entries require type and immutable payload JSON bytes')
        kind, payload = entry[0], c.strict_json(entry[1], 'stage record payload')
        raw = record_bytes(record_type=kind, sequence=len(pins),
            previous_record_sha256=pins[-1].sha256 if pins else None,
            selection_sha256=selection.registration.pin.sha256,
            execution_sha256=execution.execution.pin.sha256, attempt_id=execution.attempt_id,
            session_id=None if kind == 'genesis' else execution.session_id, payload=payload)
        item = _artifact(raw, 'record', _dynamic(selection, 'record', len(pins)))
        proposed.append(item)
        pins.append(item.pin)
        failed |= kind == 'failed'
    journal = _artifact(journal_bytes(selection_sha256=selection.registration.pin.sha256,
        execution_sha256=execution.execution.pin.sha256, attempt_id=execution.attempt_id, records=tuple(pins)),
        'journal', selection.role('journal'))
    _budget(selection, history, tuple(proposed) + (journal,), failed=failed)
    return tuple(proposed), journal


def _budget(selection, history, proposed, *, failed=False):
    bounds = selection.bounds()
    reserve = 0 if failed else c.HARD_LIMITS['finalization_reserve_history_bytes']
    records = [item for item in proposed if item.pin.role == 'record']
    if len(history.records) + len(records) > bounds['max_history_records'] - (0 if failed else 1):
        raise ValueError('native stage leaves no reserved failure record')
    history_bytes = sum(len(item.raw) for item in history.records) + sum(len(item.raw) for item in records)
    journal = next((item for item in proposed if item.pin.role == 'journal'), history.journal)
    if history_bytes + len(journal.raw) > bounds['max_history_bytes'] - reserve:
        raise ValueError('native stage leaves no reserved failure history bytes')
    total = sum(len(item.raw) for item in (history.journal, *history.records, *history.artifacts,
                                         *history.observations, *proposed))
    if total > bounds['max_evidence_bytes'] - (0 if failed else c.HARD_LIMITS['finalization_reserve_raw_bytes']):
        raise ValueError('native stage leaves no reserved failure evidence bytes')


def _publication(item, predecessor=None):
    return c.HelperPublication(artifact=item, action='create_once' if predecessor is None else
                              'replace_journal_from_exact_predecessor', predecessor_sha256=predecessor)


def _envelope(raw):
    return {'origin': 'helper_derived_typed_response_v1', 'bytes': len(raw),
            'sha256': c.sha(raw), 'base64': base64.b64encode(raw).decode('ascii')}


class _Replay:
    def __init__(self, selection, execution, phase1, history, *, _catalogs=None):
        self.catalogs = nr._catalog_context(_catalogs)
        self.s, self.e, self.p, self.h = selection, execution, phase1, history
        self.rows, self.artifacts = _history(selection, execution, history)
        self.at = 0
        self.receipt = self.packet = self.index = self.assembly = None
        self.workers, self.omission, self.origins = {}, None, []
        self.cache = typed.DerivationCache()
        self.options = {'captured_assets': nr.omission_assets(selection), 'derivations': self.cache}
        self.pending = None
        self.failure = None
        self.checked_outputs = {}
        self._base()

    def _expect(self, kind, payload):
        if self.at >= len(self.rows) or self.rows[self.at]['record_type'] != kind:
            raise ValueError('native history lacks ordered ' + kind)
        if self.rows[self.at]['payload'] != payload:
            raise ValueError('native ' + kind + ' differs from exact captured authority')
        self.at += 1

    def _base(self):
        self._expect('genesis', {'execution': c.pin_dict(self.e.execution.pin), 'started': c.pin_dict(self.e.started.pin)})
        self._expect('session_bound', {'binding': c.pin_dict(self.e.binding_artifact.pin),
                                      'init_observation': c.pin_dict(self.e.init_observation.pin)})
        self._expect('phase1_sealed', {'seal': c.pin_dict(self.p.seal.pin), 'full': c.pin_dict(self.p.full.pin),
            'original_receipt': c.pin_dict(self.p.original_receipt.pin), 'observation': c.pin_dict(self.p.full_seal_observation.pin)})
        for role, item in (('phase1_seal', self.p.seal), ('phase1_full', self.p.full),
                           ('phase1_receipt', self.p.original_receipt)):
            if item.pin.role != role or item.pin.path != self.s.role(role):
                raise ValueError('native original seal role/path differs from S')

    def _prefix(self, count=None):
        count = self.at if count is None else count
        return c.sha(journal_bytes(selection_sha256=self.s.registration.pin.sha256,
            execution_sha256=self.e.execution.pin.sha256, attempt_id=self.e.attempt_id,
            records=tuple(item.pin for item in self.h.records[:count])))

    def _captured(self, pin, *, observation=False):
        selected = _pin(pin)
        item = self.artifacts.get(selected.path)
        if item is None or item.pin != selected:
            raise ValueError('native history lacks the exact captured artifact')
        if observation and item not in self.h.observations:
            raise ValueError('native response lacks its captured tool observation')
        return item

    def _output(self, role, raw):
        return _artifact(raw, role, self.s.role(role))

    def _compare_outputs(self, outputs):
        for item in outputs:
            actual = self._captured(c.pin_dict(item.pin))
            if actual.raw != item.raw:
                raise ValueError('native output differs from independent raw-response reconstruction')
            self.checked_outputs[item.pin.role] = actual

    def _receipt_outputs(self, value):
        return (self._output('effective_receipt', value.effective_receipt),
                self._output('receipt_result', value.result_json), self._output('receipt_carry', value.carry_json))

    def _packet(self):
        inputs, limits = self.s.document()['inputs'], self.s.bounds()
        schema = nr.schema_snapshot(self.s)
        packet = typed._prepare(protocol='typed_audit_protocol_v1', original_full=self.p.full.raw,
            original_core=self.p.core.raw, bundle=self.s.raw(inputs['bundle']['path']),
            manifest=self.s.raw(inputs['chunk_manifest']['path']), receipt=self.receipt.effective_receipt,
            context=self.s.raw(inputs['context']['path']),
            source_manifest=None if inputs['source_manifest'] is None else self.s.raw(inputs['source_manifest']['path']),
            project=None if inputs['source_manifest'] is None else self.s.project,
            schema_path=schema.sources[0][1], schema_snapshot=schema,
            max_output_tokens=nr.output_ceiling(self.e), max_paths=limits['max_paths_per_worker'],
            max_inventory_bytes=limits['max_inventory_bytes'], max_workers=limits['max_workers'],
            max_request_bytes=limits['max_request_bytes'],
            _catalog_lookup=catalog_reuse._CatalogLookup(self.catalogs, self.s), **self.options)
        if len(packet['plan']['inventory']['values']) > limits['max_populated_paths']:
            raise ValueError('native global populated path bound exceeded')
        return packet

    def _inner(self, cursor):
        if cursor.kind == 'receipt':
            return nr._prepare(self.s, self.e, self.p, self.catalogs)
        if cursor.kind == 'worker':
            return typed.worker_request(self.packet, cursor.target_id, **self.options)
        if cursor.kind == 'omission':
            return self.packet['omission_request']
        self.index = typed.index(self.packet, self.workers, self.omission, **self.options)
        return self.index

    def _request(self, cursor, predecessor):
        inner = self._inner(cursor)
        # Receipt precedes core. Replaying it after a genuine core has been
        # sealed must retain the original request's then-absent core context.
        core = None if cursor.kind == 'receipt' else self.p.core
        core_seal = None if cursor.kind == 'receipt' else self.p.core_seal
        maximum = min(self.s.bounds()['max_response_bytes'],
                      c.HARD_LIMITS['typed_response_bytes'] if cursor.kind in ('worker', 'integration') else
                      c.HARD_LIMITS['generic_response_bytes'])
        response = c.ResponseDestination(role='response', path=_dynamic(self.s, 'response', cursor.ordinal),
            max_bytes=maximum, media_type='application/yaml' if cursor.kind == 'receipt' else 'application/json')
        policies = [{'name': name, 'identity': pin, 'raw_text': self.s.raw(pin['path']).decode('utf-8')}
                    for name, pin in self.s.document()['selection']['assets'].items()]
        catalog = inner['schema'] if cursor.kind == 'receipt' else self.packet['omission_request']['payload']['schema']
        owners = inner['owner_classes'] if cursor.kind == 'receipt' else self.packet['omission_request']['payload']['owner_classes']
        payload = {'protocol': c.NAME, 'selection': {'sha256': self.s.registration.pin.sha256,
            'registration_id': self.s.run_id, 'descriptor_sha256': self.s.descriptor.sha256},
            'execution': {'sha256': self.e.execution.pin.sha256, 'instruction_sha256': self.e.instruction_sha256,
                'runtime_declaration_sha256': self.e.runtime_declaration_sha256},
            'attempt_id': self.e.attempt_id, 'session_id': self.e.session_id, 'cursor': asdict(cursor),
            'predecessor_history_sha256': predecessor,
            'phase1': {'seal': c.pin_dict(self.p.seal.pin), 'full': c.pin_dict(self.p.full.pin),
                'receipt': c.pin_dict(self.p.original_receipt.pin),
                'core': None if core is None else c.pin_dict(core.pin),
                'core_seal': None if core_seal is None else c.pin_dict(core_seal.pin)},
            'policies': policies, 'receipt_carry': None if self.receipt is None else c.strict_json(self.receipt.carry_json),
            'generation_context': self.s.generation_context(),
            'owner_context': {'original_full_yaml': self.p.full.raw.decode('utf-8'),
                'original_core_yaml': None if core is None else core.raw.decode('utf-8'),
                'schema': catalog, 'owner_classes': owners,
                'role_review': 'Review each whole containing entity and its owning role slot; an attested name alone does not establish its relationship. Scientific truth remains unverified.'},
            'inner_request': inner, 'response': asdict(response)}
        c.exact(payload, c.OUTER_REQUEST_KEYS, 'native outer request')
        raw = c.canonical({'request_sha256': c.sha(c.canonical(payload)), 'payload': payload})
        c.strict_json(raw, 'complete native stage request', self.s.bounds()['max_request_bytes'])
        return _artifact(raw, 'request', _dynamic(self.s, 'request', cursor.ordinal)), response, inner

    def _derive_response(self, cursor, inner, raw):
        envelope, outputs = None, ()
        if cursor.kind == 'receipt':
            value = nr._complete(self.s, self.e, self.p, raw, self.catalogs)
            outputs = self._receipt_outputs(value)
            if c.strict_json(value.result_json)['state'] != 'answers_complete':
                raise _IncompleteReceipt(outputs)
            self.receipt = value
        elif cursor.kind == 'worker':
            envelope = typed.capture_response(inner, raw)
            if not typed.check_worker(self.packet, cursor.target_id, envelope, **self.options)['passed']:
                raise ValueError('native worker does not satisfy complete structural coverage')
            self.workers[cursor.target_id] = envelope
        elif cursor.kind == 'omission':
            typed.index(self.packet, self.workers, raw, **self.options)
            self.omission = raw
        else:
            envelope = typed.capture_response(inner, raw)
            self.assembly = typed.assemble(self.packet, self.workers, self.omission, envelope, **self.options)
            audit_raw = typed._unblob(self.assembly['audit'], typed.audit_grammar.MAX_BYTES)
            outputs = (self._output('typed_assembly', c.canonical(self.assembly)), self._output('audit', audit_raw))
        return envelope, outputs

    def _stage(self, cursor):
        predecessor = self._prefix()
        request, destination, inner = self._request(cursor, predecessor)
        auxiliary = ()
        if cursor.kind == 'worker' and not self.workers:
            auxiliary = (self._output('packet', c.canonical(self.packet)),)
        elif cursor.kind == 'integration':
            auxiliary = (self._output('typed_index', c.canonical(self.index)),)
        if self.at == len(self.rows):
            self.pending = ('request_ready', cursor, request, destination, inner, auxiliary, None)
            return False
        expected = {'cursor': asdict(cursor), 'request': c.pin_dict(request.pin),
            'response': asdict(destination), 'predecessor_history_sha256': predecessor}
        self._expect('request_admitted', expected)
        captured_request = self._captured(expected['request'])
        if captured_request.raw != request.raw:
            raise ValueError('native admitted request differs from complete intended semantic content')
        self._compare_outputs(auxiliary)
        if self.at == len(self.rows):
            self.pending = ('awaiting_response', cursor, captured_request, destination, inner, (), None)
            return False
        row = self.rows[self.at]
        if row['record_type'] != 'response_consumed':
            raise ValueError('native stage requires first response consumption before checking')
        consumed = row['payload']
        request_hash = c.strict_json(request.raw, max_bytes=self.s.bounds()['max_request_bytes'])['request_sha256']
        if consumed['cursor'] != asdict(cursor) or consumed['request_sha256'] != request_hash:
            raise ValueError('native consumed response belongs to another stage or complete request')
        response = self._captured(consumed['response'])
        if (response.pin.role != destination.role or response.pin.path != destination.path
                or len(response.raw) > destination.max_bytes):
            raise ValueError('native first response destination/size differs from current cursor')
        self._captured(consumed['read_observation'], observation=True)
        self._captured(consumed['response_observation'], observation=True)
        consumed_pin = self.h.records[self.at].pin
        self.at += 1
        if self.at == len(self.rows):
            self.pending = ('awaiting_response', cursor, captured_request, destination, inner, (),
                            (response, consumed_pin))
            return False
        if self.rows[self.at]['record_type'] == 'failed':
            # Failure is sticky, never an acceptance shortcut. Capacity and
            # publication refusals need not be reproduced against a later,
            # larger capture. The consumed causal bytes and identity must be
            # present; no response can be admitted from this state.
            failure = self.rows[self.at]['payload']
            if (failure['cursor'] != asdict(cursor) or failure['request_sha256'] != request_hash
                    or failure['response_sha256'] != response.pin.sha256
                    or type(failure['diagnostic']) is not str
                    or len(failure['diagnostic'].encode('utf-8')) > c.HARD_LIMITS['failure_diagnostics_bytes']):
                raise ValueError('native failed stage is not bound to its first consumed response')
            self.at += 1
            self.failure = failure
            return False
        try:
            envelope, outputs = self._derive_response(cursor, inner, response.raw)
        except ValueError as exc:
            self._expect('failed', _failure_payload(cursor, request_hash, response.pin.sha256, exc))
            self.failure = _failure_payload(cursor, request_hash, response.pin.sha256, exc)
            return False
        checked = {'cursor': asdict(cursor), 'request_sha256': request_hash,
            'response_sha256': response.pin.sha256, 'outputs': [c.pin_dict(item.pin) for item in outputs],
            'derived_response': None if envelope is None else _envelope(envelope)}
        self._expect('stage_checked', checked)
        self._compare_outputs(outputs)
        self.origins.append({'cursor': asdict(cursor), 'request_sha256': request_hash,
            'request_artifact_sha256': captured_request.pin.sha256,
            'response_sha256': response.pin.sha256, 'session_id': self.e.session_id,
            'consumed_record_sha256': consumed_pin.sha256,
            'helper_derived_response_sha256': None if envelope is None else c.sha(envelope)})
        return True

    def run(self):
        requested = nr._prepare(self.s, self.e, self.p, self.catalogs)['requested_paths']
        ordinal = 1
        if requested:
            if not self._stage(c.StageCursor(ordinal=ordinal, kind='receipt', target_id='receipt')):
                return self
            ordinal += 1
        else:
            self.receipt = nr._complete(self.s, self.e, self.p, None, self.catalogs)
            outputs = self._receipt_outputs(self.receipt)
            if self.at == len(self.rows):
                self.pending = ('receipt_zero_work', None, None, None, None, outputs, None)
                return self
            self._expect('receipt_zero_work', {'outputs': [c.pin_dict(item.pin) for item in outputs]})
            self._compare_outputs(outputs)
        wait = {'receipt_result_sha256': c.sha(self.receipt.result_json)}
        if self.at < len(self.rows) and self.rows[self.at]['record_type'] == 'waiting_for_core':
            self._expect('waiting_for_core', wait)
        if self.p.core is None:
            if self.at != len(self.rows):
                raise ValueError('native typed stages precede the genuine sealed core')
            self.pending = ('await_core', None, None, None, None, (), None)
            return self
        if self.p.core.pin.path != self.s.role('phase1_core') or self.p.core_seal.pin.path != self.s.role('core_seal'):
            raise ValueError('native core capture has foreign selected paths')
        self._expect('core_sealed', {'seal': c.pin_dict(self.p.core_seal.pin), 'core': c.pin_dict(self.p.core.pin),
                                   'observation': c.pin_dict(self.p.core_seal_observation.pin)})
        self.packet = self._packet()
        roster = [('worker', worker['id']) for worker in self.packet['plan']['workers']]
        roster += [('omission', 'omission'), ('integration', 'integration')]
        if ordinal - 1 + len(roster) > self.s.bounds()['max_submissions']:
            raise ValueError('complete native stage roster exceeds declared submissions; no truncation')
        for kind, target in roster:
            if not self._stage(c.StageCursor(ordinal=ordinal, kind=kind, target_id=target)):
                return self
            ordinal += 1
        # The completion artifact names its pre-integration-check history, never
        # the journal that subsequently includes its own identity.
        completion = self._completion_artifact()
        self._expect('assembly_checked', {'assembly': c.pin_dict(self.checked_outputs['typed_assembly'].pin),
            'audit': c.pin_dict(self.checked_outputs['audit'].pin), 'completion': c.pin_dict(completion.pin)})
        self._compare_outputs((completion,))
        if self.at != len(self.rows):
            raise ValueError('native stage history has effects after assembly completion')
        return self

    def _completion_artifact(self):
        integration = self.origins[-1]
        consumed = next(index for index, item in enumerate(self.h.records)
                        if item.pin.sha256 == integration['consumed_record_sha256'])
        body = {'kind': c.KINDS['completion'], 'version': c.VERSION,
            'selection_sha256': self.s.registration.pin.sha256, 'execution_sha256': self.e.execution.pin.sha256,
            'attempt_id': self.e.attempt_id, 'session_id': self.e.session_id,
            'predecessor_history_sha256': self._prefix(consumed + 1),
            'phase1_seal_sha256': self.p.seal.pin.sha256, 'core_seal_sha256': self.p.core_seal.pin.sha256,
            'assembly_sha256': c.sha(c.canonical(self.assembly)), 'stage_origins': self.origins,
            'acceptance': self.assembly['acceptance']}
        return self._output('completion', c.canonical(body))


def _failure_payload(cursor, request_hash, response_hash, exc):
    raw = str(exc).encode('utf-8')
    limit = c.HARD_LIMITS['failure_diagnostics_bytes']
    text = raw[:limit].decode('utf-8', errors='ignore')
    if len(raw) > limit:
        text = text[:-32] + ' [diagnostic truncated]'
    return {'cursor': None if cursor is None else asdict(cursor), 'request_sha256': request_hash,
            'response_sha256': response_hash, 'diagnostic': text}


def _sealed(replay):
    original = (replay.p.seal, replay.p.full, replay.p.original_receipt,
                replay.p.core, replay.p.core_seal)
    return tuple(item.pin for item in original if item is not None) + tuple(
        replay.checked_outputs[role].pin for role in OUTPUT_ROLES if role in replay.checked_outputs)


def prepare_next(selection, execution, phase1, history):
    """Rebuild history and derive the only next request or no-response state."""
    return _prepare_next(selection, execution, phase1, history, nr._ReceiptCatalogContext())


def _prepare_next(selection, execution, phase1, history, catalogs):
    replay = _Replay(selection, execution, phase1, history, _catalogs=catalogs).run()
    state, cursor, request, destination, publications, predecessor = 'assembly_complete', None, None, None, (), None
    failure = None
    completion = None
    if replay.failure is not None:
        state, failure = 'failed', c.canonical(replay.failure)
        if replay.at != len(replay.rows):
            raise ValueError('native history continues after failed consumed response')
    elif replay.pending is None:
        completion = _complete(replay)
    else:
        state, cursor, request, response, inner, outputs, consumed = replay.pending
        if state == 'awaiting_response':
            destination = response
            predecessor = c.strict_json(request.raw, max_bytes=selection.bounds()['max_request_bytes'])['payload']['predecessor_history_sha256']
        else:
            entries = ()
            if state == 'request_ready':
                predecessor = history.journal.pin.sha256
                payload = {'cursor': asdict(cursor), 'request': c.pin_dict(request.pin),
                           'response': asdict(response), 'predecessor_history_sha256': predecessor}
                entries = (('request_admitted', c.canonical(payload)),)
                outputs += (request,)
            elif state == 'receipt_zero_work':
                entries = (('receipt_zero_work', c.canonical({'outputs': [c.pin_dict(item.pin) for item in outputs]})),)
            elif not replay.rows or replay.rows[-1]['record_type'] != 'waiting_for_core':
                entries = (('waiting_for_core', c.canonical({'receipt_result_sha256': c.sha(replay.receipt.result_json)})),)
            if entries:
                records, journal = append_records(selection, execution, history, entries)
                _budget(selection, history, outputs + records + (journal,))
                publications = tuple(_publication(item) for item in outputs + records) + (
                    _publication(journal, history.journal.pin.sha256),)
    return c.StageDecision(state=state, history_sha256=history.journal.pin.sha256,
        request_predecessor_history_sha256=predecessor, cursor=cursor, request=request,
        response=destination, sealed=_sealed(replay), publications=publications,
        completion=completion, failure_json=failure)


def check_response(selection, execution, phase1, history, request_raw, response_raw):
    """First bytes must already be consumed; parsing can never buy another answer."""
    return _check_response(selection, execution, phase1, history, request_raw, response_raw, nr._ReceiptCatalogContext())


def _check_response(selection, execution, phase1, history, request_raw, response_raw, catalogs):
    replay = _Replay(selection, execution, phase1, history, _catalogs=catalogs).run()
    if replay.pending is None or replay.pending[0] != 'awaiting_response' or replay.pending[-1] is None:
        raise ValueError('native response has no unique durable first consumption')
    _, cursor, request, destination, inner, _, consumed = replay.pending
    response, consumed_pin = consumed
    if request.raw != request_raw or response.raw != response_raw:
        raise ValueError('native helper answer differs from first consumed request/response bytes')
    request_hash = c.strict_json(request_raw, max_bytes=selection.bounds()['max_request_bytes'])['request_sha256']
    outputs, entries, disposition = (), (), 'checked'
    try:
        envelope, outputs = replay._derive_response(cursor, inner, response_raw)
        checked = {'cursor': asdict(cursor), 'request_sha256': request_hash,
            'response_sha256': response.pin.sha256, 'outputs': [c.pin_dict(item.pin) for item in outputs],
            'derived_response': None if envelope is None else _envelope(envelope)}
        entries = (('stage_checked', c.canonical(checked)),)
        if cursor.kind == 'integration':
            replay.origins.append({'cursor': asdict(cursor), 'request_sha256': request_hash,
                'request_artifact_sha256': request.pin.sha256, 'response_sha256': response.pin.sha256,
                'session_id': execution.session_id, 'consumed_record_sha256': consumed_pin.sha256,
                'helper_derived_response_sha256': c.sha(envelope)})
            completed = replay._completion_artifact()
            outputs += (completed,)
            by_role = {item.pin.role: item for item in outputs}
            entries += (('assembly_checked', c.canonical({'assembly': c.pin_dict(by_role['typed_assembly'].pin),
                'audit': c.pin_dict(by_role['audit'].pin), 'completion': c.pin_dict(completed.pin)})),)
        records, journal = append_records(selection, execution, history, entries)
        _budget(selection, history, outputs + records + (journal,))
    except ValueError as exc:
        disposition = 'failed'
        outputs = exc.outputs if type(exc) is _IncompleteReceipt else ()
        entries = (('failed', c.canonical(_failure_payload(cursor, request_hash, response.pin.sha256, exc))),)
        records, journal = append_records(selection, execution, history, entries)
        _budget(selection, history, outputs + records + (journal,), failed=True)
    return c.StageTransition(before_history_sha256=history.journal.pin.sha256, cursor=cursor,
        request_sha256=request_hash, first_response=response, consumed_record_sha256=consumed_pin.sha256,
        disposition=disposition, records_to_append=records,
        publications=tuple(_publication(item) for item in outputs), predicted_journal=journal)


def _complete(replay):
    # A fresh cache forces an independent derivation, while deduplicating only
    # repeated pure opens within this final check. No earlier verdict is reused.
    checked = typed.check(replay.assembly, captured_assets=replay.options['captured_assets'],
                          derivations=typed.DerivationCache())
    if not checked['passed']:
        raise ValueError('native final typed assembly did not pass reconstruction')
    out = replay.checked_outputs
    return c.StageCompletion(selection_sha256=replay.s.registration.pin.sha256,
        execution_sha256=replay.e.execution.pin.sha256, attempt_id=replay.e.attempt_id,
        session_id=replay.e.session_id, history_sha256=replay.h.journal.pin.sha256,
        phase1_seal_sha256=replay.p.seal.pin.sha256, core_seal_sha256=replay.p.core_seal.pin.sha256,
        effective_receipt=out['effective_receipt'], receipt_result=out['receipt_result'],
        receipt_carry=out['receipt_carry'], packet=out['packet'], typed_index=out['typed_index'],
        assembly=out['typed_assembly'], audit=out['audit'],
        counts_json=c.canonical({'stages': len(replay.origins), 'workers': len(replay.workers),
            'findings': checked['finding_counts'], 'omissions': checked['omission_counts'],
            'receipt': c.strict_json(replay.receipt.result_json)['counts']}),
        stage_origins_json=c.canonical(replay.origins))


def check_assembly(selection, execution, phase1, history, assembly_raw):
    replay = _Replay(selection, execution, phase1, history).run()
    if replay.pending is not None or replay.failure is not None or replay.assembly is None:
        raise ValueError('native assembly cannot complete before every mandatory consumed stage')
    if c.canonical(replay.assembly) != assembly_raw:
        raise ValueError('native assembly differs from exact current captured history')
    return _complete(replay)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    advance = commands.add_parser('advance')
    advance.add_argument('--registration', required=True)
    args = parser.parse_args()
    from .native_shared_capture import capture_stage, publish_stage
    invocation = capture_stage(args.registration)
    selected = (invocation.selection, invocation.execution, invocation.phase1, invocation.history)
    replay = _Replay(*selected).run()
    if replay.pending is not None and replay.pending[-1] is not None:
        response, _ = replay.pending[-1]
        proposal = check_response(*selected, replay.pending[2].raw, response.raw)
    else:
        proposal = prepare_next(*selected)
    result = publish_stage(invocation, proposal)
    print(c.canonical(result).decode('utf-8'))


if __name__ == '__main__':
    main()
