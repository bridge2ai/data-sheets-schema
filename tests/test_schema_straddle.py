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


class TestDetection(unittest.TestCase):
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
                    self.assertEqual(
                        bundle_drift("claudecode_agent", label, project)[0],
                        "current")
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
