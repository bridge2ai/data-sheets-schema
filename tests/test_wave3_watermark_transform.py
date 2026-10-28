"""Offline R_V5 F5/F7/F9 controls (#5226), 2026-10-27.

Inputs are synthetic reports, JSON keys and mapping mutations; no generation
artifacts or provider calls are used. Root runs these with the frozen suite.
"""
from __future__ import annotations

import pytest
import yaml

from data_sheets_schema import provedown as pd
from data_sheets_schema import report_claims as reports
from data_sheets_schema import transformation_receipts as tr


@pytest.mark.parametrize("version", [7, 8, 9])
def test_watermark_optin_has_one_unambiguous_instrument(version):
    kwargs = {"declared": {"Dataset": {"total_files"}, "CoreDataset": {"total_files"}}}
    report = "Count `3`{pd: full:/total_files}"
    actual = reports.check_report(report, {"total_files": 2}, {},
                                  instrument_version=version, check_watermarks=True, **kwargs)
    expected = reports.check_report(report, {"total_files": 2}, {}, instrument_version=9, **kwargs)
    assert actual == expected
    assert actual["watermarks"]["mismatched"] == 1


@pytest.mark.parametrize("report", [
    "Count `2`{pd: full:/total_files",
    "Count `2`{pd: }",
    "Count 2{pd: full:/total_files}",
    "Count [2]<!-- pd: full:/total_files",
    "Count [2]<!-- pd: -->",
    "Count 2<!-- pd: full:/total_files -->",
    "Count `   `{pd: full:/total_files}",
    "Count [   ]<!-- pd: full:/total_files -->",
])
def test_malformed_explicit_watermark_is_counted_and_refused(report):
    checked = pd.verify_watermarks(report, full={"total_files": 2})
    assert checked["total"] == checked["mismatched"] == 1
    assert checked["verified"] == 0
    assert checked["findings"][0]["kind"] == "watermark_malformed"


def test_valid_and_malformed_markers_retained_without_counting_fenced_examples():
    report = """```markdown
`2`{pd: full:/total_files
```
Count `2`{pd: full:/total_files}
Broken [2]<!-- pd: full:/total_files
"""
    checked = pd.verify_watermarks(report, full={"total_files": 2})
    assert checked["total"] == 2
    assert checked["verified"] == checked["mismatched"] == 1
    assert checked["findings"][0]["line"] == 5


@pytest.mark.parametrize("path,value", [
    ("/", {"b": 3}),
    ("//b", 3),
    ("/a//b", 5),
    ("/a/", {"b": 5}),
    ("/a~1b/~0key", 7),
])
def test_json_pointer_empty_segments_and_escapes(path, value):
    source = {"": {"b": 3}, "a": {"": {"b": 5}}, "a/b": {"~key": 7}}
    found, actual, wildcard = pd._resolve_tokens(source, pd._parse_path_tokens(path))
    assert found
    assert actual == value
    assert not wildcard


def _record_and_receipt():
    full = {"id": "example:dataset", "title": "Example", "description": "Synthetic record"}
    core = tr.derive_core_declarative(full)
    return full, core, tr.emit_transformation_receipt(full, core)


@pytest.mark.parametrize("mutation", ["missing", "extra", "boolean", "float", "changed"])
def test_transformation_counters_have_exact_keys_values_and_integer_types(mutation):
    full, core, receipt = _record_and_receipt()
    assert tr.verify_transformation_receipt(receipt, full, core)["verified"]
    if mutation == "missing":
        del receipt["counts"]["constants_set"]
    elif mutation == "extra":
        receipt["counts"]["unverified_counter"] = 0
    elif mutation == "boolean":
        receipt["counts"]["dialect_derived"] = False
    elif mutation == "float":
        receipt["counts"]["constants_set"] = 2.0
    else:
        receipt["counts"]["identity_copied"] += 1
    result = tr.verify_transformation_receipt(receipt, full, core)
    assert not result["verified"]
    assert any(f["kind"] == "transformation_counts_mismatch" for f in result["findings"])


@pytest.mark.parametrize("class_name,slot_name,mutation", [
    ("CoreDataset", "dialect", "'invented dialect'"),
    ("CoreDataset", "resources", "different_projection(resources)"),
    ("CoreDataset", "distributions", "different_projection(file_collections)"),
    ("CoreDataset", "conforms_to_class", "'Dataset'"),
    ("CoreDataset", "conforms_to_schema", "'different-schema.yaml'"),
    ("CoreDistributionFromCollection", "bytes", "total_bytes * 1000"),
    ("CoreDistributionFromFile", "bytes", "bytes * 1000"),
])
def test_modified_mapping_expression_is_rejected_before_execution(tmp_path, class_name, slot_name, mutation):
    document = yaml.safe_load(tr.DEFAULT_MAPPING_PATH.read_text())
    document["class_derivations"][class_name]["slot_derivations"][slot_name]["expr"] = mutation
    mapping = tmp_path / "mapping.yaml"
    mapping.write_text(yaml.safe_dump(document))
    spec, _, _ = tr.load_transformation_spec(mapping)
    assert not tr.validate_spec_against_pair_schema(spec)["valid"]
    with pytest.raises(ValueError, match="unsupported transformation specification"):
        tr.derive_core_declarative({"id": "example:dataset"}, spec_path=mapping)
    full, core, receipt = _record_and_receipt()
    result = tr.verify_transformation_receipt(receipt, full, core, spec_path=mapping)
    assert not result["verified"]
    assert result["derivations_verified"] == 0


