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
#: The rules live in one file since #563; before that they were inside
#: d4d-full-core.md, where /d4d-agent could not see them.
PLAYBOOK = ROOT / ".claude/commands/d4d-uniform-rules.md"
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
        # The rules are a file of their own since #563, so the section is the
        # file below its heading rather than a span between two headings.
        start = self.text.index("Uniform decision rules")
        self.assertIn("American English", self.text[start:])

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

    #: The conditions created *with* the rule, so they re-baseline nothing:
    #: v5 introduced it and every later version inherits v5's block.
    NEW_CONDITIONS = ("d4d_generic_arm_prompt_v5.md", "d4d_generic_arm_prompt_v6.md",
                      "d4d_generic_arm_prompt_v7.md", "d4d_generic_arm_prompt_v8.md")

    def test_no_existing_condition_prompt_acquired_the_rule(self):
        """#502's actual constraint, which v5 does not breach.

        The rule went into the playbook rather than the prompts because adding
        it to a prompt that had already been run would change what that
        condition means for every record naming it, and require a pin rotation
        mid-arm. That is still forbidden, and it is about *existing* conditions.

        v5 carries the rule from birth (#545). No record names generic_v5 yet,
        so nothing is re-baselined — which is exactly why a version boundary is
        where a playbook-only rule is allowed to move.
        """
        for path in sorted(PROMPTS.glob("d4d_*_arm_prompt*.md")):
            if path.name in self.NEW_CONDITIONS:
                continue
            with self.subTest(prompt=path.name):
                self.assertNotIn("American English",
                                 path.read_text(encoding="utf-8"))

    def test_the_new_condition_does_carry_it(self):
        """Otherwise the exemption above is an unguarded hole rather than a
        statement about one file."""
        for name in self.NEW_CONDITIONS:
            with self.subTest(prompt=name):
                self.assertIn("American English", (PROMPTS / name).read_text(encoding="utf-8"))
        text = (PROMPTS / self.NEW_CONDITIONS[0]).read_text(encoding="utf-8")
        self.assertIn("American English", text)

    def test_no_record_yet_names_the_new_condition(self):
        """The premise of the exemption, asserted rather than assumed.

        The moment a run is generated under generic_v5, this test should be
        deleted — not because the rule changed, but because from then on the
        prompt may not be edited at all, which is a stronger guarantee than
        this one and is enforced by the pin.
        """
        import yaml
        from data_sheets_schema.provenance import CONCAT_DIR
        named = []
        for rec in CONCAT_DIR.glob("*_core/*/*_provenance.yaml"):
            data = yaml.safe_load(rec.read_text(encoding="utf-8")) or {}
            if "generic_v5" in str(data.get("condition") or ""):
                named.append(rec.parts[-2])
        self.assertEqual(named, [])

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
        from data_sheets_schema.runs import canonical_sets
        runs = {(rt, p): i for rt, found in canonical_sets().items() for p, i in found.items()}
        if not runs:
            self.skipTest("no canonical records on disk")
        for (_rt, project), info in runs.items():
            with self.subTest(project=project):
                status, why = canonical_prompt_status(
                    info["method"], info["label"], project)
                self.assertIn(status, ("canonical", "superseded"), why)
