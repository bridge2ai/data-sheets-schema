"""#402 — the trap that passes validation.

`uriorcurie` declares no `pattern`, so LinkML renders it as
`{"type": ["string","null"]}` and every string is legal. `funder_nih` validates
exactly as cleanly as `https://ror.org/01cwqze88`, which is why four
incompatible conventions coexisted across one label with no warning from
anything.

`trap-inventory` cannot find this: it mines validation *failures*, and these
values pass. That is the whole point — the defect that passes is the dangerous
one, because nothing in the pipeline is looking at it.
"""

import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema import identifiers as ident

PREFIXES = {"d4d", "schema", "dcterms"}


class TestClassify(unittest.TestCase):
    def test_absolute_iris(self):
        for v in ("https://ror.org/01cwqze88",
                  "http://example.org/x",
                  "https://doi.org/10.13026/h995-bt35"):
            with self.subTest(v=v):
                self.assertEqual(ident.URI, ident.classify(v, PREFIXES))

    def test_a_curie_on_a_declared_prefix(self):
        self.assertEqual(ident.CURIE_DECLARED,
                         ident.classify("d4d:VOICE-funding-nih", PREFIXES))

    def test_a_curie_on_an_undeclared_prefix_is_not_the_same_thing(self):
        """Well-formed and still unresolvable. Reported separately, because the
        remedy differs: declare the prefix, versus rewrite the value."""
        self.assertEqual(ident.CURIE_UNDECLARED,
                         ident.classify("nosuch:thing", PREFIXES))

    def test_bare_tokens(self):
        for v in ("funder_nih", "purpose_workforce_and_education",
                  "file_demographics", "x"):
            with self.subTest(v=v):
                self.assertEqual(ident.BARE, ident.classify(v, PREFIXES))

    def test_a_bare_token_is_worse_than_an_absent_id(self):
        """It looks like an identifier and is scoped to nothing, so two records
        emitting `funder_nih` collide by accident rather than agree by
        reference. Both classify as bare; the point is that neither resolves."""
        self.assertIn(ident.classify("funder_nih", PREFIXES),
                      ident.UNRESOLVABLE)
        self.assertNotIn(ident.classify("https://ror.org/x", PREFIXES),
                         ident.UNRESOLVABLE)

    def test_surrounding_whitespace_does_not_change_the_verdict(self):
        self.assertEqual(ident.URI,
                         ident.classify("  https://ror.org/x  ", PREFIXES))

    def test_a_prefix_with_no_reference_identifies_nothing(self):
        """`d4d:` expands to the namespace itself. Accepting it would pass a
        value that names no entity."""
        self.assertEqual(ident.BARE, ident.classify("d4d:", PREFIXES))

    def test_the_values_that_prompted_this(self):
        """Real values from the corpus, in slots ranged `uriorcurie`."""
        for v in ("%", "years", "PhysioNet", "10.60775/fairhub.3",
                  "Type 2 diabetes mellitus and associated health outcomes"):
            with self.subTest(v=v):
                self.assertIn(ident.classify(v, PREFIXES), ident.UNRESOLVABLE)


