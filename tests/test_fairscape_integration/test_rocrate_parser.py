#!/usr/bin/env python3
"""
Tests for ROCrateParser utility.

Tests RO-Crate JSON-LD parsing and property extraction. #4186: a crate is
read as the static-map arm reads one, and one that is not UTF-8 is refused
with its `CrateEncodingError` by the parser and by `fairscape-cli parse`,
`merge`, `rank` and `transform`. #4187: an `@graph` written as one node
object is read as that one entity by the parser and by `fairscape-cli info`.
"""

import contextlib
import io
import unittest
import sys
import tempfile
import json
from pathlib import Path

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from data_sheets_schema.rocrate_map import CrateEncodingError
from src.fairscape_integration.utils.rocrate_parser import ROCrateParser, graph_entities

#: The AI-READI v3.0.0 release crate and its copy among the raw downloads,
#: both windows-1252, not UTF-8 (#4089)
AI_READI = repo_root / "data/ro-crate_packages/AI_READI/raw/ro-crate-metadata.json"
AI_READI_DOWNLOAD = (repo_root / "data/raw/AI_READI/"
                     "aireadi_ro_crate_metadata_2026-08-12.json")
#: A UTF-8 crate, for a run that reads one before the crate it refuses
VOICE = repo_root / "data/ro-crate/examples/voice_fairscape_test.json"
#: VOICE's provenance graph, whose `@graph` is one node object (#4187)
PROV_GRAPH = repo_root / "data/ro-crate_packages/VOICE/raw/ro-crate-prov-graph.json"
#: The mapping `merge`, `rank` and `transform` read
MAPPING = repo_root / "data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv"


def refusal(path):
    """How a tracked AI-READI copy, given by its path, is refused, word for
    word: the numbers are those crate_manifest.yaml's `encoding_note` gives,
    and the ending is the one `fairscape-cli rocrate-to-d4d` and `info` give
    (#4192)."""
    return (f"{path} is not UTF-8, as RFC 8259 requires of JSON: byte 0xa9 at "
            "offset 5096, 31 undecodable byte(s) in all. Not decoded under a "
            "guessed encoding; transcode it to UTF-8 from the encoding it is "
            "written in")


def cli_runner():
    """A Click runner that keeps stderr apart from stdout, under Click 8.1
    and 8.2."""
    from click.testing import CliRunner
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


def written(directory, name, crate):
    """`crate` written as UTF-8 JSON to `name` under `directory`."""
    path = Path(directory) / name
    path.write_text(json.dumps(crate, ensure_ascii=False), encoding="utf-8")
    return path


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


class TestCrateEncoding(unittest.TestCase):
    """#4186: the parser opened a crate as UTF-8, and AI-READI's
    windows-1252 release crate ended `fairscape-cli parse`, `merge`, `rank`
    and `transform` with a bare `'utf-8' codec can't decode byte 0xa9 in
    position 5096`. The crate is read as the static-map arm reads one
    (`rocrate_map.read_crate_json`), and refused with a CrateEncodingError
    that names the first byte that does not decode and says to transcode
    the file."""

    def test_the_parser_refuses_a_crate_that_is_not_utf8(self):
        for path in (AI_READI, AI_READI_DOWNLOAD):
            for given in (path, str(path)):
                with self.subTest(crate=path.name, given=type(given).__name__):
                    printed = io.StringIO()
                    with self.assertRaises(CrateEncodingError) as cm, \
                            contextlib.redirect_stdout(printed):
                        ROCrateParser(given, verbose=True)
                    self.assertIsInstance(cm.exception, ValueError)
                    self.assertEqual(str(cm.exception), refusal(path))
                    # Refused before any of it is read as a crate
                    self.assertEqual(printed.getvalue(), "")

    def test_a_utf8_crate_is_read_as_written(self):
        """Text that is not ASCII is decoded as UTF-8. Read as windows-1252,
        the name would be `DonnÃ©es Â© 2025`."""
        with tempfile.TemporaryDirectory() as tmp:
            path = written(tmp, "ro-crate-metadata.json", {
                "@context": "https://w3id.org/ro/crate/1.1/context",
                "@graph": [{"@id": "./", "@type": "Dataset",
                            "name": "Données © 2025", "keywords": ["café"]}]})
            parser = ROCrateParser(path)
        self.assertEqual(parser.get_property("name"), "Données © 2025")
        self.assertEqual(parser.get_property("keywords"), ["café"])

    def test_each_fairscape_cli_command_reports_the_refusal_and_exits_1(self):
        """Each reports it as it reports any other error: one `✗ Error:`
        line on stderr, exit 1, no traceback, nothing on stdout and no file
        written. `merge` and `rank` read a UTF-8 crate first."""
        from src.fairscape_integration.cli import cli

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            commands = {
                "parse": ["parse", str(AI_READI)],
                "parse --verbose": ["parse", str(AI_READI), "--verbose"],
                "merge": ["merge", str(VOICE), str(AI_READI), "-o",
                          str(out / "merged.yaml"), "-m", str(MAPPING), "--report"],
                "rank": ["rank", str(VOICE), str(AI_READI), "-m", str(MAPPING)],
                "transform": ["transform", str(AI_READI), "-o", str(out / "d4d.yaml"),
                              "-m", str(MAPPING), "--report"],
            }
            for name, args in commands.items():
                with self.subTest(command=name):
                    result = cli_runner().invoke(cli, args)
                    self.assertEqual(result.exit_code, 1)
                    self.assertIsInstance(result.exception, SystemExit)
                    self.assertEqual(result.stdout, "")
                    self.assertEqual(result.stderr,
                                     f"✗ Error: {refusal(AI_READI)}\n")
            self.assertEqual(list(out.iterdir()), [])


