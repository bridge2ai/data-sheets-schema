#!/usr/bin/env python3
"""
Tests for InformativenessScorer utility.

Tests RO-Crate informativeness scoring and ranking.
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

from src.fairscape_integration.utils.informativeness_scorer import InformativenessScorer
from src.fairscape_integration.utils.rocrate_parser import ROCrateParser
from src.fairscape_integration.utils.mapping_loader import MappingLoader


class TestInformativenessScorer(unittest.TestCase):
    """Test InformativenessScorer scoring and ranking."""

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

        # Create comprehensive RO-Crate with high informativeness
        self.comprehensive_rocrate = {
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
                    "name": "Comprehensive Dataset",
                    "description": "A very detailed description that exceeds 200 characters to test the rich description scoring. " * 5,
                    "keywords": ["comprehensive", "test"],
                    "version": "1.0",
                    "license": "MIT",
                    "author": [{"@id": "#person1"}],
                    "contentUrl": "https://example.com/download",
                    "md5": "abc123",
                    "encodingFormat": "application/json",
                    "contentSize": "1024000",
                    "additionalProperty": [
                        {"@type": "PropertyValue", "name": "key1", "value": "value1"}
                    ],
                    "workflow": {"@id": "#workflow1"}
                },
                {
                    "@id": "#person1",
                    "@type": "Person",
                    "name": "Test Author"
                },
                {
                    "@id": "#workflow1",
                    "@type": "ComputationalWorkflow",
                    "name": "Processing Workflow"
                }
            ]
        }

        # Create minimal RO-Crate with low informativeness
        self.minimal_rocrate = {
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
                    "name": "Minimal Dataset",
                    "description": "Short"
                }
            ]
        }

        # Create medium RO-Crate
        self.medium_rocrate = {
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
                    "name": "Medium Dataset",
                    "description": "Medium description",
                    "keywords": ["medium"],
                    "version": "2.0",
                    "license": "Apache-2.0"
                }
            ]
        }

        # Write RO-Crate files
        self.comp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.comprehensive_rocrate, self.comp_file)
        self.comp_file.close()

        self.min_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.minimal_rocrate, self.min_file)
        self.min_file.close()

        self.med_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.medium_rocrate, self.med_file)
        self.med_file.close()

        self.comp_parser = ROCrateParser(self.comp_file.name, verbose=False)
        self.min_parser = ROCrateParser(self.min_file.name, verbose=False)
        self.med_parser = ROCrateParser(self.med_file.name, verbose=False)

        self.scorer = InformativenessScorer(verbose=False)

    def tearDown(self):
        """Clean up temporary files."""
        Path(self.temp_tsv.name).unlink()
        Path(self.comp_file.name).unlink()
        Path(self.min_file.name).unlink()
        Path(self.med_file.name).unlink()

    def test_scorer_initialization(self):
        """Test scorer initializes correctly."""
        self.assertIsNotNone(self.scorer.weights)
        self.assertEqual(self.scorer.weights['d4d_coverage'], 0.4)
        self.assertEqual(self.scorer.weights['unique_fields'], 0.3)
        self.assertEqual(self.scorer.weights['metadata_richness'], 0.2)
        self.assertEqual(self.scorer.weights['technical_completeness'], 0.1)
        self.assertFalse(self.scorer.verbose)

    def test_scorer_with_verbose(self):
        """Test scorer with verbose output."""
        verbose_scorer = InformativenessScorer(verbose=True)
        self.assertTrue(verbose_scorer.verbose)

    def test_score_comprehensive_rocrate(self):
        """Test scoring comprehensive RO-Crate."""
        scores = self.scorer.score_rocrate(
            self.comp_parser,
            self.mapping_loader
        )

        self.assertIn('d4d_coverage', scores)
        self.assertIn('unique_fields', scores)
        self.assertIn('metadata_richness', scores)
        self.assertIn('technical_completeness', scores)
        self.assertIn('total_score', scores)

        # Comprehensive should have good coverage
        self.assertGreater(scores['d4d_coverage'], 3)

        # Richness should be high (has additionalProperty, Person, workflow, rich description)
        self.assertEqual(scores['metadata_richness'], 1.0)

        # Technical completeness should be high (has URL, checksum, format, size)
        self.assertEqual(scores['technical_completeness'], 1.0)

        # Total score should be positive
        self.assertGreater(scores['total_score'], 0.5)

    def test_score_minimal_rocrate(self):
        """Test scoring minimal RO-Crate."""
        scores = self.scorer.score_rocrate(
            self.min_parser,
            self.mapping_loader
        )

        # Minimal should have low coverage
        self.assertEqual(scores['d4d_coverage'], 2)  # Only name and description

        # Richness should be low
        self.assertEqual(scores['metadata_richness'], 0.0)

        # Technical completeness should be low
        self.assertEqual(scores['technical_completeness'], 0.0)

        # Total score should be lower than comprehensive
        # (Coverage: 2/5 = 0.4 → 0.4*0.4 = 0.16, Unique: 2/2 = 1.0 → 1.0*0.3 = 0.3, Total ≈ 0.46)
        self.assertLess(scores['total_score'], 0.5)

    def test_unique_field_counting(self):
        """Test unique field counting with multiple parsers."""
        # Score comprehensive against minimal (comprehensive has unique fields)
        scores = self.scorer.score_rocrate(
            self.comp_parser,
            self.mapping_loader,
            other_parsers=[self.min_parser]
        )

        # Unique fields should be less than total coverage
        self.assertLessEqual(scores['unique_fields'], scores['d4d_coverage'])
        self.assertGreater(scores['unique_fields'], 0)

    def test_rank_rocrates(self):
        """Test ranking multiple RO-Crate parsers."""
        parsers = [self.comp_parser, self.min_parser, self.med_parser]
        ranked = self.scorer.rank_rocrates(parsers, self.mapping_loader)

        # Should return list of tuples (parser, scores, rank)
        self.assertEqual(len(ranked), 3)

        # Check structure
        for parser, scores, rank in ranked:
            self.assertIsNotNone(parser)
            self.assertIn('total_score', scores)
            self.assertIsInstance(rank, int)
            self.assertGreaterEqual(rank, 1)
            self.assertLessEqual(rank, 3)

        # Ranks should be unique and ordered
        ranks = [rank for _, _, rank in ranked]
        self.assertEqual(sorted(ranks), [1, 2, 3])

        # Comprehensive should rank highest
        top_parser, top_scores, top_rank = ranked[0]
        self.assertEqual(top_rank, 1)
        self.assertEqual(top_parser, self.comp_parser)

        # Minimal should rank lowest
        bottom_parser, bottom_scores, bottom_rank = ranked[-1]
        self.assertEqual(bottom_rank, 3)
        self.assertEqual(bottom_parser, self.min_parser)

    def test_rank_single_rocrate(self):
        """Test ranking with single RO-Crate."""
        ranked = self.scorer.rank_rocrates([self.comp_parser], self.mapping_loader)

        self.assertEqual(len(ranked), 1)
        parser, scores, rank = ranked[0]
        self.assertEqual(rank, 1)
        self.assertEqual(parser, self.comp_parser)

    def test_metadata_richness_scoring(self):
        """Test metadata richness calculation."""
        # Comprehensive has all richness indicators
        comp_richness = self.scorer._calculate_metadata_richness(self.comp_parser)
        self.assertEqual(comp_richness, 1.0)

        # Minimal has none
        min_richness = self.scorer._calculate_metadata_richness(self.min_parser)
        self.assertEqual(min_richness, 0.0)

    def test_technical_completeness_scoring(self):
        """Test technical completeness calculation."""
        # Comprehensive has all technical indicators
        comp_completeness = self.scorer._calculate_technical_completeness(self.comp_parser)
        self.assertEqual(comp_completeness, 1.0)

        # Minimal has none
        min_completeness = self.scorer._calculate_technical_completeness(self.min_parser)
        self.assertEqual(min_completeness, 0.0)

    def test_score_with_no_other_parsers(self):
        """Test scoring without other parsers for comparison."""
        scores = self.scorer.score_rocrate(
            self.comp_parser,
            self.mapping_loader,
            other_parsers=None
        )

        # Unique fields should equal coverage when no comparison
        self.assertEqual(scores['unique_fields'], scores['d4d_coverage'])

    def test_score_with_empty_other_parsers(self):
        """Test scoring with empty other_parsers list."""
        scores = self.scorer.score_rocrate(
            self.comp_parser,
            self.mapping_loader,
            other_parsers=[]
        )

        # Unique fields should equal coverage
        self.assertEqual(scores['unique_fields'], scores['d4d_coverage'])

    def test_print_ranking_report(self):
        """Test printing ranking report (no errors)."""
        ranked = self.scorer.rank_rocrates(
            [self.comp_parser, self.min_parser],
            self.mapping_loader
        )

        # Should not raise exception
        try:
            self.scorer.print_ranking_report(ranked)
        except Exception as e:
            self.fail(f"print_ranking_report raised {e}")

    def test_scores_are_normalized(self):
        """Test that all score components are between 0 and 1."""
        scores = self.scorer.score_rocrate(
            self.comp_parser,
            self.mapping_loader
        )

        self.assertGreaterEqual(scores['metadata_richness'], 0.0)
        self.assertLessEqual(scores['metadata_richness'], 1.0)

        self.assertGreaterEqual(scores['technical_completeness'], 0.0)
        self.assertLessEqual(scores['technical_completeness'], 1.0)

        self.assertGreaterEqual(scores['total_score'], 0.0)
        self.assertLessEqual(scores['total_score'], 1.0)

    def test_total_score_weighted_combination(self):
        """Test that total score uses correct weights."""
        scores = self.scorer.score_rocrate(
            self.comp_parser,
            self.mapping_loader
        )

        covered_fields = self.mapping_loader.get_covered_fields()
        coverage_normalized = scores['d4d_coverage'] / max(len(covered_fields), 1)
        unique_normalized = scores['unique_fields'] / max(scores['d4d_coverage'], 1)

        expected_total = (
            coverage_normalized * 0.4 +
            unique_normalized * 0.3 +
            scores['metadata_richness'] * 0.2 +
            scores['technical_completeness'] * 0.1
        )

        self.assertAlmostEqual(scores['total_score'], expected_total, places=5)


if __name__ == '__main__':
    unittest.main()
