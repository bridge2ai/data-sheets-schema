"""The registry vocabulary reaches the run and the judge (#538).

`data_topic` and `data_substrate` have declared `values_from: B2AI_TOPIC` /
`B2AI_SUBSTRATE` all along. Nothing rendered it, so no run was ever shown the
terms — and the corpus records the consequence:

    data_substrate, 23 well-formed IRIs, every one wrong
      cellosaurus.org/CVCL_0419  x11   MDA-MB-468, a breast cancer cell line
      cellosaurus.org/CVCL_B5P3  x9    KOLF2.1J, an iPSC line
      meshb…D005453 / D013058 / D064113  Fluorescence, Mass Spectrometry, CRISPR

None is a type of data. The 11 prose values were right in substance and had no
term to be written as — `B2AI_SUBSTRATE` has DICOM, Comma-separated values,
Waveform Data, JSON, Image, Text and Parquet, and always did.

So the declaration was correct and invisible. This renders it.
"""

import unittest
from pathlib import Path

import yaml

from data_sheets_schema import schema_digest
from data_sheets_schema.evidence_score import slot_spec

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "src/data_sheets_schema/b2ai_registry_vocabularies.yaml"


class TestTheVocabularyIsPinned(unittest.TestCase):
    def test_both_vocabularies_are_present(self):
        vocab = schema_digest.vocabularies()
        self.assertGreater(len(vocab["B2AI_SUBSTRATE"]), 70)
        self.assertGreater(len(vocab["B2AI_TOPIC"]), 50)

    def test_it_covers_what_the_prose_values_describe(self):
        """The test that decides whether option 3 was possible at all. If the
        registry could not express DICOM or waveform data, rendering it would
        have forced runs to pick a near-neighbour."""
        terms = set(schema_digest.vocabularies()["B2AI_SUBSTRATE"].values())
        for needed in ("DICOM", "Comma-separated values", "Waveform Data",
                       "JSON", "Image", "Text"):
            with self.subTest(term=needed):
                self.assertIn(needed, terms)

    def test_it_covers_each_project_topic(self):
        terms = set(schema_digest.vocabularies()["B2AI_TOPIC"].values())
        for needed in ("Diabetes", "Voice", "Clinical Observations", "Cell"):
            with self.subTest(term=needed):
                self.assertIn(needed, terms)

    def test_the_pin_is_traceable(self):
        source = (yaml.safe_load(PIN.read_text(encoding="utf-8")) or {})["source"]
        self.assertRegex(str(source["commit"]), r"^[0-9a-f]{40}$")
        self.assertTrue(source.get("repository"))


class TestItReachesTheGenerationPrompt(unittest.TestCase):
    """`data_topic` and `data_substrate` are attributes of `Instance`, not
    slots of `Dataset`, so a top-level-only rendering would reach neither —
    the same trap #486 hit with nested ranges."""

    @classmethod
    def setUpClass(cls):
        cls.text = schema_digest.digest_text("Dataset")

    def test_the_digest_names_the_vocabulary(self):
        self.assertIn("draws from", self.text)

    def test_both_slots_are_covered(self):
        for slot in ("data_topic", "data_substrate"):
            with self.subTest(slot=slot):
                self.assertTrue(
                    any(slot in line and "draws from" in line
                        for line in self.text.splitlines()))

    def test_specific_terms_are_visible(self):
        """A vocabulary named but not listed is no more usable than none."""
        for term in ("DICOM", "Waveform Data", "Diabetes"):
            with self.subTest(term=term):
                self.assertIn(term, self.text)

    def test_the_digest_stays_within_budget(self):
        self.assertLess(len(self.text), 44_000)


class TestItReachesTheJudge(unittest.TestCase):
    def test_slot_spec_names_the_vocabulary(self):
        spec = slot_spec("instances")
        self.assertIn("must be drawn from", spec)
        self.assertIn("data_substrate", spec)

    def test_the_judge_sees_the_terms(self):
        """Without them a judge cannot tell that a Cellosaurus cell line is
        the wrong *kind* of thing — it is a resolvable IRI, so every syntactic
        check passes it."""
        self.assertIn("DICOM", slot_spec("instances"))


