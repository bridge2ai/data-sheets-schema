#!/usr/bin/env python3
"""
CLI tests for d4d schema commands.
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


class TestSchemaCLI(unittest.TestCase):
    """Test schema CLI wrappers."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.runner = CliRunner()
        self.d4d_file = self.test_path / "sample.yaml"
        self.schema_file = self.test_path / "schema.yaml"
        self.d4d_file.write_text("DatasetCollection: {}\n", encoding="utf-8")
        self.schema_file.write_text("id: test\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_stats_forwards_expected_arguments(self):
        captured_argv = []

        def fake_main():
            captured_argv.append(list(sys.argv))

        fake_modules = build_module_tree("schema_stats", main=fake_main)

        with patch("data_sheets_schema.cli.schema.require_repo_context"), \
             patch("data_sheets_schema.cli.schema.setup_repo_imports"), \
             patch.dict(sys.modules, fake_modules):
            original_argv = list(sys.argv)
            result = self.runner.invoke(
                cli,
                [
                    "schema",
                    "stats",
                    "--level",
                    "3",
                    "--format",
                    "json",
                    "--output",
                    str(self.test_path / "stats.json"),
                    "--schema-file",
                    str(self.schema_file),
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertEqual(
            captured_argv,
            [[
                "schema_stats.py",
                "--level",
                "3",
                "--format",
                "json",
                "--output",
                str(self.test_path / "stats.json"),
                "--schema",
                str(self.schema_file),
            ]],
        )
        self.assertEqual(sys.argv, original_argv)
        self.assertIn("Statistics saved to", result.output)

    def test_validate_reports_success(self):
        class FakeValidator:
            def __init__(self, schema_file):
                self.schema_file = schema_file

            def validate_file(self, d4d_file):
                return True, []

        fake_modules = build_module_tree("validator", D4DValidator=FakeValidator)

        with patch("data_sheets_schema.cli.schema.require_repo_context"), \
             patch("data_sheets_schema.cli.schema.setup_repo_imports"), \
             patch.dict(sys.modules, fake_modules):
            result = self.runner.invoke(
                cli,
                [
                    "schema",
                    "validate",
                    str(self.d4d_file),
                    "--schema-file",
                    str(self.schema_file),
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("is valid", result.output)

    def test_validate_reports_failures_and_exits_nonzero(self):
        class FakeValidator:
            def __init__(self, schema_file):
                self.schema_file = schema_file

            def validate_file(self, d4d_file):
                return False, ["missing required field", "bad enum value"]

        fake_modules = build_module_tree("validator", D4DValidator=FakeValidator)

        with patch("data_sheets_schema.cli.schema.require_repo_context"), \
             patch("data_sheets_schema.cli.schema.setup_repo_imports"), \
             patch.dict(sys.modules, fake_modules):
            result = self.runner.invoke(
                cli,
                [
                    "schema",
                    "validate",
                    str(self.d4d_file),
                    "--schema-file",
                    str(self.schema_file),
                ],
            )

        self.assertEqual(result.exit_code, 1, msg=result.output)
        self.assertIn("validation errors", result.output)
        self.assertIn("missing required field", result.output)
        self.assertIn("bad enum value", result.output)


if __name__ == "__main__":
    unittest.main()
