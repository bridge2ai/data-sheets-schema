"""Archiving a score must preserve the instrument that produced its bytes."""
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("rewrite", [False, True])
def test_archive_move_preserves_instrument_unless_score_changes(tmp_path, monkeypatch, rewrite):
    script = Path(__file__).resolve().parents[1] / "scripts/instrument_provenance.py"
    spec = importlib.util.spec_from_file_location("archive_instrument", script)
    resolver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resolver)
    monkeypatch.setattr(resolver, "ROOT", tmp_path)

    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, check=True,
                              capture_output=True, text=True).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "Instrument history test")
    git("config", "user.email", "test@example.invalid")
    git("config", "commit.gpgsign", "false")
    agent = tmp_path / resolver.RUBRICS["rubric20_semantic"][0]
    rubric = tmp_path / resolver.RUBRICS["rubric20_semantic"][1]
    base = tmp_path / "data/evaluation_llm/rubric20_semantic/concatenated"
    for directory in (agent.parent, rubric.parent, base):
        directory.mkdir(parents=True, exist_ok=True)
    agent.write_text("original scoring rules\n")
    rubric.write_text("rubric text\n")
    original_sha = hashlib.sha256(agent.read_bytes()).hexdigest()
    evaluation = base / "example_evaluation.json"
    evaluation.write_text(json.dumps({"metadata": {}, "score": 1}) + "\n")
    git("add", ".")
    git("commit", "-qm", "Score with the original instrument")
    original_commit = git("rev-parse", "HEAD")

    archived = base / "_archive/example_evaluation.json"
    archived.parent.mkdir()
    evaluation.rename(archived)
    agent.write_text("revised scoring rules\n")
    if rewrite:
        archived.write_text(json.dumps({"metadata": {}, "score": 2}) + "\n")
    git("add", ".")
    git("commit", "-qm", "Archive the score and revise the agent")
    archive_commit = git("rev-parse", "HEAD")

    entry = resolver.resolve("rubric20_semantic")["evaluations"][
        "concatenated/_archive/example_evaluation.json"]
    expected_commit = archive_commit if rewrite else original_commit
    expected_sha = hashlib.sha256(agent.read_bytes()).hexdigest() if rewrite else original_sha
    assert entry["basis"] == "recovered_from_commit"
    assert entry["recovered_from"] == expected_commit[:8]
    assert entry["instrument_sha256"] == expected_sha
