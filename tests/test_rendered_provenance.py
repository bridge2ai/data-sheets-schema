"""The generation metadata reaches the reader of a datasheet (#505).

Camille Nebeker's review asked whether a metadata record exists for the
generation process — input docs, model, parameters, reproducibility context. It
does, and has since #353. The review's other instinct was right too: appending
it to the D4D would break LinkML, which is exactly why it is a separate file.

So the gap was never capture. A reviewer reading a datasheet had no way to
reach it — a sibling directory, a filename they have no reason to guess, and a
run-label scheme they would have to already know.
"""

import tempfile
import unittest
from pathlib import Path

import yaml

from src.html.human_readable_renderer import provenance_for, render_yaml_file

LABEL = "2026-08-11_claude-opus-5-claudecode-generic_rep1"
RECORD = Path("data/d4d_concatenated/claudecode_agent") / LABEL / "CHORUS_d4d.yaml"


class TestProvenanceLookup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.full = self.root / "claudecode_agent" / "L" / "P_d4d.yaml"
        self.core = self.root / "claudecode_agent_core" / "L"
        self.full.parent.mkdir(parents=True)
        self.core.mkdir(parents=True)
        self.full.write_text("id: x\n", encoding="utf-8")

    def _write_prov(self, body):
        (self.core / "P_provenance.yaml").write_text(
            yaml.safe_dump(body), encoding="utf-8")

    def test_it_finds_the_sibling_record(self):
        self._write_prov({"record_mode": "live",
                          "model": {"model": "claude-opus-5"}})
        rows, _ = provenance_for(self.full)
        self.assertIn(("Model", "claude-opus-5"), rows)

    def test_a_missing_record_yields_none_rather_than_an_empty_section(self):
        """A datasheet with no provenance and one whose provenance failed to
        load must not look alike."""
        rows, unverified = provenance_for(self.full)
        self.assertIsNone(rows)
        self.assertIsNone(unverified)

    def test_an_unreadable_record_yields_none_rather_than_raising(self):
        (self.core / "P_provenance.yaml").write_bytes(b"\xff\xfe not yaml")
        self.assertEqual(provenance_for(self.full), (None, None))

    def test_absent_fields_are_omitted_not_rendered_blank(self):
        """A blank row reads as 'we looked and there was nothing', which is a
        different claim from 'this record does not carry that field'."""
        self._write_prov({"record_mode": "live", "model": {}})
        rows, _ = provenance_for(self.full)
        self.assertTrue(all(v not in (None, "", []) for _, v in rows))

    def test_unverified_entries_are_surfaced(self):
        self._write_prov({
            "record_mode": "live",
            "unverified": [{"field": "model.temperature", "reason": "no knob"}],
        })
        _, unverified = provenance_for(self.full)
        self.assertEqual(unverified, [("model.temperature", "no knob")])

    def test_a_core_record_resolves_to_the_same_provenance(self):
        core_doc = self.core / "P_d4d_core.yaml"
        core_doc.write_text("id: x\n", encoding="utf-8")
        self._write_prov({"record_mode": "live"})
        rows, _ = provenance_for(core_doc)
        self.assertIsNotNone(rows)


@unittest.skipUnless(RECORD.exists(), "corpus record absent")
class TestRenderedOutput(unittest.TestCase):
    def test_the_datasheet_carries_what_the_review_asked_for(self):
        """Input docs, model, parameters and reproducibility context — the
        four things the review listed, in the document a reviewer opens."""
        with tempfile.TemporaryDirectory() as d:
            out = render_yaml_file(RECORD, Path(d) / "out.html")
            html = Path(out).read_text(encoding="utf-8")
        self.assertIn("How this datasheet was generated", html)
        for expected in ("claude-opus-5",                     # model
                         "CHORUS_preprocessed.txt",           # input docs
                         "d4d_generic_arm_prompt.md",         # prompt
                         "_provenance.yaml"):                 # where to look
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

    def test_it_says_why_the_record_is_a_separate_file(self):
        """The review's own instinct — that appending would break LinkML — is
        the reason for the split, and the page should say so rather than leave
        the separation looking accidental."""
        with tempfile.TemporaryDirectory() as d:
            out = render_yaml_file(RECORD, Path(d) / "out.html")
            html = Path(out).read_text(encoding="utf-8")
        self.assertIn("would not validate", html)

    def test_a_datasheet_without_provenance_renders_without_the_section(self):
        with tempfile.TemporaryDirectory() as d:
            orphan = Path(d) / "lonely_d4d.yaml"
            orphan.write_text("id: x\nname: y\n", encoding="utf-8")
            out = render_yaml_file(orphan, Path(d) / "out.html")
            html = Path(out).read_text(encoding="utf-8")
        self.assertNotIn("How this datasheet was generated", html)
