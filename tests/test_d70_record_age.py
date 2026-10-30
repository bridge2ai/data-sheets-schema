"""D70: age requires positive evidence; missing guard fields do not date runs."""
import pytest
from data_sheets_schema import canary, latch_journal as journal
from tests.test_api_latch_guard import clean_integrity, record_with

PRE = "f8c5ac73caba610d40c49aaceddb31ead3590a72"


@pytest.mark.parametrize("commit,stamp,age", [
    (PRE, None, "pre-D41"),
    (journal.D41_COMMIT, "2000-01-01T00:00:00Z", "post-D41"),
    ("d9b69d84d", None, "post-D41"),
    (None, "2026-09-12T12:00:00Z", "pre-D41"),
    ("a" * 40, "2026-09-12T12:00:00Z", "pre-D41"),
    (None, None, "age unestablished"),
    ("a" * 40, journal.D41_COMMITTED_AT, "age unestablished"),
    (None, "2026-09-12", "age unestablished"),
    (None, "bad", "age unestablished"),
])
def test_age_and_consumers(commit, stamp, age):
    record = record_with(clean_integrity())
    record.pop("model")
    record.update(repo={"commit": commit}, record_generated_at=stamp)
    assert journal.record_age(record) == age
    problem = journal.record_eligibility_problem(record)
    assert (problem is None) == (age == "pre-D41")
    from data_sheets_schema.evaluation.registered_eval_runner import require_eligible_generation
    if problem:
        with pytest.raises(LookupError, match=age):
            canary._require_eligible_baseline(record, "test")
        with pytest.raises(ValueError, match=age):
            require_eligible_generation(record)
    else:
        canary._require_eligible_baseline(record, "test")
        require_eligible_generation(record)
    result = canary.verdict(canary.checks_from_record(record), {}, baseline_requested=False)
    assert (result["status"] == canary.OK) == (age == "pre-D41")


def test_removed_assisted_block_does_not_restore_eligibility():
    record = record_with({**clean_integrity(), "assisted": True, "evidence_only": True})
    record["repo"] = {"commit": journal.D41_COMMIT}
    assert journal.record_eligibility_problem(record)
    del record["model"]["runtime_integrity"]
    assert "post-D41" in journal.record_eligibility_problem(record)


def test_clean_block_does_not_depend_on_git_availability(monkeypatch):
    monkeypatch.setattr(journal, "record_age", lambda *a, **k: pytest.fail("unnecessary age lookup"))
    assert journal.record_eligibility_problem(record_with(clean_integrity())) is None
