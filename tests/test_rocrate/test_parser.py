#!/usr/bin/env python3
"""
Unit tests for rocrate_parser.py

Tests RO-Crate JSON-LD parsing functionality.
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from claude.agents.scripts.rocrate_parser import ROCrateParser
except ImportError:
    try:
        # Alternative import path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "scripts"))
        from rocrate_parser import ROCrateParser
    except ImportError as e:
        print(f"Warning: Could not import rocrate_parser: {e}", file=sys.stderr)
        ROCrateParser = None


class TestROCrateParser(unittest.TestCase):
    """Test RO-Crate parser functionality."""

    def setUp(self):
        """Set up test fixtures - create temporary directory with sample RO-Crate."""
        if ROCrateParser is None:
            self.skipTest("rocrate_parser module not available")

        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

        # Create a sample RO-Crate JSON-LD file
        self.sample_rocrate = {
            "@context": "https://w3id.org/ro/crate/1.1/context",
            "@graph": [
                {
                    "@type": "CreativeWork",
                    "@id": "ro-crate-metadata.json",
                    "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
                    "about": {"@id": "./"}
                },
                {
                    "@type": "Dataset",
                    "@id": "./",
                    "name": "Test Dataset",
                    "description": "A test dataset for unit testing",
                    "author": [
                        {
                            "@type": "Person",
                            "@id": "#person1",
                            "name": "John Doe",
                            "email": "john@example.com"
                        }
                    ],
                    "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
                    "datePublished": "2024-01-01",
                    "keywords": ["test", "sample", "rocrate"]
                },
                {
                    "@type": "Person",
                    "@id": "#person1",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "affiliation": {
                        "@type": "Organization",
                        "name": "Test University"
                    }
                },
                {
                    "@type": "Organization",
                    "@id": "#org1",
                    "name": "Test University",
                    "url": "https://test.edu"
                }
            ]
        }

        self.rocrate_file = self.test_path / "ro-crate-metadata.json"
        with open(self.rocrate_file, 'w', encoding='utf-8') as f:
            json.dump(self.sample_rocrate, f, indent=2)

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, 'test_dir'):
            shutil.rmtree(self.test_dir)

    def test_parser_initialization(self):
        """Test ROCrateParser initialization."""
        parser = ROCrateParser(str(self.rocrate_file))
        self.assertIsNotNone(parser)
        self.assertEqual(parser.rocrate_path, self.rocrate_file)

    def test_parser_initialization_file_not_found(self):
        """Test parser initialization with nonexistent file."""
        nonexistent = self.test_path / "nonexistent.json"

        with self.assertRaises(FileNotFoundError):
            ROCrateParser(str(nonexistent))

    def test_load_rocrate(self):
        """Test RO-Crate loading."""
        parser = ROCrateParser(str(self.rocrate_file))

        self.assertIsNotNone(parser.rocrate_data)
        self.assertIn("@context", parser.rocrate_data)
        self.assertIn("@graph", parser.rocrate_data)

    def test_find_root_dataset(self):
        """Test finding root Dataset entity."""
        parser = ROCrateParser(str(self.rocrate_file))

        root = parser.get_root_dataset()
        self.assertIsNotNone(root)
        self.assertEqual(root.get("@id"), "./")
        self.assertIn("Dataset", root.get("@type", []))

    def test_get_property_simple(self):
        """Test getting simple property."""
        parser = ROCrateParser(str(self.rocrate_file))

        name = parser.get_property("name")
        self.assertEqual(name, "Test Dataset")

        description = parser.get_property("description")
        self.assertEqual(description, "A test dataset for unit testing")

    def test_get_property_nested(self):
        """Test getting nested property."""
        parser = ROCrateParser(str(self.rocrate_file))

        # Get first author's name
        author_name = parser.get_property("author[0].name")
        self.assertEqual(author_name, "John Doe")

    def test_get_property_nonexistent(self):
        """Test getting nonexistent property."""
        parser = ROCrateParser(str(self.rocrate_file))

        nonexistent = parser.get_property("nonexistent_property")
        self.assertIsNone(nonexistent)

    def test_extract_all_properties(self):
        """Test extracting all flattened properties."""
        parser = ROCrateParser(str(self.rocrate_file))

        all_props = parser.extract_all_properties()
        self.assertIsInstance(all_props, dict)
        self.assertIn("name", all_props)
        self.assertIn("description", all_props)
        self.assertGreater(len(all_props), 0)

    def test_flatten_properties(self):
        """Test property flattening."""
        parser = ROCrateParser(str(self.rocrate_file))

        # Verify flattened properties include nested paths
        self.assertIn("author", parser.all_properties)
        # Arrays should be flattened with indices
        author_keys = [k for k in parser.all_properties.keys() if k.startswith("author")]
        self.assertGreater(len(author_keys), 0)

    def test_get_entity_by_id(self):
        """Test getting entity by @id."""
        parser = ROCrateParser(str(self.rocrate_file))

        person = parser.get_entity_by_id("#person1")
        self.assertIsNotNone(person)
        self.assertEqual(person.get("name"), "John Doe")

    def test_get_entity_by_id_nonexistent(self):
        """Test getting nonexistent entity by @id."""
        parser = ROCrateParser(str(self.rocrate_file))

        entity = parser.get_entity_by_id("#nonexistent")
        self.assertIsNone(entity)

    def test_get_entities_by_type(self):
        """Test getting entities by @type."""
        parser = ROCrateParser(str(self.rocrate_file))

        persons = parser.get_entities_by_type("Person")
        self.assertIsInstance(persons, list)
        self.assertEqual(len(persons), 1)
        self.assertEqual(persons[0].get("name"), "John Doe")

    def test_get_entities_by_type_multiple(self):
        """Test getting multiple entities of same type."""
        parser = ROCrateParser(str(self.rocrate_file))

        # There should be at least one Organization
        orgs = parser.get_entities_by_type("Organization")
        self.assertIsInstance(orgs, list)
        self.assertGreater(len(orgs), 0)

    def test_get_entities_by_type_nonexistent(self):
        """Test getting entities of nonexistent type."""
        parser = ROCrateParser(str(self.rocrate_file))

        entities = parser.get_entities_by_type("NonexistentType")
        self.assertIsInstance(entities, list)
        self.assertEqual(len(entities), 0)

    def test_get_unmapped_properties(self):
        """Test getting unmapped properties."""
        parser = ROCrateParser(str(self.rocrate_file))

        # Provide a set of mapped properties
        mapped = {"name", "description", "author"}

        unmapped = parser.get_unmapped_properties(mapped)
        self.assertIsInstance(unmapped, dict)

        # Should not include mapped properties
        for prop in unmapped.keys():
            base_prop = prop.split('.')[0].split('[')[0]
            self.assertNotIn(base_prop, mapped)

    def test_context_loading(self):
        """Test @context loading."""
        parser = ROCrateParser(str(self.rocrate_file))

        self.assertIsNotNone(parser.context)
        # Simple context is just a string URL
        self.assertEqual(parser.context, "https://w3id.org/ro/crate/1.1/context")

    def test_graph_loading(self):
        """Test @graph loading."""
        parser = ROCrateParser(str(self.rocrate_file))

        self.assertIsInstance(parser.graph, list)
        self.assertEqual(len(parser.graph), 4)  # 4 entities in sample

    def test_complex_nested_property(self):
        """Test accessing complex nested properties."""
        parser = ROCrateParser(str(self.rocrate_file))

        # Access array property
        keywords = parser.get_property("keywords")
        self.assertIsInstance(keywords, list)
        self.assertEqual(len(keywords), 3)
        self.assertIn("test", keywords)


if __name__ == '__main__':
    unittest.main()
