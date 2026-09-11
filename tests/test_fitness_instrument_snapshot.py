"""Fitness prompts and persisted contexts must describe the same instrument (#1259)."""

import json
from types import SimpleNamespace

import pytest

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
