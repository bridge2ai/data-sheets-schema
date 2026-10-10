"""Public defect shapes reach the existing nested instrument (#3342).

Records are neutral synthetic examples, not private canary outputs. These
controls prove request binding and context, not a model's semantic accuracy.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import support_judge, support_targets as nested


@pytest.fixture(scope="module")
def real_schema():
    path = Path(__file__).resolve().parents[2] / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
    return nested.NestedSupportSchema.from_schema(path, root_class="Dataset")


@pytest.fixture
def record():
    return {
        "id": "dataset:harbor", "name": "Harbor survey",
        "collection_mechanisms": [
            {"name": "Interviews", "mechanism_details": "Staff recorded interviews."},
            {"name": "Sensors", "mechanism_details": "Sensors recorded measurements."},
            {"name": "Collection service", "mechanism_details": "The collection service is deployed.",
             "description": "Source A describes deployment as a future activity."},
        ],
        "distribution_formats": [
            {"name": f"Format {i}", "notes": "Measurements are provided."}
            for i in range(6)
        ],
        "maintainers": [{"name": "Dana Example", "role": "academic_institution",
                         "maintainer_details": "Project contact; maintenance responsibility is unspecified."}],
        "data_governance": {
            "name": "Access oversight",
            "committee_contact": {"id": "person:dana", "name": "Dana Example"},
        },
        "splits": [{"name": "Holdout plan", "split_details":
                    "Source B describes the holdout; Source A corroborates it."}],
    }


def inventory(record, schema):
    raw = yaml.safe_dump(record, sort_keys=False, allow_unicode=True).encode("utf-8")
    return raw, nested.inventory_targets(raw, schema, artifact_kind="full")


@pytest.mark.parametrize("pointer,kind,owner_pointer,owner_class,slot,slot_range", [
    ("/collection_mechanisms/2/mechanism_details", "attribute_value",
     "/collection_mechanisms/2", "CollectionMechanism", "mechanism_details", "string"),
    ("/distribution_formats/4/notes", "attribute_value",
     "/distribution_formats/4", "DistributionFormat", "notes", "string"),
    ("/distribution_formats/5/notes", "attribute_value",
     "/distribution_formats/5", "DistributionFormat", "notes", "string"),
    ("/maintainers/0/role", "attribute_value",
     "/maintainers/0", "Maintainer", "role", "CreatorOrMaintainerEnum"),
    ("/data_governance/committee_contact", "relationship_edge",
     "/data_governance", "DataGovernance", "committee_contact", "Person"),
    ("/splits/0/split_details", "attribute_value",
     "/splits/0", "Splits", "split_details", "string"),
])
def test_public_defect_paths_use_effective_nested_spec_and_nearest_owner(
        real_schema, record, pointer, kind, owner_pointer, owner_class, slot, slot_range):
    """#1782/#1801/#1815 require these nested questions, not parent verdicts."""
    before = deepcopy(record)
    raw, targets = inventory(record, real_schema)
    target = targets.target(pointer, kind=kind)
    payload = target.to_dict()
    expected_value = nested.resolve_pointer(record, pointer)
    owner = nested.resolve_pointer(record, owner_pointer)
    specification = payload["specification"]
    assert payload["value"] == expected_value
    assert specification["slot"] == real_schema.to_dict()["classes"][owner_class]["slots"][slot]["definition"]
    assert specification["slot"]["range"] == slot_range
    assert specification["slot"]["description"].strip()
    assert specification["owning_class"]["name"] == owner_class
    assert [edge["slot"]["name"] for edge in specification["class_slot_chain"]] == [pointer.split("/")[1], slot]
    context = payload["context"]
    assert context["containing_entity"]["pointer"] == owner_pointer
    assert context["containing_entity"]["class"] == owner_class
    assert context["containing_entity"]["value"]["name"] == owner["name"]
    assert context["collection_metadata_inherited"] is False
    assert payload["artifact"]["input_sha256"] == hashlib.sha256(raw).hexdigest()
    request = nested.render_request(target, bundle="Source A: a plan.\nSource B: a holdout.", model="offline-fixture")
    sent = json.loads(request["messages"][0]["content"][1]["text"].split("\n\n", 1)[1])
    assert sent["pointer"] == pointer and sent["kind"] == kind
    assert yaml.safe_load(sent["value_yaml"]) == expected_value
    assert sent["specification"] == specification
    assert yaml.safe_load(sent["context"]["containing_entity"]["value_yaml"])["name"] == owner["name"]
    assert request["system"] == nested.SYSTEM != support_judge.SUPPORT_V2_SYSTEM
    assert payload["axis"] == nested.AXIS != support_judge.AXIS
    assert record == before
    assert yaml.safe_load(raw) == before


