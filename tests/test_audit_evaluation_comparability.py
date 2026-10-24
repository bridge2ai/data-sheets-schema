"""Offline provenance/condition audit tests; never score or alter retained corpus."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket

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
    return audit.audit(corpus[0], arms=ARMS, evaluator_model=MODEL,
                       contexts={"CHORUS": CONTEXT}, **kwargs)


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
    result = audit.audit(corpus[0], arms=ARMS)
    row = block(result)["files"][0]
    assert not row["reasons"]
    assert row["pending"] == ["target_context_not_selected", "target_evaluator_not_selected"]
    assert row["eligible_for_condition_review"] is False
    assert result["targets"]["context_human_review_verified"] is False


def test_changed_independent_context_refuses_self_consistent_evaluator_context(corpus):
    rating(corpus)
    result = audit.audit(corpus[0], arms=ARMS, evaluator_model=MODEL, contexts={"CHORUS": {"human_subjects": False}})
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
