"""Reporting which verdicts say what schema they were reached against (#433).

`validation_status` returns STALE when a pinned schema moves, and leaves an
unpinned verdict alone — absent is not stale, and failing every verdict written
before the pin existed would discard evidence rather than check it (#426).

The cost of that correct choice is that `VALID` means two different things
depending on when it was written. `d4d runs validate` will not close the gap on
its own, because it skips a run already VALID — which is the entire point of
caching a verdict. So the gap is reported, not repaired.
"""

import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.runs import (
    VERDICT_ABSENT,
    VERDICT_PINNED,
    VERDICT_UNPINNED,
    verdict_schema_pin,
)

METHOD, LABEL, PROJECT = "claudecode_agent", "2026-08-11_pin_rep1", "CHORUS"


class TestVerdictSchemaPin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.concat = Path(self.tmp.name) / "data/d4d_concatenated"
        (self.concat / f"{METHOD}_core" / LABEL).mkdir(parents=True)

    def _write(self, validation):
        path = (self.concat / f"{METHOD}_core" / LABEL
                / f"{PROJECT}_provenance.yaml")
        body = {"record_version": 1}
        if validation is not None:
            body["validation"] = validation
        path.write_text(yaml.safe_dump(body), encoding="utf-8")

    def _status(self):
        return verdict_schema_pin(METHOD, LABEL, PROJECT, self.concat)

    def test_a_pinned_verdict_is_recognised(self):
        self._write({"passed": True, "schema": {"full_sha256": "a" * 64}})
        self.assertEqual(self._status(), VERDICT_PINNED)

    def test_a_core_only_pin_counts(self):
        """Either half is enough to make the verdict falsifiable."""
        self._write({"passed": True, "schema": {"core_sha256": "b" * 64}})
        self.assertEqual(self._status(), VERDICT_PINNED)

    def test_a_verdict_with_no_schema_block_is_unpinned(self):
        self._write({"passed": True, "recorded_by": "d4d runs validate"})
        self.assertEqual(self._status(), VERDICT_UNPINNED)

    def test_an_empty_schema_block_is_unpinned_not_pinned(self):
        """A block with no hash in it pins nothing, and must not read as if it
        did — that would be worse than an absent block, because it looks
        checked."""
        self._write({"passed": True, "schema": {}})
        self.assertEqual(self._status(), VERDICT_UNPINNED)

    def test_a_schema_block_with_empty_hashes_is_unpinned(self):
        self._write({"passed": True,
                     "schema": {"full_sha256": None, "core_sha256": ""}})
        self.assertEqual(self._status(), VERDICT_UNPINNED)

    def test_a_failing_verdict_can_still_be_pinned(self):
        """The pin is about falsifiability, not about the outcome."""
        self._write({"passed": False, "schema": {"full_sha256": "c" * 64}})
        self.assertEqual(self._status(), VERDICT_PINNED)

    def test_no_verdict_is_absent_not_unpinned(self):
        """A different gap, counted separately so the two cannot be confused."""
        self._write(None)
        self.assertEqual(self._status(), VERDICT_ABSENT)

    def test_a_verdict_without_passed_is_absent(self):
        """A block that records no outcome is not a verdict."""
        self._write({"recorded_by": "d4d runs validate"})
        self.assertEqual(self._status(), VERDICT_ABSENT)

    def test_a_missing_record_is_absent(self):
        self.assertEqual(self._status(), VERDICT_ABSENT)

    def test_an_unreadable_record_is_absent_not_raised(self):
        """One bad record must not abort a corpus sweep — the #444 lesson."""
        path = (self.concat / f"{METHOD}_core" / LABEL
                / f"{PROJECT}_provenance.yaml")
        path.write_bytes(b"\xff\xfe not utf-8")
        self.assertEqual(self._status(), VERDICT_ABSENT)


@unittest.skipUnless(Path("data/d4d_concatenated").exists(), "corpus absent")
class TestAgainstTheRealCorpus(unittest.TestCase):
    def test_the_corpus_gap_is_visible_and_counted(self):
        """Pinned at the state #433 describes, so the number can be watched.

        Every verdict in the corpus is unpinned, because the pin postdates them
        all and `d4d runs validate` skips a run already VALID. This asserts the
        gap exists rather than asserting a target — when it starts shrinking,
        this test is where that shows up.
        """
        from data_sheets_schema.runs import discover, is_complete

        counts = {VERDICT_PINNED: 0, VERDICT_UNPINNED: 0, VERDICT_ABSENT: 0}
        for run in discover():
            if run.is_core or run.deterministic:
                continue
            for project in run.projects:
                if not is_complete(run.method, run.label, project):
                    continue
                counts[verdict_schema_pin(run.method, run.label, project)] += 1

        self.assertGreater(counts[VERDICT_UNPINNED], 0,
                           "if this is zero the corpus has converged — update "
                           "the test and #433 rather than deleting it")
        self.assertEqual(counts[VERDICT_ABSENT], 0,
                         "a complete run with no verdict at all is a different "
                         "and more serious gap than an unpinned one")
