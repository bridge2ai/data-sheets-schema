"""Neutral offline tests for nested assertion identity, never calibration."""
import copy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.support_targets import (
    AXIS, BLOCKERS, NestedSupportSchema, inventory_targets, pointer_tokens,
    render_request, request_identity, resolve_pointer,
)


@pytest.fixture
def schema_path(tmp_path):
    source = {
        "id": "https://example.test/nested", "name": "nested", "imports": ["linkml:types"],
        "prefixes": {"linkml": "https://w3id.org/linkml/"}, "default_range": "string",
        "classes": {
            "Entity": {"attributes": {n: {"range": "string"} for n in
                         ("id", "name", "notes", "attributed_to", "claim_status", "source_status", "status", "was_derived_from")}},
            "Dataset": {"is_a": "Entity", "description": "A documented dataset.", "attributes": {
                "resources": {"range": "Dataset", "multivalued": True, "inlined_as_list": True},
                "creators": {"range": "Creator", "multivalued": True, "inlined_as_list": True,
                             "description": "The individuals who created this dataset, not merely leadership."},
                "variables": {"range": "Variable", "multivalued": True, "inlined_as_list": True},
                "data_governance": {"range": "Governance", "inlined": True},
                "sensitive_elements": {"range": "Sensitive", "multivalued": True, "inlined_as_list": True},
                "flags": {"range": "boolean", "multivalued": True},
                "count": {"range": "integer"},
                "a/b~c": {"range": "string"},
                "reference": {"range": "Entity", "inlined": False},
                "ambiguous": {"any_of": [{"range": "string"}, {"range": "integer"}]},
                "controlled": {"range": "string", "values_from": ["fixture_terms"]},
            }},
            "Creator": {"is_a": "Entity", "description": "An author of the dataset.",
                        "slot_usage": {"name": {"description": "Full name of the creator, not of the Dataset."}}},
            "Governance": {"is_a": "Entity", "attributes": {
                "committee_contact": {"range": "Entity", "inlined": True,
                                      "description": "Answers questions about access policy and oversight."}}},
            "Sensitive": {"is_a": "Entity", "attributes": {
                "present": {"range": "boolean", "description": "Actual presence, not a plan."}}},
            "Variable": {"is_a": "Entity", "attributes": {
                "variable_name": {"range": "string", "description": "L" * 700 + " Identifier as it appears in data files."}}},
        },
    }
    source["classes"]["Entity"]["attributes"]["id"]["identifier"] = True
    source["classes"]["Entity"]["attributes"].update(
        issued={"range": "date"}, modified={"range": "datetime"})
    source["classes"]["Dataset"]["attributes"]["dates"] = {"range": "date", "multivalued": True}
    path = tmp_path / "schema.yaml"
    path.write_text(yaml.safe_dump(source, sort_keys=False))
    return path


@pytest.fixture
def schema(schema_path):
    return NestedSupportSchema.from_schema(schema_path)


def inventory(document, schema, *, kind="full", **kwargs):
    return inventory_targets(json.dumps(document).encode(), schema, artifact_kind=kind, **kwargs)


def test_mixed_creator_list_has_separate_membership_and_attribute_questions(schema):
    doc = {"id": "dataset:one", "creators": [
        {"name": "Author", "notes": "The source calls this person the creator."},
        {"name": "Leader", "notes": "Leadership only; no creation role stated."}]}
    original = copy.deepcopy(doc)
    result = inventory(doc, schema)
    edges = [t for t in result.targets if t.kind == "relationship_edge"]
    assert [t.pointer for t in edges] == ["/creators/0", "/creators/1"]
    leaf = result.target("/creators/1/name", kind="attribute_value").to_dict()
    assert leaf["specification"]["slot"]["description"] == "Full name of the creator, not of the Dataset."
    assert "not merely leadership" in leaf["specification"]["class_slot_chain"][0]["slot"]["description"]
    assert leaf["context"]["containing_entity"]["pointer"] == "/creators/1"
    assert leaf["context"]["ancestors"][0]["identity"] == {"id": "dataset:one"}
    assert edges[1].to_dict()["context"]["containing_entity"]["pointer"] == ""
    assert result.to_dict()["eligible_by_kind"] == {"relationship_edge": 2, "attribute_value": 5}
    assert leaf["fitness"] == {"basis": "top_level_only", "mapping": "many_to_one", "pointer": "/creators"}
    assert doc == original


