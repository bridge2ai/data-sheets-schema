"""generic-v3 must stay generic, and must be v2 plus one rule.

Mirrors `test_generic_v2_prompt.py`. The arm's value is that every project
receives identical text and that exactly one thing changed since the baseline it
is measured against — v2, not v1.
"""

import re
import unittest
from pathlib import Path

from data_sheets_schema.api_runner import (
    CONDITION_AXES,
    CONDITION_PROMPTS,
    GENERIC_PROMPT,
    GENERIC_PROMPT_V2,
    GENERIC_PROMPT_V3,
    comparable_conditions,
    condition_delta,
    prompt_body,
)

PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE")
MARK_START = "--- ADDED IN v3 ---"
MARK_END = "--- END ADDED IN v3 ---"


def _added_block(text):
    return text.split(MARK_START, 1)[1].split(MARK_END, 1)[0]


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


class TestV3IsV2PlusTheAddedBlock(unittest.TestCase):

    def test_body_differs_from_v2_only_by_the_marked_block(self):
        v2 = prompt_body(GENERIC_PROMPT_V2)
        v3 = prompt_body(GENERIC_PROMPT_V3)
        stripped = (v3.split(MARK_START, 1)[0]
                    + v3.split(MARK_END, 1)[1]).strip()
        self.assertEqual(_norm(stripped), _norm(v2),
                         "v3 must be v2 plus the marked block and nothing else")

    def test_v2s_three_rules_survive_intact(self):
        """The companion supplements rule 1; it does not replace it.

        If v2's rules were dropped, a v2-vs-v3 difference would measure their
        removal as well as the addition.
        """
        v3 = prompt_body(GENERIC_PROMPT_V3)
        v2_block = v3.split("--- ADDED IN v2 ---", 1)[1] \
                     .split("--- END ADDED IN v2 ---", 1)[0]
        self.assertEqual(len([l for l in v2_block.splitlines()
                              if l.startswith("- ")]), 3)

    def test_the_added_block_holds_exactly_one_rule(self):
        rules = [l for l in _added_block(GENERIC_PROMPT_V3.read_text()).splitlines()
                 if l.startswith("- ")]
        self.assertEqual(len(rules), 1)

    def test_v1_and_v2_are_untouched_by_v3(self):
        for path in (GENERIC_PROMPT, GENERIC_PROMPT_V2):
            with self.subTest(path=path.name):
                self.assertNotIn(MARK_START, path.read_text(),
                                 "an earlier version produced a baseline and "
                                 "must not acquire v3's rule")


class TestTheAddedRuleIsGeneric(unittest.TestCase):

    def setUp(self):
        self.block = _added_block(GENERIC_PROMPT_V3.read_text())

    def test_no_project_is_named(self):
        for project in PROJECTS:
            with self.subTest(project=project):
                self.assertNotIn(project, self.block)

    def test_no_dataset_identifiers(self):
        for token in ("fairhub", "physionet", "dataverse", "10.18130",
                      "cm4ai.org", "HIGT4C", "B35XWX"):
            with self.subTest(token=token):
                self.assertNotIn(token.lower(), self.block.lower())

    def test_no_expected_quantities(self):
        numbers = re.findall(r"\b\d+\b", self.block)
        self.assertEqual(numbers, [],
                         f"the rule must state no quantities, found {numbers}")
        for phrase in ("expect", "should yield", "typically", "at least",
                       "roughly", "approximately"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.block.lower())

    def test_no_reference_to_prior_runs(self):
        """The defect it corrects was found in a prior run; saying so would
        turn a decision rule into a quality warning."""
        for phrase in ("earlier run", "previous run", "prior run", "last time",
                       "has been observed", "tends to", "hollow"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.block.lower())

    def test_the_prediction_lives_outside_the_prompt(self):
        text = GENERIC_PROMPT_V3.read_text().lower()
        self.assertNotIn("we expect", text)
        self.assertTrue(Path("notes/generic_v3_analysis_plan.md").exists(),
                        "the prediction must be registered before running")


class TestTheConditionIsWiredComparably(unittest.TestCase):

    def test_v3_resolves_to_its_own_prompt(self):
        self.assertEqual(CONDITION_PROMPTS["generic_v3"], GENERIC_PROMPT_V3)

    def test_v2_against_v3_is_the_isolating_comparison(self):
        self.assertTrue(comparable_conditions("generic_v2", "generic_v3"))
        self.assertEqual(condition_delta("generic_v2", "generic_v3"), ["base"])

    def test_v3_against_tuned_is_confounded(self):
        """Same trap v2 had: tuned is pinned to the v1 base."""
        self.assertFalse(comparable_conditions("generic_v3", "tuned"))
        self.assertEqual(sorted(condition_delta("generic_v3", "tuned")),
                         ["base", "tuned"])

    def test_each_generic_base_is_distinct(self):
        bases = [CONDITION_AXES[c]["base"]
                 for c in ("generic", "generic_v2", "generic_v3")]
        self.assertEqual(len(set(bases)), 3,
                         "two conditions sharing a base would be indistinguishable")


if __name__ == "__main__":
    unittest.main()
