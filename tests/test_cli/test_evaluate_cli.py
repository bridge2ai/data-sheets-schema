#!/usr/bin/env python3
"""
CLI tests for d4d evaluate commands.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from data_sheets_schema.cli import cli
from tests.test_cli._helpers import build_module_tree


class TestEvaluateCLI(unittest.TestCase):
    """Test evaluate CLI wrappers."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.runner = CliRunner()
        self.input_file = self.test_path / "sample.yaml"
        self.input_file.write_text("DatasetCollection: {}\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_presence_forwards_expected_arguments(self):
        captured_argv = []

        def fake_main():
            captured_argv.append(list(sys.argv))

        fake_modules = build_module_tree("src.evaluation.evaluate_d4d", main=fake_main)

        with patch("data_sheets_schema.cli.evaluate.require_repo_context"), \
             patch("data_sheets_schema.cli.evaluate.setup_repo_imports"), \
             patch.dict(sys.modules, fake_modules):
            original_argv = list(sys.argv)
            result = self.runner.invoke(
                cli,
                [
                    "evaluate",
                    "presence",
                    "--project",
                    "AI_READI",
                    "--method",
                    "claudecode_agent",
                    "--output-dir",
                    str(self.test_path / "reports"),
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertEqual(
            captured_argv,
            [[
                "evaluate_d4d.py",
                "--methods",
                "claudecode_agent",
                "--output-dir",
                str(self.test_path / "reports"),
                "--project",
                "AI_READI",
            ]],
        )
        self.assertEqual(sys.argv, original_argv)
        self.assertIn("Evaluation complete", result.output)

    def test_llm_forwards_expected_arguments(self):
        captured_argv = []

        def fake_main():
            captured_argv.append(list(sys.argv))

        fake_modules = build_module_tree("src.evaluation.evaluate_d4d_llm", main=fake_main)

        with patch("data_sheets_schema.cli.evaluate.require_repo_context"), \
             patch("data_sheets_schema.cli.evaluate.setup_repo_imports"), \
             patch.dict(sys.modules, fake_modules):
            original_argv = list(sys.argv)
            result = self.runner.invoke(
                cli,
                [
                    "evaluate",
                    "llm",
                    "--file",
                    str(self.input_file),
                    "--project",
                    "AI_READI",
                    "--method",
                    "claudecode_agent",
                    "--rubric",
                    "rubric20",
                    "--output-dir",
                    str(self.test_path / "llm_reports"),
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertEqual(
            captured_argv,
            [[
                "evaluate_d4d_llm.py",
                "--file",
                str(self.input_file),
                "--project",
                "AI_READI",
                "--method",
                "claudecode_agent",
                "--rubric",
                "rubric20",
                "--output-dir",
                str(self.test_path / "llm_reports"),
            ]],
        )
        self.assertEqual(sys.argv, original_argv)
        self.assertIn("LLM evaluation complete", result.output)

    def test_llm_reports_missing_backend_module_cleanly(self):
        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "src.evaluation.evaluate_d4d_llm":
                raise ImportError("missing llm backend")
            return original_import(name, globals, locals, fromlist, level)

        original_import = __import__

        with patch("data_sheets_schema.cli.evaluate.require_repo_context"), \
             patch("data_sheets_schema.cli.evaluate.setup_repo_imports"), \
             patch("builtins.__import__", side_effect=fake_import):
            result = self.runner.invoke(
                cli,
                [
                    "evaluate",
                    "llm",
                    "--file",
                    str(self.input_file),
                    "--project",
                    "AI_READI",
                    "--method",
                    "claudecode_agent",
                ],
            )

        self.assertEqual(result.exit_code, 1, msg=result.output)
        self.assertIn("LLM evaluation script not found", result.output)


if __name__ == "__main__":
    unittest.main()
