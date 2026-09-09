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
import hashlib
import json
import unittest
from collections import defaultdict
from pathlib import Path

from tests.arm_labels import arm_of

ROOT = Path(__file__).resolve().parents[1]
RUBRICS = ("rubric10_semantic", "rubric20_semantic")
PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE")

#: One definition of which prefixes are one arm, shared with
#: `test_reviewer_basis` (#1097). This file and that one carried
#: byte-identical copies, which is one copy nobody updates — and the copied
#: shape let an undeclared same-day suffix form its own arm silently.
_arm_key = arm_of


MANIFEST = ROOT / "tests" / "data" / "evaluation_manifest.json"


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
        projects times three replicates, on each rubric.

        Asserted as the expected set, not as a count (#1084): a cell for an
        unexpected project, or a `rep4`, would otherwise stand in for a
        missing expected one and the arm would still measure 12.
        """
        expected = {(project, f"rep{n}") for project in PROJECTS for n in (1, 2, 3)}
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
                    self.assertEqual(
                        found[arm], expected,
                        f"{rubric} {arm}: missing {sorted(expected - found[arm])}; "
                        f"unexpected {sorted(found[arm] - expected)}")

    def test_one_evaluator_per_arm_in_the_live_set(self):
        """A mixed evaluator inside one arm is the #1058 defect; an archive is
        where the other evaluator's scores belong.

        Bite is limited today (#1079): four rubric10 prefixes hold a single
        file and are trivially uniform, and every pre-2026-09-01 arm is
        uniformly claude-fable-5, so this passes for those arms rather than
        certifying them. It has real force on the two Opus-rescored arms,
        which are the ones a comparison is drawn from.

        The v8 arm is one arm (#1084). Its `04f` and `04g` prefixes are a
        launch detail, not two conditions, so grouping by the full prefix
        would let the two halves carry different evaluators and still pass.
        An absent evaluator is a failure rather than a uniform value: a set
        holding only `None` has one member.
        """
        for rubric in RUBRICS:
            evaluators = defaultdict(set)
            for p in _label_aware(rubric).glob("*_evaluation.json"):
                d = json.loads(p.read_text())
                label = d.get("label", "")
                prefix = _arm_key(label)
                evaluators[prefix].add((d.get("model") or {}).get("evaluator_model"))
            for prefix, models in sorted(evaluators.items()):
                with self.subTest(rubric=rubric, arm=prefix):
                    self.assertEqual(len(models), 1, f"{prefix}: {models}")
                    self.assertNotIn(None, models, f"{prefix}: no evaluator recorded")


class TestNoEvaluationChangesWithoutAnArchivedPredecessor(unittest.TestCase):
    """The archive convention, made checkable (#1084).

    `test_every_archived_evaluation_has_a_live_counterpart` catches an archive
    that lost its live copy. It cannot see the opposite failure: a live
    evaluation overwritten with no archived predecessor, which is what
    happened to the AI_READI and CHORUS controls on 2026-09-08. Nothing on
    disk records that the old numbers ever existed.

    `tests/data/evaluation_manifest.json` records each live evaluation's hash
    and the hashes it has held before. A rescore that archives the file it
    replaces produces a manifest diff whose `sha256` moves and whose
    `archived` list gains the previous value, each half checkable here. A
    rescore that does not archive can only fail this test or state the gap in
    its own diff.
    """

    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text())

    def _live(self):
        out = {}
        for rubric in RUBRICS:
            base = _label_aware(rubric)
            if not base.exists():
                continue
            for p in sorted(base.glob("*_evaluation.json")):
                out[f"{rubric}/{p.name}"] = hashlib.sha256(p.read_bytes()).hexdigest()
        return out

    def _archived(self):
        out = defaultdict(set)
        for rubric in RUBRICS:
            base = _label_aware(rubric)
            if not base.exists():
                continue
            for d in sorted(base.glob("superseded_*")):
                for p in sorted(d.glob("*_evaluation.json")):
                    out[f"{rubric}/{p.name}"].add(
                        hashlib.sha256(p.read_bytes()).hexdigest())
        return out

    def test_the_manifest_covers_exactly_the_live_evaluations(self):
        live = self._live()
        self.assertEqual(
            sorted(self.manifest), sorted(live),
            "run scripts/evaluation_manifest.py --write after adding or "
            "removing an evaluation")

    def test_every_live_evaluation_matches_its_recorded_hash(self):
        for key, digest in sorted(self._live().items()):
            with self.subTest(evaluation=key):
                self.assertEqual(
                    self.manifest.get(key, {}).get("sha256"), digest,
                    "content changed since the manifest was written: archive "
                    "the file it replaced, then run "
                    "scripts/evaluation_manifest.py --write")

    def test_every_superseded_hash_is_still_on_disk(self):
        archived = self._archived()
        for key, entry in sorted(self.manifest.items()):
            for digest in entry.get("archived", []):
                with self.subTest(evaluation=key, sha256=digest[:12]):
                    self.assertIn(
                        digest, archived.get(key, set()),
                        "the manifest records a superseded version that no "
                        "archived copy carries")


if __name__ == "__main__":
    unittest.main()
