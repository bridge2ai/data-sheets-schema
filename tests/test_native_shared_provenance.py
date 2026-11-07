"""Real native record kernels and genuine v2 incomplete-entry refusals.

Completed-stage fixtures use synthetic stream observations, not permission or
runtime admission. Public recorded success belongs to the Python-peer end-to-end
suite; these tests never replace its loader, phase checks or gate verdicts.
"""
from copy import deepcopy
from dataclasses import replace

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import provenance
from tests.test_native_shared_receipt_readers import completed_reader, case, supplied, declaration, artifact
from tests.test_native_shared_results import initial
from tests.test_native_shared_live_capture import started
from tests.test_native_shared_registration import execution, bound, native_spec, inputs, isolated_modules
from tests.test_record_required_values import record as minimal_record


def test_stage_record_identity_is_fresh_reconstruction_not_scientific_acceptance(completed_reader):
    run, completion = completed_reader
    block = capture._provenance_block(run)
    assert block['selection_sha256'] == run.selection.registration.pin.sha256
    assert block['execution_sha256'] == run.binding.execution.pin.sha256
    assert block['assembly_sha256'] == completion.assembly.pin.sha256
    assert block['audit_sha256'] == completion.audit.pin.sha256
    assert block['receipt_result_sha256'] == completion.receipt_result.pin.sha256
    assert block['scientific_support'] == 'unverified evaluator declarations'
    assert block['runtime_acceptance'] == 'pending independent saved readback'
    record = minimal_record(); record['native_shared_generation'] = block
    assert provenance.check_record(record) == ([], None)
    assert capture._provenance_block(run) == block
    changed = tuple(artifact(item.pin.role, item.pin.path, item.raw + b'\n')
        if item.pin.role == 'typed_assembly' else item for item in run.history.artifacts)
    with pytest.raises(ValueError):
        capture._provenance_block(replace(run, history=replace(run.history, artifacts=changed)))
    missing = evidence.CapturePool(tuple(member for member in run.pool.members
        if member.captured.pin.role != 'completion'), ())
    with pytest.raises(ValueError, match='exact artifact'):
        capture._provenance_block(replace(run, pool=missing,
            reader=capture._Reader(run.selection, pool=missing)))


def test_public_recorded_readers_refuse_genuine_v2_init_without_completed_stages(started):
    run, _ = initial(started)
    selection_path = run.selection.registration.pin.path
    with pytest.raises(ValueError, match='final helper obligations'):
        capture.live_provenance_block(selection_path)
    record = {'prompts': {'request': {'spec': deepcopy(run.composition['render_spec'])}},
              'native_shared_generation': {'runtime_acceptance': 'passed'}}
    paths = run.spec._agentic_artifact_paths
    for reader, extra in ((capture.recorded_receipt_block, {}),
                          (capture.recorded_receipt_claims, {'expected_block': {'passed': True}})):
        with pytest.raises(ValueError, match='complete freshly reconstructed'):
            reader(None, record=record, full_path=paths['full'], receipt_path=paths['receipt'], **extra)
    # A stored native marker or passing block cannot substitute for observations.
    assert run.phase1 is None and not any(item.captured.pin.role == 'completion' for item in run.pool.members)


def test_recorded_reader_refuses_render_substitution_before_recorded_verdict(started):
    run, _ = initial(started)
    paths = run.spec._agentic_artifact_paths
    record = {'prompts': {'request': {'spec': deepcopy(run.composition['render_spec'])}}}
    record['prompts']['request']['spec']['label'] = 'foreign-label'
    with pytest.raises(ValueError):
        capture.recorded_receipt_block(None, record=record,
            full_path=paths['full'], receipt_path=paths['receipt'])
