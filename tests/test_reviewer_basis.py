"""Which model made each review is recorded, and constant within an arm.

Why this exists (#1058): the v7 production reviews were made by
`claude-fable-5` and the v8 reviews by `claude-fable-5-1`. The agent
definition pinned `claude-fable-5`, and the reviewers write their own runtime
identity, so a point release of the judge changed the instrument with nothing
declaring it. The v7-against-v8 review comparison merged in #1055 was
presented as like-for-like and is not: it measures the package plus the
reviewer version.

Nothing here re-reviews anything or asserts which model is correct. It asserts
the two properties that make a reviewer difference *visible*: every review says
what made it, and one arm is one reviewer. A comparison across arms is then a
statement a reader can check rather than one they have to trust.

The reviewer is an instrument, the same as the rubric evaluators are
(`test_evaluation_coverage.py`), and this is that file's argument applied to
the review pass.
"""
import unittest
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONCAT = ROOT / "data" / "d4d_concatenated"
AGENT = ROOT / ".claude" / "agents" / "d4d-review-record.md"

#: Label prefixes that are one arm launched twice on one day (#934/#1084).
_ARM_ALIASES = {"2026-09-04f": "2026-09-04v8", "2026-09-04g": "2026-09-04v8"}


def _arm(label):
    prefix = label.rsplit("_rep", 1)[0] if "_rep" in label else label
    for mark, arm in _ARM_ALIASES.items():
        if prefix.startswith(mark):
            return arm + prefix[len(mark):]
    return prefix


def _reviews():
    """{arm: {label_dir: {project: model}}} from the review files on disk."""
    out = defaultdict(dict)
    for path in sorted(CONCAT.rglob("*_review.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        out[_arm(path.parent.name)][str(path)] = doc.get("model")
    return out


class TestEveryReviewSaysWhatMadeIt(unittest.TestCase):
    def setUp(self):
        self.reviews = _reviews()
        if not self.reviews:
            self.skipTest("no review files in this checkout")

    def test_no_review_omits_its_model(self):
        """An unrecorded reviewer is worse than a differing one: a differing
        one can be declared."""
        missing = [p for arm in self.reviews.values()
                   for p, model in arm.items() if not model]
        self.assertEqual(missing, [])

    def test_one_reviewer_per_arm(self):
        """The #1058 defect, as a check. It fails today only if a *new* arm
        mixes reviewers — the recorded v7 and v8 arms are each internally
        uniform, and it is the difference *between* them that #1058 is about,
        which is declared in the plan note rather than asserted here.
        """
        for arm, files in sorted(self.reviews.items()):
            with self.subTest(arm=arm):
                models = {m for m in files.values() if m}
                self.assertLessEqual(
                    len(models), 1,
                    f"{arm} was reviewed by more than one model: "
                    f"{sorted(models)}")

    def test_the_two_production_arms_do_not_share_a_reviewer(self):
        """Not a wish: the state of the corpus, pinned so that a later change
        to either arm's reviews cannot quietly make the comparison look
        like-for-like when the note says it is not (#1058)."""
        def models(mark):
            return {m for arm, files in self.reviews.items()
                    if arm.startswith(mark)
                    for m in files.values() if m}
        v7, v8 = models("2026-09-01"), models("2026-09-04v8")
        if not (v7 and v8):
            self.skipTest("the production reviews are not in this checkout")
        self.assertEqual(v7, {"claude-fable-5"})
        self.assertEqual(v8, {"claude-fable-5-1"})


class TestTheAgentDeclaresItsModel(unittest.TestCase):
    def test_the_definition_pins_a_model(self):
        """The pin does not decide what a subagent runs — the reviewer writes
        its own runtime identity, which is how #1058 happened — but an absent
        pin makes the intended instrument unstateable."""
        header = AGENT.read_text(encoding="utf-8").split("---")[1]
        pinned = [l.split(":", 1)[1].strip() for l in header.splitlines()
                  if l.startswith("model:")]
        self.assertEqual(len(pinned), 1, header)
        self.assertTrue(pinned[0], "the model line is empty")


if __name__ == "__main__":
    unittest.main()
