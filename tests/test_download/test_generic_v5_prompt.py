"""generic-v5 must stay generic, and must be v5 plus its block.

Mirrors `test_generic_v5_prompt.py`, with one deliberate difference: **v5 adds
four rules, not one.** Two are parity fixes for rules that already reach the
agentic path through the playbook and reached the API path through nothing
(#545); two are new and inseparable — where an identifier may come from (#547)
and what to write when the evidence supplies none (#531).

The cost is that a v5-against-v5 delta cannot be attributed to any single rule.
`notes/generic_v5_analysis_plan.md` says so, registered before any run, which is
the same discipline #338 established and not an exception to it.

The genericity assertions below are unchanged and are why the block reads as it
does: a first draft used a real dataset DOI as its example of a minted fragment,
which `test_no_dataset_identifiers` refused. A generic arm that illustrates a
rule with one project's identifier is priming every other project.
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
    GENERIC_PROMPT_V5,
    comparable_conditions,
    condition_delta,
    prompt_body,
)
from data_sheets_schema.constants import PROJECTS

# PROJECTS is imported, not restated. A four-project literal here made
# the per-project assertions below exclude VOICE_PEDIATRIC from the day
# #298 made it a project, so a guard that reads as covering every
# project covered four of five (#467).
MARK_START = "--- ADDED IN v5 ---"
MARK_END = "--- END ADDED IN v5 ---"


def _added_block(text):
    return text.split(MARK_START, 1)[1].split(MARK_END, 1)[0]


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


class TestV5IsV4PlusTheAddedBlock(unittest.TestCase):

    #: The header lines that name the version, which must differ (#337).
    VERSION_STAMP = re.compile(r"#\s*(?:Mode|Prompt):[^\n]*")

    def test_body_differs_from_v4_only_by_the_marked_block(self):
        v3 = prompt_body(GENERIC_PROMPT_V4)
        v5 = prompt_body(GENERIC_PROMPT_V5)
        stripped = (v5.split(MARK_START, 1)[0]
                    + v5.split(MARK_END, 1)[1]).strip()
        self.assertEqual(_norm(self.VERSION_STAMP.sub("", stripped)),
                         _norm(self.VERSION_STAMP.sub("", v3)),
                         "v5 must be v3 plus the marked block, the version "
                         "stamp, and nothing else")

    def test_the_version_stamp_names_v5(self):
        v5 = prompt_body(GENERIC_PROMPT_V5)
        self.assertIn("generic-v5 prompt", v5)
        self.assertIn("d4d_generic_arm_prompt_v5.md", v5)
        self.assertNotIn("generic-v3 prompt", v5)
        self.assertNotIn("d4d_generic_arm_prompt_v4.md", v5)

    def test_the_earlier_additions_survive_intact(self):
        """v5 supplements v2's three and v3's one; it replaces neither.

        If they were dropped, a v3-vs-v5 difference would measure their removal
        as well as the addition.
        """
        v5 = prompt_body(GENERIC_PROMPT_V5)
        for mark, expected in (("v2", 3), ("v3", 1), ("v4", 1)):
            block = (v5.split(f"--- ADDED IN {mark} ---", 1)[1]
                       .split(f"--- END ADDED IN {mark} ---", 1)[0])
            with self.subTest(version=mark):
                self.assertEqual(
                    len([l for l in block.splitlines() if l.startswith("- ")]),
                    expected)

    def test_the_added_block_holds_exactly_four_rules(self):
        """Four, and the number is asserted so a fifth cannot arrive quietly.

        The convention is one rule per version; v5 departs from it for the
        reason in the module docstring. A departure that is counted is a
        decision — one that is not is a drift.
        """
        rules = [l for l in _added_block(GENERIC_PROMPT_V5.read_text()).splitlines()
                 if l.startswith("- ")]
        self.assertEqual(len(rules), 4)

    def test_earlier_versions_are_untouched_by_v5(self):
        for path in (GENERIC_PROMPT, GENERIC_PROMPT_V2, GENERIC_PROMPT_V3,
                     GENERIC_PROMPT_V4):
            with self.subTest(path=path.name):
                self.assertNotIn(MARK_START, path.read_text(),
                                 "an earlier version produced a baseline and "
                                 "must not acquire v5's rule")


class TestTheAddedRuleIsGeneric(unittest.TestCase):

    def setUp(self):
        self.block = _added_block(GENERIC_PROMPT_V5.read_text())

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
        text = GENERIC_PROMPT_V5.read_text().lower()
        self.assertNotIn("we expect", text)
        self.assertTrue(Path("notes/generic_v5_analysis_plan.md").exists(),
                        "the prediction must be registered before running")


class TestTheConditionIsWiredComparably(unittest.TestCase):

    def test_v5_resolves_to_its_own_prompt(self):
        self.assertEqual(CONDITION_PROMPTS["generic_v5"], GENERIC_PROMPT_V5)

    def test_v4_against_v5_is_the_isolating_comparison(self):
        self.assertTrue(comparable_conditions("generic_v4", "generic_v5"))
        self.assertEqual(condition_delta("generic_v4", "generic_v5"), ["base"])

    def test_v2_against_v5_is_not_isolating(self):
        """Two rule additions apart. `condition_delta` reports the single axis
        `base`, which is why comparability needs adjacency and not just a
        one-axis difference (#338)."""
        self.assertEqual(condition_delta("generic_v2", "generic_v5"), ["base"])
        self.assertFalse(comparable_conditions("generic_v2", "generic_v5"))

    def test_v5_against_tuned_is_confounded(self):
        self.assertFalse(comparable_conditions("generic_v5", "tuned"))
        self.assertEqual(sorted(condition_delta("generic_v5", "tuned")),
                         ["base", "tuned"])

    def test_each_generic_base_is_distinct(self):
        bases = [CONDITION_AXES[c]["base"]
                 for c in ("generic", "generic_v2", "generic_v4", "generic_v5")]
        self.assertEqual(len(set(bases)), 4,
                         "two conditions sharing a base would be indistinguishable")

    def test_v5_is_launchable_from_the_cli(self):
        """`generic_v2` was once staged, tested and unreachable because the
        condition list was written out inline three times."""
        from data_sheets_schema.cli.api import _CONDITIONS
        self.assertIn("generic_v5", _CONDITIONS)


@unittest.skipUnless(GENERIC_PROMPT_V5.exists(), "v5 prompt not present")
class TestConditionIsRecoverableFromProvenance(unittest.TestCase):
    """`condition_of` returned None for every v3 and v5 run (#340).

    Its hardcoded chain knew v1, v2 and tuned. `d4d_generic_arm_prompt_v4.md`
    does not contain `d4d_generic_arm_prompt.md` as a substring — the `_v4` sits
    between `prompt` and `.md` — so a v3 run fell through every branch and the
    function reported nothing, silently, on the path the rerun takes.
    """

    def _infer(self, *prompt_paths):
        import tempfile

        import yaml

        from data_sheets_schema.runs import condition_of
        with tempfile.TemporaryDirectory() as tmp:
            # `record_path_for` appends `_core` to the method, which is where
            # provenance is written for both arms.
            root = Path(tmp) / "claudecode_agent_core" / "LBL"
            root.mkdir(parents=True)
            # Entries are mappings in real provenance, not bare strings.
            (root / "CHORUS_provenance.yaml").write_text(yaml.safe_dump(
                {"prompts": {"files": [{"path": p, "sha256": "x"}
                                       for p in prompt_paths]}}))
            return condition_of("claudecode_agent", "LBL", "CHORUS",
                                concat_dir=Path(tmp))

    def test_every_registered_condition_is_recoverable(self):
        for condition, path in CONDITION_PROMPTS.items():
            if condition == "tuned":
                continue
            with self.subTest(condition=condition):
                self.assertEqual(self._infer(f"src/download/prompts/{path.name}"),
                                 condition)

    def test_the_tuned_arm_is_still_distinguished_from_its_generic_base(self):
        """It shares v1's file, so testing the generic bases first would report
        it as `generic`."""
        self.assertEqual(
            self._infer("src/download/prompts/d4d_generic_arm_prompt.md",
                        "src/download/prompts/d4d_tuned_arm_prompt.md"),
            "tuned")

    def test_the_more_specific_version_wins_when_several_are_listed(self):
        """Provenance may name more than one prompt — `tuned` already does.

        Iterating the registry in an arbitrary order would return whichever
        matched first, so a run listing both the v1 base and v5 could be
        reported as `generic`. That failure is silent and wrong in the same way
        #340 was, which is why the registry is walked longest-name-first rather
        than in dict order.

        No provenance on disk lists two generic prompts today; this is the case
        the ordering exists for, exercised rather than assumed.
        """
        self.assertEqual(
            self._infer("src/download/prompts/d4d_generic_arm_prompt.md",
                        "src/download/prompts/d4d_generic_arm_prompt_v5.md"),
            "generic_v5")

    def test_an_unrecognised_prompt_still_returns_none(self):
        self.assertIsNone(self._infer("src/download/prompts/something_else.md"))

    def test_no_condition_is_reported_for_a_run_without_provenance(self):
        from data_sheets_schema.runs import condition_of
        self.assertIsNone(condition_of("claudecode_agent", "no-such-label",
                                       "CHORUS", concat_dir=Path("/nonexistent")))


if __name__ == "__main__":
    unittest.main()
