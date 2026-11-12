"""PROPOSAL ONLY: optional native registered at-receipt coverage basis.

Pure receipt arithmetic and selected-policy tests; no RunSpec, executable,
provider, public completion or scientific acceptance. The deletion trap uses
real v4 receipt checking. The API evaluator is an unchanged comparison oracle.
The policy asset and protected pins deliberately remain unchanged pending a
separate owner decision; these tests do not authorize using the proposal.
"""
from copy import deepcopy
from pathlib import Path
import json

import pytest

from data_sheets_schema import canary
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_receipts as native
from data_sheets_schema import native_shared_selection as selection
from data_sheets_schema import receipt_completion_policy as api_policy
from data_sheets_schema import receipts as rc
from tests.test_native_shared_selection import declaration, pin, save  # noqa: F401
from tests.test_receipt_floor_basis import _policy as api_selected_policy
from tests.test_receipts import _manifest_and_texts, _receipt


REGISTERED = {'state': 'registered', 'numerator': 2, 'denominator': 3}
BASIS = {**REGISTERED, 'basis': 'receipted_part'}
PENDING = {'state': 'pending', 'mode': 'diagnostic_pilot'}


@pytest.fixture
def selected(declaration):
    def build(floor, *, pretty=False):
        path = Path(declaration['receipt_policy']['path'])
        policy = c.strict_json(path.read_bytes())
        policy['coverage_floor'] = deepcopy(floor)
        raw = ((json.dumps(policy, indent=2) + '\n').encode()
               if pretty else c.canonical(policy))
        path.write_bytes(raw)
        declaration['receipt_policy'] = pin(path, raw)
        save(declaration)
        captured = selection.capture(declaration['registration_path'])
        assert captured.receipt_policy.raw == raw
        assert captured.receipt_policy.pin.sha256 == c.sha(raw)
        return captured
    return build


def selected_block(captured, slots):
    chosen = api_policy.select_policy(api_policy.native_render_declaration(captured))
    return {'expected': True, 'checked': True, 'instrument': rc.RERECEIPTS_INSTRUMENT,
            'native_receipt_stage': 'final', 'final_stage_complete': True,
            'native_stage_completion_history_sha256': 'a' * 64,
            'native_shared_receipt_policy': dict(chosen['identity']),
            api_policy.BLOCK_KEY: api_policy.block_identity(chosen),
            'slots': deepcopy(slots), 'coverage_floor': native.floor(slots, captured),
            'chunks': {'total': 1, 'reviewed': 1}, 'snippets': {'verified': 1},
            'findings': [], 'findings_gated': 0}


def without_registration_hash(result):
    return {key: value for key, value in result.items() if key != 'registration_sha256'}


def test_real_receipt_deletion_trap_gates_one_of_two_not_final_one_of_one(selected):
    manifest, texts = _manifest_and_texts()
    receipt = _receipt(manifest['bundle_md5'])
    receipt['chunks'][1]['extracted'] = [{'slot': 'name', 'snippet': 'AI-READI dataset'}]
    original = {'name': 'AI-READI', 'description': 'An original unreceipted description.'}
    final = {'name': 'AI-READI'}
    block = rc.check(receipt, manifest, texts, final, manifest['bundle_md5'],
                     original, instrument_version=4)
    slots = block['slots']
    assert (slots['with_receipt'], slots['receiptable']) == (1, 1)
    assert (slots['with_receipt_at_receipt'], slots['receiptable_at_receipt']) == (1, 2)
    captured = selected(BASIS)
    result = native.floor(slots, captured)
    assert result['state'] == 'failed' and result['passed'] is False
    assert (result['with_receipt'], result['receiptable']) == (1, 1)
    assert (result['with_receipt_at_receipt'], result['receiptable_at_receipt']) == (1, 2)
    gated = selected_block(captured, slots)
    assert native.final_receipt_floors(gated, captured)['registered receipt coverage'] == 1
    legacy = selected(REGISTERED)
    assert native.floor(slots, legacy)['passed'] is True


