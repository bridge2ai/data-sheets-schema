import copy
import csv
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema.judge_contract import evaluation_contract, validate_result
from evaluation.evaluate_d4d_llm import D4DLLMEvaluator, LLMEvaluationConfig
from evaluation.evaluate_d4d_llm import IDENTITY
from tests.judge_fixtures import judge_reply

ROOT = Path(__file__).resolve().parents[2]


def evaluator(tmp_path, *, context=None, mutate=None):
    calls = []

    def create(**request):
        calls.append(request)
        user = request["messages"][0]["content"]
        contract = json.loads(user.split("```json\n")[1].split("\n```")[0])
        rubric = "rubric10" if "Rubric10" in request["system"] else "rubric20"
        result = judge_reply(contract, rubric, "EXTERNAL_CLINICAL", "manual")
        if mutate:
            mutate(result)
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(text=json.dumps(result))])

    obj = D4DLLMEvaluator(
        LLMEvaluationConfig(rubric_dir=ROOT / "data/rubric",
                            prompts_dir=ROOT / "src/download/prompts",
                            error_dir=tmp_path / "errors"),
        context=context, client=SimpleNamespace(messages=SimpleNamespace(create=create)))
    return obj, calls


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_actual_request_carries_external_identity_context_all_resources_and_exact_hash(tmp_path, rubric):
    record = tmp_path / "external.yaml"
    raw = b"CoreDatasetCollection:\n  resources:\n    - id: example:first\n    - id: example:second\n"
    record.write_bytes(raw)
    obj, calls = evaluator(tmp_path, context={"human_subjects": False})
    result = obj.evaluate_file(record, "EXTERNAL_CLINICAL", "manual", rubric)[rubric]
    assert len(calls) == 1
    assert len(result["evaluation_scope"]["units"]) == 2
    assert result["overall_score"]["excluded_items"]
    meta = result["metadata"]
    assert meta["d4d_file_hash"] == hashlib.sha256(raw).hexdigest()
    assert meta["instrument_sha256"] == hashlib.sha256(calls[0]["system"].encode()).hexdigest()
    assert meta["request_user_prompt_sha256"] == hashlib.sha256(calls[0]["messages"][0]["content"].encode()).hexdigest()


@pytest.mark.parametrize("mutation", ["identity", "na", "maximum", "total", "unit", "domain", "duplicate", "name"])
@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_invalid_judge_result_is_refused_and_each_raw_attempt_preserved(tmp_path, rubric, mutation):
    def mutate(result):
        item = result["elements"][0]["sub_elements"][0] if rubric == "rubric10" else result["categories"][0]["questions"][0]
        if mutation == "identity":
            result["project"] = "WRONG"
        elif mutation == "na":
            item.update(applicable=False, score=None, na_reason="field missing", max_score=0)
        elif mutation == "maximum":
            result["overall_score"]["max_points"] -= 1
        elif mutation == "total":
            result["overall_score"]["total_points"] = 1
        elif mutation == "unit":
            item["unit_scores"] = []
        elif mutation == "domain":
            item["score"] = item["unit_scores"][0]["score"] = 0.5 if rubric == "rubric10" else 6
        elif mutation == "name":
            item["name"] = "A different criterion"
        else:
            rows = result["elements"][0]["sub_elements"] if rubric == "rubric10" else result["categories"][0]["questions"]
            rows[1]["id"] = rows[0]["id"]

    record = tmp_path / "input.yaml"
    record.write_text("id: example:record\n")
    obj, calls = evaluator(tmp_path, mutate=mutate)
    for _ in range(2):
        with pytest.raises(RuntimeError, match="Response saved"):
            obj.evaluate_file(record, "EXTERNAL_CLINICAL", "manual", rubric)
    paths = list((tmp_path / "errors").glob("*.json"))
    assert len(paths) == len(calls) == 2
    assert all(json.loads(path.read_text())["response"] for path in paths)


