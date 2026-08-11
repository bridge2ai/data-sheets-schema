"""generic-v2 must stay generic.

The arm's whole value is that every project receives identical text. A rule that
mentions a project, a dataset, or an expected quantity converts it into a third
condition and destroys the comparison it exists to support — which is what
happened to the 2026-07-28 `-deprimed` series.
"""

import re
import unittest
from pathlib import Path

from data_sheets_schema.api_runner import (
    GENERIC_PROMPT, GENERIC_PROMPT_V2, RunSpec, prompt_body, resolve_prompt,
)
from data_sheets_schema.constants import PROJECTS

# PROJECTS is imported, not restated. This file previously shadowed it with a
# four-project literal, so the assertion "every project receives identical
# text" excluded VOICE_PEDIATRIC from the day it became a project (#298) — a
# guard whose stated scope was wider than its actual scope, in exactly the area
# #419 and #422 were about. A fifth project now fails this file rather than
# passing it by omission (#467).
MARK_START = "--- ADDED IN v2 ---"
MARK_END = "--- END ADDED IN v2 ---"


def _added_block(text):
    return text.split(MARK_START, 1)[1].split(MARK_END, 1)[0]


class TestV2IsV1PlusTheAddedBlock(unittest.TestCase):

    def test_prompt_body_differs_only_by_the_marked_block(self):
        v1 = prompt_body(GENERIC_PROMPT)
        v2 = prompt_body(GENERIC_PROMPT_V2)
        stripped = (v2.split(MARK_START, 1)[0]
                    + v2.split(MARK_END, 1)[1]).strip()
        # The header block legitimately names its own file and mode.
        norm = lambda t: re.sub(r"\s+", " ", t).strip()
        a = norm(v1).replace("d4d_generic_arm_prompt.md", "P").replace(
            "generic prompt", "C").replace("# Generated: 2026-07-28",
                                           "# Generated: {DATE}")
        b = norm(stripped).replace("d4d_generic_arm_prompt_v2.md", "P").replace(
            "generic-v2 prompt", "C")
        self.assertEqual(a, b,
                         "v2 must be v1 plus the marked block and nothing else")

    def test_the_added_block_holds_exactly_three_rules(self):
        rules = [l for l in _added_block(GENERIC_PROMPT_V2.read_text()).splitlines()
                 if l.startswith("- ")]
        self.assertEqual(len(rules), 3)

    def test_v1_is_untouched_by_v2(self):
        self.assertNotIn(MARK_START, GENERIC_PROMPT.read_text(),
                         "v1 produced the 2026-07-28 baseline and must not "
                         "acquire v2's rules")


class TestTheAddedRulesAreGeneric(unittest.TestCase):
    """Each addition is checked against the playbook's priming taxonomy."""

    def setUp(self):
        self.block = _added_block(GENERIC_PROMPT_V2.read_text())

    def test_no_project_is_named(self):
        for project in PROJECTS:
            with self.subTest(project=project):
                self.assertNotIn(project, self.block,
                                 "a project name makes the rule tuned, not generic")

    def test_no_dataset_identifiers(self):
        for token in ("fairhub", "physionet", "dataverse", "10.18130",
                      "cm4ai.org", "HIGT4C", "B35XWX"):
            with self.subTest(token=token):
                self.assertNotIn(token.lower(), self.block.lower())

    def test_no_expected_quantities(self):
        """An outcome expectation is banned in both arms, not merely in generic.

        "~47 creators" or "expect 10 file_collections" would tell the model what
        answer to produce rather than how to decide.
        """
        numbers = re.findall(r"\b\d+\b", self.block)
        self.assertEqual(numbers, [],
                         f"the rules must state no quantities, found {numbers}")
        for phrase in ("expect", "should yield", "typically", "at least",
                       "roughly", "approximately"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.block.lower())

    def test_no_reference_to_prior_runs(self):
        """A quality warning steers behaviour rather than stating a rule."""
        for phrase in ("earlier run", "previous run", "prior run", "last time",
                       "has been observed", "tends to"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.block.lower())

    def test_the_prediction_lives_outside_the_prompt(self):
        """The expectation belongs in the analysis plan, or the run confirms
        the prompt rather than the rules."""
        text = GENERIC_PROMPT_V2.read_text().lower()
        self.assertNotIn("we expect", text)
        self.assertTrue(Path("notes/generic_v2_analysis_plan.md").exists(),
                        "the prediction must be registered before running")


