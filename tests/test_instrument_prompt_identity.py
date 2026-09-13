"""Scores must identify their sent rules, independent of unrelated branches."""
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from evaluation import evaluate_d4d_llm as llm
from tests.judge_fixtures import judge_reply


def evaluator(tmp_path, metadata=None):
    obj = llm.D4DLLMEvaluator.__new__(llm.D4DLLMEvaluator)
    obj.config = llm.LLMEvaluationConfig(rubric_dir=tmp_path, error_dir=tmp_path / "errors")
    (tmp_path / "rubric20.txt").write_text("rubric: example\n")
    obj.rubric20 = {"rubric": "example", "d4d_evaluation_rubric": {"rubric": [
        {"id": 1, "name": "Example", "score_type": "numeric", "field": ["id"]}]}}
    obj.context = {}
    obj._rubric_bytes = {"rubric20.txt": (tmp_path / "rubric20.txt").read_bytes()}
    obj.rubric20_system_prompt = "Judge only these rules:\n{RUBRIC_SPECIFICATION}"
    calls = []

    def create(**kw):
        calls.append(kw)
        contract = json.loads(kw["messages"][0]["content"].split("```json\n")[1].split("\n```")[0])
        result = judge_reply(contract, "rubric20", metadata=metadata)
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(result))])

    obj.client = SimpleNamespace(messages=SimpleNamespace(create=create))
    return obj, calls


def score(obj):
    return obj._evaluate_with_rubric("rubric20", "id: x\n", "P", "method", "record.yaml", "input-hash")


def test_driver_attests_the_actual_request_and_keeps_judge_annotations(tmp_path):
    obj, calls = evaluator(tmp_path, {"instrument_sha256": "invented", "annotation": "keep me"})
    meta = score(obj)["metadata"]
    assert meta["instrument_kind"] == "api_system_prompt"
    assert meta["instrument_sha256"] == hashlib.sha256(calls[0]["system"].encode()).hexdigest()
    assert len(meta["instrument_sha256"]) == 64
    assert meta["evaluator_reported_instrument_sha256"] == "invented"
    assert meta["annotation"] == "keep me"
    sent_user = calls[0]["messages"][0]["content"]
    assert meta["request_user_prompt_sha256"] == hashlib.sha256(sent_user.encode()).hexdigest()


@pytest.mark.parametrize("change", ["template", "rubric"])
def test_every_sent_scoring_rule_change_moves_the_system_digest(tmp_path, change):
    obj, _ = evaluator(tmp_path)
    before = score(obj)["metadata"]["instrument_sha256"]
    if change == "template":
        obj.rubric20_system_prompt += "\nA changed scoring rule."
    else:
        obj.rubric20["rubric"] = "a changed band"
    assert score(obj)["metadata"]["instrument_sha256"] != before


def test_an_unsent_agent_edit_does_not_change_the_api_instrument(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "__file__", str(tmp_path / "src/evaluation/evaluate_d4d_llm.py"))
    agent = tmp_path / ".claude/agents/d4d-rubric20-semantic.md"
    agent.parent.mkdir(parents=True)
    agent.write_text("unsent definition one")
    obj, _ = evaluator(tmp_path)
    before = score(obj)["metadata"]["instrument_sha256"]
    agent.write_text("unsent definition two")
    assert score(obj)["metadata"]["instrument_sha256"] == before


def resolver(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts/instrument_provenance.py"
    spec = importlib.util.spec_from_file_location("prompt_identity_resolver", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module


@pytest.mark.parametrize("digest", ["a" * 64, None, "short", "z" * 64])
def test_explicit_api_identity_never_falls_back_to_an_agent(tmp_path, monkeypatch, digest):
    module = resolver(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "versions", lambda path: [])

    def unexpected(*args):
        raise AssertionError("must not invent an agent attribution")

    monkeypatch.setattr(module, "_dirty", unexpected)
    base = tmp_path / "data/evaluation_llm/rubric20_semantic"
    base.mkdir(parents=True)
    path = base / "new_evaluation.json"
    path.write_text(json.dumps({"metadata": {
        "instrument_kind": "api_system_prompt", "instrument_sha256": digest,
        "rubric_hash": "b" * 64,
    }}))
    entry = module.resolve("rubric20_semantic")["evaluations"][path.name]
    assert entry["instrument_commit"] is None
    assert entry["basis"] == ("recorded_api_system_prompt" if digest == "a" * 64 else "unresolved")
    assert entry["instrument_sha256"] == (digest if digest == "a" * 64 else None)


def test_an_unrelated_branch_cannot_change_the_checked_out_instrument_history(tmp_path, monkeypatch):
    module = resolver(tmp_path, monkeypatch)

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True,
                                       stderr=subprocess.DEVNULL).strip()

    git("init", "-q", "-b", "main")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Instrument branch test")
    git("config", "commit.gpgsign", "false")
    agent = tmp_path / "agent.md"
    agent.write_text("main rules\n")
    git("add", "."); git("commit", "-qm", "main rules")
    before = module.versions("agent.md")
    git("checkout", "-qb", "unrelated")
    agent.write_text("unmerged rules\n")
    git("commit", "-qam", "unmerged rules")
    git("checkout", "-q", "main")
    assert module.versions("agent.md") == before


def test_unknown_instrument_kind_is_not_reinterpreted_as_an_agent(tmp_path, monkeypatch):
    module = resolver(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "versions", lambda path: [{"sha256": "a" * 64, "commit": "fake"}])
    base = tmp_path / "data/evaluation_llm/rubric20_semantic"
    base.mkdir(parents=True)
    (base / "unknown_evaluation.json").write_text(json.dumps({"metadata": {
        "instrument_kind": "another_evaluator", "instrument_sha256": "a" * 64,
    }}))
    entry = module.resolve("rubric20_semantic")["evaluations"]["unknown_evaluation.json"]
    assert entry["basis"] == "unresolved"
    assert entry["instrument_commit"] is None
