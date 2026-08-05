"""The evaluation count must be derived, never restated (#315).

It has been written down four times and been wrong three of them, in both
directions:

    8   4 projects x 2 rubrics      full records only, unstated
    6   3 projects x 2 rubrics      after VOICE failed selection; still full-only
    12  3 projects x 2 variants x 2 correct only while VOICE and VOICE_PEDIATRIC
                                    have no canonical record
    20  5 projects x 2 variants x 2 correct only after a successful rerun

Every one was typed into a note and then quoted from that note. So the tests
here deliberately do **not** assert a number against the live corpus — doing so
would recreate the defect inside the test suite, and would break on the day the
rerun succeeds, which is the day it should quietly become 20.

What they assert is that the plan is a function of the canonical marks: change
the marks, the plan changes with them.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from data_sheets_schema.evaluation_plan import (SEMANTIC_RUBRICS, VARIANTS,
                                                Evaluation, NothingSelected,
                                                plan, summarise)


def _corpus(root: Path, projects, config="2026-08-05_cfg", variants=VARIANTS):
    """A concatenated directory with `canonical` marks for the named projects.

    Shaped as `canonical_runs` reads it: a `canonical` block, `run.project`,
    `run.label`, and `outputs.<variant>.path`. Writing a looser fixture made
    every assertion here pass vacuously against an empty plan.
    """
    label = f"{config}_rep1"
    for project in projects:
        outputs = {}
        for variant in variants:
            sub = "claudecode_agent" if variant == "full" else "claudecode_agent_core"
            suffix = "_d4d.yaml" if variant == "full" else "_d4d_core.yaml"
            path = root / sub / label / f"{project}{suffix}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("id: x\n")
            outputs[variant] = {"path": str(path)}
        prov_dir = root / "claudecode_agent_core" / label
        prov_dir.mkdir(parents=True, exist_ok=True)
        (prov_dir / f"{project}_provenance.yaml").write_text(yaml.safe_dump({
            "run": {"project": project, "label": label,
                    "method": "claudecode_agent"},
            "outputs": outputs,
            "canonical": {"criterion": "test", "selected_from": ["a"]},
        }))
    return root


class TestThePlanFollowsTheMarks(unittest.TestCase):
    """Not a number. A function of what is marked."""

    def test_one_project_yields_variants_times_rubrics(self):
        with TemporaryDirectory() as tmp:
            root = _corpus(Path(tmp), ["CHORUS"])
            got = plan(concat_dir=root)
        self.assertEqual(len(got), len(VARIANTS) * len(SEMANTIC_RUBRICS))
        self.assertEqual({e.project for e in got}, {"CHORUS"})

    def test_adding_a_project_adds_its_evaluations(self):
        """The rerun's effect, in miniature: mark more projects, get more
        evaluations, with no number edited anywhere."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _corpus(root, ["CHORUS"])
            before = len(plan(concat_dir=root))
            _corpus(root, ["AI_READI", "CM4AI"])
            after = len(plan(concat_dir=root))
        self.assertEqual(after - before, 2 * len(VARIANTS) * len(SEMANTIC_RUBRICS))

    def test_a_project_with_no_mark_contributes_nothing(self):
        """The reason the count cannot be stated in advance: VOICE has no
        canonical record while no replicate validates (#292)."""
        with TemporaryDirectory() as tmp:
            root = _corpus(Path(tmp), ["CHORUS", "CM4AI"])
            got = plan(concat_dir=root)
        self.assertNotIn("VOICE", {e.project for e in got})

    def test_a_missing_variant_is_skipped_not_guessed(self):
        with TemporaryDirectory() as tmp:
            root = _corpus(Path(tmp), ["CHORUS"], variants=("full",))
            got = plan(concat_dir=root)
        self.assertEqual({e.variant for e in got}, {"full"})
        self.assertEqual(len(got), len(SEMANTIC_RUBRICS))

    def test_every_record_is_paired_with_every_rubric(self):
        with TemporaryDirectory() as tmp:
            root = _corpus(Path(tmp), ["CHORUS", "CM4AI"])
            got = plan(concat_dir=root)
        for project in ("CHORUS", "CM4AI"):
            for variant in VARIANTS:
                rubrics = {e.rubric for e in got
                           if e.project == project and e.variant == variant}
                with self.subTest(project=project, variant=variant):
                    self.assertEqual(rubrics, set(SEMANTIC_RUBRICS))

    def test_the_order_does_not_depend_on_the_resolver(self):
        """`canonical_runs` happens to return a sorted dict, which masked
        whether `plan` sorts at all — mutation showed removing its `sorted()`
        changed nothing. Feed an unsorted mapping so `plan` owns its ordering
        rather than inheriting it.
        """
        import data_sheets_schema.evaluation_plan as module
        from unittest.mock import patch
        unsorted = {
            "VOICE": {"full": "v.yaml", "core": "vc.yaml"},
            "AI_READI": {"full": "a.yaml", "core": "ac.yaml"},
        }
        with patch("data_sheets_schema.runs.canonical_runs",
                   return_value=unsorted):
            projects = [e.project for e in module.plan()]
        self.assertEqual(projects[0], "AI_READI",
                         "plan must sort projects itself")

    def test_the_order_is_stable(self):
        with TemporaryDirectory() as tmp:
            root = _corpus(Path(tmp), ["CM4AI", "AI_READI"])
            first = [e.name for e in plan(concat_dir=root)]
            second = [e.name for e in plan(concat_dir=root)]
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first, key=lambda s: s.split("/")[0]))


