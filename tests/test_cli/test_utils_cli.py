#!/usr/bin/env python3
"""
CLI tests for d4d utils commands.
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


class TestUtilsCLI(unittest.TestCase):
    """Test utils CLI behavior."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.runner = CliRunner()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_status_quick_reports_counts_from_working_tree(self):
        raw_dir = self.test_path / "data" / "raw" / "AI_READI"
        raw_dir.mkdir(parents=True)
        (raw_dir / "a.txt").write_text("a", encoding="utf-8")
        (raw_dir / "b.txt").write_text("b", encoding="utf-8")

        result = self.runner.invoke(cli, ["utils", "status", "--quick"], catch_exceptions=False)

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("D4D Pipeline Status (Compact)", result.output)

    def test_validate_preprocessing_forwards_expected_arguments(self):
        captured_argv = []

        def fake_main():
            captured_argv.append(list(sys.argv))

        fake_modules = build_module_tree("src.download.validate_preprocessing_quality", main=fake_main)

        with patch("data_sheets_schema.cli.utils.require_repo_context"), \
             patch("data_sheets_schema.cli.utils.setup_repo_imports"), \
             patch.dict(sys.modules, fake_modules):
            original_argv = list(sys.argv)
            result = self.runner.invoke(
                cli,
                [
                    "utils",
                    "validate-preprocessing",
                    "--raw-dir",
                    str(self.test_path / "raw"),
                    "--preprocessed-dir",
                    str(self.test_path / "preprocessed"),
                    "--project",
                    "CM4AI",
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertEqual(
            captured_argv,
            [[
                "validate_preprocessing_quality.py",
                "--raw-dir",
                str(self.test_path / "raw"),
                "--preprocessed-dir",
                str(self.test_path / "preprocessed"),
                "--project",
                "CM4AI",
            ]],
        )
        self.assertEqual(sys.argv, original_argv)


if __name__ == "__main__":
    unittest.main()
