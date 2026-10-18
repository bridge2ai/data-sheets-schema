"""Read-only, relocatable completion of explicitly selected routing API v2.

Logical paths are identities, never filesystem requests. This fixed reader is
not a RunSpec accepted for execution and cannot admit or recover a call.
"""
from __future__ import annotations

import base64
import copy
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from . import api_runner as api, shared_generation as sg
from .usage_ledger import UsageLedgerError

FORMAT = 'source_heading_completed_v1'
MAX_FILES = 4096
MAX_FILE_BYTES = 64_000_000
MAX_TOTAL_BYTES = 256_000_000
MAX_ENVELOPE_BYTES = 384_000_000
MAX_METADATA_BYTES = 8_000_000
MAX_DEPTH = 100


class _CompletedSpec(api.RunSpec):
    """Private rendering context. Construction deliberately has no live init.

    from_render_spec still verifies the installed policy/renderer identities.
    Public execute rejects _replay_only before any authority or output action.
    """
    def __post_init__(self):
        if not self._replay_only or self.shared_generation_version != 2:
            raise ValueError('captured completion requires explicit read-only routing v2')
        self._paths = {}

    @property
    def full_path(self):
        return Path(self._paths['full'])

    @property
    def core_path(self):
        return Path(self._paths['core'])

    @property
    def report_path(self):
        return Path(self._paths['report'])

    @property
    def provenance_path(self):
        return Path(self._paths['provenance'])

    @property
    def metadata_dir(self):
        return self.provenance_path.parent

    def input_identity(self):
        captured = self._captured_authority
        inputs = captured.document()['inputs']
        def entry(pin):
            return {k: pin[k] for k in ('path', 'sha256')} if pin else None
        schema = {'sources': [{'name': name, 'path': str(path), 'sha256': sg.sha(raw)}
                             for name, path, raw in captured.full_schema.sources]}
        return {'receipt_completion_schema': schema, 'shared_generation': captured.identity(),
            'bundle': entry(inputs['bundle']),
            'source_manifest': entry(inputs['source_manifest']) if self.manifest_used else None,
            'chunks': entry(inputs['chunk_manifest']),
            'profile': {'name': self.profile, 'digest_md5': hashlib.md5(sg.digest_text(self, 'Dataset').encode()).hexdigest()},
            'instruction': {'render_version': self.render_version,
                'spec': {k: v for k, v in self.render_spec().items() if k != 'profile_basis'},
                'sha256': sg.sha(self.instruction.encode())}}


@dataclass(frozen=True)
class _Reader:
    files: tuple[tuple[str, bytes], ...]

    def raw(self, path):
        name = str(path)
        for logical, raw in self.files:
            if logical == name:
                return raw
        raise UsageLedgerError('completed closure lacks its exact logical artifact: ' + name)

    def load(self, pin):
        sg._exact(pin, {'path', 'sha256'}, 'completed artifact pin')
        raw = self.raw(pin['path'])
        if sg.sha(raw) != pin['sha256']:
            raise UsageLedgerError('completed artifact pin differs')
        from .evidence_assertions import load_json
        value = load_json(raw.decode('utf-8'))
        if type(value) is not dict:
            raise UsageLedgerError('completed artifact must be a JSON object')
        return value


