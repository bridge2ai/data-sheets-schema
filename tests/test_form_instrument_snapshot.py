"""Preserve frozen subtype measurements without mislabelling new calls (#1263)."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner, schema_digest
from data_sheets_schema.agreement import _digest
from data_sheets_schema.evidence_score import LLMSlotFitnessScorer
from data_sheets_schema.form_defects import FORM_SUBTYPE_SYSTEM, FormFailure, FormSubtypeClassifier


def failure(value="place", reason="form problem"):
    return FormFailure("offline", "subject", value, reason, 0)


@pytest.fixture
def instrument(tmp_path, monkeypatch):
    path = tmp_path / "data_sheets_schema_all.yaml"
    path.write_text("id: https://example.org/form\nname: form\ndefault_range: string\n"
                    "classes:\n  Dataset:\n    attributes:\n      subject:\n"
                    "        description: Enter a country.\n        values_from: [TEST]\n")
    pin = tmp_path / "vocabulary.yaml"
    pin.write_text("vocabularies:\n  TEST:\n    TEST:1: first\n")
    monkeypatch.setitem(schema_digest.CLASS_SCHEMA, "Dataset", path)
    monkeypatch.setattr(schema_digest, "VOCABULARY_PIN", pin)
    calls, clients = [], []

    def client():
        clients.append(True)
        return object()

    def fake(client, **kwargs):
        calls.append(kwargs["messages"][0]["content"])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(
            {"subtype": "other", "reason": f"call {len(calls)}"}))])

    monkeypatch.setattr(api_runner, "_client", client)
    monkeypatch.setattr(api_runner, "_call_with_retry", fake)
    cache = tmp_path / "subtypes.jsonl"

    def classifier(**kwargs):
        return FormSubtypeClassifier(model="offline-test", cache_path=cache, **kwargs)

    return path, pin, cache, calls, clients, classifier


def test_historical_fill_is_refused_before_creating_a_client(instrument):
    path, pin, cache, calls, clients, classifier = instrument
    c = classifier(schema="historical-schema")
    with pytest.raises(ValueError, match="fresh cache"):
        c(failure())
    assert calls == clients == [] and not cache.exists()


def test_legacy_replay_is_retained_but_a_new_label_requires_an_attested_instrument(instrument):
    path, pin, cache, calls, clients, classifier = instrument
    current = LLMSlotFitnessScorer()._context("offline-test").schema
    row = {"rubric": _digest(FORM_SUBTYPE_SYSTEM), "model": "offline-test", "schema": current,
           "key": failure().key, "slot": "subject", "subtype": "both", "reason": "historic"}
    original = json.dumps(row) + "\n"
    cache.write_text(original)
    c = classifier()
    assert c(failure()) == ("both", "historic")
    with pytest.raises(ValueError, match="fresh cache"):
        c(failure("new value"))
    assert calls == clients == [] and cache.read_text() == original


def test_frozen_offline_replay_does_not_need_the_live_schema(instrument, monkeypatch):
    path, pin, cache, calls, clients, classifier = instrument
    original = classifier()(failure())

    def unavailable(*args, **kwargs):
        raise AssertionError("historical replay must not parse the current schema")

    monkeypatch.setattr(schema_digest, "digest_text", unavailable)
    monkeypatch.setattr(FormSubtypeClassifier, "_live_snapshot", unavailable)
    assert classifier(offline=True)(failure()) == original


def test_two_complete_specifications_require_an_explicit_selection(instrument):
    from data_sheets_schema.form_defects import PooledInstruments
    path, pin, cache, calls, clients, classifier = instrument
    classifier()(failure())
    first = json.loads(cache.read_text())
    second = {**first, "specification": "0" * 64, "reason": "another instrument"}
    with cache.open("a") as stream:
        stream.write(json.dumps(second) + "\n")
    with pytest.raises(PooledInstruments, match="multiple complete specifications"):
        classifier(offline=True)
    assert classifier(offline=True, specification="0" * 64)(failure()) == ("other", "another instrument")


@pytest.mark.parametrize("part", ["schema", "vocabulary"])
def test_a_frozen_classifier_refuses_new_labels_after_instrument_drift(instrument, part):
    path, pin, cache, calls, clients, classifier = instrument
    c = classifier()
    c(failure())
    before = cache.read_bytes()
    changed = path if part == "schema" else pin
    changed.write_text(changed.read_text().replace("country", "species").replace("first", "other"))
    with pytest.raises(ValueError, match="fresh cache"):
        c(failure("new value"))
    assert len(calls) == 1 and cache.read_bytes() == before
    # The old entry remains a replay of its named historical instrument.
    assert classifier(offline=True)(failure()) == ("other", "call 1")


def test_new_label_names_the_complete_specification_and_the_supplied_reason(instrument):
    path, pin, cache, calls, clients, classifier = instrument
    classifier()(failure())
    row = json.loads(cache.read_text())
    expected = LLMSlotFitnessScorer()._context("offline-test")
    assert row["schema"] == expected.schema
    assert row["specification"] == expected.specification
    assert row["input_reason_sha256"] == hashlib.sha256(failure().reason.encode()).hexdigest()


def test_changed_fitness_reason_is_a_distinct_classifier_input(instrument):
    path, pin, cache, calls, clients, classifier = instrument
    c = classifier()
    first = c(failure())
    second = c(failure(reason="another form problem"))
    assert len(calls) == 2 and first != second
    offline = classifier(offline=True)
    assert offline(failure()) == first
    assert offline(failure(reason="another form problem")) == second


def test_prompt_uses_the_same_capture_as_its_recorded_instrument(instrument, monkeypatch):
    path, pin, cache, calls, clients, classifier = instrument
    c = classifier()
    expected = c.specification
    schema = c.schema
    capture = c._live_snapshot

    def change_after_capture():
        snapshot = capture()
        path.write_text(path.read_text().replace("country", "species"))
        return snapshot

    monkeypatch.setattr(c, "_live_snapshot", change_after_capture)
    c(failure())
    assert "country" in calls[0] and "species" not in calls[0]
    assert json.loads(cache.read_text())["specification"] == expected
    assert json.loads(cache.read_text())["schema"] == schema
