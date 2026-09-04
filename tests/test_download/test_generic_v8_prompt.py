"""generic-v8 must stay generic, and must be v7 plus its block.

Mirrors `test_generic_v7_prompt.py`. v8 adds **one block of four rules**
(R1–R4 of `notes/generic_v8_analysis_plan.md`) and nothing else changes but
the version stamp. The runner-side halves of the v8 configuration — the
depth-two digest (#916), the inlined Person slots (#805), the audit and
report-gate additions — are tested where they live.
"""

import re
import unittest

from data_sheets_schema.api_runner import (
    CONDITION_AXES,
    CONDITION_PROMPTS,
    GENERIC_PROMPT_V7,
    GENERIC_PROMPT_V8,
    PHASE_INSTRUCTIONS,
    RECEIPT_CONDITIONS,
    comparable_conditions,
    condition_delta,
    prompt_body,
)

MARK_START = "--- ADDED IN v8 ---"
MARK_END = "--- END ADDED IN v8 ---"


def _added_block(text):
    return text.split(MARK_START, 1)[1].split(MARK_END, 1)[0]


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


class TestV8IsV7PlusTheAddedBlock(unittest.TestCase):
    VERSION_STAMP = re.compile(r"#\s*(?:Mode|Prompt):[^\n]*")

    def test_body_differs_from_v7_only_by_the_block(self):
        v7 = prompt_body(GENERIC_PROMPT_V7)
        v8 = prompt_body(GENERIC_PROMPT_V8)
        stripped = (v8.split(MARK_START, 1)[0] + v8.split(MARK_END, 1)[1]).strip()
        scrub = lambda t: _norm(self.VERSION_STAMP.sub("", t))  # noqa: E731
        self.assertEqual(scrub(stripped), scrub(v7))

    def test_the_version_stamp_names_v8(self):
        v8 = prompt_body(GENERIC_PROMPT_V8)
        self.assertIn("generic-v8 prompt", v8)
        self.assertIn("d4d_generic_arm_prompt_v8.md", v8)
        self.assertNotIn("generic-v7 prompt", v8)

    def test_the_earlier_additions_survive_intact(self):
        v7 = GENERIC_PROMPT_V7.read_text()
        v8 = GENERIC_PROMPT_V8.read_text()
        for mark in ("v2", "v3", "v4", "v5", "v6", "v7"):
            a = v7.split(f"--- ADDED IN {mark} ---", 1)[1].split(f"--- END ADDED IN {mark} ---", 1)[0]
            b = v8.split(f"--- ADDED IN {mark} ---", 1)[1].split(f"--- END ADDED IN {mark} ---", 1)[0]
            self.assertEqual(_norm(a), _norm(b), f"the {mark} block changed")

    def test_the_block_carries_the_five_registered_rules(self):
        block = _added_block(GENERIC_PROMPT_V8.read_text())
        bullets = re.findall(r"^- ", block, re.M)
        self.assertEqual(len(bullets), 5)          # R1–R4 (#928) and R5 (#981)
        block = _norm(block)                                   # the file wraps at 78 columns
        for probe in ("(reference — a string, not an object)",      # R1: read off the digest's marking
                      "about and when",                              # R2: tense and scope
                      "record's own computation",                    # R3: derived figures
                      "each entry carries its own receipt"):         # R4: receipts per roster entry
            self.assertIn(probe, block)

    def test_no_project_is_named(self):
        from data_sheets_schema.constants import PROJECTS
        body = prompt_body(GENERIC_PROMPT_V8)
        for p in PROJECTS:
            self.assertNotIn(p, body)


class TestV8IsRegistered(unittest.TestCase):
    def test_condition_and_axes(self):
        self.assertIs(CONDITION_PROMPTS["generic_v8"], GENERIC_PROMPT_V8)
        self.assertEqual(CONDITION_AXES["generic_v8"], {"base": "v8", "tuned": False})
        self.assertIn("generic_v8", RECEIPT_CONDITIONS)                # the receipt rule carries over
        self.assertTrue(comparable_conditions("generic_v7", "generic_v8"))
        self.assertEqual(condition_delta("generic_v7", "generic_v8"), ["base"])