def test_role_question_keeps_enum_and_caveat_without_accepting_them(real_schema, record):
    _, targets = inventory(record, real_schema)
    role = targets.target("/maintainers/0/role", kind="attribute_value").to_dict()
    assert "academic_institution" in role["specification"]["enums"]["CreatorOrMaintainerEnum"]["permissible_values"]
    assert "responsible for maintaining" in role["specification"]["class_slot_chain"][0]["slot"]["description"]
    assert role["context"]["containing_entity"]["value"]["maintainer_details"] == record["maintainers"][0]["maintainer_details"]
    assert "verdict" not in role
    assert "Context, sibling prose and declarations are claims under test" in nested.SYSTEM
    assert "or treat a caveat as permission" in nested.SYSTEM


def test_same_nested_claim_in_another_entity_or_position_has_distinct_identity(real_schema, record):
    pointer = "/distribution_formats/4/notes"
    _, original = inventory(record, real_schema)
    first = original.target(pointer, kind="attribute_value")
    other_position = original.target("/distribution_formats/5/notes", kind="attribute_value")
    changed = deepcopy(record)
    changed["distribution_formats"][4]["name"] = "Another distribution"
    _, newer = inventory(changed, real_schema)
    other_entity = newer.target(pointer, kind="attribute_value")
    payloads = [target.to_dict() for target in (first, other_position, other_entity)]
    assert len({value["value_sha256"] for value in payloads}) == 1
    assert len({value["context_sha256"] for value in payloads}) == 3
    keys = {nested.request_identity(target, bundle="Source text", model="offline-fixture")
            for target in (first, other_position, other_entity)}
    assert len(keys) == 3
    # Requests expand detached copies; editing one cannot change later identity.
    request = nested.render_request(first, bundle="Source text", model="offline-fixture")
    key = nested.request_identity(first, bundle="Source text", model="offline-fixture")
    request["messages"][0]["content"][1]["text"] = "another entity"
    first.to_dict()["context"]["containing_entity"]["value"]["name"] = "changed copy"
    assert nested.request_identity(first, bundle="Source text", model="offline-fixture") == key


def test_role_edge_and_attributes_have_separate_counts_and_one_fitness_mapping(real_schema):
    _, targets = inventory({"maintainers": [{"name": "Dana Example", "role": "academic_institution"}]}, real_schema)
    assert [(target.pointer, target.kind) for target in targets.targets] == [
        ("/maintainers/0", "relationship_edge"),
        ("/maintainers/0/name", "attribute_value"),
        ("/maintainers/0/role", "attribute_value"),
    ]
    report = targets.to_dict()
    assert report["eligible_by_kind"] == {"relationship_edge": 1, "attribute_value": 2}
    assert report["blocked"] == []
    for target in targets.targets:
        assert target.to_dict()["fitness"] == {
            "basis": "top_level_only", "mapping": "many_to_one", "pointer": "/maintainers"}
    assert "For relationship_edge, judge only whether this entity/reference" in nested.SYSTEM
    assert "do not grade all its\ndescendant attributes again" in nested.SYSTEM
