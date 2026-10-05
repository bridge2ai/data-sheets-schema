"""Completed authority selection; invented local evidence, no generation calls."""
from copy import deepcopy
from contextlib import nullcontext
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner as api, snapshot_store as snapshots
from data_sheets_schema import usage_ledger as ledger, typed_audit_runtime as runtime
from data_sheets_schema import shared_generation as sg, receipt_completion as receipts
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_generation_manifest_identity import external, offline  # noqa: F401
from tests.test_typed_audit import supplied  # noqa: F401


@pytest.fixture(autouse=True)
def own_imports():
    root = Path(__file__).resolve().parents[1]
    for module in (api, snapshots, ledger, runtime, sg, receipts):
        assert root in Path(module.__file__).resolve().parents


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def saved_originals(spec, full=b'name: Example\n', core=b'name: Example\n'):
    ledger.prepare_usage(spec, resume=True)
    snapshots.activate(spec, fresh=True, completed=False, prior_record={})
    for phase, raw in (('full', full), ('core', core)):
        api._snapshot(spec, f'{spec.project}_{phase}.yaml', raw.decode())
    identity = spec.input_identity()
    record = {'run': {**ledger.run_identity(spec), 'generation_id': ledger.generation_id(spec)},
        'inputs': {'bundle_path': str(spec.bundle), 'bundle_sha256': identity['bundle']['sha256'],
                   'source_manifest': identity['source_manifest'], 'chunks': identity['chunks']},
        'schema': {'profile': identity['profile']['name'], 'digest_md5': identity['profile']['digest_md5']},
        'prompts': {'request': {'sha256': identity['instruction']['sha256']}},
        'intermediates': snapshots.entries(spec)}
    spec.provenance_path.write_text(yaml.safe_dump(record))
    return record


def original_entry(spec, record, phase='core'):
    return next(row for row in record['intermediates'] if row['phase'] == f'{spec.project}_{phase}.yaml')


def inventory(spec):
    return {str(p): p.read_bytes() for p in spec.metadata_dir.rglob('*') if p.is_file()}


@pytest.mark.parametrize('index_state', ['matching', 'missing_phase', 'missing_index', 'other_bytes'])
def test_explicit_originals_outrank_live_index_without_writes(external, index_state):
    record = saved_originals(external)
    index_path = snapshots.index_path(external.metadata_dir, external.project)
    value = json.loads(index_path.read_bytes())
    if index_state == 'missing_phase':
        value['snapshots'] = [r for r in value['snapshots'] if r['name'] != f'{external.project}_core.yaml']
        index_path.write_bytes(sg.canonical(value))
    elif index_state == 'missing_index':
        index_path.unlink()
    elif index_state == 'other_bytes':
        different = external.metadata_dir / 'different-core.yaml'
        different.write_bytes(b'name: Example\n# different raw evidence\n')
        row = next(r for r in value['snapshots'] if r['name'] == f'{external.project}_core.yaml')
        row.update(path=str(different), sha256=sha(different.read_bytes()))
        index_path.write_bytes(sg.canonical(value))
    before = inventory(external)
    assert runtime._originals(external, record=record) == {
        'original_full': b'name: Example\n', 'original_core': b'name: Example\n'}
    if index_state == 'missing_phase':
        with pytest.raises(ledger.UsageLedgerError, match='both immutable'):
            runtime._originals(external)
    elif index_state == 'other_bytes':
        assert runtime._originals(external)['original_core'] != b'name: Example\n'
    assert inventory(external) == before


@pytest.mark.parametrize('change', ['omitted', 'null', 'mapping', 'full', 'core', 'missing_file', 'wrong_hash'])
def test_explicit_incomplete_authority_never_uses_live_alternative(external, change):
    record = saved_originals(external)
    if change == 'omitted': record.pop('intermediates')
    elif change == 'null': record['intermediates'] = None
    elif change == 'mapping': record['intermediates'] = {}
    elif change in ('full', 'core'):
        record['intermediates'].remove(original_entry(external, record, change))
    elif change == 'missing_file':
        original_entry(external, record)['path'] = str(external.metadata_dir / 'never-published.yaml')
    else: original_entry(external, record)['sha256'] = '0' * 64
    before = inventory(external)
    with pytest.raises(ledger.UsageLedgerError):
        runtime._originals(external, record=record)
    assert runtime._originals(external)['original_core'] == b'name: Example\n'
    assert inventory(external) == before


