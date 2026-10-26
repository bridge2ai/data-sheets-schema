"""Causal regressions for original-ledger accounting and conditional cache timing."""
from datetime import datetime, timedelta, timezone
import json

import pytest

from scripts.adhoc import k1_v2_ledger_originals_20261026 as audit


def row(usage_id="a", **updates):
    return {"usage_id": usage_id, "phase": "typed_audit_worker", "attempt": 1,
            "started_at": "2026-10-22T14:00:00+00:00", "seconds": 500,
            "input_tokens": 2, "cache_read": 0, "cache_write": 100,
            "output_tokens": 50, "thinking_tokens": 25, "max_tokens": 64000,
            "stop_reason": "end_turn", **updates}


def test_admission_rewrite_is_reported_even_when_every_usage_counter_matches():
    original = row(source_review_admission={"state": "pending", "response_sha256": "old"})
    edited = row(source_review_admission={"state": "accepted", "response_sha256": "new"})
    result = audit.compare_rows([original], [edited, row("later")])
    assert result["matched_count"] == result["changed_matched_row_count"] == 1
    assert {d["path"] for d in result["matched_rows"][0]["differences"]} == {
        "/source_review_admission/state", "/source_review_admission/response_sha256"}
    assert result["added_rows"] == [row("later")]
    assert not result["removed_rows"]


@pytest.mark.parametrize("field,value", [("input_tokens", 999), ("output_tokens", 999),
    ("cache_read", 999), ("cache_write", 999), ("max_tokens", 25000),
    ("phase", "report"), ("stop_reason", "max_tokens"), ("outcome", "edited")])
def test_k1_comparison_excludes_estimates_but_detects_each_raw_counter_or_outcome_edit(field, value):
    original = row()
    derived = {**original, "date": "2026-10-22a", "cost_usd": 1.2,
               "payload_bytes": 400, "raw_a1_estimate": 300, field: value}
    result = audit.compare_rows([original], [derived], derived_after=True)
    assert [d["path"] for d in result["matched_rows"][0]["differences"]] == [f"/{field}"]


def test_missing_null_false_and_zero_do_not_become_identical():
    delta = audit.differences({"null": None, "flag": False, "zero": 0},
                             {"flag": 0, "zero": False, "added": None})
    assert {d["path"] for d in delta} == {"/null", "/flag", "/zero", "/added"}
    assert next(d for d in delta if d["path"] == "/null")["after"] == {"present": False}


def test_duplicate_usage_id_fails_instead_of_overwriting_original():
    with pytest.raises(ValueError, match="duplicate usage ID"):
        audit.compare_rows([row(), row(input_tokens=300)], [row()])


def test_preserved_manifest_mismatch_is_fatal(tmp_path):
    archive = tmp_path / "chorus_rep1_unmodified_archive"
    archive.mkdir()
    path = archive / "ledger.json"
    raw = b'{"rows": []}'
    path.write_bytes(raw)
    (tmp_path / "MANIFEST.sha256").write_text(f"{audit.digest(raw)}  ./chorus_rep1_unmodified_archive/ledger.json\n")
    assert len(audit.verify_archive(audit.Reader(), tmp_path)["verified_archive_files"]) == 1
    path.write_bytes(b'{"rows": [1]}')
    with pytest.raises(ValueError, match="manifest mismatch"):
        audit.verify_archive(audit.Reader(), tmp_path)


def test_absence_inventory_includes_ignored_hidden_and_extensionless_ledgers(tmp_path):
    (tmp_path / ".gitignore").write_text("ignored/\n")
    hidden = tmp_path / "ignored/.secret"
    hidden.mkdir(parents=True)
    (hidden / "snapshot").write_text(json.dumps({"identity": {"label": "2026-10-22a_canary"},
                                                "generation_id": "g", "rows": [row()]}))
    report = audit.original_search(audit.Reader(), tmp_path)
    assert report["ignored_and_hidden_included"]
    assert report["ten22_standalone_ledger_count"] == 1
    assert report["standalone_ledger_candidates"][0]["relative_path"] == "ignored/.secret/snapshot"
    assert "No standalone" not in report["conclusion"]


def test_ttl_bounds_use_duration_not_only_small_gap_and_do_not_assert_actual_hit():
    pair = {"start_to_start_seconds": 505, "previous_end_to_start_seconds": 5}
    assert audit.ttl_classification(pair, 300) == "depends_on_cache_write_or_refresh_time"
    assert audit.ttl_classification(pair, 3600) == "within_ttl_for_both_timestamp_endpoints"
    assert audit.ttl_classification({"start_to_start_seconds": 500, "previous_end_to_start_seconds": 300}, 300) == "expired_for_both_timestamp_endpoints"
    assert audit.ttl_classification({"start_to_start_seconds": 240, "previous_end_to_start_seconds": -20}, 300) == "overlap_cache_publication_unknown"


def test_worker_sample_excludes_truncation_and_keeps_unverified_original_distinct():
    start = datetime(2026, 10, 22, tzinfo=timezone.utc)
    rows = [row("a", seconds=500, started_at=start.isoformat()),
            row("b", seconds=200, started_at=(start + timedelta(seconds=505)).isoformat()),
            row("bad", max_tokens=25000, stop_reason="max_tokens", started_at=(start - timedelta(hours=1)).isoformat())]
    report = audit.timing([{"date": "d", "rows": rows, "original_matching_timing_ids": {"a"}}])
    assert report["completed_worker_seconds"]["count"] == 2
    assert [r["usage_id"] for r in report["excluded_workers"]] == ["bad"]
    assert [r["timing_matches_preserved_original"] for r in report["selected_completed_workers"]] == [True, False]
    assert report["ttl_scenarios"][0]["possible_hits_min"] == 0
    assert report["ttl_scenarios"][0]["possible_hits_max"] == 1
    assert report["ttl_scenarios"][0]["assumed_cold_calls_one_per_run"] == 1


def test_reader_refuses_post_read_mutation(tmp_path):
    path = tmp_path / "evidence"
    path.write_bytes(b"old")
    reader = audit.Reader()
    reader.raw(path)
    path.write_bytes(b"new")
    with pytest.raises(ValueError, match="input changed after"):
        reader.verify()
