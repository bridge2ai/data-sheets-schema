#!/usr/bin/env python3
"""
Tests for MappingLoader utility.

Tests TSV mapping file loading and lookup functions.
"""

import unittest
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.fairscape_integration.utils.mapping_loader import MappingLoader


class TestMappingLoader(unittest.TestCase):
    """Test MappingLoader TSV parsing and lookups."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary TSV mapping file
        self.tsv_content = """Class\tD4D Property\tType\tDef\tD4D description\tFAIRSCAPE RO-Crate Property\tCovered by FAIRSCAPE? Yes =1; No = 0\tDirect mapping? Yes =1; No = 0
D4D: Dataset\t\t\t\t\t\t\t
RO-Crate: Root Dataset\ttitle\tstr\t\tThe title of the dataset\tname\t1\t1
RO-Crate: Root Dataset\tdescription\tstr\t\tA description of the dataset\tdescription\t1\t1
RO-Crate: Root Dataset\tkeywords\tlist[str]\t\tKeywords for the dataset\tkeywords\t1\t1
RO-Crate: Root Dataset\tacquisition_methods\tstr\t\tData collection methods\trai:dataCollection,rai:dataCollectionType\t1\t0
RO-Crate: Root Dataset\taddressing_gaps\tstr\t\tGap being addressed\t*addressingGaps\t1\t1
RO-Crate: Root Dataset\tanomalies\tstr\t\tData anomalies\t*anomalies\t1\t1
RO-Crate: Root Dataset\tuncovered_field\tstr\t\tNot in RO-Crate\t\t0\t0
"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False)
        self.temp_file.write(self.tsv_content)
        self.temp_file.close()

        self.loader = MappingLoader(self.temp_file.name, verbose=False)

    def tearDown(self):
        """Clean up temporary files."""
        Path(self.temp_file.name).unlink()

    def test_loader_initialization(self):
        """Test loader initializes correctly."""
        self.assertEqual(self.loader.tsv_path, Path(self.temp_file.name))
        self.assertGreater(len(self.loader.mappings), 0)

    def test_loader_with_nonexistent_file(self):
        """Test loader raises error for nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            MappingLoader("/nonexistent/file.tsv")

    def test_get_covered_fields(self):
        """Test getting covered D4D fields."""
        covered = self.loader.get_covered_fields()

        self.assertIn('title', covered)
        self.assertIn('description', covered)
        self.assertIn('keywords', covered)
        self.assertIn('acquisition_methods', covered)
        self.assertNotIn('uncovered_field', covered)

    def test_get_rocrate_to_d4d_mapping(self):
        """Test RO-Crate to D4D mapping dictionary."""
        mapping = self.loader.get_rocrate_to_d4d_mapping()

        self.assertEqual(mapping['name'], 'title')
        self.assertEqual(mapping['description'], 'description')
        self.assertEqual(mapping['keywords'], 'keywords')

    def test_get_d4d_to_rocrate_mapping(self):
        """Test D4D to RO-Crate mapping dictionary."""
        mapping = self.loader.get_d4d_to_rocrate_mapping()

        self.assertEqual(mapping['title'], 'name')
        self.assertEqual(mapping['description'], 'description')
        self.assertEqual(mapping['keywords'], 'keywords')

    def test_get_rocrate_property(self):
        """Test lookup of RO-Crate property from D4D field."""
        self.assertEqual(self.loader.get_rocrate_property('title'), 'name')
        self.assertEqual(self.loader.get_rocrate_property('description'), 'description')
        self.assertIsNone(self.loader.get_rocrate_property('nonexistent_field'))

    def test_get_d4d_field(self):
        """Test lookup of D4D field from RO-Crate property."""
        self.assertEqual(self.loader.get_d4d_field('name'), 'title')
        self.assertEqual(self.loader.get_d4d_field('description'), 'description')
        self.assertIsNone(self.loader.get_d4d_field('nonexistent_property'))

    def test_is_direct_mapping(self):
        """Test direct mapping detection."""
        self.assertTrue(self.loader.is_direct_mapping('title'))
        self.assertTrue(self.loader.is_direct_mapping('description'))
        self.assertFalse(self.loader.is_direct_mapping('acquisition_methods'))

    def test_get_mapping_info(self):
        """Test getting complete mapping info."""
        info = self.loader.get_mapping_info('title')

        self.assertIsNotNone(info)
        self.assertEqual(info['D4D Property'], 'title')
        self.assertEqual(info['FAIRSCAPE RO-Crate Property'], 'name')
        self.assertEqual(info['Type'], 'str')

    def test_get_mapping_info_nonexistent(self):
        """Test getting mapping info for nonexistent field."""
        info = self.loader.get_mapping_info('nonexistent_field')
        self.assertIsNone(info)

    def test_get_all_mapped_rocrate_properties(self):
        """Test getting all mapped RO-Crate properties."""
        properties = self.loader.get_all_mapped_rocrate_properties()

        self.assertIn('name', properties)
        self.assertIn('description', properties)
        self.assertIn('keywords', properties)
        self.assertIn('*addressingGaps', properties)

    def test_multiple_rocrate_properties_mapping(self):
        """Test handling of multiple RO-Crate properties mapping to one D4D field."""
        # acquisition_methods maps to "rai:dataCollection,rai:dataCollectionType"
        rocrate_prop = self.loader.get_rocrate_property('acquisition_methods')
        self.assertIn(',', rocrate_prop)

        # Both RO-Crate properties should map back to the same D4D field
        self.assertEqual(self.loader.get_d4d_field('rai:dataCollection'), 'acquisition_methods')
        self.assertEqual(self.loader.get_d4d_field('rai:dataCollectionType'), 'acquisition_methods')

    def test_get_statistics(self):
        """Test getting mapping statistics."""
        stats = self.loader.get_statistics()

        self.assertIn('total_mappings', stats)
        self.assertIn('covered_mappings', stats)
        self.assertIn('d4d_to_rocrate', stats)
        self.assertIn('rocrate_to_d4d', stats)
        self.assertIn('direct_mappings', stats)

        # Verify counts
        self.assertGreater(stats['total_mappings'], 0)
        self.assertGreater(stats['covered_mappings'], 0)
        self.assertEqual(stats['covered_mappings'], 6)  # 6 covered fields in test data

    def test_mapping_copy_returns_new_dict(self):
        """Test that mapping getters return copies, not references."""
        mapping1 = self.loader.get_d4d_to_rocrate_mapping()
        mapping2 = self.loader.get_d4d_to_rocrate_mapping()

        # Should be equal but not the same object
        self.assertEqual(mapping1, mapping2)
        self.assertIsNot(mapping1, mapping2)

        # Modifying one shouldn't affect the other
        mapping1['test_key'] = 'test_value'
        self.assertNotIn('test_key', mapping2)


class TestMappingLoaderWithRealFile(unittest.TestCase):
    """Test MappingLoader with real mapping file if available."""

    def test_load_real_mapping_file(self):
        """Test loading actual D4D-RO-Crate mapping file."""
        # Try to load the real mapping file if it exists
        real_tsv = repo_root / "data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv"

        if not real_tsv.exists():
            self.skipTest("Real mapping file not found")

        loader = MappingLoader(str(real_tsv), verbose=False)

        # Basic sanity checks
        self.assertGreater(len(loader.mappings), 0)
        self.assertGreater(len(loader.covered_mappings), 0)

        # Check some known mappings
        covered = loader.get_covered_fields()
        self.assertIsInstance(covered, list)

        # Get statistics
        stats = loader.get_statistics()
        self.assertGreater(stats['covered_mappings'], 10)  # Should have many mappings


if __name__ == '__main__':
    unittest.main()
