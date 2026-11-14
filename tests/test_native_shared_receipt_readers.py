"""Real captured receipt reader kernels, without a fabricated admission verdict.

S and its schema closure are captured from real fixture files. The stage frames
are explicitly synthetic criterion-3 evidence; the actual receipt/stage readers
reconstruct them. This is not a successful public recorded-run or launch test.
The public entry tests separately prove incomplete genuine v2 runs refuse.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_receipts as native_receipts
from data_sheets_schema import native_shared_selection as selection
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import receipt_origin_record as origin
from data_sheets_schema import receipts
from data_sheets_schema.schema_snapshot import capture_schema
from tests.native_shared_captured_fixture import CapturedStages
from tests.test_native_shared_selection import declaration, pin, save, update_input
from tests.test_native_shared_stages import case, supplied, artifact, append


def _member(item, number):
    return evidence.PoolMember(item, c.canonical({
        'exists': True, 'regular': True, 'symlink': False, 'links': 1,
        'device': 0, 'inode': number + 1, 'size': item.pin.bytes, 'mtime_ns': 0}))


@pytest.fixture
def completed_reader(case, declaration, supplied, tmp_path, monkeypatch):
    """Actual selected assets and real stage computation; invented delivery frames."""
    for name, source in (('bundle', 'bundle'), ('chunk_manifest', 'manifest'), ('context', 'context')):
        update_input(declaration, name, supplied[source])
    root_schema = supplied['schema_path']
    # This fixture selects its real imported schema closure; keep the configured
    # validation root aligned with that selection instead of bypassing capture.
    from data_sheets_schema import api_runner
    monkeypatch.setattr(api_runner, 'FULL_SCHEMA_PATH', root_schema)
    root_schema.write_bytes(root_schema.read_bytes() + b'prefixes:\n  selected: https://selected.example/\n')
    child_schema = root_schema.with_name('child.yaml')
    child_schema.write_bytes(child_schema.read_bytes().replace(
        b"prefixes: {linkml: 'https://w3id.org/linkml/'}",
        b"prefixes: {linkml: 'https://w3id.org/linkml/', imported_only: 'https://imported.example/'}"))
    snapshot = capture_schema(supplied['schema_path'], strict=True)
    declaration['inputs']['full_schema'] = {
        'root': str(supplied['schema_path']), 'root_class': 'Dataset',
        'sources': [{'name': str(name), **pin(path, raw)} for name, path, raw in snapshot.sources]}
    policy_path = Path(declaration['receipt_policy']['path'])
    policy = c.strict_json(policy_path.read_bytes())
    policy['coverage_floor'] = {'state': 'registered', 'numerator': 0, 'denominator': 1,
                                'basis': 'receipted_part'}
    policy_raw = c.canonical(policy)
    policy_path.write_bytes(policy_raw)
    declaration['receipt_policy'] = pin(policy_path, policy_raw)
    save(declaration)
    selected = selection.capture(declaration['registration_path'])

    def at(role, item):
        return artifact(role, selected.role(role), item.raw)

    old_binding, old_phase1 = case[1:3]
    binding = replace(old_binding, selection_sha256=selected.registration.pin.sha256,
        execution=at('execution_capture', old_binding.execution),
        started=at('started_capture', old_binding.started),
        binding_artifact=at('session_binding', old_binding.binding_artifact),
        init_observation=artifact('observation', selected.role('observations_root') + '/000000.json',
                                  old_binding.init_observation.raw))
    phase1 = replace(old_phase1, full=at('phase1_full', old_phase1.full),
        original_receipt=at('phase1_receipt', old_phase1.original_receipt),
        seal=at('phase1_seal', old_phase1.seal),
        full_seal_observation=artifact('observation', selected.role('observations_root') + '/000001.json',
                                       old_phase1.full_seal_observation.raw))
    journal = artifact('journal', selected.role('journal'), stage.journal_bytes(
        selection_sha256=selected.registration.pin.sha256,
        execution_sha256=binding.execution.pin.sha256, attempt_id=binding.attempt_id, records=()))
    history = c.RawHistory(journal=journal, records=(), artifacts=(), observations=())
    entries = (
        ('genesis', {'execution': c.pin_dict(binding.execution.pin), 'started': c.pin_dict(binding.started.pin)}),
        ('session_bound', {'binding': c.pin_dict(binding.binding_artifact.pin),
                           'init_observation': c.pin_dict(binding.init_observation.pin)}),
        ('phase1_sealed', {'seal': c.pin_dict(phase1.seal.pin), 'full': c.pin_dict(phase1.full.pin),
                           'original_receipt': c.pin_dict(phase1.original_receipt.pin),
                           'observation': c.pin_dict(phase1.full_seal_observation.pin)}))
    records, journal = stage.append_records(selected, binding, history,
        tuple((kind, c.canonical(payload)) for kind, payload in entries))
    stages = CapturedStages((selected, binding, phase1, append(history, records, journal)))
    completion = stages.complete()
    streams = stages.final_pool()
    selected, binding, phase1, history = stages.case
    paths = {key: str(tmp_path / ('ordinary-' + key)) for key in ('full', 'core', 'report', 'receipt')}
    originals = (artifact('final_full', paths['full'], phase1.full.raw),
        artifact('original_receipt_output', paths['receipt'], phase1.original_receipt.raw))
    # Every test reader sees immutable actual stage publications, not a verdict.
    items = {(item.pin.role, item.pin.path): item for item in (*history.artifacts, *originals)}
    pool = evidence.CapturePool(tuple(_member(item, n) for n, item in enumerate(items.values())), ())
    reader = capture._Reader(selected, pool=pool)
    prefixes = tuple(capture._prefix(member, None) for member in streams.members)
    run = capture._CapturedRun(selected, c.strict_json(binding.execution.raw)['registration'],
        {'policy': {'post_final_recorder': {'destination': str(tmp_path / 'provenance.yaml')}}},
        SimpleNamespace(_agentic_artifact_paths=paths), reader, pool, *prefixes,
        binding, history, history.observations, phase1)
    return run, completion


def assess(run, **overrides):
    paths = run.spec._agentic_artifact_paths
    return capture._receipt_assessment(run,
        full_path=overrides.get('full_path', paths['full']),
        receipt_path=overrides.get('receipt_path', paths['receipt']))


def replace_pool(run, role, raw):
    members = tuple(_member(artifact(role, member.captured.pin.path, raw), n)
        if member.captured.pin.role == role else member
        for n, member in enumerate(run.pool.members))
    pool = evidence.CapturePool(members, run.pool.stream_bindings)
    return replace(run, pool=pool, reader=capture._Reader(run.selection, pool=pool))


def test_final_reader_reconstructs_effective_bytes_and_keeps_original_history(completed_reader, tmp_path, monkeypatch):
    run, completion = completed_reader
    original = run.phase1.original_receipt.raw
    # Captured schema graphs remain authoritative after their live paths change.
    for schema in run.selection.schemas:
        for source in schema.sources:
            path = Path(source.pin.path)
            if path.is_relative_to(tmp_path):
                path.write_bytes(b'not the selected schema\n')
    def forbidden(*args, **kwargs):
        pytest.fail('captured receipt assessment attempted live I/O')
    with monkeypatch.context() as trapped:
        trapped.setattr(evidence, 'read_regular', forbidden)
        for name in ('read_bytes', 'read_text', 'open', 'resolve'):
            trapped.setattr(Path, name, forbidden)
        block, full, effective = assess(run)
        assert assess(run)[0] == block  # independent subsequent reconstruction
    assert block['checked'] and block['final_stage_complete']
    assert block['native_receipt_stage'] == 'final'
    assert effective == completion.effective_receipt
    assert effective.raw != original
    assert block['native_receipt_inputs']['selected_original']['sha256'] == c.sha(original)
    assert block['native_receipt_inputs']['sealed_original'] == c.pin_dict(run.phase1.original_receipt.pin)
    assert block['native_receipt_inputs']['assessed_effective'] == c.pin_dict(effective.pin)
    assert block['native_receipt_inputs']['final_full'] == c.pin_dict(full.pin)
    assert block['identity_rules']['basis'] == 'captured native full schema'
    assert ['https://selected.example/', 'selected'] in block['identity_rules']['identifier_bases']
    assert ['https://imported.example/', 'imported_only'] not in block['identity_rules']['identifier_bases']
    # The D91 native declaration stays instrument 4; this is not an API-v5 rewrite.
    assert c.strict_json(completion.receipt_result.raw)['receipt_instrument_version'] == 4
    assert run.phase1.original_receipt.raw == original

    receipt_path = tmp_path / 'retained-original.json'; receipt_path.write_bytes(original)
    full_path = tmp_path / 'retained-full.yaml'; full_path.write_bytes(full.raw)
    prior = {'status': 'checked', 'transcripts': [{'sha256': 'a' * 64}],
             'receipt': {'sha256': c.sha(original)}, 'origin': {'contemporaneous': 1}}
    kept = origin.for_assessment(block, prior, receipt_path, full_path)
    assert kept['status'] == 'unknown'
    assert kept['original_receipt_origin'] == prior
    assert kept['prior'] == prior and origin.split({'origin': kept}) is None
    assert kept['native_receipt_inputs'] == block['native_receipt_inputs']


def test_final_reader_refuses_original_substitution_and_rechecks_stage_bytes(completed_reader):
    run, _ = completed_reader
    baseline = assess(run)[0]
    with pytest.raises(ValueError, match='sealed original'):
        assess(replace_pool(run, 'original_receipt_output', run.phase1.original_receipt.raw + b'\n'))
    for key in ('full_path', 'receipt_path'):
        with pytest.raises(ValueError, match='exact execution-selected'):
            assess(run, **{key: '/foreign/' + key})
    for role in ('typed_assembly', 'audit', 'receipt_result', 'effective_receipt'):
        assert any(item.pin.role == role for item in run.history.artifacts), role
        changed = tuple(artifact(role, item.pin.path, item.raw + b'\n')
            if item.pin.role == role else item for item in run.history.artifacts)
        with pytest.raises(ValueError):
            assess(replace(run, history=replace(run.history, artifacts=changed)))
    assert assess(run)[0] == baseline


def test_native_effective_origin_does_not_change_api_v5_assessment(completed_reader, tmp_path):
    run, _ = completed_reader
    native = assess(run)[0]
    ordinary = tmp_path / 'receipt.json'; ordinary.write_bytes(run.phase1.original_receipt.raw)
    full = tmp_path / 'full.yaml'; full.write_bytes(run.phase1.full.raw)
    prior = {'status': 'checked', 'transcripts': [{'sha256': 'b' * 64}],
             'receipt': {'sha256': c.sha(ordinary.read_bytes())}}
    original, original_receipt, manifest, texts, md5, bases, _, _ = native_receipts._inputs(
        run.selection, run.phase1)
    api = receipts.check(original_receipt, manifest, texts, original, md5, original,
                         instrument_version=5, identifier_bases=bases)
    before = deepcopy(api)
    assert origin.for_assessment(api, prior, ordinary, full, api_path=True) == prior
    assert api == before
    assert 'native_receipt_stage' not in api
    assert origin.for_assessment(native, prior, ordinary, full)['status'] == 'unknown'
