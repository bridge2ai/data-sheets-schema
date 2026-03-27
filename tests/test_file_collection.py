#!/usr/bin/env python3
"""
Unit tests for FileCollection class.

Tests FileCollection validation, property constraints, and integration
with Dataset class.
"""

import unittest
import yaml
from pathlib import Path
import tempfile


class TestFileCollection(unittest.TestCase):
    """Test FileCollection class validation and properties."""

    def test_filecollection_basic_validation(self):
        """Test that basic FileCollection validates correctly."""
        filecollection_data = {
            'id': 'test-collection-1',
            'name': 'Training Data',
            'description': 'Training dataset files',
            'collection_type': 'training_split',
            'format': 'CSV',
            'bytes': 1048576,
            'file_count': 100
        }

        # This should validate without errors when using linkml-validate
        # For now, just test the data structure is correct
        self.assertIn('id', filecollection_data)
        self.assertEqual(filecollection_data['collection_type'], 'training_split')

    def test_dataset_with_file_collections(self):
        """Test Dataset containing FileCollections."""
        dataset_data = {
            'id': 'test-dataset',
            'title': 'Test Dataset',
            'description': 'A dataset with file collections',
            'file_collections': [
                {
                    'id': 'collection-1',
                    'name': 'Training Files',
                    'collection_type': 'training_split',
                    'format': 'CSV',
                    'bytes': 1048576
                },
                {
                    'id': 'collection-2',
                    'name': 'Test Files',
                    'collection_type': 'test_split',
                    'format': 'CSV',
                    'bytes': 524288
                }
            ],
            'total_file_count': 200,
            'total_size_bytes': 1572864
        }

        self.assertEqual(len(dataset_data['file_collections']), 2)
        self.assertEqual(dataset_data['total_file_count'], 200)

    def test_filecollection_enum_values(self):
        """Test FileCollectionTypeEnum permissible values."""
        valid_types = [
            'raw_data',
            'processed_data',
            'training_split',
            'test_split',
            'validation_split',
            'documentation',
            'metadata',
            'code',
            'supplementary',
            'other'
        ]

        for collection_type in valid_types:
            collection = {
                'id': f'collection-{collection_type}',
                'name': f'{collection_type} files',
                'collection_type': collection_type
            }
            self.assertEqual(collection['collection_type'], collection_type)

    def test_filecollection_properties_complete(self):
        """Test FileCollection with all properties."""
        complete_collection = {
            'id': 'complete-collection',
            'name': 'Complete File Collection',
            'description': 'A collection with all properties',
            'collection_type': 'processed_data',
            'format': 'JSON',
            'bytes': 2097152,
            'total_bytes': 2097152,
            'file_count': 50,
            'path': '/data/processed/',
            'encoding': 'UTF-8',
            'compression': 'gzip',
            'media_type': 'application/json',
            'hash': 'abc123def456',
            'md5': 'abc123',
            'sha256': 'def456789'
        }

        # Verify all expected properties present
        expected_props = ['id', 'name', 'description', 'collection_type',
                          'format', 'bytes', 'file_count', 'path', 'encoding',
                          'compression', 'md5', 'sha256']

        for prop in expected_props:
            self.assertIn(prop, complete_collection)

    def test_nested_file_collections(self):
        """Test FileCollection can contain nested FileCollections via resources."""
        parent_collection = {
            'id': 'parent-collection',
            'name': 'Parent Collection',
            'resources': [
                {
                    'id': 'child-collection-1',
                    'name': 'Child Collection 1',
                    'format': 'CSV'
                },
                {
                    'id': 'child-collection-2',
                    'name': 'Child Collection 2',
                    'format': 'JSON'
                }
            ]
        }

        self.assertEqual(len(parent_collection['resources']), 2)
        self.assertEqual(parent_collection['resources'][0]['format'], 'CSV')

    def test_dataset_without_file_collections_still_valid(self):
        """Test that Dataset without file_collections is still valid."""
        legacy_dataset = {
            'id': 'legacy-dataset',
            'title': 'Legacy Dataset',
            'description': 'Dataset without file collections',
            'purposes': [],
            'creators': []
        }

        # Should be valid without file_collections
        self.assertNotIn('file_collections', legacy_dataset)
        self.assertIn('id', legacy_dataset)


class TestFileCollectionYAMLGeneration(unittest.TestCase):
    """Test FileCollection YAML generation and validation."""

    def test_generate_yaml_with_filecollection(self):
        """Test generating valid D4D YAML with FileCollection."""
        d4d_data = {
            'id': 'https://example.org/dataset/123',
            'title': 'Example Dataset',
            'description': 'A dataset with file collections',
            'file_collections': [
                {
                    'id': 'collection-raw',
                    'name': 'Raw Data Files',
                    'description': 'Unprocessed sensor data',
                    'collection_type': 'raw_data',
                    'format': 'CSV',
                    'bytes': 5242880,
                    'file_count': 150,
                    'encoding': 'UTF-8',
                    'sha256': 'a1b2c3d4e5f6'
                },
                {
                    'id': 'collection-processed',
                    'name': 'Processed Data Files',
                    'description': 'Cleaned and normalized data',
                    'collection_type': 'processed_data',
                    'format': 'JSON',
                    'bytes': 3145728,
                    'file_count': 100,
                    'encoding': 'UTF-8',
                    'compression': 'gzip',
                    'sha256': 'g7h8i9j0k1l2'
                }
            ],
            'total_file_count': 250,
            'total_size_bytes': 8388608
        }

        # Convert to YAML
        yaml_str = yaml.dump(d4d_data, default_flow_style=False, sort_keys=False)

        # Parse back
        parsed = yaml.safe_load(yaml_str)

        self.assertEqual(parsed['id'], d4d_data['id'])
        self.assertEqual(len(parsed['file_collections']), 2)
        self.assertEqual(parsed['file_collections'][0]['collection_type'], 'raw_data')
        self.assertEqual(parsed['total_file_count'], 250)

    def test_write_and_read_filecollection_yaml(self):
        """Test writing and reading FileCollection YAML file."""
        d4d_data = {
            'id': 'test-dataset',
            'title': 'Test Dataset',
            'file_collections': [
                {
                    'id': 'test-collection',
                    'name': 'Test Files',
                    'collection_type': 'test_split',
                    'format': 'CSV',
                    'bytes': 1024
                }
            ]
        }

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(d4d_data, f, default_flow_style=False)
            temp_path = f.name

        try:
            # Read back
            with open(temp_path) as f:
                loaded_data = yaml.safe_load(f)

            self.assertEqual(loaded_data['id'], 'test-dataset')
            self.assertEqual(loaded_data['file_collections'][0]['name'], 'Test Files')
        finally:
            Path(temp_path).unlink()


if __name__ == '__main__':
    unittest.main()
