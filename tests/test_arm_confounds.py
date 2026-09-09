"""What differs between two arms besides the condition (#576).

`comparable_conditions` reasons from condition *names*, so it reported
v4-against-v5 as an isolating comparison while the schema digest had moved
underneath it and `reconcile_full` had gained an input. Neither is visible in a
name.

This reads what the records state. v5 is a production run: the comparison is
reported with its confounds rather than presented as a measurement of the
prompt block.
"""

import unittest

from data_sheets_schema.runs import (
    ARM_PROCEDURE_FIELDS,
    arm_confounds,
    arm_facts,
)

V4 = "2026-08-13_claude-opus-5-api-generic-v4"
AGENTIC = "2026-08-11_claude-opus-5-claudecode-generic"


class ArmFactsTest(unittest.TestCase):

    def setUp(self):
        self.a = arm_facts(V4)
        if not self.a["labels"]:
            self.skipTest("v4 arm not present in this checkout")

    def test_it_reads_every_replicate_of_the_arm(self):
        self.assertEqual(len(self.a["labels"]), 3)
        self.assertEqual(len(self.a["projects"]), 4)

    def test_a_constant_field_has_one_value(self):
        """The v4 arm was deliberately generated at one digest."""
        self.assertEqual(self.a["values"]["schema digest"], ["622e6d037335ef0022c32974a21a714e"])

    def test_a_straddled_arm_shows_more_than_one(self):
        """#517: the 2026-08-11 agentic arm spans two schema digests, and this
        surfaces it without being told to look."""
        b = arm_facts(AGENTIC)
        if not b["labels"]:
            self.skipTest("agentic arm not present in this checkout")
        self.assertGreater(len(b["values"]["schema digest"]), 1)


class ConfoundTest(unittest.TestCase):

    def test_the_v4_and_agentic_arms_differ_on_schema_and_runtime(self):
        a, b = arm_facts(V4), arm_facts(AGENTIC)
        if not (a["labels"] and b["labels"]):
            self.skipTest("arms not present in this checkout")
        fields = {c["field"] for c in arm_confounds(a, b)}
        self.assertIn("schema digest", fields)
        self.assertIn("runtime", fields)

    def test_an_arm_against_itself_has_no_confounds(self):
        a = arm_facts(V4)
        if not a["labels"]:
            self.skipTest("v4 arm not present in this checkout")
        self.assertEqual(arm_confounds(a, a), [])

    def test_an_absent_arm_produces_no_false_confounds(self):
        """Missing evidence is not a difference. An empty side would otherwise
        report every field as differing, which reads as a confounded comparison
        when it is an unmeasured one."""
        a = arm_facts(V4)
        if not a["labels"]:
            self.skipTest("v4 arm not present in this checkout")
        self.assertEqual(arm_confounds(a, arm_facts("no-such-arm-prefix")), [])

    def test_the_fields_checked_are_the_ones_that_change_meaning(self):
        names = [n for n, _ in ARM_PROCEDURE_FIELDS]
        for expected in ("schema digest", "assembly digest", "condition"):
            self.assertIn(expected, names)


class ConditionComparabilityIsNotEnoughTest(unittest.TestCase):

    def test_a_true_from_comparable_conditions_does_not_settle_it(self):
        """The precise gap #576 was filed for."""
        from data_sheets_schema.api_runner import comparable_conditions
        self.assertTrue(comparable_conditions("generic_v4", "generic_v5"))
        a = arm_facts(V4)
        if not a["labels"]:
            self.skipTest("v4 arm not present in this checkout")
        # The v4 arm's own digest is not today's, so a v5 arm run now differs.
        from data_sheets_schema import schema_digest
        today = schema_digest.fingerprint(schema_digest.digest_text("Dataset"))
        self.assertNotIn(today, a["values"]["schema digest"])


