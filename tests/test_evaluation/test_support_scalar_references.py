"""Original-string relationship mechanics; no support labels or calibration."""
import copy
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import support_targets as targets
from tests.test_evaluation.test_support_targets import schema_path, schema  # noqa: F401

POLICY = "relationship_edge_and_attribute_value_inline_class_strings_v1"
INSTRUMENT = "support_targets v3 scalar-reference draft (#4902)"


def inventory(document, specification, *, policy=POLICY, **options):
    raw = json.dumps(document, ensure_ascii=False).encode("utf-8")
    result = targets.inventory_targets(raw, specification, artifact_kind="full",
                                      relationship_policy=policy, **options)
    return raw, result


def request_payload(target):
    request = targets.render_request(target, bundle="Neutral source document.", model="fixture")
    return request, json.loads(request["messages"][0]["content"][1]["text"].split("\n\n", 1)[1])


@pytest.fixture(scope="module")
def real_schema():
    path = Path(__file__).resolve().parents[2] / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
    return targets.NestedSupportSchema.from_schema(path, root_class="Dataset")


@pytest.mark.parametrize("root_slot,many,owner_class,slot", [
    ("creators", True, "Creator", "principal_investigator"),
    ("data_governance", False, "DataGovernance", "committee_contact"),
    ("ethical_reviews", True, "EthicalReview", "contact_person"),
    ("license_and_use_terms", False, "LicenseAndUseTerms", "contact_person"),
    ("regulatory_restrictions", False, "ExportControlRegulatoryRestrictions", "governance_committee_contact"),
])
def test_real_person_slots_keep_original_role_and_mismatch(
        real_schema, root_slot, many, owner_class, slot):
    value = "  Dr. Dana / 李; team ~1\n(coordinator)  "
    owner = {"name": "Neutral owner", "notes": "The source describes a proposed role.", slot: value}
    document = {"id": "dataset:one", root_slot: [owner] if many else owner}
    original = copy.deepcopy(document)
    pointer = "/" + root_slot + ("/0" if many else "") + "/" + slot
    raw, new = inventory(document, real_schema)
    _, strict = inventory(document, real_schema, policy=targets.POLICY)
    assert {"pointer": pointer, "code": "inline_class_requires_mapping"} in strict.to_dict()["blocked"]
    target = new.target(pointer, kind="relationship_edge")
    payload = target.to_dict()
    assert payload["value"] == value
    assert payload["value_type"] == "str"
    assert yaml.safe_load(payload["value_yaml"]) == value
    assert payload["policy"] == POLICY and payload["instrument"] == INSTRUMENT
    assert payload["specification"]["slot"] == real_schema.to_dict()["classes"][owner_class]["slots"][slot]["definition"]
    assert payload["specification"]["slot"]["range"] == "Person"
    context = payload["context"]["containing_entity"]
    assert context["pointer"] == pointer.rsplit("/", 1)[0]
    assert context["class"] == owner_class
    assert context["value"]["name"] == "Neutral owner"
    assert context["value"]["notes"] == owner["notes"]
    assert not any(t.pointer.startswith(pointer + "/") for t in new.targets)
    assert new.to_dict()["eligible_by_kind"]["relationship_edge"] == strict.to_dict()["eligible_by_kind"]["relationship_edge"] + 1
    assert new.to_dict()["eligible_by_kind"]["attribute_value"] == strict.to_dict()["eligible_by_kind"]["attribute_value"]
    request, sent = request_payload(target)
    assert request["system"] != targets.SYSTEM
    assert yaml.safe_load(sent["value_yaml"]) == value
    assert sent["specification"] == payload["specification"]
    assert document == original and json.loads(raw) == original
    assert "verdict" not in payload
    assert payload["representation"] == {
        "status": "schema_invalid_inline_class_string", "expected": "mapping", "observed": "str", "range": "Person"}
    assert sent["representation"] == payload["representation"]
    assert new.to_dict()["representation_issues"] == [{
        "pointer": pointer, "kind": "relationship_edge", "code": "inline_class_requires_mapping", "range": "Person"}]
    assert "representation_issues" not in strict.to_dict()


def test_generic_string_and_existing_mapping_reference_paths_have_one_facet(schema):
    doc = {"creators": ["A and B", {"name": "C"}], "reference": "entity:remote"}
    _, new = inventory(doc, schema)
    _, strict = inventory(doc, schema, policy=targets.POLICY)
    assert [(t.pointer, t.kind) for t in new.targets] == [
        ("/creators/0", "relationship_edge"), ("/creators/1", "relationship_edge"),
        ("/creators/1/name", "attribute_value"), ("/reference", "relationship_edge")]
    assert new.target("/creators/0", kind="relationship_edge").to_dict()["value"] == "A and B"
    for old in strict.targets:
        before = old.to_dict()
        after = new.target(old.pointer, kind=old.kind).to_dict()
        for key in ("value", "value_type", "value_yaml", "value_sha256", "context", "context_sha256",
                    "specification", "specification_ref", "fitness"):
            assert after[key] == before[key]
    assert new.to_dict()["eligible_by_kind"] == {"relationship_edge": 3, "attribute_value": 1}
    assert new.to_dict()["blocked"] == []
    assert new.to_dict()["representation_issues"] == [{
        "pointer": "/creators/0", "kind": "relationship_edge", "code": "inline_class_requires_mapping", "range": "Creator"}]
    assert "representation" not in new.target("/creators/1", kind="relationship_edge").to_dict()
    assert "representation" not in new.target("/reference", kind="relationship_edge").to_dict()


