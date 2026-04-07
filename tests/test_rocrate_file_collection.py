#!/usr/bin/env python3
"""
Integration tests for FileCollection RO-Crate transformations.

Tests bidirectional transformation between D4D FileCollection and
RO-Crate nested Dataset entities.
"""

import unittest
from pathlib import Path
import sys

# Add src to path for imports
repo_root = Path(__file__).parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    from src.fairscape_integration.d4d_to_fairscape import D4DToFairscapeConverter
    from src.fairscape_integration.fairscape_to_d4d import FairscapeToD4DConverter
    # Try to instantiate to check if FAIRSCAPE models are actually available
    try:
        _test_converter = D4DToFairscapeConverter()
        FAIRSCAPE_AVAILABLE = True
    except RuntimeError:
        FAIRSCAPE_AVAILABLE = False
except ImportError:
    FAIRSCAPE_AVAILABLE = False


@unittest.skipIf(not FAIRSCAPE_AVAILABLE, "FAIRSCAPE integration not available")
class TestFileCollectionROCrateTransformation(unittest.TestCase):
    """Test D4D ↔ RO-Crate transformations with FileCollection."""

    def setUp(self):
        """Set up converters."""
        self.d4d_to_rocrate = D4DToFairscapeConverter()
        self.rocrate_to_d4d = FairscapeToD4DConverter()

    def test_d4d_to_rocrate_with_filecollections(self):
        """Test D4D with FileCollections converts to RO-Crate with nested Datasets."""
        d4d_data = {
            'id': 'test-dataset',
            'title': 'Test Dataset',
            'description': 'A dataset with file collections',
            'version': '1.0',
            'license': 'MIT',
            'file_collections': [
                {
                    'id': 'collection-1',
                    'name': 'Training Files',
                    'description': 'Training data files',
                    'collection_type': 'training_split',
                    'total_bytes': 1048576,
                    'file_count': 100,
                    'resources': [
                        {
                            'id': 'train001.csv',
                            'file_type': 'data_file',
                            'format': 'CSV',
                            'bytes': 10485,
                            'sha256': 'abc123'
                        }
                    ]
                },
                {
                    'id': 'collection-2',
                    'name': 'Test Files',
                    'description': 'Test data files',
                    'collection_type': 'test_split',
                    'total_bytes': 524288,
                    'file_count': 50,
                    'resources': [
                        {
                            'id': 'test001.json',
                            'file_type': 'data_file',
                            'format': 'JSON',
                            'bytes': 10485,
                            'md5': 'def456'
                        }
                    ]
                }
            ],
            'total_file_count': 150,
            'total_size_bytes': 1572864
        }

        # Convert to RO-Crate
        rocrate = self.d4d_to_rocrate.convert(d4d_data)

        # Verify RO-Crate structure
        rocrate_dict = rocrate.model_dump(by_alias=True, exclude_none=True)
        graph = rocrate_dict['@graph']

        # Should have: metadata descriptor + root dataset + 2 file collections = 4 entities
        self.assertEqual(len(graph), 4)

        # Find root dataset
        root_dataset = None
        nested_datasets = []
        for entity in graph:
            if entity.get('@id') == './':
                root_dataset = entity
            elif entity.get('@id') != 'ro-crate-metadata.json':
                # Check if Dataset is in @type (can be string or list)
                entity_type = entity.get('@type', [])
                if isinstance(entity_type, str):
                    entity_type = [entity_type]
                if 'Dataset' in entity_type and entity.get('@id') != './':
                    nested_datasets.append(entity)

        # Verify root dataset
        self.assertIsNotNone(root_dataset)
        self.assertEqual(root_dataset['name'], 'Test Dataset')
        self.assertIn('hasPart', root_dataset)
        self.assertEqual(len(root_dataset['hasPart']), 2)

        # Verify nested datasets (file collections)
        self.assertEqual(len(nested_datasets), 2)

        # Find training collection
        training_collection = next(
            (ds for ds in nested_datasets if ds.get('@id') == 'collection-1'),
            None
        )
        self.assertIsNotNone(training_collection)
        self.assertEqual(training_collection['name'], 'Training Files')
        # Note: encodingFormat and sha256 are now on individual File objects, not FileCollection
        # FileCollection has aggregate total_bytes which maps to contentSize
        self.assertEqual(training_collection.get('contentSize'), '1048576')
        self.assertEqual(training_collection['d4d:fileCount'], 100)

    def test_rocrate_to_d4d_with_nested_datasets(self):
        """Test RO-Crate with nested Datasets converts to D4D with FileCollections."""
        rocrate_data = {
            '@context': {
                '@vocab': 'https://schema.org/',
                'd4d': 'https://w3id.org/bridge2ai/data-sheets-schema/'
            },
            '@graph': [
                {
                    '@id': 'ro-crate-metadata.json',
                    '@type': 'CreativeWork',
                    'conformsTo': {'@id': 'https://w3id.org/ro/crate/1.2'},
                    'about': {'@id': './'}
                },
                {
                    '@id': './',
                    '@type': ['Dataset', 'https://w3id.org/EVI#ROCrate'],
                    'name': 'Test Dataset',
                    'description': 'A dataset with nested datasets',
                    'version': '1.0',
                    'license': 'MIT',
                    'author': 'Test Author',
                    'hasPart': [
                        {'@id': '#files-raw'},
                        {'@id': '#files-processed'}
                    ]
                },
                {
                    '@id': '#files-raw',
                    '@type': 'Dataset',
                    'name': 'Raw Data Files',
                    'description': 'Unprocessed data',
                    'encodingFormat': 'CSV',
                    'contentSize': '2097152',
                    'sha256': 'raw123',
                    'd4d:collectionType': 'raw_data',
                    'd4d:fileCount': 200
                },
                {
                    '@id': '#files-processed',
                    '@type': 'Dataset',
                    'name': 'Processed Data Files',
                    'description': 'Cleaned data',
                    'encodingFormat': 'JSON',
                    'contentSize': '1048576',
                    'md5': 'proc456',
                    'd4d:collectionType': 'processed_data',
                    'd4d:fileCount': 100
                }
            ]
        }

        # Convert to D4D
        d4d_data = self.rocrate_to_d4d.convert(rocrate_data)

        # Verify D4D structure
        self.assertEqual(d4d_data['title'], 'Test Dataset')
        self.assertIn('file_collections', d4d_data)
        self.assertEqual(len(d4d_data['file_collections']), 2)

        # Find raw collection
        raw_collection = next(
            (fc for fc in d4d_data['file_collections'] if fc.get('id') == '#files-raw'),
            None
        )
        self.assertIsNotNone(raw_collection)
        self.assertEqual(raw_collection['name'], 'Raw Data Files')
        # Note: format, bytes, sha256 are now file-level properties, not collection-level
        # Collection has aggregate total_bytes from RO-Crate contentSize
        self.assertEqual(raw_collection.get('total_bytes'), 2097152)
        self.assertEqual(raw_collection['collection_type'], ['raw_data'])
        self.assertEqual(raw_collection['file_count'], 200)

    def test_roundtrip_preservation(self):
        """Test D4D → RO-Crate → D4D preserves FileCollection structure."""
        original_d4d = {
            'id': 'roundtrip-dataset',
            'title': 'Round-trip Test Dataset',
            'description': 'Testing round-trip transformation',
            'version': '1.0',
            'license': 'Apache-2.0',
            'file_collections': [
                {
                    'id': 'test-collection',
                    'name': 'Test Files',
                    'description': 'Test data',
                    'collection_type': ['test_split'],
                    'total_bytes': 1024,
                    'file_count': 10,
                    'path': '/data/test/',
                    'resources': [
                        {
                            'id': 'test001.csv',
                            'file_type': 'data_file',
                            'format': 'CSV',
                            'bytes': 102,
                            'encoding': 'UTF-8',
                            'sha256': 'test123'
                        }
                    ]
                }
            ],
            'total_file_count': 10,
            'total_size_bytes': 1024
        }

        # D4D → RO-Crate
        rocrate = self.d4d_to_rocrate.convert(original_d4d)
        rocrate_dict = rocrate.model_dump(by_alias=True, exclude_none=True)

        # RO-Crate → D4D
        recovered_d4d = self.rocrate_to_d4d.convert(rocrate_dict)

        # Verify preservation
        self.assertEqual(recovered_d4d['title'], original_d4d['title'])
        self.assertIn('file_collections', recovered_d4d)
        self.assertEqual(len(recovered_d4d['file_collections']), 1)

        recovered_collection = recovered_d4d['file_collections'][0]
        original_collection = original_d4d['file_collections'][0]

        # Check collection-level properties preserved
        self.assertEqual(recovered_collection['name'], original_collection['name'])
        self.assertEqual(recovered_collection.get('total_bytes'), original_collection['total_bytes'])
        self.assertEqual(recovered_collection['file_count'], original_collection['file_count'])
        self.assertEqual(recovered_collection['collection_type'], original_collection['collection_type'])
        # Note: File-level properties (format, encoding, sha256) are in resources, not on collection

    def test_backward_compatibility_no_filecollections(self):
        """Test that D4D without FileCollections still works."""
        legacy_d4d = {
            'id': 'legacy-dataset',
            'title': 'Legacy Dataset',
            'description': 'Dataset without file collections',
            'version': '1.0',
            'license': 'MIT',
            'bytes': 2048,
            'format': 'CSV',
            'md5': 'legacy123'
        }

        # Should convert without errors
        rocrate = self.d4d_to_rocrate.convert(legacy_d4d)
        rocrate_dict = rocrate.model_dump(by_alias=True, exclude_none=True)

        # Verify file properties at root level
        root_dataset = next(
            (e for e in rocrate_dict['@graph'] if e.get('@id') == './'),
            None
        )
        self.assertIsNotNone(root_dataset)
        self.assertEqual(root_dataset['contentSize'], '2048')
        self.assertEqual(root_dataset['evi:md5'], 'legacy123')


if __name__ == '__main__':
    unittest.main()