def test_resource_creator_is_asserted_of_resource_not_collection(schema):
    result = inventory({"id": "collection:A", "resources": [
        {"id": "dataset:B", "creators": [{"name": "X"}]}]}, schema, kind="collection")
    target = result.target("/resources/0/creators/0", kind="relationship_edge").to_dict()
    context = target["context"]
    assert context["containing_entity"]["pointer"] == "/resources/0"
    assert context["containing_entity"]["value"]["id"] == "dataset:B"
    assert context["ancestors"][0]["identity"]["id"] == "collection:A"
    assert context["collection_metadata_inherited"] is False
    assert target["fitness"]["pointer"] == "/resources"


def test_nested_boolean_and_variable_keep_complete_induced_meaning(schema):
    result = inventory({"sensitive_elements": [{"name": "Sensitive trait", "present": False}],
                        "variables": [{"variable_name": "Broad modality"}], "count": 0}, schema)
    boolean = result.target("/sensitive_elements/0/present", kind="attribute_value").to_dict()
    assert boolean["value"] is False
    assert boolean["context"]["containing_entity"]["value"]["name"] == "Sensitive trait"
    assert boolean["specification"]["slot"]["description"] == "Actual presence, not a plan."
    variable = result.target("/variables/0/variable_name", kind="attribute_value").to_dict()
    assert len(variable["specification"]["slot"]["description"]) > 700
    assert "as it appears in data files" in variable["specification"]["slot"]["description"]
    assert result.target("/count", kind="attribute_value").to_dict()["value"] == 0


def test_governance_relationship_keeps_slot_role_and_anonymous_containing_entity(schema):
    result = inventory({"data_governance": {"notes": "Anonymous committee", "committee_contact": {"name": "A"}}}, schema)
    target = result.target("/data_governance/committee_contact", kind="relationship_edge").to_dict()
    assert target["context"]["containing_entity"]["pointer"] == "/data_governance"
    assert target["specification"]["slot"]["description"].endswith("access policy and oversight.")


@pytest.mark.parametrize("pointer", ["#", "#/x", "x", "/a~2", "/a~", "/flags/-", "/flags/-1", "/flags/01", "/flags/2", "/flags/0/x"])
def test_malformed_or_unresolvable_pointers_refused(pointer):
    with pytest.raises(ValueError):
        resolve_pointer({"flags": [False, True]}, pointer)


def test_escaped_keys_and_scalar_array_items(schema):
    doc = {"a/b~c": "literal", "flags": [False, True]}
    result = inventory(doc, schema)
    assert pointer_tokens("/a~1b~0c") == ["a/b~c"]
    assert resolve_pointer(doc, "/a~1b~0c") == "literal"
    assert result.target("/a~1b~0c", kind="attribute_value").to_dict()["value"] == "literal"
    assert result.target("/flags/0", kind="attribute_value").to_dict()["value"] is False
    with pytest.raises(ValueError):
        result.target("/flags", kind="attribute_value")


def test_unresolved_shapes_are_blocked_not_silently_skipped_or_coerced(schema):
    result = inventory({"unknown": "x", "creators": {"key": {"name": "A"}},
                        "data_governance": "A", "notes": {"text": "x"},
                        "ambiguous": "value", "flags": [None], "controlled": "term"}, schema)
    blocked = {b["pointer"]: b["code"] for b in result.to_dict()["blocked"]}
    assert blocked == {"/unknown": "unknown_schema_slot", "/creators": "unsupported_keyed_map_or_cardinality",
                       "/data_governance": "inline_class_requires_mapping", "/notes": "scalar_slot_has_container",
                       "/ambiguous": "unsupported_schema_constraint_or_polymorphism",
                       "/flags/0": "unpopulated_list_member", "/controlled": "missing_values_from_vocabulary"}
    assert not result.targets
    assert set(result.to_dict()["readiness_blockers"]) == set(BLOCKERS)


def test_reference_is_an_edge_never_dereferenced(schema):
    result = inventory({"reference": "https://example.invalid/entity"}, schema)
    assert [(t.pointer, t.kind) for t in result.targets] == [("/reference", "relationship_edge")]


def test_declared_sources_scoped_to_target_not_unrelated_sibling_or_publication_status(schema):
    result = inventory({"creators": [
        {"name": "A", "attributed_to": "doc-one", "status": "published", "was_derived_from": "urn:work:1"},
        {"name": "B", "attributed_to": "doc-two"}]}, schema)
    first = result.target("/creators/0/name", kind="attribute_value").to_dict()
    assert first["context"]["declarations"] == {"/creators/0/attributed_to": "doc-one"}
    assert "published" in json.dumps(first["context"]["containing_entity"])
    assert "was_derived_from" not in first["context"]["declarations"]


