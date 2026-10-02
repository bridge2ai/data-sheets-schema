"""Offline model selection, output disclosure and cache-identity preservation."""
import hashlib
import json
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner, evaluation_model as em
from data_sheets_schema.agreement import EquivalenceJudge, build_matrix
from data_sheets_schema.evidence_score import LLMSlotScorer, LLMSlotFitnessScorer
from data_sheets_schema.form_defects import FormSubtypeClassifier
from data_sheets_schema.support_judge import SupportJudgeV2, SupportSpecification
from tests.test_evaluation_model import PATHS


@pytest.fixture
def config(tmp_path, monkeypatch):
    p = tmp_path / "evaluation.yaml"
    p.write_text("version: 1\nmodel: independent-judge\n")
    monkeypatch.setattr(em, "CONFIG_PATH", p)
    return p


@pytest.mark.parametrize("name", sorted(PATHS))
def test_config_moves_every_judge_without_moving_generator(config, name, tmp_path, monkeypatch):
    monkeypatch.setattr(api_runner, "_model_settings", lambda: {"name": "generator-only"})
    assert PATHS[name](monkeypatch, tmp_path) == "independent-judge"
    selected = em.evaluation_model_settings()
    assert selected["basis"] == "evaluation_config"
    assert selected["generation_model"] == "generator-only"
    assert selected["configuration"]["sha256"] == hashlib.sha256(config.read_bytes()).hexdigest()
    assert api_runner._model_settings()["name"] == "generator-only"


@pytest.mark.parametrize("body", [
    "[]", "model: m", "version: 2\nmodel: m", "version: true\nmodel: m",
    "version: 1\nmodel: ''", "version: 1\nmodel: false", "version: 1\nmodel: [m]",
    "version: 1\nmodel: m\nmodel: n", "version: 1\nmodel: m\nmodle: n",
    "version: 1\nmodel: ' m '",
])
def test_invalid_default_config_fails_but_explicit_selection_needs_no_default(config, body):
    config.write_text(body)
    with pytest.raises(ValueError):
        em.evaluation_model_settings()
    assert em.model_selection("explicit") == {"name": "explicit", "basis": "explicit_override"}


def test_config_is_read_at_call_time_and_never_from_ambient_working_directory(config, tmp_path, monkeypatch):
    other = tmp_path / "ambient" / "src" / "data_sheets_schema"
    other.mkdir(parents=True)
    (other / "evaluation_config.yaml").write_text("version: 1\nmodel: wrong\n")
    monkeypatch.chdir(other.parents[1])
    assert em.evaluation_model_name() == "independent-judge"
    config.write_text("version: 1\nmodel: changed\n")
    assert em.evaluation_model_name() == "changed"
    config.unlink()
    with pytest.raises(FileNotFoundError):
        em.evaluation_model_name()


