#!/usr/bin/env python3
"""
Unit tests for concatenate_documents.py

Tests document concatenation functionality.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.download.concatenate_documents import DocumentConcatenator
except ImportError as e:
    print(f"Warning: Could not import concatenate_documents: {e}", file=sys.stderr)
    DocumentConcatenator = None


class TestDocumentConcatenation(unittest.TestCase):
    """Test document concatenation functionality."""

    def setUp(self):
        """Set up test fixtures - create temporary directory with test files."""
        if DocumentConcatenator is None:
            self.skipTest("concatenate_documents module not available")

        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

        # Create test files
        (self.test_path / "file1.txt").write_text("Content of file 1\nLine 2\n")
        (self.test_path / "file2.txt").write_text("Content of file 2\n")
        (self.test_path / "file3.md").write_text("# Markdown file\nSome content\n")

        # Create a subdirectory with files (for recursive testing)
        subdir = self.test_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("Nested file content\n")

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, 'test_dir'):
            shutil.rmtree(self.test_dir)

    def test_concatenator_initialization(self):
        """Test DocumentConcatenator initialization."""
        concatenator = DocumentConcatenator()
        self.assertIsNotNone(concatenator)

    def test_get_files_sorted_basic(self):
        """Test getting sorted file list."""
        concatenator = DocumentConcatenator()
        files = concatenator.get_files_sorted(
            self.test_path,
            extensions=['.txt'],
            recursive=False
        )

        # Should find 2 .txt files
        self.assertEqual(len(files), 2)
        # Files should be sorted
        self.assertTrue(all(isinstance(f, Path) for f in files))

    def test_get_files_sorted_multiple_extensions(self):
        """Test file discovery with multiple extensions."""
        concatenator = DocumentConcatenator()
        files = concatenator.get_files_sorted(
            self.test_path,
            extensions=['.txt', '.md'],
            recursive=False
        )

        # Should find 3 files (.txt and .md)
        self.assertEqual(len(files), 3)

    def test_get_files_sorted_recursive(self):
        """Test recursive file discovery."""
        concatenator = DocumentConcatenator()
        files = concatenator.get_files_sorted(
            self.test_path,
            extensions=['.txt'],
            recursive=True
        )

        # Should find 3 .txt files including nested one
        self.assertEqual(len(files), 3)

    def test_get_files_sorted_alphabetical(self):
        """Test that files are returned in alphabetical order."""
        concatenator = DocumentConcatenator()
        files = concatenator.get_files_sorted(
            self.test_path,
            extensions=['.txt'],
            recursive=False
        )

        # Files should be in alphabetical order
        file_names = [f.name for f in files]
        self.assertEqual(file_names, sorted(file_names))

    def test_read_file_content(self):
        """Test file content reading."""
        concatenator = DocumentConcatenator()
        test_file = self.test_path / "file1.txt"

        content = concatenator.read_file_content(test_file)

        self.assertIn("Content of file 1", content)
        self.assertIn("Line 2", content)

    def test_create_file_header(self):
        """Test file header creation."""
        concatenator = DocumentConcatenator()
        test_file = self.test_path / "file1.txt"

        header = concatenator.create_file_header(test_file, relative_to=self.test_path)

        self.assertIn("file1.txt", header)
        # Header should contain some metadata
        self.assertGreater(len(header), 10)

    def test_nonexistent_directory(self):
        """Test handling of nonexistent directory."""
        concatenator = DocumentConcatenator()
        nonexistent = self.test_path / "does_not_exist"

        with self.assertRaises(FileNotFoundError):
            concatenator.get_files_sorted(nonexistent)

    def test_empty_directory(self):
        """Test file discovery in empty directory."""
        empty_dir = self.test_path / "empty"
        empty_dir.mkdir()

        concatenator = DocumentConcatenator()
        files = concatenator.get_files_sorted(empty_dir, extensions=['.txt'])

        self.assertEqual(len(files), 0)


if __name__ == '__main__':
    unittest.main()
