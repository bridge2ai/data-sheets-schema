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


class TestWalkIds(unittest.TestCase):
    def test_nested_ids_are_found_at_every_depth(self):
        doc = {"id": "top",
               "funders": [{"id": "funder_nih"}],
               "file_collections": [
                   {"id": "fc", "resources": [{"id": "file_a"},
                                              {"id": "file_b"}]}]}
        found = dict(ident.walk_ids(doc))
        self.assertIn("$.id", found)
        self.assertIn("$.funders[].id", found)
        self.assertIn("$.file_collections[].resources[].id", found)

    def test_list_positions_collapse_so_one_slot_is_one_finding(self):
        """12 bad ids in one list is one defect, not twelve — the same
        normalisation `trap_inventory` applies, for the same reason."""
        doc = {"purposes": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}
        paths = [p for p, _ in ident.walk_ids(doc)]
        self.assertEqual(["$.purposes[].id"] * 3, paths)

    def test_a_non_string_or_empty_id_is_not_reported_as_an_identifier(self):
        doc = {"id": None, "a": {"id": ""}, "b": {"id": 7}}
        self.assertEqual([], list(ident.walk_ids(doc)))


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.schema = self.root / "schema.yaml"
        self.schema.write_text(yaml.safe_dump(
            {"prefixes": {p: f"https://example.org/{p}/" for p in PREFIXES}}))

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
