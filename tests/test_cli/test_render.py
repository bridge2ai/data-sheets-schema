#!/usr/bin/env python3
"""
CLI tests for d4d render commands.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

from click.testing import CliRunner
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from data_sheets_schema.cli import cli


class TestRenderCLI(unittest.TestCase):
    """Test single-file HTML rendering through the CLI."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.input_file = self.test_path / "sample_d4d.yaml"
        self.output_file = self.test_path / "rendered" / "sample.html"
        self.runner = CliRunner()

        sample_data = {
            "DatasetCollection": {
                "resources": [
                    {
                        "title": "Sample Dataset",
                        "description": "A compact test datasheet."
                    }
                ]
            },
            "license": "CC-BY-4.0",
            "version": "1.0"
        }
        self.input_file.write_text(yaml.safe_dump(sample_data), encoding="utf-8")
        self.linkml_output_file = self.test_path / "rendered" / "sample_linkml.html"
        self.evaluation_json = self.test_path / "evaluation.json"
        self.evaluation20_json = self.test_path / "evaluation20.json"
        self.named_evaluation_json = self.test_path / "AI_READI_claudecode_agent_evaluation.json"
        self.named_evaluation20_dir = self.test_path / "rubric20"
        self.named_evaluation20_dir.mkdir()
        self.named_evaluation20_json = self.named_evaluation20_dir / "CM4AI_claudecode_agent_evaluation.json"
        self.evaluation_output = self.test_path / "rendered" / "evaluation.html"
        self.evaluation20_output = self.test_path / "rendered" / "evaluation20.html"

        rubric10_eval = {
            "evaluation_metadata": {
                "dataset_id": "Sample Dataset",
                "method": "claudecode_agent"
            },
            "element_scores": [
                {
                    "element": "Documentation Quality",
                    "score": 4,
                    "max_score": 5,
                    "sub_elements": []
                }
            ],
            "summary_scores": {
                "total_score": 4,
                "total_max_score": 5,
                "overall_percentage": 80
            },
            "semantic_analysis": {},
            "recommendations": {}
        }
        self.evaluation_json.write_text(json.dumps(rubric10_eval), encoding="utf-8")
        self.named_evaluation_json.write_text(json.dumps(rubric10_eval), encoding="utf-8")

        rubric20_eval = {
            "rubric": "rubric20",
            "project": "Sample Dataset",
            "method": "claudecode_agent",
            "evaluation_timestamp": "2026-01-01T00:00:00",
            "model": {"name": "test-model", "temperature": "N/A"},
            "overall_score": {"total_points": 10, "max_points": 20, "percentage": 50},
            "categories": {
                "Structural Completeness": {
                    "name": "Structural Completeness",
                    "questions": [
                        {
                            "id": 1,
                            "name": "Field Completeness",
                            "description": "Test question",
                            "score": 3,
                            "max_score": 5,
                            "score_type": "numeric",
                            "quality_note": "Adequate",
                            "evidence": "Test evidence",
                        }
                    ],
                }
            },
            "semantic_analysis": {},
        }
        self.evaluation20_json.write_text(json.dumps(rubric20_eval), encoding="utf-8")
        self.named_evaluation20_json.write_text(json.dumps(rubric20_eval), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_render_html_honors_output_path_and_copies_css(self):
        result = self.runner.invoke(
            cli,
            ["render", "html", str(self.input_file), "-o", str(self.output_file)],
        )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(self.output_file.exists(), msg=result.output)

        html = self.output_file.read_text(encoding="utf-8")
        self.assertIn("Sample Dataset", html)
        self.assertIn("datasheet-common.css", html)

        css_file = self.output_file.parent / "datasheet-common.css"
        self.assertTrue(css_file.exists(), msg=result.output)
        self.assertIn("HTML saved to", result.output)
        self.assertIn("Stylesheet saved to", result.output)

    def test_render_linkml_honors_output_path(self):
        result = self.runner.invoke(
            cli,
            [
                "render", "html", str(self.input_file),
                "--template", "linkml",
                "-o", str(self.linkml_output_file),
            ],
        )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(self.linkml_output_file.exists(), msg=result.output)

        html = self.linkml_output_file.read_text(encoding="utf-8")
        self.assertIn("Sample Dataset", html)
        self.assertIn("Generated using Bridge2AI Data Sheets Schema", html)
        self.assertIn("LinkML HTML saved to", result.output)

    def test_render_evaluation_command_auto_detects_rubric10(self):
        result = self.runner.invoke(
            cli,
            [
                "render", "evaluation", str(self.evaluation_json),
                "-o", str(self.evaluation_output),
            ],
        )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(self.evaluation_output.exists(), msg=result.output)

        html = self.evaluation_output.read_text(encoding="utf-8")
        self.assertIn("Rubric10-Semantic Evaluation", html)
        self.assertIn("Sample Dataset", html)
        self.assertIn("(rubric10)", result.output)

    def test_render_html_template_evaluation_delegates_to_evaluation_renderer(self):
        output_file = self.test_path / "rendered" / "evaluation_via_html.html"
        result = self.runner.invoke(
            cli,
            [
                "render", "html", str(self.evaluation_json),
                "--template", "evaluation",
                "-o", str(output_file),
            ],
        )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(output_file.exists(), msg=result.output)
        self.assertIn("(rubric10)", result.output)

    def test_render_html_template_evaluation_defaults_to_canonical_output_name(self):
        result = self.runner.invoke(
            cli,
            [
                "render", "html", str(self.named_evaluation_json),
                "--template", "evaluation",
            ],
        )

        expected_output = self.test_path / "AI_READI_evaluation.html"
        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(expected_output.exists(), msg=result.output)
        self.assertIn(str(expected_output), result.output)
        self.assertIn("(rubric10)", result.output)

    def test_render_evaluation_command_renders_rubric20_category_dict(self):
        result = self.runner.invoke(
            cli,
            [
                "render", "evaluation", str(self.evaluation20_json),
                "-o", str(self.evaluation20_output),
            ],
        )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(self.evaluation20_output.exists(), msg=result.output)

        html = self.evaluation20_output.read_text(encoding="utf-8")
        self.assertIn("Rubric20-Semantic Evaluation", html)
        self.assertIn("Structural Completeness", html)
        self.assertIn("(rubric20)", result.output)

    def test_render_evaluation_command_defaults_to_canonical_rubric10_output_name(self):
        result = self.runner.invoke(
            cli,
            ["render", "evaluation", str(self.named_evaluation_json)],
        )

        expected_output = self.test_path / "AI_READI_evaluation.html"
        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(expected_output.exists(), msg=result.output)
        self.assertIn(str(expected_output), result.output)
        self.assertFalse((self.test_path / "AI_READI_claudecode_agent_evaluation.html").exists())
        self.assertIn("(rubric10)", result.output)

    def test_render_evaluation_command_defaults_to_canonical_rubric20_output_name(self):
        result = self.runner.invoke(
            cli,
            ["render", "evaluation", str(self.named_evaluation20_json)],
        )

        expected_output = self.named_evaluation20_dir / "CM4AI_evaluation_rubric20.html"
        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(expected_output.exists(), msg=result.output)
        self.assertIn(str(expected_output), result.output)
        self.assertFalse((self.named_evaluation20_dir / "CM4AI_claudecode_agent_evaluation.html").exists())
        self.assertIn("(rubric20)", result.output)


if __name__ == "__main__":
    unittest.main()
