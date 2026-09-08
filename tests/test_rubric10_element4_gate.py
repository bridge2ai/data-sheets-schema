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

    def _gated_sub_elements(self, condition):
        """Which Element 4 sub-elements the conditions table says a condition
        gates. Derived from the table, so the prose is checked against what
        the table actually claims rather than against a literal I chose."""
        row = self._row(condition)
        cell = row.split("|")[3]
        if "all 5" in cell:
            return {1, 2, 3, 4, 5}
        m = re.search(r"sub-elements? (\d)\s*[–-]\s*(\d)", cell)
        self.assertTrue(m, f"cannot read the gated sub-elements from {cell!r}")
        return set(range(int(m.group(1)), int(m.group(2)) + 1))

    def test_the_prose_matches_whatever_the_table_says_governance_gates(self):
        """The property, not the wording (#1075): read the gated set off the
        table, then require exactly those sub-elements to offer the governance
        route in their own prose. A consistent rewording passes; a table and a
        prose that disagree fail, whichever of them moved."""
        gated = self._gated_sub_elements("Governance restrictions")
        for n, applies in self._applies_to().items():
            offers = "governance constraint that applies" in applies
            with self.subTest(sub_element=n, gated=n in gated):
                self.assertEqual(offers, n in gated,
                                 f"sub-element {n}: table says gated={n in gated}, "
                                 f"prose offers the route={offers}")

    def test_no_instruction_says_the_element_is_all_or_nothing(self):
        """The first fix failed because a second statement of the rule sat
        above the prose; a third sat five lines from the corrected table, an
        example reading 'no human subjects → Element 4 sub-elements are not
        applicable' unqualified (#1075). Any sentence that scopes an
        applicability verdict to Element 4 as a whole is that defect."""
        #: Line-wise, not sentence-wise: the offending example carried no
        #: full stop, so a sentence split walked straight past it.
        for raw in self.text.splitlines():
            line = re.sub(r"\s+", " ", raw)
            if "Element 4" in line and "not applicable" in line:
                with self.subTest(line=line.strip()[:80]):
                    self.assertTrue(
                        re.search(r"sub-elements? ?[1-5]\s*[–-]\s*[1-5]", line),
                        f"an unscoped Element 4 applicability claim: "
                        f"{line.strip()[:170]!r}")

    def _applies_to(self):
        e4 = self.text.split("### Element 4:", 1)[1].split("### Element 5:", 1)[0]
        subs = re.split(r"^\d+\. \*\*", e4, flags=re.M)[1:]
        self.assertEqual(len(subs), 5, "expected five sub-elements")
        return {n: re.sub(r"\s+", " ", b.split("**Applies to:**", 1)[1])
                for n, b in enumerate(subs, start=1)}

    def test_the_anti_circular_rule_is_told_it_does_not_resurrect_the_condition(self):
        """A round-0 evaluator argued the anti-circular rule forced the
        participant sub-elements applicable, since the record's own
        no-human-subjects determination sits in an Element 4 field. The
        ambiguity rule got an explicit carve-out; this one needed the same."""
        self.assertIn("does not resurrect a condition that fails", self.flat)

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


class TestTheSoftwareThresholdNamesItsFailureMode(unittest.TestCase):
    """#1059 round 3. The threshold first said a tooling slot could be
    `external_resources` "pointing at a code repository", and a rescore
    awarded the point for a link to a GitHub *organisation* — the very
    evidence five sibling evaluations had scored 0 on, and which the record
    pairs with "produced by a combination of automated and custom
    processing". A category is not a rule until it names what falls outside
    it."""

    def setUp(self):
        self.flat = re.sub(r"\s+", " ", AGENT.read_text(encoding="utf-8"))

    def test_a_publisher_level_pointer_does_not_qualify(self):
        self.assertIn("must identify the software, not its publisher", self.flat)
        for probe in ("organisation or account root", "project homepage",
                      "released via GitHub"):
            self.assertIn(probe, self.flat)

    def test_what_does_qualify_is_stated_too(self):
        """A rule that only forbids leaves the scorer guessing at the pass
        condition, which is how the first version produced a 0 and a 1 on one
        record."""
        self.assertIn("A repository, a package, an archived release or a "
                      "software DOI scores 1", self.flat)


if __name__ == "__main__":
    unittest.main()
