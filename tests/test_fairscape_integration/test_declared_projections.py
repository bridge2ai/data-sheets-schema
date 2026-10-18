"""#4046 Part A: actual model projections and bound assertion re-emission."""
from copy import deepcopy
import json

import pytest

from src.fairscape_integration.d4d_to_fairscape import D4DToFairscapeConverter
from tests.test_fairscape_integration.test_declared_assertions import crate, convert, typed


def project(fields, *, evidence=None, converter=None):
    from fairscape_models.rocrate import ROCrateV1_2
    data = {"id": "urn:test:projection", "title": "Projection", **fields}
    original = typed(data)
    converter = converter or D4DToFairscapeConverter()
    model = converter.convert(data, source_evidence=evidence)
    assert typed(data) == original
    full = model.model_dump(mode="json", by_alias=True, exclude_none=False)
    root = next(node for node in full["@graph"] if node.get("@id") == "./")
    # Genuine constructor, envelope and JSON readback; no model_construct.
    reloaded = ROCrateV1_2(**json.loads(json.dumps(full, ensure_ascii=True, allow_nan=False)))
    assert typed(reloaded.model_dump(mode="json", by_alias=True, exclude_none=False)) == typed(full)
    return root, converter


@pytest.mark.parametrize("field,value,target,expected", [
    ("citation", "  whole; citation\nα  ", "citation", "  whole; citation\nα  "),
    ("citation", "", "citation", ""),
    ("cleaning_strategies", [{"cleaning_details": ""}], "rai:dataManipulationProtocol", ""),
    ("cleaning_strategies", [{"cleaning_details": "whole; not split"}], "rai:dataManipulationProtocol", "whole; not split"),
    ("funders", [{"grantor": "A, B"}], "funder", "A, B"),
    ("human_subject_research", {"involves_human_subjects": False}, "humanSubjectResearch", "No"),
    ("human_subject_research", {"involves_human_subjects": True}, "humanSubjectResearch", "Yes"),
])
def test_scalar_projection_uses_real_typed_model(field, value, target, expected):
    root, converter = project({field: value})
    assert type(root[target]) is str and root[target] == expected
    row = next(row for row in converter.route_evidence["assertions"] if row["source"] == field)
    assert typed(row["raw"]) == typed(value)
    assert row["target"] == target and row["retention"] == "retained"
    assert row["final_value"] == expected
    if field == "human_subject_research":
        assert root["humanSubjects"] is None
        assert typed(root["d4d:humanSubject"]) == typed(value)


@pytest.mark.parametrize("field,value,target", [
    ("citation", ["first", "second"], "citation"),
    ("citation", False, "citation"),
    ("cleaning_strategies", [{"cleaning_details": "A"}, {"cleaning_details": "A"}], "rai:dataManipulationProtocol"),
    ("cleaning_strategies", [{"cleaning_details": "A", "description": "independent"}], "rai:dataManipulationProtocol"),
    ("funders", [{"grantor": "A"}, {"grantor": "B"}], "funder"),
    ("funders", [{"grantor": "A", "grants": [{"name": "G"}]}], "funder"),
    ("human_subject_research", {"involves_human_subjects": 0}, "humanSubjectResearch"),
    ("data_governance", {"description": "An arbitrary narrative"}, "dataGovernanceCommittee"),
])
def test_no_illegal_scalar_or_inferred_assertion(field, value, target):
    root, converter = project({field: value})
    assert root[target] is None
    row = next(row for row in converter.route_evidence["assertions"] if row["source"] == field)
    assert typed(row["raw"]) == typed(value)
    assert row["decision"] == "unplaced" and row["retention"] == "not_constructed"


