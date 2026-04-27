#!/usr/bin/env python3
"""
Tests for SSSOM Integration utility.

Tests integration with standard sssom-py package with fallback to custom reader.
"""

import unittest
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.fairscape_integration.utils.sssom_integration import SSSOMIntegration, SSSOM_AVAILABLE


class TestSSSOMIntegration(unittest.TestCase):
    """Test SSSOMIntegration with standard sssom-py or fallback."""

    def setUp(self):
        """Set up test fixtures."""
        # Create test SSSOM TSV
        self.sssom_content = """# Test SSSOM mapping file
subject_id\tsubject_label\tpredicate_id\tobject_id\tobject_label\tmapping_justification\tconfidence\tsubject_source\tobject_source\tmapping_status
d4d:title\ttitle\tskos:exactMatch\tname\tname\tsemapv:ManualMappingCuration\t1.0\td4d:schema\trocrate:schema\tmapped
d4d:description\tdescription\tskos:exactMatch\tdescription\tdescription\tsemapv:ManualMappingCuration\t1.0\td4d:schema\trocrate:schema\tmapped
d4d:keywords\tkeywords\tskos:exactMatch\tkeywords\tkeywords\tsemapv:ManualMappingCuration\t0.9\td4d:schema\trocrate:schema\tmapped
d4d:version\tversion\tskos:closeMatch\tversion\tversion\tsemapv:ManualMappingCuration\t0.8\td4d:schema\trocrate:schema\trecommended
"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False, encoding='utf-8')
        self.temp_file.write(self.sssom_content)
        self.temp_file.close()

        self.integration = SSSOMIntegration(self.temp_file.name, verbose=False)

    def tearDown(self):
        """Clean up temporary files."""
        Path(self.temp_file.name).unlink()

    def test_integration_initialization(self):
        """Test integration initializes correctly."""
        self.assertEqual(self.integration.sssom_path, Path(self.temp_file.name))
        self.assertFalse(self.integration.verbose)

    def test_is_sssom_available(self):
        """Test checking if sssom-py is available."""
        result = SSSOMIntegration.is_sssom_available()
        self.assertIsInstance(result, bool)

        # Should match module-level constant
        self.assertEqual(result, SSSOM_AVAILABLE)

    def test_get_implementation(self):
        """Test getting implementation type."""
        impl = SSSOMIntegration.get_implementation()
        self.assertIn(impl, ['sssom-py', 'custom'])

    def test_get_mappings_count(self):
        """Test getting total number of mappings."""
        count = self.integration.get_mappings_count()
        self.assertEqual(count, 4)

    def test_get_mappings_by_subject(self):
        """Test getting mappings by subject ID."""
        mappings = self.integration.get_mappings_by_subject('d4d:title')

        self.assertIsInstance(mappings, list)
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]['subject_id'], 'd4d:title')
        self.assertEqual(mappings[0]['object_id'], 'name')

    def test_get_mappings_by_subject_nonexistent(self):
        """Test getting mappings for nonexistent subject."""
        mappings = self.integration.get_mappings_by_subject('d4d:nonexistent')
        self.assertEqual(len(mappings), 0)

    def test_get_mappings_by_object(self):
        """Test getting mappings by object ID."""
        mappings = self.integration.get_mappings_by_object('description')

        self.assertIsInstance(mappings, list)
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]['subject_id'], 'd4d:description')

    def test_get_mappings_by_predicate(self):
        """Test getting mappings by predicate."""
        mappings = self.integration.get_mappings_by_predicate('skos:exactMatch')

        self.assertIsInstance(mappings, list)
        self.assertEqual(len(mappings), 3)
        for mapping in mappings:
            self.assertEqual(mapping['predicate_id'], 'skos:exactMatch')

    def test_get_exact_matches(self):
        """Test getting exact match mappings."""
        mappings = self.integration.get_exact_matches()

        self.assertEqual(len(mappings), 3)
        for mapping in mappings:
            self.assertEqual(mapping['predicate_id'], 'skos:exactMatch')

    def test_get_subjects(self):
        """Test getting set of subject IDs."""
        subjects = self.integration.get_subjects()

        self.assertIsInstance(subjects, set)
        self.assertIn('d4d:title', subjects)
        self.assertIn('d4d:description', subjects)
        self.assertEqual(len(subjects), 4)

    def test_get_objects(self):
        """Test getting set of object IDs."""
        objects = self.integration.get_objects()

        self.assertIsInstance(objects, set)
        self.assertIn('name', objects)
        self.assertIn('description', objects)

    def test_get_predicates(self):
        """Test getting set of predicates."""
        predicates = self.integration.get_predicates()

        self.assertIsInstance(predicates, set)
        self.assertIn('skos:exactMatch', predicates)
        self.assertIn('skos:closeMatch', predicates)

    def test_filter_by_confidence(self):
        """Test filtering by confidence threshold."""
        high_conf = self.integration.filter_by_confidence(0.95)

        self.assertIsInstance(high_conf, list)
        # Should have 2 mappings with confidence >= 0.95
        self.assertEqual(len(high_conf), 2)

    def test_get_statistics(self):
        """Test getting statistics."""
        stats = self.integration.get_statistics()

        self.assertIsInstance(stats, dict)
        self.assertIn('total_mappings', stats)
        self.assertIn('unique_subjects', stats)
        self.assertIn('unique_objects', stats)
        self.assertIn('predicates', stats)
        self.assertIn('predicate_counts', stats)

        # Verify counts
        self.assertEqual(stats['total_mappings'], 4)
        self.assertEqual(stats['predicate_counts']['skos:exactMatch'], 3)
        self.assertEqual(stats['predicate_counts']['skos:closeMatch'], 1)


class TestSSSOMIntegrationWithRealFile(unittest.TestCase):
    """Test SSSOM integration with real SSSOM file."""

    def test_load_structural_mapping(self):
        """Test loading real structural mapping file."""
        sssom_file = repo_root / "data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv"

        if not sssom_file.exists():
            self.skipTest("Structural SSSOM file not found")

        integration = SSSOMIntegration(str(sssom_file), verbose=False)

        # Basic checks
        self.assertGreater(integration.get_mappings_count(), 50)
        self.assertGreater(len(integration.get_subjects()), 50)

        # Get exact matches
        exact_matches = integration.get_exact_matches()
        self.assertGreater(len(exact_matches), 50)

        # Get statistics
        stats = integration.get_statistics()
        self.assertGreater(stats['total_mappings'], 50)
        self.assertIn('skos:exactMatch', stats['predicate_counts'])


if __name__ == '__main__':
    unittest.main()
