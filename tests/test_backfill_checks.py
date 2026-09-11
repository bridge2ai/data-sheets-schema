"""Backfilling the three post-generation checks onto older records (#552).

The risk this guards is not that the computation is wrong — it is shared with
the runner — but that writing 192 provenance records loses something. Each of
those files carries a header comment `yaml.safe_dump` would silently drop, and
a backfilled verdict makes a claim the run itself never made.
"""

import hashlib
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.backfill_checks import (
    RECORDED_BY,
    _split_header,
    apply,
    declared_bundle,
    record_paths,
)


class HeaderTest(unittest.TestCase):

    def test_comments_are_split_off_and_survive_a_rewrite(self):
        text = ("# D4D generation provenance record\n"
                "# record_version 1 — see src/data_sheets_schema/provenance.py\n"
                "record_mode: live\n")
        header, body = _split_header(text)
        self.assertEqual(header.count("#"), 2)
        self.assertEqual(yaml.safe_load(body), {"record_mode": "live"})

    def test_a_record_with_extra_comments_keeps_them(self):
        """Re-emitted verbatim rather than reconstructed from a template."""
        text = "# one\n# two\n# three\nrecord_mode: live\n"
        self.assertEqual(_split_header(text)[0], "# one\n# two\n# three\n")


class PathTest(unittest.TestCase):

    def test_the_full_record_is_not_beside_the_provenance_file(self):
        p = Path("data/d4d_concatenated/claudecode_agent_core/L/CHORUS_provenance.yaml")
        paths = record_paths(p)
        self.assertEqual(paths["project"], "CHORUS")
        self.assertEqual(paths["core"].parent.name, "L")
        self.assertEqual(paths["core"].parent.parent.name, "claudecode_agent_core")
        self.assertEqual(paths["full"].parent.parent.name, "claudecode_agent")

    def test_declared_bundle(self):
        self.assertEqual(declared_bundle({"inputs": {"bundle_path": "a/b.txt"}}),
                         Path("a/b.txt"))
        self.assertIsNone(declared_bundle({"inputs": {}}))


class ApplyTest(unittest.TestCase):

    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "p.yaml"
        self.path.write_text("# header line\nrecord_mode: live\n",
                             encoding="utf-8")

    def test_writing_is_additive_and_keeps_the_header(self):
        self.assertTrue(apply(self.path, {"grounding": {"checked": True}}))
        text = self.path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# header line\n"))
        loaded = yaml.safe_load(text)
        self.assertEqual(loaded["record_mode"], "live")
        self.assertEqual(loaded["grounding"], {"checked": True})

    def test_an_existing_block_is_left_alone(self):
        """A verdict the run attested outranks one recomputed today."""
        apply(self.path, {"grounding": {"checked": True, "from": "run"}})
        self.assertFalse(apply(self.path, {"grounding": {"from": "backfill"}}))
        self.assertEqual(
            yaml.safe_load(self.path.read_text())["grounding"]["from"], "run")

    def test_overwrite_replaces_it(self):
        apply(self.path, {"grounding": {"from": "run"}})
        self.assertTrue(apply(self.path, {"grounding": {"from": "backfill"}},
                              overwrite=True))


