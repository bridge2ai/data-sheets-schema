"""The documented source commands still render their legacy batch layouts."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("style", ["human", "linkml", "rubric10", "rubric20"])
def test_source_renderer_command_writes_html(style, tmp_path):
    if style in ("human", "linkml"):
        name = "clinical_data" if style == "human" else "clinical"
        source = tmp_path / ("data/sheets/html_output" if style == "human" else "data/sheets") / f"{name}.yaml"
        source.parent.mkdir(parents=True)
        source.write_text("id: https://example.org/clinical\ntitle: Clinical fixture\nname: clinical\ndescription: Synthetic test.\n")
        script = "src/html/" + ("human_readable_renderer.py" if style == "human" else "process_text_files.py")
        destination = tmp_path / ("src/html/output" if style == "human" else "data/sheets/html_output")
    else:
        source = tmp_path / f"data/evaluation_llm/{style}_semantic/concatenated/CLINICAL_claudecode_agent_evaluation.json"
        source.parent.mkdir(parents=True)
        source.write_text(json.dumps({
            "rubric": style, "project": "Clinical fixture", "method": "claudecode_agent",
            "elements" if style == "rubric10" else "categories": [],
            "overall_score": {"total_points": 0, "max_points": 50 if style == "rubric10" else 88,
                              "percentage": 0}, "semantic_analysis": {}}))
        script = f"scripts/render_evaluation_html_{style}_semantic.py"
        destination = tmp_path / "data/d4d_html/concatenated/claudecode_agent"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, str(ROOT / script)], cwd=tmp_path,
                            env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    rendered = list(destination.glob("*.html"))
    assert len(rendered) == 1, result.stdout + result.stderr
    assert "Clinical fixture" in rendered[0].read_text()
