"""The full and core schemas declare one release identity (#1874).

Through 2026-09-16 the full schema kept `version: 2.0.0` across the
narrative scalarization, Person inlining, DataGovernance, data-standard
vocabulary and anchored-DOI changes, and the core entry point declared no
version at all. Content hashes distinguished the instruments; the human
label did not. 3.0.0 names the definitions as they now stand, the core
declares the same version, the generated artifacts carry it, and the
provenance record states both.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "src" / "data_sheets_schema" / "schema"
CHECKER_SCRIPT = ROOT / "scripts" / "adhoc" / "check_citation_metadata_20261110.py"
RELEASE = "3.2.0"

METADATA_FILES = (
    "CITATION.cff",
    "pyproject.toml",
    "LICENSE",
    "about.yaml",
    ".cruft.json",
    "src/data_sheets_schema/schema/data_sheets_schema.yaml",
    "src/data_sheets_schema/schema/data_sheets_schema_core.yaml",
    "src/data_sheets_schema/schema/D4D_Core.yaml",
    "src/data_sheets_schema/schema/release_history.yaml",
)


def _declared(path: Path) -> str | None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    value = doc.get("version")
    return None if value is None else str(value)


def _copy_metadata_fixture(dst: Path, *, mutable: tuple[str, ...] = ("CITATION.cff",)) -> Path:
    for rel in METADATA_FILES:
        src_path = ROOT / rel
        dst_path = dst / rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if rel in mutable:
            shutil.copy2(src_path, dst_path)
        else:
            os.symlink(src_path, dst_path)
    return dst


def _invoke_checker(
    root_arg: Path | None = None,
    *,
    cwd: Path | None = None,
    use_tomli_fallback: bool = False,
) -> tuple[int | None, str, str, BaseException | None]:
    """Run check_citation_metadata_20261110.py and return (exit_code, stdout, stderr, unhandled_exc)."""
    argv = [str(CHECKER_SCRIPT)]
    if root_arg is not None:
        argv.append(str(root_arg))
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    old_cwd = Path.cwd()
    module_overrides: dict[str, object] = {}
    if use_tomli_fallback:
        try:
            import tomli as _tomli_mod
        except ModuleNotFoundError:
            import tomllib as _tomli_mod  # standards-compliant stdlib equivalent for Python >= 3.11 venvs
        module_overrides = {"tomllib": None, "tomli": _tomli_mod}
    try:
        if cwd is not None:
            os.chdir(cwd)
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict(sys.modules, module_overrides),
            contextlib.redirect_stdout(out_buf),
            contextlib.redirect_stderr(err_buf),
        ):
            runpy.run_path(str(CHECKER_SCRIPT), run_name="__main__")
        return 0, out_buf.getvalue(), err_buf.getvalue(), None
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        return code, out_buf.getvalue(), err_buf.getvalue(), None
    except BaseException as exc:  # pragma: no cover - captured for canary/crash assertion
        return None, out_buf.getvalue(), err_buf.getvalue(), exc
    finally:
        if cwd is not None:
            os.chdir(old_cwd)


class TestReleaseIdentity(unittest.TestCase):
    def test_full_and_core_declare_the_same_release(self):
        self.assertEqual(_declared(SCHEMA / "data_sheets_schema.yaml"), RELEASE)
        self.assertEqual(_declared(SCHEMA / "data_sheets_schema_core.yaml"), RELEASE)
        self.assertEqual(_declared(SCHEMA / "D4D_Core.yaml"), RELEASE)
        self.assertEqual(_declared(ROOT / "CITATION.cff"), RELEASE)

    def test_the_release_is_semantic_and_past_the_two_line(self):
        """2.0.0 was declared on 2026-08-06 and kept through incompatible
        changes; the release that names the current definitions must be a
        later major."""
        major, minor, patch = (int(x) for x in RELEASE.split("."))
        self.assertGreaterEqual(major, 3)
        self.assertTrue(re.fullmatch(r"\d+\.\d+\.\d+", RELEASE))

    def test_the_generated_artifacts_carry_it(self):
        for merged in ("data_sheets_schema_all.yaml", "data_sheets_schema_core_all.yaml"):
            path = SCHEMA / merged
            if not path.exists():
                self.skipTest(f"{merged} not present in this checkout")
            head = path.read_text(encoding="utf-8")[:4000]
            self.assertIn(f"version: {RELEASE}", head, merged)
        model = ROOT / "src" / "data_sheets_schema" / "datamodel" / "data_sheets_schema.py"
        self.assertIn(f'version = "{RELEASE}"', model.read_text(encoding="utf-8"))
        jsonschema = ROOT / "project" / "jsonschema" / "data_sheets_schema.schema.json"
        if jsonschema.exists():
            self.assertIn(f'"version": "{RELEASE}"', jsonschema.read_text(encoding="utf-8"))

    def test_provenance_reads_both_declarations(self):
        from data_sheets_schema import provenance
        self.assertEqual(provenance.declared_schema_version(), RELEASE)
        self.assertEqual(provenance.declared_schema_version(provenance.CORE_SOURCE_SCHEMA), RELEASE)
        facts = provenance.schema_facts()
        self.assertEqual(facts["declared_version"], RELEASE)
        self.assertEqual(facts["core_declared_version"], RELEASE)
        self.assertEqual(facts["core_declared_in"], str(provenance.CORE_SOURCE_SCHEMA))
        self.assertTrue(facts["merged_schema_carries_version"])
        self.assertNotIn("note", facts)

    def test_a_core_that_disagrees_is_a_stated_fact(self):
        """The note is the only place a disagreement would surface; a
        recorder that silently reported the full version for both would hide
        exactly the drift #1874 found."""
        from unittest import mock
        from data_sheets_schema import provenance
        real = provenance.declared_schema_version

        def fake(source=provenance.SOURCE_SCHEMA):
            return "2.0.0" if source == provenance.CORE_SOURCE_SCHEMA else real(source)
        with mock.patch.object(provenance, "declared_schema_version", side_effect=fake):
            facts = provenance.schema_facts()
        self.assertEqual(facts["core_declared_version"], "2.0.0")
        self.assertIn("core entry point declares 2.0.0", facts["note"])

    def test_a_core_that_declares_nothing_is_a_stated_fact_too(self):
        """The pre-3.0.0 condition: full declared, core silent. A note that
        only fires on two present values would pass it silently (#1885)."""
        from unittest import mock
        from data_sheets_schema import provenance
        real = provenance.declared_schema_version

        def fake(source=provenance.SOURCE_SCHEMA):
            return None if source == provenance.CORE_SOURCE_SCHEMA else real(source)
        with mock.patch.object(provenance, "declared_schema_version", side_effect=fake):
            facts = provenance.schema_facts()
        self.assertIsNone(facts["core_declared_version"])
        self.assertIn("core entry point declares no version", facts["note"])

    def test_the_record_contract_declares_the_core_version(self):
        doc = yaml.safe_load((SCHEMA / "d4d_generation_record.yaml").read_text(encoding="utf-8"))
        attrs = doc["classes"]["SchemaFacts"]["attributes"]
        self.assertIn("core_declared_version", attrs)
        self.assertIn("core_declared_in", attrs)
        self.assertFalse(attrs["core_declared_version"].get("required", False))


