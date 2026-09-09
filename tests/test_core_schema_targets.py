"""`make validate-core` validates the core exchange schema (#1127).

The target ran `linkml-validate --validate-schema`, a flag the installed
linkml-validate no longer accepts, so it exited 2 on main and nothing in CI
noticed because nothing in CI called it. Two things are pinned here: the
target exits 0 on the committed core schema, and the same recipe fails on a
copy whose one slot names a range no schema declares — a check that cannot
fail is not a check. The recipe is exercised through `make` itself, with the
schema path overridden on the command line, so the test reads the Makefile
the operator runs rather than a restatement of it.
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


def _make(*args, cwd=ROOT):
    return subprocess.run(["make", *args], cwd=cwd, capture_output=True, text=True)


class TestValidateCore(unittest.TestCase):
    def test_the_recipe_names_no_retired_flag(self):
        text = (ROOT / "Makefile").read_text()
        recipe = text.split("\nvalidate-core:", 1)[1].split("\n\n", 1)[0]
        self.assertNotIn("--validate-schema", recipe)

    def test_the_committed_core_schema_validates(self):
        result = _make("validate-core")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Core schema validates", result.stdout)

    def test_a_schema_with_an_unknown_range_fails_the_same_recipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path in SCHEMA_DIR.glob("*.yaml"):
                shutil.copy(path, tmp)
            module = Path(tmp) / "D4D_Core.yaml"
            broken = re.sub(r"(\n\s+range: )\w+\n", r"\1NoSuchClassXYZ\n", module.read_text(), count=1)
            self.assertIn("NoSuchClassXYZ", broken)
            module.write_text(broken)
            copy = Path(tmp) / CORE.name
            result = _make("validate-core", f"D4D_CORE_SCHEMA={copy}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NoSuchClassXYZ", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
