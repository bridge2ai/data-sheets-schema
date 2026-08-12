"""Compensation and retention incentives are separate claims (#504).

From Camille Nebeker's review: *"For compensation, the goal should be to
represent as incentives to prevent dropout of participants. Deemphasize
compensation itself and replace with incentives."*

**Widened rather than renamed.** Renaming `compensation_*` would move the schema
digest and orphan the values already in the corpus, and — worse — it would make
a record report a payment as a retention design when the source says only that a
payment was made. The evidence usually says "compensation"; re-framing it is the
`target` failure the fitness axis names.

So the two live side by side, and these tests hold that they stay distinguishable.
"""

import unittest
from pathlib import Path

from linkml_runtime import SchemaView

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"

COMPENSATION = ("compensation_provided", "compensation_type",
                "compensation_amount", "compensation_rationale")
RETENTION = ("retention_incentives", "retention_incentive_rationale")


class TestBothVocabulariesExist(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.view = SchemaView(str(FULL))
        cls.slots = {s.name: s for s in
                     cls.view.class_induced_slots("HumanSubjectCompensation")}

    def test_the_compensation_slots_survive(self):
        """The whole point of widening rather than renaming. If these ever
        disappear, existing values are orphaned and every record that reports a
        payment has nowhere honest to put it."""
        for slot in COMPENSATION:
            with self.subTest(slot=slot):
                self.assertIn(slot, self.slots)

    def test_the_retention_slots_exist(self):
        for slot in RETENTION:
            with self.subTest(slot=slot):
                self.assertIn(slot, self.slots)

    def test_structure_and_rationale_are_separate(self):
        """What was done and why it was done are different claims, and sources
        frequently give one without the other — the same reason
        `compensation_rationale` is separate from `compensation_amount`."""
        self.assertIn("retention_incentives", self.slots)
        self.assertIn("retention_incentive_rationale", self.slots)

    def test_the_retention_slots_have_their_own_uris(self):
        """Reusing a compensation URI would erase the distinction downstream,
        where a consumer sees the URI and not the slot name."""
        uris = {self.slots[s].slot_uri for s in RETENTION}
        comp = {self.slots[s].slot_uri for s in COMPENSATION}
        self.assertEqual(uris & comp, set())
        self.assertEqual(len(uris), len(RETENTION))

    def test_nothing_is_required(self):
        """A source that reports only a payment must produce a valid record.
        Requiring a retention slot would force a run to invent intent."""
        for slot in RETENTION:
            with self.subTest(slot=slot):
                self.assertFalse(self.slots[slot].required)


class TestTheDescriptionsForbidInference(unittest.TestCase):
    """The instruction half. Without it the schema invites exactly the error
    the review would create: reading an escalating payment schedule as evidence
    of retention design."""

    @classmethod
    def setUpClass(cls):
        cls.view = SchemaView(str(FULL))
        cls.slots = {s.name: s for s in
                     cls.view.class_induced_slots("HumanSubjectCompensation")}

    def test_the_class_says_the_two_must_not_be_conflated(self):
        text = self.view.get_class("HumanSubjectCompensation").description
        self.assertIn("must not be conflated", text)

    def test_the_class_names_both_concepts(self):
        text = self.view.get_class("HumanSubjectCompensation").description.lower()
        self.assertIn("compensation", text)
        self.assertIn("retention", text)

    def test_retention_incentives_says_not_to_infer_from_a_schedule(self):
        text = self.slots["retention_incentives"].description
        self.assertIn("not by itself evidence", text)

    def test_it_says_where_to_put_the_schedule_instead(self):
        """A rule that says only "do not" leaves the run with nowhere to put a
        true fact, which is how content gets dropped."""
        text = self.slots["retention_incentives"].description
        self.assertIn("compensation slots", text)


class TestTheChangeIsAdditive(unittest.TestCase):
    def test_no_compensation_slot_was_renamed_or_deprecated(self):
        view = SchemaView(str(FULL))
        slots = {s.name: s for s in
                 view.class_induced_slots("HumanSubjectCompensation")}
        for slot in COMPENSATION:
            with self.subTest(slot=slot):
                self.assertFalse(getattr(slots[slot], "deprecated", None),
                                 "compensation is still the right slot when "
                                 "the source reports only a payment")
