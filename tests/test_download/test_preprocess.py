#!/usr/bin/env python3
"""
Unit tests for preprocess_sources.py

Tests preprocessing functionality (PDF/HTML extraction).
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.download.preprocess_sources import (
        extract_pdf_text,
        extract_html_text,
        preprocess_project
    )
except ImportError as e:
    print(f"Warning: Could not import preprocess_sources: {e}", file=sys.stderr)
    extract_pdf_text = None
    extract_html_text = None
    preprocess_project = None


class TestPreprocessing(unittest.TestCase):
    """Test preprocessing functionality."""

    def setUp(self):
        """Set up test fixtures."""
        if extract_html_text is None:
            self.skipTest("preprocess_sources module not available")

        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.src_dir = self.test_path / "src"
        self.dst_dir = self.test_path / "dst"
        self.src_dir.mkdir()
        self.dst_dir.mkdir()

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, 'test_dir'):
            shutil.rmtree(self.test_dir)

    def test_extract_html_basic(self):
        """Test basic HTML text extraction."""
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <h1>Header</h1>
                <p>This is a test paragraph.</p>
            </body>
        </html>
        """
        html_file = self.src_dir / "test.html"
        html_file.write_text(html_content)

        extracted_text = extract_html_text(html_file)

        self.assertIn("Header", extracted_text)
        self.assertIn("test paragraph", extracted_text)
        self.assertNotIn("<html>", extracted_text)  # Tags should be removed

    def test_extract_html_removes_scripts(self):
        """Test that script and style tags are removed."""
        html_content = """
        <html>
            <head>
                <style>body { color: red; }</style>
                <script>alert('test');</script>
            </head>
            <body>
                <p>Visible content</p>
                <script>console.log('hidden');</script>
            </body>
        </html>
        """
        html_file = self.src_dir / "test_scripts.html"
        html_file.write_text(html_content)

        extracted_text = extract_html_text(html_file)

        self.assertIn("Visible content", extracted_text)
        self.assertNotIn("color: red", extracted_text)
        self.assertNotIn("alert", extracted_text)
        self.assertNotIn("console.log", extracted_text)

    def test_extract_html_error_handling(self):
        """Test HTML extraction error handling."""
        nonexistent_file = self.src_dir / "nonexistent.html"

        # Should return empty string on error, not crash
        result = extract_html_text(nonexistent_file)
        self.assertEqual(result, "")

    def test_preprocess_project_txt_files(self):
        """Test preprocessing of .txt files (should be copied as-is)."""
        # Create test .txt file
        txt_file = self.src_dir / "test.txt"
        txt_content = "This is plain text content.\n"
        txt_file.write_text(txt_content)

        stats = preprocess_project(self.src_dir, self.dst_dir)

        # Should have copied the file
        self.assertEqual(stats['copied'], 1)

        # Output file should exist and match content
        output_file = self.dst_dir / "test.txt"
        self.assertTrue(output_file.exists())
        self.assertEqual(output_file.read_text(), txt_content)

    def test_preprocess_project_json_files(self):
        """Test preprocessing of .json files (should be preserved)."""
        json_file = self.src_dir / "test.json"
        json_content = '{"key": "value"}'
        json_file.write_text(json_content)

        stats = preprocess_project(self.src_dir, self.dst_dir)

        self.assertEqual(stats['copied'], 1)

        output_file = self.dst_dir / "test.json"
        self.assertTrue(output_file.exists())
        self.assertEqual(output_file.read_text(), json_content)

    def test_preprocess_project_html_files(self):
        """Test preprocessing of .html files (should extract text)."""
        html_file = self.src_dir / "test.html"
        html_content = """<html><body>
            <h1>Test HTML Document</h1>
            <p>This is a test paragraph with sufficient content to pass the minimum character threshold.</p>
            <p>The HTML extraction requires more than 100 characters of text content.</p>
            <p>This third paragraph ensures we have enough content for the test to pass successfully.</p>
        </body></html>"""
        html_file.write_text(html_content)

        stats = preprocess_project(self.src_dir, self.dst_dir)

        # Should have extracted HTML
        self.assertEqual(stats['html_extracted'], 1)

        # Output should be .txt file
        output_file = self.dst_dir / "test.txt"
        self.assertTrue(output_file.exists())

        output_content = output_file.read_text()
        self.assertIn("Test HTML Document", output_content)
        self.assertIn("sufficient content", output_content)
        self.assertGreater(len(output_content), 100)  # Verify meets minimum threshold

    def test_preprocess_project_skips_directories(self):
        """Test that subdirectories are skipped."""
        subdir = self.src_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("Nested content")

        stats = preprocess_project(self.src_dir, self.dst_dir)

        # Should not process files in subdirectories
        self.assertFalse((self.dst_dir / "subdir" / "nested.txt").exists())

    def test_preprocess_project_nonexistent_directory(self):
        """Test handling of nonexistent source directory."""
        nonexistent = self.test_path / "nonexistent"

        stats = preprocess_project(nonexistent, self.dst_dir)

        # Should return stats with no operations
        self.assertEqual(stats['copied'], 0)
        self.assertEqual(stats['html_extracted'], 0)

    def test_preprocess_creates_output_directory(self):
        """Test that output directory is created if it doesn't exist."""
        new_dst = self.test_path / "new_destination"

        # Create a source file
        (self.src_dir / "test.txt").write_text("content")

        # Preprocess to non-existent destination
        stats = preprocess_project(self.src_dir, new_dst)

        # Destination should have been created
        self.assertTrue(new_dst.exists())
        self.assertEqual(stats['copied'], 1)


if __name__ == '__main__':
    unittest.main()
