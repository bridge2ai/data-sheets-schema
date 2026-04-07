#!/usr/bin/env python3
"""
Tests for legacy file property migration.

Tests that D4D files with file properties at Dataset level are automatically
migrated to use FileCollection.
"""

import unittest
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

        # Collection-level properties
        self.assertEqual(file_collection['total_bytes'], 1048576)  # bytes → total_bytes
        self.assertEqual(file_collection['path'], '/data/test.csv')
        self.assertEqual(file_collection['compression'], 'gzip')
        self.assertEqual(file_collection['file_count'], 1)

        # File-level properties should be in resources
        self.assertIn('resources', file_collection)
        self.assertEqual(len(file_collection['resources']), 1)

        file_obj = file_collection['resources'][0]
        self.assertEqual(file_obj['bytes'], 1048576)
        self.assertEqual(file_obj['format'], 'CSV')
        self.assertEqual(file_obj['encoding'], 'UTF-8')
        self.assertEqual(file_obj['md5'], 'abc123')
        self.assertEqual(file_obj['sha256'], 'def456')
        self.assertEqual(file_obj['file_type'], 'data_file')

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

        # Collection should have total_bytes
        self.assertEqual(file_collection['total_bytes'], 4096)
        self.assertEqual(file_collection['file_count'], 1)

        # File-level properties should be in resources
        self.assertIn('resources', file_collection)
        file_obj = file_collection['resources'][0]
        self.assertEqual(file_obj['bytes'], 4096)
        self.assertEqual(file_obj['format'], 'JSON')

        # Properties not present should not be in File object
        self.assertNotIn('md5', file_obj)
        self.assertNotIn('sha256', file_obj)


if __name__ == '__main__':
    unittest.main()
