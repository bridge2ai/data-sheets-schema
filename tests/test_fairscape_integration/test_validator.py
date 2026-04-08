#!/usr/bin/env python3
"""
Tests for D4DValidator utility.

Tests D4D YAML validation wrapper functionality.
"""

import unittest
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.fairscape_integration.utils.validator import D4DValidator


class TestD4DValidator(unittest.TestCase):
    """Test D4DValidator validation and error parsing."""

    def setUp(self):
        """Set up test fixtures."""
        # Use actual D4D schema from repository
        self.schema_path = repo_root / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"

        if not self.schema_path.exists():
            self.skipTest("D4D schema not found - skipping validator tests")

        self.validator = D4DValidator(str(self.schema_path))

    def test_validator_init_with_valid_schema(self):
        """Test validator initialization with valid schema path."""
        validator = D4DValidator(str(self.schema_path))
        self.assertEqual(validator.schema_path, self.schema_path)

    def test_validator_init_with_invalid_schema(self):
        """Test validator initialization with invalid schema path."""
        with self.assertRaises(FileNotFoundError):
            D4DValidator("/nonexistent/schema.yaml")

    def test_parse_validation_errors_missing_required(self):
        """Test parsing of missing required field errors."""
        error_output = "'title' is a required field"
        errors = self.validator.parse_validation_errors(error_output)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['field'], 'title')
        self.assertEqual(errors[0]['type'], 'missing_required')

    def test_parse_validation_errors_type_mismatch(self):
        """Test parsing of type mismatch errors."""
        error_output = "bytes: Expected type int, got str"
        errors = self.validator.parse_validation_errors(error_output)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['field'], 'bytes')
        self.assertEqual(errors[0]['type'], 'type_mismatch')

    def test_parse_validation_errors_invalid_enum(self):
        """Test parsing of invalid enum value errors."""
        error_output = "'invalid_value' not in permissible values [value1, value2]"
        errors = self.validator.parse_validation_errors(error_output)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['field'], 'invalid_value')
        self.assertEqual(errors[0]['type'], 'invalid_enum')

    def test_classify_error_missing_required(self):
        """Test error classification for missing required fields."""
        error_type = self.validator._classify_error("'title' is a required field")
        self.assertEqual(error_type, 'missing_required')

    def test_classify_error_type_mismatch(self):
        """Test error classification for type mismatches."""
        error_type = self.validator._classify_error("Expected type int, got str")
        self.assertEqual(error_type, 'type_mismatch')

    def test_classify_error_invalid_enum(self):
        """Test error classification for invalid enum values."""
        error_type = self.validator._classify_error("not in permissible values")
        self.assertEqual(error_type, 'invalid_enum')

    def test_classify_error_format_error(self):
        """Test error classification for format errors."""
        error_type = self.validator._classify_error("Invalid date format")
        self.assertEqual(error_type, 'format_error')

    def test_classify_error_other(self):
        """Test error classification for unknown errors."""
        error_type = self.validator._classify_error("Some unknown error")
        self.assertEqual(error_type, 'other')

    def test_suggest_fixes_missing_required(self):
        """Test fix suggestions for missing required fields."""
        errors = [{'type': 'missing_required', 'field': 'title'}]
        suggestions = self.validator.suggest_fixes(errors)

        self.assertEqual(len(suggestions), 1)
        self.assertIn('title', suggestions[0])
        self.assertIn('Add required field', suggestions[0])

    def test_suggest_fixes_type_mismatch(self):
        """Test fix suggestions for type mismatches."""
        errors = [{'type': 'type_mismatch', 'field': 'bytes'}]
        suggestions = self.validator.suggest_fixes(errors)

        self.assertEqual(len(suggestions), 1)
        self.assertIn('bytes', suggestions[0])
        self.assertIn('Fix type', suggestions[0])

    def test_suggest_fixes_invalid_enum(self):
        """Test fix suggestions for invalid enum values."""
        errors = [{'type': 'invalid_enum', 'field': 'status'}]
        suggestions = self.validator.suggest_fixes(errors)

        self.assertEqual(len(suggestions), 1)
        self.assertIn('status', suggestions[0])
        self.assertIn('permissible values', suggestions[0])

    def test_suggest_fixes_date_format(self):
        """Test fix suggestions for date format errors."""
        errors = [{'type': 'format_error', 'field': 'created_date'}]
        suggestions = self.validator.suggest_fixes(errors)

        self.assertEqual(len(suggestions), 1)
        self.assertIn('date', suggestions[0].lower())
        self.assertIn('YYYY-MM-DD', suggestions[0])

    def test_suggest_fixes_url_format(self):
        """Test fix suggestions for URL format errors."""
        errors = [{'type': 'format_error', 'field': 'download_url'}]
        suggestions = self.validator.suggest_fixes(errors)

        self.assertEqual(len(suggestions), 1)
        self.assertIn('url', suggestions[0].lower())
        self.assertIn('http', suggestions[0])

    def test_get_validation_summary_valid(self):
        """Test validation summary for valid file."""
        summary = self.validator.get_validation_summary(True, "")
        self.assertIn("Validation passed", summary)
        self.assertIn("✓", summary)

    def test_get_validation_summary_invalid_with_errors(self):
        """Test validation summary for invalid file with parsed errors."""
        error_output = "'title' is a required field"
        summary = self.validator.get_validation_summary(False, error_output)

        self.assertIn("Validation failed", summary)
        self.assertIn("✗", summary)
        self.assertIn("Found 1 error", summary)
        self.assertIn("title", summary)
        self.assertIn("Suggested fixes", summary)

    def test_get_validation_summary_invalid_no_parsed_errors(self):
        """Test validation summary for invalid file with unparseable errors."""
        error_output = "Some random validation error"
        summary = self.validator.get_validation_summary(False, error_output)

        self.assertIn("Validation failed", summary)
        self.assertIn("Raw error output", summary)
        self.assertIn("random validation error", summary)

    def test_validate_nonexistent_file(self):
        """Test validation of nonexistent file."""
        is_valid, output = self.validator.validate_d4d_yaml("/nonexistent/file.yaml")

        self.assertFalse(is_valid)
        self.assertIn("File not found", output)


if __name__ == '__main__':
    unittest.main()
