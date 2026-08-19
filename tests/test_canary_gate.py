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
        "grounding": {"checked": True, "distinct": {"absent": 0}},
        "form": {"checked": True, "organisational_fragments": 0,
                 "undeclared_prefix_occurrences": 0, "british_spellings": 0}}


class CountsTest(unittest.TestCase):

    def test_a_check_that_did_not_run_counts_as_none_not_zero(self):
        """Zero is a measurement; None is the absence of one. Collapsing them
        is the mistake the grounding check itself made (#578)."""
        counts = counts_from({"pair": {"ran": False, "reason": "x"},
                              "report": {"checked": False},
                              "grounding": {"checked": False}})
        self.assertEqual(set(counts.values()), {None})

    def test_counts_are_read_from_each_block(self):
        """By metric, not by a literal dict: the set grew from four to seven
        when #602 added the preregistered families, and a test about *where*
        each count comes from should not fail over *how many* there are."""
        counts = counts_from(GOOD)
        self.assertEqual(counts["pair errors"], 2)
        self.assertEqual(counts["report findings"], 0)
        self.assertEqual(counts["ungrounded identifiers"], 0)
        from data_sheets_schema.canary import METRICS
        self.assertEqual(set(counts), {m[0] for m in METRICS})


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
           "ungrounded identifiers": 0,
           "resolver URLs in identifier slots": 0,
           "organisational fragments": 0, "undeclared prefixes": 0,
           "British spellings": 0}

    def test_no_worse_than_the_baseline_passes(self):
        self.assertEqual(verdict(GOOD, self.BAR)["status"], OK)

    def test_equalling_the_worst_baseline_is_not_a_regression(self):
        at_bar = {**GOOD, "pair": {"ran": True, "errors": 10},
                  "report": {"checked": True, "findings": [1, 2]}}
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

    def test_a_baseline_that_was_asked_for_and_missing_is_unmeasurable(self):
        """The blocker this test used to assert the opposite of (#599).

        It read: "No bar is not a failed bar. A first-ever arm has nothing to
        compare against and must not be blocked by that." True of an arm with
        no baseline; false of a **mistyped** one — and the code could not tell
        them apart, so a run with 999 defects in every metric passed.

        That is "not established is not fine", missed inside the gate built to
        enforce it.
        """
        awful = {"pair": {"ran": True, "errors": 999},
                 "report": {"checked": True, "findings": [1] * 999},
                 "grounding": {"checked": True, "distinct": {"absent": 999},
                               "findings": []}}
        v = verdict(awful, {k: None for k in self.BAR}, baseline_requested=True)
        self.assertEqual(v["status"], UNMEASURABLE)
        self.assertEqual(sorted(v["unbaselined"]), sorted(self.BAR))

    def test_no_baseline_asked_for_is_still_permissible(self):
        """The case the old test was right about: a first-ever arm has nothing
        to compare against, and saying so is not the same as failing."""
        self.assertEqual(
            verdict(GOOD, {k: None for k in self.BAR},
                    baseline_requested=False)["status"], OK)

    def test_a_partially_resolved_baseline_does_not_pass(self):
        """One metric with no bar is enough: a gate that passes on the metrics
        it happens to have is the #591 hole in another form."""
        bar = dict(self.BAR); bar["ungrounded identifiers"] = None
        self.assertEqual(verdict(GOOD, bar)["status"], UNMEASURABLE)


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
                  "grounding": rec.get("grounding"), "form": rec.get("form")}
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
                     "grounding": grounding, "form": rec.get("form")},
                    baseline_for("AI_READI", self.B))
        self.assertEqual(v["status"], REGRESSED)
        self.assertTrue(any("resolver URLs" in r for r in v["regressions"]))

    def test_the_host_map_is_derived_from_the_schema(self):
        """Hardcoding three hosts missed the other 35 (#593).

        The schema declares 38 prefixes with an http base. A resolver URL for
        any of the others was invisible, and adding a prefix did not extend the
        check — the defect of #340, #467 and #563 in a fourth place.
        """
        from data_sheets_schema.grounding import declared_bases
        bases = declared_bases()
        self.assertGreater(len(bases), 30)
        self.assertEqual({p for _, p in bases} & {"doi", "ROR", "ORCID"},
                         {"doi", "ROR", "ORCID"})

    def test_longer_bases_are_matched_first(self):
        """Several prefixes share the w3id.org host, so matching the shorter
        base first would attribute a value to the wrong prefix."""
        from data_sheets_schema.grounding import declared_bases
        lengths = [len(b) for b, _ in declared_bases()]
        self.assertEqual(lengths, sorted(lengths, reverse=True))

    def test_a_prefix_beyond_the_original_three_is_caught(self):
        """The point of deriving: a w3id.org base is now detected too."""
        from data_sheets_schema.grounding import (declared_bases,
                                                  resolver_urls_in_identifier_slots)
        from data_sheets_schema.identifiers import uriorcurie_slots
        base, _ = next((b, p) for b, p in declared_bases()
                       if "w3id.org" in b)
        found = resolver_urls_in_identifier_slots(
            {"id": base + "something"}, uriorcurie_slots())
        self.assertEqual(len(found), 1)

    def test_the_metric_counts_distinct_identifiers(self):
        """#556 again: every identifier appears in both records, so an
        occurrence count is roughly double. The canary's 45 is 22 distinct."""
        from data_sheets_schema.canary import counts_from
        findings = [{"kind": "resolver_url_in_identifier_slot",
                     "value": "https://doi.org/10.1/x", "record": r}
                    for r in ("full", "core")]
        counts = counts_from({"grounding": {"checked": True,
                                            "distinct": {"absent": 0},
                                            "findings": findings}})
        self.assertEqual(counts["resolver URLs in identifier slots"], 1)

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