class TestGraphWrittenAsOneObject(unittest.TestCase):
    """#4187: JSON-LD lets `@graph` be one node object as well as an array
    of them, and VOICE's provenance graph writes it that way. The parser and
    `fairscape-cli info` iterated it as an array, walked the object's keys,
    and ended with `'str' object has no attribute 'get'`. Each reads it as
    the one entity it is, as JSON-LD processing does."""

    #: One node object: a dataset that is the root, with a nested author
    NODE = {"@id": "./", "@type": "Dataset", "name": "One entity",
            "description": "A crate whose @graph is one node object",
            "author": [{"@id": "#a", "name": "An Author"}]}

    def test_the_tracked_provenance_graph_is_one_entity(self):
        node = json.loads(PROV_GRAPH.read_text(encoding="utf-8"))["@graph"]
        self.assertIsInstance(node, dict)              # the case, as tracked
        parser = ROCrateParser(PROV_GRAPH)
        self.assertEqual(parser.graph, [node])
        self.assertEqual(parser.get_root_dataset(), node)
        self.assertEqual(parser.get_entity_by_id(node["@id"]), node)
        self.assertEqual(parser.get_entities_by_type("prov:Entity"), [node])
        self.assertEqual(parser.get_property("name"), "ppgs.parquet")

    def test_one_node_object_parses_as_the_array_that_holds_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = "https://w3id.org/ro/crate/1.1/context"
            one = ROCrateParser(written(tmp, "object.json",
                                        {"@context": context, "@graph": self.NODE}))
            listed = ROCrateParser(written(tmp, "array.json",
                                           {"@context": context, "@graph": [self.NODE]}))
        self.assertEqual(one.graph, [self.NODE])
        for name in ("context", "graph", "root_dataset", "all_properties"):
            with self.subTest(attribute=name):
                self.assertEqual(getattr(one, name), getattr(listed, name))
        self.assertEqual(one.get_property("author[0].name"), "An Author")

    def test_only_an_object_is_put_in_a_list(self):
        self.assertEqual(graph_entities(self.NODE), [self.NODE])
        # Anything else is returned as it is, the same object
        for other in ([self.NODE], [], None, 5, "./"):
            with self.subTest(graph=other):
                self.assertIs(graph_entities(other), other)

    def test_fairscape_cli_parse_and_info_read_it_as_one_entity(self):
        """Both exit 0 and count one entity, on the tracked file and on a
        synthetic one. On the synthetic one, whose entity is the root `./`,
        `info` shows the root's fields as it does from an array."""
        from src.fairscape_integration.cli import cli

        result = cli_runner().invoke(cli, ["parse", str(PROV_GRAPH)])
        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("  @id: ark:59853/b2ai-voice-dataset-feature-ppgs\n"
                      "  @type: ['prov:Entity', 'https://w3id.org/EVI#Dataset']\n"
                      "  name: ppgs.parquet\n", result.stdout)
        self.assertIn("Total Entities: 1\n", result.stdout)

        result = cli_runner().invoke(cli, ["info", str(PROV_GRAPH)])
        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout,
                         f"File: {PROV_GRAPH}\nType: RO-Crate JSON-LD\n"
                         f"Size: {PROV_GRAPH.stat().st_size:,} bytes\n\n"
                         "RO-Crate Metadata:\n  @graph entities: 1\n")

        with tempfile.TemporaryDirectory() as tmp:
            path = written(tmp, "one-node.json", {"@graph": self.NODE})
            result = cli_runner().invoke(cli, ["info", str(path)])
            size = path.stat().st_size
        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertEqual(result.stdout,
                         f"File: {path}\nType: RO-Crate JSON-LD\n"
                         f"Size: {size:,} bytes\n\n"
                         "RO-Crate Metadata:\n  @graph entities: 1\n"
                         "  name: One entity\n"
                         "  description: A crate whose @graph is one node object\n")


if __name__ == '__main__':
    unittest.main()
