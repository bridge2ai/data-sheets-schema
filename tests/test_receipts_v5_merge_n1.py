"""N1 causal regressions: run authority selects the instrument, never the receipt/env."""
import pytest
import yaml

from data_sheets_schema import receipts as rc
from tests.test_receipt_completion_policy import declaration, disk  # noqa: F401


@pytest.mark.parametrize("authority", ["legacy", "registration", "provenance"])
@pytest.mark.parametrize("injection", ["marker", "environment", "both"])
def test_n1_untrusted_selection_cannot_override_run(disk, monkeypatch, authority, injection):
    if injection in {"environment", "both"}:
        monkeypatch.setenv("RECEIPTS_V5_INSTRUMENT", "1")
    if injection in {"marker", "both"}:
        receipt = yaml.safe_load(disk["receipt"].read_text())
        receipt["receipt_format_version"] = 5
        disk["receipt"].write_text(yaml.safe_dump(receipt))
    kwargs = {}
    if authority == "registration":
        kwargs["receipt_render_spec"] = declaration()
    elif authority == "provenance":
        kwargs["snapshot_record"] = {"run": {"project": "P"},
                                     "prompts": {"request": {"spec": declaration()}}}
    block = rc.block_for(**disk, **kwargs)
    version = 3 if authority == "legacy" else 4
    assert block["checked"], block
    assert block["instrument"] == rc.receipt_instrument(version)
    assert "tool_receipts" not in block
    mismatches = [f for f in block["findings"] if f["kind"] == "receipt_format_version_mismatch"]
    assert mismatches == ([] if injection == "environment" else [{
        "kind": "receipt_format_version_mismatch", "declared": 5, "selected": version,
    }])


@pytest.mark.parametrize("version", [3, 4, 5])
@pytest.mark.parametrize("marker", [3, 4, 5, "5", None, True, [5]])
def test_n1_explicit_check_records_disagreement(version, marker):
    receipt = {"bundle_md5": "abc", "receipt_format_version": marker, "chunks": []}
    block = rc.check(receipt, {"bundle_md5": "abc", "chunks": []}, {}, {}, "abc",
                     instrument_version=version)
    assert block["instrument"] == rc.receipt_instrument(version)
    mismatches = [f for f in block["findings"] if f["kind"] == "receipt_format_version_mismatch"]
    assert bool(mismatches) == (type(marker) is not int or marker != version)


@pytest.mark.parametrize("version", [None, 3, 4, 5])
def test_n1_claim_shape_requires_explicit_caller_version(monkeypatch, version):
    monkeypatch.setenv("RECEIPTS_V5_INSTRUMENT", "1")
    pair = {"slot": "description", "snippet": "A documented description", "supports": "REFUTE"}
    receipt = {"receipt_format_version": 5, "chunks": [
        {"id": "c001", "status": "extracted", "extracted": [pair]}]}
    claims = rc.claim_receipts(receipt, instrument_version=version)
    item = claims["slots"]["description"]["receipts"][0]
    assert ("supports" in item) == (version == 5)
