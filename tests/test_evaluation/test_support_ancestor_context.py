"""Ancestor context mechanics, with neutral claims and no scientific labels."""
import copy
from datetime import date, datetime, timezone
import json

import pytest
import yaml

from data_sheets_schema import support_targets as targets
from tests.test_evaluation.test_support_targets import schema_path  # noqa: F401

LEGACY = "nearest_owner_and_ancestor_identity_v1"
ANCESTORS = "ancestor_scalar_qualifiers_v1"
SCALAR = "relationship_edge_and_attribute_value_inline_class_strings_v1"


@pytest.fixture
def ancestor_schema(schema_path):
    source = yaml.safe_load(schema_path.read_bytes())
    creator = source["classes"]["Creator"].setdefault("attributes", {})
    creator.update({
        "affiliations": {"range": "Organization", "multivalued": True, "inlined_as_list": True},
        "aff/il~iation": {"range": "Organization", "multivalued": True, "inlined_as_list": True},
        "source_caveats": {"range": "string"},
    })
    source["classes"]["Organization"] = {"is_a": "Entity"}
    schema_path.write_text(yaml.safe_dump(source, sort_keys=False))
    return targets.NestedSupportSchema.from_schema(schema_path)


def inventory(document, schema, *, relationship=targets.POLICY, context=ANCESTORS, **limits):
    return targets.inventory_targets(yaml.safe_dump(document, sort_keys=True).encode(), schema,
        artifact_kind="full", relationship_policy=relationship, context_policy=context, **limits)


def rendered(target):
    request = targets.render_request(target, bundle="Document A: invented neutral evidence.\n"
        "Document B: another invented neutral source.", model="fixture")
    return request, json.loads(request["messages"][0]["content"][1]["text"].split("\n\n", 1)[1])


@pytest.mark.parametrize("relationship", [targets.POLICY, SCALAR])
def test_ancestor_attribution_is_actual_rendered_text_not_just_a_hash(ancestor_schema, relationship):
    document = {"id": "collection:neutral", "creators": [{
        "name": "Dana", "source_caveats": "This organization name is attributed to Document A.",
        "attributed_to": "Document A", "affiliations": [{"name": "Harbor Institute"}]}]}
    pointer = "/creators/0/affiliations/0/name"
    old = inventory(document, ancestor_schema, relationship=relationship, context=LEGACY)
    new = inventory(document, ancestor_schema, relationship=relationship)
    old_target, new_target = old.target(pointer, kind="attribute_value"), new.target(pointer, kind="attribute_value")
    before, after = old_target.to_dict(), new_target.to_dict()
    for key in ("value", "value_sha256", "value_yaml", "specification", "specification_ref", "fitness"):
        assert after[key] == before[key]
    old_request, old_sent = rendered(old_target)
    new_request, sent = rendered(new_target)
    assert "source_caveats" not in old_sent["context"]["ancestors"][1].get("identity", {})
    ancestor = sent["context"]["ancestors"][1]
    assert ancestor["pointer"] == "/creators/0" and ancestor["class"] == "Creator"
    assert yaml.safe_load(ancestor["value_yaml"])["source_caveats"] == document["creators"][0]["source_caveats"]
    assert ancestor["field_origins"]["source_caveats"] == "/creators/0/source_caveats"
    assert "value" not in ancestor  # the full YAML is sent once, not a second JSON preview
    assert "value" in after["context"]["ancestors"][1]
    assert sent["context"]["declarations"] == before["context"]["declarations"] == {}
    assert sent["context"]["collection_metadata_inherited"] is False
    assert old_request["system"] != new_request["system"]
    changed = copy.deepcopy(document)
    changed["creators"][0]["source_caveats"] = "This organization name is attributed to Document B."
    changed["creators"][0]["attributed_to"] = "Document B"
    other = inventory(changed, ancestor_schema, relationship=relationship).target(pointer, kind="attribute_value")
    _, other_sent = rendered(other)
    assert "Document B" in other_sent["context"]["ancestors"][1]["value_yaml"]
    assert other.to_dict()["value_sha256"] == after["value_sha256"]
    assert other.to_dict()["specification_ref"] == after["specification_ref"]
    assert targets.request_identity(other, bundle="same source", model="fixture") != targets.request_identity(
        new_target, bundle="same source", model="fixture")


