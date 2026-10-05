"""Initial receipt checks use captured inputs, without execution/seal fiction."""
from dataclasses import replace
from pathlib import Path

import pytest

from tests.test_native_shared_stages import case, artifact, plain
from tests.test_typed_audit import supplied
from data_sheets_schema import native_shared_contract as c, native_shared_receipts as nr


def checked(case, **kwargs):
    selection, _, phase1 = case[:3]
    return nr.check_initial(selection, full_raw=kwargs.get('full', phase1.full.raw),
                            receipt_raw=kwargs.get('receipt', phase1.original_receipt.raw))


@pytest.mark.parametrize('case', [{'zero_work': True}], indirect=True)
def test_initial_success_uses_only_captured_authority_and_has_no_final_claim(case, monkeypatch):
    def forbidden(*args, **kwargs): pytest.fail('initial check tried to read live authority')
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(Path, 'read_text', forbidden)
    monkeypatch.setattr(Path, 'resolve', forbidden)
    result = checked(case)
    assert result['checked'] is True and result['passed'] is True
    assert result['native_receipt_stage'] == 'phase1_initial'
    assert result['final_stage_complete'] is False
    assert result['coverage_floor']['state'] == 'pending'
    assert result['coverage_floor']['passed'] is False
    assert result['snippets']['verified'] == 1
    assert result['snippets']['by_origin']['phase1']['total'] == 1
    assert result['structural_receipt_floors'] and not any(result['structural_receipt_floors'].values())
    assert 'native_stage_completion_history_sha256' not in result
    assert result['native_initial_inputs']['full_sha256'] == case[2].full.pin.sha256
    assert result['native_initial_inputs']['receipt_sha256'] == case[2].original_receipt.pin.sha256


@pytest.mark.parametrize('case', [{'zero_work': True}], indirect=True)
@pytest.mark.parametrize('mutation', ['wrong_bundle', 'null', 'list', 'duplicate_key', 'source', 'partial'])
def test_initial_wrong_or_partial_input_cannot_pass(case, mutation):
    receipt = c.strict_json(case[2].original_receipt.raw)
    if mutation == 'wrong_bundle': receipt['bundle_md5'] = '0' * 32
    elif mutation == 'null':
        with pytest.raises(ValueError, match='captured bytes'): checked(case, receipt=None)
        return
    elif mutation == 'list':
        with pytest.raises(ValueError): checked(case, receipt=b'[]')
        return
    elif mutation == 'duplicate_key':
        with pytest.raises(ValueError): checked(case, receipt=b'{"chunks": [], "chunks": []}')
        return
    elif mutation == 'source':
        row = next(row for row in receipt['chunks'] if row['status'] == 'extracted')
        row['extracted'][0]['snippet'] = 'A wholly invented quotation absent from every captured input.'
    else:
        receipt['chunks'] = []
    if mutation == 'wrong_bundle':
        with pytest.raises(ValueError, match='captured bundle'): checked(case, receipt=c.canonical(receipt))
    else:
        result = checked(case, receipt=c.canonical(receipt))
        assert result['passed'] is False and any(result['structural_receipt_floors'].values())
        assert result['final_stage_complete'] is False and result['coverage_floor']['passed'] is False


def test_vacuous_initial_receipt_does_not_use_pending_floor_as_a_bypass(case):
    result = checked(case)
    assert result['structural_receipt_floors']['receipts vacuous'] == 1
    assert result['passed'] is False


@pytest.mark.parametrize('case', [{'zero_work': True}], indirect=True)
def test_pending_registration_is_disclosed_without_certifying_a_final_floor(case):
    selection = case[0]
    value = c.strict_json(selection.receipt_policy.raw)
    value['coverage_floor'] = {'state': 'pending', 'mode': 'diagnostic_pilot'}
    captured = artifact('receipt_policy', selection.receipt_policy.pin.path, c.canonical(value))
    document = selection.document(); document['receipt_policy'] = plain(captured)
    changed = replace(selection, receipt_policy=captured,
        registration=artifact('selection', selection.registration.pin.path, c.canonical(document)),
        authority=tuple(captured if item.pin.role == 'receipt_policy' else item for item in selection.authority))
    result = nr.check_initial(changed, full_raw=case[2].full.raw, receipt_raw=case[2].original_receipt.raw)
    assert result['passed'] is True and result['final_stage_complete'] is False
    assert result['coverage_floor']['floor'] == value['coverage_floor']
    assert result['coverage_floor']['passed'] is False
    assert result['receipt_completion_policy']['registration']['sha256'] == captured.pin.sha256


@pytest.mark.parametrize('case', [{'bounds': {'max_input_bytes': 16384}}], indirect=True)
def test_initial_input_bound_is_applied_without_a_phase1_carrier(case):
    with pytest.raises(ValueError, match='byte bound'):
        checked(case, receipt=b'x' * 16385)