@pytest.fixture
def prepared(external, supplied, monkeypatch):
    """Real snapshots and packet builder; unrelated receipt/registration are fixtures.

    This journal has no admitted stage. Public complete replay is exercised by
    the existing real pipeline's saved-evidence checks and retained external probes.
    """
    record = saved_originals(external, supplied['original_full'])
    raw_inputs = {key: supplied[key] for key in ('bundle', 'manifest', 'context')}
    limits = dict(max_paths=8, max_inventory_bytes=2_000_000, max_workers=16,
        max_request_bytes=4_000_000, max_calls=18, omission_output_tokens=4000,
        aggregate_input_tokens=100000, aggregate_output_tokens=100000)
    document = {'inputs': {'bundle': {'path': 'bundle'}, 'chunk_manifest': {'path': 'manifest'},
        'context': {'path': 'context'}, 'source_manifest': None}, 'audit_limits': limits}
    authority = SimpleNamespace(registration=sg.canonical(document), files=tuple(raw_inputs.items()),
        document=lambda: deepcopy(document), raw=lambda key: raw_inputs[key],
        full_schema=capture_schema(supplied['schema_path']))
    monkeypatch.setattr(sg, 'assert_current', lambda spec: authority)
    monkeypatch.setattr(sg, 'capture', lambda spec: authority)
    monkeypatch.setattr(sg, 'identity', lambda spec: {'fixture': 'unadmitted packet reconstruction'})
    monkeypatch.setattr(sg, 'preflight', lambda spec, settings: authority)
    monkeypatch.setattr(receipts, 'recover', lambda spec: None)
    api._receipt_path(external).write_bytes(supplied['receipt'])
    packet = runtime.prepare_packet(external)
    pin = runtime._save(external, 'packet', packet)
    state = {'format': runtime.STATE, 'generation_id': ledger.generation_id(external),
        'authority': sg.identity(external), 'state': 'prepared', 'packet': pin,
        'roster': runtime.roster(packet), 'settings': {}, 'stages': []}
    runtime._store(external, state)
    return external, record, packet, state


@pytest.mark.parametrize('entrypoint', ['prepare', 'validate', 'rebuild', 'delivered', 'recover', 'complete'])
def test_complete_forwarding_uses_exact_portable_bytes_after_warm_live_cache(prepared, entrypoint):
    spec, record, packet, state = prepared
    assert runtime.prepare_packet(spec) == packet
    alternate = spec.metadata_dir / 'portable-original.yaml'
    alternate.write_bytes(b'name: Example\n# changed but parse-equivalent\n')
    original_entry(spec, record).update(path=str(alternate), sha256=sha(alternate.read_bytes()))
    before = inventory(spec)
    if entrypoint == 'prepare':
        changed = runtime.prepare_packet(spec, record=record)
        assert changed != packet
        assert changed['inputs']['original_core']['sha256'] == sha(alternate.read_bytes())
    else:
        calls = {
            'validate': lambda: runtime._validate_base(spec, state, record=record),
            'rebuild': lambda: runtime._rebuild(spec, state, record=record),
            'delivered': lambda: runtime.recover_delivered(spec, record=record),
            'recover': lambda: runtime.recover(spec, record=record),
            'complete': lambda: runtime.completion_check(spec, record=record),
        }
        with pytest.raises(ledger.UsageLedgerError, match='packet/originals'):
            calls[entrypoint]()
    assert inventory(spec) == before


def test_identical_byte_relocation_preserves_packet_and_unadmitted_recovery(prepared):
    spec, record, packet, state = prepared
    row = original_entry(spec, record)
    alternate = spec.metadata_dir / 'same-original.yaml'
    alternate.write_bytes(Path(row['path']).read_bytes())
    row['path'] = str(alternate)
    before = inventory(spec)
    assert runtime.prepare_packet(spec, record=record) == packet
    assert runtime._validate_base(spec, state, record=record) == packet
    runtime.recover_delivered(spec, record=record)
    assert runtime.recover(spec, record=record) is None
    assert inventory(spec) == before


@pytest.mark.parametrize('completed', [['full', 'core'], 'full', None, {}, False])
def test_explicit_completed_guard_cannot_override_active_or_malformed_progress(prepared, completed):
    spec, record, _, _ = prepared
    before = inventory(spec)
    with pytest.raises(ledger.UsageLedgerError, match='cannot override'):
        runtime.resume_guard(spec, {'completed': completed}, record=record)
    assert inventory(spec) == before


def test_recognition_reuses_exact_raw_candidate_and_detects_later_byte_drift(external):
    record = saved_originals(external)
    context = api._read_resume_record(external, generation=ledger.generation_id(external), progress={})
    assert context.prior_matches and context.parsed == record
    assert context.raw == external.provenance_path.read_bytes()
    assert context.prior_identifier == ledger.generation_id(external)
    api._require_same_resume_record(external, context)
    external.provenance_path.write_bytes(context.raw + b'\n# late change\n')
    with pytest.raises(ledger.UsageLedgerError, match='changed after resume'):
        api._require_same_resume_record(external, context)
    assert context.parsed == record


