"""Backfilling the three post-generation checks onto older records (#552).

The risk this guards is not that the computation is wrong — it is shared with
the runner — but that writing 192 provenance records loses something. Each of
those files carries a header comment `yaml.safe_dump` would silently drop, and
a backfilled verdict makes a claim the run itself never made.
"""

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

    def test_the_agentic_arm_is_not_clean(self):
        """Corrects the figure #544 and #550 were filed on.

        I reported the 2026-08-11 agentic arm as 0 divergent pairs of 15. It is
        not: `related_datasets` sits in the full record and not in core, and it
        is a schema-identity slot. The schema pin above rules out a stale-schema
        artifact — those hashes are today's bytes.
        """
        rec = self._record("2026-08-11_claude-opus-5-claudecode-generic_rep1",
                           "AI_READI")
        pair = rec["pair_consistency"]
        self.assertTrue(pair["ran"])
        self.assertFalse(pair["consistent"])
        self.assertIn("related_datasets",
                      " ".join(f["path"] for f in pair["findings"]))

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