def test_supplied_assertions_reemit_only_with_complete_dataset_binding():
    data, reverse = convert(crate({"humanSubjects": False, "humanSubjectResearch": " no ",
        "dataGovernanceCommittee": "committee as supplied", "completeness": "unscored"}))
    evidence = reverse.route_evidence
    forward = D4DToFairscapeConverter()
    before = typed(data), typed(evidence)
    model = forward.convert(data, source_evidence=evidence)
    root = next(node for node in model.model_dump(by_alias=True)["@graph"] if node["@id"] == "./")
    assert root["humanSubjects"] == "No" and root["humanSubjectResearch"] == " no "
    assert root["dataGovernanceCommittee"] == "committee as supplied"
    assert root["completeness"] == "unscored"
    assert (typed(data), typed(evidence)) == before
    assert forward.route_evidence["input"]["kind"] == "dict"
    assert forward.route_evidence["input"]["source_sha256"] is None
    assert forward.route_evidence["supplied_source_evidence"] == evidence
    data["title"] = "Changed outside all seven covered targets"
    with pytest.raises(ValueError, match="complete final Dataset"):
        forward.convert(data, source_evidence=evidence)
    assert forward.route_evidence["status"] == "failed"


@pytest.mark.parametrize("mutation", ["status", "contract", "missing", "duplicate", "pointer", "target"])
def test_evidence_roster_and_binding_are_checked(mutation):
    data, reverse = convert(crate({"citation": "a"}))
    evidence = reverse.route_evidence
    row = next(row for row in evidence["assertions"] if row["source"] == "citation")
    if mutation == "status":
        evidence["status"] = "pending"
    elif mutation == "contract":
        evidence["contract"] = "another contract"
    elif mutation == "missing":
        evidence["assertions"].remove(row)
    elif mutation == "duplicate":
        evidence["assertions"].append(deepcopy(row))
    elif mutation == "pointer":
        row["source_pointer"] = "/@graph/2/citation"
    else:
        row["target"] = "description"
    forward = D4DToFairscapeConverter()
    with pytest.raises(ValueError, match="source_evidence"):
        forward.convert(data, source_evidence=evidence)
    assert forward.route_evidence["status"] == "failed"


def test_richer_supplied_assertion_is_raw_evidence_not_stringified_wire():
    data, reverse = convert(crate({"completeness": {"values": [False, 0, None]},
                                  "dataGovernanceCommittee": {"name": "Not a literal"}}))
    forward = D4DToFairscapeConverter()
    model = forward.convert(data, source_evidence=reverse.route_evidence)
    root = next(node for node in model.model_dump(by_alias=True)["@graph"] if node["@id"] == "./")
    assert root["completeness"] is None and root["dataGovernanceCommittee"] is None
    rows = [row for row in forward.route_evidence["assertions"]
            if row.get("source_kind") == "supplied_reverse_evidence"]
    assert [row["raw"] for row in rows] == [{"values": [False, 0, None]}, {"name": "Not a literal"}]
    assert all(row["decision"] == "unplaced" for row in rows)


@pytest.mark.parametrize("replacement", [0, 0.0])
def test_final_target_binding_distinguishes_boolean_from_number(replacement):
    data, reverse = convert(crate({"humanSubjectResearch": "No"}))
    evidence = reverse.route_evidence
    # The complete Dataset/digest remain genuine; corrupt only the claimed
    # observed final target. Python equality would accept False == 0 == 0.0.
    row = next(row for row in evidence["assertions"] if row["source"] == "humanSubjectResearch")
    assert row["final_value"]["involves_human_subjects"] is False
    row["final_value"]["involves_human_subjects"] = replacement
    with pytest.raises(ValueError, match="final target"):
        D4DToFairscapeConverter().convert(data, source_evidence=evidence)


def test_forward_failed_model_and_reuse_do_not_retain_prior_evidence():
    forward = D4DToFairscapeConverter()
    project({"citation": "previous"}, converter=forward)
    with pytest.raises(ValueError):
        forward.convert({"id": "x", "keywords": False, "citation": "this attempt"})
    evidence = forward.route_evidence
    assert evidence["status"] == "failed" and "previous" not in json.dumps(evidence)
    assert next(row for row in evidence["assertions"] if row["source"] == "citation")["retention"] == "unknown_failed"
    project({"citation": "next"}, converter=forward)
    saved = typed(forward.route_evidence)
    forward.route_evidence["assertions"].clear()
    assert typed(forward.route_evidence) == saved