def test_completed_receipt_additions_count_against_unchanged_original_snapshot(selected):
    manifest, texts = _manifest_and_texts()
    initial = _receipt(manifest['bundle_md5'])
    initial['chunks'][1]['extracted'] = [{'slot': 'name', 'snippet': 'AI-READI dataset'}]
    original = {'name': 'AI-READI', 'description': 'a longitudinal, multimodal study',
                'license': 'An unreceipted licence term.'}
    # Immutable snapshot bytes model the already sealed phase-1 record. This
    # arithmetic test does not claim that an observer actually published a seal.
    original_raw, initial_raw = c.canonical(original), c.canonical(initial)
    before = rc.check(initial, manifest, texts, original, manifest['bundle_md5'],
                      c.strict_json(original_raw), instrument_version=4)
    assert (before['slots']['with_receipt_at_receipt'],
            before['slots']['receiptable_at_receipt']) == (1, 3)
    completed = rc.apply_rereceipt(initial, c.strict_json(original_raw), [
        {'path': 'description', 'receipt': {'chunk': 'c002',
            'snippet': 'a longitudinal, multimodal study'}},
        {'path': 'license', 'unsupported': True, 'reason': 'No matching passage is supplied.'},
    ], texts, listed=['description', 'license'], instrument_version=4)
    assert completed['added'] == 1 and completed['unsupported'] == 1
    assert completed['rejected'] == 0 and completed['rejections'] == []
    effective = completed['receipt']
    retained = rc.check(effective, manifest, texts, c.strict_json(original_raw),
                        manifest['bundle_md5'], c.strict_json(original_raw), instrument_version=4)
    # This hypothetical deletion tests the denominator; an unsupported answer
    # never authorizes deleting the value or establishes scientific acceptance.
    final = {key: value for key, value in original.items() if key != 'license'}
    deleted = rc.check(effective, manifest, texts, final, manifest['bundle_md5'],
                       c.strict_json(original_raw), instrument_version=4)
    assert (retained['slots']['with_receipt'], retained['slots']['receiptable']) == (2, 3)
    assert (deleted['slots']['with_receipt'], deleted['slots']['receiptable']) == (2, 2)
    captured = selected(BASIS)
    assert native.floor(before['slots'], captured)['passed'] is False
    for block in (retained, deleted):
        assert (block['slots']['with_receipt_at_receipt'],
                block['slots']['receiptable_at_receipt']) == (2, 3)
        result = native.floor(block['slots'], captured)
        assert result['basis'] == 'receipted_part' and result['passed'] is True
        assert (result['with_receipt_at_receipt'], result['receiptable_at_receipt']) == (2, 3)
    # The new quoted addition changes the numerator, while neither that addition
    # nor the final deletion alters or replaces the original sealed denominator.
    assert c.canonical(original) == original_raw
    assert c.canonical(initial) == initial_raw


@pytest.mark.parametrize('covered,eligible,expected', [(1, 3, False), (2, 3, True), (3, 3, True)])
def test_registered_snapshot_threshold_matches_unchanged_api(selected, covered, eligible, expected):
    slots = {'with_receipt': 1, 'receiptable': 1,
             'with_receipt_at_receipt': covered, 'receiptable_at_receipt': eligible}
    captured = selected(BASIS)
    result = native.floor(slots, captured)
    oracle = api_policy.evaluate_floor(slots, api_selected_policy(BASIS))
    assert without_registration_hash(result) == without_registration_hash(oracle)
    assert result['passed'] is expected
    block = selected_block(captured, slots)
    assert native.final_receipt_floors(block, captured) == canary.receipt_floors(block)
    assert native.final_receipt_floors(block, captured)['registered receipt coverage'] == int(not expected)


