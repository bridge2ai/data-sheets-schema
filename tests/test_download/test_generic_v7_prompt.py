"""generic-v7 must stay generic, and must be v6 plus its block (#710).

Mirrors `test_generic_v6_prompt.py`. v7 adds **one** rule — the full record
is followed by its coverage receipt — and nothing else changes but the
version stamp. The runner-side half of the condition (chunk markers in the
cached bundle, the receipt instruction on the full phase, the receipt file
and its provenance block) is tested in `test_api_runner.py`.
"""

import re
import unittest

from data_sheets_schema.api_runner import (
    CONDITION_AXES,
    CONDITION_PROMPTS,
    GENERIC_PROMPT_V6,
    GENERIC_PROMPT_V7,
    RECEIPT_CONDITIONS,
    RECEIPT_MARK,
    comparable_conditions,
    condition_delta,
    prompt_body,
)
from data_sheets_schema.constants import PROJECTS

MARK_START = "--- ADDED IN v7 ---"
MARK_END = "--- END ADDED IN v7 ---"


def _added_block(text):
    return text.split(MARK_START, 1)[1].split(MARK_END, 1)[0]


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


class TestV7IsV6PlusTheAddedBlock(unittest.TestCase):
    VERSION_STAMP = re.compile(r"#\s*(?:Mode|Prompt):[^\n]*")

    def test_body_differs_from_v6_only_by_the_block(self):
        v6 = prompt_body(GENERIC_PROMPT_V6)
        v7 = prompt_body(GENERIC_PROMPT_V7)
        stripped = (v7.split(MARK_START, 1)[0] + v7.split(MARK_END, 1)[1]).strip()
        scrub = lambda t: _norm(self.VERSION_STAMP.sub("", t))  # noqa: E731
        self.assertEqual(scrub(stripped), scrub(v6))

    def test_the_version_stamp_names_v7(self):
        v7 = prompt_body(GENERIC_PROMPT_V7)
        self.assertIn("generic-v7 prompt", v7)
        self.assertIn("d4d_generic_arm_prompt_v7.md", v7)
        self.assertNotIn("generic-v6 prompt", v7)

    def test_the_earlier_additions_survive_intact(self):
        v6 = GENERIC_PROMPT_V6.read_text()
        v7 = GENERIC_PROMPT_V7.read_text()
        for mark in ("v2", "v3", "v4", "v5", "v6"):
            a = v6.split(f"--- ADDED IN {mark} ---", 1)[1].split(f"--- END ADDED IN {mark} ---", 1)[0]
            b = v7.split(f"--- ADDED IN {mark} ---", 1)[1].split(f"--- END ADDED IN {mark} ---", 1)[0]
            self.assertEqual(_norm(a), _norm(b), f"the {mark} block changed")

    def test_the_added_block_holds_exactly_one_rule(self):
        rules = [l for l in _added_block(GENERIC_PROMPT_V7.read_text()).splitlines()
                 if l.startswith("- ")]
        self.assertEqual(len(rules), 1)

    def test_v6_is_untouched_by_v7(self):
        self.assertNotIn(MARK_START, GENERIC_PROMPT_V6.read_text())

    def test_the_rule_names_the_marker_and_the_validator_vocabulary(self):
        """The prompt's rule and the runner/validator must agree on the
        marker line and the closed status set, or the receipt the model
        writes is one the check cannot read."""
        from data_sheets_schema.receipts import STATUSES
        block = _added_block(GENERIC_PROMPT_V7.read_text())
        self.assertIn(f"`{RECEIPT_MARK}`", block)
        for st in STATUSES:
            self.assertIn(f"`{st}`", block)
        self.assertIn("[cNNN]", block)


class TestTheAddedRuleIsGeneric(unittest.TestCase):
    def setUp(self):
        self.block = _added_block(GENERIC_PROMPT_V7.read_text())

    def test_no_project_is_named(self):
        low = self.block.lower()
        for p in PROJECTS:
            self.assertNotIn(p.lower().replace("_", "-"), low.replace("_", "-"))
        for name in ("bridge2ai", "physionet", "fairhub", "dataverse", "voice", "chorus"):
            self.assertNotIn(name, low)

    def test_no_dataset_identifiers(self):
        self.assertIsNone(re.search(r"10\.\d{4,}/|ror\.org/|orcid\.org/|\bdoi:", self.block))

    def test_no_expected_quantities(self):
        # `funders[0]` is a path shape, not a quantity; strip bracket indexes first
        text = re.sub(r"\[\d+\]", "[]", self.block)
        self.assertIsNone(re.search(r"\b\d+\b", text), "a quantity in the rule is an outcome expectation")

    def test_no_reference_to_prior_runs(self):
        low = self.block.lower()
        for word in ("replicate", "earlier run", "previous", "arm ", "v6", "#708", "#710"):
            self.assertNotIn(word, low)


class TestTheConditionIsWiredComparably(unittest.TestCase):
    def test_v7_resolves_to_its_own_prompt_and_is_a_receipt_condition(self):
        self.assertEqual(CONDITION_PROMPTS["generic_v7"], GENERIC_PROMPT_V7)
        self.assertEqual(CONDITION_AXES["generic_v7"], {"base": "v7", "tuned": False})
        self.assertIn("generic_v7", RECEIPT_CONDITIONS)
        self.assertNotIn("generic_v6", RECEIPT_CONDITIONS)

    def test_v6_against_v7_is_one_condition_step(self):
        self.assertEqual(condition_delta("generic_v6", "generic_v7"), ["base"])
        self.assertTrue(comparable_conditions("generic_v6", "generic_v7"))
        self.assertFalse(comparable_conditions("generic_v5", "generic_v7"))

    def test_v7_is_launchable_from_the_cli(self):
        import click.testing

        from data_sheets_schema.cli.api import api
        r = click.testing.CliRunner().invoke(api, ["batch", "--help"])
        self.assertIn("generic_v7", r.output)


if __name__ == "__main__":
    unittest.main()
