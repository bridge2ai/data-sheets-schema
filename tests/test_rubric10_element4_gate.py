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


class TestTheSoftwareSubElementIsStatedOnce(unittest.TestCase):
    """#1059, after four rounds and a Codex review (#1081, #1082, #1084).

    Round 1 named the qualifying slots and a rescore awarded the point for a
    GitHub organisation root. Round 3 barred publisher-level pointers, which
    would have flipped three CHORUS records. Round 4 wrote the applicability
    rule as a new paragraph and left two older gate texts standing that said
    the opposite, so several rescores recorded `match: false` and applied the
    launcher's quoted rule instead of the checked-in one.

    The tests that guarded round 4 were whole-file substring searches. They
    passed with the contradiction in place, and would have passed had "Score 0"
    become "Score 1". So these read the sub-element's own block, check that no
    other text in the file re-imposes the gate it drops, and check the
    polarity of the failure list rather than the presence of its phrases.
    """

    def setUp(self):
        self.text = AGENT.read_text(encoding="utf-8")
        self.flat = re.sub(r"\s+", " ", self.text)
        element = self.text.split("### Element 8:", 1)[1].split("### Element 9:", 1)[0]
        # The next item's source-aligned title changed in #158. Locate the
        # numbered item within E8 so every software assertion still executes.
        self.block = re.split(r"^4\. \*\*", element, flags=re.M)[1]
        self.block = re.split(r"^5\. \*\*", self.block, flags=re.M)[0]
        self.block_flat = re.sub(r"\s+", " ", self.block)

    def _row(self, condition):
        for line in self.text.splitlines():
            if line.strip().startswith(f"| {condition} "):
                return line
        self.fail(f"no conditions-table row for {condition!r}")

    def test_preprocessing_has_its_own_gate_independent_of_released_software(self):
        """#1414: processing documentation applies without a software output."""
        row = self._row("Data processing")
        gates = row.rsplit("|", 2)[1]
        self.assertIn("sub-element 3", gates)
        self.assertNotIn("3–4", gates)
        self.assertNotIn("3-4", gates)
        self.assertNotIn("Software tools produced as dataset output", self.text)
        element = self.text.split("### Element 8:", 1)[1].split("### Element 9:", 1)[0]
        processing = re.split(r"^3\. \*\*", element, flags=re.M)[1]
        processing = re.split(r"^4\. \*\*", processing, flags=re.M)[0]
        self.assertIn("data_processing predicate", processing)
        self.assertNotIn("only score if `external_resources`", processing)
        self.assertIn("sub-element 4", self._row("Processing software"))

    def test_nothing_in_the_block_re_imposes_the_repository_gate(self):
        """The unchanged local `Applies to` restored the very gate the
        applicability paragraph drops, three bullets above it."""
        self.assertNotIn("only score if `external_resources`", self.block)
        self.assertNotIn("Do not use E8's own fields as the applicability signal",
                         self.block)

    def test_the_block_declares_only_fields_the_schema_has(self):
        """`software_and_tools` is not a slot in the D4D schema and appears in
        no record, so a rule written against it could never be satisfied."""
        self.assertNotIn("Fields: `software_and_tools`", self.block)
        self.assertIn("used_software", self.block)

    def test_the_rule_states_the_question_not_only_the_slots(self):
        self.assertIn("what software **produced or transformed the data being "
                      "distributed**", self.block_flat)

    def test_the_failure_list_scores_zero_not_one(self):
        """A polarity check: the round-4 tests searched for the case phrases
        and would have passed had the sentence introducing them been negated."""
        self.assertIn("Score 0 whenever no such software is named", self.block_flat)
        self.assertNotIn("Score 1 whenever no such software is named",
                         self.block_flat)

    def test_every_role_that_does_not_answer_the_question_is_named(self):
        """The rule has to be total over what software can have done to the
        released data: packaging and quality assessment fell outside the three
        cases round 4 named, and one record drew both a 0 and a 1 for the
        same packaging evidence (#1082)."""
        roles = re.findall(r"- \(([a-e])\) \*\*(.+?)\*\*", self.block_flat)
        self.assertEqual([r[0] for r in roles], ["a", "b", "c", "d", "e"],
                         f"roles found: {roles}")
        named = " ".join(r[1] for r in roles)
        for probe in ("capture", "hosting", "packaging", "validation"):
            self.assertIn(probe, named)
        self.assertIn("outputs that are not in this release", self.block_flat)

    def test_a_publisher_pointer_neither_earns_nor_forfeits_the_point(self):
        """Round 3 made an organisation root a hard 0, which would have
        flipped three CHORUS records whose tooling is named in prose. The
        pointer is not the evidence; the name is."""
        self.assertIn("neither earns nor forfeits the point on its own",
                      self.block_flat)

    def test_applicability_does_not_depend_on_the_pointer(self):
        """Gating on a referenced repository would excuse a record that
        documents no tooling by that very silence."""
        self.assertIn("is **not** gated on whether a repository is pointed at",
                      self.block_flat)
        self.assertIn("processing_software predicate", self.block_flat)
        self.assertIn("Missing scoring fields never establish false", self.block_flat)


if __name__ == "__main__":
    unittest.main()