class TestCitationMetadataValidation(unittest.TestCase):
    """Focused metadata validation tests for CITATION.cff and companion files (#5732-#5736)."""

    def test_live_repository_passes_and_runs_from_outside_cwd(self):
        code, stdout, stderr, exc = _invoke_checker(ROOT)
        self.assertIsNone(exc)
        self.assertEqual(code, 0, msg=stdout + stderr)
        self.assertIn("0 failure(s)", stdout)
        self.assertEqual(stderr, "")

        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, str(CHECKER_SCRIPT)],
                cwd=tmp,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("0 failure(s)", proc.stdout)
            self.assertEqual(proc.stderr, "")

    def test_malformed_inputs_fail_cleanly_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            # C1: empty CITATION.cff (yaml.safe_load -> None)
            d1 = _copy_metadata_fixture(base / "c1")
            (d1 / "CITATION.cff").write_text("", encoding="utf-8")
            code, stdout, stderr, exc = _invoke_checker(d1)
            self.assertIsNone(exc, f"C1 raised unhandled {exc!r}")
            self.assertEqual(code, 1)
            self.assertIn("FAIL ", stdout)
            self.assertEqual(stderr, "")

            # C2: authors is a list of strings instead of dicts
            d2 = _copy_metadata_fixture(base / "c2")
            (d2 / "CITATION.cff").write_text(
                "cff-version: 1.2.0\nmessage: m\ntitle: t\nauthors:\n  - Jane Doe\n",
                encoding="utf-8",
            )
            code, stdout, stderr, exc = _invoke_checker(d2)
            self.assertIsNone(exc, f"C2 raised unhandled {exc!r}")
            self.assertEqual(code, 1)
            self.assertIn("FAIL ", stdout)
            self.assertEqual(stderr, "")

            # C3: authors is a scalar string
            d3 = _copy_metadata_fixture(base / "c3")
            (d3 / "CITATION.cff").write_text(
                "cff-version: 1.2.0\nmessage: m\ntitle: t\nauthors: Jane Doe\n",
                encoding="utf-8",
            )
            code, stdout, stderr, exc = _invoke_checker(d3)
            self.assertIsNone(exc, f"C3 raised unhandled {exc!r}")
            self.assertEqual(code, 1)
            self.assertIn("FAIL ", stdout)
            self.assertEqual(stderr, "")

            # C4: keywords is null
            d4 = _copy_metadata_fixture(base / "c4")
            cff_doc = yaml.safe_load((d4 / "CITATION.cff").read_text(encoding="utf-8"))
            cff_doc["keywords"] = None
            (d4 / "CITATION.cff").write_text(yaml.safe_dump(cff_doc, sort_keys=False), encoding="utf-8")
            code, stdout, stderr, exc = _invoke_checker(d4)
            self.assertIsNone(exc, f"C4 raised unhandled {exc!r}")
            self.assertEqual(code, 1)
            self.assertIn("FAIL ", stdout)
            self.assertEqual(stderr, "")

            # C5: non-string ORCID (integer)
            d5 = _copy_metadata_fixture(base / "c5")
            cff_doc = yaml.safe_load((d5 / "CITATION.cff").read_text(encoding="utf-8"))
            cff_doc["authors"][0]["orcid"] = 12345
            (d5 / "CITATION.cff").write_text(yaml.safe_dump(cff_doc, sort_keys=False), encoding="utf-8")
            code, stdout, stderr, exc = _invoke_checker(d5)
            self.assertIsNone(exc, f"C5 raised unhandled {exc!r}")
            self.assertEqual(code, 1)
            self.assertIn("FAIL ", stdout)
            self.assertEqual(stderr, "")

            # C6: malformed YAML, TOML, or JSON syntax
            for idx, (rel_path, bad_text) in enumerate(
                (
                    ("CITATION.cff", "cff-version: [unclosed\n"),
                    ("about.yaml", "name: [unclosed\n"),
                    ("pyproject.toml", "[tool.poetry\nauthors = [\n"),
                    (".cruft.json", "{bad json"),
                )
            ):
                d6 = _copy_metadata_fixture(base / f"c6_{idx}", mutable=(rel_path,))
                (d6 / rel_path).write_text(bad_text, encoding="utf-8")
                code, stdout, stderr, exc = _invoke_checker(d6)
                self.assertIsNone(exc, f"C6 ({rel_path}) raised unhandled {exc!r}")
                self.assertEqual(code, 1, f"C6 ({rel_path}) should exit 1")
                self.assertIn("FAIL ", stdout)
                self.assertEqual(stderr, "")

    def test_cff_types_urls_and_keywords_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            # FP2: empty or null required CFF strings (message, title, family-names)
            for idx, mutator in enumerate(
                (
                    lambda d: d.__setitem__("message", ""),
                    lambda d: d.__setitem__("title", None),
                    lambda d: d["authors"][0].__setitem__("family-names", "   "),
                    lambda d: d["authors"][0].__setitem__("given-names", ""),
                )
            ):
                fx = _copy_metadata_fixture(base / f"fp2_{idx}")
                cff_doc = yaml.safe_load((fx / "CITATION.cff").read_text(encoding="utf-8"))
                mutator(cff_doc)
                (fx / "CITATION.cff").write_text(yaml.safe_dump(cff_doc, sort_keys=False), encoding="utf-8")
                code, stdout, _, exc = _invoke_checker(fx)
                self.assertIsNone(exc)
                self.assertEqual(code, 1, f"FP2 case {idx} should fail")
                self.assertIn("FAIL ", stdout)

            # FP3: keywords as a bare string or containing an empty string
            for idx, bad_kw in enumerate(("Datasheets", [], ["Datasheets", "  "])):
                fx = _copy_metadata_fixture(base / f"fp3_{idx}")
                cff_doc = yaml.safe_load((fx / "CITATION.cff").read_text(encoding="utf-8"))
                cff_doc["keywords"] = bad_kw
                (fx / "CITATION.cff").write_text(yaml.safe_dump(cff_doc, sort_keys=False), encoding="utf-8")
                code, stdout, _, exc = _invoke_checker(fx)
                self.assertIsNone(exc)
                self.assertEqual(code, 1, f"FP3 case {idx} ({bad_kw!r}) should fail")
                self.assertIn("FAIL ", stdout)

            # FP4: malformed https:// URLs in repository-code or url
            for idx, (field, bad_url) in enumerate(
                (
                    ("repository-code", "https://"),
                    ("url", "https://"),
                    ("repository-code", "https://example.com"),
                    ("url", "https://not a valid url/path"),
                    ("repository-code", "http://github.com/bridge2ai/data-sheets-schema"),
                )
            ):
                fx = _copy_metadata_fixture(base / f"fp4_{idx}")
                cff_doc = yaml.safe_load((fx / "CITATION.cff").read_text(encoding="utf-8"))
                cff_doc[field] = bad_url
                (fx / "CITATION.cff").write_text(yaml.safe_dump(cff_doc, sort_keys=False), encoding="utf-8")
                code, stdout, _, exc = _invoke_checker(fx)
                self.assertIsNone(exc)
                self.assertEqual(code, 1, f"FP4 case {idx} ({field}={bad_url!r}) should fail")
                self.assertIn("FAIL ", stdout)

    def test_cff_optional_author_fields_vs_project_primary_author_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            # Project policy: primary author (authors[0]) must declare orcid and affiliation
            for field in ("orcid", "affiliation"):
                fx = _copy_metadata_fixture(base / f"primary_missing_{field}")
                cff_doc = yaml.safe_load((fx / "CITATION.cff").read_text(encoding="utf-8"))
                cff_doc["authors"][0].pop(field, None)
                (fx / "CITATION.cff").write_text(yaml.safe_dump(cff_doc, sort_keys=False), encoding="utf-8")
                code, stdout, _, exc = _invoke_checker(fx)
                self.assertIsNone(exc)
                self.assertEqual(code, 1, f"Primary author missing {field} should fail project policy")
                self.assertIn("FAIL ", stdout)

            # CFF 1.2.0 optionality: additional co-authors (authors[1+]) may omit orcid and affiliation
            fx_coauthor_ok = _copy_metadata_fixture(base / "coauthor_optional_ok")
            cff_doc = yaml.safe_load((fx_coauthor_ok / "CITATION.cff").read_text(encoding="utf-8"))
            cff_doc["authors"].append({"family-names": "Mungall", "given-names": "Christopher J."})
            (fx_coauthor_ok / "CITATION.cff").write_text(
                yaml.safe_dump(cff_doc, sort_keys=False), encoding="utf-8"
            )
            code, stdout, _, exc = _invoke_checker(fx_coauthor_ok)
            self.assertIsNone(exc)
            self.assertEqual(code, 0, f"Co-author without optional orcid/affiliation must pass:\n{stdout}")

            # When a co-author DOES provide orcid or affiliation, invalid values must fail
            fx_coauthor_bad_orcid = _copy_metadata_fixture(base / "coauthor_bad_orcid")
            cff_doc = yaml.safe_load((fx_coauthor_bad_orcid / "CITATION.cff").read_text(encoding="utf-8"))
            cff_doc["authors"].append(
                {
                    "family-names": "Doe",
                    "given-names": "Jane",
                    "orcid": "https://orcid.org/0000-0002-5355-2570",
                }
            )
            (fx_coauthor_bad_orcid / "CITATION.cff").write_text(
                yaml.safe_dump(cff_doc, sort_keys=False), encoding="utf-8"
            )
            code, stdout, _, exc = _invoke_checker(fx_coauthor_bad_orcid)
            self.assertIsNone(exc)
            self.assertEqual(code, 1, "Co-author with invalid ORCID checksum must fail")
            self.assertIn("FAIL ", stdout)

            fx_coauthor_bad_affil = _copy_metadata_fixture(base / "coauthor_bad_affil")
            cff_doc = yaml.safe_load((fx_coauthor_bad_affil / "CITATION.cff").read_text(encoding="utf-8"))
            cff_doc["authors"].append(
                {
                    "family-names": "Doe",
                    "given-names": "Jane",
                    "affiliation": "   ",
                }
            )
            (fx_coauthor_bad_affil / "CITATION.cff").write_text(
                yaml.safe_dump(cff_doc, sort_keys=False), encoding="utf-8"
            )
            code, stdout, _, exc = _invoke_checker(fx_coauthor_bad_affil)
            self.assertIsNone(exc)
            self.assertEqual(code, 1, "Co-author with blank affiliation string must fail")
            self.assertIn("FAIL ", stdout)

    def test_schema_version_consistency_across_all_declarations(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            # Non-string float version in CITATION.cff (e.g. version: 3.20) must fail
            fx_float = _copy_metadata_fixture(base / "version_float")
            cff_text = (fx_float / "CITATION.cff").read_text(encoding="utf-8")
            (fx_float / "CITATION.cff").write_text(
                re.sub(r"^version:\s*3\.2\.0\b", "version: 3.20", cff_text, count=1, flags=re.MULTILINE),
                encoding="utf-8",
            )
            code, stdout, _, exc = _invoke_checker(fx_float)
            self.assertIsNone(exc)
            self.assertEqual(code, 1, "Non-string float version in CITATION.cff must fail")
            self.assertIn("FAIL ", stdout)

            # Version drift in any of the 4 schema/release files must fail
            for idx, rel_schema in enumerate(
                (
                    "src/data_sheets_schema/schema/data_sheets_schema.yaml",
                    "src/data_sheets_schema/schema/data_sheets_schema_core.yaml",
                    "src/data_sheets_schema/schema/D4D_Core.yaml",
                    "src/data_sheets_schema/schema/release_history.yaml",
                )
            ):
                fx = _copy_metadata_fixture(base / f"drift_{idx}", mutable=(rel_schema,))
                p = fx / rel_schema
                text = p.read_text(encoding="utf-8")
                if rel_schema.endswith("release_history.yaml"):
                    text = text.replace("  - version: 3.2.0", "  - version: 3.1.9", 1)
                else:
                    text = re.sub(r"^version:\s*3\.2\.0\b", "version: 3.1.9", text, count=1, flags=re.MULTILINE)
                p.write_text(text, encoding="utf-8")
                code, stdout, _, exc = _invoke_checker(fx)
                self.assertIsNone(exc)
                self.assertEqual(code, 1, f"Version drift in {rel_schema} must fail")
                self.assertIn("FAIL ", stdout)

    def test_cross_file_author_copyright_and_case_insensitive_placeholder_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            # Empty author in about.yaml
            fx_about = _copy_metadata_fixture(base / "about_empty_author", mutable=("about.yaml",))
            about_doc = yaml.safe_load((fx_about / "about.yaml").read_text(encoding="utf-8"))
            about_doc["author"] = "   "
            (fx_about / "about.yaml").write_text(yaml.safe_dump(about_doc, sort_keys=False), encoding="utf-8")
            code, stdout, _, exc = _invoke_checker(fx_about)
            self.assertIsNone(exc)
            self.assertEqual(code, 1, "Empty author in about.yaml must fail")
            self.assertIn("FAIL ", stdout)

            # Empty full_name or __author in .cruft.json
            for key in ("full_name", "__author"):
                fx_cruft = _copy_metadata_fixture(base / f"cruft_empty_{key}", mutable=(".cruft.json",))
                cruft_text = (fx_cruft / ".cruft.json").read_text(encoding="utf-8")
                cruft_doc = yaml.safe_load(cruft_text)
                cruft_doc["context"]["cookiecutter"][key] = ""
                import json as _json

                (fx_cruft / ".cruft.json").write_text(_json.dumps(cruft_doc, indent=2), encoding="utf-8")
                code, stdout, _, exc = _invoke_checker(fx_cruft)
                self.assertIsNone(exc)
                self.assertEqual(code, 1, f"Empty {key} in .cruft.json must fail")
                self.assertIn("FAIL ", stdout)

            # Missing Copyright (c) line in LICENSE
            fx_lic = _copy_metadata_fixture(base / "license_no_copyright", mutable=("LICENSE",))
            (fx_lic / "LICENSE").write_text("MIT License\n\nPermission is hereby granted...\n", encoding="utf-8")
            code, stdout, _, exc = _invoke_checker(fx_lic)
            self.assertIsNone(exc)
            self.assertEqual(code, 1, "Missing Copyright (c) line in LICENSE must fail")
            self.assertIn("FAIL ", stdout)

            # Case-insensitive "my name" placeholder in any of the 5 files
            for idx, rel_file in enumerate(
                ("pyproject.toml", "LICENSE", "about.yaml", ".cruft.json", "CITATION.cff")
            ):
                fx_ph = _copy_metadata_fixture(base / f"placeholder_{idx}", mutable=(rel_file,))
                p = fx_ph / rel_file
                text = p.read_text(encoding="utf-8")
                self.assertIn("Joachimiak", text)
                p.write_text(text.replace("Joachimiak", "my name", 1), encoding="utf-8")
                code, stdout, _, exc = _invoke_checker(fx_ph)
                self.assertIsNone(exc)
                self.assertEqual(code, 1, f"Lowercase 'my name' placeholder in {rel_file} must fail")
                self.assertIn("FAIL ", stdout)

    def test_python_pre_311_tomli_fallback_and_lockfile_support(self):
        # Verify the `except ModuleNotFoundError: import tomli as tomllib` fallback path (#5736)
        code, stdout, stderr, exc = _invoke_checker(ROOT, use_tomli_fallback=True)
        self.assertIsNone(exc, f"tomli fallback raised {exc!r}")
        self.assertEqual(code, 0, msg=stdout + stderr)
        self.assertIn("0 failure(s)", stdout)

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fx_bad = _copy_metadata_fixture(base / "fallback_bad_toml", mutable=("pyproject.toml",))
            (fx_bad / "pyproject.toml").write_text("[tool.poetry\nauthors = [\n", encoding="utf-8")
            code, stdout, _, exc = _invoke_checker(fx_bad, use_tomli_fallback=True)
            self.assertIsNone(exc)
            self.assertEqual(code, 1)
            self.assertIn("FAIL ", stdout)

            fx_empty = _copy_metadata_fixture(base / "fallback_empty_authors", mutable=("pyproject.toml",))
            pp_text = (fx_empty / "pyproject.toml").read_text(encoding="utf-8")
            (fx_empty / "pyproject.toml").write_text(
                re.sub(r"^authors\s*=\s*\[.*?\]", "authors = []", pp_text, count=1, flags=re.MULTILINE),
                encoding="utf-8",
            )
            code, stdout, _, exc = _invoke_checker(fx_empty, use_tomli_fallback=True)
            self.assertIsNone(exc)
            self.assertEqual(code, 1)
            self.assertIn("FAIL ", stdout)

            fx_no_tomli = _copy_metadata_fixture(base / "fallback_no_tomli_dep", mutable=("pyproject.toml",))
            (fx_no_tomli / "pyproject.toml").write_text(
                re.sub(r"^tomli\s*=.*$", "", pp_text, count=1, flags=re.MULTILINE),
                encoding="utf-8",
            )
            code, stdout, _, exc = _invoke_checker(fx_no_tomli, use_tomli_fallback=True)
            self.assertIsNone(exc)
            self.assertEqual(code, 1)
            self.assertIn("FAIL pyproject.toml declares conditional tomli dependency for Python < 3.11", stdout)


if __name__ == "__main__":
    unittest.main()
