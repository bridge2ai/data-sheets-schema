#!/usr/bin/env python3
"""
CLI tests for d4d download commands.
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


class TestDownloadCLI(unittest.TestCase):
    """Test download CLI wrappers."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.runner = CliRunner()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_sources_forwards_expected_arguments(self):
        captured_argv = []

        def fake_main():
            captured_argv.append(list(sys.argv))

        fake_modules = build_module_tree("src.download.organized_dataset_extractor", main=fake_main)

        with patch.dict(sys.modules, fake_modules):
            original_argv = list(sys.argv)
            result = self.runner.invoke(
                cli,
                [
                    "download",
                    "sources",
                    "--project",
                    "AI_READI",
                    "--output-dir",
                    str(self.test_path / "raw"),
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertEqual(
            captured_argv,
            [[
                "organized_dataset_extractor.py",
                "--output-dir",
                str(self.test_path / "raw"),
                "--projects",
                "AI_READI",
            ]],
        )
        self.assertEqual(sys.argv, original_argv)
        self.assertIn("Downloaded AI_READI sources", result.output)

    def test_preprocess_forwards_expected_arguments(self):
        captured_argv = []

        def fake_main():
            captured_argv.append(list(sys.argv))

        fake_modules = build_module_tree("src.download.preprocess_sources", main=fake_main)

        with patch("data_sheets_schema.cli.download.require_repo_context"), \
             patch("data_sheets_schema.cli.download.setup_repo_imports"), \
             patch.dict(sys.modules, fake_modules):
            original_argv = list(sys.argv)
            result = self.runner.invoke(
                cli,
                [
                    "download",
                    "preprocess",
                    "--project",
                    "CHORUS",
                    "--input-dir",
                    str(self.test_path / "raw"),
                    "--output-dir",
                    str(self.test_path / "preprocessed"),
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertEqual(
            captured_argv,
            [[
                "preprocess_sources.py",
                "-i",
                str(self.test_path / "raw"),
                "-o",
                str(self.test_path / "preprocessed"),
                "-p",
                "CHORUS",
            ]],
        )
        self.assertEqual(sys.argv, original_argv)
        self.assertIn("Preprocessed files saved", result.output)

    def test_concatenate_forwards_expected_arguments(self):
        captured_argv = []
        input_dir = self.test_path / "preprocessed"
        project_dir = input_dir / "VOICE"
        project_dir.mkdir(parents=True)

        def fake_main():
            captured_argv.append(list(sys.argv))

        fake_modules = build_module_tree("src.download.concatenate_documents", main=fake_main)

        with patch.dict(sys.modules, fake_modules):
            original_argv = list(sys.argv)
            result = self.runner.invoke(
                cli,
                [
                    "download",
                    "concatenate",
                    "--project",
                    "VOICE",
                    "--input-dir",
                    str(input_dir),
                    "--output-file",
                    str(self.test_path / "VOICE.txt"),
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertEqual(
            captured_argv,
            [[
                "concatenate_documents.py",
                "-i",
                str(project_dir),
                "-o",
                str(self.test_path / "VOICE.txt"),
            ]],
        )
        self.assertEqual(sys.argv, original_argv)
        self.assertIn("Concatenated file saved", result.output)


if __name__ == "__main__":
    unittest.main()
