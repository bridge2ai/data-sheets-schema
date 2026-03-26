#!/usr/bin/env python3
"""
Unit tests for schema_stats.py

Tests schema statistics generation functionality.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    # Import from .claude/agents/scripts/
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "scripts"))
    from schema_stats import (
        load_schema,
        get_high_level_stats,
        get_module_from_prefix,
        generate_stats
    )
    from data_sheets_schema.constants import MODULE_MAP
except ImportError as e:
    print(f"Warning: Could not import schema_stats: {e}", file=sys.stderr)
    # Define dummy functions to allow tests to be discovered but skipped
    load_schema = None
    get_high_level_stats = None
    get_module_from_prefix = None
    generate_stats = None


class TestSchemaStats(unittest.TestCase):
    """Test schema statistics generation."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures - load schema once for all tests."""
        if load_schema is None:
            cls.skipTest(cls, "schema_stats module not available")

        try:
            cls.schema_view = load_schema()
        except Exception as e:
            cls.skipTest(cls, f"Could not load schema: {e}")

    def test_load_schema(self):
        """Test schema loading."""
        self.assertIsNotNone(self.schema_view)
        self.assertTrue(hasattr(self.schema_view, 'all_classes'))

    def test_high_level_stats(self):
        """Test high-level statistics generation."""
        stats = get_high_level_stats(self.schema_view)

        # Check required keys
        self.assertIn('total_classes', stats)
        self.assertIn('total_slots', stats)
        self.assertIn('total_enums', stats)

        # Check values are reasonable
        self.assertGreater(stats['total_classes'], 0)
        self.assertGreater(stats['total_slots'], 0)

    def test_module_from_prefix(self):
        """Test module name mapping from prefix."""
        # Test known prefixes
        self.assertEqual(get_module_from_prefix('d4dmotivation'), 'D4D_Motivation')
        self.assertEqual(get_module_from_prefix('d4dcomposition'), 'D4D_Composition')
        self.assertEqual(get_module_from_prefix('linkml'), 'LinkML_Core')

        # Test unknown prefix
        self.assertEqual(get_module_from_prefix('unknown'), 'Unknown')

    def test_module_map_consistency(self):
        """Test that MODULE_MAP from constants matches schema_stats usage."""
        # Verify MODULE_MAP has expected keys
        expected_prefixes = [
            'd4dmotivation', 'd4dcomposition', 'd4dcollection',
            'd4dpreprocessing', 'd4duses', 'd4ddistribution'
        ]

        for prefix in expected_prefixes:
            self.assertIn(prefix, MODULE_MAP)

    def test_generate_stats_level1(self):
        """Test stats generation at level 1 (summary)."""
        stats = generate_stats(self.schema_view, level=1)

        self.assertIn('summary', stats)
        self.assertIn('total_classes', stats['summary'])

    def test_generate_stats_level2(self):
        """Test stats generation at level 2 (breakdown)."""
        stats = generate_stats(self.schema_view, level=2)

        self.assertIn('summary', stats)
        self.assertIn('classes', stats)
        self.assertIn('by_module', stats['classes'])

    def test_schema_has_d4d_classes(self):
        """Test that schema contains D4D classes."""
        all_classes = list(self.schema_view.all_classes())

        # Should have Dataset class
        self.assertIn('Dataset', all_classes)

        # Should have multiple classes (at least 50 for D4D schema)
        self.assertGreater(len(all_classes), 50, "Schema should contain many classes")

    def test_schema_has_enums(self):
        """Test that schema contains enumerations."""
        all_enums = list(self.schema_view.all_enums())
        self.assertGreater(len(all_enums), 0, "Schema should contain enumerations")


if __name__ == '__main__':
    unittest.main()
