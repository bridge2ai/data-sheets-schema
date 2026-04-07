#!/usr/bin/env python3
"""
CLI tests for d4d rocrate commands.
"""

import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from data_sheets_schema.cli import cli
from tests.test_cli._helpers import build_module_tree


class TestROCrateCLI(unittest.TestCase):
    """Test RO-Crate CLI behavior."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.runner = CliRunner()

        self.input_a = self.test_path / "a.json"
        self.input_b = self.test_path / "b.json"
        self.input_a.write_text("{}", encoding="utf-8")
        self.input_b.write_text("{}", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_transform_merge_mode_accepts_inputs_without_positional_input_file(self):
        fake_module = types.SimpleNamespace(main=lambda: None)

        with patch("data_sheets_schema.cli.rocrate.require_repo_context"), \
             patch("data_sheets_schema.cli.rocrate.setup_repo_imports"), \
             patch.dict(sys.modules, {"rocrate_to_d4d": fake_module}):
            result = self.runner.invoke(
                cli,
                [
                    "rocrate",
                    "transform",
                    "--merge",
                    "--inputs",
                    str(self.input_a),
                    "--inputs",
                    str(self.input_b),
                    "-o",
                    str(self.test_path / "output.yaml"),
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("merge mode", result.output)
        self.assertIn("D4D YAML saved to", result.output)

    def test_transform_single_file_mode_still_requires_input_file(self):
        result = self.runner.invoke(
            cli,
            [
                "rocrate",
                "transform",
                "-o",
                str(self.test_path / "output.yaml"),
            ],
        )

        self.assertEqual(result.exit_code, 2, msg=result.output)
        self.assertIn("Missing argument 'INPUT_FILE'", result.output)

    def test_parse_writes_json_output(self):
        class FakeParser:
            def __init__(self, input_file):
                self.input_file = input_file

            def get_all_entities(self):
                return {"dataset": {"@type": "Dataset"}}

        fake_modules = build_module_tree("rocrate_parser", ROCrateParser=FakeParser)
        output_file = self.test_path / "parsed.json"

        with patch("data_sheets_schema.cli.rocrate.require_repo_context"), \
             patch("data_sheets_schema.cli.rocrate.setup_repo_imports"), \
             patch.dict(sys.modules, fake_modules):
            result = self.runner.invoke(
                cli,
                ["rocrate", "parse", str(self.input_a), "--output", str(output_file)],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(output_file.exists(), msg=result.output)
        self.assertIn("Parsed 1 entities", result.output)

    def test_merge_invokes_merger_with_primary_marker(self):
        calls = []

        class FakeMerger:
            def add_rocrate(self, input_file, is_primary=False):
                calls.append(("add", input_file, is_primary))

            def merge(self):
                calls.append(("merge",))
                return {"merged": True}

        fake_modules = build_module_tree("rocrate_merger", ROCrateMerger=FakeMerger)
        output_file = self.test_path / "merged.json"

        with patch("data_sheets_schema.cli.rocrate.require_repo_context"), \
             patch("data_sheets_schema.cli.rocrate.setup_repo_imports"), \
             patch.dict(sys.modules, fake_modules):
            result = self.runner.invoke(
                cli,
                [
                    "rocrate",
                    "merge",
                    str(self.input_a),
                    str(self.input_b),
                    "--primary",
                    str(self.input_b),
                    "-o",
                    str(output_file),
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(output_file.exists(), msg=result.output)
        self.assertEqual(
            calls,
            [
                ("add", str(self.input_a), False),
                ("add", str(self.input_b), True),
                ("merge",),
            ],
        )
        self.assertIn("Merged RO-Crate saved", result.output)


if __name__ == "__main__":
    unittest.main()
