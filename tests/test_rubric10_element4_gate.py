"""Element 4's applicability is stated once and consistently (#1060).

Six evaluations of one cell-line project split on this gate: two scored the
element out of 50, four excluded it and scored out of 45, and the difference
set CM4AI's v7 rubric10 minimum, which prediction 8's CM4AI verdict rests on.

The first fix edited the per-sub-element prose and did not hold: the agent
carries an authoritative conditions table above it that still mapped both
conditions to all five sub-elements, and two rescored evaluations resolved
"the shared condition list once" from that table. Two statements of one rule,
and the reader followed the one this test did not exist to check.

So the property is agreement, not wording: whatever the table says about
which sub-elements a condition gates, the prose beneath must not contradict.
"""
import re
import unittest
from pathlib import Path

AGENT = (Path(__file__).resolve().parents[1] / ".claude" / "agents"
         / "d4d-rubric10-semantic.md")


class TestTheGateIsStatedOnce(unittest.TestCase):
    def setUp(self):
        self.text = AGENT.read_text(encoding="utf-8")
        #: The file wraps at 78 columns, so a phrase to be searched for is
        #: joined first — the same reason the prompt tests normalise.
        self.flat = re.sub(r"\s+", " ", self.text)

    def _row(self, condition):
        for line in self.text.splitlines():
            if line.strip().startswith(f"| {condition} "):
                return line
        self.fail(f"no conditions-table row for {condition!r}")

    def test_the_table_scopes_governance_to_the_oversight_sub_elements(self):
        row = self._row("Governance restrictions")
        self.assertIn("sub-elements 1–2", row)
        self.assertNotIn("all 5 sub-elements", row)

    def test_the_table_keeps_human_subjects_on_all_five(self):
        """The participant sub-elements are gated by this condition alone,
        so it must still reach every one of them."""
        self.assertIn("all 5 sub-elements", self._row("Human subjects"))

    def test_the_participant_sub_elements_do_not_offer_the_governance_route(self):
        """Sub-elements 3, 4 and 5 ask about participants. If their prose
        still carried the governance disjunct, a dataset with none would be
        scored 0 on three counts for not having them."""
        e4 = self.text.split("### Element 4:", 1)[1].split("### Element 5:", 1)[0]
        subs = re.split(r"^\d+\. \*\*", e4, flags=re.M)[1:]
        self.assertEqual(len(subs), 5, "expected five sub-elements")
        for n, body in enumerate(subs[2:], start=3):
            with self.subTest(sub_element=n):
                applies = re.sub(r"\s+", " ", body.split("**Applies to:**", 1)[1])
                self.assertNotIn("indicate governance constraints", applies)
                self.assertIn("not a participant signal", applies)

    def test_the_oversight_sub_elements_keep_it_and_say_what_counts(self):
        e4 = self.text.split("### Element 4:", 1)[1].split("### Element 5:", 1)[0]
        subs = re.split(r"^\d+\. \*\*", e4, flags=re.M)[1:]
        for n, body in enumerate(subs[:2], start=1):
            with self.subTest(sub_element=n):
                applies = re.sub(r"\s+", " ", body.split("**Applies to:**", 1)[1])
                self.assertIn("governance constraint that applies", applies)
                self.assertIn("no restriction applies is not a constraint", applies)

    def test_the_ambiguity_rule_is_told_it_does_not_reach_a_plain_failure(self):
        """The ambiguity rule resolves a borderline condition toward
        applicable. One rescore invoked it to score all five on a project
        whose human-subjects condition plainly fails, so the interaction is
        stated rather than left to be inferred."""
        self.assertIn("plainly fails is not borderline", self.flat)
        self.assertIn("a governance constraint does not make it fire", self.flat)


if __name__ == "__main__":
    unittest.main()
