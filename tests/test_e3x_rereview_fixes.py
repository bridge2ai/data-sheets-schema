"""Offline causal regressions for claude's E3x re-review R1-R6, 2026-10-29."""
import json
from pathlib import Path

import pytest

from tests.test_audit_evaluation_comparability import (
    audit, isolated_execution_locks, no_network, no_unmocked_runtime,
    registered_audit, registered_case, registered_generation_inputs, registered_prepared,
    registered_problem, registered_roster, rewrite_plan, save, anchor_synthetic_receipt,
)


def test_r1_record_outside_root_is_refused_without_crashing(registered_case):
    # Reviewer rn1: the authority root holds the record; --root holds only packages.
    root, output, prepared = registered_case
    sub_root = output.parent.parent
    record = Path(prepared.document()["record"]["path"])
    assert not record.is_relative_to(sub_root) and output.is_relative_to(sub_root)
    result = audit.audit(sub_root, roster_manifest=registered_roster(registered_case),
        registered_evaluations=[("explicit-v10", output.relative_to(sub_root))],
        authority_roots=[root])
    assert registered_problem(result) == ["registered_record_outside_root"]
    assert result["totals"]["bound_registered_rating_files"] == 0


@pytest.mark.parametrize("lock_available,committed", [(False, False), (False, True), (True, False), (True, True)])
def test_r2_lock_and_commit_pending_reasons_reach_queue(registered_case, tmp_path, monkeypatch,
                                                       lock_available, committed):
    monkeypatch.setattr(audit, "committed_package", lambda capture: committed)
    result = registered_audit(registered_case, **({} if lock_available else
        {"execution_lock_root": tmp_path / "missing-store"}))
    expected = ([] if lock_available else ["execution_lock_unverified"]) + (
        [] if committed else ["package_not_committed"])
    package = result["registered_evaluations"][0]
    assert package["reasons"] == [] and package["status"] == "bound_ratings"
    rows = result["records"][0]["evaluations"]["rubric20"]["files"]
    assert len(rows) == 3 and all(row["pending"] == expected for row in rows)
    assert all(row["eligible_for_condition_review"] == (not expected) for row in rows)
    queued = [row for row in result["rescore_tuples"] if row["rubric"] == "rubric20"]
    assert [row["reasons"] for row in queued] == ([expected] if expected else [])
    assert package["lock_consistent"] is lock_available
    assert "lock_verified" not in package
    if expected:
        assert queued[0]["action"] == "verify_execution_lock_and_commit_package"


def test_r2_unmarked_receipt_cannot_skip_file_pins(registered_case, tmp_path):
    _, output, _ = registered_case
    receipt = json.loads((output / "receipt.json").read_bytes())
    receipt.pop("format")
    for row in receipt["ratings"] + receipt["attempts"]:
        for key in ("transcript_sha256", "stderr_sha256", "files"):
            row.pop(key, None)
    save(output / "receipt.json", receipt)
    (output / "rating-001" / "stderr.txt").write_text("rewritten stderr")
    result = registered_audit(registered_case, execution_lock_root=tmp_path / "missing-store")
    assert registered_problem(result) == ["registered_receipt_format_unsupported"]
    assert result["totals"]["bound_registered_rating_files"] == 0


def test_r1_provenance_outside_root_is_refused_without_crashing(registered_case, tmp_path):
    root, output, prepared = registered_case
    old_pin = prepared.document()["generation_provenance"]
    external = tmp_path / "external-provenance.yaml"
    external.write_bytes(Path(old_pin["path"]).read_bytes())
    assert not external.is_relative_to(root)

    def relocate(plan):
        new_pin = {**old_pin, "path": str(external)}
        plan["generation_provenance"] = new_pin
        plan["authorities"] = [new_pin if pin == old_pin else pin for pin in plan["authorities"]]

    rewrite_plan(output, relocate)
    result = registered_audit(registered_case, authority_roots=[tmp_path])
    assert registered_problem(result) == ["registered_provenance_outside_root"]
    assert result["totals"]["bound_registered_rating_files"] == 0


@pytest.mark.parametrize("event", [{"type": "user"}, {"type": "tool_result"},
                                   {"type": "system", "subtype": "compact_boundary"},
                                   {"type": "unexpected"}])
def test_r4_disallowed_event_has_specific_refusal_after_repinning(registered_case, event):
    _, output, _ = registered_case
    path = output / "rating-001" / "transcript.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    events.insert(1, {**event, "session_id": events[0]["session_id"]})
    path.write_text("\n".join(json.dumps(row) for row in events) + "\n")
    receipt = json.loads((output / "receipt.json").read_bytes())
    for row in (receipt["attempts"][0], receipt["ratings"][0]):
        row["transcript_sha256"] = audit.sha(path.read_bytes())
    save(output / "receipt.json", receipt)
    anchor_synthetic_receipt(output)
    assert registered_problem(registered_audit(registered_case)) == ["registered_event_type_not_allowed"]
