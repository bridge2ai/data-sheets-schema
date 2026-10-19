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
imports:
  - linkml:types
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
      variable_name:
      source_url:
  Contact:
    attributes:
      name:
      email:
  ExtendedContact:
    is_a: Contact
    attributes:
      department:
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
        self.assertIn("schema-violation", result.output)

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
        f = self._write("types.yaml",
                        "title: T\ncount: not-a-number\nreleased: not-a-date\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("schema-violation", result.output)
        self.assertIn("/count", result.output)

    def test_scalar_types_accept_valid_values(self):
        f = self._write("types.yaml",
                        'title: T\ncount: 42\nreleased: "2026-09-28"\n')
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("schema-violation", result.output)

    def test_british_spelling_warns(self):
        f = self._write("gb.yaml",
                        "title: T\ndescription: The data was organised by colour.\n")
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("british-spelling", result.output)

    def test_british_spelling_respects_quotes_proper_nouns_and_verbatim_slots(self):
        f = self._write(
            "exempt.yaml",
            "title: The World Health Organisation study\n"
            'description: Data from the Temerty Centre with "colour" labels, '
            "Haemophilus cultures, and programme.csv.\n"
            "variable_name: Haemoglobin\n"
            "source_url: https://example.org/programme/colour\n",
        )
        result = self._invoke(f)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("british-spelling", result.output)

    def test_duplicate_yaml_key_is_error(self):
        f = self._write(
            "dup.yaml",
            "title: First\ntitle: Second\ncontact:\n  name: A\n  name: B\n",
        )
        result = self._invoke("--format", "json", f)
        self.assertEqual(result.exit_code, 1, result.output)
        payload = json.loads(result.output)[0]
        self.assertFalse(payload["valid"])
        dup_issues = [i for i in payload["issues"] if i["code"] == "duplicate-key"]
        self.assertEqual({i["path"] for i in dup_issues}, {"/title", "/contact/name"})

    def test_non_string_yaml_keys_reported_cleanly(self):
        f = self._write(
            "non_str_keys.yaml",
            "title: T\n2024: yr\nno: nope\n~: nullkey\n",
        )
        result = self._invoke("--format", "json", f)
        self.assertEqual(result.exit_code, 1, result.output)
        payload = json.loads(result.output)[0]
        unknown_paths = {
            i["path"] for i in payload["issues"] if i["code"] == "unknown-field"
        }
        self.assertEqual(unknown_paths, {"/2024", "/False", "/None"})

    def test_descendant_class_slots_allowed_on_nested_range_not_root(self):
        f_nested = self._write(
            "sub_ok.yaml",
            "title: T\ncontact:\n  name: Ada\n  department: Computing\n",
        )
        res_nested = self._invoke(f_nested)
        self.assertEqual(res_nested.exit_code, 0, res_nested.output)
        self.assertNotIn("unknown-field", res_nested.output)

        f_root = self._write("sub_root.yaml", "title: T\ndepartment: Computing\n")
        res_root = self._invoke(f_root)
        self.assertEqual(res_root.exit_code, 1, res_root.output)
        self.assertIn("unknown-field", res_root.output)

    def test_missing_identifier_only_warns_for_induced_slots(self):
        # TestDataset has title and description, but not 'name'.
        f = self._write("ok.yaml", "title: T\ndescription: D\n")
        result = self._invoke("--format", "json", f)
        self.assertEqual(result.exit_code, 0, result.output)
        payload = json.loads(result.output)[0]
        codes = {i["code"] for i in payload["issues"]}
        self.assertNotIn("missing-identifier", codes)

    def test_schema_core_preserved_with_schema_file(self):
        core_schema = self.root / "core_schema.yaml"
        core_schema.write_text(
            SYNTHETIC_SCHEMA.replace("TestDataset:", "CoreDataset:"),
            encoding="utf-8",
        )
        f = self._write("core_ok.yaml", "title: Core item\ndescription: D\n")
        result = self.runner.invoke(
            cli,
            [
                "validate",
                "--schema", "core",
                "--schema-file", str(core_schema),
                f,
            ],
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("VALID", result.output)

    def test_malformed_schema_exits_two(self):
        bad_schema = self.root / "broken_schema.yaml"
        bad_schema.write_text("not: [valid: schema\n", encoding="utf-8")
        f = self._write("ok.yaml", "title: T\n")
        result = self.runner.invoke(
            cli,
            ["validate", "--schema-file", str(bad_schema), f],
        )
        self.assertEqual(result.exit_code, 2, result.output)
        self.assertIn("Error:", result.output)

    def test_multi_document_yaml_and_root_list_reported(self):
        multi = self._write("multi.yaml", "title: A\n---\ntitle: B\n")
        res_multi = self._invoke(multi)
        self.assertEqual(res_multi.exit_code, 1, res_multi.output)
        self.assertIn("unparseable", res_multi.output)

        root_list = self._write("list.yaml", "- title: A\n")
        res_list = self._invoke(root_list)
        self.assertEqual(res_list.exit_code, 1, res_list.output)
        self.assertIn("not-a-mapping", res_list.output)

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
        for key in ("file", "schema", "schema_sha256", "target_class", "valid",
                    "summary", "issues", "sections"):
            self.assertIn(key, report)
        self.assertEqual(len(report["schema_sha256"]), 64)
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
            schema_sha256="a" * 64,
        )
        payload = json.loads(json.dumps(report.to_dict()))
        self.assertEqual(payload["summary"]["completeness"], 50)
        self.assertEqual(payload["summary"]["warnings"], 1)
        self.assertEqual(payload["schema_sha256"], "a" * 64)

    def test_validator_cached_and_invalidated_on_schema_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            schema = Path(tmp) / "schema.yaml"
            schema.write_text(SYNTHETIC_SCHEMA, encoding="utf-8")
            v1 = instance_lint._validator(str(schema))
            v2 = instance_lint._validator(str(schema))
            self.assertIs(v1, v2)

            # Mutating the schema file invalidates the cache via content sha256.
            schema.write_text(
                SYNTHETIC_SCHEMA.replace(
                    "      source_url:\n", "      source_url:\n      extra_slot:\n"
                ),
                encoding="utf-8",
            )
            v3 = instance_lint._validator(str(schema))
            self.assertIsNot(v1, v3)
            r = instance_lint.lint_instance(
                {"title": "T", "extra_slot": "ok"},
                str(schema),
                "TestDataset",
            )
            self.assertTrue(r.valid, r.to_dict()["issues"])


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
        section_names = [s.name for s in report.sections]
        self.assertIn("Motivation", section_names)
        self.assertIn("Distribution", section_names)

    def test_full_schema_allows_data_subset_slots_under_resources(self):
        repo_root = Path(__file__).parent.parent.parent
        schema = (repo_root / "src" / "data_sheets_schema" / "schema"
                  / "data_sheets_schema_all.yaml")
        report = instance_lint.lint_instance(
            {
                "id": "https://example.org/datasets/full-sub",
                "title": "Dataset with DataSubset resource",
                "description": "Tests polymorphic DataSubset under resources.",
                "resources": [
                    {
                        "id": "https://example.org/datasets/full-sub/split-1",
                        "title": "Train split",
                        "is_data_split": True,
                    }
                ],
            },
            str(schema),
            "Dataset",
        )
        self.assertTrue(report.valid, report.to_dict()["issues"])


if __name__ == "__main__":
    unittest.main()


def test_schema_cache_key_covers_imported_modules(tmp_path):
    """#5082: an edit confined to an imported module changes the instance-lint cache key."""
    from data_sheets_schema import instance_lint
    head = "prefixes: {linkml: https://w3id.org/linkml/}\ndefault_range: string\n"
    (tmp_path / "imp.yaml").write_text("id: https://x/imp\nname: imp\n" + head + "imports: [linkml:types]\nclasses: {A: {}}\n")
    root = tmp_path / "root.yaml"
    root.write_text("id: https://x/root\nname: root\n" + head + "imports: [linkml:types, imp]\nclasses: {R: {}}\n")
    before = instance_lint._cache_key(str(root))
    (tmp_path / "imp.yaml").write_text((tmp_path / "imp.yaml").read_text().replace("A: {}", "A: {}, B: {}"))
    assert instance_lint._cache_key(str(root)) != before