class TestEveryProjectGetsIdenticalText(unittest.TestCase):

    def _body(self, project):
        spec = RunSpec(project=project, arm="BASELINE",
                       method="claudecode_agent",
                       bundle=Path(f"data/preprocessed/concatenated/"
                                   f"{project}_preprocessed.txt"),
                       label="L", condition="generic_v2")
        return resolve_prompt(spec)

    def test_bodies_differ_only_in_mechanical_substitutions(self):
        bodies = {p: self._body(p) for p in PROJECTS}
        base = bodies["AI_READI"].replace("AI_READI", "{P}")
        for project, body in bodies.items():
            with self.subTest(project=project):
                self.assertEqual(body.replace(project, "{P}"), base)

    def test_the_added_rules_survive_substitution(self):
        """Whitespace-normalised: the rules are line-wrapped in the file."""
        for project in PROJECTS:
            with self.subTest(project=project):
                body = re.sub(r"\s+", " ", self._body(project))
                self.assertIn("one object per distinct entity", body)
                self.assertIn("not with a pointer to where that information "
                              "lives", body)
                self.assertIn("Read the slot's description before populating "
                              "it", body)


class TestConditionResolution(unittest.TestCase):

    def _spec(self, condition):
        return RunSpec(project="CHORUS", arm="", method="claudecode_agent",
                       bundle=Path("b"), label="L", condition=condition)

    def test_generic_v2_resolves_to_v2(self):
        self.assertEqual(self._spec("generic_v2").base_prompt, GENERIC_PROMPT_V2)

    def test_generic_still_resolves_to_v1(self):
        self.assertEqual(self._spec("generic").base_prompt, GENERIC_PROMPT)

    def test_unknown_condition_is_refused(self):
        with self.assertRaises(ValueError):
            self._spec("nearly-generic").base_prompt

    def test_prompt_files_are_recorded_for_provenance(self):
        self.assertIn(GENERIC_PROMPT_V2, self._spec("generic_v2").prompt_files)


if __name__ == "__main__":
    unittest.main()


class TestEveryConditionIsReachable(unittest.TestCase):
    """A condition that cannot be launched is not staged, it is stranded.

    `generic_v2` was written, tested, and documented while the CLI's
    `--condition` choices were spelled out inline in three places — so every
    entry point rejected it. The list is now derived from the registry.
    """

    def test_the_cli_offers_every_registered_condition(self):
        from click.testing import CliRunner
        from data_sheets_schema.api_runner import CONDITION_PROMPTS
        from data_sheets_schema.cli.api import plan_cmd
        help_text = CliRunner().invoke(plan_cmd, ["--help"]).output
        for condition in CONDITION_PROMPTS:
            with self.subTest(condition=condition):
                self.assertIn(condition, help_text)

    def test_generic_v2_plans_without_error(self):
        from click.testing import CliRunner
        from data_sheets_schema.cli.api import plan_cmd
        r = CliRunner().invoke(plan_cmd, [
            "--project", "CHORUS", "--condition", "generic_v2",
            "--arm", "baseline",
            "--label", "2026-07-30_claude-opus-5-generic-v2_rep1"])
        if r.exit_code != 0 and "bundle" in (r.output or ""):
            self.skipTest("bundle not present")
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("d4d_generic_arm_prompt_v2.md", r.output)


class TestTheRunGuardsAgree(unittest.TestCase):
    """execute() raises if its own provenance check fails — after six phases.

    A mismatch between where the record is written and where the check looks
    would fail a good run at the very end, having spent the whole generation.
    """

    def test_write_and_check_resolve_to_the_same_path(self):
        from pathlib import Path
        from data_sheets_schema.api_runner import RunSpec
        from data_sheets_schema.provenance import record_path_for
        spec = RunSpec(project="CHORUS", arm="baseline",
                       method="claudecode_agent", bundle=Path("b"),
                       label="2026-07-30_x_rep1", condition="generic_v2")
        self.assertEqual(spec.provenance_path,
                         record_path_for(spec.project, spec.method, spec.label))

    def test_a_post_cutoff_label_is_subject_to_the_requirement(self):
        from data_sheets_schema.runs import requires_live
        self.assertTrue(requires_live("2026-07-30_claude-opus-5-generic-v2_rep1"))