@pytest.mark.parametrize('shape', ['missing', 'malformed', 'empty', 'scalar', 'foreign_run', 'foreign_generation'])
def test_recognition_preserves_default_nonmatching_states(external, shape):
    record = saved_originals(external)
    if shape == 'missing': external.provenance_path.unlink()
    elif shape == 'malformed': external.provenance_path.write_text('broken: [')
    elif shape == 'empty': external.provenance_path.write_text('')
    elif shape == 'scalar': external.provenance_path.write_text('scalar')
    else:
        record['run']['label' if shape == 'foreign_run' else 'generation_id'] = 'other'
        external.provenance_path.write_text(yaml.safe_dump(record))
    before = inventory(external)
    context = api._read_resume_record(external, generation=ledger.generation_id(external), progress={})
    assert not context.prior_matches
    assert context.foreign_prior is (shape == 'foreign_run')
    assert inventory(external) == before


def test_changed_recorded_inputs_refuse_during_recognition(external):
    record = saved_originals(external)
    record['inputs']['bundle_sha256'] = '0' * 64
    external.provenance_path.write_text(yaml.safe_dump(record))
    before = inventory(external)
    with pytest.raises(ledger.UsageLedgerError, match='input identity changed'):
        api._read_resume_record(external, generation=ledger.generation_id(external), progress={})
    assert inventory(external) == before


def test_legacy_yaml_exception_envelope_keeps_flags_without_accepting_record(external, monkeypatch):
    saved_originals(external)
    before = inventory(external)
    def malformed_input(*args):
        raise yaml.YAMLError('synthetic malformed input while recognizing prior record')
    monkeypatch.setattr(api, '_require_recorded_inputs', malformed_input)
    context = api._read_resume_record(external, generation=ledger.generation_id(external), progress={})
    assert context.prior_matches and context.prior_identifier == ledger.generation_id(external)
    assert not context.foreign_prior and context.foreign_identifier is None
    assert context.parsed is None  # No early candidate or usage/repair seed.
    assert context.raw == external.provenance_path.read_bytes()
    assert inventory(external) == before


def assert_completed_replay_authority(spec):
    """Reuse the existing pipeline test's completed fixture, never generate another.

    All acceptance/readers stay real. Only OS lock acquisition is inert so
    replay may be asserted read-only; generation and durable writers are traps.
    """
    record = yaml.safe_load(spec.provenance_path.read_bytes())
    index_path = snapshots.index_path(spec.metadata_dir, spec.project)
    index = json.loads(index_path.read_bytes())
    core = Path(original_entry(spec, record)['path']).read_bytes()
    alternate = spec.metadata_dir / 'portable-original-core.yaml'
    with alternate.open('xb') as stream:
        stream.write(core)
    baseline = inventory(spec)
    def forbidden(*args, **kwargs):
        raise AssertionError('completed replay cannot generate or persist new evidence')
    for case in ('identical_path', 'different_bytes', 'missing_core_index', 'missing_intermediates'):
        selected = deepcopy(record)
        if case in ('identical_path', 'different_bytes'):
            raw = core + (b'\n# Different valid original bytes.\n' if case == 'different_bytes' else b'')
            alternate.write_bytes(raw)
            original_entry(spec, selected).update(path=str(alternate), sha256=sha(raw))
            spec.provenance_path.write_text(yaml.safe_dump(selected))
        elif case == 'missing_core_index':
            changed = deepcopy(index)
            changed['snapshots'] = [r for r in changed['snapshots'] if r['name'] != f'{spec.project}_core.yaml']
            index_path.write_bytes(sg.canonical(changed))
        else:
            selected.pop('intermediates')
            spec.provenance_path.write_text(yaml.safe_dump(selected))
        before = inventory(spec)
        try:
            with pytest.MonkeyPatch.context() as patch:
                for module, name in ((api, '_client'), (api, '_call_with_usage'),
                        (api, '_call_with_retry'), (api, '_generate_phase'), (api, '_snapshot'),
                        (api, '_save_progress'), (ledger, '_write'), (ledger, 'persist_usage'),
                        (snapshots, '_write'), (api.provenance.ProvenanceRecord, 'write'),
                        (api.reasoning, 'append')):
                    patch.setattr(module, name, forbidden)
                patch.setattr(api, '_exclusive_run', lambda spec: nullcontext())
                client = SimpleNamespace(base_url=sg.capture(spec).document()['runtime']['base_url'],
                    messages=SimpleNamespace(create=forbidden, stream=forbidden, count_tokens=forbidden))
                if case in ('different_bytes', 'missing_intermediates'):
                    with pytest.raises(ledger.UsageLedgerError, match='original|attestation|packet'):
                        api.execute(replace(spec), resume=True, client=client)
                else:
                    result = api.execute(replace(spec), resume=True, client=client)
                    assert result['already_complete'] and result['validation_problems'] == []
                    assert result['checks']['shared_generation'] == record['shared_generation']
            assert inventory(spec) == before
        finally:
            for path, raw in baseline.items():
                Path(path).write_bytes(raw)
    assert inventory(spec) == baseline
