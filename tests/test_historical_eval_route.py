"""Offline historical evaluation canary for #5126; no scoring authorization.

Use the real admission, released instrument validation, receipt writer and
saved-package audit. Only the external evaluator process is replaced.
"""
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation import historical_eval_binding as historical
from data_sheets_schema.evaluation import registered_eval_runner as runner
from tests.test_audit_evaluation_comparability import audit
from tests.test_registered_eval_runner import install_cli, no_provider, sha


@pytest.fixture
def historical_inputs(tmp_path):
    """Fresh fictional authorities, returned as prepare_historical keyword args.

    All retained fixture evidence lives beneath ``record.parent``. Cohort and
    decision paths are the corresponding pins in ``registration``. The fixture
    deliberately has no shared registration, recorded generation age, runtime
    integrity block, or ``run.condition``.
    """
    root = tmp_path.resolve() / "historical-evidence"
    root.mkdir()
    record = root / "retained-full.yaml"
    label = "historical-fixture-rep1"
    record.write_text(
        f"# Label: {label}\nrun_label: {label}\n"
        "conforms_to_class: Dataset\nid: example:dataset\n"
        "name: Fictional scientific dataset\n"
        "description: Source text must be retained exactly.\n"
        "resources:\n- id: example:child\n  name: Child dataset\n"
    )
    project, condition = "FICTIONAL_STUDY", "historical-fixture-condition"
    provenance = root / "retained-provenance.yaml"
    provenance.write_text(yaml.safe_dump({
        "record_type": "d4d_generation_provenance",
        "run": {"project": project, "label": label, "method": "claudecode_api",
                "arm": "baseline", "replicate": 1},
        "prompts": {"request": {"spec": {"condition": condition}}},
        "validation": {"passed": True, "artifacts": {"full": {
            "path": str(record), "sha256": sha(record.read_bytes()),
        }}},
    }))
    cohort = root / "declared-cohort.yaml"
    cohort.write_text(yaml.safe_dump({
        "format": "evaluation_cohort_v1", "cells": [{
            "arm": "historical", "projects": [project], "replicates": [1],
            "label_template": label, "method": "claudecode_api", "input_arm": "baseline",
            "condition": condition, "comparison_arm": "historical-comparison",
        }],
    }))
    decision = root / "fixture-decision.md"
    decision.write_text(
        "# Fixture selection decision\n\n"
        "This fictional cohort exercises offline artifact admission only.\n"
        "It grants no scientific approval or permission to score real records.\n"
    )
    binding = root / "historical-binding.json"
    binding.write_bytes(runner.shared.canonical({
        "format": historical.FORMAT, "record_role": "full",
        "record": runner.shared.file_pin(record, record.read_bytes()),
        "provenance": runner.shared.file_pin(provenance, provenance.read_bytes()),
        "cohort": runner.shared.file_pin(cohort, cohort.read_bytes()),
        "decision": runner.shared.file_pin(decision, decision.read_bytes()),
        "decision_reference": "fictional-selection-v1",
        "condition_pointer": "/prompts/request/spec/condition",
    }))
    context = root / "applicability.json"
    context.write_text(json.dumps({
        "human_subjects": {"value": None, "evidence": "Synthetic unresolved predicate"},
    }))
    runtime = root / "synthetic-runtime"
    runtime.write_bytes(b"synthetic runtime bytes, never executed\n")
    return {
        "registration": binding, "registration_sha256": sha(binding.read_bytes()),
        "record": record, "record_sha256": sha(record.read_bytes()),
        "provenance": provenance, "provenance_sha256": sha(provenance.read_bytes()),
        "context": context, "context_sha256": sha(context.read_bytes()),
        "rubric": "rubric20", "instrument_version": "3.0", "repeat_count": 1,
        "model": "claude-opus-5", "canonical_model": "claude-opus-5",
        "base_url": runner.CBORG_BASE_URL, "context_window": 1_000_000,
        "runtime": runtime, "runtime_sha256": sha(runtime.read_bytes()),
        "runtime_version": "2.1.269", "max_cost_dollars": "5",
        "comparison_arm": "historical-comparison",
    }