class CorpusTest(unittest.TestCase):
    """What the backfill actually produced, read back off disk."""

    BASE = Path("data/d4d_concatenated")

    def _record(self, label, project):
        p = self.BASE / "claudecode_agent_core" / label / f"{project}_provenance.yaml"
        if not p.exists():
            self.skipTest(f"{p} not present in this checkout")
        return yaml.safe_load(p.read_text(encoding="utf-8"))

    def test_backfilled_blocks_say_so(self):
        """Not the same claim as one the run attested."""
        rec = self._record("2026-08-11_claude-opus-5-claudecode-generic_rep1",
                           "AI_READI")
        self.assertEqual(rec["pair_consistency"]["recorded_by"], RECORDED_BY)

    def test_a_backfilled_pair_verdict_pins_its_schema(self):
        """Identity slots come from the schema, so the verdict depends on it.

        Without this a recomputed verdict cannot be distinguished from one
        reached against a schema that has since moved — the question a reader
        asks first of any recomputed result. #426 is the same lesson for
        validation verdicts.
        """
        rec = self._record("2026-08-11_claude-opus-5-claudecode-generic_rep1",
                           "AI_READI")
        self.assertEqual(set(rec["pair_consistency"]["schema"]),
                         {"full_sha256", "core_sha256"})

    def test_the_computation_itself_pins_all_inputs(self):
        """The code, not the records it already wrote.

        The two tests below read blocks off disk, so they would keep passing
        if the fix were reverted — the records would still carry the pins.
        This recomputes one and fails on the code.
        """
        from data_sheets_schema.backfill_checks import compute
        p = (self.BASE / "claudecode_api_core"
             / "2026-09-04f_claude-opus-5-api-generic-v8_rep2"
             / "VOICE_provenance.yaml")
        if not p.exists():
            self.skipTest(f"{p} not present in this checkout")
        block = compute(p, only={"report_claims"})["report_claims"]
        self.assertEqual(set(block["artifacts"]), {"report", "full", "core", "phase1_snapshot"})
        self.assertEqual(set(block["schema"]), {"full_sha256", "core_sha256"})
        self.assertTrue(block["artifacts"]["full"]["md5"])
        self.assertTrue(block["artifacts"]["core"]["md5"])
        snapshot = block["artifacts"]["phase1_snapshot"]
        self.assertEqual(snapshot["state"], "usable")
        self.assertEqual(snapshot["sha256"], hashlib.sha256(Path(snapshot["path"]).read_bytes()).hexdigest())

    def test_a_backfilled_report_verdict_pins_what_it_read(self):
        """The same lesson as the pair verdict above, learned twice (#1085).

        A schema claim is resolved against the schema and is about the two
        records, so a recomputed `report_claims` block that pins only the
        report cannot be told apart from one reached against records or a
        schema that have since moved. The backfill wrote exactly that until
        the v3 recompute made it visible: 282 records would have lost the
        full and core md5s and the schema digests the runner records.

        Written against the corpus rather than a fixture because the defect
        was invisible in the code and obvious in the diff.
        """
        rec = self._record("2026-09-01_claude-opus-5-api-generic-v7_rep1",
                           "VOICE")
        block = rec["report_claims"]
        if block.get("recorded_by") != RECORDED_BY:
            self.skipTest("this record's block was not written by the backfill")
        self.assertEqual(set(block["schema"]), {"full_sha256", "core_sha256"})
        self.assertEqual(set(block["artifacts"]), {"report", "full", "core", "phase1_snapshot"})
        for name in ("report", "full", "core"):
            with self.subTest(artifact=name):
                self.assertIn("md5", block["artifacts"][name])
                self.assertIn("path", block["artifacts"][name])

    def test_every_backfilled_report_block_in_the_corpus_pins_all_inputs(self):
        """Not one record: the whole recompute. An `md5: null` is allowed and
        says the file was absent; a missing key is the defect."""
        thin = []
        for p in sorted(self.BASE.rglob("*_provenance.yaml")):
            rec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            block = rec.get("report_claims") or {}
            if block.get("recorded_by") != RECORDED_BY or not block.get("checked"):
                continue
            if (set(block.get("artifacts") or {}) != {"report", "full", "core", "phase1_snapshot"}
                    or set(block.get("schema") or {}) != {"full_sha256",
                                                          "core_sha256"}):
                thin.append(str(p))
            snapshot = (block.get("artifacts") or {}).get("phase1_snapshot")
            if block.get("snapshot_checked"):
                if (not snapshot or snapshot.get("state") != "usable"
                        or snapshot.get("sha256") != hashlib.sha256(Path(snapshot["path"]).read_bytes()).hexdigest()):
                    thin.append(f"{p}: missing or stale phase-1 snapshot pin")
        if not thin and not list(self.BASE.rglob("*_provenance.yaml")):
            self.skipTest("no records in this checkout")
        self.assertEqual(thin, [])

    def test_every_checked_report_block_in_the_corpus_is_under_one_instrument(self):
        """A half-finished backfill at the next revision would leave the
        corpus straddling two instruments with every other test green, and
        a sum over `rows_by_record` would silently mix two readings (#1139
        review, S3). Every checked block carries the current instrument and
        the tally with its fixed keys, summing to `disposition_rows`."""
        from data_sheets_schema.report_claims import RECORD_COLUMN_VALUES, REPORT_CLAIMS_INSTRUMENT
        off = []
        seen = 0
        for p in sorted(self.BASE.rglob("*_provenance.yaml")):
            rec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            block = rec.get("report_claims") or {}
            if not block.get("checked"):
                continue
            seen += 1
            rows = block.get("rows_by_record")
            if block.get("instrument") != REPORT_CLAIMS_INSTRUMENT:
                off.append(f"{p}: instrument {str(block.get('instrument'))[:40]!r}")
            elif not isinstance(rows, dict) or tuple(rows) != RECORD_COLUMN_VALUES:
                off.append(f"{p}: rows_by_record keys {list(rows) if isinstance(rows, dict) else rows}")
            elif sum(rows.values()) != block.get("disposition_rows"):
                off.append(f"{p}: rows_by_record sums to {sum(rows.values())}, disposition_rows {block.get('disposition_rows')}")
        if not seen:
            self.skipTest("no checked report_claims blocks in this checkout")
        self.assertEqual(off, [])

    def test_the_agentic_arm_is_clean_once_the_guard_is_applied(self):
        """Reverses what this test asserted when it was first written (#550).

        It asserted the agentic arm was not clean, on a backfill that omitted
        `schema_moved`. `related_datasets` was added to `CoreDataset` after
        these records were written, so its absence from core is a fact about
        the schema's history — #520 makes that a warning, and the first version
        of the backfill made it an error in 70 pairs.

        With the guard the arm is clean, which is what I originally reported
        and then wrongly corrected.
        """
        rec = self._record("2026-08-11_claude-opus-5-claudecode-generic_rep1",
                           "AI_READI")
        pair = rec["pair_consistency"]
        self.assertTrue(pair["ran"])
        self.assertTrue(pair["schema_moved"],
                        "the premise: this pair predates the current schema")
        self.assertTrue(pair["consistent"])

    def test_the_v4_arm_still_diverges_with_the_guard(self):
        """The guard does not explain the API arm away.

        All 12 v4 pairs predate the current schema too, so the guard applies to
        both arms equally. This one fails on content, which no schema change
        excuses.
        """
        rec = self._record("2026-08-13_claude-opus-5-api-generic-v4_rep1",
                           "CHORUS")
        pair = rec["pair_consistency"]
        self.assertTrue(pair["schema_moved"])
        self.assertFalse(pair["consistent"])
        self.assertTrue(any("content" in f["code"] for f in pair["findings"]),
                        "content divergence, not a presence artifact")

    def test_grounding_is_declined_for_a_drifted_bundle(self):
        """Checking against today's bundle would test a file the run never read.

        At least one record must decline, or the drift handling is untested —
        59 records name a bundle whose bytes have changed.
        """
        declined = 0
        for p in self.BASE.glob("*_core/*/*_provenance.yaml"):
            rec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            g = rec.get("grounding") or {}
            if not g.get("checked") and "drifted" in (g.get("reason") or ""):
                declined += 1
        if not list(self.BASE.glob("*_core/*/*_provenance.yaml")):
            self.skipTest("no corpus in this checkout")
        self.assertGreater(declined, 0)