def test_registered_large_fraction_is_exact_integer_comparison(selected):
    n = 10**18
    floor = {'state': 'registered', 'numerator': n - 1, 'denominator': n, 'basis': 'receipted_part'}
    captured = selected(floor)
    for covered, expected in ((n - 2, False), (n - 1, True), (n, True)):
        slots = {'with_receipt': 1, 'receiptable': 1,
                 'with_receipt_at_receipt': covered, 'receiptable_at_receipt': n}
        assert native.floor(slots, captured)['passed'] is expected
        assert without_registration_hash(native.floor(slots, captured)) == without_registration_hash(
            api_policy.evaluate_floor(slots, api_selected_policy(floor)))


@pytest.mark.parametrize('snapshot', [
    {}, {'with_receipt_at_receipt': None, 'receiptable_at_receipt': None},
    {'with_receipt_at_receipt': 1}, {'receiptable_at_receipt': 2},
    {'with_receipt_at_receipt': None, 'receiptable_at_receipt': 2},
])
def test_registered_missing_snapshot_never_falls_back_to_final_coverage(selected, snapshot):
    slots = {'with_receipt': 1, 'receiptable': 1, **snapshot}
    captured = selected(BASIS)
    result = native.floor(slots, captured)
    assert result['state'] == 'unmeasurable' and result['passed'] is False
    assert without_registration_hash(result) == without_registration_hash(
        api_policy.evaluate_floor(slots, api_selected_policy(BASIS)))
    assert native.final_receipt_floors(selected_block(captured, slots), captured)['registered receipt coverage'] == 1


def test_registered_zero_snapshot_never_becomes_full_coverage(selected):
    slots = {'with_receipt': 1, 'receiptable': 1,
             'with_receipt_at_receipt': 0, 'receiptable_at_receipt': 0}
    captured = selected(BASIS)
    result = native.floor(slots, captured)
    assert result['state'] == 'not_applicable' and result['passed'] is False
    assert without_registration_hash(result) == without_registration_hash(
        api_policy.evaluate_floor(slots, api_selected_policy(BASIS)))


@pytest.mark.parametrize('changes', [
    {'with_receipt_at_receipt': True}, {'receiptable_at_receipt': False},
    {'with_receipt_at_receipt': -1}, {'receiptable_at_receipt': 2.0},
    {'with_receipt_at_receipt': '1'}, {'with_receipt_at_receipt': 3},
])
def test_registered_invalid_snapshot_refuses_like_api(selected, changes):
    slots = {'with_receipt': 1, 'receiptable': 1,
             'with_receipt_at_receipt': 1, 'receiptable_at_receipt': 2, **changes}
    with pytest.raises(ValueError):
        native.floor(slots, selected(BASIS))
    with pytest.raises(ValueError):
        api_policy.evaluate_floor(slots, api_selected_policy(BASIS))


@pytest.mark.parametrize('snapshot', [
    {}, {'with_receipt_at_receipt': 0, 'receiptable_at_receipt': 100},
    {'with_receipt_at_receipt': None, 'receiptable_at_receipt': None},
    {'with_receipt_at_receipt': True, 'receiptable_at_receipt': 'historically ignored'},
])
def test_absent_registered_basis_preserves_legacy_bytes_and_interpretation(selected, snapshot):
    captured = selected(REGISTERED, pretty=True)
    raw = captured.receipt_policy.raw
    expected = {'with_receipt': 2, 'receiptable': 3,
                'floor': c.strict_json(raw)['coverage_floor'], 'passed': True,
                'registration_sha256': c.sha(raw), 'state': 'passed'}
    result = native.floor({'with_receipt': 2, 'receiptable': 3, **snapshot}, captured)
    assert json.dumps(result) == json.dumps(expected)
    assert captured.receipt_policy.raw == raw
    assert 'basis' not in c.parse_receipt_policy(raw)['coverage_floor']


@pytest.mark.parametrize('basis', [None, False, 1, [], {}, 'final_record', 'at_receipt', ''])
def test_registered_basis_is_a_single_closed_literal(selected, basis):
    with pytest.raises(ValueError):
        selected({**REGISTERED, 'basis': basis})


