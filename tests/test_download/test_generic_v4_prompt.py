"""generic-v4 must stay generic, and must be v3 plus one rule.

Mirrors `test_generic_v3_prompt.py`. The arm's value is that every project
receives identical text and that exactly one thing changed since the baseline it
is measured against — v3, not v2.

v4 exists as its own version rather than as a second rule inside v3 (#338).
`notes/generic_v3_analysis_plan.md` was registered before any run and names one
rule; adding a second to v3 would have invalidated that pre-registration and
made the v2-against-v3 delta unattributable to either rule.
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
    GENERIC_PROMPT_V4,
    comparable_conditions,
    condition_delta,
    prompt_body,
)

PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE")
MARK_START = "--- ADDED IN v4 ---"
MARK_END = "--- END ADDED IN v4 ---"


def _added_block(text):
    return text.split(MARK_START, 1)[1].split(MARK_END, 1)[0]


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


class TestV4IsV3PlusTheAddedBlock(unittest.TestCase):

    #: The header lines that name the version, which must differ (#337).
    VERSION_STAMP = re.compile(r"#\s*(?:Mode|Prompt):[^\n]*")

    def test_body_differs_from_v3_only_by_the_marked_block(self):
        v3 = prompt_body(GENERIC_PROMPT_V3)
        v4 = prompt_body(GENERIC_PROMPT_V4)
        stripped = (v4.split(MARK_START, 1)[0]
                    + v4.split(MARK_END, 1)[1]).strip()
        self.assertEqual(_norm(self.VERSION_STAMP.sub("", stripped)),
                         _norm(self.VERSION_STAMP.sub("", v3)),
                         "v4 must be v3 plus the marked block, the version "
                         "stamp, and nothing else")

    def test_the_version_stamp_names_v4(self):
        v4 = prompt_body(GENERIC_PROMPT_V4)
        self.assertIn("generic-v4 prompt", v4)
        self.assertIn("d4d_generic_arm_prompt_v4.md", v4)
        self.assertNotIn("generic-v3 prompt", v4)
        self.assertNotIn("d4d_generic_arm_prompt_v3.md", v4)

    def test_the_earlier_additions_survive_intact(self):
        """v4 supplements v2's three and v3's one; it replaces neither.

        If they were dropped, a v3-vs-v4 difference would measure their removal
        as well as the addition.
        """
        v4 = prompt_body(GENERIC_PROMPT_V4)
        for mark, expected in (("v2", 3), ("v3", 1)):
            block = (v4.split(f"--- ADDED IN {mark} ---", 1)[1]
                       .split(f"--- END ADDED IN {mark} ---", 1)[0])
            with self.subTest(version=mark):
                self.assertEqual(
                    len([l for l in block.splitlines() if l.startswith("- ")]),
                    expected)

    def test_the_added_block_holds_exactly_one_rule(self):
        rules = [l for l in _added_block(GENERIC_PROMPT_V4.read_text()).splitlines()
                 if l.startswith("- ")]
        self.assertEqual(len(rules), 1)

    def test_earlier_versions_are_untouched_by_v4(self):
        for path in (GENERIC_PROMPT, GENERIC_PROMPT_V2, GENERIC_PROMPT_V3):
            with self.subTest(path=path.name):
                self.assertNotIn(MARK_START, path.read_text(),
                                 "an earlier version produced a baseline and "
                                 "must not acquire v4's rule")


class TestTheAddedRuleIsGeneric(unittest.TestCase):

    def setUp(self):
        self.block = _added_block(GENERIC_PROMPT_V4.read_text())

    def test_no_project_is_named(self):
        for project in PROJECTS:
            with self.subTest(project=project):
                self.assertNotIn(project, self.block)

    def test_no_dataset_identifiers(self):
        for token in ("fairhub", "physionet", "dataverse", "10.18130",
                      "cm4ai.org", "HIGT4C", "B35XWX"):
            with self.subTest(token=token):
                self.assertNotIn(token.lower(), self.block.lower())

    def test_no_slot_is_named(self):
        """Sharper than v3's check, and the trap this rule was most likely to
        fall into: it was written to fix `target_dataset`, so naming that slot
        would turn a generic decision rule into an instruction about one field.
        """
        for slot in ("target_dataset", "related_datasets", "relationship_type"):
            with self.subTest(slot=slot):
                self.assertNotIn(slot, self.block)

    def test_no_expected_quantities(self):
        numbers = re.findall(r"\b\d+\b", self.block)
        self.assertEqual(numbers, [],
                         f"the rule must state no quantities, found {numbers}")
        for phrase in ("expect", "should yield", "typically", "at least",
                       "roughly", "approximately"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.block.lower())

    def test_no_reference_to_prior_runs(self):
        for phrase in ("earlier run", "previous run", "prior run", "last time",
                       "has been observed", "tends to", "replicate"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.block.lower())

    def test_the_prediction_lives_outside_the_prompt(self):
        text = GENERIC_PROMPT_V4.read_text().lower()
        self.assertNotIn("we expect", text)
        self.assertTrue(Path("notes/generic_v4_analysis_plan.md").exists(),
                        "the prediction must be registered before running")


class TestTheConditionIsWiredComparably(unittest.TestCase):

    def test_v4_resolves_to_its_own_prompt(self):
        self.assertEqual(CONDITION_PROMPTS["generic_v4"], GENERIC_PROMPT_V4)

    def test_v3_against_v4_is_the_isolating_comparison(self):
        self.assertTrue(comparable_conditions("generic_v3", "generic_v4"))
        self.assertEqual(condition_delta("generic_v3", "generic_v4"), ["base"])

    def test_v2_against_v4_is_not_isolating(self):
        """Two rule additions apart. `condition_delta` reports the single axis
        `base`, which is why comparability needs adjacency and not just a
        one-axis difference (#338)."""
        self.assertEqual(condition_delta("generic_v2", "generic_v4"), ["base"])
        self.assertFalse(comparable_conditions("generic_v2", "generic_v4"))

    def test_v4_against_tuned_is_confounded(self):
        self.assertFalse(comparable_conditions("generic_v4", "tuned"))
        self.assertEqual(sorted(condition_delta("generic_v4", "tuned")),
                         ["base", "tuned"])

    def test_each_generic_base_is_distinct(self):
        bases = [CONDITION_AXES[c]["base"]
                 for c in ("generic", "generic_v2", "generic_v3", "generic_v4")]
        self.assertEqual(len(set(bases)), 4,
                         "two conditions sharing a base would be indistinguishable")

    def test_v4_is_launchable_from_the_cli(self):
        """`generic_v2` was once staged, tested and unreachable because the
        condition list was written out inline three times."""
        from data_sheets_schema.cli.api import _CONDITIONS
        self.assertIn("generic_v4", _CONDITIONS)


if __name__ == "__main__":
    unittest.main()