class TestReplicateCoverage(unittest.TestCase):
    """#287's other option: every replicate of the canonical config.

    Buys a within-config variance estimate at ~3x the cost. It does not buy a
    between-config comparison — #169 established four projects cannot resolve
    differences near the noise floor, and more replicates of the same four
    projects does not change that.
    """

    def _corpus_with_replicates(self, root, project="CHORUS", reps=3):
        """rep1 marked canonical; rep2 and rep3 are unmarked siblings.

        `validation_status` is patched in each test rather than faked in
        provenance: it re-hashes the artifacts a verdict was reached on, so a
        fixture claiming `passed` would have to reproduce that too, and the
        gate under test here is the plan's, not the verdict's.
        """
        config = "2026-08-05_cfg"
        for rep in range(1, reps + 1):
            label = f"{config}_rep{rep}"
            for variant in VARIANTS:
                sub = ("claudecode_agent" if variant == "full"
                       else "claudecode_agent_core")
                suffix = "_d4d.yaml" if variant == "full" else "_d4d_core.yaml"
                path = root / sub / label / f"{project}{suffix}"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("id: x\n")
        _corpus(root, [project], config=config)
        return root

    @staticmethod
    def _all_valid():
        from unittest.mock import patch
        return patch("data_sheets_schema.runs.validation_status",
                     return_value="valid")

    def test_it_covers_every_replicate_not_just_the_marked_one(self):
        with TemporaryDirectory() as tmp:
            root = self._corpus_with_replicates(Path(tmp))
            with self._all_valid():
                canonical = plan(concat_dir=root)
                widened = plan(concat_dir=root, all_replicates=True)
        self.assertEqual(len(widened), 3 * len(canonical))
    def test_each_evaluation_names_its_replicate(self):
        """Without the label the widened plan has three indistinguishable
        entries per record, and a sweep cannot tell their results apart."""
        with TemporaryDirectory() as tmp:
            root = self._corpus_with_replicates(Path(tmp))
            with self._all_valid():
                widened = plan(concat_dir=root, all_replicates=True)
        labels = {e.label for e in widened}
        self.assertEqual(len(labels), 3)
        self.assertTrue(all(e.label in e.name for e in widened))
    def test_the_canonical_plan_carries_no_label(self):
        """One record per project — the label is implied by the mark."""
        with TemporaryDirectory() as tmp:
            root = self._corpus_with_replicates(Path(tmp))
            for evaluation in plan(concat_dir=root):
                self.assertIsNone(evaluation.label)

    def test_the_summary_product_matches_the_total(self):
        """The derivation must multiply to the number beside it, or it is worse
        than no derivation at all."""
        import re
        with TemporaryDirectory() as tmp:
            root = self._corpus_with_replicates(Path(tmp))
            for widen in (False, True):
                with self._all_valid():
                    got = plan(concat_dir=root, all_replicates=widen)
                line = summarise(got)
                if "not a product" in line:
                    continue
                factors = [int(n) for n in re.findall(
                    r"(\d+) (?:projects|variants|rubrics|replicates)", line)]
                product = 1
                for factor in factors:
                    product *= factor
                with self.subTest(all_replicates=widen):
                    self.assertEqual(product, len(got), line)

    def test_an_uneven_exclusion_stops_the_summary_claiming_a_product(self):
        """Gating on validity can make the plan ragged (#344), and a
        factorisation multiplying to something other than the total reads as a
        check that passed.

        Excluding the *same* replicate from every project leaves an even grid
        and stays a legitimate product — my first version of this test asserted
        raggedness there and was wrong. Raggedness needs an **uneven**
        exclusion: two projects keeping different numbers of replicates.
        """
        from unittest.mock import patch
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._corpus_with_replicates(root, project="CHORUS")
            self._corpus_with_replicates(root, project="CM4AI")
            # CHORUS keeps all three; CM4AI keeps only rep1.
            def status(method, label, project):
                if project == "CM4AI" and not label.endswith("rep1"):
                    return "invalid"
                return "valid"
            with patch("data_sheets_schema.runs.validation_status",
                       side_effect=status):
                got = plan(concat_dir=root, all_replicates=True)
                line = summarise(got)
        self.assertIn("not a product", line)
        self.assertIn("excluded as not validating", line)
        self.assertIn("CM4AI", line)

    def test_an_even_exclusion_is_still_reported_as_a_product(self):
        """The complement: dropping rep2 and rep3 everywhere leaves a grid, so
        the factorisation is honest and should still be printed."""
        from unittest.mock import patch
        with TemporaryDirectory() as tmp:
            root = self._corpus_with_replicates(Path(tmp))
            with patch("data_sheets_schema.runs.validation_status",
                       side_effect=lambda m, l, p: (
                           "valid" if l.endswith("rep1") else "invalid")):
                line = summarise(plan(concat_dir=root, all_replicates=True))
        self.assertNotIn("not a product", line)
        self.assertIn("excluded as not validating", line)
        # Named, not merely counted. "2 excluded" invites the reader to assume
        # they were the same kind of thing, and which replicate was dropped is
        # what makes the exclusion checkable.
        self.assertIn("rep2", line)
        self.assertIn("rep3", line)
        self.assertIn("(invalid)", line)

    def test_only_validating_replicates_are_evaluated(self):
        """A record that fails validation would be scored by an LLM judge and
        pooled into a variance estimate, measuring validation failure as quality
        variance (#344)."""
        from unittest.mock import patch
        with TemporaryDirectory() as tmp:
            root = self._corpus_with_replicates(Path(tmp))
            with patch("data_sheets_schema.runs.validation_status",
                       side_effect=lambda m, l, p: (
                           "valid" if l.endswith("rep1") else "invalid")):
                got = plan(concat_dir=root, all_replicates=True)
        self.assertEqual({e.label for e in got},
                         {"2026-08-05_cfg_rep1"})

    def test_an_unverified_replicate_is_excluded_too(self):
        """Absence of evidence is not validity — the same reasoning
        `validation_status` itself carries."""
        from unittest.mock import patch
        with TemporaryDirectory() as tmp:
            root = self._corpus_with_replicates(Path(tmp))
            with patch("data_sheets_schema.runs.validation_status",
                       return_value="unverified"):
                with self.assertRaises(NothingSelected):
                    plan(concat_dir=root, all_replicates=True)


