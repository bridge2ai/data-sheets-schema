"""A required provenance block cannot be replaced by null (#614)."""
from copy import deepcopy
import json
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml
from jsonschema.validators import validator_for

from data_sheets_schema import provenance
from data_sheets_schema.cli.provenance import provenance as cli
from data_sheets_schema.record_schema import compile_record_schema, _non_null_required

SCHEMA = Path(__file__).resolve().parents[1] / "src/data_sheets_schema/schema/d4d_generation_record.yaml"


def record(mode="live"):
    result = {
        "record_type": "d4d_generation_provenance", "record_version": 1,
        "record_mode": mode, "record_generated_at": "2026-09-11T00:00:00Z",
        "run": {"project": "TEST", "method": "fixture", "label": "test_rep1", "arm": "fixture"},
        "schema": {"declared_version": "test", "declared_in": "fixture",
                   "merged_schema_carries_version": False, "full_path": "full.yaml", "core_path": "core.yaml"},
        "repo": {"commit": "fixture"}, "software": {"python": "fixture"},
        "outputs": {"full": {"path": "full.yaml"}},
    }
    if mode == "derived":
        result.update(record_type="d4d_derived_provenance", derivation={"method": "fixture"},
                      sources=[{"path": "source.yaml"}],
                      not_applicable=[{"field": "model", "reason": "deterministic derivation"}])
    else:
        result.update(inputs={"bundle_path": "bundle.txt"}, model={"model": "fixture"},
                      system={"platform": "fixture"})
    if mode == "reconstructed":
        result["unrecoverable"] = [{"field": "model.temperature", "reason": "not recorded"}]
    return result


@pytest.fixture(scope="module")
def exported():
    schema = compile_record_schema(SCHEMA)
    cls = validator_for(schema)
    cls.check_schema(schema)
    return cls(schema, format_checker=cls.FORMAT_CHECKER)


@pytest.mark.parametrize("mode", ["live", "reconstructed", "derived"])
def test_null_required_values_fail_both_export_and_runtime(mode, exported):
    good = record(mode)
    assert provenance.check_record(good) == ([], None)
    assert exported.is_valid(good)
    source = yaml.safe_load(SCHEMA.read_text())["classes"]["GenerationRecord"]
    required = {k for k, v in source["attributes"].items() if v.get("required")}
    for rule in source["rules"]:
        condition = rule.get("preconditions", {}).get("slot_conditions", {}).get("record_mode", {})
        if condition.get("equals_string") == mode:
            required.update(k for k, v in rule["postconditions"]["slot_conditions"].items() if v.get("required"))
    for field in required:
        bad = {**good, field: None}
        findings, failure = provenance.check_record(bad)
        assert failure is None
        assert findings, (mode, field)
        assert not exported.is_valid(bad), (mode, field)


def test_optional_nulls_and_arbitrary_interior_values_remain_valid(exported):
    good = record()
    good.update(validation=None, unrecoverable=None)
    good["model"].update(temperature=None, new_nested_block={"anything": [None, False, 0, [1, 2]]})
    assert provenance.check_record(good) == ([], None)
    assert exported.is_valid(good)
    derived = record("derived")
    derived.update(inputs=None, model=None, system=None)
    assert provenance.check_record(derived) == ([], None)
    assert exported.is_valid(derived)


def test_existing_datetime_format_checks_remain_enabled(exported):
    bad = {**record(), "record_generated_at": "not a timestamp"}
    findings, failure = provenance.check_record(bad)
    assert failure is None and findings
    assert not exported.is_valid(bad)


def test_policy_uses_new_schema_requirements_without_a_parallel_field_list(tmp_path):
    source = yaml.safe_load(SCHEMA.read_text())
    cls = source["classes"]["GenerationRecord"]
    cls["attributes"]["new_block"] = {"range": "AnyBlock", "inlined": True}
    live = next(r for r in cls["rules"] if r.get("preconditions", {}).get(
        "slot_conditions", {}).get("record_mode", {}).get("equals_string") == "live")
    live["postconditions"]["slot_conditions"]["new_block"] = {"required": True}
    path = tmp_path / "record.yaml"
    path.write_text(yaml.safe_dump(source))
    schema = compile_record_schema(path)
    validator = validator_for(schema)(schema)
    assert not validator.is_valid({**record(), "new_block": None})
    assert validator.is_valid({**record(), "new_block": {"any_added_field": [None, {}]}})
    assert validator.is_valid(record("derived"))