def test_direct_numeric_scale_remains_continuous_and_collection_minimum_is_enforced(tmp_path):
    obj, _ = evaluator(tmp_path)
    document = {"resources": [{"id": "example:a"}, {"id": "example:b"}]}
    contract = evaluation_contract("rubric20", obj.rubric20, {}, document)
    result = judge_reply(contract, "rubric20")
    item = result["categories"][0]["questions"][0]
    item["unit_scores"][0]["score"] = 2.5
    item["unit_scores"][1]["score"] = 4.5
    item["score"] = 2.5
    result["categories"][0]["category_score"] = 2.5
    result["overall_score"].update(total_points=2.5, percentage=round(250/88, 1))
    validate_result(result, "rubric20", "P", "method", contract)
    item["score"] = 4.5
    with pytest.raises(ValueError, match="disagrees"):
        validate_result(result, "rubric20", "P", "method", contract)


def test_malformed_context_and_collections_fail_before_any_request(tmp_path):
    obj, calls = evaluator(tmp_path)
    record = tmp_path / "bad.yaml"
    record.write_text("DatasetCollection: {}\n")
    with pytest.raises(ValueError):
        obj.evaluate_file(record, "EXTERNAL_CLINICAL", "manual")
    assert not calls
    with pytest.raises(ValueError):
        evaluator(tmp_path, context={"human_subjects": "no"})


def test_accepted_first_rating_survives_a_later_rubric_failure(tmp_path):
    def mutate(result):
        if result["rubric"] == "rubric20":
            result["project"] = "WRONG"
    record = tmp_path / "input.yaml"
    record.write_text("id: example:record\n")
    obj, calls = evaluator(tmp_path, mutate=mutate)
    obj.config.attempts_dir = tmp_path / "attempts"
    with pytest.raises(RuntimeError, match="Response saved"):
        obj.evaluate_file(record, "EXTERNAL_CLINICAL", "manual", "both")
    accepted = list(obj.config.attempts_dir.glob("*.json"))
    assert len(calls) == 2 and len(accepted) == 1
    saved = json.loads(accepted[0].read_text())
    assert saved["evaluation"]["rubric"] == "rubric10"
    assert json.loads(saved["raw_response"])["project"] == "EXTERNAL_CLINICAL"
    assert len(list((tmp_path / "errors").glob("*.json"))) == 1


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_extra_or_misgrouped_items_cannot_change_group_results(tmp_path, rubric):
    obj, _ = evaluator(tmp_path)
    specification = obj.rubric10 if rubric == "rubric10" else obj.rubric20
    contract = evaluation_contract(rubric, specification, {}, {"id": "example:record"})
    result = judge_reply(contract, rubric)
    if rubric == "rubric10":
        result["elements"].append({"id": 99, "sub_elements": [], "element_score": 0, "element_max": 0})
    else:
        groups = result["categories"]
        groups[0]["questions"][0], groups[1]["questions"][0] = groups[1]["questions"][0], groups[0]["questions"][0]
    with pytest.raises(ValueError):
        validate_result(result, rubric, "P", "method", contract)


def test_exports_keep_run_and_instrument_identity_for_partially_populated_results(tmp_path):
    record = tmp_path / "input.yaml"
    record.write_text("id: example:record\n")
    obj, _ = evaluator(tmp_path, context={"human_subjects": False})
    results = {}
    for rubric, label in (("rubric10", "first-run"), ("rubric20", "second-run")):
        rating = obj.evaluate_file(record, "EXTERNAL_CLINICAL", "manual", rubric)
        rating[IDENTITY] = {"project": "EXTERNAL_CLINICAL", "method": "manual", "label": label,
                            "file_path": str(record)}
        results[label] = rating
    csv_path = tmp_path / "scores.csv"
    obj.export_to_csv(results, csv_path)
    with csv_path.open() as stream:
        rows = list(csv.DictReader(stream))
    assert [row["label"] for row in rows] == ["first-run", "second-run"]
    assert all(row["file_path"] == str(record) for row in rows)
    assert rows[0]["rubric10_fixed_max_points"] == "50"
    assert rows[1]["rubric20_fixed_max_points"] == "88"
    assert rows[0]["rubric10_context_sha256"]
    assert rows[1]["rubric20_instrument_sha256"]
    markdown = tmp_path / "report.md"
    obj.export_to_markdown(results, markdown, "rubric10")
    assert "first-run" in markdown.read_text()
    assert str(record) in markdown.read_text()
