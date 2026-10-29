"""Offline provenance/condition audit tests; never score or alter retained corpus."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import shutil
import subprocess

import pytest
import yaml

from data_sheets_schema import agent_pin
from tests.test_reference_rescore import current_record

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("comparability_audit", ROOT / "scripts/audit_evaluation_comparability.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
PREFIX = "synthetic_v10"
LABEL = PREFIX + "_rep1"
ARMS = {"synthetic": (PREFIX, ("CHORUS",))}
CONTEXT = {"human_subjects": {"value": None, "evidence": "Synthetic unresolved predicate."}}
MODEL = "claude-opus-5"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **kw: pytest.fail("network forbidden"))


@pytest.fixture(autouse=True)
def isolated_execution_locks(monkeypatch, tmp_path):
    # Imported registration helpers do not inherit their source module's
    # autouse fixtures. Keep fake executions off the shared Git-common-dir
    # lock store while preserving the production per-plan lock semantics.
    from data_sheets_schema.evaluation import registered_eval_runner as runner
    monkeypatch.setattr(runner, "LOCK_DIR", tmp_path / ".registered_eval_locks")


@pytest.fixture(autouse=True)
def no_unmocked_runtime(monkeypatch):
    actual = subprocess.run
    def local_git_only(command, **kwargs):
        if command[0] == "git":
            return actual(command, **kwargs)
        pytest.fail(f"unmocked runtime forbidden: {command[0]}")
    monkeypatch.setattr(subprocess, "run", local_git_only)


@pytest.fixture
def corpus(tmp_path):
    record = tmp_path / f"data/d4d_concatenated/claudecode_api/{LABEL}/CHORUS_d4d.yaml"
    record.parent.mkdir(parents=True)
    record.write_text("conforms_to_class: Dataset\nid: example:dataset\nname: Synthetic dataset\n")
    relative = record.relative_to(tmp_path).as_posix()
    provenance = tmp_path / f"data/d4d_concatenated/claudecode_api_core/{LABEL}/CHORUS_provenance.yaml"
    provenance.parent.mkdir(parents=True)
    doc = {
        "record_type": "d4d_generation_provenance",
        "run": {"project": "CHORUS", "label": LABEL, "method": "claudecode_api", "replicate": 1},
        "canonical": {"criterion": "synthetic declaration"},
        "validation": {"passed": True, "artifacts": {"full": {
            "path": relative, "md5": hashlib.md5(record.read_bytes()).hexdigest()}}},
        "outputs": {"full": {"path": relative}},
    }
    provenance.write_text(yaml.safe_dump(doc))
    return tmp_path, record, provenance, doc


def rating(corpus, number=10, *, name=None, session="session-one", version="3.0"):
    root, record, _, _ = corpus
    doc = current_record(record, number, CONTEXT)
    selected, resources = audit.instrument(f"rubric{number}", version)
    doc.update(project="CHORUS", label=LABEL, method="claudecode_api",
               d4d_file=record.relative_to(root).as_posix(), version=version)
    doc["model"].update(name=MODEL, evaluator_model=MODEL, temperature=None)
    predecessor = None
    if version == "4.0":
        predecessor = (ROOT / audit.select_semantic_instrument("rubric20", "3.0").definition_path).read_text()
        spec = yaml.safe_load(resources[selected.rubric_path])
        q19 = spec["d4d_evaluation_rubric"]["rubric"][18]["name"]
        for group in doc["categories"]:
            for item in group["questions"]:
                if item["id"] == 19:
                    item["name"] = q19
    doc["metadata"].update(
        instrument_sha256=audit.sha(resources[selected.definition_path]),
        rubric_sha256=audit.sha(resources[selected.rubric_path]),
        evidence_authority_sha256=audit.sha(resources[selected.evidence_authority_path]),
        instrument_kind="agent_definition", instrument_version=version,
        definition_echo=agent_pin.challenge(selected.agent, predecessor_text=predecessor)["expected"],
        session_id=session,
    )
    folder = root / f"data/evaluation_llm/rubric{number}_semantic/label_aware"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (name or f"{number}.json")
    path.write_text(json.dumps(doc))
    return path, doc


def run(corpus, **kwargs):
    return audit.audit(corpus[0], roster_manifest=legacy_roster(corpus[0]), evaluator_model=MODEL,
                       contexts={"CHORUS": CONTEXT}, **kwargs)


def legacy_roster(root):
    path = root / "cohort.yaml"
    path.write_text(yaml.safe_dump({"format": "evaluation_cohort_v1", "cells": [
        {"arm": "synthetic", "projects": ["CHORUS"], "replicates": [1, 2, 3],
         "label_template": PREFIX + "_rep{replicate}", "method": "claudecode_api",
         "condition": "generic_v10", "input_arm": "baseline"}]}))
    return path


def block(result, rubric="rubric10"):
    return result["records"][0]["evaluations"][rubric]


def save(path, doc):
    path.write_text(json.dumps(doc))


def test_current_bound_ratings_still_require_scientific_and_repeat_review(corpus):
    rating(corpus, 10)
    rating(corpus, 20)
    result = run(corpus)
    assert not block(result)["reasons"], block(result)
    assert not block(result, "rubric20")["reasons"], block(result, "rubric20")
    assert block(result)["files"][0]["contract_checked"] is True
    assert block(result)["files"][0]["eligible_for_condition_review"] is True
    assert block(result)["comparable_for_final_v10"] is False
    assert result["targets"]["context_human_review_verified"] is False
    assert result["summary"][0]["canonical_labels"] == [LABEL]
    assert len(result["rescore_tuples"]) == 4  # two missing replicates, two rubrics
    assert result["repeat_panel_actions"][0]["status"] == "fixed_record_selection_and_repeat_ratings_pending"


def test_no_ratings_reports_exact_missing_tuples_including_ignored_files(corpus):
    root = corpus[0]
    (root / ".gitignore").write_text("data/\n")
    result = run(corpus)
    assert len(result["rescore_tuples"]) == 6
    first = result["rescore_tuples"][0]
    assert (first["arm"], first["project"], first["label"], first["rubric"]) == ("synthetic", "CHORUS", LABEL, "rubric10")
    assert first["reasons"] == ["evaluation_missing_from_selected_stores"]
    assert result["scope"]["filesystem_globs_include_ignored_and_hidden"] is True
    path, _ = rating(corpus, name=".ignored-rating.json")
    assert block(run(corpus))["files"][0]["path"].endswith(path.name)


@pytest.mark.parametrize(("mutation", "reason"), [
    (lambda d: d.update(version="1.1"), "pre_3_instrument"),
    (lambda d: d.update(version="2.5"), "pre_3_instrument"),
    (lambda d: d.update(version="4.0"), "instrument_version_mismatch"),
    (lambda d: d.update(rubric="rubric20-semantic"), "rubric_disagrees_with_store"),
    (lambda d: d.update(project="VOICE"), "evaluation_run_identity_conflict"),
    (lambda d: d.update(label="different_rep1"), "evaluation_run_identity_conflict"),
    (lambda d: d.update(method="claudecode_agent"), "evaluation_method_conflict"),
    (lambda d: d.update(d4d_file="elsewhere.yaml"), "evaluation_input_path_unverified"),
    (lambda d: d["metadata"].pop("input_sha256"), "evaluation_input_hash_missing"),
    (lambda d: d["metadata"].update(input_sha256="0"*64), "evaluation_input_hash_mismatch"),
    (lambda d: d.pop("applicability_context"), "applicability_context_missing"),
    (lambda d: d["metadata"].pop("context_sha256"), "applicability_context_hash_missing_or_mismatched"),
    (lambda d: d.update(applicability_context={"bogus": False}), "applicability_context_invalid"),
    (lambda d: d["model"].update(name="other", evaluator_model="other"), "evaluator_differs_from_target"),
    (lambda d: d["model"].update(evaluator_model="other"), "evaluator_model_fields_conflict"),
    (lambda d: d.update(model={}), "evaluator_model_missing"),
    (lambda d: d["metadata"].pop("instrument_sha256"), "instrument_sha256_missing_or_mismatched"),
    (lambda d: d["metadata"].pop("rubric_sha256"), "rubric_sha256_missing_or_mismatched"),
    (lambda d: d["metadata"].pop("definition_echo"), "definition_echo_evidence_missing"),
    (lambda d: d["metadata"].update(definition_echo="stale"), "definition_echo_not_verified"),
    (lambda d: d["overall_score"].update(total_points=0), "current_semantic_contract_invalid"),
])
def test_condition_mismatch_enters_exact_queue(corpus, mutation, reason):
    path, doc = rating(corpus)
    mutation(doc)
    save(path, doc)
    result = run(corpus)
    assert reason in block(result)["reasons"]
    assert reason in result["rescore_tuples"][0]["reasons"]
    assert block(result)["comparable_for_final_v10"] is False


def test_context_hash_presence_never_implies_target_selection_or_human_review(corpus):
    rating(corpus)
    result = audit.audit(corpus[0], roster_manifest=legacy_roster(corpus[0]))
    row = block(result)["files"][0]
    assert not row["reasons"]
    assert row["pending"] == ["target_context_not_selected", "target_evaluator_not_selected"]
    assert row["eligible_for_condition_review"] is False
    assert result["targets"]["context_human_review_verified"] is False


def test_changed_independent_context_refuses_self_consistent_evaluator_context(corpus):
    rating(corpus)
    result = audit.audit(corpus[0], roster_manifest=legacy_roster(corpus[0]), evaluator_model=MODEL, contexts={"CHORUS": {"human_subjects": False}})
    assert "applicability_context_differs_from_target" in block(result)["reasons"]


def test_filename_alone_cannot_join_evaluation(corpus):
    path, doc = rating(corpus, name=f"CHORUS_{LABEL}_rubric10.json")
    doc.pop("label")
    doc.pop("project")
    doc.pop("d4d_file")
    save(path, doc)
    result = run(corpus)
    assert block(result)["file_count"] == 0
    assert result["unassociated_evaluations"][0]["path"].endswith(path.name)


def test_ambiguous_provenance_is_not_resolved_using_evaluation_filename(corpus):
    root, _, _, doc = corpus
    second = root / f"data/d4d_concatenated/claudecode_agent_core/{LABEL}/CHORUS_provenance.yaml"
    second.parent.mkdir(parents=True)
    second.write_text(yaml.safe_dump(doc))
    rating(corpus)
    result = run(corpus)
    assert result["records"][0]["record_path"] is None
    assert "provenance_ambiguous" in block(result)["reasons"]


def test_reused_artifact_path_is_ambiguous_even_when_rating_has_matching_hash(corpus):
    root, _, provenance, doc = corpus
    second = provenance.parent.parent / f"{PREFIX}_rep2" / provenance.name
    second.parent.mkdir()
    doc = deepcopy(doc)
    doc["run"].update(label=f"{PREFIX}_rep2", replicate=2)
    second.write_text(yaml.safe_dump(doc))
    path, rating_doc = rating(corpus)
    rating_doc.pop("label")
    save(path, rating_doc)
    result = run(corpus)
    for record in result["records"][:2]:
        assert "evaluation_linkage_ambiguous" in record["evaluations"]["rubric10"]["reasons"]
    assert result["totals"]["associated_evaluation_files"] == 1


@pytest.mark.parametrize("fault", ["hash", "outputs_hash", "invalid", "unknown", "run", "nonfinite", "recursive"])
def test_invalid_generation_provenance_is_not_current_comparator(corpus, fault):
    _, record, path, doc = corpus
    if fault == "hash":
        record.write_text("changed: true\n")
    elif fault == "outputs_hash":
        doc["outputs"]["full"]["sha256"] = "0"*64
    elif fault == "invalid":
        doc["validation"]["passed"] = False
    elif fault == "unknown":
        doc["validation"].pop("passed")
    elif fault == "run":
        doc["run"]["replicate"] = True
    elif fault == "nonfinite":
        doc["canonical"]["criterion"] = float("inf")
    else:
        doc["loop"] = doc
    path.write_text(yaml.safe_dump(doc))
    result = run(corpus)
    assert result["records"][0]["reasons"]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("kind", ["provenance_parent", "evaluation_parent", "artifact"])
def test_symlink_escape_never_reads_external_files(corpus, tmp_path_factory, monkeypatch, kind):
    root, record, provenance, doc = corpus
    outside = tmp_path_factory.mktemp("outside")
    path, rating_doc = rating(corpus)
    if kind == "provenance_parent":
        provenance.unlink()
        provenance.parent.rmdir()
        (outside / provenance.name).write_text(yaml.safe_dump(doc))
        provenance.parent.symlink_to(outside, target_is_directory=True)
    elif kind == "evaluation_parent":
        path.unlink()
        path.parent.rmdir()
        (outside / path.name).write_text(json.dumps(rating_doc))
        path.parent.symlink_to(outside, target_is_directory=True)
    else:
        record.unlink()
        (outside / record.name).write_text("secret: true\n")
        record.symlink_to(outside / record.name)
    original = audit.read
    def guarded(selected):
        assert not Path(selected).is_relative_to(outside), "escaped root"
        return original(selected)
    monkeypatch.setattr(audit, "read", guarded)
    result = run(corpus)
    if kind == "evaluation_parent":
        assert result["unreadable_evaluations"]
    else:
        assert result["records"][0]["reasons"]


@pytest.mark.parametrize("text", ['{"rubric":1,"rubric":2}', '{"x":NaN}', '{"x":1e999}', '[1,2]'])
def test_bad_json_reported_without_crashing(corpus, text):
    path, _ = rating(corpus)
    path.write_text(text)
    result = run(corpus)
    assert result["unreadable_evaluations"]
    assert block(result)["file_count"] == 0


def test_instrument_resources_are_fresh_for_each_audit(corpus, monkeypatch):
    rating(corpus)
    assert not block(run(corpus))["reasons"]
    original = audit.read
    def changed(path):
        raw = original(path)
        return raw + b"\n" if str(path).endswith("d4d-rubric10-semantic.md") else raw
    monkeypatch.setattr(audit, "read", changed)
    assert "instrument_sha256_missing_or_mismatched" in block(run(corpus))["reasons"]


def test_aggregate_n_and_generation_replicates_are_not_independent_ratings(corpus):
    path, doc = rating(corpus, 20)
    doc["repeat_panel"] = {"n": 3}
    save(path, doc)
    result = run(corpus)
    panel = block(result, "rubric20")["repeat_panel"]
    assert panel["reported_n_at_least_three"] is True
    assert panel["distinct_reported_sessions"] == 1
    assert panel["three_distinct_session_claims_present"] is False
    assert result["repeat_panel_actions"][0]["status"] == "fixed_record_selection_and_repeat_ratings_pending"


def test_three_session_claims_are_reported_without_asserting_independence(corpus):
    for n in range(3):
        rating(corpus, 20, name=f"rating{n}.json", session=f"session-{n}")
    result = run(corpus)
    panel = block(result, "rubric20")["repeat_panel"]
    assert panel["distinct_reported_sessions"] == 3
    assert panel["three_distinct_session_claims_present"] is True
    assert panel["independence_verified"] is False
    assert result["repeat_panel_actions"][0]["status"] == "independence_and_selection_review_pending"
    assert result["repeat_panel_actions"][0]["three_session_candidate_tuples"][0]["label"] == LABEL


def test_duplicate_session_does_not_form_repeat_panel(corpus):
    for n in range(3):
        path, doc = rating(corpus, 20, name=f"rating{n}.json", session="reused-session")
        doc["metadata"]["other"] = n
        save(path, doc)
    result = run(corpus)
    assert block(result, "rubric20")["repeat_panel"]["distinct_reported_sessions"] == 1


def test_other_context_and_evaluator_sessions_cannot_complete_target_repeat_panel(corpus):
    for n in range(3):
        path, doc = rating(corpus, 20, name=f"rating{n}.json", session=f"session-{n}")
        if n == 1:
            doc["model"].update(name="other-evaluator", evaluator_model="other-evaluator")
        elif n == 2:
            doc["applicability_context"]["human_subjects"]["evidence"] = "Different independent declaration."
            doc["metadata"]["context_sha256"] = audit.context_digest(doc["applicability_context"])
        save(path, doc)
    panel = block(run(corpus), "rubric20")["repeat_panel"]
    assert panel["distinct_reported_sessions"] == 1
    assert panel["three_distinct_session_claims_present"] is False


def test_v4_is_a_distinct_target_not_implicitly_accepted_as_v3(corpus):
    rating(corpus, 20, version="4.0")
    assert "instrument_version_mismatch" in block(run(corpus), "rubric20")["reasons"]
    assert not block(run(corpus, rubric20_version="4.0"), "rubric20")["reasons"]


def test_invalid_out_of_roster_canary_is_excluded_and_visible(corpus):
    root, _, provenance, doc = corpus
    path = provenance.with_name("AI_READI_provenance.yaml")
    doc = deepcopy(doc)
    doc["run"]["project"] = "AI_READI"
    doc["validation"]["passed"] = False
    path.write_text(yaml.safe_dump(doc))
    result = run(corpus)
    assert len(result["records"]) == 3
    assert result["excluded_records"][0]["project"] == "AI_READI"
    assert result["excluded_records"][0]["validation_passed"] is False
    assert "declared_invalid_generation_outside_selected_roster" in audit.markdown(result)


def test_output_deterministic_and_historical_bytes_untouched(corpus):
    rating(corpus, 10)
    rating(corpus, 20)
    root = corpus[0]
    before = {str(path): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    first, second = run(corpus), run(corpus)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert audit.markdown(first) == audit.markdown(second)
    assert before == {str(path): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert "Repeat-panel action queue" in audit.markdown(first)
    assert "Canonical labels" in audit.markdown(first)


def test_subdirectory_store_is_explicitly_out_of_scope(corpus):
    path, _ = rating(corpus)
    dest = path.parent / "superseded"
    dest.mkdir()
    path.rename(dest / path.name)
    result = run(corpus)
    assert block(result)["file_count"] == 0
    assert result["scope"]["other_evaluation_directories_audited"] is False


@pytest.fixture(scope="module")
def registered_generation_inputs(tmp_path_factory):
    # Reuse the real E1 generation/provenance builder; the fake runtime bytes
    # are never launched. Only execute's evaluator subprocess is mocked below.
    from tests import test_registered_eval_runner as support
    return support.registration.__wrapped__(tmp_path_factory)


@pytest.fixture(scope="module")
def registered_prepared(registered_generation_inputs):
    from tests import test_registered_eval_runner as support
    return support.runner.prepare(**{**registered_generation_inputs, "repeat_count": 3})


@pytest.fixture
def registered_case(registered_prepared, tmp_path, monkeypatch):
    from tests import test_registered_eval_runner as support
    prepared = registered_prepared
    root = Path(prepared.document()["record"]["path"]).parent
    output = root / "evaluation-tests" / tmp_path.name / "ratings"
    with monkeypatch.context() as mocked:
        calls = support.install_cli(mocked, prepared)
        receipt = support.runner.execute(prepared, output, plan_sha256=prepared.digest,
                                         environ={"CBORG_API_KEY": "synthetic-never-sent"})
    assert receipt["status"] == "validated" and len(calls) == 3
    return root, output, prepared


def registered_audit(case, *, directories=None, **kwargs):
    root, output, prepared = case
    plan = prepared.document()
    return audit.audit(root, roster_manifest=registered_roster(case), evaluator_model=plan["runtime"]["canonical_model"],
        contexts={plan["generation_run"]["project"]: json.loads(prepared.context)},
        registered_evaluations=directories or [("explicit-v10", output)], **kwargs)


def registered_roster(case):
    root, output, prepared = case
    run = prepared.document()["generation_run"]
    path = output.parent / "cohort.yaml"
    path.write_text(yaml.safe_dump({"format": "evaluation_cohort_v1", "cells": [
        {"arm": "explicit-v10", "projects": [run["project"]], "replicates": [17],
         "label_template": run["label"], "method": run["method"],
         "condition": "generic_v10", "input_arm": run["arm"]}]}))
    return path


def rewrite_plan(output, callback):
    from data_sheets_schema.evaluation import registered_eval_runner as runner
    plan = json.loads((output / "registration.json").read_bytes())
    callback(plan)
    raw = runner.shared.canonical(plan)
    (output / "registration.json").write_bytes(raw)
    receipt = json.loads((output / "receipt.json").read_bytes())
    receipt.update(plan=plan, plan_sha256=audit.sha(raw))
    (output / "receipt.json").write_bytes(runner.shared.canonical(receipt))


def registered_problem(result):
    return result["registered_evaluations"][0]["reasons"]


def test_writer_roundtrip_with_declared_external_authority_root(registered_generation_inputs, tmp_path, monkeypatch):
    from tests import test_registered_eval_runner as support
    inputs = support.rebind_record(dict(registered_generation_inputs), tmp_path,
                                  registered_generation_inputs["record"].read_bytes())
    prior = yaml.safe_load(inputs["provenance"].read_bytes())
    assert prior["run"]["arm"] == "baseline"
    original_registration = inputs["registration"].read_bytes()
    prepared = support.runner.prepare(**inputs)
    output = tmp_path / "ratings"
    with monkeypatch.context() as mocked:
        support.install_cli(mocked, prepared)
        receipt = support.runner.execute(prepared, output, plan_sha256=prepared.digest,
                                         environ={"CBORG_API_KEY": "synthetic"})
    assert receipt["status"] == "validated"
    case = (tmp_path, output, prepared)
    assert registered_problem(registered_audit(case)) == ["registered_authority_missing_or_external"]
    result = registered_audit(case, authority_roots=[inputs["registration"].parent])
    assert not registered_problem(result)
    assert {row["rubric"] for row in result["rescore_tuples"]} == {"rubric10"}
    assert inputs["registration"].read_bytes() == original_registration


def test_actual_registered_runner_output_satisfies_only_its_exact_ingestion_tuple(registered_case):
    root, output, prepared = registered_case
    before = {str(path): path.read_bytes() for path in output.rglob("*") if path.is_file()}
    result = registered_audit(registered_case)
    assert not registered_problem(result), result["registered_evaluations"]
    record = result["records"][0]
    assert record["label"] == "concealed-v10-rep17" and record["replicate"] == 17
    assert record["registered_run"] == prepared.document()["generation_run"]
    assert record["arm"] == "explicit-v10"  # audit grouping does not rewrite generation arm
    accepted = record["evaluations"]["rubric20"]
    assert accepted["file_count"] == 3 and accepted["reasons"] == []
    assert accepted["comparable_for_final_v10"] is False
    assert {row["rubric"] for row in result["rescore_tuples"]} == {"rubric10"}
    panel = accepted["repeat_panel"]
    assert panel["distinct_reported_sessions"] == 3
    assert panel["three_distinct_session_claims_present"] is True
    assert panel["independence_verified"] is False
    assert len({row["sha256"] for row in accepted["files"]}) == 1  # identical scores are legitimate
    assert all(row["transcript_sha256"] and row["manifest_sha256"] and row["receipt_sha256"]
               and row["original_sha256"] != row["input_hashes"]["input_sha256"]
               and row["transcript_pin_supplied"] is False for row in accepted["files"])
    assert result["targets"]["context_human_review_verified"] is False
    assert before == {str(path): path.read_bytes() for path in output.rglob("*") if path.is_file()}
    assert audit.markdown(result) == audit.markdown(registered_audit(registered_case))


@pytest.mark.parametrize(("rubric", "version", "repeats"), [("rubric10", "3.0", 1), ("rubric20", "4.0", 3)])
def test_alternate_supported_instruments_roundtrip_actual_runner_to_audit(
        registered_generation_inputs, tmp_path, monkeypatch, rubric, version, repeats):
    from tests import test_registered_eval_runner as support
    prepared = support.runner.prepare(**{**registered_generation_inputs,
        "rubric": rubric, "instrument_version": version, "repeat_count": repeats})
    root = Path(prepared.document()["record"]["path"]).parent
    output = root / "alternate-instrument-tests" / tmp_path.name / "ratings"
    with monkeypatch.context() as mocked:
        calls = support.install_cli(mocked, prepared)
        receipt = support.runner.execute(prepared, output, plan_sha256=prepared.digest,
                                         environ={"CBORG_API_KEY": "synthetic-never-sent"})
    assert receipt["status"] == "validated" and len(calls) == repeats
    case = root, output, prepared
    result = registered_audit(case, rubric20_version=version)
    assert not registered_problem(result), result["registered_evaluations"]
    accepted = block(result, rubric)
    assert accepted["file_count"] == repeats and accepted["reasons"] == []
    assert all(row["version"] == version and row["eligible_for_condition_review"] for row in accepted["files"])
    other = "rubric20" if rubric == "rubric10" else "rubric10"
    assert {(row["label"], row["rubric"]) for row in result["rescore_tuples"]} == {
        (prepared.document()["generation_run"]["label"], other)}
    assert accepted["comparable_for_final_v10"] is False
    if version == "4.0":
        predecessor = audit.ROOT / audit.select_semantic_instrument("rubric20", "3.0").definition_path
        assert (output / "predecessor.md").read_bytes() == predecessor.read_bytes()
        wrong_target = registered_audit(case, rubric20_version="3.0")
        assert "registered_instrument_version_unsupported" in registered_problem(wrong_target)
        assert block(wrong_target, rubric)["reasons"]
        assert not block(wrong_target, rubric)["repeat_panel"]["three_distinct_session_claims_present"]
    rewrite_plan(output, lambda plan: plan["instrument"].update(version="99.0"))
    unsupported = registered_audit(case, rubric20_version=version)
    assert "registered_instrument_version_unsupported" in registered_problem(unsupported)
    assert any(row["rubric"] == rubric for row in unsupported["rescore_tuples"])


@pytest.mark.parametrize(("fault", "reason"), [
    ("manifest-pin", "registered_receipt_plan_mismatch"),
    ("record-role", "unsupported_for_full_audit"),
    ("run", "registered_generation_identity_mismatch"),
    ("blinding-version", "registered_blinding_unsupported_or_mismatched"),
    ("blinding-arm", "registered_blinding_unsupported_or_mismatched"),
    ("original", "registered_original_copy_mismatch"),
    ("blinded", "registered_blinded_input_mismatch"),
    ("context", "registered_context_mismatch"),
    ("instrument", "registered_instrument_resource_unsupported_or_mismatched"),
    ("predecessor", "registered_predecessor_pin_mismatch"),
    ("adapter", "registered_adapter_unsupported_or_mismatched"),
    ("system", "registered_adapter_unsupported_or_mismatched"),
    ("prompt", "registered_prompt_unsupported_or_mismatched"),
    ("evaluation", "registered_evaluation_pin_mismatch"),
    ("receipt-session", "registered_session_reused_or_mismatched"),
    ("receipt-echo", "registered_rating_receipt_mismatch"),
    ("receipt-trace", "registered_transcript_pin_mismatch"),
    ("duplicate-index", "registered_rating_identity_invalid"),
    ("missing-transcript", "registered_evidence_invalid_or_unavailable"),
])
def test_registered_join_mutations_are_visible_and_never_accepted(registered_case, fault, reason):
    _, output, prepared = registered_case
    assert not registered_problem(registered_audit(registered_case))
    if fault == "manifest-pin":
        path = output / "receipt.json"
        doc = json.loads(path.read_bytes())
        doc["plan_sha256"] = "0" * 64
        save(path, doc)
    elif fault in {"record-role", "run", "blinding-version", "blinding-arm"}:
        def mutate(plan):
            if fault == "record-role":
                plan["record_role"] = "core"
            elif fault == "run":
                plan["generation_run"]["label"] = "different-run"
            elif fault == "blinding-version":
                plan["blinding"]["version"] = "unknown-v0"
            else:
                plan["blinding"]["arm"] = "invented-arm"
        rewrite_plan(output, mutate)
    elif fault in {"receipt-session", "receipt-echo", "receipt-trace", "duplicate-index"}:
        path = output / "receipt.json"
        doc = json.loads(path.read_bytes())
        if fault == "duplicate-index":
            doc["ratings"].append(deepcopy(doc["ratings"][0]))
            # Keep bounded counts so the actual duplicate-identity guard is exercised.
            doc["ratings"].pop(2)
        else:
            key = {"receipt-session": "session_id", "receipt-echo": "check_echo",
                   "receipt-trace": "transcript_sha256"}[fault]
            doc["ratings"][0][key] = "0" * 64
        save(path, doc)
    else:
        selected = audit.select_semantic_instrument("rubric20", "3.0")
        name = {"original": "original.yaml", "blinded": "record.yaml", "context": "context.json",
            "instrument": "instrument/" + selected.rubric_path, "predecessor": "predecessor.md",
            "adapter": "execution_adapter.txt", "system": "effective_system.txt", "prompt": "prompt.txt",
            "evaluation": "rating-001/evaluation.json", "missing-transcript": "rating-001/transcript.jsonl"}[fault]
        path = output / name
        if fault == "missing-transcript":
            path.unlink()
        elif fault == "context":
            path.write_text('{"human_subjects":false}')
        elif fault == "evaluation":
            doc = json.loads(path.read_bytes())
            doc["metadata"]["input_sha256"] = "0" * 64
            save(path, doc)
        else:
            path.write_bytes(path.read_bytes() + b"\n")
    result = registered_audit(registered_case)
    assert reason in registered_problem(result), result["registered_evaluations"]
    assert result["totals"]["bound_registered_rating_files"] == 0
    if fault == "record-role":
        assert result["records"] == []


@pytest.mark.parametrize("fault", ["echo", "assistant", "session", "model", "tools", "reused-session"])
def test_actual_retained_transcript_revalidated_not_trusted_receipt_claim(registered_case, fault):
    _, output, _ = registered_case
    assert not registered_problem(registered_audit(registered_case))
    path = output / ("rating-002" if fault == "reused-session" else "rating-001") / "transcript.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    if fault == "echo":
        from tests.test_registered_eval_runner import change_reply
        change_reply(events, lambda envelope: envelope.update(definition_echo="stale definition"))
    elif fault == "assistant":
        events[1]["message"]["content"][0]["text"] = "{}"
    elif fault in {"session", "reused-session"}:
        session = "different-session" if fault == "session" else "synthetic-session-1"
        for event in events:
            event["session_id"] = session
    elif fault == "model":
        events[1]["message"]["model"] = "other-model"
    else:
        events[0]["tools"] = ["Bash"]
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n")
    result = registered_audit(registered_case)
    assert registered_problem(result)
    assert result["totals"]["bound_registered_rating_files"] == 0


def test_copied_directories_and_aliases_cannot_inflate_registered_sessions(registered_case):
    _, output, _ = registered_case
    copied = output.with_name("copied")
    shutil.copytree(output, copied)
    alias = output.with_name("alias")
    alias.symlink_to(output, target_is_directory=True)
    result = registered_audit(registered_case, directories=[("explicit-v10", output),
        ("explicit-v10", copied), ("explicit-v10", alias)])
    panel = block(result, "rubric20")["repeat_panel"]
    assert panel["distinct_reported_sessions"] == 3
    assert result["totals"]["bound_registered_rating_files"] == 3
    assert any("registered_directory_duplicate" in package["reasons"] for package in result["registered_evaluations"])
    assert any("registered_attempt_duplicate" in row["reasons"] for row in block(result, "rubric20")["files"])


@pytest.mark.parametrize("bad_first", [False, True])
@pytest.mark.parametrize("fault", ["missing-transcript", "early-record-pin"])
def test_invalid_package_never_poisons_independently_bound_good_record(registered_case, bad_first, fault):
    _, output, _ = registered_case
    good = output.with_name("z-good" if bad_first else "a-good")
    bad = output.with_name("a-bad" if bad_first else "z-bad")
    shutil.copytree(output, good)
    shutil.copytree(output, bad)
    if fault == "missing-transcript":
        (bad / "rating-001/transcript.jsonl").unlink()
    else:
        def mutate(plan):
            old = deepcopy(plan["record"])
            plan["record"]["sha256"] = "0" * 64
            plan["authorities"] = [plan["record"] if entry == old else entry for entry in plan["authorities"]]
        rewrite_plan(bad, mutate)
    result = registered_audit(registered_case, directories=[("explicit-v10", bad), ("explicit-v10", good)])
    assert len(result["records"]) == 1
    assert block(result, "rubric20")["reasons"] == []
    assert block(result, "rubric20")["repeat_panel"]["distinct_reported_sessions"] == 3
    assert {row["rubric"] for row in result["rescore_tuples"]} == {"rubric10"}
    rejected = [package for package in result["registered_evaluations"] if package["status"] == "refused"]
    assert len(rejected) == 1 and rejected[0]["reasons"]


@pytest.mark.parametrize("other_first", [False, True])
def test_genuine_conflicting_provenance_identities_still_refuse_same_tuple(registered_case, other_first):
    _, output, prepared = registered_case
    other = output.with_name("a-other" if other_first else "z-other")
    shutil.copytree(output, other)
    prior = Path(prepared.document()["generation_provenance"]["path"])
    doc = yaml.safe_load(prior.read_bytes())
    doc["notes"] = "A distinct provenance declaration; never silently select between these."
    raw = yaml.safe_dump(doc).encode()
    new_path = other.parent / "other-provenance.yaml"
    new_path.write_bytes(raw)
    def mutate(plan):
        old = plan["generation_provenance"]
        new = {"path": str(new_path), "sha256": audit.sha(raw), "bytes": len(raw)}
        plan["generation_provenance"] = new
        plan["authorities"] = [new if entry == old else entry for entry in plan["authorities"]]
    rewrite_plan(other, mutate)
    assert not registered_problem(registered_audit(registered_case, directories=[("explicit-v10", other)]))
    result = registered_audit(registered_case, directories=[("explicit-v10", output), ("explicit-v10", other)])
    assert "registered_record_linkage_conflict" in block(result, "rubric20")["reasons"]
    assert not any(row["eligible_for_condition_review"] for row in block(result, "rubric20")["files"])
    assert any(row["rubric"] == "rubric20" for row in result["rescore_tuples"])


def test_repeat_condition_groups_do_not_mix_legacy_blinded_adapter_or_runtime(registered_case):
    result = registered_audit(registered_case)
    rows = block(result, "rubric20")["files"]
    assert audit.repeat_panel(rows)["three_distinct_session_claims_present"]
    for field in ("source", "adapter", "blinding", "record_role", "runtime"):
        changed = [deepcopy(row) for row in rows]
        changed[1]["input_condition"][field] = "different-condition"
        panel = audit.repeat_panel(changed)
        assert panel["distinct_reported_sessions"] == 2 and panel["condition_groups"] == 2
        assert not panel["three_distinct_session_claims_present"]


def test_historical_code_pin_is_condition_evidence_not_executed_current_code_gate(registered_case):
    _, output, _ = registered_case
    def mutate(plan):
        code = next(entry for entry in plan["authorities"]
                    if entry["path"].endswith("/evaluation/registered_eval_runner.py"))
        code["sha256"] = "1" * 64
    rewrite_plan(output, mutate)
    result = registered_audit(registered_case)
    assert not registered_problem(result), result["registered_evaluations"]
    pins = block(result, "rubric20")["files"][0]["input_condition"]["implementation_pins"]
    assert any(pin["sha256"] == "1" * 64 for pin in pins)


@pytest.mark.parametrize("module", ["registered_eval_runner.py", "blind_review_pack.py"])
def test_declared_blinding_requires_both_captured_implementation_pins(registered_case, module):
    _, output, _ = registered_case
    def mutate(plan):
        plan["authorities"] = [entry for entry in plan["authorities"]
                               if not entry["path"].endswith("/evaluation/" + module)]
    rewrite_plan(output, mutate)
    result = registered_audit(registered_case)
    assert "registered_blinding_implementation_pin_missing" in registered_problem(result)


@pytest.mark.parametrize("fault", ["orphan", "excess", "symlink", "non-directory"])
def test_registered_rating_directory_roster_is_exact_and_bounded(registered_case, fault):
    _, output, _ = registered_case
    if fault == "orphan":
        (output / "rating-004").mkdir()
    elif fault == "excess":
        for index in range(129):
            (output / f"unlisted-{index}").touch()
    elif fault == "symlink":
        (output / "rating-004").symlink_to(output / "rating-001", target_is_directory=True)
    else:
        (output / "rating-004").write_text("not a directory")
    result = registered_audit(registered_case)
    assert registered_problem(result)
    assert result["totals"]["bound_registered_rating_files"] == 0


@pytest.mark.parametrize("fault", ["full-hash", "full-path", "run", "capture", "declared-invalid"])
def test_independently_pinned_generation_provenance_is_joined(registered_case, fault):
    _, output, prepared = registered_case
    prior_path = Path(prepared.document()["generation_provenance"]["path"])
    document = yaml.safe_load(prior_path.read_bytes())
    if fault == "full-hash":
        document["validation"]["artifacts"]["full"]["md5"] = "0" * 32
    elif fault == "full-path":
        document["validation"]["artifacts"]["full"]["path"] += ".other"
    elif fault == "run":
        document["run"]["label"] = "different-run"
    elif fault == "capture":
        document["shared_generation"]["authority"]["files"] = []
    else:
        document["validation"]["passed"] = False
    new_path = output.parent / "changed-provenance.yaml"
    raw = yaml.safe_dump(document).encode()
    new_path.write_bytes(raw)
    def mutate(plan):
        old = plan["generation_provenance"]
        new = {"path": str(new_path), "sha256": audit.sha(raw), "bytes": len(raw)}
        plan["generation_provenance"] = new
        plan["authorities"] = [new if entry == old else entry for entry in plan["authorities"]]
    rewrite_plan(output, mutate)
    result = registered_audit(registered_case)
    assert registered_problem(result)
    assert result["totals"]["bound_registered_rating_files"] == 0


def test_registered_failed_later_attempt_retains_only_actual_validated_rating(registered_case):
    _, output, _ = registered_case
    path = output / "receipt.json"
    receipt = json.loads(path.read_bytes())
    receipt.update(status="incomplete", ratings=receipt["ratings"][:1], attempts=receipt["attempts"][:2])
    receipt["attempts"][1].update(status="failed", exit_code=1)
    save(path, receipt)
    shutil.rmtree(output / "rating-003")
    (output / "rating-002/evaluation.json").unlink()
    result = registered_audit(registered_case)
    assert not registered_problem(result), result["registered_evaluations"]
    assert block(result, "rubric20")["file_count"] == 1
    assert block(result, "rubric20")["repeat_panel"]["distinct_reported_sessions"] == 1
    assert result["registered_evaluations"][0]["attempts"][1]["reason"] == "registered_attempt_failed_or_incomplete"


@pytest.mark.parametrize("fault", ["nonfinite", "duplicate-json", "escape", "fifo", "budget", "changed"])
def test_registered_capture_bounds_and_current_bytes(registered_case, tmp_path, monkeypatch, fault):
    _, output, _ = registered_case
    if fault in {"nonfinite", "duplicate-json"}:
        (output / "receipt.json").write_text('{"a":NaN}' if fault == "nonfinite" else '{"a":1,"a":2}')
    elif fault == "escape":
        path = output / "record.yaml"
        outside = tmp_path / "outside.yaml"
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
    elif fault == "fifo":
        import os
        path = output / "record.yaml"
        path.unlink()
        os.mkfifo(path)
    elif fault == "budget":
        monkeypatch.setattr(audit, "MAX_REGISTERED_BYTES", 10)
    else:
        original = audit.RegisteredCapture.unchanged
        def changed(capture):
            path = output / "record.yaml"
            path.write_bytes(path.read_bytes() + b"\n")
            return original(capture)
        monkeypatch.setattr(audit.RegisteredCapture, "unchanged", changed)
    result = registered_audit(registered_case)
    assert registered_problem(result)
    assert result["totals"]["bound_registered_rating_files"] == 0


@pytest.mark.parametrize("kind", ["file", "directory"])
@pytest.mark.parametrize("replacement", ["same-bytes", "different-bytes", "outside"])
def test_registered_alias_retarget_refuses_without_mutating_captured_target(
        registered_case, tmp_path, monkeypatch, kind, replacement):
    root, output, _ = registered_case
    original_record = (output / "record.yaml").read_bytes()
    if kind == "file":
        original_target = output.with_name("original-record.yaml")
        original_target.write_bytes(original_record)
        alias = output / "record.yaml"
        alias.unlink()
        alias.symlink_to(original_target)
        other = (tmp_path if replacement == "outside" else output.parent) / "other-record.yaml"
        other.write_bytes(original_record + (b"\n" if replacement == "different-bytes" else b""))
        directories = [("explicit-v10", output)]
    else:
        original_target = output
        alias = output.with_name("selected-alias")
        alias.symlink_to(original_target, target_is_directory=True)
        other = (tmp_path if replacement == "outside" else output.parent) / "other-package"
        shutil.copytree(original_target, other)
        if replacement == "different-bytes":
            (other / "record.yaml").write_bytes(original_record + b"\n")
        directories = [("explicit-v10", alias)]
    if replacement == "outside":
        assert audit.local_path(root, str(other)) is None

    # The exact public entry point supports this stable in-root alias first.
    baseline = registered_audit(registered_case, directories=directories)
    assert not registered_problem(baseline)
    assert baseline["totals"]["bound_registered_rating_files"] == 3
    unchanged = audit.RegisteredCapture.unchanged
    checked = []

    def retarget_after_capture(capture):
        checked.append(capture)
        assert alias.resolve() == original_target
        alias.unlink()
        alias.symlink_to(other, target_is_directory=kind == "directory")
        return unchanged(capture)

    monkeypatch.setattr(audit.RegisteredCapture, "unchanged", retarget_after_capture)
    result = registered_audit(registered_case, directories=directories)
    assert len(checked) == 1
    assert registered_problem(result) == ["registered_evidence_changed"]
    assert result["totals"]["bound_registered_rating_files"] == 0
    captured_file = original_target if kind == "file" else original_target / "record.yaml"
    assert captured_file.read_bytes() == original_record


def test_registered_capture_rechecks_absolute_authority_alias_on_repeated_take(tmp_path):
    directory = tmp_path / "package"
    directory.mkdir()
    first, second, alias = (tmp_path / name for name in ("first.json", "second.json", "authority.json"))
    first.write_bytes(b'{"captured":true}')
    second.write_bytes(first.read_bytes())
    alias.symlink_to(first)
    capture = audit.RegisteredCapture(tmp_path, directory)
    assert capture.take(alias) == first.read_bytes()
    capture.unchanged()
    alias.unlink()
    alias.symlink_to(second)
    with pytest.raises(audit.RegisteredRefusal, match="registered_evidence_changed"):
        capture.take(alias)
    with pytest.raises(audit.RegisteredRefusal, match="registered_evidence_changed"):
        capture.unchanged()
    assert first.read_bytes() == second.read_bytes()


def test_registered_cli_input_is_explicit_and_does_not_select_comparator(registered_case, capsys):
    root, output, _ = registered_case
    assert audit.main(["--root", str(root), "--format", "json",
                       "--roster-manifest", str(registered_roster(registered_case)),
                       "--registered-evaluation", f"explicit-v10={output}"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["totals"]["registered_directories"] == 1
    assert result["targets"]["evaluator_model"] is None
    assert result["targets"]["context_human_review_verified"] is False
    package = result["registered_evaluations"][0]
    assert not package["reasons"], package
    assert package["generation_run"]["arm"] != "explicit-v10"


def test_cli_can_select_context_for_actual_registered_project_without_expanding_legacy_roster(registered_case, capsys):
    root, output, prepared = registered_case
    plan = prepared.document()
    project = plan["generation_run"]["project"]
    assert audit.main(["--root", str(root), "--format", "json",
        "--roster-manifest", str(registered_roster(registered_case)),
        "--registered-evaluation", f"explicit-v10={output}",
        "--context", f"{project}={plan['applicability_context']['path']}",
        "--evaluator-model", plan["runtime"]["canonical_model"]]) == 0
    result = json.loads(capsys.readouterr().out)
    selected = [row for row in result["records"] if row["project"] == project]
    assert len(selected) == 1 and selected[0]["label"] == plan["generation_run"]["label"]
    rows = selected[0]["evaluations"]["rubric20"]["files"]
    assert len(rows) == 3 and all(row["eligible_for_condition_review"] for row in rows)
    assert result["targets"]["context_digests"][project] == plan["context_sha256"]
    assert result["targets"]["context_human_review_verified"] is False
