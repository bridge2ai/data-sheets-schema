"""The four smaller defects from the Codex review, and #572.

Grouped because each is small; separated here by class so a failure names the
one that broke.
"""

import unittest
from pathlib import Path


class ProjectFilterTest(unittest.TestCase):
    """`--project VOICE` matched VOICE_PEDIATRIC (#580).

    A scoped `--overwrite` therefore rewrote records of a different project.
    Only noticed after it matters.
    """

    def test_the_filter_is_exact_not_a_prefix(self):
        import inspect

        from data_sheets_schema.cli.provenance import backfill_checks
        src = inspect.getsource(backfill_checks.callback)
        self.assertIn('p.name == f"{project}_provenance.yaml"', src)
        self.assertNotIn('startswith(f"{project}_")', src)

    def test_the_two_project_names_would_have_collided(self):
        self.assertTrue("VOICE_PEDIATRIC_provenance.yaml".startswith("VOICE_"))
        self.assertNotEqual("VOICE_PEDIATRIC_provenance.yaml",
                            "VOICE_provenance.yaml")


class PlannerTest(unittest.TestCase):
    """The free check that sizes a run must describe the requests it will make."""

    def _plan(self):
        from data_sheets_schema.api_runner import RunSpec, plan
        bundle = Path("data/preprocessed/concatenated/AI_READI_preprocessed.txt")
        if not bundle.exists():
            self.skipTest("AI_READI bundle not present in this checkout")
        return plan(RunSpec(project="AI_READI", arm="baseline",
                            method="claudecode_agent", bundle=bundle,
                            label="plan_test", condition="generic_v5"))

    def test_every_phase_is_costed_with_its_declared_inputs(self):
        """It carried a nine-character placeholder after phase 1 and nothing
        else ever, so `reconcile_core` and `report` were costed with nothing.
        """
        from data_sheets_schema.api_runner import PHASE_NEEDS
        for ph in self._plan()["phases"]:
            with self.subTest(phase=ph["phase"]):
                self.assertEqual(set(ph["carried"]),
                                 set(PHASE_NEEDS[ph["phase"]]))

    def test_reconcile_full_is_costed_with_the_core_record(self):
        """The change whose size was the open question (#568) — the planner
        could not see it at all."""
        phases = {p["phase"]: p for p in self._plan()["phases"]}
        carried = phases["reconcile_full"]["carried"]
        self.assertGreater(carried["Completed core record"], 1000)

    def test_later_phases_cost_more_than_the_first(self):
        phases = {p["phase"]: p["approx_input_tokens"] for p in self._plan()["phases"]}
        self.assertGreater(phases["reconcile_full"], phases["full"])

    def test_the_estimate_says_where_its_sizes_came_from(self):
        self.assertTrue(self._plan()["estimate_basis"])

    def test_cached_blocks_are_not_counted_twice(self):
        """`build_phase` starts the message parts with `list(cached)`, so the
        bundle was counted in both — the largest thing in the request."""
        from data_sheets_schema.api_runner import RunSpec, build_phase
        bundle = Path("data/preprocessed/concatenated/CHORUS_preprocessed.txt")
        if not bundle.exists():
            self.skipTest("CHORUS bundle not present in this checkout")
        req = build_phase(
            RunSpec(project="CHORUS", arm="baseline", method="claudecode_agent",
                    bundle=bundle, label="t", condition="generic_v5"),
            "full", carry={})
        cached_chars = sum(len(b.get("text", "")) for b in req.cached_blocks)
        message_chars = sum(len(x.get("text", ""))
                            for m in req.messages for x in m["content"])
        self.assertLessEqual(req.approx_tokens(),
                             (len(req.system) + message_chars) // 4 + 1)
        self.assertGreater(cached_chars, 0, "the fixture must have cached text")


class ReportPhaseTest(unittest.TestCase):
    """It was asked what changed and shown only the audit findings (#580)."""

    def test_it_receives_the_records_it_describes(self):
        from data_sheets_schema.api_runner import PHASE_NEEDS
        needs = PHASE_NEEDS["report"]
        self.assertIn("Reconciled full record", needs)
        self.assertIn("Completed core record", needs)

    def test_it_is_told_to_check_before_asserting(self):
        from data_sheets_schema.api_runner import PHASE_INSTRUCTIONS
        # Case-insensitive: the phrase became sentence-initial when #639
        # rewrote the instruction, and an assertion on the capitalisation of
        # prose fails for a reason that has nothing to do with the behaviour
        # it is guarding.
        text = PHASE_INSTRUCTIONS["report"].lower()
        self.assertIn("check each statement against them", text)
        self.assertIn("still present", text)

    def test_it_is_given_both_sides_of_the_diff_and_told_to_use_them(self):
        """#639. The instruction and the inputs have to agree.

        Asking for a change account while supplying only after-states is what
        both readiness reviews found; supplying the before-states without
        telling the phase they are there would be the same defect with the
        halves swapped.
        """
        from data_sheets_schema.api_runner import (PHASE_INSTRUCTIONS,
                                                   PHASE_NEEDS)
        for key in ("Original full record", "Original core record"):
            self.assertIn(key, PHASE_NEEDS["report"])
        text = PHASE_INSTRUCTIONS["report"].lower()
        self.assertIn("original records", text)
        self.assertIn("compare them", text)

    def test_the_verdict_pins_the_records_and_the_schema(self):
        """A claim is checked *against* a record and a slot inventory, so a
        verdict pinned only to the report survives an edit to either."""
        from data_sheets_schema.api_runner import RunSpec, report_claims_block
        label = "2026-08-13_claude-opus-5-api-generic-v4_rep1"
        spec = RunSpec(project="CHORUS", arm="baseline",
                       method="claudecode_agent",
                       bundle=Path("data/preprocessed/concatenated/CHORUS_preprocessed.txt"),
                       label=label, condition="generic_v4")
        if not spec.report_path.exists():
            self.skipTest("v4 arm not present in this checkout")
        block = report_claims_block(spec)
        self.assertEqual(set(block["artifacts"]), {"report", "full", "core"})
        self.assertEqual(set(block["schema"]), {"full_sha256", "core_sha256"})


class SchemaMovedNarrowingTest(unittest.TestCase):
    """`schema_moved` excused every presence mismatch (#580).

    It is true whenever the digest differs at all, so an unrelated schema edit
    suppressed real defects. The ledger records which slots each digest had.
    """

    def _report(self, **kw):
        from data_sheets_schema.d4d_pair_consistency import (load_pair_schema,
                                                             validate_pair_data)
        from data_sheets_schema.provenance import CORE_SCHEMA, FULL_SCHEMA
        pair = load_pair_schema(FULL_SCHEMA, CORE_SCHEMA)
        return validate_pair_data({"related_datasets": [{"id": "x"}]}, {},
                                  pair, **kw)

    def test_a_slot_that_existed_at_the_run_digest_stays_an_error(self):
        from data_sheets_schema import schema_digest as sd
        sd.record_inventory()
        today = sd.fingerprint(sd.digest_text("Dataset"))
        r = self._report(schema_moved=True, run_digest=today)
        self.assertFalse(r.passed)

    def test_an_unrecorded_digest_falls_back_to_the_broad_rule(self):
        """Not a guess. An unknown digest cannot show the slot existed, and
        inventing an answer would fail history retroactively."""
        r = self._report(schema_moved=True, run_digest="deadbeefdeadbeef")
        self.assertTrue(r.passed)
        self.assertEqual(len(r.warnings), 1)

    def test_without_a_digest_the_behaviour_is_unchanged(self):
        self.assertTrue(self._report(schema_moved=True).passed)

    def test_the_ledger_is_append_only_per_digest(self):
        from data_sheets_schema import schema_digest as sd
        self.assertFalse(sd.record_inventory(),
                         "a second call for the same digest must add nothing")


class PhaseLogExpectationTest(unittest.TestCase):
    """An agentic run that could have recorded phases and did not (#572)."""

    def test_the_statuses_are_four_not_three(self):
        from data_sheets_schema.runs import (PHASES_ABSENT, PHASES_API,
                                             PHASES_MISSING, PHASES_RECORDED)
        self.assertEqual(len({PHASES_ABSENT, PHASES_API, PHASES_MISSING,
                              PHASES_RECORDED}), 4)

    def test_a_record_predating_the_feature_is_not_a_defect(self):
        """Calling honest history a defect is the error #400 avoided for
        reasoning logs."""
        from data_sheets_schema.runs import PHASE_LOG_SINCE
        self.assertEqual(PHASE_LOG_SINCE, "2026-08-15")

    def test_existing_agentic_records_are_absent_not_missing(self):
        from data_sheets_schema.runs import PHASES_MISSING, phase_log_status
        status, _ = phase_log_status(
            "claudecode_agent",
            "2026-08-11_claude-opus-5-claudecode-generic_rep1", "AI_READI")
        self.assertNotEqual(status, PHASES_MISSING)


if __name__ == "__main__":
    unittest.main()
