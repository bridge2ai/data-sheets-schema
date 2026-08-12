"""A slot that describes the record is exempt from strict identity (#499).

`conforms_to_schema` and `conforms_to_class` describe the record they sit in,
so their correct values necessarily differ between a full/core pair — `Dataset`
in one and `CoreDataset` in the other. Both were strict-identity slots, which
made them unrepresentable: any honest population failed the pair check, and
`--sync-core` copied full's value into core and wrote a false claim about what
the core record instantiates.

The AI_READI run of the 2026-08-11 sweep hit this in phase 4 and resolved it by
omitting the slot from both records — the only state that neither fails the gate
nor asserts something false.

`conforms_to` is *correctly* strict-identity: a standard the dataset's content
follows is a fact about the dataset and is the same in both records. The tests
below hold that distinction from both sides, because an exemption that leaked
to `conforms_to` would silently stop checking a real fact.
"""

import unittest
from pathlib import Path

from linkml_runtime.linkml_model.meta import SlotDefinition

from data_sheets_schema.d4d_pair_consistency import (
    PER_RECORD_ANNOTATION,
    _is_per_record,
    load_pair_schema,
    synchronize_core_data,
    validate_pair_data,
)

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
CORE = ROOT / "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"

PER_RECORD = ("conforms_to_class", "conforms_to_schema")


def _pair(**core_over):
    full = {"id": "https://e.org/d", "name": "x",
            "conforms_to_class": "Dataset",
            "conforms_to_schema": "https://w3id.org/bridge2ai/data-sheets-schema",
            "conforms_to": "BIDS v1.9.0"}
    core = {**full, "conforms_to_class": "CoreDataset",
            "conforms_to_schema":
                "https://w3id.org/bridge2ai/data-sheets-schema/core-schema"}
    core.update(core_over)
    return full, core


class TestTheAnnotationIsActuallyRead(unittest.TestCase):
    """The bug that made the first version of this do nothing.

    `slot.annotations` is a `jsonasobj2.JsonObj`, which has no `.get`. The
    accessor called it inside `except AttributeError: return False`, so every
    slot read as unmarked, `per_record_slots` was empty, and the schema
    annotation was decorative. A check that cannot fail is worse than no check.
    """

    def test_a_marked_slot_reads_as_marked(self):
        slot = SlotDefinition("s", annotations={PER_RECORD_ANNOTATION: True})
        self.assertTrue(_is_per_record(slot))

    def test_an_unmarked_slot_does_not(self):
        self.assertFalse(_is_per_record(SlotDefinition("s")))

    def test_a_slot_with_other_annotations_does_not(self):
        slot = SlotDefinition("s", annotations={"d4d:docExample": "Dataset"})
        self.assertFalse(_is_per_record(slot))

    def test_explicit_false_is_not_a_marking(self):
        """Present-and-false must not mean the same as present-and-true."""
        for value in (False, "false", "no", ""):
            with self.subTest(value=value):
                slot = SlotDefinition(
                    "s", annotations={PER_RECORD_ANNOTATION: value})
                self.assertFalse(_is_per_record(slot))

    def test_it_reads_the_real_schema_not_only_fixtures(self):
        """The property the fixtures cannot establish: that the annotation as
        actually written in D4D_Base_import.yaml survives the merge and is
        found on the induced slot."""
        pair = load_pair_schema(FULL, CORE)
        self.assertEqual(sorted(pair.per_record_slots), sorted(PER_RECORD))


class TestTheExemptionApplies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pair = load_pair_schema(FULL, CORE)

    def test_an_honest_pair_now_passes(self):
        """`Dataset` in full and `CoreDataset` in core — both correct, and
        before this the only passing state was to omit them from both."""
        full, core = _pair()
        report = validate_pair_data(full, core, self.pair)
        self.assertEqual(report.errors, [])

    def test_per_record_slots_are_not_identity_slots(self):
        for slot in PER_RECORD:
            with self.subTest(slot=slot):
                self.assertNotIn(slot, self.pair.identity_slots)

    def test_sync_core_no_longer_overwrites_the_core_value(self):
        """The damaging half. `--sync-core` copying `Dataset` into a core
        record makes it claim to instantiate a class it does not."""
        full, core = _pair()
        synced = synchronize_core_data(full, dict(core), self.pair)
        out = synced[0] if isinstance(synced, tuple) else synced
        self.assertEqual(out.get("conforms_to_class"), "CoreDataset")
        self.assertIn("core-schema", out.get("conforms_to_schema", ""))


class TestTheExemptionDoesNotLeak(unittest.TestCase):
    """An over-broad exemption would stop checking a real fact, which is the
    more dangerous direction: it fails silently and forever."""

    @classmethod
    def setUpClass(cls):
        cls.pair = load_pair_schema(FULL, CORE)

    def test_conforms_to_is_still_strict_identity(self):
        self.assertIn("conforms_to", self.pair.identity_slots)
        self.assertNotIn("conforms_to", self.pair.per_record_slots)

    def test_a_disagreement_about_conforms_to_is_still_an_error(self):
        full, core = _pair(conforms_to="OMOP CDM v5.4")
        report = validate_pair_data(full, core, self.pair)
        self.assertTrue(
            any(i.path.endswith("conforms_to") for i in report.errors),
            "a dataset standard differing between the pair must still fail")

    def test_only_the_two_declared_slots_are_exempt(self):
        """If a third ever appears it is a decision someone made about what
        describes the record, and it should not arrive silently."""
        self.assertEqual(sorted(self.pair.per_record_slots), sorted(PER_RECORD))

    def test_the_three_categories_do_not_overlap(self):
        buckets = (set(self.pair.identity_slots),
                   set(self.pair.projected_slots),
                   set(self.pair.per_record_slots))
        for i, a in enumerate(buckets):
            for b in buckets[i + 1:]:
                self.assertEqual(a & b, set())
