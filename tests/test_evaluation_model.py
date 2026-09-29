"""The evaluation-model seam (#2928).

Every judging path resolves its model through `evaluation_model` when it was
given none. The hazard this change carries is silently changing which judge
runs: a judge cache is scoped on the model name, so a default that moved would
make every cached judgement fall out of scope (#351, #462). These tests pin the
default to exactly the old resolution, and prove the seam is the one place a
future evaluation config needs to change.

Offline throughout: the fake client records the model it was asked for and
answers nothing that matters.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner, evaluation_model
from data_sheets_schema.agreement import EquivalenceJudge, _digest
from data_sheets_schema.evaluation_model import (
    BASIS_GENERATION_DEFAULT,
    evaluation_model_settings,
    model_family,
    same_family,
    same_family_label,
)
from data_sheets_schema.evidence_score import LLMSlotFitnessScorer, LLMSlotScorer
from data_sheets_schema.form_defects import (
    FORM_SUBTYPE_SYSTEM,
    FormSubtypeClassifier,
    PooledInstruments,
)
from data_sheets_schema.merge import LLMReferentJudge

FAKE_CLIENT = object()


def _slot_scorer():
    return LLMSlotScorer(client=FAKE_CLIENT)._resolve()[1]


def _fitness_scorer():
    return LLMSlotFitnessScorer(client=FAKE_CLIENT)._resolve()[1]


def _referent_judge(monkeypatch):
    seen = {}

    def fake_call(client, *, model, **_):
        seen["model"] = model
        return SimpleNamespace(content=[SimpleNamespace(
            type="text", text='{"same_referent": true, "reason": "x"}')])

    monkeypatch.setattr(api_runner, "_call_with_retry", fake_call)
    LLMReferentJudge(client=FAKE_CLIENT)(slot="title", values={"a": "x", "b": "x"})
    return seen["model"]


def _equivalence_judge():
    return EquivalenceJudge(client=FAKE_CLIENT, offline=True).model


def _form_defects(tmp: Path):
    return FormSubtypeClassifier(cache_path=tmp / "absent.jsonl", offline=True).model


PATHS = {
    "evidence_score.LLMSlotScorer": lambda mp, tmp: _slot_scorer(),
    "evidence_score.LLMSlotFitnessScorer": lambda mp, tmp: _fitness_scorer(),
    "merge.LLMReferentJudge": lambda mp, tmp: _referent_judge(mp),
    "agreement.EquivalenceJudge": lambda mp, tmp: _equivalence_judge(),
    "form_defects.FormSubtypeClassifier": lambda mp, tmp: _form_defects(tmp),
}


@pytest.fixture
def tmp(tmp_path):
    return tmp_path


@pytest.mark.parametrize("path", sorted(PATHS))
def test_with_no_evaluation_config_every_judge_resolves_the_generation_model(
        path, monkeypatch, tmp):
    """Exactly what each path resolved before #2928: the generation pin."""
    assert PATHS[path](monkeypatch, tmp) == api_runner._model_settings()["name"]


def test_the_default_is_todays_shipped_generation_model():
    """The judge caches are scoped on this name. If the shipped generation
    config moves, this fails — and the judge identity would move with it,
    which is a decision to make on purpose, not a side effect."""
    settings = evaluation_model_settings()
    assert settings == {"name": "claude-opus-5",
                        "basis": BASIS_GENERATION_DEFAULT,
                        "generation_model": "claude-opus-5"}


@pytest.mark.parametrize("path", sorted(PATHS))
def test_every_judge_resolves_through_the_evaluation_setting(path, monkeypatch, tmp):
    """Naming an evaluation model moves every path, and the generation model
    alone moves none of them (the issue's required test)."""
    monkeypatch.setattr(evaluation_model, "evaluation_model_settings",
                        lambda: {"name": "evaluator-x", "basis": "test",
                                 "generation_model": "unused"})
    monkeypatch.setattr(api_runner, "_model_settings",
                        lambda: {"name": "a-different-generator"})
    assert PATHS[path](monkeypatch, tmp) == "evaluator-x"


@pytest.mark.parametrize("path", sorted(PATHS))
def test_the_default_follows_the_generation_model_at_call_time(path, monkeypatch, tmp):
    """The default is read when the judge resolves, as the old fallback was."""
    monkeypatch.setattr(api_runner, "_model_settings",
                        lambda: {"name": "generator-y"})
    assert PATHS[path](monkeypatch, tmp) == "generator-y"


