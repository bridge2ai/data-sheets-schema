#!/usr/bin/env python3
"""
Tests for ROCrateMerger utility.

Tests merging multiple RO-Crate sources into single D4D dataset.
"""

import unittest
import sys
import tempfile
import json
from pathlib import Path

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.fairscape_integration.utils.rocrate_merger import ROCrateMerger
from src.fairscape_integration.utils.rocrate_parser import ROCrateParser
from src.fairscape_integration.utils.mapping_loader import MappingLoader


class TestROCrateMerger(unittest.TestCase):
    """Test ROCrateMerger multi-source merging."""

    def setUp(self):
        """Set up test fixtures."""
        # Create test mapping TSV
        self.tsv_content = """Class\tD4D Property\tType\tDef\tD4D description\tFAIRSCAPE RO-Crate Property\tCovered by FAIRSCAPE? Yes =1; No = 0\tDirect mapping? Yes =1; No = 0
D4D: Dataset\t\t\t\t\t\t\t
RO-Crate: Root Dataset\ttitle\tstr\t\tThe title\tname\t1\t1
RO-Crate: Root Dataset\tdescription\tstr\t\tThe description\tdescription\t1\t1
RO-Crate: Root Dataset\tkeywords\tlist[str]\t\tKeywords\tkeywords\t1\t1
RO-Crate: Root Dataset\tversion\tstr\t\tVersion\tversion\t1\t1
RO-Crate: Root Dataset\tlicense\tstr\t\tLicense\tlicense\t1\t1
"""
        self.temp_tsv = tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False)
        self.temp_tsv.write(self.tsv_content)
        self.temp_tsv.close()

        self.mapping_loader = MappingLoader(self.temp_tsv.name, verbose=False)

        # Create primary RO-Crate
        self.primary_rocrate = {
            "@context": "https://w3id.org/ro/crate/1.1/context",
            "@graph": [
                {
                    "@id": "ro-crate-metadata.json",
                    "@type": "CreativeWork",
                    "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
                    "about": {"@id": "./"}
                },
                {
                    "@id": "./",
                    "@type": "Dataset",
                    "name": "Primary Dataset",
                    "description": "Primary description",
                    "keywords": ["primary"],
                    "version": "1.0"
                }
            ]
        }

        # Create secondary RO-Crate 1 (has unique fields)
        self.secondary1_rocrate = {
            "@context": "https://w3id.org/ro/crate/1.1/context",
            "@graph": [
                {
                    "@id": "ro-crate-metadata.json",
                    "@type": "CreativeWork",
                    "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
                    "about": {"@id": "./"}
                },
                {
                    "@id": "./",
                    "@type": "Dataset",
                    "name": "Secondary Dataset 1",
                    "description": "Secondary description 1",
                    "keywords": ["secondary1"],
                    "license": "MIT"  # Unique to secondary1
                }
            ]
        }

        # Create secondary RO-Crate 2 (overlaps with primary)
        self.secondary2_rocrate = {
            "@context": "https://w3id.org/ro/crate/1.1/context",
            "@graph": [
                {
                    "@id": "ro-crate-metadata.json",
                    "@type": "CreativeWork",
                    "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
                    "about": {"@id": "./"}
                },
                {
                    "@id": "./",
                    "@type": "Dataset",
                    "name": "Secondary Dataset 2",
                    "description": "Secondary description 2",
                    "keywords": ["secondary2"],
                    "version": "2.0"  # Conflicts with primary version
                }
            ]
        }

        # Write RO-Crate files
        self.primary_file = tempfile.NamedTemporaryFile(mode='w', suffix='-primary-ro-crate-metadata.json', delete=False)
        json.dump(self.primary_rocrate, self.primary_file)
        self.primary_file.close()

        self.secondary1_file = tempfile.NamedTemporaryFile(mode='w', suffix='-secondary1-ro-crate-metadata.json', delete=False)
        json.dump(self.secondary1_rocrate, self.secondary1_file)
        self.secondary1_file.close()

        self.secondary2_file = tempfile.NamedTemporaryFile(mode='w', suffix='-secondary2-ro-crate-metadata.json', delete=False)
        json.dump(self.secondary2_rocrate, self.secondary2_file)
        self.secondary2_file.close()

        self.primary_parser = ROCrateParser(self.primary_file.name, verbose=False)
        self.secondary1_parser = ROCrateParser(self.secondary1_file.name, verbose=False)
        self.secondary2_parser = ROCrateParser(self.secondary2_file.name, verbose=False)

        self.merger = ROCrateMerger(self.mapping_loader, verbose=False)

    def tearDown(self):
        """Clean up temporary files."""
        Path(self.temp_tsv.name).unlink()
        Path(self.primary_file.name).unlink()
        Path(self.secondary1_file.name).unlink()
        Path(self.secondary2_file.name).unlink()

    def test_merger_initialization(self):
        """Test merger initializes correctly."""
        self.assertIsNotNone(self.merger.mapping)
        self.assertIsNotNone(self.merger.prioritizer)
        self.assertEqual(self.merger.merged_data, {})
        self.assertEqual(self.merger.provenance, {})
        self.assertFalse(self.merger.verbose)

    def test_merger_with_verbose(self):
        """Test merger with verbose output."""
        verbose_merger = ROCrateMerger(self.mapping_loader, verbose=True)
        self.assertTrue(verbose_merger.verbose)

    def test_merge_single_rocrate(self):
        """Test merging single RO-Crate."""
        dataset = self.merger.merge_rocrates([self.primary_parser])

        self.assertIsInstance(dataset, dict)
        self.assertGreater(len(dataset), 0)
        self.assertEqual(dataset['title'], 'Primary Dataset')

    def test_merge_multiple_rocrates(self):
        """Test merging multiple RO-Crates."""
        parsers = [self.primary_parser, self.secondary1_parser, self.secondary2_parser]
        dataset = self.merger.merge_rocrates(parsers)

        self.assertIsInstance(dataset, dict)
        self.assertGreater(len(dataset), 0)

        # Should have primary title (primary wins)
        self.assertEqual(dataset['title'], 'Primary Dataset')

        # Should have unique field from secondary1
        self.assertIn('license', dataset)
        self.assertEqual(dataset['license'], 'MIT')

    def test_merge_with_no_parsers(self):
        """Test merging with empty parser list raises error."""
        with self.assertRaises(ValueError) as cm:
            self.merger.merge_rocrates([])

        self.assertIn("No RO-Crate parsers provided", str(cm.exception))

    def test_merge_with_invalid_primary_index(self):
        """Test merging with out-of-range primary index raises error."""
        with self.assertRaises(ValueError) as cm:
            self.merger.merge_rocrates([self.primary_parser], primary_index=10)

        self.assertIn("Primary index", str(cm.exception))

    def test_merge_with_custom_primary_index(self):
        """Test merging with non-zero primary index."""
        parsers = [self.primary_parser, self.secondary1_parser]
        dataset = self.merger.merge_rocrates(parsers, primary_index=1)

        # Secondary1 should be primary now
        self.assertEqual(dataset['title'], 'Secondary Dataset 1')

    def test_merge_with_custom_source_names(self):
        """Test merging with custom source names."""
        parsers = [self.primary_parser, self.secondary1_parser]
        source_names = ['Source A', 'Source B']

        dataset = self.merger.merge_rocrates(parsers, source_names=source_names)

        provenance = self.merger.get_provenance()

        # Check that custom names are used in provenance
        for field, sources in provenance.items():
            for source in sources:
                self.assertIn(source, source_names)

    def test_get_provenance(self):
        """Test getting provenance information."""
        parsers = [self.primary_parser, self.secondary1_parser]
        self.merger.merge_rocrates(parsers)

        provenance = self.merger.get_provenance()

        self.assertIsInstance(provenance, dict)
        self.assertGreater(len(provenance), 0)

        # Check that each field has source list
        for field, sources in provenance.items():
            self.assertIsInstance(sources, list)
            self.assertGreater(len(sources), 0)

    def test_get_provenance_returns_copy(self):
        """Test that get_provenance returns a copy."""
        parsers = [self.primary_parser, self.secondary1_parser]
        self.merger.merge_rocrates(parsers)

        prov1 = self.merger.get_provenance()
        prov2 = self.merger.get_provenance()

        # Should be equal but not the same object
        self.assertEqual(prov1, prov2)
        self.assertIsNot(prov1, prov2)

    def test_get_merge_stats(self):
        """Test getting merge statistics."""
        parsers = [self.primary_parser, self.secondary1_parser, self.secondary2_parser]
        self.merger.merge_rocrates(parsers)

        stats = self.merger.get_merge_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn('total_sources', stats)
        self.assertIn('total_unique_fields', stats)
        self.assertIn('fields_from_primary', stats)
        self.assertIn('fields_from_secondary', stats)
        self.assertIn('fields_combined', stats)
        self.assertIn('fields_merged_as_arrays', stats)

        # Verify counts
        self.assertEqual(stats['total_sources'], 3)
        self.assertGreater(stats['total_unique_fields'], 0)

    def test_get_merge_stats_returns_copy(self):
        """Test that get_merge_stats returns a copy."""
        parsers = [self.primary_parser, self.secondary1_parser]
        self.merger.merge_rocrates(parsers)

        stats1 = self.merger.get_merge_stats()
        stats2 = self.merger.get_merge_stats()

        # Should be equal but not the same object
        self.assertEqual(stats1, stats2)
        self.assertIsNot(stats1, stats2)

    def test_get_merged_dataset(self):
        """Test getting merged dataset."""
        parsers = [self.primary_parser, self.secondary1_parser]
        self.merger.merge_rocrates(parsers)

        dataset = self.merger.get_merged_dataset()

        self.assertIsInstance(dataset, dict)
        self.assertGreater(len(dataset), 0)

    def test_get_merged_dataset_returns_copy(self):
        """Test that get_merged_dataset returns a copy."""
        parsers = [self.primary_parser, self.secondary1_parser]
        self.merger.merge_rocrates(parsers)

        dataset1 = self.merger.get_merged_dataset()
        dataset2 = self.merger.get_merged_dataset()

        # Should be equal but not the same object
        self.assertEqual(dataset1, dataset2)
        self.assertIsNot(dataset1, dataset2)

    def test_generate_merge_report(self):
        """Test generating merge report."""
        parsers = [self.primary_parser, self.secondary1_parser, self.secondary2_parser]
        self.merger.merge_rocrates(parsers)

        report = self.merger.generate_merge_report(parsers)

        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)

        # Check report contains expected sections
        self.assertIn("Multi-RO-Crate Merge Report", report)
        self.assertIn("SOURCES PROCESSED", report)
        self.assertIn("MERGE STATISTICS", report)
        self.assertIn("FIELD CONTRIBUTIONS BY CATEGORY", report)

    def test_generate_merge_report_with_custom_names(self):
        """Test generating merge report with custom source names."""
        parsers = [self.primary_parser, self.secondary1_parser]
        source_names = ['Custom Primary', 'Custom Secondary']
        self.merger.merge_rocrates(parsers, source_names=source_names)

        report = self.merger.generate_merge_report(parsers, source_names)

        # Check custom names appear in report
        self.assertIn('Custom Primary', report)
        self.assertIn('Custom Secondary', report)

    def test_save_merge_report(self):
        """Test saving merge report to file."""
        parsers = [self.primary_parser, self.secondary1_parser]
        self.merger.merge_rocrates(parsers)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "merge_output.yaml"
            self.merger.save_merge_report(output_path, parsers)

            # Check report file was created
            report_path = Path(tmpdir) / "merge_output_merge_report.txt"
            self.assertTrue(report_path.exists())

            # Check report content
            with open(report_path, 'r') as f:
                content = f.read()
                self.assertGreater(len(content), 0)
                self.assertIn("Multi-RO-Crate Merge Report", content)

    def test_merge_field_provenance_tracking(self):
        """Test that merge_field tracks provenance correctly."""
        parsers = [self.primary_parser, self.secondary1_parser]
        source_names = ['primary_source', 'secondary_source']
        self.merger.merge_rocrates(parsers, source_names=source_names)

        provenance = self.merger.get_provenance()

        # Title should come from primary
        self.assertIn('title', provenance)
        self.assertIn('primary_source', provenance['title'])

        # License should come from secondary
        self.assertIn('license', provenance)
        self.assertIn('secondary_source', provenance['license'])


if __name__ == '__main__':
    unittest.main()
