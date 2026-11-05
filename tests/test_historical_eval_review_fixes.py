"""Offline regression probes for independent review F1–F12, #5126 (2026-11-05)."""
from copy import deepcopy
from pathlib import Path
import subprocess

import pytest
import yaml

from data_sheets_schema import latch_journal
from data_sheets_schema.evaluation import registered_eval_runner as runner
from tests.test_historical_eval_route import historical_inputs
from tests.test_historical_eval_admission import binding_document, write_binding, rebind_provenance, rebind_evidence
from tests.test_registered_eval_runner import no_provider
from tests.test_audit_evaluation_comparability import (
    audit, registered_case, registered_generation_inputs, registered_prepared, registered_audit, registered_problem, rewrite_plan,
)


def test_default_prepare_never_sniffs_historical_binding(historical_inputs):
    # First prove the exact binding is valid through its explicit route.
    runner.prepare_historical(**historical_inputs)
    with pytest.raises(ValueError, match="unsupported shared registration format"):
        runner.prepare(**historical_inputs)


def test_default_cli_never_sniffs_historical_binding(historical_inputs, capsys):
    args = [part for key, value in historical_inputs.items()
            for part in ("--" + key.replace("_", "-"), str(value))]
    output = historical_inputs["record"].parent / "refused-output"
    with pytest.raises(SystemExit) as exc:
        runner.main([*args, "--output", str(output), "--dry-run"])
    assert exc.value.code == 2
    assert "unsupported shared registration format" in capsys.readouterr().err
    assert not output.exists()


def test_authority_kind_must_be_explicit_and_supported(historical_inputs):
    with pytest.raises(ValueError, match="explicit supported"):
        runner.prepare(**historical_inputs, authority_kind="other")
    with pytest.raises(ValueError, match="fixes its own authority"):
        runner.prepare_historical(**historical_inputs, authority_kind="historical_provenance_v1")


@pytest.mark.parametrize("component", ["record", "provenance", "cohort", "decision"])
def test_correct_digest_wrong_byte_count_refuses(historical_inputs, component):
    binding = binding_document(historical_inputs)
    binding[component]["bytes"] += 1
    inputs = write_binding(historical_inputs, binding)
    with pytest.raises(ValueError, match="captured evidence differs from its pin"):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("age", ["unknown", "modern"])
def test_only_positive_historical_age_admits(historical_inputs, age):
    prior = yaml.safe_load(historical_inputs["provenance"].read_bytes())
    prior.pop("record_generated_at")
    if age == "modern":
        prior["repo"] = {"commit": latch_journal.D41_COMMIT}
        prior["model"] = {"runtime_integrity": {
            "format": latch_journal.FORMAT, "verified": True, "assisted": False,
            "evidence_only": False, "overrides": [],
            "journal": {"path": "journal.jsonl", "sha256": "a" * 64,
                        "head_sha256": "b" * 64, "line_count": 1},
            "authentication": "not_cryptographically_authenticated"}}
        runner.require_eligible_generation(prior)
    with pytest.raises(ValueError, match="positive pre-D41 age evidence"):
        runner.prepare_historical(**rebind_provenance(historical_inputs, prior))


def test_new_timestamp_on_historical_code_lineage_is_admissible(historical_inputs):
    prior = yaml.safe_load(historical_inputs["provenance"].read_bytes())
    prior["record_generated_at"] = "2026-11-05T00:00:00+00:00"
    root = Path(runner.__file__).resolve().parents[3]
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse",
                                     latch_journal.D41_COMMIT + "^"], text=True).strip()
    prior["repo"] = {"commit": commit}
    prepared = runner.prepare_historical(**rebind_provenance(historical_inputs, prior))
    assert prepared.generation_record_age == "pre-D41"


def test_excluded_record_cannot_be_added_to_pinned_roster(historical_inputs):
    root = Path(__file__).resolve().parents[1]
    cohort = yaml.safe_load((root / "configs/evaluation/d64_retained_v8_comparator.yaml").read_bytes())
    cohort["cells"][1]["projects"].append("AI_READI")
    inputs = rebind_evidence(historical_inputs, "cohort", yaml.safe_dump(cohort).encode())
    with pytest.raises(ValueError, match="matches a declared exclusion"):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("key,value", [
    ("historical_identity", {}), ("historical_binding", {}),
    ("generation_authority_kind", "historical_provenance_v1"), ("unknown", None),
])
def test_shared_manifest_rejects_foreign_fields(registered_case, key, value):
    rewrite_plan(registered_case[1], lambda plan: plan.update({key: value}))
    assert registered_problem(registered_audit(registered_case)) == ["registered_shared_manifest_contract"]


