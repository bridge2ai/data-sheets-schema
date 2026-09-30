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
    ("The higher-ranked source gives 19 July 2023 as the start of the collection period for the "
     "whole of the study; that date is recorded here.", "higher-ranked", "semicolon"),
]

#: The changes `LIFTS` names that admit each fixture leaf's dropped term: one
#: bound lifted on its own, or the bounds lifted cumulatively (#3806).
ADMITTED = {
    "/source_caveats/1": [],                                                     # no_verb
    "/source_caveats/2": ["cumulative_full_stop", "cumulative_semicolon", "cumulative_window", "window"],
    "/source_caveats/3": ["cumulative_full_stop", "cumulative_semicolon", "semicolon_alone"],
    "/source_caveats/4": ["cumulative_full_stop", "full_stop_alone"],
    "/source_caveats/5": [],                                                     # absorbed
    "/source_caveats/6": [],                                                     # consumed
    # past a `;` and more than 80 characters away: crossing `;` alone is not enough
    "/source_caveats/7": ["cumulative_full_stop", "cumulative_semicolon"],
}


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

    def test_each_change_admits_its_rows_alone_and_cumulatively(self):
        """A `semicolon` row whose verb is also past the window is admitted
        only when the window is widened as well: crossing `;` alone is not
        the `semicolon` cause (#3806)."""
        rows = {h["pointer"]: h for _, h in self.m.dropped(self.corpus, self.pins)["rows"]}
        got = {p: rows[p]["admitted_by"] for p in ADMITTED}
        self.assertEqual(got, ADMITTED)
        self.assertEqual(rows["/notes"]["admitted_by"], [])

    def test_a_pattern_without_the_window_is_refused(self):
        v3 = lx.load(al.LEXICON, 3)
        pattern = next(p for p in v3.patterns if p.id == self.m.PATTERN)
        self.assertEqual(len(self.m._alternatives(pattern.regex.pattern)), 3)
        regex = re.compile(pattern.regex.pattern.replace("{0,80}?", "{0,120}?"), pattern.regex.flags)
        widened = lx.Pattern(id=pattern.id, cls=pattern.cls, regex=regex)
        with self.assertRaises(self.m.Refused):
            self.m._variants(widened)

    def test_the_kept_matches_are_v3s_matches(self):
        """The kept population is every v3 match of the pattern, beside the
        dropped ones: v2's count is the two together (#3793)."""
        found = self.m.dropped(self.corpus, self.pins)
        kept = {(h["pointer"], h["text"]) for _, h in found["kept"]}
        self.assertEqual(len(found["kept"]), found["totals"]["v3"])
        self.assertIn(("/source_caveats/0", "higher-ranked"), kept)
        self.assertEqual(len(found["kept"]) + len(found["rows"]), found["totals"]["v2"])
        dropped = {(p, h["pointer"], h["start"], h["end"]) for p, h in found["rows"]}
        self.assertFalse(dropped & {(p, h["pointer"], h["start"], h["end"]) for p, h in found["kept"]})

    def test_the_kept_sample_prints_the_kept_draw(self):
        found = self.m.dropped(self.corpus, self.pins)
        out = self.m.sample(found, 3, 7, "kept")
        self.assertTrue(out[0].startswith(f"## {RSN}: 3 of {len(found['kept'])} kept"))
        self.assertEqual(out[-1], f"draw sha256 {self.m.baseline.draw_sha256(self.m.draw(found, 3, 7, 'kept'))} "
                                  "(--kept-sample 3 --seed 7)")
        self.assertNotIn("cause=", "\n".join(out))

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
        self.kept_file = self.dir / "kept.yaml"
        self._kept(2)

    def _kept(self, n):
        """A judged kept draw of `n`: the first phrase a source statement,
        the rest construction."""
        kept_drawn = self.m.draw(self.found, n, 7, "kept")
        _, kept_picked = kept_drawn[RSN]
        self.kept_rows = [{"n": i, "record": p, "pointer": h["pointer"], "start": h["start"], "end": h["end"],
                           "patterns": h["patterns"], "text": h["text"],
                           "reading": "construction" if i > 1 else "source",
                           "verdict": "in_class" if i > 1 else "borderline", "reason": "fixture"}
                          for i, (p, h) in enumerate(kept_picked, 1)]
        self.m.KEPT = {**self.m.KEPT, "record_set_sha256": self.found["record_set_sha256"], "sample": n,
                       "seed": 7, "draw_sha256": self.m.baseline.draw_sha256(kept_drawn),
                       "classes": {RSN: (len(self.kept_rows) - 1, 1, 0)}, "judgements": str(self.kept_file)}
        self._write_kept(self.kept_rows)

    def _write_kept(self, rows):
        k = self.m.KEPT
        self.kept_file.write_text(yaml.safe_dump({
            "draw_sha256": k["draw_sha256"], "lexicon_sha256": k["lexicon_sha256"],
            "record_set_sha256": k["record_set_sha256"], "sample": k["sample"], "seed": k["seed"],
            "recorded": "2026-09-30", "judgements": {RSN: rows}}, sort_keys=False), encoding="utf-8")

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
        # all fixture rows but no_verb are construction; see ADMITTED
        self.assertIn("| Widen the window only | 1 | 1 | 0 | 0 | 0 | 0 |", md)
        self.assertIn("| Cross `;` only (80-character window kept) | 1 | 1 | 0 | 0 | 0 |", md)
        self.assertIn("| Cross a full stop only (80-character window and `;` kept) | 1 | 1 |", md)
        self.assertIn("| Widen the window and cross `;` | 3 | 3 | 0 | 0 | 0 |", md)
        self.assertIn("| Widen the window, cross `;` and cross a full stop | 4 | 4 | 0 | 0 | 0 |", md)
        self.assertIn(f"v3 therefore gives up {len(self.rows) - 1} in-class matches", md)

    def test_the_note_reports_the_kept_precision_and_the_recall_estimate(self):
        """The kept draw's precision replaces the all-in-class upper bound
        with a point estimate (#3793)."""
        md = self.m.render_markdown(self.found)
        n_in, n_kept, kept = len(self.kept_rows) - 1, len(self.kept_rows), self.found["totals"]["v3"]
        lost = len(self.rows) - 1
        self.assertLess(n_kept, kept)
        self.assertIn("| construction | in_class | 1 |", md)
        self.assertIn("| source | borderline | 1 |", md)
        lo, hi = self.m.wilson(n_in, n_kept)
        self.assertIn(f"{n_in} of the {n_kept} drawn are in class: a precision of {100 * n_in / n_kept:.1f}% "
                      f"(Wilson 95% interval {100 * lo:.1f}% to {100 * hi:.1f}%)", md)
        est = kept * n_in / n_kept
        self.assertIn(f"an estimated **{100 * est / (est + lost):.1f}%**", md)
        self.assertIn("that is the upper bound", md)
        self.assertNotIn("is not measured here", md)

    def test_a_kept_tally_that_is_not_the_entry_is_refused(self):
        self.m.KEPT["classes"] = {RSN: (len(self.kept_rows), 0, 0)}
        with self.assertRaisesRegex(self.m.Refused, "verdict tally"):
            self.m.render_markdown(self.found)

    def test_a_kept_reading_that_does_not_carry_its_verdict_is_refused(self):
        rows = copy.deepcopy(self.kept_rows)
        rows[1]["reading"] = "absence"
        self._write_kept(rows)
        with self.assertRaisesRegex(self.m.Refused, "does not carry the verdict"):
            self.m.render_markdown(self.found)

    def test_a_dropped_match_judged_as_kept_is_refused(self):
        """A dropped phrase in the kept file is refused even when the entry
        names that draw: it is not a match v3 keeps."""
        rows = copy.deepcopy(self.kept_rows)
        rec, h = self.found["rows"][0]
        rows[1].update(record=rec, pointer=h["pointer"], start=h["start"], end=h["end"], text=h["text"])
        self.m.KEPT["draw_sha256"] = self.m.baseline.draw_sha256({RSN: (0, [(r["record"], r) for r in rows])})
        self._write_kept(rows)
        with self.assertRaisesRegex(self.m.Refused, "not a match v3 keeps"):
            self.m.render_markdown(self.found)

    def test_a_kept_set_that_is_not_the_seeded_draw_is_refused(self):
        """A hand-picked kept set, its pin and file in step, is refused: the
        pinned hash must be the draw the entry's seed makes (#3891)."""
        rows = list(reversed(self.kept_rows))
        self.assertGreater(len(rows), 1)
        self.m.KEPT["draw_sha256"] = self.m.baseline.draw_sha256({RSN: (0, [(r["record"], r) for r in rows])})
        self._write_kept(rows)
        with self.assertRaisesRegex(self.m.Refused, "is not the seeded draw"):
            self.m.render_markdown(self.found)

    def test_a_kept_draw_under_another_seed_is_refused(self):
        """The file and pin of another seed's draw, labelled with this seed."""
        for seed in range(8, 200):
            other = self.m.draw(self.found, self.m.KEPT["sample"], seed, "kept")
            if self.m.baseline.draw_sha256(other) != self.m.KEPT["draw_sha256"]:
                break
        else:
            self.fail("no other seed makes another draw")
        rows = [{**r, "record": p, "pointer": h["pointer"], "start": h["start"], "end": h["end"]}
                for r, (p, h) in zip(self.kept_rows, other[RSN][1])]
        self.m.KEPT["draw_sha256"] = self.m.baseline.draw_sha256(other)
        self._write_kept(rows)
        with self.assertRaisesRegex(self.m.Refused, "is not the seeded draw"):
            self.m.render_markdown(self.found)

    def test_a_dropped_set_that_is_not_the_seeded_draw_is_refused(self):
        """The same guard on the recall draw: a census in another order."""
        rows = list(reversed(self.rows))
        self.m.RECALL["draw_sha256"] = self.m.baseline.draw_sha256({RSN: (0, [(r["record"], r) for r in rows])})
        self._write(rows)
        with self.assertRaisesRegex(self.m.Refused, "is not the seeded draw"):
            self.m.render_markdown(self.found)

    def test_a_census_of_the_kept_matches_reports_no_interval(self):
        """A kept draw of every kept match has no sampling error."""
        self._kept(self.found["totals"]["v3"])
        md = self.m.render_markdown(self.found)
        self.assertIn(": every kept match.", md)
        self.assertNotIn("Wilson", md)
        self.assertNotIn("over the precision's interval", md)

    def test_wilson_interval(self):
        lo, hi = self.m.wilson(45, 50)
        self.assertAlmostEqual(lo, 0.7864, places=4)
        self.assertAlmostEqual(hi, 0.9565, places=4)
        self.assertEqual(self.m.wilson(3, 3)[1], 1.0)

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

    def test_the_committed_kept_judgements_are_the_entry_they_name(self):
        m = _script()
        k = m.KEPT
        self.assertEqual((k["lexicon_sha256"], k["record_set_sha256"]),
                         (m.RECALL["lexicon_sha256"], m.RECALL["record_set_sha256"]))
        data = m.baseline.read_judgements(k["lexicon_sha256"], k)
        rows = data["judgements"][RSN]
        self.assertEqual(len(rows), k["sample"])
        self.assertTrue(all(m.READINGS[row["reading"]] == row["verdict"] for row in rows))
        self.assertTrue(all(row["patterns"] == [m.PATTERN] for row in rows))
        self.assertIn(k["draw_sha256"][:8], k["judgements"])


