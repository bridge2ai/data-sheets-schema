"""N4 causal regressions: preserve A13 scalar coverage and planner behavior at v3/v4."""
import pytest

from data_sheets_schema import receipts as rc


@pytest.mark.parametrize("version", [3, 4, 5])
@pytest.mark.parametrize("snippet", [2026, 2026.5, True])
def test_n4_nonstring_scalar_coverage_uses_selected_version(version, snippet):
    full = {"record_count": 2026}
    receipt = {"bundle_md5": "abc", "chunks": [{"id": "c001", "status": "extracted",
               "extracted": [{"slot": "record_count", "snippet": snippet}]}]}
    manifest = {"bundle_md5": "abc", "chunks": [{"id": "c001"}]}
    texts = {"c001": "The dataset contains 2026 records."}
    block = rc.check(receipt, manifest, texts, full, "abc", original=full, instrument_version=version)
    assert block["slots"]["with_receipt"] == (0 if version == 5 else 1)
    if version in (4, 5):
        assert block["slots"]["with_receipt_at_receipt"] == (0 if version == 5 else 1)
    assert rc.uncovered_receiptable_leaves(
        receipt, manifest, texts, full, "abc", original=full, instrument_version=version,
    ) == (["record_count"] if version == 5 else [])