def test_missing_common_pin_names_specific_refusal(registered_case):
    module = "evaluation/run_identity.py"
    def mutate(plan):
        plan["authorities"] = [pin for pin in plan["authorities"] if not pin["path"].endswith("/" + module)]
    rewrite_plan(registered_case[1], mutate)
    reasons = registered_problem(registered_audit(registered_case))
    assert len(reasons) == 1
    assert reasons[0].startswith("registered_condition_identity_incomplete:") and module in reasons[0]


def test_shared_repeat_panel_does_not_pool_different_repeat_keys(registered_case):
    result = registered_audit(registered_case)
    rows = result["records"][0]["evaluations"]["rubric20"]["files"]
    assert audit.repeat_panel(rows)["three_distinct_session_claims_present"] is True
    split = deepcopy(rows)
    split[-1]["repeat_key"] = "different-fixed-input-or-per-attempt-cap"
    assert audit.repeat_panel(split)["three_distinct_session_claims_present"] is False
    assert audit.repeat_panel(split)["condition_groups"] == 2


def test_real_mixed_condition_group_labels_each_evidence_kind(
        registered_case, registered_generation_inputs, historical_inputs, monkeypatch):
    from tests.test_historical_eval_parity import equivalent_historical_inputs
    from tests.test_historical_eval_audit import historical_audit
    from tests.test_registered_eval_runner import install_cli
    shared_prior = yaml.safe_load(registered_generation_inputs["provenance"].read_bytes())
    shared_prior["run"]["replicate"] = 17
    counterpart = historical_inputs["record"].parent / "shared-counterpart.yaml"
    counterpart.write_text(yaml.safe_dump(shared_prior))
    inputs = equivalent_historical_inputs(
        {**registered_generation_inputs, "repeat_count": 3, "provenance": counterpart}, historical_inputs)
    prepared = runner.prepare_historical(**inputs)
    output = inputs["record"].parent / "mixed-historical"
    with monkeypatch.context() as mocked:
        install_cli(mocked, prepared)
        runner.execute(prepared, output, plan_sha256=prepared.digest,
                       environ={"CBORG_API_KEY": "synthetic-never-sent"})
    binding = binding_document(inputs)
    historical = historical_audit({"prepared": prepared, "output": output,
        "root": inputs["record"].parent, "cohort": Path(binding["cohort"]["path"]),
        "decision": Path(binding["decision"]["path"])})
    shared = registered_audit(registered_case)
    for report, kind in ((historical, "historical_provenance_v1"), (shared, "shared_generation_v1")):
        assert report["registered_evaluations"][0]["reasons"] == []
        assert report["registered_evaluations"][0]["generation_authority_kind"] == kind
        assert all(row["generation_authority_kind"] == kind
                   for row in report["records"][0]["evaluations"]["rubric20"]["files"])
    groups = audit.evaluation_condition_groups(historical["records"] + shared["records"])
    assert len(groups) == 1
    assert groups[0]["generation_authority_kinds"] == {"historical_provenance_v1": 3, "shared_generation_v1": 3}
    assert len({member["repeat_key"] for member in groups[0]["members"]}) == 2


def test_stale_size_claim_survives_preparation_and_audit(historical_inputs, monkeypatch):
    from tests.test_historical_eval_audit import historical_audit
    from tests.test_registered_eval_runner import install_cli
    prior = yaml.safe_load(historical_inputs["provenance"].read_bytes())
    prior["outputs"] = {"full": {"bytes": 1}}
    inputs = rebind_provenance(historical_inputs, prior)
    prepared = runner.prepare_historical(**inputs)
    expected = [{"source": "outputs.full.bytes", "claimed": 1,
                 "actual": len(prepared.original)}]
    assert prepared.document()["historical_identity"]["recorded_byte_claim_disagreements"] == expected
    output = inputs["record"].parent / "size-disagreement"
    with monkeypatch.context() as mocked:
        install_cli(mocked, prepared)
        runner.execute(prepared, output, plan_sha256=prepared.digest,
                       environ={"CBORG_API_KEY": "synthetic-never-sent"})
    binding = binding_document(inputs)
    result = historical_audit({"prepared": prepared, "output": output,
        "root": inputs["record"].parent, "cohort": Path(binding["cohort"]["path"]),
        "decision": Path(binding["decision"]["path"])})
    assert result["registered_evaluations"][0]["reasons"] == []
    assert result["registered_evaluations"][0]["recorded_byte_claim_disagreements"] == expected
