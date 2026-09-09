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
        self.assertEqual(a["values"]["condition"], ["generic_v4"])      # from the hashed v4 prompt: records predate #1094

    def test_two_arms_differ_on_condition(self):
        a, b = arm_facts(V4), arm_facts("2026-08-20b_claude-opus-5-api-generic-v5")
        if not (a["labels"] and b["labels"]):
            self.skipTest("v4 or v5 arm not present in this checkout")
        fields = {c["field"] for c in arm_confounds(a, b)}
        self.assertIn("condition", fields)

    def test_a_record_the_evidence_contradicts_is_named_with_the_source(self):
        from data_sheets_schema.runs import condition_contradiction, condition_unfalsifiable
        label = "2026-08-13_claude-opus-5-api-generic-v4_rep1"
        self.assertIsNone(condition_contradiction({"run": {}}, label))                # states none (pre-#1094)
        self.assertIsNone(condition_contradiction({"run": {"condition": "generic_v4"}}, label))
        got = condition_contradiction({"run": {"condition": "generic_v5", "condition_basis": "stated by the runner"}}, label)
        self.assertEqual((got["record"], got["disagrees_with"]), ("generic_v5", {"label": "generic_v4"}))
        # the strong comparison: the prompt the record hashed (the #420 shape)
        v1 = {"run": {"condition": "generic_v3"},
              "prompts": {"files": [{"path": "src/download/prompts/d4d_generic_arm_prompt.md"}]}}
        got = condition_contradiction(v1, "2026-08-07_claude-opus-5-claudecode-generic-v3_rep2")
        self.assertEqual(got["disagrees_with"], {"hashed prompt": "generic"})
        # an unregistered condition is a finding whatever the label says
        got = condition_contradiction({"run": {"condition": "generic_v99"}}, "2026-07-27_claude-opus-5_rep1")
        self.assertEqual(got["disagrees_with"], {"registry": "not a registered condition"})
        self.assertIsNone(condition_contradiction({"run": "not a mapping"}, label))    # a gate input read from disk
        # stated, and nothing to check it against: reported, never failed
        self.assertTrue(condition_unfalsifiable({"run": {"condition": "generic_v2"}}, "2026-07-27_claude-opus-5_rep1"))
        self.assertFalse(condition_unfalsifiable({"run": {"condition": "generic_v2"}}, "2026-07-31_x-generic-v2_rep1"))

    def test_the_record_claims_its_condition_from_the_strongest_source(self):
        from data_sheets_schema.provenance import _condition_claim
        self.assertEqual(_condition_claim("2026-08-13_x-api-generic-v4_rep1", "generic_v4"),
                         {"condition": "generic_v4", "condition_basis": "stated by the runner"})
        # a runner statement is recorded as stated even where the label disagrees: the gate's job, not the claim's
        self.assertEqual(_condition_claim("2026-08-13_x-api-generic-v4_rep1", "generic_v5")["condition"], "generic_v5")
        # the hashed prompt outranks the label (the #420 shape: labelled v3, hashed v1)
        c = _condition_claim("2026-08-07_x-claudecode-generic-v3_rep2", None,
                             ["src/download/prompts/d4d_generic_arm_prompt.md"])
        self.assertEqual((c["condition"], c["condition_basis"]),
                         ("generic", "read from the prompt file the record hashes; no runner stated it"))
        self.assertEqual(_condition_claim("2026-08-13_x-api-generic-v4_rep1", None)["condition_basis"],
                         "read from the label; no runner stated it and no prompt file names one")
        self.assertIsNone(_condition_claim("2026-07-27_claude-opus-5_rep1", None)["condition"])
        self.assertEqual(_condition_claim("2026-07-27_x_rep1", "  ")["condition"], None)   # empty is not a statement

    def test_a_label_names_a_condition_only_as_a_delimited_registered_token(self):
        """#1094 review, N8."""
        from data_sheets_schema.runs import condition_from_label
        self.assertEqual(condition_from_label("2026-08-13_claude-opus-5-api-generic-v4_rep1"), "generic_v4")
        self.assertEqual(condition_from_label("2026-07-29_claude-opus-5-api-generic_rep1"), "generic")
        self.assertIsNone(condition_from_label("2026-09-09_x-api-generic-v99_rep1"))     # not registered: not its prefix
        self.assertIsNone(condition_from_label("someone-untuned-thing"))
        self.assertIsNone(condition_from_label("2026-09-09_x-api-generic-tuned_rep1"))   # ambiguous
        self.assertEqual(condition_from_label("2026-07-27_x-tuned_rep1"), "tuned")

    def test_arm_facts_reads_a_recorded_condition_before_falling_back(self):
        """No corpus record carries the key yet (review N3): a temp arm does."""
        import tempfile
        import yaml
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rep, cond in ((1, "generic_v9"), (2, None)):
                d = root / "claudecode_api_core" / f"2026-09-09_x-api-generic-v9_rep{rep}"; d.mkdir(parents=True)
                run = {"label": d.name}
                if cond:
                    run["condition"] = cond
                (d / "CHORUS_provenance.yaml").write_text(yaml.safe_dump(
                    {"run": run, "prompts": {"files": [{"path": "src/download/prompts/d4d_generic_arm_prompt_v9.md"}]}}))
            facts = arm_facts("2026-09-09_x-api-generic-v9", method="claudecode_api", concat_dir=root)
            self.assertEqual(facts["values"]["condition"], ["generic_v9"])   # rep1 from the record, rep2 from its prompt

    def test_the_strict_gate_and_the_launch_refusal_are_wired(self):
        import inspect
        from pathlib import Path
        import click
        from data_sheets_schema.cli import api as api_cli, runs as runs_cli
        src = inspect.getsource(runs_cli.check_cmd.callback)
        self.assertIn("or condition_contradictions", src)
        self.assertIn("condition_unfalsifiable(", src)
        self.assertIn("_refuse_condition_mismatch(spec, allow_condition_mismatch)", inspect.getsource(api_cli.run_cmd.callback))
        self.assertIn("_refuse_condition_mismatch(s, allow_condition_mismatch)", inspect.getsource(api_cli.batch_cmd.callback))
        from data_sheets_schema.api_runner import RunSpec
        spec = RunSpec(project="CHORUS", arm="baseline", method="claudecode_api", bundle=Path("x"),
                       label="2026-09-10_claude-opus-5-api-generic-v9_rep1", condition="generic", condition_stated=False)
        with self.assertRaises(click.ClickException) as cm:
            api_cli._refuse_condition_mismatch(spec, allow=False)
        self.assertIn("the default; no --condition given", str(cm.exception))
        api_cli._refuse_condition_mismatch(spec, allow=True)                                   # deliberate
        self.assertTrue(spec.condition_mismatch_allowed)                                        # and recorded
        from data_sheets_schema.runs import condition_contradiction
        declared = {"run": {"condition": "generic_v5", "condition_mismatch_allowed": True},
                    "prompts": {"files": [{"path": "src/download/prompts/d4d_generic_arm_prompt_v5.md"}]}}
        cc = condition_contradiction(declared, "2026-09-10_x-api-generic-v8_rep1")
        self.assertTrue(cc["declared"])                                                          # label only: reported
        undeclared = {"run": {"condition": "generic_v5"}, "prompts": declared["prompts"]}
        self.assertFalse(condition_contradiction(undeclared, "2026-09-10_x-api-generic-v8_rep1")["declared"])
        wrong_prompt = {"run": {"condition": "generic_v5", "condition_mismatch_allowed": True},
                        "prompts": {"files": [{"path": "src/download/prompts/d4d_generic_arm_prompt.md"}]}}
        self.assertFalse(condition_contradiction(wrong_prompt, "2026-09-10_x-api-generic-v8_rep1")["declared"])  # prompt: fatal
        self.assertIn("_refuse_condition_mismatch(spec, allow_condition_mismatch)",
                      inspect.getsource(api_cli.render_prompt_cmd.callback))                   # the agentic launch instrument
        api_cli._refuse_condition_mismatch(RunSpec(project="CHORUS", arm="baseline", method="claudecode_api",
                                                   bundle=Path("x"), label="2026-09-10_x-api-generic-v9_rep1",
                                                   condition="generic_v9"), allow=False)      # agrees