class TestWalkIdentifiers(unittest.TestCase):
    SLOTS = {"id", "publisher", "unit", "latest_version_doi"}

    def _paths(self, doc):
        return [p for p, _, _ in ident.walk_identifiers(doc, self.SLOTS)]

    def test_nested_ids_are_found_at_every_depth(self):
        doc = {"id": "top",
               "funders": [{"id": "funder_nih"}],
               "file_collections": [
                   {"id": "fc", "resources": [{"id": "file_a"},
                                              {"id": "file_b"}]}]}
        found = set(self._paths(doc))
        self.assertIn("$.id", found)
        self.assertIn("$.funders[].id", found)
        self.assertIn("$.file_collections[].resources[].id", found)

    def test_slots_other_than_id_are_audited(self):
        """`id` is one of six uriorcurie slots and not the worst: `unit` holds
        `%`, `publisher` holds bare names. Auditing only `id` would report a
        clean `unit` that has never held an identifier."""
        doc = {"unit": "%", "publisher": "PhysioNet",
               "latest_version_doi": "10.60775/fairhub.3"}
        found = {slot for _, slot, _ in ident.walk_identifiers(doc, self.SLOTS)}
        self.assertEqual({"unit", "publisher", "latest_version_doi"}, found)

    def test_a_multivalued_identifier_slot_yields_each_value(self):
        doc = {"publisher": ["PhysioNet", "https://ror.org/x"]}
        vals = [v for _, _, v in ident.walk_identifiers(doc, self.SLOTS)]
        self.assertEqual(["PhysioNet", "https://ror.org/x"], vals)

    def test_list_positions_collapse_so_one_slot_is_one_finding(self):
        """12 bad ids in one list is one defect, not twelve — the same
        normalisation `trap_inventory` applies, for the same reason."""
        doc = {"purposes": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}
        self.assertEqual(["$.purposes[].id"] * 3, self._paths(doc))

    def test_a_non_string_or_empty_id_is_not_reported_as_an_identifier(self):
        doc = {"id": None, "a": {"id": ""}, "b": {"id": 7}}
        self.assertEqual([], self._paths(doc))

    def test_a_slot_not_ranged_uriorcurie_is_left_alone(self):
        doc = {"description": "a sentence that is not an identifier"}
        self.assertEqual([], self._paths(doc))


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        # A real LinkML schema, not a prefixes-only stub: `audit` derives the
        # slot set from it, so the fixture has to be loadable and has to
        # declare a slot ranged `uriorcurie` other than `id` — otherwise the
        # tests would pass against a scan that only ever looked at `id`.
        self.schema = self.root / "schema.yaml"
        self.schema.write_text(yaml.safe_dump({
            "id": "https://example.org/test",
            "name": "test_schema",
            "prefixes": {p: f"https://example.org/{p}/" for p in PREFIXES},
            "default_range": "string",
            "slots": {
                "id": {"range": "uriorcurie", "identifier": True},
                "publisher": {"range": "uriorcurie"},
                "funders": {"range": "Thing", "multivalued": True,
                            "inlined_as_list": True},
                "x": {"range": "Thing", "multivalued": True,
                      "inlined_as_list": True},
                "description": {"range": "string"},
            },
            "classes": {
                "Thing": {"slots": ["id", "publisher", "description"]},
                "Dataset": {"slots": ["id", "publisher", "funders", "x",
                                      "description"]},
            },
        }))

    def _record(self, rel: str, doc: dict):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(doc))
        return p

    def test_a_clean_record_reports_nothing(self):
        self._record("m/lbl/P_d4d.yaml",
                     {"id": "https://doi.org/10.1/x",
                      "funders": [{"id": "d4d:nih"}]})
        rep = ident.audit(self.root, self.schema)
        self.assertEqual(0, rep["unresolvable"])
        self.assertEqual(0.0, rep["unresolvable_share"])

    def test_offenders_are_named_with_their_slot_and_value(self):
        self._record("m/lbl/P_d4d.yaml",
                     {"id": "https://doi.org/10.1/x",
                      "funders": [{"id": "funder_nih"}]})
        rep = ident.audit(self.root, self.schema)
        self.assertEqual(1, rep["unresolvable"])
        off = rep["records"][0]["offenders"]
        self.assertEqual("$.funders[].id", off[0]["slot_path"])
        self.assertEqual("funder_nih", off[0]["value"])

    def test_the_dominant_convention_is_reported(self):
        """A record that is 107/108 CURIE has a convention and one slip; one
        split down the middle has none, and they want different remedies."""
        self._record("m/lbl/P_d4d.yaml",
                     {"id": "d4d:a",
                      "x": [{"id": "d4d:b"}, {"id": "d4d:c"},
                            {"id": "oops"}]})
        rep = ident.audit(self.root, self.schema)
        self.assertEqual(ident.CURIE_DECLARED, rep["records"][0]["dominant"])

    def test_the_slot_set_is_derived_from_the_schema_not_hardcoded(self):
        rep = ident.audit(self.root, self.schema)
        self.assertIn("publisher", rep["slots_audited"])
        self.assertIn("id", rep["slots_audited"])

    def test_a_bad_value_in_a_non_id_slot_is_caught(self):
        """The version that only walked `id` reported this record clean, while
        `publisher: PhysioNet` sat in a slot ranged `uriorcurie`."""
        self._record("m/lbl/P_d4d.yaml",
                     {"id": "https://doi.org/10.1/x",
                      "publisher": "PhysioNet"})
        rep = ident.audit(self.root, self.schema)
        self.assertEqual(1, rep["unresolvable"])
        self.assertEqual({"publisher": 1}, rep["unresolvable_by_slot"])

    def test_offenders_are_grouped_by_slot(self):
        self._record("m/lbl/P_d4d.yaml",
                     {"id": "bare_one",
                      "publisher": "PhysioNet",
                      "funders": [{"id": "bare_two"}]})
        rep = ident.audit(self.root, self.schema)
        self.assertEqual({"id": 2, "publisher": 1},
                         rep["unresolvable_by_slot"])

    def test_core_records_are_scanned_too(self):
        self._record("m_core/lbl/P_d4d_core.yaml", {"id": "bare"})
        rep = ident.audit(self.root, self.schema)
        self.assertEqual(1, rep["records_scanned"])
        self.assertEqual(1, rep["unresolvable"])

    def test_attic_is_excluded_by_default(self):
        """Archived records were set aside because their provenance could not
        be established; counting them inflates a live-corpus figure."""
        self._record("ATTIC/m/lbl/P_d4d.yaml", {"id": "bare"})
        self.assertEqual(0, ident.audit(self.root, self.schema)["records_scanned"])
        self.assertEqual(1, ident.audit(self.root, self.schema,
                                        include_archived=True)["records_scanned"])

    def test_an_unparseable_record_is_reported_not_skipped(self):
        p = self.root / "m/lbl/P_d4d.yaml"
        p.parent.mkdir(parents=True)
        p.write_text("{{ not yaml")
        rep = ident.audit(self.root, self.schema)
        self.assertEqual(1, len(rep["unreadable"]))