def test_mixed_members_keep_indices_and_nonstring_refusals(schema):
    doc = {"creators": ["A", {"name": "B"}, False, 0, 1.5, None, "", [], {}]}
    _, new = inventory(doc, schema)
    assert [(t.pointer, t.kind) for t in new.targets] == [
        ("/creators/0", "relationship_edge"), ("/creators/1", "relationship_edge"),
        ("/creators/1/name", "attribute_value")]
    assert new.to_dict()["blocked"] == [
        *[{"pointer": f"/creators/{i}", "code": "inline_class_requires_mapping"} for i in (2, 3, 4)],
        *[{"pointer": f"/creators/{i}", "code": "unpopulated_list_member"} for i in (5, 6, 7, 8)],
    ]


@pytest.mark.parametrize("document,expected", [
    ({"creators": "A"}, [{"pointer": "/creators", "code": "unsupported_keyed_map_or_cardinality"}]),
    ({"creators": {"key": "A"}}, [{"pointer": "/creators", "code": "unsupported_keyed_map_or_cardinality"}]),
    ({"data_governance": ["A"]}, [{"pointer": "/data_governance", "code": "unsupported_keyed_map_or_cardinality"}]),
    ({"data_governance": False}, [{"pointer": "/data_governance", "code": "inline_class_requires_mapping"}]),
    ({"data_governance": 0}, [{"pointer": "/data_governance", "code": "inline_class_requires_mapping"}]),
    ({"data_governance": None}, []),
    ({"data_governance": ""}, []),
    ({"unknown": "A"}, [{"pointer": "/unknown", "code": "unknown_schema_slot"}]),
])
def test_shape_admission_does_not_coerce_other_values(schema, document, expected):
    _, result = inventory(document, schema)
    assert not result.targets
    assert result.to_dict()["blocked"] == expected


@pytest.mark.parametrize("inheritance", ["direct", "parent", "mixin"])
def test_new_scalar_range_gate_keeps_existing_mapped_edge_behavior(schema, inheritance):
    captured = schema.to_dict()
    classes = captured["classes"]
    restricted = classes["Creator"]["definition"]
    if inheritance != "direct":
        classes["RestrictedParent"] = {"definition": {"name": "RestrictedParent"}, "slots": {}}
        restricted = classes["RestrictedParent"]["definition"]
        if inheritance == "parent":
            classes["Creator"]["definition"]["is_a"] = "RestrictedParent"
        else:
            restricted["mixin"] = True
            classes["Creator"]["definition"]["mixins"] = ["RestrictedParent"]
    restricted["rules"] = [{"description": "Uninterpreted rule remains a blocker."}]
    spec = targets.NestedSupportSchema(json.dumps(captured))
    doc = {"creators": ["A", {"name": "B"}]}
    _, new = inventory(doc, spec)
    _, strict = inventory(doc, spec, policy=targets.POLICY)
    assert [(t.pointer, t.kind) for t in new.targets] == [("/creators/1", "relationship_edge")]
    assert {"pointer": "/creators/0", "code": "unsupported_class_constraint"} in new.to_dict()["blocked"]
    assert {"pointer": "/creators/1", "code": "unsupported_class_constraint"} in new.to_dict()["blocked"]
    assert strict.target("/creators/1", kind="relationship_edge").to_dict()["value"] == {"name": "B"}


@pytest.mark.parametrize("mode", ["owner_rule", "slot_rule", "missing_vocabulary"])
def test_existing_owner_slot_and_vocabulary_gates_precede_scalar_admission(schema, mode):
    captured = schema.to_dict()
    slot = captured["classes"]["Dataset"]["slots"]["creators"]["definition"]
    if mode == "owner_rule":
        captured["classes"]["Dataset"]["definition"]["rules"] = [{"description": "Unsupported"}]
        expected = [{"pointer": "", "code": "unsupported_class_constraint"}]
    elif mode == "slot_rule":
        slot["any_of"] = [{"range": "Creator"}, {"range": "string"}]
        expected = [{"pointer": "/creators", "code": "unsupported_schema_constraint_or_polymorphism"}]
    else:
        slot["values_from"] = ["absent_registry"]
        expected = [{"pointer": "/creators", "code": "missing_values_from_vocabulary"}]
    _, result = inventory({"creators": ["A"]}, targets.NestedSupportSchema(json.dumps(captured)))
    assert not result.targets and result.to_dict()["blocked"] == expected


