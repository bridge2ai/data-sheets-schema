"""U3-C criterion 3: real typed stages with synthetic, exactly joined streams.

No runtime admission, provider, native binary, U3-D gate or publication is mocked
into success. These tests establish the captured computation/delivery boundary.
"""
from copy import deepcopy
from dataclasses import replace

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import native_shared_receipts as receipts
from data_sheets_schema import typed_audit as typed
from tests.native_shared_captured_fixture import CapturedStages
from tests.test_native_shared_stages import case, supplied, artifact, receipt_answer


@pytest.mark.parametrize('case', [{'full': b'name: Example\ndescription: Existing description.\nissued: 2026-10-05\n',
    'bounds': {'max_paths_per_worker': 1, 'max_workers': 3, 'max_submissions': 6}}], indirect=True)
def test_complete_observed_typed_sequence_accounts_for_every_stage_and_source(case):
    run = CapturedStages(case)
    originals = run.case[2].full, run.case[2].original_receipt
    completion = run.complete()
    final_pool = run.final_pool()
    assert len(final_pool.stream_bindings) == 2
    checked = stage.check_assembly(*run.case, completion.assembly.raw)
    assert checked == completion
    assert (run.case[2].full, run.case[2].original_receipt) == originals
    kinds = [decision.cursor.kind for decision, _, _ in run.joins]
    assert kinds == ['receipt', 'worker', 'worker', 'worker', 'omission', 'integration']
    counts = c.strict_json(completion.counts_json)
    assert counts['stages'] == len(run.joins) == 6
    assert counts['workers'] == 3
    assert counts['omissions']['expected_chunks'] == counts['omissions']['declared_unique_chunks'] == 3
    assert counts['omissions']['retained'] == 2
    assert counts['findings']['omission'] == 1
    origins = c.strict_json(completion.stage_origins_json)
    assert len(origins) == len(run.joins)
    for origin, (decision, response, observations) in zip(origins, run.joins):
        assert origin['request_artifact_sha256'] == decision.request.pin.sha256
        assert origin['response_sha256'] == response.pin.sha256
        assert origin['session_id'] == run.case[1].session_id
        docs = [c.strict_json(item.raw) for item in observations]
        assert [doc['observation_type'] for doc in docs] == ['request_read', 'response_intent', 'response_written']
        assert docs[1]['payload']['read_observation'] == c.pin_dict(observations[0].pin)
        assert docs[2]['payload']['intent_observation'] == c.pin_dict(observations[1].pin)
        assert docs[2]['payload']['response'] == c.pin_dict(response.pin)
    records = [c.strict_json(item.raw) for item in run.case[3].records]
    consumed = [row['payload'] for row in records if row['record_type'] == 'response_consumed']
    assert len(consumed) == 6
    assert len({row['response']['path'] for row in consumed}) == 6
    assert len({row['read_observation']['sha256'] for row in consumed}) == 6
    receipt_result = c.strict_json(completion.receipt_result.raw)
    assert receipt_result['state'] == 'answers_complete'
    assert receipt_result['counts'] == counts['receipt']
    assert completion.effective_receipt.raw != b''
    # A consistently re-sealed omission still cannot erase required worker work.
    assembly = c.strict_json(completion.assembly.raw, max_bytes=c.HARD_LIMITS['assembly_bytes'])
    missing = deepcopy(assembly)
    missing['workers'].pop(next(iter(missing['workers'])))
    missing.pop('sha256')
    missing = typed._seal(missing)
    with pytest.raises(ValueError):
        typed.check(missing, captured_assets=receipts.omission_assets(run.case[0]))
    changed = replace(run.case[2], full=artifact('phase1_full', run.case[2].full.pin.path,
        run.case[2].full.raw + b'# changed original\n'))
    with pytest.raises(ValueError, match='phase1_sealed'):
        stage.check_assembly(run.case[0], run.case[1], changed, run.case[3], completion.assembly.raw)


@pytest.mark.parametrize('mutation', ['reordered_callback', 'foreign_reply', 'duplicate_request', 'spent_request'])
def test_observed_response_refuses_reordered_foreign_duplicate_or_spent_bytes(case, mutation):
    run = CapturedStages(case)
    with pytest.raises(ValueError):
        run.respond(receipt_answer(run.case), mutation=mutation)
    assert not run.joins
    assert not any(c.strict_json(row.raw)['record_type'] == 'response_consumed' for row in run.case[3].records)


def test_completed_receipt_request_cannot_be_consumed_again(case):
    run = CapturedStages(case)
    raw = receipt_answer(run.case)
    assert run.respond(raw).disposition == 'checked'
    request = run.joins[0][0].request.raw
    with pytest.raises(ValueError, match='no unique durable'):
        stage.check_response(*run.case, request, raw)
    assert len(run.joins) == 1
    assert stage.prepare_next(*run.case).state == 'await_core'
