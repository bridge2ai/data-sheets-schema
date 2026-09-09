"""Which model made each review is recorded, declared, and checkable.

Why this exists (#1058): the v7 production reviews were made by
`claude-fable-5` and the v8 reviews by `claude-fable-5-1`. The agent
definition pinned `claude-fable-5`, and reviewers write their own runtime
identity, so a point release of the judge changed the instrument with nothing
declaring it. The v7-against-v8 review comparison merged in #1055 was
presented as like-for-like and is not.

The first version of this file (#1097) did not prevent the recurrence. Its
uniformity check fired only on drift *inside* one arm's review pass, and
#1058's drift was uniform within each arm and different *between* them; a
whole new arm reviewed by the next point release passed everything. So the
arm-to-reviewer map is now a **checked-in manifest**: a new arm is invisible
to the corpus until someone writes down who reviewed it, and changing a
recorded arm's reviewer is a diff a reader sees.

Nothing here re-reviews anything or asserts which model is correct. The
reviewer is an instrument, the same as the rubric evaluators are
(`test_evaluation_coverage.py`), and this is that file's argument applied to
the review pass.
"""
import json
import unittest
from collections import defaultdict
from pathlib import Path

import yaml

from tests.arm_labels import arm_of

ROOT = Path(__file__).resolve().parents[1]
CONCAT = ROOT / "data" / "d4d_concatenated"
MANIFEST = Path(__file__).resolve().parent / "data" / "reviewer_basis.json"
AGENT = ROOT / ".claude" / "agents" / "d4d-review-record.md"


def _reviews():
    """{arm: {pass: {path: doc}}} over both passes.

    `_review_b.yaml` is included (#1097): the six retests produce every
    reliability figure the plan note cites, and the outstanding work on #1058
    — a second pass under a different model — writes there. The artifact that
    will carry the next reviewer-version evidence must not be the one nothing
    looks at. The two passes are kept apart because a `_b` under a different
    model is the *point* of a paired pass, not a uniformity violation.
    """
    out = defaultdict(lambda: defaultdict(dict))
    for path in sorted(CONCAT.rglob("*_review*.yaml")):
        if "_review_pack" in path.name:
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            #: Fail, never skip (#1097). In a check whose purpose is "every
            #: review says what made it", a review that cannot be read is the
            #: strongest possible instance, and swallowing it made it vanish
            #: from all three tests instead of failing one.
            raise AssertionError(f"{path} is not parseable YAML: {exc}")
        if not isinstance(doc, dict):
            raise AssertionError(f"{path} is not a mapping: {type(doc).__name__}")
        kind = "b" if path.name.endswith("_review_b.yaml") else "a"
        out[arm_of(path.parent.name)][kind][str(path)] = doc
    return out


class ReviewCorpus(unittest.TestCase):
    def setUp(self):
        self.reviews = _reviews()
        if not self.reviews:
            self.skipTest("no review files in this checkout")
        doc = json.loads(MANIFEST.read_text())
        self.manifest = doc["arms"]
        self.undated = set(doc["undated_reviews"]["paths"])


class TestEveryReviewSaysWhatMadeIt(ReviewCorpus):
    def test_no_review_omits_its_model(self):
        """An unrecorded reviewer is worse than a differing one: a differing
        one can be declared."""
        missing = [p for arm in self.reviews.values()
                   for passes in arm.values()
                   for p, doc in passes.items() if not doc.get("model")]
        self.assertEqual(missing, [])

    def test_no_review_omits_when_it_ran(self):
        """The whole argument is that the reviewer changed *over time*, so a
        review with no time is a hole in the axis being argued (#1097). One
        `_review_b` on disk has `reviewed_at: null`; this fails until it is
        given a time or the gap is recorded deliberately."""
        undated = sorted(
            str(Path(p).relative_to(ROOT))
            for arm in self.reviews.values() for passes in arm.values()
            for p, doc in passes.items() if not doc.get("reviewed_at"))
        self.assertEqual(
            undated, sorted(self.undated),
            "a review with no reviewed_at cannot support a claim about when "
            "the reviewer changed: list it under undated_reviews with why, or "
            "give it a time with its basis stated")


class TestTheReviewerOfEachArmIsDeclared(ReviewCorpus):
    def test_the_manifest_covers_exactly_the_arms_on_disk(self):
        """A new arm must be written down. That is the recurrence #1058
        would otherwise have at v9: uniform within the arm, different from
        every arm it will be compared against, and invisible."""
        self.assertEqual(sorted(self.manifest), sorted(self.reviews))

    def test_each_arm_and_pass_matches_its_declared_reviewer(self):
        for arm, passes in sorted(self.reviews.items()):
            for kind, docs in sorted(passes.items()):
                with self.subTest(arm=arm, pass_=kind):
                    found = sorted({d.get("model") for d in docs.values()})
                    self.assertEqual(
                        found, self.manifest.get(arm, {}).get(kind),
                        "run scripts/… or edit tests/data/reviewer_basis.json "
                        "and say in the plan note what changed")

    def test_one_reviewer_within_one_arm_and_pass(self):
        for arm, passes in sorted(self.reviews.items()):
            for kind, docs in sorted(passes.items()):
                with self.subTest(arm=arm, pass_=kind):
                    self.assertLessEqual(
                        len({d.get("model") for d in docs.values() if d.get("model")}), 1)

    def test_the_two_production_arms_do_not_share_a_reviewer(self):
        """The state #1058 is about, pinned so a later change cannot quietly
        make the comparison look like-for-like while the note says it is not."""
        def models(mark):
            return {m for arm, passes in self.manifest.items()
                    if arm.startswith(mark)
                    for models_ in passes.values() for m in models_}
        v7, v8 = models("2026-09-01"), models("2026-09-04v8")
        #: Fail rather than skip (#1097). Once the arm-to-reviewer map is a
        #: checked-in manifest, the manifest is the assertion that those arms
        #: exist, so a declared arm with no reviews is a defect and not an
        #: absent checkout. This is the one test the plan note leans on.
        self.assertTrue(v7 and v8,
                        "the manifest declares both production arms; their "
                        "reviews are missing from the corpus")
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
