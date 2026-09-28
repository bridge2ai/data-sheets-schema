"""Tests for the our-mapping crate → D4D arm."""

import copy
import tempfile
import unittest
from pathlib import Path

import yaml
from linkml_runtime import SchemaView

from data_sheets_schema.rocrate_map import (
    FULL_SCHEMA,
    MapResult,
    _normalize_datetime,
    build_placement,
    crate_root,
    doi_for_slot,
    load_mapping,
    map_crate,
    resolve_path,
    validate,
    verdict_basis,
    write_provenance,
)
from data_sheets_schema.schema_cache import sha256_of

GRAPH = [
    {"@id": "ro-crate-metadata.json", "@type": "CreativeWork"},
    {"@id": "ark:59853/thing", "@type": ["https://w3id.org/EVI#Dataset",
                                         "https://w3id.org/EVI#ROCrate"],
     "name": "Test Crate", "description": "A crate for tests",
     "identifier": "https://doi.org/10.5555/Test",
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
        """A DOI id is written as the `doi:` CURIE, the form #974's write-time
        normaliser gives the generated arms (#2916)."""
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        self.assertEqual(res.record["id"], "doi:10.5555/Test")

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


def _with_identifier(identifier):
    graph = copy.deepcopy(GRAPH)
    graph[1]["identifier"] = identifier
    return graph


class TestDoi(unittest.TestCase):
    """#2916. The `doi` pattern is anchored to the bare DOI (#646) and crates
    carry the resolver URL; copying it through failed the schema while the
    provenance report still said PASS."""

    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.rows = load_mapping()

    def doi_field(self, res):
        return next(f for f in res.fields if f.d4d_path == "Dataset.doi")

    def test_a_resolver_url_is_written_as_the_bare_doi_in_its_case(self):
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        self.assertEqual(res.record["doi"], "10.5555/Test")
        self.assertEqual(self.doi_field(res).status, "filled")

    def test_a_doi_curie_identifier_maps_to_the_same_record(self):
        res = map_crate(_with_identifier("doi:10.5555/Test"),
                        self.rows, self.sv, "TEST")
        self.assertEqual(res.record["doi"], "10.5555/Test")
        self.assertEqual(res.record["id"], "doi:10.5555/Test")

    def test_a_non_doi_identifier_writes_no_doi_and_says_why(self):
        res = map_crate(_with_identifier("ark:59853/other"),
                        self.rows, self.sv, "TEST")
        self.assertNotIn("doi", res.record)
        field = self.doi_field(res)
        self.assertEqual(field.status, "empty")
        self.assertIn("not a DOI", field.detail)
        # The id is not a DOI either, so it stays as the crate wrote it.
        self.assertEqual(res.record["id"], "ark:59853/other")

    def test_a_list_gives_up_its_one_doi(self):
        value, note = doi_for_slot(["ark:59853/other",
                                    "https://doi.org/10.5555/Test",
                                    "doi:10.5555/Test"])
        self.assertEqual(value, "10.5555/Test")
        self.assertIn("one DOI among 3", note)

    def test_two_different_dois_give_none_and_neither_is_chosen(self):
        res = map_crate(_with_identifier(["https://doi.org/10.5555/Test",
                                          "https://doi.org/10.5555/Other"]),
                        self.rows, self.sv, "TEST")
        self.assertNotIn("doi", res.record)
        field = self.doi_field(res)
        self.assertEqual(field.status, "empty")
        self.assertIn("2 distinct DOIs", field.detail)

    def test_a_bare_doi_passes_through_with_no_note(self):
        self.assertEqual(doi_for_slot("10.5555/Test"), ("10.5555/Test", ""))

    def test_the_mapped_record_validates_against_the_schema(self):
        """The check test_map.py never made: the mapper's output is judged by
        the schema it claims to target, not only by its shape."""
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapped_d4d.yaml"
            path.write_text(yaml.safe_dump(res.record, sort_keys=False,
                                           allow_unicode=True), encoding="utf-8")
            self.assertEqual(validate(path), "PASS")


class TestVerdictBasis(unittest.TestCase):
    """#2916. A verdict names the schema it was reached against, so a later
    schema change leaves a PASS that says which schema it was about."""

    def test_the_basis_names_version_hash_and_date(self):
        basis = verdict_basis(FULL_SCHEMA, on="2026-09-28")
        self.assertRegex(basis, r"^schema \d+\.\d+\.\d+ / ")
        self.assertIn(f"sha256 {sha256_of(FULL_SCHEMA)}", basis)
        self.assertIn("/ 2026-09-28 ", basis)
        self.assertIn(str(FULL_SCHEMA), basis)

    def test_the_provenance_report_writes_it_beside_the_verdict(self):
        res = MapResult(project="TEST", validation="PASS")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapping_provenance.md"
            write_provenance(res, path, Path("crate/ro-crate-metadata.json"))
            line = next(l for l in path.read_text(encoding="utf-8").splitlines()
                        if l.startswith("- Validation:"))
        self.assertTrue(line.startswith("- Validation: **PASS** — schema "), line)
        self.assertIn(f"sha256 {sha256_of(FULL_SCHEMA)}", line)
        self.assertRegex(line, r" / \d{4}-\d{2}-\d{2} ")


if __name__ == "__main__":
    unittest.main()
