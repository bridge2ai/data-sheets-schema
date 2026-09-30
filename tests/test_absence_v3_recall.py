"""The recall absence lexicon v3 gives up on `rsn.source-ranking` (#3705).

`scripts/absence_v3_recall.py` names the v2 matches v3 drops, computes why v3
drops each, and renders `notes/absence_v3_recall.md` only beside per-phrase
judgements that are the draw it names. The fixture tests build their own
corpus; the corpus-marked test reproduces the committed note from the pinned
records.
"""
import contextlib
import copy
import dataclasses
import importlib.util
import re
import shutil
import tempfile
import unittest
from unittest import mock
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

#: What the registered v4 pattern does with each fixture leaf's dropped term
#: (#3791): its window runs to the end of the sentence across `;`, so the
#: `window` and `semicolon` rows are recovered; a full stop still ends it; an
#: absorbed name stays inside a longer match; a consumed verb stays consumed.
V4 = {
    "/source_caveats/1": "dropped",        # no_verb
    "/source_caveats/2": "recovered",      # window
    "/source_caveats/3": "recovered",      # semicolon
    "/source_caveats/4": "dropped",        # other_sentence
    "/source_caveats/5": "inside",         # absorbed
    "/source_caveats/6": "dropped",        # consumed
    "/source_caveats/7": "recovered",      # semicolon, past the window too
    "/notes": "dropped",                   # no_verb
}


#: A `;` sentence whose dropped term no other v3 phrase shares a sentence
#: with: an in-class row v3 counts nothing in, which v4 recovers (#3896).
UNFLAGGED_SEMICOLON = "The higher-ranked source gives 19 July 2023; that date is used."


