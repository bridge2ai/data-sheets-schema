#!/usr/bin/env python3
"""
Tests for ROCrateParser utility.

Tests RO-Crate JSON-LD parsing and property extraction.
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

from src.fairscape_integration.utils.rocrate_parser import ROCrateParser


class TestROCrateParser(unittest.TestCase):
    """Test ROCrateParser JSON-LD parsing."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal RO-Crate JSON-LD structure
        self.rocrate_data = {
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
                    "name": "Test Dataset",
                    "description": "A test RO-Crate dataset",
                    "version": "1.0",
                    "license": "MIT",
                    "keywords": ["test", "rocrate"],
                    "author": [
                        {
                            "@id": "#person1",
                            "name": "Test Author"
                        }
                    ],
                    "hasPart": [
                        {"@id": "#file1"},
                        {"@id": "#file2"}
                    ],
                    "rai:dataCollection": "Experimental data",
                    "contentSize": "1024000"
                },
                {
                    "@id": "#person1",
                    "@type": "Person",
                    "name": "Test Author",
                    "affiliation": "Test University"
                },
                {
                    "@id": "#file1",
                    "@type": "File",
                    "name": "data.csv",
                    "encodingFormat": "text/csv"
                }
            ]
        }

        # Write to temporary file
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(self.rocrate_data, self.temp_file)
        self.temp_file.close()

        self.parser = ROCrateParser(self.temp_file.name, verbose=False)

    def tearDown(self):
        """Clean up temporary files."""
        Path(self.temp_file.name).unlink()

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        self.assertEqual(self.parser.rocrate_path, Path(self.temp_file.name))
        self.assertIsNotNone(self.parser.rocrate_data)
        self.assertIsNotNone(self.parser.graph)

    def test_parser_with_nonexistent_file(self):
        """Test parser raises error for nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            ROCrateParser("/nonexistent/rocrate.json")

    def test_find_root_dataset(self):
        """Test finding root dataset entity."""
        root = self.parser.get_root_dataset()

        self.assertIsNotNone(root)
        self.assertEqual(root['@id'], './')
        self.assertEqual(root['name'], 'Test Dataset')

    def test_get_property_direct(self):
        """Test getting property with direct lookup."""
        name = self.parser.get_property('name')
        self.assertEqual(name, 'Test Dataset')

        description = self.parser.get_property('description')
        self.assertEqual(description, 'A test RO-Crate dataset')

    def test_get_property_nested(self):
        """Test getting nested property."""
        # Test nested property (author[0].name)
        author_name = self.parser.get_property('author[0].name')
        self.assertEqual(author_name, 'Test Author')

    def test_get_property_with_namespace(self):
        """Test getting property with namespace prefix."""
        data_collection = self.parser.get_property('rai:dataCollection')
        self.assertEqual(data_collection, 'Experimental data')

    def test_get_property_nonexistent(self):
        """Test getting nonexistent property returns None."""
        result = self.parser.get_property('nonexistent_property')
        self.assertIsNone(result)

    def test_extract_all_properties(self):
        """Test extracting all flattened properties."""
        all_props = self.parser.extract_all_properties()

        self.assertIsInstance(all_props, dict)
        self.assertIn('name', all_props)
        self.assertIn('description', all_props)
        self.assertIn('keywords', all_props)

    def test_get_entity_by_id(self):
        """Test getting entity by @id."""
        person = self.parser.get_entity_by_id('#person1')

        self.assertIsNotNone(person)
        self.assertEqual(person['@type'], 'Person')
        self.assertEqual(person['name'], 'Test Author')

    def test_get_entity_by_id_nonexistent(self):
        """Test getting nonexistent entity returns None."""
        result = self.parser.get_entity_by_id('#nonexistent')
        self.assertIsNone(result)

    def test_get_entities_by_type(self):
        """Test getting all entities of a specific type."""
        persons = self.parser.get_entities_by_type('Person')

        self.assertEqual(len(persons), 1)
        self.assertEqual(persons[0]['name'], 'Test Author')

    def test_get_entities_by_type_dataset(self):
        """Test getting Dataset entities."""
        datasets = self.parser.get_entities_by_type('Dataset')

        self.assertGreaterEqual(len(datasets), 1)
        # Root dataset should be in the list
        self.assertTrue(any(d.get('@id') == './' for d in datasets))

    def test_get_entities_by_type_none_found(self):
        """Test getting entities of type that doesn't exist."""
        results = self.parser.get_entities_by_type('NonexistentType')
        self.assertEqual(len(results), 0)

    def test_get_unmapped_properties(self):
        """Test getting unmapped properties."""
        # Use a small set of mapped properties
        mapped = {'name', 'description', 'keywords'}
        unmapped = self.parser.get_unmapped_properties(mapped)

        self.assertIsInstance(unmapped, dict)
        # Should have unmapped properties like version, license, etc.
        self.assertGreater(len(unmapped), 0)

        # Mapped properties should not be in unmapped
        for prop in mapped:
            # Check base property name (before dots/brackets)
            unmapped_base_props = [p.split('.')[0].split('[')[0] for p in unmapped.keys()]
            self.assertNotIn(prop, unmapped_base_props)

    def test_flatten_properties_dict(self):
        """Test flattening nested dictionary."""
        obj = {
            'name': 'Test',
            'nested': {
                'field': 'value',
                'deep': {
                    'field2': 'value2'
                }
            }
        }

        flattened = self.parser._flatten_properties(obj)

        self.assertIn('name', flattened)
        self.assertIn('nested', flattened)
        self.assertIn('nested.field', flattened)
        self.assertIn('nested.deep', flattened)
        self.assertIn('nested.deep.field2', flattened)

    def test_flatten_properties_list(self):
        """Test flattening list."""
        obj = {
            'items': ['item1', 'item2', 'item3']
        }

        flattened = self.parser._flatten_properties(obj)

        self.assertIn('items', flattened)
        self.assertEqual(flattened['items'], ['item1', 'item2', 'item3'])

    def test_context_extraction(self):
        """Test that context is extracted."""
        self.assertIsNotNone(self.parser.context)
        self.assertEqual(
            self.parser.context,
            "https://w3id.org/ro/crate/1.1/context"
        )

    def test_graph_extraction(self):
        """Test that graph entities are extracted."""
        self.assertIsInstance(self.parser.graph, list)
        self.assertGreater(len(self.parser.graph), 0)

        # Should have at least: metadata descriptor, root dataset, person, file
        self.assertGreaterEqual(len(self.parser.graph), 4)


class TestROCrateParserEdgeCases(unittest.TestCase):
    """Test ROCrateParser edge cases."""

    def test_parser_with_empty_graph(self):
        """Test parser with empty @graph."""
        rocrate_data = {
            "@context": "https://w3id.org/ro/crate/1.1/context",
            "@graph": []
        }

        temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(rocrate_data, temp_file)
        temp_file.close()

        try:
            parser = ROCrateParser(temp_file.name, verbose=False)
            self.assertIsNone(parser.get_root_dataset())
        finally:
            Path(temp_file.name).unlink()

    def test_parser_with_missing_graph(self):
        """Test parser with missing @graph."""
        rocrate_data = {
            "@context": "https://w3id.org/ro/crate/1.1/context"
        }

        temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(rocrate_data, temp_file)
        temp_file.close()

        try:
            parser = ROCrateParser(temp_file.name, verbose=False)
            self.assertEqual(parser.graph, [])
        finally:
            Path(temp_file.name).unlink()


if __name__ == '__main__':
    unittest.main()
