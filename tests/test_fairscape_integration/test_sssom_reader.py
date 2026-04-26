#!/usr/bin/env python3
"""
Tests for SSSOMReader utility.

Tests SSSOM file reading and querying.
"""

import unittest
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.fairscape_integration.utils.sssom_reader import SSSOMReader, SSSOMMapping


class TestSSSOMReader(unittest.TestCase):
    """Test SSSOMReader SSSOM file reading and querying."""

    def setUp(self):
        """Set up test fixtures."""
        # Create test SSSOM TSV
        self.sssom_content = """# Test SSSOM mapping file
# Comment line
subject_id\tsubject_label\tpredicate_id\tobject_id\tobject_label\tmapping_justification\tconfidence\tsubject_source\tobject_source\tcomment\tmapping_status
d4d:title\ttitle\tskos:exactMatch\tname\tname\tsemapv:ManualMappingCuration\t1.0\td4d:schema\trocrate:schema\tDirect mapping\tmapped
d4d:description\tdescription\tskos:exactMatch\tdescription\tdescription\tsemapv:ManualMappingCuration\t1.0\td4d:schema\trocrate:schema\tDirect mapping\tmapped
d4d:keywords\tkeywords\tskos:exactMatch\tkeywords\tkeywords\tsemapv:ManualMappingCuration\t0.9\td4d:schema\trocrate:schema\tArray field\tmapped
d4d:version\tversion\tskos:closeMatch\tversion\tversion\tsemapv:ManualMappingCuration\t0.8\td4d:schema\trocrate:schema\tType differs\trecommended
d4d:novel_field\tnovel_field\tsemapv:UnmappedProperty\t\t\tsemapv:UnmappableProperty\t\td4d:schema\t\tNo RO-Crate equivalent\tunmapped
"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False, encoding='utf-8')
        self.temp_file.write(self.sssom_content)
        self.temp_file.close()

        self.reader = SSSOMReader(self.temp_file.name, verbose=False)

    def tearDown(self):
        """Clean up temporary files."""
        Path(self.temp_file.name).unlink()

    def test_reader_initialization(self):
        """Test reader initializes correctly."""
        self.assertEqual(self.reader.sssom_path, Path(self.temp_file.name))
        self.assertGreater(len(self.reader.mappings), 0)
        self.assertFalse(self.reader.verbose)

    def test_reader_with_verbose(self):
        """Test reader with verbose output."""
        verbose_reader = SSSOMReader(self.temp_file.name, verbose=True)
        self.assertTrue(verbose_reader.verbose)

    def test_reader_with_nonexistent_file(self):
        """Test reader raises error for nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            SSSOMReader("/nonexistent/file.tsv")

    def test_load_mappings(self):
        """Test loading mappings from SSSOM file."""
        mappings = self.reader.get_all_mappings()

        self.assertEqual(len(mappings), 5)
        self.assertIsInstance(mappings[0], SSSOMMapping)

    def test_mapping_fields(self):
        """Test that mapping fields are correctly parsed."""
        mapping = self.reader.get_by_subject('d4d:title')[0]

        self.assertEqual(mapping.subject_id, 'd4d:title')
        self.assertEqual(mapping.subject_label, 'title')
        self.assertEqual(mapping.predicate_id, 'skos:exactMatch')
        self.assertEqual(mapping.object_id, 'name')
        self.assertEqual(mapping.object_label, 'name')
        self.assertEqual(mapping.mapping_justification, 'semapv:ManualMappingCuration')
        self.assertEqual(mapping.confidence, 1.0)
        self.assertEqual(mapping.subject_source, 'd4d:schema')
        self.assertEqual(mapping.object_source, 'rocrate:schema')
        self.assertEqual(mapping.comment, 'Direct mapping')
        self.assertEqual(mapping.mapping_status, 'mapped')

    def test_get_by_subject(self):
        """Test getting mappings by subject ID."""
        mappings = self.reader.get_by_subject('d4d:description')

        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0].subject_id, 'd4d:description')
        self.assertEqual(mappings[0].object_id, 'description')

    def test_get_by_subject_nonexistent(self):
        """Test getting mappings for nonexistent subject."""
        mappings = self.reader.get_by_subject('d4d:nonexistent')

        self.assertEqual(len(mappings), 0)

    def test_get_by_object(self):
        """Test getting mappings by object ID."""
        mappings = self.reader.get_by_object('keywords')

        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0].subject_id, 'd4d:keywords')

    def test_get_by_object_nonexistent(self):
        """Test getting mappings for nonexistent object."""
        mappings = self.reader.get_by_object('nonexistent')

        self.assertEqual(len(mappings), 0)

    def test_get_by_predicate(self):
        """Test getting mappings by predicate."""
        mappings = self.reader.get_by_predicate('skos:exactMatch')

        self.assertEqual(len(mappings), 3)
        for mapping in mappings:
            self.assertEqual(mapping.predicate_id, 'skos:exactMatch')

    def test_get_by_predicate_close_match(self):
        """Test getting close match mappings."""
        mappings = self.reader.get_by_predicate('skos:closeMatch')

        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0].subject_id, 'd4d:version')

    def test_get_exact_matches(self):
        """Test getting exact match mappings."""
        mappings = self.reader.get_exact_matches()

        self.assertEqual(len(mappings), 3)
        for mapping in mappings:
            self.assertEqual(mapping.predicate_id, 'skos:exactMatch')

    def test_get_mapped_subjects(self):
        """Test getting set of mapped subjects."""
        subjects = self.reader.get_mapped_subjects()

        self.assertIsInstance(subjects, set)
        self.assertIn('d4d:title', subjects)
        self.assertIn('d4d:description', subjects)
        self.assertIn('d4d:keywords', subjects)
        self.assertEqual(len(subjects), 5)

    def test_get_mapped_objects(self):
        """Test getting set of mapped objects."""
        objects = self.reader.get_mapped_objects()

        self.assertIsInstance(objects, set)
        self.assertIn('name', objects)
        self.assertIn('description', objects)
        self.assertIn('keywords', objects)

    def test_get_predicates(self):
        """Test getting set of predicates."""
        predicates = self.reader.get_predicates()

        self.assertIsInstance(predicates, set)
        self.assertIn('skos:exactMatch', predicates)
        self.assertIn('skos:closeMatch', predicates)
        self.assertIn('semapv:UnmappedProperty', predicates)

    def test_get_statistics(self):
        """Test getting mapping statistics."""
        stats = self.reader.get_statistics()

        self.assertIn('total_mappings', stats)
        self.assertIn('unique_subjects', stats)
        self.assertIn('unique_objects', stats)
        self.assertIn('predicates', stats)
        self.assertIn('predicate_counts', stats)
        self.assertIn('status_counts', stats)
        self.assertIn('avg_confidence', stats)
        self.assertIn('mappings_with_confidence', stats)

        # Verify counts
        self.assertEqual(stats['total_mappings'], 5)
        self.assertEqual(stats['unique_subjects'], 5)
        self.assertEqual(stats['predicates'], 3)

        # Verify predicate counts
        self.assertEqual(stats['predicate_counts']['skos:exactMatch'], 3)
        self.assertEqual(stats['predicate_counts']['skos:closeMatch'], 1)

        # Verify status counts
        self.assertEqual(stats['status_counts']['mapped'], 3)
        self.assertEqual(stats['status_counts']['recommended'], 1)
        self.assertEqual(stats['status_counts']['unmapped'], 1)

    def test_filter_by_confidence(self):
        """Test filtering by confidence threshold."""
        high_conf = self.reader.filter_by_confidence(0.95)

        # Should have 2 mappings with confidence >= 0.95 (title and description)
        self.assertEqual(len(high_conf), 2)
        for mapping in high_conf:
            self.assertGreaterEqual(mapping.confidence, 0.95)

    def test_filter_by_confidence_medium(self):
        """Test filtering by medium confidence threshold."""
        medium_conf = self.reader.filter_by_confidence(0.8)

        # Should have 4 mappings with confidence >= 0.8
        self.assertEqual(len(medium_conf), 4)

    def test_filter_by_status(self):
        """Test filtering by mapping status."""
        mapped = self.reader.filter_by_status('mapped')

        self.assertEqual(len(mapped), 3)
        for mapping in mapped:
            self.assertEqual(mapping.mapping_status, 'mapped')

    def test_filter_by_status_unmapped(self):
        """Test filtering by unmapped status."""
        unmapped = self.reader.filter_by_status('unmapped')

        self.assertEqual(len(unmapped), 1)
        self.assertEqual(unmapped[0].subject_id, 'd4d:novel_field')


class TestSSSOMReaderWithRealFile(unittest.TestCase):
    """Test SSSOMReader with real SSSOM file."""

    def test_load_structural_mapping(self):
        """Test loading structural mapping file."""
        sssom_file = repo_root / "data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv"

        if not sssom_file.exists():
            self.skipTest("Structural SSSOM file not found")

        reader = SSSOMReader(str(sssom_file), verbose=False)

        # Basic sanity checks
        self.assertGreater(len(reader.mappings), 50)
        self.assertGreater(len(reader.get_mapped_subjects()), 50)

        # Check statistics
        stats = reader.get_statistics()
        self.assertGreater(stats['total_mappings'], 50)
        self.assertIn('skos:exactMatch', stats['predicate_counts'])

        # Check exact matches
        exact_matches = reader.get_exact_matches()
        self.assertGreater(len(exact_matches), 50)


if __name__ == '__main__':
    unittest.main()
