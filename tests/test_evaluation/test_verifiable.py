"""Values a record states, checked against the documents it was given (#165).

Every assertion here exists because the naive version of this check was wrong in
a way that would have been published as a fabrication. Four separate
classification bugs turned up while measuring the corpus, each inflating the
apparent error rate:

  1. `2025-01-17` vs "January 17, 2025" — a date in another format;
  2. `https://doi.org/10.x/y` normalised asymmetrically against the bundle;
  3. the same token counted as both a DOI and a URL;
  4. constructed identifiers in class-ranged slots demanded to appear in sources.

The corpus rate moved from 78%–97% to 90%–100% as they were fixed. A checker
whose false positives dominate is worse than none, because the real findings are
buried among them.
"""

import unittest
from pathlib import Path

from data_sheets_schema.verifiable import (
    Claim,
    RecordCheck,
    check_record,
    extract,
    identifier_slots,
    normalise,
    renderings,
)


class TestDateRenderings(unittest.TestCase):
    """A date in the source's format is not a fabrication."""

    def test_iso_date_matches_a_written_month(self):
        r = renderings("iso_date", "2025-01-17")
        self.assertIn("january 17, 2025", r)
        self.assertIn("17 january 2025", r)

    def test_month_precision_is_accepted(self):
        """Sources often give only 'June 2026' for a dated release."""
        self.assertIn("june 2026", renderings("iso_date", "2026-06-17"))

    def test_a_malformed_date_degrades_to_the_literal(self):
        self.assertEqual(renderings("iso_date", "not-a-date"), ["not-a-date"])

    def test_non_dates_have_a_single_rendering(self):
        self.assertEqual(len(renderings("doi", "10.1234/x")), 1)


class TestNormalisationIsSymmetric(unittest.TestCase):
    """The claim and the bundle must be reduced the same way."""

    def test_a_doi_url_and_a_bare_doi_agree(self):
        self.assertEqual(normalise("url", "https://doi.org/10.18130/V3/HIGT4C"),
                         normalise("doi", "10.18130/V3/HIGT4C"))

    def test_resolver_prefixes_are_stripped(self):
        for form in ("doi:10.1234/x", "https://doi.org/10.1234/x",
                     "https://dx.doi.org/10.1234/x", "10.1234/x"):
            with self.subTest(form=form):
                self.assertEqual(normalise("doi", form), "10.1234/x")

    def test_url_scheme_and_trailing_slash_do_not_matter(self):
        self.assertEqual(normalise("url", "https://Example.org/a/"),
                         normalise("url", "http://example.org/a"))

    def test_trailing_punctuation_is_stripped(self):
        self.assertEqual(normalise("doi", "10.1234/x,"), "10.1234/x")


class TestNoDoubleCounting(unittest.TestCase):
    """One fact must not be counted twice, once grounded and once not."""

    def test_a_doi_url_yields_one_claim(self):
        claims = list(extract({"citation": "https://doi.org/10.18130/V3/HIGT4C"},
                              skip_slots=set()))
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].kind, "doi")

    def test_distinct_tokens_still_yield_distinct_claims(self):
        claims = list(extract(
            {"a": "10.1234/x and https://example.org/p and 2025-01-17"},
            skip_slots=set()))
        self.assertEqual({c.kind for c in claims}, {"doi", "url", "iso_date"})


class TestConstructedIdentifiersAreExempt(unittest.TestCase):
    """A minted URI is not a claim about the world."""

    def test_identifier_and_class_ranged_slots_are_exempt(self):
        skip = identifier_slots()
        self.assertIn("id", skip)
        self.assertIn("principal_investigator", skip,
                      "a Person reference is minted, not asserted")

    def test_a_bare_string_in_a_class_ranged_slot_is_skipped(self):
        claims = list(extract(
            {"principal_investigator": "https://b2ai-voice.org/person/x"}))
        self.assertEqual(claims, [])

    def test_but_a_nested_object_is_still_checked(self):
        """Only the identifier is exempt; the fields inside it are assertions."""
        claims = list(extract(
            {"principal_investigator": {"id": "https://b2ai-voice.org/person/x",
                                        "page": "https://real.example/bio"}}))
        self.assertEqual([c.value for c in claims],
                         ["https://real.example/bio"])

    def test_a_list_of_nested_objects_is_checked(self):
        claims = list(extract({"creators": [{"page": "https://a.example/1"},
                                            {"page": "https://a.example/2"}]}))
        self.assertEqual(len(claims), 2)