class TestNothingSelected(unittest.TestCase):
    """An unstarted scoping and a finished one are different states."""

    def test_an_empty_corpus_raises_rather_than_returning_an_empty_plan(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(NothingSelected):
                plan(concat_dir=Path(tmp))

    def test_the_message_says_what_to_do(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(NothingSelected) as caught:
                plan(concat_dir=Path(tmp))
        message = str(caught.exception)
        self.assertIn("d4d runs select --execute", message)
        self.assertIn("--missing", message)


class TestSummarise(unittest.TestCase):
    """The derivation travels with the number, so a bare count is harder to
    quote onward — which is how this went wrong four times."""

    def test_it_states_the_factors_not_just_the_total(self):
        with TemporaryDirectory() as tmp:
            root = _corpus(Path(tmp), ["CHORUS", "CM4AI"])
            line = summarise(plan(concat_dir=root))
        self.assertIn("8 evaluations", line)
        self.assertIn("2 projects", line)
        self.assertIn("CHORUS", line)
        self.assertIn("2 variants", line)
        self.assertIn("2 rubrics", line)


class TestTheCliRendersFailures(unittest.TestCase):
    """Every way this can fail must arrive as a message, not a traceback.

    `AmbiguousCanonical` is the state the rerun creates — marks under the old
    and new config until re-selection settles — and it reached the user as a
    bare traceback with no mention of `--config` (#342).
    """

    def _invoke(self, side_effect=None, return_value=None):
        from unittest.mock import patch

        from click.testing import CliRunner

        from data_sheets_schema.cli.evaluate import evaluate
        kwargs = ({"side_effect": side_effect} if side_effect
                  else {"return_value": return_value})
        with patch("data_sheets_schema.runs.canonical_runs", **kwargs):
            return CliRunner().invoke(evaluate, ["plan"])

    def test_two_marks_are_reported_with_the_remedy(self):
        from data_sheets_schema.runs import AmbiguousCanonical
        result = self._invoke(
            side_effect=AmbiguousCanonical("CHORUS: v2_rep1, v3_rep1"))
        self.assertIsNone(result.exception if result.exit_code == 0 else None)
        self.assertNotIsInstance(result.exception, AmbiguousCanonical)
        self.assertIn("--config", result.output)
        self.assertIn("CHORUS", result.output)

    def test_nothing_selected_is_reported_with_the_remedy(self):
        result = self._invoke(return_value={})
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("d4d runs select --execute", result.output)

    def test_a_resolvable_corpus_exits_zero(self):
        """The guard must not turn every invocation into an error."""
        result = self._invoke(return_value={
            "CHORUS": {"full": "c.yaml", "core": "cc.yaml"}})
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("evaluations =", result.output)


class TestTheLiveCorpus(unittest.TestCase):
    """Properties of the real plan — deliberately not its size."""

    def test_the_plan_is_derivable_and_self_consistent(self):
        try:
            got = plan()
        except NothingSelected:
            self.skipTest("no canonical record on disk")
        self.assertEqual(
            len(got),
            len({(e.project, e.variant) for e in got}) * len(SEMANTIC_RUBRICS),
            "every canonical record must pair with every rubric exactly once")


if __name__ == "__main__":
    unittest.main()