def test_deep_escaped_path_excludes_sibling_values_and_keeps_exact_origins(ancestor_schema):
    selected = {"name": "Chosen", "attributed_to": "Direct owner source", "notes": "Direct owner qualifier"}
    creator = {"name": "Dana", "notes": "Creator qualifier", "attributed_to": "Ancestor source",
               "aff/il~iation": [selected, {"name": "SIBLING ORGANIZATION SECRET"}]}
    resource = {"id": "resource:one", "notes": "Resource qualifier", "creators": [
        creator, {"name": "SIBLING CREATOR SECRET", "notes": "SIBLING CAVEAT SECRET"}]}
    document = {"id": "collection:one", "notes": "Collection qualifier", "resources": [resource],
                "variables": [{"variable_name": "UNRELATED CONTAINER SECRET"}]}
    pointer = "/resources/0/creators/0/aff~1il~0iation/0/name"
    result = inventory(document, ancestor_schema)
    target = result.target(pointer, kind="attribute_value")
    payload = target.to_dict()
    ancestors = payload["context"]["ancestors"]
    assert [r["pointer"] for r in ancestors] == ["", "/resources/0", "/resources/0/creators/0"]
    assert [r["class"] for r in ancestors] == ["Dataset", "Dataset", "Creator"]
    for row, source, branch, child in zip(ancestors,
            [document, resource, creator], ["resources", "creators", "aff/il~iation"],
            ["/resources/0", "/resources/0/creators/0", "/resources/0/creators/0/aff~1il~0iation/0"]):
        branch_pointer = row["pointer"] + "/" + targets._token(branch)
        assert row["source_mapping_sha256"] == targets._digest(source)
        assert row["value_sha256"] == targets._digest(yaml.safe_load(row["value_yaml"]))
        assert branch not in row["value"]
        assert row["path_branch"] == {"pointer": branch_pointer, "selected_entity_pointer": child,
            "sha256": targets._digest(source[branch]), "size": len(source[branch]),
            "reason": "selected_path_branch_represented_separately"}
        assert row["field_origins"] == {name: row["pointer"] + "/" + targets._token(name)
                                       for name in row["value"]}
    assert ancestors[0]["omitted_containers"] == [{"pointer": "/variables",
        "sha256": targets._digest(document["variables"]), "size": 1,
        "reason": "other_container_not_selected_assertion"}]
    direct = payload["context"]["containing_entity"]
    assert direct["pointer"] == "/resources/0/creators/0/aff~1il~0iation/0"
    assert direct["value"]["notes"] == "Direct owner qualifier"
    assert "name" not in direct["value"]
    assert payload["context"]["declarations"] == {
        "/resources/0/creators/0/aff~1il~0iation/0/attributed_to": "Direct owner source"}
    _, sent = rendered(target)
    sent_text = json.dumps(sent, ensure_ascii=False)
    for secret in ("SIBLING ORGANIZATION SECRET", "SIBLING CREATOR SECRET", "SIBLING CAVEAT SECRET",
                   "UNRELATED CONTAINER SECRET"):
        assert secret not in sent_text
    original = target.payload_json
    payload["context"]["ancestors"][0]["value"]["notes"] = "Detached edit"
    assert target.payload_json == original and target.to_dict()["context"]["ancestors"][0]["value"]["notes"] == "Collection qualifier"


def test_complete_typed_scalars_and_explicit_container_qualifiers_are_retained(ancestor_schema):
    day = date(2024, 2, 3)
    instant = datetime(2024, 2, 3, 4, 5, 6, tzinfo=timezone.utc)
    caveat = {"documents": ["A", "B"], "claims": {"status": "unreviewed"}}
    document = {"id": {"malformed": "IDENTITY CONTAINER SECRET"}, "count": 0, "enabled": False,
        "nothing": None, "issued": day, "modified": instant, "dates": [day],
        "flags": [False, True], "a/b~c": "Escaped scalar field", "source_caveats": caveat,
        "resources": [{"id": "resource:one", "creators": [{"name": "Dana"}]}]}
    target = inventory(document, ancestor_schema).target("/resources/0/creators/0/name", kind="attribute_value")
    ancestor = target.to_dict()["context"]["ancestors"][0]
    kept = yaml.safe_load(ancestor["value_yaml"])
    assert kept == {k: v for k, v in document.items() if k not in ("id", "resources")}
    assert kept["count"] == 0 and type(kept["count"]) is int
    assert kept["enabled"] is False and kept["nothing"] is None
    assert type(kept["issued"]) is date and type(kept["modified"]) is datetime
    assert ancestor["value_sha256"] == targets._digest(kept)
    assert ancestor["field_origins"]["a/b~c"] == "/a~1b~0c"
    assert ancestor["omitted_containers"] == [{"pointer": "/id", "sha256": targets._digest(document["id"]),
        "size": 1, "reason": "other_container_not_selected_assertion"}]
    assert caveat == kept["source_caveats"]
    assert target.to_dict()["context"]["declarations"] == {}


