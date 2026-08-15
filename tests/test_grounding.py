"""External identifiers checked against the bundle they were read from (#547).

VOICE rep1 carries RORs that appear nowhere in its bundle. Every one is
correct: `ror.org/032db5x82` really is the University of South Florida, whose
name appears in the bundle 16 times. The run learned the institution from the
evidence and the identifier from memory.

That is the hardest form of fabrication to catch, because checking the *value*
cannot detect it. `linkml-validate` accepts any well-formed `uriorcurie` and
`d4d runs identifiers` treats a resolvable IRI as the best possible outcome.
Only checking the source can.
"""

import unittest
from pathlib import Path

import yaml

from data_sheets_schema.grounding import (
    authority,
    check_record,
    ground,
    person_fragment_on_org,
)

SLOTS = {"id", "affiliations", "creators", "publisher"}


class AuthorityTest(unittest.TestCase):
    """The bare form, so one identifier written three ways is one identifier."""

    def test_the_same_ror_in_three_notations(self):
        for value in ("https://ror.org/032db5x82", "ror.org/032db5x82",
                      "ROR:032db5x82"):
            with self.subTest(value=value):
                self.assertEqual(authority(value), ("ROR", "032db5x82"))

    def test_orcid_and_doi(self):
        self.assertEqual(authority("ORCID:0000-0002-1825-0097"),
                         ("ORCID", "0000-0002-1825-0097"))
        self.assertEqual(authority("https://doi.org/10.60775/fairhub.3"),
                         ("doi", "10.60775/fairhub.3"))

    def test_a_local_identifier_has_no_external_authority(self):
        """Nothing to check it against; `identifiers.classify` covers these."""
        for value in ("urn:d4d:voice:creator:1", "b2ai-voice.org", "x"):
            self.assertIsNone(authority(value))


class GroundTest(unittest.TestCase):

    BUNDLE = ("the dataset is published at https://doi.org/10.60775/fairhub.3 "
              "by an author with orcid 0000-0002-1825-0097, affiliated with "
              "ror.org/0153tk833.").lower()

    def test_present_in_the_bundle(self):
        self.assertEqual(ground("ROR:0153tk833", self.BUNDLE)[2], "grounded")

    def test_absent_from_the_bundle(self):
        """The University of South Florida's real ROR, and not in this text."""
        self.assertEqual(ground("ROR:032db5x82", self.BUNDLE)[2], "absent")

    def test_a_fragment_on_a_bundle_identifier_is_minted_not_absent(self):
        """`doi:10.60775/fairhub.3#split-train` — attested base, our fragment.

        Kept separate deliberately. Collapsing it into `absent` made a narrow
        defect look systematic: AI_READI rep1 has 17 of these and 0 absent.
        """
        self.assertEqual(ground("doi:10.60775/fairhub.3#split-train",
                                self.BUNDLE)[2], "minted_fragment")

    def test_a_fragment_on_an_absent_base_is_still_absent(self):
        self.assertEqual(ground("doi:10.9999/nothing#x", self.BUNDLE)[2],
                         "absent")

    def test_notation_does_not_decide_grounding(self):
        """The bundle writes a URL; the record, since the CURIE rule, a CURIE."""
        self.assertEqual(ground("doi:10.60775/fairhub.3", self.BUNDLE)[2],
                         "grounded")


class OrgFragmentTest(unittest.TestCase):
    """A ROR names an organisation, so a person fragment on one is wrong."""

    def test_person_fragment_on_a_ror(self):
        self.assertTrue(person_fragment_on_org("ROR:02r109517#rameau"))

    def test_a_plain_ror_is_fine(self):
        self.assertFalse(person_fragment_on_org("ROR:02r109517"))

    def test_a_fragment_on_a_doi_is_fine(self):
        """`#split-train` on a dataset DOI names a part of that dataset."""
        self.assertFalse(person_fragment_on_org(
            "doi:10.60775/fairhub.3#split-train"))


