#!/usr/bin/env python3
"""
Unit tests for validate_preprocessing_quality.py

Tests validation functionality for preprocessing quality checks.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.download.validate_preprocessing_quality import (
        get_file_size,
        count_text_content,
        is_stub_content,
        validate_file,
        validate_project,
        format_size,
        FileQuality
    )
except ImportError as e:
    print(f"Warning: Could not import validate_preprocessing_quality: {e}", file=sys.stderr)
    get_file_size = None
    count_text_content = None
    is_stub_content = None
    validate_file = None
    validate_project = None
    format_size = None
    FileQuality = None


class TestValidationQuality(unittest.TestCase):
    """Test preprocessing quality validation functionality."""

    def setUp(self):
        """Set up test fixtures - create temporary directories with test files."""
        if get_file_size is None:
            self.skipTest("validate_preprocessing_quality module not available")

        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

        self.raw_dir = self.test_path / "raw" / "TEST_PROJECT"
        self.preprocessed_dir = self.test_path / "preprocessed" / "individual" / "TEST_PROJECT"

        self.raw_dir.mkdir(parents=True)
        self.preprocessed_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, 'test_dir'):
            shutil.rmtree(self.test_dir)

    def test_get_file_size(self):
        """Test file size retrieval."""
        test_file = self.test_path / "test.txt"
        test_file.write_text("Hello World!")

        size = get_file_size(test_file)
        self.assertEqual(size, 12)  # "Hello World!" is 12 bytes

    def test_get_file_size_nonexistent(self):
        """Test file size for nonexistent file."""
        nonexistent = self.test_path / "nonexistent.txt"
        size = get_file_size(nonexistent)
        self.assertEqual(size, 0)

    def test_count_text_content(self):
        """Test text content counting."""
        test_file = self.test_path / "test.txt"
        content = "Line 1\nLine 2\nLine 3"
        test_file.write_text(content)

        char_count, line_count = count_text_content(test_file)

        self.assertEqual(char_count, len(content))
        self.assertEqual(line_count, 3)

    def test_count_text_content_empty(self):
        """Test text counting for empty file."""
        test_file = self.test_path / "empty.txt"
        test_file.write_text("")

        char_count, line_count = count_text_content(test_file)

        self.assertEqual(char_count, 0)
        self.assertEqual(line_count, 0)

    def test_is_stub_content_small_file(self):
        """Test stub detection for small file."""
        test_file = self.test_path / "stub.txt"
        test_file.write_text("Small content")  # Less than 500 chars

        is_stub = is_stub_content(test_file, min_chars=500)
        self.assertTrue(is_stub)

    def test_is_stub_content_google_docs_indicator(self):
        """Test stub detection for Google Docs stub."""
        test_file = self.test_path / "gdocs_stub.txt"
        # Small file with Google Docs indicators
        test_file.write_text("Google Docs\nSign in\nFile Edit View Tools Help")

        is_stub = is_stub_content(test_file, min_chars=500)
        self.assertTrue(is_stub)

    def test_is_stub_content_valid_file(self):
        """Test stub detection for valid large file."""
        test_file = self.test_path / "valid.txt"
        # Large file with substantial content
        content = "This is a valid document with substantial content.\n" * 20
        test_file.write_text(content)

        is_stub = is_stub_content(test_file, min_chars=500)
        self.assertFalse(is_stub)

    def test_validate_file_empty_extraction(self):
        """Test validation of empty extraction."""
        raw_file = self.raw_dir / "test.pdf"
        preprocessed_file = self.preprocessed_dir / "test.txt"

        # Create files
        raw_file.write_text("Some raw content" * 100)
        preprocessed_file.write_text("")  # Empty extraction

        quality = validate_file(raw_file, preprocessed_file)

        self.assertTrue(quality.is_empty)
        self.assertTrue(quality.is_problematic)
        self.assertEqual(quality.issue, "Empty extraction")

    def test_validate_file_stub_extraction(self):
        """Test validation of stub extraction."""
        raw_file = self.raw_dir / "test.html"
        preprocessed_file = self.preprocessed_dir / "test.txt"

        # Create files
        raw_file.write_text("<html><body>Content</body></html>" * 100)
        preprocessed_file.write_text("Small stub")  # Less than 500 chars

        quality = validate_file(raw_file, preprocessed_file, min_chars=500)

        self.assertTrue(quality.is_stub)
        self.assertTrue(quality.is_problematic)
        self.assertIn("Stub file", quality.issue)

    def test_validate_file_low_extraction_rate(self):
        """Test validation of low extraction rate."""
        raw_file = self.raw_dir / "test.pdf"
        preprocessed_file = self.preprocessed_dir / "test.txt"

        # Create files - large raw, larger preprocessed but still low ratio
        # Need >500 chars to avoid stub detection, but <1% of raw to trigger low extraction
        raw_file.write_text("x" * 100000)
        preprocessed_file.write_text("x" * 600)  # 0.6% of raw size, but >500 chars

        quality = validate_file(raw_file, preprocessed_file, min_ratio=0.01)

        self.assertTrue(quality.is_problematic)
        self.assertIn("Significant data loss", quality.issue)

    def test_validate_file_good_quality(self):
        """Test validation of good quality extraction."""
        raw_file = self.raw_dir / "test.pdf"
        preprocessed_file = self.preprocessed_dir / "test.txt"

        # Create files with reasonable extraction ratio
        raw_content = "This is the raw PDF content. " * 100
        preprocessed_content = "This is the extracted text content. " * 50

        raw_file.write_text(raw_content)
        preprocessed_file.write_text(preprocessed_content)

        quality = validate_file(raw_file, preprocessed_file, min_ratio=0.01)

        self.assertFalse(quality.is_empty)
        self.assertFalse(quality.is_stub)
        self.assertFalse(quality.is_problematic)
        self.assertEqual(quality.issue, "")

    def test_validate_project_missing_outputs(self):
        """Test project validation with missing outputs."""
        # Create raw PDF without corresponding preprocessed file
        (self.raw_dir / "missing.pdf").write_text("Content")

        results = validate_project(
            self.raw_dir,
            self.preprocessed_dir,
            "TEST_PROJECT"
        )

        self.assertEqual(results["project"], "TEST_PROJECT")
        self.assertEqual(results["missing_outputs"], 1)

    def test_validate_project_problematic_files(self):
        """Test project validation with problematic files."""
        # Create raw and preprocessed files with quality issues
        (self.raw_dir / "problem.pdf").write_text("x" * 10000)
        (self.preprocessed_dir / "problem.txt").write_text("small")  # Stub

        results = validate_project(
            self.raw_dir,
            self.preprocessed_dir,
            "TEST_PROJECT"
        )

        self.assertEqual(results["project"], "TEST_PROJECT")
        self.assertGreater(results["problematic_files"], 0)
        self.assertGreater(results["stub_files"], 0)

    def test_validate_project_nonexistent_directory(self):
        """Test project validation with nonexistent directory."""
        nonexistent_dir = self.test_path / "nonexistent"

        results = validate_project(
            nonexistent_dir,
            self.preprocessed_dir,
            "TEST_PROJECT"
        )

        self.assertIn("error", results)

    def test_format_size_bytes(self):
        """Test size formatting for bytes."""
        self.assertEqual(format_size(512), "512.0B")

    def test_format_size_kb(self):
        """Test size formatting for kilobytes."""
        self.assertEqual(format_size(2048), "2.0KB")

    def test_format_size_mb(self):
        """Test size formatting for megabytes."""
        self.assertEqual(format_size(2 * 1024 * 1024), "2.0MB")

    def test_file_quality_dataclass(self):
        """Test FileQuality dataclass creation."""
        quality = FileQuality(
            raw_file=Path("test.pdf"),
            preprocessed_file=Path("test.txt"),
            raw_size=1000,
            preprocessed_size=500,
            size_ratio=0.5,
            char_count=500,
            line_count=10,
            is_empty=False,
            is_stub=False,
            is_problematic=False,
            issue=""
        )

        self.assertEqual(quality.raw_size, 1000)
        self.assertEqual(quality.preprocessed_size, 500)
        self.assertEqual(quality.size_ratio, 0.5)
        self.assertFalse(quality.is_problematic)


if __name__ == '__main__':
    unittest.main()