def test_exact_artifact_and_context_bind_request_identity_and_v2_is_distinct(schema):
    from data_sheets_schema.support_judge import AXIS as V2_AXIS, SUPPORT_V2_SYSTEM
    doc = {"notes": "Those rows are under variables."}
    full = inventory(doc, schema).target("/notes", kind="attribute_value")
    core = inventory(doc, schema, kind="core").target("/notes", kind="attribute_value")
    changed = inventory({**doc, "id": "another:entity"}, schema).target("/notes", kind="attribute_value")
    keys = [request_identity(t, bundle="Document one\nA fact.", model="test-model") for t in [full, core, changed]]
    assert len(set(keys)) == 3
    assert AXIS != V2_AXIS
    request = render_request(full, bundle="Document one\nA fact.", model="test-model")
    assert request["system"] != SUPPORT_V2_SYSTEM
    assert "Do not judge unrelated" in request["system"]
    expected = full.to_dict()
    expected.pop("value")
    expected["context"]["containing_entity"].pop("value")
    assert json.loads(request["messages"][0]["content"][1]["text"].split("\n\n", 1)[1]) == expected
    assert request_identity(full, bundle="Different document", model="test-model") != keys[0]
    assert request_identity(full, bundle="Document one\nA fact.", model="other-model") != keys[0]
    request["messages"][0]["content"][1]["text"] = "changed"
    full.to_dict()["context"]["containing_entity"]["value"]["notes"] = "changed"
    assert request_identity(full, bundle="Document one\nA fact.", model="test-model") == keys[0]


def test_schema_snapshot_is_frozen_and_independent_of_later_file_change(schema_path):
    spec = NestedSupportSchema.from_schema(schema_path)
    before = spec.digest
    schema_path.write_text(schema_path.read_text().replace("not merely leadership", "including leadership"))
    newer = NestedSupportSchema.from_schema(schema_path)
    assert spec.digest == before != newer.digest
    target = inventory({"creators": [{"name": "A"}]}, spec).targets[0]
    assert "not merely leadership" in json.dumps(target.to_dict())
    copy_spec = spec.to_dict(); copy_spec["classes"].clear()
    assert spec.to_dict()["classes"]


@pytest.mark.parametrize("raw", [b'{"name":"A", "name":"B"}', b"1: bad\n", b"name: .nan\n", b"name: !!binary SGVsbG8=\n", b"- name: A\n"])
def test_ambiguous_non_json_or_wrong_root_documents_refused(schema, raw):
    with pytest.raises(ValueError):
        inventory_targets(raw, schema, artifact_kind="full")


def test_traversal_limits_and_invalid_requests_refused(schema):
    with pytest.raises(ValueError, match="traversal limits"):
        inventory({"resources": [{"name": "A"}]}, schema, max_nodes=2)
    with pytest.raises(ValueError, match="traversal limits"):
        inventory({"resources": [{"name": "A"}]}, schema, max_depth=1)
    with pytest.raises(ValueError, match="max_input_bytes"):
        inventory({"name": "A"}, schema, max_input_bytes=2)
    with pytest.raises(ValueError, match="max_inventory_bytes"):
        inventory({"name": "A"}, schema, max_inventory_bytes=1)
    target = inventory({"name": "A"}, schema).targets[0]
    for args in ({"bundle": "", "model": "M"}, {"bundle": "x", "model": ""},
                 {"bundle": "x", "model": "M", "max_tokens": True}):
        with pytest.raises(ValueError):
            render_request(target, **args)


def test_public_offline_path_never_initializes_provider_or_opens_network(schema_path, monkeypatch):
    import socket
    from data_sheets_schema.support_judge import SupportJudgeV2
    def forbidden(*args, **kwargs):
        pytest.fail("offline inventory/rendering reached a provider or network")
    monkeypatch.setattr(SupportJudgeV2, "_resolve", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    spec = NestedSupportSchema.from_schema(schema_path)
    targets = inventory({"name": "Neutral record"}, spec)
    render_request(targets.targets[0], bundle="A source document", model="explicit-test-model")


@pytest.mark.parametrize("value", [date(2026, 1, 2), datetime(2026, 1, 2, 3, 4, 5),
    datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=timezone(timedelta(hours=5, minutes=30)))])