def test_same_string_nearest_owner_escaped_pointer_and_fresh_results(schema):
    captured = schema.to_dict()
    slot = copy.deepcopy(captured["classes"]["Dataset"]["slots"]["creators"])
    slot["definition"]["name"] = "a/b~c"
    captured["classes"]["Dataset"]["slots"]["a/b~c"] = slot
    spec = targets.NestedSupportSchema(json.dumps(captured))
    doc = {"id": "collection:one", "resources": [
        {"id": "dataset:A", "a/b~c": ["Same", "Same"]},
        {"id": "dataset:B", "a/b~c": ["Same"]}]}
    _, result = inventory(doc, spec)
    pointers = ["/resources/0/a~1b~0c/0", "/resources/0/a~1b~0c/1", "/resources/1/a~1b~0c/0"]
    selected = [result.target(p, kind="relationship_edge") for p in pointers]
    assert {t.to_dict()["value_sha256"] for t in selected} == {selected[0].to_dict()["value_sha256"]}
    assert len({targets.request_identity(t, bundle="source", model="fixture") for t in selected}) == 3
    for t, expected in zip(selected, ["dataset:A", "dataset:A", "dataset:B"]):
        payload = t.to_dict()
        assert targets.resolve_pointer(doc, t.pointer) == "Same"
        assert payload["context"]["containing_entity"]["value"]["id"] == expected
        assert payload["context"]["ancestors"][0]["identity"]["id"] == "collection:one"
    original = selected[0].to_dict()
    selected[0].to_dict()["context"]["containing_entity"]["value"]["id"] = "tampered copy"
    assert selected[0].to_dict() == original
    doc["resources"][0]["id"] = "dataset:C"
    _, changed = inventory(doc, spec)
    assert changed.target(pointers[0], kind="relationship_edge").to_dict()["context_sha256"] != original["context_sha256"]


def test_omitted_and_explicit_strict_are_identical_and_unknown_policy_refuses(schema):
    raw = b'{"creators":["A", {"name":"B"}],"count":0}'
    default = targets.inventory_targets(raw, schema, artifact_kind="full")
    strict = targets.inventory_targets(raw, schema, artifact_kind="full", relationship_policy=targets.POLICY)
    assert default.to_dict() == strict.to_dict()
    assert [t.payload_json for t in default.targets] == [t.payload_json for t in strict.targets]
    for a, b in zip(default.targets, strict.targets):
        assert targets.render_request(a, bundle="source", model="fixture") == targets.render_request(b, bundle="source", model="fixture")
    with pytest.raises(ValueError, match="policy"):
        targets.inventory_targets(raw, schema, artifact_kind="full", relationship_policy="unknown")


@pytest.mark.parametrize("limits", [{"max_nodes": 1}, {"max_depth": 1}, {"max_input_bytes": 1}, {"max_inventory_bytes": 1}])
def test_new_policy_retains_existing_atomic_resource_limits(schema, limits):
    with pytest.raises(ValueError):
        inventory({"resources": [{"creators": ["A"]}]}, schema, **limits)


@pytest.mark.parametrize("case_name", ["ordinary", "mixed_inline_string"])
@pytest.mark.parametrize("explicit", [False, True])
def test_strict_bytes_match_actual_prechange_capture(case_name, explicit):
    """The expected strings were copied before implementation, not regenerated."""
    from data_sheets_schema import evidence_score, support_plan
    path = Path(__file__).parents[1] / "fixtures/support_strict_v2/semantic.json"
    golden = json.loads(path.read_bytes())
    assert golden["source_commit"] == "f2c050c1833c9a5c54c4373a02f6230578a27fe4"
    assert golden["original_receipt_sha256"] == "40301a379129047d8e0b9b496d8ba505cbd6b80f29a7b84b7670f74f968f3284"
    common = golden["common"]
    case = next(c for c in golden["cases"] if c["name"] == case_name)
    specification = targets.NestedSupportSchema(common["captured_specification_json"])
    options = {"relationship_policy": targets.POLICY} if explicit else {}
    actual = targets.inventory_targets(case["record_yaml"].encode(), specification, artifact_kind="full", **options)
    assert support_plan.canonical(actual.to_dict()) == case["inventory_json"].encode()
    assert len(actual.targets) == len(case["targets"])
    for current, old in zip(actual.targets, case["targets"]):
        assert current.payload_json.encode() == old["payload_json"].encode()
        assert current.specification_json.encode() == old["specification_json"].encode()
    document = yaml.safe_load(case["record_yaml"])
    fitness_specs = json.loads(common["fitness_specifications_json"])["slots"]
    for old in case["requests"]:
        if old["axis"] == targets.AXIS:
            kind = old["target_id"].split(":", 3)[2]
            current = targets.render_request(actual.target(old["pointer"], kind=kind),
                bundle=common["bundle"], model=common["model"], max_tokens=common["max_tokens"])
        else:
            slot = targets.pointer_tokens(old["pointer"])[0]
            current = evidence_score.fitness_request_arguments(model=common["model"],
                max_tokens=common["max_tokens"], slot=slot, value=document[slot], specification=fitness_specs[slot])
        assert support_plan.canonical(current) == old["request_json"].encode()
