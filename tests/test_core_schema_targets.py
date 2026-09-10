"""`make validate-core` validates the core exchange schema (#1127).

The target ran `linkml-validate --validate-schema`, a flag the installed
linkml-validate no longer accepts, so it exited 2 on main and nothing in CI
noticed because nothing in CI called it. The recipe now has two halves —
the linter's metamodel validation on every file, and gen-python's
resolution of every slot, range and import — and each half is pinned by a
break only it catches: a `title` that is a number passes gen-python and
fails the linter (in the wrapper and in a module, since the linter reads
one file); a range no schema declares passes the linter on every file and
fails gen-python. The recipe is
exercised through `make` itself, with the schema path overridden on the
command line, so the test reads the Makefile the operator runs rather than
a restatement of it. A check that cannot fail is not a check.
"""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "src" / "data_sheets_schema" / "schema"
CORE = SCHEMA_DIR / "data_sheets_schema_core.yaml"


def _make(*args):
    return subprocess.run(["make", *args], cwd=ROOT, capture_output=True, text=True, timeout=300)


def _broken_copy(tmp, edit):
    """The schema directory copied to `tmp` with `edit(module_path)` applied."""
    for path in SCHEMA_DIR.glob("*.yaml"):
        shutil.copy(path, tmp)
    edit(Path(tmp))
    return Path(tmp) / CORE.name


