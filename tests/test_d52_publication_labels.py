"""D52 publication finding D1, 2026-10-28: labels describe retained criteria.

Inputs are synthetic datasets and the frozen rubrics; JSON outputs stay in
pytest's external basetemp. No historical scoring or rubric/context edits.
"""
import copy
import json

import pytest
import yaml

from tests.test_d52_scoring import evaluator, q9, record


def test_exported_unregulated_q9_labels_describe_only_retained_criteria(tmp_path):
    ev = evaluator({"regulated_access": False})
    data = record()
    data["regulatory_restrictions"] = {"description": "Synthetic unregulated dataset"}
    source = tmp_path / "record.yaml"
    source.write_text(yaml.safe_dump(data), encoding="utf-8")
    result = ev.evaluate_d4d_file(source, "EXAMPLE", "manual")
    target = tmp_path / "scores.json"
    ev.export_scores_json([result], target)
    exported = json.loads(target.read_text(encoding="utf-8"))[0]
    question = next(q for q in exported["rubric20"]["questions"] if q["id"] == 9)
    assert question["score"] == question["max_score"] == 5
    assert exported["rubric20"]["fixed_max"] == 88
    assert "3/3 fields populated" in question["score_label"]
    assert "4 regulated-access criteria excluded under D52" in question["score_label"]
    assert "confidentiality classification" not in question["score_label"]
    assert "governance contact" not in question["score_label"]
    assert "no additional source evidence is inferred" in question["applicability_evidence"]
    assert question["unit_scores"][0]["label"] == question["score_label"]


@pytest.mark.parametrize("populated,expected", [(0, 0), (1, 3), (2, 3), (3, 5)])
def test_all_false_context_bands_describe_actual_remaining_coverage(populated, expected):
    ev = evaluator({"regulated_access": False})
    question = q9(ev)
    original = copy.deepcopy(question)
    keys = ("license_and_use_terms", "ip_restrictions", "regulatory_restrictions")
    data = {key: {"description": "Synthetic evidence"} for key in keys[:populated]}
    result = ev._score_rubric20_question(data, question)
    assert result.score == expected and result.max_score == 5
    assert f"{populated}/3 fields populated" in result.score_label
    assert "4 regulated-access criteria excluded under D52" in result.score_label
    assert "confidentiality classification" not in result.score_label
    assert "governance contact" not in result.score_label
    assert question == original


@pytest.mark.parametrize("context", [{}, {"regulated_access": None}, {"regulated_access": True}])
def test_context_without_omissions_keeps_original_band_label(context):
    ev = evaluator(context)
    question = q9(ev)
    result = ev._score_rubric20_question(record(), question)
    bands = {int(key): value for key, value in question["scoring"].items()}
    assert result.score == 3
    assert result.score_label == bands[3] + " (6/7 fields populated)"


def test_collection_label_follows_worst_member_without_combining_evidence(tmp_path):
    ev = evaluator({"regulated_access": False})
    complete = record()
    complete["regulatory_restrictions"] = {"description": "Synthetic evidence"}
    partial = {"license_and_use_terms": {"description": "Synthetic terms"}}
    path = tmp_path / "collection.yaml"
    path.write_text(yaml.safe_dump({"DatasetCollection": {"resources": [complete, partial]}}))
    result = ev.evaluate_d4d_file(path, "EXAMPLE", "manual")
    scored = next(q for q in result.rubric20_scores if q.question_id == 9)
    assert scored.score == 3
    assert [unit["score"] for unit in scored.unit_scores] == [5, 3]
    assert "3/3 fields populated" in scored.unit_scores[0]["label"]
    assert "1/3 fields populated" in scored.score_label == scored.unit_scores[1]["label"]
    assert all("4 regulated-access criteria excluded under D52" in unit["label"] for unit in scored.unit_scores)
