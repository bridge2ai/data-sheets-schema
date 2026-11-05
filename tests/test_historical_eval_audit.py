"""Offline historical audit joins and distinct condition/repeat keys (#5126)."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml

from data_sheets_schema.evaluation import registered_eval_runner as runner
from data_sheets_schema.evaluation.evaluation_identity import evaluation_condition_key, repeat_key
from tests.test_audit_evaluation_comparability import audit, rewrite_plan
from tests.test_historical_eval_route import historical_inputs
from tests.test_registered_eval_runner import install_cli, no_provider


@pytest.fixture
def historical_case(historical_inputs, monkeypatch):
    prepared = runner.prepare_historical(**historical_inputs)
    binding = json.loads(historical_inputs["registration"].read_bytes())
    root = historical_inputs["record"].parent
    output = root / "audit-rating-package"
    with monkeypatch.context() as mocked:
        calls = install_cli(mocked, prepared)
        receipt = runner.execute(prepared, output, plan_sha256=prepared.digest,
                                 environ={"CBORG_API_KEY": "synthetic-never-sent"})
    assert receipt["status"] == "validated" and len(calls) == 1
    return {"root": root, "output": output, "prepared": prepared,
            "cohort": Path(binding["cohort"]["path"]), "decision": Path(binding["decision"]["path"])}


def historical_audit(case, **changes):
    prepared = case["prepared"]
    plan = prepared.document()
    roster, _ = audit.read_cohort(case["cohort"])
    options = {"roster_manifest": case["cohort"], "historical_decisions": [case["decision"]],
               "evaluator_model": plan["runtime"]["canonical_model"],
               "contexts": {plan["generation_run"]["project"]: json.loads(prepared.context)},
               "registered_evaluations": [(roster[0]["arm"], case["output"])]}
    return audit.audit(case["root"], **{**options, **changes})


def historical_problem(result):
    return result["registered_evaluations"][0]["reasons"]


def test_saved_historical_rating_is_bound_without_generation_acceptance(historical_case):
    before = {path: path.read_bytes() for path in historical_case["root"].rglob("*") if path.is_file()}
    result = historical_audit(historical_case)
    assert historical_problem(result) == []
    package = result["registered_evaluations"][0]
    assert package["generation_authority_kind"] == "historical_provenance_v1"
    assert package["generation_acceptance_verified"] is False
    assert package["historical_identity"]["evidence_status"] == {
        "generation_registration": "not_recorded", "generation_acceptance": "not_established"}
    block = result["records"][0]["evaluations"]["rubric20"]
    assert block["file_count"] == 1 and block["comparable_for_final_v10"] is False
    assert block["repeat_panel"]["three_distinct_session_claims_present"] is False
    row = block["files"][0]
    plan = historical_case["prepared"].document()
    assert row["evaluation_condition_key"] == evaluation_condition_key(plan)
    assert row["repeat_key"] == repeat_key(plan)
    groups = result["evaluation_condition_groups"]
    assert len(groups) == 1 and groups[0]["record_count"] == groups[0]["bound_rating_files"] == 1
    assert groups[0]["members"][0]["manifest_sha256"] == row["manifest_sha256"]
    assert groups[0]["members"][0]["pending"] == ["package_not_committed"]
    assert groups[0]["comparable_for_final_v10"] is False
    assert result["targets"]["context_human_review_verified"] is False
    assert before == {path: path.read_bytes() for path in historical_case["root"].rglob("*") if path.is_file()}


def test_committed_historical_package_reaches_condition_review_without_scientific_acceptance(
        historical_case, monkeypatch):
    root, output = historical_case["root"], historical_case["output"]
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    # Git must operate only in this fresh synthetic fixture, without inherited
    # repository selection, configuration, templates, hooks, or signing.
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_ATTR_NOSYSTEM", "1")
    command = ["git", "-c", "core.hooksPath=" + os.devnull,
               "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false",
               "-c", "user.name=Synthetic Fixture", "-c", "user.email=fixture@example.invalid"]
    for arguments in (
        ["init", "--quiet", "--template=", "--initial-branch=fixture"],
        ["add", "--", output.relative_to(root).as_posix()],
        ["commit", "--quiet", "--no-gpg-sign", "-m", "Capture synthetic evaluation evidence"],
    ):
        subprocess.run([*command, *arguments], cwd=root, check=True, capture_output=True)

    result = historical_audit(historical_case)
    package = result["registered_evaluations"][0]
    assert package["reasons"] == []
    assert package["committed_package"] is True
    assert package["lock_consistent"] is True and package["lock_status"] == "consistent"
    assert package["generation_acceptance_verified"] is False
    block = result["records"][0]["evaluations"]["rubric20"]
    assert block["status"] == "condition_review_pending"
    assert block["reasons"] == block["pending"] == []
    assert block["comparable_for_final_v10"] is False
    assert block["files"][0]["eligible_for_condition_review"] is True
    assert block["files"][0]["pending"] == []
    group = result["evaluation_condition_groups"][0]
    assert group["members"][0]["eligible_for_condition_review"] is True
    assert group["members"][0]["pending"] == []
    assert group["comparable_for_final_v10"] is False
    assert group["context_human_review_verified"] is False
    assert group["independence_verified"] is False
    assert historical_case["prepared"].document()["scientific_review_verified"] is False
    after = {path: path.read_bytes() for path in root.rglob("*")
             if path.is_file() and ".git" not in path.relative_to(root).parts}
    assert before == after


@pytest.mark.parametrize("selection", ["missing", "other", "duplicate"])
def test_historical_decision_must_be_selected_independently(historical_case, selection):
    selected = []
    if selection == "other":
        other = historical_case["root"] / "different-decision.md"
        other.write_text("Another explicit decision; never human approval.\n")
        selected = [other]
    elif selection == "duplicate":
        selected = [historical_case["decision"], historical_case["decision"]]
    result = historical_audit(historical_case, historical_decisions=selected)
    assert historical_problem(result) == ["registered_historical_decision_not_selected"]
    assert result["totals"]["bound_registered_rating_files"] == 0


def test_same_cohort_bytes_at_unselected_path_do_not_replace_pinned_selection(historical_case):
    other = historical_case["root"] / "other-cohort.yaml"
    other.write_bytes(historical_case["cohort"].read_bytes())
    result = historical_audit(historical_case, roster_manifest=other)
    assert historical_problem(result) == ["registered_historical_cohort_not_selected"]


@pytest.mark.parametrize(("mutation", "reason"), [
    ("unknown_format", "registered_manifest_format_or_encoding"),
    ("shared_format", "registered_pin_invalid"),
    ("kind", "registered_historical_authority_kind_mismatch"),
    ("historical_identity", "registered_historical_identity_mismatch"),
    ("extra_field", "registered_historical_manifest_contract"),
    ("claimed_acceptance", "registered_historical_manifest_contract"),
])
def test_historical_manifest_dispatch_and_identity_fail_closed(historical_case, mutation, reason):
    def change(plan):
        if mutation == "unknown_format":
            plan["format"] = "unsupported_historical_format"
        elif mutation == "shared_format":
            plan["format"] = runner.FORMAT
        elif mutation == "kind":
            plan["generation_authority_kind"] = "shared_generation_v1"
        elif mutation == "historical_identity":
            plan["historical_identity"]["normalized_run"]["condition"] = "invented-condition"
        elif mutation == "extra_field":
            plan["invented_authority"] = True
        else:
            plan["generation_acceptance_verified"] = True
    rewrite_plan(historical_case["output"], change)
    result = historical_audit(historical_case)
    assert historical_problem(result) == [reason]
    assert result["totals"]["bound_registered_rating_files"] == 0


@pytest.mark.parametrize(("component", "reason"), [
    ("record", "registered_authority_pin_mismatch"),
    ("generation_provenance", "registered_authority_pin_mismatch"),
    ("cohort", "registered_authority_pin_mismatch"),
    ("decision", "registered_authority_pin_mismatch"),
    ("original.yaml", "registered_original_copy_mismatch"),
    ("record.yaml", "registered_blinded_input_mismatch"),
    ("prompt.txt", "registered_prompt_unsupported_or_mismatched"),
    ("effective_system.txt", "registered_adapter_unsupported_or_mismatched"),
    ("rating-001/evaluation.json", "registered_evaluation_pin_mismatch"),
    ("rating-001/transcript.jsonl", "registered_transcript_pin_mismatch"),
])
def test_historical_saved_evidence_bytes_are_rechecked(historical_case, component, reason):
    if component in {"record", "generation_provenance"}:
        path = Path(historical_case["prepared"].document()[component]["path"])
    elif component in {"cohort", "decision"}:
        path = historical_case[component]
    else:
        path = historical_case["output"] / component
    path.write_bytes(path.read_bytes() + b"\n")
    result = historical_audit(historical_case)
    assert historical_problem(result) == [reason]
    assert result["totals"]["bound_registered_rating_files"] == 0


@pytest.mark.parametrize("module", ["historical_eval_binding.py", "cohort_manifest.py"])
def test_historical_admission_implementation_pins_cannot_be_removed(historical_case, module):
    def change(plan):
        plan["authorities"] = [pin for pin in plan["authorities"]
                               if not pin["path"].endswith("/evaluation/" + module)]
    rewrite_plan(historical_case["output"], change)
    result = historical_audit(historical_case)
    assert historical_problem(result) == ["registered_historical_implementation_pin_missing"]
    assert result["totals"]["bound_registered_rating_files"] == 0
    assert result["evaluation_condition_groups"] == []


@pytest.mark.parametrize("authority", ["decision", "cohort", "historical_binding"])
def test_same_byte_historical_authority_alias_is_refused(historical_case, authority):
    if authority == "historical_binding":
        path = Path(historical_case["prepared"].document()[authority]["path"])
    else:
        path = historical_case[authority]
    target = path.with_name(path.name + ".retained-copy")
    path.rename(target)
    path.symlink_to(target)
    result = historical_audit(historical_case)
    assert historical_problem(result) == ["registered_historical_authority_alias"]
    assert result["totals"]["bound_registered_rating_files"] == 0


def test_actual_distinct_records_share_condition_group_without_inflating_repeats(historical_inputs, monkeypatch):
    root = historical_inputs["record"].parent
    first_binding = json.loads(historical_inputs["registration"].read_bytes())
    cohort_path = Path(first_binding["cohort"]["path"])
    cohort = yaml.safe_load(cohort_path.read_bytes())
    cohort["cells"][0].update(replicates=[1, 2], label_template="historical-fixture-rep{replicate}")
    cohort_path.write_text(yaml.safe_dump(cohort))
    first_binding["cohort"] = runner.shared.file_pin(cohort_path, cohort_path.read_bytes())
    historical_inputs["registration"].write_bytes(runner.shared.canonical(first_binding))
    first_inputs = {**historical_inputs,
                    "registration_sha256": audit.sha(historical_inputs["registration"].read_bytes())}

    second_record = root / "second-full.yaml"
    second_record.write_bytes(historical_inputs["record"].read_bytes()
        .replace(b"historical-fixture-rep1", b"historical-fixture-rep2")
        .replace(b"Source text must be retained exactly.", b"Another independently retained description."))
    second_provenance = root / "second-provenance.yaml"
    prior = yaml.safe_load(historical_inputs["provenance"].read_bytes())
    prior["run"].update(label="historical-fixture-rep2", replicate=2)
    prior["validation"]["artifacts"]["full"] = {
        "path": str(second_record), "sha256": audit.sha(second_record.read_bytes())}
    second_provenance.write_text(yaml.safe_dump(prior))
    second_binding = {**first_binding,
        "record": runner.shared.file_pin(second_record, second_record.read_bytes()),
        "provenance": runner.shared.file_pin(second_provenance, second_provenance.read_bytes())}
    second_binding_path = root / "second-binding.json"
    second_binding_path.write_bytes(runner.shared.canonical(second_binding))
    second_inputs = {**first_inputs, "registration": second_binding_path,
        "registration_sha256": audit.sha(second_binding_path.read_bytes()), "record": second_record,
        "record_sha256": audit.sha(second_record.read_bytes()), "provenance": second_provenance,
        "provenance_sha256": audit.sha(second_provenance.read_bytes())}

    outputs = []
    for index, inputs in enumerate((first_inputs, second_inputs), 1):
        prepared = runner.prepare_historical(**inputs)
        output = root / f"ratings-{index}"
        with monkeypatch.context() as mocked:
            calls = install_cli(mocked, prepared)
            receipt = runner.execute(prepared, output, plan_sha256=prepared.digest,
                                     environ={"CBORG_API_KEY": "synthetic-never-sent"})
        assert receipt["status"] == "validated" and len(calls) == 1
        outputs.append(("historical", output))
    result = audit.audit(root, roster_manifest=cohort_path,
        historical_decisions=[Path(first_binding["decision"]["path"])],
        evaluator_model=first_inputs["canonical_model"],
        contexts={prior["run"]["project"]: json.loads(prepared.context)}, registered_evaluations=outputs)
    assert all(package["reasons"] == [] for package in result["registered_evaluations"])
    groups = result["evaluation_condition_groups"]
    assert len(groups) == 1 and groups[0]["record_count"] == groups[0]["bound_rating_files"] == 2
    assert {member["replicate"] for member in groups[0]["members"]} == {1, 2}
    assert len({member["record_sha256"] for member in groups[0]["members"]}) == 2
    assert len({member["repeat_key"] for member in groups[0]["members"]}) == 2
    assert groups[0]["comparable_for_final_v10"] is False
    assert groups[0]["independence_verified"] is False
    assert all(record["evaluations"]["rubric20"]["repeat_panel"]["distinct_reported_sessions"] == 1
               for record in result["records"])

    # Exercise grouping itself after the real audit populated its bound members.
    # A distinct evaluation condition partitions records; it never joins repeats.
    records = deepcopy(result["records"])
    records[1]["evaluations"]["rubric20"]["files"][0]["evaluation_condition_key"] = "f" * 64
    assert len(audit.evaluation_condition_groups(records)) == 2


@pytest.fixture
def identity_plan():
    """A synthetic admitted-plan shape for the identity projection contract."""
    pin = {"path": "/fixture/full.yaml", "sha256": "a" * 64, "bytes": 40}
    return {
        "format": runner.FORMAT,
        "record_role": "full", "record": pin,
        "generation_run": {"arm": "baseline", "project": "StudyOne", "label": "old-one", "method": "claudecode_api"},
        "generation_registration": {**pin, "path": "/fixture/generation.json"},
        "generation_provenance": {**pin, "path": "/fixture/provenance.yaml"},
        "blinded_input_sha256": "b" * 64, "context_sha256": "c" * 64,
        "instrument": {"rubric": "rubric20-semantic", "version": "3.0", "rubric_sha256": "d" * 64},
        "execution_adapter": {"name": "no_tools_controller_validation_v1", "sha256": "e" * 64},
        "execution_mode": "isolated_no_tools_controller_validation",
        "runtime": {"model": "synthetic-model", "version": "2.1.269", "effort": "high",
                    "binary": {**pin, "path": "/fixture/runtime"}},
        "reserved_cost_dollars_per_attempt": "1.000000",
        "repeat_count": 1, "max_cost_dollars": "1",
        "blinding": {"version": "identity-aware-v1", "pyyaml_version": "synthetic-version",
                     "dumper_class": "yaml.dumper.SafeDumper", "arm": "historic", "input_arm": "baseline",
                     "project": "StudyOne", "label": "old-one", "condition": "old", "method": "claudecode_api",
                     "replicate_token": "rep1"},
        "authorities": [{**pin, "path": "/fixture/src/data_sheets_schema/" + module}
                        for module in runner.EVALUATOR_MODULES]
                       + [{**pin, "path": "/fixture/src/download/prompts/rubric20_semantic_schema.json"}],
    }


def test_different_generation_records_share_conditions_but_never_repeat_identity(identity_plan):
    other = deepcopy(identity_plan)
    other["generation_run"].update(project="StudyTwo", label="new-two")
    other["generation_provenance"]["sha256"] = "1" * 64
    other["record"]["sha256"] = "2" * 64
    other["blinded_input_sha256"] = "3" * 64
    other["blinding"].update(project="StudyTwo", label="new-two", condition="new", arm="current", replicate_token="rep2")
    assert evaluation_condition_key(identity_plan) == evaluation_condition_key(other)
    assert repeat_key(identity_plan) != repeat_key(other)


def test_historical_admission_does_not_change_common_evaluator_condition(identity_plan):
    other = deepcopy(identity_plan)
    other.update(format="registered_historical_semantic_evaluation_v1", generation_registration=None,
                 historical_binding={"path": "/fixture/binding.json", "sha256": "4" * 64, "bytes": 200},
                 historical_identity={"kind": "historical_provenance_v1"})
    other["authorities"].append({"path": "/fixture/src/data_sheets_schema/evaluation/historical_eval_binding.py",
                                 "sha256": "5" * 64, "bytes": 400})
    assert evaluation_condition_key(identity_plan) == evaluation_condition_key(other)
    assert repeat_key(identity_plan) != repeat_key(other)


def test_checkout_runtime_locations_and_panel_size_are_not_one_rating_condition(identity_plan):
    other = deepcopy(identity_plan)
    for pin in other["authorities"]:
        pin["path"] = pin["path"].replace("/fixture/", "/relocated/")
    other["runtime"]["binary"]["path"] = "/other/runtime"
    other.update(repeat_count=3, max_cost_dollars="3")
    assert evaluation_condition_key(identity_plan) == evaluation_condition_key(other)


@pytest.mark.parametrize("change", [
    "context", "rubric", "schema", "runtime_model", "runtime_effort", "runtime_binary", "runtime_version",
    "adapter", "blinding_version", "emitter_version", "dumper", "implementation", "per_attempt_cap",
])
def test_material_rating_condition_changes_split_both_keys(identity_plan, change):
    other = deepcopy(identity_plan)
    if change == "context":
        other["context_sha256"] = "1" * 64
    elif change == "rubric":
        other["instrument"]["rubric_sha256"] = "1" * 64
    elif change == "schema":
        other["authorities"][-1]["sha256"] = "1" * 64
    elif change.startswith("runtime_"):
        name = change.removeprefix("runtime_")
        if name == "binary":
            other["runtime"]["binary"]["sha256"] = "1" * 64
        else:
            other["runtime"][name] = "different"
    elif change == "adapter":
        other["execution_adapter"]["sha256"] = "1" * 64
    elif change in {"blinding_version", "emitter_version", "dumper"}:
        key = {"blinding_version": "version", "emitter_version": "pyyaml_version", "dumper": "dumper_class"}[change]
        other["blinding"][key] = "different"
    elif change == "implementation":
        other["authorities"][0]["sha256"] = "1" * 64
    else:
        other["reserved_cost_dollars_per_attempt"] = "2.000000"
    assert evaluation_condition_key(identity_plan) != evaluation_condition_key(other)
    assert repeat_key(identity_plan) != repeat_key(other)


@pytest.mark.parametrize("fault", ["missing", "duplicate"])
def test_condition_key_refuses_ambiguous_common_implementation(identity_plan, fault):
    if fault == "missing":
        identity_plan["authorities"].pop(0)
    else:
        identity_plan["authorities"].append(deepcopy(identity_plan["authorities"][0]))
    with pytest.raises(ValueError, match="each common evaluator implementation"):
        evaluation_condition_key(identity_plan)


@pytest.mark.parametrize("fault", ["missing", "duplicate"])
def test_condition_key_requires_unique_selected_schema(identity_plan, fault):
    if fault == "missing":
        identity_plan["authorities"].pop()
    else:
        identity_plan["authorities"].append(deepcopy(identity_plan["authorities"][-1]))
    with pytest.raises(ValueError, match="selected instrument schema"):
        evaluation_condition_key(identity_plan)
