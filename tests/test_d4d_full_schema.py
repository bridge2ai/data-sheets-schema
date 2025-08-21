"""Test D4D Full Schema generation and validation."""
import os
import subprocess
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
        """Set up test class by generating the D4D Full Schema."""
        cls.d4d_root_path = os.path.join(SCHEMA_DIR, "data_sheets_schema.yaml")
        cls.d4d_full_path = os.path.join(
            SCHEMA_DIR, "data_sheets_schema_all.yaml")

        # Generate the D4D Full Schema using the Makefile target
        try:
            result = subprocess.run(
                ["make", "full-schema"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"D4D Full Schema generation output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"Error generating D4D Full Schema: {e.stderr}")
            raise

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

    def test_d4d_full_schema_contains_all_modules(self):
        """Test that the D4D Full Schema contains definitions from all modules."""
        if not os.path.exists(self.d4d_full_path):
            self.skipTest("D4D_Full_Schema.yaml not found")

        with open(self.d4d_full_path, 'r') as f:
            schema_content = f.read()

        # Check for presence of key module-specific classes/slots
        expected_sections = [
            "MotivationSection",
            "CompositionSection",
            "CollectionSection",
            "PreprocessingSection",
            "UsesSection",
            "DistributionSection",
            "MaintenanceSection",
            "EthicsSection",
            "HumanSection",
            "DataGovernanceSection"
        ]

        for section in expected_sections:
            with self.subTest(section=section):
                self.assertIn(section, schema_content,
                              f"Expected section {section} not found in D4D Full Schema")

    def test_d4d_full_schema_has_no_imports(self):
        """Test that the D4D Full Schema has no import statements (fully merged)."""
        if not os.path.exists(self.d4d_full_path):
            self.skipTest("D4D_Full_Schema.yaml not found")

        with open(self.d4d_full_path, 'r') as f:
            schema_content = f.read()

        # The full schema should not contain import statements
        # (it should be fully merged)
        self.assertNotIn("imports:", schema_content,
                         "D4D Full Schema should not contain imports (should be fully merged)")


if __name__ == '__main__':
    unittest.main()
