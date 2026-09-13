"""Partial resume must prove the accounting for every surviving response."""
import json
import pytest
from data_sheets_schema import api_runner as api, usage_ledger as ledger
from tests.test_download.test_api_runner import FakeClient
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


@pytest.mark.parametrize("keep_reasoning", [False, True])
def test_partial_resume_refuses_a_missing_completed_journal_row(external, keep_reasoning):
    first = FakeClient()
    first.messages.fail_on = "reconcile_full"
    with pytest.raises(RuntimeError, match="boom"):
        api.execute(external, client=first)
    progress = api._progress_path(external).read_bytes()
    data = json.loads(ledger.ledger_path(external).read_text())
    assert any(row["phase"] == "full" for row in data["rows"])
    data["rows"] = [row for row in data["rows"] if row["phase"] != "full"]
    ledger.ledger_path(external).write_text(json.dumps(data))
    if not keep_reasoning:
        api._reasoning_path(external).unlink()
    second = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="account|reasoning|attempt"):
        api.execute(external, client=second)
    assert second.messages.calls == []
    assert api._progress_path(external).read_bytes() == progress
    assert not external.provenance_path.exists()
