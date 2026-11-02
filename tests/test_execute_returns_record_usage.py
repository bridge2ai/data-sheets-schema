"""`execute()` returns the record's api_usage (#5069, #5085 N1).

The final accounting (`_require_surviving_accounting`) rebuilds the record's
api_usage from a copy after repair and the report regate. An attempt it
recovers there, such as one abandoned during the regate, must be in what
`execute()` returns, which `d4d api run` prints and `d4d api batch` counts.
"""
import yaml

from data_sheets_schema import api_runner as api
from tests.test_download.test_api_runner import FakeClient
from tests.test_generation_manifest_identity import external, offline  # noqa: F401

ABANDONED = {"usage_id": "regate-abandoned", "phase": "report", "attempt": 2, "input_tokens": 11,
             "output_tokens": 7, "snapshot": "intermediate/x_report_incomplete_attempt2_1.txt"}


def test_a_row_recovered_at_the_final_accounting_is_returned(external, monkeypatch):
    real = api._require_surviving_accounting

    def recovering(spec, usage=None):
        merged = real(spec, usage)
        return merged if usage is None else [*merged, dict(ABANDONED)]
    monkeypatch.setattr(api, "_require_surviving_accounting", recovering)
    result = api.execute(external, client=FakeClient())
    recorded = yaml.safe_load(external.provenance_path.read_text(encoding="utf-8"))["api_usage"]
    assert ABANDONED in recorded
    assert ABANDONED in result["usage"]
    assert result["usage"] == recorded


# D57: retain externally observed journal heads across fixture resumes.
import pytest
pytestmark = pytest.mark.usefixtures("journal_launch_monitor")
