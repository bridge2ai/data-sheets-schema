"""`make validate-core` validates the core exchange schema (#1127).

The target ran `linkml-validate --validate-schema`, a flag the installed
linkml-validate no longer accepts, so it exited 2 on main and nothing in CI
noticed because nothing in CI called it. The recipe now has two halves —
the linter's metamodel validation on every file, and gen-python's
resolution of every slot, range and import — and each half is pinned by a
break only it catches: a wrapper whose `title` is a number passes gen-python
and fails the linter; a module with an unknown key passes plain
`linkml-lint` (and `make lint-core`) and fails gen-python. The recipe is
exercised through `make` itself, with the schema path overridden on the
command line, so the test reads the Makefile the operator runs rather than
a restatement of it. A check that cannot fail is not a check.
"""
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

    def test_an_unknown_key_in_the_module_fails_the_recipe(self):
        """Plain `linkml-lint` reports no problem for this (verified in the
        #1136 review); gen-python names it."""
        def edit(d):
            m = d / "D4D_Core.yaml"
            m.write_text(m.read_text().replace("\nclasses:", "\ndescriptionnn: not a metamodel key\nclasses:", 1))
        with tempfile.TemporaryDirectory() as tmp:
            result = _make("validate-core", f"D4D_CORE_SCHEMA={_broken_copy(tmp, edit)}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("descriptionnn", result.stdout + result.stderr)

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
        self.assertIn("title", result.stdout + result.stderr)

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
        self.assertIn("title", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