@pytest.mark.parametrize("change", ["missing_expr", "extra_slot", "source_class", "source_slot"])
def test_ignored_mapping_structure_cannot_be_accepted(tmp_path, change):
    document = yaml.safe_load(tr.DEFAULT_MAPPING_PATH.read_text())
    deriv = document["class_derivations"]["CoreDataset"]
    if change == "missing_expr":
        deriv["slot_derivations"]["dialect"] = {}
    elif change == "extra_slot":
        deriv["slot_derivations"]["invented"] = {"expr": "'ignored'"}
    elif change == "source_class":
        deriv["populated_from"] = "File"
    else:
        deriv["slot_derivations"]["resources"]["populated_from"] = "other_resources"
    mapping = tmp_path / "mapping.yaml"
    mapping.write_text(yaml.safe_dump(document))
    spec, _, _ = tr.load_transformation_spec(mapping)
    assert not tr.validate_spec_against_pair_schema(spec)["valid"]
    with pytest.raises(ValueError, match="unsupported transformation specification"):
        tr.derive_core_declarative({"id": "example:dataset"}, spec_path=mapping)


@pytest.mark.parametrize("change", ["slot_hide", "slot_range", "class_mirror", "top_slots", "slot_name"])
def test_unsupported_linkml_operations_are_not_silently_ignored(tmp_path, change):
    document = yaml.safe_load(tr.DEFAULT_MAPPING_PATH.read_text())
    deriv = document["class_derivations"]["CoreDataset"]
    slot = deriv["slot_derivations"]["title"]
    if change == "slot_hide":
        slot["hide"] = True
    elif change == "slot_range":
        slot["range"] = "integer"
    elif change == "class_mirror":
        deriv["mirror_source"] = True
    elif change == "top_slots":
        document["slot_derivations"] = {"extra": {"name": "extra", "expr": "'ignored'"}}
    else:
        slot["name"] = "different_target"
    mapping = tmp_path / "mapping.yaml"
    mapping.write_text(yaml.safe_dump(document))
    spec, _, _ = tr.load_transformation_spec(mapping)
    assert not tr.validate_spec_against_pair_schema(spec)["valid"]
    with pytest.raises(ValueError, match="unsupported transformation specification"):
        tr.derive_core_declarative({"id": "example:dataset"}, spec_path=mapping)


def test_mapping_documentation_changes_remain_accepted(tmp_path):
    document = yaml.safe_load(tr.DEFAULT_MAPPING_PATH.read_text())
    document["title"] = "Documented bounded transformation"
    document["class_derivations"]["CoreDataset"]["slot_derivations"]["title"]["description"] = "Copy title."
    mapping = tmp_path / "mapping.yaml"
    mapping.write_text(yaml.safe_dump(document))
    spec, _, _ = tr.load_transformation_spec(mapping)
    assert tr.validate_spec_against_pair_schema(spec)["valid"]
    full = {"id": "example:dataset", "title": "Preserved"}
    assert tr.derive_core_declarative(full, spec_path=mapping) == tr.derive_core_declarative(full)


@pytest.mark.parametrize("field", ["source_schema", "target_schema"])
def test_mapping_schema_identity_must_match_loaded_pair(tmp_path, field):
    document = yaml.safe_load(tr.DEFAULT_MAPPING_PATH.read_text())
    document[field] = "different-schema.yaml"
    mapping = tmp_path / "mapping.yaml"
    mapping.write_text(yaml.safe_dump(document))
    spec, _, _ = tr.load_transformation_spec(mapping)
    result = tr.validate_spec_against_pair_schema(spec)
    assert not result["valid"]
    assert any(field in reason for reason in result["unsupported_semantics"])
    with pytest.raises(ValueError, match="unsupported transformation specification"):
        tr.derive_core_declarative({"id": "example:dataset"}, spec_path=mapping)


@pytest.mark.parametrize("change", ["null_classes", "missing_class", "null_slots", "invalid_yaml_model"])
def test_malformed_mapping_verification_is_structured(tmp_path, change):
    full, core, receipt = _record_and_receipt()
    document = yaml.safe_load(tr.DEFAULT_MAPPING_PATH.read_text())
    if change == "null_classes":
        document["class_derivations"] = None
    elif change == "missing_class":
        del document["class_derivations"]["CoreDataset"]
    elif change == "null_slots":
        document["class_derivations"]["CoreDataset"]["slot_derivations"] = None
    else:
        document["class_derivations"]["CoreDataset"] = "not a class derivation"
    mapping = tmp_path / "mapping.yaml"
    mapping.write_text(yaml.safe_dump(document))
    result = tr.verify_transformation_receipt(receipt, full, core, spec_path=mapping)
    assert result["checked"]
    assert not result["verified"]
    assert result["mismatched"] == 1
    assert result["derivations_verified"] == 0