def test_native_dates_keep_type_and_exact_input_identity_without_rewriting(schema, tmp_path, value):
    slot = "modified" if isinstance(value, datetime) else "issued"
    doc = {"creators": [{"name": "A", slot: value}], "dates": [date(2026, 1, 2)]}
    raw = yaml.safe_dump(doc, sort_keys=False).encode()
    source = tmp_path / "input.yaml"; source.write_bytes(raw)
    result = inventory_targets(source.read_bytes(), schema, artifact_kind="full")
    target = result.target(f"/creators/0/{slot}", kind="attribute_value")
    payload = target.to_dict()
    assert payload["artifact"]["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert source.read_bytes() == raw
    assert yaml.safe_load(payload["value_yaml"]) == value
    assert type(yaml.safe_load(payload["value_yaml"])) is type(value)
    assert yaml.safe_load(payload["context"]["containing_entity"]["value_yaml"])["name"] == "A"
    assert result.target("/dates/0", kind="attribute_value").to_dict()["value_type"] == "date"
    name_context = result.target("/creators/0/name", kind="attribute_value").to_dict()["context"]
    assert yaml.safe_load(name_context["containing_entity"]["value_yaml"])[slot] == value
    request = render_request(target, bundle="Source", model="test")
    rendered = json.loads(request["messages"][0]["content"][1]["text"].split("\n\n", 1)[1])
    assert yaml.safe_load(rendered["value_yaml"]) == value
    text = inventory({"creators": [{"name": "A", slot: value.isoformat()}]}, schema)
    assert text.target(f"/creators/0/{slot}", kind="attribute_value").to_dict()["value_sha256"] != payload["value_sha256"]


def test_typed_value_hashes_distinguish_date_string_and_tag_shaped_mapping():
    from data_sheets_schema.support_targets import _digest
    day = date(2026, 1, 2)
    values = [day, day.isoformat(), {"$yaml_type": "date", "value": day.isoformat()},
              ["date", day.isoformat()], datetime(2026, 1, 2),
              datetime(2026, 1, 2, tzinfo=timezone.utc), False, 0, 0.0, -0.0]
    assert len({_digest(value) for value in values}) == len(values)
    assert _digest({"a": day, "b": [False]}) == _digest({"b": [False], "a": day})


def test_real_d4d_specs_have_nested_meaning_without_loading_private_records():
    path = Path(__file__).resolve().parents[2] / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
    spec = NestedSupportSchema.from_schema(path)
    result = inventory({"variables": [{"variable_name": "Broad modality"}],
                        "data_governance": {"committee_contact": {"name": "Contact"}}}, spec)
    variable = result.target("/variables/0/variable_name", kind="attribute_value").to_dict()
    assert "as it appears in the data files" in variable["specification"]["slot"]["description"]
    contact = result.target("/data_governance/committee_contact", kind="relationship_edge").to_dict()
    assert "policy, procedure and oversight" in contact["specification"]["slot"]["description"]


def test_context_keeps_qualifiers_but_excludes_unrelated_sibling_containers(schema):
    notes = "Important qualifier. " * 300
    document = {"id": "dataset:one", "notes": notes,
                "creators": [{"name": "A"}, {"name": "B"}],
                "variables": [{"variable_name": "irrelevant-wide-container" * 100}]}
    result = inventory(document, schema)
    target = result.target("/creators/0", kind="relationship_edge").to_dict()
    owner = target["context"]["containing_entity"]
    assert owner["value"] == {"id": "dataset:one", "notes": notes}
    assert owner["omitted_containers"][0]["pointer"] == "/variables"
    assert owner["selected_slot_supplied_as_target"] == "creators"
    assert "context_projection_review_3342" in result.to_dict()["readiness_blockers"]
    prompt = render_request(result.target("/creators/0", kind="relationship_edge"), bundle="source", model="test")
    assert "irrelevant-wide-container" not in json.dumps(prompt)
    assert yaml.safe_load(target["context"]["containing_entity"]["value_yaml"])["notes"] == notes


def test_specs_are_deduplicated_and_only_selected_semantics_expand(schema):
    result = inventory({"creators": [{"name": "A"}, {"name": "B"}]}, schema)
    encoded = result.to_dict()
    edges = [t for t in encoded["targets"] if t["kind"] == "relationship_edge"]
    assert edges[0]["specification_ref"] == edges[1]["specification_ref"]
    assert all("specification" not in t for t in encoded["targets"])
    assert len(encoded["specifications"]) < len(encoded["targets"])
    target = result.target("/creators/0", kind="relationship_edge").to_dict()
    assert "attributes" not in target["specification"]["owning_class"]
    assert "attributes" not in target["specification"]["range_class"]
    assert "variables" not in json.dumps(target["specification"])
    assert "not merely leadership" in json.dumps(target["specification"])


@pytest.mark.corpus
def test_first_public_reference_record_fits_default_inventory_limits_without_rewrites():
    root = Path(__file__).resolve().parents[2]
    source = root / "data/d4d_concatenated/claudecode_agent/2026-09-01_claude-opus-5-api-generic-v7_rep1/AI_READI_d4d.yaml"
    before = source.read_bytes()
    assert hashlib.sha256(before).hexdigest() == "dd656a3a6e8b6bc0f00a50c5d1a5e75c6d2eae8407866c2ba3d2cc3c63b8fdb5"
    spec = NestedSupportSchema.from_schema(root / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
    result = inventory_targets(before, spec, artifact_kind="full")
    encoded = result.to_dict()
    assert all(encoded["eligible_by_kind"][kind] > 0 for kind in ("relationship_edge", "attribute_value"))
    assert len(json.dumps(encoded).encode()) < 64_000_000
    target = result.target("/creators/0", kind="relationship_edge")
    assert len(json.dumps(render_request(target, bundle="source", model="test")).encode()) < 30_000
    assert source.read_bytes() == before


@pytest.mark.parametrize("inheritance", ["is_a", "mixins"])
def test_inherited_class_rules_are_blocked_from_captured_schema(schema_path, inheritance):
    """#4232: the projected ancestor meaning must not erase a rule silently."""
    source = yaml.safe_load(schema_path.read_text())
    source["classes"]["Entity"]["rules"] = [{
        "preconditions": {"slot_conditions": {"claim_status": {"equals_string": "planned"}}},
        "postconditions": {"slot_conditions": {"name": {"equals_string": "planned specimen"}}},
    }]
    if inheritance == "mixins":
        source["classes"]["Entity"]["mixin"] = True
        source["classes"]["Dataset"].pop("is_a")
        source["classes"]["Dataset"]["mixins"] = ["Entity"]
    schema_path.write_text(yaml.safe_dump(source))
    captured = NestedSupportSchema.from_schema(schema_path)
    result = inventory({"name": "observed specimen", "claim_status": "planned"}, captured)
    assert result.to_dict()["blocked"] == [{"pointer": "", "code": "unsupported_class_constraint"}]
    assert not result.targets


@pytest.mark.parametrize("constraint", ["rules", "any_of", "all_of", "exactly_one_of", "none_of"])
def test_inherited_constraint_refusal_matches_every_existing_direct_refusal(schema, constraint):
    payload = schema.to_dict()
    # Exercise the captured representation: interpretation of the conditional
    # expression is deliberately unsupported, irrespective of its contents.
    payload["classes"]["Entity"]["definition"][constraint] = [{"description": "uninterpreted constraint"}]
    result = inventory({"name": "X"}, NestedSupportSchema(json.dumps(payload)))
    assert not result.targets
    assert result.to_dict()["blocked"] == [{"pointer": "", "code": "unsupported_class_constraint"}]


@pytest.mark.parametrize("constrained", [False, True])
def test_constraint_closure_handles_shared_ancestors_and_cycles(schema, constrained):
    payload = schema.to_dict()
    classes = payload["classes"]
    for name in ("Left", "Right"):
        classes[name] = {"definition": {"name": name, "is_a": "Entity"}, "slots": {}}
    classes["Dataset"]["definition"]["mixins"] = ["Left", "Right"]
    # A pre-captured graph can carry a cycle even though capture/schema tooling
    # normally refuses it first. Neither projection nor refusal should loop.
    classes["Entity"]["definition"]["mixins"] = ["Dataset"]
    if constrained:
        classes["Right"]["definition"]["rules"] = [{"description": "uninterpreted constraint"}]
    result = inventory({"name": "X"}, NestedSupportSchema(json.dumps(payload)))
    if constrained:
        assert not result.targets
        assert result.to_dict()["blocked"] == [{"pointer": "", "code": "unsupported_class_constraint"}]
    else:
        assert result.to_dict()["blocked"] == []
        assert result.target("/name", kind="attribute_value").to_dict()["value"] == "X"


def test_direct_constraint_refusal_is_preserved(schema):
    payload = schema.to_dict()
    payload["classes"]["Dataset"]["definition"]["rules"] = [{"description": "uninterpreted constraint"}]
    result = inventory({"name": "X"}, NestedSupportSchema(json.dumps(payload)))
    assert not result.targets
    assert result.to_dict()["blocked"] == [{"pointer": "", "code": "unsupported_class_constraint"}]