def response(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn")


@pytest.mark.parametrize("kind", ["support_v1", "fitness", "support_v2"])
def test_new_logs_disclose_selection_and_existing_cache_remains_reusable(config, tmp_path, monkeypatch, kind):
    cache, log = tmp_path / "cache.jsonl", tmp_path / "reasoning.jsonl"
    seen = []
    answer = ({"verdict": "supported", "reason": "fixture"} if kind == "support_v2"
              else {"supported": 1.0, "fitness": 1.0, "failure": None, "reason": "fixture"})
    def call(client, **kwargs):
        seen.append(kwargs)
        return response(json.dumps(answer))
    monkeypatch.setattr(api_runner, "_call_with_retry", call)
    opts = dict(client=object(), cache_path=cache, log_path=log)
    if kind == "support_v1":
        make = lambda **kw: LLMSlotScorer(**opts, **kw)
        run = lambda j: j(project="P", slot="title", value="A", bundle="A")
    elif kind == "fitness":
        make = lambda **kw: LLMSlotFitnessScorer(**opts, **kw)
        run = lambda j: j(project="P", slot="title", value="A")
    else:
        spec = SupportSpecification(digest="spec", render=lambda s: "A title", relationship=lambda s: False)
        make = lambda **kw: SupportJudgeV2(specification=spec, **opts, **kw)
        run = lambda j: j.judge(project="P", record={"title": "A"}, slot="title", bundle="A")
    first = make()
    run(first)
    assert seen[0]["model"] == "independent-judge"
    assert first.usage[0]["evaluation_model"]["basis"] == "evaluation_config"
    for path in (cache, log):
        row = json.loads(path.read_text().splitlines()[0])
        assert row["evaluation_model"]["basis"] == "evaluation_config"
        assert row["evaluation_model"]["name"] == row["model"]
    # Legacy rows carry the same model/instrument; metadata never becomes a new
    # cache key, and replay must not backfill a made-up historical basis.
    legacy = json.loads(cache.read_text())
    legacy.pop("evaluation_model")
    cache.write_text(json.dumps(legacy) + "\n")
    before = cache.read_bytes(), log.read_bytes()
    second = make(model="independent-judge")
    run(second)
    assert len(seen) == 1 and second.memo_hits == 1
    assert (cache.read_bytes(), log.read_bytes()) == before
    assert second.evaluation_model["basis"] == "explicit_override"


def test_equivalence_matrix_and_new_cache_disclose_selection(config, tmp_path, monkeypatch):
    monkeypatch.setattr(api_runner, "_call_with_retry", lambda *a, **kw: response('{"equivalent": true, "reason": "fixture"}'))
    cache = tmp_path / "equivalence.jsonl"
    j = EquivalenceJudge(client=object(), cache_path=cache)
    j("title", ["A", "B"])
    row = json.loads(cache.read_text())
    assert row["evaluation_model"]["basis"] == "evaluation_config"
    for rep in (1, 2):
        p = tmp_path / "method" / f"label_rep{rep}" / "P_d4d.yaml"
        p.parent.mkdir(parents=True)
        p.write_text("title: same\n")
    matrix, _ = build_matrix(root=tmp_path, method="method", configs={"c": "label"},
                             projects=("P",), reps=2, cache_dir=tmp_path, offline=True)
    assert matrix["c|P"]["evaluation_model"]["basis"] == "evaluation_config"
    assert matrix["c|P"]["judge_model"] == "independent-judge"


def test_form_subtype_cache_precedence_and_new_entries_disclose_basis(config, tmp_path):
    path = tmp_path / "form.jsonl"
    first = FormSubtypeClassifier(cache_path=path)
    first._save("key", "title", "other", "fixture")
    assert json.loads(path.read_text())["evaluation_model"]["basis"] == "evaluation_config"
    config.write_text("version: 1\nmodel: another-judge\n")
    second = FormSubtypeClassifier(cache_path=path, offline=True)
    assert second.model == "independent-judge"
    second._save("new", "title", "other", "fixture")
    assert json.loads(path.read_text().splitlines()[1])["evaluation_model"]["basis"] == "recorded_cache_model"


def test_api_rubric_retains_its_separate_registered_default(config, monkeypatch):
    from data_sheets_schema.evaluation.evaluate_d4d_llm import LLMEvaluationConfig
    monkeypatch.setattr(api_runner, "_model_settings", lambda: {"name": "new-generator"})
    assert em.evaluation_model_name() == "independent-judge"
    assert LLMEvaluationConfig().model == "claude-sonnet-4-5-20250929"
    assert LLMEvaluationConfig(model="registered-other").model == "registered-other"


def test_referent_report_binds_one_judge_model_across_config_changes(config, monkeypatch):
    from data_sheets_schema.merge import LLMReferentJudge, referent_report
    before = hashlib.sha256(config.read_bytes()).hexdigest()
    calls = []
    def call(client, **kwargs):
        calls.append(kwargs["model"])
        config.write_text("version: 1\nmodel: changed-mid-report\n")
        return response('{"same_referent": true, "reason": "fixture"}')
    monkeypatch.setattr(api_runner, "_call_with_retry", call)
    j = LLMReferentJudge(client=object())
    report = referent_report({"a": {"title": "A", "description": "One"},
                              "b": {"title": "B", "description": "Two"}},
                             judge=j, slots=("title", "description"))
    assert calls == ["independent-judge", "independent-judge"]
    for finding in report.findings:
        assert finding.evaluation_model["name"] == "independent-judge"
        assert finding.evaluation_model["basis"] == "evaluation_config"
        assert finding.evaluation_model["configuration"]["sha256"] == before
    report.findings[0].evaluation_model["configuration"]["sha256"] = "changed-output"
    assert report.findings[1].evaluation_model["configuration"]["sha256"] == before
    assert j.evaluation_model["configuration"]["sha256"] == before
    LLMReferentJudge(client=object())(slot="title", values={"a": "A", "b": "B"})
    assert calls[-1] == "changed-mid-report"


def test_referent_explicit_model_and_unjudged_findings_do_not_invent_basis(config, monkeypatch):
    from data_sheets_schema.merge import LLMReferentJudge, referent_report
    config.write_text("invalid configuration")
    monkeypatch.setattr(api_runner, "_call_with_retry", lambda *a, **kw: response('{"same_referent": false}'))
    j = LLMReferentJudge(client=object(), model="explicit")
    result = j(slot="title", values={"a": "A", "b": "B"})
    assert result.evaluation_model == {"name": "explicit", "basis": "explicit_override"}
    for records in ({"a": {"title": "A"}, "b": {"title": "A"}},
                    {"a": {"title": "A"}, "b": {"title": "B"}}):
        report = referent_report(records)
        assert all(f.evaluation_model is None for f in report.findings)
