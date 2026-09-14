"""Nested vocabulary constraints reach the actual judge and its cache (#1469)."""

import json
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner, evidence_score, form_defects, schema_digest
from data_sheets_schema.profiles import BRIDGE2AI, NEUTRAL, Profile


@pytest.fixture
def calls(monkeypatch):
    requests = []

    def fake(client, **kwargs):
        requests.append(kwargs["messages"][0]["content"])
        reply = ('{"subtype": "other", "reason": "offline"}'
                 if kwargs["system"] == form_defects.FORM_SUBTYPE_SYSTEM
                 else '{"fitness": 1, "reason": "offline"}')
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=reply)],
            stop_reason="end_turn", usage=None)

    monkeypatch.setattr(api_runner, "_call_with_retry", fake)
    return requests


@pytest.mark.parametrize("profile", [NEUTRAL, BRIDGE2AI], ids=lambda p: p.name)
def test_resources_request_includes_instance_scope_under_selected_profile(profile, calls):
    scorer = evidence_score.LLMSlotFitnessScorer(
        client=object(), model="offline", profile=profile)
    scorer(project="example", slot="resources",
           value=[{"instances": [{"data_topic": "MeSH:D012345"}]}])
    spec = calls[0].split("Value supplied:")[0]
    assert "On each `Instance` object, `data_topic` must be drawn from a term from GO, MeSH" in spec
    assert ("B2AI_TOPIC" in spec) == (profile == BRIDGE2AI)
    assert spec.count("On each `Instance` object, `data_topic`") == 1


def test_form_subtype_request_uses_the_same_nested_scope(calls):
    classifier = form_defects.FormSubtypeClassifier(
        client=object(), model="offline", profile=NEUTRAL)
    failure = form_defects.FormFailure(
        project="example", slot="resources", value="[]", reason="wrong vocabulary",
        fitness=0, schema=classifier.schema, specification=classifier.specification)
    assert classifier(failure) == ("other", "offline")
    assert "On each `Instance` object, `data_topic` must be drawn from a term from GO, MeSH" in calls[0]
    assert "B2AI_TOPIC" not in calls[0]


@pytest.fixture
def nested_schema(tmp_path):
    # Leaf is deeper than the generation digest; Branch -> Node closes a cycle.
    # References and the unrelated Dataset field must not leak into `subject`.
    doc = {
        "id": "https://example.org/nested-fitness", "name": "nested_fitness",
        "default_range": "string",
        "classes": {
            "Dataset": {"attributes": {
                "subject": {"range": "Node", "inlined": True},
                "elsewhere": {"range": "Unrelated"},
                "reference_elsewhere": {"range": "Reference", "inlined": True},
                "reference": {"range": "Reference"}}},
            "Node": {"attributes": {
                "id": {"identifier": True},
                "branches": {"range": "Branch", "multivalued": True},
                "reference": {"range": "Reference"}}},
            "Branch": {"attributes": {
                "leaf": {"range": "Leaf"},
                "parent": {"range": "Node", "inlined": True}}},
            "Leaf": {"attributes": {
                "term": {"values_from": ["TEST"],
                         "annotations": {"d4d:termSources": "OntologyOne"}}}},
            "Unrelated": {"attributes": {
                "term": {"annotations": {"d4d:termSources": "UnrelatedOnly"}}}},
            "Reference": {"attributes": {
                "id": {"identifier": True},
                "term": {"annotations": {"d4d:termSources": "ReferenceOnly"}}}},
        },
    }
    path = tmp_path / "schema.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    pin = tmp_path / "vocabulary.yaml"
    pin.write_text("vocabularies:\n  TEST:\n    TEST:1: alpha\n")
    return path, doc, pin, Profile(name="example", vocabulary_pin=pin)


def test_deep_implicit_objects_cycles_and_reference_boundaries(nested_schema):
    path, _, _, profile = nested_schema
    before = schema_digest.digest_text("Dataset", path, profile=profile)
    spec = evidence_score.slot_spec("subject", schema_path=path, profile=profile)
    assert "OntologyOne" not in before  # Beyond the generation digest's two levels.
    assert spec.count("On each `Leaf` object, `term`") == 1
    assert "OntologyOne" in spec and "1=alpha" in spec
    assert "ReferenceOnly" not in spec and "UnrelatedOnly" not in spec
    reference = evidence_score.slot_spec("reference", schema_path=path, profile=profile)
    assert "ReferenceOnly" not in reference and "requires:" not in reference
    assert schema_digest.digest_text("Dataset", path, profile=profile) == before
    assert evidence_score.slot_spec("subject", schema_path=path, profile=profile) == spec


