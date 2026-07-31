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

    def test_month_precision_is_no_longer_accepted(self):
        """'June 2026' once grounded 2026-06-17 — and every other day in June,
        so a fabricated day was undetectable. Raised by review; the trade is
        that a source giving only month precision now reads as ungrounded,
        which is the safer direction for a check whose signal is absence."""
        self.assertNotIn("june 2026", renderings("iso_date", "2026-06-17"))

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
                        # 0.70, not 0.85. Boundary-aware matching removed ~1000
                        # false groundings and the corpus moved 87.3% -> 79.9%;
                        # a floor set against the inflated figure would fail on
                        # the honest one.
                        self.assertGreaterEqual(r.rate, 0.70)


if __name__ == "__main__":
    unittest.main()


class TestTokenBoundaries(unittest.TestCase):
    """A token must not match inside a longer one.

    Raised by an independent review. Substring search reported a fabricated
    value as grounded — the failure this module exists to catch, produced by the
    module itself. Removing it moved the corpus from 87.3% to 79.9%, so roughly a
    thousand "grounded" values were never located at all.
    """

    def _grounded(self, kind, value, bundle):
        from data_sheets_schema.verifiable import check_record
        slot = {"doi": "doi", "url": "page", "count": "counts",
                "accession": "accession", "iso_date": "issued"}[kind]
        return check_record({slot: value}, bundle, skip_slots=set()).grounded == 1

    def test_a_doi_does_not_match_a_longer_doi(self):
        self.assertFalse(self._grounded("doi", "10.1234/x", "see 10.1234/xyz"))
        self.assertTrue(self._grounded("doi", "10.1234/x", "see 10.1234/x."))

    def test_a_url_does_not_match_a_longer_path(self):
        self.assertFalse(self._grounded("url", "https://example.org/a",
                                        "https://example.org/abc"))
        self.assertTrue(self._grounded("url", "https://example.org/a",
                                       "visit https://example.org/a for more"))

    def test_a_number_does_not_match_a_longer_number(self):
        self.assertFalse(self._grounded("count", "1234", "value 12345"))
        self.assertFalse(self._grounded("count", "1234", "value 912345"))
        self.assertTrue(self._grounded("count", "1234", "value 1234 total"))

    def test_an_accession_does_not_match_a_longer_one(self):
        self.assertFalse(self._grounded("accession", "GSE123", "GSE1234"))
        self.assertTrue(self._grounded("accession", "GSE123", "see GSE123)"))


class TestThousandsSeparators(unittest.TestCase):
    """Sources group thousands; records do not.

    `61937` was reported invented while the VOICE bundle plainly said `61,937`.
    """

    def test_a_grouped_figure_in_the_source_grounds_a_bare_one(self):
        from data_sheets_schema.verifiable import check_record
        r = check_record({"counts": "61937"}, "a total of 61,937 recordings",
                         skip_slots=set())
        self.assertEqual(r.grounded, 1)

    def test_a_bare_figure_in_the_source_also_grounds(self):
        from data_sheets_schema.verifiable import check_record
        self.assertEqual(
            check_record({"counts": "61937"}, "61937 recordings",
                         skip_slots=set()).grounded, 1)

    def test_renderings_include_both_forms(self):
        from data_sheets_schema.verifiable import number_renderings
        self.assertIn("61937", number_renderings("61937"))
        self.assertIn("61,937", number_renderings("61937"))


class TestDateValidity(unittest.TestCase):
    """Three numbers are not a date."""

    def test_month_zero_does_not_wrap_to_december(self):
        """`MONTHS[m - 1]` with m == 0 indexed backwards, rendering
        `2025-00-17` as 'December 17, 2025' and grounding an impossible date."""
        from data_sheets_schema.verifiable import check_record, renderings
        self.assertEqual(renderings("iso_date", "2025-00-17"), ["2025-00-17"])
        self.assertEqual(
            check_record({"issued": "2025-00-17"}, "December 17, 2025",
                         skip_slots=set()).grounded, 0)

    def test_an_impossible_day_is_not_expanded(self):
        from data_sheets_schema.verifiable import renderings
        self.assertEqual(renderings("iso_date", "2025-02-30"), ["2025-02-30"])
        self.assertEqual(renderings("iso_date", "2025-06-31"), ["2025-06-31"])

    def test_a_leap_day_is_valid_only_in_a_leap_year(self):
        from data_sheets_schema.verifiable import renderings
        self.assertIn("february 29, 2024", renderings("iso_date", "2024-02-29"))
        self.assertEqual(renderings("iso_date", "2025-02-29"), ["2025-02-29"])

    def test_a_month_only_source_no_longer_grounds_a_full_date(self):
        """'June 2026' grounded 2026-06-17 — and every other day in June, so
        day-level fabrication was undetectable."""
        from data_sheets_schema.verifiable import check_record
        self.assertEqual(
            check_record({"issued": "2026-06-17"}, "released in June 2026",
                         skip_slots=set()).grounded, 0)