def test_policy_is_declared_in_the_source_and_bad_annotations_fail(tmp_path):
    source = yaml.safe_load(SCHEMA.read_text())
    assert source["annotations"]["required_values_non_null"] is True
    path = tmp_path / "record.yaml"
    source["annotations"]["required_values_non_null"] = False
    path.write_text(yaml.safe_dump(source))
    schema = compile_record_schema(path)
    assert validator_for(schema)(schema).is_valid({**record(), "model": None})
    source["annotations"]["required_values_non_null"] = "true"
    path.write_text(yaml.safe_dump(source))
    with pytest.raises(ValueError, match="boolean"):
        compile_record_schema(path)


def test_annotation_and_compilation_use_the_same_captured_bytes(tmp_path, monkeypatch):
    from data_sheets_schema import record_schema
    path = tmp_path / "record.yaml"
    path.write_bytes(SCHEMA.read_bytes())
    real_generator = record_schema.JsonSchemaGenerator

    def edit_before_generation(*args, **kwargs):
        changed = yaml.safe_load(path.read_text())
        changed["annotations"]["required_values_non_null"] = False
        path.write_text(yaml.safe_dump(changed))
        return real_generator(*args, **kwargs)

    monkeypatch.setattr(record_schema, "JsonSchemaGenerator", edit_before_generation)
    captured = compile_record_schema(path)
    bad = {**record(), "model": None}
    assert not validator_for(captured)(captured).is_valid(bad)
    fresh = compile_record_schema(path)
    assert validator_for(fresh)(fresh).is_valid(bad)


def test_compilation_does_not_reinterpret_defaults_or_examples_as_schema():
    example = {"required": ["example_key"], "properties": {"example_key": {}}}
    schema = {"required": ["actual"], "properties": {"actual": {}},
              "examples": [deepcopy(example)], "default": deepcopy(example)}
    _non_null_required(schema)
    assert schema["examples"] == [example] and schema["default"] == example
    assert schema["properties"]["actual"] == {"allOf": [{}, {"not": {"type": "null"}}]}


def test_cli_exports_the_same_contract_used_by_the_runtime():
    result = CliRunner().invoke(cli, ["record-schema"])
    assert result.exit_code == 0, result.output
    schema = json.loads(result.output)
    assert schema == compile_record_schema(provenance.record_schema_path())
    assert not validator_for(schema)(schema).is_valid({**record(), "model": None})


def test_validate_records_checks_nulls_and_keeps_processing_bad_files(tmp_path, monkeypatch):
    monkeypatch.setattr(provenance, "CONCAT_DIR", tmp_path)
    directory = tmp_path / "fixture_core/test_rep1"
    directory.mkdir(parents=True)
    (directory / "GOOD_provenance.yaml").write_text(yaml.safe_dump(record()))
    (directory / "NULL_provenance.yaml").write_text(yaml.safe_dump({**record(), "model": None}))
    (directory / "BROKEN_provenance.yaml").write_text("[invalid yaml")
    result = CliRunner().invoke(cli, ["validate-records", "--strict"])
    assert result.exit_code == 1, result.output
    assert "3 record(s) checked, 2 failing" in result.output
    assert "/model" in result.output and "BROKEN_provenance.yaml" in result.output


def test_validate_records_cannot_call_an_unavailable_validator_clean(tmp_path, monkeypatch):
    monkeypatch.setattr(provenance, "CONCAT_DIR", tmp_path)
    directory = tmp_path / "fixture_core/test_rep1"
    directory.mkdir(parents=True)
    (directory / "TEST_provenance.yaml").write_text(yaml.safe_dump(record()))
    monkeypatch.setattr(provenance, "check_record", lambda data: ([], "validator unavailable"))
    result = CliRunner().invoke(cli, ["validate-records", "--strict"])
    assert result.exit_code == 1 and "validator unavailable" in result.output