class RecordTest(unittest.TestCase):

    def test_distinct_and_occurrence_counts_are_both_reported(self):
        """One bad identifier in twenty slots is one fact and twenty slots."""
        record = {"id": "ROR:032db5x82",
                  "creators": [{"id": "ROR:032db5x82"}, {"id": "ROR:032db5x82"}]}
        out = check_record(record, "nothing here", SLOTS)
        self.assertEqual(out["counts"]["absent"], 3)
        self.assertEqual(out["distinct"]["absent"], 1)

    def test_counts_and_findings(self):
        record = {"id": "ROR:0153tk833",
                  "creators": [{"id": "ROR:032db5x82"},
                               {"id": "doi:10.60775/fairhub.3#a"}]}
        bundle = "ror.org/0153tk833 and 10.60775/fairhub.3"
        out = check_record(record, bundle, SLOTS)
        self.assertEqual(out["counts"],
                         {"grounded": 1, "minted_fragment": 1, "absent": 1})
        self.assertEqual([f["identifier"] for f in out["findings"]],
                         ["032db5x82"])


class CorpusTest(unittest.TestCase):
    """The two records the check finds, pinned against the arm."""

    BASE = Path("data/d4d_concatenated")

    def _distinct(self, project, rep):
        from data_sheets_schema.grounding import ground, iter_external
        from data_sheets_schema.identifiers import uriorcurie_slots
        label = f"2026-08-13_claude-opus-5-api-generic-v4_rep{rep}"
        core = self.BASE / "claudecode_agent_core" / label / f"{project}_d4d_core.yaml"
        full = self.BASE / "claudecode_agent" / label / f"{project}_d4d.yaml"
        bundle = Path(f"data/preprocessed/concatenated/{project}_preprocessed.txt")
        if not (core.exists() and bundle.exists()):
            self.skipTest("v4 arm not present in this checkout")
        text = bundle.read_text(encoding="utf-8", errors="replace").lower()
        slots = uriorcurie_slots()
        seen = {}
        for path in (full, core):
            if not path.exists():
                continue
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for _p, auth, bare in iter_external(doc, slots):
                seen[(auth, bare)] = ground(f"{auth}:{bare}", text)[2]
        return seen

    def test_voice_rep1_supplied_rors_its_bundle_never_stated(self):
        seen = self._distinct("VOICE", 1)
        absent = [b for (a, b), s in seen.items() if s == "absent"]
        # #547's figures exactly: 5 grounded, 0 minted, 19 absent.
        self.assertEqual(len(absent), 19)
        self.assertEqual(len([1 for s in seen.values() if s == "grounded"]), 5)
        self.assertEqual(len([1 for s in seen.values()
                              if s == "minted_fragment"]), 0)

    def test_cm4ai_rep3_has_the_same_defect(self):
        """#547 measured one replicate per project and did not see this one.

        The CM4AI bundle contains exactly one ROR (`0153tk833`); rep3's records
        carry ten others.
        """
        seen = self._distinct("CM4AI", 3)
        absent = sorted(b for (a, b), s in seen.items() if s == "absent")
        self.assertEqual(len(absent), 10)

    def test_voice_rep1_hangs_people_off_an_institutional_ror(self):
        """`ROR:02r109517#rameau` asserts "Weill Cornell Medicine, fragment
        rameau" and is used to identify a person. #547 lists six examples;
        there are seven distinct identifiers, each appearing in both records.

        Counted distinctly on purpose. The occurrence count is 14, and
        reporting that as "14 organisational fragments" would double every
        figure — which the first version of this test did.
        """
        from data_sheets_schema.grounding import check_run
        from data_sheets_schema.identifiers import uriorcurie_slots
        label = "2026-08-13_claude-opus-5-api-generic-v4_rep1"
        core = self.BASE / "claudecode_agent_core" / label / "VOICE_d4d_core.yaml"
        if not core.exists():
            self.skipTest("v4 arm not present in this checkout")
        out = check_run(
            self.BASE / "claudecode_agent" / label / "VOICE_d4d.yaml", core,
            Path("data/preprocessed/concatenated/VOICE_preprocessed.txt"),
            uriorcurie_slots())
        frags = {f["identifier"] for f in out["findings"]
                 if f["kind"] == "fragment_on_org_identifier"}
        self.assertEqual(len(frags), 7)
        occurrences = sum(1 for f in out["findings"]
                          if f["kind"] == "fragment_on_org_identifier")
        self.assertEqual(occurrences, 14, "seven identifiers, in both records")

    def test_chorus_carries_no_external_identifiers_at_all(self):
        self.assertEqual(self._distinct("CHORUS", 1), {})


if __name__ == "__main__":
    unittest.main()