class TestKnownLimits(unittest.TestCase):
    """Documented weaknesses, pinned so they are not mistaken for guarantees."""

    def test_presence_is_not_correctness(self):
        """A coincidental match grounds a wrong value. The rate is not an
        accuracy score, and the docstring says so."""
        from data_sheets_schema.verifiable import check_record
        r = check_record({"counts": "2025"}, "the paper was published in 2025",
                         skip_slots=set())
        self.assertEqual(r.grounded, 1, "documented limitation, not a bug")

    def test_small_counts_are_not_checked_and_that_inflates_the_rate(self):
        from data_sheets_schema.verifiable import extract
        self.assertEqual(list(extract({"counts": "833"}, skip_slots=set())), [])

    def test_the_module_documents_the_asymmetry(self):
        from data_sheets_schema import verifiable
        doc = verifiable.__doc__ or ""
        self.assertIn("Absence is evidence; presence is not", doc)
        self.assertIn("bias the reported rate", doc)


class TestWorksFromAnyDirectory(unittest.TestCase):
    """Paths resolved from the module, not the working directory."""

    def test_the_schema_path_is_absolute(self):
        from data_sheets_schema.verifiable import FULL_SCHEMA
        self.assertTrue(FULL_SCHEMA.is_absolute())

    def test_identifier_slots_works_from_a_foreign_cwd(self):
        import os
        import tempfile
        from data_sheets_schema.verifiable import identifier_slots
        cwd = os.getcwd()
        try:
            os.chdir(tempfile.mkdtemp())
            self.assertIn("id", identifier_slots())
        finally:
            os.chdir(cwd)


class TestTheDeclaredBundleIsUsed(unittest.TestCase):
    """Different arms read different inputs.

    Checking every run against `{project}_preprocessed.txt` reported the whole
    crate arm as inventing everything — 0 of 5 DOIs, 0 of 11 URLs on one CHORUS
    record — because `crate_only` declares `{project}_crate_only.txt`. The
    provenance records which bundle was read; assuming it was the failure.
    """

    def test_the_crate_arm_declares_a_different_bundle(self):
        from data_sheets_schema.verifiable import declared_bundle
        b = declared_bundle("claudecode_agent_crate_only",
                            "2026-07-28_claude-opus-5-crateonly_rep2", "CHORUS")
        if b is None:
            self.skipTest("crate arm not present")
        self.assertIn("crate_only", str(b))

    def test_the_baseline_arm_declares_the_preprocessed_bundle(self):
        from data_sheets_schema.verifiable import declared_bundle
        b = declared_bundle("claudecode_agent",
                            "2026-07-28_claude-opus-5-generic_rep1", "CHORUS")
        if b is None:
            self.skipTest("generic arm not present")
        self.assertIn("preprocessed", str(b))

    def test_a_run_without_provenance_returns_none(self):
        from data_sheets_schema.verifiable import declared_bundle
        self.assertIsNone(declared_bundle("nope", "nope", "nope"))

    def test_the_crate_arm_is_not_reported_as_wholly_ungrounded(self):
        """The regression this guards: 18.8% for a record whose values were
        presumably in the crate it was actually given."""
        import yaml
        from data_sheets_schema.verifiable import (
            check_record, declared_bundle, identifier_slots)
        from data_sheets_schema.runs import record_path
        method = "claudecode_agent_crate_only"
        label = "2026-07-28_claude-opus-5-crateonly_rep2"
        b = declared_bundle(method, label, "CHORUS")
        rec = record_path(method, label, "CHORUS")
        if not (b and b.exists() and rec and rec.exists()):
            self.skipTest("crate arm not present")
        r = check_record(yaml.safe_load(rec.read_text()), b.read_text(),
                         skip_slots=identifier_slots())
        self.assertGreater(r.rate, 0.5)
