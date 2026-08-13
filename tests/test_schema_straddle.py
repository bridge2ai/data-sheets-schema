"""Replicates generated against different schemas are visible (#517).

The 2026-08-11 v1 arm ran across #503, which added `data_governance`. rep1
predates it and has no such slot; rep2 and rep3 postdate it and all ten
populate one. That difference reads as replicate variance and is not.

`d4d runs check --strict` exited 0 on all fifteen, correctly: each record
individually names the schema it saw, and every single-record check it has
was satisfied. The property is only visible *between* records, and nothing
looked between them.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.runs import generation_digest, schema_straddle

ARM = "2026-08-11_claude-opus-5-claudecode-generic"
CORE = Path("data/d4d_concatenated/claudecode_agent_core")
PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC")


def _rows(labels, projects=PROJECTS, method="claudecode_agent"):
    return [{"method": method, "label": l, "project": p}
            for l in labels for p in projects]


class TestTheLogicOnFixtures(unittest.TestCase):
    """The same properties on synthetic records, so they are still checked
    where the corpus is absent — a shallow CI checkout, or after the arm is
    eventually archived. The real-arm tests below are the ones that show the
    check fires on the records that defeated every other check; these are the
    ones that keep working when it does not."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def _record(self, label, project, digest):
        path = self.dir / "m_core" / label / f"{project}_provenance.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {"schema": {"digest_md5": digest}} if digest else {"schema": {}}
        path.write_text(yaml.safe_dump(body), encoding="utf-8")
        return {"method": "m", "label": label, "project": project}

    def test_two_digests_in_one_series_is_a_straddle(self):
        rows = [self._record("s_rep1", "P", "aaa"),
                self._record("s_rep2", "P", "bbb")]
        found = schema_straddle(rows, self.dir)
        self.assertEqual(sorted(found["m/s"]), ["aaa", "bbb"])

    def test_one_digest_is_not(self):
        rows = [self._record("s_rep1", "P", "aaa"),
                self._record("s_rep2", "P", "aaa")]
        self.assertEqual(schema_straddle(rows, self.dir), {})

    def test_two_series_do_not_contaminate_each_other(self):
        """Different configs legitimately sit at different schemas — that is
        ordinary evolution, and reporting it would fire on the whole corpus."""
        rows = [self._record("one_rep1", "P", "aaa"),
                self._record("two_rep1", "P", "bbb")]
        self.assertEqual(schema_straddle(rows, self.dir), {})

    def test_a_missing_digest_does_not_manufacture_a_straddle(self):
        rows = [self._record("s_rep1", "P", "aaa"),
                self._record("s_rep2", "P", None)]
        self.assertEqual(schema_straddle(rows, self.dir), {})

    def test_a_straddle_across_projects_of_one_series_is_reported_once(self):
        """The series is the unit, not the project: an arm generated across a
        schema change is one event however many projects it covers."""
        rows = [self._record("s_rep1", "P", "aaa"),
                self._record("s_rep1", "Q", "aaa"),
                self._record("s_rep2", "P", "bbb"),
                self._record("s_rep2", "Q", "bbb")]
        found = schema_straddle(rows, self.dir)
        self.assertEqual(list(found), ["m/s"])
        self.assertEqual(found["m/s"]["aaa"], ["s_rep1"],
                         "labels are deduplicated across projects")

    def test_a_missing_record_is_not_fatal(self):
        rows = [{"method": "m", "label": "s_rep1", "project": "GONE"},
                self._record("s_rep2", "P", "bbb")]
        self.assertEqual(schema_straddle(rows, self.dir), {})


@unittest.skipUnless((CORE / f"{ARM}_rep1").exists(), "arm absent")
class TestDetection(unittest.TestCase):
    """Driven by the real arm rather than fixtures, so the detection is
    demonstrated on the records that defeated every other check. That makes
    the arm a precondition: without it `generation_digest` returns None for
    every row and these would pass by finding nothing."""

    def test_a_series_on_one_schema_is_not_reported(self):
        """The false-positive direction. Every other series in the corpus is
        homogeneous, and a check that flagged them would be ignored."""
        rows = _rows([f"{ARM}_rep2", f"{ARM}_rep3"])
        self.assertEqual(schema_straddle(rows), {})

    def test_the_straddled_arm_is_reported(self):
        rows = _rows([f"{ARM}_rep{n}" for n in (1, 2, 3)])
        found = schema_straddle(rows)
        self.assertEqual(len(found), 1)
        [by_digest] = found.values()
        self.assertEqual(len(by_digest), 2)

    def test_it_says_which_replicates_are_on_which_side(self):
        """A bare 'this series is straddled' would leave the reader to redo
        the work. The split is the actionable part."""
        rows = _rows([f"{ARM}_rep{n}" for n in (1, 2, 3)])
        [by_digest] = schema_straddle(rows).values()
        sides = sorted(sorted(l.rsplit("_", 1)[-1] for l in labels)
                       for labels in by_digest.values())
        self.assertEqual(sides, [["rep1"], ["rep2", "rep3"]])

    def test_a_single_replicate_cannot_straddle(self):
        self.assertEqual(schema_straddle(_rows([f"{ARM}_rep1"])), {})

    def test_a_missing_digest_is_not_a_distinct_schema(self):
        """Absent is no claim, not a different claim. Counting it as a value
        would report every pre-digest series as straddled, which is false and
        would bury the real ones."""
        rows = _rows([f"{ARM}_rep2", f"{ARM}_rep3"]) + [
            {"method": "claudecode_agent", "label": f"{ARM}_rep9",
             "project": "NOWHERE"}]
        self.assertEqual(schema_straddle(rows), {})

    def test_a_label_without_a_replicate_index_is_skipped(self):
        """There is no series to compare it against."""
        rows = [{"method": "claudecode_agent", "label": ARM,
                 "project": p} for p in PROJECTS]
        self.assertEqual(schema_straddle(rows), {})