@pytest.mark.parametrize("relationship", [targets.POLICY, SCALAR])
@pytest.mark.parametrize("context", [LEGACY, ANCESTORS])
def test_four_contracts_preserve_membership_values_specs_and_representation(ancestor_schema, relationship, context):
    document = {"title": "Neutral collection", "creators": [
        {"name": "Dana", "source_caveats": "Document A", "affiliations": [{"name": "Organization"}]},
        "Original composite role"]}
    old = inventory(document, ancestor_schema, relationship=relationship, context=LEGACY)
    current = inventory(document, ancestor_schema, relationship=relationship, context=context)
    assert [(t.pointer, t.kind) for t in current.targets] == [(t.pointer, t.kind) for t in old.targets]
    assert current.to_dict()["blocked"] == old.to_dict()["blocked"]
    for before, after in zip(old.targets, current.targets):
        a, b = before.to_dict(), after.to_dict()
        for key in ("value", "value_type", "value_yaml", "value_sha256", "specification_ref", "specification", "fitness"):
            assert a[key] == b[key]
        assert a.get("representation") == b.get("representation")
        if context == LEGACY:
            assert before.payload_json == after.payload_json
            assert rendered(before) == rendered(after)
            assert "context_policy" not in b
        else:
            assert b["context_policy"] == b["context"]["context_policy"] == ANCESTORS
            assert b["context_sha256"] != a["context_sha256"]
            assert b["instrument"] != a["instrument"]
    assert current.to_dict().get("representation_issues") == old.to_dict().get("representation_issues")
    assert current.to_dict().get("context_policy") == (ANCESTORS if context == ANCESTORS else None)
    if relationship == SCALAR:
        assert not any(t.pointer.startswith("/creators/1/") for t in current.targets)


@pytest.mark.parametrize("relationship", [targets.POLICY, SCALAR])
def test_omitted_and_explicit_legacy_context_are_byte_identical(ancestor_schema, relationship):
    raw = b'{"creators":[{"name":"Dana"},"Original string"],"count":0}'
    a = targets.inventory_targets(raw, ancestor_schema, artifact_kind="full", relationship_policy=relationship)
    b = targets.inventory_targets(raw, ancestor_schema, artifact_kind="full", relationship_policy=relationship,
                                  context_policy=LEGACY)
    assert a.to_dict() == b.to_dict()
    assert [(t.payload_json, t.specification_json) for t in a.targets] == [(t.payload_json, t.specification_json) for t in b.targets]
    assert [rendered(t) for t in a.targets] == [rendered(t) for t in b.targets]


@pytest.mark.parametrize("context", [None, False, 1, "", "unknown-context"])
def test_unknown_context_does_not_silently_choose_a_contract(ancestor_schema, context):
    with pytest.raises(ValueError, match="context|policy"):
        inventory({"creators": [{"name": "Dana"}]}, ancestor_schema, context=context)


def test_ancestor_expansion_uses_existing_atomic_inventory_bound(ancestor_schema):
    document = {"notes": "Full original qualifier. " * 400,
        "resources": [{"creators": [{"affiliations": [{"name": "Organization"}]}]}]}
    old = inventory(document, ancestor_schema, context=LEGACY)
    specifications = {t.specification_json for t in old.targets}
    budget = sum(len(t.payload_json.encode()) for t in old.targets) + sum(len(s.encode()) for s in specifications) + 2000
    assert inventory(document, ancestor_schema, context=LEGACY, max_inventory_bytes=budget).targets
    with pytest.raises(ValueError, match="max_inventory_bytes.*no partial"):
        inventory(document, ancestor_schema, max_inventory_bytes=budget)
    complete = inventory(document, ancestor_schema)
    leaf = complete.target("/resources/0/creators/0/affiliations/0/name", kind="attribute_value").to_dict()
    assert yaml.safe_load(leaf["context"]["ancestors"][0]["value_yaml"])["notes"] == document["notes"]
