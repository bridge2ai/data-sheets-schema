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
from pathlib import Path

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
                          "ungrounded identifiers": 0,
                          "resolver URLs in identifier slots": 0})


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


class GateControlFlowTest(unittest.TestCase):
    """Where the refusal is raised decides whether it works at all.

    The first version raised inside the per-run `try`, whose bare
    `except Exception` catches everything — so under `--continue-on-error` the
    sweep caught its own canary refusal, logged it as a failed run, and fanned
    out. The gate existed and did nothing, which is worse than not having it,
    because the summary then says a canary passed.
    """

    def _source(self):
        import inspect

        from data_sheets_schema.cli.api import batch_cmd
        return inspect.getsource(batch_cmd.callback)

    def test_the_refusal_is_raised_outside_the_per_run_handler(self):
        src = self._source()
        self.assertGreater(src.index("raise click.ClickException(canary_stop)"),
                           src.index("except Exception as exc:"))

    def test_the_loop_breaks_rather_than_continuing(self):
        """`--continue-on-error` must not override the canary: it governs
        individual run failures, not the decision to fan out at all."""
        self.assertIn("if canary_stop:", self._source())

    def test_the_lock_is_released_exactly_once(self):
        """Releasing twice on the refusal path, or not at all, turns a stopped
        sweep into a permanently blocked label prefix (#513)."""
        self.assertEqual(self._source().count("run_lock.release(lock_path)"), 1)

    def test_the_gate_is_opt_in_and_says_how_to_bypass(self):
        src = self._source()
        self.assertIn("--no-canary-gate", src)
        self.assertIn("canary_baseline and not no_canary_gate", src)


class ResolverUrlMetricTest(unittest.TestCase):
    """The metric the v5 canary needed and the gate did not have (#591).

    A resolver URL for a declared prefix grounds perfectly —
    `doi.org/10.60775/…` is in the bundle — so what is wrong with it is form,
    not evidence. The canary wrote 45 and passed a gate measuring pair
    consistency, report claims and grounding, none of which could see the rule
    v5 exists to enforce.
    """

    B = "2026-08-13_claude-opus-5-api-generic-v4"
    V5 = "2026-08-16_claude-opus-5-api-generic-v5_rep1"
    BASE = Path("data/d4d_concatenated")

    def test_it_is_one_of_the_gate_metrics(self):
        from data_sheets_schema.canary import METRICS
        self.assertIn("resolver URLs in identifier slots",
                      [m[0] for m in METRICS])

    def test_the_v4_baseline_is_zero(self):
        bar = baseline_for("AI_READI", self.B)
        if bar["pair errors"] is None:
            self.skipTest("v4 arm not present in this checkout")
        self.assertEqual(bar["resolver URLs in identifier slots"], 0)

    def test_the_canary_would_now_be_refused(self):
        """The whole point: the gate must fail the run it passed."""
        import yaml

        from data_sheets_schema.grounding import check_run
        from data_sheets_schema.identifiers import uriorcurie_slots
        core = self.BASE / "claudecode_agent_core" / self.V5 / "AI_READI_provenance.yaml"
        if not core.exists():
            self.skipTest("v5 canary not present in this checkout")
        grounding = check_run(
            self.BASE / "claudecode_agent" / self.V5 / "AI_READI_d4d.yaml",
            self.BASE / "claudecode_agent_core" / self.V5 / "AI_READI_d4d_core.yaml",
            Path("data/preprocessed/concatenated/AI_READI_preprocessed.txt"),
            uriorcurie_slots())
        rec = yaml.safe_load(core.read_text(encoding="utf-8"))
        v = verdict({"pair": rec.get("pair_consistency"),
                     "report": rec.get("report_claims"),
                     "grounding": grounding},
                    baseline_for("AI_READI", self.B))
        self.assertEqual(v["status"], REGRESSED)
        self.assertTrue(any("resolver URLs" in r for r in v["regressions"]))

    def test_a_url_ranged_slot_is_not_counted(self):
        """`download_url` and `access_urls` are declared `uri`; a URL there is
        correct, and counting it would penalise the schema's own design."""
        from data_sheets_schema.grounding import resolver_urls_in_identifier_slots
        from data_sheets_schema.identifiers import uriorcurie_slots
        found = resolver_urls_in_identifier_slots(
            {"download_url": "https://doi.org/10.1234/x"}, uriorcurie_slots())
        self.assertEqual(found, [])

    def test_an_undeclared_host_is_not_counted(self):
        """No prefix exists for it, so a URL is the correct answer there."""
        from data_sheets_schema.grounding import resolver_urls_in_identifier_slots
        from data_sheets_schema.identifiers import uriorcurie_slots
        found = resolver_urls_in_identifier_slots(
            {"id": "https://b2ai-voice.org/thing"}, uriorcurie_slots())
        self.assertEqual(found, [])
