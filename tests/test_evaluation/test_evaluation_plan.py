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
            first = [e.label for e in plan(concat_dir=root)]
            second = [e.label for e in plan(concat_dir=root)]
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first, key=lambda s: s.split("/")[0]))


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