def test_historical_full_record_prepare_execute_saved_package_audit(historical_inputs, monkeypatch):
    root = historical_inputs["record"].parent
    source_before = {path: path.read_bytes() for path in root.iterdir() if path.is_file()}
    binding = json.loads(historical_inputs["registration"].read_bytes())
    original_provenance = yaml.safe_load(historical_inputs["provenance"].read_bytes())
    assert "shared_generation" not in original_provenance
    assert "condition" not in original_provenance["run"]

    prepared = runner.prepare_historical(**historical_inputs)
    plan = prepared.document()
    assert plan["format"] == historical.EVALUATION_FORMAT
    assert plan["generation_authority_kind"] == historical.KIND
    assert plan["generation_registration"] is None and plan["omission_context"] is None
    assert plan["historical_identity"]["normalized_run"]["condition"] == (
        original_provenance["prompts"]["request"]["spec"]["condition"]
    )
    assert plan["historical_identity"]["evidence_status"] == {
        "generation_registration": "not_recorded", "generation_acceptance": "not_established",
    }
    assert prepared.generation_record_age == "age unestablished"
    assert plan["scientific_review_verified"] is False
    assert plan["generation_acceptance_verified"] is False

    output = root / "new-evaluation"
    with monkeypatch.context() as mocked:
        calls = install_cli(mocked, prepared)
        receipt = runner.execute(prepared, output, plan_sha256=prepared.digest,
                                 environ={"CBORG_API_KEY": "synthetic-never-sent"})
    assert receipt["status"] == "validated", receipt
    assert len(calls) == receipt["runtime_attempts"] == 1
    assert receipt["model_calls"] is None
    assert receipt["cost_accounting_complete"] is True
    assert receipt["total_cost_usd"] == "0.75"
    assert len(receipt["ratings"]) == 1
    assert receipt["ratings"][0]["purpose"] == "primary"

    expected_bytes = {
        "registration.json": prepared.manifest, "original.yaml": prepared.original,
        "record.yaml": prepared.blinded, "context.json": prepared.context,
        "effective_system.txt": prepared.system_prompt,
        "predecessor.md": prepared.predecessor.encode(),
        "execution_adapter.txt": runner.EXECUTION_ADAPTER.encode(),
        "prompt.txt": runner.rating_prompt(prepared).encode(),
        **{"instrument/" + rel: raw for rel, raw in prepared.resources},
    }
    for relative, expected in expected_bytes.items():
        path = output / relative
        assert path.is_file() and path.stat().st_size > 0, relative
        assert path.read_bytes() == expected, relative
    assert prepared.original != prepared.blinded
    assert json.loads((output / "receipt.json").read_bytes()) == receipt
    rating = receipt["ratings"][0]
    for name, pin in (("evaluation.json", "evaluation_sha256"),
                      ("transcript.jsonl", "transcript_sha256"),
                      ("stderr.txt", "stderr_sha256")):
        path = output / "rating-001" / name
        assert path.is_file() and path.stat().st_size > 0, name
        assert sha(path.read_bytes()) == rating[pin], name
    lock_path = Path(runner.LOCK_DIR) / (prepared.digest + ".json")
    lock_before = lock_path.read_bytes()
    lock = json.loads(lock_before)
    assert lock["plan_sha256"] == prepared.digest
    assert lock["receipt_sha256"] == sha((output / "receipt.json").read_bytes())
    assert Path(lock["receipt_path"]) == (output / "receipt.json").resolve()
    assert lock["attempts"] == receipt["attempts"] and lock["ratings"] == receipt["ratings"]
    command, process = calls[0]
    assert command[0] == str(historical_inputs["runtime"])
    assert command[command.index("--tools") + 1] == ""
    assert command[command.index("--system-prompt") + 1].encode() == prepared.system_prompt
    assert process["input"] == runner.rating_prompt(prepared)
    assert process["env"]["ANTHROPIC_BASE_URL"] == runner.CBORG_BASE_URL
    assert not Path(process["cwd"]).exists()

    package_before = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    result = audit.audit(
        root, roster_manifest=Path(binding["cohort"]["path"]),
        historical_decisions=[Path(binding["decision"]["path"])],
        evaluator_model=plan["runtime"]["canonical_model"],
        contexts={plan["generation_run"]["project"]: json.loads(prepared.context)},
        registered_evaluations=[("historical", output)],
    )
    assert len(result["registered_evaluations"]) == 1
    package = result["registered_evaluations"][0]
    assert package["reasons"] == [], package
    assert package["generation_authority_kind"] == historical.KIND
    assert package["historical_identity"] == plan["historical_identity"]
    assert package["generation_acceptance_verified"] is False
    assert package["lock_consistent"] is True and package["lock_status"] == "consistent"
    assert package["committed_package"] is False
    assert len(result["records"]) == 1
    rows = result["records"][0]["evaluations"]["rubric20"]["files"]
    assert len(rows) == 1
    row = rows[0]
    assert row["contract_checked"] is True and row["reasons"] == []
    assert row["pending"] == ["package_not_committed"]
    assert row["eligible_for_condition_review"] is False
    assert row["manifest_sha256"] == prepared.digest
    assert row["receipt_sha256"] == sha((output / "receipt.json").read_bytes())
    assert row["transcript_sha256"] == rating["transcript_sha256"]
    assert row["original_sha256"] == sha(prepared.original)
    assert row["input_hashes"]["input_sha256"] == sha(prepared.blinded)
    assert len(result["records"]) == 1
    record = result["records"][0]
    assert record["registered_run"] == plan["generation_run"] and record["replicate"] == 1
    accepted = record["evaluations"]["rubric20"]
    assert accepted["file_count"] == 1 and accepted["reasons"] == ["package_not_committed"]
    assert accepted["comparable_for_final_v10"] is False
    assert result["targets"]["context_human_review_verified"] is False
    assert source_before == {path: path.read_bytes() for path in source_before}
    assert package_before == {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    assert lock_path.read_bytes() == lock_before
