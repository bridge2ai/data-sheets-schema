"""What must reach the exchange layer, and why (#510).

`CoreDataset` carried two of the three Data Governance classes and not the
third, and had no `related_datasets` at all. Neither omission was decided; both
were the residue of adding slots one at a time, each time keeping the blast
radius small. The asymmetry accumulated because nobody was asked the general
question.

**The position these tests encode: the core record is for deciding whether to
ingest a dataset, not only for describing one already ingested.** The evidence
is what core already carried before this change — `license_and_use_terms` (may
I use it), `regulatory_restrictions` (what law applies), `conforms_to` on
`CoreDistribution` (#403, can I read it). Every one is an ingest-decision fact.
Access governance is the same kind of fact and arguably the most decisive: a
consumer who cannot find out who grants access cannot obtain the data at all.

The tests are written against that position rather than against the slot list,
so if the position is ever reversed the failure says which claim was abandoned.
"""

import unittest
from pathlib import Path

from linkml_runtime import SchemaView

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"
FULL = ROOT / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"

#: The Data Governance module's three top-level classes as they attach to a
#: dataset. Named, not counted — a count would pass if one were swapped out.
GOVERNANCE = {
    "license_and_use_terms": "what the licence permits",
    "regulatory_restrictions": "which regulations apply",
    "data_governance": "who decides access, and how",
}


class TestGovernanceReachesCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = {s.name for s in
                    SchemaView(str(CORE)).class_induced_slots("CoreDataset")}
        cls.full = {s.name for s in
                    SchemaView(str(FULL)).class_induced_slots("Dataset")}

    def test_all_three_governance_slots_are_in_core(self):
        for slot, what in GOVERNANCE.items():
            with self.subTest(slot=slot):
                self.assertIn(slot, self.core,
                              f"core cannot say {what}")

    def test_an_ingest_decision_cannot_be_made_without_them(self):
        """Stated as the whole set rather than three separate facts.

        Two of three is the state this issue was filed about, and it is worse
        than none: a reader who finds licence terms and regulations present
        reasonably infers governance was considered and found absent, rather
        than never expressible.
        """
        self.assertEqual(set(GOVERNANCE) & self.core, set(GOVERNANCE))

    def test_related_datasets_can_express_a_scope_relation(self):
        """`source_manifest.yaml` names `related_datasets` in `express_as` for
        a related-but-distinct dataset. Without it in core, a core record could
        not state its own declared scope relation — VOICE_PEDIATRIC is in scope
        by `id` while a core-only reader cannot see the distinct adult dataset.
        """
        self.assertIn("related_datasets", self.core)

    def test_core_stays_a_subset_of_full(self):
        """The direction that must not reverse. Core is a projection of the
        full record; a slot in core and not in full would be unprojectable and
        could only be authored by hand.

        Two exceptions are declared, not discovered: `CoreDistribution` and
        `FormatDialect` group full-schema slots that live on other classes.
        """
        core_only = self.core - self.full - {"distributions", "dialect"}
        self.assertEqual(core_only, set())


class TestTheRelationIsIdentityNotProjection(unittest.TestCase):
    """A fact that appears in both records must appear identically.

    `resources` is the one projected slot — its range differs between the two
    schemas, so full and core legitimately state it differently. Governance and
    relations are not like that: they are the same fact, and a pair disagreeing
    about who runs the access committee is a defect rather than a projection.
    """

    @classmethod
    def setUpClass(cls):
        from data_sheets_schema.d4d_pair_consistency import load_pair_schema
        cls.pair = load_pair_schema(FULL, CORE)

    def test_governance_and_relations_are_identity_slots(self):
        for slot in (*GOVERNANCE, "related_datasets"):
            with self.subTest(slot=slot):
                self.assertIn(slot, self.pair.identity_slots)

    def test_resources_is_still_the_only_projected_slot(self):
        """If a second projected slot ever appears, it is a decision someone
        made about what core is for, and it should not arrive silently."""
        self.assertEqual(("resources",), self.pair.projected_slots)


class TestTheRangesResolve(unittest.TestCase):
    """A slot whose range is not reachable from the core schema would generate
    but not validate — the failure would surface on the first record that used
    it, not here."""

    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(CORE))

    def test_data_governance_resolves_to_a_class_with_a_committee(self):
        cls = self.sv.get_class("DataGovernance")
        self.assertIsNotNone(cls, "DataGovernance unreachable from core")
        attrs = {s.name for s in self.sv.class_induced_slots("DataGovernance")}
        for expected in ("committee_name", "committee_contact",
                        "access_review_process", "accountable_organization"):
            with self.subTest(attr=expected):
                self.assertIn(expected, attrs)

    def test_related_datasets_resolves_to_a_typed_relationship(self):
        """Untyped relations are the failure this range prevents: a bare list
        of ids says two datasets are connected and never how."""
        cls = self.sv.get_class("DatasetRelationship")
        self.assertIsNotNone(cls, "DatasetRelationship unreachable from core")