class TestTheBlockStaysGeneric(unittest.TestCase):
    """v7's guards, carried forward. One departs: the block backticks slot
    and key names (`grants`, `grant_number`, `principal_investigator`,
    `related_datasets`, `source_caveats`, …). The v5–v7 convention (#742) kept
    slot paths out of backticks because a backticked path ties a rule to one
    schema shape; R1 and R4 are *about* the digest's named shapes and R3
    names the slot a caveat goes in, so the tie is the point — recorded
    here rather than silently dropped."""

    def setUp(self):
        self.block = _added_block(GENERIC_PROMPT_V8.read_text())

    def test_no_dataset_identifiers(self):
        self.assertIsNone(re.search(r"10\.\d{4,}/|ror\.org/|orcid\.org/|\bdoi:", self.block))

    def test_no_expected_quantities(self):
        text = re.sub(r"\[\d+\]", "[]", self.block)
        self.assertIsNone(re.search(r"\b\d+\b", text), "a quantity in the rule is an outcome expectation")

    def test_no_reference_to_prior_runs(self):
        low = self.block.lower()
        for word in ("replicate", "earlier run", "previous", "arm ", "v7", "v6", "#708", "#710", "#805", "#916"):
            self.assertNotIn(word, low)

    def test_backticks_name_digest_vocabulary_only(self):
        """Slot names and class names the digest renders, plus the marker
        text: nothing else may be backticked (the #742 concern, narrowed)."""
        from data_sheets_schema import schema_digest
        digest = schema_digest.build("Dataset")
        known = {s.name for s in digest.slots} | {n.name for n in digest.nested}
        for n in digest.nested:
            known |= set(n.required) | set(n.optional)
        known |= {"(reference — a string, not an object)"}
        for tok in re.findall(r"`([^`]+)`", self.block):
            tok = _norm(tok)                                   # the file wraps at 78 columns
            self.assertIn(tok, known, f"`{tok}` is neither a digest name nor the marker")

    def test_v7_is_untouched_by_v8(self):
        v7 = GENERIC_PROMPT_V7.read_text()
        self.assertNotIn("ADDED IN v8", v7)
        self.assertIn("generic-v7 prompt", prompt_body(GENERIC_PROMPT_V7))


class TestTheConditionIsWiredComparably(unittest.TestCase):
    def test_v8_is_launchable_from_the_cli(self):
        import click.testing

        from data_sheets_schema.cli.api import api
        r = click.testing.CliRunner().invoke(api, ["batch", "--help"])
        self.assertIn("generic_v8", r.output)

    def test_r1s_example_agrees_with_the_digest(self):
        """R1 says a `Person` under `principal_investigator` takes an object.
        That is true only once #805 (PR #927) has inlined the slot — on a
        main that still marks it a reference, R1 contradicts the digest it
        defers to (#573 class). This is the merge-order assertion: it
        fails until #927 lands."""
        from data_sheets_schema import schema_digest
        digest = schema_digest.build("Dataset")
        creator = next(n for n in digest.nested if n.name == "Creator")
        self.assertEqual(creator.ranges["principal_investigator"], "Person")
        gov = next(n for n in digest.nested if n.name == "DataGovernance")
        self.assertEqual(gov.ranges["committee_contact"], "Person")

    def test_the_audit_phase_carries_the_e2_flags(self):
        audit = PHASE_INSTRUCTIONS["audit"]
        for probe in ("absent, pending or held elsewhere", "neighbouring field", "`prohibition_reason`",
                      "earlier release stated as the dataset's current state",
                      "computed from other figures"):
            self.assertIn(probe, audit)
        self.assertNotIn("v8 plan", audit)                     # nothing the model cannot read


if __name__ == "__main__":
    unittest.main()