if __name__ == "__main__":
    unittest.main()


class RefusalTest(unittest.TestCase):
    """A record that does not parse must not be replaced by the blocks."""

    def _write(self, text):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p = Path(tmp.name) / "p.yaml"
        p.write_text(text, encoding="utf-8")
        return p

    def test_a_record_that_is_not_a_mapping_is_refused(self):
        p = self._write("# header\n- a\n- list\n")
        with self.assertRaises(ValueError):
            apply(p, {"grounding": {"checked": True}})
        self.assertIn("- list", p.read_text(encoding="utf-8"),
                      "the original content must still be there")

    def test_an_all_comment_file_is_refused_rather_than_filled_in(self):
        p = self._write("# only comments\n")
        with self.assertRaises(ValueError):
            apply(p, {"grounding": {"checked": True}})


class NeverEraseAMeasurement(unittest.TestCase):
    def test_an_unchecked_recomputation_does_not_overwrite_a_checked_block(self):
        """#907 review: a --blocks receipts pass over a drifted bundle erased
        three run-attested receipts blocks with `checked: false`."""
        import tempfile
        from pathlib import Path

        import yaml

        from data_sheets_schema.backfill_checks import apply
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "P_provenance.yaml"
            p.write_text("# h\n" + yaml.safe_dump({"run": {"label": "L"},
                                                    "receipts": {"checked": True, "chunks": {"reviewed": 28}},
                                                    "form": {"british_spellings": 3}}))
            changed = apply(p, {"receipts": {"checked": False, "reason": "bundle drifted"},
                                "form": {"british_spellings": 5}}, overwrite=True)
            rec = yaml.safe_load(p.read_text())
            self.assertTrue(changed)
            self.assertEqual(rec["receipts"]["chunks"]["reviewed"], 28)
            self.assertEqual(rec["form"]["british_spellings"], 5)