@contextlib.contextmanager
def _v4_without_prefer(m):
    """The script's v4, with the preference verbs taken out of the pattern's
    verb list and its bytes' identity kept, so a v3 match resting on
    "preferred" is ended by no v4 match (#3896)."""
    load = m.lx.load

    def narrowed(name, version=None, **kw):
        lexicon = load(name, version, **kw)
        if version != m.NEXT_VERSION:
            return lexicon
        patterns = tuple(dataclasses.replace(p, regex=re.compile(p.regex.pattern.replace(
                             "prefer(?:s|red|ring)?|", ""), p.regex.flags)) if p.id == m.PATTERN else p
                         for p in lexicon.patterns)
        assert patterns != tuple(lexicon.patterns)
        return dataclasses.replace(lexicon, patterns=type(lexicon.patterns)(patterns))

    with mock.patch.object(m.lx, "load", narrowed):
        yield


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

    def test_v4_recovers_the_window_and_semicolon_rows_and_nothing_past_a_full_stop(self):
        found = self.m.dropped(self.corpus, self.pins)
        self.assertEqual({h["pointer"]: h["v4"] for _, h in found["rows"]}, V4)
        self.assertEqual(found["totals"]["v3_not_ended_by_v4"], 0)
        self.assertEqual(found["totals"]["v4"], found["totals"]["v3"] + 3)

    def test_a_v3_match_no_v4_match_ends_at_is_counted(self):
        """#3896: the registered v4 ends every v3 match, so the fixture's
        count is 0; a v4 without the preference verbs does not end the two
        v3 matches that rest on "preferred", and the counter says so."""
        with _v4_without_prefer(self.m):
            found = self.m.dropped(self.corpus, self.pins)
        self.assertEqual(found["totals"]["v3_not_ended_by_v4"], 2)
        self.assertEqual(self.m.dropped(self.corpus, self.pins)["totals"]["v3_not_ended_by_v4"], 0)

    def test_v4_recovers_a_term_past_an_abbreviation_that_no_lift_of_v3_admits_short_of_a_full_stop(self):
        """#3792: v3 and every lift short of crossing a full stop take the
        `.` of "St." for one; v4 does not, and the note tells that recovery
        apart from the window-and-`;` lift's. A verb-first v4 match starts
        before the term, and ending at it is what makes it a recovery."""
        path = self.corpus / "m_a" / "label" / "P_d4d.yaml"
        path.write_text(yaml.safe_dump({"source_caveats": [
            "The higher-ranked source names Washington University in St. Louis as the sponsor, and that name "
            "is used.",
            "The higher-ranked source gives Washington University in St. Louis. Both values are recorded above.",
            # verb first: the v4 match starts at the verb and ends at the term, and that is a recovery
            "Both dates are recorded; two tier-1 sources disagree."]}),
            encoding="utf-8")
        found = self.m.dropped(self.corpus, self.m.baseline.current_records(self.corpus))
        rows = {h["pointer"]: h for _, h in found["rows"]}
        self.assertEqual({p: (h["cause"], h["v4"]) for p, h in rows.items()}, {
            "/source_caveats/0": ("other_sentence", "recovered"),
            "/source_caveats/1": ("other_sentence", "dropped"),
            "/source_caveats/2": ("semicolon", "recovered")})
        self.assertNotIn("cumulative_semicolon", rows["/source_caveats/0"]["admitted_by"])
        self.assertIn("cumulative_full_stop", rows["/source_caveats/0"]["admitted_by"])

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
        self._build([text for text, _, _ in LEAVES])

    def _build(self, leaves):
        """Write the fixture record with these leaves, and judgements that
        are the draw over it: every row in class but the `no_verb` one."""
        self.corpus = self.dir / "d4d_concatenated"
        path = self.corpus / "m_a" / "label" / "P_d4d.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump({"source_caveats": leaves}), encoding="utf-8")
        self.found = self.m.dropped(self.corpus, self.m.baseline.current_records(self.corpus))
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

    def test_the_note_says_what_v4_recovers_from_the_same_judgements(self):
        md = self.m.render_markdown(self.found)
        self.assertIn("## What v4 recovers (#3791)", md)
        self.assertIn("| construction | in_class | 6 | 3 | 1 | 2 |", md)
        self.assertIn("| source | borderline | 1 | 0 | 0 | 1 |", md)
        self.assertIn("| **all** | | 7 | 3 | 1 | 3 |", md)
        self.assertIn("v4 recovers 3 of the 7 dropped matches: 3 in class, 0 borderline and\n0 not in class.", md)
        self.assertIn("none needs an abbreviation's `.`.", md)
        self.assertIn("by reading and cause: 1 construction `absorbed`, 1 construction `consumed`, "
                      "1 construction `other_sentence`.", md)

    def test_the_note_says_how_many_lost_in_class_phrases_v4_recovers(self):
        """#3896: "lost" rows are in-class dropped terms in sentences v3
        counts nothing in. In the fixture one is lost and v4 does not recover
        it; an added `;` sentence with no other phrase is lost and recovered."""
        md = self.m.render_markdown(self.found)
        self.assertIn("It recovers 0 of the 1 in-class phrases in sentences v3 counts nothing in.", md)
        self._build([text for text, _, _ in LEAVES] + [UNFLAGGED_SEMICOLON])
        rows = {h["pointer"]: h for _, h in self.found["rows"]}
        self.assertEqual((rows["/source_caveats/8"]["cause"], rows["/source_caveats/8"]["flagged"],
                          rows["/source_caveats/8"]["v4"]), ("semicolon", [], "recovered"))
        md = self.m.render_markdown(self.found)
        self.assertIn("It recovers 1 of the 2 in-class phrases in sentences v3 counts nothing in.", md)

    def test_the_note_counts_the_v3_matches_no_v4_match_ends_at(self):
        """#3896: with a v4 that lacks the verb one v3 match rests on, that
        match is counted as ended by no v4 match, the note says so, and the
        in-class share v4 keeps loses it."""
        md = self.m.render_markdown(self.found)
        self.assertIn("0 of v3's 3 matches end where no v4 match does.", md)
        self.assertIn("v4 keeps 6 of 9 (66.7%) of the in-class matches v2 had", md)
        with _v4_without_prefer(self.m):
            found = self.m.dropped(self.corpus, self.m.baseline.current_records(self.corpus))
        self.assertEqual(found["totals"]["v3_not_ended_by_v4"], 2)
        md = self.m.render_markdown(found)
        self.assertIn("2 of v3's 3 matches end where no v4 match does.", md)
        self.assertIn("v4 keeps 4 of 9 (44.4%) of the in-class matches v2 had", md)
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

    def test_the_note_restates_v4_at_the_measured_precision(self):
        """v4's matches are v3's at the kept draw's precision plus the
        recovered rows as judged; the "not measured here" sentence is gone
        (#3895)."""
        md = self.m.render_markdown(self.found)
        t = self.found["totals"]
        n_in, n_kept, kept = len(self.kept_rows) - 1, len(self.kept_rows), t["v3"]
        retained, rec_in, lost = kept - t["v3_not_ended_by_v4"], 3, len(self.rows) - 1
        self.assertEqual((t["v4"], retained), (6, 3))
        est, v3_est = retained * n_in / n_kept + rec_in, kept * n_in / n_kept
        lo, hi = self.m.wilson(n_in, n_kept)
        self.assertIn("### v4 at the measured precision", md)
        self.assertIn("the 3 v3 matches it still ends at, the 3 judged dropped rows it\nrecovers, and nothing else.",
                      md)
        self.assertIn(f"v4 keeps an estimated {est:.1f} in-class matches ({retained} × {n_in}/{n_kept} + {rec_in}): "
                      f"a precision of {100 * est / t['v4']:.1f}%", md)
        self.assertIn(f"over those {t['v4']} matches ({100 * (retained * lo + rec_in) / t['v4']:.1f}% to "
                      f"{100 * (retained * hi + rec_in) / t['v4']:.1f}% over the kept draw's interval)", md)
        self.assertIn(f"an estimated **{100 * est / (v3_est + lost):.1f}%** ("
                      f"{100 * (retained * lo + rec_in) / (kept * lo + lost):.1f}% to "
                      f"{100 * (retained * hi + rec_in) / (kept * hi + lost):.1f}%), against v3's "
                      f"{100 * v3_est / (v3_est + lost):.1f}%.", md)
        self.assertIn("As for v3, that is the upper bound.", md)
        self.assertNotIn("not measured here", md)

    def test_v4_matches_no_judgement_covers_are_named_and_left_out(self):
        found = {**self.found, "totals": {**self.found["totals"], "v4": self.found["totals"]["v4"] + 2}}
        md = self.m.render_markdown(found)
        self.assertIn("recovers, and 2 that neither judgement file covers, left out below.", md)
        self.assertIn("over those 6 matches", md)

    def test_v4_at_the_measured_precision_counts_only_the_v3_matches_it_still_ends_at(self):
        with _v4_without_prefer(self.m):
            found = self.m.dropped(self.corpus, self.m.baseline.current_records(self.corpus))
        retained = found["totals"]["v3"] - found["totals"]["v3_not_ended_by_v4"]
        self.assertEqual(retained, 1)
        md = self.m.render_markdown(found)
        self.assertIn(f"are the {retained} v3 matches it still ends at", md)
        self.assertIn(f"({retained} × 1/2 + ", md)

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
        self.assertNotIn("over the kept draw's interval", md)
        self.assertNotIn("sampling error alone", md)
        self.assertIn("in-class matches (3 × 2/3 + 3): a precision of 83.3%\nover those 6 matches,", md)

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
    assert (found["totals"]["v4"], found["totals"]["v3_not_ended_by_v4"]) == (276, 0)
    assert sum(h["v4"] == "recovered" for _, h in found["rows"]) == 28
    assert len(found["kept"]) == 248
    assert m.OUT_MD.read_text(encoding="utf-8") == m.render_markdown(found), (
        "notes/absence_v3_recall.md does not match its records and judgements: run scripts/absence_v3_recall.py")


if __name__ == "__main__":
    unittest.main()