@unittest.skipUnless((CORE / f"{ARM}_rep1").exists(), "arm absent")
class TestAgainstTheRealArm(unittest.TestCase):
    """The records on disk, because the point is what actually happened."""

    def test_rep1_and_rep2_really_do_name_different_schemas(self):
        """The premise. If a future rebuild makes these equal, the detection
        tests above keep passing while testing nothing."""
        a = generation_digest("claudecode_agent", f"{ARM}_rep1", "AI_READI")
        b = generation_digest("claudecode_agent", f"{ARM}_rep2", "AI_READI")
        self.assertTrue(a and b)
        self.assertNotEqual(a, b)

    def test_the_split_is_structural_not_scattered(self):
        """Five of five rep1 records lack `data_governance` and ten of ten
        rep2/rep3 records have it. A perfect split along the schema boundary
        is what distinguishes a schema effect from model variation — had it
        been 3 of 5, this would be an ordinary difference between runs.
        """
        full = Path("data/d4d_concatenated/claudecode_agent")
        for rep, expected in ((1, False), (2, True), (3, True)):
            for project in PROJECTS:
                path = full / f"{ARM}_rep{rep}" / f"{project}_d4d.yaml"
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                present = bool(data.get("data_governance"))
                with self.subTest(rep=rep, project=project):
                    self.assertEqual(present, expected)

    def test_generation_digest_is_not_the_validation_pin(self):
        """These answer different questions and must not be conflated.

        rep1 was generated pre-#503 and validated after it, so it names the
        old digest here and the current schema in `validation.schema`. A check
        that read the validation pin would see no straddle at all — which is
        precisely why this one reads the generation digest.
        """
        record = CORE / f"{ARM}_rep1" / "AI_READI_provenance.yaml"
        data = yaml.safe_load(record.read_text(encoding="utf-8")) or {}
        pinned = (data.get("validation") or {}).get("schema") or {}
        self.assertTrue(pinned.get("full_sha256"),
                        "no validation pin, so this test proves nothing")

        from data_sheets_schema.provenance import FULL_SCHEMA, _sha256
        self.assertEqual(pinned["full_sha256"], _sha256(FULL_SCHEMA),
                         "the verdict is against the current schema")
        self.assertNotEqual(
            generation_digest("claudecode_agent", f"{ARM}_rep1", "AI_READI"),
            generation_digest("claudecode_agent", f"{ARM}_rep2", "AI_READI"))

    def test_the_arm_still_passes_every_single_record_check(self):
        """Not a contradiction — the reason the check was needed.

        Each record is sound. If this ever fails, the straddle is no longer
        the interesting thing about this arm.
        """
        from data_sheets_schema.runs import (bundle_drift,
                                             canonical_prompt_status,
                                             validation_status, verify_request)
        for rep in (1, 2, 3):
            for project in PROJECTS:
                label = f"{ARM}_rep{rep}"
                with self.subTest(rep=rep, project=project):
                    self.assertEqual(
                        verify_request("claudecode_agent", label, project)[0],
                        "match")
                    self.assertEqual(
                        canonical_prompt_status(
                            "claudecode_agent", label, project)[0], "canonical")
                    # Not asserted `current`: the AI_READI bundle changed on
                    # 2026-08-12 when it absorbed the release-3.0.0 RO-Crate
                    # and the v2.0 licence (#539), so those records correctly
                    # report `drifted` — they state the bytes they read, and
                    # the path no longer resolves to them. `absent` would be a
                    # different matter, since it means the bundle is gone.
                    self.assertIn(
                        bundle_drift("claudecode_agent", label, project)[0],
                        ("current", "drifted"))
                    self.assertEqual(
                        validation_status("claudecode_agent", label, project),
                        "valid")


class TestTheCheckReportsIt(unittest.TestCase):
    def test_check_names_the_straddled_series(self):
        out = subprocess.run(["poetry", "run", "d4d", "runs", "check"],
                             capture_output=True, text=True,
                             check=False).stdout
        if f"{ARM}_rep1" not in out and ARM not in out:
            self.skipTest("arm absent from corpus")
        self.assertIn("more than one schema", out)

    def test_it_is_reported_and_not_fatal(self):
        """A straddled series is usable if it is known to be straddled. Making
        it fatal would force a rerun of correct records to clear a gate."""
        result = subprocess.run(
            ["poetry", "run", "d4d", "runs", "check", "--strict"],
            capture_output=True, text=True, check=False)
        if "more than one schema" not in result.stdout:
            self.skipTest("no straddled series in corpus")
        self.assertEqual(result.returncode, 0)
