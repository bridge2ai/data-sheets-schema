#!/usr/bin/env python3
"""
CLI tests for d4d schema commands.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from data_sheets_schema.cli import cli
from data_sheets_schema.cli.schema import VALIDATE_TIMEOUT_SECONDS
from data_sheets_schema.constants import SCHEMA_FULL_PATH
from data_sheets_schema.resources import linkml_validate
from tests.test_cli._helpers import build_module_tree


def recording_subprocess_run(calls, fake=None):
    """Patch `subprocess.run` to append each call's `(command, timeout)` to *calls*.

    *fake* answers the call when given; otherwise the call runs as it would
    have. The tests that reach the real validator used to widen its timeout
    here to 300 s (#4065); that is the command's own bound now (#4188).
    """
    run = subprocess.run

    def recording(command, *args, **kwargs):
        calls.append(([str(part) for part in command], kwargs.get("timeout")))
        return (fake or run)(command, *args, **kwargs)

    return patch("subprocess.run", recording)


def validator_call(d4d_file, schema_file=SCHEMA_FULL_PATH):
    """The one call `d4d schema validate` makes: this interpreter's linkml-validate (#4188)."""
    return ([*linkml_validate(), "-s", str(schema_file), "-C", "Dataset", str(d4d_file)],
            VALIDATE_TIMEOUT_SECONDS)


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

    def invoke_validate_answered_by(self, fake):
        """`d4d schema validate --schema-file`, linkml-validate's answer faked."""
        calls = []
        with patch("data_sheets_schema.cli.schema.require_repo_context"), \
             recording_subprocess_run(calls, fake):
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
        self.assertEqual(calls, [validator_call(self.d4d_file, self.schema_file)], msg=result.output)
        return result

    def test_validate_reports_success(self):
        result = self.invoke_validate_answered_by(
            lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "No issues found\n", ""))
        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("is valid", result.output)

    def test_validate_reports_failures_and_exits_nonzero(self):
        """Both of linkml-validate's streams are the diagnostic."""
        result = self.invoke_validate_answered_by(
            lambda command, **kwargs: subprocess.CompletedProcess(
                command, 1, "missing required field\n", "bad enum value\n"))
        self.assertEqual(result.exit_code, 1, msg=result.output)
        self.assertIn("validation errors", result.output)
        self.assertIn("missing required field", result.output)
        self.assertIn("bad enum value", result.output)

    def test_a_validator_that_does_not_finish_is_reported_with_its_bound(self):
        """The legacy script's message said 30s whatever bound it ran under (#4188)."""
        def hangs(command, **kwargs):
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        result = self.invoke_validate_answered_by(hangs)
        self.assertEqual(result.exit_code, 1, msg=result.output)
        self.assertIn(f"has validation errors:\nValidation timeout ({VALIDATE_TIMEOUT_SECONDS}s)\n",
                      result.output)
        self.assertNotIn("Traceback", result.output)

    def invoke_real_validator(self):
        """Run `d4d schema validate` through the real validator.

        A `poetry` and a `linkml-validate` that would answer "valid" sit first
        on PATH and record any call: the verdict must not depend on the
        caller's PATH (#4188). The streams are kept apart so the diagnostic is
        read where the command prints it.
        """
        decoys = self.test_path / "decoys"
        decoys.mkdir()
        ran = decoys / "ran"
        for name in ("poetry", "linkml-validate"):
            decoy = decoys / name
            decoy.write_text(f'#!/bin/sh\necho "$0 $*" >> "{ran}"\n', encoding="utf-8")
            decoy.chmod(0o755)
        calls = []
        with recording_subprocess_run(calls):
            result = CliRunner(mix_stderr=False).invoke(
                cli, ["schema", "validate", str(self.d4d_file)],
                env={"PATH": f"{decoys}{os.pathsep}{os.environ.get('PATH', '')}"})
        self.assertFalse(ran.exists(), msg=f"a PATH decoy ran: {ran.read_text() if ran.exists() else ''}")
        self.assertEqual(calls, [validator_call(self.d4d_file)], msg=result.stdout + result.stderr)
        return result

    def test_validate_reaches_the_real_validator(self):
        """A fake with the CLI's invented method hid #1024."""
        self.d4d_file.write_text(
            "id: https://example.org/datasets/cli-test\nname: CLI test\n",
            encoding="utf-8",
        )
        result = self.invoke_real_validator()
        self.assertEqual(result.exit_code, 0, msg=result.stdout + result.stderr)
        self.assertEqual(result.stdout, f"✓ Validating {self.d4d_file}...\n✓ {self.d4d_file} is valid!\n")

    def test_real_validation_failure_preserves_the_diagnostic(self):
        """The diagnostic itself, where the command prints it: "id" alone was
        satisfied by the word "Validating" (#4189)."""
        self.d4d_file.write_text("name: Missing identifier\n", encoding="utf-8")
        result = self.invoke_real_validator()
        self.assertEqual(result.exit_code, 1, msg=result.stdout + result.stderr)
        self.assertEqual(result.stdout, f"✓ Validating {self.d4d_file}...\n")
        self.assertIn(f"❌ {self.d4d_file} has validation errors:\n"
                      f"[ERROR] [{self.d4d_file}/0] 'id' is a required property in /\n", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