@pytest.mark.parametrize('floor', [
    {**BASIS, 'extra': 'not allowed'}, {**PENDING, 'basis': 'receipted_part'},
    {**REGISTERED, 'numerator': True, 'basis': 'receipted_part'},
    {**REGISTERED, 'denominator': False, 'basis': 'receipted_part'},
])
def test_basis_extension_does_not_open_other_registration_fields(selected, floor):
    with pytest.raises(ValueError):
        selected(floor)


@pytest.mark.parametrize('snapshot', [
    {'with_receipt_at_receipt': 1, 'receiptable_at_receipt': 2},
    {'with_receipt_at_receipt': 0, 'receiptable_at_receipt': 0},
])
def test_pending_snapshot_is_reported_only_never_selected_as_a_gating_basis(selected, snapshot):
    captured = selected(PENDING)
    slots = {'with_receipt': 1, 'receiptable': 1, **snapshot}
    result = native.floor(slots, captured)
    assert result['state'] == 'pending' and result['passed'] is False
    assert {key: result[key] for key in snapshot} == snapshot
    assert result['floor'] == PENDING and 'basis' not in result
    block = selected_block(captured, slots)
    assert block['coverage_floor'] == result
    assert 'registered receipt coverage' not in native.final_receipt_floors(block, captured)


@pytest.mark.parametrize('snapshot', [{}, {'with_receipt_at_receipt': 1},
    {'with_receipt_at_receipt': None, 'receiptable_at_receipt': None}])
def test_pending_missing_snapshot_does_not_invent_diagnostic_counts(selected, snapshot):
    result = native.floor({'with_receipt': 1, 'receiptable': 1, **snapshot}, selected(PENDING))
    assert result['state'] == 'pending' and result['passed'] is False
    assert 'with_receipt_at_receipt' not in result and 'receiptable_at_receipt' not in result
    assert 'basis' not in result


@pytest.mark.parametrize('snapshot', [
    {'with_receipt_at_receipt': True, 'receiptable_at_receipt': 2},
    {'with_receipt_at_receipt': 2, 'receiptable_at_receipt': 1},
    {'with_receipt_at_receipt': -1}, {'receiptable_at_receipt': 2.0},
])
def test_pending_refuses_invalid_supplied_snapshot_diagnostics(selected, snapshot):
    with pytest.raises(ValueError):
        native.floor({'with_receipt': 1, 'receiptable': 1, **snapshot}, selected(PENDING))


@pytest.mark.parametrize('mutation', ['captured-raw', 'rehashed-block-basis', 'report-counter'])
def test_final_gate_cannot_rebind_basis_or_snapshot_after_identity_capture(selected, mutation):
    captured = selected(BASIS)
    slots = {'with_receipt': 1, 'receiptable': 1,
             'with_receipt_at_receipt': 1, 'receiptable_at_receipt': 2}
    block = selected_block(captured, slots)
    if mutation == 'captured-raw':
        captured = deepcopy(captured)
        raw = c.strict_json(captured.receipt_policy.raw)
        raw['coverage_floor'].pop('basis')
        object.__setattr__(captured.receipt_policy, 'raw', c.canonical(raw))
    elif mutation == 'rehashed-block-basis':
        raw = c.strict_json(block[api_policy.BLOCK_KEY]['registration']['raw_json'].encode())
        raw['coverage_floor'].pop('basis')
        encoded = c.canonical(raw)
        identity = {'sha256': c.sha(encoded), 'raw_json': encoded.decode()}
        block[api_policy.BLOCK_KEY]['registration'] = identity
        block['native_shared_receipt_policy'] = dict(identity)
        block['coverage_floor'].update(state='passed', passed=True)
    else:
        block['coverage_floor']['with_receipt_at_receipt'] = 2
    with pytest.raises(ValueError):
        native.final_receipt_floors(block, captured)
