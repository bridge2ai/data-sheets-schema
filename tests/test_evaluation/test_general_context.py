"""Behavioral coverage for external identities, applicability and collections."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema.evaluation_context import (
    PREDICATES, applicability, dataset_units, normalize_context, unwrap_document,
)
from evaluation.evaluate_d4d import D4DEvaluator, validate_d4d_yaml

ROOT = Path(__file__).resolve().parents[2]


def evaluator(context=None):
    return D4DEvaluator(ROOT / "data/rubric/rubric10.txt",
                        ROOT / "data/rubric/rubric20.txt", context=context)


def test_individual_records_accept_any_method_and_honor_explicit_project_selection(tmp_path):
    for project in ("EXTERNAL_CLINICAL", "ANOTHER_DATASET"):
        directory = tmp_path / "d4d_individual" / "curated" / project
        directory.mkdir(parents=True)
        (directory / "protocol_d4d.yaml").write_text("id: example:record\n")
    results = evaluator().evaluate_individual_files(tmp_path, ["curated"], projects=["EXTERNAL_CLINICAL"])
    assert [(result.project, result.method) for result in results] == [("EXTERNAL_CLINICAL/protocol", "curated")]


def test_presence_cli_keeps_external_identity_and_writes_beside_earlier_results(tmp_path, monkeypatch):
    import socket
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli
    def no_network(*args, **kwargs):
        raise AssertionError("presence evaluation must be offline")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    record = tmp_path / "external.yaml"
    record.write_text("id: https://example.org/synthetic\ntitle: Synthetic external dataset\n")
    context = tmp_path / "context.yaml"
    context.write_text("human_subjects: false\n")
    output = tmp_path / "results"
    output.mkdir()
    previous = output / "earlier-scores.json"
    previous.write_text('{"historical": true}\n')
    args = ["evaluate", "presence", "--file", str(record), "--context", str(context),
            "--project", "EXTERNAL CLINICAL", "--method", "manual", "--output-dir", str(output)]
    for _ in range(2):
        response = CliRunner().invoke(cli, args)
        assert response.exit_code == 0, response.output
    scores = list(output.glob("*_presence-v2_*/*scores.json"))
    assert len(scores) == 2
    for path in scores:
        result = json.loads(path.read_text())[0]
        assert result["project"] == "EXTERNAL CLINICAL"
        assert result["method"] == "manual"
        assert result["instrument"]["context_sha256"]
    assert previous.read_text() == '{"historical": true}\n'


def evaluate(tmp_path, document, context=None):
    path = tmp_path / "external.yaml"
    path.write_text(yaml.safe_dump(document))
    return evaluator(context).evaluate_d4d_file(path, "EXTERNAL_CLINICAL", "manual")


def test_missing_context_is_unknown_and_does_not_exclude_missing_evidence(tmp_path):
    result = evaluate(tmp_path, {"id": "example:record"})
    assert result.rubric10_max == 50
    assert result.rubric20_max == 88
    assert result.excluded_items == {"rubric10": [], "rubric20": []}
    assert result.rubric10_scores[3].sub_element_scores[2].applicability_status == "unknown"
    assert result.rubric10_scores[3].sub_element_scores[2].score == 0


def test_nonhuman_does_not_imply_no_governance_and_processing_is_independent(tmp_path):
    context = {"human_subjects": False, "regulated_access": True,
               "data_processing": True, "processing_software": False}
    result = evaluate(tmp_path, {"id": "example:record"}, context)
    assert result.rubric10_scores[3].max_score == 2
    assert result.rubric10_scores[7].sub_element_scores[2].applicable
    assert result.rubric10_scores[7].sub_element_scores[2].score == 0
    assert not result.rubric10_scores[7].sub_element_scores[3].applicable
    assert result.rubric20_scores[10].applicable
    assert "E4.3" in result.excluded_items["rubric10"]
    assert "Q8" in result.excluded_items["rubric20"]
    assert result.rubric20_scores[7].score is None


@pytest.mark.parametrize("context", [
    {"human_subject": True}, {"human_subjects": "false"}, {"human_subjects": 0},
    {"human_subjects": {"value": False}}, {"human_subjects": {"value": False, "evidence": " "}},
    {"human_subjects": {"value": True, "evidence": "source", "typo": True}}, [],
])
def test_invalid_declarations_are_refused(context):
    with pytest.raises(ValueError):
        normalize_context(context)


def test_three_valued_predicates_preserve_unknowns():
    context = normalize_context({"human_subjects": False, "data_processing": True})
    assert applicability({"any": ["human_subjects", "regulated_access"]}, context).value is None
    assert applicability({"all": ["human_subjects", "regulated_access"]}, context).value is False
    assert applicability({"any": ["data_processing", "regulated_access"]}, context).value is True


@pytest.mark.parametrize("wrapper", ["DatasetCollection", "CoreDatasetCollection"])
def test_all_collection_children_and_distributions_have_evidence_without_sibling_credit(tmp_path, wrapper):
    children = [{"id": "example:empty"}, {"id": "example:rich", "title": "Complete",
                "description": "A documented resource", "keywords": ["clinical"],
                "distributions": [{"format": "CSV", "bytes": 1024}]}]
    first = evaluate(tmp_path, {wrapper: {"resources": children}})
    second = evaluate(tmp_path, {wrapper: {"resources": list(reversed(children))}})
    assert first.rubric10_total == second.rubric10_total
    assert first.rubric20_total == second.rubric20_total
    title = first.rubric10_scores[0].sub_element_scores[1]
    assert title.score == 0
    assert [row["score"] for row in title.unit_scores] == [0, 1]
    assert any("#/resources/1/title" in value for value in title.found_values)
    distribution = [value for element in first.rubric10_scores
                    for item in element.sub_element_scores for value in item.found_values]
    assert any("#/resources/1/distributions/0/format" in value for value in distribution)
    assert len(first.evaluation_scope["units"]) == 2


@pytest.mark.parametrize("document", [
    {"DatasetCollection": {}}, {"CoreDatasetCollection": {"resources": []}},
    {"resources": "bad"}, {"resources": [{"id": "example:x"}, "bad"]},
])
def test_empty_or_malformed_collections_are_not_silently_scored(document):
    with pytest.raises(ValueError):
        dataset_units(unwrap_document(document))


def test_zero_denominator_and_exports_retain_na_scope_and_prior_outputs(tmp_path):
    obj = evaluator({key: False for key in PREDICATES})
    for element in obj.rubric10["d4d_complex_proxy_rubric"]["rubric"]:
        for item in element["sub_elements"]:
            item["applies_to"] = "human_subjects"
    for item in obj.rubric20["d4d_evaluation_rubric"]["rubric"]:
        item["applies_to"] = "human_subjects"
    record = tmp_path / "input.yaml"
    record.write_text("id: example:record\n")
    result = obj.evaluate_d4d_file(record, "EXTERNAL_CLINICAL", "manual")
    assert result.rubric10_max == result.rubric20_max == 0
    assert result.rubric10_percentage is result.rubric20_percentage is None
    assert result.rubric10_fixed_max == 50
    obj.export_scores_json([result], tmp_path / "scores.json")
    obj.generate_detailed_report(result, tmp_path / "detail.md")
    obj.generate_summary_report([result], tmp_path / "summary.md")
    exported = json.loads((tmp_path / "scores.json").read_text())[0]
    assert exported["rubric10"]["percentage"] is None
    assert exported["rubric10"]["fixed_percentage"] == 0
    assert len(exported["excluded_items"]["rubric10"]) == 50
    assert "N/A" in (tmp_path / "detail.md").read_text()
    assert "EXTERNAL_CLINICAL" in (tmp_path / "summary.md").read_text()


@pytest.mark.parametrize("wrapper", ["DatasetCollection", "CoreDatasetCollection"])
def test_validator_passes_the_entire_collection_to_linkml(tmp_path, monkeypatch, wrapper):
    record = tmp_path / "collection.yaml"
    children = [{"id": "example:first"}, {"id": "example:second", "unknown_slot": "bad"}]
    record.write_text(yaml.safe_dump({wrapper: {"resources": children}}))
    captured = []

    def run(command, **kwargs):
        captured.append(command)
        assert yaml.safe_load(Path(command[-1]).read_text())["resources"] == children
        assert command[command.index("-C") + 1] == wrapper
        return SimpleNamespace(returncode=1, stdout="invalid second resource", stderr="")

    monkeypatch.setattr("evaluation.evaluate_d4d.subprocess.run", run)
    assert not validate_d4d_yaml(record)
    assert len(captured) == 1


@pytest.mark.parametrize("method,filename,document", [
    ("independent_core", "record.yaml", {"id": "example:core"}),
    ("manual", "record_core.yaml", {"id": "example:core"}),
    ("manual", "record.yaml", {"id": "example:core", "conforms_to_class": "CoreDataset"}),
    ("manual", "record.yaml", {"id": "example:core", "distributions": [{"format": "CSV"}]}),
])
def test_core_validation_is_independent_of_study_method_names(tmp_path, monkeypatch, method, filename, document):
    path = tmp_path / filename
    path.write_text(yaml.safe_dump(document))
    def run(command, **kwargs):
        assert command[command.index("-C")+1] == "CoreDataset"
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr("evaluation.evaluate_d4d.subprocess.run", run)
    assert validate_d4d_yaml(path, method)
