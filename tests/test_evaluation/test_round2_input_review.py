"""Schema-valid external inputs and complete instrument guidance (#1458/#1459)."""
import json
from pathlib import Path
import re
from types import SimpleNamespace

import jsonschema
from linkml.generators.jsonschemagen import JsonSchemaGenerator
import pytest
import yaml

from data_sheets_schema.evaluation_context import dataset_units, unwrap_document
from data_sheets_schema.judge_contract import evaluation_contract
from evaluation.evaluate_d4d import validate_d4d_yaml
from tests.test_evaluation.test_general_context import evaluator

ROOT = Path(__file__).resolve().parents[2]

# Every MediaTypeEnum value has a declared format counterpart. JSONL has no
# MIME entry in the schema; do not assume application/json means JSON Lines.
PAIRS = {
    "text/csv": "CSV", "text/tab-separated-values": "TSV",
    "application/json": "JSON", "application/xml": "XML", "text/xml": "XML",
    "application/yaml": "YAML", "text/yaml": "YAML", "text/html": "HTML",
    "application/pdf": "PDF",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "XLSX",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PPTX",
    "text/plain": "TXT", "text/markdown": "MD", "application/zip": "ZIP",
    "application/x-tar": "TAR", "application/gzip": "GZ",
    "application/x-bzip2": "BZ2", "application/x-xz": "XZ",
}


@pytest.mark.parametrize("empty", [None, []])
@pytest.mark.parametrize("wrapper", [None, "Dataset"])
def test_empty_optional_resources_are_a_terminal_dataset(tmp_path, empty, wrapper):
    document = {"id": "https://example.org/dataset", "resources": empty}
    raw = {wrapper: document} if wrapper else document
    assert dataset_units(unwrap_document(raw)) == [("#", document)]
    path = tmp_path / "record.yaml"
    path.write_text(yaml.safe_dump(raw))
    obj = evaluator()
    score = obj.evaluate_d4d_file(path, "EXTERNAL", "manual")
    assert score.evaluation_scope["policy"] == "single_dataset"
    for name, rubric in (("rubric10", obj.rubric10), ("rubric20", obj.rubric20)):
        contract = evaluation_contract(name, rubric, {}, unwrap_document(raw))
        assert contract["scope"]["policy"] == "single_dataset"


@pytest.mark.parametrize("wrapper", ["DatasetCollection", "CoreDatasetCollection"])
@pytest.mark.parametrize("empty", [None, []])
def test_explicit_empty_collections_still_fail(wrapper, empty):
    with pytest.raises(ValueError, match="collection must contain"):
        dataset_units(unwrap_document({wrapper: {"id": "example:collection", "resources": empty}}))


@pytest.fixture(scope="module")
def schemas():
    return {name: json.loads(JsonSchemaGenerator(str(ROOT / path)).serialize()) for name, path in {
        "full": "src/data_sheets_schema/schema/data_sheets_schema.yaml",
        "core": "src/data_sheets_schema/schema/data_sheets_schema_core.yaml",
    }.items()}


def schema_validator(monkeypatch, schemas):
    """Run the selected actual LinkML-generated JSON schema, not a canned pass."""
    chosen = []
    def run(command, **kwargs):
        cls = command[command.index("-C") + 1]
        chosen.append(cls)
        schema = schemas["core" if cls.startswith("Core") else "full"]
        validation = {"$defs": schema["$defs"], "$ref": f"#/$defs/{cls}"}
        try:
            jsonschema.validate(yaml.safe_load(Path(command[-1]).read_text()), validation)
        except jsonschema.ValidationError as exc:
            return SimpleNamespace(returncode=1, stdout=exc.message, stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr("evaluation.evaluate_d4d.subprocess.run", run)
    return chosen


@pytest.mark.parametrize("method", ["manual", "curated", "independent_core"])
def test_core_collection_validation_does_not_depend_on_method(tmp_path, monkeypatch, schemas, method):
    path = tmp_path / "collection.yaml"
    path.write_text(yaml.safe_dump({"id": "https://example.org/collection", "resources": [
        {"id": "https://example.org/dataset", "distributions": [{"format": "CSV"}]}]}))
    chosen = schema_validator(monkeypatch, schemas)
    assert validate_d4d_yaml(path, method)
    assert chosen == ["CoreDatasetCollection"]


@pytest.mark.parametrize("empty", [None, []])
def test_validator_uses_dataset_class_for_empty_optional_resources(tmp_path, monkeypatch, schemas, empty):
    path = tmp_path / "dataset.yaml"
    path.write_text(yaml.safe_dump({"id": "https://example.org/dataset", "resources": empty}))
    chosen = schema_validator(monkeypatch, schemas)
    assert validate_d4d_yaml(path, "manual")
    assert chosen == ["Dataset"]


@pytest.mark.parametrize("explicit", [False, True])
def test_collection_inference_does_not_override_declarations_or_hide_invalid_children(tmp_path, monkeypatch, schemas, explicit):
    document = {"id": "https://example.org/collection", "resources": [
        {"id": "https://example.org/one", "distributions": [{"format": "CSV"}]}]}
    if explicit:
        document = {"DatasetCollection": document}
    else:
        document["resources"].append({"id": "https://example.org/two", "unknown_slot": True})
    path = tmp_path / "collection.yaml"
    path.write_text(yaml.safe_dump(document))
    chosen = schema_validator(monkeypatch, schemas)
    assert not validate_d4d_yaml(path, "manual")
    assert chosen == ["DatasetCollection" if explicit else "CoreDatasetCollection"]


@pytest.mark.parametrize("field", ["distribution_formats", "distributions"])
@pytest.mark.parametrize("mime,format_name", PAIRS.items())
def test_every_schema_format_and_its_mime_alias_count_as_one_type(field, mime, format_name):
    obj = evaluator()
    question = next(q for q in obj.rubric20["d4d_evaluation_rubric"]["rubric"] if q["id"] == 4)
    result = obj._score_rubric20_question({field: [
        {"format": format_name}, {"media_type": mime}]}, question)
    assert result.score == 0


def test_format_equivalence_cases_cover_the_actual_schema_enums():
    schema = yaml.safe_load((ROOT / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml").read_text())
    assert set(PAIRS) == set(schema["enums"]["MediaTypeEnum"]["permissible_values"])
    assert set(PAIRS.values()) == set(schema["enums"]["FormatEnum"]["permissible_values"]) - {"JSONL"}
    assert evaluator()._count_distinct_types(["ZIP", "application/zip", "TAR", "application/x-tar"]) == 2
    assert evaluator()._count_distinct_types(["JSON", "JSONL", "application/octet-stream"]) == 3


def test_entire_semantic_definition_teaches_only_discrete_individual_numeric_scores():
    text = (ROOT / ".claude/agents/d4d-rubric20-semantic.md").read_text()
    assert not re.search(r"0\s*[-–]\s*5|from 0 through 5|full .*range for numeric", text)
    sections = text.split("## Rubric20 Specification", 1)[-1]
    assert "**Scoring (numeric 0/3/5):**" in sections
    assert "only 0, 3 or 5" in text.split("## Scoring Summary", 1)[1]
