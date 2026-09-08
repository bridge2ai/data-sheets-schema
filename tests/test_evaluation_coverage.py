"""Every arm the comparison reads has a live evaluation, not only an archive.

Six CM4AI rubric10 evaluations vanished from `main` on 2026-09-08 (#1076).
Nothing failed: the plan note kept quoting their numbers, `arm_comparison.py`
silently produced a shorter list, and the loss surfaced only because the next
issue happened to read those files.

The mechanism is worth stating, because the archiving convention invites it.
Superseding an evaluation means writing a replacement at the canonical path
and copying the previous file, byte-identical, into a `superseded_*/`
subdirectory. To git that is a rename plus a modification, and a later merge
can apply the rename and take the replacement with it.

So this asserts the property the archive convention endangers: for every
(project, label, rubric) that has an archived evaluation, a live one exists
at the canonical path. An archive is a record of what a number used to be,
never the only copy.
"""
import json
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUBRICS = ("rubric10_semantic", "rubric20_semantic")


def _label_aware(rubric):
    return ROOT / "data" / "evaluation_llm" / rubric / "label_aware"


class TestNoEvaluationSurvivesOnlyInAnArchive(unittest.TestCase):
    def test_every_archived_evaluation_has_a_live_counterpart(self):
        missing = []
        for rubric in RUBRICS:
            base = _label_aware(rubric)
            if not base.exists():
                continue
            live = {p.name for p in base.glob("*_evaluation.json")}
            for archive in sorted(base.glob("superseded_*")):
                for p in sorted(archive.glob("*_evaluation.json")):
                    if p.name not in live:
                        missing.append(f"{rubric}/{archive.name}/{p.name}")
        self.assertEqual(missing, [], "archived with no live evaluation: " + ", ".join(missing))

    def test_the_two_production_arms_are_complete_on_both_rubrics(self):
        """v7 production and v8 are the arms prediction 8 is read from: four
        projects times three replicates, on each rubric."""
        for rubric in RUBRICS:
            found = defaultdict(set)
            for p in _label_aware(rubric).glob("*_evaluation.json"):
                d = json.loads(p.read_text())
                label = d.get("label", "")
                #: The production prefixes by name (#1079): "2026-09-04" also
                #: matches the 04b-04e exploratory canaries, so evaluating one
                #: would break the count and count a canary as production.
                for arm, marks in (("v7", ("2026-09-01_",)),
                                   ("v8", ("2026-09-04f_", "2026-09-04g_"))):
                    if any(label.startswith(m) for m in marks) and "generic-v" in label:
                        found[arm].add((d.get("project"), label.rsplit("_", 1)[-1]))
            for arm in ("v7", "v8"):
                with self.subTest(rubric=rubric, arm=arm):
                    self.assertEqual(len(found[arm]), 12,
                                     f"{rubric} {arm}: {sorted(found[arm])}")

    def test_one_evaluator_per_arm_in_the_live_set(self):
        """A mixed evaluator inside one arm is the #1058 defect; an archive is
        where the other evaluator's scores belong.

        Bite is limited today (#1079): four rubric10 prefixes hold a single
        file and are trivially uniform, and every pre-2026-09-01 arm is
        uniformly claude-fable-5, so this passes for those arms rather than
        certifying them. It has real force on the two Opus-rescored arms,
        which are the ones a comparison is drawn from.
        """
        for rubric in RUBRICS:
            evaluators = defaultdict(set)
            for p in _label_aware(rubric).glob("*_evaluation.json"):
                d = json.loads(p.read_text())
                label = d.get("label", "")
                prefix = label.rsplit("_rep", 1)[0] if "_rep" in label else label
                evaluators[prefix].add((d.get("model") or {}).get("evaluator_model"))
            for prefix, models in sorted(evaluators.items()):
                with self.subTest(rubric=rubric, arm=prefix):
                    self.assertEqual(len(models), 1, f"{prefix}: {models}")


if __name__ == "__main__":
    unittest.main()
