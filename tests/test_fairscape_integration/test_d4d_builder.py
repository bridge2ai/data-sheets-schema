#!/usr/bin/env python3
"""
Tests for D4DBuilder utility.

Tests D4D dataset building and field transformations.
"""

import unittest
import sys
import tempfile
import json
from pathlib import Path
from datetime import datetime

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.fairscape_integration.utils.d4d_builder import D4DBuilder
from src.fairscape_integration.utils.rocrate_parser import ROCrateParser
from src.fairscape_integration.utils.mapping_loader import MappingLoader


class TestD4DBuilder(unittest.TestCase):
    """Test D4DBuilder dataset construction."""

    def setUp(self):
        """Set up test fixtures."""
        # Create test mapping TSV
        self.tsv_content = """Class\tD4D Property\tType\tDef\tD4D description\tFAIRSCAPE RO-Crate Property\tCovered by FAIRSCAPE? Yes =1; No = 0\tDirect mapping? Yes =1; No = 0
D4D: Dataset\t\t\t\t\t\t\t
RO-Crate: Root Dataset\ttitle\tstr\t\tThe title\tname\t1\t1
RO-Crate: Root Dataset\tdescription\tstr\t\tThe description\tdescription\t1\t1
RO-Crate: Root Dataset\tkeywords\tlist[str]\t\tKeywords\tkeywords\t1\t1
RO-Crate: Root Dataset\tcreated_on\tdate\t\tCreation date\tdateCreated\t1\t1
RO-Crate: Root Dataset\tversion\tint\t\tVersion number\tversion\t1\t1
RO-Crate: Root Dataset\tdoi\turi\t\tDOI\tidentifier\t1\t1
RO-Crate: Root Dataset\tcompression\tCompressionEnum\t\tCompression\tencodingFormat\t1\t1
RO-Crate: Root Dataset\tcreators\tPerson\t\tCreators\tauthor\t1\t1
"""
        self.temp_tsv = tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False)
        self.temp_tsv.write(self.tsv_content)
        self.temp_tsv.close()

        self.mapping_loader = MappingLoader(self.temp_tsv.name, verbose=False)

        # Create comprehensive RO-Crate with various field types
        self.test_rocrate = {
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
                    "description": "Test description",
                    "keywords": ["test", "data"],
                    "dateCreated": "2024-01-15T10:30:00Z",
                    "version": "2",
                    "identifier": "10.1234/test",
                    "encodingFormat": "application/gzip",
                    "author": [
                        {
                            "@id": "#person1",
                            "name": "John Doe"
                        },
                        {
                            "@id": "#person2",
                            "givenName": "Jane",
                            "familyName": "Smith"
                        }
                    ]
                },
                {
                    "@id": "#person1",
                    "@type": "Person",
                    "name": "John Doe"
                },
                {
                    "@id": "#person2",
                    "@type": "Person",
                    "givenName": "Jane",
                    "familyName": "Smith"
                }
            ]
        }

        # Write RO-Crate file
        self.test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_rocrate, self.test_file)
        self.test_file.close()

        self.rocrate_parser = ROCrateParser(self.test_file.name, verbose=False)
        self.builder = D4DBuilder(self.mapping_loader, verbose=False)

    def tearDown(self):
        """Clean up temporary files."""
        Path(self.temp_tsv.name).unlink()
        Path(self.test_file.name).unlink()

    def test_builder_initialization(self):
        """Test builder initializes correctly."""
        self.assertIsNotNone(self.builder.mapping)
        self.assertEqual(self.builder.d4d_data, {})
        self.assertFalse(self.builder.verbose)

    def test_builder_with_verbose(self):
        """Test builder with verbose output."""
        verbose_builder = D4DBuilder(self.mapping_loader, verbose=True)
        self.assertTrue(verbose_builder.verbose)

    def test_build_dataset(self):
        """Test building complete dataset from RO-Crate."""
        dataset = self.builder.build_dataset(self.rocrate_parser)

        self.assertIsInstance(dataset, dict)
        self.assertGreater(len(dataset), 0)

        # Check that mapped fields are present
        self.assertIn('title', dataset)
        self.assertIn('description', dataset)
        self.assertIn('keywords', dataset)

    def test_transform_string_field(self):
        """Test string field transformation."""
        dataset = self.builder.build_dataset(self.rocrate_parser)

        self.assertEqual(dataset['title'], 'Test Dataset')
        self.assertEqual(dataset['description'], 'Test description')

    def test_transform_date_field(self):
        """Test date transformation (ISO 8601 to YYYY-MM-DD)."""
        dataset = self.builder.build_dataset(self.rocrate_parser)

        self.assertIn('created_on', dataset)
        self.assertEqual(dataset['created_on'], '2024-01-15')

    def test_transform_date_iso8601(self):
        """Test ISO 8601 datetime transformation."""
        result = self.builder._transform_date("2024-01-15T10:30:00Z")
        self.assertEqual(result, "2024-01-15")

    def test_transform_date_already_formatted(self):
        """Test date already in YYYY-MM-DD format."""
        result = self.builder._transform_date("2024-01-15")
        self.assertEqual(result, "2024-01-15")

    def test_transform_date_none(self):
        """Test None date transformation."""
        result = self.builder._transform_date(None)
        self.assertIsNone(result)

    def test_transform_int_field(self):
        """Test integer transformation."""
        dataset = self.builder.build_dataset(self.rocrate_parser)

        self.assertIn('version', dataset)
        self.assertEqual(dataset['version'], 2)
        self.assertIsInstance(dataset['version'], int)

    def test_transform_int_from_string(self):
        """Test integer transformation from string."""
        result = self.builder._transform_int("42")
        self.assertEqual(result, 42)

    def test_transform_int_invalid(self):
        """Test invalid integer transformation."""
        result = self.builder._transform_int("not a number")
        self.assertIsNone(result)

    def test_transform_int_none(self):
        """Test None integer transformation."""
        result = self.builder._transform_int(None)
        self.assertIsNone(result)

    def test_transform_list_field(self):
        """Test list transformation."""
        dataset = self.builder.build_dataset(self.rocrate_parser)

        self.assertIn('keywords', dataset)
        self.assertEqual(dataset['keywords'], ['test', 'data'])
        self.assertIsInstance(dataset['keywords'], list)

    def test_transform_list_to_list(self):
        """Test transforming non-list to list."""
        result = self.builder._transform_list("single_value", "keywords")
        self.assertEqual(result, ["single_value"])

    def test_transform_list_none(self):
        """Test None list transformation."""
        result = self.builder._transform_list(None, "keywords")
        self.assertIsNone(result)

    def test_transform_uri_field(self):
        """Test URI transformation."""
        dataset = self.builder.build_dataset(self.rocrate_parser)

        self.assertIn('doi', dataset)
        self.assertEqual(dataset['doi'], 'https://doi.org/10.1234/test')

    def test_transform_uri_doi(self):
        """Test DOI transformation (add https prefix)."""
        result = self.builder._transform_uri("10.1234/test")
        self.assertEqual(result, "https://doi.org/10.1234/test")

    def test_transform_uri_already_formatted(self):
        """Test URI already formatted."""
        result = self.builder._transform_uri("https://example.com")
        self.assertEqual(result, "https://example.com")

    def test_transform_uri_none(self):
        """Test None URI transformation."""
        result = self.builder._transform_uri(None)
        self.assertIsNone(result)

    def test_transform_enum_field(self):
        """Test enum transformation."""
        dataset = self.builder.build_dataset(self.rocrate_parser)

        self.assertIn('compression', dataset)
        self.assertEqual(dataset['compression'], 'GZIP')

    def test_transform_enum_compression_gzip(self):
        """Test compression enum transformation for gzip."""
        result = self.builder._transform_enum("application/gzip", "compression")
        self.assertEqual(result, "GZIP")

    def test_transform_enum_compression_zip(self):
        """Test compression enum transformation for zip."""
        result = self.builder._transform_enum("application/zip", "compression")
        self.assertEqual(result, "ZIP")

    def test_transform_enum_none(self):
        """Test None enum transformation."""
        result = self.builder._transform_enum(None, "compression")
        self.assertIsNone(result)

    def test_transform_person_org_field(self):
        """Test Person/Organization transformation."""
        dataset = self.builder.build_dataset(self.rocrate_parser)

        self.assertIn('creators', dataset)
        # Should extract names from Person entities
        self.assertIsInstance(dataset['creators'], list)
        self.assertIn('John Doe', dataset['creators'])
        self.assertIn('Jane Smith', dataset['creators'])

    def test_extract_name_from_entity_simple(self):
        """Test extracting name from simple entity."""
        entity = {"@id": "#person1", "name": "John Doe"}
        result = self.builder._extract_name_from_entity(entity)
        self.assertEqual(result, "John Doe")

    def test_extract_name_from_entity_given_family(self):
        """Test extracting name from givenName/familyName entity."""
        entity = {"@id": "#person2", "givenName": "Jane", "familyName": "Smith"}
        result = self.builder._extract_name_from_entity(entity)
        self.assertEqual(result, "Jane Smith")

    def test_extract_name_from_entity_id_fallback(self):
        """Test fallback to @id for name."""
        entity = {"@id": "#person3"}
        result = self.builder._extract_name_from_entity(entity)
        self.assertEqual(result, "#person3")

    def test_extract_name_from_entity_none(self):
        """Test extracting name from None entity."""
        result = self.builder._extract_name_from_entity(None)
        self.assertIsNone(result)

    def test_transform_bool_true(self):
        """Test boolean transformation for true values."""
        self.assertTrue(self.builder._transform_bool(True))
        self.assertTrue(self.builder._transform_bool("true"))
        self.assertTrue(self.builder._transform_bool("yes"))
        self.assertTrue(self.builder._transform_bool("1"))

    def test_transform_bool_false(self):
        """Test boolean transformation for false values."""
        self.assertFalse(self.builder._transform_bool(False))
        self.assertFalse(self.builder._transform_bool("false"))
        self.assertFalse(self.builder._transform_bool("no"))
        self.assertFalse(self.builder._transform_bool("0"))

    def test_transform_bool_none(self):
        """Test None boolean transformation."""
        result = self.builder._transform_bool(None)
        self.assertIsNone(result)

    def test_transform_bool_invalid(self):
        """Test invalid boolean transformation."""
        result = self.builder._transform_bool("invalid")
        self.assertIsNone(result)

    def test_set_field(self):
        """Test manually setting a field."""
        self.builder.set_field('custom_field', 'custom_value')
        self.assertEqual(self.builder.d4d_data['custom_field'], 'custom_value')

    def test_get_field(self):
        """Test getting a field value."""
        self.builder.set_field('test_field', 'test_value')
        result = self.builder.get_field('test_field')
        self.assertEqual(result, 'test_value')

    def test_get_field_nonexistent(self):
        """Test getting nonexistent field returns None."""
        result = self.builder.get_field('nonexistent_field')
        self.assertIsNone(result)

    def test_get_dataset(self):
        """Test getting complete dataset."""
        self.builder.set_field('field1', 'value1')
        self.builder.set_field('field2', 'value2')

        dataset = self.builder.get_dataset()

        self.assertIsInstance(dataset, dict)
        self.assertEqual(dataset['field1'], 'value1')
        self.assertEqual(dataset['field2'], 'value2')

    def test_get_dataset_returns_copy(self):
        """Test that get_dataset returns a copy, not reference."""
        self.builder.set_field('field1', 'value1')

        dataset1 = self.builder.get_dataset()
        dataset2 = self.builder.get_dataset()

        # Should be equal but not the same object
        self.assertEqual(dataset1, dataset2)
        self.assertIsNot(dataset1, dataset2)

        # Modifying one shouldn't affect the other
        dataset1['new_field'] = 'new_value'
        self.assertNotIn('new_field', dataset2)


if __name__ == '__main__':
    unittest.main()