@pytest.mark.parametrize("path", sorted(PATHS))
def test_an_explicit_model_is_never_overridden(path, monkeypatch, tmp):
    monkeypatch.setattr(evaluation_model, "evaluation_model_settings",
                        lambda: {"name": "evaluator-x"})
    explicit = {
        "evidence_score.LLMSlotScorer":
            lambda: LLMSlotScorer(client=FAKE_CLIENT, model="m")._resolve()[1],
        "evidence_score.LLMSlotFitnessScorer":
            lambda: LLMSlotFitnessScorer(client=FAKE_CLIENT, model="m")._resolve()[1],
        "agreement.EquivalenceJudge":
            lambda: EquivalenceJudge(client=FAKE_CLIENT, model="m", offline=True).model,
        "form_defects.FormSubtypeClassifier":
            lambda: FormSubtypeClassifier(cache_path=tmp / "absent.jsonl",
                                          model="m", offline=True).model,
    }
    if path == "merge.LLMReferentJudge":
        seen = {}
        monkeypatch.setattr(api_runner, "_call_with_retry",
                            lambda client, *, model, **_: seen.update(model=model)
                            or SimpleNamespace(content=[SimpleNamespace(
                                type="text", text='{"same_referent": true}')]))
        LLMReferentJudge(client=FAKE_CLIENT, model="m")(slot="s", values={"a": "1"})
        assert seen["model"] == "m"
    else:
        assert explicit[path]() == "m"


class TestFormDefectsKeepsItsCacheFirst:
    """#462/#464 survive the rewiring: the cache's instrument outranks the
    evaluation setting, and a pooled cache still refuses to choose."""

    def _write(self, path: Path, models):
        path.write_text("\n".join(
            json.dumps({"rubric": _digest(FORM_SUBTYPE_SYSTEM), "model": m,
                        "chars": 4000, "key": f"k{i}", "slot": "s",
                        "subtype": "other", "reason": ""})
            for i, m in enumerate(models)) + "\n", encoding="utf-8")

    def test_the_recorded_model_wins(self, monkeypatch, tmp):
        monkeypatch.setattr(evaluation_model, "evaluation_model_settings",
                            lambda: {"name": "evaluator-x"})
        cache = tmp / "subtypes.jsonl"
        self._write(cache, ["google/claude-opus-5-high"])
        assert FormSubtypeClassifier(cache_path=cache, offline=True).model \
            == "google/claude-opus-5-high"

    def test_a_pooled_cache_still_refuses(self, monkeypatch, tmp):
        monkeypatch.setattr(evaluation_model, "evaluation_model_settings",
                            lambda: {"name": "evaluator-x"})
        cache = tmp / "subtypes.jsonl"
        self._write(cache, ["a-model", "b-model"])
        with pytest.raises(PooledInstruments):
            FormSubtypeClassifier(cache_path=cache, offline=True).model


@pytest.mark.parametrize("name", [
    "google/claude-opus-5-high", "claude-opus-5[1m]", "claude-opus-5",
    "claude-sonnet-4-5-20250929", "claude-fable-5",
    "anthropic/claude-sonnet-4-5", "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "Claude-Opus-5",
])
def test_claude_identifiers_are_one_family(name):
    assert model_family(name) == "claude"


@pytest.mark.parametrize("name,family", [
    ("openai:gpt-5", "gpt"), ("gpt-5", "gpt"), ("openai/gpt-5-mini", "gpt"),
    ("gpt5", "gpt"), ("o3-mini", "gpt"),
    ("google/gemini-2.5-pro", "gemini"),
])
def test_other_vendors_are_other_families(name, family):
    assert model_family(name) == family


@pytest.mark.parametrize("name", [None, "", "claudecode", "curated", "unknown-model", 7])
def test_an_unrecognised_name_is_unknown_not_a_guess(name):
    assert model_family(name) is None


def test_same_family():
    assert same_family("claude-opus-5[1m]", "google/claude-opus-5-high") is True
    assert same_family("claude-sonnet-4-5-20250929", "openai:gpt-5") is False
    assert same_family(None, "claude-opus-5") is None
    assert same_family("claude-opus-5", "unknown-model") is None
    assert same_family_label("claude-opus-5", "claude-opus-5") == "yes"
    assert same_family_label("claude-opus-5", "gpt-5") == "no"
    assert same_family_label("claude-opus-5", None) == "unknown"
