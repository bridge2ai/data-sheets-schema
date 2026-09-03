"""Cross-slot restatement is measured, not enforced (#501).

The decision on #501 was to **accept** the repetition: a reader who opens one
slot must find an answer there, not a pointer to another slot. So these tests
hold that the measurement is honest and that nothing acts on it — a later change
that turned this into a gate would silently reverse a decision.
"""

import subprocess
import unittest
from pathlib import Path

from data_sheets_schema import redundancy as red

CORE = Path("data/d4d_concatenated/claudecode_agent")
LONG = ("The public release is stripped of protected health information as "
        "defined by the HIPAA Privacy Rule Safe Harbor method.")
PARA = ("The public release excludes protected health information as defined "
        "by the HIPAA Privacy Rule Safe Harbor method.")
OTHER = ("Participants were recruited at three clinical sites between March "
         "2021 and November 2023 under a common protocol.")


class TestItFindsParaphraseNotOnlyCopies(unittest.TestCase):
    """The property an exact-match pass lacks. Measured on the real records,
    exact matching found 8 restatements in AI_READI and missed the Safe Harbor
    family entirely, because every one of its five placements is reworded."""

    def test_a_paraphrase_across_slots_is_found(self):
        found = red.restatements({"is_deidentified": LONG,
                                  "preprocessing_strategies": PARA})
        self.assertEqual(len(found), 1)
        self.assertGreater(found[0].similarity, red.THRESHOLD)

    def test_an_exact_copy_is_found_too(self):
        found = red.restatements({"is_deidentified": LONG,
                                  "participant_privacy": LONG})
        self.assertEqual(len(found), 1)

    def test_unrelated_sentences_are_not(self):
        self.assertEqual(
            red.restatements({"is_deidentified": LONG, "creators": OTHER}), [])

    def test_repetition_within_one_slot_is_not_cross_slot(self):
        """A slot restating itself is a different defect and not this one."""
        self.assertEqual(
            red.restatements({"is_deidentified": [LONG, PARA]}), [])


class TestWhatIsDeliberatelyNotCounted(unittest.TestCase):
    def test_a_bare_url_is_structural(self):
        found = red.restatements({
            "distribution_formats": "https://dataverse.lib.virginia.edu/x?persistentId=doi:10.18130/V3/B35XWX",
            "download_url": "https://dataverse.lib.virginia.edu/x?persistentId=doi:10.18130/V3/B35XWX"})
        self.assertTrue(all(r.structural for r in found))

    def test_a_nested_resource_repeating_its_parent_is_structural(self):
        found = red.restatements({"title": LONG, "resources": LONG})
        self.assertTrue(all(r.structural for r in found))

    def test_structural_pairs_are_excluded_from_the_headline_rate(self):
        """Folding them in would overstate the figure by about a third —
        CM4AI's 30 structural pairs are almost all Dataverse URLs."""
        summary = red.summarize({"title": LONG, "resources": LONG})
        self.assertEqual(summary["prose_restatements"], 0)
        self.assertEqual(summary["structural_restatements"], 1)

    def test_short_fragments_are_ignored(self):
        """Below the content-word floor, overlap says nothing: two five-word
        sentences sharing three words score 0.43 without restating anything."""
        self.assertEqual(red.restatements({"a": "Yes, it is.",
                                           "b": "Yes, it is."}), [])


class TestTheRateIsPerSentence(unittest.TestCase):
    def test_the_denominator_is_sentences_not_slots(self):
        """A per-slot rate would fall simply by generating more content, which
        would reward padding."""
        summary = red.summarize({"is_deidentified": LONG,
                                 "preprocessing_strategies": PARA,
                                 "creators": OTHER})
        self.assertEqual(summary["sentences"], 3)
        self.assertAlmostEqual(summary["rate"], 1 / 3)

    def test_an_empty_record_has_no_rate_rather_than_a_crash(self):
        self.assertEqual(red.summarize({})["rate"], 0.0)


