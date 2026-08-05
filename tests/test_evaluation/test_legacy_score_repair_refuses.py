"""The legacy score-repair tool must refuse records newer than itself (#328).

`scripts/fix_evaluation_scores.py` recomputes an evaluation's totals and writes
`overall_score.percentage`. Both halves are wrong for a record written after the
N/A convention:

- the reported figure is `normalized_percentage`, computed over
  `adjusted_max_points` — the maximum *after* excluding non-applicable items —
  so `total_points / max_points` is a different number whenever anything is
  excluded; and
- `percentage` is not declared by either semantic schema (#323), so writing it
  turns a conformant record into a non-conformant one.

Nothing in the pipeline invokes this script, and everything it could still
legitimately repair — the 12 superseded and 8 invalid records — is being
regenerated. So migrating it to the N/A vocabulary would be work spent on a
corpus about to be replaced. Refusing is the whole remaining fix, and these
tests are what make the refusal real.

A refusal is not an error. The caller reports it separately from a fault,
because a traceback here would read as a problem with the corpus rather than a
tool that is out of date.
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "fix_evaluation_scores.py"


def _module():
    spec = importlib.util.spec_from_file_location("fix_evaluation_scores", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _legacy_record():
    """The shape this tool was written for: one percentage, no exclusions."""
    return {
        "rubric": "rubric20-semantic",
        "version": "1.0",
        "project": "AI_READI",
        "method": "claudecode_agent",
        "overall_score": {"total_points": 70, "max_points": 88, "percentage": 79.5},
        "categories": [{"name": "Structural Completeness", "questions": [
            {"id": 1, "name": "Field Completeness", "score": 5, "max_score": 5}]}],
    }


def _current_record(marker="normalized_percentage"):
    """The shape the agents have instructed since the N/A convention."""
    overall = {"total_points": 70, "max_points": 88, "excluded_max_points": 5,
               "adjusted_max_points": 83, "normalized_percentage": 84.3,
               "questions_not_applicable": 1}
    record = _legacy_record()
    record["overall_score"] = {k: v for k, v in overall.items()
                               if k == marker or k in ("total_points", "max_points")}
    return record


@unittest.skipUnless(SCRIPT.exists(), "repair script not present")
class TestItRefusesCurrentRecords(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.module = _module()

    def _write(self, record, directory):
        path = Path(directory) / "AI_READI_claudecode_agent_evaluation.json"
        path.write_text(json.dumps(record))
        return path

    #: Named here rather than read from the module. An earlier version iterated
    #: over `module.CURRENT_SHAPE_MARKERS`, so narrowing that tuple to one entry
    #: made the test pass vacuously — it derived its expectation from the code it
    #: was checking. Caught by mutation.
    MARKERS = ("normalized_percentage", "adjusted_max_points", "excluded_max_points")

    def test_each_marker_of_the_current_shape_triggers_a_refusal(self):
        """Any one of the three is enough. A record carrying only
        `adjusted_max_points` is still one this tool would miscompute."""
        for marker in self.MARKERS:
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as tmp:
                path = self._write(_current_record(marker), tmp)
                with self.assertRaises(self.module.CurrentShapeRecord):
                    self.module.fix_evaluation_scores(path)

    def test_the_module_recognises_exactly_those_markers(self):
        """The complement: if the N/A vocabulary grows a fourth key, this fails
        rather than the guard silently missing it."""
        self.assertEqual(tuple(self.module.CURRENT_SHAPE_MARKERS), self.MARKERS)

    def test_the_refusal_names_the_file_and_the_marker(self):
        """It has to be actionable without reading the source."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(_current_record(), tmp)
            with self.assertRaises(self.module.CurrentShapeRecord) as caught:
                self.module.fix_evaluation_scores(path)
        message = str(caught.exception)
        self.assertIn("AI_READI_claudecode_agent_evaluation.json", message)
        self.assertIn("normalized_percentage", message)

    def test_a_refused_record_is_not_modified(self):
        """The point of the guard. `dry_run` defaults to False, so a refusal
        that happened *after* the rewrite would be no guard at all."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(_current_record(), tmp)
            before = path.read_bytes()
            with self.assertRaises(self.module.CurrentShapeRecord):
                self.module.fix_evaluation_scores(path, dry_run=False)
            self.assertEqual(path.read_bytes(), before)

    def test_it_refuses_before_deciding_the_rubric_type(self):
        """A current record with an unrecognisable rubric must still refuse
        rather than return the softer "unknown rubric type" skip, which reads
        as "nothing to do here"."""
        with tempfile.TemporaryDirectory() as tmp:
            record = _current_record()
            record.pop("rubric")
            record.pop("categories")
            path = self._write(record, tmp)
            with self.assertRaises(self.module.CurrentShapeRecord):
                self.module.fix_evaluation_scores(path)


@unittest.skipUnless(SCRIPT.exists(), "repair script not present")
class TestItStillHandlesWhatItWasWrittenFor(unittest.TestCase):
    """The guard must not refuse everything — that would be indistinguishable
    from deleting the tool, and the pre-2026 corpus is what it exists for."""

    @classmethod
    def setUpClass(cls):
        cls.module = _module()

    def test_a_legacy_record_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AI_READI_claudecode_agent_evaluation.json"
            path.write_text(json.dumps(_legacy_record()))
            modified, message = self.module.fix_evaluation_scores(path, dry_run=True)
        self.assertIsInstance(message, str)

    def test_a_record_with_no_overall_score_is_not_refused(self):
        """The pre-2026 rubric10 shape reports `summary_scores`, and has no
        `overall_score` at all."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AI_READI_claudecode_agent_evaluation.json"
            path.write_text(json.dumps({
                "rubric": "rubric10-semantic",
                "summary_scores": {"total_score": 40, "total_max_score": 50,
                                   "overall_percentage": 80.0},
                "element_scores": []}))
            self.module.fix_evaluation_scores(path, dry_run=True)  # must not raise


@unittest.skipUnless(SCRIPT.exists(), "repair script not present")
class TestTheLiveCorpus(unittest.TestCase):
    """Every recorded semantic evaluation is either legacy or refused."""

    def test_no_current_record_would_be_rewritten(self):
        module = _module()
        current = REPO / "data" / "evaluation_llm"
        checked = refused = 0
        for path in sorted(current.glob("*_semantic/concatenated/*_evaluation.json")):
            record = json.loads(path.read_text())
            checked += 1
            try:
                module.refuse_current_shape(record, path)
            except module.CurrentShapeRecord:
                refused += 1
        self.assertGreater(checked, 0, "no recorded evaluations found")
        self.assertEqual(
            refused,
            sum(1 for p in sorted(current.glob("*_semantic/concatenated/*_evaluation.json"))
                if "overall_score" in json.loads(p.read_text())),
            "every record in the current shape must be refused, and no other")


if __name__ == "__main__":
    unittest.main()
