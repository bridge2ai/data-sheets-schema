"""The recall absence lexicon v3 gives up on `rsn.source-ranking` (#3705).

`scripts/absence_v3_recall.py` names the v2 matches v3 drops, computes why v3
drops each, and renders `notes/absence_v3_recall.md` only beside per-phrase
judgements that are the draw it names. The fixture tests build their own
corpus; the corpus-marked test reproduces the committed note from the pinned
records.
"""
import copy
import importlib.util
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import absence_lint as al
from data_sheets_schema import lexicon as lx

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "absence_v3_recall.py"
RSN = "record_self_narration"

#: One leaf per cause, each a sentence of the kind a record carries, with the
#: v2 term v3 drops and the cause the script must give it.
LEAVES = [
    ("The higher-ranked source is preferred.", None, None),                                  # v3 keeps it
    ("Publisher: two tier-1 sources disagree.", "tier-1 sources", "no_verb"),
    ("FAIRhub, the higher-ranked source, gives 19 July 2023 as the start of the collection period "
     "for the whole study, and that value is recorded here.", "higher-ranked", "window"),
    ("The higher-ranked source gives 19 July 2023; that date is recorded here.", "higher-ranked", "semicolon"),
    ("Two tier-1 sources disagree. Both values are recorded above.", "tier-1 sources", "other_sentence"),
    ("The value used from the input manifest is the higher-ranked one.", "input manifest", "absorbed"),
    ("It was preferred over the lower-ranked source, the higher-ranked one being older.",
     "higher-ranked", "consumed"),
]


def _script():
    spec = importlib.util.spec_from_file_location("absence_v3_recall", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Causes(unittest.TestCase):
    """Each cause is decided by v3's own regex with one bound lifted."""

    def setUp(self):
        self.m = _script()
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.corpus = self.dir / "d4d_concatenated"
        path = self.corpus / "m_a" / "label" / "P_d4d.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(yaml.safe_dump({"source_caveats": [text for text, _, _ in LEAVES],
                                        "notes": "This record describes the release, the highest-ranked "
                                                 "source in the bundle."}), encoding="utf-8")
        self.pins = self.m.baseline.current_records(self.corpus)

    def test_every_dropped_match_gets_its_cause(self):
        found = self.m.dropped(self.corpus, self.pins)
        got = {(h["pointer"], h["text"]): h["cause"] for _, h in found["rows"]}
        want = {(f"/source_caveats/{i}", term): cause for i, (_, term, cause) in enumerate(LEAVES) if term}
        want[("/notes", "highest-ranked")] = "no_verb"
        self.assertEqual(got, want)
        self.assertEqual(found["totals"]["v2"] - found["totals"]["v3"], len(found["rows"]))

    def test_flagged_names_the_v3_phrases_in_the_sentence_to_its_full_stop(self):
        """A referent sentence that `rsn.this-record` still counts is flagged;
        a source conflict with no other phrase is not; a `;` does not end the
        sentence the flag looks at, although it ends v3's window."""
        rows = {h["pointer"]: h for _, h in self.m.dropped(self.corpus, self.pins)["rows"]}
        self.assertEqual(rows["/notes"]["flagged"], ["rsn.this-record"])
        self.assertEqual(rows["/source_caveats/1"]["flagged"], [])
        self.assertEqual(rows["/source_caveats/2"]["flagged"], ["rsn.recorded-here"])
        self.assertEqual(rows["/source_caveats/3"]["flagged"], ["rsn.recorded-here"])   # past the `;`
        self.assertEqual(rows["/source_caveats/4"]["flagged"], [])     # the verb is in the next sentence

    def test_a_pattern_without_the_window_is_refused(self):
        v3 = lx.load(al.LEXICON, 3)
        pattern = next(p for p in v3.patterns if p.id == self.m.PATTERN)
        self.assertEqual(len(self.m._alternatives(pattern.regex.pattern)), 3)
        regex = re.compile(pattern.regex.pattern.replace("{0,80}?", "{0,120}?"), pattern.regex.flags)
        widened = lx.Pattern(id=pattern.id, cls=pattern.cls, regex=regex)
        with self.assertRaises(self.m.Refused):
            self.m._variants(widened)

    def test_a_changed_pinned_record_is_stale(self):
        path = self.corpus / "m_a" / "label" / "P_d4d.yaml"
        path.write_text(path.read_text(encoding="utf-8") + "description: more\n", encoding="utf-8")
        with self.assertRaises(self.m.baseline.Stale):
            self.m.dropped(self.corpus, self.pins)


