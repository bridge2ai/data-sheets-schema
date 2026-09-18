"""Subtype labels use the fitness target class and complete specification (#2090)."""

import json
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner, schema_digest
from data_sheets_schema.evidence_score import (
    LLMSlotFitnessScorer,
    _render_slot_spec,
    slot_specification_snapshot,
)
from data_sheets_schema.form_defects import FormFailure, FormSubtypeClassifier
from data_sheets_schema.profiles import NEUTRAL, Profile


@pytest.fixture
def transport(monkeypatch):
    clients, calls = [], []

    def client():
        clients.append(True)
        return object()

    def call(client, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(
            type="text", text='{"subtype":"other","reason":"offline"}')])

    monkeypatch.setattr(api_runner, "_client", client)
    monkeypatch.setattr(api_runner, "_call_with_retry", call)
    return clients, calls


def form_failure(snapshot, *, slot="description", value='"example"'):
    return FormFailure("example", slot, value, "wrong form", 0,
                       schema=snapshot[0], specification=snapshot[3])


@pytest.mark.parametrize("class_name", ["Dataset", "CoreDataset"])
def test_fresh_label_matches_fitness_class_and_attests_actual_prompt(
        tmp_path, transport, class_name):
    clients, calls = transport
    expected = slot_specification_snapshot(class_name, profile=NEUTRAL)
    context = LLMSlotFitnessScorer(
        class_name=class_name, profile=NEUTRAL)._context("offline")
    cache = tmp_path / "subtypes.jsonl"
    # Exercise the unchanged default call as well as explicit CoreDataset.
    kwargs = {} if class_name == "Dataset" else {"class_name": class_name}
    classifier = FormSubtypeClassifier(
        model="offline", profile=NEUTRAL, cache_path=cache, **kwargs)

    assert classifier(form_failure(expected)) == ("other", "offline")
    assert len(clients) == len(calls) == classifier.calls == 1
    assert classifier.schema == context.schema == expected[0]
    assert classifier.specification == context.specification == expected[3]
    prompt = calls[0]["messages"][0]["content"]
    assert prompt.startswith(_render_slot_spec("description", expected[1], expected[2]) + "\n\n")
    row = json.loads(cache.read_text())
    assert (row["schema"], row["specification"]) == (context.schema, context.specification)


@pytest.mark.parametrize("explicit_core_identity", [False, True])
def test_dataset_classifier_cannot_fill_a_core_failure(
        tmp_path, transport, explicit_core_identity):
    clients, calls = transport
    core = slot_specification_snapshot("CoreDataset", profile=NEUTRAL)
    kwargs = {"schema": core[0], "specification": core[3]} if explicit_core_identity else {}
    cache = tmp_path / "subtypes.jsonl"
    classifier = FormSubtypeClassifier(
        model="offline", profile=NEUTRAL, cache_path=cache, **kwargs)

    with pytest.raises(ValueError, match="fresh cache|different instruments"):
        classifier(form_failure(core))
    assert calls == clients == []
    assert not cache.exists()


@pytest.fixture
def custom_instrument(tmp_path):
    path = tmp_path / "schema.yaml"
    path.write_text(
        "id: https://example.org/custom-subtype\nname: custom_subtype\n"
        "default_range: string\nclasses:\n"
        "  Dataset:\n    attributes:\n      subject:\n"
        "        description: Dataset-only instruction.\n"
        "  CoreDataset:\n    attributes:\n      subject:\n"
        "        description: Custom core instruction.\n"
        "        range: Topic\n        inlined: true\n"
        "  Topic:\n    attributes:\n      term:\n        values_from: [TEST]\n")
    pin = tmp_path / "vocabulary.yaml"
    pin.write_text("vocabularies:\n  TEST:\n    TEST:1: selected-profile-term\n")
    return path, Profile(name="custom", vocabulary_pin=pin)


def test_custom_schema_and_profile_reach_digest_snapshot_prompt_and_cache(
        tmp_path, custom_instrument, transport, monkeypatch):
    path, profile = custom_instrument
    clients, calls = transport
    monkeypatch.setenv("D4D_PROFILE", "neutral")
    expected = slot_specification_snapshot("CoreDataset", path, profile=profile)
    context = LLMSlotFitnessScorer(
        class_name="CoreDataset", schema_path=path, profile=profile)._context("offline")
    cache = tmp_path / "subtypes.jsonl"
    classifier = FormSubtypeClassifier(
        model="offline", class_name="CoreDataset", schema_path=path,
        profile=profile, cache_path=cache)

    classifier(form_failure(expected, slot="subject", value='{"term":"TEST:1"}'))
    assert len(clients) == len(calls) == 1
    assert classifier.schema == context.schema == expected[0]
    assert classifier.specification == context.specification == expected[3]
    prompt = calls[0]["messages"][0]["content"]
    assert "Custom core instruction." in prompt
    assert "1=selected-profile-term" in prompt
    assert "Dataset-only instruction." not in prompt
    row = json.loads(cache.read_text())
    assert (row["schema"], row["specification"]) == (context.schema, context.specification)


def test_core_cache_replays_its_recorded_instrument_but_wrong_class_cannot_fill(
        tmp_path, transport):
    clients, calls = transport
    expected = slot_specification_snapshot("CoreDataset", profile=NEUTRAL)
    cache = tmp_path / "subtypes.jsonl"
    failure = form_failure(expected)
    first = FormSubtypeClassifier(
        model="offline", class_name="CoreDataset", profile=NEUTRAL, cache_path=cache)
    answer = first(failure)
    original = cache.read_bytes()

    # Cache-first historical replay is independent of the working-tree class.
    replay = FormSubtypeClassifier(model="offline", profile=NEUTRAL, cache_path=cache)
    assert replay(failure) == answer
    assert replay.memo_hits == 1 and replay.calls == 0
    with pytest.raises(ValueError, match="fresh cache"):
        replay(form_failure(expected, value='"uncached value"'))
    assert len(clients) == len(calls) == 1
    assert cache.read_bytes() == original


def test_explicit_core_cache_replay_needs_no_live_schema(tmp_path, transport, monkeypatch):
    _, calls = transport
    expected = slot_specification_snapshot("CoreDataset", profile=NEUTRAL)
    cache = tmp_path / "subtypes.jsonl"
    failure = form_failure(expected)
    first = FormSubtypeClassifier(
        model="offline", class_name="CoreDataset", profile=NEUTRAL, cache_path=cache)
    answer = first(failure)
    original = cache.read_bytes()

    def unavailable(*args, **kwargs):
        raise AssertionError("frozen replay must not read a live schema")

    monkeypatch.setattr(schema_digest, "digest_text", unavailable)
    monkeypatch.setattr(FormSubtypeClassifier, "_live_snapshot", unavailable)
    replay = FormSubtypeClassifier(
        model="offline", class_name="CoreDataset", profile=NEUTRAL,
        schema_path=tmp_path / "missing.yaml", cache_path=cache, offline=True)
    assert replay(failure) == answer
    assert len(calls) == 1 and replay.calls == 0
    assert cache.read_bytes() == original
