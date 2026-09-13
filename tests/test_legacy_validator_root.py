"""Legacy batch validation owns the script's corpus, even from another cwd."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from tests.test_evaluation.test_semantic_context_scope import record as semantic_record


ROOT = Path(__file__).resolve().parents[1]


def _stage_script(repository):
    script = repository / "scripts/validate_evaluation_schema.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/validate_evaluation_schema.py", script)
    schemas = repository / "src/download/prompts"
    schemas.mkdir(parents=True)
    for rubric in ("rubric10", "rubric20"):
        name = f"{rubric}_semantic_schema.json"
        shutil.copyfile(ROOT / "src/download/prompts" / name, schemas / name)
    return script


@pytest.mark.parametrize("repository_valid", [False, True])
@pytest.mark.parametrize("explicit_file", [False, True])
def test_legacy_validator_selects_the_intended_corpus(
    tmp_path, repository_valid, explicit_file
):
    repository = tmp_path / "repository"
    caller = tmp_path / "caller"
    script = _stage_script(repository)
    for owner, valid in ((repository, repository_valid), (caller, not repository_valid)):
        evaluation = owner / "data/evaluation_llm/fixture_evaluation.json"
        evaluation.parent.mkdir(parents=True)
        record, _ = semantic_record(owner, "rubric20")
        if not valid:
            record["overall_score"]["max_points"] = -1
        evaluation.write_text(json.dumps(record))

    args = [sys.executable, str(script)]
    if explicit_file:
        args.extend(["--file", "data/evaluation_llm/fixture_evaluation.json",
                     "--input", "external.yaml", "--context", "caller-context.yaml",
                     "--agent-definition", str(ROOT / ".claude/agents/d4d-rubric20-semantic.md")])
    result = subprocess.run(
        args, cwd=caller, capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    expected_valid = not repository_valid if explicit_file else repository_valid
    assert result.returncode == int(not expected_valid), result.stdout + result.stderr
    if not explicit_file:
        assert str(repository / "data/evaluation_llm") in result.stdout


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_legacy_batch_schema_cannot_be_replaced_by_the_caller(tmp_path, rubric):
    repository = tmp_path / "repository"
    script = _stage_script(repository)
    record, _ = semantic_record(repository, rubric)
    record["model"] = {}  # Invalid in the repository's actual semantic schema.
    evaluation = repository / "data/evaluation_llm/fixture_evaluation.json"
    evaluation.parent.mkdir(parents=True)
    evaluation.write_text(json.dumps(record))

    caller = tmp_path / "caller"
    (caller / "src/data_sheets_schema").mkdir(parents=True)
    (caller / "pyproject.toml").write_text('name = "data-sheets-schema"\n')
    schemas = caller / "src/download/prompts"; schemas.mkdir(parents=True)
    rubrics = caller / "data/rubric"; rubrics.mkdir(parents=True)
    for name in ("rubric10", "rubric20"):
        (schemas / f"{name}_semantic_schema.json").write_text("{}")
        shutil.copyfile(ROOT / f"data/rubric/{name}.txt", rubrics / f"{name}.txt")
    result = subprocess.run(
        [sys.executable, str(script)], cwd=caller, capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "model" in result.stdout


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
@pytest.mark.parametrize("absolute_file", [False, True])
@pytest.mark.parametrize("valid", [False, True])
def test_explicit_file_keeps_wrapper_schemas_and_caller_input(tmp_path, rubric, absolute_file, valid):
    repository = tmp_path / "repository"
    script = _stage_script(repository)
    caller = tmp_path / "caller"
    caller.mkdir()
    record, _ = semantic_record(caller, rubric)
    if not valid:
        record["model"] = {}
    evaluation = caller / "assessment.json"
    evaluation.write_text(json.dumps(record))
    (caller / "src/data_sheets_schema").mkdir(parents=True)
    (caller / "pyproject.toml").write_text('name = "data-sheets-schema"\n')
    schemas = caller / "src/download/prompts"
    schemas.mkdir(parents=True)
    rubrics = caller / "data/rubric"
    rubrics.mkdir(parents=True)
    for name in ("rubric10", "rubric20"):
        # Oppose the true result so either use of the caller's schema is visible.
        (schemas / f"{name}_semantic_schema.json").write_text(
            json.dumps({"not": {}} if valid else {}))
        shutil.copyfile(ROOT / f"data/rubric/{name}.txt", rubrics / f"{name}.txt")
    result = subprocess.run(
        [sys.executable, str(script), "--file",
         str(evaluation if absolute_file else evaluation.relative_to(caller)),
         "--input", "external.yaml", "--context", "caller-context.yaml",
         "--agent-definition", str(ROOT / f".claude/agents/d4d-{rubric}-semantic.md")],
        cwd=caller, capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == int(not valid), result.stdout + result.stderr
    if not valid:
        assert "model" in result.stdout