class Judgements(unittest.TestCase):
    """The note is rendered only beside judgements that are the draw its
    entry names, whose computed fields are what the script computes, and
    whose readings carry their verdicts."""

    def setUp(self):
        self.m = _script()
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        corpus = self.dir / "d4d_concatenated"
        path = corpus / "m_a" / "label" / "P_d4d.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(yaml.safe_dump({"source_caveats": [text for text, _, _ in LEAVES]}), encoding="utf-8")
        self.found = self.m.dropped(corpus, self.m.baseline.current_records(corpus))
        drawn = self.m.draw(self.found, 10, 7)
        _, picked = drawn[RSN]
        self.rows = [{"n": i, "record": p, "pointer": h["pointer"], "start": h["start"], "end": h["end"],
                      "patterns": h["patterns"], "text": h["text"], "cause": h["cause"], "flagged": h["flagged"],
                      "reading": "source" if h["cause"] == "no_verb" else "construction",
                      "verdict": "borderline" if h["cause"] == "no_verb" else "in_class", "reason": "fixture"}
                     for i, (p, h) in enumerate(picked, 1)]
        self.file = self.dir / "judgements.yaml"
        self.m.RECALL = {**self.m.RECALL, "record_set_sha256": self.found["record_set_sha256"], "sample": 10,
                         "seed": 7, "draw_sha256": self.m.baseline.draw_sha256(drawn),
                         "classes": {RSN: (len(self.rows) - 1, 1, 0)}, "judgements": str(self.file)}
        self._write(self.rows)

    def _write(self, rows):
        r = self.m.RECALL
        self.file.write_text(yaml.safe_dump({
            "draw_sha256": r["draw_sha256"], "from_lexicon_sha256": r["from_lexicon_sha256"],
            "lexicon_sha256": r["lexicon_sha256"], "record_set_sha256": r["record_set_sha256"],
            "sample": r["sample"], "seed": r["seed"], "recorded": "2026-09-30",
            "judgements": {RSN: rows}}, sort_keys=False), encoding="utf-8")

    def test_the_note_renders_and_counts_the_readings(self):
        md = self.m.render_markdown(self.found)
        self.assertIn(f"| construction | in_class | {len(self.rows) - 1} |", md)
        self.assertIn("| source | borderline | 1 |", md)
        self.assertIn("| `no_verb` | 1 | 0 | 0 | 1 | 0 | 0 |", md)
        self.assertIn(f"v3 therefore gives up {len(self.rows) - 1} in-class matches", md)

    def test_a_row_whose_cause_is_not_the_computed_one_is_refused(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["cause"] = "window" if rows[0]["cause"] != "window" else "no_verb"
        self._write(rows)
        with self.assertRaisesRegex(self.m.Refused, "not the computed"):
            self.m.render_markdown(self.found)

    def test_a_row_whose_flag_is_not_the_computed_one_is_refused(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["flagged"] = rows[0]["flagged"] + ["rsn.slot-word"]
        self._write(rows)
        with self.assertRaisesRegex(self.m.Refused, "not the computed"):
            self.m.render_markdown(self.found)

    def test_a_reading_that_does_not_carry_its_verdict_is_refused(self):
        rows = copy.deepcopy(self.rows)
        i = next(i for i, r in enumerate(rows) if r["reading"] == "construction")
        rows[i]["reading"] = "absence"
        self._write(rows)
        with self.assertRaisesRegex(self.m.Refused, "does not carry the verdict"):
            self.m.render_markdown(self.found)

    def test_a_tally_that_is_not_the_entry_is_refused(self):
        self.m.RECALL["classes"] = {RSN: (len(self.rows), 0, 0)}
        with self.assertRaisesRegex(self.m.Refused, "verdict tally"):
            self.m.render_markdown(self.found)

    def test_another_draw_is_refused(self):
        self._write(list(reversed(self.rows)))
        with self.assertRaisesRegex(self.m.Refused, "not the draw"):
            self.m.render_markdown(self.found)


class Committed(unittest.TestCase):
    """The committed judgements, read without walking the corpus."""

    def test_the_committed_judgements_are_the_entry_they_name(self):
        m = _script()
        r = m.RECALL
        v2, v3 = (lx.load(al.LEXICON, v) for v in (2, 3))
        self.assertEqual((r["from_lexicon_sha256"], r["lexicon_sha256"]), (v2.sha256, v3.sha256))
        data = m.baseline.read_judgements(r["lexicon_sha256"], r)
        rows = data["judgements"][RSN]
        self.assertEqual(len(rows), r["sample"])
        self.assertEqual({row["reading"] for row in rows} - set(m.READINGS), set())
        self.assertTrue(all(m.READINGS[row["reading"]] == row["verdict"] for row in rows))
        self.assertEqual({row["cause"] for row in rows} - set(m.CAUSES), set())
        self.assertTrue(all(row["patterns"] == [m.PATTERN] for row in rows))


@pytest.mark.corpus   # walks the committed corpus
def test_the_committed_recall_note_is_what_its_records_and_judgements_reproduce():
    m = _script()
    found = m.dropped(m.baseline.CORPUS, m.baseline.read_pins(m.baseline.PINS))
    assert (found["totals"]["v2"], found["totals"]["v3"], len(found["rows"])) == (336, 248, 88)
    assert m.OUT_MD.read_text(encoding="utf-8") == m.render_markdown(found), (
        "notes/absence_v3_recall.md does not match its records and judgements: run scripts/absence_v3_recall.py")


if __name__ == "__main__":
    unittest.main()