@pytest.mark.corpus   # walks the committed corpus
def test_the_committed_draws_are_the_seeded_draws_they_name():
    """Each committed judgement file's phrases, in its order, are the draw
    `random.Random(seed).sample` makes of the pinned records, and hash to
    both the entry's pin and the file's own `draw_sha256` (#3891; the
    baseline's #3173 check for its precision sample)."""
    m = _script()
    found = m.dropped(m.baseline.CORPUS, m.baseline.read_pins(m.baseline.PINS))
    for entry, population in ((m.KEPT, "kept"), (m.RECALL, "rows")):
        drawn = m.draw(found, entry["sample"], entry["seed"], population)
        data = yaml.safe_load((m.baseline.ROOT / entry["judgements"]).read_text(encoding="utf-8"))
        want = m.baseline.draw_sha256(drawn)
        assert want == entry["draw_sha256"] == data["draw_sha256"], entry["judgements"]
        assert (data["sample"], data["seed"]) == (entry["sample"], entry["seed"])
        assert [(r["record"], r["pointer"], r["start"], r["end"]) for r in data["judgements"][RSN]] == [
            (p, h["pointer"], h["start"], h["end"]) for p, h in drawn[RSN][1]], entry["judgements"]
    assert (m.KEPT["sample"], m.KEPT["seed"], m.KEPT["draw_sha256"][:8]) == (50, 2919, "ec97ce4b")


@pytest.mark.corpus   # walks the committed corpus
def test_the_committed_recall_note_is_what_its_records_and_judgements_reproduce():
    m = _script()
    found = m.dropped(m.baseline.CORPUS, m.baseline.read_pins(m.baseline.PINS))
    assert (found["totals"]["v2"], found["totals"]["v3"], len(found["rows"])) == (336, 248, 88)
    assert len(found["kept"]) == 248
    assert m.OUT_MD.read_text(encoding="utf-8") == m.render_markdown(found), (
        "notes/absence_v3_recall.md does not match its records and judgements: run scripts/absence_v3_recall.py")


if __name__ == "__main__":
    unittest.main()
