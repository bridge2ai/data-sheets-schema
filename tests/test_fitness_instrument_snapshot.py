"""Fitness prompts and persisted contexts must describe the same instrument (#1259)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner, schema_digest
from data_sheets_schema.evidence_score import LLMSlotFitnessScorer


def schema(kind):
    return ("id: https://example.org/fitness\nname: fitness\ndefault_range: string\n"
            "classes:\n  Dataset:\n    attributes:\n      subject:\n"
            f"        description: Enter a {kind}.\n"
            "        range: Topic\n        inlined: true\n"
            "  Topic:\n    attributes:\n      term:\n        values_from: [TEST]\n")


@pytest.fixture
def scorer(tmp_path, monkeypatch):
    path = tmp_path / "schema.yaml"
    path.write_text(schema("country"))
    pin = tmp_path / "vocabulary.yaml"
    pin.write_text("vocabularies:\n  TEST:\n    TEST:1: first\n")
    monkeypatch.setattr(schema_digest, "VOCABULARY_PIN", pin)
    calls = []

    def fake(client, **kwargs):
        calls.append(kwargs["messages"][0]["content"])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text='{"fitness":1.0,"failure":"none","reason":"offline"}')],
                               stop_reason="end_turn", usage=None)

    monkeypatch.setattr(api_runner, "_call_with_retry", fake)
    cache = tmp_path / "fitness.jsonl"
    sc = LLMSlotFitnessScorer(client=object(), model="offline-test", schema_path=path, cache_path=cache)
    return sc, path, pin, calls, cache


def rate(sc):
    return sc(project="offline", slot="subject", value={"term": "TEST:1"})


@pytest.mark.parametrize("part", ["schema", "vocabulary"])
def test_reused_scorer_refreshes_prompt_and_cache_context_together(scorer, part):
    sc, path, pin, calls, cache = scorer
    assert "country" in sc.spec("subject")
    before = sc._context("offline-test").schema
    rate(sc)
    old = cache.read_bytes()
    target = path if part == "schema" else pin
    original = target.read_text()
    target.write_text(schema("species") if part == "schema" else original.replace("first", "other"))
    after = sc._context("offline-test").schema
    assert before != after
    rate(sc)
    assert len(calls) == 2
    assert ("Enter a species." if part == "schema" else "1=other") in calls[1]
    assert ("Enter a country." if part == "schema" else "1=first") not in calls[1]
    assert cache.read_bytes().startswith(old)
    assert [d["schema"] for d in map(json.loads, cache.read_text().splitlines())] == [before, after]
    target.write_text(original)
    rate(sc)
    assert len(calls) == 2  # The original judgement still belongs to the original instrument.


@pytest.mark.parametrize("part", ["schema", "vocabulary"])
def test_change_between_context_and_prompt_uses_the_captured_instrument(scorer, monkeypatch, part):
    sc, path, pin, calls, cache = scorer
    before = sc._context("offline-test").schema
    load = sc._load_cache
    changed = False

    def change_after_context(ctx):
        nonlocal changed
        load(ctx)
        if not changed:
            changed = True
            if part == "schema":
                path.write_text(schema("species"))
            else:
                pin.write_text(pin.read_text().replace("first", "other"))

    monkeypatch.setattr(sc, "_load_cache", change_after_context)
    rate(sc)
    assert "Enter a country." in calls[0] and "1=first" in calls[0]
    assert json.loads(cache.read_text())["schema"] == before
    rate(sc)
    assert len(calls) == 2
    assert ("Enter a species." if part == "schema" else "1=other") in calls[1]


def test_a_nested_range_omitted_from_generation_digest_still_invalidates_fitness(tmp_path, monkeypatch):
    path = tmp_path / schema_digest.FULL_SCHEMA.name
    doc = yaml.safe_load(schema_digest.FULL_SCHEMA.read_bytes())
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    calls = []

    def fake(client, **kwargs):
        calls.append(kwargs["messages"][0]["content"])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text='{"fitness":1,"reason":"offline"}')],
                               stop_reason="end_turn", usage=None)

    monkeypatch.setattr(api_runner, "_call_with_retry", fake)
    cache = tmp_path / "fitness.jsonl"
    sc = LLMSlotFitnessScorer(client=object(), model="offline-test", schema_path=path, cache_path=cache)
    first = sc._context("offline-test")
    sc(project="offline", slot="subsets", value=[{"total_size_bytes": 1}])
    assert "total_size_bytes → integer" in calls[0]
    doc["classes"]["DataSubset"]["attributes"]["total_size_bytes"]["range"] = "decimal"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    second = sc._context("offline-test")
    assert first.schema == second.schema  # The generation instrument deliberately omits this range.
    assert first.fingerprint() != second.fingerprint()
    sc(project="offline", slot="subsets", value=[{"total_size_bytes": 1}])
    assert len(calls) == 2
    assert "total_size_bytes → decimal" in calls[1]
    entries = [json.loads(line) for line in cache.read_text().splitlines()]
    assert entries[0]["schema"] == entries[1]["schema"]
    assert entries[0]["specification"] != entries[1]["specification"]


def test_legacy_judgement_without_complete_specification_is_retained_but_not_used(scorer):
    sc, path, pin, calls, cache = scorer
    context = sc._context("offline-test").as_entry()
    context.pop("specification")
    legacy = {**context, "slot": "subject", "value": json.dumps({"term": "TEST:1"}, sort_keys=True),
              "fitness": 0, "failure": "form", "reason": "legacy"}
    original = json.dumps(legacy) + "\n"
    cache.write_text(original)
    assert rate(sc).fitness == 1
    assert len(calls) == 1
    assert cache.read_text().startswith(original)
    assert sc.cache_skipped == {"specification": 1}
