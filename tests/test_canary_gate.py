"""The first run of a sweep is held to a higher bar than the rest (#579).

`d4d api batch` counted a run as succeeded on schema validation alone, so a run
whose pair diverges, whose report contradicts its record, or which carries
identifiers absent from its bundle entered the "succeeded" column. That is how
the 2026-08-13 arm swept clean: twelve valid records, `runs check --strict` exit
0, eleven divergent pairs and twenty-nine ungrounded identifiers inside them.

The canary rule says one unit is verified before fanning out — but the canary's
verdict *was* the batch's verdict, and the batch did not look. A canary could
pass while showing exactly the defects the arm was built to fix.
"""

import unittest

from data_sheets_schema.canary import (
    OK,
    REGRESSED,
    UNMEASURABLE,
    baseline_for,
    counts_from,
    verdict,
)

BASELINE = "2026-08-13_claude-opus-5-api-generic-v4"

GOOD = {"pair": {"ran": True, "errors": 2},
        "report": {"checked": True, "findings": []},
        "grounding": {"checked": True, "distinct": {"absent": 0}}}


class CountsTest(unittest.TestCase):

    def test_a_check_that_did_not_run_counts_as_none_not_zero(self):
        """Zero is a measurement; None is the absence of one. Collapsing them
        is the mistake the grounding check itself made (#578)."""
        counts = counts_from({"pair": {"ran": False, "reason": "x"},
                              "report": {"checked": False},
                              "grounding": {"checked": False}})
        self.assertEqual(set(counts.values()), {None})

    def test_counts_are_read_from_each_block(self):
        self.assertEqual(counts_from(GOOD),
                         {"pair errors": 2, "report findings": 0,
                          "ungrounded identifiers": 0})


class BaselineTest(unittest.TestCase):

    def test_the_bar_is_the_worst_run_not_the_best(self):
        """The best would make ordinary replicate variance read as a
        regression, and this gate stops a paid sweep."""
        bar = baseline_for("AI_READI", BASELINE)
        if bar["pair errors"] is None:
            self.skipTest("v4 arm not present in this checkout")
        self.assertEqual(bar["pair errors"], 10)     # reps are 10, 8, 6
        self.assertEqual(bar["ungrounded identifiers"], 0)

    def test_voice_carries_its_own_ungrounded_baseline(self):
        """VOICE rep1's 19 ungrounded identifiers are in the baseline, so a v5
        VOICE run is not failed for inheriting them — only for exceeding."""
        bar = baseline_for("VOICE", BASELINE)
        if bar["ungrounded identifiers"] is None:
            self.skipTest("v4 arm not present in this checkout")
        self.assertEqual(bar["ungrounded identifiers"], 19)

    def test_an_unknown_project_yields_no_bar(self):
        self.assertEqual(set(baseline_for("NOPE", BASELINE).values()), {None})


class VerdictTest(unittest.TestCase):

    BAR = {"pair errors": 10, "report findings": 2,
           "ungrounded identifiers": 0}

    def test_no_worse_than_the_baseline_passes(self):
        self.assertEqual(verdict(GOOD, self.BAR)["status"], OK)

    def test_equalling_the_worst_baseline_is_not_a_regression(self):
        at_bar = {"pair": {"ran": True, "errors": 10},
                  "report": {"checked": True, "findings": [1, 2]},
                  "grounding": {"checked": True, "distinct": {"absent": 0}}}
        self.assertEqual(verdict(at_bar, self.BAR)["status"], OK)

    def test_one_metric_worse_stops_the_sweep(self):
        worse = {**GOOD,
                 "grounding": {"checked": True, "distinct": {"absent": 5}}}
        v = verdict(worse, self.BAR)
        self.assertEqual(v["status"], REGRESSED)
        self.assertIn("ungrounded identifiers", v["regressions"][0])

    def test_a_blind_check_stops_the_sweep_too(self):
        """A canary whose instruments could not run has verified nothing —
        the failure #565 recorded one level down, where a snippet was proved
        against the only project that had nothing to find."""
        blind = {**GOOD, "pair": {"ran": False, "reason": "schema missing"}}
        v = verdict(blind, self.BAR)
        self.assertEqual(v["status"], UNMEASURABLE)
        self.assertEqual(v["blind"], ["pair errors"])

    def test_a_missing_baseline_never_regresses(self):
        """No bar is not a failed bar. A first-ever arm has nothing to compare
        against and must not be blocked by that."""
        self.assertEqual(
            verdict(GOOD, {k: None for k in self.BAR})["status"], OK)


class RealArmTest(unittest.TestCase):

    def test_a_v4_record_does_not_regress_against_its_own_arm(self):
        """The gate must be satisfiable by the arm that defined it, or it is
        not a regression test but a wish."""
        import yaml
        from pathlib import Path
        p = (Path("data/d4d_concatenated/claudecode_agent_core")
             / f"{BASELINE}_rep1" / "AI_READI_provenance.yaml")
        if not p.exists():
            self.skipTest("v4 arm not present in this checkout")
        rec = yaml.safe_load(p.read_text(encoding="utf-8"))
        checks = {"pair": rec.get("pair_consistency"),
                  "report": rec.get("report_claims"),
                  "grounding": rec.get("grounding")}
        self.assertEqual(
            verdict(checks, baseline_for("AI_READI", BASELINE))["status"], OK)


if __name__ == "__main__":
    unittest.main()
