#!/usr/bin/env python3
"""
Tests for FieldPrioritizer utility.

Tests field merge strategy selection and conflict resolution when
combining multiple RO-Crate sources.
"""

import unittest
import sys
from pathlib import Path

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.fairscape_integration.utils.field_prioritizer import FieldPrioritizer
from src.fairscape_integration.constants import MergeStrategy


class TestFieldPrioritizer(unittest.TestCase):
    """Test FieldPrioritizer merge strategy selection and conflict resolution."""

    def setUp(self):
        """Set up test fixtures."""
        self.prioritizer = FieldPrioritizer()

    def test_policy_fields_use_primary_wins(self):
        """Test that policy fields use PRIMARY_WINS strategy."""
        policy_fields = [
            'prohibited_uses',
            'license_and_use_terms',
            'ethical_reviews',
            'informed_consent',
        ]

        for field in policy_fields:
            strategy = self.prioritizer.get_merge_strategy(field)
            self.assertEqual(
                strategy,
                MergeStrategy.PRIMARY_WINS,
                f"{field} should use PRIMARY_WINS strategy"
            )

    def test_technical_fields_use_secondary_wins(self):
        """Test that technical fields use SECONDARY_WINS strategy."""
        technical_fields = [
            'download_url',
            'hash',
            'md5',
            'sha256',
            'compression',
        ]

        for field in technical_fields:
            strategy = self.prioritizer.get_merge_strategy(field)
            self.assertEqual(
                strategy,
                MergeStrategy.SECONDARY_WINS,
                f"{field} should use SECONDARY_WINS strategy"
            )

    def test_array_fields_use_union(self):
        """Test that array fields use UNION strategy."""
        array_fields = [
            'keywords',
            'creators',
            'funders',
            'tasks',
        ]

        for field in array_fields:
            strategy = self.prioritizer.get_merge_strategy(field)
            self.assertEqual(
                strategy,
                MergeStrategy.UNION,
                f"{field} should use UNION strategy"
            )

    def test_descriptive_fields_use_combine(self):
        """Test that descriptive fields use COMBINE strategy."""
        descriptive_fields = [
            'description',
            'purposes',
            'known_limitations',
            'content_warnings',
        ]

        for field in descriptive_fields:
            strategy = self.prioritizer.get_merge_strategy(field)
            self.assertEqual(
                strategy,
                MergeStrategy.COMBINE,
                f"{field} should use COMBINE strategy"
            )

    def test_aggregate_fields_use_aggregate(self):
        """Test that aggregate fields use AGGREGATE strategy."""
        aggregate_fields = [
            'bytes',
            'total_bytes',
            'file_count',
        ]

        for field in aggregate_fields:
            strategy = self.prioritizer.get_merge_strategy(field)
            self.assertEqual(
                strategy,
                MergeStrategy.AGGREGATE,
                f"{field} should use AGGREGATE strategy"
            )

    def test_unknown_fields_default_to_primary_wins(self):
        """Test that unknown fields default to PRIMARY_WINS."""
        unknown_fields = [
            'some_random_field',
            'another_unknown',
        ]

        for field in unknown_fields:
            strategy = self.prioritizer.get_merge_strategy(field)
            self.assertEqual(
                strategy,
                MergeStrategy.PRIMARY_WINS,
                f"{field} should default to PRIMARY_WINS"
            )

    def test_resolve_union_strategy(self):
        """Test conflict resolution for UNION strategy (keywords)."""
        primary = ['AI', 'READI', 'diabetes']
        secondary = [
            (['iPSC', 'stem cells', 'AI'], 'mass-spec-iPSCs'),
            (['cancer', 'proteomics', 'READI'], 'mass-spec-cancer')
        ]

        merged, sources = self.prioritizer.resolve_conflict(
            'keywords', primary, secondary
        )

        # Check all unique keywords are present
        self.assertIn('AI', merged)
        self.assertIn('READI', merged)
        self.assertIn('diabetes', merged)
        self.assertIn('iPSC', merged)
        self.assertIn('stem cells', merged)
        self.assertIn('cancer', merged)
        self.assertIn('proteomics', merged)

        # Check deduplication (AI and READI appear only once)
        self.assertEqual(merged.count('AI'), 1)
        self.assertEqual(merged.count('READI'), 1)

        # Check sources tracked
        self.assertIn('primary', sources)
        self.assertIn('mass-spec-iPSCs', sources)
        self.assertIn('mass-spec-cancer', sources)

    def test_resolve_combine_strategy(self):
        """Test conflict resolution for COMBINE strategy (description)."""
        primary_desc = "CM4AI release dataset for mass spectrometry"
        secondary_desc = [
            ('iPSC proteomics data', 'mass-spec-iPSCs'),
            ('Cancer cell proteomics data', 'mass-spec-cancer')
        ]

        merged_desc, sources = self.prioritizer.resolve_conflict(
            'description', primary_desc, secondary_desc
        )

        # Check all descriptions are combined with headers
        self.assertIn('## Overview', merged_desc)
        self.assertIn('CM4AI release dataset', merged_desc)
        self.assertIn('## Mass Spec Ipscs', merged_desc)
        self.assertIn('iPSC proteomics data', merged_desc)
        self.assertIn('## Mass Spec Cancer', merged_desc)
        self.assertIn('Cancer cell proteomics data', merged_desc)

        # Check sources tracked
        self.assertEqual(len(sources), 3)
        self.assertIn('primary', sources)

    def test_resolve_primary_wins_strategy(self):
        """Test conflict resolution for PRIMARY_WINS strategy."""
        primary = "CC-BY-4.0"
        secondary = [
            ('MIT', 'sub-crate-1'),
            ('Apache-2.0', 'sub-crate-2')
        ]

        merged, sources = self.prioritizer.resolve_conflict(
            'license', primary, secondary
        )

        # Primary should win
        self.assertEqual(merged, "CC-BY-4.0")
        self.assertEqual(sources, ["primary"])

    def test_resolve_secondary_wins_strategy(self):
        """Test conflict resolution for SECONDARY_WINS strategy."""
        primary = "https://old-url.org/download"
        secondary = [
            ('https://new-url.org/download', 'sub-crate-1'),
            ('https://another-url.org/download', 'sub-crate-2')
        ]

        merged, sources = self.prioritizer.resolve_conflict(
            'download_url', primary, secondary
        )

        # First secondary should win
        self.assertEqual(merged, "https://new-url.org/download")
        self.assertEqual(sources, ["sub-crate-1"])

    def test_resolve_aggregate_strategy(self):
        """Test conflict resolution for AGGREGATE strategy."""
        primary = 1073741824  # 1 GB
        secondary = [
            (524288000, 'sub-crate-1'),
            (524288000, 'sub-crate-2')
        ]

        merged, sources = self.prioritizer.resolve_conflict(
            'bytes', primary, secondary
        )

        # Primary aggregate should be used (not sum of secondaries)
        self.assertEqual(merged, 1073741824)
        self.assertEqual(sources, ["primary"])

    def test_get_field_category(self):
        """Test field category classification."""
        test_cases = [
            ('prohibited_uses', 'Policy/Governance'),
            ('download_url', 'Technical/Access'),
            ('keywords', 'Array/Collection'),
            ('description', 'Descriptive'),
            ('bytes', 'Aggregate Statistics'),
            ('unknown_field', 'General'),
        ]

        for field, expected_category in test_cases:
            category = self.prioritizer.get_field_category(field)
            self.assertEqual(
                category,
                expected_category,
                f"{field} should be categorized as {expected_category}"
            )

    def test_resolve_conflict_with_none_primary(self):
        """Test conflict resolution when primary value is None."""
        primary = None
        secondary = [
            ('Secondary value', 'sub-crate-1'),
        ]

        merged, sources = self.prioritizer.resolve_conflict(
            'title', primary, secondary
        )

        # Should fallback to secondary
        self.assertEqual(merged, 'Secondary value')
        self.assertIn('sub-crate-1', sources)

    def test_resolve_conflict_with_all_none(self):
        """Test conflict resolution when all values are None."""
        primary = None
        secondary = [
            (None, 'sub-crate-1'),
            (None, 'sub-crate-2'),
        ]

        merged, sources = self.prioritizer.resolve_conflict(
            'title', primary, secondary
        )

        # Should return None
        self.assertIsNone(merged)
        self.assertEqual(sources, [])


if __name__ == '__main__':
    unittest.main()