class TestSummarizeMatchesItsRecords(unittest.TestCase):
    """A filtered record list beside corpus-wide totals states two scopes in
    one breath and reads as one. The CLI recomputes; this pins that."""

    def test_totals_describe_exactly_the_records_given(self):
        recs = [
            {"path": "a", "total": 2, "counts": {ident.URI: 2,
                                                 ident.CURIE_DECLARED: 0,
                                                 ident.CURIE_UNDECLARED: 0,
                                                 ident.BARE: 0},
             "offenders": [], "dominant": ident.URI},
            {"path": "b", "total": 2, "counts": {ident.URI: 0,
                                                 ident.CURIE_DECLARED: 0,
                                                 ident.CURIE_UNDECLARED: 0,
                                                 ident.BARE: 2},
             "offenders": [{"slot_path": "$.id", "value": "x",
                            "kind": ident.BARE}] * 2,
             "dominant": ident.BARE},
        ]
        both = ident.summarize(recs, 33)
        self.assertEqual(4, both["identifiers"])
        self.assertEqual(2, both["unresolvable"])
        self.assertEqual(0.5, both["unresolvable_share"])

        just_a = ident.summarize(recs[:1], 33)
        self.assertEqual(2, just_a["identifiers"])
        self.assertEqual(0, just_a["unresolvable"])
        self.assertEqual(1, just_a["records_scanned"])

    def test_an_empty_selection_does_not_divide_by_zero(self):
        empty = ident.summarize([], 33)
        self.assertEqual(0, empty["identifiers"])
        self.assertEqual(0.0, empty["unresolvable_share"])


if __name__ == "__main__":
    unittest.main()
