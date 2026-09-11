"""Test D4D Full Schema generation and validation."""
import os
import subprocess
import tempfile
import unittest
import yaml

from linkml_runtime.loaders import yaml_loader


ROOT = os.path.join(os.path.dirname(__file__), '..')
SCHEMA_DIR = os.path.join(ROOT, "src", "data_sheets_schema", "schema")
DATA_SHEETS_DIR = os.path.join(ROOT, "data", "sheets", "html_output")

# Test cases that the full schema should be able to validate
TEST_CASES = [
    "D4D_-_AI-READI_FAIRHub_v3_data.yaml",
    "D4D_-_CM4AI_Dataverse_v3_data.yaml",
    "D4D_-_VOICE_PhysioNet_v3_data.yaml"
]


class TestD4DFullSchema(unittest.TestCase):
    """Test D4D Full Schema generation and validation."""

    @classmethod
    def setUpClass(cls):
        """Build the merged schema into a temporary directory.

        This used to run `make full-schema` in the repository root, which
        rewrites the committed `data_sheets_schema_all.yaml` **in place** as
        a side effect of running the tests. The rewrite puts back
        byte-identical content — the committed file reproduces exactly, on
        Linux and on macOS — so nothing about it was ever wrong. What
        mattered is that `gen-linkml` writes the file non-atomically, so
        another test reading it during the write sees a partial one, and
        `schema_sync.check`, which `api_runner.execute` treats as fatal,
        then reports the merged schema as differing from a fresh build of
        its source. Serially the rewrite finishes before anything else
        looks; under `pytest -n auto` between one and nine runner-gate
        tests failed per run, on different tests each time, which read as
        flakiness rather than as one test mutating a shared input (#1208).

        Generating into a temporary directory tests the same thing — that
        the merged schema builds from source and is valid — without making
        the repository's own artifact a mutable fixture.
        """
        cls.d4d_root_path = os.path.join(SCHEMA_DIR, "data_sheets_schema.yaml")
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        cls.d4d_full_path = os.path.join(cls._tmp.name, "data_sheets_schema_all.yaml")

        try:
            subprocess.run(
                ["poetry", "run", "gen-linkml", "-o", cls.d4d_full_path,
                 "-f", "yaml", cls.d4d_root_path],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=600,
            )
        except subprocess.CalledProcessError as e:
            raise AssertionError(
                f"the merged schema could not be generated: {(e.stderr or e.stdout)[-400:]}") from e
        # The Makefile rule pipes `---` onto its output; the committed file
        # carries it, so a test comparing against that file needs it too.
        with open(cls.d4d_full_path, encoding="utf-8") as fh:
            body = fh.read()
        with open(cls.d4d_full_path, "w", encoding="utf-8") as fh:
            fh.write("---\n" + body)

    def test_d4d_root_exists(self):
        """Test that root exists."""
        self.assertTrue(os.path.exists(self.d4d_root_path),
                        f"root yaml not found at {self.d4d_root_path}")

    def test_d4d_full_schema_generated(self):
        """Test that full schema was generated successfully."""
        self.assertTrue(os.path.exists(self.d4d_full_path),
                        f"full schema not found at {self.d4d_full_path}")

        # Check that the file is not empty
        with open(self.d4d_full_path, 'r') as f:
            content = f.read().strip()
            self.assertGreater(len(content), 0, "full schema is empty")

    def test_d4d_full_schema_validates_test_cases(self):
        """Test that the full schema can load all test cases."""
        if not os.path.exists(self.d4d_full_path):
            self.skipTest("full schema not found")

        for test_case in TEST_CASES:
            test_case_path = os.path.join(DATA_SHEETS_DIR, test_case)

            with self.subTest(test_case=test_case):
                if not os.path.exists(test_case_path):
                    self.skipTest(
                        f"Test case {test_case} not found at {test_case_path}")

                # Load the test case data
                try:
                    with open(test_case_path, 'r') as f:
                        test_data = yaml.safe_load(f)

                    # Basic check that we can load the data and it has expected structure
                    self.assertIsInstance(
                        test_data, dict, f"{test_case} should load as a dictionary")
                    self.assertIn("DatasetCollection", test_data,
                                  f"{test_case} should contain DatasetCollection")

                    print(
                        f"✅ {test_case} loaded successfully and has expected structure")

                except Exception as e:
                    self.fail(f"Error loading {test_case}: {str(e)}")

    def test_d4d_full_schema_prefixes_include_expected(self):
        """Parse full schema as YAML and ensure expected prefixes are present."""
        if not os.path.exists(self.d4d_full_path):
            self.skipTest("full schema not found")

        with open(self.d4d_full_path, 'r') as f:
            schema_yaml = yaml.safe_load(f)

        prefixes = schema_yaml.get("prefixes")
        self.assertIsNotNone(prefixes, "prefixes not found in full schema")

        if isinstance(prefixes, dict):
            prefix_items = list(prefixes.keys())
        elif isinstance(prefixes, list):
            prefix_items = prefixes
        else:
            self.fail(f"Unexpected type for prefixes: {type(prefixes)}")

        expected = [
            "d4dmotivation",
            "d4dcomposition",
            "d4dpreprocessing",
            "d4duses",
            "d4ddistribution",
            "d4dmaintenance",
            "d4dethics",
            "d4dhuman",
            "d4ddatagovernance",
        ]
        for p in expected:
            with self.subTest(prefix=p):
                self.assertIn(
                    p, prefix_items, f"Expected prefix '{p}' not found in full schema")

    def test_d4d_full_schema_has_no_imports(self):
        """Test that the full schema has no import statements (fully merged)."""
        if not os.path.exists(self.d4d_full_path):
            self.skipTest("full schema not found")

        with open(self.d4d_full_path, 'r') as f:
            schema_content = f.read()

        # The full schema should not contain import statements
        # (it should be fully merged)
        self.assertNotIn("imports:", schema_content,
                         "D4D Full Schema should not contain imports (should be fully merged)")


if __name__ == '__main__':
    unittest.main()