def _decode(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_ENVELOPE_BYTES:
        raise ValueError('completed capture exceeds encoded byte bound')
    from .support_targets import _validate_json
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=sg._pairs, parse_constant=sg._invalid_constant)
    _validate_json(value, max_nodes=200_000, max_depth=MAX_DEPTH)
    sg._exact(value, {'format', 'selection', 'files', 'blobs'}, 'completed capture')
    if value['format'] != FORMAT:
        raise ValueError('unsupported completed routing capture')
    metadata = {key: value[key] for key in ('format', 'selection', 'files')}
    if len(sg.canonical(metadata)) > MAX_METADATA_BYTES:
        raise ValueError('completed capture metadata exceeds bound')
    if type(value['files']) is not list or not 0 < len(value['files']) <= MAX_FILES:
        raise ValueError('completed capture file roster exceeds bound')
    if type(value['blobs']) is not dict or len(value['blobs']) > MAX_FILES:
        raise ValueError('invalid completed content map')
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > MAX_DEPTH:
            raise ValueError('completed capture exceeds depth bound')
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
    decoded, total, names, used, files = {}, 0, set(), set(), []
    for digest, text in value['blobs'].items():
        if type(text) is not str or len(text) > 4 * ((MAX_FILE_BYTES + 2) // 3):
            raise ValueError('completed content exceeds file bound')
        data = base64.b64decode(text, validate=True)
        if len(data) > MAX_FILE_BYTES or sg.sha(data) != digest:
            raise ValueError('completed content hash/size differs')
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise ValueError('completed content exceeds total byte bound')
        decoded[digest] = data
    logical_total = 0
    for pin in value['files']:
        sg._exact(pin, {'path', 'sha256', 'bytes'}, 'completed logical file')
        sg._path(pin['path'], 'completed logical file')
        data = decoded.get(pin['sha256'])
        if pin['path'] in names or data is None or type(pin['bytes']) is not int or pin['bytes'] != len(data):
            raise ValueError('duplicate, missing or mismatched completed logical file')
        logical_total += len(data)
        if logical_total > MAX_TOTAL_BYTES:
            raise ValueError('completed logical files exceed total byte bound')
        names.add(pin['path']); used.add(pin['sha256']); files.append((pin['path'], data))
    if used != set(decoded):
        raise ValueError('completed capture contains unreferenced content')
    return value['selection'], _Reader(tuple(files))


def _authority(reg, registration, reader):
    inputs = reg['inputs']
    pins = [inputs[key] for key in ('bundle', 'chunk_manifest', 'source_manifest', 'context')
            if inputs[key] is not None]
    pins += [reg['routing']['artifact']]
    pins += [pin for pin in (inputs['profile']['vocabulary'], reg['runtime']['config']) if pin]
    pins += inputs['full_schema']['sources'] + inputs['core_schema']['sources']
    files = {reg['registration_path']: registration}
    if reader.raw(reg['registration_path']) != registration:
        raise ValueError('captured registration differs from selected authority')
    for pin in pins:
        raw = reader.raw(pin['path'])
        if sg.file_pin(Path(pin['path']), raw) != pin:
            raise ValueError('captured authority bytes differ from registration')
        files[pin['path']] = raw
    return sg._capture_bytes(registration, reg, files, captured_only=True)


def _json(raw, label):
    from .audit_omissions import _mapping
    return _mapping(raw, label, limit=MAX_FILE_BYTES, json_only=True)


def _record(raw, label):
    from .audit_omissions import _mapping
    return _mapping(raw, label, limit=MAX_FILE_BYTES)


def _snapshot(spec, name):
    from .snapshot_store import _portable_entry
    pin = _portable_entry(spec._record, spec.project, spec.project + '_' + name)
    if pin is None:
        raise UsageLedgerError('completed capture lacks attested snapshot: ' + name)
    raw = spec._reader.raw(pin['path'])
    if sg.sha(raw) != pin['sha256']:
        raise UsageLedgerError('completed snapshot bytes differ')
    return raw, pin



def _live_path_display(spec):
    from . import provenance, chunking
    return {'full_path': str(spec.full_path), 'bundle_path': str(spec.bundle),
            'source_manifest': str(spec.manifest) if spec.manifest is not None else None,
            'core_source': provenance.repo_relative(spec.full_path),
            'bundle_name': chunking.canonical_name(spec.bundle, source_manifest=spec.manifest)}


def _check_path_display(display, paths, registration, reader):
    sg._exact(display, {'full_path', 'bundle_path', 'source_manifest', 'core_source', 'bundle_name'}, 'completed path display')
    inputs = registration['inputs']
    if (display['full_path'] != paths['full'] or display['bundle_path'] != inputs['bundle']['path']
            or display['source_manifest'] != (inputs['source_manifest']['path'] if inputs['source_manifest'] else None)):
        raise ValueError('completed path display differs from logical input/output identities')
    for key in ('core_source', 'bundle_name'):
        if type(display[key]) is not str or not display[key] or any(c in display[key] for c in '\r\n\0'):
            raise ValueError('invalid completed path display spelling')
    manifest = _record(reader.raw(inputs['chunk_manifest']['path']), 'captured chunk manifest')
    if display['bundle_name'] != manifest['bundle']:
        raise ValueError('completed bundle display differs from captured manifest')
    # The core source display is historical producer metadata. Both original
    # and final core bytes are independently reconstructed from it in _ordinary;
    # it is not an attestation of a filesystem that is no longer available.
    return copy.deepcopy(display)


FORM_KEY = 'source_heading_form_measurement'


def measure_form(spec):
    """Persist the instrument actually consumed by this selected measurement."""
    from . import grounding, usage_ledger as ledger
    if type(spec) is not api.RunSpec or spec._replay_only or spec.shared_generation_version != 2:
        raise ValueError('form capture requires live selected v2')
    result, observation, records = grounding._form_facts_with_naming(spec.full_path, spec.core_path)
    if any(records.get(path) is None for path in (spec.full_path, spec.core_path)):
        raise ValueError('selected form measurement requires both final records')
    raw = observation['raw']
    naming = {'path': observation['path'], 'present': raw is not None,
              'sha256': sg.sha(raw) if raw is not None else None,
              'bytes': len(raw) if raw is not None else 0,
              'base64': base64.b64encode(raw).decode('ascii') if raw is not None else None}
    data = ledger._read(spec)
    data[FORM_KEY] = {'generation_id': data['generation_id'],
        'registration_sha256': sg.sha(sg._context_capture(spec).registration),
        'full': sg.file_pin(spec.full_path, records[spec.full_path]), 'core': sg.file_pin(spec.core_path, records[spec.core_path]),
        'naming': naming, 'result': copy.deepcopy(result)}
    ledger._write(spec, data)
    return result


def _captured_form(spec, full, core, rules):
    from . import grounding
    row = spec._ledger.get(FORM_KEY)
    sg._exact(row, {'generation_id', 'registration_sha256', 'full', 'core', 'naming', 'result'}, 'completed form measurement')
    for key in ('full', 'core'):
        sg._exact(row[key], {'path', 'sha256', 'bytes'}, 'completed measured record pin')
        if type(row[key]['bytes']) is not int:
            raise ValueError('completed measured byte count must be an integer')
    if (row['generation_id'] != spec._ledger['generation_id']
            or row['registration_sha256'] != sg.sha(spec._captured_authority.registration)
            or row['full'] != sg.file_pin(spec.full_path, full.encode())
            or row['core'] != sg.file_pin(spec.core_path, core.encode())):
        raise UsageLedgerError('completed form measurement identity differs')
    naming = row['naming']
    sg._exact(naming, {'path', 'present', 'sha256', 'bytes', 'base64'}, 'completed naming observation')
    path = sg._path(naming['path'], 'completed naming instrument')
    if path.parts[-3:] != ('data', 'preprocessed', 'source_manifest.yaml') or type(naming['present']) is not bool:
        raise ValueError('completed naming instrument does not use the actual default locator')
    if type(naming['bytes']) is not int:
        raise ValueError('completed naming byte count must be an integer')
    raw = None
    if naming['present']:
        if (type(naming['base64']) is not str or type(naming['bytes']) is not int
                or not 0 <= naming['bytes'] <= grounding.MAX_CAPTURED_NAMING_BYTES
                or len(naming['base64']) > 4 * ((grounding.MAX_CAPTURED_NAMING_BYTES + 2) // 3)):
            raise ValueError('completed naming instrument exceeds byte bound')
        raw = base64.b64decode(naming['base64'], validate=True)
        if len(raw) != naming['bytes'] or sg.sha(raw) != naming['sha256']:
            raise ValueError('completed naming instrument bytes differ')
    elif naming != {'path': str(path), 'present': False, 'sha256': None, 'bytes': 0, 'base64': None}:
        raise ValueError('completed absent naming instrument has contradictory bytes')
    result = grounding._form_facts([(spec.full_path, grounding._form_text(full.encode())),
        (spec.core_path, grounding._form_text(core.encode()))], spec.full_path,
        rules.slots, rules=rules, naming=grounding._naming_from_bytes(raw))
    if sg.canonical(result) != sg.canonical(row['result']):
        raise UsageLedgerError('completed form differs from consumed naming bytes')
    return result


def _spec(selection, reader):
    from . import usage_ledger as ledger
    sg._exact(selection, {'run', 'render_spec', 'paths', 'registration', 'ledger', 'snapshot_index',
                          'reasoning', 'record_schema', 'record_schema_sources', 'abandoned', 'path_display'}, 'completed selection')
    sg._exact(selection['run'], {'project', 'method', 'label'}, 'completed run')
    sg._exact(selection['paths'], {'full', 'core', 'report', 'provenance', 'receipt'}, 'completed paths')
    for path in [*selection['paths'].values(), selection['registration'], selection['ledger'],
                 selection['snapshot_index'], selection['reasoning'], selection['record_schema']]:
        sg._path(path, 'completed selection path')
    raw = reader.raw(selection['registration'])
    reg = sg.parse_registration(raw)
    if reg['format'] != sg.ROUTING_FORMAT or reg['registration_path'] != selection['registration']:
        raise ValueError('completed capture requires the exact v2 registration')
    spec = _CompletedSpec.from_render_spec(selection['render_spec'], **selection['run'])
    spec._paths = copy.deepcopy(selection['paths'])
    spec._captured_path_display = _check_path_display(selection['path_display'], selection['paths'], reg, reader)
    spec._reader = reader
    spec._captured_authority = _authority(reg, raw, reader)
    spec._record = _record(reader.raw(spec.provenance_path), 'completed provenance')
    if spec.render_spec() != selection['render_spec']:
        raise ValueError('completed render metadata is not a closed exact round trip')
    if reg['run'] != {key: getattr(spec, key) for key in ('project', 'arm', 'method', 'label')}:
        raise ValueError('completed run differs from its registration')
    inputs = reg['inputs']
    if (str(spec.bundle) != inputs['bundle']['path'] or str(spec.chunk_manifest) != inputs['chunk_manifest']['path']
            or (str(spec.manifest) if spec.manifest else None) != (inputs['source_manifest']['path'] if inputs['source_manifest'] else None)
            or {k: inputs['profile'][k] for k in ('name', 'basis')} != {'name': spec.profile, 'basis': spec.profile_basis}):
        raise ValueError('completed render inputs differ from registration')
    if str(ledger.ledger_path(spec)) != selection['ledger']:
        raise ValueError('completed ledger is not the run-owned ledger')
    spec._ledger = ledger._validate_data(spec, _json(reader.raw(selection['ledger']), 'completed ledger'), selection['ledger'])
    data = spec._ledger
    if data.get('pending_call') is not None or data.get('pending_snapshot_activation') is not None or data.get('evidence_refusals'):
        raise UsageLedgerError('completed capture contains pending or refused execution')
    if data['input_identity'] != spec.input_identity():
        raise UsageLedgerError('completed original input/renderer identity differs')
    record = spec._record
    if ((record.get('run') or {}).get('generation_id') != data['generation_id']
            or not ledger.record_matches(spec, record.get('run')) or record.get('api_usage') != data['rows']):
        raise UsageLedgerError('completed provenance generation/accounting differs')
    if (record.get('prompts') or {}).get('request', {}).get('spec') != selection['render_spec']:
        raise ValueError('provenance does not bind completed render metadata')
    index = _json(reader.raw(selection['snapshot_index']), 'completed snapshot index')
    if (index.get('version') != 1 or index.get('generation_id') != data['generation_id']
            or index.get('run_identity') != data['identity'] or index.get('input_identity') != data['input_identity']):
        raise UsageLedgerError('completed snapshot generation/input differs')
    entries = record.get('intermediates')
    if type(entries) is not list:
        raise UsageLedgerError('completed provenance lacks its explicit snapshot roster')
    expected = []
    uids = {row['usage_id'] for row in data['rows']}
    for entry in entries:
        if entry.get('generation_id') != data['generation_id'] or not entry.get('phase'):
            raise UsageLedgerError('completed snapshot has no unambiguous generation/phase')
        if entry.get('usage_id') is not None and entry['usage_id'] not in uids:
            raise UsageLedgerError('completed snapshot claims unaccounted delivery')
        raw = reader.raw(entry['path'])
        if sg.sha(raw) != entry['sha256']:
            raise UsageLedgerError('completed snapshot pin differs')
        expected.append({'name': entry['phase'], 'path': entry['path'], 'sha256': entry['sha256'],
                         **({'usage_id': entry['usage_id']} if entry.get('usage_id') else {})})
    if index.get('snapshots') != expected:
        raise UsageLedgerError('completed snapshot index diverges from provenance chronology')
    spec._originals = {name: _snapshot(spec, suffix)[0] for name, suffix in
                       (('original_full', 'full.yaml'), ('original_core', 'core.yaml'))}
    spec._effective_receipt = reader.raw(selection['paths']['receipt'])
    spec._reasoning = [_json(line.encode(), 'completed reasoning') for line in reader.raw(selection['reasoning']).decode().splitlines() if line.strip()]
    return spec


def _receipt(spec):
    from . import receipt_completion as rc
    data, reader = spec._ledger, spec._reader
    state = data.get('receipt_completion')
    if type(state) is not dict or state.get('state') != 'complete':
        raise UsageLedgerError('captured receipt continuation is not terminal complete')
    inputs = reader.load(state['inputs'])
    payload = reader.load(state['request'])
    transcript = reader.load(inputs['transcript_pin'])
    if transcript != inputs['transcript'] or inputs['transcript_pin'] != data.get('receipt_completion_transcript'):
        raise UsageLedgerError('captured receipt transcript differs')
    rc._check_request(inputs, payload, state['requested_paths'],
        reader.load(state['context']) if state['requested_paths'] else state.get('context'),
        input_identity=spec.input_identity(), registration_identity=rc.registration_identity(spec), reg=rc.registration(spec))
    selected = spec._captured_authority.document()['inputs']
    expected_schema = {'sources': [{'name': n, 'path': str(p), 'sha256': sg.sha(raw), 'text': raw.decode()}
                                  for n, p, raw in spec._captured_authority.full_schema.sources]}
    if (inputs['schema'] != expected_schema or inputs['bundle'].encode() != spec._captured_authority.raw(selected['bundle']['path'])
            or inputs['manifest'].encode() != spec._captured_authority.raw(selected['chunk_manifest']['path'])
            or inputs['record'].encode() != spec._originals['original_full']):
        raise UsageLedgerError('captured receipt inputs differ from original authority')
    sealed = data.get('receipt_completion_full') or {}
    if (sealed.get('full_sha256') != sg.sha(inputs['record'].encode())
            or sealed.get('receipt_sha256') != sg.sha(inputs['receipt'].encode())
            or sealed.get('transcript') != inputs['transcript_pin']
            or sealed.get('usage_id') != transcript.get('usage_id')):
        raise UsageLedgerError('captured receipt inputs differ from sealed full boundary')
    response = reader.load(state['response'])
    rc._check_accounted_response(state, response, data['rows'])
    result = rc._checked_result(inputs, response, reader.load(state['result']))
    if (result['state'] != 'answers_complete' or result['receipt_yaml'].encode() != spec._effective_receipt
            or result['receipt_after_sha256'] != sg.sha(spec._effective_receipt)):
        raise UsageLedgerError('captured effective receipt is not the checked complete result')
    lines, failure = _validator_lines(inputs['record'].encode(), _snapshot(spec, 'full.yaml')[1]['path'],
                                      spec._captured_authority.full_schema, 'Dataset')
    if failure or lines is None or lines:
        raise UsageLedgerError('captured original full fails receipt schema validation')
    spec._receipt_outcome = {**result, 'journal': copy.deepcopy(state), 'response_sha256': state['response']['sha256']}
    return spec._receipt_outcome


def _typed(spec):
    from . import typed_audit_runtime as runtime, typed_audit as typed
    state = spec._ledger.get('typed_audit')
    packet, workers, omission, assembly, _, _ = runtime._rebuild(spec, state, record=spec._record, _reader=spec._reader)
    if (state.get('state') not in ('assembled', 'accepted') or assembly is None
            or len(state['stages']) != len(state['roster'])
            or any(row['state'] != 'checked' for row in state['stages'])
            or spec._reader.load(state.get('assembly')) != assembly):
        raise UsageLedgerError('captured typed audit is not completely checked')
    body = typed._unblob(assembly['audit'], typed.audit_grammar.MAX_BYTES)
    snapshot, pin = _snapshot(spec, 'audit.json')
    integration = [row for row in state['stages'] if row['selection']['phase'] == runtime.INTEGRATION_PHASE]
    if len(integration) != 1 or pin.get('usage_id') != integration[0]['usage_id'] or snapshot != body:
        raise UsageLedgerError('captured audit snapshot differs from its checked integration')
    spec._audit = body.decode()
    return {'protocol': 'shared_generation_v2', 'generation_id': spec._ledger['generation_id'],
        'assembly_sha256': assembly['sha256'], 'audit_sha256': sg.sha(body),
        'acceptance': typed.check(assembly, derivations=typed.DerivationCache()),
        'authority': spec._captured_authority.identity(),
        'scientific_support': 'unverified evaluator declarations'}


def _roster(selection, reader):
    """Fixed selected roots plus the explicit attested snapshot roster."""
    reg = sg.parse_registration(reader.raw(selection['registration']))
    authority = _authority(reg, reader.raw(selection['registration']), reader)
    names = {name for name, _ in authority.files}
    names.update(selection['paths'].values())
    names.update(selection[key] for key in ('ledger', 'snapshot_index', 'reasoning', 'record_schema'))
    names.update(pin['path'] for pin in selection['record_schema_sources'])
    if selection['abandoned'] is not None:
        sg._path(selection['abandoned'], 'completed abandoned journal')
        names.add(selection['abandoned'])
    index = _json(reader.raw(selection['snapshot_index']), 'completed snapshot index')
    directory = Path(selection['paths']['provenance']).parent / 'intermediate'
    for row in index['snapshots']:
        path = sg._path(row['path'], 'completed snapshot')
        if path.parent != directory:
            raise ValueError('completed snapshot lies outside its explicit run directory')
        names.add(str(path))
    return names


def capture_completed(spec):
    """Export only a newly rechecked terminal v2 closure, without new calls."""
    from . import receipt_completion as rc, typed_audit_runtime as typed, usage_ledger as ledger, snapshot_store, provenance
    if type(spec) is not api.RunSpec or spec._replay_only or spec.shared_generation_version != 2:
        raise ValueError('capture requires a live selected v2 specification')
    authority = sg.assert_current(spec)
    record = _record(spec.provenance_path.read_bytes(), 'completed provenance')
    if api._progress_path(spec).exists():
        raise UsageLedgerError('completed export requires no outstanding progress')
    rc.recover(spec)
    checked = typed.completion_check(spec, record=record)
    if record.get('shared_generation') != checked:
        raise UsageLedgerError('completed record differs from reconstructed shared completion')
    selection = {'run': {key: getattr(spec, key) for key in ('project', 'method', 'label')},
        'render_spec': spec.render_spec(),
        'paths': {key: str(getattr(spec, key + '_path')) for key in ('full', 'core', 'report', 'provenance')},
        'registration': authority.document()['registration_path'], 'ledger': str(ledger.ledger_path(spec)),
        'snapshot_index': str(snapshot_store.index_path(spec.metadata_dir, spec.project)),
        'reasoning': str(api._reasoning_path(spec)), 'record_schema': str(provenance.record_schema_path().absolute())}
    from .schema_snapshot import capture_schema
    record_snapshot = capture_schema(provenance.record_schema_path(), strict=True)
    selection['record_schema_sources'] = [sg.file_pin(path, raw) for _, path, raw in record_snapshot.sources]
    selection['paths']['receipt'] = str(api._receipt_path(spec))
    selection['path_display'] = _live_path_display(spec)
    abandoned = ledger.abandoned_journal_path(spec)
    selection['abandoned'] = str(abandoned) if abandoned.exists() else None
    files = dict(authority.files)
    for _, path, raw in record_snapshot.sources:
        files[str(path)] = raw
    roots = [*selection['paths'].values(), *(selection[k] for k in ('ledger', 'snapshot_index', 'reasoning', 'record_schema'))]
    def read(path):
        if path in files:
            return
        target = Path(path)
        if target.is_symlink() or not target.is_file() or target.stat().st_size > MAX_FILE_BYTES:
            raise ValueError('completed capture requires bounded ordinary files')
        with target.open('rb') as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('completed file grew beyond capture bound')
        files[path] = raw
        if len(files) > MAX_FILES or sum(map(len, files.values())) > MAX_TOTAL_BYTES:
            raise ValueError('completed capture exceeds aggregate bound')
    if selection['abandoned'] is not None:
        roots.append(selection['abandoned'])
    for name in roots:
        read(name)
    for name in _roster(selection, _Reader(tuple(files.items()))):
        read(name)
    value = {'format': FORMAT, 'selection': selection,
        'files': [sg.file_pin(Path(name), raw) for name, raw in sorted(files.items())],
        'blobs': {sg.sha(raw): base64.b64encode(raw).decode('ascii') for raw in files.values()}}
    raw = sg.canonical(value)
    # This is the same captured-only checker as relocated public readback.
    # Prior live success cannot authorize a torn assembled export.
    recheck_completed(raw)
    return raw


def _captured_json_schema(snapshot, *, cls, closed=True, descendants=True):
    """Run the installed generator on its original captured import view.

    Generator constructs a root-only SchemaView before _init_namespaces. This
    fixed instance hook installs the closed reader before any import lookup;
    all namespace, inheritance, precedence and generation code stays inherited.
    No flattening/merge policy or process-global loader substitution is used.
    """
    from linkml.generators.jsonschemagen import JsonSchemaGenerator
    from .schema_view import captured_view
    with captured_view(snapshot) as view:
        class CapturedGenerator(JsonSchemaGenerator):
            def _init_namespaces(self):
                self.schemaview = view
                self.schema = view.schema
                return super()._init_namespaces()
        return CapturedGenerator(view.schema, top_class=cls, not_closed=not closed,
            mergeimports=True, include_range_class_descendants=descendants).generate()


@contextmanager
def _captured_validator(snapshot, plugins):
    from linkml.validator import Validator
    from linkml.validator.validation_context import ValidationContext
    from .schema_view import captured_view
    import jsonschema
    with captured_view(snapshot) as view:
        class CapturedContext(ValidationContext):
            def _get_target_class(self, target_class=None):
                self._schema_view = view
                return super()._get_target_class(target_class)

            def json_schema_validator(self, *, closed, include_range_class_descendants, path_override=None):
                if path_override is not None:
                    raise ValueError('captured validation does not accept a schema path override')
                key = (closed, include_range_class_descendants)
                if key not in self._validators:
                    schema = _captured_json_schema(snapshot, cls=self.target_class, closed=closed,
                        descendants=include_range_class_descendants)
                    klass = jsonschema.validators.validator_for(schema, default=jsonschema.Draft7Validator)
                    self._validators[key] = klass(schema, format_checker=klass.FORMAT_CHECKER)
                return self._validators[key]

        class CapturedValidator(Validator):
            def _context(self, target_class=None):
                if target_class not in self._contexts:
                    context = CapturedContext(self._schema, target_class)
                    context._validators = {}
                    self._contexts[target_class] = context
                return self._contexts[target_class]
        validator = CapturedValidator(view.schema, validation_plugins=plugins, strict=False)
        validator._contexts = {}
        try:
            yield validator
        finally:
            validator._contexts.clear()


def _validator_lines(raw, logical_path, snapshot, cls):
    """Actual LinkML CLI plugin/loader semantics, with already captured bytes."""
    import io
    import traceback
    import yaml
    from linkml.validator.plugins import JsonschemaValidationPlugin
    from linkml.validator.loaders.passthrough_loader import PassthroughLoader
    from linkml.validator.report import Severity
    stream = io.StringIO(raw.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n'))
    stream.name = str(logical_path)
    def instances():
        for document in yaml.safe_load_all(stream):
            if isinstance(document, list):
                yield from document
            else:
                yield document
    emitted, errors = [], 0
    try:
        with _captured_validator(snapshot, [JsonschemaValidationPlugin(closed=True)]) as validator:
            for result in validator.iter_results_from_source(PassthroughLoader(instances()), cls):
                emitted.append(f'[{result.severity.value}] [{logical_path}/{result.instance_index}] {result.message}')
                errors += result.severity == Severity.ERROR
    except Exception:
        trace = traceback.format_exc()
        if api._validator_did_not_run(trace, Path(logical_path)):
            return None, 'linkml-validate did not run: ' + trace.strip()[-300:]
        return emitted + api._crash_diagnostic(trace), None
    return emitted if errors else [], None


def _normalization_rules(spec):
    from . import identifiers, grounding
    from .schema_view import captured_view
    captured = spec._captured_authority
    doc = _record(captured.full_schema.sources[0][2], 'captured normalization schema')
    multivalued = set()
    with captured_view(captured.full_schema) as full, captured_view(captured.core_schema) as core:
        for view in (full, core):
            multivalued.update(api._multivalued_of(view))
        slots = frozenset(identifiers.uriorcurie_slots_of(full))
        persons = frozenset(identifiers.person_slots_of(full))
        known = {str(slot.name) for slot in full.class_induced_slots('Dataset')}
    bases = tuple(grounding.declared_bases_of(doc))
    rules = {'enums': api._enum_aliases_of(doc), 'multivalued': multivalued,
             'identifiers': (slots, tuple((b, p) for b, p in bases if b.endswith(('/', '#', '_', ':')))),
             'persons': persons}
    spec._rules, spec._known_slots = rules, known
    return rules


def _normalise(spec, text, phase=None):
    return api.normalise_record_text(text, phase=phase, _rules=spec._rules)


def _settings(spec):
    runtime = spec._captured_authority.document()['runtime']
    return {'name': runtime['model'], 'temperature': runtime['temperature'],
            'temperature_applies': api.accepts_temperature(runtime['model']),
            'thinking': runtime['thinking'], 'effort': runtime['effort']}


def _body(spec, response, phase):
    if response['stop_reason'] == 'max_tokens':
        raise ValueError('completed delivered body is truncated')
    text = response['text']
    if phase == 'full':
        text, receipt = api.split_receipt(text)
        if receipt is None:
            raise ValueError('completed full response lacks required receipt')
    kind = 'md' if phase in ('report', 'report_after_repair', 'report_regate') else 'yaml'
    body = api._extract(text, kind, _slots=spec._known_slots)
    if kind == 'yaml':
        body = api.stamp_provenance_header(_normalise(spec, body, phase), _settings(spec))
    return body


def _core(spec, full, *, complete):
    raw = sg._core_text(spec._captured_authority, full.encode(), spec.full_path, phase4_complete=complete,
                       _source_display=spec._captured_path_display['core_source'])[0]
    return api.stamp_provenance_header(_normalise(spec, raw, 'reconcile_core' if complete else 'core'), _settings(spec))


def _report_check(spec, report, full, core):
    from . import report_claims
    from .schema_view import captured_view
    with captured_view(spec._captured_authority.full_schema) as fv, captured_view(spec._captured_authority.core_schema) as cv:
        return report_claims._check_report_text(report, _record(full.encode(), 'report full'),
            _record(core.encode(), 'report core'), report_claims.declared_slots_of(fv, cv),
            snapshot=_record(spec._originals['original_full'], 'report original full'),
            dispositions_expected=True, ranges=report_claims.declared_ranges_of(cv))


def _evidence_check(spec, report, full, core):
    from . import evidence_assertions as evidence
    chunks, pins = sg.source_chunks(spec)
    metadata = api.source_metadata_authority(spec)
    originals = {key: value.decode() for key, value in spec._originals.items()}
    audit = evidence.load_json(spec._audit)
    out = evidence.check_audit(audit, artifacts=originals, chunks=chunks,
                              protocol_version=evidence.protocol_for_renderer(spec.render_version), **metadata)
    out['findings'] += evidence.check_relationship_removals(audit,
        evidence.load_record(originals['original_full']), evidence.load_record(full),
        protocol_version=evidence.protocol_for_renderer(spec.render_version), original_raw=originals['original_full'])
    final = evidence.check_report(report, artifacts={**originals, 'final_full': full, 'final_core': core},
        chunks=chunks, protocol_version=evidence.protocol_for_renderer(spec.render_version), **metadata)
    out['assertions_checked'] += final['assertions_checked']
    out['findings'] += final['findings']
    if 'source_review_final' in final:
        out['source_review_final'] = final['source_review_final']
    return out


def _ordinary(spec):
    from . import source_heading_admission as admission, receipt_completion as rc
    from .duplicate_keys import find_duplicate_keys, findings
    import yaml
    state, checked = admission._recheck(spec, spec._ledger, _reader=spec._reader)
    _normalization_rules(spec)
    original_full = spec._originals['original_full'].decode()
    original_core = spec._originals['original_core'].decode()
    if _core(spec, original_full, complete=False) != original_core:
        raise UsageLedgerError('original core differs from actual deterministic derivation')
    current_full = current_core = current_report = None
    full_request = full_response = None
    seen = []
    original_uid = _snapshot(spec, 'full.yaml')[1].get('usage_id')
    original_seen = False
    selected_receipt = None
    transcript_seen = False
    for row, saved in checked:
        phase = row['phase']
        response = spec._reader.load(row['response'])
        if phase == 'full':
            if any(p not in ('full',) for p in seen):
                raise UsageLedgerError('full generation appears after a later phase')
            request = api.build_phase(spec, 'full', carry={})
            full_request, full_response = request, response
        elif phase == 'full_readdress':
            if full_request is None or not seen or seen[-1] != 'full':
                raise UsageLedgerError('readdress has no immediately preceding full exchange')
            full_text, receipt_text = api.split_receipt(full_response['text'])
            parsed_full = yaml.safe_load(_normalise(spec, api._extract(full_text, 'yaml', _slots=spec._known_slots)))
            receipt = yaml.safe_load(api._extract_receipt(receipt_text))
            unresolved = api.unresolved_receipt_slots(parsed_full, receipt)
            if not original_seen or not unresolved or selected_receipt is None:
                raise UsageLedgerError('readdress lacks its selected original unresolved receipt')
            request = api.build_readdress(full_request, full_response['text'], unresolved)
            # The live best-effort phase keeps the original bytes on a
            # truncated, malformed or inapplicable answer. It still accounts
            # for the complete exchange, which remains the sealed transcript.
            if response['stop_reason'] != 'max_tokens':
                try:
                    api.apply_readdress(receipt, parsed_full, api._extract_readdress(response['text']))
                    selected_receipt = yaml.safe_dump(receipt, sort_keys=False, allow_unicode=True, width=10000)
                except Exception:
                    pass
        elif phase == 'reconcile_full':
            if current_full is None or any(p in seen for p in ('report', 'repair_full', 'report_regate')):
                raise UsageLedgerError('reconcile request occurs outside its selected phase')
            if not original_seen:
                raise UsageLedgerError('reconcile does not follow the exact selected original full delivery')
            carry = {'Completed full record': original_full, 'Completed core record': original_core,
                     'Audit findings': spec._audit}
            request = api.build_phase(spec, phase, carry={key: carry[key] for key in api.PHASE_NEEDS[phase]})
        elif phase in ('report', 'report_after_repair', 'report_regate'):
            if current_full is None or 'reconcile_full' not in seen:
                raise UsageLedgerError('report has no reconciled records')
            current_core = _core(spec, current_full, complete=True)
            carry = {'Original full record': original_full, 'Original core record': original_core,
                'Reconciled full record': current_full, 'Completed core record': current_core, 'Audit findings': spec._audit}
            request = api.build_phase(spec, 'report', carry={key: carry[key] for key in api.PHASE_NEEDS['report']})
            if phase == 'report_after_repair' and 'repair_full' not in seen:
                raise UsageLedgerError('report-after-repair has no actual repair')
            if phase == 'report_regate':
                if current_report is None or 'report_regate' in seen:
                    raise UsageLedgerError('regate has no original report or was repeated')
                reading = _report_check(spec, current_report, current_full, current_core)
                contradictions = list(reading.get('findings') or []) + _evidence_check(spec, current_report, current_full, current_core)['findings']
                if not reading.get('disposition_rows'):
                    contradictions.append({'kind': 'dispositions_table_missing', 'detail': api.DISPOSITIONS_MISSING_DETAIL})
                if not contradictions or _snapshot(spec, 'report_before_regate.md')[0].decode() != current_report:
                    raise UsageLedgerError('regate does not match actual prior report/findings')
                api._append_regate(request, spec, current_report, contradictions)
        elif phase == 'repair_full':
            if current_full is None or current_report is None:
                raise UsageLedgerError('repair lacks its completed original pipeline')
            errors, failure = _validator_lines(current_full.encode(), spec.full_path, spec._captured_authority.full_schema, 'Dataset')
            if failure:
                raise UsageLedgerError('captured repair validator did not run: ' + failure)
            errors += findings(find_duplicate_keys(current_full))
            if not errors:
                raise UsageLedgerError('repair lacks actual validator findings')
            request = api.build_repair('full', current_full, errors, profile=spec.profile_obj,
                                      _captured_digest=sg.digest_text(spec, 'Dataset'))
            request.messages[0]['content'].insert(-1, {'type': 'text', 'text': sg.generation_context(spec)})
            request.messages[0]['content'].insert(-1, {'type': 'text', 'text': sg.routing_context(spec)})
        else:
            raise UsageLedgerError('unrecognized model phase in selected completed route: ' + str(phase))
        payload = rc.request_payload(request, _settings(spec), {'max_output_tokens': saved['payload']['max_tokens']})
        if payload != saved['payload']:
            raise UsageLedgerError('completed ordinary whole wire differs from reconstructed phase/carry')
        seen.append(phase)
        if phase in ('full', 'full_readdress'):
            inputs = spec._reader.load(spec._ledger['receipt_completion']['inputs'])
            transcript = inputs['transcript']
            if row['usage_id'] == transcript.get('usage_id'):
                expected = {'phase': phase, 'system': request.system, 'messages': request.messages,
                    'cached_blocks': request.cached_blocks, 'response': response['text'], 'usage_id': row['usage_id']}
                if transcript != expected:
                    raise UsageLedgerError('sealed transcript differs from its actual ordinary exchange')
                transcript_seen = True
        if phase == 'full_readdress':
            continue
        try:
            body = _body(spec, response, phase)
        except (ValueError, RuntimeError):
            if phase in ('report', 'report_after_repair', 'report_regate'):
                raise
            continue  # accounted unusable response; only a later accepted snapshot can complete
        if phase == 'full':
            current_full = body
        elif phase in ('reconcile_full', 'repair_full'):
            current_full = body
        else:
            current_report = body
        if phase in ('full', 'reconcile_full', 'report'):
            matches = [entry for entry in spec._record['intermediates']
                       if entry['phase'] == spec.project + '_' + phase + ('.md' if phase == 'report' else '.yaml')
                       and entry.get('usage_id') == row['usage_id']]
            # Earlier unusable attempts do not claim an accepted phase snapshot.
            if matches and (len(matches) != 1 or spec._reader.raw(matches[0]['path']).decode() != body):
                raise UsageLedgerError('ordinary response differs from its attributed phase snapshot')
        if phase == 'full' and row['usage_id'] == original_uid:
            if body != original_full:
                raise UsageLedgerError('original full differs from its actual delivered normalized response')
            original_seen = True
            selected_receipt = api._extract_receipt(api.split_receipt(response['text'])[1])
    if not transcript_seen or selected_receipt != spec._reader.load(spec._ledger['receipt_completion']['inputs'])['receipt']:
        raise UsageLedgerError('sealed original receipt/transcript differs from actual delivered exchanges')
    if (not seen or current_full is None or current_report is None or 'report' not in seen
            or 'reconcile_full' not in seen):
        raise UsageLedgerError('captured ordinary phase sequence is incomplete')
    current_core = _core(spec, current_full, complete=True)
    for key, expected in [('full', current_full), ('core', current_core), ('report', current_report)]:
        if spec._reader.raw(spec._paths[key]).decode() != expected:
            raise UsageLedgerError('completed final ' + key + ' differs from actual phase lineage')
    return admission._completion_check(spec, spec._ledger, _reader=spec._reader)


def _final_checks(spec, selection):
    from . import duplicate_keys, grounding, identifiers, report_claims, provenance, record_schema
    from .d4d_pair_consistency import pair_schema_from_views, validate_pair_data
    from .schema_view import captured_view
    from .schema_snapshot import _capture_schema
    from .run_schema import IdentifierRules
    from linkml.validator import Validator
    import yaml
    full_raw, core_raw, report_raw = (spec._reader.raw(spec._paths[key]) for key in ('full', 'core', 'report'))
    full, core, report = full_raw.decode(), core_raw.decode(), report_raw.decode()
    problems = []
    for raw, path, snapshot, cls in [(full_raw, spec.full_path, spec._captured_authority.full_schema, 'Dataset'),
                                    (core_raw, spec.core_path, spec._captured_authority.core_schema, 'CoreDataset')]:
        dups = duplicate_keys.find_duplicate_keys(raw.decode(errors='replace').replace('\r\n','\n').replace('\r','\n'))
        if dups:
            problems.append({'artifact': str(path), 'class': cls, 'error': duplicate_keys.describe(dups)})
        lines, failure = _validator_lines(raw, path, snapshot, cls)
        if failure:
            raise UsageLedgerError('captured final validator unavailable: ' + failure)
        if lines:
            problems.append({'artifact': str(path), 'class': cls, 'error': ' | '.join(lines[:4])})
    if problems:
        raise UsageLedgerError('captured final records do not validate: ' + sg.canonical(problems).decode())
    evidence = _evidence_check(spec, report, full, core)
    if not evidence.get('checked') or evidence.get('findings'):
        raise UsageLedgerError('captured final evidence/source/relationship checks failed')
    with captured_view(spec._captured_authority.full_schema) as fv, captured_view(spec._captured_authority.core_schema) as cv:
        pair = pair_schema_from_views(fv, cv)
        # The complete selected schema is the generation schema. This is its
        # strict current-pair check, without a historical filesystem ledger.
        paired = validate_pair_data(yaml.safe_load(full), yaml.safe_load(core), pair, schema_moved=False)
        doc = yaml.safe_load(spec._captured_authority.full_schema.sources[0][2])
        rules = IdentifierRules(frozenset(identifiers.declared_prefixes_of(doc)),
            frozenset(identifiers.uriorcurie_slots_of(fv)), frozenset(identifiers.person_slots_of(fv)),
            tuple(grounding.declared_bases_of(doc)))
    # Pair/report/form/grounding findings remain informational, as on execute.
    form = _captured_form(spec, full, core, rules)
    if sg.canonical(form) != sg.canonical(spec._record.get('form')):
        raise UsageLedgerError('completed form differs from its invocation-bound naming measurement')
    ground = grounding._check_run([('full', full), ('core', core)],
        spec._captured_authority.raw(spec._captured_authority.document()['inputs']['bundle']['path']).decode(errors='replace'),
        rules.slots, rules=rules)
    # Provenance uses its separate non-null schema compiler and real plugin.
    schema_path = Path(selection['record_schema'])
    snapshot = _capture_schema(schema_path, lambda path: spec._reader.raw(path), strict=True)
    if [sg.file_pin(path, raw) for _, path, raw in snapshot.sources] != selection['record_schema_sources']:
        raise ValueError('captured provenance schema closure differs')
    raw_schema = spec._reader.raw(schema_path)
    policy = (yaml.safe_load(raw_schema).get('annotations') or {}).get('required_values_non_null', False)
    if type(policy) is not bool:
        raise ValueError('captured provenance non-null policy is not boolean')
    compiled = record_schema._record_policy(_captured_json_schema(snapshot, cls='GenerationRecord'), policy)
    with _captured_validator(snapshot, [record_schema.RecordValidationPlugin(compiled)]) as validation:
        conformance = [r.message for r in validation.validate(spec._record, 'GenerationRecord').results]
    profile_problem = provenance._spec_profile_disagreement(spec._record)
    if profile_problem:
        conformance.append(profile_problem)
    if conformance:
        raise UsageLedgerError('captured provenance does not conform: ' + '; '.join(conformance[:5]))
    return {'validation_problems': problems, 'provenance_conformance': conformance,
            'evidence_assertions': evidence, 'report': _report_check(spec, report, full, core),
            'pair': {'ran': True, 'consistent': paired.passed, 'errors': len(paired.errors), 'warnings': len(paired.warnings)},
            'grounding': ground, 'form': form}


def recheck_completed(raw):
    """Reconstruct a complete selected v2 run from its immutable byte closure."""
    selection, reader = _decode(raw)
    if set(name for name, _ in reader.files) != _roster(selection, reader):
        raise ValueError('completed logical file roster is incomplete or contains extra files')
    spec = _spec(selection, reader)
    receipt = _receipt(spec)
    shared = _typed(spec)
    shared['routing'] = _ordinary(spec)
    if spec._record.get('shared_generation') != shared:
        raise UsageLedgerError('completed shared report differs from reconstructed journals')
    _accounting(spec, selection)
    _reasoning(spec)
    _provenance_links(spec, selection)
    checks = _final_checks(spec, selection)
    return {'format': FORMAT, 'complete': True, 'scientific_eligibility': False,
            'scientific_readiness': 'draft/unreviewed', 'generation_id': spec._ledger['generation_id'],
            'registration_sha256': sg.sha(spec._captured_authority.registration),
            'outputs': copy.deepcopy(selection['paths']), 'usage': copy.deepcopy(spec._ledger['rows']),
            'checks': {**checks, 'shared_generation': shared, 'receipt_completion': receipt},
            'basis': 'Captured complete bytes and reconstructed checks; no new calls, admissions, recovery or scientific approval.'}


def completed_path(spec):
    return spec.metadata_dir / (spec.project + '_routing_completed.json')

def publish_completed(spec):
    """Write only after the complete captured closure independently passes."""
    raw = capture_completed(spec)
    destination = completed_path(spec)
    # metadata is already inside shared_write_footprint; recheck authority and
    # aliases immediately before this selected-only publication.
    sg.assert_current(spec)
    if destination.is_symlink():
        raise ValueError('completed capture destination is a symlink')
    if destination.exists() and destination.read_bytes() == raw:
        return sg.file_pin(destination, raw)
    import os
    import tempfile
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.' + destination.name, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return sg.file_pin(destination)


def _reasoning(spec):
    """Same-generation response/accounting join; never repair absent evidence."""
    from . import source_heading_admission as admission, receipt_completion as rc
    responses = []
    for row in spec._ledger[admission.KEY]['rows']:
        response = spec._reader.load(row['response'])
        payload = spec._reader.load(row['request'])['payload']
        responses.append((row['usage_id'], row['phase'], row['attempt'], payload, response))
    state = spec._ledger['receipt_completion']
    if state['requested_paths']:
        responses.append((state['usage_id'], rc.PHASE, 1, spec._reader.load(state['request']), spec._reader.load(state['response'])))
    for row in spec._ledger['typed_audit']['stages']:
        responses.append((row['usage_id'], row['selection']['phase'], 1, spec._reader.load(row['request']), spec._reader.load(row['response'])))
    uids = [row['usage_id'] for row in spec._ledger['rows']]
    if len(set(uids)) != len(uids) or set(uids) != {row[0] for row in responses} or len(responses) != len(uids):
        raise UsageLedgerError('captured responses do not cover exact completed usage')
    current_reasoning = [r for r in spec._reasoning if r.get('generation_id') == spec._ledger['generation_id']
                         and not api._foreign_usage_identity(spec, r.get('run_identity') or r)]
    if len(current_reasoning) != len(uids):
        raise UsageLedgerError('completed reasoning does not cover exact accounted calls')
    for uid, phase, attempt, payload, response in responses:
        matching = [r for r in current_reasoning if r.get('usage_id') == uid]
        if len(matching) != 1:
            raise UsageLedgerError('completed response lacks unique reasoning evidence')
        entry = matching[0]
        expected = {'usage_id': uid, 'phase': phase, 'attempt': attempt, 'model': payload['model'],
            'generation_id': spec._ledger['generation_id'], 'run_identity': spec._ledger['identity'],
            'project': spec.project, 'label': spec.label}
        if any(entry.get(k) != v for k, v in expected.items()):
            raise UsageLedgerError('completed reasoning has foreign delivery identity')
        usage = next(row for row in spec._ledger['rows'] if row['usage_id'] == uid)
        if (entry.get('output_tokens') != usage['output_tokens'] or entry.get('stop_reason') != response['stop_reason']
                or entry.get('visible_text_chars') != len(response['text'])
                or entry.get('reasoning_tokens_observed') != usage.get('thinking_tokens')):
            raise UsageLedgerError('completed reasoning contradicts delivered text/accounting')
        if 'reasoning_entry' in response and response['reasoning_entry'] != entry:
            raise UsageLedgerError('completed reasoning differs from captured response evidence')


def _accounting(spec, selection):
    from .usage_ledger import abandoned_journal_path
    name = selection['abandoned']
    boundary = spec._ledger.get('abandoned_journal_offset', 0)
    if name is None:
        if boundary:
            raise UsageLedgerError('captured abandoned journal is missing its recorded prefix')
        rows = []
    else:
        if name != str(abandoned_journal_path(spec)):
            raise UsageLedgerError('captured abandoned journal belongs to another run')
        rows = api._abandoned_rows_bytes(spec._reader.raw(name), boundary, name)
    if api._unrecorded_abandoned_rows(spec, spec._record, rows):
        raise UsageLedgerError('captured abandoned charges lack completed accounting')
    if api._unrecorded_reasoning_entries(spec, spec._record, spec._reasoning):
        raise UsageLedgerError('captured reasoning lacks completed accounting')


def _provenance_links(spec, selection):
    """Recorded hashes remain claims about the same captured bytes."""
    record = spec._record
    if record.get('record_mode') != 'live':
        raise UsageLedgerError('selected completed capture requires its actual live provenance')
    req = record['prompts']['request']
    instruction = spec.instruction.encode()
    if req.get('sha256') != sg.sha(instruction) or req.get('bytes') != len(instruction):
        raise UsageLedgerError('completed instruction pin differs from recorded renderer')
    selected = spec._captured_authority.document()['inputs']
    schema = record['schema']
    if (schema.get('profile') != spec.profile or schema.get('digest_md5') != spec.input_identity()['profile']['digest_md5']
            or schema.get('full_sha256') != selected['full_schema']['sources'][0]['sha256']
            or schema.get('core_sha256') != selected['core_schema']['sources'][0]['sha256']):
        raise UsageLedgerError('completed provenance schema/profile identity differs')
    from . import provenance
    for name, expected_path in (('full', provenance.FULL_SCHEMA), ('core', provenance.CORE_SCHEMA)):
        # The selected live producer stores these exact relative spellings;
        # comparison never resolves a historical path on the current host.
        if schema.get(name + '_path') != str(expected_path):
            raise UsageLedgerError('completed provenance schema path claim differs')
        md5_key = name + '_md5'
        root = selected[name + '_schema']['sources'][0]
        if md5_key in schema and schema[md5_key] != hashlib.md5(spec._captured_authority.raw(root['path'])).hexdigest():
            raise UsageLedgerError('completed provenance schema MD5 claim differs')
    inputs = record['inputs']
    bundle = spec._captured_authority.raw(selected['bundle']['path'])
    if (inputs.get('bundle_path') != selected['bundle']['path']
            or inputs.get('bundle_md5') != hashlib.md5(bundle).hexdigest()
            or inputs.get('bundle_bytes') != len(bundle)
            or any(inputs.get('chunks', {}).get(k) != selected['chunk_manifest'][k] for k in ('path','sha256'))):
        raise UsageLedgerError('completed provenance source identity differs')
    source = selected['source_manifest']
    recorded_source = inputs.get('source_manifest') or {}
    if (recorded_source.get('path') != (source['path'] if source else None)
            or recorded_source.get('md5') != (hashlib.md5(spec._captured_authority.raw(source['path'])).hexdigest() if source else None)):
        raise UsageLedgerError('completed provenance manifest identity differs')
    for key in ('full', 'core', 'report'):
        raw = spec._reader.raw(selection['paths'][key])
        output = record.get('outputs', {}).get(key, {})
        if output.get('path') != selection['paths'][key] or output.get('bytes') != len(raw):
            raise UsageLedgerError('completed provenance output identity differs')
        if key != 'report':
            validated = record.get('validation', {}).get('artifacts', {}).get(key, {})
            if validated != {'path': selection['paths'][key], 'md5': hashlib.md5(raw).hexdigest()}:
                raise UsageLedgerError('completed validation artifact pin differs')
    companion = record.get('companions', {}).get('reasoning_log', {})
    if companion.get('path') != selection['reasoning'] or companion.get('md5') != hashlib.md5(spec._reader.raw(selection['reasoning'])).hexdigest():
        raise UsageLedgerError('completed reasoning companion pin differs')
