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


@pytest.mark.parametrize("repository_valid", [False, True])
@pytest.mark.parametrize("explicit_file", [False, True])
def test_legacy_validator_selects_the_intended_corpus(
    tmp_path, repository_valid, explicit_file
):
    repository = tmp_path / "repository"
    caller = tmp_path / "caller"
    script = repository / "scripts/validate_evaluation_schema.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/validate_evaluation_schema.py", script)
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