def test_direct_vocabulary_slot_uses_the_same_scope(nested_schema):
    path, _, _, profile = nested_schema
    spec = evidence_score.slot_spec("term", "Leaf", path, profile=profile)
    assert "`term` must be drawn from a term from OntologyOne" in spec
    assert "1=alpha" in spec


@pytest.mark.parametrize("change", ["schema", "vocabulary"])
def test_deep_edit_rejects_old_cache_without_changing_generation(nested_schema, tmp_path, calls, change):
    path, doc, pin, profile = nested_schema
    cache = tmp_path / "fitness.jsonl"

    def new_scorer():
        return evidence_score.LLMSlotFitnessScorer(
            client=object(), model="offline", schema_path=path,
            profile=profile, cache_path=cache)

    def rate(scorer):
        scorer(project="example", slot="subject",
               value={"branches": [{"leaf": {"term": "TEST:1"}}]})

    first = new_scorer()
    before = first._context("offline")
    rate(first)
    old = cache.read_bytes()
    if change == "schema":
        doc["classes"]["Leaf"]["attributes"]["term"]["annotations"]["d4d:termSources"] = "OntologyTwo"
        path.write_text(yaml.safe_dump(doc, sort_keys=False))
    else:
        pin.write_text(pin.read_text().replace("alpha", "omega"))
    second = new_scorer()
    after = second._context("offline")
    assert before.schema == after.schema
    assert before.specification != after.specification
    rate(second)
    assert second.cache_skipped == {"specification": 1}
    assert len(calls) == 2
    assert ("OntologyTwo" if change == "schema" else "1=omega") in calls[1]
    assert ("OntologyOne" if change == "schema" else "1=alpha") not in calls[1]
    assert cache.read_bytes().startswith(old)
    entries = [json.loads(line) for line in cache.read_text().splitlines()]
    assert [entry["specification"] for entry in entries] == [before.specification, after.specification]
    rate(first)  # A long-lived scorer also leaves its old in-memory judgement behind.
    assert len(calls) == 2  # The fresh persisted judgement is reusable.


def test_deep_edit_during_call_uses_one_captured_schema(nested_schema, tmp_path, monkeypatch, calls):
    path, doc, _, profile = nested_schema
    cache = tmp_path / "fitness.jsonl"
    scorer = evidence_score.LLMSlotFitnessScorer(
        client=object(), model="offline", schema_path=path, profile=profile, cache_path=cache)
    before = scorer._context("offline")
    load = scorer._load_cache

    def edit_after_snapshot(ctx):
        load(ctx)
        doc["classes"]["Leaf"]["attributes"]["term"]["annotations"]["d4d:termSources"] = "OntologyTwo"
        path.write_text(yaml.safe_dump(doc, sort_keys=False))

    monkeypatch.setattr(scorer, "_load_cache", edit_after_snapshot)
    scorer(project="example", slot="subject", value={})
    assert "OntologyOne" in calls[0] and "OntologyTwo" not in calls[0]
    assert json.loads(cache.read_text())["specification"] == before.specification
    scorer(project="example", slot="subject", value={})
    assert "OntologyTwo" in calls[1] and "OntologyOne" not in calls[1]


def test_complete_inventory_cache_is_not_exposed(nested_schema):
    path, _, _, profile = nested_schema
    before = evidence_score.slot_spec("subject", schema_path=path, profile=profile)
    generation, complete = schema_digest.build_for_judgement("Dataset", path)
    generation.slots.clear()
    complete.slots.clear()
    for nested in complete.nested:
        nested.inlined_ranges.clear()
        nested.term_sources.clear()
    assert evidence_score.slot_spec("subject", schema_path=path, profile=profile) == before


def test_edit_between_generation_and_complete_inventory_uses_one_snapshot(nested_schema, monkeypatch, calls):
    path, doc, _, profile = nested_schema
    build_generation = schema_digest._build_cached

    def edit_after_generation(*args, **kwargs):
        result = build_generation(*args, **kwargs)
        doc["classes"]["Leaf"]["attributes"]["term"]["annotations"]["d4d:termSources"] = "OntologyTwo"
        path.write_text(yaml.safe_dump(doc, sort_keys=False))
        return result

    monkeypatch.setattr(schema_digest, "_build_cached", edit_after_generation)
    scorer = evidence_score.LLMSlotFitnessScorer(
        client=object(), model="offline", schema_path=path, profile=profile)
    scorer(project="example", slot="subject", value={})
    assert "OntologyOne" in calls[0] and "OntologyTwo" not in calls[0]
    scorer(project="example", slot="subject", value={})
    assert "OntologyTwo" in calls[1] and "OntologyOne" not in calls[1]