class TestUnknownVocabulariesRenderNothing(unittest.TestCase):
    """Silence is the honest output when the terms are unknown — guessing
    would put a vocabulary in front of a run that nobody pinned."""

    def test_an_unpinned_name_renders_none(self):
        self.assertIsNone(schema_digest.render_values_from(["NOT_A_REGISTRY"]))

    def test_an_empty_list_renders_none(self):
        self.assertIsNone(schema_digest.render_values_from([]))

    def test_a_known_name_still_renders_alongside_an_unknown_one(self):
        out = schema_digest.render_values_from(["NOPE", "B2AI_TOPIC"])
        self.assertIn("Diabetes", out)


class TestTheCacheKeyMoves(unittest.TestCase):
    """The judge's question changed, so cached fitness labels must not be
    reused — the #465 failure this repository keeps having to avoid."""

    def test_stripping_the_vocabulary_changes_the_fingerprint(self):
        import copy

        digest = copy.deepcopy(schema_digest.build("Dataset"))
        before = schema_digest.fingerprint(schema_digest.render(digest))
        for nested in digest.nested:
            nested.values_from = {}
        after = schema_digest.fingerprint(schema_digest.render(digest))
        self.assertNotEqual(before, after)


class TestTheFallbackIsRendered(unittest.TestCase):
    """The vocabulary is not exhaustive, and the slot's own guidance does not
    reach the run.

    Found reviewing this change. A nested attribute's *description* is not
    rendered, so `data_topic`'s "Where no term is found, prefer omission over a
    prose topic" is invisible — a run sees 56 terms and no instruction to
    decline. CHORUS is the live case: its subject is acute and critical care,
    and none of the 56 `B2AI_TOPIC` terms names it. Without the fallback the
    run has 56 near-neighbours in front of it, and picking the closest is the
    invention `OTHER` was added to prevent in #403.
    """

    def test_the_rendering_says_to_omit_rather_than_approximate(self):
        out = schema_digest.render_values_from(["B2AI_TOPIC"])
        self.assertIn("omit the slot rather than approximate", out)

    def test_it_also_forbids_falling_back_to_prose(self):
        """The other failure mode, and the one the corpus actually shows: 11
        prose values in a slot ranged `uriorcurie`."""
        out = schema_digest.render_values_from(["B2AI_TOPIC"])
        self.assertIn("never restate the subject as prose", out)

    def test_it_reaches_both_the_run_and_the_judge(self):
        self.assertIn("omit the slot rather than approximate",
                      schema_digest.digest_text("Dataset"))
        self.assertIn("omit the slot rather than approximate",
                      slot_spec("instances"))

    def test_nothing_is_rendered_when_no_vocabulary_is_known(self):
        """The fallback must not appear on its own — a bare instruction to
        omit, with no list, would be worse than silence."""
        self.assertIsNone(schema_digest.render_values_from(["NOT_A_REGISTRY"]))


class TestTheVocabularyCoverageIsKnown(unittest.TestCase):
    """What the vocabulary can and cannot express, pinned so a future registry
    refresh shows up as a diff here rather than as a silent change in what runs
    can say."""

    def test_every_substrate_concept_the_corpus_needs_exists(self):
        terms = set(schema_digest.vocabularies()["B2AI_SUBSTRATE"].values())
        for concept in ("DICOM", "Comma-separated values", "Waveform Data",
                        "JSON", "Text", "Image", "Parquet", "Data Frame"):
            with self.subTest(concept=concept):
                self.assertIn(concept, terms)

    def test_chorus_topic_is_a_known_gap(self):
        """Not a defect to fix here — a fact the fallback exists for. If a
        `Critical Care` term is ever added upstream, this test fails and the
        gap is closed rather than forgotten."""
        terms = set(schema_digest.vocabularies()["B2AI_TOPIC"].values())
        self.assertNotIn("Critical Care", terms)
        self.assertNotIn("Radiology", terms)
