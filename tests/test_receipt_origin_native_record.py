"""Native metadata joins; genuine origin histories, synthetic assessment pins.

These controls exercise the real origin instrument and record wrapper. They do
not certify that the synthetic assessment shell passed native stage validation.
"""
from copy import deepcopy
import hashlib

import pytest

from data_sheets_schema import receipt_origin_record as ror
from tests.test_receipt_origin_record import _three_origins


def pin(path, role):
    raw = path.read_bytes()
    return {"role": role, "path": str(path), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


@pytest.mark.parametrize("equal_bytes", [False, True])
def test_native_stale_measurement_survives_repeated_reporting_and_restoration(tmp_path, equal_bytes):
    r, transcript = _three_origins(tmp_path / "history")
    original = r.receipt.read_bytes()
    measured = ror.for_record(None, r.receipt, r.full, transcripts=[transcript])
    assert measured["status"] == "checked" and measured["origin"]["contemporaneous"] == 3
    effective = tmp_path / "effective-receipt.yaml"
    effective.write_bytes(original if equal_bytes else original + b"# synthetic effective difference\n")
    assessment = {"checked": True, "native_receipt_stage": "final", "native_receipt_inputs": {
        "selected_original": pin(r.receipt, "original_receipt_output"),
        "sealed_original": pin(r.receipt, "phase1_receipt"),
        "assessed_effective": pin(effective, "effective_receipt")}}
    before = deepcopy(assessment)
    prior = deepcopy(measured)
    # Ordinary and initial-phase callers preserve exact legacy result bytes.
    assert ror.for_assessment({}, prior, r.receipt, r.full) == measured
    assert ror.for_assessment({"native_receipt_stage": "phase1_initial"}, prior,
                              r.receipt, r.full) == measured
    r.receipt.write_bytes(original + b"# original changed after the measured history\n")
    stale = ror.for_record(prior, r.receipt, r.full)
    assert stale["status"] == "unknown" and stale["prior"] == measured
    assert "changed after the transcripts" in stale["reasons"][0]
    for _ in range(3):
        reported = ror.for_assessment(assessment, prior, r.receipt, r.full)
        assert ror.ever_measured(reported), "native wrapper must not hide the retained measurement"
        assert reported["status"] == "unknown" and "origin" not in reported
        assert reported["prior"] == measured
        assert reported["original_receipt_origin"] == stale
        assert reported["native_receipt_inputs"] == before["native_receipt_inputs"]
        assert ror.split({**assessment, "origin": reported}) is None
        prior = reported
    r.receipt.write_bytes(original)
    restored = ror.for_assessment(assessment, prior, r.receipt, r.full)
    assert restored["status"] == "unknown" and ror.ever_measured(restored)
    assert restored["prior"] == restored["original_receipt_origin"] == measured
    assert ror.split({**assessment, "origin": restored}) is None
    assert assessment == before
    restored["native_receipt_inputs"]["selected_original"]["sha256"] = "0" * 64
    restored["prior"]["reasons"].append("caller mutation")
    assert assessment == before and measured["reasons"] == []


def test_native_explicit_transcript_keeps_original_history_separate(tmp_path):
    r, transcript = _three_origins(tmp_path / "history")
    ordinary = ror.for_record(None, r.receipt, r.full, transcripts=[transcript])
    assessment = {"native_receipt_stage": "final", "native_receipt_inputs": {
        "selected_original": pin(r.receipt, "original_receipt_output"),
        "assessed_effective": pin(r.receipt, "effective_receipt")}}
    reported = ror.for_assessment(assessment, None, r.receipt, r.full, transcripts=[transcript])
    assert reported["status"] == "unknown"
    assert reported["original_receipt_origin"] == reported["prior"] == ordinary
    assert ror.ever_measured(reported) and ror.split({**assessment, "origin": reported}) is None
