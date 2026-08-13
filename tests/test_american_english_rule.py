"""The American-English rule is stated where it does not redefine a condition (#502).

From Camille Nebeker's review. The rule itself is uncontroversial; *where* it is
written is the decision, because editing a condition prompt rotates its pin and
v1's pin is what the fifteen records of the 2026-08-11 canonical arm hashed.
Rotating it would move all fifteen from `canonical` to `superseded`.

So the rule lives in the playbook, and these tests hold both halves: that it is
stated there, and that stating it disturbed no pin.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / ".claude/commands/d4d-full-core.md"
PROMPTS = ROOT / "src/download/prompts"


class TestTheRuleIsStated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PLAYBOOK.read_text(encoding="utf-8")

    def test_the_playbook_states_american_english(self):
        self.assertIn("American English", self.text)

    def test_it_sits_among_the_uniform_decision_rules(self):
        """Not in a section a run might skip. The uniform rules are the ones
        the playbook says to enforce whether or not a prompt file was used."""
        start = self.text.index("Uniform decision rules")
        end = self.text.index("### Recording the condition")
        self.assertIn("American English", self.text[start:end])

    def test_the_three_carve_outs_are_present(self):
        """Without them the rule instructs a run to corrupt evidence — the
        bundles contain `licence` 13 times and `programme` 6."""
        section = self.text[self.text.index("American English"):]
        for phrase in ("Quoted source text", "Proper nouns",
                       "Identifiers copied from a source"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

    def test_the_load_bearing_rule_is_named_not_positional(self):
        """It used to read "the last rule", which a later insertion would
        silently repoint at something else."""
        self.assertNotIn("The last rule is the load-bearing", self.text)
        self.assertIn("no target slot count is the load-bearing", self.text)


class TestItDidNotRedefineACondition(unittest.TestCase):
    """The reason it is in the playbook rather than the prompts."""

    def test_no_condition_prompt_carries_the_rule(self):
        for path in sorted(PROMPTS.glob("d4d_*_arm_prompt*.md")):
            with self.subTest(prompt=path.name):
                self.assertNotIn("American English",
                                 path.read_text(encoding="utf-8"))

    def test_every_pinned_prompt_is_still_at_its_pin(self):
        import subprocess
        result = subprocess.run(
            ["poetry", "run", "d4d", "api", "prompts", "check", "--strict"],
            capture_output=True, text=True, check=False, cwd=ROOT)
        self.assertEqual(result.returncode, 0,
                         (result.stdout + result.stderr)[-600:])

    def test_the_canonical_arm_is_not_uncanonical(self):
        """The property that would have been lost by editing v1 *for this rule*.

        The arm reads `superseded` since #515 deliberately rotated the pins
        ahead of a re-baselining. That is the state this test was written to
        avoid reaching *accidentally* — and reaching it by decision, with the
        rotation recorded and the previous hash retained, is a different thing.
        `uncanonical` remains the failure: it would mean the text was never a
        published version of its condition.
        """
        from data_sheets_schema.runs import (canonical_prompt_status,
                                             canonical_runs)
        runs = canonical_runs()
        if not runs:
            self.skipTest("no canonical records on disk")
        for project, info in runs.items():
            with self.subTest(project=project):
                status, why = canonical_prompt_status(
                    "claudecode_agent", info["label"], project)
                self.assertIn(status, ("canonical", "superseded"), why)
