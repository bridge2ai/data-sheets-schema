#!/usr/bin/env python3
"""Tests for `d4d validate` and the instance_lint library.

Fast hermetic tests use a tiny synthetic LinkML schema; one integration
test exercises the real D4D core schema.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from data_sheets_schema.cli import cli  # noqa: E402
from data_sheets_schema import instance_lint  # noqa: E402

SYNTHETIC_SCHEMA = """\
id: https://example.org/test-datasheet-schema
name: test-datasheet-schema
title: Test datasheet schema
prefixes:
  ex: https://example.org/
  linkml: https://w3id.org/linkml/
default_range: string
classes:
  TestDataset:
    attributes:
      title:
        required: true
      description:
      count:
        range: integer
      released:
        range: date
      tags:
        multivalued: true
      contact:
        range: Contact
  Contact:
    attributes:
      name:
      email:
"""


class ValidateCLITestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.schema = self.root / "schema.yaml"
        self.schema.write_text(SYNTHETIC_SCHEMA, encoding="utf-8")
        self.runner = CliRunner()
        self.base_args = [
            "--schema-file", str(self.schema),
            "--target-class", "TestDataset",
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, text):
        p = self.root / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def _invoke(self, *args):
        return self.runner.invoke(cli, ["validate", *self.base_args, *args])

    def test_valid_instance_exits_zero(self):
        f = self._write("ok.yaml", "title: My dataset\ndescription: A fine dataset.\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("VALID", result.output)

    def test_missing_required_field_is_error(self):
        f = self._write("bad.yaml", "description: No title here.\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("INVALID", result.output)
        self.assertIn("schema-violation", result.output)

    def test_wrong_type_is_error(self):
        f = self._write("bad.yaml", "title: T\ncount: not-a-number\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("type-mismatch", result.output)

    def test_unknown_field_is_error_with_hint(self):
        f = self._write("typo.yaml", "title: T\ntitel: typo\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("INVALID", result.output)
        self.assertIn("unknown-field", result.output)
        self.assertIn("did you mean 'title'", result.output)

    def test_fail_on_warning_turns_lint_into_failure(self):
        f = self._write("ph.yaml", "title: T\ndescription: TBD\n")
        result = self._invoke("--fail-on-warning", f)
        self.assertEqual(result.exit_code, 1, result.output)

    def test_placeholder_value_warns(self):
        f = self._write("ph.yaml", "title: T\ndescription: TBD\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("placeholder-value", result.output)

    def test_empty_value_warns(self):
        f = self._write("empty.yaml", "title: T\ndescription: ''\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("empty-value", result.output)

    def test_nested_unknown_field_reports_path(self):
        f = self._write("nested.yaml",
                        "title: T\ncontact:\n  naem: Ada\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("unknown-field", result.output)
        self.assertIn("/contact/naem", result.output)

    def test_scalar_type_mismatch_is_error(self):
        # linkml's own validator misses scalar coercion problems, even
        # `linkml-validate`; the linter catches them.
        f = self._write("types.yaml",
                        "title: T\ncount: not-a-number\nreleased: not-a-date\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("type-mismatch", result.output)
        self.assertIn("/count", result.output)
        self.assertIn("/released", result.output)

    def test_scalar_types_accept_valid_values(self):
        f = self._write("types.yaml",
                        "title: T\ncount: 42\nreleased: 2026-09-28\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("type-mismatch", result.output)

    def test_british_spelling_warns(self):
        f = self._write("gb.yaml",
                        "title: T\ndescription: The data was organised by colour.\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("british-spelling", result.output)

    def test_missing_file_exits_two(self):
        result = self._invoke(str(self.root / "nope.yaml"))
        self.assertEqual(result.exit_code, 2)

    def test_bad_target_class_exits_two(self):
        f = self._write("ok.yaml", "title: T\n")
        result = self.runner.invoke(
            cli, ["validate", "--schema-file", str(self.schema),
                  "--target-class", "NoSuchClass", f])
        self.assertEqual(result.exit_code, 2, result.output)

    def test_json_format_is_machine_readable(self):
        f = self._write("ok.yaml", "title: T\ndescription: TBD\n")
        result = self._invoke("--format", "json", f)
        self.assertEqual(result.exit_code, 0, result.output)
        payload = json.loads(result.output)
        self.assertEqual(len(payload), 1)
        report = payload[0]
        for key in ("file", "schema", "target_class", "valid",
                    "summary", "issues", "sections"):
            self.assertIn(key, report)
        codes = {i["code"] for i in report["issues"]}
        self.assertIn("placeholder-value", codes)
        self.assertIn("completeness", report["summary"])

    def test_output_file(self):
        f = self._write("ok.yaml", "title: T\n")
        out = str(self.root / "report.json")
        result = self._invoke("--format", "json", "--output", out, f)
        self.assertEqual(result.exit_code, 0, result.output)
        payload = json.loads(Path(out).read_text(encoding="utf-8"))
        self.assertTrue(payload[0]["valid"])

    def test_multiple_files_summary(self):
        good = self._write("good.yaml", "title: T\n")
        bad = self._write("bad.yaml", "count: 1\n")
        result = self._invoke(good, bad)
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("2 files: 1 valid, 1 invalid", result.output)

    def test_quiet_prints_only_summary(self):
        f = self._write("ph.yaml", "title: T\ndescription: TBD\n")
        result = self._invoke("--quiet", f)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("placeholder-value", result.output)
        self.assertIn("VALID", result.output)

    def test_json_instance_supported(self):
        f = self._write("ok.json", json.dumps({"title": "T"}))
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("VALID", result.output)

    def test_unparseable_file_is_error(self):
        f = self._write("broken.yaml", "title: [unclosed\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("unparseable", result.output)


class InstanceLintLibraryTestCase(unittest.TestCase):
    def test_report_to_dict_is_json_serialisable(self):
        report = instance_lint.LintReport(
            file="x.yaml", schema="s.yaml", target_class="C", valid=True,
            issues=[instance_lint.Issue("warning", "empty-section", "/",
                                        "empty")],
            sections=[instance_lint.SectionCoverage("Motivation", 4, 2)],
        )
        payload = json.loads(json.dumps(report.to_dict()))
        self.assertEqual(payload["summary"]["completeness"], 50)
        self.assertEqual(payload["summary"]["warnings"], 1)


class ValidateCoreIntegrationTestCase(unittest.TestCase):
    """One end-to-end run against the real D4D core schema."""

    def test_minimal_core_datasheet_validates(self):
        repo_root = Path(__file__).parent.parent.parent
        schema = (repo_root / "src" / "data_sheets_schema" / "schema"
                  / "data_sheets_schema_core_all.yaml")
        self.assertTrue(schema.exists(), f"core schema missing: {schema}")
        with tempfile.TemporaryDirectory() as tmp:
            inst = Path(tmp) / "mini.yaml"
            inst.write_text(
                "id: https://example.org/datasets/mini\n"
                "name: mini\n"
                "title: Minimal test datasheet\n"
                "description: A minimal datasheet for the integration test.\n",
                encoding="utf-8",
            )
            report = instance_lint.lint_file(str(inst), str(schema),
                                             "CoreDataset")
        self.assertTrue(report.valid, report.to_dict()["issues"])
        self.assertGreater(len(report.sections), 3)
        self.assertIn("Motivation", [s.name for s in report.sections])


if __name__ == "__main__":
    unittest.main()
