"""Offline causal receipt anchoring regressions, E3x F2/F8/F12, 2026-10-29."""
import json
from pathlib import Path
import shutil

import pytest
from data_sheets_schema.evaluation import registered_eval_runner as runner
from tests.test_registered_eval_runner import trace_for
from tests.test_audit_evaluation_comparability import (
    audit, isolated_execution_locks, no_network, no_unmocked_runtime,
    registered_generation_inputs, registered_prepared, registered_case,
    registered_audit, registered_problem, rewrite_plan, save,
    anchor_synthetic_receipt,
)


def test_f2_receipt_and_lock_pin_attempt_files(registered_case):
    _, output, prepared = registered_case
    receipt = json.loads((output / "receipt.json").read_bytes())
    lock = json.loads((runner.LOCK_DIR / f"{prepared.digest}.json").read_bytes())
    assert receipt["format"] == "registered_evaluation_receipt_v2"
    for attempt, rating in zip(receipt["attempts"], receipt["ratings"]):
        folder = output / f'rating-{rating["rating"]:03d}'
        for row in (attempt, rating):
            assert row["transcript_sha256"] == audit.sha((folder / "transcript.jsonl").read_bytes())
            assert row["stderr_sha256"] == audit.sha((folder / "stderr.txt").read_bytes())
            assert row["files"] == ["evaluation.json", "stderr.txt", "transcript.jsonl"]
    assert lock["attempts"] == receipt["attempts"] and lock["ratings"] == receipt["ratings"]
    assert registered_audit(registered_case)["registered_evaluations"][0]["lock_consistent"] is True


@pytest.mark.parametrize("name,reason", [
    ("transcript.jsonl", "registered_transcript_pin_mismatch"),
    ("stderr.txt", "registered_stderr_pin_mismatch"),
])
def test_f2_changed_retained_bytes_are_not_bound(registered_case, name, reason):
    _, output, _ = registered_case
    path = output / "rating-001" / name
    path.write_bytes(path.read_bytes() + b"\n")
    assert registered_problem(registered_audit(registered_case)) == [reason]


@pytest.mark.parametrize("event", [{"type": "user"}, {"type": "system", "subtype": "compact_boundary"},
                                   {"type": "tool_result"}, {"type": "unexpected"}])
def test_f2_impossible_isolated_events_refused(registered_prepared, event):
    events = trace_for(registered_prepared)
    events.insert(1, event)
    with pytest.raises(ValueError, match="event type is not allowed in an isolated no-tools run"):
        runner._accept(registered_prepared, events)


def test_f2_receipt_change_is_detected_by_execution_lock(registered_case):
    _, output, _ = registered_case
    receipt = json.loads((output / "receipt.json").read_bytes())
    receipt["added_after_execution"] = True
    save(output / "receipt.json", receipt)
    assert registered_problem(registered_audit(registered_case)) == ["registered_execution_lock_mismatch"]


def test_f2_replanned_copy_has_no_execution_lock(registered_case):
    _, output, _ = registered_case
    rewrite_plan(output, lambda plan: plan.update(max_cost_dollars="6", reserved_cost_dollars_per_attempt="2.000000"))
    assert registered_problem(registered_audit(registered_case)) == ["registered_execution_lock_missing"]


@pytest.mark.parametrize("field", ["transcript_sha256", "stderr_sha256"])
def test_f2_marked_receipt_requires_pins(registered_case, field):
    _, output, _ = registered_case
    receipt = json.loads((output / "receipt.json").read_bytes())
    receipt["ratings"][0].pop(field)
    save(output / "receipt.json", receipt)
    assert registered_problem(registered_audit(registered_case)) == ["registered_" + field.replace("sha256", "pin_mismatch")]


def test_f2_unavailable_lock_store_is_explicit(registered_case, tmp_path):
    result = registered_audit(registered_case, execution_lock_root=tmp_path / "unavailable")
    package = result["registered_evaluations"][0]
    assert package["reasons"] == []
    assert package["lock_consistent"] is False and package["lock_status"] == "store_unavailable"
    assert package["committed_package"] is False
    assert "Final claims require committed" in result["interpretation"]


def test_f8_started_attempt_is_durable_before_directory_creation(registered_prepared, tmp_path, monkeypatch):
    from tests.test_registered_eval_runner import install_cli
    prepared = registered_prepared
    root = Path(prepared.document()["record"]["path"]).parent
    destination = root / (tmp_path.name + "-interrupted")
    frozen = root / (tmp_path.name + "-kill-snapshot")
    mkdir = Path.mkdir

    def kill_before_directory(path, *args, **kwargs):
        if path == destination / "rating-002":
            saved = json.loads((destination / "receipt.json").read_bytes())
            assert [r["status"] for r in saved["attempts"]] == ["validated", "started"]
            assert saved["unaccounted_reserved_usd"] == prepared.document()["reserved_cost_dollars_per_attempt"]
            shutil.copytree(destination, frozen)
            raise KeyboardInterrupt("snapshot of hard-kill boundary")
        return mkdir(path, *args, **kwargs)

    with monkeypatch.context() as mocked:
        install_cli(mocked, prepared)
        mocked.setattr(Path, "mkdir", kill_before_directory)
        with pytest.raises(KeyboardInterrupt):
            runner.execute(prepared, destination, plan_sha256=prepared.digest, environ={"CBORG_API_KEY": "synthetic"})
    result = registered_audit((root, frozen, prepared))
    assert not registered_problem(result), result["registered_evaluations"]
    assert result["totals"]["bound_registered_rating_files"] == 1
    assert result["registered_evaluations"][0]["attempts"][1]["reason"] == "registered_attempt_failed_or_incomplete"


def test_f12_reported_panel_count_uses_actual_ratings(registered_case):
    _, output, _ = registered_case
    receipt = json.loads((output / "receipt.json").read_bytes())
    receipt.update(status="incomplete", ratings=receipt["ratings"][:1], attempts=receipt["attempts"][:1])
    save(output / "receipt.json", receipt)
    for index in (2, 3):
        shutil.rmtree(output / f"rating-{index:03d}")
    anchor_synthetic_receipt(output)
    result = registered_audit(registered_case)
    assert not registered_problem(result)
    block = result["records"][0]["evaluations"]["rubric20"]
    assert block["repeat_panel"]["reported_n_at_least_three"] is False
    assert block["repeat_panel"]["declared_n"] == [1]
    assert block["files"][0]["planned_repeat_n"] == 3
