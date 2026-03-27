#!/usr/bin/env python3
"""
Tests for legacy file property migration.

Tests that D4D files with file properties at Dataset level are automatically
migrated to use FileCollection.
"""

import unittest
from pathlib import Path
from src.validation.unified_validator import UnifiedValidator


class TestLegacyMigration(unittest.TestCase):
    """Test legacy file property migration."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = UnifiedValidator()

    def test_migrate_legacy_file_properties(self):
        """Test migration of file properties to FileCollection."""
        # Legacy data with file properties at Dataset level
        legacy_data = {
            'id': 'test-dataset',
            'name': 'Test Dataset',
            'bytes': 1048576,
            'path': '/data/test.csv',
            'format': 'CSV',
            'encoding': 'UTF-8',
            'compression': 'gzip',
            'md5': 'abc123',
            'sha256': 'def456'
        }

        # Apply migration
        migrated_data, warnings = self.validator.migrate_legacy_file_properties(legacy_data)

        # Check migration happened
        self.assertEqual(len(warnings), 1)
        self.assertIn('DEPRECATION', warnings[0])
        self.assertIn('file_collections', warnings[0])

        # Check file properties moved to file_collections
        self.assertIn('file_collections', migrated_data)
        self.assertEqual(len(migrated_data['file_collections']), 1)

        file_collection = migrated_data['file_collections'][0]
        self.assertEqual(file_collection['bytes'], 1048576)
        self.assertEqual(file_collection['path'], '/data/test.csv')
        self.assertEqual(file_collection['format'], 'CSV')
        self.assertEqual(file_collection['encoding'], 'UTF-8')
        self.assertEqual(file_collection['compression'], 'gzip')
        self.assertEqual(file_collection['md5'], 'abc123')
        self.assertEqual(file_collection['sha256'], 'def456')

        # Check file properties removed from dataset level
        self.assertNotIn('bytes', migrated_data)
        self.assertNotIn('path', migrated_data)
        self.assertNotIn('format', migrated_data)
        self.assertNotIn('encoding', migrated_data)
        self.assertNotIn('compression', migrated_data)
        self.assertNotIn('md5', migrated_data)
        self.assertNotIn('sha256', migrated_data)

        # Check dataset-level properties preserved
        self.assertEqual(migrated_data['id'], 'test-dataset')
        self.assertEqual(migrated_data['name'], 'Test Dataset')

    def test_no_migration_when_file_collections_present(self):
        """Test that migration doesn't happen if file_collections already exists."""
        data_with_collections = {
            'id': 'test-dataset',
            'name': 'Test Dataset',
            'bytes': 1048576,  # File property present
            'file_collections': [  # But file_collections also present
                {
                    'id': 'collection-1',
                    'name': 'Data Files',
                    'format': 'JSON'
                }
            ]
        }

        migrated_data, warnings = self.validator.migrate_legacy_file_properties(data_with_collections)

        # No migration should happen
        self.assertEqual(len(warnings), 0)
        self.assertEqual(migrated_data, data_with_collections)

    def test_no_migration_when_no_file_properties(self):
        """Test that migration doesn't happen if no file properties present."""
        clean_data = {
            'id': 'test-dataset',
            'name': 'Test Dataset',
            'description': 'A clean dataset without legacy file properties'
        }

        migrated_data, warnings = self.validator.migrate_legacy_file_properties(clean_data)

        # No migration should happen
        self.assertEqual(len(warnings), 0)
        self.assertEqual(migrated_data, clean_data)

    def test_migration_preserves_collection_metadata(self):
        """Test that migrated FileCollection has correct metadata."""
        legacy_data = {
            'id': 'test-dataset',
            'bytes': 2048,
            'format': 'CSV'
        }

        migrated_data, warnings = self.validator.migrate_legacy_file_properties(legacy_data)

        # Check FileCollection metadata
        file_collection = migrated_data['file_collections'][0]
        self.assertEqual(file_collection['id'], 'test-dataset-files')
        self.assertEqual(file_collection['name'], 'Dataset Files')
        self.assertIn('Migrated from legacy', file_collection['description'])

    def test_migration_handles_partial_file_properties(self):
        """Test migration with only some file properties present."""
        partial_data = {
            'id': 'test-dataset',
            'bytes': 4096,
            'format': 'JSON'
            # No md5, sha256, compression, etc.
        }

        migrated_data, warnings = self.validator.migrate_legacy_file_properties(partial_data)

        # Migration should still happen
        self.assertEqual(len(warnings), 1)
        file_collection = migrated_data['file_collections'][0]
        self.assertEqual(file_collection['bytes'], 4096)
        self.assertEqual(file_collection['format'], 'JSON')
        # Properties not present should not be in collection
        self.assertNotIn('md5', file_collection)
        self.assertNotIn('sha256', file_collection)


if __name__ == '__main__':
    unittest.main()
