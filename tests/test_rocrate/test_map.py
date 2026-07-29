"""Tests for the our-mapping crate → D4D arm."""

import unittest

from linkml_runtime import SchemaView

from data_sheets_schema.rocrate_map import (
    FULL_SCHEMA,
    _normalize_datetime,
    build_placement,
    crate_root,
    load_mapping,
    map_crate,
    resolve_path,
)

GRAPH = [
    {"@id": "ro-crate-metadata.json", "@type": "CreativeWork"},
    {"@id": "ark:59853/thing", "@type": ["https://w3id.org/EVI#Dataset",
                                         "https://w3id.org/EVI#ROCrate"],
     "name": "Test Crate", "description": "A crate for tests",
     "identifier": "https://doi.org/10.5555/test",
     "author": ["Ada Lovelace", "Alan Turing"],
     "rai:dataBiases": "Sampling bias: clinic-recruited cohort.",
     "additionalProperty": [{"name": "Completeness", "value": "Interim"}],
     "keywords": ["voice", "health"]},
]


class TestPathResolution(unittest.TestCase):
    def setUp(self):
        self.root = crate_root(GRAPH)

    def test_crate_root_prefers_the_rocrate_entity(self):
        self.assertEqual(self.root["@id"], "ark:59853/thing")

    def test_type_match_tolerates_evi_prefixed_types(self):
        value, _ = resolve_path("@graph[?@type='Dataset']['name']", GRAPH, self.root)
        self.assertEqual(value, "Test Crate")

    def test_bare_property_resolves_on_root(self):
        value, _ = resolve_path("rai:dataBiases", GRAPH, self.root)
        self.assertEqual(value, "Sampling bias: clinic-recruited cohort.")

    def test_nested_name_selector(self):
        value, _ = resolve_path(
            "@graph[?@type='Dataset']['additionalProperty'][?name='Completeness']['value']",
            GRAPH, self.root)
        self.assertEqual(value, "Interim")

    def test_non_paths_are_reported_not_guessed(self):
        for expr in ("N/A", "encodingFormat MIME parameter", "d4d:samplingStrategy"):
            with self.subTest(expr=expr):
                value, note = resolve_path(expr, GRAPH, self.root)
                self.assertIsNone(value)
                self.assertEqual(note, "not a crate path")

    def test_absent_property_reports_why(self):
        value, note = resolve_path("@graph[?@type='Dataset']['nope']", GRAPH, self.root)
        self.assertIsNone(value)
        self.assertIn("nope", note)


class TestDateNormalization(unittest.TestCase):
    def test_iso_date_becomes_datetime(self):
        value, note = _normalize_datetime("2026-04-03")
        self.assertEqual(value, "2026-04-03T00:00:00Z")
        self.assertTrue(note)

    def test_unambiguous_us_order_resolves(self):
        value, _ = _normalize_datetime("12/16/2025")
        self.assertEqual(value, "2025-12-16T00:00:00Z")

    def test_unambiguous_day_first_resolves(self):
        value, _ = _normalize_datetime("16/12/2025")
        self.assertEqual(value, "2025-12-16T00:00:00Z")

    def test_ambiguous_date_is_dropped_not_guessed(self):
        value, note = _normalize_datetime("03/04/2026")
        self.assertIsNone(value)
        self.assertIn("ambiguous", note)


class TestMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.rows = load_mapping()

    def test_the_shipped_table_loads(self):
        self.assertGreater(len(self.rows), 100)
        self.assertTrue(all("D4D_Full_Path" in r for r in self.rows))

    def test_placement_is_schema_derived(self):
        placement = build_placement(self.sv)
        self.assertEqual(placement.get("EthicalReview"), "ethical_reviews")
        self.assertEqual(placement.get("PreprocessingStrategy"),
                         "preprocessing_strategies")

    def test_every_row_is_accounted_for(self):
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        # id is appended separately, so field count is rows + at most one
        self.assertGreaterEqual(len(res.fields), len(self.rows))
        self.assertTrue(all(f.status in
                            ("filled", "empty", "unresolvable", "unplaceable")
                            for f in res.fields))

    def test_record_takes_its_id_from_the_crate(self):
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        self.assertEqual(res.record["id"], "https://doi.org/10.5555/test")

    def test_string_authors_become_creator_objects(self):
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        creators = res.record.get("creators")
        self.assertTrue(creators)
        self.assertEqual(creators[0]["name"], "Ada Lovelace")

    def test_nothing_is_filled_without_a_resolving_path(self):
        """An empty crate must yield no filled fields beyond none at all."""
        res = map_crate([{"@id": "x", "@type": "CreativeWork"}],
                        self.rows, self.sv, "TEST")
        self.assertEqual([f for f in res.fields if f.status == "filled"], [])
        self.assertEqual(res.record, {})

    def test_unplaceable_rows_state_a_reason(self):
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        unplaceable = [f for f in res.fields if f.status == "unplaceable"]
        self.assertTrue(unplaceable)
        self.assertTrue(all(f.detail for f in unplaceable))


if __name__ == "__main__":
    unittest.main()
