"""generic-v6 must stay generic, and must be v5 plus its block and its two
counted header lines.

Mirrors `test_generic_v5_prompt.py`. v6 adds **one** rule — the minting
density norm (#685) — so the one-rule-per-version convention holds for the
rule. It also rewrites the Phase 2 sentence and two lines of the CORE HEADER
BLOCK to say the core is derived (#694), because a pinned header claiming a
generation that no longer happens would be a false attestation. Those are
counted here as the *only* other differences, so a third cannot arrive
quietly.

The genericity assertions are the v5 file's, unchanged: the norm must name no
project, dataset, slot, quantity or prior run.
"""

import re
import unittest

from data_sheets_schema.api_runner import (
    CONDITION_AXES,
    CONDITION_PROMPTS,
    GENERIC_PROMPT,
    GENERIC_PROMPT_V2,
    GENERIC_PROMPT_V3,
    GENERIC_PROMPT_V4,
    GENERIC_PROMPT_V5,
    GENERIC_PROMPT_V6,
    comparable_conditions,
    condition_delta,
    prompt_body,
)
from data_sheets_schema.constants import PROJECTS

MARK_START = "--- ADDED IN v6 ---"
MARK_END = "--- END ADDED IN v6 ---"


def _added_block(text):
    return text.split(MARK_START, 1)[1].split(MARK_END, 1)[0]


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


class TestV6IsV5PlusTheAddedBlockAndTheDerivedHeader(unittest.TestCase):

    #: The header lines that name the version, which must differ (#337).
    VERSION_STAMP = re.compile(r"#\s*(?:Mode|Prompt):[^\n]*")
    #: The two counted header differences (#694) and the Phase 2 sentence.
    DERIVED_LINES = re.compile(
        r"#\s*Generation Method: (?:schema-grounded agentic, phase 2|derived by projection[^\n]*)"
        r"|#\s*Sources:[^\n]*"
        r"|Execution mode: four-phase project agent\.[^.]*\.[^.]*\.")

    def test_body_differs_from_v5_only_by_the_block_and_the_counted_lines(self):
        v5 = prompt_body(GENERIC_PROMPT_V5)
        v6 = prompt_body(GENERIC_PROMPT_V6)
        stripped = (v6.split(MARK_START, 1)[0] + v6.split(MARK_END, 1)[1]).strip()

        def scrub(t):
            return _norm(self.DERIVED_LINES.sub("", self.VERSION_STAMP.sub("", t)))
        self.assertEqual(scrub(stripped), scrub(v5),
                         "v6 must be v5 plus the marked block, the version "
                         "stamp, the Phase 2 sentence and the two derived "
                         "header lines, and nothing else")

    def test_the_core_header_says_derived_and_names_the_full_only(self):
        v6 = prompt_body(GENERIC_PROMPT_V6)
        self.assertIn("# Generation Method: derived by projection from the full record (#694)", v6)
        self.assertNotIn("schema-grounded agentic, phase 2", v6)
        self.assertIn("# Sources: data/d4d_concatenated/{METHOD}/{LABEL}/{PROJECT}_d4d.yaml", v6)
        self.assertNotIn("# Sources: {BUNDLE} +", v6)
        self.assertIn("Phase 2 core\nderivation", v6)

    def test_the_version_stamp_names_v6(self):
        v6 = prompt_body(GENERIC_PROMPT_V6)
        self.assertIn("generic-v6 prompt", v6)
        self.assertIn("d4d_generic_arm_prompt_v6.md", v6)
        self.assertNotIn("generic-v5 prompt", v6)
        self.assertNotIn("d4d_generic_arm_prompt_v5.md", v6)

    def test_the_earlier_additions_survive_intact(self):
        v5 = GENERIC_PROMPT_V5.read_text()
        v6 = GENERIC_PROMPT_V6.read_text()
        for mark in ("v2", "v3", "v4", "v5"):
            a = v5.split(f"--- ADDED IN {mark} ---", 1)[1].split(f"--- END ADDED IN {mark} ---", 1)[0]
            b = v6.split(f"--- ADDED IN {mark} ---", 1)[1].split(f"--- END ADDED IN {mark} ---", 1)[0]
            self.assertEqual(_norm(a), _norm(b), f"the {mark} block changed")

    def test_the_added_block_holds_exactly_one_rule(self):
        rules = [l for l in _added_block(GENERIC_PROMPT_V6.read_text()).splitlines()
                 if l.startswith("- ")]
        self.assertEqual(len(rules), 1)

    def test_earlier_versions_are_untouched_by_v6(self):
        for path in (GENERIC_PROMPT, GENERIC_PROMPT_V2, GENERIC_PROMPT_V3,
                     GENERIC_PROMPT_V4, GENERIC_PROMPT_V5):
            with self.subTest(path=path.name):
                self.assertNotIn(MARK_START, path.read_text())


class TestTheAddedRuleIsGeneric(unittest.TestCase):
    def setUp(self):
        self.block = _added_block(GENERIC_PROMPT_V6.read_text())

    def test_no_project_is_named(self):
        low = self.block.lower()
        for p in PROJECTS:
            self.assertNotIn(p.lower().replace("_", "-"), low.replace("_", "-"))
        for name in ("bridge2ai", "physionet", "fairhub", "dataverse", "voice", "chorus"):
            self.assertNotIn(name, low)

    def test_no_dataset_identifiers(self):
        self.assertIsNone(re.search(r"10\.\d{4,}/|ror\.org/|orcid\.org/|\bdoi:", self.block))

    def test_no_slot_is_named(self):
        self.assertNotIn("`", self.block, "a slot in backticks would tie the rule to one schema shape")

    def test_no_expected_quantities(self):
        self.assertIsNone(re.search(r"\b\d+\b|\bhundred\b|\bthree\b|\bdozen\b", self.block),
                          "a quantity in the rule is an outcome expectation")

    def test_no_reference_to_prior_runs(self):
        low = self.block.lower()
        for word in ("replicate", "earlier run", "previous", "arm", "v5", "#685"):
            self.assertNotIn(word, low)

    def test_the_prediction_lives_outside_the_prompt(self):
        low = self.block.lower()
        for word in ("variance", "should fall", "expect", "reduce"):
            self.assertNotIn(word, low)


class TestTheConditionIsWiredComparably(unittest.TestCase):
    def test_v6_resolves_to_its_own_prompt(self):
        self.assertEqual(CONDITION_PROMPTS["generic_v6"], GENERIC_PROMPT_V6)
        self.assertEqual(CONDITION_AXES["generic_v6"], {"base": "v6", "tuned": False})

    def test_v5_against_v6_is_one_condition_step(self):
        self.assertEqual(condition_delta("generic_v5", "generic_v6"), ["base"])
        self.assertTrue(comparable_conditions("generic_v5", "generic_v6"))

    def test_v4_against_v6_is_not_isolating(self):
        self.assertFalse(comparable_conditions("generic_v4", "generic_v6"))

    def test_v6_is_launchable_from_the_cli(self):
        import click.testing

        from data_sheets_schema.cli.api import api
        r = click.testing.CliRunner().invoke(api, ["batch", "--help"])
        self.assertIn("generic_v6", r.output)


if __name__ == "__main__":
    unittest.main()
