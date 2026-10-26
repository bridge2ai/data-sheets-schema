"""D41 runner latch integrity tests (#5144, 10-20a, 10-22a)."""
from __future__ import annotations

import json
import pytest

from data_sheets_schema import api_runner as api, snapshot_store, usage_ledger as ledger
from tests.test_download.test_api_runner import spec


def _init_spec(tmp_path):
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=False)
    ledger.require_resolved(s)
    return s


def test_typed_audit_latch_rewind_refused(tmp_path):
    s = _init_spec(tmp_path)
    data = ledger._read(s)
    data["typed_audit"] = {
        "format": "d4d_typed_audit_state_v1",
        "state": "running",
        "failure_type": "UsageLedgerError",
        "stages": [],
    }
    ledger._write(s, data)
    with pytest.raises(ledger.UsageLedgerError, match="typed audit terminal failure latch was rewound"):
        ledger.require_resolved(s)

    # Prepared stage carrying prior admission/failure evidence
    data["typed_audit"] = {
        "format": "d4d_typed_audit_state_v1",
        "state": "running",
        "stages": [{"state": "prepared", "usage_id": "u1"}],
    }
    ledger._write(s, data)
    with pytest.raises(ledger.UsageLedgerError, match="prepared typed audit stage carries prior admission"):
        ledger.require_resolved(s)

    # Settled typed_audit_worker usage row without matching response_saved/checked stage
    data["typed_audit"] = {
        "format": "d4d_typed_audit_state_v1",
        "state": "running",
        "stages": [{"state": "admitted", "usage_id": "u1"}],
    }
    data["rows"] = [{"usage_id": "u1", "phase": "typed_audit_worker", "attempt": 1}]
    ledger._write(s, data)
    with pytest.raises(ledger.UsageLedgerError, match="typed audit stage journal was rewound after settling usage"):
        ledger.require_resolved(s)


def test_typed_audit_snapshot_and_abandoned_latch_rewind_refused(tmp_path):
    s = _init_spec(tmp_path)
    api._snapshot(s, f"{s.project}_typed_audit_0_response.json", "{}", usage_id="u1")
    data = ledger._read(s)
    data["typed_audit"] = {
        "format": "d4d_typed_audit_state_v1",
        "state": "running",
        "stages": [{"state": "prepared"}],
    }
    ledger._write(s, data)
    with pytest.raises(ledger.UsageLedgerError, match="typed audit stage was rewound after recording a response snapshot"):
        ledger.require_resolved(s)

    # Abandoned attempt in active generation requires failed state
    s2 = _init_spec(tmp_path / "sub")
    d2 = ledger._read(s2)
    ledger.abandoned_journal_path(s2).write_text(
        json.dumps({
            "usage_id": "ab1",
            "phase": "typed_audit_worker",
            "generation_id": d2["generation_id"],
            "run_identity": ledger.run_identity(s2),
        }) + "\n",
        encoding="utf-8",
    )
    d2["typed_audit"] = {"format": "d4d_typed_audit_state_v1", "state": "running", "stages": []}
    ledger._write(s2, d2)
    with pytest.raises(ledger.UsageLedgerError, match="typed audit failure latch was rewound after an abandoned attempt"):
        ledger.require_resolved(s2)


def test_receipt_completion_latch_rewind_refused(tmp_path):
    s = _init_spec(tmp_path)
    data = ledger._read(s)
    data["receipt_completion"] = {"state": "intent", "usage_id": "rc1"}
    ledger._write(s, data)
    with pytest.raises(ledger.UsageLedgerError, match="receipt completion intent carries prior admission"):
        ledger.require_resolved(s)

    data["receipt_completion"] = {"state": "admitted", "failure_type": "RuntimeError"}
    ledger._write(s, data)
    with pytest.raises(ledger.UsageLedgerError, match="receipt completion failure latch was rewound"):
        ledger.require_resolved(s)

    data["receipt_completion"] = {"state": "admitted"}
    data["rows"] = [{"usage_id": "rc1", "phase": "full_receipt_completion", "attempt": 1}]
    ledger._write(s, data)
    with pytest.raises(ledger.UsageLedgerError, match="receipt completion state was rewound after settling usage"):
        ledger.require_resolved(s)


def test_evidence_refusal_and_one_shot_latches_refused(tmp_path):
    s = _init_spec(tmp_path)
    api._snapshot(s, f"{s.project}_report_rejected_response_u9.txt", "bad", usage_id="u9")
    with pytest.raises(ledger.UsageLedgerError, match="terminal evidence refusal latch was removed"):
        ledger.require_resolved(s)

    data = ledger._read(s)
    data["evidence_refusal"] = {"stage": "report", "reading": {"checked": False}}
    data["rows"] = [{
        "usage_id": "u9",
        "phase": "report",
        "source_review_admission": {"state": "accepted", "response_sha256": "a" * 64},
    }]
    ledger._write(s, data)
    with pytest.raises(ledger.UsageLedgerError, match="rejected source-review response cannot be marked accepted"):
        ledger.require_resolved(s)

    # Regate snapshot without report_regate_attempted
    s2 = _init_spec(tmp_path / "regate")
    api._snapshot(s2, f"{s2.project}_report_regate.md", "# Report\n", usage_id="u2")
    with pytest.raises(ledger.UsageLedgerError, match="report regate latch was rewound"):
        ledger.require_resolved(s2)

    # Removal repair snapshot without removal_repair_attempted
    s3 = _init_spec(tmp_path / "repair")
    api._snapshot(s3, f"{s3.project}_report_after_repair.md", "# Report\n", usage_id="u3")
    with pytest.raises(ledger.UsageLedgerError, match="removal repair latch was rewound"):
        ledger.require_resolved(s3)