@unittest.skipUnless(CORE.exists(), "corpus absent")
class TestAgainstTheCanonicalSet(unittest.TestCase):
    def test_the_rate_is_in_the_range_the_decision_was_made_on(self):
        """A floor and a ceiling, not a pinned figure. The decision to accept
        repetition was made at 7.4%; if a later arm reads 30% something changed
        that nobody chose, and if it reads 0% the measure has broken.
        """
        from data_sheets_schema.runs import canonical_runs

        total = restated = 0
        from data_sheets_schema.runs import canonical_sets
        for _rt, found in canonical_sets().items():
          for project, info in found.items():
            path = CORE.parent / info["method"] / info["label"] / f"{project}_d4d.yaml"
            if not path.exists():
                continue
            summary = red.summarize(red.load(path))
            total += summary["sentences"]
            restated += summary["prose_restatements"]
        if not total:
            self.skipTest("no canonical records on disk")
        rate = restated / total
        self.assertGreater(rate, 0.01, "measure appears to have stopped firing")
        self.assertLess(rate, 0.25, "restatement well above the decided level")

    def test_the_safe_harbor_family_is_detected(self):
        """The case the issue was filed about. If this stops firing, the
        measure has regressed to string matching."""
        from data_sheets_schema.runs import canonical_runs

        info = canonical_runs(runtime="api").get("AI_READI")
        path = CORE.parent / info["method"] / info["label"] / "AI_READI_d4d.yaml" if info else None
        if not path or not path.exists():
            self.skipTest("AI_READI canonical record absent")
        found = red.restatements(red.load(path))
        self.assertTrue(found, "no restatement found in the worst-case record")


class TestItIsReportedNotEnforced(unittest.TestCase):
    def test_the_command_exits_zero(self):
        """The decision was to accept the repetition. A non-zero exit would
        make it a gate and reverse that silently."""
        result = subprocess.run(
            ["poetry", "run", "d4d", "runs", "redundancy"],
            capture_output=True, text=True, check=False)
        if "no canonical records" in (result.stdout + result.stderr):
            self.skipTest("no canonical records on disk")
        self.assertEqual(result.returncode, 0)

    def test_the_output_says_it_is_not_a_failure(self):
        result = subprocess.run(
            ["poetry", "run", "d4d", "runs", "redundancy"],
            capture_output=True, text=True, check=False)
        if result.returncode != 0:
            self.skipTest("command unavailable here")
        self.assertIn("reported, not failed", result.stdout)


class TestTheRateIsReportedWithItsThreshold(unittest.TestCase):
    """Found reviewing this change. The headline swings 2.1% (exact match) to
    12.0% (0.6 -> 0.5) on the same corpus, so a rate quoted without its
    threshold is unfalsifiable and invites comparison against a future figure
    computed differently."""

    def test_the_threshold_changes_the_count(self):
        """The premise. If these ever agreed, the measure would have stopped
        depending on the parameter and this guard would be vacuous."""
        record = {"is_deidentified": LONG, "preprocessing_strategies": PARA}
        loose = red.summarize(record, threshold=0.5)["prose_restatements"]
        strict = red.summarize(record, threshold=1.0)["prose_restatements"]
        self.assertGreater(loose, strict)

    def test_the_command_prints_the_threshold(self):
        result = subprocess.run(
            ["poetry", "run", "d4d", "runs", "redundancy"],
            capture_output=True, text=True, check=False)
        if result.returncode != 0:
            self.skipTest("command unavailable here")
        self.assertIn(f"threshold {red.THRESHOLD}", result.stdout)

    def test_an_overridden_threshold_is_the_one_reported(self):
        """Printing the default while having used an override would be worse
        than printing nothing."""
        result = subprocess.run(
            ["poetry", "run", "d4d", "runs", "redundancy", "--threshold", "0.9"],
            capture_output=True, text=True, check=False)
        if result.returncode != 0:
            self.skipTest("command unavailable here")
        self.assertIn("threshold 0.9", result.stdout)