class ResumedBatchCanRegateTest(unittest.TestCase):
    """A sweep interrupted after a passing canary must be able to resume (#599).

    `execute()`'s completed-run early return omitted `checks`, so every metric
    became None and the canary reported `unmeasurable`. A batch that had already
    satisfied the gate could not fan out after an interruption — and
    interruption is normal: arms take hours and #513 is the precedent.
    """

    def test_the_completed_run_path_returns_the_checks(self):
        import inspect

        from data_sheets_schema.api_runner import execute
        src = inspect.getsource(execute)
        head = src[:src.index("already_complete")]
        self.assertIn('"checks":', head)

    def test_they_are_recomputed_rather_than_read_from_the_record(self):
        """Same reason validation is recomputed there: returning a verdict the
        record asserted earlier would report a clean bill nobody checked."""
        import inspect

        from data_sheets_schema.api_runner import execute
        src = inspect.getsource(execute)
        head = src[:src.index("already_complete")]
        for fn in ("pair_consistency(spec)", "report_claims_block(spec)",
                   "grounding_block(spec)"):
            with self.subTest(fn=fn):
                self.assertIn(fn, head)


class PredictionCoverageTest(unittest.TestCase):
    """Every preregistered prediction must have a metric (#602).

    The gate measured four things; the v5 plan preregisters five outcome
    families, and only one of them was among the four. So the canary could
    print "canary ok" while a run broke three of the five things v5 exists to
    change.

    That is #591 in general form: there, a run regressed on the rule v5 exists
    to enforce and the gate passed it because nothing measured that rule.
    Fixing the instance added one metric. This makes the omission fail a test.
    """

    PLAN = Path("notes/generic_v5_analysis_plan.md")

    def test_every_prediction_in_the_plan_maps_to_a_metric(self):
        import re

        from data_sheets_schema.canary import PREDICTION_METRICS
        if not self.PLAN.exists():
            self.skipTest("plan not present in this checkout")
        body = self.PLAN.read_text(encoding="utf-8")
        section = body[body.index("## Predictions"):]
        section = section[:section.index("\n## ")]
        numbered = {int(n) for n in re.findall(r"^(\d+)\. ", section, re.M)}
        self.assertTrue(numbered, "the plan states no numbered predictions")
        self.assertEqual(numbered, set(PREDICTION_METRICS),
                         "a prediction has no metric, or a metric no prediction")

    def test_every_named_metric_exists(self):
        from data_sheets_schema.canary import (METRICS, PREDICTION_METRICS,
                                               REPORTED_ONLY)
        known = {m[0] for m in METRICS} | {m[0] for m in REPORTED_ONLY}
        for prediction, metric in PREDICTION_METRICS.items():
            with self.subTest(prediction=prediction):
                self.assertIn(metric, known)

    def test_minted_fragments_is_reported_and_not_gated(self):
        """Prediction 2 is that the count **rises or holds**, so "higher than
        baseline" is the intended outcome and gating on it would fail the arm
        for working."""
        from data_sheets_schema.canary import METRICS, REPORTED_ONLY
        self.assertIn("minted fragments", {m[0] for m in REPORTED_ONLY})
        self.assertNotIn("minted fragments", {m[0] for m in METRICS})

    def test_the_gate_is_satisfiable_by_the_arm_that_defines_it(self):
        """The check that caught this change breaking itself.

        The three new metrics first lived inside the `grounding` block, whose
        recorded form predated them — so every v4 baseline read 0 and all
        twelve records "regressed" against their own arm. A gate that always
        fails is as useless as one that always passes, and worse, because it
        gets switched off.
        """
        import yaml
        base = Path("data/d4d_concatenated/claudecode_agent_core")
        checked = 0
        for rep in (1, 2, 3):
            label = f"{BASELINE}_rep{rep}"
            for project in ("AI_READI", "CHORUS", "CM4AI", "VOICE"):
                p = base / label / f"{project}_provenance.yaml"
                if not p.exists():
                    continue
                rec = yaml.safe_load(p.read_text(encoding="utf-8"))
                if not rec.get("form"):
                    self.skipTest("records predate the form block")
                v = verdict({"pair": rec["pair_consistency"],
                             "report": rec["report_claims"],
                             "grounding": rec["grounding"],
                             "form": rec["form"]},
                            baseline_for(project, BASELINE))
                checked += 1
                with self.subTest(project=project, rep=rep):
                    self.assertEqual(v["status"], OK, v.get("regressions"))
        if not checked:
            self.skipTest("v4 arm not present in this checkout")

    def test_form_counts_survive_a_drifted_bundle(self):
        """They are properties of the records alone, so burying them inside
        `grounding` — which declines when a bundle has drifted (#452) — would
        make three preregistered predictions unmeasurable for 59 records."""
        from data_sheets_schema.grounding import form_facts
        label = f"{BASELINE}_rep1"
        base = Path("data/d4d_concatenated")
        full = base / "claudecode_agent" / label / "VOICE_d4d.yaml"
        core = base / "claudecode_agent_core" / label / "VOICE_d4d_core.yaml"
        if not core.exists():
            self.skipTest("v4 arm not present in this checkout")
        facts = form_facts(full, core)      # no bundle argument at all
        self.assertTrue(facts["checked"])
        self.assertEqual(facts["organisational_fragments"], 7)

    def test_the_v4_baseline_carries_the_new_metrics(self):
        """A metric with no baseline makes the gate unmeasurable (#599), so
        adding one without its bar would have disabled the whole gate."""
        bar = baseline_for("VOICE", BASELINE)
        if bar["pair errors"] is None:
            self.skipTest("v4 arm not present in this checkout")
        for metric in ("organisational fragments", "undeclared prefixes",
                       "British spellings"):
            with self.subTest(metric=metric):
                self.assertIsNotNone(bar[metric])