class TestGrounding(unittest.TestCase):

    def test_a_value_present_in_the_bundle_is_grounded(self):
        r = check_record({"doi": "10.13026/249v-w155"},
                         "see 10.13026/249v-w155 for details", skip_slots=set())
        self.assertEqual(r.grounded, 1)
        self.assertEqual(r.ungrounded, [])

    def test_a_value_absent_from_the_bundle_is_not(self):
        r = check_record({"doi": "10.9999/invented"}, "unrelated text",
                         skip_slots=set())
        self.assertEqual(r.grounded, 0)
        self.assertEqual(len(r.ungrounded), 1)

    def test_a_date_in_the_sources_format_is_grounded(self):
        r = check_record({"issued": "2025-01-17"},
                         "Released January 17, 2025.", skip_slots=set())
        self.assertEqual(r.grounded, 1)


class TestTheDenominatorTrap(unittest.TestCase):
    """A record that states nothing must not rank top."""

    def test_an_empty_record_has_no_rate(self):
        r = check_record({}, "any bundle")
        self.assertEqual(r.stated, 0)
        self.assertIsNone(r.rate, "an empty record must not score 100%")

    def test_stated_is_reported_alongside_grounded(self):
        r = check_record({"doi": "10.1234/x"}, "10.1234/x", skip_slots=set())
        self.assertEqual((r.stated, r.grounded), (1, 1))

    def test_a_sparse_correct_record_does_not_beat_a_full_one_on_count(self):
        sparse = check_record({"doi": "10.1234/x"}, "10.1234/x", skip_slots=set())
        full = check_record({"doi": "10.1234/x", "a": "10.5678/y",
                             "b": "10.9012/z"},
                            "10.1234/x 10.5678/y 10.9012/z", skip_slots=set())
        self.assertEqual(sparse.rate, full.rate)
        self.assertGreater(full.stated, sparse.stated,
                           "the pair, not the ratio, separates them")


class TestAgainstTheCorpus(unittest.TestCase):

    def _check(self, project, rep):
        import yaml
        b = Path(f"data/preprocessed/concatenated/{project}_preprocessed.txt")
        f = Path(f"data/d4d_concatenated/claudecode_agent/"
                 f"2026-07-28_claude-opus-5-generic_rep{rep}/{project}_d4d.yaml")
        if not (b.exists() and f.exists()):
            self.skipTest("corpus not present")
        return check_record(yaml.safe_load(f.read_text()), b.read_text(),
                            project=project, label=f"rep{rep}")

    def test_dois_are_grounded_across_the_corpus(self):
        """No fabricated DOI was found in any record; a regression here is the
        clearest possible signal that generation has started inventing."""
        for project in ("AI_READI", "CM4AI", "VOICE"):
            with self.subTest(project=project):
                r = self._check(project, 1)
                stated, grounded = r.by_kind().get("doi", (0, 0))
                if stated:
                    self.assertEqual(grounded, stated)

    def test_the_known_voice_finding_is_still_detected(self):
        """VOICE rep2 states three release dates absent from its bundle in any
        format. This is the check's first real positive; if it stops firing,
        the checker has been broken rather than the record fixed."""
        r = self._check("VOICE", 2)
        missing = {c.value for c in r.ungrounded if c.kind == "iso_date"}
        self.assertTrue({"2025-08-18", "2025-12-16", "2025-12-17"} <= missing)

    def test_no_record_falls_below_the_measured_floor(self):
        """Guards against a normalisation regression reintroducing false
        positives: four such bugs moved the corpus from 78% to 90%."""
        for project in ("AI_READI", "CHORUS", "CM4AI", "VOICE"):
            for rep in (1, 2, 3):
                with self.subTest(project=project, rep=rep):
                    r = self._check(project, rep)
                    if r.stated:
                        self.assertGreaterEqual(r.rate, 0.85)


if __name__ == "__main__":
    unittest.main()
