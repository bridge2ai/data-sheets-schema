"""E3x review (2026-10-29): one targeted input per ingestion guard that no shipped test kills.

Purpose: show each guard fires on unmodified code (so these are the missing tests).
Inputs: the fb34ed882 tree on PYTHONPATH; the repository's own fixtures and mock.
Outputs: pass/fail only. No provider call.
"""
import json
import shutil
from pathlib import Path

import yaml

from tests.test_audit_evaluation_comparability import (  # noqa: F401  (fixtures)
    audit, isolated_execution_locks, no_network, no_unmocked_runtime,
    registered_audit, registered_case, registered_generation_inputs, registered_prepared,
    registered_problem, rewrite_plan, save, registered_roster,
)


def _events(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _receipt(output):
    return json.loads((output / "receipt.json").read_bytes())


def test_kill_I2_saved_evaluation_differs_from_transcript(registered_case):
    _, output, _ = registered_case
    from data_sheets_schema.evaluation import registered_eval_runner as runner
    path = output / "rating-001" / "evaluation.json"
    doc = json.loads(path.read_bytes())
    doc["metadata"]["note_added_after_run"] = "edited"
    raw = runner.shared.canonical(doc)
    path.write_bytes(raw)
    receipt = _receipt(output)
    receipt["ratings"][0]["evaluation_sha256"] = audit.sha(raw)
    save(output / "receipt.json", receipt)
    assert "registered_transcript_evaluation_mismatch" in registered_problem(registered_audit(registered_case))


def test_kill_I4_same_session_twice_in_one_package(registered_case):
    _, output, _ = registered_case
    path = output / "rating-002" / "transcript.jsonl"
    events = _events(path)
    for event in events:
        if "session_id" in event:
            event["session_id"] = "synthetic-session-1"
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    receipt = _receipt(output)
    receipt["ratings"][1]["session_id"] = "synthetic-session-1"
    # Isolate session reuse from the independent retained-byte guard.
    for row in (receipt["ratings"][1], receipt["attempts"][1]):
        row["transcript_sha256"] = audit.sha(path.read_bytes())
    save(output / "receipt.json", receipt)
    assert "registered_session_reused_or_mismatched" in registered_problem(registered_audit(registered_case))


def test_kill_I5_provenance_embeds_another_registration(registered_case):
    _, output, prepared = registered_case
    prior = Path(prepared.document()["generation_provenance"]["path"])
    doc = yaml.safe_load(prior.read_bytes())
    doc["shared_generation"]["authority"]["registration"]["raw_json"] += " "
    raw = yaml.safe_dump(doc).encode()
    new = output.parent / "other-registration-provenance.yaml"
    new.write_bytes(raw)
    def mutate(plan):
        old = plan["generation_provenance"]
        pin = {"path": str(new), "sha256": audit.sha(raw), "bytes": len(raw)}
        plan["generation_provenance"] = pin
        plan["authorities"] = [pin if entry == old else entry for entry in plan["authorities"]]
    rewrite_plan(output, mutate)
    assert "registered_provenance_registration_mismatch" in registered_problem(registered_audit(registered_case))


def test_kill_I12_receipt_cost_differs_from_transcript(registered_case):
    _, output, _ = registered_case
    receipt = _receipt(output)
    receipt["ratings"][0]["estimated_cost_usd"] = "0.5"
    save(output / "receipt.json", receipt)
    assert "registered_rating_receipt_mismatch" in registered_problem(registered_audit(registered_case))


def test_kill_I17_noncanonical_manifest(registered_case):
    _, output, _ = registered_case
    plan = json.loads((output / "registration.json").read_bytes())
    raw = json.dumps(plan, indent=2, sort_keys=True).encode()
    (output / "registration.json").write_bytes(raw)
    receipt = _receipt(output)
    receipt.update(plan=plan, plan_sha256=audit.sha(raw))
    save(output / "receipt.json", receipt)
    assert "registered_manifest_format_or_encoding" in registered_problem(registered_audit(registered_case))


def test_kill_I20_validated_receipt_with_short_panel(registered_case):
    _, output, _ = registered_case
    receipt = _receipt(output)
    receipt.update(ratings=receipt["ratings"][:2], attempts=receipt["attempts"][:2])
    save(output / "receipt.json", receipt)
    shutil.rmtree(output / "rating-003")
    assert "registered_validated_panel_incomplete" in registered_problem(registered_audit(registered_case))


def test_kill_I21_validated_attempt_with_nonzero_exit(registered_case):
    _, output, _ = registered_case
    receipt = _receipt(output)
    receipt["attempts"][0]["exit_code"] = 1
    save(output / "receipt.json", receipt)
    assert "registered_rating_not_validated" in registered_problem(registered_audit(registered_case))


def test_kill_I25_other_execution_mode(registered_case):
    _, output, _ = registered_case
    rewrite_plan(output, lambda plan: plan.update(execution_mode="tools_allowed"))
    assert "registered_execution_mode_unsupported" in registered_problem(registered_audit(registered_case))


def test_kill_I28_registered_rows_against_other_context(registered_case):
    root, output, prepared = registered_case
    project = prepared.document()["generation_run"]["project"]
    other_context = audit.audit(root, roster_manifest=registered_roster(registered_case), evaluator_model=prepared.document()["runtime"]["canonical_model"],
                                contexts={project: {"human_subjects": {"value": True, "evidence": "Other."}}},
                                registered_evaluations=[("explicit-v10", output)])
    rows = other_context["records"][0]["evaluations"]["rubric20"]["files"]
    assert all("applicability_context_differs_from_target" in row["reasons"] for row in rows)


def test_kill_I29_registered_rows_against_other_model(registered_case):
    root, output, prepared = registered_case
    other_model = audit.audit(root, roster_manifest=registered_roster(registered_case), evaluator_model="another-evaluator",
                              registered_evaluations=[("explicit-v10", output)])
    rows = other_model["records"][0]["evaluations"]["rubric20"]["files"]
    assert all("evaluator_differs_from_target" in row["reasons"] for row in rows)


def test_kill_B4_registered_label_in_scientific_text_without_header(registered_generation_inputs, tmp_path):
    """The shared gate's own Record identity is the only thing forbidding a headerless label."""
    import pytest
    from tests import test_registered_eval_runner as support
    raw = (b"conforms_to_class: Dataset\nid: example:dataset\nname: Fictional scientific dataset\n"
           b"description: Derived in run concealed-v10-rep17 of this study.\n")
    inputs = support.rebind_record(dict(registered_generation_inputs), tmp_path, raw)
    with pytest.raises(ValueError, match="identity"):
        support.runner.prepare(**inputs)
