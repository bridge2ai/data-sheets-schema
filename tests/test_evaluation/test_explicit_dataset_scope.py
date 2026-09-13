"""Explicit datasets remain scoring targets; collections expose their members."""
import copy
import hashlib
import json

import pytest
import yaml

from data_sheets_schema.evaluation_context import dataset_units, load_document, unwrap_document
from evaluation.evaluate_d4d import D4DEvaluator
from tests.test_evaluation.test_general_api_judge import evaluator
from tests.test_evaluation.test_semantic_context_scope import record, ROOT
from tests.test_evaluation.test_semantic_evaluation_contract import _validator


def declared(name, shape, payload):
    if shape == "wrapper":
        return {name: payload}
    return {**payload, "conforms_to_class": name if shape == "plain" else f"https://example.org/schema/{name}"}


@pytest.mark.parametrize("name", ["Dataset", "CoreDataset", "DatasetCollection", "CoreDatasetCollection"])
@pytest.mark.parametrize("shape", ["plain", "uri", "wrapper"])
def test_explicit_scope_agrees_across_presence_api_and_both_semantic_gates(tmp_path, name, shape):
    payload = {"id": "example:parent", "title": "Parent documentation",
               "purposes": [{"response": "Synthetic cohort research"}],
               "resources": [{"id": "example:child"}]}
    source = declared(name, shape, payload)
    raw = yaml.safe_dump(source).encode()
    path = tmp_path / "scoped.yaml"
    path.write_bytes(raw)
    is_collection = name.endswith("Collection")
    expected = [{"path": "#/resources/0", "id": "example:child"}] if is_collection else [{"path": "#", "id": "example:parent"}]
    wrong = [{"path": "#", "id": "example:parent"}] if is_collection else [{"path": "#/resources/0", "id": "example:child"}]

    presence = D4DEvaluator(ROOT / "data/rubric/rubric10.txt", ROOT / "data/rubric/rubric20.txt")
    scored = presence.evaluate_d4d_file(path, "EXTERNAL_CLINICAL", "manual")
    assert scored.evaluation_scope["units"] == expected
    for element, index in ((1, 2), (1, 4), (7, 1)):
        item = scored.rubric10_scores[element - 1].sub_element_scores[index - 1]
        assert item.score == (0 if is_collection else 1), (element, index, item)

    judge, calls = evaluator(tmp_path)
    ratings = judge.evaluate_file(path, "EXTERNAL_CLINICAL", "manual", "both")
    assert len(calls) == 2
    assert all(rating["evaluation_scope"]["units"] == expected for rating in ratings.values())
    for call in calls:
        contract = json.loads(call["messages"][0]["content"].split("```json\n")[1].split("\n```")[0])
        assert contract["scope"]["units"] == expected

    for rubric in ("rubric10", "rubric20"):
        result, original = record(tmp_path, rubric, {})
        original.write_bytes(raw)
        result["metadata"]["input_sha256"] = hashlib.sha256(raw).hexdigest()
        result["evaluation_scope"].update(policy="single_dataset", units=expected)
        for group in result["elements" if rubric == "rubric10" else "categories"]:
            for item in group["sub_elements" if rubric == "rubric10" else "questions"]:
                item["unit_scores"] = [{**item["unit_scores"][0], "path": expected[0]["path"]}]
        output = tmp_path / f"{rubric}.json"
        output.write_text(json.dumps(result))
        kwargs = {"input_path": original, "definition_path": ROOT / f".claude/agents/d4d-{rubric}-semantic.md"}
        assert _validator().validate_outputs([output], **kwargs) == 0
        result["evaluation_scope"]["units"] = wrong
        for group in result["elements" if rubric == "rubric10" else "categories"]:
            for item in group["sub_elements" if rubric == "rubric10" else "questions"]:
                item["unit_scores"][0]["path"] = wrong[0]["path"]
        output.write_text(json.dumps(result))
        assert _validator().validate_outputs([output], **kwargs) == 1
    assert path.read_bytes() == raw


def test_nested_collection_stops_at_an_explicit_dataset_and_does_not_modify_input():
    child = {"id": "example:dataset", "title": "Member", "resources": [{"id": "example:component"}]}
    source = {"DatasetCollection": {"resources": [{"Dataset": child}, {"id": "example:second"}]}}
    before = copy.deepcopy(source)
    units = dataset_units(unwrap_document(source))
    assert [(path, unit["id"]) for path, unit in units] == [
        ("#/resources/0", "example:dataset"), ("#/resources/1", "example:second")]
    assert source == before
    assert dict(units[0][1]) == child


@pytest.mark.parametrize("name", ["DatasetCollection", "CoreDatasetCollection"])
@pytest.mark.parametrize("shape", ["plain", "uri", "wrapper"])
def test_an_explicit_empty_collection_is_never_a_single_dataset(name, shape):
    with pytest.raises(ValueError, match="resources|resource datasets"):
        dataset_units(unwrap_document(declared(name, shape, {"id": "example:empty", "resources": []})))


@pytest.mark.parametrize("bad", ["invalid", ["invalid"], [{"resources": "invalid"}]])
def test_explicit_dataset_scope_does_not_hide_malformed_components(bad):
    with pytest.raises(ValueError, match="resources"):
        dataset_units({"conforms_to_class": "Dataset", "resources": bad})
