"""U3-C receipt delivery accounting and repeated validation, 2026-11-07.

These captured helper cases do not grant execution admission. U3-B must supply
the real catalog owner before they can run; no replacement context is mocked.
"""
import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_receipts as receipts
from tests.test_native_shared_stages import case
from tests.test_typed_audit import supplied


MULTI = {'full': b'name: Example\ndescription: Existing description.\nissued: 2026-10-05\n'}


@pytest.mark.parametrize('coverage', [
    {'receiptable': True, 'with_receipt': 0},
    {'receiptable': 1, 'with_receipt': 2},
    {'receiptable': 1, 'with_receipt': 0, 'populated': 3, 'exempt': 1},
    {'receiptable': 1, 'with_receipt': 0, 'without_receipt': ['name', 'name']},
    {'receiptable': 1, 'with_receipt': 0, 'without_receipt_truncated': 1},
    {'receiptable': 1, 'with_receipt': 0, 'never_receipted': 1, 'added_after_receipt': 1},
    {'receiptable': 1, 'with_receipt': 0, 'receipt_paths': False},
])
def test_coverage_accounting_refuses_malformed_counters_before_policy(coverage):
    with pytest.raises(ValueError):
        receipts._coverage_counts(coverage)


def test_coverage_accounting_preserves_zero_and_complete_integer_counts():
    assert receipts._coverage_counts({'receiptable': 0, 'with_receipt': 0}) == (0, 0)
    assert receipts._coverage_counts({'receiptable': 3, 'with_receipt': 1,
        'populated': 4, 'exempt': 1, 'without_receipt': ['name'],
        'without_receipt_truncated': 1, 'never_receipted': 1, 'added_after_receipt': 1}) == (1, 3)


@pytest.mark.parametrize('case', [MULTI], indirect=True)
def test_accounting_distinguishes_unsupported_rejected_and_unanswered(case):
    selection, execution, phase1 = case[:3]
    before = phase1.original_receipt.raw
    request = receipts.prepare(selection, execution, phase1)
    assert set(request['requested_paths']) == {'name', 'description', 'issued'}
    response = c.canonical({'rereceipt': [
        {'path': 'name', 'unsupported': True, 'reason': 'Requires independent source review.'},
        {'path': 'description', 'receipt': {'chunk': 'absent', 'snippet': 'Not in the source.'}},
    ]})
    result = receipts.complete(selection, execution, phase1, response)
    report, carry = c.strict_json(result.result_json), c.strict_json(result.carry_json)
    assert report['state'] == 'answers_incomplete'
    assert report['counts']['requested'] == 3
    assert report['counts']['answers_received'] == 2
    assert report['counts']['accepted'] == report['counts']['unsupported'] == 1
    assert report['counts']['rejected_answers'] == report['counts']['rejected_paths'] == 1
    assert report['counts']['unanswered'] == 1
    assert report['counts']['receipts_added'] == report['counts']['already_present'] == 0
    assert report['unanswered_paths'] == carry['unanswered_paths'] == ['issued']
    assert report['rejected_paths'] == carry['rejected_paths'] == ['description']
    assert set(report['still_uncovered_paths']) == {'name', 'description', 'issued'}
    assert report['semantic_support'] == 'unverified'
    assert phase1.original_receipt.raw == before
    assert carry['original_receipt_sha256'] == c.sha(before)
    assert carry['effective_receipt_sha256'] == c.sha(result.effective_receipt)
    assert carry['result_sha256'] == c.sha(result.result_json)


def test_reusing_catalog_context_does_not_reuse_completed_response_verdict(case):
    selection, execution, phase1 = case[:3]
    owner = receipts._ReceiptCatalogContext()
    valid = c.canonical({'rereceipt': [{'path': 'name', 'unsupported': True,
                                     'reason': 'Requires independent source review.'}]})
    first = receipts._complete(selection, execution, phase1, valid, owner)
    assert c.strict_json(first.result_json)['state'] == 'answers_complete'
    invalid = receipts._complete(selection, execution, phase1, b'{invalid', owner)
    report = c.strict_json(invalid.result_json)
    assert report['state'] == 'answers_incomplete'
    assert report['response_problem']
    assert report['counts']['accepted'] == 0 and report['counts']['unanswered'] == 1
    repeated = receipts._complete(selection, execution, phase1, valid, owner)
    assert repeated == first
    assert repeated is not first


def test_reusing_catalog_context_rechecks_original_receipt_bytes(case):
    selection, _, phase1 = case[:3]
    owner = receipts._ReceiptCatalogContext()
    full, original = phase1.full.raw, phase1.original_receipt.raw
    receipts._raw_inputs(selection, full, original, _catalogs=owner)
    changed = c.strict_json(original)
    changed['bundle_md5'] = '0' * 32
    with pytest.raises(ValueError, match='captured bundle'):
        receipts._raw_inputs(selection, full, c.canonical(changed), _catalogs=owner)
    replay = receipts._raw_inputs(selection, full, original, _catalogs=owner)
    assert replay[1] == c.strict_json(original)