class TestTheReviewerIsAConfound(unittest.TestCase):
    """#1097: the judge is part of the procedure.

    v7 was reviewed by `claude-fable-5` and v8 by `claude-fable-5-1`, and a
    reader running this tool on exactly the comparison that difference affects
    got a report that omitted it. The confound lived in the plan note's prose
    only, which is the failure `arm_confounds` exists to prevent.
    """

    def test_the_production_arms_differ_on_reviewer(self):
        from data_sheets_schema.runs import arm_confounds, arm_facts
        v7 = arm_facts("2026-09-01_claude-opus-5-api-generic-v7")
        v8 = arm_facts("2026-09-04g_claude-opus-5-api-generic-v8")
        if not (v7["labels"] and v8["labels"]):
            self.skipTest("the production records are not in this checkout")
        fields = [c["field"] for c in arm_confounds(v7, v8)]
        self.assertIn("reviewer", fields)

    def test_an_unreviewed_arm_is_not_reported_as_differing(self):
        """A stringified absence is not a reading. `arm_facts` turns a missing
        field into ["None"], and reporting that against an arm that has one
        would call an absence a difference — the error this whole function
        exists to avoid making about conditions."""
        from data_sheets_schema.runs import arm_confounds, arm_facts
        v4 = arm_facts("2026-08-13_claude-opus-5-api-generic-v4")
        v7 = arm_facts("2026-09-01_claude-opus-5-api-generic-v7")
        if not (v4["labels"] and v7["labels"]):
            self.skipTest("those arms are not in this checkout")
        self.assertEqual(v4["values"].get("reviewer"), ["None"],
                         "precondition: the v4 arm carries no review block")
        self.assertNotIn("reviewer",
                         [c["field"] for c in arm_confounds(v4, v7)])


if __name__ == "__main__":
    unittest.main()


class ConditionIsAFieldThatCanFire(unittest.TestCase):
    """#1094: the tuple read a top-level `condition` key no record has, so
    `arm_confounds` compared "None" with "None" and never reported a
    condition difference — the one field a reader of confounds would take
    as coverage of the thing the comparison is about."""

    def test_the_field_reads_run_condition_and_falls_back_to_the_label(self):
        self.assertIn(("condition", ("run", "condition")), ARM_PROCEDURE_FIELDS)
        a = arm_facts(V4)
        if not a["labels"]:
            self.skipTest("v4 arm not present in this checkout")
        self.assertEqual(a["values"]["condition"], ["generic_v4"])      # from the label: records predate #1094

    def test_two_arms_differ_on_condition(self):
        a, b = arm_facts(V4), arm_facts("2026-08-20b_claude-opus-5-api-generic-v5")
        if not (a["labels"] and b["labels"]):
            self.skipTest("v4 or v5 arm not present in this checkout")
        fields = {c["field"] for c in arm_confounds(a, b)}
        self.assertIn("condition", fields)

    def test_a_record_that_contradicts_its_label_is_named(self):
        from data_sheets_schema.runs import condition_contradiction
        label = "2026-08-13_claude-opus-5-api-generic-v4_rep1"
        self.assertIsNone(condition_contradiction({"run": {}}, label))                # states none (pre-#1094)
        self.assertIsNone(condition_contradiction({"run": {"condition": "generic_v4"}}, label))
        got = condition_contradiction({"run": {"condition": "generic_v5", "condition_basis": "stated by the runner"}}, label)
        self.assertEqual((got["record"], got["label_condition"]), ("generic_v5", "generic_v4"))

    def test_the_record_claims_its_condition_with_a_basis(self):
        from data_sheets_schema.provenance import _condition_claim
        self.assertEqual(_condition_claim("2026-08-13_x-api-generic-v4_rep1", "generic_v4"),
                         {"condition": "generic_v4", "condition_basis": "stated by the runner"})
        self.assertEqual(_condition_claim("2026-08-13_x-api-generic-v4_rep1", None)["condition_basis"],
                         "read from the label; no runner stated it")
        self.assertIsNone(_condition_claim("2026-07-27_claude-opus-5_rep1", None)["condition"])