class TestValidateCore(unittest.TestCase):
    def test_the_committed_core_schema_validates(self):
        result = _make("validate-core")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Core schema validates", result.stdout)

    def test_an_unknown_range_in_the_module_fails_the_recipe(self):
        """The break the linter cannot see (#1136 review, round 2, M1): the
        metamodel check reads one file's raw YAML, so a range no schema
        declares passes it — every linted file reports no problem — and only
        gen-python's cross-file resolution names it. This case pins the
        gen-python line; delete it and this test fails."""
        def edit(d):
            m = d / "D4D_Core.yaml"
            text = m.read_text()
            self.assertIn("\n        range: CoreDataset\n", text)
            m.write_text(text.replace("\n        range: CoreDataset\n", "\n        range: NoSuchClassXYZ\n", 1))
        with tempfile.TemporaryDirectory() as tmp:
            result = _make("validate-core", f"D4D_CORE_SCHEMA={_broken_copy(tmp, edit)}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NoSuchClassXYZ", result.stdout + result.stderr)
        self.assertNotIn("✖", result.stdout)                     # the linter passed every file

    def test_a_metamodel_break_in_the_wrapper_fails_the_recipe(self):
        """gen-python coerces a numeric title and passes; only the linter's
        metamodel validation catches it — this case pins the linter line."""
        def edit(d):
            w = d / CORE.name
            text = w.read_text()
            self.assertIn("\ntitle:", text)
            w.write_text(text.replace("\ntitle:", "\ntitle: 12345 #", 1))
        with tempfile.TemporaryDirectory() as tmp:
            result = _make("validate-core", f"D4D_CORE_SCHEMA={_broken_copy(tmp, edit)}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("12345", result.stdout + result.stderr)   # the planted sentinel, echoed by the linter
        self.assertRegex(result.stdout, r"✖ .*" + re.escape(CORE.name))   # attributed to the wrapper, not merely echoed

    def test_a_metamodel_break_in_the_module_fails_the_recipe(self):
        """The linter does not follow imports, so the recipe lints each
        module itself; `title: 999` in `D4D_Core.yaml` passed the first
        version of the recipe (#1136 review, S1)."""
        def edit(d):
            m = d / "D4D_Core.yaml"
            text = m.read_text()
            self.assertIn("\ntitle:", text)
            m.write_text(text.replace("\ntitle:", "\ntitle: 999 #", 1))
        with tempfile.TemporaryDirectory() as tmp:
            result = _make("validate-core", f"D4D_CORE_SCHEMA={_broken_copy(tmp, edit)}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("999", result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"✖ .*D4D_Core\.yaml")

    def test_a_numeric_range_in_the_module_fails_the_recipe(self):
        """#1150 reported that `range: 123` in `D4D_Core.yaml` passed both
        halves. It did not: gen-python names it (`unrecognized range (123)`)
        and, since every module is linted (#1136 round 2), so does the
        linter's metamodel check. The value it reported degraded to a string
        is what a *null* range produces (the next test). Pinned by the
        planted sentinel and the file the linter attributes it to."""
        def edit(d):
            m = d / "D4D_Core.yaml"
            text = m.read_text()
            self.assertIn("\n        range: CoreDataset\n", text)
            m.write_text(text.replace("\n        range: CoreDataset\n", "\n        range: 123\n", 1))
        with tempfile.TemporaryDirectory() as tmp:
            result = _make("validate-core", f"D4D_CORE_SCHEMA={_broken_copy(tmp, edit)}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("123", result.stdout + result.stderr)              # the planted sentinel
        self.assertRegex(result.stdout, r"✖ .*D4D_Core\.yaml")

    def test_a_null_range_in_the_module_fails_the_recipe(self):
        """The break neither half sees (#1150, #1179 review M1): `range: null`
        is legal LinkML, the linter and gen-python pass it, and the slot
        generates as `Optional[Union[str, list[str]]]` where a `CoreDataset`
        collection was meant. The third line of the recipe reads the raw YAML;
        delete it and this test fails."""
        def edit(d):
            m = d / "D4D_Core.yaml"
            text = m.read_text()
            self.assertIn("\n        range: CoreDataset\n", text)
            m.write_text(text.replace("\n        range: CoreDataset\n", "\n        range: null\n", 1))
        with tempfile.TemporaryDirectory() as tmp:
            result = _make("validate-core", f"D4D_CORE_SCHEMA={_broken_copy(tmp, edit)}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("`range:` is present with no value", result.stdout + result.stderr)
        self.assertIn("CoreDatasetCollection.resources", result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"✓ .*D4D_Core\.yaml")          # the linter passed it; the range check named it

    def test_the_range_check_reads_slots_slot_usage_and_attributes_and_names_a_file_it_cannot_read(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("check_schema_ranges", ROOT / "scripts" / "check_schema_ranges.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        self.assertEqual(mod.problems(CORE), [])
        with tempfile.TemporaryDirectory() as tmp:
            def edit(d):
                m = d / "D4D_Core.yaml"                                    # an attribute's range
                text = m.read_text()
                m.write_text(text.replace("\n        range: CoreDataset\n", "\n        range: null\n", 1))
                b = d / "D4D_Base_import.yaml"                             # a top-level slot's range
                text = b.read_text()
                i = text.index("\nslots:\n"); j = text.index("range: ", i)
                b.write_text(text[:j] + "range: 123" + text[text.index("\n", j):])
                c = d / "D4D_Composition.yaml"                              # a slot_usage range
                text = c.read_text()
                i = text.index("slot_usage:"); j = text.index("range: ", i)
                c.write_text(text[:j] + "range: null" + text[text.index("\n", j):])
                (d / "D4D_FileCollection.yaml").write_text("classes: [\n", encoding="utf-8")   # not parseable
            read: list = []
            found = mod.problems(_broken_copy(tmp, edit), read)
        self.assertEqual(len(found), 4, found)
        self.assertTrue(any("D4D_Core.yaml: CoreDatasetCollection.resources (attributes)" in f and "no value" in f for f in found), found)
        self.assertTrue(any("D4D_Base_import.yaml: slot " in f and "range is a int (123)" in f for f in found), found)
        self.assertTrue(any("D4D_Composition.yaml: " in f and "(slot_usage)" in f and "no value" in f for f in found), found)
        self.assertTrue(any("D4D_FileCollection.yaml: not parseable, not checked" in f for f in found), found)
        self.assertNotIn("D4D_FileCollection.yaml", [p.name for p in read])

if __name__ == "__main__":
    unittest.main()
